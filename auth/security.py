"""
Security utilities for user authentication system.
Password hashing, JWT token management, and security validation.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
import jwt
from config import config


class SecurityConfig:
    """Security configuration constants."""
    
    # JWT Configuration
    SECRET_KEY = config.get("JWT_SECRET_KEY", secrets.token_urlsafe(32))
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS = 30    # 30 days
    
    # Password Configuration
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL = True
    
    # Account Security
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    
    # Session Security
    MAX_SESSIONS_PER_USER = 5
    SESSION_TIMEOUT_MINUTES = 120  # 2 hours of inactivity


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordValidator:
    """Password strength validation."""
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, list[str]]:
        """
        Validate password strength.
        Returns (is_valid, list_of_errors).
        """
        errors = []
        
        # Length check
        if len(password) < SecurityConfig.MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {SecurityConfig.MIN_PASSWORD_LENGTH} characters long")
        
        if len(password) > SecurityConfig.MAX_PASSWORD_LENGTH:
            errors.append(f"Password must be no more than {SecurityConfig.MAX_PASSWORD_LENGTH} characters long")
        
        # Character requirements
        if SecurityConfig.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if SecurityConfig.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if SecurityConfig.REQUIRE_DIGITS and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if SecurityConfig.REQUIRE_SPECIAL and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        # Common password check (basic)
        common_passwords = [
            "password", "123456", "password123", "admin", "qwerty",
            "letmein", "welcome", "monkey", "dragon", "bitcoin"
        ]
        
        if password.lower() in common_passwords:
            errors.append("Password is too common, please choose a more secure password")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def calculate_password_strength(password: str) -> int:
        """
        Calculate password strength score (0-100).
        """
        score = 0
        
        # Length bonus
        score += min(len(password) * 2, 25)
        
        # Character variety bonus
        if any(c.isupper() for c in password):
            score += 15
        if any(c.islower() for c in password):
            score += 15
        if any(c.isdigit() for c in password):
            score += 15
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 20
        
        # Uniqueness bonus (no repeated patterns)
        unique_chars = len(set(password))
        if unique_chars >= len(password) * 0.8:
            score += 10
        
        return min(score, 100)


class PasswordManager:
    """Password hashing and verification."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False
    
    @staticmethod
    def needs_rehash(hashed_password: str) -> bool:
        """Check if password needs rehashing (due to algorithm updates)."""
        return pwd_context.needs_update(hashed_password)


class JWTManager:
    """JWT token creation and validation."""
    
    @staticmethod
    def create_access_token(
        subject: str, 
        user_id: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create JWT access token."""
        expire = datetime.utcnow() + timedelta(minutes=SecurityConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Create token ID for session tracking
        token_id = secrets.token_urlsafe(32)
        
        payload = {
            "sub": subject,          # Subject (username)
            "user_id": user_id,      # User ID
            "jti": token_id,         # JWT ID for session tracking
            "exp": expire,           # Expiration time
            "iat": datetime.utcnow(), # Issued at
            "type": "access"         # Token type
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, SecurityConfig.SECRET_KEY, algorithm=SecurityConfig.ALGORITHM)
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Create JWT refresh token."""
        expire = datetime.utcnow() + timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "token_id": secrets.token_urlsafe(32)
        }
        
        return jwt.encode(payload, SecurityConfig.SECRET_KEY, algorithm=SecurityConfig.ALGORITHM)
    
    @staticmethod
    def verify_token(token: str, expected_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token, 
                SecurityConfig.SECRET_KEY, 
                algorithms=[SecurityConfig.ALGORITHM]
            )
            
            # Check token type
            if payload.get("type") != expected_type:
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def get_token_expiry(token: str) -> Optional[datetime]:
        """Get token expiry time without full verification."""
        try:
            # Decode without verification to get expiry
            payload = jwt.decode(token, options={"verify_signature": False})
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp)
        except Exception:
            pass
        return None


class SecurityUtils:
    """General security utilities."""
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure random token."""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_verification_code(length: int = 6) -> str:
        """Generate numeric verification code."""
        return ''.join(secrets.choice('0123456789') for _ in range(length))
    
    @staticmethod
    def hash_email_for_lookup(email: str) -> str:
        """Create hash of email for privacy-preserving lookups."""
        return hashlib.sha256(email.lower().encode()).hexdigest()
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Basic email validation."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_username(username: str) -> tuple[bool, list[str]]:
        """Validate username format."""
        errors = []
        
        if len(username) < 3:
            errors.append("Username must be at least 3 characters long")
        
        if len(username) > 30:
            errors.append("Username must be no more than 30 characters long")
        
        if not username.isalnum() and '_' not in username:
            errors.append("Username can only contain letters, numbers, and underscores")
        
        if username.startswith('_') or username.endswith('_'):
            errors.append("Username cannot start or end with underscore")
        
        if '__' in username:
            errors.append("Username cannot contain consecutive underscores")
        
        # Reserved usernames
        reserved = [
            'admin', 'administrator', 'mod', 'moderator', 'support',
            'help', 'api', 'www', 'mail', 'ftp', 'root', 'system',
            'guest', 'anonymous', 'null', 'undefined', 'bot'
        ]
        
        if username.lower() in reserved:
            errors.append("Username is reserved, please choose another")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def is_ip_address_valid(ip: str) -> bool:
        """Validate IP address format."""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def rate_limit_key(ip: str, identifier: str = "") -> str:
        """Generate rate limiting key."""
        key_parts = [ip]
        if identifier:
            key_parts.append(identifier)
        return f"rate_limit:{'_'.join(key_parts)}"
    
    @staticmethod
    def sanitize_user_agent(user_agent: str) -> str:
        """Sanitize and truncate user agent string."""
        if not user_agent:
            return "Unknown"
        
        # Remove potentially dangerous characters
        safe_chars = ''.join(c for c in user_agent if c.isprintable())
        
        # Truncate to reasonable length
        return safe_chars[:500] if len(safe_chars) > 500 else safe_chars
    
    @staticmethod
    def extract_device_info(user_agent: str) -> str:
        """Extract basic device info from user agent."""
        if not user_agent:
            return "Unknown Device"
        
        user_agent_lower = user_agent.lower()
        
        # Operating System
        if 'windows' in user_agent_lower:
            os_info = "Windows"
        elif 'mac' in user_agent_lower:
            os_info = "macOS"
        elif 'linux' in user_agent_lower:
            os_info = "Linux"
        elif 'android' in user_agent_lower:
            os_info = "Android"
        elif 'ios' in user_agent_lower:
            os_info = "iOS"
        else:
            os_info = "Unknown OS"
        
        # Browser
        if 'chrome' in user_agent_lower:
            browser = "Chrome"
        elif 'firefox' in user_agent_lower:
            browser = "Firefox"
        elif 'safari' in user_agent_lower:
            browser = "Safari"
        elif 'edge' in user_agent_lower:
            browser = "Edge"
        else:
            browser = "Unknown Browser"
        
        return f"{browser} on {os_info}"


# Export main classes for easy import
__all__ = [
    "SecurityConfig",
    "PasswordValidator", 
    "PasswordManager",
    "JWTManager",
    "SecurityUtils"
]