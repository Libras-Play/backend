"""
FASE 5: Integration Tests for Badge System

Tests end-to-end flow:
1. Exercise completed → Event listener → Badge evaluation → Assignment
2. Streak updated → Badge evaluation
3. Level up → Badge evaluation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from app.logic import listeners
from app.logic import badge_service


class TestBadgeIntegrationFlow:
    """Integration tests for complete badge assignment flow"""
    
    @patch('app.logic.badge_service.check_and_assign_badges')
    def test_exercise_completion_triggers_badge_check(self, mock_check_badges):
        """Exercise completed event triggers badge evaluation"""
        # Setup mock
        mock_check_badges.return_value = [
            {
                'badge_id': 'exercises-10',
                'title': {'es': '10 Ejercicios', 'en': '10 Exercises', 'pt': '10 Exercícios'},
                'earned_at': datetime.utcnow().isoformat()
            }
        ]
        
        # Trigger event
        event = {
            'userId': 'test-user',
            'learningLanguage': 'LSB',
            'timestamp': datetime.utcnow().isoformat(),
            'exerciseId': 'ex-001',
            'correct': True,
            'xpEarned': 5
        }
        
        result = listeners.on_exercise_completed(event)
        
        # Assertions
        assert result['success'] is True
        assert result['totalBadgesEarned'] == 1
        assert len(result['newBadges']) == 1
        assert result['newBadges'][0]['badge_id'] == 'exercises-10'
        
        # Verify badge check was called
        mock_check_badges.assert_called_once_with('test-user', 'LSB')
    
    @patch('app.logic.badge_service.check_and_assign_badges')
    def test_lesson_completion_triggers_badge_check(self, mock_check_badges):
        """Lesson completed event triggers badge evaluation"""
        mock_check_badges.return_value = []
        
        event = {
            'userId': 'test-user',
            'learningLanguage': 'LSB',
            'timestamp': datetime.utcnow().isoformat(),
            'lessonId': 'lesson-001',
            'xpEarned': 10,
            'perfect': True
        }
        
        result = listeners.on_lesson_completed(event)
        
        assert result['success'] is True
        assert result['totalBadgesEarned'] == 0
        mock_check_badges.assert_called_once_with('test-user', 'LSB')
    
    @patch('app.logic.badge_service.check_and_assign_badges')
    def test_streak_increase_triggers_badge_check(self, mock_check_badges):
        """Streak increase triggers badge evaluation"""
        mock_check_badges.return_value = [
            {
                'badge_id': 'streak-7',
                'title': {'es': 'Racha de 7 días', 'en': '7-Day Streak', 'pt': 'Sequência de 7 dias'}
            }
        ]
        
        event = {
            'userId': 'test-user',
            'learningLanguage': 'LSB',
            'timestamp': datetime.utcnow().isoformat(),
            'newStreak': 7,
            'previousStreak': 6,
            'streakIncreased': True
        }
        
        result = listeners.on_streak_updated(event)
        
        assert result['success'] is True
        assert result['totalBadgesEarned'] == 1
        mock_check_badges.assert_called_once_with('test-user', 'LSB')
    
    @patch('app.logic.badge_service.check_and_assign_badges')
    def test_streak_decrease_skips_badge_check(self, mock_check_badges):
        """Streak decrease skips badge evaluation (optimization)"""
        event = {
            'userId': 'test-user',
            'learningLanguage': 'LSB',
            'timestamp': datetime.utcnow().isoformat(),
            'newStreak': 5,
            'previousStreak': 6,
            'streakIncreased': False
        }
        
        result = listeners.on_streak_updated(event)
        
        assert result['success'] is True
        assert result.get('skipped') is True
        # Badge check should NOT be called
        mock_check_badges.assert_not_called()
    
    @patch('app.logic.badge_service.check_and_assign_badges')
    def test_level_up_triggers_badge_check(self, mock_check_badges):
        """Level up event triggers badge evaluation"""
        mock_check_badges.return_value = [
            {
                'badge_id': 'level-5',
                'title': {'es': 'Nivel 5', 'en': 'Level 5', 'pt': 'Nível 5'}
            }
        ]
        
        event = {
            'userId': 'test-user',
            'learningLanguage': 'LSB',
            'timestamp': datetime.utcnow().isoformat(),
            'newLevel': 5,
            'previousLevel': 4,
            'totalXP': 1500
        }
        
        result = listeners.on_level_up(event)
        
        assert result['success'] is True
        assert result['totalBadgesEarned'] == 1
        mock_check_badges.assert_called_once_with('test-user', 'LSB')
    
    def test_invalid_event_returns_error(self):
        """Invalid event returns error without calling badge check"""
        event = {
            # Missing userId
            'learningLanguage': 'LSB',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        result = listeners.on_lesson_completed(event)
        
        assert result['success'] is False
        assert 'Missing required field: userId' in result['error']
    
    @patch('app.logic.badge_service.check_and_assign_badges')
    def test_multiple_badges_earned(self, mock_check_badges):
        """Multiple badges can be earned in single event"""
        mock_check_badges.return_value = [
            {'badge_id': 'xp-100', 'title': {'es': '100 XP'}},
            {'badge_id': 'exercises-10', 'title': {'es': '10 Ejercicios'}},
            {'badge_id': 'streak-3', 'title': {'es': 'Racha de 3 días'}}
        ]
        
        event = {
            'userId': 'test-user',
            'learningLanguage': 'LSB',
            'timestamp': datetime.utcnow().isoformat(),
            'exerciseId': 'ex-001',
            'correct': True
        }
        
        result = listeners.on_exercise_completed(event)
        
        assert result['success'] is True
        assert result['totalBadgesEarned'] == 3
        assert len(result['newBadges']) == 3


class TestBadgeEvaluationLogic:
    """Integration tests for badge evaluation logic"""
    
    @patch('app.logic.badge_service.get_all_badges')
    @patch('app.dynamo_badges.get_user_badges')
    @patch('app.logic.badge_service.get_user_stats')
    @patch('app.dynamo_badges.assign_badge')
    def test_badge_assigned_when_condition_met(
        self, mock_assign, mock_stats, mock_user_badges, mock_all_badges
    ):
        """Badge is assigned when condition is met and not already earned"""
        # Setup mocks
        mock_all_badges.return_value = [
            {
                'badge_id': 'xp-100',
                'title': {'es': '100 XP'},
                'conditions': {'metric': 'xp', 'operator': '>=', 'value': 100}
            }
        ]
        mock_user_badges.return_value = []  # No badges earned yet
        mock_stats.return_value = {'xp': 150}  # Meets condition
        mock_assign.return_value = {
            'newly_earned': True,
            'earned_at': datetime.utcnow().isoformat()
        }
        
        # Call
        result = badge_service.check_and_assign_badges('test-user', 'LSB')
        
        # Assertions
        assert len(result) == 1
        assert result[0]['badge_id'] == 'xp-100'
        mock_assign.assert_called_once()
    
    @patch('app.logic.badge_service.get_all_badges')
    @patch('app.dynamo_badges.get_user_badges')
    @patch('app.logic.badge_service.get_user_stats')
    def test_badge_not_assigned_when_condition_not_met(
        self, mock_stats, mock_user_badges, mock_all_badges
    ):
        """Badge is not assigned when condition is not met"""
        mock_all_badges.return_value = [
            {
                'badge_id': 'xp-100',
                'conditions': {'metric': 'xp', 'operator': '>=', 'value': 100}
            }
        ]
        mock_user_badges.return_value = []
        mock_stats.return_value = {'xp': 50}  # Does not meet condition
        
        result = badge_service.check_and_assign_badges('test-user', 'LSB')
        
        assert len(result) == 0
    
    @patch('app.logic.badge_service.get_all_badges')
    @patch('app.dynamo_badges.get_user_badges')
    @patch('app.logic.badge_service.get_user_stats')
    def test_badge_not_assigned_if_already_earned(
        self, mock_stats, mock_user_badges, mock_all_badges
    ):
        """Badge is not assigned if user already has it"""
        mock_all_badges.return_value = [
            {
                'badge_id': 'xp-100',
                'conditions': {'metric': 'xp', 'operator': '>=', 'value': 100}
            }
        ]
        mock_user_badges.return_value = [
            {'badge_id': 'xp-100'}  # Already earned
        ]
        mock_stats.return_value = {'xp': 150}
        
        result = badge_service.check_and_assign_badges('test-user', 'LSB')
        
        assert len(result) == 0


class TestErrorHandling:
    """Test error handling in listeners"""
    
    @patch('app.logic.badge_service.check_and_assign_badges')
    def test_listener_handles_badge_check_exception(self, mock_check_badges):
        """Listener catches and returns error when badge check fails"""
        mock_check_badges.side_effect = Exception("Database error")
        
        event = {
            'userId': 'test-user',
            'learningLanguage': 'LSB',
            'timestamp': datetime.utcnow().isoformat(),
            'exerciseId': 'ex-001'
        }
        
        result = listeners.on_exercise_completed(event)
        
        assert result['success'] is False
        assert 'Database error' in result['error']
    
    def test_missing_lesson_id_returns_error(self):
        """Missing lessonId in lesson event returns error"""
        event = {
            'userId': 'test-user',
            'learningLanguage': 'LSB',
            'timestamp': datetime.utcnow().isoformat()
            # Missing lessonId
        }
        
        result = listeners.on_lesson_completed(event)
        
        assert result['success'] is False
        assert 'Missing lessonId' in result['error']
