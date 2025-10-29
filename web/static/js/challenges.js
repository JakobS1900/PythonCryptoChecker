/**
 * Daily Challenges Manager
 * Handles login streaks, daily challenges, and reward claiming
 */

class ChallengesManager {
    constructor() {
        this.loginStreak = null;
        this.challenges = [];
        this.refreshInterval = null;
        this.timerInterval = null;
    }

    async init() {
        console.log('[Challenges] Initializing...');

        // Check if user is logged in
        const token = localStorage.getItem('auth_token');
        if (!token) {
            window.location.href = '/login';
            return;
        }

        // Load data
        await this.loadLoginStreak();
        await this.loadChallenges();

        // Start auto-refresh every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.loadLoginStreak();
            this.loadChallenges();
        }, 30000);

        // Start countdown timer
        this.startResetTimer();

        // Hide loading state
        document.getElementById('loading-state').style.display = 'none';

        console.log('[Challenges] Ready!');
    }

    async loadLoginStreak() {
        const token = localStorage.getItem('auth_token');

        try {
            const response = await fetch('/api/challenges/login-streak', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load login streak');
            }

            const data = await response.json();
            this.loginStreak = data;
            this.renderLoginStreak();

        } catch (error) {
            console.error('[Challenges] Error loading login streak:', error);
        }
    }

    renderLoginStreak() {
        if (!this.loginStreak) return;

        document.getElementById('current-streak').textContent = this.loginStreak.current_streak;
        document.getElementById('longest-streak').textContent = this.loginStreak.longest_streak;
        document.getElementById('total-logins').textContent = this.loginStreak.total_logins;

        // Calculate bonus for next login
        const nextBonus = this.getLoginBonus(this.loginStreak.current_streak + 1);
        document.getElementById('today-bonus').textContent = nextBonus.toLocaleString();

        // Update claim button state
        const claimBtn = document.getElementById('claim-login-btn');
        if (this.loginStreak.can_claim) {
            claimBtn.disabled = false;
            claimBtn.innerHTML = '<i class="bi bi-gift"></i> Claim Daily Login Bonus';
        } else {
            claimBtn.disabled = true;
            claimBtn.innerHTML = '<i class="bi bi-check-circle"></i> Already Claimed Today';
        }
    }

    getLoginBonus(streak) {
        const bonuses = {
            1: 100, 2: 150, 3: 200, 4: 250, 5: 300,
            7: 500, 10: 750, 14: 1000, 21: 1500, 30: 2500
        };

        // Find the highest bonus for this streak
        let bonus = 100;
        for (const [days, amount] of Object.entries(bonuses)) {
            if (streak >= parseInt(days)) {
                bonus = amount;
            }
        }
        return bonus;
    }

    async claimDailyLogin() {
        const token = localStorage.getItem('auth_token');
        const claimBtn = document.getElementById('claim-login-btn');

        // Disable button during request
        claimBtn.disabled = true;
        claimBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Claiming...';

        try {
            const response = await fetch('/api/challenges/daily-login', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to claim login bonus');
            }

            // Show success message
            this.showNotification('success', `Daily Login Bonus Claimed! +${data.bonus_amount.toLocaleString()} GEM`);

            // Reload streak data
            await this.loadLoginStreak();

            // Update balance in navbar if available
            if (window.updateBalance) {
                await window.updateBalance();
            }

        } catch (error) {
            console.error('[Challenges] Error claiming login bonus:', error);
            this.showNotification('error', error.message);

            // Re-enable button on error
            claimBtn.disabled = false;
            claimBtn.innerHTML = '<i class="bi bi-gift"></i> Claim Daily Login Bonus';
        }
    }

    async loadChallenges() {
        const token = localStorage.getItem('auth_token');

        try {
            const response = await fetch('/api/challenges/active', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load challenges');
            }

            const data = await response.json();
            this.challenges = data.challenges;
            this.renderChallenges();

        } catch (error) {
            console.error('[Challenges] Error loading challenges:', error);
            document.getElementById('challenges-grid').innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-exclamation-circle" style="font-size: 3rem; color: var(--error);"></i>
                    <p class="mt-3">Failed to load challenges</p>
                </div>
            `;
        }
    }

    renderChallenges() {
        const container = document.getElementById('challenges-grid');

        if (this.challenges.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-inbox" style="font-size: 3rem; color: var(--text-secondary);"></i>
                    <p class="mt-3">No active challenges available</p>
                </div>
            `;
            return;
        }

        let html = '';

        this.challenges.forEach(challenge => {
            const progress = challenge.progress || 0;
            const requirement = challenge.requirement_value;
            const percentage = Math.min((progress / requirement) * 100, 100);
            const isCompleted = challenge.completed;
            const isClaimed = challenge.claimed;

            const difficulty = this.getChallengeDifficulty(challenge.challenge_type);

            html += `
                <div class="challenge-card ${isCompleted ? 'completed' : ''}">
                    <div class="challenge-header">
                        <div>
                            <div class="challenge-title">${challenge.title}</div>
                        </div>
                        <span class="challenge-type ${difficulty}">${difficulty}</span>
                    </div>

                    <div class="challenge-description">
                        ${challenge.description}
                    </div>

                    <div class="challenge-progress">
                        <div class="progress-bar-container">
                            <div class="progress-bar-fill ${isCompleted ? 'completed' : ''}"
                                 style="width: ${percentage}%"></div>
                        </div>
                        <div class="progress-text">
                            <span class="progress-current">${this.formatNumber(progress)} / ${this.formatNumber(requirement)}</span>
                            <span class="progress-requirement">${percentage.toFixed(0)}%</span>
                        </div>
                    </div>

                    <div class="challenge-footer">
                        <div class="challenge-reward">
                            <i class="bi bi-gem"></i>
                            ${this.formatNumber(challenge.gem_reward)} GEM
                        </div>

                        ${isClaimed ? `
                            <button class="claim-challenge-btn" disabled>
                                <i class="bi bi-check-circle"></i> Claimed
                            </button>
                        ` : isCompleted ? `
                            <button class="claim-challenge-btn" onclick="Challenges.claimReward(${challenge.id})">
                                <i class="bi bi-gift"></i> Claim Reward
                            </button>
                        ` : `
                            <button class="claim-challenge-btn" disabled>
                                <i class="bi bi-lock"></i> Incomplete
                            </button>
                        `}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    getChallengeDifficulty(challengeType) {
        const easy = ['daily_login', 'roulette_bets'];
        const hard = ['minigame_profit', 'gem_earned'];

        if (easy.includes(challengeType)) return 'easy';
        if (hard.includes(challengeType)) return 'hard';
        return 'normal';
    }

    async claimReward(challengeId) {
        const token = localStorage.getItem('auth_token');

        try {
            const response = await fetch(`/api/challenges/claim/${challengeId}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to claim reward');
            }

            // Show success message
            this.showNotification('success', `Challenge Completed! +${data.reward.toLocaleString()} GEM`);

            // Reload challenges
            await this.loadChallenges();

            // Update balance in navbar if available
            if (window.updateBalance) {
                await window.updateBalance();
            }

        } catch (error) {
            console.error('[Challenges] Error claiming reward:', error);
            this.showNotification('error', error.message);
        }
    }

    startResetTimer() {
        const updateTimer = () => {
            const now = new Date();
            const utc = new Date(now.toLocaleString('en-US', { timeZone: 'UTC' }));

            // Calculate time until next UTC midnight
            const tomorrow = new Date(utc);
            tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
            tomorrow.setUTCHours(0, 0, 0, 0);

            const diff = tomorrow - utc;

            const hours = Math.floor(diff / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);

            const timerElement = document.getElementById('reset-timer');
            if (timerElement) {
                timerElement.textContent = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
            }
        };

        // Update immediately
        updateTimer();

        // Update every second
        this.timerInterval = setInterval(updateTimer, 1000);
    }

    formatNumber(num) {
        return new Intl.NumberFormat('en-US').format(num);
    }

    showNotification(type, message) {
        // Create notification element
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: ${type === 'success' ? 'var(--success)' : 'var(--error)'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        notification.innerHTML = `
            <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            ${message}
        `;

        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
        }
    }
}

// Create global instance
const Challenges = new ChallengesManager();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    Challenges.destroy();
});
