"""
FASE 5: Unit Tests for Badge System

Tests cover:
- Pydantic validators (multilang, conditions)
- DynamoDB helpers (PK/SK patterns)
- Badge evaluation logic
- Event listeners
"""

import pytest
from pydantic import ValidationError
from datetime import datetime
from app.schemas_badges import (
    BadgeCondition,
    BadgeMasterCreate,
    BadgeMasterBase
)
from app.logic import badge_service
from app.logic import listeners


# ============================================================================
# Test Badge Condition Validator
# ============================================================================

class TestBadgeConditionValidator:
    """Test validation of badge conditions"""
    
    def test_valid_condition(self):
        """Valid condition passes"""
        condition = BadgeCondition(
            metric='xp',
            operator='>=',
            value=100
        )
        assert condition.metric == 'xp'
        assert condition.operator == '>='
        assert condition.value == 100
    
    def test_invalid_metric(self):
        """Invalid metric raises error"""
        with pytest.raises(ValidationError) as exc_info:
            BadgeCondition(
                metric='invalid_metric',
                operator='>=',
                value=100
            )
        assert 'metric must be one of' in str(exc_info.value)
    
    def test_invalid_operator(self):
        """Invalid operator raises error"""
        with pytest.raises(ValidationError) as exc_info:
            BadgeCondition(
                metric='xp',
                operator='!=',  # Not allowed
                value=100
            )
        assert 'operator must be one of' in str(exc_info.value)
    
    def test_zero_value(self):
        """Value must be > 0"""
        with pytest.raises(ValidationError) as exc_info:
            BadgeCondition(
                metric='xp',
                operator='>=',
                value=0  # Not allowed
            )
        assert 'greater than 0' in str(exc_info.value).lower()
    
    def test_negative_value(self):
        """Negative value raises error"""
        with pytest.raises(ValidationError) as exc_info:
            BadgeCondition(
                metric='xp',
                operator='>=',
                value=-10
            )
        assert 'greater than 0' in str(exc_info.value).lower()


# ============================================================================
# Test Multilang Validator
# ============================================================================

class TestMultilangValidator:
    """Test validation of multilang fields"""
    
    def test_valid_multilang(self):
        """Valid multilang badge passes"""
        badge = BadgeMasterCreate(
            type='milestone',
            title={'es': 'Test ES', 'en': 'Test EN', 'pt': 'Test PT'},
            description={'es': 'Desc ES', 'en': 'Desc EN', 'pt': 'Desc PT'},
            icon_url='https://example.com/icon.png',
            conditions={'metric': 'xp', 'operator': '>=', 'value': 100},
            learning_language='LSB'
        )
        assert badge.title['es'] == 'Test ES'
        assert badge.title['en'] == 'Test EN'
        assert badge.title['pt'] == 'Test PT'
    
    def test_missing_spanish(self):
        """Missing 'es' key raises error"""
        with pytest.raises(ValidationError) as exc_info:
            BadgeMasterCreate(
                type='milestone',
                title={'en': 'Test EN', 'pt': 'Test PT'},  # Missing 'es'
                description={'es': 'Desc ES', 'en': 'Desc EN', 'pt': 'Desc PT'},
                icon_url='https://example.com/icon.png',
                conditions={'metric': 'xp', 'operator': '>=', 'value': 100},
                learning_language='LSB'
            )
        assert "missing: {'es'}" in str(exc_info.value)
    
    def test_missing_english(self):
        """Missing 'en' key raises error"""
        with pytest.raises(ValidationError) as exc_info:
            BadgeMasterCreate(
                type='milestone',
                title={'es': 'Test ES', 'pt': 'Test PT'},  # Missing 'en'
                description={'es': 'Desc ES', 'en': 'Desc EN', 'pt': 'Desc PT'},
                icon_url='https://example.com/icon.png',
                conditions={'metric': 'xp', 'operator': '>=', 'value': 100},
                learning_language='LSB'
            )
        assert "missing: {'en'}" in str(exc_info.value)
    
    def test_missing_portuguese(self):
        """Missing 'pt' key raises error"""
        with pytest.raises(ValidationError) as exc_info:
            BadgeMasterCreate(
                type='milestone',
                title={'es': 'Test ES', 'en': 'Test EN'},  # Missing 'pt'
                description={'es': 'Desc ES', 'en': 'Desc EN', 'pt': 'Desc PT'},
                icon_url='https://example.com/icon.png',
                conditions={'metric': 'xp', 'operator': '>=', 'value': 100},
                learning_language='LSB'
            )
        assert "missing: {'pt'}" in str(exc_info.value)
    
    def test_empty_string_value(self):
        """Empty string in multilang raises error"""
        with pytest.raises(ValidationError) as exc_info:
            BadgeMasterCreate(
                type='milestone',
                title={'es': '', 'en': 'Test EN', 'pt': 'Test PT'},  # Empty string
                description={'es': 'Desc ES', 'en': 'Desc EN', 'pt': 'Desc PT'},
                icon_url='https://example.com/icon.png',
                conditions={'metric': 'xp', 'operator': '>=', 'value': 100},
                learning_language='LSB'
            )
        assert 'non-empty string' in str(exc_info.value)


# ============================================================================
# Test Conditions Structure Validator
# ============================================================================

class TestConditionsStructureValidator:
    """Test validation of conditions structure"""
    
    def test_valid_conditions(self):
        """Valid conditions pass"""
        badge = BadgeMasterCreate(
            type='milestone',
            title={'es': 'Test', 'en': 'Test', 'pt': 'Test'},
            description={'es': 'Desc', 'en': 'Desc', 'pt': 'Desc'},
            icon_url='https://example.com/icon.png',
            conditions={'metric': 'streak_days', 'operator': '>=', 'value': 7},
            learning_language='LSB'
        )
        assert badge.conditions['metric'] == 'streak_days'
    
    def test_missing_metric(self):
        """Missing metric in conditions raises error"""
        with pytest.raises(ValidationError) as exc_info:
            BadgeMasterCreate(
                type='milestone',
                title={'es': 'Test', 'en': 'Test', 'pt': 'Test'},
                description={'es': 'Desc', 'en': 'Desc', 'pt': 'Desc'},
                icon_url='https://example.com/icon.png',
                conditions={'operator': '>=', 'value': 7},  # Missing metric
                learning_language='LSB'
            )
        assert 'metric' in str(exc_info.value).lower()
    
    def test_invalid_conditions_metric(self):
        """Invalid metric in conditions raises error"""
        with pytest.raises(ValidationError) as exc_info:
            BadgeMasterCreate(
                type='milestone',
                title={'es': 'Test', 'en': 'Test', 'pt': 'Test'},
                description={'es': 'Desc', 'en': 'Desc', 'pt': 'Desc'},
                icon_url='https://example.com/icon.png',
                conditions={'metric': 'invalid', 'operator': '>=', 'value': 7},
                learning_language='LSB'
            )
        assert 'metric must be one of' in str(exc_info.value)


# ============================================================================
# Test evaluate_condition Logic
# ============================================================================

class TestEvaluateCondition:
    """Test badge condition evaluation logic"""
    
    def test_greater_than_or_equal_true(self):
        """Test >= operator when condition met"""
        condition = {'metric': 'xp', 'operator': '>=', 'value': 100}
        user_stats = {'xp': 150}
        
        result = badge_service.evaluate_condition(condition, user_stats)
        assert result is True
    
    def test_greater_than_or_equal_false(self):
        """Test >= operator when condition not met"""
        condition = {'metric': 'xp', 'operator': '>=', 'value': 100}
        user_stats = {'xp': 50}
        
        result = badge_service.evaluate_condition(condition, user_stats)
        assert result is False
    
    def test_greater_than_true(self):
        """Test > operator"""
        condition = {'metric': 'xp', 'operator': '>', 'value': 100}
        user_stats = {'xp': 101}
        
        result = badge_service.evaluate_condition(condition, user_stats)
        assert result is True
    
    def test_equal_true(self):
        """Test == operator"""
        condition = {'metric': 'level', 'operator': '==', 'value': 5}
        user_stats = {'level': 5}
        
        result = badge_service.evaluate_condition(condition, user_stats)
        assert result is True
    
    def test_missing_stat(self):
        """Test when user stat is missing (defaults to 0)"""
        condition = {'metric': 'streak_days', 'operator': '>=', 'value': 7}
        user_stats = {}  # No streak_days
        
        result = badge_service.evaluate_condition(condition, user_stats)
        assert result is False


# ============================================================================
# Test Event Listeners
# ============================================================================

class TestEventListeners:
    """Test event listener validation and structure"""
    
    def test_lesson_completed_valid_payload(self):
        """Valid lesson completed payload passes validation"""
        event = {
            'userId': 'test-user',
            'learningLanguage': 'LSB',
            'timestamp': datetime.utcnow().isoformat(),
            'lessonId': 'lesson-001',
            'xpEarned': 10
        }
        
        # Validate base fields
        error = listeners.validate_base_event(event)
        assert error is None
    
    def test_lesson_completed_missing_user_id(self):
        """Missing userId raises validation error"""
        event = {
            'learningLanguage': 'LSB',
            'timestamp': datetime.utcnow().isoformat(),
            'lessonId': 'lesson-001'
        }
        
        error = listeners.validate_base_event(event)
        assert error == 'Missing required field: userId'
    
    def test_lesson_completed_invalid_language(self):
        """Invalid learningLanguage raises error"""
        event = {
            'userId': 'test-user',
            'learningLanguage': 'INVALID',
            'timestamp': datetime.utcnow().isoformat(),
            'lessonId': 'lesson-001'
        }
        
        error = listeners.validate_base_event(event)
        assert 'Invalid learningLanguage' in error
    
    def test_exercise_completed_valid(self):
        """Valid exercise completed event"""
        event = {
            'userId': 'test-user',
            'learningLanguage': 'LSB',
            'timestamp': datetime.utcnow().isoformat(),
            'exerciseId': 'ex-001',
            'correct': True
        }
        
        error = listeners.validate_base_event(event)
        assert error is None


# ============================================================================
# Test Type/Rarity/Language Validators
# ============================================================================

class TestEnumValidators:
    """Test enum-like field validators"""
    
    def test_invalid_type(self):
        """Invalid badge type raises error"""
        with pytest.raises(ValidationError) as exc_info:
            BadgeMasterCreate(
                type='invalid_type',
                title={'es': 'Test', 'en': 'Test', 'pt': 'Test'},
                description={'es': 'Desc', 'en': 'Desc', 'pt': 'Desc'},
                icon_url='https://example.com/icon.png',
                conditions={'metric': 'xp', 'operator': '>=', 'value': 100},
                learning_language='LSB'
            )
        assert 'type must be one of' in str(exc_info.value)
    
    def test_invalid_rarity(self):
        """Invalid rarity raises error"""
        with pytest.raises(ValidationError) as exc_info:
            BadgeMasterCreate(
                type='milestone',
                title={'es': 'Test', 'en': 'Test', 'pt': 'Test'},
                description={'es': 'Desc', 'en': 'Desc', 'pt': 'Desc'},
                icon_url='https://example.com/icon.png',
                conditions={'metric': 'xp', 'operator': '>=', 'value': 100},
                learning_language='LSB',
                rarity='invalid_rarity'
            )
        assert 'rarity must be one of' in str(exc_info.value)
    
    def test_invalid_learning_language(self):
        """Invalid learning_language raises error"""
        with pytest.raises(ValidationError) as exc_info:
            BadgeMasterCreate(
                type='milestone',
                title={'es': 'Test', 'en': 'Test', 'pt': 'Test'},
                description={'es': 'Desc', 'en': 'Desc', 'pt': 'Desc'},
                icon_url='https://example.com/icon.png',
                conditions={'metric': 'xp', 'operator': '>=', 'value': 100},
                learning_language='INVALID'
            )
        assert 'learning_language must be one of' in str(exc_info.value)
