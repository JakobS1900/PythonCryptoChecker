"""
User Interface module for Crypto Analytics Platform.
Contains all terminal UI functions and display logic.
"""
import os
from typing import List, Optional
from datetime import datetime

from models import CoinData, ApplicationState, UserSession
from config import COLORS, SUPPORTED_CURRENCIES, COINS_PER_PAGE, EXCHANGE_PAIRS
from utils import (
    clear_screen, any_key, format_price, format_crypto_amount, 
    get_trend_indicators, get_pagination_info, animated_loading,
    validate_positive_number, truncate_string, setup_console_encoding
)
from data_providers import DataManager, FeeProvider


# Windows-safe character alternatives
SAFE_CHARS = {
    'windows': {
        'top_left': '+',
        'top_right': '+',
        'bottom_left': '+',
        'bottom_right': '+',
        'horizontal': '-',
        'vertical': '|',
        'header_line': '=',
        'chart_emoji': '$',
        'book_emoji': '#',
        'warning_emoji': '!',
        'check_emoji': '*',
        'arrow_up': '^',
        'arrow_down': 'v'
    },
    'other': {
        'top_left': '┌',
        'top_right': '┐',
        'bottom_left': '└',
        'bottom_right': '┘',
        'horizontal': '─',
        'vertical': '│',
        'header_line': '━',
        'chart_emoji': '📊',
        'book_emoji': '📖',
        'warning_emoji': '⚠️',
        'check_emoji': '✅',
        'arrow_up': '▲',
        'arrow_down': '▼'
    }
}


def get_safe_chars():
    """Get platform-appropriate characters for UI elements."""
    return SAFE_CHARS['windows' if os.name == 'nt' else 'other']


class UserInterface:
    """Handles all user interface operations."""
    
    def __init__(self, data_manager: DataManager, app_state: ApplicationState):
        self.data_manager = data_manager
        self.app_state = app_state
    
    def display_header(self) -> None:
        """Display application header with branding."""
        uc = self.app_state.user_session.user_currency.upper()
        platform = self.app_state.user_session.platform_type
        
        chars = get_safe_chars()
        if platform == 'android':
            print(f"\n{COLORS['yellow']}{chars['chart_emoji']} CRYPTO ANALYTICS PLATFORM (Top 100, {uc}){COLORS['reset']}")
        else:
            print(f"\n{COLORS['yellow']}{chars['chart_emoji']} CRYPTO ANALYTICS PLATFORM (Top 100 Coins, {uc}){COLORS['reset']}")
        
        # Display active API
        api_display = self.app_state.active_api if self.app_state.active_api else "N/A"
        print(f"{COLORS['blue']}API SELECTED = \"{api_display}\"{COLORS['reset']}")
        chars = get_safe_chars()
        print(f"{COLORS['green']}{chars['header_line']}{chars['header_line'] * 40}{COLORS['reset']}")
    
    def display_coins_page(self, page: int, coins: List[CoinData]) -> None:
        """Display a paginated list of coins."""
        pagination = get_pagination_info(page, len(coins), COINS_PER_PAGE)
        start_idx = pagination['start_index']
        end_idx = pagination['end_index']
        page_coins = coins[start_idx:end_idx]
        
        chars = get_safe_chars()
        print(f"\n{COLORS['yellow']}{chars['book_emoji']} Page {pagination['current_page']}/{pagination['total_pages']}{COLORS['reset']}")
        print(f"{COLORS['green']}{chars['top_left']}{chars['horizontal'] * 40}{chars['top_right']}{COLORS['reset']}")
        
        for i, coin in enumerate(page_coins):
            num = start_idx + i + 1
            trend_color, trend_symbol = get_trend_indicators(coin.price_change_24h)
            price_display = format_price(coin.price)
            name_display = truncate_string(coin.name, 20)
            
            print(f"{num:2}. {coin.emoji} {name_display:<20} {price_display:>12} "
                  f"{trend_color}{trend_symbol}{COLORS['reset']}")
        
        chars = get_safe_chars()
        print(f"{COLORS['green']}{chars['bottom_left']}{chars['horizontal'] * 40}{chars['bottom_right']}{COLORS['reset']}")
        print(f"\n{COLORS['cyan']}N: Next Page  P: Prev Page  S: Search  Q: Quit{COLORS['reset']}")
    
    def display_coin_details(self, coin: CoinData) -> None:
        """Display detailed information for a single coin."""
        clear_screen()
        print(f"\n{COLORS['yellow']}┌───────────────────────────────────┐")
        print(f"│   {coin.emoji} {coin.name} ({coin.symbol})   │")
        print(f"└───────────────────────────────────┘{COLORS['reset']}")
        
        trend_color, trend_symbol = get_trend_indicators(coin.price_change_24h)
        user_currency = self.app_state.user_session.user_currency.upper()
        price_display = format_price(coin.price)
        
        print(f"\nCurrent Price: {COLORS['white']}{price_display} {user_currency}{COLORS['reset']}")
        print(f"24h Change:    {trend_color}{trend_symbol} {abs(coin.price_change_24h):.2f}%{COLORS['reset']}")
        
        # Display market cap and volume if available
        if coin.market_cap:
            market_cap_display = format_price(coin.market_cap)
            print(f"Market Cap:    {COLORS['white']}{market_cap_display} {user_currency}{COLORS['reset']}")
        
        if coin.volume_24h:
            volume_display = format_price(coin.volume_24h)
            print(f"24h Volume:    {COLORS['white']}{volume_display} {user_currency}{COLORS['reset']}")
        
        self._display_historical_trends(coin)
    
    def _display_historical_trends(self, coin: CoinData) -> None:
        """Display historical price trends for a coin."""
        print(f"\n{COLORS['blue']}Historical Trends ({self.data_manager.historical_primary_api} primary):{COLORS['reset']}")
        
        time_frames = [
            ('24h', 'Past 24h', 1),
            ('7d', 'Past 7d', 7),
            ('1m', 'Past 1m', 30),
            ('3m', 'Past 3m', 90),
            ('1y', 'Past 1y', 365),
            ('max', 'All Time', 'max')
        ]
        
        user_currency = self.app_state.user_session.user_currency
        
        for timeframe, label, days in time_frames:
            prices = self.data_manager.get_historical_data(coin.id, str(days), user_currency)
            if not prices:
                continue
            
            from utils import calculate_price_change
            price_change = calculate_price_change(prices)
            trend_color, trend_symbol = get_trend_indicators(price_change)
            
            start_price = prices[0].price
            end_price = prices[-1].price
            start_display = format_price(start_price)
            end_display = format_price(end_price)
            
            print(f"{label}: {trend_color}{trend_symbol} {abs(price_change):.2f}%{COLORS['reset']} "
                  f"(Start: {start_display} → End: {end_display})")
    
    def display_conversion_interface(self, coin: CoinData) -> None:
        """Display currency conversion interface."""
        user_currency = self.app_state.user_session.user_currency.upper()
        
        while True:
            self.display_coin_details(coin)
            print(f"\n{COLORS['cyan']}Options:")
            print(f"1. Convert {user_currency} to {coin.symbol}")
            print(f"2. View Network/Exchange Fees")
            print(f"3. Go Back{COLORS['reset']}")
            
            choice = input(f"\n{COLORS['blue']}Select option: {COLORS['reset']}").strip()
            
            if choice == '3':
                break
            elif choice == '1':
                self._handle_currency_conversion(coin)
            elif choice == '2':
                self._display_fee_information(coin)
            else:
                print(f"{COLORS['red']}Invalid choice!{COLORS['reset']}")
                any_key()
    
    def _handle_currency_conversion(self, coin: CoinData) -> None:
        """Handle currency conversion input and display."""
        user_currency = self.app_state.user_session.user_currency.upper()
        
        prompt = f"\n{COLORS['blue']}Amount in {user_currency}: {COLORS['reset']}"
        amount_input = input(prompt)
        
        is_valid, amount_fiat = validate_positive_number(amount_input)
        if not is_valid:
            print(f"{COLORS['red']}⚠️ Please enter a valid positive amount.{COLORS['reset']}")
            any_key()
            return
        
        print(f"\n{COLORS['yellow']}Converting to {coin.symbol}…{COLORS['reset']}")
        animated_loading()
        
        crypto_amount = amount_fiat / coin.price
        crypto_display = format_crypto_amount(crypto_amount)
        
        print(f"\n{COLORS['green']}{coin.emoji} {crypto_display} {coin.symbol}{COLORS['reset']}")
        print(f"{COLORS['cyan']}⏱️ {datetime.now().strftime('%H:%M:%S')}{COLORS['reset']}")
        print(f"{COLORS['blue']}{user_currency} {format_price(amount_fiat)} → "
              f"{coin.emoji} {crypto_display} {coin.symbol}{COLORS['reset']}")
        any_key()
    
    def _display_fee_information(self, coin: CoinData) -> None:
        """Display fee information for a coin."""
        clear_screen()
        user_currency = self.app_state.user_session.user_currency.upper()
        print(f"\n{COLORS['yellow']}┌───────────────────────────────────┐")
        print(f"│   {coin.emoji} {coin.name} ({coin.symbol}) Fees   │")
        print(f"└───────────────────────────────────┘{COLORS['reset']}")
        
        # Find available exchange pairs
        direct_pairs = []
        for pair_key in EXCHANGE_PAIRS:
            base_id, quote_id = pair_key.split('_')
            if base_id == coin.id:
                base_coin = next((c for c in self.app_state.coins_list if c.id == base_id), None)
                quote_coin = next((c for c in self.app_state.coins_list if c.id == quote_id), None)
                if base_coin and quote_coin:
                    direct_pairs.append((pair_key, base_coin, quote_coin))
        
        if not direct_pairs:
            print(f"\n{COLORS['yellow']}No direct exchange pairs found for {coin.symbol}.{COLORS['reset']}")
            any_key()
            return
        
        while True:
            print(f"\n{COLORS['blue']}Select an exchange pair to view fees:{COLORS['reset']}")
            for idx, (_, base_coin, quote_coin) in enumerate(direct_pairs, start=1):
                print(f"  {idx}. {base_coin.symbol} → {quote_coin.symbol}")
            print(f"  3. Go Back")
            
            choice = input(f"\n{COLORS['cyan']}Choice (1-{len(direct_pairs)}, 3): {COLORS['reset']}").strip()
            
            if choice == '3':
                break
            
            try:
                sel = int(choice)
                if 1 <= sel <= len(direct_pairs):
                    pair_key, base_coin, quote_coin = direct_pairs[sel - 1]
                    self._show_exchange_fee_details(pair_key, base_coin, quote_coin, user_currency)
                else:
                    print(f"{COLORS['red']}Invalid selection!{COLORS['reset']}")
                    any_key()
            except ValueError:
                print(f"{COLORS['red']}Enter a number between 1 and {len(direct_pairs)}, or 3 to go back.{COLORS['reset']}")
                any_key()
    
    def _show_exchange_fee_details(self, pair_key: str, base_coin: CoinData, quote_coin: CoinData, user_currency: str) -> None:
        """Show detailed fee information for an exchange pair."""
        fee_data = FeeProvider.get_exchange_fees(pair_key)
        if not fee_data:
            print(f"{COLORS['red']}Error: could not fetch fees for that pair.{COLORS['reset']}")
            any_key()
            return
        
        fixed_fee_crypto = fee_data.fee_fixed
        fixed_fee_fiat = fixed_fee_crypto * quote_coin.price
        min_amount_crypto = fee_data.min_amount
        min_amount_fiat = min_amount_crypto * base_coin.price
        
        clear_screen()
        print(f"\n{COLORS['yellow']}┌───────────────────────────────────┐")
        print(f"│   {base_coin.emoji} {base_coin.symbol} → {quote_coin.emoji} {quote_coin.symbol}   │")
        print(f"└───────────────────────────────────┘{COLORS['reset']}\n")
        
        print(f"{COLORS['cyan']}Variable fee:{COLORS['reset']} {fee_data.fee_percent:.2f}%")
        print(f"{COLORS['cyan']}Fixed fee:   {COLORS['reset']}"
              f"{fixed_fee_crypto:.6f} {quote_coin.symbol} "
              f"(≈ {user_currency} {format_price(fixed_fee_fiat)})")
        print(f"{COLORS['cyan']}Min amount:  {COLORS['reset']}"
              f"{min_amount_crypto:.6f} {base_coin.symbol} "
              f"(≈ {user_currency} {format_price(min_amount_fiat)})")
        any_key()
    
    def display_api_switch_menu(self) -> None:
        """Display API switching menu."""
        clear_screen()
        print(f"{COLORS['yellow']}┌──────────────────────────────┐")
        print("│   SWITCH PRIMARY API         │")
        print(f"└──────────────────────────────┘{COLORS['reset']}")
        print("\nCurrent primary API:", self.data_manager.coinlist_primary_api)
        print("1. CoinGecko")
        print("2. CoinCap")
        print("Press Enter to keep current.\n")
        
        choice = input(f"{COLORS['blue']}Choice (1-2 or Enter): {COLORS['reset']}").strip()
        
        if choice == '1':
            self.data_manager.set_primary_api("CoinGecko")
        elif choice == '2':
            self.data_manager.set_primary_api("CoinCap")
        
        print(f"\nNew primary API: {self.data_manager.coinlist_primary_api}")
        any_key()
    
    def get_search_query(self) -> str:
        """Get search query from user."""
        return input(f"{COLORS['blue']}Search coin: {COLORS['reset']}").strip()
    
    def show_no_results_message(self) -> None:
        """Display no search results message."""
        print(f"{COLORS['red']}No coins found!{COLORS['reset']}")
        any_key()
    
    def show_error_message(self, message: str) -> None:
        """Display error message."""
        print(f"{COLORS['red']}⚠️ {message}{COLORS['reset']}")
        any_key()
    
    def show_invalid_selection(self) -> None:
        """Display invalid selection message."""
        print(f"{COLORS['red']}⚠️ Invalid selection!{COLORS['reset']}")
        any_key()
    
    def get_main_menu_choice(self) -> str:
        """Get main menu choice from user."""
        return input(f"\n{COLORS['cyan']}Select option (1-{COINS_PER_PAGE}, N/P/S/Q/A): {COLORS['reset']}").strip().lower()
    
    def show_exit_message(self) -> None:
        """Display exit message."""
        print(f"\n{COLORS['blue']}💼 Thank you for using Crypto Analytics Platform. Happy investing!{COLORS['reset']}")
        any_key()
    
    def show_refresh_timestamps(self, last_update: int, refresh_rate: int) -> None:
        """Display refresh timestamps."""
        last_ts = datetime.fromtimestamp(last_update).strftime('%H:%M:%S')
        next_ts = datetime.fromtimestamp(last_update + refresh_rate).strftime('%H:%M:%S')
        print(f"\n{COLORS['blue']}Last refresh: {last_ts} | Next refresh: {next_ts}{COLORS['reset']}")
        print(f"{COLORS['blue']}A: Switch API{COLORS['reset']}")


class SetupInterface:
    """Handles first-run setup interface."""
    
    @staticmethod
    def get_platform_selection() -> str:
        """Get platform selection from user."""
        clear_screen()
        chars = get_safe_chars()
        print(f"{COLORS['yellow']}{chars['top_left']}{chars['horizontal'] * 30}{chars['top_right']}")
        print(f"{chars['vertical']}   PLATFORM DETECTION         {chars['vertical']}")
        print(f"{chars['bottom_left']}{chars['horizontal'] * 30}{chars['bottom_right']}{COLORS['reset']}")
        print("\n1. Windows")
        print("2. Android (Pydroid)")
        print("3. Other")
        
        while True:
            choice = input("\nSelect your platform: ").strip()
            if choice == '1':
                return 'windows'
            elif choice == '2':
                return 'android'
            elif choice == '3':
                return 'other'
            print(f"{COLORS['red']}Invalid choice!{COLORS['reset']}")
    
    @staticmethod
    def get_currency_selection() -> str:
        """Get currency selection from user."""
        clear_screen()
        chars = get_safe_chars()
        print(f"{COLORS['yellow']}{chars['top_left']}{chars['horizontal'] * 46}{chars['top_right']}")
        print(f"{chars['vertical']}   SELECT YOUR LOCAL CURRENCY (FIRST RUN)   {chars['vertical']}")
        print(f"{chars['bottom_left']}{chars['horizontal'] * 46}{chars['bottom_right']}{COLORS['reset']}")
        print("\nBelow is the list of 3-letter fiat codes supported by CoinGecko.")
        print("Type one of those codes and press Enter, or press Enter alone to default to USD.\n")
        
        # Display currencies in rows of 8
        per_row = 8
        for i in range(0, len(SUPPORTED_CURRENCIES), per_row):
            chunk = SUPPORTED_CURRENCIES[i:i + per_row]
            print("  " + "   ".join(chunk))
        print()
        
        choice = input(f"{COLORS['blue']}Currency: {COLORS['reset']}").strip().upper()
        if choice == '' or choice not in SUPPORTED_CURRENCIES:
            return 'usd'
        else:
            return choice.lower()