"""
Stock Metadata Seeder
Seeds the stock_metadata table with 100+ popular stocks across various sectors.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import StockMetadata
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Stock data organized by sector
STOCK_DATA = [
    # Technology (30 stocks)
    {"ticker": "AAPL", "company_name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"},
    {"ticker": "MSFT", "company_name": "Microsoft Corporation", "sector": "Technology", "industry": "Software"},
    {"ticker": "GOOGL", "company_name": "Alphabet Inc. (Google)", "sector": "Technology", "industry": "Internet Services"},
    {"ticker": "META", "company_name": "Meta Platforms Inc. (Facebook)", "sector": "Technology", "industry": "Social Media"},
    {"ticker": "NVDA", "company_name": "NVIDIA Corporation", "sector": "Technology", "industry": "Semiconductors"},
    {"ticker": "TSLA", "company_name": "Tesla Inc.", "sector": "Technology", "industry": "Electric Vehicles"},
    {"ticker": "AMD", "company_name": "Advanced Micro Devices", "sector": "Technology", "industry": "Semiconductors"},
    {"ticker": "INTC", "company_name": "Intel Corporation", "sector": "Technology", "industry": "Semiconductors"},
    {"ticker": "ORCL", "company_name": "Oracle Corporation", "sector": "Technology", "industry": "Software"},
    {"ticker": "ADBE", "company_name": "Adobe Inc.", "sector": "Technology", "industry": "Software"},
    {"ticker": "CRM", "company_name": "Salesforce Inc.", "sector": "Technology", "industry": "Cloud Software"},
    {"ticker": "NFLX", "company_name": "Netflix Inc.", "sector": "Technology", "industry": "Streaming"},
    {"ticker": "CSCO", "company_name": "Cisco Systems Inc.", "sector": "Technology", "industry": "Networking"},
    {"ticker": "AVGO", "company_name": "Broadcom Inc.", "sector": "Technology", "industry": "Semiconductors"},
    {"ticker": "QCOM", "company_name": "Qualcomm Inc.", "sector": "Technology", "industry": "Semiconductors"},
    {"ticker": "TXN", "company_name": "Texas Instruments", "sector": "Technology", "industry": "Semiconductors"},
    {"ticker": "IBM", "company_name": "IBM Corporation", "sector": "Technology", "industry": "IT Services"},
    {"ticker": "NOW", "company_name": "ServiceNow Inc.", "sector": "Technology", "industry": "Cloud Software"},
    {"ticker": "SHOP", "company_name": "Shopify Inc.", "sector": "Technology", "industry": "E-commerce"},
    {"ticker": "SQ", "company_name": "Block Inc. (Square)", "sector": "Technology", "industry": "Fintech"},
    {"ticker": "PYPL", "company_name": "PayPal Holdings Inc.", "sector": "Technology", "industry": "Fintech"},
    {"ticker": "UBER", "company_name": "Uber Technologies Inc.", "sector": "Technology", "industry": "Ride Sharing"},
    {"ticker": "SPOT", "company_name": "Spotify Technology", "sector": "Technology", "industry": "Streaming"},
    {"ticker": "SNAP", "company_name": "Snap Inc.", "sector": "Technology", "industry": "Social Media"},
    {"ticker": "TWTR", "company_name": "Twitter Inc.", "sector": "Technology", "industry": "Social Media"},
    {"ticker": "RBLX", "company_name": "Roblox Corporation", "sector": "Technology", "industry": "Gaming"},
    {"ticker": "U", "company_name": "Unity Software Inc.", "sector": "Technology", "industry": "Gaming Software"},
    {"ticker": "PLTR", "company_name": "Palantir Technologies", "sector": "Technology", "industry": "Data Analytics"},
    {"ticker": "SNOW", "company_name": "Snowflake Inc.", "sector": "Technology", "industry": "Cloud Data"},
    {"ticker": "ZM", "company_name": "Zoom Video Communications", "sector": "Technology", "industry": "Video Conferencing"},

    # Finance (20 stocks)
    {"ticker": "JPM", "company_name": "JPMorgan Chase & Co.", "sector": "Finance", "industry": "Banking"},
    {"ticker": "BAC", "company_name": "Bank of America Corp.", "sector": "Finance", "industry": "Banking"},
    {"ticker": "WFC", "company_name": "Wells Fargo & Co.", "sector": "Finance", "industry": "Banking"},
    {"ticker": "GS", "company_name": "Goldman Sachs Group", "sector": "Finance", "industry": "Investment Banking"},
    {"ticker": "MS", "company_name": "Morgan Stanley", "sector": "Finance", "industry": "Investment Banking"},
    {"ticker": "C", "company_name": "Citigroup Inc.", "sector": "Finance", "industry": "Banking"},
    {"ticker": "BLK", "company_name": "BlackRock Inc.", "sector": "Finance", "industry": "Asset Management"},
    {"ticker": "SCHW", "company_name": "Charles Schwab Corp.", "sector": "Finance", "industry": "Brokerage"},
    {"ticker": "AXP", "company_name": "American Express Co.", "sector": "Finance", "industry": "Credit Services"},
    {"ticker": "V", "company_name": "Visa Inc.", "sector": "Finance", "industry": "Payment Processing"},
    {"ticker": "MA", "company_name": "Mastercard Inc.", "sector": "Finance", "industry": "Payment Processing"},
    {"ticker": "BRK.B", "company_name": "Berkshire Hathaway Inc.", "sector": "Finance", "industry": "Conglomerate"},
    {"ticker": "PNC", "company_name": "PNC Financial Services", "sector": "Finance", "industry": "Banking"},
    {"ticker": "USB", "company_name": "U.S. Bancorp", "sector": "Finance", "industry": "Banking"},
    {"ticker": "TFC", "company_name": "Truist Financial Corp.", "sector": "Finance", "industry": "Banking"},
    {"ticker": "COF", "company_name": "Capital One Financial", "sector": "Finance", "industry": "Banking"},
    {"ticker": "AIG", "company_name": "American International Group", "sector": "Finance", "industry": "Insurance"},
    {"ticker": "MET", "company_name": "MetLife Inc.", "sector": "Finance", "industry": "Insurance"},
    {"ticker": "PRU", "company_name": "Prudential Financial", "sector": "Finance", "industry": "Insurance"},
    {"ticker": "ALL", "company_name": "Allstate Corp.", "sector": "Finance", "industry": "Insurance"},

    # Healthcare (20 stocks)
    {"ticker": "JNJ", "company_name": "Johnson & Johnson", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    {"ticker": "UNH", "company_name": "UnitedHealth Group", "sector": "Healthcare", "industry": "Health Insurance"},
    {"ticker": "PFE", "company_name": "Pfizer Inc.", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    {"ticker": "ABBV", "company_name": "AbbVie Inc.", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    {"ticker": "TMO", "company_name": "Thermo Fisher Scientific", "sector": "Healthcare", "industry": "Life Sciences"},
    {"ticker": "ABT", "company_name": "Abbott Laboratories", "sector": "Healthcare", "industry": "Medical Devices"},
    {"ticker": "MRK", "company_name": "Merck & Co. Inc.", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    {"ticker": "LLY", "company_name": "Eli Lilly and Co.", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    {"ticker": "BMY", "company_name": "Bristol Myers Squibb", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    {"ticker": "AMGN", "company_name": "Amgen Inc.", "sector": "Healthcare", "industry": "Biotechnology"},
    {"ticker": "GILD", "company_name": "Gilead Sciences Inc.", "sector": "Healthcare", "industry": "Biotechnology"},
    {"ticker": "CVS", "company_name": "CVS Health Corp.", "sector": "Healthcare", "industry": "Pharmacy"},
    {"ticker": "CI", "company_name": "Cigna Corp.", "sector": "Healthcare", "industry": "Health Insurance"},
    {"ticker": "ANTM", "company_name": "Anthem Inc.", "sector": "Healthcare", "industry": "Health Insurance"},
    {"ticker": "HUM", "company_name": "Humana Inc.", "sector": "Healthcare", "industry": "Health Insurance"},
    {"ticker": "ISRG", "company_name": "Intuitive Surgical Inc.", "sector": "Healthcare", "industry": "Medical Devices"},
    {"ticker": "MDT", "company_name": "Medtronic PLC", "sector": "Healthcare", "industry": "Medical Devices"},
    {"ticker": "DHR", "company_name": "Danaher Corporation", "sector": "Healthcare", "industry": "Life Sciences"},
    {"ticker": "SYK", "company_name": "Stryker Corporation", "sector": "Healthcare", "industry": "Medical Devices"},
    {"ticker": "BSX", "company_name": "Boston Scientific Corp.", "sector": "Healthcare", "industry": "Medical Devices"},

    # Consumer (15 stocks)
    {"ticker": "AMZN", "company_name": "Amazon.com Inc.", "sector": "Consumer", "industry": "E-commerce"},
    {"ticker": "WMT", "company_name": "Walmart Inc.", "sector": "Consumer", "industry": "Retail"},
    {"ticker": "HD", "company_name": "Home Depot Inc.", "sector": "Consumer", "industry": "Home Improvement"},
    {"ticker": "MCD", "company_name": "McDonald's Corp.", "sector": "Consumer", "industry": "Fast Food"},
    {"ticker": "NKE", "company_name": "Nike Inc.", "sector": "Consumer", "industry": "Apparel"},
    {"ticker": "SBUX", "company_name": "Starbucks Corporation", "sector": "Consumer", "industry": "Coffee"},
    {"ticker": "TGT", "company_name": "Target Corporation", "sector": "Consumer", "industry": "Retail"},
    {"ticker": "LOW", "company_name": "Lowe's Companies Inc.", "sector": "Consumer", "industry": "Home Improvement"},
    {"ticker": "COST", "company_name": "Costco Wholesale Corp.", "sector": "Consumer", "industry": "Wholesale"},
    {"ticker": "PG", "company_name": "Procter & Gamble Co.", "sector": "Consumer", "industry": "Consumer Goods"},
    {"ticker": "KO", "company_name": "Coca-Cola Company", "sector": "Consumer", "industry": "Beverages"},
    {"ticker": "PEP", "company_name": "PepsiCo Inc.", "sector": "Consumer", "industry": "Beverages"},
    {"ticker": "DIS", "company_name": "Walt Disney Company", "sector": "Consumer", "industry": "Entertainment"},
    {"ticker": "CMCSA", "company_name": "Comcast Corporation", "sector": "Consumer", "industry": "Telecommunications"},
    {"ticker": "VZ", "company_name": "Verizon Communications", "sector": "Consumer", "industry": "Telecommunications"},

    # Energy (10 stocks)
    {"ticker": "XOM", "company_name": "Exxon Mobil Corporation", "sector": "Energy", "industry": "Oil & Gas"},
    {"ticker": "CVX", "company_name": "Chevron Corporation", "sector": "Energy", "industry": "Oil & Gas"},
    {"ticker": "COP", "company_name": "ConocoPhillips", "sector": "Energy", "industry": "Oil & Gas"},
    {"ticker": "SLB", "company_name": "Schlumberger Ltd.", "sector": "Energy", "industry": "Oilfield Services"},
    {"ticker": "EOG", "company_name": "EOG Resources Inc.", "sector": "Energy", "industry": "Oil & Gas"},
    {"ticker": "PXD", "company_name": "Pioneer Natural Resources", "sector": "Energy", "industry": "Oil & Gas"},
    {"ticker": "MPC", "company_name": "Marathon Petroleum Corp.", "sector": "Energy", "industry": "Refining"},
    {"ticker": "PSX", "company_name": "Phillips 66", "sector": "Energy", "industry": "Refining"},
    {"ticker": "VLO", "company_name": "Valero Energy Corp.", "sector": "Energy", "industry": "Refining"},
    {"ticker": "OXY", "company_name": "Occidental Petroleum", "sector": "Energy", "industry": "Oil & Gas"},

    # Industrials (10 stocks)
    {"ticker": "BA", "company_name": "Boeing Company", "sector": "Industrials", "industry": "Aerospace"},
    {"ticker": "CAT", "company_name": "Caterpillar Inc.", "sector": "Industrials", "industry": "Machinery"},
    {"ticker": "GE", "company_name": "General Electric Co.", "sector": "Industrials", "industry": "Conglomerate"},
    {"ticker": "LMT", "company_name": "Lockheed Martin Corp.", "sector": "Industrials", "industry": "Defense"},
    {"ticker": "RTX", "company_name": "Raytheon Technologies", "sector": "Industrials", "industry": "Aerospace & Defense"},
    {"ticker": "UPS", "company_name": "United Parcel Service", "sector": "Industrials", "industry": "Logistics"},
    {"ticker": "HON", "company_name": "Honeywell International", "sector": "Industrials", "industry": "Conglomerate"},
    {"ticker": "UNP", "company_name": "Union Pacific Corp.", "sector": "Industrials", "industry": "Rail Transportation"},
    {"ticker": "DE", "company_name": "Deere & Company", "sector": "Industrials", "industry": "Agricultural Equipment"},
    {"ticker": "MMM", "company_name": "3M Company", "sector": "Industrials", "industry": "Conglomerate"},
]


def seed_stock_metadata():
    """Seed the stock_metadata table with stock data."""
    logger.info("Starting stock metadata seeding...")

    # Get database URL (convert async to sync)
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crypto_tracker_v3.db")
    database_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    logger.info(f"Connecting to database...")

    # Create engine and session
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Count existing stocks
        existing_count = session.query(StockMetadata).count()
        logger.info(f"Found {existing_count} existing stocks in database")

        # Add stocks
        added_count = 0
        updated_count = 0

        for stock_data in STOCK_DATA:
            # Check if stock already exists
            existing_stock = session.query(StockMetadata).filter_by(
                ticker=stock_data['ticker']
            ).first()

            if existing_stock:
                # Update existing stock
                existing_stock.company_name = stock_data['company_name']
                existing_stock.sector = stock_data['sector']
                existing_stock.industry = stock_data['industry']
                existing_stock.is_active = True
                updated_count += 1
                logger.debug(f"Updated {stock_data['ticker']}")
            else:
                # Create new stock
                new_stock = StockMetadata(
                    ticker=stock_data['ticker'],
                    company_name=stock_data['company_name'],
                    sector=stock_data['sector'],
                    industry=stock_data['industry'],
                    is_active=True
                )
                session.add(new_stock)
                added_count += 1
                logger.debug(f"Added {stock_data['ticker']}")

        # Commit changes
        session.commit()

        # Print summary
        total_stocks = session.query(StockMetadata).count()
        logger.info(f"\n{'='*60}")
        logger.info(f"Stock Metadata Seeding Complete!")
        logger.info(f"{'='*60}")
        logger.info(f"Added: {added_count} stocks")
        logger.info(f"Updated: {updated_count} stocks")
        logger.info(f"Total stocks in database: {total_stocks}")

        # Print sector breakdown
        logger.info(f"\nSector Breakdown:")
        sectors = session.query(
            StockMetadata.sector,
            session.query(StockMetadata).filter_by(sector=StockMetadata.sector).count()
        ).distinct().all()

        for sector, count in sectors:
            sector_stocks = session.query(StockMetadata).filter_by(sector=sector).count()
            logger.info(f"  {sector}: {sector_stocks} stocks")

        logger.info(f"{'='*60}\n")

        return True

    except Exception as e:
        session.rollback()
        logger.error(f"❌ Seeding failed: {e}")
        raise
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    seed_stock_metadata()
