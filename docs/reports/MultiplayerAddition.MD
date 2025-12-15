## Multiplayer System Proposal and Integration Plan

This document outlines a safe, incremental path to introduce multiplayer features into the existing CryptoChecker gaming/gamification platform. It focuses on backend-first changes to avoid conflicts with the ongoing UI overhaul. It reuses current models (users, friendships, leaderboards, achievements) and adds clearly-scoped new models and APIs.

---

### Goals
- Real-time peer play (rooms/matches) for crypto-themed games
- Async competition modes (tournaments/challenges) that fit daily use
- Minimal surface area changes to UI; feature-flagged APIs first
- Reuse social graph, achievements, leaderboards, notifications

---

### Phase 0: Foundations (now)
- Add profile avatar upload (done): POST `/api/profile/avatar` → stores image in `web/static/uploads/avatars`, updates `User.avatar_url`.
- Document and enable feature flags for multiplayer endpoints (without UI hooks).

Config keys (example in `.env`):
- `FEATURE_MULTIPLAYER=true`
- `FEATURE_TOURNAMENTS=true`
- `FEATURE_PRESENCE=true`

---

### Phase 1: Data Model Additions (backend-only)

Proposed new tables (SQLAlchemy models), all linking to existing `User`:

- Match: a game instance players join
  - id, game_type, status (WAITING, ACTIVE, COMPLETED, CANCELLED)
  - created_at, started_at, completed_at
  - room_code (for invites), metadata JSON

- MatchParticipant: player membership per match
  - id, match_id (FK), user_id (FK), join_time, leave_time
  - team_id (nullable), is_host, score, result (WIN/LOSS/DRAW)

- MatchEvent: immutable event log for provable fairness and replay
  - id, match_id, type, payload JSON, created_at

- Party (optional for pre-made teams)
  - id, owner_user_id, name, invite_code, is_open, created_at
  - PartyMember: party_id, user_id, role (owner/member)

- Presence (optional if not using external cache)
  - id, user_id, status (ONLINE, IN_MATCH, OFFLINE), last_seen, current_match_id

No changes to existing `User` required, but we will integrate with:
- Achievements: new triggers (match_won, streak, teamplay, tournaments)
- Leaderboards: new types (ELO/MMR, wins, streaks)
- Notifications: invites, match start, results, rewards

Schema changes should be in a separate migration file; do not run on prod until ready.

---

### Phase 2: API Surface (backend-first, no UI coupling)

Base router: `/api/multiplayer` (feature-flag protected)

- Matchmaking
  - POST `/queue/join` {game_type, skill_hint?} → returns ticket id
  - POST `/queue/leave` {ticket_id}
  - GET `/queue/status` → ticket state

- Rooms/Matches
  - POST `/matches` {game_type, visibility, max_players} → creates match room (hosted)
  - POST `/matches/{id}/join` → join
  - POST `/matches/{id}/leave`
  - POST `/matches/{id}/start` (host only)
  - GET `/matches/{id}` → state, players, status
  - WS `/ws/matches/{id}` → real-time updates (join/leave, ticks, results)

- Parties (optional, later)
  - POST `/parties` → create
  - POST `/parties/{id}/invite` {username}
  - POST `/parties/{id}/join` {invite_code}
  - POST `/parties/{id}/leave`

Security: all endpoints require auth; host-only actions enforced; rate limits applied.

---

### Phase 3: Realtime Transport

Transport options (incremental):
- Start: FastAPI WebSocket per-match channel (already used for price stream)
- Later: add Redis pub/sub for scalability (optional), room fanout per match id

Message patterns:
- Server → clients: state_snapshot, player_joined, player_left, tick, action_result, match_end
- Client → server: ready, place_bet/action, chat (optional), leave

Reliability: Use event log (MatchEvent) as source of truth; recover state on reconnect with snapshot + events since `last_event_id`.

---

### Phase 4: Game Modes

1) Synchronous Quick Match (2–8 players)
- Example: “Price Prediction Blitz” → each round predict next 30s candle direction; scoring per round; most points wins
- Hooks: achievements (multi_wins, streaks), leaderboards (wins, ELO)

2) Weekly Tournament (async)
- Entrants play N matches during period; best average score qualifies
- Rewards auto-granted via VirtualTransaction + items

3) Cooperative Party Challenges (optional)
- Parties complete objectives over 24h (e.g., group XP, win targets) for rewards

All modes share: provably-fair seeds per match, event logs, anti-cheat checks server-side.

---

### Phase 5: Integration with Existing Systems

- Achievements: extend triggers in `achievements/achievement_engine.py` for:
  - `match_won`, `match_participated`, `win_streak`, `team_victory`, `tournament_rank`

- Leaderboards: add calculations for
  - wins (all-time/weekly), ELO/MMR, longest streak

- Social: friend invites to matches; activity feed entries on wins/trophies

- Notifications: match invites, start countdowns, results, tournament standings

---

### Phase 6: UI (deferred until Claude’s overhaul is settled)

Backend-first rollout. Minimum UI hooks:
- Social page: “Invite to match” button → calls `/api/multiplayer/matches` then shares join link
- Simple modal to show room code and participants (later)

Avoid touching shared templates until Claude’s work lands. Provide API docs + example cURL during interim.

---

### Security, Fairness, and Abuse Controls
- Rate limit lobby actions; auth required everywhere
- Server-authoritative results; verify actions server-side
- Provably fair: server_seed/server_seed_hash + client_seed + nonce per match
- Anti-collusion signals: unusual win rates, repeated pairings
- Privacy: honor `profile_public`, `allow_friend_requests`

---

### Step-by-Step Execution Checklist
1. Migrations: add Match/MatchParticipant/MatchEvent (and optional Party/Presence)
2. Router: `/api/multiplayer` with room + matchmaking endpoints (feature-flagged)
3. WebSocket channel and server-side match loop scaffold
4. Achievements: wire new triggers
5. Leaderboards: add wins + streak rankings
6. Notifications + activity feed entries
7. Minimal UI hooks post-UI overhaul

---

### Example API Usage (Interim)

Upload avatar (already implemented):
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/avatar.png" \
  http://localhost:8000/api/profile/avatar

Create a match room:
POST /api/multiplayer/matches {"game_type":"PRICE_PREDICTION","visibility":"private","max_players":4}

Join a match:
POST /api/multiplayer/matches/{match_id}/join

WebSocket join:
ws://localhost:8000/api/multiplayer/ws/matches/{match_id}

---

### Rollback Plan
- All new features behind env flags; disabling flags closes routes
- Migrations are additive; safe to roll forward only in dev until stable

---

### Notes for Other LMs
- Please avoid editing shared templates until the UI overhaul is merged
- Prefer adding backend endpoints and documenting usage here
- Coordinate schema changes via a migration file in `database/` and update this doc

