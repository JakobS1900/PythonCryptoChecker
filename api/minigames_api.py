"""
Mini-Games API

REST API endpoints for Coin Flip, Dice Roll, and Higher/Lower games.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import User
from api.auth_api import require_authentication
from services.minigames_service import MiniGamesService


router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CoinFlipRequest(BaseModel):
    """Request model for Coin Flip game."""
    bet_amount: int = Field(..., ge=100, le=100000, description="Bet amount (100-100000 GEM)")
    choice: str = Field(..., description="'heads' or 'tails'")


class DiceRollRequest(BaseModel):
    """Request model for Dice Roll game."""
    bet_amount: int = Field(..., ge=100, le=100000, description="Bet amount (100-100000 GEM)")
    bet_type: str = Field(..., description="'exact', 'even', 'odd', 'high', or 'low'")
    bet_value: Optional[int] = Field(None, ge=1, le=6, description="For 'exact' bets only (1-6)")


class HigherLowerRequest(BaseModel):
    """Request model for Higher/Lower game."""
    bet_amount: int = Field(..., ge=100, le=100000, description="Bet amount (100-100000 GEM)")
    guess: str = Field(..., description="'higher', 'lower', or 'same'")


class GameResultResponse(BaseModel):
    """Response model for game results."""
    success: bool
    message: str
    result: dict


class StatsResponse(BaseModel):
    """Response model for user statistics."""
    stats: dict


class HistoryResponse(BaseModel):
    """Response model for game history."""
    games: list


# ============================================================================
# GAME ENDPOINTS
# ============================================================================

@router.post("/coinflip", response_model=GameResultResponse)
async def play_coinflip(
    request: CoinFlipRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Play Coin Flip game.

    - **bet_amount**: Amount to wager (100-100000 GEM)
    - **choice**: 'heads' or 'tails'
    - **Payout**: 2x on win
    """
    try:
        result = await MiniGamesService.play_coinflip(
            user_id=current_user.id,
            bet_amount=request.bet_amount,
            choice=request.choice,
            db=db
        )

        message = f"🎉 You won {result['payout']} GEM!" if result['won'] else f"💔 You lost {request.bet_amount} GEM"

        return GameResultResponse(
            success=True,
            message=message,
            result=result
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Game error: {str(e)}")


@router.post("/dice", response_model=GameResultResponse)
async def play_dice(
    request: DiceRollRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Play Dice Roll game.

    - **bet_amount**: Amount to wager (100-100000 GEM)
    - **bet_type**: 'exact' (1-6), 'even', 'odd', 'high' (4-6), 'low' (1-3)
    - **bet_value**: Required for 'exact' bets
    - **Payout**: 6x for exact, 2x for even/odd/high/low
    """
    try:
        result = await MiniGamesService.play_dice(
            user_id=current_user.id,
            bet_amount=request.bet_amount,
            bet_type=request.bet_type,
            db=db,
            bet_value=request.bet_value
        )

        message = f"🎉 You won {result['payout']} GEM!" if result['won'] else f"💔 You lost {request.bet_amount} GEM"

        return GameResultResponse(
            success=True,
            message=message,
            result=result
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Game error: {str(e)}")


@router.post("/higherlower", response_model=GameResultResponse)
async def play_higherlower(
    request: HigherLowerRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Play Higher/Lower card game.

    - **bet_amount**: Amount to wager (100-100000 GEM)
    - **guess**: 'higher', 'lower', or 'same'
    - **Payout**: 2x for higher/lower, 5x for same
    """
    try:
        result = await MiniGamesService.play_higherlower(
            user_id=current_user.id,
            bet_amount=request.bet_amount,
            guess=request.guess,
            db=db
        )

        message = f"🎉 You won {result['payout']} GEM!" if result['won'] else f"💔 You lost {request.bet_amount} GEM"

        return GameResultResponse(
            success=True,
            message=message,
            result=result
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Game error: {str(e)}")


# ============================================================================
# STATISTICS ENDPOINTS
# ============================================================================

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's mini-game statistics.

    Returns overall stats, per-game stats, streaks, and records.
    """
    try:
        stats = await MiniGamesService.get_user_stats(current_user.id, db)

        return StatsResponse(stats=stats)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    limit: int = 50,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's recent game history.

    - **limit**: Number of games to return (default: 50, max: 100)
    """
    try:
        if limit > 100:
            limit = 100

        games = await MiniGamesService.get_recent_games(current_user.id, db, limit)

        return HistoryResponse(games=games)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


# ============================================================================
# INFO ENDPOINT
# ============================================================================

@router.get("/info")
async def get_game_info():
    """
    Get information about all available mini-games.

    Returns game rules, payouts, and limits.
    """
    return {
        'min_bet': MiniGamesService.MIN_BET,
        'max_bet': MiniGamesService.MAX_BET,
        'games': {
            'coinflip': {
                'name': 'Coin Flip',
                'description': 'Guess heads or tails',
                'payout': '2x on win',
                'multiplier': MiniGamesService.COINFLIP_MULTIPLIER,
                'win_chance': '50%'
            },
            'dice': {
                'name': 'Dice Roll',
                'description': 'Bet on dice outcomes',
                'payouts': {
                    'exact': '6x (guess exact number 1-6)',
                    'even': '2x (roll 2, 4, or 6)',
                    'odd': '2x (roll 1, 3, or 5)',
                    'high': '2x (roll 4, 5, or 6)',
                    'low': '2x (roll 1, 2, or 3)'
                },
                'multipliers': MiniGamesService.DICE_MULTIPLIERS
            },
            'higherlower': {
                'name': 'Higher or Lower',
                'description': 'Guess if next card is higher, lower, or same',
                'payouts': {
                    'higher/lower': '2x on correct guess',
                    'same': '5x on correct guess (rare)'
                },
                'multiplier_normal': MiniGamesService.HIGHERLOWER_MULTIPLIER,
                'multiplier_same': MiniGamesService.HIGHERLOWER_SAME_MULTIPLIER
            }
        }
    }
