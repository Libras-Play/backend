# ML Service

Microservicio para procesamiento de Machine Learning y reconocimiento de lenguaje de señas.

## Tecnologías



### Caracteristicas Principales- Python 3.11

- FastAPI

- POST /api/v1/assess - Endpoint de evaluacion de video  - PyTorch

- SageMaker Integration - Flag USE_SAGEMAKER para prod/dev  - MediaPipe (detección de manos)

- SQS Consumer Worker - Procesamiento asincrono de videos  - OpenCV

- Local Stub Inference - Simulacion deterministica para desarrollo  - AWS SageMaker (opcional)

- DynamoDB Integration - Compartido con user-service (tabla AiSessions)  - S3 (almacenamiento de modelos)

- Mocking completo - Tests con moto para SageMaker/SQS/DynamoDB  

- Dockerfile dual - Variantes CPU/GPU  ## Estructura



---```

ml-service/

## Arquitectura├── app/

│   ├── core/

```│   │   ├── config.py      # Configuración

Client (Flutter) --POST /assess--> ML Service FastAPI│   │   └── db.py          # Cliente AWS (S3, SageMaker)

                 <--sessionId+status--│   ├── models.py          # (helpers para modelos ML)

                                 |│   ├── schemas.py         # Schemas Pydantic

                                 +-> SQS (video queue)│   ├── crud.py            # Lógica de ML e inferencia

                                 +-> DynamoDB (AiSessions)│   └── main.py            # Aplicación FastAPI

                                 +-> S3 (videos, models)├── tests/                 # Tests con pytest

├── Dockerfile

SQS Consumer Worker <--poll SQS-- SQS Queue├── requirements.txt

       |└── README.md

       +-> Download video from S3```

       +-> Run inference (SageMaker or Local)

       +-> Save results to DynamoDB## Variables de Entorno



Inference Routing:```bash

  USE_SAGEMAKER=true  --> SageMaker Endpoint (production)AWS_REGION=us-east-1

  USE_SAGEMAKER=false --> Local Stub (development)AWS_ENDPOINT_URL=http://localstack:4566  # Solo para local

```AWS_ACCESS_KEY_ID=test                   # Solo para local

AWS_SECRET_ACCESS_KEY=test               # Solo para local

---S3_BUCKET=ml-models-bucket

SAGEMAKER_ENDPOINT=                      # Opcional

## EstructuraMODEL_PATH=/models

DEFAULT_MODEL_NAME=sign_language_classifier.pth

```ENVIRONMENT=local

ml-service/LOG_LEVEL=INFO

├── app/```

│   ├── config.py              # Settings con USE_SAGEMAKER flag

│   ├── models.py              # Pydantic schemas## Desarrollo Local

│   ├── aws_client.py          # SageMaker, S3, SQS, DynamoDB

│   ├── main.py                # FastAPI app### Con Docker Compose (recomendado)

│   ├── inference/

│   │   ├── sagemaker_client.py    # SageMaker runtime```bash

│   │   └── local_stub.py          # Stub deterministico# Desde la raíz del backend

│   └── handlers/docker-compose up ml-service localstack

│       └── sqs_consumer.py        # Background worker```

├── tests/

│   └── test_ml_service.py     # 13 tests con moto### Sin Docker

├── .env.example

├── requirements.txt```bash

├── Dockerfile# Instalar dependencias

└── README.mdpip install -r requirements.txt

```

# Configurar variables de entorno

---export MODEL_PATH="./models"



## Inicio Rapido# Iniciar servidor

uvicorn app.main:app --reload --port 8003

```bash```

# Instalar dependencias

pip install -r requirements.txt## Modelos de ML



# Configurar variables### Estructura del Modelo

cp .env.example .env

El servicio espera modelos PyTorch (.pth) en el directorio especificado por `MODEL_PATH`.

# Iniciar servicio

uvicorn app.main:app --reload --port 8003### Descargar Modelo desde S3

```

```bash

API: http://localhost:8003  aws s3 cp s3://ml-models-bucket/sign_language_classifier.pth ./models/

Docs: http://localhost:8003/api/docs```



---### Entrenar Modelo (Futuro)



## API Endpoints```python

# TODO: Implementar pipeline de entrenamiento

### POST /api/v1/assess# - Dataset de señas con labels

# - Arquitectura CNN o Transformer

Submit video for assessment:# - Fine-tuning desde modelo pre-entrenado

```

```json

{## Tests

  "userId": "user123",

  "exerciseId": 1,```bash

  "levelId": 1,# Ejecutar todos los tests

  "s3VideoUrl": "s3://bucket/video.mp4"pytest

}

```# Con cobertura

pytest --cov=app tests/

Returns: `{"sessionId": "...", "status": "queued"}`

# Tests específicos

### GET /api/v1/assess/{sessionId}pytest tests/test_basic.py -v

```

Check status:

## API Endpoints

```json

{### Health Check

  "sessionId": "...",- `GET /health` - Estado del servicio y modelo

  "status": "completed",

  "recognizedGesture": "A",### Predictions

  "confidence": 0.95,- `POST /api/predict` - Predicción desde base64 o URL

  "score": 100  - Soporta imágenes y videos (video en desarrollo)

}  - Parámetro `top_k` para las N mejores predicciones

```  

- `POST /api/predict/upload` - Predicción desde archivo subido

### GET /health  - Soporta: jpg, png, mp4, avi, mov, webm



Health check:### Hand Detection

- `POST /api/detect-hands` - Detecta manos en imagen base64

```json- `POST /api/detect-hands/upload` - Detecta manos desde archivo

{

  "status": "healthy",### Model Info

  "modelLoaded": true,- `GET /api/model/info` - Información del modelo cargado

  "useSagemaker": false,

  "modelVersion": "1.0.0"### SageMaker (Opcional)

}- `POST /api/sagemaker/invoke` - Invoca endpoint de SageMaker

```

## Documentación API

### GET /api/v1/model/info

Una vez iniciado el servicio:

Model information:- Swagger UI: http://localhost:8003/api/docs

- ReDoc: http://localhost:8003/api/redoc

```json- OpenAPI JSON: http://localhost:8003/api/openapi.json

{

  "modelVersion": "1.0.0",## Ejemplo de Uso

  "framework": "TensorFlow Lite",

  "supportedGestures": ["A", "B", "C", ..., "Z"],### Predicción desde imagen

  "gestureCount": 26

}```python

```import requests

import base64

---

# Leer imagen

## Testswith open("sign_image.jpg", "rb") as f:

    img_base64 = base64.b64encode(f.read()).decode('utf-8')

```bash

pytest                      # All tests# Hacer predicción

pytest --cov=app tests/     # With coverageresponse = requests.post(

pytest tests/test_ml_service.py::test_assess_video_queues_message -v    "http://localhost:8003/api/predict",

```    json={

        "type": "image",

### Tests Implementados (13 total)        "data": img_base64,

        "language_code": "ASL",

1. test_health_check - Verifica endpoint de salud        "top_k": 5

2. test_root_endpoint - Verifica endpoint raiz    }

3. test_assess_video_queues_message - POST /assess encola mensaje)

4. test_get_assessment_status_completed - GET /assess/{id} con resultado

5. test_get_assessment_status_not_found - GET /assess/{id} 404result = response.json()

6. test_local_stub_inference - Stub inference funcionalprint(f"Predictions: {result['predictions']}")

7. test_local_stub_deterministic - Resultados deterministicos```

8. test_sagemaker_client_mock - SageMaker mocking con moto

9. test_sqs_consumer_processes_message - Consumer procesa mensaje### Detección de manos

10. test_sqs_consumer_handles_error - Consumer maneja errores

11. test_get_model_info - Endpoint model info```python

12. test_get_consumer_status - Endpoint consumer statusresponse = requests.post(

13. test_full_assessment_flow - Flujo completo end-to-end    "http://localhost:8003/api/detect-hands",

    json=img_base64

**Mocking con moto:**)

- SageMaker Runtime: invoke_endpoint()

- SQS: send_message(), receive_message(), delete_message()hands = response.json()

- S3: get_object() para descargar videosprint(f"Hands detected: {hands['hands_detected']}")

- DynamoDB: update_item(), get_item() para AiSessions```



---## MediaPipe Hand Landmarks



## Inference ModesEl servicio usa MediaPipe para detectar 21 landmarks por mano:

- Muñeca

### Local Stub (Development)- Nudillos y puntas de dedos

- Articulaciones intermedias

```bash

USE_SAGEMAKER=falseCada landmark tiene coordenadas (x, y, z).

```

## SageMaker Integration

- Simulacion deterministica (hash MD5 del video)

- Sin modelo real requerido### Crear Endpoint en SageMaker

- Latencia simulada (50-200ms)

- Gestos y confianza generados aleatoriamente```bash

- Ideal para desarrollo y testing# 1. Entrenar modelo en SageMaker

# 2. Desplegar endpoint

### SageMaker (Production)# 3. Configurar variable de entorno

export SAGEMAKER_ENDPOINT=sign-language-endpoint-2024

```bash```

USE_SAGEMAKER=true

SAGEMAKER_ENDPOINT_NAME=sign-language-endpoint-2024### Invocar Endpoint

```

```python

- Invoca endpoint SageMaker realresponse = requests.post(

- Requiere modelo desplegado    "http://localhost:8003/api/sagemaker/invoke",

- Escalado automatico    json=img_base64

- Metricas y logging en CloudWatch)

```

### TFLite (Optional Local Model)

## Build Docker

Para usar modelo TFLite real localmente:

```bash

1. Descomentar en requirements.txt:# Build imagen

```docker build -t ml-service:latest .

tensorflow==2.15.0

opencv-python-headless==4.8.1.78# Ejecutar contenedor

numpy==1.26.2docker run -p 8003:8000 \

```  -v $(pwd)/models:/models \

  -e MODEL_PATH="/models" \

2. Descargar modelo:  ml-service:latest

```bash```

aws s3 cp s3://ml-models-bucket/sign_language_v1.tflite ./models/

```## Roadmap



3. Extender TFLiteInference en local_stub.py- [ ] Implementar predicción de video

- [ ] Soporte para más lenguajes de señas (LSB, LSM, etc.)

---- [ ] Fine-tuning de modelos

- [ ] Integración con SageMaker training jobs

## Docker- [ ] Batch predictions

- [ ] Real-time streaming predictions

```bash- [ ] Model versioning

# Build CPU
docker build -t ml-service:latest .

# Build GPU
docker build --target gpu -t ml-service:gpu .

# Run
docker run -d -p 8003:8000 --env-file .env ml-service:latest
```

---

## Score Calculation

El score (0-100) se calcula basado en la confianza del modelo:

| Confidence | Score |
|------------|-------|
| >= 0.9     | 100   |
| >= 0.8     | 90    |
| >= 0.7     | 80    |
| >= 0.6     | 70    |
| >= 0.5     | 60    |
| < 0.5      | 0     |

---

## SQS Consumer Workflow

El worker en background:

1. Poll SQS (long polling, 20s wait time)
2. Parse message -> SQSVideoMessage
3. Update DynamoDB -> status='processing'
4. Download video from S3
5. Validate size (max 50MB)
6. Run inference (SageMaker o local stub)
7. Calculate score from confidence
8. Save results to DynamoDB
9. Delete message from SQS

**Error Handling:**
- Excepcion -> status='failed' en DynamoDB
- Mensaje no se elimina -> retry automatico (visibility timeout)
- Timeout configurado en VIDEO_PROCESSING_TIMEOUT_SECONDS

---

## Integracion con user-service

Comparte tabla DynamoDB AiSessions:

**Esquema:**
```python
{
  'sessionId': str,          # PK
  'userId': str,
  'exerciseId': int,
  'levelId': int,
  'status': str,             # queued, processing, completed, failed
  'result': {
    'recognizedGesture': str,
    'confidence': float,
    'score': int,
    'processingTime': float,
    'modelVersion': str,
    'metadata': dict
  },
  'createdAt': str,
  'updatedAt': str
}
```

**Flujo completo:**
1. Client POST /api/v1/assess -> ml-service
2. ml-service crea session en AiSessions (status='queued')
3. ml-service encola mensaje en SQS
4. Consumer procesa -> actualiza AiSessions (status='completed')
5. Client GET /api/v1/assess/{sessionId} -> lee de AiSessions

---

## Variables de Entorno

Ver `.env.example` para lista completa. Principales:

```bash
# AWS
AWS_REGION=us-east-1
AWS_ENDPOINT_URL=http://localhost:4566  # LocalStack

# SageMaker
USE_SAGEMAKER=false
SAGEMAKER_ENDPOINT_NAME=sign-language-endpoint-2024

# S3
S3_BUCKET_MODELS=ml-models-bucket
S3_BUCKET_VIDEOS=user-videos-bucket

# SQS
SQS_QUEUE_URL=http://localhost:4566/000000000000/video-processing-queue

# DynamoDB
DYNAMODB_TABLE_AI_SESSIONS=AiSessions

# ML
GESTURE_LABELS=A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z
MAX_VIDEO_SIZE_MB=50
```

---

## Checklist de Verificacion

- [x] POST /api/v1/assess implementado
- [x] GET /api/v1/assess/{sessionId} implementado
- [x] Flag USE_SAGEMAKER funcional
- [x] SageMaker client con boto3
- [x] Local stub deterministico
- [x] SQS consumer worker background
- [x] Integracion DynamoDB AiSessions
- [x] Tests con moto (13/13)
- [x] Dockerfile CPU/GPU
- [x] Documentacion completa
- [x] .env.example configurado
- [x] Requirements.txt con extras opcionales

---

## Proximos Pasos

1. Entrenar modelo real (TensorFlow/PyTorch)
2. Desplegar en SageMaker
3. Configurar CI/CD
4. Agregar metricas (Prometheus/CloudWatch)
5. Implementar batch inference
6. Agregar real-time streaming con WebSockets

---

**FASE 4 COMPLETADA**

ml-service listo para produccion local y SageMaker integration.
