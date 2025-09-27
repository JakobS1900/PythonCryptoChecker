"""
Trading API for buying and selling cryptocurrencies with GEM currency.
Handles portfolio management and crypto trading with fees.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from database.database import get_db
from database.models import User, CryptoCurrency, PortfolioHolding, TransactionType
from crypto.portfolio import portfolio_manager
from crypto.price_service import price_service
from api.auth_api import get_current_user as get_current_user_optional

# Trading fee percentage (1% per trade)
TRADING_FEE_PERCENTAGE = 0.01

router = APIRouter(prefix="/api/trading", tags=["trading"])

# Request models
class BuyCryptoRequest(BaseModel):
    crypto_id: str = Field(..., description="Cryptocurrency ID to buy")
    gem_amount: float = Field(..., gt=0, description="Amount of GEMs to spend")

class SellCryptoRequest(BaseModel):
    holding_id: str = Field(..., description="Portfolio holding ID to sell")
    quantity_to_sell: float = Field(..., gt=0, description="Quantity of crypto to sell")

class PortfolioResponse(BaseModel):
    total_value_gem: float
    total_invested_gem: float
    total_profit_loss_gem: float
    total_profit_loss_percentage: float
    holdings: List[Dict[str, Any]]

@router.post("/buy", response_model=Dict[str, Any])
async def buy_cryptocurrency(
    request: BuyCryptoRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Buy cryptocurrency with GEMs."""

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for trading"
        )

    try:
        # Get cryptocurrency
        crypto = await db.get(CryptoCurrency, request.crypto_id)
        if not crypto or not crypto.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cryptocurrency not found or inactive"
            )

        if not crypto.current_price_usd:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cryptocurrency price not available"
            )

        # Calculate trading fee
        trading_fee = request.gem_amount * TRADING_FEE_PERCENTAGE
        total_cost = request.gem_amount + trading_fee

        # Check user balance
        user_balance = await portfolio_manager.get_user_balance(current_user.id)
        if user_balance < total_cost:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient balance. Required: {total_cost:.2f} GEM (including {trading_fee:.2f} GEM fee), Available: {user_balance:.2f} GEM"
            )

        # Calculate crypto quantity to buy
        # Convert USD price to GEM price
        crypto_price_gem = crypto.current_price_usd / portfolio_manager.gem_to_usd_rate
        crypto_quantity = request.gem_amount / crypto_price_gem

        # Deduct GEMs for purchase
        success = await portfolio_manager.deduct_gems(
            user_id=current_user.id,
            amount=total_cost,
            transaction_type=TransactionType.CRYPTO_BUY,
            description=f"Buy {crypto_quantity:.8f} {crypto.symbol.upper()} for {request.gem_amount:.2f} GEM (fee: {trading_fee:.2f} GEM)"
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to process payment"
            )

        # Get or create portfolio holding
        holding_result = await db.execute(
            select(PortfolioHolding).where(
                and_(
                    PortfolioHolding.user_id == current_user.id,
                    PortfolioHolding.crypto_id == crypto.id
                )
            )
        )
        holding = holding_result.scalar_one_or_none()

        if holding:
            # Update existing holding with average price calculation
            total_quantity = holding.quantity + crypto_quantity
            total_invested = holding.total_invested_gem + request.gem_amount

            holding.quantity = total_quantity
            holding.average_buy_price_gem = total_invested / total_quantity if total_quantity > 0 else 0
            holding.total_invested_gem = total_invested
        else:
            # Create new holding
            holding = PortfolioHolding(
                user_id=current_user.id,
                crypto_id=crypto.id,
                quantity=crypto_quantity,
                average_buy_price_gem=crypto_price_gem,
                total_invested_gem=request.gem_amount
            )
            db.add(holding)

        await db.commit()
        await db.refresh(holding)

        return {
            "success": True,
            "message": f"Successfully bought {crypto_quantity:.8f} {crypto.symbol.upper()}",
            "transaction": {
                "crypto_quantity": crypto_quantity,
                "gem_spent": request.gem_amount,
                "trading_fee": trading_fee,
                "total_cost": total_cost,
                "crypto_price_gem": crypto_price_gem,
                "crypto_symbol": crypto.symbol.upper()
            },
            "holding": holding.to_dict(current_price_usd=crypto.current_price_usd)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trading error: {str(e)}"
        )

@router.post("/sell", response_model=Dict[str, Any])
async def sell_cryptocurrency(
    request: SellCryptoRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Sell cryptocurrency for GEMs."""

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for trading"
        )

    try:
        # Get holding with crypto data
        holding_result = await db.execute(
            select(PortfolioHolding)
            .options(selectinload(PortfolioHolding.cryptocurrency))
            .where(
                and_(
                    PortfolioHolding.id == request.holding_id,
                    PortfolioHolding.user_id == current_user.id
                )
            )
        )
        holding = holding_result.scalar_one_or_none()

        if not holding:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio holding not found"
            )

        if holding.quantity < request.quantity_to_sell:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient quantity. Available: {holding.quantity:.8f}, Requested: {request.quantity_to_sell:.8f}"
            )

        crypto = holding.cryptocurrency
        if not crypto.current_price_usd:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cryptocurrency price not available"
            )

        # Calculate sale proceeds
        crypto_price_gem = crypto.current_price_usd / portfolio_manager.gem_to_usd_rate
        gross_proceeds = request.quantity_to_sell * crypto_price_gem

        # Calculate trading fee
        trading_fee = gross_proceeds * TRADING_FEE_PERCENTAGE
        net_proceeds = gross_proceeds - trading_fee

        # Update holding
        if holding.quantity == request.quantity_to_sell:
            # Selling entire holding
            await db.delete(holding)
        else:
            # Partial sale
            remaining_quantity = holding.quantity - request.quantity_to_sell
            proportion_sold = request.quantity_to_sell / holding.quantity

            holding.quantity = remaining_quantity
            holding.total_invested_gem -= (holding.total_invested_gem * proportion_sold)

        # Add GEMs to user wallet
        success = await portfolio_manager.add_gems(
            user_id=current_user.id,
            amount=net_proceeds,
            description=f"Sell {request.quantity_to_sell:.8f} {crypto.symbol.upper()} for {gross_proceeds:.2f} GEM (fee: {trading_fee:.2f} GEM)"
        )

        if not success:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process sale proceeds"
            )

        await db.commit()

        return {
            "success": True,
            "message": f"Successfully sold {request.quantity_to_sell:.8f} {crypto.symbol.upper()}",
            "transaction": {
                "crypto_quantity_sold": request.quantity_to_sell,
                "gross_proceeds_gem": gross_proceeds,
                "trading_fee": trading_fee,
                "net_proceeds_gem": net_proceeds,
                "crypto_price_gem": crypto_price_gem,
                "crypto_symbol": crypto.symbol.upper()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trading error: {str(e)}"
        )
@router.get("/portfolio", response_model=PortfolioResponse)
async def get_user_portfolio(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Get user's cryptocurrency portfolio."""

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view portfolio"
        )

    try:
        # Get all holdings with crypto data
        holdings_result = await db.execute(
            select(PortfolioHolding)
            .options(selectinload(PortfolioHolding.cryptocurrency))
            .where(PortfolioHolding.user_id == current_user.id)
            .order_by(PortfolioHolding.created_at.desc())
        )
        holdings = holdings_result.scalars().all()

        total_value_gem = 0.0
        total_invested_gem = 0.0
        holdings_data = []

        for holding in holdings:
            crypto = holding.cryptocurrency
            current_price_usd = crypto.current_price_usd if crypto else 0.0

            holding_data = holding.to_dict(
                include_crypto_data=True,
                current_price_usd=current_price_usd
            )
            holdings_data.append(holding_data)

            # Add to totals
            total_invested_gem += holding.total_invested_gem
            if current_price_usd:
                total_value_gem += holding.calculate_current_value_gem(current_price_usd)

        total_profit_loss_gem = total_value_gem - total_invested_gem
        total_profit_loss_percentage = (total_profit_loss_gem / total_invested_gem * 100) if total_invested_gem > 0 else 0.0

        return PortfolioResponse(
            total_value_gem=round(total_value_gem, 2),
            total_invested_gem=round(total_invested_gem, 2),
            total_profit_loss_gem=round(total_profit_loss_gem, 2),
            total_profit_loss_percentage=round(total_profit_loss_percentage, 2),
            holdings=holdings_data
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portfolio error: {str(e)}"
        )

@router.get("/fees", response_model=Dict[str, Any])
async def get_trading_fees():
    """Get current trading fees."""
    return {
        "trading_fee_percentage": TRADING_FEE_PERCENTAGE * 100,  # Convert to percentage
        "description": f"Trading fee: {TRADING_FEE_PERCENTAGE * 100}% per transaction"
    }