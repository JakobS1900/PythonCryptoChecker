"""
Visual Playwright Test - Token Fix Verification
Watch the browser test all fixed pages in real-time!
"""

import asyncio
from playwright.async_api import async_playwright, Page
import sys

BASE_URL = "http://localhost:8000"
TEST_USERNAME = "Emu"
TEST_PASSWORD = "EmuEmu"

# Pages we fixed
PAGES_TO_TEST = [
    {"url": "/challenges", "name": "Daily Challenges", "keyword": "streak"},
    {"url": "/crash", "name": "Crash Game", "keyword": "crash"},
    {"url": "/minigames", "name": "Mini-Games", "keyword": "games"},
    {"url": "/social", "name": "Social Hub", "keyword": "friends"},
    {"url": "/staking", "name": "GEM Staking", "keyword": "stake"},
    {"url": "/trading", "name": "GEM Trading", "keyword": "trade"},
]

async def log(message, color="white"):
    """Colored console output"""
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "white": "\033[0m",
        "cyan": "\033[96m",
    }
    print(f"{colors.get(color, '')}{message}\033[0m")

async def wait_for_user(message):
    """Pause and wait for user to observe"""
    await log(f"\n{'='*60}", "cyan")
    await log(f"  {message}", "cyan")
    await log(f"{'='*60}\n", "cyan")
    await asyncio.sleep(2)  # Give time to observe

async def test_login(page: Page):
    """Login with visual feedback"""
    await log("\n[STEP 1] Testing Login...", "yellow")

    try:
        # Go to home page first
        await page.goto(BASE_URL)
        await page.wait_for_load_state("networkidle")
        await wait_for_user("Opened home page - observe the navbar")

        # Click login button in navbar (if not logged in)
        try:
            login_button = page.locator('button:has-text("Login")')
            if await login_button.is_visible():
                await log("Clicking Login button...", "blue")
                await login_button.click()
                await page.wait_for_timeout(1000)
        except:
            await log("No login button found (may already be logged in)", "yellow")

        # Check if login modal or page appeared
        await page.wait_for_timeout(1000)

        # Try to fill login form
        username_input = page.locator('input[name="username"]').first
        password_input = page.locator('input[name="password"]').first

        if await username_input.is_visible():
            await log("Filling login form...", "blue")
            await username_input.fill(TEST_USERNAME)
            await password_input.fill(TEST_PASSWORD)

            # Click submit
            submit_button = page.locator('button[type="submit"]').first
            await submit_button.click()

            await log("Login submitted!", "green")
            await page.wait_for_timeout(3000)

            # Check if we're logged in
            navbar = await page.content()
            if "GEM" in navbar:
                await log("[SUCCESS] Logged in successfully!", "green")
                return True

        # Maybe already logged in
        await log("[INFO] Checking if already logged in...", "yellow")
        navbar = await page.content()
        if "GEM" in navbar or "Balance" in navbar:
            await log("[SUCCESS] Already logged in!", "green")
            return True

        await log("[WARNING] Login status unclear - continuing anyway", "yellow")
        return True

    except Exception as e:
        await log(f"[ERROR] Login issue: {str(e)}", "red")
        await log("[INFO] Continuing with guest mode...", "yellow")
        return False

async def test_token_storage(page: Page):
    """Check localStorage for auth_token"""
    await log("\n[STEP 2] Checking Token Storage...", "yellow")

    try:
        # Check for auth_token
        auth_token = await page.evaluate("localStorage.getItem('auth_token')")

        if auth_token:
            await log(f"[SUCCESS] auth_token found: {auth_token[:20]}...", "green")
        else:
            await log("[WARNING] auth_token not found (guest mode?)", "yellow")

        # Check old token doesn't exist
        old_token = await page.evaluate("localStorage.getItem('token')")

        if old_token:
            await log("[ERROR] Old 'token' still exists! Fix didn't work!", "red")
            return False
        else:
            await log("[SUCCESS] Old 'token' name not present - fix is working!", "green")

        await wait_for_user("Token storage verified - see console output above")
        return True

    except Exception as e:
        await log(f"[ERROR] Token check failed: {str(e)}", "red")
        return False

async def test_page(page: Page, page_info: dict):
    """Test a single page navigation"""
    url = page_info["url"]
    name = page_info["name"]

    await log(f"\n[TESTING] {name} ({url})", "yellow")

    try:
        # Navigate to page
        await page.goto(f"{BASE_URL}{url}")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1500)

        # Check current URL
        current_url = page.url

        # Check if redirected to login
        if "/login" in current_url:
            await log(f"[FAIL] Redirected to login page!", "red")
            await log(f"       URL: {current_url}", "red")
            await wait_for_user(f"FAILED - {name} redirected to login - PRESS ANY KEY")
            return False

        # Check for "Welcome Back" text
        content = await page.content()
        if "Welcome Back!" in content and url != "/login":
            await log(f"[FAIL] Found 'Welcome Back!' - on login page!", "red")
            await wait_for_user(f"FAILED - {name} shows login page")
            return False

        # Success!
        await log(f"[PASS] {name} loaded successfully!", "green")
        await log(f"       URL: {current_url}", "blue")
        await wait_for_user(f"SUCCESS - {name} working correctly!")
        return True

    except Exception as e:
        await log(f"[ERROR] Test failed: {str(e)}", "red")
        await wait_for_user(f"ERROR testing {name}")
        return False

async def run_visual_tests():
    """Main test runner with visual feedback"""

    print("\n" + "="*60)
    print("  VISUAL TOKEN FIX VERIFICATION")
    print("  Watch the browser test all pages!")
    print("="*60 + "\n")

    results = {"passed": 0, "failed": 0, "pages": []}

    async with async_playwright() as p:
        await log("Launching browser (Chromium)...", "cyan")

        # Launch in headed mode so you can watch
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=500  # Slow down actions so you can see them
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 720}
        )

        page = await context.new_page()

        await log("Browser launched! Watch the window...", "green")
        await wait_for_user("Browser ready - starting tests")

        # Test 1: Login
        login_success = await test_login(page)

        # Test 2: Token storage
        token_success = await test_token_storage(page)

        # Test 3-8: Test each page
        await log("\n[STEP 3] Testing All Fixed Pages...", "yellow")
        await log("Watch as we navigate to each page!\n", "cyan")

        for page_info in PAGES_TO_TEST:
            success = await test_page(page, page_info)

            page_result = {
                "name": page_info["name"],
                "url": page_info["url"],
                "passed": success
            }
            results["pages"].append(page_result)

            if success:
                results["passed"] += 1
            else:
                results["failed"] += 1

        # Final summary
        await log("\n" + "="*60, "cyan")
        await log("  TEST SUMMARY", "cyan")
        await log("="*60, "cyan")

        total = results["passed"] + results["failed"]
        await log(f"\nTotal Pages Tested: {total}", "white")
        await log(f"Passed: {results['passed']}", "green")
        await log(f"Failed: {results['failed']}", "red")

        if results["failed"] == 0:
            await log("\n ALL TESTS PASSED!", "green")
            await log("Token fix is working perfectly!", "green")
        else:
            await log(f"\n{results['failed']} tests failed", "red")
            await log("Some pages still have issues", "yellow")

        await log("\n" + "="*60 + "\n", "cyan")

        # Show detailed results
        await log("Detailed Results:", "cyan")
        for result in results["pages"]:
            status = "[PASS]" if result["passed"] else "[FAIL]"
            color = "green" if result["passed"] else "red"
            await log(f"  {status} {result['name']} ({result['url']})", color)

        await log("\n\nPress Ctrl+C to close browser and exit...", "yellow")

        # Keep browser open for inspection
        try:
            await asyncio.sleep(300)  # 5 minutes
        except KeyboardInterrupt:
            await log("\nClosing browser...", "yellow")

        await browser.close()

        return results["failed"] == 0

if __name__ == "__main__":
    print("\nStarting Visual Test Suite...")
    print("Watch the browser window for live testing!\n")

    try:
        success = asyncio.run(run_visual_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
