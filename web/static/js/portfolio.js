/**
 * Portfolio Module for CryptoChecker v3
 * Handles portfolio management, balance tracking, and transaction history
 */

window.Portfolio = {
    // State management
    portfolioData: null,
    transactions: [],
    isLoading: false,

    // Initialize portfolio
    init() {
        this.setupEventListeners();
        this.loadPortfolioData();
        console.log('Portfolio module initialized');
    },

    // Set up event listeners
    setupEventListeners() {
        // Tab switch events
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                this.handleTabSwitch(e.target.getAttribute('data-bs-target'));
            });
        });

        // Authentication state changes
        document.addEventListener('authStateChanged', () => {
            this.loadPortfolioData();
        });
    },

    // Load portfolio data
    async loadPortfolioData() {
        try {
            this.isLoading = true;

            // Load portfolio stats
            const portfolioResponse = await App.api.get('/crypto/portfolio');
            if (portfolioResponse.success) {
                this.portfolioData = portfolioResponse.portfolio;
                this.updatePortfolioDisplay();
            }

            // Show guest notice if in guest mode
            this.handleGuestModeDisplay();

        } catch (error) {
            console.error('Failed to load portfolio data:', error);
            this.showPortfolioError('Failed to load portfolio data');
        } finally {
            this.isLoading = false;
        }
    },

    // Update portfolio display
    updatePortfolioDisplay() {
        if (!this.portfolioData) return;

        const wallet = this.portfolioData.wallet || {};
        const stats = this.portfolioData.stats || {};

        // Update balance displays
        const balance = wallet.gem_balance || 0;
        const balanceUsd = (balance * 0.01).toFixed(2);

        this.updateElement('portfolio-balance', this.formatBalance(balance));
        this.updateElement('portfolio-balance-usd', balanceUsd);
        this.updateElement('current-balance', this.formatBalance(balance) + ' GEM');
        this.updateElement('balance-display', this.formatBalance(balance));
        this.updateElement('balance-usd-display', balanceUsd);

        // Update stats
        this.updateElement('total-earned', this.formatBalance(wallet.total_won || 0) + ' GEM');
        this.updateElement('games-played', stats.total_games || 0);
        this.updateElement('win-rate', ((stats.win_rate || 0) * 100).toFixed(1) + '%');

        // Update gaming stats
        this.updateElement('games-won-count', stats.games_won || 0);
        this.updateElement('games-lost-count', stats.games_lost || 0);
        this.updateElement('total-games-count', stats.total_games || 0);
        this.updateElement('win-rate-percentage', ((stats.win_rate || 0) * 100).toFixed(1) + '%');

        this.updateElement('total-wagered', this.formatBalance(wallet.total_wagered || 0) + ' GEM');
        this.updateElement('total-won', this.formatBalance(wallet.total_won || 0) + ' GEM');

        const netResult = (wallet.total_won || 0) - (wallet.total_wagered || 0);
        const netResultElement = document.getElementById('net-gaming-result');
        if (netResultElement) {
            netResultElement.textContent = this.formatBalance(netResult) + ' GEM';
            netResultElement.className = netResult >= 0 ? 'fw-bold text-success' : 'fw-bold text-danger';
        }
    },

    // Load transaction history
    async loadTransactionHistory() {
        try {
            const response = await App.api.get('/crypto/portfolio/transactions', { limit: 50 });
            if (response.success) {
                this.transactions = response.transactions || [];
                this.updateTransactionTable();
            } else {
                this.showTransactionError(response.message || 'Failed to load transactions');
            }
        } catch (error) {
            console.error('Failed to load transactions:', error);
            this.showTransactionError('Failed to load transaction history');
        }
    },

    // Update transaction table
    updateTransactionTable() {
        const tableBody = document.getElementById('transactions-table-body');
        if (!tableBody) return;

        if (!this.transactions || this.transactions.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4 text-muted">
                        ${App.isGuest ? 'Transaction history not available in guest mode' : 'No transactions found'}
                    </td>
                </tr>
            `;
            return;
        }

        const rows = this.transactions.map(transaction => this.createTransactionRow(transaction)).join('');
        tableBody.innerHTML = rows;
    },

    // Create transaction row
    createTransactionRow(transaction) {
        const date = new Date(transaction.created_at).toLocaleDateString();
        const time = new Date(transaction.created_at).toLocaleTimeString();

        const amountClass = transaction.amount >= 0 ? 'text-success' : 'text-danger';
        const amountSymbol = transaction.amount >= 0 ? '+' : '';

        return `
            <tr>
                <td>
                    <div>${date}</div>
                    <small class="text-muted">${time}</small>
                </td>
                <td>
                    <span class="badge ${this.getTransactionTypeBadge(transaction.transaction_type)}">
                        ${this.formatTransactionType(transaction.transaction_type)}
                    </span>
                </td>
                <td>
                    <div>${transaction.description || 'No description'}</div>
                    ${transaction.details ? `<small class="text-muted">${transaction.details}</small>` : ''}
                </td>
                <td class="text-end ${amountClass}">
                    <strong>${amountSymbol}${this.formatBalance(Math.abs(transaction.amount))} GEM</strong>
                </td>
                <td class="text-end">
                    ${this.formatBalance(transaction.balance_after)} GEM
                </td>
                <td>
                    <span class="badge ${this.getStatusBadge(transaction.status)}">
                        ${transaction.status || 'completed'}
                    </span>
                </td>
            </tr>
        `;
    },

    // Handle tab switch
    handleTabSwitch(target) {
        switch (target) {
            case '#transactions':
                if (this.transactions.length === 0) {
                    this.loadTransactionHistory();
                }
                break;
            case '#gaming':
                // Gaming stats are already loaded with portfolio data
                break;
        }
    },

    // Handle guest mode display
    handleGuestModeDisplay() {
        const guestNotice = document.getElementById('guest-portfolio-notice');
        if (guestNotice) {
            guestNotice.style.display = App.isGuest ? 'block' : 'none';
        }
    },

    // Utility functions
    refreshBalance() {
        App.showAlert('info', 'Refreshing balance...', 2000);
        this.loadPortfolioData();
    },

    refreshTransactions() {
        App.showAlert('info', 'Refreshing transactions...', 2000);
        this.loadTransactionHistory();
    },

    formatBalance(balance) {
        return new Intl.NumberFormat('en-US').format(balance || 0);
    },

    getTransactionTypeBadge(type) {
        const badges = {
            'deposit': 'bg-success',
            'withdrawal': 'bg-danger',
            'gaming_win': 'bg-primary',
            'gaming_loss': 'bg-warning',
            'bonus': 'bg-info',
            'fee': 'bg-secondary'
        };
        return badges[type] || 'bg-secondary';
    },

    formatTransactionType(type) {
        const types = {
            'deposit': 'Deposit',
            'withdrawal': 'Withdrawal',
            'gaming_win': 'Gaming Win',
            'gaming_loss': 'Gaming Loss',
            'bonus': 'Bonus',
            'fee': 'Fee'
        };
        return types[type] || type.charAt(0).toUpperCase() + type.slice(1);
    },

    getStatusBadge(status) {
        const badges = {
            'completed': 'bg-success',
            'pending': 'bg-warning',
            'failed': 'bg-danger',
            'cancelled': 'bg-secondary'
        };
        return badges[status] || 'bg-success';
    },

    showPortfolioError(message) {
        App.showAlert('danger', message);

        // Update displays with error state
        this.updateElement('portfolio-balance', 'Error');
        this.updateElement('current-balance', 'Error loading balance');
    },

    showTransactionError(message) {
        const tableBody = document.getElementById('transactions-table-body');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4 text-danger">
                        <i class="bi bi-exclamation-triangle"></i> ${message}
                        <br>
                        <button class="btn btn-outline-primary btn-sm mt-2" onclick="Portfolio.refreshTransactions()">
                            <i class="bi bi-arrow-clockwise"></i> Try Again
                        </button>
                    </td>
                </tr>
            `;
        }
    },

    updateElement(id, content) {
        App.updateElement(id, content);
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Portfolio will be initialized by the page_init block in template
});