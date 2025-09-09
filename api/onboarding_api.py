"""
Onboarding and tutorial API endpoints.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from database.database_manager import get_db_session
from auth.auth_manager import get_current_user
from onboarding.onboarding_manager import onboarding_manager
from onboarding.tutorial_system import tutorial_system
from logger import logger

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


# ==================== PYDANTIC MODELS ====================

class OnboardingStepResponse(BaseModel):
    """Response for onboarding step information."""
    step_id: str
    step_name: str
    title: str
    description: str
    requirements: list
    rewards: dict
    is_completed: bool
    is_current: bool


class TutorialStepRequest(BaseModel):
    """Request to complete a tutorial step."""
    step_id: str
    validation_data: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SkipStepRequest(BaseModel):
    """Request to skip a tutorial step."""
    step_id: str
    reason: Optional[str] = None


class OnboardingProgressResponse(BaseModel):
    """Response with complete onboarding progress."""
    onboarding_started: bool
    onboarding_completed: bool
    tutorial_started: bool
    tutorial_completed: bool
    current_onboarding_step: Optional[int]
    current_tutorial_step: Optional[str]
    completion_percentage: float
    rewards_earned: dict


# ==================== ONBOARDING ENDPOINTS ====================

@router.post("/start", response_model=Dict[str, Any])
async def start_onboarding(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Start the onboarding process for a new user."""
    try:
        result = await onboarding_manager.start_onboarding(db, current_user.id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to start onboarding")
            )
        
        return {
            "success": True,
            "message": "Onboarding started successfully",
            "onboarding_id": result.get("onboarding_id"),
            "current_step": result.get("current_step"),
            "total_steps": result.get("total_steps")
        }
        
    except Exception as e:
        logger.error(f"Failed to start onboarding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/progress", response_model=OnboardingProgressResponse)
async def get_onboarding_progress(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get user's complete onboarding and tutorial progress."""
    try:
        # Get onboarding progress
        onboarding_result = await onboarding_manager.get_onboarding_status(db, current_user.id)
        
        # Get tutorial progress
        tutorial_result = await tutorial_system.get_tutorial_progress(db, current_user.id)
        
        return OnboardingProgressResponse(
            onboarding_started=onboarding_result.get("onboarding_started", False),
            onboarding_completed=onboarding_result.get("onboarding_completed", False),
            tutorial_started=tutorial_result.get("tutorial_started", False),
            tutorial_completed=tutorial_result.get("completed", False),
            current_onboarding_step=onboarding_result.get("current_step"),
            current_tutorial_step=tutorial_result.get("current_step"),
            completion_percentage=max(
                onboarding_result.get("progress", {}).get("completion_percentage", 0),
                tutorial_result.get("progress", {}).get("progress_percentage", 0)
            ),
            rewards_earned=onboarding_result.get("rewards_earned", {})
        )
        
    except Exception as e:
        logger.error(f"Failed to get onboarding progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/current-step", response_model=Dict[str, Any])
async def get_current_onboarding_step(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get details about the user's current onboarding step."""
    try:
        result = await onboarding_manager.get_current_step(db, current_user.id)
        
        if not result["success"]:
            return {
                "success": False,
                "message": result.get("error", "No active onboarding found")
            }
        
        return {
            "success": True,
            "current_step": result["current_step"],
            "step_info": result["step_info"],
            "progress": result.get("progress", {}),
            "can_skip": result.get("can_skip", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to get current onboarding step: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/complete-step", response_model=Dict[str, Any])
async def complete_onboarding_step(
    step_number: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Complete the current onboarding step."""
    try:
        result = await onboarding_manager.complete_step(db, current_user.id, step_number)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to complete step")
            )
        
        return {
            "success": True,
            "message": f"Step {step_number} completed successfully",
            "rewards": result.get("rewards", {}),
            "next_step": result.get("next_step"),
            "onboarding_completed": result.get("onboarding_completed", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to complete onboarding step: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/skip-step", response_model=Dict[str, Any])
async def skip_onboarding_step(
    step_number: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Skip the current onboarding step."""
    try:
        result = await onboarding_manager.skip_step(db, current_user.id, step_number)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to skip step")
            )
        
        return {
            "success": True,
            "message": f"Step {step_number} skipped",
            "next_step": result.get("next_step"),
            "onboarding_completed": result.get("onboarding_completed", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to skip onboarding step: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ==================== TUTORIAL ENDPOINTS ====================

@router.post("/tutorial/start", response_model=Dict[str, Any])
async def start_tutorial(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Start the interactive tutorial."""
    try:
        result = await tutorial_system.start_tutorial(db, current_user.id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to start tutorial")
            )
        
        return {
            "success": True,
            "message": result.get("message", "Tutorial started"),
            "current_step": result.get("current_step"),
            "step_info": result.get("step_info")
        }
        
    except Exception as e:
        logger.error(f"Failed to start tutorial: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/tutorial/current-step", response_model=Dict[str, Any])
async def get_current_tutorial_step(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get user's current tutorial step."""
    try:
        result = await tutorial_system.get_current_step(db, current_user.id)
        
        return {
            "success": result.get("success", False),
            "current_step": result.get("current_step"),
            "step_info": result.get("step_info", {}),
            "progress": result.get("progress", {}),
            "completed": result.get("completed", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to get current tutorial step: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/tutorial/complete-step", response_model=Dict[str, Any])
async def complete_tutorial_step(
    request: TutorialStepRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Complete a tutorial step."""
    try:
        result = await tutorial_system.complete_step(
            db, current_user.id, request.step_id, request.validation_data
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to complete tutorial step")
            )
        
        return {
            "success": True,
            "step_completed": result.get("step_completed"),
            "rewards": result.get("rewards", {}),
            "next_step": result.get("next_step"),
            "next_step_info": result.get("next_step_info", {}),
            "tutorial_completed": result.get("tutorial_completed", False)
        }
        
    except Exception as e:
        logger.error(f"Failed to complete tutorial step: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/tutorial/skip-step", response_model=Dict[str, Any])
async def skip_tutorial_step(
    request: SkipStepRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Skip a tutorial step (with reduced rewards)."""
    try:
        result = await tutorial_system.skip_step(db, current_user.id, request.step_id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to skip tutorial step")
            )
        
        return {
            "success": True,
            "step_skipped": result.get("step_skipped"),
            "rewards": result.get("rewards", {}),
            "next_step": result.get("next_step"),
            "next_step_info": result.get("next_step_info", {})
        }
        
    except Exception as e:
        logger.error(f"Failed to skip tutorial step: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/tutorial/progress", response_model=Dict[str, Any])
async def get_tutorial_progress(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get comprehensive tutorial progress."""
    try:
        result = await tutorial_system.get_tutorial_progress(db, current_user.id)
        
        return {
            "success": True,
            "progress": result
        }
        
    except Exception as e:
        logger.error(f"Failed to get tutorial progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/tutorial/reset", response_model=Dict[str, Any])
async def reset_tutorial(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Reset tutorial progress (admin function or for testing)."""
    try:
        result = await tutorial_system.reset_tutorial(db, current_user.id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to reset tutorial")
            )
        
        return {
            "success": True,
            "message": "Tutorial progress reset successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to reset tutorial: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ==================== UTILITY ENDPOINTS ====================

@router.get("/steps/list", response_model=Dict[str, Any])
async def list_onboarding_steps():
    """Get list of all onboarding steps."""
    try:
        steps = await onboarding_manager.get_all_steps()
        return {
            "success": True,
            "steps": steps
        }
        
    except Exception as e:
        logger.error(f"Failed to list onboarding steps: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/tutorial/steps/list", response_model=Dict[str, Any])
async def list_tutorial_steps():
    """Get list of all tutorial steps."""
    try:
        steps = {}
        for step_id, step in tutorial_system.tutorial_steps.items():
            steps[step_id] = await tutorial_system.get_step_info(step_id)
        
        return {
            "success": True,
            "steps": steps
        }
        
    except Exception as e:
        logger.error(f"Failed to list tutorial steps: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/status", response_model=Dict[str, Any])
async def get_onboarding_status(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get complete onboarding and tutorial status."""
    try:
        onboarding_status = await onboarding_manager.get_onboarding_status(db, current_user.id)
        tutorial_progress = await tutorial_system.get_tutorial_progress(db, current_user.id)
        
        return {
            "success": True,
            "user_id": current_user.id,
            "onboarding": onboarding_status,
            "tutorial": tutorial_progress
        }
        
    except Exception as e:
        logger.error(f"Failed to get onboarding status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )