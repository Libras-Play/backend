"""
Streak Service - Business logic for daily streak system (FASE 3)

Handles:
- Activity recording with timezone awareness
- Streak state calculation (consecutive days, breaks, resets)
- Reward calculation (base + multiplier + milestones)
- Anti-cheat detection (timezone fraud, suspicious activity)
- Event emission for streak state changes
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from zoneinfo import ZoneInfo
import logging

from app.dynamo import (
    get_user_streak,
    create_streak_item,
    update_streak_activity,
    check_suspicious_activity
)
from app.schemas import (
    StreakStatus,
    RecordActivityResponse,
    RewardGranted,
    StreakEvent
)

logger = logging.getLogger(__name__)

# Reward configuration
BASE_DAILY_COINS = 10  # Base coins for meeting daily goal
STREAK_MULTIPLIER_COINS = 2  # Additional coins per streak day
MILESTONE_DAYS = 7  # Days between gem rewards
MILESTONE_GEMS = 1  # Gems per milestone

# Activity limits (anti-cheat)
MAX_DAILY_ACTIVITIES = 100  # Cap on daily activity count


def get_user_day(timezone: str, now_utc: Optional[datetime] = None) -> str:
    """
    Convert UTC time to user's local date
    
    Args:
        timezone: User's IANA timezone (e.g., "America/Sao_Paulo")
        now_utc: Current UTC time (defaults to datetime.utcnow())
    
    Returns:
        Date string in YYYY-MM-DD format in user's timezone
    
    Example:
        >>> get_user_day("America/Sao_Paulo", datetime(2025, 11, 19, 2, 0))  # 2 AM UTC
        "2025-11-18"  # Still Nov 18 in São Paulo (UTC-3)
    """
    if now_utc is None:
        now_utc = datetime.utcnow()
    
    try:
        tz = ZoneInfo(timezone)
        local_time = now_utc.replace(tzinfo=ZoneInfo('UTC')).astimezone(tz)
        return local_time.strftime("%Y-%m-%d")
    except Exception as e:
        logger.warning(f"Invalid timezone {timezone}, falling back to UTC: {e}")
        # Fallback to UTC
        return now_utc.strftime("%Y-%m-%d")


def is_consecutive_day(last_day: str, current_day: str, timezone: str) -> bool:
    """
    Check if current_day is exactly 1 day after last_day in user's timezone
    
    Args:
        last_day: Last activity date (YYYY-MM-DD)
        current_day: Current activity date (YYYY-MM-DD)
        timezone: User's IANA timezone
    
    Returns:
        True if days are consecutive, False otherwise
    
    Examples:
        >>> is_consecutive_day("2025-11-18", "2025-11-19", "UTC")
        True
        >>> is_consecutive_day("2025-11-18", "2025-11-20", "UTC")
        False
    """
    try:
        last_dt = datetime.strptime(last_day, "%Y-%m-%d")
        current_dt = datetime.strptime(current_day, "%Y-%m-%d")
        
        # Check if exactly 1 day apart
        delta = (current_dt - last_dt).days
        return delta == 1
        
    except Exception as e:
        logger.error(f"Error checking consecutive days: {e}")
        return False


def calculate_streak_state(
    current_state: Dict[str, Any],
    user_day: str,
    yesterday_day: str
) -> Tuple[int, str, bool]:
    """
    Calculate new streak state based on current state and activity day
    
    Args:
        current_state: Current streak item from DynamoDB
        user_day: Today's date in user timezone (YYYY-MM-DD)
        yesterday_day: Yesterday's date in user timezone (YYYY-MM-DD)
    
    Returns:
        Tuple of (new_streak_value, streak_health, streak_updated)
        - new_streak_value: New streak count
        - streak_health: "active", "at_risk", or "broken"
        - streak_updated: True if streak incremented, False if maintained or broken
    
    Logic:
        - If activity today AND goal met yesterday: streak continues (+1)
        - If activity today BUT no activity yesterday: streak resets to 1
        - If last activity was 2+ days ago: streak broken (0)
        - If last activity was yesterday: streak at risk (no increment)
    """
    current_streak = current_state.get('currentStreak', 0)
    last_activity_day = current_state.get('lastActivityDay')
    metric_count_today = current_state.get('metricCountToday', 0)
    metric_required = current_state.get('metricRequired', 3)
    timezone = current_state.get('timezone', 'UTC')
    
    # First activity ever
    if not last_activity_day:
        logger.info(f"First activity ever, starting streak at 1")
        return 1, "active", True
    
    # Same day activity (no streak change)
    if last_activity_day == user_day:
        logger.info(f"Activity on same day {user_day}, streak maintained at {current_streak}")
        return current_streak, "active", False
    
    # Check if consecutive days
    if is_consecutive_day(last_activity_day, user_day, timezone):
        # Consecutive day: increment streak
        new_streak = current_streak + 1
        logger.info(f"Consecutive day activity: streak incremented from {current_streak} to {new_streak}")
        return new_streak, "active", True
    
    # Check if last activity was yesterday (at risk)
    if last_activity_day == yesterday_day:
        logger.info(f"Last activity was yesterday, streak at risk at {current_streak}")
        return current_streak, "at_risk", False
    
    # Last activity was 2+ days ago: streak broken
    logger.warning(f"Streak broken: last activity {last_activity_day}, current day {user_day}")
    return 1, "active", True  # Start new streak at 1


def grant_rewards(current_streak: int, new_streak: int) -> Dict[str, int]:
    """
    Calculate rewards based on streak progression
    
    Args:
        current_streak: Streak value before increment
        new_streak: Streak value after increment
    
    Returns:
        Dict with {"coins": int, "gems": int, "xp": int}
    
    Reward Formula:
        - Base: 10 coins per day
        - Multiplier: +2 coins per streak day
        - Milestone: 1 gem every 7 days
        - XP: Same as coins
    
    Examples:
        >>> grant_rewards(0, 1)
        {"coins": 12, "gems": 0, "xp": 12}  # Day 1: 10 + (1*2)
        >>> grant_rewards(6, 7)
        {"coins": 24, "gems": 1, "xp": 24}  # Day 7: 10 + (7*2) + milestone
    """
    coins = BASE_DAILY_COINS + (new_streak * STREAK_MULTIPLIER_COINS)
    gems = 0
    xp = coins  # XP mirrors coins
    
    # Check for milestone gem reward
    if new_streak > 0 and new_streak % MILESTONE_DAYS == 0:
        gems = MILESTONE_GEMS
        logger.info(f"Milestone reached at streak {new_streak}: granting {gems} gems")
    
    logger.info(f"Rewards calculated for streak {new_streak}: {coins} coins, {gems} gems, {xp} XP")
    return {"coins": coins, "gems": gems, "xp": xp}


def detect_timezone_fraud(
    user_id: str,
    learning_language: str,
    new_timezone: str,
    current_state: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Detect suspicious timezone changes (anti-cheat)
    
    Args:
        user_id: User identifier
        learning_language: Sign language code
        new_timezone: New timezone being set
        current_state: Current streak state (optional)
    
    Returns:
        True if fraud detected, False otherwise
    
    Detection:
        - Timezone changed < 24 hours ago
        - Multiple timezone changes in short period
        - Delegates to check_suspicious_activity in dynamo.py
    """
    return check_suspicious_activity(
        user_id=user_id,
        learning_language=learning_language,
        new_timezone=new_timezone,
        current_streak=current_state
    )


def emit_streak_event(
    event_type: str,
    user_id: str,
    learning_language: str,
    current_streak: int,
    previous_streak: Optional[int] = None,
    reward_granted: Optional[Dict[str, int]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Emit streak event for external systems (SNS, EventBridge)
    
    Args:
        event_type: STREAK_UPDATED, STREAK_BROKEN, STREAK_REWARDED, etc.
        user_id: User identifier
        learning_language: Sign language code
        current_streak: Current streak value
        previous_streak: Previous streak value (optional)
        reward_granted: Reward dict (optional)
        metadata: Additional event metadata (optional)
    
    TODO: Integrate with SNS/EventBridge for real-time notifications
    """
    event = StreakEvent(
        eventType=event_type,
        userId=user_id,
        learningLanguage=learning_language,
        currentStreak=current_streak,
        previousStreak=previous_streak,
        rewardGranted=RewardGranted(
            coins=reward_granted.get('coins', 0),
            gems=reward_granted.get('gems', 0),
            xp=reward_granted.get('xp', 0),
            reason=f"Streak day {current_streak}",
            milestone=current_streak if current_streak % MILESTONE_DAYS == 0 else None
        ) if reward_granted else None,
        timestamp=datetime.utcnow().isoformat(),
        metadata=metadata or {}
    )
    
    logger.info(f"STREAK EVENT: {event_type} for user {user_id}, language {learning_language}, streak {current_streak}")
    
    # TODO: Publish to SNS topic
    # sns_client.publish(
    #     TopicArn=settings.SNS_TOPIC_ARN,
    #     Message=event.model_dump_json()
    # )


def record_activity(
    user_id: str,
    learning_language: str,
    activity_type: str = "exercise_complete",
    value: int = 1,
    exercise_id: Optional[str] = None,
    user_timezone: Optional[str] = None
) -> RecordActivityResponse:
    """
    Record user activity and update streak (MAIN ENTRY POINT)
    
    Args:
        user_id: User identifier
        learning_language: Sign language code (LSB, ASL, LSM)
        activity_type: Type of activity (exercise_complete, xp_earned, etc.)
        value: Activity count (default 1)
        exercise_id: Exercise ID if applicable
        user_timezone: User's timezone (will fetch from profile if not provided)
    
    Returns:
        RecordActivityResponse with streak status and rewards
    
    Flow:
        1. Get/create user streak
        2. Check timezone fraud
        3. Calculate user's current day
        4. Determine if streak continues/breaks/starts
        5. Update activity count (capped at MAX_DAILY_ACTIVITIES)
        6. Grant rewards if daily goal met
        7. Update DynamoDB atomically
        8. Emit events
        9. Return response
    
    Raises:
        ValueError: If invalid parameters or activity limit exceeded
        Exception: If DynamoDB operation fails
    """
    try:
        # 1. Get or create streak
        current_state = get_user_streak(user_id, learning_language)
        
        if not current_state:
            # Create initial streak item
            timezone = user_timezone or "UTC"
            current_state = create_streak_item(
                user_id=user_id,
                learning_language=learning_language,
                timezone=timezone
            )
            logger.info(f"Created initial streak for user {user_id}, language {learning_language}")
        
        timezone = current_state.get('timezone', 'UTC')
        
        # 2. Check timezone fraud (if timezone provided and different)
        if user_timezone and user_timezone != timezone:
            if detect_timezone_fraud(user_id, learning_language, user_timezone, current_state):
                logger.warning(f"SUSPICIOUS ACTIVITY: Timezone fraud detected for user {user_id}")
                emit_streak_event(
                    event_type="SUSPICIOUS_ACTIVITY",
                    user_id=user_id,
                    learning_language=learning_language,
                    current_streak=current_state.get('currentStreak', 0),
                    metadata={
                        "reason": "timezone_fraud",
                        "old_timezone": timezone,
                        "new_timezone": user_timezone
                    }
                )
                # Allow activity but flag it
                timezone = user_timezone  # Update timezone
        
        # 3. Calculate user's current day
        now_utc = datetime.utcnow()
        user_day = get_user_day(timezone, now_utc)
        yesterday_day = get_user_day(timezone, now_utc - timedelta(days=1))
        
        # 4. Calculate streak state
        current_streak = current_state.get('currentStreak', 0)
        new_streak, streak_health, streak_updated = calculate_streak_state(
            current_state=current_state,
            user_day=user_day,
            yesterday_day=yesterday_day
        )
        
        # 5. Update activity count (capped)
        metric_count_today = current_state.get('metricCountToday', 0)
        metric_required = current_state.get('metricRequired', 3)
        reward_granted_today = current_state.get('rewardGrantedToday', False)
        
        # Anti-cheat: Cap daily activities
        if metric_count_today + value > MAX_DAILY_ACTIVITIES:
            logger.warning(f"Activity limit exceeded for user {user_id}: {metric_count_today} + {value} > {MAX_DAILY_ACTIVITIES}")
            value = max(0, MAX_DAILY_ACTIVITIES - metric_count_today)
        
        new_metric_count = metric_count_today + value
        
        # 6. Grant rewards if daily goal met AND not already rewarded today
        reward_coins = 0
        reward_gems = 0
        reward_xp = 0
        reward_granted = None
        
        if new_metric_count >= metric_required and not reward_granted_today and streak_updated:
            rewards = grant_rewards(current_streak, new_streak)
            reward_coins = rewards['coins']
            reward_gems = rewards['gems']
            reward_xp = rewards['xp']
            
            reward_granted = RewardGranted(
                coins=reward_coins,
                gems=reward_gems,
                xp=reward_xp,
                reason=f"Daily goal met - streak day {new_streak}",
                milestone=new_streak if new_streak % MILESTONE_DAYS == 0 else None
            )
            
            logger.info(f"Rewards granted to user {user_id}: {reward_coins} coins, {reward_gems} gems, {reward_xp} XP")
        
        # 7. Update DynamoDB atomically
        best_streak = current_state.get('bestStreak', 0)
        new_best = max(best_streak, new_streak) if streak_updated else best_streak
        
        updated_state = update_streak_activity(
            user_id=user_id,
            learning_language=learning_language,
            activity_count=value,
            new_streak_value=new_streak if streak_updated else None,
            new_best_streak=new_best if new_best > best_streak else None,
            reward_coins=reward_coins,
            reward_gems=reward_gems,
            reward_xp=reward_xp,
            last_activity_day=user_day,
            streak_health=streak_health
        )
        
        # 8. Emit events
        if streak_updated:
            event_type = "STREAK_UPDATED" if new_streak > current_streak else "STREAK_BROKEN"
            emit_streak_event(
                event_type=event_type,
                user_id=user_id,
                learning_language=learning_language,
                current_streak=new_streak,
                previous_streak=current_streak,
                reward_granted={"coins": reward_coins, "gems": reward_gems, "xp": reward_xp} if reward_granted else None,
                metadata={
                    "activity_type": activity_type,
                    "exercise_id": exercise_id,
                    "metric_count": new_metric_count
                }
            )
        
        if reward_granted:
            emit_streak_event(
                event_type="STREAK_REWARDED",
                user_id=user_id,
                learning_language=learning_language,
                current_streak=new_streak,
                reward_granted={"coins": reward_coins, "gems": reward_gems, "xp": reward_xp},
                metadata={
                    "milestone": new_streak % MILESTONE_DAYS == 0
                }
            )
        
        # 9. Build response
        progress = min(100, (new_metric_count / metric_required) * 100)
        next_milestone = ((new_streak // MILESTONE_DAYS) + 1) * MILESTONE_DAYS
        
        message = _build_response_message(
            streak_updated=streak_updated,
            new_streak=new_streak,
            progress=progress,
            reward_granted=reward_granted
        )
        
        return RecordActivityResponse(
            success=True,
            streakUpdated=streak_updated,
            currentStreak=new_streak,
            metricCountToday=new_metric_count,
            metricRequired=metric_required,
            progress=progress,
            rewardGranted=reward_granted,
            nextMilestone=next_milestone,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Error recording activity: {str(e)}")
        raise


def _build_response_message(
    streak_updated: bool,
    new_streak: int,
    progress: float,
    reward_granted: Optional[RewardGranted]
) -> str:
    """Build user-friendly response message"""
    if reward_granted:
        if reward_granted.milestone:
            return f"🎉 Milestone reached! {new_streak} day streak - {reward_granted.coins} coins + {reward_granted.gems} gems!"
        else:
            return f"🔥 {new_streak} day streak - {reward_granted.coins} coins earned!"
    
    if streak_updated:
        return f"🔥 Streak updated to {new_streak} days!"
    
    if progress >= 100:
        return f"✅ Daily goal complete! Claim your reward."
    
    return f"📊 Progress: {int(progress)}% towards daily goal"


# Exported functions for router compatibility
def get_or_create_user_streak(user_id: str, learning_language: str) -> Dict[str, Any]:
    """Get or create user streak - wrapper for router"""
    current_state = get_user_streak(user_id, learning_language)
    if not current_state:
        current_state = create_streak_item(
            user_id=user_id,
            learning_language=learning_language,
            timezone="UTC"
        )
    return current_state


def claim_streak_reward(user_id: str, learning_language: str) -> Dict[str, Any]:
    """Claim pending streak rewards - wrapper for router"""
    # TODO: Implement reward claiming logic
    current_state = get_user_streak(user_id, learning_language)
    if not current_state:
        raise ValueError("No streak found for user")
    
    # Return dummy response for now
    return {
        "success": True,
        "coins_granted": 0,
        "gems_granted": 0,
        "xp_granted": 0,
        "message": "No pending rewards"
    }
