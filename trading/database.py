"""
Database configuration and connection management for trading system.
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app_config import config
from logger import logger
# Use the unified database models instead of separate ones
from database.unified_models import Base

# Database URL configuration - use the same database as main application
DATABASE_URL = config.get(
    "DATABASE_URL", 
    "sqlite+aiosqlite:///./crypto_gaming.db"
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=config.get("DEBUG_MODE", False),
    poolclass=StaticPool if "sqlite" in DATABASE_URL else None,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def init_database():
    """Initialize database tables using unified models."""
    try:
        logger.info("Initializing trading database with unified models...")
        
        # The unified models are already initialized by the main database manager
        # We just need to ensure we're using the same database
        
        logger.info("Trading database uses unified models - no separate initialization needed")
        
    except Exception as e:
        logger.error(f"Failed to initialize trading database: {e}", exc_info=True)
        raise


async def get_async_session() -> AsyncSession:
    """Get an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class DatabaseManager:
    """Database operations manager."""
    
    def __init__(self):
        self.engine = engine
        self.session_factory = AsyncSessionLocal
    
    def create_session(self):
        """Create a new database session context manager."""
        return self.session_factory()
    
    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            async with self.session_factory() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def close(self):
        """Close database engine."""
        await self.engine.dispose()


# Global database manager instance
db_manager = DatabaseManager()
