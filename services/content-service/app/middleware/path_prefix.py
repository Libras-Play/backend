"""
Middleware to handle ALB path prefix routing.

Since AWS ALB doesn't support path rewriting, we need to handle
the path prefix (/content, /users, /ml) in the application.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class PathPrefixMiddleware(BaseHTTPMiddleware):
    """
    Middleware that strips a path prefix from incoming requests.
    
    This allows the app to be mounted behind an ALB with path-based routing.
    For example, if ALB forwards /content/* to this service, this middleware
    will strip /content so the app sees /health instead of /content/health.
    """
    
    def __init__(self, app, prefix: str):
        super().__init__(app)
        self.prefix = prefix.rstrip("/")
    
    async def dispatch(self, request: Request, call_next):
        # Strip prefix from path
        if request.url.path.startswith(self.prefix):
            # Create a new scope with the stripped path
            scope = request.scope
            original_path = scope["path"]
            stripped_path = original_path[len(self.prefix):]
            if not stripped_path:
                stripped_path = "/"
            
            scope["path"] = stripped_path
            
            # Update raw_path as well (used by some frameworks)
            if "raw_path" in scope:
                scope["raw_path"] = stripped_path.encode("utf-8")
        
        response = await call_next(request)
        return response
