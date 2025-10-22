"""
Crash Game Service

Handles the crash game logic including:
- Game round management
- Provably fair crash point generation
- Bet placement and cashout
- Real-time multiplier calculation
"""

import hashlib
import secrets
import math
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    User, CrashGame, CrashBet, Transaction, TransactionType
)


class CrashGameService:
    """Service for crash game operations."""

    # Game settings
    MIN_BET = 100
    MAX_BET = 100000
    MIN_CRASH_POINT = 1.01
    MAX_CRASH_POINT = 100.00

    # Timing settings
    BETTING_DURATION = 10  # Seconds for betting phase
    MULTIPLIER_SPEED = 0.1  # Seconds between multiplier updates

    # Current active game (in-memory singleton)
    current_game_id: Optional[int] = None
    current_multiplier: float = 1.00
    game_task: Optional[asyncio.Task] = None

    @staticmethod
    def generate_crash_point(server_seed: str) -> float:
        """
        Generate provably fair crash point using server seed.
        Uses SHA256 hash to generate a deterministic crash point.

        Formula: crash_point = 99 / (1 - hash_value)
        Where hash_value is a normalized float between 0-1
        """
        # Hash the server seed
        hash_hex = hashlib.sha256(server_seed.encode()).hexdigest()

        # Convert first 13 hex digits to integer
        hash_int = int(hash_hex[:13], 16)

        # Normalize to 0-1 range
        max_int = int('f' * 13, 16)
        hash_normalized = hash_int / max_int

        # Calculate crash point with house edge
        # This formula ensures most crashes are low but occasionally very high
        if hash_normalized == 0:
            hash_normalized = 1

        # Calculate crash point: 1 / (1 - hash^(1/3))
        # This creates a distribution where lower crashes are more common
        crash_point = 99 / (99 * (1 - hash_normalized ** 0.5))

        # Clamp to reasonable range
        crash_point = max(CrashGameService.MIN_CRASH_POINT,
                         min(crash_point, CrashGameService.MAX_CRASH_POINT))

        return round(crash_point, 2)

    @staticmethod
    async def create_game(db: AsyncSession) -> CrashGame:
        """Create a new crash game round."""
        # Generate server seed and hash
        server_seed = secrets.token_hex(32)  # 64 char hex string
        server_seed_hash = hashlib.sha256(server_seed.encode()).hexdigest()

        # Create game
        game = CrashGame(
            status='waiting',
            server_seed=server_seed,
            server_seed_hash=server_seed_hash
        )

        db.add(game)
        await db.commit()
        await db.refresh(game)

        print(f"[Crash] Created game #{game.id}, seed hash: {server_seed_hash[:16]}...")

        return game

    @staticmethod
    async def place_bet(
        user_id: str,
        bet_amount: int,
        game_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Place a bet on the current game."""
        # Validate bet amount
        if bet_amount < CrashGameService.MIN_BET:
            raise ValueError(f"Minimum bet is {CrashGameService.MIN_BET} GEM")
        if bet_amount > CrashGameService.MAX_BET:
            raise ValueError(f"Maximum bet is {CrashGameService.MAX_BET} GEM")

        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        # Check balance
        if user.gem_balance < bet_amount:
            raise ValueError("Insufficient GEM balance")

        # Get game
        result = await db.execute(select(CrashGame).where(CrashGame.id == game_id))
        game = result.scalar_one_or_none()

        if not game:
            raise ValueError("Game not found")

        if game.status not in ['waiting', 'starting']:
            raise ValueError("Cannot bet on game in progress")

        # Check if user already has a bet in this game
        result = await db.execute(
            select(CrashBet).where(
                and_(CrashBet.game_id == game_id, CrashBet.user_id == user_id)
            )
        )
        existing_bet = result.scalar_one_or_none()
        if existing_bet:
            raise ValueError("You already have a bet in this game")

        # Deduct bet amount
        user.gem_balance -= bet_amount

        # Create bet record
        bet = CrashBet(
            game_id=game_id,
            user_id=user_id,
            bet_amount=bet_amount,
            status='active'
        )

        db.add(bet)

        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.CRASH_BET,
            amount=-bet_amount,
            balance_after=user.gem_balance,
            description=f"Crash game #{game_id} bet"
        )

        db.add(transaction)

        # Update game stats
        game.total_bets += 1
        game.total_wagered += bet_amount

        await db.commit()
        await db.refresh(bet)

        print(f"[Crash] User {user.username} bet {bet_amount} GEM on game #{game_id}")

        return {
            "bet_id": bet.id,
            "game_id": game_id,
            "bet_amount": bet_amount,
            "new_balance": user.gem_balance,
            "message": f"Bet placed: {bet_amount} GEM"
        }

    @staticmethod
    async def cashout(
        user_id: str,
        game_id: int,
        current_multiplier: float,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Cash out a bet at the current multiplier."""
        # Get bet
        result = await db.execute(
            select(CrashBet).where(
                and_(
                    CrashBet.game_id == game_id,
                    CrashBet.user_id == user_id,
                    CrashBet.status == 'active'
                )
            )
        )
        bet = result.scalar_one_or_none()

        if not bet:
            raise ValueError("No active bet found")

        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        # Calculate payout
        payout = int(bet.bet_amount * current_multiplier)
        profit = payout - bet.bet_amount

        # Update bet
        bet.status = 'cashed_out'
        bet.cashout_at = current_multiplier
        bet.profit = profit
        bet.cashed_out_at = datetime.utcnow()

        # Update user balance
        user.gem_balance += payout

        # Create transaction
        transaction = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.CRASH_WIN,
            amount=payout,
            balance_after=user.gem_balance,
            description=f"Crash game #{game_id} cashout at {current_multiplier:.2f}x"
        )

        db.add(transaction)

        # Update game stats
        result = await db.execute(select(CrashGame).where(CrashGame.id == game_id))
        game = result.scalar_one_or_none()
        if game:
            game.total_paid_out += payout

        await db.commit()

        print(f"[Crash] User {user.username} cashed out at {current_multiplier:.2f}x, profit: {profit} GEM")

        return {
            "bet_id": bet.id,
            "cashout_multiplier": current_multiplier,
            "bet_amount": bet.bet_amount,
            "payout": payout,
            "profit": profit,
            "new_balance": user.gem_balance,
            "message": f"Cashed out at {current_multiplier:.2f}x!"
        }

    @staticmethod
    async def finish_game(game_id: int, crash_point: float, db: AsyncSession):
        """Finish a game and mark all active bets as lost."""
        # Get game
        result = await db.execute(select(CrashGame).where(CrashGame.id == game_id))
        game = result.scalar_one_or_none()

        if not game:
            return

        # Update game
        game.status = 'crashed'
        game.crash_point = crash_point
        game.crashed_at = datetime.utcnow()
        game.completed_at = datetime.utcnow()

        # Get all active bets (those that didn't cash out)
        result = await db.execute(
            select(CrashBet).where(
                and_(CrashBet.game_id == game_id, CrashBet.status == 'active')
            )
        )
        active_bets = result.scalars().all()

        # Mark them as lost
        for bet in active_bets:
            bet.status = 'lost'
            bet.profit = -bet.bet_amount

        await db.commit()

        print(f"[Crash] Game #{game_id} crashed at {crash_point:.2f}x, {len(active_bets)} bets lost")

    @staticmethod
    async def get_current_game(db: AsyncSession) -> Optional[CrashGame]:
        """Get the current active game or create a new one."""
        # Find a game that's waiting or in progress
        result = await db.execute(
            select(CrashGame).where(
                CrashGame.status.in_(['waiting', 'starting', 'playing'])
            ).order_by(CrashGame.id.desc())
        )
        game = result.scalar_one_or_none()

        if not game:
            # Create new game
            game = await CrashGameService.create_game(db)

        return game

    @staticmethod
    async def get_game_bets(game_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get all bets for a game."""
        result = await db.execute(
            select(CrashBet, User.username).join(User).where(CrashBet.game_id == game_id)
        )

        bets = []
        for bet, username in result.all():
            bets.append({
                "id": bet.id,
                "username": username,
                "bet_amount": bet.bet_amount,
                "cashout_at": bet.cashout_at,
                "profit": bet.profit,
                "status": bet.status,
                "placed_at": bet.placed_at.isoformat()
            })

        return bets

    @staticmethod
    async def get_recent_games(db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent completed games."""
        result = await db.execute(
            select(CrashGame).where(
                CrashGame.status == 'crashed'
            ).order_by(CrashGame.id.desc()).limit(limit)
        )

        games = []
        for game in result.scalars().all():
            games.append({
                "id": game.id,
                "crash_point": game.crash_point,
                "total_bets": game.total_bets,
                "total_wagered": game.total_wagered,
                "total_paid_out": game.total_paid_out,
                "created_at": game.created_at.isoformat(),
                "crashed_at": game.crashed_at.isoformat() if game.crashed_at else None
            })

        return games
