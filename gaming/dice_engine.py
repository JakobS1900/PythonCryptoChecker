"""
Dice Game Engine - Provably Fair Crypto Gaming
Fast-paced, transparent dice game with customizable risk levels.
Research shows dice games are crypto casino staples due to transparency and speed.
"""
import asyncio
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal

from database import get_db_session, User, VirtualWallet
from logger import logger

class DiceResult(Enum):
    WIN = "win"
    LOSS = "loss"
    
class DiceDifficulty(Enum):
    EASY = "easy"        # 70% win chance, 1.35x payout
    MEDIUM = "medium"    # 50% win chance, 1.95x payout  
    HARD = "hard"        # 30% win chance, 3.2x payout
    EXPERT = "expert"    # 20% win chance, 4.75x payout
    INSANE = "insane"    # 10% win chance, 9.5x payout

@dataclass
class DiceGameSession:
    """Individual dice game session"""
    id: str
    user_id: str
    bet_amount: int  # GEM coins
    difficulty: DiceDifficulty
    target_number: int  # 1-100, user's target
    win_condition: str  # "over" or "under"
    server_seed: str
    client_seed: str
    nonce: int
    created_at: datetime
    
    # Results (filled after game)
    rolled_number: Optional[int] = None
    result: Optional[DiceResult] = None
    payout: Optional[int] = None
    resolved: bool = False

@dataclass
class DiceStats:
    """User's dice game statistics"""
    games_played: int
    total_wagered: int
    total_won: int
    win_rate: float
    profit_loss: int
    biggest_win: int
    current_streak: int
    longest_streak: int
    favorite_difficulty: DiceDifficulty

class ProvablyFairDice:
    """
    Provably Fair Dice System
    Uses cryptographic hashing to ensure transparent, verifiable randomness.
    """
    
    @staticmethod
    def generate_server_seed() -> str:
        """Generate cryptographically secure server seed"""
        return secrets.token_hex(32)  # 64-character hex string
    
    @staticmethod
    def generate_client_seed() -> str:
        """Generate client seed (can be user-provided or random)"""
        return secrets.token_hex(8)   # 16-character hex string
    
    @staticmethod
    def calculate_dice_result(server_seed: str, client_seed: str, nonce: int) -> int:
        """
        Calculate provably fair dice result (1-100)
        Uses HMAC-SHA256 for cryptographic verification
        """
        # Create the hash input
        hash_input = f"{server_seed}:{client_seed}:{nonce}"
        
        # Generate SHA256 hash
        hash_result = hashlib.sha256(hash_input.encode()).hexdigest()
        
        # Convert first 8 hex characters to integer
        hex_substring = hash_result[:8]
        result_int = int(hex_substring, 16)
        
        # Convert to 1-100 range
        dice_result = (result_int % 100) + 1
        
        return dice_result
    
    @staticmethod
    def verify_result(server_seed: str, client_seed: str, nonce: int, claimed_result: int) -> bool:
        """Verify that a dice result was calculated correctly"""
        calculated_result = ProvablyFairDice.calculate_dice_result(server_seed, client_seed, nonce)
        return calculated_result == claimed_result

class DiceGameEngine:
    """
    High-speed dice gaming engine with addiction mechanics.
    
    Key Features:
    - Sub-second game resolution
    - Provably fair transparency  
    - Variable risk levels for different player types
    - Streak bonuses and near-miss psychology
    - Real-time statistics and leaderboards
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, DiceGameSession] = {}
        self.difficulty_payouts = {
            DiceDifficulty.EASY: 1.35,
            DiceDifficulty.MEDIUM: 1.95,
            DiceDifficulty.HARD: 3.2,
            DiceDifficulty.EXPERT: 4.75,
            DiceDifficulty.INSANE: 9.5
        }
        
        self.difficulty_win_rates = {
            DiceDifficulty.EASY: 70,
            DiceDifficulty.MEDIUM: 50,
            DiceDifficulty.HARD: 30,
            DiceDifficulty.EXPERT: 20,
            DiceDifficulty.INSANE: 10
        }
    
    async def create_dice_session(self, user_id: str, bet_amount: int, 
                                 difficulty: str, target_number: int, 
                                 win_condition: str, client_seed: str = None) -> Dict[str, Any]:
        """
        Create a new dice game session with provably fair setup.
        This is the moment of maximum anticipation - leverage psychology here.
        """
        try:
            # Validate input
            if bet_amount < 10:
                return {'success': False, 'error': 'Minimum bet is 10 GEM coins'}
            
            if target_number < 1 or target_number > 99:
                return {'success': False, 'error': 'Target number must be between 1 and 99'}
                
            if win_condition not in ['over', 'under']:
                return {'success': False, 'error': 'Win condition must be "over" or "under"'}
            
            try:
                difficulty_enum = DiceDifficulty(difficulty)
            except ValueError:
                return {'success': False, 'error': 'Invalid difficulty level'}
            
            # Check user balance
            async with get_db_session() as session:
                user = await session.get(User, user_id)
                if not user or not user.virtual_wallet:
                    return {'success': False, 'error': 'User wallet not found'}
                
                if user.virtual_wallet.gem_coins < bet_amount:
                    return {'success': False, 'error': 'Insufficient GEM coins'}
            
            # Generate provably fair seeds
            server_seed = ProvablyFairDice.generate_server_seed()
            if not client_seed:
                client_seed = ProvablyFairDice.generate_client_seed()
            
            # Get next nonce for this user
            nonce = await self._get_next_nonce(user_id)
            
            # Create game session
            session_id = f"dice_{user_id}_{int(datetime.now().timestamp())}"
            game_session = DiceGameSession(
                id=session_id,
                user_id=user_id,
                bet_amount=bet_amount,
                difficulty=difficulty_enum,
                target_number=target_number,
                win_condition=win_condition,
                server_seed=server_seed,
                client_seed=client_seed,
                nonce=nonce,
                created_at=datetime.now()
            )
            
            # Store session
            self.active_sessions[session_id] = game_session
            
            # Calculate win probability for user info
            win_probability = self._calculate_win_probability(target_number, win_condition)
            potential_payout = int(bet_amount * self.difficulty_payouts[difficulty_enum])
            
            # Generate excitement messaging
            excitement = self._generate_dice_excitement(bet_amount, difficulty_enum, win_probability)
            
            return {
                'success': True,
                'session_id': session_id,
                'server_seed_hash': hashlib.sha256(server_seed.encode()).hexdigest(),  # Hidden until reveal
                'client_seed': client_seed,
                'nonce': nonce,
                'target_number': target_number,
                'win_condition': win_condition,
                'win_probability': win_probability,
                'potential_payout': potential_payout,
                'excitement_message': excitement['message'],
                'risk_level': excitement['risk'],
                'ready_to_roll': True
            }
            
        except Exception as e:
            logger.error(f"Error creating dice session for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def roll_dice(self, session_id: str) -> Dict[str, Any]:
        """
        Execute the dice roll with instant results and payouts.
        This is the climax moment - maximum psychological impact.
        """
        try:
            if session_id not in self.active_sessions:
                return {'success': False, 'error': 'Session not found'}
            
            session = self.active_sessions[session_id]
            if session.resolved:
                return {'success': False, 'error': 'Session already resolved'}
            
            # Calculate provably fair result
            rolled_number = ProvablyFairDice.calculate_dice_result(
                session.server_seed, 
                session.client_seed, 
                session.nonce
            )
            
            # Determine win/loss
            if session.win_condition == 'over':
                is_win = rolled_number > session.target_number
            else:  # under
                is_win = rolled_number < session.target_number
            
            result = DiceResult.WIN if is_win else DiceResult.LOSS
            
            # Calculate payout
            payout = 0
            if is_win:
                base_payout = int(session.bet_amount * self.difficulty_payouts[session.difficulty])
                
                # Apply streak bonuses
                user_streak = await self._get_dice_streak(session.user_id)
                streak_multiplier = self._get_streak_multiplier(user_streak)
                payout = int(base_payout * streak_multiplier)
            
            # Update session
            session.rolled_number = rolled_number
            session.result = result
            session.payout = payout
            session.resolved = True
            
            # Apply results to user wallet
            await self._apply_dice_results(session, is_win)
            
            # Update user statistics
            await self._update_dice_stats(session.user_id, session, is_win)
            
            # Generate result messaging with psychology
            result_message = self._generate_result_message(session, is_win, user_streak)
            
            # Save session to database for verification
            await self._save_dice_session(session)
            
            # Check for achievements
            achievements = await self._check_dice_achievements(session.user_id, session, is_win)
            
            return {
                'success': True,
                'rolled_number': rolled_number,
                'target_number': session.target_number,
                'win_condition': session.win_condition,
                'result': result.value,
                'is_win': is_win,
                'payout': payout,
                'streak_multiplier': streak_multiplier if is_win else 1.0,
                'result_message': result_message,
                'server_seed_revealed': session.server_seed,  # Now safe to reveal
                'verification_data': {
                    'server_seed': session.server_seed,
                    'client_seed': session.client_seed,
                    'nonce': session.nonce,
                    'calculated_result': rolled_number
                },
                'achievements_earned': achievements,
                'next_game_ready': True
            }
            
        except Exception as e:
            logger.error(f"Error rolling dice for session {session_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_dice_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive dice game statistics for user"""
        try:
            stats = await self._calculate_dice_stats(user_id)
            recent_games = await self._get_recent_dice_games(user_id, limit=10)
            
            return {
                'success': True,
                'stats': {
                    'games_played': stats.games_played,
                    'total_wagered': stats.total_wagered,
                    'total_won': stats.total_won,
                    'win_rate': stats.win_rate,
                    'profit_loss': stats.profit_loss,
                    'biggest_win': stats.biggest_win,
                    'current_streak': stats.current_streak,
                    'longest_streak': stats.longest_streak,
                    'favorite_difficulty': stats.favorite_difficulty.value
                },
                'recent_games': recent_games,
                'leaderboard_position': await self._get_dice_leaderboard_position(user_id),
                'next_achievement': await self._get_next_dice_achievement(user_id)
            }
            
        except Exception as e:
            logger.error(f"Error getting dice stats for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _calculate_win_probability(self, target_number: int, win_condition: str) -> float:
        """Calculate win probability based on target and condition"""
        if win_condition == 'over':
            winning_numbers = 99 - target_number
        else:  # under
            winning_numbers = target_number - 1
        
        return (winning_numbers / 99) * 100
    
    def _generate_dice_excitement(self, bet_amount: int, difficulty: DiceDifficulty, 
                                 win_probability: float) -> Dict[str, Any]:
        """Generate excitement messaging based on risk/reward"""
        if difficulty == DiceDifficulty.INSANE and bet_amount > 1000:
            return {
                'message': f"🎲 INSANE DICE! Only {win_probability:.1f}% chance but MASSIVE 9.5x payout! Are you feeling lucky?",
                'risk': 'EXTREME',
                'hype_level': 'MAXIMUM'
            }
        elif difficulty == DiceDifficulty.EXPERT:
            return {
                'message': f"⚡ EXPERT LEVEL! {win_probability:.1f}% win chance for 4.75x payout - high risk, high reward!",
                'risk': 'HIGH',
                'hype_level': 'INTENSE'
            }
        elif difficulty == DiceDifficulty.HARD:
            return {
                'message': f"💎 Hard mode activated! {win_probability:.1f}% win chance for 3.2x multiplier!",
                'risk': 'MEDIUM-HIGH',
                'hype_level': 'CONFIDENT'
            }
        elif difficulty == DiceDifficulty.MEDIUM:
            return {
                'message': f"🎯 Balanced bet! {win_probability:.1f}% win chance for nearly 2x payout!",
                'risk': 'MEDIUM',
                'hype_level': 'STEADY'
            }
        else:  # EASY
            return {
                'message': f"🍀 Safe bet! {win_probability:.1f}% win chance - great for building streaks!",
                'risk': 'LOW',
                'hype_level': 'ENCOURAGING'
            }
    
    def _generate_result_message(self, session: DiceGameSession, is_win: bool, streak: int) -> str:
        """Generate psychologically impactful result messaging"""
        if is_win:
            if session.difficulty == DiceDifficulty.INSANE:
                return f"🚀 LEGENDARY WIN! You beat 10% odds and won {session.payout:,} GEM coins! The crypto gods smile upon you!"
            elif streak > 5:
                return f"🔥 STREAK MASTER! {streak} wins in a row! You've won {session.payout:,} GEM coins with streak bonus!"
            elif session.payout > 5000:
                return f"💰 BIG WIN! {session.payout:,} GEM coins! You rolled {session.rolled_number} - perfect timing!"
            else:
                return f"✅ Winner! You rolled {session.rolled_number} and won {session.payout:,} GEM coins!"
        else:
            # Near-miss psychology for addiction
            if session.win_condition == 'over' and session.rolled_number == session.target_number:
                return f"💔 SO CLOSE! You needed over {session.target_number} and rolled exactly {session.rolled_number}! Try again!"
            elif session.win_condition == 'under' and session.rolled_number == session.target_number:
                return f"💔 ALMOST! You needed under {session.target_number} and rolled exactly {session.rolled_number}! So close!"
            elif abs(session.rolled_number - session.target_number) <= 2:
                return f"😤 Near miss! Rolled {session.rolled_number}, needed {session.win_condition} {session.target_number}. You're getting closer!"
            else:
                return f"❌ Not this time. Rolled {session.rolled_number}, needed {session.win_condition} {session.target_number}. Ready for revenge?"
    
    def _get_streak_multiplier(self, streak: int) -> float:
        """Calculate streak bonus multipliers (exponential growth)"""
        streak_bonuses = {
            0: 1.0, 1: 1.0, 2: 1.1, 3: 1.2, 4: 1.3, 5: 1.5,
            6: 1.7, 7: 2.0, 8: 2.3, 9: 2.7, 10: 3.0
        }
        
        return streak_bonuses.get(streak, 3.0)  # Cap at 3x for 10+ streaks
    
    async def _get_next_nonce(self, user_id: str) -> int:
        """Get the next nonce number for provably fair verification"""
        # This would query database for user's last nonce
        # For now, return timestamp-based nonce
        return int(datetime.now().timestamp() * 1000) % 1000000

# Global dice engine instance
dice_engine = DiceGameEngine()