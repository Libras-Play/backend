"""
Streak API endpoints - FASE 3
"""
from typing import Optional
from datetime import date
from fastapi import APIRouter, Header, HTTPException, Query

from app.schemas import (
    StreakStatus,
    RecordActivityRequest,
    RecordActivityResponse,
    ClaimRewardRequest,
    ClaimRewardResponse
    # DailyActivity  # TODO: Implement when get_streak_history is ready
)
from app.logic.streak_service import (
    get_or_create_user_streak,
    record_activity,
    claim_streak_reward
    # get_streak_history  # TODO: Implement
)

router = APIRouter(prefix="/streaks", tags=["Streaks"])


@router.get("", response_model=StreakStatus)
async def get_user_streak(
    learning_language: str = Query(..., description="Learning language (LSB, ASL, LSM)"),
    x_user_id: str = Header(..., alias="X-User-ID")
):
    """Get current streak status for a user and language."""
    try:
        streak = get_or_create_user_streak(user_id=x_user_id, learning_language=learning_language)
        return StreakStatus(**streak)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record", response_model=RecordActivityResponse)
async def record_user_activity(
    request: RecordActivityRequest,
    x_user_id: str = Header(..., alias="X-User-ID")
):
    """Record a learning activity and update streak."""
    try:
        result = record_activity(
            user_id=x_user_id,
            learning_language=request.learningLanguage,
            activity_type=request.activityType,
            value=request.value,
            user_timezone=request.timezone
        )
        # record_activity already returns RecordActivityResponse object
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/claim", response_model=ClaimRewardResponse)
async def claim_reward(
    request: ClaimRewardRequest,
    x_user_id: str = Header(..., alias="X-User-ID")
):
    """Claim pending streak rewards and credit to user account."""
    try:
        result = claim_streak_reward(user_id=x_user_id, learning_language=request.learningLanguage)
        return ClaimRewardResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# TODO: Implement DailyActivity schema and get_streak_history logic
# @router.get("/history", response_model=list[DailyActivity])
# async def get_activity_history(
#     learning_language: str = Query(..., description="Learning language"),
#     days: int = Query(7, ge=1, le=90, description="Number of days to retrieve"),
#     x_user_id: str = Header(..., alias="X-User-ID")
# ):
#     """Get historical daily activity records."""
#     try:
#         history = get_streak_history(
#             user_id=x_user_id,
#             learning_language=learning_language,
#             num_days=days
#         )
#         return [DailyActivity(**item) for item in history]
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
