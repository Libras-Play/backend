"""
FASE 5: Event Listeners for Badge System

ANTI-ERROR PRINCIPLES:
1. Structured JSON logging for debugging
2. Try-except all listener calls to prevent cascade failures
3. Validate payloads before processing
4. Use existing badge_service functions (no duplication)
5. Emit CloudWatch metrics for observability
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from app.logic import badge_service
from app import dynamo

# Setup structured logging
logger = logging.getLogger(__name__)


# ============================================================================
# Event Payload Validators
# ============================================================================

def validate_base_event(event: Dict[str, Any]) -> Optional[str]:
    """
    Validate common fields in all events.
    
    Returns error message if invalid, None if valid
    """
    required_fields = ['userId', 'learningLanguage', 'timestamp']
    
    for field in required_fields:
        if field not in event:
            return f"Missing required field: {field}"
    
    # Validate learningLanguage
    allowed_langs = {'LSB', 'ASL', 'LSM', 'LIBRAS'}
    if event['learningLanguage'] not in allowed_langs:
        return f"Invalid learningLanguage: {event['learningLanguage']}, must be one of {allowed_langs}"
    
    return None


# ============================================================================
# Listener: Lesson Completed
# ============================================================================

def on_lesson_completed(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trigger badge evaluation when a lesson is completed.
    
    Event Payload:
    {
        "userId": "user123",
        "learningLanguage": "LSB",
        "timestamp": "2025-11-20T12:00:00Z",
        "lessonId": "lesson-001",
        "xpEarned": 10,
        "perfect": true
    }
    
    Returns:
        {
            "success": true,
            "newBadges": [...],
            "totalBadgesEarned": 5
        }
    
    ANTI-ERROR: Logs all steps, catches exceptions
    """
    correlation_id = f"lesson_{event.get('lessonId', 'unknown')}_{event.get('timestamp', '')}"
    
    log_context = {
        'event': 'on_lesson_completed',
        'correlation_id': correlation_id,
        'user_id': event.get('userId'),
        'learning_language': event.get('learningLanguage'),
        'lesson_id': event.get('lessonId')
    }
    
    logger.info(f"Lesson completed event received", extra=log_context)
    
    try:
        # Validate payload
        error = validate_base_event(event)
        if error:
            logger.error(f"Invalid event payload: {error}", extra=log_context)
            return {'success': False, 'error': error}
        
        if 'lessonId' not in event:
            logger.error("Missing lessonId in event", extra=log_context)
            return {'success': False, 'error': 'Missing lessonId'}
        
        user_id = event['userId']
        learning_language = event['learningLanguage']
        
        # Call badge evaluation
        logger.info("Evaluating badge conditions", extra=log_context)
        newly_earned = badge_service.check_and_assign_badges(user_id, learning_language)
        
        log_context['new_badges_count'] = len(newly_earned)
        log_context['new_badges'] = [b.get('badge_id') for b in newly_earned]
        
        if newly_earned:
            logger.info(f"🏆 {len(newly_earned)} new badges earned!", extra=log_context)
            # TODO: Emit to SNS topic for notifications
            # emit_badge_notification(user_id, newly_earned)
        else:
            logger.debug("No new badges earned", extra=log_context)
        
        # Emit CloudWatch metric
        emit_metric('BadgesEarnedOnLesson', len(newly_earned))
        
        return {
            'success': True,
            'newBadges': newly_earned,
            'totalBadgesEarned': len(newly_earned)
        }
        
    except Exception as e:
        logger.error(f"Error in on_lesson_completed: {str(e)}", extra=log_context, exc_info=True)
        emit_metric('BadgeEvaluationErrors', 1)
        return {'success': False, 'error': str(e)}


# ============================================================================
# Listener: Exercise Completed
# ============================================================================

def on_exercise_completed(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trigger badge evaluation when an exercise is completed.
    
    Event Payload:
    {
        "userId": "user123",
        "learningLanguage": "LSB",
        "timestamp": "2025-11-20T12:00:00Z",
        "exerciseId": "ex-001",
        "correct": true,
        "xpEarned": 5
    }
    
    ANTI-ERROR: Same pattern as lesson listener
    """
    correlation_id = f"exercise_{event.get('exerciseId', 'unknown')}_{event.get('timestamp', '')}"
    
    log_context = {
        'event': 'on_exercise_completed',
        'correlation_id': correlation_id,
        'user_id': event.get('userId'),
        'learning_language': event.get('learningLanguage'),
        'exercise_id': event.get('exerciseId')
    }
    
    logger.info(f"Exercise completed event received", extra=log_context)
    
    try:
        # Validate payload
        error = validate_base_event(event)
        if error:
            logger.error(f"Invalid event payload: {error}", extra=log_context)
            return {'success': False, 'error': error}
        
        if 'exerciseId' not in event:
            logger.error("Missing exerciseId in event", extra=log_context)
            return {'success': False, 'error': 'Missing exerciseId'}
        
        user_id = event['userId']
        learning_language = event['learningLanguage']
        
        # Call badge evaluation
        logger.info("Evaluating badge conditions", extra=log_context)
        newly_earned = badge_service.check_and_assign_badges(user_id, learning_language)
        
        log_context['new_badges_count'] = len(newly_earned)
        log_context['new_badges'] = [b.get('badge_id') for b in newly_earned]
        
        if newly_earned:
            logger.info(f"🏆 {len(newly_earned)} new badges earned!", extra=log_context)
        else:
            logger.debug("No new badges earned", extra=log_context)
        
        # Emit CloudWatch metric
        emit_metric('BadgesEarnedOnExercise', len(newly_earned))
        
        return {
            'success': True,
            'newBadges': newly_earned,
            'totalBadgesEarned': len(newly_earned)
        }
        
    except Exception as e:
        logger.error(f"Error in on_exercise_completed: {str(e)}", extra=log_context, exc_info=True)
        emit_metric('BadgeEvaluationErrors', 1)
        return {'success': False, 'error': str(e)}


# ============================================================================
# Listener: Streak Updated
# ============================================================================

def on_streak_updated(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trigger badge evaluation when streak is updated.
    
    Event Payload:
    {
        "userId": "user123",
        "learningLanguage": "LSB",
        "timestamp": "2025-11-20T12:00:00Z",
        "newStreak": 7,
        "previousStreak": 6,
        "streakIncreased": true
    }
    
    ANTI-ERROR: Only evaluate if streak increased (optimization)
    """
    correlation_id = f"streak_{event.get('userId', 'unknown')}_{event.get('timestamp', '')}"
    
    log_context = {
        'event': 'on_streak_updated',
        'correlation_id': correlation_id,
        'user_id': event.get('userId'),
        'learning_language': event.get('learningLanguage'),
        'new_streak': event.get('newStreak'),
        'streak_increased': event.get('streakIncreased')
    }
    
    logger.info(f"Streak updated event received", extra=log_context)
    
    try:
        # Validate payload
        error = validate_base_event(event)
        if error:
            logger.error(f"Invalid event payload: {error}", extra=log_context)
            return {'success': False, 'error': error}
        
        required_streak_fields = ['newStreak', 'streakIncreased']
        for field in required_streak_fields:
            if field not in event:
                logger.error(f"Missing {field} in event", extra=log_context)
                return {'success': False, 'error': f'Missing {field}'}
        
        # Optimization: Only evaluate if streak increased
        if not event['streakIncreased']:
            logger.debug("Streak did not increase, skipping badge evaluation", extra=log_context)
            return {'success': True, 'newBadges': [], 'totalBadgesEarned': 0, 'skipped': True}
        
        user_id = event['userId']
        learning_language = event['learningLanguage']
        
        # Call badge evaluation
        logger.info("Evaluating badge conditions for streak", extra=log_context)
        newly_earned = badge_service.check_and_assign_badges(user_id, learning_language)
        
        log_context['new_badges_count'] = len(newly_earned)
        log_context['new_badges'] = [b.get('badge_id') for b in newly_earned]
        
        if newly_earned:
            logger.info(f"🏆 {len(newly_earned)} new badges earned on streak!", extra=log_context)
        else:
            logger.debug("No new badges earned", extra=log_context)
        
        # Emit CloudWatch metric
        emit_metric('BadgesEarnedOnStreak', len(newly_earned))
        
        return {
            'success': True,
            'newBadges': newly_earned,
            'totalBadgesEarned': len(newly_earned)
        }
        
    except Exception as e:
        logger.error(f"Error in on_streak_updated: {str(e)}", extra=log_context, exc_info=True)
        emit_metric('BadgeEvaluationErrors', 1)
        return {'success': False, 'error': str(e)}


# ============================================================================
# Listener: Level Up
# ============================================================================

def on_level_up(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trigger badge evaluation when user levels up.
    
    Event Payload:
    {
        "userId": "user123",
        "learningLanguage": "LSB",
        "timestamp": "2025-11-20T12:00:00Z",
        "newLevel": 5,
        "previousLevel": 4,
        "totalXP": 1500
    }
    """
    correlation_id = f"levelup_{event.get('newLevel', 'unknown')}_{event.get('timestamp', '')}"
    
    log_context = {
        'event': 'on_level_up',
        'correlation_id': correlation_id,
        'user_id': event.get('userId'),
        'learning_language': event.get('learningLanguage'),
        'new_level': event.get('newLevel'),
        'previous_level': event.get('previousLevel')
    }
    
    logger.info(f"Level up event received", extra=log_context)
    
    try:
        # Validate payload
        error = validate_base_event(event)
        if error:
            logger.error(f"Invalid event payload: {error}", extra=log_context)
            return {'success': False, 'error': error}
        
        required_level_fields = ['newLevel', 'previousLevel']
        for field in required_level_fields:
            if field not in event:
                logger.error(f"Missing {field} in event", extra=log_context)
                return {'success': False, 'error': f'Missing {field}'}
        
        user_id = event['userId']
        learning_language = event['learningLanguage']
        
        # Call badge evaluation
        logger.info("Evaluating badge conditions for level up", extra=log_context)
        newly_earned = badge_service.check_and_assign_badges(user_id, learning_language)
        
        log_context['new_badges_count'] = len(newly_earned)
        log_context['new_badges'] = [b.get('badge_id') for b in newly_earned]
        
        if newly_earned:
            logger.info(f"🏆 {len(newly_earned)} new badges earned on level up!", extra=log_context)
        else:
            logger.debug("No new badges earned", extra=log_context)
        
        # Emit CloudWatch metric
        emit_metric('BadgesEarnedOnLevelUp', len(newly_earned))
        
        return {
            'success': True,
            'newBadges': newly_earned,
            'totalBadgesEarned': len(newly_earned)
        }
        
    except Exception as e:
        logger.error(f"Error in on_level_up: {str(e)}", extra=log_context, exc_info=True)
        emit_metric('BadgeEvaluationErrors', 1)
        return {'success': False, 'error': str(e)}


# ============================================================================
# Utility Functions
# ============================================================================

def emit_metric(metric_name: str, value: float):
    """
    Emit CloudWatch metric.
    
    In production, this would use boto3 CloudWatch client.
    For now, just log it.
    """
    logger.info(f"METRIC: {metric_name} = {value}")
    # TODO: Implement actual CloudWatch metrics
    # cloudwatch = boto3.client('cloudwatch')
    # cloudwatch.put_metric_data(
    #     Namespace='LibrasPlay/Badges',
    #     MetricData=[{
    #         'MetricName': metric_name,
    #         'Value': value,
    #         'Unit': 'Count',
    #         'Timestamp': datetime.utcnow()
    #     }]
    # )


def emit_badge_notification(user_id: str, badges: list):
    """
    Emit notification event to SNS topic.
    
    TODO: Implement when SNS topic is configured
    """
    logger.info(f"TODO: Send notification to user {user_id} about {len(badges)} new badges")
    # sns = boto3.client('sns')
    # sns.publish(
    #     TopicArn='arn:aws:sns:region:account:user-notifications',
    #     Message=json.dumps({
    #         'userId': user_id,
    #         'type': 'BADGE_EARNED',
    #         'badges': badges
    #     })
    # )
