#!/usr/bin/env python3
"""
Quick script to check if round_id column exists in game_bets table
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")

async def check_schema():
    print("=" * 60)
    print("DATABASE SCHEMA CHECK")
    print("=" * 60)
    print(f"\nDatabase: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        # Check game_bets columns
        result = await conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'game_bets'
            ORDER BY ordinal_position
        """))

        columns = result.fetchall()

        print("\n[*] game_bets table columns:")
        print("-" * 60)
        has_round_id = False
        for col_name, col_type in columns:
            marker = "[OK]" if col_name == "round_id" else "    "
            print(f"{marker} {col_name:30} {col_type}")
            if col_name == "round_id":
                has_round_id = True

        print("-" * 60)

        if has_round_id:
            print("\n[SUCCESS] round_id column EXISTS in game_bets table")
        else:
            print("\n[ERROR] round_id column MISSING from game_bets table")
            print("\n[FIX] To fix, run: python database/migrations/run_migration_002.py")

        # Check if roulette_rounds table exists
        result = await conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'roulette_rounds'
            )
        """))

        table_exists = result.scalar()

        status = "[OK]" if table_exists else "[ERROR]"
        exists_text = "EXISTS" if table_exists else "MISSING"
        print(f"\n{status} roulette_rounds table: {exists_text}")

    await engine.dispose()

    return has_round_id

if __name__ == "__main__":
    result = asyncio.run(check_schema())
    sys.exit(0 if result else 1)
