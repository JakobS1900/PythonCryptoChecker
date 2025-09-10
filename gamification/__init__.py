"""
Gamification system for crypto platform.
Virtual currency, rewards, and collectible items system.
"""

from .models import (
    VirtualWallet, VirtualCryptoHolding, CollectibleItem, UserInventory,
    VirtualTransaction, RewardBundle, VirtualEconomyConstants,
    CurrencyType, ItemRarity, ItemType, RewardType
)

from .virtual_economy import VirtualEconomyEngine
from .item_generator import CryptoItemGenerator, initialize_collectible_items

__all__ = [
    # Models
    "VirtualWallet",
    "VirtualCryptoHolding", 
    "CollectibleItem",
    "UserInventory",
    "VirtualTransaction",
    "RewardBundle",
    "VirtualEconomyConstants",
    
    # Enums
    "CurrencyType",
    "ItemRarity", 
    "ItemType",
    "RewardType",
    
    # Core classes
    "VirtualEconomyEngine",
    "CryptoItemGenerator",
    
    # Utility functions
    "initialize_collectible_items"
]