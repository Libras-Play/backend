"""
Unit Tests for Security Middleware

Tests para middleware.py:
- CORS configuration por environment
- Security headers
- Request ID tracking
- Request logging con masking
- Rate limiting
- Exception handling
"""

import time
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

# Import middleware to test
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.middleware import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    add_health_endpoint,
    get_cors_config,
    http_exception_handler,
    setup_security_middleware,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def app():
    """Create a FastAPI app for testing."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    @app.get("/error")
    async def error_endpoint():
        raise Exception("Test error")
    
    return app


@pytest.fixture
def client(app):
    """Create TestClient."""
    return TestClient(app)


# ============================================================================
# Test CORS Configuration
# ============================================================================

def test_cors_config_production():
    """Test CORS config for production environment."""
    config = get_cors_config("production")
    
    assert "https://aplicacion-senas.com" in config["allow_origins"]
    assert "http://localhost:3000" not in config["allow_origins"]
    assert config["allow_credentials"] is True
    assert "GET" in config["allow_methods"]
    assert "POST" in config["allow_methods"]
    assert config["max_age"] == 600


def test_cors_config_staging():
    """Test CORS config for staging environment."""
    config = get_cors_config("staging")
    
    assert "https://staging.aplicacion-senas.com" in config["allow_origins"]
    assert config["allow_credentials"] is True
    assert "*" in config["allow_methods"] or "OPTIONS" in config["allow_methods"]


def test_cors_config_development():
    """Test CORS config for development environment."""
    config = get_cors_config("development")
    
    assert "http://localhost:3000" in config["allow_origins"]
    assert "http://127.0.0.1:3000" in config["allow_origins"]
    assert config["allow_methods"] == ["*"]
    assert config["allow_headers"] == ["*"]
    assert config["max_age"] == 3600


def test_cors_config_default():
    """Test CORS config defaults to development."""
    config = get_cors_config()
    
    assert "http://localhost:3000" in config["allow_origins"]


# ============================================================================
# Test Security Headers Middleware
# ============================================================================

def test_security_headers_production(app):
    """Test security headers in production mode."""
    app.add_middleware(SecurityHeadersMiddleware, environment="production")
    client = TestClient(app)
    
    response = client.get("/test")
    
    # Check HSTS (only in production)
    assert "Strict-Transport-Security" in response.headers
    assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
    
    # Check other security headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert "Content-Security-Policy" in response.headers
    assert "Referrer-Policy" in response.headers
    assert "Permissions-Policy" in response.headers


def test_security_headers_development(app):
    """Test security headers in development mode."""
    app.add_middleware(SecurityHeadersMiddleware, environment="development")
    client = TestClient(app)
    
    response = client.get("/test")
    
    # HSTS should NOT be present in development
    assert "Strict-Transport-Security" not in response.headers
    
    # Other headers should still be present
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_security_headers_csp():
    """Test Content Security Policy header."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, environment="production")
    
    @app.get("/test")
    async def test():
        return {"ok": True}
    
    client = TestClient(app)
    response = client.get("/test")
    
    csp = response.headers["Content-Security-Policy"]
    
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "base-uri 'self'" in csp


def test_security_headers_permissions_policy():
    """Test Permissions Policy header."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, environment="production")
    
    @app.get("/test")
    async def test():
        return {"ok": True}
    
    client = TestClient(app)
    response = client.get("/test")
    
    permissions = response.headers["Permissions-Policy"]
    
    assert "geolocation=()" in permissions
    assert "camera=(self)" in permissions  # Necesario para captura de señas
    assert "microphone=()" in permissions


def test_security_headers_server_removed():
    """Test that Server header is removed."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/test")
    async def test():
        return {"ok": True}
    
    client = TestClient(app)
    response = client.get("/test")
    
    # Server header should be removed
    assert "Server" not in response.headers or response.headers.get("Server") != "uvicorn"


# ============================================================================
# Test Request ID Middleware
# ============================================================================

def test_request_id_generated(app):
    """Test that Request ID is generated automatically."""
    app.add_middleware(RequestIDMiddleware)
    client = TestClient(app)
    
    response = client.get("/test")
    
    assert "X-Request-ID" in response.headers
    # Should be a UUID
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36  # UUID format
    assert request_id.count("-") == 4


def test_request_id_from_client(app):
    """Test that client-provided Request ID is preserved."""
    app.add_middleware(RequestIDMiddleware)
    client = TestClient(app)
    
    client_request_id = "client-provided-id-12345"
    response = client.get("/test", headers={"X-Request-ID": client_request_id})
    
    assert response.headers["X-Request-ID"] == client_request_id


def test_request_id_in_request_state(app):
    """Test that Request ID is available in request.state."""
    app.add_middleware(RequestIDMiddleware)
    
    request_id_from_handler = None
    
    @app.get("/check-state")
    async def check_state(request: Request):
        nonlocal request_id_from_handler
        request_id_from_handler = request.state.request_id
        return {"ok": True}
    
    client = TestClient(app)
    response = client.get("/check-state")
    
    assert request_id_from_handler is not None
    assert response.headers["X-Request-ID"] == request_id_from_handler


# ============================================================================
# Test Request Logging Middleware
# ============================================================================

@patch("shared.middleware.logger")
def test_request_logging_success(mock_logger, app):
    """Test logging of successful requests."""
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    client = TestClient(app)
    
    response = client.get("/test?param1=value1")
    
    # Should log request start
    assert mock_logger.info.call_count >= 2  # Start + Complete
    
    # Check log messages
    calls = [str(call) for call in mock_logger.info.call_args_list]
    assert any("started" in str(call).lower() for call in calls)
    assert any("completed" in str(call).lower() for call in calls)


@patch("shared.middleware.logger")
def test_request_logging_masks_sensitive_params(mock_logger, app):
    """Test that sensitive query params are masked."""
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    client = TestClient(app)
    
    # Request with sensitive params
    response = client.get("/test?password=secret123&user=john")
    
    # Check that password was masked
    calls = mock_logger.info.call_args_list
    for call in calls:
        if call.kwargs and "extra" in call.kwargs:
            extra = call.kwargs["extra"]
            if "query_params" in extra:
                assert extra["query_params"].get("password") == "***MASKED***"
                assert extra["query_params"].get("user") == "john"


@patch("shared.middleware.logger")
def test_request_logging_exception(mock_logger, app):
    """Test logging when request raises exception."""
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    client = TestClient(app)
    
    # This will raise an exception
    with pytest.raises(Exception):
        client.get("/error")
    
    # Should log error
    assert mock_logger.error.called
    
    # Check error message
    error_call = mock_logger.error.call_args
    assert "failed" in str(error_call).lower() or "exception" in str(error_call).lower()


# ============================================================================
# Test Rate Limiting Middleware
# ============================================================================

def test_rate_limit_under_limit(app):
    """Test requests under rate limit."""
    app.add_middleware(RateLimitMiddleware, max_requests=5, window_seconds=60)
    client = TestClient(app)
    
    # Make 4 requests (under limit of 5)
    for i in range(4):
        response = client.get("/test")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "5"


def test_rate_limit_exceeded(app):
    """Test rate limiting when limit is exceeded."""
    app.add_middleware(RateLimitMiddleware, max_requests=3, window_seconds=60)
    client = TestClient(app)
    
    # Make 3 requests (at limit)
    for i in range(3):
        response = client.get("/test")
        assert response.status_code == 200
    
    # 4th request should be rate limited
    response = client.get("/test")
    assert response.status_code == 429
    assert "X-RateLimit-Remaining" in response.headers
    assert response.headers["X-RateLimit-Remaining"] == "0"
    assert "Retry-After" in response.headers


def test_rate_limit_headers(app):
    """Test rate limit headers are present."""
    app.add_middleware(RateLimitMiddleware, max_requests=10, window_seconds=60)
    client = TestClient(app)
    
    response = client.get("/test")
    
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers
    
    assert response.headers["X-RateLimit-Limit"] == "10"
    assert int(response.headers["X-RateLimit-Remaining"]) == 9  # 1 request made


def test_rate_limit_excluded_paths(app):
    """Test that excluded paths are not rate limited."""
    add_health_endpoint(app)
    app.add_middleware(RateLimitMiddleware, max_requests=2, window_seconds=60)
    client = TestClient(app)
    
    # /health should be excluded from rate limiting
    for i in range(10):
        response = client.get("/health")
        assert response.status_code == 200


def test_rate_limit_per_ip():
    """Test that rate limiting is per IP address."""
    app = FastAPI()
    
    @app.get("/test")
    async def test():
        return {"ok": True}
    
    app.add_middleware(RateLimitMiddleware, max_requests=2, window_seconds=60)
    
    client = TestClient(app)
    
    # Simulate different IPs using X-Forwarded-For
    for i in range(2):
        response = client.get("/test", headers={"X-Forwarded-For": "192.168.1.1"})
        assert response.status_code == 200
    
    # 3rd request from same IP should fail
    response = client.get("/test", headers={"X-Forwarded-For": "192.168.1.1"})
    assert response.status_code == 429
    
    # But request from different IP should succeed
    response = client.get("/test", headers={"X-Forwarded-For": "192.168.1.2"})
    assert response.status_code == 200


# ============================================================================
# Test Exception Handler
# ============================================================================

@pytest.mark.asyncio
async def test_http_exception_handler():
    """Test HTTP exception handler."""
    mock_request = Mock(spec=Request)
    mock_request.state = Mock()
    mock_request.state.request_id = "test-request-id"
    mock_request.method = "GET"
    mock_request.url = Mock()
    mock_request.url.path = "/test"
    
    exception = Exception("Test exception")
    
    response = await http_exception_handler(mock_request, exception)
    
    assert isinstance(response, JSONResponse)
    assert response.status_code == 500
    
    # Parse response body
    import json
    body = json.loads(response.body)
    assert body["error"] == "internal_server_error"
    assert body["request_id"] == "test-request-id"


# ============================================================================
# Test setup_security_middleware
# ============================================================================

def test_setup_security_middleware_production():
    """Test setting up all security middleware for production."""
    app = FastAPI()
    
    setup_security_middleware(
        app,
        environment="production",
        enable_rate_limiting=True,
        rate_limit_requests=1000,
        rate_limit_window=60,
    )
    
    # App should have middleware configured
    # We can't easily inspect middleware stack, but we can test it works
    client = TestClient(app)
    
    @app.get("/test")
    async def test():
        return {"ok": True}
    
    response = client.get("/test")
    
    # Should have security headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Request-ID" in response.headers
    assert "X-RateLimit-Limit" in response.headers


def test_setup_security_middleware_development():
    """Test setting up middleware for development."""
    app = FastAPI()
    
    setup_security_middleware(
        app,
        environment="development",
        enable_rate_limiting=False,
    )
    
    client = TestClient(app)
    
    @app.get("/test")
    async def test():
        return {"ok": True}
    
    response = client.get("/test")
    
    # Should have security headers
    assert "X-Content-Type-Options" in response.headers
    # Should NOT have HSTS in development
    assert "Strict-Transport-Security" not in response.headers


# ============================================================================
# Test Health Endpoint
# ============================================================================

def test_health_endpoint():
    """Test health check endpoint."""
    app = FastAPI()
    add_health_endpoint(app)
    
    client = TestClient(app)
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_health_endpoint_no_rate_limit():
    """Test that health endpoint bypasses rate limiting."""
    app = FastAPI()
    add_health_endpoint(app)
    app.add_middleware(RateLimitMiddleware, max_requests=2, window_seconds=60)
    
    client = TestClient(app)
    
    # Should be able to call health endpoint many times
    for i in range(10):
        response = client.get("/health")
        assert response.status_code == 200


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_middleware_stack():
    """Test complete middleware stack integration."""
    app = FastAPI()
    
    setup_security_middleware(
        app,
        environment="production",
        enable_rate_limiting=True,
        rate_limit_requests=10,
        rate_limit_window=60,
    )
    
    add_health_endpoint(app)
    
    @app.get("/api/test")
    async def test_endpoint(request: Request):
        return {
            "message": "success",
            "request_id": request.state.request_id,
        }
    
    client = TestClient(app)
    
    # Test normal request
    response = client.get("/api/test")
    assert response.status_code == 200
    
    # Check all expected headers
    assert "X-Request-ID" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-RateLimit-Limit" in response.headers
    assert "Strict-Transport-Security" in response.headers  # Production
    
    # Check response contains request_id
    data = response.json()
    assert "request_id" in data
    assert data["request_id"] == response.headers["X-Request-ID"]
    
    # Test health endpoint
    response = client.get("/health")
    assert response.status_code == 200


def test_middleware_order():
    """Test that middleware is applied in correct order."""
    app = FastAPI()
    
    execution_order = []
    
    # Custom middleware to track order
    @app.middleware("http")
    async def track_middleware(request: Request, call_next):
        execution_order.append("before")
        response = await call_next(request)
        execution_order.append("after")
        return response
    
    setup_security_middleware(app, environment="development")
    
    @app.get("/test")
    async def test():
        execution_order.append("handler")
        return {"ok": True}
    
    client = TestClient(app)
    response = client.get("/test")
    
    # Middleware should execute before and after handler
    assert "before" in execution_order
    assert "handler" in execution_order
    assert "after" in execution_order


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
