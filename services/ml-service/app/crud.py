import os
import io
import base64
import time
from typing import List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image
import mediapipe as mp
import torch

from app.core.config import get_settings
from app.core.db import get_aws_client, AWSClient
from app import schemas

settings = get_settings()


class HandDetector:
    """Detector de manos usando MediaPipe"""
    
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
    
    def detect_hands(self, image: np.ndarray) -> List[schemas.HandLandmarks]:
        """Detecta manos en una imagen"""
        # Convertir BGR a RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Procesar
        results = self.hands.process(image_rgb)
        
        hand_landmarks_list = []
        
        if results.multi_hand_landmarks:
            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                # Extraer landmarks
                landmarks = []
                for landmark in hand_landmarks.landmark:
                    landmarks.append({
                        'x': landmark.x,
                        'y': landmark.y,
                        'z': landmark.z
                    })
                
                # Handedness
                handedness = "Right"
                if results.multi_handedness and idx < len(results.multi_handedness):
                    handedness = results.multi_handedness[idx].classification[0].label
                
                hand_landmarks_list.append(schemas.HandLandmarks(
                    landmarks=landmarks,
                    handedness=handedness,
                    confidence=0.9  # Placeholder
                ))
        
        return hand_landmarks_list
    
    def close(self):
        """Cierra el detector"""
        self.hands.close()


class SignLanguageModel:
    """Modelo de clasificación de lenguaje de señas (Placeholder)"""
    
    def __init__(self):
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.labels = self._load_labels()
        self.model_loaded = False
    
    def _load_labels(self) -> List[str]:
        """Carga las etiquetas/clases del modelo"""
        # Placeholder - en producción se cargarían desde archivo
        return [
            "hello", "goodbye", "thanks", "yes", "no",
            "please", "sorry", "help", "love", "family",
            "A", "B", "C", "D", "E", "F", "G", "H", "I", "J"
        ]
    
    def load_model(self, model_path: str):
        """Carga el modelo desde disco"""
        if not os.path.exists(model_path):
            print(f"Warning: Model file not found at {model_path}. Using dummy predictions.")
            return
        
        try:
            self.model = torch.load(model_path, map_location=self.device)
            self.model.eval()
            self.model_loaded = True
        except Exception as e:
            print(f"Error loading model: {e}")
    
    def predict(
        self,
        image: np.ndarray,
        hand_landmarks: List[schemas.HandLandmarks],
        top_k: int = 5
    ) -> List[schemas.SignPrediction]:
        """Hace predicción de señas"""
        # Placeholder - implementación dummy
        # En producción usaría el modelo real
        
        if not self.model_loaded or not hand_landmarks:
            # Retornar predicciones dummy
            return [
                schemas.SignPrediction(
                    sign_id=f"sign_{i}",
                    sign_name=self.labels[i % len(self.labels)],
                    confidence=0.9 - (i * 0.1),
                    metadata={"dummy": True}
                )
                for i in range(min(top_k, 5))
            ]
        
        # TODO: Implementar predicción real con el modelo
        # 1. Preprocesar imagen y landmarks
        # 2. Pasar por el modelo
        # 3. Obtener top_k predicciones
        
        return []
    
    def predict_video(
        self,
        video_path: str,
        top_k: int = 5
    ) -> List[schemas.SignPrediction]:
        """Hace predicción de señas desde video"""
        # Placeholder
        return self.predict(np.zeros((224, 224, 3), dtype=np.uint8), [], top_k)


# Singleton instances
_hand_detector: Optional[HandDetector] = None
_sign_model: Optional[SignLanguageModel] = None


def get_hand_detector() -> HandDetector:
    """Retorna detector de manos (singleton)"""
    global _hand_detector
    if _hand_detector is None:
        _hand_detector = HandDetector()
    return _hand_detector


def get_sign_model() -> SignLanguageModel:
    """Retorna modelo de señas (singleton)"""
    global _sign_model
    if _sign_model is None:
        _sign_model = SignLanguageModel()
        # Intentar cargar modelo por defecto
        model_path = os.path.join(settings.MODEL_PATH, settings.DEFAULT_MODEL_NAME)
        _sign_model.load_model(model_path)
    return _sign_model


# Helper functions
def decode_base64_image(base64_str: str) -> np.ndarray:
    """Decodifica imagen base64 a numpy array"""
    img_bytes = base64.b64decode(base64_str)
    img_pil = Image.open(io.BytesIO(img_bytes))
    img_array = np.array(img_pil)
    
    # Convertir RGB a BGR para OpenCV
    if len(img_array.shape) == 3 and img_array.shape[2] == 3:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    return img_array


def encode_image_to_base64(image: np.ndarray) -> str:
    """Codifica imagen numpy a base64"""
    # Convertir BGR a RGB
    if len(image.shape) == 3 and image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    img_pil = Image.fromarray(image)
    buffer = io.BytesIO()
    img_pil.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return img_base64


async def predict_from_image(
    image_data: str,
    language_code: str,
    top_k: int
) -> schemas.PredictionResponse:
    """Predicción desde imagen base64"""
    start_time = time.time()
    
    # Decodificar imagen
    image = decode_base64_image(image_data)
    
    # Detectar manos
    detector = get_hand_detector()
    hands = detector.detect_hands(image)
    
    # Predecir señas
    model = get_sign_model()
    predictions = model.predict(image, hands, top_k)
    
    processing_time = (time.time() - start_time) * 1000  # ms
    
    return schemas.PredictionResponse(
        success=True,
        predictions=predictions,
        processing_time_ms=processing_time,
        metadata={
            "hands_detected": len(hands),
            "language_code": language_code
        }
    )


async def predict_from_url(
    url: str,
    language_code: str,
    top_k: int,
    aws_client: AWSClient
) -> schemas.PredictionResponse:
    """Predicción desde URL (S3)"""
    # TODO: Implementar descarga desde S3 y predicción
    raise NotImplementedError("URL prediction not yet implemented")


async def detect_hands_from_image(image_data: str) -> schemas.HandDetectionResponse:
    """Detecta manos en una imagen"""
    start_time = time.time()
    
    # Decodificar imagen
    image = decode_base64_image(image_data)
    
    # Detectar manos
    detector = get_hand_detector()
    hands = detector.detect_hands(image)
    
    processing_time = (time.time() - start_time) * 1000  # ms
    
    return schemas.HandDetectionResponse(
        success=True,
        hands_detected=len(hands),
        hands=hands,
        processing_time_ms=processing_time
    )
