"""
Crypto Registry - Manages all supported cryptocurrencies and their metadata.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func

from database import get_db_session
from .models import CryptoCurrency, CryptoMarketConstants
from logger import logger


class CryptoRegistry:
    """Manages the registry of all supported cryptocurrencies."""
    
    def __init__(self):
        self._cache = {}
        self._last_cache_update = None
        self.cache_duration = 300  # 5 minutes
    
    async def initialize_default_cryptos(self, session: AsyncSession) -> bool:
        """Initialize the database with default cryptocurrency list."""
        
        try:
            # Check if cryptos already exist
            result = await session.execute(select(func.count(CryptoCurrency.id)))
            count = result.scalar()
            
            if count > 0:
                logger.info(f"Crypto registry already initialized with {count} cryptocurrencies")
                return True
            
            # Add all default cryptocurrencies
            cryptos_added = 0
            for crypto_data in CryptoMarketConstants.TOP_CRYPTOS:
                crypto = CryptoCurrency(
                    symbol=crypto_data["symbol"],
                    name=crypto_data["name"],
                    coingecko_id=crypto_data["coingecko_id"],
                    category=crypto_data["category"],
                    is_tradeable=True,
                    is_active=True
                )
                session.add(crypto)
                cryptos_added += 1
            
            await session.commit()
            logger.info(f"Initialized crypto registry with {cryptos_added} cryptocurrencies")
            
            # Clear cache to force refresh
            self._cache.clear()
            self._last_cache_update = None
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize crypto registry: {e}")
            await session.rollback()
            return False
    
    async def get_all_cryptos(
        self, 
        session: AsyncSession, 
        active_only: bool = True,
        tradeable_only: bool = False
    ) -> List[CryptoCurrency]:
        """Get all cryptocurrencies with optional filtering."""
        
        query = select(CryptoCurrency)
        
        filters = []
        if active_only:
            filters.append(CryptoCurrency.is_active == True)
        if tradeable_only:
            filters.append(CryptoCurrency.is_tradeable == True)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.order_by(CryptoCurrency.market_cap_rank.asc().nullslast())
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_crypto_by_symbol(
        self, 
        session: AsyncSession, 
        symbol: str
    ) -> Optional[CryptoCurrency]:
        """Get cryptocurrency by symbol."""
        
        # Check cache first
        cache_key = f"crypto_symbol_{symbol.upper()}"
        if self._is_cache_valid() and cache_key in self._cache:
            return self._cache[cache_key]
        
        result = await session.execute(
            select(CryptoCurrency).where(
                and_(
                    CryptoCurrency.symbol == symbol.upper(),
                    CryptoCurrency.is_active == True
                )
            )
        )
        crypto = result.scalar_one_or_none()
        
        # Cache the result
        if crypto:
            self._cache[cache_key] = crypto
        
        return crypto
    
    async def get_crypto_by_id(
        self, 
        session: AsyncSession, 
        crypto_id: str
    ) -> Optional[CryptoCurrency]:
        """Get cryptocurrency by ID."""
        
        cache_key = f"crypto_id_{crypto_id}"
        if self._is_cache_valid() and cache_key in self._cache:
            return self._cache[cache_key]
        
        result = await session.execute(
            select(CryptoCurrency).where(CryptoCurrency.id == crypto_id)
        )
        crypto = result.scalar_one_or_none()
        
        if crypto:
            self._cache[cache_key] = crypto
        
        return crypto
    
    async def get_cryptos_by_category(
        self, 
        session: AsyncSession, 
        category: str
    ) -> List[CryptoCurrency]:
        """Get cryptocurrencies by category."""
        
        result = await session.execute(
            select(CryptoCurrency).where(
                and_(
                    CryptoCurrency.category == category,
                    CryptoCurrency.is_active == True
                )
            ).order_by(CryptoCurrency.market_cap_rank.asc().nullslast())
        )
        return result.scalars().all()
    
    async def search_cryptos(
        self, 
        session: AsyncSession, 
        query: str, 
        limit: int = 20
    ) -> List[CryptoCurrency]:
        """Search cryptocurrencies by name or symbol."""
        
        search_term = f"%{query.lower()}%"
        
        result = await session.execute(
            select(CryptoCurrency).where(
                and_(
                    or_(
                        func.lower(CryptoCurrency.name).like(search_term),
                        func.lower(CryptoCurrency.symbol).like(search_term)
                    ),
                    CryptoCurrency.is_active == True
                )
            ).order_by(
                CryptoCurrency.market_cap_rank.asc().nullslast()
            ).limit(limit)
        )
        return result.scalars().all()
    
    async def update_crypto_prices(
        self, 
        session: AsyncSession, 
        price_updates: Dict[str, Dict[str, Any]]
    ) -> int:
        """Batch update cryptocurrency prices."""
        
        updated_count = 0
        
        for symbol, price_data in price_updates.items():
            try:
                # Find crypto by symbol
                crypto = await self.get_crypto_by_symbol(session, symbol)
                if not crypto:
                    continue
                
                # Update price data
                update_data = {}
                if "price" in price_data:
                    update_data["current_price"] = price_data["price"]
                if "market_cap" in price_data:
                    update_data["market_cap"] = price_data["market_cap"]
                if "volume_24h" in price_data:
                    update_data["volume_24h"] = price_data["volume_24h"]
                if "price_change_24h" in price_data:
                    update_data["price_change_24h"] = price_data["price_change_24h"]
                if "price_change_percentage_24h" in price_data:
                    update_data["price_change_percentage_24h"] = price_data["price_change_percentage_24h"]
                if "market_cap_rank" in price_data:
                    update_data["market_cap_rank"] = price_data["market_cap_rank"]
                
                update_data["last_updated"] = datetime.utcnow()
                
                if update_data:
                    await session.execute(
                        update(CryptoCurrency)
                        .where(CryptoCurrency.id == crypto.id)
                        .values(**update_data)
                    )
                    updated_count += 1
                    
                    # Clear cache for this crypto
                    cache_key = f"crypto_symbol_{symbol.upper()}"
                    if cache_key in self._cache:
                        del self._cache[cache_key]
                        
            except Exception as e:
                logger.error(f"Failed to update price for {symbol}: {e}")
                continue
        
        if updated_count > 0:
            await session.commit()
            logger.info(f"Updated prices for {updated_count} cryptocurrencies")
        
        return updated_count
    
    async def add_custom_crypto(
        self, 
        session: AsyncSession, 
        symbol: str, 
        name: str, 
        category: str = "Custom",
        **kwargs
    ) -> Optional[CryptoCurrency]:
        """Add a custom cryptocurrency."""
        
        try:
            # Check if symbol already exists
            existing = await self.get_crypto_by_symbol(session, symbol)
            if existing:
                logger.warning(f"Cryptocurrency with symbol {symbol} already exists")
                return existing
            
            crypto = CryptoCurrency(
                symbol=symbol.upper(),
                name=name,
                category=category,
                coingecko_id=kwargs.get("coingecko_id"),
                description=kwargs.get("description", ""),
                is_tradeable=kwargs.get("is_tradeable", True),
                is_active=kwargs.get("is_active", True),
                min_trade_amount=kwargs.get("min_trade_amount", 0.00001),
                max_trade_amount=kwargs.get("max_trade_amount", 1000000.0),
                trading_fee_percentage=kwargs.get("trading_fee_percentage", 0.25)
            )
            
            session.add(crypto)
            await session.commit()
            await session.refresh(crypto)
            
            logger.info(f"Added custom cryptocurrency: {symbol} - {name}")
            
            # Clear cache
            self._cache.clear()
            self._last_cache_update = None
            
            return crypto
            
        except Exception as e:
            logger.error(f"Failed to add custom crypto {symbol}: {e}")
            await session.rollback()
            return None
    
    async def toggle_crypto_trading(
        self, 
        session: AsyncSession, 
        symbol: str, 
        is_tradeable: bool
    ) -> bool:
        """Enable or disable trading for a cryptocurrency."""
        
        try:
            crypto = await self.get_crypto_by_symbol(session, symbol)
            if not crypto:
                return False
            
            await session.execute(
                update(CryptoCurrency)
                .where(CryptoCurrency.id == crypto.id)
                .values(
                    is_tradeable=is_tradeable,
                    last_updated=datetime.utcnow()
                )
            )
            
            await session.commit()
            
            # Clear cache
            cache_key = f"crypto_symbol_{symbol.upper()}"
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            logger.info(f"{'Enabled' if is_tradeable else 'Disabled'} trading for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to toggle trading for {symbol}: {e}")
            await session.rollback()
            return False
    
    async def get_market_overview(self, session: AsyncSession) -> Dict[str, Any]:
        """Get market overview statistics."""
        
        # Get top cryptocurrencies by market cap
        top_cryptos_result = await session.execute(
            select(CryptoCurrency)
            .where(
                and_(
                    CryptoCurrency.is_active == True,
                    CryptoCurrency.market_cap > 0
                )
            )
            .order_by(CryptoCurrency.market_cap.desc())
            .limit(10)
        )
        top_cryptos = top_cryptos_result.scalars().all()
        
        # Calculate market statistics
        market_stats_result = await session.execute(
            select(
                func.count(CryptoCurrency.id).label("total_cryptos"),
                func.sum(CryptoCurrency.market_cap).label("total_market_cap"),
                func.sum(CryptoCurrency.volume_24h).label("total_volume_24h"),
                func.avg(CryptoCurrency.price_change_percentage_24h).label("avg_change_24h")
            ).where(
                and_(
                    CryptoCurrency.is_active == True,
                    CryptoCurrency.market_cap > 0
                )
            )
        )
        market_stats = market_stats_result.first()
        
        # Get category breakdown
        category_result = await session.execute(
            select(
                CryptoCurrency.category,
                func.count(CryptoCurrency.id).label("count"),
                func.sum(CryptoCurrency.market_cap).label("market_cap")
            ).where(
                and_(
                    CryptoCurrency.is_active == True,
                    CryptoCurrency.category.isnot(None)
                )
            ).group_by(CryptoCurrency.category)
            .order_by(func.sum(CryptoCurrency.market_cap).desc())
        )
        categories = category_result.all()
        
        return {
            "total_cryptocurrencies": market_stats.total_cryptos or 0,
            "total_market_cap": market_stats.total_market_cap or 0.0,
            "total_volume_24h": market_stats.total_volume_24h or 0.0,
            "average_change_24h": market_stats.avg_change_24h or 0.0,
            "top_cryptocurrencies": [
                {
                    "symbol": crypto.symbol,
                    "name": crypto.name,
                    "price": crypto.current_price,
                    "market_cap": crypto.market_cap,
                    "change_24h": crypto.price_change_percentage_24h,
                    "rank": crypto.market_cap_rank
                }
                for crypto in top_cryptos
            ],
            "categories": [
                {
                    "category": cat.category,
                    "count": cat.count,
                    "market_cap": cat.market_cap or 0.0
                }
                for cat in categories
            ],
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._last_cache_update is None:
            return False
        
        return (datetime.utcnow() - self._last_cache_update).total_seconds() < self.cache_duration
    
    def clear_cache(self):
        """Clear the internal cache."""
        self._cache.clear()
        self._last_cache_update = None
        logger.info("Crypto registry cache cleared")


# Global instance
crypto_registry = CryptoRegistry()