# Manual Testing Guide - October 27, 2025 Updates

## 🎯 Features to Test

1. **Token Expiration Handling** (Phase 3)
2. **Accessibility Improvements** (Phase 4)
3. **Roulette Error Handling** (Phase 2)

---

## 🧪 Test Suite 1: Token Expiration Handling

### Prerequisites
- Clear browser cache and localStorage
- Server running on http://localhost:8000

### Test 1.1: Token Renewal Monitor Setup
**Steps**:
1. Open http://localhost:8000 in browser
2. Open DevTools Console (F12)
3. Login with valid credentials (or register new account)
4. Look for console message: `⏰ Token expires in XX minutes`
5. Look for: `⏰ Token renewal scheduled in XX minutes`

**Expected Results**:
✅ Console shows token expiration time
✅ Renewal scheduled at 75% of lifetime
✅ Warning scheduled at 90% of lifetime
✅ No errors in console

---

### Test 1.2: Manual Token Refresh
**Steps**:
1. After logging in, open Console
2. Type: `Auth.renewToken()`
3. Wait for response

**Expected Results**:
✅ Console: `🔄 Attempting proactive token renewal...`
✅ Console: `✅ Token renewed successfully. New expiration: [timestamp]`
✅ New token stored in localStorage
✅ No page reload required
✅ User balance updated

---

### Test 1.3: Token Expiration Simulation
**Steps**:
1. Login to application
2. Open DevTools → Application → Local Storage
3. Delete `auth_token` and `auth_token_data`
4. Try to perform any action (e.g., view profile)

**Expected Results**:
✅ Toast notification: "Your session has expired. Please log in again."
✅ Smooth transition to guest mode
✅ No errors or broken UI
✅ Can continue as guest or re-login

---

## 🧪 Test Suite 2: Accessibility Improvements

### Test 2.1: Loading State ARIA Attributes
**Steps**:
1. Navigate to GEM Store page
2. Open DevTools → Elements
3. Click "Purchase" on any package
4. Inspect the button while loading

**Expected Results**:
✅ Button shows: `<span class="spinner-border spinner-border-sm" role="status"></span> Processing...`
✅ Button is disabled during loading
✅ Screen reader announces loading state

---

### Test 2.2: Stock Purchase Loading State
**Steps**:
1. Navigate to Stocks page
2. Click on any stock
3. Click "Buy" button
4. Inspect button during loading

**Expected Results**:
✅ Button shows: `<span ... role="status"></span> Buying...`
✅ Screen reader compatible
✅ Button disabled during operation

---

### Test 2.3: Toast Notifications (No More Alerts)
**Steps**:
1. Navigate through app and trigger various actions
2. Watch for notifications
3. Check console for any `alert()` calls

**Expected Results**:
✅ All notifications use Toast (top-right corner)
✅ No browser alert() dialogs
✅ Toast auto-dismisses after few seconds
✅ Can manually dismiss with X button

---

## 🧪 Test Suite 3: Roulette Error Handling

### Test 3.1: Connection Status Indicator
**Steps**:
1. Navigate to Roulette game (Gaming page)
2. Wait for game to load
3. Look in top-right corner for connection indicator

**Expected Results**:
✅ Initially shows "✓ Connected" (green)
✅ Auto-hides after 2 seconds
✅ Position: Fixed top-right corner

---

### Test 3.2: Network Failure Simulation
**Steps**:
1. Open Roulette game
2. Open DevTools → Network tab
3. Set throttling to "Offline"
4. Try to place a bet
5. Wait a few seconds
6. Set throttling back to "No throttling"

**Expected Results**:
✅ Bet fails after 3 retry attempts
✅ Connection indicator shows "✗ Connection Lost" (red)
✅ Toast notification: "Connection lost. Attempting to reconnect..."
✅ After network restored: "Connection restored!" (green toast)
✅ Game state refreshes automatically
✅ Can place bets again

---

### Test 3.3: Request Timeout
**Steps**:
1. Open Roulette game
2. Open DevTools → Network tab
3. Right-click any request → "Block request URL" (to simulate slow server)
4. Try to place a bet
5. Wait 10+ seconds

**Expected Results**:
✅ Request times out after 10 seconds
✅ Error message: "Request timed out. Please check your connection."
✅ Connection status: "Reconnecting..." (yellow)
✅ Balance not deducted
✅ Can retry bet

---

### Test 3.4: Bet Placement with Network Issues
**Steps**:
1. Open Roulette game
2. Note current balance
3. Open DevTools → Network → Set to "Slow 3G"
4. Place a bet
5. Switch network back to normal

**Expected Results**:
✅ Bet request may timeout initially
✅ Automatic retry attempts (up to 3 times)
✅ If all retries fail: balance not deducted
✅ Clear error message shown
✅ If retry succeeds: bet placed successfully

---

### Test 3.5: Balance Rollback Protection
**Steps**:
1. Open Roulette game
2. Note current balance
3. Open Console
4. Simulate failed bet by entering:
   ```javascript
   game.balance = game.balance - 100; // Manually deduct
   // Then trigger a bet that will fail
   ```
5. Use DevTools to force bet API to fail

**Expected Results**:
✅ Console: `⚠️ Balance mismatch detected! Rolling back...`
✅ Balance restored to original amount
✅ Error message: "Failed to place bet. Balance has been restored."
✅ No phantom balance deduction

---

### Test 3.6: Connection Loss During Active Game
**Steps**:
1. Open Roulette game
2. Place a bet and wait for round to start spinning
3. During spin: Open DevTools → Network → Set to "Offline"
4. Wait 15 seconds
5. Set network back to "No throttling"

**Expected Results**:
✅ Polling stops during offline period
✅ After 10s: Connection indicator shows "Connection Lost"
✅ After network restored: Automatic reconnection
✅ Toast: "Connection restored!"
✅ Game state syncs (shows current round)
✅ If spin completed: results shown correctly

---

### Test 3.7: Authentication Error in Roulette
**Steps**:
1. Login and open Roulette
2. Open DevTools → Application → Local Storage
3. Delete `auth_token`
4. Try to place a bet

**Expected Results**:
✅ API returns 401 Unauthorized
✅ Error handler detects auth error
✅ Toast: "Your session has expired. Please log in again."
✅ Auth.handleTokenExpiration() is triggered
✅ Smooth transition to guest mode
✅ No game crashes

---

### Test 3.8: Multiple Bet Failures
**Steps**:
1. Open Roulette game
2. Open DevTools → Network → Set to "Offline"
3. Try to place 3 bets in a row
4. Set network back to "No throttling"

**Expected Results**:
✅ First bet: Fails with retry attempts
✅ Second bet: Fails with retry attempts
✅ Third bet: Triggers "checking connection..."
✅ Connection status updates to "Reconnecting"
✅ After network restored: Can place bets normally

---

## 🧪 Test Suite 4: Integration Testing

### Test 4.1: Token Renewal + Roulette Gaming
**Steps**:
1. Login to application
2. Open Roulette game
3. Play for 45+ minutes (or reduce token lifetime in .env for faster testing)
4. Watch console for token renewal
5. Continue playing after renewal

**Expected Results**:
✅ Token automatically renewed at 45 min mark
✅ No interruption to gameplay
✅ No re-authentication required
✅ Game continues seamlessly

---

### Test 4.2: Network Issues + Token Expiration
**Steps**:
1. Login to application
2. Open Roulette game
3. Simulate network issues (offline mode)
4. Wait for token to expire (or delete it)
5. Restore network

**Expected Results**:
✅ Auth error detected before network issues
✅ Clear expiration message shown
✅ After network restored: prompted to login
✅ Can login and resume gaming

---

### Test 4.3: Cross-Browser Compatibility
**Test in**: Chrome, Firefox, Edge

**Steps**:
1. Open application in each browser
2. Test token renewal
3. Test roulette error handling
4. Test toast notifications

**Expected Results**:
✅ All features work in all browsers
✅ Connection indicator displays correctly
✅ Toasts appear in correct position
✅ No browser-specific errors

---

## 📋 Testing Checklist

Use this checklist to track your testing:

### Token Expiration Handling
- [ ] Token renewal monitor setup
- [ ] Manual token refresh works
- [ ] Token expiration simulation
- [ ] Warning notification appears
- [ ] Graceful logout on expiration

### Accessibility
- [ ] GEM store loading state has role="status"
- [ ] Stock purchase loading state has role="status"
- [ ] All notifications use Toast (no alert())
- [ ] Screen reader compatibility

### Roulette Error Handling
- [ ] Connection status indicator shows/hides
- [ ] Network failure detected and recovered
- [ ] Request timeout works (10s)
- [ ] Bet placement retries automatically
- [ ] Balance rollback protection works
- [ ] Connection loss during game handled
- [ ] Auth error triggers proper logout
- [ ] Multiple failures trigger reconnection

### Integration
- [ ] Token renewal + gaming works together
- [ ] Network issues + expiration handled
- [ ] Cross-browser compatibility verified

---

## 🐛 If You Find Issues

### Reporting Format
```
**Issue**: Brief description
**Test**: Which test suite and step
**Expected**: What should happen
**Actual**: What actually happened
**Browser**: Chrome/Firefox/Edge + version
**Console Errors**: Any errors from console
**Steps to Reproduce**: Detailed steps
```

### Quick Fixes

**Issue**: Connection indicator not showing
- **Check**: DevTools console for JavaScript errors
- **Check**: Is roulette game initialized? (`window.game` should exist)

**Issue**: Token not renewing
- **Check**: Is user authenticated? (`Auth.isAuthenticated === true`)
- **Check**: Console logs for `⏰ Token renewal scheduled...`
- **Check**: localStorage has `auth_token_data`

**Issue**: Toasts not appearing
- **Check**: Is `Toast` object available? (`window.Toast`)
- **Check**: Check for CSS conflicts
- **Check**: Console for Toast errors

---

## ✅ Success Criteria

### All Tests Pass If:
1. ✅ Token renewal works automatically (no manual intervention)
2. ✅ Connection issues detected and recovered gracefully
3. ✅ All error messages are user-friendly (no technical jargon)
4. ✅ Game balance protected (no phantom deductions)
5. ✅ No browser alert() dialogs (all Toast)
6. ✅ Connection status indicator visible and accurate
7. ✅ No console errors during normal operation
8. ✅ Screen readers can access all interactive elements

---

## 🚀 Quick Start Testing

**Fastest way to test everything**:

```bash
# 1. Ensure server is running
# Check: http://localhost:8000

# 2. Open browser with DevTools (F12)

# 3. Test token expiration (5 minutes):
#    - Login
#    - Watch console for token renewal messages
#    - Manually call: Auth.renewToken()
#    - Delete auth_token and trigger action

# 4. Test roulette errors (10 minutes):
#    - Open roulette game
#    - Go offline, place bet, go online
#    - Block network requests, place bet
#    - Delete auth_token, place bet

# 5. Test accessibility (2 minutes):
#    - Go to GEM store, purchase package
#    - Go to stocks, buy stock
#    - Verify loading spinners have role="status"

# Total: ~20 minutes for comprehensive testing
```

---

**Happy Testing!** 🧪🚀

Found an issue? Let me know and I'll help fix it immediately!
