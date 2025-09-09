"""
Authentication manager for user registration, login, and session management.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.orm import selectinload

from database.unified_models import (
    User, UserSession, UserRole, UserStatus
)
from .security import (
    PasswordManager, PasswordValidator, JWTManager, SecurityUtils, SecurityConfig
)
from fastapi import Depends
from fastapi.security import HTTPBearer
from database.database_manager import get_db_session
from logger import logger


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass


class AccountLockedException(AuthenticationError):
    """Exception raised when account is locked due to failed attempts."""
    pass


class AuthenticationManager:
    """Core authentication and user management system."""
    
    def __init__(self):
        self.password_manager = PasswordManager()
        self.password_validator = PasswordValidator()
        self.jwt_manager = JWTManager()
        self.security_utils = SecurityUtils()
    
    async def register_user(
        self,
        session: AsyncSession,
        username: str,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[User, str]:
        """
        Register new user account.
        Returns (User, verification_token).
        """
        # Validate input
        username_valid, username_errors = self.security_utils.validate_username(username)
        if not username_valid:
            raise AuthenticationError(f"Invalid username: {', '.join(username_errors)}")
        
        if not self.security_utils.validate_email(email):
            raise AuthenticationError("Invalid email format")
        
        password_valid, password_errors = self.password_validator.validate_password(password)
        if not password_valid:
            raise AuthenticationError(f"Invalid password: {', '.join(password_errors)}")
        
        # Check if username or email already exists
        existing_user = await session.execute(
            select(User).where(
                (User.username == username) | (User.email == email.lower())
            )
        )
        if existing_user.scalar_one_or_none():
            raise AuthenticationError("Username or email already exists")
        
        # Create user account
        hashed_password = self.password_manager.hash_password(password)
        
        user = User(
            username=username,
            email=email.lower(),
            hashed_password=hashed_password,
            display_name=display_name or username,
            role=UserRole.PLAYER.value,
            status=UserStatus.ACTIVE.value
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        # Create user preferences
        preferences = UserPreferences(user_id=user.id)
        session.add(preferences)
        
        # Initialize virtual wallet
        await self.virtual_economy.create_user_wallet(session, user.id)
        
        # Generate email verification token
        verification_token = self.security_utils.generate_secure_token()
        email_token = EmailVerificationToken(
            user_id=user.id,
            token=verification_token,
            email=email.lower(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        session.add(email_token)
        
        await session.commit()
        
        # Log successful registration
        logger.info(f"New user registered: {username} ({email}) from IP {ip_address}")
        
        return user, verification_token
    
    async def authenticate_user(
        self,
        session: AsyncSession,
        username_or_email: str,
        password: str,
        ip_address: str,
        user_agent: str = None
    ) -> Tuple[User, str, str]:
        """
        Authenticate user login.
        Returns (User, access_token, refresh_token).
        """
        # Check for rate limiting
        await self._check_login_rate_limit(session, ip_address, username_or_email)
        
        # Find user
        user = await self._find_user_by_credentials(session, username_or_email)
        
        # Log login attempt
        await self._log_login_attempt(session, user, username_or_email, ip_address, user_agent)
        
        if not user:
            await self._log_login_attempt(
                session, None, username_or_email, ip_address, user_agent,
                success=False, failure_reason="user_not_found"
            )
            raise AuthenticationError("Invalid credentials")
        
        # Check account status
        if user.status != UserStatus.ACTIVE.value:
            await self._log_login_attempt(
                session, user, username_or_email, ip_address, user_agent,
                success=False, failure_reason=f"account_{user.status.lower()}"
            )
            raise AuthenticationError(f"Account is {user.status.lower()}")
        
        # Verify password
        if not self.password_manager.verify_password(password, user.hashed_password):
            await self._log_login_attempt(
                session, user, username_or_email, ip_address, user_agent,
                success=False, failure_reason="invalid_password"
            )
            raise AuthenticationError("Invalid credentials")
        
        # Update last login
        user.last_login = datetime.utcnow()
        
        # Create session tokens
        access_token = self.jwt_manager.create_access_token(
            subject=user.username,
            user_id=user.id,
            additional_claims={
                "role": user.role,
                "level": user.current_level
            }
        )
        
        refresh_token = self.jwt_manager.create_refresh_token(user.id)
        
        # Create user session record
        await self._create_user_session(session, user.id, access_token, refresh_token, ip_address, user_agent)
        
        await session.commit()
        
        # Log successful login
        await self._log_login_attempt(
            session, user, username_or_email, ip_address, user_agent,
            success=True
        )
        
        logger.info(f"User logged in: {user.username} from IP {ip_address}")
        
        return user, access_token, refresh_token
    
    async def refresh_token(
        self,
        session: AsyncSession,
        refresh_token: str,
        ip_address: str
    ) -> Tuple[str, str]:
        """
        Refresh access token using refresh token.
        Returns (new_access_token, new_refresh_token).
        """
        # Verify refresh token
        payload = self.jwt_manager.verify_token(refresh_token, "refresh")
        if not payload:
            raise AuthenticationError("Invalid refresh token")
        
        user_id = payload.get("user_id")
        
        # Find and validate session
        session_record = await session.execute(
            select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.refresh_token == refresh_token,
                    UserSession.is_active == True
                )
            )
        )
        session_record = session_record.scalar_one_or_none()
        
        if not session_record or not session_record.is_valid():
            raise AuthenticationError("Invalid or expired session")
        
        # Get user
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar_one_or_none()
        
        if not user or user.status != UserStatus.ACTIVE.value:
            raise AuthenticationError("User account not active")
        
        # Create new tokens
        new_access_token = self.jwt_manager.create_access_token(
            subject=user.username,
            user_id=user.id,
            additional_claims={
                "role": user.role,
                "level": user.current_level
            }
        )
        
        new_refresh_token = self.jwt_manager.create_refresh_token(user.id)
        
        # Update session record
        session_record.refresh_token = new_refresh_token
        session_record.last_activity = datetime.utcnow()
        session_record.expires_at = datetime.utcnow() + timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS)
        
        await session.commit()
        
        logger.info(f"Token refreshed for user {user.username}")
        
        return new_access_token, new_refresh_token
    
    async def logout_user(
        self,
        session: AsyncSession,
        access_token: str
    ) -> bool:
        """Logout user by invalidating their session."""
        # Verify token
        payload = self.jwt_manager.verify_token(access_token, "access")
        if not payload:
            return False
        
        # Find and deactivate session
        jwt_id = payload.get("jti")
        if jwt_id:
            await session.execute(
                update(UserSession)
                .where(UserSession.jwt_token_id == jwt_id)
                .values(is_active=False)
            )
            await session.commit()
            
            logger.info(f"User logged out: {payload.get('sub')}")
            return True
        
        return False
    
    async def logout_all_sessions(
        self,
        session: AsyncSession,
        user_id: str
    ) -> int:
        """Logout user from all sessions."""
        result = await session.execute(
            update(UserSession)
            .where(and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            ))
            .values(is_active=False)
        )
        
        await session.commit()
        
        sessions_closed = result.rowcount
        logger.info(f"Logged out user from {sessions_closed} sessions: {user_id}")
        
        return sessions_closed
    
    async def verify_email(
        self,
        session: AsyncSession,
        token: str
    ) -> bool:
        """Verify user email with verification token."""
        # Find verification token
        token_record = await session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token == token
            )
        )
        token_record = token_record.scalar_one_or_none()
        
        if not token_record or not token_record.is_valid():
            raise AuthenticationError("Invalid or expired verification token")
        
        # Update user
        user = await session.execute(select(User).where(User.id == token_record.user_id))
        user = user.scalar_one_or_none()
        
        if not user:
            raise AuthenticationError("User not found")
        
        user.is_email_verified = True
        user.email_verified_at = datetime.utcnow()
        
        # Mark token as used
        token_record.used_at = datetime.utcnow()
        
        await session.commit()
        
        logger.info(f"Email verified for user: {user.username}")
        
        return True
    
    async def change_password(
        self,
        session: AsyncSession,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """Change user password."""
        # Get user
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar_one_or_none()
        
        if not user:
            raise AuthenticationError("User not found")
        
        # Verify current password
        if not self.password_manager.verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect")
        
        # Validate new password
        password_valid, password_errors = self.password_validator.validate_password(new_password)
        if not password_valid:
            raise AuthenticationError(f"Invalid new password: {', '.join(password_errors)}")
        
        # Update password
        user.hashed_password = self.password_manager.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        
        # Invalidate all sessions (force re-login)
        await self.logout_all_sessions(session, user_id)
        
        await session.commit()
        
        logger.info(f"Password changed for user: {user.username}")
        
        return True
    
    async def get_user_by_token(
        self,
        session: AsyncSession,
        access_token: str
    ) -> Optional[User]:
        """Get user from access token."""
        payload = self.jwt_manager.verify_token(access_token, "access")
        if not payload:
            return None
        
        user_id = payload.get("user_id")
        jwt_id = payload.get("jti")
        
        # Verify session is still active
        session_record = await session.execute(
            select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.jwt_token_id == jwt_id,
                    UserSession.is_active == True
                )
            )
        )
        session_record = session_record.scalar_one_or_none()
        
        if not session_record or not session_record.is_valid():
            return None
        
        # Update last activity
        session_record.last_activity = datetime.utcnow()
        await session.commit()
        
        # Get user with relationships
        result = await session.execute(
            select(User)
            .options(selectinload(User.wallet))
            .where(User.id == user_id)
        )
        
        return result.scalar_one_or_none()
    
    async def cleanup_expired_sessions(self, session: AsyncSession) -> int:
        """Clean up expired sessions and tokens."""
        now = datetime.utcnow()
        
        # Clean expired sessions
        session_result = await session.execute(
            delete(UserSession).where(
                (UserSession.expires_at < now) | 
                (UserSession.is_active == False)
            )
        )
        
        # Clean expired verification tokens
        await session.execute(
            delete(EmailVerificationToken).where(
                EmailVerificationToken.expires_at < now
            )
        )
        
        # Clean expired password reset tokens
        await session.execute(
            delete(PasswordResetToken).where(
                PasswordResetToken.expires_at < now
            )
        )
        
        await session.commit()
        
        cleaned_sessions = session_result.rowcount
        logger.info(f"Cleaned up {cleaned_sessions} expired sessions")
        
        return cleaned_sessions
    
    async def _find_user_by_credentials(
        self,
        session: AsyncSession,
        username_or_email: str
    ) -> Optional[User]:
        """Find user by username or email."""
        result = await session.execute(
            select(User).where(
                (User.username == username_or_email) | 
                (User.email == username_or_email.lower())
            )
        )
        return result.scalar_one_or_none()
    
    async def _check_login_rate_limit(
        self,
        session: AsyncSession,
        ip_address: str,
        username_or_email: str
    ):
        """Check login rate limiting."""
        # Check recent failed attempts from this IP
        recent_time = datetime.utcnow() - timedelta(minutes=SecurityConfig.LOCKOUT_DURATION_MINUTES)
        
        failed_attempts = await session.execute(
            select(func.count(LoginAttempt.id)).where(
                and_(
                    LoginAttempt.ip_address == ip_address,
                    LoginAttempt.success == False,
                    LoginAttempt.attempted_at > recent_time
                )
            )
        )
        
        failed_count = failed_attempts.scalar()
        
        if failed_count >= SecurityConfig.MAX_LOGIN_ATTEMPTS:
            raise AccountLockedException(
                f"Too many failed login attempts. Please try again after {SecurityConfig.LOCKOUT_DURATION_MINUTES} minutes."
            )
    
    async def _log_login_attempt(
        self,
        session: AsyncSession,
        user: Optional[User],
        username_attempted: str,
        ip_address: str,
        user_agent: str = None,
        success: bool = True,
        failure_reason: str = None
    ):
        """Log login attempt for security monitoring."""
        attempt = LoginAttempt(
            user_id=user.id if user else None,
            username_attempted=username_attempted,
            success=success,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=self.security_utils.sanitize_user_agent(user_agent or "")
        )
        
        session.add(attempt)
        await session.commit()
    
    async def _create_user_session(
        self,
        session: AsyncSession,
        user_id: str,
        access_token: str,
        refresh_token: str,
        ip_address: str,
        user_agent: str = None
    ):
        """Create user session record."""
        # Get JWT ID from access token
        payload = self.jwt_manager.verify_token(access_token, "access")
        jwt_id = payload.get("jti") if payload else None
        
        # Clean up old sessions if user has too many
        await self._cleanup_old_sessions(session, user_id)
        
        user_session = UserSession(
            user_id=user_id,
            jwt_token_id=jwt_id,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=self.security_utils.sanitize_user_agent(user_agent or ""),
            device_info=self.security_utils.extract_device_info(user_agent or ""),
            expires_at=datetime.utcnow() + timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        session.add(user_session)
        await session.commit()
    
    async def _cleanup_old_sessions(self, session: AsyncSession, user_id: str):
        """Remove old sessions if user has too many."""
        # Count active sessions
        session_count = await session.execute(
            select(func.count(UserSession.id)).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True
                )
            )
        )
        
        if session_count.scalar() >= SecurityConfig.MAX_SESSIONS_PER_USER:
            # Get oldest sessions to remove
            old_sessions = await session.execute(
                select(UserSession).where(
                    and_(
                        UserSession.user_id == user_id,
                        UserSession.is_active == True
                    )
                ).order_by(UserSession.last_activity.asc())
                .limit(1)
            )
            
            for old_session in old_sessions.scalars():
                old_session.is_active = False


# Global authentication manager instance
auth_manager = AuthenticationManager()


# FastAPI dependency injection functions
async def get_current_user(
    authorization: str = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """Get current authenticated user from JWT token."""
    from fastapi import HTTPException, status
    
    try:
        # Extract token from authorization header
        token = authorization.credentials
        
        # Verify and decode the token
        payload = auth_manager.jwt_manager.verify_token(token, "access")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        # Get user from database
        user = await auth_manager._get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is not active"
            )
        
        return user
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role for endpoint access."""
    from fastapi import HTTPException, status
    
    if current_user.role not in [UserRole.ADMIN, UserRole.MODERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


async def require_vip(current_user: User = Depends(get_current_user)) -> User:
    """Require VIP or higher role for endpoint access."""
    from fastapi import HTTPException, status
    
    if current_user.role not in [UserRole.VIP, UserRole.MODERATOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="VIP access required"
        )
    
    return current_user