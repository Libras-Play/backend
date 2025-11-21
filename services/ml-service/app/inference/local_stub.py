"""
Local stub inference for development

Simulates ML inference without actual model for testing
Can be extended with real TFLite model
"""
import logging
import random
import time
import hashlib
from typing import Dict, Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LocalStubInference:
    """Local stub for ML inference (development mode)"""
    
    def __init__(self):
        """Initialize local inference stub"""
        self.settings = settings
        self.gesture_labels = settings.gesture_labels_list
        self.model_loaded = True  # Simulated
        logger.info(f"Local stub inference initialized ({len(self.gesture_labels)} gestures)")
    
    async def predict(self, video_bytes: bytes) -> Dict[str, Any]:
        """
        Simulate inference on video (deterministic based on video hash)
        
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
            # Simulate processing delay
            await self._simulate_processing()
            
            # Generate deterministic prediction based on video hash
            video_hash = hashlib.md5(video_bytes).hexdigest()
            seed = int(video_hash[:8], 16)
            random.seed(seed)
            
            # Pick a gesture (deterministic for same video)
            recognized_gesture = random.choice(self.gesture_labels)
            
            # Generate confidence (0.5 to 1.0)
            confidence = random.uniform(0.5, 1.0)
            
            # Calculate score
            score = self._calculate_score(confidence)
            
            result = {
                'recognizedGesture': recognized_gesture,
                'confidence': round(confidence, 3),
                'score': score,
                'modelVersion': f"{settings.MODEL_VERSION}-stub",
                'metadata': {
                    'mode': 'local_stub',
                    'video_size': len(video_bytes),
                    'video_hash': video_hash[:8],
                    'alternative_predictions': self._get_alternatives(seed, recognized_gesture)
                }
            }
            
            logger.info(f"Stub prediction: {recognized_gesture} (confidence: {confidence:.3f}, score: {score})")
            return result
            
        except Exception as e:
            logger.error(f"Stub prediction failed: {e}")
            raise
    
    async def _simulate_processing(self):
        """Simulate processing delay (50-200ms)"""
        delay = random.uniform(0.05, 0.2)
        time.sleep(delay)
    
    def _calculate_score(self, confidence: float) -> int:
        """
        Calculate user score from confidence
        
        Same logic as SageMaker client for consistency
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
    
    def _get_alternatives(self, seed: int, top_gesture: str) -> list:
        """Generate alternative predictions"""
        random.seed(seed + 1)
        alternatives = [g for g in self.gesture_labels if g != top_gesture]
        random.shuffle(alternatives)
        
        return [
            {'gesture': alternatives[0], 'confidence': random.uniform(0.3, 0.5)},
            {'gesture': alternatives[1], 'confidence': random.uniform(0.2, 0.4)},
            {'gesture': alternatives[2], 'confidence': random.uniform(0.1, 0.3)}
        ]
    
    def get_model_version(self) -> str:
        """Get stub model version"""
        return f"{settings.MODEL_VERSION}-stub"
    
    def is_model_loaded(self) -> bool:
        """Check if model is loaded (always true for stub)"""
        return self.model_loaded


# ============= TFLITE EXTENSION (OPTIONAL) =============

class TFLiteInference(LocalStubInference):
    """
    Real TFLite inference (optional extension)
    
    To use:
    1. Install: pip install tensorflow-lite
    2. Download model to MODEL_LOCAL_PATH
    3. Implement load_model() and _run_tflite_inference()
    """
    
    def __init__(self):
        """Initialize TFLite inference"""
        super().__init__()
        self.interpreter = None
        self.model_loaded = False
        
        # Attempt to load model
        try:
            self._load_model()
        except Exception as e:
            logger.warning(f"TFLite model not loaded, using stub: {e}")
    
    def _load_model(self):
        """Load TFLite model"""
        # Uncomment when TFLite is available:
        # import tensorflow as tf
        # self.interpreter = tf.lite.Interpreter(model_path=settings.MODEL_LOCAL_PATH)
        # self.interpreter.allocate_tensors()
        # self.model_loaded = True
        # logger.info(f"TFLite model loaded: {settings.MODEL_LOCAL_PATH}")
        pass
    
    async def predict(self, video_bytes: bytes) -> Dict[str, Any]:
        """Run inference with TFLite or fallback to stub"""
        if self.model_loaded and self.interpreter:
            return await self._run_tflite_inference(video_bytes)
        else:
            # Fallback to stub
            return await super().predict(video_bytes)
    
    async def _run_tflite_inference(self, video_bytes: bytes) -> Dict[str, Any]:
        """
        Run actual TFLite inference
        
        Steps:
        1. Extract frames from video
        2. Preprocess frames (resize, normalize)
        3. Run inference
        4. Postprocess predictions
        """
        # TODO: Implement real TFLite inference
        # For now, fallback to stub
        return await super().predict(video_bytes)


def get_local_inference() -> LocalStubInference:
    """Get local inference client (stub or TFLite)"""
    # To use TFLite, change to: return TFLiteInference()
    return LocalStubInference()
