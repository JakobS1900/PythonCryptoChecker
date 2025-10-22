"""
GEM P2P Trading API

REST API endpoints for the P2P trading system.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database.models import User
from api.auth_api import require_authentication
from services.trading_service import TradingService


router = APIRouter()


# Request/Response Models

class CreateOrderRequest(BaseModel):
    order_type: str = Field(..., description="Order type: buy or sell")
    price: int = Field(..., gt=0, description="Price per GEM")
    amount: int = Field(..., gt=0, description="Amount of GEM")


class OrderInfo(BaseModel):
    id: int
    user_id: str
    order_type: str
    price: int
    amount: int
    filled_amount: int
    status: str
    created_at: datetime
    updated_at: datetime
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CreateOrderResponse(BaseModel):
    success: bool
    message: str
    order: Optional[OrderInfo] = None


class OrderBookEntry(BaseModel):
    price: int
    amount: int
    filled_amount: int
    remaining: int
    created_at: datetime


class OrderBookResponse(BaseModel):
    buy_orders: List[OrderBookEntry]
    sell_orders: List[OrderBookEntry]
    spread: Optional[int] = None


class TradeInfo(BaseModel):
    id: int
    buyer_id: str
    seller_id: str
    order_id: int
    price: int
    amount: int
    total_value: int
    fee: int
    created_at: datetime

    class Config:
        from_attributes = True


class CancelOrderResponse(BaseModel):
    success: bool
    message: str


class MarketStatsResponse(BaseModel):
    total_orders: int
    active_buy_orders: int
    active_sell_orders: int
    total_trades_24h: int
    volume_24h: int
    best_bid: Optional[int] = None
    best_ask: Optional[int] = None


# API Endpoints

@router.post("/order", response_model=CreateOrderResponse)
async def create_order(
    request: CreateOrderRequest,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    success, message, order = await TradingService.create_order(
        user_id=current_user.id,
        order_type=request.order_type,
        price=request.price,
        amount=request.amount,
        db=db
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return CreateOrderResponse(
        success=success,
        message=message,
        order=OrderInfo.from_orm(order) if order else None
    )


@router.get("/order-book", response_model=OrderBookResponse)
async def get_order_book(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    order_book = await TradingService.get_order_book(db, limit=limit)

    buy_orders = [
        OrderBookEntry(
            price=order.price,
            amount=order.amount,
            filled_amount=order.filled_amount,
            remaining=order.amount - order.filled_amount,
            created_at=order.created_at
        )
        for order in order_book["buy_orders"]
    ]

    sell_orders = [
        OrderBookEntry(
            price=order.price,
            amount=order.amount,
            filled_amount=order.filled_amount,
            remaining=order.amount - order.filled_amount,
            created_at=order.created_at
        )
        for order in order_book["sell_orders"]
    ]

    spread = None
    if buy_orders and sell_orders:
        best_bid = buy_orders[0].price
        best_ask = sell_orders[0].price
        spread = best_ask - best_bid

    return OrderBookResponse(
        buy_orders=buy_orders,
        sell_orders=sell_orders,
        spread=spread
    )


@router.get("/my-orders", response_model=List[OrderInfo])
async def get_my_orders(
    status: Optional[str] = None,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    orders = await TradingService.get_user_orders(
        user_id=current_user.id,
        db=db,
        status=status
    )

    return [OrderInfo.from_orm(order) for order in orders]


@router.post("/cancel-order/{order_id}", response_model=CancelOrderResponse)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    success, message = await TradingService.cancel_order(
        order_id=order_id,
        user_id=current_user.id,
        db=db
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return CancelOrderResponse(success=success, message=message)


@router.get("/trades/recent", response_model=List[TradeInfo])
async def get_recent_trades(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    trades = await TradingService.get_recent_trades(db, limit=limit)
    return [TradeInfo.from_orm(trade) for trade in trades]


@router.get("/trades/my-history", response_model=List[TradeInfo])
async def get_my_trade_history(
    limit: int = 50,
    current_user: User = Depends(require_authentication),
    db: AsyncSession = Depends(get_db)
):
    trades = await TradingService.get_user_trade_history(
        user_id=current_user.id,
        db=db,
        limit=limit
    )

    return [TradeInfo.from_orm(trade) for trade in trades]


@router.get("/stats", response_model=MarketStatsResponse)
async def get_market_stats(
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select, func, and_
    from database.models import GemTradeOrder, GemTrade
    from datetime import datetime, timedelta

    order_book = await TradingService.get_order_book(db, limit=1)

    best_bid = None
    if order_book["buy_orders"]:
        best_bid = order_book["buy_orders"][0].price

    best_ask = None
    if order_book["sell_orders"]:
        best_ask = order_book["sell_orders"][0].price

    result = await db.execute(
        select(func.count(GemTradeOrder.id))
        .where(GemTradeOrder.status.in_(["active", "partial"]))
    )
    total_orders = result.scalar() or 0

    result = await db.execute(
        select(func.count(GemTradeOrder.id))
        .where(
            and_(
                GemTradeOrder.order_type == "buy",
                GemTradeOrder.status.in_(["active", "partial"])
            )
        )
    )
    active_buy_orders = result.scalar() or 0

    result = await db.execute(
        select(func.count(GemTradeOrder.id))
        .where(
            and_(
                GemTradeOrder.order_type == "sell",
                GemTradeOrder.status.in_(["active", "partial"])
            )
        )
    )
    active_sell_orders = result.scalar() or 0

    yesterday = datetime.utcnow() - timedelta(hours=24)

    result = await db.execute(
        select(func.count(GemTrade.id))
        .where(GemTrade.created_at >= yesterday)
    )
    total_trades_24h = result.scalar() or 0

    result = await db.execute(
        select(func.sum(GemTrade.total_value))
        .where(GemTrade.created_at >= yesterday)
    )
    volume_24h = result.scalar() or 0

    return MarketStatsResponse(
        total_orders=total_orders,
        active_buy_orders=active_buy_orders,
        active_sell_orders=active_sell_orders,
        total_trades_24h=total_trades_24h,
        volume_24h=volume_24h,
        best_bid=best_bid,
        best_ask=best_ask
    )
