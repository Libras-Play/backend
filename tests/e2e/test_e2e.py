"""
=============================================================================
Tests End-to-End (E2E) - Aplicación de Señas
=============================================================================
Tests completos de flujos de usuario desde la creación hasta levelUp.

Flujos cubiertos:
1. Creación de usuario con Cognito
2. Consumo de vidas (lives system)
3. Completar ejercicio de test
4. Completar ejercicio con cámara (simulado)
5. Subida de XP y levelUp
=============================================================================
"""

import pytest
import time
from datetime import datetime, timedelta
from typing import Dict, Any
import json


class TestUserCreationFlow:
    """Tests de flujo de creación de usuario"""
    
    def test_user_registration_complete_flow(self, api_client, cognito_mock):
        """
        Test E2E: Registro completo de usuario
        
        Flujo:
        1. Registrar usuario en Cognito
        2. Verificar email
        3. Crear perfil en base de datos
        4. Validar datos iniciales (vidas, XP, nivel)
        """
        # Paso 1: Registro en Cognito
        registration_data = {
            "email": "nuevo.usuario@example.com",
            "password": "SecurePass123!",
            "username": "nuevo_usuario",
            "name": "Nuevo Usuario"
        }
        
        response = api_client.post("/auth/register", json=registration_data)
        assert response.status_code == 201
        
        data = response.json()
        assert "user_id" in data
        assert data["email"] == registration_data["email"]
        assert "verification_pending" in data
        
        user_id = data["user_id"]
        
        # Paso 2: Verificar email (mock)
        verification_response = api_client.post(
            f"/auth/verify",
            json={
                "user_id": user_id,
                "code": "123456"  # Mock code
            }
        )
        assert verification_response.status_code == 200
        
        # Paso 3: Login y obtener token
        login_response = api_client.post(
            "/auth/login",
            json={
                "email": registration_data["email"],
                "password": registration_data["password"]
            }
        )
        assert login_response.status_code == 200
        
        token_data = login_response.json()
        assert "access_token" in token_data
        assert "id_token" in token_data
        
        # Paso 4: Obtener perfil de usuario
        headers = {"Authorization": f"Bearer {token_data['id_token']}"}
        profile_response = api_client.get("/users/me", headers=headers)
        
        assert profile_response.status_code == 200
        profile = profile_response.json()
        
        # Validar datos iniciales
        assert profile["user_id"] == user_id
        assert profile["email"] == registration_data["email"]
        assert profile["lives"] == 5  # Vidas iniciales
        assert profile["xp"] == 0
        assert profile["level"] == 1
        assert profile["streak"] == 0
        assert "created_at" in profile
    
    def test_user_with_google_oauth(self, api_client, google_oauth_mock):
        """Test E2E: Registro/Login con Google OAuth"""
        
        # Simular callback de Google OAuth
        oauth_data = {
            "provider": "google",
            "code": "mock_google_auth_code",
            "redirect_uri": "http://localhost:3000/auth/callback"
        }
        
        response = api_client.post("/auth/oauth/google", json=oauth_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        
        user = data["user"]
        assert user["email"].endswith("@gmail.com")
        assert user["oauth_provider"] == "google"
        
        # Validar que se creó el perfil automáticamente
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        profile_response = api_client.get("/users/me", headers=headers)
        
        assert profile_response.status_code == 200
        profile = profile_response.json()
        assert profile["lives"] == 5
        assert profile["level"] == 1


class TestLivesSystemFlow:
    """Tests de flujo del sistema de vidas"""
    
    def test_consume_life_on_wrong_answer(self, authenticated_client, user_with_lives):
        """
        Test E2E: Consumo de vida al fallar ejercicio
        
        Flujo:
        1. Usuario con 5 vidas completa ejercicio incorrectamente
        2. Se consume 1 vida
        3. Vidas restantes = 4
        4. Timestamp de última vida perdida se actualiza
        """
        # Estado inicial
        profile = authenticated_client.get("/users/me").json()
        initial_lives = profile["lives"]
        assert initial_lives == 5
        
        # Completar ejercicio incorrectamente
        exercise_data = {
            "exercise_id": "ex_001",
            "answer": "respuesta_incorrecta",
            "time_spent": 30
        }
        
        response = authenticated_client.post("/exercises/submit", json=exercise_data)
        assert response.status_code == 200
        
        result = response.json()
        assert result["correct"] is False
        assert result["life_lost"] is True
        assert result["lives_remaining"] == 4
        
        # Verificar actualización de perfil
        profile = authenticated_client.get("/users/me").json()
        assert profile["lives"] == 4
        assert "last_life_lost_at" in profile
    
    def test_lives_regeneration(self, authenticated_client, user_with_no_lives, time_machine):
        """
        Test E2E: Regeneración de vidas cada 30 minutos
        
        Flujo:
        1. Usuario con 0 vidas
        2. Esperar 30 minutos (simulado)
        3. Regenerar 1 vida
        4. Verificar vida disponible
        """
        # Estado inicial: 0 vidas
        profile = authenticated_client.get("/users/me").json()
        assert profile["lives"] == 0
        
        # Avanzar tiempo 30 minutos
        time_machine.advance(minutes=30)
        
        # Trigger regeneración (puede ser automático o manual)
        response = authenticated_client.post("/users/regenerate-lives")
        assert response.status_code == 200
        
        result = response.json()
        assert result["lives"] == 1
        assert result["regenerated"] == 1
        
        # Avanzar 2 horas más (4 vidas adicionales)
        time_machine.advance(hours=2)
        
        response = authenticated_client.post("/users/regenerate-lives")
        assert response.status_code == 200
        
        result = response.json()
        assert result["lives"] == 5  # Máximo
        assert result["regenerated"] == 4
    
    def test_cannot_do_exercise_without_lives(self, authenticated_client, user_with_no_lives):
        """Test E2E: Bloqueo de ejercicios sin vidas"""
        
        profile = authenticated_client.get("/users/me").json()
        assert profile["lives"] == 0
        
        # Intentar hacer ejercicio sin vidas
        exercise_data = {
            "exercise_id": "ex_001",
            "answer": "respuesta_correcta",
            "time_spent": 30
        }
        
        response = authenticated_client.post("/exercises/submit", json=exercise_data)
        assert response.status_code == 403
        
        error = response.json()
        assert "no lives remaining" in error["detail"].lower()
        assert "next_life_in" in error
    
    def test_restore_all_lives_with_gems(self, authenticated_client, user_with_gems):
        """Test E2E: Restaurar vidas con gemas premium"""
        
        # Usuario con 2 vidas y 100 gemas
        profile = authenticated_client.get("/users/me").json()
        assert profile["lives"] == 2
        assert profile["gems"] >= 100
        
        # Comprar restauración completa (50 gemas)
        response = authenticated_client.post("/shop/restore-lives")
        assert response.status_code == 200
        
        result = response.json()
        assert result["lives"] == 5
        assert result["gems_spent"] == 50
        
        # Verificar actualización
        profile = authenticated_client.get("/users/me").json()
        assert profile["lives"] == 5
        assert profile["gems"] == 50  # 100 - 50


class TestExerciseCompletionFlow:
    """Tests de flujo de completar ejercicios"""
    
    def test_complete_test_exercise_correct(self, authenticated_client):
        """
        Test E2E: Completar ejercicio de test correctamente
        
        Flujo:
        1. Obtener ejercicio de test
        2. Enviar respuesta correcta
        3. Ganar XP (+10)
        4. Mantener vidas
        5. Actualizar progreso
        """
        # Obtener ejercicio
        response = authenticated_client.get("/exercises/next?type=test")
        assert response.status_code == 200
        
        exercise = response.json()
        assert exercise["type"] == "test"
        assert "question" in exercise
        assert "options" in exercise
        assert len(exercise["options"]) >= 2
        
        # Completar correctamente
        submission = {
            "exercise_id": exercise["id"],
            "answer": exercise["correct_answer"],  # Mock conoce respuesta
            "time_spent": 25
        }
        
        response = authenticated_client.post("/exercises/submit", json=submission)
        assert response.status_code == 200
        
        result = response.json()
        assert result["correct"] is True
        assert result["xp_earned"] == 10
        assert result["life_lost"] is False
        
        # Verificar progreso
        progress = authenticated_client.get(f"/progress/exercises/{exercise['id']}").json()
        assert progress["completed"] is True
        assert progress["score"] == 100
        assert progress["attempts"] == 1
    
    def test_complete_camera_exercise_simulated(
        self, 
        authenticated_client, 
        camera_mock,
        ml_inference_mock
    ):
        """
        Test E2E: Completar ejercicio de cámara (simulado)
        
        Flujo:
        1. Obtener ejercicio de cámara
        2. Simular captura de video
        3. Enviar frames al ML service
        4. Obtener predicción
        5. Validar seña correcta
        6. Ganar XP (+15 por cámara)
        """
        # Obtener ejercicio de cámara
        response = authenticated_client.get("/exercises/next?type=camera")
        assert response.status_code == 200
        
        exercise = response.json()
        assert exercise["type"] == "camera"
        assert "target_sign" in exercise
        assert "video_demo_url" in exercise
        
        target_sign = exercise["target_sign"]
        
        # Simular captura de video (10 frames)
        frames = camera_mock.capture_sign_video(target_sign, num_frames=10)
        assert len(frames) == 10
        
        # Enviar frames al ML service
        ml_request = {
            "exercise_id": exercise["id"],
            "frames": frames,  # Base64 encoded images
            "fps": 30
        }
        
        response = authenticated_client.post("/ml/predict-sign", json=ml_request)
        assert response.status_code == 200
        
        prediction = response.json()
        assert prediction["predicted_sign"] == target_sign
        assert prediction["confidence"] >= 0.85
        
        # Completar ejercicio con predicción
        submission = {
            "exercise_id": exercise["id"],
            "prediction_id": prediction["prediction_id"],
            "time_spent": 45
        }
        
        response = authenticated_client.post("/exercises/submit", json=submission)
        assert response.status_code == 200
        
        result = response.json()
        assert result["correct"] is True
        assert result["xp_earned"] == 15  # Cámara da más XP
        assert result["confidence"] >= 0.85
    
    def test_exercise_with_low_confidence_rejected(
        self, 
        authenticated_client,
        camera_mock,
        ml_inference_mock
    ):
        """Test E2E: Ejercicio rechazado por baja confianza"""
        
        exercise = authenticated_client.get("/exercises/next?type=camera").json()
        
        # Simular seña incorrecta/mala calidad
        frames = camera_mock.capture_poor_quality_video()
        
        ml_request = {
            "exercise_id": exercise["id"],
            "frames": frames,
            "fps": 30
        }
        
        prediction = authenticated_client.post("/ml/predict-sign", json=ml_request).json()
        assert prediction["confidence"] < 0.7  # Baja confianza
        
        # Intentar completar
        submission = {
            "exercise_id": exercise["id"],
            "prediction_id": prediction["prediction_id"],
            "time_spent": 30
        }
        
        response = authenticated_client.post("/exercises/submit", json=submission)
        assert response.status_code == 400
        
        error = response.json()
        assert "confidence too low" in error["detail"].lower()
        assert error["min_confidence"] == 0.7


class TestXPAndLevelUpFlow:
    """Tests de flujo de XP y subida de nivel"""
    
    def test_gain_xp_from_exercises(self, authenticated_client):
        """
        Test E2E: Ganar XP completando ejercicios
        
        Flujo:
        1. Completar 3 ejercicios de test (+10 XP c/u)
        2. Completar 2 ejercicios de cámara (+15 XP c/u)
        3. Total XP = 60
        4. Verificar actualización de perfil
        """
        initial_profile = authenticated_client.get("/users/me").json()
        initial_xp = initial_profile["xp"]
        
        # Completar 3 ejercicios de test
        for i in range(3):
            exercise = authenticated_client.get("/exercises/next?type=test").json()
            submission = {
                "exercise_id": exercise["id"],
                "answer": exercise["correct_answer"],
                "time_spent": 20
            }
            result = authenticated_client.post("/exercises/submit", json=submission).json()
            assert result["xp_earned"] == 10
        
        # Completar 2 ejercicios de cámara (mock)
        for i in range(2):
            exercise = authenticated_client.get("/exercises/next?type=camera").json()
            # Simular completación exitosa
            result = authenticated_client.post(
                "/exercises/submit",
                json={
                    "exercise_id": exercise["id"],
                    "prediction_id": f"pred_{i}",
                    "time_spent": 40
                }
            ).json()
            assert result["xp_earned"] == 15
        
        # Verificar XP total
        final_profile = authenticated_client.get("/users/me").json()
        expected_xp = initial_xp + (3 * 10) + (2 * 15)
        assert final_profile["xp"] == expected_xp
    
    def test_level_up_on_xp_threshold(self, authenticated_client, user_near_levelup):
        """
        Test E2E: Subida de nivel al alcanzar threshold
        
        Flujo:
        1. Usuario con 95 XP (5 XP para level 2)
        2. Completar ejercicio (+10 XP)
        3. LevelUp a nivel 2
        4. Recompensas: +1 vida, +10 gemas
        5. Notificación de levelUp
        """
        # Estado inicial: Nivel 1, 95 XP (threshold: 100)
        profile = authenticated_client.get("/users/me").json()
        assert profile["level"] == 1
        assert profile["xp"] == 95
        initial_lives = profile["lives"]
        initial_gems = profile["gems"]
        
        # Completar ejercicio
        exercise = authenticated_client.get("/exercises/next?type=test").json()
        response = authenticated_client.post(
            "/exercises/submit",
            json={
                "exercise_id": exercise["id"],
                "answer": exercise["correct_answer"],
                "time_spent": 25
            }
        )
        
        result = response.json()
        assert result["xp_earned"] == 10
        assert result["level_up"] is True
        assert result["new_level"] == 2
        
        # Verificar recompensas
        assert "rewards" in result
        rewards = result["rewards"]
        assert rewards["lives"] == 1
        assert rewards["gems"] == 10
        
        # Verificar perfil actualizado
        profile = authenticated_client.get("/users/me").json()
        assert profile["level"] == 2
        assert profile["xp"] == 105  # 95 + 10
        assert profile["lives"] == min(initial_lives + 1, 5)  # Max 5
        assert profile["gems"] == initial_gems + 10
    
    def test_multiple_level_ups(self, authenticated_client):
        """Test E2E: Múltiples subidas de nivel"""
        
        # Simular completar muchos ejercicios
        # Level 1->2: 100 XP
        # Level 2->3: 250 XP total
        # Level 3->4: 500 XP total
        
        profile = authenticated_client.get("/users/me").json()
        assert profile["level"] == 1
        assert profile["xp"] == 0
        
        # Completar suficientes ejercicios para level 3
        total_exercises = 30  # 30 * 10 = 300 XP
        
        for i in range(total_exercises):
            exercise = authenticated_client.get("/exercises/next?type=test").json()
            authenticated_client.post(
                "/exercises/submit",
                json={
                    "exercise_id": exercise["id"],
                    "answer": exercise["correct_answer"],
                    "time_spent": 20
                }
            )
        
        # Verificar nivel final
        profile = authenticated_client.get("/users/me").json()
        assert profile["level"] >= 3
        assert profile["xp"] >= 300
    
    def test_xp_bonus_for_streak(self, authenticated_client, user_with_streak):
        """Test E2E: Bonus de XP por racha"""
        
        # Usuario con racha de 7 días (bonus 10%)
        profile = authenticated_client.get("/users/me").json()
        assert profile["streak"] == 7
        
        # Completar ejercicio
        exercise = authenticated_client.get("/exercises/next?type=test").json()
        result = authenticated_client.post(
            "/exercises/submit",
            json={
                "exercise_id": exercise["id"],
                "answer": exercise["correct_answer"],
                "time_spent": 20
            }
        ).json()
        
        # XP base = 10, con 10% bonus = 11
        assert result["xp_earned"] == 11
        assert result["streak_bonus"] == 0.1


class TestCompleteUserJourneyFlow:
    """Tests de flujo completo de usuario (journey)"""
    
    def test_complete_daily_session(self, authenticated_client):
        """
        Test E2E: Sesión diaria completa
        
        Flujo completo:
        1. Usuario inicia sesión
        2. Completa 5 ejercicios variados
        3. Gana XP y potencialmente sube de nivel
        4. Pierde y regenera vidas
        5. Mantiene racha diaria
        6. Cierra sesión
        """
        # Inicio de sesión
        start_time = datetime.utcnow()
        session_response = authenticated_client.post("/sessions/start")
        assert session_response.status_code == 200
        
        session = session_response.json()
        session_id = session["session_id"]
        
        # Estado inicial
        initial_profile = authenticated_client.get("/users/me").json()
        
        # Completar 5 ejercicios (mix de test y cámara)
        exercises_completed = []
        
        for i in range(5):
            exercise_type = "test" if i % 2 == 0 else "camera"
            exercise = authenticated_client.get(
                f"/exercises/next?type={exercise_type}"
            ).json()
            
            # Simular completación
            if exercise_type == "test":
                submission = {
                    "exercise_id": exercise["id"],
                    "answer": exercise["correct_answer"],
                    "time_spent": 20 + i * 5
                }
            else:
                submission = {
                    "exercise_id": exercise["id"],
                    "prediction_id": f"pred_{i}",
                    "time_spent": 40 + i * 5
                }
            
            result = authenticated_client.post(
                "/exercises/submit",
                json=submission
            ).json()
            
            exercises_completed.append(result)
        
        # Finalizar sesión
        end_response = authenticated_client.post(
            f"/sessions/{session_id}/end",
            json={"exercises_completed": len(exercises_completed)}
        )
        assert end_response.status_code == 200
        
        session_summary = end_response.json()
        
        # Validar resumen de sesión
        assert session_summary["exercises_completed"] == 5
        assert session_summary["total_xp_earned"] > 0
        assert session_summary["duration_seconds"] > 0
        
        # Verificar progreso final
        final_profile = authenticated_client.get("/users/me").json()
        assert final_profile["xp"] > initial_profile["xp"]
        
        # Verificar racha actualizada
        assert final_profile["streak"] >= initial_profile["streak"]
        assert final_profile["last_practice_date"] == datetime.utcnow().date().isoformat()
    
    def test_weekly_progress_tracking(self, authenticated_client, user_with_history):
        """Test E2E: Tracking de progreso semanal"""
        
        # Obtener estadísticas semanales
        response = authenticated_client.get("/stats/weekly")
        assert response.status_code == 200
        
        stats = response.json()
        
        assert "days_practiced" in stats
        assert "total_exercises" in stats
        assert "total_xp" in stats
        assert "average_accuracy" in stats
        assert "total_time_minutes" in stats
        
        # Validar estructura de datos diarios
        assert "daily_breakdown" in stats
        assert len(stats["daily_breakdown"]) <= 7
        
        for day in stats["daily_breakdown"]:
            assert "date" in day
            assert "exercises" in day
            assert "xp" in day
            assert "time_minutes" in day


# =============================================================================
# Fixtures compartidas se definen en conftest.py
# =============================================================================
