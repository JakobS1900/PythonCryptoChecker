"""
Database migration script for Stock Market tables.
Adds support for virtual stock trading system.

Tables created:
- stock_metadata: Stock company information
- stock_price_cache: Cached price data from APIs
- stock_holdings: User stock positions
- stock_transactions: Buy/sell transaction history
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database.models import Base, StockMetadata, StockPriceCache, StockHolding, StockTransaction
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def run_migration():
    """Run the stock market tables migration."""
    logger.info("Starting stock market tables migration...")

    # Get database URL (convert async SQLAlchemy URL to sync)
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crypto_tracker_v3.db")
    # Convert async driver to sync driver
    database_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    logger.info(f"Connecting to database: {database_url.split('@')[0] if '@' in database_url else 'SQLite'}")

    # Create engine
    engine = create_engine(database_url)

    try:
        # Create all stock market tables
        logger.info("Creating stock market tables...")

        # Create tables using SQLAlchemy metadata
        StockMetadata.__table__.create(engine, checkfirst=True)
        logger.info("✓ Created stock_metadata table")

        StockPriceCache.__table__.create(engine, checkfirst=True)
        logger.info("✓ Created stock_price_cache table")

        StockHolding.__table__.create(engine, checkfirst=True)
        logger.info("✓ Created stock_holdings table")

        StockTransaction.__table__.create(engine, checkfirst=True)
        logger.info("✓ Created stock_transactions table")

        logger.info("✅ Migration completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        engine.dispose()


def rollback_migration():
    """Rollback the stock market tables migration."""
    logger.info("Rolling back stock market tables migration...")

    # Get database URL (convert async to sync)
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crypto_tracker_v3.db")
    database_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            # Drop tables in reverse order (respecting foreign keys)
            logger.info("Dropping stock_transactions table...")
            conn.execute(text("DROP TABLE IF EXISTS stock_transactions"))

            logger.info("Dropping stock_holdings table...")
            conn.execute(text("DROP TABLE IF EXISTS stock_holdings"))

            logger.info("Dropping stock_price_cache table...")
            conn.execute(text("DROP TABLE IF EXISTS stock_price_cache"))

            logger.info("Dropping stock_metadata table...")
            conn.execute(text("DROP TABLE IF EXISTS stock_metadata"))

            conn.commit()

        logger.info("✅ Rollback completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        raise
    finally:
        engine.dispose()


def verify_migration():
    """Verify that the migration was successful."""
    logger.info("Verifying migration...")

    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crypto_tracker_v3.db")
    database_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            # Check if tables exist
            tables = ['stock_metadata', 'stock_price_cache', 'stock_holdings', 'stock_transactions']

            for table_name in tables:
                # Try to query the table
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                logger.info(f"✓ Table '{table_name}' exists (rows: {count})")

            logger.info("✅ All stock market tables verified!")
            return True

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False
    finally:
        engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Stock Market Tables Migration")
    parser.add_argument(
        'action',
        choices=['migrate', 'rollback', 'verify'],
        help='Migration action to perform'
    )

    args = parser.parse_args()

    if args.action == 'migrate':
        run_migration()
        verify_migration()
    elif args.action == 'rollback':
        rollback_migration()
    elif args.action == 'verify':
        verify_migration()
