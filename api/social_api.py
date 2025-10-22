"""
Social API

REST endpoints for friends, messaging, profiles, and activity feeds.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import User
from api.auth_api import require_authentication
from services.friends_service import FriendsService
from services.social_service import MessagingService, ActivityService, ProfileService


router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SendFriendRequestRequest(BaseModel):
    """Request to send a friend request."""
    username: str


class FriendRequestActionRequest(BaseModel):
    """Request to accept/reject a friend request."""
    request_id: int


class RemoveFriendRequest(BaseModel):
    """Request to remove a friend."""
    friend_id: str


class SendMessageRequest(BaseModel):
    """Request to send a message."""
    username: str
    message: str


class UpdateProfileRequest(BaseModel):
    """Request to update profile."""
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None


class UpdatePrivacyRequest(BaseModel):
    """Request to update privacy settings."""
    profile_public: Optional[bool] = None
    show_stats: Optional[bool] = None
    show_activity: Optional[bool] = None


# ============================================================================
# FRIENDS ENDPOINTS
# ============================================================================

@router.post("/friends/request")
async def send_friend_request(
    request: SendFriendRequestRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Send a friend request to another user."""
    try:
        result = await FriendsService.send_friend_request(
            current_user.id,
            request.username,
            db
        )
        return result
    except ValueError as e:
        return {"success": False, "message": str(e)}


@router.post("/friends/accept")
async def accept_friend_request(
    request: FriendRequestActionRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Accept a friend request."""
    try:
        result = await FriendsService.accept_friend_request(
            current_user.id,
            request.request_id,
            db
        )
        return result
    except ValueError as e:
        return {"success": False, "message": str(e)}


@router.post("/friends/reject")
async def reject_friend_request(
    request: FriendRequestActionRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Reject a friend request."""
    try:
        result = await FriendsService.reject_friend_request(
            current_user.id,
            request.request_id,
            db
        )
        return result
    except ValueError as e:
        return {"success": False, "message": str(e)}


@router.post("/friends/remove")
async def remove_friend(
    request: RemoveFriendRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Remove a friend."""
    try:
        result = await FriendsService.remove_friend(
            current_user.id,
            request.friend_id,
            db
        )
        return result
    except ValueError as e:
        return {"success": False, "message": str(e)}


@router.get("/friends")
async def get_friends(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Get list of friends."""
    friends = await FriendsService.get_friends(current_user.id, db)
    return {"success": True, "friends": friends}


@router.get("/friends/requests")
async def get_friend_requests(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Get pending friend requests."""
    requests = await FriendsService.get_friend_requests(current_user.id, db)
    return {"success": True, **requests}


@router.get("/friends/search")
async def search_users(
    query: str,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Search for users."""
    users = await FriendsService.search_users(query, current_user.id, db)
    return {"success": True, "users": users}


# ============================================================================
# MESSAGING ENDPOINTS
# ============================================================================

@router.post("/messages/send")
async def send_message(
    request: SendMessageRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Send a private message."""
    try:
        result = await MessagingService.send_message(
            current_user.id,
            request.username,
            request.message,
            db
        )
        return result
    except ValueError as e:
        return {"success": False, "message": str(e)}


@router.get("/messages/conversation/{user_id}")
async def get_conversation(
    user_id: str,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation with a user."""
    messages = await MessagingService.get_conversation(current_user.id, user_id, db)
    return {"success": True, "messages": messages}


@router.post("/messages/mark-read/{user_id}")
async def mark_messages_read(
    user_id: str,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Mark messages from a user as read."""
    result = await MessagingService.mark_messages_read(current_user.id, user_id, db)
    return result


@router.get("/messages/unread-count")
async def get_unread_count(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Get count of unread messages."""
    count = await MessagingService.get_unread_count(current_user.id, db)
    return {"success": True, "unread_count": count}


@router.get("/messages/recent")
async def get_recent_conversations(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Get recent conversations."""
    conversations = await MessagingService.get_recent_conversations(current_user.id, db)
    return {"success": True, "conversations": conversations}


# ============================================================================
# PROFILE ENDPOINTS
# ============================================================================

@router.get("/profile/{username}")
async def get_profile(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a user's public profile."""
    try:
        profile = await ProfileService.get_public_profile(username, db)
        return {"success": True, "profile": profile}
    except ValueError as e:
        return {"success": False, "message": str(e)}


@router.post("/profile/update")
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Update your profile."""
    result = await ProfileService.update_profile(
        current_user.id,
        bio=request.bio,
        avatar_url=request.avatar_url,
        location=request.location,
        website=request.website,
        db=db
    )
    return result


@router.post("/profile/privacy")
async def update_privacy(
    request: UpdatePrivacyRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Update privacy settings."""
    result = await ProfileService.update_privacy_settings(
        current_user.id,
        profile_public=request.profile_public,
        show_stats=request.show_stats,
        show_activity=request.show_activity,
        db=db
    )
    return result


# ============================================================================
# ACTIVITY FEED ENDPOINTS
# ============================================================================

@router.get("/activity/me")
async def get_my_activity(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Get your activity feed."""
    activities = await ActivityService.get_user_activity(current_user.id, db)
    return {"success": True, "activities": activities}


@router.get("/activity/friends")
async def get_friends_activity(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """Get friends' activity feed."""
    activities = await ActivityService.get_friends_activity(current_user.id, db)
    return {"success": True, "activities": activities}
