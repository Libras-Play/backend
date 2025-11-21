from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuración de la aplicación.
    Las variables se cargan desde el entorno o archivo .env
    """
    
    # App
    APP_NAME: str = "User Service"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "local"
    LOG_LEVEL: str = "INFO"
    
    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ENDPOINT_URL: Optional[str] = None  # Para LocalStack
    AWS_ACCESS_KEY_ID: Optional[str] = None  # Para LocalStack
    AWS_SECRET_ACCESS_KEY: Optional[str] = None  # Para LocalStack
    
    # DynamoDB Tables
    DYNAMODB_USERS_TABLE: str = "users"
    DYNAMODB_PROGRESS_TABLE: str = "user_progress"
    
    # Cognito
    COGNITO_POOL_ID: Optional[str] = None
    COGNITO_CLIENT_ID: Optional[str] = None
    COGNITO_REGION: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Retorna configuración cacheada (singleton)"""
    return Settings()
