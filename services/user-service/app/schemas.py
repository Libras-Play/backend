"""
Pydantic schemas for user-service

All schemas use Pydantic v2 syntax with ConfigDict
"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime


# ============= ENUMS AND CONSTANTS =============

# Idiomas de interfaz disponibles (UI Languages)
VALID_UI_LANGUAGES = ["pt-BR", "es-ES", "en-US"]

# Lenguajes de señas disponibles (Sign Languages) 
VALID_SIGN_LANGUAGES = ["LSB", "ASL", "LSM"]

# Learning languages (same as sign languages for streak system)
VALID_LEARNING_LANGUAGES = ["LSB", "ASL", "LSM"]


# ============= USER SCHEMAS =============

class UserCreate(BaseModel):
    """Schema for creating a new user"""
    userId: str = Field(..., description="Unique user identifier (from Firebase Auth)")
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Display username")
    preferredLanguage: Optional[str] = Field(
        default="pt-BR", 
        description="Preferred UI language (pt-BR, es-ES, en-US)"
    )
    preferredSignLanguage: Optional[str] = Field(
        default="LSB",
        description="Preferred sign language to learn (LSB, ASL, LSM)"
    )
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="User preferences")
    
    @field_validator('preferredLanguage')
    @classmethod
    def validate_ui_language(cls, v: str) -> str:
        """Validate that UI language is one of the supported languages"""
        if v not in VALID_UI_LANGUAGES:
            raise ValueError(
                f"Invalid UI language '{v}'. Must be one of: {', '.join(VALID_UI_LANGUAGES)}"
            )
        return v
    
    @field_validator('preferredSignLanguage')
    @classmethod
    def validate_sign_language(cls, v: str) -> str:
        """Validate that sign language is one of the supported sign languages"""
        if v not in VALID_SIGN_LANGUAGES:
            raise ValueError(
                f"Invalid sign language '{v}'. Must be one of: {', '.join(VALID_SIGN_LANGUAGES)}"
            )
        return v
    
    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """Schema for user data response"""
    userId: str
    email: str
    username: str
    lives: int
    lastLifeLost: Optional[str] = None
    livesMaxedAt: Optional[str] = None  # Calculated field
    nextLifeAt: Optional[str] = None  # Calculated field
    xp: int
    totalXp: Optional[int] = None  # Alias for xp (backward compatibility)
    level: int
    currentLevel: Optional[int] = None  # Alias for level (backward compatibility)
    coins: int = Field(default=0, ge=0, description="Virtual coins earned")
    gems: int = Field(default=0, ge=0, description="Premium gems (can be purchased)")
    streakDays: int
    lastStreakDate: Optional[str] = None
    achievements: List[str]
    pathProgress: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Guided path progress: currentTopicId, currentDifficulty, completedExercisesCount"
    )
    preferredLanguage: str  # UI language (pt-BR, es-ES, en-US)
    preferredSignLanguage: Optional[str] = None  # Sign language to learn (LSB, ASL, LSM)
    settings: Dict[str, Any]
    createdAt: str
    lastLoginAt: str
    updatedAt: str
    
    model_config = ConfigDict(from_attributes=True)


class UserStatus(BaseModel):
    """Schema for user status (lives, XP, streak, coins, gems)"""
    userId: str
    lives: int
    livesMaxedAt: Optional[str] = None
    nextLifeAt: Optional[str] = None
    xp: int
    totalXp: Optional[int] = None  # Alias for xp
    level: int
    currentLevel: Optional[int] = None  # Alias for level
    coins: int = Field(default=0, ge=0)
    gems: int = Field(default=0, ge=0)
    xpProgress: Dict[str, int] = Field(
        ...,
        description="XP progress: currentLevel, xpInLevel, xpNeededForNext, xpPerLevel"
    )
    streakDays: int
    lastStreakDate: Optional[str] = None
    pathProgress: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Guided path progress"
    )
    
    model_config = ConfigDict(from_attributes=True)


class ConsumeLifeRequest(BaseModel):
    """Schema for consuming a life"""
    consume: int = Field(default=1, ge=1, le=5, description="Number of lives to consume")
    
    model_config = ConfigDict(from_attributes=True)


class ConsumeLifeResponse(BaseModel):
    """Schema for consume life response"""
    userId: str
    lives: int
    livesConsumed: int
    nextLifeAt: Optional[str] = None
    livesMaxedAt: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============= PROGRESS SCHEMAS =============

class ProgressUpdate(BaseModel):
    """Schema for updating user progress"""
    exerciseId: int = Field(..., description="Exercise ID")
    score: int = Field(..., ge=0, le=100, description="Score achieved (0-100)")
    xpEarned: int = Field(..., ge=0, description="XP earned from this attempt")
    completed: bool = Field(default=False, description="Whether exercise was completed successfully")
    
    model_config = ConfigDict(from_attributes=True)


class ProgressResponse(BaseModel):
    """Schema for progress data response"""
    userId: str
    levelId: str
    exercises: Dict[str, Dict[str, Any]]
    totalAttempts: int
    totalScore: int
    xpEarned: int
    completed: bool
    createdAt: str
    updatedAt: str
    completedAt: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class ExerciseAttemptResult(BaseModel):
    """Schema for exercise attempt result with gamification"""
    progressUpdated: bool
    xpGained: int
    levelUp: bool
    newLevel: int
    currentStreak: int
    achievementsUnlocked: List[str]
    userStatus: UserStatus
    
    model_config = ConfigDict(from_attributes=True)


# ============= AI SESSION SCHEMAS =============

class AiSessionCreate(BaseModel):
    """Schema for creating AI processing session"""
    userId: str = Field(..., description="User identifier")
    exerciseId: int = Field(..., description="Exercise identifier")
    levelId: int = Field(..., description="Level identifier")
    videoUrl: str = Field(..., description="S3 URL of uploaded video")
    
    model_config = ConfigDict(from_attributes=True)


class AiSessionResponse(BaseModel):
    """Schema for AI session data response"""
    sessionId: str
    userId: str
    exerciseId: int
    levelId: int
    videoUrl: str
    status: str  # pending, processing, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    createdAt: str
    updatedAt: str
    processedAt: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============= ACHIEVEMENT SCHEMAS =============

class Achievement(BaseModel):
    """Schema for achievement data"""
    code: str
    title: str
    description: str
    xpReward: int
    unlocked: bool
    
    model_config = ConfigDict(from_attributes=True)


class AchievementProgress(BaseModel):
    """Schema for user's achievement progress"""
    unlocked: int
    total: int
    percentage: int
    achievements: List[Achievement]
    
    model_config = ConfigDict(from_attributes=True)


# ============= COINS AND GEMS SCHEMAS =============

class AddCoinsRequest(BaseModel):
    """Schema for adding coins to user"""
    amount: int = Field(..., gt=0, description="Amount of coins to add (must be > 0)")
    reason: Optional[str] = Field(default="Coins earned", description="Reason for earning coins")
    
    model_config = ConfigDict(from_attributes=True)


class AddCoinsResponse(BaseModel):
    """Schema for add coins response"""
    userId: str
    coinsAdded: int
    totalCoins: int
    reason: str
    
    model_config = ConfigDict(from_attributes=True)


class AddXpRequest(BaseModel):
    """Schema for adding XP to user"""
    amount: int = Field(..., gt=0, description="Amount of XP to add (must be > 0)")
    reason: Optional[str] = Field(default="XP earned", description="Reason for earning XP")
    
    model_config = ConfigDict(from_attributes=True)


class AddXpResponse(BaseModel):
    """Schema for add XP response"""
    userId: str
    xpAdded: int
    totalXp: int
    previousLevel: int
    currentLevel: int
    leveledUp: bool
    reason: str
    
    model_config = ConfigDict(from_attributes=True)


class RegenLivesResponse(BaseModel):
    """Schema for regenerate lives response"""
    userId: str
    livesBeforeRegen: int
    livesAfterRegen: int
    livesRegened: int
    nextLifeAt: Optional[str] = None
    livesMaxedAt: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============= GENERAL SCHEMAS =============

class ErrorResponse(BaseModel):
    """Schema for error responses"""
    error: str
    detail: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class SuccessResponse(BaseModel):
    """Schema for generic success responses"""
    message: str
    data: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============= PATH PROGRESSION SCHEMAS (FASE 2) =============

class LevelProgress(BaseModel):
    """Schema for a single difficulty level progress within a topic"""
    progress: int = Field(default=0, ge=0, le=100, description="Progress percentage (0-100)")
    completedExercises: int = Field(default=0, ge=0, description="Number of completed exercises")
    unlocked: bool = Field(default=False, description="Whether this level is unlocked")
    requiredToUnlock: int = Field(default=10, gt=0, description="Number of exercises required to unlock next level")
    completed: bool = Field(default=False, description="Whether this level is completed (progress >= 100)")
    
    model_config = ConfigDict(from_attributes=True)


class TopicPathStatus(BaseModel):
    """Schema for a single topic's path status (includes all difficulty levels)"""
    topicId: str = Field(..., description="Topic identifier")
    userId: str = Field(..., description="User identifier")
    learningLanguage: str = Field(..., description="Sign language code (LSB, ASL, LSM)")
    unlocked: bool = Field(default=False, description="Whether this topic is unlocked")
    completed: bool = Field(default=False, description="Whether all levels in this topic are completed")
    levels: Dict[str, LevelProgress] = Field(
        default_factory=dict,
        description="Progress for each difficulty level (easy, medium, hard)"
    )
    currentDifficulty: str = Field(default="easy", description="Current active difficulty level")
    orderIndex: int = Field(default=0, ge=0, description="Position in the learning path")
    autoUnlocked: bool = Field(default=False, description="Whether topic was auto-unlocked after completing previous")
    autoUnlockedAt: Optional[str] = Field(default=None, description="Timestamp when topic was auto-unlocked")
    manualUnlock: bool = Field(default=False, description="Whether manual unlock is allowed")
    manualUnlockCostCoins: int = Field(default=100, ge=0, description="Coins cost to manually unlock")
    manualUnlockCostGems: int = Field(default=1, ge=0, description="Gems cost to manually unlock")
    createdAt: str = Field(..., description="Creation timestamp")
    updatedAt: str = Field(..., description="Last update timestamp")
    
    @field_validator('learningLanguage')
    @classmethod
    def validate_learning_language(cls, v: str) -> str:
        """Validate that learning language is supported"""
        if v not in VALID_SIGN_LANGUAGES:
            raise ValueError(
                f"Invalid learning language '{v}'. Must be one of: {', '.join(VALID_SIGN_LANGUAGES)}"
            )
        return v
    
    model_config = ConfigDict(from_attributes=True)


class UserPathResponse(BaseModel):
    """Schema for complete user path response (all topics for a learning language)"""
    userId: str
    learningLanguage: str
    topics: List[TopicPathStatus]
    totalTopics: int
    unlockedTopics: int
    completedTopics: int
    currentTopicId: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class UnlockTopicRequest(BaseModel):
    """Schema for manually unlocking a topic"""
    topicId: str = Field(..., description="Topic identifier to unlock")
    learningLanguage: str = Field(..., description="Sign language code (LSB, ASL, LSM)")
    payment: Optional[Dict[str, int]] = Field(
        default=None,
        description="Payment for manual unlock: {'coins': 100, 'gems': 0}"
    )
    
    @field_validator('learningLanguage')
    @classmethod
    def validate_learning_language(cls, v: str) -> str:
        if v not in VALID_SIGN_LANGUAGES:
            raise ValueError(
                f"Invalid learning language '{v}'. Must be one of: {', '.join(VALID_SIGN_LANGUAGES)}"
            )
        return v
    
    @field_validator('payment')
    @classmethod
    def validate_payment(cls, v: Optional[Dict[str, int]]) -> Optional[Dict[str, int]]:
        """Validate payment structure if provided"""
        if v is not None:
            if 'coins' not in v and 'gems' not in v:
                raise ValueError("Payment must include 'coins' and/or 'gems'")
            if v.get('coins', 0) < 0 or v.get('gems', 0) < 0:
                raise ValueError("Payment amounts cannot be negative")
        return v
    
    model_config = ConfigDict(from_attributes=True)


class UnlockTopicResponse(BaseModel):
    """Schema for unlock topic response"""
    userId: str
    topicId: str
    learningLanguage: str
    unlocked: bool
    method: str = Field(..., description="Unlock method: auto, manual, already_unlocked")
    coinsSpent: int = Field(default=0, ge=0)
    gemsSpent: int = Field(default=0, ge=0)
    remainingCoins: int = Field(default=0, ge=0)
    remainingGems: int = Field(default=0, ge=0)
    message: str
    
    model_config = ConfigDict(from_attributes=True)


class PathProgressRequest(BaseModel):
    """Schema for updating path progress after exercise attempt"""
    topicId: str = Field(..., description="Topic identifier")
    exerciseId: str = Field(..., description="Exercise identifier")
    learningLanguage: str = Field(..., description="Sign language code (LSB, ASL, LSM)")
    difficulty: str = Field(..., description="Exercise difficulty: easy, medium, hard")
    outcome: str = Field(..., description="Attempt outcome: correct, incorrect")
    xpEarned: int = Field(default=0, ge=0, description="XP earned from this attempt")
    
    @field_validator('learningLanguage')
    @classmethod
    def validate_learning_language(cls, v: str) -> str:
        if v not in VALID_SIGN_LANGUAGES:
            raise ValueError(
                f"Invalid learning language '{v}'. Must be one of: {', '.join(VALID_SIGN_LANGUAGES)}"
            )
        return v
    
    @field_validator('difficulty')
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        valid_difficulties = ['easy', 'medium', 'hard']
        if v.lower() not in valid_difficulties:
            raise ValueError(
                f"Invalid difficulty '{v}'. Must be one of: {', '.join(valid_difficulties)}"
            )
        return v.lower()
    
    @field_validator('outcome')
    @classmethod
    def validate_outcome(cls, v: str) -> str:
        valid_outcomes = ['correct', 'incorrect']
        if v.lower() not in valid_outcomes:
            raise ValueError(
                f"Invalid outcome '{v}'. Must be one of: {', '.join(valid_outcomes)}"
            )
        return v.lower()
    
    model_config = ConfigDict(from_attributes=True)


class PathProgressResponse(BaseModel):
    """Schema for path progress update response"""
    userId: str
    topicId: str
    exerciseId: str
    learningLanguage: str
    difficulty: str
    outcome: str
    progressUpdated: bool
    levelCompleted: bool = Field(default=False)
    topicCompleted: bool = Field(default=False)
    nextTopicUnlocked: bool = Field(default=False)
    nextTopicId: Optional[str] = None
    currentProgress: int = Field(ge=0, le=100, description="Current progress percentage")
    completedExercises: int = Field(ge=0)
    requiredExercises: int = Field(gt=0)
    message: str
    
    model_config = ConfigDict(from_attributes=True)


class PathEvent(BaseModel):
    """Schema for path-related events (for SNS/EventBridge)"""
    eventType: str = Field(
        ..., 
        description="Event type: TOPIC_UNLOCKED, TOPIC_COMPLETED, LEVEL_COMPLETED, PATH_PROGRESS_UPDATED"
    )
    userId: str
    topicId: str
    learningLanguage: str
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(from_attributes=True)


# ============= STREAK SYSTEM SCHEMAS (FASE 3) =============

class PendingReward(BaseModel):
    """Pending rewards for streak milestone"""
    coins: int = Field(default=0, ge=0, description="Pending coins to claim")
    gems: int = Field(default=0, ge=0, description="Pending gems to claim")
    xp: int = Field(default=0, ge=0, description="Pending XP to claim")


class StreakStatus(BaseModel):
    """Current streak status for a user and learning language"""
    userId: str = Field(..., description="User identifier")
    learningLanguage: str = Field(..., description="Sign language code (LSB, ASL, LSM)")
    currentStreak: int = Field(default=0, ge=0, description="Current consecutive days")
    bestStreak: int = Field(default=0, ge=0, description="Best streak achieved")
    lastActivityDay: Optional[str] = Field(None, description="Last activity date (YYYY-MM-DD)")
    lastClaimedAt: Optional[str] = Field(None, description="Last reward claim timestamp (ISO 8601)")
    metricCountToday: int = Field(default=0, ge=0, description="Activities counted today")
    metricRequired: int = Field(default=3, ge=1, description="Required activities per day")
    rewardGrantedToday: bool = Field(default=False, description="Whether reward was granted today")
    pendingReward: PendingReward = Field(default_factory=PendingReward, description="Unclaimed rewards")
    timezone: str = Field(default="UTC", description="User timezone (IANA format)")
    nextResetAt: Optional[str] = Field(None, description="Next streak reset time (ISO 8601)")
    streakHealth: str = Field(default="active", description="Streak health: active, at_risk, broken")
    
    @field_validator('learningLanguage')
    @classmethod
    def validate_learning_language(cls, v: str) -> str:
        """Validate learning_language"""
        if v not in VALID_LEARNING_LANGUAGES:
            raise ValueError(f"Invalid learning_language. Must be one of: {', '.join(VALID_LEARNING_LANGUAGES)}")
        return v
    
    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone is valid IANA timezone"""
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(v)
            return v
        except Exception:
            # Fallback to UTC if invalid
            return "UTC"


class RecordActivityRequest(BaseModel):
    """Request to record user activity for streak tracking"""
    learningLanguage: str = Field(..., description="Sign language code")
    activityType: str = Field(default="exercise_complete", description="Type of activity")
    value: int = Field(default=1, ge=1, le=100, description="Activity count (capped at 100/day)")
    exerciseId: Optional[str] = Field(None, description="Exercise ID if applicable")
    timezone: Optional[str] = Field(default="UTC", description="User timezone (default: UTC)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('learningLanguage')
    @classmethod
    def validate_learning_language(cls, v: str) -> str:
        if v not in VALID_LEARNING_LANGUAGES:
            raise ValueError(f"Invalid learning_language. Must be one of: {', '.join(VALID_LEARNING_LANGUAGES)}")
        return v
    
    @field_validator('activityType')
    @classmethod
    def validate_activity_type(cls, v: str) -> str:
        valid_types = ["exercise_complete", "xp_earned", "camera_minutes", "topic_completed"]
        if v not in valid_types:
            raise ValueError(f"Invalid activityType. Must be one of: {', '.join(valid_types)}")
        return v


class RewardGranted(BaseModel):
    """Rewards granted for streak milestone"""
    coins: int = Field(default=0, ge=0)
    gems: int = Field(default=0, ge=0)
    xp: int = Field(default=0, ge=0)
    reason: str = Field(..., description="Reason for reward")
    milestone: Optional[int] = Field(None, description="Streak milestone if applicable")


class RecordActivityResponse(BaseModel):
    """Response after recording activity"""
    success: bool = Field(..., description="Whether activity was recorded")
    streakUpdated: bool = Field(default=False, description="Whether streak was incremented")
    currentStreak: int = Field(..., ge=0, description="Current streak after update")
    metricCountToday: int = Field(..., ge=0, description="Total activities today")
    metricRequired: int = Field(..., ge=1, description="Required activities per day")
    progress: float = Field(..., ge=0, le=100, description="Progress towards daily goal (%)")
    rewardGranted: Optional[RewardGranted] = Field(None, description="Reward granted if any")
    nextMilestone: Optional[int] = Field(None, description="Next streak milestone for reward")
    message: str = Field(..., description="User-friendly message")


class ClaimRewardRequest(BaseModel):
    """Request to claim pending streak rewards"""
    learningLanguage: str = Field(..., description="Sign language code")
    
    @field_validator('learningLanguage')
    @classmethod
    def validate_learning_language(cls, v: str) -> str:
        if v not in VALID_LEARNING_LANGUAGES:
            raise ValueError(f"Invalid learning_language. Must be one of: {', '.join(VALID_LEARNING_LANGUAGES)}")
        return v


class ClaimRewardResponse(BaseModel):
    """Response after claiming rewards"""
    success: bool = Field(..., description="Whether claim was successful")
    rewardClaimed: RewardGranted = Field(..., description="Rewards claimed")
    newBalance: Dict[str, int] = Field(..., description="New balances after claim")
    message: str = Field(..., description="User-friendly message")


class StreakHistoryItem(BaseModel):
    """Historical streak record for a specific day"""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    metricCount: int = Field(..., ge=0, description="Activities completed that day")
    metricRequired: int = Field(..., ge=1, description="Required activities")
    goalMet: bool = Field(..., description="Whether daily goal was met")
    streakValue: int = Field(..., ge=0, description="Streak value on that day")
    rewardEarned: Optional[RewardGranted] = Field(None, description="Reward earned that day")


class StreakHistoryResponse(BaseModel):
    """Historical streak data"""
    userId: str
    learningLanguage: str
    history: List[StreakHistoryItem] = Field(..., description="Daily history items")
    totalDays: int = Field(..., ge=0, description="Total days in history")
    daysWithGoalMet: int = Field(..., ge=0, description="Days where goal was met")
    currentStreak: int = Field(..., ge=0, description="Current active streak")
    bestStreak: int = Field(..., ge=0, description="Best streak in history")


class StreakEvent(BaseModel):
    """Event emitted for streak state changes"""
    eventType: str = Field(..., description="Event type: STREAK_UPDATED, STREAK_BROKEN, STREAK_REWARDED")
    userId: str = Field(..., description="User identifier")
    learningLanguage: str = Field(..., description="Sign language code")
    currentStreak: int = Field(..., ge=0, description="Current streak value")
    previousStreak: Optional[int] = Field(None, description="Previous streak value")
    rewardGranted: Optional[RewardGranted] = Field(None, description="Reward if granted")
    timestamp: str = Field(..., description="Event timestamp (ISO 8601)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional event data")
    
    @field_validator('eventType')
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        valid_types = ["STREAK_UPDATED", "STREAK_BROKEN", "STREAK_REWARDED", "STREAK_MILESTONE", "SUSPICIOUS_ACTIVITY"]
        if v not in valid_types:
            raise ValueError(f"Invalid eventType. Must be one of: {', '.join(valid_types)}")
        return v
