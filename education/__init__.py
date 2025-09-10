"""
Education System - Investment education, learning management, and trading simulation.
"""

from .learning_system import (
    LearningSystem, 
    learning_system, 
    EducationLesson, 
    UserLessonProgress, 
    TradingStrategy,
    SimulationSession,
    LessonDifficulty, 
    LessonType, 
    UserProgress
)
from .simulation_trainer import (
    SimulationTrainer,
    simulation_trainer,
    SimulationType,
    MarketScenario,
    TrainingChallenge
)
from .education_api import router as education_router

__all__ = [
    "LearningSystem",
    "learning_system",
    "EducationLesson",
    "UserLessonProgress", 
    "TradingStrategy",
    "SimulationSession",
    "LessonDifficulty",
    "LessonType",
    "UserProgress",
    "SimulationTrainer",
    "simulation_trainer",
    "SimulationType",
    "MarketScenario", 
    "TrainingChallenge",
    "education_router"
]