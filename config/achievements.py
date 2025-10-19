"""
Achievement definitions for CryptoChecker GEM Marketplace.

Achievements reward users for completing various milestones and goals.
Categories: roulette, trading, social, milestones
"""

# ==================== ROULETTE ACHIEVEMENTS ====================

ROULETTE_ACHIEVEMENTS = [
    {
        "id": "first_win",
        "name": "First Victory",
        "description": "Win your first roulette bet",
        "reward": 500,
        "category": "roulette",
        "trigger": "roulette_first_win",
        "target": 1,
        "icon": "bi-trophy",
        "rarity": "common"
    },
    {
        "id": "lucky_streak_3",
        "name": "Lucky Streak",
        "description": "Win 3 roulette bets in a row",
        "reward": 1000,
        "category": "roulette",
        "trigger": "roulette_win_streak",
        "target": 3,
        "icon": "bi-fire",
        "rarity": "uncommon"
    },
    {
        "id": "mega_streak_5",
        "name": "Mega Streak",
        "description": "Win 5 roulette bets in a row",
        "reward": 2500,
        "category": "roulette",
        "trigger": "roulette_win_streak",
        "target": 5,
        "icon": "bi-lightning-fill",
        "rarity": "rare"
    },
    {
        "id": "big_win_10k",
        "name": "Big Winner",
        "description": "Win 10,000 GEM in a single spin",
        "reward": 3000,
        "category": "roulette",
        "trigger": "roulette_big_win",
        "target": 10000,
        "icon": "bi-cash-stack",
        "rarity": "rare"
    },
    {
        "id": "total_wins_100",
        "name": "Seasoned Player",
        "description": "Win 100 total roulette bets",
        "reward": 5000,
        "category": "roulette",
        "trigger": "roulette_total_wins",
        "target": 100,
        "icon": "bi-award-fill",
        "rarity": "epic"
    },
    {
        "id": "roulette_master",
        "name": "Roulette Master",
        "description": "Earn 100,000 GEM from roulette",
        "reward": 10000,
        "category": "roulette",
        "trigger": "roulette_total_earnings",
        "target": 100000,
        "icon": "bi-gem",
        "rarity": "legendary"
    }
]

# ==================== TRADING ACHIEVEMENTS ====================

TRADING_ACHIEVEMENTS = [
    {
        "id": "first_trade",
        "name": "Stock Trader",
        "description": "Execute your first stock trade",
        "reward": 500,
        "category": "trading",
        "trigger": "trade_executed",
        "target": 1,
        "icon": "bi-graph-up",
        "rarity": "common"
    },
    {
        "id": "profitable_trader",
        "name": "Profitable Trader",
        "description": "Make 10,000 GEM profit from stock trading",
        "reward": 3000,
        "category": "trading",
        "trigger": "trade_profit",
        "target": 10000,
        "icon": "bi-graph-up-arrow",
        "rarity": "rare"
    },
    {
        "id": "portfolio_50k",
        "name": "Portfolio Builder",
        "description": "Build a portfolio worth 50,000 GEM",
        "reward": 5000,
        "category": "trading",
        "trigger": "portfolio_value",
        "target": 50000,
        "icon": "bi-briefcase-fill",
        "rarity": "epic"
    },
    {
        "id": "day_trader",
        "name": "Day Trader",
        "description": "Execute 50 trades",
        "reward": 4000,
        "category": "trading",
        "trigger": "total_trades",
        "target": 50,
        "icon": "bi-bar-chart-line-fill",
        "rarity": "epic"
    }
]

# ==================== SOCIAL ACHIEVEMENTS ====================

SOCIAL_ACHIEVEMENTS = [
    {
        "id": "profile_complete",
        "name": "Profile Pro",
        "description": "Complete your profile with bio and avatar",
        "reward": 250,
        "category": "social",
        "trigger": "profile_completed",
        "target": 1,
        "icon": "bi-person-check-fill",
        "rarity": "common"
    },
    {
        "id": "seven_day_streak",
        "name": "Dedicated Player",
        "description": "Log in 7 days in a row",
        "reward": 2000,
        "category": "social",
        "trigger": "login_streak",
        "target": 7,
        "icon": "bi-calendar-check-fill",
        "rarity": "uncommon"
    },
    {
        "id": "thirty_day_streak",
        "name": "Loyal Member",
        "description": "Log in 30 days in a row",
        "reward": 10000,
        "category": "social",
        "trigger": "login_streak",
        "target": 30,
        "icon": "bi-heart-fill",
        "rarity": "legendary"
    }
]

# ==================== MILESTONE ACHIEVEMENTS ====================

MILESTONE_ACHIEVEMENTS = [
    {
        "id": "gem_collector_10k",
        "name": "GEM Collector",
        "description": "Accumulate 10,000 total GEM",
        "reward": 1000,
        "category": "milestones",
        "trigger": "total_gems_earned",
        "target": 10000,
        "icon": "bi-coin",
        "rarity": "uncommon"
    },
    {
        "id": "gem_hoarder_50k",
        "name": "GEM Hoarder",
        "description": "Accumulate 50,000 total GEM",
        "reward": 5000,
        "category": "milestones",
        "trigger": "total_gems_earned",
        "target": 50000,
        "icon": "bi-safe-fill",
        "rarity": "rare"
    },
    {
        "id": "gem_tycoon_100k",
        "name": "GEM Tycoon",
        "description": "Accumulate 100,000 total GEM",
        "reward": 15000,
        "category": "milestones",
        "trigger": "total_gems_earned",
        "target": 100000,
        "icon": "bi-bank",
        "rarity": "epic"
    },
    {
        "id": "account_anniversary",
        "name": "One Year Strong",
        "description": "Celebrate 1 year with CryptoChecker",
        "reward": 20000,
        "category": "milestones",
        "trigger": "account_age_days",
        "target": 365,
        "icon": "bi-cake2-fill",
        "rarity": "legendary"
    }
]

# ==================== ALL ACHIEVEMENTS ====================

ALL_ACHIEVEMENTS = (
    ROULETTE_ACHIEVEMENTS +
    TRADING_ACHIEVEMENTS +
    SOCIAL_ACHIEVEMENTS +
    MILESTONE_ACHIEVEMENTS
)

# Create achievement lookup by ID
ACHIEVEMENTS_BY_ID = {a["id"]: a for a in ALL_ACHIEVEMENTS}

# Create achievement lookup by trigger
ACHIEVEMENTS_BY_TRIGGER = {}
for achievement in ALL_ACHIEVEMENTS:
    trigger = achievement["trigger"]
    if trigger not in ACHIEVEMENTS_BY_TRIGGER:
        ACHIEVEMENTS_BY_TRIGGER[trigger] = []
    ACHIEVEMENTS_BY_TRIGGER[trigger].append(achievement)

# ==================== STATS ====================

ACHIEVEMENT_STATS = {
    "total_achievements": len(ALL_ACHIEVEMENTS),
    "by_category": {
        "roulette": len(ROULETTE_ACHIEVEMENTS),
        "trading": len(TRADING_ACHIEVEMENTS),
        "social": len(SOCIAL_ACHIEVEMENTS),
        "milestones": len(MILESTONE_ACHIEVEMENTS)
    },
    "by_rarity": {
        "common": len([a for a in ALL_ACHIEVEMENTS if a["rarity"] == "common"]),
        "uncommon": len([a for a in ALL_ACHIEVEMENTS if a["rarity"] == "uncommon"]),
        "rare": len([a for a in ALL_ACHIEVEMENTS if a["rarity"] == "rare"]),
        "epic": len([a for a in ALL_ACHIEVEMENTS if a["rarity"] == "epic"]),
        "legendary": len([a for a in ALL_ACHIEVEMENTS if a["rarity"] == "legendary"])
    },
    "total_rewards": sum(a["reward"] for a in ALL_ACHIEVEMENTS)
}


def get_achievements_for_trigger(trigger_name: str):
    """Get all achievements that use a specific trigger."""
    return ACHIEVEMENTS_BY_TRIGGER.get(trigger_name, [])


def get_achievement(achievement_id: str):
    """Get a specific achievement by ID."""
    return ACHIEVEMENTS_BY_ID.get(achievement_id)


def get_achievements_by_category(category: str):
    """Get all achievements in a specific category."""
    return [a for a in ALL_ACHIEVEMENTS if a["category"] == category]
