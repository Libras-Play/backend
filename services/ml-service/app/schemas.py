from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class PredictionType(str, Enum):
    """Tipos de predicción"""
    IMAGE = "image"
    VIDEO = "video"
    REALTIME = "realtime"


class SignPrediction(BaseModel):
    """Predicción de una seña"""
    sign_id: str
    sign_name: str
    confidence: float = Field(..., ge=0, le=1)
    metadata: Optional[Dict[str, Any]] = None


class PredictionRequest(BaseModel):
    """Request para hacer una predicción"""
    type: PredictionType
    data: Optional[str] = None  # Base64 encoded image/video
    url: Optional[str] = None   # URL de S3 de la imagen/video
    language_code: str = "ASL"  # Código del lenguaje de señas
    top_k: int = Field(default=5, ge=1, le=20)  # Top K predicciones


class PredictionResponse(BaseModel):
    """Respuesta de predicción"""
    success: bool = True
    predictions: List[SignPrediction]
    processing_time_ms: float
    model_version: str = "1.0.0"
    metadata: Optional[Dict[str, Any]] = None


class HandLandmarks(BaseModel):
    """Landmarks de una mano detectada"""
    landmarks: List[Dict[str, float]]  # x, y, z para cada landmark
    handedness: str  # "Left" o "Right"
    confidence: float


class HandDetectionResponse(BaseModel):
    """Respuesta de detección de manos"""
    success: bool = True
    hands_detected: int
    hands: List[HandLandmarks]
    processing_time_ms: float


class ModelInfo(BaseModel):
    """Información del modelo de ML"""
    name: str
    version: str
    framework: str  # "pytorch", "tensorflow", etc.
    input_shape: List[int]
    num_classes: int
    labels: List[str]
    last_updated: str


class TrainingRequest(BaseModel):
    """Request para entrenar/fine-tune modelo (futuro)"""
    dataset_url: str
    language_code: str
    epochs: int = 10
    batch_size: int = 32
    learning_rate: float = 0.001


# API Response wrapper
class APIResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: Optional[Any] = None
