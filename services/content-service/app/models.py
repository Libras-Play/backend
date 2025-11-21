from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, Boolean, Index, Date, CheckConstraint, Numeric, text, ARRAY, TypeDecorator, Float
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.orm import relationship
import enum
from app.core.db import Base


class MetricTypeEnum(TypeDecorator):
    """Custom type for PostgreSQL ENUM with proper casting"""
    impl = String
    cache_ok = True
    
    def __init__(self):
        super().__init__(30)
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, MetricType):
            return value.value
        return str(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # Try to find by value (lowercase from DB)
        for member in MetricType:
            if member.value == value:
                return member
        # Fallback: try direct construction
        return MetricType(value)
    
    def column_expression(self, col):
        return text(f"CAST({col} AS metric_type_enum)")


class DifficultyLevel(str, enum.Enum):
    """Niveles de dificultad para ejercicios
    
    NOTA TEMPORAL: Usando valores viejos del enum PostgreSQL (BEGINNER, INTERMEDIATE, ADVANCED)
    hasta que se ejecute migración para convertir a nuevos valores (easy, medium, hard).
    
    Los nombres de los enum members son los nuevos (EASY, MEDIUM, HARD) para compatibilidad
    con el código, pero los valores son los viejos que existen en la BD.
    """
    EASY = "BEGINNER"
    MEDIUM = "INTERMEDIATE"
    HARD = "ADVANCED"


class ExerciseType(str, enum.Enum):
    """Tipos de ejercicios"""
    TEST = "test"  # Opción múltiple
    CAMERA = "camera"  # Reconocimiento de gesto con cámara


class ConditionType(str, enum.Enum):
    """Tipos de condiciones para logros"""
    EXERCISES_COMPLETED = "exercises_completed"
    LEVELS_COMPLETED = "levels_completed"
    XP_EARNED = "xp_earned"
    STREAK_DAYS = "streak_days"
    PERFECT_LEVELS = "perfect_levels"


class ExerciseOutcome(str, enum.Enum):
    """Resultado de un intento de ejercicio"""
    CORRECT = "correct"
    INCORRECT = "incorrect"
    SKIPPED = "skipped"


class LifeEventType(str, enum.Enum):
    """Tipo de evento de vidas"""
    LOST = "lost"
    GAINED = "gained"
    RESET = "reset"


class StreakEventType(str, enum.Enum):
    """Tipo de evento de racha"""
    CONTINUED = "continued"
    BROKEN = "broken"
    MILESTONE = "milestone"


class Language(Base):
    """Idiomas de interfaz de usuario (pt-BR, es-ES, en-US)
    
    NOTA: Esta tabla es para idiomas de INTERFAZ únicamente.
    Para lenguajes de señas (ASL, LSB, LSM), ver tabla SignLanguage.
    """
    __tablename__ = "languages"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)  # e.g., "pt-BR", "es-ES", "en-US"
    name = Column(String(100), nullable=False)  # e.g., "Português (Brasil)"
    flag_url = Column(String(500), nullable=True)  # URL de imagen de bandera
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    signs = relationship("Sign", back_populates="language", cascade="all, delete-orphan")
    translations = relationship("Translation", back_populates="language", cascade="all, delete-orphan")


class SignLanguage(Base):
    """Lenguajes de señas disponibles para aprender (ASL, LSB, LSM, etc.)"""
    __tablename__ = "sign_languages"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)  # e.g., "ASL", "LSB", "LSM"
    name = Column(String(100), nullable=False)  # e.g., "American Sign Language"
    country = Column(String(100), nullable=True)  # País principal
    description = Column(Text, nullable=True)
    flag_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    # NOTE: topics relationship eliminado - Topics ya no están vinculados a SignLanguage específico
    exercise_variants = relationship("ExerciseVariant", back_populates="sign_language", cascade="all, delete-orphan")


class Topic(Base):
    """Temas/categorías de contenido (Alfabeto, Números, Saludos, etc.)
    
    Cada Topic incluye 3 niveles fijos (easy, medium, hard) en un array JSON.
    
    MULTILENGUAJE:
    - title: JSONB con traducciones {"es": "...", "en": "...", "pt": "..."}
    - description: JSONB con traducciones {"es": "...", "en": "...", "pt": "..."}
    - Todos los Topics tienen traducciones en todos los idiomas (es, en, pt)
    - No están vinculados a un sign_language específico (eso se maneja en los Exercises)
    """
    __tablename__ = "topics"
    
    id = Column(Integer, primary_key=True, index=True)
    # NOTE: sign_language_id eliminado - Topics son multilenguaje y universales
    
    # Campos multilenguaje (JSONB)
    title = Column(JSONB, nullable=False)  # {"es": "Alfabeto", "en": "Alphabet", "pt": "Alfabeto"}
    description = Column(JSONB, nullable=False)  # {"es": "Descripción", "en": "Description", "pt": "Descrição"}
    
    # Imagen del topic (nullable)
    img_url = Column(String(500), nullable=True)  # URL de imagen principal del topic
    
    order_index = Column(Integer, default=0, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    # NOTE: sign_language relationship eliminado - Topics ya no están vinculados a un lenguaje específico
    exercises = relationship("Exercise", back_populates="topic", cascade="all, delete-orphan", order_by="Exercise.order_index")
    exercise_bases = relationship("ExerciseBase", back_populates="topic", cascade="all, delete-orphan", order_by="ExerciseBase.order_index")
    translations = relationship("TopicTranslation", back_populates="topic", cascade="all, delete-orphan")
    
    # NOTE: __table_args__ eliminado - índice ix_topics_sign_language_order ya no es necesario


class TopicTranslation(Base):
    """Traducciones de topics a diferentes idiomas de interfaz"""
    __tablename__ = "topic_translations"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    language_code = Column(String(10), nullable=False, index=True)  # pt-BR, es-ES, en-US
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    topic = relationship("Topic", back_populates="translations")
    
    __table_args__ = (
        Index('ix_topic_translations_topic_language', 'topic_id', 'language_code', unique=True),
    )


class Exercise(Base):
    """Ejercicios individuales dentro de cada topic
    
    Reestructuración completa con MULTILENGUAJE:
    - Cada ejercicio pertenece a un topic con dificultad (easy/medium/hard)
    - exerciseType: test o camera
    - title y statement son JSONB multilenguaje {"es": "...", "en": "...", "pt": "..."}
    - Estructura de respuestas varía según type (answers para test, expectedSign para camera)
    
    CAMBIOS DE MIGRACIÓN 0006:
    - title: String → JSONB multilenguaje (requerido)
    - statement: String → JSONB multilenguaje (requerido)
    - ELIMINADOS: language, learning_language, description (ya no se usan)
    """
    __tablename__ = "exercises"
    
    # Campos básicos obligatorios
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Campos multilenguaje (JSONB) - OBLIGATORIOS
    title = Column(JSONB, nullable=False)  # {"es": "Título", "en": "Title", "pt": "Título"}
    statement = Column(JSONB, nullable=False)  # {"es": "Pregunta", "en": "Question", "pt": "Pergunta"}
    
    difficulty = Column(
        SQLEnum(
            DifficultyLevel,
            values_callable=lambda x: [e.value for e in x],  # Usa BEGINNER/INTERMEDIATE/ADVANCED
            name='difficultylevel'
        ),
        nullable=False,
        index=True
    )  # Valores: BEGINNER, INTERMEDIATE, ADVANCED (temporales)
    exercise_type = Column(
        SQLEnum(
            ExerciseType,
            values_callable=lambda x: [e.value for e in x],  # Usa test/camera
            name='exercisetype'
        ),
        nullable=False,
        index=True
    )  # test o camera
    
    # Lenguaje de señas que el ejercicio enseña (obligatorio)
    learning_language = Column(String(10), ForeignKey("sign_languages.code", ondelete="RESTRICT"), nullable=False, index=True)
    
    # Media obligatorio
    img_url = Column(String(500), nullable=False)  # Logo/imagen del ejercicio (obligatorio)
    
    # Estructura de datos según type (almacenados en JSONB)
    # Si type='test': {"correct": "...", "options": ["...", "...", "..."]}
    # Si type='camera': {"expectedSign": "..."}
    answers = Column(JSONB, nullable=True)  # Para type='test'
    expected_sign = Column(String(100), nullable=True)  # Para type='camera'
    
    # Video opcional (para ambos types)
    video_url = Column(String(500), nullable=True)
    
    # Metadatos
    order_index = Column(Integer, default=0, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    topic = relationship("Topic", back_populates="exercises")
    sign_language = relationship("SignLanguage", foreign_keys=[learning_language])
    
    # Constraints y validaciones
    __table_args__ = (
        Index('ix_exercises_topic_difficulty', 'topic_id', 'difficulty'),
        Index('ix_exercises_topic_order', 'topic_id', 'order_index'),
        Index('ix_exercises_type', 'exercise_type'),
        # Constraint: si type=test, answers debe estar presente
        CheckConstraint(
            "(exercise_type != 'test') OR (answers IS NOT NULL)",
            name='check_test_has_answers'
        ),
        # Constraint: si type=camera, expected_sign debe estar presente
        CheckConstraint(
            "(exercise_type != 'camera') OR (expected_sign IS NOT NULL)",
            name='check_camera_has_expected_sign'
        ),
    )


class ExerciseBase(Base):
    """Ejercicios base (abstractos) sin contenido específico de lenguaje de señas
    
    Representa el concepto abstracto de un ejercicio.
    Las preguntas traducidas están en ExerciseTranslation.
    Las variantes por lenguaje de señas están en ExerciseVariant.
    """
    __tablename__ = "exercise_base"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # TEST, GESTURE
    difficulty = Column(SQLEnum(DifficultyLevel), nullable=False, index=True)  # easy, medium, hard
    order_index = Column(Integer, nullable=False, default=0, index=True)
    legacy_exercise_id = Column(Integer, nullable=True, index=True)  # TEMPORAL: ID del ejercicio original
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    topic = relationship("Topic", back_populates="exercise_bases")
    translations = relationship("ExerciseTranslation", back_populates="exercise_base", cascade="all, delete-orphan")
    variants = relationship("ExerciseVariant", back_populates="exercise_base", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_exercise_base_topic_difficulty', 'topic_id', 'difficulty'),
        Index('ix_exercise_base_topic_order', 'topic_id', 'order_index'),
        CheckConstraint("type IN ('TEST', 'GESTURE')", name='check_exercise_type'),
    )


class ExerciseTranslation(Base):
    """Traducciones de preguntas de ejercicios a diferentes idiomas de UI"""
    __tablename__ = "exercise_translations"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_base_id = Column(Integer, ForeignKey("exercise_base.id", ondelete="CASCADE"), nullable=False, index=True)
    language_code = Column(String(10), nullable=False, index=True)  # pt-BR, es-ES, en-US
    question_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    exercise_base = relationship("ExerciseBase", back_populates="translations")
    
    __table_args__ = (
        Index('ix_exercise_translations_base_language', 'exercise_base_id', 'language_code', unique=True),
    )


class ExerciseVariant(Base):
    """Variantes de ejercicios específicas por lenguaje de señas
    
    Cada ejercicio base puede tener múltiples variantes, una por cada
    lenguaje de señas (LSB, ASL, LSM), ya que los gestos son diferentes.
    """
    __tablename__ = "exercise_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_base_id = Column(Integer, ForeignKey("exercise_base.id", ondelete="CASCADE"), nullable=False, index=True)
    sign_language_id = Column(Integer, ForeignKey("sign_languages.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Campos para ejercicios TEST
    correct_answer = Column(String(200), nullable=True)  # Solo para TEST
    options = Column(JSONB, nullable=True)  # Solo para TEST: ["A", "B", "C", "D"]
    
    # Campos para ejercicios GESTURE
    gesture_label = Column(String(100), nullable=True, index=True)  # Solo para GESTURE
    gesture_model_version = Column(String(50), nullable=True)  # Versión del modelo ML
    gesture_detection_threshold = Column(Numeric(3, 2), nullable=True)  # Umbral de confianza (0.00-1.00)
    gesture_expected_handshape = Column(String(100), nullable=True)  # Forma de mano esperada
    gesture_metadata = Column(JSONB, nullable=True)  # Metadata adicional para ML Service
    
    # Campos comunes
    image_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    exercise_base = relationship("ExerciseBase", back_populates="variants")
    sign_language = relationship("SignLanguage", back_populates="exercise_variants")
    attempts = relationship("ExerciseAttempt", back_populates="exercise_variant", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_exercise_variants_base_sign_language', 'exercise_base_id', 'sign_language_id', unique=True),
        # Constraint: Si es TEST debe tener options y correct_answer (no gesture_label)
        # Si es GESTURE debe tener gesture_label (no options ni correct_answer)
        CheckConstraint(
            """
            (options IS NOT NULL AND correct_answer IS NOT NULL AND gesture_label IS NULL) OR
            (options IS NULL AND correct_answer IS NULL AND gesture_label IS NOT NULL)
            """,
            name='check_variant_type_consistency'
        ),
    )


class Sign(Base):
    """Diccionario de señas con videos/imágenes de referencia"""
    __tablename__ = "signs"
    
    id = Column(Integer, primary_key=True, index=True)
    language_id = Column(Integer, ForeignKey("languages.id", ondelete="CASCADE"), nullable=False, index=True)
    word = Column(String(200), nullable=False, index=True)  # Palabra/concepto
    video_url = Column(String(500), nullable=True)  # Video en S3
    image_url = Column(String(500), nullable=True)  # Imagen de referencia
    difficulty = Column(SQLEnum(DifficultyLevel), nullable=False, default=DifficultyLevel.EASY)
    tags = Column(JSON, nullable=True)  # Tags para búsqueda (array de strings)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    language = relationship("Language", back_populates="signs")
    
    __table_args__ = (
        Index('ix_signs_language_word', 'language_id', 'word'),
        Index('ix_signs_difficulty', 'difficulty'),
    )


class Translation(Base):
    """Traducciones de UI/strings a diferentes idiomas escritos (i18n)"""
    __tablename__ = "translations"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(200), nullable=False, index=True)  # e.g., "welcome_message"
    language_id = Column(Integer, ForeignKey("languages.id", ondelete="CASCADE"), nullable=False, index=True)
    value = Column(Text, nullable=False)  # Texto traducido
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    language = relationship("Language", back_populates="translations")
    
    __table_args__ = (
        Index('ix_translations_key_language', 'key', 'language_id', unique=True),
    )


class Achievement(Base):
    """Logros/medallas que los usuarios pueden desbloquear"""
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "first_level"
    title = Column(String(200), nullable=False)  # e.g., "Primer Nivel"
    description = Column(Text, nullable=True)
    condition_type = Column(SQLEnum(ConditionType), nullable=False)
    condition_value = Column(Integer, nullable=False)  # Valor necesario para desbloquear
    reward = Column(Integer, default=0, nullable=False)  # XP bonus
    icon_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ExerciseAttempt(Base):
    """Historial de intentos de ejercicios por usuario
    
    Registra cada vez que un usuario intenta un ejercicio,
    permitiendo calcular progreso, rachas y estadísticas.
    """
    __tablename__ = "exercise_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    exercise_variant_id = Column(Integer, ForeignKey("exercise_variants.id", ondelete="CASCADE"), nullable=False, index=True)
    outcome = Column(String(20), nullable=False, index=True)  # correct, incorrect, skipped
    xp_earned = Column(Integer, default=0, nullable=False)
    time_taken_seconds = Column(Integer, nullable=True)
    attempt_number = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    exercise_variant = relationship("ExerciseVariant", back_populates="attempts")
    
    __table_args__ = (
        Index('ix_exercise_attempts_user_variant', 'user_id', 'exercise_variant_id'),
        Index('ix_exercise_attempts_user_created', 'user_id', 'created_at'),
        CheckConstraint("outcome IN ('correct', 'incorrect', 'skipped')", name='check_outcome'),
    )


class UserStats(Base):
    """Estadísticas de progreso de usuarios
    
    Source of truth para XP, nivel, rachas y vidas.
    Reemplaza la lógica en DynamoDB del User Service.
    """
    __tablename__ = "user_stats"
    
    user_id = Column(String(255), primary_key=True)
    xp_total = Column(Integer, default=0, nullable=False, index=True)
    level = Column(Integer, default=1, nullable=False, index=True)
    streak_count = Column(Integer, default=0, nullable=False)
    lives = Column(Integer, default=5, nullable=False)
    max_lives = Column(Integer, default=5, nullable=False)
    last_life_lost_at = Column(DateTime, nullable=True)
    last_activity_date = Column(Date, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    life_events = relationship("LifeEvent", back_populates="user", cascade="all, delete-orphan")
    streak_events = relationship("StreakEvent", back_populates="user", cascade="all, delete-orphan")


class LifeEvent(Base):
    """Historial de cambios de vidas de usuarios
    
    Auditoría completa de cuándo y por qué un usuario ganó/perdió vidas.
    """
    __tablename__ = "life_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), ForeignKey("user_stats.user_id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(20), nullable=False, index=True)  # lost, gained, reset
    lives_before = Column(Integer, nullable=True)
    lives_after = Column(Integer, nullable=True)
    reason = Column(String(100), nullable=True)  # incorrect_answer, daily_reset, purchase
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("UserStats", back_populates="life_events")
    
    __table_args__ = (
        Index('ix_life_events_user_created', 'user_id', 'created_at'),
        CheckConstraint("event_type IN ('lost', 'gained', 'reset')", name='check_life_event_type'),
    )


class StreakEvent(Base):
    """Historial de rachas de usuarios
    
    Registra cuando un usuario continúa, rompe o alcanza hitos de racha.
    """
    __tablename__ = "streak_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), ForeignKey("user_stats.user_id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(20), nullable=False, index=True)  # continued, broken, milestone
    streak_count = Column(Integer, nullable=True)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("UserStats", back_populates="streak_events")
    
    __table_args__ = (
        Index('ix_streak_events_user_date', 'user_id', 'date'),
        CheckConstraint("event_type IN ('continued', 'broken', 'milestone')", name='check_streak_event_type'),
    )


class MetricType(str, enum.Enum):
    """Tipos de métricas para misiones diarias"""
    # Values match DB enum (lowercase)
    EXERCISES_COMPLETED = "exercises_completed"
    CAMERA_MINUTES = "camera_minutes"
    XP_EARNED = "xp_earned"
    TOPIC_COMPLETED = "topic_completed"
    PRACTICE_SECONDS = "practice_seconds"


class MissionTemplate(Base):
    """Plantillas de misiones diarias - FASE 4
    
    Define los tipos de misiones que pueden asignarse a usuarios.
    Las misiones se generan diariamente basándose en estas plantillas.
    """
    __tablename__ = "mission_templates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    
    # Multilenguaje: DEBE contener {es, en, pt}
    title = Column(JSONB, nullable=False)
    description = Column(JSONB, nullable=False)
    
    # Filtros de aplicabilidad
    learning_languages = Column(ARRAY(Text), nullable=False, server_default='{}')  # ['LSB','ASL'] o [] = todos
    
    # Métrica y objetivo
    metric_type = Column(String(30), nullable=False, index=True)  # Using String instead of Enum for flexibility
    metric_value = Column(Integer, nullable=False)  # Cantidad requerida
    
    # Dificultad (opcional: null = aplica a todas)
    difficulty = Column(String(20), nullable=True)  # 'easy', 'medium', 'hard'
    
    # Recompensas
    reward_coins = Column(Integer, nullable=False, server_default='0')
    reward_xp = Column(Integer, nullable=False, server_default='0')
    reward_gems = Column(Integer, nullable=False, server_default='0')
    
    # Metadata
    image_url = Column(String(500), nullable=True)
    active = Column(Boolean, nullable=False, server_default='true', index=True)
    priority = Column(Integer, nullable=False, server_default='0')  # Mayor = más prioridad
    
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        CheckConstraint('metric_value > 0', name='positive_metric_value'),
        CheckConstraint('reward_coins >= 0', name='positive_reward_coins'),
        CheckConstraint('reward_xp >= 0', name='positive_reward_xp'),
        CheckConstraint('reward_gems >= 0', name='positive_reward_gems'),
        CheckConstraint('priority >= 0', name='positive_priority'),
        Index('idx_mission_templates_active_priority', 'active', 'priority', postgresql_where=text('active = true')),
    )


# ============================================================================
# FASE 5: BADGES / ACHIEVEMENTS
# ============================================================================
# NOTA CRÍTICA: NO usar SQLEnum para evitar errores de serialización.
# Todas las columnas tipo "enum" usan String(30).
# ============================================================================

class BadgeMaster(Base):
    """
    Master table for badge definitions.
    
    ANTI-ERROR DESIGN:
    - NO ENUMS: All enum-like columns use String(30)
    - NO ARRAYS: No PostgreSQL array columns
    - JSON for multilang: Avoids separate translation tables
    - Conditions as JSON: Flexible evaluation without ORM complexity
    """
    __tablename__ = 'badges_master'
    
    badge_id = Column(String(36), primary_key=True, comment='UUID or custom ID')
    
    # Badge classification - NO ENUM to avoid serialization errors
    type = Column(String(30), nullable=False, index=True, 
                  comment='Badge type: milestone, achievement, streak, skill, special')
    
    # Multilingual fields as JSON (es, en, pt)
    title = Column(JSONB, nullable=False, 
                   comment='{"es": "...", "en": "...", "pt": "..."}')
    description = Column(JSONB, nullable=False,
                        comment='{"es": "...", "en": "...", "pt": "..."}')
    
    # Visual representation
    icon_url = Column(Text, nullable=False, 
                     comment='URL to badge icon/image')
    
    # Conditions to earn badge - stored as JSON for flexibility
    # Example: {"metric": "xp_earned", "operator": ">=", "value": 1000}
    conditions = Column(JSONB, nullable=False,
                       comment='Conditions: {metric, operator, value}')
    
    # Language-specific badge (LSB, ASL, LSM)
    learning_language = Column(String(10), nullable=False, index=True,
                              comment='LSB, ASL, LSM')
    
    # Visibility and rarity - NO ENUM
    is_hidden = Column(Boolean, default=False, nullable=False,
                      comment='Hidden until earned (secret badge)')
    rarity = Column(String(20), nullable=False, default='common', index=True,
                   comment='common, rare, epic, legendary')
    
    # Ordering
    order_index = Column(Integer, default=0, nullable=False,
                        comment='Display order in badge list')
    
    # Timestamps
    created_at = Column(DateTime, server_default=text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=text('now()'), 
                       onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        CheckConstraint("type IN ('milestone', 'achievement', 'streak', 'skill', 'special')", 
                       name='valid_badge_type'),
        CheckConstraint("rarity IN ('common', 'rare', 'epic', 'legendary')", 
                       name='valid_badge_rarity'),
        CheckConstraint('order_index >= 0', name='positive_order_index'),
    )


class UserExercisePerformance(Base):
    """
    FASE 8: Registra desempeño del usuario sobre ejercicios específicos.
    
    Permite calcular patrones de error, confianza y tiempo de respuesta
    para el algoritmo de orden inteligente de ejercicios.
    
    EVITA ERROR #1: No usa protected namespaces (model_*)
    """
    __tablename__ = "user_exercise_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Performance metrics
    attempts = Column(Integer, nullable=False, default=0)
    errors = Column(Integer, nullable=False, default=0)
    last_result = Column(String(20), nullable=True)  # 'success' | 'fail'
    avg_response_time = Column(Float, nullable=True)  # Average time in seconds
    last_timestamp = Column(DateTime, nullable=True)
    confidence_score = Column(Float, nullable=False, default=0.5)  # 0.0 to 1.0
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
    exercise = relationship("Exercise", backref="user_performances")
    
    __table_args__ = (
        Index('ix_user_exercise_performance_user_id', 'user_id'),
        Index('ix_user_exercise_performance_exercise_id', 'exercise_id'),
        Index('ix_user_exercise_performance_user_exercise', 'user_id', 'exercise_id', unique=True),
        Index('ix_user_exercise_performance_confidence', 'confidence_score'),
        CheckConstraint('confidence_score >= 0.0 AND confidence_score <= 1.0', name='check_confidence_range'),
        CheckConstraint('attempts >= 0', name='check_attempts_positive'),
        CheckConstraint('errors >= 0', name='check_errors_positive'),
    )

