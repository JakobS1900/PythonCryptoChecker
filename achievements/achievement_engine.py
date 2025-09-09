"""
Achievement and progression system for gamification platform.
Handles achievement tracking, rewards, and level progression.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func

from database import (
    User, Achievement, UserAchievement, VirtualWallet, VirtualTransaction,
    GameStats, UserInventory, Friendship, DailyReward,
    AchievementStatus, CurrencyType, GameConstants
)
from logger import logger


class AchievementEngine:
    """Core achievement system for tracking progress and awarding rewards."""
    
    def __init__(self):
        self.xp_per_level_base = GameConstants.XP_PER_LEVEL_BASE
        self.xp_scaling = GameConstants.XP_PER_LEVEL_SCALING
        self.level_up_bonus = GameConstants.LEVEL_UP_GEM_BONUS
    
    async def check_user_achievements(
        self,
        session: AsyncSession,
        user_id: str,
        trigger_event: str,
        event_data: Dict[str, Any] = None
    ):
        """Check and update user achievements based on trigger events."""
        
        if not event_data:
            event_data = {}
        
        # Get user's current achievement progress
        user_achievements = await session.execute(
            select(UserAchievement, Achievement)
            .join(Achievement, UserAchievement.achievement_id == Achievement.id)
            .where(UserAchievement.user_id == user_id)
        )
        
        achievement_progress = {
            ua.achievement_id: ua for ua, _ in user_achievements
        }
        
        # Get all active achievements
        all_achievements = await session.execute(
            select(Achievement).where(Achievement.is_active == True)
        )
        
        newly_completed = []
        
        for achievement in all_achievements.scalars():
            user_achievement = achievement_progress.get(achievement.id)
            
            # Create achievement progress if it doesn't exist
            if not user_achievement:
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id,
                    status=AchievementStatus.IN_PROGRESS.value
                )
                session.add(user_achievement)
                achievement_progress[achievement.id] = user_achievement
            
            # Skip if already completed
            if user_achievement.status == AchievementStatus.COMPLETED.value:
                continue
            
            # Check if this event triggers this achievement
            if self._should_check_achievement(achievement, trigger_event):
                updated = await self._update_achievement_progress(
                    session, user_id, achievement, user_achievement, event_data
                )
                
                if updated and user_achievement.status == AchievementStatus.COMPLETED.value:
                    newly_completed.append(achievement)
        
        # Award rewards for newly completed achievements
        for achievement in newly_completed:
            await self._award_achievement_rewards(session, user_id, achievement)
        
        await session.commit()
        
        return newly_completed
    
    async def get_user_achievements(
        self,
        session: AsyncSession,
        user_id: str,
        status_filter: Optional[AchievementStatus] = None
    ) -> List[Dict[str, Any]]:
        """Get user's achievement progress."""
        
        query = (
            select(UserAchievement, Achievement)
            .join(Achievement, UserAchievement.achievement_id == Achievement.id)
            .where(UserAchievement.user_id == user_id)
        )
        
        if status_filter:
            query = query.where(UserAchievement.status == status_filter.value)
        
        query = query.order_by(UserAchievement.completed_at.desc().nullsfirst())
        
        result = await session.execute(query)
        
        achievements = []
        for user_achievement, achievement in result:
            achievements.append({
                "id": achievement.id,
                "name": achievement.name,
                "description": achievement.description,
                "type": achievement.achievement_type,
                "status": user_achievement.status,
                "progress": user_achievement.progress,
                "progress_percentage": user_achievement.progress_percentage,
                "requirement_value": achievement.requirement_value,
                "gem_reward": achievement.gem_reward,
                "xp_reward": achievement.xp_reward,
                "icon_url": achievement.icon_url,
                "color_theme": achievement.color_theme,
                "rarity": achievement.rarity,
                "unlocked_at": user_achievement.unlocked_at.isoformat() if user_achievement.unlocked_at else None,
                "completed_at": user_achievement.completed_at.isoformat() if user_achievement.completed_at else None,
                "is_secret": achievement.is_secret
            })
        
        return achievements
    
    async def calculate_level_progression(
        self,
        session: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """Calculate user's level progression and requirements."""
        
        # Get user data
        user_result = await session.execute(
            select(User, VirtualWallet)
            .join(VirtualWallet, User.id == VirtualWallet.user_id)
            .where(User.id == user_id)
        )
        user_data = user_result.first()
        
        if not user_data:
            raise ValueError("User not found")
        
        user, wallet = user_data
        
        current_level = user.current_level
        current_xp = user.total_experience
        
        # Calculate XP for current level and next level
        current_level_xp = self._calculate_xp_for_level(current_level)
        next_level_xp = self._calculate_xp_for_level(current_level + 1)
        
        # XP progress within current level
        xp_in_current_level = current_xp - current_level_xp
        xp_needed_for_next = next_level_xp - current_xp
        level_progress_percentage = (xp_in_current_level / (next_level_xp - current_level_xp)) * 100
        
        return {
            "current_level": current_level,
            "prestige_level": user.prestige_level,
            "total_experience": current_xp,
            "xp_in_current_level": xp_in_current_level,
            "xp_needed_for_next": max(0, xp_needed_for_next),
            "next_level_xp_requirement": next_level_xp - current_level_xp,
            "level_progress_percentage": min(100, max(0, level_progress_percentage)),
            "can_prestige": current_level >= 50,  # Can prestige at level 50
            "estimated_levels_from_prestige": user.prestige_level * 5  # Each prestige adds 5 effective levels
        }
    
    async def award_experience(
        self,
        session: AsyncSession,
        user_id: str,
        xp_amount: int,
        source: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """Award experience points and handle level ups."""
        
        # Get user data
        user_result = await session.execute(
            select(User, VirtualWallet)
            .join(VirtualWallet, User.id == VirtualWallet.user_id)
            .where(User.id == user_id)
        )
        user_data = user_result.first()
        
        if not user_data:
            raise ValueError("User not found")
        
        user, wallet = user_data
        
        old_level = user.current_level
        old_xp = user.total_experience
        
        # Add experience
        user.total_experience += xp_amount
        wallet.experience_points += xp_amount
        
        # Check for level ups
        level_ups = 0
        total_gem_bonus = 0.0
        
        while True:
            next_level_xp = self._calculate_xp_for_level(user.current_level + 1)
            
            if user.total_experience >= next_level_xp:
                user.current_level += 1
                level_ups += 1
                
                # Award level up bonus
                level_bonus = self.level_up_bonus * user.current_level
                wallet.gem_coins += level_bonus
                wallet.total_gems_earned += level_bonus
                total_gem_bonus += level_bonus
                
                # Log level up transaction
                transaction = VirtualTransaction(
                    wallet_id=wallet.id,
                    transaction_type="EARN",
                    currency_type=CurrencyType.GEM_COINS.value,
                    amount=level_bonus,
                    source="level_up",
                    description=f"Level {user.current_level} bonus!",
                    balance_before=wallet.gem_coins - level_bonus,
                    balance_after=wallet.gem_coins
                )
                session.add(transaction)
                
                # Check for level-based achievements
                await self.check_user_achievements(
                    session, user_id, "level_up",
                    {"new_level": user.current_level, "total_xp": user.total_experience}
                )
            else:
                break
        
        # Log XP transaction
        xp_transaction = VirtualTransaction(
            wallet_id=wallet.id,
            transaction_type="EARN",
            currency_type=CurrencyType.EXPERIENCE_POINTS.value,
            amount=xp_amount,
            source=source,
            description=description,
            balance_before=old_xp,
            balance_after=user.total_experience
        )
        session.add(xp_transaction)
        
        user.updated_at = datetime.utcnow()
        wallet.updated_at = datetime.utcnow()
        
        await session.commit()
        
        result = {
            "xp_awarded": xp_amount,
            "total_xp": user.total_experience,
            "old_level": old_level,
            "new_level": user.current_level,
            "levels_gained": level_ups,
            "gem_bonus_awarded": total_gem_bonus
        }
        
        if level_ups > 0:
            logger.info(f"User {user_id} gained {level_ups} level(s): {old_level} -> {user.current_level}")
        
        return result
    
    async def prestige_user(
        self,
        session: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """Prestige user - reset level but gain permanent bonuses."""
        
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")
        
        if user.current_level < 50:
            raise ValueError("Must be level 50+ to prestige")
        
        old_prestige = user.prestige_level
        old_level = user.current_level
        
        # Increase prestige level
        user.prestige_level += 1
        
        # Reset level but keep some XP based on prestige
        base_xp_after_prestige = user.prestige_level * 10000  # 10k XP per prestige level
        user.current_level = self._calculate_level_from_xp(base_xp_after_prestige)
        user.total_experience = base_xp_after_prestige
        
        # Award prestige bonus
        prestige_bonus = 5000.0 * user.prestige_level  # Increasing bonus per prestige
        
        wallet = await session.execute(
            select(VirtualWallet).where(VirtualWallet.user_id == user_id)
        )
        wallet = wallet.scalar_one()
        
        wallet.gem_coins += prestige_bonus
        wallet.total_gems_earned += prestige_bonus
        
        # Log prestige transaction
        transaction = VirtualTransaction(
            wallet_id=wallet.id,
            transaction_type="EARN",
            currency_type=CurrencyType.GEM_COINS.value,
            amount=prestige_bonus,
            source="prestige",
            description=f"Prestige {user.prestige_level} bonus!",
            balance_before=wallet.gem_coins - prestige_bonus,
            balance_after=wallet.gem_coins
        )
        session.add(transaction)
        
        user.updated_at = datetime.utcnow()
        wallet.updated_at = datetime.utcnow()
        
        await session.commit()
        
        logger.info(f"User {user_id} prestiged: {old_prestige} -> {user.prestige_level}")
        
        return {
            "old_prestige": old_prestige,
            "new_prestige": user.prestige_level,
            "old_level": old_level,
            "new_level": user.current_level,
            "gem_bonus": prestige_bonus,
            "permanent_bonuses": {
                "daily_reward_multiplier": 1 + (user.prestige_level * 0.1),
                "xp_bonus_multiplier": 1 + (user.prestige_level * 0.05),
                "drop_rate_bonus": user.prestige_level * 0.02
            }
        }
    
    def _should_check_achievement(self, achievement: Achievement, trigger_event: str) -> bool:
        """Check if achievement should be evaluated for this event."""
        
        trigger_mappings = {
            "game_played": ["games_played", "total_games_played"],
            "game_won": ["games_won", "win_streak"],
            "level_up": ["level_reached"],
            "item_collected": ["unique_items_collected", "legendary_items_owned"],
            "friend_added": ["friends_count"],
            "daily_login": ["daily_login_streak"],
            "big_win": ["single_game_winnings", "total_winnings"],
            "high_bet": ["single_bet_amount"]
        }
        
        relevant_requirements = trigger_mappings.get(trigger_event, [])
        return achievement.requirement_type in relevant_requirements
    
    async def _update_achievement_progress(
        self,
        session: AsyncSession,
        user_id: str,
        achievement: Achievement,
        user_achievement: UserAchievement,
        event_data: Dict[str, Any]
    ) -> bool:
        """Update achievement progress and check for completion."""
        
        requirement_type = achievement.requirement_type
        requirement_value = achievement.requirement_value
        
        # Get current progress value
        current_value = await self._get_user_metric(session, user_id, requirement_type, event_data)
        
        if current_value is None:
            return False
        
        # Update progress
        old_progress = user_achievement.progress
        user_achievement.progress = min(current_value, requirement_value)
        user_achievement.progress_percentage = (user_achievement.progress / requirement_value) * 100
        
        # Check for completion
        if current_value >= requirement_value and user_achievement.status != AchievementStatus.COMPLETED.value:
            user_achievement.status = AchievementStatus.COMPLETED.value
            user_achievement.completed_at = datetime.utcnow()
            
            if not user_achievement.unlocked_at:
                user_achievement.unlocked_at = datetime.utcnow()
            
            logger.info(f"Achievement completed: {achievement.name} for user {user_id}")
            return True
        
        elif user_achievement.progress > old_progress:
            if user_achievement.status == AchievementStatus.LOCKED.value:
                user_achievement.status = AchievementStatus.IN_PROGRESS.value
                user_achievement.unlocked_at = datetime.utcnow()
            
            return True
        
        return False
    
    async def _get_user_metric(
        self,
        session: AsyncSession,
        user_id: str,
        metric_type: str,
        event_data: Dict[str, Any]
    ) -> Optional[int]:
        """Get user's current value for a specific metric."""
        
        if metric_type == "games_played":
            stats = await session.execute(
                select(GameStats.total_games_played).where(GameStats.user_id == user_id)
            )
            result = stats.scalar()
            return result or 0
        
        elif metric_type == "games_won":
            stats = await session.execute(
                select(GameStats.total_games_won).where(GameStats.user_id == user_id)
            )
            result = stats.scalar()
            return result or 0
        
        elif metric_type == "win_streak":
            stats = await session.execute(
                select(GameStats.current_win_streak).where(GameStats.user_id == user_id)
            )
            result = stats.scalar()
            return result or 0
        
        elif metric_type == "level_reached":
            user = await session.execute(
                select(User.current_level).where(User.id == user_id)
            )
            return user.scalar() or 1
        
        elif metric_type == "unique_items_collected":
            count = await session.execute(
                select(func.count(func.distinct(UserInventory.item_id)))
                .where(UserInventory.user_id == user_id)
            )
            return count.scalar() or 0
        
        elif metric_type == "legendary_items_owned":
            count = await session.execute(
                select(func.sum(UserInventory.quantity))
                .join(CollectibleItem, UserInventory.item_id == CollectibleItem.id)
                .where(
                    and_(
                        UserInventory.user_id == user_id,
                        CollectibleItem.rarity == "LEGENDARY"
                    )
                )
            )
            return count.scalar() or 0
        
        elif metric_type == "friends_count":
            count = await session.execute(
                select(func.count(Friendship.id))
                .where(
                    and_(
                        or_(
                            Friendship.sender_id == user_id,
                            Friendship.receiver_id == user_id
                        ),
                        Friendship.status == "ACCEPTED"
                    )
                )
            )
            return count.scalar() or 0
        
        elif metric_type == "daily_login_streak":
            daily_reward = await session.execute(
                select(DailyReward.current_streak).where(DailyReward.user_id == user_id)
            )
            result = daily_reward.scalar()
            return result or 0
        
        elif metric_type == "single_game_winnings":
            return event_data.get("winnings", 0)
        
        elif metric_type == "single_bet_amount":
            return event_data.get("bet_amount", 0)
        
        elif metric_type == "total_winnings":
            stats = await session.execute(
                select(GameStats.total_amount_won).where(GameStats.user_id == user_id)
            )
            result = stats.scalar()
            return result or 0
        
        return None
    
    async def _award_achievement_rewards(
        self,
        session: AsyncSession,
        user_id: str,
        achievement: Achievement
    ):
        """Award rewards for completed achievement."""
        
        if achievement.gem_reward > 0 or achievement.xp_reward > 0:
            wallet = await session.execute(
                select(VirtualWallet).where(VirtualWallet.user_id == user_id)
            )
            wallet = wallet.scalar_one()
            
            # Award GEM coins
            if achievement.gem_reward > 0:
                old_balance = wallet.gem_coins
                wallet.gem_coins += achievement.gem_reward
                wallet.total_gems_earned += achievement.gem_reward
                
                transaction = VirtualTransaction(
                    wallet_id=wallet.id,
                    transaction_type="EARN",
                    currency_type=CurrencyType.GEM_COINS.value,
                    amount=achievement.gem_reward,
                    source="achievement",
                    description=f"Achievement: {achievement.name}",
                    reference_id=achievement.id,
                    balance_before=old_balance,
                    balance_after=wallet.gem_coins
                )
                session.add(transaction)
            
            # Award XP
            if achievement.xp_reward > 0:
                await self.award_experience(
                    session, user_id, achievement.xp_reward,
                    "achievement", f"Achievement: {achievement.name}"
                )
        
        # Award items if specified
        if achievement.item_rewards:
            for item_id in achievement.item_rewards:
                # Add item to inventory
                inventory_item = UserInventory(
                    user_id=user_id,
                    item_id=item_id,
                    quantity=1,
                    acquisition_method="achievement"
                )
                session.add(inventory_item)
    
    def _calculate_xp_for_level(self, level: int) -> int:
        """Calculate total XP required to reach a specific level."""
        if level <= 1:
            return 0
        
        total_xp = 0
        for l in range(2, level + 1):
            total_xp += int(self.xp_per_level_base * (l - 1) ** self.xp_scaling)
        
        return total_xp
    
    def _calculate_level_from_xp(self, total_xp: int) -> int:
        """Calculate level from total XP."""
        if total_xp < 0:
            return 1
        
        level = 1
        xp_used = 0
        
        while True:
            xp_for_next_level = int(self.xp_per_level_base * level ** self.xp_scaling)
            if xp_used + xp_for_next_level > total_xp:
                break
            
            xp_used += xp_for_next_level
            level += 1
        
        return level


# Create global achievement engine instance
achievement_engine = AchievementEngine()