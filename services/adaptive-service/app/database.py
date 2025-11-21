"""
Database utilities for Adaptive Service

Handles:
1. DynamoDB connections (user stats, exercise history)
2. PostgreSQL connections (adaptive_logs for ML dataset)

WARNING: NO REPETIR ERROR 4
✔ Usar SIEMPRE las estructuras DynamoDB probadas:
  - PK = USER#{userId}#LL#{learning_language}
  - SK = STATS
  - SK = EXERCISE#{uuid}
✔ NO inventar tablas que no existen
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import uuid

import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class DynamoDBClient:
    """
    DynamoDB client for user data
    
    Uses VERIFIED structure from User Service:
    - Table: libras-play-dev-user-streaks
    - PK: USER#{userId}#LL#{learning_language}
    - SK: STATS | EXERCISE#{uuid}
    """
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_REGION)
        self.streaks_table = self.dynamodb.Table(settings.DYNAMODB_USER_STREAKS_TABLE)
        self.user_data_table = self.dynamodb.Table(settings.DYNAMODB_USER_DATA_TABLE)
    
    def get_user_stats(self, user_id: str, learning_language: str) -> Optional[Dict[str, Any]]:
        """
        Get user stats from DynamoDB
        
        Args:
            user_id: User ID
            learning_language: Sign language code (LSB, LIBRAS, etc.)
            
        Returns:
            Dict with xp, level, exercisesCompleted, lessonsCompleted or None
        """
        try:
            pk = f"USER#{user_id}#LL#{learning_language}"
            sk = "STATS"
            
            response = self.streaks_table.get_item(Key={'PK': pk, 'SK': sk})
            item = response.get('Item')
            
            if not item:
                logger.warning(f"No STATS found for user {user_id}, language {learning_language}")
                return None
            
            return {
                'xp': int(item.get('xp', 0)),
                'level': int(item.get('level', 1)),
                'exercisesCompleted': int(item.get('exercisesCompleted', 0)),
                'lessonsCompleted': int(item.get('lessonsCompleted', 0))
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return None
    
    def get_recent_exercises(
        self,
        user_id: str,
        learning_language: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent exercise history from DynamoDB
        
        Args:
            user_id: User ID
            learning_language: Sign language code
            limit: Max number of exercises to return
            
        Returns:
            List of exercises sorted by timestamp (newest first)
            Each exercise has: {correct, timeSpent, exerciseId, timestamp}
        """
        try:
            pk = f"USER#{user_id}#LL#{learning_language}"
            
            # Query all EXERCISE# items for this user
            response = self.streaks_table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
                ExpressionAttributeValues={
                    ':pk': pk,
                    ':sk_prefix': 'EXERCISE#'
                },
                ScanIndexForward=False,  # Newest first
                Limit=limit
            )
            
            exercises = []
            for item in response.get('Items', []):
                exercises.append({
                    'correct': item.get('correct', False),
                    'timeSpent': float(item.get('timeSpent', 0)),
                    'exerciseId': item.get('exerciseId', ''),
                    'timestamp': item.get('timestamp', ''),
                    'difficulty': int(item.get('difficulty', 1))
                })
            
            return exercises
            
        except Exception as e:
            logger.error(f"Error getting exercise history: {e}")
            return []
    
    def save_exercise_attempt(
        self,
        user_id: str,
        learning_language: str,
        exercise_id: str,
        correct: bool,
        time_spent: float,
        difficulty: int
    ) -> bool:
        """
        Save exercise attempt to DynamoDB
        
        Args:
            user_id: User ID
            learning_language: Sign language code
            exercise_id: Exercise ID
            correct: Whether answer was correct
            time_spent: Time in seconds
            difficulty: Difficulty level
            
        Returns:
            bool: Success status
        """
        try:
            pk = f"USER#{user_id}#LL#{learning_language}"
            sk = f"EXERCISE#{uuid.uuid4()}"
            
            item = {
                'PK': pk,
                'SK': sk,
                'exerciseId': exercise_id,
                'correct': correct,
                'timeSpent': time_spent,
                'difficulty': difficulty,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.streaks_table.put_item(Item=item)
            logger.info(f"Saved exercise attempt: {sk}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving exercise attempt: {e}")
            return False


class PostgreSQLClient:
    """
    PostgreSQL client for adaptive_logs table
    
    This table stores ML training dataset
    """
    
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def save_adaptive_decision(self, log_data: Dict[str, Any]) -> bool:
        """
        Save adaptive decision to PostgreSQL for ML training dataset
        
        Args:
            log_data: Decision data matching AdaptiveDecisionLog schema
            
        Returns:
            bool: Success status
        """
        try:
            session = self.SessionLocal()
            
            # Insert using raw SQL to avoid ORM overhead
            query = text("""
                INSERT INTO adaptive_logs (
                    user_id, learning_language, exercise_type,
                    current_difficulty, next_difficulty, mastery_score,
                    time_spent, correct, error_rate,
                    consistency_adjustment, error_adjustment, speed_adjustment,
                    model_used, model_prediction, timestamp
                ) VALUES (
                    :user_id, :learning_language, :exercise_type,
                    :current_difficulty, :next_difficulty, :mastery_score,
                    :time_spent, :correct, :error_rate,
                    :consistency_adjustment, :error_adjustment, :speed_adjustment,
                    :model_used, :model_prediction, :timestamp
                )
            """)
            
            session.execute(query, log_data)
            session.commit()
            session.close()
            
            logger.info(f"Saved adaptive decision for user {log_data['user_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving adaptive decision: {e}")
            return False
    
    def get_dataset_for_training(self, limit: int = 10000) -> List[Dict[str, Any]]:
        """
        Get dataset for ML model training
        
        Args:
            limit: Max records to return
            
        Returns:
            List of log records
        """
        try:
            session = self.SessionLocal()
            
            query = text("""
                SELECT * FROM adaptive_logs
                ORDER BY timestamp DESC
                LIMIT :limit
            """)
            
            result = session.execute(query, {'limit': limit})
            dataset = [dict(row._mapping) for row in result]
            session.close()
            
            logger.info(f"Retrieved {len(dataset)} records for training")
            return dataset
            
        except Exception as e:
            logger.error(f"Error retrieving training dataset: {e}")
            return []


# Singleton instances
_dynamo_client: Optional[DynamoDBClient] = None
_postgres_client: Optional[PostgreSQLClient] = None


def get_dynamo_client() -> DynamoDBClient:
    """Get singleton DynamoDB client"""
    global _dynamo_client
    if _dynamo_client is None:
        _dynamo_client = DynamoDBClient()
    return _dynamo_client


def get_postgres_client() -> PostgreSQLClient:
    """Get singleton PostgreSQL client"""
    global _postgres_client
    if _postgres_client is None:
        _postgres_client = PostgreSQLClient()
    return _postgres_client
