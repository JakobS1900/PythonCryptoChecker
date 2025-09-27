"""
Portfolio management system with persistent GEM balances.
Handles user wallets, transactions, and balance management.
"""

from datetime import datetime
from typing import Optional, Dict, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, case

from database.models import Wallet, Transaction, TransactionType
from database.database import AsyncSessionLocal



class PortfolioManager:
    """Manages user portfolios and GEM balance operations."""

    def __init__(self):
        self.gem_to_usd_rate = 0.01  # 1 GEM = $0.01 USD (100 GEM = $1)

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
                    # Auto-create wallet for new user
                    print(f">> Info: Creating wallet for new user {user_id}")
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
        game_session_id: Optional[str] = None
    ) -> bool:
        """Deduct GEMs from user's wallet."""
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
                print(f">> Error: Error deducting GEMs: {e}")
                return False

    async def process_win(
        self,
        user_id: str,
        amount: float,
        description: str,
        game_session_id: Optional[str] = None
    ) -> bool:
        """Process a gambling win by adding GEMs."""
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
            # Get wallet
            wallet = await self.get_user_wallet(user_id)
            if not wallet:
                wallet = await self.create_wallet(user_id, initial_gems=1000.0)
                if not wallet:
                    # Return a valid empty portfolio structure
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

            # Type conditions
            bet_type = Transaction.transaction_type
            won = bet_type == TransactionType.BET_WON.value
            placed = bet_type == TransactionType.BET_PLACED.value
            lost = bet_type == TransactionType.BET_LOST.value

            # Build the query
            query = select(
                func.count(Transaction.id).label('total_transactions'),
                func.coalesce(
                    func.sum(
                        case({won: Transaction.amount}, else_=0)
                    ),
                    0
                ).label('total_winnings'),
                func.coalesce(
                    func.sum(
                        case({placed: -Transaction.amount}, else_=0)
                    ),
                    0
                ).label('total_bets'),
                func.coalesce(
                    func.count(
                        case({won: 1}, else_=None)
                    ),
                    0
                ).label('games_won'),
                func.coalesce(
                    func.count(
                        case({lost: 1}, else_=None)
                    ),
                    0
                ).label('games_lost')
            ).where(Transaction.user_id == user_id)

            # Execute query and get results with defaults
            result = await session.execute(query)
            row = result.first()
            row_data = {
                'total_transactions': 0,
                'total_winnings': 0,
                'total_bets': 0,
                'games_won': 0,
                'games_lost': 0
            }

            if row:
                for key in row_data:
                    row_data[key] = getattr(row, key, 0) or 0

            # Calculate metrics
            total_games = (
                row_data['games_won'] + row_data['games_lost']
            )
            win_rate = (
                100.0 * row_data['games_won'] / total_games
                if total_games > 0 else 0.0
            )
            net_gambling = (
                row_data['total_winnings'] - row_data['total_bets']
            )
            
            # Get wallet value in USD
            wallet_dict = wallet.to_dict()
            gems = float(wallet_dict.get('gem_balance', 0))
            gem_value_usd = gems * self.gem_to_usd_rate

            return {
                "wallet": wallet.to_dict(),
                "stats": {
                    "total_transactions": row_data['total_transactions'],
                    "total_winnings": row_data['total_winnings'],
                    "total_bets": row_data['total_bets'],
                    "games_won": row_data['games_won'],
                    "games_lost": row_data['games_lost'],
                    "total_games": total_games,
                    "win_rate": round(win_rate, 2),
                    "net_gambling": round(net_gambling, 2),
                    "gem_value_usd": round(gem_value_usd, 2)
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
            if amount < 10:
                return False, "Minimum bet amount is 10 GEM"

            # Check maximum bet
            if amount > 10000:
                return False, "Maximum bet amount is 10,000 GEM"

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
