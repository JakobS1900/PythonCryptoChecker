/**
 * Portfolio Module for CryptoChecker v3
 * Simple, reliable portfolio data loading
 */

window.Portfolio = {
    // State management
    portfolioData: null,
    transactions: [],
    isLoading: false,

    // Initialize portfolio - simple and reliable
    init() {
        console.log('🚀 Portfolio initializing...');

        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.loadDataWhenReady();
            });
        } else {
            this.loadDataWhenReady();
        }
    },

    // Load data when everything is ready
    loadDataWhenReady() {
        // Try multiple strategies to ensure data loads
        this.attemptLoad();

        // Fallback attempts
        setTimeout(() => this.attemptLoad(), 1000);
        setTimeout(() => this.attemptLoad(), 3000);
    },

    // Simple load attempt
    async attemptLoad() {
        try {
            console.log('📊 Attempting to load portfolio data...');

            // Make direct API call
            const response = await fetch('/api/crypto/portfolio', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                console.log('✅ Portfolio data loaded:', data);

                if (data.success && data.portfolio) {
                    this.portfolioData = data.portfolio;
                    this.updateDisplay();
                    return;
                }
            }

            console.log('❌ API call failed, response:', response.status);

        } catch (error) {
            console.error('💥 Portfolio load error:', error);
        }

        // If we get here, the load failed - show error
        this.showError();
    },

    // Update all display elements
    updateDisplay() {
        if (!this.portfolioData) return;

        const wallet = this.portfolioData.wallet || {};
        const stats = this.portfolioData.stats || {};

        // Update balance displays
        const balance = wallet.gem_balance || 0;
        const balanceUsd = (balance * 0.01).toFixed(2);

        this.updateElement('portfolio-balance', this.formatNumber(balance));
        this.updateElement('portfolio-balance-usd', balanceUsd);
        this.updateElement('current-balance', this.formatNumber(balance) + ' GEM');
        this.updateElement('balance-display', this.formatNumber(balance));
        this.updateElement('balance-usd-display', balanceUsd);

        // Update stats
        this.updateElement('total-earned', this.formatNumber(wallet.total_won || 0) + ' GEM');
        this.updateElement('games-played', stats.total_games || 0);
        this.updateElement('win-rate', ((stats.win_rate || 0) * 100).toFixed(1) + '%');

        // Update gaming stats
        this.updateElement('games-won-count', stats.games_won || 0);
        this.updateElement('games-lost-count', stats.games_lost || 0);
        this.updateElement('total-games-count', stats.total_games || 0);
        this.updateElement('win-rate-percentage', ((stats.win_rate || 0) * 100).toFixed(1) + '%');

        this.updateElement('total-wagered', this.formatNumber(wallet.total_wagered || 0) + ' GEM');
        this.updateElement('total-won', this.formatNumber(wallet.total_won || 0) + ' GEM');

        const netResult = (wallet.total_won || 0) - (wallet.total_wagered || 0);
        const netResultElement = document.getElementById('net-gaming-result');
        if (netResultElement) {
            netResultElement.textContent = this.formatNumber(netResult) + ' GEM';
            netResultElement.className = netResult >= 0 ? 'fw-bold text-success' : 'fw-bold text-danger';
        }

        console.log('🎉 Portfolio display updated successfully');
    },

    // Show error state
    showError() {
        console.log('❌ Showing portfolio error state');
        this.updateElement('portfolio-balance', 'Error');
        this.updateElement('current-balance', 'Error loading balance');
    },

    // Format numbers
    formatNumber(num) {
        return new Intl.NumberFormat('en-US').format(num || 0);
    },

    // Update element safely
    updateElement(id, content) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = content;
        }
    },

    // Manual refresh function
    refreshBalance() {
        console.log('🔄 Manual refresh requested');
        this.loadDataWhenReady();
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Portfolio.init();
});
