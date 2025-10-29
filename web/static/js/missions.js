// Missions Management JavaScript
const MissionsManager = {
    data: {
        daily: [],
        weekly: [],
        stats: null
    },

    init() {
        console.log('Initializing Missions Manager...');
        this.loadMissions();

        // Set up auto-refresh every 30 seconds
        setInterval(() => this.loadMissions(), 30000);

        // Set up tab switching
        document.querySelectorAll('#missionsTabs button[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                console.log('Tab switched:', e.target.id);
            });
        });
    },

    async loadMissions() {
        try {
            const token = localStorage.getItem('auth_token');
            if (!token) {
                this.showLoginRequired();
                return;
            }

            // Load overview data (includes both daily and weekly)
            const response = await fetch('/api/missions/overview', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                if (response.status === 401) {
                    this.showLoginRequired();
                    return;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Missions data loaded:', data);

            this.data.daily = data.daily_missions;
            this.data.weekly = data.weekly_challenges;

            // Update stats
            this.updateStats(data);

            // Render missions
            this.renderDailyMissions();
            this.renderWeeklyChallenges();

            // Update timers
            this.startTimers(data.seconds_until_daily_reset, data.seconds_until_weekly_reset);

        } catch (error) {
            console.error('Error loading missions:', error);
            this.showError('Failed to load missions. Please try again later.');
        }
    },

    updateStats(data) {
        // Count completed missions
        const dailyCompleted = data.daily_missions.filter(m => m.status === 'completed' || m.status === 'claimed').length;
        const weeklyCompleted = data.weekly_challenges.filter(c => c.status === 'completed' || c.status === 'claimed').length;

        // Count available gems (completed but not claimed)
        const availableGems = [
            ...data.daily_missions.filter(m => m.status === 'completed'),
            ...data.weekly_challenges.filter(c => c.status === 'completed')
        ].reduce((sum, item) => sum + item.reward, 0);

        // Update stat cards
        document.getElementById('daily-completed').textContent = dailyCompleted;
        document.getElementById('daily-total').textContent = data.daily_missions.length;
        document.getElementById('weekly-completed').textContent = weeklyCompleted;
        document.getElementById('weekly-total').textContent = data.weekly_challenges.length;
        document.getElementById('daily-rewards').textContent = data.total_daily_rewards.toLocaleString();
        document.getElementById('weekly-rewards').textContent = data.total_weekly_rewards.toLocaleString();
        document.getElementById('available-gems').textContent = availableGems.toLocaleString();
    },

    renderDailyMissions() {
        const container = document.getElementById('daily-missions-container');

        if (this.data.daily.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-inbox" style="font-size: 4rem; color: var(--text-tertiary);"></i>
                    <p class="text-muted mt-3">No daily missions available</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.data.daily.map(mission => this.renderMissionCard(mission, 'daily')).join('');

        // Add click listeners to claim buttons
        container.querySelectorAll('.claim-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const missionId = e.target.dataset.missionId;
                const type = e.target.dataset.type;
                this.claimReward(missionId, type);
            });
        });
    },

    renderWeeklyChallenges() {
        const container = document.getElementById('weekly-challenges-container');

        if (this.data.weekly.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-inbox" style="font-size: 4rem; color: var(--text-tertiary);"></i>
                    <p class="text-muted mt-3">No weekly challenges available</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.data.weekly.map(challenge => this.renderMissionCard(challenge, 'weekly')).join('');

        // Add click listeners to claim buttons
        container.querySelectorAll('.claim-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const challengeId = e.target.dataset.missionId;
                const type = e.target.dataset.type;
                this.claimReward(challengeId, type);
            });
        });
    },

    renderMissionCard(mission, type) {
        const progress = Math.min((mission.progress / mission.target) * 100, 100);
        const isCompleted = mission.status === 'completed';
        const isClaimed = mission.status === 'claimed';
        const isActive = mission.status === 'active';

        // Difficulty badge for weekly challenges
        const difficultyBadge = type === 'weekly' ? `
            <span class="badge-modern badge-modern-${mission.difficulty === 'hard' ? 'error' : mission.difficulty === 'medium' ? 'warning' : 'info'}" style="font-size: var(--text-xs);">
                ${mission.difficulty.toUpperCase()}
            </span>
        ` : '';

        // Status badge
        let statusBadge = '';
        if (isClaimed) {
            statusBadge = '<span class="badge-modern badge-modern-success" style="font-size: var(--text-xs);"><i class="bi bi-check-circle-fill"></i> CLAIMED</span>';
        } else if (isCompleted) {
            statusBadge = '<span class="badge-modern badge-modern-gem" style="font-size: var(--text-xs);"><i class="bi bi-gift-fill"></i> READY TO CLAIM</span>';
        }

        // Action button
        let actionButton = '';
        if (isCompleted) {
            actionButton = `
                <button class="btn btn-sm claim-btn" data-mission-id="${mission.id}" data-type="${type}"
                        style="background: linear-gradient(135deg, var(--gem) 0%, var(--warning) 100%);
                               border: none; color: white; padding: var(--space-2) var(--space-4);
                               border-radius: var(--radius-md); font-weight: var(--font-semibold);">
                    <i class="bi bi-gift-fill"></i> Claim ${mission.reward.toLocaleString()} GEM
                </button>
            `;
        } else if (isClaimed) {
            actionButton = `
                <button class="btn btn-sm" disabled
                        style="background: var(--bg-tertiary); border: 1px solid var(--border-subtle);
                               color: var(--text-tertiary); padding: var(--space-2) var(--space-4);
                               border-radius: var(--radius-md);">
                    <i class="bi bi-check-circle"></i> Claimed
                </button>
            `;
        }

        return `
            <div class="card-modern mission-card" style="margin-bottom: var(--space-4); padding: var(--space-6); ${isCompleted ? 'border-color: var(--gem); background: linear-gradient(135deg, rgba(255, 215, 0, 0.05) 0%, rgba(255, 193, 7, 0.02) 100%);' : ''}">
                <div class="row align-items-center">
                    <div class="col-auto">
                        <div class="mission-icon" style="width: 60px; height: 60px; border-radius: var(--radius-lg); background: ${isCompleted ? 'linear-gradient(135deg, var(--gem) 0%, var(--warning) 100%)' : 'var(--bg-tertiary)'}; display: flex; align-items: center; justify-content: center; font-size: 1.75rem; color: ${isCompleted ? 'white' : 'var(--text-secondary)'};">
                            <i class="bi ${mission.icon || 'bi-star'}"></i>
                        </div>
                    </div>
                    <div class="col">
                        <div class="d-flex align-items-center gap-2 mb-1">
                            <h5 style="margin: 0; font-size: var(--text-lg); font-weight: var(--font-semibold); color: var(--text-primary);">
                                ${mission.name}
                            </h5>
                            ${difficultyBadge}
                            ${statusBadge}
                        </div>
                        <p style="margin: 0 0 var(--space-3) 0; color: var(--text-secondary); font-size: var(--text-sm);">
                            ${mission.description}
                        </p>
                        <div class="row align-items-center">
                            <div class="col-md-6">
                                <div class="progress-bar-container" style="background: var(--bg-tertiary); border-radius: var(--radius-full); height: 8px; overflow: hidden; position: relative;">
                                    <div class="progress-bar-fill" style="background: linear-gradient(90deg, var(--primary) 0%, var(--gem) 100%); width: ${progress}%; height: 100%; border-radius: var(--radius-full); transition: width 0.3s ease;"></div>
                                </div>
                                <small style="color: var(--text-tertiary); font-size: var(--text-xs); margin-top: var(--space-1); display: block;">
                                    ${mission.progress.toLocaleString()} / ${mission.target.toLocaleString()} ${progress === 100 ? '✓' : ''}
                                </small>
                            </div>
                            <div class="col-md-6 text-md-end mt-3 mt-md-0">
                                <div class="d-flex align-items-center justify-content-md-end gap-3">
                                    <div class="reward-badge" style="background: ${isClaimed ? 'var(--bg-tertiary)' : 'rgba(255, 215, 0, 0.1)'}; border: 1px solid ${isClaimed ? 'var(--border-subtle)' : 'var(--gem)'}; border-radius: var(--radius-md); padding: var(--space-2) var(--space-3); display: inline-flex; align-items: center; gap: var(--space-2);">
                                        <i class="bi bi-gem" style="color: ${isClaimed ? 'var(--text-tertiary)' : 'var(--gem)'};"></i>
                                        <span style="font-weight: var(--font-semibold); color: ${isClaimed ? 'var(--text-tertiary)' : 'var(--text-primary)'};">
                                            ${mission.reward.toLocaleString()} GEM
                                        </span>
                                    </div>
                                    ${actionButton}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    async claimReward(missionId, type) {
        try {
            const token = localStorage.getItem('auth_token');
            if (!token) {
                this.showLoginRequired();
                return;
            }

            const endpoint = type === 'daily'
                ? `/api/missions/daily/${missionId}/claim`
                : `/api/missions/weekly/${missionId}/claim`;

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to claim reward');
            }

            const data = await response.json();
            console.log('Reward claimed:', data);

            // Show success message
            this.showSuccess(`Successfully claimed ${data.reward_claimed.toLocaleString()} GEM! New balance: ${data.new_balance.toLocaleString()} GEM`);

            // Reload missions to update UI
            setTimeout(() => this.loadMissions(), 500);

            // Update balance in header if available
            if (window.Auth && window.Auth.updateBalance) {
                window.Auth.updateBalance();
            }

        } catch (error) {
            console.error('Error claiming reward:', error);
            this.showError(error.message || 'Failed to claim reward');
        }
    },

    startTimers(dailySeconds, weeklySeconds) {
        // Update daily reset timer
        const updateDailyTimer = () => {
            dailySeconds--;
            if (dailySeconds <= 0) {
                document.getElementById('daily-reset-timer').textContent = 'Resetting...';
                setTimeout(() => this.loadMissions(), 1000);
                return;
            }

            const hours = Math.floor(dailySeconds / 3600);
            const minutes = Math.floor((dailySeconds % 3600) / 60);
            const seconds = dailySeconds % 60;

            document.getElementById('daily-reset-timer').textContent =
                `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        };

        // Start timer
        updateDailyTimer();
        setInterval(updateDailyTimer, 1000);
    },

    showLoginRequired() {
        const container = document.getElementById('daily-missions-container');
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-lock" style="font-size: 4rem; color: var(--text-tertiary);"></i>
                <h4 class="mt-4" style="color: var(--text-primary);">Login Required</h4>
                <p class="text-muted">You need to be logged in to view and complete missions.</p>
                <a href="/login" class="btn btn-primary mt-3">
                    <i class="bi bi-box-arrow-in-right"></i> Log In
                </a>
            </div>
        `;
        document.getElementById('weekly-challenges-container').innerHTML = container.innerHTML;
    },

    showError(message) {
        // Create toast notification for error
        console.error('Mission error:', message);

        Toast.error('Error: ' + message);
    },

    showSuccess(message) {
        // Create toast notification for success
        console.log('Mission success:', message);

        Toast.success('Success: ' + message);
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    MissionsManager.init();
});
