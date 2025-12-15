# Claude Directions: Restore Navbar, Polish Roulette, and Fully Flesh Out Trading System

This document is a precise implementation brief for Claude (or any code-gen assistant) to complete the remaining work in the CryptoChecker project. It defines scope, acceptance criteria, file paths, and a step-by-step plan. Follow it exactly, keeping changes focused and incremental.

---

## Project Snapshot (Current State)

- Framework: FastAPI backend + Jinja templates + vanilla JS + Bootstrap 5
- Auth: Session-based (see `main.py`, `web/static/js/auth.js`)
- Trading: UI restored at `/trading`; API mounted at `/api/trading` via `web/trading_api.py`, core engine in `trading/engine.py`
- GEM Economy: Configurable rate via `GEM_USD_RATE_USD_PER_GEM` (default 0.01 → 1 GEM = $0.01)
- Roulette: Classic roulette running at `/gaming/roulette` with cleaned layout
- Navbar: Global nav restored; ensure consistency across pages

---

## High-Priority Fixes (Navigation + Consistency)

1) Unify Global Navbar
- Goal: Every user-facing page must use the same navbar and auth controls.
- Actions:
  - Ensure templates extend a single base with the global navbar where feasible (`web/templates/base.html` or `base_enhanced.html`).
  - Pages that currently embed their own nav (e.g., `web/templates/trading.html`) should either:
    - extend the base layout and move page-specific content into blocks, OR
    - keep the in-page nav but ensure auth hooks (`#auth-buttons`, `#user-menu`) and script includes (`utils.js`, `auth.js`, `api.js`) match base.
- Acceptance:
  - On `/`, `/trading`, `/gaming/roulette`, `/inventory`, the top bar is visible and clickable.
  - Auth consistently switches between guest buttons and user menu.

2) Auth State on All Pages
- Ensure every page that shows nav also includes the base script order:
  - `utils.js`, `auth.js`, `api.js` before other page scripts.
- Verify `/api/auth/me` is called and nav is updated on page load.

---

## Trading System: Full Feature Build-Out

Target: A complete paper-trading experience using real-time crypto prices that integrates with the GEM economy.

### Backend Scope

Files to edit/add:
- `web/trading_api.py`
- `trading/engine.py`
- `trading/models.py` (migrations if needed)
- `data_providers.py` (reuse `DataManager` for prices)

Features:
1) Order Types
- Already: MARKET
- Add: LIMIT, STOP_LOSS, TAKE_PROFIT (persist, enforce), OCO linking
  - Engine should place pending orders and evaluate triggers periodically in `evaluate_risk_triggers()` (already stubbed for SL/TP — extend it and add tests/logic for LIMIT).

2) OCO (One-Cancels-the-Other)
- Create/maintain `OcoGroup` and `OcoLink` for SL/TP pairs.
- When one order fills, cancel peers in the same group.

3) Portfolio Performance & Analytics
- Extend `get_portfolio_summary()` to include:
  - Daily PnL (simple bucketed returns), cumulative returns, win rate, drawdown estimate, Sharpe proxy
  - Return top-N winners/losers based on unrealized PnL

4) Real-time Pricing
- Continue using `DataManager` (CoinGecko/CoinCap fallback). Add a small in-memory cache to avoid hammering APIs.
- For frontend updates, expose `/api/trading/prices?ids=bitcoin,ethereum,...` that returns latest prices in one call.

5) GEM Integration
- Quick Trade currently adjusts GEM on BUY/SELL by converting USD↔GEM using `GEM_USD_RATE_USD_PER_GEM`.
- Extend to full engine executions:
  - When orders fill in `_execute_order()`, call a helper to adjust GEM wallet by the USD notional (and reverse on SELL).
  - Respect `GEM_USD_RATE_USD_PER_GEM` from env.

6) Risk Policy Management
- Endpoints to GET/PUT a portfolio’s risk policy (max trade value %, max position %, max open positions, default SL/TP%).
- Validate BUYs against policy; compute portfolio value safely (cash + holdings marked-to-market).

7) Transactions & History
- Ensure all trade executions create transaction rows with fee, PnL fields.
- Add `/api/trading/portfolio/{id}/performance` with risk metrics and recent transactions (API already scaffolded — complete and verify return shape).

8) DB Compatibility
- Avoid breaking existing tables. If adding columns is required, implement lazy-add (try/except on missing columns) or write a migration note.

### Frontend Scope

Files to edit/add:
- `web/templates/trading.html`
- `web/static/css/trading-clean.css`
- Add new file `web/static/js/trading.js` for modularity (move inline script logic gradually)

Layout Guidelines:
- Two-column layout (already present):
  - Left: Holdings, Open Orders, Transactions (with sorting/filtering). Consider collapsible sections and sticky headings.
  - Right (sticky): Quick Trade, Wallet (with GEM conversion), Inventory preview, Consumables, Active Effects.

Interactions:
- Quick Trade: USD input, Action (Buy/Sell), Coin select, Order Type select (Market/Limit for now).
  - MARKET: call `/api/trading/quick-trade/{action}/{coin_id}?amount={USD}`.
  - LIMIT: POST to `/api/trading/orders` with JSON `{ type: 'LIMIT', side: 'BUY/SELL', price, quantity, coin_id }`.
- Open Orders: allow cancel; show trigger price for STOP_LOSS/TAKE_PROFIT.
- Holdings: show quantity, avg cost, current price, market value, PnL.
- Transactions: show list with date, type, quantity, price, amount, fee, PnL (if applicable).
- Prices: poll `/api/trading/prices` every 10-15s to update holdings and order triggers.

Acceptance Criteria (Trading)
- Place MARKET/LIMIT/SL/TP orders and see correct state transitions.
- OCO: creating SL+TP for a position results in mutual cancellation when one fills.
- Portfolio summary shows correct totals and updates after trades.
- GEM wallet updates according to `GEM_USD_RATE_USD_PER_GEM` for all trade executions.
- API endpoints return structured JSON with `status: "success"` for success and proper HTTP codes on error.

---

## Roulette Verification (Regression Pass)

- Ensure only one JS controller is attached; no console errors.
- Confirm Spin button enables after at least one bet.
- Validate classic bets payouts: number (35:1), red/black (1:1), even/odd (1:1), high/low (1:1), green (35:1).
- Keep layout aligned with `enhanced-theme.css` and the current wheel visuals.

---

## API Catalogue (Trading)

Implement/verify the following endpoints (under `/api/trading`):

- `GET /health`
- `GET /gamification/wallet`
- `GET /gamification/inventory`
- `GET /portfolio/{portfolio_id}/summary` (or `/performance`) — summary + analytics
- `GET /portfolio/{portfolio_id}/orders/open`
- `GET /portfolio/{portfolio_id}/transactions?limit=10`
- `GET /quick-trade/{action}/{coin_id}?amount={USD}`
- `GET /prices?ids=bitcoin,ethereum,...` — returns map of id→price
- `POST /orders` — create LIMIT/STOP_LOSS/TAKE_PROFIT (body includes side, price, quantity, coin_id)
- `POST /oco/{group_id}/cancel` — cancel OCO group
- `POST /orders/{order_id}/cancel` — cancel single order
- `GET /risk-policy/{portfolio_id}` / `PUT /risk-policy/{portfolio_id}`

All should return `{ "status": "success", "data": ... }` or 4xx/5xx with `detail`.

---

## Styling & UX Guidelines

- Keep styles in `web/static/css/trading-clean.css`; avoid inline CSS.
- Respect existing visual language (glassmorphism, gradients, icons).
- Maintain accessibility: clear labels, focus styles, reasonable contrasts.
- Ensure mobile responsiveness (min-width breakpoints, sticky disabled on small screens).

---

## Testing Plan

Manual Scenarios:
1) Auth flows: login/logout; nav updates on `/`, `/trading`, `/gaming/roulette`.
2) Trading MARKET buy/sell with USD amount; GEM wallet adjusts.
3) LIMIT order placement; appears in open orders; cancels; fills on trigger.
4) OCO: place SL+TP; trigger one path and see the other canceled.
5) Portfolio summary updates: totals, PnL.
6) Prices polling updates holdings and triggers; no console errors.
7) Roulette: place bets, spin, payouts correct; no duplicate controllers.

Automated (optional, if test harness available):
- Unit tests for `trading/engine.py` core methods (validate_order, execute_order, evaluate_risk_triggers).

---

## Step-by-Step Plan for Claude

1) Read & Sync
- Skim these files to understand current wiring:
  - `main.py`, `web/trading_api.py`, `trading/engine.py`, `trading/models.py`
  - `web/templates/trading.html`, `web/static/js/auth.js`, `data_providers.py`

2) Navbar Consistency
- Make `/trading` extend `base.html` or ensure the embedded navbar matches exactly. Prefer extension for less duplication.

3) Trading Backend
- Implement missing endpoints for LIMIT/SL/TP/OCO.
- Complete `evaluate_risk_triggers()` for LIMIT and OCO logic.
- Add `/api/trading/prices` for batched price fetch.
- Ensure GEM wallet adjustments happen on all executions.

4) Trading Frontend
- Create `web/static/js/trading.js`; move most inline logic from `trading.html` here.
- Add basic sorting/filtering for holdings and transactions.
- Wire prices polling and UI updates.

5) Docs Update
- Append README “Trading & GEM Economy” section with new endpoints.
- Confirm DEPLOYMENT.md lists `GEM_USD_RATE_USD_PER_GEM`.

6) QA Checklist
- Run server; verify flows above. Fix any console or 500 errors tightly.

---

## Guardrails

- Do not break unrelated routes or templates.
- Keep changes minimal and focused; no sweeping refactors.
- Preserve API response shape; return proper HTTP status codes on errors.
- Avoid cross-registry SQLAlchemy relationships (prior mapper error cause).

---

## Example Prompts for Claude

- “Please extend `web/trading_api.py` to add POST `/api/trading/orders` supporting LIMIT/STOP_LOSS/TAKE_PROFIT with JSON body { side, price, quantity, coin_id }, and wire it to `trading/engine.py.place_order`. Return { status: 'success', data: { order_id, status } } or appropriate 4xx on validation failures.”
- “Implement batched price endpoint GET `/api/trading/prices?ids=bitcoin,ethereum` using `DataManager`, cache for 10s, and return a map of `id -> { price, ts }`.”
- “In `trading/engine.py`, complete `evaluate_risk_triggers()` to handle LIMIT orders and OCO cancelation. Add a helper that cancels peer orders when one fills.”
- “Move the inline script in `web/templates/trading.html` into a new `web/static/js/trading.js`, adjusting the template to include it after `api.js` and `auth.js`. Ensure no console errors.”
- “Update `web/templates/trading.html` to extend `base.html` for the navbar, removing duplicated header markup.”

---

## Done Definition (Sign-off)

- Navbar consistent and clickable across `/`, `/trading`, `/gaming/roulette`, `/inventory`.
- Trading supports MARKET/LIMIT/SL/TP, OCO, and real-time prices.
- Portfolio summary and PnL correct; transactions logged with fees.
- GEM wallet adjusts on BUY/SELL according to `GEM_USD_RATE_USD_PER_GEM`.
- No console errors; API returns clean JSON with correct status codes.
- README/DEPLOYMENT updated with new endpoints and environment variable.

