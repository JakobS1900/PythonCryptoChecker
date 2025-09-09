"""
Main application module for Crypto Analytics Platform.
Entry point and main application logic.
"""
import sys
import time
import os
from typing import Optional

# Setup console encoding for Windows Unicode support
if os.name == 'nt':
    try:
        # Enable UTF-8 encoding for Windows console
        os.system('chcp 65001 > nul')
    except Exception:
        pass

# Import check for requests library
try:
    import requests
except ImportError:
    print("Error: 'requests' library not found. Please install it by running:")
    print("    pip install requests")
    print("Then rerun this script.")
    sys.exit(1)

from models import ApplicationState, UserSession
from data_providers import DataManager
from ui import UserInterface, SetupInterface
from utils import detect_platform, clear_screen, setup_console_encoding
from config import REFRESH_RATE, COINS_PER_PAGE


class CryptoAnalyticsPlatform:
    """Main application class for Crypto Analytics Platform."""
    
    def __init__(self):
        self.app_state = ApplicationState()
        self.data_manager = DataManager()
        self.ui: Optional[UserInterface] = None
    
    def initialize(self) -> None:
        """Initialize the application with first-run setup if needed."""
        # Setup console encoding for better Unicode support
        setup_console_encoding()
        
        # Detect or prompt for platform
        platform_type = detect_platform()
        if platform_type == 'other':
            platform_type = SetupInterface.get_platform_selection()
        
        # Get currency selection
        user_currency = SetupInterface.get_currency_selection()
        
        # Create user session
        self.app_state.user_session = UserSession(
            platform_type=platform_type,
            user_currency=user_currency,
            first_run=False
        )
        
        # Initialize UI with dependencies
        self.ui = UserInterface(self.data_manager, self.app_state)
    
    def refresh_coins_data(self) -> None:
        """Refresh the coins data if needed."""
        current_time = time.time()
        
        if (current_time - self.app_state.last_update >= REFRESH_RATE) or not self.app_state.coins_list:
            coins, active_api = self.data_manager.get_top_coins(
                user_currency=self.app_state.user_session.user_currency,
                limit=100
            )
            
            if coins:
                self.app_state.update_coins_list(coins, active_api)
            elif not self.app_state.coins_list:
                # No cached data and API failed
                self.ui.show_error_message("Unable to fetch cryptocurrency data. Please check your internet connection.")
                sys.exit(1)
            else:
                # Use cached data with warning
                print("⚠️ Warning: API unavailable. Using cached data.")
    
    def handle_main_menu_input(self, choice: str, current_coins: list) -> tuple[bool, list, int]:
        """
        Handle main menu input and return (should_continue, updated_coins, updated_page).
        Returns False for should_continue if user wants to quit.
        """
        should_continue = True
        updated_coins = current_coins
        updated_page = self.app_state.current_page
        
        if choice == 'n':  # Next page
            total_pages = (len(current_coins) + COINS_PER_PAGE - 1) // COINS_PER_PAGE
            if self.app_state.current_page < total_pages - 1:
                updated_page = self.app_state.current_page + 1
        
        elif choice == 'p':  # Previous page
            if self.app_state.current_page > 0:
                updated_page = self.app_state.current_page - 1
        
        elif choice == 's':  # Search
            search_term = self.ui.get_search_query()
            results = self.app_state.search_coins(search_term)
            if results:
                updated_coins = results
                updated_page = 0
            else:
                self.ui.show_no_results_message()
        
        elif choice == 'a':  # Switch API
            self.ui.display_api_switch_menu()
            # Force refresh after API switch
            self.app_state.last_update = 0
            self.refresh_coins_data()
            updated_coins = self.app_state.coins_list[:]
            updated_page = 0
        
        elif choice == 'q':  # Quit
            self.ui.show_exit_message()
            should_continue = False
        
        else:
            # Try to parse as coin selection number
            try:
                choice_num = int(choice)
                coin = self.app_state.get_coin_by_index(self.app_state.current_page, choice_num)
                
                if coin and 1 <= choice_num <= COINS_PER_PAGE:
                    self.ui.display_conversion_interface(coin)
                    # Reset to full list after coin interaction
                    updated_coins = self.app_state.coins_list[:]
                    updated_page = 0
                else:
                    self.ui.show_invalid_selection()
            
            except ValueError:
                self.ui.show_error_message("Please enter a valid number or command.")
        
        return should_continue, updated_coins, updated_page
    
    def run_main_session(self) -> None:
        """Run the main application session."""
        # Initial data load
        self.refresh_coins_data()
        
        current_coins = self.app_state.coins_list[:]
        self.app_state.current_page = 0
        
        while True:
            # Refresh data if needed
            self.refresh_coins_data()
            
            # Update current coins if we're showing the full list
            if current_coins is self.app_state.coins_list or len(current_coins) == len(self.app_state.coins_list):
                current_coins = self.app_state.coins_list[:]
            
            # Clear screen and display interface
            clear_screen()
            self.ui.display_header()
            self.ui.display_coins_page(self.app_state.current_page, current_coins)
            self.ui.show_refresh_timestamps(self.app_state.last_update, REFRESH_RATE)
            
            # Get user input and handle it
            choice = self.ui.get_main_menu_choice()
            should_continue, updated_coins, updated_page = self.handle_main_menu_input(choice, current_coins)
            
            if not should_continue:
                break
            
            current_coins = updated_coins
            self.app_state.current_page = updated_page
    
    def run(self) -> None:
        """Main application entry point."""
        try:
            self.initialize()
            while True:
                self.run_main_session()
                break  # Exit after main session (user quit)
        
        except KeyboardInterrupt:
            print(f"\n💼 Thank you for using Crypto Analytics Platform. Goodbye!")
        
        except Exception as e:
            print(f"\n⚠️ An unexpected error occurred: {str(e)}")
            print("Please report this issue on our GitHub repository.")
            sys.exit(1)


def main():
    """Application entry point."""
    app = CryptoAnalyticsPlatform()
    app.run()


if __name__ == "__main__":
    main()