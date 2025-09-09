"""
Authentication API endpoints for user management.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import os
import shutil
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from database.database_manager import get_db_session
from database.unified_models import User
from auth.auth_manager import AuthenticationManager
from auth.security import SecurityUtils
from logger import logger

router = APIRouter()
security = HTTPBearer()
auth_manager = AuthenticationManager()
security_utils = SecurityUtils()


# ==================== REQUEST/RESPONSE MODELS ====================

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: Optional[str] = Field(None, max_length=100)


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=255)
    profile_public: Optional[bool] = None
    show_stats: Optional[bool] = None
    allow_friend_requests: Optional[bool] = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    role: str
    status: str
    current_level: int
    prestige_level: int
    total_experience: int
    created_at: str
    last_login: Optional[str] = None
    profile_public: bool
    show_stats: bool


# ==================== ENDPOINTS ====================

@router.post("/register", response_model=AuthResponse)
async def register_user(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Register new user account."""
    try:
        # Validate input
        username_valid, username_errors = security_utils.validate_username(request.username)
        if not username_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid username: {', '.join(username_errors)}"
            )
        
        # Register user
        user, verification_token = await auth_manager.register_user(
            session=session,
            username=request.username,
            email=request.email,
            password=request.password,
            display_name=request.display_name,
            ip_address="127.0.0.1",  # Will be extracted from request in production
            user_agent="API Client"
        )
        
        # Create initial session
        user_data, access_token, refresh_token = await auth_manager.authenticate_user(
            session=session,
            username_or_email=request.username,
            password=request.password,
            ip_address="127.0.0.1",
            user_agent="API Client"
        )
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,  # 1 hour
            user=user_data.to_dict(include_sensitive=True)
        )
        
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=AuthResponse)
async def login_user(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Login user and create session."""
    try:
        user, access_token, refresh_token = await auth_manager.authenticate_user(
            session=session,
            username_or_email=request.username_or_email,
            password=request.password,
            ip_address="127.0.0.1",
            user_agent="API Client"
        )
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,
            user=user.to_dict(include_sensitive=True)
        )
        
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Refresh access token."""
    try:
        new_access_token, new_refresh_token = await auth_manager.refresh_token(
            session=session,
            refresh_token=refresh_token,
            ip_address="127.0.0.1"
        )
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": 3600
        }
        
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout_user(
    token: str = Depends(security),
    session: AsyncSession = Depends(get_db_session)
):
    """Logout user and invalidate session."""
    try:
        success = await auth_manager.logout_user(session, token.credentials)
        
        if success:
            return {"message": "Logged out successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token"
            )
            
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logout failed"
        )


@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    token: str = Depends(security),
    session: AsyncSession = Depends(get_db_session)
):
    """Get current user profile."""
    try:
        user = await auth_manager.get_user_by_token(session, token.credentials)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return UserResponse(**user.to_dict(include_sensitive=True))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get profile failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get profile"
        )


@router.put("/profile")
async def update_user_profile(
    request: ProfileUpdateRequest,
    token: str = Depends(security),
    session: AsyncSession = Depends(get_db_session)
):
    """Update user profile."""
    try:
        user = await auth_manager.get_user_by_token(session, token.credentials)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Update profile fields
        update_data = request.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        await session.commit()
        
        return {"message": "Profile updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.post("/profile/avatar")
async def upload_profile_avatar(
    file: UploadFile = File(...),
    token: str = Depends(security),
    session: AsyncSession = Depends(get_db_session)
):
    """Upload and set the current user's profile avatar.

    - Accepts: JPEG/PNG/WebP up to ~5MB
    - Stores under: web/static/uploads/avatars
    - Updates: User.avatar_url
    """
    try:
        user = await auth_manager.get_user_by_token(session, token.credentials)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        # Validate content type
        allowed_types = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
        content_type = (file.content_type or "").lower()
        if content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Unsupported image type. Use JPG, PNG, or WebP.")

        # Ensure upload directory exists
        base_dir = Path("web/static/uploads/avatars")
        base_dir.mkdir(parents=True, exist_ok=True)

        # Enforce size limit (~5MB) while streaming to disk
        max_bytes = 5 * 1024 * 1024
        ext = allowed_types[content_type]
        safe_filename = f"{user.id}{ext}"
        dest_path = base_dir / safe_filename

        bytes_written = 0
        with dest_path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 64)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    try:
                        out.close()
                        dest_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    raise HTTPException(status_code=413, detail="File too large (max 5MB)")
                out.write(chunk)

        # Update user profile
        relative_url = f"/static/uploads/avatars/{safe_filename}"
        user.avatar_url = relative_url
        user.updated_at = datetime.utcnow()
        await session.commit()

        return {"message": "Avatar updated", "avatar_url": relative_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Avatar upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload avatar")


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    token: str = Depends(security),
    session: AsyncSession = Depends(get_db_session)
):
    """Change user password."""
    try:
        user = await auth_manager.get_user_by_token(session, token.credentials)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        success = await auth_manager.change_password(
            session=session,
            user_id=user.id,
            current_password=request.current_password,
            new_password=request.new_password
        )
        
        if success:
            return {"message": "Password changed successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to change password"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/verify-email/{token}")
async def verify_email(
    token: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Verify user email address."""
    try:
        success = await auth_manager.verify_email(session, token)
        
        if success:
            return {"message": "Email verified successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email verification failed"
        )


@router.get("/me/sessions")
async def get_user_sessions(
    token: str = Depends(security),
    session: AsyncSession = Depends(get_db_session)
):
    """Get user's active sessions."""
    try:
        user = await auth_manager.get_user_by_token(session, token.credentials)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user sessions (simplified - would implement proper session listing)
        return {
            "active_sessions": 1,
            "current_session": {
                "created_at": user.last_login.isoformat() if user.last_login else None,
                "device_info": "API Client",
                "ip_address": "127.0.0.1"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get sessions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sessions"
        )
