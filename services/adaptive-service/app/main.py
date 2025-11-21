"""
Adaptive Service - FastAPI application

FASE 6: Sistema de Dificultad Adaptativa
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import adaptive
from app.schemas import HealthResponse
from app.ai_model.model_manager import get_model_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Adaptive Service",
    description="Sistema de Dificultad Adaptativa - Rule Engine + ML-ready",
    version=settings.VERSION,
    docs_url="/adaptive/api/docs",
    redoc_url="/adaptive/api/redoc",
    openapi_url="/adaptive/api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(adaptive.router)

# Health check
@app.get("/health", response_model=HealthResponse)
@app.get("/adaptive/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    model_manager = get_model_manager()
    
    return HealthResponse(
        status="healthy",
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
        ml_model_available=model_manager.is_model_available()
        # timestamp uses default_factory=datetime.utcnow from schema
    )


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.VERSION}")
    
    # Try to load ML model if enabled
    if settings.ML_MODEL_ENABLED:
        model_manager = get_model_manager()
        model_manager.load_model_if_exists()
    
    logger.info("Service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down service")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
