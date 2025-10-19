"""
Stock Data Service
Fetches and caches stock price data from external APIs (Yahoo Finance, Alpha Vantage).
Handles price lookups, historical data, and stock information.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import yfinance as yf

from database.models import StockMetadata, StockPriceCache

logger = logging.getLogger(__name__)


class StockDataService:
    """Service for fetching and caching stock market data."""

    def __init__(self):
        """Initialize stock data service with caching."""
        self.cache_duration_minutes = 5  # Stock prices cache for 5 minutes
        self.history_cache_duration_minutes = 60  # Historical data cache for 1 hour
        self.info_cache_duration_hours = 24  # Stock info cache for 24 hours

        # In-memory cache for quick lookups (Redis alternative)
        self._memory_cache = {}

    def _is_cache_valid(self, last_updated: datetime, duration_minutes: int) -> bool:
        """Check if cached data is still valid."""
        if not last_updated:
            return False
        age = datetime.utcnow() - last_updated
        return age < timedelta(minutes=duration_minutes)

    async def get_stock_price(self, ticker: str, db: AsyncSession) -> Optional[Dict]:
        """
        Get current stock price with caching.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            db: Database session

        Returns:
            Dict with price data or None if not found
        """
        try:
            # Check memory cache first
            cache_key = f"price_{ticker}"
            if cache_key in self._memory_cache:
                cached_data, cached_time = self._memory_cache[cache_key]
                if self._is_cache_valid(cached_time, self.cache_duration_minutes):
                    logger.debug(f"Memory cache hit for {ticker}")
                    return cached_data

            # Check database cache
            result = await db.execute(
                select(StockPriceCache).where(StockPriceCache.ticker == ticker.upper())
            )
            db_cache = result.scalar_one_or_none()

            if db_cache and self._is_cache_valid(db_cache.last_updated, self.cache_duration_minutes):
                logger.debug(f"DB cache hit for {ticker}")
                price_data = db_cache.to_dict()
                self._memory_cache[cache_key] = (price_data, db_cache.last_updated)
                return price_data

            # Fetch fresh data from Yahoo Finance
            logger.info(f"Fetching fresh price data for {ticker}")
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or 'currentPrice' not in info:
                # Try alternative price field
                current_price = info.get('regularMarketPrice') or info.get('previousClose')
                if not current_price:
                    logger.warning(f"No price data available for {ticker}")
                    return None
            else:
                current_price = info['currentPrice']

            # Build price data
            price_data = {
                "ticker": ticker.upper(),
                "current_price_usd": float(current_price),
                "price_change_pct": float(info.get('regularMarketChangePercent', 0) or 0),
                "volume": int(info.get('volume', 0) or 0),
                "market_cap": int(info.get('marketCap', 0) or 0),
                "day_high": float(info.get('dayHigh', 0) or current_price),
                "day_low": float(info.get('dayLow', 0) or current_price),
                "open_price": float(info.get('open', 0) or current_price),
                "prev_close": float(info.get('previousClose', 0) or current_price),
                "last_updated": datetime.utcnow().isoformat(),
                "data_source": "yahoo_finance"
            }

            # Update database cache
            if db_cache:
                db_cache.current_price_usd = price_data["current_price_usd"]
                db_cache.price_change_pct = price_data["price_change_pct"]
                db_cache.volume = price_data["volume"]
                db_cache.market_cap = price_data["market_cap"]
                db_cache.day_high = price_data["day_high"]
                db_cache.day_low = price_data["day_low"]
                db_cache.open_price = price_data["open_price"]
                db_cache.prev_close = price_data["prev_close"]
                db_cache.last_updated = datetime.utcnow()
                db_cache.data_source = "yahoo_finance"
            else:
                db_cache = StockPriceCache(
                    ticker=ticker.upper(),
                    current_price_usd=price_data["current_price_usd"],
                    price_change_pct=price_data["price_change_pct"],
                    volume=price_data["volume"],
                    market_cap=price_data["market_cap"],
                    day_high=price_data["day_high"],
                    day_low=price_data["day_low"],
                    open_price=price_data["open_price"],
                    prev_close=price_data["prev_close"],
                    data_source="yahoo_finance"
                )
                db.add(db_cache)

            await db.commit()

            # Update memory cache
            self._memory_cache[cache_key] = (price_data, datetime.utcnow())

            return price_data

        except Exception as e:
            logger.error(f"Error fetching price for {ticker}: {e}")
            return None

    async def get_stock_history(
        self,
        ticker: str,
        period: str = "1mo"
    ) -> Optional[List[Dict]]:
        """
        Get historical price data for charts.

        Args:
            ticker: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 1y, 5y)

        Returns:
            List of price data points or None
        """
        try:
            # Check memory cache
            cache_key = f"history_{ticker}_{period}"
            if cache_key in self._memory_cache:
                cached_data, cached_time = self._memory_cache[cache_key]
                if self._is_cache_valid(cached_time, self.history_cache_duration_minutes):
                    logger.debug(f"Memory cache hit for {ticker} history")
                    return cached_data

            logger.info(f"Fetching historical data for {ticker} ({period})")
            stock = yf.Ticker(ticker)

            # Fetch historical data
            hist = stock.history(period=period)

            if hist.empty:
                logger.warning(f"No historical data for {ticker}")
                return None

            # Format for Chart.js
            history_data = []
            for index, row in hist.iterrows():
                history_data.append({
                    "date": index.strftime("%Y-%m-%d"),
                    "timestamp": int(index.timestamp() * 1000),  # JS timestamp
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close']),
                    "volume": int(row['Volume'])
                })

            # Cache the result
            self._memory_cache[cache_key] = (history_data, datetime.utcnow())

            return history_data

        except Exception as e:
            logger.error(f"Error fetching history for {ticker}: {e}")
            return None

    async def get_stock_info(self, ticker: str, db: AsyncSession) -> Optional[Dict]:
        """
        Get detailed stock information.

        Args:
            ticker: Stock ticker symbol
            db: Database session

        Returns:
            Dict with stock info or None
        """
        try:
            # Get metadata from database first
            result = await db.execute(
                select(StockMetadata).where(StockMetadata.ticker == ticker.upper())
            )
            metadata = result.scalar_one_or_none()

            if not metadata:
                logger.warning(f"Stock {ticker} not found in database")
                return None

            # Check memory cache for extended info
            cache_key = f"info_{ticker}"
            if cache_key in self._memory_cache:
                cached_data, cached_time = self._memory_cache[cache_key]
                age_hours = (datetime.utcnow() - cached_time).total_seconds() / 3600
                if age_hours < self.info_cache_duration_hours:
                    logger.debug(f"Memory cache hit for {ticker} info")
                    return cached_data

            # Fetch extended info from Yahoo Finance
            logger.info(f"Fetching stock info for {ticker}")
            stock = yf.Ticker(ticker)
            info = stock.info

            # Combine metadata with live data
            stock_info = {
                "ticker": ticker.upper(),
                "company_name": metadata.company_name,
                "sector": metadata.sector,
                "industry": metadata.industry,
                "website": metadata.website or info.get('website', ''),
                "description": metadata.description or info.get('longBusinessSummary', ''),
                "logo_url": metadata.logo_url,
                "current_price": info.get('currentPrice') or info.get('regularMarketPrice'),
                "market_cap": info.get('marketCap'),
                "pe_ratio": info.get('trailingPE'),
                "dividend_yield": info.get('dividendYield'),
                "52_week_high": info.get('fiftyTwoWeekHigh'),
                "52_week_low": info.get('fiftyTwoWeekLow'),
                "avg_volume": info.get('averageVolume'),
                "beta": info.get('beta'),
                "is_active": metadata.is_active
            }

            # Cache the result
            self._memory_cache[cache_key] = (stock_info, datetime.utcnow())

            return stock_info

        except Exception as e:
            logger.error(f"Error fetching info for {ticker}: {e}")
            return None

    async def search_stocks(self, query: str, db: AsyncSession) -> List[Dict]:
        """
        Search stocks by ticker or company name.

        Args:
            query: Search query string
            db: Database session

        Returns:
            List of matching stocks
        """
        try:
            query_upper = query.upper()

            # Search in database metadata
            result = await db.execute(
                select(StockMetadata).where(
                    (StockMetadata.ticker.like(f"%{query_upper}%")) |
                    (StockMetadata.company_name.ilike(f"%{query}%"))
                ).filter(StockMetadata.is_active == True).limit(20)
            )
            stocks = result.scalars().all()

            # Format results
            results = []
            for stock in stocks:
                results.append({
                    "ticker": stock.ticker,
                    "company_name": stock.company_name,
                    "sector": stock.sector,
                    "industry": stock.industry
                })

            return results

        except Exception as e:
            logger.error(f"Error searching stocks: {e}")
            return []

    async def get_market_overview(self, db: AsyncSession) -> Dict:
        """
        Get market summary with top gainers, losers, and most active.

        Returns:
            Dict with market overview data
        """
        try:
            # Get all active stocks from metadata
            result = await db.execute(
                select(StockMetadata).where(StockMetadata.is_active == True)
            )
            all_stocks = result.scalars().all()

            # Get prices for all stocks (this may be slow, consider optimizing)
            stock_prices = []
            for stock in all_stocks[:50]:  # Limit to first 50 for performance
                price_data = await self.get_stock_price(stock.ticker, db)
                if price_data:
                    stock_prices.append({
                        "ticker": stock.ticker,
                        "company_name": stock.company_name,
                        "current_price_usd": price_data["current_price_usd"],
                        "price_change_pct": price_data["price_change_pct"],
                        "volume": price_data["volume"]
                    })

            # Sort by different criteria
            gainers = sorted(stock_prices, key=lambda x: x["price_change_pct"], reverse=True)[:10]
            losers = sorted(stock_prices, key=lambda x: x["price_change_pct"])[:10]
            most_active = sorted(stock_prices, key=lambda x: x["volume"], reverse=True)[:10]

            return {
                "top_gainers": gainers,
                "top_losers": losers,
                "most_active": most_active,
                "total_stocks": len(all_stocks),
                "last_updated": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching market overview: {e}")
            return {
                "top_gainers": [],
                "top_losers": [],
                "most_active": [],
                "total_stocks": 0,
                "last_updated": datetime.utcnow().isoformat()
            }

    def clear_cache(self):
        """Clear all cached data."""
        self._memory_cache.clear()
        logger.info("Stock data cache cleared")


# Global instance
stock_data_service = StockDataService()
