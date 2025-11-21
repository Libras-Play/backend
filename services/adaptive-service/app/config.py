"""
Configuration settings for Adaptive Service

WARNING: NO REPETIR ERROR 2
✔ NUNCA importar como: from app.config import settings
✔ SIEMPRE usar: from app.config import get_settings; settings = get_settings()
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Service
    SERVICE_NAME: str = "adaptive-service"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # AWS
    AWS_REGION: str = "us-east-1"
    DYNAMODB_USER_STREAKS_TABLE: str = "libras-play-dev-user-streaks"
    DYNAMODB_USER_DATA_TABLE: str = "libras-play-dev-user-data"
    
    # PostgreSQL (for adaptive_logs dataset)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/libras_play_dev"
    
    # Adaptive Engine Parameters
    MIN_DIFFICULTY: int = 1
    MAX_DIFFICULTY: int = 5
    CONSECUTIVE_CORRECT_THRESHOLD: int = 3  # Regla 1
    ERROR_RATE_THRESHOLD: float = 0.5       # Regla 2
    FAST_RESPONSE_TIME: int = 5             # seconds - Regla 3
    SLOW_RESPONSE_TIME: int = 30            # seconds - Regla 3
    
    # ML Model (future)
    ML_MODEL_PATH: str = "/app/models/adaptive_model.joblib"
    ML_MODEL_ENABLED: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    
    IMPORTANT: Always use this function, never import Settings directly
    """
    return Settings()
