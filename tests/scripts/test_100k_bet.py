"""
Quick test to reproduce the >5K betting issue
"""
import asyncio
from playwright.async_api import async_playwright

async def test_100k_bet():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # Store console messages
        console_messages = []
        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))

        # Navigate to homepage
        print("1. Navigating to homepage...")
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")

        # Check if already logged in
        balance_elem = await page.query_selector(".balance-amount, #gaming-balance")
        if balance_elem:
            balance_text = await balance_elem.inner_text()
            print(f"   Already logged in! Balance: {balance_text}")
        else:
            # Login
            print("2. Logging in as Emu...")
            # Check if login modal is visible or needs to be opened
            login_input = await page.query_selector("#loginUsername")
            if not await login_input.is_visible():
                # Click sign in button to open modal
                await page.click("text=Sign In")
                await page.wait_for_timeout(500)

            await page.fill("#loginUsername", "Emu")
            await page.fill("#loginPassword", "EmuEmu")
            await page.click("button:has-text('Sign In')")
            await page.wait_for_timeout(2000)

        # Navigate to roulette
        print("3. Navigating to roulette...")
        await page.goto("http://localhost:8000/gaming")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Get balance
        balance = await page.locator("#gaming-balance").inner_text()
        print(f"   Current balance: {balance} GEM")

        # Test 1: 10K bet (should work)
        print("\n4. Testing 10K bet...")
        await page.click("button:has-text('10K')")
        await page.wait_for_timeout(500)
        amount = await page.input_value("#betAmount")
        print(f"   Bet amount set to: {amount}")

        # Click RED button
        await page.evaluate("""
            Array.from(document.querySelectorAll('button'))
                .find(btn => btn.textContent.includes('RED') && btn.textContent.includes('2:1'))
                ?.click()
        """)
        await page.wait_for_timeout(2000)

        # Check for errors
        errors = [msg for msg in console_messages if 'error' in msg.lower() or '❌' in msg]
        if errors:
            print(f"   ❌ ERRORS FOUND:")
            for error in errors[-5:]:
                print(f"      {error}")
        else:
            print(f"   ✅ 10K bet succeeded!")

        console_messages.clear()

        # Test 2: 100K bet (reported as broken)
        print("\n5. Testing 100K bet...")
        await page.click("button:has-text('100K')")
        await page.wait_for_timeout(500)
        amount = await page.input_value("#betAmount")
        print(f"   Bet amount set to: {amount}")

        # Click BLACK button
        await page.evaluate("""
            Array.from(document.querySelectorAll('button'))
                .find(btn => btn.textContent.includes('BLACK') && btn.textContent.includes('2:1'))
                ?.click()
        """)
        await page.wait_for_timeout(2000)

        # Check for errors
        errors = [msg for msg in console_messages if 'error' in msg.lower() or '❌' in msg or 'insufficient' in msg.lower()]
        if errors:
            print(f"   ❌ ERRORS FOUND:")
            for error in errors[-10:]:
                print(f"      {error}")
        else:
            print(f"   ✅ 100K bet succeeded!")

        # Test 3: Custom 50K bet
        print("\n6. Testing custom 50K bet...")
        await page.fill("#betAmount", "50000")
        await page.wait_for_timeout(500)

        # Click GREEN button
        await page.evaluate("""
            Array.from(document.querySelectorAll('button'))
                .find(btn => btn.textContent.includes('GREEN') && btn.textContent.includes('14:1'))
                ?.click()
        """)
        await page.wait_for_timeout(2000)

        # Check for errors
        errors = [msg for msg in console_messages if 'error' in msg.lower() or '❌' in msg or 'insufficient' in msg.lower()]
        if errors:
            print(f"   ❌ ERRORS FOUND:")
            for error in errors[-10:]:
                print(f"      {error}")
        else:
            print(f"   ✅ 50K bet succeeded!")

        # Take screenshot
        await page.screenshot(path="bet_test_result.png")
        print("\n7. Screenshot saved to bet_test_result.png")

        # Wait to see results
        print("\n8. Waiting 5 seconds to see results...")
        await page.wait_for_timeout(5000)

        await browser.close()

        print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_100k_bet())
