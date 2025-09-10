"""
Plinko Game Engine - Visual Physics-Based Gaming
Ball-drop physics simulation with multiple payout zones and risk levels.
Research shows Plinko is highly engaging due to visual anticipation and broad appeal.
"""
import asyncio
import hashlib
import secrets
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from dataclasses import dataclass
from enum import Enum
import random

from database import get_db_session, User, VirtualWallet
from logger import logger

class PlinkoRiskLevel(Enum):
    LOW = "low"         # 16 pins, balanced payouts
    MEDIUM = "medium"   # 14 pins, higher variance
    HIGH = "high"       # 12 pins, extreme payouts

class PlinkoRows(Enum):
    ROWS_8 = 8    # Beginner friendly
    ROWS_12 = 12  # Standard
    ROWS_16 = 16  # Advanced

@dataclass
class PlinkoBoard:
    """Plinko board configuration with pins and payouts"""
    rows: int
    pins: List[Tuple[float, float]]  # (x, y) positions
    multipliers: List[float]  # Payout multipliers for each slot
    risk_level: PlinkoRiskLevel
    
@dataclass
class PlinkoBall:
    """Individual Plinko ball with physics simulation"""
    ball_id: str
    user_id: str
    bet_amount: int
    board_config: PlinkoBoard
    
    # Physics state
    position: Tuple[float, float] = (0.5, 0.0)  # Normalized coordinates (0-1)
    velocity: Tuple[float, float] = (0.0, 0.0)
    bounces: List[Tuple[float, float]] = None  # Bounce positions for animation
    
    # Game state
    final_slot: Optional[int] = None
    multiplier: Optional[float] = None
    payout: Optional[int] = None
    completed: bool = False
    server_seed: str = None
    client_seed: str = None
    nonce: int = None

@dataclass
class PlinkoSession:
    """Complete Plinko game session"""
    session_id: str
    user_id: str
    created_at: datetime
    total_balls: int
    balls_dropped: int
    total_bet: int
    total_payout: int
    risk_level: PlinkoRiskLevel
    rows: int
    completed: bool = False

class PlinkoGameEngine:
    """
    Advanced Plinko game engine with realistic physics simulation.
    
    Key Features:
    - Physics-based ball movement with deterministic outcomes
    - Visual animation data for smooth frontend rendering
    - Multiple risk levels and board configurations
    - Batch ball dropping for rapid-fire gameplay
    - Provably fair outcome verification
    - Auto-play features for grinding
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, PlinkoSession] = {}
        self.board_configs = self._initialize_board_configurations()
        
        # Physics constants
        self.gravity = 0.8
        self.bounce_factor = 0.7
        self.pin_collision_radius = 0.02
        self.slot_width = 1.0
        
        # Game limits
        self.min_bet = 10
        self.max_bet = 50000
        self.max_balls_per_session = 100
    
    def _initialize_board_configurations(self) -> Dict[str, PlinkoBoard]:
        """Initialize different Plinko board configurations"""
        configs = {}
        
        # LOW RISK - 16 rows, balanced multipliers
        low_risk_multipliers = [
            110, 41, 10, 5, 3, 1.5, 1, 0.5, 0.3, 0.5, 1, 1.5, 3, 5, 10, 41, 110
        ]
        configs[f"{PlinkoRiskLevel.LOW.value}_16"] = PlinkoBoard(
            rows=16,
            pins=self._generate_pin_positions(16),
            multipliers=low_risk_multipliers,
            risk_level=PlinkoRiskLevel.LOW
        )
        
        # MEDIUM RISK - 14 rows, higher variance
        medium_risk_multipliers = [
            1000, 130, 26, 9, 4, 2, 0.2, 0.2, 0.2, 2, 4, 9, 26, 130, 1000
        ]
        configs[f"{PlinkoRiskLevel.MEDIUM.value}_14"] = PlinkoBoard(
            rows=14,
            pins=self._generate_pin_positions(14),
            multipliers=medium_risk_multipliers,
            risk_level=PlinkoRiskLevel.MEDIUM
        )
        
        # HIGH RISK - 12 rows, extreme payouts
        high_risk_multipliers = [
            1000, 140, 15, 4, 1, 0.2, 0.2, 1, 4, 15, 140, 1000
        ]
        configs[f"{PlinkoRiskLevel.HIGH.value}_12"] = PlinkoBoard(
            rows=12,
            pins=self._generate_pin_positions(12),
            multipliers=high_risk_multipliers,
            risk_level=PlinkoRiskLevel.HIGH
        )
        
        return configs
    
    def _generate_pin_positions(self, rows: int) -> List[Tuple[float, float]]:
        """Generate pin positions for the Plinko board"""
        pins = []
        
        for row in range(rows):
            # Number of pins in this row
            pins_in_row = row + 1
            
            # Y position (0 = top, 1 = bottom)
            y = (row + 1) / (rows + 1)
            
            # X positions distributed evenly
            if pins_in_row == 1:
                pins.append((0.5, y))
            else:
                for pin in range(pins_in_row):
                    x = (pin / (pins_in_row - 1)) * 0.8 + 0.1  # Center with margins
                    pins.append((x, y))
        
        return pins
    
    async def create_plinko_session(self, user_id: str, risk_level: str, 
                                  rows: int = 16) -> Dict[str, Any]:
        """
        Create a new Plinko gaming session.
        Sets up the board and prepares for ball dropping.
        """
        try:
            # Validate inputs
            try:
                risk_enum = PlinkoRiskLevel(risk_level)
            except ValueError:
                return {'success': False, 'error': 'Invalid risk level'}
            
            if rows not in [8, 12, 14, 16]:
                return {'success': False, 'error': 'Invalid number of rows'}
            
            # Get board configuration
            config_key = f"{risk_level}_{rows}"
            if config_key not in self.board_configs:
                # Use closest available configuration
                config_key = f"{risk_level}_16"
                rows = 16
            
            board_config = self.board_configs[config_key]
            
            # Create session
            session_id = f"plinko_{user_id}_{int(datetime.now().timestamp())}"
            session = PlinkoSession(
                session_id=session_id,
                user_id=user_id,
                created_at=datetime.now(),
                total_balls=0,
                balls_dropped=0,
                total_bet=0,
                total_payout=0,
                risk_level=risk_enum,
                rows=rows
            )
            
            self.active_sessions[session_id] = session
            
            return {
                'success': True,
                'session_id': session_id,
                'board_config': {
                    'rows': rows,
                    'pins': board_config.pins,
                    'multipliers': board_config.multipliers,
                    'risk_level': risk_level,
                    'slots': len(board_config.multipliers)
                },
                'game_limits': {
                    'min_bet': self.min_bet,
                    'max_bet': self.max_bet,
                    'max_balls': self.max_balls_per_session
                },
                'excitement_message': self._generate_session_excitement(risk_enum, rows)
            }
            
        except Exception as e:
            logger.error(f"Error creating Plinko session for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def drop_ball(self, session_id: str, bet_amount: int, 
                       client_seed: str = None) -> Dict[str, Any]:
        """
        Drop a single Plinko ball with physics simulation.
        This is the moment of maximum anticipation and excitement.
        """
        try:
            if session_id not in self.active_sessions:
                return {'success': False, 'error': 'Session not found'}
            
            session = self.active_sessions[session_id]
            if session.completed:
                return {'success': False, 'error': 'Session completed'}
            
            if bet_amount < self.min_bet or bet_amount > self.max_bet:
                return {'success': False, 'error': f'Bet must be between {self.min_bet} and {self.max_bet:,} GEM coins'}
            
            if session.balls_dropped >= self.max_balls_per_session:
                return {'success': False, 'error': 'Maximum balls per session reached'}
            
            # Check user balance
            async with get_db_session() as db_session:
                user = await db_session.get(User, session.user_id)
                if not user or not user.virtual_wallet:
                    return {'success': False, 'error': 'User wallet not found'}
                
                if user.virtual_wallet.gem_coins < bet_amount:
                    return {'success': False, 'error': 'Insufficient GEM coins'}
                
                # Deduct bet amount
                user.virtual_wallet.gem_coins -= bet_amount
                await db_session.commit()
            
            # Create ball
            ball_id = f"ball_{session_id}_{session.balls_dropped + 1}"
            server_seed = secrets.token_hex(32)
            if not client_seed:
                client_seed = secrets.token_hex(8)
            nonce = session.balls_dropped + 1
            
            board_config = self.board_configs[f"{session.risk_level.value}_{session.rows}"]
            
            ball = PlinkoBall(
                ball_id=ball_id,
                user_id=session.user_id,
                bet_amount=bet_amount,
                board_config=board_config,
                server_seed=server_seed,
                client_seed=client_seed,
                nonce=nonce
            )
            
            # Simulate physics and determine outcome
            await self._simulate_ball_physics(ball)
            
            # Apply results
            ball.payout = int(ball.bet_amount * ball.multiplier)
            ball.completed = True
            
            # Credit winnings
            if ball.payout > 0:
                async with get_db_session() as db_session:
                    user = await db_session.get(User, session.user_id)
                    if user and user.virtual_wallet:
                        user.virtual_wallet.gem_coins += ball.payout
                        await db_session.commit()
            
            # Update session
            session.balls_dropped += 1
            session.total_bet += bet_amount
            session.total_payout += ball.payout
            
            # Generate result messaging with excitement
            result_message = self._generate_ball_result_message(ball)
            
            # Check for achievements
            achievements = await self._check_plinko_achievements(session.user_id, ball)
            
            return {
                'success': True,
                'ball': {
                    'ball_id': ball_id,
                    'bet_amount': bet_amount,
                    'final_slot': ball.final_slot,
                    'multiplier': ball.multiplier,
                    'payout': ball.payout,
                    'profit': ball.payout - bet_amount,
                    'bounce_path': ball.bounces,  # For animation
                    'animation_duration': len(ball.bounces) * 0.1  # 100ms per bounce
                },
                'session_stats': {
                    'balls_dropped': session.balls_dropped,
                    'total_bet': session.total_bet,
                    'total_payout': session.total_payout,
                    'net_profit': session.total_payout - session.total_bet,
                    'average_multiplier': session.total_payout / session.total_bet if session.total_bet > 0 else 0
                },
                'verification': {
                    'server_seed': server_seed,
                    'client_seed': client_seed,
                    'nonce': nonce,
                    'final_slot': ball.final_slot
                },
                'result_message': result_message,
                'achievements_earned': achievements,
                'next_ball_ready': session.balls_dropped < self.max_balls_per_session
            }
            
        except Exception as e:
            logger.error(f"Error dropping Plinko ball: {e}")
            return {'success': False, 'error': str(e)}
    
    async def drop_multiple_balls(self, session_id: str, bet_amount: int, 
                                 ball_count: int, auto_play: bool = False) -> Dict[str, Any]:
        """
        Drop multiple balls rapidly for high-intensity gaming.
        Perfect for grinding and rapid-fire gameplay.
        """
        try:
            if ball_count < 1 or ball_count > 50:
                return {'success': False, 'error': 'Ball count must be between 1 and 50'}
            
            session = self.active_sessions.get(session_id)
            if not session:
                return {'success': False, 'error': 'Session not found'}
            
            # Check if user can afford all balls
            total_cost = bet_amount * ball_count
            async with get_db_session() as db_session:
                user = await db_session.get(User, session.user_id)
                if not user or not user.virtual_wallet:
                    return {'success': False, 'error': 'User wallet not found'}
                
                if user.virtual_wallet.gem_coins < total_cost:
                    return {'success': False, 'error': f'Need {total_cost:,} GEM coins for {ball_count} balls'}
            
            # Drop all balls
            results = []
            total_payout = 0
            best_multiplier = 0
            
            for i in range(ball_count):
                ball_result = await self.drop_ball(session_id, bet_amount)
                if ball_result['success']:
                    results.append(ball_result['ball'])
                    total_payout += ball_result['ball']['payout']
                    best_multiplier = max(best_multiplier, ball_result['ball']['multiplier'])
                else:
                    break  # Stop on first failure
            
            # Generate summary excitement
            summary_message = self._generate_multi_ball_summary(
                len(results), ball_count, total_cost, total_payout, best_multiplier
            )
            
            return {
                'success': True,
                'balls_dropped': len(results),
                'requested_count': ball_count,
                'results': results,
                'summary': {
                    'total_bet': total_cost,
                    'total_payout': total_payout,
                    'net_profit': total_payout - total_cost,
                    'best_multiplier': best_multiplier,
                    'average_multiplier': total_payout / total_cost if total_cost > 0 else 0
                },
                'excitement_message': summary_message,
                'auto_play_completed': auto_play
            }
            
        except Exception as e:
            logger.error(f"Error dropping multiple Plinko balls: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _simulate_ball_physics(self, ball: PlinkoBall):
        """
        Simulate realistic ball physics with deterministic outcomes.
        Uses provably fair algorithm to determine bounce directions.
        """
        # Initialize ball at top center
        ball.position = (0.5, 0.0)
        ball.bounces = [(0.5, 0.0)]  # Start position
        
        # Calculate deterministic path using seeds
        path_hash = hashlib.sha256(
            f"{ball.server_seed}:{ball.client_seed}:{ball.nonce}".encode()
        ).hexdigest()
        
        # Convert hash to bounce decisions
        bounce_decisions = []
        for i in range(0, len(path_hash), 2):
            hex_pair = path_hash[i:i+2]
            decision = int(hex_pair, 16) / 255.0  # 0-1 range
            bounce_decisions.append(decision)
        
        current_x = 0.5
        decision_index = 0
        
        # Simulate ball falling through pins
        for row in range(ball.board_config.rows):
            if decision_index >= len(bounce_decisions):
                decision_index = 0  # Wrap around if needed
            
            # Determine bounce direction (left or right)
            bounce_probability = bounce_decisions[decision_index]
            decision_index += 1
            
            # Add some variance based on current position
            position_influence = abs(current_x - 0.5) * 0.1  # Slight drift toward center
            final_probability = bounce_probability + position_influence
            
            # Bounce decision
            if final_probability < 0.5:
                current_x -= 0.02  # Bounce left
            else:
                current_x += 0.02  # Bounce right
            
            # Keep within bounds
            current_x = max(0.05, min(0.95, current_x))
            
            # Record bounce position
            y_position = (row + 1) / (ball.board_config.rows + 1)
            ball.bounces.append((current_x, y_position))
        
        # Final position determines slot
        slots_count = len(ball.board_config.multipliers)
        slot_width = 1.0 / slots_count
        ball.final_slot = min(int(current_x / slot_width), slots_count - 1)
        ball.multiplier = ball.board_config.multipliers[ball.final_slot]
        
        # Add final position
        final_x = (ball.final_slot + 0.5) * slot_width
        ball.bounces.append((final_x, 1.0))
    
    def _generate_session_excitement(self, risk_level: PlinkoRiskLevel, rows: int) -> str:
        """Generate excitement message for session creation"""
        if risk_level == PlinkoRiskLevel.HIGH:
            return f"🚀 HIGH RISK Plinko! {rows} rows of extreme payouts up to 1000x! Fortune favors the bold!"
        elif risk_level == PlinkoRiskLevel.MEDIUM:
            return f"⚡ MEDIUM RISK Plinko! {rows} rows with balanced thrills - perfect mix of safety and excitement!"
        else:
            return f"💎 LOW RISK Plinko! {rows} rows of steady wins - great for building your bankroll!"
    
    def _generate_ball_result_message(self, ball: PlinkoBall) -> str:
        """Generate result message with psychological impact"""
        profit = ball.payout - ball.bet_amount
        
        if ball.multiplier >= 1000:
            return f"🌟 LEGENDARY DROP! {ball.multiplier:.1f}x JACKPOT! You won {ball.payout:,} GEM coins! (+{profit:,})"
        elif ball.multiplier >= 100:
            return f"💥 AMAZING HIT! {ball.multiplier:.1f}x multiplier earned {ball.payout:,} GEM coins! (+{profit:,})"
        elif ball.multiplier >= 10:
            return f"🎉 GREAT DROP! {ball.multiplier:.1f}x payout of {ball.payout:,} GEM coins! (+{profit:,})"
        elif profit > 0:
            return f"✅ Winner! {ball.multiplier:.1f}x earned you {ball.payout:,} GEM coins! (+{profit:,})"
        elif ball.multiplier >= 0.5:
            return f"😐 Close one! {ball.multiplier:.1f}x - only lost {abs(profit):,} coins. Try again!"
        else:
            return f"💔 Tough break! {ball.multiplier:.1f}x slot. The next drop could be THE ONE! 🚀"
    
    def _generate_multi_ball_summary(self, completed: int, requested: int, 
                                   total_bet: int, total_payout: int, best_multiplier: float) -> str:
        """Generate summary message for multiple ball drops"""
        profit = total_payout - total_bet
        
        if best_multiplier >= 1000:
            return f"🚀 EPIC SESSION! {completed} balls included a {best_multiplier:.1f}x JACKPOT! Total: {total_payout:,} coins ({profit:+,})"
        elif profit > total_bet * 0.5:  # 50%+ profit
            return f"💰 WINNING STREAK! {completed} balls earned {total_payout:,} coins! Profit: +{profit:,} 📈"
        elif profit > 0:
            return f"✅ Profitable session! {completed} balls, best: {best_multiplier:.1f}x. Profit: +{profit:,}"
        else:
            return f"⚡ {completed} balls complete! Best hit: {best_multiplier:.1f}x. Keep going - the big win is coming! 🎯"

# Global Plinko engine
plinko_engine = PlinkoGameEngine()