#!/usr/bin/env python3
"""
Script to add the 20 missing cryptocurrencies to the database.
"""

import asyncio
from database.database import AsyncSessionLocal
from database.models import CryptoCurrency
from sqlalchemy import select

async def add_missing_cryptocurrencies():
    """Add the 20 missing cryptocurrencies to the database."""

    # The 20 new cryptocurrencies to add
    new_cryptos = [
        # Tier 1 - Highest Priority (Infrastructure & Institutional)
        {"id": "monero", "symbol": "xmr", "name": "Monero"},
        {"id": "lido-dao", "symbol": "ldo", "name": "Lido DAO"},
        {"id": "arbitrum", "symbol": "arb", "name": "Arbitrum"},
        {"id": "maker", "symbol": "mkr", "name": "Maker"},
        {"id": "kaspa", "symbol": "kas", "name": "Kaspa"},
        {"id": "optimism", "symbol": "op", "name": "Optimism"},

        # Tier 2 - High Priority (Gaming, DeFi, L1s)
        {"id": "sui", "symbol": "sui", "name": "Sui"},
        {"id": "immutable-x", "symbol": "imx", "name": "Immutable X"},
        {"id": "secret", "symbol": "scrt", "name": "Secret Network"},
        {"id": "injective-protocol", "symbol": "inj", "name": "Injective Protocol"},
        {"id": "celestia", "symbol": "tia", "name": "Celestia"},
        {"id": "sei-network", "symbol": "sei", "name": "Sei Network"},

        # Tier 3 - Medium Priority (Emerging Tech & Regional)
        {"id": "starknet", "symbol": "strk", "name": "Starknet"},
        {"id": "render-token", "symbol": "rndr", "name": "Render"},
        {"id": "aerodrome-finance", "symbol": "aero", "name": "Aerodrome Finance"},
        {"id": "wax", "symbol": "waxp", "name": "WAX"},
        {"id": "fantom", "symbol": "ftm", "name": "Fantom"},
        {"id": "near", "symbol": "near", "name": "NEAR Protocol"},
        {"id": "mantle", "symbol": "mnt", "name": "Mantle"},
        {"id": "zcash", "symbol": "zec", "name": "Zcash"}
    ]

    async with AsyncSessionLocal() as session:
        try:
            added_count = 0

            for crypto_data in new_cryptos:
                # Check if cryptocurrency already exists
                result = await session.execute(
                    select(CryptoCurrency).where(CryptoCurrency.id == crypto_data["id"])
                )
                existing = result.scalar_one_or_none()

                if not existing:
                    # Add new cryptocurrency
                    crypto = CryptoCurrency(**crypto_data)
                    session.add(crypto)
                    added_count += 1
                    print(f"Adding: {crypto_data['symbol'].upper()} - {crypto_data['name']}")
                else:
                    print(f"Skipping: {crypto_data['symbol'].upper()} - {crypto_data['name']} (already exists)")

            if added_count > 0:
                await session.commit()
                print(f"\n✅ Successfully added {added_count} new cryptocurrencies!")

                # Verify total count
                count_result = await session.execute(select(CryptoCurrency))
                total_count = len(count_result.scalars().all())
                print(f"Total cryptocurrencies in database: {total_count}")

                # Verify XMR specifically
                xmr_result = await session.execute(
                    select(CryptoCurrency).where(CryptoCurrency.symbol == "xmr")
                )
                xmr = xmr_result.scalar_one_or_none()
                if xmr:
                    print(f"✅ XMR (Monero) successfully added: {xmr.name}")
                else:
                    print("❌ XMR (Monero) not found after adding")
            else:
                print("No new cryptocurrencies needed to be added.")

        except Exception as e:
            await session.rollback()
            print(f"❌ Error adding cryptocurrencies: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(add_missing_cryptocurrencies())