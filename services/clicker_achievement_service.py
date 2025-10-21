"""
Clicker Achievement Service
Handles achievement unlocking, progress tracking, and reward claiming for GEM Clicker Phase 3A.
"""
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from database.models import (
    ClickerAchievement, ClickerStats, ClickerLeaderboard,
    ClickerUpgradePurchase, ClickerPrestige, User, Wallet
)
from config.clicker_achievements import (
    get_achievement, get_all_achievements,
    ACHIEVEMENT_CATEGORIES, calculate_total_achievement_points
)


class ClickerAchievementService:
    """Service for managing clicker achievements"""

    @staticmethod
    async def check_and_unlock_achievements(db: AsyncSession, user_id: str) -> List[Dict]:
        """
        Check user's progress and unlock any newly earned achievements.
        Returns list of newly unlocked achievements.
        """
        newly_unlocked = []

        # Get user's current stats
        stats_result = await db.execute(
            select(ClickerStats).where(ClickerStats.user_id == user_id)
        )
        stats = stats_result.scalar_one_or_none()
        if not stats:
            return []

        # Get leaderboard stats
        leaderboard_result = await db.execute(
            select(ClickerLeaderboard).where(ClickerLeaderboard.user_id == user_id)
        )
        leaderboard = leaderboard_result.scalar_one_or_none()

        # Get prestige stats
        prestige_result = await db.execute(
            select(ClickerPrestige).where(ClickerPrestige.user_id == user_id)
        )
        prestige = prestige_result.scalar_one_or_none()

        # Get already unlocked achievements
        unlocked_result = await db.execute(
            select(ClickerAchievement.achievement_id).where(
                ClickerAchievement.user_id == user_id
            )
        )
        unlocked_ids = {row[0] for row in unlocked_result.all()}

        # Check all achievements
        all_achievements = get_all_achievements()
        for achievement_id, achievement_data in all_achievements.items():
            # Skip if already unlocked
            if achievement_id in unlocked_ids:
                continue

            # Check if user meets requirements
            if await ClickerAchievementService._check_achievement_requirement(
                achievement_data, stats, leaderboard, prestige, db, user_id
            ):
                # Unlock the achievement
                new_unlock = ClickerAchievement(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    achievement_id=achievement_id,
                    unlocked_at=datetime.utcnow(),
                    reward_claimed=False
                )
                db.add(new_unlock)
                newly_unlocked.append({
                    "achievement_id": achievement_id,
                    "name": achievement_data["name"],
                    "description": achievement_data["description"],
                    "category": achievement_data["category"],
                    "icon": achievement_data["icon"],
                    "rarity": achievement_data["rarity"],
                    "reward_gems": achievement_data["reward_gems"],
                    "achievement_points": achievement_data["achievement_points"]
                })

        if newly_unlocked:
            await db.commit()

        return newly_unlocked

    @staticmethod
    async def _check_achievement_requirement(
        achievement: Dict,
        stats: Optional[ClickerStats],
        leaderboard: Optional[ClickerLeaderboard],
        prestige: Optional[ClickerPrestige],
        db: AsyncSession,
        user_id: str
    ) -> bool:
        """Check if user meets the requirement for an achievement"""
        requirement_type = achievement["requirement_type"]
        requirement_value = achievement["requirement_value"]

        if requirement_type == "total_clicks":
            return leaderboard and leaderboard.total_clicks >= requirement_value

        elif requirement_type == "total_gems_earned":
            return leaderboard and leaderboard.total_gems_earned >= requirement_value

        elif requirement_type == "best_combo":
            return leaderboard and leaderboard.best_combo >= requirement_value

        elif requirement_type == "prestige_level":
            return prestige and prestige.prestige_level >= requirement_value

        elif requirement_type == "mega_bonuses":
            return stats and stats.mega_bonuses_hit >= requirement_value

        elif requirement_type == "upgrades_purchased":
            # Count total upgrades purchased
            upgrade_result = await db.execute(
                select(func.count(ClickerUpgradePurchase.id)).where(
                    ClickerUpgradePurchase.user_id == user_id
                )
            )
            upgrade_count = upgrade_result.scalar() or 0
            return upgrade_count >= requirement_value

        return False

    @staticmethod
    async def get_user_achievements(db: AsyncSession, user_id: str) -> Dict:
        """
        Get all achievements with unlock status for a user.
        Returns categorized achievement data with progress.
        """
        # Get unlocked achievements
        unlocked_result = await db.execute(
            select(ClickerAchievement).where(ClickerAchievement.user_id == user_id)
        )
        unlocked_achievements = {
            unlock.achievement_id: {
                "unlocked_at": unlock.unlocked_at.isoformat(),
                "reward_claimed": unlock.reward_claimed
            }
            for unlock in unlocked_result.scalars().all()
        }

        # Get all achievement definitions
        all_achievements = get_all_achievements()

        # Organize by category
        categorized = {}
        for category_id, category_data in ACHIEVEMENT_CATEGORIES.items():
            if category_id == "all":
                continue

            categorized[category_id] = {
                "name": category_data["name"],
                "icon": category_data["icon"],
                "color": category_data["color"],
                "achievements": []
            }

        # Add achievements to categories
        total_unlocked = 0
        total_points_earned = 0

        for achievement_id, achievement_data in all_achievements.items():
            category = achievement_data["category"]
            unlock_data = unlocked_achievements.get(achievement_id)

            achievement_info = {
                "id": achievement_id,
                "name": achievement_data["name"],
                "description": achievement_data["description"],
                "icon": achievement_data["icon"],
                "rarity": achievement_data["rarity"],
                "reward_gems": achievement_data["reward_gems"],
                "achievement_points": achievement_data["achievement_points"],
                "requirement_type": achievement_data["requirement_type"],
                "requirement_value": achievement_data["requirement_value"],
                "unlocked": unlock_data is not None,
                "unlocked_at": unlock_data["unlocked_at"] if unlock_data else None,
                "reward_claimed": unlock_data["reward_claimed"] if unlock_data else False
            }

            if unlock_data:
                total_unlocked += 1
                total_points_earned += achievement_data["achievement_points"]

            categorized[category]["achievements"].append(achievement_info)

        return {
            "categories": categorized,
            "summary": {
                "total_achievements": len(all_achievements),
                "total_unlocked": total_unlocked,
                "completion_percentage": round((total_unlocked / len(all_achievements)) * 100, 1),
                "total_points_earned": total_points_earned,
                "total_points_possible": calculate_total_achievement_points()
            }
        }

    @staticmethod
    async def claim_achievement_reward(db: AsyncSession, user_id: str, achievement_id: str) -> Optional[Dict]:
        """
        Claim reward for an unlocked achievement.
        Returns reward info if successful, None if already claimed or not unlocked.
        """
        # Get the achievement unlock record
        unlock_result = await db.execute(
            select(ClickerAchievement).where(
                and_(
                    ClickerAchievement.user_id == user_id,
                    ClickerAchievement.achievement_id == achievement_id
                )
            )
        )
        unlock = unlock_result.scalar_one_or_none()

        if not unlock:
            return None  # Achievement not unlocked

        if unlock.reward_claimed:
            return None  # Reward already claimed

        # Get achievement data
        achievement_data = get_achievement(achievement_id)
        if not achievement_data:
            return None

        # Mark reward as claimed
        unlock.reward_claimed = True

        # Add GEM reward to user wallet
        wallet_result = await db.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallet = wallet_result.scalar_one_or_none()
        if wallet:
            wallet.gem_balance += achievement_data["reward_gems"]

        await db.commit()

        return {
            "achievement_id": achievement_id,
            "name": achievement_data["name"],
            "reward_gems": achievement_data["reward_gems"],
            "achievement_points": achievement_data["achievement_points"]
        }

    @staticmethod
    async def get_recent_unlocks(db: AsyncSession, user_id: str, limit: int = 5) -> List[Dict]:
        """Get recently unlocked achievements for a user"""
        result = await db.execute(
            select(ClickerAchievement)
            .where(ClickerAchievement.user_id == user_id)
            .order_by(ClickerAchievement.unlocked_at.desc())
            .limit(limit)
        )
        unlocks = result.scalars().all()

        recent = []
        for unlock in unlocks:
            achievement_data = get_achievement(unlock.achievement_id)
            if achievement_data:
                recent.append({
                    "achievement_id": unlock.achievement_id,
                    "name": achievement_data["name"],
                    "description": achievement_data["description"],
                    "icon": achievement_data["icon"],
                    "rarity": achievement_data["rarity"],
                    "unlocked_at": unlock.unlocked_at.isoformat(),
                    "reward_claimed": unlock.reward_claimed
                })

        return recent
