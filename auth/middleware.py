"""
Authentication middleware for FastAPI application.
Handles JWT token validation and user context.
"""

from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from .auth_manager import AuthenticationManager
from .models import User, UserRole
from .security import JWTManager
from logger import logger


# Security scheme for FastAPI
security = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """Authentication middleware for request handling."""
    
    def __init__(self):
        self.auth_manager = AuthenticationManager()
        self.jwt_manager = JWTManager()
    
    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = None
    ) -> Optional[User]:
        """Get current authenticated user from request."""
        if not credentials:
            return None
        
        try:
            user = await self.auth_manager.get_user_by_token(session, credentials.credentials)
            return user
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return None
    
    async def require_authentication(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = None
    ) -> User:
        """Require valid authentication, raise 401 if not authenticated."""
        user = await self.get_current_user(credentials, session)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user
    
    async def require_role(
        self,
        required_roles: list[UserRole],
        user: User = Depends(require_authentication)
    ) -> User:
        """Require specific user role."""
        if UserRole(user.role) not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges"
            )
        
        return user
    
    async def require_admin(
        self,
        user: User = Depends(require_authentication)
    ) -> User:
        """Require admin role."""
        if user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        return user
    
    async def require_moderator_or_admin(
        self,
        user: User = Depends(require_authentication)
    ) -> User:
        """Require moderator or admin role."""
        if user.role not in [UserRole.MODERATOR.value, UserRole.ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Moderator or admin privileges required"
            )
        
        return user


# Global middleware instance
auth_middleware = AuthMiddleware()

# Dependency functions for FastAPI
get_current_user = auth_middleware.get_current_user
require_authentication = auth_middleware.require_authentication
require_admin = auth_middleware.require_admin
require_moderator_or_admin = auth_middleware.require_moderator_or_admin


def require_roles(*roles: UserRole):
    """Decorator factory for requiring specific roles."""
    async def role_dependency(user: User = Depends(require_authentication)):
        if UserRole(user.role) not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join([role.value for role in roles])}"
            )
        return user
    
    return role_dependency


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self.requests = {}  # In production, use Redis
    
    def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """Check if request is within rate limit."""
        import time
        
        current_time = time.time()
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if current_time - req_time < window_seconds
        ]
        
        # Check limit
        if len(self.requests[key]) >= max_requests:
            return False
        
        # Add current request
        self.requests[key].append(current_time)
        return True


# Global rate limiter
rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    # Check for forwarded headers first
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client IP
    if hasattr(request, "client") and request.client:
        return request.client.host
    
    return "unknown"


def create_rate_limit_dependency(
    max_requests: int = 60,
    window_seconds: int = 60,
    key_func = None
):
    """Create rate limiting dependency."""
    
    def rate_limit_dependency(request: Request):
        if key_func:
            key = key_func(request)
        else:
            key = get_client_ip(request)
        
        if not rate_limiter.check_rate_limit(key, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        return True
    
    return rate_limit_dependency


# Common rate limiting dependencies
login_rate_limit = create_rate_limit_dependency(
    max_requests=5,
    window_seconds=300  # 5 attempts per 5 minutes
)

registration_rate_limit = create_rate_limit_dependency(
    max_requests=3,
    window_seconds=3600  # 3 registrations per hour
)

api_rate_limit = create_rate_limit_dependency(
    max_requests=100,
    window_seconds=60  # 100 requests per minute
)


async def extract_user_context(request: Request) -> Dict[str, Any]:
    """Extract user context from request for logging."""
    context = {
        "ip": get_client_ip(request),
        "user_agent": request.headers.get("User-Agent", ""),
        "method": request.method,
        "path": str(request.url.path),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Try to get user from token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = JWTManager.verify_token(token, "access")
        if payload:
            context.update({
                "user_id": payload.get("user_id"),
                "username": payload.get("sub"),
                "user_role": payload.get("role")
            })
    
    return context