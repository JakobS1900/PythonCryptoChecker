"""
Market data service for fetching live cryptocurrency prices and information.
Integrates CoinGecko and CoinCap APIs like EmusPythonCryptoChecker v1.
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.dialects.sqlite import insert

from database.unified_models import CryptoAsset
from logger import logger


class MarketDataService:
    """Service for fetching and managing cryptocurrency market data."""

    def __init__(self):
        self.supported_currencies = [
            'USD', 'EUR', 'JPY', 'GBP', 'AUD', 'CAD', 'CHF', 'CNY',
            'INR', 'BRL', 'RUB', 'KRW', 'SGD', 'MXN', 'NZD', 'HKD',
            'NOK', 'SEK', 'ZAR', 'TRY'
        ]
        self.session_timeout = aiohttp.ClientTimeout(total=30)  # Increased timeout
        self.cache_duration = 300  # 5 minutes cache

        # Major cryptocurrencies we want to ensure are included
        self.priority_coins = [
            'bitcoin', 'ethereum', 'binancecoin', 'cardano', 'solana',
            'monero', 'avalanche-2', 'polkadot', 'chainlink', 'polygon',
            'litecoin', 'bitcoin-cash', 'stellar', 'dogecoin', 'shiba-inu',
            'uniswap', 'wrapped-bitcoin', 'cosmos', 'ethereum-classic',
            'filecoin', 'tron', 'cronos', 'near', 'apecoin', 'sandbox',
            'decentraland', 'axie-infinity', 'fantom', 'algorand', 'vechain',
            'hedera-hashgraph', 'internet-computer', 'flow', 'tezos',
            'elrond-erd-2', 'theta-token', 'chiliz', 'enjincoin', 'mana'
        ]

    async def fetch_coins_list(self, vs_currency: str = "USD", limit: int = 100) -> Tuple[List[Dict], str]:
        """
        Fetch list of cryptocurrencies with market data.
        Returns (coins_data, status).
        """
        vs_currency = vs_currency.lower()

        # Try CoinGecko first
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                url = "https://api.coingecko.com/api/v3/coins/markets"
                params = {
                    'vs_currency': vs_currency,
                    'order': 'market_cap_desc',
                    'per_page': str(limit),
                    'page': '1',
                    'sparkline': 'false',
                    'price_change_percentage': '24h'
                }

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        formatted_data = []

                        for coin in data:
                            # Safe conversion to float, handling None values
                            try:
                                current_price = coin.get("current_price")
                                price_change_24h = coin.get("price_change_24h")
                                price_change_percentage_24h = coin.get("price_change_percentage_24h")
                                market_cap = coin.get("market_cap")
                                total_volume = coin.get("total_volume")

                                # Skip coins with missing essential data
                                if current_price is None or coin.get("id") is None:
                                    logger.warning(f"Skipping coin with missing data: {coin.get('symbol', 'UNKNOWN')}")
                                    continue

                                formatted_data.append({
                                    "id": coin["id"],
                                    "symbol": coin["symbol"].upper() if coin.get("symbol") else "UNKNOWN",
                                    "name": coin.get("name", "Unknown"),
                                    "price": float(current_price),
                                    "change_24h": float(price_change_24h) if price_change_24h is not None else 0.0,
                                    "change_24h_percent": float(price_change_percentage_24h) if price_change_percentage_24h is not None else 0.0,
                                    "market_cap": float(market_cap) if market_cap is not None else 0.0,
                                    "volume_24h": float(total_volume) if total_volume is not None else 0.0,
                                    "image_url": coin.get("image"),
                                    "last_updated": coin.get("last_updated")
                                })
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Error processing coin {coin.get('symbol', 'UNKNOWN')}: {e}")
                                continue

                        logger.info(f"Fetched {len(formatted_data)} coins from CoinGecko")
                        return formatted_data, "coingecko_success"

        except Exception as e:
            logger.warning(f"CoinGecko API failed: {e}")

        # Fallback to CoinCap API
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                url = "https://api.coincap.io/v2/assets"
                params = {'limit': limit}

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        assets = data.get('data', [])
                        formatted_data = []

                        # Get conversion rate if not USD
                        conversion_rate = 1.0
                        if vs_currency.upper() != 'USD':
                            conversion_rate = await self.get_fiat_conversion_rate(vs_currency.upper())

                        for asset in assets:
                            try:
                                price_usd_raw = asset.get("priceUsd")
                                market_cap_usd_raw = asset.get("marketCapUsd")
                                volume_usd_raw = asset.get("volumeUsd24Hr")

                                # Skip assets with missing essential data
                                if price_usd_raw is None or asset.get("id") is None:
                                    continue

                                price_usd = float(price_usd_raw)
                                market_cap_usd = float(market_cap_usd_raw) if market_cap_usd_raw is not None else 0.0
                                volume_usd = float(volume_usd_raw) if volume_usd_raw is not None else 0.0
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Error processing CoinCap asset {asset.get('symbol', 'UNKNOWN')}: {e}")
                                continue

                            formatted_data.append({
                                "id": asset["id"],
                                "symbol": asset["symbol"].upper(),
                                "name": asset["name"],
                                "price": price_usd * conversion_rate,
                                "change_24h": 0,  # CoinCap doesn't provide absolute change
                                "change_24h_percent": float(asset.get("changePercent24Hr", 0)),
                                "market_cap": market_cap_usd * conversion_rate,
                                "volume_24h": volume_usd * conversion_rate,
                                "image_url": None,
                                "last_updated": None
                            })

                        logger.info(f"Fetched {len(formatted_data)} coins from CoinCap")
                        return formatted_data, "coincap_success"

        except Exception as e:
            logger.warning(f"CoinCap API failed: {e}")

        return [], "api_failure"

    async def get_fiat_conversion_rate(self, fiat_currency: str) -> float:
        """Get USD to fiat currency conversion rate."""
        if fiat_currency.upper() == 'USD':
            return 1.0

        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                url = f"https://api.exchangerate-api.com/v4/latest/USD"

                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        rates = data.get('rates', {})
                        return float(rates.get(fiat_currency.upper(), 1.0))
        except Exception as e:
            logger.warning(f"Failed to get conversion rate for {fiat_currency}: {e}")

        return 1.0

    async def fetch_trending_coins(self) -> List[str]:
        """Fetch trending cryptocurrency symbols."""
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                url = "https://api.coingecko.com/api/v3/search/trending"

                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        coins = data.get("coins", [])
                        trending_symbols = [coin["item"]["symbol"].upper() for coin in coins]
                        logger.info(f"Fetched {len(trending_symbols)} trending coins")
                        return trending_symbols
        except Exception as e:
            logger.warning(f"Failed to fetch trending coins: {e}")

        return []

    async def fetch_historical_data(
        self,
        coin_id: str,
        vs_currency: str = "USD",
        days: str = "7"
    ) -> List[Dict]:
        """
        Fetch historical price data for a cryptocurrency.
        Returns list of {'timestamp': datetime, 'price': float} dicts.
        """
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
                params = {
                    "vs_currency": vs_currency.lower(),
                    "days": days
                }

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        prices = data.get("prices", [])

                        historical_data = []
                        for timestamp_ms, price in prices:
                            historical_data.append({
                                "timestamp": datetime.fromtimestamp(timestamp_ms / 1000),
                                "price": float(price)
                            })

                        logger.info(f"Fetched {len(historical_data)} historical data points for {coin_id}")
                        return historical_data
        except Exception as e:
            logger.warning(f"Failed to fetch historical data for {coin_id}: {e}")

        return []

    async def update_crypto_assets(self, session: AsyncSession, coins_data: List[Dict]) -> int:
        """
        Update or insert crypto assets in database.
        Returns number of assets updated/inserted.
        """
        updated_count = 0

        try:
            for coin_data in coins_data:
                # Use SQLite UPSERT (INSERT ... ON CONFLICT)
                stmt = insert(CryptoAsset).values(
                    id=coin_data["id"],
                    symbol=coin_data["symbol"],
                    name=coin_data["name"],
                    current_price_usd=coin_data["price"],
                    market_cap=coin_data["market_cap"],
                    price_change_24h=coin_data["change_24h"],
                    price_change_percentage_24h=coin_data["change_24h_percent"],
                    image_url=coin_data.get("image_url"),
                    last_price_update=datetime.utcnow(),
                    is_active=True
                )

                # ON CONFLICT UPDATE
                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=['id'],
                    set_=dict(
                        symbol=stmt.excluded.symbol,
                        name=stmt.excluded.name,
                        current_price_usd=stmt.excluded.current_price_usd,
                        market_cap=stmt.excluded.market_cap,
                        price_change_24h=stmt.excluded.price_change_24h,
                        price_change_percentage_24h=stmt.excluded.price_change_percentage_24h,
                        image_url=stmt.excluded.image_url,
                        last_price_update=stmt.excluded.last_price_update,
                        is_active=stmt.excluded.is_active
                    )
                )

                await session.execute(upsert_stmt)
                updated_count += 1

            await session.commit()
            logger.info(f"Updated {updated_count} crypto assets in database")

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to update crypto assets: {e}")
            return 0

        return updated_count

    async def get_cached_assets(
        self,
        session: AsyncSession,
        limit: int = 500
    ) -> List[Dict]:
        """Get cached crypto assets from database."""
        try:
            stmt = select(CryptoAsset).where(
                CryptoAsset.is_active == True
            ).order_by(
                CryptoAsset.market_cap.desc()
            ).limit(limit)

            result = await session.execute(stmt)
            assets = result.scalars().all()

            cached_data = []
            for asset in assets:
                cached_data.append({
                    "id": asset.id,
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "price": asset.current_price_usd,
                    "change_24h": asset.price_change_24h,
                    "change_24h_percent": asset.price_change_percentage_24h,
                    "market_cap": asset.market_cap,
                    "image_url": asset.image_url,
                    "last_updated": asset.last_price_update.isoformat() if asset.last_price_update else None
                })

            logger.info(f"Retrieved {len(cached_data)} cached assets from database")
            return cached_data

        except Exception as e:
            logger.error(f"Failed to get cached assets: {e}")
            return []

    async def should_refresh_data(self, session: AsyncSession) -> bool:
        """Check if market data should be refreshed."""
        try:
            stmt = select(func.max(CryptoAsset.last_price_update))
            result = await session.execute(stmt)
            last_update = result.scalar()

            if not last_update:
                return True

            time_since_update = datetime.utcnow() - last_update
            return time_since_update.total_seconds() > self.cache_duration

        except Exception as e:
            logger.error(f"Error checking refresh status: {e}")
            return True

    async def fetch_priority_coins(self, vs_currency: str = "USD") -> Tuple[List[Dict], str]:
        """
        Fetch specific high-priority cryptocurrencies to ensure comprehensive coverage.
        Returns (coins_data, status).
        """
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                # Construct coin IDs string for CoinGecko
                coin_ids = ','.join(self.priority_coins)

                url = "https://api.coingecko.com/api/v3/coins/markets"
                params = {
                    'ids': coin_ids,
                    'vs_currency': vs_currency.lower(),
                    'order': 'market_cap_desc',
                    'per_page': '250',
                    'page': '1',
                    'sparkline': 'false',
                    'price_change_percentage': '24h'
                }

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        formatted_data = []

                        for coin in data:
                            try:
                                current_price = coin.get("current_price")
                                if current_price is None or coin.get("id") is None:
                                    continue

                                price_change_24h = coin.get("price_change_24h")
                                price_change_percentage_24h = coin.get("price_change_percentage_24h")
                                market_cap = coin.get("market_cap")
                                total_volume = coin.get("total_volume")

                                formatted_data.append({
                                    "id": coin["id"],
                                    "symbol": coin["symbol"].upper() if coin.get("symbol") else "UNKNOWN",
                                    "name": coin.get("name", "Unknown"),
                                    "price": float(current_price),
                                    "change_24h": float(price_change_24h) if price_change_24h is not None else 0.0,
                                    "change_24h_percent": float(price_change_percentage_24h) if price_change_percentage_24h is not None else 0.0,
                                    "market_cap": float(market_cap) if market_cap is not None else 0.0,
                                    "volume_24h": float(total_volume) if total_volume is not None else 0.0,
                                    "image_url": coin.get("image"),
                                    "last_updated": coin.get("last_updated")
                                })
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Error processing priority coin {coin.get('symbol', 'UNKNOWN')}: {e}")
                                continue

                        logger.info(f"Fetched {len(formatted_data)} priority coins from CoinGecko")
                        return formatted_data, "priority_coingecko_success"
                    else:
                        logger.warning(f"CoinGecko priority coins API returned status {response.status}")

        except Exception as e:
            logger.warning(f"Priority coins CoinGecko API failed: {e}")

        return [], "priority_api_failure"

    async def get_market_overview(
        self,
        session: AsyncSession,
        vs_currency: str = "USD",
        force_refresh: bool = False
    ) -> Tuple[List[Dict], str]:
        """
        Get comprehensive market overview with priority coins and general market data.
        Returns (coins_data, source_info).
        """
        # Check if we should refresh data
        should_refresh = force_refresh or await self.should_refresh_data(session)

        if should_refresh:
            # Try to get comprehensive data by combining multiple approaches
            all_coins_data = []

            # First, fetch general market data (top 100 by market cap)
            general_coins, general_status = await self.fetch_coins_list(vs_currency, limit=100)
            if general_coins:
                all_coins_data.extend(general_coins)
                logger.info(f"Added {len(general_coins)} general market coins")

            # Then, ensure we have our priority coins
            priority_coins, priority_status = await self.fetch_priority_coins(vs_currency)
            if priority_coins:
                # Merge priority coins, avoiding duplicates
                existing_ids = {coin["id"] for coin in all_coins_data}
                new_priority_coins = [coin for coin in priority_coins if coin["id"] not in existing_ids]
                all_coins_data.extend(new_priority_coins)
                logger.info(f"Added {len(new_priority_coins)} new priority coins")

            if all_coins_data:
                # Sort by market cap descending
                all_coins_data.sort(key=lambda x: x.get("market_cap", 0), reverse=True)

                # Update database cache
                await self.update_crypto_assets(session, all_coins_data)

                combined_status = f"combined_data_{general_status}_{priority_status}"
                logger.info(f"Successfully fetched {len(all_coins_data)} total cryptocurrencies")
                return all_coins_data, combined_status

        # Return cached data if refresh not needed or APIs failed
        cached_data = await self.get_cached_assets(session, limit=500)  # Increased cache limit
        if cached_data:
            logger.info(f"Returning {len(cached_data)} cached cryptocurrencies")
            return cached_data, "cached_data"

        # Final fallback: try to fetch fresh data even if not time to refresh
        logger.info("Attempting final fallback data fetch")

        # Try general coins first
        coins_data, api_status = await self.fetch_coins_list(vs_currency, limit=100)
        if coins_data:
            await self.update_crypto_assets(session, coins_data)
            return coins_data, f"fallback_{api_status}"

        # Try priority coins as final attempt
        priority_coins, priority_status = await self.fetch_priority_coins(vs_currency)
        if priority_coins:
            await self.update_crypto_assets(session, priority_coins)
            return priority_coins, f"fallback_{priority_status}"

        # No data available from any source
        logger.error("All API sources and cache failed to provide cryptocurrency data")
        return [], "complete_failure"


# Global instance
market_data_service = MarketDataService()