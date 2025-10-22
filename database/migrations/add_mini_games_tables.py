"""
Migration: Add Mini-Games Tables
Creates mini_games and mini_game_stats tables for the mini-games system.
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
    """Create mini-games tables."""

    async with engine.begin() as conn:
        # Create mini_games table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mini_games (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                game_type TEXT NOT NULL,
                bet_amount INTEGER NOT NULL,
                payout INTEGER NOT NULL DEFAULT 0,
                profit INTEGER NOT NULL DEFAULT 0,
                game_data TEXT,
                won BOOLEAN NOT NULL,
                played_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))

        # Create indexes for mini_games
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_minigames_user ON mini_games(user_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_minigames_type ON mini_games(game_type)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_minigames_played ON mini_games(played_at)
        """))

        # Create mini_game_stats table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mini_game_stats (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                total_games_played INTEGER NOT NULL DEFAULT 0,
                total_games_won INTEGER NOT NULL DEFAULT 0,
                total_games_lost INTEGER NOT NULL DEFAULT 0,
                total_wagered INTEGER NOT NULL DEFAULT 0,
                total_won INTEGER NOT NULL DEFAULT 0,
                net_profit INTEGER NOT NULL DEFAULT 0,
                coinflip_stats TEXT,
                dice_stats TEXT,
                higherlower_stats TEXT,
                current_win_streak INTEGER NOT NULL DEFAULT 0,
                longest_win_streak INTEGER NOT NULL DEFAULT 0,
                current_loss_streak INTEGER NOT NULL DEFAULT 0,
                longest_loss_streak INTEGER NOT NULL DEFAULT 0,
                biggest_win INTEGER NOT NULL DEFAULT 0,
                biggest_loss INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))

        # Create indexes for mini_game_stats
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_minigamestats_user ON mini_game_stats(user_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_minigamestats_profit ON mini_game_stats(net_profit)
        """))

        print("[OK] Created mini_games table")
        print("[OK] Created mini_game_stats table")
        print("[OK] Created indexes")

if __name__ == "__main__":
    print("Running migration: Add Mini-Games Tables")
    asyncio.run(run_migration())
    print("Migration complete!")
