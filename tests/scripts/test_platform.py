"""Playwright test with proper login"""
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        page = await browser.new_page()

        print("1. Login via API...")
        await page.goto("http://localhost:8000")
        
        # Login and reload to apply auth
        result = await page.evaluate("""
            async () => {
                const res = await fetch('http://localhost:8000/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: 'Emu', password: 'EmuEmu'})
                });
                const data = await res.json();
                if (data.access_token) {
                    localStorage.setItem('jwt_token', data.access_token);
                    // Reload page to apply auth
                    window.location.reload();
                }
                return data;
            }
        """)
        print(f"   Login response: {result.get('user', {}).get('username', 'N/A')}")
        print(f"   Balance: {result.get('user', {}).get('wallet_balance', 'N/A')} GEM")
        
        # Wait for reload
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        
        # Verify login
        is_logged_in = await page.evaluate("() => !!localStorage.getItem('jwt_token')")
        print(f"   JWT Token stored: {is_logged_in}\n")

        print("2. Roulette test...")
        try:
            await page.goto("http://localhost:8000/gaming", wait_until="domcontentloaded")
            await page.wait_for_timeout(6000)  # Wait for balance retry
            
            # Check balance
            balance = await page.locator("#gaming-balance").inner_text(timeout=5000)
            print(f"   Balance: {balance}")
            
            # Check retry logs
            logs = await page.evaluate("() => window.rouletteGame?.balance || 'N/A'")
            print(f"   Roulette object balance: {logs}")
            
            if "5,000" in balance or "5000" in balance:
                print("   ❌ STILL GUEST MODE")
            else:
                print("   ✅ AUTHENTICATED")
                
                # Try bet
                await page.click("button:has-text('100K')")
                await page.wait_for_timeout(500)
                await page.evaluate("document.querySelectorAll('button').forEach(b => b.textContent.includes('RED') && b.click())")
                await page.wait_for_timeout(2000)
                print("   ✅ 100K bet placed!\n")
        except Exception as e:
            print(f"   ❌ ERROR: {e}\n")

        print("3. Minigames test...")
        try:
            await page.goto("http://localhost:8000/minigames")
            await page.wait_for_timeout(2000)
            await page.click("text=Play Now >> nth=0")
            await page.wait_for_timeout(1000)
            await page.fill("#betAmount", "1000")
            await page.click("button:has-text('HEADS')")
            await page.wait_for_timeout(3000)
            print("   ✅ Coin flip done!\n")
        except Exception as e:
            print(f"   ❌ ERROR: {e}\n")

        await page.screenshot(path="test_result.png")
        print("Screenshot: test_result.png")
        await page.wait_for_timeout(5000)
        await browser.close()

asyncio.run(test())
