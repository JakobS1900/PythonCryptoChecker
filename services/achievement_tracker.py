"""
Achievement tracking service for CryptoChecker GEM Marketplace.

Handles unlocking achievements, tracking progress, and awarding rewards.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database.models import User, AchievementUnlocked
from config.achievements import (
    get_achievements_for_trigger,
    get_achievement,
    ALL_ACHIEVEMENTS
)


class AchievementTracker:
    """Manages achievement tracking and rewards."""

    async def check_achievements(
        self,
        user_id: str,
        trigger: str,
        value: float,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Check if any achievements should be unlocked for this event.

        Args:
            user_id: User ID
            trigger: Achievement trigger name (e.g., "roulette_first_win")
            value: Current value for the trigger (e.g., number of wins, GEM amount)
            db: Database session

        Returns:
            List of newly unlocked achievements
        """
        unlocked = []

        # Get all achievements for this trigger
        relevant_achievements = get_achievements_for_trigger(trigger)

        for achievement_def in relevant_achievements:
            # Check if user already has this achievement
            result = await db.execute(
                select(AchievementUnlocked).where(
                    and_(
                        AchievementUnlocked.user_id == user_id,
                        AchievementUnlocked.achievement_key == achievement_def["id"]
                    )
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                continue  # Already unlocked

            # Check if target is reached
            target = achievement_def["target"]
            if value >= target:
                # Unlock achievement!
                achievement = await self.unlock_achievement(
                    user_id=user_id,
                    achievement_key=achievement_def["id"],
                    progress_value=value,
                    db=db
                )
                unlocked.append(achievement)

        return unlocked

    async def unlock_achievement(
        self,
        user_id: str,
        achievement_key: str,
        progress_value: Optional[float],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Unlock an achievement for a user.

        Args:
            user_id: User ID
            achievement_key: Achievement ID from config
            progress_value: Optional progress value
            db: Database session

        Returns:
            Achievement data
        """
        achievement_def = get_achievement(achievement_key)
        if not achievement_def:
            raise ValueError(f"Achievement {achievement_key} not found")

        # Create achievement unlock record
        achievement = AchievementUnlocked(
            id=str(uuid.uuid4()),
            user_id=user_id,
            achievement_key=achievement_key,
            reward_amount=achievement_def["reward"],
            progress_value=progress_value,
            unlocked_at=datetime.utcnow(),
            reward_claimed=False
        )

        db.add(achievement)
        await db.commit()
        await db.refresh(achievement)

        return {
            "id": achievement.id,
            "achievement_key": achievement_key,
            "name": achievement_def["name"],
            "description": achievement_def["description"],
            "reward": achievement_def["reward"],
            "category": achievement_def["category"],
            "rarity": achievement_def["rarity"],
            "icon": achievement_def["icon"],
            "unlocked_at": achievement.unlocked_at.isoformat(),
            "progress_value": progress_value
        }

    async def claim_achievement_reward(
        self,
        user_id: str,
        achievement_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Claim the GEM reward for an unlocked achievement.

        Args:
            user_id: User ID
            achievement_id: Achievement unlock record ID
            db: Database session

        Returns:
            Claim result with new balance
        """
        # Get achievement unlock record
        result = await db.execute(
            select(AchievementUnlocked).where(
                and_(
                    AchievementUnlocked.id == achievement_id,
                    AchievementUnlocked.user_id == user_id
                )
            )
        )
        achievement = result.scalar_one_or_none()

        if not achievement:
            raise ValueError("Achievement not found or does not belong to user")

        if achievement.reward_claimed:
            raise ValueError("Reward already claimed")

        # Get user
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one()

        # Add GEM to balance
        user.gem_balance += achievement.reward_amount

        # Mark as claimed
        achievement.reward_claimed = True
        achievement.reward_claimed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)

        return {
            "success": True,
            "reward_amount": achievement.reward_amount,
            "new_balance": user.gem_balance,
            "claimed_at": achievement.reward_claimed_at.isoformat()
        }

    async def get_user_achievements(
        self,
        user_id: str,
        db: AsyncSession,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all achievements for a user (unlocked and locked).

        Args:
            user_id: User ID
            db: Database session
            category: Optional category filter

        Returns:
            Achievement data with unlock status
        """
        # Get all unlocked achievements for user
        result = await db.execute(
            select(AchievementUnlocked).where(
                AchievementUnlocked.user_id == user_id
            )
        )
        unlocked_records = result.scalars().all()

        # Create lookup
        unlocked_map = {a.achievement_key: a for a in unlocked_records}

        # Build response with all achievements
        achievements_to_show = ALL_ACHIEVEMENTS
        if category:
            achievements_to_show = [a for a in ALL_ACHIEVEMENTS if a["category"] == category]

        achievements = []
        for achievement_def in achievements_to_show:
            unlock_record = unlocked_map.get(achievement_def["id"])

            achievement_data = {
                "id": achievement_def["id"],
                "name": achievement_def["name"],
                "description": achievement_def["description"],
                "reward": achievement_def["reward"],
                "category": achievement_def["category"],
                "rarity": achievement_def["rarity"],
                "icon": achievement_def["icon"],
                "target": achievement_def["target"],
                "is_unlocked": unlock_record is not None
            }

            if unlock_record:
                achievement_data.update({
                    "unlock_id": unlock_record.id,
                    "unlocked_at": unlock_record.unlocked_at.isoformat(),
                    "progress_value": unlock_record.progress_value,
                    "reward_claimed": unlock_record.reward_claimed,
                    "reward_claimed_at": unlock_record.reward_claimed_at.isoformat() if unlock_record.reward_claimed_at else None
                })
            else:
                achievement_data.update({
                    "unlock_id": None,
                    "unlocked_at": None,
                    "progress_value": None,
                    "reward_claimed": False,
                    "reward_claimed_at": None
                })

            achievements.append(achievement_data)

        # Calculate stats
        total_unlocked = len(unlocked_records)
        total_claimed = len([a for a in unlocked_records if a.reward_claimed])
        total_unclaimed_rewards = sum(
            a.reward_amount for a in unlocked_records if not a.reward_claimed
        )

        return {
            "achievements": achievements,
            "stats": {
                "total_achievements": len(ALL_ACHIEVEMENTS),
                "total_unlocked": total_unlocked,
                "total_claimed": total_claimed,
                "unclaimed_rewards": total_unclaimed_rewards,
                "completion_percentage": round((total_unlocked / len(ALL_ACHIEVEMENTS)) * 100, 1)
            }
        }

    async def track_win_streak(
        self,
        user_id: str,
        current_streak: int,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Helper method to track win streaks.

        Args:
            user_id: User ID
            current_streak: Current win streak count
            db: Database session

        Returns:
            List of newly unlocked achievements
        """
        return await self.check_achievements(
            user_id=user_id,
            trigger="roulette_win_streak",
            value=current_streak,
            db=db
        )


# Global instance
achievement_tracker = AchievementTracker()
