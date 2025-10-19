"""
Migration: Add achievements tracking table (PostgreSQL)
Adds table:
- achievements_unlocked: Track unlocked achievements for users
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    """Add achievements_unlocked table to PostgreSQL database."""

    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL", "")

    if not db_url.startswith("postgresql"):
        print("ERROR: This migration is for PostgreSQL only")
        return

    # Parse PostgreSQL URL
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        print("[MIGRATION] Connected to PostgreSQL database")

        # Check if table already exists
        check_table = await conn.fetchval(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name='achievements_unlocked'
            """
        )

        if check_table:
            print("[INFO] Achievements table already exists, skipping migration")
            await conn.close()
            return

        # ==================== CREATE ACHIEVEMENTS UNLOCKED TABLE ====================
        await conn.execute(
            """
            CREATE TABLE achievements_unlocked (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                achievement_key VARCHAR(100) NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                reward_amount FLOAT NOT NULL,
                reward_claimed BOOLEAN DEFAULT FALSE,
                reward_claimed_at TIMESTAMP,
                progress_value FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        print("[SUCCESS] Created table: achievements_unlocked")

        # Create indexes for performance
        await conn.execute(
            "CREATE INDEX idx_user_achievement ON achievements_unlocked(user_id, achievement_key)"
        )
        print("[SUCCESS] Created index: idx_user_achievement")

        await conn.execute(
            "CREATE INDEX idx_unlocked_at ON achievements_unlocked(unlocked_at)"
        )
        print("[SUCCESS] Created index: idx_unlocked_at")

        await conn.execute(
            "CREATE INDEX idx_reward_claimed ON achievements_unlocked(reward_claimed)"
        )
        print("[SUCCESS] Created index: idx_reward_claimed")

        print("[MIGRATION] ✅ Migration completed successfully!")
        print("[INFO] Created 1 table with 3 indexes")

        # Close connection
        await conn.close()

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        raise

if __name__ == "__main__":
    print("=" * 60)
    print("GEM MARKETPLACE - ACHIEVEMENTS SYSTEM MIGRATION")
    print("=" * 60)
    asyncio.run(migrate())
