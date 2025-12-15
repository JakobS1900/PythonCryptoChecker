"""
Migration: Increase avatar_url column length to support base64 data URLs
Changes avatar_url from VARCHAR(500) to VARCHAR(100000)
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    """Increase avatar_url column length in PostgreSQL."""

    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL", "")

    if not db_url.startswith("postgresql"):
        print("ERROR: This migration is for PostgreSQL only")
        return

    # Parse PostgreSQL URL
    # Format: postgresql+asyncpg://user:pass@host:port/dbname
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        print("[MIGRATION] Connected to PostgreSQL database")

        # Check if avatar_url column exists
        check_column = await conn.fetchval(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='users' AND column_name='avatar_url'
            """
        )

        if not check_column:
            print("[WARNING] avatar_url column does not exist, skipping migration")
            await conn.close()
            return

        # Alter column to increase length
        await conn.execute(
            "ALTER TABLE users ALTER COLUMN avatar_url TYPE VARCHAR(100000)"
        )
        print("[SUCCESS] Increased avatar_url column length to VARCHAR(100000)")

        print("[MIGRATION] Migration completed successfully!")

        # Close connection
        await conn.close()

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(migrate())
