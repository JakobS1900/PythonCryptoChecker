"""
Inventory API endpoints for item management and trading.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session, ItemType, ItemRarity
from inventory import InventoryManager, TradingSystem
from achievements import achievement_engine
from auth import AuthenticationManager
from logger import logger

router = APIRouter()
security = HTTPBearer()
auth_manager = AuthenticationManager()
inventory_manager = InventoryManager()
trading_system = TradingSystem()


# ==================== REQUEST/RESPONSE MODELS ====================

class InventoryFilterRequest(BaseModel):
    item_type: Optional[str] = None
    rarity: Optional[str] = None
    search_query: Optional[str] = None
    sort_by: str = Field(default="acquired_at", description="Sort field")
    sort_desc: bool = Field(default=True, description="Sort descending")
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=100)


class SellItemRequest(BaseModel):
    inventory_id: str
    quantity: int = Field(default=1, ge=1)


class TradeOfferRequest(BaseModel):
    recipient_username: str
    offered_items: List[Dict[str, Any]] = Field(default=[], description="Items to offer")
    requested_items: List[Dict[str, Any]] = Field(default=[], description="Items to request")
    gem_coins_offered: float = Field(default=0.0, ge=0)
    gem_coins_requested: float = Field(default=0.0, ge=0)
    message: Optional[str] = Field(None, max_length=500)


class TradeResponseRequest(BaseModel):
    accept: bool


# ==================== HELPER FUNCTIONS ====================

async def get_current_user_id(
    token: str = Depends(security),
    session: AsyncSession = Depends(get_db_session)
) -> str:
    """Get current authenticated user ID."""
    user = await auth_manager.get_user_by_token(session, token.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return user.id


# ==================== INVENTORY ENDPOINTS ====================

@router.get("/")
async def get_user_inventory(
    item_type: Optional[str] = None,
    rarity: Optional[str] = None,
    search_query: Optional[str] = None,
    sort_by: str = "acquired_at",
    sort_desc: bool = True,
    page: int = 1,
    per_page: int = 50,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get user's inventory with filtering and pagination."""
    try:
        # Convert string enums to enum objects
        item_type_enum = ItemType(item_type) if item_type else None
        rarity_enum = ItemRarity(rarity) if rarity else None
        
        inventory = await inventory_manager.get_user_inventory(
            session=session,
            user_id=user_id,
            item_type=item_type_enum,
            rarity=rarity_enum,
            search_query=search_query,
            sort_by=sort_by,
            sort_desc=sort_desc,
            page=page,
            per_page=per_page
        )
        
        return inventory
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get inventory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get inventory"
        )


@router.get("/summary")
async def get_inventory_summary(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get inventory summary statistics."""
    try:
        summary = await inventory_manager.get_inventory_summary(
            session=session,
            user_id=user_id
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get inventory summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get inventory summary"
        )


@router.post("/items/{inventory_id}/favorite")
async def toggle_item_favorite(
    inventory_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Toggle favorite status of inventory item."""
    try:
        is_favorite = await inventory_manager.toggle_favorite(
            session=session,
            user_id=user_id,
            inventory_id=inventory_id
        )
        
        return {
            "inventory_id": inventory_id,
            "is_favorite": is_favorite
        }
        
    except Exception as e:
        logger.error(f"Failed to toggle favorite: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/items/{inventory_id}/equip")
async def equip_cosmetic_item(
    inventory_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Equip cosmetic item."""
    try:
        success = await inventory_manager.equip_cosmetic(
            session=session,
            user_id=user_id,
            inventory_id=inventory_id
        )
        
        if success:
            return {"message": "Item equipped successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to equip item"
            )
            
    except Exception as e:
        logger.error(f"Failed to equip item: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/equipped")
async def get_equipped_items(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get all equipped cosmetic items."""
    try:
        equipped_items = await inventory_manager.get_equipped_items(
            session=session,
            user_id=user_id
        )
        
        return {"equipped_items": equipped_items}
        
    except Exception as e:
        logger.error(f"Failed to get equipped items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get equipped items"
        )


@router.post("/items/sell")
async def sell_inventory_item(
    request: SellItemRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Sell inventory item for GEM coins."""
    try:
        result = await inventory_manager.sell_item(
            session=session,
            user_id=user_id,
            inventory_id=request.inventory_id,
            quantity=request.quantity
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to sell item: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/items/{inventory_id}/use")
async def use_consumable_item(
    inventory_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Use consumable item."""
    try:
        result = await inventory_manager.use_consumable(
            session=session,
            user_id=user_id,
            inventory_id=inventory_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to use item: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== TRADING ENDPOINTS ====================

@router.post("/trades")
async def create_trade_offer(
    request: TradeOfferRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Create new trade offer."""
    try:
        # Find recipient by username
        from database import User
        from sqlalchemy import select
        
        recipient = await session.execute(
            select(User).where(User.username == request.recipient_username)
        )
        recipient = recipient.scalar_one_or_none()
        
        if not recipient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipient user not found"
            )
        
        trade_id = await trading_system.create_trade_offer(
            session=session,
            initiator_id=user_id,
            recipient_id=recipient.id,
            offered_items=request.offered_items,
            requested_items=request.requested_items,
            gem_coins_offered=request.gem_coins_offered,
            gem_coins_requested=request.gem_coins_requested,
            message=request.message
        )
        
        return {
            "trade_id": trade_id,
            "message": "Trade offer created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create trade offer: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/trades/{trade_id}/respond")
async def respond_to_trade_offer(
    trade_id: str,
    request: TradeResponseRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Accept or decline trade offer."""
    try:
        if request.accept:
            success = await trading_system.accept_trade_offer(
                session=session,
                trade_id=trade_id,
                recipient_id=user_id
            )
            
            if success:
                # Check for trading achievement
                await achievement_engine.check_user_achievements(
                    session, user_id, "trade_completed", {}
                )
                
                return {"message": "Trade offer accepted successfully"}
        else:
            success = await trading_system.decline_trade_offer(
                session=session,
                trade_id=trade_id,
                recipient_id=user_id
            )
            
            if success:
                return {"message": "Trade offer declined"}
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to respond to trade offer"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to respond to trade: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/trades/{trade_id}/cancel")
async def cancel_trade_offer(
    trade_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Cancel pending trade offer."""
    try:
        success = await trading_system.cancel_trade_offer(
            session=session,
            trade_id=trade_id,
            initiator_id=user_id
        )
        
        if success:
            return {"message": "Trade offer cancelled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel trade offer"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel trade: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/trades")
async def get_user_trades(
    status: Optional[str] = None,
    as_initiator: Optional[bool] = None,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get user's trade offers."""
    try:
        from inventory.trading_system import TradeStatus
        
        status_enum = TradeStatus(status) if status else None
        
        trades = await trading_system.get_user_trade_offers(
            session=session,
            user_id=user_id,
            status=status_enum,
            as_initiator=as_initiator
        )
        
        return {"trades": trades}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get trades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trades"
        )


# ==================== MARKETPLACE ENDPOINTS ====================

@router.get("/marketplace")
async def get_marketplace_items(
    item_type: Optional[str] = None,
    rarity: Optional[str] = None,
    search_query: Optional[str] = None,
    sort_by: str = "gem_value",
    sort_desc: bool = False,
    page: int = 1,
    per_page: int = 50,
    session: AsyncSession = Depends(get_db_session)
):
    """Get marketplace items (all available collectibles)."""
    try:
        from database import CollectibleItem
        from sqlalchemy import select, and_
        
        query = select(CollectibleItem).where(
            and_(
                CollectibleItem.is_active == True,
                CollectibleItem.is_tradeable == True
            )
        )
        
        # Apply filters
        if item_type:
            item_type_enum = ItemType(item_type)
            query = query.where(CollectibleItem.item_type == item_type_enum.value)
        
        if rarity:
            rarity_enum = ItemRarity(rarity)
            query = query.where(CollectibleItem.rarity == rarity_enum.value)
        
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.where(
                CollectibleItem.name.ilike(search_pattern) |
                CollectibleItem.description.ilike(search_pattern)
            )
        
        # Apply sorting
        sort_column = getattr(CollectibleItem, sort_by, CollectibleItem.gem_value)
        if sort_desc:
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        result = await session.execute(query)
        items = result.scalars().all()
        
        marketplace_items = []
        for item in items:
            marketplace_items.append({
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "item_type": item.item_type,
                "rarity": item.rarity,
                "image_url": item.image_url,
                "color_theme": item.color_theme,
                "gem_value": item.gem_value,
                "crypto_theme": item.crypto_theme,
                "effect_description": item.effect_description
            })
        
        return {
            "items": marketplace_items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": len(marketplace_items)
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get marketplace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get marketplace"
        )


# ==================== ITEM INFO ENDPOINTS ====================

@router.get("/items/{item_id}")
async def get_item_details(
    item_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Get detailed information about a collectible item."""
    try:
        from database import CollectibleItem
        from sqlalchemy import select
        
        result = await session.execute(
            select(CollectibleItem).where(CollectibleItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        return {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "item_type": item.item_type,
            "rarity": item.rarity,
            "image_url": item.image_url,
            "color_theme": item.color_theme,
            "animation_type": item.animation_type,
            "gem_value": item.gem_value,
            "is_tradeable": item.is_tradeable,
            "is_consumable": item.is_consumable,
            "effect_description": item.effect_description,
            "crypto_theme": item.crypto_theme,
            "release_date": item.release_date.isoformat() if item.release_date else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get item details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get item details"
        )


@router.get("/rarities")
async def get_item_rarities():
    """Get item rarity information."""
    from gamification.models import VirtualEconomyConstants
    
    return {
        "rarities": {
            "COMMON": {
                "name": "Common",
                "color": "#9CA3AF",
                "drop_rate": 70.0,
                "gem_value": 10.0
            },
            "UNCOMMON": {
                "name": "Uncommon", 
                "color": "#10B981",
                "drop_rate": 20.0,
                "gem_value": 50.0
            },
            "RARE": {
                "name": "Rare",
                "color": "#3B82F6", 
                "drop_rate": 8.0,
                "gem_value": 200.0
            },
            "EPIC": {
                "name": "Epic",
                "color": "#8B5CF6",
                "drop_rate": 1.8,
                "gem_value": 1000.0
            },
            "LEGENDARY": {
                "name": "Legendary",
                "color": "#F59E0B",
                "drop_rate": 0.2,
                "gem_value": 5000.0
            }
        },
        "drop_rates": VirtualEconomyConstants.DROP_RATES
    }