"""
Portfolio API endpoints for crypto portfolio tracking with GEMs integration.
Migrated from EmusPythonCryptoChecker v1 with enhanced virtual economy.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime

from database.database_manager import get_db_session
from database.unified_models import (
    User, UserPortfolio, PortfolioHolding, PortfolioTransaction,
    CryptoAsset, VirtualWallet, VirtualTransaction, CurrencyType
)
from services.market_data_service import market_data_service
from auth.auth_manager import AuthenticationManager, get_current_user
from logger import logger

router = APIRouter()
security = HTTPBearer()
auth_manager = AuthenticationManager()


# ==================== REQUEST/RESPONSE MODELS ====================

class PortfolioSummaryResponse(BaseModel):
    total_value_usd: float
    total_invested: float
    total_pnl: float
    total_pnl_percentage: float
    total_transactions: int
    holdings_count: int
    best_performing_asset: Optional[str]
    worst_performing_asset: Optional[str]


class HoldingResponse(BaseModel):
    asset_id: str
    symbol: str
    name: str
    quantity: float
    average_buy_price: float
    current_price: float
    current_value: float
    total_cost: float
    unrealized_pnl: float
    unrealized_pnl_percentage: float
    first_purchase_date: Optional[datetime]


class AddTransactionRequest(BaseModel):
    asset_id: str = Field(..., description="Cryptocurrency asset ID")
    transaction_type: str = Field(..., description="BUY or SELL")
    quantity: float = Field(..., gt=0, description="Amount of crypto")
    price_per_coin: float = Field(..., gt=0, description="Price per coin in USD")
    use_gems: bool = Field(default=True, description="Use GEMs for virtual purchase")
    notes: Optional[str] = Field(None, description="Transaction notes")


class TransactionResponse(BaseModel):
    id: str
    asset_id: str
    asset_symbol: str
    asset_name: str
    transaction_type: str
    quantity: float
    price_per_coin: float
    total_amount: float
    gems_used: float
    is_virtual_transaction: bool
    notes: Optional[str]
    created_at: datetime


class MarketDataResponse(BaseModel):
    id: str
    symbol: str
    name: str
    price: float
    change_24h: float
    change_24h_percent: float
    market_cap: float
    image_url: Optional[str]


# ==================== UTILITY FUNCTIONS ====================

async def get_user_portfolio(session: AsyncSession, user_id: str) -> UserPortfolio:
    """Get or create user portfolio."""
    stmt = select(UserPortfolio).where(UserPortfolio.user_id == user_id)
    result = await session.execute(stmt)
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        # Create new portfolio
        portfolio = UserPortfolio(
            user_id=user_id,
            name="My Portfolio",
            base_currency="USD"
        )
        session.add(portfolio)
        await session.flush()

    return portfolio


async def get_user_wallet(session: AsyncSession, user_id: str) -> VirtualWallet:
    """Get user's virtual wallet."""
    stmt = select(VirtualWallet).where(VirtualWallet.user_id == user_id)
    result = await session.execute(stmt)
    wallet = result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User wallet not found"
        )

    return wallet


async def calculate_gems_cost(usd_amount: float) -> float:
    """Calculate GEMs cost for USD amount. 1,000 GEM = $10 USD."""
    return usd_amount * 100  # $1 USD = 100 GEMs


async def update_portfolio_metrics(session: AsyncSession, portfolio: UserPortfolio):
    """Update portfolio performance metrics."""
    # Get all holdings
    stmt = select(PortfolioHolding).where(PortfolioHolding.portfolio_id == portfolio.id)
    result = await session.execute(stmt)
    holdings = result.scalars().all()

    total_value = 0.0
    total_cost = 0.0
    best_asset = None
    worst_asset = None
    best_pnl_pct = float('-inf')
    worst_pnl_pct = float('inf')

    for holding in holdings:
        if holding.quantity > 0:
            current_value = holding.current_value
            cost = holding.total_cost
            total_value += current_value
            total_cost += cost

            # Track best/worst performing assets
            if holding.unrealized_pnl_percentage > best_pnl_pct:
                best_pnl_pct = holding.unrealized_pnl_percentage
                best_asset = holding.asset_id
            if holding.unrealized_pnl_percentage < worst_pnl_pct:
                worst_pnl_pct = holding.unrealized_pnl_percentage
                worst_asset = holding.asset_id

    # Update portfolio metrics
    portfolio.total_value_usd = total_value
    portfolio.total_invested = total_cost
    portfolio.total_pnl = total_value - total_cost
    portfolio.total_pnl_percentage = ((total_value / total_cost) - 1) * 100 if total_cost > 0 else 0.0
    portfolio.best_performing_asset = best_asset
    portfolio.worst_performing_asset = worst_asset
    portfolio.updated_at = datetime.utcnow()


# ==================== API ENDPOINTS ====================

async def get_current_user_id(
    current_user: User = Depends(get_current_user)
) -> str:
    """Extract user ID from authenticated user."""
    return current_user.id


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get user's portfolio summary."""
    try:
        portfolio = await get_user_portfolio(session, user_id)

        # Count holdings with quantity > 0
        stmt = select(func.count(PortfolioHolding.id)).where(
            and_(
                PortfolioHolding.portfolio_id == portfolio.id,
                PortfolioHolding.quantity > 0
            )
        )
        result = await session.execute(stmt)
        holdings_count = result.scalar() or 0

        return PortfolioSummaryResponse(
            total_value_usd=portfolio.total_value_usd,
            total_invested=portfolio.total_invested,
            total_pnl=portfolio.total_pnl,
            total_pnl_percentage=portfolio.total_pnl_percentage,
            total_transactions=portfolio.total_transactions,
            holdings_count=holdings_count,
            best_performing_asset=portfolio.best_performing_asset,
            worst_performing_asset=portfolio.worst_performing_asset
        )

    except Exception as e:
        logger.error(f"Error getting portfolio summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get portfolio summary"
        )


@router.get("/holdings", response_model=List[HoldingResponse])
async def get_portfolio_holdings(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get user's portfolio holdings."""
    try:
        portfolio = await get_user_portfolio(session, user_id)

        # Get holdings with asset information
        stmt = select(PortfolioHolding, CryptoAsset).join(
            CryptoAsset, PortfolioHolding.asset_id == CryptoAsset.id
        ).where(
            and_(
                PortfolioHolding.portfolio_id == portfolio.id,
                PortfolioHolding.quantity > 0
            )
        ).order_by(PortfolioHolding.current_value.desc())

        result = await session.execute(stmt)
        holdings_data = result.all()

        holdings = []
        for holding, asset in holdings_data:
            # Update current price from asset data
            holding.current_price = asset.current_price_usd
            holding.current_value = holding.quantity * asset.current_price_usd
            holding.unrealized_pnl = holding.current_value - holding.total_cost
            holding.unrealized_pnl_percentage = ((holding.current_value / holding.total_cost) - 1) * 100 if holding.total_cost > 0 else 0.0

            holdings.append(HoldingResponse(
                asset_id=holding.asset_id,
                symbol=asset.symbol,
                name=asset.name,
                quantity=holding.quantity,
                average_buy_price=holding.average_buy_price,
                current_price=holding.current_price,
                current_value=holding.current_value,
                total_cost=holding.total_cost,
                unrealized_pnl=holding.unrealized_pnl,
                unrealized_pnl_percentage=holding.unrealized_pnl_percentage,
                first_purchase_date=holding.first_purchase_date
            ))

        # Update portfolio metrics
        await update_portfolio_metrics(session, portfolio)
        await session.commit()

        return holdings

    except Exception as e:
        logger.error(f"Error getting portfolio holdings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get portfolio holdings"
        )


@router.post("/transactions", response_model=TransactionResponse)
async def add_portfolio_transaction(
    transaction_data: AddTransactionRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Add a new portfolio transaction using GEMs."""
    try:
        # Get user portfolio and wallet
        portfolio = await get_user_portfolio(session, user_id)
        wallet = await get_user_wallet(session, user_id)

        # Get asset information
        stmt = select(CryptoAsset).where(CryptoAsset.id == transaction_data.asset_id)
        result = await session.execute(stmt)
        asset = result.scalar_one_or_none()

        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cryptocurrency asset not found"
            )

        # Calculate transaction amounts
        total_amount = transaction_data.quantity * transaction_data.price_per_coin
        gems_required = await calculate_gems_cost(total_amount)

        # Check if user has enough GEMs for purchase
        if transaction_data.use_gems and transaction_data.transaction_type.upper() == "BUY":
            if wallet.gem_coins < gems_required:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient GEMs. Required: {gems_required:.2f}, Available: {wallet.gem_coins:.2f}"
                )

        # Get or create portfolio holding
        stmt = select(PortfolioHolding).where(
            and_(
                PortfolioHolding.portfolio_id == portfolio.id,
                PortfolioHolding.asset_id == transaction_data.asset_id
            )
        )
        result = await session.execute(stmt)
        holding = result.scalar_one_or_none()

        if not holding:
            holding = PortfolioHolding(
                portfolio_id=portfolio.id,
                asset_id=transaction_data.asset_id,
                quantity=0.0,
                average_buy_price=0.0,
                total_cost=0.0
            )
            session.add(holding)

        # Process transaction
        if transaction_data.transaction_type.upper() == "BUY":
            # Calculate new average buy price
            new_total_cost = holding.total_cost + total_amount
            new_quantity = holding.quantity + transaction_data.quantity
            new_avg_price = new_total_cost / new_quantity if new_quantity > 0 else 0

            holding.quantity = new_quantity
            holding.total_cost = new_total_cost
            holding.average_buy_price = new_avg_price

            if not holding.first_purchase_date:
                holding.first_purchase_date = datetime.utcnow()

            # Deduct GEMs if using virtual currency
            if transaction_data.use_gems:
                wallet.gem_coins -= gems_required
                wallet.total_gems_spent += gems_required

                # Record GEMs transaction
                gems_transaction = VirtualTransaction(
                    wallet_id=wallet.id,
                    transaction_type="PORTFOLIO_PURCHASE",
                    currency_type=CurrencyType.GEM_COINS.value,
                    amount=-gems_required,
                    source="PORTFOLIO_TRACKER",
                    description=f"Virtual purchase of {transaction_data.quantity} {asset.symbol}",
                    balance_before=wallet.gem_coins + gems_required,
                    balance_after=wallet.gem_coins
                )
                session.add(gems_transaction)

        elif transaction_data.transaction_type.upper() == "SELL":
            if holding.quantity < transaction_data.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient holdings. Available: {holding.quantity}, Requested: {transaction_data.quantity}"
                )

            # Calculate cost basis for sold portion
            cost_per_unit = holding.total_cost / holding.quantity if holding.quantity > 0 else 0
            sold_cost = transaction_data.quantity * cost_per_unit

            holding.quantity -= transaction_data.quantity
            holding.total_cost -= sold_cost

            # Add GEMs if selling virtual holdings
            if transaction_data.use_gems:
                wallet.gem_coins += gems_required
                wallet.total_gems_earned += gems_required

                # Record GEMs transaction
                gems_transaction = VirtualTransaction(
                    wallet_id=wallet.id,
                    transaction_type="PORTFOLIO_SALE",
                    currency_type=CurrencyType.GEM_COINS.value,
                    amount=gems_required,
                    source="PORTFOLIO_TRACKER",
                    description=f"Virtual sale of {transaction_data.quantity} {asset.symbol}",
                    balance_before=wallet.gem_coins - gems_required,
                    balance_after=wallet.gem_coins
                )
                session.add(gems_transaction)

        # Record portfolio transaction
        portfolio_transaction = PortfolioTransaction(
            portfolio_id=portfolio.id,
            asset_id=transaction_data.asset_id,
            transaction_type=transaction_data.transaction_type.upper(),
            quantity=transaction_data.quantity,
            price_per_coin=transaction_data.price_per_coin,
            total_amount=total_amount,
            gems_used=gems_required if transaction_data.use_gems else 0.0,
            is_virtual_transaction=transaction_data.use_gems,
            notes=transaction_data.notes,
            source="MANUAL"
        )
        session.add(portfolio_transaction)

        # Update holding timestamps
        holding.last_transaction_date = datetime.utcnow()
        holding.updated_at = datetime.utcnow()

        # Update portfolio transaction count
        portfolio.total_transactions += 1

        await session.commit()

        return TransactionResponse(
            id=portfolio_transaction.id,
            asset_id=portfolio_transaction.asset_id,
            asset_symbol=asset.symbol,
            asset_name=asset.name,
            transaction_type=portfolio_transaction.transaction_type,
            quantity=portfolio_transaction.quantity,
            price_per_coin=portfolio_transaction.price_per_coin,
            total_amount=portfolio_transaction.total_amount,
            gems_used=portfolio_transaction.gems_used,
            is_virtual_transaction=portfolio_transaction.is_virtual_transaction,
            notes=portfolio_transaction.notes,
            created_at=portfolio_transaction.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error adding portfolio transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add portfolio transaction"
        )


@router.get("/transactions", response_model=List[TransactionResponse])
async def get_portfolio_transactions(
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get user's portfolio transaction history."""
    try:
        portfolio = await get_user_portfolio(session, user_id)

        stmt = select(PortfolioTransaction, CryptoAsset).join(
            CryptoAsset, PortfolioTransaction.asset_id == CryptoAsset.id
        ).where(
            PortfolioTransaction.portfolio_id == portfolio.id
        ).order_by(
            PortfolioTransaction.created_at.desc()
        ).offset(offset).limit(limit)

        result = await session.execute(stmt)
        transactions_data = result.all()

        transactions = []
        for transaction, asset in transactions_data:
            transactions.append(TransactionResponse(
                id=transaction.id,
                asset_id=transaction.asset_id,
                asset_symbol=asset.symbol,
                asset_name=asset.name,
                transaction_type=transaction.transaction_type,
                quantity=transaction.quantity,
                price_per_coin=transaction.price_per_coin,
                total_amount=transaction.total_amount,
                gems_used=transaction.gems_used,
                is_virtual_transaction=transaction.is_virtual_transaction,
                notes=transaction.notes,
                created_at=transaction.created_at
            ))

        return transactions

    except Exception as e:
        logger.error(f"Error getting portfolio transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get portfolio transactions"
        )


@router.delete("/transactions/{transaction_id}")
async def delete_portfolio_transaction(
    transaction_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Delete a portfolio transaction (for corrections)."""
    try:
        portfolio = await get_user_portfolio(session, user_id)

        # Get transaction
        stmt = select(PortfolioTransaction).where(
            and_(
                PortfolioTransaction.id == transaction_id,
                PortfolioTransaction.portfolio_id == portfolio.id
            )
        )
        result = await session.execute(stmt)
        transaction = result.scalar_one_or_none()

        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )

        # Note: This is a simplified deletion. In production, you might want to
        # reverse the effects on holdings and wallet balances.
        await session.delete(transaction)
        portfolio.total_transactions = max(0, portfolio.total_transactions - 1)

        await session.commit()

        return {"message": "Transaction deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting portfolio transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete portfolio transaction"
        )


@router.get("/market/overview", response_model=List[MarketDataResponse])
async def get_market_overview(
    limit: int = 200,
    vs_currency: str = "USD",
    refresh: bool = False,
    session: AsyncSession = Depends(get_db_session)
):
    """Get cryptocurrency market overview."""
    try:
        coins_data, source_info = await market_data_service.get_market_overview(
            session, vs_currency, force_refresh=refresh
        )

        market_data = []
        for coin in coins_data[:limit]:
            market_data.append(MarketDataResponse(
                id=coin["id"],
                symbol=coin["symbol"],
                name=coin["name"],
                price=coin["price"],
                change_24h=coin.get("change_24h", 0),
                change_24h_percent=coin.get("change_24h_percent", 0),
                market_cap=coin.get("market_cap", 0),
                image_url=coin.get("image_url")
            ))

        logger.info(f"Returned {len(market_data)} market data items (source: {source_info})")
        return market_data

    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get market overview"
        )