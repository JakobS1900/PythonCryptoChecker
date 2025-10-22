"""
Leaderboard API

REST API endpoints for leaderboards across different categories.
"""

from fastapi import APIRouter, Depends, Query, Path
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import User
from api.auth_api import require_authentication
from services.leaderboard_service import LeaderboardService


router = APIRouter()


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class LeaderboardResponse(BaseModel):
    """Response model for leaderboard data."""
    category: str
    timeframe: str
    entries: list


class UserRankResponse(BaseModel):
    """Response model for user rank."""
    rank: Optional[int]
    score: Optional[int]
    stats: dict


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/wealth/{timeframe}", response_model=LeaderboardResponse)
async def get_wealth_leaderboard(
    timeframe: str = Path(..., regex="^(all_time|weekly|monthly)$"),
    limit: int = Query(100, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get wealth leaderboard (richest users).

    - **timeframe**: all_time, weekly, or monthly
    - **limit**: Number of entries (max 100)
    """
    entries = await LeaderboardService.get_leaderboard('wealth', timeframe, db, limit)

    return LeaderboardResponse(
        category='wealth',
        timeframe=timeframe,
        entries=entries
    )


@router.get("/minigames/{timeframe}", response_model=LeaderboardResponse)
async def get_minigames_leaderboard(
    timeframe: str = Path(..., regex="^(all_time|weekly|monthly)$"),
    limit: int = Query(100, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get mini-games leaderboard (highest profit).

    - **timeframe**: all_time, weekly, or monthly
    - **limit**: Number of entries (max 100)
    """
    entries = await LeaderboardService.get_leaderboard('minigames', timeframe, db, limit)

    return LeaderboardResponse(
        category='minigames',
        timeframe=timeframe,
        entries=entries
    )


@router.get("/trading/{timeframe}", response_model=LeaderboardResponse)
async def get_trading_leaderboard(
    timeframe: str = Path(..., regex="^(all_time|weekly|monthly)$"),
    limit: int = Query(100, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get trading leaderboard (highest volume).

    - **timeframe**: all_time, weekly, or monthly
    - **limit**: Number of entries (max 100)
    """
    entries = await LeaderboardService.get_leaderboard('trading', timeframe, db, limit)

    return LeaderboardResponse(
        category='trading',
        timeframe=timeframe,
        entries=entries
    )


@router.get("/roulette/{timeframe}", response_model=LeaderboardResponse)
async def get_roulette_leaderboard(
    timeframe: str = Path(..., regex="^(all_time|weekly|monthly)$"),
    limit: int = Query(100, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get roulette leaderboard (highest wagered).

    - **timeframe**: all_time, weekly, or monthly
    - **limit**: Number of entries (max 100)
    """
    entries = await LeaderboardService.get_leaderboard('roulette', timeframe, db, limit)

    return LeaderboardResponse(
        category='roulette',
        timeframe=timeframe,
        entries=entries
    )


@router.get("/my-rank/{category}/{timeframe}", response_model=UserRankResponse)
async def get_my_rank(
    category: str = Path(..., regex="^(wealth|minigames|trading|roulette)$"),
    timeframe: str = Path(..., regex="^(all_time|weekly|monthly)$"),
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's rank in a leaderboard.

    - **category**: wealth, minigames, trading, or roulette
    - **timeframe**: all_time, weekly, or monthly
    """
    rank_data = await LeaderboardService.get_user_rank(
        current_user.id,
        category,
        timeframe,
        db
    )

    if rank_data:
        return UserRankResponse(
            rank=rank_data['rank'],
            score=rank_data['score'],
            stats=rank_data['stats']
        )
    else:
        return UserRankResponse(
            rank=None,
            score=None,
            stats={}
        )


@router.post("/update")
async def update_leaderboards(db: AsyncSession = Depends(get_db)):
    """
    Manually trigger leaderboard updates (admin endpoint).

    Should be called periodically (e.g., every hour) via cron job.
    """
    await LeaderboardService.update_all_leaderboards(db)

    return {"message": "Leaderboards updated successfully"}
