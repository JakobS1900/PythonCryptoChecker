"""
Onboarding manager for new user experience and tutorial flow.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from database.unified_models import User, UserOnboarding, OnboardingStep, VirtualWallet
from gamification.virtual_economy import VirtualEconomyEngine
from achievements.achievement_engine import achievement_engine
from notifications.notification_manager import notification_manager
from logger import logger


class OnboardingManager:
    """Manages new user onboarding experience."""
    
    def __init__(self):
        self.virtual_economy = VirtualEconomyEngine()
        self.onboarding_steps = self._initialize_onboarding_steps()
    
    def _initialize_onboarding_steps(self) -> List[Dict[str, Any]]:
        """Initialize the onboarding step sequence."""
        return [
            {
                "step_id": "welcome",
                "name": "Welcome to CryptoGaming",
                "description": "Learn about the platform and what makes it special",
                "type": "introduction",
                "required": True,
                "estimated_time": 2,
                "rewards": {"gem_coins": 500, "xp": 100},
                "content": {
                    "title": "Welcome to the Ultimate Crypto Gaming Experience!",
                    "sections": [
                        {
                            "title": "What is CryptoGaming?",
                            "content": "A virtual gambling and gaming platform where you can play crypto-themed games, collect items, and compete with friends - all without any real money involved!"
                        },
                        {
                            "title": "Key Features",
                            "content": "🎲 Crypto Roulette Games\n🎒 Collectible Item System\n👥 Social Features & Friends\n🏆 Achievements & Progression\n💎 Virtual Currency (GEM Coins)"
                        },
                        {
                            "title": "Getting Started",
                            "content": "You'll start with 1,000 GEM coins and a starter pack of items. Everything is completely virtual and designed for entertainment!"
                        }
                    ]
                }
            },
            {
                "step_id": "profile_setup",
                "name": "Set Up Your Profile",
                "description": "Customize your gaming profile and preferences",
                "type": "profile",
                "required": True,
                "estimated_time": 3,
                "rewards": {"gem_coins": 200, "xp": 50},
                "actions": [
                    {"type": "set_display_name", "label": "Choose a display name"},
                    {"type": "set_avatar", "label": "Select an avatar (optional)"},
                    {"type": "privacy_settings", "label": "Set privacy preferences"}
                ]
            },
            {
                "step_id": "wallet_intro",
                "name": "Your Virtual Wallet",
                "description": "Learn about GEM coins and virtual currency",
                "type": "tutorial",
                "required": True,
                "estimated_time": 2,
                "rewards": {"gem_coins": 300, "xp": 75},
                "content": {
                    "title": "Understanding Your Virtual Wallet",
                    "sections": [
                        {
                            "title": "GEM Coins",
                            "content": "Your primary currency for playing games and purchasing items. Earned through gameplay, quests, and daily bonuses."
                        },
                        {
                            "title": "Virtual Crypto Holdings",
                            "content": "Track virtual cryptocurrency values that sync with real market prices, but remember - these are just for fun!"
                        },
                        {
                            "title": "Earning & Spending",
                            "content": "Earn coins by playing games, completing quests, and achieving milestones. Spend them on games, item packs, and trading."
                        }
                    ]
                }
            },
            {
                "step_id": "first_game",
                "name": "Play Your First Game",
                "description": "Experience crypto roulette with a guided tutorial",
                "type": "gameplay",
                "required": True,
                "estimated_time": 5,
                "rewards": {"gem_coins": 500, "xp": 150},
                "tutorial_data": {
                    "game_type": "crypto_roulette",
                    "guided": True,
                    "free_spins": 3,
                    "tutorial_bets": [
                        {"type": "SINGLE_CRYPTO", "value": "bitcoin", "amount": 50},
                        {"type": "CRYPTO_COLOR", "value": "red", "amount": 100},
                        {"type": "EVEN_ODD", "value": "even", "amount": 75}
                    ]
                }
            },
            {
                "step_id": "inventory_intro",
                "name": "Your Item Collection",
                "description": "Learn about collectible items and inventory management",
                "type": "tutorial", 
                "required": True,
                "estimated_time": 3,
                "rewards": {"gem_coins": 250, "item_pack": "starter"},
                "content": {
                    "title": "Building Your Collection",
                    "sections": [
                        {
                            "title": "Collectible Items",
                            "content": "Collect crypto-themed trading cards, accessories, and special items. Each has different rarities and values."
                        },
                        {
                            "title": "Item Packs",
                            "content": "Open packs to discover new items! Higher tier packs have better chances for rare items."
                        },
                        {
                            "title": "Trading System",
                            "content": "Trade items with other players to complete your collection or get items you need."
                        }
                    ]
                },
                "actions": [
                    {"type": "open_starter_pack", "label": "Open your starter pack"},
                    {"type": "view_inventory", "label": "Explore your inventory"}
                ]
            },
            {
                "step_id": "social_intro",
                "name": "Connect with Others",
                "description": "Learn about friends, leaderboards, and social features",
                "type": "social",
                "required": False,
                "estimated_time": 3,
                "rewards": {"gem_coins": 400, "xp": 100},
                "content": {
                    "title": "Join the Community",
                    "sections": [
                        {
                            "title": "Friends System",
                            "content": "Add friends to see their progress, send gifts, and compete together. Playing with friends is more fun!"
                        },
                        {
                            "title": "Leaderboards",
                            "content": "Compete on various leaderboards - level, experience, games won, and more. See how you rank globally!"
                        },
                        {
                            "title": "Social Activities",
                            "content": "View friend activity, share achievements, and participate in community events."
                        }
                    ]
                }
            },
            {
                "step_id": "achievements_intro",
                "name": "Achievements & Progress",
                "description": "Understand the progression system and achievement rewards",
                "type": "progression",
                "required": False,
                "estimated_time": 2,
                "rewards": {"gem_coins": 300, "xp": 100},
                "content": {
                    "title": "Track Your Progress",
                    "sections": [
                        {
                            "title": "Achievement System",
                            "content": "Unlock achievements by completing various challenges. Each achievement rewards coins, XP, and sometimes special items."
                        },
                        {
                            "title": "Level Progression",
                            "content": "Gain XP to level up and unlock new features. Higher levels bring better rewards and recognition."
                        },
                        {
                            "title": "Daily Quests",
                            "content": "Complete daily quests for consistent rewards. New quests appear every day with various challenges."
                        }
                    ]
                }
            },
            {
                "step_id": "daily_systems",
                "name": "Daily Bonuses & Quests",
                "description": "Learn about daily login bonuses and quest system",
                "type": "daily",
                "required": False,
                "estimated_time": 2,
                "rewards": {"gem_coins": 200, "xp": 75},
                "content": {
                    "title": "Daily Rewards & Activities",
                    "sections": [
                        {
                            "title": "Daily Login Bonus",
                            "content": "Log in daily to receive bonus coins and XP. Consecutive login streaks provide increasing rewards!"
                        },
                        {
                            "title": "Daily Quests",
                            "content": "Fresh quests every day with varied objectives. Complete them for substantial rewards and progress."
                        },
                        {
                            "title": "Building Habits",
                            "content": "Regular play and engagement unlocks the best rewards and keeps you progressing steadily."
                        }
                    ]
                }
            },
            {
                "step_id": "completion",
                "name": "Onboarding Complete!",
                "description": "Congratulations! You're ready to start your gaming journey",
                "type": "completion",
                "required": True,
                "estimated_time": 1,
                "rewards": {"gem_coins": 1000, "xp": 200, "item_pack": "premium", "achievement": "onboarding_complete"},
                "content": {
                    "title": "Welcome to the Community!",
                    "sections": [
                        {
                            "title": "You're All Set!",
                            "content": "Congratulations on completing the onboarding process! You now have all the knowledge needed to enjoy CryptoGaming to the fullest."
                        },
                        {
                            "title": "What's Next?",
                            "content": "🎲 Play roulette games and try different strategies\n🎒 Collect rare items and build your collection\n👥 Add friends and join the community\n🏆 Work towards achievements and climb leaderboards"
                        },
                        {
                            "title": "Final Rewards",
                            "content": "As a completion bonus, you've received extra coins, a premium item pack, and a special achievement!"
                        }
                    ]
                }
            }
        ]
    
    async def start_onboarding(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Start onboarding process for a new user."""
        try:
            # Check if user already has onboarding
            existing_result = await session.execute(
                select(UserOnboarding).where(UserOnboarding.user_id == user_id)
            )
            existing_onboarding = existing_result.scalar_one_or_none()
            
            if existing_onboarding:
                return {"error": "User already has onboarding in progress"}
            
            # Create onboarding record
            onboarding = UserOnboarding(
                user_id=user_id,
                current_step=0,
                completed_steps=[],
                started_at=datetime.utcnow(),
                completed=False
            )
            session.add(onboarding)
            
            # Give initial welcome bonus
            await self._award_welcome_bonus(session, user_id)
            
            # Send welcome notification
            await notification_manager.send_notification(
                session, user_id, "welcome"
            )
            
            await session.commit()
            
            # Return first step
            first_step = self.onboarding_steps[0]
            return {
                "onboarding_started": True,
                "total_steps": len(self.onboarding_steps),
                "current_step": first_step,
                "progress": 0
            }
            
        except Exception as e:
            logger.error(f"Failed to start onboarding: {e}")
            return {"error": str(e)}
    
    async def get_current_step(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get user's current onboarding step."""
        try:
            result = await session.execute(
                select(UserOnboarding).where(UserOnboarding.user_id == user_id)
            )
            onboarding = result.scalar_one_or_none()
            
            if not onboarding:
                return {"error": "Onboarding not started"}
            
            if onboarding.completed:
                return {
                    "completed": True,
                    "completed_at": onboarding.completed_at.isoformat(),
                    "progress": 100
                }
            
            current_step_data = self.onboarding_steps[onboarding.current_step]
            progress = (len(onboarding.completed_steps) / len(self.onboarding_steps)) * 100
            
            return {
                "current_step": current_step_data,
                "step_number": onboarding.current_step + 1,
                "total_steps": len(self.onboarding_steps),
                "completed_steps": onboarding.completed_steps,
                "progress": progress,
                "started_at": onboarding.started_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get current step: {e}")
            return {"error": str(e)}
    
    async def complete_step(self, session: AsyncSession, user_id: str, step_id: str, 
                           step_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Complete an onboarding step."""
        try:
            result = await session.execute(
                select(UserOnboarding).where(UserOnboarding.user_id == user_id)
            )
            onboarding = result.scalar_one_or_none()
            
            if not onboarding:
                return {"error": "Onboarding not started"}
            
            if onboarding.completed:
                return {"error": "Onboarding already completed"}
            
            # Find step by ID
            step_index = None
            step_config = None
            for i, step in enumerate(self.onboarding_steps):
                if step["step_id"] == step_id:
                    step_index = i
                    step_config = step
                    break
            
            if step_index is None:
                return {"error": "Invalid step ID"}
            
            # Check if this is the current step
            if step_index != onboarding.current_step:
                return {"error": "Not the current step"}
            
            # Process step completion
            completion_result = await self._process_step_completion(
                session, user_id, step_config, step_data or {}
            )
            
            # Update onboarding progress
            onboarding.completed_steps.append(step_id)
            onboarding.current_step += 1
            
            # Check if onboarding is complete
            if onboarding.current_step >= len(self.onboarding_steps):
                onboarding.completed = True
                onboarding.completed_at = datetime.utcnow()
                
                # Trigger onboarding completion achievement
                await achievement_engine.check_user_achievements(
                    session, user_id, "onboarding_complete", {}
                )
                
                await session.commit()
                
                return {
                    "step_completed": True,
                    "onboarding_completed": True,
                    "rewards": completion_result.get("rewards", {}),
                    "progress": 100
                }
            
            # Get next step
            next_step = self.onboarding_steps[onboarding.current_step]
            progress = (len(onboarding.completed_steps) / len(self.onboarding_steps)) * 100
            
            await session.commit()
            
            return {
                "step_completed": True,
                "onboarding_completed": False,
                "rewards": completion_result.get("rewards", {}),
                "next_step": next_step,
                "progress": progress
            }
            
        except Exception as e:
            logger.error(f"Failed to complete step: {e}")
            return {"error": str(e)}
    
    async def skip_optional_step(self, session: AsyncSession, user_id: str, step_id: str) -> Dict[str, Any]:
        """Skip an optional onboarding step."""
        try:
            # Find step and verify it's optional
            step_config = None
            for step in self.onboarding_steps:
                if step["step_id"] == step_id:
                    step_config = step
                    break
            
            if not step_config:
                return {"error": "Invalid step ID"}
            
            if step_config.get("required", True):
                return {"error": "Cannot skip required step"}
            
            # Complete the step without rewards
            return await self.complete_step(session, user_id, step_id, {"skipped": True})
            
        except Exception as e:
            logger.error(f"Failed to skip step: {e}")
            return {"error": str(e)}
    
    async def reset_onboarding(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Reset user's onboarding progress (admin function)."""
        try:
            result = await session.execute(
                select(UserOnboarding).where(UserOnboarding.user_id == user_id)
            )
            onboarding = result.scalar_one_or_none()
            
            if onboarding:
                onboarding.current_step = 0
                onboarding.completed_steps = []
                onboarding.completed = False
                onboarding.completed_at = None
                onboarding.started_at = datetime.utcnow()
            
            await session.commit()
            
            return {"onboarding_reset": True}
            
        except Exception as e:
            logger.error(f"Failed to reset onboarding: {e}")
            return {"error": str(e)}
    
    async def get_onboarding_stats(self, session: AsyncSession) -> Dict[str, Any]:
        """Get onboarding completion statistics."""
        try:
            from sqlalchemy import func
            
            # Total users with onboarding
            total_result = await session.execute(
                select(func.count(UserOnboarding.user_id))
            )
            total_onboarding = total_result.scalar() or 0
            
            # Completed onboarding
            completed_result = await session.execute(
                select(func.count(UserOnboarding.user_id)).where(
                    UserOnboarding.completed == True
                )
            )
            completed_onboarding = completed_result.scalar() or 0
            
            # Average completion rate per step
            step_completion = {}
            for step in self.onboarding_steps:
                step_result = await session.execute(
                    select(func.count(UserOnboarding.user_id)).where(
                        UserOnboarding.completed_steps.contains([step["step_id"]])
                    )
                )
                step_count = step_result.scalar() or 0
                step_completion[step["step_id"]] = {
                    "completed": step_count,
                    "rate": (step_count / total_onboarding * 100) if total_onboarding > 0 else 0
                }
            
            completion_rate = (completed_onboarding / total_onboarding * 100) if total_onboarding > 0 else 0
            
            return {
                "total_users": total_onboarding,
                "completed_users": completed_onboarding,
                "completion_rate": round(completion_rate, 2),
                "step_completion": step_completion,
                "total_steps": len(self.onboarding_steps)
            }
            
        except Exception as e:
            logger.error(f"Failed to get onboarding stats: {e}")
            return {"error": str(e)}
    
    async def _award_welcome_bonus(self, session: AsyncSession, user_id: str):
        """Award initial welcome bonus to new user."""
        try:
            # Get or create wallet
            wallet_result = await session.execute(
                select(VirtualWallet).where(VirtualWallet.user_id == user_id)
            )
            wallet = wallet_result.scalar_one_or_none()
            
            if not wallet:
                wallet = VirtualWallet(
                    user_id=user_id,
                    gem_coins=1000,  # Welcome bonus
                    total_virtual_crypto_value=0.0,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(wallet)
            else:
                wallet.gem_coins += 1000  # Add welcome bonus
                wallet.updated_at = datetime.utcnow()
            
            # Award welcome XP
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                user.total_experience += 200  # Welcome XP
                # Check for level up
                new_level = self._calculate_level_from_xp(user.total_experience)
                if new_level > user.current_level:
                    user.current_level = new_level
            
        except Exception as e:
            logger.error(f"Failed to award welcome bonus: {e}")
    
    async def _process_step_completion(self, session: AsyncSession, user_id: str, 
                                     step_config: Dict[str, Any], step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the completion of a specific step."""
        try:
            rewards = step_config.get("rewards", {})
            awarded_rewards = {}
            
            # Skip rewards if step was skipped
            if step_data.get("skipped"):
                return {"rewards": {}}
            
            # Award GEM coins
            if "gem_coins" in rewards:
                await self._award_currency(session, user_id, "gem_coins", rewards["gem_coins"])
                awarded_rewards["gem_coins"] = rewards["gem_coins"]
            
            # Award XP
            if "xp" in rewards:
                await self._award_currency(session, user_id, "xp", rewards["xp"])
                awarded_rewards["xp"] = rewards["xp"]
            
            # Award item packs
            if "item_pack" in rewards:
                # Would integrate with inventory system
                awarded_rewards["item_pack"] = rewards["item_pack"]
            
            # Handle special step types
            step_type = step_config.get("type")
            
            if step_type == "gameplay" and step_config["step_id"] == "first_game":
                # Create a tutorial game session
                await self._create_tutorial_game(session, user_id, step_config.get("tutorial_data", {}))
            
            elif step_type == "profile" and step_config["step_id"] == "profile_setup":
                # Process profile setup data
                await self._process_profile_setup(session, user_id, step_data)
            
            return {"rewards": awarded_rewards}
            
        except Exception as e:
            logger.error(f"Failed to process step completion: {e}")
            return {"rewards": {}}
    
    async def _award_currency(self, session: AsyncSession, user_id: str, currency_type: str, amount: int):
        """Award currency to user."""
        try:
            if currency_type == "gem_coins":
                wallet_result = await session.execute(
                    select(VirtualWallet).where(VirtualWallet.user_id == user_id)
                )
                wallet = wallet_result.scalar_one_or_none()
                
                if wallet:
                    wallet.gem_coins += amount
                    wallet.updated_at = datetime.utcnow()
                    
            elif currency_type == "xp":
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if user:
                    user.total_experience += amount
                    new_level = self._calculate_level_from_xp(user.total_experience)
                    if new_level > user.current_level:
                        user.current_level = new_level
                        
        except Exception as e:
            logger.error(f"Failed to award currency: {e}")
    
    async def _create_tutorial_game(self, session: AsyncSession, user_id: str, tutorial_data: Dict[str, Any]):
        """Create a tutorial game session."""
        try:
            # Would integrate with gaming system to create a guided tutorial game
            logger.info(f"Created tutorial game for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to create tutorial game: {e}")
    
    async def _process_profile_setup(self, session: AsyncSession, user_id: str, profile_data: Dict[str, Any]):
        """Process profile setup step data."""
        try:
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user and profile_data:
                if "display_name" in profile_data:
                    user.display_name = profile_data["display_name"]
                if "avatar_url" in profile_data:
                    user.avatar_url = profile_data["avatar_url"]
                if "profile_public" in profile_data:
                    user.profile_public = profile_data["profile_public"]
                
                user.updated_at = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"Failed to process profile setup: {e}")
    
    def _calculate_level_from_xp(self, total_xp: int) -> int:
        """Calculate level from total XP."""
        if total_xp < 1000:
            return 1
        
        import math
        level = int(math.sqrt(total_xp / 1000)) + 1
        return min(level, 100)


# Global instance
onboarding_manager = OnboardingManager()