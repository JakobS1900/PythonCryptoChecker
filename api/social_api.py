"""
Social features API endpoints for friends, leaderboards, and community.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from database.database_manager import get_db_session
from social.social_manager import social_manager
from auth.auth_manager import AuthenticationManager
from logger import logger

router = APIRouter()
security = HTTPBearer()
auth_manager = AuthenticationManager()


# ==================== REQUEST/RESPONSE MODELS ====================

class SendFriendRequestModel(BaseModel):
    username: str = Field(..., description="Username to send friend request to")


class FriendRequestResponseModel(BaseModel):
    request_id: str = Field(..., description="Friend request ID")
    action: str = Field(..., pattern="^(ACCEPT|DECLINE)$", description="Action to take")


class SendGiftRequest(BaseModel):
    friend_id: str = Field(..., description="Friend user ID")
    currency_type: str = Field(..., pattern="^(GEM_COINS|VIRTUAL_CRYPTO)$")
    amount: float = Field(..., gt=0, description="Amount to gift")
    message: Optional[str] = Field(None, max_length=200, description="Optional message")


class UpdateStatusRequest(BaseModel):
    status: str = Field(..., max_length=100, description="New status message")
    mood: Optional[str] = Field(None, pattern="^(HAPPY|SAD|EXCITED|FOCUSED|RELAXED)$")


class FriendResponse(BaseModel):
    id: str
    username: str
    display_name: str
    avatar_url: Optional[str]
    status: str
    is_online: bool
    friendship_since: str
    last_active: Optional[str]


class FriendRequestResponse(BaseModel):
    id: str
    from_user: Dict[str, Any]
    to_user: Dict[str, Any]
    status: str
    created_at: str
    updated_at: Optional[str]


class LeaderboardResponse(BaseModel):
    rank: int
    user: Dict[str, Any]
    score: float
    change_from_yesterday: Optional[int]


class ActivityResponse(BaseModel):
    id: str
    user: Dict[str, Any]
    activity_type: str
    content: Dict[str, Any]
    timestamp: str


# ==================== HELPER FUNCTIONS ====================

async def get_current_user_id(
    token: str = Depends(security),
    session: AsyncSession = Depends(get_db_session)
) -> str:
    """Get current authenticated user ID."""
    user = await auth_manager.get_user_by_token(session, token.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return user.id


# ==================== FRIEND MANAGEMENT ENDPOINTS ====================

@router.get("/friends", response_model=List[FriendResponse])
async def get_friends(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get user's friends list."""
    try:
        friends = await social_manager.get_user_friends(session, user_id)
        
        return [
            FriendResponse(
                id=friend.id,
                username=friend.username,
                display_name=friend.display_name or friend.username,
                avatar_url=friend.avatar_url,
                status=friend.status_message or "No status set",
                is_online=friend.is_online,
                friendship_since=friend.friendship_date.isoformat(),
                last_active=friend.last_activity.isoformat() if friend.last_activity else None
            )
            for friend in friends
        ]
        
    except Exception as e:
        logger.error(f"Failed to get friends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get friends"
        )


@router.post("/friends/request")
async def send_friend_request(
    request: SendFriendRequestModel,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Send friend request."""
    try:
        success = await social_manager.send_friend_request(
            session=session,
            from_user_id=user_id,
            to_username=request.username
        )
        
        if success:
            return {"message": f"Friend request sent to {request.username}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to send friend request"
            )
            
    except Exception as e:
        logger.error(f"Failed to send friend request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/friends/requests", response_model=List[FriendRequestResponse])
async def get_friend_requests(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get pending friend requests."""
    try:
        requests = await social_manager.get_pending_friend_requests(session, user_id)
        
        return [
            FriendRequestResponse(
                id=req.id,
                from_user={
                    "id": req.from_user.id,
                    "username": req.from_user.username,
                    "display_name": req.from_user.display_name or req.from_user.username,
                    "avatar_url": req.from_user.avatar_url
                },
                to_user={
                    "id": req.to_user.id,
                    "username": req.to_user.username,
                    "display_name": req.to_user.display_name or req.to_user.username,
                    "avatar_url": req.to_user.avatar_url
                },
                status=req.status,
                created_at=req.created_at.isoformat(),
                updated_at=req.updated_at.isoformat() if req.updated_at else None
            )
            for req in requests
        ]
        
    except Exception as e:
        logger.error(f"Failed to get friend requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get friend requests"
        )


@router.post("/friends/requests/{request_id}")
async def respond_friend_request(
    request_id: str,
    response: FriendRequestResponseModel,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Accept or decline friend request."""
    try:
        if response.action == "ACCEPT":
            success = await social_manager.accept_friend_request(
                session=session,
                request_id=request_id,
                user_id=user_id
            )
            message = "Friend request accepted"
        else:
            success = await social_manager.decline_friend_request(
                session=session,
                request_id=request_id,
                user_id=user_id
            )
            message = "Friend request declined"
        
        if success:
            return {"message": message}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to process friend request"
            )
            
    except Exception as e:
        logger.error(f"Failed to respond to friend request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/friends/{friend_id}")
async def remove_friend(
    friend_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Remove friend."""
    try:
        success = await social_manager.remove_friend(session, user_id, friend_id)
        
        if success:
            return {"message": "Friend removed successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to remove friend"
            )
            
    except Exception as e:
        logger.error(f"Failed to remove friend: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== LEADERBOARDS ====================

@router.get("/leaderboards/{leaderboard_type}", response_model=List[LeaderboardResponse])
async def get_leaderboard(
    leaderboard_type: str,
    limit: int = 50,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get leaderboard rankings."""
    try:
        # Validate leaderboard type
        valid_types = ["level", "experience", "games_won", "total_winnings", "win_streak"]
        if leaderboard_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid leaderboard type. Must be one of: {', '.join(valid_types)}"
            )
        
        rankings = await social_manager.get_leaderboard_rankings(
            session=session,
            leaderboard_type=leaderboard_type,
            limit=limit
        )
        
        return [
            LeaderboardResponse(
                rank=idx + 1,
                user={
                    "id": user_data.id,
                    "username": user_data.username,
                    "display_name": user_data.display_name or user_data.username,
                    "avatar_url": user_data.avatar_url,
                    "current_level": user_data.current_level,
                    "prestige_level": user_data.prestige_level
                },
                score=score,
                change_from_yesterday=None  # Would implement with daily tracking
            )
            for idx, (user_data, score) in enumerate(rankings)
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get leaderboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get leaderboard"
        )


@router.get("/leaderboards/{leaderboard_type}/my-rank")
async def get_my_leaderboard_rank(
    leaderboard_type: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get current user's rank on leaderboard."""
    try:
        rank = await social_manager.get_user_leaderboard_rank(
            session=session,
            user_id=user_id,
            leaderboard_type=leaderboard_type
        )
        
        return {
            "rank": rank,
            "leaderboard_type": leaderboard_type,
            "total_users": await social_manager.get_total_users_count(session)
        }
        
    except Exception as e:
        logger.error(f"Failed to get user rank: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user rank"
        )


# ==================== GIFTING SYSTEM ====================

@router.post("/gifts/send")
async def send_gift(
    request: SendGiftRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Send gift to friend."""
    try:
        success = await social_manager.send_gift_to_friend(
            session=session,
            from_user_id=user_id,
            to_user_id=request.friend_id,
            currency_type=request.currency_type,
            amount=request.amount,
            message=request.message
        )
        
        if success:
            return {"message": "Gift sent successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to send gift"
            )
            
    except Exception as e:
        logger.error(f"Failed to send gift: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/gifts/received")
async def get_received_gifts(
    limit: int = 20,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get gifts received from friends."""
    try:
        gifts = await social_manager.get_user_received_gifts(
            session=session,
            user_id=user_id,
            limit=limit
        )
        
        return {"gifts": gifts}
        
    except Exception as e:
        logger.error(f"Failed to get received gifts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get gifts"
        )


# ==================== ACTIVITY FEED ====================

@router.get("/activity", response_model=List[ActivityResponse])
async def get_activity_feed(
    limit: int = 50,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get social activity feed."""
    try:
        activities = await social_manager.get_user_activity_feed(
            session=session,
            user_id=user_id,
            limit=limit
        )
        
        return [
            ActivityResponse(
                id=activity.id,
                user={
                    "id": activity.user.id,
                    "username": activity.user.username,
                    "display_name": activity.user.display_name or activity.user.username,
                    "avatar_url": activity.user.avatar_url
                },
                activity_type=activity.activity_type,
                content=activity.content,
                timestamp=activity.created_at.isoformat()
            )
            for activity in activities
        ]
        
    except Exception as e:
        logger.error(f"Failed to get activity feed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get activity feed"
        )


# ==================== USER STATUS ====================

@router.put("/status")
async def update_user_status(
    request: UpdateStatusRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Update user status and mood."""
    try:
        success = await social_manager.update_user_status(
            session=session,
            user_id=user_id,
            status=request.status,
            mood=request.mood
        )
        
        if success:
            return {"message": "Status updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update status"
            )
            
    except Exception as e:
        logger.error(f"Failed to update status: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/online-friends")
async def get_online_friends(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get currently online friends."""
    try:
        online_friends = await social_manager.get_online_friends(session, user_id)
        
        return {
            "online_friends": [
                {
                    "id": friend.id,
                    "username": friend.username,
                    "display_name": friend.display_name or friend.username,
                    "avatar_url": friend.avatar_url,
                    "status": friend.status_message,
                    "mood": friend.current_mood
                }
                for friend in online_friends
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get online friends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get online friends"
        )


# ==================== SOCIAL STATS ====================

@router.get("/stats")
async def get_social_stats(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get user's social statistics."""
    try:
        stats = await social_manager.get_user_social_stats(session, user_id)
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get social stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get social stats"
        )