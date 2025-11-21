"""
Configuration settings for User Service
"""
from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # App
    APP_NAME: str = "User Service"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "local"
    LOG_LEVEL: str = "INFO"
    
    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None  # Only for LocalStack, ECS uses IAM roles
    AWS_SECRET_ACCESS_KEY: Optional[str] = None  # Only for LocalStack, ECS uses IAM roles
    
    # DynamoDB
    DYNAMODB_ENDPOINT: Optional[str] = None  # None uses AWS, set for LocalStack
    DYNAMODB_USER_TABLE: str = "libras-play-dev-user-data"
    DYNAMODB_PROGRESS_TABLE: str = "libras-play-dev-user-progress"
    DYNAMODB_AI_SESSIONS_TABLE: str = "libras-play-dev-ai-sessions"
    DYNAMODB_USER_PATH_PROGRESS_TABLE: str = "libras-play-dev-user-path-progress"  # FASE 2: Path progression
    DYNAMODB_USER_STREAKS_TABLE: str = "libras-play-dev-user-streaks"  # FASE 3: Streak system
    DYNAMODB_USER_MISSIONS_TABLE: str = "libras-play-dev-user-streaks"  # FASE 4: Daily missions (shared with streaks for single-table design)
    
    # S3
    S3_BUCKET: str = "senas-user-media"
    S3_ENDPOINT: Optional[str] = None
    
    # SNS
    SNS_TOPIC_ARN: Optional[str] = None
    
    # Content Service (FASE 4: Mission Templates)
    CONTENT_SERVICE_URL: str = "http://libras-play-dev-alb-1450968088.us-east-1.elb.amazonaws.com/content"
    
    # Cognito Authentication
    COGNITO_USER_POOL_ID: str = "us-east-1_PvKA8zuHt"
    COGNITO_CLIENT_ID: str = "4r8ba8i780s8nc61lbnk7sh8jt"
    COGNITO_REGION: str = "us-east-1"
    
    # Gamification
    LIVES_MAX: int = 5
    LIVES_REGEN_MINUTES: int = 30
    XP_PER_LEVEL: int = 100
    STREAK_HOURS_THRESHOLD: int = 48
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True
    )


@lru_cache()
def get_settings() -> Settings:
    """Returns cached settings instance (singleton)"""
    return Settings()
