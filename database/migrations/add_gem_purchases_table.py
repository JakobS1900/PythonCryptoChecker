"""
Database migration script for GEM Purchases table.
Adds support for GEM package purchase system (educational/simulated only).

Tables created:
- gem_purchases: GEM package purchase history
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, GemPurchase
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def run_migration():
    """Run the GEM purchases table migration."""
    logger.info("Starting GEM purchases table migration...")

    # Get database URL (convert async SQLAlchemy URL to sync)
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crypto_tracker_v3.db")
    # Convert async driver to sync driver
    database_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    logger.info(f"Connecting to database: {database_url.split('@')[0] if '@' in database_url else 'SQLite'}")

    # Create engine
    engine = create_engine(database_url)

    try:
        # Create gem_purchases table
        logger.info("Creating gem_purchases table...")

        # Create table using SQLAlchemy metadata
        GemPurchase.__table__.create(engine, checkfirst=True)
        logger.info("✓ Created gem_purchases table")

        logger.info("✅ Migration completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        engine.dispose()


def rollback_migration():
    """Rollback the GEM purchases table migration."""
    logger.info("Rolling back GEM purchases table migration...")

    # Get database URL (convert async to sync)
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crypto_tracker_v3.db")
    database_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(database_url)

    try:
        logger.info("Dropping gem_purchases table...")
        GemPurchase.__table__.drop(engine, checkfirst=True)
        logger.info("✓ Dropped gem_purchases table")

        logger.info("✅ Rollback completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate GEM purchases table")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    else:
        run_migration()
