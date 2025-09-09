"""
Learn-to-Earn Educational System
Balanced reward system designed to avoid the 45% engagement drop from motivation crowding.
Uses progressive disclosure and autonomy-preserving mechanics.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from dataclasses import dataclass
from enum import Enum
import json
import random

from database import get_db_session, User, VirtualWallet, Achievement, UserAchievement
from logger import logger

class DifficultyLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class ModuleType(Enum):
    INTERACTIVE_LESSON = "interactive_lesson"
    MARKET_SIMULATION = "market_simulation"
    CASE_STUDY = "case_study"
    LIVE_ANALYSIS = "live_analysis"
    PEER_DISCUSSION = "peer_discussion"

@dataclass
class LearningModule:
    """Educational module with gamified progression"""
    id: str
    title: str
    description: str
    module_type: ModuleType
    difficulty: DifficultyLevel
    estimated_time: int  # minutes
    prerequisites: List[str]
    learning_objectives: List[str]
    content_sections: List[Dict[str, Any]]
    quiz_questions: List[Dict[str, Any]]
    practical_exercises: List[Dict[str, Any]]
    completion_criteria: Dict[str, Any]
    base_reward: int  # GEM coins
    mastery_bonus: int
    time_bonus_threshold: int  # minutes for time bonus

@dataclass
class UserProgress:
    """User's learning progress and achievements"""
    user_id: str
    module_id: str
    started_at: datetime
    last_accessed: datetime
    completion_percentage: float
    quiz_scores: List[float]
    time_spent: int  # minutes
    completed: bool
    mastery_achieved: bool
    attempts: int

class LearnToEarnEngine:
    """
    Educational gamification engine that preserves intrinsic motivation.
    
    Key Design Principles from 2024 Research:
    1. Progressive reward disclosure (don't lead with rewards)
    2. Mastery-based progression (competence builds motivation)
    3. Choice and autonomy (users pick learning paths)
    4. Social learning elements (community engagement)
    5. Real-world application (connect to actual trading)
    """
    
    def __init__(self):
        self.modules = self._initialize_learning_modules()
        self.learning_paths = self._create_learning_paths()
        
    def _initialize_learning_modules(self) -> Dict[str, LearningModule]:
        """Initialize comprehensive crypto education modules"""
        modules = {}
        
        # BEGINNER MODULES
        modules['crypto_basics'] = LearningModule(
            id='crypto_basics',
            title='Cryptocurrency Fundamentals',
            description='Understanding blockchain technology, digital currencies, and basic concepts.',
            module_type=ModuleType.INTERACTIVE_LESSON,
            difficulty=DifficultyLevel.BEGINNER,
            estimated_time=30,
            prerequisites=[],
            learning_objectives=[
                'Understand what cryptocurrency is and how it works',
                'Learn the difference between coins and tokens',
                'Understand basic blockchain concepts',
                'Recognize major cryptocurrencies and their use cases'
            ],
            content_sections=[
                {'type': 'video', 'title': 'What is Cryptocurrency?', 'duration': 8},
                {'type': 'interactive', 'title': 'Blockchain Visualization', 'activity': 'drag_and_drop'},
                {'type': 'reading', 'title': 'Major Cryptocurrencies Overview', 'words': 800},
                {'type': 'simulation', 'title': 'Send Your First Transaction', 'scenario': 'testnet_transfer'}
            ],
            quiz_questions=[
                {
                    'question': 'What makes cryptocurrency decentralized?',
                    'options': ['Banks control it', 'Government regulates it', 'Distributed network validates it', 'Companies manage it'],
                    'correct': 2,
                    'explanation': 'Cryptocurrency operates on a distributed network where multiple participants validate transactions, eliminating central control.'
                },
                {
                    'question': 'Which is the key innovation of blockchain?',
                    'options': ['Digital money', 'Immutable record keeping', 'Online payments', 'Virtual wallets'],
                    'correct': 1,
                    'explanation': 'Blockchain\'s key innovation is creating an immutable, transparent ledger that cannot be altered once records are added.'
                }
            ],
            practical_exercises=[
                {
                    'title': 'Set up a test wallet',
                    'instructions': 'Create a testnet wallet and receive test coins',
                    'verification': 'wallet_creation',
                    'reward_multiplier': 1.2
                }
            ],
            completion_criteria={'quiz_score': 80, 'time_spent': 20, 'exercises_completed': 1},
            base_reward=500,
            mastery_bonus=200,
            time_bonus_threshold=25
        )
        
        modules['wallet_security'] = LearningModule(
            id='wallet_security',
            title='Crypto Wallet Security',
            description='Essential security practices for protecting your cryptocurrency.',
            module_type=ModuleType.INTERACTIVE_LESSON,
            difficulty=DifficultyLevel.BEGINNER,
            estimated_time=25,
            prerequisites=['crypto_basics'],
            learning_objectives=[
                'Learn different types of crypto wallets',
                'Understand private key management',
                'Master security best practices',
                'Recognize common scams and threats'
            ],
            content_sections=[
                {'type': 'interactive', 'title': 'Wallet Types Comparison', 'activity': 'comparison_table'},
                {'type': 'video', 'title': 'Private Key Security', 'duration': 10},
                {'type': 'case_study', 'title': 'Common Security Mistakes', 'examples': 5},
                {'type': 'checklist', 'title': 'Security Checklist', 'items': 15}
            ],
            quiz_questions=[
                {
                    'question': 'What should you NEVER share with anyone?',
                    'options': ['Public key', 'Wallet address', 'Private key', 'Transaction hash'],
                    'correct': 2,
                    'explanation': 'Your private key is like the password to your funds. Never share it with anyone, legitimate services will never ask for it.'
                }
            ],
            practical_exercises=[
                {
                    'title': 'Security audit simulation',
                    'instructions': 'Complete a security checklist for a sample wallet setup',
                    'verification': 'security_checklist',
                    'reward_multiplier': 1.1
                }
            ],
            completion_criteria={'quiz_score': 85, 'time_spent': 18, 'exercises_completed': 1},
            base_reward=400,
            mastery_bonus=150,
            time_bonus_threshold=22
        )
        
        # INTERMEDIATE MODULES
        modules['technical_analysis'] = LearningModule(
            id='technical_analysis',
            title='Technical Analysis Fundamentals',
            description='Learn to read crypto charts and identify trading patterns.',
            module_type=ModuleType.MARKET_SIMULATION,
            difficulty=DifficultyLevel.INTERMEDIATE,
            estimated_time=45,
            prerequisites=['crypto_basics', 'wallet_security'],
            learning_objectives=[
                'Read and interpret price charts',
                'Identify support and resistance levels',
                'Understand common chart patterns',
                'Use technical indicators effectively'
            ],
            content_sections=[
                {'type': 'interactive_chart', 'title': 'Chart Reading Basics', 'activity': 'identify_patterns'},
                {'type': 'video', 'title': 'Support and Resistance', 'duration': 15},
                {'type': 'simulation', 'title': 'Pattern Recognition Game', 'scenarios': 20},
                {'type': 'live_data', 'title': 'Real-Time Analysis Practice', 'markets': ['BTC', 'ETH', 'ADA']}
            ],
            quiz_questions=[
                {
                    'question': 'What does a support level indicate?',
                    'options': ['Price ceiling', 'Price floor', 'Volume spike', 'Market cap'],
                    'correct': 1,
                    'explanation': 'A support level acts as a price floor where buying interest typically emerges, preventing further decline.'
                }
            ],
            practical_exercises=[
                {
                    'title': 'Live chart analysis',
                    'instructions': 'Analyze 3 different crypto charts and identify key levels',
                    'verification': 'chart_analysis',
                    'reward_multiplier': 1.5
                },
                {
                    'title': 'Pattern prediction challenge',
                    'instructions': 'Predict price movement based on identified patterns',
                    'verification': 'prediction_accuracy',
                    'reward_multiplier': 2.0
                }
            ],
            completion_criteria={'quiz_score': 75, 'time_spent': 35, 'exercises_completed': 2},
            base_reward=800,
            mastery_bonus=400,
            time_bonus_threshold=40
        )
        
        # ADVANCED MODULES  
        modules['defi_strategies'] = LearningModule(
            id='defi_strategies',
            title='DeFi Investment Strategies',
            description='Master decentralized finance protocols and yield optimization.',
            module_type=ModuleType.CASE_STUDY,
            difficulty=DifficultyLevel.ADVANCED,
            estimated_time=60,
            prerequisites=['technical_analysis'],
            learning_objectives=[
                'Understand DeFi protocol mechanics',
                'Calculate and compare yield opportunities',
                'Assess smart contract risks',
                'Build diversified DeFi strategies'
            ],
            content_sections=[
                {'type': 'protocol_deep_dive', 'title': 'Major DeFi Protocols', 'protocols': ['Uniswap', 'Aave', 'Compound']},
                {'type': 'calculator', 'title': 'Yield Calculation Workshop', 'activity': 'yield_modeling'},
                {'type': 'risk_assessment', 'title': 'Smart Contract Risk Analysis', 'case_studies': 8},
                {'type': 'strategy_builder', 'title': 'Portfolio Construction', 'tools': 'drag_drop_interface'}
            ],
            quiz_questions=[
                {
                    'question': 'What is impermanent loss?',
                    'options': ['Permanent token loss', 'Temporary price volatility', 'Opportunity cost from price changes', 'Smart contract failure'],
                    'correct': 2,
                    'explanation': 'Impermanent loss occurs when providing liquidity to an AMM, representing the opportunity cost compared to simply holding the tokens.'
                }
            ],
            practical_exercises=[
                {
                    'title': 'DeFi strategy simulation',
                    'instructions': 'Create and backtest a DeFi investment strategy',
                    'verification': 'strategy_performance',
                    'reward_multiplier': 2.5
                }
            ],
            completion_criteria={'quiz_score': 80, 'time_spent': 45, 'exercises_completed': 1},
            base_reward=1500,
            mastery_bonus=800,
            time_bonus_threshold=55
        )
        
        return modules
    
    def _create_learning_paths(self) -> Dict[str, Dict[str, Any]]:
        """Define structured learning paths for different user goals"""
        return {
            'beginner_investor': {
                'title': 'New Crypto Investor Path',
                'description': 'Perfect for those new to cryptocurrency investing',
                'modules': ['crypto_basics', 'wallet_security', 'market_basics', 'portfolio_management'],
                'estimated_time': 180,
                'completion_reward': 3000,
                'badge': 'crypto_novice_graduate'
            },
            'technical_trader': {
                'title': 'Technical Analysis Master Path',
                'description': 'Learn to analyze charts and trade like a pro',
                'modules': ['crypto_basics', 'technical_analysis', 'advanced_patterns', 'risk_management'],
                'estimated_time': 240,
                'completion_reward': 5000,
                'badge': 'chart_master'
            },
            'defi_expert': {
                'title': 'DeFi Specialist Path',
                'description': 'Master decentralized finance protocols and strategies',
                'modules': ['crypto_basics', 'defi_basics', 'defi_strategies', 'yield_optimization'],
                'estimated_time': 300,
                'completion_reward': 8000,
                'badge': 'defi_guru'
            }
        }
    
    async def get_personalized_recommendations(self, user_id: str) -> Dict[str, Any]:
        """
        Recommend learning modules based on user's portfolio and goals.
        This creates AUTONOMY by letting users choose their path.
        """
        try:
            async with get_db_session() as session:
                user = await session.get(User, user_id)
                if not user:
                    return {'success': False, 'error': 'User not found'}
                
                # Get user's completed modules
                user_progress = await self._get_user_progress(user_id)
                completed_modules = [p.module_id for p in user_progress if p.completed]
                
                # Analyze user's portfolio to suggest relevant modules
                portfolio_analysis = await self._analyze_user_portfolio(user_id)
                
                recommendations = []
                
                # Beginner recommendations
                if len(completed_modules) == 0:
                    recommendations.append({
                        'type': 'start_here',
                        'module': self.modules['crypto_basics'],
                        'reason': 'Perfect starting point for crypto education',
                        'urgency': 'high'
                    })
                
                # Portfolio-based recommendations
                if portfolio_analysis.get('has_defi_exposure') and 'defi_strategies' not in completed_modules:
                    recommendations.append({
                        'type': 'portfolio_optimization',
                        'module': self.modules['defi_strategies'], 
                        'reason': 'Optimize your existing DeFi holdings',
                        'urgency': 'medium'
                    })
                
                # Skill gap recommendations
                if 'crypto_basics' in completed_modules and 'technical_analysis' not in completed_modules:
                    recommendations.append({
                        'type': 'skill_building',
                        'module': self.modules['technical_analysis'],
                        'reason': 'Level up your trading skills',
                        'urgency': 'medium'
                    })
                
                # Learning path suggestions
                suggested_paths = self._suggest_learning_paths(completed_modules, portfolio_analysis)
                
                return {
                    'success': True,
                    'recommendations': recommendations,
                    'learning_paths': suggested_paths,
                    'completed_count': len(completed_modules),
                    'total_modules': len(self.modules),
                    'next_milestone': self._get_next_milestone(completed_modules)
                }
                
        except Exception as e:
            logger.error(f"Error getting recommendations for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def start_learning_module(self, user_id: str, module_id: str) -> Dict[str, Any]:
        """
        Start a learning module with motivation-preserving onboarding.
        Key: Don't lead with rewards, lead with curiosity and mastery.
        """
        try:
            if module_id not in self.modules:
                return {'success': False, 'error': 'Module not found'}
            
            module = self.modules[module_id]
            
            # Check prerequisites
            user_progress = await self._get_user_progress(user_id)
            completed_modules = [p.module_id for p in user_progress if p.completed]
            
            missing_prereqs = [prereq for prereq in module.prerequisites if prereq not in completed_modules]
            if missing_prereqs:
                return {
                    'success': False,
                    'error': 'Missing prerequisites',
                    'missing_prerequisites': missing_prereqs
                }
            
            # Create or update user progress
            progress = UserProgress(
                user_id=user_id,
                module_id=module_id,
                started_at=datetime.now(),
                last_accessed=datetime.now(),
                completion_percentage=0,
                quiz_scores=[],
                time_spent=0,
                completed=False,
                mastery_achieved=False,
                attempts=1
            )
            
            # Store progress in database
            await self._save_user_progress(progress)
            
            # Return module content with curiosity-driven introduction
            return {
                'success': True,
                'module': {
                    'id': module.id,
                    'title': module.title,
                    'description': module.description,
                    'learning_objectives': module.learning_objectives,
                    'estimated_time': module.estimated_time,
                    'difficulty': module.difficulty.value,
                    'content_sections': module.content_sections[:2],  # Progressive disclosure
                    'progress_tracking': {
                        'completion_percentage': 0,
                        'current_section': 0,
                        'sections_total': len(module.content_sections)
                    }
                },
                'motivation_message': self._get_motivation_message(module, 'start'),
                'community_stats': await self._get_module_community_stats(module_id)
            }
            
        except Exception as e:
            logger.error(f"Error starting module {module_id} for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def submit_quiz_answer(self, user_id: str, module_id: str, question_id: int, answer: int) -> Dict[str, Any]:
        """
        Process quiz answer with immediate feedback and adaptive difficulty.
        Uses mastery-based progression to maintain intrinsic motivation.
        """
        try:
            module = self.modules[module_id]
            question = module.quiz_questions[question_id]
            is_correct = answer == question['correct']
            
            # Update user progress
            progress = await self._get_user_module_progress(user_id, module_id)
            if not progress:
                return {'success': False, 'error': 'Module not started'}
            
            progress.quiz_scores.append(1.0 if is_correct else 0.0)
            
            # Calculate adaptive feedback
            recent_performance = progress.quiz_scores[-5:]  # Last 5 answers
            avg_recent = sum(recent_performance) / len(recent_performance)
            
            feedback = {
                'correct': is_correct,
                'explanation': question['explanation'],
                'encouragement': self._get_adaptive_encouragement(is_correct, avg_recent),
                'next_question': question_id + 1 < len(module.quiz_questions)
            }
            
            # Adaptive difficulty adjustment
            if avg_recent < 0.6 and len(recent_performance) >= 3:
                feedback['hint_unlocked'] = True
                feedback['additional_resources'] = self._get_remedial_content(question['topic'])
            
            # Mastery achievement check
            if len(progress.quiz_scores) >= len(module.quiz_questions):
                quiz_average = sum(progress.quiz_scores) / len(progress.quiz_scores)
                if quiz_average >= 0.8:
                    progress.mastery_achieved = True
                    feedback['mastery_unlocked'] = True
            
            await self._save_user_progress(progress)
            
            return {'success': True, 'feedback': feedback, 'progress': progress.completion_percentage}
            
        except Exception as e:
            logger.error(f"Error processing quiz answer for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def complete_module(self, user_id: str, module_id: str) -> Dict[str, Any]:
        """
        Complete learning module with celebration and meaningful rewards.
        Focuses on achievement and mastery rather than just external rewards.
        """
        try:
            module = self.modules[module_id]
            progress = await self._get_user_module_progress(user_id, module_id)
            
            if not progress:
                return {'success': False, 'error': 'Module not started'}
            
            # Validate completion criteria
            quiz_average = sum(progress.quiz_scores) / len(progress.quiz_scores) if progress.quiz_scores else 0
            meets_criteria = (
                quiz_average >= module.completion_criteria['quiz_score'] / 100 and
                progress.time_spent >= module.completion_criteria['time_spent'] and
                len(progress.quiz_scores) >= len(module.quiz_questions)
            )
            
            if not meets_criteria:
                return {
                    'success': False,
                    'error': 'Completion criteria not met',
                    'requirements': {
                        'quiz_score_required': module.completion_criteria['quiz_score'],
                        'quiz_score_current': int(quiz_average * 100),
                        'time_required': module.completion_criteria['time_spent'],
                        'time_current': progress.time_spent
                    }
                }
            
            # Mark as completed
            progress.completed = True
            progress.completion_percentage = 100
            
            # Calculate rewards (revealed only after completion)
            rewards = await self._calculate_completion_rewards(user_id, module, progress)
            
            # Apply rewards
            async with get_db_session() as session:
                user = await session.get(User, user_id)
                if user and user.virtual_wallet:
                    user.virtual_wallet.gem_coins += rewards['gem_coins']
                    user.virtual_wallet.total_xp += rewards['xp']
                    
                    # Check for level up
                    new_level = user.virtual_wallet.total_xp // 1000
                    if new_level > user.virtual_wallet.level:
                        user.virtual_wallet.level = new_level
                        rewards['level_up'] = True
                        rewards['new_level'] = new_level
                
                await session.commit()
            
            await self._save_user_progress(progress)
            
            # Check for learning path completion
            path_completions = await self._check_learning_path_completion(user_id)
            
            return {
                'success': True,
                'completion_celebration': {
                    'module_title': module.title,
                    'mastery_achieved': progress.mastery_achieved,
                    'time_spent': progress.time_spent,
                    'quiz_performance': int(quiz_average * 100),
                    'personal_best': await self._check_personal_records(user_id, module)
                },
                'rewards': rewards,
                'unlocked_content': await self._get_unlocked_content(user_id),
                'learning_paths': path_completions,
                'next_recommendations': await self._get_next_module_suggestions(user_id, module_id)
            }
            
        except Exception as e:
            logger.error(f"Error completing module {module_id} for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_motivation_message(self, module: LearningModule, context: str) -> str:
        """Generate contextual motivation messages that emphasize mastery"""
        messages = {
            'start': [
                f"Ready to master {module.title}? You're about to discover skills that could transform your crypto journey!",
                f"Thousands of successful investors started exactly where you are now. Let's build your expertise step by step.",
                f"This knowledge could be the difference between guessing and making informed decisions. Let's dive in!"
            ],
            'progress': [
                "You're building real expertise! Each concept you master makes you a more confident investor.",
                "Great progress! The skills you're developing will serve you for years to come.",
                "You're not just learning facts - you're developing the mindset of successful crypto investors."
            ],
            'challenge': [
                "This is where it gets interesting! Challenging concepts are where real learning happens.",
                "Don't worry if this feels difficult - you're expanding your capabilities right now.",
                "Every expert was once a beginner who refused to give up. You're on the right path!"
            ]
        }
        
        return random.choice(messages.get(context, messages['progress']))
    
    async def _calculate_completion_rewards(self, user_id: str, module: LearningModule, 
                                          progress: UserProgress) -> Dict[str, Any]:
        """Calculate meaningful rewards that celebrate achievement"""
        rewards = {'gem_coins': module.base_reward, 'xp': module.base_reward // 2, 'items': [], 'achievements': []}
        
        # Mastery bonus
        if progress.mastery_achieved:
            rewards['gem_coins'] += module.mastery_bonus
            rewards['xp'] += module.mastery_bonus // 2
            rewards['achievements'].append(f"{module.id}_mastery")
        
        # Time bonus (for focused learning)
        if progress.time_spent <= module.time_bonus_threshold:
            time_bonus = int(module.base_reward * 0.3)
            rewards['gem_coins'] += time_bonus
            rewards['achievements'].append(f"{module.id}_speed_learner")
        
        # First-time completion bonus
        user_modules_completed = await self._get_completed_modules_count(user_id)
        if user_modules_completed == 0:  # First module ever
            rewards['gem_coins'] += 1000
            rewards['items'].append('first_graduate_badge')
            rewards['achievements'].append('first_lesson_complete')
        
        # Difficulty-based rewards
        difficulty_multipliers = {
            DifficultyLevel.BEGINNER: 1.0,
            DifficultyLevel.INTERMEDIATE: 1.3,
            DifficultyLevel.ADVANCED: 1.6,
            DifficultyLevel.EXPERT: 2.0
        }
        
        multiplier = difficulty_multipliers[module.difficulty]
        rewards['gem_coins'] = int(rewards['gem_coins'] * multiplier)
        rewards['xp'] = int(rewards['xp'] * multiplier)
        
        return rewards

# Global learn-to-earn engine instance  
learn_to_earn = LearnToEarnEngine()