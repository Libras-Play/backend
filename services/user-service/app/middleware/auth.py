"""
Authentication middleware for User Service

Validates JWT tokens from AWS Cognito and extracts user information.
"""
import jwt
import requests
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from functools import lru_cache

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


@lru_cache()
def get_cognito_public_keys() -> Dict[str, Any]:
    """
    Download and cache Cognito public keys (JWKS)
    
    Returns:
        Dictionary with public keys indexed by 'kid'
    """
    region = settings.AWS_REGION
    user_pool_id = settings.COGNITO_USER_POOL_ID
    
    keys_url = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json'
    
    try:
        response = requests.get(keys_url, timeout=10)
        response.raise_for_status()
        keys = response.json()['keys']
        
        # Index keys by 'kid' for fast lookup
        return {key['kid']: key for key in keys}
        
    except Exception as e:
        logger.error(f"Error downloading Cognito public keys: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Unable to validate authentication tokens"
        )


def verify_cognito_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a Cognito JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload with user claims
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        # Get the key ID from token header
        headers = jwt.get_unverified_header(token)
        kid = headers['kid']
        
        # Get the corresponding public key
        public_keys = get_cognito_public_keys()
        
        if kid not in public_keys:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: Unknown key ID"
            )
        
        key = public_keys[kid]
        
        # Convert JWK to PEM format
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
        
        # Verify and decode the token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            audience=settings.COGNITO_CLIENT_ID,
            options={'verify_exp': True}
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Authorization header with Bearer token
        
    Returns:
        Dict with user information from token:
        - sub: Cognito user ID (UUID)
        - email: User email
        - username: Username (from cognito:username claim)
        - email_verified: Boolean
        
    Raises:
        HTTPException: If authentication fails
        
    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"user_id": user["sub"]}
    """
    token = credentials.credentials
    payload = verify_cognito_token(token)
    
    return {
        "sub": payload.get("sub"),  # Cognito user ID
        "email": payload.get("email"),
        "username": payload.get("cognito:username", payload.get("email")),
        "email_verified": payload.get("email_verified", False),
        "token_use": payload.get("token_use"),  # 'access' or 'id'
    }


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security, auto_error=False)
) -> Optional[Dict[str, Any]]:
    """
    Optional authentication - returns None if no token provided
    
    Useful for endpoints that work both authenticated and unauthenticated
    
    Args:
        credentials: Optional HTTP Authorization header
        
    Returns:
        User dict if authenticated, None otherwise
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency to require admin role
    
    Args:
        user: Current authenticated user
        
    Returns:
        User dict if user is admin
        
    Raises:
        HTTPException: If user is not admin
        
    Usage:
        @app.delete("/admin/users/{user_id}")
        async def delete_user(user: dict = Depends(require_admin)):
            ...
    """
    # Check if user has admin role in cognito:groups
    groups = user.get("cognito:groups", [])
    
    if "admin" not in groups:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    return user
