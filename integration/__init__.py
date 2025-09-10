"""
Integration System - Bridges crypto trading with mini-games for enhanced rewards.
"""

from .crypto_minigame_bridge import (
    CryptoMiniGameBridge,
    crypto_minigame_bridge,
    RewardMultiplierType,
    CryptoMiniGameBonus,
    CryptoGameIntegration
)
from .integration_api import router as integration_router

__all__ = [
    "CryptoMiniGameBridge",
    "crypto_minigame_bridge",
    "RewardMultiplierType",
    "CryptoMiniGameBonus",
    "CryptoGameIntegration",
    "integration_router"
]