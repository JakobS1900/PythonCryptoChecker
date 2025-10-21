"""
GEM Clicker Phase 3A: Achievement Definitions
All achievement configurations, requirements, and rewards
"""

# Achievement structure:
# {
#     "id": unique_key,
#     "name": display_name,
#     "description": description,
#     "category": category,
#     "icon": bootstrap_icon,
#     "requirement_type": stat_to_check,
#     "requirement_value": threshold,
#     "reward_gems": gem_reward,
#     "achievement_points": points (1-10),
#     "rarity": common/rare/epic/legendary
# }

ACHIEVEMENTS = {
    # ==========================================
    # CLICK ACHIEVEMENTS (5)
    # ==========================================
    "click_first": {
        "id": "click_first",
        "name": "First Click",
        "description": "Make your first click",
        "category": "clicks",
        "icon": "bi-mouse",
        "requirement_type": "total_clicks",
        "requirement_value": 1,
        "reward_gems": 100,
        "achievement_points": 1,
        "rarity": "common"
    },
    "click_novice": {
        "id": "click_novice",
        "name": "Click Novice",
        "description": "Reach 100 total clicks",
        "category": "clicks",
        "icon": "bi-mouse-fill",
        "requirement_type": "total_clicks",
        "requirement_value": 100,
        "reward_gems": 500,
        "achievement_points": 2,
        "rarity": "common"
    },
    "click_expert": {
        "id": "click_expert",
        "name": "Click Expert",
        "description": "Reach 1,000 total clicks",
        "category": "clicks",
        "icon": "bi-hand-index-thumb",
        "requirement_type": "total_clicks",
        "requirement_value": 1000,
        "reward_gems": 2500,
        "achievement_points": 3,
        "rarity": "rare"
    },
    "click_master": {
        "id": "click_master",
        "name": "Click Master",
        "description": "Reach 10,000 total clicks",
        "category": "clicks",
        "icon": "bi-hand-index-thumb-fill",
        "requirement_type": "total_clicks",
        "requirement_value": 10000,
        "reward_gems": 10000,
        "achievement_points": 5,
        "rarity": "epic"
    },
    "click_legend": {
        "id": "click_legend",
        "name": "Click Legend",
        "description": "Reach 100,000 total clicks",
        "category": "clicks",
        "icon": "bi-trophy-fill",
        "requirement_type": "total_clicks",
        "requirement_value": 100000,
        "reward_gems": 50000,
        "achievement_points": 10,
        "rarity": "legendary"
    },

    # ==========================================
    # EARNING ACHIEVEMENTS (5)
    # ==========================================
    "gems_first": {
        "id": "gems_first",
        "name": "First Gems",
        "description": "Earn 100 GEM",
        "category": "earning",
        "icon": "bi-gem",
        "requirement_type": "total_gems_earned",
        "requirement_value": 100,
        "reward_gems": 200,
        "achievement_points": 1,
        "rarity": "common"
    },
    "gems_collector": {
        "id": "gems_collector",
        "name": "Gem Collector",
        "description": "Earn 10,000 GEM",
        "category": "earning",
        "icon": "bi-cash-stack",
        "requirement_type": "total_gems_earned",
        "requirement_value": 10000,
        "reward_gems": 5000,
        "achievement_points": 2,
        "rarity": "common"
    },
    "gems_hoarder": {
        "id": "gems_hoarder",
        "name": "Gem Hoarder",
        "description": "Earn 100,000 GEM",
        "category": "earning",
        "icon": "bi-safe-fill",
        "requirement_type": "total_gems_earned",
        "requirement_value": 100000,
        "reward_gems": 25000,
        "achievement_points": 3,
        "rarity": "rare"
    },
    "gems_tycoon": {
        "id": "gems_tycoon",
        "name": "Gem Tycoon",
        "description": "Earn 1,000,000 GEM",
        "category": "earning",
        "icon": "bi-bank",
        "requirement_type": "total_gems_earned",
        "requirement_value": 1000000,
        "reward_gems": 100000,
        "achievement_points": 5,
        "rarity": "epic"
    },
    "gems_emperor": {
        "id": "gems_emperor",
        "name": "Gem Emperor",
        "description": "Earn 10,000,000 GEM",
        "category": "earning",
        "icon": "bi-award-fill",
        "requirement_type": "total_gems_earned",
        "requirement_value": 10000000,
        "reward_gems": 500000,
        "achievement_points": 10,
        "rarity": "legendary"
    },

    # ==========================================
    # COMBO ACHIEVEMENTS (4)
    # ==========================================
    "combo_starter": {
        "id": "combo_starter",
        "name": "Combo Starter",
        "description": "Achieve a 3x combo",
        "category": "combos",
        "icon": "bi-lightning",
        "requirement_type": "best_combo",
        "requirement_value": 3,
        "reward_gems": 500,
        "achievement_points": 2,
        "rarity": "common"
    },
    "combo_pro": {
        "id": "combo_pro",
        "name": "Combo Pro",
        "description": "Achieve a 10x combo",
        "category": "combos",
        "icon": "bi-lightning-charge",
        "requirement_type": "best_combo",
        "requirement_value": 10,
        "reward_gems": 2000,
        "achievement_points": 3,
        "rarity": "rare"
    },
    "combo_king": {
        "id": "combo_king",
        "name": "Combo King",
        "description": "Achieve a 25x combo",
        "category": "combos",
        "icon": "bi-lightning-charge-fill",
        "requirement_type": "best_combo",
        "requirement_value": 25,
        "reward_gems": 10000,
        "achievement_points": 5,
        "rarity": "epic"
    },
    "combo_god": {
        "id": "combo_god",
        "name": "Combo God",
        "description": "Achieve a 50x combo",
        "category": "combos",
        "icon": "bi-stars",
        "requirement_type": "best_combo",
        "requirement_value": 50,
        "reward_gems": 50000,
        "achievement_points": 10,
        "rarity": "legendary"
    },

    # ==========================================
    # PRESTIGE ACHIEVEMENTS (4)
    # ==========================================
    "prestige_first": {
        "id": "prestige_first",
        "name": "First Prestige",
        "description": "Prestige for the first time",
        "category": "prestige",
        "icon": "bi-arrow-repeat",
        "requirement_type": "prestige_level",
        "requirement_value": 1,
        "reward_gems": 5000,
        "achievement_points": 3,
        "rarity": "rare"
    },
    "prestige_veteran": {
        "id": "prestige_veteran",
        "name": "Prestige Veteran",
        "description": "Prestige 5 times",
        "category": "prestige",
        "icon": "bi-arrow-clockwise",
        "requirement_type": "prestige_level",
        "requirement_value": 5,
        "reward_gems": 25000,
        "achievement_points": 5,
        "rarity": "epic"
    },
    "prestige_master": {
        "id": "prestige_master",
        "name": "Prestige Master",
        "description": "Prestige 15 times",
        "category": "prestige",
        "icon": "bi-arrow-counterclockwise",
        "requirement_type": "prestige_level",
        "requirement_value": 15,
        "reward_gems": 100000,
        "achievement_points": 8,
        "rarity": "epic"
    },
    "prestige_legend": {
        "id": "prestige_legend",
        "name": "Prestige Legend",
        "description": "Prestige 50 times",
        "category": "prestige",
        "icon": "bi-infinity",
        "requirement_type": "prestige_level",
        "requirement_value": 50,
        "reward_gems": 500000,
        "achievement_points": 10,
        "rarity": "legendary"
    },

    # ==========================================
    # MEGA BONUS ACHIEVEMENTS (3)
    # ==========================================
    "mega_lucky": {
        "id": "mega_lucky",
        "name": "Mega Lucky",
        "description": "Hit 100 mega bonuses",
        "category": "special",
        "icon": "bi-star-fill",
        "requirement_type": "mega_bonuses_hit",
        "requirement_value": 100,
        "reward_gems": 50000,
        "achievement_points": 5,
        "rarity": "epic"
    },
    "mega_master": {
        "id": "mega_master",
        "name": "Mega Master",
        "description": "Hit 500 mega bonuses",
        "category": "special",
        "icon": "bi-stars",
        "requirement_type": "mega_bonuses_hit",
        "requirement_value": 500,
        "reward_gems": 150000,
        "achievement_points": 8,
        "rarity": "epic"
    },
    "mega_god": {
        "id": "mega_god",
        "name": "Mega God",
        "description": "Hit 1,000 mega bonuses",
        "category": "special",
        "icon": "bi-star-half",
        "requirement_type": "mega_bonuses_hit",
        "requirement_value": 1000,
        "reward_gems": 300000,
        "achievement_points": 10,
        "rarity": "legendary"
    },

    # ==========================================
    # UPGRADE ACHIEVEMENTS (2)
    # ==========================================
    "upgrade_starter": {
        "id": "upgrade_starter",
        "name": "Upgrade Starter",
        "description": "Purchase your first upgrade",
        "category": "upgrades",
        "icon": "bi-shop",
        "requirement_type": "upgrades_purchased",
        "requirement_value": 1,
        "reward_gems": 1000,
        "achievement_points": 1,
        "rarity": "common"
    },
    "upgrade_collector": {
        "id": "upgrade_collector",
        "name": "Upgrade Collector",
        "description": "Purchase 10 upgrades",
        "category": "upgrades",
        "icon": "bi-shop-window",
        "requirement_type": "upgrades_purchased",
        "requirement_value": 10,
        "reward_gems": 10000,
        "achievement_points": 3,
        "rarity": "rare"
    },
}


# Achievement categories for filtering
ACHIEVEMENT_CATEGORIES = {
    "all": {"name": "All Achievements", "icon": "bi-trophy", "color": "#6366f1"},
    "clicks": {"name": "Clicking", "icon": "bi-mouse-fill", "color": "#3b82f6"},
    "earning": {"name": "Earning", "icon": "bi-gem", "color": "#10b981"},
    "combos": {"name": "Combos", "icon": "bi-lightning-charge-fill", "color": "#f59e0b"},
    "prestige": {"name": "Prestige", "icon": "bi-arrow-repeat", "color": "#8b5cf6"},
    "special": {"name": "Special", "icon": "bi-star-fill", "color": "#ec4899"},
    "upgrades": {"name": "Upgrades", "icon": "bi-shop", "color": "#06b6d4"},
}


# Rarity colors and multipliers
RARITY_CONFIG = {
    "common": {
        "color": "#9ca3af",
        "glow": "rgba(156, 163, 175, 0.3)",
        "name": "Common"
    },
    "rare": {
        "color": "#3b82f6",
        "glow": "rgba(59, 130, 246, 0.4)",
        "name": "Rare"
    },
    "epic": {
        "color": "#8b5cf6",
        "glow": "rgba(139, 92, 246, 0.5)",
        "name": "Epic"
    },
    "legendary": {
        "color": "#f59e0b",
        "glow": "rgba(245, 158, 11, 0.6)",
        "name": "Legendary"
    },
}


def get_achievement(achievement_id: str):
    """Get achievement by ID"""
    return ACHIEVEMENTS.get(achievement_id)


def get_all_achievements():
    """Get all achievement definitions"""
    return ACHIEVEMENTS


def get_achievements_by_category(category: str):
    """Get achievements filtered by category"""
    if category == "all":
        return ACHIEVEMENTS
    return {k: v for k, v in ACHIEVEMENTS.items() if v["category"] == category}


def calculate_total_achievement_points():
    """Calculate max possible achievement points"""
    return sum(ach["achievement_points"] for ach in ACHIEVEMENTS.values())


def get_achievement_categories():
    """Get all achievement categories"""
    return ACHIEVEMENT_CATEGORIES


# Total achievements: 23
# Total possible points: 106
print(f"[Achievement System] Loaded {len(ACHIEVEMENTS)} achievements")
print(f"[Achievement System] Total possible points: {calculate_total_achievement_points()}")
