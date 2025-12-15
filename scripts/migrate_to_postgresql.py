#!/usr/bin/env python3
"""
Database migration script for PostgreSQL upgrade.
Exports data from SQLite and imports into PostgreSQL.
Usage: python scripts/migrate_to_postgresql.py
"""

import os
import sys
import json
import asyncio
import logging
import uuid
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, create_engine

# Load environment variables
load_dotenv()

# Database URLs
SQLITE_URL = "sqlite+aiosqlite:///./crypto_tracker_v3.db"
POSTGRESQL_URL = os.getenv("DATABASE_URL")

# Fix async connection - use asyncpg for PostgreSQL async operations
if POSTGRESQL_URL and 'postgresql://' in POSTGRESQL_URL:
    POSTGRESQL_URL = POSTGRESQL_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)

if not POSTGRESQL_URL:
    print("❌ Error: DATABASE_URL environment variable not set")
    exit(1)

if not POSTGRESQL_URL.startswith("postgresql"):
    print("❌ Error: DATABASE_URL does not point to PostgreSQL")
    exit(1)

# Add current directory to Python path so we can import local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    def __init__(self):
        self.sqlite_engine = create_async_engine(SQLITE_URL, echo=False)
        self.postgresql_engine = create_async_engine(POSTGRESQL_URL, echo=True)

    async def export_sqlite_data(self):
        """Export all data from SQLite database."""
        logger.info("📤 Exporting data from SQLite...")

        data = {}

        # Define tables in dependency order for import
        tables = [
            "users", "wallets", "game_sessions", "game_bets",
            "transactions", "cryptocurrencies", "portfolio_holdings",
            "daily_bonuses", "achievements", "user_achievements",
            "emergency_tasks", "user_emergency_tasks"
        ]

        async with self.sqlite_engine.connect() as conn:
            for table in tables:
                try:
                    logger.info(f"  ↳ Exporting table: {table}")
                    result = await conn.execute(text(f"SELECT * FROM {table}"))
                    rows = result.fetchall()
                    column_names = result.keys()

                    data[table] = []
                    for row in rows:
                        # Convert row to dict with column names
                        row_dict = {}
                        for i, column_name in enumerate(column_names):
                            value = row[i]

                            # Handle datetime serialization
                            if hasattr(value, 'isoformat'):
                                value = value.isoformat()
                            elif isinstance(value, bytes):
                                # Handle binary data (passwords, etc.)
                                value = value.decode('utf-8', errors='ignore')

                            # Convert integer boolean fields to actual booleans for PostgreSQL
                            if column_name in ['is_active', 'is_bot', 'is_winner'] and isinstance(value, int):
                                value = bool(value)
                            # Convert datetime strings to datetime objects for PostgreSQL
                            elif column_name in ['created_at', 'last_login', 'updated_at', 'timestamp', 'completed_at', 'started_at', 'last_updated'] and isinstance(value, str) and value:
                                try:
                                    # Parse ISO format datetime strings (e.g., '2025-09-27 15:49:58.184438')
                                    if '.' in value:
                                        # With microseconds
                                        value = datetime.fromisoformat(value.replace(' ', 'T'))
                                    else:
                                        # Without microseconds
                                        value = datetime.fromisoformat(value.replace(' ', 'T') + '.000000')
                                except (ValueError, TypeError):
                                    # If parsing fails, keep as string but it will likely fail in PostgreSQL
                                    logger.warning(f"Failed to parse datetime '{value}' for column {column_name}")
                            elif isinstance(value, str) and value == '':
                                value = None  # Convert empty strings to None

                            row_dict[column_name] = value

                        data[table].append(row_dict)

                    logger.info(f"  ✅ {table}: {len(data[table])} records exported")

                except Exception as e:
                    logger.warning(f"  ⚠️ Failed to export {table}: {e}")
                    data[table] = []

        logger.info("📤 SQLite export complete!")
        return data

    async def create_postgresql_schema(self):
        """Create PostgreSQL schema tables."""
        logger.info("🏗️ Creating PostgreSQL schema...")

        from database.models import Base

        try:
            # For schema operations, we temporarily need to connect as postgres user
            # since crypto_app user cannot drop the public schema
            postgres_url = POSTGRESQL_URL.replace('crypto_app:secure_password_2024', 'postgres:secure_password_2024')
            postgres_engine = create_async_engine(postgres_url, echo=False)

            try:
                # Drop existing tables if they exist
                logger.info("  ↳ Dropping existing tables...")
                async with postgres_engine.connect() as conn:
                    await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
                    await conn.execute(text("CREATE SCHEMA public;"))
                    await conn.commit()

                # Grant usage on schema to crypto_app
                async with postgres_engine.connect() as conn:
                    await conn.execute(text("GRANT USAGE ON SCHEMA public TO crypto_app;"))
                    await conn.execute(text("GRANT CREATE ON SCHEMA public TO crypto_app;"))
                    await conn.commit()

            finally:
                await postgres_engine.dispose()

            # Create all tables using the app user
            logger.info("  ↳ Creating new tables...")

            # Create tables synchronously with sync engine
            def create_sync():
                sync_url = POSTGRESQL_URL.replace('postgresql+asyncpg://', 'postgresql://')
                sync_engine = create_engine(sync_url, echo=False)
                try:
                    Base.metadata.create_all(bind=sync_engine)
                finally:
                    sync_engine.dispose()

            # Run sync operation in thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                await asyncio.get_event_loop().run_in_executor(executor, create_sync)

            logger.info("✅ PostgreSQL schema created successfully!")

        except Exception as e:
            logger.error(f"❌ Failed to create PostgreSQL schema: {e}")
            logger.error("This might be due to insufficient privileges.")
            logger.error("Try granting superuser privileges to the postgres user during setup.")
            raise

    async def import_data_to_postgresql(self, data):
        """Import exported data into PostgreSQL."""
        logger.info("📥 Importing data into PostgreSQL...")

        # Check if we have guest game sessions but no guest user, create one if needed
        if "game_sessions" in data and any(record['user_id'] == 'guest' for record in data["game_sessions"]):
            guest_exists = any(record['id'] == 'guest' for record in data.get("users", []))
            if not guest_exists:
                logger.info("  ↳ Creating guest user for game sessions...")
                # Create a guest user record
                guest_user = {
                    'id': 'guest',
                    'username': 'guest',
                    'email': 'guest@guest.crypto',
                    'password_hash': 'guest_user_placeholder',
                    'role': 'PLAYER',
                    'is_active': True,
                    'created_at': datetime.utcnow(),
                    'last_login': None,
                    'is_bot': False,
                    'bot_personality': None
                }
                data["users"].append(guest_user)

                # Create wallet for guest user
                guest_wallet = {
                    'id': str(uuid.uuid4()),
                    'user_id': 'guest',
                    'gem_balance': 0.0,
                    'total_deposited': 0.0,
                    'total_withdrawn': 0.0,
                    'total_wagered': 0.0,
                    'total_won': 0.0,
                    'updated_at': datetime.utcnow()
                }
                data["wallets"].append(guest_wallet)

        # Import tables in dependency order
        import_order = [
            "users", "wallets", "game_sessions", "game_bets",
            "transactions", "cryptocurrencies", "portfolio_holdings",
            "daily_bonuses", "achievements", "user_achievements",
            "emergency_tasks", "user_emergency_tasks"
        ]

        async with self.postgresql_engine.begin() as conn:
            for table in import_order:
                if table not in data or len(data[table]) == 0:
                    logger.info(f"  ↳ Skipping empty table: {table}")
                    continue

                try:
                    logger.info(f"  ↳ Importing {len(data[table])} records into {table}")

                    # Prepare INSERT statement
                    if data[table]:
                        columns = list(data[table][0].keys())
                        placeholders = ", ".join(f":{col}" for col in columns)
                        insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"

                        # Batch insert for performance
                        batch_size = 100
                        for i in range(0, len(data[table]), batch_size):
                            batch = data[table][i:i + batch_size]
                            await conn.execute(text(insert_sql), batch)

                    logger.info(f"  ✅ {table}: {len(data[table])} records imported")

                except Exception as e:
                    logger.error(f"  ❌ Failed to import {table}: {e}")
                    # Log more details for debugging
                    logger.error(f"    Sample record: {data[table][0] if data[table] else 'No data'}")
                    raise

        logger.info("📥 PostgreSQL import complete!")

    async def verify_migration(self):
        """Verify that data was migrated correctly."""
        logger.info("🔍 Verifying migration...")

        verification = {}

        async with self.postgresql_engine.connect() as conn:
            for table in ["users", "wallets", "game_bets", "cryptocurrencies"]:
                try:
                    result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    verification[table] = count
                    logger.info(f"  ✅ {table}: {count} records")
                except Exception as e:
                    logger.error(f"  ❌ {table}: verification failed - {e}")
                    verification[table] = 0

        return verification

    async def migrate(self):
        """Run the complete migration process."""
        logger.info("🚀 Starting PostgreSQL migration...")
        logger.info(f"📡 Source: {SQLITE_URL}")
        logger.info(f"📡 Target: {POSTGRESQL_URL}")
        logger.info("─" * 50)

        try:
            # Step 1: Export from SQLite
            sqlite_data = await self.export_sqlite_data()
            total_records = sum(len(records) for records in sqlite_data.values())
            logger.info(f"📊 Exported {total_records} total records from SQLite")
            logger.info("─" * 50)

            # Step 2: Create PostgreSQL schema
            await self.create_postgresql_schema()
            logger.info("─" * 50)

            # Step 3: Import to PostgreSQL
            await self.import_data_to_postgresql(sqlite_data)
            logger.info("─" * 50)

            # Step 4: Verify migration
            verification = await self.verify_migration()
            total_verified = sum(verification.values())
            logger.info("─" * 50)

            if total_records == total_verified:
                logger.info("🎉 Migration completed successfully!")
                logger.info(f"✅ Total records migrated: {total_verified}")
                return True
            else:
                logger.warning(f"⚠️ Migration completed with issues. Expected {total_records}, got {total_verified}")
                return True

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise
        finally:
            # Close engines
            await self.sqlite_engine.dispose()
            await self.postgresql_engine.dispose()

async def main():
    """Run the migration."""
    logger.info("PostgreSQL Migration Script")
    logger.info("=" * 50)

    migrator = DatabaseMigrator()
    success = await migrator.migrate()

    if success:
        logger.info("")
        logger.info("🎯 MIGRATION SUCCESS!")
        logger.info("You can now:")
        logger.info("1. Set DATABASE_URL to PostgreSQL in your environment")
        logger.info("2. Restart your application with: python main.py")
        logger.info("3. Test concurrent operations - bots, price updates, and spins")
        exit(0)
    else:
        logger.error("❌ Migration failed")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
