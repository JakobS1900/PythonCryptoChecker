#!/usr/bin/env python3
"""
Quick test script to initialize and test the bot gambling system.
"""

import asyncio
from api.bot_system import initialize_bot_population, get_bot_population_stats

async def test_bots():
    """Test the bot system."""
    print("🎰 Testing CryptoChecker Bot System")

    # Initialize bots
    print("🤖 Initializing bot population...")
    await initialize_bot_population(num_bots=22)

    # Get stats
    print("📊 Getting bot population stats...")
    stats = await get_bot_population_stats()

    print("✅ Bot System Test Results:")
    print(f"   Total Bots: {stats['total_bots']}")
    print(f"   Average Balance: {stats['average_balance']:.2f} GEM")
    print("   Personality Distribution:")
    for personality, count in stats['personalities'].items():
        print(f"      {personality}: {count} bots")

    print("\n🎯 Bot system successfully initialized!")
    print("💡 Bots are now available to populate gambling rooms with realistic betting behavior.")
if __name__ == "__main__":
    asyncio.run(test_bots())
