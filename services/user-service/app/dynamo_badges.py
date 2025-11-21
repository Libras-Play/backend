"""
FASE 5: Badges / Achievements - DynamoDB Operations

ANTI-ERROR DESIGN PRINCIPLES:
1. NO ARRAYS in DynamoDB items (learned from missions claim error)
2. Each badge earned = separate item (PK/SK design)
3. NO UpdateExpression on nested maps
4. Simple PUT operations only
5. NO cross-service imports
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal
import uuid
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DynamoDB Schema for user_badges
# ============================================================================
# Table: libras-play-dev-user-streaks (shared with streaks and missions)
#
# PK: USER#{userId}#LL#{learningLanguage}
# SK: BADGE#{badgeId}
#
# Attributes:
# - badgeId: str
# - earnedAt: number (Unix timestamp)
# - notified: bool (whether user was notified)
#
# WHY THIS DESIGN:
# - No arrays → No UpdateExpression errors
# - Each badge is independent item → Atomic operations
# - Easy to query all badges for user
# - No race conditions
# ============================================================================


def get_user_badges(
    dynamo,
    user_id: str,
    learning_language: str
) -> List[Dict[str, Any]]:
    """
    Get all badges earned by user for a specific learning language.
    
    Args:
        dynamo: DynamoDB client wrapper
        user_id: User ID
        learning_language: LSB, ASL, LSM
        
    Returns:
        List of badge objects with badge_id and earned_at
        
    ANTI-ERROR: Uses simple query, no complex filters
    """
    pk = f"USER#{user_id}#LL#{learning_language}"
    
    try:
        response = dynamo.db_client.streaks_table.query(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
            ExpressionAttributeValues={
                ":pk": pk,
                ":sk_prefix": "BADGE#"
            }
        )
        
        badges = []
        for item in response.get('Items', []):
            badges.append({
                'badge_id': item['SK'].replace('BADGE#', ''),
                'earned_at': item.get('earnedAt'),
                'notified': item.get('notified', False)
            })
        
        logger.info(f"Retrieved {len(badges)} badges for user {user_id} ({learning_language})")
        return badges
        
    except Exception as e:
        logger.error(f"Error getting user badges: {str(e)}")
        return []


def has_badge(
    dynamo,
    user_id: str,
    learning_language: str,
    badge_id: str
) -> bool:
    """
    Check if user has earned a specific badge.
    
    ANTI-ERROR: Direct get_item, no complex logic
    """
    pk = f"USER#{user_id}#LL#{learning_language}"
    sk = f"BADGE#{badge_id}"
    
    try:
        response = dynamo.db_client.streaks_table.get_item(
            Key={'PK': pk, 'SK': sk}
        )
        return 'Item' in response
    except Exception as e:
        logger.error(f"Error checking badge {badge_id}: {str(e)}")
        return False


def assign_badge(
    dynamo,
    user_id: str,
    learning_language: str,
    badge_id: str
) -> Dict[str, Any]:
    """
    Assign a badge to user.
    
    ANTI-ERROR DESIGN:
    - NO arrays → Just PUT a new item
    - NO UpdateExpression → Simple put_item
    - Atomic by design
    - No race conditions (idempotent)
    
    Returns:
        Badge object with earned_at timestamp
    """
    pk = f"USER#{user_id}#LL#{learning_language}"
    sk = f"BADGE#{badge_id}"
    
    # Check if already earned (idempotent)
    if has_badge(dynamo, user_id, learning_language, badge_id):
        logger.info(f"Badge {badge_id} already earned by {user_id}")
        response = dynamo.db_client.streaks_table.get_item(
            Key={'PK': pk, 'SK': sk}
        )
        item = response.get('Item', {})
        return {
            'badge_id': badge_id,
            'earned_at': item.get('earnedAt'),
            'newly_earned': False
        }
    
    # Assign new badge
    now = datetime.utcnow()
    timestamp = int(now.timestamp())
    
    try:
        dynamo.db_client.streaks_table.put_item(
            Item={
                'PK': pk,
                'SK': sk,
                'badgeId': badge_id,
                'earnedAt': timestamp,
                'notified': False,  # For future push notifications
                'createdAt': now.isoformat(),
            }
        )
        
        logger.info(f"✅ Badge {badge_id} assigned to user {user_id} ({learning_language})")
        
        return {
            'badge_id': badge_id,
            'earned_at': timestamp,
            'newly_earned': True
        }
        
    except Exception as e:
        logger.error(f"Error assigning badge {badge_id}: {str(e)}")
        raise


def get_badge_stats(
    dynamo,
    user_id: str,
    learning_language: str
) -> Dict[str, Any]:
    """
    Get badge statistics for user.
    
    Returns:
        {
            'total_earned': int,
            'by_rarity': {'common': 5, 'rare': 2, ...},
            'by_type': {'milestone': 3, 'achievement': 4, ...}
        }
    """
    badges = get_user_badges(dynamo, user_id, learning_language)
    
    return {
        'total_earned': len(badges),
        'earned_badge_ids': [b['badge_id'] for b in badges]
    }


def mark_badge_notified(
    dynamo,
    user_id: str,
    learning_language: str,
    badge_id: str
) -> bool:
    """
    Mark badge as notified (user saw the achievement popup).
    
    ANTI-ERROR: Simple update, no nested structures
    """
    pk = f"USER#{user_id}#LL#{learning_language}"
    sk = f"BADGE#{badge_id}"
    
    try:
        dynamo.db_client.streaks_table.update_item(
            Key={'PK': pk, 'SK': sk},
            UpdateExpression="SET notified = :true",
            ExpressionAttributeValues={':true': True}
        )
        return True
    except Exception as e:
        logger.error(f"Error marking badge notified: {str(e)}")
        return False
