"""
Migration: Add Social Features Tables
Creates friendships, friend_requests, private_messages, activity_feed, and user_profiles tables.
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
    """Create social features tables."""

    async with engine.begin() as conn:
        # Create friendships table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS friendships (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                friend_id TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (friend_id) REFERENCES users(id)
            )
        """))

        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_friendship_user ON friendships(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_friendship_friend ON friendships(friend_id)"))
        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_friendship_unique ON friendships(user_id, friend_id)"))

        # Create friend_requests table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS friend_requests (
                id SERIAL PRIMARY KEY,
                sender_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                responded_at TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id)
            )
        """))

        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_friend_request_sender ON friend_requests(sender_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_friend_request_receiver ON friend_requests(receiver_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_friend_request_status ON friend_requests(status)"))

        # Create private_messages table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS private_messages (
                id SERIAL PRIMARY KEY,
                sender_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                message TEXT NOT NULL,
                read BOOLEAN NOT NULL DEFAULT FALSE,
                read_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id)
            )
        """))

        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_private_message_sender ON private_messages(sender_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_private_message_receiver ON private_messages(receiver_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_private_message_read ON private_messages(read)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_private_message_created ON private_messages(created_at)"))

        # Create activity_feed table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS activity_feed (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                activity_type VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                data TEXT,
                is_public BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))

        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_activity_feed_user ON activity_feed(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_activity_feed_type ON activity_feed(activity_type)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_activity_feed_created ON activity_feed(created_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_activity_feed_public ON activity_feed(is_public)"))

        # Create user_profiles table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                bio TEXT,
                avatar_url VARCHAR(500),
                banner_url VARCHAR(500),
                location VARCHAR(100),
                website VARCHAR(200),
                profile_public BOOLEAN NOT NULL DEFAULT TRUE,
                show_stats BOOLEAN NOT NULL DEFAULT TRUE,
                show_activity BOOLEAN NOT NULL DEFAULT TRUE,
                is_online BOOLEAN NOT NULL DEFAULT FALSE,
                last_seen TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))

        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_profile_user ON user_profiles(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_profile_online ON user_profiles(is_online)"))

        print("[OK] Created friendships table")
        print("[OK] Created friend_requests table")
        print("[OK] Created private_messages table")
        print("[OK] Created activity_feed table")
        print("[OK] Created user_profiles table")
        print("[OK] Created all indexes")

if __name__ == "__main__":
    print("Running migration: Add Social Features Tables")
    asyncio.run(run_migration())
    print("Migration complete!")
