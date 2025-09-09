"""
Special game variants and tournament modes for crypto roulette.
Enhanced gameplay mechanics and social features.
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Any, Optional
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.orm import relationship, selectinload

from .models import GameSession, GameBet, GameStats, CryptoRouletteWheel
from .roulette_engine import RouletteEngine
from data_providers import DataManager
from logger import logger

Base = declarative_base()


class TournamentStatus(Enum):
    """Tournament status."""
    REGISTRATION = "REGISTRATION"   # Players can join
    ACTIVE = "ACTIVE"              # Tournament in progress
    FINISHED = "FINISHED"          # Tournament completed
    CANCELLED = "CANCELLED"        # Tournament cancelled


class Tournament(Base):
    """Tournament competitions with leaderboards."""
    __tablename__ = "tournaments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Tournament details
    name = Column(String(100), nullable=False)
    description = Column(Text)
    tournament_type = Column(String, default="WEEKLY_LEADERBOARD")
    
    # Entry requirements
    entry_fee = Column(Float, default=0.0)  # GEM coins to enter
    min_level = Column(Integer, default=1)   # Minimum player level
    max_participants = Column(Integer, default=100)
    
    # Prize pool
    total_prize_pool = Column(Float, default=0.0)
    prize_distribution = Column(JSON)  # How prizes are distributed
    
    # Tournament settings
    duration_hours = Column(Integer, default=168)  # 1 week default
    min_games_required = Column(Integer, default=10)
    
    # Status and timing
    status = Column(String, default=TournamentStatus.REGISTRATION.value)
    registration_deadline = Column(DateTime)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    
    # Statistics
    current_participants = Column(Integer, default=0)
    total_games_played = Column(Integer, default=0)
    total_volume_bet = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    participants = relationship("TournamentParticipant", back_populates="tournament")
    leaderboard = relationship("TournamentLeaderboard", back_populates="tournament")


class TournamentParticipant(Base):
    """Players participating in tournaments."""
    __tablename__ = "tournament_participants"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tournament_id = Column(String, ForeignKey("tournaments.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Entry details
    joined_at = Column(DateTime, default=datetime.utcnow)
    entry_fee_paid = Column(Float, default=0.0)
    
    # Performance tracking
    games_played = Column(Integer, default=0)
    total_bet_amount = Column(Float, default=0.0)
    total_winnings = Column(Float, default=0.0)
    net_profit = Column(Float, default=0.0)
    
    # Leaderboard metrics
    tournament_score = Column(Float, default=0.0)  # Calculated ranking score
    current_rank = Column(Integer)
    best_rank = Column(Integer)
    
    # Relationships
    tournament = relationship("Tournament", back_populates="participants")
    user = relationship("User")


class TournamentLeaderboard(Base):
    """Real-time tournament leaderboard."""
    __tablename__ = "tournament_leaderboard"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tournament_id = Column(String, ForeignKey("tournaments.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Ranking
    current_rank = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    
    # Performance metrics
    games_played = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    total_profit = Column(Float, default=0.0)
    roi_percentage = Column(Float, default=0.0)
    
    # Timestamps
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tournament = relationship("Tournament", back_populates="leaderboard")
    user = relationship("User")


class PricePredictionGame(Base):
    """Special game mode betting on crypto price movements."""
    __tablename__ = "price_prediction_games"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Prediction details
    crypto_id = Column(String, nullable=False)
    crypto_symbol = Column(String, nullable=False)
    
    # Price data
    start_price = Column(Float, nullable=False)
    end_price = Column(Float)
    prediction_direction = Column(String, nullable=False)  # UP, DOWN, SIDEWAYS
    confidence_level = Column(Float, default=50.0)  # 0-100%
    
    # Betting
    bet_amount = Column(Float, nullable=False)
    potential_payout = Column(Float, nullable=False)
    actual_payout = Column(Float, default=0.0)
    
    # Game timing
    prediction_duration = Column(Integer, default=300)  # 5 minutes in seconds
    created_at = Column(DateTime, default=datetime.utcnow)
    prediction_deadline = Column(DateTime)
    result_time = Column(DateTime)
    
    # Result
    is_winner = Column(Boolean)
    price_change_percentage = Column(Float)
    
    # Relationships
    user = relationship("User")


class GameVariants:
    """Special game variants and enhanced mechanics."""
    
    def __init__(self):
        self.roulette_engine = RouletteEngine()
        self.data_manager = DataManager()
    
    async def create_tournament(
        self,
        session: AsyncSession,
        name: str,
        description: str,
        entry_fee: float = 100.0,
        prize_pool: float = 5000.0,
        duration_hours: int = 168,
        max_participants: int = 100
    ) -> Tournament:
        """Create a new tournament."""
        
        start_time = datetime.utcnow() + timedelta(hours=1)  # Start in 1 hour
        end_time = start_time + timedelta(hours=duration_hours)
        registration_deadline = start_time - timedelta(minutes=30)
        
        # Default prize distribution (60% to 1st, 25% to 2nd, 15% to 3rd)
        prize_distribution = {
            "1": prize_pool * 0.60,
            "2": prize_pool * 0.25,
            "3": prize_pool * 0.15
        }
        
        tournament = Tournament(
            name=name,
            description=description,
            entry_fee=entry_fee,
            total_prize_pool=prize_pool,
            prize_distribution=prize_distribution,
            duration_hours=duration_hours,
            max_participants=max_participants,
            registration_deadline=registration_deadline,
            start_time=start_time,
            end_time=end_time
        )
        
        session.add(tournament)
        await session.commit()
        await session.refresh(tournament)
        
        logger.info(f"Created tournament: {name} ({tournament.id})")
        
        return tournament
    
    async def join_tournament(
        self,
        session: AsyncSession,
        tournament_id: str,
        user_id: str
    ) -> bool:
        """Join a tournament."""
        
        # Get tournament
        tournament_result = await session.execute(
            select(Tournament).where(Tournament.id == tournament_id)
        )
        tournament = tournament_result.scalar_one_or_none()
        
        if not tournament:
            raise ValueError("Tournament not found")
        
        if tournament.status != TournamentStatus.REGISTRATION.value:
            raise ValueError("Tournament registration is closed")
        
        if datetime.utcnow() > tournament.registration_deadline:
            raise ValueError("Registration deadline has passed")
        
        if tournament.current_participants >= tournament.max_participants:
            raise ValueError("Tournament is full")
        
        # Check if already joined
        existing = await session.execute(
            select(TournamentParticipant).where(
                and_(
                    TournamentParticipant.tournament_id == tournament_id,
                    TournamentParticipant.user_id == user_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Already joined this tournament")
        
        # Check entry fee and deduct if needed
        if tournament.entry_fee > 0:
            from gamification.virtual_economy import VirtualEconomyEngine
            economy = VirtualEconomyEngine()
            
            from database.unified_models import CurrencyType
            success = await economy.spend_currency(
                session, user_id, 
                CurrencyType.GEM_COINS,
                tournament.entry_fee,
                "tournament_entry",
                f"Entry fee for tournament: {tournament.name}"
            )
            
            if not success:
                raise ValueError("Insufficient GEM coins for entry fee")
        
        # Create participant
        participant = TournamentParticipant(
            tournament_id=tournament_id,
            user_id=user_id,
            entry_fee_paid=tournament.entry_fee
        )
        
        session.add(participant)
        
        # Update tournament participant count
        tournament.current_participants += 1
        tournament.total_prize_pool += tournament.entry_fee  # Add entry fee to prize pool
        
        await session.commit()
        
        logger.info(f"User {user_id} joined tournament {tournament_id}")
        
        return True
    
    async def get_tournament_leaderboard(
        self,
        session: AsyncSession,
        tournament_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get tournament leaderboard."""
        
        result = await session.execute(
            select(TournamentLeaderboard, User)
            .join(User, TournamentLeaderboard.user_id == User.id)
            .where(TournamentLeaderboard.tournament_id == tournament_id)
            .order_by(TournamentLeaderboard.current_rank.asc())
            .limit(limit)
        )
        
        leaderboard = []
        for entry, user in result:
            leaderboard.append({
                "rank": entry.current_rank,
                "user_id": user.id,
                "username": user.username,
                "display_name": user.display_name or user.username,
                "score": entry.score,
                "games_played": entry.games_played,
                "win_rate": entry.win_rate,
                "total_profit": entry.total_profit,
                "roi_percentage": entry.roi_percentage,
                "last_updated": entry.last_updated.isoformat()
            })
        
        return leaderboard
    
    async def create_price_prediction_game(
        self,
        session: AsyncSession,
        user_id: str,
        crypto_id: str,
        prediction_direction: str,
        bet_amount: float,
        prediction_duration: int = 300
    ) -> PricePredictionGame:
        """Create price prediction game."""
        
        # Get current price
        try:
            crypto_data = await self.data_manager.get_coin_data(crypto_id)
            if not crypto_data:
                raise ValueError(f"Could not get price data for {crypto_id}")
            
            current_price = crypto_data.current_price
        except Exception as e:
            logger.error(f"Error getting crypto price: {e}")
            raise ValueError("Unable to get current price")
        
        # Validate prediction direction
        if prediction_direction not in ["UP", "DOWN", "SIDEWAYS"]:
            raise ValueError("Prediction must be UP, DOWN, or SIDEWAYS")
        
        # Calculate potential payout based on difficulty
        payout_multiplier = {
            "UP": 1.8,      # Easier to predict in bull market
            "DOWN": 2.0,    # Harder to predict
            "SIDEWAYS": 5.0 # Very hard to predict (within ±2%)
        }[prediction_direction]
        
        potential_payout = bet_amount * payout_multiplier
        
        # Deduct bet amount
        from gamification.virtual_economy import VirtualEconomyEngine
        economy = VirtualEconomyEngine()
        
        from database.unified_models import CurrencyType
        success = await economy.spend_currency(
            session, user_id,
            CurrencyType.GEM_COINS,
            bet_amount,
            "price_prediction",
            f"Price prediction bet: {crypto_data.symbol} {prediction_direction}"
        )
        
        if not success:
            raise ValueError("Insufficient GEM coins for bet")
        
        # Create prediction game
        prediction_deadline = datetime.utcnow() + timedelta(seconds=prediction_duration)
        
        game = PricePredictionGame(
            user_id=user_id,
            crypto_id=crypto_id,
            crypto_symbol=crypto_data.symbol,
            start_price=current_price,
            prediction_direction=prediction_direction,
            bet_amount=bet_amount,
            potential_payout=potential_payout,
            prediction_duration=prediction_duration,
            prediction_deadline=prediction_deadline
        )
        
        session.add(game)
        await session.commit()
        await session.refresh(game)
        
        logger.info(f"Created price prediction game: {crypto_id} {prediction_direction} for user {user_id}")
        
        return game
    
    async def resolve_price_prediction_game(
        self,
        session: AsyncSession,
        game_id: str
    ) -> Dict[str, Any]:
        """Resolve completed price prediction game."""
        
        # Get game
        game_result = await session.execute(
            select(PricePredictionGame).where(
                and_(
                    PricePredictionGame.id == game_id,
                    PricePredictionGame.result_time.is_(None)
                )
            )
        )
        game = game_result.scalar_one_or_none()
        
        if not game:
            raise ValueError("Game not found or already resolved")
        
        if datetime.utcnow() < game.prediction_deadline:
            raise ValueError("Game has not finished yet")
        
        # Get current price
        try:
            crypto_data = await self.data_manager.get_coin_data(game.crypto_id)
            if not crypto_data:
                raise ValueError("Could not get final price")
            
            final_price = crypto_data.current_price
        except Exception as e:
            logger.error(f"Error getting final crypto price: {e}")
            raise ValueError("Unable to get final price")
        
        # Calculate price change
        price_change_percentage = ((final_price - game.start_price) / game.start_price) * 100
        game.end_price = final_price
        game.price_change_percentage = price_change_percentage
        game.result_time = datetime.utcnow()
        
        # Determine winner
        is_winner = False
        
        if game.prediction_direction == "UP" and price_change_percentage > 0.5:
            is_winner = True
        elif game.prediction_direction == "DOWN" and price_change_percentage < -0.5:
            is_winner = True
        elif game.prediction_direction == "SIDEWAYS" and abs(price_change_percentage) <= 2.0:
            is_winner = True
        
        game.is_winner = is_winner
        
        # Pay out winnings if won
        if is_winner:
            game.actual_payout = game.potential_payout
            
            from gamification.virtual_economy import VirtualEconomyEngine
            economy = VirtualEconomyEngine()
            
            from database.unified_models import CurrencyType
            await economy.add_currency(
                session, game.user_id,
                CurrencyType.GEM_COINS,
                game.actual_payout,
                "price_prediction_win",
                f"Won price prediction: {game.crypto_symbol} {game.prediction_direction}"
            )
        
        await session.commit()
        
        result = {
            "game_id": game_id,
            "crypto_symbol": game.crypto_symbol,
            "prediction": game.prediction_direction,
            "start_price": game.start_price,
            "end_price": game.end_price,
            "price_change": price_change_percentage,
            "bet_amount": game.bet_amount,
            "is_winner": is_winner,
            "payout": game.actual_payout,
            "net_result": game.actual_payout - game.bet_amount
        }
        
        logger.info(f"Resolved price prediction game {game_id}: {is_winner}")
        
        return result
    
    async def get_active_tournaments(
        self,
        session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get list of active tournaments."""
        
        result = await session.execute(
            select(Tournament)
            .where(Tournament.status.in_([
                TournamentStatus.REGISTRATION.value,
                TournamentStatus.ACTIVE.value
            ]))
            .order_by(Tournament.start_time.asc())
        )
        
        tournaments = []
        for tournament in result.scalars():
            tournaments.append({
                "id": tournament.id,
                "name": tournament.name,
                "description": tournament.description,
                "status": tournament.status,
                "entry_fee": tournament.entry_fee,
                "prize_pool": tournament.total_prize_pool,
                "participants": tournament.current_participants,
                "max_participants": tournament.max_participants,
                "start_time": tournament.start_time.isoformat(),
                "end_time": tournament.end_time.isoformat(),
                "registration_deadline": tournament.registration_deadline.isoformat(),
                "duration_hours": tournament.duration_hours
            })
        
        return tournaments
    
    async def cleanup_expired_games(self, session: AsyncSession) -> int:
        """Clean up expired price prediction games."""
        
        # Find expired unresolved games
        expired_games = await session.execute(
            select(PricePredictionGame)
            .where(
                and_(
                    PricePredictionGame.prediction_deadline < datetime.utcnow(),
                    PricePredictionGame.result_time.is_(None)
                )
            )
        )
        
        count = 0
        for game in expired_games.scalars():
            try:
                await self.resolve_price_prediction_game(session, game.id)
                count += 1
            except Exception as e:
                logger.error(f"Failed to resolve expired game {game.id}: {e}")
        
        return count