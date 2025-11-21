"""
FASE 4 - Daily Missions Schemas
Schemas para el sistema de misiones diarias
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# MISSION SCHEMAS
# ============================================================================

class MissionReward(BaseModel):
    """Recompensa de una misión"""
    coins: int = Field(default=0, ge=0)
    xp: int = Field(default=0, ge=0)
    gems: int = Field(default=0, ge=0)


class MultiLangText(BaseModel):
    """Texto en múltiples idiomas"""
    es: str
    en: str
    pt: str


class DailyMission(BaseModel):
    """
    Una misión individual del día
    
    Representa una misión asignada al usuario, con progreso y estado.
    """
    mission_id: str = Field(..., description="ID de la plantilla de misión (ej: 'mt-12')")
    code: str = Field(..., description="Código único de la misión")
    
    # Multilenguaje
    title: MultiLangText = Field(..., description="Título en 3 idiomas")
    description: MultiLangText = Field(..., description="Descripción en 3 idiomas")
    
    # Métrica y progreso
    metric_type: str = Field(..., description="Tipo de métrica a trackear")
    metric_required: int = Field(..., gt=0, description="Cantidad requerida para completar")
    metric_progress: int = Field(default=0, ge=0, description="Progreso actual")
    
    # Estado
    completed: bool = Field(default=False, description="Si se alcanzó el objetivo")
    claimable: bool = Field(default=False, description="Si se puede reclamar la recompensa")
    claimed_at: Optional[datetime] = Field(None, description="Cuándo se reclamó")
    
    # Recompensa
    reward: MissionReward = Field(..., description="Recompensa al completar")
    
    # Metadata
    image_url: Optional[str] = None
    order_index: int = Field(default=0, description="Orden de visualización (0, 1, 2)")
    
    @field_validator('metric_progress')
    @classmethod
    def validate_progress(cls, v: int, info) -> int:
        """Progress no puede exceder required"""
        if 'metric_required' in info.data and v > info.data['metric_required']:
            return info.data['metric_required']
        return v


class DailyMissionsResponse(BaseModel):
    """
    Respuesta con las misiones del día del usuario
    
    Contiene las 3 misiones asignadas para hoy.
    """
    userId: str
    learningLanguage: str
    date: str  # YYYY-MM-DD
    timezone: str
    
    missions: List[DailyMission] = Field(..., min_length=3, max_length=3)
    
    generated_at: datetime
    expires_at: datetime  # Medianoche en zona horaria del usuario
    
    # Stats
    completed_count: int = Field(default=0, ge=0, le=3, description="Misiones completadas")
    claimed_count: int = Field(default=0, ge=0, le=3, description="Misiones reclamadas")


class GenerateMissionsRequest(BaseModel):
    """Request para generar misiones del día"""
    learning_language: str = Field(..., description="Idioma de señas (LSB, ASL, LSM)")
    timezone: str = Field(default="UTC", description="Zona horaria del usuario")
    date: Optional[str] = Field(None, description="Fecha YYYY-MM-DD (default: hoy)")
    
    @field_validator('learning_language')
    @classmethod
    def validate_learning_language(cls, v: str) -> str:
        valid_langs = ['LSB', 'ASL', 'LSM', 'LIBRAS']
        if v not in valid_langs:
            raise ValueError(f"learning_language debe ser uno de: {', '.join(valid_langs)}")
        return v


# ============================================================================
# PROGRESS UPDATE SCHEMAS
# ============================================================================

class UpdateMissionProgressRequest(BaseModel):
    """Request para actualizar progreso de una misión"""
    value: int = Field(default=1, gt=0, le=100, description="Cantidad a sumar (default: 1)")
    
    # Context opcional para validación
    exercise_id: Optional[str] = None
    topic_id: Optional[str] = None
    activity_type: Optional[str] = None


class UpdateMissionProgressResponse(BaseModel):
    """Response al actualizar progreso"""
    success: bool
    mission_id: str
    
    # Estado actualizado
    metric_progress: int
    metric_required: int
    progress_percentage: float = Field(..., ge=0, le=100)
    
    # Flags
    just_completed: bool = Field(default=False, description="Si se completó en este update")
    already_completed: bool = Field(default=False, description="Si ya estaba completada antes")
    
    # Reward info (si se completó)
    reward_earned: Optional[MissionReward] = None
    
    message: str


# ============================================================================
# CLAIM REWARD SCHEMAS
# ============================================================================

class ClaimMissionRewardRequest(BaseModel):
    """Request para reclamar recompensa de misión"""
    mission_id: str = Field(..., description="ID de la misión a reclamar")


class ClaimMissionRewardResponse(BaseModel):
    """Response al reclamar recompensa"""
    success: bool
    mission_id: str
    
    # Reward claimed
    reward_claimed: MissionReward
    
    # Updated balance
    new_balance: Dict[str, int] = Field(..., description="Nuevo balance: {coins, xp, gems}")
    
    # Timestamps
    claimed_at: datetime
    
    message: str


# ============================================================================
# HISTORY SCHEMAS
# ============================================================================

class DailyMissionHistoryItem(BaseModel):
    """Una entrada del historial de misiones"""
    date: str  # YYYY-MM-DD
    completed_count: int = Field(..., ge=0, le=3)
    claimed_count: int = Field(..., ge=0, le=3)
    
    # Rewards totales del día
    total_coins_earned: int = Field(default=0, ge=0)
    total_xp_earned: int = Field(default=0, ge=0)
    total_gems_earned: int = Field(default=0, ge=0)
    
    # Detalles de misiones (opcional)
    missions: Optional[List[DailyMission]] = None


class DailyMissionsHistoryResponse(BaseModel):
    """Historial de misiones diarias"""
    userId: str
    learningLanguage: str
    
    history: List[DailyMissionHistoryItem]
    
    # Stats generales
    total_days: int
    total_missions_completed: int
    total_missions_claimed: int
    total_coins_earned: int
    total_xp_earned: int
    total_gems_earned: int
    
    # Streaks
    current_streak: int = Field(default=0, description="Días consecutivos completando al menos 1 misión")
    best_streak: int = Field(default=0, description="Mejor racha histórica")


# ============================================================================
# INTERNAL SCHEMAS (para DynamoDB)
# ============================================================================

class DailyMissionItem(BaseModel):
    """
    Estructura interna almacenada en DynamoDB
    
    PK = USER#<userId>#LL#<learning_language>
    SK = DAY#YYYY-MM-DD
    """
    userId: str
    learning_language: str
    date: str  # YYYY-MM-DD
    timezone: str
    
    missions: List[DailyMission]
    
    generated_at: datetime
    expires_at: datetime
    
    # TTL para auto-eliminación (timestamp Unix)
    ttl: Optional[int] = None
    
    model_config = {"extra": "allow"}  # Allow additional DynamoDB fields like PK, SK
