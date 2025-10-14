/**
 * CryptoChecker Version3 - Main JavaScript Module
 * Core functionality and utilities
 */

// Global App Object
window.CryptoChecker = {
    // Configuration
    config: {
        apiBaseUrl: '/api',
        refreshInterval: 30000, // 30 seconds
        maxRetries: 3,
        retryDelay: 1000
    },

    // Current user data
    user: null,
    isAuthenticated: false,
    isGuest: true,

    // Cache for API responses
    cache: new Map(),

    // API module for making HTTP requests
    api: {
        // Base configuration
        baseUrl: '/api',
        defaultHeaders: {
            'Content-Type': 'application/json'
        },

        // Get authentication headers
        getAuthHeaders() {
            const headers = { ...this.defaultHeaders };
            const token = localStorage.getItem('auth_token');
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            return headers;
        },

        // Generic request method
        async request(method, endpoint, data = null) {
            const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
            const options = {
                method: method.toUpperCase(),
                headers: this.getAuthHeaders()
            };

            // Handle different data types
            if (data) {
                if (data instanceof FormData) {
                    // Remove Content-Type for FormData to let browser set it
                    delete options.headers['Content-Type'];
                    options.body = data;
                } else if (typeof data === 'object') {
                    options.body = JSON.stringify(data);
                } else {
                    options.body = data;
                }
            }

            try {
                console.log(`🌐 API Request: ${method.toUpperCase()} ${url}`);

                const response = await fetch(url, options);

                let responseData;
                try {
                    responseData = await response.json();
                } catch (jsonError) {
                    console.warn('Failed to parse JSON response:', jsonError);
                    responseData = { error: 'Invalid JSON response from server' };
                }

                const result = {
                    ...responseData,
                    status: response.status,
                    ok: response.ok
                };

                // Log response for debugging
                if (!response.ok) {
                    console.warn(`⚠️ API Error ${response.status}:`, url, result);
                } else {
                    console.log(`✅ API Success ${response.status}:`, url);
                }

                return result;
            } catch (error) {
                console.error('❌ API Request Error:', error);
                console.error('Request details:', {
                    method: method.toUpperCase(),
                    url,
                    hasAuth: options.headers['Authorization'] ? 'Yes' : 'No',
                    error: error.message
                });
                throw new Error(`Request failed: ${error.message}`);
            }
        },

        // Convenience methods
        async get(endpoint) {
            return this.request('GET', endpoint);
        },

        async post(endpoint, data) {
            return this.request('POST', endpoint, data);
        },

        async put(endpoint, data) {
            return this.request('PUT', endpoint, data);
        },

        async delete(endpoint) {
            return this.request('DELETE', endpoint);
        }
    },

    // Utility functions
    utils: {
        // Generate unique ID
        generateId() {
            return 'id-' + Math.random().toString(36).substr(2, 9) + '-' + Date.now().toString(36);
        },

        // Storage utilities with expiration
        storage: {
            set(key, value, minutesExpiry = 60) {
                const item = {
                    value: value,
                    expiry: Date.now() + (minutesExpiry * 60 * 1000)
                };
                localStorage.setItem(key, JSON.stringify(item));
            },

            get(key) {
                const itemStr = localStorage.getItem(key);
                if (!itemStr) return null;

                try {
                    const item = JSON.parse(itemStr);
                    if (Date.now() > item.expiry) {
                        localStorage.removeItem(key);
                        return null;
                    }
                    return item.value;
                } catch (error) {
                    localStorage.removeItem(key);
                    return null;
                }
            },

            remove(key) {
                localStorage.removeItem(key);
            }
        },

        // Format numbers
        formatNumber(num, decimals = 2) {
            return new Intl.NumberFormat('en-US', {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals
            }).format(num);
        },

        // Debounce function
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
        }
    },

    // Initialize the application
    init() {
        this.initEventListeners();
        this.startPriceUpdates();
        this.startBalanceUpdates();
        console.log('CryptoChecker v3 initialized');
    },

    // Set up global event listeners
    initEventListeners() {
        // Handle navigation clicks and login modal actions
        document.addEventListener('click', (e) => {
            console.log('🖱️ Global click handler triggered for:', e.target.tagName, e.target.id, e.target.className);
            if (e.target.matches('[data-action]')) {
                console.log('✨ Found data-action element:', e.target.dataset.action);
                e.preventDefault();
                const action = e.target.dataset.action;
                if (action === 'showLoginModal') {
                    console.log('📬 Calling showLoginModal...');
                    this.showLoginModal();
                } else {
                    this.handleAction(action, e.target);
                }
            }
        });

        // Handle form submissions
        document.addEventListener('submit', (e) => {
            if (e.target.matches('[data-api-form]')) {
                e.preventDefault();
                this.handleApiForm(e.target);
            }
        });

        // Handle keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'r':
                        e.preventDefault();
                        this.refreshData();
                        break;
                    case '/':
                        e.preventDefault();
                        this.focusSearch();
                        break;
                }
            }
        });
    },

    // Start automatic price updates
    startPriceUpdates() {
        // Initial load with delay to prevent race conditions
        setTimeout(() => {
            this.updatePrices();
        }, 1000);

        // Set up interval
        setInterval(() => {
            this.updatePrices();
        }, this.config.refreshInterval);
    },

    // Update cryptocurrency prices
    async updatePrices() {
        try {
            const prices = await this.api.get('/crypto/prices?limit=20');
            if (prices.success) {
                // Cache the successful response
                this.utils.storage.set('crypto_prices', prices.data, 10); // 10 minutes cache
                this.utils.storage.set('last_price_update', new Date().toISOString(), 60);
                this.updatePriceDisplays(prices.data);
                this.updatePriceStatus('live');
            } else {
                // Try to use cached data
                await this.handlePriceUpdateFailure('API returned unsuccessful response');
            }
        } catch (error) {
            console.warn('Failed to update prices:', error);
            await this.handlePriceUpdateFailure(error.message);
        }
    },

    // Handle price update failures gracefully
    async handlePriceUpdateFailure(errorMessage) {
        // Try to use cached data first
        const cachedPrices = this.utils.storage.get('crypto_prices');
        if (cachedPrices && cachedPrices.length > 0) {
            console.log('Using cached price data due to API failure');
            this.updatePriceDisplays(cachedPrices);
            this.updatePriceStatus('cached');
            return;
        }

        // Fallback to mock data if no cache available
        console.log('Using mock price data due to complete API failure');
        const mockData = this.getMockPriceData();
        this.updatePriceDisplays(mockData);
        this.updatePriceStatus('offline');
    },

    // Update price status indicator
    updatePriceStatus(status) {
        const statusElement = document.getElementById('price-status');
        if (statusElement) {
            const statusText = {
                'live': '🟢 Live',
                'cached': '🟡 Cached',
                'offline': '🔴 Offline'
            };
            statusElement.textContent = statusText[status] || '⚪ Unknown';
            statusElement.className = `price-status ${status}`;
        }
    },

    // Provide mock price data as ultimate fallback
    getMockPriceData() {
        return [
            { id: 'bitcoin', symbol: 'BTC', name: 'Bitcoin', current_price_usd: 43250, price_change_percentage_24h: 2.1, market_cap: 847000000000, image: null },
            { id: 'ethereum', symbol: 'ETH', name: 'Ethereum', current_price_usd: 2640, price_change_percentage_24h: 1.8, market_cap: 317000000000, image: null },
            { id: 'binancecoin', symbol: 'BNB', name: 'BNB', current_price_usd: 310, price_change_percentage_24h: -0.5, market_cap: 47000000000, image: null },
            { id: 'cardano', symbol: 'ADA', name: 'Cardano', current_price_usd: 0.48, price_change_percentage_24h: 3.2, market_cap: 17000000000, image: null },
            { id: 'solana', symbol: 'SOL', name: 'Solana', current_price_usd: 98, price_change_percentage_24h: 4.1, market_cap: 43000000000, image: null },
            { id: 'ripple', symbol: 'XRP', name: 'XRP', current_price_usd: 0.52, price_change_percentage_24h: 1.1, market_cap: 29000000000, image: null },
            { id: 'polkadot', symbol: 'DOT', name: 'Polkadot', current_price_usd: 7.2, price_change_percentage_24h: -1.2, market_cap: 9000000000, image: null }
        ];
    },

    // Update price displays in the UI
    updatePriceDisplays(cryptos) {
        // Update BTC price in navbar/stats
        const btc = cryptos.find(c => c.symbol.toLowerCase() === 'btc');
        if (btc) {
            this.updateElement('btc-price', this.formatPrice(btc.current_price_usd));
            this.updateElement('btc-change', this.formatChange(btc.price_change_percentage_24h));
        }

        // Update crypto count
        this.updateElement('crypto-count', `${cryptos.length}+`);

        // Emit event for other modules
        document.dispatchEvent(new CustomEvent('pricesUpdated', { detail: cryptos }));
    },

    // Start automatic balance updates
    startBalanceUpdates() {
        // Update balance every 30 seconds if authenticated
        setInterval(async () => {
            if (this.isAuthenticated && !this.isGuest) {
                try {
                    const response = await this.api.get('/crypto/portfolio/balance');
                    if (response.success && response.balance !== undefined) {
                        // Update user balance if it changed
                        if (this.user && this.user.wallet_balance !== response.balance) {
                            this.user.wallet_balance = response.balance;

                            // Dispatch balance update event
                            document.dispatchEvent(new CustomEvent('balanceUpdated', {
                                detail: {
                                    balance: response.balance,
                                    isGuest: false
                                }
                            }));

                            // Update Auth module
                            if (window.Auth && Auth.currentUser) {
                                Auth.currentUser.wallet_balance = response.balance;
                                Auth.updateBalanceDisplays();
                            }
                        }
                    }
                } catch (error) {
                    console.warn('Failed to update balance:', error);
                }
            }
        }, 30000); // 30 seconds
    },

    // Manually refresh balance (can be called by other modules)
    async refreshBalance() {
        if (this.isAuthenticated && !this.isGuest) {
            try {
                const response = await this.api.get('/auth/status');
                if (response.authenticated && response.user && response.user.wallet_balance !== undefined) {
                    // Update user balance
                    if (this.user && this.user.wallet_balance !== response.user.wallet_balance) {
                        this.user.wallet_balance = response.user.wallet_balance;

                        // Dispatch balance update event
                        document.dispatchEvent(new CustomEvent('balanceUpdated', {
                            detail: {
                                balance: response.user.wallet_balance,
                                isGuest: false
                            }
                        }));

                        // Update Auth module and sync authentication status
                        if (window.Auth) {
                            if (Auth.currentUser) {
                                Auth.currentUser.wallet_balance = response.user.wallet_balance;
                            }
                            Auth.updateBalanceDisplays();

                            // Sync authentication state
                            this.user = response.user;
                            this.isAuthenticated = true;
                            this.isGuest = false;
                        }

                        console.log(`Balance refreshed: ${response.user.wallet_balance} GEM`);
                    }
                }
                return true;
            } catch (error) {
                console.warn('Failed to refresh balance:', error);
                return false;
            }
        }
        return false;
    },

    // Handle action buttons
    handleAction(action, element) {
        switch (action) {
            case 'refresh':
                this.refreshData();
                break;
            case 'login':
                Auth.showLoginModal();
                break;
            case 'logout':
                Auth.logout();
                break;
            case 'guest-info':
                this.showGuestInfo();
                break;
            default:
                console.warn('Unknown action:', action);
        }
    },

    // Handle API form submissions
    async handleApiForm(form) {
        const formData = new FormData(form);
        const endpoint = form.dataset.apiForm;
        const method = form.dataset.method || 'POST';

        try {
            this.showLoading(form);
            const response = await this.api.request(method, endpoint, formData);
            this.handleApiResponse(response, form);
        } catch (error) {
            this.showAlert('error', error.message);
        } finally {
            this.hideLoading(form);
        }
    },

    // Handle API response from form submissions
    handleApiResponse(response, form) {
        try {
            // Check if response is successful
            if (response.success || (response.status >= 200 && response.status < 300)) {
                // Handle successful response
                if (response.message) {
                    this.showAlert('success', response.message, 4000);
                } else if (response.data && response.data.message) {
                    this.showAlert('success', response.data.message, 4000);
                } else {
                    this.showAlert('success', 'Operation completed successfully', 3000);
                }

                // Reset form if it was a submission
                if (form && typeof form.reset === 'function') {
                    form.reset();
                }

                // Trigger any custom success handlers
                if (form && form.dataset.onSuccess) {
                    const successHandler = window[form.dataset.onSuccess];
                    if (typeof successHandler === 'function') {
                        successHandler(response);
                    }
                }

                // Refresh authentication status and balance if needed
                if (response.user || response.access_token) {
                    setTimeout(() => {
                        if (window.Auth && typeof window.Auth.checkAuthStatus === 'function') {
                            window.Auth.checkAuthStatus();
                        }
                    }, 500);
                }

            } else {
                // Handle error response
                let errorMessage = 'Operation failed';

                if (response.error) {
                    errorMessage = response.error;
                } else if (response.detail) {
                    errorMessage = response.detail;
                } else if (response.message) {
                    errorMessage = response.message;
                } else if (response.status) {
                    errorMessage = `Request failed with status ${response.status}`;
                }

                this.showAlert('danger', errorMessage, 5000);

                // Log error for debugging
                console.error('API Response Error:', response);
            }

        } catch (error) {
            console.error('Error handling API response:', error);
            this.showAlert('danger', 'Failed to process server response', 4000);
        }
    },

    // Refresh all data
    async refreshData() {
        this.showAlert('info', 'Refreshing data...', 2000);
        await Promise.all([
            this.updatePrices(),
            Auth.checkAuthStatus()
        ]);
        this.showAlert('success', 'Data refreshed!', 2000);
    },

    // Focus search input
    focusSearch() {
        const searchInput = document.querySelector('#price-search, .search-input');
        if (searchInput) {
            searchInput.focus();
        }
    },

    // Show guest mode information
    showGuestInfo() {
        this.showModal('Guest Mode Information', `
            <div class="alert alert-info">
                <h6><i class="bi bi-info-circle"></i> You're in Guest Mode</h6>
                <p class="mb-2">You can explore all features with limitations:</p>
                <ul class="mb-2">
                    <li>5,000 temporary GEM balance</li>
                    <li>Full crypto tracking access</li>
                    <li>Currency converter access</li>
                    <li>Roulette gaming access</li>
                </ul>
                <p class="mb-0"><strong>Limitations:</strong> No balance persistence, no transaction history</p>
            </div>
            <div class="text-center">
                <button class="btn btn-primary" onclick="Auth.showLoginModal()">
                    <i class="bi bi-person-plus"></i> Sign Up / Login
                </button>
            </div>
        `);
    },

    // API wrapper object (moved to end to avoid conflicts)

    // Utility functions
    utils: {
        // Format price with appropriate currency symbol
        formatPrice(price, currency = 'USD') {
            if (price === null || price === undefined) return 'N/A';

            const formatter = new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency,
                minimumFractionDigits: price < 1 ? 6 : 2,
                maximumFractionDigits: price < 1 ? 6 : 2
            });

            return formatter.format(price);
        },

        // Format percentage change
        formatChange(change) {
            if (change === null || change === undefined) return 'N/A';

            const formatted = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
            const className = change >= 0 ? 'text-success' : 'text-danger';

            return `<span class="${className}">${formatted}</span>`;
        },

        // Format large numbers
        formatNumber(num) {
            if (num === null || num === undefined) return 'N/A';

            if (num >= 1e12) return (num / 1e12).toFixed(2) + 'T';
            if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
            if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
            if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';

            return num.toFixed(2);
        },

        // Debounce function
        debounce(func, delay) {
            let timeoutId;
            return function (...args) {
                clearTimeout(timeoutId);
                timeoutId = setTimeout(() => func.apply(this, args), delay);
            };
        },

        // Throttle function
        throttle(func, limit) {
            let inThrottle;
            return function (...args) {
                if (!inThrottle) {
                    func.apply(this, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            };
        },

        // Deep clone object
        deepClone(obj) {
            return JSON.parse(JSON.stringify(obj));
        },

        // Generate random ID
        generateId() {
            return Date.now().toString(36) + Math.random().toString(36).substr(2);
        },

        // Validate email
        isValidEmail(email) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(email);
        },

        // Local storage with expiry
        storage: {
            set(key, value, expiryMinutes = 60) {
                const item = {
                    value: value,
                    expiry: Date.now() + (expiryMinutes * 60 * 1000)
                };
                localStorage.setItem(key, JSON.stringify(item));
            },

            get(key) {
                const itemStr = localStorage.getItem(key);
                if (!itemStr) return null;

                try {
                    const item = JSON.parse(itemStr);
                    if (Date.now() > item.expiry) {
                        localStorage.removeItem(key);
                        return null;
                    }
                    return item.value;
                } catch {
                    localStorage.removeItem(key);
                    return null;
                }
            },

            remove(key) {
                localStorage.removeItem(key);
            }
        }
    },

    // Format price (shorthand)
    formatPrice(price, currency = 'USD') {
        return this.utils.formatPrice(price, currency);
    },

    // Format change (shorthand)
    formatChange(change) {
        return this.utils.formatChange(change);
    },

    // Format number (shorthand)
    formatNumber(num) {
        return this.utils.formatNumber(num);
    },

    // Update element content safely
    updateElement(id, content) {
        const element = document.getElementById(id);
        if (element) {
            if (typeof content === 'string' && content.includes('<')) {
                element.innerHTML = content;
            } else {
                element.textContent = content;
            }
        }
    },

    // Show loading state
    showLoading(element) {
        if (element) {
            element.classList.add('loading');
            const btn = element.querySelector('button[type="submit"], .btn-primary');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Loading...';
            }
        }
    },

    // Hide loading state
    hideLoading(element) {
        if (element) {
            element.classList.remove('loading');
            const btn = element.querySelector('button[type="submit"], .btn-primary');
            if (btn) {
                btn.disabled = false;
                // Restore original text (you might want to store this)
                btn.innerHTML = btn.dataset.originalText || 'Submit';
            }
        }
    },

    // Show alert message
    showAlert(type, message, duration = 5000) {
        const alertsContainer = document.getElementById('alerts-container');
        if (!alertsContainer) return;

        const alertId = this.utils.generateId();
        const alertHtml = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
                <i class="bi bi-${this.getAlertIcon(type)}"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        alertsContainer.insertAdjacentHTML('beforeend', alertHtml);

        // Auto-dismiss after duration
        if (duration > 0) {
            setTimeout(() => {
                const alert = document.getElementById(alertId);
                if (alert) {
                    alert.remove();
                }
            }, duration);
        }
    },

    // Get icon for alert type
    getAlertIcon(type) {
        const icons = {
            success: 'check-circle',
            danger: 'exclamation-triangle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    },

    // Show modal
    showModal(title, content, size = '') {
        const modalId = 'dynamic-modal-' + this.utils.generateId();
        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1">
                <div class="modal-dialog ${size}">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${content}
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);

        const modal = new bootstrap.Modal(document.getElementById(modalId));
        modal.show();

        // Clean up when modal is hidden
        document.getElementById(modalId).addEventListener('hidden.bs.modal', () => {
            document.getElementById(modalId).remove();
        });

        return modal;
    },

    // Show login modal
    showLoginModal() {
        if (window.Auth && typeof window.Auth.showLoginModal === 'function') {
            window.Auth.showLoginModal();
        } else {
            console.warn('Auth module not ready or showLoginModal function not available');
        }
    }
};

// Alias for easier access
window.App = window.CryptoChecker;

// Global function to show login modal (defined immediately when script loads)
window.showLoginModal = function() {
    if (window.Auth && typeof window.Auth.showLoginModal === 'function') {
        window.Auth.showLoginModal();
    } else {
        console.warn('Auth module not ready or showLoginModal function not available');
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    CryptoChecker.init();

    // Set active nav link based on current page
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link-modern').forEach(link => {
        const href = link.getAttribute('href');
        if (currentPath === href || (currentPath === '/' && href === '/')) {
            link.classList.add('active');
        }
    });
});
