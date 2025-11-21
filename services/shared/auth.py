"""
AWS Cognito JWT Authentication Module

This module provides JWT token validation for AWS Cognito User Pools.
Supports:
- JWKS (JSON Web Key Set) validation
- Token expiration validation
- Audience and issuer validation
- Claims extraction

Usage:
    from shared.auth import verify_jwt, get_current_user
    
    @app.get("/protected")
    async def protected_route(user: dict = Depends(get_current_user)):
        return {"user_id": user["sub"], "email": user["email"]}
"""

import os
import time
from typing import Dict, Optional
from functools import lru_cache
import logging

import jwt
from jwt import PyJWKClient
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidTokenError,
    InvalidAudienceError,
    InvalidIssuerError,
)
from fastapi import HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CognitoConfig(BaseModel):
    """AWS Cognito configuration"""
    region: str
    user_pool_id: str
    app_client_id: str
    
    @property
    def issuer(self) -> str:
        """Get Cognito issuer URL"""
        return f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
    
    @property
    def jwks_url(self) -> str:
        """Get JWKS URL for public keys"""
        return f"{self.issuer}/.well-known/jwks.json"


class TokenPayload(BaseModel):
    """JWT token payload model"""
    sub: str  # User ID (Cognito UUID)
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    phone_number: Optional[str] = None
    phone_number_verified: Optional[bool] = None
    name: Optional[str] = None
    cognito_username: str
    cognito_groups: Optional[list[str]] = None
    token_use: str  # "id" or "access"
    auth_time: int
    iat: int  # Issued at
    exp: int  # Expiration
    iss: str  # Issuer
    aud: Optional[str] = None  # Audience (only in ID tokens)
    client_id: Optional[str] = None  # Client ID (only in access tokens)


@lru_cache()
def get_cognito_config() -> CognitoConfig:
    """
    Get Cognito configuration from environment variables.
    Cached for performance.
    
    Environment variables required:
    - AWS_COGNITO_REGION: AWS region (e.g., us-east-1)
    - AWS_COGNITO_USER_POOL_ID: User Pool ID (e.g., us-east-1_XXXXXXXXX)
    - AWS_COGNITO_APP_CLIENT_ID: App Client ID
    
    Returns:
        CognitoConfig: Configuration object
        
    Raises:
        RuntimeError: If required environment variables are missing
    """
    region = os.getenv("AWS_COGNITO_REGION")
    user_pool_id = os.getenv("AWS_COGNITO_USER_POOL_ID")
    app_client_id = os.getenv("AWS_COGNITO_APP_CLIENT_ID")
    
    if not all([region, user_pool_id, app_client_id]):
        missing = []
        if not region:
            missing.append("AWS_COGNITO_REGION")
        if not user_pool_id:
            missing.append("AWS_COGNITO_USER_POOL_ID")
        if not app_client_id:
            missing.append("AWS_COGNITO_APP_CLIENT_ID")
        
        raise RuntimeError(
            f"Missing required Cognito environment variables: {', '.join(missing)}"
        )
    
    return CognitoConfig(
        region=region,
        user_pool_id=user_pool_id,
        app_client_id=app_client_id,
    )


@lru_cache()
def get_jwk_client() -> PyJWKClient:
    """
    Get PyJWKClient for fetching public keys from Cognito JWKS endpoint.
    Cached for performance (keys are cached by PyJWKClient).
    
    Returns:
        PyJWKClient: Client for fetching JWKS
    """
    config = get_cognito_config()
    return PyJWKClient(
        config.jwks_url,
        cache_keys=True,
        max_cached_keys=10,
        cache_jwk_set=True,
        lifespan=3600,  # Cache for 1 hour
    )


def verify_jwt(
    token: str,
    token_use: str = "id",
    verify_exp: bool = True,
) -> Dict:
    """
    Verify and decode a Cognito JWT token.
    
    This function:
    1. Downloads the JWKS (JSON Web Key Set) from Cognito
    2. Validates the token signature using the public key
    3. Validates token expiration
    4. Validates audience (for ID tokens) or client_id (for access tokens)
    5. Validates issuer
    6. Extracts and returns claims
    
    Args:
        token: JWT token string
        token_use: Expected token use - "id" or "access"
        verify_exp: Whether to verify token expiration (default: True)
        
    Returns:
        dict: Decoded token claims
        
    Raises:
        HTTPException: If token is invalid
        
    Example:
        >>> token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
        >>> claims = verify_jwt(token, token_use="id")
        >>> print(claims["sub"])  # User ID
        'a1b2c3d4-5678-90ab-cdef-1234567890ab'
    """
    config = get_cognito_config()
    
    try:
        # Get signing key from JWKS
        jwk_client = get_jwk_client()
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        
        # Decode and validate token
        decode_options = {
            "verify_signature": True,
            "verify_exp": verify_exp,
            "verify_iat": True,
            "verify_aud": token_use == "id",  # Only verify aud for ID tokens
        }
        
        # Build verification options
        verify_options = {
            "issuer": config.issuer,
        }
        
        # Add audience verification for ID tokens
        if token_use == "id":
            verify_options["audience"] = config.app_client_id
        
        # Decode JWT
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options=decode_options,
            **verify_options,
        )
        
        # Validate token_use claim
        if payload.get("token_use") != token_use:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token_use. Expected '{token_use}', got '{payload.get('token_use')}'",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # For access tokens, validate client_id
        if token_use == "access":
            if payload.get("client_id") != config.app_client_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid client_id in access token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Log successful validation
        logger.info(
            f"JWT validated successfully",
            extra={
                "user_id": payload.get("sub"),
                "token_use": token_use,
                "exp": payload.get("exp"),
            }
        )
        
        return payload
        
    except ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    except InvalidAudienceError:
        logger.warning("Invalid token audience")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    except InvalidIssuerError:
        logger.warning("Invalid token issuer")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    except InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    except Exception as e:
        logger.error(f"Unexpected error validating token: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token validation",
        )


def verify_access_token(token: str) -> Dict:
    """
    Verify an access token from Cognito.
    
    Access tokens are used for authorizing API calls.
    They contain scopes and groups but not user profile info.
    
    Args:
        token: Access token string
        
    Returns:
        dict: Decoded token claims
    """
    return verify_jwt(token, token_use="access")


def verify_id_token(token: str) -> Dict:
    """
    Verify an ID token from Cognito.
    
    ID tokens contain user profile information (email, name, etc.).
    Use this when you need user details.
    
    Args:
        token: ID token string
        
    Returns:
        dict: Decoded token claims with user info
    """
    return verify_jwt(token, token_use="id")


def extract_user_info(claims: Dict) -> Dict:
    """
    Extract common user information from token claims.
    
    Args:
        claims: Decoded JWT claims
        
    Returns:
        dict: User information
    """
    return {
        "user_id": claims.get("sub"),
        "username": claims.get("cognito:username") or claims.get("cognito_username"),
        "email": claims.get("email"),
        "email_verified": claims.get("email_verified", False),
        "phone_number": claims.get("phone_number"),
        "phone_number_verified": claims.get("phone_number_verified", False),
        "name": claims.get("name"),
        "groups": claims.get("cognito:groups", []),
        "auth_time": claims.get("auth_time"),
        "token_use": claims.get("token_use"),
    }


def check_user_in_group(claims: Dict, required_group: str) -> bool:
    """
    Check if user belongs to a specific Cognito group.
    
    Args:
        claims: Decoded JWT claims
        required_group: Group name to check
        
    Returns:
        bool: True if user is in the group
    """
    groups = claims.get("cognito:groups", [])
    return required_group in groups


def require_group(claims: Dict, required_group: str) -> None:
    """
    Require user to be in a specific Cognito group.
    
    Args:
        claims: Decoded JWT claims
        required_group: Required group name
        
    Raises:
        HTTPException: If user is not in the required group
    """
    if not check_user_in_group(claims, required_group):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User must be in '{required_group}' group",
        )


# Example usage in FastAPI routes:
"""
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict:
    '''Get current authenticated user from JWT token'''
    token = credentials.credentials
    claims = verify_id_token(token)
    return extract_user_info(claims)

async def get_current_admin_user(
    user: Dict = Depends(get_current_user)
) -> Dict:
    '''Require user to be an admin'''
    # Note: This requires claims, not user_info
    # So we need to re-verify or pass claims through
    raise NotImplementedError("Use require_group with claims")

# In your routes:
@app.get("/api/users/me")
async def get_me(user: Dict = Depends(get_current_user)):
    return user

@app.get("/api/admin/users")
async def admin_only(user: Dict = Depends(get_current_admin_user)):
    return {"message": "Admin access granted"}
"""
