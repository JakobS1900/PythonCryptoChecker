"""
Database Migration: Add Clicker Phase 2 Tables
- clicker_prestige: Prestige system with permanent bonuses
- clicker_powerups: Active power-ups
- clicker_powerup_cooldowns: Power-up cooldown tracking
- clicker_challenges: Daily and weekly challenges
- clicker_leaderboards: Leaderboard statistics
- clicker_themes: Visual customization preferences
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import asyncio
from sqlalchemy import text
from database.database import AsyncSessionLocal

async def migrate():
    """Create Clicker Phase 2 tables"""
    print("Creating Clicker Phase 2 tables...")

    async with AsyncSessionLocal() as session:
        # ClickerPrestige table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS clicker_prestige (
                user_id VARCHAR(36) PRIMARY KEY,
                prestige_level INTEGER DEFAULT 0 NOT NULL,
                prestige_points INTEGER DEFAULT 0 NOT NULL,
                total_lifetime_gems FLOAT DEFAULT 0.0 NOT NULL,
                last_prestige_at TIMESTAMP,
                has_click_master BOOLEAN DEFAULT FALSE NOT NULL,
                has_energy_expert BOOLEAN DEFAULT FALSE NOT NULL,
                has_quick_start BOOLEAN DEFAULT FALSE NOT NULL,
                has_auto_unlock BOOLEAN DEFAULT FALSE NOT NULL,
                has_multiplier_boost BOOLEAN DEFAULT FALSE NOT NULL,
                has_prestige_master BOOLEAN DEFAULT FALSE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        print("  [OK] Created clicker_prestige table")

        # ClickerPowerup table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS clicker_powerups (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                powerup_type VARCHAR(50) NOT NULL,
                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        print("  [OK] Created clicker_powerups table")

        # Powerup indexes
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_powerup_user ON clicker_powerups(user_id)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_powerup_active ON clicker_powerups(user_id, is_active)
        """))

        # ClickerPowerupCooldown table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS clicker_powerup_cooldowns (
                user_id VARCHAR(36) NOT NULL,
                powerup_type VARCHAR(50) NOT NULL,
                cooldown_ends_at TIMESTAMP NOT NULL,
                PRIMARY KEY (user_id, powerup_type),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        print("  [OK] Created clicker_powerup_cooldowns table")

        # Cooldown indexes
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_powerup_cooldown_user ON clicker_powerup_cooldowns(user_id)
        """))

        # ClickerChallenge table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS clicker_challenges (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                challenge_type VARCHAR(50) NOT NULL,
                challenge_period VARCHAR(20) NOT NULL,
                challenge_date DATE NOT NULL,
                progress INTEGER DEFAULT 0 NOT NULL,
                target INTEGER NOT NULL,
                is_completed BOOLEAN DEFAULT FALSE NOT NULL,
                completed_at TIMESTAMP,
                claimed BOOLEAN DEFAULT FALSE NOT NULL,
                claimed_at TIMESTAMP,
                reward_gems FLOAT DEFAULT 0.0 NOT NULL,
                reward_pp INTEGER DEFAULT 0 NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        print("  [OK] Created clicker_challenges table")

        # Challenge indexes
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_challenge_user ON clicker_challenges(user_id)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_challenge_user_date ON clicker_challenges(user_id, challenge_date)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_challenge_active ON clicker_challenges(user_id, is_completed, claimed)
        """))

        # ClickerLeaderboard table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS clicker_leaderboards (
                user_id VARCHAR(36) PRIMARY KEY,
                total_clicks BIGINT DEFAULT 0 NOT NULL,
                best_combo INTEGER DEFAULT 0 NOT NULL,
                total_gems_earned FLOAT DEFAULT 0.0 NOT NULL,
                prestige_level INTEGER DEFAULT 0 NOT NULL,
                daily_gems_earned FLOAT DEFAULT 0.0 NOT NULL,
                daily_last_reset DATE,
                first_million_seconds INTEGER,
                first_million_achieved_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        print("  [OK] Created clicker_leaderboards table")

        # Leaderboard indexes
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_leaderboard_clicks ON clicker_leaderboards(total_clicks DESC)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_leaderboard_combo ON clicker_leaderboards(best_combo DESC)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_leaderboard_gems ON clicker_leaderboards(total_gems_earned DESC)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_leaderboard_prestige ON clicker_leaderboards(prestige_level DESC)
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_leaderboard_daily ON clicker_leaderboards(daily_gems_earned DESC)
        """))

        # ClickerTheme table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS clicker_themes (
                user_id VARCHAR(36) PRIMARY KEY,
                button_theme VARCHAR(50) DEFAULT 'classic_blue' NOT NULL,
                particle_effect VARCHAR(50) DEFAULT 'gem_burst' NOT NULL,
                background_theme VARCHAR(50) DEFAULT 'gradient_purple' NOT NULL,
                unlocked_button_themes TEXT,
                unlocked_particle_effects TEXT,
                unlocked_backgrounds TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        print("  [OK] Created clicker_themes table")

        await session.commit()
        print("  [OK] Created indexes")

    print("\n[SUCCESS] Clicker Phase 2 tables created successfully!")

if __name__ == "__main__":
    asyncio.run(migrate())
