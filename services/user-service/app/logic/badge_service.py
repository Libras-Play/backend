"""
FASE 5: Badge Service - Business Logic

ANTI-ERROR PRINCIPLES:
1. NO cross-service imports (no Content Service dependencies)
2. Filter in memory, NOT in SQL (avoid array.contains errors)
3. Simple condition evaluation logic
4. Comprehensive logging for debugging
5. NO ORM magic, explicit logic only
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import requests
from app.config import get_settings

settings = get_settings()
from app import dynamo
from app.dynamo_badges import (
    get_user_badges,
    has_badge,
    assign_badge,
    get_badge_stats
)

logger = logging.getLogger(__name__)


# ============================================================================
# Badge Condition Evaluation
# ============================================================================

def evaluate_condition(
    condition: Dict[str, Any],
    user_stats: Dict[str, Any]
) -> bool:
    """
    Evaluate if user meets badge condition.
    
    Args:
        condition: {metric, operator, value}
            Examples:
            - {"metric": "xp_earned", "operator": ">=", "value": 1000}
            - {"metric": "streak_days", "operator": ">=", "value": 7}
            - {"metric": "exercises_completed", "operator": ">=", "value": 50}
        
        user_stats: Dictionary with user metrics
            {
                'xp': 1500,
                'level': 5,
                'streak_days': 10,
                'exercises_completed': 75,
                'topics_completed': 3,
                'camera_minutes': 120,
                ...
            }
    
    Returns:
        True if condition is met, False otherwise
        
    ANTI-ERROR: Pure logic, no ORM dependencies
    """
    metric = condition.get('metric')
    operator = condition.get('operator', '>=')
    required_value = condition.get('value', 0)
    
    # Get current value from user stats
    current_value = user_stats.get(metric, 0)
    
    # Evaluate condition
    if operator == '>=':
        result = current_value >= required_value
    elif operator == '>':
        result = current_value > required_value
    elif operator == '==':
        result = current_value == required_value
    elif operator == '<=':
        result = current_value <= required_value
    elif operator == '<':
        result = current_value < required_value
    else:
        logger.warning(f"Unknown operator: {operator}")
        return False
    
    logger.debug(
        f"Condition eval: {metric} {operator} {required_value} "
        f"(current: {current_value}) → {result}"
    )
    
    return result


def get_user_stats(user_id: str, learning_language: str) -> Dict[str, Any]:
    """
    Fetch user statistics from DynamoDB.
    
    Returns comprehensive stats for badge evaluation.
    
    ANTI-ERROR: Direct DynamoDB access, no service dependencies
    """
    try:
        from boto3.dynamodb.conditions import Key
        
        # PK for user data in streaks table
        pk = f"USER#{user_id}#LL#{learning_language}"
        
        # Query all user data
        response = dynamo.db_client.streaks_table.query(
            KeyConditionExpression=Key('PK').eq(pk)
        )
        
        items = response.get('Items', [])
        
        # Initialize stats
        stats = {
            'xp': 0,
            'level': 1,
            'streak_days': 0,
            'exercises_completed': 0,
            'topics_completed': 0,
            'camera_minutes': 0
        }
        
        # Parse items
        for item in items:
            sk = item.get('SK', '')
            
            if sk == 'STATS':
                # Extract stats
                stats['xp'] = int(item.get('xp', 0))
                stats['level'] = int(item.get('level', 1))
                stats['exercises_completed'] = int(item.get('exercisesCompleted', 0))
                stats['topics_completed'] = int(item.get('topicsCompleted', 0))
                stats['camera_minutes'] = int(item.get('cameraMinutes', 0))
                
            elif sk == 'STREAK':
                # Extract streak
                stats['streak_days'] = int(item.get('currentStreak', 0))
        
        logger.debug(f"User stats for {user_id}: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}", exc_info=True)
        return {}


def get_all_badges(learning_language: str) -> List[Dict[str, Any]]:
    """
    Get all badge definitions from Content Service.
    
    IMPORTANT: Filters in memory, NOT in SQL query.
    
    ANTI-ERROR: No array operations, filter after fetch
    """
    try:
        # Fetch from Content Service
        url = f"{settings.CONTENT_SERVICE_URL}/api/v1/badges"
        params = {'learning_language': learning_language}
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        badges = response.json()
        
        # FILTER IN MEMORY (not SQL) to avoid array.contains errors
        filtered_badges = [
            badge for badge in badges
            if badge.get('learning_language') == learning_language
        ]
        
        logger.info(f"Retrieved {len(filtered_badges)} badges for {learning_language}")
        return filtered_badges
        
    except Exception as e:
        logger.error(f"Error fetching badges from Content Service: {str(e)}")
        return []


def check_and_assign_badges(
    user_id: str,
    learning_language: str
) -> List[Dict[str, Any]]:
    """
    Check all badge conditions and assign newly earned badges.
    
    This is the MAIN function called after user actions.
    
    Returns:
        List of newly earned badges
        
    ANTI-ERROR WORKFLOW:
    1. Get user stats (DynamoDB)
    2. Get all badges (Content Service API)
    3. Get user's earned badges (DynamoDB)
    4. Filter NOT earned yet
    5. Evaluate conditions in memory
    6. Assign new badges with simple PUT
    """
    logger.info(f"Checking badges for user {user_id} ({learning_language})")
    
    # Step 1: Get user stats
    user_stats = get_user_stats(user_id, learning_language)
    if not user_stats:
        logger.warning("No user stats available")
        return []
    
    # Step 2: Get all possible badges
    all_badges = get_all_badges(learning_language)
    if not all_badges:
        logger.warning("No badges defined")
        return []
    
    # Step 3: Get already earned badges
    earned_badges = get_user_badges(dynamo, user_id, learning_language)
    earned_badge_ids = {b['badge_id'] for b in earned_badges}
    
    # Step 4: Filter not earned yet
    unearned_badges = [
        badge for badge in all_badges
        if badge['badge_id'] not in earned_badge_ids
    ]
    
    # Step 5: Evaluate conditions and assign
    newly_earned = []
    for badge in unearned_badges:
        condition = badge.get('conditions', {})
        
        if evaluate_condition(condition, user_stats):
            # Assign badge
            result = assign_badge(
                dynamo,
                user_id,
                learning_language,
                badge['badge_id']
            )
            
            if result.get('newly_earned'):
                newly_earned.append({
                    **badge,
                    'earned_at': result['earned_at']
                })
                logger.info(f"🏆 Badge earned: {badge['badge_id']} - {badge.get('title', {}).get('en')}")
    
    if newly_earned:
        logger.info(f"✅ {len(newly_earned)} new badges earned!")
    else:
        logger.debug("No new badges earned this time")
    
    return newly_earned


def get_user_badges_with_details(
    user_id: str,
    learning_language: str
) -> Dict[str, Any]:
    """
    Get user's earned badges with full details from badge master.
    
    Returns:
        {
            'earned_badges': [...],  # Full badge details
            'total_earned': int,
            'total_available': int,
            'progress_percentage': float
        }
    """
    # Get earned badges (DynamoDB)
    earned = get_user_badges(dynamo, user_id, learning_language)
    earned_ids = {b['badge_id'] for b in earned}
    
    # Get all badges (Content Service)
    all_badges = get_all_badges(learning_language)
    
    # Match earned badges with details
    earned_with_details = [
        {
            **badge,
            'earned_at': next(
                (e['earned_at'] for e in earned if e['badge_id'] == badge['badge_id']),
                None
            )
        }
        for badge in all_badges
        if badge['badge_id'] in earned_ids
    ]
    
    # Sort by earned_at (most recent first)
    earned_with_details.sort(
        key=lambda x: x.get('earned_at', 0),
        reverse=True
    )
    
    total_available = len(all_badges)
    total_earned = len(earned_with_details)
    progress_percentage = (total_earned / total_available * 100) if total_available > 0 else 0
    
    return {
        'earned_badges': earned_with_details,
        'total_earned': total_earned,
        'total_available': total_available,
        'progress_percentage': round(progress_percentage, 1)
    }


def get_all_badges_with_status(
    user_id: str,
    learning_language: str
) -> List[Dict[str, Any]]:
    """
    Get ALL badges (earned + not earned) with status.
    
    Returns:
        List of badges with 'earned' and 'earned_at' fields
    """
    # Get earned badges
    earned = get_user_badges(dynamo, user_id, learning_language)
    earned_map = {b['badge_id']: b for b in earned}
    
    # Get all badges
    all_badges = get_all_badges(learning_language)
    
    # Add earned status
    badges_with_status = []
    for badge in all_badges:
        badge_id = badge['badge_id']
        earned_data = earned_map.get(badge_id)
        
        badges_with_status.append({
            **badge,
            'earned': badge_id in earned_map,
            'earned_at': earned_data['earned_at'] if earned_data else None,
            # Hide details if hidden and not earned
            'hidden': badge.get('is_hidden', False) and not earned_data
        })
    
    return badges_with_status
