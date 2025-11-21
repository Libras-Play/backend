"""
FASE 9: Topic Statistics Router

Provides aggregated statistics for topics:
- Total exercises count
- Breakdown by difficulty (easy, medium, hard)
- Breakdown by type (test, camera)

ANTI-ERROR DESIGN (Lecciones FASE 8):
- Uses async/await correctly (Error #3)
- Uses select() + await execute() (Error #2)
- Unique router prefix to avoid collisions (Error #4)
- All imports included explicitly (Error #6)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, Any
import logging

from app.core.db import get_db
from app.models import Exercise, Topic, DifficultyLevel, ExerciseType

logger = logging.getLogger(__name__)

# ANTI-ERROR #4: Unique prefix to avoid route collisions
router = APIRouter(
    prefix="/api/v1/topics",
    tags=["Topic Statistics - FASE 9"]
)


@router.get("/{topic_id}/stats", response_model=Dict[str, Any])
async def get_topic_stats(
    topic_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated statistics for a topic.
    
    Used by User Service to synchronize total_exercises_available.
    
    Returns:
        {
            "topic_id": int,
            "total_exercises": int,
            "by_difficulty": {
                "easy": int,
                "medium": int,
                "hard": int
            },
            "by_type": {
                "test": int,
                "camera": int
            }
        }
    
    ANTI-ERROR DESIGN:
    - Uses select() for AsyncSession compatibility (Error #2)
    - All queries use await (Error #3)
    - No .query() method (Error #2)
    """
    try:
        # Verificar que el topic existe
        # ANTI-ERROR #2: Usar select() + await execute() (NO .query())
        topic_query = select(Topic).where(Topic.id == topic_id)
        topic_result = await db.execute(topic_query)
        topic = topic_result.scalar_one_or_none()
        
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topic {topic_id} not found"
            )
        
        # ========== TOTAL EXERCISES ==========
        # ANTI-ERROR #2: Usar select(func.count()) en lugar de .query().count()
        total_query = select(func.count(Exercise.id)).where(Exercise.topic_id == topic_id)
        total_result = await db.execute(total_query)
        total_exercises = total_result.scalar() or 0
        
        logger.info(f"Topic {topic_id}: total exercises = {total_exercises}")
        
        # ========== BREAKDOWN BY DIFFICULTY ==========
        by_difficulty = {
            "easy": 0,
            "medium": 0,
            "hard": 0
        }
        
        # Count easy exercises
        # NOTA: En PostgreSQL los valores del enum son "BEGINNER", "INTERMEDIATE", "ADVANCED"
        # pero en Python los mapeamos a EASY, MEDIUM, HARD en DifficultyLevel
        easy_query = select(func.count(Exercise.id)).where(
            Exercise.topic_id == topic_id,
            Exercise.difficulty == DifficultyLevel.EASY  # Compara con "BEGINNER" en DB
        )
        easy_result = await db.execute(easy_query)
        by_difficulty["easy"] = easy_result.scalar() or 0
        
        # Count medium exercises
        medium_query = select(func.count(Exercise.id)).where(
            Exercise.topic_id == topic_id,
            Exercise.difficulty == DifficultyLevel.MEDIUM  # Compara con "INTERMEDIATE" en DB
        )
        medium_result = await db.execute(medium_query)
        by_difficulty["medium"] = medium_result.scalar() or 0
        
        # Count hard exercises
        hard_query = select(func.count(Exercise.id)).where(
            Exercise.topic_id == topic_id,
            Exercise.difficulty == DifficultyLevel.HARD  # Compara con "ADVANCED" en DB
        )
        hard_result = await db.execute(hard_query)
        by_difficulty["hard"] = hard_result.scalar() or 0
        
        logger.info(f"Topic {topic_id} by difficulty: {by_difficulty}")
        
        # ========== BREAKDOWN BY TYPE ==========
        by_type = {
            "test": 0,
            "camera": 0
        }
        
        # Count test exercises
        test_query = select(func.count(Exercise.id)).where(
            Exercise.topic_id == topic_id,
            Exercise.exercise_type == ExerciseType.TEST
        )
        test_result = await db.execute(test_query)
        by_type["test"] = test_result.scalar() or 0
        
        # Count camera exercises
        camera_query = select(func.count(Exercise.id)).where(
            Exercise.topic_id == topic_id,
            Exercise.exercise_type == ExerciseType.CAMERA
        )
        camera_result = await db.execute(camera_query)
        by_type["camera"] = camera_result.scalar() or 0
        
        logger.info(f"Topic {topic_id} by type: {by_type}")
        
        # ========== BUILD RESPONSE ==========
        response = {
            "topic_id": topic_id,
            "total_exercises": total_exercises,
            "by_difficulty": by_difficulty,
            "by_type": by_type
        }
        
        logger.info(f"Topic stats for {topic_id}: {response}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting topic stats for {topic_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving topic statistics: {str(e)}"
        )
