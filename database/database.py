"""
Database connection and session management for CryptoChecker Version3.
Supports both SQLite and PostgreSQL for concurrent write operations.
"""

import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

from .models import Base, User, Wallet, CryptoCurrency, PortfolioHolding

# Load environment variables
load_dotenv()

# Database configuration - supports SQLite and PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crypto_tracker_v3.db")

# Detect database type
is_postgresql = DATABASE_URL.startswith("postgresql")

# Create async engine with database-specific optimizations
if is_postgresql:
    # PostgreSQL configuration - optimized for concurrent writes
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,
        pool_size=20,  # Increase for concurrent connections
        max_overflow=30,  # Allow more overflow connections
        pool_recycle=300,  # Recycle connections frequently
        pool_timeout=60,  # Wait longer for connections in pool
    )
    logging.info("🔧 Database: PostgreSQL configuration loaded")
else:
    # SQLite configuration - local development fallback
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,
        pool_recycle=300,
        # SQLite optimizations
        connect_args={
            "check_same_thread": False,  # Allow multi-thread access
        }
    )
    logging.info("🔧 Database: SQLite configuration loaded")

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_database():
    """Initialize database tables and seed data."""
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print(">> Database tables created")

    # Seed initial data
    await seed_default_data()

async def seed_default_data():
    """Seed database with default cryptocurrency data."""
    async with AsyncSessionLocal() as session:
        try:
            # Check if cryptocurrencies already exist
            result = await session.execute(text("SELECT COUNT(*) FROM cryptocurrencies"))
            count = result.scalar()

            if count == 0:
                # Add top cryptocurrencies for roulette wheel and trading
                default_cryptos = [
                    # Original 37 cryptocurrencies
                    {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
                    {"id": "ethereum", "symbol": "eth", "name": "Ethereum"},
                    {"id": "binancecoin", "symbol": "bnb", "name": "BNB"},
                    {"id": "cardano", "symbol": "ada", "name": "Cardano"},
                    {"id": "solana", "symbol": "sol", "name": "Solana"},
                    {"id": "ripple", "symbol": "xrp", "name": "XRP"},
                    {"id": "polkadot", "symbol": "dot", "name": "Polkadot"},
                    {"id": "dogecoin", "symbol": "doge", "name": "Dogecoin"},
                    {"id": "avalanche-2", "symbol": "avax", "name": "Avalanche"},
                    {"id": "shiba-inu", "symbol": "shib", "name": "Shiba Inu"},
                    {"id": "matic-network", "symbol": "matic", "name": "Polygon"},
                    {"id": "uniswap", "symbol": "uni", "name": "Uniswap"},
                    {"id": "chainlink", "symbol": "link", "name": "Chainlink"},
                    {"id": "litecoin", "symbol": "ltc", "name": "Litecoin"},
                    {"id": "cosmos", "symbol": "atom", "name": "Cosmos"},
                    {"id": "bitcoin-cash", "symbol": "bch", "name": "Bitcoin Cash"},
                    {"id": "filecoin", "symbol": "fil", "name": "Filecoin"},
                    {"id": "tron", "symbol": "trx", "name": "TRON"},
                    {"id": "ethereum-classic", "symbol": "etc", "name": "Ethereum Classic"},
                    {"id": "stellar", "symbol": "xlm", "name": "Stellar"},
                    {"id": "theta-token", "symbol": "theta", "name": "Theta Network"},
                    {"id": "vechain", "symbol": "vet", "name": "VeChain"},
                    {"id": "algorand", "symbol": "algo", "name": "Algorand"},
                    {"id": "internet-computer", "symbol": "icp", "name": "Internet Computer"},
                    {"id": "hedera-hashgraph", "symbol": "hbar", "name": "Hedera"},
                    {"id": "flow", "symbol": "flow", "name": "Flow"},
                    {"id": "decentraland", "symbol": "mana", "name": "Decentraland"},
                    {"id": "the-sandbox", "symbol": "sand", "name": "The Sandbox"},
                    {"id": "curve-dao-token", "symbol": "crv", "name": "Curve DAO Token"},
                    {"id": "compound-governance-token", "symbol": "comp", "name": "Compound"},
                    {"id": "yearn-finance", "symbol": "yfi", "name": "yearn.finance"},
                    {"id": "sushi", "symbol": "sushi", "name": "SushiSwap"},
                    {"id": "havven", "symbol": "snx", "name": "Synthetix"},
                    {"id": "1inch", "symbol": "1inch", "name": "1inch"},
                    {"id": "balancer", "symbol": "bal", "name": "Balancer"},
                    {"id": "republic-protocol", "symbol": "ren", "name": "Ren"},
                    {"id": "0x", "symbol": "zrx", "name": "0x"},

                    # NEW: Top 20 missing cryptocurrencies
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

                for crypto_data in default_cryptos:
                    crypto = CryptoCurrency(**crypto_data)
                    session.add(crypto)

                await session.commit()
                print(f">> Seeded {len(default_cryptos)} cryptocurrencies")

        except Exception as e:
            await session.rollback()
            print(f">> Error seeding data: {e}")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

async def create_user_with_wallet(
    session: AsyncSession,
    username: str,
    email: str,
    password: str,
    initial_gems: float = 1000.0
) -> User:
    """Create a new user with wallet."""
    try:
        # Create user
        user = User(username=username, email=email)
        user.set_password(password)
        session.add(user)
        await session.flush()  # Get user ID

        # Create wallet
        wallet = Wallet(
            user_id=user.id,
            gem_balance=initial_gems,
            total_deposited=initial_gems
        )
        session.add(wallet)

        await session.commit()
        await session.refresh(user)
        await session.refresh(wallet)

        return user

    except Exception as e:
        await session.rollback()
        raise e

async def get_user_by_username(session: AsyncSession, username: str) -> User:
    """Get user by username."""
    result = await session.execute(text("SELECT * FROM users WHERE username = :username"), {"username": username})
    row = result.fetchone()
    if row:
        user = User()
        user.id = row[0]
        user.username = row[1]
        user.email = row[2]
        user.password_hash = row[3]
        user.role = row[4]
        user.is_active = row[5]
        user.created_at = row[6]
        user.last_login = row[7]
        return user
    return None

async def get_user_by_email(session: AsyncSession, email: str) -> User:
    """Get user by email."""
    result = await session.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})
    row = result.fetchone()
    if row:
        user = User()
        user.id = row[0]
        user.username = row[1]
        user.email = row[2]
        user.password_hash = row[3]
        user.role = row[4]
        user.is_active = row[5]
        user.created_at = row[6]
        user.last_login = row[7]
        return user
    return None
