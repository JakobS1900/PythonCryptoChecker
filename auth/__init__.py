"""
Authentication system for crypto gamification platform.
JWT-based authentication with session management.
"""

from .models import (
    User, UserSession, LoginAttempt, EmailVerificationToken,
    PasswordResetToken, UserPreferences, UserRole, UserStatus
)

from .security import (
    SecurityConfig, PasswordValidator, PasswordManager,
    JWTManager, SecurityUtils
)

from .auth_manager import (
    AuthenticationManager, AuthenticationError, AccountLockedException
)

from .middleware import (
    auth_middleware, get_current_user, require_authentication,
    require_admin, require_moderator_or_admin, require_roles,
    login_rate_limit, registration_rate_limit, api_rate_limit,
    get_client_ip, extract_user_context
)

__all__ = [
    # Models
    "User",
    "UserSession", 
    "LoginAttempt",
    "EmailVerificationToken",
    "PasswordResetToken",
    "UserPreferences",
    
    # Enums
    "UserRole",
    "UserStatus",
    
    # Security
    "SecurityConfig",
    "PasswordValidator",
    "PasswordManager", 
    "JWTManager",
    "SecurityUtils",
    
    # Authentication
    "AuthenticationManager",
    "AuthenticationError",
    "AccountLockedException",
    
    # Middleware
    "auth_middleware",
    "get_current_user",
    "require_authentication",
    "require_admin", 
    "require_moderator_or_admin",
    "require_roles",
    "login_rate_limit",
    "registration_rate_limit",
    "api_rate_limit",
    "get_client_ip",
    "extract_user_context"
]