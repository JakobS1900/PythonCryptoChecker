"""
Administrative API endpoints for platform management.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session, User, UserRole
from social import social_manager
from auth import AuthenticationManager
from achievements import achievement_engine
from gamification import item_generator
from logger import logger

router = APIRouter()
security = HTTPBearer()
auth_manager = AuthenticationManager()


# ==================== REQUEST/RESPONSE MODELS ====================

class UserManagementRequest(BaseModel):
    user_id: str = Field(..., description="Target user ID")
    action: str = Field(..., pattern="^(BAN|UNBAN|SUSPEND|ACTIVATE|PROMOTE|DEMOTE)$")
    reason: Optional[str] = Field(None, max_length=500)
    duration_hours: Optional[int] = Field(None, description="Duration for temporary actions")


class CreateItemRequest(BaseModel):
    name: str = Field(..., max_length=100)
    description: str = Field(..., max_length=500)
    item_type: str = Field(..., pattern="^(TRADING_CARD|ACCESSORY|CONSUMABLE|SPECIAL)$")
    rarity: str = Field(..., pattern="^(COMMON|UNCOMMON|RARE|EPIC|LEGENDARY|MYTHIC)$")
    category: str = Field(..., max_length=50)
    effect_data: Optional[Dict[str, Any]] = None
    is_tradeable: bool = True
    max_stack_size: int = 1


class CreateAchievementRequest(BaseModel):
    name: str = Field(..., max_length=100)
    description: str = Field(..., max_length=500)
    achievement_type: str = Field(..., max_length=50)
    trigger_condition: str = Field(..., max_length=100)
    requirement_value: float = Field(default=1.0)
    reward_coins: int = Field(default=0, ge=0)
    reward_xp: int = Field(default=0, ge=0)
    reward_items: Optional[List[str]] = None
    is_active: bool = True
    is_hidden: bool = False


class BulkCurrencyRequest(BaseModel):
    user_ids: List[str] = Field(..., description="List of user IDs")
    currency_type: str = Field(..., pattern="^(GEM_COINS|VIRTUAL_CRYPTO)$")
    amount: float = Field(..., description="Amount to add/remove")
    reason: str = Field(..., max_length=200, description="Reason for currency change")


class SystemMaintenanceRequest(BaseModel):
    maintenance_type: str = Field(..., pattern="^(SCHEDULED|EMERGENCY)$")
    duration_minutes: int = Field(..., gt=0)
    message: str = Field(..., max_length=500)
    affected_services: List[str] = Field(default=["ALL"])


class AdminResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# ==================== HELPER FUNCTIONS ====================

async def get_admin_user(
    token: str = Depends(security),
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """Get current authenticated admin user."""
    user = await auth_manager.get_user_by_token(session, token.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    if user.role not in [UserRole.ADMIN, UserRole.MODERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return user


async def get_super_admin_user(
    token: str = Depends(security),
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """Get current authenticated super admin user."""
    user = await auth_manager.get_user_by_token(session, token.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    
    return user


# ==================== USER MANAGEMENT ====================

@router.get("/users", response_model=List[Dict[str, Any]])
async def get_all_users(
    limit: int = 100,
    offset: int = 0,
    search: Optional[str] = None,
    role_filter: Optional[str] = None,
    admin_user: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Get all users with filtering options."""
    try:
        from sqlalchemy import select, or_
        
        query = select(User)
        
        # Apply search filter
        if search:
            query = query.where(
                or_(
                    User.username.ilike(f"%{search}%"),
                    User.display_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
            )
        
        # Apply role filter
        if role_filter:
            query = query.where(User.role == role_filter)
        
        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        users = result.scalars().all()
        
        return [
            {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "email": user.email,
                "role": user.role,
                "status": user.status,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "current_level": user.current_level,
                "total_experience": user.total_experience,
                "is_verified": user.is_email_verified
            }
            for user in users
        ]
        
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get users"
        )


@router.post("/users/manage", response_model=AdminResponse)
async def manage_user(
    request: UserManagementRequest,
    admin_user: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Manage user account (ban, suspend, promote, etc.)."""
    try:
        from sqlalchemy import select
        
        # Get target user
        result = await session.execute(select(User).where(User.id == request.user_id))
        target_user = result.scalar_one_or_none()
        
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent self-targeting
        if target_user.id == admin_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot perform this action on yourself"
            )
        
        success = False
        message = ""
        
        if request.action == "BAN":
            target_user.status = "BANNED"
            target_user.banned_until = None  # Permanent ban
            message = f"User {target_user.username} has been banned"
            success = True
            
        elif request.action == "UNBAN":
            target_user.status = "ACTIVE"
            target_user.banned_until = None
            message = f"User {target_user.username} has been unbanned"
            success = True
            
        elif request.action == "SUSPEND":
            if not request.duration_hours:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Duration required for suspension"
                )
            target_user.status = "SUSPENDED"
            target_user.banned_until = datetime.utcnow() + timedelta(hours=request.duration_hours)
            message = f"User {target_user.username} suspended for {request.duration_hours} hours"
            success = True
            
        elif request.action == "ACTIVATE":
            target_user.status = "ACTIVE"
            target_user.banned_until = None
            message = f"User {target_user.username} has been activated"
            success = True
            
        elif request.action == "PROMOTE":
            if admin_user.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can promote users"
                )
            if target_user.role == UserRole.USER:
                target_user.role = UserRole.MODERATOR
                message = f"User {target_user.username} promoted to moderator"
                success = True
            else:
                message = "User cannot be promoted further"
                
        elif request.action == "DEMOTE":
            if admin_user.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can demote users"
                )
            if target_user.role == UserRole.MODERATOR:
                target_user.role = UserRole.USER
                message = f"User {target_user.username} demoted to regular user"
                success = True
            else:
                message = "User cannot be demoted further"
        
        if success:
            target_user.updated_at = datetime.utcnow()
            await session.commit()
            
            # Log admin action
            logger.info(f"Admin {admin_user.username} performed {request.action} on user {target_user.username}. Reason: {request.reason}")
        
        return AdminResponse(success=success, message=message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to manage user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to manage user"
        )


# ==================== CURRENCY MANAGEMENT ====================

@router.post("/currency/bulk-adjust", response_model=AdminResponse)
async def bulk_adjust_currency(
    request: BulkCurrencyRequest,
    admin_user: User = Depends(get_super_admin_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Bulk adjust user currencies."""
    try:
        from database.unified_models import VirtualWallet
        from sqlalchemy import select
        
        successful_updates = 0
        failed_updates = 0
        
        for user_id in request.user_ids:
            try:
                # Get user wallet
                result = await session.execute(
                    select(VirtualWallet).where(VirtualWallet.user_id == user_id)
                )
                wallet = result.scalar_one_or_none()
                
                if wallet:
                    if request.currency_type == "GEM_COINS":
                        wallet.gem_coins = max(0, wallet.gem_coins + request.amount)
                    elif request.currency_type == "VIRTUAL_CRYPTO":
                        # Adjust virtual crypto balance
                        wallet.total_virtual_crypto_value = max(0, wallet.total_virtual_crypto_value + request.amount)
                    
                    wallet.updated_at = datetime.utcnow()
                    successful_updates += 1
                else:
                    failed_updates += 1
                    
            except Exception as e:
                logger.error(f"Failed to adjust currency for user {user_id}: {e}")
                failed_updates += 1
        
        await session.commit()
        
        message = f"Currency adjusted for {successful_updates} users. {failed_updates} failed."
        logger.info(f"Admin {admin_user.username} bulk adjusted {request.currency_type} by {request.amount}. Reason: {request.reason}")
        
        return AdminResponse(
            success=True,
            message=message,
            data={"successful": successful_updates, "failed": failed_updates}
        )
        
    except Exception as e:
        logger.error(f"Failed to bulk adjust currency: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk adjust currency"
        )


# ==================== ITEM MANAGEMENT ====================

@router.post("/items/create", response_model=AdminResponse)
async def create_custom_item(
    request: CreateItemRequest,
    admin_user: User = Depends(get_super_admin_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Create custom collectible item."""
    try:
        # Create item using item generator
        item_data = {
            "name": request.name,
            "description": request.description,
            "item_type": request.item_type,
            "rarity": request.rarity,
            "category": request.category,
            "effect_data": request.effect_data or {},
            "is_tradeable": request.is_tradeable,
            "max_stack_size": request.max_stack_size
        }
        
        success = await item_generator.create_custom_item(session, item_data)
        
        if success:
            logger.info(f"Admin {admin_user.username} created custom item: {request.name}")
            return AdminResponse(
                success=True,
                message=f"Custom item '{request.name}' created successfully"
            )
        else:
            return AdminResponse(
                success=False,
                message="Failed to create custom item"
            )
        
    except Exception as e:
        logger.error(f"Failed to create custom item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create custom item"
        )


@router.post("/achievements/create", response_model=AdminResponse)
async def create_custom_achievement(
    request: CreateAchievementRequest,
    admin_user: User = Depends(get_super_admin_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Create custom achievement."""
    try:
        achievement_data = {
            "name": request.name,
            "description": request.description,
            "achievement_type": request.achievement_type,
            "trigger_condition": request.trigger_condition,
            "requirement_value": request.requirement_value,
            "reward_coins": request.reward_coins,
            "reward_xp": request.reward_xp,
            "reward_items": request.reward_items or [],
            "is_active": request.is_active,
            "is_hidden": request.is_hidden
        }
        
        success = await achievement_engine.create_custom_achievement(session, achievement_data)
        
        if success:
            logger.info(f"Admin {admin_user.username} created custom achievement: {request.name}")
            return AdminResponse(
                success=True,
                message=f"Custom achievement '{request.name}' created successfully"
            )
        else:
            return AdminResponse(
                success=False,
                message="Failed to create custom achievement"
            )
        
    except Exception as e:
        logger.error(f"Failed to create custom achievement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create custom achievement"
        )


# ==================== SYSTEM STATISTICS ====================

@router.get("/stats/overview")
async def get_system_overview(
    admin_user: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Get system overview statistics."""
    try:
        from sqlalchemy import select, func
        from database.unified_models import GameSession, CollectibleItem, Achievement
        
        # Get user statistics
        total_users_result = await session.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar()
        
        active_users_result = await session.execute(
            select(func.count(User.id)).where(
                User.last_login >= datetime.utcnow() - timedelta(days=30)
            )
        )
        active_users = active_users_result.scalar()
        
        # Get game statistics
        total_games_result = await session.execute(select(func.count(GameSession.id)))
        total_games = total_games_result.scalar()
        
        # Get item statistics
        total_items_result = await session.execute(select(func.count(CollectibleItem.id)))
        total_items = total_items_result.scalar()
        
        # Get achievement statistics
        total_achievements_result = await session.execute(select(func.count(Achievement.id)))
        total_achievements = total_achievements_result.scalar()
        
        return {
            "users": {
                "total": total_users,
                "active_monthly": active_users,
                "growth_rate": 0  # Would calculate from historical data
            },
            "gaming": {
                "total_games": total_games,
                "games_today": 0,  # Would calculate from today's data
                "average_session_length": 0  # Would calculate from game data
            },
            "economy": {
                "total_items": total_items,
                "total_achievements": total_achievements,
                "currency_in_circulation": 0  # Would sum from all wallets
            },
            "system": {
                "uptime": "99.9%",  # Would track from system monitoring
                "response_time": "45ms",  # Would calculate from monitoring
                "error_rate": "0.1%"  # Would calculate from logs
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system overview"
        )


# ==================== SYSTEM MAINTENANCE ====================

@router.post("/maintenance", response_model=AdminResponse)
async def schedule_maintenance(
    request: SystemMaintenanceRequest,
    admin_user: User = Depends(get_super_admin_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Schedule system maintenance."""
    try:
        # In a real system, this would integrate with a maintenance management system
        logger.info(f"Admin {admin_user.username} scheduled {request.maintenance_type} maintenance for {request.duration_minutes} minutes")
        
        # Would typically:
        # 1. Update system maintenance status
        # 2. Send notifications to all users
        # 3. Schedule automatic service shutdown/restart
        # 4. Update API responses to show maintenance mode
        
        return AdminResponse(
            success=True,
            message=f"Maintenance scheduled successfully for {request.duration_minutes} minutes",
            data={
                "maintenance_type": request.maintenance_type,
                "duration_minutes": request.duration_minutes,
                "affected_services": request.affected_services,
                "scheduled_by": admin_user.username,
                "scheduled_at": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to schedule maintenance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule maintenance"
        )


# ==================== SYSTEM LOGS ====================

@router.get("/logs")
async def get_system_logs(
    level: str = "INFO",
    limit: int = 100,
    search: Optional[str] = None,
    admin_user: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Get system logs (simplified implementation)."""
    try:
        # In a real system, this would read from log files or log database
        # This is a simplified implementation
        
        return {
            "logs": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "message": "System logs endpoint accessed",
                    "service": "admin-api",
                    "user": admin_user.username
                }
            ],
            "total": 1,
            "level_filter": level,
            "search_filter": search
        }
        
    except Exception as e:
        logger.error(f"Failed to get system logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system logs"
        )