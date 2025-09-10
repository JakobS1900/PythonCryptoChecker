"""
Spin-to-Win Wheel System
Free hourly spins and special event wheels for GEM coins and rewards.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, JSON
from database import Base, get_db_session
from gamification import VirtualEconomyEngine, RewardBundle
from logger import logger


class WheelType(Enum):
    BASIC_HOURLY = "BASIC_HOURLY"      # Free hourly spin
    PREMIUM_DAILY = "PREMIUM_DAILY"    # Premium daily wheel
    EVENT_SPECIAL = "EVENT_SPECIAL"    # Special event wheels
    MEGA_WEEKLY = "MEGA_WEEKLY"        # Weekly mega rewards
    STREAK_BONUS = "STREAK_BONUS"      # Streak milestone wheels


class RewardType(Enum):
    GEM_COINS = "GEM_COINS"
    EXPERIENCE = "EXPERIENCE"
    COLLECTIBLE_ITEM = "COLLECTIBLE_ITEM"
    MULTIPLIER_BOOST = "MULTIPLIER_BOOST"
    FREE_SPINS = "FREE_SPINS"
    SPECIAL_BADGE = "SPECIAL_BADGE"


@dataclass
class WheelSegment:
    """Individual segment of the spin wheel."""
    id: str
    label: str
    reward_type: RewardType
    reward_amount: float
    probability: float  # Probability weight (0.0 to 1.0)
    color: str
    rarity: str  # COMMON, RARE, EPIC, LEGENDARY
    special_effect: Optional[str] = None


@dataclass
class SpinResult:
    """Result of a wheel spin."""
    segment: WheelSegment
    spin_angle: float
    timestamp: datetime
    multiplier_applied: float = 1.0


class SpinWheelSession(Base):
    """Database model for spin wheel sessions and history."""
    __tablename__ = "spin_wheel_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    
    # Wheel Configuration
    wheel_type = Column(String)
    wheel_config = Column(JSON)  # Segments and probabilities
    
    # Spin Details
    spin_result = Column(JSON)  # Winning segment and details
    spin_angle = Column(Float)  # Final wheel position
    
    # Rewards
    reward_type = Column(String)
    reward_amount = Column(Float)
    gem_coins_awarded = Column(Float, default=0.0)
    xp_awarded = Column(Integer, default=0)
    item_awarded = Column(String)  # Item ID if applicable
    
    # Timing and Restrictions
    spin_time = Column(DateTime, default=datetime.utcnow)
    next_available_spin = Column(DateTime)  # When next spin is available
    
    # Special Effects
    multiplier_applied = Column(Float, default=1.0)
    bonus_triggered = Column(String)  # Special bonus if triggered
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class UserSpinStatus(Base):
    """Track user's spin availability and streaks."""
    __tablename__ = "user_spin_status"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, unique=True)
    
    # Spin Availability
    last_hourly_spin = Column(DateTime)
    last_daily_spin = Column(DateTime)
    last_weekly_spin = Column(DateTime)
    
    # Free spins earned from other activities
    free_spins_available = Column(Integer, default=0)
    
    # Streaks and Statistics
    consecutive_days_spun = Column(Integer, default=0)
    total_spins = Column(Integer, default=0)
    total_gems_won = Column(Float, default=0.0)
    
    # Lucky multipliers
    luck_multiplier = Column(Float, default=1.0)  # From achievements/items
    temporary_boost_expires = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SpinWheelGame:
    """Spin-to-win wheel system for earning rewards."""
    
    def __init__(self, virtual_economy: VirtualEconomyEngine):
        self.virtual_economy = virtual_economy
    
    def _create_basic_hourly_wheel(self) -> List[WheelSegment]:
        """Create segments for basic hourly wheel."""
        return [
            WheelSegment("gems_10", "10 GEM", RewardType.GEM_COINS, 10, 0.25, "#4ade80", "COMMON"),
            WheelSegment("gems_25", "25 GEM", RewardType.GEM_COINS, 25, 0.20, "#22c55e", "COMMON"),
            WheelSegment("gems_50", "50 GEM", RewardType.GEM_COINS, 50, 0.15, "#16a34a", "RARE"),
            WheelSegment("xp_15", "15 XP", RewardType.EXPERIENCE, 15, 0.15, "#3b82f6", "COMMON"),
            WheelSegment("xp_30", "30 XP", RewardType.EXPERIENCE, 30, 0.10, "#2563eb", "RARE"),
            WheelSegment("gems_100", "100 GEM", RewardType.GEM_COINS, 100, 0.08, "#f59e0b", "EPIC"),
            WheelSegment("free_spin", "Free Spin", RewardType.FREE_SPINS, 1, 0.05, "#8b5cf6", "EPIC"),
            WheelSegment("gems_200", "200 GEM", RewardType.GEM_COINS, 200, 0.02, "#ef4444", "LEGENDARY")
        ]
    
    def _create_premium_daily_wheel(self) -> List[WheelSegment]:
        """Create segments for premium daily wheel."""
        return [
            WheelSegment("gems_50", "50 GEM", RewardType.GEM_COINS, 50, 0.20, "#4ade80", "COMMON"),
            WheelSegment("gems_100", "100 GEM", RewardType.GEM_COINS, 100, 0.18, "#22c55e", "COMMON"),
            WheelSegment("gems_200", "200 GEM", RewardType.GEM_COINS, 200, 0.15, "#16a34a", "RARE"),
            WheelSegment("xp_50", "50 XP", RewardType.EXPERIENCE, 50, 0.12, "#3b82f6", "RARE"),
            WheelSegment("item_rare", "Rare Item", RewardType.COLLECTIBLE_ITEM, 1, 0.10, "#f59e0b", "EPIC"),
            WheelSegment("multiplier", "2x Boost", RewardType.MULTIPLIER_BOOST, 2, 0.08, "#8b5cf6", "EPIC"),
            WheelSegment("gems_500", "500 GEM", RewardType.GEM_COINS, 500, 0.05, "#ef4444", "LEGENDARY"),
            WheelSegment("mega_prize", "MEGA PRIZE", RewardType.SPECIAL_BADGE, 1, 0.02, "#dc2626", "LEGENDARY", "JACKPOT")
        ]
    
    def _create_mega_weekly_wheel(self) -> List[WheelSegment]:
        """Create segments for mega weekly wheel."""
        return [
            WheelSegment("gems_200", "200 GEM", RewardType.GEM_COINS, 200, 0.15, "#4ade80", "COMMON"),
            WheelSegment("gems_500", "500 GEM", RewardType.GEM_COINS, 500, 0.15, "#22c55e", "RARE"),
            WheelSegment("gems_1000", "1000 GEM", RewardType.GEM_COINS, 1000, 0.12, "#16a34a", "RARE"),
            WheelSegment("xp_200", "200 XP", RewardType.EXPERIENCE, 200, 0.12, "#3b82f6", "RARE"),
            WheelSegment("item_epic", "Epic Item", RewardType.COLLECTIBLE_ITEM, 1, 0.10, "#f59e0b", "EPIC"),
            WheelSegment("multiplier_5x", "5x Boost", RewardType.MULTIPLIER_BOOST, 5, 0.08, "#8b5cf6", "EPIC"),
            WheelSegment("gems_2500", "2500 GEM", RewardType.GEM_COINS, 2500, 0.05, "#ef4444", "LEGENDARY"),
            WheelSegment("legendary_item", "Legendary Item", RewardType.COLLECTIBLE_ITEM, 1, 0.03, "#dc2626", "LEGENDARY", "ULTIMATE")
        ]
    
    async def get_available_wheels(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get all available wheels for the user."""
        
        # Get or create user spin status
        from sqlalchemy import select
        result = await session.execute(
            select(UserSpinStatus).where(UserSpinStatus.user_id == user_id)
        )
        spin_status = result.scalar_one_or_none()
        
        if not spin_status:
            spin_status = UserSpinStatus(user_id=user_id)
            session.add(spin_status)
            await session.commit()
        
        now = datetime.utcnow()
        available_wheels = []
        
        # Check hourly wheel (available every hour)
        if not spin_status.last_hourly_spin or (now - spin_status.last_hourly_spin) >= timedelta(hours=1):
            available_wheels.append({
                "type": WheelType.BASIC_HOURLY.value,
                "name": "Hourly Spin",
                "description": "Free spin every hour!",
                "cost": 0,
                "segments": [s.__dict__ for s in self._create_basic_hourly_wheel()],
                "available": True
            })
        else:
            next_available = spin_status.last_hourly_spin + timedelta(hours=1)
            available_wheels.append({
                "type": WheelType.BASIC_HOURLY.value,
                "name": "Hourly Spin",
                "description": "Free spin every hour!",
                "cost": 0,
                "available": False,
                "next_available": next_available.isoformat()
            })
        
        # Check daily wheel (available every 24 hours)
        if not spin_status.last_daily_spin or (now - spin_status.last_daily_spin) >= timedelta(days=1):
            available_wheels.append({
                "type": WheelType.PREMIUM_DAILY.value,
                "name": "Daily Premium Wheel",
                "description": "Better rewards, once per day!",
                "cost": 0,
                "segments": [s.__dict__ for s in self._create_premium_daily_wheel()],
                "available": True
            })
        else:
            next_available = spin_status.last_daily_spin + timedelta(days=1)
            available_wheels.append({
                "type": WheelType.PREMIUM_DAILY.value,
                "name": "Daily Premium Wheel",
                "description": "Better rewards, once per day!",
                "cost": 0,
                "available": False,
                "next_available": next_available.isoformat()
            })
        
        # Check weekly wheel (available every 7 days)
        if not spin_status.last_weekly_spin or (now - spin_status.last_weekly_spin) >= timedelta(days=7):
            available_wheels.append({
                "type": WheelType.MEGA_WEEKLY.value,
                "name": "Mega Weekly Wheel",
                "description": "MASSIVE rewards, once per week!",
                "cost": 0,
                "segments": [s.__dict__ for s in self._create_mega_weekly_wheel()],
                "available": True
            })
        else:
            next_available = spin_status.last_weekly_spin + timedelta(days=7)
            available_wheels.append({
                "type": WheelType.MEGA_WEEKLY.value,
                "name": "Mega Weekly Wheel",
                "description": "MASSIVE rewards, once per week!",
                "cost": 0,
                "available": False,
                "next_available": next_available.isoformat()
            })
        
        # Free spins from other activities
        if spin_status.free_spins_available > 0:
            available_wheels.append({
                "type": "FREE_BONUS",
                "name": f"Bonus Spins ({spin_status.free_spins_available})",
                "description": "Free spins earned from activities!",
                "cost": 0,
                "segments": [s.__dict__ for s in self._create_premium_daily_wheel()],
                "available": True,
                "spins_remaining": spin_status.free_spins_available
            })
        
        return {
            "available_wheels": available_wheels,
            "user_stats": {
                "total_spins": spin_status.total_spins,
                "total_gems_won": spin_status.total_gems_won,
                "consecutive_days": spin_status.consecutive_days_spun,
                "luck_multiplier": spin_status.luck_multiplier,
                "free_spins": spin_status.free_spins_available
            }
        }
    
    def _calculate_winning_segment(self, segments: List[WheelSegment]) -> Tuple[WheelSegment, float]:
        """Calculate which segment the wheel lands on."""
        
        # Calculate cumulative probabilities
        total_weight = sum(s.probability for s in segments)
        cumulative_prob = 0.0
        
        # Generate random number for selection
        rand = random.random()
        
        for segment in segments:
            cumulative_prob += segment.probability / total_weight
            if rand <= cumulative_prob:
                # Calculate visual spin angle (multiple rotations + final position)
                base_rotations = random.randint(3, 6) * 360  # 3-6 full rotations
                segment_angle = 360 / len(segments) * segments.index(segment)
                final_angle = base_rotations + segment_angle + random.uniform(-15, 15)
                
                return segment, final_angle
        
        # Fallback to first segment (should never happen)
        return segments[0], 360
    
    async def spin_wheel(
        self,
        session: AsyncSession,
        user_id: str,
        wheel_type: str
    ) -> Dict[str, Any]:
        """Perform a wheel spin."""
        
        # Get user spin status
        from sqlalchemy import select
        result = await session.execute(
            select(UserSpinStatus).where(UserSpinStatus.user_id == user_id)
        )
        spin_status = result.scalar_one_or_none()
        
        if not spin_status:
            return {"status": "error", "message": "User spin status not found"}
        
        now = datetime.utcnow()
        
        # Validate spin availability
        if wheel_type == WheelType.BASIC_HOURLY.value:
            if spin_status.last_hourly_spin and (now - spin_status.last_hourly_spin) < timedelta(hours=1):
                return {"status": "error", "message": "Hourly spin not yet available"}
            segments = self._create_basic_hourly_wheel()
            spin_status.last_hourly_spin = now
            
        elif wheel_type == WheelType.PREMIUM_DAILY.value:
            if spin_status.last_daily_spin and (now - spin_status.last_daily_spin) < timedelta(days=1):
                return {"status": "error", "message": "Daily spin not yet available"}
            segments = self._create_premium_daily_wheel()
            spin_status.last_daily_spin = now
            
        elif wheel_type == WheelType.MEGA_WEEKLY.value:
            if spin_status.last_weekly_spin and (now - spin_status.last_weekly_spin) < timedelta(days=7):
                return {"status": "error", "message": "Weekly spin not yet available"}
            segments = self._create_mega_weekly_wheel()
            spin_status.last_weekly_spin = now
            
        elif wheel_type == "FREE_BONUS":
            if spin_status.free_spins_available <= 0:
                return {"status": "error", "message": "No free spins available"}
            segments = self._create_premium_daily_wheel()
            spin_status.free_spins_available -= 1
            
        else:
            return {"status": "error", "message": "Invalid wheel type"}
        
        # Calculate winning segment
        winning_segment, spin_angle = self._calculate_winning_segment(segments)
        
        # Apply luck multiplier
        multiplier = spin_status.luck_multiplier
        if spin_status.temporary_boost_expires and now < spin_status.temporary_boost_expires:
            multiplier *= 2.0  # Temporary boost is active
        
        # Calculate final reward
        base_amount = winning_segment.reward_amount
        final_amount = base_amount * multiplier
        
        # Create spin session record
        spin_session = SpinWheelSession(
            user_id=user_id,
            wheel_type=wheel_type,
            wheel_config=[s.__dict__ for s in segments],
            spin_result=winning_segment.__dict__,
            spin_angle=spin_angle,
            reward_type=winning_segment.reward_type.value,
            reward_amount=final_amount,
            multiplier_applied=multiplier
        )
        
        # Award the reward
        gems_awarded = 0.0
        xp_awarded = 0
        item_awarded = None
        special_effect = None
        
        if winning_segment.reward_type == RewardType.GEM_COINS:
            gems_awarded = final_amount
            spin_session.gem_coins_awarded = gems_awarded
            
            # Award through virtual economy
            reward_bundle = RewardBundle(
                gem_coins=gems_awarded,
                description=f"Spin Wheel ({wheel_type}): {winning_segment.label}"
            )
            await self.virtual_economy.award_reward(session, user_id, reward_bundle)
            
        elif winning_segment.reward_type == RewardType.EXPERIENCE:
            xp_awarded = int(final_amount)
            spin_session.xp_awarded = xp_awarded
            
            reward_bundle = RewardBundle(
                experience_points=xp_awarded,
                description=f"Spin Wheel ({wheel_type}): {winning_segment.label}"
            )
            await self.virtual_economy.award_reward(session, user_id, reward_bundle)
            
        elif winning_segment.reward_type == RewardType.FREE_SPINS:
            spin_status.free_spins_available += int(final_amount)
            special_effect = f"Earned {int(final_amount)} free spins!"
            
        elif winning_segment.reward_type == RewardType.MULTIPLIER_BOOST:
            # Apply temporary luck boost
            spin_status.luck_multiplier = min(3.0, spin_status.luck_multiplier + 0.2)  # Cap at 3x
            spin_status.temporary_boost_expires = now + timedelta(hours=2)
            special_effect = f"{final_amount}x multiplier boost for 2 hours!"
            
        elif winning_segment.reward_type == RewardType.COLLECTIBLE_ITEM:
            # TODO: Integrate with inventory system to award random item
            item_awarded = f"random_{winning_segment.rarity.lower()}_item"
            spin_session.item_awarded = item_awarded
            special_effect = f"Won a {winning_segment.rarity.lower()} collectible item!"
        
        # Update user statistics
        spin_status.total_spins += 1
        if gems_awarded > 0:
            spin_status.total_gems_won += gems_awarded
        
        # Update daily spin streak
        if wheel_type in [WheelType.BASIC_HOURLY.value, WheelType.PREMIUM_DAILY.value]:
            last_spin_date = spin_status.last_daily_spin.date() if spin_status.last_daily_spin else None
            today = now.date()
            yesterday = today - timedelta(days=1)
            
            if last_spin_date == yesterday:
                spin_status.consecutive_days_spun += 1
            elif last_spin_date != today:
                spin_status.consecutive_days_spun = 1
        
        session.add(spin_session)
        await session.commit()
        
        logger.info(f"Wheel spin completed - User: {user_id}, Wheel: {wheel_type}, Won: {winning_segment.label} (×{multiplier:.1f})")
        
        return {
            "status": "success",
            "spin_result": {
                "segment": winning_segment.__dict__,
                "spin_angle": spin_angle,
                "multiplier_applied": multiplier,
                "final_amount": final_amount,
                "special_effect": special_effect
            },
            "rewards": {
                "gems_awarded": gems_awarded,
                "xp_awarded": xp_awarded,
                "item_awarded": item_awarded,
                "free_spins_earned": int(final_amount) if winning_segment.reward_type == RewardType.FREE_SPINS else 0
            },
            "updated_stats": {
                "total_spins": spin_status.total_spins,
                "total_gems_won": spin_status.total_gems_won,
                "consecutive_days": spin_status.consecutive_days_spun,
                "free_spins_available": spin_status.free_spins_available,
                "luck_multiplier": spin_status.luck_multiplier
            }
        }
    
    async def add_free_spins(self, session: AsyncSession, user_id: str, amount: int, source: str):
        """Add free spins to user's account (from achievements, purchases, etc.)."""
        
        from sqlalchemy import select
        result = await session.execute(
            select(UserSpinStatus).where(UserSpinStatus.user_id == user_id)
        )
        spin_status = result.scalar_one_or_none()
        
        if not spin_status:
            spin_status = UserSpinStatus(user_id=user_id)
            session.add(spin_status)
        
        spin_status.free_spins_available += amount
        await session.commit()
        
        logger.info(f"Added {amount} free spins to user {user_id} from {source}")
    
    async def get_spin_history(self, session: AsyncSession, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's recent spin history."""
        
        from sqlalchemy import select, desc
        result = await session.execute(
            select(SpinWheelSession)
            .where(SpinWheelSession.user_id == user_id)
            .order_by(desc(SpinWheelSession.spin_time))
            .limit(limit)
        )
        
        sessions = result.scalars().all()
        
        history = []
        for session_record in sessions:
            history.append({
                "wheel_type": session_record.wheel_type,
                "result": session_record.spin_result,
                "gems_awarded": session_record.gem_coins_awarded,
                "xp_awarded": session_record.xp_awarded,
                "item_awarded": session_record.item_awarded,
                "multiplier": session_record.multiplier_applied,
                "spin_time": session_record.spin_time.isoformat()
            })
        
        return history
    
    async def get_leaderboard(self, session: AsyncSession, timeframe: str = "weekly") -> List[Dict[str, Any]]:
        """Get spin wheel leaderboard."""
        
        from sqlalchemy import select, func, desc
        from database import User
        
        # Calculate date range
        now = datetime.utcnow()
        if timeframe == "daily":
            start_date = now - timedelta(days=1)
        elif timeframe == "weekly":
            start_date = now - timedelta(days=7)
        else:  # monthly
            start_date = now - timedelta(days=30)
        
        result = await session.execute(
            select(
                SpinWheelSession.user_id,
                User.username,
                func.sum(SpinWheelSession.gem_coins_awarded).label("total_gems"),
                func.count(SpinWheelSession.id).label("total_spins")
            )
            .join(User, SpinWheelSession.user_id == User.id)
            .where(SpinWheelSession.spin_time >= start_date)
            .group_by(SpinWheelSession.user_id, User.username)
            .order_by(desc("total_gems"))
            .limit(10)
        )
        
        leaderboard = []
        for i, row in enumerate(result, 1):
            leaderboard.append({
                "rank": i,
                "username": row.username,
                "total_gems_won": row.total_gems or 0.0,
                "total_spins": row.total_spins or 0,
                "average_per_spin": (row.total_gems or 0.0) / max(1, row.total_spins or 1)
            })
        
        return leaderboard