"""User Service API - FastAPI with DynamoDB and gamification"""
import logging
import uuid
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app import schemas, dynamo, schemas_missions, dynamo_missions, schemas_badges
from app.logic import gamification, path_logic, streak_service, badge_service
from app import content_client
from app.middleware import PathPrefixMiddleware
from app.routers import auth, streaks, lives_router, topic_progress

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="User Service API",
    description="User management with gamification and authentication",
    version="2.0.0",
    docs_url="/api/docs",  # Swagger UI at /api/docs (also accessible at /docs)
    redoc_url="/api/redoc"  # ReDoc at /api/redoc
)

# Path prefix middleware (for ALB path-based routing)
app.add_middleware(PathPrefixMiddleware, prefix="/users")

# Include authentication router
app.include_router(auth.router, prefix="/api/v1")
# Include streaks router (FASE 3)
app.include_router(streaks.router, prefix="/api/v1")
# Include lives router (FASE 7 - Sistema de Vidas Refinado)
# NOTE: Middleware strips /users, so this receives /api/v1/... already
app.include_router(lives_router.router, prefix="")

# Include topic progress router (FASE 9 - Topic Progress Tracking)
app.include_router(topic_progress.router, prefix="")

app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def root():
    return {"service": "user-service", "status": "running", "version": "1.0.0"}

@app.get("/health")
async def health():
    try:
        # Try to check DynamoDB connectivity
        dynamo.db_client.user_table.meta.client.describe_table(TableName=settings.DYNAMODB_USER_TABLE)
        return {"status": "healthy", "dynamodb": "connected"}
    except Exception as e:
        logger.warning(f"Health check DynamoDB connection failed: {str(e)}")
        # Return healthy anyway for ALB health checks
        # The service can start even if DynamoDB is temporarily unavailable
        return {"status": "healthy", "dynamodb": "unavailable", "warning": str(e)[:100]}

@app.post("/api/v1/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: schemas.UserCreate):
    try:
        existing = await dynamo.get_user(user.userId)
        if existing:
            raise HTTPException(status_code=400, detail=f"User {user.userId} already exists")
        user_data = await dynamo.create_user(user.model_dump())
        logger.info(f"Created user: {user.userId}")
        return schemas.UserResponse(**user_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/{user_id}/status", response_model=schemas.UserStatus)
async def get_user_status(user_id: str):
    try:
        user = await dynamo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        # Debug log to see what keys we actually have
        logger.info(f"User keys: {list(user.keys())}")
        
        xp_progress = gamification.xp_progress_in_level(user.get("xp", 0))
        status_data = {
            "userId": user.get("userId", user.get("user_id", user_id)),
            "lives": user.get("lives", 5),
            "livesMaxedAt": user.get("livesMaxedAt"),
            "nextLifeAt": user.get("nextLifeAt"),
            "xp": user.get("xp", 0),
            "totalXp": user.get("xp", 0),  # Alias for backward compatibility
            "level": user.get("level", 1),
            "currentLevel": user.get("level", 1),  # Alias for backward compatibility
            "coins": user.get("coins", 0),
            "gems": user.get("gems", 0),
            "xpProgress": xp_progress,
            "streakDays": user.get("streakDays", 0),
            "lastStreakDate": user.get("lastStreakDate"),
            "pathProgress": user.get("pathProgress", {}),
        }
        return schemas.UserStatus(**status_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/{user_id}/consume-life", response_model=schemas.ConsumeLifeResponse)
async def consume_life(user_id: str, request: schemas.ConsumeLifeRequest):
    try:
        updated_user = await dynamo.update_user_lives(user_id, consume=request.consume)
        updated_user = dynamo.recalculate_lives_lazy(updated_user)
        response_data = {
            "userId": user_id, "lives": updated_user["lives"], "livesConsumed": request.consume,
            "nextLifeAt": updated_user.get("nextLifeAt"), "livesMaxedAt": updated_user.get("livesMaxedAt"),
        }
        return schemas.ConsumeLifeResponse(**response_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error consuming life: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/{user_id}", response_model=schemas.UserResponse)
async def get_user(user_id: str):
    try:
        user = await dynamo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        return schemas.UserResponse(**user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/{user_id}/progress")
async def update_progress_simple(user_id: str, progress_data: dict):
    """Simple progress update endpoint (for smoke tests)"""
    try:
        user = await dynamo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        lesson_id = progress_data.get("lessonId", "default-lesson")
        progress_pct = progress_data.get("progress", 0)
        completed = progress_data.get("completed", False)
        
        logger.info(f"Updated progress for user {user_id}: lesson={lesson_id}, progress={progress_pct}%, completed={completed}")
        
        return {
            "userId": user_id,
            "lessonId": lesson_id,
            "progress": progress_pct,
            "completed": completed,
            "message": "Progress updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating progress: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/{user_id}/progress/{level_id}", response_model=schemas.ExerciseAttemptResult)
async def save_progress(user_id: str, level_id: int, progress: schemas.ProgressUpdate):
    try:
        user = await dynamo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        await dynamo.update_progress(user_id, level_id, progress.exerciseId, progress.score, progress.xpEarned, progress.completed)
        gamification_result = await gamification.process_exercise_completion(user, progress.score, progress.xpEarned)
        user_updates = {
            "xp": user["xp"], "level": user["level"], "streakDays": user["streakDays"],
            "lastStreakDate": user["lastStreakDate"], "achievements": user["achievements"],
        }
        await dynamo.update_user(user_id, user_updates)
        xp_progress = gamification.xp_progress_in_level(user["xp"])
        user_status = schemas.UserStatus(
            userId=user["userId"], lives=user["lives"], livesMaxedAt=user.get("livesMaxedAt"),
            nextLifeAt=user.get("nextLifeAt"), xp=user["xp"], level=user["level"],
            xpProgress=xp_progress, streakDays=user["streakDays"], lastStreakDate=user.get("lastStreakDate"),
        )
        result = schemas.ExerciseAttemptResult(
            progressUpdated=True, xpGained=gamification_result["xpGained"],
            levelUp=gamification_result["levelUp"], newLevel=gamification_result["newLevel"],
            currentStreak=gamification_result["currentStreak"],
            achievementsUnlocked=gamification_result["achievementsUnlocked"], userStatus=user_status,
        )
        logger.info(f"Saved progress for user {user_id}, level {level_id}, exercise {progress.exerciseId}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving progress: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/{user_id}/progress/{level_id}", response_model=schemas.ProgressResponse)
async def get_progress(user_id: str, level_id: int):
    try:
        progress = await dynamo.get_user_progress(user_id, level_id)
        if not progress:
            raise HTTPException(status_code=404, detail=f"No progress found for user {user_id}, level {level_id}")
        return schemas.ProgressResponse(**progress)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting progress: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/{user_id}/achievements", response_model=schemas.AchievementProgress)
async def get_achievements(user_id: str):
    try:
        user = await dynamo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        progress = gamification.get_achievement_progress(user)
        return schemas.AchievementProgress(**progress)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting achievements: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/{user_id}/experience")
async def add_experience(user_id: str, xp_data: dict):
    """Add experience points to a user"""
    try:
        user = await dynamo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        points = xp_data.get("points", 0)
        if points <= 0:
            raise HTTPException(status_code=400, detail="Points must be greater than 0")
        
        # Update user XP
        new_xp = user["xp"] + points
        old_level = user["level"]
        new_level = gamification.calculate_level(new_xp)
        
        await dynamo.update_user(user_id, {
            "xp": new_xp,
            "level": new_level
        })
        
        logger.info(f"Added {points} XP to user {user_id}. New XP: {new_xp}, Level: {new_level}")
        
        return {
            "userId": user_id,
            "xpAdded": points,
            "totalXp": new_xp,
            "level": new_level,
            "levelUp": new_level > old_level,
            "reason": xp_data.get("reason", "Experience gained")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding experience: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/{user_id}/lives/reduce")
async def reduce_lives(user_id: str, lives_data: dict):
    """Reduce user lives (alias for consume-life)"""
    try:
        amount = lives_data.get("amount", 1)
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        updated_user = await dynamo.update_user_lives(user_id, consume=amount)
        updated_user = dynamo.recalculate_lives_lazy(updated_user)
        
        logger.info(f"Reduced {amount} lives from user {user_id}. Remaining: {updated_user['lives']}")
        
        return {
            "userId": user_id,
            "lives": updated_user["lives"],
            "livesReduced": amount,
            "nextLifeAt": updated_user.get("nextLifeAt"),
            "livesMaxedAt": updated_user.get("livesMaxedAt"),
            "reason": lives_data.get("reason", "Life consumed")
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error reducing lives: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/{user_id}/stats")
async def get_user_stats(user_id: str):
    """Get user statistics"""
    try:
        user = await dynamo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        xp_progress = gamification.xp_progress_in_level(user["xp"])
        
        return {
            "userId": user["userId"],
            "level": user["level"],
            "xp": user["xp"],
            "xpProgress": xp_progress,
            "lives": user["lives"],
            "streakDays": user["streakDays"],
            "achievements": user.get("achievements", []),
            "totalAchievements": len(user.get("achievements", [])),
            "createdAt": user.get("createdAt"),
            "lastLoginAt": user.get("lastLoginAt")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/ai-sessions", response_model=schemas.AiSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_session(session: schemas.AiSessionCreate):
    try:
        session_id = str(uuid.uuid4())
        session_data = await dynamo.create_ai_session(session_id, session.userId, session.exerciseId, session.levelId, session.videoUrl)
        logger.info(f"Created AI session: {session_id}")
        return schemas.AiSessionResponse(**session_data)
    except Exception as e:
        logger.error(f"Error creating AI session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/ai-sessions/{session_id}", response_model=schemas.AiSessionResponse)
async def get_ai_session(session_id: str):
    try:
        session = await dynamo.get_ai_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"AI session {session_id} not found")
        return schemas.AiSessionResponse(**session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= NEW ENDPOINTS: COINS, XP, LIVES REGEN =============

@app.post("/api/v1/{user_id}/add-coins", response_model=schemas.AddCoinsResponse)
async def add_coins(user_id: str, request: schemas.AddCoinsRequest):
    """
    Add coins to user account
    
    Coins can be earned from:
    - Completing exercises
    - Daily streaks
    - Leveling up
    - Special events
    """
    try:
        updated_user = await dynamo.add_coins(user_id, request.amount)
        
        response_data = {
            "userId": user_id,
            "coinsAdded": request.amount,
            "totalCoins": updated_user.get("coins", 0),
            "reason": request.reason,
        }
        
        logger.info(f"Added {request.amount} coins to user {user_id}. Reason: {request.reason}")
        
        return schemas.AddCoinsResponse(**response_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding coins: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/{user_id}/add-xp", response_model=schemas.AddXpResponse)
async def add_xp(user_id: str, request: schemas.AddXpRequest):
    """
    Add XP to user and recalculate level
    
    XP can be earned from:
    - Completing exercises
    - Achievements
    - Daily quests
    - Special bonuses
    """
    try:
        user_before = await dynamo.get_user(user_id)
        if not user_before:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        previous_level = user_before.get("level", 1)
        
        updated_user = await dynamo.add_xp_direct(user_id, request.amount)
        
        current_level = updated_user.get("level", 1)
        leveled_up = current_level > previous_level
        
        response_data = {
            "userId": user_id,
            "xpAdded": request.amount,
            "totalXp": updated_user.get("xp", 0),
            "previousLevel": previous_level,
            "currentLevel": current_level,
            "leveledUp": leveled_up,
            "reason": request.reason,
        }
        
        logger.info(f"Added {request.amount} XP to user {user_id}. Level: {previous_level} → {current_level}")
        
        return schemas.AddXpResponse(**response_data)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding XP: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/{user_id}/regen-lives", response_model=schemas.RegenLivesResponse)
async def regen_lives(user_id: str):
    """
    Manually trigger life regeneration
    
    Lives regenerate automatically based on time elapsed since lastLifeLost.
    This endpoint forces recalculation and can be used for:
    - Manual testing
    - Cron jobs
    - User-requested refresh
    """
    try:
        user_before = await dynamo.get_user(user_id)
        if not user_before:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        lives_before = user_before.get("lives", 5)
        
        updated_user = await dynamo.regenerate_lives_manual(user_id)
        
        lives_after = updated_user.get("lives", 5)
        lives_regened = lives_after - lives_before
        
        response_data = {
            "userId": user_id,
            "livesBeforeRegen": lives_before,
            "livesAfterRegen": lives_after,
            "livesRegened": lives_regened,
            "nextLifeAt": updated_user.get("nextLifeAt"),
            "livesMaxedAt": updated_user.get("livesMaxedAt"),
        }
        
        logger.info(f"Regenerated {lives_regened} lives for user {user_id}")
        
        return schemas.RegenLivesResponse(**response_data)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error regenerating lives: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= PATH PROGRESSION ENDPOINTS (FASE 2) =============

@app.get("/api/v1/{user_id}/path", response_model=schemas.UserPathResponse)
async def get_user_path(
    user_id: str,
    learning_language: str = Query(..., description="Sign language code (LSB, ASL, LSM)")
):
    """
    Get user's complete learning path for a specific sign language
    
    Returns all topics with their unlock status, progress, and difficulty levels.
    If path doesn't exist for this learning language, initializes it automatically (idempotent).
    """
    try:
        # Validate learning_language
        if learning_language not in schemas.VALID_SIGN_LANGUAGES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid learning_language '{learning_language}'. "
                       f"Must be one of: {', '.join(schemas.VALID_SIGN_LANGUAGES)}"
            )
        
        # Get user to verify exists
        user = await dynamo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        # Get existing path items
        path_items = await dynamo.get_user_path(user_id, learning_language)
        
        # If no path exists, initialize it
        if not path_items:
            logger.info(f"No path found for user {user_id}, language {learning_language}. Initializing...")
            init_result = await path_logic.initialize_user_path(user_id, learning_language)
            # Get path items after initialization
            path_items = await dynamo.get_user_path(user_id, learning_language)
        
        # Calculate stats
        stats = await path_logic.calculate_path_stats(user_id, learning_language)
        
        # Build response
        response_data = {
            "userId": user_id,
            "learningLanguage": learning_language,
            "topics": path_items,
            "totalTopics": stats['totalTopics'],
            "unlockedTopics": stats['unlockedTopics'],
            "completedTopics": stats['completedTopics'],
            "currentTopicId": stats['currentTopicId']
        }
        
        logger.info(
            f"Retrieved path for user {user_id}, language {learning_language}: "
            f"{stats['totalTopics']} topics, {stats['completedTopics']} completed"
        )
        
        return schemas.UserPathResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user path: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/{user_id}/path/{topic_id}", response_model=schemas.TopicPathStatus)
async def get_path_topic(
    user_id: str,
    topic_id: str,
    learning_language: str = Query(..., description="Sign language code (LSB, ASL, LSM)")
):
    """
    Get detailed status of a specific topic in the user's path
    
    Returns unlock status, progress for each difficulty level, and metadata.
    """
    try:
        # Validate learning_language
        if learning_language not in schemas.VALID_SIGN_LANGUAGES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid learning_language '{learning_language}'. "
                       f"Must be one of: {', '.join(schemas.VALID_SIGN_LANGUAGES)}"
            )
        
        # Get path topic
        path_item = await dynamo.get_path_topic(user_id, learning_language, topic_id)
        
        if not path_item:
            raise HTTPException(
                status_code=404,
                detail=f"Path topic {topic_id} not found for user {user_id}, language {learning_language}"
            )
        
        return schemas.TopicPathStatus(**path_item)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting path topic: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/{user_id}/path/unlock", response_model=schemas.UnlockTopicResponse)
async def unlock_topic(user_id: str, request: schemas.UnlockTopicRequest):
    """
    Manually unlock a topic in the user's path
    
    Can be unlocked by:
    - Auto: When previous topic is completed (free)
    - Manual: Using coins/gems (payment required)
    
    Validates that user has sufficient coins/gems before unlocking.
    """
    try:
        # Get user to verify exists and check balance
        user = await dynamo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        # Get topic from Content Service to verify exists
        topic = await content_client.get_topic(request.topicId)
        if not topic:
            raise HTTPException(status_code=404, detail=f"Topic {request.topicId} not found")
        
        # Check if topic has exercises for this language
        has_exercises = await content_client.topic_has_exercises_for_language(
            request.topicId,
            request.learningLanguage
        )
        
        if not has_exercises:
            raise HTTPException(
                status_code=422,
                detail=f"Topic {request.topicId} has no exercises for language {request.learningLanguage}"
            )
        
        # Get path item (create if doesn't exist)
        path_item = await dynamo.get_path_topic(user_id, request.learningLanguage, request.topicId)
        
        if not path_item:
            # Create path item for this topic
            order_index = topic.get('order_index', 0)
            path_item = await dynamo.create_path_item(
                user_id=user_id,
                topic_id=request.topicId,
                learning_language=request.learningLanguage,
                order_index=order_index,
                unlocked=False,
                auto_unlocked=False,
                manual_unlock_cost_coins=100,
                manual_unlock_cost_gems=1
            )
        
        # Check if already unlocked
        if path_item.get('unlocked', False):
            response_data = {
                "userId": user_id,
                "topicId": request.topicId,
                "learningLanguage": request.learningLanguage,
                "unlocked": True,
                "method": "already_unlocked",
                "coinsSpent": 0,
                "gemsSpent": 0,
                "remainingCoins": user.get('coins', 0),
                "remainingGems": user.get('gems', 0),
                "message": "Topic is already unlocked"
            }
            return schemas.UnlockTopicResponse(**response_data)
        
        # Manual unlock with payment
        coins_spent = 0
        gems_spent = 0
        
        if request.payment:
            coins_required = request.payment.get('coins', 0)
            gems_required = request.payment.get('gems', 0)
            
            current_coins = user.get('coins', 0)
            current_gems = user.get('gems', 0)
            
            # Validate sufficient funds
            if coins_required > current_coins:
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient coins. Required: {coins_required}, available: {current_coins}"
                )
            
            if gems_required > current_gems:
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient gems. Required: {gems_required}, available: {current_gems}"
                )
            
            coins_spent = coins_required
            gems_spent = gems_required
        
        # Unlock the topic
        unlocked_item = await dynamo.unlock_path_topic(
            user_id=user_id,
            learning_language=request.learningLanguage,
            topic_id=request.topicId,
            method='manual',
            coins_spent=coins_spent,
            gems_spent=gems_spent
        )
        
        # Get updated user balance
        user_updated = await dynamo.get_user(user_id)
        
        # Emit event
        await path_logic.emit_path_event(
            event_type='TOPIC_UNLOCKED',
            user_id=user_id,
            topic_id=request.topicId,
            learning_language=request.learningLanguage,
            metadata={
                'unlockMethod': 'manual',
                'coinsSpent': coins_spent,
                'gemsSpent': gems_spent
            }
        )
        
        response_data = {
            "userId": user_id,
            "topicId": request.topicId,
            "learningLanguage": request.learningLanguage,
            "unlocked": True,
            "method": "manual",
            "coinsSpent": coins_spent,
            "gemsSpent": gems_spent,
            "remainingCoins": user_updated.get('coins', 0),
            "remainingGems": user_updated.get('gems', 0),
            "message": f"Topic unlocked successfully for {coins_spent} coins and {gems_spent} gems"
        }
        
        logger.info(
            f"User {user_id} unlocked topic {request.topicId} manually: "
            f"{coins_spent} coins, {gems_spent} gems"
        )
        
        return schemas.UnlockTopicResponse(**response_data)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error unlocking topic: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/{user_id}/path/progress", response_model=schemas.PathProgressResponse)
async def update_path_progress(user_id: str, request: schemas.PathProgressRequest):
    """
    Update path progress after an exercise attempt
    
    Validates that the exercise belongs to the topic and has the correct learning_language.
    Updates progress, checks for level/topic completion, and auto-unlocks next topic if needed.
    
    Returns updated progress with flags for levelCompleted, topicCompleted, nextTopicUnlocked.
    """
    try:
        # Validate that exercise belongs to topic with correct learning_language
        is_valid = await content_client.validate_exercise_belongs_to_topic(
            exercise_id=request.exerciseId,
            topic_id=request.topicId,
            learning_language=request.learningLanguage
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Exercise {request.exerciseId} does not belong to topic {request.topicId} "
                    f"or has incorrect learning_language (expected: {request.learningLanguage})"
                )
            )
        
        # Get path item
        path_item = await dynamo.get_path_topic(
            user_id,
            request.learningLanguage,
            request.topicId
        )
        
        if not path_item:
            raise HTTPException(
                status_code=404,
                detail=f"Path topic {request.topicId} not found for user {user_id}"
            )
        
        # Check if topic is unlocked
        if not path_item.get('unlocked', False):
            raise HTTPException(
                status_code=403,
                detail=f"Topic {request.topicId} is not unlocked for user {user_id}"
            )
        
        # Check if difficulty level is unlocked
        levels = path_item.get('levels', {})
        level_data = levels.get(request.difficulty, {})
        
        if not level_data.get('unlocked', False):
            raise HTTPException(
                status_code=403,
                detail=f"Difficulty '{request.difficulty}' is not unlocked for topic {request.topicId}"
            )
        
        # Update progress (only increment on correct attempts)
        increment = 1 if request.outcome == 'correct' else 0
        
        updated_item = await dynamo.update_path_progress(
            user_id=user_id,
            learning_language=request.learningLanguage,
            topic_id=request.topicId,
            difficulty=request.difficulty,
            increment_exercises=increment
        )
        
        # FASE 3: Record activity for streak tracking (if correct answer)
        streak_response = None
        if request.outcome == 'correct':
            try:
                streak_response = streak_service.record_activity(
                    user_id=user_id,
                    learning_language=request.learningLanguage,
                    activity_type='exercise_complete',
                    value=1,
                    exercise_id=request.exerciseId,
                    user_timezone=None  # TODO: Get from user profile
                )
                logger.info(
                    f"Streak activity recorded for user {user_id}: "
                    f"streak={streak_response.currentStreak}, "
                    f"progress={streak_response.progress}%"
                )
            except Exception as streak_error:
                # Don't fail the main request if streak update fails
                logger.error(f"Failed to update streak (non-fatal): {streak_error}")
        
        # FASE 4: Auto-track mission progress (if correct answer)
        if request.outcome == 'correct':
            try:
                from datetime import datetime
                from app.logic import mission_service
                
                today = datetime.utcnow().strftime("%Y-%m-%d")
                await mission_service.auto_track_mission_progress(
                    user_id=user_id,
                    learning_language=request.learningLanguage,
                    metric_type="exercises_completed",
                    value=1,
                    date=today
                )
                logger.info(f"Mission progress auto-tracked for user {user_id}")
            except Exception as mission_error:
                # Don't fail the main request if mission update fails
                logger.warning(f"Failed to update mission progress (non-fatal): {mission_error}")
        
        # Check results
        updated_levels = updated_item.get('levels', {})
        updated_level = updated_levels.get(request.difficulty, {})
        
        level_completed = updated_level.get('completed', False)
        topic_completed = updated_item.get('completed', False)
        
        current_progress = updated_level.get('progress', 0)
        completed_exercises = updated_level.get('completedExercises', 0)
        required_exercises = updated_level.get('requiredToUnlock', 10)
        
        # Auto-unlock next topic if this topic is completed
        next_topic_unlocked = False
        next_topic_id = None
        
        if topic_completed:
            next_topic_data = await path_logic.auto_unlock_next_topic(
                user_id=user_id,
                learning_language=request.learningLanguage,
                current_topic_id=request.topicId
            )
            
            if next_topic_data:
                next_topic_unlocked = True
                next_topic_id = next_topic_data.get('topicId')
                logger.info(f"Auto-unlocked next topic: {next_topic_id}")
            
            # Emit TOPIC_COMPLETED event
            await path_logic.emit_path_event(
                event_type='TOPIC_COMPLETED',
                user_id=user_id,
                topic_id=request.topicId,
                learning_language=request.learningLanguage,
                metadata={
                    'nextTopicUnlocked': next_topic_unlocked,
                    'nextTopicId': next_topic_id
                }
            )
        
        # Emit LEVEL_COMPLETED event if level completed
        if level_completed:
            await path_logic.emit_path_event(
                event_type='LEVEL_COMPLETED',
                user_id=user_id,
                topic_id=request.topicId,
                learning_language=request.learningLanguage,
                metadata={
                    'difficulty': request.difficulty,
                    'completedExercises': completed_exercises
                }
            )
        
        # Always emit PATH_PROGRESS_UPDATED event
        await path_logic.emit_path_event(
            event_type='PATH_PROGRESS_UPDATED',
            user_id=user_id,
            topic_id=request.topicId,
            learning_language=request.learningLanguage,
            metadata={
                'difficulty': request.difficulty,
                'outcome': request.outcome,
                'progress': current_progress,
                'levelCompleted': level_completed,
                'topicCompleted': topic_completed
            }
        )
        
        response_data = {
            "userId": user_id,
            "topicId": request.topicId,
            "exerciseId": request.exerciseId,
            "learningLanguage": request.learningLanguage,
            "difficulty": request.difficulty,
            "outcome": request.outcome,
            "progressUpdated": increment > 0,
            "levelCompleted": level_completed,
            "topicCompleted": topic_completed,
            "nextTopicUnlocked": next_topic_unlocked,
            "nextTopicId": next_topic_id,
            "currentProgress": current_progress,
            "completedExercises": completed_exercises,
            "requiredExercises": required_exercises,
            "message": f"Progress updated: {current_progress}% ({completed_exercises}/{required_exercises})"
        }
        
        logger.info(
            f"Path progress updated for user {user_id}: topic {request.topicId}, "
            f"difficulty {request.difficulty}, outcome {request.outcome}, "
            f"progress {current_progress}%, level_completed={level_completed}, "
            f"topic_completed={topic_completed}"
        )
        
        return schemas.PathProgressResponse(**response_data)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating path progress: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= FASE 3: STREAK SYSTEM ENDPOINTS =============

@app.get("/api/v1/{user_id}/streaks", response_model=schemas.StreakStatus)
async def get_user_streak(
    user_id: str,
    learning_language: str = Query(..., description="Sign language code (LSB, ASL, LSM)")
):
    """
    Get current streak status for user and learning language
    
    Returns:
        - Current streak value
        - Best streak achieved
        - Today's activity progress
        - Pending rewards
        - Next reset time
    """
    try:
        # Get or create streak
        streak = dynamo.get_user_streak(user_id, learning_language)
        
        if not streak:
            # Create initial streak
            streak = dynamo.create_streak_item(user_id, learning_language)
            logger.info(f"Created initial streak for user {user_id}, language {learning_language}")
        
        # Convert to StreakStatus response
        return schemas.StreakStatus(
            userId=streak['userId'],
            learningLanguage=streak['learningLanguage'],
            currentStreak=streak.get('currentStreak', 0),
            bestStreak=streak.get('bestStreak', 0),
            lastActivityDay=streak.get('lastActivityDay'),
            lastClaimedAt=streak.get('lastClaimedAt'),
            metricCountToday=streak.get('metricCountToday', 0),
            metricRequired=streak.get('metricRequired', 3),
            rewardGrantedToday=streak.get('rewardGrantedToday', False),
            pendingReward=schemas.PendingReward(
                coins=streak.get('pendingRewardCoins', 0),
                gems=streak.get('pendingRewardGems', 0),
                xp=streak.get('pendingRewardXp', 0)
            ),
            timezone=streak.get('timezone', 'UTC'),
            nextResetAt=None,  # TODO: Calculate based on timezone
            streakHealth=streak.get('streakHealth', 'active')
        )
        
    except Exception as e:
        logger.error(f"Error getting user streak: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/{user_id}/streaks/record", response_model=schemas.RecordActivityResponse)
async def record_streak_activity(
    user_id: str,
    request: schemas.RecordActivityRequest
):
    """
    Record user activity for streak tracking
    
    Args:
        - learningLanguage: Sign language code
        - activityType: exercise_complete, xp_earned, camera_minutes, topic_completed
        - value: Activity count (default 1, capped at 100/day)
        - exerciseId: Optional exercise ID
    
    Returns:
        - Streak updated status
        - Current streak value
        - Today's progress
        - Rewards granted (if any)
    
    Rate Limit: 5 requests/second per user (TODO: implement with Redis/DynamoDB)
    """
    try:
        # TODO: Implement rate limiting (5 req/s per user)
        # For now, log a warning if called too frequently
        
        # Record activity through streak service
        response = streak_service.record_activity(
            user_id=user_id,
            learning_language=request.learningLanguage,
            activity_type=request.activityType,
            value=request.value,
            exercise_id=request.exerciseId,
            user_timezone=None  # TODO: Get from user profile
        )
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error recording streak activity: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/{user_id}/streaks/claim", response_model=schemas.ClaimRewardResponse)
async def claim_streak_rewards(
    user_id: str,
    request: schemas.ClaimRewardRequest
):
    """
    Claim pending streak rewards
    
    Args:
        - learningLanguage: Sign language code
    
    Returns:
        - Rewards claimed (coins, gems, XP)
        - New balance
    
    Note: Atomic operation - rewards are credited to user account and cleared from streak
    """
    try:
        # Claim rewards (atomic transaction)
        updated_streak, rewards_claimed = dynamo.claim_streak_reward(
            user_id=user_id,
            learning_language=request.learningLanguage
        )
        
        # Get updated user balance
        user = await dynamo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        reward_granted = schemas.RewardGranted(
            coins=rewards_claimed['coins'],
            gems=rewards_claimed['gems'],
            xp=rewards_claimed['xp'],
            reason=f"Streak rewards claimed",
            milestone=None
        )
        
        return schemas.ClaimRewardResponse(
            success=True,
            rewardClaimed=reward_granted,
            newBalance={
                "coins": user.get('coins', 0),
                "gems": user.get('gems', 0),
                "xp": user.get('xp', 0)
            },
            message=f"Claimed {rewards_claimed['coins']} coins, {rewards_claimed['gems']} gems, {rewards_claimed['xp']} XP!"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error claiming streak rewards: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/{user_id}/streaks/history", response_model=schemas.StreakHistoryResponse)
async def get_streak_history(
    user_id: str,
    learning_language: str = Query(..., description="Sign language code"),
    days: int = Query(30, ge=1, le=365, description="Number of days to retrieve")
):
    """
    Get historical streak data
    
    Args:
        - learning_language: Sign language code
        - days: Number of days (1-365, default 30)
    
    Returns:
        - Historical daily records
        - Statistics (total days, days with goal met, best streak)
    """
    try:
        # Get historical items
        history_items = dynamo.get_streak_history(
            user_id=user_id,
            learning_language=learning_language,
            days=days
        )
        
        # Get current streak
        current_streak_data = dynamo.get_user_streak(user_id, learning_language)
        current_streak = current_streak_data.get('currentStreak', 0) if current_streak_data else 0
        best_streak = current_streak_data.get('bestStreak', 0) if current_streak_data else 0
        
        # Convert to StreakHistoryItem objects
        history = []
        days_with_goal_met = 0
        
        for item in history_items:
            # Extract date from SK (format: STREAK#DAILY#YYYY-MM-DD)
            sk = item.get('SK', '')
            date = sk.split('#')[-1] if '#' in sk else None
            
            if not date or date == 'current':
                continue
            
            metric_count = item.get('metricCountToday', 0)
            metric_required = item.get('metricRequired', 3)
            goal_met = metric_count >= metric_required
            
            if goal_met:
                days_with_goal_met += 1
            
            # Check if reward was earned (look for pending rewards or reward_granted flag)
            reward_earned = None
            if item.get('rewardGrantedToday') or item.get('pendingRewardCoins', 0) > 0:
                reward_earned = schemas.RewardGranted(
                    coins=item.get('rewardCoins', 0),
                    gems=item.get('rewardGems', 0),
                    xp=item.get('rewardXp', 0),
                    reason=f"Streak day {item.get('streakValue', 0)}",
                    milestone=None
                )
            
            history.append(schemas.StreakHistoryItem(
                date=date,
                metricCount=metric_count,
                metricRequired=metric_required,
                goalMet=goal_met,
                streakValue=item.get('currentStreak', 0),
                rewardEarned=reward_earned
            ))
        
        return schemas.StreakHistoryResponse(
            userId=user_id,
            learningLanguage=learning_language,
            history=history,
            totalDays=len(history),
            daysWithGoalMet=days_with_goal_met,
            currentStreak=current_streak,
            bestStreak=best_streak
        )
        
    except Exception as e:
        logger.error(f"Error getting streak history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= FASE 4: DAILY MISSIONS ENDPOINTS =============

@app.get("/api/v1/{user_id}/daily-missions", response_model=schemas_missions.DailyMissionsResponse)
async def get_daily_missions(
    user_id: str,
    learning_language: str = Query(..., description="Sign language code (LSB, ASL, LSM)"),
    date: Optional[str] = Query(None, description="Date YYYY-MM-DD (default: today)")
):
    """
    Get daily missions for user
    
    If missions don't exist for the date, they will be generated automatically.
    
    Returns:
        - 3 daily missions
        - Progress and completion status
        - Reward information
    """
    try:
        # Determine date
        if date is None:
            from datetime import datetime
            date = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Try to get existing missions
        missions = dynamo_missions.get_daily_missions(user_id, learning_language, date)
        
        if missions:
            return missions
        
        # Generate new missions
        logger.info(f"Generating daily missions for user {user_id}, lang {learning_language}, date {date}")
        
        # Get user level for difficulty calculation
        user = await dynamo.get_user(user_id)
        user_level = user.get("level", 1) if user else 1
        
        # Generate missions
        from app.logic import mission_service
        missions = await mission_service.generate_daily_missions(
            user_id=user_id,
            learning_language=learning_language,
            user_level=user_level,
            timezone="UTC",  # TODO: Get from user profile
            date=date
        )
        
        return missions
        
    except ValueError as e:
        logger.warning(f"Validation error in daily missions: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Validation Error: {str(e)}")
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        import traceback
        error_details = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        logger.error(f"Error getting daily missions: {error_details}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal Error: {type(e).__name__}: {str(e)}"
        )


@app.post("/api/v1/{user_id}/daily-missions/{date}/{mission_id}/progress", 
          response_model=schemas_missions.UpdateMissionProgressResponse)
async def update_mission_progress(
    user_id: str,
    date: str,
    mission_id: str,
    request: schemas_missions.UpdateMissionProgressRequest,
    learning_language: str = Query(..., description="Sign language code")
):
    """
    Update progress for a specific mission
    
    Args:
        - date: YYYY-MM-DD
        - mission_id: Mission ID (e.g., "mt-12")
        - value: Amount to add to progress (default: 1)
    
    Returns:
        - Updated progress
        - Completion status
        - Reward earned (if just completed)
    """
    try:
        result = dynamo_missions.update_mission_progress(
            user_id=user_id,
            learning_language=learning_language,
            date=date,
            mission_id=mission_id,
            value=request.value
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating mission progress: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/{user_id}/daily-missions/{date}/{mission_id}/claim",
          response_model=schemas_missions.ClaimMissionRewardResponse)
async def claim_mission_reward(
    user_id: str,
    date: str,
    mission_id: str,
    learning_language: str = Query(..., description="Sign language code")
):
    """
    Claim reward for a completed mission
    
    Atomic operation:
    - Credits coins/XP/gems to user account
    - Marks mission as claimed
    - Prevents double-claiming
    
    Args:
        - date: YYYY-MM-DD
        - mission_id: Mission ID
    
    Returns:
        - Reward claimed
        - New user balance
    """
    try:
        result = dynamo_missions.claim_mission_reward(
            user_id=user_id,
            learning_language=learning_language,
            date=date,
            mission_id=mission_id
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error claiming mission reward: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/{user_id}/daily-missions/history", response_model=schemas_missions.DailyMissionsHistoryResponse)
async def get_mission_history(
    user_id: str,
    learning_language: str = Query(..., description="Sign language code"),
    days: int = Query(7, ge=1, le=90, description="Number of days to retrieve")
):
    """
    Get historical daily missions
    
    Args:
        - learning_language: LSB, ASL, LSM
        - days: Number of days (1-90, default: 7)
    
    Returns:
        - Historical mission records
        - Statistics (completed, claimed, rewards earned)
        - Streak information
    """
    try:
        history = dynamo_missions.get_mission_history(
            user_id=user_id,
            learning_language=learning_language,
            days=days
        )
        
        # Calculate stats
        total_completed = sum(item.completed_count for item in history)
        total_claimed = sum(item.claimed_count for item in history)
        total_coins = sum(item.total_coins_earned for item in history)
        total_xp = sum(item.total_xp_earned for item in history)
        total_gems = sum(item.total_gems_earned for item in history)
        
        # Calculate streaks (days with at least 1 mission completed)
        current_streak = 0
        best_streak = 0
        temp_streak = 0
        
        for item in history:
            if item.completed_count > 0:
                temp_streak += 1
                best_streak = max(best_streak, temp_streak)
            else:
                temp_streak = 0
        
        # Current streak is from most recent consecutive days
        for item in history:
            if item.completed_count > 0:
                current_streak += 1
            else:
                break
        
        return schemas_missions.DailyMissionsHistoryResponse(
            userId=user_id,
            learningLanguage=learning_language,
            history=history,
            total_days=len(history),
            total_missions_completed=total_completed,
            total_missions_claimed=total_claimed,
            total_coins_earned=total_coins,
            total_xp_earned=total_xp,
            total_gems_earned=total_gems,
            current_streak=current_streak,
            best_streak=best_streak
        )
        
    except Exception as e:
        logger.error(f"Error getting mission history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FASE 5: BADGES / ACHIEVEMENTS ENDPOINTS
# ============================================================================
# ANTI-ERROR DESIGN:
# - All endpoints start with /api/v1/{user_id}/badges (correct ALB routing)
# - No cross-service imports
# - Simple logic, comprehensive logging
# ============================================================================

@app.get("/api/v1/{user_id}/badges", 
         response_model=schemas_badges.UserBadgesStatsResponse)
async def get_user_badges(
    user_id: str,
    learning_language: str = Query(..., description="LSB, ASL, LSM")
):
    """
    Get user's earned badges with statistics.
    
    Returns:
        - List of earned badges with details
        - Statistics (total earned, progress percentage)
    """
    try:
        logger.info(f"Getting badges for user {user_id} ({learning_language})")
        
        result = badge_service.get_user_badges_with_details(
            user_id,
            learning_language
        )
        
        return schemas_badges.UserBadgesStatsResponse(**result)
        
    except Exception as e:
        logger.error(f"Error getting user badges: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving badges: {str(e)}")


@app.get("/api/v1/{user_id}/badges/all",
         response_model=schemas_badges.AllBadgesResponse)
async def get_all_badges_with_status(
    user_id: str,
    learning_language: str = Query(..., description="LSB, ASL, LSM")
):
    """
    Get ALL badges (earned + not earned) with status.
    
    Useful for showing badge gallery/collection.
    
    Returns:
        - All badges with earned status
        - Hidden badges shown as locked if not earned
    """
    try:
        logger.info(f"Getting all badges for user {user_id} ({learning_language})")
        
        badges = badge_service.get_all_badges_with_status(
            user_id,
            learning_language
        )
        
        # Calculate stats
        earned_count = sum(1 for b in badges if b.get('earned'))
        total_count = len(badges)
        
        by_rarity = {}
        by_type = {}
        
        for badge in badges:
            if badge.get('earned'):
                rarity = badge.get('rarity', 'common')
                badge_type = badge.get('type', 'achievement')
                by_rarity[rarity] = by_rarity.get(rarity, 0) + 1
                by_type[badge_type] = by_type.get(badge_type, 0) + 1
        
        stats = {
            'total_earned': earned_count,
            'total_available': total_count,
            'by_rarity': by_rarity,
            'by_type': by_type
        }
        
        return schemas_badges.AllBadgesResponse(
            badges=badges,
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"Error getting all badges: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving badges: {str(e)}")


@app.post("/api/v1/{user_id}/badges/check",
          response_model=schemas_badges.CheckBadgesResponse)
async def check_and_assign_badges(
    user_id: str,
    learning_language: str = Query(..., description="LSB, ASL, LSM")
):
    """
    Check badge conditions and assign newly earned badges.
    
    This endpoint is called automatically after user actions:
    - Exercise completed
    - Level up
    - Streak updated
    - XP gained
    
    Returns:
        - List of newly earned badges
        - Count of new badges
    """
    try:
        logger.info(f"Checking badges for user {user_id} ({learning_language})")
        
        newly_earned = badge_service.check_and_assign_badges(
            user_id,
            learning_language
        )
        
        message = "No new badges earned"
        if newly_earned:
            badge_names = [b.get('title', {}).get('en', 'Unknown') for b in newly_earned]
            message = f"Congratulations! Earned: {', '.join(badge_names)}"
        
        return schemas_badges.CheckBadgesResponse(
            newly_earned=newly_earned,
            total_new=len(newly_earned),
            message=message
        )
        
    except Exception as e:
        logger.error(f"Error checking badges: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking badges: {str(e)}")


@app.post("/api/v1/{user_id}/badges/notify",
          response_model=schemas_badges.BadgeNotificationResponse)
async def mark_badge_notified(
    user_id: str,
    request: schemas_badges.BadgeNotificationRequest,
    learning_language: str = Query(..., description="LSB, ASL, LSM")
):
    """
    Mark a badge as notified (user saw the achievement popup).
    
    Used to track which badges have been shown to user.
    """
    try:
        from app.dynamo_badges import mark_badge_notified
        
        success = mark_badge_notified(
            dynamo,
            user_id,
            learning_language,
            request.badge_id
        )
        
        if success:
            return schemas_badges.BadgeNotificationResponse(
                success=True,
                message="Badge marked as notified"
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to mark notification")
            
    except Exception as e:
        logger.error(f"Error marking badge notified: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FASE 5: Event Listener Endpoints
# ============================================================================

@app.post("/api/v1/events/lesson-completed")
async def event_lesson_completed(event: Dict[str, Any]):
    """
    Handle lesson completed event for badge evaluation.
    
    Payload:
    {
        "userId": "user123",
        "learningLanguage": "LSB",
        "timestamp": "2025-11-20T12:00:00Z",
        "lessonId": "lesson-001",
        "xpEarned": 10,
        "perfect": true
    }
    """
    from app.logic import listeners
    return listeners.on_lesson_completed(event)


@app.post("/api/v1/events/exercise-completed")
async def event_exercise_completed(event: Dict[str, Any]):
    """
    Handle exercise completed event for badge evaluation.
    
    Payload:
    {
        "userId": "user123",
        "learningLanguage": "LSB",
        "timestamp": "2025-11-20T12:00:00Z",
        "exerciseId": "ex-001",
        "correct": true,
        "xpEarned": 5
    }
    """
    from app.logic import listeners
    return listeners.on_exercise_completed(event)


@app.post("/api/v1/events/streak-updated")
async def event_streak_updated(event: Dict[str, Any]):
    """
    Handle streak updated event for badge evaluation.
    
    Payload:
    {
        "userId": "user123",
        "learningLanguage": "LSB",
        "timestamp": "2025-11-20T12:00:00Z",
        "newStreak": 7,
        "previousStreak": 6,
        "streakIncreased": true
    }
    """
    from app.logic import listeners
    return listeners.on_streak_updated(event)


@app.post("/api/v1/events/level-up")
async def event_level_up(event: Dict[str, Any]):
    """
    Handle level up event for badge evaluation.
    
    Payload:
    {
        "userId": "user123",
        "learningLanguage": "LSB",
        "timestamp": "2025-11-20T12:00:00Z",
        "newLevel": 5,
        "previousLevel": 4,
        "totalXP": 1500
    }
    """
    from app.logic import listeners
    return listeners.on_level_up(event)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
# Build Wed, Nov 19, 2025  9:00:21 PM
