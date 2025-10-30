"""
Portfolio management system with persistent GEM balances.
Handles user wallets, transactions, and balance management.
"""

from datetime import datetime
from typing import Optional, Dict, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, case

from database.models import Wallet, Transaction, TransactionType, User
from database.database import AsyncSessionLocal
from sqlalchemy import select, and_



class PortfolioManager:
    """Manages user portfolios and GEM balance operations."""

    def __init__(self):
        self.gem_to_usd_rate = 0.01  # 1 GEM = $0.01 USD (100 GEM = $1)

    async def _is_user_bot(self, user_id: str) -> bool:
        """Check if user is a bot."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User.is_bot).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            return bool(user)

    async def get_user_wallet(self, user_id: str) -> Optional[Wallet]:
        """Get user's wallet."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Wallet).where(Wallet.user_id == user_id)
            )
            return result.scalar_one_or_none()

    async def get_user_balance(self, user_id: str) -> float:
        """Get user's current GEM balance."""
        async with AsyncSessionLocal() as session:
            stmt = select(Wallet.gem_balance).where(Wallet.user_id == user_id)
            result = await session.execute(stmt)
            balance = result.scalar_one_or_none()
            return float(balance) if balance is not None else 0.0

    async def create_wallet(
        self, user_id: str, initial_gems: float = 1000.0
    ) -> Wallet:
        """Create a new wallet for user with initial GEM balance."""
        async with AsyncSessionLocal() as session:
            try:
                wallet = Wallet(
                    user_id=user_id,
                    gem_balance=initial_gems,
                    total_deposited=initial_gems
                )
                session.add(wallet)

                # Create initial deposit transaction
                await self._create_transaction(
                    session=session,
                    user_id=user_id,
                    transaction_type=TransactionType.DEPOSIT,
                    amount=initial_gems,
                    balance_before=0.0,
                    balance_after=initial_gems,
                    description="Initial GEM deposit"
                )

                await session.commit()
                await session.refresh(wallet)
                return wallet

            except Exception as e:
                await session.rollback()
                raise e

    async def add_gems(
        self,
        user_id: str,
        amount: float,
        description: str = "GEM deposit"
    ) -> bool:
        """Add GEMs to user's wallet."""
        async with AsyncSessionLocal() as session:
            try:
                # Get current wallet
                # Check for existing wallet
                balance_stmt = select(Wallet.gem_balance).where(
                    Wallet.user_id == user_id
                )
                result = await session.execute(balance_stmt)
                current_balance = result.scalar_one_or_none()

                # Initialize variables
                old_balance = 0.0
                new_balance = 0.0

                if current_balance is None:
                    # Check if this is a bot - bots should have wallets created by bot system
                    is_bot = await self._is_user_bot(user_id)

                    if is_bot:
                        # CRITICAL: Bots should have wallets created by initialize_bots()
                        print(f">> CRITICAL: Bot {user_id} has no wallet! Bot system failed to initialize properly.")
                        print(f">> WARNING: Creating emergency wallet for bot {user_id} with 2000 GEM")

                        # Create wallet with bot-appropriate balance
                        wallet = Wallet(
                            user_id=user_id,
                            gem_balance=2000.0,  # Bot starting balance
                            total_deposited=2000.0,
                            updated_at=datetime.utcnow()
                        )
                        session.add(wallet)

                        # Create initial deposit transaction for bot
                        await self._create_transaction(
                            session=session,
                            user_id=user_id,
                            transaction_type=TransactionType.DEPOSIT,
                            amount=2000.0,
                            balance_before=0.0,
                            balance_after=2000.0,
                            description="Bot initial GEM deposit"
                        )

                        await session.flush()
                        old_balance = 2000.0
                        new_balance = old_balance + amount
                    else:
                        # Auto-create wallet for new human user
                        print(f">> Info: Creating wallet for new human user {user_id}")
                        wallet = Wallet(
                            user_id=user_id,
                            gem_balance=1000.0,
                            total_deposited=1000.0,
                            updated_at=datetime.utcnow()
                        )
                        session.add(wallet)

                        # Create initial deposit transaction
                        await self._create_transaction(
                            session=session,
                            user_id=user_id,
                            transaction_type=TransactionType.DEPOSIT,
                            amount=1000.0,
                            balance_before=0.0,
                            balance_after=1000.0,
                            description="Initial GEM deposit"
                        )

                        await session.flush()
                        old_balance = 1000.0
                        new_balance = old_balance + amount
                else:
                    old_balance = float(current_balance)
                    new_balance = old_balance + amount

                # Update wallet
                stmt = (
                    update(Wallet)
                    .where(Wallet.user_id == user_id)
                    .values(
                        gem_balance=new_balance,
                        total_deposited=Wallet.total_deposited + amount,
                        updated_at=datetime.utcnow()
                    )
                )
                await session.execute(stmt)

                # Create transaction record with scalar values
                await self._create_transaction(
                    session=session,
                    user_id=user_id,
                    transaction_type=TransactionType.DEPOSIT,
                    amount=float(amount),
                    balance_before=old_balance,
                    balance_after=new_balance,
                    description=description
                )

                await session.commit()
                return True

            except Exception as e:
                await session.rollback()
                print(f">> Error: Error adding GEMs: {e}")
                return False

    async def deduct_gems(
        self,
        user_id: str,
        amount: float,
        transaction_type: TransactionType,
        description: str,
        game_session_id: Optional[str] = None,
        max_retries: int = 3
    ) -> bool:
        """Deduct GEMs from user's wallet with retry logic for database locks."""
        for attempt in range(max_retries):
            async with AsyncSessionLocal() as session:
                try:
                    # Get and verify wallet balance
                    stmt = select(Wallet).where(Wallet.user_id == user_id)
                    result = await session.execute(stmt)
                    wallet = result.scalar_one_or_none()

                    if not wallet:
                        raise ValueError(f"Wallet not found for user {user_id}")

                    old_balance = float(wallet.gem_balance)
                    if old_balance < amount:
                        return False  # Insufficient balance

                    new_balance = old_balance - amount

                    # Prepare update values
                    update_values = {
                        'gem_balance': new_balance,
                        'updated_at': datetime.utcnow()
                    }

                    if transaction_type == TransactionType.WITHDRAWAL:
                        update_values['total_withdrawn'] = (
                            Wallet.total_withdrawn + amount
                        )
                    elif transaction_type in [
                        TransactionType.BET_PLACED,
                        TransactionType.BET_LOST
                    ]:
                        update_values['total_wagered'] = (
                            Wallet.total_wagered + amount
                        )

                    # Update wallet
                    stmt = (
                        update(Wallet)
                        .where(Wallet.user_id == user_id)
                        .values(**update_values)
                    )
                    await session.execute(stmt)

                    # Create transaction record
                    await self._create_transaction(
                        session=session,
                        user_id=user_id,
                        transaction_type=transaction_type,
                        amount=-float(amount),  # Negative for deduction
                        balance_before=old_balance,
                        balance_after=new_balance,
                        description=description,
                        game_session_id=game_session_id
                    )

                    await session.commit()
                    return True

                except Exception as e:
                    await session.rollback()

                    # Check if it's a database lock error and we haven't exhausted retries
                    error_str = str(e).lower()
                    is_lock_error = 'database is locked' in error_str or 'operationalerror' in error_str

                    if is_lock_error and attempt < max_retries - 1:
                        print(f">> Retry {attempt + 1}/{max_retries}: Database locked, retrying deduct GEMs...")
                        import asyncio
                        await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        print(f">> Error: Error deducting GEMs: {e}")
                        return False

    async def process_win(
        self,
        user_id: str,
        amount: float,
        description: str,
        game_session_id: Optional[str] = None,
        max_retries: int = 3
    ) -> bool:
        """Process a gambling win by adding GEMs with retry logic."""
        for attempt in range(max_retries):
            async with AsyncSessionLocal() as session:
                try:
                    # Get current wallet
                    # Get current balance
                    stmt = (
                        select(Wallet.gem_balance)
                        .where(Wallet.user_id == user_id)
                    )
                    result = await session.execute(stmt)
                    current_balance = result.scalar_one_or_none()

                    if current_balance is None:
                        raise ValueError(f"Wallet not found for user {user_id}")

                    old_balance = float(current_balance)
                    new_balance = old_balance + amount

                    # Update wallet
                    stmt = (
                        update(Wallet)
                        .where(Wallet.user_id == user_id)
                        .values(
                            gem_balance=new_balance,
                            total_won=Wallet.total_won + amount,
                            updated_at=datetime.utcnow()
                        )
                    )
                    await session.execute(stmt)

                    # Create transaction record
                    await self._create_transaction(
                        session=session,
                        user_id=user_id,
                        transaction_type=TransactionType.BET_WON,
                        amount=float(amount),
                        balance_before=old_balance,
                        balance_after=new_balance,
                        description=description,
                        game_session_id=game_session_id
                    )

                    await session.commit()
                    return True

                except Exception as e:
                    await session.rollback()

                    # Check if it's a database lock error and we haven't exhausted retries
                    error_str = str(e).lower()
                    is_lock_error = 'database is locked' in error_str or 'operationalerror' in error_str

                    if is_lock_error and attempt < max_retries - 1:
                        print(f">> Retry {attempt + 1}/{max_retries}: Database locked, retrying process win...")
                        import asyncio
                        await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        print(f">> Error: Error processing win: {e}")
                        return False

    async def transfer_gems(
        self,
        from_user_id: str,
        to_user_id: str,
        amount: float,
        description: str = "GEM transfer"
    ) -> bool:
        """Transfer GEMs between users."""
        async with AsyncSessionLocal() as session:
            try:
                # Get both wallets
                # Get sender's balance
                stmt = (
                    select(Wallet.gem_balance)
                    .where(Wallet.user_id == from_user_id)
                )
                result = await session.execute(stmt)
                from_balance = result.scalar_one_or_none()
                
                # Get receiver's balance
                stmt = (
                    select(Wallet.gem_balance)
                    .where(Wallet.user_id == to_user_id)
                )
                result = await session.execute(stmt)
                to_balance = result.scalar_one_or_none()

                if from_balance is None or to_balance is None:
                    return False

                # Check balance
                from_balance = float(from_balance)
                if from_balance < amount:
                    return False  # Insufficient balance

                # Store old balances for transaction records
                from_old_balance = from_balance
                to_old_balance = float(to_balance)

                # Update balances
                time_now = datetime.utcnow()
                
                # Update sender's wallet
                from_new_balance = from_old_balance - amount
                stmt = (
                    update(Wallet)
                    .where(Wallet.user_id == from_user_id)
                    .values(
                        gem_balance=from_new_balance,
                        updated_at=time_now
                    )
                )
                await session.execute(stmt)

                # Update receiver's wallet
                to_new_balance = to_old_balance + amount
                stmt = (
                    update(Wallet)
                    .where(Wallet.user_id == to_user_id)
                    .values(
                        gem_balance=to_new_balance,
                        updated_at=time_now
                    )
                )
                await session.execute(stmt)

                # Create transaction records for both users
                await self._create_transaction(
                    session=session,
                    user_id=from_user_id,
                    transaction_type=TransactionType.TRANSFER,
                    amount=-float(amount),
                    balance_before=from_old_balance,
                    balance_after=from_new_balance,
                    description=f"Transfer to user {to_user_id}: {description}"
                )

                await self._create_transaction(
                    session=session,
                    user_id=to_user_id,
                    transaction_type=TransactionType.TRANSFER,
                    amount=float(amount),
                    balance_before=to_old_balance,
                    balance_after=to_new_balance,
                    description=(
                        f"Transfer from user {from_user_id}: {description}"
                    )
                )

                await session.commit()
                return True

            except Exception as e:
                await session.rollback()
                print(f">> Error: Error transferring GEMs: {e}")
                return False

    async def get_transaction_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Get user's transaction history."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Transaction)
                .where(Transaction.user_id == user_id)
                .order_by(Transaction.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            transactions = result.scalars().all()
            return [transaction.to_dict() for transaction in transactions]

    async def get_portfolio_stats(self, user_id: str) -> Dict:
        """Get comprehensive portfolio statistics."""
        async with AsyncSessionLocal() as session:
            try:
                # Get wallet first
                wallet = await self.get_user_wallet(user_id)
                if not wallet:
                    print(f">> Creating wallet for user {user_id}")
                    wallet = await self.create_wallet(user_id, initial_gems=1000.0)
                    if not wallet:
                        print(f">> Failed to create wallet for user {user_id}")
                        return self._get_empty_portfolio_stats()

                # Get basic transaction counts
                total_transactions = await session.execute(
                    select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
                )
                total_transactions = total_transactions.scalar() or 0

                # Get winnings (positive BET_WON amounts)
                winnings_result = await session.execute(
                    select(func.coalesce(func.sum(Transaction.amount), 0))
                    .where(
                        and_(
                            Transaction.user_id == user_id,
                            Transaction.transaction_type == TransactionType.BET_WON.value
                        )
                    )
                )
                total_winnings = float(winnings_result.scalar() or 0)

                # Get bets placed (negative BET_PLACED amounts, so we use absolute value)
                bets_result = await session.execute(
                    select(func.coalesce(func.sum(func.abs(Transaction.amount)), 0))
                    .where(
                        and_(
                            Transaction.user_id == user_id,
                            Transaction.transaction_type == TransactionType.BET_PLACED.value
                        )
                    )
                )
                total_bets = float(bets_result.scalar() or 0)

                # Count games won and lost
                games_won_result = await session.execute(
                    select(func.count(Transaction.id))
                    .where(
                        and_(
                            Transaction.user_id == user_id,
                            Transaction.transaction_type == TransactionType.BET_WON.value
                        )
                    )
                )
                games_won = games_won_result.scalar() or 0

                games_lost_result = await session.execute(
                    select(func.count(Transaction.id))
                    .where(
                        and_(
                            Transaction.user_id == user_id,
                            Transaction.transaction_type == TransactionType.BET_LOST.value
                        )
                    )
                )
                games_lost = games_lost_result.scalar() or 0

                # Calculate metrics
                total_games = games_won + games_lost
                win_rate = (100.0 * games_won / total_games) if total_games > 0 else 0.0
                net_gambling = total_winnings - total_bets

                # Get wallet value in USD
                wallet_dict = wallet.to_dict()
                gems = float(wallet_dict.get('gem_balance', 0))
                gem_value_usd = gems * self.gem_to_usd_rate

                return {
                    "wallet": wallet.to_dict(),
                    "stats": {
                        "total_transactions": total_transactions,
                        "total_winnings": total_winnings,
                        "total_bets": total_bets,
                        "games_won": games_won,
                        "games_lost": games_lost,
                        "total_games": total_games,
                        "win_rate": round(win_rate, 2),
                        "net_gambling": round(net_gambling, 2),
                        "gem_value_usd": round(gem_value_usd, 2)
                    }
                }

            except Exception as e:
                print(f">> Error in get_portfolio_stats: {e}")
                import traceback
                traceback.print_exc()
                return self._get_empty_portfolio_stats()

    def _get_empty_portfolio_stats(self) -> Dict:
        """Return empty portfolio stats structure."""
        return {
            "wallet": {
                "gem_balance": 0,
                "total_deposited": 0,
                "total_withdrawn": 0,
                "total_wagered": 0,
                "total_won": 0
            },
            "stats": {
                "total_transactions": 0,
                "total_winnings": 0,
                "total_bets": 0,
                "games_won": 0,
                "games_lost": 0,
                "total_games": 0,
                "win_rate": 0,
                "net_gambling": 0,
                "gem_value_usd": 0
            }
        }

    async def validate_bet_amount(
        self,
        user_id: str,
        amount: float
    ) -> Tuple[bool, str]:
        """Validate if user can place a bet of given amount."""
        try:
            # Check minimum bet
            if amount < 1000:
                return False, "Minimum bet amount is 1,000 GEM"

            # Check maximum bet
            if amount > 5000000:
                return False, "Maximum bet amount is 5,000,000 GEM"

            # Check user balance
            balance = await self.get_user_balance(user_id)
            if balance < amount:
                msg = (
                    f"Insufficient balance. "
                    f"Current: {balance:.2f} GEM, "
                    f"Required: {amount:.2f} GEM"
                )
                return False, msg

            return True, "Valid bet amount"

        except Exception as e:
            return False, f"Error validating bet: {e}"

    async def _create_transaction(
        self,
        session: AsyncSession,
        user_id: str,
        transaction_type: TransactionType,
        amount: float,
        balance_before: float,
        balance_after: float,
        description: str,
        game_session_id: Optional[str] = None
    ) -> None:
        """Create a transaction record."""
        transaction = Transaction(
            user_id=user_id,
            transaction_type=transaction_type.value,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            game_session_id=game_session_id
        )
        session.add(transaction)

    def gem_to_usd(self, gem_amount: float) -> float:
        """Convert GEM amount to USD equivalent."""
        return gem_amount * self.gem_to_usd_rate

    def usd_to_gem(self, usd_amount: float) -> float:
        """Convert USD amount to GEM equivalent."""
        return usd_amount / self.gem_to_usd_rate


# Global portfolio manager instance
portfolio_manager = PortfolioManager()
