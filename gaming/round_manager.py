"""
Server-Managed Roulette Round System
Maintains global round state and auto-advances phases for all players.
"""

import asyncio
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Set, Any
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from database.models import RouletteRound, RoundPhase, GameBet
from database.database import AsyncSessionLocal
from gaming.roulette import CryptoRouletteEngine


@dataclass
class RoundState:
    """In-memory representation of current round"""
    round_id: str
    round_number: int
    phase: RoundPhase
    started_at: datetime
    betting_duration: int  # seconds
    phase_ends_at: datetime
    outcome_number: Optional[int] = None
    outcome_color: Optional[str] = None
    outcome_crypto: Optional[str] = None
    triggered_by: Optional[str] = None
    bets: Set[str] = field(default_factory=set)
    players: Set[str] = field(default_factory=set)


class RoundManager:
    """
    Server-side round manager for CryptoChecker roulette.
    Singleton instance maintains current round state and auto-advances phases.
    """

    def __init__(self, betting_duration: int = 15, results_display_duration: int = 5):
        self.betting_duration = betting_duration
        self.results_display_duration = results_display_duration
        self.current_round: Optional[RoundState] = None
        self.roulette_engine = CryptoRouletteEngine()
        self.sse_subscribers: Dict[str, asyncio.Queue] = {}  # user_id → event queue
        self._lock = asyncio.Lock()  # Prevent race conditions on phase transitions
        self._timer_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize round manager - start first round and background timer"""
        print("[Round Manager] Initializing...")
        await self.start_new_round()

        # Start background timer task
        self._timer_task = asyncio.create_task(self.auto_advance_timer())
        print("[Round Manager] Initialized - first round started, timer running")

    async def start_new_round(self, triggered_by: Optional[str] = None) -> RoundState:
        """Initialize a new betting round"""
        async with self._lock:
            round_id = str(uuid.uuid4())
            started_at = datetime.utcnow()
            betting_ends_at = started_at + timedelta(seconds=self.betting_duration)

            # Create database record
            async with AsyncSessionLocal() as session:
                # Get next round number
                result = await session.execute(
                    select(RouletteRound).order_by(RouletteRound.round_number.desc()).limit(1)
                )
                last_round = result.scalar_one_or_none()
                next_round_number = (last_round.round_number + 1) if last_round else 1

                db_round = RouletteRound(
                    id=round_id,
                    round_number=next_round_number,
                    phase=RoundPhase.BETTING.value,
                    started_at=started_at,
                    betting_ends_at=betting_ends_at,
                    triggered_by=triggered_by
                )
                session.add(db_round)
                await session.commit()
                await session.refresh(db_round)

                print(f"[Round Manager] Round {next_round_number} started (ID: {round_id[:8]}...)")

            # Update in-memory state
            self.current_round = RoundState(
                round_id=round_id,
                round_number=next_round_number,
                phase=RoundPhase.BETTING,
                started_at=started_at,
                betting_duration=self.betting_duration,
                phase_ends_at=betting_ends_at,
                triggered_by=triggered_by
            )

            # Broadcast to all connected clients
            await self._broadcast_event("round_started", {
                "round_id": round_id,
                "round_number": next_round_number,
                "phase": "BETTING",
                "betting_duration": self.betting_duration,
                "started_at": started_at.isoformat(),
                "ends_at": betting_ends_at.isoformat()
            })

            return self.current_round

    async def trigger_spin(self, user_id: Optional[str], game_session_id: str) -> Dict:
        """
        Manually trigger spin (player clicks "SPIN NOW" button).
        Advances from BETTING → SPINNING immediately.
        """
        async with self._lock:
            if not self.current_round:
                raise ValueError("No active round")

            if self.current_round.phase != RoundPhase.BETTING:
                raise ValueError(f"Cannot spin during {self.current_round.phase.value} phase")

            print(f"[Round Manager] Manual spin triggered by user {user_id or 'AUTO'}")

            # Transition to SPINNING phase
            self.current_round.phase = RoundPhase.SPINNING
            self.current_round.triggered_by = user_id

            # Generate provably fair outcome using existing roulette engine
            # Use a simple hash-based approach for now
            import hashlib
            combined = f"{self.current_round.round_id}{self.current_round.round_number}"
            hash_result = hashlib.sha256(combined.encode()).hexdigest()
            outcome_number = int(hash_result[:8], 16) % 37  # 0-36

            # Determine color and crypto based on number
            outcome = self.roulette_engine.crypto_wheel.get(outcome_number, {})
            outcome_color = outcome.get("color", "green")
            outcome_crypto = outcome.get("crypto", "BTC")

            self.current_round.outcome_number = outcome_number
            self.current_round.outcome_color = outcome_color
            self.current_round.outcome_crypto = outcome_crypto

            # Update database
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(RouletteRound)
                    .where(RouletteRound.id == self.current_round.round_id)
                    .values(
                        phase=RoundPhase.SPINNING.value,
                        triggered_by=user_id,
                        outcome_number=outcome_number,
                        outcome_color=outcome_color,
                        outcome_crypto=outcome_crypto
                    )
                )
                await session.commit()

            # Broadcast phase change
            await self._broadcast_event("phase_changed", {
                "round_id": self.current_round.round_id,
                "phase": "SPINNING",
                "outcome": outcome_number,
                "color": outcome_color,
                "crypto": outcome_crypto,
                "triggered_by": user_id
            })

            print(f"[Round Manager] Outcome: {outcome_number} ({outcome_color})")

            # Schedule automatic transition to RESULTS phase after animation (3s)
            asyncio.create_task(self._auto_transition_to_results(delay=3))

            return {
                "number": outcome_number,
                "color": outcome_color,
                "crypto": outcome_crypto
            }

    async def _auto_transition_to_results(self, delay: int):
        """Automatically transition SPINNING → RESULTS after animation completes"""
        await asyncio.sleep(delay)

        async with self._lock:
            if not self.current_round or self.current_round.phase != RoundPhase.SPINNING:
                return  # Already moved on

            print(f"[Round Manager] Transitioning to RESULTS phase")
            self.current_round.phase = RoundPhase.RESULTS

            # Update database
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(RouletteRound)
                    .where(RouletteRound.id == self.current_round.round_id)
                    .values(phase=RoundPhase.RESULTS.value)
                )
                await session.commit()

            # Broadcast results phase
            await self._broadcast_event("round_results", {
                "round_id": self.current_round.round_id,
                "phase": "RESULTS",
                "outcome": self.current_round.outcome_number,
                "color": self.current_round.outcome_color,
                "crypto": self.current_round.outcome_crypto
            })

            # Schedule transition to new round
            asyncio.create_task(self._auto_start_new_round(delay=self.results_display_duration))

    async def _auto_start_new_round(self, delay: int):
        """Automatically start new round after results display duration"""
        await asyncio.sleep(delay)

        async with self._lock:
            if not self.current_round or self.current_round.phase != RoundPhase.RESULTS:
                return

            print(f"[Round Manager] Round {self.current_round.round_number} complete")

            # Mark old round as completed
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(RouletteRound)
                    .where(RouletteRound.id == self.current_round.round_id)
                    .values(
                        phase=RoundPhase.CLEANUP.value,
                        completed_at=datetime.utcnow()
                    )
                )
                await session.commit()

            # Broadcast round end
            await self._broadcast_event("round_ended", {
                "round_id": self.current_round.round_id
            })

        # Start new round (releases lock, then re-acquires)
        await self.start_new_round()

    async def auto_advance_timer(self):
        """
        Background task: check timer every second, auto-spin when betting time expires.
        This runs indefinitely in the background.
        """
        print("[Round Manager] Background timer started")

        while True:
            try:
                await asyncio.sleep(1)  # Check every second

                if not self.current_round:
                    continue

                if self.current_round.phase != RoundPhase.BETTING:
                    continue

                # Check if betting time expired
                if datetime.utcnow() >= self.current_round.phase_ends_at:
                    print(f"[Round Manager] Timer expired - auto-spinning round {self.current_round.round_number}")
                    # Auto-spin (no user triggered it, timer expired)
                    try:
                        await self.trigger_spin(
                            user_id=None,  # Auto-spin, not user-triggered
                            game_session_id="auto"
                        )
                    except ValueError as e:
                        # Already spinning (race condition avoided by lock)
                        print(f"[Round Manager] Auto-spin skipped: {e}")

            except Exception as e:
                print(f"[Round Manager] Timer error: {e}")
                # Continue running despite errors

    def get_current_round(self) -> Optional[Dict]:
        """Return current round state for API consumption"""
        if not self.current_round:
            return None

        time_remaining = max(
            0,
            (self.current_round.phase_ends_at - datetime.utcnow()).total_seconds()
        )

        return {
            "round_id": self.current_round.round_id,
            "round_number": self.current_round.round_number,
            "phase": self.current_round.phase.value,
            "time_remaining": time_remaining,
            "betting_duration": self.betting_duration,
            "outcome": {
                "number": self.current_round.outcome_number,
                "color": self.current_round.outcome_color,
                "crypto": self.current_round.outcome_crypto
            } if self.current_round.outcome_number is not None else None,
            "triggered_by": self.current_round.triggered_by,
            "total_bets": len(self.current_round.bets),
            "total_players": len(self.current_round.players)
        }

    async def register_bet(self, bet_id: str, user_id: str):
        """Register a bet for the current round"""
        if self.current_round:
            self.current_round.bets.add(bet_id)
            self.current_round.players.add(user_id)
            print(f"[Round Manager] Bet {bet_id[:8]}... registered (total: {len(self.current_round.bets)})")

    async def _broadcast_event(self, event_type: str, data: Dict):
        """Send SSE event to all subscribed clients"""
        event_data = {"event": event_type, "data": data}

        # Remove disconnected subscribers
        disconnected = []
        for user_id, queue in list(self.sse_subscribers.items()):
            try:
                # Non-blocking put with timeout
                await asyncio.wait_for(queue.put(event_data), timeout=1.0)
            except (asyncio.TimeoutError, Exception) as e:
                print(f"[Round Manager] Removing disconnected subscriber {user_id}: {e}")
                disconnected.append(user_id)

        for user_id in disconnected:
            self.sse_subscribers.pop(user_id, None)

        if self.sse_subscribers:
            print(f"[Round Manager] Broadcast '{event_type}' to {len(self.sse_subscribers)} clients")

    async def subscribe_sse(self, user_id: str) -> asyncio.Queue:
        """Register a new SSE subscriber"""
        queue = asyncio.Queue(maxsize=100)  # Prevent memory issues
        self.sse_subscribers[user_id] = queue

        print(f"[Round Manager] New SSE subscriber: {user_id} (total: {len(self.sse_subscribers)})")

        # Send current round state immediately
        current = self.get_current_round()
        if current:
            await queue.put({"event": "round_current", "data": current})

        return queue

    def unsubscribe_sse(self, user_id: str):
        """Remove SSE subscriber"""
        if user_id in self.sse_subscribers:
            self.sse_subscribers.pop(user_id)
            print(f"[Round Manager] SSE subscriber removed: {user_id} (remaining: {len(self.sse_subscribers)})")


# Global singleton instance
round_manager = RoundManager(betting_duration=15, results_display_duration=5)
