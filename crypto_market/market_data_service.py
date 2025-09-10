"""
Market Data Service - Fetches and manages real-time cryptocurrency data.
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from .models import CryptoCurrency, PriceHistory, PriceData, CandlestickData, PriceInterval, CryptoMarketConstants
from .crypto_registry import crypto_registry
from logger import logger


class MarketDataService:
    """Service for fetching and managing cryptocurrency market data."""
    
    def __init__(self):
        self.base_url = CryptoMarketConstants.COINGECKO_API_BASE
        self.update_interval = CryptoMarketConstants.PRICE_UPDATE_INTERVAL
        self.session = None
        self.is_running = False
        self._price_cache = {}
        self._cache_expiry = {}
        self.cache_duration = 30  # 30 seconds cache
    
    async def start_service(self):
        """Start the market data service."""
        if self.is_running:
            return
        
        self.session = aiohttp.ClientSession()
        self.is_running = True
        
        # Initialize crypto registry
        async with get_db_session() as db_session:
            await crypto_registry.initialize_default_cryptos(db_session)
        
        # Start background price update task
        asyncio.create_task(self._price_update_loop())
        
        logger.info("Market data service started")
    
    async def stop_service(self):
        """Stop the market data service."""
        self.is_running = False
        
        if self.session:
            await self.session.close()
            self.session = None
        
        logger.info("Market data service stopped")
    
    async def _price_update_loop(self):
        """Background loop for updating cryptocurrency prices."""
        while self.is_running:
            try:
                await self.update_all_prices()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in price update loop: {e}")
                await asyncio.sleep(10)  # Wait 10 seconds before retrying
    
    async def fetch_current_prices(self, symbols: List[str] = None) -> Dict[str, PriceData]:
        """Fetch current prices from CoinGecko API."""
        
        if not self.session:
            await self.start_service()
        
        try:
            async with get_db_session() as db_session:
                # Get all active cryptocurrencies if no symbols provided
                if symbols is None:
                    cryptos = await crypto_registry.get_all_cryptos(db_session, active_only=True)
                    coingecko_ids = [crypto.coingecko_id for crypto in cryptos if crypto.coingecko_id]
                else:
                    cryptos = []
                    for symbol in symbols:
                        crypto = await crypto_registry.get_crypto_by_symbol(db_session, symbol)
                        if crypto and crypto.coingecko_id:
                            cryptos.append(crypto)
                    coingecko_ids = [crypto.coingecko_id for crypto in cryptos]
                
                if not coingecko_ids:
                    return {}
                
                # Build API URL
                ids_param = ",".join(coingecko_ids)
                url = f"{self.base_url}/simple/price"
                params = {
                    "ids": ids_param,
                    "vs_currencies": "usd",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true",
                    "include_24hr_change": "true",
                    "include_last_updated_at": "true"
                }
                
                async with self.session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"CoinGecko API error: {response.status}")
                        return {}
                    
                    data = await response.json()
                    
                    # Convert to PriceData objects
                    price_data = {}
                    crypto_lookup = {crypto.coingecko_id: crypto for crypto in cryptos}
                    
                    for coingecko_id, price_info in data.items():
                        if coingecko_id not in crypto_lookup:
                            continue
                        
                        crypto = crypto_lookup[coingecko_id]
                        
                        price_data[crypto.symbol] = PriceData(
                            symbol=crypto.symbol,
                            price=price_info.get("usd", 0.0),
                            price_change_24h=price_info.get("usd_24h_change", 0.0),
                            price_change_percentage_24h=price_info.get("usd_24h_change", 0.0),
                            market_cap=price_info.get("usd_market_cap"),
                            volume_24h=price_info.get("usd_24h_vol"),
                            timestamp=datetime.utcnow()
                        )
                    
                    # Cache the results
                    current_time = datetime.utcnow()
                    for symbol, data in price_data.items():
                        self._price_cache[symbol] = data
                        self._cache_expiry[symbol] = current_time + timedelta(seconds=self.cache_duration)
                    
                    return price_data
                    
        except Exception as e:
            logger.error(f"Failed to fetch prices from CoinGecko: {e}")
            return {}
    
    async def get_cached_price(self, symbol: str) -> Optional[PriceData]:
        """Get price from cache if available and valid."""
        
        if symbol not in self._price_cache:
            return None
        
        if symbol in self._cache_expiry and datetime.utcnow() > self._cache_expiry[symbol]:
            # Cache expired
            del self._price_cache[symbol]
            del self._cache_expiry[symbol]
            return None
        
        return self._price_cache[symbol]
    
    async def get_current_price(self, symbol: str) -> Optional[PriceData]:
        """Get current price for a single cryptocurrency."""
        
        # Check cache first
        cached_price = await self.get_cached_price(symbol)
        if cached_price:
            return cached_price
        
        # Fetch from API
        prices = await self.fetch_current_prices([symbol])
        return prices.get(symbol)
    
    async def update_all_prices(self) -> int:
        """Update all cryptocurrency prices in the database."""
        
        try:
            # Fetch current prices
            prices = await self.fetch_current_prices()
            
            if not prices:
                return 0
            
            # Update database
            async with get_db_session() as db_session:
                price_updates = {}
                for symbol, price_data in prices.items():
                    price_updates[symbol] = {
                        "price": price_data.price,
                        "market_cap": price_data.market_cap,
                        "volume_24h": price_data.volume_24h,
                        "price_change_24h": price_data.price_change_24h,
                        "price_change_percentage_24h": price_data.price_change_percentage_24h
                    }
                
                updated_count = await crypto_registry.update_crypto_prices(db_session, price_updates)
                
                # Store historical data
                await self._store_price_history(db_session, prices)
                
                logger.info(f"Updated prices for {updated_count} cryptocurrencies")
                return updated_count
                
        except Exception as e:
            logger.error(f"Failed to update all prices: {e}")
            return 0
    
    async def _store_price_history(
        self, 
        session: AsyncSession, 
        prices: Dict[str, PriceData]
    ):
        """Store price data as historical records."""
        
        try:
            for symbol, price_data in prices.items():
                crypto = await crypto_registry.get_crypto_by_symbol(session, symbol)
                if not crypto:
                    continue
                
                # Create 1-minute price history entry
                price_history = PriceHistory(
                    crypto_id=crypto.id,
                    symbol=symbol,
                    timestamp=price_data.timestamp,
                    interval="1m",
                    open_price=price_data.price,  # For real-time data, all OHLC values are the same
                    high_price=price_data.price,
                    low_price=price_data.price,
                    close_price=price_data.price,
                    volume=price_data.volume_24h or 0.0,
                    market_cap=price_data.market_cap,
                    price_change=price_data.price_change_24h,
                    price_change_percentage=price_data.price_change_percentage_24h,
                    source="COINGECKO"
                )
                
                session.add(price_history)
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to store price history: {e}")
            await session.rollback()
    
    async def get_price_history(
        self, 
        symbol: str, 
        interval: PriceInterval = PriceInterval.ONE_HOUR,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[CandlestickData]:
        """Get historical price data for a cryptocurrency."""
        
        try:
            async with get_db_session() as db_session:
                crypto = await crypto_registry.get_crypto_by_symbol(db_session, symbol)
                if not crypto:
                    return []
                
                # Build query
                from sqlalchemy import select, and_
                query = select(PriceHistory).where(
                    and_(
                        PriceHistory.crypto_id == crypto.id,
                        PriceHistory.interval == interval.value
                    )
                )
                
                # Add time filters
                if start_time:
                    query = query.where(PriceHistory.timestamp >= start_time)
                if end_time:
                    query = query.where(PriceHistory.timestamp <= end_time)
                
                query = query.order_by(PriceHistory.timestamp.desc()).limit(limit)
                
                result = await db_session.execute(query)
                history_records = result.scalars().all()
                
                # Convert to CandlestickData
                candlesticks = []
                for record in reversed(history_records):  # Reverse to get chronological order
                    candlesticks.append(CandlestickData(
                        symbol=record.symbol,
                        timestamp=record.timestamp,
                        open_price=record.open_price,
                        high_price=record.high_price,
                        low_price=record.low_price,
                        close_price=record.close_price,
                        volume=record.volume,
                        interval=PriceInterval(record.interval)
                    ))
                
                return candlesticks
                
        except Exception as e:
            logger.error(f"Failed to get price history for {symbol}: {e}")
            return []
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """Get overall market summary."""
        
        try:
            async with get_db_session() as db_session:
                market_overview = await crypto_registry.get_market_overview(db_session)
                
                # Add real-time price cache status
                cache_status = {
                    "cached_prices": len(self._price_cache),
                    "cache_hit_rate": len(self._price_cache) / max(1, len(market_overview.get("top_cryptocurrencies", []))),
                    "last_update": max(
                        [data.timestamp for data in self._price_cache.values()],
                        default=datetime.utcnow()
                    ).isoformat() if self._price_cache else None
                }
                
                market_overview["cache_status"] = cache_status
                return market_overview
                
        except Exception as e:
            logger.error(f"Failed to get market summary: {e}")
            return {}
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old price history data."""
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            async with get_db_session() as db_session:
                from sqlalchemy import delete
                
                # Delete old price history
                await db_session.execute(
                    delete(PriceHistory).where(PriceHistory.timestamp < cutoff_date)
                )
                
                await db_session.commit()
                logger.info(f"Cleaned up price history older than {days_to_keep} days")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        
        current_time = datetime.utcnow()
        valid_entries = 0
        
        for symbol in self._price_cache:
            if symbol in self._cache_expiry and current_time <= self._cache_expiry[symbol]:
                valid_entries += 1
        
        return {
            "total_cached": len(self._price_cache),
            "valid_entries": valid_entries,
            "cache_hit_rate": valid_entries / max(1, len(self._price_cache)),
            "cache_duration": self.cache_duration,
            "update_interval": self.update_interval
        }


# Global instance
market_data_service = MarketDataService()