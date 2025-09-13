"""
WebSocket endpoints for real-time roulette gaming.
Enhanced with crypto-inspired real-time features.
"""

import json
import asyncio
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.database_manager import get_db_session
from gaming.websocket_manager import websocket_manager
from gaming.roulette_engine import RouletteEngine
from auth.auth_manager import AuthenticationManager
from logger import logger


auth_manager = AuthenticationManager()
roulette_engine = RouletteEngine()


async def authenticate_websocket(websocket: WebSocket) -> tuple[str, str, str]:
    """Authenticate WebSocket connection and return user info."""
    
    # Get token from query params
    token = websocket.query_params.get("token")
    if not token or token == "undefined":
        # Demo mode - return demo user info
        return "demo-user-123", "DemoPlayer", "demo@cryptochecker.com"
    
    # Verify token and get user for real authentication
    try:
        async with get_db_session() as session:
            user = await auth_manager.get_user_by_token(session, token)
            if not user:
                # Fallback to demo mode
                logger.warning(f"Invalid token {token}, falling back to demo mode")
                return "demo-user-123", "DemoPlayer", "demo@cryptochecker.com"
            
            return user.id, user.username, user.email
    except Exception as e:
        # If authentication fails, use demo mode
        logger.warning(f"Auth error: {e}, falling back to demo mode")
        return "demo-user-123", "DemoPlayer", "demo@cryptochecker.com"


async def websocket_roulette_game(websocket: WebSocket, session_id: str):
    """Enhanced WebSocket endpoint for real-time roulette gaming."""
    
    connection_id = None
    user_id = None
    
    try:
        # Authenticate user
        user_id, username, email = await authenticate_websocket(websocket)
        
        # Connect to game room
        connection_id = await websocket_manager.connect(
            websocket, session_id, user_id, username
        )
        
        logger.info(f"WebSocket connected: User {username} to session {session_id}")
        
        # Handle incoming messages
        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                await handle_websocket_message(
                    session_id, user_id, username, message
                )
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {username} from {session_id}")
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": asyncio.get_event_loop().time()
                })
            except Exception as e:
                logger.error(f"WebSocket error for {username}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Internal server error",
                    "timestamp": asyncio.get_event_loop().time()
                })
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    
    finally:
        # Clean up connection
        if connection_id:
            await websocket_manager.disconnect(connection_id)


async def handle_websocket_message(
    session_id: str,
    user_id: str,
    username: str,
    message: Dict[str, Any]
):
    """Handle incoming WebSocket messages with enhanced features."""
    
    message_type = message.get("type")
    
    if message_type == "place_live_bet":
        await handle_live_bet(session_id, user_id, message.get("bet_data", {}))
    
    elif message_type == "chat_message":
        await handle_chat_message(
            session_id, user_id, username, message.get("message", "")
        )
    
    elif message_type == "request_room_stats":
        await handle_room_stats_request(session_id, user_id)
    
    elif message_type == "request_game_history":
        await handle_game_history_request(session_id, user_id, message.get("limit", 10))
    
    elif message_type == "ping":
        await websocket_manager.send_to_user(user_id, {
            "type": "pong",
            "timestamp": asyncio.get_event_loop().time()
        })
    
    else:
        await websocket_manager.send_to_user(user_id, {
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": asyncio.get_event_loop().time()
        })


async def handle_live_bet(session_id: str, user_id: str, bet_data: Dict[str, Any]):
    """Handle live bet placement with validation."""
    
    try:
        # Validate bet through gaming engine first
        async with get_db_session() as session:
            # Check if game session is active and accepting bets
            game_bet = await roulette_engine.place_bet(
                session, session_id, user_id,
                BetType(bet_data["bet_type"]),
                bet_data["bet_value"],
                float(bet_data["bet_amount"])
            )
            
            # If successful, handle live bet through WebSocket manager
            await websocket_manager.handle_live_bet(session_id, user_id, {
                "bet_id": game_bet.id,
                "bet_type": bet_data["bet_type"],
                "bet_value": bet_data["bet_value"],
                "bet_amount": bet_data["bet_amount"],
                "potential_payout": game_bet.potential_payout
            })
    
    except Exception as e:
        logger.error(f"Live bet error for user {user_id}: {e}")
        await websocket_manager.send_to_user(user_id, {
            "type": "bet_error",
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time()
        })


async def handle_chat_message(
    session_id: str,
    user_id: str,
    username: str,
    message: str
):
    """Handle chat messages with basic filtering."""
    
    # Basic message validation
    if not message or len(message.strip()) == 0:
        return
    
    if len(message) > 200:
        await websocket_manager.send_to_user(user_id, {
            "type": "chat_error",
            "error": "Message too long (max 200 characters)",
            "timestamp": asyncio.get_event_loop().time()
        })
        return
    
    # Send chat message to room
    await websocket_manager.send_chat_message(
        session_id, user_id, username, message
    )


async def handle_room_stats_request(session_id: str, user_id: str):
    """Send current room statistics to user."""
    
    stats = websocket_manager.get_room_statistics(session_id)
    
    await websocket_manager.send_to_user(user_id, {
        "type": "room_stats",
        "stats": stats,
        "timestamp": asyncio.get_event_loop().time()
    })


async def handle_game_history_request(session_id: str, user_id: str, limit: int):
    """Send recent game history to user."""
    
    try:
        async with get_db_session() as session:
            history = await roulette_engine.get_user_game_history(
                session, user_id, limit=min(limit, 50)
            )
            
            await websocket_manager.send_to_user(user_id, {
                "type": "game_history",
                "history": history,
                "timestamp": asyncio.get_event_loop().time()
            })
    
    except Exception as e:
        logger.error(f"Game history error for user {user_id}: {e}")
        await websocket_manager.send_to_user(user_id, {
            "type": "error",
            "message": "Failed to retrieve game history",
            "timestamp": asyncio.get_event_loop().time()
        })


async def trigger_spin_sequence(session_id: str, winning_number: int):
    """Trigger enhanced wheel spinning sequence."""
    
    # Start the spin sequence with suspense
    await websocket_manager.start_spin_sequence(session_id, winning_number)


async def announce_game_results(session_id: str, result_data: Dict[str, Any]):
    """Announce game results to all room participants."""
    
    await websocket_manager.announce_results(session_id, result_data)


# Additional utility functions for integration

async def get_active_room_count() -> int:
    """Get number of active game rooms."""
    return len(websocket_manager.game_rooms)


async def get_total_active_users() -> int:
    """Get total number of active WebSocket connections."""
    return len(websocket_manager.active_connections)


async def broadcast_server_announcement(message: str):
    """Broadcast server-wide announcement to all connected users."""
    
    announcement = {
        "type": "server_announcement",
        "message": message,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    # Broadcast to all active sessions
    for session_id in websocket_manager.game_rooms.keys():
        await websocket_manager.broadcast_to_room(session_id, announcement)


async def emergency_shutdown_notifications():
    """Send emergency shutdown notifications to all users."""
    
    shutdown_message = {
        "type": "emergency_shutdown",
        "message": "Server maintenance in progress. Games will be restored shortly.",
        "timestamp": asyncio.get_event_loop().time()
    }
    
    # Notify all users
    for session_id in websocket_manager.game_rooms.keys():
        await websocket_manager.broadcast_to_room(session_id, shutdown_message)
    
    # Give users time to receive the message
    await asyncio.sleep(5)
    
    # Close all connections gracefully
    for connection_id in list(websocket_manager.active_connections.keys()):
        await websocket_manager.disconnect(connection_id)