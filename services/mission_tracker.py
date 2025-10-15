"""
Mission Tracker Service
Handles tracking user progress on daily missions and weekly challenges
"""

import asyncio
from datetime import datetime, date, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from config.missions import (
    DAILY_MISSIONS,
    WEEKLY_CHALLENGES,
    get_mission_by_id,
    get_challenge_by_id,
    get_missions_for_event,
    get_current_week_start,
    EVENT_TYPE_MAP
)
from database.database import get_db
from database.models import User

class MissionTracker:
    """Service for tracking and managing user mission progress."""

    def __init__(self):
        self.daily_missions = DAILY_MISSIONS
        self.weekly_challenges = WEEKLY_CHALLENGES

    async def initialize_daily_missions(self, user_id: int, db: AsyncSession):
        """
        Initialize today's daily missions for a user if they don't exist.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            List of initialized mission records
        """
        today = date.today()

        # Check if missions already initialized for today
        existing = await db.execute(
            text("""
            SELECT mission_id FROM daily_missions_progress
            WHERE user_id = :user_id AND date = :date
            """),
            {"user_id": user_id, "date": today}
        )
        existing_ids = [row[0] for row in existing.fetchall()]

        initialized = []

        for mission in self.daily_missions:
            if mission["id"] not in existing_ids:
                # Insert new mission progress
                result = await db.execute(
                    text("""
                    INSERT INTO daily_missions_progress
                    (user_id, mission_id, mission_name, mission_description, progress, target, reward_gems, date)
                    VALUES (:user_id, :mission_id, :name, :description, 0, :target, :reward, :date)
                    RETURNING id
                    """),
                    {
                        "user_id": user_id,
                        "mission_id": mission["id"],
                        "name": mission["name"],
                        "description": mission["description"],
                        "target": mission["target"],
                        "reward": mission["reward"],
                        "date": today
                    }
                )
                initialized.append(mission["id"])

        await db.commit()
        return initialized

    async def initialize_weekly_challenges(self, user_id: int, db: AsyncSession):
        """
        Initialize this week's challenges for a user if they don't exist.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            List of initialized challenge records
        """
        week_start = get_current_week_start()

        # Check if challenges already initialized for this week
        existing = await db.execute(
            text("""
            SELECT challenge_id FROM weekly_challenges_progress
            WHERE user_id = :user_id AND week_start = :week_start
            """),
            {"user_id": user_id, "week_start": week_start}
        )
        existing_ids = [row[0] for row in existing.fetchall()]

        initialized = []

        for challenge in self.weekly_challenges:
            if challenge["id"] not in existing_ids:
                # Insert new challenge progress
                result = await db.execute(
                    text("""
                    INSERT INTO weekly_challenges_progress
                    (user_id, challenge_id, challenge_name, challenge_description, progress, target, reward_gems, week_start)
                    VALUES (:user_id, :challenge_id, :name, :description, 0, :target, :reward, :week_start)
                    RETURNING id
                    """),
                    {
                        "user_id": user_id,
                        "challenge_id": challenge["id"],
                        "name": challenge["name"],
                        "description": challenge["description"],
                        "target": challenge["target"],
                        "reward": challenge["reward"],
                        "week_start": week_start
                    }
                )
                initialized.append(challenge["id"])

        await db.commit()
        return initialized

    async def track_event(
        self,
        user_id: int,
        event_name: str,
        amount: int = 1,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Track an event and update relevant mission/challenge progress.

        Args:
            user_id: User ID
            event_name: Event identifier (e.g., 'user_login', 'roulette_bet_placed')
            amount: Amount to increment progress by (default 1)
            db: Database session (optional, will create if not provided)

        Returns:
            Dict with completed missions/challenges info
        """
        if db is None:
            async for session in get_db():
                db = session
                break

        # Initialize missions if needed
        await self.initialize_daily_missions(user_id, db)
        await self.initialize_weekly_challenges(user_id, db)

        # Get missions/challenges affected by this event
        affected = get_missions_for_event(event_name)

        completed_missions = []
        completed_challenges = []

        # Update daily missions
        today = date.today()
        for mission_id in affected["daily"]:
            mission_def = get_mission_by_id(mission_id)
            if not mission_def:
                continue

            # Update progress
            result = await db.execute(
                text("""
                UPDATE daily_missions_progress
                SET progress = LEAST(progress + :amount, target),
                    completed_at = CASE
                        WHEN progress + :amount >= target AND completed_at IS NULL
                        THEN CURRENT_TIMESTAMP
                        ELSE completed_at
                    END,
                    status = CASE
                        WHEN progress + :amount >= target THEN 'completed'
                        ELSE 'active'
                    END
                WHERE user_id = :user_id
                  AND mission_id = :mission_id
                  AND date = :date
                  AND status = 'active'
                RETURNING id, progress, target, status
                """),
                {
                    "user_id": user_id,
                    "mission_id": mission_id,
                    "amount": amount,
                    "date": today
                }
            )

            row = result.fetchone()
            if row and row[3] == 'completed':
                completed_missions.append({
                    "id": mission_id,
                    "name": mission_def["name"],
                    "reward": mission_def["reward"]
                })

        # Update weekly challenges
        week_start = get_current_week_start()
        for challenge_id in affected["weekly"]:
            challenge_def = get_challenge_by_id(challenge_id)
            if not challenge_def:
                continue

            # Update progress
            result = await db.execute(
                text("""
                UPDATE weekly_challenges_progress
                SET progress = LEAST(progress + :amount, target),
                    completed_at = CASE
                        WHEN progress + :amount >= target AND completed_at IS NULL
                        THEN CURRENT_TIMESTAMP
                        ELSE completed_at
                    END,
                    status = CASE
                        WHEN progress + :amount >= target THEN 'completed'
                        ELSE 'active'
                    END
                WHERE user_id = :user_id
                  AND challenge_id = :challenge_id
                  AND week_start = :week_start
                  AND status = 'active'
                RETURNING id, progress, target, status
                """),
                {
                    "user_id": user_id,
                    "challenge_id": challenge_id,
                    "amount": amount,
                    "week_start": week_start
                }
            )

            row = result.fetchone()
            if row and row[3] == 'completed':
                completed_challenges.append({
                    "id": challenge_id,
                    "name": challenge_def["name"],
                    "reward": challenge_def["reward"]
                })

        await db.commit()

        return {
            "event": event_name,
            "amount": amount,
            "completed_missions": completed_missions,
            "completed_challenges": completed_challenges
        }

    async def get_daily_missions_progress(self, user_id: int, db: AsyncSession) -> List[Dict]:
        """Get user's daily missions with progress."""
        await self.initialize_daily_missions(user_id, db)

        today = date.today()
        result = await db.execute(
            text("""
            SELECT mission_id, mission_name, mission_description, progress, target,
                   status, reward_gems, completed_at, claimed_at
            FROM daily_missions_progress
            WHERE user_id = :user_id AND date = :date
            ORDER BY id
            """),
            {"user_id": user_id, "date": today}
        )

        missions = []
        for row in result.fetchall():
            mission_def = get_mission_by_id(row[0])
            missions.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "progress": row[3],
                "target": row[4],
                "status": row[5],
                "reward": row[6],
                "completed_at": row[7].isoformat() if row[7] else None,
                "claimed_at": row[8].isoformat() if row[8] else None,
                "icon": mission_def["icon"] if mission_def else "bi-star",
                "category": mission_def["category"] if mission_def else "general"
            })

        return missions

    async def get_weekly_challenges_progress(self, user_id: int, db: AsyncSession) -> List[Dict]:
        """Get user's weekly challenges with progress."""
        await self.initialize_weekly_challenges(user_id, db)

        week_start = get_current_week_start()
        result = await db.execute(
            text("""
            SELECT challenge_id, challenge_name, challenge_description, progress, target,
                   status, reward_gems, completed_at, claimed_at
            FROM weekly_challenges_progress
            WHERE user_id = :user_id AND week_start = :week_start
            ORDER BY id
            """),
            {"user_id": user_id, "week_start": week_start}
        )

        challenges = []
        for row in result.fetchall():
            challenge_def = get_challenge_by_id(row[0])
            challenges.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "progress": row[3],
                "target": row[4],
                "status": row[5],
                "reward": row[6],
                "completed_at": row[7].isoformat() if row[7] else None,
                "claimed_at": row[8].isoformat() if row[8] else None,
                "icon": challenge_def["icon"] if challenge_def else "bi-trophy",
                "difficulty": challenge_def.get("difficulty", "medium") if challenge_def else "medium"
            })

        return challenges

    async def claim_mission_reward(self, user_id: int, mission_id: str, db: AsyncSession) -> Dict[str, Any]:
        """
        Claim reward for a completed daily mission.

        Args:
            user_id: User ID
            mission_id: Mission ID
            db: Database session

        Returns:
            Dict with claim info and new balance

        Raises:
            ValueError: If mission not found, not completed, or already claimed
        """
        today = date.today()

        # Get mission progress
        result = await db.execute(
            text("""
            SELECT id, status, reward_gems, claimed_at
            FROM daily_missions_progress
            WHERE user_id = :user_id AND mission_id = :mission_id AND date = :date
            """),
            {"user_id": user_id, "mission_id": mission_id, "date": today}
        )

        row = result.fetchone()
        if not row:
            raise ValueError(f"Mission {mission_id} not found for today")

        progress_id, status, reward, claimed_at = row

        if status != 'completed':
            raise ValueError(f"Mission {mission_id} not completed yet")

        if claimed_at:
            raise ValueError(f"Mission {mission_id} already claimed")

        # Mark as claimed
        await db.execute(
            text("""
            UPDATE daily_missions_progress
            SET claimed_at = CURRENT_TIMESTAMP,
                status = 'claimed'
            WHERE id = :id
            """),
            {"id": progress_id}
        )

        # Get current balance before update
        balance_result = await db.execute(
            text("SELECT gem_balance FROM wallets WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        balance_before = balance_result.scalar() or 0.0
        balance_after = balance_before + reward

        # Add GEM to user wallet balance
        await db.execute(
            text("""
            UPDATE wallets
            SET gem_balance = gem_balance + :reward
            WHERE user_id = :user_id
            """),
            {"reward": reward, "user_id": user_id}
        )

        # Log transaction with proper schema (including id)
        import uuid
        transaction_id = str(uuid.uuid4())
        await db.execute(
            text("""
            INSERT INTO transactions (id, user_id, transaction_type, amount, balance_before, balance_after, description, created_at)
            VALUES (:id, :user_id, :transaction_type, :amount, :balance_before, :balance_after, :description, CURRENT_TIMESTAMP)
            """),
            {
                "id": transaction_id,
                "user_id": user_id,
                "transaction_type": "BONUS",
                "amount": reward,
                "balance_before": balance_before,
                "balance_after": balance_after,
                "description": f"Daily Mission: {mission_id}"
            }
        )

        await db.commit()
        new_balance = balance_after

        return {
            "mission_id": mission_id,
            "reward_claimed": reward,
            "new_balance": new_balance
        }

    async def claim_challenge_reward(self, user_id: int, challenge_id: str, db: AsyncSession) -> Dict[str, Any]:
        """
        Claim reward for a completed weekly challenge.

        Args:
            user_id: User ID
            challenge_id: Challenge ID
            db: Database session

        Returns:
            Dict with claim info and new balance

        Raises:
            ValueError: If challenge not found, not completed, or already claimed
        """
        week_start = get_current_week_start()

        # Get challenge progress
        result = await db.execute(
            text("""
            SELECT id, status, reward_gems, claimed_at
            FROM weekly_challenges_progress
            WHERE user_id = :user_id AND challenge_id = :challenge_id AND week_start = :week_start
            """),
            {"user_id": user_id, "challenge_id": challenge_id, "week_start": week_start}
        )

        row = result.fetchone()
        if not row:
            raise ValueError(f"Challenge {challenge_id} not found for this week")

        progress_id, status, reward, claimed_at = row

        if status != 'completed':
            raise ValueError(f"Challenge {challenge_id} not completed yet")

        if claimed_at:
            raise ValueError(f"Challenge {challenge_id} already claimed")

        # Mark as claimed
        await db.execute(
            text("""
            UPDATE weekly_challenges_progress
            SET claimed_at = CURRENT_TIMESTAMP,
                status = 'claimed'
            WHERE id = :id
            """),
            {"id": progress_id}
        )

        # Get current balance before update
        balance_result = await db.execute(
            text("SELECT gem_balance FROM wallets WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        balance_before = balance_result.scalar() or 0.0
        balance_after = balance_before + reward

        # Add GEM to user wallet balance
        await db.execute(
            text("""
            UPDATE wallets
            SET gem_balance = gem_balance + :reward
            WHERE user_id = :user_id
            """),
            {"reward": reward, "user_id": user_id}
        )

        # Log transaction with proper schema (including id)
        import uuid
        transaction_id = str(uuid.uuid4())
        await db.execute(
            text("""
            INSERT INTO transactions (id, user_id, transaction_type, amount, balance_before, balance_after, description, created_at)
            VALUES (:id, :user_id, :transaction_type, :amount, :balance_before, :balance_after, :description, CURRENT_TIMESTAMP)
            """),
            {
                "id": transaction_id,
                "user_id": user_id,
                "transaction_type": "BONUS",
                "amount": reward,
                "balance_before": balance_before,
                "balance_after": balance_after,
                "description": f"Weekly Challenge: {challenge_id}"
            }
        )

        await db.commit()
        new_balance = balance_after

        return {
            "challenge_id": challenge_id,
            "reward_claimed": reward,
            "new_balance": new_balance
        }


# Global mission tracker instance
mission_tracker = MissionTracker()
