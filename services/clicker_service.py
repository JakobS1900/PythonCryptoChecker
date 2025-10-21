"""
Clicker Service - Handles all clicker game logic including upgrades, energy, combos, and passive income.
Phase 2: Integrated with Prestige and Power-up systems
"""

import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database.models import ClickerStats, ClickerUpgradePurchase, Wallet, Transaction, User
from config.clicker_upgrades import (
    get_click_reward_range,
    get_auto_click_info,
    get_multiplier,
    get_max_energy,
    get_energy_regen_rate,
    get_upgrade_cost,
    can_afford_upgrade,
    get_combo_multiplier,
    BONUS_CHANCES,
    UPGRADE_CATEGORIES,
    COMBO_WINDOW_SECONDS
)
from services.prestige_service import PrestigeService
from services.powerup_service import PowerupService
from services.clicker_leaderboard_service import ClickerLeaderboardService


class ClickerService:
    """Centralized service for all clicker game operations."""

    def __init__(self):
        self.active_combos = {}  # user_id -> {"count": int, "last_click": datetime}
        self.prestige_service = PrestigeService()
        self.powerup_service = PowerupService()
        self.leaderboard_service = ClickerLeaderboardService()

    async def get_or_create_stats(self, user_id: str, db: AsyncSession) -> ClickerStats:
        """Get or create clicker stats for a user."""
        result = await db.execute(
            select(ClickerStats).where(ClickerStats.user_id == user_id)
        )
        stats = result.scalar_one_or_none()

        if not stats:
            stats = ClickerStats(
                user_id=user_id,
                total_clicks=0,
                total_gems_earned=0.0,
                best_combo=0,
                mega_bonuses_hit=0,
                click_power_level=1,
                auto_clicker_level=0,
                multiplier_level=0,
                energy_capacity_level=0,
                energy_regen_level=0,
                current_energy=100,
                max_energy=100,
                last_energy_update=datetime.utcnow(),
                daily_streak=0
            )
            db.add(stats)
            await db.commit()
            await db.refresh(stats)

        return stats

    async def regenerate_energy(self, stats: ClickerStats, db: AsyncSession, user_id: str = None) -> int:
        """Regenerate energy based on time passed and regen rate (with Phase 2 bonuses)."""
        now = datetime.utcnow()
        time_diff = (now - stats.last_energy_update).total_seconds()

        if time_diff <= 0:
            return stats.current_energy

        # Calculate base energy regenerated
        regen_rate = get_energy_regen_rate(stats.energy_regen_level)

        # Apply prestige energy regen bonus if user_id provided
        if user_id:
            prestige = await self.prestige_service.get_or_create_prestige(user_id, db)
            prestige_multipliers = self.prestige_service.get_prestige_multipliers(prestige)
            regen_rate *= prestige_multipliers["energy_regen_bonus"]

        energy_per_second = regen_rate / 60
        energy_to_add = int(time_diff * energy_per_second)

        if energy_to_add > 0:
            old_energy = stats.current_energy
            stats.current_energy = min(stats.max_energy, stats.current_energy + energy_to_add)
            stats.last_energy_update = now

            # Only commit if energy actually changed
            if stats.current_energy != old_energy:
                await db.commit()

        return stats.current_energy

    async def process_auto_click_rewards(self, stats: ClickerStats, user_id: str, db: AsyncSession) -> float:
        """Process and claim accumulated auto-click rewards (Phase 2: with power-up bonuses)."""
        if stats.auto_clicker_level == 0:
            return 0.0

        now = datetime.utcnow()
        last_auto = stats.last_auto_click or stats.created_at

        auto_info = get_auto_click_info(stats.auto_clicker_level)
        interval = auto_info["interval_seconds"]
        gems_per_tick = auto_info["gems_per_tick"]

        # Calculate number of ticks since last claim
        time_diff = (now - last_auto).total_seconds()
        ticks = int(time_diff / interval)

        if ticks <= 0:
            return stats.auto_click_accumulated

        # Get Phase 2 bonuses
        active_powerups = await self.powerup_service.get_active_powerups(user_id, db)
        powerup_multipliers = self.powerup_service.get_active_multipliers(active_powerups)

        # Calculate total passive gems earned with Phase 2 bonuses
        base_passive_gems = ticks * gems_per_tick
        multiplier = get_multiplier(stats.multiplier_level)
        # Apply power-up auto-click multiplier
        total_passive_gems = base_passive_gems * multiplier * powerup_multipliers["auto_click"]

        # Update stats
        stats.last_auto_click = now
        stats.auto_click_accumulated += total_passive_gems
        stats.total_gems_earned += total_passive_gems

        await db.commit()

        return total_passive_gems

    async def claim_passive_rewards(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Claim all accumulated passive rewards."""
        stats = await self.get_or_create_stats(user_id, db)

        if stats.auto_click_accumulated <= 0:
            return {
                "success": False,
                "message": "No passive rewards to claim",
                "accumulated": 0.0
            }

        # Add gems to wallet
        wallet_result = await db.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallet = wallet_result.scalar_one_or_none()

        if not wallet:
            return {
                "success": False,
                "message": "Wallet not found"
            }

        claimed_amount = stats.auto_click_accumulated
        old_balance = wallet.gem_balance
        wallet.gem_balance += claimed_amount

        # Create transaction
        transaction = Transaction(
            user_id=user_id,
            amount=claimed_amount,
            balance_before=old_balance,
            balance_after=wallet.gem_balance,
            transaction_type="BONUS",
            description=f"Auto-clicker passive rewards ({int(claimed_amount)} GEM)"
        )
        db.add(transaction)

        # Reset accumulated
        stats.auto_click_accumulated = 0.0

        await db.commit()
        await db.refresh(wallet)

        return {
            "success": True,
            "claimed": claimed_amount,
            "new_balance": wallet.gem_balance
        }

    async def handle_click(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Process a single click and return rewards (Phase 2: with prestige and power-up bonuses)."""
        stats = await self.get_or_create_stats(user_id, db)

        # Regenerate energy first (with prestige bonus)
        await self.regenerate_energy(stats, db, user_id)

        # Check energy
        if stats.current_energy < 1:
            return {
                "success": False,
                "error": "Not enough energy",
                "current_energy": stats.current_energy
            }

        # Consume energy
        stats.current_energy -= 1

        # Get Phase 2 bonuses
        prestige = await self.prestige_service.get_or_create_prestige(user_id, db)
        prestige_multipliers = self.prestige_service.get_prestige_multipliers(prestige)

        active_powerups = await self.powerup_service.get_active_powerups(user_id, db)
        powerup_multipliers = self.powerup_service.get_active_multipliers(active_powerups)

        # Calculate base reward
        min_reward, max_reward = get_click_reward_range(stats.click_power_level)
        base_reward = random.randint(min_reward, max_reward)

        # Check for bonuses (with prestige and power-up bonus chance multipliers)
        bonus = 0
        bonus_type = None
        bonus_roll = random.random()

        # Calculate bonus chances with Phase 2 multipliers
        mega_chance = BONUS_CHANCES["mega"]["base_chance"] * prestige_multipliers["bonus_chance"] * powerup_multipliers["bonus_chance"]
        big_chance = BONUS_CHANCES["big"]["base_chance"] * prestige_multipliers["bonus_chance"] * powerup_multipliers["bonus_chance"]
        medium_chance = BONUS_CHANCES["medium"]["base_chance"] * prestige_multipliers["bonus_chance"] * powerup_multipliers["bonus_chance"]

        if bonus_roll < mega_chance:
            bonus = BONUS_CHANCES["mega"]["reward"]
            bonus_type = "mega"
            stats.mega_bonuses_hit += 1
        elif bonus_roll < mega_chance + big_chance:
            bonus = BONUS_CHANCES["big"]["reward"]
            bonus_type = "big"
        elif bonus_roll < mega_chance + big_chance + medium_chance:
            bonus = BONUS_CHANCES["medium"]["reward"]
            bonus_type = "medium"

        # Calculate combo
        now = datetime.utcnow()
        combo_count = 0
        combo_multiplier = 1.0
        combo_name = ""

        if user_id in self.active_combos:
            last_click_time = self.active_combos[user_id]["last_click"]
            time_since_last = (now - last_click_time).total_seconds()

            if time_since_last <= COMBO_WINDOW_SECONDS:
                # Continue combo
                self.active_combos[user_id]["count"] += 1
                self.active_combos[user_id]["last_click"] = now
                combo_count = self.active_combos[user_id]["count"]
            else:
                # Combo broke, restart
                self.active_combos[user_id] = {"count": 1, "last_click": now}
                combo_count = 1
        else:
            # Start new combo
            self.active_combos[user_id] = {"count": 1, "last_click": now}
            combo_count = 1

        # Get combo multiplier
        if combo_count > 2:
            combo_multiplier, combo_name = get_combo_multiplier(combo_count)

        # Apply power-up combo boost
        combo_multiplier *= powerup_multipliers["combo_boost"]

        # Update best combo
        if combo_count > stats.best_combo:
            stats.best_combo = combo_count

        # Apply global multiplier
        global_multiplier = get_multiplier(stats.multiplier_level)

        # Calculate total reward with all Phase 2 multipliers
        # Base formula: (base + bonus) * global * combo
        # Phase 2 adds: prestige click bonus multiplier, power-up click reward multiplier
        total_reward = (base_reward + bonus) * prestige_multipliers["click_bonus"] * global_multiplier * combo_multiplier * powerup_multipliers["click_reward"]

        # Update stats
        stats.total_clicks += 1
        stats.total_gems_earned += total_reward

        # Update daily streak
        if stats.last_click_date:
            days_since = (now.date() - stats.last_click_date.date()).days
            if days_since == 0:
                # Same day, keep streak
                pass
            elif days_since == 1:
                # Next day, increase streak
                stats.daily_streak += 1
            else:
                # Streak broken
                stats.daily_streak = 1
        else:
            stats.daily_streak = 1

        stats.last_click_date = now

        # Add gems to wallet
        wallet_result = await db.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallet = wallet_result.scalar_one_or_none()

        if not wallet:
            return {
                "success": False,
                "error": "Wallet not found"
            }

        old_balance = wallet.gem_balance
        wallet.gem_balance += total_reward

        # Create transaction
        message_parts = [f"+{int(total_reward)} GEM"]
        if bonus_type:
            message_parts.append(f"({BONUS_CHANCES[bonus_type]['name']})")
        if combo_count > 2:
            message_parts.append(f"{combo_name} x{combo_count}")

        transaction = Transaction(
            user_id=user_id,
            amount=total_reward,
            balance_before=old_balance,
            balance_after=wallet.gem_balance,
            transaction_type="BONUS",
            description=f"Click reward: {' '.join(message_parts)}"
        )
        db.add(transaction)

        await db.commit()
        await db.refresh(wallet)
        await db.refresh(stats)

        # Update leaderboard stats (Phase 3B)
        await self.leaderboard_service.update_leaderboard_stats(
            db,
            user_id=user_id,
            total_clicks=stats.total_clicks,
            best_combo=stats.best_combo,
            total_gems_earned=stats.total_gems_earned,
            prestige_level=prestige.prestige_level,
            daily_gems_earned=stats.total_gems_earned  # Will handle daily reset separately
        )

        return {
            "success": True,
            "reward": int(total_reward),
            "base_reward": base_reward,
            "bonus": bonus,
            "bonus_type": bonus_type,
            "combo_count": combo_count,
            "combo_multiplier": combo_multiplier,
            "combo_name": combo_name,
            "global_multiplier": global_multiplier,
            "new_balance": wallet.gem_balance,
            "current_energy": stats.current_energy,
            "max_energy": stats.max_energy,
            "message": " ".join(message_parts)
        }

    async def purchase_upgrade(self, user_id: str, category: str, db: AsyncSession) -> Dict[str, Any]:
        """Purchase an upgrade for the user."""
        if category not in UPGRADE_CATEGORIES:
            return {
                "success": False,
                "error": f"Invalid upgrade category: {category}"
            }

        stats = await self.get_or_create_stats(user_id, db)

        # Get current level for this category
        current_level = getattr(stats, f"{category}_level", 0)
        max_level = UPGRADE_CATEGORIES[category]["max_level"]

        if current_level >= max_level:
            return {
                "success": False,
                "error": "Already at max level"
            }

        # Check cost
        cost = get_upgrade_cost(category, current_level)
        if cost is None:
            return {
                "success": False,
                "error": "Max level reached"
            }

        # Check if user can afford
        wallet_result = await db.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallet = wallet_result.scalar_one_or_none()

        if not wallet or wallet.gem_balance < cost:
            return {
                "success": False,
                "error": f"Not enough GEM (need {cost}, have {wallet.gem_balance if wallet else 0})"
            }

        # Deduct cost
        old_balance = wallet.gem_balance
        wallet.gem_balance -= cost

        # Upgrade level
        new_level = current_level + 1
        setattr(stats, f"{category}_level", new_level)

        # Update max energy if needed
        if category == "energy_capacity":
            new_max = get_max_energy(new_level)
            stats.max_energy = new_max
            stats.current_energy = min(stats.current_energy, new_max)

        # Create transaction
        upgrade_name = UPGRADE_CATEGORIES[category]["upgrades"][new_level]["name"]
        transaction = Transaction(
            user_id=user_id,
            amount=-cost,
            balance_before=old_balance,
            balance_after=wallet.gem_balance,
            transaction_type="BONUS",  # Could create UPGRADE type
            description=f"Purchased {upgrade_name} (Level {new_level})"
        )
        db.add(transaction)

        # Record purchase
        purchase = ClickerUpgradePurchase(
            user_id=user_id,
            upgrade_type=category,
            level_purchased=new_level,
            cost_gems=cost
        )
        db.add(purchase)

        await db.commit()
        await db.refresh(wallet)
        await db.refresh(stats)

        return {
            "success": True,
            "upgrade_name": upgrade_name,
            "new_level": new_level,
            "cost": cost,
            "new_balance": wallet.gem_balance
        }

    async def get_user_upgrades(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get all upgrade information for a user."""
        stats = await self.get_or_create_stats(user_id, db)
        wallet_result = await db.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallet = wallet_result.scalar_one_or_none()
        balance = wallet.gem_balance if wallet else 0.0

        upgrades = {}

        for category, category_info in UPGRADE_CATEGORIES.items():
            current_level = getattr(stats, f"{category}_level", 0)
            max_level = category_info["max_level"]
            next_cost = get_upgrade_cost(category, current_level)
            can_afford = can_afford_upgrade(category, current_level, balance)

            current_upgrade_info = category_info["upgrades"][current_level]
            next_upgrade_info = category_info["upgrades"].get(current_level + 1) if next_cost else None

            upgrades[category] = {
                "name": category_info["name"],
                "description": category_info["description"],
                "icon": category_info["icon"],
                "color": category_info["color"],
                "current_level": current_level,
                "max_level": max_level,
                "upgrades": category_info["upgrades"],  # Include full upgrades dict with numeric keys
                "current_upgrade": current_upgrade_info,
                "next_upgrade": next_upgrade_info,
                "next_cost": next_cost,
                "can_afford": can_afford,
                "is_max": current_level >= max_level
            }

        return {
            "upgrades": upgrades,
            "balance": balance
        }


# Global singleton instance
clicker_service = ClickerService()
