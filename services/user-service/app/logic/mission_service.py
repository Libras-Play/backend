"""
Mission Selection Service - FASE 4
Lógica para generar y seleccionar misiones diarias
"""
import logging
import random
from datetime import datetime, date as date_type
from typing import List, Dict, Any, Optional
import httpx

from app.config import get_settings
from app.schemas_missions import DailyMission, MissionReward, MultiLangText, DailyMissionsResponse
from app import dynamo_missions

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================================================
# CONTENT SERVICE CLIENT
# ============================================================================

async def fetch_mission_templates(
    learning_language: str,
    difficulty: Optional[str] = None,
    active_only: bool = True
) -> List[Dict[str, Any]]:
    """
    Fetch mission templates from Content Service
    
    Args:
        learning_language: LSB, ASL, LSM
        difficulty: easy, medium, hard (optional)
        active_only: Only active templates
    
    Returns:
        List of mission template dicts
    """
    # Build URL
    content_service_url = settings.CONTENT_SERVICE_URL or "http://libras-play-dev-alb-1450968088.us-east-1.elb.amazonaws.com/content"
    url = f"{content_service_url}/api/v1/mission-templates"
    
    params = {
        "active_only": active_only,
        # NOTE: All templates now have [LSB, ASL, LSM], no need to filter
        # "learning_language": learning_language,
        "page_size": 100
    }
    
    if difficulty:
        params["difficulty"] = difficulty
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            templates = data.get("templates", [])
            
            logger.info(f"Fetched {len(templates)} mission templates for {learning_language}")
            return templates
    
    except Exception as e:
        logger.error(f"Error fetching mission templates: {e}")
        return []


# ============================================================================
# MISSION SELECTION ALGORITHM
# ============================================================================

def select_varied_missions(
    templates: List[Dict[str, Any]],
    count: int = 3
) -> List[Dict[str, Any]]:
    """
    Select varied missions ensuring diversity
    
    Strategy:
    1. Select 1 exercise mission (exercises_completed)
    2. Select 1 practice mission (camera_minutes, practice_seconds)
    3. Select 1 goal mission (xp_earned, topic_completed)
    
    Uses priority to rank within each category.
    
    Args:
        templates: List of mission templates
        count: Number to select (default: 3)
    
    Returns:
        List of selected templates
    """
    if not templates:
        logger.warning("No templates available for selection")
        return []
    
    # Categorize by metric_type
    exercise_missions = [t for t in templates if t["metric_type"] == "exercises_completed"]
    practice_missions = [t for t in templates if t["metric_type"] in ["camera_minutes", "practice_seconds"]]
    goal_missions = [t for t in templates if t["metric_type"] in ["xp_earned", "topic_completed"]]
    
    # Sort by priority (descending)
    exercise_missions.sort(key=lambda x: x.get("priority", 0), reverse=True)
    practice_missions.sort(key=lambda x: x.get("priority", 0), reverse=True)
    goal_missions.sort(key=lambda x: x.get("priority", 0), reverse=True)
    
    selected = []
    
    # Select 1 from each category
    if exercise_missions:
        selected.append(random.choice(exercise_missions[:3]))  # Pick from top 3 by priority
    
    if practice_missions:
        selected.append(random.choice(practice_missions[:3]))
    elif exercise_missions and len(exercise_missions) > 1:
        # Fallback: pick another exercise mission
        selected.append(random.choice([m for m in exercise_missions if m not in selected]))
    
    if goal_missions:
        selected.append(random.choice(goal_missions[:3]))
    elif exercise_missions and len(exercise_missions) > 2:
        # Fallback: pick another exercise mission
        selected.append(random.choice([m for m in exercise_missions if m not in selected]))
    
    # If we don't have 3 yet, fill with any available
    while len(selected) < count and len(selected) < len(templates):
        remaining = [t for t in templates if t not in selected]
        if remaining:
            selected.append(random.choice(remaining))
        else:
            break
    
    logger.info(f"Selected {len(selected)} missions: {[m['code'] for m in selected]}")
    
    return selected


def template_to_daily_mission(template: Dict[str, Any], order_index: int) -> DailyMission:
    """
    Convert mission template to DailyMission instance
    
    Args:
        template: Mission template dict from Content Service
        order_index: Order index (0, 1, 2)
    
    Returns:
        DailyMission
    """
    return DailyMission(
        mission_id=f"mt-{template['id']}",
        code=template["code"],
        title=MultiLangText(**template["title"]),
        description=MultiLangText(**template["description"]),
        metric_type=template["metric_type"],
        metric_required=template["metric_value"],
        metric_progress=0,
        completed=False,
        claimable=False,
        claimed_at=None,
        reward=MissionReward(
            coins=template.get("reward_coins", 0),
            xp=template.get("reward_xp", 0),
            gems=template.get("reward_gems", 0)
        ),
        image_url=template.get("image_url"),
        order_index=order_index
    )


# ============================================================================
# GENERATE DAILY MISSIONS
# ============================================================================

async def generate_daily_missions(
    user_id: str,
    learning_language: str,
    user_level: int = 1,
    timezone: str = "UTC",
    date: Optional[str] = None
) -> DailyMissionsResponse:
    """
    Generate daily missions for a user
    
    Workflow:
    1. Fetch templates from Content Service (filtered by learning_language)
    2. Determine difficulty based on user level
    3. Select 3 varied missions
    4. Create DailyMission objects
    5. Store in DynamoDB with idempotency
    
    Args:
        user_id: User ID
        learning_language: LSB, ASL, LSM
        user_level: User level (1-100) - determines difficulty
        timezone: User timezone (default: UTC)
        date: Date YYYY-MM-DD (default: today)
    
    Returns:
        DailyMissionsResponse
    
    Raises:
        ValueError: If unable to generate missions
    """
    # Determine date
    if date is None:
        date = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Check if missions already exist
    existing = dynamo_missions.get_daily_missions(user_id, learning_language, date)
    if existing:
        logger.info(f"Daily missions already exist for user {user_id} on {date}")
        return existing
    
    # Determine difficulty based on user level
    if user_level <= 10:
        difficulty = "easy"
    elif user_level <= 30:
        difficulty = "medium"
    else:
        difficulty = "hard"
    
    logger.info(f"Generating missions for user {user_id} (level {user_level}, difficulty {difficulty})")
    
    # Fetch templates from Content Service
    templates = await fetch_mission_templates(
        learning_language=learning_language,
        difficulty=difficulty,
        active_only=True
    )
    
    if not templates:
        # Fallback: try without difficulty filter
        logger.warning(f"No templates found for {learning_language}/{difficulty}, trying without difficulty filter")
        templates = await fetch_mission_templates(
            learning_language=learning_language,
            difficulty=None,
            active_only=True
        )
    
    if not templates:
        raise ValueError(f"No mission templates available for {learning_language}")
    
    # Select 3 varied missions
    selected_templates = select_varied_missions(templates, count=3)
    
    if len(selected_templates) < 3:
        raise ValueError(f"Not enough templates to generate 3 missions (found {len(selected_templates)})")
    
    # Convert to DailyMission objects
    missions = [
        template_to_daily_mission(template, order_index=i)
        for i, template in enumerate(selected_templates)
    ]
    
    # Store in DynamoDB
    try:
        response = dynamo_missions.create_daily_missions(
            user_id=user_id,
            learning_language=learning_language,
            date=date,
            missions=missions,
            timezone=timezone
        )
        
        logger.info(f"Generated daily missions for user {user_id} on {date}")
        return response
    
    except Exception as e:
        logger.error(f"Error creating daily missions: {e}")
        raise


# ============================================================================
# AUTO-TRACK MISSION PROGRESS
# ============================================================================

def auto_track_mission_progress(
    user_id: str,
    learning_language: str,
    metric_type: str,
    value: int = 1,
    date: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Auto-track mission progress based on user activity
    
    Called from other endpoints (e.g., POST /path/progress, POST /streaks/record)
    
    Args:
        user_id: User ID
        learning_language: LSB, ASL, LSM
        metric_type: exercises_completed, xp_earned, etc.
        value: Amount to increment (default: 1)
        date: Date YYYY-MM-DD (default: today)
    
    Returns:
        Dict with update result or None if no matching mission found
    """
    if date is None:
        date = datetime.utcnow().strftime("%Y-%m-%d")
    
    try:
        # Get today's missions
        missions = dynamo_missions.get_daily_missions(user_id, learning_language, date)
        
        if not missions:
            logger.debug(f"No missions found for user {user_id} on {date}")
            return None
        
        # Find mission with matching metric_type
        matching_mission = None
        for mission in missions.missions:
            if mission.metric_type == metric_type and not mission.claimed_at:
                matching_mission = mission
                break
        
        if not matching_mission:
            logger.debug(f"No matching unclaimed mission found for metric_type {metric_type}")
            return None
        
        # Update progress
        result = dynamo_missions.update_mission_progress(
            user_id=user_id,
            learning_language=learning_language,
            date=date,
            mission_id=matching_mission.mission_id,
            value=value
        )
        
        logger.info(
            f"Auto-tracked mission progress: user={user_id}, mission={matching_mission.mission_id}, "
            f"progress={result.metric_progress}/{result.metric_required}"
        )
        
        return result.model_dump()
    
    except Exception as e:
        # Non-fatal: log but don't fail the main operation
        logger.warning(f"Failed to auto-track mission progress: {e}")
        return None
