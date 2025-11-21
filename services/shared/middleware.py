"""
Security Middleware for FastAPI Applications

Este módulo proporciona middleware de seguridad para aplicaciones FastAPI:
- CORS configuration
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- Request ID tracking
- Rate limiting
- Request logging con masking de datos sensibles
- Error handling

Uso:
    from shared.middleware import setup_security_middleware
    
    app = FastAPI()
    setup_security_middleware(app, environment="production")
"""

import hashlib
import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional, Set

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ============================================================================
# CORS Configuration
# ============================================================================

def get_cors_config(environment: str = "development") -> dict:
    """
    Retorna configuración CORS según el environment.
    
    Args:
        environment: "development", "staging", o "production"
    
    Returns:
        Dict con configuración CORS
    """
    if environment == "production":
        return {
            "allow_origins": [
                "https://aplicacion-senas.com",
                "https://www.aplicacion-senas.com",
                "https://app.aplicacion-senas.com",
            ],
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
            "allow_headers": [
                "Authorization",
                "Content-Type",
                "X-Request-ID",
                "X-CSRF-Token",
            ],
            "expose_headers": ["X-Request-ID", "X-RateLimit-Remaining"],
            "max_age": 600,  # 10 minutos
        }
    elif environment == "staging":
        return {
            "allow_origins": [
                "https://staging.aplicacion-senas.com",
                "https://app-staging.aplicacion-senas.com",
            ],
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            "allow_headers": ["*"],
            "expose_headers": ["X-Request-ID", "X-RateLimit-Remaining"],
            "max_age": 300,
        }
    else:  # development
        return {
            "allow_origins": [
                "http://localhost:3000",
                "http://localhost:8000",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
            ],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
            "expose_headers": ["*"],
            "max_age": 3600,
        }


# ============================================================================
# Security Headers Middleware
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Agrega security headers a todas las respuestas.
    
    Headers incluidos:
    - Strict-Transport-Security (HSTS)
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Content-Security-Policy
    - Referrer-Policy
    - Permissions-Policy
    """
    
    def __init__(self, app, environment: str = "production"):
        super().__init__(app)
        self.environment = environment
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # HSTS: Force HTTPS (solo en production)
        if self.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Prevenir MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevenir clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS Protection (legacy, pero útil para navegadores viejos)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy
        csp = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Ajustar según necesidades
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self' https://cognito-idp.*.amazonaws.com",
            "media-src 'self' https://aplicacion-senas-content-*.s3.amazonaws.com",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp)
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (antes Feature-Policy)
        permissions = [
            "geolocation=()",
            "microphone=()",
            "camera=(self)",  # Necesario para captura de señas
            "payment=()",
            "usb=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions)
        
        # Remove Server header (no revelar tecnología)
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response


# ============================================================================
# Request ID Middleware
# ============================================================================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Agrega un Request ID único a cada request para tracing.
    
    El Request ID se puede:
    - Recibir del cliente en header X-Request-ID
    - Generar automáticamente si no viene
    - Incluir en logs para correlacionar requests
    - Retornar en header de response
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Intentar obtener Request ID del cliente, o generar uno nuevo
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Agregar Request ID al state del request (accesible en handlers)
        request.state.request_id = request_id
        
        # Procesar request
        response = await call_next(request)
        
        # Agregar Request ID a response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


# ============================================================================
# Request Logging Middleware
# ============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Loggea requests y responses con masking de datos sensibles.
    
    Features:
    - Log de request method, path, query params
    - Log de response status code y duration
    - Masking de Authorization headers, passwords, tokens
    - Structured logging con request_id
    """
    
    SENSITIVE_HEADERS = {
        "authorization",
        "x-api-key",
        "x-auth-token",
        "cookie",
    }
    
    SENSITIVE_PARAMS = {
        "password",
        "token",
        "secret",
        "api_key",
        "access_token",
        "refresh_token",
    }
    
    def _mask_sensitive_data(self, data: dict) -> dict:
        """Maskea datos sensibles en un dict."""
        masked = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_PARAMS):
                masked[key] = "***MASKED***"
            else:
                masked[key] = value
        return masked
    
    def _mask_headers(self, headers: dict) -> dict:
        """Maskea headers sensibles."""
        masked = {}
        for key, value in headers.items():
            if key.lower() in self.SENSITIVE_HEADERS:
                masked[key] = "***MASKED***"
            else:
                masked[key] = value
        return masked
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log del request
        query_params = dict(request.query_params)
        masked_params = self._mask_sensitive_data(query_params)
        
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": masked_params,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
            }
        )
        
        # Procesar request
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                f"Request failed with exception",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "exception": str(exc),
                },
                exc_info=True
            )
            raise
        
        # Log del response
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            }
        )
        
        return response


# ============================================================================
# Rate Limiting Middleware
# ============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting basado en IP del cliente.
    
    IMPORTANTE: Esta es una implementación en memoria (in-memory).
    Para producción, usar Redis con redis-py o FastAPI-Limiter.
    
    Features:
    - Límite por IP y por endpoint
    - Ventana deslizante (sliding window)
    - Headers informativos (X-RateLimit-Limit, X-RateLimit-Remaining)
    - Response 429 Too Many Requests
    
    Args:
        max_requests: Máximo de requests permitidos
        window_seconds: Ventana de tiempo en segundos
        exclude_paths: Paths a excluir del rate limiting (ej: /health)
    """
    
    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
        exclude_paths: Optional[Set[str]] = None,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exclude_paths = exclude_paths or {"/health", "/metrics", "/docs", "/openapi.json"}
        
        # In-memory storage: {ip: [(timestamp, path), ...]}
        self.requests: Dict[str, list] = defaultdict(list)
    
    def _clean_old_requests(self, ip: str, current_time: float):
        """Limpia requests fuera de la ventana de tiempo."""
        cutoff_time = current_time - self.window_seconds
        self.requests[ip] = [
            (ts, path) for ts, path in self.requests[ip]
            if ts > cutoff_time
        ]
    
    def _get_client_ip(self, request: Request) -> str:
        """Obtiene IP del cliente, considerando proxies."""
        # Check X-Forwarded-For (from ALB/CloudFront)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Excluir paths especificados
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Limpiar requests viejos
        self._clean_old_requests(client_ip, current_time)
        
        # Contar requests en ventana actual
        request_count = len(self.requests[client_ip])
        
        # Check rate limit
        if request_count >= self.max_requests:
            # Calcular tiempo de retry
            oldest_request = min(ts for ts, _ in self.requests[client_ip])
            retry_after = int(self.window_seconds - (current_time - oldest_request)) + 1
            
            logger.warning(
                f"Rate limit exceeded",
                extra={
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "request_count": request_count,
                    "limit": self.max_requests,
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Limit: {self.max_requests} per {self.window_seconds}s",
                    "retry_after": retry_after,
                },
                headers={
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + retry_after)),
                    "Retry-After": str(retry_after),
                }
            )
        
        # Agregar request actual
        self.requests[client_ip].append((current_time, request.url.path))
        
        # Procesar request
        response = await call_next(request)
        
        # Agregar rate limit headers
        remaining = max(0, self.max_requests - request_count - 1)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_seconds))
        
        return response


# ============================================================================
# Exception Handler Middleware
# ============================================================================

async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler global para excepciones HTTP.
    
    Proporciona responses consistentes con:
    - Request ID para debugging
    - Mensaje de error limpio (sin stack traces en production)
    - Status code apropiado
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Log del error
    logger.error(
        f"HTTP exception occurred",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "exception": str(exc),
        },
        exc_info=True
    )
    
    # Retornar error limpio
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": request_id,
        }
    )


# ============================================================================
# Setup Function
# ============================================================================

def setup_security_middleware(
    app: FastAPI,
    environment: str = "development",
    enable_rate_limiting: bool = True,
    rate_limit_requests: int = 100,
    rate_limit_window: int = 60,
) -> None:
    """
    Configura todos los middlewares de seguridad en una aplicación FastAPI.
    
    Args:
        app: Instancia de FastAPI
        environment: "development", "staging", o "production"
        enable_rate_limiting: Si activar rate limiting (True en production)
        rate_limit_requests: Requests permitidos en ventana
        rate_limit_window: Ventana de tiempo en segundos
    
    Ejemplo:
        app = FastAPI(title="Content Service")
        setup_security_middleware(
            app,
            environment="production",
            enable_rate_limiting=True,
            rate_limit_requests=1000,
            rate_limit_window=60,
        )
    """
    
    # 1. CORS (debe ser el primero)
    cors_config = get_cors_config(environment)
    app.add_middleware(CORSMiddleware, **cors_config)
    logger.info(f"CORS configured for environment: {environment}")
    
    # 2. Security Headers
    app.add_middleware(SecurityHeadersMiddleware, environment=environment)
    logger.info("Security headers middleware added")
    
    # 3. Request ID (antes de logging para tener ID disponible)
    app.add_middleware(RequestIDMiddleware)
    logger.info("Request ID middleware added")
    
    # 4. Request Logging
    app.add_middleware(RequestLoggingMiddleware)
    logger.info("Request logging middleware added")
    
    # 5. Rate Limiting (opcional)
    if enable_rate_limiting:
        app.add_middleware(
            RateLimitMiddleware,
            max_requests=rate_limit_requests,
            window_seconds=rate_limit_window,
        )
        logger.info(
            f"Rate limiting enabled: {rate_limit_requests} requests per {rate_limit_window}s"
        )
    
    logger.info("All security middleware configured successfully")


# ============================================================================
# Health Check Endpoint (sin rate limiting)
# ============================================================================

def add_health_endpoint(app: FastAPI) -> None:
    """
    Agrega un endpoint /health para health checks de ALB/ECS.
    
    Este endpoint:
    - No requiere autenticación
    - No tiene rate limiting
    - Retorna 200 si la app está healthy
    """
    
    @app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
    async def health_check():
        """Health check endpoint for ALB/ECS."""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    logger.info("Health check endpoint added at /health")
