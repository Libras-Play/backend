"""
AWS Client for S3 uploads and SNS notifications
"""
import boto3
import logging
from typing import Optional, BinaryIO
from datetime import datetime
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class AWSClient:
    """AWS services client wrapper"""
    
    def __init__(self):
        self.settings = settings
        self._s3_client = None
        self._sns_client = None
        self._dynamodb_client = None
    
    @property
    def s3(self):
        """Lazy initialization of S3 client"""
        if self._s3_client is None:
            kwargs = {
                'region_name': self.settings.AWS_REGION,
                'aws_access_key_id': self.settings.AWS_ACCESS_KEY_ID,
                'aws_secret_access_key': self.settings.AWS_SECRET_ACCESS_KEY,
            }
            if self.settings.S3_ENDPOINT:
                kwargs['endpoint_url'] = self.settings.S3_ENDPOINT
            
            self._s3_client = boto3.client('s3', **kwargs)
        return self._s3_client
    
    @property
    def sns(self):
        """Lazy initialization of SNS client"""
        if self._sns_client is None:
            self._sns_client = boto3.client(
                'sns',
                region_name=self.settings.AWS_REGION,
                aws_access_key_id=self.settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.settings.AWS_SECRET_ACCESS_KEY,
            )
        return self._sns_client
    
    @property
    def dynamodb(self):
        """Lazy initialization of DynamoDB client"""
        if self._dynamodb_client is None:
            kwargs = {
                'region_name': self.settings.AWS_REGION
            }
            if hasattr(self.settings, 'DYNAMODB_ENDPOINT') and self.settings.DYNAMODB_ENDPOINT:
                kwargs['endpoint_url'] = self.settings.DYNAMODB_ENDPOINT
            if self.settings.AWS_ACCESS_KEY_ID:
                kwargs['aws_access_key_id'] = self.settings.AWS_ACCESS_KEY_ID
            if self.settings.AWS_SECRET_ACCESS_KEY:
                kwargs['aws_secret_access_key'] = self.settings.AWS_SECRET_ACCESS_KEY
            
            self._dynamodb_client = boto3.client('dynamodb', **kwargs)
        return self._dynamodb_client
    
    async def upload_user_media(
        self,
        user_id: str,
        file: BinaryIO,
        filename: str,
        content_type: str = "video/mp4"
    ) -> str:
        """
        Upload user media (video, image) to S3
        
        Args:
            user_id: User identifier
            file: File-like object to upload
            filename: Original filename
            content_type: MIME type
            
        Returns:
            S3 URL of uploaded file
        """
        try:
            # Generate unique key
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            key = f"users/{user_id}/media/{timestamp}_{filename}"
            
            # Upload to S3
            self.s3.upload_fileobj(
                file,
                self.settings.S3_BUCKET,
                key,
                ExtraArgs={'ContentType': content_type}
            )
            
            # Generate URL
            if self.settings.S3_ENDPOINT:
                # LocalStack URL
                url = f"{self.settings.S3_ENDPOINT}/{self.settings.S3_BUCKET}/{key}"
            else:
                # AWS URL
                url = f"https://{self.settings.S3_BUCKET}.s3.{self.settings.AWS_REGION}.amazonaws.com/{key}"
            
            logger.info(f"Uploaded media for user {user_id}: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Error uploading media: {str(e)}")
            raise
    
    async def publish_notification(
        self,
        message: str,
        subject: Optional[str] = None,
        attributes: Optional[dict] = None
    ) -> Optional[str]:
        """
        Publish notification to SNS topic
        
        Args:
            message: Notification message
            subject: Message subject (optional)
            attributes: Message attributes (optional)
            
        Returns:
            Message ID if published successfully
        """
        if not self.settings.SNS_TOPIC_ARN:
            logger.warning("SNS_TOPIC_ARN not configured, skipping notification")
            return None
        
        try:
            kwargs = {
                'TopicArn': self.settings.SNS_TOPIC_ARN,
                'Message': message,
            }
            
            if subject:
                kwargs['Subject'] = subject
            
            if attributes:
                kwargs['MessageAttributes'] = {
                    k: {'DataType': 'String', 'StringValue': str(v)}
                    for k, v in attributes.items()
                }
            
            response = self.sns.publish(**kwargs)
            message_id = response['MessageId']
            
            logger.info(f"Published SNS notification: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Error publishing notification: {str(e)}")
            return None
    
    async def notify_level_up(self, user_id: str, new_level: int):
        """Send level up notification"""
        await self.publish_notification(
            message=f"¡Felicitaciones! Has alcanzado el nivel {new_level}",
            subject="¡Nuevo Nivel!",
            attributes={
                'user_id': user_id,
                'event_type': 'level_up',
                'new_level': str(new_level)
            }
        )
    
    async def notify_achievement(self, user_id: str, achievement_code: str):
        """Send achievement unlocked notification"""
        await self.publish_notification(
            message=f"¡Has desbloqueado un nuevo logro: {achievement_code}!",
            subject="¡Nuevo Logro!",
            attributes={
                'user_id': user_id,
                'event_type': 'achievement',
                'achievement_code': achievement_code
            }
        )
    
    async def notify_streak_milestone(self, user_id: str, streak_days: int):
        """Send streak milestone notification"""
        await self.publish_notification(
            message=f"¡Increíble! Llevas {streak_days} días consecutivos practicando",
            subject="¡Racha Activa!",
            attributes={
                'user_id': user_id,
                'event_type': 'streak_milestone',
                'streak_days': str(streak_days)
            }
        )


# Global instance
aws_client = AWSClient()
