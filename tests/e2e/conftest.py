"""
=============================================================================
Pytest Fixtures - Tests E2E
=============================================================================
Fixtures reutilizables para tests end-to-end.
=============================================================================
"""

import pytest
import asyncio
from typing import Dict, Any, Generator
from datetime import datetime, timedelta
import base64
import json
from unittest.mock import Mock, MagicMock, patch
import httpx
from fastapi.testclient import TestClient


# =============================================================================
# Fixtures de Configuración
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Event loop para tests async"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Configuración de test"""
    return {
        "API_BASE_URL": "http://testserver",
        "COGNITO_USER_POOL_ID": "test-pool-id",
        "COGNITO_CLIENT_ID": "test-client-id",
        "AWS_REGION": "us-east-1",
        "DYNAMODB_TABLE_PREFIX": "test-senas",
        "S3_BUCKET": "test-senas-content",
        "ML_SERVICE_URL": "http://ml-service:8080"
    }


# =============================================================================
# Fixtures de API Client
# =============================================================================

@pytest.fixture(scope="function")
def api_client(test_config) -> Generator[TestClient, None, None]:
    """
    Cliente API de FastAPI para tests
    
    Usage:
        def test_endpoint(api_client):
            response = api_client.get("/health")
            assert response.status_code == 200
    """
    from main import app  # Importar app principal
    
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
def authenticated_client(api_client, test_user_token) -> TestClient:
    """
    Cliente API autenticado con token de usuario
    
    Usage:
        def test_protected_endpoint(authenticated_client):
            response = authenticated_client.get("/users/me")
            assert response.status_code == 200
    """
    api_client.headers.update({
        "Authorization": f"Bearer {test_user_token}"
    })
    return api_client


# =============================================================================
# Fixtures de Usuarios
# =============================================================================

@pytest.fixture(scope="function")
def test_user_token(cognito_mock) -> str:
    """Token JWT de usuario de test"""
    return cognito_mock.create_test_token({
        "sub": "test-user-id-123",
        "email": "test@example.com",
        "email_verified": True,
        "cognito:groups": ["Users"],
        "cognito:username": "test_user"
    })


@pytest.fixture(scope="function")
def test_user_data() -> Dict[str, Any]:
    """Datos de usuario de test"""
    return {
        "user_id": "test-user-id-123",
        "email": "test@example.com",
        "username": "test_user",
        "name": "Test User",
        "lives": 5,
        "xp": 0,
        "level": 1,
        "gems": 100,
        "streak": 0,
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture(scope="function")
def user_with_lives(test_user_data, dynamodb_mock) -> Dict[str, Any]:
    """Usuario con 5 vidas completas"""
    user_data = test_user_data.copy()
    user_data["lives"] = 5
    dynamodb_mock.put_user(user_data)
    return user_data


@pytest.fixture(scope="function")
def user_with_no_lives(test_user_data, dynamodb_mock) -> Dict[str, Any]:
    """Usuario sin vidas (0)"""
    user_data = test_user_data.copy()
    user_data["lives"] = 0
    user_data["last_life_lost_at"] = (datetime.utcnow() - timedelta(minutes=20)).isoformat()
    dynamodb_mock.put_user(user_data)
    return user_data


@pytest.fixture(scope="function")
def user_with_gems(test_user_data, dynamodb_mock) -> Dict[str, Any]:
    """Usuario con gemas para comprar vidas"""
    user_data = test_user_data.copy()
    user_data["lives"] = 2
    user_data["gems"] = 100
    dynamodb_mock.put_user(user_data)
    return user_data


@pytest.fixture(scope="function")
def user_near_levelup(test_user_data, dynamodb_mock) -> Dict[str, Any]:
    """Usuario cerca de subir de nivel (95/100 XP)"""
    user_data = test_user_data.copy()
    user_data["level"] = 1
    user_data["xp"] = 95
    dynamodb_mock.put_user(user_data)
    return user_data


@pytest.fixture(scope="function")
def user_with_streak(test_user_data, dynamodb_mock) -> Dict[str, Any]:
    """Usuario con racha de 7 días"""
    user_data = test_user_data.copy()
    user_data["streak"] = 7
    user_data["last_practice_date"] = (datetime.utcnow() - timedelta(days=1)).date().isoformat()
    dynamodb_mock.put_user(user_data)
    return user_data


@pytest.fixture(scope="function")
def user_with_history(test_user_data, dynamodb_mock) -> Dict[str, Any]:
    """Usuario con historial de ejercicios"""
    user_data = test_user_data.copy()
    user_data["xp"] = 250
    user_data["level"] = 3
    
    # Agregar historial de ejercicios de la última semana
    exercises_history = []
    for i in range(7):
        date = (datetime.utcnow() - timedelta(days=i)).date()
        exercises_history.append({
            "date": date.isoformat(),
            "exercises_completed": 5 + i,
            "xp_earned": 50 + (i * 10),
            "accuracy": 0.85 + (i * 0.02)
        })
    
    user_data["exercises_history"] = exercises_history
    dynamodb_mock.put_user(user_data)
    return user_data


# =============================================================================
# Fixtures de Mocks - AWS Services
# =============================================================================

@pytest.fixture(scope="function")
def cognito_mock():
    """Mock de AWS Cognito"""
    
    class CognitoMock:
        def __init__(self):
            self.users = {}
        
        def create_test_token(self, claims: Dict[str, Any]) -> str:
            """Crea un token JWT de test"""
            import jwt
            
            payload = {
                **claims,
                "iss": f"https://cognito-idp.us-east-1.amazonaws.com/test-pool-id",
                "aud": "test-client-id",
                "token_use": "id",
                "auth_time": int(datetime.utcnow().timestamp()),
                "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
                "iat": int(datetime.utcnow().timestamp())
            }
            
            # En tests, usamos una clave secreta simple (en prod usa RS256)
            return jwt.encode(payload, "test-secret", algorithm="HS256")
        
        def register_user(self, email: str, password: str, **kwargs) -> Dict[str, Any]:
            """Simula registro de usuario"""
            user_id = f"user-{len(self.users) + 1}"
            self.users[user_id] = {
                "user_id": user_id,
                "email": email,
                "verified": False,
                **kwargs
            }
            return {"user_id": user_id, "verification_pending": True}
        
        def verify_user(self, user_id: str, code: str) -> bool:
            """Simula verificación de email"""
            if user_id in self.users and code == "123456":
                self.users[user_id]["verified"] = True
                return True
            return False
    
    mock = CognitoMock()
    
    with patch("services.shared.auth.get_jwk_client") as mock_jwk:
        mock_jwk.return_value = Mock()
        yield mock


@pytest.fixture(scope="function")
def dynamodb_mock():
    """Mock de DynamoDB"""
    
    class DynamoDBMock:
        def __init__(self):
            self.users = {}
            self.exercises = {}
            self.progress = {}
        
        def put_user(self, user_data: Dict[str, Any]):
            """Guarda usuario"""
            self.users[user_data["user_id"]] = user_data
        
        def get_user(self, user_id: str) -> Dict[str, Any]:
            """Obtiene usuario"""
            return self.users.get(user_id)
        
        def update_user(self, user_id: str, updates: Dict[str, Any]):
            """Actualiza usuario"""
            if user_id in self.users:
                self.users[user_id].update(updates)
        
        def put_progress(self, user_id: str, exercise_id: str, data: Dict[str, Any]):
            """Guarda progreso de ejercicio"""
            key = f"{user_id}#{exercise_id}"
            self.progress[key] = data
        
        def get_progress(self, user_id: str, exercise_id: str) -> Dict[str, Any]:
            """Obtiene progreso"""
            key = f"{user_id}#{exercise_id}"
            return self.progress.get(key)
    
    mock = DynamoDBMock()
    
    with patch("services.shared.dependencies.get_dynamodb_client") as mock_db:
        mock_db.return_value = mock
        yield mock


@pytest.fixture(scope="function")
def s3_mock():
    """Mock de S3"""
    
    class S3Mock:
        def __init__(self):
            self.objects = {}
        
        def upload_file(self, bucket: str, key: str, body: bytes) -> str:
            """Simula upload de archivo"""
            full_key = f"{bucket}/{key}"
            self.objects[full_key] = body
            return f"https://s3.amazonaws.com/{bucket}/{key}"
        
        def get_presigned_url(self, bucket: str, key: str, expiration: int = 3600) -> str:
            """Simula URL presignada"""
            return f"https://s3.amazonaws.com/{bucket}/{key}?signature=test"
    
    mock = S3Mock()
    
    with patch("boto3.client") as mock_boto:
        mock_boto.return_value = mock
        yield mock


@pytest.fixture(scope="function")
def google_oauth_mock():
    """Mock de Google OAuth"""
    
    class GoogleOAuthMock:
        def exchange_code(self, code: str) -> Dict[str, Any]:
            """Simula intercambio de código por token"""
            return {
                "access_token": "mock_google_access_token",
                "id_token": "mock_google_id_token",
                "email": "user@gmail.com",
                "verified_email": True,
                "name": "Test User"
            }
    
    mock = GoogleOAuthMock()
    
    with patch("services.user_service.auth.google_oauth_client") as mock_google:
        mock_google.return_value = mock
        yield mock


# =============================================================================
# Fixtures de Mocks - ML Service
# =============================================================================

@pytest.fixture(scope="function")
def ml_inference_mock():
    """Mock del servicio de ML para predicción de señas"""
    
    class MLServiceMock:
        def predict_sign(self, frames: list, target_sign: str = None) -> Dict[str, Any]:
            """Simula predicción de seña"""
            
            # Si se proporciona target_sign, simular predicción correcta
            if target_sign:
                return {
                    "prediction_id": f"pred_{datetime.utcnow().timestamp()}",
                    "predicted_sign": target_sign,
                    "confidence": 0.92,
                    "alternative_predictions": [
                        {"sign": "other_sign_1", "confidence": 0.05},
                        {"sign": "other_sign_2", "confidence": 0.03}
                    ],
                    "processing_time_ms": 245
                }
            else:
                # Predicción genérica
                return {
                    "prediction_id": f"pred_{datetime.utcnow().timestamp()}",
                    "predicted_sign": "hola",
                    "confidence": 0.88,
                    "processing_time_ms": 230
                }
        
        def predict_low_confidence(self) -> Dict[str, Any]:
            """Simula predicción con baja confianza"""
            return {
                "prediction_id": f"pred_{datetime.utcnow().timestamp()}",
                "predicted_sign": "unknown",
                "confidence": 0.45,
                "processing_time_ms": 210
            }
    
    mock = MLServiceMock()
    
    with patch("services.ml_service.client.MLInferenceClient") as mock_ml:
        mock_ml.return_value = mock
        yield mock


@pytest.fixture(scope="function")
def camera_mock():
    """Mock de cámara para captura de video"""
    
    class CameraMock:
        def capture_sign_video(self, sign: str, num_frames: int = 10) -> list:
            """Simula captura de video de una seña"""
            frames = []
            
            for i in range(num_frames):
                # Crear imagen simulada (1x1 pixel codificado en base64)
                fake_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
                encoded = base64.b64encode(fake_image).decode('utf-8')
                
                frames.append({
                    "frame_number": i,
                    "timestamp": datetime.utcnow().isoformat(),
                    "image_data": encoded
                })
            
            return frames
        
        def capture_poor_quality_video(self, num_frames: int = 10) -> list:
            """Simula captura de video de mala calidad"""
            # Mismo formato pero etiquetado como pobre calidad
            frames = self.capture_sign_video("unknown", num_frames)
            for frame in frames:
                frame["quality"] = "poor"
            return frames
    
    return CameraMock()


# =============================================================================
# Fixtures de Time Control
# =============================================================================

@pytest.fixture(scope="function")
def time_machine():
    """
    Fixture para controlar el tiempo en tests
    
    Usage:
        def test_time_based_feature(time_machine):
            time_machine.advance(hours=2)
            # El tiempo ahora es 2 horas en el futuro
    """
    
    class TimeMachine:
        def __init__(self):
            self.current_time = datetime.utcnow()
        
        def advance(self, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0):
            """Avanza el tiempo"""
            delta = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
            self.current_time += delta
        
        def set(self, dt: datetime):
            """Establece tiempo específico"""
            self.current_time = dt
        
        def now(self) -> datetime:
            """Retorna tiempo actual simulado"""
            return self.current_time
    
    machine = TimeMachine()
    
    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.utcnow.return_value = machine.current_time
        mock_datetime.now.return_value = machine.current_time
        yield machine


# =============================================================================
# Fixtures de Helpers
# =============================================================================

@pytest.fixture(scope="function")
def exercise_factory():
    """Factory para crear ejercicios de test"""
    
    def create_exercise(
        exercise_type: str = "test",
        difficulty: str = "beginner",
        **kwargs
    ) -> Dict[str, Any]:
        """Crea un ejercicio"""
        
        exercise = {
            "id": f"ex_{datetime.utcnow().timestamp()}",
            "type": exercise_type,
            "difficulty": difficulty,
            "xp_reward": 10 if exercise_type == "test" else 15,
            "created_at": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        if exercise_type == "test":
            exercise.update({
                "question": "¿Cuál es la seña para 'hola'?",
                "options": ["opción_a", "opción_b", "opción_c", "opción_d"],
                "correct_answer": "opción_a"
            })
        elif exercise_type == "camera":
            exercise.update({
                "target_sign": "hola",
                "video_demo_url": "https://s3.amazonaws.com/demos/hola.mp4",
                "instructions": "Realiza la seña para 'hola'"
            })
        
        return exercise
    
    return create_exercise


@pytest.fixture(scope="function")
def assertion_helpers():
    """Helpers para assertions comunes"""
    
    class AssertionHelpers:
        @staticmethod
        def assert_valid_user_profile(profile: Dict[str, Any]):
            """Valida estructura de perfil de usuario"""
            required_fields = [
                "user_id", "email", "username", "lives", 
                "xp", "level", "gems", "created_at"
            ]
            for field in required_fields:
                assert field in profile, f"Missing field: {field}"
            
            assert 0 <= profile["lives"] <= 5
            assert profile["xp"] >= 0
            assert profile["level"] >= 1
            assert profile["gems"] >= 0
        
        @staticmethod
        def assert_valid_exercise_result(result: Dict[str, Any]):
            """Valida resultado de ejercicio"""
            required_fields = ["correct", "xp_earned"]
            for field in required_fields:
                assert field in result, f"Missing field: {field}"
            
            assert isinstance(result["correct"], bool)
            assert result["xp_earned"] >= 0
        
        @staticmethod
        def assert_valid_jwt_token(token: str):
            """Valida estructura de JWT"""
            import jwt
            
            # Decodificar sin verificar (para tests)
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            required_claims = ["sub", "email", "exp", "iat"]
            for claim in required_claims:
                assert claim in decoded, f"Missing JWT claim: {claim}"
    
    return AssertionHelpers()


# =============================================================================
# Fixtures de Limpieza
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Limpia recursos después de cada test"""
    yield
    # Aquí se puede agregar lógica de limpieza si es necesaria
    pass


@pytest.fixture(scope="session", autouse=True)
def cleanup_after_session():
    """Limpia recursos después de toda la sesión de tests"""
    yield
    # Limpieza final
    pass
