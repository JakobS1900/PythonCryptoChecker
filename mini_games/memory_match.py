"""
Crypto Memory Match Mini-Game
Players match crypto logos and earn GEM coins based on performance.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, JSON
from database import Base, get_db_session
from gamification import VirtualEconomyEngine, RewardBundle
from logger import logger


class GameDifficulty(Enum):
    EASY = "EASY"        # 4x4 grid, 8 pairs
    MEDIUM = "MEDIUM"    # 4x6 grid, 12 pairs  
    HARD = "HARD"        # 6x6 grid, 18 pairs
    EXPERT = "EXPERT"    # 6x8 grid, 24 pairs


@dataclass
class MemoryGameStats:
    """Statistics for memory game performance."""
    moves_made: int = 0
    time_taken: float = 0.0
    pairs_found: int = 0
    perfect_matches: int = 0
    mistakes: int = 0
    difficulty: str = "EASY"
    

@dataclass
class CryptoCard:
    """Individual crypto card in memory game."""
    id: str
    crypto_symbol: str
    crypto_name: str
    icon_url: str
    is_flipped: bool = False
    is_matched: bool = False
    position: int = 0


class MemoryGameSession(Base):
    """Database model for memory game sessions."""
    __tablename__ = "memory_game_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    
    # Game Configuration
    difficulty = Column(String, default="EASY")
    grid_size = Column(String)  # "4x4", "4x6", etc.
    total_pairs = Column(Integer)
    
    # Game State
    game_state = Column(String, default="ACTIVE")  # ACTIVE, COMPLETED, ABANDONED
    cards_data = Column(JSON)  # Serialized card positions and states
    current_moves = Column(Integer, default=0)
    pairs_found = Column(Integer, default=0)
    
    # Performance Metrics
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    time_taken_seconds = Column(Float)
    perfect_matches = Column(Integer, default=0)  # Matches on first try
    mistakes = Column(Integer, default=0)
    
    # Rewards
    gem_coins_earned = Column(Float, default=0.0)
    xp_earned = Column(Integer, default=0)
    bonus_multiplier = Column(Float, default=1.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MemoryMatchGame:
    """Crypto-themed memory matching game for earning GEM coins."""
    
    CRYPTO_CARDS = [
        {"symbol": "BTC", "name": "Bitcoin", "icon": "₿"},
        {"symbol": "ETH", "name": "Ethereum", "icon": "Ξ"},
        {"symbol": "ADA", "name": "Cardano", "icon": "₳"},
        {"symbol": "DOT", "name": "Polkadot", "icon": "●"},
        {"symbol": "DOGE", "name": "Dogecoin", "icon": "Ð"},
        {"symbol": "LTC", "name": "Litecoin", "icon": "Ł"},
        {"symbol": "XRP", "name": "Ripple", "icon": "✕"},
        {"symbol": "SOL", "name": "Solana", "icon": "◎"},
        {"symbol": "AVAX", "name": "Avalanche", "icon": "🔺"},
        {"symbol": "MATIC", "name": "Polygon", "icon": "⬟"},
        {"symbol": "LINK", "name": "Chainlink", "icon": "🔗"},
        {"symbol": "UNI", "name": "Uniswap", "icon": "🦄"},
        {"symbol": "ATOM", "name": "Cosmos", "icon": "⚛"},
        {"symbol": "VET", "name": "VeChain", "icon": "🌿"},
        {"symbol": "ICP", "name": "Internet Computer", "icon": "∞"},
        {"symbol": "ALGO", "name": "Algorand", "icon": "△"},
        {"symbol": "XLM", "name": "Stellar", "icon": "⭐"},
        {"symbol": "FIL", "name": "Filecoin", "icon": "📁"},
        {"symbol": "MANA", "name": "Decentraland", "icon": "🏰"},
        {"symbol": "SAND", "name": "The Sandbox", "icon": "🏖"},
        {"symbol": "CRO", "name": "Crypto.com", "icon": "💎"},
        {"symbol": "FTT", "name": "FTX Token", "icon": "🚀"},
        {"symbol": "THETA", "name": "Theta Network", "icon": "θ"},
        {"symbol": "SHIB", "name": "Shiba Inu", "icon": "🐕"}
    ]
    
    DIFFICULTY_CONFIG = {
        GameDifficulty.EASY: {"grid": (4, 4), "pairs": 8, "time_bonus": 30, "base_reward": 25},
        GameDifficulty.MEDIUM: {"grid": (4, 6), "pairs": 12, "time_bonus": 45, "base_reward": 40},
        GameDifficulty.HARD: {"grid": (6, 6), "pairs": 18, "time_bonus": 60, "base_reward": 60},
        GameDifficulty.EXPERT: {"grid": (6, 8), "pairs": 24, "time_bonus": 90, "base_reward": 85}
    }
    
    def __init__(self, virtual_economy: VirtualEconomyEngine):
        self.virtual_economy = virtual_economy
    
    async def start_new_game(
        self, 
        session: AsyncSession, 
        user_id: str, 
        difficulty: GameDifficulty = GameDifficulty.EASY
    ) -> Dict[str, Any]:
        """Start a new memory match game session."""
        
        config = self.DIFFICULTY_CONFIG[difficulty]
        grid_rows, grid_cols = config["grid"]
        total_pairs = config["pairs"]
        
        # Generate random crypto cards for this game
        selected_cryptos = random.sample(self.CRYPTO_CARDS, total_pairs)
        
        # Create card pairs and shuffle positions
        cards = []
        card_id = 0
        
        for crypto in selected_cryptos:
            # Add two cards for each crypto (matching pair)
            for _ in range(2):
                cards.append(CryptoCard(
                    id=str(card_id),
                    crypto_symbol=crypto["symbol"],
                    crypto_name=crypto["name"],
                    icon_url=crypto["icon"],
                    position=card_id
                ))
                card_id += 1
        
        # Shuffle card positions
        random.shuffle(cards)
        
        # Update positions after shuffle
        for i, card in enumerate(cards):
            card.position = i
        
        # Create game session
        game_session = MemoryGameSession(
            user_id=user_id,
            difficulty=difficulty.value,
            grid_size=f"{grid_rows}x{grid_cols}",
            total_pairs=total_pairs,
            cards_data=[{
                "id": card.id,
                "crypto_symbol": card.crypto_symbol,
                "crypto_name": card.crypto_name,
                "icon_url": card.icon_url,
                "position": card.position,
                "is_flipped": card.is_flipped,
                "is_matched": card.is_matched
            } for card in cards]
        )
        
        session.add(game_session)
        await session.commit()
        
        logger.info(f"Started memory game for user {user_id}: {difficulty.value} difficulty")
        
        return {
            "status": "success",
            "game_id": game_session.id,
            "difficulty": difficulty.value,
            "grid_size": f"{grid_rows}x{grid_cols}",
            "total_pairs": total_pairs,
            "cards": [card.__dict__ for card in cards],
            "potential_reward": config["base_reward"]
        }
    
    async def make_move(
        self,
        session: AsyncSession,
        game_id: str,
        card1_id: str,
        card2_id: str
    ) -> Dict[str, Any]:
        """Process a move attempt (flipping two cards)."""
        
        # Get game session
        from sqlalchemy import select
        result = await session.execute(
            select(MemoryGameSession).where(MemoryGameSession.id == game_id)
        )
        game_session = result.scalar_one_or_none()
        
        if not game_session or game_session.game_state != "ACTIVE":
            return {"status": "error", "message": "Game not found or inactive"}
        
        # Load current cards state
        cards_data = game_session.cards_data
        cards = {card["id"]: card for card in cards_data}
        
        if card1_id not in cards or card2_id not in cards:
            return {"status": "error", "message": "Invalid card selection"}
        
        card1 = cards[card1_id]
        card2 = cards[card2_id]
        
        # Check if cards are already matched or the same card
        if (card1["is_matched"] or card2["is_matched"] or 
            card1_id == card2_id):
            return {"status": "error", "message": "Invalid move"}
        
        # Flip cards
        card1["is_flipped"] = True
        card2["is_flipped"] = True
        
        # Check for match
        is_match = card1["crypto_symbol"] == card2["crypto_symbol"]
        
        # Update game state
        game_session.current_moves += 1
        
        if is_match:
            # Mark cards as matched
            card1["is_matched"] = True
            card2["is_matched"] = True
            card1["is_flipped"] = False  # Hide matched cards
            card2["is_flipped"] = False
            
            game_session.pairs_found += 1
            
            # Check if this was a perfect match (first try)
            if game_session.current_moves == game_session.pairs_found:
                game_session.perfect_matches += 1
        else:
            # Not a match - flip cards back after showing briefly
            card1["is_flipped"] = False
            card2["is_flipped"] = False
            game_session.mistakes += 1
        
        # Update cards data
        game_session.cards_data = list(cards.values())
        
        # Check if game is complete
        game_complete = game_session.pairs_found >= game_session.total_pairs
        
        if game_complete:
            await self._complete_game(session, game_session)
        
        await session.commit()
        
        return {
            "status": "success",
            "is_match": is_match,
            "game_complete": game_complete,
            "pairs_found": game_session.pairs_found,
            "total_pairs": game_session.total_pairs,
            "moves": game_session.current_moves,
            "cards": list(cards.values()),
            "reward_earned": game_session.gem_coins_earned if game_complete else 0
        }
    
    async def _complete_game(self, session: AsyncSession, game_session: MemoryGameSession):
        """Complete the game and calculate rewards."""
        
        game_session.end_time = datetime.utcnow()
        game_session.time_taken_seconds = (
            game_session.end_time - game_session.start_time
        ).total_seconds()
        game_session.game_state = "COMPLETED"
        
        # Calculate reward based on performance
        difficulty = GameDifficulty(game_session.difficulty)
        config = self.DIFFICULTY_CONFIG[difficulty]
        base_reward = config["base_reward"]
        time_bonus_threshold = config["time_bonus"]
        
        # Performance multipliers
        multiplier = 1.0
        
        # Perfect game bonus (no mistakes)
        if game_session.mistakes == 0:
            multiplier += 0.5  # 50% bonus for perfect game
        
        # Speed bonus (completed within time threshold)
        if game_session.time_taken_seconds <= time_bonus_threshold:
            multiplier += 0.3  # 30% bonus for fast completion
        
        # Efficiency bonus (fewer moves = higher bonus)
        optimal_moves = game_session.total_pairs * 2  # Perfect would be exactly 2 moves per pair
        if game_session.current_moves <= optimal_moves * 1.2:  # Within 20% of optimal
            multiplier += 0.25  # 25% bonus for efficiency
        
        # Calculate final reward
        final_reward = base_reward * multiplier
        xp_reward = int(final_reward * 0.4)  # XP is 40% of GEM reward
        
        game_session.gem_coins_earned = final_reward
        game_session.xp_earned = xp_reward
        game_session.bonus_multiplier = multiplier
        
        # Award the reward through virtual economy
        reward_bundle = RewardBundle(
            gem_coins=final_reward,
            experience_points=xp_reward,
            description=f"Memory Game ({difficulty.value}): {game_session.pairs_found} pairs, {multiplier:.1f}x multiplier"
        )
        
        await self.virtual_economy.award_reward(session, game_session.user_id, reward_bundle)
        
        logger.info(f"Memory game completed - User: {game_session.user_id}, Reward: {final_reward} GEM, {xp_reward} XP")
    
    async def get_game_state(self, session: AsyncSession, game_id: str) -> Optional[Dict[str, Any]]:
        """Get current state of a memory game."""
        
        from sqlalchemy import select
        result = await session.execute(
            select(MemoryGameSession).where(MemoryGameSession.id == game_id)
        )
        game_session = result.scalar_one_or_none()
        
        if not game_session:
            return None
        
        return {
            "game_id": game_session.id,
            "difficulty": game_session.difficulty,
            "grid_size": game_session.grid_size,
            "game_state": game_session.game_state,
            "pairs_found": game_session.pairs_found,
            "total_pairs": game_session.total_pairs,
            "current_moves": game_session.current_moves,
            "cards": game_session.cards_data,
            "time_elapsed": (
                (datetime.utcnow() - game_session.start_time).total_seconds()
                if game_session.game_state == "ACTIVE" else game_session.time_taken_seconds
            ),
            "gem_coins_earned": game_session.gem_coins_earned,
            "xp_earned": game_session.xp_earned
        }
    
    async def get_user_stats(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get user's memory game statistics."""
        
        from sqlalchemy import select, func
        
        # Get overall stats
        result = await session.execute(
            select(
                func.count(MemoryGameSession.id).label("total_games"),
                func.sum(MemoryGameSession.gem_coins_earned).label("total_gems"),
                func.sum(MemoryGameSession.xp_earned).label("total_xp"),
                func.avg(MemoryGameSession.bonus_multiplier).label("avg_multiplier"),
                func.min(MemoryGameSession.time_taken_seconds).label("best_time"),
                func.sum(MemoryGameSession.perfect_matches).label("perfect_matches")
            ).where(
                (MemoryGameSession.user_id == user_id) & 
                (MemoryGameSession.game_state == "COMPLETED")
            )
        )
        stats = result.first()
        
        # Get difficulty breakdown
        difficulty_result = await session.execute(
            select(
                MemoryGameSession.difficulty,
                func.count(MemoryGameSession.id).label("games"),
                func.avg(MemoryGameSession.time_taken_seconds).label("avg_time"),
                func.max(MemoryGameSession.gem_coins_earned).label("best_reward")
            ).where(
                (MemoryGameSession.user_id == user_id) & 
                (MemoryGameSession.game_state == "COMPLETED")
            ).group_by(MemoryGameSession.difficulty)
        )
        
        difficulty_stats = {
            row.difficulty: {
                "games_played": row.games,
                "average_time": row.avg_time,
                "best_reward": row.best_reward
            }
            for row in difficulty_result
        }
        
        return {
            "total_games": stats.total_games or 0,
            "total_gems_earned": stats.total_gems or 0.0,
            "total_xp_earned": stats.total_xp or 0,
            "average_multiplier": float(stats.avg_multiplier or 1.0),
            "best_time_seconds": stats.best_time,
            "perfect_matches": stats.perfect_matches or 0,
            "difficulty_breakdown": difficulty_stats
        }