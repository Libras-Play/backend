"""
ML Service - Sign Language Recognition API

FastAPI application for video assessment with SageMaker/local inference
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import (
    AssessmentRequest,
    AssessmentResponse,
    AssessmentStatusRequest,
    HealthResponse,
    ErrorResponse
)
from app.aws_client import get_aws_client
from app.handlers.sqs_consumer import start_consumer, stop_consumer, get_consumer
from app.middleware import PathPrefixMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("=" * 80)
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"SageMaker Mode: {settings.USE_SAGEMAKER}")
    logger.info("=" * 80)
    
    # Initialize AWS client
    aws_client = get_aws_client()
    logger.info("AWS client initialized")
    
    # Start SQS consumer in background
    logger.info("Starting SQS consumer...")
    consumer_task = asyncio.create_task(start_consumer())
    
    yield
    
    # Shutdown
    logger.info("Shutting down ML Service...")
    stop_consumer()
    
    # Cancel consumer task
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    
    logger.info("ML Service stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Sign Language Recognition Service with SageMaker integration",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Path prefix middleware (for ALB path-based routing)
app.add_middleware(PathPrefixMiddleware, prefix="/ml")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ==================== HEALTH CHECK ====================

@app.get("/", tags=["Health"])
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint
    
    Returns service status and configuration
    """
    consumer = get_consumer()
    
    return HealthResponse(
        status="healthy",
        modelLoaded=True,  # Stub is always loaded
        modelVersion=settings.MODEL_VERSION,
        sagemakerEndpoint=settings.SAGEMAKER_ENDPOINT_NAME if settings.USE_SAGEMAKER else None,
        useSagemaker=settings.USE_SAGEMAKER,
        sqsQueueUrl=settings.SQS_QUEUE_URL
    )


# ==================== ASSESSMENT ENDPOINTS ====================

@app.post("/api/v1/assess", response_model=AssessmentResponse, tags=["Assessment"])
async def assess_video(request: AssessmentRequest):
    """
    Submit video for sign language assessment
    
    - **userId**: User identifier
    - **exerciseId**: Exercise identifier
    - **levelId**: Level identifier
    - **s3VideoUrl**: S3 URL of video to analyze (s3://bucket/key or https://...)
    
    Returns session ID and queues video for processing.
    Use GET /api/v1/assess/{sessionId} to check status.
    """
    try:
        aws_client = get_aws_client()
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Create SQS message
        message = {
            'sessionId': session_id,
            'userId': request.userId,
            'exerciseId': request.exerciseId,
            'levelId': request.levelId,
            's3VideoUrl': request.s3VideoUrl,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Send to SQS
        logger.info(f"Queueing assessment for user {request.userId}, exercise {request.exerciseId}")
        await aws_client.send_to_sqs(message)
        
        # Create initial AI session in DynamoDB
        await aws_client.update_ai_session(
            session_id=session_id,
            status='queued',
            result={
                'userId': request.userId,
                'exerciseId': request.exerciseId,
                'levelId': request.levelId,
                's3VideoUrl': request.s3VideoUrl,
                'queuedAt': datetime.utcnow().isoformat()
            }
        )
        
        return AssessmentResponse(
            sessionId=session_id,
            status='queued',
            message='Video queued for processing'
        )
        
    except Exception as e:
        logger.error(f"Failed to queue assessment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue assessment: {str(e)}"
        )


@app.get("/api/v1/assess/{session_id}", response_model=AssessmentResponse, tags=["Assessment"])
async def get_assessment_status(session_id: str):
    """
    Get assessment status and results
    
    - **session_id**: Session ID returned from POST /api/v1/assess
    
    Status values:
    - **queued**: Waiting in queue
    - **processing**: Video being processed
    - **completed**: Processing complete (includes results)
    - **failed**: Processing failed (includes error)
    """
    try:
        aws_client = get_aws_client()
        
        # Get session from DynamoDB
        session = await aws_client.get_ai_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}"
            )
        
        # Parse session data
        status_value = session.get('status', 'unknown')
        result = session.get('result', {})
        
        response = AssessmentResponse(
            sessionId=session_id,
            status=status_value,
            message=f"Assessment {status_value}"
        )
        
        # Add results if completed
        if status_value == 'completed' and result:
            response.recognizedGesture = result.get('recognizedGesture')
            response.confidence = result.get('confidence')
            response.score = result.get('score')
            response.processingTime = result.get('processingTime')
            response.modelVersion = result.get('modelVersion')
            response.metadata = result.get('metadata', {})
        
        # Add error if failed
        elif status_value == 'failed' and result:
            response.metadata = {'error': result.get('error')}
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get assessment status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get assessment status: {str(e)}"
        )


# ==================== ADMIN ENDPOINTS ====================

@app.get("/api/v1/model/info", tags=["Model"])
async def get_model_info():
    """
    Get information about the ML model
    
    Returns model version, configuration, and supported gestures
    """
    return {
        "modelVersion": settings.MODEL_VERSION,
        "framework": "TensorFlow Lite" if not settings.USE_SAGEMAKER else "SageMaker",
        "useSagemaker": settings.USE_SAGEMAKER,
        "sagemakerEndpoint": settings.SAGEMAKER_ENDPOINT_NAME if settings.USE_SAGEMAKER else None,
        "supportedGestures": settings.gesture_labels_list,
        "gestureCount": len(settings.gesture_labels_list),
        "confidenceThreshold": settings.CONFIDENCE_THRESHOLD,
        "maxVideoSizeMB": settings.MAX_VIDEO_SIZE_MB
    }


@app.get("/api/v1/consumer/status", tags=["Admin"])
async def get_consumer_status():
    """
    Get SQS consumer status
    
    Returns whether the background worker is running
    """
    consumer = get_consumer()
    return {
        "running": consumer.running,
        "queueUrl": settings.SQS_QUEUE_URL,
        "pollInterval": settings.SQS_POLL_INTERVAL_SECONDS
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )
