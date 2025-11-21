from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """
    Configuración de la aplicación.
    Las variables se cargan desde el entorno o archivo .env
    """
    
    # App
    APP_NAME: str = "Content Service"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "local"
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False
    
    # AWS
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: Optional[str] = None
    SECRETS_MANAGER_ARN: Optional[str] = None
    
    # Cognito
    COGNITO_POOL_ID: Optional[str] = None
    COGNITO_CLIENT_ID: Optional[str] = None
    COGNITO_REGION: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: list[str] = ["*"]
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True
    )


@lru_cache()
def get_settings() -> Settings:
    """Retorna configuración cacheada (singleton)"""
    return Settings()
