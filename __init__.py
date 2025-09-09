"""
Crypto Analytics Platform - Professional cryptocurrency analytics and trading platform.

This package provides a comprehensive suite of tools for cryptocurrency analysis,
real-time price tracking, portfolio management, and trading operations.

Main modules:
- main: Application entry point
- models: Data models and structures
- data_providers: API integrations and data fetching
- ui: User interface components
- utils: Utility functions
- config: Configuration settings

Author: Your Name
Version: 1.0.0
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__license__ = "MIT"

# Import main application class for easy access
from .main import CryptoAnalyticsPlatform

__all__ = ["CryptoAnalyticsPlatform"]