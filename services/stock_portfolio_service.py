"""
Stock Portfolio Service
Handles portfolio calculations, P/L tracking, and performance analytics.
Provides portfolio summary, holdings details, and transaction history.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from database.models import StockHolding, StockTransaction, StockMetadata
from services.stock_data_service import stock_data_service

logger = logging.getLogger(__name__)


class StockPortfolioService:
    """Service for stock portfolio management and analytics."""

    async def get_holdings(self, user_id: str, db: AsyncSession) -> List[Dict]:
        """
        Get all stock holdings with current prices and P/L calculations.

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
                select(StockHolding).where(StockHolding.user_id == user_id)
            )
            holdings = result.scalars().all()

            if not holdings:
                return []

            # Process each holding
            holdings_data = []
            for holding in holdings:
                # Get current price
                price_data = await stock_data_service.get_stock_price(holding.ticker, db)

                if price_data:
                    current_price_gem = price_data["current_price_usd"] / 0.01  # USD to GEM
                    current_value_gem = holding.quantity * current_price_gem
                    profit_loss_gem = current_value_gem - holding.total_invested_gem
                    profit_loss_pct = (profit_loss_gem / holding.total_invested_gem * 100) if holding.total_invested_gem > 0 else 0

                    # Get stock metadata
                    meta_result = await db.execute(
                        select(StockMetadata).where(StockMetadata.ticker == holding.ticker)
                    )
                    metadata = meta_result.scalar_one_or_none()

                    holdings_data.append({
                        "ticker": holding.ticker,
                        "company_name": metadata.company_name if metadata else holding.ticker,
                        "sector": metadata.sector if metadata else None,
                        "quantity": holding.quantity,
                        "average_buy_price_gem": holding.average_buy_price_gem,
                        "total_invested_gem": holding.total_invested_gem,
                        "current_price_usd": price_data["current_price_usd"],
                        "current_price_gem": current_price_gem,
                        "current_value_gem": current_value_gem,
                        "profit_loss_gem": profit_loss_gem,
                        "profit_loss_pct": profit_loss_pct,
                        "price_change_pct": price_data.get("price_change_pct", 0),
                        "last_updated": price_data.get("last_updated")
                    })
                else:
                    # Price unavailable - use last known price
                    logger.warning(f"Price unavailable for {holding.ticker}")
                    holdings_data.append({
                        "ticker": holding.ticker,
                        "company_name": holding.ticker,
                        "sector": None,
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
            logger.error(f"Error fetching holdings: {e}")
            return []

    async def get_portfolio_summary(self, user_id: str, db: AsyncSession) -> Dict:
        """
        Get complete portfolio summary.

        Returns:
            total_value_gem: Current value of all holdings
            total_invested_gem: Total amount invested
            profit_loss_gem: Total P/L
            profit_loss_pct: Total P/L percentage
            holdings_count: Number of different stocks owned
            diversification: Breakdown by sector
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
                    "diversification": {},
                    "top_performer": None,
                    "worst_performer": None
                }

            # Calculate totals
            total_value_gem = 0
            total_invested_gem = 0
            sector_breakdown = {}

            for holding in holdings_data:
                if holding.get("current_value_gem") is not None:
                    total_value_gem += holding["current_value_gem"]
                total_invested_gem += holding["total_invested_gem"]

                # Sector breakdown
                sector = holding.get("sector") or "Other"
                if sector not in sector_breakdown:
                    sector_breakdown[sector] = {
                        "sector": sector,
                        "value_gem": 0,
                        "count": 0
                    }
                if holding.get("current_value_gem") is not None:
                    sector_breakdown[sector]["value_gem"] += holding["current_value_gem"]
                sector_breakdown[sector]["count"] += 1

            # Calculate overall P/L
            profit_loss_gem = total_value_gem - total_invested_gem
            profit_loss_pct = (profit_loss_gem / total_invested_gem * 100) if total_invested_gem > 0 else 0

            # Calculate sector percentages
            for sector_data in sector_breakdown.values():
                sector_data["percentage"] = (sector_data["value_gem"] / total_value_gem * 100) if total_value_gem > 0 else 0

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
                "diversification": list(sector_breakdown.values()),
                "top_performer": {
                    "ticker": top_performer["ticker"],
                    "profit_loss_pct": top_performer["profit_loss_pct"]
                } if top_performer else None,
                "worst_performer": {
                    "ticker": worst_performer["ticker"],
                    "profit_loss_pct": worst_performer["profit_loss_pct"]
                } if worst_performer else None
            }

        except Exception as e:
            logger.error(f"Error calculating portfolio summary: {e}")
            return {
                "total_value_gem": 0,
                "total_invested_gem": 0,
                "profit_loss_gem": 0,
                "profit_loss_pct": 0,
                "holdings_count": 0,
                "diversification": {},
                "top_performer": None,
                "worst_performer": None,
                "error": str(e)
            }

    async def get_transaction_history(
        self,
        user_id: str,
        limit: int = 50,
        ticker: Optional[str] = None,
        transaction_type: Optional[str] = None,
        db: AsyncSession = None
    ) -> List[Dict]:
        """
        Get stock transaction history.

        Args:
            user_id: User ID
            limit: Maximum number of transactions to return
            ticker: Filter by stock ticker (optional)
            transaction_type: Filter by BUY or SELL (optional)
            db: Database session

        Returns:
            List of transactions
        """
        try:
            # Build query
            query = select(StockTransaction).where(
                StockTransaction.user_id == user_id
            )

            if ticker:
                query = query.where(StockTransaction.ticker == ticker.upper())

            if transaction_type:
                query = query.where(StockTransaction.transaction_type == transaction_type.upper())

            query = query.order_by(desc(StockTransaction.created_at)).limit(limit)

            # Execute query
            result = await db.execute(query)
            transactions = result.scalars().all()

            # Format transactions
            transactions_data = []
            for tx in transactions:
                # Get stock metadata
                meta_result = await db.execute(
                    select(StockMetadata).where(StockMetadata.ticker == tx.ticker)
                )
                metadata = meta_result.scalar_one_or_none()

                transactions_data.append({
                    "id": tx.id,
                    "ticker": tx.ticker,
                    "company_name": metadata.company_name if metadata else tx.ticker,
                    "transaction_type": tx.transaction_type,
                    "quantity": tx.quantity,
                    "price_per_share_gem": tx.price_per_share_gem,
                    "total_amount_gem": tx.total_amount_gem,
                    "fee_gem": tx.fee_gem,
                    "profit_loss_gem": tx.profit_loss_gem,
                    "created_at": tx.created_at.isoformat() if tx.created_at else None
                })

            return transactions_data

        except Exception as e:
            logger.error(f"Error fetching transaction history: {e}")
            return []

    async def get_portfolio_performance(
        self,
        user_id: str,
        days: int = 30,
        db: AsyncSession = None
    ) -> List[Dict]:
        """
        Get portfolio value over time for performance charts.

        Note: This is a simplified version that calculates performance based on
        transaction history. In production, you'd want daily snapshots.

        Args:
            user_id: User ID
            days: Number of days to look back
            db: Database session

        Returns:
            List of daily portfolio value snapshots
        """
        try:
            # Get all transactions within timeframe
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            result = await db.execute(
                select(StockTransaction).where(
                    StockTransaction.user_id == user_id,
                    StockTransaction.created_at >= cutoff_date
                ).order_by(StockTransaction.created_at)
            )
            transactions = result.scalars().all()

            if not transactions:
                return []

            # Get current portfolio summary
            current_summary = await self.get_portfolio_summary(user_id, db)

            # For now, return simplified performance data
            # In production, you'd calculate daily snapshots
            performance_data = [
                {
                    "date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "portfolio_value_gem": current_summary["total_value_gem"],
                    "profit_loss_gem": current_summary["profit_loss_gem"],
                    "profit_loss_pct": current_summary["profit_loss_pct"]
                }
            ]

            return performance_data

        except Exception as e:
            logger.error(f"Error fetching portfolio performance: {e}")
            return []

    async def get_stock_position(
        self,
        user_id: str,
        ticker: str,
        db: AsyncSession
    ) -> Optional[Dict]:
        """
        Get detailed information about a specific stock position.

        Args:
            user_id: User ID
            ticker: Stock ticker
            db: Database session

        Returns:
            Position details or None if not owned
        """
        try:
            ticker = ticker.upper()

            # Get holding
            result = await db.execute(
                select(StockHolding).where(
                    StockHolding.user_id == user_id,
                    StockHolding.ticker == ticker
                )
            )
            holding = result.scalar_one_or_none()

            if not holding:
                return None

            # Get current price and calculate P/L
            price_data = await stock_data_service.get_stock_price(ticker, db)

            if price_data:
                current_price_gem = price_data["current_price_usd"] / 0.01
                current_value_gem = holding.quantity * current_price_gem
                profit_loss_gem = current_value_gem - holding.total_invested_gem
                profit_loss_pct = (profit_loss_gem / holding.total_invested_gem * 100) if holding.total_invested_gem > 0 else 0
            else:
                current_price_gem = None
                current_value_gem = None
                profit_loss_gem = None
                profit_loss_pct = None

            # Get stock metadata
            meta_result = await db.execute(
                select(StockMetadata).where(StockMetadata.ticker == ticker)
            )
            metadata = meta_result.scalar_one_or_none()

            # Get transaction history for this stock
            tx_result = await db.execute(
                select(StockTransaction).where(
                    StockTransaction.user_id == user_id,
                    StockTransaction.ticker == ticker
                ).order_by(desc(StockTransaction.created_at)).limit(10)
            )
            recent_transactions = tx_result.scalars().all()

            return {
                "ticker": ticker,
                "company_name": metadata.company_name if metadata else ticker,
                "sector": metadata.sector if metadata else None,
                "quantity": holding.quantity,
                "average_buy_price_gem": holding.average_buy_price_gem,
                "total_invested_gem": holding.total_invested_gem,
                "current_price_gem": current_price_gem,
                "current_value_gem": current_value_gem,
                "profit_loss_gem": profit_loss_gem,
                "profit_loss_pct": profit_loss_pct,
                "recent_transactions": [tx.to_dict() for tx in recent_transactions]
            }

        except Exception as e:
            logger.error(f"Error fetching stock position: {e}")
            return None


# Global instance
stock_portfolio_service = StockPortfolioService()
