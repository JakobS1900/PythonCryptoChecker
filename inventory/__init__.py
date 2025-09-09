"""
Virtual inventory system for crypto gamification platform.
Item collection, management, and peer-to-peer trading.
"""

from .inventory_manager import InventoryManager
from .trading_system import TradingSystem, TradeOffer, TradeOfferItem, TradeStatus

__all__ = [
    # Core classes
    "InventoryManager",
    "TradingSystem",
    
    # Models
    "TradeOffer",
    "TradeOfferItem", 
    
    # Enums
    "TradeStatus"
]