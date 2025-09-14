"""
Gaming API endpoints for roulette and casino games.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

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


async def get_optional_user_id(
    request: Request,
    session: AsyncSession = Depends(get_db_session)
) -> Optional[str]:
    """Optionally resolve user ID from Authorization header if present.

    Returns None when no valid bearer token is provided.
    """
    try:
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            if token:
                user = await auth_manager.get_user_by_token(session, token)
                if user:
                    return user.id
    except Exception as e:
        # Log at warning level; this is an optional resolver
        try:
            logger.warning(f"Optional user resolution failed: {e}")
        except Exception:
            pass
    return None


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


# ==================== BALANCE MANAGEMENT ENDPOINTS ====================

@router.get("/gaming/roulette/balance")
async def get_roulette_balance(
    request: Request,
    user_id: Optional[str] = Depends(get_optional_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get user's current balance - supporting both authenticated and demo mode with enhanced persistence."""
    try:
        # Demo mode handling with improved persistence chain
        if not user_id:
            demo_balance = 5000.0  # Default demo balance
            persistence_source = "default"

            # Priority chain: Session → Cookie → LocalStorage hint → Default
            session_data = request.session if hasattr(request, 'session') else {}
            stored_session = None
            if isinstance(session_data, dict):
                stored_session = session_data.get('demo_balance')

            # Cookie fallback with better validation
            stored_cookie = request.cookies.get('cc_demo_balance')
            
            # Check for localStorage hint in headers (added by frontend)
            localStorage_hint = request.headers.get('x-demo-balance-hint')

            # Apply persistence chain
            if stored_session is not None:
                try:
                    demo_balance = max(0.0, float(stored_session))
                    persistence_source = "session"
                except (ValueError, TypeError):
                    pass
            elif stored_cookie is not None:
                try:
                    demo_balance = max(0.0, float(stored_cookie))
                    persistence_source = "cookie"
                except (ValueError, TypeError):
                    pass
            elif localStorage_hint is not None:
                try:
                    demo_balance = max(0.0, float(localStorage_hint))
                    persistence_source = "localStorage"
                except (ValueError, TypeError):
                    pass

            # Enhanced response with persistence metadata
            from fastapi.responses import JSONResponse
            content = {
                "status": "success",
                "data": {
                    "balance": demo_balance,
                    "is_demo_mode": True,
                    "currency": "GEM",
                    "persistence_source": persistence_source,
                    "should_sync_frontend": True
                }
            }
            response = JSONResponse(content)
            
            # Always update both session and cookie for redundancy
            try:
                if hasattr(request, 'session'):
                    request.session['demo_balance'] = demo_balance
                    request.session['gem_coins'] = demo_balance
                    request.session['balance_last_update'] = datetime.utcnow().isoformat()
                
                # Set cookie with extended expiration and proper flags
                response.set_cookie(
                    key='cc_demo_balance', 
                    value=str(demo_balance), 
                    max_age=60*60*24*90,  # 90 days for better persistence
                    samesite='lax',
                    httponly=False,  # Allow JavaScript access for sync
                    secure=False  # Set to True in production with HTTPS
                )
                
                # Additional cookie for balance update timestamp
                response.set_cookie(
                    key='cc_demo_balance_updated', 
                    value=datetime.utcnow().isoformat(), 
                    max_age=60*60*24*90, 
                    samesite='lax'
                )
            except Exception as e:
                logger.warning(f"Failed to set demo balance persistence: {e}")
            
            return response
        
        # Authenticated user handling
        from database.unified_models import User
        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        balance = user.current_balance if hasattr(user, 'current_balance') else getattr(user, 'gems', 1000)
        
        return {
            "status": "success",
            "data": {
                "balance": balance,
                "is_demo_mode": False,
                "currency": "GEM"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get balance: {e}")
        return {
            "status": "error",
            "error": str(e),
            "data": {
                "balance": 1000,  # Fallback balance
                "is_demo_mode": True,
                "currency": "GEM"
            }
        }


@router.post("/gaming/roulette/update_balance")
async def update_roulette_balance(
    request: Request,
    balance_data: dict,
    user_id: Optional[str] = Depends(get_optional_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Update user balance - enhanced demo mode persistence with validation."""
    try:
        new_balance = balance_data.get('balance', 5000)
        
        # Validate balance value
        try:
            new_balance = max(0.0, float(new_balance))
        except (ValueError, TypeError):
            new_balance = 5000.0  # Reset to default on invalid value
        
        # Demo mode handling - enhanced persistence
        if not user_id:
            from fastapi.responses import JSONResponse
            
            # Store in session with metadata
            if hasattr(request, 'session'):
                request.session['demo_balance'] = new_balance
                request.session['gem_coins'] = new_balance  # Compatibility alias
                request.session['balance_last_update'] = datetime.utcnow().isoformat()
                request.session['balance_update_count'] = request.session.get('balance_update_count', 0) + 1
            
            content = {
                "status": "success",
                "data": {
                    "balance": new_balance,
                    "is_demo_mode": True,
                    "updated_at": datetime.utcnow().isoformat(),
                    "sync_frontend": True
                },
                "message": "Demo balance updated successfully"
            }
            resp = JSONResponse(content)
            
            # Enhanced cookie persistence
            try:
                resp.set_cookie(
                    key='cc_demo_balance', 
                    value=str(new_balance), 
                    max_age=60*60*24*90,  # 90 days
                    samesite='lax',
                    httponly=False,  # Allow JS access for sync
                    secure=False  # Set to True in production
                )
                resp.set_cookie(
                    key='cc_demo_balance_updated', 
                    value=datetime.utcnow().isoformat(), 
                    max_age=60*60*24*90, 
                    samesite='lax'
                )
                logger.info(f"Updated demo balance to {new_balance} GEM with enhanced persistence")
            except Exception as e:
                logger.error(f"Failed to set demo balance cookies: {e}")
            
            return resp
        
        # Authenticated users - balance is handled by roulette engine
        return {
            "status": "success",
            "data": {
                "balance": new_balance,
                "is_demo_mode": False
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to update balance: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.post("/gaming/roulette/sync_balance")
async def sync_demo_balance(
    request: Request,
    balance_data: dict,
    user_id: Optional[str] = Depends(get_optional_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Synchronize balance between frontend localStorage and server persistence for demo users."""
    try:
        # Only for demo users
        if user_id:
            return {
                "status": "skipped",
                "message": "Authenticated users don't need balance sync",
                "data": {"is_demo_mode": False}
            }
        
        frontend_balance = balance_data.get('frontend_balance')
        action = balance_data.get('action', 'sync')  # sync, restore, save
        
        if action == 'restore':
            # Frontend wants to restore from server
            demo_balance = 5000.0  # Default
            
            # Check server-side sources
            session_data = request.session if hasattr(request, 'session') else {}
            if isinstance(session_data, dict) and 'demo_balance' in session_data:
                try:
                    demo_balance = float(session_data['demo_balance'])
                except (ValueError, TypeError):
                    pass
            else:
                # Check cookie
                stored_cookie = request.cookies.get('cc_demo_balance')
                if stored_cookie:
                    try:
                        demo_balance = float(stored_cookie)
                    except (ValueError, TypeError):
                        pass
            
            return {
                "status": "success",
                "action": "balance_restored",
                "data": {
                    "balance": demo_balance,
                    "source": "server",
                    "is_demo_mode": True
                }
            }
        
        elif action == 'save' and frontend_balance is not None:
            # Frontend wants to save its current balance to server
            try:
                save_balance = max(0.0, float(frontend_balance))
            except (ValueError, TypeError):
                return {
                    "status": "error",
                    "message": "Invalid balance value provided"
                }
            
            # Save to server persistence
            from fastapi.responses import JSONResponse
            if hasattr(request, 'session'):
                request.session['demo_balance'] = save_balance
                request.session['gem_coins'] = save_balance
                request.session['balance_last_sync'] = datetime.utcnow().isoformat()
            
            content = {
                "status": "success",
                "action": "balance_saved",
                "data": {
                    "balance": save_balance,
                    "saved_at": datetime.utcnow().isoformat(),
                    "is_demo_mode": True
                }
            }
            resp = JSONResponse(content)
            
            # Update cookie
            try:
                resp.set_cookie(
                    key='cc_demo_balance', 
                    value=str(save_balance), 
                    max_age=60*60*24*90, 
                    samesite='lax',
                    httponly=False
                )
            except Exception as e:
                logger.warning(f"Failed to update demo balance cookie: {e}")
            
            return resp
        
        else:
            return {
                "status": "error",
                "message": "Invalid sync action or missing data"
            }
        
    except Exception as e:
        logger.error(f"Failed to sync demo balance: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Balance synchronization failed"
        }


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

async def get_optional_user_id(
    request: Request,
    session: AsyncSession = Depends(get_db_session)
) -> Optional[str]:
    """Get user ID if authenticated, otherwise return None for demo mode."""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
            
        token = auth_header.replace("Bearer ", "")
        if token in ["null", "undefined", ""]:
            return None
            
        user = await auth_manager.get_user_by_token(session, token)
        return user.id if user else None
    except Exception:
        return None

@router.post("/gaming/roulette/place_bet")
async def place_roulette_bet(
    request: PlaceBetRequest,
    http_request: Request,
    user_id: Optional[str] = Depends(get_optional_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Place bet on roulette game - Enhanced endpoint with demo mode support."""
    try:
        # Demo mode handling
        if not user_id:
            import time
            demo_bet_id = f"demo-bet-{int(time.time())}"

            # Calculate potential payout for demo
            bet_amount = request.bet_amount or getattr(request, 'amount', None) or 10
            try:
                bet_amount = float(bet_amount)
            except Exception:
                bet_amount = 10.0
            if bet_amount < 0:
                bet_amount = 0.0

            payout_multiplier = {
                'number': 35,
                'color': 2,
                'category': 3,
                'traditional': 2
            }.get(request.bet_type, 2)

            # Load current demo balance and accumulate pending bet (no immediate deduction)
            current_balance = 5000.0
            try:
                if hasattr(http_request, 'session') and isinstance(http_request.session, dict):
                    stored = http_request.session.get('demo_balance')
                    if stored is not None:
                        current_balance = float(stored)
                    pending = float(http_request.session.get('demo_pending_bet', 0) or 0)
                    pending += bet_amount
                    http_request.session['demo_pending_bet'] = pending
            except Exception:
                pass

            # Do NOT change balance here; update on spin result
            new_balance = current_balance

            return {
                "success": True,
                "bet_id": demo_bet_id,
                "bet_type": request.bet_type,
                "bet_value": request.bet_value,
                "amount": bet_amount,
                "potential_payout": bet_amount * payout_multiplier,
                "odds": payout_multiplier,
                "new_balance": new_balance,
                "game_id": "demo-session",
                "placed_at": "2025-01-13T00:00:00Z",
                "demo_mode": True,
                "apply_balance_after_spin": True
            }
        
        # Authenticated user handling
        game_session = await roulette_engine.get_or_create_active_session(
            session=session,
            user_id=user_id,
            game_type=GameType.CRYPTO_ROULETTE
        )
        
        bet_type = BetType(request.bet_type)
        bet_amount = request.bet_amount or request.amount or 10
        
        game_bet = await roulette_engine.place_bet(
            session=session,
            game_session_id=game_session.id,
            user_id=user_id,
            bet_type=bet_type,
            bet_value=request.bet_value,
            bet_amount=bet_amount
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
            "placed_at": game_bet.placed_at.isoformat(),
            "demo_mode": False
        }
        
    except Exception as e:
        logger.error(f"Failed to place roulette bet: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to place bet: {str(e)}"
        )


@router.post("/gaming/roulette/spin")
async def spin_roulette_wheel(
    request: Request,
    user_id: Optional[str] = Depends(get_optional_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Spin roulette wheel and get results - Enhanced endpoint with demo mode support."""
    try:
        # Demo mode handling for spin
        if not user_id:
            import random
            
            # Get request body to access bet information
            request_body = await request.json() if request.method == 'POST' else {}
            demo_bets = request_body.get('bets', [])
            
            # Generate demo spin result
            winning_number = random.randint(0, 36)
            
            # Define color mapping for demo mode
            RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
            BLACK_NUMBERS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
            
            if winning_number == 0:
                winning_color = 'green'
            elif winning_number in RED_NUMBERS:
                winning_color = 'red'
            else:
                winning_color = 'black'
            
            # Get current demo balance from session or fallback
            current_balance = 5000  # Default demo balance
            try:
                session_data = request.session if hasattr(request, 'session') else {}
                stored_demo_balance = session_data.get('demo_balance')
                if stored_demo_balance:
                    current_balance = float(stored_demo_balance)
            except:
                pass

            # Calculate demo payouts based on actual bets placed
            total_bet = sum(bet.get('amount', 0) for bet in demo_bets)
            total_payout = 0
            winning_bets = []
            
            # Process each bet to calculate payouts
            for bet in demo_bets:
                bet_type = bet.get('type', '')
                bet_value = bet.get('value', '')
                bet_amount = bet.get('amount', 0)
                payout = 0
                
                # Check if bet wins
                if bet_type == 'number' and str(bet_value) == str(winning_number):
                    payout = bet_amount * 35  # 35:1 payout for single number
                elif bet_type == 'color' and bet_value == winning_color:
                    if winning_color == 'green':
                        payout = bet_amount * 14  # 14:1 for green
                    else:
                        payout = bet_amount * 2   # 2:1 for red/black
                elif bet_type == 'traditional':
                    if (bet_value == 'even' and winning_number != 0 and winning_number % 2 == 0) or \
                       (bet_value == 'odd' and winning_number != 0 and winning_number % 2 == 1) or \
                       (bet_value == 'high' and winning_number >= 19) or \
                       (bet_value == 'low' and 1 <= winning_number <= 18):
                        payout = bet_amount * 2   # 2:1 for traditional bets
                
                if payout > 0:
                    winning_bets.append({
                        'type': bet_type,
                        'value': bet_value,
                        'amount': bet_amount,
                        'payout': payout
                    })
                    total_payout += payout
            
            # Update demo balance: deduct total_bet then add winnings
            new_balance = current_balance - total_bet + total_payout
            if new_balance < 0:
                new_balance = 0

            # Store updated balance in session and persistent cookie
            from fastapi.responses import JSONResponse
            try:
                if hasattr(request, 'session'):
                    request.session['demo_balance'] = new_balance
                    request.session['gem_coins'] = new_balance
                    # Clear or reduce pending bet tracker
                    pending = float(request.session.get('demo_pending_bet', 0) or 0)
                    pending = max(0.0, pending - total_bet)
                    request.session['demo_pending_bet'] = pending
            except Exception:
                pass

            # Calculate net winnings (profit) for better UX
            net_winnings = total_payout - total_bet if total_payout > 0 else 0

            content = {
                "success": True,
                "data": {
                    "winning_number": winning_number,
                    "winning_color": winning_color,
                    "winning_bets": winning_bets,
                    "total_payout": total_payout,
                    "net_winnings": net_winnings,  # Show actual profit, not total payout
                    "total_bet": total_bet,
                    "new_balance": new_balance,
                    "is_winner": total_payout > 0,
                    "demo_mode": True
                }
            }
            resp = JSONResponse(content)
            try:
                resp.set_cookie('cc_demo_balance', str(new_balance), max_age=60*60*24*30, samesite='lax')
            except Exception:
                pass
            return resp
        
        # Authenticated user handling
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
        
        # Spin the wheel - this should NOT deduct balance again (already deducted on bet placement)
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
        from database.unified_models import User
        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one()
        
        # Calculate net winnings (profit) for better UX
        total_winnings = result["total_winnings"]
        total_bet = result["total_bet"]
        net_winnings = total_winnings - total_bet if total_winnings > 0 else 0

        return {
            "success": True,
            "data": {
                "winning_number": result["winning_number"],
                "winning_bets": result.get("payouts", []),
                "total_payout": total_winnings,
                "net_winnings": net_winnings,  # Show actual profit, not total payout
                "total_bet": total_bet,
                "new_balance": user.current_balance if hasattr(user, 'current_balance') else 1000,
                "server_seed": result.get("server_seed"),
                "client_seed": result.get("client_seed"),
                "nonce": result.get("nonce"),
                "is_winner": won_game,
                "demo_mode": False
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to spin roulette wheel: {e}")
        return {
            "success": False,
            "error": str(e)
        }
