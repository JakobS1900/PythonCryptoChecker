/**
 * GEM Earning System - Frontend Integration
 * Handles daily bonuses, achievements, and emergency tasks
 */

class GemEarningSystem {
    constructor() {
        this.isInitialized = false;
        this.currentBalance = 0;
        this.activeTab = 'daily-bonus';

        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    init() {
        if (this.isInitialized) return;

        console.log('🎁 Initializing GEM Earning System');

        this.setupEventListeners();
        this.checkDailyBonusStatus();
        this.checkLowBalance();

        this.isInitialized = true;
    }

    setupEventListeners() {
        // Earn GEM button
        const earnGemBtn = document.getElementById('earn-gem-btn');
        if (earnGemBtn) {
            earnGemBtn.addEventListener('click', () => this.showEarningPanel());
        }

        // Daily bonus card click
        const dailyBonusCard = document.getElementById('daily-bonus-card');
        if (dailyBonusCard) {
            dailyBonusCard.addEventListener('click', () => {
                this.showEarningPanel();
                this.switchTab('daily-bonus');
            });
        }

        // Close earning panel
        const closeBtn = document.getElementById('close-earning-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hideEarningPanel());
        }

        // Earning tabs
        const tabs = document.querySelectorAll('.earning-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // Claim daily bonus
        const claimBonusBtn = document.getElementById('claim-daily-bonus-btn');
        if (claimBonusBtn) {
            claimBonusBtn.addEventListener('click', () => this.claimDailyBonus());
        }

        // Close modals on background click
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('achievement-modal') ||
                e.target.classList.contains('task-modal')) {
                this.hideModals();
            }
        });

        // Close task modal
        const closeTaskBtn = document.getElementById('close-task-btn');
        if (closeTaskBtn) {
            closeTaskBtn.addEventListener('click', () => this.hideModals());
        }
    }

    async checkDailyBonusStatus() {
        try {
            console.log('🎁 Checking daily bonus status...');

            // Use the main App API system for consistent authentication
            const response = await App.api.get('/gaming/daily-bonus');

            console.log('🎁 Daily bonus response:', response);

            if (response.success || response.ok) {
                console.log('✅ Daily bonus status loaded successfully');
                this.updateDailyBonusStatus(response);
            } else {
                console.warn('⚠️ Daily bonus check failed:', response.status, response.error || response.detail);
                this.updateDailyBonusStatus({ success: false });
            }
        } catch (error) {
            console.error('❌ Error checking daily bonus status:', error);
            console.error('Error details:', {
                message: error.message,
                stack: error.stack,
                isAuthenticated: App.isAuthenticated,
                hasToken: !!localStorage.getItem('auth_token')
            });
            this.updateDailyBonusStatus({ success: false });
        }
    }

    updateDailyBonusStatus(data) {
        const statusText = document.getElementById('bonus-status-text');
        const statusElement = document.getElementById('daily-bonus-status');
        const bonusCard = document.getElementById('daily-bonus-card');

        if (!statusText || !statusElement || !bonusCard) return;

        if (!data.success) {
            // Not authenticated or error
            statusText.textContent = 'Login Required';
            statusElement.className = 'stat-value daily-bonus-status claimed';
            bonusCard.style.cursor = 'default';
            return;
        }

        if (data.next_claim_available) {
            // Already claimed today
            statusText.textContent = 'Claimed';
            statusElement.className = 'stat-value daily-bonus-status claimed';
            bonusCard.style.cursor = 'default';
        } else {
            // Available to claim
            statusText.textContent = 'Available!';
            statusElement.className = 'stat-value daily-bonus-status available';
            bonusCard.style.cursor = 'pointer';
        }

        // Update bonus details in panel
        const streakElement = document.getElementById('bonus-streak');
        if (streakElement && data.consecutive_days) {
            streakElement.textContent = `Current Streak: ${data.consecutive_days} days`;
        }
    }

    async checkLowBalance() {
        // Check if user has low balance to show earning opportunities
        const balanceElement = document.getElementById('gaming-balance');
        if (!balanceElement) return;

        const balanceText = balanceElement.textContent.replace(/[^\d]/g, '');
        const balance = parseInt(balanceText) || 0;
        this.currentBalance = balance;

        // Show earn button more prominently if balance is low
        const earnBtn = document.getElementById('earn-gem-btn');
        if (earnBtn && balance < 100) {
            earnBtn.classList.add('pulse-glow');
            earnBtn.title = `Low balance: ${balance} GEM - Click to earn more!`;
        }
    }

    showEarningPanel() {
        const panel = document.getElementById('gem-earning-panel');
        if (panel) {
            panel.classList.add('show');
            panel.style.display = 'block';

            // Load content for active tab
            this.loadTabContent(this.activeTab);
        }
    }

    hideEarningPanel() {
        const panel = document.getElementById('gem-earning-panel');
        if (panel) {
            panel.classList.remove('show');
            setTimeout(() => {
                panel.style.display = 'none';
            }, 400);
        }
    }

    switchTab(tabName) {
        this.activeTab = tabName;

        // Update tab buttons
        document.querySelectorAll('.earning-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // Update tab content
        document.querySelectorAll('.earning-tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}-content`);
        });

        // Load content for the new tab
        this.loadTabContent(tabName);
    }

    async loadTabContent(tabName) {
        switch (tabName) {
            case 'daily-bonus':
                await this.loadDailyBonusContent();
                break;
            case 'achievements':
                await this.loadAchievementsContent();
                break;
            case 'emergency-tasks':
                await this.loadEmergencyTasksContent();
                break;
        }
    }

    async loadDailyBonusContent() {
        // Daily bonus content is mostly static, just update status
        await this.checkDailyBonusStatus();
    }

    async loadAchievementsContent() {
        const achievementsList = document.getElementById('achievements-list');
        const unclaimedRewards = document.getElementById('unclaimed-rewards');

        if (!achievementsList) return;

        // Show loading
        achievementsList.innerHTML = `
            <div class="achievements-loading">
                <i class="fas fa-spinner fa-spin"></i>
                <span>Loading achievements...</span>
            </div>
        `;

        try {
            // Use the main App API system for consistent authentication
            const response = await App.api.get('/gaming/achievements');

            if (response.success || response.ok) {
                this.renderAchievements(response.achievements || [], response.total_unclaimed_rewards || 0);
            } else {
                achievementsList.innerHTML = `
                    <div class="achievements-loading">
                        <i class="fas fa-lock"></i>
                        <span>Login required to view achievements</span>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading achievements:', error);
            achievementsList.innerHTML = `
                <div class="achievements-loading">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>Failed to load achievements</span>
                </div>
            `;
        }
    }

    renderAchievements(achievements, totalUnclaimed) {
        const achievementsList = document.getElementById('achievements-list');
        const unclaimedRewards = document.getElementById('unclaimed-rewards');

        if (unclaimedRewards) {
            unclaimedRewards.innerHTML = `<span>Unclaimed: ${totalUnclaimed} GEM</span>`;
        }

        if (!achievements.length) {
            achievementsList.innerHTML = `
                <div class="achievements-loading">
                    <i class="fas fa-trophy"></i>
                    <span>No achievements available yet</span>
                </div>
            `;
            return;
        }

        const achievementsHtml = achievements.map(userAchievement => {
            const achievement = userAchievement.achievement;
            const progress = userAchievement.progress_percentage || 0;
            const isCompleted = userAchievement.is_completed;
            const isClaimable = isCompleted && !userAchievement.reward_claimed;

            return `
                <div class="achievement-item ${isCompleted ? 'completed' : ''}">
                    <div class="achievement-header">
                        <div class="achievement-icon">
                            <i class="fas fa-${achievement.icon || 'trophy'}"></i>
                        </div>
                        <div class="achievement-info">
                            <div class="achievement-name">${achievement.name}</div>
                            <div class="achievement-desc">${achievement.description}</div>
                        </div>
                        <div class="reward-amount">
                            <i class="fas fa-gem"></i>
                            <span>${achievement.reward_amount}</span>
                        </div>
                    </div>
                    <div class="achievement-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${progress}%"></div>
                        </div>
                        <div class="progress-text">
                            Progress: ${userAchievement.current_progress} / ${achievement.target_value} (${progress.toFixed(1)}%)
                        </div>
                    </div>
                    ${isClaimable ? `
                        <button class="claim-achievement" onclick="gemEarning.claimAchievement('${achievement.id}')">
                            <i class="fas fa-gift"></i> Claim Reward
                        </button>
                    ` : ''}
                </div>
            `;
        }).join('');

        achievementsList.innerHTML = achievementsHtml;
    }

    async loadEmergencyTasksContent() {
        const tasksList = document.getElementById('emergency-tasks-list');
        if (!tasksList) return;

        // Show loading
        tasksList.innerHTML = `
            <div class="tasks-loading">
                <i class="fas fa-spinner fa-spin"></i>
                <span>Loading emergency tasks...</span>
            </div>
        `;

        try {
            // Use the main App API system for consistent authentication
            const response = await App.api.get('/gaming/emergency-tasks');

            if (response.success || response.ok) {
                this.renderEmergencyTasks(response.available_tasks || []);
            } else {
                tasksList.innerHTML = `
                    <div class="tasks-loading">
                        <i class="fas fa-lock"></i>
                        <span>Login required for emergency tasks</span>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading emergency tasks:', error);
            tasksList.innerHTML = `
                <div class="tasks-loading">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>Failed to load emergency tasks</span>
                </div>
            `;
        }
    }

    renderEmergencyTasks(tasks) {
        const tasksList = document.getElementById('emergency-tasks-list');

        if (this.currentBalance >= 50) {
            tasksList.innerHTML = `
                <div class="low-balance-warning">
                    <h4><i class="fas fa-info-circle"></i> Balance Sufficient</h4>
                    <p>Emergency tasks are only available when your balance is below 50 GEM. Current balance: ${this.currentBalance} GEM</p>
                </div>
            `;
            return;
        }

        if (!tasks.length) {
            tasksList.innerHTML = `
                <div class="low-balance-warning">
                    <h4><i class="fas fa-clock"></i> No Tasks Available</h4>
                    <p>All emergency tasks are on cooldown or have reached daily limits. Check back later!</p>
                </div>
            `;
            return;
        }

        const tasksHtml = tasks.map(task => {
            const canComplete = task.can_complete;
            const cooldownText = task.cooldown_remaining_minutes > 0
                ? `Cooldown: ${task.cooldown_remaining_minutes}m remaining`
                : '';
            const completionsText = `${task.completions_today}/${task.max_completions_per_day} completed today`;

            return `
                <div class="emergency-task">
                    <div class="task-header">
                        <div class="task-name">${task.name}</div>
                        <div class="task-reward">
                            <i class="fas fa-gem"></i>
                            <span>${task.reward_amount} GEM</span>
                        </div>
                    </div>
                    <div class="task-description">${task.description}</div>
                    <div class="task-meta">
                        <span>${completionsText}</span>
                        ${cooldownText ? `<span class="cooldown">${cooldownText}</span>` : ''}
                    </div>
                    <button class="complete-emergency-task"
                            ${canComplete ? '' : 'disabled'}
                            onclick="gemEarning.startEmergencyTask('${task.id}', '${task.name}', '${task.description}', ${task.reward_amount})">
                        ${canComplete ? '<i class="fas fa-play"></i> Start Task' : '<i class="fas fa-clock"></i> Not Available'}
                    </button>
                </div>
            `;
        }).join('');

        tasksList.innerHTML = tasksHtml;
    }

    async claimDailyBonus() {
        const claimBtn = document.getElementById('claim-daily-bonus-btn');
        if (!claimBtn) return;

        // Disable button and show loading
        claimBtn.disabled = true;
        claimBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Claiming...</span>';

        try {
            console.log('🎁 Claiming daily bonus...');

            // Use the main App API system for consistent authentication
            const response = await App.api.post('/gaming/daily-bonus/claim');

            console.log('🎁 Daily bonus claim response:', response);

            if (response.success && response.claimed) {
                // Success - show notification and update UI
                console.log('✅ Daily bonus claimed successfully!');
                this.showNotification(`${response.message}`, 'success');

                // Update bonus status
                this.updateDailyBonusStatus({
                    success: true,
                    next_claim_available: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
                    consecutive_days: response.consecutive_days
                });

                // Update balance through Auth system and trigger refresh events
                if (window.Auth && typeof window.Auth.refreshBalance === 'function') {
                    await window.Auth.refreshBalance();
                }

                // Also update balance if game instance is available (fallback)
                if (window.game && typeof window.game.loadBalance === 'function') {
                    await window.game.loadBalance();
                }

                // Reset button
                claimBtn.innerHTML = '<i class="fas fa-check"></i> <span>Claimed Today</span>';
                claimBtn.disabled = true;
            } else {
                // Error - show message and reset button
                console.warn('⚠️ Daily bonus claim failed:', response);
                const errorMsg = response.error || response.detail || 'Failed to claim daily bonus';
                this.showNotification(errorMsg, 'error');
                claimBtn.innerHTML = '<i class="fas fa-gift"></i> <span>Claim Bonus</span>';
                claimBtn.disabled = false;
            }
        } catch (error) {
            console.error('❌ Error claiming daily bonus:', error);
            console.error('Error details:', {
                message: error.message,
                stack: error.stack,
                isAuthenticated: App.isAuthenticated,
                hasToken: !!localStorage.getItem('auth_token')
            });
            this.showNotification('Error claiming daily bonus', 'error');
            claimBtn.innerHTML = '<i class="fas fa-gift"></i> <span>Claim Bonus</span>';
            claimBtn.disabled = false;
        }
    }

    async claimAchievement(achievementId) {
        try {
            // Use the main App API system for consistent authentication
            const response = await App.api.post(`/gaming/achievements/${achievementId}/claim`);

            if (response.success || response.ok) {
                this.showNotification(response.message, 'success');

                // Reload achievements
                await this.loadAchievementsContent();

                // Update balance through Auth system and trigger refresh events
                if (window.Auth && typeof window.Auth.refreshBalance === 'function') {
                    await window.Auth.refreshBalance();
                }

                // Also update balance if game instance is available (fallback)
                if (window.game && typeof window.game.loadBalance === 'function') {
                    await window.game.loadBalance();
                }
            } else {
                this.showNotification(response.detail || response.error || 'Failed to claim achievement reward', 'error');
            }
        } catch (error) {
            console.error('Error claiming achievement:', error);
            this.showNotification('Error claiming achievement reward', 'error');
        }
    }

    startEmergencyTask(taskId, name, description, rewardAmount) {
        // Show task modal
        const modal = document.getElementById('task-modal');
        const title = document.getElementById('task-title');
        const desc = document.getElementById('task-description');
        const reward = document.getElementById('task-reward-amount');
        const action = document.getElementById('task-action');
        const completeBtn = document.getElementById('complete-task-btn');

        if (!modal) return;

        title.textContent = name;
        desc.textContent = description;
        reward.textContent = rewardAmount;

        // Set up task action based on type
        if (name.toLowerCase().includes('advertisement') || name.toLowerCase().includes('ad')) {
            action.innerHTML = `
                <div style="color: #9ca3af; margin-bottom: 1rem;">
                    <i class="fas fa-tv" style="font-size: 2rem; margin-bottom: 0.5rem;"></i>
                    <p>Simulated advertisement viewing</p>
                    <div style="font-size: 0.875rem; opacity: 0.7;">Click "Complete Task" to simulate watching an ad</div>
                </div>
            `;
        } else if (name.toLowerCase().includes('survey')) {
            action.innerHTML = `
                <div style="color: #9ca3af; margin-bottom: 1rem;">
                    <i class="fas fa-clipboard-list" style="font-size: 2rem; margin-bottom: 0.5rem;"></i>
                    <p>Quick satisfaction survey</p>
                    <div style="font-size: 0.875rem; opacity: 0.7;">Rate your gaming experience: ⭐⭐⭐⭐⭐</div>
                </div>
            `;
        } else {
            action.innerHTML = `
                <div style="color: #9ca3af; margin-bottom: 1rem;">
                    <i class="fas fa-gamepad" style="font-size: 2rem; margin-bottom: 0.5rem;"></i>
                    <p>Simple mini challenge</p>
                    <div style="font-size: 0.875rem; opacity: 0.7;">Complete the task to earn GEM</div>
                </div>
            `;
        }

        // Set up completion handler
        completeBtn.onclick = () => this.completeEmergencyTask(taskId);

        modal.style.display = 'flex';
    }

    async completeEmergencyTask(taskId) {
        const completeBtn = document.getElementById('complete-task-btn');
        if (!completeBtn) return;

        // Disable button and show loading
        completeBtn.disabled = true;
        completeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Completing...';

        try {
            // Use the main App API system for consistent authentication
            const response = await App.api.post(`/gaming/emergency-tasks/${taskId}/complete`);

            if (response.success) {
                this.showNotification(response.message, 'success');
                this.hideModals();

                // Reload emergency tasks
                await this.loadEmergencyTasksContent();

                // Update balance through Auth system and trigger refresh events
                if (window.Auth && typeof window.Auth.refreshBalance === 'function') {
                    await window.Auth.refreshBalance();
                }

                // Also update balance if game instance is available (fallback)
                if (window.game && typeof window.game.loadBalance === 'function') {
                    await window.game.loadBalance();
                }
            } else {
                this.showNotification(response.error || 'Failed to complete task', 'error');
                completeBtn.innerHTML = '<i class="fas fa-check"></i> Complete Task';
                completeBtn.disabled = false;
            }
        } catch (error) {
            console.error('Error completing emergency task:', error);
            this.showNotification('Error completing task', 'error');
            completeBtn.innerHTML = '<i class="fas fa-check"></i> Complete Task';
            completeBtn.disabled = false;
        }
    }

    hideModals() {
        const achievementModal = document.getElementById('achievement-modal');
        const taskModal = document.getElementById('task-modal');

        if (achievementModal) achievementModal.style.display = 'none';
        if (taskModal) taskModal.style.display = 'none';
    }

    showNotification(message, type = 'info') {
        // Use the existing game notification system if available
        if (window.game && typeof window.game.showNotification === 'function') {
            window.game.showNotification(message, type);
        } else {
            // Fallback notification
            console.log(`${type.toUpperCase()}: ${message}`);

            // Create a simple notification
            const notification = document.createElement('div');
            notification.className = `toast-notification ${type}`;
            notification.textContent = message;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: ${type === 'success' ? '#4ade80' : type === 'error' ? '#ef4444' : '#3b82f6'};
                color: white;
                padding: 1rem 1.5rem;
                border-radius: 8px;
                z-index: 9999;
                animation: slideInRight 0.3s ease;
            `;

            document.body.appendChild(notification);

            setTimeout(() => {
                notification.style.animation = 'slideOutRight 0.3s ease';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }
    }

    getAuthHeaders() {
        const token = localStorage.getItem('auth_token');
        const headers = {
            'Content-Type': 'application/json'
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        return headers;
    }

    // Public method to trigger achievement checks (can be called from game logic)
    async checkAchievementProgress(eventType, value) {
        // This could be called when users place bets, win games, etc.
        // For now, achievements are processed server-side, but we could add
        // client-side progress tracking here if needed
        console.log(`Achievement check: ${eventType} = ${value}`);
    }

    // Public method to update balance and check for low balance warnings
    updateBalance(newBalance) {
        this.currentBalance = newBalance;
        this.checkLowBalance();
    }
}

// Initialize the GEM earning system
const gemEarning = new GemEarningSystem();

// Make it globally available
window.gemEarning = gemEarning;

// CSS for notification animations
const style = document.createElement('style');
style.textContent = `
@keyframes slideInRight {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

@keyframes slideOutRight {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(100%); opacity: 0; }
}

.pulse-glow {
    animation: pulse-glow-btn 2s ease-in-out infinite alternate;
}

@keyframes pulse-glow-btn {
    from { box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3); }
    to { box-shadow: 0 8px 25px rgba(245, 158, 11, 0.6); }
}
`;
document.head.appendChild(style);

console.log('🎁 GEM Earning System loaded successfully');