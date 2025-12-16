/**
 * Portfolio Module for CryptoChecker v3
 * Simple, reliable portfolio data loading
 */

window.Portfolio = {
    // State management
    portfolioData: null,
    transactions: [],
    isLoading: false,
    stocksLoaded: false,

    // Initialize portfolio - simple and reliable
    init() {
        console.log('🚀 Portfolio initializing...');

        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.loadDataWhenReady();
                this.setupTabListeners();
            });
        } else {
            this.loadDataWhenReady();
            this.setupTabListeners();
        }
    },

    // Set up tab switch listeners
    setupTabListeners() {
        // Listen for when Stocks tab is shown
        const stocksTab = document.getElementById('stocks-tab');
        if (stocksTab) {
            stocksTab.addEventListener('shown.bs.tab', () => {
                if (!this.stocksLoaded) {
                    this.loadStockHoldings();
                    this.stocksLoaded = true;
                }
            });
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
    },

    // ========== STOCK HOLDINGS FUNCTIONS ==========

    // Load stock holdings from API
    async loadStockHoldings() {
        console.log('📈 Loading stock holdings...');

        try {
            const response = await fetch('/api/stocks/portfolio/holdings', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                console.log('✅ Stock holdings loaded:', data);

                if (data.success && data.holdings) {
                    this.renderStockHoldings(data.holdings, data.summary || {});
                    return;
                }
            }

            // No holdings or error
            this.renderStockHoldings([], {});

        } catch (error) {
            console.error('💥 Stock holdings load error:', error);
            this.renderStockHoldings([], {});
        }
    },

    // Render stock holdings table
    renderStockHoldings(holdings, summary) {
        const tableBody = document.getElementById('stock-holdings-table-body');
        const emptyState = document.getElementById('stock-empty-state');

        // Calculate summary from holdings if not provided
        let totalValue = 0;
        let totalInvested = 0;
        let totalPL = 0;

        if (holdings && holdings.length > 0) {
            holdings.forEach(h => {
                totalValue += h.current_value_gem || 0;
                totalInvested += h.total_invested_gem || 0;
                totalPL += h.profit_loss_gem || 0;
            });
        }

        const totalPLPct = totalInvested > 0 ? (totalPL / totalInvested * 100) : 0;

        // Update summary stats
        this.updateElement('stock-total-value', this.formatNumber(totalValue));
        this.updateElement('stock-total-pl', this.formatNumber(totalPL));
        this.updateElement('stock-pl-pct', totalPLPct.toFixed(2));
        this.updateElement('stock-positions-count', holdings.length);

        // Apply P/L colors
        const plContainer = document.getElementById('stock-total-pl-container');
        const plPctContainer = document.getElementById('stock-pl-pct-container');
        if (plContainer) {
            plContainer.style.color = totalPL >= 0 ? 'var(--success)' : 'var(--error)';
        }
        if (plPctContainer) {
            plPctContainer.style.color = totalPLPct >= 0 ? 'var(--success)' : 'var(--error)';
        }

        if (!tableBody) return;

        if (!holdings || holdings.length === 0) {
            tableBody.innerHTML = '';
            if (emptyState) emptyState.style.display = 'block';
            return;
        }

        if (emptyState) emptyState.style.display = 'none';

        const rows = holdings.map(h => {
            const profitLoss = h.profit_loss_gem || 0;
            const profitLossPct = h.profit_loss_pct || 0;
            const plColor = profitLoss >= 0 ? 'var(--success)' : 'var(--error)';
            const plIcon = profitLoss >= 0 ? 'bi-arrow-up' : 'bi-arrow-down';

            return `
                <tr>
                    <td>
                        <div style="font-weight: var(--font-semibold); color: var(--text-primary);">${h.ticker}</div>
                        <small style="color: var(--text-muted);">${h.company_name || ''}</small>
                    </td>
                    <td class="text-end" style="color: var(--text-primary);">${this.formatNumber(h.quantity)}</td>
                    <td class="text-end" style="color: var(--text-secondary);">${this.formatNumber(h.average_buy_price_gem || 0)} GEM</td>
                    <td class="text-end" style="color: var(--text-primary);">${this.formatNumber(h.current_price_gem || 0)} GEM</td>
                    <td class="text-end" style="color: var(--text-primary);">${this.formatNumber(h.current_value_gem || 0)} GEM</td>
                    <td class="text-end" style="color: ${plColor};">
                        <i class="bi ${plIcon}"></i>
                        ${this.formatNumber(Math.abs(profitLoss))} GEM
                        <small>(${profitLossPct >= 0 ? '+' : ''}${profitLossPct.toFixed(2)}%)</small>
                    </td>
                    <td class="text-center">
                        <button class="btn-modern btn-modern-danger btn-modern-sm" 
                                onclick="Portfolio.confirmSellStock('${h.ticker}', ${h.quantity}, ${h.current_price_gem || 0})">
                            <i class="bi bi-cash-coin"></i> Sell
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        tableBody.innerHTML = rows;
        console.log('🎉 Stock holdings rendered successfully');
    },

    // Refresh stock holdings
    refreshStockHoldings() {
        console.log('🔄 Refreshing stock holdings...');
        this.loadStockHoldings();
    },

    // Confirm sell stock (opens modal or redirects)
    confirmSellStock(ticker, quantity, currentPrice) {
        if (confirm(`Sell ${quantity} shares of ${ticker} at ${this.formatNumber(currentPrice)} GEM each?`)) {
            this.sellStock(ticker, quantity);
        }
    },

    // Execute stock sale
    async sellStock(ticker, quantity) {
        try {
            const response = await fetch(`/api/stocks/${ticker}/sell`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`
                },
                body: JSON.stringify({ quantity: quantity })
            });

            const data = await response.json();

            if (data.success) {
                alert(`Successfully sold ${quantity} shares of ${ticker}!\nProceeds: ${this.formatNumber(data.net_proceeds_gem)} GEM`);
                this.loadStockHoldings(); // Refresh
                this.attemptLoad(); // Refresh main balance
            } else {
                alert(`Failed to sell: ${data.message || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('💥 Sell stock error:', error);
            alert('Failed to sell stock. Please try again.');
        }
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Portfolio.init();
});
