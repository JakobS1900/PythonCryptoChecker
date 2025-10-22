"""
Migration: Add GEM P2P Trading Tables

Creates tables for the P2P trading system:
- gem_trade_orders: Buy/sell limit orders
- gem_trades: Completed trades
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
from sqlalchemy import text
from database.database import get_db


async def run_migration():
    """Add GEM trading tables to the database."""
    print(">> Starting GEM Trading Tables Migration...")

    async for session in get_db():
        try:
            # Create gem_trade_orders table
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS gem_trade_orders (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,

                    order_type VARCHAR(10) NOT NULL CHECK (order_type IN ('buy', 'sell')),
                    price INTEGER NOT NULL CHECK (price > 0),
                    amount INTEGER NOT NULL CHECK (amount > 0),
                    filled_amount INTEGER DEFAULT 0 NOT NULL CHECK (filled_amount >= 0),

                    status VARCHAR(20) DEFAULT 'active' NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    filled_at TIMESTAMP,
                    cancelled_at TIMESTAMP,

                    CHECK (filled_amount <= amount),
                    CHECK (status IN ('active', 'partial', 'filled', 'cancelled'))
                )
            """))

            # Create indexes for gem_trade_orders
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_trade_orders_user
                ON gem_trade_orders(user_id)
            """))

            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_trade_orders_status
                ON gem_trade_orders(status)
            """))

            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_trade_orders_type
                ON gem_trade_orders(order_type)
            """))

            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_trade_orders_price
                ON gem_trade_orders(price)
            """))

            print("   OK Created gem_trade_orders table with indexes")

            # Create gem_trades table
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS gem_trades (
                    id SERIAL PRIMARY KEY,

                    buyer_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    seller_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,

                    order_id INTEGER NOT NULL REFERENCES gem_trade_orders(id) ON DELETE CASCADE,
                    price INTEGER NOT NULL CHECK (price > 0),
                    amount INTEGER NOT NULL CHECK (amount > 0),
                    total_value INTEGER NOT NULL CHECK (total_value > 0),
                    fee INTEGER DEFAULT 0 NOT NULL CHECK (fee >= 0),

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

                    CHECK (buyer_id != seller_id)
                )
            """))

            # Create indexes for gem_trades
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_trades_buyer
                ON gem_trades(buyer_id)
            """))

            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_trades_seller
                ON gem_trades(seller_id)
            """))

            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_trades_order
                ON gem_trades(order_id)
            """))

            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_trades_created
                ON gem_trades(created_at DESC)
            """))

            print("   OK Created gem_trades table with indexes")

            await session.commit()
            print(">> GEM Trading Tables Migration Complete!")

        except Exception as e:
            await session.rollback()
            print(f">> Migration failed: {str(e)}")
            raise
        finally:
            await session.close()
            break


if __name__ == "__main__":
    asyncio.run(run_migration())
