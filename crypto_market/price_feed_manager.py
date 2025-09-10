"""
Price Feed Manager - Manages real-time price feeds and data distribution.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable, Set
from dataclasses import dataclass
from enum import Enum

from .market_data_service import market_data_service
from .crypto_registry import crypto_registry
from .models import PriceData, MarketDataSource
from database import get_db_session
from logger import logger


class FeedStatus(Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


@dataclass
class PriceFeedConfig:
    """Configuration for price feed sources."""
    source: MarketDataSource
    enabled: bool
    priority: int
    update_interval: int  # seconds
    retry_attempts: int
    retry_delay: int  # seconds


@dataclass
class FeedMetrics:
    """Metrics for price feed performance."""
    messages_received: int = 0
    last_update: Optional[datetime] = None
    errors: int = 0
    reconnections: int = 0
    latency_ms: float = 0.0
    uptime_percentage: float = 100.0


class PriceFeedManager:
    """Manages multiple price feed sources and distributes price updates."""
    
    def __init__(self):
        self.is_running = False
        self.feeds = {}
        self.subscribers = {}  # symbol -> list of callback functions
        self.feed_configs = self._initialize_feed_configs()
        self.metrics = {source: FeedMetrics() for source in MarketDataSource}
        self._price_cache = {}
        self._last_price_broadcast = {}
        self.broadcast_throttle = 1.0  # seconds between broadcasts per symbol
        
    def _initialize_feed_configs(self) -> Dict[MarketDataSource, PriceFeedConfig]:
        """Initialize default feed configurations."""
        return {
            MarketDataSource.COINGECKO: PriceFeedConfig(
                source=MarketDataSource.COINGECKO,
                enabled=True,
                priority=1,
                update_interval=30,
                retry_attempts=3,
                retry_delay=5
            ),
            MarketDataSource.SIMULATION: PriceFeedConfig(
                source=MarketDataSource.SIMULATION,
                enabled=True,
                priority=2,
                update_interval=5,
                retry_attempts=5,
                retry_delay=2
            )
        }
    
    async def start(self):
        """Start the price feed manager."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start market data service
        await market_data_service.start_service()
        
        # Start feed monitoring
        for source, config in self.feed_configs.items():
            if config.enabled:
                asyncio.create_task(self._monitor_feed(source, config))
        
        # Start price distribution
        asyncio.create_task(self._price_distribution_loop())
        
        logger.info("Price feed manager started")
    
    async def stop(self):
        """Stop the price feed manager."""
        self.is_running = False
        
        # Stop market data service
        await market_data_service.stop_service()
        
        logger.info("Price feed manager stopped")
    
    async def _monitor_feed(self, source: MarketDataSource, config: PriceFeedConfig):
        """Monitor a specific price feed source."""
        while self.is_running:
            try:
                if source == MarketDataSource.COINGECKO:
                    await self._fetch_coingecko_prices()
                elif source == MarketDataSource.SIMULATION:
                    await self._fetch_simulated_prices()
                
                # Update metrics
                self.metrics[source].last_update = datetime.utcnow()
                self.metrics[source].messages_received += 1
                
                await asyncio.sleep(config.update_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring {source.value} feed: {e}")
                self.metrics[source].errors += 1
                await asyncio.sleep(config.retry_delay)
    
    async def _fetch_coingecko_prices(self):
        """Fetch prices from CoinGecko API."""
        start_time = datetime.utcnow()
        
        try:
            prices = await market_data_service.fetch_current_prices()
            
            for symbol, price_data in prices.items():
                self._update_price_cache(symbol, price_data, MarketDataSource.COINGECKO)
            
            # Calculate latency
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.metrics[MarketDataSource.COINGECKO].latency_ms = latency
            
        except Exception as e:
            logger.error(f"Failed to fetch CoinGecko prices: {e}")
            raise
    
    async def _fetch_simulated_prices(self):
        """Fetch simulated prices for testing/demo purposes."""
        from .market_simulator import market_simulator
        
        try:
            simulated_prices = await market_simulator.get_current_prices()
            
            for symbol, price_data in simulated_prices.items():
                # Only use simulation if no real data available
                if symbol not in self._price_cache or \
                   self._price_cache[symbol]['source'] == MarketDataSource.SIMULATION:
                    self._update_price_cache(symbol, price_data, MarketDataSource.SIMULATION)
            
        except Exception as e:
            logger.error(f"Failed to fetch simulated prices: {e}")
    
    def _update_price_cache(self, symbol: str, price_data: PriceData, source: MarketDataSource):
        """Update the internal price cache."""
        self._price_cache[symbol] = {
            'data': price_data,
            'source': source,
            'timestamp': datetime.utcnow(),
            'changed': True  # Mark for broadcast
        }
    
    async def _price_distribution_loop(self):
        """Distribute price updates to subscribers."""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                
                for symbol, cache_entry in self._price_cache.items():
                    if not cache_entry.get('changed', False):
                        continue
                    
                    # Check throttling
                    last_broadcast = self._last_price_broadcast.get(symbol)
                    if last_broadcast and \
                       (current_time - last_broadcast).total_seconds() < self.broadcast_throttle:
                        continue
                    
                    # Broadcast to subscribers
                    if symbol in self.subscribers:
                        price_data = cache_entry['data']
                        for callback in self.subscribers[symbol]:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(symbol, price_data)
                                else:
                                    callback(symbol, price_data)
                            except Exception as e:
                                logger.error(f"Error in price callback for {symbol}: {e}")
                    
                    # Mark as broadcasted
                    cache_entry['changed'] = False
                    self._last_price_broadcast[symbol] = current_time
                
                await asyncio.sleep(0.5)  # 500ms update cycle
                
            except Exception as e:
                logger.error(f"Error in price distribution loop: {e}")
                await asyncio.sleep(1)
    
    def subscribe_to_price(self, symbol: str, callback: Callable):
        """Subscribe to price updates for a specific symbol."""
        if symbol not in self.subscribers:
            self.subscribers[symbol] = []
        
        self.subscribers[symbol].append(callback)
        logger.info(f"Subscribed to price updates for {symbol}")
        
        # Send current price if available
        if symbol in self._price_cache:
            price_data = self._price_cache[symbol]['data']
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(symbol, price_data))
                else:
                    callback(symbol, price_data)
            except Exception as e:
                logger.error(f"Error sending initial price for {symbol}: {e}")
    
    def unsubscribe_from_price(self, symbol: str, callback: Callable):
        """Unsubscribe from price updates for a specific symbol."""
        if symbol in self.subscribers and callback in self.subscribers[symbol]:
            self.subscribers[symbol].remove(callback)
            if not self.subscribers[symbol]:
                del self.subscribers[symbol]
            logger.info(f"Unsubscribed from price updates for {symbol}")
    
    def get_current_price(self, symbol: str) -> Optional[PriceData]:
        """Get the current cached price for a symbol."""
        if symbol in self._price_cache:
            return self._price_cache[symbol]['data']
        return None
    
    def get_all_prices(self) -> Dict[str, PriceData]:
        """Get all current cached prices."""
        return {
            symbol: cache_entry['data'] 
            for symbol, cache_entry in self._price_cache.items()
        }
    
    def get_feed_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for all feeds."""
        metrics_data = {}
        
        for source, metrics in self.metrics.items():
            uptime_hours = 24  # Calculate based on actual uptime
            total_possible_updates = uptime_hours * 3600 / self.feed_configs[source].update_interval
            success_rate = (metrics.messages_received / max(total_possible_updates, 1)) * 100
            
            metrics_data[source.value] = {
                'messages_received': metrics.messages_received,
                'last_update': metrics.last_update.isoformat() if metrics.last_update else None,
                'errors': metrics.errors,
                'reconnections': metrics.reconnections,
                'latency_ms': metrics.latency_ms,
                'success_rate': min(success_rate, 100.0),
                'status': 'CONNECTED' if metrics.last_update and 
                         (datetime.utcnow() - metrics.last_update).seconds < 120 else 'DISCONNECTED'
            }
        
        return metrics_data
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """Get statistics about price subscriptions."""
        return {
            'total_subscriptions': sum(len(callbacks) for callbacks in self.subscribers.values()),
            'symbols_subscribed': len(self.subscribers),
            'active_symbols': list(self.subscribers.keys()),
            'cached_symbols': len(self._price_cache),
            'last_broadcast_times': {
                symbol: timestamp.isoformat() 
                for symbol, timestamp in self._last_price_broadcast.items()
            }
        }
    
    async def force_price_update(self, symbols: Optional[List[str]] = None):
        """Force an immediate price update for specified symbols or all."""
        try:
            if symbols:
                # Fetch specific symbols
                prices = await market_data_service.fetch_current_prices(symbols)
            else:
                # Fetch all prices
                prices = await market_data_service.fetch_current_prices()
            
            for symbol, price_data in prices.items():
                self._update_price_cache(symbol, price_data, MarketDataSource.COINGECKO)
            
            logger.info(f"Forced price update completed for {len(prices)} symbols")
            return len(prices)
            
        except Exception as e:
            logger.error(f"Failed to force price update: {e}")
            return 0
    
    def configure_feed(self, source: MarketDataSource, **config_updates):
        """Update configuration for a price feed source."""
        if source in self.feed_configs:
            for key, value in config_updates.items():
                if hasattr(self.feed_configs[source], key):
                    setattr(self.feed_configs[source], key, value)
            
            logger.info(f"Updated configuration for {source.value} feed")
        else:
            logger.warning(f"Unknown feed source: {source.value}")


# Global instance
price_feed_manager = PriceFeedManager()