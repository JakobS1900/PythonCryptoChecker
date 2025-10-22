"""
GEM Staking API Endpoints

Provides REST API for staking operations including creating stakes,
claiming rewards, unstaking, and viewing statistics.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from database.database import get_db
from database.models import User
from auth.dependencies import require_authentication
from services.staking_service import StakingService
from config.staking_plans import get_all_plans, get_plan

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================

class StakePlanInfo(BaseModel):
    """Staking plan information."""
    id: str
    name: str
    lock_period_days: int
    apr_rate: float
    min_stake: int
    max_stake: Optional[int]
    description: str
    badge: str
    color: str
    icon: str
    popular: bool
    best_value: bool

    class Config:
        from_attributes = True


class CreateStakeRequest(BaseModel):
    """Request to create a new stake."""
    plan_id: str = Field(..., description="Staking plan ID")
    amount: int = Field(..., gt=0, description="Amount of GEM to stake")


class CreateStakeResponse(BaseModel):
    """Response after creating a stake."""
    success: bool
    message: str
    stake_id: Optional[int] = None
    amount: int
    lock_period_days: int
    apr_rate: float
    unlock_at: Optional[datetime] = None
    estimated_daily_reward: int


class StakeInfo(BaseModel):
    """Information about a stake."""
    id: int
    amount: int
    lock_period_days: int
    apr_rate: float
    total_rewards_earned: int
    unclaimed_rewards: int
    status: str
    staked_at: datetime
    unlock_at: datetime
    unstaked_at: Optional[datetime]
    can_unstake: bool
    days_remaining: int


class ClaimRewardsResponse(BaseModel):
    """Response after claiming rewards."""
    success: bool
    message: str
    rewards_claimed: int
    new_balance: int


class UnstakeResponse(BaseModel):
    """Response after unstaking."""
    success: bool
    message: str
    principal_returned: int
    final_rewards: int
    total_returned: int
    new_balance: int


class StakingStatsResponse(BaseModel):
    """User's staking statistics."""
    active_stakes_count: int
    total_staked_amount: int
    total_unclaimed_rewards: int
    total_rewards_earned_all_time: int
    completed_stakes_count: int


# ============================================================
# API ENDPOINTS
# ============================================================

@router.get("/plans", response_model=List[StakePlanInfo])
async def get_staking_plans():
    """
    Get all available staking plans.

    Public endpoint - no authentication required.
    """
    try:
        plans = get_all_plans()
        return [StakePlanInfo(**plan) for plan in plans]
    except Exception as e:
        logger.error(f"Error fetching staking plans: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching plans: {str(e)}")


@router.post("/stake", response_model=CreateStakeResponse)
async def create_stake(
    request: CreateStakeRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new stake.

    Requires authentication.
    """
    try:
        success, message, stake = await StakingService.create_stake(
            user_id=current_user.id,
            plan_id=request.plan_id,
            amount=request.amount,
            db=db
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        # Get plan for additional info
        plan = get_plan(request.plan_id)

        from config.staking_plans import calculate_daily_reward
        estimated_daily_reward = calculate_daily_reward(request.amount, plan['apr_rate'])

        return CreateStakeResponse(
            success=True,
            message=message,
            stake_id=stake.id,
            amount=stake.amount,
            lock_period_days=stake.lock_period_days,
            apr_rate=stake.apr_rate,
            unlock_at=stake.unlock_at,
            estimated_daily_reward=estimated_daily_reward
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating stake: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating stake: {str(e)}")


@router.get("/my-stakes", response_model=List[StakeInfo])
async def get_my_stakes(
    status: Optional[str] = None,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's stakes.

    Query params:
    - status: Filter by status ('active', 'completed', 'cancelled')
    """
    try:
        stakes = await StakingService.get_user_stakes(
            user_id=current_user.id,
            db=db,
            status=status
        )

        # Update rewards for all active stakes
        for stake in stakes:
            if stake.status == 'active':
                await StakingService.update_stake_rewards(stake, db)

        now = datetime.utcnow()
        stake_list = []

        for stake in stakes:
            # Calculate if can unstake
            can_unstake = stake.status == 'active' and (
                stake.lock_period_days == 0 or now >= stake.unlock_at
            )

            # Calculate days remaining
            days_remaining = 0
            if stake.status == 'active' and stake.lock_period_days > 0:
                time_remaining = stake.unlock_at - now
                days_remaining = max(0, time_remaining.days)

            stake_list.append(StakeInfo(
                id=stake.id,
                amount=stake.amount,
                lock_period_days=stake.lock_period_days,
                apr_rate=stake.apr_rate,
                total_rewards_earned=stake.total_rewards_earned,
                unclaimed_rewards=stake.unclaimed_rewards,
                status=stake.status,
                staked_at=stake.staked_at,
                unlock_at=stake.unlock_at,
                unstaked_at=stake.unstaked_at,
                can_unstake=can_unstake,
                days_remaining=days_remaining
            ))

        return stake_list

    except Exception as e:
        logger.error(f"Error fetching user stakes: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching stakes: {str(e)}")


@router.post("/claim-rewards/{stake_id}", response_model=ClaimRewardsResponse)
async def claim_stake_rewards(
    stake_id: int,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Claim accumulated rewards from a stake.

    Requires authentication.
    """
    try:
        success, message, rewards_claimed = await StakingService.claim_rewards(
            stake_id=stake_id,
            user_id=current_user.id,
            db=db
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        # Get updated wallet balance
        from sqlalchemy import select
        from database.models import Wallet
        wallet_result = await db.execute(
            select(Wallet).where(Wallet.user_id == current_user.id)
        )
        wallet = wallet_result.scalar_one_or_none()
        new_balance = wallet.gem_balance if wallet else 0

        return ClaimRewardsResponse(
            success=True,
            message=message,
            rewards_claimed=rewards_claimed,
            new_balance=new_balance
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error claiming rewards: {e}")
        raise HTTPException(status_code=500, detail=f"Error claiming rewards: {str(e)}")


@router.post("/unstake/{stake_id}", response_model=UnstakeResponse)
async def unstake_gems(
    stake_id: int,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Unstake GEM and return principal + rewards.

    Requires authentication.
    """
    try:
        # Get stake first to know principal amount
        from sqlalchemy import select
        from database.models import GemStake
        stake_result = await db.execute(
            select(GemStake).where(
                GemStake.id == stake_id,
                GemStake.user_id == current_user.id
            )
        )
        stake = stake_result.scalar_one_or_none()

        if not stake:
            raise HTTPException(status_code=404, detail="Stake not found")

        principal = stake.amount

        success, message, total_returned = await StakingService.unstake(
            stake_id=stake_id,
            user_id=current_user.id,
            db=db
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        final_rewards = total_returned - principal

        # Get updated wallet balance
        from database.models import Wallet
        wallet_result = await db.execute(
            select(Wallet).where(Wallet.user_id == current_user.id)
        )
        wallet = wallet_result.scalar_one_or_none()
        new_balance = wallet.gem_balance if wallet else 0

        return UnstakeResponse(
            success=True,
            message=message,
            principal_returned=principal,
            final_rewards=final_rewards,
            total_returned=total_returned,
            new_balance=new_balance
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unstaking: {e}")
        raise HTTPException(status_code=500, detail=f"Error unstaking: {str(e)}")


@router.get("/stats", response_model=StakingStatsResponse)
async def get_staking_stats(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's staking statistics.

    Requires authentication.
    """
    try:
        stats = await StakingService.get_user_staking_stats(
            user_id=current_user.id,
            db=db
        )

        return StakingStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error fetching staking stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")
