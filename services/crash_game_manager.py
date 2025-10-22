"""
Crash Game Manager

Manages automatic crash game rounds in the background.
Handles timing, multiplier progression, and game state.
"""

import asyncio
from datetime import datetime
from typing import Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import CrashGame
from services.crash_service import CrashGameService


class CrashGameManager:
    """Manages automatic crash game rounds."""

    def __init__(self):
        self.current_game: Optional[CrashGame] = None
        self.current_multiplier: float = 1.00
        self.is_running: bool = False
        self.task: Optional[asyncio.Task] = None
        self.connected_clients: Set = set()

    async def start(self):
        """Start the game manager."""
        if self.is_running:
            return

        self.is_running = True
        self.task = asyncio.create_task(self._game_loop())
        print("[Crash Manager] Started")

    async def stop(self):
        """Stop the game manager."""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        print("[Crash Manager] Stopped")

    async def _game_loop(self):
        """Main game loop that runs continuously."""
        while self.is_running:
            try:
                # Create new game
                async for db in get_db():
                    self.current_game = await CrashGameService.create_game(db)
                    break

                # Phase 1: Waiting for bets (10 seconds)
                print(f"[Crash Manager] Game #{self.current_game.id} - Betting phase (10s)")
                await self._betting_phase()

                # Phase 2: Starting (2 second countdown)
                print(f"[Crash Manager] Game #{self.current_game.id} - Starting in 2s...")
                await self._starting_phase()

                # Phase 3: Playing (multiplier increases until crash)
                print(f"[Crash Manager] Game #{self.current_game.id} - Playing!")
                await self._playing_phase()

                # Phase 4: Crashed (show result for 3 seconds)
                print(f"[Crash Manager] Game #{self.current_game.id} - Crashed at {self.current_game.crash_point:.2f}x")
                await self._crashed_phase()

                # Small delay before next round
                await asyncio.sleep(2)

            except Exception as e:
                print(f"[Crash Manager] Error in game loop: {e}")
                await asyncio.sleep(5)

    async def _betting_phase(self):
        """Betting phase - players can place bets."""
        async for db in get_db():
            self.current_game.status = 'waiting'
            await db.commit()
            break

        # Broadcast game state
        await self.broadcast({
            "type": "game_state",
            "game_id": self.current_game.id,
            "status": "waiting",
            "server_seed_hash": self.current_game.server_seed_hash
        })

        # Wait for betting duration
        await asyncio.sleep(CrashGameService.BETTING_DURATION)

    async def _starting_phase(self):
        """Starting phase - countdown before game starts."""
        async for db in get_db():
            self.current_game.status = 'starting'
            await db.commit()
            break

        # Broadcast starting
        await self.broadcast({
            "type": "game_state",
            "game_id": self.current_game.id,
            "status": "starting"
        })

        # 2 second countdown
        await asyncio.sleep(2)

    async def _playing_phase(self):
        """Playing phase - multiplier increases until crash."""
        # Generate crash point
        crash_point = CrashGameService.generate_crash_point(self.current_game.server_seed)

        async for db in get_db():
            self.current_game.status = 'playing'
            self.current_game.crash_point = crash_point
            self.current_game.started_at = datetime.utcnow()
            await db.commit()
            break

        # Start multiplier at 1.00
        self.current_multiplier = 1.00

        # Broadcast game started
        await self.broadcast({
            "type": "game_started",
            "game_id": self.current_game.id
        })

        # Increase multiplier until crash point
        while self.current_multiplier < crash_point:
            # Calculate next multiplier
            # Speed increases slightly as multiplier goes up
            elapsed = (self.current_multiplier - 1.00) * 10  # Seconds since start
            increment = 0.01 * (1 + elapsed * 0.01)  # Gradually faster
            self.current_multiplier = round(self.current_multiplier + increment, 2)

            if self.current_multiplier >= crash_point:
                self.current_multiplier = crash_point
                break

            # Broadcast current multiplier
            await self.broadcast({
                "type": "multiplier_update",
                "game_id": self.current_game.id,
                "multiplier": self.current_multiplier
            })

            # Update speed (faster as it goes higher)
            await asyncio.sleep(CrashGameService.MULTIPLIER_SPEED)

    async def _crashed_phase(self):
        """Crashed phase - game has crashed, show results."""
        # Finish game in database
        async for db in get_db():
            await CrashGameService.finish_game(
                self.current_game.id,
                self.current_game.crash_point,
                db
            )
            # Get final bets
            bets = await CrashGameService.get_game_bets(self.current_game.id, db)
            break

        # Broadcast crash
        await self.broadcast({
            "type": "game_crashed",
            "game_id": self.current_game.id,
            "crash_point": self.current_game.crash_point,
            "server_seed": self.current_game.server_seed,  # Reveal seed for verification
            "bets": bets
        })

        # Show results for 3 seconds
        await asyncio.sleep(3)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected WebSocket clients."""
        if not self.connected_clients:
            return

        # Remove disconnected clients
        disconnected = set()
        for client in self.connected_clients:
            try:
                await client.send_json(message)
            except Exception:
                disconnected.add(client)

        # Cleanup
        self.connected_clients -= disconnected

    def add_client(self, websocket):
        """Add a WebSocket client to receive updates."""
        self.connected_clients.add(websocket)

    def remove_client(self, websocket):
        """Remove a WebSocket client."""
        self.connected_clients.discard(websocket)

    def get_current_state(self) -> dict:
        """Get the current game state for new connections."""
        if not self.current_game:
            return {"status": "no_game"}

        return {
            "game_id": self.current_game.id,
            "status": self.current_game.status,
            "multiplier": self.current_multiplier if self.current_game.status == 'playing' else None,
            "crash_point": self.current_game.crash_point if self.current_game.status == 'crashed' else None,
            "server_seed_hash": self.current_game.server_seed_hash
        }


# Global instance
crash_manager = CrashGameManager()
