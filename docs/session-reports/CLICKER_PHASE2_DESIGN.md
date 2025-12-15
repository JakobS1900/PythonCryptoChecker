# GEM Clicker System - Phase 2 Design Document

## Overview
Phase 2 adds advanced idle game mechanics: Prestige System, Power-ups, Daily Challenges, Leaderboards, and Visual Customization.

---

## 1. Prestige System

### Concept
Players can "prestige" (reset progress) in exchange for permanent bonuses and special currency.

### Mechanics

#### Prestige Points (PP)
- Earned based on total GEM accumulated before reset
- Formula: `PP = floor(sqrt(total_gems_earned / 100000))`
- Example: 1,000,000 GEM earned = 3 PP
- Example: 10,000,000 GEM earned = 10 PP

#### What Gets Reset
- Current GEM balance → 0
- All upgrade levels → 1
- Current energy → 100
- Total clicks → 0
- Current combo → 0
- Auto-click accumulated → 0

#### What Persists
- Prestige Points (PP)
- Prestige Level (number of times prestiged)
- Total Lifetime GEM Earned (stat only)
- Achievements unlocked
- Themes unlocked
- Best combo record

#### Prestige Bonuses (Permanent)
Each Prestige Point provides:
- **+2% base click rewards** (stacks)
- **+1% energy regeneration** (stacks)
- **+5% chance for rare bonuses** (stacks)

#### Prestige Shop (Exclusive Upgrades)
Use Prestige Points to buy permanent bonuses:

1. **Click Master** (1 PP) - Start with Click Power Level 2
2. **Energy Expert** (2 PP) - Start with 120 max energy
3. **Quick Start** (3 PP) - Start with 5,000 GEM
4. **Auto Unlock** (5 PP) - Start with Bronze Auto-Clicker unlocked
5. **Multiplier Boost** (10 PP) - All multipliers +10%
6. **Prestige Master** (20 PP) - Earn 50% more PP on next prestige

#### UI Requirements
- Prestige button (only shows when eligible)
- Prestige calculator (shows PP gain)
- Confirmation modal with reset warning
- Prestige shop modal
- Prestige stats display (level, total PP, bonuses)

---

## 2. Power-ups System

### Concept
Temporary boosters that enhance gameplay for limited time or uses.

### Power-up Types

#### 1. Double Rewards (2x Multiplier)
- **Duration**: 60 seconds
- **Effect**: All click rewards doubled
- **Cost**: 10,000 GEM
- **Cooldown**: 5 minutes
- **Visual**: Golden glow on button

#### 2. Energy Refill
- **Effect**: Instantly restore energy to 100%
- **Cost**: 5,000 GEM
- **Cooldown**: 3 minutes
- **Visual**: Blue flash animation

#### 3. Auto-Click Burst
- **Duration**: 30 seconds
- **Effect**: Auto-clicker rate 5x faster
- **Cost**: 15,000 GEM
- **Cooldown**: 10 minutes
- **Visual**: Green pulsing effect

#### 4. Lucky Streak
- **Duration**: 45 seconds
- **Effect**: 50% chance for bonuses (instead of 15%)
- **Cost**: 8,000 GEM
- **Cooldown**: 8 minutes
- **Visual**: Rainbow shimmer

#### 5. Mega Combo
- **Effect**: Instantly activate 10x combo
- **Cost**: 12,000 GEM
- **Cooldown**: 15 minutes
- **Visual**: Purple explosion

### Power-up Mechanics
- Can stack multiple different power-ups
- Cannot use same power-up while active
- Cooldowns persist across sessions
- Visual timer shows remaining duration
- Audio notification when expires

### UI Requirements
- Power-up bar with 5 slots
- Active power-up indicators with timers
- Cooldown displays
- Purchase confirmation
- Visual effects overlay

---

## 3. Daily Challenges

### Concept
Daily rotating challenges that reward players for specific achievements.

### Challenge Types

#### Daily Challenges (Reset every 24 hours)
1. **Click Master** - Click 500 times
   - Reward: 5,000 GEM

2. **Combo King** - Achieve a 15x combo
   - Reward: 10,000 GEM

3. **Energy Efficient** - Earn 50,000 GEM without depleting energy
   - Reward: 8,000 GEM

4. **Speed Clicker** - Click 100 times in 60 seconds
   - Reward: 12,000 GEM

5. **Big Earner** - Earn 100,000 GEM in one session
   - Reward: 15,000 GEM

#### Weekly Challenges (Reset every 7 days)
1. **Dedication** - Click 5,000 times this week
   - Reward: 50,000 GEM + 1 PP

2. **Idle Master** - Accumulate 500,000 GEM from auto-clicker
   - Reward: 100,000 GEM + Power-up Pack

3. **Prestige Ready** - Earn 1,000,000 total GEM
   - Reward: 3 PP

### Challenge Mechanics
- 3 daily challenges active at once (random selection)
- 1-2 weekly challenges active
- Progress tracked automatically
- Claim rewards manually
- Can skip daily challenges (1 per day)

### UI Requirements
- Challenges panel/modal
- Progress bars for each challenge
- Claim reward buttons
- Timer showing reset time
- Completed challenge archive

---

## 4. Leaderboards

### Leaderboard Categories

#### 1. Total Clicks (All-Time)
- Top 100 players by lifetime clicks
- Updates in real-time

#### 2. Highest Combo
- Top 100 players by best combo achieved
- Shows current combo record

#### 3. Total GEM Earned (All-Time)
- Top 100 by lifetime GEM earnings
- Includes prestiged amounts

#### 4. Fastest 1M GEM
- Top 100 by time to earn first 1 million GEM
- Measured from account creation

#### 5. Prestige Level
- Top 100 by number of prestiges
- Shows total PP accumulated

#### 6. Daily Top Earner
- Top 100 by GEM earned today
- Resets at midnight

### Leaderboard Features
- Player's own rank highlighted
- Pagination (10 entries per page)
- Search/filter by username
- View player profiles (click username)
- Last updated timestamp
- Prize rewards for top 10

### UI Requirements
- Dedicated leaderboards page
- Category tabs
- Rank, username, score columns
- Player highlight
- Refresh button
- Prize indicators

---

## 5. Visual Themes & Customization

### Button Themes (Unlockable)

#### Free Themes
1. **Classic Blue** (Default) - Blue gradient
2. **Green Machine** - Green/emerald
3. **Purple Power** - Purple/violet

#### Unlock Requirements
4. **Golden Glory** (100,000 total clicks) - Gold/yellow
5. **Ruby Red** (1M GEM earned) - Red/crimson
6. **Diamond Shine** (Prestige Level 5) - White/silver
7. **Rainbow Burst** (Prestige Level 10) - Animated rainbow
8. **Dark Matter** (Prestige Level 20) - Black/purple animated

### Particle Effects (Unlockable)

#### Free Effects
1. **Gem Burst** (Default) - Gem emojis
2. **Stars** - Star particles

#### Unlock Requirements
3. **Fireworks** (500,000 total clicks) - Explosive particles
4. **Hearts** (100 PP total) - Heart particles
5. **Lightning** (Prestige Level 15) - Electric bolts
6. **Galaxy** (Prestige Level 25) - Cosmic particles

### Background Themes

#### Free Backgrounds
1. **Gradient Purple** (Default)
2. **Blue Ocean**
3. **Green Forest**

#### Unlock Requirements
4. **Starry Night** (1M GEM earned)
5. **Sunset** (Prestige Level 3)
6. **Aurora** (Prestige Level 10)
7. **Void** (Prestige Level 20) - Animated dark theme

### UI Requirements
- Customization menu/modal
- Theme preview
- Lock indicators for locked themes
- Apply button
- Save preferences

---

## Database Schema Changes

### New Tables

#### `clicker_prestige`
```sql
CREATE TABLE clicker_prestige (
    user_id VARCHAR(36) PRIMARY KEY,
    prestige_level INT DEFAULT 0,
    prestige_points INT DEFAULT 0,
    total_lifetime_gems FLOAT DEFAULT 0,
    last_prestige_at TIMESTAMP,
    -- Prestige shop purchases
    has_click_master BOOLEAN DEFAULT FALSE,
    has_energy_expert BOOLEAN DEFAULT FALSE,
    has_quick_start BOOLEAN DEFAULT FALSE,
    has_auto_unlock BOOLEAN DEFAULT FALSE,
    has_multiplier_boost BOOLEAN DEFAULT FALSE,
    has_prestige_master BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### `clicker_powerups`
```sql
CREATE TABLE clicker_powerups (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    powerup_type VARCHAR(50) NOT NULL, -- 'double_rewards', 'energy_refill', etc.
    activated_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### `clicker_powerup_cooldowns`
```sql
CREATE TABLE clicker_powerup_cooldowns (
    user_id VARCHAR(36) NOT NULL,
    powerup_type VARCHAR(50) NOT NULL,
    cooldown_ends_at TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, powerup_type),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### `clicker_challenges`
```sql
CREATE TABLE clicker_challenges (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    challenge_type VARCHAR(50) NOT NULL, -- 'daily_clicks', 'weekly_combo', etc.
    challenge_date DATE NOT NULL, -- For daily/weekly rotation
    progress INT DEFAULT 0,
    target INT NOT NULL,
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    claimed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### `clicker_leaderboards`
```sql
CREATE TABLE clicker_leaderboards (
    user_id VARCHAR(36) PRIMARY KEY,
    total_clicks BIGINT DEFAULT 0,
    best_combo INT DEFAULT 0,
    total_gems_earned FLOAT DEFAULT 0,
    prestige_level INT DEFAULT 0,
    daily_gems_earned FLOAT DEFAULT 0,
    daily_last_reset DATE,
    first_million_seconds INT, -- Time to reach 1M GEM
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### `clicker_themes`
```sql
CREATE TABLE clicker_themes (
    user_id VARCHAR(36) PRIMARY KEY,
    button_theme VARCHAR(50) DEFAULT 'classic_blue',
    particle_effect VARCHAR(50) DEFAULT 'gem_burst',
    background_theme VARCHAR(50) DEFAULT 'gradient_purple',
    -- Unlocked themes (JSON array)
    unlocked_button_themes TEXT, -- JSON: ['classic_blue', 'green_machine', ...]
    unlocked_particle_effects TEXT,
    unlocked_backgrounds TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## API Endpoints

### Prestige
- `POST /api/clicker/prestige` - Perform prestige (reset with PP)
- `GET /api/clicker/prestige/preview` - Calculate PP gain without resetting
- `POST /api/clicker/prestige/shop/{item}` - Buy prestige shop item
- `GET /api/clicker/prestige/stats` - Get prestige stats and bonuses

### Power-ups
- `POST /api/clicker/powerup/{type}/activate` - Activate power-up
- `GET /api/clicker/powerup/active` - Get active power-ups
- `GET /api/clicker/powerup/cooldowns` - Get cooldown status

### Challenges
- `GET /api/clicker/challenges` - Get active challenges
- `POST /api/clicker/challenges/{id}/claim` - Claim challenge reward
- `POST /api/clicker/challenges/daily/skip` - Skip daily challenge

### Leaderboards
- `GET /api/clicker/leaderboard/{category}` - Get leaderboard (paginated)
- `GET /api/clicker/leaderboard/rank/{category}` - Get player's rank

### Themes
- `GET /api/clicker/themes` - Get unlocked and active themes
- `POST /api/clicker/themes/apply` - Apply theme
- `GET /api/clicker/themes/check-unlocks` - Check for new unlocks

---

## Implementation Priority

### Phase 2A (Core Mechanics)
1. Prestige system backend + UI
2. Power-ups backend + UI
3. Daily challenges backend + UI

### Phase 2B (Social & Customization)
4. Leaderboards backend + page
5. Visual themes + customization UI

---

## Success Metrics

### Engagement
- Average prestige level across users
- Power-ups purchased per session
- Daily challenge completion rate
- Leaderboard page views

### Retention
- Daily active users increase
- Session length increase
- Return rate after prestige

### Balance
- Time to first prestige (target: 2-3 hours)
- Power-up usage frequency
- Challenge completion rates (target: 60-80%)

---

## Next Steps

1. Create database models for Phase 2
2. Implement prestige service
3. Build power-ups system
4. Create challenges engine
5. Implement leaderboards
6. Add theme customization
7. Build UI components
8. Test and balance

**Estimated Implementation Time**: 2-3 hours for complete Phase 2
