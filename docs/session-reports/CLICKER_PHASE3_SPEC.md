# GEM Clicker Phase 3: Achievements, Leaderboards & Events

**Status**: Planning
**Priority**: High
**Estimated Effort**: 3-4 hours

---

## 🎯 Phase 3 Overview

Phase 3 adds **competitive and progression elements** to the GEM Clicker to increase engagement and retention:

1. **Achievements System** - Unlock badges and earn rewards for milestones
2. **Leaderboards** - Compete with other players across multiple categories
3. **Special Events** - Time-limited challenges with bonus rewards
4. **Statistics Dashboard** - Detailed player analytics and progress tracking

---

## 📊 Feature 1: Achievements System

### Achievement Categories

**Click Achievements** (5 achievements)
- First Click (1 click) - Reward: 100 GEM
- Click Novice (100 clicks) - Reward: 500 GEM
- Click Expert (1,000 clicks) - Reward: 2,500 GEM
- Click Master (10,000 clicks) - Reward: 10,000 GEM
- Click Legend (100,000 clicks) - Reward: 50,000 GEM

**Earning Achievements** (5 achievements)
- First Gems (100 GEM earned) - Reward: 200 GEM
- Gem Collector (10,000 GEM earned) - Reward: 5,000 GEM
- Gem Hoarder (100,000 GEM earned) - Reward: 25,000 GEM
- Gem Tycoon (1,000,000 GEM earned) - Reward: 100,000 GEM
- Gem Emperor (10,000,000 GEM earned) - Reward: 500,000 GEM

**Combo Achievements** (4 achievements)
- Combo Starter (3x combo) - Reward: 500 GEM
- Combo Pro (10x combo) - Reward: 2,000 GEM
- Combo King (25x combo) - Reward: 10,000 GEM
- Combo God (50x combo) - Reward: 50,000 GEM

**Prestige Achievements** (4 achievements)
- First Prestige (1 prestige) - Reward: 5,000 GEM
- Prestige Veteran (5 prestiges) - Reward: 25,000 GEM
- Prestige Master (15 prestiges) - Reward: 100,000 GEM
- Prestige Legend (50 prestiges) - Reward: 500,000 GEM

**Power-up Achievements** (3 achievements)
- Power User (Activate 10 power-ups) - Reward: 5,000 GEM
- Power Master (Activate 50 power-ups) - Reward: 25,000 GEM
- Power God (Activate 200 power-ups) - Reward: 100,000 GEM

**Special Achievements** (4 achievements)
- Speed Demon (10,000 clicks in 1 hour) - Reward: 25,000 GEM
- Energy Efficient (Reach max energy 100 times) - Reward: 10,000 GEM
- Mega Lucky (Hit 100 mega bonuses) - Reward: 50,000 GEM
- All Maxed (Max all upgrade categories) - Reward: 1,000,000 GEM

**Total**: 25 achievements

### Achievement Features
- **Progress Tracking**: Show % completion for locked achievements
- **Notifications**: Toast notifications when achievements unlock
- **Rewards**: Auto-grant GEM rewards when unlocked
- **Badges**: Visual badge display on profile
- **Achievement Points**: Each achievement worth points (1-10 based on rarity)

---

## 🏆 Feature 2: Leaderboards

### Leaderboard Categories

1. **Total Clicks Leaderboard**
   - Top 100 players by all-time total clicks
   - Updates: Real-time

2. **Total GEM Earned Leaderboard**
   - Top 100 players by lifetime GEM earned
   - Updates: Real-time

3. **Highest Combo Leaderboard**
   - Top 100 players by best combo achieved
   - Updates: Real-time

4. **Prestige Points Leaderboard**
   - Top 100 players by total PP
   - Updates: Real-time

5. **Achievement Points Leaderboard**
   - Top 100 players by total achievement points
   - Updates: Every 5 minutes

6. **Weekly Clicks Leaderboard**
   - Top 100 players by clicks this week
   - Resets: Monday 00:00 UTC
   - Rewards: Top 10 get bonus GEM

### Leaderboard Features
- **Real-time Updates**: WebSocket or polling for live updates
- **Player Highlighting**: Current user highlighted in rankings
- **Rank Change Indicators**: Up/down arrows showing rank changes
- **Rewards**: Weekly top performers get GEM bonuses
- **Filtering**: All-time, Monthly, Weekly views

---

## 🎊 Feature 3: Special Events

### Event Types

**1. Double GEM Event**
- Duration: 2-4 hours
- Effect: All GEM rewards doubled
- Frequency: 2-3 times per week
- Notification: 15 minutes warning before start

**2. Mega Bonus Frenzy**
- Duration: 1 hour
- Effect: 3x chance for mega bonuses
- Frequency: Once per day
- Notification: Announced 30 minutes before

**3. Energy Rush**
- Duration: 30 minutes
- Effect: Energy regenerates 5x faster
- Frequency: 3-4 times per day
- Notification: 10 minutes warning

**4. PP Bonus Weekend**
- Duration: 48 hours (Saturday-Sunday)
- Effect: +50% PP on prestige
- Frequency: Every weekend
- Notification: Friday evening announcement

**5. Click Challenge**
- Duration: 1 hour
- Goal: Most clicks in 1 hour wins prizes
- Rewards: Top 10 get GEM bonuses
- Frequency: Twice per week

### Event Features
- **Event Calendar**: View upcoming events
- **Active Event Banner**: Visual indicator on clicker page
- **Event History**: Past event results and rewards
- **Participation Tracking**: Track user participation
- **Auto-activation**: Events activate automatically

---

## 📈 Feature 4: Statistics Dashboard

### Statistics Tracked

**Clicking Stats**
- Total clicks (all-time)
- Average clicks per day
- Click streak (consecutive days)
- Fastest 100 clicks time
- Total energy spent

**Earning Stats**
- Total GEM earned (all-time)
- Total GEM spent
- Average GEM per click
- Highest single click reward
- Total bonus GEM earned

**Prestige Stats**
- Total prestiges
- Total PP earned
- Average PP per prestige
- Fastest prestige time
- Total prestige shop purchases

**Power-up Stats**
- Total power-ups activated
- Favorite power-up (most used)
- Total GEM spent on power-ups
- Total bonus time from power-ups

**Combo Stats**
- Best combo achieved
- Total combos (3+ streak)
- Average combo length
- Combo break count

**Time Stats**
- Total play time
- Sessions played
- Average session length
- First click date
- Last active

---

## 💾 Database Schema

### New Tables

```python
# clicker_achievements
- id: UUID (PK)
- user_id: UUID (FK -> users)
- achievement_id: String (achievement key)
- unlocked_at: DateTime
- reward_claimed: Boolean
- created_at: DateTime

# clicker_leaderboard_weekly
- id: UUID (PK)
- user_id: UUID (FK -> users)
- week_start: Date
- clicks: Integer
- gems_earned: Float
- best_combo: Integer
- created_at: DateTime
- updated_at: DateTime

# clicker_events
- id: UUID (PK)
- event_type: String (double_gem, mega_frenzy, etc.)
- start_time: DateTime
- end_time: DateTime
- is_active: Boolean
- config: JSON (event-specific settings)
- created_at: DateTime

# clicker_event_participation
- id: UUID (PK)
- user_id: UUID (FK -> users)
- event_id: UUID (FK -> clicker_events)
- clicks_during: Integer
- gems_earned_during: Float
- reward_earned: Float
- participated_at: DateTime

# clicker_statistics
- id: UUID (PK)
- user_id: UUID (FK -> users, UNIQUE)
- fastest_100_clicks_ms: Integer
- total_energy_spent: Integer
- total_bonus_gems: Float
- click_streak_days: Integer
- longest_session_minutes: Integer
- total_play_time_minutes: Integer
- sessions_played: Integer
- first_click_date: DateTime
- last_active: DateTime
- updated_at: DateTime
```

---

## 🔌 API Endpoints

### Achievements
- `GET /api/clicker/achievements` - Get all achievements with unlock status
- `GET /api/clicker/achievements/unlocked` - Get user's unlocked achievements
- `POST /api/clicker/achievements/{achievement_id}/claim` - Claim achievement reward

### Leaderboards
- `GET /api/clicker/leaderboards/{category}` - Get leaderboard (all-time)
- `GET /api/clicker/leaderboards/{category}/weekly` - Get weekly leaderboard
- `GET /api/clicker/leaderboards/my-rank` - Get current user's ranks

### Events
- `GET /api/clicker/events/active` - Get currently active events
- `GET /api/clicker/events/upcoming` - Get upcoming scheduled events
- `GET /api/clicker/events/history` - Get past events and participation

### Statistics
- `GET /api/clicker/statistics` - Get detailed user statistics
- `GET /api/clicker/statistics/summary` - Get summary stats for dashboard

---

## 🎨 UI Components

### Achievement Panel
- Achievement grid with icons and progress bars
- Filter by category (All, Click, Earning, Prestige, etc.)
- Achievement detail modal on click
- Total achievement points display
- Progress percentage for each category

### Leaderboard Panel
- Tabbed interface for different categories
- Scrollable table with rankings
- Current user highlight with glow effect
- Rank change indicators (↑ ↓ -)
- Time period filter (All-time, Monthly, Weekly)
- Top 3 podium display

### Events Panel
- Active event banner with countdown timer
- Event effects display (2x GEM, 3x Mega Bonus, etc.)
- Upcoming events calendar
- Past event results and rewards
- Participation badges

### Statistics Dashboard
- Chart visualizations (Chart.js)
- Key stats cards with icons
- Progress charts (clicks over time, GEM over time)
- Comparison to platform averages
- Personal records section

---

## 🎯 Implementation Plan

### Phase 3A: Achievements (Week 1)
1. Database models and migration
2. AchievementService with unlock logic
3. Achievement API endpoints
4. Achievement checking on click/prestige/etc
5. Achievement UI panel
6. Achievement notifications

### Phase 3B: Leaderboards (Week 2)
1. Leaderboard database tables
2. LeaderboardService with ranking logic
3. Leaderboard API endpoints
4. Real-time leaderboard updates
5. Leaderboard UI panel
6. Weekly reset cron job

### Phase 3C: Events (Week 3)
1. Event database models
2. EventService with scheduling
3. Event API endpoints
4. Event activation/deactivation logic
5. Event UI components
6. Event calendar and notifications

### Phase 3D: Statistics (Week 4)
1. Statistics tracking database
2. StatisticsService with analytics
3. Statistics API endpoints
4. Statistics UI dashboard
5. Chart visualizations
6. Testing and polish

---

## 📦 Dependencies

**Python Packages** (if needed)
- `apscheduler` - Event scheduling
- None other (use existing)

**JavaScript Libraries**
- `chart.js` - Charts and visualizations (already included)
- Existing libraries sufficient

---

## 🎮 Success Metrics

- **Achievement Unlocks**: 70% of users unlock 5+ achievements in first week
- **Leaderboard Engagement**: 50% of active users check leaderboards daily
- **Event Participation**: 80% of users participate in at least one event per week
- **Session Duration**: Average session increases by 30%
- **Retention**: 7-day retention increases by 20%

---

## 🚀 Future Enhancements (Phase 4?)

- **Guilds/Clans**: Team-based competitions
- **Trading System**: Trade achievements or items
- **Custom Challenges**: User-created challenges
- **Seasonal Content**: Themed events (holidays, etc.)
- **Achievement Tiers**: Bronze, Silver, Gold, Platinum versions

---

**End of Phase 3 Specification**
