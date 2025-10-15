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
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                mission_id VARCHAR(50) NOT NULL,
                mission_name VARCHAR(100) NOT NULL,
                mission_description TEXT,
                progress INTEGER DEFAULT 0,
                target INTEGER NOT NULL,
                status VARCHAR(20) DEFAULT 'active',
                reward_gems INTEGER NOT NULL,
                completed_at TIMESTAMP,
                claimed_at TIMESTAMP,
                date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, mission_id, date)
            )
            """
        )
        print("[SUCCESS] Created table: daily_missions_progress")

        # Create indexes for daily missions
        await conn.execute(
            "CREATE INDEX idx_missions_user_date ON daily_missions_progress(user_id, date)"
        )
        print("[SUCCESS] Created index: idx_missions_user_date")

        await conn.execute(
            "CREATE INDEX idx_missions_status ON daily_missions_progress(status)"
        )
        print("[SUCCESS] Created index: idx_missions_status")

        await conn.execute(
            "CREATE INDEX idx_missions_date ON daily_missions_progress(date)"
        )
        print("[SUCCESS] Created index: idx_missions_date")

        # ==================== CREATE WEEKLY CHALLENGES PROGRESS TABLE ====================
        await conn.execute(
            """
            CREATE TABLE weekly_challenges_progress (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                challenge_id VARCHAR(50) NOT NULL,
                challenge_name VARCHAR(100) NOT NULL,
                challenge_description TEXT,
                progress INTEGER DEFAULT 0,
                target INTEGER NOT NULL,
                status VARCHAR(20) DEFAULT 'active',
                reward_gems INTEGER NOT NULL,
                completed_at TIMESTAMP,
                claimed_at TIMESTAMP,
                week_start DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, challenge_id, week_start)
            )
            """
        )
        print("[SUCCESS] Created table: weekly_challenges_progress")

        # Create indexes for weekly challenges
        await conn.execute(
            "CREATE INDEX idx_challenges_user_week ON weekly_challenges_progress(user_id, week_start)"
        )
        print("[SUCCESS] Created index: idx_challenges_user_week")

        await conn.execute(
            "CREATE INDEX idx_challenges_status ON weekly_challenges_progress(status)"
        )
        print("[SUCCESS] Created index: idx_challenges_status")

        await conn.execute(
            "CREATE INDEX idx_challenges_week ON weekly_challenges_progress(week_start)"
        )
        print("[SUCCESS] Created index: idx_challenges_week")

        print("[MIGRATION] ✅ Migration completed successfully!")
        print("[INFO] Created 2 tables with 6 indexes")

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
