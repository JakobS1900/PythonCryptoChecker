-- Migration 002: Add server-managed roulette rounds
-- Created: 2025-10-01
-- Purpose: Transform from client-driven to server-managed round system

-- Create roulette_rounds table
CREATE TABLE IF NOT EXISTS roulette_rounds (
    id VARCHAR(36) PRIMARY KEY,
    round_number INTEGER NOT NULL UNIQUE,
    phase VARCHAR(20) NOT NULL DEFAULT 'betting',
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    betting_ends_at TIMESTAMP,
    outcome_number INTEGER,  -- 0-36, NULL until spun
    outcome_color VARCHAR(10),  -- red/black/green
    outcome_crypto VARCHAR(10),  -- BTC, ETH, etc.
    triggered_by VARCHAR(36),  -- user_id who clicked spin (NULL if auto)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (triggered_by) REFERENCES users(id)
);

-- Create index on round_number for fast lookups
CREATE INDEX IF NOT EXISTS ix_roulette_rounds_round_number ON roulette_rounds(round_number);

-- Create index on phase for filtering active rounds
CREATE INDEX IF NOT EXISTS ix_roulette_rounds_phase ON roulette_rounds(phase);

-- Add round_id column to game_bets
-- NOTE: Using PRAGMA for SQLite compatibility; PostgreSQL would use ALTER TABLE directly
-- SQLite doesn't support ALTER TABLE ADD COLUMN with FOREIGN KEY, so we'll add it without FK first

-- Check if column already exists (idempotent migration)
-- For SQLite: must recreate table to add FK constraint properly
-- For development: we'll add column without FK, then rely on application-level integrity

-- Add round_id column if it doesn't exist
-- This is SQLite-compatible (PostgreSQL would be more straightforward)
SELECT CASE
    WHEN EXISTS (
        SELECT 1 FROM pragma_table_info('game_bets') WHERE name='round_id'
    )
    THEN 'Column already exists'
    ELSE (
        SELECT 'Adding column'
        FROM (
            SELECT 1  -- Placeholder for actual ALTER TABLE
        )
    )
END;

-- For SQLite: Add column (FK constraint will be enforced by ORM)
-- If column doesn't exist, add it
-- Note: This works in SQLite but syntax varies by database
-- For production PostgreSQL, use: ALTER TABLE game_bets ADD COLUMN round_id VARCHAR(36) REFERENCES roulette_rounds(id);

-- SQLite version (add column without FK, ORM will handle FK)
-- Uncomment for actual migration:
-- ALTER TABLE game_bets ADD COLUMN round_id VARCHAR(36);

-- Create index on game_bets.round_id for performance
CREATE INDEX IF NOT EXISTS ix_game_bets_round_id ON game_bets(round_id);

-- Verification queries (comment out for production)
-- SELECT COUNT(*) as roulette_rounds_created FROM sqlite_master WHERE type='table' AND name='roulette_rounds';
-- SELECT name FROM pragma_table_info('game_bets') WHERE name='round_id';
