"""
GEM Staking Service

Handles all staking operations including stake creation, reward calculation,
unstaking, and reward claims.
"""
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, Dict, List
import uuid

from database.models import GemStake, User, Wallet, Transaction, TransactionType
from config.staking_plans import (
    get_plan,
    validate_plan_id,
    validate_stake_amount,
    calculate_unlock_date,
    calculate_daily_reward,
    STAKING_LIMITS,
)
import logging

logger = logging.getLogger(__name__)


class StakingService:
    """Service for managing GEM staking operations."""

    @staticmethod
    async def create_stake(
        user_id: str,
        plan_id: str,
        amount: int,
        db: AsyncSession
    ) -> tuple[bool, str, Optional[GemStake]]:
        """
        Create a new stake for a user.

        Args:
            user_id: User ID
            plan_id: Staking plan ID
            amount: GEM amount to stake
            db: Database session

        Returns:
            (success, message, stake_object)
        """
        try:
            # Validate plan
            if not validate_plan_id(plan_id):
                return False, "Invalid staking plan", None

            plan = get_plan(plan_id)

            # Validate amount
            is_valid, error_msg = validate_stake_amount(plan_id, amount)
            if not is_valid:
                return False, error_msg, None

            # Check user's active stakes count
            active_stakes_result = await db.execute(
                select(func.count(GemStake.id)).where(
                    GemStake.user_id == user_id,
                    GemStake.status == 'active'
                )
            )
            active_stakes_count = active_stakes_result.scalar()

            if active_stakes_count >= STAKING_LIMITS["max_active_stakes_per_user"]:
                return False, f"Maximum {STAKING_LIMITS['max_active_stakes_per_user']} active stakes allowed", None

            # Get user's wallet
            wallet_result = await db.execute(
                select(Wallet).where(Wallet.user_id == user_id)
            )
            wallet = wallet_result.scalar_one_or_none()

            if not wallet:
                return False, "Wallet not found", None

            if wallet.gem_balance < amount:
                return False, f"Insufficient GEM balance. Need {amount:,} GEM, have {wallet.gem_balance:,} GEM", None

            # Calculate unlock date
            unlock_at = calculate_unlock_date(plan["lock_period_days"])

            # Deduct GEM from wallet
            balance_before = wallet.gem_balance
            wallet.gem_balance -= amount

            # Create stake record
            stake = GemStake(
                user_id=user_id,
                amount=amount,
                lock_period_days=plan["lock_period_days"],
                apr_rate=plan["apr_rate"],
                total_rewards_earned=0,
                unclaimed_rewards=0,
                last_reward_calculation=datetime.utcnow(),
                status='active',
                staked_at=datetime.utcnow(),
                unlock_at=unlock_at,
            )
            db.add(stake)

            # Create transaction record
            transaction = Transaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                transaction_type=TransactionType.STAKE.value,
                amount=amount,
                balance_before=balance_before,
                balance_after=wallet.gem_balance,
                description=f"Staked {amount:,} GEM in {plan['name']} plan (ID: {stake.id})",
                reference_id=str(stake.id),
            )
            db.add(transaction)

            await db.commit()
            await db.refresh(stake)

            logger.info(f"User {user_id} staked {amount:,} GEM in {plan_id} plan")
            return True, f"Successfully staked {amount:,} GEM", stake

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating stake for user {user_id}: {e}")
            return False, f"Error creating stake: {str(e)}", None

    @staticmethod
    async def calculate_pending_rewards(stake: GemStake) -> int:
        """
        Calculate pending rewards for a stake since last calculation.

        Args:
            stake: GemStake object

        Returns:
            Pending rewards in GEM
        """
        if stake.status != 'active':
            return 0

        now = datetime.utcnow()
        time_since_last_calc = now - stake.last_reward_calculation
        days_since_last_calc = time_since_last_calc.total_seconds() / 86400  # Convert to days

        if days_since_last_calc < 1:
            return 0  # Only calculate after at least 1 day

        daily_reward = calculate_daily_reward(stake.amount, stake.apr_rate)
        pending_rewards = int(daily_reward * int(days_since_last_calc))

        return pending_rewards

    @staticmethod
    async def update_stake_rewards(
        stake: GemStake,
        db: AsyncSession
    ) -> int:
        """
        Update stake with calculated rewards.

        Args:
            stake: GemStake object
            db: Database session

        Returns:
            Rewards added
        """
        pending_rewards = await StakingService.calculate_pending_rewards(stake)

        if pending_rewards > 0:
            stake.unclaimed_rewards += pending_rewards
            stake.last_reward_calculation = datetime.utcnow()
            await db.commit()

        return pending_rewards

    @staticmethod
    async def claim_rewards(
        stake_id: int,
        user_id: str,
        db: AsyncSession
    ) -> tuple[bool, str, int]:
        """
        Claim accumulated rewards for a stake.

        Args:
            stake_id: Stake ID
            user_id: User ID (for verification)
            db: Database session

        Returns:
            (success, message, rewards_claimed)
        """
        try:
            # Get stake
            stake_result = await db.execute(
                select(GemStake).where(
                    GemStake.id == stake_id,
                    GemStake.user_id == user_id
                )
            )
            stake = stake_result.scalar_one_or_none()

            if not stake:
                return False, "Stake not found", 0

            if stake.status != 'active':
                return False, "Stake is not active", 0

            # Update rewards first
            await StakingService.update_stake_rewards(stake, db)

            if stake.unclaimed_rewards == 0:
                return False, "No rewards to claim", 0

            # Get wallet
            wallet_result = await db.execute(
                select(Wallet).where(Wallet.user_id == user_id)
            )
            wallet = wallet_result.scalar_one_or_none()

            if not wallet:
                return False, "Wallet not found", 0

            # Add rewards to wallet
            rewards_amount = stake.unclaimed_rewards
            balance_before = wallet.gem_balance
            wallet.gem_balance += rewards_amount

            # Update stake
            stake.total_rewards_earned += rewards_amount
            stake.unclaimed_rewards = 0

            # Create transaction record
            transaction = Transaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                transaction_type=TransactionType.STAKE_REWARD.value,
                amount=rewards_amount,
                balance_before=balance_before,
                balance_after=wallet.gem_balance,
                description=f"Staking rewards claimed from Stake ID {stake_id}",
                reference_id=str(stake_id),
            )
            db.add(transaction)

            await db.commit()

            logger.info(f"User {user_id} claimed {rewards_amount:,} GEM rewards from stake {stake_id}")
            return True, f"Claimed {rewards_amount:,} GEM rewards", rewards_amount

        except Exception as e:
            await db.rollback()
            logger.error(f"Error claiming rewards for stake {stake_id}: {e}")
            return False, f"Error claiming rewards: {str(e)}", 0

    @staticmethod
    async def unstake(
        stake_id: int,
        user_id: str,
        db: AsyncSession
    ) -> tuple[bool, str, int]:
        """
        Unstake GEM and return principal + any unclaimed rewards.

        Args:
            stake_id: Stake ID
            user_id: User ID (for verification)
            db: Database session

        Returns:
            (success, message, total_returned_amount)
        """
        try:
            # Get stake
            stake_result = await db.execute(
                select(GemStake).where(
                    GemStake.id == stake_id,
                    GemStake.user_id == user_id
                )
            )
            stake = stake_result.scalar_one_or_none()

            if not stake:
                return False, "Stake not found", 0

            if stake.status != 'active':
                return False, "Stake is already completed or cancelled", 0

            # Check if unlocked (only for locked plans)
            now = datetime.utcnow()
            if stake.lock_period_days > 0 and now < stake.unlock_at:
                time_remaining = stake.unlock_at - now
                days_remaining = time_remaining.days
                return False, f"Stake is still locked for {days_remaining} days", 0

            # Update rewards one last time
            await StakingService.update_stake_rewards(stake, db)

            # Get wallet
            wallet_result = await db.execute(
                select(Wallet).where(Wallet.user_id == user_id)
            )
            wallet = wallet_result.scalar_one_or_none()

            if not wallet:
                return False, "Wallet not found", 0

            # Calculate total return (principal + unclaimed rewards)
            principal = stake.amount
            unclaimed_rewards = stake.unclaimed_rewards
            total_return = principal + unclaimed_rewards

            # Return GEM to wallet
            balance_before = wallet.gem_balance
            wallet.gem_balance += total_return

            # Update stake status
            stake.status = 'completed'
            stake.unstaked_at = now
            stake.total_rewards_earned += unclaimed_rewards
            stake.unclaimed_rewards = 0

            # Create transaction for principal return
            transaction_unstake = Transaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                transaction_type=TransactionType.UNSTAKE.value,
                amount=principal,
                balance_before=balance_before,
                balance_after=balance_before + principal,
                description=f"Unstaked {principal:,} GEM from Stake ID {stake_id}",
                reference_id=str(stake_id),
            )
            db.add(transaction_unstake)

            # Create transaction for final rewards if any
            if unclaimed_rewards > 0:
                transaction_reward = Transaction(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    transaction_type=TransactionType.STAKE_REWARD.value,
                    amount=unclaimed_rewards,
                    balance_before=balance_before + principal,
                    balance_after=wallet.gem_balance,
                    description=f"Final staking rewards from Stake ID {stake_id}",
                    reference_id=str(stake_id),
                )
                db.add(transaction_reward)

            await db.commit()

            logger.info(f"User {user_id} unstaked {principal:,} GEM + {unclaimed_rewards:,} rewards from stake {stake_id}")
            return True, f"Unstaked {principal:,} GEM + {unclaimed_rewards:,} GEM rewards", total_return

        except Exception as e:
            await db.rollback()
            logger.error(f"Error unstaking stake {stake_id}: {e}")
            return False, f"Error unstaking: {str(e)}", 0

    @staticmethod
    async def get_user_stakes(
        user_id: str,
        db: AsyncSession,
        status: Optional[str] = None
    ) -> List[GemStake]:
        """
        Get all stakes for a user.

        Args:
            user_id: User ID
            db: Database session
            status: Filter by status ('active', 'completed', 'cancelled')

        Returns:
            List of GemStake objects
        """
        query = select(GemStake).where(GemStake.user_id == user_id)

        if status:
            query = query.where(GemStake.status == status)

        query = query.order_by(GemStake.created_at.desc())

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_user_staking_stats(
        user_id: str,
        db: AsyncSession
    ) -> Dict:
        """
        Get staking statistics for a user.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Dictionary with staking statistics
        """
        # Get all active stakes
        active_stakes = await StakingService.get_user_stakes(user_id, db, status='active')

        # Calculate totals
        total_staked = sum(stake.amount for stake in active_stakes)
        total_unclaimed_rewards = sum(stake.unclaimed_rewards for stake in active_stakes)

        # Get all stakes for total rewards earned
        all_stakes = await StakingService.get_user_stakes(user_id, db)
        total_rewards_earned = sum(stake.total_rewards_earned for stake in all_stakes)

        return {
            "active_stakes_count": len(active_stakes),
            "total_staked_amount": total_staked,
            "total_unclaimed_rewards": total_unclaimed_rewards,
            "total_rewards_earned_all_time": total_rewards_earned,
            "completed_stakes_count": len([s for s in all_stakes if s.status == 'completed']),
        }
