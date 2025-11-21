from datetime import datetime
from typing import List, Optional, Dict, Any
from botocore.exceptions import ClientError
import uuid
from app.core.db import DynamoDBClient
from app import schemas


# User CRUD Operations
async def get_user(db: DynamoDBClient, user_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene un usuario por ID"""
    try:
        response = db.users_table.get_item(Key={'user_id': user_id})
        return response.get('Item')
    except ClientError:
        return None


async def get_user_by_cognito_sub(db: DynamoDBClient, cognito_sub: str) -> Optional[Dict[str, Any]]:
    """Obtiene un usuario por Cognito Sub ID"""
    try:
        response = db.users_table.scan(
            FilterExpression='cognito_sub = :sub',
            ExpressionAttributeValues={':sub': cognito_sub}
        )
        items = response.get('Items', [])
        return items[0] if items else None
    except ClientError:
        return None


async def create_user(db: DynamoDBClient, user: schemas.UserCreate) -> Dict[str, Any]:
    """Crea un nuevo usuario"""
    now = datetime.utcnow().isoformat()
    user_id = str(uuid.uuid4())
    
    user_item = {
        'user_id': user_id,
        'cognito_sub': user.cognito_sub,
        'email': user.email,
        'username': user.username,
        'full_name': user.full_name,
        'preferred_language': user.preferred_language,
        'avatar_url': user.avatar_url,
        'is_active': True,
        'created_at': now,
        'updated_at': now,
    }
    
    db.users_table.put_item(Item=user_item)
    return user_item


async def update_user(
    db: DynamoDBClient, user_id: str, user: schemas.UserUpdate
) -> Optional[Dict[str, Any]]:
    """Actualiza un usuario existente"""
    # Verificar que existe
    existing = await get_user(db, user_id)
    if not existing:
        return None
    
    now = datetime.utcnow().isoformat()
    update_data = user.model_dump(exclude_unset=True)
    
    if not update_data:
        return existing
    
    # Construir expresión de actualización
    update_expr_parts = []
    expr_attr_values = {}
    expr_attr_names = {}
    
    for key, value in update_data.items():
        update_expr_parts.append(f"#{key} = :{key}")
        expr_attr_values[f":{key}"] = value
        expr_attr_names[f"#{key}"] = key
    
    update_expr_parts.append("#updated_at = :updated_at")
    expr_attr_values[":updated_at"] = now
    expr_attr_names["#updated_at"] = "updated_at"
    
    update_expression = "SET " + ", ".join(update_expr_parts)
    
    response = db.users_table.update_item(
        Key={'user_id': user_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expr_attr_values,
        ExpressionAttributeNames=expr_attr_names,
        ReturnValues='ALL_NEW'
    )
    
    return response.get('Attributes')


async def delete_user(db: DynamoDBClient, user_id: str) -> bool:
    """Elimina un usuario (marca como inactivo)"""
    try:
        db.users_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET is_active = :inactive, updated_at = :now',
            ExpressionAttributeValues={
                ':inactive': False,
                ':now': datetime.utcnow().isoformat()
            }
        )
        return True
    except ClientError:
        return False


# Progress CRUD Operations
async def get_progress(
    db: DynamoDBClient, user_id: str, exercise_id: str
) -> Optional[Dict[str, Any]]:
    """Obtiene el progreso de un usuario en un ejercicio específico"""
    try:
        response = db.progress_table.get_item(
            Key={'user_id': user_id, 'exercise_id': exercise_id}
        )
        return response.get('Item')
    except ClientError:
        return None


async def get_user_progress_list(
    db: DynamoDBClient, user_id: str
) -> List[Dict[str, Any]]:
    """Obtiene todo el progreso de un usuario"""
    try:
        response = db.progress_table.query(
            KeyConditionExpression='user_id = :uid',
            ExpressionAttributeValues={':uid': user_id}
        )
        return response.get('Items', [])
    except ClientError:
        return []


async def create_or_update_progress(
    db: DynamoDBClient, user_id: str, exercise_id: str, progress: schemas.ProgressUpdate
) -> Dict[str, Any]:
    """Crea o actualiza el progreso de un ejercicio"""
    now = datetime.utcnow().isoformat()
    
    # Obtener progreso existente
    existing = await get_progress(db, user_id, exercise_id)
    
    if existing:
        # Actualizar
        update_data = progress.model_dump(exclude_unset=True)
        
        update_expr_parts = []
        expr_attr_values = {':now': now}
        expr_attr_names = {'#updated_at': 'updated_at'}
        
        for key, value in update_data.items():
            update_expr_parts.append(f"#{key} = :{key}")
            expr_attr_values[f":{key}"] = value
            expr_attr_names[f"#{key}"] = key
        
        # Incrementar intentos si se proporciona
        if 'attempts' not in update_data:
            update_expr_parts.append("#attempts = #attempts + :one")
            expr_attr_values[":one"] = 1
            expr_attr_names["#attempts"] = "attempts"
        
        update_expr_parts.append("#updated_at = :now")
        update_expression = "SET " + ", ".join(update_expr_parts)
        
        response = db.progress_table.update_item(
            Key={'user_id': user_id, 'exercise_id': exercise_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expr_attr_values,
            ExpressionAttributeNames=expr_attr_names,
            ReturnValues='ALL_NEW'
        )
        return response.get('Attributes')
    else:
        # Crear nuevo
        progress_item = {
            'user_id': user_id,
            'exercise_id': exercise_id,
            'completed': progress.completed if progress.completed is not None else False,
            'score': progress.score,
            'attempts': progress.attempts if progress.attempts is not None else 1,
            'time_spent_seconds': progress.time_spent_seconds,
            'metadata': progress.metadata or {},
            'created_at': now,
            'updated_at': now,
        }
        
        db.progress_table.put_item(Item=progress_item)
        return progress_item


async def get_user_stats(db: DynamoDBClient, user_id: str) -> Dict[str, Any]:
    """Calcula estadísticas del usuario"""
    progress_list = await get_user_progress_list(db, user_id)
    
    total_completed = sum(1 for p in progress_list if p.get('completed', False))
    total_time = sum(p.get('time_spent_seconds', 0) for p in progress_list)
    
    scores = [p.get('score') for p in progress_list if p.get('score') is not None]
    avg_score = sum(scores) / len(scores) if scores else None
    
    return {
        'user_id': user_id,
        'total_exercises_completed': total_completed,
        'total_time_spent_seconds': total_time,
        'average_score': round(avg_score, 2) if avg_score else None,
        'current_streak_days': 0,  # TODO: implementar lógica de racha
        'longest_streak_days': 0,
        'achievements': [],  # TODO: implementar logros
    }


async def delete_progress(
    db: DynamoDBClient, user_id: str, exercise_id: str
) -> bool:
    """Elimina el progreso de un ejercicio"""
    try:
        db.progress_table.delete_item(
            Key={'user_id': user_id, 'exercise_id': exercise_id}
        )
        return True
    except ClientError:
        return False
