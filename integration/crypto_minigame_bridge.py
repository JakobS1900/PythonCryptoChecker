"""
Crypto-MiniGame Integration Bridge - Connects trading system with mini-games for enhanced rewards.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, Integer, JSON

from database import get_db_session, Base
from virtual_economy import virtual_economy_engine
from crypto_market import market_data_service
from crypto_trading import portfolio_manager
from mini_games import mini_game_manager
from logger import logger


class RewardMultiplierType(Enum):
    TRADING_VOLUME = "TRADING_VOLUME"      # Based on recent trading activity
    PORTFOLIO_SIZE = "PORTFOLIO_SIZE"      # Based on portfolio value
    LEARNING_STREAK = "LEARNING_STREAK"    # Based on education progress
    ACHIEVEMENT_TIER = "ACHIEVEMENT_TIER"  # Based on user achievements
    CRYPTO_PERFORMANCE = "CRYPTO_PERFORMANCE" # Based on portfolio performance


class CryptoMiniGameBonus(Base):
    """Crypto-based bonuses for mini-game performance."""
    __tablename__ = "crypto_minigame_bonuses"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    
    # Bonus Configuration
    bonus_type = Column(String, nullable=False)  # TRADING_VOLUME, PORTFOLIO_SIZE, etc.
    multiplier = Column(Float, default=1.0)      # Reward multiplier (1.0 = 100%)
    active_until = Column(DateTime)              # When bonus expires
    
    # Trigger Conditions
    trigger_conditions = Column(JSON)            # Conditions that activated bonus
    current_streak = Column(Integer, default=0)  # Current streak for streak-based bonuses
    
    # Usage Tracking
    times_used = Column(Integer, default=0)
    max_uses = Column(Integer, default=10)       # Maximum uses per bonus period
    gems_boosted = Column(Float, default=0.0)    # Total extra GEMs earned
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CryptoGameIntegration(Base):
    """Integration events between crypto trading and mini-games."""
    __tablename__ = "crypto_game_integrations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    
    # Integration Type
    integration_type = Column(String, nullable=False)  # TRADING_REWARD, PRICE_PREDICTION, etc.
    source_system = Column(String, nullable=False)     # TRADING, MINI_GAMES, EDUCATION
    target_system = Column(String, nullable=False)     # TRADING, MINI_GAMES, EDUCATION
    
    # Event Data
    event_data = Column(JSON)                          # Specific event information
    reward_amount = Column(Float, default=0.0)         # GEMs rewarded
    bonus_multiplier = Column(Float, default=1.0)      # Applied bonus multiplier
    
    # Crypto Context
    related_crypto = Column(String)                    # Cryptocurrency involved
    market_condition = Column(String)                  # Market condition at time of event
    portfolio_impact = Column(Float, default=0.0)     # Impact on user's portfolio
    
    # Status
    processed = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class CryptoMiniGameBridge:
    """Manages integration between crypto trading and mini-games systems."""
    
    def __init__(self):
        self.base_multipliers = {
            RewardMultiplierType.TRADING_VOLUME: {
                "low": 1.1,      # 10% bonus for low volume traders
                "medium": 1.25,  # 25% bonus for medium volume
                "high": 1.5,     # 50% bonus for high volume
                "whale": 2.0     # 100% bonus for whale traders
            },
            RewardMultiplierType.PORTFOLIO_SIZE: {
                "starter": 1.0,   # No bonus for small portfolios
                "growing": 1.15,  # 15% bonus for growing portfolios
                "established": 1.3, # 30% bonus for established portfolios
                "whale": 1.75     # 75% bonus for whale portfolios
            },
            RewardMultiplierType.LEARNING_STREAK: {
                "newbie": 1.0,    # No bonus for new learners
                "student": 1.2,   # 20% bonus for consistent learners
                "scholar": 1.4,   # 40% bonus for dedicated learners
                "master": 1.8     # 80% bonus for learning masters
            }
        }
    
    async def calculate_user_multipliers(self, user_id: str) -> Dict[str, float]:
        """Calculate all active multipliers for a user."""
        try:
            async with get_db_session() as session:
                multipliers = {}
                
                # Trading Volume Multiplier
                trading_multiplier = await self._calculate_trading_volume_multiplier(session, user_id)
                if trading_multiplier > 1.0:
                    multipliers[RewardMultiplierType.TRADING_VOLUME.value] = trading_multiplier
                
                # Portfolio Size Multiplier
                portfolio_multiplier = await self._calculate_portfolio_size_multiplier(session, user_id)
                if portfolio_multiplier > 1.0:
                    multipliers[RewardMultiplierType.PORTFOLIO_SIZE.value] = portfolio_multiplier
                
                # Learning Streak Multiplier
                learning_multiplier = await self._calculate_learning_streak_multiplier(session, user_id)
                if learning_multiplier > 1.0:
                    multipliers[RewardMultiplierType.LEARNING_STREAK.value] = learning_multiplier
                
                # Performance Multiplier
                performance_multiplier = await self._calculate_performance_multiplier(session, user_id)
                if performance_multiplier > 1.0:
                    multipliers[RewardMultiplierType.CRYPTO_PERFORMANCE.value] = performance_multiplier
                
                return multipliers
                
        except Exception as e:
            logger.error(f"Failed to calculate user multipliers: {e}")
            return {}
    
    async def _calculate_trading_volume_multiplier(self, session: AsyncSession, user_id: str) -> float:
        """Calculate multiplier based on recent trading volume."""
        try:
            # Get trading history from last 7 days
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            # This would query actual trading history in a full implementation
            # For now, simulate based on portfolio activity
            portfolio = await portfolio_manager.get_user_portfolio(user_id)
            
            total_portfolio_value = portfolio.get("total_portfolio_value_gems", 0)
            
            if total_portfolio_value >= 50000:
                return self.base_multipliers[RewardMultiplierType.TRADING_VOLUME]["whale"]
            elif total_portfolio_value >= 20000:
                return self.base_multipliers[RewardMultiplierType.TRADING_VOLUME]["high"]
            elif total_portfolio_value >= 5000:
                return self.base_multipliers[RewardMultiplierType.TRADING_VOLUME]["medium"]
            elif total_portfolio_value >= 1000:
                return self.base_multipliers[RewardMultiplierType.TRADING_VOLUME]["low"]
            else:
                return 1.0
                
        except Exception as e:
            logger.error(f"Failed to calculate trading volume multiplier: {e}")
            return 1.0
    
    async def _calculate_portfolio_size_multiplier(self, session: AsyncSession, user_id: str) -> float:
        """Calculate multiplier based on portfolio size."""
        try:
            portfolio = await portfolio_manager.get_user_portfolio(user_id)
            total_value = portfolio.get("total_portfolio_value_gems", 0)
            
            if total_value >= 100000:
                return self.base_multipliers[RewardMultiplierType.PORTFOLIO_SIZE]["whale"]
            elif total_value >= 25000:
                return self.base_multipliers[RewardMultiplierType.PORTFOLIO_SIZE]["established"]
            elif total_value >= 5000:
                return self.base_multipliers[RewardMultiplierType.PORTFOLIO_SIZE]["growing"]
            else:
                return self.base_multipliers[RewardMultiplierType.PORTFOLIO_SIZE]["starter"]
                
        except Exception as e:
            logger.error(f"Failed to calculate portfolio size multiplier: {e}")
            return 1.0
    
    async def _calculate_learning_streak_multiplier(self, session: AsyncSession, user_id: str) -> float:
        """Calculate multiplier based on learning streak."""
        try:
            # This would integrate with the education system
            # For now, return a base multiplier
            
            # Simulate learning streak (would be actual data from education system)
            learning_streak = 5  # Mock 5-day streak
            
            if learning_streak >= 30:
                return self.base_multipliers[RewardMultiplierType.LEARNING_STREAK]["master"]
            elif learning_streak >= 14:
                return self.base_multipliers[RewardMultiplierType.LEARNING_STREAK]["scholar"]
            elif learning_streak >= 7:
                return self.base_multipliers[RewardMultiplierType.LEARNING_STREAK]["student"]
            else:
                return self.base_multipliers[RewardMultiplierType.LEARNING_STREAK]["newbie"]
                
        except Exception as e:
            logger.error(f"Failed to calculate learning streak multiplier: {e}")
            return 1.0
    
    async def _calculate_performance_multiplier(self, session: AsyncSession, user_id: str) -> float:
        """Calculate multiplier based on trading performance."""
        try:
            # Get performance metrics from last 30 days
            performance = await portfolio_manager.get_portfolio_performance(user_id, 30)
            
            roi_percentage = performance.get("roi_percentage", 0)
            
            if roi_percentage >= 50:
                return 2.0  # 100% bonus for exceptional performance
            elif roi_percentage >= 25:
                return 1.6  # 60% bonus for great performance
            elif roi_percentage >= 10:
                return 1.3  # 30% bonus for good performance
            elif roi_percentage >= 0:
                return 1.1  # 10% bonus for positive performance
            else:
                return 1.0  # No bonus for negative performance
                
        except Exception as e:
            logger.error(f"Failed to calculate performance multiplier: {e}")
            return 1.0
    
    async def apply_crypto_bonus_to_minigame(
        self,
        user_id: str,
        game_type: str,
        base_reward: float,
        game_performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply crypto-based bonuses to mini-game rewards."""
        try:
            async with get_db_session() as session:
                # Calculate all multipliers
                multipliers = await self.calculate_user_multipliers(user_id)
                
                # Calculate total multiplier
                total_multiplier = 1.0
                applied_bonuses = []
                
                for bonus_type, multiplier in multipliers.items():
                    total_multiplier *= multiplier
                    applied_bonuses.append({
                        "type": bonus_type,
                        "multiplier": multiplier,
                        "description": self._get_bonus_description(bonus_type, multiplier)
                    })
                
                # Apply crypto market condition bonus
                market_bonus = await self._get_market_condition_bonus()
                if market_bonus > 1.0:
                    total_multiplier *= market_bonus
                    applied_bonuses.append({
                        "type": "MARKET_CONDITION",
                        "multiplier": market_bonus,
                        "description": f"Market condition bonus: {(market_bonus-1)*100:.0f}%"
                    })
                
                # Calculate final reward
                bonus_reward = base_reward * (total_multiplier - 1.0)
                final_reward = base_reward + bonus_reward
                
                # Track the bonus application
                integration_event = CryptoGameIntegration(
                    user_id=user_id,
                    integration_type="MINIGAME_BONUS",
                    source_system="TRADING",
                    target_system="MINI_GAMES",
                    event_data={
                        "game_type": game_type,
                        "base_reward": base_reward,
                        "applied_bonuses": applied_bonuses,
                        "game_performance": game_performance
                    },
                    reward_amount=bonus_reward,
                    bonus_multiplier=total_multiplier
                )
                session.add(integration_event)
                await session.commit()
                
                logger.info(f"Applied {total_multiplier:.2f}x multiplier to {game_type} for user {user_id}")
                
                return {
                    "base_reward": base_reward,
                    "bonus_reward": bonus_reward,
                    "final_reward": final_reward,
                    "total_multiplier": total_multiplier,
                    "applied_bonuses": applied_bonuses,
                    "integration_event_id": integration_event.id
                }
                
        except Exception as e:
            logger.error(f"Failed to apply crypto bonus to mini-game: {e}")
            return {
                "base_reward": base_reward,
                "bonus_reward": 0.0,
                "final_reward": base_reward,
                "total_multiplier": 1.0,
                "applied_bonuses": [],
                "error": str(e)
            }
    
    def _get_bonus_description(self, bonus_type: str, multiplier: float) -> str:
        """Get human-readable bonus description."""
        bonus_pct = (multiplier - 1.0) * 100
        
        descriptions = {
            "TRADING_VOLUME": f"Active trader bonus: +{bonus_pct:.0f}%",
            "PORTFOLIO_SIZE": f"Portfolio size bonus: +{bonus_pct:.0f}%", 
            "LEARNING_STREAK": f"Learning streak bonus: +{bonus_pct:.0f}%",
            "CRYPTO_PERFORMANCE": f"Performance bonus: +{bonus_pct:.0f}%"
        }
        
        return descriptions.get(bonus_type, f"Bonus: +{bonus_pct:.0f}%")
    
    async def _get_market_condition_bonus(self) -> float:
        """Get bonus based on current market conditions."""
        try:
            # Get market overview
            market_overview = await portfolio_manager.get_market_overview()
            
            # Simple market condition bonus logic
            top_gainers = market_overview.get("top_gainers", [])
            
            if len(top_gainers) >= 5:
                avg_gain = sum(crypto.get("change_24h", 0) for crypto in top_gainers[:5]) / 5
                
                if avg_gain > 10:
                    return 1.3  # 30% bonus in strong bull market
                elif avg_gain > 5:
                    return 1.15 # 15% bonus in moderate bull market
            
            return 1.0  # No market bonus
            
        except Exception as e:
            logger.error(f"Failed to get market condition bonus: {e}")
            return 1.0
    
    async def create_crypto_prediction_game(
        self,
        user_id: str,
        crypto_symbol: str,
        prediction_type: str,  # UP, DOWN, SIDEWAYS
        time_horizon_hours: int = 24,
        stake_amount: float = 100.0
    ) -> Dict[str, Any]:
        """Create a crypto price prediction mini-game."""
        try:
            async with get_db_session() as session:
                # Get current price
                current_price_data = await market_data_service.get_current_price(crypto_symbol)
                if not current_price_data:
                    raise ValueError(f"Cannot get current price for {crypto_symbol}")
                
                current_price = current_price_data.price
                
                # Check user balance
                wallet = await virtual_economy_engine.get_user_wallet(session, user_id)
                if not wallet or wallet.gem_balance < stake_amount:
                    raise ValueError("Insufficient GEM balance for prediction")
                
                # Deduct stake amount
                await virtual_economy_engine.update_wallet_balance(
                    session, user_id, "GEM_COINS", -stake_amount,
                    f"Price prediction stake: {crypto_symbol}"
                )
                
                # Create prediction game
                prediction_id = str(uuid.uuid4())
                prediction_data = {
                    "prediction_id": prediction_id,
                    "crypto_symbol": crypto_symbol,
                    "current_price": current_price,
                    "prediction_type": prediction_type,
                    "stake_amount": stake_amount,
                    "time_horizon_hours": time_horizon_hours,
                    "created_at": datetime.utcnow().isoformat(),
                    "expires_at": (datetime.utcnow() + timedelta(hours=time_horizon_hours)).isoformat(),
                    "status": "ACTIVE"
                }
                
                # Store prediction
                integration_event = CryptoGameIntegration(
                    user_id=user_id,
                    integration_type="PRICE_PREDICTION",
                    source_system="MINI_GAMES",
                    target_system="TRADING",
                    event_data=prediction_data,
                    related_crypto=crypto_symbol,
                    portfolio_impact=-stake_amount
                )
                session.add(integration_event)
                await session.commit()
                
                logger.info(f"Created price prediction game for {crypto_symbol} by user {user_id}")
                
                return {
                    "prediction_id": prediction_id,
                    "crypto_symbol": crypto_symbol,
                    "current_price": current_price,
                    "prediction_type": prediction_type,
                    "stake_amount": stake_amount,
                    "potential_payout": stake_amount * 1.8,  # 80% payout for correct prediction
                    "expires_at": prediction_data["expires_at"],
                    "status": "ACTIVE"
                }
                
        except Exception as e:
            logger.error(f"Failed to create crypto prediction game: {e}")
            raise
    
    async def resolve_crypto_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """Resolve a crypto price prediction game."""
        try:
            async with get_db_session() as session:
                # Find prediction
                prediction_query = select(CryptoGameIntegration).where(
                    and_(
                        CryptoGameIntegration.integration_type == "PRICE_PREDICTION",
                        CryptoGameIntegration.event_data["prediction_id"].astext == prediction_id
                    )
                )
                result = await session.execute(prediction_query)
                prediction = result.scalar_one_or_none()
                
                if not prediction:
                    raise ValueError("Prediction not found")
                
                event_data = prediction.event_data
                crypto_symbol = event_data["crypto_symbol"]
                original_price = event_data["current_price"]
                prediction_type = event_data["prediction_type"]
                stake_amount = event_data["stake_amount"]
                
                # Get current price
                current_price_data = await market_data_service.get_current_price(crypto_symbol)
                if not current_price_data:
                    raise ValueError(f"Cannot get current price for {crypto_symbol}")
                
                current_price = current_price_data.price
                price_change_pct = ((current_price - original_price) / original_price) * 100
                
                # Determine if prediction was correct
                correct = False
                if prediction_type == "UP" and price_change_pct > 2:
                    correct = True
                elif prediction_type == "DOWN" and price_change_pct < -2:
                    correct = True
                elif prediction_type == "SIDEWAYS" and abs(price_change_pct) <= 2:
                    correct = True
                
                # Calculate payout
                payout = 0.0
                if correct:
                    payout = stake_amount * 1.8  # 80% profit for correct prediction
                    
                    # Apply crypto trading bonuses to payout
                    bonus_result = await self.apply_crypto_bonus_to_minigame(
                        prediction.user_id,
                        "PRICE_PREDICTION",
                        payout - stake_amount,  # Only bonus on profit
                        {
                            "prediction_correct": True,
                            "price_change_percentage": price_change_pct,
                            "prediction_type": prediction_type
                        }
                    )
                    
                    final_bonus = bonus_result["bonus_reward"]
                    payout += final_bonus
                    
                    # Credit payout
                    await virtual_economy_engine.update_wallet_balance(
                        session, prediction.user_id, "GEM_COINS", payout,
                        f"Price prediction win: {crypto_symbol}"
                    )
                
                # Update prediction record
                event_data["status"] = "RESOLVED"
                event_data["final_price"] = current_price
                event_data["price_change_percentage"] = price_change_pct
                event_data["correct"] = correct
                event_data["payout"] = payout
                event_data["resolved_at"] = datetime.utcnow().isoformat()
                
                prediction.event_data = event_data
                prediction.processed = True
                prediction.portfolio_impact = payout - stake_amount
                
                await session.commit()
                
                logger.info(f"Resolved prediction {prediction_id}: {'WIN' if correct else 'LOSS'}")
                
                return {
                    "prediction_id": prediction_id,
                    "crypto_symbol": crypto_symbol,
                    "original_price": original_price,
                    "final_price": current_price,
                    "price_change_percentage": price_change_pct,
                    "prediction_type": prediction_type,
                    "correct": correct,
                    "stake_amount": stake_amount,
                    "payout": payout,
                    "profit": payout - stake_amount,
                    "status": "RESOLVED"
                }
                
        except Exception as e:
            logger.error(f"Failed to resolve crypto prediction: {e}")
            raise
    
    async def get_user_integration_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user's crypto-minigame integration statistics."""
        try:
            async with get_db_session() as session:
                # Get integration events
                events_query = select(CryptoGameIntegration).where(
                    CryptoGameIntegration.user_id == user_id
                ).order_by(CryptoGameIntegration.created_at.desc())
                
                result = await session.execute(events_query)
                events = result.scalars().all()
                
                # Calculate statistics
                total_events = len(events)
                total_bonus_gems = sum(event.reward_amount for event in events)
                
                # Count by integration type
                integration_counts = {}
                for event in events:
                    int_type = event.integration_type
                    integration_counts[int_type] = integration_counts.get(int_type, 0) + 1
                
                # Get current multipliers
                current_multipliers = await self.calculate_user_multipliers(user_id)
                
                # Recent activity (last 10 events)
                recent_activity = []
                for event in events[:10]:
                    recent_activity.append({
                        "integration_type": event.integration_type,
                        "reward_amount": event.reward_amount,
                        "bonus_multiplier": event.bonus_multiplier,
                        "related_crypto": event.related_crypto,
                        "created_at": event.created_at.isoformat()
                    })
                
                return {
                    "user_id": user_id,
                    "total_integrations": total_events,
                    "total_bonus_gems_earned": total_bonus_gems,
                    "integration_type_counts": integration_counts,
                    "current_active_multipliers": current_multipliers,
                    "recent_activity": recent_activity,
                    "stats_generated_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get integration stats: {e}")
            return {}


# Global instance
crypto_minigame_bridge = CryptoMiniGameBridge()