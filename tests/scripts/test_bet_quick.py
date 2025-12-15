"""
SUPER QUICK test - assumes you're already logged in as Emu
Just tests the betting
"""
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Store errors
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if 'error' in msg.type or '❌' in msg.text or 'Insufficient' in msg.text else None)

        print("Navigating to roulette...")
        await page.goto("http://localhost:8000/gaming")
        await page.wait_for_timeout(3000)

        balance = await page.locator("#gaming-balance").inner_text()
        print(f"Balance: {balance}")

        # Test 100K bet
        print("\nTesting 100K bet...")
        await page.click("button:has-text('100K')")
        await page.wait_for_timeout(500)

        # Click RED
        red_btn = await page.query_selector("button:has-text('RED')")
        if red_btn:
            await red_btn.click()
            print("Clicked RED button")
            await page.wait_for_timeout(3000)

            if errors:
                print(f"\n❌ ERRORS:")
                for e in errors:
                    print(f"   {e}")
            else:
                print("✅ No errors - bet may have succeeded!")

        await page.screenshot(path="quick_bet_test.png")
        print("\nScreenshot: quick_bet_test.png")

        await page.wait_for_timeout(5000)
        await browser.close()

asyncio.run(test())
