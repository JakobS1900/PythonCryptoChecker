"""
Market Simulator - Generates realistic crypto price movements and market events.
"""

import asyncio
import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .models import PriceData, MarketTrend, CryptoMarketConstants
from .crypto_registry import crypto_registry
from database import get_db_session
from logger import logger


class MarketCondition(Enum):
    BULL_MARKET = "BULL_MARKET"
    BEAR_MARKET = "BEAR_MARKET"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    FLASH_CRASH = "FLASH_CRASH"
    PUMP_AND_DUMP = "PUMP_AND_DUMP"


@dataclass
class MarketEvent:
    """Represents a market event affecting crypto prices."""
    event_type: str
    severity: float  # 0.0 to 1.0
    duration_minutes: int
    affected_cryptos: List[str]
    price_impact: float  # percentage change
    started_at: datetime


@dataclass
class CryptoSimulationState:
    """Simulation state for a specific cryptocurrency."""
    symbol: str
    base_price: float
    current_price: float
    trend: MarketTrend
    volatility: float
    trend_strength: float
    trend_duration_left: int  # minutes
    last_update: datetime
    daily_change: float
    support_level: float
    resistance_level: float


class MarketSimulator:
    """Simulates realistic cryptocurrency market behavior."""
    
    def __init__(self):
        self.is_running = False
        self.crypto_states: Dict[str, CryptoSimulationState] = {}
        self.market_condition = MarketCondition.SIDEWAYS
        self.active_events: List[MarketEvent] = []
        self.correlation_matrix = {}  # crypto correlations
        self.simulation_speed = 1.0  # 1.0 = real time, 2.0 = 2x speed
        self.base_volatility = CryptoMarketConstants.BASE_VOLATILITY
        
    async def start_simulation(self):
        """Start the market simulation."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Initialize crypto states
        await self._initialize_crypto_states()
        
        # Start simulation loops
        asyncio.create_task(self._price_simulation_loop())
        asyncio.create_task(self._market_event_loop())
        asyncio.create_task(self._trend_management_loop())
        
        logger.info("Market simulator started")
    
    async def stop_simulation(self):
        """Stop the market simulation."""
        self.is_running = False
        logger.info("Market simulator stopped")
    
    async def _initialize_crypto_states(self):
        """Initialize simulation states for all cryptocurrencies."""
        try:
            async with get_db_session() as session:
                cryptos = await crypto_registry.get_all_cryptos(session, active_only=True)
                
                for crypto in cryptos:
                    # Use real price if available, otherwise generate base price
                    base_price = crypto.current_price if crypto.current_price > 0 else self._generate_base_price(crypto.symbol)
                    
                    self.crypto_states[crypto.symbol] = CryptoSimulationState(
                        symbol=crypto.symbol,
                        base_price=base_price,
                        current_price=base_price,
                        trend=MarketTrend.SIDEWAYS,
                        volatility=self._calculate_crypto_volatility(crypto.symbol),
                        trend_strength=random.uniform(0.1, 0.8),
                        trend_duration_left=random.randint(60, 480),  # 1-8 hours
                        last_update=datetime.utcnow(),
                        daily_change=0.0,
                        support_level=base_price * 0.85,
                        resistance_level=base_price * 1.15
                    )
                
                logger.info(f"Initialized simulation for {len(self.crypto_states)} cryptocurrencies")
                
        except Exception as e:
            logger.error(f"Failed to initialize crypto states: {e}")
    
    def _generate_base_price(self, symbol: str) -> float:
        """Generate a realistic base price for a cryptocurrency."""
        # Price ranges based on typical crypto categories
        price_ranges = {
            'BTC': (25000, 70000),
            'ETH': (1500, 4500),
            'BNB': (200, 600),
            'ADA': (0.30, 1.20),
            'DOT': (4, 40),
            'LINK': (6, 50),
            'UNI': (4, 30)
        }
        
        if symbol in price_ranges:
            min_price, max_price = price_ranges[symbol]
            return random.uniform(min_price, max_price)
        
        # Generate based on symbol characteristics
        if 'USD' in symbol or symbol in ['USDT', 'USDC', 'DAI', 'BUSD']:
            return random.uniform(0.98, 1.02)  # Stablecoins
        elif symbol in ['SHIB', 'DOGE']:
            return random.uniform(0.00001, 0.10)  # Meme coins
        else:
            return random.uniform(0.10, 1000)  # Other altcoins
    
    def _calculate_crypto_volatility(self, symbol: str) -> float:
        """Calculate base volatility for a cryptocurrency."""
        # Different crypto types have different volatility profiles
        volatility_profiles = {
            'BTC': 0.03,   # Lower volatility
            'ETH': 0.04,
            'USDT': 0.005, # Very low volatility
            'USDC': 0.005,
            'BNB': 0.045,
            'DOGE': 0.08,  # High volatility
            'SHIB': 0.12   # Very high volatility
        }
        
        base_vol = volatility_profiles.get(symbol, 0.06)  # Default 6% volatility
        
        # Add random factor
        return base_vol * random.uniform(0.8, 1.4)
    
    async def _price_simulation_loop(self):
        """Main price simulation loop."""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                
                for symbol, state in self.crypto_states.items():
                    # Calculate time since last update
                    time_delta = (current_time - state.last_update).total_seconds() / 60  # minutes
                    time_delta *= self.simulation_speed
                    
                    if time_delta >= 1:  # Update every minute (simulation time)
                        new_price = self._calculate_new_price(state, time_delta)
                        
                        # Update state
                        state.current_price = new_price
                        state.last_update = current_time
                        state.daily_change = ((new_price - state.base_price) / state.base_price) * 100
                        
                        # Update support/resistance levels occasionally
                        if random.random() < 0.1:  # 10% chance per update
                            self._update_support_resistance(state)
                
                # Sleep based on simulation speed
                sleep_time = 5.0 / self.simulation_speed  # 5 seconds real time
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in price simulation loop: {e}")
                await asyncio.sleep(5)
    
    def _calculate_new_price(self, state: CryptoSimulationState, time_delta: float) -> float:
        """Calculate new price based on current state and market conditions."""
        # Base random walk
        random_factor = random.normalvariate(0, state.volatility)
        
        # Trend influence
        trend_factor = self._calculate_trend_factor(state)
        
        # Market condition influence
        market_factor = self._calculate_market_factor(state)
        
        # Event influence
        event_factor = self._calculate_event_factor(state)
        
        # Support/resistance influence
        sr_factor = self._calculate_support_resistance_factor(state)
        
        # Combine all factors
        total_change = (random_factor + trend_factor + market_factor + event_factor + sr_factor) * time_delta
        
        # Apply change
        new_price = state.current_price * (1 + total_change)
        
        # Ensure price doesn't go negative
        new_price = max(new_price, state.base_price * 0.01)  # Minimum 1% of base price
        
        # Apply daily change limits
        daily_change = ((new_price - state.base_price) / state.base_price)
        max_daily_change = CryptoMarketConstants.MAX_DAILY_CHANGE
        
        if abs(daily_change) > max_daily_change:
            if daily_change > 0:
                new_price = state.base_price * (1 + max_daily_change)
            else:
                new_price = state.base_price * (1 - max_daily_change)
        
        return new_price
    
    def _calculate_trend_factor(self, state: CryptoSimulationState) -> float:
        """Calculate trend influence on price movement."""
        if state.trend == MarketTrend.BULLISH:
            return state.trend_strength * 0.02  # 2% max positive trend
        elif state.trend == MarketTrend.BEARISH:
            return -state.trend_strength * 0.02  # 2% max negative trend
        elif state.trend == MarketTrend.VOLATILE:
            # Volatile trend adds extra randomness
            return random.normalvariate(0, state.volatility * 0.5)
        else:  # SIDEWAYS
            return 0.0
    
    def _calculate_market_factor(self, state: CryptoSimulationState) -> float:
        """Calculate market condition influence."""
        condition_effects = {
            MarketCondition.BULL_MARKET: 0.015,
            MarketCondition.BEAR_MARKET: -0.015,
            MarketCondition.SIDEWAYS: 0.0,
            MarketCondition.HIGH_VOLATILITY: random.normalvariate(0, 0.02),
            MarketCondition.FLASH_CRASH: -0.05,
            MarketCondition.PUMP_AND_DUMP: random.choice([0.03, -0.03])
        }
        
        return condition_effects.get(self.market_condition, 0.0)
    
    def _calculate_event_factor(self, state: CryptoSimulationState) -> float:
        """Calculate event influence on specific crypto."""
        event_factor = 0.0
        
        for event in self.active_events:
            if state.symbol in event.affected_cryptos:
                event_factor += event.price_impact * event.severity
        
        return event_factor
    
    def _calculate_support_resistance_factor(self, state: CryptoSimulationState) -> float:
        """Calculate support/resistance level influence."""
        current_price = state.current_price
        
        # Resistance pressure (when near resistance, tend to go down)
        if current_price > state.resistance_level * 0.95:
            resistance_pressure = -(current_price - state.resistance_level) / state.resistance_level * 0.1
            return resistance_pressure
        
        # Support bounce (when near support, tend to go up)
        elif current_price < state.support_level * 1.05:
            support_bounce = (state.support_level - current_price) / state.support_level * 0.1
            return support_bounce
        
        return 0.0
    
    def _update_support_resistance(self, state: CryptoSimulationState):
        """Update support and resistance levels based on recent price action."""
        # Simple algorithm: support = recent low * 0.98, resistance = recent high * 1.02
        recent_high = state.current_price * 1.1  # Simplified
        recent_low = state.current_price * 0.9   # Simplified
        
        state.resistance_level = recent_high * 1.02
        state.support_level = recent_low * 0.98
    
    async def _market_event_loop(self):
        """Generate and manage market events."""
        while self.is_running:
            try:
                # Clean up expired events
                current_time = datetime.utcnow()
                self.active_events = [
                    event for event in self.active_events 
                    if (current_time - event.started_at).total_seconds() < event.duration_minutes * 60
                ]
                
                # Generate new events occasionally
                if random.random() < 0.02:  # 2% chance every loop
                    await self._generate_market_event()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in market event loop: {e}")
                await asyncio.sleep(60)
    
    async def _generate_market_event(self):
        """Generate a random market event."""
        event_types = [
            ("BREAKING_NEWS", 0.7, 30, 0.05),
            ("REGULATORY_NEWS", 0.8, 120, 0.08),
            ("EXCHANGE_ISSUE", 0.6, 15, -0.03),
            ("WHALE_MOVEMENT", 0.5, 45, 0.04),
            ("TECHNICAL_BREAKTHROUGH", 0.9, 180, 0.12),
            ("MARKET_CORRECTION", 0.8, 90, -0.06)
        ]
        
        event_type, severity, duration, impact = random.choice(event_types)
        
        # Select affected cryptos
        all_symbols = list(self.crypto_states.keys())
        num_affected = random.randint(1, min(10, len(all_symbols)))
        affected_cryptos = random.sample(all_symbols, num_affected)
        
        event = MarketEvent(
            event_type=event_type,
            severity=severity * random.uniform(0.5, 1.5),
            duration_minutes=duration + random.randint(-15, 15),
            affected_cryptos=affected_cryptos,
            price_impact=impact * random.uniform(0.5, 2.0),
            started_at=datetime.utcnow()
        )
        
        self.active_events.append(event)
        logger.info(f"Generated market event: {event_type} affecting {len(affected_cryptos)} cryptos")
    
    async def _trend_management_loop(self):
        """Manage crypto trends and market conditions."""
        while self.is_running:
            try:
                # Update crypto trends
                for state in self.crypto_states.values():
                    state.trend_duration_left -= 5  # 5 minutes per loop
                    
                    # Change trend when duration expires
                    if state.trend_duration_left <= 0:
                        self._assign_new_trend(state)
                
                # Change market condition occasionally
                if random.random() < 0.05:  # 5% chance every 5 minutes
                    self._change_market_condition()
                
                await asyncio.sleep(300)  # Every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in trend management loop: {e}")
                await asyncio.sleep(300)
    
    def _assign_new_trend(self, state: CryptoSimulationState):
        """Assign a new trend to a cryptocurrency."""
        # Trend probabilities based on current market condition
        trend_probs = {
            MarketCondition.BULL_MARKET: {
                MarketTrend.BULLISH: 0.5,
                MarketTrend.SIDEWAYS: 0.3,
                MarketTrend.BEARISH: 0.1,
                MarketTrend.VOLATILE: 0.1
            },
            MarketCondition.BEAR_MARKET: {
                MarketTrend.BEARISH: 0.5,
                MarketTrend.SIDEWAYS: 0.3,
                MarketTrend.BULLISH: 0.1,
                MarketTrend.VOLATILE: 0.1
            },
            MarketCondition.SIDEWAYS: {
                MarketTrend.SIDEWAYS: 0.6,
                MarketTrend.BULLISH: 0.15,
                MarketTrend.BEARISH: 0.15,
                MarketTrend.VOLATILE: 0.1
            },
            MarketCondition.HIGH_VOLATILITY: {
                MarketTrend.VOLATILE: 0.7,
                MarketTrend.BULLISH: 0.1,
                MarketTrend.BEARISH: 0.1,
                MarketTrend.SIDEWAYS: 0.1
            }
        }
        
        probs = trend_probs.get(self.market_condition, trend_probs[MarketCondition.SIDEWAYS])
        trends = list(probs.keys())
        weights = list(probs.values())
        
        new_trend = random.choices(trends, weights=weights)[0]
        
        state.trend = new_trend
        state.trend_strength = random.uniform(0.2, 0.9)
        state.trend_duration_left = random.randint(60, 480)  # 1-8 hours
        
        logger.debug(f"Assigned new trend {new_trend.value} to {state.symbol}")
    
    def _change_market_condition(self):
        """Change the overall market condition."""
        conditions = list(MarketCondition)
        # Remove extreme conditions from normal rotation
        normal_conditions = [c for c in conditions if c not in [MarketCondition.FLASH_CRASH, MarketCondition.PUMP_AND_DUMP]]
        
        if random.random() < 0.1:  # 10% chance for extreme condition
            self.market_condition = random.choice([MarketCondition.FLASH_CRASH, MarketCondition.PUMP_AND_DUMP])
        else:
            self.market_condition = random.choice(normal_conditions)
        
        logger.info(f"Market condition changed to {self.market_condition.value}")
    
    async def get_current_prices(self) -> Dict[str, PriceData]:
        """Get current simulated prices for all cryptocurrencies."""
        prices = {}
        
        for symbol, state in self.crypto_states.items():
            price_change_24h = (state.current_price - state.base_price)
            price_change_percentage_24h = ((state.current_price - state.base_price) / state.base_price) * 100
            
            prices[symbol] = PriceData(
                symbol=symbol,
                price=state.current_price,
                price_change_24h=price_change_24h,
                price_change_percentage_24h=price_change_percentage_24h,
                market_cap=state.current_price * 1000000,  # Simplified market cap
                volume_24h=state.current_price * random.uniform(10000, 100000),  # Simulated volume
                timestamp=datetime.utcnow()
            )
        
        return prices
    
    def get_simulation_stats(self) -> Dict[str, Any]:
        """Get comprehensive simulation statistics."""
        if not self.crypto_states:
            return {}
        
        total_cryptos = len(self.crypto_states)
        bull_trends = sum(1 for s in self.crypto_states.values() if s.trend == MarketTrend.BULLISH)
        bear_trends = sum(1 for s in self.crypto_states.values() if s.trend == MarketTrend.BEARISH)
        
        avg_volatility = sum(s.volatility for s in self.crypto_states.values()) / total_cryptos
        avg_daily_change = sum(s.daily_change for s in self.crypto_states.values()) / total_cryptos
        
        return {
            "simulation_speed": self.simulation_speed,
            "market_condition": self.market_condition.value,
            "total_cryptocurrencies": total_cryptos,
            "bull_trends": bull_trends,
            "bear_trends": bear_trends,
            "sideways_trends": total_cryptos - bull_trends - bear_trends,
            "active_events": len(self.active_events),
            "average_volatility": avg_volatility,
            "average_daily_change": avg_daily_change,
            "top_performers": self._get_top_performers(5),
            "bottom_performers": self._get_bottom_performers(5),
            "recent_events": [
                {
                    "type": event.event_type,
                    "severity": event.severity,
                    "affected_count": len(event.affected_cryptos),
                    "started_ago_minutes": (datetime.utcnow() - event.started_at).total_seconds() / 60
                }
                for event in self.active_events[-5:]  # Last 5 events
            ]
        }
    
    def _get_top_performers(self, limit: int) -> List[Dict[str, Any]]:
        """Get top performing cryptocurrencies."""
        sorted_cryptos = sorted(
            self.crypto_states.values(),
            key=lambda s: s.daily_change,
            reverse=True
        )
        
        return [
            {
                "symbol": state.symbol,
                "daily_change": state.daily_change,
                "current_price": state.current_price,
                "trend": state.trend.value
            }
            for state in sorted_cryptos[:limit]
        ]
    
    def _get_bottom_performers(self, limit: int) -> List[Dict[str, Any]]:
        """Get worst performing cryptocurrencies."""
        sorted_cryptos = sorted(
            self.crypto_states.values(),
            key=lambda s: s.daily_change
        )
        
        return [
            {
                "symbol": state.symbol,
                "daily_change": state.daily_change,
                "current_price": state.current_price,
                "trend": state.trend.value
            }
            for state in sorted_cryptos[:limit]
        ]
    
    def set_simulation_speed(self, speed: float):
        """Set the simulation speed multiplier."""
        self.simulation_speed = max(0.1, min(speed, 10.0))  # Limit between 0.1x and 10x
        logger.info(f"Simulation speed set to {self.simulation_speed}x")
    
    async def trigger_market_event(self, event_type: str, severity: float, affected_symbols: List[str], duration_minutes: int):
        """Manually trigger a market event."""
        event = MarketEvent(
            event_type=event_type,
            severity=severity,
            duration_minutes=duration_minutes,
            affected_cryptos=affected_symbols,
            price_impact=severity * random.uniform(-0.1, 0.1),  # Random impact based on severity
            started_at=datetime.utcnow()
        )
        
        self.active_events.append(event)
        logger.info(f"Manually triggered market event: {event_type}")


# Global instance
market_simulator = MarketSimulator()