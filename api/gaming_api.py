"""
Gaming API endpoints for roulette and casino games.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.database_manager import get_db_session
from database.unified_models import GameType, BetType
from gaming.roulette_engine import RouletteEngine
from gaming.game_variants import GameVariants
from gaming.websocket_manager import websocket_manager
from achievements.achievement_engine import achievement_engine
from auth.auth_manager import AuthenticationManager
from logger import logger

router = APIRouter()
security = HTTPBearer()
auth_manager = AuthenticationManager()
roulette_engine = RouletteEngine()
game_variants = GameVariants()


# ==================== REQUEST/RESPONSE MODELS ====================

class CreateGameRequest(BaseModel):
    game_type: str = Field(default="CLASSIC_CRYPTO", description="Type of game to create")
    client_seed_input: Optional[str] = Field(None, description="Optional client seed input")


class PlaceBetRequest(BaseModel):
    bet_type: str = Field(..., description="Type of bet (SINGLE_CRYPTO, CRYPTO_COLOR, etc.)")
    bet_value: str = Field(..., description="Value being bet on (bitcoin, red, even, etc.)")
    bet_amount: float = Field(..., gt=0, description="Amount in GEM coins")
    live_betting: bool = Field(default=True, description="Enable real-time WebSocket updates")


class GameSessionResponse(BaseModel):
    game_id: str
    game_type: str
    status: str
    server_seed_hash: str
    client_seed: str
    nonce: int
    total_bet_amount: float
    created_at: str
    websocket_url: str
    room_stats: Dict[str, Any]


class GameResultResponse(BaseModel):
    game_id: str
    winning_number: int
    winning_crypto: str
    winning_details: Dict[str, Any]
    total_bet: float
    total_winnings: float
    net_result: float
    winning_bets: int
    losing_bets: int
    bets_details: List[Dict[str, Any]]
    provably_fair: Dict[str, Any]


class TournamentRequest(BaseModel):
    name: str = Field(..., max_length=100)
    description: str = Field(..., max_length=500)
    entry_fee: float = Field(default=100.0, ge=0)
    prize_pool: float = Field(default=5000.0, gt=0)
    duration_hours: int = Field(default=168, gt=0)  # 1 week
    max_participants: int = Field(default=100, gt=0)


class PricePredictionRequest(BaseModel):
    crypto_id: str = Field(..., description="Cryptocurrency ID (e.g., bitcoin)")
    prediction_direction: str = Field(..., pattern="^(UP|DOWN|SIDEWAYS)$")
    bet_amount: float = Field(..., gt=0, description="Bet amount in GEM coins")
    prediction_duration: int = Field(default=300, gt=0, description="Duration in seconds")


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


# ==================== GAME SESSION ENDPOINTS ====================

@router.post("/sessions", response_model=GameSessionResponse)
async def create_game_session(
    request: CreateGameRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Create new game session."""
    try:
        game_type = GameType(request.game_type)
        
        game_session = await roulette_engine.create_game_session(
            session=session,
            user_id=user_id,
            game_type=game_type,
            client_seed_input=request.client_seed_input
        )
        
        return GameSessionResponse(
            game_id=game_session.id,
            game_type=game_session.game_type,
            status=game_session.status,
            server_seed_hash=game_session.server_seed_hash,
            client_seed=game_session.client_seed,
            nonce=game_session.nonce,
            total_bet_amount=game_session.total_bet_amount,
            created_at=game_session.created_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to create game session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/sessions/{game_id}/bets")
async def place_bet(
    game_id: str,
    request: PlaceBetRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Place bet on game session."""
    try:
        bet_type = BetType(request.bet_type)
        
        game_bet = await roulette_engine.place_bet(
            session=session,
            game_session_id=game_id,
            user_id=user_id,
            bet_type=bet_type,
            bet_value=request.bet_value,
            bet_amount=request.bet_amount
        )
        
        return {
            "bet_id": game_bet.id,
            "bet_type": game_bet.bet_type,
            "bet_value": game_bet.bet_value,
            "bet_amount": game_bet.bet_amount,
            "potential_payout": game_bet.potential_payout,
            "odds": game_bet.payout_odds,
            "placed_at": game_bet.placed_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to place bet: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/sessions/{game_id}/spin", response_model=GameResultResponse)
async def spin_wheel(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Spin roulette wheel and get results."""
    try:
        result = await roulette_engine.spin_wheel(
            session=session,
            game_session_id=game_id,
            user_id=user_id
        )
        
        # Trigger achievement checks
        won_game = result["total_winnings"] > result["total_bet"]
        
        await achievement_engine.check_user_achievements(
            session, user_id, "game_played", 
            {"game_id": game_id, "won": won_game}
        )
        
        if won_game:
            await achievement_engine.check_user_achievements(
                session, user_id, "game_won", 
                {
                    "winnings": result["total_winnings"] - result["total_bet"],
                    "bet_amount": result["total_bet"]
                }
            )
            
            # Check for big win achievement
            if result["total_winnings"] >= 10000:
                await achievement_engine.check_user_achievements(
                    session, user_id, "big_win",
                    {"winnings": result["total_winnings"]}
                )
        
        return GameResultResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to spin wheel: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/sessions/{game_id}/verify")
async def verify_game_fairness(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Reveal server seed for provably fair verification."""
    try:
        verification_data = await roulette_engine.reveal_server_seed(
            session=session,
            game_session_id=game_id,
            user_id=user_id
        )
        
        return verification_data
        
    except Exception as e:
        logger.error(f"Failed to verify game fairness: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== GAME HISTORY & STATS ====================

@router.get("/history")
async def get_game_history(
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get user's game history."""
    try:
        history = await roulette_engine.get_user_game_history(
            session=session,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        return {
            "games": history,
            "limit": limit,
            "offset": offset,
            "total": len(history)
        }
        
    except Exception as e:
        logger.error(f"Failed to get game history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get game history"
        )


@router.get("/stats")
async def get_user_game_stats(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get comprehensive user gaming statistics."""
    try:
        stats = await roulette_engine.get_user_stats(
            session=session,
            user_id=user_id
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get game stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get game stats"
        )


# ==================== TOURNAMENTS ====================

@router.post("/tournaments")
async def create_tournament(
    request: TournamentRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Create new tournament (admin only in production)."""
    try:
        tournament = await game_variants.create_tournament(
            session=session,
            name=request.name,
            description=request.description,
            entry_fee=request.entry_fee,
            prize_pool=request.prize_pool,
            duration_hours=request.duration_hours,
            max_participants=request.max_participants
        )
        
        return {
            "tournament_id": tournament.id,
            "name": tournament.name,
            "entry_fee": tournament.entry_fee,
            "prize_pool": tournament.total_prize_pool,
            "start_time": tournament.start_time.isoformat(),
            "registration_deadline": tournament.registration_deadline.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to create tournament: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/tournaments/{tournament_id}/join")
async def join_tournament(
    tournament_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Join tournament."""
    try:
        success = await game_variants.join_tournament(
            session=session,
            tournament_id=tournament_id,
            user_id=user_id
        )
        
        if success:
            return {"message": "Successfully joined tournament"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to join tournament"
            )
            
    except Exception as e:
        logger.error(f"Failed to join tournament: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/tournaments")
async def get_tournaments(
    session: AsyncSession = Depends(get_db_session)
):
    """Get active tournaments."""
    try:
        tournaments = await game_variants.get_active_tournaments(session)
        return {"tournaments": tournaments}
        
    except Exception as e:
        logger.error(f"Failed to get tournaments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tournaments"
        )


@router.get("/tournaments/{tournament_id}/leaderboard")
async def get_tournament_leaderboard(
    tournament_id: str,
    limit: int = 50,
    session: AsyncSession = Depends(get_db_session)
):
    """Get tournament leaderboard."""
    try:
        leaderboard = await game_variants.get_tournament_leaderboard(
            session=session,
            tournament_id=tournament_id,
            limit=limit
        )
        
        return {"leaderboard": leaderboard}
        
    except Exception as e:
        logger.error(f"Failed to get tournament leaderboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tournament leaderboard"
        )


# ==================== PRICE PREDICTION GAMES ====================

@router.post("/price-prediction")
async def create_price_prediction(
    request: PricePredictionRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Create price prediction game."""
    try:
        game = await game_variants.create_price_prediction_game(
            session=session,
            user_id=user_id,
            crypto_id=request.crypto_id,
            prediction_direction=request.prediction_direction,
            bet_amount=request.bet_amount,
            prediction_duration=request.prediction_duration
        )
        
        return {
            "game_id": game.id,
            "crypto_symbol": game.crypto_symbol,
            "prediction": game.prediction_direction,
            "start_price": game.start_price,
            "bet_amount": game.bet_amount,
            "potential_payout": game.potential_payout,
            "prediction_deadline": game.prediction_deadline.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to create price prediction: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/price-prediction/{game_id}/result")
async def get_price_prediction_result(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get price prediction game result."""
    try:
        result = await game_variants.resolve_price_prediction_game(
            session=session,
            game_id=game_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get price prediction result: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== GAME INFO ENDPOINTS ====================

@router.get("/wheel-info")
async def get_wheel_info():
    """Get crypto roulette wheel information."""
    from gaming.models import CryptoRouletteWheel
    
    return {
        "total_positions": 37,
        "positions": CryptoRouletteWheel.WHEEL_POSITIONS,
        "red_numbers": CryptoRouletteWheel.RED_NUMBERS,
        "black_numbers": CryptoRouletteWheel.BLACK_NUMBERS,
        "green_numbers": CryptoRouletteWheel.GREEN_NUMBERS,
        "house_edge": 2.7
    }


@router.get("/bet-types")
async def get_bet_types():
    """Get available bet types and their payouts."""
    from gaming.models import RoulettePayouts
    
    return {
        "bet_types": {
            "SINGLE_CRYPTO": {
                "description": "Bet on specific cryptocurrency",
                "payout": "35:1",
                "example": "bitcoin"
            },
            "CRYPTO_COLOR": {
                "description": "Bet on red/black/green",
                "payout": "1:1 (red/black), 35:1 (green)",
                "example": "red"
            },
            "CRYPTO_CATEGORY": {
                "description": "Bet on crypto category",
                "payout": "2:1",
                "example": "defi"
            },
            "EVEN_ODD": {
                "description": "Bet on even or odd numbers",
                "payout": "1:1",
                "example": "even"
            },
            "HIGH_LOW": {
                "description": "Bet on high (19-36) or low (1-18)",
                "payout": "1:1", 
                "example": "high"
            }
        },
        "payout_odds": RoulettePayouts.PAYOUT_ODDS
    }


# ==================== ENHANCED ROULETTE ENDPOINTS ====================

@router.post("/gaming/roulette/place_bet")
async def place_roulette_bet(
    request: PlaceBetRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Place bet on roulette game - Enhanced endpoint for JavaScript."""
    try:
        # Create or get active game session for user
        game_session = await roulette_engine.get_or_create_active_session(
            session=session,
            user_id=user_id,
            game_type=GameType.CRYPTO_ROULETTE
        )
        
        bet_type = BetType(request.bet_type)
        
        game_bet = await roulette_engine.place_bet(
            session=session,
            game_session_id=game_session.id,
            user_id=user_id,
            bet_type=bet_type,
            bet_value=request.bet_value,
            bet_amount=request.bet_amount
        )
        
        # Get updated user balance
        from database import User
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        
        return {
            "success": True,
            "bet_id": game_bet.id,
            "bet_type": game_bet.bet_type,
            "bet_value": game_bet.bet_value,
            "amount": game_bet.bet_amount,
            "potential_payout": game_bet.potential_payout,
            "odds": game_bet.payout_odds,
            "new_balance": user.current_balance if hasattr(user, 'current_balance') else 1000,
            "game_id": game_session.id,
            "placed_at": game_bet.placed_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to place roulette bet: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/gaming/roulette/spin")
async def spin_roulette_wheel(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Spin roulette wheel and get results - Enhanced endpoint for JavaScript."""
    try:
        # Get user's active game session
        game_session = await roulette_engine.get_active_session(
            session=session,
            user_id=user_id
        )
        
        if not game_session:
            return {
                "success": False,
                "error": "No active game session found. Please place a bet first."
            }
        
        # Spin the wheel
        result = await roulette_engine.spin_wheel(
            session=session,
            game_session_id=game_session.id,
            user_id=user_id
        )
        
        # Trigger achievement checks
        won_game = result["total_winnings"] > result["total_bet"]
        
        await achievement_engine.check_user_achievements(
            session, user_id, "game_played", 
            {"game_id": game_session.id, "won": won_game}
        )
        
        if won_game:
            await achievement_engine.check_user_achievements(
                session, user_id, "game_won", 
                {"game_id": game_session.id, "winnings": result["total_winnings"]}
            )
        
        # Get updated user balance
        from database import User
        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one()
        
        return {
            "success": True,
            "winning_number": result["winning_number"],
            "payouts": result.get("payouts", []),
            "total_payout": result["total_winnings"],
            "total_bet": result["total_bet"],
            "net_result": result["total_winnings"] - result["total_bet"],
            "new_balance": user.current_balance if hasattr(user, 'current_balance') else 1000,
            "server_seed": result.get("server_seed"),
            "client_seed": result.get("client_seed"),
            "nonce": result.get("nonce"),
            "game_id": game_session.id
        }
        
    except Exception as e:
        logger.error(f"Failed to spin roulette wheel: {e}")
        return {
            "success": False,
            "error": str(e)
        }