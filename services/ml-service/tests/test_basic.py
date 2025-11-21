import pytest
from httpx import AsyncClient
import base64
import io
from PIL import Image
import numpy as np

from app.main import app


def create_dummy_image_base64() -> str:
    """Crea una imagen dummy en base64"""
    # Crear imagen RGB simple
    img = Image.new('RGB', (224, 224), color=(73, 109, 137))
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return img_base64


@pytest.fixture(scope="function")
async def client():
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
    assert data["service"] == "ML Service"
    assert "device" in data


@pytest.mark.asyncio
async def test_predict_image_base64(client: AsyncClient):
    """Test predicción desde imagen base64"""
    img_base64 = create_dummy_image_base64()
    
    request_data = {
        "type": "image",
        "data": img_base64,
        "language_code": "ASL",
        "top_k": 5
    }
    
    response = await client.post("/api/predict", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "predictions" in data
    assert len(data["predictions"]) <= 5
    assert "processing_time_ms" in data


@pytest.mark.asyncio
async def test_predict_missing_data(client: AsyncClient):
    """Test predicción sin datos"""
    request_data = {
        "type": "image",
        "language_code": "ASL",
        "top_k": 3
    }
    
    response = await client.post("/api/predict", json=request_data)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_predict_video_not_implemented(client: AsyncClient):
    """Test que video prediction no está implementado"""
    request_data = {
        "type": "video",
        "data": "dummy_data",
        "language_code": "ASL",
        "top_k": 5
    }
    
    response = await client.post("/api/predict", json=request_data)
    assert response.status_code == 501


@pytest.mark.asyncio
async def test_detect_hands(client: AsyncClient):
    """Test detección de manos"""
    img_base64 = create_dummy_image_base64()
    
    response = await client.post("/api/detect-hands", json=img_base64)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "hands_detected" in data
    assert "hands" in data
    assert "processing_time_ms" in data


@pytest.mark.asyncio
async def test_get_model_info(client: AsyncClient):
    """Test obtener información del modelo"""
    response = await client.get("/api/model/info")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "framework" in data
    assert data["framework"] == "pytorch"
    assert "labels" in data
    assert isinstance(data["labels"], list)


@pytest.mark.asyncio
async def test_sagemaker_not_configured(client: AsyncClient):
    """Test que SageMaker no está configurado en local"""
    response = await client.post("/api/sagemaker/invoke", json="dummy_data")
    assert response.status_code == 501


@pytest.mark.asyncio
async def test_prediction_response_structure(client: AsyncClient):
    """Test estructura de respuesta de predicción"""
    img_base64 = create_dummy_image_base64()
    
    request_data = {
        "type": "image",
        "data": img_base64,
        "language_code": "ASL",
        "top_k": 3
    }
    
    response = await client.post("/api/predict", json=request_data)
    data = response.json()
    
    # Verificar estructura
    assert "predictions" in data
    if len(data["predictions"]) > 0:
        pred = data["predictions"][0]
        assert "sign_id" in pred
        assert "sign_name" in pred
        assert "confidence" in pred
        assert 0 <= pred["confidence"] <= 1


@pytest.mark.asyncio
async def test_top_k_parameter(client: AsyncClient):
    """Test que el parámetro top_k funciona"""
    img_base64 = create_dummy_image_base64()
    
    for k in [1, 3, 5, 10]:
        request_data = {
            "type": "image",
            "data": img_base64,
            "language_code": "ASL",
            "top_k": k
        }
        
        response = await client.post("/api/predict", json=request_data)
        data = response.json()
        assert len(data["predictions"]) <= k
