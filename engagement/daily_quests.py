"""
Daily quest system for user engagement and retention.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func

from database.unified_models import DailyQuest, UserQuest, QuestType
from logger import logger


class DailyQuestSystem:
    """Manages daily quests for user engagement."""
    
    def __init__(self):
        self.quest_templates = self._initialize_quest_templates()
    
    def _initialize_quest_templates(self) -> List[Dict[str, Any]]:
        """Initialize available quest templates."""
        return [
            {
                "id": "play_games",
                "name": "Gaming Session",
                "description": "Play {target} games of crypto roulette",
                "type": QuestType.GAMING,
                "target_action": "game_played",
                "target_values": [3, 5, 10],
                "base_rewards": {"gem_coins": 200, "xp": 50},
                "difficulty": "easy"
            },
            {
                "id": "win_games", 
                "name": "Victory Streak",
                "description": "Win {target} games in a row",
                "type": QuestType.GAMING,
                "target_action": "game_won_streak",
                "target_values": [2, 3, 5],
                "base_rewards": {"gem_coins": 500, "xp": 100},
                "difficulty": "medium"
            },
            {
                "id": "earn_coins",
                "name": "Coin Collector",
                "description": "Earn {target} GEM coins from games",
                "type": QuestType.CURRENCY,
                "target_action": "coins_earned",
                "target_values": [1000, 2500, 5000],
                "base_rewards": {"gem_coins": 300, "xp": 75},
                "difficulty": "medium"
            },
            {
                "id": "make_friends",
                "name": "Social Butterfly",
                "description": "Add {target} new friends",
                "type": QuestType.SOCIAL,
                "target_action": "friend_added",
                "target_values": [1, 2, 3],
                "base_rewards": {"gem_coins": 400, "xp": 80},
                "difficulty": "easy"
            },
            {
                "id": "trade_items",
                "name": "Master Trader",
                "description": "Complete {target} successful trades",
                "type": QuestType.TRADING,
                "target_action": "trade_completed",
                "target_values": [1, 3, 5],
                "base_rewards": {"gem_coins": 350, "xp": 90},
                "difficulty": "medium"
            },
            {
                "id": "collect_items",
                "name": "Collector's Quest",
                "description": "Obtain {target} new collectible items",
                "type": QuestType.COLLECTION,
                "target_action": "item_obtained",
                "target_values": [2, 5, 8],
                "base_rewards": {"gem_coins": 250, "xp": 60},
                "difficulty": "easy"
            },
            {
                "id": "login_streak",
                "name": "Dedication Reward",
                "description": "Maintain login streak for {target} consecutive days",
                "type": QuestType.ENGAGEMENT,
                "target_action": "daily_login",
                "target_values": [3, 7, 14],
                "base_rewards": {"gem_coins": 600, "xp": 120},
                "difficulty": "hard"
            },
            {
                "id": "spend_coins",
                "name": "Big Spender",
                "description": "Spend {target} GEM coins on games or items",
                "type": QuestType.CURRENCY,
                "target_action": "coins_spent",
                "target_values": [500, 1000, 2000],
                "base_rewards": {"gem_coins": 200, "xp": 40},
                "difficulty": "easy"
            },
            {
                "id": "level_up",
                "name": "Experience Seeker",
                "description": "Gain {target} experience points",
                "type": QuestType.PROGRESSION,
                "target_action": "xp_gained",
                "target_values": [500, 1000, 2000],
                "base_rewards": {"gem_coins": 400, "xp": 100},
                "difficulty": "medium"
            },
            {
                "id": "daily_bonus",
                "name": "Daily Dedication",
                "description": "Claim your daily login bonus",
                "type": QuestType.ENGAGEMENT,
                "target_action": "daily_bonus_claimed",
                "target_values": [1],
                "base_rewards": {"gem_coins": 150, "xp": 25},
                "difficulty": "easy"
            }
        ]
    
    async def generate_daily_quests(self, session: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
        """Generate new daily quests for a user."""
        try:
            # Clear existing daily quests
            await session.execute(
                delete(UserQuest).where(
                    and_(
                        UserQuest.user_id == user_id,
                        UserQuest.quest_date == datetime.utcnow().date()
                    )
                )
            )
            
            # Generate 3-5 random quests with balanced difficulty
            num_quests = random.randint(3, 5)
            selected_templates = self._select_balanced_quests(num_quests)
            
            generated_quests = []
            
            for template in selected_templates:
                quest = await self._create_quest_from_template(session, user_id, template)
                if quest:
                    generated_quests.append(quest)
            
            await session.commit()
            return generated_quests
            
        except Exception as e:
            logger.error(f"Failed to generate daily quests: {e}")
            return []
    
    async def get_user_daily_quests(self, session: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
        """Get user's current daily quests."""
        try:
            today = datetime.utcnow().date()
            
            result = await session.execute(
                select(UserQuest).where(
                    and_(
                        UserQuest.user_id == user_id,
                        UserQuest.quest_date == today
                    )
                )
            )
            user_quests = result.scalars().all()
            
            # If no quests exist for today, generate them
            if not user_quests:
                return await self.generate_daily_quests(session, user_id)
            
            # Convert to dict format
            quests_data = []
            for quest in user_quests:
                quests_data.append({
                    "id": quest.id,
                    "name": quest.name,
                    "description": quest.description,
                    "type": quest.quest_type,
                    "target_value": quest.target_value,
                    "current_progress": quest.current_progress,
                    "completed": quest.completed,
                    "rewards": quest.rewards,
                    "difficulty": quest.difficulty,
                    "progress_percentage": min(100, (quest.current_progress / quest.target_value) * 100) if quest.target_value > 0 else 0
                })
            
            return quests_data
            
        except Exception as e:
            logger.error(f"Failed to get user daily quests: {e}")
            return []
    
    async def update_quest_progress(self, session: AsyncSession, user_id: str, action: str, metadata: Dict = None) -> List[Dict[str, Any]]:
        """Update progress on user's quests based on action."""
        try:
            today = datetime.utcnow().date()
            
            # Get active quests that match this action
            result = await session.execute(
                select(UserQuest).where(
                    and_(
                        UserQuest.user_id == user_id,
                        UserQuest.quest_date == today,
                        UserQuest.target_action == action,
                        UserQuest.completed == False
                    )
                )
            )
            matching_quests = result.scalars().all()
            
            updates = []
            
            for quest in matching_quests:
                # Calculate progress increase
                progress_increase = self._calculate_progress_increase(action, metadata or {})
                old_progress = quest.current_progress
                quest.current_progress = min(quest.target_value, quest.current_progress + progress_increase)
                
                # Check if quest is completed
                if quest.current_progress >= quest.target_value and not quest.completed:
                    quest.completed = True
                    quest.completed_at = datetime.utcnow()
                
                updates.append({
                    "quest_id": quest.id,
                    "name": quest.name,
                    "old_progress": old_progress,
                    "new_progress": quest.current_progress,
                    "target": quest.target_value,
                    "completed": quest.completed,
                    "progress_increase": progress_increase
                })
            
            await session.commit()
            return updates
            
        except Exception as e:
            logger.error(f"Failed to update quest progress: {e}")
            return []
    
    async def check_completed_quests(self, session: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
        """Check for recently completed quests that haven't been claimed."""
        try:
            today = datetime.utcnow().date()
            
            result = await session.execute(
                select(UserQuest).where(
                    and_(
                        UserQuest.user_id == user_id,
                        UserQuest.quest_date == today,
                        UserQuest.completed == True,
                        UserQuest.rewards_claimed == False
                    )
                )
            )
            completed_quests = result.scalars().all()
            
            quests_data = []
            for quest in completed_quests:
                quests_data.append({
                    "id": quest.id,
                    "name": quest.name,
                    "rewards": quest.rewards,
                    "completed_at": quest.completed_at
                })
            
            return quests_data
            
        except Exception as e:
            logger.error(f"Failed to check completed quests: {e}")
            return []
    
    async def claim_quest_rewards(self, session: AsyncSession, user_id: str, quest_id: str) -> Dict[str, Any]:
        """Claim rewards for a completed quest."""
        try:
            result = await session.execute(
                select(UserQuest).where(
                    and_(
                        UserQuest.id == quest_id,
                        UserQuest.user_id == user_id,
                        UserQuest.completed == True,
                        UserQuest.rewards_claimed == False
                    )
                )
            )
            quest = result.scalar_one_or_none()
            
            if not quest:
                return {"error": "Quest not found or already claimed"}
            
            # Mark rewards as claimed
            quest.rewards_claimed = True
            quest.rewards_claimed_at = datetime.utcnow()
            
            await session.commit()
            
            return {
                "quest_name": quest.name,
                "rewards": quest.rewards,
                "claimed_at": quest.rewards_claimed_at
            }
            
        except Exception as e:
            logger.error(f"Failed to claim quest rewards: {e}")
            return {"error": str(e)}
    
    async def reset_daily_quests(self, session: AsyncSession) -> Dict[str, Any]:
        """Reset daily quests system (called daily)."""
        try:
            yesterday = datetime.utcnow().date() - timedelta(days=1)
            
            # Archive completed quests from yesterday
            result = await session.execute(
                select(func.count(UserQuest.id)).where(
                    UserQuest.quest_date == yesterday
                )
            )
            archived_count = result.scalar() or 0
            
            # Delete old uncompleted quests (older than 7 days)
            week_ago = datetime.utcnow().date() - timedelta(days=7)
            await session.execute(
                delete(UserQuest).where(UserQuest.quest_date < week_ago)
            )
            
            await session.commit()
            
            return {
                "archived_count": archived_count,
                "cleanup_completed": True
            }
            
        except Exception as e:
            logger.error(f"Failed to reset daily quests: {e}")
            return {"error": str(e)}
    
    def _select_balanced_quests(self, num_quests: int) -> List[Dict[str, Any]]:
        """Select a balanced mix of quests by difficulty and type."""
        available_templates = self.quest_templates.copy()
        selected = []
        
        # Ensure at least one easy quest
        easy_quests = [t for t in available_templates if t["difficulty"] == "easy"]
        if easy_quests:
            selected.append(random.choice(easy_quests))
            available_templates = [t for t in available_templates if t not in selected]
        
        # Fill remaining slots randomly
        while len(selected) < num_quests and available_templates:
            quest = random.choice(available_templates)
            selected.append(quest)
            available_templates.remove(quest)
        
        return selected
    
    async def _create_quest_from_template(self, session: AsyncSession, user_id: str, template: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a quest instance from a template."""
        try:
            # Select random target value based on difficulty
            target_value = random.choice(template["target_values"])
            
            # Scale rewards based on difficulty
            rewards = template["base_rewards"].copy()
            difficulty_multipliers = {"easy": 1.0, "medium": 1.5, "hard": 2.0}
            multiplier = difficulty_multipliers.get(template["difficulty"], 1.0)
            
            for reward_type, amount in rewards.items():
                rewards[reward_type] = int(amount * multiplier)
            
            # Create quest instance
            quest = UserQuest(
                user_id=user_id,
                name=template["name"],
                description=template["description"].format(target=target_value),
                quest_type=template["type"],
                target_action=template["target_action"],
                target_value=target_value,
                current_progress=0,
                rewards=rewards,
                difficulty=template["difficulty"],
                quest_date=datetime.utcnow().date(),
                completed=False,
                rewards_claimed=False
            )
            
            session.add(quest)
            
            return {
                "id": quest.id,
                "name": quest.name,
                "description": quest.description,
                "type": quest.quest_type,
                "target_value": quest.target_value,
                "rewards": quest.rewards,
                "difficulty": quest.difficulty
            }
            
        except Exception as e:
            logger.error(f"Failed to create quest from template: {e}")
            return None
    
    def _calculate_progress_increase(self, action: str, metadata: Dict) -> int:
        """Calculate how much progress to add based on action and metadata."""
        # Simple progress calculation - can be enhanced based on specific actions
        progress_map = {
            "game_played": 1,
            "game_won_streak": metadata.get("streak_length", 1),
            "coins_earned": metadata.get("amount", 0),
            "friend_added": 1,
            "trade_completed": 1,
            "item_obtained": 1,
            "daily_login": 1,
            "coins_spent": metadata.get("amount", 0),
            "xp_gained": metadata.get("amount", 0),
            "daily_bonus_claimed": 1
        }
        
        return progress_map.get(action, 1)


# Global instance
daily_quest_system = DailyQuestSystem()