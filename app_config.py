"""
Application configuration for CryptoChecker Gaming Platform.
Loads configuration from environment variables with fallback defaults.
"""

import os
from typing import Any, Dict, Optional


class Config:
    """Configuration manager for the application."""
    
    def __init__(self):
        # Load from environment variables
        self._config = {
            # Application Settings
            "DEBUG": os.getenv("DEBUG", "True").lower() == "true",
            "SECRET_KEY": os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
            "HOST": os.getenv("HOST", "localhost"),
            "PORT": int(os.getenv("PORT", "8000")),
            
            # Database Configuration
            "DATABASE_URL": os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crypto_gaming.db"),
            "DEBUG_MODE": os.getenv("DEBUG", "True").lower() == "true",
            
            # JWT Settings
            "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key"),
            "JWT_ALGORITHM": os.getenv("JWT_ALGORITHM", "HS256"),
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
            
            # Game Configuration
            "STARTING_GEM_COINS": float(os.getenv("STARTING_GEM_COINS", "1000")),
            "DAILY_BONUS_GEMS": float(os.getenv("DAILY_BONUS_GEMS", "50")),
            "MIN_BET_AMOUNT": float(os.getenv("MIN_BET_AMOUNT", "1")),
            "MAX_BET_AMOUNT": float(os.getenv("MAX_BET_AMOUNT", "10000")),
            
            # Admin Configuration
            "ADMIN_USERNAME": os.getenv("ADMIN_USERNAME", "admin"),
            "ADMIN_EMAIL": os.getenv("ADMIN_EMAIL", "admin@cryptochecke.local"),
            "ADMIN_PASSWORD": os.getenv("ADMIN_PASSWORD", "change-this-password"),
            
            # Analytics Configuration
            "ANALYTICS_ENABLED": os.getenv("ANALYTICS_ENABLED", "True").lower() == "true",
            "MONITORING_ENABLED": os.getenv("MONITORING_ENABLED", "True").lower() == "true",
            "METRICS_RETENTION_DAYS": int(os.getenv("METRICS_RETENTION_DAYS", "30")),
            
            # Security Settings
            "CORS_ORIGINS": os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
            "SESSION_TIMEOUT_HOURS": int(os.getenv("SESSION_TIMEOUT_HOURS", "24")),
            "PASSWORD_MIN_LENGTH": int(os.getenv("PASSWORD_MIN_LENGTH", "8")),
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with optional default."""
        return self._config.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        return self._config[key]
    
    def __contains__(self, key: str) -> bool:
        """Allow 'in' operator."""
        return key in self._config
    
    @property
    def all(self) -> Dict[str, Any]:
        """Get all configuration as dictionary."""
        return self._config.copy()


# Create global config instance
config = Config()