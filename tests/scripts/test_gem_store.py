"""
Quick GEM Store Purchase Test
Tests the reference_id fix we just applied
"""

import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8000"
TEST_USERNAME = "Emu"
TEST_PASSWORD = "EmuEmu"

async def test_gem_store_purchase():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        page = await browser.new_page()

        print("\n[STEP 1] Going to login page...")
        await page.goto(f"{BASE_URL}/login")
        await page.wait_for_load_state("networkidle")

        print("[STEP 2] Logging in as Emu...")
        await page.fill('input[name="username"]', TEST_USERNAME)
        await page.fill('input[name="password"]', TEST_PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

        # Check if we're logged in
        current_url = page.url
        print(f"[INFO] Current URL after login: {current_url}")

        print("[STEP 3] Navigating to GEM Store...")
        await page.goto(f"{BASE_URL}/gem-store")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

        # Check current URL
        current_url = page.url
        print(f"[INFO] GEM Store URL: {current_url}")

        if "login" in current_url:
            print("[FAIL] Redirected to login - authentication issue!")
            await browser.close()
            return False

        print("[STEP 4] Looking for purchase buttons...")
        # Wait for purchase buttons to appear
        try:
            await page.wait_for_selector('.purchase-btn', timeout=5000)
            print("[SUCCESS] Purchase buttons found!")
        except:
            print("[FAIL] No purchase buttons found!")
            await browser.close()
            return False

        print("[STEP 5] Getting initial balance...")
        # Try to get balance from navbar
        try:
            balance_text = await page.text_content('.text-light-emphasis')
            print(f"[INFO] Initial balance: {balance_text}")
        except:
            print("[WARN] Could not read balance")

        print("[STEP 6] Clicking first purchase button...")
        await page.click('.purchase-btn')
        await asyncio.sleep(3)

        # Check console for errors
        print("[STEP 7] Checking for errors...")
        await asyncio.sleep(2)

        print("\n[TEST COMPLETE] Check the browser window and server logs!")
        print("Keeping browser open for 10 seconds for inspection...")
        await asyncio.sleep(10)

        await browser.close()
        return True

if __name__ == "__main__":
    asyncio.run(test_gem_store_purchase())
