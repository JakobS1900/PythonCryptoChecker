# CryptoChecker V3 - Comprehensive Bug Report & Testing Guide

**Date:** November 3, 2025
**Test Account:** Emu / EmuEmu
**Priority Issues:** Roulette 100K Bet & Trading Features

---

## Executive Summary

This document provides a comprehensive testing strategy and bug identification guide for the CryptoChecker V3 platform, with special focus on the user-reported issues:
1. **100K GEM bet issue on roulette** (Critical Priority)
2. **Trading features not working well** (High Priority)

---

## Test Execution Plan

### **Phase 1: Authentication & Core Systems**

#### Test 1.1: Login Authentication
**Steps:**
1. Navigate to `http://localhost:8000/login`
2. Enter username: `Emu`
3. Enter password: `EmuEmu`
4. Click "Login"

**Expected Results:**
- Redirect to homepage or dashboard
- JWT token stored in localStorage (`access_token`)
- User balance displayed in navbar/header
- No console errors

**Check for Issues:**
- Login form validation
- JWT token expiration handling
- Session management
- Redirect loops

---

### **Phase 2: Roulette Game Testing (CRITICAL PRIORITY)**

User reported: **Cannot place 100K GEM bet**

#### Test 2.1: 100K GEM Bet on RED
**Steps:**
1. Navigate to `/gaming`
2. Enter bet amount: `100000`
3. Click "RED" button
4. Observe result

**What to Check:**
- Does bet input accept 100,000?
- Is there a max bet limit lower than 100K?
- Does the bet  actually place or does it fail silently?
- Any console errors?
- Network request status (check DevTools Network tab)

**Possible Issues to Document:**
- Input validation preventing large amounts
- Backend bet limit lower than expected
- JavaScript number handling issues
- Balance check failing incorrectly
- Race condition in bet placement

#### Test 2.2: Various Bet Amounts
**Test these amounts:**
- 10,000 GEM
- 50,000 GEM
- 75,000 GEM
- 100,000 GEM
- 125,000 GEM
- MAX button

**Document for each:**
- Bet accepted? (Y/N)
- Error message (if any)
- Actual bet placed vs. intended
- Console errors
- Network failures

#### Test 2.3: Game Flow
**Check:**
- Bet placement confirmation
- Spin animation
- Result display
- Balance update after win/loss
- Multiple consecutive bets

---

### **Phase 3: Trading Features Testing (HIGH PRIORITY)**

User reported: **Trading features not working well**

#### Test 3.1: Stock Market (`/stocks`)

**Interface Loading:**
- Does page load without errors?
- Are stock listings displayed?
- Do prices update/display correctly?
- Console errors?

**Buying Stocks:**
1. Click "Buy" on any stock
2. Enter amount: `1`
3. Confirm purchase

**Check:**
- Buy modal/form opens?
- Amount input works?
- Confirm button functional?
- Success/error feedback?
- Balance deducted correctly?
- Stock added to portfolio?
- Network request succeeds? (Check DevTools)

**Selling Stocks:**
1. Click "Sell" on owned stock
2. Enter amount
3. Confirm sale

**Check:**
- Sell modal/form opens?
- Can sell partial amounts?
- Balance credited correctly?
- Portfolio updated?
- Network request succeeds?

**Common Issues to Look For:**
- API endpoints returning 404/500 errors
- Missing authentication headers
- Balance not updating
- Portfolio not reflecting trades
- Price data not loading
- Transaction history not recording

#### Test 3.2: Staking (`/staking`)

**Interface Loading:**
- Page loads without errors?
- Staking options displayed?
- APY/rewards visible?

**Staking GEM:**
1. Select staking duration
2. Enter amount to stake
3. Confirm stake

**Check:**
- Staking form works?
- GEM deducted from balance?
- Staked amount shown?
- Rewards calculating?
- Unstaking works?

**Common Issues:**
- Staking duration options missing
- Rewards not calculating
- Cannot unstake
- Minimum stake amount unclear

#### Test 3.3: P2P Trading (`/trading`)

**Check:**
- Trading interface loads?
- Order book displays?
- Can create buy/sell orders?
- Orders execute properly?
- Trade history visible?

---

### **Phase 4: Core Features**

#### Test 4.1: Crypto Prices (`/`)
- Price cards load
- Real-time updates work
- Prices accurate
- No console errors

#### Test 4.2: Portfolio (`/portfolio`)
- Portfolio displays correctly
- Holdings shown
- Total value calculated
- Performance metrics visible

#### Test 4.3: Currency Converter (`/converter`)
- Converter interface loads
- Currency selection works
- Conversion calculations correct
- Exchange rates update

#### Test 4.4: GEM Store (`/gem-store`)
- Store interface loads
- Package options displayed
- Purchase flow works (if test mode available)

#### Test 4.5: Achievements (`/achievements`)
- Achievements list loads
- Progress tracked
- Claim rewards works
- Achievement notifications

#### Test 4.6: Daily Bonus
- Daily bonus button visible
- Can claim bonus
- Cooldown timer works
- GEM credited correctly

---

## Manual Testing Checklist

### Before Each Test
- [ ] Clear browser cache/cookies
- [ ] Open DevTools (F12)
- [ ] Enable "Preserve log" in Console
- [ ] Switch to Network tab
- [ ] Login as Emu/EmuEmu

### During Tests
- [ ] Note any console errors (red messages)
- [ ] Check Network tab for failed requests (red status)
- [ ] Screenshot any error messages
- [ ] Record current balance before/after transactions
- [ ] Note exact error messages

### Error Documentation Format
For each bug found, document:

```
BUG #X: [Short Description]
-------------------
Feature: [Roulette/Stocks/Staking/etc.]
Severity: [Critical/High/Medium/Low]
Steps to Reproduce:
1.
2.
3.

Expected Result:
[What should happen]

Actual Result:
[What actually happens]

Console Errors:
[Paste exact error messages]

Network Errors:
[HTTP status, endpoint, error response]

Screenshots:
[File names or paths]

User Impact:
[How this affects users]

Suggested Fix:
[If obvious]
```

---

## Known Areas to Investigate

### Roulette 100K Bet Issue - Likely Causes:

1. **Frontend Input Validation**
   - File: `web/static/js/roulette.js`
   - Check for: `max` attribute on input, JS validation
   - Look for: Input clamping, number formatting

2. **Backend Bet Limits**
   - File: `api/gaming_api.py`
   - Check: `place_bet` endpoint
   - Look for: MAX_BET_AMOUNT constant
   - Verify: Balance checking logic

3. **Round Manager**
   - File: `gaming/round_manager.py`
   - Recent changes suggest this was modified
   - Check: Bet validation in round processing

4. **Database Constraints**
   - File: `database/models.py`
   - Check: Bet amount column type/constraints

### Trading Issues - Likely Causes:

1. **API Routing**
   - File: `main.py` shows `trading_router` included twice (lines 155-157 and 187-191)
   - This could cause routing conflicts
   - Check if endpoints accessible

2. **Authentication**
   - Check if trading endpoints require auth
   - Verify JWT token passed correctly
   - Look for 401/403 errors

3. **Stock API**
   - File: `api/stocks_api.py`
   - Check buy/sell endpoint logic
   - Verify portfolio updates

4. **Database Transactions**
   - Check if trades commit to database
   - Verify balance updates atomic
   - Look for transaction rollbacks

---

## Critical Files to Examine

### Roulette System:
- `web/static/js/roulette.js` - Frontend logic
- `api/gaming_api.py` - API endpoints
- `gaming/round_manager.py` - Server-side round logic
- `web/templates/gaming.html` - UI template

### Trading System:
- `api/stocks_api.py` - Stock trading endpoints
- `api/staking_api.py` - Staking endpoints
- `api/trading_api.py` - P2P trading endpoints
- `web/static/js/stocks.js` (if exists) - Frontend logic

### Authentication:
- `api/auth_api.py` - Auth endpoints
- `web/static/js/auth.js` - JWT handling

---

## Expected Test Results Location

After running `test_platform_comprehensive.py`:
- **Results JSON:** `test_results.json`
- **Screenshots:** `test_screenshots/` directory
- **Videos:** `test_videos/` directory

---

## Quick Console Commands for Debugging

### Check if server is running:
```bash
curl http://localhost:8000/api
```

### Check authentication:
```bash
curl -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"username":"Emu","password":"EmuEmu"}'
```

### Check gaming endpoint:
```bash
curl http://localhost:8000/api/gaming/round-info -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Check stock listings:
```bash
curl http://localhost:8000/api/stocks/ -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## Browser DevTools - What to Look For

### Console Tab:
- **Red errors:** JavaScript exceptions
- **Yellow warnings:** Non-critical issues
- **Network errors:** Failed API calls

### Network Tab:
- **Red status codes:** 4xx (client error) or 5xx (server error)
- **Pending requests:** Requests that never complete
- **Failed requests:** Connection refused, timeout

### Application Tab:
- **localStorage:** Check for `access_token`
- **Cookies:** Check session cookies
- **Session Storage:** Check temporary data

---

## Testing Best Practices

1. **Test in Order:** Authentication → Roulette → Trading → Other Features
2. **Document Everything:** Screenshot errors, save console logs
3. **Test Edge Cases:** Minimum bets, maximum bets, zero amounts, negative numbers
4. **Verify Balance:** Check balance before and after each transaction
5. **Clear State:** Logout/login between major test phases
6. **Multiple Attempts:** Try failing operations 2-3 times to confirm consistency

---

## Automated Test Script

The comprehensive Playwright test script has been created at:
`test_platform_comprehensive.py`

**To run:**
```bash
python test_platform_comprehensive.py
```

**Features:**
- Tests all 10 major features
- Captures screenshots at each step
- Records console errors
- Tracks network failures
- Generates JSON report
- Records video of entire test session

---

## Next Steps

1. **Run Automated Tests:**
   - Execute `test_platform_comprehensive.py`
   - Review `test_results.json`
   - Examine screenshots in `test_screenshots/`

2. **Manual Verification:**
   - For any failed automated tests, verify manually
   - Test edge cases not covered by automation
   - Document detailed reproduction steps

3. **Bug Fixing Priority:**
   - **P0 (Critical):** Roulette 100K bet issue
   - **P1 (High):** Stock market trading issues
   - **P1 (High):** Staking functionality
   - **P2 (Medium):** Other trading features
   - **P3 (Low):** UI/UX improvements

4. **Code Review:**
   - Review recent changes to `gaming/round_manager.py`
   - Check for duplicate router registrations in `main.py`
   - Verify bet limit constants across frontend/backend

---

## Contact/Questions

For questions about this testing guide or to report findings:
- Review test results in `test_results.json`
- Check screenshots for visual evidence
- Examine console output for technical details

---

**Remember:** The goal is to identify exact reproduction steps, error messages, and affected code areas for each bug. Be thorough and document everything!
