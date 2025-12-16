"""
Crypto Portfolio Service
Handles portfolio calculations, P/L tracking, and performance analytics.
Provides portfolio summary, holdings details, and transaction history.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database.models import PortfolioHolding, CryptoTransaction, CryptoCurrency

logger = logging.getLogger(__name__)


class CryptoPortfolioService:
    """Service for crypto portfolio management and analytics."""

    # Constants
    GEM_TO_USD_RATE = 0.01  # 1 GEM = $0.01 USD

    def usd_to_gem(self, usd_amount: float) -> float:
        """Convert USD to GEM. $1 = 100 GEM"""
        return usd_amount / self.GEM_TO_USD_RATE

    async def get_holdings(self, user_id: str, db: AsyncSession) -> List[Dict]:
        """
        Get all crypto holdings with current prices and P/L calculations.

        For each holding:
        - Get current price
        - Calculate current value (quantity * current_price)
        - Calculate P/L (current_value - total_invested)
        - Calculate P/L% ((P/L / total_invested) * 100)

        Args:
            user_id: User ID
            db: Database session

        Returns:
            List of holdings with P/L data
        """
        try:
            # Get all holdings for user
            result = await db.execute(
                select(PortfolioHolding).where(PortfolioHolding.user_id == user_id)
            )
            holdings = result.scalars().all()

            if not holdings:
                return []

            # Process each holding
            holdings_data = []
            for holding in holdings:
                # Get crypto info and current price
                result = await db.execute(
                    select(CryptoCurrency).where(CryptoCurrency.id == holding.crypto_id)
                )
                crypto = result.scalar_one_or_none()

                if crypto and crypto.current_price_usd:
                    current_price_gem = self.usd_to_gem(crypto.current_price_usd)
                    current_value_gem = holding.quantity * current_price_gem
                    profit_loss_gem = current_value_gem - holding.total_invested_gem
                    profit_loss_pct = (profit_loss_gem / holding.total_invested_gem * 100) if holding.total_invested_gem > 0 else 0

                    holdings_data.append({
                        "crypto_id": holding.crypto_id,
                        "symbol": crypto.symbol.upper(),
                        "name": crypto.name,
                        "image": crypto.image,
                        "quantity": holding.quantity,
                        "average_buy_price_gem": holding.average_buy_price_gem,
                        "total_invested_gem": holding.total_invested_gem,
                        "current_price_usd": crypto.current_price_usd,
                        "current_price_gem": current_price_gem,
                        "current_value_gem": current_value_gem,
                        "profit_loss_gem": profit_loss_gem,
                        "profit_loss_pct": profit_loss_pct,
                        "price_change_pct": crypto.price_change_percentage_24h or 0,
                        "last_updated": crypto.last_updated.isoformat() if crypto.last_updated else None
                    })
                else:
                    # Price unavailable
                    logger.warning(f"Price unavailable for {holding.crypto_id}")
                    holdings_data.append({
                        "crypto_id": holding.crypto_id,
                        "symbol": holding.crypto_id.upper(),
                        "name": holding.crypto_id.title(),
                        "image": None,
                        "quantity": holding.quantity,
                        "average_buy_price_gem": holding.average_buy_price_gem,
                        "total_invested_gem": holding.total_invested_gem,
                        "current_price_usd": None,
                        "current_price_gem": None,
                        "current_value_gem": None,
                        "profit_loss_gem": None,
                        "profit_loss_pct": None,
                        "price_change_pct": 0,
                        "last_updated": None,
                        "error": "Price unavailable"
                    })

            return holdings_data

        except Exception as e:
            logger.error(f"Error fetching crypto holdings: {e}")
            return []

    async def get_portfolio_summary(self, user_id: str, db: AsyncSession) -> Dict:
        """
        Get complete crypto portfolio summary.

        Returns:
            total_value_gem: Current value of all holdings
            total_invested_gem: Total amount invested
            profit_loss_gem: Total P/L
            profit_loss_pct: Total P/L percentage
            holdings_count: Number of different cryptos owned
            top_performer: Best performing crypto
            worst_performer: Worst performing crypto
        """
        try:
            # Get all holdings with P/L
            holdings_data = await self.get_holdings(user_id, db)

            if not holdings_data:
                return {
                    "total_value_gem": 0,
                    "total_invested_gem": 0,
                    "profit_loss_gem": 0,
                    "profit_loss_pct": 0,
                    "holdings_count": 0,
                    "top_performer": None,
                    "worst_performer": None
                }

            # Calculate totals
            total_value_gem = 0
            total_invested_gem = 0

            for holding in holdings_data:
                if holding.get("current_value_gem") is not None:
                    total_value_gem += holding["current_value_gem"]
                total_invested_gem += holding["total_invested_gem"]

            # Calculate overall P/L
            profit_loss_gem = total_value_gem - total_invested_gem
            profit_loss_pct = (profit_loss_gem / total_invested_gem * 100) if total_invested_gem > 0 else 0

            # Find top and worst performers
            valid_holdings = [h for h in holdings_data if h.get("profit_loss_pct") is not None]
            top_performer = max(valid_holdings, key=lambda x: x["profit_loss_pct"]) if valid_holdings else None
            worst_performer = min(valid_holdings, key=lambda x: x["profit_loss_pct"]) if valid_holdings else None

            return {
                "total_value_gem": total_value_gem,
                "total_invested_gem": total_invested_gem,
                "profit_loss_gem": profit_loss_gem,
                "profit_loss_pct": profit_loss_pct,
                "holdings_count": len(holdings_data),
                "top_performer": {
                    "symbol": top_performer["symbol"],
                    "name": top_performer["name"],
                    "profit_loss_pct": top_performer["profit_loss_pct"]
                } if top_performer else None,
                "worst_performer": {
                    "symbol": worst_performer["symbol"],
                    "name": worst_performer["name"],
                    "profit_loss_pct": worst_performer["profit_loss_pct"]
                } if worst_performer else None
            }

        except Exception as e:
            logger.error(f"Error calculating crypto portfolio summary: {e}")
            return {
                "total_value_gem": 0,
                "total_invested_gem": 0,
                "profit_loss_gem": 0,
                "profit_loss_pct": 0,
                "holdings_count": 0,
                "top_performer": None,
                "worst_performer": None,
                "error": str(e)
            }

    async def get_transaction_history(
        self,
        user_id: str,
        limit: int = 50,
        crypto_id: Optional[str] = None,
        transaction_type: Optional[str] = None,
        db: AsyncSession = None
    ) -> List[Dict]:
        """
        Get crypto transaction history.

        Args:
            user_id: User ID
            limit: Maximum number of transactions to return
            crypto_id: Filter by crypto ID (optional)
            transaction_type: Filter by BUY or SELL (optional)
            db: Database session

        Returns:
            List of transactions
        """
        try:
            # Build query
            query = select(CryptoTransaction).where(
                CryptoTransaction.user_id == user_id
            )

            if crypto_id:
                query = query.where(CryptoTransaction.crypto_id == crypto_id.lower())

            if transaction_type:
                query = query.where(CryptoTransaction.transaction_type == transaction_type.upper())

            query = query.order_by(desc(CryptoTransaction.created_at)).limit(limit)

            # Execute query
            result = await db.execute(query)
            transactions = result.scalars().all()

            # Format transactions
            transactions_data = []
            for tx in transactions:
                # Get crypto info
                result = await db.execute(
                    select(CryptoCurrency).where(CryptoCurrency.id == tx.crypto_id)
                )
                crypto = result.scalar_one_or_none()

                transactions_data.append({
                    "id": tx.id,
                    "crypto_id": tx.crypto_id,
                    "symbol": crypto.symbol.upper() if crypto else tx.crypto_id.upper(),
                    "name": crypto.name if crypto else tx.crypto_id.title(),
                    "image": crypto.image if crypto else None,
                    "transaction_type": tx.transaction_type,
                    "quantity": tx.quantity,
                    "price_per_unit_gem": tx.price_per_unit_gem,
                    "total_amount_gem": tx.total_amount_gem,
                    "fee_gem": tx.fee_gem,
                    "profit_loss_gem": tx.profit_loss_gem,
                    "created_at": tx.created_at.isoformat() if tx.created_at else None
                })

            return transactions_data

        except Exception as e:
            logger.error(f"Error fetching crypto transaction history: {e}")
            return []

    async def get_crypto_position(
        self,
        user_id: str,
        crypto_id: str,
        db: AsyncSession
    ) -> Optional[Dict]:
        """
        Get detailed information about a specific crypto position.

        Args:
            user_id: User ID
            crypto_id: Crypto ID
            db: Database session

        Returns:
            Position details or None if not owned
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
                return None

            # Get crypto info and current price
            result = await db.execute(
                select(CryptoCurrency).where(CryptoCurrency.id == crypto_id)
            )
            crypto = result.scalar_one_or_none()

            if crypto and crypto.current_price_usd:
                current_price_gem = self.usd_to_gem(crypto.current_price_usd)
                current_value_gem = holding.quantity * current_price_gem
                profit_loss_gem = current_value_gem - holding.total_invested_gem
                profit_loss_pct = (profit_loss_gem / holding.total_invested_gem * 100) if holding.total_invested_gem > 0 else 0
            else:
                current_price_gem = None
                current_value_gem = None
                profit_loss_gem = None
                profit_loss_pct = None

            # Get recent transactions for this crypto
            tx_result = await db.execute(
                select(CryptoTransaction).where(
                    CryptoTransaction.user_id == user_id,
                    CryptoTransaction.crypto_id == crypto_id
                ).order_by(desc(CryptoTransaction.created_at)).limit(10)
            )
            recent_transactions = tx_result.scalars().all()

            return {
                "crypto_id": crypto_id,
                "symbol": crypto.symbol.upper() if crypto else crypto_id.upper(),
                "name": crypto.name if crypto else crypto_id.title(),
                "image": crypto.image if crypto else None,
                "quantity": holding.quantity,
                "average_buy_price_gem": holding.average_buy_price_gem,
                "total_invested_gem": holding.total_invested_gem,
                "current_price_usd": crypto.current_price_usd if crypto else None,
                "current_price_gem": current_price_gem,
                "current_value_gem": current_value_gem,
                "profit_loss_gem": profit_loss_gem,
                "profit_loss_pct": profit_loss_pct,
                "price_change_pct": crypto.price_change_percentage_24h if crypto else 0,
                "recent_transactions": [tx.to_dict() for tx in recent_transactions]
            }

        except Exception as e:
            logger.error(f"Error fetching crypto position: {e}")
            return None


# Global instance
crypto_portfolio_service = CryptoPortfolioService()
