"""
P2P Trading API - RESTful endpoints for peer-to-peer cryptocurrency trading.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from auth.middleware import get_current_user
from .p2p_marketplace import p2p_marketplace, TradeOfferType, PortfolioError, InsufficientFundsError, InvalidTradeError
from logger import logger

router = APIRouter()
security = HTTPBearer()


# Pydantic Models
class CreateTradeOfferRequest(BaseModel):
    offer_type: str = Field(..., pattern="^(BUY|SELL|SWAP)$", description="Type of trade offer")
    crypto_symbol: str = Field(..., description="Cryptocurrency symbol")
    crypto_amount: float = Field(..., gt=0, description="Amount of cryptocurrency")
    price_per_unit: Optional[float] = Field(None, gt=0, description="Price per unit in GEMs (required for BUY/SELL)")
    wanted_crypto_symbol: Optional[str] = Field(None, description="Wanted crypto symbol (required for SWAP)")
    wanted_crypto_amount: Optional[float] = Field(None, gt=0, description="Wanted crypto amount (required for SWAP)")
    duration_hours: int = Field(default=24, ge=1, le=168, description="Offer duration in hours (1-168)")
    min_trade_amount: float = Field(default=0.0, ge=0, description="Minimum trade amount")
    is_partial_fill_allowed: bool = Field(default=True, description="Allow partial fills")
    description: str = Field(default="", max_length=500, description="Optional description")
    tags: List[str] = Field(default=[], description="Optional tags")


class AcceptTradeOfferRequest(BaseModel):
    offer_id: str = Field(..., description="Trade offer ID to accept")
    trade_amount: Optional[float] = Field(None, gt=0, description="Amount to trade (optional for full fill)")


class MarketplaceFilters(BaseModel):
    offer_type: Optional[str] = Field(None, pattern="^(BUY|SELL|SWAP)$")
    crypto_symbol: Optional[str] = None
    min_amount: Optional[float] = Field(None, ge=0)
    max_amount: Optional[float] = Field(None, ge=0)
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


@router.post("/offers", response_model=Dict[str, Any])
async def create_trade_offer(
    request: CreateTradeOfferRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new peer-to-peer trade offer."""
    try:
        # Convert string to enum
        offer_type = TradeOfferType(request.offer_type)
        
        result = await p2p_marketplace.create_trade_offer(
            user_id=current_user["user_id"],
            offer_type=offer_type,
            crypto_symbol=request.crypto_symbol,
            crypto_amount=request.crypto_amount,
            price_per_unit=request.price_per_unit,
            wanted_crypto_symbol=request.wanted_crypto_symbol,
            wanted_crypto_amount=request.wanted_crypto_amount,
            duration_hours=request.duration_hours,
            min_trade_amount=request.min_trade_amount,
            is_partial_fill_allowed=request.is_partial_fill_allowed,
            description=request.description,
            tags=request.tags
        )
        
        return {
            "success": True,
            "data": result,
            "message": f"Successfully created {request.offer_type} offer"
        }
        
    except InvalidTradeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InsufficientFundsError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except PortfolioError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid offer type: {request.offer_type}")
    except Exception as e:
        logger.error(f"Create offer endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/offers", response_model=Dict[str, Any])
async def get_marketplace_offers(
    offer_type: Optional[str] = Query(None, regex="^(BUY|SELL|SWAP)$"),
    crypto_symbol: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None, ge=0),
    max_amount: Optional[float] = Query(None, ge=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get marketplace trade offers with filtering."""
    try:
        # Convert string to enum if provided
        offer_type_enum = TradeOfferType(offer_type) if offer_type else None
        
        result = await p2p_marketplace.get_marketplace_offers(
            offer_type=offer_type_enum,
            crypto_symbol=crypto_symbol,
            min_amount=min_amount,
            max_amount=max_amount,
            min_price=min_price,
            max_price=max_price,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid offer type: {offer_type}")
    except Exception as e:
        logger.error(f"Get offers endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/offers/accept", response_model=Dict[str, Any])
async def accept_trade_offer(
    request: AcceptTradeOfferRequest,
    current_user: dict = Depends(get_current_user)
):
    """Accept a trade offer and execute the trade."""
    try:
        result = await p2p_marketplace.accept_trade_offer(
            user_id=current_user["user_id"],
            offer_id=request.offer_id,
            trade_amount=request.trade_amount
        )
        
        return {
            "success": True,
            "data": result,
            "message": "Trade executed successfully"
        }
        
    except InvalidTradeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InsufficientFundsError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except PortfolioError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Accept offer endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/offers/{offer_id}", response_model=Dict[str, Any])
async def cancel_trade_offer(
    offer_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancel a user's trade offer."""
    try:
        success = await p2p_marketplace.cancel_trade_offer(
            user_id=current_user["user_id"],
            offer_id=offer_id
        )
        
        if success:
            return {
                "success": True,
                "message": "Trade offer cancelled successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel trade offer")
            
    except InvalidTradeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PortfolioError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Cancel offer endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/my-offers", response_model=Dict[str, Any])
async def get_user_offers(
    status: Optional[str] = Query(None, regex="^(ACTIVE|COMPLETED|CANCELLED|EXPIRED)$"),
    current_user: dict = Depends(get_current_user)
):
    """Get all trade offers created by the current user."""
    try:
        offers = await p2p_marketplace.get_user_offers(
            user_id=current_user["user_id"],
            status=status
        )
        
        return {
            "success": True,
            "data": {
                "offers": offers,
                "total_count": len(offers)
            }
        }
        
    except PortfolioError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Get user offers endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/offers/{offer_id}", response_model=Dict[str, Any])
async def get_trade_offer_details(offer_id: str):
    """Get detailed information about a specific trade offer."""
    try:
        # Get offers with specific ID filter
        result = await p2p_marketplace.get_marketplace_offers(limit=1)
        
        # Find the specific offer
        offer = None
        for o in result["offers"]:
            if o["offer_id"] == offer_id:
                offer = o
                break
        
        if not offer:
            raise HTTPException(status_code=404, detail="Trade offer not found")
        
        return {
            "success": True,
            "data": offer
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get offer details endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/marketplace/stats", response_model=Dict[str, Any])
async def get_marketplace_statistics():
    """Get marketplace statistics and metrics."""
    try:
        stats = await p2p_marketplace.get_marketplace_stats()
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Marketplace stats endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/offers/search/{crypto_symbol}", response_model=Dict[str, Any])
async def search_offers_by_crypto(
    crypto_symbol: str,
    offer_type: Optional[str] = Query(None, regex="^(BUY|SELL|SWAP)$"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    limit: int = Query(20, ge=1, le=50)
):
    """Search trade offers for a specific cryptocurrency."""
    try:
        offer_type_enum = TradeOfferType(offer_type) if offer_type else None
        
        result = await p2p_marketplace.get_marketplace_offers(
            offer_type=offer_type_enum,
            crypto_symbol=crypto_symbol.upper(),
            min_price=min_price,
            max_price=max_price,
            limit=limit,
            offset=0
        )
        
        # Add market analysis
        offers = result["offers"]
        if offers:
            prices = [o["price_per_unit"] for o in offers if o.get("price_per_unit")]
            if prices:
                market_analysis = {
                    "average_price": sum(prices) / len(prices),
                    "min_price": min(prices),
                    "max_price": max(prices),
                    "total_offers": len(offers),
                    "buy_offers": len([o for o in offers if o["offer_type"] == "BUY"]),
                    "sell_offers": len([o for o in offers if o["offer_type"] == "SELL"]),
                    "swap_offers": len([o for o in offers if o["offer_type"] == "SWAP"])
                }
            else:
                market_analysis = {
                    "total_offers": len(offers),
                    "buy_offers": len([o for o in offers if o["offer_type"] == "BUY"]),
                    "sell_offers": len([o for o in offers if o["offer_type"] == "SELL"]),
                    "swap_offers": len([o for o in offers if o["offer_type"] == "SWAP"])
                }
        else:
            market_analysis = {"total_offers": 0}
        
        return {
            "success": True,
            "data": {
                "crypto_symbol": crypto_symbol.upper(),
                "offers": offers,
                "market_analysis": market_analysis
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid offer type: {offer_type}")
    except Exception as e:
        logger.error(f"Search offers endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/best-offers/{crypto_symbol}", response_model=Dict[str, Any])
async def get_best_offers(crypto_symbol: str):
    """Get the best buy and sell offers for a cryptocurrency."""
    try:
        # Get buy offers (highest price first)
        buy_offers = await p2p_marketplace.get_marketplace_offers(
            offer_type=TradeOfferType.BUY,
            crypto_symbol=crypto_symbol.upper(),
            limit=5
        )
        
        # Get sell offers (lowest price first)
        sell_offers = await p2p_marketplace.get_marketplace_offers(
            offer_type=TradeOfferType.SELL,
            crypto_symbol=crypto_symbol.upper(),
            limit=5
        )
        
        # Sort buy offers by price (highest first)
        buy_offers["offers"].sort(key=lambda x: x.get("price_per_unit", 0), reverse=True)
        
        # Sort sell offers by price (lowest first)
        sell_offers["offers"].sort(key=lambda x: x.get("price_per_unit", float('inf')))
        
        # Calculate spread
        best_buy = buy_offers["offers"][0] if buy_offers["offers"] else None
        best_sell = sell_offers["offers"][0] if sell_offers["offers"] else None
        
        spread = None
        if best_buy and best_sell:
            spread = {
                "absolute": best_sell["price_per_unit"] - best_buy["price_per_unit"],
                "percentage": ((best_sell["price_per_unit"] - best_buy["price_per_unit"]) / best_buy["price_per_unit"]) * 100
            }
        
        return {
            "success": True,
            "data": {
                "crypto_symbol": crypto_symbol.upper(),
                "best_buy_offers": buy_offers["offers"][:3],
                "best_sell_offers": sell_offers["offers"][:3],
                "spread": spread,
                "market_depth": {
                    "total_buy_offers": buy_offers["total_count"],
                    "total_sell_offers": sell_offers["total_count"]
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Best offers endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/cleanup/expired", response_model=Dict[str, Any])
async def cleanup_expired_offers(
    current_user: dict = Depends(get_current_user)
):
    """Clean up expired trade offers (admin only)."""
    try:
        # Check if user is admin/moderator
        if current_user.get("role") not in ["ADMIN", "MODERATOR"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        cleaned_count = await p2p_marketplace.cleanup_expired_offers()
        
        return {
            "success": True,
            "data": {
                "cleaned_offers": cleaned_count
            },
            "message": f"Cleaned up {cleaned_count} expired offers"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cleanup endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")