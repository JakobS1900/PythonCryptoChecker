"""
Gaming models for crypto-themed roulette system.
Provably fair game mechanics with virtual betting.
"""

import uuid
import hashlib
import secrets
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class GameType(Enum):
    """Types of roulette games available."""
    CLASSIC_CRYPTO = "CLASSIC_CRYPTO"           # Traditional roulette with crypto themes
    PRICE_PREDICTION = "PRICE_PREDICTION"       # Bet on crypto price movements
    VOLATILITY_ROULETTE = "VOLATILITY_ROULETTE" # High/low volatility betting
    TOURNAMENT = "TOURNAMENT"                   # Tournament mode


class BetType(Enum):
    """Types of bets in roulette."""
    # Crypto-specific bets
    SINGLE_CRYPTO = "SINGLE_CRYPTO"           # Bet on specific cryptocurrency
    CRYPTO_COLOR = "CRYPTO_COLOR"             # Green (bullish) or Red (bearish)
    CRYPTO_CATEGORY = "CRYPTO_CATEGORY"       # DeFi, Gaming, Layer 1, etc.
    
    # Traditional roulette bets adapted
    EVEN_ODD = "EVEN_ODD"                     # Even or odd numbers
    HIGH_LOW = "HIGH_LOW"                     # 1-18 (low) or 19-36 (high)
    DOZEN = "DOZEN"                           # First, second, or third dozen
    COLUMN = "COLUMN"                         # Column betting


class GameStatus(Enum):
    """Status of game sessions."""
    ACTIVE = "ACTIVE"         # Game in progress, accepting bets
    SPINNING = "SPINNING"     # Wheel spinning, no more bets
    COMPLETED = "COMPLETED"   # Game finished
    CANCELLED = "CANCELLED"   # Game cancelled


class CryptoRouletteWheel:
    """Configuration for crypto-themed roulette wheel."""
    
    # 37 slots: 0 (Bitcoin) + 36 crypto positions
    WHEEL_POSITIONS = {
        0: {"crypto": "bitcoin", "symbol": "BTC", "color": "gold", "category": "store_of_value"},
        1: {"crypto": "ethereum", "symbol": "ETH", "color": "blue", "category": "smart_contracts"},
        2: {"crypto": "cardano", "symbol": "ADA", "color": "blue", "category": "smart_contracts"},
        3: {"crypto": "solana", "symbol": "SOL", "color": "purple", "category": "smart_contracts"},
        4: {"crypto": "dogecoin", "symbol": "DOGE", "color": "yellow", "category": "meme"},
        5: {"crypto": "polygon", "symbol": "MATIC", "color": "purple", "category": "layer2"},
        6: {"crypto": "chainlink", "symbol": "LINK", "color": "blue", "category": "oracle"},
        7: {"crypto": "litecoin", "symbol": "LTC", "color": "silver", "category": "payment"},
        8: {"crypto": "avalanche", "symbol": "AVAX", "color": "red", "category": "smart_contracts"},
        9: {"crypto": "polkadot", "symbol": "DOT", "color": "pink", "category": "interoperability"},
        10: {"crypto": "cosmos", "symbol": "ATOM", "color": "blue", "category": "interoperability"},
        11: {"crypto": "algorand", "symbol": "ALGO", "color": "black", "category": "smart_contracts"},
        12: {"crypto": "stellar", "symbol": "XLM", "color": "blue", "category": "payment"},
        13: {"crypto": "vechain", "symbol": "VET", "color": "blue", "category": "supply_chain"},
        14: {"crypto": "tezos", "symbol": "XTZ", "color": "blue", "category": "smart_contracts"},
        15: {"crypto": "monero", "symbol": "XMR", "color": "orange", "category": "privacy"},
        16: {"crypto": "zcash", "symbol": "ZEC", "color": "yellow", "category": "privacy"},
        17: {"crypto": "dash", "symbol": "DASH", "color": "blue", "category": "payment"},
        18: {"crypto": "decred", "symbol": "DCR", "color": "teal", "category": "governance"},
        19: {"crypto": "uniswap", "symbol": "UNI", "color": "pink", "category": "defi"},
        20: {"crypto": "sushiswap", "symbol": "SUSHI", "color": "blue", "category": "defi"},
        21: {"crypto": "compound", "symbol": "COMP", "color": "green", "category": "defi"},
        22: {"crypto": "aave", "symbol": "AAVE", "color": "purple", "category": "defi"},
        23: {"crypto": "curve-dao-token", "symbol": "CRV", "color": "yellow", "category": "defi"},
        24: {"crypto": "yearn-finance", "symbol": "YFI", "color": "blue", "category": "defi"},
        25: {"crypto": "the-sandbox", "symbol": "SAND", "color": "blue", "category": "gaming"},
        26: {"crypto": "decentraland", "symbol": "MANA", "color": "orange", "category": "gaming"},
        27: {"crypto": "axie-infinity", "symbol": "AXS", "color": "blue", "category": "gaming"},
        28: {"crypto": "enjincoin", "symbol": "ENJ", "color": "purple", "category": "gaming"},
        29: {"crypto": "gala", "symbol": "GALA", "color": "black", "category": "gaming"},
        30: {"crypto": "apecoin", "symbol": "APE", "color": "blue", "category": "nft"},
        31: {"crypto": "theta-token", "symbol": "THETA", "color": "blue", "category": "media"},
        32: {"crypto": "filecoin", "symbol": "FIL", "color": "blue", "category": "storage"},
        33: {"crypto": "arweave", "symbol": "AR", "color": "black", "category": "storage"},
        34: {"crypto": "helium", "symbol": "HNT", "color": "blue", "category": "iot"},
        35: {"crypto": "the-graph", "symbol": "GRT", "color": "purple", "category": "indexing"},
        36: {"crypto": "basic-attention-token", "symbol": "BAT", "color": "orange", "category": "advertising"}
    }
    
    # Color mappings for traditional betting
    GREEN_NUMBERS = [0]  # Bitcoin is the "green" (house edge)
    RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
    BLACK_NUMBERS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
    
    @classmethod
    def get_winning_bets(cls, winning_number: int) -> Dict[str, Any]:
        """Get all winning bet types for a winning number."""
        if winning_number not in cls.WHEEL_POSITIONS:
            raise ValueError(f"Invalid winning number: {winning_number}")
        
        position = cls.WHEEL_POSITIONS[winning_number]
        
        return {
            "single_crypto": position["crypto"],
            "crypto_symbol": position["symbol"],
            "color": "green" if winning_number == 0 else ("red" if winning_number in cls.RED_NUMBERS else "black"),
            "category": position["category"],
            "even_odd": "even" if winning_number % 2 == 0 and winning_number != 0 else "odd" if winning_number != 0 else None,
            "high_low": "high" if winning_number >= 19 else "low" if winning_number >= 1 else None,
            "dozen": "first" if 1 <= winning_number <= 12 else "second" if 13 <= winning_number <= 24 else "third" if 25 <= winning_number <= 36 else None,
            "column": ((winning_number - 1) % 3) + 1 if winning_number > 0 else None
        }


class GameSession(Base):
    """Individual game session with provably fair mechanics."""
    __tablename__ = "game_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Game configuration
    game_type = Column(String, default=GameType.CLASSIC_CRYPTO.value)
    status = Column(String, default=GameStatus.ACTIVE.value)
    
    # Provably fair system
    server_seed = Column(String, nullable=False)  # Secret until revealed
    server_seed_hash = Column(String, nullable=False)  # Hash shown to player
    client_seed = Column(String, nullable=False)  # Player's input
    nonce = Column(Integer, default=1)  # Incremental counter
    
    # Game results
    winning_number = Column(Integer)  # 0-36
    winning_crypto = Column(String)   # Cryptocurrency that won
    spin_hash = Column(String)        # Hash used for result generation
    
    # Betting and results
    total_bet_amount = Column(Float, default=0.0)
    total_winnings = Column(Float, default=0.0)
    house_edge_amount = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    spin_time = Column(DateTime)      # When wheel was spun
    completed_at = Column(DateTime)   # When results were finalized
    
    # Relationships
    user = relationship("User")
    bets = relationship("GameBet", back_populates="game_session", cascade="all, delete-orphan")
    
    def generate_result(self) -> int:
        """Generate provably fair result using enhanced cryptographic hashing."""
        if self.status != GameStatus.ACTIVE:
            raise ValueError("Game session is not active")
        
        # Generate enhanced result
        winning_number, hash_result = EnhancedProvablyFairGenerator.generate_enhanced_result(
            self.server_seed, self.client_seed, self.nonce
        )
        
        # Store results
        self.winning_number = winning_number
        self.spin_hash = hash_result
        self.winning_crypto = CryptoRouletteWheel.WHEEL_POSITIONS[winning_number]["crypto"]
        self.spin_time = datetime.utcnow()
        self.status = GameStatus.SPINNING.value
        
        return winning_number
    
    def verify_result(self) -> bool:
        """Verify the game result using enhanced provably fair verification."""
        if not self.server_seed or not self.spin_hash:
            return False
        
        # Use enhanced verification
        return EnhancedProvablyFairGenerator.verify_enhanced_fairness(
            self.server_seed,
            self.client_seed,
            self.nonce,
            self.spin_hash,
            self.winning_number
        )


class GameBet(Base):
    """Individual bet placed in a game session."""
    __tablename__ = "game_bets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    game_session_id = Column(String, ForeignKey("game_sessions.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Bet details
    bet_type = Column(String, nullable=False)  # BetType enum
    bet_value = Column(String, nullable=False)  # What was bet on (e.g., "bitcoin", "red", "even")
    bet_amount = Column(Float, nullable=False)  # Amount in GEM coins
    
    # Payout information
    potential_payout = Column(Float, nullable=False)  # If bet wins
    payout_odds = Column(Float, nullable=False)       # Multiplier (e.g., 35:1, 2:1)
    actual_payout = Column(Float, default=0.0)        # Actual winnings
    
    # Result
    is_winner = Column(Boolean, default=False)
    
    # Metadata
    bet_data = Column(JSON)  # Additional bet configuration
    placed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    game_session = relationship("GameSession", back_populates="bets")
    user = relationship("User")


class GameStats(Base):
    """Player gaming statistics and achievements."""
    __tablename__ = "game_stats"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Game statistics
    total_games_played = Column(Integer, default=0)
    total_games_won = Column(Integer, default=0)
    total_amount_bet = Column(Float, default=0.0)
    total_amount_won = Column(Float, default=0.0)
    
    # Streak tracking
    current_win_streak = Column(Integer, default=0)
    longest_win_streak = Column(Integer, default=0)
    current_loss_streak = Column(Integer, default=0)
    longest_loss_streak = Column(Integer, default=0)
    
    # Betting patterns
    favorite_bet_type = Column(String)
    favorite_crypto = Column(String)
    biggest_single_win = Column(Float, default=0.0)
    biggest_single_loss = Column(Float, default=0.0)
    
    # Achievement tracking
    achievements_earned = Column(JSON, default=list)  # List of achievement IDs
    last_achievement_date = Column(DateTime)
    
    # Timestamps
    first_game_date = Column(DateTime)
    last_game_date = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.total_games_played == 0:
            return 0.0
        return (self.total_games_won / self.total_games_played) * 100
    
    @property
    def net_profit_loss(self) -> float:
        """Calculate net profit or loss."""
        return self.total_amount_won - self.total_amount_bet
    
    @property
    def roi_percentage(self) -> float:
        """Calculate return on investment percentage."""
        if self.total_amount_bet == 0:
            return 0.0
        return (self.net_profit_loss / self.total_amount_bet) * 100


class RoulettePayouts:
    """Payout calculations for different bet types."""
    
    PAYOUT_ODDS = {
        BetType.SINGLE_CRYPTO: 35.0,      # 35:1 - Single number
        BetType.CRYPTO_COLOR: 1.0,        # 1:1 - Red/Black (even money)
        BetType.CRYPTO_CATEGORY: 2.0,     # 2:1 - Category betting
        BetType.EVEN_ODD: 1.0,            # 1:1 - Even/Odd
        BetType.HIGH_LOW: 1.0,            # 1:1 - High/Low
        BetType.DOZEN: 2.0,               # 2:1 - Dozen betting
        BetType.COLUMN: 2.0               # 2:1 - Column betting
    }
    
    @classmethod
    def calculate_payout(cls, bet_type: BetType, bet_amount: float) -> float:
        """Calculate potential payout for a bet."""
        odds = cls.PAYOUT_ODDS.get(bet_type, 1.0)
        return bet_amount * (odds + 1)  # Includes original bet
    
    @classmethod
    def get_odds_multiplier(cls, bet_type: BetType) -> float:
        """Get odds multiplier for bet type."""
        return cls.PAYOUT_ODDS.get(bet_type, 1.0)


class EnhancedProvablyFairGenerator:
    """Enhanced provably fair random number generation with CS:GO-inspired security."""
    
    @staticmethod
    def generate_server_seed() -> str:
        """Generate cryptographically secure server seed (64 chars)."""
        return secrets.token_hex(32)  # 64 character hex string
    
    @staticmethod
    def hash_server_seed(server_seed: str) -> str:
        """Create hash of server seed to show players before game."""
        return hashlib.sha256(server_seed.encode()).hexdigest()
    
    @staticmethod
    def generate_client_seed(user_input: str = None) -> str:
        """Generate client seed from user input or random (16 chars)."""
        if user_input:
            # Hash user input for consistency
            return hashlib.sha256(user_input.encode()).hexdigest()[:16]
        else:
            # Generate random client seed
            return secrets.token_hex(8)  # 16 character hex string
    
    @staticmethod
    def generate_enhanced_result(
        server_seed: str,
        client_seed: str,
        nonce: int
    ) -> tuple[int, str]:
        """Generate result using enhanced multi-iteration hashing."""
        # Combine seeds and nonce
        combined_input = f"{server_seed}:{client_seed}:{nonce}"
        
        # Multiple hash iterations for enhanced security (CS:GO inspired)
        hash_result = hashlib.sha256(combined_input.encode()).hexdigest()
        
        # Additional hash iterations to prevent prediction
        for iteration in range(5):
            hash_result = hashlib.sha256(f"{hash_result}:{iteration}".encode()).hexdigest()
        
        # Use multiple segments of hash for better distribution
        segment1 = int(hash_result[:8], 16)
        segment2 = int(hash_result[8:16], 16)
        segment3 = int(hash_result[16:24], 16)
        
        # Combine segments with XOR for enhanced randomness
        final_value = segment1 ^ segment2 ^ segment3
        
        # Convert to roulette position (0-36)
        winning_number = final_value % 37
        
        return winning_number, hash_result
    
    @staticmethod
    def verify_enhanced_fairness(
        server_seed: str,
        client_seed: str,
        nonce: int,
        expected_hash: str,
        expected_result: int
    ) -> bool:
        """Verify enhanced provably fair result."""
        try:
            # Recreate the enhanced result
            actual_result, actual_hash = EnhancedProvablyFairGenerator.generate_enhanced_result(
                server_seed, client_seed, nonce
            )
            
            # Verify both hash and result match
            return actual_hash == expected_hash and actual_result == expected_result
        except Exception:
            return False
    
    @staticmethod
    def create_verification_url(server_seed: str, client_seed: str, nonce: int) -> str:
        """Create verification URL for transparency."""
        return f"/verify-fairness?server_seed={server_seed}&client_seed={client_seed}&nonce={nonce}"


class ProvablyFairGenerator(EnhancedProvablyFairGenerator):
    """Backward compatibility alias for existing code."""
    pass