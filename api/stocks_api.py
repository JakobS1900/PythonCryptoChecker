"""
Stock Market API Endpoints
Provides REST API for virtual stock trading system.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import User
from api.auth_api import get_current_user, require_authentication
from services.stock_data_service import stock_data_service
from services.stock_trading_service import stock_trading_service
from services.stock_portfolio_service import stock_portfolio_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


# ==================== REQUEST/RESPONSE MODELS ====================

class BuyStockRequest(BaseModel):
    """Request model for buying stocks."""
    quantity: float = Field(..., gt=0, description="Number of shares to buy")


class SellStockRequest(BaseModel):
    """Request model for selling stocks."""
    quantity: float = Field(..., gt=0, description="Number of shares to sell")


class StockQuoteResponse(BaseModel):
    """Response model for stock quote."""
    ticker: str
    company_name: str
    quantity: float
    price_per_share_usd: float
    price_per_share_gem: float
    subtotal_gem: float
    fee_gem: float
    total_cost_gem: float
    user_balance_gem: float
    sufficient_funds: bool
    price_change_pct: float


class TradeResponse(BaseModel):
    """Response model for trade execution."""
    success: bool
    transaction_id: str
    ticker: str
    company_name: str
    transaction_type: str
    quantity: float
    price_per_share_usd: float
    price_per_share_gem: float
    subtotal_gem: float
    fee_gem: float
    total_cost_gem: Optional[float] = None  # For buys
    net_proceeds_gem: Optional[float] = None  # For sells
    profit_loss_gem: Optional[float] = None  # For sells
    profit_loss_pct: Optional[float] = None  # For sells
    new_balance_gem: float


# ==================== STOCK BROWSING ENDPOINTS ====================

@router.get("/")
async def list_stocks(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    search: Optional[str] = Query(None, description="Search by ticker or company name"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of stocks to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    List available stocks with optional filtering.

    Returns:
        List of stocks with basic information
    """
    try:
        from sqlalchemy import select
        from database.models import StockMetadata

        # Build query
        query = select(StockMetadata).where(StockMetadata.is_active == True)

        if sector:
            query = query.where(StockMetadata.sector == sector)

        if search:
            search_upper = search.upper()
            query = query.where(
                (StockMetadata.ticker.like(f"%{search_upper}%")) |
                (StockMetadata.company_name.ilike(f"%{search}%"))
            )

        query = query.limit(limit)

        result = await db.execute(query)
        stocks = result.scalars().all()

        # Get current prices for each stock
        stocks_with_prices = []
        for stock in stocks:
            price_data = await stock_data_service.get_stock_price(stock.ticker, db)

            stock_info = {
                "ticker": stock.ticker,
                "company_name": stock.company_name,
                "sector": stock.sector,
                "industry": stock.industry,
            }

            if price_data:
                stock_info.update({
                    "current_price_usd": price_data["current_price_usd"],
                    "current_price_gem": price_data["current_price_usd"] / 0.01,
                    "price_change_pct": price_data.get("price_change_pct", 0),
                    "volume": price_data.get("volume", 0),
                    "market_cap": price_data.get("market_cap", 0)
                })

            stocks_with_prices.append(stock_info)

        return {
            "success": True,
            "stocks": stocks_with_prices,
            "total": len(stocks_with_prices)
        }

    except Exception as e:
        logger.error(f"Error listing stocks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list stocks: {str(e)}")


@router.get("/search")
async def search_stocks(
    q: str = Query(..., min_length=1, description="Search query"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search stocks by ticker or company name.

    Args:
        q: Search query string

    Returns:
        List of matching stocks
    """
    try:
        results = await stock_data_service.search_stocks(q, db)

        return {
            "success": True,
            "query": q,
            "results": results,
            "total": len(results)
        }

    except Exception as e:
        logger.error(f"Error searching stocks: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/market/overview")
async def get_market_overview(db: AsyncSession = Depends(get_db)):
    """
    Get market overview with top gainers, losers, and most active stocks.

    Returns:
        Market summary data
    """
    try:
        overview = await stock_data_service.get_market_overview(db)

        return {
            "success": True,
            "overview": overview
        }

    except Exception as e:
        logger.error(f"Error fetching market overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch market overview: {str(e)}")


@router.get("/{ticker}")
async def get_stock_detail(
    ticker: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific stock.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Detailed stock information with current price
    """
    try:
        ticker = ticker.upper()

        # Get stock info
        stock_info = await stock_data_service.get_stock_info(ticker, db)

        if not stock_info:
            raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

        # Get current price
        price_data = await stock_data_service.get_stock_price(ticker, db)

        if price_data:
            stock_info.update({
                "current_price_usd": price_data["current_price_usd"],
                "current_price_gem": price_data["current_price_usd"] / 0.01,
                "price_change_pct": price_data.get("price_change_pct", 0),
                "volume": price_data.get("volume", 0),
                "day_high": price_data.get("day_high"),
                "day_low": price_data.get("day_low"),
                "last_updated": price_data.get("last_updated")
            })

        return {
            "success": True,
            "stock": stock_info
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stock detail: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stock detail: {str(e)}")


@router.get("/{ticker}/chart")
async def get_stock_chart(
    ticker: str,
    period: str = Query("1mo", regex="^(1d|5d|1mo|3mo|1y|5y)$", description="Time period")
):
    """
    Get historical price data for charts.

    Args:
        ticker: Stock ticker symbol
        period: Time period (1d, 5d, 1mo, 3mo, 1y, 5y)

    Returns:
        Historical price data formatted for Chart.js
    """
    try:
        ticker = ticker.upper()

        history = await stock_data_service.get_stock_history(ticker, period)

        if not history:
            raise HTTPException(status_code=404, detail=f"No historical data for {ticker}")

        return {
            "success": True,
            "ticker": ticker,
            "period": period,
            "data": history
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stock chart: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch chart data: {str(e)}")


# ==================== TRADING ENDPOINTS ====================

@router.post("/{ticker}/quote")
async def get_buy_quote(
    ticker: str,
    request: BuyStockRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a quote for buying stocks without executing the trade.

    Args:
        ticker: Stock ticker symbol
        request: Buy request with quantity

    Returns:
        Quote with cost breakdown
    """
    try:
        quote = await stock_trading_service.get_buy_quote(
            user_id=current_user.id,
            ticker=ticker,
            quantity=request.quantity,
            db=db
        )

        return {
            "success": True,
            "quote": quote
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting quote: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get quote: {str(e)}")


@router.post("/{ticker}/buy")
async def buy_stock(
    ticker: str,
    request: BuyStockRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Buy stock shares.

    Args:
        ticker: Stock ticker symbol
        request: Buy request with quantity

    Returns:
        Transaction details
    """
    try:
        result = await stock_trading_service.buy_stock(
            user_id=current_user.id,
            ticker=ticker,
            quantity=request.quantity,
            db=db
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error buying stock: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to buy stock: {str(e)}")


@router.post("/{ticker}/sell")
async def sell_stock(
    ticker: str,
    request: SellStockRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Sell stock shares.

    Args:
        ticker: Stock ticker symbol
        request: Sell request with quantity

    Returns:
        Transaction details with P/L
    """
    try:
        result = await stock_trading_service.sell_stock(
            user_id=current_user.id,
            ticker=ticker,
            quantity=request.quantity,
            db=db
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error selling stock: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sell stock: {str(e)}")


# ==================== PORTFOLIO ENDPOINTS ====================

@router.get("/portfolio/summary")
async def get_portfolio_summary(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get portfolio summary with total value, P/L, and diversification.

    Returns:
        Portfolio summary data
    """
    try:
        summary = await stock_portfolio_service.get_portfolio_summary(
            user_id=current_user.id,
            db=db
        )

        return {
            "success": True,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error fetching portfolio summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch portfolio summary: {str(e)}")


@router.get("/portfolio/holdings")
async def get_holdings(
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all stock holdings with P/L calculations.

    Returns:
        List of holdings
    """
    try:
        holdings = await stock_portfolio_service.get_holdings(
            user_id=current_user.id,
            db=db
        )

        return {
            "success": True,
            "holdings": holdings,
            "total": len(holdings)
        }

    except Exception as e:
        logger.error(f"Error fetching holdings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch holdings: {str(e)}")


@router.get("/portfolio/transactions")
async def get_transactions(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of transactions"),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    transaction_type: Optional[str] = Query(None, regex="^(BUY|SELL)$", description="Filter by type"),
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get stock transaction history.

    Args:
        limit: Maximum number of transactions
        ticker: Filter by stock ticker (optional)
        transaction_type: Filter by BUY or SELL (optional)

    Returns:
        List of transactions
    """
    try:
        transactions = await stock_portfolio_service.get_transaction_history(
            user_id=current_user.id,
            limit=limit,
            ticker=ticker,
            transaction_type=transaction_type,
            db=db
        )

        return {
            "success": True,
            "transactions": transactions,
            "total": len(transactions)
        }

    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch transactions: {str(e)}")


@router.get("/portfolio/performance")
async def get_performance(
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get portfolio performance over time.

    Args:
        days: Number of days to look back

    Returns:
        Portfolio performance data for charts
    """
    try:
        performance = await stock_portfolio_service.get_portfolio_performance(
            user_id=current_user.id,
            days=days,
            db=db
        )

        return {
            "success": True,
            "performance": performance,
            "days": days
        }

    except Exception as e:
        logger.error(f"Error fetching performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch performance: {str(e)}")


@router.get("/portfolio/position/{ticker}")
async def get_position(
    ticker: str,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific stock position.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Position details with P/L and recent transactions
    """
    try:
        position = await stock_portfolio_service.get_stock_position(
            user_id=current_user.id,
            ticker=ticker,
            db=db
        )

        if not position:
            raise HTTPException(status_code=404, detail=f"No position found for {ticker}")

        return {
            "success": True,
            "position": position
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching position: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch position: {str(e)}")
