"""
FastAPI Authentication Dependencies

Provides reusable dependencies for authentication and authorization.
"""

from typing import Optional, List
from functools import wraps

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .auth import (
    verify_id_token,
    verify_access_token,
    extract_user_info,
    check_user_in_group,
    require_group,
)

# Security scheme for Swagger UI
security = HTTPBearer(
    scheme_name="JWT Bearer Token",
    description="Enter your Cognito JWT token (ID token or Access token)",
)


async def get_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Extract JWT token from Authorization header.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        str: JWT token
    """
    return credentials.credentials


async def get_current_user(
    token: str = Depends(get_token),
) -> dict:
    """
    Get current authenticated user from ID token.
    
    This dependency validates the JWT token and returns user information.
    Use this when you need user profile data (email, name, etc.).
    
    Args:
        token: JWT token from Authorization header
        
    Returns:
        dict: User information with keys:
            - user_id: Cognito user UUID
            - username: Cognito username
            - email: User email
            - email_verified: Email verification status
            - groups: List of Cognito groups
            - etc.
    
    Raises:
        HTTPException 401: If token is invalid or expired
        
    Example:
        @app.get("/api/users/me")
        async def get_me(user: dict = Depends(get_current_user)):
            return {"user_id": user["user_id"], "email": user["email"]}
    """
    claims = verify_id_token(token)
    return extract_user_info(claims)


async def get_token_claims(
    token: str = Depends(get_token),
    token_type: str = "id",
) -> dict:
    """
    Get raw JWT claims without processing.
    
    Use this when you need access to all JWT claims,
    not just user information.
    
    Args:
        token: JWT token from Authorization header
        token_type: "id" or "access"
        
    Returns:
        dict: Raw JWT claims
    """
    if token_type == "id":
        return verify_id_token(token)
    else:
        return verify_access_token(token)


async def get_current_active_user(
    user: dict = Depends(get_current_user),
) -> dict:
    """
    Get current active user (email verified).
    
    Args:
        user: User information from get_current_user
        
    Returns:
        dict: User information
        
    Raises:
        HTTPException 403: If email is not verified
    """
    if not user.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email.",
        )
    return user


def require_groups(required_groups: List[str], require_all: bool = False):
    """
    Dependency factory to require user to be in specific Cognito groups.
    
    Args:
        required_groups: List of group names
        require_all: If True, user must be in ALL groups.
                    If False, user must be in AT LEAST ONE group.
    
    Returns:
        Dependency function
        
    Example:
        # Require admin group
        @app.delete("/api/users/{user_id}")
        async def delete_user(
            user_id: str,
            user: dict = Depends(require_groups(["admins"]))
        ):
            return {"message": "User deleted"}
        
        # Require admin OR moderator
        @app.post("/api/posts/{post_id}/moderate")
        async def moderate_post(
            post_id: str,
            user: dict = Depends(require_groups(["admins", "moderators"]))
        ):
            return {"message": "Post moderated"}
        
        # Require BOTH admin AND moderator
        @app.post("/api/system/critical-action")
        async def critical_action(
            user: dict = Depends(require_groups(["admins", "moderators"], require_all=True))
        ):
            return {"message": "Critical action performed"}
    """
    async def dependency(
        token: str = Depends(get_token),
    ) -> dict:
        claims = verify_id_token(token)
        user_groups = claims.get("cognito:groups", [])
        
        if require_all:
            # User must be in ALL required groups
            missing_groups = [g for g in required_groups if g not in user_groups]
            if missing_groups:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User must be in all of these groups: {', '.join(required_groups)}. "
                           f"Missing: {', '.join(missing_groups)}",
                )
        else:
            # User must be in AT LEAST ONE required group
            if not any(g in user_groups for g in required_groups):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User must be in at least one of these groups: {', '.join(required_groups)}",
                )
        
        return extract_user_info(claims)
    
    return dependency


def require_admin():
    """
    Convenience dependency to require admin group.
    
    Example:
        @app.delete("/api/users/{user_id}")
        async def delete_user(
            user_id: str,
            admin: dict = Depends(require_admin())
        ):
            return {"message": "User deleted"}
    """
    return require_groups(["admins"])


def require_moderator():
    """
    Convenience dependency to require moderator group.
    """
    return require_groups(["moderators"])


def require_premium():
    """
    Convenience dependency to require premium user group.
    """
    return require_groups(["premium_users"])


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[dict]:
    """
    Get current user if token is provided, otherwise return None.
    
    Useful for endpoints that work for both authenticated and anonymous users,
    but provide different data/features based on authentication status.
    
    Args:
        credentials: Optional HTTP authorization credentials
        
    Returns:
        dict or None: User information if authenticated, None otherwise
        
    Example:
        @app.get("/api/posts")
        async def list_posts(user: Optional[dict] = Depends(get_optional_user)):
            if user:
                # Show personalized feed
                return {"posts": get_personalized_posts(user["user_id"])}
            else:
                # Show public posts only
                return {"posts": get_public_posts()}
    """
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        claims = verify_id_token(token)
        return extract_user_info(claims)
    except HTTPException:
        # Invalid token, treat as unauthenticated
        return None


# Rate limiting dependency (requires rate limit state)
class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )


def create_rate_limit_dependency(max_requests: int, window_seconds: int):
    """
    Create a rate limiting dependency.
    
    Note: This is a simple in-memory implementation.
    For production, use Redis or similar.
    
    Args:
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        
    Returns:
        Dependency function
        
    Example:
        # Allow 100 requests per minute
        rate_limit = create_rate_limit_dependency(100, 60)
        
        @app.get("/api/expensive-operation")
        async def expensive_op(
            _: None = Depends(rate_limit),
            user: dict = Depends(get_current_user)
        ):
            return perform_expensive_operation()
    """
    from collections import defaultdict
    from time import time
    
    # In-memory storage (use Redis in production)
    request_counts = defaultdict(list)
    
    async def dependency(
        user: dict = Depends(get_current_user),
    ):
        user_id = user["user_id"]
        now = time()
        
        # Clean old requests outside window
        request_counts[user_id] = [
            timestamp for timestamp in request_counts[user_id]
            if now - timestamp < window_seconds
        ]
        
        # Check if limit exceeded
        if len(request_counts[user_id]) >= max_requests:
            raise RateLimitExceeded(retry_after=window_seconds)
        
        # Record this request
        request_counts[user_id].append(now)
    
    return dependency


# Example usage in your API:
"""
from fastapi import FastAPI, Depends
from .dependencies import (
    get_current_user,
    get_current_active_user,
    get_optional_user,
    require_groups,
    require_admin,
)

app = FastAPI()

# Public endpoint
@app.get("/api/public")
async def public_endpoint():
    return {"message": "This is public"}

# Authenticated endpoint
@app.get("/api/users/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user

# Active user only (email verified)
@app.post("/api/posts")
async def create_post(
    post: PostCreate,
    user: dict = Depends(get_current_active_user)
):
    return create_post_for_user(user["user_id"], post)

# Admin only
@app.delete("/api/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: dict = Depends(require_admin())
):
    return {"message": f"User {user_id} deleted by admin {admin['user_id']}"}

# Admin or moderator
@app.post("/api/posts/{post_id}/moderate")
async def moderate_post(
    post_id: str,
    action: str,
    moderator: dict = Depends(require_groups(["admins", "moderators"]))
):
    return {"message": f"Post {post_id} moderated by {moderator['username']}"}

# Optional authentication
@app.get("/api/posts")
async def list_posts(
    user: Optional[dict] = Depends(get_optional_user)
):
    if user:
        return {"posts": get_personalized_posts(user["user_id"])}
    else:
        return {"posts": get_public_posts()}
"""
