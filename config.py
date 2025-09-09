"""
Configuration module for Crypto Analytics Platform.
Contains all application settings, constants, and configuration parameters.
Supports environment variable overrides for flexible deployment.
"""

import os
from typing import Any, Dict, List, Optional


class ConfigurationManager:
    """Manages application configuration with environment variable support."""
    
    def __init__(self):
        self._config = self._load_configuration()
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration from environment variables with fallback to defaults."""
        return {
            # Application Settings
            'REFRESH_RATE': self._get_int_env('CAP_REFRESH_RATE', 60),
            'HIST_CACHE_TTL': self._get_int_env('CAP_HIST_CACHE_TTL', 3),
            'COINS_PER_PAGE': self._get_int_env('CAP_COINS_PER_PAGE', 10),
            'REQUEST_TIMEOUT': self._get_int_env('CAP_REQUEST_TIMEOUT', 10),
            
            # API Configuration
            'COINLIST_PRIMARY_API': self._get_str_env('CAP_COINLIST_PRIMARY_API', 'CoinGecko'),
            'HISTORICAL_PRIMARY_API': self._get_str_env('CAP_HISTORICAL_PRIMARY_API', 'CoinGecko'),
            'MAX_RETRIES': self._get_int_env('CAP_MAX_RETRIES', 3),
            'RETRY_DELAY': self._get_float_env('CAP_RETRY_DELAY', 0.5),
            
            # User Interface Settings
            'DEFAULT_CURRENCY': self._get_str_env('CAP_DEFAULT_CURRENCY', 'usd'),
            'DISABLE_COLORS': self._get_bool_env('CAP_DISABLE_COLORS', False),
            'FORCE_PLATFORM': self._get_str_env('CAP_FORCE_PLATFORM', None),
            
            # Development/Debug Settings
            'DEBUG_MODE': self._get_bool_env('CAP_DEBUG_MODE', False),
            'LOG_LEVEL': self._get_str_env('CAP_LOG_LEVEL', 'INFO'),
            'CACHE_ENABLED': self._get_bool_env('CAP_CACHE_ENABLED', True),
            
            # API URLs (for testing/development)
            'COINGECKO_BASE_URL': self._get_str_env('CAP_COINGECKO_BASE_URL', 'https://api.coingecko.com/api/v3'),
            'COINCAP_BASE_URL': self._get_str_env('CAP_COINCAP_BASE_URL', 'https://api.coincap.io/v2'),
            
            # Future API Keys (for premium endpoints)
            'COINGECKO_API_KEY': self._get_str_env('CAP_COINGECKO_API_KEY', None),
            'COINCAP_API_KEY': self._get_str_env('CAP_COINCAP_API_KEY', None),
        }
    
    def _get_str_env(self, key: str, default: Optional[str]) -> Optional[str]:
        """Get string environment variable with fallback."""
        value = os.getenv(key, default)
        return value if value != '' else default
    
    def _get_int_env(self, key: str, default: int) -> int:
        """Get integer environment variable with fallback."""
        try:
            value = os.getenv(key)
            return int(value) if value else default
        except (ValueError, TypeError):
            return default
    
    def _get_float_env(self, key: str, default: float) -> float:
        """Get float environment variable with fallback."""
        try:
            value = os.getenv(key)
            return float(value) if value else default
        except (ValueError, TypeError):
            return default
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean environment variable with fallback."""
        value = os.getenv(key, '').lower()
        if value in ('true', '1', 'yes', 'on'):
            return True
        elif value in ('false', '0', 'no', 'off'):
            return False
        return default
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return self._config.get(key, default)
    
    def update(self, key: str, value: Any) -> None:
        """Update configuration value at runtime."""
        self._config[key] = value
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values."""
        return self._config.copy()
    
    def reload(self) -> None:
        """Reload configuration from environment variables."""
        self._config = self._load_configuration()


# Initialize global configuration manager
config = ConfigurationManager()

# Legacy compatibility - these are now loaded from config manager
REFRESH_RATE = config.get('REFRESH_RATE')
HIST_CACHE_TTL = config.get('HIST_CACHE_TTL')
COINS_PER_PAGE = config.get('COINS_PER_PAGE')
COINLIST_PRIMARY_API = config.get('COINLIST_PRIMARY_API')
HISTORICAL_PRIMARY_API = config.get('HISTORICAL_PRIMARY_API')

# ANSI color codes for terminal output
COLORS = {
    'red': '\033[91m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'blue': '\033[94m',
    'magenta': '\033[95m',
    'cyan': '\033[96m',
    'white': '\033[97m',
    'reset': '\033[0m'
}

# Emoji map for popular cryptocurrencies
EMOJI_MAP = {
    'btc': '₿', 'bitcoin': '₿',
    'eth': 'Ξ', 'ethereum': 'Ξ',
    'xmr': 'Ⓜ', 'monero': 'Ⓜ',
    'avax': 'ⓐ', 'avalanche': 'ⓐ',
    'sol': '◎', 'solana': '◎',
    'doge': '🐕', 'dogecoin': '🐕',
    'shib': '🐕', 'shiba-inu': '🐕',
    'meme': '🎭', 'memecoin': '🎭',
    'ada': '𝔸', 'cardano': '𝔸',
    'dot': '●', 'polkadot': '●',
    'ltc': 'Ł', 'litecoin': 'Ł',
    'xrp': '✕', 'ripple': '✕',
    'trx': '₮', 'tron': '₮',
    'matic': '🟣', 'polygon': '🟣',
    'link': '🔗', 'chainlink': '🔗',
    'atom': '⚛', 'cosmos': '⚛',
    'uni': '🦄', 'uniswap': '🦄',
    'bch': 'Ƀ', 'bitcoin-cash': 'Ƀ',
    'etc': 'ξ', 'ethereum-classic': 'ξ',
    'xlm': '★', 'stellar': '★',
    'algo': '▵', 'algorand': '▵',
    'vet': '✔', 'vechain': '✔',
    'icp': '∞', 'internet-computer': '∞',
    'fil': '📁', 'filecoin': '📁',
    'ape': '🦍', 'apecoin': '🦍',
    'mana': '🎮', 'decentraland': '🎮',
    'sand': '🏖', 'the-sandbox': '🏖',
    'hbar': 'ⓗ', 'hedera': 'ⓗ'
}

# Supported fiat currency codes (uppercase) for CoinGecko
SUPPORTED_CURRENCIES = [
    'AED', 'ARS', 'AUD', 'BDT', 'BHD', 'BNB', 'BRL', 'BTC', 'CAD', 'CHF', 'CLP', 'CNY', 'CZK',
    'DKK', 'EUR', 'GBP', 'HKD', 'HUF', 'IDR', 'ILS', 'INR', 'JPY', 'KRW', 'KWD', 'LKR', 'MMK',
    'MXN', 'MYR', 'NGN', 'NOK', 'NZD', 'PHP', 'PKR', 'PLN', 'RUB', 'SAR', 'SEK', 'SGD', 'THB',
    'TWD', 'TRY', 'UAH', 'USD', 'VEF', 'VND', 'ZAR'
]

# Popular exchange pairs with typical fees
EXCHANGE_PAIRS = {
    'xmr_btc': {'fee_percent': 0.5, 'fee_fixed': 0.0005, 'min_amount': 0.01},
    'btc_eth': {'fee_percent': 0.3, 'fee_fixed': 0.0003, 'min_amount': 0.001},
    'eth_usdt': {'fee_percent': 0.2, 'fee_fixed': 1.0, 'min_amount': 0.1},
}

# Network fee API endpoints
FEE_API_ENDPOINTS = {
    'btc': 'https://mempool.space/api/v1/fees/recommended',
    'eth': 'https://ethgasstation.info/api/ethgasAPI.json',
    'xmr': 'https://localmonero.co/blocks/api/get_stats',
}