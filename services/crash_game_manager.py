"""
Crash Game Manager

Manages automatic crash game rounds in the background.
Handles timing, multiplier progression, and game state.
"""

import asyncio
import random
from datetime import datetime
from typing import Optional, Set, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import CrashGame
from services.crash_service import CrashGameService


class CrashGameManager:
    """Manages automatic crash game rounds."""
    
    # Bot simulation settings
    MIN_BOTS = 1
    MAX_BOTS = 3

    def __init__(self):
        self.current_game: Optional[CrashGame] = None
        self.current_multiplier: float = 1.00
        self.is_running: bool = False
        self.is_idle: bool = True  # True when no players connected
        self.task: Optional[asyncio.Task] = None
        self.connected_clients: Set = set()
        self.current_bets: List[Dict] = []  # Track bets for current round

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
                # Wait for at least one player to connect before starting rounds
                while not self.connected_clients and self.is_running:
                    if not self.is_idle:
                        self.is_idle = True
                        print("[Crash Manager] Entering idle mode - waiting for players")
                        await self.broadcast({
                            "type": "game_state",
                            "status": "idle",
                            "message": "Waiting for players..."
                        })
                    await asyncio.sleep(0.5)  # Check every 500ms
                
                # Player connected - exit idle mode
                if self.is_idle:
                    self.is_idle = False
                    print(f"[Crash Manager] Player connected! Starting new round...")
                
                # Reset bets for new round
                self.current_bets = []
                
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

        # Simulate bot bets during betting phase (staggered for realism)
        asyncio.create_task(self._simulate_bot_bets())
        
        # Adaptive betting duration: shorter when solo, longer with multiple players
        player_count = len(self.connected_clients)
        if player_count <= 1:
            betting_duration = 5  # Faster for solo debugging
            print(f"[Crash Manager] Solo mode: {betting_duration}s betting phase")
        else:
            betting_duration = CrashGameService.BETTING_DURATION  # Full 10s
            print(f"[Crash Manager] Multiplayer ({player_count} players): {betting_duration}s betting phase")
        
        await asyncio.sleep(betting_duration)

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

    async def _simulate_bot_bets(self):
        """
        Simulate bot bets during betting phase for a livelier feel.
        Bots place 1-3 bets with staggered timing for realism.
        """
        # Bot names for display (subset of available bots)
        BOT_NAMES = [
            "CryptoKing", "LuckyBettor", "DiamondHands", "MoonShot",
            "BlockChainBoss", "TokenMaster", "GemHunter", "RocketRider"
        ]
        
        # Determine number of bots (fewer if real players are betting)
        real_player_count = len(self.current_bets)
        max_bots = max(1, self.MAX_BOTS - real_player_count)
        num_bots = random.randint(self.MIN_BOTS, max_bots)
        
        # Select random bot names
        selected_bots = random.sample(BOT_NAMES, min(num_bots, len(BOT_NAMES)))
        
        for bot_name in selected_bots:
            # Stagger bet timing (1-4 seconds into betting phase)
            await asyncio.sleep(random.uniform(1.0, 4.0))
            
            # Don't place bet if game has moved past waiting phase
            if self.current_game and self.current_game.status != 'waiting':
                break
            
            # Generate random bet amount (100-5000 GEM)
            bet_amount = random.choice([100, 250, 500, 1000, 2000, 2500, 3000, 5000])
            
            # Broadcast bot bet (display only - not real database bet)
            await self.broadcast({
                "type": "bet_placed",
                "username": bot_name,
                "bet_amount": bet_amount,
                "game_id": self.current_game.id if self.current_game else 0,
                "is_bot": True
            })
            
            print(f"[Crash Manager] Bot {bot_name} placed {bet_amount} GEM bet")


# Global instance
crash_manager = CrashGameManager()

