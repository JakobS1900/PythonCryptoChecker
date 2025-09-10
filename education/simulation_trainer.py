"""
Trading Simulation Trainer - Risk-free practice trading with AI coaching.
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func

from database import get_db_session, VirtualCryptoHolding
from crypto_market import market_data_service, market_simulator
from virtual_economy import virtual_economy_engine
from .learning_system import SimulationSession
from logger import logger


class SimulationType(Enum):
    PAPER_TRADING = "PAPER_TRADING"        # Live market simulation
    STRATEGY_TEST = "STRATEGY_TEST"        # Test specific strategies
    SCENARIO_PRACTICE = "SCENARIO_PRACTICE" # Predefined market scenarios
    CHALLENGE_MODE = "CHALLENGE_MODE"       # Timed challenges
    AI_COACHING = "AI_COACHING"            # AI-guided learning


class MarketScenario(Enum):
    BULL_MARKET = "BULL_MARKET"
    BEAR_MARKET = "BEAR_MARKET"
    FLASH_CRASH = "FLASH_CRASH"
    ALTCOIN_SEASON = "ALTCOIN_SEASON"
    BTCD_DOMINANCE = "BTC_DOMINANCE"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    SIDEWAYS_MARKET = "SIDEWAYS_MARKET"


class TrainingChallenge:
    """Training challenges with specific objectives."""
    
    def __init__(self, challenge_id: str, title: str, description: str, 
                 objective: str, scenario: MarketScenario, duration_hours: int,
                 starting_balance: float, target_return: float, difficulty: str):
        self.challenge_id = challenge_id
        self.title = title
        self.description = description
        self.objective = objective
        self.scenario = scenario
        self.duration_hours = duration_hours
        self.starting_balance = starting_balance
        self.target_return = target_return
        self.difficulty = difficulty


class SimulationTrainer:
    """Manages trading simulations and educational challenges."""
    
    def __init__(self):
        self.default_balance = 10000.0  # Starting GEMs for simulation
        self.training_challenges = self._initialize_challenges()
        self.ai_coaching_prompts = self._initialize_coaching_prompts()
    
    def _initialize_challenges(self) -> List[TrainingChallenge]:
        """Initialize predefined trading challenges."""
        return [
            TrainingChallenge(
                "bull-market-basics",
                "Bull Market Basics",
                "Learn to identify and trade in a rising market environment",
                "Achieve 15% return in 7 days during a bull market",
                MarketScenario.BULL_MARKET,
                168,  # 7 days in hours
                5000.0,
                15.0,
                "BEGINNER"
            ),
            TrainingChallenge(
                "bear-market-survival",
                "Bear Market Survival",
                "Practice defensive trading strategies during market downturns",
                "Minimize losses to less than 5% during bear market",
                MarketScenario.BEAR_MARKET,
                240,  # 10 days
                10000.0,
                -5.0,  # Target is to lose less than 5%
                "INTERMEDIATE"
            ),
            TrainingChallenge(
                "flash-crash-recovery",
                "Flash Crash Recovery",
                "Learn to handle sudden market crashes and find opportunities",
                "Recover from 30% portfolio drop within 3 days",
                MarketScenario.FLASH_CRASH,
                72,   # 3 days
                8000.0,
                10.0,
                "ADVANCED"
            ),
            TrainingChallenge(
                "altcoin-season-master",
                "Altcoin Season Master",
                "Capitalize on altcoin pumps while managing risk",
                "Beat Bitcoin performance by 25% in altcoin season",
                MarketScenario.ALTCOIN_SEASON,
                336,  # 14 days
                15000.0,
                50.0,
                "EXPERT"
            ),
            TrainingChallenge(
                "scalping-speedrun",
                "Scalping Speedrun",
                "Master quick in-and-out trades for small profits",
                "Make 20 profitable trades with 1% average gain each",
                MarketScenario.HIGH_VOLATILITY,
                24,   # 1 day
                3000.0,
                20.0,
                "ADVANCED"
            ),
            TrainingChallenge(
                "hodler-patience",
                "HODL Master",
                "Practice long-term holding strategies and patience",
                "Hold through 40% drawdown and end with 30% profit",
                MarketScenario.SIDEWAYS_MARKET,
                720,  # 30 days
                20000.0,
                30.0,
                "INTERMEDIATE"
            )
        ]
    
    def _initialize_coaching_prompts(self) -> Dict[str, List[str]]:
        """Initialize AI coaching prompts for different situations."""
        return {
            "entry_signals": [
                "📈 Great entry signal! This support bounce could be a good buying opportunity.",
                "⚠️  Consider waiting for confirmation. This might be a false breakout.",
                "🎯 Perfect timing! The RSI oversold condition suggests a potential reversal.",
                "🚨 High risk entry! Market is overbought - consider smaller position size."
            ],
            "risk_management": [
                "🛡️  Excellent risk management! Your stop loss protects your capital.",
                "⚠️  Your position size is too large. Consider reducing to 2-3% of portfolio.",
                "📊 Good risk-reward ratio! This 1:3 setup has great potential.",
                "🚨 Don't forget your stop loss! Never trade without protection."
            ],
            "market_psychology": [
                "🧠 FOMO detected! Take a deep breath and stick to your plan.",
                "💪 Great patience! Waiting for the right setup shows discipline.",
                "😰 Don't panic sell! This could be a temporary dip.",
                "🎉 Nice work staying calm during volatility!"
            ],
            "trade_execution": [
                "⚡ Perfect execution! Entry at support with good volume.",
                "🎯 Consider taking partial profits here - lock in some gains.",
                "📈 Trail your stop loss to protect profits as price rises.",
                "⏰ Time to exit? Your target has been reached."
            ]
        }
    
    async def create_simulation_session(
        self,
        user_id: str,
        simulation_type: SimulationType,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new simulation trading session."""
        try:
            async with get_db_session() as session:
                # Create simulation session
                sim_session = SimulationSession(
                    user_id=user_id,
                    simulation_type=simulation_type.value,
                    strategy_id=config.get("strategy_id"),
                    scenario_name=config.get("scenario_name"),
                    starting_balance_gems=config.get("starting_balance", self.default_balance),
                    current_balance_gems=config.get("starting_balance", self.default_balance),
                    allowed_cryptos=config.get("allowed_cryptos", ["BTC", "ETH", "ADA", "SOL", "DOT"]),
                    simulation_speed=config.get("simulation_speed", 1.0),
                    duration_days=config.get("duration_days", 7),
                    enable_margin=config.get("enable_margin", False),
                    educational_hints=config.get("educational_hints", True)
                )
                
                session.add(sim_session)
                await session.commit()
                await session.refresh(sim_session)
                
                # Initialize market scenario if specified
                if config.get("scenario_name"):
                    await self._setup_market_scenario(sim_session.id, config["scenario_name"])
                
                logger.info(f"Created simulation session {sim_session.id} for user {user_id}")
                
                return {
                    "session_id": sim_session.id,
                    "simulation_type": sim_session.simulation_type,
                    "starting_balance": sim_session.starting_balance_gems,
                    "current_balance": sim_session.current_balance_gems,
                    "allowed_cryptos": sim_session.allowed_cryptos,
                    "duration_days": sim_session.duration_days,
                    "created_at": sim_session.created_at.isoformat(),
                    "status": sim_session.status
                }
                
        except Exception as e:
            logger.error(f"Failed to create simulation session: {e}")
            raise
    
    async def _setup_market_scenario(self, session_id: str, scenario_name: str):
        """Setup specific market scenario for simulation."""
        try:
            # Configure market simulator based on scenario
            if scenario_name == MarketScenario.BULL_MARKET.value:
                market_simulator.market_condition = market_simulator.MarketCondition.BULL_MARKET
                market_simulator.simulation_speed = 2.0  # Faster for learning
            elif scenario_name == MarketScenario.BEAR_MARKET.value:
                market_simulator.market_condition = market_simulator.MarketCondition.BEAR_MARKET
            elif scenario_name == MarketScenario.FLASH_CRASH.value:
                market_simulator.market_condition = market_simulator.MarketCondition.FLASH_CRASH
                # Trigger immediate crash event
                await market_simulator.trigger_market_event(
                    "FLASH_CRASH", 0.9, ["BTC", "ETH", "ADA"], 60
                )
            elif scenario_name == MarketScenario.HIGH_VOLATILITY.value:
                market_simulator.market_condition = market_simulator.MarketCondition.HIGH_VOLATILITY
                market_simulator.base_volatility *= 2.0
            
            logger.info(f"Setup market scenario {scenario_name} for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to setup market scenario: {e}")
    
    async def execute_simulation_trade(
        self,
        session_id: str,
        trade_type: str,  # BUY or SELL
        crypto_symbol: str,
        amount: float,
        order_type: str = "MARKET"
    ) -> Dict[str, Any]:
        """Execute a trade within a simulation session."""
        try:
            async with get_db_session() as session:
                # Get simulation session
                sim_query = select(SimulationSession).where(SimulationSession.id == session_id)
                sim_result = await session.execute(sim_query)
                sim_session = sim_result.scalar_one_or_none()
                
                if not sim_session or sim_session.status != "ACTIVE":
                    raise ValueError("Simulation session not found or not active")
                
                # Check if crypto is allowed
                if crypto_symbol not in sim_session.allowed_cryptos:
                    raise ValueError(f"{crypto_symbol} not allowed in this simulation")
                
                # Get current price (from simulation)
                price_data = await market_simulator.get_current_prices()
                if crypto_symbol not in price_data:
                    raise ValueError(f"Price data not available for {crypto_symbol}")
                
                current_price = price_data[crypto_symbol].price
                
                # Execute trade logic
                if trade_type.upper() == "BUY":
                    total_cost = amount
                    crypto_amount = amount / current_price
                    
                    if sim_session.current_balance_gems < total_cost:
                        raise ValueError("Insufficient simulation balance")
                    
                    # Update balance
                    sim_session.current_balance_gems -= total_cost
                    
                    # Update or create crypto holding in simulation
                    await self._update_simulation_holding(
                        session, session_id, crypto_symbol, crypto_amount, current_price, "BUY"
                    )
                    
                elif trade_type.upper() == "SELL":
                    crypto_amount = amount
                    total_proceeds = amount * current_price
                    
                    # Check crypto balance
                    current_holding = await self._get_simulation_holding(
                        session, session_id, crypto_symbol
                    )
                    
                    if not current_holding or current_holding < crypto_amount:
                        raise ValueError(f"Insufficient {crypto_symbol} in simulation")
                    
                    # Update balance
                    sim_session.current_balance_gems += total_proceeds
                    
                    # Update crypto holding
                    await self._update_simulation_holding(
                        session, session_id, crypto_symbol, -crypto_amount, current_price, "SELL"
                    )
                
                # Update trade statistics
                sim_session.total_trades += 1
                sim_session.updated_at = datetime.utcnow()
                
                # Calculate portfolio value
                portfolio_value = await self._calculate_simulation_portfolio_value(
                    session, session_id, price_data
                )
                sim_session.current_portfolio_value = portfolio_value
                
                # Calculate performance metrics
                total_value = sim_session.current_balance_gems + portfolio_value
                sim_session.total_return_percentage = (
                    (total_value - sim_session.starting_balance_gems) / 
                    sim_session.starting_balance_gems * 100
                )
                
                await session.commit()
                
                # Generate AI coaching feedback if enabled
                coaching_feedback = []
                if sim_session.educational_hints:
                    coaching_feedback = await self._generate_coaching_feedback(
                        sim_session, trade_type, crypto_symbol, current_price
                    )
                
                logger.info(f"Executed {trade_type} trade in simulation {session_id}")
                
                return {
                    "trade_id": str(uuid.uuid4()),
                    "trade_type": trade_type,
                    "crypto_symbol": crypto_symbol,
                    "crypto_amount": crypto_amount if trade_type == "BUY" else amount,
                    "gem_amount": total_cost if trade_type == "BUY" else total_proceeds,
                    "price": current_price,
                    "new_balance": sim_session.current_balance_gems,
                    "portfolio_value": portfolio_value,
                    "total_return_percentage": sim_session.total_return_percentage,
                    "coaching_feedback": coaching_feedback,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to execute simulation trade: {e}")
            raise
    
    async def _update_simulation_holding(
        self,
        session: AsyncSession,
        session_id: str,
        crypto_symbol: str,
        amount_change: float,
        price: float,
        operation: str
    ):
        """Update crypto holdings in simulation (stored in metadata)."""
        # For simulation, we'll store holdings in the session metadata
        # In a full implementation, you'd have a separate simulation holdings table
        
        sim_query = select(SimulationSession).where(SimulationSession.id == session_id)
        result = await session.execute(sim_query)
        sim_session = result.scalar_one()
        
        # Initialize metadata if not exists
        if not hasattr(sim_session, 'metadata') or not sim_session.metadata:
            sim_session.metadata = {"holdings": {}}
        
        holdings = sim_session.metadata.get("holdings", {})
        
        if operation == "BUY":
            if crypto_symbol in holdings:
                # Update average cost
                old_amount = holdings[crypto_symbol]["amount"]
                old_cost = holdings[crypto_symbol]["average_cost"]
                new_total_cost = (old_amount * old_cost) + (amount_change * price)
                new_total_amount = old_amount + amount_change
                new_average_cost = new_total_cost / new_total_amount
                
                holdings[crypto_symbol] = {
                    "amount": new_total_amount,
                    "average_cost": new_average_cost
                }
            else:
                holdings[crypto_symbol] = {
                    "amount": amount_change,
                    "average_cost": price
                }
        
        elif operation == "SELL":
            if crypto_symbol in holdings:
                holdings[crypto_symbol]["amount"] -= abs(amount_change)
                if holdings[crypto_symbol]["amount"] <= 0:
                    del holdings[crypto_symbol]
        
        sim_session.metadata = {"holdings": holdings}
    
    async def _get_simulation_holding(
        self,
        session: AsyncSession,
        session_id: str,
        crypto_symbol: str
    ) -> float:
        """Get current simulation holding amount for a crypto."""
        sim_query = select(SimulationSession).where(SimulationSession.id == session_id)
        result = await session.execute(sim_query)
        sim_session = result.scalar_one()
        
        if not hasattr(sim_session, 'metadata') or not sim_session.metadata:
            return 0.0
        
        holdings = sim_session.metadata.get("holdings", {})
        return holdings.get(crypto_symbol, {}).get("amount", 0.0)
    
    async def _calculate_simulation_portfolio_value(
        self,
        session: AsyncSession,
        session_id: str,
        current_prices: Dict[str, Any]
    ) -> float:
        """Calculate current portfolio value in simulation."""
        sim_query = select(SimulationSession).where(SimulationSession.id == session_id)
        result = await session.execute(sim_query)
        sim_session = result.scalar_one()
        
        if not hasattr(sim_session, 'metadata') or not sim_session.metadata:
            return 0.0
        
        holdings = sim_session.metadata.get("holdings", {})
        total_value = 0.0
        
        for crypto_symbol, holding in holdings.items():
            if crypto_symbol in current_prices:
                current_price = current_prices[crypto_symbol].price
                total_value += holding["amount"] * current_price
        
        return total_value
    
    async def _generate_coaching_feedback(
        self,
        sim_session: SimulationSession,
        trade_type: str,
        crypto_symbol: str,
        price: float
    ) -> List[str]:
        """Generate AI coaching feedback based on trade."""
        feedback = []
        
        # Risk management feedback
        if trade_type == "BUY":
            position_size = (price * (sim_session.starting_balance_gems - sim_session.current_balance_gems)) / sim_session.starting_balance_gems * 100
            if position_size > 10:
                feedback.append(random.choice(self.ai_coaching_prompts["risk_management"][:2]))
            else:
                feedback.append(random.choice(self.ai_coaching_prompts["risk_management"][2:]))
        
        # Market psychology feedback
        if sim_session.total_trades > 5:
            return_pct = sim_session.total_return_percentage
            if return_pct > 10:
                feedback.append("🎉 Great performance! Remember to take profits and manage risk.")
            elif return_pct < -5:
                feedback.append("📚 Consider reviewing your strategy. Learning from losses is key!")
        
        # Trade execution feedback
        feedback.append(random.choice(self.ai_coaching_prompts["trade_execution"]))
        
        return feedback[:2]  # Return max 2 feedback messages
    
    async def get_simulation_dashboard(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Get simulation dashboard with performance metrics."""
        try:
            async with get_db_session() as session:
                # Get simulation session
                sim_query = select(SimulationSession).where(
                    and_(
                        SimulationSession.id == session_id,
                        SimulationSession.user_id == user_id
                    )
                )
                result = await session.execute(sim_query)
                sim_session = result.scalar_one_or_none()
                
                if not sim_session:
                    raise ValueError("Simulation session not found")
                
                # Get current prices for portfolio calculation
                current_prices = await market_simulator.get_current_prices()
                portfolio_value = await self._calculate_simulation_portfolio_value(
                    session, session_id, current_prices
                )
                
                # Calculate detailed metrics
                total_value = sim_session.current_balance_gems + portfolio_value
                holdings = sim_session.metadata.get("holdings", {}) if sim_session.metadata else {}
                
                # Calculate holdings with current values
                holdings_data = []
                for crypto_symbol, holding in holdings.items():
                    if crypto_symbol in current_prices:
                        current_price = current_prices[crypto_symbol].price
                        current_value = holding["amount"] * current_price
                        cost_basis = holding["amount"] * holding["average_cost"]
                        pnl = current_value - cost_basis
                        pnl_percentage = (pnl / cost_basis * 100) if cost_basis > 0 else 0
                        
                        holdings_data.append({
                            "crypto_symbol": crypto_symbol,
                            "amount": holding["amount"],
                            "average_cost": holding["average_cost"],
                            "current_price": current_price,
                            "current_value": current_value,
                            "unrealized_pnl": pnl,
                            "unrealized_pnl_percentage": pnl_percentage
                        })
                
                # Time remaining
                time_elapsed = datetime.utcnow() - sim_session.started_at
                time_remaining = timedelta(days=sim_session.duration_days) - time_elapsed
                
                return {
                    "session_id": sim_session.id,
                    "simulation_type": sim_session.simulation_type,
                    "status": sim_session.status,
                    "performance": {
                        "starting_balance": sim_session.starting_balance_gems,
                        "current_balance": sim_session.current_balance_gems,
                        "portfolio_value": portfolio_value,
                        "total_value": total_value,
                        "total_return": total_value - sim_session.starting_balance_gems,
                        "total_return_percentage": sim_session.total_return_percentage,
                        "total_trades": sim_session.total_trades,
                        "winning_trades": sim_session.winning_trades
                    },
                    "holdings": holdings_data,
                    "timing": {
                        "started_at": sim_session.started_at.isoformat(),
                        "duration_days": sim_session.duration_days,
                        "time_elapsed_hours": time_elapsed.total_seconds() / 3600,
                        "time_remaining_hours": max(0, time_remaining.total_seconds() / 3600)
                    },
                    "configuration": {
                        "allowed_cryptos": sim_session.allowed_cryptos,
                        "simulation_speed": sim_session.simulation_speed,
                        "educational_hints": sim_session.educational_hints,
                        "scenario_name": sim_session.scenario_name
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get simulation dashboard: {e}")
            raise
    
    async def complete_simulation(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Complete a simulation session and generate final report."""
        try:
            async with get_db_session() as session:
                sim_query = select(SimulationSession).where(
                    and_(
                        SimulationSession.id == session_id,
                        SimulationSession.user_id == user_id,
                        SimulationSession.status == "ACTIVE"
                    )
                )
                result = await session.execute(sim_query)
                sim_session = result.scalar_one_or_none()
                
                if not sim_session:
                    raise ValueError("Active simulation session not found")
                
                # Mark as completed
                sim_session.status = "COMPLETED"
                sim_session.ended_at = datetime.utcnow()
                
                # Calculate final metrics
                current_prices = await market_simulator.get_current_prices()
                portfolio_value = await self._calculate_simulation_portfolio_value(
                    session, session_id, current_prices
                )
                
                total_value = sim_session.current_balance_gems + portfolio_value
                final_return = (total_value - sim_session.starting_balance_gems) / sim_session.starting_balance_gems * 100
                
                # Generate final report
                final_report = {
                    "performance_summary": {
                        "starting_balance": sim_session.starting_balance_gems,
                        "ending_balance": total_value,
                        "total_return": total_value - sim_session.starting_balance_gems,
                        "total_return_percentage": final_return,
                        "total_trades": sim_session.total_trades,
                        "winning_trades": sim_session.winning_trades,
                        "win_rate": (sim_session.winning_trades / max(sim_session.total_trades, 1)) * 100
                    },
                    "lessons_learned": [
                        "Risk management is crucial for long-term success",
                        "Patience and discipline beat emotional trading",
                        "Always have a plan before entering trades",
                        "Small consistent wins are better than big risky bets"
                    ],
                    "areas_for_improvement": [],
                    "achievements_unlocked": []
                }
                
                # Add specific insights based on performance
                if final_return > 10:
                    final_report["achievements_unlocked"].append("Profitable Trader")
                if sim_session.total_trades > 20:
                    final_report["achievements_unlocked"].append("Active Trader")
                if final_return < -10:
                    final_report["areas_for_improvement"].append("Focus on risk management")
                
                sim_session.final_report = final_report
                
                # Award completion rewards
                base_reward = 250.0
                performance_bonus = max(0, final_return * 10)  # 10 GEMs per 1% return
                total_reward = base_reward + performance_bonus
                
                await virtual_economy_engine.update_wallet_balance(
                    session, user_id, "GEM_COINS", total_reward,
                    f"Simulation completion reward: {sim_session.simulation_type}"
                )
                
                await session.commit()
                
                logger.info(f"Completed simulation {session_id} for user {user_id}")
                
                return {
                    "session_id": session_id,
                    "final_report": final_report,
                    "gems_awarded": total_reward,
                    "completion_time": sim_session.ended_at.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to complete simulation: {e}")
            raise
    
    def get_available_challenges(self) -> List[Dict[str, Any]]:
        """Get available training challenges."""
        challenges = []
        for challenge in self.training_challenges:
            challenges.append({
                "challenge_id": challenge.challenge_id,
                "title": challenge.title,
                "description": challenge.description,
                "objective": challenge.objective,
                "difficulty": challenge.difficulty,
                "scenario": challenge.scenario.value,
                "duration_hours": challenge.duration_hours,
                "starting_balance": challenge.starting_balance,
                "target_return": challenge.target_return
            })
        
        return challenges
    
    async def start_challenge(self, user_id: str, challenge_id: str) -> Dict[str, Any]:
        """Start a specific training challenge."""
        try:
            # Find challenge
            challenge = next((c for c in self.training_challenges if c.challenge_id == challenge_id), None)
            if not challenge:
                raise ValueError("Challenge not found")
            
            # Create simulation session with challenge parameters
            config = {
                "starting_balance": challenge.starting_balance,
                "scenario_name": challenge.scenario.value,
                "duration_days": challenge.duration_hours // 24,
                "educational_hints": True,
                "allowed_cryptos": ["BTC", "ETH", "ADA", "SOL", "DOT", "LINK", "AVAX"]
            }
            
            session_result = await self.create_simulation_session(
                user_id, SimulationType.CHALLENGE_MODE, config
            )
            
            return {
                **session_result,
                "challenge": {
                    "challenge_id": challenge.challenge_id,
                    "title": challenge.title,
                    "objective": challenge.objective,
                    "target_return": challenge.target_return,
                    "difficulty": challenge.difficulty
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to start challenge: {e}")
            raise


# Global instance
simulation_trainer = SimulationTrainer()