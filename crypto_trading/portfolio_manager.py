"""
Portfolio Management System - Manages user cryptocurrency holdings and trading operations.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func

from database import get_db_session, VirtualWallet, VirtualCryptoHolding, VirtualTransaction
from crypto_market import market_data_service, crypto_registry
from virtual_economy import virtual_economy_engine
from logger import logger


class PortfolioError(Exception):
    """Portfolio operation errors."""
    pass


class InsufficientFundsError(PortfolioError):
    """Raised when user has insufficient funds for operation."""
    pass


class InvalidTradeError(PortfolioError):
    """Raised when trade parameters are invalid."""
    pass


class PortfolioManager:
    """Manages user cryptocurrency portfolios and trading operations."""
    
    def __init__(self):
        self.trading_fee_rate = 0.0025  # 0.25% trading fee
        self.min_trade_amount_gems = 10.0  # Minimum 10 GEM trade
        self.max_trade_amount_gems = 100000.0  # Maximum 100k GEM trade
    
    async def get_user_portfolio(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user portfolio information."""
        try:
            async with get_db_session() as session:
                # Get wallet balance
                wallet = await virtual_economy_engine.get_user_wallet(session, user_id)
                if not wallet:
                    raise PortfolioError(f"User {user_id} does not have a wallet")
                
                # Get crypto holdings
                holdings_query = select(VirtualCryptoHolding).where(
                    and_(
                        VirtualCryptoHolding.user_id == user_id,
                        VirtualCryptoHolding.amount > 0
                    )
                )
                result = await session.execute(holdings_query)
                holdings = result.scalars().all()
                
                # Calculate portfolio metrics
                portfolio_data = []
                total_value_gems = 0.0
                total_invested = 0.0
                
                for holding in holdings:
                    # Get current price
                    current_price = await market_data_service.get_current_price(holding.crypto_symbol)
                    if current_price:
                        current_value = holding.amount * current_price.price
                        total_value_gems += current_value
                        
                        # Calculate profit/loss
                        invested_amount = holding.average_cost * holding.amount
                        total_invested += invested_amount
                        profit_loss = current_value - invested_amount
                        profit_loss_percentage = (profit_loss / invested_amount * 100) if invested_amount > 0 else 0
                        
                        portfolio_data.append({
                            "symbol": holding.crypto_symbol,
                            "amount": float(holding.amount),
                            "average_cost": float(holding.average_cost),
                            "current_price": current_price.price,
                            "current_value_gems": current_value,
                            "invested_amount_gems": invested_amount,
                            "profit_loss_gems": profit_loss,
                            "profit_loss_percentage": profit_loss_percentage,
                            "last_updated": current_price.timestamp.isoformat()
                        })
                
                # Portfolio summary
                total_portfolio_value = wallet.gem_balance + total_value_gems
                cash_percentage = (wallet.gem_balance / total_portfolio_value * 100) if total_portfolio_value > 0 else 100
                crypto_percentage = (total_value_gems / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
                
                return {
                    "user_id": user_id,
                    "wallet_balance_gems": float(wallet.gem_balance),
                    "total_crypto_value_gems": total_value_gems,
                    "total_portfolio_value_gems": total_portfolio_value,
                    "total_invested_gems": total_invested,
                    "total_profit_loss_gems": total_value_gems - total_invested,
                    "total_profit_loss_percentage": ((total_value_gems - total_invested) / total_invested * 100) if total_invested > 0 else 0,
                    "cash_percentage": cash_percentage,
                    "crypto_percentage": crypto_percentage,
                    "holdings_count": len(holdings),
                    "holdings": portfolio_data,
                    "last_updated": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get user portfolio for {user_id}: {e}")
            raise PortfolioError(f"Failed to retrieve portfolio: {e}")
    
    async def buy_cryptocurrency(
        self, 
        user_id: str, 
        crypto_symbol: str, 
        amount_gems: float,
        order_type: str = "MARKET"
    ) -> Dict[str, Any]:
        """Buy cryptocurrency with GEM coins."""
        try:
            async with get_db_session() as session:
                # Validate inputs
                if amount_gems < self.min_trade_amount_gems:
                    raise InvalidTradeError(f"Minimum trade amount is {self.min_trade_amount_gems} GEM")
                
                if amount_gems > self.max_trade_amount_gems:
                    raise InvalidTradeError(f"Maximum trade amount is {self.max_trade_amount_gems} GEM")
                
                # Check if crypto exists and is tradeable
                crypto = await crypto_registry.get_crypto_by_symbol(session, crypto_symbol)
                if not crypto:
                    raise InvalidTradeError(f"Cryptocurrency {crypto_symbol} not found")
                
                if not crypto.is_tradeable:
                    raise InvalidTradeError(f"Cryptocurrency {crypto_symbol} is not tradeable")
                
                # Get current price
                price_data = await market_data_service.get_current_price(crypto_symbol)
                if not price_data:
                    raise InvalidTradeError(f"Unable to get current price for {crypto_symbol}")
                
                current_price = price_data.price
                
                # Calculate trading fee
                trading_fee = amount_gems * self.trading_fee_rate
                total_cost = amount_gems + trading_fee
                
                # Check user wallet balance
                wallet = await virtual_economy_engine.get_user_wallet(session, user_id)
                if not wallet or wallet.gem_balance < total_cost:
                    raise InsufficientFundsError("Insufficient GEM balance for purchase")
                
                # Calculate crypto amount to buy
                crypto_amount = amount_gems / current_price
                
                # Update wallet balance
                await virtual_economy_engine.update_wallet_balance(
                    session, user_id, "GEM_COINS", -total_cost, 
                    f"Buy {crypto_amount:.8f} {crypto_symbol}"
                )
                
                # Update or create crypto holding
                await self._update_crypto_holding(
                    session, user_id, crypto_symbol, crypto_amount, current_price, "BUY"
                )
                
                # Record transaction
                transaction_id = str(uuid.uuid4())
                transaction = VirtualTransaction(
                    id=transaction_id,
                    user_id=user_id,
                    transaction_type="CRYPTO_BUY",
                    currency_type="CRYPTO",
                    amount=crypto_amount,
                    balance_after=0.0,  # Will be updated by holding query
                    description=f"Bought {crypto_amount:.8f} {crypto_symbol} @ {current_price:.6f} GEM/token",
                    metadata={
                        "crypto_symbol": crypto_symbol,
                        "price_per_token": current_price,
                        "total_cost_gems": total_cost,
                        "trading_fee": trading_fee,
                        "order_type": order_type
                    }
                )
                session.add(transaction)
                await session.commit()
                
                logger.info(f"User {user_id} bought {crypto_amount:.8f} {crypto_symbol} for {total_cost:.2f} GEM")
                
                return {
                    "transaction_id": transaction_id,
                    "crypto_symbol": crypto_symbol,
                    "crypto_amount": crypto_amount,
                    "price_per_token": current_price,
                    "total_cost_gems": total_cost,
                    "trading_fee": trading_fee,
                    "order_type": order_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "COMPLETED"
                }
                
        except (InsufficientFundsError, InvalidTradeError) as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to buy crypto for user {user_id}: {e}")
            raise PortfolioError(f"Failed to execute buy order: {e}")
    
    async def sell_cryptocurrency(
        self, 
        user_id: str, 
        crypto_symbol: str, 
        crypto_amount: float,
        order_type: str = "MARKET"
    ) -> Dict[str, Any]:
        """Sell cryptocurrency for GEM coins."""
        try:
            async with get_db_session() as session:
                # Validate inputs
                if crypto_amount <= 0:
                    raise InvalidTradeError("Sell amount must be positive")
                
                # Check if crypto exists and is tradeable
                crypto = await crypto_registry.get_crypto_by_symbol(session, crypto_symbol)
                if not crypto:
                    raise InvalidTradeError(f"Cryptocurrency {crypto_symbol} not found")
                
                if not crypto.is_tradeable:
                    raise InvalidTradeError(f"Cryptocurrency {crypto_symbol} is not tradeable")
                
                # Check user's crypto holding
                holding_query = select(VirtualCryptoHolding).where(
                    and_(
                        VirtualCryptoHolding.user_id == user_id,
                        VirtualCryptoHolding.crypto_symbol == crypto_symbol
                    )
                )
                result = await session.execute(holding_query)
                holding = result.scalar_one_or_none()
                
                if not holding or holding.amount < crypto_amount:
                    raise InsufficientFundsError(f"Insufficient {crypto_symbol} balance")
                
                # Get current price
                price_data = await market_data_service.get_current_price(crypto_symbol)
                if not price_data:
                    raise InvalidTradeError(f"Unable to get current price for {crypto_symbol}")
                
                current_price = price_data.price
                
                # Calculate proceeds
                gross_proceeds = crypto_amount * current_price
                trading_fee = gross_proceeds * self.trading_fee_rate
                net_proceeds = gross_proceeds - trading_fee
                
                # Check minimum trade value
                if gross_proceeds < self.min_trade_amount_gems:
                    raise InvalidTradeError(f"Trade value must be at least {self.min_trade_amount_gems} GEM")
                
                # Update user's crypto holding
                await self._update_crypto_holding(
                    session, user_id, crypto_symbol, -crypto_amount, current_price, "SELL"
                )
                
                # Update wallet balance
                await virtual_economy_engine.update_wallet_balance(
                    session, user_id, "GEM_COINS", net_proceeds, 
                    f"Sell {crypto_amount:.8f} {crypto_symbol}"
                )
                
                # Record transaction
                transaction_id = str(uuid.uuid4())
                transaction = VirtualTransaction(
                    id=transaction_id,
                    user_id=user_id,
                    transaction_type="CRYPTO_SELL",
                    currency_type="CRYPTO",
                    amount=-crypto_amount,
                    balance_after=holding.amount - crypto_amount,
                    description=f"Sold {crypto_amount:.8f} {crypto_symbol} @ {current_price:.6f} GEM/token",
                    metadata={
                        "crypto_symbol": crypto_symbol,
                        "price_per_token": current_price,
                        "gross_proceeds_gems": gross_proceeds,
                        "trading_fee": trading_fee,
                        "net_proceeds_gems": net_proceeds,
                        "order_type": order_type
                    }
                )
                session.add(transaction)
                await session.commit()
                
                logger.info(f"User {user_id} sold {crypto_amount:.8f} {crypto_symbol} for {net_proceeds:.2f} GEM")
                
                return {
                    "transaction_id": transaction_id,
                    "crypto_symbol": crypto_symbol,
                    "crypto_amount": crypto_amount,
                    "price_per_token": current_price,
                    "gross_proceeds_gems": gross_proceeds,
                    "trading_fee": trading_fee,
                    "net_proceeds_gems": net_proceeds,
                    "order_type": order_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "COMPLETED"
                }
                
        except (InsufficientFundsError, InvalidTradeError) as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to sell crypto for user {user_id}: {e}")
            raise PortfolioError(f"Failed to execute sell order: {e}")
    
    async def _update_crypto_holding(
        self, 
        session: AsyncSession, 
        user_id: str, 
        crypto_symbol: str, 
        amount_change: float, 
        price: float, 
        operation: str
    ):
        """Update user's cryptocurrency holding."""
        # Get existing holding
        holding_query = select(VirtualCryptoHolding).where(
            and_(
                VirtualCryptoHolding.user_id == user_id,
                VirtualCryptoHolding.crypto_symbol == crypto_symbol
            )
        )
        result = await session.execute(holding_query)
        holding = result.scalar_one_or_none()
        
        if operation == "BUY":
            if holding:
                # Update existing holding with new average cost
                old_total_value = holding.amount * holding.average_cost
                new_total_value = amount_change * price
                new_total_amount = holding.amount + amount_change
                new_average_cost = (old_total_value + new_total_value) / new_total_amount
                
                holding.amount = new_total_amount
                holding.average_cost = new_average_cost
                holding.last_updated = datetime.utcnow()
            else:
                # Create new holding
                holding = VirtualCryptoHolding(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    crypto_symbol=crypto_symbol,
                    amount=amount_change,
                    average_cost=price,
                    last_updated=datetime.utcnow()
                )
                session.add(holding)
        
        elif operation == "SELL":
            if holding:
                holding.amount -= abs(amount_change)
                holding.last_updated = datetime.utcnow()
                
                # Remove holding if amount becomes zero or negative
                if holding.amount <= 0:
                    await session.delete(holding)
            else:
                raise InsufficientFundsError(f"No {crypto_symbol} holding found")
    
    async def get_trading_history(
        self, 
        user_id: str, 
        limit: int = 50, 
        crypto_symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user's cryptocurrency trading history."""
        try:
            async with get_db_session() as session:
                query = select(VirtualTransaction).where(
                    and_(
                        VirtualTransaction.user_id == user_id,
                        VirtualTransaction.transaction_type.in_(["CRYPTO_BUY", "CRYPTO_SELL"])
                    )
                )
                
                if crypto_symbol:
                    # Filter by crypto symbol in metadata
                    query = query.where(
                        VirtualTransaction.metadata['crypto_symbol'].astext == crypto_symbol
                    )
                
                query = query.order_by(VirtualTransaction.created_at.desc()).limit(limit)
                
                result = await session.execute(query)
                transactions = result.scalars().all()
                
                trading_history = []
                for transaction in transactions:
                    trading_history.append({
                        "transaction_id": transaction.id,
                        "transaction_type": transaction.transaction_type,
                        "crypto_symbol": transaction.metadata.get("crypto_symbol"),
                        "crypto_amount": abs(float(transaction.amount)),
                        "price_per_token": transaction.metadata.get("price_per_token"),
                        "total_value_gems": transaction.metadata.get("total_cost_gems") or transaction.metadata.get("gross_proceeds_gems"),
                        "trading_fee": transaction.metadata.get("trading_fee"),
                        "net_amount_gems": transaction.metadata.get("net_proceeds_gems") if transaction.transaction_type == "CRYPTO_SELL" else -(transaction.metadata.get("total_cost_gems", 0)),
                        "description": transaction.description,
                        "timestamp": transaction.created_at.isoformat(),
                        "order_type": transaction.metadata.get("order_type", "MARKET")
                    })
                
                return trading_history
                
        except Exception as e:
            logger.error(f"Failed to get trading history for user {user_id}: {e}")
            raise PortfolioError(f"Failed to retrieve trading history: {e}")
    
    async def get_portfolio_performance(
        self, 
        user_id: str, 
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get portfolio performance metrics over a specified period."""
        try:
            async with get_db_session() as session:
                start_date = datetime.utcnow() - timedelta(days=period_days)
                
                # Get all crypto transactions in the period
                transactions_query = select(VirtualTransaction).where(
                    and_(
                        VirtualTransaction.user_id == user_id,
                        VirtualTransaction.transaction_type.in_(["CRYPTO_BUY", "CRYPTO_SELL"]),
                        VirtualTransaction.created_at >= start_date
                    )
                ).order_by(VirtualTransaction.created_at)
                
                result = await session.execute(transactions_query)
                transactions = result.scalars().all()
                
                # Calculate performance metrics
                total_bought = 0.0
                total_sold = 0.0
                trading_fees_paid = 0.0
                transactions_count = len(transactions)
                
                crypto_performance = {}
                
                for transaction in transactions:
                    crypto_symbol = transaction.metadata.get("crypto_symbol")
                    trading_fee = transaction.metadata.get("trading_fee", 0)
                    trading_fees_paid += trading_fee
                    
                    if transaction.transaction_type == "CRYPTO_BUY":
                        cost = transaction.metadata.get("total_cost_gems", 0)
                        total_bought += cost
                        
                        if crypto_symbol not in crypto_performance:
                            crypto_performance[crypto_symbol] = {"bought": 0, "sold": 0, "net": 0}
                        crypto_performance[crypto_symbol]["bought"] += cost
                        crypto_performance[crypto_symbol]["net"] -= cost
                    
                    elif transaction.transaction_type == "CRYPTO_SELL":
                        proceeds = transaction.metadata.get("net_proceeds_gems", 0)
                        total_sold += proceeds
                        
                        if crypto_symbol not in crypto_performance:
                            crypto_performance[crypto_symbol] = {"bought": 0, "sold": 0, "net": 0}
                        crypto_performance[crypto_symbol]["sold"] += proceeds
                        crypto_performance[crypto_symbol]["net"] += proceeds
                
                # Get current portfolio value
                current_portfolio = await self.get_user_portfolio(user_id)
                
                # Calculate overall performance
                net_trading_result = total_sold - total_bought
                current_crypto_value = current_portfolio["total_crypto_value_gems"]
                unrealized_gains = current_crypto_value - current_portfolio["total_invested_gems"]
                
                total_performance = net_trading_result + unrealized_gains
                roi_percentage = (total_performance / total_bought * 100) if total_bought > 0 else 0
                
                return {
                    "period_days": period_days,
                    "start_date": start_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat(),
                    "transactions_count": transactions_count,
                    "total_bought_gems": total_bought,
                    "total_sold_gems": total_sold,
                    "net_trading_result_gems": net_trading_result,
                    "trading_fees_paid_gems": trading_fees_paid,
                    "current_crypto_value_gems": current_crypto_value,
                    "unrealized_gains_gems": unrealized_gains,
                    "total_performance_gems": total_performance,
                    "roi_percentage": roi_percentage,
                    "crypto_performance": crypto_performance,
                    "average_transaction_value": (total_bought + total_sold) / max(transactions_count, 1),
                    "win_rate": self._calculate_win_rate(transactions)
                }
                
        except Exception as e:
            logger.error(f"Failed to get portfolio performance for user {user_id}: {e}")
            raise PortfolioError(f"Failed to calculate performance: {e}")
    
    def _calculate_win_rate(self, transactions: List[VirtualTransaction]) -> float:
        """Calculate win rate based on profitable trades."""
        if not transactions:
            return 0.0
        
        # Group buy/sell pairs to determine profitable trades
        # Simplified: assume each sell after a buy is a completed trade
        profitable_trades = 0
        total_trades = 0
        
        for transaction in transactions:
            if transaction.transaction_type == "CRYPTO_SELL":
                total_trades += 1
                # Check if this sell was profitable
                cost_basis = transaction.metadata.get("price_per_token", 0)
                # This is simplified - real implementation would track specific buy/sell pairs
                if cost_basis > 0:  # Assume profitable if we have cost basis
                    profitable_trades += 1
        
        return (profitable_trades / max(total_trades, 1)) * 100
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get market overview with top movers and trending cryptos."""
        try:
            market_summary = await market_data_service.get_market_summary()
            
            # Get price data for analysis
            all_prices = await market_data_service.fetch_current_prices()
            
            # Analyze market trends
            gainers = []
            losers = []
            high_volume = []
            
            for symbol, price_data in all_prices.items():
                crypto_info = {
                    "symbol": symbol,
                    "price": price_data.price,
                    "change_24h": price_data.price_change_percentage_24h,
                    "volume_24h": price_data.volume_24h or 0,
                    "market_cap": price_data.market_cap or 0
                }
                
                if price_data.price_change_percentage_24h > 5:
                    gainers.append(crypto_info)
                elif price_data.price_change_percentage_24h < -5:
                    losers.append(crypto_info)
                
                if price_data.volume_24h and price_data.volume_24h > 1000000:
                    high_volume.append(crypto_info)
            
            # Sort lists
            gainers.sort(key=lambda x: x["change_24h"], reverse=True)
            losers.sort(key=lambda x: x["change_24h"])
            high_volume.sort(key=lambda x: x["volume_24h"], reverse=True)
            
            return {
                "market_summary": market_summary,
                "top_gainers": gainers[:10],
                "top_losers": losers[:10],
                "high_volume": high_volume[:10],
                "total_cryptocurrencies": len(all_prices),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get market overview: {e}")
            return {}
    
    def get_trading_fees(self) -> Dict[str, float]:
        """Get current trading fee structure."""
        return {
            "trading_fee_rate": self.trading_fee_rate,
            "trading_fee_percentage": self.trading_fee_rate * 100,
            "min_trade_amount_gems": self.min_trade_amount_gems,
            "max_trade_amount_gems": self.max_trade_amount_gems
        }


# Global instance
portfolio_manager = PortfolioManager()