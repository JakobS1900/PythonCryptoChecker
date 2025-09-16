"""
Inventory API endpoints for item management and trading.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db_session
from database.unified_models import ItemType, ItemRarity
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


async def get_optional_user_id(
    request: Request,
    session: AsyncSession = Depends(get_db_session)
) -> Optional[str]:
    """Get user ID if authenticated, otherwise return None for demo mode."""
    try:
        # First try JWT token authentication
        auth_header = request.headers.get("Authorization")
        logger.info(f"Auth header: {auth_header}")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            logger.info(f"Extracted token: {token[:20]}...")

            if token not in ["null", "undefined", ""]:
                user = await auth_manager.get_user_by_token(session, token)
                if user:
                    logger.info(f"User found via JWT: {user.id}")
                    return user.id

        # Fallback to session-based authentication (like /api/auth/me does)
        if hasattr(request, 'session'):
            session_data = request.session
            if session_data.get("is_authenticated") and session_data.get("user_id"):
                user_id = session_data.get("user_id")
                logger.info(f"User found via session: {user_id}")
                return user_id

        logger.info("No valid authentication found - returning None for demo mode")
        return None
    except Exception as e:
        logger.error(f"Error in get_optional_user_id: {e}")
        return None


# ==================== INVENTORY ENDPOINTS ====================


@router.get("/")
async def get_user_inventory(
    request: Request,
    item_type: Optional[str] = None,
    rarity: Optional[str] = None,
    search_query: Optional[str] = None,
    sort_by: str = "acquired_at",
    sort_desc: bool = True,
    page: int = 1,
    per_page: int = 50,
    user_id: Optional[str] = Depends(get_optional_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get user's inventory with filtering and pagination."""
    try:
        # Convert string enums to enum objects
        item_type_enum = ItemType(item_type) if item_type else None
        rarity_enum = ItemRarity(rarity) if rarity else None

        if not user_id:
            # Demo mode - return sample inventory
            logger.info("Returning demo inventory for unauthenticated user")
            demo_items = [
                {
                    "id": "demo-item-1",
                    "name": "Demo Bitcoin Card",
                    "item_name": "Demo Bitcoin Card",
                    "description": "A shimmering Bitcoin-themed trading card featuring the iconic cryptocurrency logo. This collectible showcases the digital gold that started the crypto revolution.",
                    "category": "trading_cards",
                    "item_type": "TRADING_CARD",
                    "rarity": "COMMON",
                    "quantity": 1,
                    "is_favorite": False,
                    "is_equipped": False,
                    "is_tradeable": True,
                    "gem_value": 300.0,
                    "market_value": 300.0,
                    "max_stack_size": 10,
                    "acquired_at": "2025-01-14T10:00:00Z",
                    "created_at": "2025-01-14T10:00:00Z",
                    "obtained_at": "2025-01-14T10:00:00Z",
                    "demo": True
                },
                {
                    "id": "demo-item-2",
                    "name": "Demo Ethereum Badge",
                    "item_name": "Demo Ethereum Badge",
                    "description": "An elegant Ethereum-themed cosmetic badge that displays your crypto knowledge. Features the distinctive Ethereum diamond logo with a premium metallic finish.",
                    "category": "accessories",
                    "item_type": "COSMETIC",
                    "rarity": "UNCOMMON",
                    "quantity": 1,
                    "is_favorite": True,
                    "is_equipped": False,
                    "is_tradeable": True,
                    "gem_value": 750.0,
                    "market_value": 750.0,
                    "max_stack_size": 1,
                    "acquired_at": "2025-01-14T10:30:00Z",
                    "created_at": "2025-01-14T10:30:00Z",
                    "obtained_at": "2025-01-14T10:30:00Z",
                    "demo": True
                },
                {
                    "id": "demo-item-3",
                    "name": "Demo Crypto Potion",
                    "item_name": "Demo Crypto Potion",
                    "description": "A mysterious consumable potion that glows with digital energy. When used, it provides a temporary boost to your gaming performance and luck.",
                    "category": "consumables",
                    "item_type": "CONSUMABLE",
                    "rarity": "RARE",
                    "quantity": 3,
                    "is_favorite": False,
                    "is_equipped": False,
                    "is_tradeable": True,
                    "gem_value": 1500.0,
                    "market_value": 1500.0,
                    "max_stack_size": 5,
                    "acquired_at": "2025-01-14T11:00:00Z",
                    "created_at": "2025-01-14T11:00:00Z",
                    "obtained_at": "2025-01-14T11:00:00Z",
                    "demo": True
                }
            ]
            return {
                "items": demo_items,
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total": len(demo_items),
                    "total_pages": 1
                },
                "summary": {
                    "total_items": len(demo_items),
                    "total_value": 5550.0,  # 300 + 750 + (1500 * 3)
                    "unique_items": len(demo_items)
                },
                "demo_mode": True
            }

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
    request: Request,
    user_id: Optional[str] = Depends(get_optional_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get inventory summary statistics."""
    try:
        if not user_id:
            # Demo mode - return sample summary
            logger.info("Returning demo inventory summary for unauthenticated user")
            return {
                "total_items": 5,  # 1 + 1 + 3 (quantities)
                "total_value": 5550.0,  # 300 + 750 + (1500 * 3)
                "unique_items": 3,
                "by_rarity": {
                    "COMMON": 1,
                    "UNCOMMON": 1,
                    "RARE": 1,
                    "EPIC": 0,
                    "LEGENDARY": 0
                },
                "by_type": {
                    "TRADING_CARD": 1,
                    "COSMETIC": 1,
                    "CONSUMABLE": 1
                },
                "demo_mode": True
            }

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
    request: Request,
    user_id: Optional[str] = Depends(get_optional_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get all equipped cosmetic items."""
    try:
        if not user_id:
            # Demo mode - return empty equipped items
            logger.info("Returning demo equipped items for unauthenticated user")
            return {
                "equipped_items": [],
                "demo_mode": True
            }

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


@router.post("/items/{inventory_id}/sell")
async def sell_inventory_item_by_id(
    inventory_id: str,
    quantity: int = 1,
    request: Request = None,
    user_id: Optional[str] = Depends(get_optional_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Sell inventory item for GEM coins (path parameter version)."""
    try:
        if not user_id:
            # Demo mode - return mock result
            logger.info(f"Demo mode sell attempt for item {inventory_id}")
            return {
                "success": True,
                "inventory_id": inventory_id,
                "quantity_sold": quantity,
                "gem_coins_earned": 225.0,  # Mock value (75% of 300 GEM common item)
                "remaining_quantity": 0,
                "demo_mode": True,
                "message": "Demo item sold successfully (no real transaction)"
            }

        result = await inventory_manager.sell_item(
            session=session,
            user_id=user_id,
            inventory_id=inventory_id,
            quantity=quantity
        )

        return result

    except Exception as e:
        logger.error(f"Failed to sell item {inventory_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
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
    from database.unified_models import GameConstants
    
    return {
        "rarities": {
            "COMMON": {
                "name": "Common",
                "color": "#9CA3AF",
                "drop_rate": 70.0,
                "gem_value": 300.0,
                "test_marker": "UPDATED_VERSION"
            },
            "UNCOMMON": {
                "name": "Uncommon",
                "color": "#10B981",
                "drop_rate": 20.0,
                "gem_value": 750.0
            },
            "RARE": {
                "name": "Rare",
                "color": "#3B82F6",
                "drop_rate": 8.0,
                "gem_value": 1500.0
            },
            "EPIC": {
                "name": "Epic",
                "color": "#8B5CF6",
                "drop_rate": 1.8,
                "gem_value": 3000.0
            },
            "LEGENDARY": {
                "name": "Legendary",
                "color": "#F59E0B",
                "drop_rate": 0.2,
                "gem_value": 6000.0
            }
        },
        "drop_rates": GameConstants.DROP_RATES
    }


@router.get("/test-auth")
async def test_authentication(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Test endpoint to verify authentication works."""
    return {
        "success": True,
        "user_id": user_id,
        "is_demo": user_id is None,
        "auth_header": request.headers.get("Authorization", "None")
    }


@router.post("/packs/open")
async def open_item_pack(
    pack_data: dict,
    request: Request,
    user_id: Optional[str] = Depends(get_optional_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Open an item pack and award random items to user inventory."""
    try:
        pack_type = pack_data.get("pack_type", "standard")

        # Pack costs and item counts
        pack_config = {
            "standard": {"cost": 500, "items": 3, "legendary_bonus": False},
            "premium": {"cost": 1500, "items": 5, "legendary_bonus": False},
            "legendary": {"cost": 5000, "items": 7, "legendary_bonus": True}
        }

        if pack_type not in pack_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid pack type"
            )

        config = pack_config[pack_type]

        if not user_id:
            # Demo mode - return simulated results without affecting database
            mock_items = []
            for i in range(config["items"]):
                # Select random rarity based on drop rates
                import random
                rand = random.random()
                if rand < 0.02 and config["legendary_bonus"]:
                    rarity = "LEGENDARY"
                elif rand < 0.038:
                    rarity = "EPIC"
                elif rand < 0.118:
                    rarity = "RARE"
                elif rand < 0.318:
                    rarity = "UNCOMMON"
                else:
                    rarity = "COMMON"

                mock_items.append({
                    "id": f"demo-{i}",
                    "name": f"{rarity.capitalize()} Demo Item {i+1}",
                    "rarity": rarity,
                    "item_type": "TRADING_CARD",
                    "gem_value": {"COMMON": 300, "UNCOMMON": 750, "RARE": 1500, "EPIC": 3000, "LEGENDARY": 6000}[rarity],
                    "demo": True
                })

            return {
                "success": True,
                "pack_type": pack_type,
                "cost": config["cost"],
                "items": mock_items,
                "demo_mode": True
            }

        # Real mode - check balance and deduct cost
        from database.unified_models import VirtualWallet, CollectibleItem, UserInventory, GameConstants, ItemRarity

        # Get user's wallet
        wallet_result = await session.execute(
            select(VirtualWallet).where(VirtualWallet.user_id == user_id)
        )
        wallet = wallet_result.scalar_one_or_none()

        if not wallet or wallet.gem_coins < config["cost"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient GEM coins"
            )

        # Deduct cost
        wallet.gem_coins -= config["cost"]

        # Get all available items
        items_result = await session.execute(
            select(CollectibleItem).where(CollectibleItem.is_active == True)
        )
        all_items = items_result.scalars().all()

        if not all_items:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No items available in the database"
            )

        # Group items by rarity
        items_by_rarity = {}
        for item in all_items:
            if item.rarity not in items_by_rarity:
                items_by_rarity[item.rarity] = []
            items_by_rarity[item.rarity].append(item)

        # Generate random items based on drop rates
        import random
        awarded_items = []
        drop_rates = GameConstants.DROP_RATES

        for i in range(config["items"]):
            # Select rarity based on drop rates
            rand = random.random()
            cumulative = 0.0
            selected_rarity = "COMMON"  # fallback

            # Legendary pack bonus - increased legendary chance
            if config["legendary_bonus"]:
                drop_rates_adjusted = {
                    ItemRarity.COMMON: 0.50,     # Reduced from 70%
                    ItemRarity.UNCOMMON: 0.25,   # Increased from 20%
                    ItemRarity.RARE: 0.15,       # Increased from 8%
                    ItemRarity.EPIC: 0.08,       # Increased from 1.8%
                    ItemRarity.LEGENDARY: 0.02   # Increased from 0.2%
                }
            else:
                drop_rates_adjusted = drop_rates

            for rarity, rate in drop_rates_adjusted.items():
                cumulative += rate
                if rand <= cumulative:
                    selected_rarity = rarity.value
                    break

            # Select random item from that rarity
            if selected_rarity in items_by_rarity and items_by_rarity[selected_rarity]:
                selected_item = random.choice(items_by_rarity[selected_rarity])

                # Add to user inventory
                existing_result = await session.execute(
                    select(UserInventory).where(
                        and_(
                            UserInventory.user_id == user_id,
                            UserInventory.item_id == selected_item.id
                        )
                    )
                )
                existing_inventory = existing_result.scalar_one_or_none()

                if existing_inventory:
                    existing_inventory.quantity += 1
                    inventory_item = existing_inventory
                else:
                    inventory_item = UserInventory(
                        user_id=user_id,
                        item_id=selected_item.id,
                        quantity=1,
                        acquisition_method="pack_opening"
                    )
                    session.add(inventory_item)

                awarded_items.append({
                    "id": selected_item.id,
                    "name": selected_item.name,
                    "description": selected_item.description,
                    "rarity": selected_item.rarity,
                    "item_type": selected_item.item_type,
                    "gem_value": selected_item.gem_value,
                    "color_theme": selected_item.color_theme,
                    "quantity": 1
                })

        await session.commit()

        return {
            "success": True,
            "pack_type": pack_type,
            "cost": config["cost"],
            "items": awarded_items,
            "remaining_balance": wallet.gem_coins
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to open pack: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to open pack"
        )


@router.post("/packs/test-open")
async def test_open_pack_authenticated(
    pack_data: dict,
    session: AsyncSession = Depends(get_db_session)
):
    """Test pack opening with real authenticated user logic (TEMPORARY TEST ENDPOINT)."""
    try:
        # Hardcode test user for now
        user_id = "user-testuser2-1757810573"
        pack_type = pack_data.get("pack_type", "standard")

        # Pack costs and item counts
        pack_config = {
            "standard": {"cost": 500, "items": 3, "legendary_bonus": False},
            "premium": {"cost": 1500, "items": 5, "legendary_bonus": False},
            "legendary": {"cost": 5000, "items": 7, "legendary_bonus": True}
        }

        if pack_type not in pack_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid pack type"
            )

        config = pack_config[pack_type]

        # Real mode - check balance and deduct cost
        from database.unified_models import VirtualWallet, CollectibleItem, UserInventory
        from sqlalchemy import and_

        # Get user's wallet
        wallet_result = await session.execute(
            select(VirtualWallet).where(VirtualWallet.user_id == user_id)
        )
        wallet = wallet_result.scalar_one_or_none()
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User wallet not found"
            )
        if wallet.gem_coins < config["cost"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient GEM coins. Need {config['cost']}, have {wallet.gem_coins}"
            )

        # Deduct cost
        wallet.gem_coins -= config["cost"]
        logger.info(f"Deducted {config['cost']} GEM coins from user {user_id}. New balance: {wallet.gem_coins}")

        # Get all available items
        items_result = await session.execute(
            select(CollectibleItem).where(CollectibleItem.is_active == True)
        )
        all_items = items_result.scalars().all()
        if not all_items:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No items available in the database"
            )

        # Group items by rarity
        items_by_rarity = {}
        for item in all_items:
            if item.rarity not in items_by_rarity:
                items_by_rarity[item.rarity] = []
            items_by_rarity[item.rarity].append(item)

        logger.info(f"Available rarities: {list(items_by_rarity.keys())}")

        # Generate random items based on drop rates
        import random
        awarded_items = []
        drop_rates = {
            "COMMON": 0.70,
            "UNCOMMON": 0.20,
            "RARE": 0.08,
            "EPIC": 0.018,
            "LEGENDARY": 0.002
        }

        for i in range(config["items"]):
            # Select rarity based on drop rates
            rand = random.random()
            cumulative = 0.0
            selected_rarity = "COMMON"  # fallback

            # Legendary pack bonus - increased legendary chance
            if config["legendary_bonus"]:
                drop_rates_adjusted = {
                    "COMMON": 0.50,
                    "UNCOMMON": 0.25,
                    "RARE": 0.15,
                    "EPIC": 0.08,
                    "LEGENDARY": 0.02
                }
            else:
                drop_rates_adjusted = drop_rates

            for rarity, rate in drop_rates_adjusted.items():
                cumulative += rate
                if rand <= cumulative:
                    selected_rarity = rarity
                    break

            # Select random item from that rarity
            if selected_rarity in items_by_rarity and items_by_rarity[selected_rarity]:
                selected_item = random.choice(items_by_rarity[selected_rarity])
                logger.info(f"Selected {selected_rarity} item: {selected_item.name}")

                # Add to user inventory
                existing_result = await session.execute(
                    select(UserInventory).where(
                        and_(
                            UserInventory.user_id == user_id,
                            UserInventory.item_id == selected_item.id
                        )
                    )
                )
                existing_inventory = existing_result.scalar_one_or_none()

                if existing_inventory:
                    existing_inventory.quantity += 1
                    logger.info(f"Updated inventory item quantity to {existing_inventory.quantity}")
                else:
                    new_inventory = UserInventory(
                        user_id=user_id,
                        item_id=selected_item.id,
                        quantity=1,
                        acquisition_method="pack_opening"
                    )
                    session.add(new_inventory)
                    logger.info(f"Added new inventory item: {selected_item.name}")

                awarded_items.append({
                    "id": selected_item.id,
                    "name": selected_item.name,
                    "description": selected_item.description,
                    "rarity": selected_item.rarity,
                    "item_type": selected_item.item_type,
                    "gem_value": selected_item.gem_value,
                    "color_theme": selected_item.color_theme,
                    "crypto_theme": selected_item.crypto_theme,
                    "quantity": 1
                })
            else:
                logger.warning(f"No items available for rarity: {selected_rarity}")

        await session.commit()
        logger.info(f"Pack opening completed successfully. Awarded {len(awarded_items)} items.")

        return {
            "success": True,
            "pack_type": pack_type,
            "cost": config["cost"],
            "items": awarded_items,
            "remaining_balance": wallet.gem_coins,
            "user_id": user_id,
            "test_mode": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to open test pack: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to open pack: {str(e)}"
        )