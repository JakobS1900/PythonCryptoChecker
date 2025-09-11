# 🔌 CryptoChecker Platform - API Documentation

## Overview

The CryptoChecker platform provides a comprehensive RESTful API for managing virtual crypto gambling, trading, and gamification features. All endpoints use session-based authentication and return JSON responses with consistent error handling.

## Base URL

```
http://localhost:8000
```

## Authentication

The API uses session-based authentication. Users must be authenticated to access most endpoints.

### Response Format

All API responses follow this consistent format:

```json
{
  "status": "success|error",
  "message": "Human readable message",
  "data": {
    // Response data here
  }
}
```

## API Endpoints

### 🔐 Authentication & User Management

#### `POST /api/auth/demo-login`
Quick demo login with pre-populated user data.

**Request**: No body required
**Response**:
```json
{
  "status": "success",
  "user": {
    "id": "demo-user-12345",
    "username": "DemoPlayer",
    "email": "demo@cryptochecker.com",
    "display_name": "DemoPlayer",
    "gem_coins": 1000,
    "current_level": 1
  }
}
```

#### `POST /api/auth/register`
Register a new user account.

**Request**:
```json
{
  "username": "player123",
  "email": "player@example.com",
  "password": "securepassword123"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Account created successfully!",
  "data": {
    "access_token": "token-user-123-1234567890",
    "refresh_token": "refresh-user-123-1234567890",
    "user": {
      "id": "user-123-1234567890",
      "username": "player123",
      "gem_coins": 1000,
      "current_level": 1
    }
  }
}
```

#### `GET /api/auth/logout`
Logout current user and clear session.

**Response**:
```json
{
  "status": "success",
  "message": "Logged out successfully"
}
```

#### `GET /api/auth/me`
Get current authenticated user information.

**Response**:
```json
{
  "status": "success",
  "user": {
    "id": "user-123",
    "username": "player123",
    "email": "player@example.com",
    "display_name": "Player One",
    "current_level": 5,
    "avatar_url": "/static/images/default-avatar.png"
  }
}
```

---

### 💼 Advanced Trading System

#### `GET /api/trading/portfolio/demo/summary`
Get portfolio summary with real-time data.

**Authentication**: Required

**Response**:
```json
{
  "status": "success",
  "data": {
    "portfolio_value": 12500.50,
    "total_return": 2500.50,
    "return_percentage": 25.01,
    "available_cash": 7500.00,
    "open_positions": 3,
    "gem_coins": 1000
  }
}
```

#### `GET /api/trading/prices`
Get live cryptocurrency prices.

**Parameters**:
- `ids` (query): Comma-separated coin IDs (e.g., "bitcoin,ethereum,cardano")

**Response**:
```json
{
  "status": "success",
  "data": {
    "bitcoin": {
      "price": 43250.75,
      "change_24h": 2.35
    },
    "ethereum": {
      "price": 2680.40,
      "change_24h": -1.25
    }
  }
}
```

#### `GET /api/trading/quick-trade/{action}/{coin_id}`
Execute a quick market trade.

**Parameters**:
- `action` (path): "BUY" or "SELL"
- `coin_id` (path): Cryptocurrency ID (e.g., "bitcoin")
- `amount` (query): USD amount to trade

**Authentication**: Required

**Response**:
```json
{
  "status": "success",
  "data": {
    "trade_id": "trade-1234567890",
    "action": "BUY",
    "coin_id": "bitcoin",
    "amount": 100.00,
    "gem_reward": 1,
    "message": "BUY order executed successfully! +1 GEM coins earned."
  }
}
```

#### `POST /api/trading/orders`
Place advanced order (LIMIT, STOP_LOSS, TAKE_PROFIT).

**Authentication**: Required

**Request**:
```json
{
  "side": "BUY",
  "type": "LIMIT",
  "coin_id": "bitcoin",
  "quantity": 0.002,
  "price": 42000.00
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "order_id": "order-1234567890",
    "type": "LIMIT",
    "side": "BUY",
    "coin_id": "bitcoin",
    "quantity": 0.002,
    "price": 42000.00,
    "status": "PENDING",
    "message": "LIMIT order placed successfully!"
  }
}
```

#### `GET /api/trading/gamification/wallet`
Get user's GEM wallet information.

**Authentication**: Required

**Response**:
```json
{
  "status": "success",
  "data": {
    "gem_coins": 1250,
    "usd_value": 12.50,
    "total_earned": 500,
    "total_spent": 250
  }
}
```

---

### 🎰 Enhanced Roulette Gaming

#### `POST /api/roulette/spin`
Execute a roulette spin with bets.

**Authentication**: Required

**Request**:
```json
{
  "bets": [
    {
      "type": "single",
      "value": 7,
      "amount": 50
    },
    {
      "type": "red",
      "value": "red",
      "amount": 25
    }
  ]
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "winning_number": 7,
    "total_bet": 75,
    "total_payout": 1825,
    "net_result": 1750,
    "winning_bets": [
      {
        "type": "single",
        "value": 7,
        "amount": 50,
        "payout": 1800
      }
    ],
    "new_balance": 2665,
    "is_winner": true
  }
}
```

#### `GET /api/roulette/stats`
Get user's roulette gaming statistics.

**Authentication**: Required

**Response**:
```json
{
  "status": "success",
  "data": {
    "total_games": 45,
    "total_wins": 18,
    "total_losses": 27,
    "win_rate": 40.00,
    "current_level": 3,
    "total_experience": 2250,
    "gem_balance": 1500
  }
}
```

#### `POST /api/roulette/validate-bet`
Validate a roulette bet before placing.

**Authentication**: Required

**Request**:
```json
{
  "amount": 100
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "valid": true,
    "current_balance": 1500,
    "max_bet": 1500
  }
}
```

---

### 🛠️ Utility Endpoints

#### `GET /api/test`
Simple API health check.

**Response**:
```json
{
  "message": "API is working!",
  "timestamp": 1704110400.123
}
```

#### `GET /api/auth/test`
Authentication system health check.

**Response**:
```json
{
  "status": "success",
  "message": "Authentication API is working!",
  "timestamp": 1704110400.123
}
```

---

## Error Handling

All API endpoints return consistent error responses:

### Common Error Responses

#### 401 Unauthorized
```json
{
  "status": "error",
  "message": "Not authenticated"
}
```

#### 400 Bad Request
```json
{
  "status": "error",
  "message": "Invalid bet amount"
}
```

#### 500 Internal Server Error
```json
{
  "status": "error",
  "message": "Trade execution failed"
}
```

---

## Integration Examples

### JavaScript API Client

```javascript
class CryptoCheckerAPI {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
  }

  async demoLogin() {
    const response = await fetch(`${this.baseURL}/api/auth/demo-login`, {
      method: 'POST',
      credentials: 'include'
    });
    return await response.json();
  }

  async getPortfolio() {
    const response = await fetch(`${this.baseURL}/api/trading/portfolio/demo/summary`, {
      credentials: 'include'
    });
    return await response.json();
  }

  async spinRoulette(bets) {
    const response = await fetch(`${this.baseURL}/api/roulette/spin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ bets })
    });
    return await response.json();
  }
}

// Usage
const api = new CryptoCheckerAPI();
await api.demoLogin();
const portfolio = await api.getPortfolio();
const result = await api.spinRoulette([
  { type: 'red', value: 'red', amount: 10 }
]);
```

---

## Testing

Use the comprehensive test suite to validate API functionality:

```bash
python test_endpoints.py
```

This script tests all major endpoints and validates response formats.

---

*Generated for CryptoChecker Gaming Platform - January 2025*