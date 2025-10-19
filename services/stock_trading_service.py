"""
Stock Trading Service
Handles buy and sell operations for virtual stock trading with GEM currency.
Manages transaction atomicity, fee calculations, and wallet integration.
"""

import logging
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import (
    User, Wallet, StockHolding, StockTransaction, Transaction,
    TransactionType, StockMetadata
)
from services.stock_data_service import stock_data_service

logger = logging.getLogger(__name__)


class StockTradingService:
    """Service for stock buy/sell operations."""

    # Constants
    GEM_TO_USD_RATE = 0.01  # 1 GEM = $0.01 USD
    TRANSACTION_FEE_RATE = 0.01  # 1% fee on all transactions
    MIN_FEE_GEM = 1.0  # Minimum fee of 1 GEM

    def usd_to_gem(self, usd_amount: float) -> float:
        """Convert USD to GEM. $1 = 100 GEM"""
        return usd_amount / self.GEM_TO_USD_RATE

    def gem_to_usd(self, gem_amount: float) -> float:
        """Convert GEM to USD. 100 GEM = $1"""
        return gem_amount * self.GEM_TO_USD_RATE

    def calculate_buy_cost(self, price_usd: float, quantity: float) -> Dict:
        """
        Calculate total cost in GEM for buying stocks.

        Args:
            price_usd: Stock price in USD
            quantity: Number of shares

        Returns:
            Dict with cost breakdown
        """
        # Calculate base cost in GEM
        price_gem = self.usd_to_gem(price_usd)
        subtotal_gem = price_gem * quantity

        # Calculate fee (1% of transaction)
        fee_gem = max(subtotal_gem * self.TRANSACTION_FEE_RATE, self.MIN_FEE_GEM)

        # Total cost
        total_cost_gem = subtotal_gem + fee_gem

        return {
            "price_per_share_usd": price_usd,
            "price_per_share_gem": price_gem,
            "quantity": quantity,
            "subtotal_gem": subtotal_gem,
            "fee_gem": fee_gem,
            "total_cost_gem": total_cost_gem
        }

    def calculate_sell_proceeds(self, price_usd: float, quantity: float) -> Dict:
        """
        Calculate proceeds in GEM from selling stocks.

        Args:
            price_usd: Stock price in USD
            quantity: Number of shares

        Returns:
            Dict with proceeds breakdown
        """
        # Calculate base proceeds in GEM
        price_gem = self.usd_to_gem(price_usd)
        subtotal_gem = price_gem * quantity

        # Calculate fee (1% of transaction)
        fee_gem = max(subtotal_gem * self.TRANSACTION_FEE_RATE, self.MIN_FEE_GEM)

        # Net proceeds after fee
        net_proceeds_gem = subtotal_gem - fee_gem

        return {
            "price_per_share_usd": price_usd,
            "price_per_share_gem": price_gem,
            "quantity": quantity,
            "subtotal_gem": subtotal_gem,
            "fee_gem": fee_gem,
            "net_proceeds_gem": net_proceeds_gem
        }

    async def buy_stock(
        self,
        user_id: str,
        ticker: str,
        quantity: float,
        db: AsyncSession
    ) -> Dict:
        """
        Buy stock shares.

        Process:
        1. Get current stock price
        2. Calculate total cost (price * quantity + fee)
        3. Validate user has sufficient GEM
        4. Create/update stock holding
        5. Deduct GEM from wallet
        6. Create stock transaction record
        7. Create wallet transaction record
        8. Commit atomically

        Args:
            user_id: User ID
            ticker: Stock ticker symbol
            quantity: Number of shares to buy
            db: Database session

        Returns:
            Dict with transaction details

        Raises:
            ValueError: If validation fails
        """
        try:
            # Validate inputs
            if quantity <= 0:
                raise ValueError("Quantity must be positive")

            ticker = ticker.upper()

            # Verify stock exists
            result = await db.execute(
                select(StockMetadata).where(
                    StockMetadata.ticker == ticker,
                    StockMetadata.is_active == True
                )
            )
            stock_metadata = result.scalar_one_or_none()
            if not stock_metadata:
                raise ValueError(f"Stock {ticker} not found or inactive")

            # Get current stock price
            price_data = await stock_data_service.get_stock_price(ticker, db)
            if not price_data:
                raise ValueError(f"Unable to fetch price for {ticker}")

            current_price_usd = price_data["current_price_usd"]

            # Calculate costs
            cost_breakdown = self.calculate_buy_cost(current_price_usd, quantity)
            total_cost_gem = cost_breakdown["total_cost_gem"]
            price_per_share_gem = cost_breakdown["price_per_share_gem"]
            fee_gem = cost_breakdown["fee_gem"]

            # Get user wallet
            result = await db.execute(
                select(Wallet).where(Wallet.user_id == user_id)
            )
            wallet = result.scalar_one_or_none()
            if not wallet:
                raise ValueError("Wallet not found")

            # Validate sufficient balance
            if wallet.gem_balance < total_cost_gem:
                raise ValueError(
                    f"Insufficient GEM balance. Need {total_cost_gem:.2f}, have {wallet.gem_balance:.2f}"
                )

            # Get or create stock holding
            result = await db.execute(
                select(StockHolding).where(
                    StockHolding.user_id == user_id,
                    StockHolding.ticker == ticker
                )
            )
            holding = result.scalar_one_or_none()

            if holding:
                # Update existing holding - calculate new average price
                old_total_invested = holding.total_invested_gem
                new_total_invested = old_total_invested + cost_breakdown["subtotal_gem"]

                old_quantity = holding.quantity
                new_quantity = old_quantity + quantity

                # New average buy price (excluding fees)
                new_avg_price = new_total_invested / new_quantity

                holding.quantity = new_quantity
                holding.average_buy_price_gem = new_avg_price
                holding.total_invested_gem = new_total_invested
                holding.updated_at = datetime.utcnow()
            else:
                # Create new holding
                holding = StockHolding(
                    user_id=user_id,
                    ticker=ticker,
                    quantity=quantity,
                    average_buy_price_gem=price_per_share_gem,
                    total_invested_gem=cost_breakdown["subtotal_gem"]
                )
                db.add(holding)

            # Deduct GEM from wallet
            balance_before = wallet.gem_balance
            wallet.gem_balance -= total_cost_gem
            wallet.total_wagered += total_cost_gem
            balance_after = wallet.gem_balance

            # Create stock transaction record
            stock_transaction = StockTransaction(
                user_id=user_id,
                ticker=ticker,
                transaction_type="BUY",
                quantity=quantity,
                price_per_share_gem=price_per_share_gem,
                total_amount_gem=cost_breakdown["subtotal_gem"],
                fee_gem=fee_gem,
                profit_loss_gem=None  # NULL for buys
            )
            db.add(stock_transaction)

            # Create wallet transaction record
            wallet_transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.STOCK_BUY.value,
                amount=-total_cost_gem,
                balance_before=balance_before,
                balance_after=balance_after,
                description=f"Bought {quantity} shares of {ticker} @ {price_per_share_gem:.2f} GEM/share"
            )
            db.add(wallet_transaction)

            # Link wallet transaction to stock transaction
            await db.flush()
            stock_transaction.wallet_transaction_id = wallet_transaction.id

            # Commit transaction
            await db.commit()
            await db.refresh(holding)
            await db.refresh(stock_transaction)

            logger.info(f"User {user_id} bought {quantity} shares of {ticker} for {total_cost_gem:.2f} GEM")

            return {
                "success": True,
                "transaction_id": stock_transaction.id,
                "ticker": ticker,
                "company_name": stock_metadata.company_name,
                "transaction_type": "BUY",
                "quantity": quantity,
                "price_per_share_usd": current_price_usd,
                "price_per_share_gem": price_per_share_gem,
                "subtotal_gem": cost_breakdown["subtotal_gem"],
                "fee_gem": fee_gem,
                "total_cost_gem": total_cost_gem,
                "new_balance_gem": balance_after,
                "holding": {
                    "total_quantity": holding.quantity,
                    "average_buy_price_gem": holding.average_buy_price_gem,
                    "total_invested_gem": holding.total_invested_gem
                }
            }

        except ValueError as e:
            await db.rollback()
            logger.warning(f"Buy validation failed: {e}")
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error buying stock: {e}")
            raise ValueError(f"Failed to buy stock: {str(e)}")

    async def sell_stock(
        self,
        user_id: str,
        ticker: str,
        quantity: float,
        db: AsyncSession
    ) -> Dict:
        """
        Sell stock shares.

        Process:
        1. Validate user owns sufficient shares
        2. Get current stock price
        3. Calculate proceeds (price * quantity - fee)
        4. Calculate P/L vs average buy price
        5. Update/delete stock holding
        6. Add GEM to wallet
        7. Create stock transaction record with P/L
        8. Create wallet transaction record
        9. Commit atomically

        Args:
            user_id: User ID
            ticker: Stock ticker symbol
            quantity: Number of shares to sell
            db: Database session

        Returns:
            Dict with transaction details including P/L

        Raises:
            ValueError: If validation fails
        """
        try:
            # Validate inputs
            if quantity <= 0:
                raise ValueError("Quantity must be positive")

            ticker = ticker.upper()

            # Get stock holding
            result = await db.execute(
                select(StockHolding).where(
                    StockHolding.user_id == user_id,
                    StockHolding.ticker == ticker
                )
            )
            holding = result.scalar_one_or_none()

            if not holding:
                raise ValueError(f"You don't own any {ticker} shares")

            if holding.quantity < quantity:
                raise ValueError(
                    f"Insufficient shares. You own {holding.quantity}, trying to sell {quantity}"
                )

            # Get current stock price
            price_data = await stock_data_service.get_stock_price(ticker, db)
            if not price_data:
                raise ValueError(f"Unable to fetch price for {ticker}")

            current_price_usd = price_data["current_price_usd"]

            # Calculate proceeds
            proceeds_breakdown = self.calculate_sell_proceeds(current_price_usd, quantity)
            net_proceeds_gem = proceeds_breakdown["net_proceeds_gem"]
            price_per_share_gem = proceeds_breakdown["price_per_share_gem"]
            fee_gem = proceeds_breakdown["fee_gem"]

            # Calculate profit/loss
            # Cost basis for sold shares (using average buy price)
            cost_basis = holding.average_buy_price_gem * quantity
            # Profit/loss = proceeds - cost basis
            profit_loss_gem = proceeds_breakdown["subtotal_gem"] - cost_basis

            # Get user wallet
            result = await db.execute(
                select(Wallet).where(Wallet.user_id == user_id)
            )
            wallet = result.scalar_one_or_none()
            if not wallet:
                raise ValueError("Wallet not found")

            # Update stock holding
            if holding.quantity == quantity:
                # Selling all shares - delete holding
                await db.delete(holding)
                remaining_quantity = 0
                remaining_invested = 0
            else:
                # Selling partial shares - update holding
                # Reduce quantity and total invested proportionally
                proportion_sold = quantity / holding.quantity
                invested_in_sold = holding.total_invested_gem * proportion_sold

                holding.quantity -= quantity
                holding.total_invested_gem -= invested_in_sold
                holding.updated_at = datetime.utcnow()
                remaining_quantity = holding.quantity
                remaining_invested = holding.total_invested_gem

            # Add GEM to wallet
            balance_before = wallet.gem_balance
            wallet.gem_balance += net_proceeds_gem
            wallet.total_won += max(profit_loss_gem, 0)  # Only count profits
            balance_after = wallet.gem_balance

            # Create stock transaction record
            stock_transaction = StockTransaction(
                user_id=user_id,
                ticker=ticker,
                transaction_type="SELL",
                quantity=quantity,
                price_per_share_gem=price_per_share_gem,
                total_amount_gem=proceeds_breakdown["subtotal_gem"],
                fee_gem=fee_gem,
                profit_loss_gem=profit_loss_gem
            )
            db.add(stock_transaction)

            # Create wallet transaction record
            wallet_transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.STOCK_SELL.value,
                amount=net_proceeds_gem,
                balance_before=balance_before,
                balance_after=balance_after,
                description=f"Sold {quantity} shares of {ticker} @ {price_per_share_gem:.2f} GEM/share (P/L: {profit_loss_gem:+.2f})"
            )
            db.add(wallet_transaction)

            # Link wallet transaction to stock transaction
            await db.flush()
            stock_transaction.wallet_transaction_id = wallet_transaction.id

            # Get stock metadata for response
            result = await db.execute(
                select(StockMetadata).where(StockMetadata.ticker == ticker)
            )
            stock_metadata = result.scalar_one_or_none()

            # Commit transaction
            await db.commit()
            await db.refresh(stock_transaction)

            logger.info(
                f"User {user_id} sold {quantity} shares of {ticker} for {net_proceeds_gem:.2f} GEM "
                f"(P/L: {profit_loss_gem:+.2f})"
            )

            return {
                "success": True,
                "transaction_id": stock_transaction.id,
                "ticker": ticker,
                "company_name": stock_metadata.company_name if stock_metadata else ticker,
                "transaction_type": "SELL",
                "quantity": quantity,
                "price_per_share_usd": current_price_usd,
                "price_per_share_gem": price_per_share_gem,
                "subtotal_gem": proceeds_breakdown["subtotal_gem"],
                "fee_gem": fee_gem,
                "net_proceeds_gem": net_proceeds_gem,
                "profit_loss_gem": profit_loss_gem,
                "profit_loss_pct": (profit_loss_gem / cost_basis * 100) if cost_basis > 0 else 0,
                "new_balance_gem": balance_after,
                "holding": {
                    "remaining_quantity": remaining_quantity,
                    "remaining_invested_gem": remaining_invested
                }
            }

        except ValueError as e:
            await db.rollback()
            logger.warning(f"Sell validation failed: {e}")
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error selling stock: {e}")
            raise ValueError(f"Failed to sell stock: {str(e)}")

    async def get_buy_quote(
        self,
        user_id: str,
        ticker: str,
        quantity: float,
        db: AsyncSession
    ) -> Dict:
        """
        Get a quote for buying stocks without executing the trade.

        Args:
            user_id: User ID
            ticker: Stock ticker symbol
            quantity: Number of shares
            db: Database session

        Returns:
            Dict with quote details
        """
        try:
            ticker = ticker.upper()

            # Get current stock price
            price_data = await stock_data_service.get_stock_price(ticker, db)
            if not price_data:
                raise ValueError(f"Unable to fetch price for {ticker}")

            current_price_usd = price_data["current_price_usd"]

            # Calculate costs
            cost_breakdown = self.calculate_buy_cost(current_price_usd, quantity)

            # Get user wallet balance
            result = await db.execute(
                select(Wallet).where(Wallet.user_id == user_id)
            )
            wallet = result.scalar_one_or_none()
            user_balance = wallet.gem_balance if wallet else 0

            # Get stock metadata
            result = await db.execute(
                select(StockMetadata).where(StockMetadata.ticker == ticker)
            )
            stock_metadata = result.scalar_one_or_none()

            return {
                "ticker": ticker,
                "company_name": stock_metadata.company_name if stock_metadata else ticker,
                "quantity": quantity,
                "price_per_share_usd": current_price_usd,
                "price_per_share_gem": cost_breakdown["price_per_share_gem"],
                "subtotal_gem": cost_breakdown["subtotal_gem"],
                "fee_gem": cost_breakdown["fee_gem"],
                "total_cost_gem": cost_breakdown["total_cost_gem"],
                "user_balance_gem": user_balance,
                "sufficient_funds": user_balance >= cost_breakdown["total_cost_gem"],
                "price_change_pct": price_data.get("price_change_pct", 0)
            }

        except Exception as e:
            logger.error(f"Error getting buy quote: {e}")
            raise ValueError(f"Failed to get quote: {str(e)}")


# Global instance
stock_trading_service = StockTradingService()
