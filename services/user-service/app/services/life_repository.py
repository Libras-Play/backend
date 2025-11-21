"""FASE 7: Life Repository - Data Access Layer"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class LifeRepository:
    """Repository para operaciones de vidas en DynamoDB."""
    
    def __init__(self, dynamo_client):
        """
        Args:
            dynamo_client: Cliente DynamoDB (tabla user-data)
        """
        self.client = dynamo_client
        self.table_name = "libras-play-dev-user-data"
    
    def get_user_lives_data(self, user_id: str) -> Dict[str, Any]:
        """
        Obtiene datos de vidas del usuario desde DynamoDB.
        
        EVITA ERROR #P: Retorna valores por defecto si no existen.
        """
        try:
            response = self.client.get_item(
                TableName=self.table_name,
                Key={"user_id": {"S": user_id}}
            )
            
            if "Item" not in response:
                logger.info(f"User {user_id} not found, returning defaults")
                return self._default_lives_data()
            
            item = response["Item"]
            
            # Parse DynamoDB types
            lives = int(item.get("lives", {"N": "5"})["N"])
            purchased_lives = int(item.get("purchasedLives", {"N": "0"})["N"])
            
            # Parse timestamp
            last_regen_str = item.get("lastLifeRegenerationAt", {}).get("S")
            last_regen_at = None
            if last_regen_str:
                try:
                    last_regen_at = datetime.fromisoformat(last_regen_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Invalid timestamp for user {user_id}: {e}")
                    last_regen_at = datetime.now(timezone.utc)
            
            return {
                "lives": lives,
                "purchased_lives": purchased_lives,
                "last_regeneration_at": last_regen_at
            }
            
        except Exception as e:
            logger.error(f"Error getting lives data for user {user_id}: {e}")
            return self._default_lives_data()
    
    def update_user_lives(
        self,
        user_id: str,
        new_lives: int,
        new_purchased_lives: int,
        update_regen_timestamp: bool = True
    ) -> bool:
        """
        Actualiza vidas del usuario en DynamoDB.
        
        EVITA ERROR #P: Operación idempotente.
        EVITA ERROR #5: Timestamps validados.
        """
        try:
            now = datetime.now(timezone.utc).isoformat()
            
            update_expression = "SET lives = :lives, purchasedLives = :purchased"
            expression_values = {
                ":lives": {"N": str(new_lives)},
                ":purchased": {"N": str(new_purchased_lives)}
            }
            
            if update_regen_timestamp:
                update_expression += ", lastLifeRegenerationAt = :timestamp"
                expression_values[":timestamp"] = {"S": now}
            
            self.client.update_item(
                TableName=self.table_name,
                Key={"user_id": {"S": user_id}},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            logger.info(
                f"Updated lives for user {user_id}: lives={new_lives}, "
                f"purchased={new_purchased_lives}, timestamp_updated={update_regen_timestamp}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error updating lives for user {user_id}: {e}")
            return False
    
    def save_life_event(
        self,
        user_id: str,
        event_type: str,
        lives_before: int,
        lives_after: int,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Guarda evento de vida para analytics/ML futuro.
        
        FUTURO: Implementar tabla separada para eventos.
        Por ahora solo logea.
        """
        event_data = {
            "user_id": user_id,
            "event_type": event_type,
            "lives_before": lives_before,
            "lives_after": lives_after,
            "reason": reason,
            "metadata": metadata,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Life event: {event_data}")
        
        # FUTURO: Guardar en tabla de eventos para ML
        # self.events_client.put_item(...)
        
        return True
    
    def _default_lives_data(self) -> Dict[str, Any]:
        """Retorna datos por defecto de vidas."""
        return {
            "lives": 5,
            "purchased_lives": 0,
            "last_regeneration_at": datetime.now(timezone.utc)
        }
