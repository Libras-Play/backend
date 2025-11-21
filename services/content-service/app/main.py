from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
import logging

from app.core.config import get_settings
from app.core.db import get_db, init_db, close_db
from app import crud, schemas, models, validators
from app.middleware import PathPrefixMiddleware
from app.routers import exercises as exercises_router
from app.routers import topics as topics_router

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación"""
    logger.info("Starting Content Service...")
    
    # Inicializar base de datos
    await init_db()
    logger.info("Database initialized")
    yield
    # Cleanup
    logger.info("Shutting down Content Service...")
    await close_db()


app = FastAPI(
    title="Content Service",
    description="Microservice for managing educational content",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Path prefix middleware (for ALB path-based routing)
app.add_middleware(PathPrefixMiddleware, prefix="/content")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== FASE 8: Registrar router de ejercicios ==========
app.include_router(exercises_router.router)

# ========== FASE 9: Registrar router de topic stats ==========
app.include_router(topics_router.router)


# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Debug endpoint to check database tables
@app.get("/debug/tables", tags=["Debug"])
async def list_tables(db: AsyncSession = Depends(get_db)):
    """List all tables in database"""
    try:
        result = await db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        tables = [row[0] for row in result.fetchall()]
        return {"tables": tables, "count": len(tables)}
    except Exception as e:
        return {"error": str(e), "tables": []}


# ==================== SIGN LANGUAGES ====================
@app.post("/api/v1/sign-languages", response_model=schemas.SignLanguage, status_code=status.HTTP_201_CREATED, tags=["Sign Languages"])
async def create_sign_language(
    sign_language: schemas.SignLanguageCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo lenguaje de señas"""
    existing = await crud.get_sign_language_by_code(db, sign_language.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sign language with code '{sign_language.code}' already exists"
        )
    return await crud.create_sign_language(db, sign_language)


@app.get("/api/v1/sign-languages", response_model=List[schemas.SignLanguage], tags=["Sign Languages"])
async def list_sign_languages(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Lista todos los lenguajes de señas"""
    return await crud.get_sign_languages(db, skip=skip, limit=limit)


@app.get("/api/v1/sign-languages/{sign_language_id}", response_model=schemas.SignLanguage, tags=["Sign Languages"])
async def get_sign_language(
    sign_language_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene un lenguaje de señas por ID"""
    sign_language = await crud.get_sign_language_by_id(db, sign_language_id)
    if not sign_language:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sign language with id {sign_language_id} not found"
        )
    return sign_language


@app.get("/api/v1/sign-languages/{sign_language_id}/topics", response_model=List[schemas.Topic], tags=["Sign Languages"])
async def list_topics_by_sign_language(
    sign_language_id: int,
    interfaceLanguage: str = "pt-BR",
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Lista tópicos de un lenguaje de señas con sus traducciones
    
    NOTA: Este endpoint retornará lista vacía hasta que se ejecute la migración 003.
    Después de la migración, retornará topics con sign_language_id y traducciones.
    """
    # Verificar que el sign language existe
    sign_language = await crud.get_sign_language_by_id(db, sign_language_id)
    if not sign_language:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sign language with id {sign_language_id} not found"
        )
    
    # Obtener topics para este sign language
    # TODO: Después de migración 003, filtrar por sign_language_id y cargar traducciones
    # Por ahora retornamos lista vacía hasta que se ejecute la migración 003
    return []


# ==================== LANGUAGES (UI Languages) ====================
@app.post("/api/v1/languages", response_model=schemas.Language, status_code=status.HTTP_201_CREATED, tags=["UI Languages"])
async def create_language(
    language: schemas.LanguageCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo idioma de interfaz de usuario (pt-BR, es-ES, en-US)"""
    existing = await crud.get_language_by_code(db, language.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Language with code '{language.code}' already exists"
        )
    return await crud.create_language(db, language)


@app.get("/api/v1/languages", response_model=List[schemas.Language], tags=["UI Languages"])
async def list_languages(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Lista todos los idiomas de interfaz de usuario"""
    return await crud.get_languages(db, skip=skip, limit=limit)


@app.get("/api/v1/languages/{language_id}", response_model=schemas.Language, tags=["UI Languages"])
async def get_language(
    language_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene un idioma de interfaz por ID"""
    language = await crud.get_language_by_id(db, language_id)
    if not language:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Language with id {language_id} not found"
        )
    return language


# ==================== TOPICS ====================
@app.post("/api/v1/topics", response_model=schemas.Topic, status_code=status.HTTP_201_CREATED, tags=["Topics"])
async def create_topic(
    topic: schemas.TopicCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo tema multilenguaje
    
    IMPORTANTE: Topics son universales y requieren traducciones en TODOS los idiomas (es, en, pt).
    """
    # NOTE: Validación de language_id eliminada - Topics son multilenguaje y universales
    return await crud.create_topic(db, topic)


@app.get("/api/v1/languages/{language_id}/topics", response_model=List[schemas.Topic], tags=["Topics"])
async def list_topics_by_language(
    language_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Lista temas de un idioma específico (sign language)"""
    return await crud.get_topics(db, sign_language_id=language_id, skip=skip, limit=limit)


@app.get("/api/v1/topics/{topic_id}", response_model=schemas.Topic, tags=["Topics"])
async def get_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene un tema por ID"""
    topic = await crud.get_topic_by_id(db, topic_id)
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic with id {topic_id} not found"
        )
    return topic


# ==================== EXERCISES ====================
# NOTA: Los niveles (easy, medium, hard) ahora son atributos embebidos en cada Topic.
# Ya no existen endpoints separados para Levels.
# Los exercises se filtran por topic_id + difficulty.
@app.post("/api/v1/topics/{topic_id}/exercises", response_model=schemas.Exercise, status_code=status.HTTP_201_CREATED, tags=["Exercises"])
async def create_exercise(
    topic_id: int,
    exercise: schemas.ExerciseCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo ejercicio en un tema con dificultad específica
    
    El ejercicio debe incluir:
    - topic_id: ID del tema (debe coincidir con el parámetro de ruta)
    - title: Título multilenguaje (JSONB con es, en, pt) - obligatorio
    - statement: Enunciado multilenguaje (JSONB con es, en, pt) - obligatorio
    - difficulty: 'easy', 'medium', o 'hard' (obligatorio)
    - exercise_type: 'test' o 'camera' (obligatorio)
    - learning_language: Código de lenguaje de señas (LSB, ASL, LSM) - validado contra tabla
    - img_url: URL de imagen (obligatorio)
    - answers: Array de opciones multilenguaje [{text: {...}, correct: bool}] si type='test'
    - expected_sign: Seña esperada si type='camera' (obligatorio para camera)
    """
    # Verificar que el topic existe
    topic = await crud.get_topic_by_id(db, topic_id)
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic with id {topic_id} not found"
        )
    
    # Verificar que el topic_id del body coincide con el de la ruta
    if exercise.topic_id != topic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Topic ID mismatch: URL has {topic_id}, body has {exercise.topic_id}"
        )
    
    # Validar que el lenguaje de señas existe en la base de datos
    if not await validators.validate_sign_language_exists(db, exercise.learning_language):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid sign language '{exercise.learning_language}'. "
                f"Must be one of the configured sign languages in the system (LSB, ASL, LSM, etc.)"
            )
        )
    
    return await crud.create_exercise(db, exercise)


@app.get("/api/v1/topics/{topic_id}/exercises", response_model=List[schemas.Exercise], tags=["Exercises"])
async def list_exercises_by_topic(
    topic_id: int,
    difficulty: str = None,  # Opcional: 'easy', 'medium', 'hard'
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Lista ejercicios de un tema específico
    
    Parámetros opcionales:
    - difficulty: Filtrar por dificultad ('easy', 'medium', 'hard')
    - skip: Número de registros a saltar (paginación)
    - limit: Límite de resultados por página
    
    Ejemplos:
    - GET /api/v1/topics/1/exercises → Todos los ejercicios del tema 1
    - GET /api/v1/topics/1/exercises?difficulty=easy → Solo ejercicios fáciles del tema 1
    """
    # Verificar que el topic existe
    topic = await crud.get_topic_by_id(db, topic_id)
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic with id {topic_id} not found"
        )
    
    # Validar difficulty si se proporciona
    if difficulty and difficulty not in ['easy', 'medium', 'hard']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid difficulty '{difficulty}'. Must be 'easy', 'medium', or 'hard'"
        )
    
    return await crud.get_exercises(db, topic_id=topic_id, difficulty=difficulty, skip=skip, limit=limit)


@app.get("/api/v1/exercises/{exercise_id}", response_model=schemas.Exercise, tags=["Exercises"])
async def get_exercise(
    exercise_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene un ejercicio por ID"""
    exercise = await crud.get_exercise_by_id(db, exercise_id)
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise with id {exercise_id} not found"
        )
    return exercise


# ==================== TRANSLATIONS (i18n) ====================
@app.post("/api/v1/translations", response_model=schemas.Translation, status_code=status.HTTP_201_CREATED, tags=["Translations"])
async def create_translation(
    translation: schemas.TranslationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crea una traducción i18n"""
    language = await crud.get_language_by_id(db, translation.language_id)
    if not language:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Language with id {translation.language_id} not found"
        )
    return await crud.create_translation(db, translation)


@app.get("/api/v1/languages/{language_id}/translations", response_model=List[schemas.Translation], tags=["Translations"])
async def list_translations_by_language(
    language_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Lista todas las traducciones de un idioma"""
    return await crud.get_translations_by_language(db, language_id)


# ============================================================================
# MISSION TEMPLATES - FASE 4
# ============================================================================

@app.get("/api/v1/mission-templates", response_model=schemas.MissionTemplateListResponse, tags=["Mission Templates"])
async def get_mission_templates(
    active_only: bool = True,
    learning_language: str | None = None,
    metric_type: str | None = None,
    difficulty: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Obtener lista de plantillas de misiones con filtros opcionales"""
    return await crud.get_mission_templates(
        db,
        active_only=active_only,
        learning_language=learning_language,
        metric_type=metric_type,
        difficulty=difficulty,
        page=page,
        page_size=page_size
    )


@app.get("/api/v1/mission-templates/{template_id}", response_model=schemas.MissionTemplateResponse, tags=["Mission Templates"])
async def get_mission_template(
    template_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtener una plantilla específica por ID"""
    template = await crud.get_mission_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Mission template {template_id} not found")
    return template


@app.post("/api/v1/mission-templates", response_model=schemas.MissionTemplateResponse, status_code=status.HTTP_201_CREATED, tags=["Mission Templates"])
async def create_mission_template(
    template_data: schemas.MissionTemplateCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crear nueva plantilla de misión"""
    return await crud.create_mission_template(db, template_data)


@app.put("/api/v1/mission-templates/{template_id}", response_model=schemas.MissionTemplateResponse, tags=["Mission Templates"])
async def update_mission_template(
    template_id: int,
    template_data: schemas.MissionTemplateUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Actualizar plantilla de misión existente"""
    template = await crud.update_mission_template(db, template_id, template_data)
    if not template:
        raise HTTPException(status_code=404, detail=f"Mission template {template_id} not found")
    return template


@app.delete("/api/v1/mission-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Mission Templates"])
async def delete_mission_template(
    template_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Eliminar plantilla de misión"""
    deleted = await crud.delete_mission_template(db, template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Mission template {template_id} not found")
    return None


# ============================================================================
# FASE 5: BADGES / ACHIEVEMENTS ENDPOINTS
# ============================================================================

@app.get("/api/v1/badges", tags=["Badges"])
async def get_badges(
    learning_language: str = None,
    badge_type: str = None,
    rarity: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all badge definitions.
    
    ANTI-ERROR: Simple filters, no array operations
    """
    try:
        from sqlalchemy import select
        from app.models import BadgeMaster
        
        # Build query
        query = select(BadgeMaster)
        
        # Simple filters
        if learning_language:
            query = query.where(BadgeMaster.learning_language == learning_language)
        if badge_type:
            query = query.where(BadgeMaster.type == badge_type)
        if rarity:
            query = query.where(BadgeMaster.rarity == rarity)
        
        query = query.order_by(BadgeMaster.order_index)
        
        result = await db.execute(query)
        badges = result.scalars().all()
        
        # Convert to dict
        response = []
        for badge in badges:
            response.append({
                'badge_id': badge.badge_id,
                'type': badge.type,
                'title': badge.title,
                'description': badge.description,
                'icon_url': badge.icon_url,
                'conditions': badge.conditions,
                'learning_language': badge.learning_language,
                'is_hidden': badge.is_hidden,
                'rarity': badge.rarity,
                'order_index': badge.order_index,
                'created_at': badge.created_at.isoformat() if badge.created_at else None,
                'updated_at': badge.updated_at.isoformat() if badge.updated_at else None
            })
        
        logger.info(f"Retrieved {len(response)} badges")
        return response
        
    except Exception as e:
        logger.error(f"Error fetching badges: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/badges/{badge_id}", tags=["Badges"])
async def get_badge(
    badge_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific badge by ID"""
    try:
        from sqlalchemy import select
        from app.models import BadgeMaster
        
        query = select(BadgeMaster).where(BadgeMaster.badge_id == badge_id)
        result = await db.execute(query)
        badge = result.scalar_one_or_none()
        
        if not badge:
            raise HTTPException(status_code=404, detail="Badge not found")
        
        return {
            'badge_id': badge.badge_id,
            'type': badge.type,
            'title': badge.title,
            'description': badge.description,
            'icon_url': badge.icon_url,
            'conditions': badge.conditions,
            'learning_language': badge.learning_language,
            'is_hidden': badge.is_hidden,
            'rarity': badge.rarity,
            'order_index': badge.order_index,
            'created_at': badge.created_at.isoformat() if badge.created_at else None,
            'updated_at': badge.updated_at.isoformat() if badge.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching badge {badge_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/badges", tags=["Badges"])
async def create_badge(
    badge_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create a new badge"""
    try:
        import uuid
        from app.models import BadgeMaster
        
        # Generate ID if not provided
        badge_id = badge_data.get('badge_id') or str(uuid.uuid4())
        
        new_badge = BadgeMaster(
            badge_id=badge_id,
            type=badge_data['type'],
            title=badge_data['title'],
            description=badge_data['description'],
            icon_url=badge_data['icon_url'],
            conditions=badge_data['conditions'],
            learning_language=badge_data['learning_language'],
            is_hidden=badge_data.get('is_hidden', False),
            rarity=badge_data.get('rarity', 'common'),
            order_index=badge_data.get('order_index', 0)
        )
        
        db.add(new_badge)
        await db.commit()
        await db.refresh(new_badge)
        
        logger.info(f"Created badge: {badge_id}")
        
        return {
            'badge_id': new_badge.badge_id,
            'message': 'Badge created successfully'
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating badge: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
