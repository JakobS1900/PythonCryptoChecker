"""
Unified database manager for the gamification platform.
Handles database initialization, migrations, and session management.
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select, text

from .unified_models import Base, Achievement, CollectibleItem, Leaderboard
from app_config import config
from logger import logger


class DatabaseManager:
    """Centralized database management."""
    
    def __init__(self):
        self.database_url = config.get("DATABASE_URL", "sqlite+aiosqlite:///./crypto_gamification.db")
        self.engine = None
        self.session_factory = None
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize database connection and create tables."""
        if self.is_initialized:
            return
        
        try:
            # Create async engine
            self.engine = create_async_engine(
                self.database_url,
                echo=config.get("DEBUG_MODE", False),
                poolclass=StaticPool if "sqlite" in self.database_url else None,
                connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {},
                pool_pre_ping=True
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create all tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Set initialized flag before default data
            self.is_initialized = True
            
            # Initialize default data
            await self._initialize_default_data()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise
    
    def get_session(self) -> AsyncSession:
        """Get database session."""
        if not self.is_initialized:
            raise RuntimeError("Database not initialized")
        return self.session_factory()
    
    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            self.is_initialized = False
            logger.info("Database connections closed")
    
    async def _initialize_default_data(self):
        """Initialize default achievements, items, and leaderboards."""
        async with self.get_session() as session:
            try:
                # Initialize achievements
                await self._create_default_achievements(session)
                
                # Initialize collectible items
                await self._create_default_items(session)
                
                # Initialize leaderboards
                await self._create_default_leaderboards(session)
                
                await session.commit()
                logger.info("Default data initialized")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to initialize default data: {e}")
                raise
    
    async def _create_default_achievements(self, session: AsyncSession):
        """Create default achievement definitions."""
        
        # Check if achievements already exist
        existing = await session.execute(select(Achievement))
        if existing.scalars().first():
            return
        
        achievements = [
            # Gaming Achievements
            {
                "name": "First Spin",
                "description": "Complete your first roulette spin",
                "achievement_type": "GAMING",
                "requirement_type": "games_played",
                "requirement_value": 1,
                "gem_reward": 100.0,
                "xp_reward": 50,
                "icon_url": "/icons/first_spin.png",
                "color_theme": "#4CAF50"
            },
            {
                "name": "Lucky Seven",
                "description": "Win 7 games in a row",
                "achievement_type": "STREAK",
                "requirement_type": "win_streak",
                "requirement_value": 7,
                "gem_reward": 500.0,
                "xp_reward": 200,
                "icon_url": "/icons/lucky_seven.png",
                "color_theme": "#FF9800"
            },
            {
                "name": "High Roller",
                "description": "Place a single bet of 1000+ GEM coins",
                "achievement_type": "GAMING",
                "requirement_type": "single_bet_amount",
                "requirement_value": 1000,
                "gem_reward": 250.0,
                "xp_reward": 100,
                "icon_url": "/icons/high_roller.png",
                "color_theme": "#9C27B0"
            },
            
            # Collection Achievements
            {
                "name": "Crypto Collector",
                "description": "Collect 25 different cryptocurrency items",
                "achievement_type": "COLLECTION",
                "requirement_type": "unique_items_collected",
                "requirement_value": 25,
                "gem_reward": 750.0,
                "xp_reward": 300,
                "icon_url": "/icons/crypto_collector.png",
                "color_theme": "#2196F3"
            },
            {
                "name": "Legendary Hunter",
                "description": "Own a Legendary rarity item",
                "achievement_type": "COLLECTION",
                "requirement_type": "legendary_items_owned",
                "requirement_value": 1,
                "gem_reward": 2000.0,
                "xp_reward": 500,
                "icon_url": "/icons/legendary_hunter.png",
                "color_theme": "#FFD700",
                "rarity": "LEGENDARY"
            },
            
            # Social Achievements
            {
                "name": "Social Butterfly",
                "description": "Add 10 friends",
                "achievement_type": "SOCIAL",
                "requirement_type": "friends_count",
                "requirement_value": 10,
                "gem_reward": 300.0,
                "xp_reward": 150,
                "icon_url": "/icons/social_butterfly.png",
                "color_theme": "#E91E63"
            },
            
            # Milestone Achievements
            {
                "name": "Level 10 Master",
                "description": "Reach level 10",
                "achievement_type": "MILESTONE",
                "requirement_type": "level_reached",
                "requirement_value": 10,
                "gem_reward": 1000.0,
                "xp_reward": 0,  # No XP as they already leveled up
                "icon_url": "/icons/level_10.png",
                "color_theme": "#607D8B"
            },
            {
                "name": "Daily Warrior",
                "description": "Login for 30 consecutive days",
                "achievement_type": "STREAK",
                "requirement_type": "daily_login_streak",
                "requirement_value": 30,
                "gem_reward": 1500.0,
                "xp_reward": 400,
                "icon_url": "/icons/daily_warrior.png",
                "color_theme": "#795548"
            },
            
            # Gaming Milestones
            {
                "name": "Century Club",
                "description": "Play 100 games",
                "achievement_type": "MILESTONE",
                "requirement_type": "total_games_played",
                "requirement_value": 100,
                "gem_reward": 500.0,
                "xp_reward": 250,
                "icon_url": "/icons/century_club.png",
                "color_theme": "#009688"
            },
            {
                "name": "Big Winner",
                "description": "Win 10,000 GEM coins in a single game",
                "achievement_type": "GAMING",
                "requirement_type": "single_game_winnings",
                "requirement_value": 10000,
                "gem_reward": 2500.0,
                "xp_reward": 600,
                "icon_url": "/icons/big_winner.png",
                "color_theme": "#FF5722",
                "rarity": "EPIC"
            }
        ]
        
        for achievement_data in achievements:
            achievement = Achievement(**achievement_data)
            session.add(achievement)
    
    async def _create_default_items(self, session: AsyncSession):
        """Create default collectible items."""
        
        # Check if items already exist
        existing = await session.execute(select(CollectibleItem))
        if existing.scalars().first():
            return
        
        # Import item generator to create starter items
        from gamification.item_generator import CryptoItemGenerator
        
        generator = CryptoItemGenerator()
        await generator.generate_starter_items(session)
    
    async def _create_default_leaderboards(self, session: AsyncSession):
        """Create default leaderboards."""
        
        # Check if leaderboards already exist
        existing = await session.execute(select(Leaderboard))
        if existing.scalars().first():
            return
        
        leaderboards = [
            {
                "name": "Top Winners",
                "description": "Players with the highest total winnings",
                "leaderboard_type": "total_winnings",
                "time_period": "ALL_TIME",
                "rewards_config": {
                    "1": {"gems": 5000, "title": "Legendary Winner"},
                    "2": {"gems": 3000, "title": "Epic Winner"},
                    "3": {"gems": 2000, "title": "Great Winner"}
                }
            },
            {
                "name": "Level Leaders",
                "description": "Highest level players",
                "leaderboard_type": "level",
                "time_period": "ALL_TIME",
                "rewards_config": {
                    "1": {"gems": 3000, "title": "Master Player"},
                    "2": {"gems": 2000, "title": "Expert Player"},
                    "3": {"gems": 1500, "title": "Veteran Player"}
                }
            },
            {
                "name": "Collection Kings",
                "description": "Players with the most complete collections",
                "leaderboard_type": "collection_completion",
                "time_period": "ALL_TIME",
                "rewards_config": {
                    "1": {"gems": 4000, "title": "Ultimate Collector"},
                    "2": {"gems": 2500, "title": "Master Collector"},
                    "3": {"gems": 1800, "title": "Elite Collector"}
                }
            },
            {
                "name": "Weekly Winners",
                "description": "This week's biggest winners",
                "leaderboard_type": "weekly_winnings",
                "time_period": "WEEKLY",
                "rewards_config": {
                    "1": {"gems": 2000, "title": "Weekly Champion"},
                    "2": {"gems": 1200, "title": "Weekly Runner-up"},
                    "3": {"gems": 800, "title": "Weekly Star"}
                }
            }
        ]
        
        for leaderboard_data in leaderboards:
            leaderboard = Leaderboard(**leaderboard_data)
            session.add(leaderboard)


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions for database operations
async def get_db_session():
    """Get database session for dependency injection."""
    async with db_manager.get_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database():
    """Initialize database - call this on startup."""
    await db_manager.initialize()


async def close_database():
    """Close database connections - call this on shutdown."""
    await db_manager.close()


# Database migration utilities
class MigrationManager:
    """Handle database migrations and schema updates."""
    
    @staticmethod
    async def create_indexes():
        """Create additional indexes for performance."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_game_sessions_user_id ON game_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_game_sessions_created_at ON game_sessions(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_virtual_transactions_wallet_id ON virtual_transactions(wallet_id)",
            "CREATE INDEX IF NOT EXISTS idx_virtual_transactions_created_at ON virtual_transactions(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_user_inventory_user_id ON user_inventory(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_achievements_user_id ON user_achievements(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_leaderboard_entries_leaderboard_id ON leaderboard_entries(leaderboard_id)",
            "CREATE INDEX IF NOT EXISTS idx_leaderboard_entries_rank ON leaderboard_entries(current_rank)",
            "CREATE INDEX IF NOT EXISTS idx_friendships_users ON friendships(sender_id, receiver_id)",
        ]
        
        async with db_manager.get_session() as session:
            for index_sql in indexes:
                try:
                    await session.execute(text(index_sql))
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")
            
            await session.commit()
        
        logger.info("Database indexes created")
    
    @staticmethod
    async def cleanup_old_data():
        """Clean up old expired data."""
        cleanup_queries = [
            # Remove expired sessions older than 30 days
            "DELETE FROM user_sessions WHERE expires_at < datetime('now', '-30 days')",
            
            # Remove old game sessions older than 90 days (keep stats)
            "DELETE FROM game_sessions WHERE completed_at < datetime('now', '-90 days')",
            
            # Clean up old transactions older than 180 days
            "DELETE FROM virtual_transactions WHERE created_at < datetime('now', '-180 days')"
        ]
        
        async with db_manager.get_session() as session:
            total_cleaned = 0
            for query in cleanup_queries:
                try:
                    result = await session.execute(text(query))
                    total_cleaned += result.rowcount
                except Exception as e:
                    logger.error(f"Failed to execute cleanup query: {e}")
            
            await session.commit()
        
        logger.info(f"Database cleanup completed: {total_cleaned} records removed")
        return total_cleaned