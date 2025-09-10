"""
Crypto market data models for price feeds and market information.
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from sqlalchemy import Column, String, Float, DateTime, Boolean, Integer, Text, JSON, Index
from database import Base


class MarketDataSource(Enum):
    COINGECKO = "COINGECKO"
    COINMARKETCAP = "COINMARKETCAP"
    SIMULATION = "SIMULATION"
    MANUAL = "MANUAL"


class PriceInterval(Enum):
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"


class MarketTrend(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    SIDEWAYS = "SIDEWAYS"
    VOLATILE = "VOLATILE"


@dataclass
class PriceData:
    """Real-time price data structure."""
    symbol: str
    price: float
    price_change_24h: float
    price_change_percentage_24h: float
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class CandlestickData:
    """OHLCV candlestick data."""
    symbol: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    interval: PriceInterval


class CryptoCurrency(Base):
    """Cryptocurrency asset information."""
    __tablename__ = "cryptocurrencies"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic Information
    symbol = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    coingecko_id = Column(String, unique=True, index=True)
    
    # Market Data
    current_price = Column(Float, default=0.0)
    market_cap = Column(Float, default=0.0)
    market_cap_rank = Column(Integer)
    volume_24h = Column(Float, default=0.0)
    
    # Price Changes
    price_change_24h = Column(Float, default=0.0)
    price_change_percentage_24h = Column(Float, default=0.0)
    price_change_percentage_7d = Column(Float, default=0.0)
    price_change_percentage_30d = Column(Float, default=0.0)
    
    # Supply Information
    circulating_supply = Column(Float)
    total_supply = Column(Float)
    max_supply = Column(Float)
    
    # Metadata
    description = Column(Text)
    website_url = Column(String)
    logo_url = Column(String)
    category = Column(String)  # DeFi, Layer 1, Layer 2, etc.
    
    # Trading Configuration
    is_tradeable = Column(Boolean, default=True)
    min_trade_amount = Column(Float, default=0.00001)
    max_trade_amount = Column(Float, default=1000000.0)
    trading_fee_percentage = Column(Float, default=0.25)  # 0.25% default
    
    # Status
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_crypto_symbol_active', 'symbol', 'is_active'),
        Index('idx_crypto_market_cap_rank', 'market_cap_rank'),
    )


class PriceHistory(Base):
    """Historical price data storage."""
    __tablename__ = "price_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    crypto_id = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    
    # OHLCV Data
    timestamp = Column(DateTime, nullable=False, index=True)
    interval = Column(String, nullable=False)  # 1m, 5m, 1h, 1d, etc.
    
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, default=0.0)
    
    # Market Data
    market_cap = Column(Float)
    price_change = Column(Float, default=0.0)
    price_change_percentage = Column(Float, default=0.0)
    
    # Data Source
    source = Column(String, default="COINGECKO")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_price_history_crypto_time', 'crypto_id', 'timestamp'),
        Index('idx_price_history_symbol_interval', 'symbol', 'interval', 'timestamp'),
    )


class MarketEvent(Base):
    """Market events that affect crypto prices."""
    __tablename__ = "market_events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Event Information
    title = Column(String, nullable=False)
    description = Column(Text)
    event_type = Column(String, nullable=False)  # NEWS, TECHNICAL, FUNDAMENTAL
    
    # Impact
    affected_cryptos = Column(JSON)  # List of crypto symbols
    impact_severity = Column(String)  # LOW, MEDIUM, HIGH, CRITICAL
    price_impact_percentage = Column(Float)  # Expected price impact
    
    # Timing
    event_date = Column(DateTime, nullable=False)
    duration_hours = Column(Integer, default=24)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_simulated = Column(Boolean, default=False)
    
    # Metadata
    source_url = Column(String)
    tags = Column(JSON)  # List of tags
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserPriceAlert(Base):
    """User-configured price alerts."""
    __tablename__ = "user_price_alerts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    crypto_id = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    
    # Alert Configuration
    alert_type = Column(String, nullable=False)  # PRICE_ABOVE, PRICE_BELOW, CHANGE_PERCENTAGE
    target_value = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_triggered = Column(Boolean, default=False)
    triggered_at = Column(DateTime)
    
    # Notification Settings
    notify_email = Column(Boolean, default=False)
    notify_push = Column(Boolean, default=True)
    notify_in_app = Column(Boolean, default=True)
    
    # Metadata
    message = Column(String)
    repeat_alert = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketAnalysis(Base):
    """AI-powered market analysis and predictions."""
    __tablename__ = "market_analysis"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    crypto_id = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=False)
    
    # Analysis Data
    analysis_type = Column(String, nullable=False)  # TECHNICAL, SENTIMENT, FUNDAMENTAL
    timeframe = Column(String, nullable=False)  # 1h, 4h, 1d, 1w
    
    # Predictions
    price_prediction = Column(Float)
    confidence_score = Column(Float)  # 0.0 to 1.0
    trend_direction = Column(String)  # BULLISH, BEARISH, NEUTRAL
    
    # Technical Indicators
    rsi = Column(Float)
    macd = Column(Float)
    bollinger_position = Column(Float)
    volume_trend = Column(String)
    
    # Analysis Results
    buy_signal_strength = Column(Float)  # 0.0 to 1.0
    sell_signal_strength = Column(Float)  # 0.0 to 1.0
    hold_signal_strength = Column(Float)  # 0.0 to 1.0
    
    # Metadata
    analysis_data = Column(JSON)  # Additional analysis details
    analysis_summary = Column(Text)
    
    # Timestamps
    analysis_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    valid_until = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# Constants for the crypto market system
class CryptoMarketConstants:
    """Configuration constants for crypto market system."""
    
    # API Configuration
    COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"
    PRICE_UPDATE_INTERVAL = 60  # seconds
    HISTORICAL_DATA_RETENTION = 365  # days
    
    # Trading Configuration
    DEFAULT_TRADING_FEE = 0.25  # 0.25%
    MIN_TRADE_VALUE_GEM = 10.0  # Minimum 10 GEM trade
    MAX_TRADE_VALUE_GEM = 1000000.0  # Maximum 1M GEM trade
    
    # Price Simulation
    BASE_VOLATILITY = 0.02  # 2% base volatility
    MAX_DAILY_CHANGE = 0.20  # Maximum 20% daily change
    TREND_DURATION_HOURS = [4, 12, 24, 48, 72]  # Possible trend durations
    
    # Market Categories
    CRYPTO_CATEGORIES = [
        "Layer 1", "Layer 2", "DeFi", "Privacy", "Gaming", "NFT",
        "Meme", "Exchange", "Stablecoin", "Oracle", "Infrastructure",
        "Metaverse", "AI", "Storage", "IoT", "Social"
    ]
    
    # Top Cryptocurrencies (expanded list)
    TOP_CRYPTOS = [
        # Top 10 by Market Cap
        {"symbol": "BTC", "name": "Bitcoin", "coingecko_id": "bitcoin", "category": "Store of Value"},
        {"symbol": "ETH", "name": "Ethereum", "coingecko_id": "ethereum", "category": "Layer 1"},
        {"symbol": "USDT", "name": "Tether", "coingecko_id": "tether", "category": "Stablecoin"},
        {"symbol": "BNB", "name": "BNB", "coingecko_id": "binancecoin", "category": "Exchange"},
        {"symbol": "SOL", "name": "Solana", "coingecko_id": "solana", "category": "Layer 1"},
        {"symbol": "USDC", "name": "USD Coin", "coingecko_id": "usd-coin", "category": "Stablecoin"},
        {"symbol": "XRP", "name": "Ripple", "coingecko_id": "ripple", "category": "Payment"},
        {"symbol": "TON", "name": "Toncoin", "coingecko_id": "the-open-network", "category": "Layer 1"},
        {"symbol": "DOGE", "name": "Dogecoin", "coingecko_id": "dogecoin", "category": "Meme"},
        {"symbol": "ADA", "name": "Cardano", "coingecko_id": "cardano", "category": "Layer 1"},
        
        # Popular Altcoins
        {"symbol": "AVAX", "name": "Avalanche", "coingecko_id": "avalanche-2", "category": "Layer 1"},
        {"symbol": "SHIB", "name": "Shiba Inu", "coingecko_id": "shiba-inu", "category": "Meme"},
        {"symbol": "DOT", "name": "Polkadot", "coingecko_id": "polkadot", "category": "Layer 1"},
        {"symbol": "MATIC", "name": "Polygon", "coingecko_id": "matic-network", "category": "Layer 2"},
        {"symbol": "LTC", "name": "Litecoin", "coingecko_id": "litecoin", "category": "Payment"},
        {"symbol": "UNI", "name": "Uniswap", "coingecko_id": "uniswap", "category": "DeFi"},
        {"symbol": "LINK", "name": "Chainlink", "coingecko_id": "chainlink", "category": "Oracle"},
        {"symbol": "ATOM", "name": "Cosmos", "coingecko_id": "cosmos", "category": "Infrastructure"},
        {"symbol": "VET", "name": "VeChain", "coingecko_id": "vechain", "category": "Supply Chain"},
        {"symbol": "XLM", "name": "Stellar", "coingecko_id": "stellar", "category": "Payment"},
        
        # DeFi Tokens
        {"symbol": "AAVE", "name": "Aave", "coingecko_id": "aave", "category": "DeFi"},
        {"symbol": "MKR", "name": "Maker", "coingecko_id": "maker", "category": "DeFi"},
        {"symbol": "COMP", "name": "Compound", "coingecko_id": "compound-governance-token", "category": "DeFi"},
        {"symbol": "SUSHI", "name": "SushiSwap", "coingecko_id": "sushi", "category": "DeFi"},
        {"symbol": "CRV", "name": "Curve DAO", "coingecko_id": "curve-dao-token", "category": "DeFi"},
        
        # Gaming & NFT
        {"symbol": "AXS", "name": "Axie Infinity", "coingecko_id": "axie-infinity", "category": "Gaming"},
        {"symbol": "SAND", "name": "The Sandbox", "coingecko_id": "the-sandbox", "category": "Gaming"},
        {"symbol": "MANA", "name": "Decentraland", "coingecko_id": "decentraland", "category": "Metaverse"},
        {"symbol": "ENJ", "name": "Enjin Coin", "coingecko_id": "enjincoin", "category": "Gaming"},
        {"symbol": "FLOW", "name": "Flow", "coingecko_id": "flow", "category": "NFT"},
        
        # Privacy & Anonymous
        {"symbol": "XMR", "name": "Monero", "coingecko_id": "monero", "category": "Privacy"},
        {"symbol": "ZEC", "name": "Zcash", "coingecko_id": "zcash", "category": "Privacy"},
        {"symbol": "DASH", "name": "Dash", "coingecko_id": "dash", "category": "Privacy"},
        
        # Infrastructure & Utility
        {"symbol": "FIL", "name": "Filecoin", "coingecko_id": "filecoin", "category": "Storage"},
        {"symbol": "AR", "name": "Arweave", "coingecko_id": "arweave", "category": "Storage"},
        {"symbol": "GRT", "name": "The Graph", "coingecko_id": "the-graph", "category": "Infrastructure"},
        {"symbol": "THETA", "name": "Theta Network", "coingecko_id": "theta-token", "category": "Media"},
        
        # Exchange Tokens
        {"symbol": "CRO", "name": "Cronos", "coingecko_id": "crypto-com-chain", "category": "Exchange"},
        {"symbol": "OKB", "name": "OKB", "coingecko_id": "okb", "category": "Exchange"},
        {"symbol": "HT", "name": "Huobi Token", "coingecko_id": "huobi-token", "category": "Exchange"},
        
        # Emerging & Trendy
        {"symbol": "APE", "name": "ApeCoin", "coingecko_id": "apecoin", "category": "NFT"},
        {"symbol": "GMT", "name": "STEPN", "coingecko_id": "stepn", "category": "Move-to-Earn"},
        {"symbol": "LDO", "name": "Lido DAO", "coingecko_id": "lido-dao", "category": "DeFi"},
        {"symbol": "OP", "name": "Optimism", "coingecko_id": "optimism", "category": "Layer 2"},
        {"symbol": "ARB", "name": "Arbitrum", "coingecko_id": "arbitrum", "category": "Layer 2"},
        
        # Stablecoins
        {"symbol": "DAI", "name": "Dai", "coingecko_id": "dai", "category": "Stablecoin"},
        {"symbol": "BUSD", "name": "Binance USD", "coingecko_id": "binance-usd", "category": "Stablecoin"},
        {"symbol": "TUSD", "name": "TrueUSD", "coingecko_id": "true-usd", "category": "Stablecoin"},
        
        # AI & Technology
        {"symbol": "FET", "name": "Fetch.ai", "coingecko_id": "fetch-ai", "category": "AI"},
        {"symbol": "OCEAN", "name": "Ocean Protocol", "coingecko_id": "ocean-protocol", "category": "AI"},
        {"symbol": "SYN", "name": "Synapse", "coingecko_id": "synapse-2", "category": "Infrastructure"}
    ]