/**
 * Stock Market JavaScript
 * Handles stock browsing, searching, filtering, and trading
 */

class StockMarket {
    constructor() {
        this.stocks = [];
        this.filteredStocks = [];
        this.userBalance = 0;
        this.portfolioValue = 0;
        this.currentView = 'grid';
        this.currentSort = 'ticker';
        this.currentSector = '';
        this.searchQuery = '';

        this.init();
    }

    async init() {
        console.log('🏢 Initializing Stock Market...');

        // Bind event listeners
        this.bindEvents();

        // Load initial data
        await this.loadUserBalance();
        await this.loadPortfolioSummary();
        await this.loadStocks();

        // Start auto-refresh
        this.startAutoRefresh();
    }

    bindEvents() {
        // Search
        document.getElementById('stock-search')?.addEventListener('input', (e) => {
            this.searchQuery = e.target.value;
            this.filterStocks();
        });

        // Sector filter
        document.getElementById('sector-filter')?.addEventListener('change', (e) => {
            this.currentSector = e.target.value;
            this.filterStocks();
        });

        // Sort
        document.getElementById('sort-by')?.addEventListener('change', (e) => {
            this.currentSort = e.target.value;
            this.sortAndRender();
        });

        // View toggle
        document.getElementById('view-toggle')?.addEventListener('click', () => {
            this.toggleView();
        });

        // Buy quantity change
        document.getElementById('buy-quantity')?.addEventListener('input', () => {
            this.updateBuyQuote();
        });

        // Sell quantity change
        document.getElementById('sell-quantity')?.addEventListener('input', () => {
            this.updateSellQuote();
        });

        // Confirm buy
        document.getElementById('confirm-buy')?.addEventListener('click', () => {
            this.executeBuy();
        });

        // Confirm sell
        document.getElementById('confirm-sell')?.addEventListener('click', () => {
            this.executeSell();
        });
    }

    async loadUserBalance() {
        try {
            const response = await fetch('/api/auth/status');
            const data = await response.json();

            if (data.authenticated && data.user) {
                this.userBalance = data.user.wallet_balance || 0;
                this.updateBalanceDisplay();
            } else if (data.guest_mode && data.guest_user) {
                // Guest mode
                this.userBalance = data.guest_user.wallet_balance || 0;
                this.updateBalanceDisplay();
            }
        } catch (error) {
            console.error('Error loading user balance:', error);
            // Fallback: show 0
            this.userBalance = 0;
            this.updateBalanceDisplay();
        }
    }

    async loadPortfolioSummary() {
        try {
            const response = await fetch('/api/stocks/portfolio/summary', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success && data.summary) {
                    this.portfolioValue = data.summary.total_value_gem || 0;
                    this.updatePortfolioDisplay(data.summary);
                }
            } else {
                // Not authenticated or no portfolio - show zeros
                this.updatePortfolioDisplay({
                    total_value_gem: 0,
                    profit_loss_gem: 0
                });
            }
        } catch (error) {
            console.error('Error loading portfolio summary:', error);
            // Show zeros on error
            this.updatePortfolioDisplay({
                total_value_gem: 0,
                profit_loss_gem: 0
            });
        }
    }

    async loadStocks() {
        try {
            document.getElementById('loading-state').style.display = 'block';
            document.getElementById('stock-grid').style.display = 'none';

            const response = await fetch('/api/stocks/?limit=100');
            const data = await response.json();

            if (data.success && data.stocks) {
                this.stocks = data.stocks;
                this.filteredStocks = [...this.stocks];
                this.sortAndRender();
            }

            document.getElementById('loading-state').style.display = 'none';
            document.getElementById('stock-grid').style.display = 'grid';
        } catch (error) {
            console.error('Error loading stocks:', error);
            this.showError('Failed to load stocks');
        }
    }

    filterStocks() {
        this.filteredStocks = this.stocks.filter(stock => {
            // Sector filter
            if (this.currentSector && stock.sector !== this.currentSector) {
                return false;
            }

            // Search filter
            if (this.searchQuery) {
                const query = this.searchQuery.toLowerCase();
                return stock.ticker.toLowerCase().includes(query) ||
                       stock.company_name.toLowerCase().includes(query);
            }

            return true;
        });

        this.sortAndRender();
    }

    sortAndRender() {
        // Sort stocks
        this.filteredStocks.sort((a, b) => {
            switch (this.currentSort) {
                case 'price':
                    return (b.current_price_usd || 0) - (a.current_price_usd || 0);
                case 'change':
                    return (b.price_change_pct || 0) - (a.price_change_pct || 0);
                case 'volume':
                    return (b.volume || 0) - (a.volume || 0);
                default: // ticker
                    return a.ticker.localeCompare(b.ticker);
            }
        });

        this.renderStocks();
    }

    renderStocks() {
        const grid = document.getElementById('stock-grid');
        const emptyState = document.getElementById('empty-state');

        if (this.filteredStocks.length === 0) {
            grid.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }

        emptyState.style.display = 'none';
        grid.style.display = 'grid';
        grid.innerHTML = '';

        this.filteredStocks.forEach(stock => {
            const card = this.createStockCard(stock);
            grid.appendChild(card);
        });
    }

    createStockCard(stock) {
        const card = document.createElement('div');
        card.className = 'stock-card';

        const priceChange = stock.price_change_pct || 0;
        const changeClass = priceChange >= 0 ? 'text-success' : 'text-danger';
        const changeIcon = priceChange >= 0 ? 'bi-arrow-up' : 'bi-arrow-down';

        card.innerHTML = `
            <div class="stock-card-header">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h5 class="stock-ticker mb-1">${stock.ticker}</h5>
                        <p class="stock-name text-muted mb-0">${stock.company_name}</p>
                        <small class="badge bg-secondary">${stock.sector}</small>
                    </div>
                </div>
            </div>
            <div class="stock-card-body">
                <div class="stock-price">
                    <div class="price-usd">$${this.formatNumber(stock.current_price_usd)}</div>
                    <div class="price-gem text-muted">${this.formatNumber(stock.current_price_gem)} GEM</div>
                </div>
                <div class="stock-change ${changeClass}">
                    <i class="bi ${changeIcon}"></i>
                    ${this.formatPercent(priceChange)}%
                </div>
            </div>
            <div class="stock-card-footer">
                <button class="btn btn-sm btn-success" onclick="stockMarket.openBuyModal('${stock.ticker}')">
                    <i class="bi bi-cart-plus"></i> Buy
                </button>
                <button class="btn btn-sm btn-outline-primary" onclick="window.location='/stocks/${stock.ticker}'">
                    <i class="bi bi-info-circle"></i> Details
                </button>
            </div>
        `;

        return card;
    }

    async openBuyModal(ticker) {
        try {
            // Get stock quote
            const stock = this.stocks.find(s => s.ticker === ticker);
            if (!stock) return;

            // Set modal data
            document.getElementById('buy-ticker').textContent = ticker;
            document.getElementById('buy-company-name').textContent = stock.company_name;
            document.getElementById('buy-price').textContent = `$${this.formatNumber(stock.current_price_usd)}`;
            document.getElementById('buy-price-gem').textContent = this.formatNumber(stock.current_price_gem);
            document.getElementById('buy-balance').textContent = `${this.formatNumber(this.userBalance)} GEM`;
            document.getElementById('buy-quantity').value = '10';

            // Store current stock data
            this.currentStock = stock;

            // Update quote
            this.updateBuyQuote();

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('buyModal'));
            modal.show();
        } catch (error) {
            console.error('Error opening buy modal:', error);
            this.showError('Failed to open buy modal');
        }
    }

    async updateBuyQuote() {
        if (!this.currentStock) return;

        const quantity = parseFloat(document.getElementById('buy-quantity').value) || 0;

        if (quantity <= 0) {
            document.getElementById('buy-subtotal').textContent = '0 GEM';
            document.getElementById('buy-fee').textContent = '0 GEM';
            document.getElementById('buy-total').textContent = '0 GEM';
            return;
        }

        try {
            const response = await fetch(`/api/stocks/${this.currentStock.ticker}/quote`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                },
                body: JSON.stringify({ quantity })
            });

            const data = await response.json();

            if (data.success && data.quote) {
                const quote = data.quote;
                document.getElementById('buy-subtotal').textContent = `${this.formatNumber(quote.subtotal_gem)} GEM`;
                document.getElementById('buy-fee').textContent = `${this.formatNumber(quote.fee_gem)} GEM`;
                document.getElementById('buy-total').textContent = `${this.formatNumber(quote.total_cost_gem)} GEM`;

                // Check sufficient funds
                const insufficientFunds = document.getElementById('insufficient-funds');
                const confirmBtn = document.getElementById('confirm-buy');

                if (!quote.sufficient_funds) {
                    insufficientFunds.style.display = 'block';
                    confirmBtn.disabled = true;
                } else {
                    insufficientFunds.style.display = 'none';
                    confirmBtn.disabled = false;
                }
            }
        } catch (error) {
            console.error('Error getting quote:', error);
        }
    }

    async executeBuy() {
        if (!this.currentStock) return;

        const quantity = parseFloat(document.getElementById('buy-quantity').value);
        const confirmBtn = document.getElementById('confirm-buy');

        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Buying...';

        try {
            const response = await fetch(`/api/stocks/${this.currentStock.ticker}/buy`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                },
                body: JSON.stringify({ quantity })
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess(`Successfully bought ${quantity} shares of ${this.currentStock.ticker}!`);

                // Close modal
                bootstrap.Modal.getInstance(document.getElementById('buyModal')).hide();

                // Reload balance and portfolio
                await this.loadUserBalance();
                await this.loadPortfolioSummary();
            } else {
                this.showError(data.detail || 'Failed to buy stock');
            }
        } catch (error) {
            console.error('Error buying stock:', error);
            this.showError('Failed to execute buy order');
        } finally {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = '<i class="bi bi-check-circle"></i> Buy Shares';
        }
    }

    updateBalanceDisplay() {
        const balanceEl = document.getElementById('available-gem');
        if (balanceEl) {
            balanceEl.textContent = `${this.formatNumber(this.userBalance)} GEM`;
        }
    }

    updatePortfolioDisplay(summary) {
        const valueEl = document.getElementById('portfolio-value');
        const plEl = document.getElementById('today-pl');

        if (valueEl) {
            valueEl.textContent = `${this.formatNumber(summary.total_value_gem)} GEM`;
        }

        if (plEl) {
            const pl = summary.profit_loss_gem || 0;
            const plClass = pl >= 0 ? 'text-success' : 'text-danger';
            const plSign = pl >= 0 ? '+' : '';
            plEl.className = `mb-0 ${plClass}`;
            plEl.textContent = `${plSign}${this.formatNumber(pl)} GEM`;
        }
    }

    toggleView() {
        const grid = document.getElementById('stock-grid');
        const btn = document.getElementById('view-toggle');

        if (this.currentView === 'grid') {
            this.currentView = 'list';
            grid.classList.remove('stock-grid');
            grid.classList.add('stock-list');
            btn.innerHTML = '<i class="bi bi-list"></i> List';
        } else {
            this.currentView = 'grid';
            grid.classList.remove('stock-list');
            grid.classList.add('stock-grid');
            btn.innerHTML = '<i class="bi bi-grid-3x3-gap"></i> Grid';
        }
    }

    startAutoRefresh() {
        // Refresh prices every 60 seconds
        setInterval(() => {
            this.loadStocks();
            this.loadPortfolioSummary();
        }, 60000);
    }

    formatNumber(num) {
        if (num === null || num === undefined) return '0';
        return parseFloat(num).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    formatPercent(num) {
        if (num === null || num === undefined) return '0.00';
        return parseFloat(num).toFixed(2);
    }

    showSuccess(message) {
        Toast.success(message);
    }

    showError(message) {
        Toast.error(message);
    }
}

// Initialize when DOM is ready
let stockMarket;
document.addEventListener('DOMContentLoaded', () => {
    stockMarket = new StockMarket();
});
