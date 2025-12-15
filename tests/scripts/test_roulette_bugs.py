"""
Comprehensive Playwright Test Suite for Roulette Game Bug Investigation
Tests 5 critical scenarios to identify betting, timer, and SSE connection issues
"""

import asyncio
import time
import json
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

class RouletteTestReport:
    def __init__(self):
        self.findings = []
        self.screenshots = []
        self.console_logs = []
        self.network_logs = []
        self.timings = {}

    def add_finding(self, scenario, description, severity="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.findings.append({
            "time": timestamp,
            "scenario": scenario,
            "severity": severity,
            "description": description
        })
        print(f"[{timestamp}] [{severity}] {scenario}: {description}")

    def add_screenshot(self, scenario, path):
        self.screenshots.append({"scenario": scenario, "path": path})

    def generate_report(self):
        print("\n" + "="*80)
        print("ROULETTE GAME BUG INVESTIGATION REPORT")
        print("="*80)
        print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total findings: {len(self.findings)}")
        print(f"Screenshots captured: {len(self.screenshots)}")
        print(f"Console logs: {len(self.console_logs)}")
        print(f"Network requests: {len(self.network_logs)}")

        print("\n" + "-"*80)
        print("DETAILED FINDINGS BY SCENARIO")
        print("-"*80)

        scenarios = {}
        for finding in self.findings:
            scenario = finding["scenario"]
            if scenario not in scenarios:
                scenarios[scenario] = []
            scenarios[scenario].append(finding)

        for scenario, findings in scenarios.items():
            print(f"\n### {scenario}")
            for finding in findings:
                severity_marker = {
                    "CRITICAL": "🔴",
                    "WARNING": "⚠️",
                    "INFO": "ℹ️"
                }.get(finding["severity"], "•")
                print(f"  {severity_marker} [{finding['time']}] {finding['description']}")

        if self.console_logs:
            print("\n" + "-"*80)
            print("CONSOLE ERRORS AND WARNINGS")
            print("-"*80)
            for log in self.console_logs[:50]:  # Limit to first 50
                print(f"  [{log['type']}] {log['text']}")

        if self.screenshots:
            print("\n" + "-"*80)
            print("SCREENSHOTS CAPTURED")
            print("-"*80)
            for screenshot in self.screenshots:
                print(f"  {screenshot['scenario']}: {screenshot['path']}")

        print("\n" + "="*80)

report = RouletteTestReport()

async def setup_page_monitoring(page: Page):
    """Set up console and network monitoring"""

    page.on("console", lambda msg: report.console_logs.append({
        "type": msg.type,
        "text": msg.text,
        "time": datetime.now().strftime("%H:%M:%S.%f")[:-3]
    }))

    page.on("pageerror", lambda err: report.add_finding(
        "PAGE ERROR",
        f"Uncaught exception: {err}",
        "CRITICAL"
    ))

    page.on("request", lambda req: report.network_logs.append({
        "type": "request",
        "method": req.method,
        "url": req.url,
        "time": datetime.now().strftime("%H:%M:%S.%f")[:-3]
    }))

    page.on("response", lambda res: report.network_logs.append({
        "type": "response",
        "status": res.status,
        "url": res.url,
        "time": datetime.now().strftime("%H:%M:%S.%f")[:-3]
    }))

async def test_scenario_1_fresh_page_load(page: Page):
    """Test Scenario 1: Fresh Page Load"""
    report.add_finding("SCENARIO 1", "Starting fresh page load test")

    start_time = time.time()

    # Navigate to gaming page
    await page.goto("http://localhost:8000/gaming", wait_until="domcontentloaded")
    dom_loaded = time.time() - start_time
    report.add_finding("SCENARIO 1", f"DOM loaded in {dom_loaded:.2f}s")

    # Take initial screenshot
    await page.screenshot(path="test_1_initial_load.png")
    report.add_screenshot("SCENARIO 1", "test_1_initial_load.png")

    # Check for loading states
    loading_indicators = await page.locator("text=Loading").all()
    if loading_indicators:
        report.add_finding("SCENARIO 1", f"Found {len(loading_indicators)} loading indicators", "WARNING")

    # Wait for timer to appear
    try:
        timer = page.locator("#auto-spin-timer, .timer, [data-timer]").first
        await timer.wait_for(timeout=5000)
        timer_appear_time = time.time() - start_time
        report.add_finding("SCENARIO 1", f"Timer appeared after {timer_appear_time:.2f}s")

        # Get timer value
        timer_text = await timer.text_content()
        report.add_finding("SCENARIO 1", f"Initial timer value: {timer_text}")

        # Check if timer is stuck at 15.0s
        await page.wait_for_timeout(2000)
        timer_text_after = await timer.text_content()
        report.add_finding("SCENARIO 1", f"Timer value after 2s: {timer_text_after}")

        if timer_text == timer_text_after:
            report.add_finding("SCENARIO 1", "Timer appears to be STUCK!", "CRITICAL")
    except Exception as e:
        report.add_finding("SCENARIO 1", f"Timer not found: {e}", "CRITICAL")

    # Check when betting is enabled
    try:
        bet_button = page.locator("button:has-text('BET'), button:has-text('Place Bet')").first
        is_disabled = await bet_button.is_disabled()
        interactive_time = time.time() - start_time

        report.add_finding("SCENARIO 1", f"Page interactive after {interactive_time:.2f}s")
        report.add_finding("SCENARIO 1", f"Bet button disabled: {is_disabled}")
    except Exception as e:
        report.add_finding("SCENARIO 1", f"Bet button not found: {e}", "WARNING")

    # Take screenshot after initial checks
    await page.screenshot(path="test_1_after_checks.png")
    report.add_screenshot("SCENARIO 1", "test_1_after_checks.png")

    report.timings["page_load"] = dom_loaded

async def test_scenario_2_betting_attempt(page: Page):
    """Test Scenario 2: Betting Attempt"""
    report.add_finding("SCENARIO 2", "Starting betting attempt test")

    # Wait for page to fully load
    await page.wait_for_timeout(3000)

    # Take screenshot before betting
    await page.screenshot(path="test_2_before_bet.png")
    report.add_screenshot("SCENARIO 2", "test_2_before_bet.png")

    try:
        # Try to find and click RED bet option
        red_option = page.locator("button:has-text('RED'), .bet-option:has-text('RED'), [data-color='red']").first
        await red_option.wait_for(timeout=5000)

        report.add_finding("SCENARIO 2", "Found RED bet option")

        is_clickable = await red_option.is_enabled()
        report.add_finding("SCENARIO 2", f"RED option clickable: {is_clickable}")

        # Try to click it
        console_logs_before = len(report.console_logs)
        network_logs_before = len(report.network_logs)

        await red_option.click()
        report.add_finding("SCENARIO 2", "Clicked RED bet option")

        # Wait for any response
        await page.wait_for_timeout(1000)

        console_logs_after = len(report.console_logs)
        network_logs_after = len(report.network_logs)

        report.add_finding("SCENARIO 2", f"Console logs generated: {console_logs_after - console_logs_before}")
        report.add_finding("SCENARIO 2", f"Network requests made: {network_logs_after - network_logs_before}")

        # Check for error messages
        error_messages = await page.locator(".error, .alert-danger, [role='alert']").all()
        if error_messages:
            for error in error_messages:
                error_text = await error.text_content()
                report.add_finding("SCENARIO 2", f"Error message: {error_text}", "WARNING")

        # Check game phase/state
        game_state = await page.evaluate("""() => {
            return {
                gameState: window.gameState,
                currentPhase: window.currentPhase,
                canBet: window.canBet,
                betPlaced: window.betPlaced
            }
        }""")
        report.add_finding("SCENARIO 2", f"Game state: {json.dumps(game_state, indent=2)}")

    except Exception as e:
        report.add_finding("SCENARIO 2", f"Failed to place bet: {e}", "CRITICAL")

    # Take screenshot after betting attempt
    await page.screenshot(path="test_2_after_bet.png")
    report.add_screenshot("SCENARIO 2", "test_2_after_bet.png")

async def test_scenario_3_timer_observation(page: Page):
    """Test Scenario 3: Timer Observation"""
    report.add_finding("SCENARIO 3", "Starting 30-second timer observation")

    try:
        timer = page.locator("#auto-spin-timer, .timer, [data-timer]").first

        # Record timer values over 30 seconds
        timer_values = []
        for i in range(15):  # Check every 2 seconds for 30 seconds
            try:
                timer_text = await timer.text_content()
                timer_html = await timer.inner_html()
                timer_values.append({
                    "time": i * 2,
                    "text": timer_text,
                    "html": timer_html
                })
                report.add_finding("SCENARIO 3", f"t={i*2}s: Timer shows '{timer_text}'")
                await page.wait_for_timeout(2000)
            except Exception as e:
                report.add_finding("SCENARIO 3", f"Error reading timer at t={i*2}s: {e}", "WARNING")

        # Analyze timer behavior
        unique_values = set(tv["text"] for tv in timer_values)
        if len(unique_values) == 1:
            report.add_finding("SCENARIO 3", f"Timer is STUCK at value: {list(unique_values)[0]}", "CRITICAL")
        else:
            report.add_finding("SCENARIO 3", f"Timer changed {len(unique_values)} times during observation")

        # Check DOM updates
        dom_timer_info = await page.evaluate("""() => {
            const timer = document.querySelector('#auto-spin-timer, .timer, [data-timer]');
            return {
                innerHTML: timer ? timer.innerHTML : null,
                textContent: timer ? timer.textContent : null,
                classList: timer ? Array.from(timer.classList) : null,
                attributes: timer ? Array.from(timer.attributes).map(a => ({name: a.name, value: a.value})) : null
            }
        }""")
        report.add_finding("SCENARIO 3", f"Timer DOM state: {json.dumps(dom_timer_info, indent=2)}")

    except Exception as e:
        report.add_finding("SCENARIO 3", f"Timer observation failed: {e}", "CRITICAL")

    # Take screenshot after observation
    await page.screenshot(path="test_3_timer_observation.png")
    report.add_screenshot("SCENARIO 3", "test_3_timer_observation.png")

async def test_scenario_4_sse_connection(page: Page):
    """Test Scenario 4: SSE Connection"""
    report.add_finding("SCENARIO 4", "Starting SSE connection analysis")

    # Check for EventSource connections
    sse_info = await page.evaluate("""() => {
        return {
            eventSourceExists: typeof EventSource !== 'undefined',
            activeConnections: window.eventSource ? {
                url: window.eventSource.url,
                readyState: window.eventSource.readyState,
                readyStateText: ['CONNECTING', 'OPEN', 'CLOSED'][window.eventSource.readyState]
            } : null,
            pollingFallback: window.pollingActive || false
        }
    }""")
    report.add_finding("SCENARIO 4", f"SSE Info: {json.dumps(sse_info, indent=2)}")

    # Filter SSE-related network logs
    sse_requests = [log for log in report.network_logs if 'stream' in log.get('url', '').lower() or 'sse' in log.get('url', '').lower() or 'events' in log.get('url', '').lower()]

    if sse_requests:
        report.add_finding("SCENARIO 4", f"Found {len(sse_requests)} SSE-related requests")
        for req in sse_requests[:10]:
            report.add_finding("SCENARIO 4", f"  {req.get('method')} {req.get('url')} - Status: {req.get('status', 'pending')}")
    else:
        report.add_finding("SCENARIO 4", "No SSE connections found!", "WARNING")

    # Check console for SSE-related messages
    sse_console = [log for log in report.console_logs if 'sse' in log['text'].lower() or 'eventsource' in log['text'].lower() or 'stream' in log['text'].lower()]
    if sse_console:
        report.add_finding("SCENARIO 4", f"Found {len(sse_console)} SSE-related console messages")
        for log in sse_console[:10]:
            report.add_finding("SCENARIO 4", f"  [{log['type']}] {log['text']}")

    # Take screenshot
    await page.screenshot(path="test_4_sse_connection.png")
    report.add_screenshot("SCENARIO 4", "test_4_sse_connection.png")

async def test_scenario_5_page_refresh(page: Page):
    """Test Scenario 5: Page Refresh"""
    report.add_finding("SCENARIO 5", "Starting page refresh test")

    # Clear console logs to separate first load from refresh
    initial_console_count = len(report.console_logs)
    initial_network_count = len(report.network_logs)

    # Refresh the page
    start_time = time.time()
    await page.reload(wait_until="domcontentloaded")
    reload_time = time.time() - start_time

    report.add_finding("SCENARIO 5", f"Page reloaded in {reload_time:.2f}s")

    # Wait for stabilization
    await page.wait_for_timeout(3000)

    # Take screenshot after refresh
    await page.screenshot(path="test_5_after_refresh.png")
    report.add_screenshot("SCENARIO 5", "test_5_after_refresh.png")

    # Compare behavior
    console_after_refresh = len(report.console_logs) - initial_console_count
    network_after_refresh = len(report.network_logs) - initial_network_count

    report.add_finding("SCENARIO 5", f"Console logs on refresh: {console_after_refresh}")
    report.add_finding("SCENARIO 5", f"Network requests on refresh: {network_after_refresh}")

    # Check timer again
    try:
        timer = page.locator("#auto-spin-timer, .timer, [data-timer]").first
        timer_text = await timer.text_content()
        report.add_finding("SCENARIO 5", f"Timer value after refresh: {timer_text}")

        # Wait and check again
        await page.wait_for_timeout(2000)
        timer_text_after = await timer.text_content()
        if timer_text == timer_text_after:
            report.add_finding("SCENARIO 5", "Timer STILL stuck after refresh!", "CRITICAL")
        else:
            report.add_finding("SCENARIO 5", "Timer working after refresh")
    except Exception as e:
        report.add_finding("SCENARIO 5", f"Timer check failed: {e}", "WARNING")

async def run_all_tests():
    """Run all test scenarios"""
    async with async_playwright() as p:
        # Launch browser with debugging capabilities
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir="test_videos"
        )

        page = await context.new_page()

        # Set up monitoring
        await setup_page_monitoring(page)

        try:
            # Run all test scenarios
            await test_scenario_1_fresh_page_load(page)
            await test_scenario_2_betting_attempt(page)
            await test_scenario_3_timer_observation(page)
            await test_scenario_4_sse_connection(page)
            await test_scenario_5_page_refresh(page)

        except Exception as e:
            report.add_finding("TEST EXECUTION", f"Test failed with error: {e}", "CRITICAL")

        finally:
            # Close browser
            await context.close()
            await browser.close()

        # Generate final report
        report.generate_report()

        # Save detailed report to file
        with open("ROULETTE_BUG_TEST_REPORT.md", "w") as f:
            f.write("# Roulette Game Bug Investigation Report\n\n")
            f.write(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Executive Summary\n\n")
            f.write(f"- Total Findings: {len(report.findings)}\n")
            f.write(f"- Screenshots Captured: {len(report.screenshots)}\n")
            f.write(f"- Console Logs: {len(report.console_logs)}\n")
            f.write(f"- Network Requests: {len(report.network_logs)}\n\n")

            f.write("## Detailed Findings\n\n")
            for finding in report.findings:
                f.write(f"**[{finding['time']}] {finding['scenario']}** ({finding['severity']})\n")
                f.write(f"{finding['description']}\n\n")

            f.write("\n## Console Logs (First 100)\n\n")
            for log in report.console_logs[:100]:
                f.write(f"- [{log['type']}] {log['text']}\n")

            f.write("\n## Screenshots\n\n")
            for screenshot in report.screenshots:
                f.write(f"- {screenshot['scenario']}: `{screenshot['path']}`\n")

        print("\n✅ Detailed report saved to: ROULETTE_BUG_TEST_REPORT.md")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
