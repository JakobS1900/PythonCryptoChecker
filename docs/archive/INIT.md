# CryptoChecker Platform – Initialization Overview

This document is a living guide to the project: how it runs, key architecture, routes, UI patterns, testing, and recent fixes. Use it as the single place to orient new contributors and recover context quickly.

## Quick Start

- Entrypoint: `python run.py`
- App URL: `http://localhost:8000`
- API Docs: `http://localhost:8000/api/docs`
- Env: `.env` created automatically by `run.py` if missing

## Project Structure (high-level)

- `main.py` – FastAPI app, routes, mock APIs, session auth
- `web/` – templates, static assets, front-end JS
- `database/` – async SQLAlchemy manager and unified models
- `api/` – modular API routers (auth, gaming, social, etc.)
- `gamification/`, `inventory/`, `trading/` – domain modules
- `run.py` – startup helper (env + uvicorn)

## Branding & Theming

- Unified brand: “CryptoChecker Gaming Platform”
- Base templates standardized to show brand, icons, and enhanced theme
- Prior references to “CryptoGaming” removed; see `BRANDING_UPDATED.md`

## Web Routes

- `/` – Home (dashboard-like landing)
- `/login` – Enhanced login page
- `/register` – Enhanced register page
- `/dashboard` – Redirects (307) to `/` to avoid duplication
- `/gaming` → redirects to `/gaming/roulette`
- `/gaming/roulette`, `/gaming/dice`, `/gaming/crash`, `/gaming/plinko`, `/gaming/tower`
- `/gaming/inventory` – Inventory page
- `/portfolio`, `/leaderboards`, `/tournaments`, `/social`
- `/profile` – Profile view + edit

## API Endpoints (selected)

- Auth: `/api/auth/register`, `/api/auth/login`, `/api/auth/logout{GET|POST}`, `/api/auth/me`
- Wallet (demo): `/api/trading/gamification/wallet`, `/api/trading/gamification/wallet/adjust`, `/api/trading/gamification/wallet/process-bet-result`
- Social (public/mock): `/api/social/*` used by UI
- Social (secure/token): mounted under `/api/social-secure/*` to avoid 403 clashes
- Profile: `/api/profile/update`, `/api/profile/avatar`, `/api/profile/avatar/remove`

Notes:
- Mock/demo data used for rapid UI development;
- Session-based auth (Starlette `SessionMiddleware`); no password storage for demo flows.

## Navbar & Auth UI Conventions

- Guest container: `#auth-buttons`
- User container: `#user-menu`
- Username: `#username-display`
- Navbar GEM: `#nav-gem-balance` (unique in navbars)
- In-page balances use `#walletBalance`
- Global auth helper: `web/static/js/auth.js`

What `auth.js` does:
- Checks `/api/auth/me`, toggles `#auth-buttons` and `#user-menu`
- Updates `#nav-gem-balance` and, when present, `#walletBalance`
- Polls balance every 30s, refreshes on focus/visibility change

## Recent Fixes & Rationale

- Removed duplicate demo-login endpoint; unified session user data
- Standardized nav IDs → fixed auth state UI not updating
- Removed duplicate GEM counters; single counter near username
- Dashboard route redirected to home to avoid duplicate content
- Fixed 403 conflicts by moving secure Social API under `/api/social-secure`
- Added `/profile` page with edit + avatar upload support
- Added avatar fallback SVG and safe default display
- Added platform live stats endpoint with always-rising numbers and home sparklines
- Implemented DB-backed Friends system (requests/accept/decline/remove)
- Added Social Bots with opt-out controls, manual nudge, and env-configurable frequency

## Profile & Avatar

- `/profile` page shows basic info and stats, with edit form
- Edit profile: `POST /api/profile/update` updates `display_name`/`bio` in session and attempts DB persistence (best effort)
- Avatar upload: `POST /api/profile/avatar` (max 4MB, MIME-validated) saves to `web/static/uploads/avatars/` and optionally generates a 256x256 thumbnail if Pillow is installed; updates session and tries DB persistence
- Remove avatar: `POST /api/profile/avatar/remove` resets to default and deletes uploaded files

## Database

- Async SQLAlchemy engine via `database/database_manager.py`
- Unified models in `database/unified_models.py` (e.g., `User`, `VirtualWallet`, etc.)
- Current profile persistence is best-effort: updates DB if a corresponding `User` exists, otherwise session-only

## Friends System

- Endpoints (session-based):
  - `GET /api/social/friends` – accepted friends
  - `GET /api/social/friends/requests` – pending friend requests
  - `POST /api/social/friends/request` – send request `{ username }`
  - `POST /api/social/friends/requests/{id}` – respond `{ action: ACCEPT | DECLINE }`
  - `DELETE /api/social/friends/{friend_id}` – remove friendship
  - `GET /api/social/stats` – sidebar counters
- Behavior:
  - Creates a minimal DB `User` for session-only users so relationships persist
  - Respects `User.allow_friend_requests` when present (opt-out)

## Social Bots

- Background bots send occasional friend requests to users; seeded bot accounts are created on startup.
- User controls:
  - Opt-out switch on `/social` (Quick Actions) → `PUT /api/social/bots/settings` with `{ allow_bots: boolean }`
  - Manual “Show Demo Requests” button triggers `POST /api/social/bots/nudge`
- Bot settings via env:
  - `BOTS_ENABLED` (default `true`)
  - `BOTS_MIN_SEC` (default `30`)
  - `BOTS_MAX_SEC` (default `90`)
  - `BOTS_PENDING_CAP` (default `5`)
  - `BOTS_SEED_ACCEPTED` (default `2`)
  - `BOTS_SEED_PENDING` (default `1`)
- Settings endpoints:
  - `GET /api/social/bots/settings` → { bots_enabled, min_seconds, max_seconds, pending_cap, allow_bots }
  - `PUT /api/social/bots/settings` → update per-user opt-out

## Platform Live Stats

- Endpoint: `GET /api/platform/stats` (time-based, deterministic, increasing)
- Home page renders four counters with animated sparklines and smooth per-second increases
- Server sync every ~15s; re-sync on tab focus/visibility

## Testing

- Simple structural test: `test_routes.py` (checks route and template patterns)
- API smoke tests: `api_smoke_tests.py` (auth, wallet, social, gaming)
- Run: `python test_routes.py`, `python api_smoke_tests.py`

## Deployment Notes

- Development: `python run.py`
- Docker / Procfile updated to use `run.py`
- API docs served at `/api/docs`
- Consider disabling bots in production or tuning rates via env vars.

## Known Limitations & Next Steps

- Avatar thumbnails require Pillow; without it, only originals are saved (handled gracefully)
- Profile persistence is session-first; DB updates are best-effort
- Social secure API requires proper token auth to be used in production

Planned improvements:
- [ ] Add file size limits and stricter MIME checks for avatar upload
- [ ] Ensure DB `User` upsert on demo/register flows for robust persistence
- [ ] Optional: background tasks for image processing and cleanup
- [ ] Admin toggles for bot rates and enable/disable at runtime
