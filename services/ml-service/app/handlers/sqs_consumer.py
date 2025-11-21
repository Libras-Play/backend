"""
SQS Consumer Worker

Background worker that processes video assessment requests from SQS queue
"""
import asyncio
import logging
import json
import time
from typing import Dict, Any
from datetime import datetime

from app.config import get_settings
from app.aws_client import get_aws_client
from app.models import SQSVideoMessage, ProcessingResult
from app.inference.sagemaker_client import get_sagemaker_client
from app.inference.local_stub import get_local_inference

logger = logging.getLogger(__name__)
settings = get_settings()


class SQSConsumer:
    """SQS consumer for video processing"""
    
    def __init__(self):
        """Initialize SQS consumer"""
        self.aws_client = get_aws_client()
        self.settings = settings
        self.running = False
        
        # Initialize inference client based on settings
        if settings.USE_SAGEMAKER:
            self.inference_client = get_sagemaker_client()
            logger.info("Using SageMaker for inference")
        else:
            self.inference_client = get_local_inference()
            logger.info("Using local stub for inference")
    
    async def start(self):
        """Start consuming messages from SQS"""
        self.running = True
        logger.info("Starting SQS consumer...")
        
        while self.running:
            try:
                # Receive messages (long polling)
                messages = await self.aws_client.receive_from_sqs()
                
                if messages:
                    logger.info(f"Processing {len(messages)} messages")
                    
                    # Process each message
                    for message in messages:
                        try:
                            await self._process_message(message)
                            
                            # Delete message after successful processing
                            await self.aws_client.delete_sqs_message(message['ReceiptHandle'])
                            
                        except Exception as e:
                            logger.error(f"Failed to process message: {e}")
                            # Message will be retried (visibility timeout)
                else:
                    # No messages, wait before next poll
                    await asyncio.sleep(settings.SQS_POLL_INTERVAL_SECONDS)
                    
            except Exception as e:
                logger.error(f"SQS consumer error: {e}")
                await asyncio.sleep(settings.SQS_POLL_INTERVAL_SECONDS)
    
    def stop(self):
        """Stop consuming messages"""
        logger.info("Stopping SQS consumer...")
        self.running = False
    
    async def _process_message(self, message: Dict[str, Any]):
        """
        Process a single SQS message
        
        Args:
            message: SQS message
        """
        try:
            # Parse message body
            body = json.loads(message['Body'])
            video_message = SQSVideoMessage(**body)
            
            logger.info(f"Processing session {video_message.sessionId}")
            
            # Update session status to 'processing'
            await self.aws_client.update_ai_session(
                session_id=video_message.sessionId,
                status='processing'
            )
            
            # Process video
            start_time = time.time()
            result = await self._process_video(video_message)
            processing_time = time.time() - start_time
            
            # Update result with processing time
            result.processingTime = processing_time
            
            # Save result to DynamoDB
            await self._save_result(result)
            
            logger.info(f"Completed session {video_message.sessionId} in {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Message processing failed: {e}")
            # Update session as failed
            if 'video_message' in locals():
                await self._save_error_result(video_message.sessionId, str(e))
            raise
    
    async def _process_video(self, video_message: SQSVideoMessage) -> ProcessingResult:
        """
        Process video and run inference
        
        Args:
            video_message: Video message from SQS
            
        Returns:
            Processing result
        """
        try:
            # Download video from S3
            logger.info(f"Downloading video: {video_message.s3VideoUrl}")
            video_bytes = await self.aws_client.download_video_from_s3(video_message.s3VideoUrl)
            
            # Validate video size
            if len(video_bytes) > settings.max_video_size_bytes:
                raise ValueError(f"Video too large: {len(video_bytes)} bytes (max: {settings.max_video_size_bytes})")
            
            # Run inference
            logger.info("Running inference...")
            inference_result = await self.inference_client.predict(video_bytes)
            
            # Create processing result
            result = ProcessingResult(
                sessionId=video_message.sessionId,
                status='completed',
                recognizedGesture=inference_result['recognizedGesture'],
                confidence=inference_result['confidence'],
                score=inference_result['score'],
                processingTime=0,  # Will be updated
                modelVersion=inference_result['modelVersion'],
                metadata={
                    **inference_result.get('metadata', {}),
                    'userId': video_message.userId,
                    'exerciseId': video_message.exerciseId,
                    'levelId': video_message.levelId,
                    'videoSize': len(video_bytes)
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            # Return failed result
            return ProcessingResult(
                sessionId=video_message.sessionId,
                status='failed',
                error=str(e),
                processingTime=0,
                modelVersion=self.inference_client.get_model_version() if hasattr(self.inference_client, 'get_model_version') else settings.MODEL_VERSION
            )
    
    async def _save_result(self, result: ProcessingResult):
        """
        Save processing result to DynamoDB
        
        Args:
            result: Processing result
        """
        try:
            # Prepare result data
            result_data = {
                'recognizedGesture': result.recognizedGesture,
                'confidence': result.confidence,
                'score': result.score,
                'processingTime': result.processingTime,
                'modelVersion': result.modelVersion,
                'metadata': result.metadata,
                'completedAt': datetime.utcnow().isoformat()
            }
            
            # Update DynamoDB
            await self.aws_client.update_ai_session(
                session_id=result.sessionId,
                status=result.status,
                result=result_data
            )
            
        except Exception as e:
            logger.error(f"Failed to save result: {e}")
            raise
    
    async def _save_error_result(self, session_id: str, error: str):
        """
        Save error result to DynamoDB
        
        Args:
            session_id: Session ID
            error: Error message
        """
        try:
            result_data = {
                'error': error,
                'failedAt': datetime.utcnow().isoformat()
            }
            
            await self.aws_client.update_ai_session(
                session_id=session_id,
                status='failed',
                result=result_data
            )
            
        except Exception as e:
            logger.error(f"Failed to save error result: {e}")


# Global consumer instance
_consumer = None


def get_consumer() -> SQSConsumer:
    """Get or create SQS consumer instance"""
    global _consumer
    if _consumer is None:
        _consumer = SQSConsumer()
    return _consumer


async def start_consumer():
    """Start SQS consumer in background"""
    consumer = get_consumer()
    await consumer.start()


def stop_consumer():
    """Stop SQS consumer"""
    consumer = get_consumer()
    consumer.stop()
