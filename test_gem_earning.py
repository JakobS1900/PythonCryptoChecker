#!/usr/bin/env python3
"""
Test script for GEM earning system functionality
"""

import asyncio
import aiohttp
import json
from datetime import datetime

class GemEarningTester:
    def __init__(self, base_url='http://localhost:8000'):
        self.base_url = base_url
        self.session = None
        self.token = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_endpoints(self):
        """Test all GEM earning endpoints"""
        print("🧪 Testing GEM Earning System Endpoints")
        print("=" * 50)

        # Test daily bonus status (unauthenticated)
        print("\n1. Testing daily bonus status (unauthenticated)...")
        try:
            async with self.session.get(f"{self.base_url}/api/gaming/daily-bonus") as resp:
                data = await resp.json()
                print(f"   Status: {resp.status}")
                print(f"   Response: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"   Error: {e}")

        # Test achievements (unauthenticated)
        print("\n2. Testing achievements (unauthenticated)...")
        try:
            async with self.session.get(f"{self.base_url}/api/gaming/achievements") as resp:
                data = await resp.json()
                print(f"   Status: {resp.status}")
                print(f"   Response: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"   Error: {e}")

        # Test emergency tasks (unauthenticated)
        print("\n3. Testing emergency tasks (unauthenticated)...")
        try:
            async with self.session.get(f"{self.base_url}/api/gaming/emergency-tasks") as resp:
                data = await resp.json()
                print(f"   Status: {resp.status}")
                print(f"   Response: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"   Error: {e}")

        # Test server health
        print("\n4. Testing server health...")
        try:
            async with self.session.get(f"{self.base_url}/") as resp:
                print(f"   Status: {resp.status}")
                print(f"   Server is responding")
        except Exception as e:
            print(f"   Error: Server may not be running - {e}")

        print("\n" + "=" * 50)
        print("✅ GEM Earning System endpoint tests completed!")

    async def test_database_models(self):
        """Test database model structure"""
        print("\n🗄️ Testing database model imports...")

        try:
            # Import and test models
            import sys
            import os

            # Add the project root to path
            project_root = os.path.dirname(os.path.abspath(__file__))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            from database.models import (
                DailyBonus, Achievement, UserAchievement,
                EmergencyTask, UserEmergencyTask,
                TransactionType, AchievementType
            )

            print("   ✅ DailyBonus model imported successfully")
            print("   ✅ Achievement model imported successfully")
            print("   ✅ UserAchievement model imported successfully")
            print("   ✅ EmergencyTask model imported successfully")
            print("   ✅ UserEmergencyTask model imported successfully")
            print("   ✅ TransactionType enum imported successfully")
            print("   ✅ AchievementType enum imported successfully")

            # Test enum values
            print(f"\n   📊 Transaction types: {[t.value for t in TransactionType]}")
            print(f"   🏆 Achievement types: {[t.value for t in AchievementType]}")

        except ImportError as e:
            print(f"   ❌ Import error: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")

async def main():
    """Run all tests"""
    print("🎮 GEM Earning System Test Suite")
    print("Starting comprehensive tests...\n")

    # Test database models first
    tester = GemEarningTester()
    await tester.test_database_models()

    # Test API endpoints
    async with GemEarningTester() as tester:
        await tester.test_endpoints()

    print("\n🎯 Test Summary:")
    print("- Database models: ✅ Tested")
    print("- API endpoints: ✅ Tested")
    print("- Frontend integration: Ready for manual testing")
    print("\n📋 Manual Testing Steps:")
    print("1. Start the server: python main.py")
    print("2. Visit: http://localhost:8000/gaming")
    print("3. Look for 'Earn GEM' button in header")
    print("4. Test daily bonus claiming")
    print("5. Check achievement progress")
    print("6. Try emergency tasks when balance is low")

if __name__ == "__main__":
    asyncio.run(main())