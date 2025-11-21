"""
Adaptive difficulty API router

FASE 6: Main endpoint for adaptive difficulty recommendations
"""
import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.schemas import (
    NextDifficultyRequest,
    NextDifficultyResponse,
    DifficultyAdjustments,
    AdaptiveDecisionLog
)
from app.logic.adaptive_engine import get_adaptive_engine
from app.ai_model.model_manager import get_model_manager
from app.database import get_dynamo_client, get_postgres_client
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/adaptive/api/v1", tags=["adaptive"])


@router.post("/next-difficulty", response_model=NextDifficultyResponse)
async def get_next_difficulty(request: NextDifficultyRequest) -> NextDifficultyResponse:
    """
    Calculate next difficulty level for user
    
    Flow:
    1. Load user stats from DynamoDB (STATS)
    2. Load recent exercise history from DynamoDB (EXERCISE#*)
    3. Try ML model prediction (if available)
    4. Fallback to Rule Engine
    5. Log decision to PostgreSQL for future ML training
    6. Return recommendation
    
    Args:
        request: NextDifficultyRequest with user_id, learning_language, etc.
        
    Returns:
        NextDifficultyResponse with difficulty recommendation
        
    Raises:
        HTTPException: If user not found or invalid data
    """
    try:
        # Step 1: Load user stats from DynamoDB
        dynamo = get_dynamo_client()
        user_stats = dynamo.get_user_stats(
            user_id=request.user_id,
            learning_language=request.learning_language
        )
        
        if not user_stats:
            # User has no stats yet - return default difficulty
            logger.warning(f"No stats found for user {request.user_id}, using default difficulty")
            return NextDifficultyResponse(
                user_id=request.user_id,
                currentDifficulty=1,
                nextDifficulty=1,
                masteryScore=0.5,
                reason="Usuario nuevo - comenzando en dificultad básica",
                modelUsed=False,
                adjustments=DifficultyAdjustments(
                    consistency=0,
                    errorRate=0,
                    speed=0
                ),
                timestamp=datetime.utcnow()
            )
        
        # Step 2: Load recent exercise history
        exercise_history = dynamo.get_recent_exercises(
            user_id=request.user_id,
            learning_language=request.learning_language,
            limit=20
        )
        
        # Determine current difficulty
        if request.current_difficulty is not None:
            current_difficulty = request.current_difficulty
        elif exercise_history:
            # Use most recent exercise difficulty
            current_difficulty = exercise_history[0].get('difficulty', 1)
        else:
            # Default to level 1
            current_difficulty = 1
        
        # Step 3: Try ML model prediction (if available)
        model_manager = get_model_manager()
        ml_prediction = None
        model_used = False
        
        if model_manager.is_model_available():
            # Build feature vector for ML
            user_vector = _build_user_vector(
                user_stats=user_stats,
                exercise_history=exercise_history,
                current_difficulty=current_difficulty
            )
            
            ml_prediction = model_manager.predict(user_vector)
            
            if ml_prediction is not None:
                model_used = True
                logger.info(f"ML model predicted difficulty: {ml_prediction}")
        
        # Step 4: Rule Engine calculation (always run for fallback and logging)
        engine = get_adaptive_engine()
        rule_result = engine.calculate_next_difficulty(
            user_stats=user_stats,
            exercise_history=exercise_history,
            current_difficulty=current_difficulty
        )
        
        # Use ML prediction if available, otherwise use rule result
        if model_used and ml_prediction is not None:
            next_difficulty = ml_prediction
            reason = f"Predicción ML (reglas sugieren: {rule_result['reason']})"
        else:
            next_difficulty = rule_result['nextDifficulty']
            reason = rule_result['reason']
        
        # Step 5: Log decision to PostgreSQL for ML training dataset
        log_data = _build_log_data(
            request=request,
            user_stats=user_stats,
            exercise_history=exercise_history,
            current_difficulty=current_difficulty,
            next_difficulty=next_difficulty,
            mastery_score=rule_result['masteryScore'],
            adjustments=rule_result['adjustments'],
            model_used=model_used,
            model_prediction=ml_prediction
        )
        
        postgres = get_postgres_client()
        postgres.save_adaptive_decision(log_data)
        
        # Step 6: Return response
        return NextDifficultyResponse(
            user_id=request.user_id,
            currentDifficulty=current_difficulty,
            nextDifficulty=next_difficulty,
            masteryScore=rule_result['masteryScore'],
            reason=reason,
            modelUsed=model_used,
            adjustments=DifficultyAdjustments(
                consistency=rule_result['adjustments']['consistency'],
                errorRate=rule_result['adjustments']['errorRate'],
                speed=rule_result['adjustments']['speed']
            ),
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error calculating next difficulty: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating difficulty: {str(e)}"
        )


def _build_user_vector(
    user_stats: Dict[str, Any],
    exercise_history: list,
    current_difficulty: int
) -> Dict[str, Any]:
    """
    Build feature vector for ML model
    
    Args:
        user_stats: User stats from DynamoDB
        exercise_history: Recent exercises
        current_difficulty: Current difficulty level
        
    Returns:
        Dict with features for ML model
    """
    # Calculate metrics from history
    if exercise_history:
        correct_count = sum(1 for ex in exercise_history if ex.get('correct', False))
        recent_accuracy = correct_count / len(exercise_history)
        
        times = [ex.get('timeSpent', 0) for ex in exercise_history if ex.get('timeSpent', 0) > 0]
        avg_response_time = sum(times) / len(times) if times else 15.0
        
        # Count consecutive correct
        consecutive_correct = 0
        for ex in reversed(exercise_history):
            if ex.get('correct', False):
                consecutive_correct += 1
            else:
                break
        
        error_count = len(exercise_history) - correct_count
        error_rate = error_count / len(exercise_history)
    else:
        recent_accuracy = 0.5
        avg_response_time = 15.0
        consecutive_correct = 0
        error_rate = 0.5
    
    return {
        "current_difficulty": current_difficulty,
        "xp": user_stats.get('xp', 0),
        "level": user_stats.get('level', 1),
        "recent_accuracy": recent_accuracy,
        "avg_response_time": avg_response_time,
        "consecutive_correct": consecutive_correct,
        "error_rate": error_rate,
        "mastery_score": 0.5  # Will be calculated by engine
    }


def _build_log_data(
    request: NextDifficultyRequest,
    user_stats: Dict[str, Any],
    exercise_history: list,
    current_difficulty: int,
    next_difficulty: int,
    mastery_score: float,
    adjustments: Dict[str, int],
    model_used: bool,
    model_prediction: int = None
) -> Dict[str, Any]:
    """
    Build log data for PostgreSQL adaptive_logs table
    
    Args:
        request: Original request
        user_stats: User stats
        exercise_history: Recent exercises
        current_difficulty: Current difficulty
        next_difficulty: Recommended difficulty
        mastery_score: Calculated mastery
        adjustments: Rule adjustments
        model_used: Whether ML was used
        model_prediction: ML prediction if available
        
    Returns:
        Dict matching AdaptiveDecisionLog schema
    """
    # Extract metrics from history
    if exercise_history:
        most_recent = exercise_history[0]
        correct = most_recent.get('correct', None)
        
        times = [ex.get('timeSpent', 0) for ex in exercise_history if ex.get('timeSpent', 0) > 0]
        time_spent = sum(times) / len(times) if times else None
        
        error_count = sum(1 for ex in exercise_history if not ex.get('correct', False))
        error_rate = error_count / len(exercise_history)
    else:
        correct = None
        time_spent = None
        error_rate = None
    
    return {
        'user_id': request.user_id,
        'learning_language': request.learning_language,
        'exercise_type': request.exercise_type,
        'current_difficulty': current_difficulty,
        'next_difficulty': next_difficulty,
        'mastery_score': mastery_score,
        'time_spent': time_spent,
        'correct': correct,
        'error_rate': error_rate,
        'consistency_adjustment': adjustments['consistency'],
        'error_adjustment': adjustments['errorRate'],
        'speed_adjustment': adjustments['speed'],
        'model_used': model_used,
        'model_prediction': model_prediction,
        'timestamp': datetime.utcnow()
    }
