"""
FASE 7: Tests para Life Service

Valida:
- Cálculo correcto de vidas
- Consumo con validaciones
- Regeneración forzada
- Compra de vidas
- Manejo de errores
- Idempotencia
"""
import pytest
from datetime import datetime, timedelta, timezone
from app.services.life_service import LifeService


@pytest.fixture
def life_service():
    """Fixture de LifeService con configuración de prueba."""
    return LifeService(max_lives=5, regen_minutes=30, lives_per_interval=1)


class TestCalculateCurrentLives:
    """Tests para cálculo de vidas actuales."""
    
    def test_calculate_lives_at_max(self, life_service):
        """Si ya está en máximo, no regenera."""
        now = datetime.now(timezone.utc)
        result = life_service.calculate_current_lives(
            stored_lives=5,
            last_regen_at=now - timedelta(hours=2),
            purchased_lives=0
        )
        
        assert result["current_lives"] == 5
        assert result["next_life_at"] is None
        assert result["is_blocked"] is False
        assert result["lives_regenerated"] == 0
    
    def test_calculate_lives_with_regeneration(self, life_service):
        """Regenera vidas según tiempo transcurrido."""
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)  # 2 intervalos de 30min
        
        result = life_service.calculate_current_lives(
            stored_lives=2,
            last_regen_at=one_hour_ago,
            purchased_lives=0
        )
        
        assert result["current_lives"] == 4  # 2 + 2 regeneradas
        assert result["lives_regenerated"] == 2
        assert result["is_blocked"] is False
    
    def test_calculate_lives_with_purchased(self, life_service):
        """Cuenta vidas compradas en total."""
        now = datetime.now(timezone.utc)
        
        result = life_service.calculate_current_lives(
            stored_lives=3,
            last_regen_at=now,
            purchased_lives=2
        )
        
        assert result["current_lives"] == 5  # 3 + 2 compradas
        assert result["purchased_lives"] == 2
    
    def test_calculate_lives_never_exceeds_max(self, life_service):
        """No excede máximo aunque haya muchas compradas."""
        now = datetime.now(timezone.utc)
        
        result = life_service.calculate_current_lives(
            stored_lives=4,
            last_regen_at=now - timedelta(hours=5),
            purchased_lives=3
        )
        
        assert result["current_lives"] == 5  # Máximo
        assert result["is_blocked"] is False
    
    def test_calculate_next_life_prediction(self, life_service):
        """Predice correctamente cuando será próxima vida."""
        now = datetime.now(timezone.utc)
        
        result = life_service.calculate_current_lives(
            stored_lives=3,
            last_regen_at=now - timedelta(minutes=10),
            purchased_lives=0
        )
        
        assert result["current_lives"] == 3
        assert result["next_life_at"] is not None
        assert result["time_until_next_life_seconds"] > 0
    
    def test_calculate_zero_lives_is_blocked(self, life_service):
        """Con 0 vidas, usuario está bloqueado."""
        now = datetime.now(timezone.utc)
        
        result = life_service.calculate_current_lives(
            stored_lives=0,
            last_regen_at=now - timedelta(minutes=5),
            purchased_lives=0
        )
        
        assert result["current_lives"] == 0
        assert result["is_blocked"] is True


class TestConsumeLive:
    """Tests para consumo de vida."""
    
    def test_consume_life_success(self, life_service):
        """Consume vida correctamente."""
        new_lives, message = life_service.consume_life(
            current_lives=3,
            reason="exercise_failed",
            force=False
        )
        
        assert new_lives == 2
        assert "exercise_failed" in message
    
    def test_consume_life_no_lives_left(self, life_service):
        """Lanza error si no hay vidas."""
        with pytest.raises(ValueError, match="NO_LIVES_LEFT"):
            life_service.consume_life(
                current_lives=0,
                reason="exercise_failed",
                force=False
            )
    
    def test_consume_life_forced(self, life_service):
        """Consume vida aunque no haya (force=True)."""
        new_lives, message = life_service.consume_life(
            current_lives=0,
            reason="admin_test",
            force=True
        )
        
        assert new_lives == 0
        assert "FORCED" in message
    
    def test_consume_never_negative(self, life_service):
        """Vidas nunca son negativas."""
        new_lives, _ = life_service.consume_life(
            current_lives=0,
            reason="test",
            force=True
        )
        
        assert new_lives == 0


class TestRegenerateLivesForced:
    """Tests para regeneración forzada."""
    
    def test_regenerate_success(self, life_service):
        """Regenera vidas correctamente."""
        new_lives, message = life_service.regenerate_life_forced(
            current_lives=2,
            amount=2
        )
        
        assert new_lives == 4
        assert "+2" in message
    
    def test_regenerate_capped_at_max(self, life_service):
        """No excede máximo en regeneración."""
        new_lives, message = life_service.regenerate_life_forced(
            current_lives=4,
            amount=3
        )
        
        assert new_lives == 5  # Máximo
        assert "capped" in message
    
    def test_regenerate_invalid_amount(self, life_service):
        """Lanza error si amount <= 0."""
        with pytest.raises(ValueError, match="positive"):
            life_service.regenerate_life_forced(
                current_lives=3,
                amount=0
            )


class TestPurchaseLives:
    """Tests para compra de vidas."""
    
    def test_purchase_success(self, life_service):
        """Compra vidas correctamente (simulación)."""
        new_purchased, message, success = life_service.purchase_lives(
            current_lives=2,
            amount=2,
            payment_validated=False
        )
        
        assert new_purchased == 2
        assert success is True
        assert "SIMULATION" in message
    
    def test_purchase_invalid_amount(self, life_service):
        """Rechaza amount <= 0."""
        new_purchased, message, success = life_service.purchase_lives(
            current_lives=3,
            amount=0,
            payment_validated=False
        )
        
        assert success is False
        assert "Invalid" in message
    
    def test_purchase_exceeds_limit(self, life_service):
        """Rechaza compras > 5 vidas."""
        new_purchased, message, success = life_service.purchase_lives(
            current_lives=2,
            amount=10,
            payment_validated=False
        )
        
        assert success is False
        assert "Max 5" in message


class TestValidateState:
    """Tests para validación de estado."""
    
    def test_validate_negative_lives(self, life_service):
        """Rechaza vidas negativas."""
        with pytest.raises(ValueError, match="cannot be negative"):
            life_service.validate_state(lives=-1, purchased_lives=0)
    
    def test_validate_negative_purchased(self, life_service):
        """Rechaza purchased_lives negativas."""
        with pytest.raises(ValueError, match="cannot be negative"):
            life_service.validate_state(lives=3, purchased_lives=-2)
    
    def test_validate_exceeds_max_warns(self, life_service, caplog):
        """Advierte si total excede máximo."""
        import logging
        with caplog.at_level(logging.WARNING):
            life_service.validate_state(lives=4, purchased_lives=3)
        
        assert "exceeds max" in caplog.text


class TestIdempotency:
    """Tests para idempotencia."""
    
    def test_calculate_idempotent(self, life_service):
        """Mismo input produce mismo output."""
        now = datetime.now(timezone.utc)
        
        result1 = life_service.calculate_current_lives(
            stored_lives=3,
            last_regen_at=now,
            purchased_lives=1
        )
        
        result2 = life_service.calculate_current_lives(
            stored_lives=3,
            last_regen_at=now,
            purchased_lives=1
        )
        
        assert result1 == result2
    
    def test_regenerate_idempotent_at_max(self, life_service):
        """Regenerar en máximo siempre da máximo."""
        result1 = life_service.regenerate_life_forced(current_lives=5, amount=1)
        result2 = life_service.regenerate_life_forced(current_lives=5, amount=1)
        
        assert result1[0] == result2[0] == 5


class TestMLPlaceholders:
    """Tests para interfaces ML (no implementadas)."""
    
    def test_predict_optimal_regeneration_placeholder(self, life_service):
        """Placeholder retorna configuración actual."""
        result = life_service.predict_optimal_life_regeneration({})
        
        assert result["recommended_interval_minutes"] == 30
        assert result["ml_enabled"] is False
    
    def test_recommend_difficulty_placeholder(self, life_service):
        """Placeholder retorna sin cambios."""
        result = life_service.recommend_difficulty_adjustments({})
        
        assert result["recommended_difficulty_change"] == 0
        assert result["ml_enabled"] is False
