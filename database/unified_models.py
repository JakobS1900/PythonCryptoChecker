"""
Unified database models for the complete gamification platform.
Consolidates all systems with proper relationships and foreign keys.
"""

import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


# ==================== ENUMS ====================

class UserRole(Enum):
    """User roles for access control."""
    PLAYER = "PLAYER"
    VIP = "VIP"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"


class UserStatus(Enum):
    """User account status."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    BANNED = "BANNED"


class CurrencyType(Enum):
    """Types of virtual currencies."""
    GEM_COINS = "GEM_COINS"
    EXPERIENCE_POINTS = "XP"
    VIRTUAL_CRYPTO = "VIRTUAL_CRYPTO"
    PREMIUM_TOKENS = "PREMIUM"


class ItemRarity(Enum):
    """Item rarity levels."""
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"


class ItemType(Enum):
    """Types of collectible items."""
    TRADING_CARD = "TRADING_CARD"
    COSMETIC = "COSMETIC"
    TROPHY = "TROPHY"
    CONSUMABLE = "CONSUMABLE"
    SPECIAL = "SPECIAL"


class GameType(Enum):
    """Types of roulette games."""
    CLASSIC_CRYPTO = "CLASSIC_CRYPTO"
    PRICE_PREDICTION = "PRICE_PREDICTION"
    VOLATILITY_ROULETTE = "VOLATILITY_ROULETTE"
    TOURNAMENT = "TOURNAMENT"


class GameStatus(Enum):
    """Status of game sessions."""
    ACTIVE = "ACTIVE"
    SPINNING = "SPINNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class BetType(Enum):
    """Types of roulette bets."""
    SINGLE_CRYPTO = "SINGLE_CRYPTO"
    CRYPTO_COLOR = "CRYPTO_COLOR"
    CRYPTO_CATEGORY = "CRYPTO_CATEGORY"
    EVEN_ODD = "EVEN_ODD"
    HIGH_LOW = "HIGH_LOW"
    DOZEN = "DOZEN"
    COLUMN = "COLUMN"


class AchievementType(Enum):
    """Achievement categories."""
    GAMING = "GAMING"
    COLLECTION = "COLLECTION"
    TRADING = "TRADING"
    SOCIAL = "SOCIAL"
    STREAK = "STREAK"
    MILESTONE = "MILESTONE"


class AchievementStatus(Enum):
    """Achievement completion status."""
    LOCKED = "LOCKED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


# ==================== USER SYSTEM ====================

class User(Base):
    """Core user model with authentication and profile."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Authentication
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    display_name = Column(String(100))
    avatar_url = Column(String(255))
    bio = Column(Text)
    
    # Account settings
    role = Column(String, default=UserRole.PLAYER.value)
    status = Column(String, default=UserStatus.ACTIVE.value)
    is_email_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Gaming profile
    current_level = Column(Integer, default=1)
    total_experience = Column(Integer, default=0)
    prestige_level = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    email_verified_at = Column(DateTime)
    
    # Privacy settings
    profile_public = Column(Boolean, default=True)
    show_stats = Column(Boolean, default=True)
    allow_friend_requests = Column(Boolean, default=True)
    
    # Relationships
    wallet = relationship("VirtualWallet", back_populates="user", uselist=False)
    inventory = relationship("UserInventory", back_populates="user")
    game_sessions = relationship("GameSession", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")
    friendships_sent = relationship("Friendship", foreign_keys="Friendship.sender_id", back_populates="sender")
    friendships_received = relationship("Friendship", foreign_keys="Friendship.receiver_id", back_populates="receiver")
    daily_rewards = relationship("DailyReward", back_populates="user", uselist=False)

    # Trading relationships
    portfolios = relationship("Portfolio", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    orders = relationship("Order", back_populates="user")
    trading_strategies = relationship("TradingStrategy", back_populates="user")
    game_stats = relationship("GameStats", back_populates="user", uselist=False)
    tutorial_progress = relationship("TutorialProgress", back_populates="user", uselist=False)
    user_onboarding = relationship("UserOnboarding", back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="user")
    notification_preferences = relationship("NotificationPreferences", back_populates="user", uselist=False)
    mini_game_stats = relationship("UserGameStats", back_populates="user", uselist=False)

    # Market & Portfolio relationships
    user_portfolio = relationship("UserPortfolio", uselist=False)
    user_profile = relationship("UserProfile", uselist=False)
    watchlists = relationship("MarketWatchlist")
    price_alerts = relationship("PriceAlert")
    community_posts = relationship("CommunityPost")
    post_likes = relationship("PostLike")
    post_comments = relationship("PostComment")


class UserSession(Base):
    """User session tracking."""
    __tablename__ = "user_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    jwt_token_id = Column(String, unique=True, nullable=False)
    refresh_token = Column(String, unique=True, nullable=False)
    
    ip_address = Column(String(45))
    user_agent = Column(Text)
    device_info = Column(Text)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")


# ==================== VIRTUAL ECONOMY ====================

class VirtualWallet(Base):
    """User's virtual wallet."""
    __tablename__ = "virtual_wallets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Currencies
    gem_coins = Column(Float, default=1000.0)
    experience_points = Column(Integer, default=0)
    premium_tokens = Column(Integer, default=0)
    
    # Player progression
    level = Column(Integer, default=1)
    total_xp_earned = Column(Integer, default=0)
    
    # Statistics
    total_gems_earned = Column(Float, default=1000.0)
    total_gems_spent = Column(Float, default=0.0)
    games_played = Column(Integer, default=0)
    games_won = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="wallet")
    virtual_crypto_holdings = relationship("VirtualCryptoHolding", back_populates="wallet")
    transactions = relationship("VirtualTransaction", back_populates="wallet")


class VirtualCryptoHolding(Base):
    """Virtual cryptocurrency holdings."""
    __tablename__ = "virtual_crypto_holdings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_id = Column(String, ForeignKey("virtual_wallets.id"), nullable=False)
    
    crypto_id = Column(String, nullable=False)
    crypto_symbol = Column(String, nullable=False)
    virtual_amount = Column(Float, nullable=False)
    
    total_gems_invested = Column(Float, default=0.0)
    average_buy_price = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    wallet = relationship("VirtualWallet", back_populates="virtual_crypto_holdings")


class VirtualTransaction(Base):
    """Transaction history."""
    __tablename__ = "virtual_transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_id = Column(String, ForeignKey("virtual_wallets.id"), nullable=False)
    
    transaction_type = Column(String, nullable=False)
    currency_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    
    source = Column(String)
    description = Column(Text)
    reference_id = Column(String)
    
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    wallet = relationship("VirtualWallet", back_populates="transactions")


# ==================== INVENTORY SYSTEM ====================

class CollectibleItem(Base):
    """Collectible items."""
    __tablename__ = "collectible_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    name = Column(String(100), nullable=False)
    description = Column(Text)
    item_type = Column(String, nullable=False)
    rarity = Column(String, nullable=False)
    
    image_url = Column(String)
    color_theme = Column(String)
    animation_type = Column(String)
    
    gem_value = Column(Float, default=0.0)
    is_tradeable = Column(Boolean, default=True)
    is_consumable = Column(Boolean, default=False)
    effect_description = Column(Text)
    
    crypto_theme = Column(String)
    release_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user_items = relationship("UserInventory", back_populates="item")


class UserInventory(Base):
    """User's inventory."""
    __tablename__ = "user_inventory"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    item_id = Column(String, ForeignKey("collectible_items.id"), nullable=False)
    
    quantity = Column(Integer, default=1)
    acquired_at = Column(DateTime, default=datetime.utcnow)
    acquisition_method = Column(String)
    
    is_equipped = Column(Boolean, default=False)
    is_favorite = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="inventory")
    item = relationship("CollectibleItem", back_populates="user_items")


class ActiveEffect(Base):
    """Active consumable effects applied to a user (buffs)."""
    __tablename__ = "active_effects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Effect type identifiers: DROP_RATE, XP_MULT, GEM_MULT, GUARANTEED_RARE
    effect_type = Column(String, nullable=False)
    multiplier = Column(Float, default=1.0)  # For *_MULT types or drop rate boosts
    remaining_uses = Column(Integer)         # For effects with limited uses
    scope = Column(String, default="TRADING")  # Scope: TRADING, GAMING, GLOBAL

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)            # Null means until uses are consumed

    # Metadata
    source_item_id = Column(String)          # Inventory/Item source (optional)


# ==================== GAMING SYSTEM ====================

class GameSession(Base):
    """Individual game sessions."""
    __tablename__ = "game_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    game_type = Column(String, default=GameType.CLASSIC_CRYPTO.value)
    status = Column(String, default=GameStatus.ACTIVE.value)
    
    # Provably fair
    server_seed = Column(String, nullable=False)
    server_seed_hash = Column(String, nullable=False)
    client_seed = Column(String, nullable=False)
    nonce = Column(Integer, default=1)
    
    # Results
    winning_number = Column(Integer)
    winning_crypto = Column(String)
    spin_hash = Column(String)
    
    # Betting
    total_bet_amount = Column(Float, default=0.0)
    total_winnings = Column(Float, default=0.0)
    house_edge_amount = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    spin_time = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="game_sessions")
    bets = relationship("GameBet", back_populates="game_session")


class GameBet(Base):
    """Individual bets in games."""
    __tablename__ = "game_bets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    game_session_id = Column(String, ForeignKey("game_sessions.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    bet_type = Column(String, nullable=False)
    bet_value = Column(String, nullable=False)
    bet_amount = Column(Float, nullable=False)
    
    potential_payout = Column(Float, nullable=False)
    payout_odds = Column(Float, nullable=False)
    actual_payout = Column(Float, default=0.0)
    
    is_winner = Column(Boolean, default=False)
    bet_data = Column(JSON)
    placed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    game_session = relationship("GameSession", back_populates="bets")
    user = relationship("User")


class GameStats(Base):
    """Player gaming statistics."""
    __tablename__ = "game_stats"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    
    total_games_played = Column(Integer, default=0)
    total_games_won = Column(Integer, default=0)
    total_amount_bet = Column(Float, default=0.0)
    total_amount_won = Column(Float, default=0.0)
    
    current_win_streak = Column(Integer, default=0)
    longest_win_streak = Column(Integer, default=0)
    current_loss_streak = Column(Integer, default=0)
    longest_loss_streak = Column(Integer, default=0)
    
    favorite_bet_type = Column(String)
    favorite_crypto = Column(String)
    biggest_single_win = Column(Float, default=0.0)
    biggest_single_loss = Column(Float, default=0.0)
    
    first_game_date = Column(DateTime)
    last_game_date = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    # Link to User via the primary game stats relationship
    user = relationship("User", back_populates="game_stats")


# ==================== ACHIEVEMENT SYSTEM ====================

class Achievement(Base):
    """Achievement definitions."""
    __tablename__ = "achievements"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    achievement_type = Column(String, nullable=False)
    
    # Requirements
    requirement_type = Column(String, nullable=False)  # games_won, items_collected, etc.
    requirement_value = Column(Integer, nullable=False)  # Target number
    requirement_data = Column(JSON)  # Additional requirements
    
    # Rewards
    gem_reward = Column(Float, default=0.0)
    xp_reward = Column(Integer, default=0.0)
    item_rewards = Column(JSON)  # List of item IDs to award
    
    # Display
    icon_url = Column(String)
    color_theme = Column(String)
    rarity = Column(String, default=ItemRarity.COMMON.value)
    
    # Meta
    is_active = Column(Boolean, default=True)
    is_secret = Column(Boolean, default=False)  # Hidden until unlocked
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_achievements = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    """User achievement progress."""
    __tablename__ = "user_achievements"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(String, ForeignKey("achievements.id"), nullable=False)
    
    status = Column(String, default=AchievementStatus.LOCKED.value)
    progress = Column(Integer, default=0)
    progress_percentage = Column(Float, default=0.0)
    
    unlocked_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")


# ==================== SOCIAL SYSTEM ====================

class Friendship(Base):
    """User friendships."""
    __tablename__ = "friendships"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(String, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    status = Column(String, default="PENDING")  # PENDING, ACCEPTED, DECLINED, BLOCKED
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime)
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="friendships_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="friendships_received")


class DailyReward(Base):
    """Daily login rewards."""
    __tablename__ = "daily_rewards"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_claim_date = Column(DateTime)
    
    next_reward_gems = Column(Float, default=50.0)
    next_reward_xp = Column(Integer, default=25)
    
    total_logins = Column(Integer, default=0)
    total_gems_from_daily = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="daily_rewards")


# ==================== LEADERBOARDS ====================

class Leaderboard(Base):
    """Global leaderboards."""
    __tablename__ = "leaderboards"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    name = Column(String(100), nullable=False)
    description = Column(Text)
    leaderboard_type = Column(String, nullable=False)  # total_winnings, level, collection, etc.
    
    # Configuration
    time_period = Column(String, default="ALL_TIME")  # DAILY, WEEKLY, MONTHLY, ALL_TIME
    max_entries = Column(Integer, default=1000)
    is_active = Column(Boolean, default=True)
    
    # Rewards
    rewards_config = Column(JSON)  # Rewards for top positions
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    reset_date = Column(DateTime)  # When leaderboard resets
    
    # Relationships
    entries = relationship("LeaderboardEntry", back_populates="leaderboard")


class LeaderboardEntry(Base):
    """Individual leaderboard entries."""
    __tablename__ = "leaderboard_entries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    leaderboard_id = Column(String, ForeignKey("leaderboards.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    current_rank = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    previous_rank = Column(Integer)
    
    # Additional metrics
    additional_data = Column(JSON)  # Extra data for display
    
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    leaderboard = relationship("Leaderboard", back_populates="entries")
    user = relationship("User")


# ==================== TUTORIAL SYSTEM ====================

class TutorialProgress(Base):
    """Tracks user progress through the tutorial system."""
    __tablename__ = "tutorial_progress"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Progress tracking
    current_step_id = Column(String, nullable=False)
    completed_steps = Column(JSON, default=list)  # List of completed step IDs
    
    # Status
    completed = Column(Boolean, default=False)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    last_step_completed_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="tutorial_progress")


class UserOnboarding(Base):
    """User onboarding progress tracking."""
    __tablename__ = "user_onboarding"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Onboarding progress
    current_step = Column(Integer, default=0)
    completed_steps = Column(JSON, default=list)  # List of completed step numbers
    total_steps = Column(Integer, default=9)
    
    # Status
    completed = Column(Boolean, default=False)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    last_step_completed_at = Column(DateTime)
    
    # Onboarding metadata
    onboarding_version = Column(String, default="1.0")
    rewards_claimed = Column(JSON, default=dict)  # Track claimed onboarding rewards
    
    # Relationships
    user = relationship("User", back_populates="user_onboarding")


class OnboardingStep(Base):
    """Onboarding step definitions."""
    __tablename__ = "onboarding_steps"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Step details
    step_number = Column(Integer, nullable=False, unique=True)
    step_name = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Step requirements
    requirements = Column(JSON, default=list)  # List of requirements to complete this step
    validation_type = Column(String(50))  # How to validate completion
    
    # Rewards
    gem_reward = Column(Float, default=0.0)
    xp_reward = Column(Integer, default=0)
    item_rewards = Column(JSON, default=list)  # List of items to award
    
    # UI/UX
    icon_url = Column(String(255))
    color_theme = Column(String(7), default="#667eea")  # Hex color
    
    # System
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== NOTIFICATION SYSTEM ====================

class NotificationType(Enum):
    """Types of notifications."""
    WELCOME = "WELCOME"
    DAILY_BONUS = "DAILY_BONUS"
    QUEST_REMINDER = "QUEST_REMINDER"
    QUEST_COMPLETED = "QUEST_COMPLETED"
    ACHIEVEMENT = "ACHIEVEMENT"
    FRIEND_REQUEST = "FRIEND_REQUEST"
    SOCIAL = "SOCIAL"
    GAME_RESULT = "GAME_RESULT"
    MILESTONE = "MILESTONE"
    COMEBACK = "COMEBACK"
    LOW_BALANCE = "LOW_BALANCE"
    LEVEL_UP = "LEVEL_UP"
    TRADE = "TRADE"
    SYSTEM = "SYSTEM"
    SCHEDULED = "SCHEDULED"


class Notification(Base):
    """User notifications."""
    __tablename__ = "notifications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Notification content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String, nullable=False)  # NotificationType enum value
    
    # Template system
    template_key = Column(String(100))  # Reference to notification template
    template_data = Column(JSON, default=dict)  # Data for template rendering
    
    # Delivery tracking
    channels_sent = Column(JSON, default=list)  # List of channels notification was sent to
    sent_at = Column(DateTime)
    read_at = Column(DateTime)
    
    # Scheduling
    scheduled_for = Column(DateTime)
    
    # Metadata
    action_url = Column(String(500))  # URL for notification action
    icon_url = Column(String(500))
    priority = Column(Integer, default=1)  # 1=low, 2=medium, 3=high
    
    # System
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="notifications")


class NotificationPreferences(Base):
    """User notification preferences."""
    __tablename__ = "notification_preferences"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Channel preferences
    push_notifications = Column(Boolean, default=True)
    email_notifications = Column(Boolean, default=True)
    in_app_notifications = Column(Boolean, default=True)
    
    # Notification type preferences
    daily_reminders = Column(Boolean, default=True)
    quest_reminders = Column(Boolean, default=True)
    achievement_notifications = Column(Boolean, default=True)
    social_notifications = Column(Boolean, default=True)
    game_notifications = Column(Boolean, default=True)
    trade_notifications = Column(Boolean, default=True)
    system_notifications = Column(Boolean, default=True)
    
    # Quiet hours
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(String(5), default="22:00")  # HH:MM format
    quiet_hours_end = Column(String(5), default="08:00")  # HH:MM format
    
    # Frequency limits
    max_push_per_hour = Column(Integer, default=5)
    max_email_per_day = Column(Integer, default=10)
    
    # System
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="notification_preferences")


# ==================== CONSTANTS ====================

class GameConstants:
    """Game balance and configuration constants."""
    
    # Economy
    STARTING_GEM_COINS = 1000.0
    BASE_DAILY_GEMS = 50.0
    BASE_DAILY_XP = 25
    LEVEL_UP_GEM_BONUS = 100.0
    XP_PER_LEVEL_BASE = 1000  # Base XP required for leveling
    XP_PER_LEVEL_SCALING = 1.2  # XP scaling factor per level
    
    # Gaming
    MIN_BET = 1.0
    MAX_BET = 10000.0
    HOUSE_EDGE = 0.027
    
    # Items
    DROP_RATES = {
        ItemRarity.COMMON: 0.70,
        ItemRarity.UNCOMMON: 0.20,
        ItemRarity.RARE: 0.08,
        ItemRarity.EPIC: 0.018,
        ItemRarity.LEGENDARY: 0.002
    }
    
    # Achievements
    ACHIEVEMENT_CATEGORIES = [
        "First Spin", "Lucky Streak", "High Roller", "Collector", 
        "Social Butterfly", "Daily Warrior", "Big Winner"
    ]


# ==================== TRADING SYSTEM MODELS ====================
# Import trading enums
from enum import Enum as PyEnum

class OrderType(PyEnum):
    """Order types for trading."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderSide(PyEnum):
    """Order sides for trading."""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(PyEnum):
    """Order status types."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class TransactionType(PyEnum):
    """Transaction types."""
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRADE_BUY = "TRADE_BUY"
    TRADE_SELL = "TRADE_SELL"
    FEE = "FEE"


class Portfolio(Base):
    """Portfolio table for managing virtual trading portfolios."""
    __tablename__ = "portfolios"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    initial_balance = Column(Float, nullable=False, default=100000.0)
    current_balance = Column(Float, nullable=False, default=100000.0)
    base_currency = Column(String(10), default="USD")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Performance metrics
    total_invested = Column(Float, default=0.0)
    total_profit_loss = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio")
    transactions = relationship("Transaction", back_populates="portfolio")
    orders = relationship("Order", back_populates="portfolio")
    risk_policy = relationship("RiskPolicy", back_populates="portfolio", uselist=False)


class Holding(Base):
    """Holdings table for tracking owned coins."""
    __tablename__ = "holdings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String, ForeignKey("portfolios.id"), nullable=False)
    
    coin_id = Column(String(50), nullable=False)
    coin_symbol = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False, default=0.0)
    average_cost = Column(Float, nullable=False, default=0.0)
    current_price = Column(Float, nullable=False, default=0.0)
    
    last_price_update = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")


class Transaction(Base):
    """Transactions table for tracking all portfolio activities."""
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    portfolio_id = Column(String, ForeignKey("portfolios.id"), nullable=False)
    order_id = Column(String, ForeignKey("orders.id"))
    
    transaction_type = Column(String(10), nullable=False)
    coin_id = Column(String(50))
    coin_symbol = Column(String(10))
    
    quantity = Column(Float)
    price = Column(Float)
    amount = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    portfolio = relationship("Portfolio", back_populates="transactions")
    order = relationship("Order", back_populates="transactions")


class Order(Base):
    """Orders table for managing buy/sell orders."""
    __tablename__ = "orders"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    portfolio_id = Column(String, ForeignKey("portfolios.id"), nullable=False)
    
    coin_id = Column(String(50), nullable=False)
    coin_symbol = Column(String(10), nullable=False)
    
    order_type = Column(String(11), nullable=False)  # MARKET, LIMIT, STOP_LOSS, TAKE_PROFIT
    order_side = Column(String(4), nullable=False)   # BUY, SELL
    
    quantity = Column(Float, nullable=False)
    price = Column(Float)  # For limit orders
    stop_price = Column(Float)  # For stop orders
    
    status = Column(String(9), default=OrderStatus.PENDING.value)  # PENDING, FILLED, CANCELLED, EXPIRED
    filled_quantity = Column(Float, default=0.0)
    filled_price = Column(Float)
    filled_at = Column(DateTime)
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    portfolio = relationship("Portfolio", back_populates="orders")
    transactions = relationship("Transaction", back_populates="order")
    oco_links = relationship("OCOLink", back_populates="order")


class RiskPolicy(Base):
    """Risk management policies for portfolios."""
    __tablename__ = "risk_policies"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String, ForeignKey("portfolios.id"), nullable=False, unique=True)
    
    # Position size limits
    max_position_pct = Column(Float, default=10.0)  # Max % of portfolio per position
    max_open_positions = Column(Integer, default=20)  # Max number of open positions
    max_trade_value_pct = Column(Float, default=5.0)  # Max % of portfolio per trade
    
    # Default stops
    default_sl_pct = Column(Float, default=5.0)  # Default stop loss %
    default_tp_pct = Column(Float, default=10.0)  # Default take profit %
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="risk_policy")


class TradingStrategy(Base):
    """Trading strategies for backtesting and automation."""
    __tablename__ = "trading_strategies"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    name = Column(String(100), nullable=False)
    description = Column(Text)
    config = Column(Text)  # JSON configuration
    
    # Performance metrics
    total_returns = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="trading_strategies")
    backtest_results = relationship("BacktestResult", back_populates="strategy")


class BacktestResult(Base):
    """Results from strategy backtesting."""
    __tablename__ = "backtest_results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id = Column(String, ForeignKey("trading_strategies.id"), nullable=False)
    
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Capital
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=False)
    
    # Performance
    total_return = Column(Float, nullable=False)
    total_trades = Column(Integer, nullable=False)
    winning_trades = Column(Integer, nullable=False)
    losing_trades = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)
    max_drawdown = Column(Float, nullable=False)
    sharpe_ratio = Column(Float)
    volatility = Column(Float)
    
    # Detailed data
    trades_data = Column(Text)  # JSON of all trades
    equity_curve = Column(Text)  # JSON of equity curve
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    strategy = relationship("TradingStrategy", back_populates="backtest_results")


class OCOGroup(Base):
    """One-Cancels-Other order groups."""
    __tablename__ = "oco_groups"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    
    # Relationships
    oco_links = relationship("OCOLink", back_populates="group")


class OCOLink(Base):
    """Links between OCO groups and orders."""
    __tablename__ = "oco_links"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(String, ForeignKey("oco_groups.id"), nullable=False)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    
    # Relationships
    group = relationship("OCOGroup", back_populates="oco_links")
    order = relationship("Order", back_populates="oco_links")


# ==================== MARKET DATA & PORTFOLIO TRACKING ====================

class CryptoAsset(Base):
    """Cryptocurrency asset information."""
    __tablename__ = "crypto_assets"

    id = Column(String, primary_key=True)  # CoinGecko ID
    symbol = Column(String(20), nullable=False, index=True)
    name = Column(String(100), nullable=False)

    # Current market data
    current_price_usd = Column(Float, default=0.0)
    market_cap = Column(Float, default=0.0)
    price_change_24h = Column(Float, default=0.0)
    price_change_percentage_24h = Column(Float, default=0.0)

    # Asset metadata
    image_url = Column(String)
    description = Column(Text)
    website_url = Column(String)

    # Trading info
    is_active = Column(Boolean, default=True)
    last_price_update = Column(DateTime, default=datetime.utcnow)

    # Relationships
    portfolio_holdings = relationship("PortfolioHolding", back_populates="asset")
    portfolio_transactions = relationship("PortfolioTransaction", back_populates="asset")


class UserPortfolio(Base):
    """User's crypto portfolio for tracking real/virtual investments."""
    __tablename__ = "user_portfolios"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)

    # Portfolio settings
    name = Column(String(100), default="My Portfolio")
    base_currency = Column(String(10), default="USD")
    is_public = Column(Boolean, default=False)

    # Performance metrics
    total_value_usd = Column(Float, default=0.0)
    total_invested = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    total_pnl_percentage = Column(Float, default=0.0)

    # Statistics
    total_transactions = Column(Integer, default=0)
    best_performing_asset = Column(String)
    worst_performing_asset = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    holdings = relationship("PortfolioHolding", back_populates="portfolio")
    transactions = relationship("PortfolioTransaction", back_populates="portfolio")


class PortfolioHolding(Base):
    """Individual crypto holdings in user portfolio."""
    __tablename__ = "portfolio_holdings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String, ForeignKey("user_portfolios.id"), nullable=False)
    asset_id = Column(String, ForeignKey("crypto_assets.id"), nullable=False)

    # Holding details
    quantity = Column(Float, nullable=False, default=0.0)
    average_buy_price = Column(Float, nullable=False, default=0.0)
    total_cost = Column(Float, nullable=False, default=0.0)

    # Current value
    current_price = Column(Float, default=0.0)
    current_value = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    unrealized_pnl_percentage = Column(Float, default=0.0)

    # Timestamps
    first_purchase_date = Column(DateTime)
    last_transaction_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    portfolio = relationship("UserPortfolio", back_populates="holdings")
    asset = relationship("CryptoAsset", back_populates="portfolio_holdings")


class PortfolioTransaction(Base):
    """Portfolio transaction history."""
    __tablename__ = "portfolio_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String, ForeignKey("user_portfolios.id"), nullable=False)
    asset_id = Column(String, ForeignKey("crypto_assets.id"), nullable=False)

    # Transaction details
    transaction_type = Column(String, nullable=False)  # BUY, SELL
    quantity = Column(Float, nullable=False)
    price_per_coin = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    fees = Column(Float, default=0.0)

    # GEMs integration
    gems_used = Column(Float, default=0.0)  # GEMs spent on virtual purchases
    is_virtual_transaction = Column(Boolean, default=True)  # True for GEM-based virtual trades

    # Metadata
    notes = Column(Text)
    source = Column(String, default="MANUAL")  # MANUAL, IMPORT, API

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    portfolio = relationship("UserPortfolio", back_populates="transactions")
    asset = relationship("CryptoAsset", back_populates="portfolio_transactions")


class MarketWatchlist(Base):
    """User's crypto watchlist."""
    __tablename__ = "market_watchlists"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    name = Column(String(100), default="My Watchlist")
    is_default = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    items = relationship("WatchlistItem", back_populates="watchlist")


class WatchlistItem(Base):
    """Individual items in watchlist."""
    __tablename__ = "watchlist_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    watchlist_id = Column(String, ForeignKey("market_watchlists.id"), nullable=False)
    asset_id = Column(String, ForeignKey("crypto_assets.id"), nullable=False)

    # Alert settings
    price_alert_high = Column(Float)
    price_alert_low = Column(Float)
    percentage_change_alert = Column(Float)

    added_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    watchlist = relationship("MarketWatchlist", back_populates="items")
    asset = relationship("CryptoAsset")


class PriceAlert(Base):
    """Price alerts for crypto assets."""
    __tablename__ = "price_alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    asset_id = Column(String, ForeignKey("crypto_assets.id"), nullable=False)

    # Alert configuration
    alert_type = Column(String, nullable=False)  # PRICE_ABOVE, PRICE_BELOW, PERCENT_CHANGE
    target_value = Column(Float, nullable=False)
    current_price_when_set = Column(Float)

    # Status
    is_active = Column(Boolean, default=True)
    triggered_at = Column(DateTime)
    trigger_price = Column(Float)

    # Notification
    notification_sent = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    asset = relationship("CryptoAsset")


# ==================== COMMUNITY & SOCIAL ENHANCEMENT ====================

class UserProfile(Base):
    """Extended user profile information."""
    __tablename__ = "user_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)

    # Profile customization
    profile_banner_url = Column(String)
    favorite_crypto = Column(String)
    trading_experience = Column(String)  # BEGINNER, INTERMEDIATE, ADVANCED, EXPERT
    investment_style = Column(String)  # CONSERVATIVE, BALANCED, AGGRESSIVE

    # Social settings
    show_portfolio = Column(Boolean, default=False)
    show_trading_stats = Column(Boolean, default=False)
    allow_portfolio_comparison = Column(Boolean, default=True)

    # Status and activity
    status_message = Column(String(200))
    last_seen = Column(DateTime)
    is_online = Column(Boolean, default=False)

    # Statistics
    total_friends = Column(Integer, default=0)
    profile_views = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")


class CommunityPost(Base):
    """Community posts and discussions."""
    __tablename__ = "community_posts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Post content
    title = Column(String(200))
    content = Column(Text, nullable=False)
    post_type = Column(String, default="GENERAL")  # GENERAL, ANALYSIS, QUESTION, ALERT

    # Metadata
    tags = Column(JSON, default=list)  # List of tags
    mentioned_assets = Column(JSON, default=list)  # List of crypto symbols mentioned

    # Engagement
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    views_count = Column(Integer, default=0)

    # Moderation
    is_deleted = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    comments = relationship("PostComment", back_populates="post")
    likes = relationship("PostLike", back_populates="post")


class PostComment(Base):
    """Comments on community posts."""
    __tablename__ = "post_comments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String, ForeignKey("community_posts.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    parent_comment_id = Column(String, ForeignKey("post_comments.id"))  # For nested comments

    content = Column(Text, nullable=False)
    likes_count = Column(Integer, default=0)

    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    post = relationship("CommunityPost", back_populates="comments")
    user = relationship("User")
    parent_comment = relationship("PostComment", remote_side=[id])


class PostLike(Base):
    """Likes on posts and comments."""
    __tablename__ = "post_likes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    post_id = Column(String, ForeignKey("community_posts.id"))
    comment_id = Column(String, ForeignKey("post_comments.id"))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    post = relationship("CommunityPost", back_populates="likes")


# ==================== MINI-GAMES SYSTEM MODELS ====================

class UserGameStats(Base):
    """Overall user statistics across all mini-games."""
    __tablename__ = "user_game_stats"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Overall Statistics
    total_games_played = Column(Integer, default=0)
    total_gems_earned = Column(Float, default=0.0)
    total_xp_earned = Column(Integer, default=0)
    total_time_played = Column(Float, default=0.0)  # seconds
    
    # Game Type Breakdown
    memory_games = Column(Integer, default=0)
    prediction_games = Column(Integer, default=0)
    puzzle_games = Column(Integer, default=0)
    math_games = Column(Integer, default=0)
    wheel_spins = Column(Integer, default=0)
    
    # Achievement Tracking
    perfect_games = Column(Integer, default=0)  # Games completed with 100% accuracy
    speed_records = Column(Integer, default=0)  # Games completed in record time
    streak_records = Column(Integer, default=0)  # Best streaks achieved
    
    # Skill Ratings (1-100)
    memory_skill = Column(Float, default=50.0)
    math_skill = Column(Float, default=50.0)
    puzzle_skill = Column(Float, default=50.0)
    prediction_skill = Column(Float, default=50.0)
    
    # Favorites and Preferences
    favorite_game = Column(String)
    preferred_difficulty = Column(String, default="MEDIUM")
    
    # Daily/Weekly Progress
    daily_games_played = Column(Integer, default=0)
    last_daily_reset = Column(DateTime)
    weekly_gems_earned = Column(Float, default=0.0)
    last_weekly_reset = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="mini_game_stats")


class UserChallengeProgress(Base):
    """Track user progress on daily challenges."""
    __tablename__ = "user_challenge_progress"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    challenge_id = Column(String, ForeignKey("daily_challenges.id"), nullable=False)
    
    # Progress
    current_progress = Column(Float, default=0.0)
    target_value = Column(Float, nullable=False)
    is_completed = Column(Boolean, default=False)
    completion_time = Column(DateTime)
    
    # Rewards
    gems_earned = Column(Float, default=0.0)
    xp_earned = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    challenge = relationship("DailyChallenge", back_populates="user_progress")


class DailyChallenge(Base):
    """Daily challenges for mini-games."""
    __tablename__ = "daily_challenges"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    challenge_date = Column(DateTime, nullable=False)
    
    # Challenge Configuration
    game_type = Column(String, nullable=False)  # Which mini-game
    challenge_type = Column(String, nullable=False)  # Type of challenge
    target_value = Column(Float, nullable=False)  # Target to achieve
    description = Column(Text, nullable=False)
    
    # Rewards
    gem_reward = Column(Float, default=100.0)
    xp_reward = Column(Integer, default=50)
    bonus_multiplier = Column(Float, default=1.0)
    
    # Status
    is_active = Column(Boolean, default=True)
    participants = Column(Integer, default=0)
    completions = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_progress = relationship("UserChallengeProgress", back_populates="challenge")
