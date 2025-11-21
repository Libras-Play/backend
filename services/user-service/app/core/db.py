import boto3
from botocore.exceptions import ClientError
from typing import Optional
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class DynamoDBClient:
    """Cliente wrapper para DynamoDB"""
    
    def __init__(self):
        # Configuración para LocalStack o AWS
        session_config = {
            'region_name': settings.AWS_REGION
        }
        
        # Solo usar endpoint_url para LocalStack (desarrollo local)
        if settings.AWS_ENDPOINT_URL:
            session_config['endpoint_url'] = settings.AWS_ENDPOINT_URL
            logger.info(f"Using LocalStack endpoint: {settings.AWS_ENDPOINT_URL}")
        
        # Solo pasar credenciales explícitas si estamos en desarrollo local (con endpoint_url)
        # En ECS, boto3 usa automáticamente el IAM role del task
        if settings.AWS_ENDPOINT_URL and settings.AWS_ACCESS_KEY_ID:
            session_config['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
            logger.info("Using explicit AWS credentials (LocalStack mode)")
        
        if settings.AWS_ENDPOINT_URL and settings.AWS_SECRET_ACCESS_KEY:
            session_config['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY
        
        # Log configuration (without sensitive data)
        logger.info(f"DynamoDB config: region={session_config.get('region_name')}, "
                   f"endpoint={session_config.get('endpoint_url', 'AWS')}, "
                   f"explicit_creds={bool(settings.AWS_ENDPOINT_URL and settings.AWS_ACCESS_KEY_ID)}")
        
        self.dynamodb = boto3.resource('dynamodb', **session_config)
        self.client = boto3.client('dynamodb', **session_config)
        
        # Referencias a las tablas
        self.users_table = self.dynamodb.Table(settings.DYNAMODB_USERS_TABLE)
        self.progress_table = self.dynamodb.Table(settings.DYNAMODB_PROGRESS_TABLE)
    
    async def create_tables_if_not_exist(self):
        """Crea las tablas de DynamoDB si no existen (útil para desarrollo local)"""
        try:
            # Verificar si la tabla de usuarios existe
            self.client.describe_table(TableName=settings.DYNAMODB_USERS_TABLE)
        except ClientError:
            # Crear tabla de usuarios
            self.dynamodb.create_table(
                TableName=settings.DYNAMODB_USERS_TABLE,
                KeySchema=[
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'user_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
        
        try:
            # Verificar si la tabla de progreso existe
            self.client.describe_table(TableName=settings.DYNAMODB_PROGRESS_TABLE)
        except ClientError:
            # Crear tabla de progreso
            self.dynamodb.create_table(
                TableName=settings.DYNAMODB_PROGRESS_TABLE,
                KeySchema=[
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'exercise_id', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'user_id', 'AttributeType': 'S'},
                    {'AttributeName': 'exercise_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )


# Singleton del cliente
_dynamodb_client: Optional[DynamoDBClient] = None


def get_dynamodb_client() -> DynamoDBClient:
    """Retorna el cliente de DynamoDB (singleton)"""
    global _dynamodb_client
    if _dynamodb_client is None:
        _dynamodb_client = DynamoDBClient()
    return _dynamodb_client
