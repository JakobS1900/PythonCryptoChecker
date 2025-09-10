"""
Mini-Game Manager
Central management system for all mini-games and rewards.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from database import Base, get_db_session, User, UserGameStats, DailyChallenge, UserChallengeProgress
from gamification import VirtualEconomyEngine, RewardBundle
from logger import logger

from .memory_match import MemoryMatchGame, MemoryGameSession
from .number_prediction import NumberPredictionGame, NumberPredictionSession
from .puzzle_solver import PuzzleSolverGame, PuzzleSolverSession
from .quick_math import QuickMathGame, QuickMathSession
from .spin_wheel import SpinWheelGame, SpinWheelSession


class GameCategory(Enum):
    SKILL_GAMES = "SKILL_GAMES"
    LUCK_GAMES = "LUCK_GAMES"
    BRAIN_GAMES = "BRAIN_GAMES"
    SPEED_GAMES = "SPEED_GAMES"



class MiniGameManager:
    """Central manager for all mini-games."""
    
    GAME_CONFIGS = {
        "memory_match": {
            "name": "Crypto Memory Match",
            "description": "Match crypto symbols and earn GEM coins",
            "category": GameCategory.BRAIN_GAMES,
            "max_daily_plays": 10,
            "cooldown_minutes": 5,
            "skill_type": "memory_skill"
        },
        "number_prediction": {
            "name": "Number Prediction",
            "description": "Predict patterns and crypto price movements",
            "category": GameCategory.SKILL_GAMES,
            "max_daily_plays": 8,
            "cooldown_minutes": 10,
            "skill_type": "prediction_skill"
        },
        "puzzle_solver": {
            "name": "Crypto Puzzles",
            "description": "Solve sliding puzzles and brain teasers",
            "category": GameCategory.BRAIN_GAMES,
            "max_daily_plays": 6,
            "cooldown_minutes": 15,
            "skill_type": "puzzle_skill"
        },
        "quick_math": {
            "name": "Quick Math",
            "description": "Fast crypto trading calculations",
            "category": GameCategory.SPEED_GAMES,
            "max_daily_plays": 12,
            "cooldown_minutes": 3,
            "skill_type": "math_skill"
        },
        "spin_wheel": {
            "name": "Spin to Win",
            "description": "Lucky wheel spins for instant rewards",
            "category": GameCategory.LUCK_GAMES,
            "max_daily_plays": 24,  # Hourly spins
            "cooldown_minutes": 60,
            "skill_type": None
        }
    }
    
    def __init__(self, virtual_economy: VirtualEconomyEngine):
        self.virtual_economy = virtual_economy
        self.memory_game = MemoryMatchGame(virtual_economy)
        self.prediction_game = NumberPredictionGame(virtual_economy)
        self.puzzle_game = PuzzleSolverGame(virtual_economy)
        self.math_game = QuickMathGame(virtual_economy)
        self.wheel_game = SpinWheelGame(virtual_economy)
    
    async def get_user_dashboard(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get comprehensive mini-game dashboard for user."""
        
        # Get or create user game stats
        user_stats = await session.execute(
            select(UserGameStats).where(UserGameStats.user_id == user_id)
        )
        stats = user_stats.scalar_one_or_none()
        
        if not stats:
            stats = UserGameStats(user_id=user_id)
            session.add(stats)
            await session.commit()
        
        # Reset daily/weekly counters if needed
        now = datetime.utcnow()
        today = now.date()
        
        if not stats.last_daily_reset or stats.last_daily_reset.date() < today:
            stats.daily_games_played = 0
            stats.last_daily_reset = now
        
        # Weekly reset (Monday)
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        if not stats.last_weekly_reset or stats.last_weekly_reset.date() < week_start:
            stats.weekly_gems_earned = 0.0
            stats.last_weekly_reset = now
        
        await session.commit()
        
        # Get available games with play limits
        available_games = []
        for game_key, config in self.GAME_CONFIGS.items():
            # Check daily play limit
            daily_plays = await self._count_daily_plays(session, user_id, game_key)
            can_play = daily_plays < config["max_daily_plays"]
            
            # Check cooldown
            last_play = await self._get_last_play_time(session, user_id, game_key)
            cooldown_remaining = 0
            if last_play:
                cooldown_end = last_play + timedelta(minutes=config["cooldown_minutes"])
                if now < cooldown_end:
                    can_play = False
                    cooldown_remaining = int((cooldown_end - now).total_seconds())
            
            available_games.append({
                "game_id": game_key,
                "name": config["name"],
                "description": config["description"],
                "category": config["category"].value,
                "can_play": can_play,
                "daily_plays": daily_plays,
                "max_daily_plays": config["max_daily_plays"],
                "cooldown_remaining": cooldown_remaining,
                "skill_rating": getattr(stats, config["skill_type"]) if config["skill_type"] else None
            })
        
        # Get daily challenges
        daily_challenges = await self._get_daily_challenges(session, user_id)
        
        # Get recent achievements
        recent_games = await self._get_recent_game_results(session, user_id, 5)
        
        # Get leaderboard position
        leaderboard_pos = await self._get_user_leaderboard_position(session, user_id)
        
        return {
            "user_stats": {
                "total_games": stats.total_games_played,
                "total_gems": stats.total_gems_earned,
                "total_xp": stats.total_xp_earned,
                "daily_games": stats.daily_games_played,
                "weekly_gems": stats.weekly_gems_earned,
                "favorite_game": stats.favorite_game,
                "skill_ratings": {
                    "memory": stats.memory_skill,
                    "math": stats.math_skill,
                    "puzzle": stats.puzzle_skill,
                    "prediction": stats.prediction_skill
                }
            },
            "available_games": available_games,
            "daily_challenges": daily_challenges,
            "recent_results": recent_games,
            "leaderboard_position": leaderboard_pos
        }
    
    async def _count_daily_plays(self, session: AsyncSession, user_id: str, game_type: str) -> int:
        """Count how many times user played a specific game today."""
        
        today = datetime.utcnow().date()
        
        if game_type == "memory_match":
            result = await session.execute(
                select(func.count(MemoryGameSession.id))
                .where((MemoryGameSession.user_id == user_id) & 
                       (func.date(MemoryGameSession.created_at) == today))
            )
        elif game_type == "number_prediction":
            result = await session.execute(
                select(func.count(NumberPredictionSession.id))
                .where((NumberPredictionSession.user_id == user_id) & 
                       (func.date(NumberPredictionSession.created_at) == today))
            )
        elif game_type == "puzzle_solver":
            result = await session.execute(
                select(func.count(PuzzleSolverSession.id))
                .where((PuzzleSolverSession.user_id == user_id) & 
                       (func.date(PuzzleSolverSession.created_at) == today))
            )
        elif game_type == "quick_math":
            result = await session.execute(
                select(func.count(QuickMathSession.id))
                .where((QuickMathSession.user_id == user_id) & 
                       (func.date(QuickMathSession.created_at) == today))
            )
        elif game_type == "spin_wheel":
            result = await session.execute(
                select(func.count(SpinWheelSession.id))
                .where((SpinWheelSession.user_id == user_id) & 
                       (func.date(SpinWheelSession.created_at) == today))
            )
        else:
            return 0
        
        return result.scalar() or 0
    
    async def _get_last_play_time(self, session: AsyncSession, user_id: str, game_type: str) -> Optional[datetime]:
        """Get the last time user played a specific game."""
        
        if game_type == "memory_match":
            result = await session.execute(
                select(MemoryGameSession.created_at)
                .where(MemoryGameSession.user_id == user_id)
                .order_by(desc(MemoryGameSession.created_at))
                .limit(1)
            )
        elif game_type == "number_prediction":
            result = await session.execute(
                select(NumberPredictionSession.created_at)
                .where(NumberPredictionSession.user_id == user_id)
                .order_by(desc(NumberPredictionSession.created_at))
                .limit(1)
            )
        elif game_type == "puzzle_solver":
            result = await session.execute(
                select(PuzzleSolverSession.created_at)
                .where(PuzzleSolverSession.user_id == user_id)
                .order_by(desc(PuzzleSolverSession.created_at))
                .limit(1)
            )
        elif game_type == "quick_math":
            result = await session.execute(
                select(QuickMathSession.created_at)
                .where(QuickMathSession.user_id == user_id)
                .order_by(desc(QuickMathSession.created_at))
                .limit(1)
            )
        elif game_type == "spin_wheel":
            result = await session.execute(
                select(SpinWheelSession.created_at)
                .where(SpinWheelSession.user_id == user_id)
                .order_by(desc(SpinWheelSession.created_at))
                .limit(1)
            )
        else:
            return None
        
        last_time = result.scalar_one_or_none()
        return last_time
    
    async def _get_daily_challenges(self, session: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
        """Get today's daily challenges for the user."""
        
        today = datetime.utcnow().date()
        
        # Get today's challenges
        challenges_result = await session.execute(
            select(DailyChallenge)
            .where(func.date(DailyChallenge.challenge_date) == today)
            .where(DailyChallenge.is_active == True)
        )
        challenges = challenges_result.scalars().all()
        
        # Get user's progress on these challenges
        challenge_progress = []
        for challenge in challenges:
            progress_result = await session.execute(
                select(UserChallengeProgress)
                .where((UserChallengeProgress.user_id == user_id) &
                       (UserChallengeProgress.challenge_id == challenge.id))
            )
            progress = progress_result.scalar_one_or_none()
            
            if not progress:
                progress = UserChallengeProgress(
                    user_id=user_id,
                    challenge_id=challenge.id,
                    target_value=challenge.target_value
                )
                session.add(progress)
            
            progress_percentage = min(100, (progress.current_progress / challenge.target_value) * 100)
            
            challenge_progress.append({
                "id": challenge.id,
                "game_type": challenge.game_type,
                "description": challenge.description,
                "progress": progress.current_progress,
                "target": challenge.target_value,
                "progress_percentage": progress_percentage,
                "is_completed": progress.is_completed,
                "gem_reward": challenge.gem_reward,
                "xp_reward": challenge.xp_reward
            })
        
        await session.commit()
        return challenge_progress
    
    async def _get_recent_game_results(self, session: AsyncSession, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get user's recent game results across all mini-games."""
        
        recent_games = []
        
        # Memory games
        memory_result = await session.execute(
            select(MemoryGameSession)
            .where(MemoryGameSession.user_id == user_id)
            .where(MemoryGameSession.game_state == "COMPLETED")
            .order_by(desc(MemoryGameSession.end_time))
            .limit(3)
        )
        for game in memory_result.scalars():
            recent_games.append({
                "game_type": "Memory Match",
                "result": f"{game.pairs_found}/{game.total_pairs} pairs",
                "gems_earned": game.gem_coins_earned,
                "timestamp": game.end_time,
                "difficulty": game.difficulty
            })
        
        # Math games
        math_result = await session.execute(
            select(QuickMathSession)
            .where(QuickMathSession.user_id == user_id)
            .where(QuickMathSession.game_state == "COMPLETED")
            .order_by(desc(QuickMathSession.end_time))
            .limit(3)
        )
        for game in math_result.scalars():
            recent_games.append({
                "game_type": "Quick Math",
                "result": f"{game.correct_answers}/{game.total_problems} correct",
                "gems_earned": game.gem_coins_earned,
                "timestamp": game.end_time,
                "difficulty": game.difficulty
            })
        
        # Sort by timestamp and return most recent
        recent_games.sort(key=lambda x: x["timestamp"] or datetime.min, reverse=True)
        return recent_games[:limit]
    
    async def _get_user_leaderboard_position(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get user's position on the weekly leaderboard."""
        
        # Calculate weekly leaderboard
        week_start = datetime.utcnow().date() - timedelta(days=datetime.utcnow().weekday())
        
        # Get all users' weekly gems earned
        result = await session.execute(
            select(UserGameStats.user_id, User.username, UserGameStats.weekly_gems_earned)
            .join(User, UserGameStats.user_id == User.id)
            .where(UserGameStats.weekly_gems_earned > 0)
            .order_by(desc(UserGameStats.weekly_gems_earned))
        )
        
        leaderboard = list(result)
        
        # Find user's position
        user_position = None
        user_gems = 0
        for i, (uid, username, gems) in enumerate(leaderboard, 1):
            if uid == user_id:
                user_position = i
                user_gems = gems
                break
        
        return {
            "position": user_position,
            "total_players": len(leaderboard),
            "weekly_gems": user_gems,
            "top_3": [
                {"rank": i, "username": username, "gems": gems}
                for i, (_, username, gems) in enumerate(leaderboard[:3], 1)
            ]
        }
    
    async def update_user_stats_after_game(
        self,
        session: AsyncSession,
        user_id: str,
        game_type: str,
        gems_earned: float,
        xp_earned: int,
        performance_data: Dict[str, Any]
    ):
        """Update user stats after completing a game."""
        
        # Get user stats
        result = await session.execute(
            select(UserGameStats).where(UserGameStats.user_id == user_id)
        )
        stats = result.scalar_one_or_none()
        
        if not stats:
            stats = UserGameStats(user_id=user_id)
            session.add(stats)
        
        # Update overall stats
        stats.total_games_played += 1
        stats.total_gems_earned += gems_earned
        stats.total_xp_earned += xp_earned
        stats.daily_games_played += 1
        stats.weekly_gems_earned += gems_earned
        
        # Update game-specific counters
        if game_type == "memory_match":
            stats.memory_games += 1
            # Update skill based on performance
            accuracy = performance_data.get("accuracy", 0.5)
            stats.memory_skill = min(100, stats.memory_skill + (accuracy - 0.5) * 2)
        elif game_type == "quick_math":
            stats.math_games += 1
            accuracy = performance_data.get("accuracy", 0.5)
            stats.math_skill = min(100, stats.math_skill + (accuracy - 0.5) * 2)
        elif game_type == "puzzle_solver":
            stats.puzzle_games += 1
            efficiency = performance_data.get("efficiency", 50) / 100
            stats.puzzle_skill = min(100, stats.puzzle_skill + (efficiency - 0.5) * 2)
        elif game_type == "number_prediction":
            stats.prediction_games += 1
            accuracy = performance_data.get("accuracy", 0.5)
            stats.prediction_skill = min(100, stats.prediction_skill + (accuracy - 0.5) * 2)
        elif game_type == "spin_wheel":
            stats.wheel_spins += 1
        
        # Check for perfect games
        if performance_data.get("perfect", False):
            stats.perfect_games += 1
        
        # Update favorite game
        game_counts = {
            "memory_match": stats.memory_games,
            "quick_math": stats.math_games,
            "puzzle_solver": stats.puzzle_games,
            "number_prediction": stats.prediction_games,
            "spin_wheel": stats.wheel_spins
        }
        stats.favorite_game = max(game_counts.items(), key=lambda x: x[1])[0]
        
        await session.commit()
        logger.info(f"Updated stats for user {user_id} after {game_type}: +{gems_earned} GEM, +{xp_earned} XP")
    
    async def create_daily_challenges(self, session: AsyncSession, target_date: datetime):
        """Create daily challenges for a specific date."""
        
        challenges = [
            {
                "game_type": "memory_match",
                "challenge_type": "PERFECT_GAMES",
                "target_value": 3,
                "description": "Complete 3 memory games with perfect score",
                "gem_reward": 200,
                "xp_reward": 100
            },
            {
                "game_type": "quick_math",
                "challenge_type": "STREAK",
                "target_value": 5,
                "description": "Achieve a 5-answer streak in math games",
                "gem_reward": 150,
                "xp_reward": 75
            },
            {
                "game_type": "puzzle_solver",
                "challenge_type": "EFFICIENCY",
                "target_value": 90,
                "description": "Complete a puzzle with 90%+ efficiency",
                "gem_reward": 175,
                "xp_reward": 85
            },
            {
                "game_type": "spin_wheel",
                "challenge_type": "SPINS",
                "target_value": 5,
                "description": "Spin the wheel 5 times today",
                "gem_reward": 100,
                "xp_reward": 50
            }
        ]
        
        for challenge_data in challenges:
            challenge = DailyChallenge(
                challenge_date=target_date,
                **challenge_data
            )
            session.add(challenge)
        
        await session.commit()
        logger.info(f"Created {len(challenges)} daily challenges for {target_date.date()}")
    
    async def get_global_leaderboards(self, session: AsyncSession) -> Dict[str, Any]:
        """Get global leaderboards for all mini-games."""
        
        # Weekly gems leaderboard
        week_start = datetime.utcnow().date() - timedelta(days=datetime.utcnow().weekday())
        
        gems_result = await session.execute(
            select(User.username, UserGameStats.weekly_gems_earned)
            .join(UserGameStats, User.id == UserGameStats.user_id)
            .where(UserGameStats.weekly_gems_earned > 0)
            .order_by(desc(UserGameStats.weekly_gems_earned))
            .limit(10)
        )
        
        # All-time games leaderboard
        games_result = await session.execute(
            select(User.username, UserGameStats.total_games_played)
            .join(UserGameStats, User.id == UserGameStats.user_id)
            .where(UserGameStats.total_games_played > 0)
            .order_by(desc(UserGameStats.total_games_played))
            .limit(10)
        )
        
        # Skill leaders
        skill_result = await session.execute(
            select(
                User.username,
                UserGameStats.memory_skill,
                UserGameStats.math_skill,
                UserGameStats.puzzle_skill,
                UserGameStats.prediction_skill
            )
            .join(UserGameStats, User.id == UserGameStats.user_id)
            .where(UserGameStats.total_games_played >= 5)
            .order_by(desc(
                (UserGameStats.memory_skill + UserGameStats.math_skill + 
                 UserGameStats.puzzle_skill + UserGameStats.prediction_skill) / 4
            ))
            .limit(10)
        )
        
        return {
            "weekly_gems": [
                {"rank": i, "username": username, "gems": gems}
                for i, (username, gems) in enumerate(gems_result, 1)
            ],
            "total_games": [
                {"rank": i, "username": username, "games": games}
                for i, (username, games) in enumerate(games_result, 1)
            ],
            "skill_masters": [
                {
                    "rank": i,
                    "username": username,
                    "average_skill": (memory + math + puzzle + prediction) / 4,
                    "skills": {
                        "memory": memory,
                        "math": math,
                        "puzzle": puzzle,
                        "prediction": prediction
                    }
                }
                for i, (username, memory, math, puzzle, prediction) in enumerate(skill_result, 1)
            ]
        }