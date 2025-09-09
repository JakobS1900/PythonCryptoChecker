"""
Virtual currency and reward system models for gamification platform.
All currencies and rewards are virtual - no real money involved.
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class CurrencyType(Enum):
    """Types of virtual currencies in the system."""
    GEM_COINS = "GEM_COINS"          # Primary earned currency
    EXPERIENCE_POINTS = "XP"          # Progression currency
    VIRTUAL_CRYPTO = "VIRTUAL_CRYPTO" # Virtual crypto holdings
    PREMIUM_TOKENS = "PREMIUM"        # Special event currency


class ItemRarity(Enum):
    """Rarity levels for collectible items."""
    COMMON = "COMMON"         # Gray - Basic items (70% drop rate)
    UNCOMMON = "UNCOMMON"     # Green - Better rewards (20% drop rate) 
    RARE = "RARE"             # Blue - Valuable items (8% drop rate)
    EPIC = "EPIC"             # Purple - Premium items (1.8% drop rate)
    LEGENDARY = "LEGENDARY"   # Gold - Ultra-rare items (0.2% drop rate)


class ItemType(Enum):
    """Types of collectible items."""
    TRADING_CARD = "TRADING_CARD"     # Crypto-themed collectible cards
    COSMETIC = "COSMETIC"             # Avatar customizations, themes
    TROPHY = "TROPHY"                 # Achievement rewards
    CONSUMABLE = "CONSUMABLE"         # Temporary bonuses
    SPECIAL = "SPECIAL"               # Event-specific items


class RewardType(Enum):
    """Types of reward triggers."""
    DAILY_LOGIN = "DAILY_LOGIN"       # Daily login bonuses
    GAME_WIN = "GAME_WIN"             # Winning roulette games
    ACHIEVEMENT = "ACHIEVEMENT"        # Achievement unlocks
    LEVEL_UP = "LEVEL_UP"             # Level progression rewards
    STREAK = "STREAK"                 # Consecutive activity streaks
    EVENT = "EVENT"                   # Special event rewards


class VirtualWallet(Base):
    """User's virtual wallet containing all currencies."""
    __tablename__ = "virtual_wallets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Primary currencies
    gem_coins = Column(Float, default=1000.0)  # Starting bonus
    experience_points = Column(Integer, default=0)
    premium_tokens = Column(Integer, default=0)
    
    # Player progression
    level = Column(Integer, default=1)
    total_xp_earned = Column(Integer, default=0)
    
    # Statistics
    total_gems_earned = Column(Float, default=1000.0)  # Include starting bonus
    total_gems_spent = Column(Float, default=0.0)
    games_played = Column(Integer, default=0)
    games_won = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="wallet")
    virtual_crypto_holdings = relationship("VirtualCryptoHolding", back_populates="wallet")
    transaction_history = relationship("VirtualTransaction", back_populates="wallet")


class VirtualCryptoHolding(Base):
    """Virtual cryptocurrency holdings that mirror real crypto prices."""
    __tablename__ = "virtual_crypto_holdings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_id = Column(String, ForeignKey("virtual_wallets.id"), nullable=False)
    
    crypto_id = Column(String, nullable=False)      # e.g., "bitcoin"
    crypto_symbol = Column(String, nullable=False)  # e.g., "BTC"
    virtual_amount = Column(Float, nullable=False)  # Amount of virtual crypto owned
    
    # Purchase tracking
    total_gems_invested = Column(Float, default=0.0)  # Total GEM coins spent
    average_buy_price = Column(Float, default=0.0)    # Average purchase price in USD
    
    # Performance tracking
    unrealized_pnl = Column(Float, default=0.0)      # Current profit/loss
    realized_pnl = Column(Float, default=0.0)        # From sales
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    wallet = relationship("VirtualWallet", back_populates="virtual_crypto_holdings")


class CollectibleItem(Base):
    """Collectible items that users can earn and trade."""
    __tablename__ = "collectible_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    name = Column(String(100), nullable=False)
    description = Column(Text)
    item_type = Column(String, nullable=False)  # ItemType enum
    rarity = Column(String, nullable=False)     # ItemRarity enum
    
    # Visual properties
    image_url = Column(String)
    color_theme = Column(String)  # Hex color for rarity
    animation_type = Column(String)  # For special effects
    
    # Game properties
    gem_value = Column(Float, default=0.0)      # Worth in GEM coins
    is_tradeable = Column(Boolean, default=True)
    is_consumable = Column(Boolean, default=False)
    effect_description = Column(Text)  # What the item does
    
    # Metadata
    crypto_theme = Column(String)  # Associated cryptocurrency
    release_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user_items = relationship("UserInventory", back_populates="item")


class UserInventory(Base):
    """User's inventory of collectible items."""
    __tablename__ = "user_inventory"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    item_id = Column(String, ForeignKey("collectible_items.id"), nullable=False)
    
    quantity = Column(Integer, default=1)
    acquired_at = Column(DateTime, default=datetime.utcnow)
    acquisition_method = Column(String)  # How they got it (reward, trade, etc.)
    
    # Item state
    is_equipped = Column(Boolean, default=False)  # For cosmetics
    is_favorite = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="inventory")
    item = relationship("CollectibleItem", back_populates="user_items")


class VirtualTransaction(Base):
    """Transaction history for all virtual currency activities."""
    __tablename__ = "virtual_transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_id = Column(String, ForeignKey("virtual_wallets.id"), nullable=False)
    
    transaction_type = Column(String, nullable=False)  # EARN, SPEND, TRADE, etc.
    currency_type = Column(String, nullable=False)     # CurrencyType enum
    amount = Column(Float, nullable=False)              # Positive for gain, negative for spend
    
    # Context
    source = Column(String)           # Where it came from (game_win, daily_login, etc.)
    description = Column(Text)        # Human-readable description
    reference_id = Column(String)     # Link to game session, achievement, etc.
    
    # Balance tracking
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    wallet = relationship("VirtualWallet", back_populates="transaction_history")


class ActiveEffect(Base):
    """Active consumable effects applied to a user (buffs)."""
    __tablename__ = "active_effects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
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


class DailyReward(Base):
    """Daily login reward tracking."""
    __tablename__ = "daily_rewards"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Streak tracking
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_claim_date = Column(DateTime)
    
    # Reward progression (increases with streak)
    next_reward_gems = Column(Float, default=50.0)
    next_reward_xp = Column(Integer, default=25)
    
    # Statistics
    total_logins = Column(Integer, default=0)
    total_gems_from_daily = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


@dataclass
class RewardBundle:
    """Data class for reward calculations."""
    gem_coins: float = 0.0
    experience_points: int = 0
    premium_tokens: int = 0
    items: List[Dict[str, Any]] = None
    description: str = ""
    
    def __post_init__(self):
        if self.items is None:
            self.items = []


class VirtualEconomyConstants:
    """Constants for balancing the virtual economy."""
    
    # Starting balances
    STARTING_GEM_COINS = 1000.0
    STARTING_XP = 0
    STARTING_LEVEL = 1
    
    # Daily login rewards
    BASE_DAILY_GEMS = 50.0
    BASE_DAILY_XP = 25
    STREAK_MULTIPLIER = 0.1  # 10% bonus per day in streak
    MAX_STREAK_BONUS = 2.0   # Cap at 200% bonus (20 day streak)
    
    # Game rewards
    ROULETTE_WIN_BASE_GEMS = 25.0
    ROULETTE_WIN_BASE_XP = 15
    WIN_STREAK_BONUS = 0.2   # 20% bonus per consecutive win
    
    # Level progression
    XP_PER_LEVEL_BASE = 100
    XP_PER_LEVEL_SCALING = 1.5  # Each level needs 50% more XP
    LEVEL_UP_GEM_BONUS = 100.0
    
    # Item drop rates by rarity
    DROP_RATES = {
        ItemRarity.COMMON: 0.70,
        ItemRarity.UNCOMMON: 0.20,
        ItemRarity.RARE: 0.08,
        ItemRarity.EPIC: 0.018,
        ItemRarity.LEGENDARY: 0.002
    }
    
    # Item values by rarity
    ITEM_GEM_VALUES = {
        ItemRarity.COMMON: 10.0,
        ItemRarity.UNCOMMON: 50.0,
        ItemRarity.RARE: 200.0,
        ItemRarity.EPIC: 1000.0,
        ItemRarity.LEGENDARY: 5000.0
    }
    
    # Virtual crypto trading
    MIN_CRYPTO_PURCHASE = 1.0    # Minimum GEM coins for crypto purchase
    CRYPTO_TRADE_FEE = 0.01      # 1% fee in GEM coins for virtual trades
    
    # Achievement rewards
    ACHIEVEMENT_REWARDS = {
        "first_spin": RewardBundle(gem_coins=100, experience_points=50, description="Welcome bonus!"),
        "win_streak_5": RewardBundle(gem_coins=250, experience_points=100, description="Hot streak!"),
        "crypto_collector": RewardBundle(gem_coins=500, experience_points=200, description="Crypto expert!"),
        "daily_warrior": RewardBundle(gem_coins=1000, premium_tokens=1, description="Dedication pays off!")
    }
