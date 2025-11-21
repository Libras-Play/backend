"""
FASE 8: Exercise Selector Service - Motor de Selección Inteligente

Implementa los 7 criterios para orden adaptativo de ejercicios:
1. Historial de errores por tipo (test vs camera)
2. Errores por señal específica
3. Tiempo de respuesta
4. Nivel del usuario
5. Confianza (confidence_score)
6. Peso temático
7. Anti-repetición

EVITA ERROR #1: No usa protected namespaces
EVITA ERROR #P: Operaciones idempotentes
"""
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, select
from datetime import datetime, timedelta
import random
import logging

from app.models import (
    Exercise,
    ExerciseType,
    DifficultyLevel,
    UserExercisePerformance
)

logger = logging.getLogger(__name__)


class ExerciseSelectorService:
    """
    Servicio de selección inteligente de ejercicios con 7 criterios.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Configuración de pesos para los 7 criterios
        self.WEIGHTS = {
            'error_history_by_type': 0.20,      # Criterio 1
            'error_by_specific_sign': 0.20,     # Criterio 2
            'response_time': 0.15,              # Criterio 3
            'user_level': 0.15,                 # Criterio 4
            'confidence': 0.15,                 # Criterio 5
            'thematic_weight': 0.10,            # Criterio 6
            'anti_repetition': 0.05             # Criterio 7
        }
    
    async def select_next_exercise(
        self,
        user_id: str,
        topic_id: int,
        difficulty: str,
        recent_exercises: List[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Selecciona el próximo ejercicio óptimo para el usuario.
        
        Args:
            user_id: ID del usuario
            topic_id: ID del topic
            difficulty: Nivel de dificultad (BEGINNER/INTERMEDIATE/ADVANCED)
            recent_exercises: IDs de ejercicios recientes (para anti-repetición)
        
        Returns:
            Dict con ejercicio seleccionado + metadata de selección
        """
        # 1. Filtrar pool de ejercicios disponibles
        pool = await self._get_exercise_pool(topic_id, difficulty, recent_exercises or [])
        
        if not pool:
            logger.warning(f"No exercises found for topic={topic_id}, difficulty={difficulty}")
            return None
        
        # 2. Obtener historial de desempeño del usuario
        user_performance = await self._get_user_performance(user_id)
        
        # 3. Calcular scores para cada ejercicio según los 7 criterios
        scored_exercises = []
        for exercise in pool:
            score, breakdown = await self._calculate_exercise_score(
                exercise,
                user_id,
                user_performance,
                recent_exercises or []
            )
            scored_exercises.append({
                'exercise': exercise,
                'score': score,
                'breakdown': breakdown
            })
        
        # 4. Ordenar por score (mayor a menor)
        scored_exercises.sort(key=lambda x: x['score'], reverse=True)
        
        # 5. Seleccionar top exercise
        selected = scored_exercises[0]
        
        logger.info(
            f"Selected exercise_id={selected['exercise'].id} with score={selected['score']:.3f} "
            f"for user={user_id}, topic={topic_id}"
        )
        
        return {
            'exercise_id': selected['exercise'].id,
            'exercise_type': selected['exercise'].exercise_type.value,
            'title': selected['exercise'].title,
            'statement': selected['exercise'].statement,
            'img_url': selected['exercise'].img_url,
            'video_url': selected['exercise'].video_url,
            'answers': selected['exercise'].answers if selected['exercise'].exercise_type == ExerciseType.TEST else None,
            'expected_sign': selected['exercise'].expected_sign if selected['exercise'].exercise_type == ExerciseType.CAMERA else None,
            'difficulty': selected['exercise'].difficulty.value,
            'selection_score': selected['score'],
            'selection_reasons': selected['breakdown'],
            'next_recommendation': self._get_next_recommendation(selected['exercise'], user_performance)
        }
    
    async def _get_exercise_pool(
        self,
        topic_id: int,
        difficulty: str,
        exclude_ids: List[int]
    ) -> List[Exercise]:
        """
        Obtiene pool de ejercicios disponibles filtrados por topic y difficulty.
        
        EVITA ERROR #P: Query idempotente
        """
        query = select(Exercise).where(
            and_(
                Exercise.topic_id == topic_id,
                Exercise.difficulty == DifficultyLevel(difficulty)
            )
        )
        
        if exclude_ids:
            query = query.where(~Exercise.id.in_(exclude_ids))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _get_user_performance(self, user_id: str) -> Dict[int, UserExercisePerformance]:
        """
        Obtiene historial de desempeño del usuario indexado por exercise_id.
        """
        query = select(UserExercisePerformance).where(
            UserExercisePerformance.user_id == user_id
        )
        result = await self.db.execute(query)
        performances = result.scalars().all()
        
        return {p.exercise_id: p for p in performances}
    
    async def _calculate_exercise_score(
        self,
        exercise: Exercise,
        user_id: str,
        user_performance: Dict[int, UserExercisePerformance],
        recent_exercises: List[int]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calcula score total del ejercicio basado en los 7 criterios.
        
        Returns:
            (score, breakdown) donde breakdown contiene scores individuales
        """
        breakdown = {}
        
        # Criterio 1: Historial de errores por tipo
        breakdown['error_history_by_type'] = await self._score_error_history_by_type(
            exercise,
            user_performance
        )
        
        # Criterio 2: Errores por señal específica
        breakdown['error_by_specific_sign'] = self._score_error_by_sign(
            exercise,
            user_performance
        )
        
        # Criterio 3: Tiempo de respuesta
        breakdown['response_time'] = self._score_response_time(
            exercise,
            user_performance
        )
        
        # Criterio 4: Nivel del usuario (basado en performance general)
        breakdown['user_level'] = self._score_user_level(
            exercise,
            user_performance
        )
        
        # Criterio 5: Confianza
        breakdown['confidence'] = self._score_confidence(
            exercise,
            user_performance
        )
        
        # Criterio 6: Peso temático
        breakdown['thematic_weight'] = self._score_thematic_weight(
            exercise
        )
        
        # Criterio 7: Anti-repetición
        breakdown['anti_repetition'] = await self._score_anti_repetition(
            exercise,
            recent_exercises
        )
        
        # Calcular score total ponderado
        total_score = sum(
            self.WEIGHTS[key] * value
            for key, value in breakdown.items()
        )
        
        return total_score, breakdown
    
    # ========== IMPLEMENTACIÓN DE LOS 7 CRITERIOS ==========
    
    async def _score_error_history_by_type(
        self,
        exercise: Exercise,
        user_performance: Dict[int, UserExercisePerformance]
    ) -> float:
        """
        Criterio 1: Historial de errores por tipo.
        
        Si falla en TEST → mayor probabilidad de TEST
        Si falla en CAMERA → mayor probabilidad de CAMERA
        """
        # Filtrar performance por tipo
        same_type_performances = []
        for eid, p in user_performance.items():
            result = await self.db.execute(select(Exercise).where(Exercise.id == eid))
            ex = result.scalar_one_or_none()
            if ex and ex.exercise_type == exercise.exercise_type:
                same_type_performances.append(p)
        
        if not same_type_performances:
            return 0.5  # Neutral si no hay historial
        
        # Calcular tasa de error del mismo tipo
        total_attempts = sum(p.attempts for p in same_type_performances)
        total_errors = sum(p.errors for p in same_type_performances)
        
        if total_attempts == 0:
            return 0.5
        
        error_rate = total_errors / total_attempts
        
        # Mayor error_rate → mayor score (necesita práctica)
        return min(error_rate * 1.5, 1.0)
    
    def _score_error_by_sign(
        self,
        exercise: Exercise,
        user_performance: Dict[int, UserExercisePerformance]
    ) -> float:
        """
        Criterio 2: Errores por señal específica.
        
        Si siempre falla "letra M" → priorizar ese ejercicio
        """
        perf = user_performance.get(exercise.id)
        
        if not perf:
            return 0.5  # Neutral si no hay historial
        
        if perf.attempts == 0:
            return 0.5
        
        # Tasa de error de este ejercicio específico
        error_rate = perf.errors / perf.attempts
        
        # Mayor error_rate → mayor prioridad
        return min(error_rate * 1.5, 1.0)
    
    def _score_response_time(
        self,
        exercise: Exercise,
        user_performance: Dict[int, UserExercisePerformance]
    ) -> float:
        """
        Criterio 3: Tiempo de respuesta.
        
        Rápido → incrementar dificultad (score bajo para easy, alto para hard)
        Lento → bajar dificultad (score alto para easy, bajo para hard)
        """
        perf = user_performance.get(exercise.id)
        
        if not perf or not perf.avg_response_time:
            return 0.5  # Neutral
        
        # Definir tiempos baseline por dificultad
        baseline_times = {
            DifficultyLevel.BEGINNER: 5.0,         # 5 segundos
            DifficultyLevel.INTERMEDIATE: 8.0,     # 8 segundos
            DifficultyLevel.ADVANCED: 12.0         # 12 segundos
        }
        
        baseline = baseline_times.get(exercise.difficulty, 8.0)
        ratio = perf.avg_response_time / baseline
        
        # Si es lento (ratio > 1.0) en este ejercicio → dar mayor prioridad
        if ratio > 1.2:
            return 0.7
        elif ratio < 0.8:
            return 0.3
        else:
            return 0.5
    
    def _score_user_level(
        self,
        exercise: Exercise,
        user_performance: Dict[int, UserExercisePerformance]
    ) -> float:
        """
        Criterio 4: Nivel del usuario.
        
        Beginner → más repetición, más TEST
        Intermediate → variación moderada
        Advanced → más CAMERA, menos TEST
        """
        if not user_performance:
            # Usuario nuevo → priorizar exercises fáciles y TEST
            if exercise.difficulty == DifficultyLevel.EASY:
                return 0.8 if exercise.exercise_type == ExerciseType.TEST else 0.6
            else:
                return 0.3
        
        # Calcular nivel basado en confidence promedio
        avg_confidence = sum(p.confidence_score for p in user_performance.values()) / len(user_performance)
        
        if avg_confidence < 0.4:  # Beginner
            if exercise.difficulty == DifficultyLevel.BEGINNER:
                return 0.8 if exercise.exercise_type == ExerciseType.TEST else 0.5
            return 0.2
        elif avg_confidence < 0.7:  # Intermediate
            if exercise.difficulty == DifficultyLevel.INTERMEDIATE:
                return 0.7
            return 0.4
        else:  # Advanced
            if exercise.difficulty == DifficultyLevel.ADVANCED:
                return 0.8 if exercise.exercise_type == ExerciseType.CAMERA else 0.6
            return 0.3
    
    def _score_confidence(
        self,
        exercise: Exercise,
        user_performance: Dict[int, UserExercisePerformance]
    ) -> float:
        """
        Criterio 5: Confianza (confidence_score).
        
        Bajo → ejercicios fáciles
        Alto → ejercicios difíciles
        """
        perf = user_performance.get(exercise.id)
        
        if not perf:
            return 0.5  # Neutral
        
        confidence = perf.confidence_score
        
        # Invertir confidence si ejercicio es fácil (baja confianza → priorizar fácil)
        if exercise.difficulty == DifficultyLevel.BEGINNER:
            return 1.0 - confidence
        elif exercise.difficulty == DifficultyLevel.ADVANCED:
            return confidence
        else:
            return 0.5
    
    def _score_thematic_weight(self, exercise: Exercise) -> float:
        """
        Criterio 6: Peso temático.
        
        Ejemplo: En abecedario, priorizar letras confusas (M/N, P/Q)
        En números, priorizar pares conflictivos (6/9, 1/7)
        
        NOTA: Implementación básica, se puede extender con metadatos de ejercicios
        """
        # Por ahora retorna neutral, se puede extender con lógica específica por topic
        return 0.5
    
    async def _score_anti_repetition(
        self,
        exercise: Exercise,
        recent_exercises: List[int]
    ) -> float:
        """
        Criterio 7: Anti-repetición.
        
        No permitir 3 ejercicios del mismo tipo seguidos.
        """
        if not recent_exercises or len(recent_exercises) < 2:
            return 0.5  # Neutral si no hay historial suficiente
        
        # Obtener tipos de ejercicios recientes
        recent_types = []
        for ex_id in recent_exercises[-2:]:  # Últimos 2
            result = await self.db.execute(select(Exercise).where(Exercise.id == ex_id))
            ex = result.scalar_one_or_none()
            if ex:
                recent_types.append(ex.exercise_type)
        
        # Si los últimos 2 son del mismo tipo, penalizar ese tipo
        if len(recent_types) == 2 and recent_types[0] == recent_types[1] == exercise.exercise_type:
            return 0.1  # Fuerte penalización
        
        return 0.5
    
    def _get_next_recommendation(
        self,
        current_exercise: Exercise,
        user_performance: Dict[int, UserExercisePerformance]
    ) -> Dict[str, str]:
        """
        Sugiere próximo paso basado en el ejercicio actual.
        """
        perf = user_performance.get(current_exercise.id)
        
        if not perf:
            return {
                'type': 'continue',
                'message': 'Complete this exercise to get personalized recommendations'
            }
        
        if perf.confidence_score < 0.4:
            return {
                'type': 'practice_more',
                'message': 'Practice similar exercises to build confidence'
            }
        elif perf.confidence_score > 0.8:
            return {
                'type': 'level_up',
                'message': 'Try harder exercises to keep challenging yourself'
            }
        else:
            return {
                'type': 'continue',
                'message': 'Keep practicing to improve your skills'
            }


class AdaptiveDifficultyAIProvider:
    """
    FUTURO: Provider para IA de dificultad adaptativa.
    
    FASE 8: Solo interfaz mock, NO implementa IA real.
    """
    
    def get_prediction(self, user_id: str, exercise_history: List[Dict]) -> Dict[str, Any]:
        """
        MOCK: Retorna predicción simulada.
        
        En futuro: llamar a modelo ML entrenado.
        """
        return {
            'predicted_difficulty': 'INTERMEDIATE',
            'confidence': 0.0,
            'ai_enabled': False,
            'model_version': 'mock'
        }
    
    def suggest_next(self, user_id: str) -> Dict[str, Any]:
        """
        MOCK: Retorna sugerencia simulada.
        """
        return {
            'suggested_topic_id': None,
            'suggested_difficulty': 'INTERMEDIATE',
            'ai_enabled': False,
            'model_version': 'mock'
        }
