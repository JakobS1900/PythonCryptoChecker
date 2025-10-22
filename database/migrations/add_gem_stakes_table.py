"""
Database migration script for GEM Staking table.

Creates the gem_stakes table for passive income staking feature.
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from database.models import Base, GemStake
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def run_migration():
    """Run the GEM staking table migration."""
    logger.info("Starting GEM staking table migration...")

    # Get database URL
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crypto_tracker_v3.db")

    # Convert async URLs to sync for migration
    database_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "")

    logger.info(f"Database URL: {database_url}")

    # Create engine
    engine = create_engine(database_url)

    try:
        # Create gem_stakes table
        GemStake.__table__.create(engine, checkfirst=True)
        logger.info("✓ Created gem_stakes table")

        logger.info("✅ Migration completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

    finally:
        engine.dispose()


def rollback_migration():
    """Rollback the migration (drop tables)."""
    logger.info("Rolling back GEM staking table migration...")

    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crypto_tracker_v3.db")
    database_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "")

    engine = create_engine(database_url)

    try:
        GemStake.__table__.drop(engine, checkfirst=True)
        logger.info("✓ Dropped gem_stakes table")

        logger.info("✅ Rollback completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        raise

    finally:
        engine.dispose()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
