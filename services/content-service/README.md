# Content Service

Microservicio para gestión de contenidos educativos de lenguaje de señas.

## Tecnologías

- Python 3.11
- FastAPI
- SQLAlchemy (async)
- PostgreSQL
- Alembic (migraciones)

## Inicio Rápido

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar DATABASE_URL
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/content_db"

# 3. Ejecutar migraciones
alembic upgrade head

# 4. Poblar base de datos
python seed_data/seed_content.py

# 5. Correr servidor
uvicorn app.main:app --reload
```

## Estructura

```
content-service/
├── app/
│   ├── core/
│   │   ├── config.py      # Configuración
│   │   └── db.py          # Conexión a base de datos
│   ├── models.py          # Modelos SQLAlchemy

```│   ├── schemas.py         # Schemas Pydantic

│   ├── crud.py            # Operaciones CRUD

## 📋 Modelos de Datos│   └── main.py            # Aplicación FastAPI

├── alembic/               # Migraciones de base de datos

- **languages**: Lenguajes de señas (ASL, LSB, LSM)├── tests/                 # Tests con pytest

- **topics**: Temas (Alphabet, Numbers, Greetings)├── Dockerfile

- **levels**: Niveles de progresión (Letters A-E, Numbers 1-5)├── requirements.txt

- **exercises**: Ejercicios (test opción múltiple o gesture reconocimiento)└── README.md

- **signs**: Diccionario de señas con videos```

- **translations**: Traducciones i18n

- **achievements**: Logros desbloqueables## Variables de Entorno



## 📡 Endpoints API```bash

DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

Documentación interactiva: http://localhost:8001/api/docsAWS_REGION=us-east-1

ENVIRONMENT=local

### Rutas principales `/api/v1/`LOG_LEVEL=INFO

COGNITO_POOL_ID=us-east-1_xxxxx

- `POST /languages` - Crear lenguajeCOGNITO_CLIENT_ID=xxxxx

- `GET /languages` - Listar lenguajesSECRETS_MANAGER_ARN=arn:aws:secretsmanager:us-east-1:xxxxx

- `GET /languages/{id}/topics` - Temas de un lenguaje```

- `GET /topics/{id}/levels` - Niveles de un tema

- `GET /levels/{id}/exercises` - Ejercicios de un nivel## Desarrollo Local

- `GET /languages/{id}/translations` - Traducciones i18n

### Con Docker Compose (recomendado)

## ✅ Validaciones de Ejercicios

```bash

### Tipo `test`:# Desde la raíz del backend

- ✅ `options` debe tener ≥2 opcionesdocker-compose up content-service

- ✅ `correct_answer` debe estar en `options````



### Tipo `gesture`:### Sin Docker

- ✅ `gesture_label` es requerido

```bash

## 🐳 Docker# Instalar dependencias

pip install -r requirements.txt

```bash

docker-compose up -d# Configurar variables de entorno

docker exec -it content_service alembic upgrade headexport DATABASE_URL="postgresql+asyncpg://postgres:postgres_local_pass@localhost:5432/content_db"

docker exec -it content_service python seed_data/seed_content.py

```# Ejecutar migraciones

alembic upgrade head

Ver más detalles en documentación completa arriba.

# Iniciar servidor
uvicorn app.main:app --reload --port 8001
```

## Migraciones con Alembic

```bash
# Crear nueva migración (autogenerate)
alembic revision --autogenerate -m "descripción de cambios"

# Aplicar migraciones
alembic upgrade head

# Revertir última migración
alembic downgrade -1

# Ver historial
alembic history

# Ver SQL de migración sin ejecutar
alembic upgrade head --sql
```

## Poblar Base de Datos

```bash
# Ejecutar script de seed
python scripts/seed_content.py
```

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

### Languages
- `POST /api/languages` - Crear idioma
- `GET /api/languages` - Listar idiomas
- `GET /api/languages/{id}` - Obtener idioma
- `PATCH /api/languages/{id}` - Actualizar idioma
- `DELETE /api/languages/{id}` - Eliminar idioma

### Topics
- `POST /api/topics` - Crear tema
- `GET /api/languages/{language_id}/topics` - Listar temas por idioma
- `GET /api/topics/{id}` - Obtener tema
- `PATCH /api/topics/{id}` - Actualizar tema
- `DELETE /api/topics/{id}` - Eliminar tema

### Exercises
- `POST /api/exercises` - Crear ejercicio
- `GET /api/topics/{topic_id}/exercises` - Listar ejercicios por tema
- `GET /api/exercises/{id}` - Obtener ejercicio con traducciones
- `GET /api/exercises?difficulty={level}` - Filtrar por dificultad
- `PATCH /api/exercises/{id}` - Actualizar ejercicio
- `DELETE /api/exercises/{id}` - Eliminar ejercicio

### Translations
- `POST /api/translations` - Crear traducción
- `GET /api/exercises/{exercise_id}/translations` - Listar traducciones

## Documentación API

Una vez iniciado el servicio:
- Swagger UI: http://localhost:8001/api/docs
- ReDoc: http://localhost:8001/api/redoc
- OpenAPI JSON: http://localhost:8001/api/openapi.json

## Build Docker

```bash
# Build imagen
docker build -t content-service:latest .

# Ejecutar contenedor
docker run -p 8001:8000 \
  -e DATABASE_URL="postgresql+asyncpg://..." \
  content-service:latest
```
