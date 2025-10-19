"""
Achievements API endpoints for CryptoChecker GEM Marketplace.

Handles achievement retrieval, claiming rewards, and statistics.
Updated: Fixed Optional[User] type hints for proper guest mode support.
"""


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from database.database import get_db
from database.models import User
from api.auth_api import require_authentication, get_current_user
from services.achievement_tracker import achievement_tracker
from config.achievements import ACHIEVEMENT_STATS, get_achievements_by_category


router = APIRouter()


# ==================== REQUEST/RESPONSE MODELS ====================

class AchievementResponse(BaseModel):
    """Single achievement data."""
    id: str
    name: str
    description: str
    reward: float
    category: str
    rarity: str
    icon: str
    target: float
    is_unlocked: bool
    unlock_id: Optional[str]
    unlocked_at: Optional[str]
    progress_value: Optional[float]
    reward_claimed: bool
    reward_claimed_at: Optional[str]


class AchievementsStatsResponse(BaseModel):
    """Achievement statistics."""
    total_achievements: int
    total_unlocked: int
    total_claimed: int
    unclaimed_rewards: float
    completion_percentage: float


class AchievementsListResponse(BaseModel):
    """List of achievements with stats."""
    achievements: List[AchievementResponse]
    stats: AchievementsStatsResponse


class ClaimRewardResponse(BaseModel):
    """Achievement reward claim response."""
    success: bool
    reward_amount: float
    new_balance: float
    claimed_at: str


class GlobalStatsResponse(BaseModel):
    """Global achievement statistics."""
    total_achievements: int
    by_category: Dict[str, int]
    by_rarity: Dict[str, int]
    total_rewards: float


# ==================== ENDPOINTS ====================

@router.get("/stats", response_model=GlobalStatsResponse)
async def get_global_achievement_stats():
    """
    Get global achievement statistics.

    Returns:
        Achievement stats including counts by category and rarity
    """
    return ACHIEVEMENT_STATS


@router.get("", response_model=AchievementsListResponse)
async def get_user_achievements(
    category: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all achievements for the authenticated user (including guests).

    Args:
        category: Optional filter by category (roulette, trading, social, milestones)
        current_user: Current user (authenticated or guest)
        db: Database session

    Returns:
        List of achievements with unlock status and stats
    """
    # Guest users can view achievements but have no unlocks
    if not current_user:
        from config.achievements import ALL_ACHIEVEMENTS
        guest_achievements = [
            {
                **achievement,
                "is_unlocked": False,
                "unlock_id": None,
                "unlocked_at": None,
                "progress_value": None,
                "reward_claimed": False,
                "reward_claimed_at": None
            }
            for achievement in (
                [a for a in ALL_ACHIEVEMENTS if a["category"] == category] if category
                else ALL_ACHIEVEMENTS
            )
        ]
        return {
            "achievements": guest_achievements,
            "stats": {
                "total_achievements": len(ALL_ACHIEVEMENTS),
                "total_unlocked": 0,
                "total_claimed": 0,
                "unclaimed_rewards": 0.0,
                "completion_percentage": 0.0
            }
        }

    result = await achievement_tracker.get_user_achievements(
        user_id=current_user.id,
        db=db,
        category=category
    )

    return result


@router.post("/{achievement_id}/claim", response_model=ClaimRewardResponse)
async def claim_achievement_reward(
    achievement_id: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Claim the GEM reward for an unlocked achievement.

    Args:
        achievement_id: Achievement unlock record ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Claim result with new balance
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        result = await achievement_tracker.claim_achievement_reward(
            user_id=current_user.id,
            achievement_id=achievement_id,
            db=db
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/category/{category}", response_model=AchievementsListResponse)
async def get_achievements_by_category_endpoint(
    category: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get achievements filtered by category.

    Args:
        category: Category name (roulette, trading, social, milestones)
        current_user: Authenticated user
        db: Database session

    Returns:
        Filtered list of achievements
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    valid_categories = ["roulette", "trading", "social", "milestones"]
    if category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
        )

    result = await achievement_tracker.get_user_achievements(
        user_id=current_user.id,
        db=db,
        category=category
    )

    return result
