"""
Tests for refactored Exercise and Topic structure (without Level entity)
Tests validate:
- Topics auto-generate 3 fixed levels (easy, medium, hard)
- Exercises have topic_id + difficulty (no level_id)
- Exercise structure: title, exercise_type, answers/expected_sign
- Language validations
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
class TestTopicStructure:
    """Test that Topics have auto-generated levels (no separate Level entity)"""
    
    async def test_topic_has_embedded_levels(self, client):
        """Test that Topic includes 'levels' array with 3 fixed levels"""
        # Get all sign languages
        response = await client.get("/api/v1/sign-languages")
        assert response.status_code == 200
        sign_languages = response.json()
        assert len(sign_languages) > 0
        
        # Get topics for first sign language
        sign_language_id = sign_languages[0]["id"]
        response = await client.get(f"/api/v1/sign-languages/{sign_language_id}/topics")
        assert response.status_code == 200
        topics = response.json()
        
        if len(topics) > 0:
            topic = topics[0]
            # Verify topic has 'levels' array
            assert "levels" in topic, "Topic must have 'levels' array"
            assert isinstance(topic["levels"], list), "'levels' must be an array"
            assert len(topic["levels"]) == 3, "Topic must have exactly 3 levels"
            
            # Verify levels structure
            difficulties = [level["difficulty"] for level in topic["levels"]]
            assert "easy" in difficulties, "Must have 'easy' level"
            assert "medium" in difficulties, "Must have 'medium' level"
            assert "hard" in difficulties, "Must have 'hard' level"
            
            # Verify each level has required fields
            for level in topic["levels"]:
                assert "difficulty" in level
                assert "description" in level
                assert level["difficulty"] in ["easy", "medium", "hard"]
    
    async def test_no_level_endpoints_exist(self, client):
        """Test that old /levels endpoints no longer exist"""
        # These endpoints should NOT exist anymore
        response = await client.get("/api/v1/levels")
        assert response.status_code == 404 or response.status_code == 405, \
            "Old /levels endpoint should not exist"
        
        response = await client.post("/api/v1/levels", json={"topic_id": 1, "title": "Test"})
        assert response.status_code == 404 or response.status_code == 405, \
            "Old POST /levels endpoint should not exist"


@pytest.mark.asyncio
class TestExerciseStructure:
    """Test new Exercise structure with all required fields"""
    
    async def test_create_exercise_type_test(self, client):
        """Test creating an exercise with type='test'"""
        # First, ensure we have a topic
        response = await client.get("/api/v1/sign-languages")
        assert response.status_code == 200
        sign_languages = response.json()
        if len(sign_languages) == 0:
            pytest.skip("No sign languages available")
        
        sign_language_id = sign_languages[0]["id"]
        response = await client.get(f"/api/v1/sign-languages/{sign_language_id}/topics")
        topics = response.json()
        if len(topics) == 0:
            pytest.skip("No topics available")
        
        topic_id = topics[0]["id"]
        
        # Create exercise with type='test'
        exercise_data = {
            "topic_id": topic_id,
            "title": "Test de Alfabeto A",
            "difficulty": "easy",
            "exercise_type": "test",
            "language": "pt-BR",
            "learning_language": "LSB",
            "img_url": "https://example.com/img_a.jpg",
            "description": "Identifica la letra A en lenguaje de señas",
            "statement": None,  # Null usa default del frontend
            "answers": {
                "correct": "Opción A",
                "options": ["Opción A", "Opción B", "Opción C", "Opción D"]
            },
            "video_url": "https://example.com/video_a.mp4",
            "order_index": 0
        }
        
        response = await client.post(f"/api/v1/topics/{topic_id}/exercises", json=exercise_data)
        assert response.status_code == 201, f"Failed to create exercise: {response.text}"
        
        created_exercise = response.json()
        
        # Verify all required fields
        assert created_exercise["topic_id"] == topic_id
        assert created_exercise["title"] == "Test de Alfabeto A"
        assert created_exercise["difficulty"] == "easy"
        assert created_exercise["exercise_type"] == "test"
        assert created_exercise["language"] == "pt-BR"
        assert created_exercise["learning_language"] == "LSB"
        assert created_exercise["img_url"] == "https://example.com/img_a.jpg"
        
        # Verify answers structure for type='test'
        assert "answers" in created_exercise
        assert created_exercise["answers"]["correct"] == "Opción A"
        assert len(created_exercise["answers"]["options"]) == 4
        assert created_exercise["answers"]["correct"] in created_exercise["answers"]["options"]
        
        # Verify timestamps
        assert "created_at" in created_exercise
        assert "updated_at" in created_exercise
        assert "id" in created_exercise
    
    async def test_create_exercise_type_camera(self, client):
        """Test creating an exercise with type='camera'"""
        # Get a topic
        response = await client.get("/api/v1/sign-languages")
        sign_languages = response.json()
        if len(sign_languages) == 0:
            pytest.skip("No sign languages available")
        
        sign_language_id = sign_languages[0]["id"]
        response = await client.get(f"/api/v1/sign-languages/{sign_language_id}/topics")
        topics = response.json()
        if len(topics) == 0:
            pytest.skip("No topics available")
        
        topic_id = topics[0]["id"]
        
        # Create exercise with type='camera'
        exercise_data = {
            "topic_id": topic_id,
            "title": "Practica la letra A",
            "difficulty": "medium",
            "exercise_type": "camera",
            "language": "pt-BR",
            "learning_language": "LSB",
            "img_url": "https://example.com/camera_a.jpg",
            "description": "Realiza la seña de la letra A frente a la cámara",
            "statement": "Muestra la letra A con tu mano derecha",
            "expected_sign": "letra_a",
            "video_url": "https://example.com/demo_a.mp4"
        }
        
        response = await client.post(f"/api/v1/topics/{topic_id}/exercises", json=exercise_data)
        assert response.status_code == 201, f"Failed to create exercise: {response.text}"
        
        created_exercise = response.json()
        
        # Verify required fields
        assert created_exercise["exercise_type"] == "camera"
        assert created_exercise["expected_sign"] == "letra_a"
        assert created_exercise["statement"] == "Muestra la letra A con tu mano derecha"
        
        # Verify answers is null for type='camera'
        assert created_exercise.get("answers") is None or created_exercise["answers"] is None
    
    async def test_exercise_validation_test_missing_answers(self, client):
        """Test that type='test' requires 'answers' field"""
        response = await client.get("/api/v1/sign-languages")
        sign_languages = response.json()
        if len(sign_languages) == 0:
            pytest.skip("No sign languages available")
        
        sign_language_id = sign_languages[0]["id"]
        response = await client.get(f"/api/v1/sign-languages/{sign_language_id}/topics")
        topics = response.json()
        if len(topics) == 0:
            pytest.skip("No topics available")
        
        topic_id = topics[0]["id"]
        
        # Try to create test exercise without answers
        exercise_data = {
            "topic_id": topic_id,
            "title": "Test sin respuestas",
            "difficulty": "easy",
            "exercise_type": "test",
            "language": "pt-BR",
            "learning_language": "LSB",
            "img_url": "https://example.com/test.jpg"
            # Missing 'answers' field!
        }
        
        response = await client.post(f"/api/v1/topics/{topic_id}/exercises", json=exercise_data)
        assert response.status_code == 422, "Should fail validation without 'answers'"
    
    async def test_exercise_validation_camera_missing_expected_sign(self, client):
        """Test that type='camera' requires 'expected_sign' field"""
        response = await client.get("/api/v1/sign-languages")
        sign_languages = response.json()
        if len(sign_languages) == 0:
            pytest.skip("No sign languages available")
        
        sign_language_id = sign_languages[0]["id"]
        response = await client.get(f"/api/v1/sign-languages/{sign_language_id}/topics")
        topics = response.json()
        if len(topics) == 0:
            pytest.skip("No topics available")
        
        topic_id = topics[0]["id"]
        
        # Try to create camera exercise without expected_sign
        exercise_data = {
            "topic_id": topic_id,
            "title": "Cámara sin seña esperada",
            "difficulty": "easy",
            "exercise_type": "camera",
            "language": "pt-BR",
            "learning_language": "LSB",
            "img_url": "https://example.com/camera.jpg"
            # Missing 'expected_sign' field!
        }
        
        response = await client.post(f"/api/v1/topics/{topic_id}/exercises", json=exercise_data)
        assert response.status_code == 422, "Should fail validation without 'expected_sign'"
    
    async def test_exercise_validation_invalid_language(self, client):
        """Test that invalid language codes are rejected"""
        response = await client.get("/api/v1/sign-languages")
        sign_languages = response.json()
        if len(sign_languages) == 0:
            pytest.skip("No sign languages available")
        
        sign_language_id = sign_languages[0]["id"]
        response = await client.get(f"/api/v1/sign-languages/{sign_language_id}/topics")
        topics = response.json()
        if len(topics) == 0:
            pytest.skip("No topics available")
        
        topic_id = topics[0]["id"]
        
        # Try with invalid UI language
        exercise_data = {
            "topic_id": topic_id,
            "title": "Test con idioma inválido",
            "difficulty": "easy",
            "exercise_type": "test",
            "language": "invalid-lang",  # Invalid!
            "learning_language": "LSB",
            "img_url": "https://example.com/test.jpg",
            "answers": {"correct": "A", "options": ["A", "B", "C"]}
        }
        
        response = await client.post(f"/api/v1/topics/{topic_id}/exercises", json=exercise_data)
        assert response.status_code in [400, 422], "Should reject invalid language code"
    
    async def test_exercise_validation_answers_structure(self, client):
        """Test that 'answers' has correct structure for type='test'"""
        response = await client.get("/api/v1/sign-languages")
        sign_languages = response.json()
        if len(sign_languages) == 0:
            pytest.skip("No sign languages available")
        
        sign_language_id = sign_languages[0]["id"]
        response = await client.get(f"/api/v1/sign-languages/{sign_language_id}/topics")
        topics = response.json()
        if len(topics) == 0:
            pytest.skip("No topics available")
        
        topic_id = topics[0]["id"]
        
        # Try with less than 3 options
        exercise_data = {
            "topic_id": topic_id,
            "title": "Test con pocas opciones",
            "difficulty": "easy",
            "exercise_type": "test",
            "language": "pt-BR",
            "learning_language": "LSB",
            "img_url": "https://example.com/test.jpg",
            "answers": {
                "correct": "A",
                "options": ["A", "B"]  # Only 2 options, need min 3
            }
        }
        
        response = await client.post(f"/api/v1/topics/{topic_id}/exercises", json=exercise_data)
        assert response.status_code == 422, "Should require at least 3 options"
        
        # Try with correct not in options
        exercise_data["answers"]["options"] = ["B", "C", "D"]  # 'A' not in options!
        response = await client.post(f"/api/v1/topics/{topic_id}/exercises", json=exercise_data)
        assert response.status_code == 422, "Should require correct answer in options"


@pytest.mark.asyncio
class TestExerciseFiltering:
    """Test filtering exercises by topic and difficulty"""
    
    async def test_get_exercises_by_topic_and_difficulty(self, client):
        """Test filtering exercises by topic_id and difficulty"""
        # Get a topic
        response = await client.get("/api/v1/sign-languages")
        sign_languages = response.json()
        if len(sign_languages) == 0:
            pytest.skip("No sign languages available")
        
        sign_language_id = sign_languages[0]["id"]
        response = await client.get(f"/api/v1/sign-languages/{sign_language_id}/topics")
        topics = response.json()
        if len(topics) == 0:
            pytest.skip("No topics available")
        
        topic_id = topics[0]["id"]
        
        # Get all exercises for topic
        response = await client.get(f"/api/v1/topics/{topic_id}/exercises")
        assert response.status_code == 200
        all_exercises = response.json()
        
        # Get only easy exercises
        response = await client.get(f"/api/v1/topics/{topic_id}/exercises?difficulty=easy")
        assert response.status_code == 200
        easy_exercises = response.json()
        
        # Verify all returned exercises are 'easy'
        for exercise in easy_exercises:
            assert exercise["difficulty"] == "easy"
        
        # Get only medium exercises
        response = await client.get(f"/api/v1/topics/{topic_id}/exercises?difficulty=medium")
        assert response.status_code == 200
        medium_exercises = response.json()
        
        for exercise in medium_exercises:
            assert exercise["difficulty"] == "medium"
        
        # Get only hard exercises
        response = await client.get(f"/api/v1/topics/{topic_id}/exercises?difficulty=hard")
        assert response.status_code == 200
        hard_exercises = response.json()
        
        for exercise in hard_exercises:
            assert exercise["difficulty"] == "hard"
    
    async def test_invalid_difficulty_filter(self, client):
        """Test that invalid difficulty values are rejected"""
        response = await client.get("/api/v1/sign-languages")
        sign_languages = response.json()
        if len(sign_languages) == 0:
            pytest.skip("No sign languages available")
        
        sign_language_id = sign_languages[0]["id"]
        response = await client.get(f"/api/v1/sign-languages/{sign_language_id}/topics")
        topics = response.json()
        if len(topics) == 0:
            pytest.skip("No topics available")
        
        topic_id = topics[0]["id"]
        
        # Try with invalid difficulty
        response = await client.get(f"/api/v1/topics/{topic_id}/exercises?difficulty=invalid")
        assert response.status_code == 400, "Should reject invalid difficulty value"


@pytest.mark.asyncio
class TestBackwardCompatibility:
    """Test that old structure is no longer supported"""
    
    async def test_old_level_id_not_accepted(self, client):
        """Test that exercises with 'level_id' are rejected"""
        response = await client.get("/api/v1/sign-languages")
        sign_languages = response.json()
        if len(sign_languages) == 0:
            pytest.skip("No sign languages available")
        
        sign_language_id = sign_languages[0]["id"]
        response = await client.get(f"/api/v1/sign-languages/{sign_language_id}/topics")
        topics = response.json()
        if len(topics) == 0:
            pytest.skip("No topics available")
        
        topic_id = topics[0]["id"]
        
        # Try to create exercise with old 'level_id' field
        exercise_data = {
            "level_id": 1,  # Old field!
            "type": "test",  # Old field name!
            "title": "Old structure",
            "difficulty": "easy",
            "language": "pt-BR",
            "learning_language": "LSB",
            "img_url": "https://example.com/test.jpg",
            "answers": {"correct": "A", "options": ["A", "B", "C"]}
        }
        
        response = await client.post(f"/api/v1/topics/{topic_id}/exercises", json=exercise_data)
        # Should fail because 'topic_id' is required, not 'level_id'
        assert response.status_code in [400, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
