"""
FASE 8: Exercises Router - Endpoint de Selección Inteligente

Endpoint GET /exercise/next para seleccionar próximo ejercicio óptimo.

EVITA ERROR #1: No protected namespaces en schemas
EVITA ERROR #2: Validaciones estrictas de timestamps
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.core.db import get_db
from app.services.exercise_selector import ExerciseSelectorService
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/exercise-selector", tags=["Exercise Selector - FASE 8"])


# ========== SCHEMAS ==========

class ExerciseNextResponse(BaseModel):
    """
    Response del endpoint /exercise/next.
    
    EVITA ERROR #1: No usa protected namespace
    """
    exercise_id: int
    exercise_type: str  # 'test' | 'camera'
    title: dict  # JSONB multilanguage
    statement: dict  # JSONB multilanguage
    img_url: Optional[str] = None
    video_url: Optional[str] = None
    answers: Optional[dict] = None  # Solo si exercise_type='test'
    expected_sign: Optional[str] = None  # Solo si exercise_type='camera'
    difficulty: str  # 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED'
    selection_score: float = Field(ge=0.0, le=1.0)
    selection_reasons: dict  # Breakdown de scores por criterio
    next_recommendation: dict  # {type: str, message: str}
    
    class Config:
        json_schema_extra = {
            "example": {
                "exercise_id": 42,
                "exercise_type": "test",
                "title": {"en": "Alphabet Letter M", "pt": "Letra M do Alfabeto"},
                "statement": {"en": "Select the correct sign for M", "pt": "Selecione o sinal correto para M"},
                "img_url": "https://example.com/letter_m.jpg",
                "video_url": None,
                "answers": {"en": ["Option A", "Option B"], "pt": ["Opção A", "Opção B"]},
                "expected_sign": None,
                "difficulty": "BEGINNER",
                "selection_score": 0.78,
                "selection_reasons": {
                    "error_history_by_type": 0.75,
                    "error_by_specific_sign": 0.80,
                    "response_time": 0.65,
                    "user_level": 0.85,
                    "confidence": 0.70,
                    "thematic_weight": 0.50,
                    "anti_repetition": 0.50
                },
                "next_recommendation": {
                    "type": "practice_more",
                    "message": "Practice similar exercises to build confidence"
                }
            }
        }


class ExerciseAttemptRequest(BaseModel):
    """
    FUTURO: Request para registrar intento de ejercicio.
    
    EVITA ERROR #2: Validación estricta de timestamps
    """
    exercise_id: int
    user_id: str
    result: str = Field(pattern="^(success|fail)$")
    response_time_seconds: float = Field(ge=0.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    timestamp: str
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """
        Valida formato ISO8601.
        
        EVITA ERROR #2: Mismo patrón que FASE 7
        """
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError('timestamp must be in ISO8601 format')


# ========== ENDPOINTS ==========

@router.get("/next", response_model=ExerciseNextResponse)
async def get_next_exercise(
    user_id: str = Query(..., description="ID del usuario"),
    topic_id: int = Query(..., description="ID del topic"),
    difficulty: str = Query(..., pattern="^(BEGINNER|INTERMEDIATE|ADVANCED)$"),
    recent_exercises: Optional[str] = Query(
        None,
        description="IDs de ejercicios recientes (separados por coma): '1,2,3'"
    ),
    db: Session = Depends(get_db)
):
    """
    GET /next - Selecciona próximo ejercicio óptimo para el usuario.
    
    Implementa los 7 criterios de selección inteligente:
    1. Historial de errores por tipo (test vs camera)
    2. Errores por señal específica
    3. Tiempo de respuesta
    4. Nivel del usuario
    5. Confianza (confidence_score)
    6. Peso temático
    7. Anti-repetición
    
    Args:
        user_id: ID del usuario
        topic_id: ID del topic (ej: abecedario, números)
        difficulty: Nivel de dificultad
        recent_exercises: IDs de ejercicios recientes (opcional, para anti-repetición)
    
    Returns:
        ExerciseNextResponse con ejercicio seleccionado + metadata de selección
    
    EVITA ERROR #P: Query idempotente, no modifica estado
    """
    try:
        # Parse recent_exercises
        recent_ids = []
        if recent_exercises:
            try:
                recent_ids = [int(x.strip()) for x in recent_exercises.split(',')]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="recent_exercises must be comma-separated integers"
                )
        
        # Crear servicio de selección
        selector = ExerciseSelectorService(db)
        
        # Seleccionar próximo ejercicio
        result = await selector.select_next_exercise(
            user_id=user_id,
            topic_id=topic_id,
            difficulty=difficulty,
            recent_exercises=recent_ids
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No exercises found for topic_id={topic_id}, difficulty={difficulty}"
            )
        
        logger.info(
            f"Exercise selected: exercise_id={result['exercise_id']}, "
            f"score={result['selection_score']:.3f}, user={user_id}"
        )
        
        return ExerciseNextResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting next exercise: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/attempt")
async def record_attempt(
    request: ExerciseAttemptRequest,
    db: Session = Depends(get_db)
):
    """
    POST /attempt - Registra intento de ejercicio (FUTURO).
    
    FASE 8: Endpoint placeholder, implementación en futuras fases.
    
    EVITA ERROR #P: Operación idempotente (upsert en lugar de insert)
    """
    return {
        "status": "not_implemented",
        "message": "This endpoint will be implemented in future phases",
        "received_data": {
            "exercise_id": request.exercise_id,
            "user_id": request.user_id,
            "result": request.result
        }
    }
