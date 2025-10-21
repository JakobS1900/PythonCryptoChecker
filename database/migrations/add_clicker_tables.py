"""
Database migration: Add clicker system tables
Creates ClickerStats and ClickerUpgradePurchase tables
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import asyncio
from sqlalchemy import text
from database.database import AsyncSessionLocal


async def migrate():
    """Create clicker system tables"""
    async with AsyncSessionLocal() as session:
        try:
            print("Creating clicker system tables...")

            # Create clicker_stats table
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS clicker_stats (
                    user_id VARCHAR(36) PRIMARY KEY,
                    total_clicks BIGINT DEFAULT 0 NOT NULL,
                    total_gems_earned FLOAT DEFAULT 0.0 NOT NULL,
                    best_combo INTEGER DEFAULT 0 NOT NULL,
                    mega_bonuses_hit INTEGER DEFAULT 0 NOT NULL,

                    click_power_level INTEGER DEFAULT 1 NOT NULL,
                    auto_clicker_level INTEGER DEFAULT 0 NOT NULL,
                    multiplier_level INTEGER DEFAULT 0 NOT NULL,
                    energy_capacity_level INTEGER DEFAULT 0 NOT NULL,
                    energy_regen_level INTEGER DEFAULT 0 NOT NULL,

                    current_energy INTEGER DEFAULT 100 NOT NULL,
                    max_energy INTEGER DEFAULT 100 NOT NULL,
                    last_energy_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

                    last_auto_click TIMESTAMP,
                    auto_click_accumulated FLOAT DEFAULT 0.0 NOT NULL,

                    daily_streak INTEGER DEFAULT 0 NOT NULL,
                    last_click_date TIMESTAMP,

                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """))
            print("OK Created clicker_stats table")

            # Create clicker_upgrade_purchases table
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS clicker_upgrade_purchases (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    upgrade_type VARCHAR(50) NOT NULL,
                    level_purchased INTEGER NOT NULL,
                    cost_gems FLOAT NOT NULL,
                    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """))
            print("OK Created clicker_upgrade_purchases table")

            # Create index on user_id for faster queries
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_clicker_upgrades_user
                ON clicker_upgrade_purchases(user_id)
            """))
            print("OK Created indexes")

            await session.commit()
            print("\nSUCCESS Clicker system tables created successfully!")

        except Exception as e:
            print(f"\nERROR Migration failed: {e}")
            await session.rollback()
            raise


async def rollback():
    """Drop clicker system tables"""
    async with AsyncSessionLocal() as session:
        try:
            print("Rolling back clicker system tables...")

            await session.execute(text("DROP TABLE IF EXISTS clicker_upgrade_purchases"))
            await session.execute(text("DROP TABLE IF EXISTS clicker_stats"))

            await session.commit()
            print("SUCCESS Rollback complete!")

        except Exception as e:
            print(f"ERROR Rollback failed: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        asyncio.run(rollback())
    else:
        asyncio.run(migrate())
