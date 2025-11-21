"""
CRUD operations para content-service
Todas las funciones son async y usan SQLAlchemy AsyncSession
"""
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas


# ==================== SIGN LANGUAGES ====================

async def get_sign_languages(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[models.SignLanguage]:
    """Obtener todos los lenguajes de señas disponibles"""
    result = await db.execute(select(models.SignLanguage).offset(skip).limit(limit).order_by(models.SignLanguage.name))
    return result.scalars().all()


async def get_sign_language_by_id(db: AsyncSession, sign_language_id: int) -> Optional[models.SignLanguage]:
    """Obtener un lenguaje de señas por ID"""
    result = await db.execute(select(models.SignLanguage).where(models.SignLanguage.id == sign_language_id))
    return result.scalar_one_or_none()


async def get_sign_language_by_code(db: AsyncSession, code: str) -> Optional[models.SignLanguage]:
    """Obtener un lenguaje de señas por código"""
    result = await db.execute(select(models.SignLanguage).where(models.SignLanguage.code == code))
    return result.scalar_one_or_none()


async def create_sign_language(db: AsyncSession, sign_language: schemas.SignLanguageCreate) -> models.SignLanguage:
    """Crear un nuevo lenguaje de señas"""
    db_sign_language = models.SignLanguage(**sign_language.model_dump())
    db.add(db_sign_language)
    await db.commit()
    await db.refresh(db_sign_language)
    return db_sign_language


# ==================== LANGUAGES (UI Languages) ====================

async def get_languages(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[models.Language]:
    """Obtener todos los lenguajes de señas disponibles"""
    result = await db.execute(select(models.Language).offset(skip).limit(limit).order_by(models.Language.name))
    return result.scalars().all()


async def get_language_by_id(db: AsyncSession, language_id: int) -> Optional[models.Language]:
    """Obtener un lenguaje por ID"""
    result = await db.execute(select(models.Language).where(models.Language.id == language_id))
    return result.scalar_one_or_none()


async def get_language_by_code(db: AsyncSession, code: str) -> Optional[models.Language]:
    """Obtener un lenguaje por código"""
    result = await db.execute(select(models.Language).where(models.Language.code == code))
    return result.scalar_one_or_none()


async def create_language(db: AsyncSession, language: schemas.LanguageCreate) -> models.Language:
    """Crear un nuevo lenguaje de señas"""
    db_language = models.Language(**language.model_dump())
    db.add(db_language)
    await db.commit()
    await db.refresh(db_language)
    return db_language


# ==================== TOPICS ====================

async def get_topics(db: AsyncSession, sign_language_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[models.Topic]:
    """Obtener topics (todos son multilenguaje, sign_language_id ignorado)"""
    query = select(models.Topic)
    # NOTE: sign_language_id ya no se usa - Topics son universales con traducciones multilenguaje
    query = query.order_by(models.Topic.order_index).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_topic_by_id(db: AsyncSession, topic_id: int) -> Optional[models.Topic]:
    """Obtener un topic por ID"""
    result = await db.execute(select(models.Topic).where(models.Topic.id == topic_id))
    return result.scalar_one_or_none()


async def create_topic(db: AsyncSession, topic: schemas.TopicCreate) -> models.Topic:
    """
    Crear un nuevo topic multilenguaje.
    IMPORTANTE: title y description deben tener traducciones en todos los idiomas (es, en, pt).
    """
    # NOTE: DEFAULT_LEVELS eliminado - columna levels no existe actualmente en DB
    topic_data = topic.model_dump()
    
    db_topic = models.Topic(**topic_data)
    db.add(db_topic)
    await db.commit()
    await db.refresh(db_topic)
    return db_topic


# ==================== EXERCISES ====================

async def get_exercises(
    db: AsyncSession, 
    topic_id: Optional[int] = None,
    difficulty: Optional[str] = None,
    skip: int = 0, 
    limit: int = 100
) -> List[models.Exercise]:
    """
    Obtener exercises con filtros opcionales por topic y difficulty.
    difficulty puede ser: 'easy', 'medium', 'hard'
    """
    query = select(models.Exercise)
    
    if topic_id:
        query = query.where(models.Exercise.topic_id == topic_id)
    
    if difficulty:
        query = query.where(models.Exercise.difficulty == difficulty)
    
    query = query.order_by(models.Exercise.order_index).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_exercises_by_topic(db: AsyncSession, topic_id: int) -> List[models.Exercise]:
    """Obtener todos los exercises de un topic específico"""
    return await get_exercises(db, topic_id=topic_id, limit=1000)


async def get_exercises_by_topic_and_difficulty(
    db: AsyncSession, 
    topic_id: int, 
    difficulty: str
) -> List[models.Exercise]:
    """Obtener exercises de un topic filtrados por dificultad"""
    return await get_exercises(db, topic_id=topic_id, difficulty=difficulty, limit=1000)


async def get_exercise_by_id(db: AsyncSession, exercise_id: int) -> Optional[models.Exercise]:
    """Obtener un exercise por ID"""
    result = await db.execute(select(models.Exercise).where(models.Exercise.id == exercise_id))
    return result.scalar_one_or_none()


async def create_exercise(db: AsyncSession, exercise: schemas.ExerciseCreate) -> models.Exercise:
    """
    Crear un nuevo exercise.
    Requiere topic_id y difficulty (easy/medium/hard).
    """
    db_exercise = models.Exercise(**exercise.model_dump())
    db.add(db_exercise)
    await db.commit()
    await db.refresh(db_exercise)
    return db_exercise


# ==================== TRANSLATIONS ====================

async def get_translations(db: AsyncSession, language_id: Optional[int] = None, skip: int = 0, limit: int = 1000) -> List[models.Translation]:
    """Obtener translations con filtros opcionales"""
    query = select(models.Translation)
    if language_id:
        query = query.where(models.Translation.language_id == language_id)
    query = query.order_by(models.Translation.key).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_translations_by_lang(db: AsyncSession, language_id: int) -> List[models.Translation]:
    """Obtener todas las translations de un lenguaje específico"""
    return await get_translations(db, language_id=language_id, limit=10000)


async def create_translation(db: AsyncSession, translation: schemas.TranslationCreate) -> models.Translation:
    """Crear una nueva translation"""
    db_translation = models.Translation(**translation.model_dump())
    db.add(db_translation)
    await db.commit()
    await db.refresh(db_translation)
    return db_translation


# ==================== ACHIEVEMENTS ====================

async def get_achievements(db: AsyncSession, skip: int = 0, limit: int = 100):
    """Obtener todos los achievements"""
    result = await db.execute(select(models.Achievement).offset(skip).limit(limit).order_by(models.Achievement.condition_value))
    return result.scalars().all()


async def get_achievement_by_code(db: AsyncSession, code: str) -> Optional[models.Achievement]:
    """Obtener un achievement por código"""
    result = await db.execute(select(models.Achievement).where(models.Achievement.code == code))
    return result.scalar_one_or_none()


async def create_achievement(db: AsyncSession, achievement: schemas.AchievementCreate) -> models.Achievement:
    """Crear un nuevo achievement"""
    db_achievement = models.Achievement(**achievement.model_dump())
    db.add(db_achievement)
    await db.commit()
    await db.refresh(db_achievement)
    return db_achievement


# ============================================================================
# MISSION TEMPLATES - FASE 4
# ============================================================================

async def get_mission_templates(
    db: AsyncSession,
    active_only: bool = True,
    learning_language: str | None = None,
    metric_type: str | None = None,
    difficulty: str | None = None,
    page: int = 1,
    page_size: int = 50
) -> schemas.MissionTemplateListResponse:
    """
    Obtener lista de mission templates con filtros
    
    Args:
        learning_language: Si se especifica, retorna templates que:
            - Tienen learning_languages vacío (aplican a todos), o
            - Contienen el learning_language especificado
    """
    from sqlalchemy import select, func, or_, and_
    from app.models import MissionTemplate
    
    # Build query
    query = select(MissionTemplate)
    
    conditions = []
    if active_only:
        conditions.append(MissionTemplate.active == True)
    
    if metric_type:
        conditions.append(MissionTemplate.metric_type == metric_type)
    
    if difficulty:
        # Include templates with matching difficulty OR null (applies to all)
        conditions.append(
            or_(
                MissionTemplate.difficulty == difficulty,
                MissionTemplate.difficulty == None
            )
        )
    
    if learning_language:
        # Filter by:
        # 1. learning_languages is empty array (applies to all)
        # 2. learning_language is in the array
        conditions.append(
            or_(
                MissionTemplate.learning_languages == [],
                MissionTemplate.learning_languages.contains([learning_language])
            )
        )
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Count total
    count_query = select(func.count()).select_from(MissionTemplate)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(
        MissionTemplate.priority.desc(),
        MissionTemplate.id
    ).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return schemas.MissionTemplateListResponse(
        templates=[schemas.MissionTemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=page,
        page_size=page_size
    )


async def get_mission_template(db: AsyncSession, template_id: int):
    """Get mission template by ID"""
    from sqlalchemy import select
    from app.models import MissionTemplate
    
    result = await db.execute(
        select(MissionTemplate).where(MissionTemplate.id == template_id)
    )
    return result.scalar_one_or_none()


async def create_mission_template(db: AsyncSession, template_data: schemas.MissionTemplateCreate):
    """Create new mission template"""
    from app.models import MissionTemplate, MetricType
    from sqlalchemy import select
    
    # Check if code already exists
    existing = await db.execute(
        select(MissionTemplate).where(MissionTemplate.code == template_data.code)
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"Mission template with code '{template_data.code}' already exists")
    
    # Use execute with bindparams() for proper parameter handling
    from sqlalchemy.sql import text as sql_text, bindparam
    import json
    
    insert_sql = sql_text("""
        INSERT INTO mission_templates 
        (code, title, description, learning_languages, metric_type, metric_value, 
         difficulty, reward_coins, reward_xp, reward_gems, image_url, active, priority)
        VALUES 
        (:code, cast(:title as jsonb), cast(:description as jsonb), :learning_languages, 
         cast(:metric_type as metric_type_enum), :metric_value,
         :difficulty, :reward_coins, :reward_xp, :reward_gems, :image_url, :active, :priority)
        RETURNING id, created_at, updated_at
    """).bindparams(
        bindparam('code'),
        bindparam('title'),
        bindparam('description'),
        bindparam('learning_languages'),
        bindparam('metric_type'),
        bindparam('metric_value'),
        bindparam('difficulty'),
        bindparam('reward_coins'),
        bindparam('reward_xp'),
        bindparam('reward_gems'),
        bindparam('image_url'),
        bindparam('active'),
        bindparam('priority')
    )
    
    result = await db.execute(insert_sql, {
        'code': template_data.code,
        'title': json.dumps(template_data.title.model_dump()),
        'description': json.dumps(template_data.description.model_dump()),
        'learning_languages': template_data.learning_languages,
        'metric_type': template_data.metric_type.value if isinstance(template_data.metric_type, MetricType) else template_data.metric_type,
        'metric_value': template_data.metric_value,
        'difficulty': template_data.difficulty,
        'reward_coins': template_data.reward_coins,
        'reward_xp': template_data.reward_xp,
        'reward_gems': template_data.reward_gems,
        'image_url': template_data.image_url,
        'active': True,
        'priority': template_data.priority
    })
    
    row = result.one()
    await db.commit()
    
    # Fetch the complete object
    result = await db.execute(
        select(MissionTemplate).where(MissionTemplate.id == row.id)
    )
    new_template = result.scalar_one()
    
    return schemas.MissionTemplateResponse.model_validate(new_template)


async def update_mission_template(
    db: AsyncSession,
    template_id: int,
    template_data: schemas.MissionTemplateUpdate
):
    """Update mission template"""
    from app.models import MissionTemplate
    from sqlalchemy import select
    
    result = await db.execute(
        select(MissionTemplate).where(MissionTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        return None
    
    # Update only provided fields
    update_data = template_data.model_dump(exclude_unset=True)
    
    # Convert Pydantic models to dict for JSONB fields
    if 'title' in update_data and update_data['title']:
        update_data['title'] = update_data['title']
    if 'description' in update_data and update_data['description']:
        update_data['description'] = update_data['description']
    
    for field, value in update_data.items():
        setattr(template, field, value)
    
    await db.commit()
    await db.refresh(template)
    
    return schemas.MissionTemplateResponse.model_validate(template)


async def delete_mission_template(db: AsyncSession, template_id: int) -> bool:
    """Delete mission template"""
    from app.models import MissionTemplate
    from sqlalchemy import select
    
    result = await db.execute(
        select(MissionTemplate).where(MissionTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        return False
    
    await db.delete(template)
    await db.commit()
    
    return True
