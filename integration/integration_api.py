"""
Integration API - RESTful endpoints for crypto-minigame integration features.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from auth.middleware import get_current_user
from .crypto_minigame_bridge import crypto_minigame_bridge
from mini_games import mini_game_manager
from logger import logger

router = APIRouter()
security = HTTPBearer()


# Pydantic Models
class ApplyBonusRequest(BaseModel):
    game_type: str = Field(..., description="Type of mini-game")
    base_reward: float = Field(..., gt=0, description="Base reward amount")
    game_performance: Dict[str, Any] = Field(default={}, description="Game performance data")


class CreatePredictionRequest(BaseModel):
    crypto_symbol: str = Field(..., description="Cryptocurrency symbol to predict")
    prediction_type: str = Field(..., pattern="^(UP|DOWN|SIDEWAYS)$", description="Price prediction")
    time_horizon_hours: int = Field(default=24, ge=1, le=168, description="Prediction time horizon")
    stake_amount: float = Field(default=100.0, ge=50.0, le=5000.0, description="Stake amount in GEMs")


@router.get("/multipliers", response_model=Dict[str, Any])
async def get_user_multipliers(
    current_user: dict = Depends(get_current_user)
):
    """Get current reward multipliers for the user."""
    try:
        multipliers = await crypto_minigame_bridge.calculate_user_multipliers(
            current_user["user_id"]
        )
        
        # Convert to human-readable format
        multiplier_details = []
        total_multiplier = 1.0
        
        for bonus_type, multiplier in multipliers.items():
            total_multiplier *= multiplier
            bonus_pct = (multiplier - 1.0) * 100
            
            multiplier_details.append({
                "type": bonus_type,
                "multiplier": multiplier,
                "bonus_percentage": bonus_pct,
                "description": crypto_minigame_bridge._get_bonus_description(bonus_type, multiplier)
            })
        
        return {
            "success": True,
            "data": {
                "active_multipliers": multiplier_details,
                "total_multiplier": total_multiplier,
                "total_bonus_percentage": (total_multiplier - 1.0) * 100,
                "explanation": "These multipliers are applied to mini-game rewards based on your crypto trading activity"
            }
        }
        
    except Exception as e:
        logger.error(f"Get multipliers endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/apply-bonus", response_model=Dict[str, Any])
async def apply_crypto_bonus(
    request: ApplyBonusRequest,
    current_user: dict = Depends(get_current_user)
):
    """Apply crypto-based bonuses to mini-game rewards."""
    try:
        bonus_result = await crypto_minigame_bridge.apply_crypto_bonus_to_minigame(
            user_id=current_user["user_id"],
            game_type=request.game_type,
            base_reward=request.base_reward,
            game_performance=request.game_performance
        )
        
        return {
            "success": True,
            "data": bonus_result,
            "message": f"Applied {bonus_result['total_multiplier']:.2f}x multiplier to your reward!"
        }
        
    except Exception as e:
        logger.error(f"Apply bonus endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/predictions/create", response_model=Dict[str, Any])
async def create_price_prediction(
    request: CreatePredictionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a crypto price prediction game."""
    try:
        prediction = await crypto_minigame_bridge.create_crypto_prediction_game(
            user_id=current_user["user_id"],
            crypto_symbol=request.crypto_symbol.upper(),
            prediction_type=request.prediction_type,
            time_horizon_hours=request.time_horizon_hours,
            stake_amount=request.stake_amount
        )
        
        return {
            "success": True,
            "data": prediction,
            "message": f"Price prediction created for {request.crypto_symbol}!"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Create prediction endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/predictions/{prediction_id}/resolve", response_model=Dict[str, Any])
async def resolve_price_prediction(
    prediction_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Resolve a crypto price prediction game."""
    try:
        result = await crypto_minigame_bridge.resolve_crypto_prediction(prediction_id)
        
        message = "Congratulations! You won!" if result["correct"] else "Better luck next time!"
        
        return {
            "success": True,
            "data": result,
            "message": message
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Resolve prediction endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats", response_model=Dict[str, Any])
async def get_integration_stats(
    current_user: dict = Depends(get_current_user)
):
    """Get user's crypto-minigame integration statistics."""
    try:
        stats = await crypto_minigame_bridge.get_user_integration_stats(
            current_user["user_id"]
        )
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Get stats endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/enhanced-games", response_model=Dict[str, Any])
async def get_enhanced_mini_games(
    current_user: dict = Depends(get_current_user)
):
    """Get mini-games with crypto-enhanced rewards."""
    try:
        # Get current multipliers
        multipliers = await crypto_minigame_bridge.calculate_user_multipliers(
            current_user["user_id"]
        )
        
        total_multiplier = 1.0
        for multiplier in multipliers.values():
            total_multiplier *= multiplier
        
        # Get available mini-games with enhanced rewards
        enhanced_games = [
            {
                "game_type": "MEMORY_MATCH",
                "name": "Crypto Memory Match",
                "description": "Match crypto symbols and earn enhanced rewards!",
                "base_reward_range": "25-200 GEMs",
                "enhanced_reward_range": f"{int(25 * total_multiplier)}-{int(200 * total_multiplier)} GEMs",
                "multiplier": total_multiplier,
                "crypto_theme": True,
                "difficulty_levels": ["EASY", "MEDIUM", "HARD", "EXPERT"]
            },
            {
                "game_type": "NUMBER_PREDICTION",
                "name": "Market Number Prediction",
                "description": "Predict crypto-themed numbers with trading bonuses!",
                "base_reward_range": "50-300 GEMs",
                "enhanced_reward_range": f"{int(50 * total_multiplier)}-{int(300 * total_multiplier)} GEMs",
                "multiplier": total_multiplier,
                "crypto_theme": True,
                "difficulty_levels": ["BEGINNER", "INTERMEDIATE", "ADVANCED"]
            },
            {
                "game_type": "PUZZLE_SOLVER",
                "name": "Blockchain Puzzle",
                "description": "Solve crypto puzzles with portfolio-based bonuses!",
                "base_reward_range": "100-400 GEMs",
                "enhanced_reward_range": f"{int(100 * total_multiplier)}-{int(400 * total_multiplier)} GEMs",
                "multiplier": total_multiplier,
                "crypto_theme": True,
                "difficulty_levels": ["EASY", "MEDIUM", "HARD"]
            },
            {
                "game_type": "QUICK_MATH",
                "name": "Trading Math Challenge",
                "description": "Calculate trading profits with learning bonuses!",
                "base_reward_range": "30-150 GEMs",
                "enhanced_reward_range": f"{int(30 * total_multiplier)}-{int(150 * total_multiplier)} GEMs",
                "multiplier": total_multiplier,
                "crypto_theme": True,
                "difficulty_levels": ["BASIC", "INTERMEDIATE", "ADVANCED"]
            },
            {
                "game_type": "SPIN_WHEEL",
                "name": "Crypto Fortune Wheel",
                "description": "Spin for crypto-themed prizes with trading multipliers!",
                "base_reward_range": "10-500 GEMs",
                "enhanced_reward_range": f"{int(10 * total_multiplier)}-{int(500 * total_multiplier)} GEMs",
                "multiplier": total_multiplier,
                "crypto_theme": True,
                "special_features": ["Crypto symbols", "Trading bonuses", "Portfolio multipliers"]
            },
            {
                "game_type": "PRICE_PREDICTION",
                "name": "Crypto Price Prediction",
                "description": "Predict real crypto price movements!",
                "base_reward_range": "Stake x 1.8 (80% profit)",
                "enhanced_reward_range": f"Stake x {1.8 * total_multiplier:.1f} ({(1.8 * total_multiplier - 1)*100:.0f}% profit)",
                "multiplier": total_multiplier,
                "crypto_theme": True,
                "prediction_types": ["UP", "DOWN", "SIDEWAYS"],
                "time_horizons": ["1 hour", "6 hours", "24 hours", "1 week"]
            }
        ]
        
        return {
            "success": True,
            "data": {
                "enhanced_games": enhanced_games,
                "user_multiplier": total_multiplier,
                "active_bonuses": len(multipliers),
                "explanation": "Your crypto trading activity enhances mini-game rewards!"
            }
        }
        
    except Exception as e:
        logger.error(f"Get enhanced games endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/daily-challenges", response_model=Dict[str, Any])
async def get_daily_crypto_challenges():
    """Get daily crypto-themed challenges."""
    try:
        # Generate daily challenges based on current date
        from datetime import datetime
        import hashlib
        
        # Use date as seed for consistent daily challenges
        date_seed = datetime.utcnow().strftime("%Y-%m-%d")
        seed_hash = hashlib.md5(date_seed.encode()).hexdigest()
        
        # Generate challenges based on seed
        challenges = [
            {
                "challenge_id": f"daily-prediction-{date_seed}",
                "title": "Daily Price Prediction",
                "description": "Predict Bitcoin's price movement in the next 24 hours",
                "type": "PRICE_PREDICTION",
                "crypto_symbol": "BTC",
                "reward": "300 GEMs + multipliers",
                "difficulty": "MEDIUM",
                "time_limit": "24 hours",
                "requirements": ["Minimum 100 GEM stake"]
            },
            {
                "challenge_id": f"daily-memory-{date_seed}",
                "title": "Crypto Memory Challenge",
                "description": "Complete memory match game with 90%+ accuracy",
                "type": "MEMORY_MATCH",
                "target_accuracy": 90,
                "reward": "250 GEMs + multipliers",
                "difficulty": "HARD",
                "time_limit": "No limit",
                "requirements": ["Score 90% or higher"]
            },
            {
                "challenge_id": f"daily-trading-{date_seed}",
                "title": "Trading Volume Challenge",
                "description": "Make at least 3 profitable trades today",
                "type": "TRADING_ACTIVITY",
                "target_trades": 3,
                "reward": "500 GEMs + bonus multipliers",
                "difficulty": "ADVANCED",
                "time_limit": "24 hours",
                "requirements": ["3 profitable trades", "Minimum 100 GEM per trade"]
            }
        ]
        
        return {
            "success": True,
            "data": {
                "challenges": challenges,
                "reset_time": "00:00 UTC",
                "next_reset_in_hours": 24 - datetime.utcnow().hour,
                "completion_bonus": "Complete all 3 challenges for 1000 GEM bonus!"
            }
        }
        
    except Exception as e:
        logger.error(f"Get daily challenges endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/leaderboard/integration", response_model=Dict[str, Any])
async def get_integration_leaderboard():
    """Get leaderboard for crypto-minigame integration activities."""
    try:
        # Mock leaderboard data (in real implementation, query database)
        leaderboard = {
            "top_earners": [
                {"rank": 1, "username": "CryptoGamer", "bonus_gems_earned": 15750, "total_multiplier": 2.8},
                {"rank": 2, "username": "TradingPro", "bonus_gems_earned": 12340, "total_multiplier": 2.4},
                {"rank": 3, "username": "GameMaster", "bonus_gems_earned": 9820, "total_multiplier": 2.1},
                {"rank": 4, "username": "HODLGamer", "bonus_gems_earned": 8760, "total_multiplier": 1.9},
                {"rank": 5, "username": "CryptoKing", "bonus_gems_earned": 7500, "total_multiplier": 1.8}
            ],
            "top_predictors": [
                {"rank": 1, "username": "MarketOracle", "correct_predictions": 87, "accuracy": 92.5},
                {"rank": 2, "username": "PriceMaster", "correct_predictions": 76, "accuracy": 88.4},
                {"rank": 3, "username": "TrendHunter", "correct_predictions": 69, "accuracy": 85.2},
                {"rank": 4, "username": "CrystalBall", "correct_predictions": 62, "accuracy": 82.7},
                {"rank": 5, "username": "FutureSeeker", "correct_predictions": 58, "accuracy": 80.6}
            ],
            "most_active": [
                {"rank": 1, "username": "GameAddict", "games_played": 547, "avg_multiplier": 2.2},
                {"rank": 2, "username": "NonStopGamer", "games_played": 432, "avg_multiplier": 1.9},
                {"rank": 3, "username": "PlayAllDay", "games_played": 389, "avg_multiplier": 2.0},
                {"rank": 4, "username": "MiniGamePro", "games_played": 356, "avg_multiplier": 1.7},
                {"rank": 5, "username": "ChallengeMaster", "games_played": 298, "avg_multiplier": 2.1}
            ]
        }
        
        return {
            "success": True,
            "data": leaderboard
        }
        
    except Exception as e:
        logger.error(f"Get leaderboard endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")