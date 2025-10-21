"""
Database Migration: Add Clicker Achievements Table
- clicker_achievements: Achievement unlocks and rewards
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import asyncio
from sqlalchemy import text
from database.database import AsyncSessionLocal

async def migrate():
    """Create Clicker Achievements table"""
    print("Creating Clicker Achievements table...")

    async with AsyncSessionLocal() as session:
        # ClickerAchievement table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS clicker_achievements (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                achievement_id VARCHAR(100) NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                reward_claimed BOOLEAN DEFAULT FALSE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                CONSTRAINT uq_user_achievement UNIQUE (user_id, achievement_id)
            )
        """))
        print("  [OK] Created clicker_achievements table")

        # Achievement indexes
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_achievement_user ON clicker_achievements(user_id)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_achievement_id ON clicker_achievements(achievement_id)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_achievement_unlocked ON clicker_achievements(unlocked_at)
        """))

        await session.commit()
        print("  [OK] Created indexes")

    print("\n[SUCCESS] Clicker Achievements table created successfully!")

if __name__ == "__main__":
    asyncio.run(migrate())
