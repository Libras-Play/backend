"""
SageMaker Client for production inference

Handles SageMaker endpoint invocations
"""
import logging
import json
from typing import Dict, Any
import numpy as np

from app.config import get_settings
from app.aws_client import get_aws_client

logger = logging.getLogger(__name__)
settings = get_settings()


class SageMakerInferenceClient:
    """Client for SageMaker inference"""
    
    def __init__(self):
        """Initialize SageMaker client"""
        self.aws_client = get_aws_client()
        self.settings = settings
        logger.info(f"SageMaker client initialized (endpoint: {settings.SAGEMAKER_ENDPOINT_NAME})")
    
    async def predict(self, video_bytes: bytes) -> Dict[str, Any]:
        """
        Run inference on video using SageMaker endpoint
        
        Args:
            video_bytes: Video file bytes
            
        Returns:
            {
                'recognizedGesture': str,
                'confidence': float,
                'score': int,
                'modelVersion': str,
                'metadata': dict
            }
        """
        try:
            # Invoke SageMaker endpoint
            logger.info("Invoking SageMaker endpoint...")
            response = await self.aws_client.invoke_sagemaker_endpoint(video_bytes)
            
            # Parse SageMaker response
            # Expected format: {'predictions': [{'label': 'A', 'confidence': 0.95}], 'model_version': '1.0.0'}
            predictions = response.get('predictions', [])
            model_version = response.get('model_version', settings.MODEL_VERSION)
            
            if not predictions:
                raise ValueError("No predictions returned from SageMaker")
            
            # Get top prediction
            top_prediction = predictions[0]
            recognized_gesture = top_prediction.get('label', 'UNKNOWN')
            confidence = top_prediction.get('confidence', 0.0)
            
            # Calculate score (0-100 based on confidence)
            score = self._calculate_score(confidence)
            
            result = {
                'recognizedGesture': recognized_gesture,
                'confidence': confidence,
                'score': score,
                'modelVersion': model_version,
                'metadata': {
                    'endpoint': settings.SAGEMAKER_ENDPOINT_NAME,
                    'all_predictions': predictions[:5]  # Top 5
                }
            }
            
            logger.info(f"SageMaker prediction: {recognized_gesture} (confidence: {confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"SageMaker prediction failed: {e}")
            raise
    
    def _calculate_score(self, confidence: float) -> int:
        """
        Calculate user score from confidence
        
        Score mapping:
        - confidence >= 0.9: 100
        - confidence >= 0.8: 90
        - confidence >= 0.7: 80
        - confidence >= 0.6: 70
        - confidence >= 0.5: 60
        - confidence < 0.5: 0
        """
        if confidence >= 0.9:
            return 100
        elif confidence >= 0.8:
            return 90
        elif confidence >= 0.7:
            return 80
        elif confidence >= 0.6:
            return 70
        elif confidence >= 0.5:
            return 60
        else:
            return 0
    
    async def get_model_version(self) -> str:
        """
        Get model version from SageMaker endpoint metadata
        
        Returns:
            Model version string
        """
        # In production, this would query SageMaker endpoint config
        # For now, return from settings
        return settings.MODEL_VERSION


def get_sagemaker_client() -> SageMakerInferenceClient:
    """Get SageMaker inference client"""
    return SageMakerInferenceClient()
