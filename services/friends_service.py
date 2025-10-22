"""
Friends Service

Handles friend requests, friendships, and friend management.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Friendship, FriendRequest, UserProfile


class FriendsService:
    """Service for managing friendships and friend requests."""

    @staticmethod
    async def send_friend_request(sender_id: str, receiver_username: str, db: AsyncSession) -> Dict[str, Any]:
        """Send a friend request to another user."""
        # Get receiver by username
        result = await db.execute(select(User).where(User.username == receiver_username))
        receiver = result.scalar_one_or_none()

        if not receiver:
            raise ValueError("User not found")

        if sender_id == receiver.id:
            raise ValueError("Cannot send friend request to yourself")

        # Check if already friends
        result = await db.execute(
            select(Friendship).where(
                and_(Friendship.user_id == sender_id, Friendship.friend_id == receiver.id)
            )
        )
        if result.scalar_one_or_none():
            raise ValueError("Already friends with this user")

        # Check if request already exists
        result = await db.execute(
            select(FriendRequest).where(
                and_(
                    FriendRequest.sender_id == sender_id,
                    FriendRequest.receiver_id == receiver.id,
                    FriendRequest.status == 'pending'
                )
            )
        )
        if result.scalar_one_or_none():
            raise ValueError("Friend request already sent")

        # Check if receiver already sent a request (auto-accept)
        result = await db.execute(
            select(FriendRequest).where(
                and_(
                    FriendRequest.sender_id == receiver.id,
                    FriendRequest.receiver_id == sender_id,
                    FriendRequest.status == 'pending'
                )
            )
        )
        existing_request = result.scalar_one_or_none()

        if existing_request:
            # Auto-accept if receiver already sent a request
            return await FriendsService.accept_friend_request(sender_id, existing_request.id, db)

        # Create friend request
        friend_request = FriendRequest(
            sender_id=sender_id,
            receiver_id=receiver.id,
            status='pending'
        )

        db.add(friend_request)
        await db.commit()
        await db.refresh(friend_request)

        return {
            "success": True,
            "message": f"Friend request sent to {receiver.username}",
            "request_id": friend_request.id
        }

    @staticmethod
    async def accept_friend_request(user_id: str, request_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Accept a friend request."""
        # Get request
        result = await db.execute(
            select(FriendRequest).where(FriendRequest.id == request_id)
        )
        friend_request = result.scalar_one_or_none()

        if not friend_request:
            raise ValueError("Friend request not found")

        if friend_request.receiver_id != user_id:
            raise ValueError("Not authorized to accept this request")

        if friend_request.status != 'pending':
            raise ValueError("Request already responded to")

        # Update request status
        friend_request.status = 'accepted'
        friend_request.responded_at = datetime.utcnow()

        # Create bidirectional friendship
        friendship1 = Friendship(
            user_id=friend_request.sender_id,
            friend_id=friend_request.receiver_id
        )
        friendship2 = Friendship(
            user_id=friend_request.receiver_id,
            friend_id=friend_request.sender_id
        )

        db.add(friendship1)
        db.add(friendship2)

        await db.commit()

        # Get sender username
        result = await db.execute(select(User).where(User.id == friend_request.sender_id))
        sender = result.scalar_one()

        return {
            "success": True,
            "message": f"You are now friends with {sender.username}",
            "friend_id": sender.id,
            "friend_username": sender.username
        }

    @staticmethod
    async def reject_friend_request(user_id: str, request_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Reject a friend request."""
        # Get request
        result = await db.execute(
            select(FriendRequest).where(FriendRequest.id == request_id)
        )
        friend_request = result.scalar_one_or_none()

        if not friend_request:
            raise ValueError("Friend request not found")

        if friend_request.receiver_id != user_id:
            raise ValueError("Not authorized to reject this request")

        if friend_request.status != 'pending':
            raise ValueError("Request already responded to")

        # Update request status
        friend_request.status = 'rejected'
        friend_request.responded_at = datetime.utcnow()

        await db.commit()

        return {
            "success": True,
            "message": "Friend request rejected"
        }

    @staticmethod
    async def remove_friend(user_id: str, friend_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Remove a friend (delete bidirectional friendship)."""
        # Delete both friendship records
        result = await db.execute(
            select(Friendship).where(
                or_(
                    and_(Friendship.user_id == user_id, Friendship.friend_id == friend_id),
                    and_(Friendship.user_id == friend_id, Friendship.friend_id == user_id)
                )
            )
        )
        friendships = result.scalars().all()

        if not friendships:
            raise ValueError("Not friends with this user")

        for friendship in friendships:
            await db.delete(friendship)

        await db.commit()

        return {
            "success": True,
            "message": "Friend removed"
        }

    @staticmethod
    async def get_friends(user_id: str, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get list of user's friends with their profiles."""
        # Get friendships
        result = await db.execute(
            select(Friendship, User, UserProfile)
            .join(User, User.id == Friendship.friend_id)
            .outerjoin(UserProfile, UserProfile.user_id == User.id)
            .where(Friendship.user_id == user_id)
            .order_by(User.username)
        )

        friends = []
        for friendship, user, profile in result.all():
            friends.append({
                "id": user.id,
                "username": user.username,
                "gem_balance": user.gem_balance,
                "is_online": profile.is_online if profile else False,
                "last_seen": profile.last_seen.isoformat() if profile and profile.last_seen else None,
                "avatar_url": profile.avatar_url if profile else None,
                "friends_since": friendship.created_at.isoformat()
            })

        return friends

    @staticmethod
    async def get_friend_requests(user_id: str, db: AsyncSession) -> Dict[str, List[Dict[str, Any]]]:
        """Get pending friend requests (sent and received)."""
        # Get received requests
        result = await db.execute(
            select(FriendRequest, User)
            .join(User, User.id == FriendRequest.sender_id)
            .where(
                and_(
                    FriendRequest.receiver_id == user_id,
                    FriendRequest.status == 'pending'
                )
            )
            .order_by(FriendRequest.created_at.desc())
        )

        received = []
        for request, sender in result.all():
            received.append({
                "id": request.id,
                "from_user_id": sender.id,
                "from_username": sender.username,
                "created_at": request.created_at.isoformat()
            })

        # Get sent requests
        result = await db.execute(
            select(FriendRequest, User)
            .join(User, User.id == FriendRequest.receiver_id)
            .where(
                and_(
                    FriendRequest.sender_id == user_id,
                    FriendRequest.status == 'pending'
                )
            )
            .order_by(FriendRequest.created_at.desc())
        )

        sent = []
        for request, receiver in result.all():
            sent.append({
                "id": request.id,
                "to_user_id": receiver.id,
                "to_username": receiver.username,
                "created_at": request.created_at.isoformat()
            })

        return {
            "received": received,
            "sent": sent
        }

    @staticmethod
    async def search_users(query: str, current_user_id: str, db: AsyncSession, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for users by username."""
        # Search users (exclude current user)
        result = await db.execute(
            select(User, UserProfile)
            .outerjoin(UserProfile, UserProfile.user_id == User.id)
            .where(
                and_(
                    User.username.ilike(f"%{query}%"),
                    User.id != current_user_id
                )
            )
            .limit(limit)
        )

        users = []
        for user, profile in result.all():
            # Check if already friends
            friend_check = await db.execute(
                select(Friendship).where(
                    and_(Friendship.user_id == current_user_id, Friendship.friend_id == user.id)
                )
            )
            is_friend = friend_check.scalar_one_or_none() is not None

            # Check if request pending
            request_check = await db.execute(
                select(FriendRequest).where(
                    or_(
                        and_(FriendRequest.sender_id == current_user_id, FriendRequest.receiver_id == user.id),
                        and_(FriendRequest.sender_id == user.id, FriendRequest.receiver_id == current_user_id)
                    ),
                    FriendRequest.status == 'pending'
                )
            )
            request_pending = request_check.scalar_one_or_none() is not None

            users.append({
                "id": user.id,
                "username": user.username,
                "gem_balance": user.gem_balance,
                "is_online": profile.is_online if profile else False,
                "avatar_url": profile.avatar_url if profile else None,
                "is_friend": is_friend,
                "request_pending": request_pending
            })

        return users
