"""
Crash Multiplier Game Engine - Maximum Addiction Mechanics
Real-time multiplier game with instant cash-out capability.
Research shows crash games are the #1 crypto casino game type due to suspense and control illusion.
"""
import asyncio
import hashlib
import secrets
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from dataclasses import dataclass, field
from enum import Enum
import random

from database import get_db_session, User, VirtualWallet
from logger import logger

class CrashGameState(Enum):
    WAITING = "waiting"      # Waiting for players to join
    BETTING = "betting"      # Accepting bets (15 second window)
    FLYING = "flying"        # Multiplier increasing
    CRASHED = "crashed"      # Game ended, payouts calculated

class CashOutStatus(Enum):
    ACTIVE = "active"        # Still in the game
    CASHED_OUT = "cashed_out"  # Successfully cashed out
    CRASHED = "crashed"      # Didn't cash out in time

@dataclass
class CrashBet:
    """Individual player bet in a crash game"""
    user_id: str
    bet_amount: int
    auto_cashout: Optional[float] = None  # Automatic cash-out multiplier
    cashed_out_at: Optional[float] = None
    payout: int = 0
    status: CashOutStatus = CashOutStatus.ACTIVE

@dataclass  
class CrashGameRound:
    """Complete crash game round with all players"""
    id: str
    server_seed: str
    client_seed: str
    nonce: int
    state: CrashGameState
    created_at: datetime
    betting_ends_at: datetime
    
    # Game progression
    start_time: Optional[datetime] = None
    crash_point: Optional[float] = None
    current_multiplier: float = 1.0
    
    # Players and bets
    players: Dict[str, CrashBet] = field(default_factory=dict)
    total_bet_amount: int = 0
    total_payouts: int = 0
    
    # Results
    finished: bool = False

class CrashGameEngine:
    """
    High-adrenaline crash game engine with maximum psychological impact.
    
    Key Addiction Mechanics:
    - Real-time tension as multiplier climbs
    - Player control illusion (can cash out anytime)
    - FOMO from seeing others cash out at higher multipliers
    - Social pressure from multiplayer environment
    - Variable reinforcement (unpredictable crash points)
    - Near-miss psychology (crashed just after your target)
    """
    
    def __init__(self):
        self.active_round: Optional[CrashGameRound] = None
        self.round_history: List[CrashGameRound] = []
        self.connected_players: Set[str] = set()
        
        # Game configuration
        self.betting_duration = 15  # seconds
        self.house_edge = 0.01  # 1% house edge
        self.min_bet = 10
        self.max_bet = 100000
        
        # Crash point generation (provably fair)
        self.crash_points_cache: List[float] = []
        
    async def start_new_round(self) -> Dict[str, Any]:
        """
        Start a new crash game round.
        This creates the initial excitement and FOMO.
        """
        try:
            # End previous round if not finished
            if self.active_round and not self.active_round.finished:
                await self._force_end_round()
            
            # Generate provably fair seeds
            server_seed = secrets.token_hex(32)
            client_seed = secrets.token_hex(8)
            nonce = len(self.round_history) + 1
            
            # Create new round
            round_id = f"crash_{int(datetime.now().timestamp())}"
            now = datetime.now()
            
            self.active_round = CrashGameRound(
                id=round_id,
                server_seed=server_seed,
                client_seed=client_seed,
                nonce=nonce,
                state=CrashGameState.BETTING,
                created_at=now,
                betting_ends_at=now + timedelta(seconds=self.betting_duration)
            )
            
            # Pre-calculate crash point (hidden until reveal)
            crash_point = self._calculate_crash_point(server_seed, client_seed, nonce)
            self.active_round.crash_point = crash_point
            
            # Start betting timer
            asyncio.create_task(self._betting_countdown())
            
            logger.info(f"New crash round started: {round_id}, crash point: {crash_point:.2f}x")
            
            return {
                'success': True,
                'round_id': round_id,
                'state': CrashGameState.BETTING.value,
                'betting_time_left': self.betting_duration,
                'server_seed_hash': hashlib.sha256(server_seed.encode()).hexdigest(),
                'client_seed': client_seed,
                'nonce': nonce,
                'current_players': len(self.active_round.players),
                'previous_crashes': self._get_recent_crash_history()
            }
            
        except Exception as e:
            logger.error(f"Error starting crash round: {e}")
            return {'success': False, 'error': str(e)}
    
    async def place_bet(self, user_id: str, bet_amount: int, auto_cashout: float = None) -> Dict[str, Any]:
        """
        Place a bet in the current crash round.
        This is the commitment moment - psychological investment.
        """
        try:
            if not self.active_round or self.active_round.state != CrashGameState.BETTING:
                return {'success': False, 'error': 'No active betting round'}
            
            if user_id in self.active_round.players:
                return {'success': False, 'error': 'Already bet in this round'}
            
            if bet_amount < self.min_bet or bet_amount > self.max_bet:
                return {'success': False, 'error': f'Bet must be between {self.min_bet} and {self.max_bet:,} GEM coins'}
            
            # Validate auto-cashout
            if auto_cashout and (auto_cashout < 1.01 or auto_cashout > 1000):
                return {'success': False, 'error': 'Auto cash-out must be between 1.01x and 1000x'}
            
            # Check user balance
            async with get_db_session() as session:
                user = await session.get(User, user_id)
                if not user or not user.virtual_wallet:
                    return {'success': False, 'error': 'User wallet not found'}
                
                if user.virtual_wallet.gem_coins < bet_amount:
                    return {'success': False, 'error': 'Insufficient GEM coins'}
                
                # Deduct bet amount
                user.virtual_wallet.gem_coins -= bet_amount
                await session.commit()
            
            # Add bet to round
            bet = CrashBet(
                user_id=user_id,
                bet_amount=bet_amount,
                auto_cashout=auto_cashout
            )
            
            self.active_round.players[user_id] = bet
            self.active_round.total_bet_amount += bet_amount
            self.connected_players.add(user_id)
            
            # Generate excitement message
            excitement_msg = self._generate_bet_excitement(bet_amount, auto_cashout, len(self.active_round.players))
            
            return {
                'success': True,
                'bet_placed': True,
                'bet_amount': bet_amount,
                'auto_cashout': auto_cashout,
                'round_id': self.active_round.id,
                'total_players': len(self.active_round.players),
                'total_pot': self.active_round.total_bet_amount,
                'time_left': (self.active_round.betting_ends_at - datetime.now()).total_seconds(),
                'excitement_message': excitement_msg
            }
            
        except Exception as e:
            logger.error(f"Error placing crash bet for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def cash_out(self, user_id: str) -> Dict[str, Any]:
        """
        Manual cash-out during flight phase.
        This is the moment of highest tension and decision-making.
        """
        try:
            if not self.active_round or self.active_round.state != CrashGameState.FLYING:
                return {'success': False, 'error': 'No active flying round'}
            
            if user_id not in self.active_round.players:
                return {'success': False, 'error': 'Not in this round'}
            
            bet = self.active_round.players[user_id]
            if bet.status != CashOutStatus.ACTIVE:
                return {'success': False, 'error': 'Already cashed out or crashed'}
            
            # Calculate payout at current multiplier
            current_multiplier = self.active_round.current_multiplier
            payout = int(bet.bet_amount * current_multiplier)
            
            # Update bet status
            bet.cashed_out_at = current_multiplier
            bet.payout = payout
            bet.status = CashOutStatus.CASHED_OUT
            
            # Credit user wallet
            async with get_db_session() as session:
                user = await session.get(User, user_id)
                if user and user.virtual_wallet:
                    user.virtual_wallet.gem_coins += payout
                    await session.commit()
            
            # Update round totals
            self.active_round.total_payouts += payout
            
            # Generate celebration message
            celebration = self._generate_cashout_celebration(payout, current_multiplier, bet.bet_amount)
            
            # Notify other players (FOMO induction)
            await self._broadcast_cashout_event(user_id, current_multiplier, payout)
            
            return {
                'success': True,
                'cashed_out': True,
                'multiplier': current_multiplier,
                'payout': payout,
                'profit': payout - bet.bet_amount,
                'celebration_message': celebration,
                'timing': 'perfect' if current_multiplier > 2.0 else 'early' if current_multiplier < 1.5 else 'good'
            }
            
        except Exception as e:
            logger.error(f"Error cashing out for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_round_status(self, user_id: str = None) -> Dict[str, Any]:
        """
        Get current round status with real-time updates.
        This maintains engagement and tension throughout the game.
        """
        try:
            if not self.active_round:
                return {
                    'success': True,
                    'state': 'no_active_round',
                    'next_round_in': 5,  # seconds until next round starts
                    'recent_crashes': self._get_recent_crash_history()
                }
            
            round_data = {
                'success': True,
                'round_id': self.active_round.id,
                'state': self.active_round.state.value,
                'current_multiplier': self.active_round.current_multiplier,
                'total_players': len(self.active_round.players),
                'total_bet_amount': self.active_round.total_bet_amount,
                'player_count_by_status': self._get_player_status_counts()
            }
            
            # Add state-specific data
            if self.active_round.state == CrashGameState.BETTING:
                round_data.update({
                    'betting_time_left': max(0, (self.active_round.betting_ends_at - datetime.now()).total_seconds()),
                    'min_bet': self.min_bet,
                    'max_bet': self.max_bet
                })
            
            elif self.active_round.state == CrashGameState.FLYING:
                round_data.update({
                    'flight_time': (datetime.now() - self.active_round.start_time).total_seconds() if self.active_round.start_time else 0,
                    'recent_cashouts': self._get_recent_cashouts(),
                    'multiplier_speed': self._calculate_multiplier_speed(),
                    'tension_level': self._calculate_tension_level()
                })
            
            elif self.active_round.state == CrashGameState.CRASHED:
                round_data.update({
                    'crash_point': self.active_round.crash_point,
                    'total_payouts': self.active_round.total_payouts,
                    'house_profit': self.active_round.total_bet_amount - self.active_round.total_payouts,
                    'next_round_in': 5
                })
            
            # Add user-specific data if provided
            if user_id and user_id in self.active_round.players:
                bet = self.active_round.players[user_id]
                round_data['your_bet'] = {
                    'bet_amount': bet.bet_amount,
                    'auto_cashout': bet.auto_cashout,
                    'status': bet.status.value,
                    'potential_payout': int(bet.bet_amount * self.active_round.current_multiplier) if bet.status == CashOutStatus.ACTIVE else bet.payout,
                    'can_cashout': bet.status == CashOutStatus.ACTIVE and self.active_round.state == CrashGameState.FLYING
                }
            
            return round_data
            
        except Exception as e:
            logger.error(f"Error getting crash round status: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _betting_countdown(self):
        """Handle the betting phase countdown"""
        await asyncio.sleep(self.betting_duration)
        
        if self.active_round and self.active_round.state == CrashGameState.BETTING:
            if len(self.active_round.players) == 0:
                # No players, start new round immediately
                await self.start_new_round()
            else:
                # Start the flight phase
                await self._start_flight_phase()
    
    async def _start_flight_phase(self):
        """Start the multiplier flight phase"""
        if not self.active_round:
            return
        
        self.active_round.state = CrashGameState.FLYING
        self.active_round.start_time = datetime.now()
        
        # Broadcast flight start
        await self._broadcast_flight_start()
        
        # Start multiplier progression
        asyncio.create_task(self._run_multiplier_progression())
    
    async def _run_multiplier_progression(self):
        """Run the multiplier progression until crash point"""
        if not self.active_round:
            return
        
        start_time = datetime.now()
        crash_point = self.active_round.crash_point
        
        while self.active_round.current_multiplier < crash_point:
            # Calculate time-based multiplier progression
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # Exponential growth formula for realistic crash game feel
            self.active_round.current_multiplier = 1.0 + (elapsed * elapsed * 0.1)
            
            # Check for auto cash-outs
            await self._process_auto_cashouts()
            
            # Broadcast multiplier update
            await self._broadcast_multiplier_update()
            
            # Sleep for smooth animation (60 FPS)
            await asyncio.sleep(1/60)
        
        # CRASH!
        await self._execute_crash()
    
    async def _execute_crash(self):
        """Execute the crash event and finalize round"""
        if not self.active_round:
            return
        
        self.active_round.state = CrashGameState.CRASHED
        self.active_round.finished = True
        
        # Mark remaining players as crashed
        for user_id, bet in self.active_round.players.items():
            if bet.status == CashOutStatus.ACTIVE:
                bet.status = CashOutStatus.CRASHED
                # Update user statistics for crashed bets
                await self._update_crash_stats(user_id, bet, crashed=True)
        
        # Save round to history
        self.round_history.append(self.active_round)
        if len(self.round_history) > 100:  # Keep last 100 rounds
            self.round_history.pop(0)
        
        # Broadcast crash event with dramatic messaging
        await self._broadcast_crash_event()
        
        # Update global statistics
        await self._update_global_crash_stats()
        
        # Start next round after delay
        await asyncio.sleep(5)
        await self.start_new_round()
    
    def _calculate_crash_point(self, server_seed: str, client_seed: str, nonce: int) -> float:
        """
        Calculate provably fair crash point.
        Uses exponential distribution for realistic crash game economics.
        """
        # Create hash input
        hash_input = f"{server_seed}:{client_seed}:{nonce}"
        hash_result = hashlib.sha256(hash_input.encode()).hexdigest()
        
        # Convert to float between 0 and 1
        hex_value = int(hash_result[:8], 16)
        random_value = hex_value / (2**32)
        
        # Apply house edge and exponential distribution
        # This creates the expected crash point distribution
        house_edge_adjusted = random_value * (1 - self.house_edge)
        
        if house_edge_adjusted == 0:
            return 1.0
        
        crash_point = 1.0 / house_edge_adjusted
        
        # Cap at reasonable maximum and minimum
        crash_point = max(1.0, min(crash_point, 10000.0))
        
        return round(crash_point, 2)
    
    def _generate_bet_excitement(self, bet_amount: int, auto_cashout: Optional[float], player_count: int) -> str:
        """Generate excitement messaging for bet placement"""
        if bet_amount > 10000:
            return f"💎 HIGH ROLLER ALERT! {bet_amount:,} GEM coins on the line! Will you be brave enough to fly high?"
        elif auto_cashout and auto_cashout > 10:
            return f"🚀 MOON SHOT! Auto cash-out at {auto_cashout:.2f}x - going for the big win!"
        elif player_count > 50:
            return f"🔥 MEGA ROUND! {player_count} players flying together - the tension is REAL!"
        else:
            return f"✈️ Ready for takeoff! {bet_amount:,} GEM coins bet placed - let's fly!"
    
    def _generate_cashout_celebration(self, payout: int, multiplier: float, bet_amount: int) -> str:
        """Generate celebration message for successful cash-out"""
        profit = payout - bet_amount
        
        if multiplier > 10:
            return f"🌟 LEGENDARY CASH-OUT! {multiplier:.2f}x multiplier earned you {payout:,} GEM coins! (+{profit:,} profit)"
        elif multiplier > 5:
            return f"🎉 AMAZING TIMING! Cashed out at {multiplier:.2f}x for {payout:,} GEM coins! (+{profit:,} profit)"
        elif multiplier > 2:
            return f"💰 GREAT CASH-OUT! {multiplier:.2f}x earned you {payout:,} GEM coins! (+{profit:,} profit)"
        else:
            return f"✅ Safe landing! {multiplier:.2f}x payout of {payout:,} GEM coins (+{profit:,} profit)"

# Global crash engine instance
crash_engine = CrashGameEngine()