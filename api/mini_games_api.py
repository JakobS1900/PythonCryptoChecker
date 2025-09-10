"""
Mini-Games API endpoints for all gaming features.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from gamification import virtual_economy
from mini_games import MiniGameManager
from logger import logger

router = APIRouter()
security = HTTPBearer()

# Initialize mini-game manager
mini_game_manager = MiniGameManager(virtual_economy)


class GameStartRequest(BaseModel):
    game_type: str = Field(..., description="Type of game to start")
    difficulty: Optional[str] = Field("EASY", description="Game difficulty")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional game configuration")


class GameMoveRequest(BaseModel):
    game_id: str = Field(..., description="Game session ID")
    move_data: Dict[str, Any] = Field(..., description="Move or action data")


class AnswerSubmissionRequest(BaseModel):
    game_id: str = Field(..., description="Game session ID")
    question_id: str = Field(..., description="Question/problem ID")
    answer: str = Field(..., description="User's answer")
    time_taken: float = Field(..., description="Time taken to answer in seconds")


class WheelSpinRequest(BaseModel):
    wheel_type: str = Field(..., description="Type of wheel to spin")


# ==================== MINI-GAME DASHBOARD ====================

@router.get("/dashboard")
async def get_mini_game_dashboard(request: Request):
    """Get user's mini-game dashboard with all available games and stats."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with get_db_session() as session:
            dashboard_data = await mini_game_manager.get_user_dashboard(session, user_id)
            
            return {
                "status": "success",
                "data": dashboard_data
            }
            
    except Exception as e:
        logger.error(f"Dashboard error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard")


# ==================== MEMORY MATCH GAME ====================

@router.post("/memory-match/start")
async def start_memory_game(request: Request, game_request: GameStartRequest):
    """Start a new memory match game."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        from mini_games.memory_match import GameDifficulty
        difficulty = GameDifficulty(game_request.difficulty)
        
        async with get_db_session() as session:
            game_data = await mini_game_manager.memory_game.start_new_game(
                session, user_id, difficulty
            )
            
            return {
                "status": "success",
                "data": game_data
            }
            
    except Exception as e:
        logger.error(f"Memory game start error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start memory game")


@router.post("/memory-match/move")
async def make_memory_move(request: Request, move_request: GameMoveRequest):
    """Make a move in memory match game."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with get_db_session() as session:
            card1_id = move_request.move_data.get("card1_id")
            card2_id = move_request.move_data.get("card2_id")
            
            if not card1_id or not card2_id:
                raise HTTPException(status_code=400, detail="Missing card IDs")
            
            result = await mini_game_manager.memory_game.make_move(
                session, move_request.game_id, card1_id, card2_id
            )
            
            # Update user stats if game completed
            if result.get("game_complete"):
                performance_data = {
                    "accuracy": 1.0 if result.get("reward_earned", 0) > 0 else 0.5,
                    "perfect": result.get("reward_earned", 0) > 100
                }
                await mini_game_manager.update_user_stats_after_game(
                    session, user_id, "memory_match",
                    result.get("reward_earned", 0), 0, performance_data
                )
            
            return {
                "status": "success",
                "data": result
            }
            
    except Exception as e:
        logger.error(f"Memory game move error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process move")


@router.get("/memory-match/{game_id}")
async def get_memory_game_state(request: Request, game_id: str):
    """Get current state of memory game."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with get_db_session() as session:
            game_state = await mini_game_manager.memory_game.get_game_state(session, game_id)
            
            if not game_state:
                raise HTTPException(status_code=404, detail="Game not found")
            
            return {
                "status": "success",
                "data": game_state
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Memory game state error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get game state")


# ==================== NUMBER PREDICTION GAME ====================

@router.post("/number-prediction/start")
async def start_prediction_game(request: Request, game_request: GameStartRequest):
    """Start a new number prediction game."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        from mini_games.number_prediction import PredictionDifficulty
        difficulty = PredictionDifficulty(game_request.difficulty)
        total_questions = game_request.config.get("total_questions", 5)
        
        async with get_db_session() as session:
            game_data = await mini_game_manager.prediction_game.start_new_game(
                session, user_id, difficulty, total_questions
            )
            
            return {
                "status": "success",
                "data": game_data
            }
            
    except Exception as e:
        logger.error(f"Prediction game start error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start prediction game")


@router.post("/number-prediction/answer")
async def submit_prediction_answer(request: Request, answer_request: AnswerSubmissionRequest):
    """Submit answer for number prediction question."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with get_db_session() as session:
            result = await mini_game_manager.prediction_game.submit_answer(
                session, answer_request.game_id, answer_request.question_id,
                answer_request.answer, answer_request.time_taken
            )
            
            # Update user stats if game completed
            if result.get("game_complete"):
                accuracy = result.get("current_score", 0) / result.get("total_questions", 1)
                performance_data = {
                    "accuracy": accuracy,
                    "perfect": accuracy == 1.0
                }
                await mini_game_manager.update_user_stats_after_game(
                    session, user_id, "number_prediction",
                    result.get("gem_coins_earned", 0), result.get("xp_earned", 0), performance_data
                )
            
            return {
                "status": "success",
                "data": result
            }
            
    except Exception as e:
        logger.error(f"Prediction game answer error: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit answer")


# ==================== PUZZLE SOLVER GAME ====================

@router.post("/puzzle-solver/start")
async def start_puzzle_game(request: Request, game_request: GameStartRequest):
    """Start a new puzzle solving game."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        from mini_games.puzzle_solver import PuzzleType, PuzzleDifficulty
        
        puzzle_type = PuzzleType(game_request.config.get("puzzle_type", "SLIDING_PUZZLE"))
        difficulty = PuzzleDifficulty(game_request.difficulty)
        
        async with get_db_session() as session:
            game_data = await mini_game_manager.puzzle_game.start_new_puzzle(
                session, user_id, puzzle_type, difficulty
            )
            
            return {
                "status": "success",
                "data": game_data
            }
            
    except Exception as e:
        logger.error(f"Puzzle game start error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start puzzle game")


@router.post("/puzzle-solver/move")
async def make_puzzle_move(request: Request, move_request: GameMoveRequest):
    """Make a move in puzzle game."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with get_db_session() as session:
            result = await mini_game_manager.puzzle_game.make_move(
                session, move_request.game_id, move_request.move_data
            )
            
            # Update user stats if game completed
            if result.get("is_solved") or result.get("is_correct"):
                performance_data = {
                    "efficiency": result.get("efficiency_score", 50),
                    "perfect": result.get("gem_coins_earned", 0) > 75
                }
                await mini_game_manager.update_user_stats_after_game(
                    session, user_id, "puzzle_solver",
                    result.get("gem_coins_earned", 0), result.get("xp_earned", 0), performance_data
                )
            
            return {
                "status": "success",
                "data": result
            }
            
    except Exception as e:
        logger.error(f"Puzzle game move error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process puzzle move")


# ==================== QUICK MATH GAME ====================

@router.post("/quick-math/start")
async def start_math_game(request: Request, game_request: GameStartRequest):
    """Start a new quick math game."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        from mini_games.quick_math import MathDifficulty
        difficulty = MathDifficulty(game_request.difficulty)
        total_problems = game_request.config.get("total_problems", 10)
        math_type = game_request.config.get("math_type", "MIXED")
        
        async with get_db_session() as session:
            game_data = await mini_game_manager.math_game.start_new_game(
                session, user_id, difficulty, total_problems, math_type
            )
            
            return {
                "status": "success",
                "data": game_data
            }
            
    except Exception as e:
        logger.error(f"Math game start error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start math game")


@router.post("/quick-math/answer")
async def submit_math_answer(request: Request, answer_request: AnswerSubmissionRequest):
    """Submit answer for math problem."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with get_db_session() as session:
            result = await mini_game_manager.math_game.submit_answer(
                session, answer_request.game_id, answer_request.question_id,
                answer_request.answer, answer_request.time_taken
            )
            
            # Update user stats if game completed
            if result.get("game_complete"):
                accuracy = result.get("current_score", 0) / result.get("total_problems", 1)
                performance_data = {
                    "accuracy": accuracy,
                    "perfect": accuracy == 1.0
                }
                await mini_game_manager.update_user_stats_after_game(
                    session, user_id, "quick_math",
                    result.get("gem_coins_earned", 0), result.get("xp_earned", 0), performance_data
                )
            
            return {
                "status": "success",
                "data": result
            }
            
    except Exception as e:
        logger.error(f"Math game answer error: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit math answer")


# ==================== SPIN WHEEL GAME ====================

@router.get("/spin-wheel/available")
async def get_available_wheels(request: Request):
    """Get available spin wheels for user."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with get_db_session() as session:
            wheels_data = await mini_game_manager.wheel_game.get_available_wheels(session, user_id)
            
            return {
                "status": "success",
                "data": wheels_data
            }
            
    except Exception as e:
        logger.error(f"Available wheels error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available wheels")


@router.post("/spin-wheel/spin")
async def spin_wheel(request: Request, spin_request: WheelSpinRequest):
    """Spin a wheel for rewards."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with get_db_session() as session:
            result = await mini_game_manager.wheel_game.spin_wheel(
                session, user_id, spin_request.wheel_type
            )
            
            # Update user stats
            gems_earned = result.get("rewards", {}).get("gems_awarded", 0)
            xp_earned = result.get("rewards", {}).get("xp_awarded", 0)
            
            if gems_earned > 0 or xp_earned > 0:
                performance_data = {"perfect": False}
                await mini_game_manager.update_user_stats_after_game(
                    session, user_id, "spin_wheel", gems_earned, xp_earned, performance_data
                )
            
            return {
                "status": "success",
                "data": result
            }
            
    except Exception as e:
        logger.error(f"Wheel spin error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to spin wheel")


@router.get("/spin-wheel/history")
async def get_spin_history(request: Request, limit: int = 20):
    """Get user's spin wheel history."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with get_db_session() as session:
            history = await mini_game_manager.wheel_game.get_spin_history(session, user_id, limit)
            
            return {
                "status": "success",
                "data": {"history": history}
            }
            
    except Exception as e:
        logger.error(f"Spin history error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get spin history")


# ==================== LEADERBOARDS ====================

@router.get("/leaderboards")
async def get_leaderboards(request: Request):
    """Get global mini-game leaderboards."""
    
    try:
        async with get_db_session() as session:
            leaderboards = await mini_game_manager.get_global_leaderboards(session)
            
            return {
                "status": "success",
                "data": leaderboards
            }
            
    except Exception as e:
        logger.error(f"Leaderboards error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get leaderboards")


@router.get("/leaderboards/spin-wheel")
async def get_wheel_leaderboard(request: Request, timeframe: str = "weekly"):
    """Get spin wheel specific leaderboard."""
    
    try:
        async with get_db_session() as session:
            leaderboard = await mini_game_manager.wheel_game.get_leaderboard(session, timeframe)
            
            return {
                "status": "success",
                "data": {"leaderboard": leaderboard, "timeframe": timeframe}
            }
            
    except Exception as e:
        logger.error(f"Wheel leaderboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get wheel leaderboard")


# ==================== USER STATISTICS ====================

@router.get("/stats/memory-match")
async def get_memory_stats(request: Request):
    """Get user's memory match game statistics."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with get_db_session() as session:
            stats = await mini_game_manager.memory_game.get_user_stats(session, user_id)
            
            return {
                "status": "success",
                "data": stats
            }
            
    except Exception as e:
        logger.error(f"Memory stats error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get memory game stats")


@router.get("/stats/number-prediction")
async def get_prediction_stats(request: Request):
    """Get user's number prediction game statistics."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with get_db_session() as session:
            stats = await mini_game_manager.prediction_game.get_user_stats(session, user_id)
            
            return {
                "status": "success",
                "data": stats
            }
            
    except Exception as e:
        logger.error(f"Prediction stats error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get prediction game stats")


@router.get("/stats/puzzle-solver")
async def get_puzzle_stats(request: Request):
    """Get user's puzzle solving game statistics."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with get_db_session() as session:
            stats = await mini_game_manager.puzzle_game.get_user_stats(session, user_id)
            
            return {
                "status": "success",
                "data": stats
            }
            
    except Exception as e:
        logger.error(f"Puzzle stats error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get puzzle game stats")


@router.get("/stats/quick-math")
async def get_math_stats(request: Request):
    """Get user's quick math game statistics."""
    
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with get_db_session() as session:
            stats = await mini_game_manager.math_game.get_user_stats(session, user_id)
            
            return {
                "status": "success",
                "data": stats
            }
            
    except Exception as e:
        logger.error(f"Math stats error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get math game stats")


# ==================== DAILY CHALLENGES ====================

@router.post("/challenges/create")
async def create_daily_challenges(request: Request):
    """Create daily challenges (admin/system use)."""
    
    # This would typically be restricted to admin users
    try:
        async with get_db_session() as session:
            tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            await mini_game_manager.create_daily_challenges(session, tomorrow)
            
            return {
                "status": "success",
                "message": "Daily challenges created successfully"
            }
            
    except Exception as e:
        logger.error(f"Create challenges error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create daily challenges")