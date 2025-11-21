"""
Tests for User Service with moto (DynamoDB mocking)
"""
import pytest
from moto import mock_aws
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

from app import dynamo, schemas
from app.logic import gamification
from app.config import get_settings


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials for moto"""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")


@pytest.fixture
def dynamodb_tables(aws_credentials):
    """Create mock DynamoDB tables"""
    with mock_aws():
        # Create DynamoDB resource
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        
        # Create UserData table
        dynamodb.create_table(
            TableName="UserData",
            KeySchema=[{"AttributeName": "userId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "userId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        
        # Create UserProgress table
        dynamodb.create_table(
            TableName="UserProgress",
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "levelId", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "levelId", "AttributeType": "S"},
                {"AttributeName": "levelIdNumber", "AttributeType": "N"}
            ],
            GlobalSecondaryIndexes=[{
                "IndexName": "levelId-index",
                "KeySchema": [{"AttributeName": "levelIdNumber", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"}
            }],
            BillingMode="PAY_PER_REQUEST"
        )
        
        # Create AiSessions table
        dynamodb.create_table(
            TableName="AiSessions",
            KeySchema=[{"AttributeName": "sessionId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "sessionId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        
        yield dynamodb


@pytest.mark.asyncio
async def test_create_user(dynamodb_tables):
    """Test user creation"""
    user_data = {
        "userId": "test-user-123",
        "email": "test@example.com",
        "username": "testuser",
        "preferredLanguage": "LSB"
    }
    
    user = await dynamo.create_user(user_data)
    
    assert user["userId"] == "test-user-123"
    assert user["email"] == "test@example.com"
    assert user["lives"] == 5  # Max lives on creation
    assert user["xp"] == 0
    assert user["level"] == 1
    assert user["streakDays"] == 0
    assert user["achievements"] == []


@pytest.mark.asyncio
async def test_get_user(dynamodb_tables):
    """Test getting user with lazy lives regeneration"""
    # Create user
    user_data = {
        "userId": "test-user-456",
        "email": "test2@example.com",
        "username": "testuser2"
    }
    await dynamo.create_user(user_data)
    
    # Get user
    user = await dynamo.get_user("test-user-456")
    
    assert user is not None
    assert user["userId"] == "test-user-456"
    assert user["lives"] == 5


@pytest.mark.asyncio
async def test_consume_lives(dynamodb_tables):
    """Test consuming lives"""
    # Create user
    user_data = {
        "userId": "test-user-789",
        "email": "test3@example.com",
        "username": "testuser3"
    }
    await dynamo.create_user(user_data)
    
    # Consume 1 life
    updated_user = await dynamo.update_user_lives("test-user-789", consume=1)
    
    assert updated_user["lives"] == 4
    assert updated_user["lastLifeLost"] is not None
    
    # Consume 2 more lives
    updated_user = await dynamo.update_user_lives("test-user-789", consume=2)
    assert updated_user["lives"] == 2


@pytest.mark.asyncio
async def test_lives_regeneration(dynamodb_tables):
    """Test lazy lives regeneration logic"""
    # Create user with 3 lives
    now = datetime.utcnow()
    user = {
        "userId": "test-regen",
        "lives": 3,
        "lastLifeLost": (now - timedelta(minutes=90)).isoformat(),  # 90 minutes ago = 3 lives regenerated
        "xp": 0,
        "level": 1
    }
    
    # Recalculate lives (should regenerate 3 lives: 90 / 30 = 3)
    user_updated = dynamo.recalculate_lives_lazy(user)
    
    assert user_updated["lives"] == 5  # 3 + 3 = 6, but max is 5
    assert "livesMaxedAt" in user_updated


def test_xp_calculation():
    """Test XP and leveling system"""
    # Test level calculation
    assert gamification.calculate_level(0) == 1
    assert gamification.calculate_level(99) == 1
    assert gamification.calculate_level(100) == 2
    assert gamification.calculate_level(250) == 3
    assert gamification.calculate_level(1000) == 11
    
    # Test XP for level
    assert gamification.xp_for_level(1) == 0
    assert gamification.xp_for_level(2) == 100
    assert gamification.xp_for_level(5) == 400
    
    # Test XP progress
    progress = gamification.xp_progress_in_level(250)
    assert progress["currentLevel"] == 3
    assert progress["xpInLevel"] == 50
    assert progress["xpNeededForNext"] == 50


def test_add_xp():
    """Test adding XP and level up"""
    user = {
        "userId": "test-xp",
        "xp": 90,
        "level": 1
    }
    
    # Add 20 XP (should level up from 1 to 2)
    updated_user, level_up = gamification.add_xp(user, 20)
    
    assert updated_user["xp"] == 110
    assert updated_user["level"] == 2
    assert level_up is True
    
    # Add 50 more XP (should not level up)
    updated_user, level_up = gamification.add_xp(updated_user, 50)
    assert updated_user["xp"] == 160
    assert updated_user["level"] == 2
    assert level_up is False


def test_streak_system():
    """Test streak tracking"""
    now = datetime.utcnow()
    
    # First activity
    user = {
        "userId": "test-streak",
        "streakDays": 0,
        "lastStreakDate": None
    }
    updated_user = gamification.update_streak(user, now)
    assert updated_user["streakDays"] == 1
    
    # Activity within 48 hours (maintain streak)
    user["lastStreakDate"] = (now - timedelta(hours=24)).isoformat()
    user["streakDays"] = 5
    updated_user = gamification.update_streak(user, now)
    assert updated_user["streakDays"] == 6
    
    # Activity after 72 hours (break streak)
    user["lastStreakDate"] = (now - timedelta(hours=72)).isoformat()
    user["streakDays"] = 10
    updated_user = gamification.update_streak(user, now)
    assert updated_user["streakDays"] == 1


def test_achievements():
    """Test achievement unlocking"""
    user = {
        "userId": "test-achievements",
        "achievements": [],
        "xp": 0,
        "level": 1,
        "streakDays": 0
    }
    
    # First exercise completion
    achievements = gamification.check_achievements(user, "exercise_completed", {"score": 80})
    assert len(achievements) == 1
    assert achievements[0]["code"] == "first_sign"
    assert "first_sign" in user["achievements"]
    
    # Perfect score
    achievements = gamification.check_achievements(user, "exercise_completed", {"score": 100})
    assert any(a["code"] == "perfect_score" for a in achievements)
    
    # Level up to 5
    user["level"] = 5
    achievements = gamification.check_achievements(user, "level_up")
    assert any(a["code"] == "level_5" for a in achievements)
    
    # Week streak
    user["streakDays"] = 7
    achievements = gamification.check_achievements(user, "streak_milestone")
    assert any(a["code"] == "week_warrior" for a in achievements)


@pytest.mark.asyncio
async def test_update_progress(dynamodb_tables):
    """Test saving user progress"""
    # Create user first
    user_data = {
        "userId": "test-progress",
        "email": "progress@example.com",
        "username": "progressuser"
    }
    await dynamo.create_user(user_data)
    
    # Save progress
    await dynamo.update_progress(
        user_id="test-progress",
        level_id=1,
        exercise_id=5,
        score=85,
        xp_earned=50,
        completed=True
    )
    
    # Get progress
    progress = await dynamo.get_user_progress("test-progress", 1)
    
    assert progress is not None
    assert progress["userId"] == "test-progress"
    assert "5" in progress["exercises"]
    assert progress["exercises"]["5"]["bestScore"] == 85
    assert progress["exercises"]["5"]["completed"] is True
    assert progress["totalAttempts"] == 1
    assert progress["xpEarned"] == 50


@pytest.mark.asyncio
async def test_ai_session(dynamodb_tables):
    """Test AI session creation and retrieval"""
    session_id = "test-session-123"
    
    session_data = await dynamo.create_ai_session(
        session_id=session_id,
        user_id="test-user",
        exercise_id=5,
        level_id=1,
        video_url="s3://bucket/video.mp4"
    )
    
    assert session_data["sessionId"] == session_id
    assert session_data["status"] == "pending"
    assert session_data["videoUrl"] == "s3://bucket/video.mp4"
    
    # Get session
    session = await dynamo.get_ai_session(session_id)
    assert session is not None
    assert session["sessionId"] == session_id


@pytest.mark.asyncio
async def test_full_gamification_flow(dynamodb_tables):
    """Test complete gamification flow"""
    # Create user
    user_data = {
        "userId": "test-full-flow",
        "email": "flow@example.com",
        "username": "flowuser"
    }
    user = await dynamo.create_user(user_data)
    
    # Consume a life
    await dynamo.update_user_lives("test-full-flow", consume=1)
    
    # Complete exercise and process gamification
    result = await gamification.process_exercise_completion(
        user=user,
        score=100,
        xp_earned=50
    )
    
    assert result["xpGained"] == 50
    assert result["streakUpdated"] is True
    assert result["currentStreak"] == 1
    assert len(result["achievementsUnlocked"]) >= 1  # first_sign at minimum
    
    # User should have gained XP and achievements
    # XP = 50 (exercise) + 10 (first_sign) + 25 (perfect_score) = 85
    assert user["xp"] >= 50  # At least the exercise XP
    assert user["level"] == 1
    assert user["streakDays"] == 1
    assert len(user["achievements"]) >= 1
    assert "first_sign" in user["achievements"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
