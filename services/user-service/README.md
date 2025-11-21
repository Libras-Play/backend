# User Service

Microservicio para gestión de usuarios y progreso del aprendizaje.

## Tecnologías

- Python 3.11
- FastAPI
- DynamoDB (AWS)
- Boto3
- Cognito (autenticación)

## Estructura

```
user-service/
├── app/
│   ├── core/
│   │   ├── config.py      # Configuración
│   │   └── db.py          # Cliente DynamoDB
│   ├── models.py          # (vacío - no usa ORM)
│   ├── schemas.py         # Schemas Pydantic
│   ├── crud.py            # Operaciones con DynamoDB
│   └── main.py            # Aplicación FastAPI
├── tests/                 # Tests con pytest
├── Dockerfile
├── requirements.txt
└── README.md
```

## Variables de Entorno

```bash
AWS_REGION=us-east-1
AWS_ENDPOINT_URL=http://localstack:4566  # Solo para local
AWS_ACCESS_KEY_ID=test                   # Solo para local
AWS_SECRET_ACCESS_KEY=test               # Solo para local
DYNAMODB_USERS_TABLE=users
DYNAMODB_PROGRESS_TABLE=user_progress
ENVIRONMENT=local
LOG_LEVEL=INFO
COGNITO_POOL_ID=us-east-1_xxxxx
COGNITO_CLIENT_ID=xxxxx
```

## Desarrollo Local

### Con Docker Compose (recomendado)

```bash
# Desde la raíz del backend
docker-compose up user-service localstack
```

### Sin Docker

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
export AWS_REGION="us-east-1"
export AWS_ENDPOINT_URL="http://localhost:4566"
export AWS_ACCESS_KEY_ID="test"
export AWS_SECRET_ACCESS_KEY="test"

# Iniciar servidor
uvicorn app.main:app --reload --port 8002
```

## DynamoDB Tables

### Tabla: users
- **Partition Key**: `user_id` (String, UUID)
- **Atributos**:
  - `cognito_sub`: ID de Cognito
  - `email`: Email del usuario
  - `username`: Nombre de usuario
  - `full_name`: Nombre completo
  - `preferred_language`: Idioma preferido
  - `avatar_url`: URL del avatar
  - `is_active`: Usuario activo
  - `created_at`: Fecha de creación
  - `updated_at`: Fecha de actualización

### Tabla: user_progress
- **Partition Key**: `user_id` (String)
- **Sort Key**: `exercise_id` (String)
- **Atributos**:
  - `completed`: Ejercicio completado
  - `score`: Puntuación (0-100)
  - `attempts`: Número de intentos
  - `time_spent_seconds`: Tiempo dedicado
  - `metadata`: Datos adicionales (JSON)
  - `created_at`: Primera vez
  - `updated_at`: Última actualización

## Tests

```bash
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=app tests/

# Tests específicos
pytest tests/test_basic.py -v
```

## API Endpoints

### Health Check
- `GET /health` - Estado del servicio

### Users
- `POST /api/users` - Crear usuario
- `GET /api/users/{user_id}` - Obtener usuario por ID
- `GET /api/users/cognito/{cognito_sub}` - Obtener usuario por Cognito Sub
- `PATCH /api/users/{user_id}` - Actualizar usuario
- `DELETE /api/users/{user_id}` - Eliminar usuario (soft delete)

### Progress
- `GET /api/users/{user_id}/progress` - Listar todo el progreso
- `GET /api/users/{user_id}/progress/{exercise_id}` - Obtener progreso específico
- `PUT /api/users/{user_id}/progress/{exercise_id}` - Crear/actualizar progreso
- `DELETE /api/users/{user_id}/progress/{exercise_id}` - Eliminar progreso

### Statistics
- `GET /api/users/{user_id}/stats` - Obtener estadísticas del usuario

## Documentación API

Una vez iniciado el servicio:
- Swagger UI: http://localhost:8002/api/docs
- ReDoc: http://localhost:8002/api/redoc
- OpenAPI JSON: http://localhost:8002/api/openapi.json

## Crear Tablas en AWS

```bash
# Tabla de usuarios
aws dynamodb create-table \
  --table-name users \
  --attribute-definitions AttributeName=user_id,AttributeType=S \
  --key-schema AttributeName=user_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1

# Tabla de progreso
aws dynamodb create-table \
  --table-name user_progress \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=exercise_id,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
    AttributeName=exercise_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

## Build Docker

```bash
# Build imagen
docker build -t user-service:latest .

# Ejecutar contenedor
docker run -p 8002:8000 \
  -e AWS_REGION="us-east-1" \
  -e DYNAMODB_USERS_TABLE="users" \
  user-service:latest
```
