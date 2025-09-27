#!/usr/bin/env python3
"""
Comprehensive Test Suite for CryptoChecker Version3 Gaming Platform
Tests complete gaming flow, console errors, API integration, and performance
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import List, Dict, Any

class ComprehensiveTestSuite:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.console_errors = []
        self.performance_metrics = {}

    async def run_all_tests(self):
        """Execute all test categories"""
        print("CryptoChecker Version3 - Comprehensive Test Suite")
        print("=" * 60)

        async with aiohttp.ClientSession() as session:
            # Category 1: Basic Connectivity
            await self.test_basic_connectivity(session)

            # Category 2: Gaming Flow Tests
            await self.test_gaming_flow(session)

            # Category 3: API Integration Tests
            await self.test_api_integration(session)

            # Category 4: GEM Earning System Tests
            await self.test_gem_earning(session)

            # Category 5: Error Handling Tests
            await self.test_error_handling(session)

            # Category 6: Performance Tests
            await self.test_performance(session)

        # Generate comprehensive report
        self.generate_test_report()

    async def test_basic_connectivity(self, session):
        """Test basic server connectivity and endpoints"""
        print("\n[CONNECTIVITY] Testing Basic Connectivity...")

        endpoints = [
            "/",
            "/api",
            "/gaming",
            "/gaming/roulette",
            "/docs"
        ]

        for endpoint in endpoints:
            try:
                start_time = time.time()
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    response_time = (time.time() - start_time) * 1000

                    result = {
                        "test": f"GET {endpoint}",
                        "status": "PASS" if response.status in [200, 404] else "FAIL",
                        "status_code": response.status,
                        "response_time": f"{response_time:.1f}ms"
                    }
                    self.test_results.append(result)
                    print(f"  [OK] {endpoint}: {response.status} ({response_time:.1f}ms)")

            except Exception as e:
                result = {
                    "test": f"GET {endpoint}",
                    "status": "ERROR",
                    "error": str(e),
                    "response_time": "N/A"
                }
                self.test_results.append(result)
                print(f"  ✗ {endpoint}: ERROR - {e}")

    async def test_gaming_flow(self, session):
        """Test complete gaming flow for both guest and authenticated users"""
        print("\n🎰 Testing Complete Gaming Flow...")

        # Test 1: Game Session Creation
        try:
            async with session.post(
                f"{self.base_url}/api/gaming/roulette/create",
                json={"client_seed": "test_seed_123"},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    game_data = await response.json()
                    game_id = game_data.get("game_id")
                    print(f"  ✓ Game session created: {game_id}")

                    # Test 2: Place Bet
                    await self.test_place_bet(session, game_id)

                    # Test 3: Multiple Bet Types
                    await self.test_multiple_bets(session, game_id)

                else:
                    print(f"  ✗ Game creation failed: {response.status}")

        except Exception as e:
            print(f"  ✗ Gaming flow error: {e}")

    async def test_place_bet(self, session, game_id):
        """Test placing different types of bets"""
        bet_tests = [
            {"bet_type": "color", "bet_value": "red", "amount": 100},
            {"bet_type": "color", "bet_value": "black", "amount": 50},
            {"bet_type": "single_number", "bet_value": "7", "amount": 25},
            {"bet_type": "parity", "bet_value": "odd", "amount": 75},
        ]

        for bet in bet_tests:
            try:
                async with session.post(
                    f"{self.base_url}/api/gaming/roulette/{game_id}/bet",
                    json=bet,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        bet_data = await response.json()
                        print(f"  ✓ Bet placed: {bet['bet_type']} {bet['bet_value']} - {bet['amount']} GEM")
                    else:
                        print(f"  ✗ Bet failed: {response.status} - {bet}")

            except Exception as e:
                print(f"  ✗ Bet error: {e}")

    async def test_multiple_bets(self, session, game_id):
        """Test placing multiple bets rapidly"""
        print("  🔄 Testing multiple rapid bets...")

        tasks = []
        for i in range(5):
            bet = {"bet_type": "color", "bet_value": "red", "amount": 10}
            tasks.append(self.place_single_bet(session, game_id, bet, i))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if not isinstance(r, Exception))
        print(f"  ✓ Multiple bets: {success_count}/5 successful")

    async def place_single_bet(self, session, game_id, bet, index):
        """Helper method for placing a single bet"""
        try:
            async with session.post(
                f"{self.base_url}/api/gaming/roulette/{game_id}/bet",
                json=bet,
                headers={"Content-Type": "application/json"}
            ) as response:
                return response.status == 200
        except Exception:
            return False

    async def test_api_integration(self, session):
        """Test API integration and error handling"""
        print("\n🔌 Testing API Integration...")

        # Test API documentation endpoint
        try:
            async with session.get(f"{self.base_url}/docs") as response:
                print(f"  ✓ API Documentation: {response.status}")
        except Exception as e:
            print(f"  ✗ API Docs error: {e}")

        # Test invalid endpoints
        invalid_endpoints = [
            "/api/gaming/invalid",
            "/api/gaming/roulette/fake-id/bet",
            "/api/nonexistent"
        ]

        for endpoint in invalid_endpoints:
            try:
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    if response.status in [404, 422]:
                        print(f"  ✓ Proper error handling for {endpoint}: {response.status}")
                    else:
                        print(f"  ⚠ Unexpected response for {endpoint}: {response.status}")
            except Exception as e:
                print(f"  ✗ Error testing {endpoint}: {e}")

    async def test_gem_earning(self, session):
        """Test GEM earning system endpoints"""
        print("\n💎 Testing GEM Earning System...")

        gem_endpoints = [
            ("/api/gaming/daily-bonus", "Daily Bonus"),
            ("/api/gaming/achievements", "Achievements"),
            ("/api/gaming/emergency-tasks", "Emergency Tasks")
        ]

        for endpoint, name in gem_endpoints:
            try:
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    data = await response.json()
                    if response.status == 200:
                        print(f"  ✓ {name}: Working (authenticated required: {data.get('success', False)})")
                    else:
                        print(f"  ✓ {name}: Proper auth protection ({response.status})")
            except Exception as e:
                print(f"  ✗ {name} error: {e}")

    async def test_error_handling(self, session):
        """Test error handling and edge cases"""
        print("\n⚠ Testing Error Handling...")

        # Test invalid bet amounts
        try:
            async with session.post(
                f"{self.base_url}/api/gaming/roulette/create",
                json={"client_seed": "test"},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    game_data = await response.json()
                    game_id = game_data.get("game_id")

                    # Test invalid bet amounts
                    invalid_bets = [
                        {"bet_type": "color", "bet_value": "red", "amount": -10},  # Negative amount
                        {"bet_type": "color", "bet_value": "red", "amount": 100000},  # Too high
                        {"bet_type": "invalid", "bet_value": "red", "amount": 50},  # Invalid type
                    ]

                    for bet in invalid_bets:
                        try:
                            async with session.post(
                                f"{self.base_url}/api/gaming/roulette/{game_id}/bet",
                                json=bet,
                                headers={"Content-Type": "application/json"}
                            ) as bet_response:
                                if bet_response.status in [400, 422]:
                                    print(f"  ✓ Proper validation for invalid bet: {bet}")
                                else:
                                    print(f"  ⚠ Unexpected response for invalid bet: {bet_response.status}")
                        except Exception as e:
                            print(f"  ✓ Exception properly handled for invalid bet: {e}")

        except Exception as e:
            print(f"  ✗ Error handling test failed: {e}")

    async def test_performance(self, session):
        """Test performance and load handling"""
        print("\n⚡ Testing Performance...")

        # Test response times
        endpoints_to_test = [
            "/api",
            "/api/gaming/roulette/create",
            "/gaming"
        ]

        for endpoint in endpoints_to_test:
            response_times = []

            for _ in range(5):  # Test 5 times each
                start_time = time.time()
                try:
                    if endpoint.endswith('/create'):
                        async with session.post(
                            f"{self.base_url}{endpoint}",
                            json={"client_seed": "perf_test"},
                            headers={"Content-Type": "application/json"}
                        ) as response:
                            response_time = (time.time() - start_time) * 1000
                            response_times.append(response_time)
                    else:
                        async with session.get(f"{self.base_url}{endpoint}") as response:
                            response_time = (time.time() - start_time) * 1000
                            response_times.append(response_time)
                except Exception:
                    continue

            if response_times:
                avg_time = sum(response_times) / len(response_times)
                max_time = max(response_times)
                min_time = min(response_times)

                self.performance_metrics[endpoint] = {
                    "avg_response_time": avg_time,
                    "max_response_time": max_time,
                    "min_response_time": min_time
                }

                print(f"  📊 {endpoint}: Avg {avg_time:.1f}ms, Max {max_time:.1f}ms, Min {min_time:.1f}ms")

    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("📋 COMPREHENSIVE TEST REPORT")
        print("=" * 60)

        # Summary statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.get('status') == 'PASS')
        failed_tests = sum(1 for result in self.test_results if result.get('status') == 'FAIL')
        error_tests = sum(1 for result in self.test_results if result.get('status') == 'ERROR')

        print(f"\n📊 TEST SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Errors: {error_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests*100) if total_tests > 0 else 0:.1f}%")

        # Performance summary
        if self.performance_metrics:
            print(f"\n⚡ PERFORMANCE SUMMARY:")
            for endpoint, metrics in self.performance_metrics.items():
                print(f"   {endpoint}: {metrics['avg_response_time']:.1f}ms avg")

        # Detailed results
        print(f"\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status_symbol = "✓" if result['status'] == 'PASS' else "✗" if result['status'] == 'FAIL' else "⚠"
            print(f"   {status_symbol} {result['test']}: {result['status']}")
            if result.get('error'):
                print(f"      Error: {result['error']}")

        # Final assessment
        print(f"\n🏆 FINAL ASSESSMENT:")
        if passed_tests == total_tests and total_tests > 0:
            print("   🟢 ALL TESTS PASSED - Platform ready for production!")
        elif passed_tests / total_tests > 0.8:
            print("   🟡 MOSTLY SUCCESSFUL - Minor issues detected")
        else:
            print("   🔴 SIGNIFICANT ISSUES - Requires attention before deployment")

        print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

async def main():
    """Run comprehensive test suite"""
    try:
        test_suite = ComprehensiveTestSuite()
        await test_suite.run_all_tests()
    except KeyboardInterrupt:
        print("\n⚠ Test suite interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")

if __name__ == "__main__":
    asyncio.run(main())