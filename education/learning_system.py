"""
Investment Education and Learning System - Comprehensive crypto education platform.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, Integer, JSON

from database import get_db_session, Base
from virtual_economy import virtual_economy_engine
from logger import logger


class LessonDifficulty(Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    EXPERT = "EXPERT"


class LessonType(Enum):
    TUTORIAL = "TUTORIAL"
    INTERACTIVE = "INTERACTIVE"
    QUIZ = "QUIZ"
    SIMULATION = "SIMULATION"
    CASE_STUDY = "CASE_STUDY"


class UserProgress(Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    MASTERED = "MASTERED"


class EducationLesson(Base):
    """Educational lesson content."""
    __tablename__ = "education_lessons"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Lesson Info
    title = Column(String, nullable=False)
    description = Column(Text)
    content = Column(Text, nullable=False)
    lesson_type = Column(String, nullable=False)  # TUTORIAL, INTERACTIVE, etc.
    difficulty = Column(String, nullable=False)   # BEGINNER, INTERMEDIATE, etc.
    category = Column(String, nullable=False)     # Trading, Analysis, Blockchain, etc.
    
    # Ordering and Structure
    course_id = Column(String, index=True)        # Groups lessons into courses
    order_index = Column(Integer, default=0)
    prerequisites = Column(JSON)                  # List of required lesson IDs
    
    # Content Details
    estimated_duration_minutes = Column(Integer, default=15)
    learning_objectives = Column(JSON)            # List of learning goals
    key_concepts = Column(JSON)                   # List of key concepts
    
    # Interactive Elements
    quiz_questions = Column(JSON)                 # Quiz questions if applicable
    simulation_config = Column(JSON)              # Simulation parameters
    interactive_elements = Column(JSON)           # Interactive content config
    
    # Rewards
    completion_reward_gems = Column(Float, default=50.0)
    mastery_bonus_gems = Column(Float, default=25.0)
    unlock_items = Column(JSON)                   # Items unlocked on completion
    
    # Media and Resources
    video_url = Column(String)
    external_links = Column(JSON)                 # Helpful external resources
    downloadable_resources = Column(JSON)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserLessonProgress(Base):
    """Tracks user progress through lessons."""
    __tablename__ = "user_lesson_progress"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    lesson_id = Column(String, nullable=False, index=True)
    
    # Progress Tracking
    status = Column(String, default=UserProgress.NOT_STARTED.value)
    progress_percentage = Column(Float, default=0.0)
    quiz_score = Column(Float, default=0.0)       # Quiz score (0-100)
    attempts = Column(Integer, default=0)
    
    # Time Tracking
    time_spent_minutes = Column(Float, default=0.0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    # Performance Data
    quiz_answers = Column(JSON)                   # User's quiz answers
    simulation_results = Column(JSON)             # Simulation performance
    notes = Column(Text)                          # User's personal notes
    
    # Rewards Claimed
    completion_reward_claimed = Column(Boolean, default=False)
    mastery_bonus_claimed = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TradingStrategy(Base):
    """Trading strategy templates and guides."""
    __tablename__ = "trading_strategies"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Strategy Info
    name = Column(String, nullable=False)
    description = Column(Text)
    strategy_type = Column(String, nullable=False)  # SCALPING, SWING, HODL, etc.
    risk_level = Column(String, nullable=False)     # LOW, MEDIUM, HIGH
    time_horizon = Column(String, nullable=False)   # SHORT, MEDIUM, LONG
    
    # Strategy Details
    entry_conditions = Column(JSON)               # Conditions for entering trades
    exit_conditions = Column(JSON)                # Conditions for exiting trades
    risk_management = Column(JSON)                # Risk management rules
    position_sizing = Column(JSON)                # Position sizing guidelines
    
    # Performance Metrics
    historical_performance = Column(JSON)         # Backtesting results
    recommended_cryptos = Column(JSON)            # Best cryptos for this strategy
    success_rate = Column(Float)                  # Historical success rate
    average_return = Column(Float)                # Average return percentage
    
    # Educational Content
    tutorial_content = Column(Text)
    video_guides = Column(JSON)
    case_studies = Column(JSON)
    
    # Requirements
    required_knowledge_level = Column(String, default=LessonDifficulty.BEGINNER.value)
    minimum_capital_gems = Column(Float, default=1000.0)
    required_lessons = Column(JSON)               # Prerequisite lessons
    
    # Status
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SimulationSession(Base):
    """Practice trading simulation sessions."""
    __tablename__ = "simulation_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    
    # Simulation Config
    simulation_type = Column(String, nullable=False)  # PAPER_TRADING, STRATEGY_TEST, SCENARIO
    strategy_id = Column(String)                      # If testing a specific strategy
    scenario_name = Column(String)                    # Predefined market scenario
    
    # Initial Conditions
    starting_balance_gems = Column(Float, default=10000.0)
    allowed_cryptos = Column(JSON)                    # List of tradeable cryptos
    simulation_speed = Column(Float, default=1.0)     # Speed multiplier
    duration_days = Column(Integer, default=30)       # Simulation duration
    
    # Current State
    current_balance_gems = Column(Float)
    current_portfolio_value = Column(Float)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    
    # Performance Metrics
    total_return_percentage = Column(Float, default=0.0)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float, default=0.0)
    profit_factor = Column(Float)
    
    # Status and Timing
    status = Column(String, default="ACTIVE")         # ACTIVE, COMPLETED, PAUSED
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    
    # Settings
    enable_margin = Column(Boolean, default=False)
    risk_management_enabled = Column(Boolean, default=True)
    educational_hints = Column(Boolean, default=True)
    
    # Results
    final_report = Column(JSON)                       # Detailed performance report
    lessons_learned = Column(JSON)                    # AI-generated insights
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LearningSystem:
    """Manages the educational content and user learning progress."""
    
    def __init__(self):
        self.lesson_categories = [
            "Blockchain Fundamentals", "Cryptocurrency Basics", "Trading Fundamentals",
            "Technical Analysis", "Risk Management", "Market Psychology", 
            "DeFi Concepts", "Portfolio Management", "Advanced Strategies"
        ]
        self.default_lessons = self._get_default_lessons()
    
    def _get_default_lessons(self) -> List[Dict[str, Any]]:
        """Get default lesson content."""
        return [
            {
                "title": "What is Cryptocurrency?",
                "description": "Learn the basics of digital currencies and blockchain technology",
                "content": """
# What is Cryptocurrency?

Cryptocurrency is a digital or virtual currency secured by cryptography, making it nearly impossible to counterfeit or double-spend. Unlike traditional currencies, cryptocurrencies operate on decentralized networks based on blockchain technology.

## Key Characteristics:
- **Decentralized**: No central authority controls the currency
- **Secure**: Protected by advanced cryptography
- **Transparent**: All transactions are recorded on a public ledger
- **Global**: Can be sent anywhere in the world instantly
- **Limited Supply**: Most cryptocurrencies have a fixed maximum supply

## Popular Cryptocurrencies:
- **Bitcoin (BTC)**: The first and most well-known cryptocurrency
- **Ethereum (ETH)**: Platform for smart contracts and DeFi applications
- **Binance Coin (BNB)**: Exchange token with multiple utilities
- **Solana (SOL)**: High-speed blockchain for decentralized apps

## Why Use Cryptocurrency?
- Lower transaction fees compared to traditional banking
- Financial inclusion for unbanked populations
- Protection against inflation (limited supply)
- Investment opportunities and portfolio diversification
                """,
                "lesson_type": LessonType.TUTORIAL.value,
                "difficulty": LessonDifficulty.BEGINNER.value,
                "category": "Cryptocurrency Basics",
                "course_id": "crypto-fundamentals",
                "order_index": 1,
                "estimated_duration_minutes": 10,
                "learning_objectives": [
                    "Understand what cryptocurrency is",
                    "Learn key characteristics of crypto",
                    "Identify major cryptocurrencies",
                    "Understand benefits of crypto"
                ],
                "key_concepts": ["Blockchain", "Decentralization", "Cryptography", "Digital Currency"],
                "completion_reward_gems": 100.0,
                "quiz_questions": [
                    {
                        "question": "What makes cryptocurrency secure?",
                        "options": ["Government backing", "Cryptography", "Bank guarantees", "Gold reserves"],
                        "correct_answer": 1,
                        "explanation": "Cryptography provides the security that makes cryptocurrencies nearly impossible to counterfeit."
                    },
                    {
                        "question": "What is the first cryptocurrency?",
                        "options": ["Ethereum", "Bitcoin", "Litecoin", "Ripple"],
                        "correct_answer": 1,
                        "explanation": "Bitcoin was the first cryptocurrency, created by Satoshi Nakamoto in 2009."
                    }
                ]
            },
            {
                "title": "Understanding Market Orders vs Limit Orders",
                "description": "Learn the difference between market and limit orders in trading",
                "content": """
# Market Orders vs Limit Orders

Understanding order types is crucial for successful trading. Let's explore the two main types of orders.

## Market Orders
A market order is an instruction to buy or sell immediately at the current market price.

### Pros:
- **Immediate execution**: Your order fills right away
- **Guaranteed execution**: You will definitely get your trade
- **Simple**: Easy to understand and use

### Cons:
- **Price uncertainty**: You might pay more than expected
- **Slippage**: Price can move between clicking and execution
- **Higher costs**: Often worse prices due to bid-ask spread

### When to Use:
- When you need to enter/exit immediately
- In highly liquid markets
- For small trade sizes

## Limit Orders
A limit order sets a specific price at which you want to buy or sell.

### Pros:
- **Price control**: You set your exact price
- **Better prices**: Often get better execution
- **No slippage**: Price is guaranteed

### Cons:
- **May not fill**: Order might not execute
- **Timing uncertainty**: Don't know when it will fill
- **Requires monitoring**: Need to watch and adjust

### When to Use:
- When you have a target price
- For larger trade sizes
- In volatile markets
- When you can wait for better prices

## Order Examples

### Market Order Example:
"Buy 1 BTC immediately at current market price (~$45,000)"
- ✅ Fills instantly
- ❓ Might pay $45,100 due to slippage

### Limit Order Example:
"Buy 1 BTC only if price drops to $44,000"
- ✅ Better price if it fills
- ❓ Might never fill if price doesn't drop
                """,
                "lesson_type": LessonType.TUTORIAL.value,
                "difficulty": LessonDifficulty.BEGINNER.value,
                "category": "Trading Fundamentals",
                "course_id": "trading-basics",
                "order_index": 2,
                "estimated_duration_minutes": 15,
                "learning_objectives": [
                    "Understand market vs limit orders",
                    "Know when to use each order type",
                    "Understand trade-offs of each type",
                    "Apply order knowledge in practice"
                ],
                "key_concepts": ["Market Orders", "Limit Orders", "Slippage", "Liquidity"],
                "completion_reward_gems": 150.0,
                "interactive_elements": {
                    "order_simulator": True,
                    "price_impact_calculator": True
                }
            },
            {
                "title": "Risk Management Fundamentals",
                "description": "Learn essential risk management techniques for crypto trading",
                "content": """
# Risk Management Fundamentals

Risk management is the most important skill for long-term trading success. Even the best traders lose money on individual trades - what matters is managing those losses.

## The Golden Rules

### 1. Never Risk More Than You Can Afford to Lose
- Only invest money you won't need for living expenses
- Consider crypto investments as high-risk speculation
- Start small and gradually increase position sizes

### 2. Position Sizing
Determine how much to risk per trade:
- **Conservative**: 1-2% of portfolio per trade
- **Moderate**: 3-5% of portfolio per trade
- **Aggressive**: 5-10% of portfolio per trade (not recommended)

### 3. Stop Losses
Always set stop losses to limit downside:
- **Percentage-based**: Exit if price drops X%
- **Technical**: Exit at support/resistance levels
- **Time-based**: Exit after a certain time period

### 4. Diversification
Don't put all eggs in one basket:
- **Across cryptocurrencies**: Bitcoin, Ethereum, altcoins
- **Across strategies**: Long-term holds, short-term trades
- **Across time**: Dollar-cost averaging

## Risk-Reward Ratios

### Minimum 1:2 Ratio
For every $1 you risk, aim to make $2
- Risk: $100 (stop loss)
- Reward: $200 (take profit)
- This allows you to be wrong 50% of the time and still profit

### Example Trade Setup:
- Buy BTC at $50,000
- Stop loss at $48,000 (4% risk = $2,000)
- Take profit at $54,000 (8% gain = $4,000)
- Risk-reward ratio: 1:2

## Common Risk Management Mistakes

### 1. Moving Stop Losses
- Set your stop and stick to it
- Don't move stops further away when losing
- Only move stops closer to secure profits

### 2. Revenge Trading
- Don't try to immediately win back losses
- Take breaks after big losses
- Stick to your predetermined position sizes

### 3. FOMO (Fear of Missing Out)
- Don't chase pumping prices
- Wait for good setups
- There's always another opportunity

## Portfolio Heat Map
Track your total portfolio risk:
- Sum all open position risks
- Never exceed 20-30% total portfolio risk
- Reduce position sizes if approaching limits
                """,
                "lesson_type": LessonType.TUTORIAL.value,
                "difficulty": LessonDifficulty.INTERMEDIATE.value,
                "category": "Risk Management",
                "course_id": "risk-management",
                "order_index": 1,
                "estimated_duration_minutes": 20,
                "learning_objectives": [
                    "Master position sizing techniques",
                    "Understand stop loss strategies",
                    "Learn risk-reward ratios",
                    "Avoid common risk mistakes"
                ],
                "key_concepts": ["Position Sizing", "Stop Loss", "Risk-Reward", "Diversification"],
                "completion_reward_gems": 200.0,
                "quiz_questions": [
                    {
                        "question": "What's a good risk-reward ratio for beginners?",
                        "options": ["1:1", "1:2", "2:1", "1:0.5"],
                        "correct_answer": 1,
                        "explanation": "A 1:2 risk-reward ratio means you aim to make twice what you risk, allowing for a 50% win rate while staying profitable."
                    }
                ]
            },
            {
                "title": "Technical Analysis: Support and Resistance",
                "description": "Learn to identify key price levels that influence crypto markets",
                "content": """
# Support and Resistance Levels

Support and resistance are the foundation of technical analysis. These price levels help predict where prices might reverse or continue trending.

## What is Support?

Support is a price level where buying pressure is strong enough to prevent further decline.

### Characteristics:
- Price tends to "bounce" off support levels
- Buyers step in when price reaches support
- Acts as a "floor" for the price
- The more times support holds, the stronger it becomes

### How to Identify Support:
1. **Previous lows**: Look for historical low points
2. **Round numbers**: $50,000, $40,000 for Bitcoin
3. **Moving averages**: 50-day, 200-day averages
4. **Trend lines**: Connect multiple low points

## What is Resistance?

Resistance is a price level where selling pressure prevents further upward movement.

### Characteristics:
- Price tends to "bounce down" from resistance
- Sellers become active at resistance levels
- Acts as a "ceiling" for the price
- Previous highs often become new resistance

### How to Identify Resistance:
1. **Previous highs**: Look for historical peak points
2. **Round numbers**: Psychological price levels
3. **Moving averages**: Can act as dynamic resistance
4. **Volume**: High volume at a level suggests strong resistance

## Support Becomes Resistance (and Vice Versa)

This is a key concept in technical analysis:

### Broken Support → New Resistance
When price breaks below support:
- Previous support level becomes new resistance
- Failed bounces off old support confirm the break
- Sellers often wait at this level to exit

### Broken Resistance → New Support
When price breaks above resistance:
- Previous resistance becomes new support
- Successful tests of old resistance confirm the break
- Buyers step in at this level

## Trading Strategies

### 1. Buy at Support
- Enter long positions near support levels
- Set stop loss below support
- Target next resistance level

### 2. Sell at Resistance
- Enter short positions near resistance
- Set stop loss above resistance  
- Target next support level

### 3. Breakout Trading
- Buy when price breaks above resistance
- Sell when price breaks below support
- Use volume to confirm breakouts

## Strength of Levels

### Factors that make S/R stronger:
- **Number of touches**: More tests = stronger level
- **Volume**: High volume at level shows conviction
- **Time frame**: Daily/weekly levels > hourly levels
- **Round numbers**: Psychological significance
- **Confluence**: Multiple indicators at same level

## Example: Bitcoin Support/Resistance

### Historical Bitcoin Levels:
- **$30,000**: Major support in 2021 bear market
- **$40,000**: Strong resistance turned support
- **$50,000**: Round number psychological level
- **$65,000**: Previous all-time high resistance

### Trading the Levels:
1. Watch for bounces at $40,000 support
2. Look for breakouts above $50,000 resistance
3. Use these levels for entry/exit decisions
4. Set stops beyond the levels with buffer
                """,
                "lesson_type": LessonType.TUTORIAL.value,
                "difficulty": LessonDifficulty.INTERMEDIATE.value,
                "category": "Technical Analysis",
                "course_id": "technical-analysis",
                "order_index": 1,
                "estimated_duration_minutes": 25,
                "learning_objectives": [
                    "Identify support and resistance levels",
                    "Understand role reversal concept",
                    "Apply S/R in trading decisions",
                    "Evaluate strength of price levels"
                ],
                "key_concepts": ["Support", "Resistance", "Role Reversal", "Breakouts"],
                "completion_reward_gems": 250.0,
                "interactive_elements": {
                    "chart_drawing_tool": True,
                    "level_identification_quiz": True
                }
            }
        ]
    
    async def initialize_default_content(self) -> bool:
        """Initialize the system with default educational content."""
        try:
            async with get_db_session() as session:
                # Check if content already exists
                existing_count = await session.execute(select(func.count(EducationLesson.id)))
                if existing_count.scalar() > 0:
                    logger.info("Educational content already exists")
                    return True
                
                # Add default lessons
                for lesson_data in self.default_lessons:
                    lesson = EducationLesson(**lesson_data)
                    session.add(lesson)
                
                await session.commit()
                logger.info(f"Initialized {len(self.default_lessons)} educational lessons")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize educational content: {e}")
            return False
    
    async def get_user_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Get user's learning dashboard with progress and recommendations."""
        try:
            async with get_db_session() as session:
                # Get user's lesson progress
                progress_query = select(UserLessonProgress).where(
                    UserLessonProgress.user_id == user_id
                )
                progress_result = await session.execute(progress_query)
                user_progress = progress_result.scalars().all()
                
                # Get available lessons
                lessons_query = select(EducationLesson).where(
                    EducationLesson.is_active == True
                ).order_by(EducationLesson.course_id, EducationLesson.order_index)
                lessons_result = await session.execute(lessons_query)
                all_lessons = lessons_result.scalars().all()
                
                # Calculate statistics
                total_lessons = len(all_lessons)
                completed_lessons = len([p for p in user_progress if p.status == UserProgress.COMPLETED.value])
                in_progress_lessons = len([p for p in user_progress if p.status == UserProgress.IN_PROGRESS.value])
                
                # Group lessons by category
                lessons_by_category = {}
                for lesson in all_lessons:
                    if lesson.category not in lessons_by_category:
                        lessons_by_category[lesson.category] = []
                    
                    # Find user progress for this lesson
                    lesson_progress = next((p for p in user_progress if p.lesson_id == lesson.id), None)
                    
                    lesson_data = {
                        "lesson_id": lesson.id,
                        "title": lesson.title,
                        "description": lesson.description,
                        "difficulty": lesson.difficulty,
                        "estimated_duration": lesson.estimated_duration_minutes,
                        "reward_gems": lesson.completion_reward_gems,
                        "status": lesson_progress.status if lesson_progress else UserProgress.NOT_STARTED.value,
                        "progress_percentage": lesson_progress.progress_percentage if lesson_progress else 0.0,
                        "quiz_score": lesson_progress.quiz_score if lesson_progress else None
                    }
                    lessons_by_category[lesson.category].append(lesson_data)
                
                # Recommend next lessons
                next_lessons = await self._get_recommended_lessons(session, user_id, user_progress, all_lessons)
                
                # Calculate learning streak
                learning_streak = await self._calculate_learning_streak(session, user_id)
                
                return {
                    "user_id": user_id,
                    "learning_stats": {
                        "total_lessons": total_lessons,
                        "completed_lessons": completed_lessons,
                        "in_progress_lessons": in_progress_lessons,
                        "completion_percentage": (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0,
                        "learning_streak_days": learning_streak,
                        "total_gems_earned": sum(p.completion_reward_claimed * 100 for p in user_progress),  # Estimate
                    },
                    "lessons_by_category": lessons_by_category,
                    "recommended_next_lessons": next_lessons,
                    "achievements": await self._get_learning_achievements(session, user_id, user_progress),
                    "last_updated": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get user learning dashboard: {e}")
            return {}
    
    async def _get_recommended_lessons(
        self, 
        session: AsyncSession, 
        user_id: str, 
        user_progress: List[UserLessonProgress], 
        all_lessons: List[EducationLesson]
    ) -> List[Dict[str, Any]]:
        """Get personalized lesson recommendations."""
        completed_lesson_ids = {p.lesson_id for p in user_progress if p.status == UserProgress.COMPLETED.value}
        in_progress_lesson_ids = {p.lesson_id for p in user_progress if p.status == UserProgress.IN_PROGRESS.value}
        
        recommendations = []
        
        for lesson in all_lessons:
            # Skip if already completed or in progress
            if lesson.id in completed_lesson_ids or lesson.id in in_progress_lesson_ids:
                continue
            
            # Check prerequisites
            prerequisites = lesson.prerequisites or []
            if all(prereq_id in completed_lesson_ids for prereq_id in prerequisites):
                recommendations.append({
                    "lesson_id": lesson.id,
                    "title": lesson.title,
                    "description": lesson.description,
                    "difficulty": lesson.difficulty,
                    "category": lesson.category,
                    "estimated_duration": lesson.estimated_duration_minutes,
                    "reward_gems": lesson.completion_reward_gems,
                    "reason": "Prerequisites completed" if prerequisites else "Good starting point"
                })
        
        # Sort by difficulty and order
        recommendations.sort(key=lambda x: (
            LessonDifficulty[x["difficulty"]].value,
            x["estimated_duration"]
        ))
        
        return recommendations[:5]  # Return top 5 recommendations
    
    async def _calculate_learning_streak(self, session: AsyncSession, user_id: str) -> int:
        """Calculate user's current learning streak in days."""
        try:
            # Get recent lesson completions
            recent_progress = await session.execute(
                select(UserLessonProgress).where(
                    and_(
                        UserLessonProgress.user_id == user_id,
                        UserLessonProgress.status == UserProgress.COMPLETED.value,
                        UserLessonProgress.completed_at.isnot(None)
                    )
                ).order_by(UserLessonProgress.completed_at.desc())
            )
            completions = recent_progress.scalars().all()
            
            if not completions:
                return 0
            
            # Calculate consecutive days with completions
            streak = 0
            current_date = datetime.utcnow().date()
            
            completion_dates = set()
            for completion in completions:
                completion_dates.add(completion.completed_at.date())
            
            # Check consecutive days backwards from today
            while current_date in completion_dates:
                streak += 1
                current_date -= timedelta(days=1)
            
            return streak
            
        except Exception as e:
            logger.error(f"Failed to calculate learning streak: {e}")
            return 0
    
    async def _get_learning_achievements(
        self, 
        session: AsyncSession, 
        user_id: str, 
        user_progress: List[UserLessonProgress]
    ) -> List[Dict[str, Any]]:
        """Get learning-related achievements."""
        achievements = []
        
        completed_count = len([p for p in user_progress if p.status == UserProgress.COMPLETED.value])
        avg_quiz_score = sum(p.quiz_score or 0 for p in user_progress) / max(len(user_progress), 1)
        
        # Completion achievements
        if completed_count >= 1:
            achievements.append({"name": "First Steps", "description": "Completed your first lesson"})
        if completed_count >= 5:
            achievements.append({"name": "Eager Learner", "description": "Completed 5 lessons"})
        if completed_count >= 10:
            achievements.append({"name": "Knowledge Seeker", "description": "Completed 10 lessons"})
        if completed_count >= 25:
            achievements.append({"name": "Crypto Scholar", "description": "Completed 25 lessons"})
        
        # Performance achievements
        if avg_quiz_score >= 90:
            achievements.append({"name": "Quiz Master", "description": "Average quiz score above 90%"})
        if avg_quiz_score >= 95:
            achievements.append({"name": "Perfect Student", "description": "Average quiz score above 95%"})
        
        return achievements
    
    async def start_lesson(self, user_id: str, lesson_id: str) -> Dict[str, Any]:
        """Start a lesson for a user."""
        try:
            async with get_db_session() as session:
                # Get lesson
                lesson_query = select(EducationLesson).where(EducationLesson.id == lesson_id)
                lesson_result = await session.execute(lesson_query)
                lesson = lesson_result.scalar_one_or_none()
                
                if not lesson:
                    raise ValueError("Lesson not found")
                
                # Check prerequisites
                if lesson.prerequisites:
                    completed_prerequisites = await session.execute(
                        select(UserLessonProgress.lesson_id).where(
                            and_(
                                UserLessonProgress.user_id == user_id,
                                UserLessonProgress.lesson_id.in_(lesson.prerequisites),
                                UserLessonProgress.status == UserProgress.COMPLETED.value
                            )
                        )
                    )
                    completed_ids = {row[0] for row in completed_prerequisites}
                    
                    if not all(prereq in completed_ids for prereq in lesson.prerequisites):
                        raise ValueError("Prerequisites not completed")
                
                # Get or create progress record
                progress_query = select(UserLessonProgress).where(
                    and_(
                        UserLessonProgress.user_id == user_id,
                        UserLessonProgress.lesson_id == lesson_id
                    )
                )
                progress_result = await session.execute(progress_query)
                progress = progress_result.scalar_one_or_none()
                
                if not progress:
                    progress = UserLessonProgress(
                        user_id=user_id,
                        lesson_id=lesson_id,
                        started_at=datetime.utcnow()
                    )
                    session.add(progress)
                
                progress.status = UserProgress.IN_PROGRESS.value
                progress.last_accessed = datetime.utcnow()
                progress.attempts += 1
                
                await session.commit()
                
                return {
                    "lesson_id": lesson.id,
                    "title": lesson.title,
                    "content": lesson.content,
                    "lesson_type": lesson.lesson_type,
                    "difficulty": lesson.difficulty,
                    "learning_objectives": lesson.learning_objectives,
                    "key_concepts": lesson.key_concepts,
                    "quiz_questions": lesson.quiz_questions,
                    "interactive_elements": lesson.interactive_elements,
                    "progress_id": progress.id,
                    "started_at": progress.started_at.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to start lesson: {e}")
            raise
    
    async def complete_lesson_quiz(
        self, 
        user_id: str, 
        lesson_id: str, 
        answers: List[int],
        time_spent: float = 0.0
    ) -> Dict[str, Any]:
        """Complete a lesson quiz and calculate score."""
        try:
            async with get_db_session() as session:
                # Get lesson and progress
                lesson = await session.get(EducationLesson, lesson_id)
                if not lesson:
                    raise ValueError("Lesson not found")
                
                progress_query = select(UserLessonProgress).where(
                    and_(
                        UserLessonProgress.user_id == user_id,
                        UserLessonProgress.lesson_id == lesson_id
                    )
                )
                progress_result = await session.execute(progress_query)
                progress = progress_result.scalar_one_or_none()
                
                if not progress:
                    raise ValueError("Lesson not started")
                
                # Calculate quiz score
                quiz_questions = lesson.quiz_questions or []
                if not quiz_questions:
                    # No quiz, mark as completed
                    score = 100.0
                else:
                    correct_answers = 0
                    for i, user_answer in enumerate(answers):
                        if i < len(quiz_questions):
                            correct_answer = quiz_questions[i].get("correct_answer", 0)
                            if user_answer == correct_answer:
                                correct_answers += 1
                    
                    score = (correct_answers / len(quiz_questions)) * 100
                
                # Update progress
                progress.quiz_score = score
                progress.quiz_answers = answers
                progress.time_spent_minutes += time_spent
                progress.progress_percentage = 100.0
                progress.last_accessed = datetime.utcnow()
                
                # Mark as completed if score is high enough
                passing_score = 70.0  # 70% passing grade
                if score >= passing_score:
                    progress.status = UserProgress.COMPLETED.value
                    progress.completed_at = datetime.utcnow()
                    
                    # Award completion rewards
                    if not progress.completion_reward_claimed:
                        await virtual_economy_engine.update_wallet_balance(
                            session, user_id, "GEM_COINS", lesson.completion_reward_gems,
                            f"Completed lesson: {lesson.title}"
                        )
                        progress.completion_reward_claimed = True
                    
                    # Award mastery bonus for high scores
                    if score >= 95.0 and not progress.mastery_bonus_claimed:
                        await virtual_economy_engine.update_wallet_balance(
                            session, user_id, "GEM_COINS", lesson.mastery_bonus_gems,
                            f"Mastery bonus: {lesson.title}"
                        )
                        progress.mastery_bonus_claimed = True
                
                await session.commit()
                
                return {
                    "quiz_score": score,
                    "passing_score": passing_score,
                    "passed": score >= passing_score,
                    "correct_answers": correct_answers if quiz_questions else len(answers),
                    "total_questions": len(quiz_questions),
                    "gems_awarded": lesson.completion_reward_gems if score >= passing_score else 0,
                    "mastery_bonus": lesson.mastery_bonus_gems if score >= 95.0 else 0,
                    "status": progress.status,
                    "feedback": self._generate_quiz_feedback(score, quiz_questions, answers)
                }
                
        except Exception as e:
            logger.error(f"Failed to complete lesson quiz: {e}")
            raise
    
    def _generate_quiz_feedback(
        self, 
        score: float, 
        questions: List[Dict], 
        answers: List[int]
    ) -> Dict[str, Any]:
        """Generate personalized feedback based on quiz performance."""
        feedback = {
            "overall": "",
            "question_feedback": [],
            "recommendations": []
        }
        
        if score >= 95:
            feedback["overall"] = "Excellent work! You've mastered this material."
        elif score >= 85:
            feedback["overall"] = "Great job! You have a solid understanding."
        elif score >= 70:
            feedback["overall"] = "Good work! You've passed the lesson."
        else:
            feedback["overall"] = "Keep studying! Review the material and try again."
        
        # Question-specific feedback
        for i, (question, user_answer) in enumerate(zip(questions, answers)):
            correct = user_answer == question.get("correct_answer", 0)
            feedback["question_feedback"].append({
                "question_index": i,
                "correct": correct,
                "explanation": question.get("explanation", ""),
                "your_answer": question["options"][user_answer] if user_answer < len(question["options"]) else "Invalid",
                "correct_answer": question["options"][question.get("correct_answer", 0)]
            })
        
        # Recommendations based on performance
        if score < 70:
            feedback["recommendations"] = [
                "Review the lesson content carefully",
                "Take notes on key concepts",
                "Try the quiz again after studying"
            ]
        elif score < 85:
            feedback["recommendations"] = [
                "Great progress! Review any missed questions",
                "Consider exploring advanced topics in this area"
            ]
        
        return feedback


# Global instance
learning_system = LearningSystem()