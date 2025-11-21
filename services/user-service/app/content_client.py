"""
Client for Content Service API

Provides functions to fetch topics and exercises from Content Service
for path progression validation and auto-unlock logic.
"""
import httpx
import logging
from typing import Optional, Dict, Any, List
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Content Service base URL (ALB or direct)
CONTENT_SERVICE_URL = "http://libras-play-dev-alb-1450968088.us-east-1.elb.amazonaws.com/content/api/v1"

# Mapping from learning_language code to sign_language_id
SIGN_LANGUAGE_ID_MAP = {
    "LSB": 1,
    "ASL": 2,
    "LSM": 3,
    "AUSLAN": 4
}


async def get_topics(learning_language: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get all topics from Content Service
    
    NOTE: Topics in Content Service are universal (not language-specific).
    The learning_language parameter is kept for API consistency but all
    topics are returned regardless of language. Language differentiation
    happens at the exercise level.
    
    Args:
        learning_language: Optional learning language (LSB, ASL, LSM) - currently not used
    
    Returns:
        List of topics with id, title, description, order_index
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Fetch topics via /languages/3/topics (Portuguese UI language)
            # Topics are universal and contain translations for all UI languages
            response = await client.get(f"{CONTENT_SERVICE_URL}/languages/3/topics")
            response.raise_for_status()
            topics = response.json()
            
            logger.info(f"Retrieved {len(topics)} topics from Content Service")
            return topics
            
    except httpx.HTTPError as e:
        logger.error(f"Error fetching topics from Content Service: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching topics: {str(e)}")
        raise


async def get_topic(topic_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific topic from Content Service
    
    Args:
        topic_id: Topic identifier
        
    Returns:
        Topic data or None if not found
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CONTENT_SERVICE_URL}/topics/{topic_id}")
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPError as e:
        logger.error(f"Error fetching topic {topic_id}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching topic {topic_id}: {str(e)}")
        raise


async def get_exercises(
    topic_id: str,
    learning_language: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get exercises for a topic from Content Service
    
    Args:
        topic_id: Topic identifier
        learning_language: Filter by sign language (LSB, ASL, LSM)
        difficulty: Filter by difficulty (BEGINNER, INTERMEDIATE, ADVANCED)
        limit: Maximum number of exercises to return
        
    Returns:
        List of exercises
    """
    try:
        params = {"limit": limit}
        if learning_language:
            params["learning_language"] = learning_language
        if difficulty:
            params["difficulty"] = difficulty
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{CONTENT_SERVICE_URL}/topics/{topic_id}/exercises",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(
                f"Retrieved {len(data)} exercises for topic {topic_id}, "
                f"language={learning_language}, difficulty={difficulty}"
            )
            return data
            
    except httpx.HTTPError as e:
        logger.error(f"Error fetching exercises for topic {topic_id}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching exercises: {str(e)}")
        raise


async def validate_exercise_belongs_to_topic(
    exercise_id: str,
    topic_id: str,
    learning_language: str
) -> bool:
    """
    Validate that an exercise belongs to a topic and has the correct learning_language
    
    Args:
        exercise_id: Exercise identifier
        topic_id: Topic identifier
        learning_language: Expected sign language code
        
    Returns:
        True if exercise belongs to topic with correct language, False otherwise
    """
    try:
        # Get exercises for topic with specific language
        exercises = await get_exercises(
            topic_id=topic_id,
            learning_language=learning_language,
            limit=1000  # Get all to ensure we find it
        )
        
        # Check if exercise_id is in the list with matching language
        for exercise in exercises:
            if str(exercise.get('id')) == str(exercise_id):
                exercise_lang = exercise.get('learning_language')
                if exercise_lang == learning_language:
                    return True
                else:
                    logger.warning(
                        f"Exercise {exercise_id} found but language mismatch: "
                        f"expected {learning_language}, got {exercise_lang}"
                    )
                    return False
        
        logger.warning(
            f"Exercise {exercise_id} not found in topic {topic_id} "
            f"for language {learning_language}"
        )
        return False
        
    except Exception as e:
        logger.error(f"Error validating exercise: {str(e)}")
        # On error, fail open (return True) to avoid blocking users
        # Log the error for investigation
        return True


async def topic_has_exercises_for_language(topic_id: str, learning_language: str) -> bool:
    """
    Check if a topic has at least one exercise for the given learning language
    
    Args:
        topic_id: Topic identifier
        learning_language: Sign language code (LSB, ASL, LSM)
        
    Returns:
        True if topic has exercises for this language, False otherwise
    """
    try:
        exercises = await get_exercises(
            topic_id=topic_id,
            learning_language=learning_language,
            limit=1
        )
        
        has_exercises = len(exercises) > 0
        logger.info(
            f"Topic {topic_id} has exercises for {learning_language}: {has_exercises}"
        )
        return has_exercises
        
    except Exception as e:
        logger.error(
            f"Error checking exercises for topic {topic_id}, language {learning_language}: {str(e)}"
        )
        # On error, assume no exercises (safer)
        return False


async def get_next_topic(current_topic_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the next topic in order after the current topic
    
    Args:
        current_topic_id: Current topic identifier
        
    Returns:
        Next topic data or None if no next topic
    """
    try:
        # Get all topics
        topics = await get_topics()
        
        # Sort by order_index
        topics_sorted = sorted(topics, key=lambda t: t.get('order_index', 0))
        
        # Find current topic
        current_index = None
        for i, topic in enumerate(topics_sorted):
            if str(topic.get('id')) == str(current_topic_id):
                current_index = i
                break
        
        if current_index is None:
            logger.warning(f"Current topic {current_topic_id} not found in topics list")
            return None
        
        # Get next topic
        if current_index + 1 < len(topics_sorted):
            next_topic = topics_sorted[current_index + 1]
            logger.info(f"Next topic after {current_topic_id} is {next_topic.get('id')}")
            return next_topic
        else:
            logger.info(f"No next topic after {current_topic_id} (end of path)")
            return None
            
    except Exception as e:
        logger.error(f"Error getting next topic: {str(e)}")
        raise
