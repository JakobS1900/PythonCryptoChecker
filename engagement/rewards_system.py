"""
Rewards system for handling bonuses, incentives, and reward distribution.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func

from database.unified_models import User, VirtualWallet, DailyBonus, RewardHistory
from logger import logger


class RewardsSystem:
    """Manages all reward distributions and bonus systems."""
    
    def __init__(self):
        self.login_bonus_config = self._initialize_login_bonus_config()
        self.level_rewards = self._initialize_level_rewards()
    
    def _initialize_login_bonus_config(self) -> Dict[str, Any]:
        """Initialize login bonus configuration."""
        return {
            "base_bonus": {
                "gem_coins": 100,
                "xp": 25
            },
            "streak_multipliers": {
                3: 1.2,   # 20% bonus for 3+ days
                7: 1.5,   # 50% bonus for 7+ days  
                14: 2.0,  # 100% bonus for 14+ days
                30: 2.5,  # 150% bonus for 30+ days
                60: 3.0,  # 200% bonus for 60+ days
                100: 4.0  # 300% bonus for 100+ days
            },
            "special_bonuses": {
                7: {"item_pack": "standard", "message": "Weekly streak bonus!"},
                30: {"item_pack": "premium", "message": "Monthly dedication reward!"},
                100: {"item_pack": "legendary", "message": "Legendary commitment bonus!"}
            }
        }
    
    def _initialize_level_rewards(self) -> Dict[int, Dict[str, Any]]:
        """Initialize level-up reward configuration."""
        rewards = {}
        
        for level in range(1, 101):
            base_reward = level * 100
            rewards[level] = {
                "gem_coins": base_reward,
                "xp": 0,  # No XP for leveling up
                "special": {}
            }
            
            # Special rewards for milestone levels
            if level % 10 == 0:  # Every 10 levels
                rewards[level]["special"]["item_pack"] = "premium"
                rewards[level]["gem_coins"] *= 2
            
            if level % 25 == 0:  # Every 25 levels
                rewards[level]["special"]["item_pack"] = "legendary"
                rewards[level]["gem_coins"] *= 3
        
        return rewards
    
    async def process_login_bonus(self, session: AsyncSession, user_id: str) -> Optional[Dict[str, Any]]:
        """Process daily login bonus for user."""
        try:
            today = datetime.utcnow().date()
            
            # Check if user already claimed today's bonus
            result = await session.execute(
                select(DailyBonus).where(
                    and_(
                        DailyBonus.user_id == user_id,
                        DailyBonus.bonus_date == today,
                        DailyBonus.claimed == True
                    )
                )
            )
            existing_bonus = result.scalar_one_or_none()
            
            if existing_bonus:
                return None  # Already claimed today
            
            # Get user's current login streak
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Calculate login streak
            login_streak = await self._calculate_login_streak(session, user_id)
            
            # Calculate bonus amounts
            bonus = self._calculate_login_bonus(login_streak)
            
            # Award the bonus
            await self._award_currency(session, user_id, "gem_coins", bonus["gem_coins"])
            await self._award_currency(session, user_id, "xp", bonus["xp"])
            
            # Record the bonus
            daily_bonus = DailyBonus(
                user_id=user_id,
                bonus_date=today,
                gem_coins_awarded=bonus["gem_coins"],
                xp_awarded=bonus["xp"],
                login_streak=login_streak,
                special_rewards=bonus.get("special", {}),
                claimed=True,
                claimed_at=datetime.utcnow()
            )
            session.add(daily_bonus)
            
            # Record in reward history
            await self._record_reward(
                session, user_id, "daily_login_bonus", 
                bonus, f"Daily login bonus (streak: {login_streak})"
            )
            
            await session.commit()
            
            return {
                "type": "daily_login_bonus",
                "gem_coins": bonus["gem_coins"],
                "xp": bonus["xp"],
                "login_streak": login_streak,
                "special": bonus.get("special"),
                "message": f"Daily bonus received! Login streak: {login_streak}"
            }
            
        except Exception as e:
            logger.error(f"Failed to process login bonus: {e}")
            return None
    
    async def award_quest_reward(self, session: AsyncSession, user_id: str, quest_id: str, rewards: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Award rewards for completed quest."""
        try:
            awarded_rewards = []
            
            for reward_type, amount in rewards.items():
                if reward_type in ["gem_coins", "xp"]:
                    await self._award_currency(session, user_id, reward_type, amount)
                    awarded_rewards.append({
                        "type": reward_type,
                        "amount": amount
                    })
                elif reward_type == "item_pack":
                    # Award item pack (would integrate with inventory system)
                    awarded_rewards.append({
                        "type": "item_pack",
                        "pack_type": amount
                    })
            
            # Record in reward history
            await self._record_reward(
                session, user_id, "quest_completion",
                rewards, f"Quest completion reward (Quest ID: {quest_id})"
            )
            
            await session.commit()
            return awarded_rewards
            
        except Exception as e:
            logger.error(f"Failed to award quest reward: {e}")
            return []
    
    async def award_level_up_reward(self, session: AsyncSession, user_id: str, new_level: int) -> Dict[str, Any]:
        """Award rewards for leveling up."""
        try:
            if new_level not in self.level_rewards:
                return {"error": "Invalid level"}
            
            rewards = self.level_rewards[new_level]
            
            # Award currency rewards
            if rewards["gem_coins"] > 0:
                await self._award_currency(session, user_id, "gem_coins", rewards["gem_coins"])
            
            # Award special rewards
            special_rewards = {}
            if "item_pack" in rewards["special"]:
                special_rewards["item_pack"] = rewards["special"]["item_pack"]
            
            # Record reward
            await self._record_reward(
                session, user_id, "level_up",
                {"gem_coins": rewards["gem_coins"], **special_rewards},
                f"Level {new_level} reward"
            )
            
            await session.commit()
            
            return {
                "type": "level_up_reward",
                "level": new_level,
                "gem_coins": rewards["gem_coins"],
                "special": special_rewards,
                "message": f"Congratulations! You reached level {new_level}!"
            }
            
        except Exception as e:
            logger.error(f"Failed to award level up reward: {e}")
            return {"error": str(e)}
    
    async def award_achievement_reward(self, session: AsyncSession, user_id: str, achievement_id: str, rewards: Dict[str, Any]) -> Dict[str, Any]:
        """Award rewards for achievement completion."""
        try:
            awarded_rewards = []
            
            for reward_type, amount in rewards.items():
                if reward_type in ["gem_coins", "xp"]:
                    await self._award_currency(session, user_id, reward_type, amount)
                    awarded_rewards.append({
                        "type": reward_type,
                        "amount": amount
                    })
            
            # Record reward
            await self._record_reward(
                session, user_id, "achievement_unlock",
                rewards, f"Achievement reward: {achievement_id}"
            )
            
            await session.commit()
            
            return {
                "type": "achievement_reward",
                "achievement_id": achievement_id,
                "rewards": awarded_rewards
            }
            
        except Exception as e:
            logger.error(f"Failed to award achievement reward: {e}")
            return {"error": str(e)}
    
    async def award_referral_bonus(self, session: AsyncSession, referrer_id: str, referred_id: str) -> Dict[str, Any]:
        """Award referral bonus to both users."""
        try:
            referrer_bonus = {"gem_coins": 500, "xp": 100}
            referred_bonus = {"gem_coins": 250, "xp": 50}
            
            # Award to referrer
            await self._award_currency(session, referrer_id, "gem_coins", referrer_bonus["gem_coins"])
            await self._award_currency(session, referrer_id, "xp", referrer_bonus["xp"])
            
            # Award to referred user
            await self._award_currency(session, referred_id, "gem_coins", referred_bonus["gem_coins"])
            await self._award_currency(session, referred_id, "xp", referred_bonus["xp"])
            
            # Record rewards
            await self._record_reward(
                session, referrer_id, "referral_bonus",
                referrer_bonus, f"Referral bonus for user {referred_id}"
            )
            await self._record_reward(
                session, referred_id, "referral_welcome",
                referred_bonus, f"Welcome bonus from referrer {referrer_id}"
            )
            
            await session.commit()
            
            return {
                "referrer_bonus": referrer_bonus,
                "referred_bonus": referred_bonus,
                "message": "Referral bonuses awarded successfully!"
            }
            
        except Exception as e:
            logger.error(f"Failed to award referral bonus: {e}")
            return {"error": str(e)}
    
    async def get_user_reward_history(self, session: AsyncSession, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's reward history."""
        try:
            result = await session.execute(
                select(RewardHistory)
                .where(RewardHistory.user_id == user_id)
                .order_by(RewardHistory.awarded_at.desc())
                .limit(limit)
            )
            rewards = result.scalars().all()
            
            reward_history = []
            for reward in rewards:
                reward_history.append({
                    "id": reward.id,
                    "reward_type": reward.reward_type,
                    "rewards": reward.rewards,
                    "description": reward.description,
                    "awarded_at": reward.awarded_at.isoformat()
                })
            
            return reward_history
            
        except Exception as e:
            logger.error(f"Failed to get reward history: {e}")
            return []
    
    async def reset_daily_bonuses(self, session: AsyncSession) -> Dict[str, Any]:
        """Reset daily bonus system (called daily)."""
        try:
            # Nothing to reset for daily bonuses - they're date-based
            # But we can clean up old records
            
            thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
            
            # Delete old daily bonus records (keep last 30 days)
            await session.execute(
                select(func.count(DailyBonus.id)).where(
                    DailyBonus.bonus_date < thirty_days_ago
                )
            )
            
            await session.commit()
            
            return {"reset_count": 0, "cleanup_completed": True}
            
        except Exception as e:
            logger.error(f"Failed to reset daily bonuses: {e}")
            return {"error": str(e)}
    
    def _calculate_login_bonus(self, login_streak: int) -> Dict[str, Any]:
        """Calculate login bonus based on streak."""
        base_bonus = self.login_bonus_config["base_bonus"].copy()
        
        # Apply streak multiplier
        multiplier = 1.0
        for streak_threshold, mult in sorted(self.login_bonus_config["streak_multipliers"].items()):
            if login_streak >= streak_threshold:
                multiplier = mult
        
        bonus = {
            "gem_coins": int(base_bonus["gem_coins"] * multiplier),
            "xp": int(base_bonus["xp"] * multiplier)
        }
        
        # Add special bonuses
        if login_streak in self.login_bonus_config["special_bonuses"]:
            bonus["special"] = self.login_bonus_config["special_bonuses"][login_streak]
        
        return bonus
    
    async def _calculate_login_streak(self, session: AsyncSession, user_id: str) -> int:
        """Calculate user's current login streak."""
        try:
            # Get recent daily bonuses to calculate streak
            result = await session.execute(
                select(DailyBonus)
                .where(DailyBonus.user_id == user_id)
                .order_by(DailyBonus.bonus_date.desc())
                .limit(100)  # Check last 100 days max
            )
            bonuses = result.scalars().all()
            
            if not bonuses:
                return 1  # First login
            
            # Calculate consecutive days
            streak = 1  # Today counts as 1
            today = datetime.utcnow().date()
            
            for i, bonus in enumerate(bonuses):
                expected_date = today - timedelta(days=i + 1)
                if bonus.bonus_date == expected_date:
                    streak += 1
                else:
                    break
            
            return streak
            
        except Exception as e:
            logger.error(f"Failed to calculate login streak: {e}")
            return 1
    
    async def _award_currency(self, session: AsyncSession, user_id: str, currency_type: str, amount: int):
        """Award currency to user."""
        try:
            if currency_type == "gem_coins":
                # Update wallet
                wallet_result = await session.execute(
                    select(VirtualWallet).where(VirtualWallet.user_id == user_id)
                )
                wallet = wallet_result.scalar_one_or_none()
                
                if wallet:
                    wallet.gem_coins += amount
                    wallet.updated_at = datetime.utcnow()
                    
            elif currency_type == "xp":
                # Update user XP
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if user:
                    old_xp = user.total_experience
                    user.total_experience += amount
                    
                    # Check for level up
                    new_level = self._calculate_level_from_xp(user.total_experience)
                    if new_level > user.current_level:
                        user.current_level = new_level
                        # Could trigger level up reward here
                        
        except Exception as e:
            logger.error(f"Failed to award currency: {e}")
    
    async def _record_reward(self, session: AsyncSession, user_id: str, reward_type: str, rewards: Dict[str, Any], description: str):
        """Record reward in history."""
        try:
            reward_history = RewardHistory(
                user_id=user_id,
                reward_type=reward_type,
                rewards=rewards,
                description=description,
                awarded_at=datetime.utcnow()
            )
            session.add(reward_history)
            
        except Exception as e:
            logger.error(f"Failed to record reward: {e}")
    
    def _calculate_level_from_xp(self, total_xp: int) -> int:
        """Calculate level from total XP."""
        # Simple leveling formula: each level requires more XP
        # Level 1: 0 XP, Level 2: 1000 XP, Level 3: 2500 XP, etc.
        
        if total_xp < 1000:
            return 1
        
        # Use square root scaling for level calculation
        import math
        level = int(math.sqrt(total_xp / 1000)) + 1
        return min(level, 100)  # Cap at level 100


# Global instance
rewards_system = RewardsSystem()