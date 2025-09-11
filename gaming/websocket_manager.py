"""
Real-time WebSocket manager for live roulette gaming.
Enhanced with CS:GO-inspired real-time features and user interactions.
"""

import json
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Set, List, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from .models import GameSession, GameBet, GameStatus, BetType
from auth.models import User
from database import get_db_session
from logger import logger


class RouletteWebSocketManager:
    """Enhanced WebSocket manager for real-time roulette gaming."""
    
    def __init__(self):
        # Active WebSocket connections
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Game rooms - each game session has a room
        self.game_rooms: Dict[str, Set[str]] = {}
        
        # User presence tracking
        self.user_sessions: Dict[str, str] = {}  # user_id -> connection_id
        self.connection_users: Dict[str, str] = {}  # connection_id -> user_id
        
        # Live betting state
        self.live_bets: Dict[str, List[Dict]] = {}  # session_id -> live_bets
        self.betting_timers: Dict[str, asyncio.Task] = {}
        
        # Real-time statistics
        self.room_stats: Dict[str, Dict[str, Any]] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
        username: str
    ) -> str:
        """Connect user to a game room with enhanced tracking."""
        await websocket.accept()
        
        connection_id = f"{user_id}_{session_id}_{uuid.uuid4().hex[:8]}"
        
        # Store connection
        self.active_connections[connection_id] = websocket
        self.connection_users[connection_id] = user_id
        self.user_sessions[user_id] = connection_id
        
        # Add to game room
        if session_id not in self.game_rooms:
            self.game_rooms[session_id] = set()
            self.live_bets[session_id] = []
            self.room_stats[session_id] = {
                "total_viewers": 0,
                "total_bets": 0,
                "total_bet_amount": 0.0,
                "last_winners": [],
                "hot_numbers": {},
                "created_at": datetime.utcnow().isoformat()
            }
        
        self.game_rooms[session_id].add(connection_id)
        self.room_stats[session_id]["total_viewers"] = len(self.game_rooms[session_id])
        
        # Send initial room state
        await self._send_room_state(session_id, connection_id)
        
        # Notify room of new user
        await self.broadcast_to_room(session_id, {
            "type": "user_joined",
            "user_id": user_id,
            "username": username,
            "timestamp": datetime.utcnow().isoformat(),
            "total_viewers": len(self.game_rooms[session_id])
        }, exclude_user=user_id)
        
        logger.info(f"User {user_id} connected to game {session_id} - Connection: {connection_id}")
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Disconnect user and clean up state."""
        if connection_id not in self.active_connections:
            return
        
        user_id = self.connection_users.get(connection_id)
        
        # Find which room the user was in
        session_id = None
        for room_id, connections in self.game_rooms.items():
            if connection_id in connections:
                session_id = room_id
                connections.remove(connection_id)
                break
        
        # Clean up tracking
        del self.active_connections[connection_id]
        if connection_id in self.connection_users:
            del self.connection_users[connection_id]
        if user_id and user_id in self.user_sessions:
            del self.user_sessions[user_id]
        
        # Update room stats
        if session_id:
            self.room_stats[session_id]["total_viewers"] = len(self.game_rooms[session_id])
            
            # Notify room of user leaving
            if user_id:
                await self.broadcast_to_room(session_id, {
                    "type": "user_left",
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "total_viewers": len(self.game_rooms[session_id])
                })
        
        logger.info(f"Disconnected connection {connection_id} from session {session_id}")
    
    async def broadcast_to_room(
        self,
        session_id: str,
        message: Dict[str, Any],
        exclude_user: Optional[str] = None
    ):
        """Broadcast message to all users in a game room."""
        if session_id not in self.game_rooms:
            return
        
        disconnected_connections = []
        
        for connection_id in self.game_rooms[session_id].copy():
            # Skip excluded user
            user_id = self.connection_users.get(connection_id)
            if exclude_user and user_id == exclude_user:
                continue
            
            if connection_id in self.active_connections:
                try:
                    websocket = self.active_connections[connection_id]
                    await websocket.send_json(message)
                except WebSocketDisconnect:
                    disconnected_connections.append(connection_id)
                except Exception as e:
                    logger.error(f"Error sending to {connection_id}: {e}")
                    disconnected_connections.append(connection_id)
        
        # Clean up disconnected connections
        for conn_id in disconnected_connections:
            await self.disconnect(conn_id)
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to specific user."""
        if user_id not in self.user_sessions:
            return False
        
        connection_id = self.user_sessions[user_id]
        if connection_id not in self.active_connections:
            return False
        
        try:
            websocket = self.active_connections[connection_id]
            await websocket.send_json(message)
            return True
        except (WebSocketDisconnect, Exception) as e:
            logger.error(f"Error sending to user {user_id}: {e}")
            await self.disconnect(connection_id)
            return False
    
    async def handle_live_bet(
        self,
        session_id: str,
        user_id: str,
        bet_data: Dict[str, Any]
    ):
        """Handle live bet placement with real-time feedback."""
        
        # Validate bet data
        required_fields = ["bet_type", "bet_value", "bet_amount"]
        if not all(field in bet_data for field in required_fields):
            await self.send_to_user(user_id, {
                "type": "bet_error",
                "error": "Missing required bet fields",
                "timestamp": datetime.utcnow().isoformat()
            })
            return
        
        # Add bet to live tracking
        live_bet = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "bet_type": bet_data["bet_type"],
            "bet_value": bet_data["bet_value"],
            "bet_amount": float(bet_data["bet_amount"]),
            "timestamp": datetime.utcnow().isoformat(),
            "animation_delay": len(self.live_bets[session_id]) * 100  # Stagger animations
        }
        
        self.live_bets[session_id].append(live_bet)
        
        # Update room statistics
        self.room_stats[session_id]["total_bets"] += 1
        self.room_stats[session_id]["total_bet_amount"] += live_bet["bet_amount"]
        
        # Broadcast live bet to room
        await self.broadcast_to_room(session_id, {
            "type": "live_bet_placed",
            "bet": live_bet,
            "room_stats": self.room_stats[session_id],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Send confirmation to bet placer
        await self.send_to_user(user_id, {
            "type": "bet_confirmed",
            "bet_id": live_bet["id"],
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def start_spin_sequence(
        self,
        session_id: str,
        winning_number: int,
        spin_duration: int = 5000
    ):
        """Start enhanced wheel spinning sequence with suspense."""
        
        # Phase 1: Betting closed, prepare for spin
        await self.broadcast_to_room(session_id, {
            "type": "betting_closed",
            "message": "No more bets! Spinning the wheel...",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        await asyncio.sleep(1)
        
        # Phase 2: Wheel spinning begins
        await self.broadcast_to_room(session_id, {
            "type": "wheel_spinning",
            "winning_number": winning_number,
            "spin_duration": spin_duration,
            "live_bets": self.live_bets[session_id],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Phase 3: Suspense countdown (optional sound effects trigger)
        await asyncio.sleep(spin_duration / 1000 - 1)
        
        await self.broadcast_to_room(session_id, {
            "type": "wheel_slowing",
            "message": "Wheel is slowing down...",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        await asyncio.sleep(1)
    
    async def announce_results(
        self,
        session_id: str,
        result_data: Dict[str, Any]
    ):
        """Announce game results with celebration effects."""
        
        winning_number = result_data["winning_number"]
        winning_crypto = result_data["winning_crypto"]
        
        # Update hot numbers tracking
        if "hot_numbers" not in self.room_stats[session_id]:
            self.room_stats[session_id]["hot_numbers"] = {}
        
        hot_numbers = self.room_stats[session_id]["hot_numbers"]
        hot_numbers[str(winning_number)] = hot_numbers.get(str(winning_number), 0) + 1
        
        # Track recent winners
        if "last_winners" not in self.room_stats[session_id]:
            self.room_stats[session_id]["last_winners"] = []
        
        self.room_stats[session_id]["last_winners"].insert(0, {
            "number": winning_number,
            "crypto": winning_crypto,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only last 10 winners
        self.room_stats[session_id]["last_winners"] = \
            self.room_stats[session_id]["last_winners"][:10]
        
        # Broadcast results
        await self.broadcast_to_room(session_id, {
            "type": "game_results",
            "result_data": result_data,
            "room_stats": self.room_stats[session_id],
            "celebration_effects": self._get_celebration_effects(result_data),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Send individual results to each user
        for bet in self.live_bets[session_id]:
            user_id = bet["user_id"]
            is_winner = self._check_bet_winner(bet, result_data)
            
            await self.send_to_user(user_id, {
                "type": "personal_result",
                "bet_id": bet["id"],
                "is_winner": is_winner,
                "payout": bet["bet_amount"] * 35 if is_winner else 0,  # Simplified
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Clear live bets for next round
        self.live_bets[session_id] = []
    
    async def send_chat_message(
        self,
        session_id: str,
        user_id: str,
        username: str,
        message: str
    ):
        """Send chat message to room."""
        
        # Basic message filtering (could be enhanced)
        if len(message.strip()) == 0 or len(message) > 200:
            return
        
        chat_message = {
            "type": "chat_message",
            "user_id": user_id,
            "username": username,
            "message": message.strip(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_room(session_id, chat_message)
    
    def get_room_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive room statistics."""
        if session_id not in self.room_stats:
            return {}
        
        stats = self.room_stats[session_id].copy()
        stats["live_bets_count"] = len(self.live_bets.get(session_id, []))
        stats["active_users"] = len(self.game_rooms.get(session_id, set()))
        
        return stats
    
    async def _send_room_state(self, session_id: str, connection_id: str):
        """Send current room state to newly connected user."""
        
        websocket = self.active_connections[connection_id]
        
        room_state = {
            "type": "room_state",
            "session_id": session_id,
            "live_bets": self.live_bets.get(session_id, []),
            "room_stats": self.room_stats.get(session_id, {}),
            "active_users": len(self.game_rooms.get(session_id, set())),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            await websocket.send_json(room_state)
        except Exception as e:
            logger.error(f"Error sending room state: {e}")
    
    def _get_celebration_effects(self, result_data: Dict[str, Any]) -> List[str]:
        """Generate celebration effects based on results."""
        effects = []
        
        # Big win celebration
        if result_data.get("total_winnings", 0) > result_data.get("total_bet", 0) * 10:
            effects.append("big_win")
        
        # Bitcoin win (special effect)
        if result_data.get("winning_number") == 0:
            effects.append("bitcoin_win")
        
        # Multiple winners
        if result_data.get("winning_bets", 0) > 5:
            effects.append("multiple_winners")
        
        return effects
    
    def _check_bet_winner(self, bet: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        """Quick bet winner check for live feedback."""
        bet_type = bet["bet_type"]
        bet_value = bet["bet_value"]
        winning_details = result_data.get("winning_details", {})
        
        if bet_type == "SINGLE_CRYPTO":
            return winning_details.get("single_crypto") == bet_value
        elif bet_type == "CRYPTO_COLOR":
            return winning_details.get("color") == bet_value
        elif bet_type == "CRYPTO_CATEGORY":
            return winning_details.get("category") == bet_value
        elif bet_type == "EVEN_ODD":
            return winning_details.get("even_odd") == bet_value
        elif bet_type == "HIGH_LOW":
            return winning_details.get("high_low") == bet_value
        
        return False


# Global WebSocket manager instance
websocket_manager = RouletteWebSocketManager()