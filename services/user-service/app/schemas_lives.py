"""
FASE 7: Schemas para Sistema de Vidas Refinado

IMPORTANTE: 
- Evitar protected namespaces de Pydantic (model_, config_, etc.)
- Validaciones estrictas para timestamps
- Sin campos reservados
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class LivesStateResponse(BaseModel):
    """
    Schema para respuesta de estado de vidas.
    
    EVITA ERROR #1: No usar 'model_' prefix
    EVITA ERROR #5: Validación estricta de timestamps
    """
    user_id: str = Field(..., description="User identifier")
    current_lives: int = Field(..., ge=0, le=5, description="Current number of lives")
    max_lives: int = Field(default=5, description="Maximum number of lives")
    
    # Timestamps con validación estricta
    last_regeneration_at: Optional[str] = Field(None, description="Last regeneration timestamp (ISO format)")
    next_life_at: Optional[str] = Field(None, description="When next life will regenerate (ISO format)")
    lives_maxed_at: Optional[str] = Field(None, description="When lives will be maxed (ISO format)")
    
    # Estado calculado
    time_until_next_life_seconds: int = Field(default=0, ge=0, description="Seconds until next life")
    is_blocked: bool = Field(default=False, description="User is blocked due to no lives")
    
    # Vidas compradas
    purchased_lives: int = Field(default=0, ge=0, description="Number of purchased lives")
    
    # Configuración
    regeneration_interval_minutes: int = Field(default=30, gt=0, description="Minutes between life regenerations")
    lives_per_interval: int = Field(default=1, gt=0, description="Lives regenerated per interval")
    
    @field_validator('last_regeneration_at', 'next_life_at', 'lives_maxed_at')
    @classmethod
    def validate_timestamp(cls, v: Optional[str]) -> Optional[str]:
        """Valida que los timestamps sean formato ISO válido (EVITA ERROR #5)"""
        if v is None:
            return v
        
        try:
            # Intentar parsear para validar formato
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid timestamp format. Expected ISO 8601: {str(e)}")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "current_lives": 3,
                "max_lives": 5,
                "last_regeneration_at": "2025-11-20T19:00:00Z",
                "next_life_at": "2025-11-20T19:30:00Z",
                "lives_maxed_at": "2025-11-20T20:00:00Z",
                "time_until_next_life_seconds": 1800,
                "is_blocked": False,
                "purchased_lives": 0,
                "regeneration_interval_minutes": 30,
                "lives_per_interval": 1
            }
        }


class ConsumeLifeRequest(BaseModel):
    """
    Schema para request de consumo de vida.
    
    EVITA ERROR #1: No usar protected namespaces
    """
    reason: str = Field(
        ..., 
        description="Reason for consuming life",
        pattern="^(exercise_failed|lesson_failed|challenge_failed|manual)$"
    )
    force: bool = Field(
        default=False,
        description="Force consumption even if no lives available (admin only)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "reason": "exercise_failed",
                "force": False
            }
        }


class ConsumeLifeResponse(BaseModel):
    """
    Schema para respuesta de consumo de vida.
    
    EVITA ERROR #5: Timestamps validados
    """
    user_id: str = Field(..., description="User identifier")
    lives_before: int = Field(..., ge=0, description="Lives before consumption")
    lives_after: int = Field(..., ge=0, description="Lives after consumption")
    lives_consumed: int = Field(..., ge=0, description="Number of lives consumed")
    
    reason: str = Field(..., description="Reason for consumption")
    success: bool = Field(..., description="Whether consumption was successful")
    message: str = Field(..., description="Result message")
    
    # Timestamps actualizados
    consumed_at: str = Field(..., description="When life was consumed (ISO format)")
    next_life_at: Optional[str] = Field(None, description="When next life will regenerate (ISO format)")
    lives_maxed_at: Optional[str] = Field(None, description="When lives will be maxed (ISO format)")
    
    is_blocked: bool = Field(default=False, description="User is now blocked due to no lives")
    
    @field_validator('consumed_at', 'next_life_at', 'lives_maxed_at')
    @classmethod
    def validate_timestamp(cls, v: Optional[str]) -> Optional[str]:
        """Valida timestamps (EVITA ERROR #5)"""
        if v is None:
            return v
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid timestamp format: {str(e)}")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "lives_before": 3,
                "lives_after": 2,
                "lives_consumed": 1,
                "reason": "exercise_failed",
                "success": True,
                "message": "Life consumed due to: exercise_failed",
                "consumed_at": "2025-11-20T19:15:00Z",
                "next_life_at": "2025-11-20T19:45:00Z",
                "lives_maxed_at": "2025-11-20T20:45:00Z",
                "is_blocked": False
            }
        }


class RegenerateLivesRequest(BaseModel):
    """Schema para regeneración forzada (admin/testing)"""
    amount: int = Field(default=1, ge=1, le=5, description="Number of lives to regenerate")
    reason: str = Field(default="manual", description="Reason for forced regeneration")
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 1,
                "reason": "admin_action"
            }
        }


class RegenerateLivesResponse(BaseModel):
    """
    Schema para respuesta de regeneración forzada.
    
    EVITA ERROR #5: Timestamps validados
    """
    user_id: str = Field(..., description="User identifier")
    lives_before: int = Field(..., ge=0, description="Lives before regeneration")
    lives_after: int = Field(..., ge=0, description="Lives after regeneration")
    lives_regenerated: int = Field(..., ge=0, description="Number of lives regenerated")
    
    regenerated_at: str = Field(..., description="When regeneration occurred (ISO format)")
    next_life_at: Optional[str] = Field(None, description="When next life will regenerate (ISO format)")
    lives_maxed_at: Optional[str] = Field(None, description="When lives will be maxed (ISO format)")
    
    @field_validator('regenerated_at', 'next_life_at', 'lives_maxed_at')
    @classmethod
    def validate_timestamp(cls, v: Optional[str]) -> Optional[str]:
        """Valida timestamps (EVITA ERROR #5)"""
        if v is None:
            return v
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid timestamp format: {str(e)}")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "lives_before": 2,
                "lives_after": 3,
                "lives_regenerated": 1,
                "regenerated_at": "2025-11-20T19:30:00Z",
                "next_life_at": "2025-11-20T20:00:00Z",
                "lives_maxed_at": "2025-11-20T21:00:00Z"
            }
        }


class PurchaseLivesRequest(BaseModel):
    """
    Schema para compra de vidas (SIMULACIÓN).
    
    NO IMPLEMENTA BILLING REAL - preparado para futuro microservicio.
    EVITA ERROR #2: Documenta que requiere validación de billing service.
    """
    amount: int = Field(..., ge=1, le=5, description="Number of lives to purchase")
    payment_method: str = Field(
        default="simulation",
        description="Payment method (future: credit_card, gems, etc.)"
    )
    payment_token: Optional[str] = Field(
        None,
        description="Payment token from billing service (future)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 2,
                "payment_method": "simulation",
                "payment_token": None
            }
        }


class PurchaseLivesResponse(BaseModel):
    """
    Schema para respuesta de compra de vidas.
    
    EVITA ERROR #5: Timestamps validados
    """
    user_id: str = Field(..., description="User identifier")
    lives_before: int = Field(..., ge=0, description="Lives before purchase")
    lives_after: int = Field(..., ge=0, description="Lives after purchase")
    lives_purchased: int = Field(..., ge=0, description="Number of lives purchased")
    
    success: bool = Field(..., description="Whether purchase was successful")
    message: str = Field(..., description="Purchase result message")
    
    purchased_at: str = Field(..., description="When purchase occurred (ISO format)")
    
    # NOTA: En producción, incluir transaction_id del billing service
    transaction_id: Optional[str] = Field(None, description="Transaction ID from billing service (future)")
    
    @field_validator('purchased_at')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Valida timestamp (EVITA ERROR #5)"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid timestamp format: {str(e)}")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "lives_before": 1,
                "lives_after": 3,
                "lives_purchased": 2,
                "success": True,
                "message": "Lives purchased successfully (SIMULATION MODE)",
                "purchased_at": "2025-11-20T19:35:00Z",
                "transaction_id": None
            }
        }


class LifeEventLog(BaseModel):
    """
    Schema para log de eventos de vidas (para analytics/ML futuro).
    
    EVITA ERROR #1: No usar 'model_' prefix
    """
    user_id: str = Field(..., description="User identifier")
    event_type: str = Field(
        ...,
        description="Type of event",
        pattern="^(consumed|regenerated|purchased|maxed|blocked)$"
    )
    lives_before: int = Field(..., ge=0, description="Lives before event")
    lives_after: int = Field(..., ge=0, description="Lives after event")
    
    reason: Optional[str] = Field(None, description="Reason for event")
    metadata: Optional[dict] = Field(None, description="Additional event metadata")
    
    timestamp: str = Field(..., description="Event timestamp (ISO format)")
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Valida timestamp (EVITA ERROR #5)"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid timestamp format: {str(e)}")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "event_type": "consumed",
                "lives_before": 3,
                "lives_after": 2,
                "reason": "exercise_failed",
                "metadata": {"exercise_id": "ex_123", "difficulty": 3},
                "timestamp": "2025-11-20T19:15:00Z"
            }
        }
