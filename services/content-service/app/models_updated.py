"""
Updated models.py with VARCHAR + CHECK constraints instead of SQLEnum

This version is designed to work AFTER the enum-to-varchar migration is applied.
The enum classes remain for code compatibility but columns use VARCHAR with CHECK constraints.
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Index, Date, CheckConstraint, Numeric, text, ARRAY, TypeDecorator, Float
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
    
    DESPUÉS DE MIGRACIÓN: Los valores en BD son 'easy', 'medium', 'hard'
    """
    EASY = "easy"
    MEDIUM = "medium" 
    HARD = "hard"


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


# Custom TypeDecorator for case-insensitive enum handling
class CaseInsensitiveEnum(TypeDecorator):
    """
    Custom type that accepts case-insensitive enum values and stores them as lowercase VARCHAR
    """
    impl = String
    cache_ok = True
    
    def __init__(self, enum_class, length=20):
        self.enum_class = enum_class
        super().__init__(length)
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value.value.lower()
        if isinstance(value, str):
            # Accept case-insensitive input and convert to lowercase
            return value.lower()
        return str(value).lower()
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # Return the corresponding enum member
        for member in self.enum_class:
            if member.value.lower() == value.lower():
                return member
        # Fallback: try to create enum from value
        return self.enum_class(value)


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


class SignLanguage(Base):
    """Lenguajes de señas soportados por la plataforma (ASL, LSB, LSM)
    
    NOTA: Esta tabla es para LENGUAJES DE SEÑAS únicamente.
    Para idiomas de interfaz (pt-BR, es-ES, en-US), ver tabla Language.
    """
    __tablename__ = "sign_languages"
    
    code = Column(String(10), primary_key=True)  # e.g., "ASL", "LSB", "LSM"
    name = Column(String(100), nullable=False)  # e.g., "American Sign Language"
    country = Column(String(100), nullable=False)  # e.g., "United States"
    flag_url = Column(String(500), nullable=True)  # URL de imagen de bandera del país
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Topic(Base):
    """Temas/categorías de ejercicios (Familia, Comida, Números, etc.)"""
    __tablename__ = "topics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Campos multilenguaje (JSONB) - OBLIGATORIOS
    name = Column(JSONB, nullable=False)  # {"es": "Familia", "en": "Family", "pt": "Família"}
    description = Column(JSONB, nullable=True)  # {"es": "Desc", "en": "Desc", "pt": "Desc"}
    
    # Ordenamiento y estado
    order_index = Column(Integer, default=0, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Media
    icon_url = Column(String(500), nullable=True)  # Ícono del tema
    
    # Metadatos
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    exercises = relationship("Exercise", back_populates="topic", cascade="all, delete-orphan")
    exercise_bases = relationship("ExerciseBase", back_populates="topic", cascade="all, delete-orphan")


class Exercise(Base):
    """Ejercicios individuales con contenido específico
    
    MIGRADOS: Los campos difficulty y exercise_type ahora son VARCHAR con CHECK constraints
    """
    __tablename__ = "exercises"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Campos multilenguaje (JSONB) - OBLIGATORIOS
    title = Column(JSONB, nullable=False)  # {"es": "Título", "en": "Title", "pt": "Título"}
    statement = Column(JSONB, nullable=False)  # {"es": "Pregunta", "en": "Question", "pt": "Pergunta"}
    
    # MIGRADO: Antes SQLEnum, ahora VARCHAR con CHECK constraint
    difficulty = Column(
        CaseInsensitiveEnum(DifficultyLevel, 20),
        nullable=False,
        index=True
    )  # Valores: 'easy', 'medium', 'hard'
    
    # MIGRADO: Antes SQLEnum, ahora VARCHAR con CHECK constraint  
    exercise_type = Column(
        CaseInsensitiveEnum(ExerciseType, 20),
        nullable=False,
        index=True
    )  # 'test' o 'camera'
    
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
        # MIGRADO: CHECK constraints reemplazaron enum constraints
        CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name='check_exercises_difficulty_valid'),
        CheckConstraint("exercise_type IN ('test', 'camera')", name='check_exercises_exercise_type_valid'),
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
    
    MIGRADO: Campo difficulty ahora es VARCHAR con CHECK constraint
    """
    __tablename__ = "exercise_base"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # TEST, GESTURE
    
    # MIGRADO: Antes SQLEnum, ahora VARCHAR con CHECK constraint
    difficulty = Column(
        CaseInsensitiveEnum(DifficultyLevel, 20), 
        nullable=False, 
        index=True
    )  # 'easy', 'medium', 'hard'
    
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
        # MIGRADO: CHECK constraints reemplazaron enum constraints
        CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name='check_exercise_base_difficulty_valid'),
        CheckConstraint("type IN ('TEST', 'GESTURE')", name='check_exercise_type'),
    )


class ExerciseTranslation(Base):
    """Traducciones de preguntas de ejercicios a diferentes idiomas de UI"""
    __tablename__ = "exercise_translations"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_base_id = Column(Integer, ForeignKey("exercise_base.id", ondelete="CASCADE"), nullable=False, index=True)
    language_id = Column(Integer, ForeignKey("languages.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Contenido traducido
    title = Column(String(200), nullable=False)
    statement = Column(Text, nullable=False)  # Pregunta/instrucción
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    exercise_base = relationship("ExerciseBase", back_populates="translations")
    language = relationship("Language")
    
    __table_args__ = (
        Index('ix_translations_exercise_language', 'exercise_base_id', 'language_id', unique=True),
    )


class ExerciseVariant(Base):
    """Variantes de ejercicios base por lenguaje de señas
    
    Un ejercicio base puede tener diferentes variantes para ASL, LSB, LSM, etc.
    """
    __tablename__ = "exercise_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_base_id = Column(Integer, ForeignKey("exercise_base.id", ondelete="CASCADE"), nullable=False, index=True)
    sign_language_code = Column(String(10), ForeignKey("sign_languages.code", ondelete="CASCADE"), nullable=False, index=True)
    
    # Contenido específico del lenguaje de señas
    img_url = Column(String(500), nullable=False)  # Imagen principal
    video_url = Column(String(500), nullable=True)  # Video opcional
    
    # Para ejercicios TEST: opciones múltiples en el lenguaje de señas
    # JSON: {"correct": "...", "options": ["...", "...", "..."]}
    answers = Column(JSONB, nullable=True)
    
    # Para ejercicios GESTURE: gesto/seña esperada
    expected_sign = Column(String(100), nullable=True)
    
    # Metadatos
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    exercise_base = relationship("ExerciseBase", back_populates="variants")
    sign_language = relationship("SignLanguage")
    attempts = relationship("ExerciseAttempt", back_populates="exercise_variant", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_variants_base_sign_language', 'exercise_base_id', 'sign_language_code', unique=True),
        # Constraints por tipo de ejercicio
        CheckConstraint(
            "(exercise_base_id NOT IN (SELECT id FROM exercise_base WHERE type = 'TEST')) OR (answers IS NOT NULL)",
            name='check_test_variant_has_answers'
        ),
        CheckConstraint(
            "(exercise_base_id NOT IN (SELECT id FROM exercise_base WHERE type = 'GESTURE')) OR (expected_sign IS NOT NULL)",
            name='check_gesture_variant_has_expected_sign'
        ),
    )


class Translation(Base):
    """Traducciones de interfaz de usuario (labels, mensajes, etc.)
    
    Almacena todas las strings de la UI en diferentes idiomas.
    """
    __tablename__ = "translations"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, index=True)  # e.g., "buttons.start", "messages.welcome"
    language_id = Column(Integer, ForeignKey("languages.id", ondelete="CASCADE"), nullable=False, index=True)
    value = Column(Text, nullable=False)  # Texto traducido
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    language = relationship("Language")
    
    __table_args__ = (
        Index('ix_translations_key_language', 'key', 'language_id', unique=True),
    )


class Achievement(Base):
    """Logros/medallas que los usuarios pueden desbloquear
    
    MIGRADO: Campo condition_type ahora es VARCHAR con CHECK constraint
    """
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "first_level"
    title = Column(String(200), nullable=False)  # e.g., "Primer Nivel"
    description = Column(Text, nullable=True)
    
    # MIGRADO: Antes SQLEnum, ahora VARCHAR con CHECK constraint
    condition_type = Column(
        CaseInsensitiveEnum(ConditionType, 30), 
        nullable=False
    )
    
    condition_value = Column(Integer, nullable=False)  # Valor necesario para desbloquear
    reward = Column(Integer, default=0, nullable=False)  # XP bonus
    icon_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        # MIGRADO: CHECK constraint reemplazó enum constraint
        CheckConstraint(
            "condition_type IN ('exercises_completed', 'levels_completed', 'xp_earned', 'streak_days', 'perfect_levels')", 
            name='check_achievements_condition_type_valid'
        ),
    )


class ExerciseAttempt(Base):
    """Historial de intentos de ejercicios por usuario
    
    Registra cada vez que un usuario intenta un ejercicio,
    permitiendo calcular progreso, rachas y estadísticas.
    
    MIGRADO: Campo outcome mantiene CHECK constraint VARCHAR
    """
    __tablename__ = "exercise_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    exercise_variant_id = Column(Integer, ForeignKey("exercise_variants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # MEJORADO: Campo outcome con tipo enum case-insensitive
    outcome = Column(
        CaseInsensitiveEnum(ExerciseOutcome, 20), 
        nullable=False, 
        index=True
    )  # 'correct', 'incorrect', 'skipped'
    
    xp_earned = Column(Integer, default=0, nullable=False)
    time_taken_seconds = Column(Integer, nullable=True)
    attempt_number = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    exercise_variant = relationship("ExerciseVariant", back_populates="attempts")
    
    __table_args__ = (
        Index('ix_exercise_attempts_user_variant', 'user_id', 'exercise_variant_id'),
        Index('ix_exercise_attempts_user_created', 'user_id', 'created_at'),
        # MIGRADO: CHECK constraint mejorado
        CheckConstraint("outcome IN ('correct', 'incorrect', 'skipped')", name='check_exercise_attempts_outcome_valid'),
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
    
    MEJORADO: Campo event_type con tipo enum case-insensitive
    """
    __tablename__ = "life_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), ForeignKey("user_stats.user_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # MEJORADO: Campo event_type con tipo enum case-insensitive
    event_type = Column(
        CaseInsensitiveEnum(LifeEventType, 20), 
        nullable=False, 
        index=True
    )  # 'lost', 'gained', 'reset'
    
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
    
    MEJORADO: Campo event_type con tipo enum case-insensitive
    """
    __tablename__ = "streak_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), ForeignKey("user_stats.user_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # MEJORADO: Campo event_type con tipo enum case-insensitive
    event_type = Column(
        CaseInsensitiveEnum(StreakEventType, 20), 
        nullable=False, 
        index=True
    )  # 'continued', 'broken', 'milestone'
    
    streak_before = Column(Integer, nullable=True)
    streak_after = Column(Integer, nullable=True)
    milestone_reached = Column(Integer, nullable=True)  # Para event_type='milestone': días alcanzados
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("UserStats", back_populates="streak_events")
    
    __table_args__ = (
        Index('ix_streak_events_user_created', 'user_id', 'created_at'),
        CheckConstraint("event_type IN ('continued', 'broken', 'milestone')", name='check_streak_event_type'),
    )


# Temporal: mantener el resto de las clases existentes...
# (MetricType, UserProgress, UserAchievement, etc. - sin cambios)