"""
Daily Challenge System
Dynamic daily objectives for earning extra GEM coins and rewards.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, JSON, select, func
from database import Base, get_db_session, DailyChallenge, UserChallengeProgress
from gamification import VirtualEconomyEngine, RewardBundle
from logger import logger


class ChallengeType(Enum):
    PLAY_GAMES = "PLAY_GAMES"           # Play X games
    EARN_GEMS = "EARN_GEMS"             # Earn X GEM coins
    WIN_STREAK = "WIN_STREAK"           # Achieve X win streak
    PERFECT_SCORE = "PERFECT_SCORE"     # Get perfect score X times
    TIME_CHALLENGE = "TIME_CHALLENGE"   # Complete game in X seconds
    ACCURACY = "ACCURACY"               # Achieve X% accuracy
    SPECIFIC_GAME = "SPECIFIC_GAME"     # Play specific game X times


class DailyChallengeSystem:
    """Manages daily challenges and objectives."""
    
    CHALLENGE_TEMPLATES = [
        {
            "type": ChallengeType.PLAY_GAMES,
            "title": "Game Master",
            "description": "Play {target} mini-games today",
            "target_min": 5,
            "target_max": 15,
            "gem_reward": 150,
            "xp_reward": 75
        },
        {
            "type": ChallengeType.EARN_GEMS,
            "title": "Gem Hunter",
            "description": "Earn {target} GEM coins from mini-games",
            "target_min": 500,
            "target_max": 1500,
            "gem_reward": 200,
            "xp_reward": 100
        },
        {
            "type": ChallengeType.WIN_STREAK,
            "title": "Streak Master",
            "description": "Achieve a {target}-game winning streak",
            "target_min": 3,
            "target_max": 8,
            "gem_reward": 250,
            "xp_reward": 125
        },
        {
            "type": ChallengeType.PERFECT_SCORE,
            "title": "Perfectionist",
            "description": "Get perfect scores in {target} games",
            "target_min": 2,
            "target_max": 5,
            "gem_reward": 300,
            "xp_reward": 150
        },
        {
            "type": ChallengeType.ACCURACY,
            "title": "Precision Player",
            "description": "Achieve {target}% accuracy in any game",
            "target_min": 85,
            "target_max": 95,
            "gem_reward": 175,
            "xp_reward": 90
        },
        {
            "type": ChallengeType.SPECIFIC_GAME,
            "title": "Specialist",
            "description": "Play {game_type} {target} times",
            "target_min": 3,
            "target_max": 6,
            "gem_reward": 120,
            "xp_reward": 60
        }
    ]
    
    GAME_TYPES = [
        ("memory_match", "Memory Match"),
        ("quick_math", "Quick Math"),
        ("puzzle_solver", "Puzzle Solver"), 
        ("number_prediction", "Number Prediction"),
        ("spin_wheel", "Spin Wheel")
    ]
    
    def __init__(self, virtual_economy: VirtualEconomyEngine):
        self.virtual_economy = virtual_economy
    
    async def generate_daily_challenges(self, session: AsyncSession, target_date: datetime) -> List[Dict[str, Any]]:
        """Generate 4 random daily challenges for the specified date."""
        
        import random
        
        # Select 4 different challenge types
        selected_templates = random.sample(self.CHALLENGE_TEMPLATES, 4)
        
        challenges = []
        for template in selected_templates:
            challenge_data = template.copy()
            
            # Generate random target within range
            target = random.randint(challenge_data["target_min"], challenge_data["target_max"])
            
            # Handle specific game challenges
            if challenge_data["type"] == ChallengeType.SPECIFIC_GAME:
                game_id, game_name = random.choice(self.GAME_TYPES)
                challenge_data["game_type"] = game_id
                challenge_data["description"] = challenge_data["description"].format(
                    game_type=game_name,
                    target=target
                )
            else:
                challenge_data["description"] = challenge_data["description"].format(target=target)
            
            challenge_data["target_value"] = target
            
            # Create database record
            challenge = DailyChallenge(
                challenge_date=target_date,
                game_type=challenge_data.get("game_type", "ANY"),
                challenge_type=challenge_data["type"].value,
                target_value=target,
                description=challenge_data["description"],
                gem_reward=challenge_data["gem_reward"],
                xp_reward=challenge_data["xp_reward"]
            )
            
            session.add(challenge)
            challenges.append(challenge_data)
        
        await session.commit()
        logger.info(f"Generated {len(challenges)} daily challenges for {target_date.date()}")
        
        return challenges
    
    async def update_challenge_progress(
        self,
        session: AsyncSession,
        user_id: str,
        challenge_type: ChallengeType,
        progress_value: float,
        game_type: str = "ANY"
    ):
        """Update user's progress on relevant challenges."""
        
        today = datetime.utcnow().date()
        
        # Find relevant challenges for today
        challenges_result = await session.execute(
            select(DailyChallenge)
            .where(func.date(DailyChallenge.challenge_date) == today)
            .where(DailyChallenge.is_active == True)
            .where(DailyChallenge.challenge_type == challenge_type.value)
        )
        challenges = challenges_result.scalars().all()
        
        for challenge in challenges:
            # Check if challenge applies to this game type
            if challenge.game_type != "ANY" and challenge.game_type != game_type:
                continue
            
            # Get or create user progress
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
            
            # Update progress based on challenge type
            if challenge_type in [ChallengeType.PLAY_GAMES, ChallengeType.PERFECT_SCORE]:
                progress.current_progress += progress_value  # Increment
            elif challenge_type == ChallengeType.ACCURACY:
                progress.current_progress = max(progress.current_progress, progress_value)  # Take best
            elif challenge_type == ChallengeType.WIN_STREAK:
                progress.current_progress = max(progress.current_progress, progress_value)  # Track best streak
            else:
                progress.current_progress += progress_value  # Default increment
            
            # Check if challenge is completed
            if not progress.is_completed and progress.current_progress >= progress.target_value:
                progress.is_completed = True
                progress.completion_time = datetime.utcnow()
                progress.gems_earned = challenge.gem_reward
                progress.xp_earned = challenge.xp_reward
                
                # Award the reward
                reward_bundle = RewardBundle(
                    gem_coins=challenge.gem_reward,
                    experience_points=challenge.xp_reward,
                    description=f"Daily Challenge: {challenge.description}"
                )
                
                await self.virtual_economy.award_reward(session, user_id, reward_bundle)
                
                logger.info(f"Challenge completed by user {user_id}: {challenge.description} - Reward: {challenge.gem_reward} GEM")
        
        await session.commit()
    
    async def get_user_challenges(self, session: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
        """Get today's challenges for the user with progress."""
        
        today = datetime.utcnow().date()
        
        # Get today's challenges
        challenges_result = await session.execute(
            select(DailyChallenge)
            .where(func.date(DailyChallenge.challenge_date) == today)
            .where(DailyChallenge.is_active == True)
        )
        challenges = challenges_result.scalars().all()
        
        user_challenges = []
        for challenge in challenges:
            # Get user's progress
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
                await session.commit()
            
            progress_percentage = min(100, (progress.current_progress / challenge.target_value) * 100)
            
            user_challenges.append({
                "id": challenge.id,
                "title": challenge.description.split(":")[0] if ":" in challenge.description else "Challenge",
                "description": challenge.description,
                "challenge_type": challenge.challenge_type,
                "game_type": challenge.game_type,
                "progress": progress.current_progress,
                "target": challenge.target_value,
                "progress_percentage": progress_percentage,
                "is_completed": progress.is_completed,
                "gem_reward": challenge.gem_reward,
                "xp_reward": challenge.xp_reward,
                "completion_time": progress.completion_time.isoformat() if progress.completion_time else None
            })
        
        return user_challenges
    
    async def get_challenge_statistics(self, session: AsyncSession) -> Dict[str, Any]:
        """Get global challenge statistics."""
        
        today = datetime.utcnow().date()
        
        # Get today's challenge stats
        result = await session.execute(
            select(
                func.count(DailyChallenge.id).label("total_challenges"),
                func.sum(DailyChallenge.participants).label("total_participants"),
                func.sum(DailyChallenge.completions).label("total_completions")
            )
            .where(func.date(DailyChallenge.challenge_date) == today)
            .where(DailyChallenge.is_active == True)
        )
        stats = result.first()
        
        # Get completion rate by challenge type
        type_stats_result = await session.execute(
            select(
                DailyChallenge.challenge_type,
                func.count(UserChallengeProgress.id).label("attempts"),
                func.sum(func.cast(UserChallengeProgress.is_completed, Integer)).label("completions")
            )
            .join(UserChallengeProgress, DailyChallenge.id == UserChallengeProgress.challenge_id)
            .where(func.date(DailyChallenge.challenge_date) == today)
            .group_by(DailyChallenge.challenge_type)
        )
        
        type_breakdown = {}
        for row in type_stats_result:
            completion_rate = (row.completions / max(1, row.attempts)) * 100
            type_breakdown[row.challenge_type] = {
                "attempts": row.attempts,
                "completions": row.completions,
                "completion_rate": completion_rate
            }
        
        return {
            "total_challenges": stats.total_challenges or 0,
            "total_participants": stats.total_participants or 0,
            "total_completions": stats.total_completions or 0,
            "overall_completion_rate": ((stats.total_completions or 0) / max(1, stats.total_participants or 1)) * 100,
            "challenge_type_breakdown": type_breakdown
        }
    
    async def cleanup_old_challenges(self, session: AsyncSession, days_to_keep: int = 7):
        """Clean up old challenge data to keep database size manageable."""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Delete old challenge progress
        await session.execute(
            UserChallengeProgress.__table__.delete()
            .where(UserChallengeProgress.created_at < cutoff_date)
        )
        
        # Delete old challenges
        await session.execute(
            DailyChallenge.__table__.delete()
            .where(DailyChallenge.challenge_date < cutoff_date)
        )
        
        await session.commit()
        logger.info(f"Cleaned up challenges older than {days_to_keep} days")


# Helper functions for easy integration
async def update_game_challenge_progress(session: AsyncSession, user_id: str, game_type: str, game_data: Dict[str, Any]):
    """Update challenge progress after a game completion."""
    
    from gamification import virtual_economy
    challenge_system = DailyChallengeSystem(virtual_economy)
    
    # Update "play games" challenge
    await challenge_system.update_challenge_progress(
        session, user_id, ChallengeType.PLAY_GAMES, 1, game_type
    )
    
    # Update specific game challenge
    await challenge_system.update_challenge_progress(
        session, user_id, ChallengeType.SPECIFIC_GAME, 1, game_type
    )
    
    # Update gem earning challenge
    gems_earned = game_data.get("gems_earned", 0)
    if gems_earned > 0:
        await challenge_system.update_challenge_progress(
            session, user_id, ChallengeType.EARN_GEMS, gems_earned, game_type
        )
    
    # Update accuracy challenge
    accuracy = game_data.get("accuracy", 0)
    if accuracy > 0:
        await challenge_system.update_challenge_progress(
            session, user_id, ChallengeType.ACCURACY, accuracy * 100, game_type
        )
    
    # Update perfect score challenge
    if game_data.get("perfect_score", False):
        await challenge_system.update_challenge_progress(
            session, user_id, ChallengeType.PERFECT_SCORE, 1, game_type
        )
    
    # Update streak challenge
    streak = game_data.get("streak", 0)
    if streak > 0:
        await challenge_system.update_challenge_progress(
            session, user_id, ChallengeType.WIN_STREAK, streak, game_type
        )