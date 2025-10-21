"""
Configuration for Clicker Phase 2 Features
- Power-ups with costs, durations, cooldowns
- Daily and weekly challenges
- Prestige shop items
- Theme unlock requirements
"""

# ============================================================================
# POWER-UP CONFIGURATIONS
# ============================================================================

POWERUP_CONFIGS = {
    'double_rewards': {
        'name': 'Double Rewards',
        'description': 'All click rewards doubled for 60 seconds',
        'cost': 10000,
        'duration': 60,  # seconds
        'cooldown': 300,  # 5 minutes
        'multiplier': 2.0,
        'icon': 'gem',
        'color': '#fbbf24',  # Golden
    },
    'energy_refill': {
        'name': 'Energy Refill',
        'description': 'Instantly restore energy to 100%',
        'cost': 5000,
        'duration': 0,  # Instant effect
        'cooldown': 180,  # 3 minutes
        'icon': 'lightning-charge-fill',
        'color': '#3b82f6',  # Blue
    },
    'auto_burst': {
        'name': 'Auto-Click Burst',
        'description': 'Auto-clicker rate 5x faster for 30 seconds',
        'cost': 15000,
        'duration': 30,
        'cooldown': 600,  # 10 minutes
        'multiplier': 5.0,
        'icon': 'robot',
        'color': '#10b981',  # Green
    },
    'lucky_streak': {
        'name': 'Lucky Streak',
        'description': 'Increase bonus chance to 50% for 45 seconds',
        'cost': 8000,
        'duration': 45,
        'cooldown': 480,  # 8 minutes
        'bonus_chance_boost': 0.35,  # Adds 35% to base 15%
        'icon': 'star-fill',
        'color': '#8b5cf6',  # Purple
    },
    'mega_combo': {
        'name': 'Mega Combo',
        'description': 'Instantly activate 10x combo',
        'cost': 12000,
        'duration': 0,  # Instant effect
        'cooldown': 900,  # 15 minutes
        'combo_boost': 10,
        'icon': 'fire',
        'color': '#ef4444',  # Red
    },
}

# ============================================================================
# DAILY CHALLENGE CONFIGURATIONS
# ============================================================================

DAILY_CHALLENGES = {
    'click_master': {
        'name': 'Click Master',
        'description': 'Click 500 times',
        'type': 'total_clicks',
        'target': 500,
        'reward_gems': 5000,
        'reward_pp': 0,
        'icon': 'mouse-fill',
    },
    'combo_king': {
        'name': 'Combo King',
        'description': 'Achieve a 15x combo',
        'type': 'best_combo',
        'target': 15,
        'reward_gems': 10000,
        'reward_pp': 0,
        'icon': 'trophy-fill',
    },
    'energy_efficient': {
        'name': 'Energy Efficient',
        'description': 'Earn 50,000 GEM without depleting energy',
        'type': 'gems_no_deplete',
        'target': 50000,
        'reward_gems': 8000,
        'reward_pp': 0,
        'icon': 'battery-charging',
    },
    'speed_clicker': {
        'name': 'Speed Clicker',
        'description': 'Click 100 times in 60 seconds',
        'type': 'clicks_per_minute',
        'target': 100,
        'reward_gems': 12000,
        'reward_pp': 0,
        'icon': 'lightning-fill',
    },
    'big_earner': {
        'name': 'Big Earner',
        'description': 'Earn 100,000 GEM in one session',
        'type': 'session_gems',
        'target': 100000,
        'reward_gems': 15000,
        'reward_pp': 0,
        'icon': 'cash-stack',
    },
}

# ============================================================================
# WEEKLY CHALLENGE CONFIGURATIONS
# ============================================================================

WEEKLY_CHALLENGES = {
    'dedication': {
        'name': 'Dedication',
        'description': 'Click 5,000 times this week',
        'type': 'weekly_clicks',
        'target': 5000,
        'reward_gems': 50000,
        'reward_pp': 1,
        'icon': 'calendar-week',
    },
    'idle_master': {
        'name': 'Idle Master',
        'description': 'Accumulate 500,000 GEM from auto-clicker',
        'type': 'auto_clicker_gems',
        'target': 500000,
        'reward_gems': 100000,
        'reward_pp': 1,
        'icon': 'clock-fill',
    },
    'prestige_ready': {
        'name': 'Prestige Ready',
        'description': 'Earn 1,000,000 total GEM',
        'type': 'total_gems_earned',
        'target': 1000000,
        'reward_gems': 0,
        'reward_pp': 3,
        'icon': 'star',
    },
    'upgrade_collector': {
        'name': 'Upgrade Collector',
        'description': 'Purchase 10 upgrades',
        'type': 'upgrades_purchased',
        'target': 10,
        'reward_gems': 75000,
        'reward_pp': 2,
        'icon': 'shop',
    },
}

# ============================================================================
# PRESTIGE SHOP CONFIGURATIONS
# ============================================================================

PRESTIGE_SHOP_ITEMS = {
    'click_master': {
        'name': 'Click Master',
        'description': 'Start with Click Power Level 2 after prestige',
        'cost_pp': 1,
        'icon': 'cursor-fill',
        'permanent': True,
    },
    'energy_expert': {
        'name': 'Energy Expert',
        'description': 'Start with 120 max energy after prestige',
        'cost_pp': 2,
        'icon': 'battery-charging',
        'permanent': True,
    },
    'quick_start': {
        'name': 'Quick Start',
        'description': 'Start with 5,000 GEM after prestige',
        'cost_pp': 3,
        'icon': 'cash-coin',
        'permanent': True,
    },
    'auto_unlock': {
        'name': 'Auto Unlock',
        'description': 'Start with Bronze Auto-Clicker unlocked',
        'cost_pp': 5,
        'icon': 'robot',
        'permanent': True,
    },
    'multiplier_boost': {
        'name': 'Multiplier Boost',
        'description': 'All multipliers +10% (permanent)',
        'cost_pp': 10,
        'icon': 'graph-up-arrow',
        'permanent': True,
    },
    'prestige_master': {
        'name': 'Prestige Master',
        'description': 'Earn 50% more PP on next prestige',
        'cost_pp': 20,
        'icon': 'star-fill',
        'permanent': False,  # Consumed on next prestige
    },
}

# ============================================================================
# PRESTIGE FORMULA
# ============================================================================

# Minimum GEM required to prestige
PRESTIGE_MINIMUM_GEMS = 100000  # Need 100k GEM minimum to prestige

def calculate_prestige_points(total_gems_earned: float) -> int:
    """
    Calculate prestige points based on total GEM earned.
    Formula: PP = floor(sqrt(total_gems_earned / 100000))

    Examples:
    - 100,000 GEM = 1 PP
    - 1,000,000 GEM = 3 PP
    - 10,000,000 GEM = 10 PP
    """
    import math
    return math.floor(math.sqrt(total_gems_earned / 100000))


def calculate_prestige_bonuses(prestige_points: int) -> dict:
    """
    Calculate permanent bonuses from prestige points.
    Each PP provides:
    - +5% base click rewards (multiplicative)
    - +3% energy regeneration (multiplicative)
    - +2% rare bonus chance (multiplicative)

    Returns multipliers (1.0 = no bonus, 1.5 = 50% bonus)
    """
    return {
        'click_multiplier': 1.0 + (prestige_points * 0.05),  # +5% per PP
        'energy_regen_multiplier': 1.0 + (prestige_points * 0.03),  # +3% per PP
        'bonus_chance_multiplier': 1.0 + (prestige_points * 0.02),  # +2% per PP
    }

# ============================================================================
# THEME UNLOCK REQUIREMENTS
# ============================================================================

BUTTON_THEMES = {
    # Free themes (always unlocked)
    'classic_blue': {'name': 'Classic Blue', 'unlocked_by': 'default', 'gradient': ['#22d3ee', '#3b82f6', '#8b5cf6']},
    'green_machine': {'name': 'Green Machine', 'unlocked_by': 'default', 'gradient': ['#10b981', '#059669', '#047857']},
    'purple_power': {'name': 'Purple Power', 'unlocked_by': 'default', 'gradient': ['#8b5cf6', '#7c3aed', '#6d28d9']},

    # Unlock requirements
    'golden_glory': {'name': 'Golden Glory', 'unlocked_by': 'total_clicks', 'requirement': 100000, 'gradient': ['#fbbf24', '#f59e0b', '#d97706']},
    'ruby_red': {'name': 'Ruby Red', 'unlocked_by': 'total_gems_earned', 'requirement': 1000000, 'gradient': ['#ef4444', '#dc2626', '#b91c1c']},
    'diamond_shine': {'name': 'Diamond Shine', 'unlocked_by': 'prestige_level', 'requirement': 5, 'gradient': ['#e5e7eb', '#d1d5db', '#9ca3af']},
    'rainbow_burst': {'name': 'Rainbow Burst', 'unlocked_by': 'prestige_level', 'requirement': 10, 'gradient': 'rainbow'},  # Animated
    'dark_matter': {'name': 'Dark Matter', 'unlocked_by': 'prestige_level', 'requirement': 20, 'gradient': ['#1f2937', '#111827', '#030712']},
}

PARTICLE_EFFECTS = {
    # Free effects
    'gem_burst': {'name': 'Gem Burst', 'unlocked_by': 'default', 'particles': ['💎']},
    'stars': {'name': 'Stars', 'unlocked_by': 'default', 'particles': ['⭐', '✨']},

    # Unlock requirements
    'fireworks': {'name': 'Fireworks', 'unlocked_by': 'total_clicks', 'requirement': 500000, 'particles': ['💥', '🎆', '✨']},
    'hearts': {'name': 'Hearts', 'unlocked_by': 'prestige_points', 'requirement': 100, 'particles': ['💖', '💕', '💗']},
    'lightning': {'name': 'Lightning', 'unlocked_by': 'prestige_level', 'requirement': 15, 'particles': ['⚡', '🔥']},
    'galaxy': {'name': 'Galaxy', 'unlocked_by': 'prestige_level', 'requirement': 25, 'particles': ['🌟', '🌠', '✨']},
}

BACKGROUND_THEMES = {
    # Free backgrounds
    'gradient_purple': {'name': 'Gradient Purple', 'unlocked_by': 'default', 'colors': ['#6366f1', '#8b5cf6']},
    'blue_ocean': {'name': 'Blue Ocean', 'unlocked_by': 'default', 'colors': ['#0ea5e9', '#06b6d4']},
    'green_forest': {'name': 'Green Forest', 'unlocked_by': 'default', 'colors': ['#10b981', '#059669']},

    # Unlock requirements
    'starry_night': {'name': 'Starry Night', 'unlocked_by': 'total_gems_earned', 'requirement': 1000000, 'colors': ['#1e293b', '#0f172a']},
    'sunset': {'name': 'Sunset', 'unlocked_by': 'prestige_level', 'requirement': 3, 'colors': ['#f97316', '#ea580c']},
    'aurora': {'name': 'Aurora', 'unlocked_by': 'prestige_level', 'requirement': 10, 'colors': ['#8b5cf6', '#06b6d4', '#10b981']},
    'void': {'name': 'Void', 'unlocked_by': 'prestige_level', 'requirement': 20, 'colors': ['#030712', '#111827']},
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_available_powerups() -> dict:
    """Get all power-up configurations."""
    return POWERUP_CONFIGS


def get_daily_challenges_pool() -> dict:
    """Get pool of daily challenges."""
    return DAILY_CHALLENGES


def get_weekly_challenges_pool() -> dict:
    """Get pool of weekly challenges."""
    return WEEKLY_CHALLENGES


def get_prestige_shop_items() -> dict:
    """Get all prestige shop items."""
    return PRESTIGE_SHOP_ITEMS


def check_theme_unlock(theme_type: str, theme_id: str, user_stats: dict) -> bool:
    """
    Check if a theme is unlocked for a user.

    Args:
        theme_type: 'button', 'particle', or 'background'
        theme_id: The theme identifier
        user_stats: Dictionary with user stats (total_clicks, total_gems_earned, prestige_level, etc.)

    Returns:
        True if unlocked, False otherwise
    """
    theme_configs = {
        'button': BUTTON_THEMES,
        'particle': PARTICLE_EFFECTS,
        'background': BACKGROUND_THEMES,
    }

    if theme_type not in theme_configs:
        return False

    theme = theme_configs[theme_type].get(theme_id)
    if not theme:
        return False

    # Default themes are always unlocked
    if theme['unlocked_by'] == 'default':
        return True

    # Check specific requirement
    unlock_type = theme['unlocked_by']
    requirement = theme.get('requirement', 0)

    if unlock_type == 'total_clicks':
        return user_stats.get('total_clicks', 0) >= requirement
    elif unlock_type == 'total_gems_earned':
        return user_stats.get('total_gems_earned', 0) >= requirement
    elif unlock_type == 'prestige_level':
        return user_stats.get('prestige_level', 0) >= requirement
    elif unlock_type == 'prestige_points':
        return user_stats.get('total_prestige_points', 0) >= requirement

    return False
