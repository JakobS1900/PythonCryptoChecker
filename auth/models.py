"""
User authentication models for crypto gamification platform.
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class UserRole(Enum):
    """User roles for access control."""
    PLAYER = "PLAYER"         # Regular player
    VIP = "VIP"              # VIP player with special privileges  
    MODERATOR = "MODERATOR"   # Community moderator
    ADMIN = "ADMIN"          # Platform administrator


class UserStatus(Enum):
    """User account status."""
    ACTIVE = "ACTIVE"         # Normal active account
    INACTIVE = "INACTIVE"     # Temporarily inactive
    SUSPENDED = "SUSPENDED"   # Suspended for violations
    BANNED = "BANNED"        # Permanently banned


class User(Base):
    """User account model with authentication and profile data."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Authentication
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile information
    display_name = Column(String(100))
    avatar_url = Column(String(255))
    bio = Column(Text)
    
    # Account settings
    role = Column(String, default=UserRole.PLAYER.value)
    status = Column(String, default=UserStatus.ACTIVE.value)
    is_email_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    email_verified_at = Column(DateTime)
    
    # Gaming profile
    current_level = Column(Integer, default=1)
    total_experience = Column(Integer, default=0)
    games_played = Column(Integer, default=0)
    total_winnings = Column(Integer, default=0)
    favorite_crypto = Column(String(50))
    
    # Privacy settings
    profile_public = Column(Boolean, default=True)
    show_stats = Column(Boolean, default=True)
    allow_friend_requests = Column(Boolean, default=True)
    
    # Relationships
    wallet = relationship("VirtualWallet", back_populates="user", uselist=False)
    inventory = relationship("UserInventory", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")
    login_attempts = relationship("LoginAttempt", back_populates="user")
    
    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary for API responses."""
        user_data = {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name or self.username,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "role": self.role,
            "status": self.status,
            "is_email_verified": self.is_email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "current_level": self.current_level,
            "total_experience": self.total_experience,
            "games_played": self.games_played,
            "total_winnings": self.total_winnings,
            "favorite_crypto": self.favorite_crypto,
            "profile_public": self.profile_public,
            "show_stats": self.show_stats
        }
        
        if include_sensitive:
            user_data.update({
                "email": self.email,
                "allow_friend_requests": self.allow_friend_requests,
                "email_verified_at": self.email_verified_at.isoformat() if self.email_verified_at else None
            })
        
        return user_data


class UserSession(Base):
    """User session tracking for JWT token management."""
    __tablename__ = "user_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    
    # Session data
    jwt_token_id = Column(String, unique=True, nullable=False)  # JTI claim
    refresh_token = Column(String, unique=True, nullable=False)
    
    # Session metadata
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    device_info = Column(Text)
    
    # Session state
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def is_expired(self):
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """Check if session is valid and active."""
        return self.is_active and not self.is_expired()


class LoginAttempt(Base):
    """Login attempt tracking for security monitoring."""
    __tablename__ = "login_attempts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # User identification
    user_id = Column(String, index=True)  # Nullable for failed username lookups
    username_attempted = Column(String(50), index=True)
    email_attempted = Column(String(100), index=True)
    
    # Attempt details
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(100))  # invalid_credentials, account_locked, etc.
    
    # Request metadata
    ip_address = Column(String(45), nullable=False, index=True)
    user_agent = Column(Text)
    
    # Timestamps
    attempted_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="login_attempts")


class EmailVerificationToken(Base):
    """Email verification tokens."""
    __tablename__ = "email_verification_tokens"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    
    token = Column(String, unique=True, nullable=False)
    email = Column(String(100), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)
    
    def is_expired(self):
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """Check if token is valid and unused."""
        return not self.used_at and not self.is_expired()


class PasswordResetToken(Base):
    """Password reset tokens."""
    __tablename__ = "password_reset_tokens"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    
    token = Column(String, unique=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)
    
    def is_expired(self):
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """Check if token is valid and unused."""
        return not self.used_at and not self.is_expired()


class UserPreferences(Base):
    """User preferences and settings."""
    __tablename__ = "user_preferences"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, unique=True, nullable=False, index=True)
    
    # UI Preferences
    theme = Column(String(20), default="dark")  # dark, light, auto
    language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")
    
    # Notification preferences
    email_notifications = Column(Boolean, default=True)
    daily_reward_reminders = Column(Boolean, default=True)
    achievement_notifications = Column(Boolean, default=True)
    friend_notifications = Column(Boolean, default=True)
    
    # Gaming preferences
    auto_spin_enabled = Column(Boolean, default=False)
    sound_effects_enabled = Column(Boolean, default=True)
    animations_enabled = Column(Boolean, default=True)
    show_tutorial = Column(Boolean, default=True)
    
    # Privacy preferences
    show_online_status = Column(Boolean, default=True)
    allow_game_invites = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)