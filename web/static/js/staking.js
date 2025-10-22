/**
 * GEM Staking Manager
 *
 * Handles all staking operations including plan display, stake creation,
 * reward claiming, and unstaking.
 */

class StakingManager {
    constructor() {
        this.plans = [];
        this.stakes = [];
        this.selectedPlan = null;
        this.currentFilter = 'active';
        this.stakeModal = null;
        this.successModal = null;
        this.refreshInterval = null;
    }

    async init() {
        console.log('[Staking] Initializing...');

        // Initialize modals
        this.stakeModal = new bootstrap.Modal(document.getElementById('stakeModal'));
        this.successModal = new bootstrap.Modal(document.getElementById('successModal'));

        // Load data
        await this.loadBalance();
        await this.loadPlans();
        await this.loadStats();
        await this.loadStakes();

        // Setup real-time updates every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.loadStats();
            this.loadStakes();
        }, 30000);

        // Setup amount input listener for reward estimation
        document.getElementById('stake-amount').addEventListener('input', () => {
            this.updateRewardEstimates();
        });

        console.log('[Staking] Initialized successfully');
    }

    async loadBalance() {
        try {
            const token = localStorage.getItem('token');
            if (!token) return;

            const response = await fetch('/api/auth/status', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                const balance = data.gem_balance || 0;
                document.getElementById('available-balance').innerHTML = `
                    <i class="bi bi-gem"></i> <span>${this.formatNumber(balance)}</span> GEM
                `;
            }
        } catch (error) {
            console.error('[Staking] Error loading balance:', error);
        }
    }

    async loadPlans() {
        try {
            const response = await fetch('/api/staking/plans');
            const plans = await response.json();

            this.plans = plans;
            this.renderPlans(plans);
        } catch (error) {
            console.error('[Staking] Error loading plans:', error);
            this.showError('Failed to load staking plans');
        }
    }

    renderPlans(plans) {
        const container = document.getElementById('staking-plans');

        if (plans.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="bi bi-inbox" style="font-size: 3rem; color: var(--text-secondary);"></i>
                    <p class="mt-3">No staking plans available</p>
                </div>
            `;
            return;
        }

        let html = '';

        plans.forEach(plan => {
            const borderColor = plan.popular ? 'var(--primary)' :
                              plan.best_value ? 'var(--success)' :
                              'var(--border)';

            const badgeColor = plan.color === 'gem' ? 'var(--gem)' :
                             plan.color === 'primary' ? 'var(--primary)' :
                             plan.color === 'success' ? 'var(--success)' :
                             'var(--secondary)';

            html += `
                <div class="col-md-6 col-lg-3 mb-4">
                    <div class="card-modern stake-plan-card" style="border-color: ${borderColor};">
                        ${plan.popular ? '<div class="plan-badge" style="background: var(--primary);">⭐ Most Popular</div>' : ''}
                        ${plan.best_value ? '<div class="plan-badge" style="background: var(--success);">💎 Best Value</div>' : ''}

                        <div class="text-center">
                            <i class="${plan.icon} plan-icon" style="color: ${badgeColor};"></i>
                            <h4>${plan.name}</h4>
                            <div class="apr-display">${plan.apr_rate}%</div>
                            <div style="color: var(--text-secondary); margin-bottom: 1rem;">APR</div>

                            ${plan.lock_period_days > 0 ? `
                                <div class="lock-indicator mb-3">
                                    <i class="bi bi-lock-fill"></i>
                                    <span>${plan.lock_period_days} days lock</span>
                                </div>
                            ` : `
                                <div class="unlock-indicator mb-3">
                                    <i class="bi bi-unlock-fill"></i>
                                    <span>No lock period</span>
                                </div>
                            `}

                            <p style="color: var(--text-secondary); min-height: 50px;">
                                ${plan.description}
                            </p>

                            <div style="margin: 1rem 0; padding: 0.75rem; background: rgba(139, 92, 246, 0.1); border-radius: 8px;">
                                <small style="color: var(--text-secondary);">Min Stake</small>
                                <div style="font-weight: 600; color: var(--gem);">
                                    ${this.formatNumber(plan.min_stake)} GEM
                                </div>
                            </div>

                            <button class="btn-modern btn-modern-${plan.color === 'gem' ? 'primary' : plan.color} w-100"
                                    onclick="StakingManager.showStakeModal('${plan.id}')">
                                <i class="bi bi-lock-fill"></i>
                                Stake Now
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    async loadStats() {
        try {
            const token = localStorage.getItem('token');
            if (!token) return;

            const response = await fetch('/api/staking/stats', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const stats = await response.json();

                document.getElementById('active-stakes-count').textContent = stats.active_stakes_count;
                document.getElementById('total-staked').textContent = this.formatNumber(stats.total_staked_amount);
                document.getElementById('unclaimed-rewards').textContent = this.formatNumber(stats.total_unclaimed_rewards);
                document.getElementById('total-earned').textContent = this.formatNumber(stats.total_rewards_earned_all_time);
            }
        } catch (error) {
            console.error('[Staking] Error loading stats:', error);
        }
    }

    async loadStakes(status = null) {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                document.getElementById('active-stakes-list').innerHTML = `
                    <div class="alert-modern alert-modern-warning">
                        <div class="alert-modern-content">
                            <div class="alert-modern-message">Please login to view your stakes</div>
                        </div>
                    </div>
                `;
                return;
            }

            const url = status ? `/api/staking/my-stakes?status=${status}` : '/api/staking/my-stakes';
            const response = await fetch(url, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const stakes = await response.json();
                this.stakes = stakes;
                this.renderStakes(stakes);
            }
        } catch (error) {
            console.error('[Staking] Error loading stakes:', error);
        }
    }

    renderStakes(stakes) {
        const container = document.getElementById('active-stakes-list');

        if (stakes.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-inbox" style="font-size: 3rem; color: var(--text-secondary);"></i>
                    <p class="mt-3">No ${this.currentFilter} stakes found</p>
                    <button class="btn-modern btn-modern-primary mt-2" onclick="window.scrollTo({top: 0, behavior: 'smooth'})">
                        <i class="bi bi-plus-lg"></i>
                        Create Your First Stake
                    </button>
                </div>
            `;
            return;
        }

        let html = '';

        stakes.forEach(stake => {
            const statusColor = stake.status === 'active' ? 'success' : 'secondary';
            const progressPercent = stake.lock_period_days > 0 ?
                Math.min(100, ((stake.lock_period_days - stake.days_remaining) / stake.lock_period_days) * 100) : 0;

            html += `
                <div class="card-modern stake-card mb-3">
                    <div class="row align-items-center">
                        <div class="col-md-3">
                            <div class="stat-label">Staked Amount</div>
                            <div class="stat-value" style="font-size: 1.5rem;">
                                <i class="bi bi-gem"></i> ${this.formatNumber(stake.amount)}
                            </div>
                            <small class="badge badge-modern badge-modern-${statusColor}">
                                ${stake.status.toUpperCase()}
                            </small>
                        </div>

                        <div class="col-md-3">
                            <div class="stat-label">APR Rate</div>
                            <div class="stat-value" style="color: var(--gem);">
                                ${stake.apr_rate}%
                            </div>
                            ${stake.lock_period_days > 0 ? `
                                <small>${stake.lock_period_days} days lock</small>
                            ` : `
                                <small class="text-success">Flexible</small>
                            `}
                        </div>

                        <div class="col-md-3">
                            <div class="stat-label">Rewards</div>
                            <div class="stat-value" style="color: var(--success);">
                                ${this.formatNumber(stake.unclaimed_rewards)}
                            </div>
                            <small>Total earned: ${this.formatNumber(stake.total_rewards_earned)}</small>
                        </div>

                        <div class="col-md-3 text-end">
                            ${stake.status === 'active' ? `
                                ${stake.can_unstake ? `
                                    <button class="btn-modern btn-modern-success btn-modern-sm mb-2 w-100"
                                            onclick="StakingManager.unstake(${stake.id})">
                                        <i class="bi bi-unlock-fill"></i>
                                        Unstake
                                    </button>
                                ` : `
                                    <div class="countdown-timer mb-2">
                                        <i class="bi bi-clock"></i>
                                        ${stake.days_remaining} days left
                                    </div>
                                `}
                                ${stake.unclaimed_rewards > 0 ? `
                                    <button class="btn-modern btn-modern-primary btn-modern-sm w-100"
                                            onclick="StakingManager.claimRewards(${stake.id})">
                                        <i class="bi bi-gift"></i>
                                        Claim ${this.formatNumber(stake.unclaimed_rewards)} GEM
                                    </button>
                                ` : ''}
                            ` : `
                                <div class="text-muted">
                                    <i class="bi bi-check-circle"></i>
                                    Completed on ${new Date(stake.unstaked_at).toLocaleDateString()}
                                </div>
                            `}
                        </div>
                    </div>

                    ${stake.status === 'active' && stake.lock_period_days > 0 ? `
                        <div class="mt-3">
                            <div class="d-flex justify-content-between mb-2" style="font-size: 0.85rem;">
                                <span>Lock Progress</span>
                                <span>${Math.round(progressPercent)}%</span>
                            </div>
                            <div class="progress-bar-rewards">
                                <div class="progress-bar-fill" style="width: ${progressPercent}%;"></div>
                            </div>
                        </div>
                    ` : ''}

                    <div class="mt-3" style="font-size: 0.85rem; color: var(--text-secondary);">
                        <i class="bi bi-calendar"></i>
                        Staked on ${new Date(stake.staked_at).toLocaleString()}
                        ${stake.status === 'active' ? `
                            <span class="ms-3">
                                <i class="bi bi-calendar-check"></i>
                                Unlocks on ${new Date(stake.unlock_at).toLocaleString()}
                            </span>
                        ` : ''}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    filterStakes(status) {
        this.currentFilter = status;

        // Update button states
        document.querySelectorAll('.btn-group-modern button').forEach(btn => {
            btn.classList.remove('active', 'btn-modern-primary');
            btn.classList.add('btn-modern-secondary');
        });
        event.target.classList.remove('btn-modern-secondary');
        event.target.classList.add('active', 'btn-modern-primary');

        // Load stakes with filter
        this.loadStakes(status);
    }

    showStakeModal(planId) {
        const token = localStorage.getItem('token');
        if (!token) {
            window.location.href = '/login?redirect=/staking';
            return;
        }

        const plan = this.plans.find(p => p.id === planId);
        if (!plan) return;

        this.selectedPlan = plan;

        // Populate modal
        document.getElementById('modal-plan-name').textContent = plan.name;
        document.getElementById('modal-lock-period').textContent =
            plan.lock_period_days > 0 ? `${plan.lock_period_days} days` : 'Flexible (no lock)';
        document.getElementById('modal-apr-rate').textContent = `${plan.apr_rate}%`;
        document.getElementById('modal-min-stake').textContent = this.formatNumber(plan.min_stake);

        // Set min amount
        const amountInput = document.getElementById('stake-amount');
        amountInput.min = plan.min_stake;
        amountInput.value = plan.min_stake;

        // Load balance
        this.loadBalanceForModal();

        // Update estimates
        this.updateRewardEstimates();

        // Show modal
        this.stakeModal.show();
    }

    async loadBalanceForModal() {
        try {
            const token = localStorage.getItem('token');
            const response = await fetch('/api/auth/status', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                document.getElementById('modal-available-balance').textContent =
                    this.formatNumber(data.gem_balance || 0);
            }
        } catch (error) {
            console.error('[Staking] Error loading balance:', error);
        }
    }

    updateRewardEstimates() {
        const amount = parseInt(document.getElementById('stake-amount').value) || 0;

        if (!this.selectedPlan || amount === 0) {
            document.getElementById('estimated-daily').textContent = '0';
            document.getElementById('estimated-total').textContent = '0';
            return;
        }

        const dailyReward = Math.floor((amount * this.selectedPlan.apr_rate / 100) / 365);
        const days = this.selectedPlan.lock_period_days || 30; // Use 30 days for flexible
        const totalReward = dailyReward * days;

        document.getElementById('estimated-daily').textContent = this.formatNumber(dailyReward);
        document.getElementById('estimated-total').textContent = this.formatNumber(totalReward);
    }

    async confirmStake() {
        const amount = parseInt(document.getElementById('stake-amount').value);

        if (!amount || amount < this.selectedPlan.min_stake) {
            this.showError(`Minimum stake is ${this.formatNumber(this.selectedPlan.min_stake)} GEM`);
            return;
        }

        try {
            const token = localStorage.getItem('token');
            const response = await fetch('/api/staking/stake', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    plan_id: this.selectedPlan.id,
                    amount: amount
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to create stake');
            }

            // Hide stake modal
            this.stakeModal.hide();

            // Show success modal
            document.getElementById('success-amount').textContent = this.formatNumber(result.amount);
            document.getElementById('success-daily-reward').textContent =
                this.formatNumber(result.estimated_daily_reward);
            document.getElementById('success-unlock-date').textContent =
                result.unlock_at ? new Date(result.unlock_at).toLocaleString() : 'Anytime (Flexible)';

            this.successModal.show();

            // Refresh data
            await this.loadBalance();
            await this.loadStats();
            await this.loadStakes();

        } catch (error) {
            console.error('[Staking] Error creating stake:', error);
            this.showError(error.message);
        }
    }

    async claimRewards(stakeId) {
        if (!confirm('Claim your accumulated rewards?')) return;

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`/api/staking/claim-rewards/${stakeId}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to claim rewards');
            }

            this.showSuccess(`Claimed ${this.formatNumber(result.rewards_claimed)} GEM!`);

            // Refresh data
            await this.loadBalance();
            await this.loadStats();
            await this.loadStakes();

        } catch (error) {
            console.error('[Staking] Error claiming rewards:', error);
            this.showError(error.message);
        }
    }

    async unstake(stakeId) {
        if (!confirm('Unstake and return your GEM plus any remaining rewards?')) return;

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`/api/staking/unstake/${stakeId}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to unstake');
            }

            this.showSuccess(
                `Unstaked ${this.formatNumber(result.principal_returned)} GEM + ` +
                `${this.formatNumber(result.final_rewards)} GEM rewards!`
            );

            // Refresh data
            await this.loadBalance();
            await this.loadStats();
            await this.loadStakes();

        } catch (error) {
            console.error('[Staking] Error unstaking:', error);
            this.showError(error.message);
        }
    }

    formatNumber(num) {
        return new Intl.NumberFormat('en-US').format(num);
    }

    showSuccess(message) {
        // Use existing alert system if available, otherwise use alert
        if (window.showAlert) {
            window.showAlert(message, 'success');
        } else {
            alert(message);
        }
    }

    showError(message) {
        // Use existing alert system if available, otherwise use alert
        if (window.showAlert) {
            window.showAlert(message, 'danger');
        } else {
            alert(message);
        }
    }

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
}

// Create global instance
const StakingManager = new StakingManager();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    StakingManager.destroy();
});
