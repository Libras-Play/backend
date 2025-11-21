"""
Path progression logic (FASE 2)

Implements auto-unlock logic, progress calculations, and event emissions
for the guided learning path system.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app import dynamo, content_client

logger = logging.getLogger(__name__)


async def auto_unlock_next_topic(
    user_id: str,
    learning_language: str,
    current_topic_id: str
) -> Optional[Dict[str, Any]]:
    """
    Automatically unlock the next topic in the learning path
    
    This function is called when a user completes all levels of a topic.
    It finds the next topic by order_index, validates that it has exercises
    for the learning_language, and unlocks it if valid.
    
    Args:
        user_id: User identifier
        learning_language: Sign language code (LSB, ASL, LSM)
        current_topic_id: The topic that was just completed
        
    Returns:
        Unlocked topic data or None if no next topic available
    """
    try:
        # Get next topic from Content Service
        next_topic = await content_client.get_next_topic(current_topic_id)
        
        if not next_topic:
            logger.info(
                f"No next topic after {current_topic_id} for user {user_id}. "
                "User has completed the entire path!"
            )
            return None
        
        next_topic_id = str(next_topic.get('id'))
        order_index = next_topic.get('order_index', 0)
        
        # Check if next topic has exercises for this learning_language
        has_exercises = await content_client.topic_has_exercises_for_language(
            next_topic_id,
            learning_language
        )
        
        if not has_exercises:
            logger.warning(
                f"Next topic {next_topic_id} has no exercises for {learning_language}. "
                "Skipping auto-unlock."
            )
            # TODO: Emit TOPIC_SKIPPED_NO_CONTENT event
            return None
        
        # Check if path item already exists
        existing_path = await dynamo.get_path_topic(user_id, learning_language, next_topic_id)
        
        if existing_path:
            # Item exists, just unlock it
            unlocked_item = await dynamo.unlock_path_topic(
                user_id=user_id,
                learning_language=learning_language,
                topic_id=next_topic_id,
                method='auto',
                coins_spent=0,
                gems_spent=0
            )
        else:
            # Create new path item (unlocked)
            unlocked_item = await dynamo.create_path_item(
                user_id=user_id,
                topic_id=next_topic_id,
                learning_language=learning_language,
                order_index=order_index,
                unlocked=True,
                auto_unlocked=True,
                manual_unlock_cost_coins=100,
                manual_unlock_cost_gems=1
            )
        
        logger.info(
            f"Auto-unlocked next topic {next_topic_id} for user {user_id}, "
            f"language {learning_language}"
        )
        
        # TODO: Emit TOPIC_UNLOCKED event
        await emit_path_event(
            event_type='TOPIC_UNLOCKED',
            user_id=user_id,
            topic_id=next_topic_id,
            learning_language=learning_language,
            metadata={
                'unlockMethod': 'auto',
                'previousTopicId': current_topic_id,
                'orderIndex': order_index
            }
        )
        
        return unlocked_item
        
    except Exception as e:
        logger.error(
            f"Error auto-unlocking next topic for user {user_id}, "
            f"current topic {current_topic_id}: {str(e)}"
        )
        # Don't raise - log error but allow progression to continue
        return None


async def initialize_user_path(
    user_id: str,
    learning_language: str
) -> Dict[str, Any]:
    """
    Initialize a user's path for a specific learning language
    Creates path items for all topics, with only the first topic unlocked.
    This is idempotent - only creates items that don't exist.
    
    Args:
        user_id: User identifier
        learning_language: Sign language code (LSB, ASL, LSM)
        
    Returns:
        Dict with initialization results
    """
    try:
        # Get all topics from Content Service for this learning language
        topics = await content_client.get_topics(learning_language=learning_language)
        
        if not topics:
            logger.warning(f"No topics found in Content Service for {learning_language}")
            return {
                'userId': user_id,
                'learningLanguage': learning_language,
                'topicsCreated': 0,
                'firstTopicUnlocked': False
            }
        
        # Sort by order_index
        topics_sorted = sorted(topics, key=lambda t: t.get('order_index', 0))
        
        created_count = 0
        first_topic_unlocked = False
        
        for i, topic in enumerate(topics_sorted):
            topic_id = str(topic.get('id'))
            order_index = topic.get('order_index', i)
            
            # Check if topic has exercises for this language
            has_exercises = await content_client.topic_has_exercises_for_language(
                topic_id,
                learning_language
            )
            
            if not has_exercises:
                logger.info(
                    f"Skipping topic {topic_id} - no exercises for {learning_language}"
                )
                continue
            
            # First topic with exercises is unlocked
            is_first = (i == 0)
            
            # Check if path item already exists
            existing = await dynamo.get_path_topic(user_id, learning_language, topic_id)
            
            if not existing:
                await dynamo.create_path_item(
                    user_id=user_id,
                    topic_id=topic_id,
                    learning_language=learning_language,
                    order_index=order_index,
                    unlocked=is_first,
                    auto_unlocked=is_first,
                    manual_unlock_cost_coins=100,
                    manual_unlock_cost_gems=1
                )
                created_count += 1
                
                if is_first:
                    first_topic_unlocked = True
                    logger.info(f"First topic {topic_id} unlocked for {user_id}, {learning_language}")
        
        logger.info(
            f"Initialized path for user {user_id}, language {learning_language}: "
            f"{created_count} topics created"
        )
        
        return {
            'userId': user_id,
            'learningLanguage': learning_language,
            'topicsCreated': created_count,
            'firstTopicUnlocked': first_topic_unlocked
        }
        
    except Exception as e:
        logger.error(f"Error initializing user path: {str(e)}")
        raise


async def emit_path_event(
    event_type: str,
    user_id: str,
    topic_id: str,
    learning_language: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Emit a path-related event for integrations (SNS/EventBridge)
    
    Events can be consumed by:
    - Streak system (to update daily streaks)
    - Daily missions system (to track quest progress)
    - Badge/achievement system (to unlock achievements)
    - Analytics (to track user progression)
    
    Args:
        event_type: Event type (TOPIC_UNLOCKED, TOPIC_COMPLETED, etc.)
        user_id: User identifier
        topic_id: Topic identifier
        learning_language: Sign language code
        metadata: Additional event metadata
    """
    try:
        event_data = {
            'eventType': event_type,
            'userId': user_id,
            'topicId': topic_id,
            'learningLanguage': learning_language,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        logger.info(f"Path event emitted: {event_type} for user {user_id}, topic {topic_id}")
        
        # TODO: Implement actual SNS/EventBridge publishing
        # For now, just log the event
        # In production, publish to SNS topic or EventBridge bus
        
        # Example SNS implementation:
        # import boto3
        # sns_client = boto3.client('sns', region_name='us-east-1')
        # sns_client.publish(
        #     TopicArn=settings.SNS_TOPIC_ARN,
        #     Message=json.dumps(event_data),
        #     Subject=f'Path Event: {event_type}'
        # )
        
    except Exception as e:
        logger.error(f"Error emitting path event: {str(e)}")
        # Don't raise - event emission failures shouldn't block progression


async def calculate_path_stats(user_id: str, learning_language: str) -> Dict[str, Any]:
    """
    Calculate statistics for a user's path progression
    
    Args:
        user_id: User identifier
        learning_language: Sign language code
        
    Returns:
        Dict with totalTopics, unlockedTopics, completedTopics, progressPercentage
    """
    try:
        path_items = await dynamo.get_user_path(user_id, learning_language)
        
        total_topics = len(path_items)
        unlocked_topics = sum(1 for item in path_items if item.get('unlocked', False))
        completed_topics = sum(1 for item in path_items if item.get('completed', False))
        
        progress_percentage = 0
        if total_topics > 0:
            progress_percentage = int((completed_topics / total_topics) * 100)
        
        # Find current topic (first unlocked but not completed)
        current_topic_id = None
        for item in sorted(path_items, key=lambda x: x.get('orderIndex', 0)):
            if item.get('unlocked', False) and not item.get('completed', False):
                current_topic_id = item.get('topicId')
                break
        
        return {
            'totalTopics': total_topics,
            'unlockedTopics': unlocked_topics,
            'completedTopics': completed_topics,
            'progressPercentage': progress_percentage,
            'currentTopicId': current_topic_id
        }
        
    except Exception as e:
        logger.error(f"Error calculating path stats: {str(e)}")
        raise
