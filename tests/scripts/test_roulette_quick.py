"""
Quick Roulette Bug Investigation - Focused Test Suite
"""

import asyncio
import time
import json
from datetime import datetime
from playwright.async_api import async_playwright

class QuickReport:
    def __init__(self):
        self.findings = []
        self.console_logs = []
        self.errors = []

    def log(self, msg, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = f"[{timestamp}] [{level}] {msg}"
        print(entry)
        self.findings.append(entry)

    def error(self, msg):
        self.log(msg, "ERROR")
        self.errors.append(msg)

report = QuickReport()

async def quick_investigation():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # Monitor console
        page.on("console", lambda msg: report.console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: report.error(f"Page error: {err}"))

        try:
            # SCENARIO 1: Page Load
            report.log("=== SCENARIO 1: Fresh Page Load ===")
            start = time.time()
            await page.goto("http://localhost:8000/gaming", wait_until="domcontentloaded")
            report.log(f"Page loaded in {time.time()-start:.2f}s")

            await page.screenshot(path="quick_1_initial.png")
            report.log("Screenshot: quick_1_initial.png")

            # Check timer
            await page.wait_for_timeout(2000)
            try:
                timer = page.locator("#auto-spin-timer").first
                timer_text = await timer.text_content(timeout=5000)
                report.log(f"Initial timer value: {timer_text}")

                # Wait 3 seconds and check again
                await page.wait_for_timeout(3000)
                timer_text2 = await timer.text_content()
                report.log(f"Timer after 3s: {timer_text2}")

                if timer_text == timer_text2:
                    report.error("🚨 TIMER IS STUCK!")
                else:
                    report.log("✅ Timer is counting down")
            except Exception as e:
                report.error(f"Timer not found: {e}")

            # SCENARIO 2: Betting
            report.log("\n=== SCENARIO 2: Betting Attempt ===")
            await page.screenshot(path="quick_2_before_bet.png")

            # Check game state
            game_state = await page.evaluate("""() => {
                return {
                    gameState: window.gameState,
                    currentPhase: window.currentPhase,
                    canBet: window.canBet,
                    timeRemaining: window.timeRemaining,
                    betPlaced: window.betPlaced
                }
            }""")
            report.log(f"Game state: {json.dumps(game_state, indent=2)}")

            # Try to click RED
            try:
                red = page.locator("button.bet-red, .bet-option.red").first
                await red.wait_for(timeout=5000)
                is_enabled = await red.is_enabled()
                report.log(f"RED button enabled: {is_enabled}")

                if is_enabled:
                    await red.click()
                    report.log("Clicked RED button")
                    await page.wait_for_timeout(1000)

                    # Check updated state
                    new_state = await page.evaluate("() => ({ gameState: window.gameState, betPlaced: window.betPlaced })")
                    report.log(f"State after bet: {json.dumps(new_state)}")
                else:
                    report.error("🚨 RED button is DISABLED")

                await page.screenshot(path="quick_2_after_bet.png")
            except Exception as e:
                report.error(f"Betting failed: {e}")

            # SCENARIO 3: Timer Watch (reduced to 10s)
            report.log("\n=== SCENARIO 3: Timer Observation (10s) ===")
            timer_values = []
            for i in range(5):
                try:
                    timer_text = await page.locator("#auto-spin-timer").text_content()
                    timer_values.append(timer_text)
                    report.log(f"t={i*2}s: {timer_text}")
                    await page.wait_for_timeout(2000)
                except:
                    break

            unique = set(timer_values)
            if len(unique) == 1:
                report.error(f"🚨 Timer stuck at: {list(unique)[0]}")
            else:
                report.log(f"✅ Timer changed {len(unique)} times")

            # SCENARIO 4: SSE Connection
            report.log("\n=== SCENARIO 4: SSE Connection ===")
            sse = await page.evaluate("""() => {
                return {
                    hasEventSource: typeof EventSource !== 'undefined',
                    connection: window.eventSource ? {
                        url: window.eventSource.url,
                        readyState: window.eventSource.readyState,
                        stateText: ['CONNECTING', 'OPEN', 'CLOSED'][window.eventSource.readyState]
                    } : null,
                    polling: window.pollingActive
                }
            }""")
            report.log(f"SSE: {json.dumps(sse, indent=2)}")

            if not sse.get('connection'):
                report.error("🚨 No SSE connection found!")

            await page.screenshot(path="quick_4_sse.png")

            # SCENARIO 5: Refresh
            report.log("\n=== SCENARIO 5: Page Refresh ===")
            await page.reload()
            await page.wait_for_timeout(3000)

            timer_after = await page.locator("#auto-spin-timer").text_content()
            report.log(f"Timer after refresh: {timer_after}")

            await page.wait_for_timeout(2000)
            timer_after2 = await page.locator("#auto-spin-timer").text_content()

            if timer_after == timer_after2:
                report.error("🚨 Timer still stuck after refresh!")

            await page.screenshot(path="quick_5_refresh.png")

        except Exception as e:
            report.error(f"Test failed: {e}")

        finally:
            await browser.close()

        # Summary
        print("\n" + "="*80)
        print("QUICK TEST SUMMARY")
        print("="*80)
        print(f"Total findings: {len(report.findings)}")
        print(f"Errors: {len(report.errors)}")
        print(f"Console logs: {len(report.console_logs)}")

        if report.errors:
            print("\n🚨 CRITICAL ISSUES FOUND:")
            for error in report.errors:
                print(f"  - {error}")

        print("\n📋 Console logs (last 20):")
        for log in report.console_logs[-20:]:
            print(f"  {log}")

        # Save report
        with open("QUICK_BUG_REPORT.txt", "w") as f:
            f.write("ROULETTE QUICK BUG REPORT\n")
            f.write("="*80 + "\n\n")
            for finding in report.findings:
                f.write(finding + "\n")
            f.write("\n\nCONSOLE LOGS:\n")
            for log in report.console_logs:
                f.write(log + "\n")

        print("\n✅ Report saved to: QUICK_BUG_REPORT.txt")

if __name__ == "__main__":
    asyncio.run(quick_investigation())
