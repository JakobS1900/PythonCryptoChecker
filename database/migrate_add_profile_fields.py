#!/usr/bin/env python3
"""
Database migration: Add avatar_url and bio fields to users table
"""

import sqlite3
import sys
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / "crypto_tracker_v3.db"

def migrate():
    """Add avatar_url and bio columns to users table."""
    print(f"[MIGRATION] Starting migration on {DB_PATH}...")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]

        migrations_run = []

        # Add avatar_url column if it doesn't exist
        if 'avatar_url' not in columns:
            print("  Adding avatar_url column...")
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500)")
            migrations_run.append("avatar_url")
        else:
            print("  ✓ avatar_url column already exists")

        # Add bio column if it doesn't exist
        if 'bio' not in columns:
            print("  Adding bio column...")
            cursor.execute("ALTER TABLE users ADD COLUMN bio VARCHAR(500)")
            migrations_run.append("bio")
        else:
            print("  ✓ bio column already exists")

        # Commit changes
        conn.commit()

        if migrations_run:
            print(f"\n[SUCCESS] Migration completed successfully!")
            print(f"   Added columns: {', '.join(migrations_run)}")
        else:
            print(f"\n[SUCCESS] Database already up to date - no changes needed")

        # Verify the changes
        cursor.execute("PRAGMA table_info(users)")
        columns_after = cursor.fetchall()
        print(f"\n[INFO] Users table now has {len(columns_after)} columns:")
        for col in columns_after:
            print(f"   - {col[1]} ({col[2]})")

        conn.close()
        return True

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
