"""
Migration: Add profile fields to users table (PostgreSQL)
Adds: avatar_url, bio, profile_theme columns
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    """Add profile fields to users table in PostgreSQL."""

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

        # Check if columns already exist
        check_avatar = await conn.fetchval(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='users' AND column_name='avatar_url'
            """
        )

        if check_avatar:
            print("[INFO] Columns already exist, skipping migration")
            await conn.close()
            return

        # Add avatar_url column
        await conn.execute(
            "ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500)"
        )
        print("[SUCCESS] Added column: avatar_url")

        # Add bio column
        await conn.execute(
            "ALTER TABLE users ADD COLUMN bio VARCHAR(500)"
        )
        print("[SUCCESS] Added column: bio")

        # Add profile_theme column with default value
        await conn.execute(
            "ALTER TABLE users ADD COLUMN profile_theme VARCHAR(50) DEFAULT 'purple'"
        )
        print("[SUCCESS] Added column: profile_theme")

        print("[MIGRATION] Migration completed successfully!")

        # Close connection
        await conn.close()

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(migrate())
