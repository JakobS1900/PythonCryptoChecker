"""
Clicker Leaderboards Service
Handles leaderboard ranking, player positioning, and competitive features.
"""
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import ClickerLeaderboard, User
from datetime import date, datetime
from typing import List, Dict, Optional


class ClickerLeaderboardService:
    """Service for managing clicker leaderboards and rankings."""

    # Leaderboard categories and their sorting fields
    LEADERBOARD_CATEGORIES = {
        "total_clicks": {"field": "total_clicks", "name": "Total Clicks", "icon": "bi-mouse"},
        "best_combo": {"field": "best_combo", "name": "Best Combo", "icon": "bi-lightning-charge"},
        "total_gems": {"field": "total_gems_earned", "name": "Total GEM Earned", "icon": "bi-gem"},
        "prestige": {"field": "prestige_level", "name": "Prestige Level", "icon": "bi-star"},
        "daily_gems": {"field": "daily_gems_earned", "name": "Daily GEM", "icon": "bi-calendar-day"},
        "speedrun": {"field": "first_million_seconds", "name": "Race to 1M", "icon": "bi-stopwatch"},
    }

    @staticmethod
    async def get_leaderboard(
        db: AsyncSession,
        category: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get top players for a specific leaderboard category.

        Args:
            db: Database session
            category: Leaderboard category (total_clicks, best_combo, etc.)
            limit: Number of results to return (default 100)
            offset: Offset for pagination (default 0)

        Returns:
            List of player data with rankings
        """
        if category not in ClickerLeaderboardService.LEADERBOARD_CATEGORIES:
            raise ValueError(f"Invalid leaderboard category: {category}")

        config = ClickerLeaderboardService.LEADERBOARD_CATEGORIES[category]
        sort_field = getattr(ClickerLeaderboard, config["field"])

        # Build query
        query = (
            select(
                ClickerLeaderboard,
                User.username,
                User.avatar_url
            )
            .join(User, ClickerLeaderboard.user_id == User.id)
            .order_by(desc(sort_field))
        )

        # Special handling for speedrun (exclude null times)
        if category == "speedrun":
            query = query.where(ClickerLeaderboard.first_million_seconds.isnot(None))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        rows = result.all()

        # Format results with rankings
        leaderboard_data = []
        for rank, (leaderboard, username, avatar_url) in enumerate(rows, start=offset + 1):
            value = getattr(leaderboard, config["field"])

            # Skip entries with no value (0 or None)
            if value is None or (isinstance(value, (int, float)) and value == 0):
                continue

            player_data = {
                "rank": rank,
                "user_id": leaderboard.user_id,
                "username": username,
                "avatar_url": avatar_url,
                "value": value,
                "category": category
            }

            # Add speedrun-specific data
            if category == "speedrun" and leaderboard.first_million_achieved_at:
                player_data["achieved_at"] = leaderboard.first_million_achieved_at.isoformat()

            leaderboard_data.append(player_data)

        return leaderboard_data

    @staticmethod
    async def get_player_ranks(db: AsyncSession, user_id: str) -> Dict[str, Dict]:
        """
        Get player's rank across all leaderboard categories.

        Args:
            db: Database session
            user_id: User ID to get ranks for

        Returns:
            Dictionary of category -> rank data
        """
        ranks = {}

        for category, config in ClickerLeaderboardService.LEADERBOARD_CATEGORIES.items():
            field_name = config["field"]
            sort_field = getattr(ClickerLeaderboard, field_name)

            # Get player's value
            player_query = select(ClickerLeaderboard).where(
                ClickerLeaderboard.user_id == user_id
            )
            player_result = await db.execute(player_query)
            player_leaderboard = player_result.scalar_one_or_none()

            if not player_leaderboard:
                ranks[category] = {
                    "rank": None,
                    "value": 0,
                    "total_players": 0
                }
                continue

            player_value = getattr(player_leaderboard, field_name)

            # Get rank (count how many players have better score)
            rank_query = select(func.count()).select_from(ClickerLeaderboard)

            if category == "speedrun":
                # For speedrun, lower time is better
                rank_query = rank_query.where(
                    ClickerLeaderboard.first_million_seconds.isnot(None),
                    ClickerLeaderboard.first_million_seconds < player_value
                )
            else:
                # For others, higher is better
                rank_query = rank_query.where(
                    sort_field > player_value
                )

            rank_result = await db.execute(rank_query)
            better_count = rank_result.scalar()
            rank = better_count + 1

            # Get total players in this category
            total_query = select(func.count()).select_from(ClickerLeaderboard)
            if category == "speedrun":
                total_query = total_query.where(
                    ClickerLeaderboard.first_million_seconds.isnot(None)
                )
            else:
                total_query = total_query.where(sort_field > 0)

            total_result = await db.execute(total_query)
            total_players = total_result.scalar()

            ranks[category] = {
                "rank": rank,
                "value": player_value,
                "total_players": total_players
            }

        return ranks

    @staticmethod
    async def reset_daily_leaderboard(db: AsyncSession):
        """
        Reset daily GEM earned for all players.
        Called by scheduled task at midnight UTC.
        """
        today = date.today()

        # Get all leaderboard entries
        query = select(ClickerLeaderboard)
        result = await db.execute(query)
        leaderboards = result.scalars().all()

        for leaderboard in leaderboards:
            # Reset if last reset was not today
            if leaderboard.daily_last_reset != today:
                leaderboard.daily_gems_earned = 0.0
                leaderboard.daily_last_reset = today
                leaderboard.updated_at = datetime.utcnow()

        await db.commit()

    @staticmethod
    async def record_million_achievement(
        db: AsyncSession,
        user_id: str,
        seconds_taken: int
    ):
        """
        Record a player's first time reaching 1 million GEM.

        Args:
            db: Database session
            user_id: User ID
            seconds_taken: Time in seconds from account creation to 1M GEM
        """
        query = select(ClickerLeaderboard).where(
            ClickerLeaderboard.user_id == user_id
        )
        result = await db.execute(query)
        leaderboard = result.scalar_one_or_none()

        if not leaderboard:
            return

        # Only record if not already recorded
        if leaderboard.first_million_seconds is None:
            leaderboard.first_million_seconds = seconds_taken
            leaderboard.first_million_achieved_at = datetime.utcnow()
            leaderboard.updated_at = datetime.utcnow()
            await db.commit()

    @staticmethod
    async def update_leaderboard_stats(
        db: AsyncSession,
        user_id: str,
        total_clicks: int = None,
        best_combo: int = None,
        total_gems_earned: float = None,
        prestige_level: int = None,
        daily_gems_earned: float = None
    ):
        """
        Update leaderboard stats for a user.
        Called after game actions (clicks, upgrades, prestige).

        Args:
            db: Database session
            user_id: User ID
            total_clicks: Total clicks count
            best_combo: Best combo achieved
            total_gems_earned: Total GEM earned
            prestige_level: Current prestige level
            daily_gems_earned: Daily GEM earned
        """
        query = select(ClickerLeaderboard).where(
            ClickerLeaderboard.user_id == user_id
        )
        result = await db.execute(query)
        leaderboard = result.scalar_one_or_none()

        if not leaderboard:
            # Create new leaderboard entry
            from database.models import ClickerLeaderboard as LeaderboardModel
            leaderboard = LeaderboardModel(
                user_id=user_id,
                total_clicks=total_clicks or 0,
                best_combo=best_combo or 0,
                total_gems_earned=total_gems_earned or 0.0,
                prestige_level=prestige_level or 0,
                daily_gems_earned=daily_gems_earned or 0.0,
                daily_last_reset=date.today()
            )
            db.add(leaderboard)
        else:
            # Update existing entry
            if total_clicks is not None:
                leaderboard.total_clicks = total_clicks
            if best_combo is not None and best_combo > leaderboard.best_combo:
                leaderboard.best_combo = best_combo
            if total_gems_earned is not None:
                leaderboard.total_gems_earned = total_gems_earned
            if prestige_level is not None:
                leaderboard.prestige_level = prestige_level
            if daily_gems_earned is not None:
                leaderboard.daily_gems_earned = daily_gems_earned

            leaderboard.updated_at = datetime.utcnow()

        await db.commit()

    @staticmethod
    async def get_top_speedrunners(db: AsyncSession, limit: int = 10) -> List[Dict]:
        """
        Get top speedrunners (fastest to reach 1 million GEM).

        Args:
            db: Database session
            limit: Number of results to return

        Returns:
            List of speedrunner data
        """
        query = (
            select(
                ClickerLeaderboard,
                User.username,
                User.avatar_url
            )
            .join(User, ClickerLeaderboard.user_id == User.id)
            .where(ClickerLeaderboard.first_million_seconds.isnot(None))
            .order_by(ClickerLeaderboard.first_million_seconds)
            .limit(limit)
        )

        result = await db.execute(query)
        rows = result.all()

        speedrunners = []
        for rank, (leaderboard, username, avatar_url) in enumerate(rows, start=1):
            speedrunners.append({
                "rank": rank,
                "user_id": leaderboard.user_id,
                "username": username,
                "avatar_url": avatar_url,
                "seconds": leaderboard.first_million_seconds,
                "achieved_at": leaderboard.first_million_achieved_at.isoformat()
            })

        return speedrunners
