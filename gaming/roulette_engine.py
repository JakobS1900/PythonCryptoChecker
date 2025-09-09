"""
Crypto roulette gaming engine with provably fair mechanics.
Handles game sessions, betting, and result calculation.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from sqlalchemy.orm import selectinload

from .models import (
    GameSession, GameBet, GameStats, GameType, GameStatus, BetType,
    CryptoRouletteWheel, RoulettePayouts, ProvablyFairGenerator
)
from gamification.models import VirtualWallet, VirtualTransaction, CurrencyType
from gamification.virtual_economy import VirtualEconomyEngine
from auth.models import User
from logger import logger


class RouletteEngine:
    """Core crypto roulette gaming engine."""
    
    def __init__(self):
        self.virtual_economy = VirtualEconomyEngine()
        self.min_bet = 1.0        # Minimum bet in GEM coins
        self.max_bet = 10000.0    # Maximum bet in GEM coins
        self.house_edge = 0.027   # 2.7% house edge (1/37)
    
    async def create_game_session(
        self,
        session: AsyncSession,
        user_id: str,
        game_type: GameType = GameType.CLASSIC_CRYPTO,
        client_seed_input: Optional[str] = None
    ) -> GameSession:
        """Create new game session with provably fair setup."""
        
        # Generate provably fair seeds
        server_seed = ProvablyFairGenerator.generate_server_seed()
        server_seed_hash = ProvablyFairGenerator.hash_server_seed(server_seed)
        client_seed = ProvablyFairGenerator.generate_client_seed(client_seed_input)
        
        # Create game session
        game_session = GameSession(
            user_id=user_id,
            game_type=game_type.value,
            server_seed=server_seed,
            server_seed_hash=server_seed_hash,
            client_seed=client_seed,
            status=GameStatus.ACTIVE.value
        )
        
        session.add(game_session)
        await session.commit()
        await session.refresh(game_session)
        
        logger.info(f"Created game session {game_session.id} for user {user_id}")
        
        return game_session
    
    async def place_bet(
        self,
        session: AsyncSession,
        game_session_id: str,
        user_id: str,
        bet_type: BetType,
        bet_value: str,
        bet_amount: float
    ) -> GameBet:
        """Place a bet on the current game session."""
        
        # Validate bet amount
        if bet_amount < self.min_bet:
            raise ValueError(f"Minimum bet is {self.min_bet} GEM coins")
        
        if bet_amount > self.max_bet:
            raise ValueError(f"Maximum bet is {self.max_bet} GEM coins")
        
        # Get game session
        game_result = await session.execute(
            select(GameSession).where(
                and_(
                    GameSession.id == game_session_id,
                    GameSession.user_id == user_id,
                    GameSession.status == GameStatus.ACTIVE.value
                )
            )
        )
        game_session = game_result.scalar_one_or_none()
        
        if not game_session:
            raise ValueError("Game session not found or not active")
        
        # Check user has sufficient balance
        wallet_result = await session.execute(
            select(VirtualWallet).where(VirtualWallet.user_id == user_id)
        )
        wallet = wallet_result.scalar_one_or_none()
        
        if not wallet or wallet.gem_coins < bet_amount:
            raise ValueError("Insufficient GEM coins for bet")
        
        # Validate bet value for bet type
        self._validate_bet_value(bet_type, bet_value)
        
        # Calculate potential payout
        odds_multiplier = RoulettePayouts.get_odds_multiplier(bet_type)
        potential_payout = RoulettePayouts.calculate_payout(bet_type, bet_amount)
        
        # Create bet
        game_bet = GameBet(
            game_session_id=game_session_id,
            user_id=user_id,
            bet_type=bet_type.value,
            bet_value=bet_value,
            bet_amount=bet_amount,
            potential_payout=potential_payout,
            payout_odds=odds_multiplier
        )
        
        session.add(game_bet)
        
        # Deduct bet amount from wallet
        old_balance = wallet.gem_coins
        wallet.gem_coins -= bet_amount
        wallet.total_gems_spent += bet_amount
        wallet.updated_at = datetime.utcnow()
        
        # Update game session totals
        game_session.total_bet_amount += bet_amount
        
        # Log transaction
        transaction = VirtualTransaction(
            wallet_id=wallet.id,
            transaction_type="SPEND",
            currency_type=CurrencyType.GEM_COINS.value,
            amount=-bet_amount,
            source="roulette_bet",
            description=f"Roulette bet: {bet_type.value} on {bet_value}",
            reference_id=game_bet.id,
            balance_before=old_balance,
            balance_after=wallet.gem_coins
        )
        session.add(transaction)
        
        await session.commit()
        await session.refresh(game_bet)
        
        logger.info(f"Bet placed: {bet_amount} GEM on {bet_type.value}:{bet_value} in game {game_session_id}")
        
        return game_bet
    
    async def spin_wheel(
        self,
        session: AsyncSession,
        game_session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Spin the roulette wheel and determine results."""
        
        # Get game session with bets
        game_result = await session.execute(
            select(GameSession)
            .options(selectinload(GameSession.bets))
            .where(
                and_(
                    GameSession.id == game_session_id,
                    GameSession.user_id == user_id,
                    GameSession.status == GameStatus.ACTIVE.value
                )
            )
        )
        game_session = game_result.scalar_one_or_none()
        
        if not game_session:
            raise ValueError("Game session not found or not active")
        
        if not game_session.bets:
            raise ValueError("No bets placed yet")
        
        # Generate winning number
        winning_number = game_session.generate_result()
        winning_details = CryptoRouletteWheel.get_winning_bets(winning_number)
        
        # Process all bets
        total_winnings = 0.0
        winning_bets = []
        losing_bets = []
        
        for bet in game_session.bets:
            is_winner = self._check_bet_winner(bet, winning_details)
            bet.is_winner = is_winner
            
            if is_winner:
                bet.actual_payout = bet.potential_payout
                total_winnings += bet.actual_payout
                winning_bets.append(bet)
            else:
                bet.actual_payout = 0.0
                losing_bets.append(bet)
        
        # Update game session
        game_session.total_winnings = total_winnings
        game_session.house_edge_amount = game_session.total_bet_amount - total_winnings
        game_session.status = GameStatus.COMPLETED.value
        game_session.completed_at = datetime.utcnow()
        
        # Pay out winnings
        if total_winnings > 0:
            await self._pay_winnings(session, user_id, total_winnings, game_session_id)
        
        # Update user statistics
        await self._update_game_stats(session, user_id, game_session, len(winning_bets) > 0)
        
        # Award game rewards (XP, items, etc.)
        await self._award_game_rewards(session, user_id, game_session, len(winning_bets) > 0)
        
        await session.commit()
        
        # Prepare result data
        result_data = {
            "game_id": game_session_id,
            "winning_number": winning_number,
            "winning_crypto": game_session.winning_crypto,
            "winning_details": winning_details,
            "total_bet": game_session.total_bet_amount,
            "total_winnings": total_winnings,
            "net_result": total_winnings - game_session.total_bet_amount,
            "winning_bets": len(winning_bets),
            "losing_bets": len(losing_bets),
            "bets_details": [
                {
                    "bet_id": bet.id,
                    "bet_type": bet.bet_type,
                    "bet_value": bet.bet_value,
                    "bet_amount": bet.bet_amount,
                    "is_winner": bet.is_winner,
                    "payout": bet.actual_payout
                }
                for bet in game_session.bets
            ],
            "provably_fair": {
                "server_seed_hash": game_session.server_seed_hash,
                "client_seed": game_session.client_seed,
                "nonce": game_session.nonce,
                "spin_hash": game_session.spin_hash
            }
        }
        
        logger.info(f"Game {game_session_id} completed: {winning_number} ({game_session.winning_crypto})")
        
        return result_data
    
    async def reveal_server_seed(
        self,
        session: AsyncSession,
        game_session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Reveal server seed for provably fair verification."""
        
        game_result = await session.execute(
            select(GameSession).where(
                and_(
                    GameSession.id == game_session_id,
                    GameSession.user_id == user_id,
                    GameSession.status == GameStatus.COMPLETED.value
                )
            )
        )
        game_session = game_result.scalar_one_or_none()
        
        if not game_session:
            raise ValueError("Game session not found or not completed")
        
        # Verify the result
        is_fair = game_session.verify_result()
        
        return {
            "game_id": game_session_id,
            "server_seed": game_session.server_seed,
            "server_seed_hash": game_session.server_seed_hash,
            "client_seed": game_session.client_seed,
            "nonce": game_session.nonce,
            "spin_hash": game_session.spin_hash,
            "winning_number": game_session.winning_number,
            "is_provably_fair": is_fair,
            "verification_url": f"/verify-fairness?server_seed={game_session.server_seed}&client_seed={game_session.client_seed}&nonce={game_session.nonce}"
        }
    
    async def get_user_game_history(
        self,
        session: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's game history."""
        
        result = await session.execute(
            select(GameSession)
            .options(selectinload(GameSession.bets))
            .where(GameSession.user_id == user_id)
            .order_by(GameSession.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        game_sessions = result.scalars().all()
        
        history = []
        for game in game_sessions:
            game_data = {
                "game_id": game.id,
                "game_type": game.game_type,
                "status": game.status,
                "winning_number": game.winning_number,
                "winning_crypto": game.winning_crypto,
                "total_bet": game.total_bet_amount,
                "total_winnings": game.total_winnings,
                "net_result": game.total_winnings - game.total_bet_amount,
                "created_at": game.created_at.isoformat(),
                "completed_at": game.completed_at.isoformat() if game.completed_at else None,
                "bets_count": len(game.bets),
                "server_seed_hash": game.server_seed_hash
            }
            history.append(game_data)
        
        return history
    
    async def get_user_stats(
        self,
        session: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive user gaming statistics."""
        
        stats_result = await session.execute(
            select(GameStats).where(GameStats.user_id == user_id)
        )
        stats = stats_result.scalar_one_or_none()
        
        if not stats:
            # Create initial stats
            stats = GameStats(user_id=user_id)
            session.add(stats)
            await session.commit()
            await session.refresh(stats)
        
        return {
            "user_id": user_id,
            "total_games_played": stats.total_games_played,
            "total_games_won": stats.total_games_won,
            "win_rate": stats.win_rate,
            "total_amount_bet": stats.total_amount_bet,
            "total_amount_won": stats.total_amount_won,
            "net_profit_loss": stats.net_profit_loss,
            "roi_percentage": stats.roi_percentage,
            "current_win_streak": stats.current_win_streak,
            "longest_win_streak": stats.longest_win_streak,
            "current_loss_streak": stats.current_loss_streak,
            "longest_loss_streak": stats.longest_loss_streak,
            "favorite_bet_type": stats.favorite_bet_type,
            "favorite_crypto": stats.favorite_crypto,
            "biggest_single_win": stats.biggest_single_win,
            "biggest_single_loss": stats.biggest_single_loss,
            "achievements_earned": stats.achievements_earned or [],
            "first_game_date": stats.first_game_date.isoformat() if stats.first_game_date else None,
            "last_game_date": stats.last_game_date.isoformat() if stats.last_game_date else None
        }
    
    def _validate_bet_value(self, bet_type: BetType, bet_value: str):
        """Validate bet value for specific bet type."""
        if bet_type == BetType.SINGLE_CRYPTO:
            valid_cryptos = [pos["crypto"] for pos in CryptoRouletteWheel.WHEEL_POSITIONS.values()]
            if bet_value not in valid_cryptos:
                raise ValueError(f"Invalid crypto: {bet_value}")
        
        elif bet_type == BetType.CRYPTO_COLOR:
            if bet_value not in ["red", "black", "green"]:
                raise ValueError("Color must be red, black, or green")
        
        elif bet_type == BetType.CRYPTO_CATEGORY:
            valid_categories = set(pos["category"] for pos in CryptoRouletteWheel.WHEEL_POSITIONS.values())
            if bet_value not in valid_categories:
                raise ValueError(f"Invalid category: {bet_value}")
        
        elif bet_type == BetType.EVEN_ODD:
            if bet_value not in ["even", "odd"]:
                raise ValueError("Must be even or odd")
        
        elif bet_type == BetType.HIGH_LOW:
            if bet_value not in ["high", "low"]:
                raise ValueError("Must be high or low")
        
        elif bet_type == BetType.DOZEN:
            if bet_value not in ["first", "second", "third"]:
                raise ValueError("Must be first, second, or third dozen")
        
        elif bet_type == BetType.COLUMN:
            if bet_value not in ["1", "2", "3"]:
                raise ValueError("Column must be 1, 2, or 3")
    
    def _check_bet_winner(self, bet: GameBet, winning_details: Dict[str, Any]) -> bool:
        """Check if a bet is a winner based on game result."""
        bet_type = BetType(bet.bet_type)
        bet_value = bet.bet_value
        
        if bet_type == BetType.SINGLE_CRYPTO:
            return winning_details["single_crypto"] == bet_value
        
        elif bet_type == BetType.CRYPTO_COLOR:
            return winning_details["color"] == bet_value
        
        elif bet_type == BetType.CRYPTO_CATEGORY:
            return winning_details["category"] == bet_value
        
        elif bet_type == BetType.EVEN_ODD:
            return winning_details["even_odd"] == bet_value
        
        elif bet_type == BetType.HIGH_LOW:
            return winning_details["high_low"] == bet_value
        
        elif bet_type == BetType.DOZEN:
            return winning_details["dozen"] == bet_value
        
        elif bet_type == BetType.COLUMN:
            return str(winning_details["column"]) == bet_value
        
        return False
    
    async def _pay_winnings(
        self,
        session: AsyncSession,
        user_id: str,
        total_winnings: float,
        game_session_id: str
    ):
        """Pay winnings to user's wallet."""
        
        wallet_result = await session.execute(
            select(VirtualWallet).where(VirtualWallet.user_id == user_id)
        )
        wallet = wallet_result.scalar_one()
        
        old_balance = wallet.gem_coins
        wallet.gem_coins += total_winnings
        wallet.total_gems_earned += total_winnings
        wallet.updated_at = datetime.utcnow()
        
        # Log transaction
        transaction = VirtualTransaction(
            wallet_id=wallet.id,
            transaction_type="EARN",
            currency_type=CurrencyType.GEM_COINS.value,
            amount=total_winnings,
            source="roulette_win",
            description=f"Roulette winnings from game {game_session_id}",
            reference_id=game_session_id,
            balance_before=old_balance,
            balance_after=wallet.gem_coins
        )
        session.add(transaction)
    
    async def _update_game_stats(
        self,
        session: AsyncSession,
        user_id: str,
        game_session: GameSession,
        won_game: bool
    ):
        """Update user's gaming statistics."""
        
        stats_result = await session.execute(
            select(GameStats).where(GameStats.user_id == user_id)
        )
        stats = stats_result.scalar_one_or_none()
        
        if not stats:
            stats = GameStats(
                user_id=user_id,
                first_game_date=datetime.utcnow()
            )
            session.add(stats)
        
        # Update basic stats
        stats.total_games_played += 1
        stats.total_amount_bet += game_session.total_bet_amount
        stats.total_amount_won += game_session.total_winnings
        stats.last_game_date = datetime.utcnow()
        stats.updated_at = datetime.utcnow()
        
        # Update win/loss streaks
        if won_game:
            stats.total_games_won += 1
            stats.current_win_streak += 1
            stats.longest_win_streak = max(stats.longest_win_streak, stats.current_win_streak)
            stats.current_loss_streak = 0
            
            # Update biggest single win
            net_win = game_session.total_winnings - game_session.total_bet_amount
            stats.biggest_single_win = max(stats.biggest_single_win, net_win)
        else:
            stats.current_loss_streak += 1
            stats.longest_loss_streak = max(stats.longest_loss_streak, stats.current_loss_streak)
            stats.current_win_streak = 0
            
            # Update biggest single loss
            net_loss = game_session.total_bet_amount - game_session.total_winnings
            stats.biggest_single_loss = max(stats.biggest_single_loss, net_loss)
        
        # Update favorite crypto (most bet on)
        if game_session.winning_crypto:
            # This is simplified - in production, track actual betting patterns
            stats.favorite_crypto = game_session.winning_crypto
    
    async def _award_game_rewards(
        self,
        session: AsyncSession,
        user_id: str,
        game_session: GameSession,
        won_game: bool
    ):
        """Award XP and potential item drops for playing."""
        
        # Calculate win streak for bonus
        stats_result = await session.execute(
            select(GameStats).where(GameStats.user_id == user_id)
        )
        stats = stats_result.scalar_one_or_none()
        win_streak = stats.current_win_streak if stats else 0
        
        # Award game rewards through virtual economy
        reward = await self.virtual_economy.calculate_game_reward(
            session, user_id, won_game, game_session.total_bet_amount, win_streak
        )
        
        # Potential item drop (small chance)
        if won_game and win_streak >= 3:  # Bonus drop chance for win streaks
            await self.virtual_economy.generate_random_item_drop(
                session, user_id, drop_chance_multiplier=1.5
            )
        elif won_game:
            await self.virtual_economy.generate_random_item_drop(session, user_id)