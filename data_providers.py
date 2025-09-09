"""
Data providers for Crypto Analytics Platform.
Handles API interactions and data fetching from various cryptocurrency data sources.
"""
import requests
import time
from typing import List, Optional, Dict, Any
from datetime import datetime

from models import CoinData, PricePoint, ExchangeFeeData, NetworkFeeData
from config import EMOJI_MAP, EXCHANGE_PAIRS, FEE_API_ENDPOINTS, HIST_CACHE_TTL


class CoinGeckoProvider:
    """Data provider for CoinGecko API."""
    
    @staticmethod
    def get_top_coins(user_currency: str = 'usd', limit: int = 100) -> List[CoinData]:
        """Fetch top cryptocurrencies from CoinGecko API."""
        try:
            resp = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    'vs_currency': user_currency,
                    'order': 'market_cap_desc',
                    'per_page': limit,
                    'page': 1,
                    'sparkline': 'false'
                },
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            
            coins = []
            for coin in data:
                symbol = coin['symbol'].upper()
                name = coin['name']
                price = coin['current_price']
                emoji = EMOJI_MAP.get(coin['id'], EMOJI_MAP.get(coin['symbol'], symbol))
                price_change_24h = coin.get('price_change_percentage_24h', 0)
                
                coins.append(CoinData(
                    id=coin['id'],
                    name=name,
                    symbol=symbol,
                    price=price,
                    emoji=emoji,
                    price_change_24h=price_change_24h,
                    market_cap=coin.get('market_cap'),
                    volume_24h=coin.get('total_volume')
                ))
            
            return coins
            
        except Exception:
            return []
    
    @staticmethod
    def get_historical_data(coin_id: str, days: str, user_currency: str = 'usd') -> List[PricePoint]:
        """Fetch historical price data from CoinGecko."""
        try:
            if days == "max":
                params = {'vs_currency': user_currency, 'days': 'max'}
            else:
                params = {'vs_currency': user_currency, 'days': days}
            
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            
            # Try with one retry on failure
            for attempt in range(2):
                try:
                    resp = requests.get(url, params=params, timeout=10)
                    resp.raise_for_status()
                    data = resp.json()
                    
                    prices = []
                    for point in data.get('prices', []):
                        prices.append(PricePoint(timestamp=point[0], price=point[1]))
                    
                    return prices
                except Exception:
                    if attempt == 0:
                        time.sleep(0.5)
                        continue
                    else:
                        break
            
            return []
            
        except Exception:
            return []


class CoinCapProvider:
    """Data provider for CoinCap API."""
    
    @staticmethod
    def get_top_coins(limit: int = 100) -> List[CoinData]:
        """Fetch top cryptocurrencies from CoinCap API."""
        try:
            url = "https://api.coincap.io/v2/assets"
            resp = requests.get(url, params={'limit': limit}, timeout=10)
            resp.raise_for_status()
            data = resp.json().get('data', [])
            
            coins = []
            for entry in data:
                coin_id = entry.get('id', '')
                symbol = entry.get('symbol', '').upper()
                name = entry.get('name', symbol)
                price = float(entry.get('priceUsd', 0) or 0)
                change = float(entry.get('changePercent24Hr', 0) or 0)
                emoji = EMOJI_MAP.get(coin_id, EMOJI_MAP.get(symbol.lower(), symbol))
                
                coins.append(CoinData(
                    id=coin_id,
                    name=name,
                    symbol=symbol,
                    price=price,
                    emoji=emoji,
                    price_change_24h=change,
                    market_cap=float(entry.get('marketCapUsd', 0) or 0),
                    volume_24h=float(entry.get('volumeUsd24Hr', 0) or 0)
                ))
            
            return coins
            
        except Exception:
            return []
    
    @staticmethod
    def get_historical_data(coin_id: str, days: str) -> List[PricePoint]:
        """Fetch historical price data from CoinCap."""
        if days == "max":
            return []  # CoinCap does not support "max" directly
        
        try:
            now_ms = int(time.time() * 1000)
            ms_per_day = 86400000
            start_ms = now_ms - int(float(days) * ms_per_day)
            
            # Determine interval based on timeframe
            days_float = float(days)
            if days_float < 1:
                interval = 'm1'
            elif days_float == 1:
                interval = 'h1'
            else:
                interval = 'd1'
            
            url = f"https://api.coincap.io/v2/assets/{coin_id}/history"
            resp = requests.get(
                url,
                params={'interval': interval, 'start': start_ms, 'end': now_ms},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json().get('data', [])
            
            prices = []
            for point in data:
                price = float(point.get('priceUsd', 0) or 0)
                time_ms = int(point.get('time', 0))
                prices.append(PricePoint(timestamp=time_ms, price=price))
            
            return prices
            
        except Exception:
            return []


class FeeProvider:
    """Provider for network and exchange fee data."""
    
    @staticmethod
    def get_network_fees(coin_id: str) -> Optional[NetworkFeeData]:
        """Get current network fees for transactions."""
        try:
            if coin_id == 'btc':
                response = requests.get(FEE_API_ENDPOINTS['btc'], timeout=5)
                response.raise_for_status()
                data = response.json()
                return NetworkFeeData(
                    coin_id=coin_id,
                    fast=data['fastestFee'],
                    medium=data['halfHourFee'],
                    slow=data['hourFee']
                )
            
            elif coin_id == 'eth':
                response = requests.get(FEE_API_ENDPOINTS['eth'], timeout=5)
                response.raise_for_status()
                data = response.json()
                return NetworkFeeData(
                    coin_id=coin_id,
                    fast=data['fast'] / 10,
                    medium=data['average'] / 10,
                    slow=data['safeLow'] / 10
                )
            
            elif coin_id == 'xmr':
                response = requests.get(FEE_API_ENDPOINTS['xmr'], timeout=5)
                response.raise_for_status()
                data = response.json()
                return NetworkFeeData(
                    coin_id=coin_id,
                    fast=data['fee_per_byte'] * 2500 / 1e12,
                    medium=data['fee_per_byte'] * 2000 / 1e12,
                    slow=data['fee_per_byte'] * 1500 / 1e12
                )
            
            return None
            
        except Exception:
            return None
    
    @staticmethod
    def get_exchange_fees(pair: str) -> Optional[ExchangeFeeData]:
        """Get exchange fees for trading pairs."""
        try:
            if pair in EXCHANGE_PAIRS:
                fee_data = EXCHANGE_PAIRS[pair].copy()
                # Apply small random factor for realistic fee variation
                fee_data['fee_percent'] *= (0.9 + 0.2 * (time.time() % 1))
                fee_data['fee_fixed'] *= (0.8 + 0.4 * (time.time() % 1))
                
                return ExchangeFeeData(
                    pair=pair,
                    fee_percent=fee_data['fee_percent'],
                    fee_fixed=fee_data['fee_fixed'],
                    min_amount=fee_data['min_amount']
                )
            
            return None
            
        except Exception:
            return None


class DataManager:
    """Manages data fetching with fallback and caching."""
    
    def __init__(self):
        self.coinlist_primary_api = "CoinGecko"
        self.historical_primary_api = "CoinGecko"
        self.historical_cache: Dict[str, Dict[str, Any]] = {}
    
    def get_top_coins(self, user_currency: str = 'usd', limit: int = 100) -> tuple[List[CoinData], str]:
        """Get top coins with API fallback."""
        coins = []
        active_api = None
        
        if self.coinlist_primary_api == "CoinGecko":
            coins = CoinGeckoProvider.get_top_coins(user_currency, limit)
            if coins:
                active_api = "CoinGecko"
            else:
                coins = CoinCapProvider.get_top_coins(limit)
                if coins:
                    active_api = "CoinCap"
        else:  # CoinCap primary
            coins = CoinCapProvider.get_top_coins(limit)
            if coins:
                active_api = "CoinCap"
            else:
                coins = CoinGeckoProvider.get_top_coins(user_currency, limit)
                if coins:
                    active_api = "CoinGecko"
        
        return coins, active_api or "None"
    
    def get_historical_data(self, coin_id: str, days: str, user_currency: str = 'usd') -> List[PricePoint]:
        """Get historical data with caching and API fallback."""
        now = time.time()
        cache_key = f"{coin_id}_{days}"
        
        # Check cache first
        entry = self.historical_cache.get(cache_key)
        if entry and (now - entry['ts'] < HIST_CACHE_TTL):
            return entry['prices']
        
        prices = []
        
        # Try APIs based on preference
        if days == "max":
            prices = CoinGeckoProvider.get_historical_data(coin_id, days, user_currency)
            if prices:
                self.historical_primary_api = "CoinGecko"
        else:
            if self.historical_primary_api == "CoinGecko":
                prices = CoinGeckoProvider.get_historical_data(coin_id, days, user_currency)
                if not prices:
                    prices = CoinCapProvider.get_historical_data(coin_id, days)
                    if prices:
                        self.historical_primary_api = "CoinCap"
            else:  # CoinCap primary
                prices = CoinCapProvider.get_historical_data(coin_id, days)
                if not prices:
                    prices = CoinGeckoProvider.get_historical_data(coin_id, days, user_currency)
                    if prices:
                        self.historical_primary_api = "CoinGecko"
        
        # Cache the result
        self.historical_cache[cache_key] = {'ts': now, 'prices': prices}
        return prices
    
    def set_primary_api(self, api_name: str) -> None:
        """Set the primary API for coin list fetching."""
        if api_name in ["CoinGecko", "CoinCap"]:
            self.coinlist_primary_api = api_name