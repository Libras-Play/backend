"""
FASE 7: Lives Router

PATHS EXACTOS (EVITA ERROR #6):
- GET  /users/api/v1/{user_id}/lives
- POST /users/api/v1/{user_id}/lives/consume
- POST /users/api/v1/{user_id}/lives/regenerate
- POST /users/api/v1/{user_id}/lives/purchase
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import logging

from app.schemas_lives import (
    LivesStateResponse,
    ConsumeLifeRequest,
    ConsumeLifeResponse,
    RegenerateLivesRequest,
    RegenerateLivesResponse,
    PurchaseLivesRequest,
    PurchaseLivesResponse
)
from app.services.life_service import LifeService
from app.services.life_repository import LifeRepository
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter()


def get_life_service() -> LifeService:
    """Dependency injection para LifeService."""
    return LifeService(
        max_lives=settings.LIVES_MAX,
        regen_minutes=settings.LIVES_REGEN_MINUTES,
        lives_per_interval=1
    )


def get_life_repository():
    """Dependency injection para LifeRepository."""
    import boto3
    from app.config import get_settings
    settings = get_settings()
    dynamo_client = boto3.client('dynamodb', region_name=settings.AWS_REGION)
    return LifeRepository(dynamo_client)


@router.get("/api/v1/{user_id}/lives", response_model=LivesStateResponse)
async def get_user_lives(
    user_id: str,
    service: LifeService = Depends(get_life_service),
    repository: LifeRepository = Depends(get_life_repository)
):
    """
    GET /users/api/v1/{user_id}/lives
    
    Obtiene estado actual de vidas con regeneración calculada.
    BACKEND calcula todo (nunca cliente).
    """
    try:
        # Obtener datos de DynamoDB
        data = repository.get_user_lives_data(user_id)
        
        # Calcular estado actual
        state = service.calculate_current_lives(
            stored_lives=data["lives"],
            last_regen_at=data["last_regeneration_at"],
            purchased_lives=data["purchased_lives"]
        )
        
        # Construir respuesta
        return LivesStateResponse(
            user_id=user_id,
            current_lives=state["current_lives"],
            max_lives=settings.LIVES_MAX,
            last_regeneration_at=data["last_regeneration_at"].isoformat() if data["last_regeneration_at"] else None,
            next_life_at=state["next_life_at"],
            lives_maxed_at=state["lives_maxed_at"],
            time_until_next_life_seconds=state["time_until_next_life_seconds"],
            is_blocked=state["is_blocked"],
            purchased_lives=state["purchased_lives"],
            regeneration_interval_minutes=settings.LIVES_REGEN_MINUTES,
            lives_per_interval=1
        )
        
    except Exception as e:
        logger.error(f"Error getting lives for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/{user_id}/lives/consume", response_model=ConsumeLifeResponse)
async def consume_life(
    user_id: str,
    request: ConsumeLifeRequest,
    service: LifeService = Depends(get_life_service),
    repository: LifeRepository = Depends(get_life_repository)
):
    """
    POST /users/api/v1/{user_id}/lives/consume
    
    Consume una vida. Bloquea si no quedan vidas.
    """
    try:
        # Obtener estado actual
        data = repository.get_user_lives_data(user_id)
        state = service.calculate_current_lives(
            stored_lives=data["lives"],
            last_regen_at=data["last_regeneration_at"],
            purchased_lives=data["purchased_lives"]
        )
        
        lives_before = state["current_lives"]
        
        # Consumir vida
        try:
            lives_after, message = service.consume_life(
                current_lives=lives_before,
                reason=request.reason,
                force=request.force
            )
        except ValueError as e:
            if str(e) == "NO_LIVES_LEFT":
                raise HTTPException(
                    status_code=403,
                    detail="No lives remaining. Wait for regeneration or purchase lives."
                )
            raise
        
        # Actualizar DynamoDB
        purchased_to_save = state["purchased_lives"]
        if purchased_to_save > 0 and lives_after < lives_before:
            purchased_to_save = max(0, purchased_to_save - 1)
        
        success = repository.update_user_lives(
            user_id=user_id,
            new_lives=lives_after,
            new_purchased_lives=purchased_to_save,
            update_regen_timestamp=True
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update lives")
        
        # Log evento
        repository.save_life_event(
            user_id=user_id,
            event_type="consumed",
            lives_before=lives_before,
            lives_after=lives_after,
            reason=request.reason
        )
        
        # Recalcular estado
        now = datetime.now(timezone.utc)
        new_state = service.calculate_current_lives(
            stored_lives=lives_after,
            last_regen_at=now,
            purchased_lives=purchased_to_save
        )
        
        return ConsumeLifeResponse(
            user_id=user_id,
            lives_before=lives_before,
            lives_after=lives_after,
            lives_consumed=lives_before - lives_after,
            reason=request.reason,
            success=True,
            message=message,
            consumed_at=now.isoformat(),
            next_life_at=new_state["next_life_at"],
            lives_maxed_at=new_state["lives_maxed_at"],
            is_blocked=new_state["is_blocked"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error consuming life for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/{user_id}/lives/regenerate", response_model=RegenerateLivesResponse)
async def regenerate_lives(
    user_id: str,
    request: RegenerateLivesRequest,
    service: LifeService = Depends(get_life_service),
    repository: LifeRepository = Depends(get_life_repository)
):
    """
    POST /users/api/v1/{user_id}/lives/regenerate
    
    Regeneración forzada (admin/testing).
    """
    try:
        data = repository.get_user_lives_data(user_id)
        state = service.calculate_current_lives(
            stored_lives=data["lives"],
            last_regen_at=data["last_regeneration_at"],
            purchased_lives=data["purchased_lives"]
        )
        
        lives_before = state["current_lives"]
        lives_after, message = service.regenerate_life_forced(lives_before, request.amount)
        
        success = repository.update_user_lives(
            user_id=user_id,
            new_lives=lives_after,
            new_purchased_lives=state["purchased_lives"],
            update_regen_timestamp=True
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to regenerate lives")
        
        repository.save_life_event(
            user_id=user_id,
            event_type="regenerated",
            lives_before=lives_before,
            lives_after=lives_after,
            reason=request.reason
        )
        
        now = datetime.now(timezone.utc)
        new_state = service.calculate_current_lives(
            stored_lives=lives_after,
            last_regen_at=now,
            purchased_lives=state["purchased_lives"]
        )
        
        return RegenerateLivesResponse(
            user_id=user_id,
            lives_before=lives_before,
            lives_after=lives_after,
            lives_regenerated=lives_after - lives_before,
            regenerated_at=now.isoformat(),
            next_life_at=new_state["next_life_at"],
            lives_maxed_at=new_state["lives_maxed_at"]
        )
        
    except Exception as e:
        logger.error(f"Error regenerating lives for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/{user_id}/lives/purchase", response_model=PurchaseLivesResponse)
async def purchase_lives(
    user_id: str,
    request: PurchaseLivesRequest,
    service: LifeService = Depends(get_life_service),
    repository: LifeRepository = Depends(get_life_repository)
):
    """
    POST /users/api/v1/{user_id}/lives/purchase
    
    Compra de vidas (SIMULACIÓN - sin billing real).
    """
    try:
        data = repository.get_user_lives_data(user_id)
        state = service.calculate_current_lives(
            stored_lives=data["lives"],
            last_regen_at=data["last_regeneration_at"],
            purchased_lives=data["purchased_lives"]
        )
        
        lives_before = state["current_lives"]
        
        # Simular compra
        new_purchased, message, success = service.purchase_lives(
            current_lives=lives_before,
            amount=request.amount,
            payment_validated=False  # SIMULACIÓN
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        # Actualizar purchased_lives
        total_purchased = state["purchased_lives"] + new_purchased
        
        success = repository.update_user_lives(
            user_id=user_id,
            new_lives=data["lives"],
            new_purchased_lives=total_purchased,
            update_regen_timestamp=False
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to purchase lives")
        
        repository.save_life_event(
            user_id=user_id,
            event_type="purchased",
            lives_before=lives_before,
            lives_after=lives_before + new_purchased,
            reason="purchase_simulation",
            metadata={"amount": request.amount, "method": request.payment_method}
        )
        
        now = datetime.now(timezone.utc)
        
        return PurchaseLivesResponse(
            user_id=user_id,
            lives_before=lives_before,
            lives_after=lives_before + new_purchased,
            lives_purchased=new_purchased,
            success=True,
            message=message,
            purchased_at=now.isoformat(),
            transaction_id=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error purchasing lives for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
