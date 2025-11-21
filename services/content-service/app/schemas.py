from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, field_serializer, model_validator, ConfigDict
from app.models import DifficultyLevel, ExerciseType, ConditionType
from app.validators.translations import TranslationValidatorMixin, create_translation_dict
from app.core.languages import get_supported_languages


# ============================================================================
# Level Info Embebido (No es una entidad separada)
# ============================================================================

class LevelInfo(BaseModel):
    """Información de nivel embebida en Topic (easy, medium, hard)"""
    difficulty: str = Field(..., description="Dificultad del nivel")
    description: str = Field(..., description="Descripción del nivel")
    imageUrl: Optional[str] = Field(None, description="URL de imagen opcional para el nivel")


# Default levels que se auto-generan en cada Topic
DEFAULT_LEVELS = [
    {"difficulty": "easy", "description": "Nivel básico para principiantes", "imageUrl": None},
    {"difficulty": "medium", "description": "Nivel intermedio con mayor dificultad", "imageUrl": None},
    {"difficulty": "hard", "description": "Nivel avanzado para expertos", "imageUrl": None}
]


# ============================================================================
# Language Schemas (UI Languages: pt-BR, es-ES, en-US)
# ============================================================================

class LanguageBase(BaseModel):
    code: str = Field(..., max_length=10, description="Código del idioma de interfaz (pt-BR, es-ES, en-US)")
    name: str = Field(..., max_length=100, description="Nombre completo del idioma")
    flag_url: Optional[str] = Field(None, max_length=500, description="URL de la bandera/icono")


class LanguageCreate(LanguageBase):
    pass


class LanguageUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=10)
    name: Optional[str] = Field(None, max_length=100)
    flag_url: Optional[str] = Field(None, max_length=500)


class Language(LanguageBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# SignLanguage Schemas (Sign Languages: ASL, LSB, LSM)
# ============================================================================

class SignLanguageBase(BaseModel):
    code: str = Field(..., max_length=10, description="Código del lenguaje de señas (ASL, LSB, LSM)")
    name: str = Field(..., max_length=100, description="Nombre completo del lenguaje de señas")
    country: Optional[str] = Field(None, max_length=100, description="País principal")
    description: Optional[str] = Field(None, description="Descripción del lenguaje de señas")
    flag_url: Optional[str] = Field(None, max_length=500, description="URL de la bandera")


class SignLanguageCreate(SignLanguageBase):
    pass


class SignLanguageUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=10)
    name: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    flag_url: Optional[str] = Field(None, max_length=500)


class SignLanguage(SignLanguageBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Topic Schemas (CON TRADUCCIONES MULTILENGUAJE)
# ============================================================================

class TopicBase(TranslationValidatorMixin, BaseModel):
    """
    Base para Topic con traducciones multilenguaje.
    
    IMPORTANTE: Los campos 'title' y 'description' ahora son diccionarios
    con traducciones en todos los idiomas soportados.
    
    Ejemplo:
        {
            "sign_language_id": 1,
            "title": {
                "es": "Alfabeto",
                "en": "Alphabet",
                "pt": "Alfabeto"
            },
            "description": {
                "es": "Aprende las letras del alfabeto",
                "en": "Learn the alphabet letters",
                "pt": "Aprenda as letras do alfabeto"
            },
            "image_url": "https://..."
        }
    """
    # NOTE: sign_language_id eliminado - Topics son multilenguaje y universales
    title: Dict[str, str] = Field(
        ..., 
        description=f"Título del tema en todos los idiomas soportados: {get_supported_languages()}"
    )
    description: Dict[str, str] = Field(
        ...,
        description=f"Descripción del tema en todos los idiomas soportados: {get_supported_languages()}"
    )
    img_url: Optional[str] = Field(None, max_length=500, description="URL de imagen principal del topic (nullable)")
    order_index: int = Field(default=0, description="Orden de aparición")
    
    @field_validator('title')
    @classmethod
    def validate_title_translations(cls, v):
        """Valida que title tenga todas las traducciones requeridas"""
        return cls.validate_translation_field(v, 'title')
    
    @field_validator('description')
    @classmethod
    def validate_description_translations(cls, v):
        """Valida que description tenga todas las traducciones requeridas"""
        return cls.validate_translation_field(v, 'description')


class TopicCreate(TopicBase):
    """
    Schema para crear un nuevo Topic.
    
    Los niveles (easy, medium, hard) se generan automáticamente en el backend.
    """
    pass


class TopicUpdate(TranslationValidatorMixin, BaseModel):
    """
    Schema para actualizar un Topic existente.
    
    IMPORTANTE: Si actualizas 'title' o 'description', debes proporcionar
    TODAS las traducciones, no solo las que quieres cambiar.
    """
    # NOTE: sign_language_id eliminado - Topics son universales
    title: Optional[Dict[str, str]] = Field(
        None,
        description="Si se proporciona, debe incluir todos los idiomas soportados"
    )
    description: Optional[Dict[str, str]] = Field(
        None,
        description="Si se proporciona, debe incluir todos los idiomas soportados"
    )
    img_url: Optional[str] = Field(None, max_length=500, description="URL de imagen principal del topic")
    order_index: Optional[int] = None
    
    @field_validator('title')
    @classmethod
    def validate_title_translations(cls, v):
        """Valida traducciones de title si se proporciona"""
        if v is not None:
            return cls.validate_translation_field(v, 'title')
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description_translations(cls, v):
        """Valida traducciones de description si se proporciona"""
        if v is not None:
            return cls.validate_translation_field(v, 'description')
        return v


class Topic(TopicBase):
    """Schema de respuesta de Topic con traducciones"""
    id: int
    # NOTE: levels comentado - columna no existe en DB
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Exercise Schemas (CON TRADUCCIONES MULTILENGUAJE)
# ============================================================================

class AnswerOption(TranslationValidatorMixin, BaseModel):
    """
    Opción de respuesta multilenguaje para ejercicios tipo 'test'.
    Cada opción tiene texto traducido en todos los idiomas y un flag de correcta/incorrecta.
    """
    text: Dict[str, str] = Field(
        ...,
        description=f"Texto de la opción en todos los idiomas: {get_supported_languages()}"
    )
    correct: bool = Field(..., description="Si esta es la respuesta correcta")
    
    @field_validator('text')
    @classmethod
    def validate_text_translations(cls, v):
        """Valida que text tenga todas las traducciones requeridas"""
        return cls.validate_translation_field(v, 'answer.text')


class AnswersData(BaseModel):
    """
    Estructura de respuestas para ejercicios tipo 'test'.
    Debe contener un array de opciones multilenguaje con exactamente UNA marcada como correcta.
    """
    options: List[AnswerOption] = Field(
        ..., 
        min_length=2,
        description="Lista de opciones de respuesta (mínimo 2)"
    )
    
    @model_validator(mode='after')
    def validate_exactly_one_correct(self):
        """Valida que exactamente una opción esté marcada como correcta"""
        correct_count = sum(1 for option in self.options if option.correct)
        if correct_count != 1:
            raise ValueError(
                f"Exactly one answer must be marked as correct, found {correct_count}. "
                "Set 'correct: true' for exactly one option."
            )
        return self


class ExerciseBase(TranslationValidatorMixin, BaseModel):
    """
    Base para Exercise con traducciones multilenguaje.
    
    IMPORTANTE: Los campos 'title' y 'statement' ahora son diccionarios
    con traducciones en todos los idiomas soportados.
    
    Ejemplo para exercise tipo 'test':
        {
            "topic_id": 1,
            "difficulty": "easy",
            "exercise_type": "test",
            "title": {
                "es": "Identifica la letra A",
                "en": "Identify letter A",
                "pt": "Identifique a letra A"
            },
            "statement": {
                "es": "¿Qué letra representa esta seña?",
                "en": "What letter does this sign represent?",
                "pt": "Que letra esta sinal representa?"
            },
            "img_url": "https://...",
            "answers": {
                "correct": "A",
                "options": ["A", "B", "C", "D"]
            }
        }
    """
    topic_id: int = Field(..., description="ID del topic al que pertenece")
    difficulty: DifficultyLevel = Field(..., description="Dificultad: easy, medium, hard")
    exercise_type: ExerciseType = Field(..., description="Tipo de ejercicio: test o camera")
    learning_language: str = Field(
        ..., 
        max_length=10, 
        description="Código del lenguaje de señas que enseña (LSB, ASL, LSM, etc.)"
    )
    
    # Campos traducibles (obligatorios)
    title: Dict[str, str] = Field(
        ...,
        description=f"Título del ejercicio en todos los idiomas: {get_supported_languages()}"
    )
    statement: Dict[str, str] = Field(
        ...,
        description=f"Enunciado del ejercicio en todos los idiomas: {get_supported_languages()}"
    )
    
    # Media obligatorio
    img_url: str = Field(..., max_length=500, description="URL de imagen del ejercicio")
    
    # Campos opcionales
    video_url: Optional[str] = Field(None, max_length=500, description="URL de video opcional")
    order_index: int = Field(default=0, ge=0, description="Orden dentro del topic")
    
    # Datos específicos según type
    answers: Optional[AnswersData] = Field(None, description="Respuestas para type='test'")
    expected_sign: Optional[str] = Field(None, max_length=100, description="Seña esperada para type='camera'")
    
    @field_validator('title')
    @classmethod
    def validate_title_translations(cls, v):
        """Valida que title tenga todas las traducciones requeridas"""
        return cls.validate_translation_field(v, 'title')
    
    @field_validator('statement')
    @classmethod
    def validate_statement_translations(cls, v):
        """Valida que statement tenga todas las traducciones requeridas"""
        return cls.validate_translation_field(v, 'statement')
    
    @model_validator(mode='after')
    def validate_exercise_type_fields(self):
        """Valida que los campos requeridos estén presentes según el tipo de ejercicio"""
        if self.exercise_type == ExerciseType.TEST:
            if not self.answers:
                raise ValueError(
                    "Los ejercicios tipo 'test' requieren el campo 'answers' con estructura "
                    "{options: [{text: {...}, correct: bool}]}"
                )
            if not self.answers.options or len(self.answers.options) < 2:
                raise ValueError(
                    "Los ejercicios tipo 'test' requieren al menos 2 opciones en 'answers.options'"
                )
            # Validar que cada opción tenga traducciones completas
            for idx, option in enumerate(self.answers.options):
                if not option.text:
                    raise ValueError(f"Option {idx} is missing 'text' field")
        
        if self.exercise_type == ExerciseType.CAMERA:
            if not self.expected_sign:
                raise ValueError("Los ejercicios tipo 'camera' requieren el campo 'expected_sign'")
        
        return self


class ExerciseCreate(ExerciseBase):
    """
    Schema para crear un nuevo ejercicio.
    
    Requiere traducciones completas en title y statement.
    """
    pass


class ExerciseUpdate(TranslationValidatorMixin, BaseModel):
    """
    Schema para actualizar un ejercicio existente.
    
    IMPORTANTE: Si actualizas 'title' o 'statement', debes proporcionar
    TODAS las traducciones, no solo las que quieres cambiar.
    """
    topic_id: Optional[int] = None
    difficulty: Optional[DifficultyLevel] = None
    exercise_type: Optional[ExerciseType] = None
    learning_language: Optional[str] = Field(None, max_length=10, description="Código del lenguaje de señas")
    title: Optional[Dict[str, str]] = Field(
        None,
        description="Si se proporciona, debe incluir todos los idiomas soportados"
    )
    statement: Optional[Dict[str, str]] = Field(
        None,
        description="Si se proporciona, debe incluir todos los idiomas soportados"
    )
    img_url: Optional[str] = Field(None, max_length=500)
    video_url: Optional[str] = Field(None, max_length=500)
    order_index: Optional[int] = Field(None, ge=0)
    answers: Optional[AnswersData] = None
    expected_sign: Optional[str] = Field(None, max_length=100)
    
    @field_validator('title')
    @classmethod
    def validate_title_translations(cls, v):
        """Valida traducciones de title si se proporciona"""
        if v is not None:
            return cls.validate_translation_field(v, 'title')
        return v
    
    @field_validator('statement')
    @classmethod
    def validate_statement_translations(cls, v):
        """Valida traducciones de statement si se proporciona"""
        if v is not None:
            return cls.validate_translation_field(v, 'statement')
        return v


class Exercise(ExerciseBase):
    """Schema de respuesta completo con ID y timestamps"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Los demás schemas permanecen igual...
# Achievement, Translation, UserStats, etc.

class AchievementBase(BaseModel):
    code: str = Field(..., max_length=50, description="Código único del logro")
    title: str = Field(..., max_length=200, description="Título del logro")
    description: Optional[str] = Field(None, description="Descripción del logro")
    condition_type: ConditionType = Field(..., description="Tipo de condición")
    condition_value: int = Field(..., ge=0, description="Valor necesario para desbloquear")
    reward: int = Field(default=0, ge=0, description="XP bonus al desbloquear")
    icon_url: Optional[str] = Field(None, max_length=500, description="URL del icono")


class AchievementCreate(AchievementBase):
    pass


class AchievementUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    condition_type: Optional[ConditionType] = None
    condition_value: Optional[int] = Field(None, ge=0)
    reward: Optional[int] = Field(None, ge=0)
    icon_url: Optional[str] = Field(None, max_length=500)


class Achievement(AchievementBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Translation Schemas (i18n)
# ============================================================================

class TranslationBase(BaseModel):
    key: str = Field(..., max_length=200, description="Clave de traducción (e.g., 'welcome_message')")
    language_id: int = Field(..., description="ID del lenguaje")
    value: str = Field(..., description="Texto traducido")


class TranslationCreate(TranslationBase):
    pass


class TranslationUpdate(BaseModel):
    key: Optional[str] = Field(None, max_length=200)
    language_id: Optional[int] = None
    value: Optional[str] = None


class Translation(TranslationBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# schemas.py end


# ============================================================================
# Mission Templates - FASE 4
# ============================================================================

class MultiLangText(BaseModel):
    """Texto multilenguaje (es, en, pt obligatorios)"""
    es: str = Field(..., min_length=1, description="Texto en español")
    en: str = Field(..., min_length=1, description="Text in English")
    pt: str = Field(..., min_length=1, description="Texto em português")


class MissionTemplateBase(BaseModel):
    """Base para Mission Template"""
    code: str = Field(..., min_length=3, max_length=100, description="Código único de la misión")
    title: MultiLangText = Field(..., description="Título en 3 idiomas")
    description: MultiLangText = Field(..., description="Descripción en 3 idiomas")
    learning_languages: List[str] = Field(default_factory=list, description="Idiomas de señas aplicables (vacío = todos)")
    metric_type: str = Field(..., description="Tipo de métrica: exercises_completed, camera_minutes, xp_earned, topic_completed, practice_seconds")
    metric_value: int = Field(..., gt=0, description="Valor objetivo de la métrica")
    difficulty: Optional[str] = Field(None, description="Dificultad (easy, medium, hard) o null para todas")
    reward_coins: int = Field(default=0, ge=0, description="Monedas de recompensa")
    reward_xp: int = Field(default=0, ge=0, description="XP de recompensa")
    reward_gems: int = Field(default=0, ge=0, description="Gemas de recompensa")
    image_url: Optional[str] = Field(None, max_length=500, description="URL de imagen opcional")
    active: bool = Field(default=True, description="Si está activa para asignación")
    priority: int = Field(default=0, ge=0, description="Prioridad de selección (mayor = más prioritaria)")

    @field_validator('metric_type')
    @classmethod
    def validate_metric_type(cls, v: str) -> str:
        valid_types = ['exercises_completed', 'camera_minutes', 'xp_earned', 'topic_completed', 'practice_seconds']
        if v not in valid_types:
            raise ValueError(f"metric_type debe ser uno de: {', '.join(valid_types)}")
        return v
    
    @field_validator('learning_languages')
    @classmethod
    def validate_learning_languages(cls, v: List[str]) -> List[str]:
        valid_langs = ['LSB', 'ASL', 'LSM', 'LIBRAS']
        for lang in v:
            if lang not in valid_langs:
                raise ValueError(f"learning_language '{lang}' no válido. Debe ser uno de: {', '.join(valid_langs)}")
        return v
    
    @field_validator('difficulty')
    @classmethod
    def validate_difficulty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ['easy', 'medium', 'hard']:
            raise ValueError("difficulty debe ser 'easy', 'medium', 'hard' o null")
        return v


class MissionTemplateCreate(MissionTemplateBase):
    """Schema para crear Mission Template"""
    pass


class MissionTemplateUpdate(BaseModel):
    """Schema para actualizar Mission Template"""
    title: Optional[MultiLangText] = None
    description: Optional[MultiLangText] = None
    learning_languages: Optional[List[str]] = None
    metric_value: Optional[int] = Field(None, gt=0)
    difficulty: Optional[str] = None
    reward_coins: Optional[int] = Field(None, ge=0)
    reward_xp: Optional[int] = Field(None, ge=0)
    reward_gems: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = None
    active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0)


class MissionTemplateResponse(MissionTemplateBase):
    """Schema de respuesta de Mission Template"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
    
    @field_serializer('metric_type')
    def serialize_metric_type(self, value):
        """Convert enum to string"""
        if hasattr(value, 'value'):
            return value.value
        return str(value)


class MissionTemplateListResponse(BaseModel):
    """Lista de mission templates"""
    templates: List[MissionTemplateResponse]
    total: int
    page: int
    page_size: int
