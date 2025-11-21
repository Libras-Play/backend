import pytest
from httpx import AsyncClient
from moto import mock_dynamodb
import boto3
from app.main import app
from app.core.config import get_settings

settings = get_settings()


@pytest.fixture(scope="function")
def aws_credentials(monkeypatch):
    """Mock AWS Credentials"""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@pytest.fixture(scope="function")
def dynamodb_mock(aws_credentials):
    """Mock DynamoDB"""
    with mock_dynamodb():
        # Crear tablas mock
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Tabla de usuarios
        dynamodb.create_table(
            TableName='users',
            KeySchema=[{'AttributeName': 'user_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'user_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Tabla de progreso
        dynamodb.create_table(
            TableName='user_progress',
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'exercise_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'exercise_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        yield dynamodb


@pytest.fixture(scope="function")
async def client(dynamodb_mock):
    """Cliente HTTP de prueba"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test del endpoint de health check"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "User Service"


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    """Test crear un nuevo usuario"""
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "cognito_sub": "cognito-123456",
        "preferred_language": "en"
    }
    response = await client.post("/api/users", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "user_id" in data


@pytest.mark.asyncio
async def test_get_user(client: AsyncClient):
    """Test obtener un usuario"""
    # Crear usuario primero
    user_data = {
        "email": "get@example.com",
        "username": "getuser",
        "cognito_sub": "cognito-get-123"
    }
    create_response = await client.post("/api/users", json=user_data)
    user_id = create_response.json()["user_id"]
    
    # Obtener usuario
    response = await client.get(f"/api/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["email"] == "get@example.com"


@pytest.mark.asyncio
async def test_get_user_by_cognito(client: AsyncClient):
    """Test obtener usuario por Cognito Sub"""
    # Crear usuario
    user_data = {
        "email": "cognito@example.com",
        "username": "cognitouser",
        "cognito_sub": "cognito-unique-123"
    }
    await client.post("/api/users", json=user_data)
    
    # Obtener por cognito_sub
    response = await client.get("/api/users/cognito/cognito-unique-123")
    assert response.status_code == 200
    data = response.json()
    assert data["cognito_sub"] == "cognito-unique-123"


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient):
    """Test actualizar usuario"""
    # Crear usuario
    user_data = {
        "email": "update@example.com",
        "username": "updateuser",
        "cognito_sub": "cognito-update-123"
    }
    create_response = await client.post("/api/users", json=user_data)
    user_id = create_response.json()["user_id"]
    
    # Actualizar
    update_data = {
        "full_name": "Updated Name",
        "preferred_language": "es"
    }
    response = await client.patch(f"/api/users/{user_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert data["preferred_language"] == "es"


@pytest.mark.asyncio
async def test_update_progress(client: AsyncClient):
    """Test actualizar progreso"""
    # Crear usuario
    user_data = {
        "email": "progress@example.com",
        "username": "progressuser",
        "cognito_sub": "cognito-progress-123"
    }
    create_response = await client.post("/api/users", json=user_data)
    user_id = create_response.json()["user_id"]
    
    # Actualizar progreso
    progress_data = {
        "completed": True,
        "score": 95.5,
        "time_spent_seconds": 120
    }
    response = await client.put(
        f"/api/users/{user_id}/progress/exercise-1",
        json=progress_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["completed"] is True
    assert data["score"] == 95.5
    assert data["exercise_id"] == "exercise-1"


@pytest.mark.asyncio
async def test_get_user_progress_list(client: AsyncClient):
    """Test obtener lista de progreso"""
    # Crear usuario
    user_data = {
        "email": "list@example.com",
        "username": "listuser",
        "cognito_sub": "cognito-list-123"
    }
    create_response = await client.post("/api/users", json=user_data)
    user_id = create_response.json()["user_id"]
    
    # Crear progreso para dos ejercicios
    await client.put(f"/api/users/{user_id}/progress/ex-1", json={"completed": True, "score": 80})
    await client.put(f"/api/users/{user_id}/progress/ex-2", json={"completed": False, "score": 60})
    
    # Obtener lista
    response = await client.get(f"/api/users/{user_id}/progress")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_user_stats(client: AsyncClient):
    """Test obtener estadísticas"""
    # Crear usuario
    user_data = {
        "email": "stats@example.com",
        "username": "statsuser",
        "cognito_sub": "cognito-stats-123"
    }
    create_response = await client.post("/api/users", json=user_data)
    user_id = create_response.json()["user_id"]
    
    # Crear progreso
    await client.put(f"/api/users/{user_id}/progress/ex-1", json={"completed": True, "score": 85})
    await client.put(f"/api/users/{user_id}/progress/ex-2", json={"completed": True, "score": 95})
    
    # Obtener estadísticas
    response = await client.get(f"/api/users/{user_id}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_exercises_completed"] == 2
    assert data["average_score"] == 90.0


@pytest.mark.asyncio
async def test_get_nonexistent_user(client: AsyncClient):
    """Test obtener usuario que no existe"""
    response = await client.get("/api/users/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_cognito_sub(client: AsyncClient):
    """Test crear usuario con cognito_sub duplicado"""
    user_data = {
        "email": "dup@example.com",
        "username": "dupuser",
        "cognito_sub": "cognito-dup-123"
    }
    
    # Primera creación
    await client.post("/api/users", json=user_data)
    
    # Segunda creación (debe fallar)
    user_data["email"] = "dup2@example.com"
    user_data["username"] = "dupuser2"
    response = await client.post("/api/users", json=user_data)
    assert response.status_code == 400
