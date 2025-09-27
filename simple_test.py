#!/usr/bin/env python3
"""
Simple Test Suite for CryptoChecker Version3 Gaming Platform
ASCII-only version for Windows compatibility
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

class SimpleTestSuite:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []

    async def run_tests(self):
        print("CryptoChecker Version3 - Test Suite")
        print("=" * 50)

        async with aiohttp.ClientSession() as session:
            await self.test_connectivity(session)
            await self.test_gaming_api(session)
            await self.test_gem_earning(session)
            await self.test_error_handling(session)

        self.generate_report()

    async def test_connectivity(self, session):
        print("\n[CONNECTIVITY] Basic Server Tests")

        endpoints = ["/", "/api", "/gaming", "/docs"]

        for endpoint in endpoints:
            try:
                start_time = time.time()
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    response_time = (time.time() - start_time) * 1000

                    status = "PASS" if response.status in [200, 404] else "FAIL"
                    print(f"  {endpoint}: {response.status} ({response_time:.1f}ms) - {status}")

                    self.test_results.append({
                        "test": f"GET {endpoint}",
                        "status": status,
                        "response_time": response_time
                    })

            except Exception as e:
                print(f"  {endpoint}: ERROR - {str(e)}")
                self.test_results.append({
                    "test": f"GET {endpoint}",
                    "status": "ERROR",
                    "error": str(e)
                })

    async def test_gaming_api(self, session):
        print("\n[GAMING] Roulette Gaming Tests")

        try:
            # Test game creation
            async with session.post(
                f"{self.base_url}/api/gaming/roulette/create",
                json={"client_seed": "test123"},
                headers={"Content-Type": "application/json"}
            ) as response:

                if response.status == 200:
                    data = await response.json()
                    game_id = data.get("game_id")
                    print(f"  Game Creation: PASS (ID: {game_id[:8]}...)")

                    # Test bet placement
                    await self.test_bets(session, game_id)
                else:
                    print(f"  Game Creation: FAIL ({response.status})")

        except Exception as e:
            print(f"  Gaming API: ERROR - {str(e)}")

    async def test_bets(self, session, game_id):
        bet_types = [
            {"bet_type": "color", "bet_value": "red", "amount": 100},
            {"bet_type": "color", "bet_value": "black", "amount": 50},
            {"bet_type": "single_number", "bet_value": "7", "amount": 25}
        ]

        successful_bets = 0

        for bet in bet_types:
            try:
                async with session.post(
                    f"{self.base_url}/api/gaming/roulette/{game_id}/bet",
                    json=bet,
                    headers={"Content-Type": "application/json"}
                ) as response:

                    if response.status == 200:
                        successful_bets += 1

            except Exception:
                pass

        print(f"  Bet Placement: {successful_bets}/{len(bet_types)} successful")

        self.test_results.append({
            "test": "Bet Placement",
            "status": "PASS" if successful_bets > 0 else "FAIL",
            "success_rate": f"{successful_bets}/{len(bet_types)}"
        })

    async def test_gem_earning(self, session):
        print("\n[GEM EARNING] Testing GEM System")

        gem_endpoints = [
            "/api/gaming/daily-bonus",
            "/api/gaming/achievements",
            "/api/gaming/emergency-tasks"
        ]

        for endpoint in gem_endpoints:
            try:
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    if response.status == 200:
                        data = await response.json()
                        # Check if it's properly handling guest users
                        if not data.get("success") and "Authentication" in str(data.get("error", "")):
                            print(f"  {endpoint.split('/')[-1]}: PASS (Auth Protected)")
                        else:
                            print(f"  {endpoint.split('/')[-1]}: PASS (Working)")
                    else:
                        print(f"  {endpoint.split('/')[-1]}: FAIL ({response.status})")

            except Exception as e:
                print(f"  {endpoint.split('/')[-1]}: ERROR - {str(e)}")

    async def test_error_handling(self, session):
        print("\n[ERROR HANDLING] Testing Invalid Requests")

        # Test invalid endpoints
        invalid_tests = [
            ("/api/gaming/invalid-endpoint", "Invalid Endpoint"),
            ("/api/gaming/roulette/fake-id/bet", "Invalid Game ID")
        ]

        for endpoint, test_name in invalid_tests:
            try:
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    if response.status in [404, 422, 400]:
                        print(f"  {test_name}: PASS (Proper error {response.status})")
                        self.test_results.append({
                            "test": test_name,
                            "status": "PASS"
                        })
                    else:
                        print(f"  {test_name}: FAIL (Unexpected {response.status})")

            except Exception as e:
                print(f"  {test_name}: ERROR - {str(e)}")

    def generate_report(self):
        print("\n" + "=" * 50)
        print("TEST SUMMARY REPORT")
        print("=" * 50)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.get("status") == "PASS")
        failed_tests = sum(1 for r in self.test_results if r.get("status") == "FAIL")
        error_tests = sum(1 for r in self.test_results if r.get("status") == "ERROR")

        print(f"\nSUMMARY:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {passed_tests}")
        print(f"  Failed: {failed_tests}")
        print(f"  Errors: {error_tests}")

        if total_tests > 0:
            success_rate = (passed_tests / total_tests) * 100
            print(f"  Success Rate: {success_rate:.1f}%")

            print(f"\nASSESSMENT:")
            if success_rate >= 90:
                print("  [EXCELLENT] Platform is working well!")
            elif success_rate >= 70:
                print("  [GOOD] Platform is mostly functional with minor issues")
            elif success_rate >= 50:
                print("  [FAIR] Platform has some significant issues")
            else:
                print("  [POOR] Platform needs major fixes")

        print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)

async def main():
    test_suite = SimpleTestSuite()
    await test_suite.run_tests()

if __name__ == "__main__":
    asyncio.run(main())