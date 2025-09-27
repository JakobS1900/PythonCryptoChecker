/**
 * CryptoChecker Universal Currency Converter - JavaScript Module
 * Handles cryptocurrency and fiat currency conversions with real-time rates
 */

window.Converter = {
    // Converter state
    exchangeRates: {},
    cryptoPrices: {},
    lastUpdate: null,
    conversionHistory: [],
    supportedCryptos: {},
    supportedFiat: {},

    // DOM elements
    elements: {
        form: null,
        amount: null,
        fromCurrency: null,
        toCurrency: null,
        result: null,
        swapBtn: null,
        conversionDetails: null,
        conversionRate: null,
        conversionType: null,
        lastUpdated: null,
        popularConversions: null,
        conversionHistory: null,
        supportedCrypto: null,
        supportedFiat: null
    },

    // Initialize the converter
    async init() {
        try {
            console.log('Initializing Universal Currency Converter...');
            this.initElements();
            this.initEventListeners();
            await this.loadSupportedCurrencies();
            await this.loadExchangeRates();
            await this.loadCryptoPrices();
            this.populateCurrencySelects();
            this.loadPopularConversions();
            this.loadConversionHistory();
            this.updateSupportedCurrencyLists();
            this.handleUrlParameters();
            console.log('Universal Currency Converter initialized successfully');
        } catch (error) {
            console.error('Failed to initialize Converter:', error);
            CryptoChecker.showAlert('danger', 'Failed to initialize converter. Please refresh the page.');
        }
    },

    // Initialize DOM elements
    initElements() {
        this.elements = {
            form: document.getElementById('converter-form'),
            amount: document.getElementById('amount'),
            fromCurrency: document.getElementById('from-currency'),
            toCurrency: document.getElementById('to-currency'),
            result: document.getElementById('result'),
            swapBtn: document.getElementById('swap-currencies'),
            conversionDetails: document.getElementById('conversion-details'),
            conversionRate: document.getElementById('conversion-rate'),
            conversionType: document.getElementById('conversion-type'),
            lastUpdated: document.getElementById('last-updated'),
            popularConversions: document.getElementById('popular-conversions'),
            conversionHistory: document.getElementById('conversion-history'),
            supportedCrypto: document.getElementById('supported-crypto'),
            supportedFiat: document.getElementById('supported-fiat')
        };

        // Validate required elements
        const requiredElements = ['form', 'amount', 'fromCurrency', 'toCurrency', 'result'];
        for (const elementName of requiredElements) {
            if (!this.elements[elementName]) {
                throw new Error(`Required element ${elementName} not found`);
            }
        }
    },

    // Set up event listeners
    initEventListeners() {
        // Form submission
        this.elements.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.performConversion();
        });

        // Real-time conversion on input change
        this.elements.amount.addEventListener('input', CryptoChecker.utils.debounce(() => {
            if (this.elements.amount.value > 0) {
                this.performConversion();
            }
        }, 500));

        // Currency selection changes
        this.elements.fromCurrency.addEventListener('change', () => {
            if (this.elements.amount.value > 0) {
                this.performConversion();
            }
        });

        this.elements.toCurrency.addEventListener('change', () => {
            if (this.elements.amount.value > 0) {
                this.performConversion();
            }
        });

        // Swap button
        if (this.elements.swapBtn) {
            this.elements.swapBtn.addEventListener('click', () => this.swapCurrencies());
        }

        // Popular conversion quick actions
        document.addEventListener('click', (e) => {
            if (e.target.matches('.popular-conversion') || e.target.closest('.popular-conversion')) {
                const conversionBtn = e.target.matches('.popular-conversion') ? e.target : e.target.closest('.popular-conversion');
                this.selectPopularConversion(conversionBtn);
            }
        });

        // Refresh rates (if button exists)
        const refreshBtn = document.querySelector('#refresh-rates');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshRates());
        }
    },

    // Load supported currencies from API
    async loadSupportedCurrencies() {
        try {
            console.log('Loading supported currencies...');

            // Load supported cryptocurrencies
            const cryptoResponse = await CryptoChecker.api.get('/crypto/currencies/crypto');
            if (cryptoResponse.success) {
                this.supportedCryptos = cryptoResponse.currencies;
            } else {
                // Fallback: Load from prices endpoint
                const pricesResponse = await CryptoChecker.api.get('/crypto/prices?limit=100');
                if (pricesResponse.success) {
                    this.supportedCryptos = {};
                    pricesResponse.data.forEach(crypto => {
                        this.supportedCryptos[crypto.symbol.toUpperCase()] = crypto.name;
                    });
                }
            }

            // Load supported fiat currencies from API
            const fiatResponse = await CryptoChecker.api.get('/crypto/currencies/fiat');
            if (fiatResponse.success) {
                this.supportedFiat = fiatResponse.currencies;
            } else {
                // Fallback to hardcoded list
                this.supportedFiat = {
                    'USD': 'US Dollar',
                    'EUR': 'Euro',
                    'GBP': 'British Pound',
                    'JPY': 'Japanese Yen',
                    'CNY': 'Chinese Yuan',
                    'KRW': 'South Korean Won',
                    'AUD': 'Australian Dollar',
                    'CAD': 'Canadian Dollar',
                    'CHF': 'Swiss Franc',
                    'SEK': 'Swedish Krona',
                    'NOK': 'Norwegian Krone',
                    'DKK': 'Danish Krone',
                    'PLN': 'Polish Zloty',
                    'CZK': 'Czech Koruna',
                    'HUF': 'Hungarian Forint',
                    'RUB': 'Russian Ruble',
                    'BRL': 'Brazilian Real',
                    'INR': 'Indian Rupee',
                    'SGD': 'Singapore Dollar',
                    'HKD': 'Hong Kong Dollar',
                    'MXN': 'Mexican Peso',
                    'TRY': 'Turkish Lira',
                    'ZAR': 'South African Rand',
                    'AED': 'UAE Dirham',
                    'SAR': 'Saudi Riyal'
                };
            }

            // Add GEM virtual currency to crypto list
            this.supportedCryptos['GEM'] = 'Gaming Tokens';

            console.log(`Loaded ${Object.keys(this.supportedCryptos).length} cryptocurrencies and ${Object.keys(this.supportedFiat).length} fiat currencies`);
        } catch (error) {
            console.error('Failed to load supported currencies:', error);
        }
    },

    // Load exchange rates from external API
    async loadExchangeRates() {
        try {
            console.log('Loading exchange rates...');

            // For now, use basic rates - in production this would come from a financial API
            this.exchangeRates = {
                'USD': 1.0,
                'EUR': 0.85,
                'GBP': 0.73,
                'JPY': 110.0,
                'CNY': 6.45,
                'KRW': 1180.0,
                'AUD': 1.35,
                'CAD': 1.25,
                'CHF': 0.92,
                'SEK': 8.50,
                'NOK': 8.75,
                'DKK': 6.35,
                'PLN': 3.90,
                'CZK': 21.5,
                'HUF': 295.0,
                'RUB': 74.0,
                'BRL': 5.20,
                'INR': 74.5,
                'SGD': 1.35,
                'HKD': 7.80,
                'MXN': 20.1,
                'TRY': 8.50,
                'ZAR': 14.2,
                'AED': 3.67,
                'SAR': 3.75
            };

            console.log('Exchange rates loaded');
        } catch (error) {
            console.error('Failed to load exchange rates:', error);
        }
    },

    // Load cryptocurrency prices
    async loadCryptoPrices() {
        try {
            console.log('Loading crypto prices...');

            const response = await CryptoChecker.api.get('/crypto/prices?limit=100');
            if (response.success) {
                this.cryptoPrices = {};
                response.data.forEach(crypto => {
                    this.cryptoPrices[crypto.symbol.toLowerCase()] = {
                        price: crypto.current_price_usd,
                        name: crypto.name,
                        symbol: crypto.symbol.toUpperCase()
                    };
                });

                // Add GEM virtual currency (1,000 GEM = $10 USD equivalent)
                this.cryptoPrices['gem'] = {
                    price: 0.01,
                    name: 'Gaming Tokens',
                    symbol: 'GEM'
                };

                this.lastUpdate = new Date();
                console.log(`Loaded prices for ${Object.keys(this.cryptoPrices).length} cryptocurrencies`);
            }
        } catch (error) {
            console.error('Failed to load crypto prices:', error);
        }
    },

    // Populate currency select dropdowns
    populateCurrencySelects() {
        try {
            // Clear existing options except the first placeholder
            this.elements.fromCurrency.innerHTML = '<option value="">Select currency...</option>';
            this.elements.toCurrency.innerHTML = '<option value="">Select currency...</option>';

            // Add cryptocurrency options
            const cryptoGroup1 = document.createElement('optgroup');
            cryptoGroup1.label = 'Cryptocurrencies';
            const cryptoGroup2 = document.createElement('optgroup');
            cryptoGroup2.label = 'Cryptocurrencies';

            Object.entries(this.supportedCryptos).forEach(([symbol, name]) => {
                const option1 = document.createElement('option');
                option1.value = symbol;
                option1.textContent = `${name} (${symbol})`;
                cryptoGroup1.appendChild(option1);

                const option2 = document.createElement('option');
                option2.value = symbol;
                option2.textContent = `${name} (${symbol})`;
                cryptoGroup2.appendChild(option2);
            });

            // Add fiat currency options
            const fiatGroup1 = document.createElement('optgroup');
            fiatGroup1.label = 'Fiat Currencies';
            const fiatGroup2 = document.createElement('optgroup');
            fiatGroup2.label = 'Fiat Currencies';

            Object.entries(this.supportedFiat).forEach(([symbol, name]) => {
                const option1 = document.createElement('option');
                option1.value = symbol;
                option1.textContent = `${name} (${symbol})`;
                fiatGroup1.appendChild(option1);

                const option2 = document.createElement('option');
                option2.value = symbol;
                option2.textContent = `${name} (${symbol})`;
                fiatGroup2.appendChild(option2);
            });

            this.elements.fromCurrency.appendChild(cryptoGroup1);
            this.elements.fromCurrency.appendChild(fiatGroup1);
            this.elements.toCurrency.appendChild(cryptoGroup2);
            this.elements.toCurrency.appendChild(fiatGroup2);

            console.log('Currency selects populated');
        } catch (error) {
            console.error('Failed to populate currency selects:', error);
        }
    },

    // Perform currency conversion
    async performConversion() {
        const amount = parseFloat(this.elements.amount.value);
        const fromCurrency = this.elements.fromCurrency.value;
        const toCurrency = this.elements.toCurrency.value;

        // Validate inputs
        if (!amount || amount <= 0) {
            this.elements.result.value = '';
            this.hideConversionDetails();
            return;
        }

        if (!fromCurrency || !toCurrency) {
            this.elements.result.value = '';
            this.hideConversionDetails();
            return;
        }

        if (fromCurrency === toCurrency) {
            this.elements.result.value = amount.toFixed(8);
            this.updateConversionDetails(fromCurrency, toCurrency, amount, amount, 1.0, 'same_currency');
            return;
        }

        try {
            // Use API for conversion
            const response = await CryptoChecker.api.post('/crypto/convert', {
                from_currency: fromCurrency,
                to_currency: toCurrency,
                amount: amount
            });

            if (response && response.to_amount !== undefined) {
                const result = response.to_amount;
                const rate = response.rate;
                const conversionType = response.conversion_type;

                // Update result display
                this.elements.result.value = this.formatResult(result);

                // Update conversion details
                this.updateConversionDetails(fromCurrency, toCurrency, amount, result, rate, conversionType);

                // Add to history
                this.addToHistory({
                    from: fromCurrency,
                    to: toCurrency,
                    amount: amount,
                    result: result,
                    rate: rate,
                    timestamp: new Date()
                });

            } else {
                throw new Error('Invalid conversion response');
            }

        } catch (error) {
            console.error('Conversion error:', error);
            this.elements.result.value = 'Error';
            CryptoChecker.showAlert('warning', `Conversion failed: ${error.message}`);
        }
    },

    // Format conversion result
    formatResult(result) {
        if (result >= 1) {
            return result.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 8
            });
        } else {
            return result.toFixed(8);
        }
    },

    // Update conversion details display
    updateConversionDetails(fromCurrency, toCurrency, amount, result, rate, conversionType) {
        if (!this.elements.conversionDetails) return;

        // Show details section
        this.elements.conversionDetails.style.display = 'block';

        // Update conversion rate
        if (this.elements.conversionRate) {
            this.elements.conversionRate.textContent = `1 ${fromCurrency} = ${rate.toFixed(8)} ${toCurrency}`;
        }

        // Update conversion type
        if (this.elements.conversionType) {
            const typeLabels = {
                'crypto_to_crypto': 'Crypto to Crypto',
                'crypto_to_fiat': 'Crypto to Fiat',
                'fiat_to_crypto': 'Fiat to Crypto',
                'fiat_to_fiat': 'Fiat to Fiat',
                'same_currency': 'Same Currency'
            };
            this.elements.conversionType.textContent = typeLabels[conversionType] || 'Unknown';
        }

        // Update last updated time
        if (this.elements.lastUpdated) {
            this.elements.lastUpdated.textContent = 'Just now';
        }
    },

    // Hide conversion details
    hideConversionDetails() {
        if (this.elements.conversionDetails) {
            this.elements.conversionDetails.style.display = 'none';
        }
    },

    // Swap from and to currencies
    swapCurrencies() {
        const fromValue = this.elements.fromCurrency.value;
        const toValue = this.elements.toCurrency.value;

        this.elements.fromCurrency.value = toValue;
        this.elements.toCurrency.value = fromValue;

        // Trigger conversion if amount is entered
        if (this.elements.amount.value > 0) {
            this.performConversion();
        }

        console.log('Currencies swapped:', toValue, '↔', fromValue);
    },

    // Load popular conversions
    async loadPopularConversions() {
        if (!this.elements.popularConversions) return;

        try {
            const popularPairs = [
                { from: 'BTC', to: 'USD', label: 'BTC → USD' },
                { from: 'ETH', to: 'USD', label: 'ETH → USD' },
                { from: 'BTC', to: 'EUR', label: 'BTC → EUR' },
                { from: 'USD', to: 'BTC', label: 'USD → BTC' },
                { from: 'GEM', to: 'USD', label: 'GEM → USD' },
                { from: 'BTC', to: 'ETH', label: 'BTC → ETH' }
            ];

            let html = '<div class="row">';
            popularPairs.forEach((pair, index) => {
                html += `
                    <div class="col-md-4 mb-2">
                        <button class="btn btn-outline-primary btn-sm w-100 popular-conversion"
                                data-from="${pair.from}" data-to="${pair.to}">
                            ${pair.label}
                        </button>
                    </div>
                `;
            });
            html += '</div>';

            this.elements.popularConversions.innerHTML = html;
        } catch (error) {
            console.error('Failed to load popular conversions:', error);
            this.elements.popularConversions.innerHTML = '<p class="text-muted">Failed to load popular conversions</p>';
        }
    },

    // Select a popular conversion
    selectPopularConversion(button) {
        const from = button.dataset.from;
        const to = button.dataset.to;

        this.elements.fromCurrency.value = from;
        this.elements.toCurrency.value = to;

        // Set default amount if empty
        if (!this.elements.amount.value) {
            this.elements.amount.value = '1';
        }

        // Trigger conversion
        this.performConversion();
    },

    // Add conversion to history
    addToHistory(conversion) {
        this.conversionHistory.unshift(conversion);

        // Keep only last 10 conversions
        if (this.conversionHistory.length > 10) {
            this.conversionHistory = this.conversionHistory.slice(0, 10);
        }

        // Save to localStorage
        CryptoChecker.utils.storage.set('conversionHistory', this.conversionHistory, 24 * 60); // 24 hours

        // Update display
        this.updateHistoryDisplay();
    },

    // Load conversion history from localStorage
    loadConversionHistory() {
        const savedHistory = CryptoChecker.utils.storage.get('conversionHistory');
        if (savedHistory && Array.isArray(savedHistory)) {
            this.conversionHistory = savedHistory;
            this.updateHistoryDisplay();
        }
    },

    // Update history display
    updateHistoryDisplay() {
        if (!this.elements.conversionHistory) return;

        if (this.conversionHistory.length === 0) {
            this.elements.conversionHistory.innerHTML = '<p class="text-muted text-center">No conversions yet. Try converting some currencies!</p>';
            return;
        }

        let html = '';
        this.conversionHistory.forEach(conversion => {
            const timeAgo = this.timeAgo(conversion.timestamp);
            html += `
                <div class="d-flex justify-content-between align-items-center border-bottom pb-2 mb-2">
                    <div>
                        <strong>${conversion.amount} ${conversion.from} → ${this.formatResult(conversion.result)} ${conversion.to}</strong>
                        <br>
                        <small class="text-muted">Rate: 1 ${conversion.from} = ${conversion.rate.toFixed(8)} ${conversion.to}</small>
                    </div>
                    <small class="text-muted">${timeAgo}</small>
                </div>
            `;
        });

        this.elements.conversionHistory.innerHTML = html;
    },

    // Clear conversion history
    clearHistory() {
        this.conversionHistory = [];
        CryptoChecker.utils.storage.remove('conversionHistory');
        this.updateHistoryDisplay();
        CryptoChecker.showAlert('info', 'Conversion history cleared', 3000);
    },

    // Update supported currency lists
    updateSupportedCurrencyLists() {
        // Update supported crypto list
        if (this.elements.supportedCrypto) {
            const cryptoList = Object.entries(this.supportedCryptos)
                .map(([symbol, name]) => `<span class="badge bg-primary me-1 mb-1">${symbol}</span>`)
                .join('');
            this.elements.supportedCrypto.innerHTML = cryptoList || '<p class="text-muted">Loading...</p>';
        }

        // Update supported fiat list
        if (this.elements.supportedFiat) {
            const fiatList = Object.entries(this.supportedFiat)
                .map(([symbol, name]) => `<span class="badge bg-success me-1 mb-1">${symbol}</span>`)
                .join('');
            this.elements.supportedFiat.innerHTML = fiatList || '<p class="text-muted">Loading...</p>';
        }
    },

    // Refresh exchange rates
    async refreshRates() {
        console.log('Refreshing exchange rates...');

        try {
            await this.loadExchangeRates();
            await this.loadCryptoPrices();

            // Trigger conversion if values are present
            if (this.elements.amount.value > 0 && this.elements.fromCurrency.value && this.elements.toCurrency.value) {
                await this.performConversion();
            }

            CryptoChecker.showAlert('success', 'Exchange rates updated successfully!', 3000);
        } catch (error) {
            console.error('Failed to refresh rates:', error);
            CryptoChecker.showAlert('warning', 'Failed to update exchange rates', 3000);
        }
    },

    // Utility function to calculate time ago
    timeAgo(timestamp) {
        const now = new Date();
        const diff = now - new Date(timestamp);
        const minutes = Math.floor(diff / 60000);

        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;

        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;

        const days = Math.floor(hours / 24);
        return `${days}d ago`;
    },

    // Handle URL parameters for pre-filling form
    handleUrlParameters() {
        try {
            const urlParams = new URLSearchParams(window.location.search);
            const fromCurrency = urlParams.get('from');
            const toCurrency = urlParams.get('to');
            const amount = urlParams.get('amount');

            if (fromCurrency && this.elements.fromCurrency) {
                this.elements.fromCurrency.value = fromCurrency.toUpperCase();
            }

            if (toCurrency && this.elements.toCurrency) {
                this.elements.toCurrency.value = toCurrency.toUpperCase();
            }

            if (amount && this.elements.amount) {
                this.elements.amount.value = amount;
            }

            // Trigger conversion if all parameters are present
            if (fromCurrency && toCurrency && amount) {
                setTimeout(() => {
                    this.performConversion();
                }, 500); // Wait for currency selects to be populated
            }

            // Clear URL parameters after processing
            if (urlParams.get('from') || urlParams.get('to') || urlParams.get('amount')) {
                const newUrl = window.location.pathname;
                window.history.replaceState({}, document.title, newUrl);
            }

        } catch (error) {
            console.error('Error handling URL parameters:', error);
        }
    },

    // Cleanup converter
    destroy() {
        console.log('Currency Converter cleaned up');
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const converterElement = document.querySelector('#converter-form, .converter-container');
    if (converterElement) {
        Converter.init();
    }
});

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Converter;
}