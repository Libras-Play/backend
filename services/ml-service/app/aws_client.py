"""
AWS Client for ML Service

Handles SageMaker, S3, SQS, and DynamoDB operations
"""
import boto3
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AWSClient:
    """Singleton AWS client for ML operations"""
    
    def __init__(self):
        """Initialize AWS clients"""
        self.settings = settings
        
        # Configure boto3
        boto3_config = {
            'region_name': settings.AWS_REGION,
            'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
        }
        
        # Add endpoint URL for LocalStack
        if settings.ENVIRONMENT == "local":
            boto3_config['endpoint_url'] = settings.AWS_ENDPOINT_URL
        
        # Initialize clients
        self.s3 = boto3.client('s3', **boto3_config)
        self.sqs = boto3.client('sqs', **boto3_config)
        self.dynamodb = boto3.resource('dynamodb', **boto3_config)
        
        # SageMaker runtime (production only)
        if settings.USE_SAGEMAKER:
            sagemaker_config = {
                'region_name': settings.SAGEMAKER_RUNTIME_REGION,
                'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
                'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
            }
            self.sagemaker_runtime = boto3.client('sagemaker-runtime', **sagemaker_config)
        else:
            self.sagemaker_runtime = None
        
        logger.info(f"AWS Client initialized (SageMaker: {settings.USE_SAGEMAKER})")
    
    # ============= SAGEMAKER OPERATIONS =============
    
    async def invoke_sagemaker_endpoint(self, video_data: bytes) -> Dict[str, Any]:
        """
        Invoke SageMaker endpoint for inference
        
        Args:
            video_data: Video file bytes
            
        Returns:
            Inference result from SageMaker
        """
        if not self.sagemaker_runtime:
            raise ValueError("SageMaker runtime not initialized (USE_SAGEMAKER=false)")
        
        try:
            response = self.sagemaker_runtime.invoke_endpoint(
                EndpointName=settings.SAGEMAKER_ENDPOINT_NAME,
                ContentType='application/octet-stream',
                Body=video_data
            )
            
            # Parse response
            result = json.loads(response['Body'].read().decode())
            return result
            
        except Exception as e:
            logger.error(f"SageMaker invocation failed: {e}")
            raise
    
    # ============= S3 OPERATIONS =============
    
    async def download_video_from_s3(self, s3_url: str) -> bytes:
        """
        Download video from S3
        
        Args:
            s3_url: S3 URL (s3://bucket/key or https://...)
            
        Returns:
            Video file bytes
        """
        try:
            # Parse S3 URL
            if s3_url.startswith('s3://'):
                # s3://bucket/key
                parts = s3_url[5:].split('/', 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else ''
            else:
                # https://bucket.s3.region.amazonaws.com/key
                # For simplicity, assume format: https://bucket/key
                parts = s3_url.replace('https://', '').replace('http://', '').split('/', 1)
                bucket = parts[0].split('.')[0]  # Extract bucket name
                key = parts[1] if len(parts) > 1 else ''
            
            # Download from S3
            response = self.s3.get_object(Bucket=bucket, Key=key)
            video_bytes = response['Body'].read()
            
            logger.info(f"Downloaded video from S3: {bucket}/{key} ({len(video_bytes)} bytes)")
            return video_bytes
            
        except Exception as e:
            logger.error(f"Failed to download video from S3: {e}")
            raise
    
    async def get_model_from_s3(self) -> bytes:
        """
        Download ML model from S3
        
        Returns:
            Model file bytes
        """
        try:
            response = self.s3.get_object(
                Bucket=settings.S3_BUCKET_MODELS,
                Key=settings.MODEL_S3_KEY
            )
            model_bytes = response['Body'].read()
            logger.info(f"Downloaded model from S3: {settings.MODEL_S3_KEY}")
            return model_bytes
            
        except Exception as e:
            logger.error(f"Failed to download model from S3: {e}")
            raise
    
    # ============= SQS OPERATIONS =============
    
    async def send_to_sqs(self, message: Dict[str, Any]) -> str:
        """
        Send message to SQS queue
        
        Args:
            message: Message payload (will be JSON serialized)
            
        Returns:
            Message ID
        """
        try:
            response = self.sqs.send_message(
                QueueUrl=settings.SQS_QUEUE_URL,
                MessageBody=json.dumps(message)
            )
            
            message_id = response['MessageId']
            logger.info(f"Sent message to SQS: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to send SQS message: {e}")
            raise
    
    async def receive_from_sqs(self) -> List[Dict[str, Any]]:
        """
        Receive messages from SQS queue (long polling)
        
        Returns:
            List of messages
        """
        try:
            response = self.sqs.receive_message(
                QueueUrl=settings.SQS_QUEUE_URL,
                MaxNumberOfMessages=settings.SQS_MAX_MESSAGES,
                WaitTimeSeconds=settings.SQS_WAIT_TIME_SECONDS,
                AttributeNames=['All'],
                MessageAttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            logger.info(f"Received {len(messages)} messages from SQS")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to receive SQS messages: {e}")
            raise
    
    async def delete_sqs_message(self, receipt_handle: str) -> None:
        """
        Delete message from SQS queue
        
        Args:
            receipt_handle: SQS receipt handle
        """
        try:
            self.sqs.delete_message(
                QueueUrl=settings.SQS_QUEUE_URL,
                ReceiptHandle=receipt_handle
            )
            logger.info("Deleted SQS message")
            
        except Exception as e:
            logger.error(f"Failed to delete SQS message: {e}")
            raise
    
    # ============= DYNAMODB OPERATIONS =============
    
    async def update_ai_session(
        self,
        session_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update AI session in DynamoDB
        
        Args:
            session_id: Session ID
            status: Status (processing, completed, failed)
            result: Processing result (optional)
        """
        try:
            table = self.dynamodb.Table(settings.DYNAMODB_TABLE_AI_SESSIONS)
            
            update_expr = "SET #status = :status, updatedAt = :updated"
            expr_values = {
                ':status': status,
                ':updated': datetime.utcnow().isoformat()
            }
            expr_names = {'#status': 'status'}
            
            if result:
                update_expr += ", #result = :result"
                expr_values[':result'] = result
                expr_names['#result'] = 'result'
            
            table.update_item(
                Key={'sessionId': session_id},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
                ExpressionAttributeNames=expr_names
            )
            
            logger.info(f"Updated AI session {session_id}: {status}")
            
        except Exception as e:
            logger.error(f"Failed to update AI session: {e}")
            raise
    
    async def get_ai_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get AI session from DynamoDB
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None
        """
        try:
            table = self.dynamodb.Table(settings.DYNAMODB_TABLE_AI_SESSIONS)
            response = table.get_item(Key={'sessionId': session_id})
            
            return response.get('Item')
            
        except Exception as e:
            logger.error(f"Failed to get AI session: {e}")
            raise


@lru_cache()
def get_aws_client() -> AWSClient:
    """Get cached AWS client instance"""
    return AWSClient()
