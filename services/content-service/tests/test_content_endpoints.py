"""
Tests for Content Service API endpoints
Estos tests usan la base de datos real con los datos del seed
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest_asyncio.fixture(scope="function")
async def client():
    """Provide an async HTTP client for testing"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestCompleteAPIFlow:
    """Test complete API flow from languages to exercises"""
    
    async def test_complete_content_hierarchy(self, client):
        """Test the complete content hierarchy: Language → Topic → Level → Exercise"""
        # 1. Get languages
        response = await client.get("/api/v1/languages")
        assert response.status_code == 200
        languages = response.json()
        assert isinstance(languages, list)
        assert len(languages) >= 3  # ASL, LSB, LSM
        language_id = languages[0]["id"]
        
        # 2. Get specific language
        response = await client.get(f"/api/v1/languages/{language_id}")
        assert response.status_code == 200
        language = response.json()
        assert language["id"] == language_id
        assert "code" in language
        
        # 3. Test language not found
        response = await client.get("/api/v1/languages/99999")
        assert response.status_code == 404
        
        # 4. Get topics for language
        response = await client.get(f"/api/v1/languages/{language_id}/topics")
        assert response.status_code == 200
        topics = response.json()
        assert isinstance(topics, list)
        assert len(topics) > 0
        topic_id = topics[0]["id"]
        
        # 5. Get levels for topic
        response = await client.get(f"/api/v1/topics/{topic_id}/levels")
        assert response.status_code == 200
        levels = response.json()
        assert isinstance(levels, list)
        assert len(levels) > 0
        level_id = levels[0]["id"]
        
        # 6. Get exercises for level
        response = await client.get(f"/api/v1/levels/{level_id}/exercises")
        assert response.status_code == 200
        exercises = response.json()
        assert isinstance(exercises, list)
        assert len(exercises) > 0
        
        # 7. Verify exercise validations
        test_exercises = [e for e in exercises if e["type"] == "test"]
        for ex in test_exercises:
            assert ex["options"] is not None, "Test exercises must have options"
            assert len(ex["options"]) >= 2, "Test exercises must have at least 2 options"
            assert ex["correct_answer"] in ex["options"], "correct_answer must be in options"
        
        gesture_exercises = [e for e in exercises if e["type"] == "gesture"]
        for ex in gesture_exercises:
            assert ex["gesture_label"] is not None, "Gesture exercises must have gesture_label"
        
        # 8. Get translations
        response = await client.get(f"/api/v1/languages/{language_id}/translations")
        assert response.status_code == 200
        translations = response.json()
        assert isinstance(translations, list)


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Test health check endpoint"""
    
    async def test_health_check(self, client):
        """Test the health check endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert data["service"] == "Content Service"
