"""
Challenge Service

Handles daily challenges, quest tracking, and login streaks.
"""

import json
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    User, DailyChallenge, UserChallenge, LoginStreak,
    Transaction, TransactionType
)


class ChallengeService:
    """Service for daily challenges and quests."""

    # Daily login bonus rewards
    LOGIN_BONUSES = {
        1: 100,    # Day 1
        2: 150,    # Day 2
        3: 200,    # Day 3
        4: 250,    # Day 4
        5: 300,    # Day 5
        6: 400,    # Day 6
        7: 500,    # Day 7 (weekly bonus)
        14: 1000,  # Day 14
        30: 2500   # Day 30 (monthly bonus)
    }

    @staticmethod
    async def process_daily_login(user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Process daily login and award streak bonuses."""
        # Get or create login streak
        result = await db.execute(
            select(LoginStreak).where(LoginStreak.user_id == user_id)
        )
        streak = result.scalar_one_or_none()

        if not streak:
            streak = LoginStreak(user_id=user_id)
            db.add(streak)

        today = date.today()
        last_login = streak.last_login_date.date() if streak.last_login_date else None

        bonus_gem = 0
        streak_broken = False

        if last_login is None:
            # First login ever
            streak.current_streak = 1
            streak.total_logins = 1
            bonus_gem = ChallengeService.LOGIN_BONUSES[1]

        elif last_login == today:
            # Already logged in today
            return {
                'already_claimed': True,
                'current_streak': streak.current_streak,
                'bonus_gem': 0
            }

        elif last_login == today - timedelta(days=1):
            # Consecutive day
            streak.current_streak += 1
            streak.total_logins += 1

            # Get bonus for current streak
            if streak.current_streak in ChallengeService.LOGIN_BONUSES:
                bonus_gem = ChallengeService.LOGIN_BONUSES[streak.current_streak]
            elif streak.current_streak > 30:
                # After day 30, give 300 GEM per day
                bonus_gem = 300
            else:
                # Default daily bonus
                bonus_gem = 100

            # Update longest streak
            if streak.current_streak > streak.longest_streak:
                streak.longest_streak = streak.current_streak

        else:
            # Streak broken
            streak_broken = True
            streak.current_streak = 1
            streak.total_logins += 1
            bonus_gem = ChallengeService.LOGIN_BONUSES[1]

        # Update last login date
        streak.last_login_date = datetime.utcnow()

        # Award bonus GEM
        if bonus_gem > 0:
            user = await db.get(User, user_id)
            user.gem_balance += bonus_gem

            # Create transaction
            transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.DAILY_BONUS,
                amount=bonus_gem,
                description=f"Daily login bonus (Day {streak.current_streak})"
            )
            db.add(transaction)

        await db.commit()

        return {
            'already_claimed': False,
            'streak_broken': streak_broken,
            'current_streak': streak.current_streak,
            'longest_streak': streak.longest_streak,
            'bonus_gem': bonus_gem,
            'total_logins': streak.total_logins
        }

    @staticmethod
    async def create_daily_challenges(db: AsyncSession):
        """Create fresh daily challenges."""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)

        # Check if challenges already exist for today
        result = await db.execute(
            select(DailyChallenge)
            .where(
                and_(
                    DailyChallenge.starts_at >= today_start,
                    DailyChallenge.starts_at < tomorrow_start
                )
            )
        )
        existing = result.scalars().all()

        if existing:
            return  # Challenges already created for today

        # Define today's challenges
        challenges = [
            {
                'challenge_type': 'minigame_wins',
                'title': 'Mini-Game Master',
                'description': 'Win 5 mini-games',
                'requirement_value': 5,
                'gem_reward': 500,
                'difficulty': 'easy'
            },
            {
                'challenge_type': 'minigame_profit',
                'title': 'Profitable Player',
                'description': 'Earn 5,000 GEM profit from mini-games',
                'requirement_value': 5000,
                'gem_reward': 1000,
                'difficulty': 'normal'
            },
            {
                'challenge_type': 'trade_volume',
                'title': 'Active Trader',
                'description': 'Trade 10,000 GEM volume',
                'requirement_value': 10000,
                'gem_reward': 750,
                'difficulty': 'normal'
            },
            {
                'challenge_type': 'roulette_bets',
                'title': 'Roulette Enthusiast',
                'description': 'Place 10 roulette bets',
                'requirement_value': 10,
                'gem_reward': 600,
                'difficulty': 'easy'
            },
            {
                'challenge_type': 'gem_earned',
                'title': 'Wealth Builder',
                'description': 'Earn 20,000 GEM from any source',
                'requirement_value': 20000,
                'gem_reward': 2000,
                'difficulty': 'hard'
            }
        ]

        # Create challenges
        for challenge_data in challenges:
            challenge = DailyChallenge(
                challenge_type=challenge_data['challenge_type'],
                title=challenge_data['title'],
                description=challenge_data['description'],
                requirement_value=challenge_data['requirement_value'],
                gem_reward=challenge_data['gem_reward'],
                difficulty=challenge_data['difficulty'],
                starts_at=today_start,
                ends_at=tomorrow_start
            )
            db.add(challenge)

        await db.commit()

    @staticmethod
    async def get_active_challenges(user_id: str, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get all active challenges with user progress."""
        now = datetime.utcnow()

        # Get active challenges
        result = await db.execute(
            select(DailyChallenge)
            .where(
                and_(
                    DailyChallenge.starts_at <= now,
                    DailyChallenge.ends_at > now
                )
            )
            .order_by(DailyChallenge.difficulty, DailyChallenge.gem_reward.desc())
        )
        challenges = result.scalars().all()

        challenge_list = []

        for challenge in challenges:
            # Get user progress for this challenge
            result = await db.execute(
                select(UserChallenge)
                .where(
                    and_(
                        UserChallenge.user_id == user_id,
                        UserChallenge.challenge_id == challenge.id
                    )
                )
            )
            user_challenge = result.scalar_one_or_none()

            if user_challenge:
                progress = user_challenge.current_progress
                completed = user_challenge.completed
                claimed = user_challenge.claimed
            else:
                progress = 0
                completed = False
                claimed = False

            challenge_list.append({
                'id': challenge.id,
                'type': challenge.challenge_type,
                'title': challenge.title,
                'description': challenge.description,
                'requirement': challenge.requirement_value,
                'progress': progress,
                'reward': challenge.gem_reward,
                'difficulty': challenge.difficulty,
                'completed': completed,
                'claimed': claimed,
                'ends_at': challenge.ends_at.isoformat()
            })

        return challenge_list

    @staticmethod
    async def update_challenge_progress(
        user_id: str,
        challenge_type: str,
        increment: int,
        db: AsyncSession
    ):
        """Update progress for challenges of a specific type."""
        now = datetime.utcnow()

        # Get active challenges of this type
        result = await db.execute(
            select(DailyChallenge)
            .where(
                and_(
                    DailyChallenge.challenge_type == challenge_type,
                    DailyChallenge.starts_at <= now,
                    DailyChallenge.ends_at > now
                )
            )
        )
        challenges = result.scalars().all()

        for challenge in challenges:
            # Get or create user challenge
            result = await db.execute(
                select(UserChallenge)
                .where(
                    and_(
                        UserChallenge.user_id == user_id,
                        UserChallenge.challenge_id == challenge.id
                    )
                )
            )
            user_challenge = result.scalar_one_or_none()

            if not user_challenge:
                user_challenge = UserChallenge(
                    user_id=user_id,
                    challenge_id=challenge.id,
                    current_progress=0
                )
                db.add(user_challenge)

            # Update progress
            if not user_challenge.completed:
                user_challenge.current_progress += increment

                # Check if completed
                if user_challenge.current_progress >= challenge.requirement_value:
                    user_challenge.completed = True
                    user_challenge.completed_at = datetime.utcnow()

        await db.commit()

    @staticmethod
    async def claim_challenge_reward(
        user_id: str,
        challenge_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Claim reward for completed challenge."""
        # Get user challenge
        result = await db.execute(
            select(UserChallenge)
            .where(
                and_(
                    UserChallenge.user_id == user_id,
                    UserChallenge.challenge_id == challenge_id
                )
            )
        )
        user_challenge = result.scalar_one_or_none()

        if not user_challenge:
            raise ValueError("Challenge not found")

        if not user_challenge.completed:
            raise ValueError("Challenge not completed")

        if user_challenge.claimed:
            raise ValueError("Reward already claimed")

        # Get challenge details
        challenge = await db.get(DailyChallenge, challenge_id)

        # Award GEM
        user = await db.get(User, user_id)
        user.gem_balance += challenge.gem_reward

        # Create transaction
        transaction = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.DAILY_BONUS,
            amount=challenge.gem_reward,
            description=f"Challenge reward: {challenge.title}"
        )
        db.add(transaction)

        # Mark as claimed
        user_challenge.claimed = True
        user_challenge.claimed_at = datetime.utcnow()

        await db.commit()

        return {
            'challenge_title': challenge.title,
            'reward': challenge.gem_reward,
            'new_balance': user.gem_balance
        }

    @staticmethod
    async def get_user_login_streak(user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get user's login streak information."""
        result = await db.execute(
            select(LoginStreak).where(LoginStreak.user_id == user_id)
        )
        streak = result.scalar_one_or_none()

        if not streak:
            return {
                'current_streak': 0,
                'longest_streak': 0,
                'total_logins': 0,
                'last_login': None
            }

        return {
            'current_streak': streak.current_streak,
            'longest_streak': streak.longest_streak,
            'total_logins': streak.total_logins,
            'last_login': streak.last_login_date.isoformat() if streak.last_login_date else None
        }
