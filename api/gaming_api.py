"""
Gaming API endpoints for crypto roulette.
Simplified, focused gaming system with proper GEM economy.
"""

import os
import json
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import (
    User, BetType, RoundPhase,
    DailyBonus, UserAchievement, Achievement,
    EmergencyTask, UserEmergencyTask
)
from gaming.roulette import roulette_engine
from gaming.round_manager import round_manager
from crypto.portfolio import portfolio_manager
from api.auth_api import get_current_user

router = APIRouter()

# ==================== REQUEST/RESPONSE MODELS ====================

class CreateGameRequest(BaseModel):
    client_seed: Optional[str] = Field(None, description="Optional client seed for provably fair")

class PlaceBetRequest(BaseModel):
    bet_type: str = Field(..., description="Type of bet (single_number, red_black, etc.)")
    bet_value: str = Field(..., description="Value to bet on (number, color, etc.)")
    amount: float = Field(..., gt=0, description="Bet amount in GEMs")

class GameSessionResponse(BaseModel):
    game_id: str
    server_seed_hash: str
    client_seed: str
    status: str

class BetResponse(BaseModel):
    success: bool
    bet_id: Optional[str] = None
    message: str
    error: Optional[str] = None

class SpinResult(BaseModel):
    success: bool
    result: Optional[Dict[str, Any]] = None
    bets: Optional[List[Dict[str, Any]]] = None
    total_winnings: Optional[float] = None
    provably_fair: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class DailyBonusResponse(BaseModel):
    success: bool
    available: Optional[bool] = None
    bonus_amount: Optional[int] = None
    claimed: Optional[bool] = None
    consecutive_days: Optional[int] = None
    next_claim_available: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None

  
class AchievementResponse(BaseModel):
    success: bool
    achievements: Optional[List[Dict[str, Any]]] = None
    unclaimed_gems: Optional[int] = None
    error: Optional[str] = None

  
class TaskResponse(BaseModel):
    success: bool
    tasks: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

  
class AchievementProgressResponse(BaseModel):
    success: bool
    achievements: Optional[List[Dict[str, Any]]] = None
    progress: Optional[Dict[str, Any]] = None
    unclaimed_gems: Optional[int] = None
    error: Optional[str] = None

  
class EmergencyTaskResponse(BaseModel):
    success: bool
    tasks: Optional[List[Dict[str, Any]]] = None
    task_completed: Optional[Dict[str, Any]] = None
    gems_earned: Optional[int] = None
    error: Optional[str] = None

# ==================== GAME SESSION ENDPOINTS ====================

  
@router.post("/roulette/create", response_model=GameSessionResponse)
async def create_roulette_game(
    request: CreateGameRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Create a new roulette game session."""
    # Use guest user ID if not authenticated
    user_id = current_user.id if current_user else "guest"

    try:
        game_id = await roulette_engine.create_game_session(
            user_id=user_id,
            client_seed=request.client_seed
        )

        game_session = await roulette_engine.get_game_session(game_id)
        if not game_session:
            raise HTTPException(
                status_code=500,
                detail="Failed to create game session"
            )

        return GameSessionResponse(
            game_id=game_id,
            server_seed_hash=game_session["server_seed_hash"],
            client_seed=game_session["client_seed"],
            status=game_session["status"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating game: {str(e)}"
        )

  
@router.post("/roulette/{game_id}/bet", response_model=BetResponse)
async def place_roulette_bet(
    game_id: str,
    bet_request: PlaceBetRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Place a bet in a roulette game."""
    # Use guest user ID if not authenticated
    user_id = current_user.id if current_user else "guest"

    try:
        # Validate bet type
        try:
            BetType(bet_request.bet_type.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid bet type: {bet_request.bet_type}"
            )

        # Reject bets with 0 or negative GEMs
        if bet_request.amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="Bet amount must be greater than 0 GEM"
            )

        # For guest users, validate against guest balance
        if not current_user:
            guest_gems = 5000  # Guest mode balance
            if bet_request.amount > guest_gems:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Insufficient guest balance. Available: {guest_gems} GEM"
                    )
                )

        # CRITICAL FIX: Add exponential backoff retry mechanism for database locks
        max_retries = 3
        base_delay = 0.1  # Start with 100ms delay

        for attempt in range(max_retries):
            try:
                # Place the bet - casino logic ensures balance deduction happens here
                result = await roulette_engine.place_bet(
                    game_session_id=game_id,
                    user_id=user_id,
                    bet_type=bet_request.bet_type.upper(),
                    bet_value=bet_request.bet_value.lower(),
                    amount=bet_request.amount
                )

                if result["success"]:
                    # Track mission progress for authenticated users
                    if current_user:
                        try:
                            from services.mission_tracker import mission_tracker
                            from database.database import get_db
                            async for db in get_db():
                                await mission_tracker.track_event(
                                    user_id=current_user.id,
                                    event_name="roulette_bet_placed",
                                    amount=1,
                                    db=db
                                )
                                break
                        except Exception as mission_error:
                            # Don't fail bet if mission tracking fails
                            print(f"Mission tracking error: {mission_error}")

                    return BetResponse(
                        success=True,
                        bet_id=result["bet_id"],
                        message=result["message"]
                    )
                else:
                    # Explicitly return failure when database operations fail
                    return BetResponse(
                        success=False,
                        message=result.get("message", "Failed to place bet due to database issues"),
                        error=result.get("error", "Database operation failed")
                    )

            except Exception as db_error:
                error_msg = str(db_error).lower()

                # Check if it's a database lock error and we still have retries left
                is_lock_error = (
                    "database is locked" in error_msg or
                    "locked" in error_msg or
                    "concurrent access" in error_msg
                )

                if is_lock_error and attempt < max_retries - 1:
                    # Exponential backoff: 100ms, 200ms, 400ms...
                    import asyncio
                    delay = base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue

                # If not a lock error or we've exhausted retries, raise the original error
                raise db_error

        # If we get here, we've exhausted retries
        raise Exception("Failed to place bet after maximum retry attempts")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error placing bet: {str(e)}"
        )

  
@router.post("/roulette/{game_id}/spin", response_model=SpinResult)
async def spin_roulette(
    game_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Spin the roulette wheel and determine results."""
    try:
        result = await roulette_engine.spin_wheel(game_id)

        if result["success"]:
            # Track mission progress for wins (authenticated users only)
            if current_user and result.get("total_winnings", 0) > 0:
                try:
                    from services.mission_tracker import mission_tracker
                    from services.achievement_tracker import achievement_tracker
                    from database.database import get_db

                    # Count how many bets won
                    winning_bets = sum(1 for bet in result.get("bets", []) if bet.get("won", False))

                    if winning_bets > 0:
                        async for db in get_db():
                            # Track missions
                            await mission_tracker.track_event(
                                user_id=current_user.id,
                                event_name="roulette_bet_won",
                                amount=winning_bets,
                                db=db
                            )

                            # Check achievements - first win
                            await achievement_tracker.check_achievements(
                                user_id=current_user.id,
                                trigger="roulette_first_win",
                                value=1,
                                db=db
                            )

                            # Check big win achievement
                            if result.get("total_winnings", 0) >= 10000:
                                await achievement_tracker.check_achievements(
                                    user_id=current_user.id,
                                    trigger="roulette_big_win",
                                    value=result.get("total_winnings", 0),
                                    db=db
                                )

                            break
                except Exception as mission_error:
                    # Don't fail spin if mission tracking fails
                    print(f"Mission tracking error (win): {mission_error}")

            return SpinResult(
                success=True,
                result=result["result"],
                bets=result["bets"],
                total_winnings=result["total_winnings"],
                provably_fair=result["provably_fair"]
            )
        else:
            return SpinResult(
                success=False,
                error=result["error"]
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error spinning wheel: {str(e)}"
        )

  
@router.get("/roulette/{game_id}")
async def get_game_session(game_id: str):
    """Get game session details."""
    try:
        game_session = await roulette_engine.get_game_session(game_id)
        if not game_session:
            raise HTTPException(
                status_code=404,
                detail="Game session not found"
            )

        return {
            "success": True,
            "game_session": game_session
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching game: {str(e)}"
        )

# ==================== ROULETTE INFO ENDPOINTS ====================

  
@router.get("/roulette/wheel/layout")
async def get_wheel_layout():
    """Get the complete roulette wheel layout."""
    try:
        layout = roulette_engine.get_wheel_layout()
        return {
            "success": True,
            "wheel_layout": layout,
            "total_positions": len(layout)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching wheel layout: {str(e)}"
        )

  
@router.get("/roulette/bet-types")
async def get_bet_types():
    """Get available bet types and their payouts."""
    try:
        bet_types = roulette_engine.get_bet_types()
        return {
            "success": True,
            "bet_types": bet_types
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching bet types: {str(e)}"
        )

  
@router.get("/roulette/rules")
async def get_roulette_rules():
    """Get roulette game rules and information."""
    return {
        "success": True,
        "rules": {
            "game_type": "Crypto Roulette",
            "wheel_positions": 37,
            "special_position": "0 (Bitcoin) - Green",
            "bet_limits": {
                "minimum": 10,
                "maximum": 10000,
                "currency": "GEM"
            },
            "bet_types": {
                "single_number": {
                    "description": "Bet on a specific number (0-36)",
                    "payout": "35:1",
                    "example": "Bet on number 25"
                },
                "red_black": {
                    "description": "Bet on red or black cryptocurrencies",
                    "payout": "1:1",
                    "example": "Bet on 'red' or 'black'"
                },
                "even_odd": {
                    "description": "Bet on even or odd numbers (0 excluded)",
                    "payout": "1:1",
                    "example": "Bet on 'even' or 'odd'"
                },
                "high_low": {
                    "description": "Bet on high (19-36) or low (1-18) numbers",
                    "payout": "1:1",
                    "example": "Bet on 'high' or 'low'"
                },
                "crypto_category": {
                    "description": "Bet on cryptocurrency category",
                    "payout": "5:1",
                    "example": "Bet on 'defi', 'layer1', 'meme', etc."
                }
            },
            "provably_fair": {
                "enabled": True,
                "description": "All results are provably fair using cryptographic hashing",
                "verification": "Server seed + Client seed + Nonce = Verifiable result"
            },
            "guest_mode": {
                "enabled": True,
                "balance": "5000 GEM (temporary)",
                "limitations": "No balance persistence, no transaction history"
            }
        }
    }

# ==================== GAME HISTORY ENDPOINTS ====================

@router.get("/roulette/history")
async def get_game_history(
    current_user: Optional[User] = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0)
):
    """Get user's roulette game history."""
    if not current_user:
        return {
            "success": True,
            "games": [],
            "count": 0,
            "message": "Game history not available in guest mode"
        }

    try:
        games = await roulette_engine.get_user_games(current_user.id, limit, offset)
        return {
            "success": True,
            "games": games,
            "count": len(games),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching game history: {str(e)}")

# ==================== GAMING STATS ENDPOINTS ====================

@router.get("/stats")
async def get_gaming_stats(current_user: Optional[User] = Depends(get_current_user)):
    """Get user's gaming statistics."""
    if not current_user:
        return {
            "success": True,
            "stats": {
                "total_games": 0,
                "games_won": 0,
                "games_lost": 0,
                "win_rate": 0,
                "total_wagered": 0,
                "total_won": 0,
                "net_result": 0,
                "favorite_bet_type": None
            },
            "message": "Detailed stats not available in guest mode"
        }

    try:
        portfolio_stats = await portfolio_manager.get_portfolio_stats(current_user.id)
        gaming_stats = portfolio_stats.get("stats", {})

        return {
            "success": True,
            "stats": {
                "total_games": gaming_stats.get("total_games", 0),
                "games_won": gaming_stats.get("games_won", 0),
                "games_lost": gaming_stats.get("games_lost", 0),
                "win_rate": gaming_stats.get("win_rate", 0),
                "total_wagered": gaming_stats.get("total_bets", 0),
                "total_won": gaming_stats.get("total_winnings", 0),
                "net_result": gaming_stats.get("net_gambling", 0),
                "current_balance": gaming_stats.get("gem_balance", 0)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching gaming stats: {str(e)}")

@router.get("/validate-bet")
async def validate_bet_amount(
    amount: float = Query(..., gt=0, description="Bet amount to validate"),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Validate if user can place a bet of given amount."""
    # Use guest user ID if not authenticated
    user_id = current_user.id if current_user else "guest"

    try:
        if not current_user:
            # Guest mode validation
            guest_gems = 5000  # Guest mode balance
            if amount < 10:
                return {"valid": False, "message": "Minimum bet amount is 10 GEM"}
            elif amount > 10000:
                return {"valid": False, "message": "Maximum bet amount is 10,000 GEM"}
            elif amount > guest_gems:
                return {"valid": False, "message": f"Insufficient guest balance: {guest_gems} GEM"}
            else:
                return {"valid": True, "message": "Valid bet amount"}

        # Authenticated user validation
        is_valid, message = await portfolio_manager.validate_bet_amount(user_id, amount)
        return {
            "valid": is_valid,
            "message": message
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating bet: {str(e)}")

# ==================== GEM EARNING SYSTEM ENDPOINTS ====================

@router.get("/daily-bonus", response_model=DailyBonusResponse)
async def get_daily_bonus_status(
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check daily bonus availability for user."""
    if not current_user:
        return DailyBonusResponse(
            success=False,
            error="Authentication required for daily bonus"
        )

    # Defensive check: ensure the DailyBonus model is available
    try:
        _ = DailyBonus
    except NameError as ne:
        raise HTTPException(status_code=500, detail=f"DailyBonus model not available: {ne}")

    try:
        from datetime import datetime, timedelta
        from sqlalchemy import select, func

        # Get user's latest daily bonus
        query = select(DailyBonus).where(
            DailyBonus.user_id == current_user.id
        ).order_by(DailyBonus.claim_date.desc()).limit(1)

        result = await db.execute(query)
        latest_bonus = result.scalars().first()

        now = datetime.utcnow()
        can_claim = False
        next_claim_available = None
        consecutive_days = 1

        if not latest_bonus:
            # First time claiming
            can_claim = True
        else:
            # Check if 24 hours have passed
            hours_since_last_claim = (now - latest_bonus.claim_date).total_seconds() / 3600

            if hours_since_last_claim >= 24:
                can_claim = True
                # Check if streak continues (within 48 hours)
                if hours_since_last_claim <= 48:
                    consecutive_days = latest_bonus.consecutive_days + 1
                else:
                    consecutive_days = 1  # Reset streak
            else:
                next_claim_available = (latest_bonus.claim_date + timedelta(hours=24)).isoformat()

        return DailyBonusResponse(
            success=True,
            claimed=False,
            consecutive_days=consecutive_days,
            next_claim_available=next_claim_available,
            message="Daily bonus available" if can_claim else "Daily bonus already claimed today"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking daily bonus: {str(e)}")

@router.post("/daily-bonus/claim", response_model=DailyBonusResponse)
async def claim_daily_bonus(
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Claim daily bonus GEM reward."""
    if not current_user:
        return DailyBonusResponse(
            success=False,
            error="Authentication required for daily bonus"
        )

    # Defensive check: ensure the DailyBonus model is available
    try:
        _ = DailyBonus
    except NameError as ne:
        raise HTTPException(status_code=500, detail=f"DailyBonus model not available: {ne}")

    try:
        from datetime import datetime, timedelta
        from sqlalchemy import select

        # Check if bonus can be claimed
        query = select(DailyBonus).where(
            DailyBonus.user_id == current_user.id
        ).order_by(DailyBonus.claim_date.desc()).limit(1)

        result = await db.execute(query)
        latest_bonus = result.scalars().first()

        now = datetime.utcnow()
        can_claim = False
        consecutive_days = 1

        if not latest_bonus:
            can_claim = True
        else:
            hours_since_last_claim = (now - latest_bonus.claim_date).total_seconds() / 3600

            if hours_since_last_claim >= 24:
                can_claim = True
                if hours_since_last_claim <= 48:
                    consecutive_days = latest_bonus.consecutive_days + 1
                else:
                    consecutive_days = 1
            else:
                return DailyBonusResponse(
                    success=False,
                    error="Daily bonus already claimed today"
                )

        if not can_claim:
            return DailyBonusResponse(
                success=False,
                error="Daily bonus not available yet"
            )

        # Calculate bonus amount based on consecutive days
        base_bonus = 100
        streak_bonus = min(consecutive_days * 25, 400)  # Max 400 bonus for streak
        total_bonus = base_bonus + streak_bonus

        # Create daily bonus record
        daily_bonus = DailyBonus(
            user_id=current_user.id,
            claim_date=now,
            bonus_amount=total_bonus,
            consecutive_days=consecutive_days,
            last_claim_date=latest_bonus.claim_date if latest_bonus else None
        )
        db.add(daily_bonus)

        # Update user balance via portfolio manager
        await portfolio_manager.add_gems(
            current_user.id,
            total_bonus,
            f"Daily bonus claimed - Day {consecutive_days} streak"
        )

        await db.commit()

        return DailyBonusResponse(
            success=True,
            claimed=True,
            bonus_amount=total_bonus,
            consecutive_days=consecutive_days,
            message=f"Daily bonus claimed! +{total_bonus} GEM (Day {consecutive_days} streak)"
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error claiming daily bonus: {str(e)}")

@router.get("/achievements", response_model=AchievementProgressResponse)
async def get_user_achievements(
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's achievement progress and available rewards."""
    if not current_user:
        return AchievementProgressResponse(
            success=False,
            error="Authentication required for achievements"
        )

    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # Get all user achievements with achievement details
        query = select(UserAchievement).options(
            selectinload(UserAchievement.achievement)
        ).where(UserAchievement.user_id == current_user.id)

        result = await db.execute(query)
        user_achievements = result.scalars().all()

        achievements_data = []
        total_unclaimed_rewards = 0.0

        for user_achievement in user_achievements:
            achievement_dict = user_achievement.to_dict(include_achievement=True)
            achievements_data.append(achievement_dict)

            # Add to unclaimed rewards if completed but not claimed
            if user_achievement.is_completed and not user_achievement.reward_claimed:
                total_unclaimed_rewards += user_achievement.achievement.reward_amount

        return AchievementProgressResponse(
            success=True,
            achievements=achievements_data,
            total_unclaimed_rewards=total_unclaimed_rewards
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching achievements: {str(e)}")

@router.post("/achievements/{achievement_id}/claim")
async def claim_achievement_reward(
    achievement_id: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Claim reward for completed achievement."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from datetime import datetime

        # Get user achievement
        query = select(UserAchievement).options(
            selectinload(UserAchievement.achievement)
        ).where(
            UserAchievement.user_id == current_user.id,
            UserAchievement.achievement_id == achievement_id
        )

        result = await db.execute(query)
        user_achievement = result.scalars().first()

        if not user_achievement:
            raise HTTPException(status_code=404, detail="Achievement not found")

        if not user_achievement.is_completed:
            raise HTTPException(status_code=400, detail="Achievement not completed yet")

        if user_achievement.reward_claimed:
            raise HTTPException(status_code=400, detail="Reward already claimed")

        # Claim the reward
        user_achievement.reward_claimed = True
        user_achievement.reward_claimed_at = datetime.utcnow()

        # Add GEM to user balance
        reward_amount = user_achievement.achievement.reward_amount
        await portfolio_manager.add_gems(
            current_user.id,
            reward_amount,
            f"Achievement reward: {user_achievement.achievement.name}"
        )

        await db.commit()

        return {
            "success": True,
            "message": f"Achievement reward claimed! +{reward_amount} GEM",
            "reward_amount": reward_amount,
            "achievement_name": user_achievement.achievement.name
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error claiming achievement reward: {str(e)}")

@router.get("/emergency-tasks", response_model=EmergencyTaskResponse)
async def get_emergency_tasks(
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available emergency GEM tasks for low balance users."""
    if not current_user:
        return EmergencyTaskResponse(
            success=False,
            error="Authentication required for emergency tasks"
        )

    try:
        from datetime import datetime, timedelta
        from sqlalchemy import select, func

        # Get user's current balance
        portfolio_stats = await portfolio_manager.get_portfolio_stats(current_user.id)
        current_balance = portfolio_stats.get("gem_balance", 0)

        # Get all active emergency tasks
        tasks_query = select(EmergencyTask).where(
            EmergencyTask.is_active == True,
            EmergencyTask.min_balance_threshold >= current_balance
        )

        result = await db.execute(tasks_query)
        all_tasks = result.scalars().all()

        available_tasks = []

        for task in all_tasks:
            # Check user's completions today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            completions_query = select(func.count(UserEmergencyTask.id)).where(
                UserEmergencyTask.user_id == current_user.id,
                UserEmergencyTask.task_id == task.id,
                UserEmergencyTask.completed_at >= today_start
            )

            result = await db.execute(completions_query)
            today_completions = result.scalar()

            # Check last completion for cooldown
            last_completion_query = select(UserEmergencyTask).where(
                UserEmergencyTask.user_id == current_user.id,
                UserEmergencyTask.task_id == task.id
            ).order_by(UserEmergencyTask.completed_at.desc()).limit(1)

            result = await db.execute(last_completion_query)
            last_completion = result.scalars().first()

            # Check if task is available
            can_complete = True
            cooldown_remaining = 0

            if today_completions >= task.max_completions_per_day:
                can_complete = False
            elif last_completion:
                minutes_since_last = (datetime.utcnow() - last_completion.completed_at).total_seconds() / 60
                if minutes_since_last < task.cooldown_minutes:
                    can_complete = False
                    cooldown_remaining = int(task.cooldown_minutes - minutes_since_last)

            task_dict = task.to_dict()
            task_dict["can_complete"] = can_complete
            task_dict["completions_today"] = today_completions
            task_dict["cooldown_remaining_minutes"] = cooldown_remaining

            available_tasks.append(task_dict)

        return EmergencyTaskResponse(
            success=True,
            available_tasks=available_tasks,
            message=f"Found {len(available_tasks)} emergency tasks (Balance: {current_balance} GEM)"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching emergency tasks: {str(e)}")

@router.post("/emergency-tasks/{task_id}/complete", response_model=EmergencyTaskResponse)
async def complete_emergency_task(
    task_id: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Complete an emergency task and claim GEM reward."""
    if not current_user:
        return EmergencyTaskResponse(
            success=False,
            error="Authentication required for emergency tasks"
        )

    try:
        from datetime import datetime, timedelta
        from sqlalchemy import select, func

        # Get the task
        task_query = select(EmergencyTask).where(EmergencyTask.id == task_id)
        result = await db.execute(task_query)
        task = result.scalars().first()

        if not task or not task.is_active:
            return EmergencyTaskResponse(
                success=False,
                error="Task not found or inactive"
            )

        # Check user's current balance
        portfolio_stats = await portfolio_manager.get_portfolio_stats(current_user.id)
        current_balance = portfolio_stats.get("gem_balance", 0)

        if current_balance >= task.min_balance_threshold:
            return EmergencyTaskResponse(
                success=False,
                error=f"Balance too high for emergency task (need below {task.min_balance_threshold} GEM)"
            )

        # Check daily completion limit
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        completions_query = select(func.count(UserEmergencyTask.id)).where(
            UserEmergencyTask.user_id == current_user.id,
            UserEmergencyTask.task_id == task_id,
            UserEmergencyTask.completed_at >= today_start
        )

        result = await db.execute(completions_query)
        today_completions = result.scalar()

        if today_completions >= task.max_completions_per_day:
            return EmergencyTaskResponse(
                success=False,
                error="Daily completion limit reached for this task"
            )

        # Check cooldown
        last_completion_query = select(UserEmergencyTask).where(
            UserEmergencyTask.user_id == current_user.id,
            UserEmergencyTask.task_id == task_id
        ).order_by(UserEmergencyTask.completed_at.desc()).limit(1)

        result = await db.execute(last_completion_query)
        last_completion = result.scalars().first()

        if last_completion:
            minutes_since_last = (datetime.utcnow() - last_completion.completed_at).total_seconds() / 60
            if minutes_since_last < task.cooldown_minutes:
                remaining = int(task.cooldown_minutes - minutes_since_last)
                return EmergencyTaskResponse(
                    success=False,
                    error=f"Task on cooldown. Try again in {remaining} minutes."
                )

        # Complete the task
        completion = UserEmergencyTask(
            user_id=current_user.id,
            task_id=task_id,
            completed_at=datetime.utcnow(),
            reward_claimed=True
        )
        db.add(completion)

        # Award GEM
        await portfolio_manager.add_gems(
            current_user.id,
            task.reward_amount,
            f"Emergency task completed: {task.name}"
        )

        await db.commit()

        return EmergencyTaskResponse(
            success=True,
            completed_task=task.to_dict(),
            reward_amount=task.reward_amount,
            message=f"Task completed! +{task.reward_amount} GEM earned"
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error completing emergency task: {str(e)}")

@router.post("/initialize-achievements")
async def initialize_default_achievements(
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Initialize default achievements for the platform (Admin only)."""
    if not current_user or current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        from sqlalchemy import select

        # Check if achievements already exist
        query = select(Achievement).limit(1)
        result = await db.execute(query)
        existing = result.scalars().first()

        if existing:
            return {"success": True, "message": "Achievements already initialized"}

        # Default achievements
        default_achievements = [
            Achievement(
                name="First Bet",
                description="Place your first bet in crypto roulette",
                achievement_type="FIRST_BET",
                target_value=1,
                reward_amount=50,
                icon="star"
            ),
            Achievement(
                name="High Roller",
                description="Place a bet of 1000 GEM or more",
                achievement_type="HIGH_ROLLER",
                target_value=1000,
                reward_amount=100,
                icon="crown"
            ),
            Achievement(
                name="Bet Master",
                description="Place 10 total bets",
                achievement_type="TOTAL_BETS",
                target_value=10,
                reward_amount=75,
                icon="trophy"
            ),
            Achievement(
                name="GEM Spender",
                description="Wager 5000 GEM in total",
                achievement_type="TOTAL_WAGERED",
                target_value=5000,
                reward_amount=200,
                icon="gem"
            ),
            Achievement(
                name="Lucky Seven",
                description="Hit number 7 in roulette",
                achievement_type="LUCKY_NUMBER",
                target_value=7,
                reward_amount=150,
                icon="dice"
            ),
            Achievement(
                name="Big Win",
                description="Win 500 GEM or more in a single round",
                achievement_type="BIG_WIN",
                target_value=500,
                reward_amount=100,
                icon="medal"
            )
        ]

        for achievement in default_achievements:
            db.add(achievement)

        # Initialize default emergency tasks
        default_tasks = [
            EmergencyTask(
                name="Watch Advertisement",
                description="Watch a short ad to earn emergency GEM",
                task_type="watch_ad",
                reward_amount=25,
                cooldown_minutes=30,
                max_completions_per_day=5,
                min_balance_threshold=50
            ),
            EmergencyTask(
                name="Quick Survey",
                description="Complete a brief survey about your gaming experience",
                task_type="survey",
                reward_amount=50,
                cooldown_minutes=60,
                max_completions_per_day=3,
                min_balance_threshold=50
            ),
            EmergencyTask(
                name="Mini Challenge",
                description="Complete a simple number guessing game",
                task_type="mini_game",
                reward_amount=35,
                cooldown_minutes=45,
                max_completions_per_day=4,
                min_balance_threshold=50
            )
        ]

        for task in default_tasks:
            db.add(task)

        await db.commit()

        return {
            "success": True,
            "message": f"Initialized {len(default_achievements)} achievements and {len(default_tasks)} emergency tasks"
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error initializing achievements: {str(e)}")


# ==================== SERVER-MANAGED ROUND ENDPOINTS ====================

@router.get("/roulette/round/current")
async def get_current_round(current_user: User = Depends(get_current_user)):
    """Get current round state"""
    current = round_manager.get_current_round()
    if not current:
        # No round active, this shouldn't happen but handle gracefully
        return {"success": False, "error": "No active round"}

    return {"success": True, "round": current}


@router.post("/roulette/round/spin")
async def trigger_manual_spin(
    game_id: str,
    current_user: User = Depends(get_current_user)
):
    """Player-initiated spin (manual trigger)"""
    try:
        outcome = await round_manager.trigger_spin(
            user_id=current_user.id,
            game_session_id=game_id
        )
        return {"success": True, "outcome": outcome}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spin error: {str(e)}")


@router.get("/roulette/round/stream")
async def round_event_stream(current_user: Optional[User] = Depends(get_current_user)):
    """Server-Sent Events stream for round updates"""
    # Generate a unique ID for guest users
    user_id = current_user.id if current_user else f"guest-{id(current_user)}"
    queue = await round_manager.subscribe_sse(user_id)

    async def event_generator():
        try:
            while True:
                event_data = await queue.get()
                # SSE format: event: <type>\ndata: <json>\n\n
                event_type = event_data.get("event", "message")
                data = event_data.get("data", {})
                yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            round_manager.unsubscribe_sse(user_id)
            raise
        except Exception as e:
            print(f"[SSE] Error for user {user_id}: {e}")
            round_manager.unsubscribe_sse(user_id)
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/roulette/round/{round_id}/results")
async def get_round_results(
    round_id: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed bet results for a specific round (for authenticated users only)"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        from sqlalchemy import select
        from database.models import GameBet

        # Query all bets for this round and user
        query = select(GameBet).where(
            GameBet.round_id == round_id,
            GameBet.user_id == current_user.id
        )

        result = await db.execute(query)
        bets = result.scalars().all()

        if not bets:
            return {
                "success": True,
                "bets": [],
                "message": "No bets found for this round"
            }

        # Format bet results
        bet_results = []
        for bet in bets:
            bet_results.append({
                "bet_id": bet.id,
                "bet_type": bet.bet_type,
                "bet_value": bet.bet_value,
                "amount": bet.amount,
                "is_winner": bet.is_winner if bet.is_winner is not None else False,
                "payout": bet.payout_amount if bet.payout_amount is not None else 0,
                "multiplier": bet.payout_multiplier if bet.payout_multiplier is not None else 0
            })

        return {
            "success": True,
            "bets": bet_results,
            "round_id": round_id
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching round results: {str(e)}"
        )
