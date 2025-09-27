"""Development helper: drop and recreate all database tables.

Usage:
  cd Version3
  python scripts/reset_db.py

This is a dev-only convenience for local development. DO NOT use in production.
"""
import asyncio
from database.database import engine, init_database
from database.models import Base

async def reset():
    async with engine.begin() as conn:
        print('Dropping all tables...')
        await conn.run_sync(Base.metadata.drop_all)
        print('Creating all tables...')
        await conn.run_sync(Base.metadata.create_all)
    # Run seed
    await init_database()

if __name__ == '__main__':
    asyncio.run(reset())
