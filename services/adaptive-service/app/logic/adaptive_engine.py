"""
Adaptive Difficulty Engine - Rule-based system with ML-ready architecture

This module implements a deterministic rule engine for adaptive difficulty
that can be extended with ML predictions in the future.

FASE 6: Sistema de Dificultad Adaptativa
Author: LibrasPlay Team
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class AdaptiveDifficultyEngine:
    """
    Rule-based adaptive difficulty engine
    
    Implements 5 core rules:
    1. Consistency Rule: consecutive correct answers → increase difficulty
    2. Error Rate Rule: high error rate → decrease difficulty
    3. Response Time Rule: fast/slow times affect difficulty
    4. Mastery Score: composite score (0-1) based on performance
    5. Safety Rule: never jump more than ±1 difficulty level
    """
    
    def __init__(self):
        self.min_difficulty = settings.MIN_DIFFICULTY
        self.max_difficulty = settings.MAX_DIFFICULTY
        self.consecutive_threshold = settings.CONSECUTIVE_CORRECT_THRESHOLD
        self.error_threshold = settings.ERROR_RATE_THRESHOLD
        self.fast_time = settings.FAST_RESPONSE_TIME
        self.slow_time = settings.SLOW_RESPONSE_TIME
    
    def calculate_next_difficulty(
        self,
        user_stats: Dict[str, Any],
        exercise_history: List[Dict[str, Any]],
        current_difficulty: int
    ) -> Dict[str, Any]:
        """
        Main entry point: calculate next difficulty level
        
        Args:
            user_stats: User statistics from DynamoDB (xp, level, etc.)
            exercise_history: Recent exercise attempts (last 10-20)
            current_difficulty: Current difficulty level
            
        Returns:
            {
                "currentDifficulty": int,
                "nextDifficulty": int,
                "reason": str,
                "masteryScore": float,
                "adjustments": {
                    "consistency": int,
                    "errorRate": int,
                    "speed": int
                }
            }
        """
        if not exercise_history:
            # No history: start at default difficulty
            return {
                "currentDifficulty": current_difficulty,
                "nextDifficulty": current_difficulty,
                "reason": "No exercise history available",
                "masteryScore": 0.5,
                "adjustments": {
                    "consistency": 0,
                    "errorRate": 0,
                    "speed": 0
                }
            }
        
        # Apply each rule
        consistency_adj = self.adjust_difficulty_based_on_consistency(exercise_history)
        error_adj = self.adjust_difficulty_based_on_errors(exercise_history)
        speed_adj = self.adjust_difficulty_based_on_speed(exercise_history)
        
        # Combine adjustments
        total_adjustment = consistency_adj + error_adj + speed_adj
        
        # Apply safety rule (Rule 5): never jump more than ±1
        if total_adjustment > 1:
            total_adjustment = 1
        elif total_adjustment < -1:
            total_adjustment = -1
        
        # Calculate next difficulty
        next_difficulty = current_difficulty + total_adjustment
        
        # Clamp to valid range
        next_difficulty = max(self.min_difficulty, min(self.max_difficulty, next_difficulty))
        
        # Calculate mastery score
        mastery = self.calculate_mastery_score(user_stats, exercise_history)
        
        # Generate reason
        reason = self._generate_reason(consistency_adj, error_adj, speed_adj)
        
        return {
            "currentDifficulty": current_difficulty,
            "nextDifficulty": next_difficulty,
            "reason": reason,
            "masteryScore": round(mastery, 2),
            "adjustments": {
                "consistency": consistency_adj,
                "errorRate": error_adj,
                "speed": speed_adj
            }
        }
    
    def calculate_mastery_score(
        self,
        user_stats: Dict[str, Any],
        exercise_history: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate mastery score (0-1) based on multiple factors
        
        Formula:
        mastery = (0.5 * accuracy) + (0.3 * speed_score) + (0.2 * consistency_score)
        
        Args:
            user_stats: User stats (xp, level, etc.)
            exercise_history: Recent exercises
            
        Returns:
            float: Mastery score between 0 and 1
        """
        if not exercise_history:
            return 0.5  # neutral score
        
        # Component 1: Accuracy (50% weight)
        correct_count = sum(1 for ex in exercise_history if ex.get('correct', False))
        accuracy = correct_count / len(exercise_history)
        
        # Component 2: Speed (30% weight)
        avg_time = self._calculate_average_time(exercise_history)
        if avg_time < self.fast_time:
            speed_score = 1.0
        elif avg_time < self.slow_time:
            # Linear interpolation between fast and slow
            speed_score = 1.0 - ((avg_time - self.fast_time) / (self.slow_time - self.fast_time))
        else:
            speed_score = 0.0
        
        # Component 3: Consistency (20% weight)
        consistency_score = self._calculate_consistency_score(exercise_history)
        
        # Weighted sum
        mastery = (0.5 * accuracy) + (0.3 * speed_score) + (0.2 * consistency_score)
        
        return max(0.0, min(1.0, mastery))
    
    def adjust_difficulty_based_on_consistency(
        self,
        exercise_history: List[Dict[str, Any]]
    ) -> int:
        """
        RULE 1: Consistency-based adjustment
        
        If user has consecutive_threshold or more correct answers in a row → +1
        If user has consecutive_threshold or more wrong answers in a row → -1
        
        Args:
            exercise_history: Recent exercises (ordered by timestamp)
            
        Returns:
            int: -1, 0, or +1
        """
        if len(exercise_history) < self.consecutive_threshold:
            return 0
        
        # Check recent consecutive streak
        recent = exercise_history[-self.consecutive_threshold:]
        
        all_correct = all(ex.get('correct', False) for ex in recent)
        all_wrong = all(not ex.get('correct', True) for ex in recent)
        
        if all_correct:
            logger.info(f"Consistency Rule: {self.consecutive_threshold} consecutive correct → +1")
            return 1
        elif all_wrong:
            logger.info(f"Consistency Rule: {self.consecutive_threshold} consecutive wrong → -1")
            return -1
        
        return 0
    
    def adjust_difficulty_based_on_errors(
        self,
        exercise_history: List[Dict[str, Any]]
    ) -> int:
        """
        RULE 2: Error rate adjustment
        
        If error_rate >= threshold → -1
        If error_rate < (threshold / 2) → +1
        
        Args:
            exercise_history: Recent exercises
            
        Returns:
            int: -1, 0, or +1
        """
        if not exercise_history:
            return 0
        
        error_count = sum(1 for ex in exercise_history if not ex.get('correct', False))
        error_rate = error_count / len(exercise_history)
        
        if error_rate >= self.error_threshold:
            logger.info(f"Error Rule: error_rate={error_rate:.2f} >= {self.error_threshold} → -1")
            return -1
        elif error_rate < (self.error_threshold / 2):
            logger.info(f"Error Rule: error_rate={error_rate:.2f} < {self.error_threshold/2} → +1")
            return 1
        
        return 0
    
    def adjust_difficulty_based_on_speed(
        self,
        exercise_history: List[Dict[str, Any]]
    ) -> int:
        """
        RULE 3: Response time adjustment
        
        If avg_time < fast_threshold AND accuracy high → +1
        If avg_time > slow_threshold → -1
        
        Args:
            exercise_history: Recent exercises with timeSpent field
            
        Returns:
            int: -1, 0, or +1
        """
        avg_time = self._calculate_average_time(exercise_history)
        
        if avg_time == 0:
            return 0  # No time data
        
        # Check accuracy for fast responses
        correct_count = sum(1 for ex in exercise_history if ex.get('correct', False))
        accuracy = correct_count / len(exercise_history)
        
        if avg_time < self.fast_time and accuracy >= 0.7:
            logger.info(f"Speed Rule: avg_time={avg_time}s < {self.fast_time}s AND accuracy={accuracy:.2f} → +1")
            return 1
        elif avg_time > self.slow_time:
            logger.info(f"Speed Rule: avg_time={avg_time}s > {self.slow_time}s → -1")
            return -1
        
        return 0
    
    # Helper methods
    
    def _calculate_average_time(self, exercise_history: List[Dict[str, Any]]) -> float:
        """Calculate average response time in seconds"""
        times = [ex.get('timeSpent', 0) for ex in exercise_history if ex.get('timeSpent', 0) > 0]
        return sum(times) / len(times) if times else 0
    
    def _calculate_consistency_score(self, exercise_history: List[Dict[str, Any]]) -> float:
        """
        Calculate consistency score based on streaks
        
        Higher score = more consistent performance (either good or bad)
        """
        if len(exercise_history) < 2:
            return 0.5
        
        # Count transitions (correct→wrong or wrong→correct)
        transitions = 0
        for i in range(1, len(exercise_history)):
            prev_correct = exercise_history[i-1].get('correct', False)
            curr_correct = exercise_history[i].get('correct', False)
            if prev_correct != curr_correct:
                transitions += 1
        
        # Fewer transitions = more consistent
        max_transitions = len(exercise_history) - 1
        consistency = 1.0 - (transitions / max_transitions)
        
        return consistency
    
    def _generate_reason(self, consistency: int, error: int, speed: int) -> str:
        """Generate human-readable reason for difficulty change"""
        reasons = []
        
        if consistency == 1:
            reasons.append("aciertos consecutivos")
        elif consistency == -1:
            reasons.append("errores consecutivos")
        
        if error == 1:
            reasons.append("baja tasa de errores")
        elif error == -1:
            reasons.append("alta tasa de errores")
        
        if speed == 1:
            reasons.append("tiempo rápido")
        elif speed == -1:
            reasons.append("tiempo lento")
        
        if not reasons:
            return "desempeño estable"
        
        return " + ".join(reasons).capitalize()


# Singleton instance
_engine_instance: Optional[AdaptiveDifficultyEngine] = None


def get_adaptive_engine() -> AdaptiveDifficultyEngine:
    """Get singleton instance of adaptive engine"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AdaptiveDifficultyEngine()
    return _engine_instance
