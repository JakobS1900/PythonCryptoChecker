/**
 * Dashboard Module for CryptoChecker v3
 * Handles dashboard-specific functionality, price tables, and quick conversions
 */

// Crypto Icon Management System
window.CryptoIconManager = {
    // Known CoinGecko image IDs for popular cryptocurrencies
    coinGeckoImageIds: {
        // Original cryptocurrencies
        'bitcoin': 1,
        'ethereum': 279,
        'binancecoin': 825,
        'cardano': 975,
        'solana': 4128,
        'ripple': 44,
        'polkadot': 12171,
        'dogecoin': 5,
        'avalanche-2': 12559,
        'chainlink': 1027,
        'matic-network': 4713,
        'uniswap': 12504,
        'litecoin': 2,
        'bitcoin-cash': 1831,
        'algorand': 4030,
        'vechain': 3077,
        'stellar': 512,
        'filecoin': 5718,
        'tron': 1094,
        'ethereum-classic': 453,
        'cosmos': 1481,
        'the-sandbox': 12882,
        'decentraland': 1966,
        'theta-token': 2416,
        'curve-dao-token': 12124,
        'yearn-finance': 11849,
        'sushi': 12271,
        'havven': 2586,
        'maker': 1518,
        'compound-governance-token': 7598,
        'internet-computer': 8916,
        'hedera-hashgraph': 4642,
        'flow': 4558,
        'shiba-inu': 11939,
        '1inch': 8104,
        'balancer': 11683,
        'republic-protocol': 2539,
        '0x': 1896,

        // NEW: Added cryptocurrencies with CoinGecko image IDs
        // Tier 1 - Highest Priority
        'monero': 69,
        'lido-dao': 13573,
        'arbitrum': 11841,
        'kaspa': 20396,
        'optimism': 11840,

        // Tier 2 - High Priority
        'sui': 26375,
        'immutable-x': 17233,
        'secret': 5604,
        'injective-protocol': 7226,
        'celestia': 22861,
        'sei-network': 28205,

        // Tier 3 - Medium Priority
        'starknet': 22691,
        'render-token': 5690,
        'aerodrome-finance': 31596,
        'wax': 2300,
        'fantom': 16352,
        'near': 6535,
        'mantle': 28893,
        'zcash': 486
    },

    // Get crypto icon URL with reliable CoinGecko fallback
    getCryptoIconUrl(crypto) {
        const id = (crypto.id || '').toLowerCase();
        const symbol = (crypto.symbol || '').toLowerCase();

        // 1. Use API provided image if available
        if (crypto.image) {
            return crypto.image;
        }

        // 2. Use known CoinGecko image ID
        const imageId = this.coinGeckoImageIds[id];
        if (imageId) {
            return `https://assets.coingecko.com/coins/images/${imageId}/thumb/${id}.png`;
        }

        // 3. Try cryptocurrency-icons CDN
        return `https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/${symbol}.svg`;
    },

    // Load crypto icon with fallback
    loadCryptoIcon(imgElement, crypto) {
        const iconUrl = this.getCryptoIconUrl(crypto);

        // Set up fallback chain
        imgElement.onerror = () => {
            if (!imgElement.hasAttribute('data-fallback-tried')) {
                imgElement.setAttribute('data-fallback-tried', 'true');
                // Try cryptocurrency-icons as fallback
                const symbol = (crypto.symbol || '').toLowerCase();
                imgElement.src = `https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/${symbol}.svg`;
            } else {
                // Final fallback to placeholder
                imgElement.src = '/static/img/placeholder-crypto.png';
            }
        };

        imgElement.onload = () => {
            imgElement.style.opacity = '1';
        };

        // Start loading
        imgElement.style.opacity = '0.5';
        imgElement.src = iconUrl;
    }
};

window.Dashboard = {
    // State management
    cryptoData: [],
    trendingData: [],
    isLoading: false,

    // Initialize dashboard
    init() {
        this.setupEventListeners();
        this.loadDashboardData();
        console.log('Dashboard module initialized');
    },

    // Set up event listeners
    setupEventListeners() {
        // Price search functionality
        const searchInput = document.getElementById('price-search');
        if (searchInput) {
            searchInput.addEventListener('input', App.utils.debounce((e) => {
                this.filterPriceTable(e.target.value);
            }, 300));
        }

        // Quick converter form
        const convertForm = document.getElementById('quick-convert-form');
        if (convertForm) {
            convertForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleQuickConvert();
            });
        }

        // Auto-refresh when price data is updated
        document.addEventListener('pricesUpdated', (e) => {
            this.cryptoData = e.detail;
            this.updatePriceTable();
        });

        // Tab switch events
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                this.handleTabSwitch(e.target.getAttribute('data-bs-target'));
            });
        });
    },

    // Load initial dashboard data
    async loadDashboardData() {
        // Add delay to prevent race conditions during page initialization
        await new Promise(resolve => setTimeout(resolve, 500));

        // Load data sequentially to reduce server load
        await this.loadPrices();
        await new Promise(resolve => setTimeout(resolve, 100));
        await this.loadTrending();
        await this.loadUserStats();
    },

    // Load cryptocurrency prices
    async loadPrices() {
        try {
            const response = await App.api.get('/crypto/prices', { limit: 50 });
            if (response.success) {
                this.cryptoData = response.data;
                this.updatePriceTable();
            }
        } catch (error) {
            console.error('Failed to load prices:', error);
            this.showPriceTableError('Failed to load price data');
        }
    },

    // Load trending cryptocurrencies
    async loadTrending() {
        try {
            const response = await App.api.get('/crypto/trending', { limit: 12 });
            if (response.success) {
                this.trendingData = response.data;
                this.updateTrendingCards();
            }
        } catch (error) {
            console.error('Failed to load trending:', error);
            this.showTrendingError('Failed to load trending data');
        }
    },

    // Load user statistics
    async loadUserStats() {
        try {
            // Update game count and conversion count
            this.updateElement('games-count', '0');
            this.updateElement('conversions-count', '0');
        } catch (error) {
            console.error('Failed to load user stats:', error);
        }
    },

    // Update price table
    updatePriceTable() {
        const tableBody = document.getElementById('prices-table-body');
        if (!tableBody) return;

        if (!this.cryptoData || this.cryptoData.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4 text-muted">
                        No cryptocurrency data available
                    </td>
                </tr>
            `;
            return;
        }

        const rows = this.cryptoData.map(crypto => this.createPriceRow(crypto)).join('');
        tableBody.innerHTML = rows;

        // Load crypto icons after DOM is updated
        this.cryptoData.forEach(crypto => {
            const imgElement = document.getElementById(`crypto-icon-${crypto.symbol}`);
            if (imgElement) {
                CryptoIconManager.loadCryptoIcon(imgElement, crypto);
            }
        });
    },

    // Create price table row
    createPriceRow(crypto) {
        const priceFormatted = App.formatPrice(crypto.current_price_usd);
        const changeFormatted = App.formatChange(crypto.price_change_percentage_24h);
        const marketCapFormatted = App.formatNumber(crypto.market_cap);

        return `
            <tr data-crypto-id="${crypto.id}" data-symbol="${crypto.symbol.toLowerCase()}">
                <td>
                    <div class="d-flex align-items-center">
                        <img id="crypto-icon-${crypto.symbol}"
                             alt="${crypto.name}" class="me-2 crypto-icon"
                             style="width: 24px; height: 24px; opacity: 0.5; transition: opacity 0.3s ease;"
                             src="/static/img/placeholder-crypto.png">
                        <div>
                            <div class="fw-semibold">${crypto.name}</div>
                            <small class="text-muted">${crypto.symbol.toUpperCase()}</small>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="badge bg-secondary">${crypto.symbol.toUpperCase()}</span>
                </td>
                <td class="text-end fw-semibold">
                    ${priceFormatted}
                </td>
                <td class="text-end">
                    ${changeFormatted}
                </td>
                <td class="text-end">
                    ${marketCapFormatted}
                </td>
                <td class="text-end">
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary"
                                onclick="Dashboard.quickConvertTo('${crypto.symbol}')"
                                title="Quick Convert to ${crypto.symbol}">
                            <i class="bi bi-arrow-left-right"></i>
                        </button>
                        <button class="btn btn-outline-info"
                                onclick="Dashboard.showCryptoDetails('${crypto.id}')"
                                title="View details">
                            <i class="bi bi-info-circle"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    },

    // Filter price table
    filterPriceTable(searchTerm) {
        const rows = document.querySelectorAll('#prices-table-body tr[data-crypto-id]');
        const lowerSearchTerm = searchTerm.toLowerCase();

        rows.forEach(row => {
            const cryptoId = row.dataset.cryptoId;
            const symbol = row.dataset.symbol;
            const nameElement = row.querySelector('.fw-semibold');
            const name = nameElement ? nameElement.textContent.toLowerCase() : '';

            const matches = !searchTerm ||
                           name.includes(lowerSearchTerm) ||
                           symbol.includes(lowerSearchTerm) ||
                           cryptoId.includes(lowerSearchTerm);

            row.style.display = matches ? '' : 'none';
        });
    },

    // Update trending cards
    updateTrendingCards() {
        const container = document.getElementById('trending-cards');
        if (!container) return;

        if (!this.trendingData || this.trendingData.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center py-4 text-muted">
                    No trending data available
                </div>
            `;
            return;
        }

        const cards = this.trendingData.map(crypto => this.createTrendingCard(crypto)).join('');
        container.innerHTML = cards;

        // Load crypto icons after DOM is updated
        this.trendingData.forEach(crypto => {
            const imgElement = document.getElementById(`trending-icon-${crypto.symbol}`);
            if (imgElement) {
                CryptoIconManager.loadCryptoIcon(imgElement, crypto);
            }
        });
    },

    // Create trending card
    createTrendingCard(crypto) {
        const priceFormatted = App.formatPrice(crypto.current_price_usd);
        const changeFormatted = App.formatChange(crypto.price_change_percentage_24h);
        const changeClass = crypto.price_change_percentage_24h >= 0 ? 'success' : 'danger';

        return `
            <div class="col-md-4 col-lg-3 mb-3">
                <div class="card h-100 trending-card">
                    <div class="card-body text-center">
                        <img id="trending-icon-${crypto.symbol}"
                             alt="${crypto.name}" class="mb-2 crypto-icon"
                             style="width: 32px; height: 32px; opacity: 0.5; transition: opacity 0.3s ease;"
                             src="/static/img/placeholder-crypto.png">
                        <h6 class="card-title mb-1">${crypto.name}</h6>
                        <span class="badge bg-secondary mb-2">${crypto.symbol.toUpperCase()}</span>
                        <div class="fw-bold text-primary">${priceFormatted}</div>
                        <div class="small text-${changeClass}">${changeFormatted}</div>
                    </div>
                    <div class="card-footer bg-transparent border-0 pt-0">
                        <button class="btn btn-outline-primary btn-sm w-100"
                                onclick="Dashboard.quickConvertTo('${crypto.symbol}')">
                            <i class="bi bi-arrow-left-right"></i> Convert
                        </button>
                    </div>
                </div>
            </div>
        `;
    },

    // Handle quick convert form
    async handleQuickConvert() {
        const amount = parseFloat(document.getElementById('convert-amount').value);
        const fromCurrency = document.getElementById('convert-from').value;
        const toCurrency = document.getElementById('convert-to').value;

        if (!amount || amount <= 0) {
            App.showAlert('warning', 'Please enter a valid amount');
            return;
        }

        if (fromCurrency === toCurrency) {
            App.showAlert('warning', 'Please select different currencies');
            return;
        }

        try {
            this.showConvertLoading(true);

            const response = await App.api.post('/crypto/convert', {
                from_currency: fromCurrency,
                to_currency: toCurrency,
                amount: amount
            });

            if (response.from_amount && response.to_amount) {
                this.showConversionResult(response);
                this.incrementConversionsCount();
            }

        } catch (error) {
            App.showAlert('danger', error.message || 'Conversion failed');
        } finally {
            this.showConvertLoading(false);
        }
    },

    // Show conversion result
    showConversionResult(result) {
        const resultInput = document.getElementById('convert-result');
        const resultContainer = document.getElementById('conversion-result');
        const resultDetails = document.getElementById('conversion-details');

        if (resultInput) {
            resultInput.value = result.to_amount.toFixed(6);
        }

        if (resultContainer && resultDetails) {
            resultDetails.innerHTML = `
                <strong>${result.from_amount} ${result.from_currency}</strong> =
                <strong>${result.to_amount.toFixed(6)} ${result.to_currency}</strong>
                <br>
                <small class="text-muted">
                    Rate: 1 ${result.from_currency} = ${result.rate.toFixed(6)} ${result.to_currency}
                    <br>Type: ${result.conversion_type} • ${result.timestamp}
                </small>
            `;
            resultContainer.style.display = 'block';
        }
    },

    // Handle tab switch
    handleTabSwitch(target) {
        switch (target) {
            case '#trending':
                if (this.trendingData.length === 0) {
                    this.loadTrending();
                }
                break;
            case '#converter':
                // Initialize converter if needed
                break;
        }
    },

    // Utility functions
    quickConvertTo(symbol) {
        // Redirect to converter page with pre-filled target currency
        const converterUrl = `/converter?to=${encodeURIComponent(symbol)}&from=USD&amount=1`;
        window.location.href = converterUrl;
    },

    convertToCrypto(symbol) {
        // Legacy function - redirect to new quickConvertTo
        this.quickConvertTo(symbol);
    },

    showCryptoDetails(cryptoId) {
        const crypto = this.cryptoData.find(c => c.id === cryptoId);
        if (!crypto) return;

        const modalContent = `
            <div class="text-center mb-3">
                <img id="modal-icon-${crypto.symbol}"
                     alt="${crypto.name}" class="crypto-icon"
                     style="width: 64px; height: 64px; opacity: 0.5; transition: opacity 0.3s ease;"
                     src="/static/img/placeholder-crypto.png">
                <h4 class="mt-2">${crypto.name} (${crypto.symbol.toUpperCase()})</h4>
            </div>
            <div class="row">
                <div class="col-6">
                    <strong>Current Price:</strong><br>
                    <span class="text-primary fs-5">${App.formatPrice(crypto.current_price_usd)}</span>
                </div>
                <div class="col-6">
                    <strong>24h Change:</strong><br>
                    ${App.formatChange(crypto.price_change_percentage_24h)}
                </div>
            </div>
            <hr>
            <div class="row">
                <div class="col-6">
                    <strong>Market Cap:</strong><br>
                    ${App.formatNumber(crypto.market_cap)}
                </div>
                <div class="col-6">
                    <strong>Rank:</strong><br>
                    #${crypto.market_cap_rank || 'N/A'}
                </div>
            </div>
            <div class="mt-3 text-center">
                <button class="btn btn-primary" onclick="Dashboard.quickConvertTo('${crypto.symbol}')">
                    <i class="bi bi-arrow-left-right"></i> Convert to ${crypto.symbol.toUpperCase()}
                </button>
            </div>
        `;

        App.showModal(`${crypto.name} Details`, modalContent, 'modal-dialog-centered');

        // Load icon after modal is shown
        setTimeout(() => {
            const imgElement = document.getElementById(`modal-icon-${crypto.symbol}`);
            if (imgElement) {
                CryptoIconManager.loadCryptoIcon(imgElement, crypto);
            }
        }, 100);
    },

    swapCurrencies() {
        const fromSelect = document.getElementById('convert-from');
        const toSelect = document.getElementById('convert-to');

        if (fromSelect && toSelect) {
            const fromValue = fromSelect.value;
            fromSelect.value = toSelect.value;
            toSelect.value = fromValue;
        }
    },

    refreshPrices() {
        App.showAlert('info', 'Refreshing prices...', 2000);
        this.loadPrices();
    },

    incrementConversionsCount() {
        const countElement = document.getElementById('conversions-count');
        if (countElement) {
            const currentCount = parseInt(countElement.textContent) || 0;
            countElement.textContent = currentCount + 1;
        }
    },

    showConvertLoading(isLoading) {
        const submitBtn = document.querySelector('#quick-convert-form button[type="submit"]');
        if (submitBtn) {
            if (isLoading) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Converting...';
            } else {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="bi bi-arrow-left-right"></i> Convert';
            }
        }
    },

    showPriceTableError(message) {
        const tableBody = document.getElementById('prices-table-body');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4 text-danger">
                        <i class="bi bi-exclamation-triangle"></i> ${message}
                        <br>
                        <button class="btn btn-outline-primary btn-sm mt-2" onclick="Dashboard.refreshPrices()">
                            <i class="bi bi-arrow-clockwise"></i> Try Again
                        </button>
                    </td>
                </tr>
            `;
        }
    },

    showTrendingError(message) {
        const container = document.getElementById('trending-cards');
        if (container) {
            container.innerHTML = `
                <div class="col-12 text-center py-4 text-danger">
                    <i class="bi bi-exclamation-triangle"></i> ${message}
                    <br>
                    <button class="btn btn-outline-primary btn-sm mt-2" onclick="Dashboard.loadTrending()">
                        <i class="bi bi-arrow-clockwise"></i> Try Again
                    </button>
                </div>
            `;
        }
    },

    showGuestInfo() {
        App.showGuestInfo();
    },

    updateElement(id, content) {
        App.updateElement(id, content);
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Dashboard will be initialized by the page_init block in base template
});