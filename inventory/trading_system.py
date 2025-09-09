"""
Virtual item trading system for peer-to-peer exchanges.
Secure trading mechanics without real money transactions.
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import relationship

from gamification.models import CollectibleItem, UserInventory, VirtualWallet, VirtualTransaction, CurrencyType
from auth.models import User
from logger import logger

Base = declarative_base()


class TradeStatus(Enum):
    """Status of trade offers."""
    PENDING = "PENDING"         # Awaiting response
    ACCEPTED = "ACCEPTED"       # Trade completed
    DECLINED = "DECLINED"       # Trade rejected
    CANCELLED = "CANCELLED"     # Trade cancelled by initiator
    EXPIRED = "EXPIRED"         # Trade offer expired


class TradeOffer(Base):
    """Trade offer between two users."""
    __tablename__ = "trade_offers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Trade participants
    initiator_id = Column(String, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Trade details
    status = Column(String, default=TradeStatus.PENDING.value)
    gem_coins_offered = Column(Float, default=0.0)  # GEM coins offered by initiator
    gem_coins_requested = Column(Float, default=0.0)  # GEM coins requested from recipient
    
    # Metadata
    message = Column(Text)  # Optional message from initiator
    decline_reason = Column(Text)  # Reason for declining
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # Auto-decline after expiry
    responded_at = Column(DateTime)  # When recipient responded
    completed_at = Column(DateTime)  # When trade was finalized
    
    # Relationships
    offered_items = relationship("TradeOfferItem", foreign_keys="TradeOfferItem.trade_id", cascade="all, delete-orphan")
    requested_items = relationship("TradeOfferItem", foreign_keys="TradeOfferItem.trade_id", cascade="all, delete-orphan")


class TradeOfferItem(Base):
    """Items included in trade offers."""
    __tablename__ = "trade_offer_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trade_id = Column(String, ForeignKey("trade_offers.id"), nullable=False)
    
    inventory_id = Column(String, ForeignKey("user_inventory.id"), nullable=False)
    quantity = Column(Float, nullable=False, default=1)
    is_offered = Column(Boolean, nullable=False)  # True if offered, False if requested
    
    # Relationships
    inventory_item = relationship("UserInventory")


class TradingSystem:
    """Virtual item trading system manager."""
    
    def __init__(self):
        self.trade_expiry_hours = 24  # Trade offers expire after 24 hours
        self.max_active_trades = 10   # Maximum active trades per user
        self.trade_fee_percentage = 0.05  # 5% trading fee in GEM coins
    
    async def create_trade_offer(
        self,
        session: AsyncSession,
        initiator_id: str,
        recipient_id: str,
        offered_items: List[Dict[str, Any]],
        requested_items: List[Dict[str, Any]],
        gem_coins_offered: float = 0.0,
        gem_coins_requested: float = 0.0,
        message: Optional[str] = None
    ) -> str:
        """Create a new trade offer between two users."""
        
        # Validation checks
        if initiator_id == recipient_id:
            raise ValueError("Cannot trade with yourself")
        
        # Check if recipient exists
        recipient = await session.execute(select(User).where(User.id == recipient_id))
        if not recipient.scalar_one_or_none():
            raise ValueError("Recipient user not found")
        
        # Check active trade limits
        active_trades = await session.execute(
            select(TradeOffer).where(
                and_(
                    TradeOffer.initiator_id == initiator_id,
                    TradeOffer.status == TradeStatus.PENDING.value
                )
            )
        )
        if len(list(active_trades.scalars())) >= self.max_active_trades:
            raise ValueError(f"Maximum {self.max_active_trades} active trades allowed")
        
        # Validate offered items belong to initiator
        for item_data in offered_items:
            inventory_id = item_data.get("inventory_id")
            quantity = item_data.get("quantity", 1)
            
            inventory_item = await session.execute(
                select(UserInventory, CollectibleItem)
                .join(CollectibleItem, UserInventory.item_id == CollectibleItem.id)
                .where(
                    and_(
                        UserInventory.id == inventory_id,
                        UserInventory.user_id == initiator_id
                    )
                )
            )
            item_data_result = inventory_item.first()
            
            if not item_data_result:
                raise ValueError(f"Offered item {inventory_id} not found in your inventory")
            
            user_inventory, collectible = item_data_result
            
            if not collectible.is_tradeable:
                raise ValueError(f"Item '{collectible.name}' is not tradeable")
            
            if user_inventory.quantity < quantity:
                raise ValueError(f"Insufficient quantity for item '{collectible.name}'")
        
        # Validate requested items belong to recipient and are tradeable
        for item_data in requested_items:
            inventory_id = item_data.get("inventory_id")
            quantity = item_data.get("quantity", 1)
            
            inventory_item = await session.execute(
                select(UserInventory, CollectibleItem)
                .join(CollectibleItem, UserInventory.item_id == CollectibleItem.id)
                .where(
                    and_(
                        UserInventory.id == inventory_id,
                        UserInventory.user_id == recipient_id
                    )
                )
            )
            item_data_result = inventory_item.first()
            
            if not item_data_result:
                raise ValueError(f"Requested item {inventory_id} not found in recipient's inventory")
            
            user_inventory, collectible = item_data_result
            
            if not collectible.is_tradeable:
                raise ValueError(f"Requested item '{collectible.name}' is not tradeable")
            
            if user_inventory.quantity < quantity:
                raise ValueError(f"Recipient has insufficient quantity for item '{collectible.name}'")
        
        # Check GEM coin balances if applicable
        if gem_coins_offered > 0:
            initiator_wallet = await session.execute(
                select(VirtualWallet).where(VirtualWallet.user_id == initiator_id)
            )
            wallet = initiator_wallet.scalar_one_or_none()
            if not wallet or wallet.gem_coins < gem_coins_offered:
                raise ValueError("Insufficient GEM coins to offer")
        
        if gem_coins_requested > 0:
            recipient_wallet = await session.execute(
                select(VirtualWallet).where(VirtualWallet.user_id == recipient_id)
            )
            wallet = recipient_wallet.scalar_one_or_none()
            if not wallet or wallet.gem_coins < gem_coins_requested:
                raise ValueError("Recipient has insufficient GEM coins")
        
        # Create trade offer
        trade_offer = TradeOffer(
            initiator_id=initiator_id,
            recipient_id=recipient_id,
            gem_coins_offered=gem_coins_offered,
            gem_coins_requested=gem_coins_requested,
            message=message,
            expires_at=datetime.utcnow() + timedelta(hours=self.trade_expiry_hours)
        )
        
        session.add(trade_offer)
        await session.flush()  # Get the trade ID
        
        # Add offered items
        for item_data in offered_items:
            trade_item = TradeOfferItem(
                trade_id=trade_offer.id,
                inventory_id=item_data["inventory_id"],
                quantity=item_data.get("quantity", 1),
                is_offered=True
            )
            session.add(trade_item)
        
        # Add requested items
        for item_data in requested_items:
            trade_item = TradeOfferItem(
                trade_id=trade_offer.id,
                inventory_id=item_data["inventory_id"],
                quantity=item_data.get("quantity", 1),
                is_offered=False
            )
            session.add(trade_item)
        
        await session.commit()
        
        logger.info(f"Trade offer created: {trade_offer.id} from {initiator_id} to {recipient_id}")
        
        return trade_offer.id
    
    async def accept_trade_offer(
        self,
        session: AsyncSession,
        trade_id: str,
        recipient_id: str
    ) -> bool:
        """Accept a trade offer and execute the trade."""
        
        # Get trade offer with all related data
        trade_result = await session.execute(
            select(TradeOffer)
            .where(
                and_(
                    TradeOffer.id == trade_id,
                    TradeOffer.recipient_id == recipient_id,
                    TradeOffer.status == TradeStatus.PENDING.value
                )
            )
        )
        trade_offer = trade_result.scalar_one_or_none()
        
        if not trade_offer:
            raise ValueError("Trade offer not found or not available")
        
        # Check if expired
        if datetime.utcnow() > trade_offer.expires_at:
            trade_offer.status = TradeStatus.EXPIRED.value
            await session.commit()
            raise ValueError("Trade offer has expired")
        
        # Execute the trade
        try:
            # Transfer offered items to recipient
            offered_items = await session.execute(
                select(TradeOfferItem)
                .where(
                    and_(
                        TradeOfferItem.trade_id == trade_id,
                        TradeOfferItem.is_offered == True
                    )
                )
            )
            
            for trade_item in offered_items.scalars():
                await self._transfer_item(
                    session,
                    trade_item.inventory_id,
                    trade_offer.initiator_id,
                    trade_offer.recipient_id,
                    trade_item.quantity
                )
            
            # Transfer requested items to initiator
            requested_items = await session.execute(
                select(TradeOfferItem)
                .where(
                    and_(
                        TradeOfferItem.trade_id == trade_id,
                        TradeOfferItem.is_offered == False
                    )
                )
            )
            
            for trade_item in requested_items.scalars():
                await self._transfer_item(
                    session,
                    trade_item.inventory_id,
                    trade_offer.recipient_id,
                    trade_offer.initiator_id,
                    trade_item.quantity
                )
            
            # Handle GEM coin transfers
            if trade_offer.gem_coins_offered > 0:
                await self._transfer_gems(
                    session,
                    trade_offer.initiator_id,
                    trade_offer.recipient_id,
                    trade_offer.gem_coins_offered,
                    f"Trade payment for offer {trade_id}"
                )
            
            if trade_offer.gem_coins_requested > 0:
                await self._transfer_gems(
                    session,
                    trade_offer.recipient_id,
                    trade_offer.initiator_id,
                    trade_offer.gem_coins_requested,
                    f"Trade payment for offer {trade_id}"
                )
            
            # Apply trading fee (split between both parties)
            if trade_offer.gem_coins_offered > 0 or trade_offer.gem_coins_requested > 0:
                total_value = trade_offer.gem_coins_offered + trade_offer.gem_coins_requested
                trading_fee = total_value * self.trade_fee_percentage
                fee_per_party = trading_fee / 2
                
                await self._deduct_trading_fee(session, trade_offer.initiator_id, fee_per_party, trade_id)
                await self._deduct_trading_fee(session, trade_offer.recipient_id, fee_per_party, trade_id)
            
            # Update trade status
            trade_offer.status = TradeStatus.ACCEPTED.value
            trade_offer.responded_at = datetime.utcnow()
            trade_offer.completed_at = datetime.utcnow()
            
            await session.commit()
            
            logger.info(f"Trade offer {trade_id} accepted and completed")
            
            return True
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to execute trade {trade_id}: {e}")
            raise ValueError(f"Trade execution failed: {e}")
    
    async def decline_trade_offer(
        self,
        session: AsyncSession,
        trade_id: str,
        recipient_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Decline a trade offer."""
        
        trade_result = await session.execute(
            select(TradeOffer)
            .where(
                and_(
                    TradeOffer.id == trade_id,
                    TradeOffer.recipient_id == recipient_id,
                    TradeOffer.status == TradeStatus.PENDING.value
                )
            )
        )
        trade_offer = trade_result.scalar_one_or_none()
        
        if not trade_offer:
            raise ValueError("Trade offer not found or not available")
        
        trade_offer.status = TradeStatus.DECLINED.value
        trade_offer.decline_reason = reason
        trade_offer.responded_at = datetime.utcnow()
        
        await session.commit()
        
        logger.info(f"Trade offer {trade_id} declined by {recipient_id}")
        
        return True
    
    async def cancel_trade_offer(
        self,
        session: AsyncSession,
        trade_id: str,
        initiator_id: str
    ) -> bool:
        """Cancel a pending trade offer."""
        
        trade_result = await session.execute(
            select(TradeOffer)
            .where(
                and_(
                    TradeOffer.id == trade_id,
                    TradeOffer.initiator_id == initiator_id,
                    TradeOffer.status == TradeStatus.PENDING.value
                )
            )
        )
        trade_offer = trade_result.scalar_one_or_none()
        
        if not trade_offer:
            raise ValueError("Trade offer not found or cannot be cancelled")
        
        trade_offer.status = TradeStatus.CANCELLED.value
        trade_offer.responded_at = datetime.utcnow()
        
        await session.commit()
        
        logger.info(f"Trade offer {trade_id} cancelled by {initiator_id}")
        
        return True
    
    async def get_user_trade_offers(
        self,
        session: AsyncSession,
        user_id: str,
        status: Optional[TradeStatus] = None,
        as_initiator: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Get trade offers for a user."""
        
        query = select(TradeOffer).where(
            or_(
                TradeOffer.initiator_id == user_id,
                TradeOffer.recipient_id == user_id
            )
        )
        
        if status:
            query = query.where(TradeOffer.status == status.value)
        
        if as_initiator is not None:
            if as_initiator:
                query = query.where(TradeOffer.initiator_id == user_id)
            else:
                query = query.where(TradeOffer.recipient_id == user_id)
        
        query = query.order_by(TradeOffer.created_at.desc())
        
        result = await session.execute(query)
        trades = result.scalars().all()
        
        # Format response with item details
        formatted_trades = []
        for trade in trades:
            trade_data = await self._format_trade_offer(session, trade, user_id)
            formatted_trades.append(trade_data)
        
        return formatted_trades
    
    async def cleanup_expired_trades(self, session: AsyncSession) -> int:
        """Mark expired trade offers as expired."""
        
        now = datetime.utcnow()
        
        result = await session.execute(
            update(TradeOffer)
            .where(
                and_(
                    TradeOffer.expires_at < now,
                    TradeOffer.status == TradeStatus.PENDING.value
                )
            )
            .values(
                status=TradeStatus.EXPIRED.value,
                responded_at=now
            )
        )
        
        await session.commit()
        
        expired_count = result.rowcount
        logger.info(f"Marked {expired_count} trade offers as expired")
        
        return expired_count
    
    async def _transfer_item(
        self,
        session: AsyncSession,
        inventory_id: str,
        from_user_id: str,
        to_user_id: str,
        quantity: float
    ):
        """Transfer item between users."""
        
        # Get source inventory item
        source_result = await session.execute(
            select(UserInventory, CollectibleItem)
            .join(CollectibleItem, UserInventory.item_id == CollectibleItem.id)
            .where(
                and_(
                    UserInventory.id == inventory_id,
                    UserInventory.user_id == from_user_id
                )
            )
        )
        source_data = source_result.first()
        
        if not source_data:
            raise ValueError(f"Source item not found: {inventory_id}")
        
        source_inventory, collectible_item = source_data
        
        if source_inventory.quantity < quantity:
            raise ValueError(f"Insufficient quantity in source inventory")
        
        # Check if recipient already has this item
        target_result = await session.execute(
            select(UserInventory)
            .where(
                and_(
                    UserInventory.user_id == to_user_id,
                    UserInventory.item_id == collectible_item.id
                )
            )
        )
        target_inventory = target_result.scalar_one_or_none()
        
        if target_inventory:
            # Add to existing stack
            target_inventory.quantity += quantity
        else:
            # Create new inventory entry
            new_inventory = UserInventory(
                user_id=to_user_id,
                item_id=collectible_item.id,
                quantity=quantity,
                acquisition_method="trade"
            )
            session.add(new_inventory)
        
        # Remove from source
        if source_inventory.quantity == quantity:
            await session.delete(source_inventory)
        else:
            source_inventory.quantity -= quantity
    
    async def _transfer_gems(
        self,
        session: AsyncSession,
        from_user_id: str,
        to_user_id: str,
        amount: float,
        description: str
    ):
        """Transfer GEM coins between users."""
        
        # Deduct from sender
        sender_wallet = await session.execute(
            select(VirtualWallet).where(VirtualWallet.user_id == from_user_id)
        )
        sender_wallet = sender_wallet.scalar_one()
        
        if sender_wallet.gem_coins < amount:
            raise ValueError("Insufficient GEM coins")
        
        sender_old_balance = sender_wallet.gem_coins
        sender_wallet.gem_coins -= amount
        sender_wallet.total_gems_spent += amount
        
        # Add to recipient
        recipient_wallet = await session.execute(
            select(VirtualWallet).where(VirtualWallet.user_id == to_user_id)
        )
        recipient_wallet = recipient_wallet.scalar_one()
        
        recipient_old_balance = recipient_wallet.gem_coins
        recipient_wallet.gem_coins += amount
        recipient_wallet.total_gems_earned += amount
        
        # Log transactions
        sender_transaction = VirtualTransaction(
            wallet_id=sender_wallet.id,
            transaction_type="SPEND",
            currency_type=CurrencyType.GEM_COINS.value,
            amount=-amount,
            source="trade",
            description=f"Sent: {description}",
            balance_before=sender_old_balance,
            balance_after=sender_wallet.gem_coins
        )
        session.add(sender_transaction)
        
        recipient_transaction = VirtualTransaction(
            wallet_id=recipient_wallet.id,
            transaction_type="EARN",
            currency_type=CurrencyType.GEM_COINS.value,
            amount=amount,
            source="trade",
            description=f"Received: {description}",
            balance_before=recipient_old_balance,
            balance_after=recipient_wallet.gem_coins
        )
        session.add(recipient_transaction)
    
    async def _deduct_trading_fee(
        self,
        session: AsyncSession,
        user_id: str,
        fee_amount: float,
        trade_id: str
    ):
        """Deduct trading fee from user."""
        
        wallet = await session.execute(
            select(VirtualWallet).where(VirtualWallet.user_id == user_id)
        )
        wallet = wallet.scalar_one()
        
        old_balance = wallet.gem_coins
        wallet.gem_coins -= fee_amount
        wallet.total_gems_spent += fee_amount
        
        # Log transaction
        fee_transaction = VirtualTransaction(
            wallet_id=wallet.id,
            transaction_type="SPEND",
            currency_type=CurrencyType.GEM_COINS.value,
            amount=-fee_amount,
            source="trading_fee",
            description=f"Trading fee for offer {trade_id}",
            balance_before=old_balance,
            balance_after=wallet.gem_coins
        )
        session.add(fee_transaction)
    
    async def _format_trade_offer(
        self,
        session: AsyncSession,
        trade_offer: TradeOffer,
        current_user_id: str
    ) -> Dict[str, Any]:
        """Format trade offer for API response."""
        
        # Get offered items
        offered_items = await session.execute(
            select(TradeOfferItem, UserInventory, CollectibleItem)
            .join(UserInventory, TradeOfferItem.inventory_id == UserInventory.id)
            .join(CollectibleItem, UserInventory.item_id == CollectibleItem.id)
            .where(
                and_(
                    TradeOfferItem.trade_id == trade_offer.id,
                    TradeOfferItem.is_offered == True
                )
            )
        )
        
        # Get requested items
        requested_items = await session.execute(
            select(TradeOfferItem, UserInventory, CollectibleItem)
            .join(UserInventory, TradeOfferItem.inventory_id == UserInventory.id)
            .join(CollectibleItem, UserInventory.item_id == CollectibleItem.id)
            .where(
                and_(
                    TradeOfferItem.trade_id == trade_offer.id,
                    TradeOfferItem.is_offered == False
                )
            )
        )
        
        offered_items_data = []
        for trade_item, inventory, collectible in offered_items:
            offered_items_data.append({
                "inventory_id": inventory.id,
                "item_name": collectible.name,
                "item_type": collectible.item_type,
                "rarity": collectible.rarity,
                "quantity": trade_item.quantity,
                "image_url": collectible.image_url,
                "gem_value": collectible.gem_value
            })
        
        requested_items_data = []
        for trade_item, inventory, collectible in requested_items:
            requested_items_data.append({
                "inventory_id": inventory.id,
                "item_name": collectible.name,
                "item_type": collectible.item_type,
                "rarity": collectible.rarity,
                "quantity": trade_item.quantity,
                "image_url": collectible.image_url,
                "gem_value": collectible.gem_value
            })
        
        return {
            "id": trade_offer.id,
            "initiator_id": trade_offer.initiator_id,
            "recipient_id": trade_offer.recipient_id,
            "status": trade_offer.status,
            "is_initiator": current_user_id == trade_offer.initiator_id,
            "gem_coins_offered": trade_offer.gem_coins_offered,
            "gem_coins_requested": trade_offer.gem_coins_requested,
            "offered_items": offered_items_data,
            "requested_items": requested_items_data,
            "message": trade_offer.message,
            "decline_reason": trade_offer.decline_reason,
            "created_at": trade_offer.created_at.isoformat(),
            "expires_at": trade_offer.expires_at.isoformat(),
            "responded_at": trade_offer.responded_at.isoformat() if trade_offer.responded_at else None,
            "completed_at": trade_offer.completed_at.isoformat() if trade_offer.completed_at else None
        }