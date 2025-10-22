"""
Challenge API

REST API endpoints for daily challenges and login streaks.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import User
from api.auth_api import require_authentication
from services.challenge_service import ChallengeService


router = APIRouter()


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class LoginBonusResponse(BaseModel):
    """Response model for daily login."""
    already_claimed: bool
    streak_broken: bool
    current_streak: int
    longest_streak: int
    bonus_gem: int
    total_logins: int


class ChallengeListResponse(BaseModel):
    """Response model for challenge list."""
    challenges: list


class ClaimRewardResponse(BaseModel):
    """Response model for claiming reward."""
    success: bool
    message: str
    challenge_title: str
    reward: int
    new_balance: int


class LoginStreakResponse(BaseModel):
    """Response model for login streak info."""
    current_streak: int
    longest_streak: int
    total_logins: int
    last_login: str = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/daily-login", response_model=LoginBonusResponse)
async def claim_daily_login(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Claim daily login bonus.

    Rewards increase with consecutive login streaks.
    """
    try:
        result = await ChallengeService.process_daily_login(current_user.id, db)

        return LoginBonusResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing login: {str(e)}")


@router.get("/active", response_model=ChallengeListResponse)
async def get_active_challenges(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all active daily challenges with user progress.
    """
    try:
        challenges = await ChallengeService.get_active_challenges(current_user.id, db)

        return ChallengeListResponse(challenges=challenges)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching challenges: {str(e)}")


@router.post("/claim/{challenge_id}", response_model=ClaimRewardResponse)
async def claim_challenge_reward(
    challenge_id: int,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Claim reward for completed challenge.

    - **challenge_id**: ID of the challenge to claim
    """
    try:
        result = await ChallengeService.claim_challenge_reward(
            current_user.id,
            challenge_id,
            db
        )

        return ClaimRewardResponse(
            success=True,
            message=f"Claimed {result['reward']} GEM!",
            challenge_title=result['challenge_title'],
            reward=result['reward'],
            new_balance=result['new_balance']
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error claiming reward: {str(e)}")


@router.get("/login-streak", response_model=LoginStreakResponse)
async def get_login_streak(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's login streak information.
    """
    try:
        streak_data = await ChallengeService.get_user_login_streak(current_user.id, db)

        return LoginStreakResponse(**streak_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching streak: {str(e)}")


@router.post("/create-daily")
async def create_daily_challenges(db: AsyncSession = Depends(get_db)):
    """
    Create daily challenges (admin endpoint).

    Should be called once per day via cron job.
    """
    try:
        await ChallengeService.create_daily_challenges(db)

        return {"message": "Daily challenges created successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating challenges: {str(e)}")
