"""
Mini-games system for crypto gamification platform.
Engaging skill-based games for earning GEM coins and rewards.
"""

from .memory_match import MemoryMatchGame
from .number_prediction import NumberPredictionGame
from .puzzle_solver import PuzzleSolverGame
from .quick_math import QuickMathGame
from .daily_challenges import DailyChallengeSystem
from .spin_wheel import SpinWheelGame
from .mini_game_manager import MiniGameManager

__all__ = [
    "MemoryMatchGame",
    "NumberPredictionGame", 
    "PuzzleSolverGame",
    "QuickMathGame",
    "DailyChallengeSystem",
    "SpinWheelGame",
    "MiniGameManager"
]