"""
Migration: Add Crash Game Tables
Creates crash_games and crash_bets tables for the multiplayer crash betting game.
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
    """Create crash game tables."""

    async with engine.begin() as conn:
        # Create crash_games table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS crash_games (
                id SERIAL PRIMARY KEY,
                status VARCHAR(20) NOT NULL DEFAULT 'waiting',
                crash_point FLOAT,
                server_seed VARCHAR(64) NOT NULL,
                server_seed_hash VARCHAR(64) NOT NULL,
                started_at TIMESTAMP,
                crashed_at TIMESTAMP,
                completed_at TIMESTAMP,
                total_bets INTEGER NOT NULL DEFAULT 0,
                total_wagered INTEGER NOT NULL DEFAULT 0,
                total_paid_out INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))

        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_crash_game_status ON crash_games(status)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_crash_game_created ON crash_games(created_at)"))

        # Create crash_bets table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS crash_bets (
                id SERIAL PRIMARY KEY,
                game_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                bet_amount INTEGER NOT NULL,
                cashout_at FLOAT,
                profit INTEGER NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                placed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                cashed_out_at TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES crash_games(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))

        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_crash_bet_game ON crash_bets(game_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_crash_bet_user ON crash_bets(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_crash_bet_status ON crash_bets(status)"))

        print("[OK] Created crash_games table")
        print("[OK] Created crash_bets table")
        print("[OK] Created indexes")

if __name__ == "__main__":
    print("Running migration: Add Crash Game Tables")
    asyncio.run(run_migration())
    print("Migration complete!")
