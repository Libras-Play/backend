"""# ml-service no usa SQLAlchemy/DynamoDB directamente

Pydantic models for ML Service# Los modelos de ML se cargan desde archivos .pth o desde S3

# Este archivo contiene helpers para el modelo de ML

Request/Response schemas for sign language recognition API
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# ============= ASSESSMENT REQUEST/RESPONSE =============

class AssessmentRequest(BaseModel):
    """Request for video assessment"""
    userId: str = Field(..., description="User identifier")
    exerciseId: int = Field(..., description="Exercise identifier")
    levelId: int = Field(..., description="Level identifier")
    s3VideoUrl: str = Field(..., description="S3 URL of video to analyze")
    
    model_config = ConfigDict(from_attributes=True)


class AssessmentResponse(BaseModel):
    """Response from video assessment"""
    sessionId: str = Field(..., description="AI session ID for tracking")
    status: str = Field(..., description="Processing status: queued, processing, completed, failed")
    message: str = Field(default="Video queued for processing")
    
    # These fields populated when status=completed
    recognizedGesture: Optional[str] = Field(None, description="Recognized sign/gesture label")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Model confidence score (0-1)")
    score: Optional[int] = Field(None, ge=0, le=100, description="User score (0-100)")
    processingTime: Optional[float] = Field(None, description="Processing time in seconds")
    modelVersion: Optional[str] = Field(None, description="Model version used")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    model_config = ConfigDict(from_attributes=True)


class AssessmentStatusRequest(BaseModel):
    """Request to check assessment status"""
    sessionId: str = Field(..., description="AI session ID")
    
    model_config = ConfigDict(from_attributes=True)


# ============= SAGEMAKER MODELS =============

class SageMakerInferenceRequest(BaseModel):
    """Request payload for SageMaker endpoint"""
    videoUrl: str
    preprocessingParams: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    model_config = ConfigDict(from_attributes=True)


class SageMakerInferenceResponse(BaseModel):
    """Response from SageMaker endpoint"""
    predictions: List[Dict[str, Any]]
    modelVersion: str
    
    model_config = ConfigDict(from_attributes=True)


# ============= SQS MESSAGE MODELS =============

class SQSVideoMessage(BaseModel):
    """SQS message for video processing"""
    sessionId: str = Field(..., description="AI session ID")
    userId: str
    exerciseId: int
    levelId: int
    s3VideoUrl: str
    timestamp: str
    
    model_config = ConfigDict(from_attributes=True)


class ProcessingResult(BaseModel):
    """Result of video processing"""
    sessionId: str
    status: str  # 'completed', 'failed'
    recognizedGesture: Optional[str] = None
    confidence: Optional[float] = None
    score: Optional[int] = None
    error: Optional[str] = None
    processingTime: float
    modelVersion: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(from_attributes=True)


# ============= MODEL METADATA =============

class ModelInfo(BaseModel):
    """Information about ML model"""
    modelId: str
    version: str
    s3Location: str
    framework: str  # 'tensorflow', 'pytorch', 'sagemaker'
    inputShape: List[int]
    outputClasses: List[str]
    accuracy: Optional[float] = None
    createdAt: str
    
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    modelLoaded: bool
    modelVersion: Optional[str] = None
    sagemakerEndpoint: Optional[str] = None
    useSagemaker: bool
    sqsQueueUrl: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============= ERROR MODELS =============

class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
