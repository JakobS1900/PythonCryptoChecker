"""
Missions API endpoints for daily missions and weekly challenges.
Allows users to track progress and claim rewards.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import User
from api.auth_api import get_current_user, require_authentication
from services.mission_tracker import mission_tracker
from config.missions import (
    DAILY_MISSIONS,
    WEEKLY_CHALLENGES,
    get_total_daily_rewards,
    get_total_weekly_rewards,
    seconds_until_daily_reset,
    seconds_until_weekly_reset
)

router = APIRouter(prefix="/api/missions", tags=["missions"])

# ==================== REQUEST/RESPONSE MODELS ====================

class MissionProgressResponse(BaseModel):
    """Daily mission progress response."""
    id: str
    name: str
    description: str
    progress: int
    target: int
    status: str  # 'active', 'completed', 'claimed'
    reward: int
    completed_at: Optional[str] = None
    claimed_at: Optional[str] = None
    icon: str
    category: str

class ChallengeProgressResponse(BaseModel):
    """Weekly challenge progress response."""
    id: str
    name: str
    description: str
    progress: int
    target: int
    status: str  # 'active', 'completed', 'claimed'
    reward: int
    completed_at: Optional[str] = None
    claimed_at: Optional[str] = None
    icon: str
    difficulty: str

class DailyMissionsResponse(BaseModel):
    """Response for daily missions endpoint."""
    missions: List[MissionProgressResponse]
    total_rewards: int
    completed_count: int
    claimed_count: int
    seconds_until_reset: int

class WeeklyChallengesResponse(BaseModel):
    """Response for weekly challenges endpoint."""
    challenges: List[ChallengeProgressResponse]
    total_rewards: int
    completed_count: int
    claimed_count: int
    seconds_until_reset: int

class ClaimRewardResponse(BaseModel):
    """Response for claiming a reward."""
    success: bool
    mission_id: str
    reward_claimed: int
    new_balance: int
    message: str

class MissionsOverviewResponse(BaseModel):
    """Overview of all missions and challenges."""
    daily_missions: List[MissionProgressResponse]
    weekly_challenges: List[ChallengeProgressResponse]
    total_daily_rewards: int
    total_weekly_rewards: int
    daily_completed: int
    weekly_completed: int
    seconds_until_daily_reset: int
    seconds_until_weekly_reset: int

# ==================== API ENDPOINTS ====================

@router.get("/daily", response_model=DailyMissionsResponse)
async def get_daily_missions(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's daily missions with progress.
    Requires authentication.
    """
    try:
        # Get mission progress
        missions = await mission_tracker.get_daily_missions_progress(current_user.id, db)

        # Calculate stats
        completed_count = sum(1 for m in missions if m["status"] in ["completed", "claimed"])
        claimed_count = sum(1 for m in missions if m["status"] == "claimed")
        total_rewards = sum(m["reward"] for m in missions)

        # Format response
        missions_formatted = [
            MissionProgressResponse(**mission) for mission in missions
        ]

        return DailyMissionsResponse(
            missions=missions_formatted,
            total_rewards=total_rewards,
            completed_count=completed_count,
            claimed_count=claimed_count,
            seconds_until_reset=seconds_until_daily_reset()
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching daily missions: {str(e)}"
        )

@router.get("/weekly", response_model=WeeklyChallengesResponse)
async def get_weekly_challenges(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's weekly challenges with progress.
    Requires authentication.
    """
    try:
        # Get challenge progress
        challenges = await mission_tracker.get_weekly_challenges_progress(current_user.id, db)

        # Calculate stats
        completed_count = sum(1 for c in challenges if c["status"] in ["completed", "claimed"])
        claimed_count = sum(1 for c in challenges if c["status"] == "claimed")
        total_rewards = sum(c["reward"] for c in challenges)

        # Format response
        challenges_formatted = [
            ChallengeProgressResponse(**challenge) for challenge in challenges
        ]

        return WeeklyChallengesResponse(
            challenges=challenges_formatted,
            total_rewards=total_rewards,
            completed_count=completed_count,
            claimed_count=claimed_count,
            seconds_until_reset=seconds_until_weekly_reset()
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching weekly challenges: {str(e)}"
        )

@router.get("/overview", response_model=MissionsOverviewResponse)
async def get_missions_overview(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete overview of all missions and challenges.
    Useful for missions dashboard page.
    Requires authentication.
    """
    try:
        # Get both daily and weekly progress
        daily_missions = await mission_tracker.get_daily_missions_progress(current_user.id, db)
        weekly_challenges = await mission_tracker.get_weekly_challenges_progress(current_user.id, db)

        # Calculate stats
        daily_completed = sum(1 for m in daily_missions if m["status"] in ["completed", "claimed"])
        weekly_completed = sum(1 for c in weekly_challenges if c["status"] in ["completed", "claimed"])

        total_daily = sum(m["reward"] for m in daily_missions)
        total_weekly = sum(c["reward"] for c in weekly_challenges)

        return MissionsOverviewResponse(
            daily_missions=[MissionProgressResponse(**m) for m in daily_missions],
            weekly_challenges=[ChallengeProgressResponse(**c) for c in weekly_challenges],
            total_daily_rewards=total_daily,
            total_weekly_rewards=total_weekly,
            daily_completed=daily_completed,
            weekly_completed=weekly_completed,
            seconds_until_daily_reset=seconds_until_daily_reset(),
            seconds_until_weekly_reset=seconds_until_weekly_reset()
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching missions overview: {str(e)}"
        )

@router.post("/daily/{mission_id}/claim", response_model=ClaimRewardResponse)
async def claim_daily_mission_reward(
    mission_id: str,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Claim reward for a completed daily mission.
    Requires authentication.

    Args:
        mission_id: ID of the mission to claim

    Returns:
        Claim result with new balance

    Raises:
        400: Mission not found, not completed, or already claimed
        500: Server error
    """
    try:
        result = await mission_tracker.claim_mission_reward(current_user.id, mission_id, db)

        return ClaimRewardResponse(
            success=True,
            mission_id=result["mission_id"],
            reward_claimed=result["reward_claimed"],
            new_balance=result["new_balance"],
            message=f"Successfully claimed {result['reward_claimed']} GEM!"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error claiming mission reward: {str(e)}"
        )

@router.post("/weekly/{challenge_id}/claim", response_model=ClaimRewardResponse)
async def claim_weekly_challenge_reward(
    challenge_id: str,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Claim reward for a completed weekly challenge.
    Requires authentication.

    Args:
        challenge_id: ID of the challenge to claim

    Returns:
        Claim result with new balance

    Raises:
        400: Challenge not found, not completed, or already claimed
        500: Server error
    """
    try:
        result = await mission_tracker.claim_challenge_reward(current_user.id, challenge_id, db)

        return ClaimRewardResponse(
            success=True,
            mission_id=result["challenge_id"],
            reward_claimed=result["reward_claimed"],
            new_balance=result["new_balance"],
            message=f"Successfully claimed {result['reward_claimed']} GEM!"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error claiming challenge reward: {str(e)}"
        )

@router.get("/definitions")
async def get_mission_definitions():
    """
    Get all mission and challenge definitions.
    Public endpoint - no authentication required.
    Useful for documentation or UI reference.
    """
    return {
        "daily_missions": DAILY_MISSIONS,
        "weekly_challenges": WEEKLY_CHALLENGES,
        "stats": {
            "total_daily_missions": len(DAILY_MISSIONS),
            "total_weekly_challenges": len(WEEKLY_CHALLENGES),
            "max_daily_gems": get_total_daily_rewards(),
            "max_weekly_gems": get_total_weekly_rewards()
        }
    }

@router.get("/stats")
async def get_mission_stats(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's mission statistics.
    Requires authentication.

    Returns summary stats about user's mission completion.
    """
    try:
        daily_missions = await mission_tracker.get_daily_missions_progress(current_user.id, db)
        weekly_challenges = await mission_tracker.get_weekly_challenges_progress(current_user.id, db)

        # Calculate completion percentages
        daily_progress = sum(m["progress"] / m["target"] for m in daily_missions) / len(daily_missions) * 100 if daily_missions else 0
        weekly_progress = sum(c["progress"] / c["target"] for c in weekly_challenges) / len(weekly_challenges) * 100 if weekly_challenges else 0

        # Calculate potential earnings
        daily_potential = sum(m["reward"] for m in daily_missions if m["status"] == "completed")
        weekly_potential = sum(c["reward"] for c in weekly_challenges if c["status"] == "completed")

        return {
            "daily": {
                "total": len(daily_missions),
                "completed": sum(1 for m in daily_missions if m["status"] in ["completed", "claimed"]),
                "claimed": sum(1 for m in daily_missions if m["status"] == "claimed"),
                "progress_percent": round(daily_progress, 1),
                "gems_available": daily_potential
            },
            "weekly": {
                "total": len(weekly_challenges),
                "completed": sum(1 for c in weekly_challenges if c["status"] in ["completed", "claimed"]),
                "claimed": sum(1 for c in weekly_challenges if c["status"] == "claimed"),
                "progress_percent": round(weekly_progress, 1),
                "gems_available": weekly_potential
            },
            "total_gems_available": daily_potential + weekly_potential
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching mission stats: {str(e)}"
        )

# ==================== ADMIN ENDPOINTS (Future) ====================

# @router.post("/admin/reset-daily")
# async def admin_reset_daily_missions():
#     """Admin endpoint to manually trigger daily mission reset."""
#     pass

# @router.post("/admin/reset-weekly")
# async def admin_reset_weekly_challenges():
#     """Admin endpoint to manually trigger weekly challenge reset."""
#     pass
