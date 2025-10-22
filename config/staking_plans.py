"""
GEM Staking Plans Configuration

Defines available staking plans with lock periods, APR rates, and reward calculations.
"""
from datetime import datetime, timedelta
from typing import Dict, List


# ============================================================
# STAKING PLANS
# ============================================================

STAKING_PLANS = {
    "flexible": {
        "id": "flexible",
        "name": "Flexible Staking",
        "lock_period_days": 0,
        "apr_rate": 3.0,  # 3% APR
        "min_stake": 1000,
        "max_stake": None,
        "description": "Unstake anytime with no lock period",
        "badge": "Flexible",
        "color": "secondary",
        "icon": "bi-unlock",
        "popular": False,
        "best_value": False,
    },
    "short_term": {
        "id": "short_term",
        "name": "Short Term",
        "lock_period_days": 7,
        "apr_rate": 8.0,  # 8% APR
        "min_stake": 5000,
        "max_stake": None,
        "description": "7-day lock period with good returns",
        "badge": "+8% APR",
        "color": "primary",
        "icon": "bi-calendar-week",
        "popular": True,
        "best_value": False,
    },
    "medium_term": {
        "id": "medium_term",
        "name": "Medium Term",
        "lock_period_days": 30,
        "apr_rate": 12.0,  # 12% APR
        "min_stake": 10000,
        "max_stake": None,
        "description": "30-day lock period with better returns",
        "badge": "+12% APR",
        "color": "success",
        "icon": "bi-calendar-month",
        "popular": False,
        "best_value": True,
    },
    "long_term": {
        "id": "long_term",
        "name": "Long Term",
        "lock_period_days": 90,
        "apr_rate": 18.0,  # 18% APR
        "min_stake": 25000,
        "max_stake": None,
        "description": "90-day lock period with maximum returns",
        "badge": "+18% APR",
        "color": "gem",
        "icon": "bi-calendar-range",
        "popular": False,
        "best_value": False,
    },
}


# ============================================================
# STAKING LIMITS
# ============================================================

STAKING_LIMITS = {
    "max_active_stakes_per_user": 10,  # Maximum number of active stakes per user
    "absolute_min_stake": 1000,  # Absolute minimum stake amount across all plans
    "reward_calculation_interval_hours": 24,  # Calculate rewards every 24 hours
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_all_plans() -> List[Dict]:
    """Get all staking plans as a list."""
    return list(STAKING_PLANS.values())


def get_plan(plan_id: str) -> Dict:
    """Get a specific staking plan by ID."""
    return STAKING_PLANS.get(plan_id)


def validate_plan_id(plan_id: str) -> bool:
    """Check if a plan ID is valid."""
    return plan_id in STAKING_PLANS


def calculate_unlock_date(lock_period_days: int) -> datetime:
    """Calculate the unlock date based on lock period."""
    return datetime.utcnow() + timedelta(days=lock_period_days)


def calculate_daily_reward(amount: int, apr_rate: float) -> int:
    """
    Calculate daily reward for a stake.

    Formula: (amount * apr_rate / 100) / 365

    Args:
        amount: Staked GEM amount
        apr_rate: Annual Percentage Rate (e.g., 8.0 for 8%)

    Returns:
        Daily reward in GEM (rounded down)
    """
    annual_reward = (amount * apr_rate) / 100
    daily_reward = annual_reward / 365
    return int(daily_reward)  # Round down to whole GEM


def calculate_total_rewards(amount: int, apr_rate: float, days_staked: int) -> int:
    """
    Calculate total rewards for a completed stake.

    Args:
        amount: Staked GEM amount
        apr_rate: Annual Percentage Rate
        days_staked: Number of days staked

    Returns:
        Total rewards in GEM
    """
    daily_reward = calculate_daily_reward(amount, apr_rate)
    return daily_reward * days_staked


def get_plan_by_lock_period(lock_period_days: int) -> Dict:
    """Get staking plan by lock period."""
    for plan in STAKING_PLANS.values():
        if plan["lock_period_days"] == lock_period_days:
            return plan
    return None


def validate_stake_amount(plan_id: str, amount: int) -> tuple[bool, str]:
    """
    Validate if stake amount meets plan requirements.

    Returns:
        (is_valid, error_message)
    """
    plan = get_plan(plan_id)
    if not plan:
        return False, "Invalid staking plan"

    if amount < plan["min_stake"]:
        return False, f"Minimum stake for this plan is {plan['min_stake']:,} GEM"

    if plan["max_stake"] and amount > plan["max_stake"]:
        return False, f"Maximum stake for this plan is {plan['max_stake']:,} GEM"

    if amount < STAKING_LIMITS["absolute_min_stake"]:
        return False, f"Absolute minimum stake is {STAKING_LIMITS['absolute_min_stake']:,} GEM"

    return True, ""


# ============================================================
# STAKING REWARDS SUMMARY
# ============================================================

def get_rewards_summary():
    """Generate a summary of all staking plans for display."""
    summary = []

    for plan_id, plan in STAKING_PLANS.items():
        # Example rewards for 10,000 GEM
        example_amount = max(10000, plan["min_stake"])
        daily_reward = calculate_daily_reward(example_amount, plan["apr_rate"])
        total_rewards = calculate_total_rewards(
            example_amount,
            plan["apr_rate"],
            plan["lock_period_days"] if plan["lock_period_days"] > 0 else 30  # Use 30 days for flexible
        )

        summary.append({
            "plan_id": plan_id,
            "name": plan["name"],
            "lock_period_days": plan["lock_period_days"],
            "apr_rate": plan["apr_rate"],
            "min_stake": plan["min_stake"],
            "example_amount": example_amount,
            "example_daily_reward": daily_reward,
            "example_total_rewards": total_rewards,
        })

    return summary


if __name__ == "__main__":
    # Print staking plans summary
    print("=" * 60)
    print("GEM STAKING PLANS")
    print("=" * 60)

    for plan in get_all_plans():
        print(f"\n{plan['name']} ({plan['id']})")
        print(f"  Lock Period: {plan['lock_period_days']} days")
        print(f"  APR Rate: {plan['apr_rate']}%")
        print(f"  Min Stake: {plan['min_stake']:,} GEM")
        print(f"  Badge: {plan['badge']}")

        # Calculate example rewards
        example_amount = max(10000, plan['min_stake'])
        daily = calculate_daily_reward(example_amount, plan['apr_rate'])
        days = plan['lock_period_days'] if plan['lock_period_days'] > 0 else 30
        total = calculate_total_rewards(example_amount, plan['apr_rate'], days)

        print(f"  Example: {example_amount:,} GEM for {days} days")
        print(f"  Daily Reward: {daily:,} GEM")
        print(f"  Total Rewards: {total:,} GEM")

    print("\n" + "=" * 60)
