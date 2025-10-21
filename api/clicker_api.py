"""
Crypto Clicker API - Enhanced gamification system with upgrades
"""
import os
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_db
from database.models import User
from services.clicker_service import ClickerService
from services.prestige_service import PrestigeService
from services.powerup_service import PowerupService

router = APIRouter()

# JWT config
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
security = HTTPBearer(auto_error=False)

# Services
clicker_service = ClickerService()
prestige_service = PrestigeService()
powerup_service = PowerupService()


async def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """Extract user ID from JWT or session"""
    user_id = None

    # Check JWT first
    if credentials and credentials.credentials:
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
        except JWTError:
            pass

    # Fallback to session
    if not user_id:
        user_id = request.session.get("user_id")

    return user_id


@router.post("/click")
async def handle_click(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Handle a click and award gems with upgrades, energy, and combos"""
    try:
        user_id = await get_current_user_id(request, credentials)

        if not user_id:
            return {
                "success": False,
                "error": "Not authenticated. Please log in to play."
            }

        # Process click through service
        result = await clicker_service.handle_click(user_id, db)

        return {
            "success": True,
            "data": result
        }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        print(f">> Error in handle_click: {e}")
        return {
            "success": False,
            "error": "An error occurred processing your click"
        }


@router.get("/stats")
async def get_clicker_stats(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get user's clicker stats and upgrade levels"""
    try:
        user_id = await get_current_user_id(request, credentials)

        if not user_id:
            return {
                "success": False,
                "error": "Not authenticated"
            }

        # Get stats
        stats = await clicker_service.get_or_create_stats(user_id, db)

        # Regenerate energy
        await clicker_service.regenerate_energy(stats, db, user_id)

        # Process auto-click rewards
        auto_rewards = await clicker_service.process_auto_click_rewards(stats, user_id, db)

        # Get user's balance from wallet
        from sqlalchemy import select
        from database.models import Wallet
        wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
        wallet = wallet_result.scalar_one_or_none()
        balance = wallet.gem_balance if wallet else 0.0

        # Get click power ranges
        from config.clicker_upgrades import get_click_reward_range, get_auto_click_info
        min_click, max_click = get_click_reward_range(stats.click_power_level)

        # Get auto-click info
        auto_info = get_auto_click_info(stats.auto_clicker_level) if stats.auto_clicker_level > 0 else None

        return {
            "success": True,
            "data": {
                "stats": {
                    "total_clicks": stats.total_clicks,
                    "total_gems_earned": stats.total_gems_earned,
                    "best_combo": stats.best_combo,
                    "mega_bonuses_hit": stats.mega_bonuses_hit,
                    "daily_streak": stats.daily_streak,
                    "current_energy": stats.current_energy,
                    "max_energy": stats.max_energy,
                    "click_power_min": min_click,
                    "click_power_max": max_click,
                    "auto_clicker_level": stats.auto_clicker_level,
                    "auto_clicker_rate": auto_info["gems_per_tick"] if auto_info else 0,
                    "auto_clicker_interval": auto_info["interval_seconds"] if auto_info else 10,
                    "auto_click_accumulated": auto_rewards
                },
                "balance": balance
            }
        }

    except Exception as e:
        print(f">> Error in get_clicker_stats: {e}")
        return {
            "success": False,
            "error": "Failed to retrieve stats"
        }


@router.post("/upgrade/{category}")
async def purchase_upgrade(
    category: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Purchase an upgrade (click_power, auto_clicker, multiplier, energy_capacity, energy_regen)"""
    try:
        user_id = await get_current_user_id(request, credentials)

        if not user_id:
            return {
                "success": False,
                "error": "Not authenticated"
            }

        # Purchase upgrade
        result = await clicker_service.purchase_upgrade(user_id, category, db)

        return {
            "success": True,
            "data": result
        }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        print(f">> Error in purchase_upgrade: {e}")
        return {
            "success": False,
            "error": "Failed to purchase upgrade"
        }


@router.get("/upgrades")
async def get_available_upgrades(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get all available upgrades and their costs"""
    try:
        user_id = await get_current_user_id(request, credentials)

        if not user_id:
            return {
                "success": False,
                "error": "Not authenticated"
            }

        # Use the clicker service method which returns the proper format
        result = await clicker_service.get_user_upgrades(user_id, db)

        return {
            "success": True,
            "data": result["upgrades"]  # Return just the upgrades dict, nested under data
        }

    except Exception as e:
        print(f">> Error in get_available_upgrades: {e}")
        return {
            "success": False,
            "error": "Failed to retrieve upgrades"
        }


# Legacy endpoint compatibility
@router.get("/balance")
async def get_balance(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's GEM balance (legacy endpoint)"""
    try:
        user_id = await get_current_user_id(request, credentials)

        if not user_id:
            return {
                "status": "error",
                "message": "Not authenticated"
            }

        # Use crypto.portfolio to get balance
        from crypto.portfolio import portfolio_manager
        balance = await portfolio_manager.get_balance(user_id, db)

        return {
            "status": "success",
            "data": {
                "gem_coins": balance,
                "total_earned": balance
            }
        }

    except Exception as e:
        print(f">> Error in get_balance: {e}")
        return {
            "status": "error",
            "message": "Failed to retrieve balance"
        }


# ============================================
# PHASE 2: PRESTIGE SYSTEM
# ============================================

@router.get("/prestige/preview")
async def prestige_preview(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get prestige preview showing PP gain if user prestiges now"""
    try:
        user_id = await get_current_user_id(request, credentials)
        if not user_id:
            return {"success": False, "error": "Not authenticated"}

        preview = await prestige_service.calculate_prestige_preview(user_id, db)
        return {"success": True, "data": preview}

    except Exception as e:
        print(f">> Error in prestige_preview: {e}")
        return {"success": False, "error": "Failed to calculate prestige preview"}


@router.post("/prestige")
async def perform_prestige(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Perform prestige - reset progress and gain PP"""
    try:
        user_id = await get_current_user_id(request, credentials)
        if not user_id:
            return {"success": False, "error": "Not authenticated"}

        success, message, data = await prestige_service.perform_prestige(user_id, db)
        return {"success": success, "message": message, "data": data}

    except Exception as e:
        print(f">> Error in perform_prestige: {e}")
        return {"success": False, "error": "Failed to prestige"}


@router.get("/prestige/shop")
async def get_prestige_shop(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get prestige shop items"""
    try:
        user_id = await get_current_user_id(request, credentials)
        if not user_id:
            return {"success": False, "error": "Not authenticated"}

        shop = await prestige_service.get_prestige_shop(user_id, db)
        return {"success": True, "data": shop}

    except Exception as e:
        print(f">> Error in get_prestige_shop: {e}")
        return {"success": False, "error": "Failed to retrieve prestige shop"}


@router.post("/prestige/shop/{item_id}")
async def purchase_prestige_item(
    item_id: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Purchase prestige shop item with PP"""
    try:
        user_id = await get_current_user_id(request, credentials)
        if not user_id:
            return {"success": False, "error": "Not authenticated"}

        success, message = await prestige_service.purchase_prestige_shop_item(user_id, item_id, db)
        return {"success": success, "message": message}

    except Exception as e:
        print(f">> Error in purchase_prestige_item: {e}")
        return {"success": False, "error": "Failed to purchase item"}


# ============================================
# PHASE 2: POWER-UPS SYSTEM
# ============================================

@router.get("/powerups")
async def get_powerups(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get all available power-ups with status"""
    try:
        user_id = await get_current_user_id(request, credentials)
        if not user_id:
            return {"success": False, "error": "Not authenticated"}

        powerups = await powerup_service.get_available_powerups(user_id, db)
        return {"success": True, "data": powerups}

    except Exception as e:
        print(f">> Error in get_powerups: {e}")
        return {"success": False, "error": "Failed to retrieve power-ups"}


@router.post("/powerups/{powerup_type}/activate")
async def activate_powerup(
    powerup_type: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Activate a power-up"""
    try:
        user_id = await get_current_user_id(request, credentials)
        if not user_id:
            return {"success": False, "error": "Not authenticated"}

        success, message, data = await powerup_service.activate_powerup(user_id, powerup_type, db)
        return {"success": success, "message": message, "data": data}

    except Exception as e:
        print(f">> Error in activate_powerup: {e}")
        return {"success": False, "error": "Failed to activate power-up"}


@router.get("/powerups/active")
async def get_active_powerups(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get currently active power-ups"""
    try:
        user_id = await get_current_user_id(request, credentials)
        if not user_id:
            return {"success": False, "error": "Not authenticated"}

        active_powerups = await powerup_service.get_active_powerups(user_id, db)

        # Format for frontend
        formatted = []
        for powerup in active_powerups:
            from datetime import datetime
            now = datetime.utcnow()
            time_remaining = 0
            if powerup.expires_at:
                time_remaining = max(0, int((powerup.expires_at - now).total_seconds()))

            formatted.append({
                "id": powerup.id,
                "type": powerup.powerup_type,
                "activated_at": powerup.activated_at.isoformat(),
                "expires_at": powerup.expires_at.isoformat() if powerup.expires_at else None,
                "time_remaining": time_remaining
            })

        return {"success": True, "data": formatted}

    except Exception as e:
        print(f">> Error in get_active_powerups: {e}")
        return {"success": False, "error": "Failed to retrieve active power-ups"}
