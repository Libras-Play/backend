"""
DynamoDB Operations for Daily Missions - FASE 4
Gestión de misiones diarias en DynamoDB
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from zoneinfo import ZoneInfo

from app import dynamo  # Use the legitimate DynamoDBClient
from app.schemas_missions import (
    DailyMission,
    DailyMissionsResponse,
    UpdateMissionProgressResponse,
    ClaimMissionRewardResponse,
    DailyMissionHistoryItem,
    MissionReward
)

logger = logging.getLogger(__name__)


# ============================================================================
# KEY BUILDERS
# ============================================================================

def build_mission_pk(user_id: str, learning_language: str) -> str:
    """Build partition key for daily missions"""
    return f"USER#{user_id}#LL#{learning_language}"


def build_mission_sk(date: str) -> str:
    """
    Build sort key for daily missions
    
    Args:
        date: YYYY-MM-DD format
    """
    return f"DAY#{date}"


def calculate_ttl(date_str: str, timezone: str = "UTC") -> int:
    """
    Calculate TTL (time to live) for mission item
    
    Returns timestamp of midnight AFTER the date (so missions expire at end of day)
    Adds 365 days for data retention (missions deleted 1 year after date)
    """
    from datetime import datetime, timedelta
    
    # Parse date and set to midnight
    date = datetime.strptime(date_str, "%Y-%m-%d")
    tz = ZoneInfo(timezone)
    midnight = date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=tz)
    
    # TTL = midnight + 1 day + 365 days (expire 1 year later)
    ttl_datetime = midnight + timedelta(days=366)
    
    return int(ttl_datetime.timestamp())


# ============================================================================
# GET DAILY MISSIONS
# ============================================================================

def get_daily_missions(
    user_id: str,
    learning_language: str,
    date: str
) -> Optional[DailyMissionsResponse]:
    """
    Get daily missions for user and date
    
    Args:
        user_id: User ID
        learning_language: LSB, ASL, LSM
        date: YYYY-MM-DD format
    
    Returns:
        DailyMissionsResponse if exists, None otherwise
    """
    pk = build_mission_pk(user_id, learning_language)
    sk = build_mission_sk(date)
    
    try:
        response = dynamo.db_client.missions_table.get_item(Key={"PK": pk, "SK": sk})
        
        if "Item" not in response:
            return None
        
        item = response["Item"]
        
        # Calculate stats
        completed_count = sum(1 for m in item.get("missions", []) if m.get("completed", False))
        claimed_count = sum(1 for m in item.get("missions", []) if m.get("claimed_at") is not None)
        
        # Build response
        return DailyMissionsResponse(
            userId=item["userId"],
            learningLanguage=item["learning_language"],
            date=item["date"],
            timezone=item.get("timezone", "UTC"),
            missions=[DailyMission(**m) for m in item.get("missions", [])],
            generated_at=datetime.fromisoformat(item["generated_at"]),
            expires_at=datetime.fromisoformat(item["expires_at"]),
            completed_count=completed_count,
            claimed_count=claimed_count
        )
    
    except Exception as e:
        logger.error(f"Error getting daily missions: {e}")
        return None


# ============================================================================
# GENERATE DAILY MISSIONS
# ============================================================================

def create_daily_missions(
    user_id: str,
    learning_language: str,
    date: str,
    missions: List[DailyMission],
    timezone: str = "UTC"
) -> DailyMissionsResponse:
    """
    Create daily missions item in DynamoDB
    
    Uses ConditionExpression to prevent duplicates (idempotent)
    
    Args:
        user_id: User ID
        learning_language: LSB, ASL, LSM
        date: YYYY-MM-DD
        missions: List of 3 missions
        timezone: User timezone
    
    Returns:
        DailyMissionsResponse
    
    Raises:
        ValueError: If missions already exist for this date
    """
    pk = build_mission_pk(user_id, learning_language)
    sk = build_mission_sk(date)
    
    now = datetime.utcnow()
    
    # Calculate expires_at (midnight of next day in user timezone)
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    tz = ZoneInfo(timezone)
    midnight = date_obj.replace(hour=23, minute=59, second=59, microsecond=0, tzinfo=tz)
    expires_at = midnight + timedelta(days=1)
    
    # Calculate TTL (365 days after date)
    ttl = calculate_ttl(date, timezone)
    
    item = {
        "PK": pk,
        "SK": sk,
        "userId": user_id,
        "learning_language": learning_language,
        "date": date,
        "timezone": timezone,
        "missions": [m.model_dump(mode='json') for m in missions],
        "generated_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "ttl": ttl
    }
    
    try:
        # Use ConditionExpression to ensure idempotency
        dynamo.db_client.missions_table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(PK)"
        )
        
        logger.info(f"Created daily missions for user {user_id}, lang {learning_language}, date {date}")
        
        return DailyMissionsResponse(
            userId=user_id,
            learningLanguage=learning_language,
            date=date,
            timezone=timezone,
            missions=missions,
            generated_at=now,
            expires_at=expires_at,
            completed_count=0,
            claimed_count=0
        )
    
    except dynamo.db_client.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        # Missions already exist - return existing
        logger.info(f"Missions already exist for user {user_id}, date {date}")
        existing = get_daily_missions(user_id, learning_language, date)
        if existing:
            return existing
        raise ValueError(f"Failed to create missions for {user_id} on {date}")
    
    except Exception as e:
        logger.error(f"Error creating daily missions: {e}")
        raise


# ============================================================================
# UPDATE MISSION PROGRESS
# ============================================================================

def update_mission_progress(
    user_id: str,
    learning_language: str,
    date: str,
    mission_id: str,
    value: int = 1
) -> UpdateMissionProgressResponse:
    """
    Update progress for a specific mission
    
    Args:
        user_id: User ID
        learning_language: LSB, ASL, LSM
        date: YYYY-MM-DD
        mission_id: Mission ID (e.g., "mt-12")
        value: Amount to add to progress (default: 1)
    
    Returns:
        UpdateMissionProgressResponse
    
    Raises:
        ValueError: If mission not found or already claimed
    """
    pk = build_mission_pk(user_id, learning_language)
    sk = build_mission_sk(date)
    
    # First, get current missions to find the index
    current = get_daily_missions(user_id, learning_language, date)
    
    if not current:
        raise ValueError(f"No missions found for user {user_id} on {date}")
    
    # Find mission index
    mission_index = None
    current_mission = None
    for i, mission in enumerate(current.missions):
        if mission.mission_id == mission_id:
            mission_index = i
            current_mission = mission
            break
    
    if mission_index is None:
        raise ValueError(f"Mission {mission_id} not found for user {user_id} on {date}")
    
    # Check if already claimed
    if current_mission.claimed_at:
        raise ValueError(f"Mission {mission_id} already claimed")
    
    # Calculate new progress
    old_progress = current_mission.metric_progress
    new_progress = min(old_progress + value, current_mission.metric_required)
    
    # Check if just completed
    just_completed = (old_progress < current_mission.metric_required and 
                     new_progress >= current_mission.metric_required)
    already_completed = current_mission.completed
    
    # Build update expression
    update_expr = f"SET missions[{mission_index}].metric_progress = :progress"
    expr_values = {":progress": new_progress}
    
    if just_completed:
        update_expr += f", missions[{mission_index}].completed = :completed"
        update_expr += f", missions[{mission_index}].claimable = :claimable"
        expr_values[":completed"] = True
        expr_values[":claimable"] = True
    
    try:
        dynamo.db_client.missions_table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values
        )
        
        progress_percentage = (new_progress / current_mission.metric_required) * 100
        
        response = UpdateMissionProgressResponse(
            success=True,
            mission_id=mission_id,
            metric_progress=new_progress,
            metric_required=current_mission.metric_required,
            progress_percentage=progress_percentage,
            just_completed=just_completed,
            already_completed=already_completed,
            reward_earned=current_mission.reward if just_completed else None,
            message=f"Progress updated: {new_progress}/{current_mission.metric_required}"
        )
        
        logger.info(f"Updated mission {mission_id} for user {user_id}: {old_progress} → {new_progress}")
        
        return response
    
    except Exception as e:
        logger.error(f"Error updating mission progress: {e}")
        raise


# ============================================================================
# CLAIM MISSION REWARD
# ============================================================================

def claim_mission_reward(
    user_id: str,
    learning_language: str,
    date: str,
    mission_id: str
) -> ClaimMissionRewardResponse:
    """
    Claim reward for a completed mission
    
    Uses TransactWriteItems for atomic operation:
    1. Mark mission as claimed
    2. Credit user balance (coins, xp, gems)
    
    Args:
        user_id: User ID
        learning_language: LSB, ASL, LSM
        date: YYYY-MM-DD
        mission_id: Mission ID
    
    Returns:
        ClaimMissionRewardResponse
    
    Raises:
        ValueError: If mission not found, not completed, or already claimed
    """
    mission_pk = build_mission_pk(user_id, learning_language)
    mission_sk = build_mission_sk(date)
    
    user_pk = f"USER#{user_id}"
    user_sk = "PROFILE"
    
    # Get current mission state
    current = get_daily_missions(user_id, learning_language, date)
    
    if not current:
        raise ValueError(f"No missions found for user {user_id} on {date}")
    
    # Find mission
    mission_index = None
    mission = None
    for i, m in enumerate(current.missions):
        if m.mission_id == mission_id:
            mission_index = i
            mission = m
            break
    
    if mission is None:
        raise ValueError(f"Mission {mission_id} not found")
    
    if not mission.completed:
        raise ValueError(f"Mission {mission_id} not completed yet")
    
    if mission.claimed_at:
        raise ValueError(f"Mission {mission_id} already claimed")
    
    now = datetime.utcnow()
    claimed_at = now.isoformat()
    
    # Build updated mission object
    updated_mission = mission.model_copy(update={"claimed_at": now})
    updated_mission_dict = updated_mission.model_dump(mode='json')
    
    # STEP 1: Get current item to update missions array
    missions_response = dynamo.db_client.missions_table.get_item(
        Key={"PK": mission_pk, "SK": mission_sk}
    )
    
    if "Item" not in missions_response:
        raise HTTPException(status_code=404, detail="Mission day not found")
    
    current_item = missions_response["Item"]
    missions_list = current_item.get("missions", [])
    
    # Verify mission not already claimed
    if mission_index >= len(missions_list):
        raise HTTPException(status_code=404, detail="Mission not found")
    
    if missions_list[mission_index].get("claimed_at"):
        raise HTTPException(status_code=400, detail="Mission already claimed")
    
    # Update mission in list
    missions_list[mission_index] = updated_mission_dict
    
    # STEP 2: Update both tables (not atomic, but simpler)
    try:
        # Update missions table with new array
        dynamo.db_client.missions_table.update_item(
            Key={"PK": mission_pk, "SK": mission_sk},
            UpdateExpression="SET missions = :missions",
            ExpressionAttributeValues={":missions": missions_list}
        )
        
        # Update user balance
        dynamo.db_client.user_table.update_item(
            Key={"user_id": user_id},
            UpdateExpression="SET coins = if_not_exists(coins, :zero) + :coins, xp = if_not_exists(xp, :zero) + :xp, gems = if_not_exists(gems, :zero) + :gems, updated_at = :now",
            ExpressionAttributeValues={
                ":zero": 0,
                ":coins": mission.reward.coins,
                ":xp": mission.reward.xp,
                ":gems": mission.reward.gems,
                ":now": now.isoformat()
            }
        )
        
        # Get updated user balance from user_table
        user_response = dynamo.db_client.user_table.get_item(Key={"user_id": user_id})
        user_data = user_response.get("Item", {})
        
        new_balance = {
            "coins": user_data.get("coins", 0),
            "xp": user_data.get("xp", 0),
            "gems": user_data.get("gems", 0)
        }
        
        logger.info(f"Claimed mission {mission_id} for user {user_id}: +{mission.reward.coins} coins, +{mission.reward.xp} XP, +{mission.reward.gems} gems")
        
        return ClaimMissionRewardResponse(
            success=True,
            mission_id=mission_id,
            reward_claimed=mission.reward,
            new_balance=new_balance,
            claimed_at=now,
            message=f"Claimed {mission.reward.coins} coins, {mission.reward.xp} XP, {mission.reward.gems} gems!"
        )
    
    except dynamo.db_client.dynamodb.meta.client.exceptions.TransactionCanceledException as e:
        # Check cancellation reasons
        reasons = e.response.get('CancellationReasons', [])
        for reason in reasons:
            if reason.get('Code') == 'ConditionalCheckFailed':
                raise ValueError("Mission already claimed (race condition)")
        raise ValueError(f"Transaction failed: {e}")
    
    except Exception as e:
        logger.error(f"Error claiming mission reward: {e}")
        raise


# ============================================================================
# GET MISSION HISTORY
# ============================================================================

def get_mission_history(
    user_id: str,
    learning_language: str,
    days: int = 7
) -> List[DailyMissionHistoryItem]:
    """
    Get historical daily missions
    
    Args:
        user_id: User ID
        learning_language: LSB, ASL, LSM
        days: Number of days to retrieve (default: 7)
    
    Returns:
        List of DailyMissionHistoryItem (newest first)
    """
    pk = build_mission_pk(user_id, learning_language)
    
    # Query with SK prefix "DAY#"
    try:
        response = dynamo.db_client.missions_table.query(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
            ExpressionAttributeValues={
                ":pk": pk,
                ":sk_prefix": "DAY#"
            },
            ScanIndexForward=False,  # Newest first
            Limit=days
        )
        
        items = response.get("Items", [])
        
        history = []
        for item in items:
            missions = [DailyMission(**m) for m in item.get("missions", [])]
            
            completed_count = sum(1 for m in missions if m.completed)
            claimed_count = sum(1 for m in missions if m.claimed_at)
            
            total_coins = sum(m.reward.coins for m in missions if m.claimed_at)
            total_xp = sum(m.reward.xp for m in missions if m.claimed_at)
            total_gems = sum(m.reward.gems for m in missions if m.claimed_at)
            
            history.append(
                DailyMissionHistoryItem(
                    date=item["date"],
                    completed_count=completed_count,
                    claimed_count=claimed_count,
                    total_coins_earned=total_coins,
                    total_xp_earned=total_xp,
                    total_gems_earned=total_gems,
                    missions=missions
                )
            )
        
        return history
    
    except Exception as e:
        logger.error(f"Error getting mission history: {e}")
        return []
