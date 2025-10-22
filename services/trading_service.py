"""
GEM P2P Trading Service

Handles order creation, matching, and trade execution.
"""

from datetime import datetime
from typing import List, Tuple, Optional
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import (
    GemTradeOrder, GemTrade, User, Transaction,
    TransactionType
)
import uuid


class TradingService:
    """Service for handling P2P GEM trading operations."""

    # Trading fee (2% of trade value)
    TRADING_FEE_PERCENT = 2.0

    @staticmethod
    async def create_order(
        user_id: str,
        order_type: str,
        price: int,
        amount: int,
        db: AsyncSession
    ) -> Tuple[bool, str, Optional[GemTradeOrder]]:
        """
        Create a new buy or sell order.

        Args:
            user_id: User ID creating the order
            order_type: 'buy' or 'sell'
            price: Price per GEM
            amount: Amount of GEM
            db: Database session

        Returns:
            (success, message, order_object)
        """
        try:
            # Validate order type
            if order_type not in ['buy', 'sell']:
                return False, "Invalid order type. Must be 'buy' or 'sell'", None

            # Validate price and amount
            if price <= 0:
                return False, "Price must be greater than 0", None
            if amount <= 0:
                return False, "Amount must be greater than 0", None

            # Get user
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return False, "User not found", None

            # Check user has enough GEM/balance
            if order_type == 'sell':
                # Selling: Need GEM
                if user.gem_balance < amount:
                    return False, f"Insufficient GEM. You have {user.gem_balance} GEM but need {amount} GEM", None

                # Lock GEM (deduct from balance)
                user.gem_balance -= amount

            elif order_type == 'buy':
                # Buying: Need virtual currency (using GEM as currency for now)
                total_cost = price * amount
                fee = int(total_cost * TradingService.TRADING_FEE_PERCENT / 100)
                total_with_fee = total_cost + fee

                if user.gem_balance < total_with_fee:
                    return False, f"Insufficient GEM. You need {total_with_fee} GEM (including {fee} GEM fee)", None

                # Lock GEM for purchase
                user.gem_balance -= total_with_fee

            # Create order
            order = GemTradeOrder(
                user_id=user_id,
                order_type=order_type,
                price=price,
                amount=amount,
                filled_amount=0,
                status='active'
            )

            db.add(order)
            await db.commit()
            await db.refresh(order)

            # Try to match order immediately
            await TradingService._match_orders(order.id, db)

            # Refresh order to get updated status
            await db.refresh(order)

            return True, f"{order_type.capitalize()} order created successfully", order

        except Exception as e:
            await db.rollback()
            return False, f"Error creating order: {str(e)}", None

    @staticmethod
    async def _match_orders(order_id: int, db: AsyncSession):
        """
        Match a new order with existing orders in the order book.

        This implements a simple matching algorithm:
        - Buy orders match with sell orders at or below their price
        - Sell orders match with buy orders at or above their price
        - Orders are matched in price-time priority
        """
        # Get the order
        result = await db.execute(
            select(GemTradeOrder).where(GemTradeOrder.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order or order.status not in ['active', 'partial']:
            return

        remaining_amount = order.amount - order.filled_amount

        if order.order_type == 'buy':
            # Match buy order with sell orders
            # Find sell orders at or below buy price, ordered by price (lowest first), then time
            result = await db.execute(
                select(GemTradeOrder)
                .where(
                    and_(
                        GemTradeOrder.order_type == 'sell',
                        GemTradeOrder.status.in_(['active', 'partial']),
                        GemTradeOrder.price <= order.price,
                        GemTradeOrder.user_id != order.user_id  # Can't trade with yourself
                    )
                )
                .order_by(GemTradeOrder.price, GemTradeOrder.created_at)
            )
            matching_orders = result.scalars().all()

        else:  # sell order
            # Match sell order with buy orders
            # Find buy orders at or above sell price, ordered by price (highest first), then time
            result = await db.execute(
                select(GemTradeOrder)
                .where(
                    and_(
                        GemTradeOrder.order_type == 'buy',
                        GemTradeOrder.status.in_(['active', 'partial']),
                        GemTradeOrder.price >= order.price,
                        GemTradeOrder.user_id != order.user_id
                    )
                )
                .order_by(desc(GemTradeOrder.price), GemTradeOrder.created_at)
            )
            matching_orders = result.scalars().all()

        # Execute matches
        for matching_order in matching_orders:
            if remaining_amount <= 0:
                break

            matching_remaining = matching_order.amount - matching_order.filled_amount
            trade_amount = min(remaining_amount, matching_remaining)
            trade_price = matching_order.price  # Price of the resting order

            # Execute the trade
            if order.order_type == 'buy':
                buyer_id = order.user_id
                seller_id = matching_order.user_id
            else:
                buyer_id = matching_order.user_id
                seller_id = order.user_id

            await TradingService._execute_trade(
                buyer_id=buyer_id,
                seller_id=seller_id,
                order_id=matching_order.id,
                price=trade_price,
                amount=trade_amount,
                db=db
            )

            # Update orders
            order.filled_amount += trade_amount
            matching_order.filled_amount += trade_amount
            remaining_amount -= trade_amount

            # Update order statuses
            if order.filled_amount >= order.amount:
                order.status = 'filled'
                order.filled_at = datetime.utcnow()
            elif order.filled_amount > 0:
                order.status = 'partial'

            if matching_order.filled_amount >= matching_order.amount:
                matching_order.status = 'filled'
                matching_order.filled_at = datetime.utcnow()
            elif matching_order.filled_amount > 0:
                matching_order.status = 'partial'

        await db.commit()

    @staticmethod
    async def _execute_trade(
        buyer_id: str,
        seller_id: str,
        order_id: int,
        price: int,
        amount: int,
        db: AsyncSession
    ):
        """Execute a trade between buyer and seller."""
        total_value = price * amount
        fee = int(total_value * TradingService.TRADING_FEE_PERCENT / 100)

        # Get buyer and seller
        result = await db.execute(select(User).where(User.id == buyer_id))
        buyer = result.scalar_one()

        result = await db.execute(select(User).where(User.id == seller_id))
        seller = result.scalar_one()

        # Transfer GEM from seller to buyer
        buyer.gem_balance += amount

        # Transfer currency from buyer to seller (minus fee)
        seller.gem_balance += (total_value - fee)

        # Create trade record
        trade = GemTrade(
            buyer_id=buyer_id,
            seller_id=seller_id,
            order_id=order_id,
            price=price,
            amount=amount,
            total_value=total_value,
            fee=fee
        )
        db.add(trade)

        # Create transaction records
        # Buyer receives GEM
        buyer_tx = Transaction(
            id=str(uuid.uuid4()),
            user_id=buyer_id,
            transaction_type=TransactionType.TRADE_BUY.value,
            amount=amount,
            description=f"Bought {amount} GEM at {price} per GEM (Trade #{trade.id})"
        )
        db.add(buyer_tx)

        # Seller receives currency
        seller_tx = Transaction(
            id=str(uuid.uuid4()),
            user_id=seller_id,
            transaction_type=TransactionType.TRADE_SELL.value,
            amount=total_value - fee,
            description=f"Sold {amount} GEM at {price} per GEM (Trade #{trade.id})"
        )
        db.add(seller_tx)

        # Fee transaction
        if fee > 0:
            fee_tx = Transaction(
                id=str(uuid.uuid4()),
                user_id=seller_id,
                transaction_type=TransactionType.TRADE_FEE.value,
                amount=-fee,
                description=f"Trading fee for selling {amount} GEM"
            )
            db.add(fee_tx)

    @staticmethod
    async def cancel_order(
        order_id: int,
        user_id: str,
        db: AsyncSession
    ) -> Tuple[bool, str]:
        """Cancel an active order and return locked funds."""
        try:
            # Get order
            result = await db.execute(
                select(GemTradeOrder).where(
                    and_(
                        GemTradeOrder.id == order_id,
                        GemTradeOrder.user_id == user_id
                    )
                )
            )
            order = result.scalar_one_or_none()

            if not order:
                return False, "Order not found or you don't own this order"

            if order.status not in ['active', 'partial']:
                return False, f"Cannot cancel order with status '{order.status}'"

            # Calculate amount to return
            unfilled_amount = order.amount - order.filled_amount

            # Get user
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one()

            # Return locked funds
            if order.order_type == 'sell':
                # Return unsold GEM
                user.gem_balance += unfilled_amount
            else:  # buy order
                # Return unused currency
                total_cost = order.price * unfilled_amount
                fee = int(total_cost * TradingService.TRADING_FEE_PERCENT / 100)
                user.gem_balance += (total_cost + fee)

            # Update order status
            order.status = 'cancelled'
            order.cancelled_at = datetime.utcnow()

            await db.commit()

            return True, "Order cancelled successfully"

        except Exception as e:
            await db.rollback()
            return False, f"Error cancelling order: {str(e)}"

    @staticmethod
    async def get_order_book(db: AsyncSession, limit: int = 20) -> dict:
        """
        Get current order book (active buy and sell orders).

        Returns dict with 'buy_orders' and 'sell_orders' sorted by price.
        """
        # Get active buy orders (sorted by price descending - highest first)
        result = await db.execute(
            select(GemTradeOrder)
            .where(
                and_(
                    GemTradeOrder.order_type == 'buy',
                    GemTradeOrder.status.in_(['active', 'partial'])
                )
            )
            .order_by(desc(GemTradeOrder.price))
            .limit(limit)
        )
        buy_orders = result.scalars().all()

        # Get active sell orders (sorted by price ascending - lowest first)
        result = await db.execute(
            select(GemTradeOrder)
            .where(
                and_(
                    GemTradeOrder.order_type == 'sell',
                    GemTradeOrder.status.in_(['active', 'partial'])
                )
            )
            .order_by(GemTradeOrder.price)
            .limit(limit)
        )
        sell_orders = result.scalars().all()

        return {
            'buy_orders': buy_orders,
            'sell_orders': sell_orders
        }

    @staticmethod
    async def get_user_orders(
        user_id: str,
        db: AsyncSession,
        status: Optional[str] = None
    ) -> List[GemTradeOrder]:
        """Get user's orders, optionally filtered by status."""
        query = select(GemTradeOrder).where(GemTradeOrder.user_id == user_id)

        if status:
            query = query.where(GemTradeOrder.status == status)

        query = query.order_by(desc(GemTradeOrder.created_at))

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_recent_trades(db: AsyncSession, limit: int = 50) -> List[GemTrade]:
        """Get recent completed trades for market history."""
        result = await db.execute(
            select(GemTrade)
            .order_by(desc(GemTrade.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_user_trade_history(
        user_id: str,
        db: AsyncSession,
        limit: int = 50
    ) -> List[GemTrade]:
        """Get user's trade history (both buying and selling)."""
        result = await db.execute(
            select(GemTrade)
            .where(
                or_(
                    GemTrade.buyer_id == user_id,
                    GemTrade.seller_id == user_id
                )
            )
            .order_by(desc(GemTrade.created_at))
            .limit(limit)
        )
        return result.scalars().all()
