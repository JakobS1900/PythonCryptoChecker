"""
Comprehensive Playwright Test Suite for CryptoChecker V3
Tests ALL features with special focus on:
- Roulette game (100K bet issue)
- Trading features (user reported issues)
- Authentication & JWT
- All other platform features
"""

import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright, Page, BrowserContext
from pathlib import Path

class CryptoCheckerTester:
    """Comprehensive test suite for CryptoChecker V3 platform"""

    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.username = "Emu"
        self.password = "EmuEmu"
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "errors": [],
            "screenshots": []
        }
        self.screenshots_dir = Path("test_screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)

    async def take_screenshot(self, page: Page, name: str, description: str):
        """Take screenshot and log it"""
        screenshot_path = self.screenshots_dir / f"{name}_{datetime.now().strftime('%H%M%S')}.png"
        await page.screenshot(path=str(screenshot_path))
        self.test_results["screenshots"].append({
            "name": name,
            "description": description,
            "path": str(screenshot_path)
        })
        print(f"📸 Screenshot: {name}")

    def log_test(self, category: str, feature: str, status: str, details: str = ""):
        """Log test result"""
        result = {
            "category": category,
            "feature": feature,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results["tests"].append(result)

        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{icon} {category} > {feature}: {status}")
        if details:
            print(f"   {details}")

    def log_error(self, category: str, error: str, details: dict = None):
        """Log error with details"""
        error_entry = {
            "category": category,
            "error": error,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        self.test_results["errors"].append(error_entry)
        print(f"❌ ERROR in {category}: {error}")
        if details:
            print(f"   Details: {json.dumps(details, indent=2)}")

    async def capture_console_logs(self, page: Page, category: str):
        """Capture console logs and errors"""
        console_logs = []

        page.on("console", lambda msg: console_logs.append({
            "type": msg.type,
            "text": msg.text,
            "location": msg.location
        }))

        page.on("pageerror", lambda error: self.log_error(
            category,
            f"Page Error: {error}",
            {"error": str(error)}
        ))

        return console_logs

    async def capture_network_errors(self, page: Page, category: str):
        """Capture failed network requests"""
        network_errors = []

        page.on("requestfailed", lambda request: network_errors.append({
            "url": request.url,
            "method": request.method,
            "failure": request.failure
        }))

        return network_errors

    async def test_login_authentication(self, page: Page):
        """Test 1: Login & Authentication"""
        print("\n" + "="*60)
        print("TEST 1: LOGIN & AUTHENTICATION")
        print("="*60)

        console_logs = await self.capture_console_logs(page, "Authentication")
        network_errors = await self.capture_network_errors(page, "Authentication")

        try:
            # Navigate to login page
            await page.goto(f"{self.base_url}/login")
            await page.wait_for_load_state("networkidle")
            await self.take_screenshot(page, "login_page", "Login page loaded")

            # Fill credentials
            await page.fill('input[name="username"]', self.username)
            await page.fill('input[name="password"]', self.password)
            await self.take_screenshot(page, "login_filled", "Credentials entered")

            # Submit login
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)  # Wait for JWT processing

            # Check if logged in
            current_url = page.url
            if "/login" not in current_url:
                self.log_test("Authentication", "Login", "PASS", f"Redirected to {current_url}")
            else:
                self.log_test("Authentication", "Login", "FAIL", "Still on login page")
                await self.take_screenshot(page, "login_failed", "Login failed")
                return False

            # Check for JWT token in localStorage
            jwt_token = await page.evaluate("() => localStorage.getItem('access_token')")
            if jwt_token:
                self.log_test("Authentication", "JWT Token Storage", "PASS", f"Token length: {len(jwt_token)}")
            else:
                self.log_test("Authentication", "JWT Token Storage", "FAIL", "No JWT token found")

            # Check balance display
            await asyncio.sleep(1)
            balance_visible = await page.is_visible('.gem-balance, #gem-balance, [data-balance]')
            if balance_visible:
                balance_text = await page.text_content('.gem-balance, #gem-balance, [data-balance]')
                self.log_test("Authentication", "Balance Display", "PASS", f"Balance: {balance_text}")
            else:
                self.log_test("Authentication", "Balance Display", "WARN", "Balance element not visible")

            await self.take_screenshot(page, "login_success", "Login successful")

            # Check for console errors
            errors = [log for log in console_logs if log["type"] == "error"]
            if errors:
                self.log_error("Authentication", "Console Errors", {"errors": errors})

            # Check for network errors
            if network_errors:
                self.log_error("Authentication", "Network Errors", {"errors": network_errors})

            return True

        except Exception as e:
            self.log_error("Authentication", f"Exception: {str(e)}")
            await self.take_screenshot(page, "login_exception", "Exception during login")
            return False

    async def test_roulette_game(self, page: Page):
        """Test 2: Roulette Game (PRIORITY - 100K bet issue)"""
        print("\n" + "="*60)
        print("TEST 2: ROULETTE GAME (100K BET ISSUE)")
        print("="*60)

        console_logs = await self.capture_console_logs(page, "Roulette")
        network_errors = await self.capture_network_errors(page, "Roulette")

        try:
            # Navigate to gaming page
            await page.goto(f"{self.base_url}/gaming")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await self.take_screenshot(page, "roulette_initial", "Roulette game loaded")

            # Check if roulette is visible
            roulette_visible = await page.is_visible('.roulette-container, #roulette-game, .game-container')
            if roulette_visible:
                self.log_test("Roulette", "Game Interface", "PASS", "Roulette interface loaded")
            else:
                self.log_test("Roulette", "Game Interface", "FAIL", "Roulette interface not found")
                return

            # Get current balance
            balance_element = await page.query_selector('.gem-balance, #gem-balance, [data-balance]')
            initial_balance = "Unknown"
            if balance_element:
                initial_balance_text = await balance_element.text_content()
                initial_balance = initial_balance_text.strip()
                self.log_test("Roulette", "Initial Balance", "INFO", f"Balance: {initial_balance}")

            # Test 1: 100K GEM bet on RED
            print("\n--- Test 1: 100K GEM Bet on RED ---")
            await self.test_roulette_bet(page, "100000", "RED", "100k_red")

            # Wait between tests
            await asyncio.sleep(3)

            # Test 2: 50K GEM bet
            print("\n--- Test 2: 50K GEM Bet on BLACK ---")
            await self.test_roulette_bet(page, "50000", "BLACK", "50k_black")

            # Wait between tests
            await asyncio.sleep(3)

            # Test 3: MAX bet button
            print("\n--- Test 3: MAX Bet Button ---")
            max_button = await page.query_selector('button.max-bet, button[data-max], .bet-max, button:has-text("MAX")')
            if max_button:
                await max_button.click()
                await asyncio.sleep(1)

                # Get bet amount after clicking MAX
                bet_input = await page.query_selector('input[name="bet"], input.bet-amount, #bet-amount')
                if bet_input:
                    max_bet_value = await bet_input.input_value()
                    self.log_test("Roulette", "MAX Bet Button", "PASS", f"MAX bet set to: {max_bet_value}")
                else:
                    self.log_test("Roulette", "MAX Bet Button", "FAIL", "Bet input not found")

                await self.take_screenshot(page, "roulette_max_bet", "MAX bet button clicked")
            else:
                self.log_test("Roulette", "MAX Bet Button", "WARN", "MAX button not found")

            # Test 4: Custom amount input
            print("\n--- Test 4: Custom Amount Input ---")
            await self.test_custom_bet_input(page)

            # Check for errors in console
            errors = [log for log in console_logs if log["type"] == "error"]
            if errors:
                self.log_error("Roulette", "Console Errors Found", {"errors": errors[:5]})  # Log first 5
            else:
                self.log_test("Roulette", "Console Errors", "PASS", "No console errors")

            # Check for network errors
            if network_errors:
                self.log_error("Roulette", "Network Errors Found", {"errors": network_errors[:5]})
            else:
                self.log_test("Roulette", "Network Errors", "PASS", "No network errors")

        except Exception as e:
            self.log_error("Roulette", f"Exception: {str(e)}")
            await self.take_screenshot(page, "roulette_exception", "Exception during roulette test")

    async def test_roulette_bet(self, page: Page, amount: str, color: str, test_name: str):
        """Helper: Test placing a bet on roulette"""
        try:
            # Find bet input
            bet_input = await page.query_selector('input[name="bet"], input.bet-amount, #bet-amount, input[type="number"]')
            if not bet_input:
                self.log_test("Roulette", f"Bet Input ({test_name})", "FAIL", "Bet input not found")
                return

            # Clear and enter bet amount
            await bet_input.click()
            await bet_input.fill("")
            await bet_input.type(amount)
            await asyncio.sleep(0.5)

            actual_value = await bet_input.input_value()
            self.log_test("Roulette", f"Bet Amount Entry ({test_name})", "PASS", f"Entered: {actual_value}")

            await self.take_screenshot(page, f"bet_{test_name}_entered", f"Bet amount {amount} entered")

            # Find color button (RED or BLACK)
            color_button = await page.query_selector(f'button:has-text("{color}"), .bet-{color.lower()}, button[data-color="{color.lower()}"]')
            if not color_button:
                self.log_test("Roulette", f"Color Button ({test_name})", "FAIL", f"{color} button not found")
                return

            # Click color to place bet
            await color_button.click()
            await asyncio.sleep(1)
            await self.take_screenshot(page, f"bet_{test_name}_placed", f"Bet on {color} clicked")

            # Check for bet confirmation or error
            await asyncio.sleep(2)

            # Look for error messages
            error_elements = await page.query_selector_all('.error, .alert-danger, [role="alert"]')
            if error_elements:
                error_texts = []
                for elem in error_elements:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        text = await elem.text_content()
                        error_texts.append(text.strip())

                if error_texts:
                    self.log_test("Roulette", f"Bet Placement ({test_name})", "FAIL", f"Errors: {', '.join(error_texts)}")
                    await self.take_screenshot(page, f"bet_{test_name}_error", f"Error placing bet")
                    return

            # Look for success confirmation
            success_elements = await page.query_selector_all('.success, .alert-success, .bet-placed')
            bet_placed = False
            for elem in success_elements:
                if await elem.is_visible():
                    bet_placed = True
                    text = await elem.text_content()
                    self.log_test("Roulette", f"Bet Placement ({test_name})", "PASS", f"Success: {text.strip()}")
                    break

            if not bet_placed:
                # Check if bet appears in active bets
                active_bets = await page.query_selector('.active-bets, .current-bets, .my-bets')
                if active_bets:
                    bet_placed = await active_bets.is_visible()
                    if bet_placed:
                        self.log_test("Roulette", f"Bet Placement ({test_name})", "PASS", "Bet visible in active bets")
                    else:
                        self.log_test("Roulette", f"Bet Placement ({test_name})", "WARN", "Cannot confirm bet placement")
                else:
                    self.log_test("Roulette", f"Bet Placement ({test_name})", "WARN", "Cannot confirm bet placement")

            # Wait for spin result
            print(f"   Waiting for spin result...")
            await asyncio.sleep(8)  # Wait for spin animation

            await self.take_screenshot(page, f"bet_{test_name}_result", f"Result after {test_name}")

            # Check for result
            result_element = await page.query_selector('.result, .spin-result, .game-result')
            if result_element and await result_element.is_visible():
                result_text = await result_element.text_content()
                self.log_test("Roulette", f"Spin Result ({test_name})", "PASS", f"Result: {result_text.strip()}")

        except Exception as e:
            self.log_error("Roulette", f"Exception in bet test ({test_name}): {str(e)}")
            await self.take_screenshot(page, f"bet_{test_name}_exception", f"Exception during {test_name}")

    async def test_custom_bet_input(self, page: Page):
        """Test custom bet amount input validation"""
        try:
            bet_input = await page.query_selector('input[name="bet"], input.bet-amount, #bet-amount, input[type="number"]')
            if not bet_input:
                self.log_test("Roulette", "Custom Bet Input", "FAIL", "Bet input not found")
                return

            # Test various amounts
            test_amounts = ["1000", "25000", "75000", "150000"]
            for amount in test_amounts:
                await bet_input.fill("")
                await bet_input.type(amount)
                await asyncio.sleep(0.3)
                actual = await bet_input.input_value()

                if actual == amount:
                    self.log_test("Roulette", f"Custom Input ({amount})", "PASS", f"Accepted: {actual}")
                else:
                    self.log_test("Roulette", f"Custom Input ({amount})", "WARN", f"Input: {amount}, Got: {actual}")

        except Exception as e:
            self.log_error("Roulette", f"Custom input test exception: {str(e)}")

    async def test_stocks_trading(self, page: Page):
        """Test 3: Stock Market Trading (PRIORITY - User reported issues)"""
        print("\n" + "="*60)
        print("TEST 3: STOCK MARKET TRADING")
        print("="*60)

        console_logs = await self.capture_console_logs(page, "Stocks")
        network_errors = await self.capture_network_errors(page, "Stocks")

        try:
            # Navigate to stocks page
            await page.goto(f"{self.base_url}/stocks")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await self.take_screenshot(page, "stocks_initial", "Stock market page loaded")

            # Check if stocks interface is visible
            stocks_visible = await page.is_visible('.stocks-container, #stocks-market, .stock-list')
            if stocks_visible:
                self.log_test("Stocks", "Interface Load", "PASS", "Stocks interface loaded")
            else:
                self.log_test("Stocks", "Interface Load", "FAIL", "Stocks interface not found")
                return

            # Check for stock listings
            stock_items = await page.query_selector_all('.stock-item, .stock-card, [data-stock]')
            if stock_items:
                self.log_test("Stocks", "Stock Listings", "PASS", f"Found {len(stock_items)} stocks")
            else:
                self.log_test("Stocks", "Stock Listings", "FAIL", "No stocks found")

            # Test buying a stock
            print("\n--- Testing Stock Purchase ---")
            buy_button = await page.query_selector('button:has-text("Buy"), .btn-buy, button[data-action="buy"]')
            if buy_button:
                await buy_button.click()
                await asyncio.sleep(1)
                await self.take_screenshot(page, "stocks_buy_clicked", "Buy button clicked")

                # Check for buy dialog/form
                buy_form_visible = await page.is_visible('.buy-form, .trade-modal, [data-trade-form]')
                if buy_form_visible:
                    self.log_test("Stocks", "Buy Form", "PASS", "Buy form opened")

                    # Try to complete purchase
                    amount_input = await page.query_selector('input[name="amount"], input.amount-input, input[type="number"]')
                    if amount_input:
                        await amount_input.fill("1")
                        await asyncio.sleep(0.5)

                        confirm_button = await page.query_selector('button:has-text("Confirm"), button.confirm-buy, button[type="submit"]')
                        if confirm_button:
                            await confirm_button.click()
                            await asyncio.sleep(2)
                            await self.take_screenshot(page, "stocks_buy_result", "After purchase attempt")

                            # Check for success/error message
                            await self.check_for_messages(page, "Stocks", "Buy Stock")
                        else:
                            self.log_test("Stocks", "Buy Stock", "FAIL", "Confirm button not found")
                    else:
                        self.log_test("Stocks", "Buy Stock", "FAIL", "Amount input not found")
                else:
                    self.log_test("Stocks", "Buy Form", "FAIL", "Buy form did not open")
            else:
                self.log_test("Stocks", "Buy Button", "FAIL", "Buy button not found")

            # Test selling a stock
            print("\n--- Testing Stock Sale ---")
            await asyncio.sleep(2)
            sell_button = await page.query_selector('button:has-text("Sell"), .btn-sell, button[data-action="sell"]')
            if sell_button:
                await sell_button.click()
                await asyncio.sleep(1)
                await self.take_screenshot(page, "stocks_sell_clicked", "Sell button clicked")

                # Similar checks for sell functionality
                sell_form_visible = await page.is_visible('.sell-form, .trade-modal, [data-trade-form]')
                if sell_form_visible:
                    self.log_test("Stocks", "Sell Form", "PASS", "Sell form opened")
                else:
                    self.log_test("Stocks", "Sell Form", "WARN", "Sell form state unclear")
            else:
                self.log_test("Stocks", "Sell Button", "WARN", "Sell button not found (may not own stocks)")

            # Check portfolio display
            portfolio = await page.query_selector('.portfolio, .my-stocks, [data-portfolio]')
            if portfolio and await portfolio.is_visible():
                self.log_test("Stocks", "Portfolio Display", "PASS", "Portfolio visible")
            else:
                self.log_test("Stocks", "Portfolio Display", "WARN", "Portfolio not visible")

            # Check for errors
            errors = [log for log in console_logs if log["type"] == "error"]
            if errors:
                self.log_error("Stocks", "Console Errors", {"errors": errors[:5]})

            if network_errors:
                self.log_error("Stocks", "Network Errors", {"errors": network_errors[:5]})

        except Exception as e:
            self.log_error("Stocks", f"Exception: {str(e)}")
            await self.take_screenshot(page, "stocks_exception", "Exception during stocks test")

    async def test_staking_features(self, page: Page):
        """Test 4: Staking Features"""
        print("\n" + "="*60)
        print("TEST 4: STAKING FEATURES")
        print("="*60)

        try:
            await page.goto(f"{self.base_url}/staking")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await self.take_screenshot(page, "staking_initial", "Staking page loaded")

            # Check interface
            staking_visible = await page.is_visible('.staking-container, #staking-interface, .stake-form')
            if staking_visible:
                self.log_test("Staking", "Interface Load", "PASS", "Staking interface loaded")
            else:
                self.log_test("Staking", "Interface Load", "FAIL", "Staking interface not found")
                return

            # Check for staking options
            stake_buttons = await page.query_selector_all('button:has-text("Stake"), .btn-stake')
            if stake_buttons:
                self.log_test("Staking", "Stake Options", "PASS", f"Found {len(stake_buttons)} staking options")
            else:
                self.log_test("Staking", "Stake Options", "FAIL", "No staking options found")

            # Try to stake
            if stake_buttons:
                await stake_buttons[0].click()
                await asyncio.sleep(1)
                await self.take_screenshot(page, "staking_attempt", "Stake button clicked")
                await self.check_for_messages(page, "Staking", "Stake Action")

        except Exception as e:
            self.log_error("Staking", f"Exception: {str(e)}")
            await self.take_screenshot(page, "staking_exception", "Exception during staking test")

    async def test_crypto_prices(self, page: Page):
        """Test 5: Crypto Prices Display"""
        print("\n" + "="*60)
        print("TEST 5: CRYPTO PRICES DISPLAY")
        print("="*60)

        try:
            await page.goto(f"{self.base_url}/")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await self.take_screenshot(page, "crypto_prices", "Crypto prices page")

            # Check for price cards
            price_cards = await page.query_selector_all('.crypto-card, .price-card, [data-crypto]')
            if price_cards:
                self.log_test("Crypto", "Price Cards", "PASS", f"Found {len(price_cards)} crypto cards")
            else:
                self.log_test("Crypto", "Price Cards", "FAIL", "No crypto cards found")

            # Check for live updates
            await asyncio.sleep(5)
            self.log_test("Crypto", "Live Updates", "INFO", "Waited 5s for price updates")

        except Exception as e:
            self.log_error("Crypto", f"Exception: {str(e)}")

    async def test_portfolio(self, page: Page):
        """Test 6: Portfolio Page"""
        print("\n" + "="*60)
        print("TEST 6: PORTFOLIO")
        print("="*60)

        try:
            await page.goto(f"{self.base_url}/portfolio")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await self.take_screenshot(page, "portfolio", "Portfolio page")

            portfolio_visible = await page.is_visible('.portfolio-container, #portfolio')
            if portfolio_visible:
                self.log_test("Portfolio", "Page Load", "PASS", "Portfolio page loaded")
            else:
                self.log_test("Portfolio", "Page Load", "FAIL", "Portfolio not visible")

        except Exception as e:
            self.log_error("Portfolio", f"Exception: {str(e)}")

    async def test_converter(self, page: Page):
        """Test 7: Currency Converter"""
        print("\n" + "="*60)
        print("TEST 7: CURRENCY CONVERTER")
        print("="*60)

        try:
            await page.goto(f"{self.base_url}/converter")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await self.take_screenshot(page, "converter", "Converter page")

            converter_visible = await page.is_visible('.converter-container, #converter')
            if converter_visible:
                self.log_test("Converter", "Page Load", "PASS", "Converter loaded")
            else:
                self.log_test("Converter", "Page Load", "FAIL", "Converter not visible")

        except Exception as e:
            self.log_error("Converter", f"Exception: {str(e)}")

    async def test_gem_store(self, page: Page):
        """Test 8: GEM Store"""
        print("\n" + "="*60)
        print("TEST 8: GEM STORE")
        print("="*60)

        try:
            await page.goto(f"{self.base_url}/gem-store")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await self.take_screenshot(page, "gem_store", "GEM Store page")

            store_visible = await page.is_visible('.gem-store, #gem-store')
            if store_visible:
                self.log_test("GEM Store", "Page Load", "PASS", "Store loaded")
            else:
                self.log_test("GEM Store", "Page Load", "FAIL", "Store not visible")

        except Exception as e:
            self.log_error("GEM Store", f"Exception: {str(e)}")

    async def test_achievements(self, page: Page):
        """Test 9: Achievements"""
        print("\n" + "="*60)
        print("TEST 9: ACHIEVEMENTS")
        print("="*60)

        try:
            await page.goto(f"{self.base_url}/achievements")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            await self.take_screenshot(page, "achievements", "Achievements page")

            achievements_visible = await page.is_visible('.achievements-container, #achievements')
            if achievements_visible:
                self.log_test("Achievements", "Page Load", "PASS", "Achievements loaded")
            else:
                self.log_test("Achievements", "Page Load", "FAIL", "Achievements not visible")

        except Exception as e:
            self.log_error("Achievements", f"Exception: {str(e)}")

    async def test_daily_bonus(self, page: Page):
        """Test 10: Daily Bonus"""
        print("\n" + "="*60)
        print("TEST 10: DAILY BONUS")
        print("="*60)

        try:
            # Daily bonus might be on profile or separate page
            await page.goto(f"{self.base_url}/profile")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)

            daily_bonus_button = await page.query_selector('button:has-text("Daily"), .daily-bonus')
            if daily_bonus_button:
                self.log_test("Daily Bonus", "Button Found", "PASS", "Daily bonus button visible")
                await daily_bonus_button.click()
                await asyncio.sleep(2)
                await self.take_screenshot(page, "daily_bonus", "Daily bonus clicked")
                await self.check_for_messages(page, "Daily Bonus", "Claim")
            else:
                self.log_test("Daily Bonus", "Button Found", "WARN", "Daily bonus button not found")

        except Exception as e:
            self.log_error("Daily Bonus", f"Exception: {str(e)}")

    async def check_for_messages(self, page: Page, category: str, action: str):
        """Helper: Check for success/error messages"""
        # Check for error messages
        error_elements = await page.query_selector_all('.error, .alert-danger, [role="alert"]')
        for elem in error_elements:
            if await elem.is_visible():
                text = await elem.text_content()
                if text.strip():
                    self.log_test(category, action, "FAIL", f"Error: {text.strip()}")
                    return

        # Check for success messages
        success_elements = await page.query_selector_all('.success, .alert-success, .toast-success')
        for elem in success_elements:
            if await elem.is_visible():
                text = await elem.text_content()
                if text.strip():
                    self.log_test(category, action, "PASS", f"Success: {text.strip()}")
                    return

        # No clear message found
        self.log_test(category, action, "WARN", "No clear success/error message")

    async def run_all_tests(self):
        """Run all tests"""
        async with async_playwright() as p:
            # Launch browser with DevTools
            browser = await p.chromium.launch(
                headless=False,
                args=['--auto-open-devtools-for-tabs']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                record_video_dir="test_videos"
            )

            page = await context.new_page()

            # Enable console log capture for entire session
            page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))

            try:
                # Test 1: Login & Authentication
                login_success = await self.test_login_authentication(page)

                if not login_success:
                    print("\n❌ LOGIN FAILED - Cannot proceed with other tests")
                    return

                # Test 2: Roulette Game (PRIORITY)
                await self.test_roulette_game(page)

                # Test 3: Stock Market (PRIORITY)
                await self.test_stocks_trading(page)

                # Test 4: Staking
                await self.test_staking_features(page)

                # Test 5: Crypto Prices
                await self.test_crypto_prices(page)

                # Test 6: Portfolio
                await self.test_portfolio(page)

                # Test 7: Converter
                await self.test_converter(page)

                # Test 8: GEM Store
                await self.test_gem_store(page)

                # Test 9: Achievements
                await self.test_achievements(page)

                # Test 10: Daily Bonus
                await self.test_daily_bonus(page)

                print("\n" + "="*60)
                print("ALL TESTS COMPLETED")
                print("="*60)

            finally:
                # Save results to file
                await self.save_results()

                # Keep browser open for 10 seconds to review
                print("\n⏱️  Browser will close in 10 seconds...")
                await asyncio.sleep(10)

                await context.close()
                await browser.close()

    async def save_results(self):
        """Save test results to JSON file"""
        results_file = Path("test_results.json")
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)

        print(f"\n📊 Results saved to: {results_file}")

        # Generate summary report
        self.generate_summary_report()

    def generate_summary_report(self):
        """Generate and print summary report"""
        print("\n" + "="*60)
        print("TEST SUMMARY REPORT")
        print("="*60)

        total_tests = len(self.test_results["tests"])
        passed = len([t for t in self.test_results["tests"] if t["status"] == "PASS"])
        failed = len([t for t in self.test_results["tests"] if t["status"] == "FAIL"])
        warnings = len([t for t in self.test_results["tests"] if t["status"] == "WARN"])

        print(f"\nTotal Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")

        if self.test_results["errors"]:
            print(f"\n🔴 Total Errors: {len(self.test_results['errors'])}")
            print("\nCritical Errors:")
            for error in self.test_results["errors"][:5]:
                print(f"  - [{error['category']}] {error['error']}")

        print(f"\n📸 Screenshots captured: {len(self.test_results['screenshots'])}")
        print(f"📁 Screenshot directory: {self.screenshots_dir}")

        # Category breakdown
        print("\n📊 Results by Category:")
        categories = {}
        for test in self.test_results["tests"]:
            cat = test["category"]
            if cat not in categories:
                categories[cat] = {"PASS": 0, "FAIL": 0, "WARN": 0}
            categories[cat][test["status"]] += 1

        for cat, counts in categories.items():
            total = sum(counts.values())
            print(f"  {cat}: {counts['PASS']}/{total} passed, {counts['FAIL']} failed, {counts['WARN']} warnings")


async def main():
    """Main entry point"""
    print("""
    ==============================================================
      CryptoChecker V3 - Comprehensive Platform Test Suite
      Testing ALL features with focus on reported issues
    ==============================================================
    """)

    tester = CryptoCheckerTester()
    await tester.run_all_tests()

    print("\n[*] Testing complete! Check test_results.json for detailed results.")
    print("[*] Screenshots available in test_screenshots/ directory")
    print("[*] Video recording available in test_videos/ directory")


if __name__ == "__main__":
    asyncio.run(main())
