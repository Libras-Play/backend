from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuración de la aplicación.
    Las variables se cargan desde el entorno o archivo .env
    """
    
    # App
    APP_NAME: str = "ML Service"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "local"
    LOG_LEVEL: str = "INFO"
    
    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ENDPOINT_URL: Optional[str] = None  # Para LocalStack
    AWS_ACCESS_KEY_ID: Optional[str] = None  # Para LocalStack
    AWS_SECRET_ACCESS_KEY: Optional[str] = None  # Para LocalStack
    
    # S3
    S3_BUCKET: Optional[str] = None
    
    # SageMaker
    SAGEMAKER_ENDPOINT: Optional[str] = None  # Endpoint de SageMaker (opcional)
    
    # Model paths
    MODEL_PATH: str = "/models"
    DEFAULT_MODEL_NAME: str = "sign_language_classifier.pth"
    
    # Inference
    MAX_VIDEO_SIZE_MB: int = 50
    SUPPORTED_VIDEO_FORMATS: list[str] = ["mp4", "avi", "mov", "webm"]
    SUPPORTED_IMAGE_FORMATS: list[str] = ["jpg", "jpeg", "png"]
    
    # CORS
    CORS_ORIGINS: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Retorna configuración cacheada (singleton)"""
    return Settings()
