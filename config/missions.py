"""
Daily Missions and Weekly Challenges Configuration
Defines all available missions, challenges, and their rewards
"""

from datetime import datetime, timezone

# ==================== DAILY MISSIONS ====================
# Reset every day at 00:00 UTC

DAILY_MISSIONS = [
    {
        "id": "daily_login",
        "name": "Daily Check-In",
        "description": "Log in to your account",
        "reward": 100,
        "type": "login",
        "target": 1,
        "icon": "bi-calendar-check",
        "category": "general"
    },
    {
        "id": "place_5_bets",
        "name": "Active Player",
        "description": "Place 5 bets in roulette",
        "reward": 500,
        "type": "bet_placed",
        "target": 5,
        "icon": "bi-dice-5-fill",
        "category": "roulette"
    },
    {
        "id": "win_3_bets",
        "name": "Lucky Streak",
        "description": "Win 3 roulette bets",
        "reward": 1000,
        "type": "bet_won",
        "target": 3,
        "icon": "bi-trophy-fill",
        "category": "roulette"
    },
    {
        "id": "view_portfolio",
        "name": "Portfolio Manager",
        "description": "Check your portfolio",
        "reward": 50,
        "type": "view_portfolio",
        "target": 1,
        "icon": "bi-wallet2",
        "category": "general"
    },
    {
        "id": "check_prices",
        "name": "Market Watcher",
        "description": "View cryptocurrency prices",
        "reward": 75,
        "type": "view_prices",
        "target": 1,
        "icon": "bi-graph-up",
        "category": "crypto"
    }
]

# ==================== WEEKLY CHALLENGES ====================
# Reset every Monday at 00:00 UTC

WEEKLY_CHALLENGES = [
    {
        "id": "weekly_earnings",
        "name": "Profit Master",
        "description": "Earn 10,000 GEM from roulette wins",
        "reward": 5000,
        "type": "total_winnings",
        "target": 10000,
        "icon": "bi-cash-coin",
        "category": "roulette",
        "difficulty": "hard"
    },
    {
        "id": "weekly_bets",
        "name": "Dedicated Gambler",
        "description": "Place 50 roulette bets",
        "reward": 3000,
        "type": "bet_count",
        "target": 50,
        "icon": "bi-dice-6-fill",
        "category": "roulette",
        "difficulty": "medium"
    },
    {
        "id": "weekly_streak",
        "name": "Dedicated Player",
        "description": "Log in 7 days in a row",
        "reward": 2500,
        "type": "login_streak",
        "target": 7,
        "icon": "bi-fire",
        "category": "general",
        "difficulty": "medium"
    },
    {
        "id": "weekly_win_rate",
        "name": "Skilled Player",
        "description": "Win 20 roulette bets",
        "reward": 4000,
        "type": "win_count",
        "target": 20,
        "icon": "bi-award-fill",
        "category": "roulette",
        "difficulty": "hard"
    }
]

# ==================== MISSION HELPER FUNCTIONS ====================

def get_mission_by_id(mission_id: str):
    """Get mission definition by ID from daily missions."""
    for mission in DAILY_MISSIONS:
        if mission["id"] == mission_id:
            return mission
    return None

def get_challenge_by_id(challenge_id: str):
    """Get challenge definition by ID from weekly challenges."""
    for challenge in WEEKLY_CHALLENGES:
        if challenge["id"] == challenge_id:
            return challenge
    return None

def get_missions_by_category(category: str):
    """Get all daily missions in a specific category."""
    return [m for m in DAILY_MISSIONS if m.get("category") == category]

def get_challenges_by_difficulty(difficulty: str):
    """Get weekly challenges by difficulty level."""
    return [c for c in WEEKLY_CHALLENGES if c.get("difficulty") == difficulty]

def get_mission_by_type(event_type: str):
    """Get all missions that track a specific event type."""
    missions = []
    for mission in DAILY_MISSIONS:
        if mission["type"] == event_type:
            missions.append(mission)
    return missions

def get_challenge_by_type(event_type: str):
    """Get all challenges that track a specific event type."""
    challenges = []
    for challenge in WEEKLY_CHALLENGES:
        if challenge["type"] == event_type:
            challenges.append(challenge)
    return challenges

def get_total_daily_rewards():
    """Calculate total possible GEM from completing all daily missions."""
    return sum(m["reward"] for m in DAILY_MISSIONS)

def get_total_weekly_rewards():
    """Calculate total possible GEM from completing all weekly challenges."""
    return sum(c["reward"] for c in WEEKLY_CHALLENGES)

# ==================== MISSION RESET TIMING ====================

def get_next_daily_reset():
    """Get timestamp for next daily mission reset (00:00 UTC)."""
    from datetime import datetime, timedelta
    now = datetime.now(timezone.utc)
    next_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return next_reset

def get_next_weekly_reset():
    """Get timestamp for next weekly challenge reset (Monday 00:00 UTC)."""
    from datetime import datetime, timedelta
    now = datetime.now(timezone.utc)
    days_until_monday = (7 - now.weekday()) % 7
    if days_until_monday == 0 and now.hour == 0 and now.minute == 0:
        # It's currently Monday 00:00, next reset is next Monday
        days_until_monday = 7
    next_monday = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_until_monday)
    return next_monday

def get_current_week_start():
    """Get the start date (Monday) of the current week."""
    from datetime import datetime, timedelta
    now = datetime.now(timezone.utc)
    # Get Monday of current week
    monday = now - timedelta(days=now.weekday())
    return monday.date()

def seconds_until_daily_reset():
    """Get seconds remaining until next daily reset."""
    next_reset = get_next_daily_reset()
    now = datetime.now(timezone.utc)
    delta = next_reset - now
    return int(delta.total_seconds())

def seconds_until_weekly_reset():
    """Get seconds remaining until next weekly reset."""
    next_reset = get_next_weekly_reset()
    now = datetime.now(timezone.utc)
    delta = next_reset - now
    return int(delta.total_seconds())

# ==================== MISSION STATISTICS ====================

MISSION_STATS = {
    "total_daily_missions": len(DAILY_MISSIONS),
    "total_weekly_challenges": len(WEEKLY_CHALLENGES),
    "max_daily_gems": get_total_daily_rewards(),
    "max_weekly_gems": get_total_weekly_rewards(),
    "categories": list(set(m.get("category", "general") for m in DAILY_MISSIONS)),
    "difficulties": list(set(c.get("difficulty", "medium") for c in WEEKLY_CHALLENGES))
}

# ==================== EVENT TYPE MAPPING ====================
# Maps mission types to the events that should trigger progress

EVENT_TYPE_MAP = {
    "login": ["user_login"],
    "bet_placed": ["roulette_bet_placed"],
    "bet_won": ["roulette_bet_won"],
    "view_portfolio": ["portfolio_viewed"],
    "view_prices": ["crypto_prices_viewed"],
    "total_winnings": ["roulette_bet_won"],  # Tracks amount won
    "bet_count": ["roulette_bet_placed"],    # Tracks bet count
    "login_streak": ["user_login"],          # Tracks consecutive days
    "win_count": ["roulette_bet_won"]        # Tracks win count
}

def get_missions_for_event(event_name: str):
    """
    Get all missions/challenges that should be updated for a given event.

    Args:
        event_name: The event that occurred (e.g., 'user_login', 'roulette_bet_placed')

    Returns:
        dict with 'daily' and 'weekly' lists of mission/challenge IDs
    """
    result = {"daily": [], "weekly": []}

    # Check daily missions
    for mission in DAILY_MISSIONS:
        mission_type = mission["type"]
        if mission_type in EVENT_TYPE_MAP and event_name in EVENT_TYPE_MAP[mission_type]:
            result["daily"].append(mission["id"])

    # Check weekly challenges
    for challenge in WEEKLY_CHALLENGES:
        challenge_type = challenge["type"]
        if challenge_type in EVENT_TYPE_MAP and event_name in EVENT_TYPE_MAP[challenge_type]:
            result["weekly"].append(challenge["id"])

    return result

# ==================== MISSION CONFIGURATION INFO ====================

print("=" * 60)
print("GEM Marketplace - Missions Configuration")
print("=" * 60)
print(f"Daily Missions:    {len(DAILY_MISSIONS)} missions")
print(f"Weekly Challenges: {len(WEEKLY_CHALLENGES)} challenges")
print(f"Max Daily Gems:    {get_total_daily_rewards()} GEM")
print(f"Max Weekly Gems:   {get_total_weekly_rewards()} GEM")
print("=" * 60)
