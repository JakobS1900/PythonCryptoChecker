"""
Leaderboard Service

Handles leaderboard rankings across multiple categories:
- Wealth (total GEM balance)
- Mini-games (profit, wins)
- Trading (volume, profit)
- Roulette (wagered, profit)
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    User, LeaderboardEntry, MiniGameStats, GemTrade,
    GameBet, MiniGame, Transaction, TransactionType
)


class LeaderboardService:
    """Service for leaderboard rankings and updates."""

    # Top N users to display
    TOP_LIMIT = 100

    @staticmethod
    async def update_all_leaderboards(db: AsyncSession):
        """Update all leaderboard categories and timeframes."""
        # Update all-time leaderboards
        await LeaderboardService._update_wealth_leaderboard(db, 'all_time')
        await LeaderboardService._update_minigames_leaderboard(db, 'all_time')
        await LeaderboardService._update_trading_leaderboard(db, 'all_time')
        await LeaderboardService._update_roulette_leaderboard(db, 'all_time')

        # Update weekly leaderboards
        await LeaderboardService._update_wealth_leaderboard(db, 'weekly')
        await LeaderboardService._update_minigames_leaderboard(db, 'weekly')
        await LeaderboardService._update_trading_leaderboard(db, 'weekly')
        await LeaderboardService._update_roulette_leaderboard(db, 'weekly')

        # Update monthly leaderboards
        await LeaderboardService._update_wealth_leaderboard(db, 'monthly')
        await LeaderboardService._update_minigames_leaderboard(db, 'monthly')
        await LeaderboardService._update_trading_leaderboard(db, 'monthly')
        await LeaderboardService._update_roulette_leaderboard(db, 'monthly')

        await db.commit()

    @staticmethod
    async def _update_wealth_leaderboard(db: AsyncSession, timeframe: str):
        """Update wealth leaderboard (richest users by GEM balance)."""
        # Get all users ordered by GEM balance
        result = await db.execute(
            select(User.id, User.username, User.gem_balance)
            .order_by(desc(User.gem_balance))
            .limit(LeaderboardService.TOP_LIMIT)
        )
        users = result.all()

        # Calculate period
        period_start, period_end = LeaderboardService._get_period(timeframe)

        # Delete old entries for this category/timeframe
        await db.execute(
            select(LeaderboardEntry).where(
                and_(
                    LeaderboardEntry.category == 'wealth',
                    LeaderboardEntry.timeframe == timeframe
                )
            )
        )

        # Create new entries
        for rank, (user_id, username, balance) in enumerate(users, 1):
            stats_data = json.dumps({
                'username': username,
                'balance': balance
            })

            entry = LeaderboardEntry(
                user_id=user_id,
                category='wealth',
                timeframe=timeframe,
                rank=rank,
                score=balance,
                stats_data=stats_data,
                period_start=period_start,
                period_end=period_end
            )
            db.add(entry)

    @staticmethod
    async def _update_minigames_leaderboard(db: AsyncSession, timeframe: str):
        """Update mini-games leaderboard (highest profit)."""
        period_start, period_end = LeaderboardService._get_period(timeframe)

        if timeframe == 'all_time':
            # Use MiniGameStats for all-time
            result = await db.execute(
                select(
                    MiniGameStats.user_id,
                    User.username,
                    MiniGameStats.net_profit,
                    MiniGameStats.total_games_won,
                    MiniGameStats.total_games_played
                )
                .join(User, User.id == MiniGameStats.user_id)
                .order_by(desc(MiniGameStats.net_profit))
                .limit(LeaderboardService.TOP_LIMIT)
            )
        else:
            # Calculate from MiniGame records for weekly/monthly
            result = await db.execute(
                select(
                    MiniGame.user_id,
                    User.username,
                    func.sum(MiniGame.profit).label('total_profit'),
                    func.sum(func.cast(MiniGame.won, type_=func.INTEGER)).label('wins'),
                    func.count(MiniGame.id).label('games')
                )
                .join(User, User.id == MiniGame.user_id)
                .where(MiniGame.played_at >= period_start)
                .group_by(MiniGame.user_id, User.username)
                .order_by(desc('total_profit'))
                .limit(LeaderboardService.TOP_LIMIT)
            )

        users = result.all()

        # Delete old entries
        await db.execute(
            select(LeaderboardEntry).where(
                and_(
                    LeaderboardEntry.category == 'minigames',
                    LeaderboardEntry.timeframe == timeframe
                )
            )
        )

        # Create new entries
        for rank, user_data in enumerate(users, 1):
            if timeframe == 'all_time':
                user_id, username, profit, wins, games = user_data
            else:
                user_id, username, profit, wins, games = user_data

            stats_data = json.dumps({
                'username': username,
                'profit': int(profit) if profit else 0,
                'wins': int(wins) if wins else 0,
                'games': int(games) if games else 0
            })

            entry = LeaderboardEntry(
                user_id=user_id,
                category='minigames',
                timeframe=timeframe,
                rank=rank,
                score=int(profit) if profit else 0,
                stats_data=stats_data,
                period_start=period_start,
                period_end=period_end
            )
            db.add(entry)

    @staticmethod
    async def _update_trading_leaderboard(db: AsyncSession, timeframe: str):
        """Update trading leaderboard (highest volume)."""
        period_start, period_end = LeaderboardService._get_period(timeframe)

        # Calculate trading volume (sum of all trades as buyer or seller)
        query = (
            select(
                User.id,
                User.username,
                func.sum(GemTrade.total_value).label('volume')
            )
            .join(GemTrade, or_(
                GemTrade.buyer_id == User.id,
                GemTrade.seller_id == User.id
            ))
        )

        if timeframe != 'all_time':
            query = query.where(GemTrade.created_at >= period_start)

        result = await db.execute(
            query
            .group_by(User.id, User.username)
            .order_by(desc('volume'))
            .limit(LeaderboardService.TOP_LIMIT)
        )

        users = result.all()

        # Delete old entries
        await db.execute(
            select(LeaderboardEntry).where(
                and_(
                    LeaderboardEntry.category == 'trading',
                    LeaderboardEntry.timeframe == timeframe
                )
            )
        )

        # Create new entries
        for rank, (user_id, username, volume) in enumerate(users, 1):
            stats_data = json.dumps({
                'username': username,
                'volume': int(volume) if volume else 0
            })

            entry = LeaderboardEntry(
                user_id=user_id,
                category='trading',
                timeframe=timeframe,
                rank=rank,
                score=int(volume) if volume else 0,
                stats_data=stats_data,
                period_start=period_start,
                period_end=period_end
            )
            db.add(entry)

    @staticmethod
    async def _update_roulette_leaderboard(db: AsyncSession, timeframe: str):
        """Update roulette leaderboard (highest wagered)."""
        period_start, period_end = LeaderboardService._get_period(timeframe)

        # Calculate total wagered from bets
        query = (
            select(
                User.id,
                User.username,
                func.sum(GameBet.amount).label('wagered')
            )
            .join(GameBet, GameBet.user_id == User.id)
        )

        if timeframe != 'all_time':
            query = query.where(GameBet.placed_at >= period_start)

        result = await db.execute(
            query
            .group_by(User.id, User.username)
            .order_by(desc('wagered'))
            .limit(LeaderboardService.TOP_LIMIT)
        )

        users = result.all()

        # Delete old entries
        await db.execute(
            select(LeaderboardEntry).where(
                and_(
                    LeaderboardEntry.category == 'roulette',
                    LeaderboardEntry.timeframe == timeframe
                )
            )
        )

        # Create new entries
        for rank, (user_id, username, wagered) in enumerate(users, 1):
            stats_data = json.dumps({
                'username': username,
                'wagered': int(wagered) if wagered else 0
            })

            entry = LeaderboardEntry(
                user_id=user_id,
                category='roulette',
                timeframe=timeframe,
                rank=rank,
                score=int(wagered) if wagered else 0,
                stats_data=stats_data,
                period_start=period_start,
                period_end=period_end
            )
            db.add(entry)

    @staticmethod
    def _get_period(timeframe: str) -> tuple:
        """Get period start and end for timeframe."""
        now = datetime.utcnow()

        if timeframe == 'weekly':
            # Start of current week (Monday)
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
            return (start, end)

        elif timeframe == 'monthly':
            # Start of current month
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Start of next month
            if now.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
            return (start, end)

        else:  # all_time
            start = datetime(2020, 1, 1)
            end = None
            return (start, end)

    @staticmethod
    async def get_leaderboard(
        category: str,
        timeframe: str,
        db: AsyncSession,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get leaderboard for a specific category and timeframe."""
        result = await db.execute(
            select(LeaderboardEntry)
            .where(
                and_(
                    LeaderboardEntry.category == category,
                    LeaderboardEntry.timeframe == timeframe
                )
            )
            .order_by(LeaderboardEntry.rank)
            .limit(limit)
        )
        entries = result.scalars().all()

        return [
            {
                'rank': entry.rank,
                'user_id': entry.user_id,
                'score': entry.score,
                'stats': json.loads(entry.stats_data) if entry.stats_data else {},
                'period_start': entry.period_start.isoformat() if entry.period_start else None,
                'period_end': entry.period_end.isoformat() if entry.period_end else None
            }
            for entry in entries
        ]

    @staticmethod
    async def get_user_rank(
        user_id: str,
        category: str,
        timeframe: str,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Get a specific user's rank in a leaderboard."""
        result = await db.execute(
            select(LeaderboardEntry)
            .where(
                and_(
                    LeaderboardEntry.user_id == user_id,
                    LeaderboardEntry.category == category,
                    LeaderboardEntry.timeframe == timeframe
                )
            )
        )
        entry = result.scalar_one_or_none()

        if not entry:
            return None

        return {
            'rank': entry.rank,
            'score': entry.score,
            'stats': json.loads(entry.stats_data) if entry.stats_data else {}
        }
