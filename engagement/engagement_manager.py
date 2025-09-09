"""
Main engagement manager coordinating all retention and engagement systems.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

from database.unified_models import User, UserSession, EngagementMetrics
from .daily_quests import DailyQuestSystem
from .rewards_system import RewardsSystem
from .retention_manager import RetentionManager
from logger import logger


class EngagementManager:
    """Central manager for all user engagement and retention systems."""
    
    def __init__(self):
        self.daily_quests = DailyQuestSystem()
        self.rewards_system = RewardsSystem()
        self.retention_manager = RetentionManager()
    
    async def on_user_login(self, session: AsyncSession, user_id: str, ip_address: str = None) -> Dict[str, Any]:
        """Handle user login event and trigger engagement systems."""
        try:
            engagement_data = {
                "login_bonus": None,
                "daily_quests": [],
                "streak_info": {},
                "notifications": []
            }
            
            # Update engagement metrics
            await self._update_engagement_metrics(session, user_id)
            
            # Process login bonus
            login_bonus = await self.rewards_system.process_login_bonus(session, user_id)
            if login_bonus:
                engagement_data["login_bonus"] = login_bonus
                engagement_data["notifications"].append({
                    "type": "login_bonus",
                    "message": f"Daily login bonus: {login_bonus['amount']} {login_bonus['type']}!",
                    "icon": "fas fa-gift"
                })
            
            # Get daily quests
            daily_quests = await self.daily_quests.get_user_daily_quests(session, user_id)
            engagement_data["daily_quests"] = daily_quests
            
            # Get streak information
            streak_info = await self.retention_manager.get_user_streak(session, user_id)
            engagement_data["streak_info"] = streak_info
            
            # Check for returning user bonuses
            returning_bonus = await self.retention_manager.check_returning_user_bonus(session, user_id)
            if returning_bonus:
                engagement_data["notifications"].append({
                    "type": "welcome_back",
                    "message": returning_bonus["message"],
                    "icon": "fas fa-star"
                })
            
            return engagement_data
            
        except Exception as e:
            logger.error(f"Failed to process user login engagement: {e}")
            return {"error": str(e)}
    
    async def on_user_action(self, session: AsyncSession, user_id: str, action: str, metadata: Dict = None) -> Dict[str, Any]:
        """Process user action for engagement tracking."""
        try:
            result = {
                "quest_progress": [],
                "achievements_unlocked": [],
                "rewards_earned": []
            }
            
            # Update quest progress
            quest_updates = await self.daily_quests.update_quest_progress(
                session, user_id, action, metadata or {}
            )
            result["quest_progress"] = quest_updates
            
            # Check for completed quests
            completed_quests = await self.daily_quests.check_completed_quests(session, user_id)
            if completed_quests:
                for quest in completed_quests:
                    # Award quest rewards
                    rewards = await self.rewards_system.award_quest_reward(
                        session, user_id, quest["id"], quest["rewards"]
                    )
                    result["rewards_earned"].extend(rewards)
            
            # Update engagement score
            await self._update_engagement_score(session, user_id, action)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process user action engagement: {e}")
            return {"error": str(e)}
    
    async def get_user_engagement_dashboard(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get comprehensive engagement dashboard data for user."""
        try:
            dashboard = {
                "daily_quests": await self.daily_quests.get_user_daily_quests(session, user_id),
                "login_streak": await self.retention_manager.get_user_streak(session, user_id),
                "weekly_progress": await self._get_weekly_progress(session, user_id),
                "engagement_score": await self._get_engagement_score(session, user_id),
                "upcoming_rewards": await self._get_upcoming_rewards(session, user_id),
                "completion_stats": await self._get_completion_stats(session, user_id)
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Failed to get engagement dashboard: {e}")
            return {"error": str(e)}
    
    async def process_daily_reset(self, session: AsyncSession) -> Dict[str, Any]:
        """Process daily reset for all engagement systems."""
        try:
            results = {
                "quests_reset": 0,
                "streaks_updated": 0,
                "bonuses_reset": 0,
                "errors": []
            }
            
            # Reset daily quests
            quest_results = await self.daily_quests.reset_daily_quests(session)
            results["quests_reset"] = quest_results.get("reset_count", 0)
            
            # Update login streaks
            streak_results = await self.retention_manager.update_daily_streaks(session)
            results["streaks_updated"] = streak_results.get("updated_count", 0)
            
            # Reset daily bonuses
            bonus_results = await self.rewards_system.reset_daily_bonuses(session)
            results["bonuses_reset"] = bonus_results.get("reset_count", 0)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to process daily reset: {e}")
            return {"error": str(e)}
    
    async def _update_engagement_metrics(self, session: AsyncSession, user_id: str):
        """Update user engagement metrics."""
        try:
            # Get or create engagement metrics
            result = await session.execute(
                select(EngagementMetrics).where(EngagementMetrics.user_id == user_id)
            )
            metrics = result.scalar_one_or_none()
            
            now = datetime.utcnow()
            
            if not metrics:
                metrics = EngagementMetrics(
                    user_id=user_id,
                    total_sessions=1,
                    total_playtime_minutes=0,
                    last_login=now,
                    login_streak=1,
                    engagement_score=10
                )
                session.add(metrics)
            else:
                # Update metrics
                metrics.total_sessions += 1
                metrics.last_login = now
                
                # Calculate login streak
                if metrics.last_login and metrics.last_login.date() == (now - timedelta(days=1)).date():
                    metrics.login_streak += 1
                elif metrics.last_login and metrics.last_login.date() != now.date():
                    metrics.login_streak = 1
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to update engagement metrics: {e}")
    
    async def _update_engagement_score(self, session: AsyncSession, user_id: str, action: str):
        """Update user engagement score based on action."""
        try:
            # Action score mapping
            action_scores = {
                "game_played": 5,
                "quest_completed": 10,
                "friend_added": 8,
                "item_traded": 6,
                "achievement_unlocked": 15,
                "daily_login": 3
            }
            
            score_increase = action_scores.get(action, 1)
            
            await session.execute(
                update(EngagementMetrics)
                .where(EngagementMetrics.user_id == user_id)
                .values(engagement_score=EngagementMetrics.engagement_score + score_increase)
            )
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to update engagement score: {e}")
    
    async def _get_weekly_progress(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get user's weekly progress data."""
        try:
            week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
            
            # Get sessions this week
            result = await session.execute(
                select(UserSession)
                .where(
                    and_(
                        UserSession.user_id == user_id,
                        UserSession.created_at >= week_start
                    )
                )
            )
            sessions = result.scalars().all()
            
            # Calculate daily activity
            daily_activity = {i: 0 for i in range(7)}
            for user_session in sessions:
                day_of_week = user_session.created_at.weekday()
                daily_activity[day_of_week] += 1
            
            return {
                "total_sessions": len(sessions),
                "daily_activity": daily_activity,
                "active_days": len([day for day, count in daily_activity.items() if count > 0])
            }
            
        except Exception as e:
            logger.error(f"Failed to get weekly progress: {e}")
            return {}
    
    async def _get_engagement_score(self, session: AsyncSession, user_id: str) -> int:
        """Get user's current engagement score."""
        try:
            result = await session.execute(
                select(EngagementMetrics.engagement_score)
                .where(EngagementMetrics.user_id == user_id)
            )
            score = result.scalar_one_or_none()
            return score or 0
            
        except Exception as e:
            logger.error(f"Failed to get engagement score: {e}")
            return 0
    
    async def _get_upcoming_rewards(self, session: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
        """Get upcoming rewards for user."""
        try:
            upcoming = []
            
            # Get current streak for streak rewards
            streak_info = await self.retention_manager.get_user_streak(session, user_id)
            current_streak = streak_info.get("current_streak", 0)
            
            # Add milestone rewards
            milestones = [7, 14, 30, 60, 100]
            for milestone in milestones:
                if milestone > current_streak:
                    upcoming.append({
                        "type": "login_streak",
                        "requirement": f"{milestone} day login streak",
                        "days_remaining": milestone - current_streak,
                        "reward": f"Bonus rewards and {milestone * 100} GEM coins"
                    })
                    break
            
            return upcoming[:3]  # Return top 3
            
        except Exception as e:
            logger.error(f"Failed to get upcoming rewards: {e}")
            return []
    
    async def _get_completion_stats(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get user completion statistics."""
        try:
            # Get today's quest completion
            today_quests = await self.daily_quests.get_user_daily_quests(session, user_id)
            completed_today = len([q for q in today_quests if q.get("completed")])
            total_today = len(today_quests)
            
            return {
                "daily_quests": {
                    "completed": completed_today,
                    "total": total_today,
                    "percentage": (completed_today / total_today * 100) if total_today > 0 else 0
                },
                "weekly_login": {
                    "completed": 0,  # Would calculate from weekly data
                    "total": 7,
                    "percentage": 0
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get completion stats: {e}")
            return {}


# Global instance
engagement_manager = EngagementManager()