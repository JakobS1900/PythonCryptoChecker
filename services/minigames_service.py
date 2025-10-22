"""
Mini-Games Service

Handles game logic for Coin Flip, Dice Roll, and Higher/Lower card games.
Includes statistics tracking and GEM balance management.
"""

import random
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    User, MiniGame, MiniGameStats, Transaction, TransactionType
)


class MiniGamesService:
    """Service for mini-games logic and statistics."""

    # Game configuration
    MIN_BET = 100  # Minimum bet amount
    MAX_BET = 100000  # Maximum bet amount

    # Coin Flip settings
    COINFLIP_MULTIPLIER = 2.0  # Win doubles your bet

    # Dice settings
    DICE_MULTIPLIERS = {
        1: 6.0,   # Roll exactly 1: 6x payout
        2: 6.0,   # Roll exactly 2: 6x payout
        3: 6.0,   # Roll exactly 3: 6x payout
        4: 6.0,   # Roll exactly 4: 6x payout
        5: 6.0,   # Roll exactly 5: 6x payout
        6: 6.0,   # Roll exactly 6: 6x payout
        'even': 2.0,  # Roll even: 2x payout
        'odd': 2.0,   # Roll odd: 2x payout
        'high': 2.0,  # Roll 4-6: 2x payout
        'low': 2.0,   # Roll 1-3: 2x payout
    }

    # Higher/Lower settings
    HIGHERLOWER_MULTIPLIER = 2.0  # Guess correctly: 2x payout
    HIGHERLOWER_SAME_MULTIPLIER = 5.0  # Guess same (rare): 5x payout

    @staticmethod
    async def play_coinflip(
        user_id: str,
        bet_amount: int,
        choice: str,  # 'heads' or 'tails'
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Play Coin Flip game.

        Args:
            user_id: User ID
            bet_amount: Amount to bet
            choice: 'heads' or 'tails'
            db: Database session

        Returns:
            Dict with game result
        """
        # Validate bet amount
        if bet_amount < MiniGamesService.MIN_BET:
            raise ValueError(f"Minimum bet is {MiniGamesService.MIN_BET} GEM")
        if bet_amount > MiniGamesService.MAX_BET:
            raise ValueError(f"Maximum bet is {MiniGamesService.MAX_BET} GEM")

        # Validate choice
        choice = choice.lower()
        if choice not in ['heads', 'tails']:
            raise ValueError("Choice must be 'heads' or 'tails'")

        # Get user and check balance
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        if user.gem_balance < bet_amount:
            raise ValueError("Insufficient GEM balance")

        # Deduct bet amount
        user.gem_balance -= bet_amount

        # Create transaction for bet
        bet_transaction = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.MINIGAME_BET,
            amount=-bet_amount,
            description=f"Coin Flip bet: {choice}"
        )
        db.add(bet_transaction)

        # Flip the coin
        result_flip = random.choice(['heads', 'tails'])
        won = (result_flip == choice)

        # Calculate payout
        payout = 0
        profit = -bet_amount
        if won:
            payout = int(bet_amount * MiniGamesService.COINFLIP_MULTIPLIER)
            profit = payout - bet_amount
            user.gem_balance += payout

            # Create transaction for win
            win_transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.MINIGAME_WIN,
                amount=payout,
                description=f"Coin Flip win: {result_flip}"
            )
            db.add(win_transaction)

        # Create game record
        game_data = {
            'choice': choice,
            'result': result_flip,
            'multiplier': MiniGamesService.COINFLIP_MULTIPLIER if won else 0
        }

        game = MiniGame(
            user_id=user_id,
            game_type='coinflip',
            bet_amount=bet_amount,
            payout=payout,
            profit=profit,
            game_data=json.dumps(game_data),
            won=won
        )
        db.add(game)

        # Update statistics
        await MiniGamesService._update_stats(user_id, 'coinflip', bet_amount, payout, profit, won, db)

        await db.commit()

        return {
            'won': won,
            'choice': choice,
            'result': result_flip,
            'bet_amount': bet_amount,
            'payout': payout,
            'profit': profit,
            'new_balance': user.gem_balance
        }

    @staticmethod
    async def play_dice(
        user_id: str,
        bet_amount: int,
        bet_type: str,  # 'exact', 'even', 'odd', 'high', 'low'
        db: AsyncSession,
        bet_value: Optional[int] = None  # For 'exact' bets (1-6)
    ) -> Dict[str, Any]:
        """
        Play Dice Roll game.

        Args:
            user_id: User ID
            bet_amount: Amount to bet
            bet_type: Type of bet
            bet_value: Value for exact bets
            db: Database session

        Returns:
            Dict with game result
        """
        # Validate bet amount
        if bet_amount < MiniGamesService.MIN_BET:
            raise ValueError(f"Minimum bet is {MiniGamesService.MIN_BET} GEM")
        if bet_amount > MiniGamesService.MAX_BET:
            raise ValueError(f"Maximum bet is {MiniGamesService.MAX_BET} GEM")

        # Validate bet type
        bet_type = bet_type.lower()
        if bet_type not in ['exact', 'even', 'odd', 'high', 'low']:
            raise ValueError("Invalid bet type")

        # Validate exact bet value
        if bet_type == 'exact':
            if bet_value is None or bet_value < 1 or bet_value > 6:
                raise ValueError("Exact bet requires value between 1 and 6")

        # Get user and check balance
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        if user.gem_balance < bet_amount:
            raise ValueError("Insufficient GEM balance")

        # Deduct bet amount
        user.gem_balance -= bet_amount

        # Create transaction for bet
        bet_transaction = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.MINIGAME_BET,
            amount=-bet_amount,
            description=f"Dice Roll bet: {bet_type}" + (f" {bet_value}" if bet_type == 'exact' else "")
        )
        db.add(bet_transaction)

        # Roll the dice
        roll = random.randint(1, 6)

        # Check if won
        won = False
        if bet_type == 'exact':
            won = (roll == bet_value)
            multiplier_key = bet_value
        elif bet_type == 'even':
            won = (roll % 2 == 0)
            multiplier_key = 'even'
        elif bet_type == 'odd':
            won = (roll % 2 == 1)
            multiplier_key = 'odd'
        elif bet_type == 'high':
            won = (roll >= 4)
            multiplier_key = 'high'
        elif bet_type == 'low':
            won = (roll <= 3)
            multiplier_key = 'low'

        # Calculate payout
        payout = 0
        profit = -bet_amount
        multiplier = 0
        if won:
            multiplier = MiniGamesService.DICE_MULTIPLIERS[multiplier_key]
            payout = int(bet_amount * multiplier)
            profit = payout - bet_amount
            user.gem_balance += payout

            # Create transaction for win
            win_transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.MINIGAME_WIN,
                amount=payout,
                description=f"Dice Roll win: rolled {roll}"
            )
            db.add(win_transaction)

        # Create game record
        game_data = {
            'bet_type': bet_type,
            'bet_value': bet_value,
            'roll': roll,
            'multiplier': multiplier
        }

        game = MiniGame(
            user_id=user_id,
            game_type='dice',
            bet_amount=bet_amount,
            payout=payout,
            profit=profit,
            game_data=json.dumps(game_data),
            won=won
        )
        db.add(game)

        # Update statistics
        await MiniGamesService._update_stats(user_id, 'dice', bet_amount, payout, profit, won, db)

        await db.commit()

        return {
            'won': won,
            'bet_type': bet_type,
            'bet_value': bet_value,
            'roll': roll,
            'multiplier': multiplier,
            'bet_amount': bet_amount,
            'payout': payout,
            'profit': profit,
            'new_balance': user.gem_balance
        }

    @staticmethod
    async def play_higherlower(
        user_id: str,
        bet_amount: int,
        guess: str,  # 'higher', 'lower', 'same'
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Play Higher/Lower card game.

        Args:
            user_id: User ID
            bet_amount: Amount to bet
            guess: 'higher', 'lower', or 'same'
            db: Database session

        Returns:
            Dict with game result
        """
        # Validate bet amount
        if bet_amount < MiniGamesService.MIN_BET:
            raise ValueError(f"Minimum bet is {MiniGamesService.MIN_BET} GEM")
        if bet_amount > MiniGamesService.MAX_BET:
            raise ValueError(f"Maximum bet is {MiniGamesService.MAX_BET} GEM")

        # Validate guess
        guess = guess.lower()
        if guess not in ['higher', 'lower', 'same']:
            raise ValueError("Guess must be 'higher', 'lower', or 'same'")

        # Get user and check balance
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        if user.gem_balance < bet_amount:
            raise ValueError("Insufficient GEM balance")

        # Deduct bet amount
        user.gem_balance -= bet_amount

        # Create transaction for bet
        bet_transaction = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.MINIGAME_BET,
            amount=-bet_amount,
            description=f"Higher/Lower bet: {guess}"
        )
        db.add(bet_transaction)

        # Draw two cards (1-13: Ace to King)
        card1 = random.randint(1, 13)
        card2 = random.randint(1, 13)

        # Check if won
        won = False
        if guess == 'higher' and card2 > card1:
            won = True
        elif guess == 'lower' and card2 < card1:
            won = True
        elif guess == 'same' and card2 == card1:
            won = True

        # Calculate payout
        payout = 0
        profit = -bet_amount
        multiplier = 0
        if won:
            multiplier = MiniGamesService.HIGHERLOWER_SAME_MULTIPLIER if guess == 'same' else MiniGamesService.HIGHERLOWER_MULTIPLIER
            payout = int(bet_amount * multiplier)
            profit = payout - bet_amount
            user.gem_balance += payout

            # Create transaction for win
            win_transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.MINIGAME_WIN,
                amount=payout,
                description=f"Higher/Lower win: {card1} -> {card2}"
            )
            db.add(win_transaction)

        # Create game record
        game_data = {
            'guess': guess,
            'card1': card1,
            'card2': card2,
            'multiplier': multiplier
        }

        game = MiniGame(
            user_id=user_id,
            game_type='higherlower',
            bet_amount=bet_amount,
            payout=payout,
            profit=profit,
            game_data=json.dumps(game_data),
            won=won
        )
        db.add(game)

        # Update statistics
        await MiniGamesService._update_stats(user_id, 'higherlower', bet_amount, payout, profit, won, db)

        await db.commit()

        return {
            'won': won,
            'guess': guess,
            'card1': card1,
            'card2': card2,
            'multiplier': multiplier,
            'bet_amount': bet_amount,
            'payout': payout,
            'profit': profit,
            'new_balance': user.gem_balance
        }

    @staticmethod
    async def _update_stats(
        user_id: str,
        game_type: str,
        bet_amount: int,
        payout: int,
        profit: int,
        won: bool,
        db: AsyncSession
    ):
        """Update user's mini-game statistics."""
        # Get or create stats record
        result = await db.execute(
            select(MiniGameStats).where(MiniGameStats.user_id == user_id)
        )
        stats = result.scalar_one_or_none()

        if not stats:
            stats = MiniGameStats(user_id=user_id)
            db.add(stats)

        # Update overall stats
        stats.total_games_played += 1
        stats.total_wagered += bet_amount
        stats.total_won += payout
        stats.net_profit += profit

        if won:
            stats.total_games_won += 1
            stats.current_win_streak += 1
            stats.current_loss_streak = 0
            if stats.current_win_streak > stats.longest_win_streak:
                stats.longest_win_streak = stats.current_win_streak
            if profit > stats.biggest_win:
                stats.biggest_win = profit
        else:
            stats.total_games_lost += 1
            stats.current_loss_streak += 1
            stats.current_win_streak = 0
            if stats.current_loss_streak > stats.longest_loss_streak:
                stats.longest_loss_streak = stats.current_loss_streak
            if abs(profit) > stats.biggest_loss:
                stats.biggest_loss = abs(profit)

        # Update per-game stats
        game_stats_field = f"{game_type}_stats"
        current_game_stats = getattr(stats, game_stats_field)

        if current_game_stats:
            game_stats = json.loads(current_game_stats)
        else:
            game_stats = {'games': 0, 'wins': 0, 'profit': 0}

        game_stats['games'] += 1
        if won:
            game_stats['wins'] += 1
        game_stats['profit'] += profit

        setattr(stats, game_stats_field, json.dumps(game_stats))

    @staticmethod
    async def get_user_stats(user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get user's mini-game statistics."""
        result = await db.execute(
            select(MiniGameStats).where(MiniGameStats.user_id == user_id)
        )
        stats = result.scalar_one_or_none()

        if not stats:
            return {
                'total_games_played': 0,
                'total_games_won': 0,
                'total_games_lost': 0,
                'win_rate': 0.0,
                'total_wagered': 0,
                'total_won': 0,
                'net_profit': 0,
                'current_win_streak': 0,
                'longest_win_streak': 0,
                'current_loss_streak': 0,
                'longest_loss_streak': 0,
                'biggest_win': 0,
                'biggest_loss': 0,
                'coinflip_stats': {'games': 0, 'wins': 0, 'profit': 0},
                'dice_stats': {'games': 0, 'wins': 0, 'profit': 0},
                'higherlower_stats': {'games': 0, 'wins': 0, 'profit': 0}
            }

        win_rate = (stats.total_games_won / stats.total_games_played * 100) if stats.total_games_played > 0 else 0.0

        return {
            'total_games_played': stats.total_games_played,
            'total_games_won': stats.total_games_won,
            'total_games_lost': stats.total_games_lost,
            'win_rate': round(win_rate, 2),
            'total_wagered': stats.total_wagered,
            'total_won': stats.total_won,
            'net_profit': stats.net_profit,
            'current_win_streak': stats.current_win_streak,
            'longest_win_streak': stats.longest_win_streak,
            'current_loss_streak': stats.current_loss_streak,
            'longest_loss_streak': stats.longest_loss_streak,
            'biggest_win': stats.biggest_win,
            'biggest_loss': stats.biggest_loss,
            'coinflip_stats': json.loads(stats.coinflip_stats) if stats.coinflip_stats else {'games': 0, 'wins': 0, 'profit': 0},
            'dice_stats': json.loads(stats.dice_stats) if stats.dice_stats else {'games': 0, 'wins': 0, 'profit': 0},
            'higherlower_stats': json.loads(stats.higherlower_stats) if stats.higherlower_stats else {'games': 0, 'wins': 0, 'profit': 0}
        }

    @staticmethod
    async def get_recent_games(user_id: str, db: AsyncSession, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's recent game history."""
        result = await db.execute(
            select(MiniGame)
            .where(MiniGame.user_id == user_id)
            .order_by(MiniGame.played_at.desc())
            .limit(limit)
        )
        games = result.scalars().all()

        return [
            {
                'id': game.id,
                'game_type': game.game_type,
                'bet_amount': game.bet_amount,
                'payout': game.payout,
                'profit': game.profit,
                'won': game.won,
                'game_data': json.loads(game.game_data) if game.game_data else {},
                'played_at': game.played_at.isoformat()
            }
            for game in games
        ]
