"""
Utility functions for Crypto Analytics Platform.
Contains helper functions for formatting, platform detection, and calculations.
"""
import os
import sys
import time
from typing import List
from models import PricePoint


def setup_console_encoding() -> None:
    """Setup console encoding for Windows Unicode support."""
    if os.name == 'nt':
        try:
            # Try to set UTF-8 encoding for Windows console
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
        except Exception:
            # If that fails, we'll fall back to ASCII-safe characters
            pass


def detect_platform() -> str:
    """Detect if running on Windows, Android (Pydroid), or other platform."""
    try:
        if 'pydroid' in sys.executable.lower():
            return 'android'
    except Exception:
        pass
    
    if os.name == 'nt':
        return 'windows'
    
    return 'other'


def clear_screen() -> None:
    """Clear terminal screen cross-platform."""
    os.system('cls' if os.name == 'nt' else 'clear')


def format_price(price: float) -> str:
    """
    Format a float price with thousands separators and exactly two decimal places.
    
    Examples:
        103159.0       → "103,159.00"
        0.5            → "0.50"
        104054.9144115 → "104,054.91"
    """
    return f"{price:,.2f}"


def format_crypto_amount(amount: float) -> str:
    """Format cryptocurrency amount with appropriate decimal places."""
    formatted = f"{amount:,.8f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


def any_key() -> None:
    """Universal 'press any key' implementation."""
    print("\nPress Enter to continue…")
    input()


def animated_loading(duration: float = 1.0, width: int = 10) -> None:
    """Simple animated loading bar."""
    steps = int(duration * 10)  # 10 steps per second
    for i in range(steps + 1):
        progress = i / steps
        filled = int(progress * width)
        bar = '■' * filled + ' ' * (width - filled)
        sys.stdout.write(f'\r[{bar}]')
        sys.stdout.flush()
        time.sleep(duration / steps)
    print()


def calculate_price_change(prices: List[PricePoint]) -> float:
    """Calculate percentage price change between first and last data points."""
    if len(prices) < 2:
        return 0.0
    
    start_price = prices[0].price
    end_price = prices[-1].price
    
    if start_price == 0:
        return 0.0
    
    return ((end_price - start_price) / start_price) * 100


def get_trend_indicators(change: float) -> tuple[str, str]:
    """Get color and symbol for price trend display."""
    import os
    from config import COLORS
    
    # Use safe characters for Windows
    if os.name == 'nt':
        if change >= 0:
            return COLORS['green'], '^'
        else:
            return COLORS['red'], 'v'
    else:
        if change >= 0:
            return COLORS['green'], '▲'
        else:
            return COLORS['red'], '▼'


def validate_positive_number(value_str: str) -> tuple[bool, float]:
    """
    Validate and parse a positive number from string input.
    
    Returns:
        (is_valid, parsed_value)
    """
    try:
        value = float(value_str)
        return value > 0, value
    except ValueError:
        return False, 0.0


def get_pagination_info(current_page: int, total_items: int, items_per_page: int) -> dict:
    """Get pagination information for display."""
    total_pages = (total_items + items_per_page - 1) // items_per_page
    start_idx = current_page * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    
    return {
        'current_page': current_page + 1,  # 1-based for display
        'total_pages': total_pages,
        'start_index': start_idx,
        'end_index': end_idx,
        'has_next': current_page < total_pages - 1,
        'has_prev': current_page > 0
    }


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero."""
    try:
        return numerator / denominator if denominator != 0 else default
    except (TypeError, ZeroDivisionError):
        return default


def format_timestamp(timestamp: int, format_str: str = '%H:%M:%S') -> str:
    """Format timestamp to readable string."""
    from datetime import datetime
    return datetime.fromtimestamp(timestamp / 1000).strftime(format_str)


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to maximum length with optional suffix."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def get_time_ago_string(timestamp: int) -> str:
    """Get human-readable time ago string from timestamp."""
    now = time.time()
    diff = now - (timestamp / 1000)
    
    if diff < 60:
        return "just now"
    elif diff < 3600:
        minutes = int(diff / 60)
        return f"{minutes}m ago"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours}h ago"
    else:
        days = int(diff / 86400)
        return f"{days}d ago"