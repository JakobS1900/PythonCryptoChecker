"""
Migration: Add daily missions and weekly challenges tables (PostgreSQL)
Adds tables:
- daily_missions_progress: Track user progress on daily missions
- weekly_challenges_progress: Track user progress on weekly challenges
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    """Add missions and challenges tables to PostgreSQL database."""

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

        # Check if tables already exist
        check_missions = await conn.fetchval(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name='daily_missions_progress'
            """
        )

        if check_missions:
            print("[INFO] Missions tables already exist, skipping migration")
            await conn.close()
            return

        # ==================== CREATE DAILY MISSIONS PROGRESS TABLE ====================
        await conn.execute(
            """
            CREATE TABLE daily_missions_progress (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                mission_key VARCHAR(50) NOT NULL,
                current_progress INTEGER DEFAULT 0,
                target_value INTEGER NOT NULL,
                reward_amount FLOAT NOT NULL,
                is_completed BOOLEAN DEFAULT FALSE,
                completed_at TIMESTAMP,
                reward_claimed BOOLEAN DEFAULT FALSE,
                reward_claimed_at TIMESTAMP,
                reset_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        print("[SUCCESS] Created table: daily_missions_progress")

        # Create indexes for daily missions
        await conn.execute(
            "CREATE INDEX idx_user_mission_daily ON daily_missions_progress(user_id, mission_key, reset_at)"
        )
        print("[SUCCESS] Created index: idx_user_mission_daily")

        # ==================== CREATE WEEKLY CHALLENGES PROGRESS TABLE ====================
        await conn.execute(
            """
            CREATE TABLE weekly_challenges_progress (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                challenge_key VARCHAR(50) NOT NULL,
                current_progress FLOAT DEFAULT 0.0,
                target_value FLOAT NOT NULL,
                reward_amount FLOAT NOT NULL,
                is_completed BOOLEAN DEFAULT FALSE,
                completed_at TIMESTAMP,
                reward_claimed BOOLEAN DEFAULT FALSE,
                reward_claimed_at TIMESTAMP,
                reset_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        print("[SUCCESS] Created table: weekly_challenges_progress")

        # Create indexes for weekly challenges
        await conn.execute(
            "CREATE INDEX idx_user_challenge_weekly ON weekly_challenges_progress(user_id, challenge_key, reset_at)"
        )
        print("[SUCCESS] Created index: idx_user_challenge_weekly")

        print("[MIGRATION] ✅ Migration completed successfully!")
        print("[INFO] Created 2 tables with 2 indexes")

        # Close connection
        await conn.close()

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        raise

if __name__ == "__main__":
    print("=" * 60)
    print("GEM MARKETPLACE - DAILY MISSIONS & CHALLENGES MIGRATION")
    print("=" * 60)
    asyncio.run(migrate())
