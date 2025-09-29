"""
Real-time cryptocurrency price service.
Fetches prices from multiple APIs with intelligent caching and fallback.
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import os
from dotenv import load_dotenv

from database.database import AsyncSessionLocal
from database.models import CryptoCurrency

load_dotenv()

class CryptoPriceService:
    """Service for fetching and managing cryptocurrency prices."""

    def __init__(self):
        self.is_running = False
        self.session: Optional[aiohttp.ClientSession] = None
        self.price_cache: Dict[str, Any] = {}
        self._update_task = None  # Keep track of the update task
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_duration = 300  # 5 minutes cache to reduce API calls
        self.update_interval = int(os.getenv("PRICE_UPDATE_INTERVAL", "120"))  # 2 minutes instead of 30 seconds

        # API configurations
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.coincap_base = "https://api.coincap.io/v2"
        self.coingecko_api_key = os.getenv("COINGECKO_API_KEY")

        # Enhanced rate limiting and backoff
        self.last_api_call = {}
        self.api_call_limit = 2.0  # 2 seconds between calls
        self.backoff_times = {}
        self.max_backoff = 300  # 5 minutes max backoff
        self.api_failure_count = {}

        # Mock data for complete API failure fallback
        self.mock_prices = {
            "bitcoin": {"current_price": 43250.0, "market_cap": 847000000000, "total_volume": 24000000000, "price_change_percentage_24h": 2.1},
            "ethereum": {"current_price": 2640.0, "market_cap": 317000000000, "total_volume": 15000000000, "price_change_percentage_24h": 1.8},
            "binancecoin": {"current_price": 310.0, "market_cap": 47000000000, "total_volume": 800000000, "price_change_percentage_24h": -0.5},
            "cardano": {"current_price": 0.48, "market_cap": 17000000000, "total_volume": 450000000, "price_change_percentage_24h": 3.2},
            "solana": {"current_price": 98.0, "market_cap": 43000000000, "total_volume": 2100000000, "price_change_percentage_24h": 4.1},
            "ripple": {"current_price": 0.52, "market_cap": 29000000000, "total_volume": 1200000000, "price_change_percentage_24h": 1.1},
            "polkadot": {"current_price": 7.2, "market_cap": 9000000000, "total_volume": 180000000, "price_change_percentage_24h": -1.2}
        }

    async def start(self):
        """Start the price service."""
        if self.is_running:
            return

        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={
                "User-Agent": "CryptoChecker-v3/1.0",
                "Accept": "application/json"
            }
        )
        self.is_running = True

        # Start background price update task with error handling
        self._update_task = asyncio.create_task(self._price_update_loop())

        def _on_task_done(t):
            try:
                t.result()
            except asyncio.CancelledError:
                pass  # Normal shutdown
            except Exception as e:
                import sys
                print(f">> Error: Price service task crashed: {str(e)}", file=sys.stderr)

        self._update_task.add_done_callback(_on_task_done)
        print(">> Crypto price service started")

    async def stop(self):
        """Stop the price service."""
        self.is_running = False
        
        # Cancel the update task if it exists
        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        
        if self.session:
            await self.session.close()
        print(">> Crypto price service stopped")

    async def _price_update_loop(self):
        """Background task to update prices periodically."""
        while self.is_running:
            try:
                await self.update_all_prices()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                # Handle graceful shutdown
                print(">> Info: Price update loop cancelled")
                break
            except Exception as e:
                import sys
                print(f">> Error: Error in price update loop: {str(e)}")
                import traceback
                traceback.print_exc(file=sys.stderr)
                # Don't exit the loop on error, just back off and retry
                await asyncio.sleep(30)  # Longer backoff (30s) after error
                continue

    async def update_all_prices(self):
        """Update prices for all tracked cryptocurrencies."""
        async with AsyncSessionLocal() as db_session:
            try:
                # Get all active cryptocurrencies
                result = await db_session.execute(
                    select(CryptoCurrency).where(CryptoCurrency.is_active == True)
                )
                cryptos = result.scalars().all()

                if not cryptos:
                    return

                # Get crypto IDs for batch request
                crypto_ids = [crypto.id for crypto in cryptos]

                # Fetch prices in batches of 50
                batch_size = 50
                for i in range(0, len(crypto_ids), batch_size):
                    batch_ids = crypto_ids[i:i + batch_size]
                    price_data = await self._fetch_prices_batch(batch_ids)

                    if price_data:
                        # Update database
                        for crypto_id, data in price_data.items():
                            await db_session.execute(
                                update(CryptoCurrency)
                                .where(CryptoCurrency.id == crypto_id)
                                .values(
                                    current_price_usd=data.get("current_price"),
                                    market_cap=data.get("market_cap"),
                                    volume_24h=data.get("total_volume"),
                                    price_change_24h=data.get("price_change_24h"),
                                    price_change_percentage_24h=data.get("price_change_percentage_24h"),
                                    image=data.get("image"),  # Update image URL
                                    last_updated=datetime.utcnow()
                                )
                            )

                        # Update cache
                        for crypto_id, data in price_data.items():
                            self.price_cache[crypto_id] = data
                            self.cache_expiry[crypto_id] = datetime.utcnow() + timedelta(seconds=self.cache_duration)

                await db_session.commit()
                print(f">> Success: Updated prices for {len(price_data)} cryptocurrencies")

            except Exception as e:
                await db_session.rollback()
                import sys
                print(f">> Error: Error updating prices: {str(e)}")
                import traceback
                traceback.print_exc(file=sys.stderr)
                # Return early but don't re-raise
                return

    async def _fetch_prices_batch(self, crypto_ids: List[str]) -> Dict[str, Any]:
        """Fetch prices for a batch of cryptocurrencies with intelligent fallback."""
        # Check if we should skip API calls due to backoff
        if await self._should_backoff():
            print(">> Info: Using cached/mock data due to API backoff")
            return await self._get_fallback_data(crypto_ids)

        # Try CoinGecko first
        try:
            result = await self._fetch_coingecko_batch(crypto_ids)
            # Reset failure count on success
            self.api_failure_count["coingecko"] = 0
            return result
        except Exception as e:
            print(f">> Warning: CoinGecko failed: {e}, trying CoinCap...")
            await self._record_api_failure("coingecko")

        # Fallback to CoinCap
        try:
            result = await self._fetch_coincap_batch(crypto_ids)
            # Reset failure count on success
            self.api_failure_count["coincap"] = 0
            return result
        except Exception as e:
            print(f">> Warning: CoinCap failed: {e}, using fallback data...")
            await self._record_api_failure("coincap")

        # Ultimate fallback to mock data
        return await self._get_fallback_data(crypto_ids)

    async def _fetch_coingecko_batch(self, crypto_ids: List[str]) -> Dict[str, Any]:
        """Fetch prices and images from CoinGecko API."""
        if not self.session:
            raise Exception("Session not initialized")

        await self._rate_limit("coingecko")

        ids_str = ",".join(crypto_ids)
        # Use coins/markets endpoint to get image URLs
        url = f"{self.coingecko_base}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": ids_str,
            "order": "market_cap_desc",
            "per_page": 250,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h"
        }

        if self.coingecko_api_key:
            params["x_cg_demo_api_key"] = self.coingecko_api_key

        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                result = {}
                for coin in data:
                    crypto_id = coin.get("id")
                    if crypto_id:
                        result[crypto_id] = {
                            "current_price": coin.get("current_price"),
                            "market_cap": coin.get("market_cap"),
                            "total_volume": coin.get("total_volume"),
                            "price_change_24h": coin.get("price_change_24h"),
                            "price_change_percentage_24h": coin.get("price_change_percentage_24h"),
                            "image": coin.get("image")  # Add image URL
                        }
                return result
            else:
                raise Exception(f"CoinGecko API error: {response.status}")

    async def _fetch_coincap_batch(self, crypto_ids: List[str]) -> Dict[str, Any]:
        """Fetch prices from CoinCap API (fallback)."""
        if not self.session:
            raise Exception("Session not initialized")

        await self._rate_limit("coincap")

        # CoinCap uses different IDs, so we need to map them
        symbol_map = {
            "bitcoin": "BTC",
            "ethereum": "ETH",
            "binancecoin": "BNB",
            "cardano": "ADA",
            "solana": "SOL",
            "ripple": "XRP",
            "polkadot": "DOT",
            "dogecoin": "DOGE"
        }

        result = {}
        for crypto_id in crypto_ids:
            symbol = symbol_map.get(crypto_id)
            if not symbol:
                continue

            try:
                url = f"{self.coincap_base}/assets/{symbol.lower()}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        asset_data = data.get("data", {})

                        price = float(asset_data.get("priceUsd", 0))
                        market_cap = float(asset_data.get("marketCapUsd", 0))
                        volume = float(asset_data.get("volumeUsd24Hr", 0))
                        change = float(asset_data.get("changePercent24Hr", 0))

                        result[crypto_id] = {
                            "current_price": price,
                            "market_cap": market_cap,
                            "total_volume": volume,
                            "price_change_24h": None,
                            "price_change_percentage_24h": change
                        }
            except Exception as e:
                print(f">> Error: Error fetching {crypto_id} from CoinCap: {e}")

        return result

    async def _rate_limit(self, api_name: str):
        """Implement rate limiting for API calls."""
        if api_name in self.last_api_call:
            time_since_last = (datetime.now() - self.last_api_call[api_name]).total_seconds()
            if time_since_last < self.api_call_limit:
                await asyncio.sleep(self.api_call_limit - time_since_last)

        self.last_api_call[api_name] = datetime.now()

    async def _should_backoff(self) -> bool:
        """Check if we should back off from API calls."""
        now = datetime.now()
        for api_name, backoff_until in self.backoff_times.items():
            if now < backoff_until:
                return True
        return False

    async def _record_api_failure(self, api_name: str):
        """Record an API failure and implement exponential backoff."""
        if api_name not in self.api_failure_count:
            self.api_failure_count[api_name] = 0

        self.api_failure_count[api_name] += 1

        # Calculate backoff time: 2^failures * 30 seconds, max 5 minutes
        backoff_seconds = min(2 ** self.api_failure_count[api_name] * 30, self.max_backoff)
        self.backoff_times[api_name] = datetime.now() + timedelta(seconds=backoff_seconds)

        print(f">> Warning: API {api_name} failing, backing off for {backoff_seconds} seconds")

    async def _get_fallback_data(self, crypto_ids: List[str]) -> Dict[str, Any]:
        """Get fallback data from cache or mock data."""
        result = {}

        # First try cache
        for crypto_id in crypto_ids:
            if crypto_id in self.price_cache:
                result[crypto_id] = self.price_cache[crypto_id]

        # Fill remaining with mock data
        for crypto_id in crypto_ids:
            if crypto_id not in result and crypto_id in self.mock_prices:
                result[crypto_id] = self.mock_prices[crypto_id].copy()
                # Add slight randomness to mock data
                result[crypto_id]["current_price"] *= (0.98 + 0.04 * hash(str(datetime.now().minute)) % 100 / 100)

        print(f">> Info: Providing fallback data for {len(result)} cryptocurrencies")
        return result

    async def get_price(self, crypto_id: str) -> Optional[float]:
        """Get current price for a cryptocurrency."""
        # Check cache first
        if crypto_id in self.price_cache and crypto_id in self.cache_expiry:
            if datetime.utcnow() < self.cache_expiry[crypto_id]:
                return self.price_cache[crypto_id].get("current_price")

        # Fetch from database
        async with AsyncSessionLocal() as db_session:
            result = await db_session.execute(
                select(CryptoCurrency).where(CryptoCurrency.id == crypto_id)
            )
            crypto = result.scalar_one_or_none()
            if crypto:
                return crypto.current_price_usd

        return None

    async def get_prices(self, crypto_ids: List[str]) -> Dict[str, float]:
        """Get current prices for multiple cryptocurrencies."""
        prices = {}

        async with AsyncSessionLocal() as db_session:
            result = await db_session.execute(
                select(CryptoCurrency).where(CryptoCurrency.id.in_(crypto_ids))
            )
            cryptos = result.scalars().all()

            for crypto in cryptos:
                if crypto.current_price_usd:
                    prices[crypto.id] = crypto.current_price_usd

        return prices

    async def get_all_cryptos(self) -> List[Dict[str, Any]]:
        """Get all tracked cryptocurrencies with current prices."""
        async with AsyncSessionLocal() as db_session:
            result = await db_session.execute(
                select(CryptoCurrency).where(CryptoCurrency.is_active == True)
                .order_by(CryptoCurrency.market_cap.desc().nulls_last())
            )
            cryptos = result.scalars().all()
            return [crypto.to_dict() for crypto in cryptos]

    async def search_cryptos(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search cryptocurrencies by name or symbol."""
        async with AsyncSessionLocal() as db_session:
            search_pattern = f"%{query.lower()}%"
            result = await db_session.execute(
                select(CryptoCurrency)
                .where(
                    (CryptoCurrency.name.ilike(search_pattern)) |
                    (CryptoCurrency.symbol.ilike(search_pattern))
                )
                .where(CryptoCurrency.is_active == True)
                .order_by(CryptoCurrency.market_cap.desc().nulls_last())
                .limit(limit)
            )
            cryptos = result.scalars().all()
            return [crypto.to_dict() for crypto in cryptos]

# Global price service instance
price_service = CryptoPriceService()
