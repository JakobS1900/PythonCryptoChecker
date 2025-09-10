"""
Trading API - RESTful endpoints for cryptocurrency trading and portfolio management.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from auth.middleware import get_current_user
from .portfolio_manager import portfolio_manager, PortfolioError, InsufficientFundsError, InvalidTradeError
from crypto_market import market_data_service
from logger import logger

router = APIRouter()
security = HTTPBearer()


# Pydantic Models
class BuyOrderRequest(BaseModel):
    crypto_symbol: str = Field(..., description="Cryptocurrency symbol (e.g., BTC, ETH)")
    amount_gems: float = Field(..., gt=0, description="Amount in GEM coins to spend")
    order_type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT)$")


class SellOrderRequest(BaseModel):
    crypto_symbol: str = Field(..., description="Cryptocurrency symbol to sell")
    crypto_amount: float = Field(..., gt=0, description="Amount of cryptocurrency to sell")
    order_type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT)$")


class PortfolioResponse(BaseModel):
    user_id: str
    wallet_balance_gems: float
    total_crypto_value_gems: float
    total_portfolio_value_gems: float
    total_profit_loss_gems: float
    total_profit_loss_percentage: float
    holdings: List[Dict[str, Any]]


class TradeResponse(BaseModel):
    transaction_id: str
    crypto_symbol: str
    status: str
    timestamp: str


class MarketDataResponse(BaseModel):
    symbol: str
    price: float
    change_24h: float
    volume_24h: Optional[float]
    market_cap: Optional[float]
    timestamp: str


@router.get("/portfolio", response_model=Dict[str, Any])
async def get_portfolio(
    current_user: dict = Depends(get_current_user)
):
    """Get user's cryptocurrency portfolio."""
    try:
        portfolio = await portfolio_manager.get_user_portfolio(current_user["user_id"])
        return {
            "success": True,
            "data": portfolio
        }
    except PortfolioError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Portfolio endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/buy", response_model=Dict[str, Any])
async def buy_cryptocurrency(
    order: BuyOrderRequest,
    current_user: dict = Depends(get_current_user)
):
    """Buy cryptocurrency with GEM coins."""
    try:
        result = await portfolio_manager.buy_cryptocurrency(
            user_id=current_user["user_id"],
            crypto_symbol=order.crypto_symbol.upper(),
            amount_gems=order.amount_gems,
            order_type=order.order_type
        )
        return {
            "success": True,
            "data": result,
            "message": f"Successfully bought {order.crypto_symbol}"
        }
    except InvalidTradeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InsufficientFundsError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except PortfolioError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Buy endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sell", response_model=Dict[str, Any])
async def sell_cryptocurrency(
    order: SellOrderRequest,
    current_user: dict = Depends(get_current_user)
):
    """Sell cryptocurrency for GEM coins."""
    try:
        result = await portfolio_manager.sell_cryptocurrency(
            user_id=current_user["user_id"],
            crypto_symbol=order.crypto_symbol.upper(),
            crypto_amount=order.crypto_amount,
            order_type=order.order_type
        )
        return {
            "success": True,
            "data": result,
            "message": f"Successfully sold {order.crypto_symbol}"
        }
    except InvalidTradeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InsufficientFundsError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except PortfolioError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sell endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/history", response_model=Dict[str, Any])
async def get_trading_history(
    limit: int = 50,
    crypto_symbol: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get user's trading history."""
    try:
        history = await portfolio_manager.get_trading_history(
            user_id=current_user["user_id"],
            limit=min(limit, 200),  # Max 200 records
            crypto_symbol=crypto_symbol.upper() if crypto_symbol else None
        )
        return {
            "success": True,
            "data": {
                "transactions": history,
                "total_count": len(history)
            }
        }
    except PortfolioError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Trading history endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/performance", response_model=Dict[str, Any])
async def get_portfolio_performance(
    period_days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get portfolio performance metrics."""
    try:
        performance = await portfolio_manager.get_portfolio_performance(
            user_id=current_user["user_id"],
            period_days=min(period_days, 365)  # Max 1 year
        )
        return {
            "success": True,
            "data": performance
        }
    except PortfolioError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Performance endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/market/overview", response_model=Dict[str, Any])
async def get_market_overview():
    """Get market overview with top movers and trends."""
    try:
        overview = await portfolio_manager.get_market_overview()
        return {
            "success": True,
            "data": overview
        }
    except Exception as e:
        logger.error(f"Market overview endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/market/price/{symbol}", response_model=Dict[str, Any])
async def get_crypto_price(symbol: str):
    """Get current price for a specific cryptocurrency."""
    try:
        price_data = await market_data_service.get_current_price(symbol.upper())
        if not price_data:
            raise HTTPException(status_code=404, detail=f"Price data not found for {symbol}")
        
        return {
            "success": True,
            "data": {
                "symbol": price_data.symbol,
                "price": price_data.price,
                "change_24h": price_data.price_change_24h,
                "change_24h_percentage": price_data.price_change_percentage_24h,
                "market_cap": price_data.market_cap,
                "volume_24h": price_data.volume_24h,
                "timestamp": price_data.timestamp.isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Price endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/market/prices", response_model=Dict[str, Any])
async def get_all_crypto_prices():
    """Get current prices for all cryptocurrencies."""
    try:
        all_prices = await market_data_service.fetch_current_prices()
        
        price_list = []
        for symbol, price_data in all_prices.items():
            price_list.append({
                "symbol": symbol,
                "price": price_data.price,
                "change_24h": price_data.price_change_24h,
                "change_24h_percentage": price_data.price_change_percentage_24h,
                "market_cap": price_data.market_cap,
                "volume_24h": price_data.volume_24h,
                "timestamp": price_data.timestamp.isoformat()
            })
        
        # Sort by market cap (descending)
        price_list.sort(key=lambda x: x.get("market_cap", 0) or 0, reverse=True)
        
        return {
            "success": True,
            "data": {
                "prices": price_list,
                "total_count": len(price_list),
                "last_updated": max(p["timestamp"] for p in price_list) if price_list else None
            }
        }
    except Exception as e:
        logger.error(f"All prices endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/trading/fees", response_model=Dict[str, Any])
async def get_trading_fees():
    """Get current trading fee structure."""
    try:
        fees = portfolio_manager.get_trading_fees()
        return {
            "success": True,
            "data": fees
        }
    except Exception as e:
        logger.error(f"Trading fees endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/market/search/{query}", response_model=Dict[str, Any])
async def search_cryptocurrencies(query: str):
    """Search cryptocurrencies by name or symbol."""
    try:
        async with get_db_session() as session:
            from crypto_market.crypto_registry import crypto_registry
            
            cryptos = await crypto_registry.search_cryptos(session, query, limit=20)
            
            crypto_list = []
            for crypto in cryptos:
                # Get current price if available
                price_data = await market_data_service.get_current_price(crypto.symbol)
                
                crypto_info = {
                    "symbol": crypto.symbol,
                    "name": crypto.name,
                    "category": crypto.category,
                    "is_tradeable": crypto.is_tradeable,
                    "current_price": price_data.price if price_data else crypto.current_price,
                    "market_cap": price_data.market_cap if price_data else crypto.market_cap,
                    "change_24h_percentage": price_data.price_change_percentage_24h if price_data else crypto.price_change_percentage_24h
                }
                crypto_list.append(crypto_info)
            
            return {
                "success": True,
                "data": {
                    "query": query,
                    "results": crypto_list,
                    "total_count": len(crypto_list)
                }
            }
    except Exception as e:
        logger.error(f"Search endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/holdings/{symbol}", response_model=Dict[str, Any])
async def get_crypto_holding(
    symbol: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific crypto holding."""
    try:
        portfolio = await portfolio_manager.get_user_portfolio(current_user["user_id"])
        
        # Find the specific holding
        holding = None
        for h in portfolio["holdings"]:
            if h["symbol"].upper() == symbol.upper():
                holding = h
                break
        
        if not holding:
            raise HTTPException(status_code=404, detail=f"No holding found for {symbol}")
        
        # Get additional market data
        price_data = await market_data_service.get_current_price(symbol.upper())
        
        detailed_holding = {
            **holding,
            "24h_high": getattr(price_data, 'high_24h', None) if price_data else None,
            "24h_low": getattr(price_data, 'low_24h', None) if price_data else None,
            "market_cap": price_data.market_cap if price_data else None,
            "volume_24h": price_data.volume_24h if price_data else None,
            "allocation_percentage": (holding["current_value_gems"] / portfolio["total_portfolio_value_gems"] * 100) if portfolio["total_portfolio_value_gems"] > 0 else 0
        }
        
        return {
            "success": True,
            "data": detailed_holding
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Holding detail endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics/summary", response_model=Dict[str, Any])
async def get_portfolio_analytics(
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive portfolio analytics."""
    try:
        # Get portfolio data
        portfolio = await portfolio_manager.get_user_portfolio(current_user["user_id"])
        
        # Get performance data
        performance_7d = await portfolio_manager.get_portfolio_performance(current_user["user_id"], 7)
        performance_30d = await portfolio_manager.get_portfolio_performance(current_user["user_id"], 30)
        
        # Calculate analytics
        analytics = {
            "portfolio_summary": {
                "total_value_gems": portfolio["total_portfolio_value_gems"],
                "crypto_value_gems": portfolio["total_crypto_value_gems"],
                "cash_gems": portfolio["wallet_balance_gems"],
                "total_holdings": portfolio["holdings_count"],
                "diversification_score": len(portfolio["holdings"]) * 10  # Simple diversity score
            },
            "performance": {
                "7_day": {
                    "roi_percentage": performance_7d.get("roi_percentage", 0),
                    "profit_loss_gems": performance_7d.get("total_performance_gems", 0),
                    "transactions": performance_7d.get("transactions_count", 0)
                },
                "30_day": {
                    "roi_percentage": performance_30d.get("roi_percentage", 0),
                    "profit_loss_gems": performance_30d.get("total_performance_gems", 0),
                    "transactions": performance_30d.get("transactions_count", 0)
                }
            },
            "allocation": {
                "cash_percentage": portfolio["cash_percentage"],
                "crypto_percentage": portfolio["crypto_percentage"],
                "top_holdings": sorted(portfolio["holdings"], key=lambda x: x["current_value_gems"], reverse=True)[:5]
            },
            "trading_metrics": {
                "total_fees_paid_30d": performance_30d.get("trading_fees_paid_gems", 0),
                "win_rate_30d": performance_30d.get("win_rate", 0),
                "avg_transaction_value": performance_30d.get("average_transaction_value", 0)
            }
        }
        
        return {
            "success": True,
            "data": analytics
        }
    except Exception as e:
        logger.error(f"Analytics endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")