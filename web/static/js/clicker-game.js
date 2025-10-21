/**
 * Enhanced GEM Clicker Game - Phase 1
 * Features: Upgrades, Energy System, Combos, Auto-Clicker, Visual Effects
 */

class EnhancedClickerGame {
    constructor() {
        // DOM Elements
        this.clickBtn = document.getElementById('click-btn');
        this.gemBalance = document.getElementById('gem-balance');
        this.energyCurrent = document.getElementById('energy-current');
        this.energyMax = document.getElementById('energy-max');
        this.energyBar = document.getElementById('energy-bar');
        this.comboDisplay = document.getElementById('combo-display');
        this.comboCount = document.getElementById('combo-count');
        this.comboMultiplier = document.getElementById('combo-multiplier');
        this.autoClickerDisplay = document.getElementById('auto-clicker-display');
        this.autoRate = document.getElementById('auto-rate');
        this.autoInterval = document.getElementById('auto-interval');
        this.autoAccumulated = document.getElementById('auto-accumulated');
        this.totalClicksDisplay = document.getElementById('total-clicks');
        this.totalEarnedDisplay = document.getElementById('total-earned');
        this.bestComboDisplay = document.getElementById('best-combo');
        this.clickValue = document.getElementById('click-value');
        this.upgradeContent = document.getElementById('upgrade-content');

        // Game State
        this.currentBalance = 0;
        this.currentEnergy = 100;
        this.maxEnergy = 100;
        this.currentCombo = 0;
        this.comboTimeout = null;
        this.stats = {};
        this.upgrades = {};
        this.currentCategory = 'click_power';

        this.init();
    }

    async init() {
        console.log('Initializing Enhanced Clicker Game...');

        this.setupEventListeners();
        await this.loadStats();
        await this.loadUpgrades();
        this.startEnergyRegen();
        this.startAutoClickerTick();

        console.log('Enhanced Clicker Game initialized!');
    }

    setupEventListeners() {
        // Click button
        this.clickBtn.addEventListener('click', () => this.handleClick());

        // Upgrade tabs
        document.querySelectorAll('.upgrade-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                document.querySelectorAll('.upgrade-tab').forEach(t => t.classList.remove('active'));
                e.target.classList.add('active');
                this.currentCategory = e.target.dataset.category;
                this.renderUpgrades();
            });
        });
    }

    getAuthHeaders() {
        const headers = { 'Content-Type': 'application/json' };

        try {
            if (window.Auth?.getStoredToken) {
                const token = window.Auth.getStoredToken();
                if (token) {
                    headers['Authorization'] = `Bearer ${token}`;
                    return headers;
                }
            }

            const token = localStorage.getItem('auth_token');
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        } catch (e) {
            console.warn('Error getting auth headers:', e);
        }

        return headers;
    }

    async loadStats() {
        try {
            const response = await fetch('/api/clicker/stats', {
                headers: this.getAuthHeaders(),
                credentials: 'include'
            });

            const data = await response.json();
            if (data.success && data.data) {
                this.stats = data.data.stats;
                this.currentBalance = data.data.balance;
                this.currentEnergy = this.stats.current_energy || 100;
                this.maxEnergy = this.stats.max_energy || 100;

                this.updateUI();
            }
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    async loadUpgrades() {
        try {
            const response = await fetch('/api/clicker/upgrades', {
                headers: this.getAuthHeaders(),
                credentials: 'include'
            });

            const data = await response.json();
            if (data.success && data.data) {
                this.upgrades = data.data;
                this.renderUpgrades();
            }
        } catch (error) {
            console.error('Failed to load upgrades:', error);
        }
    }

    updateUI() {
        // Balance
        this.gemBalance.textContent = Math.floor(this.currentBalance);

        // Energy
        this.energyCurrent.textContent = this.currentEnergy;
        this.energyMax.textContent = this.maxEnergy;
        const energyPercent = (this.currentEnergy / this.maxEnergy) * 100;
        this.energyBar.style.width = `${energyPercent}%`;

        // Disable click button if no energy
        if (this.currentEnergy <= 0) {
            this.clickBtn.disabled = true;
            this.clickBtn.style.opacity = '0.5';
        } else {
            this.clickBtn.disabled = false;
            this.clickBtn.style.opacity = '1';
        }

        // Stats
        this.totalClicksDisplay.textContent = this.stats.total_clicks || 0;
        this.totalEarnedDisplay.textContent = Math.floor(this.stats.total_gems_earned || 0);
        this.bestComboDisplay.textContent = this.stats.best_combo || 0;

        // Click value display
        const minReward = this.stats.click_power_min || 10;
        const maxReward = this.stats.click_power_max || 100;
        this.clickValue.textContent = `+${minReward}-${maxReward}`;

        // Auto-clicker display
        const autoLevel = this.stats.auto_clicker_level || 0;
        if (autoLevel > 0) {
            this.autoClickerDisplay.style.display = 'flex';
            this.autoRate.textContent = this.stats.auto_clicker_rate || 0;
            this.autoInterval.textContent = this.stats.auto_clicker_interval || 10;
            this.autoAccumulated.textContent = Math.floor(this.stats.auto_click_accumulated || 0);
        } else {
            this.autoClickerDisplay.style.display = 'none';
        }
    }

    async handleClick() {
        if (this.currentEnergy <= 0) {
            this.showMessage('No energy! Wait for regeneration...', 'warning');
            return;
        }

        const rect = this.clickBtn.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        // Visual feedback
        this.clickBtn.style.transform = 'scale(0.95)';
        setTimeout(() => {
            this.clickBtn.style.transform = '';
        }, 150);

        try {
            const response = await fetch('/api/clicker/click', {
                method: 'POST',
                headers: this.getAuthHeaders(),
                credentials: 'include'
            });

            const data = await response.json();

            if (data.success && data.data) {
                const reward = data.data.reward;
                const newBalance = data.data.new_balance;
                const newEnergy = data.data.current_energy;
                const combo = data.data.combo || 0;
                const comboMultiplier = data.data.combo_multiplier || 1.0;

                // Update state
                this.currentBalance = newBalance;
                this.currentEnergy = newEnergy;
                this.currentCombo = combo;

                // Sync navbar balance immediately
                if (window.Auth && window.Auth.currentUser) {
                    window.Auth.currentUser.wallet_balance = newBalance;
                    window.Auth.updateBalanceDisplays();
                } else if (window.App && window.App.user) {
                    window.App.user.wallet_balance = newBalance;
                    if (window.Auth) {
                        window.Auth.updateBalanceDisplays();
                    }
                }

                // Update stats
                this.stats.total_clicks = (this.stats.total_clicks || 0) + 1;
                this.stats.total_gems_earned = (this.stats.total_gems_earned || 0) + reward;
                if (combo > (this.stats.best_combo || 0)) {
                    this.stats.best_combo = combo;
                }

                // Visual effects
                this.createFloatingReward(centerX, centerY, reward, combo > 0);
                this.createParticles(centerX, centerY, reward);

                // Combo display
                if (combo >= 3) {
                    this.showCombo(combo, comboMultiplier);
                } else {
                    this.hideCombo();
                }

                // Update UI
                this.updateUI();

                // Update navbar balance
                if (window.updateNavbarBalance) {
                    window.updateNavbarBalance(newBalance);
                }

                // Reset combo timeout
                this.resetComboTimeout();

            } else {
                console.error('Click failed:', data.message);
                this.showMessage(data.message || 'Click failed', 'error');
            }
        } catch (error) {
            console.error('Click error:', error);
            this.showMessage('Network error', 'error');
        }
    }

    showCombo(count, multiplier) {
        this.comboDisplay.style.display = 'block';
        this.comboCount.textContent = count;
        const bonusPercent = Math.round((multiplier - 1) * 100);
        this.comboMultiplier.textContent = bonusPercent;
    }

    hideCombo() {
        this.comboDisplay.style.display = 'none';
        this.currentCombo = 0;
    }

    resetComboTimeout() {
        if (this.comboTimeout) {
            clearTimeout(this.comboTimeout);
        }

        // Hide combo after 3 seconds of no clicks
        this.comboTimeout = setTimeout(() => {
            this.hideCombo();
        }, 3000);
    }

    createFloatingReward(x, y, amount, isCombo) {
        const reward = document.createElement('div');
        reward.className = 'floating-reward';
        reward.textContent = `+${amount}`;
        reward.style.cssText = `
            position: fixed;
            left: ${x - 30}px;
            top: ${y - 20}px;
            font-size: ${isCombo ? '2em' : '1.5em'};
            font-weight: bold;
            color: ${isCombo ? '#8b5cf6' : '#10b981'};
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            pointer-events: none;
            z-index: 10000;
            animation: floatUp 1.5s ease-out forwards;
        `;

        if (!document.querySelector('#float-up-style')) {
            const style = document.createElement('style');
            style.id = 'float-up-style';
            style.textContent = `
                @keyframes floatUp {
                    0% { transform: translateY(0) scale(1); opacity: 1; }
                    100% { transform: translateY(-100px) scale(1.5); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(reward);
        setTimeout(() => reward.remove(), 1500);
    }

    createParticles(x, y, amount) {
        const count = Math.min(Math.floor(amount / 20), 8);

        for (let i = 0; i < count; i++) {
            setTimeout(() => {
                const particle = document.createElement('div');
                particle.textContent = '💎';

                const angle = (Math.PI * 2 * i) / count;
                const distance = 50 + Math.random() * 30;
                const targetX = Math.cos(angle) * distance;
                const targetY = Math.sin(angle) * distance;

                particle.style.cssText = `
                    position: fixed;
                    left: ${x}px;
                    top: ${y}px;
                    font-size: ${12 + Math.random() * 6}px;
                    pointer-events: none;
                    z-index: 10000;
                    animation: particleFly 1s ease-out forwards;
                    --target-x: ${targetX}px;
                    --target-y: ${targetY}px;
                `;

                if (!document.querySelector('#particle-fly-style')) {
                    const style = document.createElement('style');
                    style.id = 'particle-fly-style';
                    style.textContent = `
                        @keyframes particleFly {
                            0% { transform: translate(0, 0) scale(1); opacity: 1; }
                            100% { transform: translate(var(--target-x), var(--target-y)) scale(0); opacity: 0; }
                        }
                    `;
                    document.head.appendChild(style);
                }

                document.body.appendChild(particle);
                setTimeout(() => particle.remove(), 1000);
            }, i * 50);
        }
    }

    renderUpgrades() {
        const category = this.upgrades[this.currentCategory];
        if (!category) {
            this.upgradeContent.innerHTML = '<div class="upgrade-loading">No upgrades available</div>';
            return;
        }

        const currentLevel = category.current_level;
        const upgrades = category.upgrades;

        let html = '';

        // Show previous levels (grayed out)
        for (let level = 1; level < currentLevel; level++) {
            if (upgrades[level]) {
                const upgrade = upgrades[level];
                html += this.renderUpgradeItem(upgrade, level, 'purchased');
            }
        }

        // Show current level
        if (upgrades[currentLevel]) {
            html += this.renderUpgradeItem(upgrades[currentLevel], currentLevel, 'current');
        }

        // Show next level
        const nextLevel = currentLevel + 1;
        if (upgrades[nextLevel]) {
            const canAfford = this.currentBalance >= upgrades[nextLevel].cost;
            html += this.renderUpgradeItem(upgrades[nextLevel], nextLevel, canAfford ? 'available' : 'locked');
        } else {
            html += `
                <div class="upgrade-item max-level">
                    <div class="upgrade-header">
                        <div class="upgrade-name">MAX LEVEL</div>
                        <div class="upgrade-level">MAXED</div>
                    </div>
                    <div class="upgrade-description">You've reached the maximum level for this upgrade!</div>
                </div>
            `;
        }

        this.upgradeContent.innerHTML = html;

        // Add buy button listeners
        document.querySelectorAll('.upgrade-buy-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const category = btn.dataset.category;
                this.purchaseUpgrade(category);
            });
        });
    }

    renderUpgradeItem(upgrade, level, status) {
        const isCurrent = status === 'current';
        const isPurchased = status === 'purchased';
        const isAvailable = status === 'available';
        const isLocked = status === 'locked';

        const canAfford = this.currentBalance >= upgrade.cost;

        return `
            <div class="upgrade-item ${isCurrent ? 'current' : ''} ${isPurchased ? 'max-level' : ''}">
                <div class="upgrade-header">
                    <div class="upgrade-name">${upgrade.name}</div>
                    <div class="upgrade-level">Level ${level}</div>
                </div>
                <div class="upgrade-description">${upgrade.description}</div>
                <div class="upgrade-footer">
                    ${isPurchased ?
                        '<div class="upgrade-cost" style="color: #10b981;">OWNED</div>' :
                        isCurrent ?
                        '<div class="upgrade-cost" style="color: #10b981;">ACTIVE</div>' :
                        `<div class="upgrade-cost"><i class="bi bi-gem"></i> ${upgrade.cost.toLocaleString()}</div>`
                    }
                    ${isAvailable && !isCurrent && !isPurchased ?
                        `<button class="upgrade-buy-btn" data-category="${this.currentCategory}" ${!canAfford ? 'disabled' : ''}>
                            ${canAfford ? 'Buy' : 'Not Enough GEM'}
                        </button>` :
                        ''
                    }
                </div>
            </div>
        `;
    }

    async purchaseUpgrade(category) {
        try {
            const response = await fetch(`/api/clicker/upgrade/${category}`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                credentials: 'include'
            });

            const data = await response.json();

            if (data.success && data.data) {
                this.currentBalance = data.data.new_balance;
                this.upgrades[category].current_level = data.data.new_level;

                // Reload stats to get updated values
                await this.loadStats();
                this.renderUpgrades();

                this.showMessage(`Upgrade purchased! Now at level ${data.data.new_level}`, 'success');

                // Update navbar balance
                if (window.updateNavbarBalance) {
                    window.updateNavbarBalance(this.currentBalance);
                }
            } else {
                this.showMessage(data.message || 'Purchase failed', 'error');
            }
        } catch (error) {
            console.error('Purchase error:', error);
            this.showMessage('Network error', 'error');
        }
    }

    startEnergyRegen() {
        setInterval(() => {
            if (this.currentEnergy < this.maxEnergy) {
                this.currentEnergy = Math.min(this.currentEnergy + 1, this.maxEnergy);
                this.updateUI();
            }
        }, 10000); // Regen 1 energy every 10 seconds
    }

    startAutoClickerTick() {
        setInterval(async () => {
            const autoLevel = this.stats.auto_clicker_level || 0;
            if (autoLevel > 0) {
                // Just refresh stats to show accumulated amount
                await this.loadStats();
            }
        }, 5000); // Check every 5 seconds
    }

    showMessage(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type === 'warning' ? 'warning' : 'success'}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            z-index: 10000;
            min-width: 250px;
            animation: slideIn 0.3s ease-out;
        `;

        if (!document.querySelector('#slide-in-style')) {
            const style = document.createElement('style');
            style.id = 'slide-in-style';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(400px); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.ClickerGame = new EnhancedClickerGame();
    console.log('🎮 Enhanced Clicker Game with Upgrades loaded!');
});
