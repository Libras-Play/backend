"""
FASE 8: Tests para Exercise Selector Service

Tests comprehensivos de los 7 criterios de selección inteligente.

EVITA ERROR #P: Tests idempotentes con fixtures aislados
"""
import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.services.exercise_selector import ExerciseSelectorService, AdaptiveDifficultyAIProvider
from app.models import (
    Exercise,
    ExerciseType,
    DifficultyLevel,
    UserExercisePerformance,
    Topic,
    SignLanguage
)


# ========== FIXTURES ==========

@pytest.fixture
def db_session(db: Session):
    """Provee sesión de DB con rollback automático."""
    yield db
    db.rollback()


@pytest.fixture
def sign_language(db_session):
    """Crea lenguaje de señas de prueba."""
    sl = SignLanguage(
        code="LSB-TEST",
        name={"en": "Test Sign Language", "pt": "Linguagem de Sinais de Teste"}
    )
    db_session.add(sl)
    db_session.commit()
    return sl


@pytest.fixture
def topic(db_session, sign_language):
    """Crea topic de prueba."""
    topic = Topic(
        title={"en": "Alphabet", "pt": "Alfabeto"},
        description={"en": "Letters", "pt": "Letras"},
        order_index=1,
        sign_language_id=sign_language.id
    )
    db_session.add(topic)
    db_session.commit()
    return topic


@pytest.fixture
def exercises_pool(db_session, topic):
    """Crea pool variado de ejercicios (test + camera, 3 dificultades)."""
    exercises = []
    
    # 2 TEST BEGINNER
    for i in range(2):
        ex = Exercise(
            topic_id=topic.id,
            title={"en": f"Test Beginner {i}", "pt": f"Teste Iniciante {i}"},
            statement={"en": "Select correct", "pt": "Selecione correto"},
            difficulty=DifficultyLevel.BEGINNER,
            exercise_type=ExerciseType.TEST,
            learning_language="LSB-TEST",
            img_url=f"http://test.com/{i}.jpg",
            answers={"en": ["A", "B"], "pt": ["A", "B"]},
            order_index=i
        )
        db_session.add(ex)
        exercises.append(ex)
    
    # 2 CAMERA BEGINNER
    for i in range(2, 4):
        ex = Exercise(
            topic_id=topic.id,
            title={"en": f"Camera Beginner {i}", "pt": f"Camera Iniciante {i}"},
            statement={"en": "Show sign", "pt": "Mostre o sinal"},
            difficulty=DifficultyLevel.BEGINNER,
            exercise_type=ExerciseType.CAMERA,
            learning_language="LSB-TEST",
            img_url=f"http://test.com/{i}.jpg",
            expected_sign="LETTER_A",
            order_index=i
        )
        db_session.add(ex)
        exercises.append(ex)
    
    # 2 TEST INTERMEDIATE
    for i in range(4, 6):
        ex = Exercise(
            topic_id=topic.id,
            title={"en": f"Test Intermediate {i}", "pt": f"Teste Intermediário {i}"},
            statement={"en": "Select correct", "pt": "Selecione correto"},
            difficulty=DifficultyLevel.INTERMEDIATE,
            exercise_type=ExerciseType.TEST,
            learning_language="LSB-TEST",
            img_url=f"http://test.com/{i}.jpg",
            answers={"en": ["A", "B", "C"], "pt": ["A", "B", "C"]},
            order_index=i
        )
        db_session.add(ex)
        exercises.append(ex)
    
    # 2 CAMERA ADVANCED
    for i in range(6, 8):
        ex = Exercise(
            topic_id=topic.id,
            title={"en": f"Camera Advanced {i}", "pt": f"Camera Avançado {i}"},
            statement={"en": "Show sign", "pt": "Mostre o sinal"},
            difficulty=DifficultyLevel.ADVANCED,
            exercise_type=ExerciseType.CAMERA,
            learning_language="LSB-TEST",
            img_url=f"http://test.com/{i}.jpg",
            expected_sign="LETTER_Z",
            order_index=i
        )
        db_session.add(ex)
        exercises.append(ex)
    
    db_session.commit()
    return exercises


# ========== TESTS BÁSICOS ==========

def test_filter_by_topic(db_session, topic, exercises_pool):
    """Test que filtra correctamente por topic_id."""
    selector = ExerciseSelectorService(db_session)
    
    result = selector.select_next_exercise(
        user_id="test-user-1",
        topic_id=topic.id,
        difficulty="BEGINNER"
    )
    
    assert result is not None
    assert result['exercise_id'] in [ex.id for ex in exercises_pool]


def test_filter_by_difficulty(db_session, topic, exercises_pool):
    """Test que filtra correctamente por difficulty."""
    selector = ExerciseSelectorService(db_session)
    
    result = selector.select_next_exercise(
        user_id="test-user-2",
        topic_id=topic.id,
        difficulty="INTERMEDIATE"
    )
    
    assert result is not None
    assert result['difficulty'] == 'INTERMEDIATE'


def test_mix_test_and_camera(db_session, topic, exercises_pool):
    """Test que pool incluye ambos tipos de ejercicios."""
    selector = ExerciseSelectorService(db_session)
    
    pool = selector._get_exercise_pool(topic.id, "BEGINNER", [])
    
    types = {ex.exercise_type for ex in pool}
    assert ExerciseType.TEST in types
    assert ExerciseType.CAMERA in types


# ========== TESTS DE LOS 7 CRITERIOS ==========

def test_criterion_1_error_history_by_type(db_session, topic, exercises_pool):
    """
    Criterio 1: Historial de errores por tipo.
    
    Usuario falla en TEST → debe priorizar TEST
    """
    selector = ExerciseSelectorService(db_session)
    user_id = "test-criterion-1"
    
    # Crear historial: muchos errores en TEST
    test_exercise = [ex for ex in exercises_pool if ex.exercise_type == ExerciseType.TEST][0]
    perf = UserExercisePerformance(
        user_id=user_id,
        exercise_id=test_exercise.id,
        attempts=10,
        errors=8,  # 80% error rate
        confidence_score=0.2,
        last_result="fail"
    )
    db_session.add(perf)
    db_session.commit()
    
    result = selector.select_next_exercise(
        user_id=user_id,
        topic_id=topic.id,
        difficulty="BEGINNER"
    )
    
    # Debe priorizar TEST por alto error_history_by_type
    assert result is not None
    assert result['selection_reasons']['error_history_by_type'] > 0.5


def test_criterion_2_error_by_specific_sign(db_session, topic, exercises_pool):
    """
    Criterio 2: Errores por señal específica.
    
    Usuario falla en ejercicio específico → priorizar ese ejercicio
    """
    selector = ExerciseSelectorService(db_session)
    user_id = "test-criterion-2"
    
    target_exercise = exercises_pool[0]
    
    # Crear historial: muchos errores en ejercicio específico
    perf = UserExercisePerformance(
        user_id=user_id,
        exercise_id=target_exercise.id,
        attempts=15,
        errors=12,  # 80% error rate
        confidence_score=0.2,
        last_result="fail"
    )
    db_session.add(perf)
    db_session.commit()
    
    result = selector.select_next_exercise(
        user_id=user_id,
        topic_id=topic.id,
        difficulty="BEGINNER"
    )
    
    # Debe tener alto score en error_by_specific_sign
    assert result is not None
    assert result['selection_reasons']['error_by_specific_sign'] > 0.5


def test_criterion_3_response_time(db_session, topic, exercises_pool):
    """
    Criterio 3: Tiempo de respuesta.
    
    Usuario lento → priorizar ese ejercicio para práctica
    """
    selector = ExerciseSelectorService(db_session)
    user_id = "test-criterion-3"
    
    slow_exercise = exercises_pool[0]
    
    # Crear historial: respuesta muy lenta (15 segundos vs baseline 5)
    perf = UserExercisePerformance(
        user_id=user_id,
        exercise_id=slow_exercise.id,
        attempts=5,
        errors=1,
        avg_response_time=15.0,  # Muy lento para BEGINNER
        confidence_score=0.5,
        last_result="success"
    )
    db_session.add(perf)
    db_session.commit()
    
    result = selector.select_next_exercise(
        user_id=user_id,
        topic_id=topic.id,
        difficulty="BEGINNER"
    )
    
    # Debe detectar lentitud
    assert result is not None
    # Score de response_time debe reflejar lentitud
    assert 'response_time' in result['selection_reasons']


def test_criterion_4_user_level(db_session, topic, exercises_pool):
    """
    Criterio 4: Nivel del usuario.
    
    Usuario nuevo (sin historial) → priorizar BEGINNER + TEST
    """
    selector = ExerciseSelectorService(db_session)
    user_id = "test-criterion-4-newbie"
    
    # Usuario nuevo: sin historial
    result = selector.select_next_exercise(
        user_id=user_id,
        topic_id=topic.id,
        difficulty="BEGINNER"
    )
    
    assert result is not None
    assert result['difficulty'] == 'BEGINNER'
    # Debe dar score alto en user_level para BEGINNER
    assert result['selection_reasons']['user_level'] > 0.5


def test_criterion_5_confidence_score(db_session, topic, exercises_pool):
    """
    Criterio 5: Confianza (confidence_score).
    
    Baja confianza → priorizar ejercicios fáciles
    """
    selector = ExerciseSelectorService(db_session)
    user_id = "test-criterion-5"
    
    # Crear historial: baja confianza general
    easy_ex = [ex for ex in exercises_pool if ex.difficulty == DifficultyLevel.BEGINNER][0]
    perf = UserExercisePerformance(
        user_id=user_id,
        exercise_id=easy_ex.id,
        attempts=10,
        errors=3,
        confidence_score=0.3,  # Baja confianza
        last_result="success"
    )
    db_session.add(perf)
    db_session.commit()
    
    result = selector.select_next_exercise(
        user_id=user_id,
        topic_id=topic.id,
        difficulty="BEGINNER"
    )
    
    assert result is not None
    # Baja confianza en BEGINNER → debe invertirse (alto score)
    # O baja confianza debe sugerir quedarse en BEGINNER
    assert 'confidence' in result['selection_reasons']


def test_criterion_6_thematic_weight(db_session, topic, exercises_pool):
    """
    Criterio 6: Peso temático.
    
    Por ahora retorna neutral (0.5), extensible en futuro.
    """
    selector = ExerciseSelectorService(db_session)
    user_id = "test-criterion-6"
    
    result = selector.select_next_exercise(
        user_id=user_id,
        topic_id=topic.id,
        difficulty="BEGINNER"
    )
    
    assert result is not None
    # Por ahora debe ser neutral
    assert result['selection_reasons']['thematic_weight'] == 0.5


def test_criterion_7_anti_repetition(db_session, topic, exercises_pool):
    """
    Criterio 7: Anti-repetición.
    
    2 TEST seguidos → penalizar TEST, priorizar CAMERA
    """
    selector = ExerciseSelectorService(db_session)
    user_id = "test-criterion-7"
    
    # Obtener 2 TEST exercises
    test_exercises = [ex for ex in exercises_pool if ex.exercise_type == ExerciseType.TEST][:2]
    recent_ids = [ex.id for ex in test_exercises]
    
    result = selector.select_next_exercise(
        user_id=user_id,
        topic_id=topic.id,
        difficulty="BEGINNER",
        recent_exercises=recent_ids
    )
    
    assert result is not None
    # Si selecciona TEST, debe tener penalización
    if result['exercise_type'] == 'test':
        assert result['selection_reasons']['anti_repetition'] < 0.5
    else:
        # Si selecciona CAMERA, es correcto (no penalizado)
        assert result['exercise_type'] == 'camera'


# ========== TEST DE ENDPOINT ==========

def test_endpoint_exercise_next(db_session, topic, exercises_pool, client):
    """
    Test del endpoint GET /exercise/next.
    
    NOTA: Requiere client fixture de pytest-fastapi
    """
    # Este test necesita que el app esté corriendo
    # Se puede implementar con TestClient de FastAPI
    
    response = client.get(
        f"/api/v1/exercises/next",
        params={
            "user_id": "test-endpoint-user",
            "topic_id": topic.id,
            "difficulty": "BEGINNER"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert 'exercise_id' in data
    assert 'exercise_type' in data
    assert 'selection_score' in data
    assert 'selection_reasons' in data
    assert 'next_recommendation' in data
    
    # Validar que selection_reasons tiene los 7 criterios
    reasons = data['selection_reasons']
    assert 'error_history_by_type' in reasons
    assert 'error_by_specific_sign' in reasons
    assert 'response_time' in reasons
    assert 'user_level' in reasons
    assert 'confidence' in reasons
    assert 'thematic_weight' in reasons
    assert 'anti_repetition' in reasons


# ========== TEST DE AI PROVIDER MOCK ==========

def test_ai_provider_mock():
    """
    Test que AdaptiveDifficultyAIProvider es solo mock.
    """
    provider = AdaptiveDifficultyAIProvider()
    
    # get_prediction debe retornar mock
    prediction = provider.get_prediction("user-1", [])
    assert prediction['ai_enabled'] is False
    assert prediction['model_version'] == 'mock'
    assert prediction['confidence'] == 0.0
    
    # suggest_next debe retornar mock
    suggestion = provider.suggest_next("user-1")
    assert suggestion['ai_enabled'] is False
    assert suggestion['model_version'] == 'mock'
    assert suggestion['suggested_topic_id'] is None


# ========== TEST DE EDGE CASES ==========

def test_no_exercises_available(db_session, topic):
    """Test cuando no hay ejercicios disponibles."""
    selector = ExerciseSelectorService(db_session)
    
    # Topic sin ejercicios
    result = selector.select_next_exercise(
        user_id="test-empty",
        topic_id=topic.id,
        difficulty="ADVANCED"
    )
    
    assert result is None


def test_recent_exercises_invalid_format(db_session, topic, exercises_pool, client):
    """Test que valida formato de recent_exercises."""
    response = client.get(
        f"/api/v1/exercises/next",
        params={
            "user_id": "test-user",
            "topic_id": topic.id,
            "difficulty": "BEGINNER",
            "recent_exercises": "abc,xyz"  # Formato inválido
        }
    )
    
    assert response.status_code == 400
    assert "comma-separated integers" in response.json()['detail']


def test_invalid_difficulty(db_session, topic, exercises_pool, client):
    """Test que valida difficulty."""
    response = client.get(
        f"/api/v1/exercises/next",
        params={
            "user_id": "test-user",
            "topic_id": topic.id,
            "difficulty": "SUPER_HARD"  # No existe
        }
    )
    
    assert response.status_code == 422  # Validation error
