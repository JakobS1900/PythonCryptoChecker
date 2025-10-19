"""Quick script to add test GEM to user wallet"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def add_gems():
    db_url = os.getenv("DATABASE_URL").replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(db_url)

    user_id = "0e31e997-7111-4ee2-9053-4d10ab6ca021"  # bob

    # Add 100,000 GEM for stock trading tests
    await conn.execute(
        "UPDATE wallets SET gem_balance = gem_balance + 100000 WHERE user_id = $1",
        user_id
    )

    # Get new balance
    balance = await conn.fetchval(
        "SELECT gem_balance FROM wallets WHERE user_id = $1",
        user_id
    )

    print(f"[SUCCESS] Added 100,000 GEM to bob's wallet")
    print(f"New balance: {balance} GEM")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(add_gems())
