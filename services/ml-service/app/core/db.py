import boto3
from typing import Optional
from app.core.config import get_settings

settings = get_settings()


class AWSClient:
    """Cliente wrapper para servicios AWS (S3, SageMaker)"""
    
    def __init__(self):
        # Configuración para LocalStack o AWS
        session_config = {
            'region_name': settings.AWS_REGION
        }
        
        if settings.AWS_ENDPOINT_URL:
            session_config['endpoint_url'] = settings.AWS_ENDPOINT_URL
        
        if settings.AWS_ACCESS_KEY_ID:
            session_config['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
        
        if settings.AWS_SECRET_ACCESS_KEY:
            session_config['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY
        
        # Clientes
        self.s3_client = boto3.client('s3', **session_config)
        
        # SageMaker runtime (solo si hay endpoint configurado)
        if settings.SAGEMAKER_ENDPOINT:
            sagemaker_config = session_config.copy()
            sagemaker_config.pop('endpoint_url', None)  # SageMaker no usa endpoint_url custom
            self.sagemaker_runtime = boto3.client('sagemaker-runtime', **sagemaker_config)
        else:
            self.sagemaker_runtime = None
    
    async def upload_to_s3(self, file_path: str, bucket: str, key: str) -> str:
        """Sube un archivo a S3 y retorna la URL"""
        self.s3_client.upload_file(file_path, bucket, key)
        url = f"https://{bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
        return url
    
    async def download_from_s3(self, bucket: str, key: str, local_path: str):
        """Descarga un archivo desde S3"""
        self.s3_client.download_file(bucket, key, local_path)
    
    async def invoke_sagemaker_endpoint(self, data: bytes) -> dict:
        """Invoca un endpoint de SageMaker para inferencia"""
        if not self.sagemaker_runtime or not settings.SAGEMAKER_ENDPOINT:
            raise ValueError("SageMaker endpoint not configured")
        
        response = self.sagemaker_runtime.invoke_endpoint(
            EndpointName=settings.SAGEMAKER_ENDPOINT,
            ContentType='application/x-image',
            Body=data
        )
        
        return response


# Singleton del cliente
_aws_client: Optional[AWSClient] = None


def get_aws_client() -> AWSClient:
    """Retorna el cliente de AWS (singleton)"""
    global _aws_client
    if _aws_client is None:
        _aws_client = AWSClient()
    return _aws_client
