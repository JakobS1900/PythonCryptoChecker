# 📊 Crypto Analytics + Gamification Platform

FastAPI-based crypto analytics and paper trading app with a virtual economy, inventory, consumables, and a growing set of gaming features.

## 🚀 Highlights

- Paper trading with RiskPolicy (max position %, trade value %, open positions)
- SL/TP protections with OCO groups; open order management and background triggers
- Virtual wallet + crypto holdings that mirror paper trades
- Consumables with active effects (XP multiplier, GEM multiplier, drop rate bonus, guaranteed rare drops)
- Item drops with rarity tiers; inventory with filters/sort/pagination
- Clean web UI: Trading dashboard and full Inventory page

## Quick Start

Prerequisites: Python 3.8+

1) Install deps
```bash
pip install -r requirements.txt
```

2) Run the web app
```bash
python run.py
```

3) Open the UI
- Trading dashboard: http://127.0.0.1:8000/trading
- Inventory page: http://127.0.0.1:8000/gaming/inventory
- API docs: http://127.0.0.1:8000/api/docs

## Key Endpoints

- Trading
  - GET /api/trading/portfolio/{id}/summary
  - GET /api/trading/portfolio/{id}/transactions
  - POST /api/trading/portfolio/{id}/orders
  - GET /api/trading/portfolio/{id}/orders/open
  - POST /api/trading/orders/{order_id}/cancel
  - POST /api/trading/oco/{group_id}/cancel
  - POST /api/trading/portfolio/{id}/orders/protect
  - POST /api/trading/portfolio/{id}/orders/protect/cancel
  - POST /api/trading/portfolio/{id}/orders/protect/replace
  - GET/PUT /api/trading/risk-policy/{id}

- Gamification
  - GET /api/trading/gamification/wallet
  - GET /api/trading/gamification/inventory
  - GET /api/trading/gamification/consumables
  - POST /api/trading/gamification/consumables/{inventory_id}/use
  - GET /api/trading/gamification/effects
  - GET /api/trading/gamification/activity

## UI Pages

- /trading — trading dashboard (wallet, inventory preview, activity, effects, open orders, replace protections)
- /gaming/inventory — full inventory with search, filters, sort, pagination, and Use Consumable

## Project Structure

```
PythonCryptoChecker/
├── run.py                  # Single entrypoint
├── scripts/                # Helper scripts
│   ├── stop-server.ps1     # Windows stop helper
│   └── stop-server.sh      # macOS/Linux stop helper
├── web/                    # FastAPI app, templates, routers
├── trading/                # Trading engine, models, DB
├── gamification/           # Virtual economy, items, effects
├── inventory/              # Inventory manager and trading system
├── auth/, gaming/, social/ # Foundations for next phases
└── README.md
```

## Roadmap (extract)

- Phase 3 — Trading Engine
  - [x] Paper trading (demo user/portfolio)
  - [x] Risk management (policy + SL/TP + OCO)
  - [x] Open orders + protections management
  - [ ] Exchange integrations

- Phase 5 — Gamification
  - [x] Virtual wallet/holdings mirror
  - [x] Inventory + consumables (ActiveEffect buffs)
  - [x] Item drops (rarity floors)
  - [ ] Achievements & badges
  - [ ] Leaderboards & friends
  - [ ] Game UI wiring (roulette)

For recent changes, see PROGRESS.md.
