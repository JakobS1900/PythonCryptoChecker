"""
Crash Game API

REST and WebSocket endpoints for the crash game.
"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import User
from api.auth_api import require_authentication
from services.crash_service import CrashGameService
from services.crash_game_manager import crash_manager


router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class PlaceBetRequest(BaseModel):
    """Request model for placing a bet."""
    bet_amount: int


class CashoutRequest(BaseModel):
    """Request model for cashing out."""
    pass


class PlaceBetResponse(BaseModel):
    """Response model for placing a bet."""
    success: bool
    bet_id: Optional[int]
    game_id: int
    bet_amount: int
    new_balance: int
    message: str


class CashoutResponse(BaseModel):
    """Response model for cashing out."""
    success: bool
    cashout_multiplier: float
    bet_amount: int
    payout: int
    profit: int
    new_balance: int
    message: str


class GameStateResponse(BaseModel):
    """Response model for current game state."""
    game_id: Optional[int]
    status: str
    multiplier: Optional[float]
    crash_point: Optional[float]
    server_seed_hash: Optional[str]


# ============================================================================
# REST ENDPOINTS
# ============================================================================

@router.get("/current", response_model=GameStateResponse)
async def get_current_game(db: AsyncSession = Depends(get_db)):
    """
    Get the current active game state.
    """
    state = crash_manager.get_current_state()

    return GameStateResponse(
        game_id=state.get('game_id'),
        status=state.get('status', 'no_game'),
        multiplier=state.get('multiplier'),
        crash_point=state.get('crash_point'),
        server_seed_hash=state.get('server_seed_hash')
    )


@router.post("/bet", response_model=PlaceBetResponse)
async def place_bet(
    request: PlaceBetRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Place a bet on the current game.

    - **bet_amount**: Amount to bet (100-100,000 GEM)
    """
    try:
        # Get current game
        game = await CrashGameService.get_current_game(db)

        if not game or game.status not in ['waiting', 'starting']:
            return PlaceBetResponse(
                success=False,
                bet_id=None,
                game_id=0,
                bet_amount=request.bet_amount,
                new_balance=current_user.gem_balance,
                message="Cannot bet on game in progress"
            )

        # Place bet
        result = await CrashGameService.place_bet(
            user_id=current_user.id,
            bet_amount=request.bet_amount,
            game_id=game.id,
            db=db
        )

        # Broadcast bet to all clients
        await crash_manager.broadcast({
            "type": "bet_placed",
            "username": current_user.username,
            "bet_amount": request.bet_amount,
            "game_id": game.id
        })

        return PlaceBetResponse(
            success=True,
            bet_id=result['bet_id'],
            game_id=result['game_id'],
            bet_amount=result['bet_amount'],
            new_balance=result['new_balance'],
            message=result['message']
        )

    except ValueError as e:
        return PlaceBetResponse(
            success=False,
            bet_id=None,
            game_id=0,
            bet_amount=request.bet_amount,
            new_balance=current_user.gem_balance,
            message=str(e)
        )


@router.post("/cashout", response_model=CashoutResponse)
async def cashout(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Cash out at the current multiplier.
    """
    try:
        # Get current game state
        state = crash_manager.get_current_state()

        if state.get('status') != 'playing':
            return CashoutResponse(
                success=False,
                cashout_multiplier=0.0,
                bet_amount=0,
                payout=0,
                profit=0,
                new_balance=current_user.gem_balance,
                message="No active game to cash out"
            )

        current_multiplier = crash_manager.current_multiplier

        # Cash out
        result = await CrashGameService.cashout(
            user_id=current_user.id,
            game_id=state['game_id'],
            current_multiplier=current_multiplier,
            db=db
        )

        # Broadcast cashout to all clients
        await crash_manager.broadcast({
            "type": "cashout",
            "username": current_user.username,
            "multiplier": current_multiplier,
            "payout": result['payout']
        })

        return CashoutResponse(
            success=True,
            cashout_multiplier=result['cashout_multiplier'],
            bet_amount=result['bet_amount'],
            payout=result['payout'],
            profit=result['profit'],
            new_balance=result['new_balance'],
            message=result['message']
        )

    except ValueError as e:
        return CashoutResponse(
            success=False,
            cashout_multiplier=0.0,
            bet_amount=0,
            payout=0,
            profit=0,
            new_balance=current_user.gem_balance,
            message=str(e)
        )


@router.get("/history")
async def get_history(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent crash game history.

    - **limit**: Number of games to return (default 10)
    """
    games = await CrashGameService.get_recent_games(db, limit)

    return {
        "success": True,
        "games": games
    }


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket connection for real-time game updates.

    Sends real-time updates for:
    - Game state changes (waiting, starting, playing, crashed)
    - Multiplier updates during gameplay
    - Bet placements by all players
    - Cashouts by all players
    - Game crash events
    """
    await websocket.accept()

    # Add client to manager
    crash_manager.add_client(websocket)

    try:
        # Send current game state immediately
        current_state = crash_manager.get_current_state()
        await websocket.send_json({
            "type": "connection_established",
            "current_state": current_state
        })

        # Keep connection alive and handle incoming messages
        while True:
            # Wait for messages from client
            data = await websocket.receive_json()

            # Handle client messages if needed (e.g., ping/pong)
            if data.get('type') == 'ping':
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    finally:
        # Remove client from manager
        crash_manager.remove_client(websocket)
