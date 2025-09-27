"""
Cryptocurrency API endpoints.
Real-time price tracking, conversion, and portfolio management.
"""

import os
from typing import Optional, Dict, Any
from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Query,
    status
)
from pydantic import BaseModel, Field
from database.models import User
from crypto.price_service import price_service
from crypto.converter import crypto_converter
from crypto.portfolio import portfolio_manager
from api.auth_api import get_current_user
from database.models import User

router = APIRouter()

# ==================== PORTFOLIO ENDPOINTS ====================


router = APIRouter()

# ==================== PORTFOLIO ENDPOINTS ====================

@router.get("/portfolio/stats", response_model=Dict[str, Any])
async def portfolio_stats_api(
    current_user: Optional[User] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get user's portfolio statistics for profile page."""
    if not current_user:
        guest_gems = int(os.getenv("GUEST_MODE_GEMS", "5000"))
        return {
            "success": True,
            "stats": {
                "total_transactions": 0,
                "games_won": 0,
                "games_lost": 0,
                "total_games": 0,
                "win_rate": 0,
                "net_gambling": 0,
                "gem_value_usd": guest_gems * 0.01
            },
            "wallet": {
                "gem_balance": guest_gems,
                "total_deposited": 0,
                "total_withdrawn": 0,
                "total_wagered": 0,
                "total_won": 0
            },
            "is_guest": True
        }
    try:
        stats = await portfolio_manager.get_portfolio_stats(str(current_user.id))
        return {
            "success": True,
            "stats": stats.get("stats", {}),
            "wallet": stats.get("wallet", {}),
            "is_guest": False
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching portfolio stats: {str(e)}"
        )

# ==================== REQUEST/RESPONSE MODELS ====================

class ConversionRequest(BaseModel):
    from_currency: str = Field(..., description="Source currency (e.g., BTC, USD)")
    to_currency: str = Field(..., description="Target currency (e.g., ETH, EUR)")
    amount: float = Field(..., gt=0, description="Amount to convert")

class ConversionResponse(BaseModel):
    from_currency: str
    to_currency: str
    from_amount: float
    to_amount: float
    conversion_type: str
    rate: float
    timestamp: str

class AddGemsRequest(BaseModel):
    amount: float = Field(..., gt=0, le=10000, description="Amount of GEMs to add")
    description: Optional[str] = Field(None, description="Transaction description")

# ==================== CRYPTO PRICE ENDPOINTS ====================

@router.get("/prices")
async def get_crypto_prices(
    limit: int = Query(50, ge=1, le=100, description="Number of cryptocurrencies to return"),
    search: Optional[str] = Query(None, description="Search by name or symbol")
):
    """Get current cryptocurrency prices."""
    try:
        if search:
            cryptos = await price_service.search_cryptos(search, limit)
        else:
            cryptos = await price_service.get_all_cryptos()
            cryptos = cryptos[:limit]

        return {
            "success": True,
            "data": cryptos,
            "count": len(cryptos),
            "search_query": search
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching prices: {str(e)}")

@router.get("/prices/{crypto_id}")
async def get_crypto_price(crypto_id: str):
    """Get price for a specific cryptocurrency."""
    try:
        price = await price_service.get_price(crypto_id.lower())
        if price is None:
            raise HTTPException(status_code=404, detail="Cryptocurrency not found")

        return {
            "success": True,
            "crypto_id": crypto_id.lower(),
            "price_usd": price,
            "timestamp": "now"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching price: {str(e)}")

@router.get("/trending")
async def get_trending_cryptos(limit: int = Query(10, ge=1, le=20)):
    """Get trending cryptocurrencies by market cap."""
    try:
        cryptos = await price_service.get_all_cryptos()

        # Filter out cryptos without market cap and sort by market cap
        trending = [
            crypto for crypto in cryptos
            if crypto.get("market_cap") is not None
        ]
        trending.sort(key=lambda x: x.get("market_cap", 0), reverse=True)

        return {
            "success": True,
            "data": trending[:limit],
            "count": len(trending[:limit])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trending: {str(e)}")

# ==================== CURRENCY CONVERSION ENDPOINTS ====================

@router.post("/convert", response_model=ConversionResponse)
async def convert_currency(conversion: ConversionRequest):
    """Convert between cryptocurrencies and fiat currencies."""
    try:
        result = await crypto_converter.universal_convert(
            from_currency=conversion.from_currency,
            to_currency=conversion.to_currency,
            amount=conversion.amount
        )

        if result is None:
            raise HTTPException(
                status_code=400,
                detail="Conversion failed. Please check currency codes and try again."
            )

        return ConversionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting: {str(e)}")

@router.get("/convert/{from_currency}/{to_currency}")
async def quick_convert(
    from_currency: str,
    to_currency: str,
    amount: float = Query(..., gt=0, description="Amount to convert")
):
    """Quick conversion endpoint for simple conversions."""
    try:
        result = await crypto_converter.universal_convert(
            from_currency=from_currency,
            to_currency=to_currency,
            amount=amount
        )

        if result is None:
            raise HTTPException(
                status_code=400,
                detail="Conversion failed. Please check currency codes."
            )

        return {
            "success": True,
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting: {str(e)}")

@router.get("/currencies/fiat")
async def get_supported_fiat():
    """Get list of supported fiat currencies."""
    try:
        fiat_currencies = crypto_converter.get_supported_fiat_currencies()
        return {
            "success": True,
            "currencies": fiat_currencies,
            "count": len(fiat_currencies)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching fiat currencies: {str(e)}")

@router.get("/currencies/crypto")
async def get_supported_crypto():
    """Get list of supported cryptocurrencies."""
    try:
        crypto_currencies = await crypto_converter.get_supported_crypto_currencies()
        return {
            "success": True,
            "currencies": crypto_currencies,
            "count": len(crypto_currencies)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching cryptocurrencies: {str(e)}")

@router.get("/popular-pairs")
async def get_popular_pairs():
    """Get popular conversion pairs."""
    try:
        pairs = await crypto_converter.get_popular_pairs()
        return {
            "success": True,
            "pairs": pairs
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching popular pairs: {str(e)}")

# ==================== PORTFOLIO ENDPOINTS ====================

@router.get("/portfolio")
async def get_portfolio(current_user: Optional[User] = Depends(get_current_user)):
    """Get user's portfolio information."""
    if not current_user:
        # Guest mode portfolio
        guest_gems = int(os.getenv("GUEST_MODE_GEMS", "5000"))
        return {
            "success": True,
            "portfolio": {
                "wallet": {
                    "gem_balance": guest_gems,
                    "total_deposited": 0,
                    "total_withdrawn": 0,
                    "total_wagered": 0,
                    "total_won": 0
                },
                "stats": {
                    "total_transactions": 0,
                    "games_won": 0,
                    "games_lost": 0,
                    "total_games": 0,
                    "win_rate": 0,
                    "net_gambling": 0,
                    "gem_value_usd": guest_gems * 0.01
                },
                "is_guest": True
            }
        }

    try:
        portfolio_stats = await portfolio_manager.get_portfolio_stats(str(current_user.id))
        return {
            "success": True,
            "portfolio": portfolio_stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching portfolio: {str(e)}")

@router.get("/portfolio/transactions")
async def get_transaction_history(
    current_user: Optional[User] = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get user's transaction history."""
    if not current_user:
        return {
            "success": True,
            "transactions": [],
            "count": 0,
            "message": "Transaction history not available in guest mode"
        }

    try:
        transactions = await portfolio_manager.get_transaction_history(
            str(current_user.id), limit, offset
        )

        return {
            "success": True,
            "transactions": transactions,
            "count": len(transactions),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {str(e)}")

@router.post("/portfolio/add-gems")
async def add_gems_to_wallet(
    request: AddGemsRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Add GEMs to user's wallet (admin/testing function)."""
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required to add GEMs"
        )

    try:
        success = await portfolio_manager.add_gems(
            user_id=str(current_user.id),
            amount=request.amount,
            description=request.description or f"Manual GEM deposit: {request.amount}"
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to add GEMs")

        # Get updated balance
        new_balance = await portfolio_manager.get_user_balance(str(current_user.id))

        return {
            "success": True,
            "message": f"Added {request.amount} GEMs to wallet",
            "new_balance": new_balance,
            "amount_added": request.amount
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding GEMs: {str(e)}")

@router.get("/portfolio/balance")
async def get_wallet_balance(current_user: Optional[User] = Depends(get_current_user)):
    """Get current wallet balance."""
    if not current_user:
        guest_gems = int(os.getenv("GUEST_MODE_GEMS", "5000"))
        return {
            "success": True,
            "balance": guest_gems,
            "balance_usd": guest_gems * 0.01,
            "is_guest": True
        }

    try:
        balance = await portfolio_manager.get_user_balance(str(current_user.id))
        return {
            "success": True,
            "balance": balance,
            "balance_usd": portfolio_manager.gem_to_usd(balance),
            "is_guest": False
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching balance: {str(e)}")

# ==================== MARKET DATA ENDPOINTS ====================

@router.get("/market/status")
async def get_market_status():
    """Get overall market status and service health."""
    try:
        cryptos = await price_service.get_all_cryptos()
        active_cryptos = len([c for c in cryptos if c.get("current_price_usd")])

        return {
            "success": True,
            "market_status": "active",
            "price_service_status": "running" if price_service.is_running else "stopped",
            "total_cryptocurrencies": len(cryptos),
            "active_prices": active_cryptos,
            "supported_conversions": {
                "crypto_pairs": active_cryptos * (active_cryptos - 1),
                "fiat_currencies": len(crypto_converter.get_supported_fiat_currencies()),
                "total_pairs": "10,000+"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching market status: {str(e)}")

@router.get("/search")
async def search_cryptocurrencies(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50)
):
    """Search cryptocurrencies by name or symbol."""
    try:
        results = await price_service.search_cryptos(q, limit)
        return {
            "success": True,
            "query": q,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching: {str(e)}")
