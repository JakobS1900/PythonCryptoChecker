"""
Database models for CryptoChecker Version3.
Focused, clean models for crypto tracking and gaming.
"""

import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from passlib.context import CryptContext

Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bot usernames and bios for realistic character generation
BOT_PROFILE_DATA = [
    ("bob", "Beer lover from Merica Town"),
    ("bob joe", "Dallas native, Geography Grad"),
    ("billybob", "Coffee Addict, Dog Person"),
    ("dogbob", "Beer Lover, Gym Rat"),
    ("cryptojoe", "Movie Buff, Tech Geek"),
    ("cryptobob", "Foodie, Music Lover"),
    ("bitcoinbob", "Sports Fan, Night Owl"),
    ("satoshisbet", "Yield Farmer, DeFi Native"),
    ("hodlbob", "DiamondHands, Crypto Trader"),
    ("hodlbilly", "PaperHands, Day Trader"),
    ("moonbob", "Bear Market Survivor"),
    ("nimblebob", "NFT Collector, All Time High believer"),
    ("cypherpunk", "Privacy Maxwell, Bitcoin Cypherpunk"),
    ("diamondjoe", "Decentralize or Die, Self Custody"),
    ("hodljr", "Gold Bug, Fiat Refugee"),
    ("cryptoking", "Merchant of Venice, From Silk Road to Litecoin"),
    ("gemhunter", "Night Owl, Hedges & APEs"),
    ("luckycharm", "Early Bird, Call Signals expert"),
    ("diamondhands", "Put Signals wizard, Sport Fan"),
    ("paperpro", "Tech Geek turned Crypto Trader"),
    ("hodlmaxwell", "Education Over Regulation advocate"),
    ("bitbro", "Privacy for the People and Keys Not Your Coins")
]

# Bot personality enum
class BotPersonalityType(Enum):
    """Types of bot personalities for gambling behavior."""
    CONSERVATIVE = "CONSERVATIVE"      # Small bets, careful play, strategic bets
    AGGRESSIVE = "AGGRESSIVE"          # Large bets, willing to risk more, high variance bets
    TREND_FOLLOWER = "TREND_FOLLOWER"  # Follows recent wins/losses
    OPPORTUNISTIC = "OPPORTUNISTIC"    # Bets on favorites, emotional play
    PREDICTABLE_GAMBLER = "PREDICTABLE_GAMBLER"  # Patterns, cycling through bets
    HIGHROLLER = "HIGHROLLER"        # Very large bets, occasionally plays to maintain status
    TIMID = "TIMID"                    # Very small bets, rarely participates

# ==================== ENUMS ====================

class UserRole(Enum):
    """User roles for access control."""
    PLAYER = "PLAYER"
    VIP = "VIP"
    ADMIN = "ADMIN"

class TransactionType(Enum):
    """Types of GEM transactions."""
    DEPOSIT = "DEPOSIT"           # Initial GEM deposit
    WITHDRAWAL = "WITHDRAWAL"     # GEM withdrawal
    BET_PLACED = "BET_PLACED"     # Roulette bet placed
    BET_WON = "BET_WON"          # Roulette bet won
    BET_LOST = "BET_LOST"        # Roulette bet lost
    BONUS = "BONUS"              # Bonus GEM reward
    TRANSFER = "TRANSFER"        # Transfer between users
    CRYPTO_BUY = "CRYPTO_BUY"    # Buy cryptocurrency with GEMs
    CRYPTO_SELL = "CRYPTO_SELL"  # Sell cryptocurrency for GEMs
    DAILY_BONUS = "DAILY_BONUS"  # Daily bonus claim
    ACHIEVEMENT = "ACHIEVEMENT"  # Achievement reward
    EMERGENCY_GEM = "EMERGENCY_GEM"  # Emergency GEM from tasks
    MINI_GAME = "MINI_GAME"      # Mini-game reward

class BetType(Enum):
    """Types of roulette bets."""
    SINGLE_NUMBER = "SINGLE_NUMBER"     # Bet on specific number (0-36)
    RED_BLACK = "RED_BLACK"             # Bet on red or black
    EVEN_ODD = "EVEN_ODD"              # Bet on even/odd
    HIGH_LOW = "HIGH_LOW"              # Bet on high (19-36) or low (1-18)
    CRYPTO_CATEGORY = "CRYPTO_CATEGORY" # Bet on crypto category

class GameStatus(Enum):
    """Status of game sessions."""
    ACTIVE = "ACTIVE"         # Game in progress
    COMPLETED = "COMPLETED"   # Game finished
    CANCELLED = "CANCELLED"   # Game cancelled

class AchievementType(Enum):
    """Types of achievements for GEM rewards."""
    FIRST_BET = "FIRST_BET"           # Place first bet
    WIN_STREAK = "WIN_STREAK"         # Win multiple rounds in a row
    BIG_WIN = "BIG_WIN"              # Win large amount in single round
    TOTAL_BETS = "TOTAL_BETS"         # Place X number of bets
    TOTAL_WAGERED = "TOTAL_WAGERED"   # Wager X total amount
    PLAY_TIME = "PLAY_TIME"           # Play for X minutes
    LUCKY_NUMBER = "LUCKY_NUMBER"     # Hit specific numbers
    COLOR_STREAK = "COLOR_STREAK"     # Win color bets in succession
    HIGH_ROLLER = "HIGH_ROLLER"       # Place high-value bets
    COMEBACK = "COMEBACK"             # Win after losing streak

class RoundPhase(Enum):
    """Phases of a roulette round (server-managed round system)."""
    BETTING = "betting"       # Players can place bets
    SPINNING = "spinning"     # Wheel is spinning, bets locked
    RESULTS = "results"       # Displaying results, calculating payouts
    CLEANUP = "cleanup"       # Round completed, preparing for next

# ==================== MODELS ====================

class User(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.PLAYER.value)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    # Profile fields
    avatar_url = Column(String(500), nullable=True)  # Avatar image URL or path
    bio = Column(String(500), nullable=True)  # User bio/description
    profile_theme = Column(String(50), default='purple', nullable=True)  # Profile card theme color
    # Bot-specific fields
    is_bot = Column(Boolean, default=False, nullable=False)  # New field to identify bots
    bot_personality = Column(String(30), nullable=True)      # Bot personality type if applicable

    # Relationships
    wallet = relationship("Wallet", back_populates="user", uselist=False)
    transactions = relationship("Transaction", back_populates="user")
    game_sessions = relationship("GameSession", back_populates="user")
    portfolio_holdings = relationship("PortfolioHolding", back_populates="user")

    def set_password(self, password: str):
        """Hash and set password."""
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(password, self.password_hash)

    def to_dict(self):
        """Convert user to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "profile_theme": self.profile_theme,
            "is_bot": self.is_bot,
            "bot_personality": self.bot_personality
        }

class Wallet(Base):
    """User wallet for GEM balance."""
    __tablename__ = "wallets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    gem_balance = Column(Float, default=0.0)
    total_deposited = Column(Float, default=0.0)
    total_withdrawn = Column(Float, default=0.0)
    total_wagered = Column(Float, default=0.0)
    total_won = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="wallet")

    def to_dict(self):
        """Convert wallet to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "gem_balance": self.gem_balance,
            "total_deposited": self.total_deposited,
            "total_withdrawn": self.total_withdrawn,
            "total_wagered": self.total_wagered,
            "total_won": self.total_won,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Transaction(Base):
    """GEM transaction history."""
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    transaction_type = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    description = Column(Text)
    game_session_id = Column(String, ForeignKey("game_sessions.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="transactions")
    game_session = relationship("GameSession", back_populates="transactions")

    def to_dict(self):
        """Convert transaction to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "transaction_type": self.transaction_type,
            "amount": self.amount,
            "balance_before": self.balance_before,
            "balance_after": self.balance_after,
            "description": self.description,
            "game_session_id": self.game_session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class GameSession(Base):
    """Roulette game session."""
    __tablename__ = "game_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default=GameStatus.ACTIVE.value)

    # Provably fair data
    server_seed = Column(String(64), nullable=False)
    server_seed_hash = Column(String(64), nullable=False)
    client_seed = Column(String(64), nullable=False)
    nonce = Column(Integer, default=0)

    # Game results
    winning_number = Column(Integer, nullable=True)  # 0-36
    winning_crypto = Column(String(20), nullable=True)  # BTC, ETH, etc.
    winning_color = Column(String(10), nullable=True)  # red, black, green

    # Session metadata
    total_bet = Column(Float, default=0.0)
    total_won = Column(Float, default=0.0)
    total_lost = Column(Float, default=0.0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="game_sessions")
    bets = relationship("GameBet", back_populates="game_session")
    transactions = relationship("Transaction", back_populates="game_session")

    def generate_result(self) -> dict:
        """Generate provably fair game result."""
        # Combine seeds and nonce for randomness
        combined = f"{self.server_seed}{self.client_seed}{self.nonce}"
        hash_result = hashlib.sha256(combined.encode()).hexdigest()

        # Convert hash to number 0-36
        number = int(hash_result[:8], 16) % 37

        # Determine crypto and color based on number
        crypto_wheel = [
            "BTC", "ETH", "BNB", "ADA", "SOL", "XRP", "DOT", "DOGE", "AVAX", "SHIB",
            "MATIC", "UNI", "LINK", "LTC", "ATOM", "BCH", "FIL", "TRX", "ETC", "XLM",
            "THETA", "VET", "ALGO", "ICP", "HBAR", "FLOW", "MANA", "SAND", "CRV", "COMP",
            "YFI", "SUSHI", "SNX", "1INCH", "BAL", "REN", "ZRX"
        ]

        if number == 0:
            crypto = "BTC"  # Bitcoin is always 0 (green)
            color = "green"
        else:
            crypto = crypto_wheel[number - 1]
            color = "red" if number % 2 == 1 else "black"

        return {
            "number": number,
            "crypto": crypto,
            "color": color
        }

    def to_dict(self):
        """Convert game session to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "status": self.status,
            "server_seed_hash": self.server_seed_hash,
            "client_seed": self.client_seed,
            "nonce": self.nonce,
            "winning_number": self.winning_number,
            "winning_crypto": self.winning_crypto,
            "winning_color": self.winning_color,
            "total_bet": self.total_bet,
            "total_won": self.total_won,
            "total_lost": self.total_lost,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

class RouletteRound(Base):
    """
    Server-managed roulette round.
    Represents a single round of roulette that all players participate in.
    """
    __tablename__ = "roulette_rounds"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    round_number = Column(Integer, autoincrement=True, nullable=False, unique=True)
    phase = Column(String(20), nullable=False, default=RoundPhase.BETTING.value)

    # Timing
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    betting_ends_at = Column(DateTime)

    # Outcome (NULL until wheel spins)
    outcome_number = Column(Integer)  # 0-36
    outcome_color = Column(String(10))  # red/black/green
    outcome_crypto = Column(String(10))  # BTC, ETH, etc.

    # Who triggered the spin
    triggered_by = Column(String(36), ForeignKey('users.id'))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    bets = relationship("GameBet", back_populates="round")
    trigger_user = relationship("User", foreign_keys=[triggered_by])

    def to_dict(self):
        """Convert round to dictionary."""
        return {
            "id": self.id,
            "round_number": self.round_number,
            "phase": self.phase,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "betting_ends_at": self.betting_ends_at.isoformat() if self.betting_ends_at else None,
            "outcome": {
                "number": self.outcome_number,
                "color": self.outcome_color,
                "crypto": self.outcome_crypto
            } if self.outcome_number is not None else None,
            "triggered_by": self.triggered_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

class GameBet(Base):
    """Individual bet within a game session."""
    __tablename__ = "game_bets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    game_session_id = Column(String, ForeignKey("game_sessions.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    round_id = Column(String(36), ForeignKey("roulette_rounds.id"))  # NEW: Link to round

    # Bet details
    bet_type = Column(String(20), nullable=False)
    bet_value = Column(String(50), nullable=False)  # The specific value bet on
    amount = Column(Float, nullable=False)

    # Results
    is_winner = Column(Boolean, nullable=True)
    payout_multiplier = Column(Float, nullable=True)
    payout_amount = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    game_session = relationship("GameSession", back_populates="bets")
    user = relationship("User")
    round = relationship("RouletteRound", back_populates="bets")  # NEW: Round relationship

    def calculate_payout(self, winning_number: int, winning_color: str, winning_crypto: str) -> tuple:
        """Calculate if bet wins and payout amount."""
        is_winner = False
        multiplier = 0.0

        if self.bet_type == BetType.SINGLE_NUMBER.value:
            if int(self.bet_value) == winning_number:
                is_winner = True
                multiplier = 35.0  # 35:1 payout for single number

        elif self.bet_type == BetType.RED_BLACK.value:
            if winning_number != 0 and self.bet_value.lower() == winning_color.lower():
                is_winner = True
                multiplier = 1.0  # 1:1 payout for color

        elif self.bet_type == BetType.EVEN_ODD.value:
            if winning_number != 0:
                is_even = winning_number % 2 == 0
                if (self.bet_value.lower() == "even" and is_even) or \
                   (self.bet_value.lower() == "odd" and not is_even):
                    is_winner = True
                    multiplier = 1.0  # 1:1 payout for even/odd

        elif self.bet_type == BetType.HIGH_LOW.value:
            if winning_number != 0:
                is_high = winning_number >= 19
                if (self.bet_value.lower() == "high" and is_high) or \
                   (self.bet_value.lower() == "low" and not is_high):
                    is_winner = True
                    multiplier = 1.0  # 1:1 payout for high/low

        payout = self.amount * multiplier if is_winner else 0.0
        return is_winner, multiplier, payout

    def to_dict(self):
        """Convert bet to dictionary."""
        return {
            "id": self.id,
            "game_session_id": self.game_session_id,
            "user_id": self.user_id,
            "bet_type": self.bet_type,
            "bet_value": self.bet_value,
            "amount": self.amount,
            "is_winner": self.is_winner,
            "payout_multiplier": self.payout_multiplier,
            "payout_amount": self.payout_amount,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

# Additional models for full functionality (CryptoCurrency, PortfolioHolding, DailyBonus, etc.)
# These are needed for the complete system but are not directly involved in the bot system

class CryptoCurrency(Base):
    """Cryptocurrency information for price tracking."""
    __tablename__ = "cryptocurrencies"

    id = Column(String, primary_key=True)  # coingecko id
    symbol = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    current_price_usd = Column(Float, nullable=True)
    market_cap = Column(Float, nullable=True)
    volume_24h = Column(Float, nullable=True)
    price_change_24h = Column(Float, nullable=True)
    price_change_percentage_24h = Column(Float, nullable=True)
    image = Column(String(500), nullable=True)  # CoinGecko image URL
    last_updated = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        """Convert cryptocurrency to dictionary."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "current_price_usd": self.current_price_usd,
            "market_cap": self.market_cap,
            "volume_24h": self.volume_24h,
            "price_change_24h": self.price_change_24h,
            "price_change_percentage_24h": self.price_change_percentage_24h,
            "image": self.image,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "is_active": self.is_active
        }

class PortfolioHolding(Base):
    """User's cryptocurrency holdings in their portfolio."""
    __tablename__ = "portfolio_holdings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    crypto_id = Column(String, ForeignKey("cryptocurrencies.id"), nullable=False)
    quantity = Column(Float, default=0.0)  # Amount of crypto owned
    average_buy_price_gem = Column(Float, default=0.0)  # Average buy price in GEMs
    total_invested_gem = Column(Float, default=0.0)  # Total GEMs invested
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="portfolio_holdings")
    cryptocurrency = relationship("CryptoCurrency")

class DailyBonus(Base):
    """Daily bonus claims for users."""
    __tablename__ = "daily_bonuses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    claim_date = Column(DateTime, default=datetime.utcnow)
    bonus_amount = Column(Float, nullable=False)  # GEM amount awarded
    consecutive_days = Column(Integer, default=1)  # Streak counter
    last_claim_date = Column(DateTime, nullable=True)  # Previous claim for streak calculation
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="daily_bonuses")

class Achievement(Base):
    """Achievement definitions and user progress tracking."""
    __tablename__ = "achievements"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    achievement_type = Column(String(50), nullable=False)  # AchievementType enum
    target_value = Column(Float, nullable=False)  # Target number to achieve
    reward_amount = Column(Float, nullable=False)  # GEM reward
    icon = Column(String(50), default="trophy")  # FontAwesome icon name
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user_achievements = relationship("UserAchievement", back_populates="achievement")

class UserAchievement(Base):
    """User progress and completion of achievements."""
    __tablename__ = "user_achievements"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(String, ForeignKey("achievements.id"), nullable=False)
    current_progress = Column(Float, default=0.0)  # Current progress towards target
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    reward_claimed = Column(Boolean, default=False)
    reward_claimed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="user_achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")

class EmergencyTask(Base):
    """Emergency GEM earning tasks for low balance users."""
    __tablename__ = "emergency_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    task_type = Column(String(50), nullable=False)  # 'watch_ad', 'mini_game', 'survey', etc.
    reward_amount = Column(Float, nullable=False)  # GEM reward
    cooldown_minutes = Column(Integer, default=60)  # Cooldown between completions
    max_completions_per_day = Column(Integer, default=3)  # Daily limit
    min_balance_threshold = Column(Float, default=50)  # Only show when balance below this
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user_completions = relationship("UserEmergencyTask", back_populates="task")

class UserEmergencyTask(Base):
    """User completion tracking for emergency tasks."""
    __tablename__ = "user_emergency_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    task_id = Column(String, ForeignKey("emergency_tasks.id"), nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow)
    reward_claimed = Column(Boolean, default=True)  # Auto-claimed for emergency tasks
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="emergency_task_completions")
    task = relationship("EmergencyTask", back_populates="user_completions")
