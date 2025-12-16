/**
 * Crypto Market JavaScript
 * Handles cryptocurrency trading with GEM currency
 */

const CryptoMarket = {
    // State
    cryptos: [],
    holdings: [],
    selectedCrypto: null,
    buyModal: null,
    sellModal: null,

    // Initialize
    async init() {
        console.log('CryptoMarket: Initializing...');

        // Initialize modals
        this.buyModal = new bootstrap.Modal(document.getElementById('buyModal'));
        this.sellModal = new bootstrap.Modal(document.getElementById('sellModal'));

        // Setup search
        const searchInput = document.getElementById('crypto-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => this.filterCryptos(), 300));
        }

        // Load data
        await Promise.all([
            this.loadBalance(),
            this.loadCryptos(),
            this.loadHoldings(),
            this.loadTransactions()
        ]);

        // Auto-refresh every 60 seconds
        setInterval(() => this.refreshPrices(), 60000);
    },

    // Debounce helper
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Get auth headers
    getAuthHeaders() {
        const token = localStorage.getItem('auth_token');
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    },

    // Format number
    formatNumber(num, decimals = 2) {
        if (num === null || num === undefined) return '—';
        return new Intl.NumberFormat('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        }).format(num);
    },

    // Format GEM
    formatGem(amount) {
        if (amount === null || amount === undefined) return '—';
        return `${this.formatNumber(amount)} GEM`;
    },

    // Load user balance
    async loadBalance() {
        try {
            const response = await fetch('/api/crypto/portfolio/balance', {
                headers: this.getAuthHeaders()
            });
            const data = await response.json();

            if (data.success) {
                document.getElementById('available-gem').textContent = this.formatGem(data.balance);
            }
        } catch (error) {
            console.error('Error loading balance:', error);
            document.getElementById('available-gem').textContent = '—';
        }
    },

    // Load all cryptocurrencies
    async loadCryptos() {
        try {
            const response = await fetch('/api/crypto/prices?limit=50');
            const data = await response.json();

            if (data.success && data.data) {
                this.cryptos = data.data;
                this.renderCryptos();
            }
        } catch (error) {
            console.error('Error loading cryptos:', error);
            document.getElementById('crypto-list').innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="bi bi-exclamation-triangle text-warning" style="font-size: 2rem;"></i>
                    <p class="text-muted mt-2">Failed to load cryptocurrencies</p>
                    <button class="btn-modern btn-modern-outline btn-sm" onclick="CryptoMarket.loadCryptos()">Try Again</button>
                </div>
            `;
        }
    },

    // Render crypto list
    renderCryptos() {
        const container = document.getElementById('crypto-list');
        const searchQuery = document.getElementById('crypto-search')?.value?.toLowerCase() || '';

        let filtered = this.cryptos;
        if (searchQuery) {
            filtered = this.cryptos.filter(crypto =>
                crypto.name?.toLowerCase().includes(searchQuery) ||
                crypto.symbol?.toLowerCase().includes(searchQuery)
            );
        }

        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="bi bi-search text-muted" style="font-size: 2rem;"></i>
                    <p class="text-muted mt-2">No cryptocurrencies found</p>
                </div>
            `;
            return;
        }

        container.innerHTML = filtered.map(crypto => {
            const priceGem = (crypto.current_price_usd || 0) / 0.01;
            const changeClass = (crypto.price_change_percentage_24h || 0) >= 0 ? 'positive' : 'negative';
            const changeIcon = changeClass === 'positive' ? 'bi-arrow-up' : 'bi-arrow-down';

            return `
                <div class="col-md-6 col-lg-4">
                    <div class="crypto-card" onclick="CryptoMarket.openBuyModal('${crypto.id}')">
                        <div class="d-flex align-items-center mb-3">
                            <img src="${crypto.image || ''}" class="crypto-icon me-3" 
                                 alt="${crypto.symbol}" onerror="this.style.display='none'">
                            <div>
                                <h6 class="crypto-name">${crypto.name || crypto.id}</h6>
                                <span class="crypto-symbol">${(crypto.symbol || crypto.id).toUpperCase()}</span>
                            </div>
                        </div>
                        <div class="d-flex justify-content-between align-items-end">
                            <div>
                                <div class="crypto-price">${this.formatNumber(priceGem, 0)} GEM</div>
                                <small class="text-muted">$${this.formatNumber(crypto.current_price_usd)}</small>
                            </div>
                            <span class="crypto-change ${changeClass}">
                                <i class="bi ${changeIcon}"></i>
                                ${this.formatNumber(Math.abs(crypto.price_change_percentage_24h || 0))}%
                            </span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    },

    // Filter cryptos
    filterCryptos() {
        this.renderCryptos();
    },

    // Refresh prices
    async refreshPrices() {
        await Promise.all([
            this.loadCryptos(),
            this.loadHoldings(),
            this.loadBalance()
        ]);
        this.showToast('Prices refreshed', 'success');
    },

    // Load user holdings
    async loadHoldings() {
        try {
            const response = await fetch('/api/crypto/holdings/list', {
                headers: this.getAuthHeaders()
            });

            if (response.status === 401) {
                this.renderHoldingsNotLoggedIn();
                return;
            }

            const data = await response.json();

            if (data.success) {
                this.holdings = data.holdings || [];
                this.renderHoldings();
                this.updatePortfolioStats();
            }
        } catch (error) {
            console.error('Error loading holdings:', error);
            document.getElementById('holdings-container').innerHTML = `
                <div class="text-center py-4">
                    <p class="text-muted mb-0">Unable to load holdings</p>
                </div>
            `;
        }
    },

    // Render holdings when not logged in
    renderHoldingsNotLoggedIn() {
        document.getElementById('holdings-container').innerHTML = `
            <div class="text-center py-4">
                <i class="bi bi-lock text-muted" style="font-size: 2rem;"></i>
                <p class="text-muted mt-2 mb-0">Login to view your holdings</p>
            </div>
        `;
        document.getElementById('crypto-portfolio-value').textContent = '—';
        document.getElementById('crypto-total-pl').textContent = '—';
    },

    // Render holdings
    renderHoldings() {
        const container = document.getElementById('holdings-container');

        if (this.holdings.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4">
                    <i class="bi bi-wallet2 text-muted" style="font-size: 2rem;"></i>
                    <p class="text-muted mt-2 mb-0">No crypto holdings yet</p>
                    <small class="text-muted">Buy some crypto to get started!</small>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="list-group list-group-flush">
                ${this.holdings.map(h => {
            const plClass = (h.profit_loss_gem || 0) >= 0 ? 'text-success' : 'text-danger';
            const plSign = (h.profit_loss_gem || 0) >= 0 ? '+' : '';

            return `
                        <div class="list-group-item bg-transparent border-0 px-0 py-3" 
                             style="border-bottom: 1px solid var(--border-subtle) !important;">
                            <div class="d-flex align-items-center">
                                <img src="${h.image || ''}" class="me-2" style="width: 32px; height: 32px; border-radius: 50%;" 
                                     onerror="this.style.display='none'">
                                <div class="flex-grow-1">
                                    <div class="d-flex justify-content-between">
                                        <strong>${h.symbol}</strong>
                                        <span>${this.formatNumber(h.current_value_gem, 0)} GEM</span>
                                    </div>
                                    <div class="d-flex justify-content-between">
                                        <small class="text-muted">${this.formatNumber(h.quantity, 6)}</small>
                                        <small class="${plClass}">${plSign}${this.formatNumber(h.profit_loss_gem, 0)} GEM</small>
                                    </div>
                                </div>
                                <button class="btn btn-sm ms-2" style="background: var(--error); color: white; border-radius: var(--radius-md);"
                                        onclick="CryptoMarket.openSellModal('${h.crypto_id}')">
                                    Sell
                                </button>
                            </div>
                        </div>
                    `;
        }).join('')}
            </div>
        `;
    },

    // Update portfolio stats
    updatePortfolioStats() {
        let totalValue = 0;
        let totalPL = 0;

        this.holdings.forEach(h => {
            totalValue += h.current_value_gem || 0;
            totalPL += h.profit_loss_gem || 0;
        });

        document.getElementById('crypto-portfolio-value').textContent = this.formatGem(totalValue);

        const plEl = document.getElementById('crypto-total-pl');
        const plSign = totalPL >= 0 ? '+' : '';
        plEl.textContent = `${plSign}${this.formatGem(totalPL)}`;
        plEl.className = totalPL >= 0 ? 'text-success' : 'text-danger';
    },

    // Load transactions
    async loadTransactions() {
        try {
            const response = await fetch('/api/crypto/holdings/transactions?limit=5', {
                headers: this.getAuthHeaders()
            });

            if (response.status === 401) {
                return;
            }

            const data = await response.json();

            if (data.success) {
                this.renderTransactions(data.transactions || []);
            }
        } catch (error) {
            console.error('Error loading transactions:', error);
        }
    },

    // Render transactions
    renderTransactions(transactions) {
        const container = document.getElementById('transactions-container');

        if (transactions.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4">
                    <p class="text-muted mb-0">No recent trades</p>
                </div>
            `;
            return;
        }

        container.innerHTML = transactions.map(tx => {
            const isBuy = tx.transaction_type === 'BUY';
            const typeClass = isBuy ? 'text-success' : 'text-danger';
            const typeIcon = isBuy ? 'bi-arrow-down-circle' : 'bi-arrow-up-circle';
            const date = new Date(tx.created_at).toLocaleDateString();

            return `
                <div class="d-flex align-items-center py-2" style="border-bottom: 1px solid var(--border-subtle);">
                    <i class="bi ${typeIcon} ${typeClass} me-2"></i>
                    <div class="flex-grow-1">
                        <div class="d-flex justify-content-between">
                            <span>${tx.symbol}</span>
                            <span>${this.formatNumber(tx.quantity, 4)}</span>
                        </div>
                        <small class="text-muted">${date}</small>
                    </div>
                </div>
            `;
        }).join('');
    },

    // Open buy modal
    openBuyModal(cryptoId) {
        const crypto = this.cryptos.find(c => c.id === cryptoId);
        if (!crypto) return;

        this.selectedCrypto = crypto;

        // Update modal content
        document.getElementById('buy-crypto-name').textContent = crypto.name;
        document.getElementById('buy-crypto-symbol').textContent = (crypto.symbol || crypto.id).toUpperCase();
        document.getElementById('buy-crypto-price').textContent = `$${this.formatNumber(crypto.current_price_usd)}`;
        document.getElementById('buy-crypto-icon').src = crypto.image || '';
        document.getElementById('buy-quantity').value = '';
        document.getElementById('buy-quote-container').style.display = 'none';

        this.buyModal.show();
    },

    // Update buy quote
    async updateBuyQuote() {
        const quantity = parseFloat(document.getElementById('buy-quantity').value);
        if (!quantity || quantity <= 0 || !this.selectedCrypto) {
            document.getElementById('buy-quote-container').style.display = 'none';
            return;
        }

        try {
            const response = await fetch(
                `/api/crypto/${this.selectedCrypto.id}/buy-quote?quantity=${quantity}`,
                { headers: this.getAuthHeaders() }
            );

            if (!response.ok) {
                throw new Error('Failed to get quote');
            }

            const data = await response.json();

            if (data.success && data.quote) {
                const quote = data.quote;
                document.getElementById('buy-price-per-unit').textContent = this.formatGem(quote.price_per_unit_gem);
                document.getElementById('buy-subtotal').textContent = this.formatGem(quote.subtotal_gem);
                document.getElementById('buy-fee').textContent = this.formatGem(quote.fee_gem);
                document.getElementById('buy-total').textContent = this.formatGem(quote.total_cost_gem);
                document.getElementById('buy-balance').textContent = this.formatNumber(quote.user_balance_gem);
                document.getElementById('buy-quote-container').style.display = 'block';

                // Check if sufficient funds
                const insufficient = !quote.sufficient_funds;
                document.getElementById('buy-insufficient-funds').style.display = insufficient ? 'block' : 'none';
                document.getElementById('confirm-buy-btn').disabled = insufficient;
            }
        } catch (error) {
            console.error('Error getting buy quote:', error);
        }
    },

    // Confirm buy
    async confirmBuy() {
        const quantity = parseFloat(document.getElementById('buy-quantity').value);
        if (!quantity || quantity <= 0 || !this.selectedCrypto) return;

        const btn = document.getElementById('confirm-buy-btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';

        try {
            const response = await fetch(`/api/crypto/${this.selectedCrypto.id}/buy`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...this.getAuthHeaders()
                },
                body: JSON.stringify({ quantity })
            });

            const data = await response.json();

            if (data.success) {
                this.buyModal.hide();
                this.showToast(`Successfully bought ${quantity} ${data.symbol}!`, 'success');

                // Refresh data
                await Promise.all([
                    this.loadBalance(),
                    this.loadHoldings(),
                    this.loadTransactions()
                ]);
            } else {
                this.showToast(data.detail || 'Failed to buy crypto', 'error');
            }
        } catch (error) {
            console.error('Error buying crypto:', error);
            this.showToast('Failed to complete purchase', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-circle"></i> Confirm Purchase';
        }
    },

    // Open sell modal
    openSellModal(cryptoId) {
        const holding = this.holdings.find(h => h.crypto_id === cryptoId);
        if (!holding) return;

        this.selectedCrypto = { id: cryptoId, ...holding };

        // Update modal content
        document.getElementById('sell-crypto-name').textContent = holding.name;
        document.getElementById('sell-crypto-symbol').textContent = holding.symbol;
        document.getElementById('sell-crypto-price').textContent = `$${this.formatNumber(holding.current_price_usd)}`;
        document.getElementById('sell-crypto-icon').src = holding.image || '';
        document.getElementById('sell-max-quantity').textContent = this.formatNumber(holding.quantity, 6);
        document.getElementById('sell-owned-symbol').textContent = holding.symbol;
        document.getElementById('sell-quantity').value = '';
        document.getElementById('sell-quote-container').style.display = 'none';

        this.sellModal.show();
    },

    // Sell max
    sellMax() {
        const holding = this.holdings.find(h => h.crypto_id === this.selectedCrypto?.id);
        if (holding) {
            document.getElementById('sell-quantity').value = holding.quantity;
            this.updateSellQuote();
        }
    },

    // Update sell quote
    async updateSellQuote() {
        const quantity = parseFloat(document.getElementById('sell-quantity').value);
        if (!quantity || quantity <= 0 || !this.selectedCrypto) {
            document.getElementById('sell-quote-container').style.display = 'none';
            return;
        }

        try {
            const response = await fetch(
                `/api/crypto/${this.selectedCrypto.id}/sell-quote?quantity=${quantity}`,
                { headers: this.getAuthHeaders() }
            );

            if (!response.ok) {
                throw new Error('Failed to get quote');
            }

            const data = await response.json();

            if (data.success && data.quote) {
                const quote = data.quote;
                document.getElementById('sell-price-per-unit').textContent = this.formatGem(quote.price_per_unit_gem);
                document.getElementById('sell-subtotal').textContent = this.formatGem(quote.subtotal_gem);
                document.getElementById('sell-fee').textContent = this.formatGem(quote.fee_gem);
                document.getElementById('sell-net').textContent = this.formatGem(quote.net_proceeds_gem);

                const plEl = document.getElementById('sell-pl');
                const pl = quote.expected_profit_loss_gem;
                const plSign = pl >= 0 ? '+' : '';
                plEl.textContent = `${plSign}${this.formatGem(pl)}`;
                plEl.className = pl >= 0 ? 'text-success' : 'text-danger';

                document.getElementById('sell-quote-container').style.display = 'block';
            }
        } catch (error) {
            console.error('Error getting sell quote:', error);
        }
    },

    // Confirm sell
    async confirmSell() {
        const quantity = parseFloat(document.getElementById('sell-quantity').value);
        if (!quantity || quantity <= 0 || !this.selectedCrypto) return;

        const btn = document.getElementById('confirm-sell-btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';

        try {
            const response = await fetch(`/api/crypto/${this.selectedCrypto.id}/sell`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...this.getAuthHeaders()
                },
                body: JSON.stringify({ quantity })
            });

            const data = await response.json();

            if (data.success) {
                this.sellModal.hide();
                const plText = data.profit_loss_gem >= 0
                    ? `+${this.formatNumber(data.profit_loss_gem)} GEM profit`
                    : `${this.formatNumber(data.profit_loss_gem)} GEM loss`;
                this.showToast(`Sold ${quantity} ${data.symbol} (${plText})`, 'success');

                // Refresh data
                await Promise.all([
                    this.loadBalance(),
                    this.loadHoldings(),
                    this.loadTransactions()
                ]);
            } else {
                this.showToast(data.detail || 'Failed to sell crypto', 'error');
            }
        } catch (error) {
            console.error('Error selling crypto:', error);
            this.showToast('Failed to complete sale', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-circle"></i> Confirm Sale';
        }
    },

    // Show toast notification
    showToast(message, type = 'info') {
        // Use existing toast system if available
        if (typeof showToast === 'function') {
            showToast(message, type);
        } else {
            console.log(`[${type}] ${message}`);
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    CryptoMarket.init();
});
