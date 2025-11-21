"""
Pydantic schemas for Adaptive Service

FASE 6: Request/Response models with validation
"""
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class NextDifficultyRequest(BaseModel):
    """Request for next difficulty calculation"""
    user_id: str = Field(..., min_length=1, description="User ID")
    learning_language: str = Field(..., min_length=2, max_length=10, description="Sign language code (LSB, LIBRAS, etc.)")
    exercise_type: str = Field(default="general", description="Type of exercise (test, practice, etc.)")
    current_difficulty: Optional[int] = Field(default=None, ge=1, le=5, description="Current difficulty level (1-5)")


class DifficultyAdjustments(BaseModel):
    """Breakdown of difficulty adjustments by rule"""
    consistency: int = Field(..., description="Adjustment from consistency rule (-1, 0, +1)")
    errorRate: int = Field(..., description="Adjustment from error rate rule (-1, 0, +1)")
    speed: int = Field(..., description="Adjustment from speed rule (-1, 0, +1)")


class NextDifficultyResponse(BaseModel):
    """Response with next difficulty recommendation"""
    user_id: str = Field(..., description="User ID")
    currentDifficulty: int = Field(..., ge=1, le=5, description="Current difficulty level")
    nextDifficulty: int = Field(..., ge=1, le=5, description="Recommended next difficulty level")
    masteryScore: float = Field(..., ge=0.0, le=1.0, description="Mastery score (0-1)")
    reason: str = Field(..., description="Human-readable reason for change")
    modelUsed: bool = Field(default=False, description="Whether ML model was used")
    adjustments: DifficultyAdjustments = Field(..., description="Rule-based adjustments breakdown")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Calculation timestamp")


class AdaptiveDecisionLog(BaseModel):
    """
    Log entry for adaptive decisions - used for future ML training dataset
    
    This schema matches the PostgreSQL adaptive_logs table structure
    """
    user_id: str = Field(..., description="User ID")
    learning_language: str = Field(..., description="Sign language code")
    exercise_type: str = Field(..., description="Exercise type")
    current_difficulty: int = Field(..., ge=1, le=5, description="Difficulty before decision")
    next_difficulty: int = Field(..., ge=1, le=5, description="Recommended difficulty")
    mastery_score: float = Field(..., ge=0.0, le=1.0, description="Calculated mastery score")
    time_spent: Optional[float] = Field(None, description="Average time spent on recent exercises (seconds)")
    correct: Optional[bool] = Field(None, description="Most recent exercise correctness")
    error_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="Recent error rate")
    consistency_adjustment: int = Field(default=0, description="Consistency rule adjustment")
    error_adjustment: int = Field(default=0, description="Error rule adjustment")
    speed_adjustment: int = Field(default=0, description="Speed rule adjustment")
    model_used: bool = Field(default=False, description="Whether ML model was used")
    model_prediction: Optional[int] = Field(None, ge=1, le=5, description="ML model prediction if available")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Decision timestamp")
    
    class Config:
        protected_namespaces = ()  # Fix Pydantic warning for model_ fields
        json_schema_extra = {
            "example": {
                "user_id": "c4d8c4d8-4071-701c-a763-4a4d255dd815",
                "learning_language": "LSB",
                "exercise_type": "test",
                "current_difficulty": 2,
                "next_difficulty": 3,
                "mastery_score": 0.81,
                "time_spent": 8.5,
                "correct": True,
                "error_rate": 0.15,
                "consistency_adjustment": 1,
                "error_adjustment": 1,
                "speed_adjustment": 1,
                "model_used": False,
                "model_prediction": None,
                "timestamp": "2025-11-20T09:30:00Z"
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(default="healthy", description="Service health status")
    service: str = Field(default="adaptive-service", description="Service name")
    version: str = Field(..., description="Service version")
    ml_model_available: bool = Field(..., description="Whether ML model is loaded")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
