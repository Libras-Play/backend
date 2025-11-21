# Adaptive Service

Motor de aprendizaje adaptativo que personaliza la dificultad según el rendimiento del usuario.

## Características

- Motor de reglas determinista
- Arquitectura lista para ML
- Logging de decisiones para análisis
- Integración con bases de datos de usuario
- Sistema de ajuste de dificultad dinámico
- ✅ Tests unitarios (17 tests)
- ✅ Deployment-ready (Docker + ECS)

## Reglas del Motor Adaptativo

1. **Consistencia**: 3+ aciertos consecutivos → +1 dificultad
2. **Tasa de Errores**: Error rate >= 50% → -1 dificultad
3. **Velocidad**: Respuesta rápida + accuracy alta → +1
4. **Mastery Score**: Combinación ponderada (0-1)
5. **Seguridad**: Nunca saltar más de ±1 nivel

## Instalación Local

```bash
cd backend/services/adaptive-service

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar PostgreSQL (crear tabla)
alembic upgrade head

# Ejecutar
python -m uvicorn app.main:app --reload
```

## Tests

```bash
pytest tests/ -v
```

## Docker Build

```bash
# Usar variable de entorno para ECR repo
export ECR_REPO="019460294038.dkr.ecr.us-east-1.amazonaws.com"

docker build -t ${ECR_REPO}/libras-play-adaptive-service:latest .
docker push ${ECR_REPO}/libras-play-adaptive-service:latest
```

## API Endpoints

### POST /api/v1/next-difficulty

Calcula siguiente nivel de dificultad.

**Request:**
```json
{
  "user_id": "c4d8c4d8-4071-701c-a763-4a4d255dd815",
  "learning_language": "LSB",
  "exercise_type": "test",
  "current_difficulty": 2
}
```

**Response:**
```json
{
  "user_id": "c4d8c4d8-4071-701c-a763-4a4d255dd815",
  "currentDifficulty": 2,
  "nextDifficulty": 3,
  "masteryScore": 0.81,
  "reason": "Aciertos consecutivos + tiempo rápido",
  "modelUsed": false,
  "adjustments": {
    "consistency": 1,
    "errorRate": 1,
    "speed": 1
  },
  "timestamp": "2025-11-20T09:30:00Z"
}
```

### GET /health

Health check.

## Estructura DynamoDB (VERIFIED)

**Tabla**: `libras-play-dev-user-streaks`

- **PK**: `USER#{userId}#LL#{learning_language}`
- **SK**: 
  - `STATS` - User stats (xp, level, exercises, lessons)
  - `EXERCISE#{uuid}` - Individual exercise attempts

## Estructura PostgreSQL

**Tabla**: `adaptive_logs`

Almacena cada decisión para entrenamiento futuro de ML.

Campos: user_id, learning_language, exercise_type, current_difficulty, next_difficulty, mastery_score, time_spent, correct, error_rate, adjustments, model_used, timestamp

## Futuro ML Integration

1. Entrenar modelo con datos de `adaptive_logs`
2. Guardar modelo en `/app/models/adaptive_model.joblib`
3. Activar `ML_MODEL_ENABLED=true` en config
4. El sistema usará predicción ML con fallback a reglas

## Variables de Entorno

```bash
AWS_REGION=us-east-1
DYNAMODB_USER_STREAKS_TABLE=libras-play-dev-user-streaks
DYNAMODB_USER_DATA_TABLE=libras-play-dev-user-data
DATABASE_URL=postgresql://user:pass@host:5432/libras_play_dev
ML_MODEL_ENABLED=false
MIN_DIFFICULTY=1
MAX_DIFFICULTY=5
```

## Author

LibrasPlay Team - FASE 6
