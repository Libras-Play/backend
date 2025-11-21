"""
Configuration settings for ML Service

Manages environment variables and application settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = "test"
    AWS_SECRET_ACCESS_KEY: str = "test"
    AWS_ENDPOINT_URL: str = "http://localhost:4566"
    
    # SageMaker Configuration
    USE_SAGEMAKER: bool = False  # Toggle between SageMaker and local stub
    SAGEMAKER_ENDPOINT_NAME: str = "sign-language-endpoint-2024"
    SAGEMAKER_RUNTIME_REGION: str = "us-east-1"
    
    # S3 Configuration
    S3_BUCKET_MODELS: str = "ml-models-bucket"
    S3_BUCKET_VIDEOS: str = "user-videos-bucket"
    MODEL_S3_KEY: str = "models/sign_language_v1.tflite"
    MODEL_VERSION: str = "1.0.0"
    
    # SQS Configuration
    SQS_QUEUE_URL: str = "http://localhost:4566/000000000000/video-processing-queue"
    SQS_POLL_INTERVAL_SECONDS: int = 5
    SQS_MAX_MESSAGES: int = 10
    SQS_WAIT_TIME_SECONDS: int = 20  # Long polling
    
    # DynamoDB Configuration
    DYNAMODB_TABLE_AI_SESSIONS: str = "AiSessions"
    
    # ML Configuration
    MODEL_LOCAL_PATH: str = "./models/sign_language_stub.tflite"
    CONFIDENCE_THRESHOLD: float = 0.5
    GESTURE_LABELS: str = "A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z"
    MAX_VIDEO_SIZE_MB: int = 50
    VIDEO_PROCESSING_TIMEOUT_SECONDS: int = 60
    
    # API Configuration
    APP_NAME: str = "ML Service"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "local"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8003
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )
    
    @property
    def gesture_labels_list(self) -> List[str]:
        """Parse gesture labels from comma-separated string"""
        return [label.strip() for label in self.GESTURE_LABELS.split(",")]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def max_video_size_bytes(self) -> int:
        """Convert max video size from MB to bytes"""
        return self.MAX_VIDEO_SIZE_MB * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
