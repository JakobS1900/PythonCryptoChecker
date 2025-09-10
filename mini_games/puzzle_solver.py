"""
Crypto Puzzle Solver Mini-Game
Sliding puzzles, jigsaw puzzles, and crypto-themed brain teasers for GEM rewards.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, JSON
from database import Base, get_db_session
from gamification import VirtualEconomyEngine, RewardBundle
from logger import logger


class PuzzleType(Enum):
    SLIDING_PUZZLE = "SLIDING_PUZZLE"      # 15-puzzle style
    JIGSAW = "JIGSAW"                      # Jigsaw pieces
    CRYPTO_CIPHER = "CRYPTO_CIPHER"        # Crypto-themed word puzzles
    LOGIC_GRID = "LOGIC_GRID"              # Logic grid puzzles
    CRYPTO_MATH = "CRYPTO_MATH"            # Math puzzles with crypto themes


class PuzzleDifficulty(Enum):
    EASY = "EASY"           # 3x3 or simple puzzles
    MEDIUM = "MEDIUM"       # 4x4 or moderate complexity
    HARD = "HARD"           # 4x4 with more complex patterns
    EXPERT = "EXPERT"       # 5x5 or very challenging


@dataclass
class PuzzlePiece:
    """Individual puzzle piece."""
    id: int
    current_position: int
    correct_position: int
    content: str  # Could be number, crypto symbol, or image reference
    is_fixed: bool = False  # Some pieces might be fixed as hints


class PuzzleSolverSession(Base):
    """Database model for puzzle solver game sessions."""
    __tablename__ = "puzzle_solver_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    
    # Puzzle Configuration
    puzzle_type = Column(String)
    difficulty = Column(String)
    grid_size = Column(String)  # "3x3", "4x4", etc.
    
    # Game State
    game_state = Column(String, default="ACTIVE")  # ACTIVE, COMPLETED, ABANDONED
    puzzle_data = Column(JSON)  # Current puzzle state
    solution_data = Column(JSON)  # Target solution
    moves_made = Column(Integer, default=0)
    hints_used = Column(Integer, default=0)
    
    # Performance Metrics
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    time_taken_seconds = Column(Float)
    efficiency_score = Column(Float)  # Based on optimal moves vs actual
    
    # Rewards
    gem_coins_earned = Column(Float, default=0.0)
    xp_earned = Column(Integer, default=0)
    difficulty_bonus = Column(Float, default=0.0)
    speed_bonus = Column(Float, default=0.0)
    efficiency_bonus = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PuzzleSolverGame:
    """Crypto-themed puzzle solver game for earning GEM coins."""
    
    CRYPTO_SYMBOLS = ["₿", "Ξ", "₳", "●", "Ð", "Ł", "✕", "◎", "🔺", "⬟", "🔗", "🦄", "⚛", "🌿", "∞", "△", "⭐", "📁"]
    
    CRYPTO_WORDS = [
        "BITCOIN", "ETHEREUM", "BLOCKCHAIN", "MINING", "WALLET", "DEFI", "NFT", "SMART",
        "CONTRACT", "HODL", "STAKING", "YIELD", "CRYPTO", "TOKEN", "COIN", "HASH",
        "SATOSHI", "LAMBO", "MOON", "DIAMOND", "HANDS", "WHALE", "PUMP", "DUMP"
    ]
    
    def __init__(self, virtual_economy: VirtualEconomyEngine):
        self.virtual_economy = virtual_economy
    
    def _generate_sliding_puzzle(self, difficulty: PuzzleDifficulty) -> Tuple[List[List[int]], List[List[int]]]:
        """Generate a sliding puzzle (15-puzzle style)."""
        
        size_map = {
            PuzzleDifficulty.EASY: 3,
            PuzzleDifficulty.MEDIUM: 4,
            PuzzleDifficulty.HARD: 4,
            PuzzleDifficulty.EXPERT: 5
        }
        
        size = size_map[difficulty]
        
        # Create solved state (0 represents empty space)
        solved = []
        num = 1
        for i in range(size):
            row = []
            for j in range(size):
                if i == size - 1 and j == size - 1:
                    row.append(0)  # Empty space at bottom right
                else:
                    row.append(num)
                    num += 1
            solved.append(row)
        
        # Create shuffled state by making random valid moves
        current = [row[:] for row in solved]  # Deep copy
        empty_row, empty_col = size - 1, size - 1
        
        # Make random moves to shuffle
        moves_to_shuffle = {
            PuzzleDifficulty.EASY: 50,
            PuzzleDifficulty.MEDIUM: 100,
            PuzzleDifficulty.HARD: 150,
            PuzzleDifficulty.EXPERT: 200
        }[difficulty]
        
        for _ in range(moves_to_shuffle):
            # Get possible moves (adjacent to empty space)
            possible_moves = []
            if empty_row > 0:
                possible_moves.append((empty_row - 1, empty_col))
            if empty_row < size - 1:
                possible_moves.append((empty_row + 1, empty_col))
            if empty_col > 0:
                possible_moves.append((empty_row, empty_col - 1))
            if empty_col < size - 1:
                possible_moves.append((empty_row, empty_col + 1))
            
            # Make random move
            move_row, move_col = random.choice(possible_moves)
            current[empty_row][empty_col] = current[move_row][move_col]
            current[move_row][move_col] = 0
            empty_row, empty_col = move_row, move_col
        
        return current, solved
    
    def _generate_crypto_cipher(self, difficulty: PuzzleDifficulty) -> Dict[str, Any]:
        """Generate a crypto-themed cipher puzzle."""
        
        word = random.choice(self.CRYPTO_WORDS)
        
        if difficulty == PuzzleDifficulty.EASY:
            # Simple Caesar cipher
            shift = random.randint(1, 5)
            cipher_word = ""
            for char in word:
                if char.isalpha():
                    shifted = ord(char) - ord('A')
                    shifted = (shifted + shift) % 26
                    cipher_word += chr(shifted + ord('A'))
                else:
                    cipher_word += char
            
            hint = f"Caesar cipher with shift {shift}"
            
        elif difficulty == PuzzleDifficulty.MEDIUM:
            # Substitution cipher with crypto symbols
            cipher_map = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 
                                random.sample(self.CRYPTO_SYMBOLS, 26) if len(self.CRYPTO_SYMBOLS) >= 26 
                                else self.CRYPTO_SYMBOLS + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")[len(self.CRYPTO_SYMBOLS):]))
            
            cipher_word = "".join(cipher_map.get(char, char) for char in word)
            hint = f"Each letter maps to a crypto symbol"
            
        else:  # HARD/EXPERT
            # Reverse + symbol substitution
            reversed_word = word[::-1]
            cipher_map = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 
                                random.sample(list("ZYXWVUTSRQPONMLKJIHGFEDCBA"), 26)))
            cipher_word = "".join(cipher_map.get(char, char) for char in reversed_word)
            hint = "Word is reversed and each letter substituted"
        
        return {
            "cipher_text": cipher_word,
            "solution": word,
            "hint": hint,
            "puzzle_type": "cipher"
        }
    
    def _generate_logic_grid(self, difficulty: PuzzleDifficulty) -> Dict[str, Any]:
        """Generate a crypto-themed logic grid puzzle."""
        
        cryptos = ["Bitcoin", "Ethereum", "Cardano", "Solana", "Dogecoin"][:3 if difficulty == PuzzleDifficulty.EASY else 5]
        prices = ["$100", "$1000", "$10000", "$50000", "$100000"][:len(cryptos)]
        holders = ["Alice", "Bob", "Charlie", "Diana", "Eve"][:len(cryptos)]
        
        # Create solution
        solution = list(zip(cryptos, prices, holders))
        random.shuffle(solution)
        
        # Generate clues
        clues = []
        if difficulty == PuzzleDifficulty.EASY:
            clues = [
                f"{solution[0][2]} owns {solution[0][0]}",
                f"{solution[1][0]} is worth {solution[1][1]}",
                f"The person with {solution[2][0]} is {solution[2][2]}"
            ]
        else:
            # More complex clues for harder difficulties
            clues = [
                f"{solution[0][2]} doesn't own the most expensive crypto",
                f"{solution[1][0]} is worth more than {solution[2][0]}",
                f"Either {solution[0][2]} or {solution[1][2]} owns {solution[0][0]}",
                f"The {solution[-1][1]} crypto belongs to {solution[-1][2]}"
            ]
        
        return {
            "cryptos": cryptos,
            "prices": prices,
            "holders": holders,
            "clues": clues,
            "solution": solution,
            "puzzle_type": "logic_grid"
        }
    
    async def start_new_puzzle(
        self,
        session: AsyncSession,
        user_id: str,
        puzzle_type: PuzzleType = PuzzleType.SLIDING_PUZZLE,
        difficulty: PuzzleDifficulty = PuzzleDifficulty.EASY
    ) -> Dict[str, Any]:
        """Start a new puzzle solving session."""
        
        puzzle_data = None
        solution_data = None
        
        if puzzle_type == PuzzleType.SLIDING_PUZZLE:
            current_state, solved_state = self._generate_sliding_puzzle(difficulty)
            puzzle_data = {"grid": current_state, "empty_pos": self._find_empty_position(current_state)}
            solution_data = {"grid": solved_state}
            grid_size = f"{len(current_state)}x{len(current_state[0])}"
            
        elif puzzle_type == PuzzleType.CRYPTO_CIPHER:
            cipher_puzzle = self._generate_crypto_cipher(difficulty)
            puzzle_data = cipher_puzzle
            solution_data = {"solution": cipher_puzzle["solution"]}
            grid_size = f"{len(cipher_puzzle['cipher_text'])}chars"
            
        elif puzzle_type == PuzzleType.LOGIC_GRID:
            logic_puzzle = self._generate_logic_grid(difficulty)
            puzzle_data = logic_puzzle
            solution_data = {"solution": logic_puzzle["solution"]}
            grid_size = f"{len(logic_puzzle['cryptos'])}x{len(logic_puzzle['cryptos'])}"
        
        # Create game session
        game_session = PuzzleSolverSession(
            user_id=user_id,
            puzzle_type=puzzle_type.value,
            difficulty=difficulty.value,
            grid_size=grid_size,
            puzzle_data=puzzle_data,
            solution_data=solution_data
        )
        
        session.add(game_session)
        await session.commit()
        
        # Calculate potential reward
        base_rewards = {
            PuzzleDifficulty.EASY: 30,
            PuzzleDifficulty.MEDIUM: 50,
            PuzzleDifficulty.HARD: 75,
            PuzzleDifficulty.EXPERT: 110
        }
        
        logger.info(f"Started {puzzle_type.value} puzzle for user {user_id}: {difficulty.value}")
        
        return {
            "status": "success",
            "game_id": game_session.id,
            "puzzle_type": puzzle_type.value,
            "difficulty": difficulty.value,
            "grid_size": grid_size,
            "puzzle_data": puzzle_data,
            "potential_reward": base_rewards[difficulty],
            "optimal_moves": self._calculate_optimal_moves(puzzle_type, difficulty)
        }
    
    def _find_empty_position(self, grid: List[List[int]]) -> Tuple[int, int]:
        """Find the position of the empty space (0) in sliding puzzle."""
        for i, row in enumerate(grid):
            for j, val in enumerate(row):
                if val == 0:
                    return (i, j)
        return (0, 0)
    
    def _calculate_optimal_moves(self, puzzle_type: PuzzleType, difficulty: PuzzleDifficulty) -> int:
        """Estimate optimal number of moves for completion."""
        if puzzle_type == PuzzleType.SLIDING_PUZZLE:
            return {
                PuzzleDifficulty.EASY: 15,
                PuzzleDifficulty.MEDIUM: 35,
                PuzzleDifficulty.HARD: 50,
                PuzzleDifficulty.EXPERT: 80
            }[difficulty]
        else:
            return {
                PuzzleDifficulty.EASY: 5,
                PuzzleDifficulty.MEDIUM: 10,
                PuzzleDifficulty.HARD: 15,
                PuzzleDifficulty.EXPERT: 25
            }[difficulty]
    
    async def make_move(
        self,
        session: AsyncSession,
        game_id: str,
        move_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a move in the puzzle."""
        
        from sqlalchemy import select
        result = await session.execute(
            select(PuzzleSolverSession).where(PuzzleSolverSession.id == game_id)
        )
        game_session = result.scalar_one_or_none()
        
        if not game_session or game_session.game_state != "ACTIVE":
            return {"status": "error", "message": "Game not found or inactive"}
        
        puzzle_type = PuzzleType(game_session.puzzle_type)
        puzzle_data = game_session.puzzle_data
        
        if puzzle_type == PuzzleType.SLIDING_PUZZLE:
            return await self._process_sliding_move(session, game_session, move_data)
        elif puzzle_type == PuzzleType.CRYPTO_CIPHER:
            return await self._process_cipher_solution(session, game_session, move_data)
        elif puzzle_type == PuzzleType.LOGIC_GRID:
            return await self._process_logic_solution(session, game_session, move_data)
        
        return {"status": "error", "message": "Unknown puzzle type"}
    
    async def _process_sliding_move(
        self,
        session: AsyncSession,
        game_session: PuzzleSolverSession,
        move_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a move in sliding puzzle."""
        
        grid = game_session.puzzle_data["grid"]
        empty_row, empty_col = game_session.puzzle_data["empty_pos"]
        
        # Get the piece to move
        move_row = move_data.get("row")
        move_col = move_data.get("col")
        
        if move_row is None or move_col is None:
            return {"status": "error", "message": "Invalid move data"}
        
        # Check if move is valid (adjacent to empty space)
        if abs(move_row - empty_row) + abs(move_col - empty_col) != 1:
            return {"status": "error", "message": "Invalid move - not adjacent to empty space"}
        
        # Make the move
        grid[empty_row][empty_col] = grid[move_row][move_col]
        grid[move_row][move_col] = 0
        
        # Update game state
        game_session.puzzle_data["grid"] = grid
        game_session.puzzle_data["empty_pos"] = (move_row, move_col)
        game_session.moves_made += 1
        
        # Check if solved
        solution_grid = game_session.solution_data["grid"]
        is_solved = grid == solution_grid
        
        if is_solved:
            await self._complete_puzzle(session, game_session)
        
        await session.commit()
        
        return {
            "status": "success",
            "puzzle_state": grid,
            "empty_position": (move_row, move_col),
            "moves_made": game_session.moves_made,
            "is_solved": is_solved,
            "gem_coins_earned": game_session.gem_coins_earned if is_solved else 0
        }
    
    async def _process_cipher_solution(
        self,
        session: AsyncSession,
        game_session: PuzzleSolverSession,
        move_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a cipher solution attempt."""
        
        user_solution = move_data.get("solution", "").upper().strip()
        correct_solution = game_session.solution_data["solution"]
        
        is_correct = user_solution == correct_solution
        
        if is_correct:
            await self._complete_puzzle(session, game_session)
        else:
            # Give hint after wrong answer
            game_session.hints_used += 1
        
        await session.commit()
        
        return {
            "status": "success",
            "is_correct": is_correct,
            "correct_solution": correct_solution if is_correct else None,
            "hint": game_session.puzzle_data["hint"] if not is_correct else None,
            "gem_coins_earned": game_session.gem_coins_earned if is_correct else 0
        }
    
    async def _process_logic_solution(
        self,
        session: AsyncSession,
        game_session: PuzzleSolverSession,
        move_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a logic grid solution attempt."""
        
        user_solution = move_data.get("solution", [])
        correct_solution = game_session.solution_data["solution"]
        
        # Convert to comparable format
        user_tuples = [(item.get("crypto"), item.get("price"), item.get("holder")) for item in user_solution]
        
        is_correct = set(user_tuples) == set(correct_solution)
        
        if is_correct:
            await self._complete_puzzle(session, game_session)
        
        await session.commit()
        
        return {
            "status": "success",
            "is_correct": is_correct,
            "correct_solution": correct_solution if is_correct else None,
            "gem_coins_earned": game_session.gem_coins_earned if is_correct else 0
        }
    
    async def _complete_puzzle(self, session: AsyncSession, game_session: PuzzleSolverSession):
        """Complete the puzzle and calculate rewards."""
        
        game_session.end_time = datetime.utcnow()
        game_session.time_taken_seconds = (
            game_session.end_time - game_session.start_time
        ).total_seconds()
        game_session.game_state = "COMPLETED"
        
        # Calculate rewards
        difficulty = PuzzleDifficulty(game_session.difficulty)
        puzzle_type = PuzzleType(game_session.puzzle_type)
        
        base_rewards = {
            PuzzleDifficulty.EASY: 30,
            PuzzleDifficulty.MEDIUM: 50,
            PuzzleDifficulty.HARD: 75,
            PuzzleDifficulty.EXPERT: 110
        }
        
        base_reward = base_rewards[difficulty]
        
        # Efficiency bonus (based on moves for sliding puzzles)
        efficiency_bonus = 0.0
        if puzzle_type == PuzzleType.SLIDING_PUZZLE:
            optimal_moves = self._calculate_optimal_moves(puzzle_type, difficulty)
            if game_session.moves_made <= optimal_moves:
                efficiency_bonus = base_reward * 0.4  # 40% bonus for optimal solution
            elif game_session.moves_made <= optimal_moves * 1.3:
                efficiency_bonus = base_reward * 0.2  # 20% bonus for near-optimal
        
        # Speed bonus
        time_thresholds = {
            PuzzleDifficulty.EASY: 120,    # 2 minutes
            PuzzleDifficulty.MEDIUM: 300,  # 5 minutes
            PuzzleDifficulty.HARD: 600,    # 10 minutes
            PuzzleDifficulty.EXPERT: 900   # 15 minutes
        }
        
        speed_bonus = 0.0
        if game_session.time_taken_seconds <= time_thresholds[difficulty]:
            speed_bonus = base_reward * 0.3  # 30% speed bonus
        
        # Hint penalty
        hint_penalty = game_session.hints_used * base_reward * 0.1  # 10% penalty per hint
        
        # Calculate final reward
        final_reward = max(base_reward * 0.2, base_reward + efficiency_bonus + speed_bonus - hint_penalty)
        xp_reward = int(final_reward * 0.6)  # XP is 60% of GEM reward
        
        game_session.gem_coins_earned = final_reward
        game_session.xp_earned = xp_reward
        game_session.efficiency_bonus = efficiency_bonus
        game_session.speed_bonus = speed_bonus
        
        # Calculate efficiency score
        if puzzle_type == PuzzleType.SLIDING_PUZZLE:
            optimal_moves = self._calculate_optimal_moves(puzzle_type, difficulty)
            game_session.efficiency_score = min(100, (optimal_moves / game_session.moves_made) * 100)
        else:
            game_session.efficiency_score = 100 - (game_session.hints_used * 10)  # Penalty for hints
        
        # Award through virtual economy
        reward_bundle = RewardBundle(
            gem_coins=final_reward,
            experience_points=xp_reward,
            description=f"Puzzle Solved ({puzzle_type.value}, {difficulty.value}): {game_session.efficiency_score:.0f}% efficiency"
        )
        
        await self.virtual_economy.award_reward(session, game_session.user_id, reward_bundle)
        
        logger.info(f"Puzzle completed - User: {game_session.user_id}, Type: {puzzle_type.value}, Reward: {final_reward} GEM")
    
    async def get_user_stats(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get user's puzzle solving statistics."""
        
        from sqlalchemy import select, func
        
        result = await session.execute(
            select(
                func.count(PuzzleSolverSession.id).label("total_puzzles"),
                func.sum(PuzzleSolverSession.gem_coins_earned).label("total_gems"),
                func.sum(PuzzleSolverSession.xp_earned).label("total_xp"),
                func.avg(PuzzleSolverSession.efficiency_score).label("avg_efficiency"),
                func.avg(PuzzleSolverSession.time_taken_seconds).label("avg_time"),
                func.min(PuzzleSolverSession.time_taken_seconds).label("best_time")
            ).where(
                (PuzzleSolverSession.user_id == user_id) & 
                (PuzzleSolverSession.game_state == "COMPLETED")
            )
        )
        stats = result.first()
        
        # Get breakdown by puzzle type
        type_result = await session.execute(
            select(
                PuzzleSolverSession.puzzle_type,
                func.count(PuzzleSolverSession.id).label("count"),
                func.avg(PuzzleSolverSession.efficiency_score).label("avg_efficiency")
            ).where(
                (PuzzleSolverSession.user_id == user_id) & 
                (PuzzleSolverSession.game_state == "COMPLETED")
            ).group_by(PuzzleSolverSession.puzzle_type)
        )
        
        type_breakdown = {
            row.puzzle_type: {
                "puzzles_solved": row.count,
                "average_efficiency": float(row.avg_efficiency or 0)
            }
            for row in type_result
        }
        
        return {
            "total_puzzles_solved": stats.total_puzzles or 0,
            "total_gems_earned": stats.total_gems or 0.0,
            "total_xp_earned": stats.total_xp or 0,
            "average_efficiency": float(stats.avg_efficiency or 0),
            "average_solve_time": stats.avg_time or 0.0,
            "best_solve_time": stats.best_time or 0.0,
            "puzzle_type_breakdown": type_breakdown
        }