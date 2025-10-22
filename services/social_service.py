"""
Social Service

Handles messaging, activity feeds, and user profiles.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    User, PrivateMessage, ActivityFeed, UserProfile, Friendship
)


class MessagingService:
    """Service for private messaging."""

    @staticmethod
    async def send_message(
        sender_id: str,
        receiver_username: str,
        message: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Send a private message to another user."""
        # Get receiver
        result = await db.execute(select(User).where(User.username == receiver_username))
        receiver = result.scalar_one_or_none()

        if not receiver:
            raise ValueError("User not found")

        if sender_id == receiver.id:
            raise ValueError("Cannot send message to yourself")

        # Check if friends (optional - you can remove this to allow messaging anyone)
        result = await db.execute(
            select(Friendship).where(
                and_(Friendship.user_id == sender_id, Friendship.friend_id == receiver.id)
            )
        )
        if not result.scalar_one_or_none():
            raise ValueError("Can only message friends")

        # Create message
        private_message = PrivateMessage(
            sender_id=sender_id,
            receiver_id=receiver.id,
            message=message,
            read=False
        )

        db.add(private_message)
        await db.commit()
        await db.refresh(private_message)

        return {
            "success": True,
            "message_id": private_message.id,
            "sent_to": receiver.username,
            "created_at": private_message.created_at.isoformat()
        }

    @staticmethod
    async def get_conversation(
        user_id: str,
        other_user_id: str,
        db: AsyncSession,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation between two users."""
        # Get messages
        result = await db.execute(
            select(PrivateMessage)
            .where(
                or_(
                    and_(PrivateMessage.sender_id == user_id, PrivateMessage.receiver_id == other_user_id),
                    and_(PrivateMessage.sender_id == other_user_id, PrivateMessage.receiver_id == user_id)
                )
            )
            .order_by(PrivateMessage.created_at.desc())
            .limit(limit)
        )

        messages = []
        for msg in result.scalars().all():
            messages.append({
                "id": msg.id,
                "sender_id": msg.sender_id,
                "receiver_id": msg.receiver_id,
                "message": msg.message,
                "read": msg.read,
                "created_at": msg.created_at.isoformat(),
                "is_mine": msg.sender_id == user_id
            })

        # Reverse to show oldest first
        messages.reverse()

        return messages

    @staticmethod
    async def mark_messages_read(user_id: str, other_user_id: str, db: AsyncSession):
        """Mark all messages from another user as read."""
        result = await db.execute(
            select(PrivateMessage).where(
                and_(
                    PrivateMessage.sender_id == other_user_id,
                    PrivateMessage.receiver_id == user_id,
                    PrivateMessage.read == False
                )
            )
        )

        messages = result.scalars().all()
        for msg in messages:
            msg.read = True
            msg.read_at = datetime.utcnow()

        await db.commit()

        return {"success": True, "marked_read": len(messages)}

    @staticmethod
    async def get_unread_count(user_id: str, db: AsyncSession) -> int:
        """Get count of unread messages."""
        result = await db.execute(
            select(PrivateMessage).where(
                and_(
                    PrivateMessage.receiver_id == user_id,
                    PrivateMessage.read == False
                )
            )
        )
        return len(result.scalars().all())

    @staticmethod
    async def get_recent_conversations(user_id: str, db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of recent conversations with message previews."""
        # Get all messages involving the user
        result = await db.execute(
            select(PrivateMessage, User)
            .join(
                User,
                or_(
                    and_(PrivateMessage.sender_id == user_id, User.id == PrivateMessage.receiver_id),
                    and_(PrivateMessage.receiver_id == user_id, User.id == PrivateMessage.sender_id)
                )
            )
            .order_by(PrivateMessage.created_at.desc())
        )

        # Group by conversation partner
        conversations = {}
        for msg, other_user in result.all():
            other_user_id = other_user.id
            if other_user_id not in conversations:
                conversations[other_user_id] = {
                    "user_id": other_user.id,
                    "username": other_user.username,
                    "last_message": msg.message,
                    "last_message_at": msg.created_at.isoformat(),
                    "unread_count": 0
                }

            # Count unread
            if msg.receiver_id == user_id and not msg.read:
                conversations[other_user_id]["unread_count"] += 1

        return list(conversations.values())[:limit]


class ActivityService:
    """Service for activity feed management."""

    @staticmethod
    async def create_activity(
        user_id: str,
        activity_type: str,
        title: str,
        description: Optional[str] = None,
        data: Optional[Dict] = None,
        is_public: bool = True,
        db: AsyncSession = None
    ):
        """Create an activity feed event."""
        activity = ActivityFeed(
            user_id=user_id,
            activity_type=activity_type,
            title=title,
            description=description,
            data=json.dumps(data) if data else None,
            is_public=is_public
        )

        db.add(activity)
        await db.commit()

    @staticmethod
    async def get_user_activity(user_id: str, db: AsyncSession, limit: int = 20) -> List[Dict[str, Any]]:
        """Get a user's activity feed."""
        result = await db.execute(
            select(ActivityFeed)
            .where(ActivityFeed.user_id == user_id)
            .order_by(ActivityFeed.created_at.desc())
            .limit(limit)
        )

        activities = []
        for activity in result.scalars().all():
            activities.append({
                "id": activity.id,
                "activity_type": activity.activity_type,
                "title": activity.title,
                "description": activity.description,
                "data": json.loads(activity.data) if activity.data else None,
                "is_public": activity.is_public,
                "created_at": activity.created_at.isoformat()
            })

        return activities

    @staticmethod
    async def get_friends_activity(user_id: str, db: AsyncSession, limit: int = 50) -> List[Dict[str, Any]]:
        """Get activity feed of user's friends."""
        # Get friend IDs
        result = await db.execute(
            select(Friendship.friend_id).where(Friendship.user_id == user_id)
        )
        friend_ids = [row[0] for row in result.all()]

        if not friend_ids:
            return []

        # Get public activities from friends
        result = await db.execute(
            select(ActivityFeed, User)
            .join(User, User.id == ActivityFeed.user_id)
            .where(
                and_(
                    ActivityFeed.user_id.in_(friend_ids),
                    ActivityFeed.is_public == True
                )
            )
            .order_by(ActivityFeed.created_at.desc())
            .limit(limit)
        )

        activities = []
        for activity, user in result.all():
            activities.append({
                "id": activity.id,
                "user_id": user.id,
                "username": user.username,
                "activity_type": activity.activity_type,
                "title": activity.title,
                "description": activity.description,
                "data": json.loads(activity.data) if activity.data else None,
                "created_at": activity.created_at.isoformat()
            })

        return activities


class ProfileService:
    """Service for user profile management."""

    @staticmethod
    async def get_or_create_profile(user_id: str, db: AsyncSession) -> UserProfile:
        """Get user profile or create if doesn't exist."""
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            profile = UserProfile(user_id=user_id)
            db.add(profile)
            await db.commit()
            await db.refresh(profile)

        return profile

    @staticmethod
    async def update_profile(
        user_id: str,
        bio: Optional[str] = None,
        avatar_url: Optional[str] = None,
        location: Optional[str] = None,
        website: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """Update user profile."""
        profile = await ProfileService.get_or_create_profile(user_id, db)

        if bio is not None:
            profile.bio = bio
        if avatar_url is not None:
            profile.avatar_url = avatar_url
        if location is not None:
            profile.location = location
        if website is not None:
            profile.website = website

        profile.updated_at = datetime.utcnow()

        await db.commit()

        return {
            "success": True,
            "message": "Profile updated"
        }

    @staticmethod
    async def update_privacy_settings(
        user_id: str,
        profile_public: Optional[bool] = None,
        show_stats: Optional[bool] = None,
        show_activity: Optional[bool] = None,
        db: AsyncSession = None
    ):
        """Update privacy settings."""
        profile = await ProfileService.get_or_create_profile(user_id, db)

        if profile_public is not None:
            profile.profile_public = profile_public
        if show_stats is not None:
            profile.show_stats = show_stats
        if show_activity is not None:
            profile.show_activity = show_activity

        await db.commit()

        return {"success": True}

    @staticmethod
    async def update_online_status(user_id: str, is_online: bool, db: AsyncSession):
        """Update user online status."""
        profile = await ProfileService.get_or_create_profile(user_id, db)

        profile.is_online = is_online
        if not is_online:
            profile.last_seen = datetime.utcnow()

        await db.commit()

    @staticmethod
    async def get_public_profile(username: str, db: AsyncSession) -> Dict[str, Any]:
        """Get a user's public profile."""
        # Get user
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        # Get profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
        profile = result.scalar_one_or_none()

        # Check privacy
        if profile and not profile.profile_public:
            raise ValueError("Profile is private")

        return {
            "id": user.id,
            "username": user.username,
            "gem_balance": user.gem_balance if (not profile or profile.show_stats) else None,
            "bio": profile.bio if profile else None,
            "avatar_url": profile.avatar_url if profile else None,
            "location": profile.location if profile else None,
            "website": profile.website if profile else None,
            "is_online": profile.is_online if profile else False,
            "last_seen": profile.last_seen.isoformat() if profile and profile.last_seen else None,
            "show_stats": profile.show_stats if profile else True,
            "show_activity": profile.show_activity if profile else True,
            "created_at": user.created_at.isoformat()
        }
