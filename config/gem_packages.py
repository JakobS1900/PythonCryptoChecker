"""
GEM Package Configuration
Defines purchasable GEM packages for the marketplace.

Note: This is a simulated purchase system for educational purposes only.
No real money is processed.
"""

GEM_PACKAGES = {
    "starter": {
        "id": "starter",
        "name": "Starter Pack",
        "description": "Perfect for trying out the platform",
        "gems": 1000,
        "bonus_gems": 0,
        "total_gems": 1000,
        "price_usd": 10.00,
        "badge": None,
        "popular": False,
        "best_value": False,
        "icon": "bi-gem",
        "color": "secondary"
    },
    "bronze": {
        "id": "bronze",
        "name": "Bronze Package",
        "description": "Get started with extra bonus GEM",
        "gems": 5000,
        "bonus_gems": 500,
        "total_gems": 5500,
        "price_usd": 25.00,
        "badge": "+10% Bonus",
        "popular": False,
        "best_value": False,
        "icon": "bi-award",
        "color": "warning"
    },
    "silver": {
        "id": "silver",
        "name": "Silver Package",
        "description": "Most popular choice for regular players",
        "gems": 15000,
        "bonus_gems": 3000,
        "total_gems": 18000,
        "price_usd": 50.00,
        "badge": "+20% Bonus",
        "popular": True,
        "best_value": False,
        "icon": "bi-star-fill",
        "color": "info"
    },
    "gold": {
        "id": "gold",
        "name": "Gold Package",
        "description": "Best value with huge bonus GEM",
        "gems": 50000,
        "bonus_gems": 15000,
        "total_gems": 65000,
        "price_usd": 100.00,
        "badge": "+30% Bonus",
        "popular": False,
        "best_value": True,
        "icon": "bi-trophy-fill",
        "color": "gem"
    },
    "platinum": {
        "id": "platinum",
        "name": "Platinum Elite",
        "description": "Ultimate package for serious players",
        "gems": 150000,
        "bonus_gems": 60000,
        "total_gems": 210000,
        "price_usd": 250.00,
        "badge": "+40% Bonus",
        "popular": False,
        "best_value": False,
        "icon": "bi-stars",
        "color": "primary"
    }
}


def get_package(package_id: str) -> dict:
    """Get package details by ID."""
    return GEM_PACKAGES.get(package_id)


def get_all_packages() -> list:
    """Get all packages as a list."""
    return list(GEM_PACKAGES.values())


def calculate_gem_value_usd(gems: float) -> float:
    """
    Calculate USD value of GEM amount.
    Based on: 1,000 GEM = $10 USD (reference rate)
    """
    return (gems / 1000) * 10.0


def validate_package_id(package_id: str) -> bool:
    """Validate if package ID exists."""
    return package_id in GEM_PACKAGES
