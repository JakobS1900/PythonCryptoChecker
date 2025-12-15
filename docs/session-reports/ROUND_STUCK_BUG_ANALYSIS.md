# Roulette Round Stuck Bug - Analysis & Fix

## Bug Report
**Symptom**: After first round starts, timer counts down to 0 but NO new round starts. System is stuck on Round 1 forever.

**Date**: 2025-10-20
**Severity**: CRITICAL - Breaks entire roulette system
**Status**: INVESTIGATING

## Root Cause Analysis

### Issue #1: Import Error (FIXED)
**File**: `gaming/round_manager.py` line 375
**Problem**: Wrong import path `from services.portfolio_manager import portfolio_manager`
**Fix Applied**: Changed to `from crypto.portfolio_manager import portfolio_manager`

**Impact**: When round tried to spin and process bets, it crashed with:
```
[Round Manager] Timer error: No module named 'services.portfolio_manager'
```

This prevented:
- Bet processing
- Round completion
- New round starting

### Issue #2: Silent Task Crash (INVESTIGATING)
**File**: `gaming/round_manager.py` lines 258-290
**Problem**: Background timer task `auto_advance_timer()` may be crashing silently

**Evidence**:
- Log shows: `[Round Manager] Background timer started`
- But NO subsequent timer messages after 20+ seconds
- Timer should print `[Round Manager] Timer expired - auto-spinning round...` every 15 seconds

**Hypothesis**: The asyncio task is either:
1. Crashing silently (exception swallowed)
2. Not executing at all (event loop issue)
3. Stuck in an infinite await

## Investigation Steps Taken

1. Checked server logs - import error found and fixed
2. Restarted server - Round 12704 started successfully
3. Waited 20 seconds - NO timer expiration message
4. Checked `auto_advance_timer()` code - appears correct
5. Verified asyncio.create_task() call - appears correct

## Current Status

Server restarted with import fix. Round 12704 started but timer is not firing.

**Next Steps**:
1. Add debug logging to `auto_advance_timer()` loop
2. Check if task is actually being scheduled
3. Verify datetime comparison logic
4. Check for deadlocks on `self._lock`
5. Test with Playwright to see frontend behavior

## Files Modified

- `gaming/round_manager.py` line 375 - Fixed import path
- (Pending) Add debug logging to timer loop

## Testing Plan

1. Add extensive logging to timer loop
2. Restart server and monitor logs
3. Use Playwright to watch round progression
4. Place test bets and verify processing
5. Monitor for 2-3 rounds to confirm stability
