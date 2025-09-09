"""
Unified database system for crypto gamification platform.
Consolidates all models and database operations.
"""

from .unified_models import (
    Base, User, UserSession, VirtualWallet, VirtualCryptoHolding,
    VirtualTransaction, CollectibleItem, UserInventory, GameSession,
    GameBet, GameStats, Achievement, UserAchievement, Friendship,
    DailyReward, Leaderboard, LeaderboardEntry,
    
    # Enums
    UserRole, UserStatus, CurrencyType, ItemRarity, ItemType,
    GameType, GameStatus, BetType, AchievementType, AchievementStatus,
    
    # Constants
    GameConstants
)

from .database_manager import (
    DatabaseManager, db_manager, get_db_session,
    init_database, close_database, MigrationManager
)

__all__ = [
    # Models
    "Base", "User", "UserSession", "VirtualWallet", "VirtualCryptoHolding",
    "VirtualTransaction", "CollectibleItem", "UserInventory", "GameSession",
    "GameBet", "GameStats", "Achievement", "UserAchievement", "Friendship",
    "DailyReward", "Leaderboard", "LeaderboardEntry",
    
    # Enums
    "UserRole", "UserStatus", "CurrencyType", "ItemRarity", "ItemType",
    "GameType", "GameStatus", "BetType", "AchievementType", "AchievementStatus",
    
    # Constants
    "GameConstants",
    
    # Database Management
    "DatabaseManager", "db_manager", "get_db_session",
    "init_database", "close_database", "MigrationManager"
]