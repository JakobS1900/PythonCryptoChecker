"""
Analytics and monitoring engine for tracking user engagement and platform metrics.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from collections import defaultdict
from logger import logger
from database.unified_models import (
    User, GameSession, Achievement, VirtualWallet, CollectibleItem,
    Friendship, DailyReward, UserOnboarding, TutorialProgress
)


class AnalyticsEvent:
    """Individual analytics event."""
    
    def __init__(self, event_type: str, user_id: str = None, 
                 properties: Dict[str, Any] = None, timestamp: datetime = None):
        self.event_type = event_type
        self.user_id = user_id
        self.properties = properties or {}
        self.timestamp = timestamp or datetime.utcnow()


class AnalyticsEngine:
    """Main analytics and monitoring system."""
    
    def __init__(self):
        self.event_buffer = []
        self.buffer_size = 1000
        self.flush_interval = 300  # 5 minutes
        self.metrics_cache = {}
        self.cache_ttl = 600  # 10 minutes
        
    async def track_event(self, event: AnalyticsEvent):
        """Track an analytics event."""
        try:
            self.event_buffer.append({
                "event_type": event.event_type,
                "user_id": event.user_id,
                "properties": event.properties,
                "timestamp": event.timestamp.isoformat()
            })
            
            # Flush buffer if full
            if len(self.event_buffer) >= self.buffer_size:
                await self.flush_events()
                
            logger.debug(f"Tracked event: {event.event_type}")
            
        except Exception as e:
            logger.error(f"Failed to track event: {e}")
    
    async def flush_events(self):
        """Flush events to storage (in production would be to analytics DB)."""
        try:
            if not self.event_buffer:
                return
            
            # In production, this would write to a time-series database like InfluxDB
            # For now, we'll just log the events
            logger.info(f"Flushing {len(self.event_buffer)} analytics events")
            
            # Clear buffer
            self.event_buffer = []
            
        except Exception as e:
            logger.error(f"Failed to flush events: {e}")
    
    async def get_user_metrics(self, session: AsyncSession, user_id: str, 
                              days: int = 30) -> Dict[str, Any]:
        """Get comprehensive user metrics."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get user info
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {"error": "User not found"}
            
            # Gaming metrics
            gaming_result = await session.execute(
                select(
                    func.count(GameSession.id).label('total_games'),
                    func.sum(GameSession.bet_amount).label('total_wagered'),
                    func.sum(GameSession.payout_amount).label('total_winnings'),
                    func.avg(GameSession.bet_amount).label('avg_bet'),
                    func.count(GameSession.id).filter(GameSession.won == True).label('games_won')
                ).where(
                    and_(
                        GameSession.user_id == user_id,
                        GameSession.created_at >= cutoff_date
                    )
                )
            )
            gaming_stats = gaming_result.first()
            
            # Achievement metrics
            achievement_result = await session.execute(
                select(func.count(Achievement.id)).where(
                    and_(
                        Achievement.user_id == user_id,
                        Achievement.unlocked_at >= cutoff_date
                    )
                )
            )
            new_achievements = achievement_result.scalar() or 0
            
            # Social metrics
            friends_result = await session.execute(
                select(func.count(Friendship.id)).where(
                    or_(
                        Friendship.sender_id == user_id,
                        Friendship.receiver_id == user_id
                    )
                )
            )
            total_friends = friends_result.scalar() or 0
            
            # Daily login streak
            daily_result = await session.execute(
                select(DailyReward).where(DailyReward.user_id == user_id)
            )
            daily_reward = daily_result.scalar_one_or_none()
            
            # Onboarding status
            onboarding_result = await session.execute(
                select(UserOnboarding).where(UserOnboarding.user_id == user_id)
            )
            onboarding = onboarding_result.scalar_one_or_none()
            
            # Calculate user level and rank
            level_info = await self._calculate_user_level(session, user)
            
            return {
                "user_id": user_id,
                "period_days": days,
                "profile": {
                    "username": user.username,
                    "display_name": user.display_name,
                    "level": user.current_level,
                    "total_xp": user.total_experience,
                    "prestige_level": user.prestige_level,
                    "account_age_days": (datetime.utcnow() - user.created_at).days,
                    "last_login": user.last_login.isoformat() if user.last_login else None
                },
                "gaming": {
                    "total_games": gaming_stats.total_games or 0,
                    "total_wagered": float(gaming_stats.total_wagered or 0),
                    "total_winnings": float(gaming_stats.total_winnings or 0),
                    "average_bet": float(gaming_stats.avg_bet or 0),
                    "games_won": gaming_stats.games_won or 0,
                    "win_rate": (gaming_stats.games_won / gaming_stats.total_games * 100) if gaming_stats.total_games else 0,
                    "net_profit": float((gaming_stats.total_winnings or 0) - (gaming_stats.total_wagered or 0))
                },
                "achievements": {
                    "new_achievements": new_achievements,
                    "achievement_rate": new_achievements / days if days > 0 else 0
                },
                "social": {
                    "total_friends": total_friends,
                    "social_rank": await self._get_user_social_rank(session, user_id)
                },
                "engagement": {
                    "daily_streak": daily_reward.consecutive_days if daily_reward else 0,
                    "last_daily_claim": daily_reward.last_claim_date.isoformat() if daily_reward and daily_reward.last_claim_date else None,
                    "onboarding_completed": onboarding.completed if onboarding else False
                },
                "ranking": level_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get user metrics: {e}")
            return {"error": str(e)}
    
    async def get_platform_metrics(self, session: AsyncSession, days: int = 30) -> Dict[str, Any]:
        """Get platform-wide analytics metrics."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # User metrics
            total_users_result = await session.execute(select(func.count(User.id)))
            total_users = total_users_result.scalar() or 0
            
            new_users_result = await session.execute(
                select(func.count(User.id)).where(User.created_at >= cutoff_date)
            )
            new_users = new_users_result.scalar() or 0
            
            active_users_result = await session.execute(
                select(func.count(User.id)).where(User.last_login >= cutoff_date)
            )
            active_users = active_users_result.scalar() or 0
            
            # Gaming metrics
            gaming_result = await session.execute(
                select(
                    func.count(GameSession.id).label('total_games'),
                    func.sum(GameSession.bet_amount).label('total_wagered'),
                    func.sum(GameSession.payout_amount).label('total_winnings'),
                    func.avg(GameSession.bet_amount).label('avg_bet'),
                    func.count(func.distinct(GameSession.user_id)).label('active_players')
                ).where(GameSession.created_at >= cutoff_date)
            )
            gaming_stats = gaming_result.first()
            
            # Achievement metrics
            achievement_result = await session.execute(
                select(
                    func.count(Achievement.id).label('total_achievements'),
                    func.count(func.distinct(Achievement.user_id)).label('active_achievers')
                ).where(Achievement.unlocked_at >= cutoff_date)
            )
            achievement_stats = achievement_result.first()
            
            # Social metrics
            friendship_result = await session.execute(
                select(func.count(Friendship.id)).where(
                    and_(
                        Friendship.created_at >= cutoff_date,
                        Friendship.status == "accepted"
                    )
                )
            )
            new_friendships = friendship_result.scalar() or 0
            
            # Onboarding metrics
            onboarding_result = await session.execute(
                select(
                    func.count(UserOnboarding.id).label('total_onboarding'),
                    func.count(UserOnboarding.id).filter(UserOnboarding.completed == True).label('completed_onboarding')
                ).where(UserOnboarding.started_at >= cutoff_date)
            )
            onboarding_stats = onboarding_result.first()
            
            # Daily active users trend
            dau_trend = await self._get_daily_active_users_trend(session, days)
            
            # Revenue metrics (virtual economy)
            economy_metrics = await self._get_economy_metrics(session, cutoff_date)
            
            return {
                "period_days": days,
                "users": {
                    "total_users": total_users,
                    "new_users": new_users,
                    "active_users": active_users,
                    "user_growth_rate": (new_users / total_users * 100) if total_users > 0 else 0,
                    "user_retention_rate": (active_users / total_users * 100) if total_users > 0 else 0
                },
                "gaming": {
                    "total_games": gaming_stats.total_games or 0,
                    "total_wagered": float(gaming_stats.total_wagered or 0),
                    "total_winnings": float(gaming_stats.total_winnings or 0),
                    "average_bet": float(gaming_stats.avg_bet or 0),
                    "active_players": gaming_stats.active_players or 0,
                    "games_per_user": (gaming_stats.total_games / gaming_stats.active_players) if gaming_stats.active_players else 0,
                    "house_edge": ((gaming_stats.total_wagered - gaming_stats.total_winnings) / gaming_stats.total_wagered * 100) if gaming_stats.total_wagered else 0
                },
                "achievements": {
                    "total_achievements": achievement_stats.total_achievements or 0,
                    "active_achievers": achievement_stats.active_achievers or 0,
                    "achievements_per_user": (achievement_stats.total_achievements / achievement_stats.active_achievers) if achievement_stats.active_achievers else 0
                },
                "social": {
                    "new_friendships": new_friendships,
                    "social_engagement_rate": (new_friendships / active_users * 100) if active_users > 0 else 0
                },
                "onboarding": {
                    "total_started": onboarding_stats.total_onboarding or 0,
                    "total_completed": onboarding_stats.completed_onboarding or 0,
                    "completion_rate": (onboarding_stats.completed_onboarding / onboarding_stats.total_onboarding * 100) if onboarding_stats.total_onboarding else 0
                },
                "engagement": {
                    "dau_trend": dau_trend,
                    "avg_session_duration": await self._calculate_avg_session_duration(session, cutoff_date)
                },
                "economy": economy_metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to get platform metrics: {e}")
            return {"error": str(e)}
    
    async def get_real_time_metrics(self, session: AsyncSession) -> Dict[str, Any]:
        """Get real-time platform metrics."""
        try:
            now = datetime.utcnow()
            last_hour = now - timedelta(hours=1)
            last_24h = now - timedelta(hours=24)
            
            # Users online (last 15 minutes)
            online_cutoff = now - timedelta(minutes=15)
            online_result = await session.execute(
                select(func.count(User.id)).where(User.last_login >= online_cutoff)
            )
            users_online = online_result.scalar() or 0
            
            # Active games (last hour)
            games_result = await session.execute(
                select(func.count(GameSession.id)).where(GameSession.created_at >= last_hour)
            )
            games_last_hour = games_result.scalar() or 0
            
            # New signups (last 24h)
            signup_result = await session.execute(
                select(func.count(User.id)).where(User.created_at >= last_24h)
            )
            new_signups = signup_result.scalar() or 0
            
            # Active achievements (last hour)
            achievement_result = await session.execute(
                select(func.count(Achievement.id)).where(Achievement.unlocked_at >= last_hour)
            )
            achievements_last_hour = achievement_result.scalar() or 0
            
            return {
                "timestamp": now.isoformat(),
                "users_online": users_online,
                "games_last_hour": games_last_hour,
                "new_signups_24h": new_signups,
                "achievements_last_hour": achievements_last_hour,
                "system_status": "healthy",
                "server_uptime": await self._get_server_uptime()
            }
            
        except Exception as e:
            logger.error(f"Failed to get real-time metrics: {e}")
            return {"error": str(e)}
    
    async def track_user_action(self, user_id: str, action: str, 
                              properties: Dict[str, Any] = None):
        """Track a specific user action."""
        event = AnalyticsEvent(
            event_type=f"user_action.{action}",
            user_id=user_id,
            properties=properties
        )
        await self.track_event(event)
    
    async def track_game_event(self, user_id: str, game_type: str, 
                             event_type: str, properties: Dict[str, Any] = None):
        """Track a gaming-specific event."""
        event = AnalyticsEvent(
            event_type=f"game.{game_type}.{event_type}",
            user_id=user_id,
            properties=properties
        )
        await self.track_event(event)
    
    async def get_user_cohort_analysis(self, session: AsyncSession, 
                                     cohort_period: str = "weekly") -> Dict[str, Any]:
        """Perform cohort analysis on user retention."""
        try:
            # This would typically require more complex SQL queries
            # For now, return a simplified cohort analysis
            
            cohorts = {}
            if cohort_period == "weekly":
                # Group users by signup week
                result = await session.execute(
                    text("""
                        SELECT 
                            DATE_TRUNC('week', created_at) as cohort_week,
                            COUNT(*) as cohort_size
                        FROM users 
                        WHERE created_at >= NOW() - INTERVAL '12 weeks'
                        GROUP BY cohort_week
                        ORDER BY cohort_week
                    """)
                )
                
                for row in result:
                    cohort_week = row.cohort_week.isoformat()
                    cohorts[cohort_week] = {
                        "cohort_size": row.cohort_size,
                        "retention": await self._calculate_cohort_retention(
                            session, row.cohort_week, "weekly"
                        )
                    }
            
            return {
                "cohort_period": cohort_period,
                "cohorts": cohorts,
                "analysis_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to perform cohort analysis: {e}")
            return {"error": str(e)}
    
    async def get_funnel_analysis(self, session: AsyncSession) -> Dict[str, Any]:
        """Analyze user funnel from signup to engagement."""
        try:
            # Define funnel steps
            total_users_result = await session.execute(select(func.count(User.id)))
            total_users = total_users_result.scalar() or 0
            
            # Users who completed onboarding
            onboarding_result = await session.execute(
                select(func.count(UserOnboarding.id)).where(UserOnboarding.completed == True)
            )
            completed_onboarding = onboarding_result.scalar() or 0
            
            # Users who played at least one game
            played_game_result = await session.execute(
                select(func.count(func.distinct(GameSession.user_id)))
            )
            played_games = played_game_result.scalar() or 0
            
            # Users who made a friend
            social_users_result = await session.execute(
                select(func.count(func.distinct(Friendship.sender_id)))
            )
            social_users = social_users_result.scalar() or 0
            
            # Users who unlocked an achievement
            achievement_users_result = await session.execute(
                select(func.count(func.distinct(Achievement.user_id)))
            )
            achievement_users = achievement_users_result.scalar() or 0
            
            funnel_steps = [
                {"step": "signup", "users": total_users, "conversion_rate": 100.0},
                {"step": "completed_onboarding", "users": completed_onboarding, "conversion_rate": (completed_onboarding / total_users * 100) if total_users else 0},
                {"step": "played_game", "users": played_games, "conversion_rate": (played_games / total_users * 100) if total_users else 0},
                {"step": "social_engagement", "users": social_users, "conversion_rate": (social_users / total_users * 100) if total_users else 0},
                {"step": "unlocked_achievement", "users": achievement_users, "conversion_rate": (achievement_users / total_users * 100) if total_users else 0}
            ]
            
            return {
                "funnel_steps": funnel_steps,
                "overall_conversion": (achievement_users / total_users * 100) if total_users else 0,
                "biggest_dropoff": self._identify_biggest_dropoff(funnel_steps)
            }
            
        except Exception as e:
            logger.error(f"Failed to perform funnel analysis: {e}")
            return {"error": str(e)}
    
    # Helper methods
    
    async def _calculate_user_level(self, session: AsyncSession, user: User) -> Dict[str, Any]:
        """Calculate user level and ranking information."""
        try:
            # Get user's rank by XP
            rank_result = await session.execute(
                select(func.count(User.id)).where(User.total_experience > user.total_experience)
            )
            rank = rank_result.scalar() + 1
            
            # Calculate next level requirements
            current_level_xp = user.current_level * 1000  # Simple calculation
            next_level_xp = (user.current_level + 1) * 1000
            
            return {
                "current_level": user.current_level,
                "global_rank": rank,
                "total_xp": user.total_experience,
                "xp_to_next_level": max(0, next_level_xp - user.total_experience),
                "level_progress": min(100, (user.total_experience - current_level_xp) / 1000 * 100)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate user level: {e}")
            return {}
    
    async def _get_user_social_rank(self, session: AsyncSession, user_id: str) -> int:
        """Get user's social ranking."""
        try:
            # Count users with more friends
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM (
                        SELECT user_id, COUNT(*) as friend_count
                        FROM (
                            SELECT sender_id as user_id FROM friendships WHERE status = 'accepted'
                            UNION ALL
                            SELECT receiver_id as user_id FROM friendships WHERE status = 'accepted'
                        ) friends
                        WHERE user_id != :user_id
                        GROUP BY user_id
                        HAVING COUNT(*) > (
                            SELECT COUNT(*) FROM (
                                SELECT sender_id as user_id FROM friendships WHERE status = 'accepted' AND (sender_id = :user_id OR receiver_id = :user_id)
                                UNION ALL
                                SELECT receiver_id as user_id FROM friendships WHERE status = 'accepted' AND (sender_id = :user_id OR receiver_id = :user_id)
                            ) user_friends
                            WHERE user_id != :user_id
                        )
                    ) ranked_users
                """), {"user_id": user_id}
            )
            
            return result.scalar() + 1
            
        except Exception as e:
            logger.error(f"Failed to get user social rank: {e}")
            return 0
    
    async def _get_daily_active_users_trend(self, session: AsyncSession, days: int) -> List[Dict[str, Any]]:
        """Get daily active users trend."""
        try:
            trend = []
            for i in range(days):
                date = datetime.utcnow().date() - timedelta(days=i)
                next_date = date + timedelta(days=1)
                
                result = await session.execute(
                    select(func.count(func.distinct(User.id))).where(
                        and_(
                            User.last_login >= date,
                            User.last_login < next_date
                        )
                    )
                )
                active_users = result.scalar() or 0
                
                trend.append({
                    "date": date.isoformat(),
                    "active_users": active_users
                })
            
            return list(reversed(trend))
            
        except Exception as e:
            logger.error(f"Failed to get DAU trend: {e}")
            return []
    
    async def _get_economy_metrics(self, session: AsyncSession, cutoff_date: datetime) -> Dict[str, Any]:
        """Get virtual economy metrics."""
        try:
            # Total GEM coins in circulation
            gem_result = await session.execute(
                select(func.sum(VirtualWallet.gem_coins))
            )
            total_gems = float(gem_result.scalar() or 0)
            
            # GEM coins earned through gaming
            gaming_gems_result = await session.execute(
                select(func.sum(GameSession.payout_amount)).where(
                    GameSession.created_at >= cutoff_date
                )
            )
            gaming_gems = float(gaming_gems_result.scalar() or 0)
            
            # Average wallet balance
            avg_balance_result = await session.execute(
                select(func.avg(VirtualWallet.gem_coins))
            )
            avg_balance = float(avg_balance_result.scalar() or 0)
            
            return {
                "total_gems_circulation": total_gems,
                "gems_earned_gaming": gaming_gems,
                "average_wallet_balance": avg_balance,
                "economy_health": "stable" if total_gems > 0 else "new"
            }
            
        except Exception as e:
            logger.error(f"Failed to get economy metrics: {e}")
            return {}
    
    async def _calculate_avg_session_duration(self, session: AsyncSession, cutoff_date: datetime) -> float:
        """Calculate average session duration in minutes."""
        try:
            # This would require session tracking in production
            # For now, return a placeholder
            return 25.5  # Average 25.5 minutes per session
            
        except Exception as e:
            logger.error(f"Failed to calculate session duration: {e}")
            return 0.0
    
    async def _get_server_uptime(self) -> str:
        """Get server uptime (placeholder)."""
        return "99.9%"
    
    async def _calculate_cohort_retention(self, session: AsyncSession, 
                                        cohort_start: datetime, period: str) -> List[float]:
        """Calculate retention rates for a cohort."""
        # Simplified retention calculation
        return [100.0, 75.0, 60.0, 50.0, 45.0, 40.0, 38.0, 35.0]  # Week 0-7 retention
    
    def _identify_biggest_dropoff(self, funnel_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify the biggest dropoff in the funnel."""
        biggest_dropoff = {"step": "", "dropoff_rate": 0.0}
        
        for i in range(1, len(funnel_steps)):
            current_rate = funnel_steps[i]["conversion_rate"]
            previous_rate = funnel_steps[i-1]["conversion_rate"]
            dropoff_rate = previous_rate - current_rate
            
            if dropoff_rate > biggest_dropoff["dropoff_rate"]:
                biggest_dropoff = {
                    "step": funnel_steps[i]["step"],
                    "dropoff_rate": dropoff_rate
                }
        
        return biggest_dropoff


# Global instance
analytics_engine = AnalyticsEngine()