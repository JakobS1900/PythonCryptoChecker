"""
Interactive tutorial system for guiding users through platform features.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from logger import logger
from database.unified_models import User, UserOnboarding, TutorialProgress, Achievement
from achievements.achievement_engine import achievement_engine
from notifications.notification_manager import notification_manager


class TutorialStep:
    """Individual tutorial step with guidance and validation."""
    
    def __init__(self, step_id: str, title: str, description: str, 
                 instructions: List[str], validation_action: str = None,
                 completion_reward: Dict[str, Any] = None):
        self.step_id = step_id
        self.title = title
        self.description = description
        self.instructions = instructions
        self.validation_action = validation_action
        self.completion_reward = completion_reward or {}


class TutorialSystem:
    """Interactive tutorial system for new users."""
    
    def __init__(self):
        self.tutorial_steps = self._initialize_tutorial_steps()
        self.step_timeouts = {}
        
    def _initialize_tutorial_steps(self) -> Dict[str, TutorialStep]:
        """Initialize all tutorial steps."""
        return {
            "welcome": TutorialStep(
                step_id="welcome",
                title="Welcome to CryptoChecker",
                description="Let's get you started with your virtual crypto gaming experience!",
                instructions=[
                    "Welcome to your personalized crypto gaming platform",
                    "This is a completely virtual environment - no real money involved",
                    "You'll earn virtual GEM coins and collect rare crypto items",
                    "Complete this tutorial to unlock all features and earn bonus rewards"
                ],
                completion_reward={"gem_coins": 100, "xp": 25}
            ),
            
            "profile_setup": TutorialStep(
                step_id="profile_setup",
                title="Set Up Your Profile",
                description="Customize your gaming profile and preferences",
                instructions=[
                    "Click on your profile icon in the top-right corner",
                    "Upload a profile picture or choose an avatar",
                    "Set your display name and gaming preferences",
                    "Enable notifications to stay updated on your progress"
                ],
                validation_action="profile_updated",
                completion_reward={"gem_coins": 150, "xp": 30}
            ),
            
            "wallet_intro": TutorialStep(
                step_id="wallet_intro", 
                title="Your Virtual Wallet",
                description="Learn about your virtual currency and holdings",
                instructions=[
                    "Navigate to your Wallet from the main menu",
                    "See your GEM coin balance and virtual crypto holdings",
                    "View your portfolio performance and trading history",
                    "Understanding: All currencies here are virtual for gaming only"
                ],
                validation_action="wallet_viewed",
                completion_reward={"gem_coins": 200, "xp": 40}
            ),
            
            "first_game": TutorialStep(
                step_id="first_game",
                title="Play Your First Game", 
                description="Experience the thrill of crypto roulette",
                instructions=[
                    "Go to the Gaming section and select Crypto Roulette",
                    "Place a small bet on any crypto symbol or number",
                    "Watch the wheel spin and see if luck is on your side",
                    "Win or lose, you'll learn the mechanics and earn XP"
                ],
                validation_action="game_played",
                completion_reward={"gem_coins": 300, "xp": 75}
            ),
            
            "inventory_intro": TutorialStep(
                step_id="inventory_intro",
                title="Discover Your Inventory",
                description="Explore collectible items and trading",
                instructions=[
                    "Visit your Inventory to see your collectible items",
                    "Each item has rarity levels: Common, Rare, Epic, Legendary",
                    "Items can be earned through gameplay or trading with others",
                    "Some items provide gameplay bonuses or unlock special features"
                ],
                validation_action="inventory_viewed",
                completion_reward={"gem_coins": 250, "xp": 50}
            ),
            
            "social_features": TutorialStep(
                step_id="social_features", 
                title="Connect with Others",
                description="Join the community and make friends",
                instructions=[
                    "Explore the Social section to see leaderboards",
                    "Add friends by searching usernames or browsing suggestions", 
                    "View your friends' achievements and gaming activity",
                    "Participate in community challenges and tournaments"
                ],
                validation_action="social_visited",
                completion_reward={"gem_coins": 200, "xp": 60}
            ),
            
            "achievements": TutorialStep(
                step_id="achievements",
                title="Track Your Progress", 
                description="Unlock achievements and earn rewards",
                instructions=[
                    "Check your Achievements page to see available goals",
                    "Complete achievements to earn GEM coins and rare items",
                    "Some achievements unlock special titles and badges",
                    "Progress is tracked automatically as you play and explore"
                ],
                validation_action="achievements_viewed",
                completion_reward={"gem_coins": 300, "xp": 80}
            ),
            
            "daily_systems": TutorialStep(
                step_id="daily_systems",
                title="Daily Rewards & Quests",
                description="Maximize your daily earning potential", 
                instructions=[
                    "Visit the Daily Quests section for new challenges each day",
                    "Complete quests to earn bonus rewards and XP",
                    "Claim your daily login bonus for just showing up",
                    "Maintain login streaks for increasingly better rewards"
                ],
                validation_action="daily_visited",
                completion_reward={"gem_coins": 400, "xp": 100}
            ),
            
            "tutorial_complete": TutorialStep(
                step_id="tutorial_complete",
                title="Tutorial Complete!",
                description="You're ready to start your crypto gaming journey",
                instructions=[
                    "Congratulations! You've completed the tutorial",
                    "You now have access to all platform features",
                    "Continue playing to level up and unlock more content",
                    "Remember: Have fun and game responsibly!"
                ],
                completion_reward={"gem_coins": 1000, "xp": 200, "items": ["welcome_badge"]}
            )
        }
    
    async def start_tutorial(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Start tutorial for user."""
        try:
            # Check if tutorial already in progress
            result = await session.execute(
                select(TutorialProgress).where(TutorialProgress.user_id == user_id)
            )
            existing_progress = result.scalar_one_or_none()
            
            if existing_progress and not existing_progress.completed:
                return {
                    "success": True,
                    "message": "Tutorial already in progress",
                    "current_step": existing_progress.current_step_id,
                    "progress": existing_progress.completed_steps
                }
            
            # Create new tutorial progress
            tutorial_progress = TutorialProgress(
                user_id=user_id,
                current_step_id="welcome",
                completed_steps=[],
                started_at=datetime.utcnow(),
                completed=False
            )
            
            session.add(tutorial_progress)
            await session.commit()
            
            # Send welcome notification
            await notification_manager.send_notification(
                session, user_id, "tutorial_started",
                {"step_title": "Welcome to CryptoChecker"}
            )
            
            logger.info(f"Started tutorial for user {user_id}")
            
            return {
                "success": True,
                "message": "Tutorial started successfully",
                "current_step": "welcome",
                "step_info": await self.get_step_info("welcome")
            }
            
        except Exception as e:
            logger.error(f"Failed to start tutorial: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_current_step(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get user's current tutorial step."""
        try:
            result = await session.execute(
                select(TutorialProgress).where(TutorialProgress.user_id == user_id)
            )
            progress = result.scalar_one_or_none()
            
            if not progress:
                return {"success": False, "error": "Tutorial not started"}
            
            if progress.completed:
                return {
                    "success": True,
                    "completed": True,
                    "message": "Tutorial already completed"
                }
            
            step_info = await self.get_step_info(progress.current_step_id)
            
            return {
                "success": True,
                "current_step": progress.current_step_id,
                "step_info": step_info,
                "progress": {
                    "completed_steps": progress.completed_steps,
                    "total_steps": len(self.tutorial_steps),
                    "progress_percentage": len(progress.completed_steps) / len(self.tutorial_steps) * 100
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get current tutorial step: {e}")
            return {"success": False, "error": str(e)}
    
    async def complete_step(self, session: AsyncSession, user_id: str, 
                          step_id: str, validation_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Complete a tutorial step."""
        try:
            # Get tutorial progress
            result = await session.execute(
                select(TutorialProgress).where(TutorialProgress.user_id == user_id)
            )
            progress = result.scalar_one_or_none()
            
            if not progress:
                return {"success": False, "error": "Tutorial not started"}
            
            if progress.completed:
                return {"success": False, "error": "Tutorial already completed"}
            
            if progress.current_step_id != step_id:
                return {
                    "success": False, 
                    "error": f"Expected step {progress.current_step_id}, got {step_id}"
                }
            
            # Validate step completion if required
            step = self.tutorial_steps.get(step_id)
            if not step:
                return {"success": False, "error": "Invalid tutorial step"}
            
            if step.validation_action:
                is_valid = await self._validate_step_completion(
                    session, user_id, step.validation_action, validation_data
                )
                if not is_valid:
                    return {
                        "success": False,
                        "error": f"Step validation failed for {step.validation_action}"
                    }
            
            # Mark step as completed
            completed_steps = progress.completed_steps.copy()
            if step_id not in completed_steps:
                completed_steps.append(step_id)
            
            # Determine next step
            step_order = list(self.tutorial_steps.keys())
            current_index = step_order.index(step_id)
            next_step = step_order[current_index + 1] if current_index + 1 < len(step_order) else None
            
            # Update progress
            progress.completed_steps = completed_steps
            progress.current_step_id = next_step
            progress.last_step_completed_at = datetime.utcnow()
            
            if not next_step:
                progress.completed = True
                progress.completed_at = datetime.utcnow()
            
            await session.commit()
            
            # Award completion rewards
            reward_result = await self._award_step_rewards(session, user_id, step)
            
            # Send completion notification
            await notification_manager.send_notification(
                session, user_id, "tutorial_step_completed",
                {
                    "step_title": step.title,
                    "rewards": step.completion_reward,
                    "next_step": self.tutorial_steps[next_step].title if next_step else "Complete!"
                }
            )
            
            logger.info(f"User {user_id} completed tutorial step: {step_id}")
            
            result = {
                "success": True,
                "step_completed": step_id,
                "rewards": reward_result,
                "tutorial_completed": not next_step
            }
            
            if next_step:
                result["next_step"] = next_step
                result["next_step_info"] = await self.get_step_info(next_step)
            
            # Check for tutorial completion achievement
            if not next_step:
                await achievement_engine.check_achievement(
                    session, user_id, "tutorial_master", {"completed": True}
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to complete tutorial step: {e}")
            return {"success": False, "error": str(e)}
    
    async def skip_step(self, session: AsyncSession, user_id: str, step_id: str) -> Dict[str, Any]:
        """Skip a tutorial step (with reduced rewards)."""
        try:
            # Get tutorial progress
            result = await session.execute(
                select(TutorialProgress).where(TutorialProgress.user_id == user_id)
            )
            progress = result.scalar_one_or_none()
            
            if not progress or progress.current_step_id != step_id:
                return {"success": False, "error": "Invalid step to skip"}
            
            # Skip with 50% rewards
            step = self.tutorial_steps.get(step_id)
            reduced_rewards = {
                key: int(value * 0.5) for key, value in step.completion_reward.items()
                if isinstance(value, (int, float))
            }
            
            # Create modified step for reward calculation
            skipped_step = TutorialStep(
                step_id=step.step_id,
                title=step.title,
                description=step.description,
                instructions=step.instructions,
                completion_reward=reduced_rewards
            )
            
            # Mark as completed with skip flag
            completed_steps = progress.completed_steps.copy()
            completed_steps.append(f"{step_id}_skipped")
            
            # Determine next step
            step_order = list(self.tutorial_steps.keys())
            current_index = step_order.index(step_id)
            next_step = step_order[current_index + 1] if current_index + 1 < len(step_order) else None
            
            progress.completed_steps = completed_steps
            progress.current_step_id = next_step
            progress.last_step_completed_at = datetime.utcnow()
            
            if not next_step:
                progress.completed = True
                progress.completed_at = datetime.utcnow()
            
            await session.commit()
            
            # Award reduced rewards
            reward_result = await self._award_step_rewards(session, user_id, skipped_step)
            
            logger.info(f"User {user_id} skipped tutorial step: {step_id}")
            
            return {
                "success": True,
                "step_skipped": step_id,
                "rewards": reward_result,
                "next_step": next_step,
                "next_step_info": await self.get_step_info(next_step) if next_step else None
            }
            
        except Exception as e:
            logger.error(f"Failed to skip tutorial step: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_step_info(self, step_id: str) -> Dict[str, Any]:
        """Get detailed information about a tutorial step."""
        step = self.tutorial_steps.get(step_id)
        if not step:
            return {"error": "Invalid step ID"}
        
        return {
            "step_id": step.step_id,
            "title": step.title,
            "description": step.description,
            "instructions": step.instructions,
            "validation_required": step.validation_action is not None,
            "rewards": step.completion_reward
        }
    
    async def get_tutorial_progress(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get comprehensive tutorial progress information."""
        try:
            result = await session.execute(
                select(TutorialProgress).where(TutorialProgress.user_id == user_id)
            )
            progress = result.scalar_one_or_none()
            
            if not progress:
                return {
                    "tutorial_started": False,
                    "available": True,
                    "message": "Tutorial available to start"
                }
            
            completed_count = len([s for s in progress.completed_steps if not s.endswith("_skipped")])
            skipped_count = len([s for s in progress.completed_steps if s.endswith("_skipped")])
            total_steps = len(self.tutorial_steps)
            
            return {
                "tutorial_started": True,
                "completed": progress.completed,
                "current_step": progress.current_step_id,
                "progress": {
                    "completed_steps": completed_count,
                    "skipped_steps": skipped_count, 
                    "total_steps": total_steps,
                    "progress_percentage": len(progress.completed_steps) / total_steps * 100
                },
                "timestamps": {
                    "started_at": progress.started_at.isoformat() if progress.started_at else None,
                    "last_step_at": progress.last_step_completed_at.isoformat() if progress.last_step_completed_at else None,
                    "completed_at": progress.completed_at.isoformat() if progress.completed_at else None
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get tutorial progress: {e}")
            return {"error": str(e)}
    
    async def reset_tutorial(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Reset user's tutorial progress."""
        try:
            result = await session.execute(
                select(TutorialProgress).where(TutorialProgress.user_id == user_id)
            )
            progress = result.scalar_one_or_none()
            
            if progress:
                await session.delete(progress)
                await session.commit()
            
            logger.info(f"Reset tutorial for user {user_id}")
            
            return {
                "success": True,
                "message": "Tutorial progress reset successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to reset tutorial: {e}")
            return {"success": False, "error": str(e)}
    
    async def _validate_step_completion(self, session: AsyncSession, user_id: str, 
                                      validation_action: str, validation_data: Dict[str, Any] = None) -> bool:
        """Validate that user has completed required action."""
        try:
            validation_data = validation_data or {}
            
            if validation_action == "profile_updated":
                # Check if user has updated their profile recently
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                return user and user.display_name and user.profile_picture
                
            elif validation_action == "wallet_viewed":
                # Check if user has viewed wallet (could be tracked via activity log)
                return validation_data.get("wallet_viewed", False)
                
            elif validation_action == "game_played":
                # Check if user has played at least one game
                return validation_data.get("game_played", False)
                
            elif validation_action == "inventory_viewed":
                return validation_data.get("inventory_viewed", False)
                
            elif validation_action == "social_visited":
                return validation_data.get("social_visited", False)
                
            elif validation_action == "achievements_viewed":
                return validation_data.get("achievements_viewed", False)
                
            elif validation_action == "daily_visited":
                return validation_data.get("daily_visited", False)
            
            return True  # Default to true for steps without specific validation
            
        except Exception as e:
            logger.error(f"Validation error for {validation_action}: {e}")
            return False
    
    async def _award_step_rewards(self, session: AsyncSession, user_id: str, step: TutorialStep) -> Dict[str, Any]:
        """Award rewards for completing a tutorial step."""
        try:
            rewards_awarded = {}
            
            # Award GEM coins
            if "gem_coins" in step.completion_reward:
                gem_amount = step.completion_reward["gem_coins"]
                
                # Update user's virtual wallet
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if user and hasattr(user, 'virtual_wallet') and user.virtual_wallet:
                    user.virtual_wallet.gem_coins += gem_amount
                    rewards_awarded["gem_coins"] = gem_amount
            
            # Award XP
            if "xp" in step.completion_reward:
                xp_amount = step.completion_reward["xp"]
                
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    user.total_xp += xp_amount
                    # Recalculate level
                    new_level = self._calculate_level(user.total_xp)
                    if new_level > user.level:
                        user.level = new_level
                        rewards_awarded["level_up"] = new_level
                    
                    rewards_awarded["xp"] = xp_amount
            
            # Award items
            if "items" in step.completion_reward:
                # This would integrate with inventory system
                rewards_awarded["items"] = step.completion_reward["items"]
            
            await session.commit()
            
            return {
                "success": True,
                "rewards": rewards_awarded
            }
            
        except Exception as e:
            logger.error(f"Failed to award tutorial rewards: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_level(self, total_xp: int) -> int:
        """Calculate user level based on total XP."""
        # Simple level calculation: level = floor(sqrt(xp / 100))
        import math
        return max(1, int(math.sqrt(total_xp / 100)))


# Global instance
tutorial_system = TutorialSystem()