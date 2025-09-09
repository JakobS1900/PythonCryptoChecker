"""
Data models for Crypto Analytics Platform.
Defines data structures and classes used throughout the application.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class CoinData:
    """Represents cryptocurrency data with price and market information."""
    id: str
    name: str
    symbol: str
    price: float
    emoji: str
    price_change_24h: float
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None


@dataclass
class PricePoint:
    """Represents a single price point in historical data."""
    timestamp: int
    price: float


@dataclass
class HistoricalData:
    """Represents historical price data for a cryptocurrency."""
    coin_id: str
    timeframe: str
    prices: List[PricePoint]
    last_updated: datetime


@dataclass
class ExchangeFeeData:
    """Represents exchange fee information for trading pairs."""
    fee_percent: float
    fee_fixed: float
    min_amount: float
    pair: str


@dataclass
class NetworkFeeData:
    """Represents network transaction fees for a cryptocurrency."""
    coin_id: str
    fast: float
    medium: float
    slow: float


@dataclass
class UserSession:
    """Represents user session data and preferences."""
    platform_type: str
    user_currency: str
    first_run: bool = True


class ApplicationState:
    """Manages global application state."""
    
    def __init__(self):
        self.last_update: int = 0
        self.coins_list: List[CoinData] = []
        self.current_page: int = 0
        self.active_api: Optional[str] = None
        self.historical_cache: Dict[str, Dict[str, Any]] = {}
        self.user_session: Optional[UserSession] = None
    
    def update_coins_list(self, coins: List[CoinData], api_name: str) -> None:
        """Update the coins list and active API."""
        self.coins_list = coins
        self.active_api = api_name
        self.last_update = int(datetime.now().timestamp())
    
    def get_coin_by_index(self, page: int, index: int) -> Optional[CoinData]:
        """Get a coin by its page and index position."""
        from config import COINS_PER_PAGE
        start_idx = page * COINS_PER_PAGE
        coin_index = start_idx + index - 1
        if 0 <= coin_index < len(self.coins_list):
            return self.coins_list[coin_index]
        return None
    
    def search_coins(self, query: str) -> List[CoinData]:
        """Search coins by query string."""
        from config import COINS_PER_PAGE
        query = query.strip().lower()
        results = []
        
        for coin in self.coins_list:
            symbol_lower = coin.symbol.lower()
            id_lower = coin.id.lower()
            name_lower = coin.name.lower()
            
            if (query == symbol_lower) or (query == id_lower) or (query in name_lower):
                results.append(coin)
                if len(results) >= COINS_PER_PAGE:
                    break
        
        return results