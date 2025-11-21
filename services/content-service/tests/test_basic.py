import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.core.db import Base, get_db

# Database de prueba en memoria
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test del endpoint de health check"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_create_language(client: AsyncClient):
    """Test crear un nuevo idioma"""
    language_data = {
        "code": "ASL",
        "name": "American Sign Language",
        "description": "Sign language used in the United States"
    }
    response = await client.post("/api/languages", json=language_data)
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "ASL"
    assert data["name"] == "American Sign Language"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_languages(client: AsyncClient):
    """Test listar idiomas"""
    # Crear un idioma primero
    language_data = {
        "code": "LSB",
        "name": "Lengua de Señas Brasileña",
        "description": "Sign language used in Brazil"
    }
    await client.post("/api/languages", json=language_data)
    
    # Listar
    response = await client.get("/api/languages")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_language(client: AsyncClient):
    """Test obtener un idioma específico"""
    # Crear idioma
    language_data = {
        "code": "LSM",
        "name": "Lengua de Señas Mexicana",
    }
    create_response = await client.post("/api/languages", json=language_data)
    language_id = create_response.json()["id"]
    
    # Obtener
    response = await client.get(f"/api/languages/{language_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "LSM"


@pytest.mark.asyncio
async def test_create_topic(client: AsyncClient):
    """Test crear un tema"""
    # Primero crear idioma
    language_data = {"code": "ASL", "name": "American Sign Language"}
    lang_response = await client.post("/api/languages", json=language_data)
    language_id = lang_response.json()["id"]
    
    # Crear tema
    topic_data = {
        "language_id": language_id,
        "name": "Greetings",
        "description": "Basic greetings in sign language",
        "order": 1
    }
    response = await client.post("/api/topics", json=topic_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Greetings"
    assert data["language_id"] == language_id


@pytest.mark.asyncio
async def test_create_exercise(client: AsyncClient):
    """Test crear un ejercicio"""
    # Crear idioma
    lang_response = await client.post("/api/languages", json={"code": "ASL", "name": "ASL"})
    language_id = lang_response.json()["id"]
    
    # Crear tema
    topic_response = await client.post("/api/topics", json={
        "language_id": language_id,
        "name": "Numbers",
        "order": 1
    })
    topic_id = topic_response.json()["id"]
    
    # Crear ejercicio
    exercise_data = {
        "topic_id": topic_id,
        "title": "Number 1",
        "description": "Learn to sign number 1",
        "type": "video",
        "difficulty": "beginner",
        "order": 1
    }
    response = await client.post("/api/exercises", json=exercise_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Number 1"
    assert data["type"] == "video"
    assert data["difficulty"] == "beginner"


@pytest.mark.asyncio
async def test_get_nonexistent_language(client: AsyncClient):
    """Test obtener idioma que no existe"""
    response = await client.get("/api/languages/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_language_code(client: AsyncClient):
    """Test crear idioma con código duplicado"""
    language_data = {"code": "ASL", "name": "American Sign Language"}
    
    # Primera creación
    await client.post("/api/languages", json=language_data)
    
    # Segunda creación (debe fallar)
    response = await client.post("/api/languages", json=language_data)
    assert response.status_code == 400
