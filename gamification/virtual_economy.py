"""
Virtual economy management system for crypto gamification platform.
Handles currency distribution, rewards, and balance management.
"""

import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from .models import (
    VirtualWallet, VirtualCryptoHolding, CollectibleItem, UserInventory,
    VirtualTransaction, RewardBundle, VirtualEconomyConstants, ActiveEffect,
    CurrencyType, ItemRarity, ItemType, RewardType
)
from database import DailyReward
from data_providers import DataManager
from logger import logger


class VirtualEconomyEngine:
    """Core engine for managing virtual economy and rewards."""
    
    def __init__(self):
        self.data_manager = DataManager()
        self.constants = VirtualEconomyConstants()
    
    async def create_user_wallet(self, session: AsyncSession, user_id: str) -> VirtualWallet:
        """Create initial wallet for new user with starting bonuses."""
        wallet = VirtualWallet(
            user_id=user_id,
            gem_coins=self.constants.STARTING_GEM_COINS,
            experience_points=self.constants.STARTING_XP,
            level=self.constants.STARTING_LEVEL,
            total_gems_earned=self.constants.STARTING_GEM_COINS
        )
        
        session.add(wallet)
        await session.commit()
        await session.refresh(wallet)
        
        # Log starting bonus transaction
        await self._create_transaction(
            session, wallet.id, 
            CurrencyType.GEM_COINS, 
            self.constants.STARTING_GEM_COINS,
            "welcome_bonus", 
            "Welcome to the platform! Starting bonus",
            0, self.constants.STARTING_GEM_COINS
        )
        
        logger.info(f"Created virtual wallet for user {user_id} with {self.constants.STARTING_GEM_COINS} GEM coins")
        return wallet
    
    async def get_user_wallet(self, session: AsyncSession, user_id: str) -> Optional[VirtualWallet]:
        """Get user's virtual wallet."""
        result = await session.execute(
            select(VirtualWallet).where(VirtualWallet.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def add_currency(
        self, 
        session: AsyncSession, 
        user_id: str, 
        currency_type: CurrencyType, 
        amount: float,
        source: str,
        description: str = ""
    ) -> bool:
        """Add virtual currency to user's wallet."""
        wallet = await self.get_user_wallet(session, user_id)
        if not wallet:
            logger.error(f"Wallet not found for user {user_id}")
            return False
        
        # Update wallet balance
        old_balance = 0
        new_balance = 0
        
        if currency_type == CurrencyType.GEM_COINS:
            old_balance = wallet.gem_coins
            wallet.gem_coins += amount
            wallet.total_gems_earned += amount
            new_balance = wallet.gem_coins
        elif currency_type == CurrencyType.EXPERIENCE_POINTS:
            old_balance = wallet.experience_points
            wallet.experience_points += amount
            wallet.total_xp_earned += amount
            new_balance = wallet.experience_points
            
            # Check for level up
            await self._check_level_up(session, wallet)
        elif currency_type == CurrencyType.PREMIUM_TOKENS:
            old_balance = wallet.premium_tokens
            wallet.premium_tokens += amount
            new_balance = wallet.premium_tokens
        
        wallet.updated_at = datetime.utcnow()
        await session.commit()
        
        # Log transaction
        await self._create_transaction(
            session, wallet.id, currency_type, amount,
            source, description, old_balance, new_balance
        )
        
        logger.info(f"Added {amount} {currency_type.value} to user {user_id} (source: {source})")
        return True
    
    async def spend_currency(
        self,
        session: AsyncSession,
        user_id: str,
        currency_type: CurrencyType,
        amount: float,
        purpose: str,
        description: str = ""
    ) -> bool:
        """Spend virtual currency from user's wallet."""
        wallet = await self.get_user_wallet(session, user_id)
        if not wallet:
            logger.error(f"Wallet not found for user {user_id}")
            return False
        
        # Check sufficient balance
        current_balance = 0
        if currency_type == CurrencyType.GEM_COINS:
            current_balance = wallet.gem_coins
        elif currency_type == CurrencyType.EXPERIENCE_POINTS:
            current_balance = wallet.experience_points
        elif currency_type == CurrencyType.PREMIUM_TOKENS:
            current_balance = wallet.premium_tokens
        
        if current_balance < amount:
            logger.warning(f"Insufficient {currency_type.value} for user {user_id}: {current_balance} < {amount}")
            return False
        
        # Deduct currency
        old_balance = current_balance
        new_balance = current_balance - amount
        
        if currency_type == CurrencyType.GEM_COINS:
            wallet.gem_coins = new_balance
            wallet.total_gems_spent += amount
        elif currency_type == CurrencyType.EXPERIENCE_POINTS:
            wallet.experience_points = new_balance
        elif currency_type == CurrencyType.PREMIUM_TOKENS:
            wallet.premium_tokens = new_balance
        
        wallet.updated_at = datetime.utcnow()
        await session.commit()
        
        # Log transaction (negative amount for spending)
        await self._create_transaction(
            session, wallet.id, currency_type, -amount,
            purpose, description, old_balance, new_balance
        )
        
        logger.info(f"Spent {amount} {currency_type.value} for user {user_id} (purpose: {purpose})")
        return True
    
    async def calculate_daily_reward(self, session: AsyncSession, user_id: str) -> Optional[RewardBundle]:
        """Calculate daily login reward based on streak."""
        # Get or create daily reward record
        result = await session.execute(
            select(DailyReward).where(DailyReward.user_id == user_id)
        )
        daily_reward = result.scalar_one_or_none()
        
        if not daily_reward:
            daily_reward = DailyReward(user_id=user_id)
            session.add(daily_reward)
        
        # Check if reward already claimed today
        today = datetime.utcnow().date()
        if daily_reward.last_claim_date and daily_reward.last_claim_date.date() == today:
            return None  # Already claimed today
        
        # Calculate streak
        yesterday = today - timedelta(days=1)
        if (daily_reward.last_claim_date and 
            daily_reward.last_claim_date.date() == yesterday):
            # Continue streak
            daily_reward.current_streak += 1
        elif (daily_reward.last_claim_date and 
              daily_reward.last_claim_date.date() < yesterday):
            # Streak broken
            daily_reward.current_streak = 1
        else:
            # First login or continuing today
            daily_reward.current_streak = max(1, daily_reward.current_streak)
        
        # Update longest streak
        daily_reward.longest_streak = max(daily_reward.longest_streak, daily_reward.current_streak)
        
        # Calculate rewards with streak bonus
        streak_multiplier = min(
            1 + (daily_reward.current_streak - 1) * self.constants.STREAK_MULTIPLIER,
            self.constants.MAX_STREAK_BONUS
        )
        
        gem_reward = int(self.constants.BASE_DAILY_GEMS * streak_multiplier)
        xp_reward = int(self.constants.BASE_DAILY_XP * streak_multiplier)
        
        # Update daily reward record
        daily_reward.last_claim_date = datetime.utcnow()
        daily_reward.total_logins += 1
        daily_reward.total_gems_from_daily += gem_reward
        daily_reward.next_reward_gems = int(self.constants.BASE_DAILY_GEMS * (streak_multiplier + self.constants.STREAK_MULTIPLIER))
        daily_reward.next_reward_xp = int(self.constants.BASE_DAILY_XP * (streak_multiplier + self.constants.STREAK_MULTIPLIER))
        
        await session.commit()
        
        return RewardBundle(
            gem_coins=gem_reward,
            experience_points=xp_reward,
            description=f"Day {daily_reward.current_streak} login bonus! {int((streak_multiplier - 1) * 100)}% streak bonus"
        )
    
    async def claim_daily_reward(self, session: AsyncSession, user_id: str) -> Optional[RewardBundle]:
        """Claim daily login reward and add to wallet."""
        reward = await self.calculate_daily_reward(session, user_id)
        if not reward:
            return None
        
        # Add rewards to wallet
        if reward.gem_coins > 0:
            await self.add_currency(
                session, user_id, CurrencyType.GEM_COINS, 
                reward.gem_coins, "daily_login", reward.description
            )
        
        if reward.experience_points > 0:
            await self.add_currency(
                session, user_id, CurrencyType.EXPERIENCE_POINTS,
                reward.experience_points, "daily_login", reward.description
            )
        
        return reward
    
    async def calculate_game_reward(
        self, 
        session: AsyncSession, 
        user_id: str, 
        won: bool, 
        bet_amount: float,
        win_streak: int = 0
    ) -> RewardBundle:
        """Calculate reward for playing roulette game."""
        if not won:
            # Small consolation XP for playing
            xp_reward = 5
            await self.add_currency(
                session, user_id, CurrencyType.EXPERIENCE_POINTS,
                xp_reward, "game_participation", "Thanks for playing!"
            )
            return RewardBundle(
                experience_points=xp_reward,
                description="Better luck next time!"
            )
        
        # Calculate win rewards
        base_gems = self.constants.ROULETTE_WIN_BASE_GEMS
        base_xp = self.constants.ROULETTE_WIN_BASE_XP
        
        # Streak bonus
        streak_multiplier = 1 + (win_streak * self.constants.WIN_STREAK_BONUS)
        
        # Bet size bonus (small bonus for higher bets)
        bet_multiplier = 1 + min(bet_amount / 1000, 0.5)  # Max 50% bonus
        
        final_gems = int(base_gems * streak_multiplier * bet_multiplier)
        final_xp = int(base_xp * streak_multiplier)
        
        # Add to wallet
        await self.add_currency(
            session, user_id, CurrencyType.GEM_COINS,
            final_gems, "game_win", f"Roulette win! Streak: {win_streak}"
        )
        await self.add_currency(
            session, user_id, CurrencyType.EXPERIENCE_POINTS,
            final_xp, "game_win", f"Roulette win! Streak: {win_streak}"
        )
        
        return RewardBundle(
            gem_coins=final_gems,
            experience_points=final_xp,
            description=f"Great win! {int((streak_multiplier - 1) * 100)}% streak bonus"
        )
    
    async def generate_random_item_drop(
        self, 
        session: AsyncSession, 
        user_id: str,
        drop_chance_multiplier: float = 1.0,
        min_rarity: Optional[ItemRarity] = None
    ) -> Optional[CollectibleItem]:
        """Generate random item drop based on rarity probabilities.

        If min_rarity is provided, guarantees rarity >= min_rarity when a drop occurs.
        """
        # Base 10% chance for item drop, modified by multiplier
        base_drop_chance = 0.1 * drop_chance_multiplier
        if random.random() > base_drop_chance:
            return None  # No drop
        
        # Determine rarity
        if min_rarity is not None:
            # Pick any rarity >= min_rarity by weighted probability limited to that range
            eligible = [(r, p) for r, p in self.constants.DROP_RATES.items() if self._rarity_rank(r) >= self._rarity_rank(min_rarity)]
            total_p = sum(p for _, p in eligible) or 1.0
            # Normalize
            rand = random.random() * total_p
            cumulative = 0
            selected_rarity = eligible[0][0]
            for rarity, prob in eligible:
                cumulative += prob
                if rand <= cumulative:
                    selected_rarity = rarity
                    break
        else:
            rand = random.random()
            cumulative_prob = 0
            selected_rarity = ItemRarity.COMMON
            for rarity, prob in self.constants.DROP_RATES.items():
                cumulative_prob += prob
                if rand <= cumulative_prob:
                    selected_rarity = rarity
                    break
        
        # Get random item of selected rarity
        result = await session.execute(
            select(CollectibleItem).where(
                CollectibleItem.rarity == selected_rarity.value,
                CollectibleItem.is_active == True
            )
        )
        available_items = result.scalars().all()
        
        if not available_items:
            logger.warning(f"No available items for rarity {selected_rarity}")
            return None
        
        dropped_item = random.choice(available_items)
        
        # Add to user inventory
        await self._add_item_to_inventory(session, user_id, dropped_item.id, "random_drop")
        
        logger.info(f"Item drop for user {user_id}: {dropped_item.name} ({selected_rarity.value})")
        return dropped_item

    def _rarity_rank(self, rarity: ItemRarity) -> int:
        order = [ItemRarity.COMMON, ItemRarity.UNCOMMON, ItemRarity.RARE, ItemRarity.EPIC, ItemRarity.LEGENDARY]
        return order.index(rarity)
    
    async def purchase_virtual_crypto(
        self,
        session: AsyncSession,
        user_id: str,
        crypto_id: str,
        crypto_symbol: str,
        gem_amount: float
    ) -> bool:
        """Purchase virtual cryptocurrency with GEM coins."""
        # Get current crypto price
        try:
            crypto_data = await self.data_manager.get_coin_data(crypto_id)
            if not crypto_data:
                logger.error(f"Could not get price data for {crypto_id}")
                return False
            
            current_price_usd = crypto_data.current_price
        except Exception as e:
            logger.error(f"Error getting crypto price: {e}")
            return False
        
        # Check if user has enough GEM coins
        if not await self.spend_currency(
            session, user_id, CurrencyType.GEM_COINS, 
            gem_amount, "crypto_purchase", f"Bought virtual {crypto_symbol}"
        ):
            return False
        
        # Calculate virtual crypto amount (1 GEM = 1 USD for simplicity)
        virtual_crypto_amount = gem_amount / current_price_usd
        
        # Get or create crypto holding
        wallet = await self.get_user_wallet(session, user_id)
        
        result = await session.execute(
            select(VirtualCryptoHolding).where(
                VirtualCryptoHolding.wallet_id == wallet.id,
                VirtualCryptoHolding.crypto_id == crypto_id
            )
        )
        holding = result.scalar_one_or_none()
        
        if holding:
            # Update existing holding
            old_amount = holding.virtual_amount
            old_invested = holding.total_gems_invested
            
            new_amount = old_amount + virtual_crypto_amount
            new_invested = old_invested + gem_amount
            
            # Calculate new average price
            holding.average_buy_price = (
                (old_amount * holding.average_buy_price + virtual_crypto_amount * current_price_usd) / 
                new_amount
            )
            holding.virtual_amount = new_amount
            holding.total_gems_invested = new_invested
        else:
            # Create new holding
            holding = VirtualCryptoHolding(
                wallet_id=wallet.id,
                crypto_id=crypto_id,
                crypto_symbol=crypto_symbol,
                virtual_amount=virtual_crypto_amount,
                total_gems_invested=gem_amount,
                average_buy_price=current_price_usd
            )
            session.add(holding)
        
        holding.updated_at = datetime.utcnow()
        await session.commit()
        
        logger.info(f"User {user_id} purchased {virtual_crypto_amount:.6f} virtual {crypto_symbol} for {gem_amount} GEM coins")
        return True

    async def get_active_effects(self, session: AsyncSession, user_id: str, scope: Optional[str] = None) -> Dict[str, Any]:
        """Return active effects for a user (optionally filtered by scope)."""
        now = datetime.utcnow()
        query = select(ActiveEffect).where(
            ActiveEffect.user_id == user_id,
            (ActiveEffect.expires_at.is_(None) | (ActiveEffect.expires_at > now))
        )
        if scope:
            query = query.where((ActiveEffect.scope == scope) | (ActiveEffect.scope == "GLOBAL"))
        res = await session.execute(query)
        effects: List[ActiveEffect] = res.scalars().all()
        return {
            "DROP_RATE": next((e for e in effects if e.effect_type == "DROP_RATE"), None),
            "XP_MULT": next((e for e in effects if e.effect_type == "XP_MULT"), None),
            "GEM_MULT": next((e for e in effects if e.effect_type == "GEM_MULT"), None),
            "GUARANTEED_RARE": next((e for e in effects if e.effect_type == "GUARANTEED_RARE"), None),
        }

    async def consume_effect_use(self, session: AsyncSession, effect: ActiveEffect) -> None:
        """Consume one use from a limited-use effect; delete if exhausted."""
        if effect.remaining_uses is None:
            return
        effect.remaining_uses = max(0, int(effect.remaining_uses) - 1)
        if effect.remaining_uses == 0:
            await session.delete(effect)
        await session.commit()
    
    async def _check_level_up(self, session: AsyncSession, wallet: VirtualWallet) -> bool:
        """Check if user leveled up and award level bonus."""
        current_level = wallet.level
        required_xp = self._calculate_xp_required(current_level + 1)
        
        if wallet.experience_points >= required_xp:
            # Level up!
            wallet.level += 1
            
            # Award level up bonus
            level_bonus = self.constants.LEVEL_UP_GEM_BONUS * wallet.level
            wallet.gem_coins += level_bonus
            wallet.total_gems_earned += level_bonus
            
            await session.commit()
            
            # Log level up transaction
            await self._create_transaction(
                session, wallet.id, CurrencyType.GEM_COINS, level_bonus,
                "level_up", f"Level {wallet.level} reached!", 
                wallet.gem_coins - level_bonus, wallet.gem_coins
            )
            
            logger.info(f"User leveled up to {wallet.level}! Bonus: {level_bonus} GEM coins")
            return True
        
        return False
    
    def _calculate_xp_required(self, level: int) -> int:
        """Calculate XP required for specific level."""
        if level <= 1:
            return 0
        return int(self.constants.XP_PER_LEVEL_BASE * (level - 1) ** self.constants.XP_PER_LEVEL_SCALING)
    
    async def _create_transaction(
        self,
        session: AsyncSession,
        wallet_id: str,
        currency_type: CurrencyType,
        amount: float,
        source: str,
        description: str,
        balance_before: float,
        balance_after: float,
        reference_id: Optional[str] = None
    ):
        """Create transaction record."""
        transaction = VirtualTransaction(
            wallet_id=wallet_id,
            transaction_type="EARN" if amount > 0 else "SPEND",
            currency_type=currency_type.value,
            amount=amount,
            source=source,
            description=description,
            reference_id=reference_id,
            balance_before=balance_before,
            balance_after=balance_after
        )
        
        session.add(transaction)
        await session.commit()
    
    async def _add_item_to_inventory(
        self,
        session: AsyncSession,
        user_id: str,
        item_id: str,
        acquisition_method: str
    ):
        """Add collectible item to user's inventory."""
        # Check if item already exists in inventory
        result = await session.execute(
            select(UserInventory).where(
                UserInventory.user_id == user_id,
                UserInventory.item_id == item_id
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Increase quantity
            existing.quantity += 1
        else:
            # Add new item
            inventory_item = UserInventory(
                user_id=user_id,
                item_id=item_id,
                acquisition_method=acquisition_method
            )
            session.add(inventory_item)
        
        await session.commit()
