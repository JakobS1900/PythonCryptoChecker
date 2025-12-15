# Server-Managed Roulette Rounds - Testing Guide

## 🎉 Implementation Complete!

Your CryptoChecker roulette game now uses **server-managed rounds** instead of client-side timer loops. This fixes all the synchronization issues you were experiencing.

---

## What Was Implemented

### ✅ Backend (Complete)
1. **Database Schema** - `roulette_rounds` table created
2. **Round Manager** - Auto-advancing rounds every 15 seconds
3. **SSE Endpoints** - Real-time round state broadcasting
4. **API Integration** - Round validation and spin triggers

### ✅ Frontend (Complete)
1. **SSE Client** - Connects to server round stream
2. **Event Handlers** - Responds to round phase changes
3. **Server-Synced Timer** - Timer syncs from server timestamps
4. **Phase-Based UI** - Betting/spinning/results controlled by server

---

## How to Test

### 1. **Start the Server**

The server is currently running on `http://localhost:8000` (background shell: 4dfd04)

### 2. **Open the Roulette Game**

Navigate to: **`http://localhost:8000/gaming`**

### 3. **What You Should See**

#### **When Page Loads:**
- Browser console shows: `[SSE] Connecting to server round stream...`
- Followed by: `[SSE] Connection established`
- Then: `[SSE] Current round state: {...}` with round number and timer

#### **During Betting Phase (15 seconds):**
- "Place Your Bets" message displayed
- Countdown timer shows remaining time (synchronized from server)
- Bet buttons are enabled
- Bots place visual bets throughout the phase

#### **When You Place a Bet:**
- Spin button enables immediately
- Your bet appears in "Active Bets"
- Balance deducts correctly

#### **When Timer Expires OR You Click Spin:**
- Console shows: `[SSE] Phase changed: {...}`
- Betting buttons disable immediately
- Wheel spins with server-provided outcome
- "Wheel Spinning..." message appears

#### **After Spin Completes:**
- Console shows: `[SSE] Round results: {...}`
- Results displayed for 2-3 seconds
- Console shows: `[SSE] Round ended: {...}`
- Followed by: `[SSE] Round started: {...}` (new round begins)

### 4. **Test Scenarios**

#### **Scenario A: Manual Spin**
1. Wait for new round to start (timer resets)
2. Place a bet (any amount, any number/color)
3. Click "SPIN TO WIN" button before timer expires
4. Watch wheel spin with server outcome
5. See results, then auto-start new round
6. **Expected**: Seamless transition, no "Round Complete" stuck messages

#### **Scenario B: Auto-Spin (Timer Expiration)**
1. Wait for new round
2. DON'T place any bets
3. Let the 15-second timer run to 0
4. **Expected**: Round auto-restarts without errors

#### **Scenario C: Multiple Rounds**
1. Place bet → Spin → Watch results
2. Immediately place another bet in new round
3. Spin again
4. Repeat 3-5 times
5. **Expected**: No page refresh needed, works continuously

#### **Scenario D: Mid-Round Join**
1. Open roulette page while a round is already in progress
2. **Expected**: Page syncs to current round state (may show "Round in progress...")
3. Wait for next round to place bets normally

---

## What to Look For (Success Indicators)

### ✅ **Fixed Issues:**
- ✅ "Round Complete" message clears properly when new round starts
- ✅ Timer and game state stay synchronized
- ✅ Bets don't disappear unexpectedly
- ✅ Spin button enables/disables correctly
- ✅ No need to refresh page between rounds
- ✅ Bot activity syncs with round phases

### ✅ **Console Logs (Normal Operation):**
```
[SSE] Connection established
[SSE] Current round state: { round_number: 115, phase: "betting", time_remaining: 12.4 ... }
[SSE] Round started: { round_id: "...", round_number: 116, ... }
[SSE] Phase changed: { phase: "SPINNING", outcome: 17, color: "black" }
[SSE] Round results: { outcome: 17, color: "black", crypto: "TRX" }
[SSE] Round ended: { round_id: "..." }
[SSE] Round started: { round_number: 117, ... }  ← New round auto-starts
```

---

## Troubleshooting

### Issue: "SSE Connection error"
**Solution**:
- Check server is running (`http://localhost:8000/api/gaming/roulette/round/current`)
- Browser will auto-fallback to polling every 2 seconds
- SSE will retry reconnection 5 times

### Issue: Timer not syncing
**Solution**:
- Check browser console for SSE events
- Verify server time vs. client time (should be within 1 second)
- Hard refresh page (Ctrl+F5)

### Issue: Bets not placing
**Solution**:
- Check console for error messages
- Verify you're logged in
- Check balance is sufficient
- Ensure round phase is "betting" (not "spinning")

### Issue: Wheel doesn't spin
**Solution**:
- Check network tab for `/round/spin` API call
- Verify SSE connection is active
- Try hard refresh (Ctrl+F5)

---

## API Endpoints (For Testing)

### Check Current Round State:
```bash
curl http://localhost:8000/api/gaming/roulette/round/current
```

**Expected Response:**
```json
{
  "success": true,
  "round": {
    "round_id": "...",
    "round_number": 120,
    "phase": "betting",
    "time_remaining": 8.234,
    "betting_duration": 15,
    "outcome": null
  }
}
```

### Monitor SSE Stream (Command Line):
```bash
curl -N http://localhost:8000/api/gaming/roulette/round/stream
```

**Expected Output:**
```
event: round_current
data: {"round_id":"...","round_number":120,...}

event: phase_changed
data: {"phase":"SPINNING","outcome":25,...}

event: round_results
data: {"outcome":25,"color":"red",...}
```

---

## Success Criteria

**Your implementation is working if:**

1. ✅ You can play multiple rounds without refreshing
2. ✅ Timer counts down and syncs across browser tabs (try opening 2 tabs!)
3. ✅ "Round Complete" message clears automatically
4. ✅ Bets clear at start of new round, not mid-round
5. ✅ Spin button works consistently
6. ✅ No stuck states or frozen UI

---

## Next Steps (Optional Enhancements)

These were documented in the spec but not yet implemented:

- **Multi-Player Display**: Show real players' bets (currently only bots are visual)
- **Round History**: Last 100 rounds with outcomes
- **Hot/Cold Numbers**: Track which numbers hit frequently
- **Fast Rounds**: Configurable round duration (5s, 10s, 15s)
- **Tournament Mode**: Scheduled high-stakes rounds

---

## Files Modified

### Backend:
- `database/models.py` - Added RouletteRound model, RoundPhase enum
- `gaming/round_manager.py` - **NEW** Round manager service (350 lines)
- `api/gaming_api.py` - Added 3 SSE endpoints
- `main.py` - Initialize round manager on startup

### Frontend:
- `web/static/js/roulette.js` - Added SSE client (~200 lines)

### Database:
- Migration created `roulette_rounds` table
- Added `game_bets.round_id` column

---

## Documentation

Full specification and implementation plan available at:
- **Spec**: `.specify/specs/002-server-managed-rounds/spec.md`
- **Plan**: `.specify/specs/002-server-managed-rounds/plan.md`

---

## Support

**If you encounter issues:**
1. Check browser console for errors
2. Check server logs (background shell: 4dfd04)
3. Hard refresh browser (Ctrl+F5)
4. Restart server if needed

**The server is currently running and ready to test!**

Open `http://localhost:8000/gaming` and enjoy your synchronized roulette experience! 🎰
