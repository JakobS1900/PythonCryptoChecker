"""
Trading API endpoints for the Crypto Analytics Platform.
Provides REST API for paper trading, portfolio management, and risk management.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.engine import trading_engine
try:
    from gamification.models import VirtualWallet, VirtualCryptoHolding, CollectibleItem
    from gamification.item_generator import initialize_collectible_items
except Exception:
    VirtualWallet = None
    VirtualCryptoHolding = None
    CollectibleItem = None
    initialize_collectible_items = None
from trading.database import AsyncSessionLocal
from trading.models import OrderType, OrderSide
from trading.database import init_database
from logger import logger
from sqlalchemy import select as _select

# Create router
router = APIRouter(prefix="/api/trading", tags=["Trading"])

# GEM conversion: USD per GEM (default: 0.01 => 1000 GEM = 10 USD)
GEM_USD_RATE = float(os.getenv("GEM_USD_RATE_USD_PER_GEM", "0.01"))

# Pydantic models for API requests/responses
class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=100)
    password: str = Field(min_length=6, max_length=100)


class CreatePortfolioRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    initial_balance: float = Field(default=100000.0, gt=0, le=1000000)
    base_currency: str = Field(default="USD", min_length=3, max_length=3)
    description: Optional[str] = Field(default=None, max_length=500)


class PlaceOrderRequest(BaseModel):
    coin_id: str = Field(min_length=1, max_length=50)
    coin_symbol: str = Field(min_length=1, max_length=10)
    order_type: str = Field(pattern="^(MARKET|LIMIT|STOP_LOSS|TAKE_PROFIT)$")
    order_side: str = Field(pattern="^(BUY|SELL)$")
    quantity: float = Field(gt=0)
    price: Optional[float] = Field(default=None, gt=0)
    stop_price: Optional[float] = Field(default=None, gt=0)
    notes: Optional[str] = Field(default=None, max_length=500)


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: str
    is_active: bool


class PortfolioResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    initial_balance: float
    current_balance: float
    base_currency: str
    created_at: str
    is_active: bool


class OrderResponse(BaseModel):
    id: str
    coin_id: str
    coin_symbol: str
    order_type: str
    order_side: str
    quantity: float
    price: Optional[float]
    stop_price: Optional[float]
    status: str
    filled_quantity: float
    filled_price: Optional[float]
    filled_at: Optional[str]
    created_at: str
    notes: Optional[str]


class RiskPolicyResponse(BaseModel):
    portfolio_id: str
    max_position_pct: float
    max_open_positions: int
    max_trade_value_pct: float
    default_sl_pct: float
    default_tp_pct: float
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UpdateRiskPolicyRequest(BaseModel):
    max_position_pct: Optional[float] = Field(default=None, ge=0, le=1)
    max_open_positions: Optional[int] = Field(default=None, ge=1, le=100)
    max_trade_value_pct: Optional[float] = Field(default=None, ge=0, le=1)
    default_sl_pct: Optional[float] = Field(default=None, ge=0, le=1)
    default_tp_pct: Optional[float] = Field(default=None, ge=0, le=1)


class CreateProtectionRequest(BaseModel):
    coin_id: str = Field(min_length=1, max_length=50)
    coin_symbol: str = Field(min_length=1, max_length=10)
    quantity: Optional[float] = Field(default=None, gt=0)
    sl_pct: Optional[float] = Field(default=None, ge=0, le=1)
    sl_price: Optional[float] = Field(default=None, gt=0)
    tp_pct: Optional[float] = Field(default=None, ge=0, le=1)
    tp_price: Optional[float] = Field(default=None, gt=0)


class CancelProtectionRequest(BaseModel):
    coin_id: Optional[str] = None


class ReplaceProtectionRequest(CreateProtectionRequest):
    oco_group_id: Optional[str] = None
    cancel_existing: bool = True


# Temporary user session management (in production, use JWT or proper auth)
# For demo purposes, we'll create a default user
DEFAULT_USER_ID = "demo-user-123"
DEFAULT_PORTFOLIO_ID = "demo-portfolio-456"

async def get_default_user():
    """Get or create default demo user."""
    return DEFAULT_USER_ID

async def get_default_portfolio():
    """Get or create default demo portfolio."""
    return DEFAULT_PORTFOLIO_ID


# API Endpoints
@router.on_event("startup")
async def startup_trading_api():
    """Initialize trading database on startup."""
    try:
        await init_database()
        logger.info("Trading API initialized successfully")
        
        # Create demo user and portfolio if they don't exist
        try:
            await trading_engine.create_user(
                username="demo_trader",
                email="demo@cryptoplatform.com", 
                hashed_password="demo_hash",  # In production, use proper password hashing
                user_id=DEFAULT_USER_ID
            )
            
            await trading_engine.create_portfolio(
                user_id=DEFAULT_USER_ID,
                name="Demo Trading Portfolio",
                initial_balance=100000.0,
                description="Default demo portfolio for testing paper trading",
                portfolio_id=DEFAULT_PORTFOLIO_ID
            )
            # Ensure virtual wallet exists for gamification layer
            if VirtualWallet is not None:
                async with AsyncSessionLocal() as session:
                    res = await session.execute(
                        __import__('sqlalchemy').select(VirtualWallet).where(VirtualWallet.user_id == DEFAULT_USER_ID)
                    )
                    wallet = res.scalar_one_or_none()
                    if not wallet:
                        session.add(VirtualWallet(user_id=DEFAULT_USER_ID))
                        await session.commit()

            # Initialize collectible catalog if empty
            if CollectibleItem is not None and initialize_collectible_items is not None:
                async with AsyncSessionLocal() as session:
                    res = await session.execute(__import__('sqlalchemy').select(CollectibleItem))
                    if not res.scalars().first():
                        await initialize_collectible_items(session)
            
        except Exception:
            # User/portfolio might already exist, that's okay
            pass
            
    except Exception as e:
        logger.error(f"Failed to initialize trading API: {e}", exc_info=True)


@router.get("/health")
async def trading_health_check():
    """Health check for trading system."""
    return {
        "status": "healthy",
        "component": "trading_engine",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/gamification/wallet", tags=["Gamification"])
async def get_virtual_wallet(user_id: str = DEFAULT_USER_ID):
    """Get user's virtual wallet and crypto holdings (gamification)."""
    if VirtualWallet is None:
        raise HTTPException(status_code=501, detail="Gamification module not available")
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select as _select
            res = await session.execute(_select(VirtualWallet).where(VirtualWallet.user_id == user_id))
            wallet = res.scalar_one_or_none()
            if not wallet:
                return {"status": "success", "data": {"wallet": None, "holdings": []}}
            res_h = await session.execute(_select(VirtualCryptoHolding).where(VirtualCryptoHolding.wallet_id == wallet.id))
            holdings = [
                {
                    "crypto_id": h.crypto_id,
                    "crypto_symbol": h.crypto_symbol,
                    "virtual_amount": h.virtual_amount,
                    "average_buy_price": h.average_buy_price,
                    "updated_at": h.updated_at.isoformat() if h.updated_at else None
                }
                for h in res_h.scalars().all()
            ]
            return {
                "status": "success",
                "data": {
                    "wallet": {
                        "id": wallet.id,
                        "gem_coins": wallet.gem_coins,
                        "experience_points": wallet.experience_points,
                        "premium_tokens": wallet.premium_tokens,
                        "level": wallet.level,
                        "total_xp_earned": wallet.total_xp_earned
                    },
                    "holdings": holdings
                }
            }
    except Exception as e:
        logger.error(f"Error getting virtual wallet: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/gamification/inventory", tags=["Gamification"])
async def get_inventory(
    user_id: str = DEFAULT_USER_ID,
    page: int = 1,
    per_page: int = 50,
    item_type: Optional[str] = None,
    rarity: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "acquired_at",
    sort_desc: bool = True
):
    """List user's virtual inventory with basic stats."""
    try:
        from inventory.inventory_manager import InventoryManager
    except Exception:
        raise HTTPException(status_code=501, detail="Inventory module not available")
    try:
        async with AsyncSessionLocal() as session:
            inv = InventoryManager()
            # Map strings to enums if provided
            from gamification.models import ItemType, ItemRarity
            itype = ItemType[item_type] if item_type else None
            irarity = ItemRarity[rarity] if rarity else None
            data = await inv.get_user_inventory(
                session, user_id,
                item_type=itype,
                rarity=irarity,
                search_query=search,
                sort_by=sort_by,
                sort_desc=sort_desc,
                page=page,
                per_page=per_page
            )
            # Normalize items list from join results
            items: List[Dict[str, Any]] = []
            for row in data.get("items", []):
                items.append(row)
            response = {
                "items": items or data.get("items", []),
                "total": data.get("total", len(items)),
                "page": data.get("page", page),
                "per_page": data.get("per_page", per_page),
                "stats": await inv.get_inventory_stats(session, user_id)
            }
            return {"status": "success", "data": response}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting inventory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/gamification/consumables", tags=["Gamification"])
async def list_consumables(user_id: str = DEFAULT_USER_ID):
    """List consumable items in user's inventory."""
    try:
        if CollectibleItem is None:
            raise HTTPException(status_code=501, detail="Gamification module not available")
        async with AsyncSessionLocal() as session:
            from gamification.models import ItemType, UserInventory, CollectibleItem as CItem
            res = await session.execute(
                _select(UserInventory, CItem)
                .join(CItem, UserInventory.item_id == CItem.id)
                .where(UserInventory.user_id == user_id, CItem.item_type == ItemType.CONSUMABLE.value)
                .order_by(UserInventory.acquired_at.desc())
            )
            items = []
            for inv, item in res.all():
                items.append({
                    "inventory_id": inv.id,
                    "item_id": item.id,
                    "name": item.name,
                    "rarity": item.rarity,
                    "description": item.description,
                    "quantity": inv.quantity,
                    "is_consumable": item.is_consumable,
                })
            return {"status": "success", "data": {"items": items, "count": len(items)}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing consumables: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/gamification/consumables/{inventory_id}/use", tags=["Gamification"])
async def use_consumable(inventory_id: str, user_id: str = DEFAULT_USER_ID):
    """Use one unit of a consumable item and apply its effect."""
    try:
        from inventory.inventory_manager import InventoryManager
        inv = InventoryManager()
        async with AsyncSessionLocal() as session:
            result = await inv.use_consumable(session, user_id, inventory_id)
            # Re-query current quantity to avoid any off-by-one in manager return
            from gamification.models import UserInventory
            res = await session.execute(_select(UserInventory).where(UserInventory.id == inventory_id))
            inv_row = res.scalar_one_or_none()
            remaining = inv_row.quantity if inv_row else 0
            result["remaining_quantity"] = remaining
            return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error using consumable: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/gamification/activity", tags=["Gamification"])
async def get_gamification_activity(user_id: str = DEFAULT_USER_ID, limit: int = 10):
    """Recent virtual transactions and latest item drops for the user."""
    if VirtualWallet is None:
        raise HTTPException(status_code=501, detail="Gamification module not available")
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select as _select
            from gamification.models import VirtualTransaction, UserInventory, CollectibleItem
            # Recent transactions
            res_tx = await session.execute(
                _select(VirtualTransaction)
                .where(VirtualTransaction.wallet_id.in_(
                    _select(VirtualWallet.id).where(VirtualWallet.user_id == user_id)
                ))
                .order_by(VirtualTransaction.created_at.desc())
                .limit(limit)
            )
            txs = [
                {
                    "type": tx.transaction_type,
                    "currency": tx.currency_type,
                    "amount": tx.amount,
                    "source": tx.source,
                    "description": tx.description,
                    "created_at": tx.created_at.isoformat() if tx.created_at else None
                }
                for tx in res_tx.scalars().all()
            ]

            # Latest item acquisitions
            res_inv = await session.execute(
                _select(UserInventory, CollectibleItem)
                .join(CollectibleItem, UserInventory.item_id == CollectibleItem.id)
                .where(UserInventory.user_id == user_id)
                .order_by(UserInventory.acquired_at.desc())
                .limit(5)
            )
            drops = []
            for inv, item in res_inv.all():
                drops.append({
                    "name": item.name,
                    "rarity": item.rarity,
                    "acquired_at": inv.acquired_at.isoformat() if inv.acquired_at else None
                })
            return {"status": "success", "data": {"transactions": txs, "recent_drops": drops}}
    except Exception as e:
        logger.error(f"Error getting gamification activity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/gamification/effects", tags=["Gamification"])
async def get_active_effects(user_id: str = DEFAULT_USER_ID, scope: str = "TRADING"):
    """List active consumable effects for the user."""
    try:
        from gamification.virtual_economy import VirtualEconomyEngine
        from gamification.models import ActiveEffect
        ve = VirtualEconomyEngine()
        async with AsyncSessionLocal() as session:
            effects_map = await ve.get_active_effects(session, user_id, scope=scope)
            def serialize(effect: ActiveEffect):
                if not effect:
                    return None
                return {
                    "id": effect.id,
                    "type": effect.effect_type,
                    "multiplier": effect.multiplier,
                    "remaining_uses": effect.remaining_uses,
                    "expires_at": effect.expires_at.isoformat() if effect.expires_at else None,
                }
            data = {k: serialize(v) for k, v in effects_map.items()}
            # Remove None entries
            data = {k: v for k, v in data.items() if v is not None}
            return {"status": "success", "data": {"effects": data}}
    except Exception as e:
        logger.error(f"Error getting active effects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/portfolio/{portfolio_id}/summary")
async def get_portfolio_summary(portfolio_id: str = DEFAULT_PORTFOLIO_ID):
    """Get comprehensive portfolio summary with holdings and performance."""
    try:
        summary = await trading_engine.get_portfolio_summary(portfolio_id)
        return {
            "status": "success",
            "data": summary
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting portfolio summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/portfolio/{portfolio_id}/transactions")
async def get_transaction_history(
    portfolio_id: str = DEFAULT_PORTFOLIO_ID,
    limit: int = 50,
    offset: int = 0
):
    """Get transaction history for a portfolio."""
    try:
        transactions = await trading_engine.get_transaction_history(
            portfolio_id, limit=limit, offset=offset
        )
        return {
            "status": "success",
            "data": {
                "transactions": transactions,
                "limit": limit,
                "offset": offset,
                "count": len(transactions)
            }
        }
    except Exception as e:
        logger.error(f"Error getting transaction history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/portfolio/{portfolio_id}/orders")
async def place_order(
    order_request: PlaceOrderRequest,
    portfolio_id: str = DEFAULT_PORTFOLIO_ID,
    user_id: str = Depends(get_default_user)
):
    """Place a trading order."""
    try:
        result = await trading_engine.place_order(
            user_id=user_id,
            portfolio_id=portfolio_id,
            coin_id=order_request.coin_id,
            coin_symbol=order_request.coin_symbol.upper(),
            order_type=OrderType[order_request.order_type],
            order_side=OrderSide[order_request.order_side],
            quantity=order_request.quantity,
            price=order_request.price,
            stop_price=order_request.stop_price,
            notes=order_request.notes
        )
        order = result.get("order")
        oco_group_id = result.get("oco_group_id")
        
        return {
            "status": "success",
            "data": {
                "order_id": order.id,
                "message": f"Order placed successfully: {order_request.order_side} {order_request.quantity} {order_request.coin_symbol}",
                "order": OrderResponse(
                    id=order.id,
                    coin_id=order.coin_id,
                    coin_symbol=order.coin_symbol,
                    order_type=order.order_type.value,
                    order_side=order.order_side.value,
                    quantity=order.quantity,
                    price=order.price,
                    stop_price=order.stop_price,
                    status=order.status.value,
                    filled_quantity=order.filled_quantity,
                    filled_price=order.filled_price,
                    filled_at=order.filled_at.isoformat() if order.filled_at else None,
                    created_at=order.created_at.isoformat(),
                    notes=order.notes
                ),
                "oco_group_id": oco_group_id
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error placing order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/portfolio")
async def create_portfolio(
    portfolio_request: CreatePortfolioRequest,
    user_id: str = Depends(get_default_user)
):
    """Create a new trading portfolio."""
    try:
        portfolio = await trading_engine.create_portfolio(
            user_id=user_id,
            name=portfolio_request.name,
            initial_balance=portfolio_request.initial_balance,
            base_currency=portfolio_request.base_currency,
            description=portfolio_request.description
        )
        
        return {
            "status": "success",
            "data": {
                "portfolio_id": portfolio.id,
                "message": f"Portfolio '{portfolio_request.name}' created successfully",
                "portfolio": PortfolioResponse(
                    id=portfolio.id,
                    name=portfolio.name,
                    description=portfolio.description,
                    initial_balance=portfolio.initial_balance,
                    current_balance=portfolio.current_balance,
                    base_currency=portfolio.base_currency,
                    created_at=portfolio.created_at.isoformat(),
                    is_active=portfolio.is_active
                )
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating portfolio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/quick-trade/{action}/{coin_id}")
async def quick_trade(
    action: str,
    coin_id: str,
    amount: float,
    portfolio_id: str = DEFAULT_PORTFOLIO_ID,
    user_id: str = Depends(get_default_user)
):
    """Quick buy/sell endpoint for easy trading."""
    try:
        if action.lower() not in ["buy", "sell"]:
            raise HTTPException(status_code=400, detail="Action must be 'buy' or 'sell'")
        
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
        
        # Get coin symbol from our data (with local fallback mapping)
        from data_providers import DataManager
        data_manager = DataManager()
        coins_data, _ = data_manager.get_top_coins("usd", limit=100)

        coin_symbol = None
        for coin in coins_data:
            if coin.id == coin_id:
                coin_symbol = coin.symbol.upper()
                break
        if not coin_symbol:
            # Fallback mapping for common IDs when external data is unavailable
            fallback_map = {
                "bitcoin": "BTC",
                "ethereum": "ETH",
                "ripple": "XRP",
                "binancecoin": "BNB",
                "solana": "SOL",
                "cardano": "ADA",
                "dogecoin": "DOGE",
                "polygon": "MATIC"
            }
            coin_symbol = fallback_map.get(coin_id)
        if not coin_symbol:
            raise HTTPException(status_code=404, detail=f"Cryptocurrency '{coin_id}' not found")
        
        # Determine current price and convert USD 'amount' to coin quantity
        current_price = await trading_engine._get_current_price(coin_id)
        if not current_price:
            raise HTTPException(status_code=400, detail=f"Unable to get current price for {coin_id}")

        coin_quantity = amount / current_price

        # For BUY, ensure sufficient GEM balance (1 GEM = GEM_USD_RATE USD)
        if action.lower() == "buy" and VirtualWallet is not None:
            try:
                async with AsyncSessionLocal() as session:
                    res = await session.execute(__import__('sqlalchemy').select(VirtualWallet).where(VirtualWallet.user_id == user_id))
                    wallet = res.scalar_one_or_none()
                    if wallet is None:
                        wallet = VirtualWallet(user_id=user_id)
                        session.add(wallet)
                        await session.commit()
                        await session.refresh(wallet)
                    required_gems = float(amount) / GEM_USD_RATE
                    if wallet.gem_coins < required_gems:
                        raise HTTPException(status_code=400, detail=f"Insufficient GEM balance. Require {required_gems:.0f} GEM for ${amount:.2f}")
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"GEM wallet precheck skipped: {e}")

        # Place market order with computed quantity
        result = await trading_engine.place_order(
            user_id=user_id,
            portfolio_id=portfolio_id,
            coin_id=coin_id,
            coin_symbol=coin_symbol,
            order_type=OrderType.MARKET,
            order_side=OrderSide.BUY if action.lower() == "buy" else OrderSide.SELL,
            quantity=coin_quantity,
            notes=f"Quick {action} via API (${amount:.2f})"
        )
        order = result.get("order")
        
        # GEM wallet integration: adjust gem balance on quick trades (1 GEM == 1 USD assumption)
        if VirtualWallet is not None:
            try:
                async with AsyncSessionLocal() as session:
                    from sqlalchemy import select as _select
                    res = await session.execute(_select(VirtualWallet).where(VirtualWallet.user_id == user_id))
                    wallet = res.scalar_one_or_none()
                    if wallet:
                        # Convert USD amount to GEM using USD per GEM rate
                        gems_delta = float(amount) / GEM_USD_RATE
                        delta = gems_delta if action.lower() == "sell" else -gems_delta
                        wallet.gem_coins = max(0.0, float(wallet.gem_coins) + delta)
                        await session.commit()
            except Exception as e:
                logger.warning(f"GEM wallet adjustment skipped: {e}")

        return {
            "status": "success",
            "data": {
                "message": f"Quick {action} executed: {amount} {coin_symbol}",
                "order_id": order.id,
                "executed": order.status.value == "FILLED"
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in quick trade: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/portfolio/{portfolio_id}/performance")
async def get_portfolio_performance(portfolio_id: str = DEFAULT_PORTFOLIO_ID):
    """Get detailed portfolio performance analytics."""
    try:
        summary = await trading_engine.get_portfolio_summary(portfolio_id)
        transactions = await trading_engine.get_transaction_history(portfolio_id, limit=1000)
        
        # Calculate additional performance metrics
        portfolio_data = summary["portfolio"]
        
        # Calculate daily P&L (simplified - in production, use proper time series)
        daily_pnl = []
        monthly_returns = []
        
        # Risk metrics (simplified calculations)
        total_return_pct = portfolio_data["total_return_percentage"]
        volatility = abs(total_return_pct) * 0.1  # Simplified volatility estimate
        sharpe_ratio = total_return_pct / volatility if volatility > 0 else 0
        
        performance_data = {
            "summary": portfolio_data,
            "risk_metrics": {
                "total_return_percentage": total_return_pct,
                "volatility": volatility,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max(0, -total_return_pct),  # Simplified
                "var_95": total_return_pct * 0.05  # Simplified VaR
            },
            "trading_stats": {
                "total_trades": portfolio_data["total_trades"],
                "winning_trades": portfolio_data["winning_trades"],
                "losing_trades": portfolio_data["losing_trades"],
                "win_rate": portfolio_data["win_rate"],
                "average_trade": portfolio_data["total_return"] / max(1, portfolio_data["total_trades"])
            },
            "recent_transactions": transactions[:10]  # Last 10 transactions
        }
        
        return {
            "status": "success",
            "data": performance_data
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio performance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/risk-policy/{portfolio_id}")
async def get_risk_policy(portfolio_id: str = DEFAULT_PORTFOLIO_ID):
    """Get risk management policy for a portfolio."""
    try:
        policy = await trading_engine.get_risk_policy(portfolio_id)
        return {"status": "success", "data": RiskPolicyResponse(**policy)}
    except Exception as e:
        logger.error(f"Error getting risk policy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/risk-policy/{portfolio_id}")
async def update_risk_policy(
    portfolio_id: str,
    updates: UpdateRiskPolicyRequest
):
    """Update risk management policy for a portfolio."""
    try:
        updated = await trading_engine.update_risk_policy(portfolio_id, updates.model_dump(exclude_none=True))
        return {"status": "success", "data": RiskPolicyResponse(**updated)}
    except Exception as e:
        logger.error(f"Error updating risk policy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/portfolio/{portfolio_id}/orders/open")
async def get_open_orders(portfolio_id: str = DEFAULT_PORTFOLIO_ID):
    """List open (pending) orders for a portfolio."""
    try:
        orders = await trading_engine.get_open_orders(portfolio_id)
        return {"status": "success", "data": {"orders": orders, "count": len(orders)}}
    except Exception as e:
        logger.error(f"Error getting open orders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/oco/{group_id}/cancel")
async def cancel_oco_group(group_id: str):
    """Cancel all open orders in an OCO group."""
    try:
        result = await trading_engine.cancel_oco_group(group_id)
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling OCO group: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: str):
    """Cancel a pending order by ID."""
    try:
        result = await trading_engine.cancel_order(order_id)
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/portfolio/{portfolio_id}/orders/protect")
async def create_protective_orders(
    portfolio_id: str,
    request: CreateProtectionRequest,
    user_id: str = Depends(get_default_user)
):
    """Create protective SL/TP orders for an existing position.

    At least one of sl_pct/sl_price or tp_pct/tp_price must be provided.
    If quantity is omitted, uses the current holding quantity.
    Prices from pct are based on current market price.
    """
    try:
        if not any([request.sl_pct, request.sl_price, request.tp_pct, request.tp_price]):
            raise HTTPException(status_code=400, detail="Provide at least one of SL or TP as pct or price")

        # Determine quantity if not provided
        quantity = request.quantity
        if quantity is None:
            # Use portfolio summary to get holding quantity
            summary = await trading_engine.get_portfolio_summary(portfolio_id)
            holding = next((h for h in summary.get("holdings", []) if h["coin_id"] == request.coin_id), None)
            if not holding or holding["quantity"] <= 0:
                raise HTTPException(status_code=400, detail="No existing holding for the specified coin")
            quantity = holding["quantity"]

        # Get current market price
        current_price = await trading_engine._get_current_price(request.coin_id)  # type: ignore
        if not current_price:
            raise HTTPException(status_code=503, detail="Unable to fetch current market price")

        created: Dict[str, Any] = {"orders": []}
        created_ids: List[str] = []

        # Create SL
        if request.sl_price or request.sl_pct:
            sl_price = request.sl_price or (current_price * (1 - float(request.sl_pct)))
            order = await trading_engine.place_order(
                user_id=user_id,
                portfolio_id=portfolio_id,
                coin_id=request.coin_id,
                coin_symbol=request.coin_symbol.upper(),
                order_type=OrderType.STOP_LOSS,
                order_side=OrderSide.SELL,
                quantity=quantity,
                price=sl_price,
                stop_price=sl_price,
                notes="Custom protective SL"
            )
            created["orders"].append({"type": "STOP_LOSS", "order_id": order.id, "price": sl_price})
            created_ids.append(order.id)

        # Create TP
        if request.tp_price or request.tp_pct:
            tp_price = request.tp_price or (current_price * (1 + float(request.tp_pct)))
            order = await trading_engine.place_order(
                user_id=user_id,
                portfolio_id=portfolio_id,
                coin_id=request.coin_id,
                coin_symbol=request.coin_symbol.upper(),
                order_type=OrderType.TAKE_PROFIT,
                order_side=OrderSide.SELL,
                quantity=quantity,
                price=tp_price,
                stop_price=tp_price,
                notes="Custom protective TP"
            )
            created["orders"].append({"type": "TAKE_PROFIT", "order_id": order.id, "price": tp_price})
            created_ids.append(order.id)

        # If both were created, link them as OCO
        if len(created_ids) >= 2:
            group_id = await trading_engine.create_oco_group(created_ids)
            created["oco_group_id"] = group_id

        return {"status": "success", "data": created}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating protective orders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/portfolio/{portfolio_id}/orders/protect/cancel")
async def cancel_protective_orders(
    portfolio_id: str,
    request: CancelProtectionRequest
):
    """Cancel all open protective SL/TP orders for a portfolio (optionally for a single coin)."""
    try:
        # Get open orders and filter
        orders = await trading_engine.get_open_orders(portfolio_id)
        cancelled = []
        for o in orders:
            if o["order_type"] in ("STOP_LOSS", "TAKE_PROFIT") and (not request.coin_id or o["coin_id"] == request.coin_id):
                result = await trading_engine.cancel_order(o["id"])
                cancelled.append(result)
        return {"status": "success", "data": {"cancelled": cancelled, "count": len(cancelled)}}
    except Exception as e:
        logger.error(f"Error cancelling protective orders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/portfolio/{portfolio_id}/orders/protect/replace")
async def replace_protective_orders(
    portfolio_id: str,
    request: ReplaceProtectionRequest,
    user_id: str = Depends(get_default_user)
):
    """Replace protective SL/TP orders. Cancels existing (by group or coin) and creates new ones."""
    try:
        # Cancel existing
        if request.cancel_existing:
            if request.oco_group_id:
                await trading_engine.cancel_oco_group(request.oco_group_id)
            else:
                await cancel_protective_orders(portfolio_id, CancelProtectionRequest(coin_id=request.coin_id))

        # Create new protections using same logic as create_protective_orders
        base = CreateProtectionRequest(
            coin_id=request.coin_id,
            coin_symbol=request.coin_symbol,
            quantity=request.quantity,
            sl_pct=request.sl_pct,
            sl_price=request.sl_price,
            tp_pct=request.tp_pct,
            tp_price=request.tp_price
        )
        return await create_protective_orders(portfolio_id, base, user_id)  # type: ignore
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replacing protective orders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
class InventoryListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int
    stats: Dict[str, Any]
