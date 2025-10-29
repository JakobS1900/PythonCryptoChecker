/**
 * Achievements Manager
 * Handles achievement loading, display, and reward claiming
 */

class AchievementsManager {
    constructor() {
        this.achievements = [];
        this.stats = null;
        this.currentCategory = 'all';

        this.init();
    }

    async init() {
        console.log('[Achievements] Initializing...');

        // Check authentication
        const isAuthenticated = await this.checkAuth();

        if (!isAuthenticated) {
            this.showLoginRequired();
            return;
        }

        // Load achievements
        await this.loadAchievements();

        // Set up category tabs
        this.setupCategoryTabs();
    }

    async checkAuth() {
        try {
            const response = await fetch('/api/auth/status');
            if (response.ok) {
                const data = await response.json();
                // Allow authenticated users OR guest users
                return data.authenticated || data.guest_mode;
            }
            return false;
        } catch (error) {
            console.error('[Achievements] Auth check failed:', error);
            return false;
        }
    }

    showLoginRequired() {
        document.getElementById('login-required').style.display = 'block';
        document.getElementById('achievements-grid').style.display = 'none';
        document.getElementById('stats-overview').style.display = 'none';
        document.getElementById('category-tabs').style.display = 'none';
    }

    async loadAchievements(category = 'all') {
        try {
            const endpoint = category === 'all'
                ? '/api/achievements'
                : `/api/achievements/category/${category}`;

            const response = await fetch(endpoint);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            this.achievements = data.achievements;
            this.stats = data.stats;

            console.log(`[Achievements] Loaded ${this.achievements.length} achievements`);

            this.updateStats();
            this.renderAchievements();

        } catch (error) {
            console.error('[Achievements] Failed to load achievements:', error);
            this.showError('Failed to load achievements. Please try again.');
        }
    }

    updateStats() {
        if (!this.stats) return;

        document.getElementById('stat-unlocked').textContent =
            `${this.stats.total_unlocked}/${this.stats.total_achievements}`;

        document.getElementById('stat-completion').textContent =
            `${this.stats.completion_percentage}%`;

        document.getElementById('stat-unclaimed').textContent =
            `${this.stats.unclaimed_rewards.toLocaleString()} GEM`;

        document.getElementById('stat-total').textContent =
            this.stats.total_achievements;
    }

    renderAchievements() {
        const grid = document.getElementById('achievements-grid');

        if (this.achievements.length === 0) {
            grid.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="bi bi-inbox" style="font-size: 64px; color: var(--text-muted); opacity: 0.5;"></i>
                    <p class="text-muted mt-3">No achievements in this category</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = this.achievements.map(achievement =>
            this.createAchievementCard(achievement)
        ).join('');
    }

    createAchievementCard(achievement) {
        const isUnlocked = achievement.is_unlocked;
        const canClaim = isUnlocked && !achievement.reward_claimed;

        return `
            <div class="col-lg-4 col-md-6">
                <div class="achievement-card ${isUnlocked ? 'unlocked' : 'locked'}"
                     data-achievement-id="${achievement.id}">

                    ${isUnlocked ? `
                        <div class="unlock-check">
                            <i class="bi bi-check-lg"></i>
                        </div>
                    ` : ''}

                    <div class="d-flex align-items-start gap-3">
                        <div class="achievement-icon ${achievement.rarity}">
                            <i class="bi ${achievement.icon}"></i>
                        </div>

                        <div class="flex-grow-1">
                            <div class="d-flex align-items-start justify-content-between mb-2">
                                <h5 class="mb-0 fw-semibold">${achievement.name}</h5>
                                <span class="rarity-badge ${achievement.rarity}">${achievement.rarity}</span>
                            </div>

                            <p class="text-muted mb-3" style="font-size: var(--text-sm);">
                                ${achievement.description}
                            </p>

                            <div class="d-flex align-items-center justify-content-between">
                                <div class="d-flex align-items-center gap-2">
                                    <i class="bi bi-gem" style="color: var(--gem);"></i>
                                    <span class="fw-semibold">${achievement.reward.toLocaleString()} GEM</span>
                                </div>

                                ${canClaim ? `
                                    <button class="btn-modern btn-modern-sm btn-modern-primary"
                                            onclick="achievementsManager.claimReward('${achievement.unlock_id}', '${achievement.id}')">
                                        <i class="bi bi-gift-fill"></i>
                                        <span>Claim</span>
                                    </button>
                                ` : isUnlocked && achievement.reward_claimed ? `
                                    <span class="badge bg-success">
                                        <i class="bi bi-check-circle-fill"></i> Claimed
                                    </span>
                                ` : `
                                    <span class="badge bg-secondary">
                                        <i class="bi bi-lock-fill"></i> Locked
                                    </span>
                                `}
                            </div>

                            ${isUnlocked ? `
                                <div class="mt-3 pt-3" style="border-top: 1px solid var(--border-subtle); font-size: var(--text-xs); color: var(--text-muted);">
                                    <i class="bi bi-calendar-check"></i>
                                    Unlocked ${this.formatDate(achievement.unlocked_at)}
                                </div>
                            ` : ''}
                        </div>
                    </div>

                    ${!isUnlocked ? `
                        <div class="locked-overlay">
                            <i class="bi bi-lock-fill"></i>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    async claimReward(unlockId, achievementId) {
        try {
            const response = await fetch(`/api/achievements/${unlockId}/claim`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to claim reward');
            }

            const data = await response.json();

            console.log('[Achievements] Reward claimed:', data);

            // Show success notification
            this.showNotification(
                'success',
                `🎉 Claimed ${data.reward_amount.toLocaleString()} GEM!`,
                `New balance: ${data.new_balance.toLocaleString()} GEM`
            );

            // Update balance in navbar
            if (window.updateUserBalance) {
                window.updateUserBalance(data.new_balance);
            }

            // Reload achievements to update UI
            await this.loadAchievements(this.currentCategory);

            // Add celebration animation
            this.celebrateUnlock(achievementId);

        } catch (error) {
            console.error('[Achievements] Failed to claim reward:', error);
            this.showNotification('error', 'Failed to claim reward', error.message);
        }
    }

    setupCategoryTabs() {
        const tabs = document.querySelectorAll('.category-tab');

        tabs.forEach(tab => {
            tab.addEventListener('click', async () => {
                // Update active state
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                // Load category
                const category = tab.dataset.category;
                this.currentCategory = category;

                console.log(`[Achievements] Switching to category: ${category}`);

                // Show loading
                document.getElementById('achievements-grid').innerHTML = `
                    <div class="col-12 text-center py-5">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                `;

                // Load achievements
                await this.loadAchievements(category);
            });
        });
    }

    celebrateUnlock(achievementId) {
        const card = document.querySelector(`[data-achievement-id="${achievementId}"]`);
        if (card) {
            card.classList.add('achievement-unlock-animation');
            setTimeout(() => {
                card.classList.remove('achievement-unlock-animation');
            }, 2000);
        }
    }

    formatDate(dateString) {
        if (!dateString) return 'Never';

        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        return date.toLocaleDateString();
    }

    showNotification(type, title, message) {
        // Use Toast notification system
        if (window.Toast) {
            const toastType = type === 'success' ? 'success' : type === 'error' ? 'error' : 'info';
            Toast[toastType](`${title}: ${message}`);
        } else if (window.showAlert) {
            window.showAlert(type, `${title}: ${message}`);
        } else {
            console.log(`[${type.toUpperCase()}] ${title}: ${message}`);
        }
    }

    showError(message) {
        const grid = document.getElementById('achievements-grid');
        grid.innerHTML = `
            <div class="col-12">
                <div class="alert alert-danger" role="alert">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    ${message}
                </div>
            </div>
        `;
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (!window.achievementsManager) {
            window.achievementsManager = new AchievementsManager();
        }
    });
} else {
    if (!window.achievementsManager) {
        window.achievementsManager = new AchievementsManager();
    }
}
