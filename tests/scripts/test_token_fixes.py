"""
Playwright Test Suite: Token Authentication Fix Verification
Tests all 6 fixed pages to ensure no redirects to login page
"""

import asyncio
from playwright.async_api import async_playwright, Page, expect
import sys

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpass123"

# Pages to test
PAGES_TO_TEST = [
    ("/challenges", "Challenges", "challenges"),
    ("/crash", "Crash", "crash game"),
    ("/minigames", "Mini-Games", "minigames"),
    ("/social", "Social", "social"),
    ("/staking", "Staking", "staking"),
    ("/trading", "Trading", "trading"),
]

class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.total = 0

    def add_pass(self, test_name):
        self.passed.append(test_name)
        self.total += 1
        print(f"[PASS] PASS: {test_name}")

    def add_fail(self, test_name, error):
        self.failed.append((test_name, error))
        self.total += 1
        print(f"[FAIL] FAIL: {test_name}")
        print(f"   Error: {error}")

    def print_summary(self):
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.total}")
        print(f"Passed: {len(self.passed)} [PASS]")
        print(f"Failed: {len(self.failed)} [FAIL]")
        print(f"Success Rate: {(len(self.passed)/self.total*100):.1f}%")

        if self.failed:
            print("\nFailed Tests:")
            for test_name, error in self.failed:
                print(f"  - {test_name}: {error}")

        print("="*60)

async def setup_test_user(page: Page):
    """Create or login test user"""
    try:
        # Try to register
        await page.goto(f"{BASE_URL}/register")
        await page.wait_for_load_state("networkidle")

        # Fill registration form
        await page.fill('input[name="username"]', TEST_USERNAME)
        await page.fill('input[name="email"]', f"{TEST_USERNAME}@test.com")
        await page.fill('input[name="password"]', TEST_PASSWORD)

        # Submit
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(2000)

    except Exception as e:
        print(f"Registration skipped (user may exist): {e}")

    # Now login
    await page.goto(f"{BASE_URL}/login")
    await page.wait_for_load_state("networkidle")

    await page.fill('input[name="username"]', TEST_USERNAME)
    await page.fill('input[name="password"]', TEST_PASSWORD)

    await page.click('button[type="submit"]')
    await page.wait_for_timeout(2000)

    return True

async def check_token_in_storage(page: Page, expected_token_name: str):
    """Verify correct token name in localStorage"""
    token = await page.evaluate(f"localStorage.getItem('{expected_token_name}')")
    return token is not None

async def test_page_no_redirect(page: Page, url: str, page_name: str, results: TestResults):
    """Test that navigating to a page doesn't redirect to login"""
    test_name = f"Navigate to {page_name} without redirect"

    try:
        # Navigate to the page
        await page.goto(f"{BASE_URL}{url}")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)

        # Check current URL - should NOT be at /login
        current_url = page.url

        if "/login" in current_url:
            results.add_fail(test_name, f"Redirected to login page! URL: {current_url}")
            return False

        # Check that we're on the correct page
        if url not in current_url:
            results.add_fail(test_name, f"Wrong page! Expected: {url}, Got: {current_url}")
            return False

        # Check for "Welcome Back" text (login page indicator)
        try:
            welcome_text = await page.text_content("body")
            if "Welcome Back!" in welcome_text and url != "/login":
                results.add_fail(test_name, "Found 'Welcome Back!' text - likely on login page")
                return False
        except:
            pass

        results.add_pass(test_name)
        return True

    except Exception as e:
        results.add_fail(test_name, str(e))
        return False

async def test_token_storage(page: Page, results: TestResults):
    """Verify auth_token is stored correctly"""
    test_name = "Token stored as 'auth_token' in localStorage"

    try:
        # Check for correct token
        auth_token = await page.evaluate("localStorage.getItem('auth_token')")

        if not auth_token:
            results.add_fail(test_name, "auth_token not found in localStorage")
            return False

        # Check that old token name is NOT present
        old_token = await page.evaluate("localStorage.getItem('token')")

        if old_token:
            results.add_fail(test_name, "Old 'token' name still in localStorage")
            return False

        results.add_pass(test_name)
        return True

    except Exception as e:
        results.add_fail(test_name, str(e))
        return False

async def run_tests():
    """Main test runner"""
    print("="*60)
    print("TOKEN FIX VERIFICATION TEST SUITE")
    print("="*60)
    print(f"Testing against: {BASE_URL}")
    print(f"Pages to test: {len(PAGES_TO_TEST)}")
    print("="*60 + "\n")

    results = TestResults()

    async with async_playwright() as p:
        # Launch browser
        print("[*] Launching browser...")
        browser = await p.chromium.launch(headless=False)  # headless=False to see the tests
        context = await browser.new_context()
        page = await context.new_page()

        # Setup test user and login
        print("[*] Setting up test user and logging in...")
        try:
            await setup_test_user(page)
            print("[PASS] Logged in successfully\n")
        except Exception as e:
            print(f"[FAIL] Login failed: {e}")
            await browser.close()
            return

        # Test 1: Verify token storage
        print("[*] Testing token storage...")
        await test_token_storage(page, results)
        print()

        # Test 2-7: Test each fixed page
        print("[*] Testing page navigation (no redirects)...\n")
        for url, name, keyword in PAGES_TO_TEST:
            await test_page_no_redirect(page, url, name, results)
            await page.wait_for_timeout(500)  # Small delay between tests

        print()

        # Test 8: Verify token persists
        print("[*] Testing token persistence...")
        test_name = "Token persists after navigation"
        try:
            # Navigate away and back
            await page.goto(f"{BASE_URL}/")
            await page.wait_for_timeout(500)

            token_after = await page.evaluate("localStorage.getItem('auth_token')")

            if token_after:
                results.add_pass(test_name)
            else:
                results.add_fail(test_name, "Token lost after navigation")
        except Exception as e:
            results.add_fail(test_name, str(e))

        print()

        # Close browser
        await browser.close()

    # Print summary
    results.print_summary()

    # Exit with appropriate code
    sys.exit(0 if len(results.failed) == 0 else 1)

if __name__ == "__main__":
    print("\nStarting Token Fix Verification Tests...\n")
    asyncio.run(run_tests())
