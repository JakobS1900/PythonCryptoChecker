/**
 * GEM Clicker Phase 3A: Achievements System
 * Handles achievement loading, display, claiming, and unlock notifications
 */

class AchievementsManager {
    constructor() {
        this.achievementsData = null;
        this.currentCategory = 'all';
        this.rarityColors = {
            common: '#9ca3af',
            rare: '#3b82f6',
            epic: '#8b5cf6',
            legendary: '#f59e0b'
        };
        this.init();
    }

    async init() {
        console.log('Initializing Achievements Manager...');

        // Setup event listeners
        this.setupCategoryTabs();

        // Load achievements
        await this.loadAchievements();

        // Auto-refresh every 30 seconds
        setInterval(() => this.loadAchievements(), 30000);
    }

    setupCategoryTabs() {
        const tabs = document.querySelectorAll('.achievement-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                // Remove active class from all tabs
                tabs.forEach(t => t.classList.remove('active'));

                // Add active class to clicked tab
                tab.classList.add('active');

                // Update current category
                this.currentCategory = tab.dataset.category;

                // Re-render achievements
                this.renderAchievements();
            });
        });
    }

    async loadAchievements() {
        try {
            const token = localStorage.getItem('authToken');
            const response = await fetch('/api/clicker/achievements', {
                headers: {
                    'Authorization': token ? `Bearer ${token}` : ''
                }
            });

            const result = await response.json();
            if (result.success) {
                this.achievementsData = result.data;
                this.updateProgressDisplay();
                this.renderAchievements();
            } else {
                console.error('Failed to load achievements:', result.error);
            }
        } catch (error) {
            console.error('Error loading achievements:', error);
        }
    }

    updateProgressDisplay() {
        if (!this.achievementsData) return;

        const summary = this.achievementsData.summary;
        document.getElementById('achievements-unlocked').textContent = summary.total_unlocked;
        document.getElementById('achievements-total').textContent = summary.total_achievements;
        document.getElementById('achievements-percentage').textContent = summary.completion_percentage;
    }

    renderAchievements() {
        if (!this.achievementsData) return;

        const grid = document.getElementById('achievements-grid');
        grid.innerHTML = '';

        const categories = this.achievementsData.categories;

        // Filter achievements by current category
        let achievementsToShow = [];
        if (this.currentCategory === 'all') {
            // Show all achievements from all categories
            for (const category in categories) {
                achievementsToShow = achievementsToShow.concat(categories[category].achievements);
            }
        } else {
            // Show achievements from selected category
            achievementsToShow = categories[this.currentCategory]?.achievements || [];
        }

        // Sort: unlocked first, then by rarity
        achievementsToShow.sort((a, b) => {
            if (a.unlocked !== b.unlocked) {
                return b.unlocked - a.unlocked; // Unlocked first
            }
            const rarityOrder = { legendary: 0, epic: 1, rare: 2, common: 3 };
            return rarityOrder[a.rarity] - rarityOrder[b.rarity];
        });

        // Render each achievement
        achievementsToShow.forEach(achievement => {
            const achievementEl = this.createAchievementElement(achievement);
            grid.appendChild(achievementEl);
        });
    }

    createAchievementElement(achievement) {
        const div = document.createElement('div');
        div.className = `achievement-item ${achievement.unlocked ? 'unlocked' : 'locked'}`;

        const rarityColor = this.rarityColors[achievement.rarity];

        div.innerHTML = `
            <div class="achievement-rarity-glow" style="background: ${rarityColor}; opacity: 0.1;"></div>

            <div class="achievement-item-header">
                <div class="achievement-icon">
                    <i class="${achievement.icon}"></i>
                </div>
                <div class="achievement-info">
                    <div class="achievement-name">${achievement.name}</div>
                    <div class="achievement-rarity" style="color: ${rarityColor};">
                        ${achievement.rarity}
                    </div>
                </div>
            </div>

            <div class="achievement-description">${achievement.description}</div>

            <div class="achievement-requirement">
                ${this.getRequirementText(achievement)}
            </div>

            <div class="achievement-reward">
                <div class="achievement-reward-gems">
                    <i class="bi bi-gem"></i> ${this.formatNumber(achievement.reward_gems)} GEM
                </div>
                <div class="achievement-reward-points">
                    <i class="bi bi-star-fill"></i> ${achievement.achievement_points} pts
                </div>
            </div>

            ${this.getActionButton(achievement)}
        `;

        return div;
    }

    getRequirementText(achievement) {
        const reqType = achievement.requirement_type;
        const reqValue = this.formatNumber(achievement.requirement_value);

        const requirementTexts = {
            total_clicks: `Make ${reqValue} total clicks`,
            total_gems_earned: `Earn ${reqValue} total GEM`,
            best_combo: `Reach a ${reqValue}x combo`,
            prestige_level: `Reach prestige level ${reqValue}`,
            mega_bonuses: `Trigger ${reqValue} mega bonuses`,
            upgrades_purchased: `Purchase ${reqValue} upgrades`
        };

        return requirementTexts[reqType] || `Requirement: ${reqValue}`;
    }

    getActionButton(achievement) {
        if (!achievement.unlocked) {
            return '<div style="text-align: center; margin-top: var(--space-3); color: var(--text-tertiary); font-size: 0.9rem;">🔒 Locked</div>';
        }

        if (achievement.reward_claimed) {
            return '<div class="achievement-claimed-badge">✓ Reward Claimed</div>';
        }

        return `<button class="achievement-claim-btn" onclick="achievementsManager.claimReward('${achievement.id}')">
            <i class="bi bi-gift-fill"></i> Claim Reward
        </button>`;
    }

    async claimReward(achievementId) {
        try {
            const token = localStorage.getItem('authToken');
            const response = await fetch(`/api/clicker/achievements/${achievementId}/claim`, {
                method: 'POST',
                headers: {
                    'Authorization': token ? `Bearer ${token}` : '',
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();
            if (result.success) {
                const reward = result.data;

                // Show success message
                this.showNotification(`Claimed ${this.formatNumber(reward.reward_gems)} GEM!`, 'success');

                // Reload achievements to update UI
                await this.loadAchievements();

                // Update balance if the game has a refresh method
                if (window.game && typeof window.game.loadStats === 'function') {
                    await window.game.loadStats();
                }
            } else {
                this.showNotification(result.error || 'Failed to claim reward', 'error');
            }
        } catch (error) {
            console.error('Error claiming reward:', error);
            this.showNotification('Error claiming reward', 'error');
        }
    }

    showUnlockNotification(achievement) {
        const notification = document.getElementById('achievement-notification');
        const nameEl = document.getElementById('notification-achievement-name');
        const rewardEl = document.getElementById('notification-reward-gems');

        nameEl.textContent = achievement.name;
        rewardEl.textContent = this.formatNumber(achievement.reward_gems);

        notification.style.display = 'block';

        // Auto-hide after 5 seconds
        setTimeout(() => {
            notification.style.display = 'none';
        }, 5000);

        // Play sound effect (if available)
        if (window.playSound) {
            window.playSound('achievement');
        }
    }

    showNotification(message, type = 'info') {
        // Use Toast notification system
        if (window.Toast) {
            Toast[type](message);
        } else if (window.showToast) {
            window.showToast(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    // Method to check for achievements unlocked from click response
    handleAchievementUnlocks(achievementsUnlocked) {
        if (!achievementsUnlocked || achievementsUnlocked.length === 0) return;

        // Show notification for first unlocked achievement
        this.showUnlockNotification(achievementsUnlocked[0]);

        // Reload achievements to update UI
        setTimeout(() => this.loadAchievements(), 1000);
    }
}

// Initialize achievements manager when DOM is ready
let achievementsManager;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        achievementsManager = new AchievementsManager();
    });
} else {
    achievementsManager = new AchievementsManager();
}
