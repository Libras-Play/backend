"""
Unit Tests for FastAPI Authentication Dependencies

Tests para dependencies.py:
- Token extraction from headers
- Current user retrieval
- Active user validation
- Group-based authorization (single group, multiple groups, all groups)
- Optional authentication
- Rate limiting
- Convenience functions (require_admin, require_moderator, etc.)
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

# Import dependencies to test
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.dependencies import (
    RateLimitExceeded,
    create_rate_limit_dependency,
    get_current_active_user,
    get_current_user,
    get_optional_user,
    get_token,
    get_token_claims,
    require_admin,
    require_groups,
    require_moderator,
    require_premium,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_request():
    """Mock FastAPI Request."""
    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "192.168.1.1"
    return request


@pytest.fixture
def valid_token():
    """Valid JWT token string."""
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.valid.token"


@pytest.fixture
def mock_credentials(valid_token):
    """Mock HTTPAuthorizationCredentials."""
    creds = Mock(spec=HTTPAuthorizationCredentials)
    creds.credentials = valid_token
    return creds


@pytest.fixture
def valid_claims():
    """Valid JWT claims."""
    return {
        "sub": "user-123456",
        "email": "test@example.com",
        "email_verified": True,
        "name": "Test User",
        "cognito:username": "testuser",
        "cognito:groups": ["users", "premium"],
        "aud": "test-client-id",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TestPool",
        "token_use": "id",
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
    }


@pytest.fixture
def admin_claims(valid_claims):
    """Claims for admin user."""
    claims = valid_claims.copy()
    claims["cognito:groups"] = ["users", "admin"]
    return claims


@pytest.fixture
def unverified_email_claims(valid_claims):
    """Claims for user with unverified email."""
    claims = valid_claims.copy()
    claims["email_verified"] = False
    return claims


# ============================================================================
# Test get_token
# ============================================================================

@pytest.mark.asyncio
async def test_get_token_success(mock_credentials):
    """Test extracting token from credentials."""
    token = await get_token(mock_credentials)
    
    assert token == mock_credentials.credentials


@pytest.mark.asyncio
async def test_get_token_none():
    """Test error when credentials are None."""
    with pytest.raises(HTTPException) as exc_info:
        await get_token(None)
    
    assert exc_info.value.status_code == 401
    assert "missing" in exc_info.value.detail.lower()


# ============================================================================
# Test get_current_user
# ============================================================================

@patch("shared.dependencies.verify_id_token")
@patch("shared.dependencies.extract_user_info")
@pytest.mark.asyncio
async def test_get_current_user_success(
    mock_extract, mock_verify, valid_token, valid_claims
):
    """Test getting current user with valid token."""
    # Setup mocks
    mock_verify.return_value = valid_claims
    mock_extract.return_value = {
        "user_id": "user-123456",
        "email": "test@example.com",
        "email_verified": True,
        "name": "Test User",
        "username": "testuser",
        "groups": ["users", "premium"],
    }
    
    # Get current user
    user = await get_current_user(valid_token)
    
    # Assertions
    assert user["user_id"] == "user-123456"
    assert user["email"] == "test@example.com"
    assert user["groups"] == ["users", "premium"]
    
    mock_verify.assert_called_once_with(valid_token)
    mock_extract.assert_called_once_with(valid_claims)


@patch("shared.dependencies.verify_id_token")
@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mock_verify, valid_token):
    """Test error with invalid token."""
    # Mock verify_id_token to raise HTTPException
    mock_verify.side_effect = HTTPException(
        status_code=401,
        detail="Invalid token"
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(valid_token)
    
    assert exc_info.value.status_code == 401


# ============================================================================
# Test get_token_claims
# ============================================================================

@patch("shared.dependencies.verify_id_token")
@pytest.mark.asyncio
async def test_get_token_claims(mock_verify, valid_token, valid_claims):
    """Test getting raw token claims."""
    mock_verify.return_value = valid_claims
    
    claims = await get_token_claims(valid_token)
    
    assert claims == valid_claims
    assert claims["sub"] == "user-123456"


# ============================================================================
# Test get_current_active_user
# ============================================================================

@pytest.mark.asyncio
async def test_get_current_active_user_verified():
    """Test getting active user with verified email."""
    user = {
        "user_id": "user-123",
        "email": "test@example.com",
        "email_verified": True,
    }
    
    active_user = await get_current_active_user(user)
    
    assert active_user == user


@pytest.mark.asyncio
async def test_get_current_active_user_unverified():
    """Test error when email is not verified."""
    user = {
        "user_id": "user-123",
        "email": "test@example.com",
        "email_verified": False,
    }
    
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(user)
    
    assert exc_info.value.status_code == 403
    assert "verify your email" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_current_active_user_no_email():
    """Test error when email is missing."""
    user = {
        "user_id": "user-123",
        "email_verified": False,
    }
    
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(user)
    
    assert exc_info.value.status_code == 403


# ============================================================================
# Test require_groups
# ============================================================================

@pytest.mark.asyncio
async def test_require_groups_single_group_present():
    """Test requiring single group when user has it."""
    user = {
        "user_id": "user-123",
        "groups": ["users", "premium"],
    }
    
    # Create dependency for "users" group
    dependency = require_groups(["users"])
    result = await dependency(user)
    
    assert result == user


@pytest.mark.asyncio
async def test_require_groups_single_group_absent():
    """Test requiring single group when user doesn't have it."""
    user = {
        "user_id": "user-123",
        "groups": ["users"],
    }
    
    dependency = require_groups(["admin"])
    
    with pytest.raises(HTTPException) as exc_info:
        await dependency(user)
    
    assert exc_info.value.status_code == 403
    assert "admin" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_require_groups_multiple_any():
    """Test requiring any of multiple groups."""
    user = {
        "user_id": "user-123",
        "groups": ["users", "premium"],
    }
    
    # User needs to be in "admin" OR "premium" (has premium)
    dependency = require_groups(["admin", "premium"], require_all=False)
    result = await dependency(user)
    
    assert result == user


@pytest.mark.asyncio
async def test_require_groups_multiple_any_none_present():
    """Test requiring any of multiple groups when user has none."""
    user = {
        "user_id": "user-123",
        "groups": ["users"],
    }
    
    dependency = require_groups(["admin", "moderator"], require_all=False)
    
    with pytest.raises(HTTPException) as exc_info:
        await dependency(user)
    
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_groups_multiple_all():
    """Test requiring all of multiple groups."""
    user = {
        "user_id": "user-123",
        "groups": ["users", "premium", "beta"],
    }
    
    # User needs to be in "users" AND "premium" (has both)
    dependency = require_groups(["users", "premium"], require_all=True)
    result = await dependency(user)
    
    assert result == user


@pytest.mark.asyncio
async def test_require_groups_multiple_all_missing_one():
    """Test requiring all groups when user is missing one."""
    user = {
        "user_id": "user-123",
        "groups": ["users", "premium"],
    }
    
    # User needs "users" AND "premium" AND "admin" (missing admin)
    dependency = require_groups(["users", "premium", "admin"], require_all=True)
    
    with pytest.raises(HTTPException) as exc_info:
        await dependency(user)
    
    assert exc_info.value.status_code == 403
    assert "admin" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_require_groups_no_groups_field():
    """Test requiring groups when user has no groups field."""
    user = {
        "user_id": "user-123",
    }
    
    dependency = require_groups(["users"])
    
    with pytest.raises(HTTPException) as exc_info:
        await dependency(user)
    
    assert exc_info.value.status_code == 403


# ============================================================================
# Test Convenience Functions
# ============================================================================

@pytest.mark.asyncio
async def test_require_admin():
    """Test require_admin convenience function."""
    admin_user = {"user_id": "admin-123", "groups": ["users", "admin"]}
    regular_user = {"user_id": "user-123", "groups": ["users"]}
    
    # Admin should pass
    dependency = require_admin()
    result = await dependency(admin_user)
    assert result == admin_user
    
    # Regular user should fail
    with pytest.raises(HTTPException) as exc_info:
        await dependency(regular_user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_moderator():
    """Test require_moderator convenience function."""
    moderator_user = {"user_id": "mod-123", "groups": ["users", "moderator"]}
    regular_user = {"user_id": "user-123", "groups": ["users"]}
    
    dependency = require_moderator()
    result = await dependency(moderator_user)
    assert result == moderator_user
    
    with pytest.raises(HTTPException) as exc_info:
        await dependency(regular_user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_premium():
    """Test require_premium convenience function."""
    premium_user = {"user_id": "premium-123", "groups": ["users", "premium"]}
    regular_user = {"user_id": "user-123", "groups": ["users"]}
    
    dependency = require_premium()
    result = await dependency(premium_user)
    assert result == premium_user
    
    with pytest.raises(HTTPException) as exc_info:
        await dependency(regular_user)
    assert exc_info.value.status_code == 403


# ============================================================================
# Test get_optional_user
# ============================================================================

@patch("shared.dependencies.verify_id_token")
@patch("shared.dependencies.extract_user_info")
@pytest.mark.asyncio
async def test_get_optional_user_authenticated(
    mock_extract, mock_verify, valid_token
):
    """Test optional auth with authenticated user."""
    mock_verify.return_value = {"sub": "user-123"}
    mock_extract.return_value = {"user_id": "user-123"}
    
    user = await get_optional_user(valid_token)
    
    assert user is not None
    assert user["user_id"] == "user-123"


@patch("shared.dependencies.verify_id_token")
@pytest.mark.asyncio
async def test_get_optional_user_unauthenticated(mock_verify):
    """Test optional auth with no token."""
    user = await get_optional_user(None)
    
    assert user is None
    mock_verify.assert_not_called()


@patch("shared.dependencies.verify_id_token")
@pytest.mark.asyncio
async def test_get_optional_user_invalid_token(mock_verify, valid_token):
    """Test optional auth with invalid token."""
    mock_verify.side_effect = HTTPException(status_code=401, detail="Invalid")
    
    user = await get_optional_user(valid_token)
    
    # Should return None instead of raising exception
    assert user is None


# ============================================================================
# Test Rate Limiting
# ============================================================================

@pytest.mark.asyncio
async def test_rate_limit_under_limit(mock_request):
    """Test rate limiting when under the limit."""
    # Create rate limiter: 5 requests per 60 seconds
    rate_limiter = create_rate_limit_dependency(max_requests=5, window_seconds=60)
    
    # Make 4 requests (under limit)
    for i in range(4):
        await rate_limiter(mock_request)
    
    # Should not raise exception


@pytest.mark.asyncio
async def test_rate_limit_at_limit(mock_request):
    """Test rate limiting at exactly the limit."""
    rate_limiter = create_rate_limit_dependency(max_requests=3, window_seconds=60)
    
    # Make exactly 3 requests
    for i in range(3):
        await rate_limiter(mock_request)
    
    # 4th request should fail
    with pytest.raises(RateLimitExceeded) as exc_info:
        await rate_limiter(mock_request)
    
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_different_ips():
    """Test that rate limiting is per-IP."""
    rate_limiter = create_rate_limit_dependency(max_requests=2, window_seconds=60)
    
    # Request from IP 1
    request1 = Mock(spec=Request)
    request1.client = Mock()
    request1.client.host = "192.168.1.1"
    
    # Request from IP 2
    request2 = Mock(spec=Request)
    request2.client = Mock()
    request2.client.host = "192.168.1.2"
    
    # Each IP should have its own limit
    await rate_limiter(request1)
    await rate_limiter(request1)  # IP1: 2 requests (at limit)
    
    await rate_limiter(request2)
    await rate_limiter(request2)  # IP2: 2 requests (at limit)
    
    # Both IPs should now be rate limited
    with pytest.raises(RateLimitExceeded):
        await rate_limiter(request1)
    
    with pytest.raises(RateLimitExceeded):
        await rate_limiter(request2)


@pytest.mark.asyncio
async def test_rate_limit_window_expiration(mock_request):
    """Test that rate limit window expires correctly."""
    # Very short window for testing
    rate_limiter = create_rate_limit_dependency(max_requests=2, window_seconds=1)
    
    # Make 2 requests
    await rate_limiter(mock_request)
    await rate_limiter(mock_request)
    
    # 3rd request should fail
    with pytest.raises(RateLimitExceeded):
        await rate_limiter(mock_request)
    
    # Wait for window to expire
    import asyncio
    await asyncio.sleep(1.1)
    
    # Should be able to make requests again
    await rate_limiter(mock_request)


# ============================================================================
# Test RateLimitExceeded Exception
# ============================================================================

def test_rate_limit_exceeded_exception():
    """Test RateLimitExceeded exception creation."""
    exc = RateLimitExceeded(retry_after=60)
    
    assert exc.status_code == 429
    assert "retry" in exc.detail.lower()


# ============================================================================
# Integration Tests
# ============================================================================

@patch("shared.dependencies.verify_id_token")
@patch("shared.dependencies.extract_user_info")
@pytest.mark.asyncio
async def test_full_auth_flow_admin_endpoint(mock_extract, mock_verify):
    """Test complete auth flow for admin-only endpoint."""
    # Admin token
    admin_token = "admin.jwt.token"
    mock_verify.return_value = {
        "sub": "admin-123",
        "cognito:groups": ["users", "admin"],
    }
    mock_extract.return_value = {
        "user_id": "admin-123",
        "email": "admin@example.com",
        "groups": ["users", "admin"],
    }
    
    # Get current user
    user = await get_current_user(admin_token)
    
    # Verify is admin
    admin_dependency = require_admin()
    result = await admin_dependency(user)
    
    assert result["user_id"] == "admin-123"


@patch("shared.dependencies.verify_id_token")
@patch("shared.dependencies.extract_user_info")
@pytest.mark.asyncio
async def test_full_auth_flow_premium_content(mock_extract, mock_verify):
    """Test auth flow for premium content access."""
    # Premium user token
    token = "premium.jwt.token"
    mock_verify.return_value = {
        "sub": "user-123",
        "email_verified": True,
        "cognito:groups": ["users", "premium"],
    }
    mock_extract.return_value = {
        "user_id": "user-123",
        "email": "premium@example.com",
        "email_verified": True,
        "groups": ["users", "premium"],
    }
    
    # Get current user
    user = await get_current_user(token)
    
    # Verify email is active
    active_user = await get_current_active_user(user)
    
    # Verify has premium access
    premium_dependency = require_premium()
    result = await premium_dependency(active_user)
    
    assert result["user_id"] == "user-123"
    assert "premium" in result["groups"]


@patch("shared.dependencies.verify_id_token")
@patch("shared.dependencies.extract_user_info")
@pytest.mark.asyncio
async def test_multi_role_authorization(mock_extract, mock_verify):
    """Test user with multiple roles accessing different endpoints."""
    token = "multi-role.jwt.token"
    mock_verify.return_value = {
        "sub": "user-123",
        "email_verified": True,
        "cognito:groups": ["users", "moderator", "premium"],
    }
    mock_extract.return_value = {
        "user_id": "user-123",
        "email_verified": True,
        "groups": ["users", "moderator", "premium"],
    }
    
    user = await get_current_user(token)
    
    # Should pass moderator check
    mod_dep = require_moderator()
    await mod_dep(user)
    
    # Should pass premium check
    premium_dep = require_premium()
    await premium_dep(user)
    
    # Should fail admin check
    admin_dep = require_admin()
    with pytest.raises(HTTPException) as exc_info:
        await admin_dep(user)
    assert exc_info.value.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
