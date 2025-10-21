"""
Prestige Service - Handles prestige system, PP calculation, resets, and prestige shop
"""

from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database.models import ClickerPrestige, ClickerStats, ClickerUpgradePurchase, Wallet, Transaction
from config.clicker_phase2_config import (
    calculate_prestige_points,
    calculate_prestige_bonuses,
    PRESTIGE_SHOP_ITEMS,
    PRESTIGE_MINIMUM_GEMS
)


class PrestigeService:
    """Service for handling prestige mechanics and prestige shop."""

    async def get_or_create_prestige(self, user_id: str, db: AsyncSession) -> ClickerPrestige:
        """Get or create prestige record for a user."""
        result = await db.execute(
            select(ClickerPrestige).where(ClickerPrestige.user_id == user_id)
        )
        prestige = result.scalar_one_or_none()

        if not prestige:
            prestige = ClickerPrestige(
                user_id=user_id,
                prestige_level=0,
                prestige_points=0,
                total_lifetime_gems=0.0,
                # All prestige shop items default to False
                has_click_master=False,
                has_energy_expert=False,
                has_quick_start=False,
                has_auto_unlock=False,
                has_multiplier_boost=False,
                has_prestige_master=False,
                last_prestige_at=None
            )
            db.add(prestige)
            await db.commit()
            await db.refresh(prestige)

        return prestige

    async def calculate_prestige_preview(
        self,
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Calculate how many PP the user would gain if they prestige now.
        Returns preview information without performing prestige.
        """
        # Get current stats
        result = await db.execute(
            select(ClickerStats).where(ClickerStats.user_id == user_id)
        )
        stats = result.scalar_one_or_none()

        if not stats:
            return {
                "can_prestige": False,
                "reason": "No clicker stats found",
                "current_gems_earned": 0,
                "pp_to_gain": 0
            }

        # Get current prestige data
        prestige = await self.get_or_create_prestige(user_id, db)

        # Calculate PP from current lifetime gems
        total_lifetime = prestige.total_lifetime_gems + stats.total_gems_earned
        new_total_pp = calculate_prestige_points(total_lifetime)
        pp_to_gain = new_total_pp - prestige.prestige_points

        # Check minimum requirement
        can_prestige = stats.total_gems_earned >= PRESTIGE_MINIMUM_GEMS and pp_to_gain > 0

        # Calculate current and new bonuses
        current_bonuses = calculate_prestige_bonuses(prestige.prestige_points)
        new_bonuses = calculate_prestige_bonuses(new_total_pp)

        return {
            "can_prestige": can_prestige,
            "reason": "Ready to prestige!" if can_prestige else f"Need {PRESTIGE_MINIMUM_GEMS} GEM earned this run",
            "current_gems_earned": stats.total_gems_earned,
            "total_lifetime_gems": total_lifetime,
            "current_pp": prestige.prestige_points,
            "pp_to_gain": pp_to_gain,
            "new_total_pp": new_total_pp,
            "current_bonuses": current_bonuses,
            "new_bonuses": new_bonuses,
            "prestige_level": prestige.prestige_level
        }

    async def perform_prestige(
        self,
        user_id: str,
        db: AsyncSession
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Perform prestige for a user - reset progress and award PP.

        Returns: (success, message, data)
        """
        # Check if prestige is possible
        preview = await self.calculate_prestige_preview(user_id, db)

        if not preview["can_prestige"]:
            return False, preview["reason"], {}

        pp_to_gain = preview["pp_to_gain"]

        # Get current data
        result = await db.execute(
            select(ClickerStats).where(ClickerStats.user_id == user_id)
        )
        stats = result.scalar_one()

        prestige = await self.get_or_create_prestige(user_id, db)

        # Store gems earned this run
        gems_this_run = stats.total_gems_earned

        # Update prestige record
        prestige.prestige_points += pp_to_gain
        prestige.prestige_level += 1
        prestige.total_lifetime_gems += gems_this_run
        prestige.last_prestige_at = datetime.utcnow()

        # Reset clicker stats (keep upgrade purchases but reset stats)
        stats.total_clicks = 0
        stats.total_gems_earned = 0.0
        stats.best_combo = 0
        stats.mega_bonuses_hit = 0
        stats.daily_streak = 0

        # Reset upgrades to level 1/0
        stats.click_power_level = 1
        stats.auto_clicker_level = 0
        stats.multiplier_level = 0
        stats.energy_capacity_level = 0
        stats.energy_regen_level = 0

        # Reset energy to max
        stats.current_energy = 100
        stats.max_energy = 100
        stats.last_energy_update = datetime.utcnow()

        # Delete all upgrade purchases
        await db.execute(
            select(ClickerUpgradePurchase).where(
                ClickerUpgradePurchase.user_id == user_id
            )
        )
        await db.execute(
            ClickerUpgradePurchase.__table__.delete().where(
                ClickerUpgradePurchase.user_id == user_id
            )
        )

        # Apply prestige shop bonuses if purchased
        if prestige.has_click_master:
            stats.click_power_level = 2  # Start at level 2

        if prestige.has_energy_expert:
            stats.energy_capacity_level = 2  # Start with more energy
            stats.max_energy = 120
            stats.current_energy = 120

        # Quick start bonus handled on first click
        # Other bonuses are passive and applied via multipliers

        await db.commit()
        await db.refresh(prestige)
        await db.refresh(stats)

        # Calculate new bonuses
        new_bonuses = calculate_prestige_bonuses(prestige.prestige_points)

        return True, f"Prestige successful! Gained {pp_to_gain} PP", {
            "pp_gained": pp_to_gain,
            "new_total_pp": prestige.prestige_points,
            "prestige_level": prestige.prestige_level,
            "gems_sacrificed": gems_this_run,
            "new_bonuses": new_bonuses
        }

    async def get_prestige_shop(
        self,
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get prestige shop items and user's purchase status."""
        prestige = await self.get_or_create_prestige(user_id, db)

        shop_items = []
        for item_id, config in PRESTIGE_SHOP_ITEMS.items():
            # Check if user owns this item
            owned = getattr(prestige, f"has_{item_id}", False)

            shop_items.append({
                "id": item_id,
                "name": config["name"],
                "description": config["description"],
                "cost_pp": config["cost_pp"],
                "owned": owned,
                "can_afford": prestige.prestige_points >= config["cost_pp"] and not owned
            })

        return {
            "current_pp": prestige.prestige_points,
            "items": shop_items
        }

    async def purchase_prestige_shop_item(
        self,
        user_id: str,
        item_id: str,
        db: AsyncSession
    ) -> Tuple[bool, str]:
        """
        Purchase a prestige shop item with PP.

        Returns: (success, message)
        """
        # Validate item exists
        if item_id not in PRESTIGE_SHOP_ITEMS:
            return False, f"Item '{item_id}' not found in prestige shop"

        item_config = PRESTIGE_SHOP_ITEMS[item_id]
        prestige = await self.get_or_create_prestige(user_id, db)

        # Check if already owned
        if getattr(prestige, f"has_{item_id}", False):
            return False, f"You already own '{item_config['name']}'"

        # Check if can afford
        if prestige.prestige_points < item_config["cost_pp"]:
            return False, f"Need {item_config['cost_pp']} PP (you have {prestige.prestige_points})"

        # Purchase item
        prestige.prestige_points -= item_config["cost_pp"]
        setattr(prestige, f"has_{item_id}", True)

        await db.commit()
        await db.refresh(prestige)

        return True, f"Purchased '{item_config['name']}' for {item_config['cost_pp']} PP!"

    def get_prestige_multipliers(self, prestige: ClickerPrestige) -> Dict[str, float]:
        """
        Calculate all prestige multipliers for a user.
        Used by clicker service to apply bonuses.

        Returns dict with:
        - click_bonus: Multiplier for click rewards (1.0 = no bonus)
        - energy_regen_bonus: Multiplier for energy regen (1.0 = no bonus)
        - bonus_chance: Multiplier for bonus drop chances (1.0 = no bonus)
        - has_*: Boolean flags for prestige shop purchases
        """
        bonuses = calculate_prestige_bonuses(prestige.prestige_points)

        return {
            "click_bonus": bonuses["click_multiplier"],
            "energy_regen_bonus": bonuses["energy_regen_multiplier"],
            "bonus_chance": bonuses["bonus_chance_multiplier"],
            "has_click_master": prestige.has_click_master,
            "has_energy_expert": prestige.has_energy_expert,
            "has_quick_start": prestige.has_quick_start,
            "has_auto_unlock": prestige.has_auto_unlock,
            "has_multiplier_boost": prestige.has_multiplier_boost,
            "has_prestige_master": prestige.has_prestige_master
        }
