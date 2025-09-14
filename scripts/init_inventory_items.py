#!/usr/bin/env python3
"""
Database initialization script for inventory items.
Seeds the database with crypto-themed collectible items.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import Base, init_database, db_manager
from database.unified_models import CollectibleItem
from gamification.item_generator import initialize_collectible_items
from sqlalchemy import select
from logger import logger


async def check_items_exist():
    """Check if collectible items already exist in database."""
    async with db_manager.get_session() as session:
        result = await session.execute(select(CollectibleItem))
        items = result.scalars().all()
        return len(items)


async def initialize_inventory_database():
    """Initialize the inventory system database with collectible items."""
    logger.info("Starting inventory database initialization...")

    try:
        # Check if items already exist
        existing_count = await check_items_exist()

        if existing_count > 0:
            logger.info(f"Database already contains {existing_count} collectible items")
            response = input(f"Found {existing_count} existing items. Reinitialize? (y/N): ")
            if response.lower() != 'y':
                logger.info("Skipping initialization")
                return existing_count

            # Clear existing items if user confirms
            async with db_manager.get_session() as session:
                result = await session.execute(select(CollectibleItem))
                existing_items = result.scalars().all()
                for item in existing_items:
                    await session.delete(item)
                await session.commit()
                logger.info(f"Cleared {len(existing_items)} existing items")

        # Initialize new items
        async with db_manager.get_session() as session:
            items = await initialize_collectible_items(session)

            logger.info("Inventory database initialization completed successfully!")
            logger.info(f"Generated {len(items)} collectible items:")

            # Show summary by type and rarity
            by_type = {}
            by_rarity = {}

            for item in items:
                # Count by type
                item_type = item.item_type
                by_type[item_type] = by_type.get(item_type, 0) + 1

                # Count by rarity
                rarity = item.rarity
                by_rarity[rarity] = by_rarity.get(rarity, 0) + 1

            logger.info("\nItems by Type:")
            for item_type, count in by_type.items():
                logger.info(f"  {item_type}: {count} items")

            logger.info("\nItems by Rarity:")
            for rarity, count in by_rarity.items():
                logger.info(f"  {rarity}: {count} items")

            return len(items)

    except Exception as e:
        logger.error(f"Failed to initialize inventory database: {e}")
        raise


async def verify_initialization():
    """Verify that initialization was successful."""
    logger.info("\nVerifying initialization...")

    async with db_manager.get_session() as session:
        # Check total count
        result = await session.execute(select(CollectibleItem))
        items = result.scalars().all()

        if len(items) == 0:
            logger.error("No items found after initialization!")
            return False

        # Check for each rarity
        rarities = ["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"]
        for rarity in rarities:
            rarity_items = [item for item in items if item.rarity == rarity]
            if len(rarity_items) == 0:
                logger.warning(f"No {rarity} items found")
            else:
                logger.info(f"{len(rarity_items)} {rarity} items found")

        # Check for each type
        types = ["TRADING_CARD", "COSMETIC", "TROPHY", "CONSUMABLE", "SPECIAL"]
        for item_type in types:
            type_items = [item for item in items if item.item_type == item_type]
            if len(type_items) == 0:
                logger.warning(f"No {item_type} items found")
            else:
                logger.info(f"{len(type_items)} {item_type} items found")

        logger.info(f"\nVerification complete: {len(items)} total items successfully initialized")
        return True


async def main():
    """Main initialization function."""
    print("CryptoChecker Gaming Platform - Inventory Database Initialization")
    print("=" * 70)

    try:
        # Initialize database
        await init_database()

        # Initialize collectible items
        item_count = await initialize_inventory_database()

        # Verify initialization
        if await verify_initialization():
            print(f"\nSUCCESS: Inventory system initialized with {item_count} items!")
            print("\nNext Steps:")
            print("  1. Start the server: python run.py")
            print("  2. Visit: http://localhost:8000/inventory")
            print("  3. Test pack opening and item collection")

        else:
            print("\nFAILED: Verification failed after initialization")
            sys.exit(1)

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        logger.error(f"Critical initialization error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())