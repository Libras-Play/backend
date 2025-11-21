"""
FASE 5: Badge Schemas (Pydantic)

ANTI-ERROR DESIGN:
- Simple types only (no Enums to avoid serialization issues)
- Clear validation rules
- Multilang support via Dict[str, str]
- Validators to ensure data integrity
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, List, Any
from datetime import datetime


# ============================================================================
# Badge Condition Schema
# ============================================================================

class BadgeCondition(BaseModel):
    """
    Condition to earn a badge.
    
    Examples:
    - {"metric": "xp", "operator": ">=", "value": 1000}
    - {"metric": "streak_days", "operator": ">=", "value": 7}
    """
    metric: str = Field(..., description="Metric to check (xp, streak_days, exercises_completed, topics_completed, camera_minutes, level)")
    operator: str = Field(default=">=", description="Comparison operator")
    value: int = Field(..., gt=0, description="Required value (must be > 0)")
    
    @field_validator('metric')
    @classmethod
    def validate_metric(cls, v: str) -> str:
        """Ensure metric is one of the known types"""
        ALLOWED_METRICS = {
            'xp', 'level', 'streak_days', 
            'exercises_completed', 'topics_completed', 
            'camera_minutes'
        }
        if v not in ALLOWED_METRICS:
            raise ValueError(f"metric must be one of {ALLOWED_METRICS}, got: {v}")
        return v
    
    @field_validator('operator')
    @classmethod
    def validate_operator(cls, v: str) -> str:
        """Ensure operator is valid"""
        ALLOWED_OPERATORS = {'>=', '>', '==', '<=', '<'}
        if v not in ALLOWED_OPERATORS:
            raise ValueError(f"operator must be one of {ALLOWED_OPERATORS}, got: {v}")
        return v


# ============================================================================
# Badge Master Schemas (Content Service)
# ============================================================================

class BadgeMasterBase(BaseModel):
    """Base schema for badge definitions"""
    type: str = Field(..., description="Badge type: milestone, achievement, streak, skill, special")
    title: Dict[str, str] = Field(..., description="Multilang title: {es, en, pt}")
    description: Dict[str, str] = Field(..., description="Multilang description")
    icon_url: str = Field(..., description="URL to badge icon")
    conditions: Dict[str, Any] = Field(..., description="Conditions: {metric, operator, value}")
    learning_language: str = Field(..., description="LSB, ASL, LSM")
    is_hidden: bool = Field(default=False, description="Hidden until earned")
    rarity: str = Field(default="common", description="common, rare, epic, legendary")
    order_index: int = Field(default=0, ge=0)
    
    @field_validator('title', 'description')
    @classmethod
    def validate_multilang(cls, v: Dict[str, str], info) -> Dict[str, str]:
        """
        Ensure multilang fields have ALL required languages.
        
        ANTI-ERROR: badgeDefinitionHasAllLanguages validation
        """
        REQUIRED_LANGUAGES = {'es', 'en', 'pt'}
        
        if not isinstance(v, dict):
            raise ValueError(f"{info.field_name} must be a dictionary")
        
        missing = REQUIRED_LANGUAGES - set(v.keys())
        if missing:
            raise ValueError(
                f"{info.field_name} must contain keys {REQUIRED_LANGUAGES}, "
                f"missing: {missing}"
            )
        
        # Ensure all values are non-empty strings
        for lang, text in v.items():
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"{info.field_name}[{lang}] must be a non-empty string")
        
        return v
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate badge type"""
        ALLOWED_TYPES = {'milestone', 'achievement', 'streak', 'skill', 'special'}
        if v not in ALLOWED_TYPES:
            raise ValueError(f"type must be one of {ALLOWED_TYPES}, got: {v}")
        return v
    
    @field_validator('rarity')
    @classmethod
    def validate_rarity(cls, v: str) -> str:
        """Validate rarity"""
        ALLOWED_RARITIES = {'common', 'rare', 'epic', 'legendary'}
        if v not in ALLOWED_RARITIES:
            raise ValueError(f"rarity must be one of {ALLOWED_RARITIES}, got: {v}")
        return v
    
    @field_validator('learning_language')
    @classmethod
    def validate_learning_language(cls, v: str) -> str:
        """Validate learning language"""
        ALLOWED_LANGUAGES = {'LSB', 'ASL', 'LSM', 'LIBRAS'}
        if v not in ALLOWED_LANGUAGES:
            raise ValueError(f"learning_language must be one of {ALLOWED_LANGUAGES}, got: {v}")
        return v
    
    @model_validator(mode='after')
    def validate_conditions_structure(self):
        """
        Validate conditions schema.
        
        ANTI-ERROR: ensureBadgeConditionsAreValid
        """
        conditions = self.conditions
        
        # Ensure conditions has required keys
        required_keys = {'metric', 'operator', 'value'}
        if not all(k in conditions for k in required_keys):
            raise ValueError(f"conditions must contain {required_keys}")
        
        # Validate using BadgeCondition schema
        try:
            BadgeCondition(**conditions)
        except Exception as e:
            raise ValueError(f"Invalid conditions structure: {str(e)}")
        
        return self


class BadgeMasterCreate(BadgeMasterBase):
    """Schema for creating a new badge"""
    badge_id: Optional[str] = None  # Auto-generated if not provided


class BadgeMasterResponse(BadgeMasterBase):
    """Schema for badge responses"""
    badge_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# User Badge Schemas (User Service)
# ============================================================================

class UserBadgeBase(BaseModel):
    """Base schema for user's earned badges"""
    badge_id: str
    earned_at: int = Field(..., description="Unix timestamp when earned")


class UserBadgeResponse(UserBadgeBase):
    """Response for user's earned badge"""
    notified: bool = Field(default=False)


class BadgeWithDetails(BadgeMasterResponse):
    """Badge with earning status"""
    earned: bool = Field(default=False)
    earned_at: Optional[int] = None
    hidden: bool = Field(default=False, description="Hidden badge not yet earned")


class UserBadgesStatsResponse(BaseModel):
    """User badge statistics"""
    total_earned: int
    total_available: int
    progress_percentage: float
    earned_badges: List[BadgeWithDetails]


class AllBadgesResponse(BaseModel):
    """All badges with status for user"""
    badges: List[BadgeWithDetails]
    stats: Dict[str, Any] = Field(
        default_factory=lambda: {
            'total_earned': 0,
            'total_available': 0,
            'by_rarity': {},
            'by_type': {}
        }
    )


class CheckBadgesResponse(BaseModel):
    """Response after checking for new badges"""
    newly_earned: List[BadgeWithDetails]
    total_new: int
    message: str = Field(default="Badge check completed")


class BadgeNotificationRequest(BaseModel):
    """Request to mark badge as notified"""
    badge_id: str


class BadgeNotificationResponse(BaseModel):
    """Response after marking notification"""
    success: bool
    message: str
