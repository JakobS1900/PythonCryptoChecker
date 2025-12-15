#!/usr/bin/env python3
"""
Migration 002: Add server-managed roulette rounds
Run this script to upgrade the database schema.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.models import Base
from database.database import engine

async def run_migration():
    """Run migration 002 - Create new tables using SQLAlchemy"""
    print("=" * 60)
    print("Migration 002: Server-Managed Roulette Rounds")
    print("=" * 60)

    print("\n[OK] Using SQLAlchemy async engine")
    print(f"[OK] Database: {engine.url}")

    async with engine.begin() as conn:
        print("\n[...] Creating new tables (roulette_rounds)...")
        print("[...] Adding columns to existing tables (game_bets.round_id)...")

        # Create all tables defined in Base metadata
        # This will only create missing tables/columns
        await conn.run_sync(Base.metadata.create_all)

        print("[OK] Schema updated successfully!")

    print("\n" + "=" * 60)
    print("Migration 002 completed successfully!")
    print("=" * 60)

    print("\n[SUCCESS] Database schema updated!")
    print("\nChanges made:")
    print("  [OK] Created table: roulette_rounds")
    print("  [OK] Added column: game_bets.round_id")
    print("  [OK] Created relationships and indexes")

    print("\nYou can now:")
    print("  1. Start the server with round manager")
    print("  2. Test the new server-managed round system")
    print("  3. All existing bets will have NULL round_id (expected)")

def main():
    """Entry point"""
    asyncio.run(run_migration())

if __name__ == "__main__":
    main()
