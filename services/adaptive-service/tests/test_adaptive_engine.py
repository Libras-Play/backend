"""
Unit tests for Adaptive Engine

FASE 6: Tests for Rule Engine (5 reglas)
"""
import pytest
from datetime import datetime, timedelta

from app.logic.adaptive_engine import AdaptiveDifficultyEngine


@pytest.fixture
def engine():
    """Create engine instance for tests"""
    return AdaptiveDifficultyEngine()


@pytest.fixture
def mock_user_stats():
    """Mock user stats"""
    return {
        'xp': 150,
        'level': 2,
        'exercisesCompleted': 25,
        'lessonsCompleted': 5
    }


# Test Rule 1: Consistency
def test_consistency_rule_all_correct(engine):
    """Rule 1: Consecutive correct answers should increase difficulty"""
    history = [
        {'correct': True, 'timeSpent': 10},
        {'correct': True, 'timeSpent': 9},
        {'correct': True, 'timeSpent': 8},
    ]
    
    adjustment = engine.adjust_difficulty_based_on_consistency(history)
    assert adjustment == 1, "3 consecutive correct should return +1"


def test_consistency_rule_all_wrong(engine):
    """Rule 1: Consecutive wrong answers should decrease difficulty"""
    history = [
        {'correct': False, 'timeSpent': 20},
        {'correct': False, 'timeSpent': 25},
        {'correct': False, 'timeSpent': 30},
    ]
    
    adjustment = engine.adjust_difficulty_based_on_consistency(history)
    assert adjustment == -1, "3 consecutive wrong should return -1"


def test_consistency_rule_mixed(engine):
    """Rule 1: Mixed results should return no adjustment"""
    history = [
        {'correct': True, 'timeSpent': 10},
        {'correct': False, 'timeSpent': 20},
        {'correct': True, 'timeSpent': 15},
    ]
    
    adjustment = engine.adjust_difficulty_based_on_consistency(history)
    assert adjustment == 0, "Mixed results should return 0"


# Test Rule 2: Error Rate
def test_error_rate_high(engine):
    """Rule 2: High error rate should decrease difficulty"""
    history = [
        {'correct': False, 'timeSpent': 10},
        {'correct': False, 'timeSpent': 10},
        {'correct': False, 'timeSpent': 10},
        {'correct': True, 'timeSpent': 10},
    ]
    
    adjustment = engine.adjust_difficulty_based_on_errors(history)
    assert adjustment == -1, "75% error rate should return -1"


def test_error_rate_low(engine):
    """Rule 2: Low error rate should increase difficulty"""
    history = [
        {'correct': True, 'timeSpent': 10},
        {'correct': True, 'timeSpent': 10},
        {'correct': True, 'timeSpent': 10},
        {'correct': True, 'timeSpent': 10},
        {'correct': False, 'timeSpent': 10},
    ]
    
    adjustment = engine.adjust_difficulty_based_on_errors(history)
    assert adjustment == 1, "20% error rate (< 25% threshold) should return +1"


# Test Rule 3: Speed
def test_speed_fast_and_accurate(engine):
    """Rule 3: Fast response + high accuracy should increase difficulty"""
    history = [
        {'correct': True, 'timeSpent': 3},
        {'correct': True, 'timeSpent': 4},
        {'correct': True, 'timeSpent': 3},
        {'correct': True, 'timeSpent': 4},
    ]
    
    adjustment = engine.adjust_difficulty_based_on_speed(history)
    assert adjustment == 1, "Fast + accurate should return +1"


def test_speed_slow(engine):
    """Rule 3: Slow response should decrease difficulty"""
    history = [
        {'correct': True, 'timeSpent': 35},
        {'correct': True, 'timeSpent': 40},
        {'correct': False, 'timeSpent': 45},
    ]
    
    adjustment = engine.adjust_difficulty_based_on_speed(history)
    assert adjustment == -1, "Slow response should return -1"


# Test Rule 4: Mastery Score
def test_mastery_score_high_performance(engine, mock_user_stats):
    """Rule 4: High performance should give high mastery score"""
    history = [
        {'correct': True, 'timeSpent': 5},
        {'correct': True, 'timeSpent': 4},
        {'correct': True, 'timeSpent': 6},
        {'correct': True, 'timeSpent': 5},
    ]
    
    mastery = engine.calculate_mastery_score(mock_user_stats, history)
    assert mastery >= 0.8, f"High performance should give mastery >= 0.8, got {mastery}"


def test_mastery_score_low_performance(engine, mock_user_stats):
    """Rule 4: Low performance should give low mastery score"""
    history = [
        {'correct': False, 'timeSpent': 40},
        {'correct': False, 'timeSpent': 45},
        {'correct': False, 'timeSpent': 50},
        {'correct': True, 'timeSpent': 30},
    ]
    
    mastery = engine.calculate_mastery_score(mock_user_stats, history)
    assert mastery <= 0.4, f"Low performance should give mastery <= 0.4, got {mastery}"


# Test Rule 5: Safety (Never jump more than ±1)
def test_safety_rule_max_increase(engine, mock_user_stats):
    """Rule 5: Even with perfect performance, max increase is +1"""
    history = [
        {'correct': True, 'timeSpent': 2},
        {'correct': True, 'timeSpent': 2},
        {'correct': True, 'timeSpent': 3},
        {'correct': True, 'timeSpent': 2},
        {'correct': True, 'timeSpent': 3},
    ]
    
    result = engine.calculate_next_difficulty(mock_user_stats, history, current_difficulty=3)
    
    assert result['nextDifficulty'] <= result['currentDifficulty'] + 1, \
        "Should never increase more than +1"


def test_safety_rule_max_decrease(engine, mock_user_stats):
    """Rule 5: Even with terrible performance, max decrease is -1"""
    history = [
        {'correct': False, 'timeSpent': 50},
        {'correct': False, 'timeSpent': 60},
        {'correct': False, 'timeSpent': 55},
        {'correct': False, 'timeSpent': 50},
    ]
    
    result = engine.calculate_next_difficulty(mock_user_stats, history, current_difficulty=3)
    
    assert result['nextDifficulty'] >= result['currentDifficulty'] - 1, \
        "Should never decrease more than -1"


# Test boundary conditions
def test_difficulty_clamp_max(engine, mock_user_stats):
    """Difficulty should never exceed MAX_DIFFICULTY (5)"""
    history = [
        {'correct': True, 'timeSpent': 2},
        {'correct': True, 'timeSpent': 2},
        {'correct': True, 'timeSpent': 2},
    ]
    
    result = engine.calculate_next_difficulty(mock_user_stats, history, current_difficulty=5)
    
    assert result['nextDifficulty'] <= 5, "Should not exceed max difficulty (5)"


def test_difficulty_clamp_min(engine, mock_user_stats):
    """Difficulty should never go below MIN_DIFFICULTY (1)"""
    history = [
        {'correct': False, 'timeSpent': 60},
        {'correct': False, 'timeSpent': 60},
        {'correct': False, 'timeSpent': 60},
    ]
    
    result = engine.calculate_next_difficulty(mock_user_stats, history, current_difficulty=1)
    
    assert result['nextDifficulty'] >= 1, "Should not go below min difficulty (1)"


# Test empty history
def test_empty_history(engine, mock_user_stats):
    """Empty history should return neutral recommendation"""
    result = engine.calculate_next_difficulty(mock_user_stats, [], current_difficulty=2)
    
    assert result['currentDifficulty'] == 2
    assert result['nextDifficulty'] == 2
    assert result['masteryScore'] == 0.5
    assert "No exercise history" in result['reason']


# Test integration
def test_full_calculation_increase(engine, mock_user_stats):
    """Test full calculation with conditions for increase"""
    history = [
        {'correct': True, 'timeSpent': 5, 'difficulty': 2},
        {'correct': True, 'timeSpent': 6, 'difficulty': 2},
        {'correct': True, 'timeSpent': 5, 'difficulty': 2},
        {'correct': True, 'timeSpent': 4, 'difficulty': 2},
    ]
    
    result = engine.calculate_next_difficulty(mock_user_stats, history, current_difficulty=2)
    
    assert result['nextDifficulty'] == 3, "Should recommend difficulty increase"
    assert result['masteryScore'] > 0.7, "Should have high mastery score"
    assert result['adjustments']['consistency'] == 1


def test_full_calculation_decrease(engine, mock_user_stats):
    """Test full calculation with conditions for decrease"""
    history = [
        {'correct': False, 'timeSpent': 35, 'difficulty': 3},
        {'correct': False, 'timeSpent': 40, 'difficulty': 3},
        {'correct': False, 'timeSpent': 38, 'difficulty': 3},
        {'correct': True, 'timeSpent': 30, 'difficulty': 3},
    ]
    
    result = engine.calculate_next_difficulty(mock_user_stats, history, current_difficulty=3)
    
    assert result['nextDifficulty'] == 2, "Should recommend difficulty decrease"
    assert result['masteryScore'] < 0.5, "Should have low mastery score"
