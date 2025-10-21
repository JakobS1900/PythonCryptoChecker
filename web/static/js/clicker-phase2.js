/**
 * GEM Clicker Phase 2: Prestige & Power-ups
 * Extends EnhancedClickerGame with Phase 2 functionality
 */

// Extend the EnhancedClickerGame class with Phase 2 methods
if (typeof EnhancedClickerGame !== 'undefined') {
    // Phase 2: Load Prestige Data
    EnhancedClickerGame.prototype.loadPrestigeData = async function() {
        try {
            // Load prestige preview
            const previewResponse = await fetch('/api/clicker/prestige/preview', {
                headers: this.getAuthHeaders(),
                credentials: 'include'
            });
            const previewData = await previewResponse.json();
            if (previewData.success && previewData.data) {
                this.updatePrestigePreview(previewData.data);
            }

            // Load prestige shop
            const shopResponse = await fetch('/api/clicker/prestige/shop', {
                headers: this.getAuthHeaders(),
                credentials: 'include'
            });
            const shopData = await shopResponse.json();
            if (shopData.success && shopData.data) {
                this.renderPrestigeShop(shopData.data);
            }
        } catch (error) {
            console.error('Failed to load prestige data:', error);
        }
    };

    EnhancedClickerGame.prototype.updatePrestigePreview = function(data) {
        document.getElementById('prestige-points').textContent = data.current_pp || 0;
        document.getElementById('prestige-level').textContent = data.prestige_level || 0;
        document.getElementById('preview-pp').textContent = data.pp_to_gain || 0;

        // Get bonuses from new_bonuses object
        const newBonuses = data.new_bonuses || {};
        const clickBonus = newBonuses.click_multiplier || 1.0;
        const energyBonus = newBonuses.energy_regen_multiplier || 1.0;
        const chanceBonus = newBonuses.bonus_chance_multiplier || 1.0;

        document.getElementById('preview-click-bonus').textContent = ((clickBonus - 1) * 100).toFixed(0);
        document.getElementById('preview-energy-bonus').textContent = ((energyBonus - 1) * 100).toFixed(0);
        document.getElementById('preview-chance-bonus').textContent = ((chanceBonus - 1) * 100).toFixed(0);

        const prestigeBtn = document.getElementById('prestige-btn');
        const warning = document.getElementById('prestige-warning');

        if (data.can_prestige) {
            prestigeBtn.disabled = false;
            warning.textContent = `Gain ${data.pp_to_gain} PP and reset progress!`;
            prestigeBtn.onclick = () => this.handlePrestige();
        } else {
            prestigeBtn.disabled = true;
            warning.textContent = data.reason || 'Requires 100,000 total GEM earned';
        }
    };

    EnhancedClickerGame.prototype.renderPrestigeShop = function(data) {
        const container = document.getElementById('prestige-shop-items');
        if (!data.shop_items || data.shop_items.length === 0) {
            container.innerHTML = '<div class="no-active-powerups">No items available</div>';
            return;
        }

        container.innerHTML = data.shop_items.map(item => {
            const owned = item.purchased;
            return `
                <div class="prestige-shop-item ${owned ? 'owned' : ''}">
                    <div class="prestige-shop-item-header">
                        <div class="prestige-shop-item-name">${item.name}</div>
                        <div class="prestige-shop-item-cost">${item.cost} PP</div>
                    </div>
                    <div class="prestige-shop-item-desc">${item.description}</div>
                    <button class="prestige-shop-item-btn"
                            onclick="window.ClickerGame.buyPrestigeItem('${item.id}')"
                            ${owned || data.current_pp < item.cost ? 'disabled' : ''}>
                        ${owned ? 'OWNED' : 'BUY'}
                    </button>
                </div>
            `;
        }).join('');
    };

    EnhancedClickerGame.prototype.handlePrestige = async function() {
        if (!confirm('Are you sure? This will reset your progress but give you permanent bonuses!')) {
            return;
        }

        try {
            const response = await fetch('/api/clicker/prestige', {
                method: 'POST',
                headers: this.getAuthHeaders(),
                credentials: 'include'
            });

            const data = await response.json();
            if (data.success) {
                this.showMessage(`Prestiged! Gained ${data.data.pp_gained} Prestige Points!`, 'success');
                // Reload everything
                await this.loadStats();
                await this.loadPrestigeData();
            } else {
                this.showMessage(data.error || 'Failed to prestige', 'error');
            }
        } catch (error) {
            console.error('Prestige error:', error);
            this.showMessage('Failed to prestige', 'error');
        }
    };

    EnhancedClickerGame.prototype.buyPrestigeItem = async function(itemId) {
        try {
            const response = await fetch(`/api/clicker/prestige/shop/${itemId}`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                credentials: 'include'
            });

            const data = await response.json();
            if (data.success) {
                this.showMessage('Prestige item purchased!', 'success');
                await this.loadPrestigeData();
            } else {
                this.showMessage(data.error || 'Failed to purchase', 'error');
            }
        } catch (error) {
            console.error('Purchase error:', error);
            this.showMessage('Failed to purchase', 'error');
        }
    };

    // Phase 2: Load Power-ups Data
    EnhancedClickerGame.prototype.loadPowerupsData = async function() {
        try {
            // Load available power-ups
            const response = await fetch('/api/clicker/powerups', {
                headers: this.getAuthHeaders(),
                credentials: 'include'
            });
            const data = await response.json();
            if (data.success && data.data) {
                this.renderPowerups(data.data);
            }

            // Load active power-ups
            await this.loadActivePowerups();
        } catch (error) {
            console.error('Failed to load power-ups:', error);
        }
    };

    EnhancedClickerGame.prototype.loadActivePowerups = async function() {
        try {
            const response = await fetch('/api/clicker/powerups/active', {
                headers: this.getAuthHeaders(),
                credentials: 'include'
            });
            const data = await response.json();
            if (data.success && data.data) {
                this.renderActivePowerups(data.data.active_powerups || []);
            }
        } catch (error) {
            console.error('Failed to load active power-ups:', error);
        }
    };

    EnhancedClickerGame.prototype.renderPowerups = function(data) {
        const container = document.getElementById('powerups-shop-items');
        if (!data.powerups || data.powerups.length === 0) {
            container.innerHTML = '<div class="no-active-powerups">No power-ups available</div>';
            return;
        }

        container.innerHTML = data.powerups.map(powerup => {
            const onCooldown = powerup.cooldown_remaining > 0;
            return `
                <div class="powerup-item ${onCooldown ? 'on-cooldown' : ''}">
                    <div class="powerup-item-header">
                        <div class="powerup-item-name">${powerup.name}</div>
                        <div class="powerup-item-cost">${powerup.cost} GEM</div>
                    </div>
                    <div class="powerup-item-desc">${powerup.description}</div>
                    <div class="powerup-item-duration">Duration: ${powerup.duration}s</div>
                    ${onCooldown ? `<div class="powerup-item-cooldown">Cooldown: ${powerup.cooldown_remaining}s</div>` : ''}
                    <button class="powerup-item-btn"
                            onclick="window.ClickerGame.activatePowerup('${powerup.type}')"
                            ${onCooldown || this.currentBalance < powerup.cost ? 'disabled' : ''}>
                        ACTIVATE
                    </button>
                </div>
            `;
        }).join('');
    };

    EnhancedClickerGame.prototype.renderActivePowerups = function(activePowerups) {
        const container = document.getElementById('active-powerups-list');
        if (!activePowerups || activePowerups.length === 0) {
            container.innerHTML = '<div class="no-active-powerups">No active power-ups</div>';
            return;
        }

        container.innerHTML = activePowerups.map(powerup => `
            <div class="active-powerup-item">
                <div class="active-powerup-name">${powerup.name}</div>
                <div class="active-powerup-time">${powerup.time_remaining}s left</div>
            </div>
        `).join('');
    };

    EnhancedClickerGame.prototype.activatePowerup = async function(powerupType) {
        try {
            const response = await fetch(`/api/clicker/powerups/${powerupType}/activate`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                credentials: 'include'
            });

            const data = await response.json();
            if (data.success) {
                this.showMessage(`Power-up activated: ${powerupType}!`, 'success');
                await this.loadPowerupsData();
                await this.loadStats(); // Update balance
            } else {
                this.showMessage(data.error || 'Failed to activate', 'error');
            }
        } catch (error) {
            console.error('Activate power-up error:', error);
            this.showMessage('Failed to activate power-up', 'error');
        }
    };

    EnhancedClickerGame.prototype.startPrestigeRefresh = function() {
        setInterval(() => {
            this.loadPrestigeData();
        }, 10000); // Refresh every 10 seconds
    };

    EnhancedClickerGame.prototype.startPowerupsRefresh = function() {
        setInterval(() => {
            this.loadPowerupsData();
        }, 5000); // Refresh every 5 seconds
    };

    console.log('✓ Phase 2 (Prestige & Power-ups) loaded successfully!');
}
