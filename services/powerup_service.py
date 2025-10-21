"""
Power-up Service - Handles power-up activation, cooldowns, and effect application
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database.models import ClickerPowerup, ClickerPowerupCooldown, ClickerStats, Wallet
from config.clicker_phase2_config import POWERUP_CONFIGS


class PowerupService:
    """Service for managing power-ups and their effects."""

    async def get_active_powerups(self, user_id: str, db: AsyncSession) -> List[ClickerPowerup]:
        """Get all active power-ups for a user, removing expired ones."""
        now = datetime.utcnow()

        # Get all active power-ups
        result = await db.execute(
            select(ClickerPowerup).where(
                and_(
                    ClickerPowerup.user_id == user_id,
                    ClickerPowerup.is_active == True
                )
            )
        )
        powerups = result.scalars().all()

        # Deactivate expired power-ups
        expired_ids = []
        for powerup in powerups:
            if powerup.expires_at and powerup.expires_at <= now:
                powerup.is_active = False
                expired_ids.append(powerup.id)

        if expired_ids:
            await db.commit()

        # Return only non-expired
        return [p for p in powerups if p.id not in expired_ids]

    async def get_cooldowns(self, user_id: str, db: AsyncSession) -> Dict[str, datetime]:
        """Get all active cooldowns for a user."""
        now = datetime.utcnow()

        result = await db.execute(
            select(ClickerPowerupCooldown).where(
                and_(
                    ClickerPowerupCooldown.user_id == user_id,
                    ClickerPowerupCooldown.cooldown_ends_at > now
                )
            )
        )
        cooldowns = result.scalars().all()

        return {cd.powerup_type: cd.cooldown_ends_at for cd in cooldowns}

    async def activate_powerup(
        self,
        user_id: str,
        powerup_type: str,
        db: AsyncSession
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Activate a power-up for the user if they can afford it and it's not on cooldown.

        Returns: (success, message, data)
        """
        # Validate powerup type
        if powerup_type not in POWERUP_CONFIGS:
            return False, f"Unknown power-up type: {powerup_type}", {}

        config = POWERUP_CONFIGS[powerup_type]
        now = datetime.utcnow()

        # Check if on cooldown
        result = await db.execute(
            select(ClickerPowerupCooldown).where(
                and_(
                    ClickerPowerupCooldown.user_id == user_id,
                    ClickerPowerupCooldown.powerup_type == powerup_type
                )
            )
        )
        cooldown = result.scalar_one_or_none()

        if cooldown and cooldown.cooldown_ends_at > now:
            seconds_remaining = int((cooldown.cooldown_ends_at - now).total_seconds())
            return False, f"{config['name']} is on cooldown ({seconds_remaining}s remaining)", {}

        # Check if user can afford
        result = await db.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallet = result.scalar_one_or_none()

        if not wallet or wallet.gem_balance < config["cost"]:
            return False, f"Need {config['cost']} GEM (you have {wallet.gem_balance if wallet else 0})", {}

        # Deduct cost
        wallet.gem_balance -= config["cost"]

        # Create or update power-up record
        expires_at = None
        if config["duration"] > 0:
            expires_at = now + timedelta(seconds=config["duration"])

        powerup = ClickerPowerup(
            id=str(uuid.uuid4()),
            user_id=user_id,
            powerup_type=powerup_type,
            activated_at=now,
            expires_at=expires_at,
            is_active=True
        )
        db.add(powerup)

        # Set cooldown
        if cooldown:
            cooldown.cooldown_ends_at = now + timedelta(seconds=config["cooldown"])
        else:
            cooldown = ClickerPowerupCooldown(
                user_id=user_id,
                powerup_type=powerup_type,
                cooldown_ends_at=now + timedelta(seconds=config["cooldown"])
            )
            db.add(cooldown)

        # Apply instant effects
        instant_effect_message = ""
        if powerup_type == "energy_refill":
            # Instant energy refill
            result = await db.execute(
                select(ClickerStats).where(ClickerStats.user_id == user_id)
            )
            stats = result.scalar_one_or_none()
            if stats:
                stats.current_energy = stats.max_energy
                stats.last_energy_update = now
                instant_effect_message = f" Energy fully restored to {stats.max_energy}!"

        elif powerup_type == "mega_combo":
            # Instant combo boost
            instant_effect_message = " Combo count boosted by 10!"

        await db.commit()
        await db.refresh(powerup)

        return True, f"{config['name']} activated!{instant_effect_message}", {
            "powerup_id": powerup.id,
            "powerup_type": powerup_type,
            "name": config["name"],
            "duration": config["duration"],
            "expires_at": expires_at.isoformat() if expires_at else None,
            "cost_paid": config["cost"],
            "cooldown_seconds": config["cooldown"]
        }

    async def get_available_powerups(self, user_id: str, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get all power-ups with their availability status."""
        now = datetime.utcnow()

        # Get active powerups
        active_powerups = await self.get_active_powerups(user_id, db)
        active_types = {p.powerup_type for p in active_powerups}

        # Get cooldowns
        cooldowns = await self.get_cooldowns(user_id, db)

        # Get user wallet
        result = await db.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallet = result.scalar_one_or_none()
        user_balance = wallet.gem_balance if wallet else 0

        # Build powerup list
        powerups = []
        for powerup_type, config in POWERUP_CONFIGS.items():
            # Check if on cooldown
            cooldown_ends_at = cooldowns.get(powerup_type)
            on_cooldown = bool(cooldown_ends_at)
            seconds_remaining = int((cooldown_ends_at - now).total_seconds()) if cooldown_ends_at else 0

            # Check if active
            is_active = powerup_type in active_types
            active_powerup = next((p for p in active_powerups if p.powerup_type == powerup_type), None)

            # Calculate time remaining
            time_remaining = 0
            if is_active and active_powerup and active_powerup.expires_at:
                time_remaining = int((active_powerup.expires_at - now).total_seconds())

            powerups.append({
                "type": powerup_type,
                "name": config["name"],
                "cost": config["cost"],
                "duration": config["duration"],
                "cooldown": config["cooldown"],
                "can_afford": user_balance >= config["cost"],
                "is_active": is_active,
                "time_remaining": time_remaining,
                "on_cooldown": on_cooldown,
                "cooldown_remaining": seconds_remaining,
                "can_activate": not on_cooldown and not is_active and user_balance >= config["cost"]
            })

        return powerups

    def get_active_multipliers(self, active_powerups: List[ClickerPowerup]) -> Dict[str, float]:
        """
        Calculate multipliers from active power-ups.
        Called by clicker service to apply bonuses.
        All multipliers default to 1.0 (no change).
        """
        multipliers = {
            "click_reward": 1.0,
            "auto_click": 1.0,
            "bonus_chance": 1.0,
            "combo_boost": 1.0  # Fixed: was 0, should be 1.0 (neutral multiplier)
        }

        for powerup in active_powerups:
            config = POWERUP_CONFIGS.get(powerup.powerup_type)
            if not config:
                continue

            if powerup.powerup_type == "double_rewards":
                multipliers["click_reward"] *= config.get("multiplier", 2.0)

            elif powerup.powerup_type == "auto_burst":
                multipliers["auto_click"] *= config.get("multiplier", 5.0)

            elif powerup.powerup_type == "lucky_streak":
                multipliers["bonus_chance"] *= 1.5  # 50% higher bonus chance

            elif powerup.powerup_type == "mega_combo":
                multipliers["combo_boost"] += config.get("combo_boost", 10)

        return multipliers

    async def deactivate_powerup(
        self,
        powerup_id: str,
        db: AsyncSession
    ) -> Tuple[bool, str]:
        """Manually deactivate a power-up (for admin/testing purposes)."""
        result = await db.execute(
            select(ClickerPowerup).where(ClickerPowerup.id == powerup_id)
        )
        powerup = result.scalar_one_or_none()

        if not powerup:
            return False, "Power-up not found"

        powerup.is_active = False
        await db.commit()

        return True, f"Power-up {powerup.powerup_type} deactivated"
