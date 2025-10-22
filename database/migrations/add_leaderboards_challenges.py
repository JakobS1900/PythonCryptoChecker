"""
Migration: Add Leaderboards and Daily Challenges Tables
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
from sqlalchemy import text
from database.database import engine

async def run_migration():
    """Create leaderboards and challenges tables."""

    async with engine.begin() as conn:
        # Leaderboard entries table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS leaderboard_entries (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                category TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                rank INTEGER NOT NULL,
                score INTEGER NOT NULL,
                stats_data TEXT,
                period_start TIMESTAMP NOT NULL,
                period_end TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))

        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_leaderboard_category_timeframe ON leaderboard_entries(category, timeframe)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_leaderboard_rank ON leaderboard_entries(rank)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_leaderboard_user ON leaderboard_entries(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_leaderboard_updated ON leaderboard_entries(updated_at)"))

        # Daily challenges table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS daily_challenges (
                id SERIAL PRIMARY KEY,
                challenge_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                requirement_value INTEGER NOT NULL,
                gem_reward INTEGER NOT NULL,
                starts_at TIMESTAMP NOT NULL,
                ends_at TIMESTAMP NOT NULL,
                difficulty TEXT NOT NULL DEFAULT 'normal'
            )
        """))

        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_challenges_active ON daily_challenges(starts_at, ends_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_challenges_type ON daily_challenges(challenge_type)"))

        # User challenges table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_challenges (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                challenge_id INTEGER NOT NULL,
                current_progress INTEGER NOT NULL DEFAULT 0,
                completed BOOLEAN NOT NULL DEFAULT FALSE,
                claimed BOOLEAN NOT NULL DEFAULT FALSE,
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                claimed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (challenge_id) REFERENCES daily_challenges(id)
            )
        """))

        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_userchallenge_user ON user_challenges(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_userchallenge_challenge ON user_challenges(challenge_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_userchallenge_completed ON user_challenges(completed)"))

        # Login streaks table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS login_streaks (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                current_streak INTEGER NOT NULL DEFAULT 0,
                longest_streak INTEGER NOT NULL DEFAULT 0,
                last_login_date TIMESTAMP,
                total_logins INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))

        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_loginstreak_user ON login_streaks(user_id)"))

        print("[OK] Created leaderboard_entries table")
        print("[OK] Created daily_challenges table")
        print("[OK] Created user_challenges table")
        print("[OK] Created login_streaks table")
        print("[OK] Created indexes")

if __name__ == "__main__":
    print("Running migration: Add Leaderboards and Challenges Tables")
    asyncio.run(run_migration())
    print("Migration complete!")
