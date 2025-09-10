"""
Crypto Number Prediction Mini-Game
Players predict crypto price movements and number patterns for GEM rewards.
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


class PredictionType(Enum):
    PRICE_DIRECTION = "PRICE_DIRECTION"  # UP/DOWN/SIDEWAYS
    NUMBER_SEQUENCE = "NUMBER_SEQUENCE"  # Next number in sequence
    PRICE_RANGE = "PRICE_RANGE"         # High/Medium/Low range
    FIBONACCI = "FIBONACCI"             # Fibonacci sequences
    PATTERN_MATCH = "PATTERN_MATCH"     # Pattern recognition


class PredictionDifficulty(Enum):
    BEGINNER = "BEGINNER"  # Simple patterns, higher success rate
    INTERMEDIATE = "INTERMEDIATE"  # Medium complexity
    ADVANCED = "ADVANCED"  # Complex patterns, higher rewards
    EXPERT = "EXPERT"     # Very difficult, maximum rewards


@dataclass
class PredictionChallenge:
    """Individual prediction challenge."""
    id: str
    type: PredictionType
    difficulty: PredictionDifficulty
    question: str
    options: List[str]
    correct_answer: str
    explanation: str
    base_reward: float
    time_limit: int  # seconds


class NumberPredictionSession(Base):
    """Database model for number prediction game sessions."""
    __tablename__ = "number_prediction_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    
    # Game Configuration
    prediction_type = Column(String)
    difficulty = Column(String)
    total_questions = Column(Integer, default=5)
    
    # Game State
    game_state = Column(String, default="ACTIVE")  # ACTIVE, COMPLETED, ABANDONED
    current_question = Column(Integer, default=0)
    questions_data = Column(JSON)  # Serialized questions and answers
    user_answers = Column(JSON, default=list)
    
    # Performance Metrics
    correct_answers = Column(Integer, default=0)
    total_time_taken = Column(Float, default=0.0)
    streak_count = Column(Integer, default=0)  # Consecutive correct answers
    best_streak = Column(Integer, default=0)
    
    # Timing
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    
    # Rewards
    gem_coins_earned = Column(Float, default=0.0)
    xp_earned = Column(Integer, default=0)
    accuracy_bonus = Column(Float, default=0.0)
    speed_bonus = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NumberPredictionGame:
    """Crypto number prediction game for earning GEM coins."""
    
    def __init__(self, virtual_economy: VirtualEconomyEngine):
        self.virtual_economy = virtual_economy
    
    def _generate_price_direction_challenge(self, difficulty: PredictionDifficulty) -> PredictionChallenge:
        """Generate a price direction prediction challenge."""
        
        crypto_symbols = ["BTC", "ETH", "ADA", "SOL", "DOGE", "MATIC", "LINK", "DOT"]
        crypto = random.choice(crypto_symbols)
        
        # Generate realistic price data
        base_price = random.uniform(100, 50000)
        price_changes = []
        
        if difficulty == PredictionDifficulty.BEGINNER:
            # Clear trends
            trend = random.choice(["up", "down", "sideways"])
            if trend == "up":
                price_changes = [random.uniform(2, 8) for _ in range(5)]
            elif trend == "down":
                price_changes = [random.uniform(-8, -2) for _ in range(5)]
            else:  # sideways
                price_changes = [random.uniform(-1, 1) for _ in range(5)]
            
            question = f"Based on the last 5 price changes for {crypto}: {[f'{c:+.1f}%' for c in price_changes]}, what's the likely next direction?"
            
        elif difficulty == PredictionDifficulty.INTERMEDIATE:
            # Mixed with some pattern
            price_changes = [random.uniform(-5, 5) for _ in range(7)]
            question = f"{crypto} price changes over 7 periods: {[f'{c:+.1f}%' for c in price_changes]}. Predict the next move:"
            
        else:  # ADVANCED/EXPERT
            # Complex patterns with technical indicators
            price_changes = [random.uniform(-10, 10) for _ in range(10)]
            rsi = random.uniform(20, 80)
            ma_position = random.choice(["above", "below"])
            
            question = f"{crypto} analysis: 10-period changes {[f'{c:+.1f}%' for c in price_changes[-3:]]}, RSI: {rsi:.1f}, Price {ma_position} MA. Next 4-hour candle?"
        
        # Determine correct answer based on pattern
        avg_change = sum(price_changes[-3:]) / 3  # Last 3 periods average
        
        if avg_change > 2:
            correct_answer = "UP"
        elif avg_change < -2:
            correct_answer = "DOWN" 
        else:
            correct_answer = "SIDEWAYS"
        
        options = ["UP", "DOWN", "SIDEWAYS"]
        
        base_rewards = {
            PredictionDifficulty.BEGINNER: 15,
            PredictionDifficulty.INTERMEDIATE: 25,
            PredictionDifficulty.ADVANCED: 40,
            PredictionDifficulty.EXPERT: 60
        }
        
        time_limits = {
            PredictionDifficulty.BEGINNER: 30,
            PredictionDifficulty.INTERMEDIATE: 25,
            PredictionDifficulty.ADVANCED: 20,
            PredictionDifficulty.EXPERT: 15
        }
        
        return PredictionChallenge(
            id=str(uuid.uuid4()),
            type=PredictionType.PRICE_DIRECTION,
            difficulty=difficulty,
            question=question,
            options=options,
            correct_answer=correct_answer,
            explanation=f"Based on recent trend analysis, {crypto} shows {correct_answer.lower()} momentum.",
            base_reward=base_rewards[difficulty],
            time_limit=time_limits[difficulty]
        )
    
    def _generate_number_sequence_challenge(self, difficulty: PredictionDifficulty) -> PredictionChallenge:
        """Generate a number sequence prediction challenge."""
        
        if difficulty == PredictionDifficulty.BEGINNER:
            # Simple arithmetic progression
            start = random.randint(1, 20)
            diff = random.randint(2, 10)
            sequence = [start + i * diff for i in range(5)]
            next_num = sequence[-1] + diff
            
            question = f"What's the next number in this sequence? {sequence}"
            options = [str(next_num), str(next_num + diff), str(next_num - diff), str(next_num + random.randint(1, 5))]
            
        elif difficulty == PredictionDifficulty.INTERMEDIATE:
            # Geometric progression or square numbers
            if random.choice([True, False]):
                # Geometric
                start = random.randint(2, 8)
                ratio = random.randint(2, 4)
                sequence = [start * (ratio ** i) for i in range(4)]
                next_num = sequence[-1] * ratio
            else:
                # Square numbers with offset
                offset = random.randint(1, 10)
                sequence = [i*i + offset for i in range(1, 5)]
                next_num = 25 + offset  # 5^2 + offset
            
            question = f"Find the pattern and next number: {sequence}"
            options = [str(next_num), str(next_num + 5), str(next_num - 3), str(next_num * 2)]
            
        else:  # ADVANCED/EXPERT
            # Fibonacci variations or complex patterns
            if random.choice([True, False]):
                # Fibonacci-like
                a, b = random.randint(1, 5), random.randint(1, 8)
                sequence = [a, b]
                for _ in range(4):
                    sequence.append(sequence[-1] + sequence[-2])
                next_num = sequence[-1] + sequence[-2]
            else:
                # Alternating operations
                base = random.randint(2, 10)
                sequence = [base]
                operations = [random.choice([2, 3, 4]) for _ in range(4)]
                for i, op in enumerate(operations):
                    if i % 2 == 0:
                        sequence.append(sequence[-1] * op)
                    else:
                        sequence.append(sequence[-1] + op)
                
                # Continue pattern
                next_op = operations[len(operations) % len(operations)]
                if len(sequence) % 2 == 1:  # Odd position, multiply
                    next_num = sequence[-1] * next_op
                else:  # Even position, add
                    next_num = sequence[-1] + next_op
            
            question = f"Complex pattern - what comes next? {sequence}"
            options = [str(next_num), str(next_num + random.randint(1, 10)), 
                      str(next_num - random.randint(1, 5)), str(int(next_num * 1.2))]
        
        random.shuffle(options)
        
        base_rewards = {
            PredictionDifficulty.BEGINNER: 20,
            PredictionDifficulty.INTERMEDIATE: 35,
            PredictionDifficulty.ADVANCED: 55,
            PredictionDifficulty.EXPERT: 80
        }
        
        return PredictionChallenge(
            id=str(uuid.uuid4()),
            type=PredictionType.NUMBER_SEQUENCE,
            difficulty=difficulty,
            question=question,
            options=options,
            correct_answer=str(next_num),
            explanation=f"The pattern continues with {next_num}",
            base_reward=base_rewards[difficulty],
            time_limit=45 if difficulty in [PredictionDifficulty.BEGINNER, PredictionDifficulty.INTERMEDIATE] else 60
        )
    
    def _generate_fibonacci_challenge(self, difficulty: PredictionDifficulty) -> PredictionChallenge:
        """Generate Fibonacci-based challenges."""
        
        if difficulty == PredictionDifficulty.BEGINNER:
            # Classic Fibonacci
            fib = [1, 1, 2, 3, 5, 8, 13]
            question = "Classic Fibonacci sequence - what's next? [1, 1, 2, 3, 5, 8, 13, ?]"
            correct = 21
            options = ["21", "19", "23", "18"]
            
        elif difficulty == PredictionDifficulty.INTERMEDIATE:
            # Fibonacci with multiplier
            multiplier = random.randint(2, 4)
            fib = [1*multiplier, 1*multiplier, 2*multiplier, 3*multiplier, 5*multiplier]
            next_fib = 8 * multiplier
            
            question = f"Modified Fibonacci (×{multiplier}): {fib}. Next number?"
            correct = next_fib
            options = [str(next_fib), str(next_fib + multiplier), str(next_fib - multiplier), str(next_fib * 2)]
            
        else:  # ADVANCED/EXPERT
            # Fibonacci squares or complex variation
            if random.choice([True, False]):
                # Fibonacci squares
                fib_base = [1, 1, 2, 3, 5]
                fib_squares = [x*x for x in fib_base]
                next_square = 8*8  # Next Fibonacci number squared
                
                question = f"Fibonacci squares: {fib_squares}. Next value?"
                correct = next_square
                options = [str(next_square), str(next_square + 10), str(next_square - 5), str(int(next_square * 1.1))]
            else:
                # Tribonacci (sum of last 3)
                trib = [1, 1, 2, 4, 7, 13]
                next_trib = 7 + 13 + 4  # Sum of last 3
                
                question = f"Tribonacci (sum of last 3): {trib}. Continue the pattern:"
                correct = next_trib
                options = [str(next_trib), str(next_trib + 3), str(next_trib - 2), str(next_trib + 7)]
        
        base_rewards = {
            PredictionDifficulty.BEGINNER: 25,
            PredictionDifficulty.INTERMEDIATE: 45,
            PredictionDifficulty.ADVANCED: 70,
            PredictionDifficulty.EXPERT: 100
        }
        
        return PredictionChallenge(
            id=str(uuid.uuid4()),
            type=PredictionType.FIBONACCI,
            difficulty=difficulty,
            question=question,
            options=options,
            correct_answer=str(correct),
            explanation=f"Following the Fibonacci pattern: {correct}",
            base_reward=base_rewards[difficulty],
            time_limit=30 if difficulty == PredictionDifficulty.BEGINNER else 45
        )
    
    async def start_new_game(
        self,
        session: AsyncSession,
        user_id: str,
        difficulty: PredictionDifficulty = PredictionDifficulty.BEGINNER,
        total_questions: int = 5
    ) -> Dict[str, Any]:
        """Start a new number prediction game session."""
        
        # Generate random mix of challenge types
        challenge_types = [
            PredictionType.PRICE_DIRECTION,
            PredictionType.NUMBER_SEQUENCE, 
            PredictionType.FIBONACCI
        ]
        
        questions = []
        for i in range(total_questions):
            challenge_type = random.choice(challenge_types)
            
            if challenge_type == PredictionType.PRICE_DIRECTION:
                challenge = self._generate_price_direction_challenge(difficulty)
            elif challenge_type == PredictionType.NUMBER_SEQUENCE:
                challenge = self._generate_number_sequence_challenge(difficulty)
            else:  # FIBONACCI
                challenge = self._generate_fibonacci_challenge(difficulty)
            
            questions.append({
                "id": challenge.id,
                "type": challenge.type.value,
                "question": challenge.question,
                "options": challenge.options,
                "correct_answer": challenge.correct_answer,
                "explanation": challenge.explanation,
                "base_reward": challenge.base_reward,
                "time_limit": challenge.time_limit
            })
        
        # Create game session
        game_session = NumberPredictionSession(
            user_id=user_id,
            prediction_type="MIXED",
            difficulty=difficulty.value,
            total_questions=total_questions,
            questions_data=questions
        )
        
        session.add(game_session)
        await session.commit()
        
        # Return first question
        first_question = questions[0]
        
        logger.info(f"Started number prediction game for user {user_id}: {difficulty.value}, {total_questions} questions")
        
        return {
            "status": "success",
            "game_id": game_session.id,
            "difficulty": difficulty.value,
            "total_questions": total_questions,
            "current_question": 1,
            "question": {
                "id": first_question["id"],
                "type": first_question["type"],
                "question": first_question["question"],
                "options": first_question["options"],
                "time_limit": first_question["time_limit"],
                "potential_reward": first_question["base_reward"]
            }
        }
    
    async def submit_answer(
        self,
        session: AsyncSession,
        game_id: str,
        question_id: str,
        answer: str,
        time_taken: float
    ) -> Dict[str, Any]:
        """Submit an answer for the current question."""
        
        from sqlalchemy import select
        result = await session.execute(
            select(NumberPredictionSession).where(NumberPredictionSession.id == game_id)
        )
        game_session = result.scalar_one_or_none()
        
        if not game_session or game_session.game_state != "ACTIVE":
            return {"status": "error", "message": "Game not found or inactive"}
        
        questions = game_session.questions_data
        current_q_index = game_session.current_question
        
        if current_q_index >= len(questions):
            return {"status": "error", "message": "No more questions"}
        
        current_question = questions[current_q_index]
        
        if current_question["id"] != question_id:
            return {"status": "error", "message": "Question ID mismatch"}
        
        # Check answer
        is_correct = answer == current_question["correct_answer"]
        
        # Update game state
        user_answers = game_session.user_answers or []
        user_answers.append({
            "question_id": question_id,
            "answer": answer,
            "correct_answer": current_question["correct_answer"],
            "is_correct": is_correct,
            "time_taken": time_taken,
            "explanation": current_question["explanation"]
        })
        
        game_session.user_answers = user_answers
        game_session.total_time_taken += time_taken
        
        if is_correct:
            game_session.correct_answers += 1
            game_session.streak_count += 1
            game_session.best_streak = max(game_session.best_streak, game_session.streak_count)
        else:
            game_session.streak_count = 0
        
        # Move to next question
        game_session.current_question += 1
        
        # Check if game is complete
        game_complete = game_session.current_question >= game_session.total_questions
        
        if game_complete:
            await self._complete_game(session, game_session)
            next_question = None
        else:
            next_question = questions[game_session.current_question]
        
        await session.commit()
        
        response = {
            "status": "success",
            "is_correct": is_correct,
            "correct_answer": current_question["correct_answer"],
            "explanation": current_question["explanation"],
            "game_complete": game_complete,
            "current_score": game_session.correct_answers,
            "total_questions": game_session.total_questions,
            "current_streak": game_session.streak_count,
            "best_streak": game_session.best_streak
        }
        
        if game_complete:
            response.update({
                "final_score": f"{game_session.correct_answers}/{game_session.total_questions}",
                "total_time": game_session.total_time_taken,
                "gem_coins_earned": game_session.gem_coins_earned,
                "xp_earned": game_session.xp_earned,
                "accuracy_bonus": game_session.accuracy_bonus,
                "speed_bonus": game_session.speed_bonus
            })
        else:
            response["next_question"] = {
                "id": next_question["id"],
                "type": next_question["type"],
                "question": next_question["question"],
                "options": next_question["options"],
                "time_limit": next_question["time_limit"],
                "potential_reward": next_question["base_reward"],
                "question_number": game_session.current_question + 1
            }
        
        return response
    
    async def _complete_game(self, session: AsyncSession, game_session: NumberPredictionSession):
        """Complete the game and calculate rewards."""
        
        game_session.end_time = datetime.utcnow()
        game_session.game_state = "COMPLETED"
        
        # Calculate base reward
        questions = game_session.questions_data
        total_base_reward = sum(q["base_reward"] for q in questions)
        
        # Calculate accuracy percentage
        accuracy = game_session.correct_answers / game_session.total_questions
        
        # Base reward is proportional to correct answers
        base_gems = total_base_reward * accuracy
        
        # Accuracy bonus (90%+ gets bonus)
        accuracy_bonus = 0.0
        if accuracy >= 0.9:
            accuracy_bonus = base_gems * 0.4  # 40% bonus for 90%+
        elif accuracy >= 0.8:
            accuracy_bonus = base_gems * 0.2  # 20% bonus for 80%+
        
        # Speed bonus (average time under threshold)
        avg_time_per_question = game_session.total_time_taken / game_session.total_questions
        target_time = 30  # Target 30 seconds per question
        
        speed_bonus = 0.0
        if avg_time_per_question <= target_time:
            speed_multiplier = max(0.1, (target_time - avg_time_per_question) / target_time)
            speed_bonus = base_gems * speed_multiplier * 0.3  # Up to 30% speed bonus
        
        # Streak bonus
        streak_bonus = 0.0
        if game_session.best_streak >= 3:
            streak_bonus = base_gems * 0.15  # 15% bonus for 3+ streak
        if game_session.best_streak >= 5:
            streak_bonus = base_gems * 0.25  # 25% bonus for 5+ streak
        
        # Calculate final rewards
        final_gems = base_gems + accuracy_bonus + speed_bonus + streak_bonus
        final_xp = int(final_gems * 0.5)  # XP is 50% of GEM reward
        
        game_session.gem_coins_earned = final_gems
        game_session.xp_earned = final_xp
        game_session.accuracy_bonus = accuracy_bonus
        game_session.speed_bonus = speed_bonus
        
        # Award through virtual economy
        reward_bundle = RewardBundle(
            gem_coins=final_gems,
            experience_points=final_xp,
            description=f"Number Prediction ({game_session.difficulty}): {game_session.correct_answers}/{game_session.total_questions} correct, {accuracy:.1%} accuracy"
        )
        
        await self.virtual_economy.award_reward(session, game_session.user_id, reward_bundle)
        
        logger.info(f"Number prediction completed - User: {game_session.user_id}, Score: {game_session.correct_answers}/{game_session.total_questions}, Reward: {final_gems} GEM")
    
    async def get_user_stats(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get user's number prediction game statistics."""
        
        from sqlalchemy import select, func
        
        result = await session.execute(
            select(
                func.count(NumberPredictionSession.id).label("total_games"),
                func.sum(NumberPredictionSession.gem_coins_earned).label("total_gems"),
                func.sum(NumberPredictionSession.xp_earned).label("total_xp"),
                func.sum(NumberPredictionSession.correct_answers).label("total_correct"),
                func.sum(NumberPredictionSession.total_questions).label("total_questions"),
                func.max(NumberPredictionSession.best_streak).label("longest_streak"),
                func.avg(NumberPredictionSession.total_time_taken).label("avg_game_time")
            ).where(
                (NumberPredictionSession.user_id == user_id) & 
                (NumberPredictionSession.game_state == "COMPLETED")
            )
        )
        stats = result.first()
        
        total_games = stats.total_games or 0
        total_correct = stats.total_correct or 0
        total_questions = stats.total_questions or 0
        
        overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
        
        return {
            "total_games": total_games,
            "total_gems_earned": stats.total_gems or 0.0,
            "total_xp_earned": stats.total_xp or 0,
            "overall_accuracy": overall_accuracy,
            "total_questions_answered": total_questions,
            "longest_streak": stats.longest_streak or 0,
            "average_game_time": stats.avg_game_time or 0.0
        }