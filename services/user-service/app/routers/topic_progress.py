"""
FASE 9: Topic Progress Router

Endpoints for user topic progress tracking and synchronization.

ANTI-ERROR DESIGN (Lecciones FASE 8):
- Unique prefix to avoid route collisions (Error #4)
- All async methods properly awaited (Error #3)
- Comprehensive logging
- Error handling for external service failures
"""
from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional
import logging

from app import schemas_topic_progress, dynamo
from app.services.user_progress_service import user_progress_service

logger = logging.getLogger(__name__)

# ANTI-ERROR #4: Unique prefix to avoid collisions with existing routes
router = APIRouter(
    prefix="/api/v1",
    tags=["Topic Progress - FASE 9"]
)


@router.get("/users/{user_id}/progress/{topic_id}", response_model=schemas_topic_progress.TopicProgressResponse)
async def get_user_topic_progress(
    user_id: str,
    topic_id: str,
    learning_language: str = Query(..., description="Sign language code (LSB, ASL, LSM)"),
    sync_total: bool = Query(True, description="Sync total exercises from Content Service")
):
    """
    Get user's progress for a specific topic.
    
    FASE 9: Returns mastery_score, exercises_completed, difficulty_level_estimated,
    and next_recommendation.
    
    Args:
        user_id: User identifier
        topic_id: Topic ID
        learning_language: Sign language (LSB, ASL, LSM)
        sync_total: Whether to sync total_exercises_available from Content Service (default: true)
    
    Returns:
        TopicProgressResponse with:
        - exercises_completed
        - total_exercises_available
        - mastery_score (0.0-1.0)
        - difficulty_level_estimated (beginner|intermediate|advanced)
        - next_recommendation (type, message, suggested_difficulty)
    
    ANTI-ERROR:
    - Handles missing progress (creates initial entry)
    - Handles Content Service unavailability gracefully
    - Logs all operations for debugging
    """
    try:
        logger.info(
            f"Getting topic progress: user={user_id}, topic={topic_id}, "
            f"lang={learning_language}, sync={sync_total}"
        )
        
        # Validate learning_language
        from app.schemas import VALID_SIGN_LANGUAGES
        if learning_language not in VALID_SIGN_LANGUAGES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid learning_language '{learning_language}'. "
                       f"Must be one of: {', '.join(VALID_SIGN_LANGUAGES)}"
            )
        
        # Get progress with recommendation
        # ANTI-ERROR #3: Properly await async method
        progress = await user_progress_service.get_topic_progress_with_recommendation(
            user_id=user_id,
            learning_language=learning_language,
            topic_id=topic_id,
            sync_total=sync_total
        )
        
        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topic progress not found for user {user_id}, topic {topic_id}"
            )
        
        # Build response
        response_data = {
            "user_id": progress['user_id'],
            "learning_language": progress['learning_language'],
            "topic_id": progress['topic_id'],
            "total_exercises_available": progress['total_exercises_available'],
            "exercises_completed": progress['exercises_completed'],
            "mastery_score": float(progress['mastery_score']),
            "difficulty_level_estimated": progress['difficulty_level_estimated'],
            "last_update_timestamp": progress['last_update_timestamp'],
            "created_at": progress['created_at'],
            "next_recommendation": progress.get('next_recommendation')
        }
        
        logger.info(
            f"Retrieved topic progress: user={user_id}, topic={topic_id}, "
            f"mastery={response_data['mastery_score']:.2f}, "
            f"completed={response_data['exercises_completed']}/{response_data['total_exercises_available']}"
        )
        
        return schemas_topic_progress.TopicProgressResponse(**response_data)
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting topic progress: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving topic progress: {str(e)}"
        )


@router.post("/users/{user_id}/progress/{topic_id}/sync", response_model=schemas_topic_progress.SyncTopicProgressResponse)
async def sync_topic_progress(
    user_id: str,
    topic_id: str,
    learning_language: str = Query(..., description="Sign language code (LSB, ASL, LSM)")
):
    """
    Manually sync total_exercises_available from Content Service.
    
    FASE 9: Forces synchronization of exercise count for a topic.
    
    Useful for:
    - Manual refresh when exercises are added/removed in Content Service
    - Debugging sync issues
    - Cron jobs
    
    Args:
        user_id: User identifier
        topic_id: Topic ID
        learning_language: Sign language
    
    Returns:
        Sync result with before/after counts and success status
    
    ANTI-ERROR:
    - Handles Content Service downtime gracefully
    - Returns meaningful error messages
    - Logs sync attempts
    """
    try:
        logger.info(f"Manual sync requested: user={user_id}, topic={topic_id}, lang={learning_language}")
        
        # Validate learning_language
        from app.schemas import VALID_SIGN_LANGUAGES
        if learning_language not in VALID_SIGN_LANGUAGES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid learning_language '{learning_language}'. "
                       f"Must be one of: {', '.join(VALID_SIGN_LANGUAGES)}"
            )
        
        # Perform sync
        # ANTI-ERROR #3: Properly await async method
        sync_result = await user_progress_service.sync_topic_total_exercises(
            user_id=user_id,
            learning_language=learning_language,
            topic_id=topic_id
        )
        
        response_data = {
            "user_id": user_id,
            "learning_language": learning_language,
            "topic_id": topic_id,
            "total_exercises_before": sync_result['total_exercises_before'],
            "total_exercises_after": sync_result['total_exercises_after'],
            "sync_successful": sync_result['sync_successful'],
            "message": sync_result['message']
        }
        
        logger.info(
            f"Sync completed: topic={topic_id}, "
            f"before={sync_result['total_exercises_before']}, "
            f"after={sync_result['total_exercises_after']}, "
            f"success={sync_result['sync_successful']}"
        )
        
        return schemas_topic_progress.SyncTopicProgressResponse(**response_data)
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error syncing topic progress: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing topic progress: {str(e)}"
        )


@router.post("/internal/exercise-completed", status_code=status.HTTP_202_ACCEPTED)
async def handle_exercise_completed_event(
    event_data: schemas_topic_progress.UpdateTopicProgressRequest
):
    """
    Internal endpoint to handle exercise.completed events.
    
    FASE 9: Placeholder for event-driven architecture.
    
    In production, this would be called by:
    - SNS subscription
    - EventBridge rule
    - SQS queue consumer
    
    Args:
        event_data: Exercise completion event
        {
            "exercise_id": str,
            "result": "success"|"fail",
            "timestamp": str (ISO 8601)
        }
    
    Returns:
        202 Accepted (event queued for processing)
    
    NOTE: This is a placeholder. Full implementation requires:
    - Exercise-to-topic mapping (query Content Service)
    - Async event processing (SQS/SNS)
    - Idempotency (deduplication)
    - Retry logic
    """
    try:
        logger.info(
            f"Received exercise.completed event: "
            f"exercise={event_data.exercise_id}, "
            f"result={event_data.result}"
        )
        
        # TODO FASE 9: Implement full event processing
        # 1. Query Content Service to get topic_id for exercise_id
        # 2. Extract user_id and learning_language from event
        # 3. Call user_progress_service.record_exercise_completion()
        # 4. Publish topic_progress_updated event
        
        logger.warning("exercise.completed event processing not yet implemented (placeholder)")
        
        return {
            "status": "accepted",
            "message": "Event queued for processing (placeholder - not yet implemented)",
            "event": {
                "exercise_id": event_data.exercise_id,
                "result": event_data.result,
                "timestamp": event_data.timestamp
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing exercise.completed event: {str(e)}")
        # Return 202 anyway to prevent SNS/EventBridge retries
        return {
            "status": "error",
            "message": f"Event processing failed: {str(e)}",
            "retry": False
        }
