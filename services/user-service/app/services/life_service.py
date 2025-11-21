"""FASE 7: Life Service - Business Logic Layer"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class LifeService:
    """Servicio de lógica de negocio para sistema de vidas."""
    
    def __init__(self, max_lives: int = 5, regen_minutes: int = 30, lives_per_interval: int = 1):
        self.max_lives = max_lives
        self.regen_minutes = regen_minutes
        self.lives_per_interval = lives_per_interval
        self.regen_interval = timedelta(minutes=regen_minutes)
        logger.info(f"LifeService initialized: max={max_lives}, regen={regen_minutes}min")
    
    def calculate_current_lives(
        self, stored_lives: int, last_regen_at: Optional[datetime], purchased_lives: int = 0
    ) -> Dict[str, Any]:
        """Calcula estado actual de vidas con regeneración temporal."""
        now = datetime.now(timezone.utc)
        
        total_lives = stored_lives + purchased_lives
        if total_lives >= self.max_lives:
            return {
                "current_lives": self.max_lives,
                "next_life_at": None,
                "lives_maxed_at": now.isoformat(),
                "time_until_next_life_seconds": 0,
                "is_blocked": False,
                "purchased_lives": purchased_lives,
                "lives_regenerated": 0
            }
        
        if last_regen_at is None:
            last_regen_at = now
        
        elapsed = now - last_regen_at
        intervals_passed = int(elapsed / self.regen_interval)
        lives_regen = min(intervals_passed * self.lives_per_interval, self.max_lives - total_lives)
        
        current_lives = min(total_lives + lives_regen, self.max_lives)
        
        if current_lives < self.max_lives:
            next_interval = last_regen_at + (self.regen_interval * (intervals_passed + 1))
            next_life_at = next_interval.isoformat()
            remaining_lives = self.max_lives - current_lives
            remaining_intervals = (remaining_lives + self.lives_per_interval - 1) // self.lives_per_interval
            lives_maxed_at = (next_interval + (self.regen_interval * (remaining_intervals - 1))).isoformat()
            time_until_next = int((next_interval - now).total_seconds())
        else:
            next_life_at = None
            lives_maxed_at = now.isoformat()
            time_until_next = 0
        
        return {
            "current_lives": current_lives,
            "next_life_at": next_life_at,
            "lives_maxed_at": lives_maxed_at,
            "time_until_next_life_seconds": max(0, time_until_next),
            "is_blocked": current_lives <= 0,
            "purchased_lives": purchased_lives,
            "lives_regenerated": lives_regen
        }
    
    def consume_life(self, current_lives: int, reason: str, force: bool = False) -> Tuple[int, str]:
        """Consume una vida con validación."""
        if current_lives <= 0 and not force:
            logger.warning(f"Attempt to consume life with 0 lives. Reason: {reason}")
            raise ValueError("NO_LIVES_LEFT")
        
        new_lives = max(0, current_lives - 1)
        message = f"Life consumed due to: {reason}"
        if force and current_lives <= 0:
            message += " (FORCED)"
        logger.info(f"Life consumed: {current_lives} -> {new_lives}. Reason: {reason}")
        return new_lives, message
    
    def regenerate_life_forced(self, current_lives: int, amount: int = 1) -> Tuple[int, str]:
        """Regeneración forzada (admin/testing)."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        new_lives = min(current_lives + amount, self.max_lives)
        actual_regen = new_lives - current_lives
        message = f"Forced regeneration: +{actual_regen} lives"
        if actual_regen < amount:
            message += f" (capped at max {self.max_lives})"
        logger.info(f"Forced regeneration: {current_lives} -> {new_lives}")
        return new_lives, message
    
    def purchase_lives(
        self, current_lives: int, amount: int, payment_validated: bool = False
    ) -> Tuple[int, str, bool]:
        """Compra de vidas (SIMULACIÓN)."""
        if amount <= 0:
            return 0, "Invalid amount", False
        if amount > 5:
            return 0, "Max 5 lives per purchase", False
        if not payment_validated:
            logger.warning("Purchase in SIMULATION mode")
        new_purchased = amount
        message = "Lives purchased successfully (SIMULATION MODE)"
        logger.info(f"Lives purchased: {amount} (simulation={not payment_validated})")
        return new_purchased, message, True
    
    def validate_state(self, lives: int, purchased_lives: int) -> None:
        """Valida consistencia del estado."""
        if lives < 0:
            raise ValueError(f"Lives cannot be negative: {lives}")
        if purchased_lives < 0:
            raise ValueError(f"Purchased lives cannot be negative: {purchased_lives}")
        total = lives + purchased_lives
        if total > self.max_lives:
            logger.warning(f"Total lives exceeds max: {total} > {self.max_lives}")
    
    def predict_optimal_life_regeneration(self, user_history: Dict[str, Any]) -> Dict[str, Any]:
        """FUTURO: ML prediction placeholder."""
        return {"recommended_interval_minutes": self.regen_minutes, "confidence": 0.0, "ml_enabled": False}
    
    def recommend_difficulty_adjustments(self, lives_usage: Dict[str, Any]) -> Dict[str, Any]:
        """FUTURO: ML recommendation placeholder."""
        return {"recommended_difficulty_change": 0, "reason": "ml_not_enabled", "ml_enabled": False}
