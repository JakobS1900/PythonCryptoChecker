"""
Central notification management system for user engagement.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func

from database.unified_models import User, Notification, NotificationPreferences, NotificationType
from .push_service import PushNotificationService
from .email_service import EmailService
from logger import logger


class NotificationManager:
    """Central manager for all notification types and delivery."""
    
    def __init__(self):
        self.push_service = PushNotificationService()
        self.email_service = EmailService()
        
        # Notification templates
        self.templates = self._initialize_templates()
        
        # Rate limiting
        self.rate_limits = {
            "push": {"max_per_hour": 5, "max_per_day": 20},
            "email": {"max_per_hour": 2, "max_per_day": 5},
            "in_app": {"max_per_hour": 10, "max_per_day": 50}
        }
    
    def _initialize_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize notification templates."""
        return {
            "welcome": {
                "title": "Welcome to CryptoGaming!",
                "body": "Start your gaming journey with 1000 free GEM coins!",
                "type": NotificationType.WELCOME,
                "channels": ["in_app", "email"],
                "priority": "high",
                "action_url": "/dashboard"
            },
            "daily_bonus": {
                "title": "Daily Bonus Available!",
                "body": "Your daily login bonus is ready to claim. Don't miss out!",
                "type": NotificationType.DAILY_BONUS,
                "channels": ["push", "in_app"],
                "priority": "medium",
                "action_url": "/dashboard"
            },
            "quest_available": {
                "title": "New Daily Quests!",
                "body": "Fresh quests are waiting. Complete them for great rewards!",
                "type": NotificationType.QUEST_REMINDER,
                "channels": ["push", "in_app"],
                "priority": "medium",
                "action_url": "/dashboard"
            },
            "quest_completed": {
                "title": "Quest Completed! 🎉",
                "body": "Congratulations! You've completed '{quest_name}' and earned rewards.",
                "type": NotificationType.QUEST_COMPLETED,
                "channels": ["in_app"],
                "priority": "low",
                "action_url": "/dashboard"
            },
            "achievement_unlocked": {
                "title": "Achievement Unlocked! 🏆",
                "body": "You've unlocked '{achievement_name}'! Check out your progress.",
                "type": NotificationType.ACHIEVEMENT,
                "channels": ["push", "in_app"],
                "priority": "high",
                "action_url": "/achievements"
            },
            "friend_request": {
                "title": "New Friend Request",
                "body": "{friend_name} wants to be your friend!",
                "type": NotificationType.FRIEND_REQUEST,
                "channels": ["push", "in_app"],
                "priority": "medium",
                "action_url": "/social"
            },
            "friend_accepted": {
                "title": "Friend Request Accepted",
                "body": "{friend_name} accepted your friend request!",
                "type": NotificationType.SOCIAL,
                "channels": ["in_app"],
                "priority": "low",
                "action_url": "/social"
            },
            "game_won": {
                "title": "Big Win! 💰",
                "body": "Congratulations! You won {amount} GEM coins in your last game!",
                "type": NotificationType.GAME_RESULT,
                "channels": ["in_app"],
                "priority": "medium",
                "action_url": "/gaming"
            },
            "streak_milestone": {
                "title": "Login Streak Milestone! 🔥",
                "body": "Amazing! You've reached a {days}-day login streak!",
                "type": NotificationType.MILESTONE,
                "channels": ["push", "in_app"],
                "priority": "high",
                "action_url": "/dashboard"
            },
            "comeback_bonus": {
                "title": "Welcome Back! 🎁",
                "body": "We missed you! Here's a special comeback bonus.",
                "type": NotificationType.COMEBACK,
                "channels": ["push", "email", "in_app"],
                "priority": "high",
                "action_url": "/dashboard"
            },
            "low_balance": {
                "title": "Low Balance Warning",
                "body": "Your GEM coin balance is running low. Time to play some games!",
                "type": NotificationType.LOW_BALANCE,
                "channels": ["in_app"],
                "priority": "low",
                "action_url": "/gaming"
            },
            "level_up": {
                "title": "Level Up! ⭐",
                "body": "Congratulations! You've reached level {level}!",
                "type": NotificationType.LEVEL_UP,
                "channels": ["push", "in_app"],
                "priority": "high",
                "action_url": "/profile"
            },
            "trade_completed": {
                "title": "Trade Completed",
                "body": "Your trade with {trader_name} has been completed!",
                "type": NotificationType.TRADE,
                "channels": ["in_app"],
                "priority": "medium",
                "action_url": "/inventory"
            },
            "maintenance": {
                "title": "Maintenance Notice",
                "body": "Scheduled maintenance will begin in {time}. Please save your progress.",
                "type": NotificationType.SYSTEM,
                "channels": ["push", "in_app"],
                "priority": "high",
                "action_url": "/dashboard"
            }
        }
    
    async def send_notification(self, session: AsyncSession, user_id: str, template_key: str, 
                              variables: Dict[str, Any] = None, channels: List[str] = None) -> Dict[str, Any]:
        """Send notification using template."""
        try:
            if template_key not in self.templates:
                return {"error": f"Template '{template_key}' not found"}
            
            template = self.templates[template_key]
            variables = variables or {}
            
            # Check user preferences
            user_prefs = await self._get_user_preferences(session, user_id)
            if not user_prefs or not self._should_send_notification(user_prefs, template["type"]):
                return {"skipped": "User preferences"}
            
            # Use provided channels or template defaults
            target_channels = channels or template["channels"]
            
            # Check rate limits
            allowed_channels = []
            for channel in target_channels:
                if await self._check_rate_limit(session, user_id, channel):
                    allowed_channels.append(channel)
            
            if not allowed_channels:
                return {"skipped": "Rate limited"}
            
            # Prepare notification content
            title = self._format_template_string(template["title"], variables)
            body = self._format_template_string(template["body"], variables)
            
            # Create notification record
            notification = Notification(
                user_id=user_id,
                title=title,
                body=body,
                notification_type=template["type"],
                priority=template["priority"],
                action_url=template.get("action_url"),
                metadata=variables,
                channels_sent=allowed_channels,
                created_at=datetime.utcnow()
            )
            session.add(notification)
            
            # Send through each channel
            delivery_results = {}
            
            for channel in allowed_channels:
                try:
                    if channel == "push":
                        result = await self.push_service.send_push_notification(
                            user_id, title, body, template.get("action_url")
                        )
                        delivery_results["push"] = result
                        
                    elif channel == "email":
                        result = await self.email_service.send_email(
                            user_id, title, body, template_key, variables
                        )
                        delivery_results["email"] = result
                        
                    elif channel == "in_app":
                        # In-app notifications are stored in database
                        notification.delivered_at = datetime.utcnow()
                        delivery_results["in_app"] = {"status": "delivered"}
                        
                    # Update rate limiting
                    await self._update_rate_limit(session, user_id, channel)
                    
                except Exception as e:
                    logger.error(f"Failed to send {channel} notification: {e}")
                    delivery_results[channel] = {"status": "failed", "error": str(e)}
            
            await session.commit()
            
            return {
                "notification_id": notification.id,
                "channels_sent": allowed_channels,
                "delivery_results": delivery_results,
                "title": title,
                "body": body
            }
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return {"error": str(e)}
    
    async def send_bulk_notification(self, session: AsyncSession, user_ids: List[str], 
                                   template_key: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send notification to multiple users."""
        try:
            results = {
                "total_users": len(user_ids),
                "successful": 0,
                "failed": 0,
                "skipped": 0,
                "errors": []
            }
            
            for user_id in user_ids:
                try:
                    result = await self.send_notification(session, user_id, template_key, variables)
                    
                    if "error" in result:
                        results["failed"] += 1
                        results["errors"].append(f"User {user_id}: {result['error']}")
                    elif "skipped" in result:
                        results["skipped"] += 1
                    else:
                        results["successful"] += 1
                        
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"User {user_id}: {str(e)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to send bulk notification: {e}")
            return {"error": str(e)}
    
    async def get_user_notifications(self, session: AsyncSession, user_id: str, 
                                   limit: int = 50, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get user's notifications."""
        try:
            query = select(Notification).where(Notification.user_id == user_id)
            
            if unread_only:
                query = query.where(Notification.read_at == None)
            
            query = query.order_by(Notification.created_at.desc()).limit(limit)
            
            result = await session.execute(query)
            notifications = result.scalars().all()
            
            notification_data = []
            for notification in notifications:
                notification_data.append({
                    "id": notification.id,
                    "title": notification.title,
                    "body": notification.body,
                    "type": notification.notification_type,
                    "priority": notification.priority,
                    "action_url": notification.action_url,
                    "read": notification.read_at is not None,
                    "created_at": notification.created_at.isoformat(),
                    "read_at": notification.read_at.isoformat() if notification.read_at else None
                })
            
            return notification_data
            
        except Exception as e:
            logger.error(f"Failed to get user notifications: {e}")
            return []
    
    async def mark_notification_read(self, session: AsyncSession, user_id: str, notification_id: str) -> bool:
        """Mark notification as read."""
        try:
            result = await session.execute(
                update(Notification)
                .where(
                    and_(
                        Notification.id == notification_id,
                        Notification.user_id == user_id,
                        Notification.read_at == None
                    )
                )
                .values(read_at=datetime.utcnow())
            )
            
            await session.commit()
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Failed to mark notification read: {e}")
            return False
    
    async def mark_all_read(self, session: AsyncSession, user_id: str) -> int:
        """Mark all user notifications as read."""
        try:
            result = await session.execute(
                update(Notification)
                .where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.read_at == None
                    )
                )
                .values(read_at=datetime.utcnow())
            )
            
            await session.commit()
            return result.rowcount
            
        except Exception as e:
            logger.error(f"Failed to mark all notifications read: {e}")
            return 0
    
    async def get_unread_count(self, session: AsyncSession, user_id: str) -> int:
        """Get count of unread notifications."""
        try:
            result = await session.execute(
                select(func.count(Notification.id)).where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.read_at == None
                    )
                )
            )
            count = result.scalar() or 0
            return count
            
        except Exception as e:
            logger.error(f"Failed to get unread count: {e}")
            return 0
    
    async def update_user_preferences(self, session: AsyncSession, user_id: str, 
                                    preferences: Dict[str, bool]) -> bool:
        """Update user notification preferences."""
        try:
            result = await session.execute(
                select(NotificationPreferences).where(NotificationPreferences.user_id == user_id)
            )
            user_prefs = result.scalar_one_or_none()
            
            if not user_prefs:
                user_prefs = NotificationPreferences(
                    user_id=user_id,
                    push_enabled=True,
                    email_enabled=True,
                    in_app_enabled=True
                )
                session.add(user_prefs)
            
            # Update preferences
            for key, value in preferences.items():
                if hasattr(user_prefs, key):
                    setattr(user_prefs, key, value)
            
            user_prefs.updated_at = datetime.utcnow()
            await session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update user preferences: {e}")
            return False
    
    async def cleanup_old_notifications(self, session: AsyncSession, days_to_keep: int = 30) -> int:
        """Clean up old notifications."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            result = await session.execute(
                delete(Notification).where(Notification.created_at < cutoff_date)
            )
            
            await session.commit()
            return result.rowcount
            
        except Exception as e:
            logger.error(f"Failed to cleanup old notifications: {e}")
            return 0
    
    async def schedule_notification(self, session: AsyncSession, user_id: str, template_key: str,
                                  send_at: datetime, variables: Dict[str, Any] = None) -> str:
        """Schedule notification for future delivery."""
        try:
            # Create scheduled notification record
            notification = Notification(
                user_id=user_id,
                title="",  # Will be populated when sent
                body="",
                notification_type=NotificationType.SCHEDULED,
                priority="medium",
                scheduled_for=send_at,
                template_key=template_key,
                template_variables=variables or {},
                created_at=datetime.utcnow()
            )
            session.add(notification)
            await session.commit()
            
            return notification.id
            
        except Exception as e:
            logger.error(f"Failed to schedule notification: {e}")
            return None
    
    async def process_scheduled_notifications(self, session: AsyncSession) -> Dict[str, Any]:
        """Process scheduled notifications that are due."""
        try:
            now = datetime.utcnow()
            
            # Get due notifications
            result = await session.execute(
                select(Notification).where(
                    and_(
                        Notification.scheduled_for <= now,
                        Notification.sent_at == None,
                        Notification.template_key != None
                    )
                )
            )
            due_notifications = result.scalars().all()
            
            processed = 0
            errors = []
            
            for notification in due_notifications:
                try:
                    # Send the notification
                    result = await self.send_notification(
                        session, 
                        notification.user_id,
                        notification.template_key,
                        notification.template_variables or {}
                    )
                    
                    # Mark as sent
                    notification.sent_at = datetime.utcnow()
                    processed += 1
                    
                except Exception as e:
                    errors.append(f"Notification {notification.id}: {str(e)}")
            
            await session.commit()
            
            return {
                "processed": processed,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to process scheduled notifications: {e}")
            return {"error": str(e)}
    
    async def _get_user_preferences(self, session: AsyncSession, user_id: str) -> Optional[NotificationPreferences]:
        """Get user notification preferences."""
        try:
            result = await session.execute(
                select(NotificationPreferences).where(NotificationPreferences.user_id == user_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return None
    
    def _should_send_notification(self, preferences: NotificationPreferences, notification_type: NotificationType) -> bool:
        """Check if notification should be sent based on user preferences."""
        # Check general preferences
        if not preferences.push_enabled and not preferences.email_enabled and not preferences.in_app_enabled:
            return False
        
        # Check specific type preferences
        type_mapping = {
            NotificationType.DAILY_BONUS: preferences.daily_reminders,
            NotificationType.QUEST_REMINDER: preferences.quest_reminders,
            NotificationType.ACHIEVEMENT: preferences.achievement_notifications,
            NotificationType.FRIEND_REQUEST: preferences.social_notifications,
            NotificationType.SOCIAL: preferences.social_notifications,
            NotificationType.GAME_RESULT: preferences.game_notifications,
            NotificationType.TRADE: preferences.trade_notifications
        }
        
        return type_mapping.get(notification_type, True)
    
    async def _check_rate_limit(self, session: AsyncSession, user_id: str, channel: str) -> bool:
        """Check if user has exceeded rate limit for channel."""
        try:
            if channel not in self.rate_limits:
                return True
            
            limits = self.rate_limits[channel]
            now = datetime.utcnow()
            
            # Check hourly limit
            hour_ago = now - timedelta(hours=1)
            hourly_result = await session.execute(
                select(func.count(Notification.id)).where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.created_at >= hour_ago,
                        Notification.channels_sent.contains([channel])
                    )
                )
            )
            hourly_count = hourly_result.scalar() or 0
            
            if hourly_count >= limits["max_per_hour"]:
                return False
            
            # Check daily limit
            day_ago = now - timedelta(days=1)
            daily_result = await session.execute(
                select(func.count(Notification.id)).where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.created_at >= day_ago,
                        Notification.channels_sent.contains([channel])
                    )
                )
            )
            daily_count = daily_result.scalar() or 0
            
            return daily_count < limits["max_per_day"]
            
        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            return True  # Allow on error
    
    async def _update_rate_limit(self, session: AsyncSession, user_id: str, channel: str):
        """Update rate limiting tracking."""
        # Rate limiting is tracked via notification records
        # No additional action needed
        pass
    
    def _format_template_string(self, template: str, variables: Dict[str, Any]) -> str:
        """Format template string with variables."""
        try:
            return template.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template
        except Exception as e:
            logger.error(f"Failed to format template: {e}")
            return template


# Global instance
notification_manager = NotificationManager()