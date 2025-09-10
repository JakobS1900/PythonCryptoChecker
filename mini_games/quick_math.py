"""
Quick Math Mini-Game
Fast-paced crypto trading math problems for GEM coins and rewards.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, JSON
from database import Base, get_db_session
from gamification import VirtualEconomyEngine, RewardBundle
from logger import logger


class MathType(Enum):
    TRADING_CALCULATIONS = "TRADING_CALCULATIONS"  # Profit/loss, percentages
    PERCENTAGE_MATH = "PERCENTAGE_MATH"            # Crypto price changes
    COMPOUND_INTEREST = "COMPOUND_INTEREST"        # Staking rewards
    PORTFOLIO_MATH = "PORTFOLIO_MATH"              # Portfolio allocation
    QUICK_ARITHMETIC = "QUICK_ARITHMETIC"          # Basic math under pressure


class MathDifficulty(Enum):
    BEGINNER = "BEGINNER"      # Simple calculations
    INTERMEDIATE = "INTERMEDIATE"  # Medium complexity
    ADVANCED = "ADVANCED"      # Complex multi-step problems
    EXPERT = "EXPERT"          # Very challenging calculations


@dataclass
class MathProblem:
    """Individual math problem."""
    id: str
    problem_type: MathType
    difficulty: MathDifficulty
    question: str
    correct_answer: float
    options: List[str]  # For multiple choice
    explanation: str
    time_limit: int
    base_reward: float


class QuickMathSession(Base):
    """Database model for quick math game sessions."""
    __tablename__ = "quick_math_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    
    # Game Configuration
    math_type = Column(String, default="MIXED")
    difficulty = Column(String)
    total_problems = Column(Integer, default=10)
    time_limit_per_problem = Column(Integer, default=30)
    
    # Game State
    game_state = Column(String, default="ACTIVE")  # ACTIVE, COMPLETED, ABANDONED
    current_problem = Column(Integer, default=0)
    problems_data = Column(JSON)
    user_answers = Column(JSON, default=list)
    
    # Performance Metrics
    correct_answers = Column(Integer, default=0)
    total_time_taken = Column(Float, default=0.0)
    streak_count = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    speed_bonus_earned = Column(Float, default=0.0)
    
    # Timing
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    
    # Rewards
    gem_coins_earned = Column(Float, default=0.0)
    xp_earned = Column(Integer, default=0)
    accuracy_bonus = Column(Float, default=0.0)
    streak_bonus = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QuickMathGame:
    """Fast-paced crypto math game for earning GEM coins."""
    
    CRYPTO_SYMBOLS = ["BTC", "ETH", "ADA", "SOL", "DOGE", "MATIC", "LINK", "DOT", "AVAX", "UNI"]
    
    def __init__(self, virtual_economy: VirtualEconomyEngine):
        self.virtual_economy = virtual_economy
    
    def _generate_trading_calculation(self, difficulty: MathDifficulty) -> MathProblem:
        """Generate trading calculation problems."""
        
        crypto = random.choice(self.CRYPTO_SYMBOLS)
        
        if difficulty == MathDifficulty.BEGINNER:
            # Simple profit/loss calculation
            buy_price = random.uniform(100, 1000)
            sell_price = random.uniform(80, 1200)
            amount = random.randint(1, 10)
            
            profit_loss = (sell_price - buy_price) * amount
            
            question = f"You bought {amount} {crypto} at ${buy_price:.2f} each and sold at ${sell_price:.2f} each. What's your profit/loss?"
            
            # Generate options
            correct = round(profit_loss, 2)
            options = [
                f"${correct:.2f}",
                f"${correct + random.uniform(10, 50):.2f}",
                f"${correct - random.uniform(10, 30):.2f}",
                f"${correct * 1.5:.2f}"
            ]
            
        elif difficulty == MathDifficulty.INTERMEDIATE:
            # Percentage gain/loss with fees
            initial_investment = random.uniform(1000, 5000)
            percentage_change = random.uniform(-25, 50)
            trading_fee = random.uniform(0.1, 0.5)
            
            final_value = initial_investment * (1 + percentage_change/100)
            fees = initial_investment * (trading_fee/100) + final_value * (trading_fee/100)
            net_result = final_value - initial_investment - fees
            
            question = f"${initial_investment:.0f} investment in {crypto} changed by {percentage_change:+.1f}%. With {trading_fee:.1f}% trading fees (both buy/sell), what's your net result?"
            
            correct = round(net_result, 2)
            options = [
                f"${correct:.2f}",
                f"${correct + random.uniform(20, 100):.2f}",
                f"${correct - random.uniform(20, 80):.2f}",
                f"${abs(correct):.2f}" if correct < 0 else f"${-correct:.2f}"
            ]
            
        else:  # ADVANCED/EXPERT
            # Complex compound trading with multiple positions
            positions = random.randint(3, 5)
            total_profit = 0
            
            position_details = []
            for i in range(positions):
                amount = random.uniform(0.1, 2.0)
                buy_price = random.uniform(100, 2000)
                change_percent = random.uniform(-15, 25)
                sell_price = buy_price * (1 + change_percent/100)
                profit = (sell_price - buy_price) * amount
                total_profit += profit
                position_details.append(f"{amount:.1f} {crypto} at ${buy_price:.0f} → ${sell_price:.0f}")
            
            question = f"Calculate total P&L for these {crypto} trades: " + "; ".join(position_details[:2]) + f" + {positions-2} more similar trades"
            
            correct = round(total_profit, 2)
            options = [
                f"${correct:.2f}",
                f"${correct * 1.2:.2f}",
                f"${correct * 0.8:.2f}",
                f"${correct + random.uniform(50, 200):.2f}"
            ]
        
        random.shuffle(options)
        
        base_rewards = {
            MathDifficulty.BEGINNER: 15,
            MathDifficulty.INTERMEDIATE: 25,
            MathDifficulty.ADVANCED: 40,
            MathDifficulty.EXPERT: 60
        }
        
        time_limits = {
            MathDifficulty.BEGINNER: 30,
            MathDifficulty.INTERMEDIATE: 45,
            MathDifficulty.ADVANCED: 60,
            MathDifficulty.EXPERT: 75
        }
        
        return MathProblem(
            id=str(uuid.uuid4()),
            problem_type=MathType.TRADING_CALCULATIONS,
            difficulty=difficulty,
            question=question,
            correct_answer=correct,
            options=options,
            explanation=f"Calculation: {crypto} trading profit/loss = ${correct:.2f}",
            time_limit=time_limits[difficulty],
            base_reward=base_rewards[difficulty]
        )
    
    def _generate_percentage_math(self, difficulty: MathDifficulty) -> MathProblem:
        """Generate percentage calculation problems."""
        
        crypto = random.choice(self.CRYPTO_SYMBOLS)
        
        if difficulty == MathDifficulty.BEGINNER:
            # Simple percentage change
            old_price = random.uniform(50, 500)
            new_price = random.uniform(40, 600)
            
            percentage_change = ((new_price - old_price) / old_price) * 100
            
            question = f"{crypto} price went from ${old_price:.2f} to ${new_price:.2f}. What's the percentage change?"
            
        elif difficulty == MathDifficulty.INTERMEDIATE:
            # Compound percentage changes
            initial_price = random.uniform(100, 1000)
            changes = [random.uniform(-10, 15) for _ in range(3)]
            
            current_price = initial_price
            for change in changes:
                current_price *= (1 + change/100)
            
            total_change = ((current_price - initial_price) / initial_price) * 100
            
            question = f"{crypto} had price changes: {changes[0]:+.1f}%, {changes[1]:+.1f}%, {changes[2]:+.1f}%. Starting at ${initial_price:.0f}, what's the total % change?"
            percentage_change = total_change
            
        else:  # ADVANCED/EXPERT
            # Complex percentage with portfolio allocation
            total_portfolio = random.uniform(10000, 50000)
            crypto_allocation = random.uniform(20, 60)  # percentage
            crypto_amount = total_portfolio * (crypto_allocation/100)
            price_change = random.uniform(-30, 80)
            
            new_crypto_value = crypto_amount * (1 + price_change/100)
            new_portfolio = total_portfolio - crypto_amount + new_crypto_value
            portfolio_change = ((new_portfolio - total_portfolio) / total_portfolio) * 100
            
            question = f"Portfolio: ${total_portfolio:.0f}, {crypto_allocation:.0f}% in {crypto} which changed {price_change:+.1f}%. What's the total portfolio % change?"
            percentage_change = portfolio_change
        
        correct = round(percentage_change, 2)
        options = [
            f"{correct:+.2f}%",
            f"{correct + random.uniform(1, 5):+.2f}%",
            f"{correct - random.uniform(1, 4):+.2f}%",
            f"{correct * 1.3:+.2f}%"
        ]
        
        random.shuffle(options)
        
        base_rewards = {
            MathDifficulty.BEGINNER: 18,
            MathDifficulty.INTERMEDIATE: 30,
            MathDifficulty.ADVANCED: 45,
            MathDifficulty.EXPERT: 65
        }
        
        return MathProblem(
            id=str(uuid.uuid4()),
            problem_type=MathType.PERCENTAGE_MATH,
            difficulty=difficulty,
            question=question,
            correct_answer=correct,
            options=options,
            explanation=f"Percentage change: {correct:+.2f}%",
            time_limit=35,
            base_reward=base_rewards[difficulty]
        )
    
    def _generate_compound_interest(self, difficulty: MathDifficulty) -> MathProblem:
        """Generate compound interest problems (staking rewards)."""
        
        crypto = random.choice(self.CRYPTO_SYMBOLS)
        
        if difficulty == MathDifficulty.BEGINNER:
            # Simple annual staking
            principal = random.uniform(1000, 5000)
            annual_rate = random.uniform(5, 15)
            years = 1
            
            final_amount = principal * (1 + annual_rate/100) ** years
            interest_earned = final_amount - principal
            
            question = f"Staking {principal:.0f} {crypto} at {annual_rate:.0f}% APY for {years} year. How much interest earned?"
            
        elif difficulty == MathDifficulty.INTERMEDIATE:
            # Monthly compounding
            principal = random.uniform(2000, 8000)
            annual_rate = random.uniform(8, 20)
            months = random.randint(6, 24)
            
            monthly_rate = annual_rate / 12 / 100
            final_amount = principal * (1 + monthly_rate) ** months
            interest_earned = final_amount - principal
            
            question = f"Staking ${principal:.0f} in {crypto} at {annual_rate:.1f}% APY (monthly compounding) for {months} months. Interest earned?"
            
        else:  # ADVANCED/EXPERT
            # Daily compounding with reinvestment
            principal = random.uniform(5000, 15000)
            annual_rate = random.uniform(12, 25)
            days = random.randint(90, 365)
            
            daily_rate = annual_rate / 365 / 100
            final_amount = principal * (1 + daily_rate) ** days
            interest_earned = final_amount - principal
            
            question = f"${principal:.0f} staked in {crypto} at {annual_rate:.1f}% APY (daily compounding) for {days} days. Total interest?"
        
        correct = round(interest_earned, 2)
        options = [
            f"${correct:.2f}",
            f"${correct * 1.1:.2f}",
            f"${correct * 0.9:.2f}",
            f"${correct + random.uniform(50, 200):.2f}"
        ]
        
        random.shuffle(options)
        
        base_rewards = {
            MathDifficulty.BEGINNER: 20,
            MathDifficulty.INTERMEDIATE: 35,
            MathDifficulty.ADVANCED: 50,
            MathDifficulty.EXPERT: 70
        }
        
        return MathProblem(
            id=str(uuid.uuid4()),
            problem_type=MathType.COMPOUND_INTEREST,
            difficulty=difficulty,
            question=question,
            correct_answer=correct,
            options=options,
            explanation=f"Compound interest earned: ${correct:.2f}",
            time_limit=40,
            base_reward=base_rewards[difficulty]
        )
    
    def _generate_quick_arithmetic(self, difficulty: MathDifficulty) -> MathProblem:
        """Generate quick arithmetic problems."""
        
        if difficulty == MathDifficulty.BEGINNER:
            # Simple addition/subtraction
            a = random.randint(10, 99)
            b = random.randint(10, 99)
            operation = random.choice(['+', '-'])
            
            if operation == '+':
                result = a + b
                question = f"{a} + {b} = ?"
            else:
                result = a - b
                question = f"{a} - {b} = ?"
            
        elif difficulty == MathDifficulty.INTERMEDIATE:
            # Multiplication and division
            if random.choice([True, False]):
                a = random.randint(12, 25)
                b = random.randint(11, 19)
                result = a * b
                question = f"{a} × {b} = ?"
            else:
                result = random.randint(100, 500)
                divisor = random.randint(2, 15)
                dividend = result * divisor
                question = f"{dividend} ÷ {divisor} = ?"
                
        else:  # ADVANCED/EXPERT
            # Mixed operations with crypto numbers
            operations = [
                lambda: (lambda a, b, c: a * b + c)(random.randint(15, 30), random.randint(8, 15), random.randint(50, 200)),
                lambda: (lambda a, b, c: (a + b) * c)(random.randint(25, 50), random.randint(30, 60), random.randint(3, 8)),
                lambda: (lambda a, b: int(math.sqrt(a) * b))(random.choice([16, 25, 36, 49, 64, 81, 100]), random.randint(5, 12))
            ]
            
            op_func = random.choice(operations)
            result = op_func()
            
            # Generate question based on operation type
            if random.choice([True, False]):
                a, b, c = random.randint(15, 30), random.randint(8, 15), random.randint(50, 200)
                if a * b + c == result:
                    question = f"{a} × {b} + {c} = ?"
                else:
                    question = f"({a} + {b}) × {c} = ?"
            else:
                base = random.choice([4, 5, 6, 7, 8, 9, 10])
                multiplier = random.randint(5, 12)
                result = base * base * multiplier
                question = f"{base}² × {multiplier} = ?"
        
        correct = float(result)
        options = [
            str(int(correct)),
            str(int(correct + random.randint(1, 10))),
            str(int(correct - random.randint(1, 8))),
            str(int(correct + random.randint(15, 50)))
        ]
        
        random.shuffle(options)
        
        base_rewards = {
            MathDifficulty.BEGINNER: 12,
            MathDifficulty.INTERMEDIATE: 20,
            MathDifficulty.ADVANCED: 32,
            MathDifficulty.EXPERT: 45
        }
        
        time_limits = {
            MathDifficulty.BEGINNER: 15,
            MathDifficulty.INTERMEDIATE: 20,
            MathDifficulty.ADVANCED: 25,
            MathDifficulty.EXPERT: 30
        }
        
        return MathProblem(
            id=str(uuid.uuid4()),
            problem_type=MathType.QUICK_ARITHMETIC,
            difficulty=difficulty,
            question=question,
            correct_answer=correct,
            options=options,
            explanation=f"Answer: {int(correct)}",
            time_limit=time_limits[difficulty],
            base_reward=base_rewards[difficulty]
        )
    
    async def start_new_game(
        self,
        session: AsyncSession,
        user_id: str,
        difficulty: MathDifficulty = MathDifficulty.BEGINNER,
        total_problems: int = 10,
        math_type: str = "MIXED"
    ) -> Dict[str, Any]:
        """Start a new quick math game session."""
        
        problems = []
        
        for i in range(total_problems):
            if math_type == "MIXED":
                problem_type = random.choice(list(MathType))
            else:
                problem_type = MathType(math_type)
            
            if problem_type == MathType.TRADING_CALCULATIONS:
                problem = self._generate_trading_calculation(difficulty)
            elif problem_type == MathType.PERCENTAGE_MATH:
                problem = self._generate_percentage_math(difficulty)
            elif problem_type == MathType.COMPOUND_INTEREST:
                problem = self._generate_compound_interest(difficulty)
            else:  # QUICK_ARITHMETIC
                problem = self._generate_quick_arithmetic(difficulty)
            
            problems.append({
                "id": problem.id,
                "type": problem.problem_type.value,
                "question": problem.question,
                "options": problem.options,
                "correct_answer": problem.correct_answer,
                "explanation": problem.explanation,
                "time_limit": problem.time_limit,
                "base_reward": problem.base_reward
            })
        
        # Create game session
        game_session = QuickMathSession(
            user_id=user_id,
            math_type=math_type,
            difficulty=difficulty.value,
            total_problems=total_problems,
            problems_data=problems
        )
        
        session.add(game_session)
        await session.commit()
        
        # Return first problem
        first_problem = problems[0]
        
        logger.info(f"Started quick math game for user {user_id}: {difficulty.value}, {total_problems} problems")
        
        return {
            "status": "success",
            "game_id": game_session.id,
            "difficulty": difficulty.value,
            "total_problems": total_problems,
            "math_type": math_type,
            "current_problem": 1,
            "question": {
                "id": first_problem["id"],
                "type": first_problem["type"],
                "question": first_problem["question"],
                "options": first_problem["options"],
                "time_limit": first_problem["time_limit"],
                "potential_reward": first_problem["base_reward"]
            }
        }
    
    async def submit_answer(
        self,
        session: AsyncSession,
        game_id: str,
        problem_id: str,
        answer: str,
        time_taken: float
    ) -> Dict[str, Any]:
        """Submit an answer for the current problem."""
        
        from sqlalchemy import select
        result = await session.execute(
            select(QuickMathSession).where(QuickMathSession.id == game_id)
        )
        game_session = result.scalar_one_or_none()
        
        if not game_session or game_session.game_state != "ACTIVE":
            return {"status": "error", "message": "Game not found or inactive"}
        
        problems = game_session.problems_data
        current_p_index = game_session.current_problem
        
        if current_p_index >= len(problems):
            return {"status": "error", "message": "No more problems"}
        
        current_problem = problems[current_p_index]
        
        if current_problem["id"] != problem_id:
            return {"status": "error", "message": "Problem ID mismatch"}
        
        # Check answer (handle both numeric and string answers)
        try:
            # Try to parse as number first
            user_answer = float(answer.replace('$', '').replace('%', '').replace('+', '').replace(' ', ''))
            is_correct = abs(user_answer - current_problem["correct_answer"]) < 0.01
        except:
            # If parsing fails, do string comparison
            is_correct = answer.strip() == str(current_problem["correct_answer"])
        
        # Update game state
        user_answers = game_session.user_answers or []
        user_answers.append({
            "problem_id": problem_id,
            "answer": answer,
            "correct_answer": current_problem["correct_answer"],
            "is_correct": is_correct,
            "time_taken": time_taken,
            "explanation": current_problem["explanation"]
        })
        
        game_session.user_answers = user_answers
        game_session.total_time_taken += time_taken
        
        # Speed bonus for quick answers
        if is_correct and time_taken <= current_problem["time_limit"] * 0.5:
            speed_bonus = current_problem["base_reward"] * 0.2  # 20% speed bonus
            game_session.speed_bonus_earned += speed_bonus
        
        if is_correct:
            game_session.correct_answers += 1
            game_session.streak_count += 1
            game_session.best_streak = max(game_session.best_streak, game_session.streak_count)
        else:
            game_session.streak_count = 0
        
        # Move to next problem
        game_session.current_problem += 1
        
        # Check if game is complete
        game_complete = game_session.current_problem >= game_session.total_problems
        
        if game_complete:
            await self._complete_game(session, game_session)
            next_problem = None
        else:
            next_problem = problems[game_session.current_problem]
        
        await session.commit()
        
        response = {
            "status": "success",
            "is_correct": is_correct,
            "correct_answer": current_problem["correct_answer"],
            "explanation": current_problem["explanation"],
            "game_complete": game_complete,
            "current_score": game_session.correct_answers,
            "total_problems": game_session.total_problems,
            "current_streak": game_session.streak_count,
            "best_streak": game_session.best_streak,
            "time_taken": time_taken
        }
        
        if game_complete:
            response.update({
                "final_score": f"{game_session.correct_answers}/{game_session.total_problems}",
                "total_time": game_session.total_time_taken,
                "gem_coins_earned": game_session.gem_coins_earned,
                "xp_earned": game_session.xp_earned,
                "speed_bonus": game_session.speed_bonus_earned,
                "accuracy_bonus": game_session.accuracy_bonus,
                "streak_bonus": game_session.streak_bonus
            })
        else:
            response["next_problem"] = {
                "id": next_problem["id"],
                "type": next_problem["type"],
                "question": next_problem["question"],
                "options": next_problem["options"],
                "time_limit": next_problem["time_limit"],
                "potential_reward": next_problem["base_reward"],
                "problem_number": game_session.current_problem + 1
            }
        
        return response
    
    async def _complete_game(self, session: AsyncSession, game_session: QuickMathSession):
        """Complete the game and calculate rewards."""
        
        game_session.end_time = datetime.utcnow()
        game_session.game_state = "COMPLETED"
        
        # Calculate base reward
        problems = game_session.problems_data
        total_base_reward = sum(p["base_reward"] for p in problems)
        
        # Calculate accuracy
        accuracy = game_session.correct_answers / game_session.total_problems
        
        # Base reward proportional to correct answers
        base_gems = total_base_reward * accuracy
        
        # Accuracy bonus
        accuracy_bonus = 0.0
        if accuracy >= 0.9:
            accuracy_bonus = base_gems * 0.5  # 50% bonus for 90%+
        elif accuracy >= 0.8:
            accuracy_bonus = base_gems * 0.25  # 25% bonus for 80%+
        
        # Streak bonus
        streak_bonus = 0.0
        if game_session.best_streak >= 5:
            streak_bonus = base_gems * 0.3  # 30% bonus for 5+ streak
        elif game_session.best_streak >= 3:
            streak_bonus = base_gems * 0.15  # 15% bonus for 3+ streak
        
        # Total final rewards
        final_gems = base_gems + accuracy_bonus + streak_bonus + game_session.speed_bonus_earned
        final_xp = int(final_gems * 0.4)  # XP is 40% of GEM reward
        
        game_session.gem_coins_earned = final_gems
        game_session.xp_earned = final_xp
        game_session.accuracy_bonus = accuracy_bonus
        game_session.streak_bonus = streak_bonus
        
        # Award through virtual economy
        reward_bundle = RewardBundle(
            gem_coins=final_gems,
            experience_points=final_xp,
            description=f"Quick Math ({game_session.difficulty}): {game_session.correct_answers}/{game_session.total_problems} correct, {game_session.best_streak} best streak"
        )
        
        await self.virtual_economy.award_reward(session, game_session.user_id, reward_bundle)
        
        logger.info(f"Quick math completed - User: {game_session.user_id}, Score: {game_session.correct_answers}/{game_session.total_problems}, Reward: {final_gems} GEM")
    
    async def get_user_stats(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get user's quick math game statistics."""
        
        from sqlalchemy import select, func
        
        result = await session.execute(
            select(
                func.count(QuickMathSession.id).label("total_games"),
                func.sum(QuickMathSession.gem_coins_earned).label("total_gems"),
                func.sum(QuickMathSession.xp_earned).label("total_xp"),
                func.sum(QuickMathSession.correct_answers).label("total_correct"),
                func.sum(QuickMathSession.total_problems).label("total_problems"),
                func.max(QuickMathSession.best_streak).label("longest_streak"),
                func.avg(QuickMathSession.total_time_taken).label("avg_game_time"),
                func.sum(QuickMathSession.speed_bonus_earned).label("total_speed_bonus")
            ).where(
                (QuickMathSession.user_id == user_id) & 
                (QuickMathSession.game_state == "COMPLETED")
            )
        )
        stats = result.first()
        
        total_games = stats.total_games or 0
        total_correct = stats.total_correct or 0
        total_problems = stats.total_problems or 0
        
        overall_accuracy = (total_correct / total_problems * 100) if total_problems > 0 else 0
        
        return {
            "total_games": total_games,
            "total_gems_earned": stats.total_gems or 0.0,
            "total_xp_earned": stats.total_xp or 0,
            "overall_accuracy": overall_accuracy,
            "total_problems_solved": total_problems,
            "longest_streak": stats.longest_streak or 0,
            "average_game_time": stats.avg_game_time or 0.0,
            "total_speed_bonuses": stats.total_speed_bonus or 0.0
        }