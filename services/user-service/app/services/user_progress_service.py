"""
FASE 9: User Topic Progress Service

Business logic for topic progress tracking and synchronization.

ANTI-ERROR DESIGN (Lecciones FASE 8):
- Methods that need I/O (HTTP, DB) are async
- Pure calculation methods are sync
- Explicit error handling with logging
- No assumptions about external service availability
"""
import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

from app import dynamo
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class UserProgressService:
    """
    Service for managing user topic progress.
    
    Responsibilities:
    - Track exercises completed per topic
    - Calculate mastery_score
    - Estimate difficulty_level
    - Sync with Content Service for total_exercises_available
    - Provide recommendations
    """
    
    def __init__(self):
        self.content_service_url = settings.CONTENT_SERVICE_URL
        logger.info(f"UserProgressService initialized with Content Service URL: {self.content_service_url}")
    
    # ========== SYNC WITH CONTENT SERVICE ==========
    
    async def sync_topic_total_exercises(
        self,
        user_id: str,
        learning_language: str,
        topic_id: str
    ) -> Dict[str, Any]:
        """
        Sync total_exercises_available from Content Service.
        
        Calls: GET /content/api/v1/topics/{topic_id}/stats
        
        Args:
            user_id: User identifier
            learning_language: Sign language
            topic_id: Topic ID
        
        Returns:
            {
                "total_exercises_before": int,
                "total_exercises_after": int,
                "sync_successful": bool,
                "message": str
            }
        
        ANTI-ERROR: Handles network errors, timeouts, 404s gracefully
        """
        try:
            # Get current progress
            progress = await dynamo.get_topic_progress(user_id, learning_language, topic_id)
            
            if not progress:
                # Create initial progress entry
                logger.info(f"Creating initial progress for user {user_id}, topic {topic_id}")
                progress = await dynamo.create_topic_progress(
                    user_id=user_id,
                    learning_language=learning_language,
                    topic_id=topic_id,
                    total_exercises_available=0
                )
            
            total_before = progress.get('total_exercises_available', 0)
            
            # Call Content Service
            url = f"{self.content_service_url}/api/v1/topics/{topic_id}/stats"
            
            logger.info(f"Syncing topic {topic_id} from Content Service: {url}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                
                if response.status_code == 404:
                    logger.warning(f"Topic {topic_id} not found in Content Service")
                    return {
                        "total_exercises_before": total_before,
                        "total_exercises_after": total_before,
                        "sync_successful": False,
                        "message": f"Topic {topic_id} not found in Content Service"
                    }
                
                response.raise_for_status()
                stats = response.json()
            
            total_after = stats.get('total_exercises', 0)
            
            # Update in DynamoDB if changed
            if total_after != total_before:
                await dynamo.update_topic_progress(
                    user_id=user_id,
                    learning_language=learning_language,
                    topic_id=topic_id,
                    total_exercises_available=total_after
                )
                logger.info(
                    f"Updated total_exercises for user {user_id}, topic {topic_id}: "
                    f"{total_before} → {total_after}"
                )
            
            return {
                "total_exercises_before": total_before,
                "total_exercises_after": total_after,
                "sync_successful": True,
                "message": f"Synced successfully: {total_after} exercises available"
            }
            
        except httpx.RequestError as e:
            logger.error(f"Network error syncing topic {topic_id}: {str(e)}")
            return {
                "total_exercises_before": progress.get('total_exercises_available', 0) if progress else 0,
                "total_exercises_after": progress.get('total_exercises_available', 0) if progress else 0,
                "sync_successful": False,
                "message": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error syncing topic {topic_id}: {str(e)}")
            return {
                "total_exercises_before": progress.get('total_exercises_available', 0) if progress else 0,
                "total_exercises_after": progress.get('total_exercises_available', 0) if progress else 0,
                "sync_successful": False,
                "message": f"Sync error: {str(e)}"
            }
    
    # ========== PROGRESS TRACKING ==========
    
    async def record_exercise_completion(
        self,
        user_id: str,
        learning_language: str,
        topic_id: str,
        exercise_id: str,
        result: str
    ) -> Dict[str, Any]:
        """
        Record an exercise completion and update topic progress.
        
        FASE 9: Called when exercise.completed event is received.
        
        Args:
            user_id: User identifier
            learning_language: Sign language
            topic_id: Topic ID
            exercise_id: Exercise ID
            result: "success" or "fail"
        
        Returns:
            Updated progress data with flags:
            {
                "progress_updated": bool,
                "exercises_completed": int,
                "mastery_score": float,
                "difficulty_level_estimated": str,
                "level_changed": bool,
                "previous_level": str,
                "current_level": str
            }
        
        ANTI-ERROR: Only increments on success, handles missing progress
        """
        try:
            # Get or create progress
            progress = await dynamo.get_topic_progress(user_id, learning_language, topic_id)
            
            if not progress:
                # Sync to create initial progress
                sync_result = await self.sync_topic_total_exercises(
                    user_id, learning_language, topic_id
                )
                progress = await dynamo.get_topic_progress(user_id, learning_language, topic_id)
            
            previous_level = progress.get('difficulty_level_estimated', 'beginner')
            
            # Only increment on success
            if result == 'success':
                await dynamo.increment_topic_exercises_completed(
                    user_id, learning_language, topic_id, increment=1
                )
                logger.info(f"Incremented exercises_completed for user {user_id}, topic {topic_id}")
            
            # Recalculate mastery and difficulty level
            updated_progress = await dynamo.calculate_and_update_mastery(
                user_id, learning_language, topic_id
            )
            
            current_level = updated_progress.get('difficulty_level_estimated', 'beginner')
            level_changed = current_level != previous_level
            
            return {
                "progress_updated": result == 'success',
                "exercises_completed": updated_progress.get('exercises_completed', 0),
                "mastery_score": float(updated_progress.get('mastery_score', 0.0)),
                "difficulty_level_estimated": current_level,
                "level_changed": level_changed,
                "previous_level": previous_level,
                "current_level": current_level
            }
            
        except Exception as e:
            logger.error(f"Error recording exercise completion: {str(e)}")
            raise
    
    # ========== RECOMMENDATIONS ==========
    
    def get_next_recommendation(
        self,
        mastery_score: float,
        difficulty_level_estimated: str,
        exercises_completed: int,
        total_exercises_available: int
    ) -> Dict[str, Any]:
        """
        Generate recommendation for next step.
        
        Pure calculation method (sync, no I/O).
        
        Args:
            mastery_score: Current mastery score (0.0-1.0)
            difficulty_level_estimated: Current difficulty level
            exercises_completed: Exercises completed count
            total_exercises_available: Total exercises available
        
        Returns:
            {
                "type": str ("continue"|"advance"|"reinforce"|"complete"),
                "message": str,
                "suggested_difficulty": str (optional)
            }
        
        ANTI-ERROR: Pure calculation, no async, no DB, no HTTP
        """
        # Complete topic (mastery >= 1.0 or all exercises done)
        if mastery_score >= 1.0 or exercises_completed >= total_exercises_available:
            return {
                "type": "complete",
                "message": "Topic mastered! Consider moving to the next topic.",
                "suggested_difficulty": "advanced"
            }
        
        # Need reinforcement (mastery < 0.33)
        if mastery_score < 0.33:
            return {
                "type": "reinforce",
                "message": "Practice more exercises to build foundational knowledge.",
                "suggested_difficulty": "beginner"
            }
        
        # Ready to advance (mastery >= 0.66)
        if mastery_score >= 0.66:
            return {
                "type": "advance",
                "message": "Great progress! Try more challenging exercises.",
                "suggested_difficulty": "advanced"
            }
        
        # Continue (0.33 <= mastery < 0.66)
        return {
            "type": "continue",
            "message": "Keep practicing to improve mastery.",
            "suggested_difficulty": "intermediate"
        }
    
    # ========== GET PROGRESS WITH ENRICHMENT ==========
    
    async def get_topic_progress_with_recommendation(
        self,
        user_id: str,
        learning_language: str,
        topic_id: str,
        sync_total: bool = True
    ) -> Dict[str, Any]:
        """
        Get topic progress with recommendation.
        
        Optionally syncs total_exercises_available before returning.
        
        Args:
            user_id: User identifier
            learning_language: Sign language
            topic_id: Topic ID
            sync_total: Whether to sync total from Content Service (default True)
        
        Returns:
            Progress data with next_recommendation field
        
        ANTI-ERROR: Handles missing progress, sync failures gracefully
        """
        try:
            # Sync total if requested
            if sync_total:
                await self.sync_topic_total_exercises(user_id, learning_language, topic_id)
            
            # Get progress
            progress = await dynamo.get_topic_progress(user_id, learning_language, topic_id)
            
            if not progress:
                # Create initial progress
                sync_result = await self.sync_topic_total_exercises(
                    user_id, learning_language, topic_id
                )
                progress = await dynamo.get_topic_progress(user_id, learning_language, topic_id)
            
            # Generate recommendation
            recommendation = self.get_next_recommendation(
                mastery_score=float(progress.get('mastery_score', 0.0)),
                difficulty_level_estimated=progress.get('difficulty_level_estimated', 'beginner'),
                exercises_completed=progress.get('exercises_completed', 0),
                total_exercises_available=progress.get('total_exercises_available', 0)
            )
            
            # Add recommendation to response
            progress['next_recommendation'] = recommendation
            
            return progress
            
        except Exception as e:
            logger.error(f"Error getting topic progress: {str(e)}")
            raise


# Global instance
user_progress_service = UserProgressService()
