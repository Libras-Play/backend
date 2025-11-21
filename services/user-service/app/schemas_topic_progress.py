"""
FASE 9: Topic Progress Schemas

Pydantic schemas for user topic progress tracking.

ANTI-ERROR DESIGN:
- All schemas use Pydantic v2 syntax with ConfigDict
- No protected namespaces (model_*)
- Clear validation rules
"""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime


class TopicProgressResponse(BaseModel):
    """
    User's progress for a specific topic.
    
    Returned by GET /users/{user_id}/progress/{topic_id}
    """
    user_id: str = Field(..., description="User identifier")
    learning_language: str = Field(..., description="Sign language (LSB, ASL, LSM)")
    topic_id: str = Field(..., description="Topic ID")
    total_exercises_available: int = Field(..., ge=0, description="Total exercises in topic")
    exercises_completed: int = Field(..., ge=0, description="Exercises completed by user")
    mastery_score: float = Field(..., ge=0.0, le=1.0, description="Mastery score (0.0-1.0)")
    difficulty_level_estimated: str = Field(
        ..., 
        description="Estimated difficulty level (beginner|intermediate|advanced)"
    )
    last_update_timestamp: str = Field(..., description="Last update timestamp (ISO 8601)")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    
    # Optional: Recommendations for next steps
    next_recommendation: Optional[Dict[str, Any]] = Field(
        None,
        description="Recommended next action based on progress"
    )
    
    @field_validator('difficulty_level_estimated')
    @classmethod
    def validate_difficulty_level(cls, v: str) -> str:
        """Validate difficulty level"""
        if v not in ['beginner', 'intermediate', 'advanced']:
            raise ValueError(
                f"Invalid difficulty_level_estimated '{v}'. "
                f"Must be: beginner, intermediate, or advanced"
            )
        return v
    
    model_config = ConfigDict(from_attributes=True)


class UpdateTopicProgressRequest(BaseModel):
    """
    Request to update topic progress after exercise completion.
    
    INTERNAL USE: Called by User Service after exercise.completed event.
    """
    exercise_id: str = Field(..., description="Exercise ID that was completed")
    result: str = Field(..., description="Result: success or fail")
    timestamp: str = Field(..., description="Completion timestamp (ISO 8601)")
    
    @field_validator('result')
    @classmethod
    def validate_result(cls, v: str) -> str:
        """Validate result"""
        if v not in ['success', 'fail']:
            raise ValueError(f"Invalid result '{v}'. Must be: success or fail")
        return v
    
    model_config = ConfigDict(from_attributes=True)


class SyncTopicProgressRequest(BaseModel):
    """
    Request to sync topic progress with Content Service.
    
    INTERNAL USE: Called periodically to update total_exercises_available.
    """
    topic_id: str = Field(..., description="Topic ID to sync")
    force: bool = Field(False, description="Force sync even if recently synced")
    
    model_config = ConfigDict(from_attributes=True)


class SyncTopicProgressResponse(BaseModel):
    """
    Response after syncing topic progress with Content Service.
    """
    user_id: str
    learning_language: str
    topic_id: str
    total_exercises_before: int
    total_exercises_after: int
    sync_successful: bool
    message: str
    
    model_config = ConfigDict(from_attributes=True)


class TopicProgressStatsResponse(BaseModel):
    """
    Aggregated statistics for user's topic progress.
    
    Used for analytics and dashboards.
    """
    user_id: str
    learning_language: str
    total_topics_started: int
    total_topics_completed: int  # mastery_score >= 1.0
    total_exercises_completed: int
    average_mastery_score: float
    topics_by_difficulty: Dict[str, int]  # {"beginner": 5, "intermediate": 3, "advanced": 1}
    
    model_config = ConfigDict(from_attributes=True)
