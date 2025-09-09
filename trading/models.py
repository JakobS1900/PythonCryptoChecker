"""
Database models for the trading system.
Defines all tables and relationships for paper trading, portfolios, and transactions.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
import uuid

# Import the unified base and models
from database.unified_models import Base, User


class OrderType(PyEnum):
    """Order types for trading."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderSide(PyEnum):
    """Order sides for trading."""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(PyEnum):
    """Order status types."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class TransactionType(PyEnum):
    """Transaction types."""
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRADE_BUY = "TRADE_BUY"
    TRADE_SELL = "TRADE_SELL"
    FEE = "FEE"


# User model is imported from unified_models


class Portfolio(Base):
    """Portfolio table for managing virtual trading portfolios."""
    __tablename__ = "portfolios"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    initial_balance = Column(Float, nullable=False, default=100000.0)  # $100k virtual money
    current_balance = Column(Float, nullable=False, default=100000.0)
    base_currency = Column(String(10), default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Performance tracking
    total_invested = Column(Float, default=0.0)
    total_profit_loss = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio")
    transactions = relationship("Transaction", back_populates="portfolio")
    orders = relationship("Order", back_populates="portfolio")
    risk_policy = relationship("RiskPolicy", uselist=False, back_populates="portfolio")


class Holding(Base):
    """Holdings table for tracking cryptocurrency positions."""
    __tablename__ = "holdings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String, ForeignKey("portfolios.id"), nullable=False)
    coin_id = Column(String(50), nullable=False)  # e.g., "bitcoin"
    coin_symbol = Column(String(10), nullable=False)  # e.g., "BTC"
    quantity = Column(Float, nullable=False, default=0.0)
    average_cost = Column(Float, nullable=False, default=0.0)
    current_price = Column(Float, nullable=False, default=0.0)
    last_price_update = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")
    
    @property
    def market_value(self) -> float:
        """Calculate current market value of the holding."""
        return self.quantity * self.current_price
    
    @property
    def total_cost(self) -> float:
        """Calculate total cost basis of the holding."""
        return self.quantity * self.average_cost
    
    @property
    def profit_loss(self) -> float:
        """Calculate unrealized profit/loss."""
        return self.market_value - self.total_cost
    
    @property
    def profit_loss_percentage(self) -> float:
        """Calculate unrealized profit/loss percentage."""
        if self.total_cost == 0:
            return 0.0
        return (self.profit_loss / self.total_cost) * 100


class Transaction(Base):
    """Transaction table for recording all portfolio activities."""
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    portfolio_id = Column(String, ForeignKey("portfolios.id"), nullable=False)
    order_id = Column(String, ForeignKey("orders.id"), nullable=True)
    
    transaction_type = Column(Enum(TransactionType), nullable=False)
    coin_id = Column(String(50))  # null for deposits/withdrawals
    coin_symbol = Column(String(10))
    quantity = Column(Float)  # cryptocurrency amount
    price = Column(Float)  # price per unit
    amount = Column(Float, nullable=False)  # total amount (quantity * price or deposit/withdrawal amount)
    fee = Column(Float, default=0.0)
    
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    portfolio = relationship("Portfolio", back_populates="transactions")
    order = relationship("Order", back_populates="transactions")


class Order(Base):
    """Order table for managing buy/sell orders and risk management."""
    __tablename__ = "orders"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    portfolio_id = Column(String, ForeignKey("portfolios.id"), nullable=False)
    
    # Order details
    coin_id = Column(String(50), nullable=False)
    coin_symbol = Column(String(10), nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    order_side = Column(Enum(OrderSide), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float)  # null for market orders
    stop_price = Column(Float)  # for stop-loss/take-profit orders
    
    # Order status and execution
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    filled_quantity = Column(Float, default=0.0)
    filled_price = Column(Float)
    filled_at = Column(DateTime)
    
    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)  # for limit orders
    
    # Relationships
    user = relationship("User", back_populates="orders")
    portfolio = relationship("Portfolio", back_populates="orders")
    transactions = relationship("Transaction", back_populates="order")
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def remaining_quantity(self) -> float:
        """Get remaining quantity to be filled."""
        return self.quantity - self.filled_quantity
    
    @property
    def total_value(self) -> float:
        """Get total value of the order."""
        price = self.filled_price or self.price or 0.0
        return self.quantity * price


class RiskPolicy(Base):
    """Per-portfolio risk management policy."""
    __tablename__ = "risk_policies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String, ForeignKey("portfolios.id"), unique=True, nullable=False)

    # Limits
    max_position_pct = Column(Float, default=0.30)       # Max per-coin exposure as % of portfolio value
    max_open_positions = Column(Integer, default=10)     # Max number of distinct positions
    max_trade_value_pct = Column(Float, default=0.20)    # Max single trade value as % of portfolio value

    # Default protective orders for new long positions
    default_sl_pct = Column(Float, default=0.05)         # e.g., 5% below entry
    default_tp_pct = Column(Float, default=0.10)         # e.g., 10% above entry

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    portfolio = relationship("Portfolio", back_populates="risk_policy")


class TradingStrategy(Base):
    """Trading strategy table for backtesting and automated trading."""
    __tablename__ = "trading_strategies"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Strategy configuration (stored as JSON)
    config = Column(Text)  # JSON string with strategy parameters
    
    # Performance metrics
    total_returns = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    
    # Metadata
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")


class BacktestResult(Base):
    """Backtest result table for storing strategy backtesting results."""
    __tablename__ = "backtest_results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id = Column(String, ForeignKey("trading_strategies.id"), nullable=False)
    
    # Backtest parameters
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Float, nullable=False)
    
    # Results
    final_capital = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)
    total_trades = Column(Integer, nullable=False)
    winning_trades = Column(Integer, nullable=False)
    losing_trades = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)
    
    # Risk metrics
    max_drawdown = Column(Float, nullable=False)
    sharpe_ratio = Column(Float)
    volatility = Column(Float)
    
    # Detailed results (stored as JSON)
    trades_data = Column(Text)  # JSON string with all trade details
    equity_curve = Column(Text)  # JSON string with equity curve data
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    strategy = relationship("TradingStrategy")


class OcoGroup(Base):
    """One-Cancels-Other group for protective orders."""
    __tablename__ = "oco_groups"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)


class OcoLink(Base):
    """Links orders to an OCO group."""
    __tablename__ = "oco_links"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(String, ForeignKey("oco_groups.id"), nullable=False)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
