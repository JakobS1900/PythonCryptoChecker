"""
Tower Climbing Game Engine - Strategic Risk/Reward Progression
High-tension tower climbing with strategic decision-making at each level.
Research shows tower games create maximum suspense through escalating risk/reward choices.
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

class TowerDifficulty(Enum):
    EASY = "easy"         # 3 safe spots, 1 mine per level (75% success chance)
    MEDIUM = "medium"     # 2 safe spots, 2 mines per level (50% success chance)  
    HARD = "hard"         # 1 safe spot, 3 mines per level (25% success chance)
    EXPERT = "expert"     # 1 safe spot, 4 mines per level (20% success chance)

class TowerAction(Enum):
    CLIMB = "climb"       # Continue to next level
    CASH_OUT = "cash_out" # Take current winnings and end game

class TowerGameState(Enum):
    ACTIVE = "active"     # Game in progress
    CASHED_OUT = "cashed_out"  # Player cashed out successfully
    EXPLODED = "exploded"      # Hit a mine, game over

@dataclass
class TowerLevel:
    """Individual tower level with safe spots and mines"""
    level: int
    safe_spots: List[int]      # Safe tile positions (0-4)
    mine_positions: List[int]  # Mine positions (0-4)  
    multiplier: float         # Current multiplier at this level
    revealed_tiles: List[int] = None  # Tiles player has revealed
    completed: bool = False

@dataclass
class TowerGame:
    """Complete tower climbing game session"""
    game_id: str
    user_id: str
    bet_amount: int
    difficulty: TowerDifficulty
    created_at: datetime
    
    # Game progression
    current_level: int = 0
    levels: List[TowerLevel] = None
    current_multiplier: float = 1.0
    potential_payout: int = 0
    
    # Game state
    state: TowerGameState = TowerGameState.ACTIVE
    final_payout: int = 0
    exploded_tile: Optional[int] = None
    cash_out_level: Optional[int] = None
    
    # Provably fair
    server_seed: str = None
    client_seed: str = None
    nonce: int = None
    
    def __post_init__(self):
        if self.levels is None:
            self.levels = []
        if self.revealed_tiles is None:
            self.revealed_tiles = []

class TowerGameEngine:
    """
    Strategic tower climbing game with maximum tension mechanics.
    
    Key Features:
    - Escalating multipliers with increasing risk
    - Strategic cash-out decisions at each level
    - Provably fair mine placement
    - Visual tension through progressive revelation
    - FOMO mechanics (what if you climbed one more level?)
    - Social sharing of epic climbs and close calls
    """
    
    def __init__(self):
        self.active_games: Dict[str, TowerGame] = {}
        self.max_levels = 20  # Maximum tower height
        self.tiles_per_level = 5  # 5 tiles to choose from each level
        
        # Difficulty configurations
        self.difficulty_configs = {
            TowerDifficulty.EASY: {
                'safe_spots': 3,
                'mines': 1,
                'base_multiplier': 1.33,  # 33% increase per level
                'description': '75% success chance - steady climb'
            },
            TowerDifficulty.MEDIUM: {
                'safe_spots': 2,
                'mines': 2,  
                'base_multiplier': 2.0,   # 100% increase per level
                'description': '50% success chance - balanced risk'
            },
            TowerDifficulty.HARD: {
                'safe_spots': 1,
                'mines': 3,
                'base_multiplier': 4.0,   # 300% increase per level  
                'description': '25% success chance - high risk'
            },
            TowerDifficulty.EXPERT: {
                'safe_spots': 1,
                'mines': 4,
                'base_multiplier': 5.0,   # 400% increase per level
                'description': '20% success chance - EXTREME risk'
            }
        }
        
        # Game limits
        self.min_bet = 10
        self.max_bet = 100000
    
    async def start_tower_game(self, user_id: str, bet_amount: int, 
                              difficulty: str, client_seed: str = None) -> Dict[str, Any]:
        """
        Start a new tower climbing game.
        This creates initial excitement and strategic planning.
        """
        try:
            # Validate inputs
            if bet_amount < self.min_bet or bet_amount > self.max_bet:
                return {'success': False, 'error': f'Bet must be between {self.min_bet:,} and {self.max_bet:,} GEM coins'}
            
            try:
                difficulty_enum = TowerDifficulty(difficulty)
            except ValueError:
                return {'success': False, 'error': 'Invalid difficulty level'}
            
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
            
            # Generate provably fair seeds
            server_seed = secrets.token_hex(32)
            if not client_seed:
                client_seed = secrets.token_hex(8)
            nonce = int(datetime.now().timestamp() * 1000) % 1000000
            
            # Create game
            game_id = f"tower_{user_id}_{int(datetime.now().timestamp())}"
            game = TowerGame(
                game_id=game_id,
                user_id=user_id,
                bet_amount=bet_amount,
                difficulty=difficulty_enum,
                created_at=datetime.now(),
                server_seed=server_seed,
                client_seed=client_seed,
                nonce=nonce
            )
            
            # Generate first level
            first_level = await self._generate_tower_level(game, 1)
            game.levels.append(first_level)
            game.current_level = 1
            game.current_multiplier = 1.0
            game.potential_payout = bet_amount
            
            # Store game
            self.active_games[game_id] = game
            
            # Generate excitement message
            excitement = self._generate_game_start_excitement(difficulty_enum, bet_amount)
            
            return {
                'success': True,
                'game_id': game_id,
                'difficulty': difficulty,
                'bet_amount': bet_amount,
                'current_level': 1,
                'max_levels': self.max_levels,
                'tiles_per_level': self.tiles_per_level,
                'difficulty_info': self.difficulty_configs[difficulty_enum],
                'current_multiplier': 1.0,
                'potential_payout': bet_amount,
                'level_layout': {
                    'safe_spots_count': self.difficulty_configs[difficulty_enum]['safe_spots'],
                    'mine_count': self.difficulty_configs[difficulty_enum]['mines'],
                    'tiles': list(range(self.tiles_per_level))  # Available tiles to click
                },
                'excitement_message': excitement,
                'strategy_tip': self._get_strategy_tip(difficulty_enum, 1)
            }
            
        except Exception as e:
            logger.error(f"Error starting tower game for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def reveal_tile(self, game_id: str, tile_position: int) -> Dict[str, Any]:
        """
        Reveal a tile at the current level.
        This is the moment of maximum tension - safe spot or mine?
        """
        try:
            if game_id not in self.active_games:
                return {'success': False, 'error': 'Game not found'}
            
            game = self.active_games[game_id]
            if game.state != TowerGameState.ACTIVE:
                return {'success': False, 'error': 'Game is not active'}
            
            if tile_position < 0 or tile_position >= self.tiles_per_level:
                return {'success': False, 'error': 'Invalid tile position'}
            
            current_level = game.levels[game.current_level - 1]
            
            # Check if tile already revealed
            if current_level.revealed_tiles and tile_position in current_level.revealed_tiles:
                return {'success': False, 'error': 'Tile already revealed'}
            
            # Initialize revealed tiles if needed
            if not current_level.revealed_tiles:
                current_level.revealed_tiles = []
            
            # Reveal the tile
            current_level.revealed_tiles.append(tile_position)
            
            # Check if it's a mine
            is_mine = tile_position in current_level.mine_positions
            
            if is_mine:
                # BOOM! Game over
                game.state = TowerGameState.EXPLODED
                game.exploded_tile = tile_position
                game.final_payout = 0
                
                # Generate dramatic explosion message
                explosion_message = self._generate_explosion_message(game)
                
                return {
                    'success': True,
                    'tile_revealed': tile_position,
                    'is_mine': True,
                    'game_over': True,
                    'state': 'exploded',
                    'final_payout': 0,
                    'level_reached': game.current_level,
                    'explosion_message': explosion_message,
                    'mine_positions': current_level.mine_positions,  # Reveal all mines
                    'almost_won': game.current_multiplier * game.bet_amount,  # What they almost won
                    'next_game_ready': True
                }
            
            else:
                # Safe spot! Calculate new multiplier
                config = self.difficulty_configs[game.difficulty]
                level_multiplier = config['base_multiplier']
                
                # Update multiplier (exponential growth)
                game.current_multiplier *= level_multiplier
                game.potential_payout = int(game.bet_amount * game.current_multiplier)
                
                # Check if level is complete
                safe_spots_revealed = len([pos for pos in current_level.revealed_tiles if pos in current_level.safe_spots])
                level_complete = safe_spots_revealed >= config['safe_spots']
                
                if level_complete:
                    current_level.completed = True
                
                # Generate success message with strategic tension
                success_message = self._generate_safe_tile_message(game, level_complete)
                
                # Prepare response
                response = {
                    'success': True,
                    'tile_revealed': tile_position,
                    'is_mine': False,
                    'is_safe': True,
                    'level_complete': level_complete,
                    'current_level': game.current_level,
                    'current_multiplier': game.current_multiplier,
                    'potential_payout': game.potential_payout,
                    'safe_spots_found': safe_spots_revealed,
                    'safe_spots_needed': config['safe_spots'],
                    'success_message': success_message,
                    'can_cash_out': True,
                    'can_continue': level_complete and game.current_level < self.max_levels
                }
                
                # If level complete, show next level preview
                if level_complete and game.current_level < self.max_levels:
                    next_level_info = await self._preview_next_level(game)
                    response['next_level_preview'] = next_level_info
                
                return response
            
        except Exception as e:
            logger.error(f"Error revealing tile in game {game_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def cash_out(self, game_id: str) -> Dict[str, Any]:
        """
        Cash out current winnings and end the game.
        This requires strategic decision-making under pressure.
        """
        try:
            if game_id not in self.active_games:
                return {'success': False, 'error': 'Game not found'}
            
            game = self.active_games[game_id]
            if game.state != TowerGameState.ACTIVE:
                return {'success': False, 'error': 'Game is not active'}
            
            # Calculate final payout
            game.state = TowerGameState.CASHED_OUT
            game.cash_out_level = game.current_level
            game.final_payout = game.potential_payout
            
            # Credit user wallet
            if game.final_payout > 0:
                async with get_db_session() as session:
                    user = await session.get(User, game.user_id)
                    if user and user.virtual_wallet:
                        user.virtual_wallet.gem_coins += game.final_payout
                        await session.commit()
            
            # Calculate what they could have won
            max_possible_payout = await self._calculate_max_possible_payout(game)
            
            # Generate cash-out celebration
            cashout_message = self._generate_cashout_celebration(game, max_possible_payout)
            
            # Update user statistics
            await self._update_tower_stats(game.user_id, game)
            
            # Check for achievements
            achievements = await self._check_tower_achievements(game.user_id, game)
            
            return {
                'success': True,
                'cashed_out': True,
                'final_payout': game.final_payout,
                'profit': game.final_payout - game.bet_amount,
                'levels_climbed': game.current_level,
                'final_multiplier': game.current_multiplier,
                'cashout_message': cashout_message,
                'statistics': {
                    'max_possible_payout': max_possible_payout,
                    'payout_percentage': (game.final_payout / max_possible_payout * 100) if max_possible_payout > 0 else 0,
                    'risk_assessment': self._assess_cashout_timing(game)
                },
                'achievements_earned': achievements,
                'leaderboard_impact': await self._check_leaderboard_impact(game.user_id, game),
                'next_game_ready': True
            }
            
        except Exception as e:
            logger.error(f"Error cashing out game {game_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def climb_to_next_level(self, game_id: str) -> Dict[str, Any]:
        """
        Continue climbing to the next level.
        This escalates tension and risk for potentially massive rewards.
        """
        try:
            if game_id not in self.active_games:
                return {'success': False, 'error': 'Game not found'}
            
            game = self.active_games[game_id]
            if game.state != TowerGameState.ACTIVE:
                return {'success': False, 'error': 'Game is not active'}
            
            if game.current_level >= self.max_levels:
                return {'success': False, 'error': 'Already at maximum level'}
            
            # Check if current level is complete
            current_level = game.levels[game.current_level - 1]
            if not current_level.completed:
                return {'success': False, 'error': 'Current level not complete'}
            
            # Generate next level
            next_level = await self._generate_tower_level(game, game.current_level + 1)
            game.levels.append(next_level)
            game.current_level += 1
            
            # Generate climbing excitement
            climb_message = self._generate_climb_excitement(game)
            
            return {
                'success': True,
                'climbed': True,
                'new_level': game.current_level,
                'current_multiplier': game.current_multiplier,
                'potential_payout': game.potential_payout,
                'level_layout': {
                    'safe_spots_count': self.difficulty_configs[game.difficulty]['safe_spots'],
                    'mine_count': self.difficulty_configs[game.difficulty]['mines'],
                    'tiles': list(range(self.tiles_per_level))
                },
                'climb_message': climb_message,
                'strategy_tip': self._get_strategy_tip(game.difficulty, game.current_level),
                'risk_warning': self._get_risk_warning(game.current_level, game.potential_payout),
                'is_final_level': game.current_level >= self.max_levels
            }
            
        except Exception as e:
            logger.error(f"Error climbing to next level in game {game_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _generate_tower_level(self, game: TowerGame, level: int) -> TowerLevel:
        """Generate a provably fair tower level with mines and safe spots"""
        config = self.difficulty_configs[game.difficulty]
        
        # Use provably fair algorithm to determine mine positions
        level_hash = hashlib.sha256(
            f"{game.server_seed}:{game.client_seed}:{game.nonce}:{level}".encode()
        ).hexdigest()
        
        # Convert hash to tile positions
        available_positions = list(range(self.tiles_per_level))
        mine_positions = []
        
        # Select mine positions deterministically
        for i in range(config['mines']):
            if not available_positions:
                break
                
            # Use hash bytes to select position
            hash_index = (i * 2) % len(level_hash)
            position_index = int(level_hash[hash_index:hash_index+2], 16) % len(available_positions)
            
            mine_positions.append(available_positions.pop(position_index))
        
        # Remaining positions are safe spots
        safe_spots = available_positions
        
        return TowerLevel(
            level=level,
            safe_spots=safe_spots,
            mine_positions=mine_positions,
            multiplier=game.current_multiplier * config['base_multiplier'],
            revealed_tiles=[]
        )
    
    def _generate_game_start_excitement(self, difficulty: TowerDifficulty, bet_amount: int) -> str:
        """Generate excitement message for game start"""
        if difficulty == TowerDifficulty.EXPERT and bet_amount > 10000:
            return f"🚀 EXPERT TOWER! {bet_amount:,} GEM coins on EXTREME difficulty! This could be LEGENDARY!"
        elif difficulty == TowerDifficulty.HARD:
            return f"⚡ HARD TOWER! 25% success rate but MASSIVE multipliers! Ready to be brave?"
        elif difficulty == TowerDifficulty.MEDIUM:
            return f"🎯 MEDIUM TOWER! Balanced risk for solid rewards - perfect for strategic climbing!"
        else:
            return f"💎 EASY TOWER! Great for steady progress and building confidence. Let's climb!"
    
    def _generate_safe_tile_message(self, game: TowerGame, level_complete: bool) -> str:
        """Generate message for revealing safe tile"""
        if level_complete and game.current_level >= 15:
            return f"🌟 LEVEL {game.current_level} COMPLETE! You're in the ELITE zone! Current value: {game.potential_payout:,} coins!"
        elif level_complete and game.current_level >= 10:
            return f"🔥 LEVEL {game.current_level} CLEARED! You're on fire! Worth: {game.potential_payout:,} coins!"
        elif level_complete:
            return f"✅ LEVEL {game.current_level} COMPLETE! {game.current_multiplier:.2f}x multiplier! Worth: {game.potential_payout:,} coins!"
        else:
            return f"💎 Safe tile! {game.current_multiplier:.2f}x multiplier building... Keep going or cash out?"
    
    def _generate_explosion_message(self, game: TowerGame) -> str:
        """Generate dramatic message for mine explosion"""
        almost_won = int(game.current_multiplier * game.bet_amount)
        
        if game.current_level >= 15:
            return f"💥 NOOO! Level {game.current_level} mine! You were SO close to {almost_won:,} coins! That was ELITE territory!"
        elif game.current_level >= 10:
            return f"💣 BOOM! Level {game.current_level} explosion! You almost had {almost_won:,} coins! Try again!"
        elif almost_won > game.bet_amount * 5:
            return f"💔 Mine hit! You were about to win {almost_won:,} coins! So close to a big payout!"
        else:
            return f"💥 Mine! Better luck next time - the tower is waiting for your return!"
    
    def _get_strategy_tip(self, difficulty: TowerDifficulty, level: int) -> str:
        """Provide strategic tips based on difficulty and level"""
        if level <= 3:
            return "Early levels are perfect for building confidence. Consider your risk tolerance!"
        elif level <= 7:
            return "Mid-tower decision point! Your winnings are growing - cash out or climb higher?"  
        elif level <= 12:
            return "High stakes territory! Each level is worth significant money. Play smart!"
        else:
            return "ELITE TOWER LEVELS! You're in legendary territory. Fortune favors the bold!"

# Global tower engine
tower_engine = TowerGameEngine()