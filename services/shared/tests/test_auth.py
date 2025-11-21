"""
Unit Tests for JWT Authentication Module

Tests para auth.py:
- Configuración de Cognito
- Validación de JWT tokens
- Verificación de ID tokens vs Access tokens
- Manejo de errores (token expirado, audience inválida, etc.)
- Extracción de user info
- Validación de grupos
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import jwt
import pytest
from fastapi import HTTPException
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidTokenError,
)

# Import functions to test
import sys
from pathlib import Path

# Add parent directory to path to import shared modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.auth import (
    CognitoConfig,
    TokenPayload,
    check_user_in_group,
    extract_user_info,
    get_cognito_config,
    get_jwk_client,
    require_group,
    verify_access_token,
    verify_id_token,
    verify_jwt,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_cognito_config():
    """Mock Cognito configuration."""
    return CognitoConfig(
        region="us-east-1",
        user_pool_id="us-east-1_TestPool",
        app_client_id="test-client-id-123456"
    )


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables."""
    monkeypatch.setenv("AWS_COGNITO_REGION", "us-east-1")
    monkeypatch.setenv("AWS_COGNITO_USER_POOL_ID", "us-east-1_TestPool")
    monkeypatch.setenv("AWS_COGNITO_APP_CLIENT_ID", "test-client-id-123456")


@pytest.fixture
def valid_id_token_claims():
    """Valid ID token claims."""
    return {
        "sub": "user-123456",
        "email": "test@example.com",
        "email_verified": True,
        "name": "Test User",
        "cognito:username": "testuser",
        "cognito:groups": ["users", "premium"],
        "aud": "test-client-id-123456",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TestPool",
        "token_use": "id",
        "auth_time": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
    }


@pytest.fixture
def valid_access_token_claims():
    """Valid Access token claims."""
    return {
        "sub": "user-123456",
        "client_id": "test-client-id-123456",
        "username": "testuser",
        "scope": "openid profile email",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TestPool",
        "token_use": "access",
        "auth_time": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
    }


@pytest.fixture
def expired_token_claims(valid_id_token_claims):
    """Expired token claims."""
    claims = valid_id_token_claims.copy()
    claims["exp"] = int((datetime.utcnow() - timedelta(hours=1)).timestamp())
    return claims


@pytest.fixture
def invalid_audience_claims(valid_id_token_claims):
    """Claims with invalid audience."""
    claims = valid_id_token_claims.copy()
    claims["aud"] = "wrong-client-id"
    return claims


@pytest.fixture
def invalid_issuer_claims(valid_id_token_claims):
    """Claims with invalid issuer."""
    claims = valid_id_token_claims.copy()
    claims["iss"] = "https://evil.com/fake-pool"
    return claims


# ============================================================================
# Test CognitoConfig
# ============================================================================

def test_cognito_config_creation(mock_cognito_config):
    """Test CognitoConfig instance creation."""
    config = mock_cognito_config
    
    assert config.region == "us-east-1"
    assert config.user_pool_id == "us-east-1_TestPool"
    assert config.app_client_id == "test-client-id-123456"


def test_cognito_config_issuer_property(mock_cognito_config):
    """Test issuer URL property."""
    config = mock_cognito_config
    expected_issuer = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TestPool"
    
    assert config.issuer == expected_issuer


def test_cognito_config_jwks_url_property(mock_cognito_config):
    """Test JWKS URL property."""
    config = mock_cognito_config
    expected_jwks_url = (
        "https://cognito-idp.us-east-1.amazonaws.com/"
        "us-east-1_TestPool/.well-known/jwks.json"
    )
    
    assert config.jwks_url == expected_jwks_url


# ============================================================================
# Test get_cognito_config
# ============================================================================

def test_get_cognito_config_with_env_vars(mock_env_vars):
    """Test getting Cognito config from environment variables."""
    config = get_cognito_config()
    
    assert config.region == "us-east-1"
    assert config.user_pool_id == "us-east-1_TestPool"
    assert config.app_client_id == "test-client-id-123456"


def test_get_cognito_config_missing_env_vars(monkeypatch):
    """Test error when environment variables are missing."""
    # Remove all Cognito env vars
    monkeypatch.delenv("AWS_COGNITO_REGION", raising=False)
    monkeypatch.delenv("AWS_COGNITO_USER_POOL_ID", raising=False)
    monkeypatch.delenv("AWS_COGNITO_APP_CLIENT_ID", raising=False)
    
    # Clear cache
    get_cognito_config.cache_clear()
    
    with pytest.raises(ValueError, match="AWS_COGNITO_REGION environment variable not set"):
        get_cognito_config()


# ============================================================================
# Test verify_jwt
# ============================================================================

@patch("shared.auth.get_jwk_client")
@patch("shared.auth.jwt.decode")
def test_verify_jwt_valid_id_token(
    mock_decode, mock_jwk_client, mock_env_vars, valid_id_token_claims
):
    """Test verifying a valid ID token."""
    # Mock JWK client
    mock_signing_key = Mock()
    mock_signing_key.key = "test-key"
    mock_jwk_client.return_value.get_signing_key_from_jwt.return_value = mock_signing_key
    
    # Mock jwt.decode to return valid claims
    mock_decode.return_value = valid_id_token_claims
    
    # Verify token
    claims = verify_jwt("fake.jwt.token", token_use="id")
    
    # Assertions
    assert claims["sub"] == "user-123456"
    assert claims["email"] == "test@example.com"
    assert claims["token_use"] == "id"
    
    # Verify jwt.decode was called with correct parameters
    mock_decode.assert_called_once()
    call_kwargs = mock_decode.call_args[1]
    assert call_kwargs["algorithms"] == ["RS256"]
    assert call_kwargs["audience"] == "test-client-id-123456"
    assert call_kwargs["issuer"] == "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TestPool"


@patch("shared.auth.get_jwk_client")
@patch("shared.auth.jwt.decode")
def test_verify_jwt_expired_token(mock_decode, mock_jwk_client, mock_env_vars):
    """Test verifying an expired token."""
    # Mock jwt.decode to raise ExpiredSignatureError
    mock_decode.side_effect = ExpiredSignatureError("Token has expired")
    
    # Should raise HTTPException with 401
    with pytest.raises(HTTPException) as exc_info:
        verify_jwt("expired.jwt.token", token_use="id")
    
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


@patch("shared.auth.get_jwk_client")
@patch("shared.auth.jwt.decode")
def test_verify_jwt_invalid_audience(mock_decode, mock_jwk_client, mock_env_vars):
    """Test verifying token with invalid audience."""
    mock_decode.side_effect = InvalidAudienceError("Invalid audience")
    
    with pytest.raises(HTTPException) as exc_info:
        verify_jwt("invalid.jwt.token", token_use="id")
    
    assert exc_info.value.status_code == 401
    assert "audience" in exc_info.value.detail.lower()


@patch("shared.auth.get_jwk_client")
@patch("shared.auth.jwt.decode")
def test_verify_jwt_invalid_issuer(mock_decode, mock_jwk_client, mock_env_vars):
    """Test verifying token with invalid issuer."""
    mock_decode.side_effect = InvalidIssuerError("Invalid issuer")
    
    with pytest.raises(HTTPException) as exc_info:
        verify_jwt("invalid.jwt.token", token_use="id")
    
    assert exc_info.value.status_code == 401
    assert "issuer" in exc_info.value.detail.lower()


@patch("shared.auth.get_jwk_client")
@patch("shared.auth.jwt.decode")
def test_verify_jwt_wrong_token_use(
    mock_decode, mock_jwk_client, mock_env_vars, valid_id_token_claims
):
    """Test verifying token with wrong token_use claim."""
    claims = valid_id_token_claims.copy()
    claims["token_use"] = "access"  # Should be 'id'
    mock_decode.return_value = claims
    
    with pytest.raises(HTTPException) as exc_info:
        verify_jwt("wrong.token.use", token_use="id")
    
    assert exc_info.value.status_code == 401
    assert "token_use" in exc_info.value.detail.lower()


@patch("shared.auth.get_jwk_client")
@patch("shared.auth.jwt.decode")
def test_verify_jwt_skip_expiration(
    mock_decode, mock_jwk_client, mock_env_vars, expired_token_claims
):
    """Test verifying token with expiration check disabled."""
    mock_signing_key = Mock()
    mock_signing_key.key = "test-key"
    mock_jwk_client.return_value.get_signing_key_from_jwt.return_value = mock_signing_key
    
    # Return expired claims
    mock_decode.return_value = expired_token_claims
    
    # Should NOT raise error when verify_exp=False
    claims = verify_jwt("expired.jwt.token", token_use="id", verify_exp=False)
    
    assert claims["sub"] == "user-123456"


# ============================================================================
# Test verify_id_token and verify_access_token
# ============================================================================

@patch("shared.auth.verify_jwt")
def test_verify_id_token(mock_verify_jwt, valid_id_token_claims):
    """Test verify_id_token wrapper."""
    mock_verify_jwt.return_value = valid_id_token_claims
    
    claims = verify_id_token("fake.id.token")
    
    assert claims["token_use"] == "id"
    mock_verify_jwt.assert_called_once_with("fake.id.token", token_use="id", verify_exp=True)


@patch("shared.auth.verify_jwt")
def test_verify_access_token(mock_verify_jwt, valid_access_token_claims):
    """Test verify_access_token wrapper."""
    mock_verify_jwt.return_value = valid_access_token_claims
    
    claims = verify_access_token("fake.access.token")
    
    assert claims["token_use"] == "access"
    mock_verify_jwt.assert_called_once_with("fake.access.token", token_use="access", verify_exp=True)


# ============================================================================
# Test extract_user_info
# ============================================================================

def test_extract_user_info_complete(valid_id_token_claims):
    """Test extracting user info from complete claims."""
    user_info = extract_user_info(valid_id_token_claims)
    
    assert user_info["user_id"] == "user-123456"
    assert user_info["email"] == "test@example.com"
    assert user_info["email_verified"] is True
    assert user_info["name"] == "Test User"
    assert user_info["username"] == "testuser"
    assert user_info["groups"] == ["users", "premium"]


def test_extract_user_info_minimal():
    """Test extracting user info from minimal claims."""
    minimal_claims = {
        "sub": "user-789",
        "cognito:username": "minimaluser",
    }
    
    user_info = extract_user_info(minimal_claims)
    
    assert user_info["user_id"] == "user-789"
    assert user_info["username"] == "minimaluser"
    assert user_info["email"] is None
    assert user_info["email_verified"] is False
    assert user_info["name"] is None
    assert user_info["groups"] == []


def test_extract_user_info_fallback_username():
    """Test username fallback to email."""
    claims = {
        "sub": "user-999",
        "email": "fallback@example.com",
    }
    
    user_info = extract_user_info(claims)
    
    assert user_info["username"] == "fallback@example.com"


# ============================================================================
# Test check_user_in_group
# ============================================================================

def test_check_user_in_group_present(valid_id_token_claims):
    """Test checking if user is in a group (positive case)."""
    assert check_user_in_group(valid_id_token_claims, "users") is True
    assert check_user_in_group(valid_id_token_claims, "premium") is True


def test_check_user_in_group_absent(valid_id_token_claims):
    """Test checking if user is in a group (negative case)."""
    assert check_user_in_group(valid_id_token_claims, "admin") is False
    assert check_user_in_group(valid_id_token_claims, "nonexistent") is False


def test_check_user_in_group_no_groups():
    """Test checking group when user has no groups."""
    claims = {"sub": "user-123"}
    
    assert check_user_in_group(claims, "users") is False


# ============================================================================
# Test require_group
# ============================================================================

def test_require_group_present(valid_id_token_claims):
    """Test requiring group when user is in group."""
    # Should not raise exception
    require_group(valid_id_token_claims, "users")
    require_group(valid_id_token_claims, "premium")


def test_require_group_absent(valid_id_token_claims):
    """Test requiring group when user is not in group."""
    with pytest.raises(HTTPException) as exc_info:
        require_group(valid_id_token_claims, "admin")
    
    assert exc_info.value.status_code == 403
    assert "admin" in exc_info.value.detail.lower()


def test_require_group_no_groups():
    """Test requiring group when user has no groups."""
    claims = {"sub": "user-123"}
    
    with pytest.raises(HTTPException) as exc_info:
        require_group(claims, "users")
    
    assert exc_info.value.status_code == 403


# ============================================================================
# Test Integration Scenarios
# ============================================================================

@patch("shared.auth.get_jwk_client")
@patch("shared.auth.jwt.decode")
def test_full_authentication_flow(
    mock_decode, mock_jwk_client, mock_env_vars, valid_id_token_claims
):
    """Test full authentication flow from token to user info."""
    # Setup mocks
    mock_signing_key = Mock()
    mock_signing_key.key = "test-key"
    mock_jwk_client.return_value.get_signing_key_from_jwt.return_value = mock_signing_key
    mock_decode.return_value = valid_id_token_claims
    
    # Verify token
    claims = verify_id_token("fake.jwt.token")
    
    # Extract user info
    user_info = extract_user_info(claims)
    
    # Check group membership
    is_premium = check_user_in_group(claims, "premium")
    
    # Assertions
    assert user_info["email"] == "test@example.com"
    assert is_premium is True


@patch("shared.auth.get_jwk_client")
@patch("shared.auth.jwt.decode")
def test_admin_authorization_flow(
    mock_decode, mock_jwk_client, mock_env_vars
):
    """Test authorization flow for admin-only endpoint."""
    # User WITH admin group
    admin_claims = {
        "sub": "admin-user",
        "email": "admin@example.com",
        "cognito:groups": ["users", "admin"],
        "aud": "test-client-id-123456",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TestPool",
        "token_use": "id",
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
    }
    
    mock_signing_key = Mock()
    mock_signing_key.key = "test-key"
    mock_jwk_client.return_value.get_signing_key_from_jwt.return_value = mock_signing_key
    mock_decode.return_value = admin_claims
    
    # Verify token
    claims = verify_id_token("admin.jwt.token")
    
    # Should NOT raise exception
    require_group(claims, "admin")
    
    # User WITHOUT admin group
    user_claims = admin_claims.copy()
    user_claims["cognito:groups"] = ["users"]
    mock_decode.return_value = user_claims
    
    claims = verify_id_token("user.jwt.token")
    
    # Should raise 403
    with pytest.raises(HTTPException) as exc_info:
        require_group(claims, "admin")
    
    assert exc_info.value.status_code == 403


# ============================================================================
# Performance Tests
# ============================================================================

@patch("shared.auth.get_jwk_client")
def test_jwk_client_caching(mock_jwk_client, mock_env_vars):
    """Test that JWK client is cached."""
    # Clear cache
    get_jwk_client.cache_clear()
    
    # First call
    client1 = get_jwk_client()
    
    # Second call (should use cache)
    client2 = get_jwk_client()
    
    # Should return same instance
    assert client1 is client2
    
    # JWK client constructor should be called only once
    assert mock_jwk_client.call_count == 1


def test_cognito_config_caching(mock_env_vars):
    """Test that Cognito config is cached."""
    # Clear cache
    get_cognito_config.cache_clear()
    
    # First call
    config1 = get_cognito_config()
    
    # Second call (should use cache)
    config2 = get_cognito_config()
    
    # Should return same instance
    assert config1 is config2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
