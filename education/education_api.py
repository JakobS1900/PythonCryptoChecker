"""
Education API - RESTful endpoints for learning system and trading simulation.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from auth.middleware import get_current_user
from .learning_system import learning_system, LessonDifficulty, LessonType, UserProgress
from .simulation_trainer import simulation_trainer, SimulationType, MarketScenario
from logger import logger

router = APIRouter()
security = HTTPBearer()


# Pydantic Models
class StartLessonRequest(BaseModel):
    lesson_id: str = Field(..., description="ID of the lesson to start")


class CompleteQuizRequest(BaseModel):
    lesson_id: str = Field(..., description="ID of the lesson")
    answers: List[int] = Field(..., description="List of answer indices")
    time_spent: float = Field(default=0.0, description="Time spent on lesson in minutes")


class CreateSimulationRequest(BaseModel):
    simulation_type: str = Field(..., pattern="^(PAPER_TRADING|STRATEGY_TEST|SCENARIO_PRACTICE|CHALLENGE_MODE|AI_COACHING)$")
    starting_balance: float = Field(default=10000.0, ge=1000, le=100000)
    duration_days: int = Field(default=7, ge=1, le=30)
    scenario_name: Optional[str] = Field(None, description="Market scenario for practice")
    allowed_cryptos: List[str] = Field(default=["BTC", "ETH", "ADA"], description="Allowed cryptocurrencies")
    educational_hints: bool = Field(default=True, description="Enable AI coaching hints")
    simulation_speed: float = Field(default=1.0, ge=0.5, le=10.0, description="Simulation speed multiplier")


class SimulationTradeRequest(BaseModel):
    session_id: str = Field(..., description="Simulation session ID")
    trade_type: str = Field(..., pattern="^(BUY|SELL)$", description="Trade type")
    crypto_symbol: str = Field(..., description="Cryptocurrency symbol")
    amount: float = Field(..., gt=0, description="Amount to trade (GEMs for BUY, crypto units for SELL)")


class ChallengeStartRequest(BaseModel):
    challenge_id: str = Field(..., description="Challenge ID to start")


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_learning_dashboard(
    current_user: dict = Depends(get_current_user)
):
    """Get user's learning dashboard with progress and recommendations."""
    try:
        dashboard = await learning_system.get_user_dashboard(current_user["user_id"])
        
        return {
            "success": True,
            "data": dashboard
        }
        
    except Exception as e:
        logger.error(f"Learning dashboard endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/lessons/start", response_model=Dict[str, Any])
async def start_lesson(
    request: StartLessonRequest,
    current_user: dict = Depends(get_current_user)
):
    """Start a lesson for the user."""
    try:
        lesson_data = await learning_system.start_lesson(
            user_id=current_user["user_id"],
            lesson_id=request.lesson_id
        )
        
        return {
            "success": True,
            "data": lesson_data,
            "message": "Lesson started successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Start lesson endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/lessons/quiz", response_model=Dict[str, Any])
async def complete_lesson_quiz(
    request: CompleteQuizRequest,
    current_user: dict = Depends(get_current_user)
):
    """Complete a lesson quiz and get results."""
    try:
        quiz_result = await learning_system.complete_lesson_quiz(
            user_id=current_user["user_id"],
            lesson_id=request.lesson_id,
            answers=request.answers,
            time_spent=request.time_spent
        )
        
        return {
            "success": True,
            "data": quiz_result,
            "message": "Quiz completed successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Complete quiz endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/lessons", response_model=Dict[str, Any])
async def get_available_lessons(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    lesson_type: Optional[str] = None
):
    """Get available lessons with filtering."""
    try:
        # For now, return basic lesson info from the system
        # In a full implementation, you'd query the database
        
        lessons_info = [
            {
                "lesson_id": "crypto-basics-1",
                "title": "What is Cryptocurrency?",
                "description": "Learn the basics of digital currencies and blockchain technology",
                "category": "Cryptocurrency Basics",
                "difficulty": "BEGINNER",
                "lesson_type": "TUTORIAL",
                "estimated_duration": 10,
                "reward_gems": 100
            },
            {
                "lesson_id": "trading-basics-1",
                "title": "Understanding Market Orders vs Limit Orders",
                "description": "Learn the difference between market and limit orders in trading",
                "category": "Trading Fundamentals",
                "difficulty": "BEGINNER",
                "lesson_type": "TUTORIAL",
                "estimated_duration": 15,
                "reward_gems": 150
            },
            {
                "lesson_id": "risk-management-1",
                "title": "Risk Management Fundamentals",
                "description": "Learn essential risk management techniques for crypto trading",
                "category": "Risk Management",
                "difficulty": "INTERMEDIATE",
                "lesson_type": "TUTORIAL",
                "estimated_duration": 20,
                "reward_gems": 200
            },
            {
                "lesson_id": "technical-analysis-1",
                "title": "Technical Analysis: Support and Resistance",
                "description": "Learn to identify key price levels that influence crypto markets",
                "category": "Technical Analysis",
                "difficulty": "INTERMEDIATE",
                "lesson_type": "TUTORIAL",
                "estimated_duration": 25,
                "reward_gems": 250
            }
        ]
        
        # Apply filters
        filtered_lessons = lessons_info
        if category:
            filtered_lessons = [l for l in filtered_lessons if l["category"] == category]
        if difficulty:
            filtered_lessons = [l for l in filtered_lessons if l["difficulty"] == difficulty.upper()]
        if lesson_type:
            filtered_lessons = [l for l in filtered_lessons if l["lesson_type"] == lesson_type.upper()]
        
        return {
            "success": True,
            "data": {
                "lessons": filtered_lessons,
                "total_count": len(filtered_lessons),
                "categories": ["Cryptocurrency Basics", "Trading Fundamentals", "Risk Management", "Technical Analysis"],
                "difficulties": ["BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"]
            }
        }
        
    except Exception as e:
        logger.error(f"Get lessons endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/simulation/create", response_model=Dict[str, Any])
async def create_simulation_session(
    request: CreateSimulationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new trading simulation session."""
    try:
        simulation_type = SimulationType(request.simulation_type)
        
        config = {
            "starting_balance": request.starting_balance,
            "duration_days": request.duration_days,
            "scenario_name": request.scenario_name,
            "allowed_cryptos": request.allowed_cryptos,
            "educational_hints": request.educational_hints,
            "simulation_speed": request.simulation_speed
        }
        
        session_data = await simulation_trainer.create_simulation_session(
            user_id=current_user["user_id"],
            simulation_type=simulation_type,
            config=config
        )
        
        return {
            "success": True,
            "data": session_data,
            "message": "Simulation session created successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Create simulation endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/simulation/trade", response_model=Dict[str, Any])
async def execute_simulation_trade(
    request: SimulationTradeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Execute a trade in simulation session."""
    try:
        trade_result = await simulation_trainer.execute_simulation_trade(
            session_id=request.session_id,
            trade_type=request.trade_type,
            crypto_symbol=request.crypto_symbol.upper(),
            amount=request.amount
        )
        
        return {
            "success": True,
            "data": trade_result,
            "message": f"Simulation {request.trade_type.lower()} executed successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Simulation trade endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/simulation/{session_id}", response_model=Dict[str, Any])
async def get_simulation_dashboard(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get simulation dashboard with performance metrics."""
    try:
        dashboard = await simulation_trainer.get_simulation_dashboard(
            user_id=current_user["user_id"],
            session_id=session_id
        )
        
        return {
            "success": True,
            "data": dashboard
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Simulation dashboard endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/simulation/{session_id}/complete", response_model=Dict[str, Any])
async def complete_simulation_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Complete a simulation session and get final report."""
    try:
        completion_result = await simulation_trainer.complete_simulation(
            user_id=current_user["user_id"],
            session_id=session_id
        )
        
        return {
            "success": True,
            "data": completion_result,
            "message": "Simulation completed successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Complete simulation endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/challenges", response_model=Dict[str, Any])
async def get_available_challenges():
    """Get available trading challenges."""
    try:
        challenges = simulation_trainer.get_available_challenges()
        
        return {
            "success": True,
            "data": {
                "challenges": challenges,
                "total_count": len(challenges)
            }
        }
        
    except Exception as e:
        logger.error(f"Get challenges endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/challenges/start", response_model=Dict[str, Any])
async def start_trading_challenge(
    request: ChallengeStartRequest,
    current_user: dict = Depends(get_current_user)
):
    """Start a specific trading challenge."""
    try:
        challenge_result = await simulation_trainer.start_challenge(
            user_id=current_user["user_id"],
            challenge_id=request.challenge_id
        )
        
        return {
            "success": True,
            "data": challenge_result,
            "message": "Challenge started successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Start challenge endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/strategies", response_model=Dict[str, Any])
async def get_trading_strategies():
    """Get available trading strategies and guides."""
    try:
        strategies = [
            {
                "strategy_id": "hodl-strategy",
                "name": "HODL Strategy",
                "description": "Long-term holding strategy for patient investors",
                "risk_level": "LOW",
                "time_horizon": "LONG",
                "success_rate": 75.0,
                "average_return": 120.0,
                "recommended_cryptos": ["BTC", "ETH"],
                "required_knowledge": "BEGINNER"
            },
            {
                "strategy_id": "swing-trading",
                "name": "Swing Trading",
                "description": "Medium-term trading based on technical analysis",
                "risk_level": "MEDIUM",
                "time_horizon": "MEDIUM",
                "success_rate": 60.0,
                "average_return": 25.0,
                "recommended_cryptos": ["BTC", "ETH", "ADA", "SOL"],
                "required_knowledge": "INTERMEDIATE"
            },
            {
                "strategy_id": "scalping",
                "name": "Scalping",
                "description": "High-frequency trading for small, quick profits",
                "risk_level": "HIGH",
                "time_horizon": "SHORT",
                "success_rate": 45.0,
                "average_return": 15.0,
                "recommended_cryptos": ["BTC", "ETH"],
                "required_knowledge": "ADVANCED"
            },
            {
                "strategy_id": "dca-strategy",
                "name": "Dollar Cost Averaging",
                "description": "Systematic buying over time to reduce volatility impact",
                "risk_level": "LOW",
                "time_horizon": "LONG",
                "success_rate": 85.0,
                "average_return": 80.0,
                "recommended_cryptos": ["BTC", "ETH", "ADA"],
                "required_knowledge": "BEGINNER"
            }
        ]
        
        return {
            "success": True,
            "data": {
                "strategies": strategies,
                "total_count": len(strategies)
            }
        }
        
    except Exception as e:
        logger.error(f"Get strategies endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/progress", response_model=Dict[str, Any])
async def get_learning_progress(
    current_user: dict = Depends(get_current_user)
):
    """Get detailed learning progress for the user."""
    try:
        # This would typically query the database for user progress
        # For now, return mock data
        progress_data = {
            "user_id": current_user["user_id"],
            "overall_progress": {
                "lessons_completed": 3,
                "total_lessons": 12,
                "completion_percentage": 25.0,
                "gems_earned": 550,
                "current_streak": 5,
                "total_study_hours": 2.5
            },
            "category_progress": [
                {
                    "category": "Cryptocurrency Basics",
                    "completed": 2,
                    "total": 4,
                    "percentage": 50.0
                },
                {
                    "category": "Trading Fundamentals", 
                    "completed": 1,
                    "total": 3,
                    "percentage": 33.3
                },
                {
                    "category": "Risk Management",
                    "completed": 0,
                    "total": 2,
                    "percentage": 0.0
                },
                {
                    "category": "Technical Analysis",
                    "completed": 0,
                    "total": 3,
                    "percentage": 0.0
                }
            ],
            "recent_activity": [
                {
                    "type": "lesson_completed",
                    "title": "What is Cryptocurrency?",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "gems_earned": 100
                },
                {
                    "type": "quiz_passed",
                    "title": "Trading Fundamentals Quiz",
                    "score": 85,
                    "timestamp": "2024-01-14T16:45:00Z"
                }
            ],
            "achievements": [
                {
                    "name": "First Steps",
                    "description": "Completed your first lesson",
                    "earned_at": "2024-01-13T14:20:00Z"
                },
                {
                    "name": "Quiz Master",
                    "description": "Scored 90%+ on a quiz",
                    "earned_at": "2024-01-14T16:45:00Z"
                }
            ]
        }
        
        return {
            "success": True,
            "data": progress_data
        }
        
    except Exception as e:
        logger.error(f"Get progress endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/leaderboard", response_model=Dict[str, Any])
async def get_learning_leaderboard():
    """Get learning leaderboard with top performers."""
    try:
        # Mock leaderboard data
        leaderboard = {
            "weekly": [
                {"rank": 1, "username": "CryptoMaster", "lessons_completed": 15, "gems_earned": 2500},
                {"rank": 2, "username": "TradingPro", "lessons_completed": 12, "gems_earned": 2100},
                {"rank": 3, "username": "BlockchainFan", "lessons_completed": 10, "gems_earned": 1800},
                {"rank": 4, "username": "HODLer", "lessons_completed": 8, "gems_earned": 1400},
                {"rank": 5, "username": "DeFiExplorer", "lessons_completed": 7, "gems_earned": 1200}
            ],
            "monthly": [
                {"rank": 1, "username": "CryptoMaster", "lessons_completed": 45, "gems_earned": 7500},
                {"rank": 2, "username": "TradingPro", "lessons_completed": 38, "gems_earned": 6300},
                {"rank": 3, "username": "BlockchainFan", "lessons_completed": 32, "gems_earned": 5400},
                {"rank": 4, "username": "HODLer", "lessons_completed": 28, "gems_earned": 4700},
                {"rank": 5, "username": "DeFiExplorer", "lessons_completed": 25, "gems_earned": 4200}
            ],
            "all_time": [
                {"rank": 1, "username": "CryptoMaster", "lessons_completed": 125, "gems_earned": 21000},
                {"rank": 2, "username": "TradingPro", "lessons_completed": 98, "gems_earned": 16500},
                {"rank": 3, "username": "BlockchainFan", "lessons_completed": 87, "gems_earned": 14700},
                {"rank": 4, "username": "HODLer", "lessons_completed": 76, "gems_earned": 12800},
                {"rank": 5, "username": "DeFiExplorer", "lessons_completed": 69, "gems_earned": 11600}
            ]
        }
        
        return {
            "success": True,
            "data": leaderboard
        }
        
    except Exception as e:
        logger.error(f"Get leaderboard endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")