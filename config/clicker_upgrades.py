"""
Clicker Upgrade Configuration System
Defines all upgradeable aspects of the clicker game with costs, benefits, and progression.
"""

# ==================== CLICK POWER UPGRADES ====================
CLICK_POWER_UPGRADES = {
    1: {
        "name": "Basic Click",
        "description": "Standard clicking power",
        "min_reward": 10,
        "max_reward": 100,
        "cost": 0,  # Starting level
        "icon": "bi-hand-index"
    },
    2: {
        "name": "Better Click",
        "description": "+50% click power",
        "min_reward": 15,
        "max_reward": 150,
        "cost": 500,
        "icon": "bi-hand-index-thumb"
    },
    3: {
        "name": "Power Click",
        "description": "+100% click power",
        "min_reward": 25,
        "max_reward": 250,
        "cost": 2500,
        "icon": "bi-lightning-charge"
    },
    4: {
        "name": "Mega Click",
        "description": "+200% click power",
        "min_reward": 50,
        "max_reward": 500,
        "cost": 10000,
        "icon": "bi-lightning-charge-fill"
    },
    5: {
        "name": "Ultimate Click",
        "description": "+400% click power",
        "min_reward": 100,
        "max_reward": 1000,
        "cost": 50000,
        "icon": "bi-stars"
    },
    6: {
        "name": "Divine Click",
        "description": "+800% click power",
        "min_reward": 200,
        "max_reward": 2000,
        "cost": 250000,
        "icon": "bi-star-fill"
    }
}

# ==================== AUTO-CLICKER UPGRADES ====================
AUTO_CLICKER_UPGRADES = {
    0: {
        "name": "No Auto-Clicker",
        "description": "Manual clicking only",
        "gems_per_tick": 0,
        "interval_seconds": 0,
        "cost": 0,
        "icon": "bi-x-circle"
    },
    1: {
        "name": "Bronze Auto-Clicker",
        "description": "Passive +10 GEM every 10 seconds",
        "gems_per_tick": 10,
        "interval_seconds": 10,
        "cost": 5000,
        "icon": "bi-robot"
    },
    2: {
        "name": "Silver Auto-Clicker",
        "description": "Passive +25 GEM every 10 seconds",
        "gems_per_tick": 25,
        "interval_seconds": 10,
        "cost": 25000,
        "icon": "bi-cpu"
    },
    3: {
        "name": "Gold Auto-Clicker",
        "description": "Passive +50 GEM every 8 seconds",
        "gems_per_tick": 50,
        "interval_seconds": 8,
        "cost": 100000,
        "icon": "bi-gear-fill"
    },
    4: {
        "name": "Diamond Auto-Clicker",
        "description": "Passive +100 GEM every 6 seconds",
        "gems_per_tick": 100,
        "interval_seconds": 6,
        "cost": 500000,
        "icon": "bi-gem"
    },
    5: {
        "name": "Cosmic Auto-Clicker",
        "description": "Passive +200 GEM every 5 seconds",
        "gems_per_tick": 200,
        "interval_seconds": 5,
        "cost": 2500000,
        "icon": "bi-stars"
    }
}

# ==================== MULTIPLIER UPGRADES ====================
MULTIPLIER_UPGRADES = {
    0: {
        "name": "No Multiplier",
        "description": "Standard rewards",
        "multiplier": 1.0,
        "cost": 0,
        "icon": "bi-x-circle"
    },
    1: {
        "name": "Lucky Charm",
        "description": "1.5x all rewards",
        "multiplier": 1.5,
        "cost": 10000,
        "icon": "bi-star"
    },
    2: {
        "name": "Fortune Amulet",
        "description": "2x all rewards",
        "multiplier": 2.0,
        "cost": 50000,
        "icon": "bi-star-fill"
    },
    3: {
        "name": "Divine Blessing",
        "description": "3x all rewards",
        "multiplier": 3.0,
        "cost": 250000,
        "icon": "bi-brightness-high-fill"
    },
    4: {
        "name": "Cosmic Power",
        "description": "5x all rewards",
        "multiplier": 5.0,
        "cost": 1000000,
        "icon": "bi-sun-fill"
    }
}

# ==================== ENERGY CAPACITY UPGRADES ====================
ENERGY_CAPACITY_UPGRADES = {
    0: {
        "name": "Standard Energy",
        "description": "100 max energy",
        "max_energy": 100,
        "cost": 0,
        "icon": "bi-battery"
    },
    1: {
        "name": "Enhanced Battery",
        "description": "150 max energy",
        "max_energy": 150,
        "cost": 7500,
        "icon": "bi-battery-half"
    },
    2: {
        "name": "Power Cell",
        "description": "200 max energy",
        "max_energy": 200,
        "cost": 30000,
        "icon": "bi-battery-full"
    },
    3: {
        "name": "Energy Core",
        "description": "300 max energy",
        "max_energy": 300,
        "cost": 100000,
        "icon": "bi-battery-charging"
    },
    4: {
        "name": "Fusion Reactor",
        "description": "500 max energy",
        "max_energy": 500,
        "cost": 500000,
        "icon": "bi-lightning-fill"
    }
}

# ==================== ENERGY REGENERATION UPGRADES ====================
ENERGY_REGEN_UPGRADES = {
    0: {
        "name": "Standard Regen",
        "description": "1 energy per minute",
        "energy_per_minute": 1.0,
        "cost": 0,
        "icon": "bi-arrow-repeat"
    },
    1: {
        "name": "Fast Regen",
        "description": "2 energy per minute",
        "energy_per_minute": 2.0,
        "cost": 5000,
        "icon": "bi-arrow-clockwise"
    },
    2: {
        "name": "Rapid Regen",
        "description": "3 energy per minute",
        "energy_per_minute": 3.0,
        "cost": 20000,
        "icon": "bi-arrow-repeat"
    },
    3: {
        "name": "Super Regen",
        "description": "5 energy per minute",
        "energy_per_minute": 5.0,
        "cost": 75000,
        "icon": "bi-lightning"
    },
    4: {
        "name": "Ultra Regen",
        "description": "10 energy per minute",
        "energy_per_minute": 10.0,
        "cost": 300000,
        "icon": "bi-lightning-fill"
    }
}

# ==================== UPGRADE CATEGORIES ====================
UPGRADE_CATEGORIES = {
    "click_power": {
        "name": "Click Power",
        "description": "Increase gems earned per click",
        "upgrades": CLICK_POWER_UPGRADES,
        "max_level": 6,
        "icon": "bi-hand-index-thumb-fill",
        "color": "#3b82f6"
    },
    "auto_clicker": {
        "name": "Auto-Clicker",
        "description": "Earn passive gems automatically",
        "upgrades": AUTO_CLICKER_UPGRADES,
        "max_level": 5,
        "icon": "bi-robot",
        "color": "#10b981"
    },
    "multiplier": {
        "name": "Multiplier",
        "description": "Multiply all gem rewards",
        "upgrades": MULTIPLIER_UPGRADES,
        "max_level": 4,
        "icon": "bi-stars",
        "color": "#fbbf24"
    },
    "energy_capacity": {
        "name": "Energy Capacity",
        "description": "Increase maximum energy",
        "upgrades": ENERGY_CAPACITY_UPGRADES,
        "max_level": 4,
        "icon": "bi-battery-full",
        "color": "#8b5cf6"
    },
    "energy_regen": {
        "name": "Energy Regen",
        "description": "Faster energy regeneration",
        "upgrades": ENERGY_REGEN_UPGRADES,
        "max_level": 4,
        "icon": "bi-lightning-charge-fill",
        "color": "#ef4444"
    }
}

# ==================== BONUS MECHANICS ====================
BONUS_CHANCES = {
    "mega": {
        "base_chance": 0.01,  # 1%
        "reward": 100,
        "name": "MEGA Bonus",
        "color": "#fbbf24"
    },
    "big": {
        "base_chance": 0.04,  # 4%
        "reward": 50,
        "name": "Big Bonus",
        "color": "#8b5cf6"
    },
    "medium": {
        "base_chance": 0.10,  # 10%
        "reward": 25,
        "name": "Medium Bonus",
        "color": "#3b82f6"
    }
}

# ==================== COMBO SYSTEM ====================
COMBO_THRESHOLDS = {
    3: {"multiplier": 1.5, "name": "Nice!", "color": "#10b981"},
    5: {"multiplier": 2.0, "name": "Great!", "color": "#3b82f6"},
    10: {"multiplier": 3.0, "name": "AMAZING!", "color": "#8b5cf6"},
    15: {"multiplier": 4.0, "name": "INCREDIBLE!", "color": "#ef4444"},
    20: {"multiplier": 5.0, "name": "LEGENDARY!", "color": "#fbbf24"}
}

COMBO_WINDOW_SECONDS = 2  # Time window to maintain combo

# ==================== DAILY MISSIONS (CLICKER-SPECIFIC) ====================
CLICKER_DAILY_MISSIONS = [
    {
        "id": "daily_clicks_100",
        "name": "Click Master",
        "description": "Click 100 times",
        "target": 100,
        "reward": 500,
        "icon": "bi-mouse-fill",
        "type": "clicks"
    },
    {
        "id": "daily_gems_10k",
        "name": "Gem Farmer",
        "description": "Earn 10,000 GEM from clicking",
        "target": 10000,
        "reward": 1000,
        "icon": "bi-gem",
        "type": "gems_earned"
    },
    {
        "id": "daily_combo_50",
        "name": "Combo King",
        "description": "Achieve a 50-click combo",
        "target": 50,
        "reward": 1500,
        "icon": "bi-fire",
        "type": "combo"
    },
    {
        "id": "daily_mega_bonus_3",
        "name": "Lucky Strike",
        "description": "Hit 3 MEGA bonuses",
        "target": 3,
        "reward": 2500,
        "icon": "bi-star-fill",
        "type": "mega_bonuses"
    }
]

# ==================== HELPER FUNCTIONS ====================

def get_click_reward_range(level: int) -> tuple[int, int]:
    """Get min/max reward for a click power level."""
    if level in CLICK_POWER_UPGRADES:
        return (CLICK_POWER_UPGRADES[level]["min_reward"],
                CLICK_POWER_UPGRADES[level]["max_reward"])
    return (10, 100)  # Default

def get_auto_click_info(level: int) -> dict:
    """Get auto-clicker information for a level."""
    if level in AUTO_CLICKER_UPGRADES:
        return AUTO_CLICKER_UPGRADES[level]
    return AUTO_CLICKER_UPGRADES[0]

def get_multiplier(level: int) -> float:
    """Get multiplier for a level."""
    if level in MULTIPLIER_UPGRADES:
        return MULTIPLIER_UPGRADES[level]["multiplier"]
    return 1.0

def get_max_energy(level: int) -> int:
    """Get max energy for a level."""
    if level in ENERGY_CAPACITY_UPGRADES:
        return ENERGY_CAPACITY_UPGRADES[level]["max_energy"]
    return 100

def get_energy_regen_rate(level: int) -> float:
    """Get energy regeneration rate per minute."""
    if level in ENERGY_REGEN_UPGRADES:
        return ENERGY_REGEN_UPGRADES[level]["energy_per_minute"]
    return 1.0

def get_upgrade_cost(category: str, current_level: int) -> int:
    """Get cost to upgrade to next level."""
    next_level = current_level + 1
    if category in UPGRADE_CATEGORIES:
        upgrades = UPGRADE_CATEGORIES[category]["upgrades"]
        if next_level in upgrades:
            return upgrades[next_level]["cost"]
    return None  # Max level reached

def can_afford_upgrade(category: str, current_level: int, user_balance: float) -> bool:
    """Check if user can afford the next upgrade."""
    cost = get_upgrade_cost(category, current_level)
    if cost is None:
        return False  # Max level
    return user_balance >= cost

def get_combo_multiplier(combo_count: int) -> tuple[float, str]:
    """Get multiplier and name for a combo count."""
    multiplier = 1.0
    name = ""

    for threshold in sorted(COMBO_THRESHOLDS.keys(), reverse=True):
        if combo_count >= threshold:
            multiplier = COMBO_THRESHOLDS[threshold]["multiplier"]
            name = COMBO_THRESHOLDS[threshold]["name"]
            break

    return (multiplier, name)
