"""
Crypto Trading Service
Handles buy and sell operations for cryptocurrency trading with GEM currency.
Manages transaction atomicity, fee calculations, and wallet integration.
"""

import logging
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import (
    User, Wallet, PortfolioHolding, CryptoTransaction, Transaction,
    TransactionType, CryptoCurrency
)
from crypto.price_service import price_service

logger = logging.getLogger(__name__)


class CryptoTradingService:
    """Service for crypto buy/sell operations."""

    # Constants
    GEM_TO_USD_RATE = 0.01  # 1 GEM = $0.01 USD
    TRANSACTION_FEE_RATE = 0.04  # 4% fee on all transactions
    MIN_FEE_GEM = 1.0  # Minimum fee of 1 GEM

    def usd_to_gem(self, usd_amount: float) -> float:
        """Convert USD to GEM. $1 = 100 GEM"""
        return usd_amount / self.GEM_TO_USD_RATE

    def gem_to_usd(self, gem_amount: float) -> float:
        """Convert GEM to USD. 100 GEM = $1"""
        return gem_amount * self.GEM_TO_USD_RATE

    def calculate_buy_cost(self, price_usd: float, quantity: float) -> Dict:
        """
        Calculate total cost in GEM for buying crypto.

        Args:
            price_usd: Crypto price in USD
            quantity: Amount of crypto to buy

        Returns:
            Dict with cost breakdown
        """
        # Calculate base cost in GEM
        price_gem = self.usd_to_gem(price_usd)
        subtotal_gem = price_gem * quantity

        # Calculate fee (4% of transaction)
        fee_gem = max(subtotal_gem * self.TRANSACTION_FEE_RATE, self.MIN_FEE_GEM)

        # Total cost
        total_cost_gem = subtotal_gem + fee_gem

        return {
            "price_per_unit_usd": price_usd,
            "price_per_unit_gem": price_gem,
            "quantity": quantity,
            "subtotal_gem": subtotal_gem,
            "fee_gem": fee_gem,
            "total_cost_gem": total_cost_gem
        }

    def calculate_sell_proceeds(self, price_usd: float, quantity: float) -> Dict:
        """
        Calculate proceeds in GEM from selling crypto.

        Args:
            price_usd: Crypto price in USD
            quantity: Amount of crypto to sell

        Returns:
            Dict with proceeds breakdown
        """
        # Calculate base proceeds in GEM
        price_gem = self.usd_to_gem(price_usd)
        subtotal_gem = price_gem * quantity

        # Calculate fee (4% of transaction)
        fee_gem = max(subtotal_gem * self.TRANSACTION_FEE_RATE, self.MIN_FEE_GEM)

        # Net proceeds after fee
        net_proceeds_gem = subtotal_gem - fee_gem

        return {
            "price_per_unit_usd": price_usd,
            "price_per_unit_gem": price_gem,
            "quantity": quantity,
            "subtotal_gem": subtotal_gem,
            "fee_gem": fee_gem,
            "net_proceeds_gem": net_proceeds_gem
        }

    async def get_crypto_price(self, crypto_id: str, db: AsyncSession) -> Optional[Dict]:
        """
        Get current crypto price from database.

        Args:
            crypto_id: Crypto ID (e.g., 'bitcoin', 'ethereum')
            db: Database session

        Returns:
            Dict with price data or None
        """
        try:
            result = await db.execute(
                select(CryptoCurrency).where(
                    CryptoCurrency.id == crypto_id.lower(),
                    CryptoCurrency.is_active == True
                )
            )
            crypto = result.scalar_one_or_none()

            if crypto and crypto.current_price_usd:
                return {
                    "crypto_id": crypto.id,
                    "symbol": crypto.symbol,
                    "name": crypto.name,
                    "current_price_usd": crypto.current_price_usd,
                    "price_change_pct": crypto.price_change_percentage_24h or 0,
                    "image": crypto.image,
                    "last_updated": crypto.last_updated.isoformat() if crypto.last_updated else None
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching crypto price: {e}")
            return None

    async def buy_crypto(
        self,
        user_id: str,
        crypto_id: str,
        quantity: float,
        db: AsyncSession
    ) -> Dict:
        """
        Buy cryptocurrency.

        Process:
        1. Get current crypto price
        2. Calculate total cost (price * quantity + fee)
        3. Validate user has sufficient GEM
        4. Create/update crypto holding
        5. Deduct GEM from wallet
        6. Create crypto transaction record
        7. Create wallet transaction record
        8. Commit atomically

        Args:
            user_id: User ID
            crypto_id: Cryptocurrency ID (e.g., 'bitcoin')
            quantity: Amount of crypto to buy
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

            crypto_id = crypto_id.lower()

            # Get crypto info
            result = await db.execute(
                select(CryptoCurrency).where(
                    CryptoCurrency.id == crypto_id,
                    CryptoCurrency.is_active == True
                )
            )
            crypto = result.scalar_one_or_none()
            if not crypto:
                raise ValueError(f"Cryptocurrency {crypto_id} not found or inactive")

            if not crypto.current_price_usd:
                raise ValueError(f"Price not available for {crypto_id}")

            current_price_usd = crypto.current_price_usd

            # Calculate costs
            cost_breakdown = self.calculate_buy_cost(current_price_usd, quantity)
            total_cost_gem = cost_breakdown["total_cost_gem"]
            price_per_unit_gem = cost_breakdown["price_per_unit_gem"]
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

            # Get or create crypto holding
            result = await db.execute(
                select(PortfolioHolding).where(
                    PortfolioHolding.user_id == user_id,
                    PortfolioHolding.crypto_id == crypto_id
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
                holding = PortfolioHolding(
                    user_id=user_id,
                    crypto_id=crypto_id,
                    quantity=quantity,
                    average_buy_price_gem=price_per_unit_gem,
                    total_invested_gem=cost_breakdown["subtotal_gem"]
                )
                db.add(holding)

            # Deduct GEM from wallet
            balance_before = wallet.gem_balance
            wallet.gem_balance -= total_cost_gem
            wallet.total_wagered += total_cost_gem
            balance_after = wallet.gem_balance

            # Create crypto transaction record
            crypto_transaction = CryptoTransaction(
                user_id=user_id,
                crypto_id=crypto_id,
                transaction_type="BUY",
                quantity=quantity,
                price_per_unit_gem=price_per_unit_gem,
                total_amount_gem=cost_breakdown["subtotal_gem"],
                fee_gem=fee_gem,
                profit_loss_gem=None  # NULL for buys
            )
            db.add(crypto_transaction)

            # Create wallet transaction record
            wallet_transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.CRYPTO_BUY.value,
                amount=-total_cost_gem,
                balance_before=balance_before,
                balance_after=balance_after,
                description=f"Bought {quantity:.6f} {crypto.symbol.upper()} @ {price_per_unit_gem:.2f} GEM"
            )
            db.add(wallet_transaction)

            # Link wallet transaction to crypto transaction
            await db.flush()
            crypto_transaction.wallet_transaction_id = wallet_transaction.id

            # Commit transaction
            await db.commit()
            await db.refresh(holding)
            await db.refresh(crypto_transaction)

            logger.info(f"User {user_id} bought {quantity} {crypto.symbol} for {total_cost_gem:.2f} GEM")

            return {
                "success": True,
                "transaction_id": crypto_transaction.id,
                "crypto_id": crypto_id,
                "symbol": crypto.symbol.upper(),
                "name": crypto.name,
                "transaction_type": "BUY",
                "quantity": quantity,
                "price_per_unit_usd": current_price_usd,
                "price_per_unit_gem": price_per_unit_gem,
                "subtotal_gem": cost_breakdown["subtotal_gem"],
                "fee_gem": fee_gem,
                "fee_pct": self.TRANSACTION_FEE_RATE * 100,
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
            logger.error(f"Error buying crypto: {e}")
            raise ValueError(f"Failed to buy crypto: {str(e)}")

    async def sell_crypto(
        self,
        user_id: str,
        crypto_id: str,
        quantity: float,
        db: AsyncSession
    ) -> Dict:
        """
        Sell cryptocurrency.

        Process:
        1. Validate user owns sufficient crypto
        2. Get current crypto price
        3. Calculate proceeds (price * quantity - fee)
        4. Calculate P/L vs average buy price
        5. Update/delete crypto holding
        6. Add GEM to wallet
        7. Create crypto transaction record with P/L
        8. Create wallet transaction record
        9. Commit atomically

        Args:
            user_id: User ID
            crypto_id: Cryptocurrency ID
            quantity: Amount of crypto to sell
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

            crypto_id = crypto_id.lower()

            # Get crypto holding
            result = await db.execute(
                select(PortfolioHolding).where(
                    PortfolioHolding.user_id == user_id,
                    PortfolioHolding.crypto_id == crypto_id
                )
            )
            holding = result.scalar_one_or_none()

            if not holding:
                raise ValueError(f"You don't own any {crypto_id}")

            if holding.quantity < quantity:
                raise ValueError(
                    f"Insufficient holdings. You own {holding.quantity:.6f}, trying to sell {quantity:.6f}"
                )

            # Get crypto info
            result = await db.execute(
                select(CryptoCurrency).where(CryptoCurrency.id == crypto_id)
            )
            crypto = result.scalar_one_or_none()
            if not crypto or not crypto.current_price_usd:
                raise ValueError(f"Unable to fetch price for {crypto_id}")

            current_price_usd = crypto.current_price_usd

            # Calculate proceeds
            proceeds_breakdown = self.calculate_sell_proceeds(current_price_usd, quantity)
            net_proceeds_gem = proceeds_breakdown["net_proceeds_gem"]
            price_per_unit_gem = proceeds_breakdown["price_per_unit_gem"]
            fee_gem = proceeds_breakdown["fee_gem"]

            # Calculate profit/loss
            # Cost basis for sold crypto (using average buy price)
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

            # Update crypto holding
            if abs(holding.quantity - quantity) < 0.00000001:  # Selling all (with float precision)
                # Selling all - delete holding
                await db.delete(holding)
                remaining_quantity = 0
                remaining_invested = 0
            else:
                # Selling partial - update holding
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

            # Create crypto transaction record
            crypto_transaction = CryptoTransaction(
                user_id=user_id,
                crypto_id=crypto_id,
                transaction_type="SELL",
                quantity=quantity,
                price_per_unit_gem=price_per_unit_gem,
                total_amount_gem=proceeds_breakdown["subtotal_gem"],
                fee_gem=fee_gem,
                profit_loss_gem=profit_loss_gem
            )
            db.add(crypto_transaction)

            # Create wallet transaction record
            wallet_transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.CRYPTO_SELL.value,
                amount=net_proceeds_gem,
                balance_before=balance_before,
                balance_after=balance_after,
                description=f"Sold {quantity:.6f} {crypto.symbol.upper()} @ {price_per_unit_gem:.2f} GEM (P/L: {profit_loss_gem:+.2f})"
            )
            db.add(wallet_transaction)

            # Link wallet transaction to crypto transaction
            await db.flush()
            crypto_transaction.wallet_transaction_id = wallet_transaction.id

            # Commit transaction
            await db.commit()
            await db.refresh(crypto_transaction)

            logger.info(
                f"User {user_id} sold {quantity} {crypto.symbol} for {net_proceeds_gem:.2f} GEM "
                f"(P/L: {profit_loss_gem:+.2f})"
            )

            return {
                "success": True,
                "transaction_id": crypto_transaction.id,
                "crypto_id": crypto_id,
                "symbol": crypto.symbol.upper(),
                "name": crypto.name,
                "transaction_type": "SELL",
                "quantity": quantity,
                "price_per_unit_usd": current_price_usd,
                "price_per_unit_gem": price_per_unit_gem,
                "subtotal_gem": proceeds_breakdown["subtotal_gem"],
                "fee_gem": fee_gem,
                "fee_pct": self.TRANSACTION_FEE_RATE * 100,
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
            logger.error(f"Error selling crypto: {e}")
            raise ValueError(f"Failed to sell crypto: {str(e)}")

    async def get_buy_quote(
        self,
        user_id: str,
        crypto_id: str,
        quantity: float,
        db: AsyncSession
    ) -> Dict:
        """
        Get a quote for buying crypto without executing the trade.

        Args:
            user_id: User ID
            crypto_id: Cryptocurrency ID
            quantity: Amount of crypto
            db: Database session

        Returns:
            Dict with quote details
        """
        try:
            crypto_id = crypto_id.lower()

            # Get crypto info
            result = await db.execute(
                select(CryptoCurrency).where(
                    CryptoCurrency.id == crypto_id,
                    CryptoCurrency.is_active == True
                )
            )
            crypto = result.scalar_one_or_none()
            if not crypto or not crypto.current_price_usd:
                raise ValueError(f"Unable to fetch price for {crypto_id}")

            current_price_usd = crypto.current_price_usd

            # Calculate costs
            cost_breakdown = self.calculate_buy_cost(current_price_usd, quantity)

            # Get user wallet balance
            result = await db.execute(
                select(Wallet).where(Wallet.user_id == user_id)
            )
            wallet = result.scalar_one_or_none()
            user_balance = wallet.gem_balance if wallet else 0

            return {
                "crypto_id": crypto_id,
                "symbol": crypto.symbol.upper(),
                "name": crypto.name,
                "image": crypto.image,
                "quantity": quantity,
                "price_per_unit_usd": current_price_usd,
                "price_per_unit_gem": cost_breakdown["price_per_unit_gem"],
                "subtotal_gem": cost_breakdown["subtotal_gem"],
                "fee_gem": cost_breakdown["fee_gem"],
                "fee_pct": self.TRANSACTION_FEE_RATE * 100,
                "total_cost_gem": cost_breakdown["total_cost_gem"],
                "user_balance_gem": user_balance,
                "sufficient_funds": user_balance >= cost_breakdown["total_cost_gem"],
                "price_change_pct": crypto.price_change_percentage_24h or 0
            }

        except Exception as e:
            logger.error(f"Error getting buy quote: {e}")
            raise ValueError(f"Failed to get quote: {str(e)}")

    async def get_sell_quote(
        self,
        user_id: str,
        crypto_id: str,
        quantity: float,
        db: AsyncSession
    ) -> Dict:
        """
        Get a quote for selling crypto without executing the trade.

        Args:
            user_id: User ID
            crypto_id: Cryptocurrency ID
            quantity: Amount of crypto
            db: Database session

        Returns:
            Dict with quote details including expected P/L
        """
        try:
            crypto_id = crypto_id.lower()

            # Get holding
            result = await db.execute(
                select(PortfolioHolding).where(
                    PortfolioHolding.user_id == user_id,
                    PortfolioHolding.crypto_id == crypto_id
                )
            )
            holding = result.scalar_one_or_none()
            if not holding:
                raise ValueError(f"You don't own any {crypto_id}")

            if holding.quantity < quantity:
                raise ValueError(
                    f"Insufficient holdings. You own {holding.quantity:.6f}, trying to sell {quantity:.6f}"
                )

            # Get crypto info
            result = await db.execute(
                select(CryptoCurrency).where(CryptoCurrency.id == crypto_id)
            )
            crypto = result.scalar_one_or_none()
            if not crypto or not crypto.current_price_usd:
                raise ValueError(f"Unable to fetch price for {crypto_id}")

            current_price_usd = crypto.current_price_usd

            # Calculate proceeds
            proceeds_breakdown = self.calculate_sell_proceeds(current_price_usd, quantity)

            # Calculate expected P/L
            cost_basis = holding.average_buy_price_gem * quantity
            expected_profit_loss = proceeds_breakdown["subtotal_gem"] - cost_basis

            return {
                "crypto_id": crypto_id,
                "symbol": crypto.symbol.upper(),
                "name": crypto.name,
                "image": crypto.image,
                "quantity": quantity,
                "max_quantity": holding.quantity,
                "price_per_unit_usd": current_price_usd,
                "price_per_unit_gem": proceeds_breakdown["price_per_unit_gem"],
                "subtotal_gem": proceeds_breakdown["subtotal_gem"],
                "fee_gem": proceeds_breakdown["fee_gem"],
                "fee_pct": self.TRANSACTION_FEE_RATE * 100,
                "net_proceeds_gem": proceeds_breakdown["net_proceeds_gem"],
                "average_buy_price_gem": holding.average_buy_price_gem,
                "cost_basis_gem": cost_basis,
                "expected_profit_loss_gem": expected_profit_loss,
                "expected_profit_loss_pct": (expected_profit_loss / cost_basis * 100) if cost_basis > 0 else 0,
                "price_change_pct": crypto.price_change_percentage_24h or 0
            }

        except Exception as e:
            logger.error(f"Error getting sell quote: {e}")
            raise ValueError(f"Failed to get quote: {str(e)}")


# Global instance
crypto_trading_service = CryptoTradingService()
