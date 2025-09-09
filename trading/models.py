"""
Trading models - now imports from unified database models.
"""

# Import all trading models from the unified models
from database.unified_models import (
    Base, User, Portfolio, Holding, Transaction, Order, 
    RiskPolicy, TradingStrategy, BacktestResult, OCOGroup, OCOLink,
    OrderType, OrderSide, OrderStatus, TransactionType
)

# Backward compatibility aliases
OcoGroup = OCOGroup
OcoLink = OCOLink

# Export for backward compatibility
__all__ = [
    "Base", "User", "Portfolio", "Holding", "Transaction", "Order",
    "RiskPolicy", "TradingStrategy", "BacktestResult", "OCOGroup", "OCOLink",
    "OcoGroup", "OcoLink",  # Backward compatibility
    "OrderType", "OrderSide", "OrderStatus", "TransactionType"
]