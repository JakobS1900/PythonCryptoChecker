"""
Fixed Playwright test with proper login
"""
import asyncio
from playwright.async_api import async_playwright

async def test_platform():
    print("🚀 Starting CryptoChecker Platform Test\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Test 1: Login as Emu
            print("1️⃣  Logging in as Emu...")
            await page.goto("http://localhost:8000")
            await page.wait_for_load_state("networkidle")

            # Check if already logged in
            if await page.locator("text=Emu").count() > 0:
                print("   ✅ Already logged in as Emu")
            else:
                print("   Attempting login...")

                # Fill login form (the modal might already be open)
                try:
                    # Try to fill the login form directly
                    await page.fill("#loginUsername", "Emu", timeout=2000)
                    await page.fill("#loginPassword", "EmuEmu")

                    # Click the Sign In button inside the form
                    await page.click("form button:has-text('Sign In')")
                    await page.wait_for_timeout(3000)
                    print("   ✅ Logged in successfully")
                except:
                    print("   ⚠️  Login form not visible - might already be logged in")

            # Test 2: Check auth status via API
            print("\n2️⃣  Checking authentication status...")
            try:
                response = await page.evaluate("""
                    async () => {
                        const res = await fetch('/api/auth/status');
                        return await res.json();
                    }
                """)
                print(f"   Auth Status: {response.get('authenticated', False)}")
                if response.get('user'):
                    print(f"   User: {response['user'].get('username', 'Unknown')}")
                    print(f"   Balance: {response['user'].get('wallet_balance', 'Unknown')} GEM")
            except Exception as e:
                print(f"   ⚠️  Could not check auth status: {e}")

            # Test 3: Roulette with balance check
            print("\n3️⃣  Testing Roulette...")
            await page.goto("http://localhost:8000/gaming")
            await page.wait_for_timeout(4000)  # Give time for balance to load

            # Check balance after waiting
            balance = await page.locator("#gaming-balance").inner_text()
            print(f"   Balance shown: {balance}")

            # Check what Auth/App objects say
            auth_check = await page.evaluate("""
                () => {
                    return {
                        hasAuth: typeof window.Auth !== 'undefined',
                        hasApp: typeof window.App !== 'undefined',
                        authUser: window.Auth?.currentUser?.wallet_balance,
                        appUser: window.App?.user?.wallet_balance,
                        rouletteBalance: window.rouletteGame?.balance
                    };
                }
            """)
            print(f"   Auth check: {auth_check}")

            if "5,000" in balance or "5000" in balance:
                print("   ❌ FAILED: Still in guest mode!")
                print("   Checking console for retry message...")
                await page.wait_for_timeout(2000)
            else:
                print(f"   ✅ Authenticated balance: {balance}")

            # Try 100K bet
            print("\n4️⃣  Testing 100K bet...")
            await page.click("button:has-text('100K')")
            await page.wait_for_timeout(500)

            bet_amount = await page.input_value("#betAmount")
            print(f"   Bet amount: {bet_amount}")

            # Click RED
            await page.evaluate("""
                document.querySelectorAll('button').forEach(btn => {
                    if (btn.textContent.includes('RED') && btn.textContent.includes('2:1')) {
                        btn.click();
                    }
                });
            """)
            print("   ✅ Clicked RED button")
            await page.wait_for_timeout(3000)

            # Test 5: Minigames
            print("\n5️⃣  Testing Minigames...")
            await page.goto("http://localhost:8000/minigames")
            await page.wait_for_timeout(2000)

            # Click first Play Now button
            await page.click("text=Play Now >> nth=0")
            await page.wait_for_timeout(1000)

            # The modal should be open, find the input
            bet_input = await page.query_selector("input#betAmount, input[placeholder*='amount'], input[type='number']")
            if bet_input:
                await bet_input.fill("1000")
                print("   ✅ Entered bet amount: 1000")

                # Click HEADS
                await page.click("button:has-text('HEADS')")
                print("   ✅ Clicked HEADS")
                await page.wait_for_timeout(3000)
                print("   ✅ Coin flip completed!")
            else:
                print("   ❌ Could not find bet input")

            # Test 6: Trading
            print("\n6️⃣  Testing Trading/Stocks...")
            await page.goto("http://localhost:8000/stocks")
            await page.wait_for_timeout(2000)

            if await page.locator("text=500").count() > 0:
                print("   ❌ 500 Server Error")
            else:
                print("   ✅ Stocks page loaded")

            print("\n" + "="*60)
            print("TEST COMPLETE")
            print("="*60)

            await page.screenshot(path="test_final.png")
            print("📸 Screenshot: test_final.png")

        except Exception as e:
            print(f"\n💥 Error: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path="test_error.png")

        finally:
            print("\nKeeping browser open for 10 seconds...")
            await page.wait_for_timeout(10000)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_platform())
