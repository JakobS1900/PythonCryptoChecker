"""
Virtual inventory management system for crypto gamification platform.
Handles item collection, organization, trading, and display.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload

from database.unified_models import (
    CollectibleItem, UserInventory, ItemType, ItemRarity,
    VirtualWallet, VirtualTransaction, CurrencyType, User
)
from logger import logger


class InventoryManager:
    """Core inventory management system for virtual items."""
    
    def __init__(self):
        pass
    
    async def get_user_inventory(
        self,
        session: AsyncSession,
        user_id: str,
        item_type: Optional[ItemType] = None,
        rarity: Optional[ItemRarity] = None,
        search_query: Optional[str] = None,
        sort_by: str = "acquired_at",
        sort_desc: bool = True,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """Get user's inventory with filtering, searching, and pagination."""
        
        # Build query
        query = (
            select(UserInventory, CollectibleItem)
            .join(CollectibleItem, UserInventory.item_id == CollectibleItem.id)
            .where(UserInventory.user_id == user_id)
        )
        
        # Apply filters
        if item_type:
            query = query.where(CollectibleItem.item_type == item_type.value)
        
        if rarity:
            query = query.where(CollectibleItem.rarity == rarity.value)
        
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.where(
                or_(
                    CollectibleItem.name.ilike(search_pattern),
                    CollectibleItem.description.ilike(search_pattern),
                    CollectibleItem.crypto_theme.ilike(search_pattern)
                )
            )
        
        # Apply sorting
        sort_column = getattr(UserInventory, sort_by, UserInventory.acquired_at)
        if hasattr(CollectibleItem, sort_by):
            sort_column = getattr(CollectibleItem, sort_by)
        
        if sort_desc:
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Get total count for pagination
        count_query = (
            select(func.count(UserInventory.id))
            .join(CollectibleItem, UserInventory.item_id == CollectibleItem.id)
            .where(UserInventory.user_id == user_id)
        )
        
        if item_type:
            count_query = count_query.where(CollectibleItem.item_type == item_type.value)
        if rarity:
            count_query = count_query.where(CollectibleItem.rarity == rarity.value)
        if search_query:
            search_pattern = f"%{search_query}%"
            count_query = count_query.where(
                or_(
                    CollectibleItem.name.ilike(search_pattern),
                    CollectibleItem.description.ilike(search_pattern),
                    CollectibleItem.crypto_theme.ilike(search_pattern)
                )
            )
        
        total_items = await session.execute(count_query)
        total_count = total_items.scalar()
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Execute query
        result = await session.execute(query)
        inventory_items = result.all()
        
        # Format response - flatten structure to match frontend expectations
        items = []
        for inventory_item, collectible_item in inventory_items:
            item_data = {
                # Inventory item fields
                "inventory_id": inventory_item.id,
                "quantity": inventory_item.quantity,
                "acquired_at": inventory_item.acquired_at.isoformat(),
                "acquisition_method": inventory_item.acquisition_method,
                "is_equipped": inventory_item.is_equipped,
                "is_favorite": inventory_item.is_favorite,

                # Flattened collectible item fields (frontend expects these at root level)
                "id": collectible_item.id,
                "name": collectible_item.name,
                "description": collectible_item.description,
                "item_type": collectible_item.item_type,
                "category": self._convert_item_type_to_category(collectible_item.item_type),  # Frontend expects 'category'
                "rarity": collectible_item.rarity,
                "image_url": collectible_item.image_url,
                "color_theme": collectible_item.color_theme,
                "animation_type": collectible_item.animation_type,
                "gem_value": collectible_item.gem_value,
                "is_tradeable": collectible_item.is_tradeable,
                "is_consumable": collectible_item.is_consumable,
                "effect_description": collectible_item.effect_description,
                "crypto_theme": collectible_item.crypto_theme
            }
            items.append(item_data)
        
        return {
            "items": items,
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "total": total_count,
                "total_pages": (total_count + per_page - 1) // per_page
            },
            "filters": {
                "item_type": item_type.value if item_type else None,
                "rarity": rarity.value if rarity else None,
                "search_query": search_query,
                "sort_by": sort_by,
                "sort_desc": sort_desc
            }
        }
    
    async def get_inventory_summary(
        self,
        session: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """Get summary statistics of user's inventory."""
        
        # Get total items by type
        type_counts = await session.execute(
            select(
                CollectibleItem.item_type,
                func.sum(UserInventory.quantity).label('total_quantity')
            )
            .join(UserInventory, CollectibleItem.id == UserInventory.item_id)
            .where(UserInventory.user_id == user_id)
            .group_by(CollectibleItem.item_type)
        )
        
        # Get items by rarity
        rarity_counts = await session.execute(
            select(
                CollectibleItem.rarity,
                func.sum(UserInventory.quantity).label('total_quantity')
            )
            .join(UserInventory, CollectibleItem.id == UserInventory.item_id)
            .where(UserInventory.user_id == user_id)
            .group_by(CollectibleItem.rarity)
        )
        
        # Calculate total value
        total_value = await session.execute(
            select(func.sum(CollectibleItem.gem_value * UserInventory.quantity))
            .join(UserInventory, CollectibleItem.id == UserInventory.item_id)
            .where(UserInventory.user_id == user_id)
        )
        
        # Get favorite items count
        favorites_count = await session.execute(
            select(func.count(UserInventory.id))
            .where(
                and_(
                    UserInventory.user_id == user_id,
                    UserInventory.is_favorite == True
                )
            )
        )
        
        # Get equipped items count
        equipped_count = await session.execute(
            select(func.count(UserInventory.id))
            .where(
                and_(
                    UserInventory.user_id == user_id,
                    UserInventory.is_equipped == True
                )
            )
        )
        
        # Format response
        by_type = {row.item_type: row.total_quantity for row in type_counts}
        by_rarity = {row.rarity: row.total_quantity for row in rarity_counts}
        
        return {
            "total_items": sum(by_type.values()),
            "total_value_gems": total_value.scalar() or 0,
            "favorites_count": favorites_count.scalar() or 0,
            "equipped_count": equipped_count.scalar() or 0,
            "by_type": by_type,
            "by_rarity": by_rarity,
            "completion_stats": await self._get_completion_stats(session, user_id)
        }
    
    async def toggle_favorite(
        self,
        session: AsyncSession,
        user_id: str,
        inventory_id: str
    ) -> bool:
        """Toggle favorite status of an inventory item."""
        
        # Get inventory item
        result = await session.execute(
            select(UserInventory).where(
                and_(
                    UserInventory.id == inventory_id,
                    UserInventory.user_id == user_id
                )
            )
        )
        inventory_item = result.scalar_one_or_none()
        
        if not inventory_item:
            raise ValueError("Inventory item not found")
        
        # Toggle favorite
        inventory_item.is_favorite = not inventory_item.is_favorite
        await session.commit()
        
        logger.info(f"Toggled favorite for item {inventory_id}: {inventory_item.is_favorite}")
        return inventory_item.is_favorite
    
    async def equip_cosmetic(
        self,
        session: AsyncSession,
        user_id: str,
        inventory_id: str
    ) -> bool:
        """Equip a cosmetic item (unequipping others of the same type)."""
        
        # Get inventory item with item details
        result = await session.execute(
            select(UserInventory, CollectibleItem)
            .join(CollectibleItem, UserInventory.item_id == CollectibleItem.id)
            .where(
                and_(
                    UserInventory.id == inventory_id,
                    UserInventory.user_id == user_id
                )
            )
        )
        inventory_data = result.first()
        
        if not inventory_data:
            raise ValueError("Inventory item not found")
        
        inventory_item, collectible_item = inventory_data
        
        if collectible_item.item_type != ItemType.COSMETIC.value:
            raise ValueError("Only cosmetic items can be equipped")
        
        # Unequip other items of the same cosmetic subtype
        await session.execute(
            update(UserInventory)
            .where(
                and_(
                    UserInventory.user_id == user_id,
                    UserInventory.id != inventory_id,
                    UserInventory.is_equipped == True
                )
            )
            .values(is_equipped=False)
        )
        
        # Equip the selected item
        inventory_item.is_equipped = True
        await session.commit()
        
        logger.info(f"Equipped cosmetic item {inventory_id} for user {user_id}")
        return True
    
    async def sell_item(
        self,
        session: AsyncSession,
        user_id: str,
        inventory_id: str,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """Sell inventory item back to the system for GEM coins."""
        
        # Get inventory item with collectible details
        result = await session.execute(
            select(UserInventory, CollectibleItem)
            .join(CollectibleItem, UserInventory.item_id == CollectibleItem.id)
            .where(
                and_(
                    UserInventory.id == inventory_id,
                    UserInventory.user_id == user_id
                )
            )
        )
        inventory_data = result.first()
        
        if not inventory_data:
            raise ValueError("Inventory item not found")
        
        inventory_item, collectible_item = inventory_data
        
        if not collectible_item.is_tradeable:
            raise ValueError("This item cannot be sold")
        
        if inventory_item.quantity < quantity:
            raise ValueError(f"Insufficient quantity. You have {inventory_item.quantity}, trying to sell {quantity}")
        
        # Calculate sell value (75% of original value)
        sell_price_per_item = collectible_item.gem_value * 0.75
        total_sell_price = sell_price_per_item * quantity
        
        # Update inventory quantity
        if inventory_item.quantity == quantity:
            # Remove item entirely
            await session.delete(inventory_item)
        else:
            # Reduce quantity
            inventory_item.quantity -= quantity
        
        # Add GEM coins to user wallet
        wallet_result = await session.execute(
            select(VirtualWallet).where(VirtualWallet.user_id == user_id)
        )
        wallet = wallet_result.scalar_one_or_none()
        
        if wallet:
            old_balance = wallet.gem_coins
            wallet.gem_coins += total_sell_price
            wallet.total_gems_earned += total_sell_price
            wallet.updated_at = datetime.utcnow()
            
            # Log transaction
            transaction = VirtualTransaction(
                wallet_id=wallet.id,
                transaction_type="EARN",
                currency_type=CurrencyType.GEM_COINS.value,
                amount=total_sell_price,
                source="item_sale",
                description=f"Sold {quantity}x {collectible_item.name}",
                reference_id=inventory_id,
                balance_before=old_balance,
                balance_after=wallet.gem_coins
            )
            session.add(transaction)
        
        await session.commit()
        
        logger.info(f"User {user_id} sold {quantity}x {collectible_item.name} for {total_sell_price} GEM coins")
        
        return {
            "item_name": collectible_item.name,
            "quantity_sold": quantity,
            "gems_earned": total_sell_price,
            "remaining_quantity": inventory_item.quantity if inventory_item.quantity > 0 else 0
        }
    
    async def use_consumable(
        self,
        session: AsyncSession,
        user_id: str,
        inventory_id: str
    ) -> Dict[str, Any]:
        """Use a consumable item and apply its effects."""
        
        # Get inventory item with collectible details
        result = await session.execute(
            select(UserInventory, CollectibleItem)
            .join(CollectibleItem, UserInventory.item_id == CollectibleItem.id)
            .where(
                and_(
                    UserInventory.id == inventory_id,
                    UserInventory.user_id == user_id
                )
            )
        )
        inventory_data = result.first()
        
        if not inventory_data:
            raise ValueError("Inventory item not found")
        
        inventory_item, collectible_item = inventory_data
        
        if not collectible_item.is_consumable:
            raise ValueError("This item is not consumable")
        
        if inventory_item.quantity < 1:
            raise ValueError("No items available to use")
        
        # Apply item effects based on item name/type
        effect_result = await self._apply_consumable_effect(session, user_id, collectible_item)
        
        # Reduce quantity
        if inventory_item.quantity == 1:
            await session.delete(inventory_item)
        else:
            inventory_item.quantity -= 1
        
        await session.commit()
        
        logger.info(f"User {user_id} used consumable {collectible_item.name}")
        
        return {
            "item_name": collectible_item.name,
            "effect_applied": effect_result,
            "remaining_quantity": inventory_item.quantity - 1 if inventory_item.quantity > 1 else 0
        }
    
    async def get_equipped_items(
        self,
        session: AsyncSession,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get all equipped cosmetic items for a user."""
        
        result = await session.execute(
            select(UserInventory, CollectibleItem)
            .join(CollectibleItem, UserInventory.item_id == CollectibleItem.id)
            .where(
                and_(
                    UserInventory.user_id == user_id,
                    UserInventory.is_equipped == True
                )
            )
        )
        
        equipped_items = []
        for inventory_item, collectible_item in result:
            equipped_items.append({
                "inventory_id": inventory_item.id,
                "item_id": collectible_item.id,
                "name": collectible_item.name,
                "item_type": collectible_item.item_type,
                "image_url": collectible_item.image_url,
                "color_theme": collectible_item.color_theme,
                "animation_type": collectible_item.animation_type,
                "effect_description": collectible_item.effect_description
            })
        
        return equipped_items
    
    async def _get_completion_stats(
        self,
        session: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """Calculate collection completion statistics."""
        
        # Get total available items by type
        total_available = await session.execute(
            select(
                CollectibleItem.item_type,
                func.count(CollectibleItem.id).label('total')
            )
            .where(CollectibleItem.is_active == True)
            .group_by(CollectibleItem.item_type)
        )
        
        # Get user's collected items by type  
        user_collected = await session.execute(
            select(
                CollectibleItem.item_type,
                func.count(func.distinct(CollectibleItem.id)).label('collected')
            )
            .join(UserInventory, CollectibleItem.id == UserInventory.item_id)
            .where(
                and_(
                    UserInventory.user_id == user_id,
                    CollectibleItem.is_active == True
                )
            )
            .group_by(CollectibleItem.item_type)
        )
        
        available_dict = {row.item_type: row.total for row in total_available}
        collected_dict = {row.item_type: row.collected for row in user_collected}
        
        completion_stats = {}
        for item_type, total in available_dict.items():
            collected = collected_dict.get(item_type, 0)
            completion_stats[item_type] = {
                "collected": collected,
                "total": total,
                "percentage": (collected / total * 100) if total > 0 else 0
            }
        
        return completion_stats
    
    async def _apply_consumable_effect(
        self,
        session: AsyncSession,
        user_id: str,
        consumable_item: CollectibleItem
    ) -> str:
        """Apply effects from consumable items."""
        from database.unified_models import ActiveEffect
        from datetime import datetime, timedelta
        name = (consumable_item.name or "").lower()

        # Helper to add effect
        async def add_effect(effect_type: str, multiplier: float = 1.0, minutes: int = 0, uses: int = None, scope: str = "TRADING") -> str:
            expires_at = (datetime.utcnow() + timedelta(minutes=minutes)) if minutes > 0 else None
            effect = ActiveEffect(
                user_id=user_id,
                effect_type=effect_type,
                multiplier=multiplier,
                remaining_uses=uses,
                scope=scope,
                expires_at=expires_at,
                source_item_id=consumable_item.id
            )
            session.add(effect)
            await session.commit()
            if uses:
                return f"{effect_type} active: {uses} uses"
            if minutes > 0:
                return f"{effect_type} active for {minutes} minutes"
            return f"{effect_type} activated"

        if "lucky charm" in name or "lucky_charm" in name:
            return await add_effect("DROP_RATE", multiplier=1.25, minutes=60, scope="TRADING")
        elif "xp booster" in name or "xp_boost" in name:
            return await add_effect("XP_MULT", multiplier=2.0, minutes=30, scope="TRADING")
        elif "gem multiplier" in name or "gem_multi" in name:
            return await add_effect("GEM_MULT", multiplier=1.5, minutes=60, scope="TRADING")
        elif "golden touch" in name or "golden_touch" in name:
            return await add_effect("GUARANTEED_RARE", uses=5, scope="TRADING")
        else:
            return f"Applied {consumable_item.name} effect"

    def _convert_item_type_to_category(self, item_type: str) -> str:
        """Convert ItemType enum to frontend category string."""
        type_to_category = {
            "TRADING_CARD": "trading_cards",
            "COLLECTIBLE": "collectibles",
            "COSMETIC": "cosmetics",
            "CONSUMABLE": "consumables",
            "EQUIPMENT": "equipment",
            "SPECIAL": "special"
        }
        return type_to_category.get(item_type, "collectibles")
