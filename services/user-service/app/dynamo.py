"""
DynamoDB operations for user-service

Implements lazy life regeneration logic and CRUD operations for:
- UserData table
- UserProgress table  
- AiSessions table
"""
import boto3
from boto3.dynamodb.conditions import Key
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class DynamoDBClient:
    """DynamoDB client with lazy initialization"""
    
    def __init__(self):
        self.settings = settings
        self._dynamodb = None
        self._user_table = None
        self._progress_table = None
        self._sessions_table = None
        self._path_progress_table = None  # FASE 2: Path progression table
        self._streaks_table = None  # FASE 3: Streak system table
    
    @property
    def dynamodb(self):
        """Lazy initialization of DynamoDB resource"""
        if self._dynamodb is None:
            kwargs = {
                'region_name': self.settings.AWS_REGION,
            }
            
            # Only use endpoint_url for LocalStack
            if self.settings.DYNAMODB_ENDPOINT:
                kwargs['endpoint_url'] = self.settings.DYNAMODB_ENDPOINT
            
            # Only pass explicit credentials if we're in LocalStack mode (endpoint set)
            # In ECS, boto3 automatically uses the IAM role
            if self.settings.DYNAMODB_ENDPOINT and self.settings.AWS_ACCESS_KEY_ID:
                kwargs['aws_access_key_id'] = self.settings.AWS_ACCESS_KEY_ID
                kwargs['aws_secret_access_key'] = self.settings.AWS_SECRET_ACCESS_KEY
                logger.info("Using explicit AWS credentials (LocalStack mode)")
            else:
                logger.info("Using IAM role credentials (AWS/ECS mode)")
            
            self._dynamodb = boto3.resource('dynamodb', **kwargs)
        return self._dynamodb
    
    @property
    def user_table(self):
        if self._user_table is None:
            self._user_table = self.dynamodb.Table(self.settings.DYNAMODB_USER_TABLE)
        return self._user_table
    
    @property
    def progress_table(self):
        if self._progress_table is None:
            self._progress_table = self.dynamodb.Table(self.settings.DYNAMODB_PROGRESS_TABLE)
        return self._progress_table
    
    @property
    def sessions_table(self):
        if self._sessions_table is None:
            self._sessions_table = self.dynamodb.Table(self.settings.DYNAMODB_AI_SESSIONS_TABLE)
        return self._sessions_table
    
    @property
    def path_progress_table(self):
        """FASE 2: Path progression table"""
        if self._path_progress_table is None:
            self._path_progress_table = self.dynamodb.Table(self.settings.DYNAMODB_USER_PATH_PROGRESS_TABLE)
        return self._path_progress_table
    
    @property
    def streaks_table(self):
        """FASE 3: Streak system table"""
        if self._streaks_table is None:
            self._streaks_table = self.dynamodb.Table(self.settings.DYNAMODB_USER_STREAKS_TABLE)
        return self._streaks_table
    
    @property
    def missions_table(self):
        """FASE 4: Daily missions table (shared with streaks for single-table design)"""
        return self.streaks_table  # Use same table as streaks


# Global instance
db_client = DynamoDBClient()


# ============= USER DATA OPERATIONS =============

async def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user by ID with lazy life regeneration
    
    Args:
        user_id: User identifier
        
    Returns:
        User data dict or None if not found
    """
    try:
        response = db_client.user_table.get_item(Key={'user_id': user_id})
        
        if 'Item' not in response:
            return None
        
        user = python_dict(response['Item'])
        
        # Recalculate lives lazily
        user = recalculate_lives_lazy(user)
        
        # Return with camelCase keys for API response
        return snake_to_camel(user)
        
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        raise


async def create_user(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new user
    
    Args:
        payload: User data (userId, email, username, etc.)
        
    Returns:
        Created user data
    """
    try:
        logger.info(f"create_user called with payload keys: {list(payload.keys())}")
        now = datetime.utcnow().isoformat()
        
        user_data = {
            'user_id': payload['userId'],
            'email': payload['email'],
            'username': payload['username'],
            'lives': settings.LIVES_MAX,
            'lastLifeLost': None,
            'xp': 0,
            'level': 1,
            'coins': 0,  # NEW: Virtual coins
            'gems': 0,   # NEW: Premium gems
            'streakDays': 0,
            'lastStreakDate': None,
            'achievements': [],
            'pathProgress': {  # NEW: Guided path progress
                'currentTopicId': None,
                'currentDifficulty': 'BEGINNER',
                'completedExercisesCount': 0,
            },
            'settings': payload.get('settings', {}),
            'preferredLanguage': payload.get('preferredLanguage', 'pt-BR'),  # UI language
            'preferredSignLanguage': payload.get('preferredSignLanguage', 'LSB'),  # Sign language
            'createdAt': now,
            'lastLoginAt': now,
            'updatedAt': now,
        }
        
        db_client.user_table.put_item(Item=dynamodb_dict(user_data))
        
        logger.info(f"Created user: {user_data['user_id']}")
        
        # Return with camelCase keys for API response
        return snake_to_camel(user_data)
        
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise


async def update_user_lives(user_id: str, consume: int = 1) -> Dict[str, Any]:
    """
    Consume lives for a user
    
    Args:
        user_id: User identifier
        consume: Number of lives to consume (default 1)
        
    Returns:
        Updated user data with current lives
    """
    try:
        user = await get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check if user has enough lives
        if user['lives'] < consume:
            raise ValueError(f"Not enough lives. Current: {user['lives']}, needed: {consume}")
        
        now = datetime.utcnow().isoformat()
        new_lives = user['lives'] - consume
        
        # Update lives and lastLifeLost timestamp
        response = db_client.user_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET lives = :lives, lastLifeLost = :lastLifeLost, updatedAt = :updatedAt',
            ExpressionAttributeValues={
                ':lives': new_lives,
                ':lastLifeLost': now,
                ':updatedAt': now,
            },
            ReturnValues='ALL_NEW'
        )
        
        updated_user = python_dict(response['Attributes'])
        logger.info(f"User {user_id} consumed {consume} lives. Current: {new_lives}")
        
        return updated_user
        
    except Exception as e:
        logger.error(f"Error updating lives for user {user_id}: {str(e)}")
        raise


def recalculate_lives_lazy(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lazy life regeneration logic.
    Calculates how many lives have regenerated since lastLifeLost.
    Updates in-memory, caller should persist if needed.
    
    Args:
        user: User data dict
        
    Returns:
        User data with recalculated lives
    """
    current_lives = user.get('lives', settings.LIVES_MAX)
    
    # If lives are already maxed, no regeneration needed
    if current_lives >= settings.LIVES_MAX:
        user['lives'] = settings.LIVES_MAX
        user['livesMaxedAt'] = user.get('lastLifeLost') or user.get('createdAt')
        return user
    
    last_life_lost = user.get('lastLifeLost')
    if not last_life_lost:
        # No lives lost yet, should be at max
        user['lives'] = settings.LIVES_MAX
        return user
    
    # Calculate time elapsed since last life lost
    last_life_time = datetime.fromisoformat(last_life_lost)
    now = datetime.utcnow()
    elapsed_minutes = (now - last_life_time).total_seconds() / 60
    
    # Calculate lives regenerated
    regen_minutes = settings.LIVES_REGEN_MINUTES
    lives_regenerated = int(elapsed_minutes // regen_minutes)
    
    if lives_regenerated > 0:
        new_lives = min(current_lives + lives_regenerated, settings.LIVES_MAX)
        
        # Calculate when lives will be maxed
        if new_lives < settings.LIVES_MAX:
            lives_remaining = settings.LIVES_MAX - new_lives
            minutes_to_max = lives_remaining * regen_minutes
            lives_maxed_at = (now + timedelta(minutes=minutes_to_max)).isoformat()
        else:
            lives_maxed_at = now.isoformat()
        
        user['lives'] = new_lives
        user['livesMaxedAt'] = lives_maxed_at
        
        logger.debug(f"Regenerated {lives_regenerated} lives for user {user.get('user_id', user.get('userId', 'unknown'))}")
    else:
        # Calculate when next life will regenerate
        minutes_until_next = regen_minutes - (elapsed_minutes % regen_minutes)
        next_life_at = (now + timedelta(minutes=minutes_until_next)).isoformat()
        
        lives_remaining = settings.LIVES_MAX - current_lives
        minutes_to_max = lives_remaining * regen_minutes - (elapsed_minutes % regen_minutes)
        lives_maxed_at = (now + timedelta(minutes=minutes_to_max)).isoformat()
        
        user['lives'] = current_lives
        user['nextLifeAt'] = next_life_at
        user['livesMaxedAt'] = lives_maxed_at
    
    return user


async def update_user(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update user attributes
    
    Args:
        user_id: User identifier
        updates: Dict of attributes to update
        
    Returns:
        Updated user data
    """
    try:
        updates['updatedAt'] = datetime.utcnow().isoformat()
        
        # DynamoDB reserved keywords that need ExpressionAttributeNames
        reserved_keywords = {'level', 'name', 'status', 'type', 'data', 'timestamp'}
        
        # Build update expression with attribute name placeholders
        expr_attr_names = {}
        update_parts = []
        
        for k in updates.keys():
            if k.lower() in reserved_keywords:
                # Use placeholder for reserved keywords
                placeholder = f'#{k}'
                expr_attr_names[placeholder] = k
                update_parts.append(f'{placeholder} = :{k}')
            else:
                update_parts.append(f'{k} = :{k}')
        
        update_expr = 'SET ' + ', '.join(update_parts)
        expr_values = {f':{k}': dynamodb_value(v) for k, v in updates.items()}
        
        update_params = {
            'Key': {'user_id': user_id},
            'UpdateExpression': update_expr,
            'ExpressionAttributeValues': expr_values,
            'ReturnValues': 'ALL_NEW'
        }
        
        # Only add ExpressionAttributeNames if we have reserved keywords
        if expr_attr_names:
            update_params['ExpressionAttributeNames'] = expr_attr_names
        
        response = db_client.user_table.update_item(**update_params)
        
        updated_user = python_dict(response['Attributes'])
        return snake_to_camel(updated_user)
        
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise


# ============= USER PROGRESS OPERATIONS =============

async def get_user_progress(user_id: str, level_id: int) -> Optional[Dict[str, Any]]:
    """Get user progress for a specific level"""
    try:
        response = db_client.progress_table.get_item(
            Key={
                'user_id': user_id,
                'levelId': f'LEVEL#{level_id}'
            }
        )
        
        if 'Item' not in response:
            return None
        
        return python_dict(response['Item'])
        
    except Exception as e:
        logger.error(f"Error getting progress for user {user_id}, level {level_id}: {str(e)}")
        raise


async def update_progress(
    user_id: str,
    level_id: int,
    exercise_id: int,
    score: int,
    xp_earned: int,
    completed: bool = False
) -> Dict[str, Any]:
    """
    Update user progress for a level/exercise
    
    Args:
        user_id: User identifier
        level_id: Level identifier
        exercise_id: Exercise identifier
        score: Score achieved (0-100)
        xp_earned: XP earned from this attempt
        completed: Whether exercise was completed successfully
        
    Returns:
        Updated progress data
    """
    try:
        now = datetime.utcnow().isoformat()
        sk = f'LEVEL#{level_id}'
        
        # Get current progress or initialize
        current = await get_user_progress(user_id, level_id)
        
        if current:
            exercises = current.get('exercises', {})
            total_attempts = current.get('totalAttempts', 0)
            total_score = current.get('totalScore', 0)
            total_xp = current.get('xpEarned', 0)
        else:
            exercises = {}
            total_attempts = 0
            total_score = 0
            total_xp = 0
        
        # Update exercise stats
        ex_key = str(exercise_id)
        if ex_key in exercises:
            ex_data = exercises[ex_key]
            ex_data['attempts'] = ex_data.get('attempts', 0) + 1
            ex_data['bestScore'] = max(ex_data.get('bestScore', 0), score)
            if completed:
                ex_data['completed'] = True
        else:
            exercises[ex_key] = {
                'attempts': 1,
                'bestScore': score,
                'completed': completed
            }
        
        # Update totals
        total_attempts += 1
        total_score += score
        total_xp += xp_earned
        
        # Check if level is completed (all exercises completed)
        level_completed = current.get('completed', False) if current else False
        
        # Put updated progress
        progress_data = {
            'user_id': user_id,
            'levelId': sk,
            'levelIdNumber': level_id,  # For GSI
            'exercises': exercises,
            'totalAttempts': total_attempts,
            'totalScore': total_score,
            'xpEarned': total_xp,
            'completed': level_completed,
            'updatedAt': now,
        }
        
        if not current:
            progress_data['createdAt'] = now
        
        if level_completed and (not current or not current.get('completedAt')):
            progress_data['completedAt'] = now
        
        db_client.progress_table.put_item(Item=dynamodb_dict(progress_data))
        
        logger.info(f"Updated progress for user {user_id}, level {level_id}, exercise {exercise_id}")
        return progress_data
        
    except Exception as e:
        logger.error(f"Error updating progress: {str(e)}")
        raise


# ============= AI SESSIONS OPERATIONS =============

async def create_ai_session(
    session_id: str,
    user_id: str,
    exercise_id: int,
    level_id: int,
    video_url: str
) -> Dict[str, Any]:
    """Create AI processing session"""
    try:
        now = datetime.utcnow().isoformat()
        
        session_data = {
            'sessionId': session_id,
            'user_id': user_id,
            'exerciseId': exercise_id,
            'levelId': level_id,
            'videoUrl': video_url,
            'status': 'pending',
            'createdAt': now,
            'updatedAt': now,
        }
        
        db_client.sessions_table.put_item(Item=dynamodb_dict(session_data))
        
        logger.info(f"Created AI session: {session_id}")
        return session_data
        
    except Exception as e:
        logger.error(f"Error creating AI session: {str(e)}")
        raise


async def get_ai_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get AI session by ID"""
    try:
        response = db_client.sessions_table.get_item(Key={'sessionId': session_id})
        
        if 'Item' not in response:
            return None
        
        return python_dict(response['Item'])
        
    except Exception as e:
        logger.error(f"Error getting AI session {session_id}: {str(e)}")
        raise


# ============= HELPER FUNCTIONS =============

def dynamodb_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Python dict to DynamoDB compatible dict (handles Decimal)"""
    return {k: dynamodb_value(v) for k, v in data.items()}


def dynamodb_value(value: Any) -> Any:
    """Convert Python value to DynamoDB compatible value"""
    if isinstance(value, float):
        return Decimal(str(value))
    elif isinstance(value, dict):
        return {k: dynamodb_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [dynamodb_value(item) for item in value]
    return value


def python_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert DynamoDB dict to Python dict (handles Decimal)"""
    return {k: python_value(v) for k, v in data.items()}


def python_value(value: Any) -> Any:
    """Convert DynamoDB value to Python value"""
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    elif isinstance(value, dict):
        return {k: python_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [python_value(item) for item in value]
    return value


def snake_to_camel(snake_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Convert snake_case keys to camelCase for API responses"""
    camel_dict = {}
    for key, value in snake_dict.items():
        # Convert user_id -> userId, last_life_lost -> lastLifeLost, etc.
        if '_' in key:
            parts = key.split('_')
            camel_key = parts[0] + ''.join(word.capitalize() for word in parts[1:])
        else:
            camel_key = key
        camel_dict[camel_key] = value
    return camel_dict


# ============= COINS AND GEMS OPERATIONS =============

async def add_coins(user_id: str, amount: int) -> Dict[str, Any]:
    """
    Add coins to user account
    
    Args:
        user_id: User identifier
        amount: Amount of coins to add (must be positive)
        
    Returns:
        Updated user data with new coin balance
    """
    try:
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")
        
        user = await get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Get current coins (default to 0 if not exists for backward compatibility)
        current_coins = user.get('coins', 0)
        new_coins = current_coins + amount
        
        # Update in DynamoDB
        response = db_client.user_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET coins = :coins, updatedAt = :updatedAt',
            ExpressionAttributeValues={
                ':coins': new_coins,
                ':updatedAt': datetime.utcnow().isoformat()
            },
            ReturnValues='ALL_NEW'
        )
        
        updated_user = python_dict(response['Attributes'])
        logger.info(f"Added {amount} coins to user {user_id}. New total: {new_coins}")
        
        return snake_to_camel(updated_user)
        
    except Exception as e:
        logger.error(f"Error adding coins to user {user_id}: {str(e)}")
        raise


async def add_xp_direct(user_id: str, amount: int) -> Dict[str, Any]:
    """
    Add XP to user and recalculate level
    
    Args:
        user_id: User identifier
        amount: Amount of XP to add (must be positive)
        
    Returns:
        Updated user data with new XP and level
    """
    try:
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")
        
        user = await get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Import here to avoid circular dependency
        from app.logic import gamification
        
        current_xp = user.get('xp', 0)
        current_level = user.get('level', 1)
        
        new_xp = current_xp + amount
        new_level = gamification.calculate_level(new_xp)
        
        # Update in DynamoDB (user-data table)
        response = db_client.user_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET xp = :xp, #lvl = :level, updatedAt = :updatedAt',
            ExpressionAttributeNames={
                '#lvl': 'level'  # 'level' is reserved keyword
            },
            ExpressionAttributeValues={
                ':xp': new_xp,
                ':level': new_level,
                ':updatedAt': datetime.utcnow().isoformat()
            },
            ReturnValues='ALL_NEW'
        )
        
        updated_user = python_dict(response['Attributes'])
        
        # FIX FASE 2: Persist STATS in user-streaks table with PK/SK pattern
        # Assume default learning language LSB if not specified
        learning_language = user.get('preferredSignLanguage', 'LSB')
        exercises_completed = user.get('exercisesCompleted', 0)
        lessons_completed = user.get('lessonsCompleted', 0)
        
        await save_user_stats(
            user_id=user_id,
            learning_language=learning_language,
            xp=new_xp,
            level=new_level,
            exercises_completed=exercises_completed,
            lessons_completed=lessons_completed
        )
        
        logger.info(f"Added {amount} XP to user {user_id}. New XP: {new_xp}, Level: {current_level} → {new_level}")
        
        return snake_to_camel(updated_user)
        
    except Exception as e:
        logger.error(f"Error adding XP to user {user_id}: {str(e)}")
        raise


async def regenerate_lives_manual(user_id: str) -> Dict[str, Any]:
    """
    Manually regenerate lives based on time elapsed
    
    This forces recalculation of lives based on lastLifeLost timestamp.
    Useful for manual triggers or cron jobs.
    
    Args:
        user_id: User identifier
        
    Returns:
        Updated user data with regenerated lives
    """
    try:
        user = await get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        lives_before = user.get('lives', settings.LIVES_MAX)
        
        # Recalculate lives (already done in get_user, but we'll force update)
        user_recalc = recalculate_lives_lazy(user)
        lives_after = user_recalc.get('lives', lives_before)
        
        # If lives changed, update in DB
        if lives_after != lives_before:
            await update_user(user_id, {
                'lives': lives_after,
                'nextLifeAt': user_recalc.get('nextLifeAt'),
                'livesMaxedAt': user_recalc.get('livesMaxedAt')
            })
            logger.info(f"Regenerated lives for user {user_id}: {lives_before} → {lives_after}")
        else:
            logger.debug(f"No lives regenerated for user {user_id} (already at {lives_after})")
        
        return user_recalc
        
    except Exception as e:
        logger.error(f"Error regenerating lives for user {user_id}: {str(e)}")
        raise


# ============= PATH PROGRESSION OPERATIONS (FASE 2) =============

def build_path_pk(user_id: str, learning_language: str) -> str:
    """Build partition key for UserPathProgress table"""
    return f"USER#{user_id}#LL#{learning_language}"


def build_path_sk(topic_id: str) -> str:
    """Build sort key for UserPathProgress table"""
    return f"PATH#{topic_id}"


async def get_user_path(user_id: str, learning_language: str) -> List[Dict[str, Any]]:
    """
    Get all path items for a user and learning language
    
    Args:
        user_id: User identifier
        learning_language: Sign language code (LSB, ASL, LSM)
        
    Returns:
        List of path items (topics) for this user and language
    """
    try:
        pk = build_path_pk(user_id, learning_language)
        
        response = db_client.path_progress_table.query(
            KeyConditionExpression=Key('PK').eq(pk)
        )
        
        items = [python_dict(item) for item in response.get('Items', [])]
        logger.info(f"Retrieved {len(items)} path items for user {user_id}, language {learning_language}")
        
        return [snake_to_camel(item) for item in items]
        
    except Exception as e:
        logger.error(f"Error getting user path for {user_id}, {learning_language}: {str(e)}")
        raise


async def get_path_topic(user_id: str, learning_language: str, topic_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific topic's path status for user and learning language
    
    Args:
        user_id: User identifier
        learning_language: Sign language code
        topic_id: Topic identifier
        
    Returns:
        Path item dict or None if not found
    """
    try:
        pk = build_path_pk(user_id, learning_language)
        sk = build_path_sk(topic_id)
        
        response = db_client.path_progress_table.get_item(
            Key={'PK': pk, 'SK': sk}
        )
        
        if 'Item' not in response:
            return None
        
        item = python_dict(response['Item'])
        return snake_to_camel(item)
        
    except Exception as e:
        logger.error(f"Error getting path topic {topic_id} for {user_id}, {learning_language}: {str(e)}")
        raise


async def create_path_item(
    user_id: str,
    topic_id: str,
    learning_language: str,
    order_index: int = 0,
    unlocked: bool = False,
    auto_unlocked: bool = False,
    manual_unlock_cost_coins: int = 100,
    manual_unlock_cost_gems: int = 1
) -> Dict[str, Any]:
    """
    Create a new path item (topic entry) for user x learning_language
    
    This is idempotent - if item exists, returns existing item.
    
    Args:
        user_id: User identifier
        topic_id: Topic identifier
        learning_language: Sign language code
        order_index: Position in learning path (0-based)
        unlocked: Whether topic is unlocked
        auto_unlocked: Whether topic was auto-unlocked
        manual_unlock_cost_coins: Coins cost for manual unlock
        manual_unlock_cost_gems: Gems cost for manual unlock
        
    Returns:
        Created or existing path item
    """
    try:
        # Check if exists first (idempotent)
        existing = await get_path_topic(user_id, learning_language, topic_id)
        if existing:
            logger.info(f"Path item already exists for {user_id}, {learning_language}, {topic_id}")
            return existing
        
        pk = build_path_pk(user_id, learning_language)
        sk = build_path_sk(topic_id)
        now = datetime.utcnow().isoformat()
        
        item_data = {
            'PK': pk,
            'SK': sk,
            'user_id': user_id,
            'topic_id': topic_id,
            'learning_language': learning_language,
            'unlocked': unlocked,
            'completed': False,
            'levels': {
                'easy': {
                    'progress': 0,
                    'completed_exercises': 0,
                    'unlocked': unlocked,  # Easy unlocks when topic unlocks
                    'required_to_unlock': 10,
                    'completed': False
                },
                'medium': {
                    'progress': 0,
                    'completed_exercises': 0,
                    'unlocked': False,
                    'required_to_unlock': 8,
                    'completed': False
                },
                'hard': {
                    'progress': 0,
                    'completed_exercises': 0,
                    'unlocked': False,
                    'required_to_unlock': 6,
                    'completed': False
                }
            },
            'current_difficulty': 'easy',
            'order_index': order_index,
            'auto_unlocked': auto_unlocked,
            'auto_unlocked_at': now if auto_unlocked else None,
            'manual_unlock': False,
            'manual_unlock_cost_coins': manual_unlock_cost_coins,
            'manual_unlock_cost_gems': manual_unlock_cost_gems,
            'created_at': now,
            'updated_at': now
        }
        
        db_client.path_progress_table.put_item(Item=dynamodb_dict(item_data))
        logger.info(f"Created path item for {user_id}, {learning_language}, {topic_id}, unlocked={unlocked}")
        
        return snake_to_camel(item_data)
        
    except Exception as e:
        logger.error(f"Error creating path item: {str(e)}")
        raise


async def update_path_progress(
    user_id: str,
    learning_language: str,
    topic_id: str,
    difficulty: str,
    increment_exercises: int = 1
) -> Dict[str, Any]:
    """
    Update progress for a specific difficulty level within a topic
    
    Increments completed_exercises, recalculates progress percentage,
    checks if level should be marked completed, and unlocks next level if needed.
    
    Args:
        user_id: User identifier
        learning_language: Sign language code
        topic_id: Topic identifier
        difficulty: Level difficulty (easy, medium, hard)
        increment_exercises: Number of exercises to increment (default 1)
        
    Returns:
        Updated path item with new progress
    """
    try:
        pk = build_path_pk(user_id, learning_language)
        sk = build_path_sk(topic_id)
        
        # Get current item
        current = await get_path_topic(user_id, learning_language, topic_id)
        if not current:
            raise ValueError(f"Path item not found for {user_id}, {learning_language}, {topic_id}")
        
        # Get current level data
        levels = current.get('levels', {})
        level_data = levels.get(difficulty, {})
        
        completed_exercises = level_data.get('completedExercises', 0) + increment_exercises
        required = level_data.get('requiredToUnlock', 10)
        progress = min(int((completed_exercises / required) * 100), 100)
        level_completed = progress >= 100
        
        # Update level data
        level_data['completedExercises'] = completed_exercises
        level_data['progress'] = progress
        level_data['completed'] = level_completed
        
        # Check if we should unlock next level
        next_level_unlocked = False
        if level_completed:
            if difficulty == 'easy' and not levels.get('medium', {}).get('unlocked', False):
                levels['medium']['unlocked'] = True
                next_level_unlocked = True
                logger.info(f"Unlocked medium level for {topic_id}")
            elif difficulty == 'medium' and not levels.get('hard', {}).get('unlocked', False):
                levels['hard']['unlocked'] = True
                next_level_unlocked = True
                logger.info(f"Unlocked hard level for {topic_id}")
        
        # Check if all levels completed → topic completed
        topic_completed = (
            levels.get('easy', {}).get('completed', False) and
            levels.get('medium', {}).get('completed', False) and
            levels.get('hard', {}).get('completed', False)
        )
        
        # Update in DynamoDB
        now = datetime.utcnow().isoformat()
        response = db_client.path_progress_table.update_item(
            Key={'PK': pk, 'SK': sk},
            UpdateExpression='SET levels = :levels, completed = :completed, updated_at = :updated_at',
            ExpressionAttributeValues={
                ':levels': dynamodb_dict(levels),
                ':completed': topic_completed,
                ':updated_at': now
            },
            ReturnValues='ALL_NEW'
        )
        
        updated_item = python_dict(response['Attributes'])
        logger.info(
            f"Updated path progress: {user_id}, {topic_id}, {difficulty} → "
            f"{progress}% ({completed_exercises}/{required}), "
            f"level_completed={level_completed}, topic_completed={topic_completed}"
        )
        
        return snake_to_camel(updated_item)
        
    except Exception as e:
        logger.error(f"Error updating path progress: {str(e)}")
        raise


async def unlock_path_topic(
    user_id: str,
    learning_language: str,
    topic_id: str,
    method: str = 'manual',
    coins_spent: int = 0,
    gems_spent: int = 0
) -> Dict[str, Any]:
    """
    Unlock a topic in the user's path
    
    Args:
        user_id: User identifier
        learning_language: Sign language code
        topic_id: Topic identifier
        method: Unlock method (auto, manual, already_unlocked)
        coins_spent: Coins spent for manual unlock
        gems_spent: Gems spent for manual unlock
        
    Returns:
        Updated path item
    """
    try:
        pk = build_path_pk(user_id, learning_language)
        sk = build_path_sk(topic_id)
        now = datetime.utcnow().isoformat()
        
        # Check if already unlocked
        current = await get_path_topic(user_id, learning_language, topic_id)
        if current and current.get('unlocked', False):
            logger.info(f"Topic {topic_id} already unlocked for {user_id}, {learning_language}")
            return current
        
        # Prepare update expression
        update_expr = 'SET unlocked = :unlocked, updated_at = :updated_at, levels.easy.unlocked = :easy_unlocked'
        expr_values = {
            ':unlocked': True,
            ':updated_at': now,
            ':easy_unlocked': True
        }
        
        if method == 'auto':
            update_expr += ', auto_unlocked = :auto_unlocked, auto_unlocked_at = :auto_unlocked_at'
            expr_values[':auto_unlocked'] = True
            expr_values[':auto_unlocked_at'] = now
        elif method == 'manual':
            update_expr += ', manual_unlock = :manual_unlock'
            expr_values[':manual_unlock'] = True
        
        # Update item
        response = db_client.path_progress_table.update_item(
            Key={'PK': pk, 'SK': sk},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ReturnValues='ALL_NEW'
        )
        
        updated_item = python_dict(response['Attributes'])
        logger.info(f"Unlocked topic {topic_id} for {user_id}, {learning_language} via {method}")
        
        # If manual unlock, deduct coins/gems from user
        if method == 'manual' and (coins_spent > 0 or gems_spent > 0):
            user = await get_user(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            current_coins = user.get('coins', 0)
            current_gems = user.get('gems', 0)
            
            if coins_spent > current_coins or gems_spent > current_gems:
                raise ValueError(
                    f"Insufficient funds. Required: {coins_spent} coins, {gems_spent} gems. "
                    f"Available: {current_coins} coins, {current_gems} gems"
                )
            
            await update_user(user_id, {
                'coins': current_coins - coins_spent,
                'gems': current_gems - gems_spent
            })
            logger.info(f"Deducted {coins_spent} coins, {gems_spent} gems from user {user_id}")
        
        return snake_to_camel(updated_item)
        
    except Exception as e:
        logger.error(f"Error unlocking path topic: {str(e)}")
        raise


# ============= FASE 3: STREAK SYSTEM OPERATIONS =============

def build_streak_pk(user_id: str, learning_language: str) -> str:
    """
    Build partition key for streak items
    
    Args:
        user_id: User identifier
        learning_language: Sign language code (LSB, ASL, LSM)
    
    Returns:
        Partition key in format: USER#<userId>#LL#<learningLanguage>
    
    Example:
        >>> build_streak_pk("123", "LSB")
        "USER#123#LL#LSB"
    """
    return f"USER#{user_id}#LL#{learning_language}"


def build_streak_sk(period_type: str = "DAILY", period_value: str = "current") -> str:
    """
    Build sort key for streak items
    
    Args:
        period_type: Period type (DAILY, WEEKLY, MONTHLY) - default DAILY
        period_value: Period identifier ("current" or date YYYY-MM-DD)
    
    Returns:
        Sort key in format: STREAK#<periodType>#<periodValue>
    
    Examples:
        >>> build_streak_sk("DAILY", "current")
        "STREAK#DAILY#current"
        >>> build_streak_sk("DAILY", "2025-11-19")
        "STREAK#DAILY#2025-11-19"
    """
    return f"STREAK#{period_type}#{period_value}"


def get_user_streak(
    user_id: str, 
    learning_language: str,
    period_type: str = "DAILY",
    period_value: str = "current"
) -> Optional[Dict[str, Any]]:
    """
    Get current or historical streak for user and learning language
    
    Args:
        user_id: User identifier
        learning_language: Sign language code
        period_type: DAILY, WEEKLY, or MONTHLY
        period_value: "current" or date (YYYY-MM-DD)
    
    Returns:
        Streak item dict or None if not found
    
    Raises:
        Exception: If DynamoDB query fails
    """
    try:
        pk = build_streak_pk(user_id, learning_language)
        sk = build_streak_sk(period_type, period_value)
        
        response = db_client.streaks_table.get_item(
            Key={"PK": pk, "SK": sk}
        )
        
        item = response.get('Item')
        if item:
            logger.info(f"Retrieved streak for user {user_id}, language {learning_language}")
            return snake_to_camel(item)
        
        logger.info(f"No streak found for user {user_id}, language {learning_language}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting user streak: {str(e)}")
        raise


def create_streak_item(
    user_id: str,
    learning_language: str,
    timezone: str = "UTC",
    metric_required: int = 3
) -> Dict[str, Any]:
    """
    Create initial streak item for user and learning language (idempotent)
    
    Args:
        user_id: User identifier
        learning_language: Sign language code
        timezone: User's IANA timezone (default UTC)
        metric_required: Required daily activities (default 3)
    
    Returns:
        Created or existing streak item
    
    Raises:
        Exception: If DynamoDB operation fails
    """
    try:
        pk = build_streak_pk(user_id, learning_language)
        sk = build_streak_sk("DAILY", "current")
        now = datetime.utcnow().isoformat()
        
        # Idempotent create with condition: only create if doesn't exist
        response = db_client.streaks_table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression="""
                SET 
                    user_id = if_not_exists(user_id, :user_id),
                    learning_language = if_not_exists(learning_language, :ll),
                    current_streak = if_not_exists(current_streak, :zero),
                    best_streak = if_not_exists(best_streak, :zero),
                    metric_count_today = if_not_exists(metric_count_today, :zero),
                    metric_required = if_not_exists(metric_required, :mr),
                    reward_granted_today = if_not_exists(reward_granted_today, :false),
                    pending_reward_coins = if_not_exists(pending_reward_coins, :zero),
                    pending_reward_gems = if_not_exists(pending_reward_gems, :zero),
                    pending_reward_xp = if_not_exists(pending_reward_xp, :zero),
                    #tz = if_not_exists(#tz, :tz),
                    streak_health = if_not_exists(streak_health, :health),
                    created_at = if_not_exists(created_at, :now),
                    updated_at = :now
            """,
            ExpressionAttributeNames={
                "#tz": "timezone"
            },
            ExpressionAttributeValues={
                ":user_id": user_id,
                ":ll": learning_language,
                ":zero": 0,
                ":mr": metric_required,
                ":false": False,
                ":tz": timezone,
                ":health": "active",
                ":now": now
            },
            ReturnValues="ALL_NEW"
        )
        
        created_item = response['Attributes']
        logger.info(f"Created/retrieved streak item for user {user_id}, language {learning_language}")
        return snake_to_camel(created_item)
        
    except Exception as e:
        logger.error(f"Error creating streak item: {str(e)}")
        raise


def update_streak_activity(
    user_id: str,
    learning_language: str,
    activity_count: int = 1,
    new_streak_value: Optional[int] = None,
    new_best_streak: Optional[int] = None,
    reward_coins: int = 0,
    reward_gems: int = 0,
    reward_xp: int = 0,
    last_activity_day: Optional[str] = None,
    streak_health: str = "active"
) -> Dict[str, Any]:
    """
    Update streak with new activity (atomic operation)
    
    Args:
        user_id: User identifier
        learning_language: Sign language code
        activity_count: Number of activities to add (default 1)
        new_streak_value: New streak value if incrementing (None = no change)
        reward_coins: Pending coins to add
        reward_gems: Pending gems to add
        reward_xp: Pending XP to add
        last_activity_day: Last activity date (YYYY-MM-DD)
        streak_health: Streak health status (active, at_risk, broken)
    
    Returns:
        Updated streak item
    
    Raises:
        Exception: If DynamoDB operation fails or concurrent modification detected
    """
    try:
        pk = build_streak_pk(user_id, learning_language)
        sk = build_streak_sk("DAILY", "current")
        now = datetime.utcnow().isoformat()
        
        # Build dynamic UpdateExpression based on what needs to be updated
        set_parts = ["updated_at = :now", "streak_health = :health"]
        add_parts = ["metric_count_today :count"]
        
        attr_values = {
            ":count": activity_count,
            ":now": now,
            ":health": streak_health
        }
        
        attr_names = {}
        
        # Update streak value if provided
        if new_streak_value is not None:
            set_parts.append("current_streak = :streak")
            attr_values[":streak"] = new_streak_value
        
        # Update best streak if provided
        if new_best_streak is not None:
            set_parts.append("best_streak = :best")
            attr_values[":best"] = new_best_streak
        
        # Update last activity day if provided
        if last_activity_day:
            set_parts.append("last_activity_day = :day")
            attr_values[":day"] = last_activity_day
        
        # Add pending rewards if provided
        if reward_coins > 0:
            add_parts.append("pending_reward_coins :coins")
            attr_values[":coins"] = reward_coins
        
        if reward_gems > 0:
            add_parts.append("pending_reward_gems :gems")
            attr_values[":gems"] = reward_gems
        
        if reward_xp > 0:
            add_parts.append("pending_reward_xp :xp")
            attr_values[":xp"] = reward_xp
        
        # Set reward_granted_today if rewards were granted
        if reward_coins > 0 or reward_gems > 0 or reward_xp > 0:
            set_parts.append("reward_granted_today = :true")
            attr_values[":true"] = True
        
        # Build complete update expression
        update_expression = "SET " + ", ".join(set_parts)
        if add_parts:
            update_expression += " ADD " + ", ".join(add_parts)
        
        update_params = {
            "Key": {"PK": pk, "SK": sk},
            "UpdateExpression": update_expression,
            "ExpressionAttributeValues": attr_values,
            "ReturnValues": "ALL_NEW"
        }
        
        if attr_names:
            update_params["ExpressionAttributeNames"] = attr_names
        
        response = db_client.streaks_table.update_item(**update_params)
        
        updated_item = response['Attributes']
        logger.info(f"Updated streak activity for user {user_id}, language {learning_language}: +{activity_count} activities")
        return snake_to_camel(updated_item)
        
    except Exception as e:
        logger.error(f"Error updating streak activity: {str(e)}")
        raise


def claim_streak_reward(
    user_id: str,
    learning_language: str
) -> tuple[Dict[str, Any], Dict[str, int]]:
    """
    Claim pending streak rewards and credit user account (atomic operation)
    
    Args:
        user_id: User identifier
        learning_language: Sign language code
    
    Returns:
        Tuple of (updated_streak_item, rewards_claimed)
        rewards_claimed: {"coins": int, "gems": int, "xp": int}
    
    Raises:
        Exception: If DynamoDB operation fails or no pending rewards
    """
    try:
        # First, get current pending rewards
        streak = get_user_streak(user_id, learning_language)
        if not streak:
            raise ValueError(f"No streak found for user {user_id}, language {learning_language}")
        
        pending_coins = streak.get('pendingRewardCoins', 0)
        pending_gems = streak.get('pendingRewardGems', 0)
        pending_xp = streak.get('pendingRewardXp', 0)
        
        if pending_coins == 0 and pending_gems == 0 and pending_xp == 0:
            raise ValueError("No pending rewards to claim")
        
        # Atomic operation: credit user account AND clear pending rewards
        # Using TransactWriteItems for atomicity across tables
        now = datetime.utcnow().isoformat()
        pk = build_streak_pk(user_id, learning_language)
        sk = build_streak_sk("DAILY", "current")
        
        transact_items = []
        
        # Update user's coins, gems, XP
        user_update = {
            'Update': {
                'TableName': db_client.user_table.name,
                'Key': {'user_id': user_id},
                'UpdateExpression': 'ADD coins :coins, gems :gems, xp :xp SET updated_at = :now',
                'ExpressionAttributeValues': {
                    ':coins': pending_coins,
                    ':gems': pending_gems,
                    ':xp': pending_xp,
                    ':now': now
                }
            }
        }
        transact_items.append(user_update)
        
        # Clear pending rewards in streak table
        streak_update = {
            'Update': {
                'TableName': db_client.streaks_table.name,
                'Key': {'PK': pk, 'SK': sk},
                'UpdateExpression': '''
                    SET 
                        pending_reward_coins = :zero,
                        pending_reward_gems = :zero,
                        pending_reward_xp = :zero,
                        last_claimed_at = :now,
                        updated_at = :now
                ''',
                'ExpressionAttributeValues': {
                    ':zero': 0,
                    ':now': now
                },
                'ConditionExpression': 'attribute_exists(PK)'  # Ensure item exists
            }
        }
        transact_items.append(streak_update)
        
        # Execute atomic transaction
        db_client.dynamodb.meta.client.transact_write_items(
            TransactItems=transact_items
        )
        
        logger.info(f"Claimed rewards for user {user_id}: {pending_coins} coins, {pending_gems} gems, {pending_xp} XP")
        
        # Return updated streak and rewards claimed
        updated_streak = get_user_streak(user_id, learning_language)
        rewards_claimed = {
            "coins": pending_coins,
            "gems": pending_gems,
            "xp": pending_xp
        }
        
        return updated_streak, rewards_claimed
        
    except Exception as e:
        logger.error(f"Error claiming streak reward: {str(e)}")
        raise


def get_streak_history(
    user_id: str,
    learning_language: str,
    days: int = 30
) -> List[Dict[str, Any]]:
    """
    Get historical streak records for user and learning language
    
    Args:
        user_id: User identifier
        learning_language: Sign language code
        days: Number of days of history to retrieve (default 30)
    
    Returns:
        List of historical streak items (sorted by date descending)
    
    Raises:
        Exception: If DynamoDB query fails
    """
    try:
        pk = build_streak_pk(user_id, learning_language)
        
        # Query all historical items (SK starts with STREAK#DAILY#)
        response = db_client.streaks_table.query(
            KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('STREAK#DAILY#'),
            ScanIndexForward=False,  # Sort descending (newest first)
            Limit=days + 1  # +1 to include "current" item
        )
        
        items = response.get('Items', [])
        
        # Convert to camelCase and filter out "current" item
        history = []
        for item in items:
            if item['SK'] != 'STREAK#DAILY#current':
                history.append(snake_to_camel(item))
        
        logger.info(f"Retrieved {len(history)} days of streak history for user {user_id}, language {learning_language}")
        return history[:days]  # Ensure we don't return more than requested
        
    except Exception as e:
        logger.error(f"Error getting streak history: {str(e)}")
        raise


def check_suspicious_activity(
    user_id: str,
    learning_language: str,
    new_timezone: str,
    current_streak: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Check for suspicious timezone manipulation activity
    
    Anti-cheat: Detect if user is changing timezone to manipulate streak
    
    Args:
        user_id: User identifier
        learning_language: Sign language code
        new_timezone: New timezone being set
        current_streak: Current streak item (optional, will fetch if not provided)
    
    Returns:
        True if suspicious activity detected, False otherwise
    
    Detection Rules:
        - Timezone changed < 24 hours ago: SUSPICIOUS
        - Multiple timezone changes in 7 days: SUSPICIOUS
        - Timezone offset jump > 12 hours: SUSPICIOUS (possible day manipulation)
    """
    try:
        if current_streak is None:
            current_streak = get_user_streak(user_id, learning_language)
        
        if not current_streak:
            # No existing streak, first timezone set is OK
            return False
        
        current_tz = current_streak.get('timezone', 'UTC')
        last_changed = current_streak.get('timezoneLastChanged')
        timezone_changes_count = current_streak.get('timezoneChangesCount', 0)
        
        # Same timezone, no change
        if current_tz == new_timezone:
            return False
        
        # Check if timezone changed recently (< 24 hours)
        if last_changed:
            last_changed_dt = datetime.fromisoformat(last_changed.replace('Z', '+00:00'))
            hours_since_change = (datetime.utcnow() - last_changed_dt.replace(tzinfo=None)).total_seconds() / 3600
            
            if hours_since_change < 24:
                logger.warning(f"SUSPICIOUS: User {user_id} changed timezone < 24h ago (was {current_tz}, now {new_timezone})")
                return True
        
        # Check for excessive timezone changes (> 3 changes in 7 days)
        if timezone_changes_count >= 3:
            logger.warning(f"SUSPICIOUS: User {user_id} has changed timezone {timezone_changes_count} times recently")
            return True
        
        # TODO: Optionally check timezone offset jump (requires timezone library)
        # from zoneinfo import ZoneInfo
        # offset_jump = abs(ZoneInfo(new_timezone).utcoffset() - ZoneInfo(current_tz).utcoffset())
        # if offset_jump > timedelta(hours=12): return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking suspicious activity: {str(e)}")
        # Fail open: don't block user on error
        return False


# ============================================================================
# FASE 5: HELPER FUNCTIONS FOR PK/SK PATTERNS
# ============================================================================
# ANTI-ERROR: Centralize PK/SK construction to avoid table/structure mistakes

def get_user_pk(user_id: str, learning_language: str) -> str:
    """
    Get PK for user data in single-table design.
    
    ANTI-ERROR: Use this instead of manual string construction
    
    Args:
        user_id: User identifier
        learning_language: LSB, ASL, LSM, etc.
    
    Returns:
        PK string: "USER#{user_id}#LL#{learning_language}"
    """
    return f"USER#{user_id}#LL#{learning_language}"


def query_user_items(
    user_id: str, 
    learning_language: str,
    sk_prefix: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Query all items for a user in single-table design.
    
    ANTI-ERROR: Consistent query pattern for user data
    
    Args:
        user_id: User identifier
        learning_language: LSB, ASL, LSM, etc.
        sk_prefix: Optional SK prefix to filter (e.g., "BADGE#", "STATS")
    
    Returns:
        List of items matching the query
    
    Example:
        # Get all user items
        items = query_user_items("user123", "LSB")
        
        # Get only badges
        badges = query_user_items("user123", "LSB", sk_prefix="BADGE#")
    """
    pk = get_user_pk(user_id, learning_language)
    
    try:
        if sk_prefix:
            response = db_client.streaks_table.query(
                KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with(sk_prefix)
            )
        else:
            response = db_client.streaks_table.query(
                KeyConditionExpression=Key('PK').eq(pk)
            )
        
        return response.get('Items', [])
        
    except Exception as e:
        logger.error(f"Error querying user items: {str(e)}")
        return []


def update_item_with_version(
    pk: str,
    sk: str,
    updates: Dict[str, Any],
    expected_version: Optional[int] = None
) -> Dict[str, Any]:
    """
    Update DynamoDB item with optimistic locking.
    
    ANTI-ERROR: Atomic updates for race conditions
    
    Args:
        pk: Partition key
        sk: Sort key
        updates: Dict of attributes to update
        expected_version: Expected current version (for optimistic lock)
    
    Returns:
        Updated item or raises error if version mismatch
    
    Example:
        # First read
        item = streaks_table.get_item(Key={'PK': pk, 'SK': sk})['Item']
        current_version = item.get('version', 0)
        
        # Update with version check
        updated = update_item_with_version(
            pk, sk, 
            {'missions': new_missions_list},
            expected_version=current_version
        )
    """
    try:
        # Build update expression
        update_expr_parts = []
        expr_values = {}
        
        # Add version increment
        new_version = (expected_version or 0) + 1
        update_expr_parts.append('version = :new_version')
        expr_values[':new_version'] = new_version
        
        # Add other updates
        for key, value in updates.items():
            update_expr_parts.append(f'{key} = :{key}')
            expr_values[f':{key}'] = value
        
        update_expr = 'SET ' + ', '.join(update_expr_parts)
        
        # Build condition expression
        kwargs = {
            'Key': {'PK': pk, 'SK': sk},
            'UpdateExpression': update_expr,
            'ExpressionAttributeValues': expr_values,
            'ReturnValues': 'ALL_NEW'
        }
        
        if expected_version is not None:
            kwargs['ConditionExpression'] = 'version = :expected_version'
            expr_values[':expected_version'] = expected_version
        
        response = db_client.streaks_table.update_item(**kwargs)
        return response['Attributes']
        
    except db_client.streaks_table.meta.client.exceptions.ConditionalCheckFailedException:
        logger.error(f"Version mismatch: expected {expected_version}, item was modified")
        raise ValueError(f"Concurrent modification detected. Please retry.")
    except Exception as e:
        logger.error(f"Error updating item with version: {str(e)}")
        raise


def get_or_initialize_version(pk: str, sk: str) -> int:
    """
    Get current version of an item, or initialize to 0.
    
    ANTI-ERROR: Safe version retrieval for new items
    """
    try:
        response = db_client.streaks_table.get_item(
            Key={'PK': pk, 'SK': sk}
        )
        item = response.get('Item', {})
        return int(item.get('version', 0))
    except Exception as e:
        logger.error(f"Error getting version: {str(e)}")
        return 0


# ============= STATS PERSISTENCE (FIX FASE 2) =============

async def save_user_stats(user_id: str, learning_language: str, xp: int, level: int, 
                         exercises_completed: int = 0, lessons_completed: int = 0) -> Dict[str, Any]:
    """
    Persist user stats in DynamoDB with PK/SK pattern.
    
    FIX: Stats now persist between sessions (not just in memory).
    
    Args:
        user_id: User ID
        learning_language: Learning language (LSB, ASL, LSM, LIBRAS)
        xp: Total XP
        level: Current level
        exercises_completed: Total exercises completed
        lessons_completed: Total lessons completed
        
    Returns:
        Saved stats data
    """
    try:
        pk = get_user_pk(user_id, learning_language)
        sk = "STATS"
        
        stats_data = {
            'PK': pk,
            'SK': sk,
            'user_id': user_id,
            'learning_language': learning_language,
            'xp': xp,
            'level': level,
            'exercisesCompleted': exercises_completed,
            'lessonsCompleted': lessons_completed,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        db_client.streaks_table.put_item(Item=stats_data)
        logger.info(f"Saved STATS for user {user_id}, lang {learning_language}: XP={xp}, Level={level}")
        
        return stats_data
        
    except Exception as e:
        logger.error(f"Error saving user stats: {str(e)}")
        raise


async def get_user_stats(user_id: str, learning_language: str) -> Optional[Dict[str, Any]]:
    """
    Get user stats from DynamoDB.
    
    Returns:
        Stats data or None if not found
    """
    try:
        pk = get_user_pk(user_id, learning_language)
        sk = "STATS"
        
        response = db_client.streaks_table.get_item(
            Key={'PK': pk, 'SK': sk}
        )
        
        return response.get('Item')
        
    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}")
        return None


# ============================================================================
# FASE 9: USER TOPIC PROGRESS OPERATIONS
# ============================================================================

def get_topic_progress_pk(user_id: str, learning_language: str) -> str:
    """Generate PK for topic progress: USER#{user_id}#{learning_language}"""
    return f"USER#{user_id}#{learning_language}"


def get_topic_progress_sk(topic_id: str) -> str:
    """Generate SK for topic progress: TOPIC_PROGRESS#{topic_id}"""
    return f"TOPIC_PROGRESS#{topic_id}"


async def get_topic_progress(user_id: str, learning_language: str, topic_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user topic progress from DynamoDB.
    
    FASE 9: Tracks user progress for a specific topic.
    
    Args:
        user_id: User identifier
        learning_language: Sign language (LSB, ASL, LSM)
        topic_id: Topic ID (as string)
    
    Returns:
        Progress data or None if not found
        {
            "user_id": str,
            "learning_language": str,
            "topic_id": str,
            "total_exercises_available": int,
            "exercises_completed": int,
            "mastery_score": float (0.0-1.0),
            "difficulty_level_estimated": str ("beginner"|"intermediate"|"advanced"),
            "last_update_timestamp": str (ISO 8601),
            "created_at": str (ISO 8601)
        }
    """
    try:
        pk = get_topic_progress_pk(user_id, learning_language)
        sk = get_topic_progress_sk(topic_id)
        
        response = db_client.streaks_table.get_item(
            Key={'PK': pk, 'SK': sk}
        )
        
        item = response.get('Item')
        
        if item:
            logger.info(f"Retrieved topic progress: user={user_id}, topic={topic_id}, completed={item.get('exercises_completed', 0)}")
        
        return item
        
    except Exception as e:
        logger.error(f"Error getting topic progress: {str(e)}")
        return None


async def create_topic_progress(
    user_id: str,
    learning_language: str,
    topic_id: str,
    total_exercises_available: int
) -> Dict[str, Any]:
    """
    Create initial topic progress entry.
    
    FASE 9: Initializes progress tracking for a new topic.
    
    Args:
        user_id: User identifier
        learning_language: Sign language
        topic_id: Topic ID
        total_exercises_available: Total exercises in topic (from Content Service)
    
    Returns:
        Created progress data
    """
    try:
        pk = get_topic_progress_pk(user_id, learning_language)
        sk = get_topic_progress_sk(topic_id)
        now = datetime.utcnow().isoformat()
        
        progress_data = {
            'PK': pk,
            'SK': sk,
            'user_id': user_id,
            'learning_language': learning_language,
            'topic_id': topic_id,
            'total_exercises_available': total_exercises_available,
            'exercises_completed': 0,
            'mastery_score': Decimal('0.0'),
            'difficulty_level_estimated': 'beginner',
            'last_update_timestamp': now,
            'created_at': now
        }
        
        db_client.streaks_table.put_item(Item=progress_data)
        logger.info(f"Created topic progress: user={user_id}, topic={topic_id}, total={total_exercises_available}")
        
        return progress_data
        
    except Exception as e:
        logger.error(f"Error creating topic progress: {str(e)}")
        raise


async def update_topic_progress(
    user_id: str,
    learning_language: str,
    topic_id: str,
    exercises_completed: int = None,
    total_exercises_available: int = None,
    mastery_score: float = None,
    difficulty_level_estimated: str = None
) -> Dict[str, Any]:
    """
    Update topic progress atomically.
    
    FASE 9: Updates progress after exercise completion or sync.
    
    Args:
        user_id: User identifier
        learning_language: Sign language
        topic_id: Topic ID
        exercises_completed: New completed count (optional)
        total_exercises_available: New total (from sync, optional)
        mastery_score: New mastery score 0.0-1.0 (optional)
        difficulty_level_estimated: New difficulty level (optional)
    
    Returns:
        Updated progress data
    """
    try:
        pk = get_topic_progress_pk(user_id, learning_language)
        sk = get_topic_progress_sk(topic_id)
        now = datetime.utcnow().isoformat()
        
        # Build update expression dynamically
        update_parts = []
        expression_values = {':timestamp': now}
        expression_names = {}
        
        if exercises_completed is not None:
            update_parts.append('#completed = :completed')
            expression_values[':completed'] = exercises_completed
            expression_names['#completed'] = 'exercises_completed'
        
        if total_exercises_available is not None:
            update_parts.append('#total = :total')
            expression_values[':total'] = total_exercises_available
            expression_names['#total'] = 'total_exercises_available'
        
        if mastery_score is not None:
            # Validate range
            if not (0.0 <= mastery_score <= 1.0):
                raise ValueError(f"mastery_score must be between 0.0 and 1.0, got {mastery_score}")
            update_parts.append('mastery_score = :mastery')
            expression_values[':mastery'] = Decimal(str(mastery_score))
        
        if difficulty_level_estimated is not None:
            # Validate values
            if difficulty_level_estimated not in ['beginner', 'intermediate', 'advanced']:
                raise ValueError(f"Invalid difficulty_level_estimated: {difficulty_level_estimated}")
            update_parts.append('difficulty_level_estimated = :difficulty')
            expression_values[':difficulty'] = difficulty_level_estimated
        
        # Always update timestamp
        update_parts.append('last_update_timestamp = :timestamp')
        
        update_expression = 'SET ' + ', '.join(update_parts)
        
        kwargs = {
            'Key': {'PK': pk, 'SK': sk},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values,
            'ReturnValues': 'ALL_NEW'
        }
        
        if expression_names:
            kwargs['ExpressionAttributeNames'] = expression_names
        
        response = db_client.streaks_table.update_item(**kwargs)
        
        updated_item = response.get('Attributes', {})
        
        logger.info(
            f"Updated topic progress: user={user_id}, topic={topic_id}, "
            f"completed={updated_item.get('exercises_completed')}, "
            f"mastery={updated_item.get('mastery_score')}"
        )
        
        return updated_item
        
    except Exception as e:
        logger.error(f"Error updating topic progress: {str(e)}")
        raise


async def increment_topic_exercises_completed(
    user_id: str,
    learning_language: str,
    topic_id: str,
    increment: int = 1
) -> Dict[str, Any]:
    """
    Atomically increment exercises_completed counter.
    
    FASE 9: Called when user completes an exercise correctly.
    
    Args:
        user_id: User identifier
        learning_language: Sign language
        topic_id: Topic ID
        increment: Amount to increment (default 1)
    
    Returns:
        Updated progress data
    """
    try:
        pk = get_topic_progress_pk(user_id, learning_language)
        sk = get_topic_progress_sk(topic_id)
        now = datetime.utcnow().isoformat()
        
        response = db_client.streaks_table.update_item(
            Key={'PK': pk, 'SK': sk},
            UpdateExpression='ADD exercises_completed :inc SET last_update_timestamp = :timestamp',
            ExpressionAttributeValues={
                ':inc': increment,
                ':timestamp': now
            },
            ReturnValues='ALL_NEW'
        )
        
        updated_item = response.get('Attributes', {})
        
        logger.info(
            f"Incremented topic exercises: user={user_id}, topic={topic_id}, "
            f"new_total={updated_item.get('exercises_completed')}"
        )
        
        return updated_item
        
    except Exception as e:
        logger.error(f"Error incrementing topic exercises: {str(e)}")
        raise


async def calculate_and_update_mastery(
    user_id: str,
    learning_language: str,
    topic_id: str
) -> Dict[str, Any]:
    """
    Calculate mastery_score and difficulty_level_estimated based on progress.
    
    FASE 9: Recalculates mastery after exercise completion.
    
    Formula:
        mastery_score = exercises_completed / total_exercises_available
        
    Difficulty level rules:
        mastery < 0.33 → beginner
        0.33 <= mastery < 0.66 → intermediate
        mastery >= 0.66 → advanced
    
    Args:
        user_id: User identifier
        learning_language: Sign language
        topic_id: Topic ID
    
    Returns:
        Updated progress data with new mastery_score and difficulty_level_estimated
    """
    try:
        # Get current progress
        progress = await get_topic_progress(user_id, learning_language, topic_id)
        
        if not progress:
            raise ValueError(f"Topic progress not found for user {user_id}, topic {topic_id}")
        
        completed = progress.get('exercises_completed', 0)
        total = progress.get('total_exercises_available', 1)  # Avoid division by zero
        
        # Calculate mastery score
        if total == 0:
            mastery_score = 0.0
        else:
            mastery_score = float(completed) / float(total)
        
        # Determine difficulty level
        if mastery_score < 0.33:
            difficulty_level = 'beginner'
        elif mastery_score < 0.66:
            difficulty_level = 'intermediate'
        else:
            difficulty_level = 'advanced'
        
        # Update in DB
        updated = await update_topic_progress(
            user_id=user_id,
            learning_language=learning_language,
            topic_id=topic_id,
            mastery_score=mastery_score,
            difficulty_level_estimated=difficulty_level
        )
        
        logger.info(
            f"Calculated mastery: user={user_id}, topic={topic_id}, "
            f"mastery={mastery_score:.2f}, level={difficulty_level}"
        )
        
        return updated
        
    except Exception as e:
        logger.error(f"Error calculating mastery: {str(e)}")
        raise


