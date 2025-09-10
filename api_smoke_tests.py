"""
Simple API smoke tests using FastAPI TestClient.
Verifies demo login, auth status, and wallet endpoints.
"""

from fastapi.testclient import TestClient
from main import app


def test_demo_login_and_me():
    client = TestClient(app)

    # Not authenticated initially
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "error"

    # Demo login
    r = client.post("/api/auth/demo-login")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "success"
    assert data.get("user", {}).get("username")

    # Authenticated now
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "success"
    assert data.get("user", {}).get("email")


def test_wallet_requires_auth_and_updates():
    client = TestClient(app)

    # Requires auth
    r = client.get("/api/trading/gamification/wallet")
    assert r.status_code == 200
    assert r.json().get("status") == "error"

    # Login
    r = client.post("/api/auth/demo-login")
    assert r.status_code == 200
    assert r.json().get("status") == "success"

    # Get wallet
    r = client.get("/api/trading/gamification/wallet")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "success"
    balance = data.get("data", {}).get("gem_coins")
    assert isinstance(balance, int)

    # Adjust wallet
    r = client.post("/api/trading/gamification/wallet/adjust", json={"amount": 250})
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "success"
    assert data.get("data", {}).get("adjustment") == 250


def test_social_public_endpoints():
    client = TestClient(app)

    # Public mock endpoints should not require token
    r = client.get("/api/social/online-friends")
    assert r.status_code == 200
    data = r.json()
    assert data.get("success") is True
    assert "data" in data or "online_friends" in data

    r = client.get("/api/social/leaderboards/level?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert data


def test_gaming_and_stats():
    client = TestClient(app)

    # Gaming stats endpoint
    r = client.get("/api/gaming/stats")
    assert r.status_code == 200
    data = r.json()
    assert data.get("success") is True
    assert "data" in data
