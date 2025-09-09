"""
Retention manager for tracking user engagement patterns and preventing churn.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func, desc

from database.unified_models import User, UserSession, EngagementMetrics, RetentionMetrics
from logger import logger


class RetentionManager:
    """Manages user retention tracking and anti-churn measures."""
    
    def __init__(self):
        self.churn_risk_thresholds = {
            "days_since_login": 7,      # 7+ days = at risk
            "session_decline": 0.3,     # 30% decline in sessions
            "engagement_drop": 0.5,     # 50% drop in engagement score
            "quest_completion": 0.2     # Less than 20% quest completion
        }
        
        self.retention_campaigns = self._initialize_campaigns()
    
    def _initialize_campaigns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize retention campaigns for different user segments."""
        return {
            "welcome_back": {
                "trigger": "returning_after_absence",
                "conditions": {"days_absent": [3, 7, 14, 30]},
                "rewards": {
                    3: {"gem_coins": 200, "message": "Welcome back! Here's a small gift."},
                    7: {"gem_coins": 500, "item_pack": "standard", "message": "We missed you! Here's a welcome back bonus."},
                    14: {"gem_coins": 1000, "item_pack": "premium", "message": "Great to see you again! Special comeback reward."},
                    30: {"gem_coins": 2000, "item_pack": "legendary", "message": "Amazing comeback! Here's an exclusive reward."}
                }
            },
            "engagement_booster": {
                "trigger": "low_engagement",
                "conditions": {"engagement_score_below": 50},
                "rewards": {"gem_coins": 300, "bonus_xp": 100, "message": "Let's get back in the game! Bonus rewards await."}
            },
            "streak_recovery": {
                "trigger": "broken_streak",
                "conditions": {"previous_streak": [7, 14, 30]},
                "rewards": {
                    7: {"gem_coins": 400, "message": "Don't give up! Restart your streak with bonus coins."},
                    14: {"gem_coins": 800, "message": "Your dedication matters! Special streak recovery bonus."},
                    30: {"gem_coins": 1500, "message": "Legendary streaks deserve legendary comebacks!"}
                }
            }
        }
    
    async def track_user_session(self, session: AsyncSession, user_id: str, session_duration: int = None) -> Dict[str, Any]:
        """Track user session for retention analytics."""
        try:
            now = datetime.utcnow()
            
            # Record session
            user_session = UserSession(
                user_id=user_id,
                start_time=now,
                end_time=now + timedelta(minutes=session_duration or 30),
                duration_minutes=session_duration or 30,
                session_type="game_session",
                created_at=now
            )
            session.add(user_session)
            
            # Update retention metrics
            await self._update_retention_metrics(session, user_id)
            
            await session.commit()
            
            return {
                "session_recorded": True,
                "session_id": user_session.id,
                "duration": session_duration or 30
            }
            
        except Exception as e:
            logger.error(f"Failed to track user session: {e}")
            return {"error": str(e)}
    
    async def get_user_streak(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get user's current login streak information."""
        try:
            result = await session.execute(
                select(EngagementMetrics).where(EngagementMetrics.user_id == user_id)
            )
            metrics = result.scalar_one_or_none()
            
            if not metrics:
                return {
                    "current_streak": 0,
                    "longest_streak": 0,
                    "last_login": None,
                    "streak_status": "inactive"
                }
            
            # Calculate current streak
            current_streak = await self._calculate_current_streak(session, user_id)
            
            return {
                "current_streak": current_streak,
                "longest_streak": metrics.longest_streak or 0,
                "last_login": metrics.last_login.isoformat() if metrics.last_login else None,
                "streak_status": "active" if current_streak > 0 else "inactive",
                "next_milestone": self._get_next_streak_milestone(current_streak)
            }
            
        except Exception as e:
            logger.error(f"Failed to get user streak: {e}")
            return {"error": str(e)}
    
    async def check_churn_risk(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Analyze user's churn risk level."""
        try:
            # Get user metrics
            metrics_result = await session.execute(
                select(EngagementMetrics).where(EngagementMetrics.user_id == user_id)
            )
            metrics = metrics_result.scalar_one_or_none()
            
            if not metrics:
                return {"risk_level": "unknown", "factors": []}
            
            risk_factors = []
            risk_score = 0
            
            # Check days since last login
            if metrics.last_login:
                days_since_login = (datetime.utcnow() - metrics.last_login).days
                if days_since_login >= self.churn_risk_thresholds["days_since_login"]:
                    risk_factors.append(f"No login for {days_since_login} days")
                    risk_score += days_since_login * 2
            
            # Check engagement score decline
            if metrics.engagement_score < 50:  # Below average
                risk_factors.append("Low engagement score")
                risk_score += 20
            
            # Check session frequency
            recent_sessions = await self._get_recent_session_count(session, user_id, days=7)
            if recent_sessions < 3:  # Less than 3 sessions per week
                risk_factors.append("Low session frequency")
                risk_score += 15
            
            # Determine risk level
            if risk_score >= 50:
                risk_level = "high"
            elif risk_score >= 25:
                risk_level = "medium"
            elif risk_score >= 10:
                risk_level = "low"
            else:
                risk_level = "minimal"
            
            return {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "factors": risk_factors,
                "recommended_actions": self._get_retention_recommendations(risk_level)
            }
            
        except Exception as e:
            logger.error(f"Failed to check churn risk: {e}")
            return {"error": str(e)}
    
    async def check_returning_user_bonus(self, session: AsyncSession, user_id: str) -> Optional[Dict[str, Any]]:
        """Check if user qualifies for returning user bonus."""
        try:
            # Get last login
            result = await session.execute(
                select(EngagementMetrics.last_login, EngagementMetrics.previous_login)
                .where(EngagementMetrics.user_id == user_id)
            )
            metrics = result.first()
            
            if not metrics or not metrics.previous_login:
                return None
            
            # Calculate days absent
            days_absent = (metrics.last_login - metrics.previous_login).days
            
            # Check if qualifies for welcome back bonus
            campaign = self.retention_campaigns["welcome_back"]
            for threshold in campaign["conditions"]["days_absent"]:
                if days_absent >= threshold:
                    # Check if already awarded this bonus recently
                    if await self._already_awarded_recently(session, user_id, "welcome_back", days=threshold):
                        continue
                    
                    reward = campaign["rewards"][threshold]
                    
                    # Award the bonus
                    await self._award_retention_bonus(session, user_id, "welcome_back", reward)
                    
                    return {
                        "type": "welcome_back",
                        "days_absent": days_absent,
                        "reward": reward,
                        "message": reward["message"]
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check returning user bonus: {e}")
            return None
    
    async def update_daily_streaks(self, session: AsyncSession) -> Dict[str, Any]:
        """Update all user streaks (called daily)."""
        try:
            yesterday = datetime.utcnow().date() - timedelta(days=1)
            updated_count = 0
            
            # Get all users with engagement metrics
            result = await session.execute(
                select(EngagementMetrics)
            )
            all_metrics = result.scalars().all()
            
            for metrics in all_metrics:
                if metrics.last_login and metrics.last_login.date() != yesterday:
                    # Streak broken - reset to 0
                    if metrics.login_streak > 0:
                        # Save as longest streak if needed
                        if metrics.login_streak > (metrics.longest_streak or 0):
                            metrics.longest_streak = metrics.login_streak
                        
                        # Trigger streak recovery campaign
                        if metrics.login_streak >= 7:
                            await self._trigger_streak_recovery(session, metrics.user_id, metrics.login_streak)
                        
                        metrics.login_streak = 0
                        updated_count += 1
            
            await session.commit()
            
            return {"updated_count": updated_count}
            
        except Exception as e:
            logger.error(f"Failed to update daily streaks: {e}")
            return {"error": str(e)}
    
    async def get_retention_analytics(self, session: AsyncSession, days: int = 30) -> Dict[str, Any]:
        """Get retention analytics for the platform."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get total active users
            active_users_result = await session.execute(
                select(func.count(EngagementMetrics.user_id)).where(
                    EngagementMetrics.last_login >= cutoff_date
                )
            )
            active_users = active_users_result.scalar() or 0
            
            # Get returning users (logged in multiple times)
            returning_users_result = await session.execute(
                select(func.count(EngagementMetrics.user_id)).where(
                    and_(
                        EngagementMetrics.last_login >= cutoff_date,
                        EngagementMetrics.total_sessions > 1
                    )
                )
            )
            returning_users = returning_users_result.scalar() or 0
            
            # Calculate retention rate
            retention_rate = (returning_users / active_users * 100) if active_users > 0 else 0
            
            # Get average session time
            avg_session_result = await session.execute(
                select(func.avg(UserSession.duration_minutes)).where(
                    UserSession.start_time >= cutoff_date
                )
            )
            avg_session_time = avg_session_result.scalar() or 0
            
            # Get churn risk distribution
            high_risk_count = 0  # Would implement churn risk analysis
            
            return {
                "period_days": days,
                "active_users": active_users,
                "returning_users": returning_users,
                "retention_rate": round(retention_rate, 2),
                "average_session_minutes": round(avg_session_time, 2),
                "high_risk_users": high_risk_count,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get retention analytics: {e}")
            return {"error": str(e)}
    
    async def _update_retention_metrics(self, session: AsyncSession, user_id: str):
        """Update user's retention metrics."""
        try:
            result = await session.execute(
                select(RetentionMetrics).where(RetentionMetrics.user_id == user_id)
            )
            metrics = result.scalar_one_or_none()
            
            if not metrics:
                metrics = RetentionMetrics(
                    user_id=user_id,
                    first_session=datetime.utcnow(),
                    last_session=datetime.utcnow(),
                    total_sessions=1,
                    average_session_length=30,
                    days_active=1
                )
                session.add(metrics)
            else:
                metrics.last_session = datetime.utcnow()
                metrics.total_sessions += 1
                
                # Update days active
                first_day = metrics.first_session.date()
                today = datetime.utcnow().date()
                metrics.days_active = (today - first_day).days + 1
                
        except Exception as e:
            logger.error(f"Failed to update retention metrics: {e}")
    
    async def _calculate_current_streak(self, session: AsyncSession, user_id: str) -> int:
        """Calculate user's current login streak."""
        try:
            result = await session.execute(
                select(EngagementMetrics.login_streak).where(EngagementMetrics.user_id == user_id)
            )
            streak = result.scalar_one_or_none()
            return streak or 0
            
        except Exception as e:
            logger.error(f"Failed to calculate current streak: {e}")
            return 0
    
    def _get_next_streak_milestone(self, current_streak: int) -> Optional[int]:
        """Get the next streak milestone."""
        milestones = [3, 7, 14, 30, 60, 100]
        
        for milestone in milestones:
            if milestone > current_streak:
                return milestone
        
        return None
    
    async def _get_recent_session_count(self, session: AsyncSession, user_id: str, days: int) -> int:
        """Get number of sessions in recent days."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            result = await session.execute(
                select(func.count(UserSession.id)).where(
                    and_(
                        UserSession.user_id == user_id,
                        UserSession.start_time >= cutoff
                    )
                )
            )
            count = result.scalar() or 0
            return count
            
        except Exception as e:
            logger.error(f"Failed to get recent session count: {e}")
            return 0
    
    def _get_retention_recommendations(self, risk_level: str) -> List[str]:
        """Get retention recommendations based on risk level."""
        recommendations = {
            "high": [
                "Send personalized re-engagement email",
                "Offer special comeback bonus",
                "Show missed achievements and progress",
                "Provide limited-time exclusive rewards"
            ],
            "medium": [
                "Send reminder notification",
                "Highlight new features or content",
                "Offer login streak recovery bonus",
                "Show friend activity updates"
            ],
            "low": [
                "Send gentle reminder",
                "Show upcoming events",
                "Highlight achievements progress",
                "Send social updates"
            ],
            "minimal": [
                "Continue regular engagement",
                "Maintain current reward schedule"
            ]
        }
        
        return recommendations.get(risk_level, [])
    
    async def _already_awarded_recently(self, session: AsyncSession, user_id: str, bonus_type: str, days: int) -> bool:
        """Check if bonus was already awarded recently."""
        # Would check reward history
        return False  # Simplified - always allow for now
    
    async def _award_retention_bonus(self, session: AsyncSession, user_id: str, bonus_type: str, reward: Dict[str, Any]):
        """Award retention bonus to user."""
        try:
            # Award GEM coins if specified
            if "gem_coins" in reward:
                from database.unified_models import VirtualWallet
                
                wallet_result = await session.execute(
                    select(VirtualWallet).where(VirtualWallet.user_id == user_id)
                )
                wallet = wallet_result.scalar_one_or_none()
                
                if wallet:
                    wallet.gem_coins += reward["gem_coins"]
                    wallet.updated_at = datetime.utcnow()
            
            # Record the bonus award
            # Would create reward history record here
            
        except Exception as e:
            logger.error(f"Failed to award retention bonus: {e}")
    
    async def _trigger_streak_recovery(self, session: AsyncSession, user_id: str, broken_streak: int):
        """Trigger streak recovery campaign."""
        try:
            campaign = self.retention_campaigns["streak_recovery"]
            
            # Find appropriate reward tier
            reward_tier = None
            for threshold in sorted(campaign["conditions"]["previous_streak"], reverse=True):
                if broken_streak >= threshold:
                    reward_tier = threshold
                    break
            
            if reward_tier and reward_tier in campaign["rewards"]:
                reward = campaign["rewards"][reward_tier]
                await self._award_retention_bonus(session, user_id, "streak_recovery", reward)
                
                # Would send notification here
                logger.info(f"Triggered streak recovery for user {user_id}, broken streak: {broken_streak}")
                
        except Exception as e:
            logger.error(f"Failed to trigger streak recovery: {e}")


# Global instance
retention_manager = RetentionManager()