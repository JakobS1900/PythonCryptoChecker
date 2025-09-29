"""
Bot System for Gambling Population
Creates and manages bot players to populate the gambling platform with realistic behavior.
"""

import random
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import (
    User, BotPersonalityType, BOT_PROFILE_DATA
)
from database.models import Wallet as Wall
from crypto.portfolio import portfolio_manager


class BotGamblingPersonality:
    """Defines a bot's gambling behavior patterns."""

    def __init__(self, personality_type: BotPersonalityType):
        self.personality_type = personality_type

        # Define betting parameters based on personality
        if personality_type == BotPersonalityType.CONSERVATIVE:
            self.min_bet = 10
            self.max_bet = 100
            self.bet_frequency = 0.6  # 60% chance to bet each round
            self.strategy_preference = ["red_black", "even_odd"]  # Safer bets
            self.risk_tolerance = 0.3

        elif personality_type == BotPersonalityType.AGGRESSIVE:
            self.min_bet = 50
            self.max_bet = 500
            self.bet_frequency = 0.8  # 80% chance to bet each round
            self.strategy_preference = ["single_number", "color", "category"]  # Riskier bets
            self.risk_tolerance = 0.8

        elif personality_type == BotPersonalityType.TREND_FOLLOWER:
            self.min_bet = 25
            self.max_bet = 200
            self.bet_frequency = 0.7
            self.strategy_preference = ["red_black", "even_odd", "high_low"]  # Follow trends
            self.risk_tolerance = 0.5

        elif personality_type == BotPersonalityType.OPPORTUNISTIC:
            self.min_bet = 20
            self.max_bet = 300
            self.bet_frequency = 0.5  # Bets less frequently, but larger when they do
            self.strategy_preference = ["single_number", "color"]  # Favorite-based
            self.risk_tolerance = 0.6

        elif personality_type == BotPersonalityType.PREDICTABLE_GAMBLER:
            self.min_bet = 15
            self.max_bet = 150
            self.bet_frequency = 0.9  # Bets most rounds
            self.strategy_preference = ["even_odd"]  # Pattern-based
            self.risk_tolerance = 0.4

        elif personality_type == BotPersonalityType.HIGHROLLER:
            self.min_bet = 100
            self.max_bet = 1000  # High roller bets
            self.bet_frequency = 0.3  # Bets less often but big when they do
            self.strategy_preference = ["single_number", "category"]  # High risk/high reward
            self.risk_tolerance = 0.9

        elif personality_type == BotPersonalityType.TIMID:
            self.min_bet = 10
            self.max_bet = 50
            self.bet_frequency = 0.2  # Rarely bets
            self.strategy_preference = ["red_black", "high_low"]  # Very safe
            self.risk_tolerance = 0.1

    def should_bet_this_round(self) -> bool:
        """Determine if this bot should place a bet this round."""
        return random.random() < self.bet_frequency

    def calculate_bet_amount(self, current_balance: float) -> float:
        """Calculate bet amount based on personality and balance."""
        if current_balance < self.min_bet:
            return 0  # Not enough to bet minimum

        # Scale bet size based on current balance and personality
        max_possible_bet = min(self.max_bet, current_balance * 0.1)  # Max 10% of balance

        if self.personality_type == BotPersonalityType.HIGHROLLER:
            # High rollers bet big regardless
            return max(self.min_bet, max_possible_bet * 0.8)
        elif self.personality_type == BotPersonalityType.AGGRESSIVE:
            # Aggressive bets larger percentages
            return max(self.min_bet, max_possible_bet * random.uniform(0.4, 0.7))
        else:
            # Conservative to moderate bets
            return max(self.min_bet, max_possible_bet * random.uniform(0.2, 0.5))

    def choose_bet_type(self) -> Dict[str, str]:
        """Choose bet type and value based on personality preference."""
        bet_type = random.choice(self.strategy_preference)

        if bet_type == "single_number":
            # Pick a number 0-36
            number = random.randint(0, 36)
            return {"type": "SINGLE_NUMBER", "value": str(number)}

        elif bet_type == "red_black":
            # Pick red or black
            color = random.choice(["red", "black"])
            return {"type": "RED_BLACK", "value": color}

        elif bet_type == "even_odd":
            # Pick even or odd
            choice = random.choice(["even", "odd"])
            return {"type": "EVEN_ODD", "value": choice}

        elif bet_type == "high_low":
            # Pick high (19-36) or low (1-18)
            choice = random.choice(["high", "low"])
            return {"type": "HIGH_LOW", "value": choice}

        elif bet_type == "color":
            # Same as red_black but more focused
            color = random.choice(["red", "black"])
            return {"type": "RED_BLACK", "value": color}

        elif bet_type == "category":
            # Pick a crypto category (would need more implementation)
            categories = ["BTC", "ETH", "DEFI", "MEME"]
            category = random.choice(categories)
            return {"type": "CRYPTO_CATEGORY", "value": category}

        else:
            # Fallback to safe bet
            color = random.choice(["red", "black"])
            return {"type": "RED_BLACK", "value": color}


class BotGambler:
    """Individual bot player with personality-driven behavior."""

    def __init__(self, user_id: str, personality: BotPersonalityType, balance: float):
        self.user_id = user_id
        self.personality = BotGamblingPersonality(personality)
        self.balance = balance
        self.win_streak = 0
        self.lose_streak = 0
        self.last_action = None

    def update_balance(self, new_balance: float):
        """Update bot's balance."""
        self.balance = new_balance

    def update_after_result(self, won: bool, amount: float):
        """Update bot's internal state based on betting result."""
        if won:
            self.win_streak += 1
            self.lose_streak = 0
        else:
            self.lose_streak += 1
            self.win_streak = 0

    def should_place_bet(self) -> bool:
        """Determine if bot should place a bet this round."""
        base_chance = self.personality.should_bet_this_round()

        # Adjust based on streaks
        if self.lose_streak >= 3 and self.personality.personality_type == BotPersonalityType.TREND_FOLLOWER:
            # Trend followers might chase losses
            base_chance += 0.2
        elif self.lose_streak >= 2 and self.personality.personality_type == BotPersonalityType.TIMID:
            # Timid bots bet even less when losing
            base_chance *= 0.5

        return random.random() < min(1.0, base_chance)

    def generate_bet(self) -> Optional[Dict]:
        """Generate a bet for this round."""
        if not self.should_place_bet():
            return None

        bet_amount = self.personality.calculate_bet_amount(self.balance)
        if bet_amount < self.personality.min_bet:
            return None

        bet_choice = self.personality.choose_bet_type()

        return {
            "user_id": self.user_id,
            "amount": bet_amount,
            "bet_type": bet_choice["type"],
            "bet_value": bet_choice["value"]
        }


class BotPopulationManager:
    """Manages the population of bot players for the gambling platform."""

    def __init__(self):
        self.bots: Dict[str, BotGambler] = {}  # user_id -> BotGambler
        self.active_rooms: List[str] = []  # Room codes where bots are active

    async def initialize_bots(self, num_bots: int = 22):
        """Create and initialize bot players."""
        async with AsyncSessionLocal() as session:
            # Check if bots already exist
            query = select(User).where(User.is_bot == True).limit(num_bots)
            result = await session.execute(query)
            existing_bots = result.scalars().all()

            if len(existing_bots) >= num_bots:
                print(f"✅ {len(existing_bots)} bots already exist")
            else:
                # Create missing bots
                existing_names = {bot.username for bot in existing_bots}
                needed_bots = num_bots - len(existing_bots)

                for bot_data in BOT_PROFILE_DATA:
                    if bot_data[0] in existing_names:
                        continue

                    # Create new bot
                    username, bio = bot_data

                    # Generate bot email
                    email = f"{username.replace(' ', '').lower()}@bot.crypto"

                    # Choose random personality
                    personality = random.choice(list(BotPersonalityType))

                    # Create bot user
                    bot_user = User(
                        username=username,
                        email=email,
                        password_hash="bot_password_placeholder",  # Bots don't log in normally
                        role="PLAYER",
                        is_active=True,
                        is_bot=True,
                        bot_personality=personality.value
                    )

                    session.add(bot_user)
                    await session.commit()
                    await session.refresh(bot_user)

                    # Create wallet with starting balance (2000 GEM for bots)
                    await portfolio_manager.create_wallet(str(bot_user.id), initial_gems=2000.0)

                    # Verify wallet was created correctly
                    balance = await portfolio_manager.get_user_balance(str(bot_user.id))
                    if balance < 2000.0:
                        print(f">> ERROR: Bot wallet for {username} created with insufficient balance: {balance} GEM")
                        # Try to correct the balance
                        await portfolio_manager.add_gems(str(bot_user.id), 2000.0 - balance, "Bot balance correction")
                    else:
                        print(f">> SUCCESS: Bot {username} wallet created with {balance} GEM")

                    print(f"🤖 Created bot: {username} (Personality: {personality.value})")
                    needed_bots -= 1

                    if needed_bots <= 0:
                        break

            await session.commit()

    async def load_bots(self):
        """Load all bots into memory."""
        async with AsyncSessionLocal() as session:
            query = select(User).where(User.is_bot == True, User.is_active == True)
            result = await session.execute(query)
            bot_users = result.scalars().all()

            for bot_user in bot_users:
                # Get bot's current balance
                balance = await portfolio_manager.get_user_balance(str(bot_user.id))
                personality = BotPersonalityType(bot_user.bot_personality)

                # CRITICAL: Repair corrupted bot balances during load
                if balance < 2000.0:
                    print(f">> CRITICAL: Bot {bot_user.username} has corrupted balance: {balance} GEM. Repairing...")
                    balance_diff = 2000.0 - balance
                    await portfolio_manager.add_gems(str(bot_user.id), balance_diff, "Bot balance repair")
                    balance = 2000.0
                    print(f">> SUCCESS: Repaired bot {bot_user.username} balance to {balance} GEM")

                # Create BotGambler instance
                bot = BotGambler(str(bot_user.id), personality, balance)
                self.bots[str(bot_user.id)] = bot

            print(f"🎰 Loaded {len(self.bots)} bot gamblers")

    async def get_bots_for_room(self, room_code: str, max_bots: int = 8) -> List[Dict]:
        """Get a subset of bots to populate a room."""
        if not self.bots:
            await self.load_bots()

        # Select random bots for this room
        available_bot_ids = list(self.bots.keys())
        selected_bot_ids = random.sample(available_bot_ids, min(max_bots, len(available_bot_ids)))

        # Return bot information (not the full BotGambler objects)
        bot_info = []
        for bot_id in selected_bot_ids:
            bot = self.bots[bot_id]
            # In a real implementation, we'd return safe data for frontend display
            bot_info.append({
                "user_id": bot_id,
                "personality": bot.personality.personality_type.value,
                "balance": bot.balance
            })

        return bot_info

    async def generate_bet_activity(self, room_code: str) -> List[Dict]:
        """Generate betting activity for bots in a room."""
        if not self.bots:
            await self.load_bots()

        bets = []

        # Get bots available for this room
        room_bots = await self.get_bots_for_room(room_code)

        for bot_info in room_bots:
            bot_id = bot_info["user_id"]
            if bot_id in self.bots:
                bot = self.bots[bot_id]

                # Update bot balance (would need real balance updates in production)
                current_balance = await portfolio_manager.get_user_balance(bot_id)
                bot.update_balance(current_balance)

                # Generate bet
                bet = bot.generate_bet()
                if bet:
                    # Add room context
                    bet["room_code"] = room_code
                    bets.append(bet)

        return bets

    async def update_bot_balances(self):
        """Update all bot balances (called periodically)."""
        for bot_id, bot in self.bots.items():
            current_balance = await portfolio_manager.get_user_balance(bot_id)
            bot.update_balance(current_balance)

    async def simulate_betting_round(self, room_code: str, spin_result: Dict) -> List[Dict]:
        """
        Simulate bot betting behavior for a completed spin.

        This would be called after each roulette spin to update bots as if they participated.
        """
        bots_activity = []

        room_bots = await self.get_bots_for_room(room_code)

        for bot_info in room_bots:
            bot_id = bot_info["user_id"]
            if bot_id in self.bots:
                bot = self.bots[bot_id]

                # Simulate bot having placed a bet (for variety)
                if random.random() < 0.4:  # 40% of bots "were betting"
                    bet_amount = bot.personality.calculate_bet_amount(bot.balance)
                    bet_choice = bot.personality.choose_bet_type()

                    # Determine if bot won (simplified - would use real bet calculation)
                    # This is just for demonstration - in real implementation would need
                    # actual bet placement and result calculation

                    bots_activity.append({
                        "bot_id": bot_id,
                        "bet_type": bet_choice["type"],
                        "bet_value": bet_choice["value"],
                        "bet_amount": bet_amount,
                        "won_result": random.choice([True, False])  # Simplified
                    })

        return bots_activity

    async def get_population_stats(self) -> Dict:
        """Get statistics about bot population."""
        if not self.bots:
            await self.load_bots()

        personalities = {}
        total_balance = 0

        for bot in self.bots.values():
            personality_key = bot.personality.personality_type.value
            personalities[personality_key] = personalities.get(personality_key, 0) + 1
            total_balance += bot.balance

        return {
            "total_bots": len(self.bots),
            "personalities": personalities,
            "average_balance": total_balance / len(self.bots) if self.bots else 0,
            "active_rooms": len(self.active_rooms)
        }


# Global bot population manager
bot_population_manager = BotPopulationManager()


# Helper functions for external use
async def initialize_bot_population(num_bots: int = 22):
    """Initialize the bot population."""
    await bot_population_manager.initialize_bots(num_bots)
    await bot_population_manager.load_bots()


async def get_room_bots(room_code: str, max_bots: int = 8) -> List[Dict]:
    """Get bots for a room to populate it."""
    return await bot_population_manager.get_bots_for_room(room_code, max_bots)


async def generate_bot_betting_activity(room_code: str) -> List[Dict]:
    """Generate simulated betting activity for bots."""
    return await bot_population_manager.generate_bet_activity(room_code)


async def get_bot_population_stats() -> Dict:
    """Get statistics about the current bot population."""
    return await bot_population_manager.get_population_stats()


async def simulate_round_completion(room_code: str, spin_result: Dict) -> List[Dict]:
    """Simulate completed betting round with bot participation."""
    return await bot_population_manager.simulate_betting_round(room_code, spin_result)
