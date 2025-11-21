"""
=============================================================================
AWS X-Ray Instrumentation for FastAPI
=============================================================================
Configuración y middleware para tracing distribuido con AWS X-Ray.
=============================================================================
"""

from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware
from aws_xray_sdk.core.async_context import AsyncContext
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import os


# =============================================================================
# Configuración de X-Ray
# =============================================================================

# Configurar contexto asíncrono para FastAPI
xray_recorder.configure(
    service=os.getenv('AWS_XRAY_TRACING_NAME', 'senas-api'),
    daemon_address=os.getenv('AWS_XRAY_DAEMON_ADDRESS', '127.0.0.1:2000'),
    context=AsyncContext(),
    sampling=True,
    plugins=('ECSPlugin',),  # Auto-detect ECS metadata
    context_missing='LOG_ERROR'  # Log errors instead of raising
)

# Patchear bibliotecas automáticamente
patch_all()  # Patchea boto3, httpx, psycopg2, etc.


# =============================================================================
# Middleware de X-Ray para FastAPI
# =============================================================================

class XRayFastAPIMiddleware(BaseHTTPMiddleware):
    """
    Middleware para capturar traces de requests HTTP en FastAPI.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Procesa cada request y crea un segment de X-Ray.
        """
        # Extraer información del request
        method = request.method
        url = str(request.url)
        client_ip = request.client.host if request.client else "unknown"
        
        # Comenzar segment principal
        segment_name = f"{method} {request.url.path}"
        
        # Crear segment con contexto del request
        segment = xray_recorder.begin_segment(
            name=segment_name,
            sampling=1  # Usar sampling rules configuradas
        )
        
        try:
            # Agregar metadata del request al segment
            segment.put_http_meta('request', {
                'method': method,
                'url': url,
                'client_ip': client_ip,
                'user_agent': request.headers.get('user-agent', 'unknown')
            })
            
            # Agregar annotations (indexables para búsqueda)
            segment.put_annotation('method', method)
            segment.put_annotation('path', request.url.path)
            
            # Si hay usuario autenticado, agregarlo
            if hasattr(request.state, 'user_id'):
                segment.put_annotation('user_id', request.state.user_id)
            
            # Timestamp de inicio
            start_time = time.time()
            
            # Procesar request
            response = await call_next(request)
            
            # Timestamp de fin
            duration = time.time() - start_time
            
            # Agregar metadata de response
            segment.put_http_meta('response', {
                'status': response.status_code,
                'content_length': response.headers.get('content-length', 0)
            })
            
            # Annotations adicionales
            segment.put_annotation('status_code', response.status_code)
            segment.put_metadata('timing', {
                'duration_ms': duration * 1000
            }, 'performance')
            
            # Marcar como error si status >= 400
            if response.status_code >= 400:
                if response.status_code >= 500:
                    segment.put_http_meta('response', {
                        'error': True
                    })
                else:
                    segment.put_http_meta('response', {
                        'fault': True
                    })
            
            return response
            
        except Exception as e:
            # Capturar excepción en segment
            segment.put_http_meta('response', {
                'error': True,
                'status': 500
            })
            
            # Agregar exception details
            xray_recorder.record_exception(e)
            
            raise
            
        finally:
            # Cerrar segment
            xray_recorder.end_segment()


# =============================================================================
# Decorador para funciones custom
# =============================================================================

def trace_function(name: str = None, **metadata):
    """
    Decorador para agregar tracing a funciones específicas.
    
    Usage:
        @trace_function(name="process_exercise")
        async def process_exercise(exercise_id: str):
            # ... logic ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            func_name = name or func.__name__
            
            with xray_recorder.capture_async(func_name) as subsegment:
                # Agregar metadata custom
                for key, value in metadata.items():
                    subsegment.put_metadata(key, value, 'custom')
                
                # Ejecutar función
                result = await func(*args, **kwargs)
                
                return result
        
        return wrapper
    return decorator


# =============================================================================
# Context Manager para subsegments
# =============================================================================

class trace_subsegment:
    """
    Context manager para crear subsegments custom.
    
    Usage:
        async with trace_subsegment("database_query") as subseg:
            subseg.put_annotation("table", "users")
            result = await db.query(...)
    """
    
    def __init__(self, name: str):
        self.name = name
        self.subsegment = None
    
    async def __aenter__(self):
        self.subsegment = xray_recorder.begin_subsegment(self.name)
        return self.subsegment
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            xray_recorder.record_exception(exc_val)
        
        xray_recorder.end_subsegment()


# =============================================================================
# Helpers para tracing common operations
# =============================================================================

async def trace_database_query(operation: str, table: str):
    """
    Helper para trace de queries de base de datos.
    
    Usage:
        async with trace_database_query("SELECT", "users") as subseg:
            result = await db.execute(query)
    """
    subseg = xray_recorder.begin_subsegment(f"database.{operation}")
    
    try:
        subseg.put_annotation("operation", operation)
        subseg.put_annotation("table", table)
        subseg.namespace = "remote"
        
        yield subseg
        
    finally:
        xray_recorder.end_subsegment()


async def trace_http_call(service_name: str, url: str):
    """
    Helper para trace de llamadas HTTP externas.
    
    Usage:
        async with trace_http_call("ml-service", "http://ml:8080/predict"):
            response = await httpx.post(...)
    """
    subseg = xray_recorder.begin_subsegment(service_name)
    
    try:
        subseg.put_metadata("url", url, "http")
        subseg.namespace = "remote"
        
        yield subseg
        
    finally:
        xray_recorder.end_subsegment()


async def trace_aws_service(service: str, operation: str):
    """
    Helper para trace de llamadas a servicios AWS.
    
    Usage:
        async with trace_aws_service("s3", "PutObject") as subseg:
            await s3_client.put_object(...)
    """
    subseg = xray_recorder.begin_subsegment(f"{service}.{operation}")
    
    try:
        subseg.put_annotation("aws_service", service)
        subseg.put_annotation("operation", operation)
        subseg.namespace = "aws"
        
        yield subseg
        
    finally:
        xray_recorder.end_subsegment()


# =============================================================================
# Setup function para FastAPI
# =============================================================================

def setup_xray(app: FastAPI, enable: bool = True):
    """
    Configura X-Ray tracing en la aplicación FastAPI.
    
    Args:
        app: Instancia de FastAPI
        enable: Si False, deshabilita X-Ray (útil para local dev)
    
    Usage:
        from fastapi import FastAPI
        from xray_config import setup_xray
        
        app = FastAPI()
        setup_xray(app, enable=os.getenv('ENABLE_XRAY', 'true') == 'true')
    """
    if not enable:
        # Deshabilitar X-Ray
        xray_recorder.configure(context_missing='LOG_ERROR')
        xray_recorder.begin_segment = lambda *args, **kwargs: None
        xray_recorder.end_segment = lambda *args, **kwargs: None
        return
    
    # Agregar middleware
    app.add_middleware(XRayFastAPIMiddleware)
    
    # Agregar metadata de la aplicación
    xray_recorder.put_metadata('app_name', app.title, 'application')
    xray_recorder.put_metadata('app_version', app.version, 'application')
    
    print(f"✅ X-Ray tracing enabled for {app.title}")


# =============================================================================
# Ejemplo de uso en endpoints
# =============================================================================

"""
# En tu archivo main.py

from fastapi import FastAPI, Depends
from xray_config import setup_xray, trace_function, trace_subsegment

app = FastAPI(title="Senas API", version="1.0.0")

# Setup X-Ray
setup_xray(app, enable=os.getenv('ENABLE_XRAY', 'true') == 'true')

# Endpoint con tracing automático (vía middleware)
@app.get("/users/{user_id}")
async def get_user(user_id: str):
    # El middleware crea el segment principal automáticamente
    
    # Crear subsegment para operación de DB
    async with trace_subsegment("fetch_user_from_db") as subseg:
        subseg.put_annotation("user_id", user_id)
        user = await db.get_user(user_id)
    
    return user

# Endpoint con decorador custom
@app.post("/exercises/submit")
@trace_function(name="submit_exercise", category="business_logic")
async def submit_exercise(exercise_id: str, answer: str):
    # Subsegment para validación
    async with trace_subsegment("validate_answer") as subseg:
        subseg.put_annotation("exercise_id", exercise_id)
        is_correct = validate_answer(exercise_id, answer)
        subseg.put_metadata("correct", is_correct, "result")
    
    # Subsegment para actualizar XP
    if is_correct:
        async with trace_subsegment("update_xp") as subseg:
            xp_earned = await update_user_xp(user_id, 10)
            subseg.put_metadata("xp_earned", xp_earned, "result")
    
    return {"correct": is_correct}

# Endpoint con trace de llamada externa
@app.post("/ml/predict")
async def predict_sign(frames: list):
    async with trace_http_call("ml-service", f"{ML_SERVICE_URL}/predict"):
        response = await httpx.post(f"{ML_SERVICE_URL}/predict", json=frames)
    
    return response.json()
"""
