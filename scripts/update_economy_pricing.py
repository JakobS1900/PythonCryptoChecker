#!/usr/bin/env python3
"""
Economy rebalancing script for CryptoChecker platform.
Updates existing item prices to the new balanced economy (1,000 GEM = $10 USD).
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import db_manager
from database.unified_models import CollectibleItem, ItemRarity
from sqlalchemy import select, update
from logger import logger


# New pricing structure based on 1,000 GEM = $10 USD
NEW_PRICING = {
    "COMMON": 300.0,      # $3.00 equivalent - reasonable for common items
    "UNCOMMON": 750.0,    # $7.50 equivalent - decent value for uncommon
    "RARE": 1500.0,       # $15.00 equivalent - good value for rare items
    "EPIC": 3000.0,       # $30.00 equivalent - premium pricing for epic
    "LEGENDARY": 6000.0   # $60.00 equivalent - luxury pricing for legendary
}

# Old pricing for reference
OLD_PRICING = {
    "COMMON": 10.0,
    "UNCOMMON": 50.0,
    "RARE": 200.0,
    "EPIC": 1000.0,
    "LEGENDARY": 5000.0
}


async def analyze_current_pricing():
    """Analyze current item pricing in the database."""
    logger.info("Analyzing current item pricing...")

    async with db_manager.get_session() as session:
        result = await session.execute(select(CollectibleItem))
        items = result.scalars().all()

        if not items:
            logger.warning("No items found in database")
            return {}

        pricing_analysis = {}
        for item in items:
            rarity = item.rarity
            if rarity not in pricing_analysis:
                pricing_analysis[rarity] = {
                    "count": 0,
                    "current_prices": [],
                    "expected_price": NEW_PRICING.get(rarity, 0.0)
                }

            pricing_analysis[rarity]["count"] += 1
            pricing_analysis[rarity]["current_prices"].append(item.gem_value)

        logger.info(f"Found {len(items)} items across {len(pricing_analysis)} rarities")

        for rarity, data in pricing_analysis.items():
            unique_prices = set(data["current_prices"])
            logger.info(f"{rarity}: {data['count']} items, prices: {unique_prices}, target: {data['expected_price']} GEM")

        return pricing_analysis


async def update_item_pricing():
    """Update all items to new pricing structure."""
    logger.info("Starting economy rebalancing update...")

    updated_count = 0
    skipped_count = 0

    async with db_manager.get_session() as session:
        for rarity, new_price in NEW_PRICING.items():
            logger.info(f"Updating {rarity} items to {new_price} GEM...")

            # Update all items of this rarity
            result = await session.execute(
                update(CollectibleItem)
                .where(CollectibleItem.rarity == rarity)
                .values(gem_value=new_price)
            )

            items_updated = result.rowcount
            updated_count += items_updated
            logger.info(f"Updated {items_updated} {rarity} items")

        await session.commit()
        logger.info(f"Economy rebalancing completed: {updated_count} items updated")

        return updated_count


async def verify_pricing_update():
    """Verify that all items have been updated correctly."""
    logger.info("Verifying pricing update...")

    async with db_manager.get_session() as session:
        result = await session.execute(select(CollectibleItem))
        items = result.scalars().all()

        verification_results = {}
        errors = []

        for item in items:
            rarity = item.rarity
            expected_price = NEW_PRICING.get(rarity)
            actual_price = item.gem_value

            if rarity not in verification_results:
                verification_results[rarity] = {
                    "correct": 0,
                    "incorrect": 0,
                    "expected": expected_price
                }

            if actual_price == expected_price:
                verification_results[rarity]["correct"] += 1
            else:
                verification_results[rarity]["incorrect"] += 1
                errors.append(f"Item {item.name} ({item.id}): expected {expected_price}, got {actual_price}")

        # Report verification results
        all_correct = True
        for rarity, results in verification_results.items():
            total = results["correct"] + results["incorrect"]
            logger.info(f"{rarity}: {results['correct']}/{total} correct (expected: {results['expected']} GEM)")
            if results["incorrect"] > 0:
                all_correct = False

        if errors:
            logger.error(f"Found {len(errors)} pricing errors:")
            for error in errors[:10]:  # Show first 10 errors
                logger.error(f"  {error}")
            if len(errors) > 10:
                logger.error(f"  ... and {len(errors) - 10} more errors")

        return all_correct


async def create_pricing_backup():
    """Create a backup of current pricing before making changes."""
    logger.info("Creating pricing backup...")

    backup_data = []

    async with db_manager.get_session() as session:
        result = await session.execute(select(CollectibleItem))
        items = result.scalars().all()

        for item in items:
            backup_data.append({
                "id": item.id,
                "name": item.name,
                "rarity": item.rarity,
                "old_gem_value": item.gem_value,
                "new_gem_value": NEW_PRICING.get(item.rarity, item.gem_value)
            })

    # Write backup to file
    backup_file = Path(__file__).parent / "pricing_backup.json"
    import json

    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)

    logger.info(f"Pricing backup saved to: {backup_file}")
    return len(backup_data)


async def main():
    """Main function for economy rebalancing."""
    print("CryptoChecker Economy Rebalancing Tool")
    print("=" * 50)
    print("New Economy Standard: 1,000 GEM = $10.00 USD")
    print("")
    print("Pricing Changes:")
    for rarity in ["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"]:
        old_price = OLD_PRICING[rarity]
        new_price = NEW_PRICING[rarity]
        usd_equivalent = new_price / 100  # 1000 GEM = $10, so divide by 100
        print(f"  {rarity:10}: {old_price:>6.0f} GEM -> {new_price:>6.0f} GEM (${usd_equivalent:.2f})")
    print("")

    try:
        # Step 1: Analyze current pricing
        current_analysis = await analyze_current_pricing()

        if not current_analysis:
            print("No items found in database. Please run item initialization first.")
            return

        # Step 2: Create backup
        backup_count = await create_pricing_backup()
        print(f"✓ Created backup of {backup_count} item prices")

        # Step 3: Confirm update
        response = input("\nProceed with economy rebalancing? (y/N): ")
        if response.lower() != 'y':
            print("Update cancelled.")
            return

        # Step 4: Update pricing
        updated_count = await update_item_pricing()
        print(f"✓ Updated pricing for {updated_count} items")

        # Step 5: Verify update
        if await verify_pricing_update():
            print("✓ All items successfully updated to new pricing")
            print("")
            print("ECONOMY REBALANCING COMPLETED SUCCESSFULLY!")
            print("")
            print("Changes made:")
            print("  • All item prices updated to balanced economy")
            print("  • Sell prices now provide meaningful returns")
            print("  • Pack values properly balanced for engagement")
            print("")
            print("Next steps:")
            print("  1. Test the /api/inventory endpoints")
            print("  2. Verify pack opening with new prices")
            print("  3. Test item selling functionality")
            print("  4. Check frontend inventory display")
        else:
            print("⚠ Some items may not have been updated correctly. Check logs.")

    except Exception as e:
        logger.error(f"Economy rebalancing failed: {e}")
        print(f"ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)