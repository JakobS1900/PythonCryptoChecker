"""
Core trading engine for paper trading and portfolio management.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    User, Portfolio, Holding, Transaction, Order,
    OrderType, OrderSide, OrderStatus, TransactionType, RiskPolicy,
    OcoGroup, OcoLink
)
from .database import db_manager, AsyncSessionLocal
from data_providers import DataManager
from logger import logger, handle_exceptions


class TradingEngine:
    """Core trading engine for executing paper trades."""
    
    def __init__(self):
        self.data_manager = DataManager()
    
    @handle_exceptions(logger)
    async def create_user(
        self, 
        username: str, 
        email: str, 
        hashed_password: str,
        user_id: Optional[str] = None
    ) -> User:
        """Create a new user account."""
        async with AsyncSessionLocal() as session:
            user = User(
                username=username,
                email=email,
                hashed_password=hashed_password
            )
            
            # Override ID if provided
            if user_id:
                user.id = user_id
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            logger.info(f"Created new user: {username}")
            return user
    
    @handle_exceptions(logger)
    async def create_portfolio(
        self, 
        user_id: str, 
        name: str, 
        initial_balance: float = 100000.0,
        base_currency: str = "USD",
        description: Optional[str] = None,
        portfolio_id: Optional[str] = None
    ) -> Portfolio:
        """Create a new portfolio for a user."""
        async with AsyncSessionLocal() as session:
            portfolio = Portfolio(
                user_id=user_id,
                name=name,
                description=description,
                initial_balance=initial_balance,
                current_balance=initial_balance,
                base_currency=base_currency
            )
            
            # Override ID if provided
            if portfolio_id:
                portfolio.id = portfolio_id
            
            session.add(portfolio)
            await session.commit()
            await session.refresh(portfolio)
            
            # Create initial deposit transaction
            deposit_transaction = Transaction(
                user_id=user_id,
                portfolio_id=portfolio.id,
                transaction_type=TransactionType.DEPOSIT,
                amount=initial_balance,
                description=f"Initial deposit for portfolio: {name}"
            )
            
            session.add(deposit_transaction)
            await session.commit()

            # Create default risk policy
            risk_policy = RiskPolicy(
                portfolio_id=portfolio.id,
                max_position_pct=0.30,
                max_open_positions=10,
                max_trade_value_pct=0.20,
                default_sl_pct=0.05,
                default_tp_pct=0.10,
            )
            session.add(risk_policy)
            await session.commit()
            
            logger.info(f"Created new portfolio '{name}' for user {user_id} with ${initial_balance:,.2f}")
            return portfolio
    
    @handle_exceptions(logger)
    async def place_order(
        self,
        user_id: str,
        portfolio_id: str,
        coin_id: str,
        coin_symbol: str,
        order_type: OrderType,
        order_side: OrderSide,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Place a trading order. Returns a dict with order and optional metadata."""
        async with AsyncSessionLocal() as session:
            # Get current market price if needed
            current_price = await self._get_current_price(coin_id)
            
            if not current_price:
                raise ValueError(f"Unable to get current price for {coin_id}")
            
            # Validate order
            await self._validate_order(
                session, portfolio_id, order_side, quantity, 
                price or current_price, coin_symbol
            )
            
            # Create order
            order = Order(
                user_id=user_id,
                portfolio_id=portfolio_id,
                coin_id=coin_id,
                coin_symbol=coin_symbol,
                order_type=order_type,
                order_side=order_side,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                notes=notes
            )
            
            session.add(order)
            await session.commit()
            await session.refresh(order)
            
            # Execute market orders immediately
            if order_type == OrderType.MARKET:
                oco_group_id = await self._execute_order(session, order, current_price)
                logger.info(f"Placed {order_side.value} order for {quantity} {coin_symbol} at ${price or current_price:.2f}")
                return {"order": order, "oco_group_id": oco_group_id}
            
            logger.info(f"Placed {order_side.value} order for {quantity} {coin_symbol} at ${price or current_price:.2f}")
            return {"order": order, "oco_group_id": None}
    
    async def _validate_order(
        self,
        session: AsyncSession,
        portfolio_id: str,
        order_side: OrderSide,
        quantity: float,
        price: float,
        coin_symbol: str
    ):
        """Validate if order can be placed."""
        # Get portfolio
        result = await session.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            raise ValueError("Portfolio not found")
        
        total_cost = quantity * price
        
        if order_side == OrderSide.BUY:
            # Check if enough balance for purchase
            if portfolio.current_balance < total_cost:
                raise ValueError(f"Insufficient balance. Need ${total_cost:.2f}, have ${portfolio.current_balance:.2f}")

            # Risk policy enforcement
            policy = await self._get_or_create_risk_policy(session, portfolio_id)

            # Compute current portfolio value (cash + market value of holdings)
            holdings_result = await session.execute(select(Holding).where(Holding.portfolio_id == portfolio_id))
            holdings = holdings_result.scalars().all()
            total_market_value = 0.0
            positions_count = 0
            for h in holdings:
                current = await self._get_current_price(h.coin_id) or h.current_price or 0.0
                total_market_value += current * h.quantity
                if h.quantity > 0:
                    positions_count += 1
            total_portfolio_value = portfolio.current_balance + total_market_value

            # Limit: max trade value % of portfolio
            if total_portfolio_value > 0 and total_cost > policy.max_trade_value_pct * total_portfolio_value:
                raise ValueError(
                    f"Trade exceeds max single trade value limit ({policy.max_trade_value_pct*100:.1f}% of portfolio value)."
                )

            # Limit: max open positions
            existing_holding = next((h for h in holdings if h.coin_symbol == coin_symbol and h.quantity > 0), None)
            if not existing_holding and positions_count >= policy.max_open_positions:
                raise ValueError(
                    f"Opening new position would exceed max open positions ({policy.max_open_positions})."
                )

            # Limit: max per-position exposure
            # Compute existing position value for this coin
            existing_value = 0.0
            if existing_holding:
                current = await self._get_current_price(existing_holding.coin_id) or existing_holding.current_price or 0.0
                existing_value = existing_holding.quantity * current
            new_position_value = existing_value + total_cost
            if total_portfolio_value > 0 and new_position_value > policy.max_position_pct * total_portfolio_value:
                raise ValueError(
                    f"Position size would exceed max position limit ({policy.max_position_pct*100:.1f}% of portfolio value)."
                )
        
        elif order_side == OrderSide.SELL:
            # Check if enough holdings to sell
            result = await session.execute(
                select(Holding).where(
                    Holding.portfolio_id == portfolio_id,
                    Holding.coin_symbol == coin_symbol
                )
            )
            holding = result.scalar_one_or_none()
            
            if not holding or holding.quantity < quantity:
                available = holding.quantity if holding else 0
                raise ValueError(f"Insufficient {coin_symbol} holdings. Need {quantity}, have {available}")
    
    async def _execute_order(
        self,
        session: AsyncSession,
        order: Order,
        execution_price: float
    ) -> Optional[str]:
        """Execute a trading order. Returns OCO group id if created for protections."""
        try:
            # Calculate transaction details
            total_amount = order.quantity * execution_price
            fee = total_amount * 0.001  # 0.1% trading fee
            
            # Update order status
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.filled_price = execution_price
            order.filled_at = datetime.utcnow()
            
            # Get portfolio
            result = await session.execute(select(Portfolio).where(Portfolio.id == order.portfolio_id))
            portfolio = result.scalar_one()
            
            created_group_id = None
            if order.order_side == OrderSide.BUY:
                # Update portfolio balance
                portfolio.current_balance -= (total_amount + fee)
                portfolio.total_invested += total_amount
                
                # Update or create holding
                result = await session.execute(
                    select(Holding).where(
                        Holding.portfolio_id == order.portfolio_id,
                        Holding.coin_id == order.coin_id
                    )
                )
                holding = result.scalar_one_or_none()
                
                if holding:
                    # Update existing holding (weighted average cost)
                    total_cost = (holding.quantity * holding.average_cost) + total_amount
                    total_quantity = holding.quantity + order.quantity
                    holding.average_cost = total_cost / total_quantity
                    holding.quantity = total_quantity
                    holding.current_price = execution_price
                    holding.last_price_update = datetime.utcnow()
                else:
                    # Create new holding
                    holding = Holding(
                        portfolio_id=order.portfolio_id,
                        coin_id=order.coin_id,
                        coin_symbol=order.coin_symbol,
                        quantity=order.quantity,
                        average_cost=execution_price,
                        current_price=execution_price
                    )
                    session.add(holding)
                
                # Create buy transaction
                transaction = Transaction(
                    user_id=order.user_id,
                    portfolio_id=order.portfolio_id,
                    order_id=order.id,
                    transaction_type=TransactionType.TRADE_BUY,
                    coin_id=order.coin_id,
                    coin_symbol=order.coin_symbol,
                    quantity=order.quantity,
                    price=execution_price,
                    amount=total_amount,
                    fee=fee,
                    description=f"Buy {order.quantity} {order.coin_symbol} at ${execution_price:.2f}"
                )
                
            elif order.order_side == OrderSide.SELL:
                # Update portfolio balance
                net_proceeds = total_amount - fee
                portfolio.current_balance += net_proceeds
                
                # Update holding
                result = await session.execute(
                    select(Holding).where(
                        Holding.portfolio_id == order.portfolio_id,
                        Holding.coin_id == order.coin_id
                    )
                )
                holding = result.scalar_one()
                
                # Calculate profit/loss
                cost_basis = holding.average_cost * order.quantity
                profit_loss = total_amount - cost_basis
                
                holding.quantity -= order.quantity
                holding.current_price = execution_price
                holding.last_price_update = datetime.utcnow()
                
                # Update portfolio P&L
                portfolio.total_profit_loss += profit_loss
                
                # Remove holding if quantity becomes zero
                if holding.quantity <= 0:
                    await session.delete(holding)
                
                # Create sell transaction
                transaction = Transaction(
                    user_id=order.user_id,
                    portfolio_id=order.portfolio_id,
                    order_id=order.id,
                    transaction_type=TransactionType.TRADE_SELL,
                    coin_id=order.coin_id,
                    coin_symbol=order.coin_symbol,
                    quantity=order.quantity,
                    price=execution_price,
                    amount=total_amount,
                    fee=fee,
                    description=f"Sell {order.quantity} {order.coin_symbol} at ${execution_price:.2f} (P&L: ${profit_loss:+.2f})"
                )
            
            # Update portfolio trade statistics
            portfolio.total_trades += 1
            if order.order_side == OrderSide.SELL:
                if profit_loss > 0:
                    portfolio.winning_trades += 1
                else:
                    portfolio.losing_trades += 1
            
            # Add fee transaction
            fee_transaction = Transaction(
                user_id=order.user_id,
                portfolio_id=order.portfolio_id,
                order_id=order.id,
                transaction_type=TransactionType.FEE,
                amount=fee,
                description=f"Trading fee for {order.order_side.value} {order.quantity} {order.coin_symbol}"
            )
            
            session.add(transaction)
            session.add(fee_transaction)
            await session.commit()
            
            logger.info(f"Executed {order.order_side.value} order: {order.quantity} {order.coin_symbol} at ${execution_price:.2f}")

            # After executing a BUY, optionally create protective SL/TP orders based on policy
            if order.order_side == OrderSide.BUY:
                policy = await self._get_or_create_risk_policy(session, order.portfolio_id)
                protective_orders: List[Order] = []
                if policy.default_sl_pct and policy.default_sl_pct > 0:
                    protective_orders.append(Order(
                        user_id=order.user_id,
                        portfolio_id=order.portfolio_id,
                        coin_id=order.coin_id,
                        coin_symbol=order.coin_symbol,
                        order_type=OrderType.STOP_LOSS,
                        order_side=OrderSide.SELL,
                        quantity=order.quantity,
                        price=execution_price * (1 - policy.default_sl_pct),
                        stop_price=execution_price * (1 - policy.default_sl_pct),
                        notes=f"Auto SL {policy.default_sl_pct*100:.1f}% from entry"
                    ))
                if policy.default_tp_pct and policy.default_tp_pct > 0:
                    protective_orders.append(Order(
                        user_id=order.user_id,
                        portfolio_id=order.portfolio_id,
                        coin_id=order.coin_id,
                        coin_symbol=order.coin_symbol,
                        order_type=OrderType.TAKE_PROFIT,
                        order_side=OrderSide.SELL,
                        quantity=order.quantity,
                        price=execution_price * (1 + policy.default_tp_pct),
                        stop_price=execution_price * (1 + policy.default_tp_pct),
                        notes=f"Auto TP {policy.default_tp_pct*100:.1f}% from entry"
                    ))
                if protective_orders:
                    for po in protective_orders:
                        session.add(po)
                    await session.commit()
                    if len(protective_orders) >= 2:
                        grp = await self._create_oco_group(session, [po.id for po in protective_orders])
                        created_group_id = grp.id

            # After executing a protective SL/TP sell, cancel sibling protective orders
            if order.order_side == OrderSide.SELL and order.order_type in (OrderType.STOP_LOSS, OrderType.TAKE_PROFIT):
                # Prefer OCO group cancellation
                cancelled_any = await self._cancel_oco_siblings(session, order)
                if not cancelled_any:
                    # Fallback by coin+portfolio
                    result = await session.execute(
                        select(Order).where(
                            Order.portfolio_id == order.portfolio_id,
                            Order.coin_id == order.coin_id,
                            Order.order_side == OrderSide.SELL,
                            Order.status == OrderStatus.PENDING,
                            Order.id != order.id,
                            Order.order_type.in_([OrderType.STOP_LOSS, OrderType.TAKE_PROFIT])
                        )
                    )
                    siblings = result.scalars().all()
                    for sib in siblings:
                        sib.status = OrderStatus.CANCELLED
                    if siblings:
                        await session.commit()

            # Sync the virtual wallet/holdings layer with this trade (gamification)
            await self._sync_virtual_after_trade(session, order, execution_price)
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to execute order {order.id}: {e}", exc_info=True)
            raise
        return created_group_id
    
    async def _get_current_price(self, coin_id: str) -> Optional[float]:
        """Get current price for a cryptocurrency."""
        try:
            coins_data, _ = self.data_manager.get_top_coins("usd", limit=100)
            
            for coin in coins_data:
                if coin.id == coin_id:
                    return coin.price
            
            return None
        except Exception as e:
            logger.error(f"Failed to get current price for {coin_id}: {e}")
            return None
    
    @handle_exceptions(logger)
    async def get_portfolio_summary(self, portfolio_id: str) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        async with AsyncSessionLocal() as session:
            # Get portfolio
            result = await session.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
            portfolio = result.scalar_one_or_none()
            
            if not portfolio:
                raise ValueError("Portfolio not found")
            
            # Get holdings
            result = await session.execute(
                select(Holding).where(Holding.portfolio_id == portfolio_id)
            )
            holdings = result.scalars().all()
            
            # Update holding prices and calculate totals
            total_market_value = 0.0
            holdings_data = []
            
            for holding in holdings:
                # Get current price
                current_price = await self._get_current_price(holding.coin_id)
                if current_price:
                    holding.current_price = current_price
                    holding.last_price_update = datetime.utcnow()
                
                market_value = holding.market_value
                total_market_value += market_value
                
                holdings_data.append({
                    "coin_id": holding.coin_id,
                    "coin_symbol": holding.coin_symbol,
                    "quantity": holding.quantity,
                    "average_cost": holding.average_cost,
                    "current_price": holding.current_price,
                    "market_value": market_value,
                    "cost_basis": holding.total_cost,
                    "profit_loss": holding.profit_loss,
                    "profit_loss_percentage": holding.profit_loss_percentage
                })
            
            # Calculate portfolio metrics
            total_portfolio_value = portfolio.current_balance + total_market_value
            total_return = total_portfolio_value - portfolio.initial_balance
            total_return_percentage = (total_return / portfolio.initial_balance) * 100 if portfolio.initial_balance > 0 else 0
            
            return {
                "portfolio": {
                    "id": portfolio.id,
                    "name": portfolio.name,
                    "initial_balance": portfolio.initial_balance,
                    "current_balance": portfolio.current_balance,
                    "total_invested": portfolio.total_invested,
                    "total_market_value": total_market_value,
                    "total_portfolio_value": total_portfolio_value,
                    "total_return": total_return,
                    "total_return_percentage": total_return_percentage,
                    "total_trades": portfolio.total_trades,
                    "winning_trades": portfolio.winning_trades,
                    "losing_trades": portfolio.losing_trades,
                    "win_rate": (portfolio.winning_trades / portfolio.total_trades * 100) if portfolio.total_trades > 0 else 0
                },
                "holdings": holdings_data,
                "summary": {
                    "cash_percentage": (portfolio.current_balance / total_portfolio_value * 100) if total_portfolio_value > 0 else 100,
                    "invested_percentage": (total_market_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0,
                    "number_of_positions": len(holdings_data)
                }
            }
    
    @handle_exceptions(logger)
    async def get_transaction_history(
        self, 
        portfolio_id: str, 
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get transaction history for a portfolio."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Transaction)
                .where(Transaction.portfolio_id == portfolio_id)
                .order_by(Transaction.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            transactions = result.scalars().all()
            
        return [
                {
                    "id": tx.id,
                    "type": tx.transaction_type.value,
                    "coin_id": tx.coin_id,
                    "coin_symbol": tx.coin_symbol,
                    "quantity": tx.quantity,
                    "price": tx.price,
                    "amount": tx.amount,
                    "fee": tx.fee,
                    "description": tx.description,
                    "created_at": tx.created_at.isoformat()
                }
                for tx in transactions
            ]

    @handle_exceptions(logger)
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel a pending order by ID."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Order).where(Order.id == order_id))
            order = result.scalar_one_or_none()
            if not order:
                raise ValueError("Order not found")
            if order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
                return {
                    "order_id": order.id,
                    "status": order.status.value,
                    "message": "Order already finalized"
                }
            order.status = OrderStatus.CANCELLED
            await session.commit()
            return {
                "order_id": order.id,
                "status": order.status.value,
                "message": "Order cancelled"
            }

    async def get_open_orders(self, portfolio_id: str) -> List[Dict[str, Any]]:
        """Get non-filled, non-cancelled orders for a portfolio."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Order)
                .where(
                    Order.portfolio_id == portfolio_id,
                    Order.status != OrderStatus.FILLED,
                    Order.status != OrderStatus.CANCELLED,
                )
                .order_by(Order.created_at.desc())
            )
            orders = result.scalars().all()

            # OCO metadata: map orders to their OCO group (if any) and peers
            order_ids = [o.id for o in orders]
            oco_meta: Dict[str, Dict[str, Any]] = {oid: {"group_id": None, "peers": []} for oid in order_ids}
            if order_ids:
                # Fetch links for these orders
                res_links = await session.execute(
                    select(OcoLink.order_id, OcoLink.group_id).where(OcoLink.order_id.in_(order_ids))
                )
                rows = res_links.all()
                if rows:
                    group_ids = list({r[1] for r in rows})
                    # Map order -> group
                    for (oid, gid) in rows:
                        oco_meta[oid]["group_id"] = gid
                    # Fetch all members of these groups
                    res_group_members = await session.execute(
                        select(OcoLink.group_id, OcoLink.order_id).where(OcoLink.group_id.in_(group_ids))
                    )
                    group_to_orders: Dict[str, List[str]] = {}
                    for (gid, oid) in res_group_members.all():
                        group_to_orders.setdefault(gid, []).append(oid)
                    # Fill peers for each order
                    for oid in order_ids:
                        gid = oco_meta[oid]["group_id"]
                        if gid and gid in group_to_orders:
                            oco_meta[oid]["peers"] = [x for x in group_to_orders[gid] if x != oid]

            return [
                {
                    "id": o.id,
                    "coin_id": o.coin_id,
                    "coin_symbol": o.coin_symbol,
                    "order_type": o.order_type.value,
                    "order_side": o.order_side.value,
                    "quantity": o.quantity,
                    "price": o.price,
                    "stop_price": o.stop_price,
                    "status": o.status.value,
                    "created_at": o.created_at.isoformat(),
                    "oco_group_id": oco_meta.get(o.id, {}).get("group_id"),
                    "oco_peer_order_ids": oco_meta.get(o.id, {}).get("peers", []),
                }
                for o in orders
            ]

    async def evaluate_risk_triggers(self) -> int:
        """Evaluate STOP_LOSS/TAKE_PROFIT orders and execute if triggered.

        Returns number of orders executed.
        """
        executed = 0
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Order).where(
                    Order.status == OrderStatus.PENDING,
                    Order.order_type.in_([OrderType.STOP_LOSS, OrderType.TAKE_PROFIT])
                )
            )
            pending_orders: List[Order] = result.scalars().all()
            for order in pending_orders:
                current_price = await self._get_current_price(order.coin_id)
                if current_price is None or order.stop_price is None:
                    continue
                trigger = False
                if order.order_type == OrderType.STOP_LOSS and current_price <= order.stop_price:
                    trigger = True
                if order.order_type == OrderType.TAKE_PROFIT and current_price >= order.stop_price:
                    trigger = True
                if trigger:
                    # Execute the order at current market price
                    await self._execute_order(session, order, current_price)
                    executed += 1
        return executed

    async def _sync_virtual_after_trade(self, session: AsyncSession, order: Order, execution_price: float) -> None:
        """Mirror paper trade to virtual wallet/holdings for gamification. Best-effort (no raise)."""
        try:
            from gamification.models import VirtualWallet, VirtualCryptoHolding, VirtualTransaction, CurrencyType
            from gamification.virtual_economy import VirtualEconomyEngine
        except Exception:
            return
        try:
            # Ensure wallet exists
            from sqlalchemy import select as _select
            res = await session.execute(_select(VirtualWallet).where(VirtualWallet.user_id == order.user_id))
            wallet = res.scalar_one_or_none()
            if wallet is None:
                wallet = VirtualWallet(user_id=order.user_id)
                session.add(wallet)
                await session.commit()
                await session.refresh(wallet)

            # Find holding
            res_h = await session.execute(
                _select(VirtualCryptoHolding).where(
                    VirtualCryptoHolding.wallet_id == wallet.id,
                    VirtualCryptoHolding.crypto_id == order.coin_id
                )
            )
            holding = res_h.scalar_one_or_none()
            qty = order.quantity
            notional_usd = execution_price * qty
            prev_avg = None
            prev_amount = None
            if order.order_side == OrderSide.BUY:
                if holding:
                    total_invested_usd = holding.average_buy_price * holding.virtual_amount + execution_price * qty
                    holding.virtual_amount += qty
                    holding.average_buy_price = total_invested_usd / max(holding.virtual_amount, 1e-9)
                    holding.updated_at = datetime.utcnow()
                else:
                    holding = VirtualCryptoHolding(
                        wallet_id=wallet.id,
                        crypto_id=order.coin_id,
                        crypto_symbol=order.coin_symbol,
                        virtual_amount=qty,
                        average_buy_price=execution_price
                    )
                    session.add(holding)
                tx_type = "TRADE_BUY"
                desc = f"Paper buy {qty} {order.coin_symbol} @ ${execution_price:.2f}"
            else:
                # SELL
                if holding:
                    prev_avg = holding.average_buy_price
                    prev_amount = holding.virtual_amount
                    sell_qty = min(qty, holding.virtual_amount)
                    holding.virtual_amount -= sell_qty
                    holding.updated_at = datetime.utcnow()
                    if holding.virtual_amount <= 0:
                        await session.delete(holding)
                tx_type = "TRADE_SELL"
                desc = f"Paper sell {qty} {order.coin_symbol} @ ${execution_price:.2f}"

            # Log virtual transaction (no balance tracking of GEM coins here)
            tx = VirtualTransaction(
                wallet_id=wallet.id,
                transaction_type=tx_type,
                currency_type=CurrencyType.VIRTUAL_CRYPTO.value,
                amount=qty,
                source="paper_trade",
                description=desc,
                reference_id=order.id,
                balance_before=0,
                balance_after=0
            )
            session.add(tx)
            await session.commit()

            # Award XP and GEM coins for participating in trading
            try:
                ve = VirtualEconomyEngine()
                # XP scales with notional and level
                level_factor = 1 + (wallet.level * 0.02)  # +2% per level
                xp_gain = int(5 + (max(0, __import__('math').log10(notional_usd + 1)) * 8) * level_factor)
                # Apply XP boost effect
                effects = await ve.get_active_effects(session, order.user_id, scope="TRADING")
                xp_mult = effects.get("XP_MULT").multiplier if effects.get("XP_MULT") else 1.0
                xp_gain = int(xp_gain * xp_mult)
                await ve.add_currency(session, order.user_id, CurrencyType.EXPERIENCE_POINTS, xp_gain, "paper_trade", "XP for placing a trade")

                # GEM bonus scales with notional; extra if profitable sell
                gem_bonus = min(50.0, 2.0 + notional_usd * 0.00002)  # 0.002% capped at 50
                if order.order_side == OrderSide.SELL and prev_avg is not None and prev_amount:
                    # Simple profit check on portion sold
                    sell_qty = min(qty, prev_amount)
                    pnl = (execution_price - prev_avg) * sell_qty
                    if pnl > 0:
                        gem_bonus += min(50.0, pnl * 0.0001)  # 0.01% of profit, capped
                gem_mult = effects.get("GEM_MULT").multiplier if effects.get("GEM_MULT") else 1.0
                gem_bonus = round(gem_bonus * gem_mult, 2)
                await ve.add_currency(session, order.user_id, CurrencyType.GEM_COINS, gem_bonus, "paper_trade", "GEM bonus for trading")

                # Item drop chance scales with notional and level
                drop_mult = min(3.0, 1.0 + (max(0, __import__('math').log10(notional_usd + 1)) / 4) + wallet.level * 0.01)
                drop_effect = effects.get("DROP_RATE")
                if drop_effect:
                    drop_mult *= drop_effect.multiplier
                min_rarity = None
                rare_effect = effects.get("GUARANTEED_RARE")
                if rare_effect:
                    from gamification.models import ItemRarity as _R
                    min_rarity = _R.RARE
                dropped = await ve.generate_random_item_drop(session, order.user_id, drop_chance_multiplier=drop_mult, min_rarity=min_rarity)
                if dropped and rare_effect:
                    await ve.consume_effect_use(session, rare_effect)
            except Exception:
                # Ignore reward failures
                pass
        except Exception as _:
            # Best-effort only; do not impact trading engine if virtual sync fails
            return

    async def _get_or_create_risk_policy(self, session: AsyncSession, portfolio_id: str) -> RiskPolicy:
        """Fetch or create default risk policy for portfolio."""
        result = await session.execute(select(RiskPolicy).where(RiskPolicy.portfolio_id == portfolio_id))
        policy = result.scalar_one_or_none()
        if policy:
            return policy
        policy = RiskPolicy(portfolio_id=portfolio_id)
        session.add(policy)
        await session.commit()
        await session.refresh(policy)
        return policy

    @handle_exceptions(logger)
    async def get_risk_policy(self, portfolio_id: str) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(RiskPolicy).where(RiskPolicy.portfolio_id == portfolio_id))
            policy = result.scalar_one_or_none()
            if not policy:
                policy = await self._get_or_create_risk_policy(session, portfolio_id)
            return {
                "portfolio_id": policy.portfolio_id,
                "max_position_pct": policy.max_position_pct,
                "max_open_positions": policy.max_open_positions,
                "max_trade_value_pct": policy.max_trade_value_pct,
                "default_sl_pct": policy.default_sl_pct,
                "default_tp_pct": policy.default_tp_pct,
                "created_at": policy.created_at.isoformat() if policy.created_at else None,
                "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
            }

    @handle_exceptions(logger)
    async def update_risk_policy(self, portfolio_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            policy = await self._get_or_create_risk_policy(session, portfolio_id)
            # Update allowed fields
            for field in [
                "max_position_pct",
                "max_open_positions",
                "max_trade_value_pct",
                "default_sl_pct",
                "default_tp_pct",
            ]:
                if field in updates and updates[field] is not None:
                    setattr(policy, field, updates[field])
            await session.commit()
            await session.refresh(policy)
            return await self.get_risk_policy(portfolio_id)

    async def _create_oco_group(self, session: AsyncSession, order_ids: List[str]) -> OcoGroup:
        group = OcoGroup()
        session.add(group)
        await session.commit()
        await session.refresh(group)
        for oid in order_ids:
            link = OcoLink(group_id=group.id, order_id=oid)
            session.add(link)
        await session.commit()
        return group

    @handle_exceptions(logger)
    async def create_oco_group(self, order_ids: List[str]) -> str:
        """Public helper to create an OCO group linking provided order IDs.
        Returns the group ID.
        """
        async with AsyncSessionLocal() as session:
            group = await self._create_oco_group(session, order_ids)
            return group.id

    @handle_exceptions(logger)
    async def cancel_oco_group(self, group_id: str) -> Dict[str, Any]:
        """Cancel all pending orders linked to an OCO group and close the group."""
        async with AsyncSessionLocal() as session:
            # Find order IDs in the group
            res = await session.execute(select(OcoLink.order_id).where(OcoLink.group_id == group_id))
            order_ids = [row[0] for row in res.all()]
            if not order_ids:
                raise ValueError("OCO group not found or empty")
            # Cancel pending orders
            res_orders = await session.execute(select(Order).where(Order.id.in_(order_ids), Order.status == OrderStatus.PENDING))
            orders = res_orders.scalars().all()
            for o in orders:
                o.status = OrderStatus.CANCELLED
            cancelled = len(orders)
            # Close group
            res_group = await session.execute(select(OcoGroup).where(OcoGroup.id == group_id))
            group = res_group.scalar_one_or_none()
            if group:
                group.closed_at = datetime.utcnow()
            await session.commit()
            return {"group_id": group_id, "cancelled": cancelled, "order_ids": order_ids}

    async def _cancel_oco_siblings(self, session: AsyncSession, executed_order: Order) -> bool:
        """Cancel other orders in same OCO group as executed_order.
        Returns True if any were cancelled.
        """
        # Find group(s) containing this order
        result = await session.execute(select(OcoLink.group_id).where(OcoLink.order_id == executed_order.id))
        group_ids = [row[0] for row in result.all()]
        if not group_ids:
            return False
        # Find sibling order ids
        result = await session.execute(
            select(OcoLink.order_id).where(
                OcoLink.group_id.in_(group_ids),
                OcoLink.order_id != executed_order.id
            )
        )
        sibling_ids = [row[0] for row in result.all()]
        if not sibling_ids:
            return False
        # Cancel siblings that are still pending
        result = await session.execute(select(Order).where(Order.id.in_(sibling_ids), Order.status == OrderStatus.PENDING))
        siblings = result.scalars().all()
        for sib in siblings:
            sib.status = OrderStatus.CANCELLED
        if siblings:
            await session.commit()
            # Optionally mark group closed
            result = await session.execute(select(OcoGroup).where(OcoGroup.id.in_(group_ids)))
            for grp in result.scalars().all():
                grp.closed_at = datetime.utcnow()
            await session.commit()
            return True
        return False


# Global trading engine instance
trading_engine = TradingEngine()
