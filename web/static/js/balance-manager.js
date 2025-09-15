/**
 * Authentication-Only Balance Manager for Crypto Gaming Platform
 * Handles balance management for authenticated users only
 * Provides single source of truth for all balance operations
 */

class AuthenticatedBalanceManager {
    constructor() {
        this.currentBalance = 0;
        this.isAuthenticated = false;
        this.balanceListeners = [];
        this.syncInProgress = false;
        this.lastSyncTime = null;
        this.autoSaveTimer = null;
        this.heartbeatTimer = null;

        // Configuration
        this.config = {
            autoSaveInterval: 30000, // 30 seconds
            heartbeatInterval: 60000, // 1 minute
            maxRetries: 3,
            storageKeys: {
                authToken: 'access_token',
                isLoggedIn: 'is_logged_in'
            }
        };

        this.init();
    }

    async init() {
        console.log('🎯 Initializing Authenticated Balance Manager...');

        // Detect authentication status
        await this.detectAuthStatus();

        // Load initial balance if authenticated
        if (this.isAuthenticated) {
            await this.loadBalance();

            // Setup event listeners
            this.setupEventListeners();

            // Start background processes
            this.startAutoSave();
            this.startHeartbeat();

            console.log(`✅ Balance Manager initialized - Authenticated: ${this.isAuthenticated}, Balance: ${this.currentBalance} GEM`);
        } else {
            console.log('⚠️ User not authenticated - balance manager waiting for login');
        }

        // Set flag to prevent other components from overriding
        window.balanceManagerAuthority = true;

        // Set sync time on initialization
        this.lastSyncTime = Date.now();

        // Notify all listeners that balance is loaded
        this.notifyBalanceChange('loaded', null, null, 'initialization');
    }

    async detectAuthStatus() {
        try {
            // Primary validation: Check API endpoint (like auth.js does)
            try {
                const response = await fetch('/api/auth/me', {
                    method: 'GET',
                    credentials: 'same-origin'
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.status === 'success' && data.user) {
                        this.isAuthenticated = true;
                        console.log(`🔍 Auth Status Detected via API - Authenticated: ${this.isAuthenticated}`);
                        return;
                    }
                }
            } catch (apiError) {
                console.log('🔍 API auth check failed, falling back to localStorage');
            }

            // Fallback validation: Check localStorage tokens
            const token = localStorage.getItem(this.config.storageKeys.authToken);
            const isLoggedIn = localStorage.getItem(this.config.storageKeys.isLoggedIn) === 'true';

            this.isAuthenticated = !!(token && token !== 'null' && token !== 'undefined' && isLoggedIn);

            console.log(`🔍 Auth Status Detected via localStorage - Authenticated: ${this.isAuthenticated}`);
        } catch (error) {
            console.warn('⚠️ Auth detection failed:', error);
            this.isAuthenticated = false;
        }
    }

    async loadBalance() {
        if (!this.isAuthenticated) {
            console.log('⚠️ User not authenticated - skipping balance load');
            return 0; // Return demo balance of 0 instead of throwing error
        }

        try {
            await this.loadAuthenticatedBalance();
        } catch (error) {
            console.error('❌ Failed to load balance:', error);
            this.notifyBalanceChange('error', error.message, null, 'load-error');
            throw error;
        }
    }

    async loadAuthenticatedBalance() {
        try {
            const response = await fetch('/api/gaming/roulette/balance', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem(this.config.storageKeys.authToken)}`,
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (data.status === 'success' && data.data) {
                this.currentBalance = parseFloat(data.data.balance) || 0;
                console.log(`💰 Authenticated balance loaded: ${this.currentBalance} GEM`);
                return;
            } else {
                throw new Error(data.error || 'Failed to load authenticated balance');
            }
        } catch (error) {
            console.error('❌ Authenticated balance load failed:', error);
            throw error;
        }
    }

    async updateBalance(newBalance, source = 'manual') {
        if (!this.isAuthenticated) {
            console.log('⚠️ User not authenticated - skipping balance update');
            return false; // Return false instead of throwing error
        }

        try {
            // Validate input
            const validBalance = Math.max(0, parseFloat(newBalance) || 0);

            if (validBalance === this.currentBalance) {
                // Even if balance is same, update sync time
                this.lastSyncTime = Date.now();
                return;
            }

            const oldBalance = this.currentBalance;

            // Update balance immediately and synchronously
            this.currentBalance = validBalance;
            this.lastSyncTime = Date.now();

            // Save to server
            await this.saveAuthenticatedBalance(validBalance);

            // Notify all listeners AFTER balance is fully updated
            this.notifyBalanceChange('updated', null, oldBalance, source);

            console.log(`💰 Balance updated: ${oldBalance} → ${validBalance} GEM (${source})`);

        } catch (error) {
            console.error('❌ Balance update failed:', error);
            this.notifyBalanceChange('error', error.message, null, 'update-error');
            throw error;
        }
    }

    async saveAuthenticatedBalance(balance) {
        try {
            const response = await fetch('/api/gaming/roulette/update_balance', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem(this.config.storageKeys.authToken)}`,
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    balance: balance
                })
            });

            const data = await response.json();

            if (data.status !== 'success') {
                throw new Error(data.error || 'Failed to save authenticated balance');
            }
        } catch (error) {
            console.error('❌ Authenticated balance save failed:', error);
            throw error;
        }
    }

    // Event listener management
    addBalanceListener(callback) {
        if (typeof callback === 'function') {
            this.balanceListeners.push(callback);
        }
    }

    removeBalanceListener(callback) {
        const index = this.balanceListeners.indexOf(callback);
        if (index > -1) {
            this.balanceListeners.splice(index, 1);
        }
    }

    notifyBalanceChange(type, error = null, oldBalance = null, source = null) {
        try {
            const event = {
                type: type, // 'updated', 'error', 'loaded', 'refreshed'
                balance: this.currentBalance,
                oldBalance: oldBalance,
                isAuthenticated: this.isAuthenticated,
                error: error,
                source: source || 'balance-manager',
                timestamp: Date.now()
            };

            // Notify registered listeners
            this.balanceListeners.forEach(callback => {
                try {
                    callback(event);
                } catch (err) {
                    console.error('❌ Balance listener error:', err);
                }
            });

            // Dispatch global event for backwards compatibility
            try {
                window.dispatchEvent(new CustomEvent('balanceUpdated', {
                    detail: {
                        balance: this.currentBalance,
                        source: event.source,
                        isAuthenticated: this.isAuthenticated,
                        type: type
                    }
                }));
            } catch (dispatchError) {
                console.error('❌ Failed to dispatch balance event:', dispatchError);
            }
        } catch (error) {
            console.error('❌ Critical error in notifyBalanceChange:', error);
            // Don't let notification errors break the system
        }
    }

    setupEventListeners() {
        // Listen for auth status changes
        window.addEventListener('authStatusChanged', (event) => {
            console.log('🔄 Auth status changed, reloading balance...');
            this.detectAuthStatus().then(() => {
                if (this.isAuthenticated) {
                    this.loadBalance();
                }
            });
        });

        // Page visibility change handling
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.isAuthenticated) {
                console.log('🔄 Page became visible, syncing balance...');
                this.loadBalance();
            }
        });
    }

    startAutoSave() {
        if (this.autoSaveTimer) clearInterval(this.autoSaveTimer);

        this.autoSaveTimer = setInterval(() => {
            if (this.isAuthenticated) {
                this.loadBalance().catch(err => console.warn('⚠️ Auto-refresh failed:', err));
            }
        }, this.config.autoSaveInterval);
    }

    startHeartbeat() {
        if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);

        this.heartbeatTimer = setInterval(() => {
            // Periodic balance refresh to catch external changes
            if (this.isAuthenticated) {
                this.loadBalance().catch(err => console.warn('⚠️ Heartbeat refresh failed:', err));
            }
        }, this.config.heartbeatInterval);
    }

    // Public API
    getBalance() {
        // 🚨 EMERGENCY: Circuit breaker for balance manager
        if (!this.errorCount) this.errorCount = 0;
        if (this.errorCount >= 10) {
            console.error('🚨 BALANCE MANAGER CIRCUIT BREAKER: Too many errors, returning safe value');
            return this.isAuthenticated ? 0 : 5000;
        }

        try {
            // Check authentication status first
            if (!this.isAuthenticated) {
                console.log('⚠️ User not authenticated - returning demo balance');
                return 5000; // Return demo balance instead of throwing error
            }

            // Validate current balance before returning
            if (typeof this.currentBalance !== 'number' || isNaN(this.currentBalance)) {
                console.warn('⚠️ Invalid balance detected, resetting to 0');
                this.currentBalance = 0;
                return 0;
            }

            // Ensure balance is non-negative
            if (this.currentBalance < 0) {
                console.warn('⚠️ Negative balance detected, resetting to 0');
                this.currentBalance = 0;
                return 0;
            }

            return this.currentBalance;
        } catch (error) {
            this.errorCount++;
            console.error('❌ Critical error in getBalance:', this.errorCount, '/ 10:', error);
            // Return safe fallback value instead of throwing
            return this.isAuthenticated ? 0 : 5000;
        }
    }

    isUserAuthenticated() {
        return this.isAuthenticated;
    }

    async refresh() {
        console.log('🔄 Manual balance refresh requested');
        await this.detectAuthStatus();
        if (this.isAuthenticated) {
            await this.loadBalance();
        }
    }

    destroy() {
        if (this.autoSaveTimer) clearInterval(this.autoSaveTimer);
        if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
        this.balanceListeners = [];
        console.log('🗑️ Balance Manager destroyed');
    }
}

// Global instance - auto-initialize
window.balanceManager = null;

// Initialize when DOM is ready with error handling
function initializeBalanceManager() {
    try {
        if (!window.balanceManager) {
            window.balanceManager = new AuthenticatedBalanceManager();
            console.log('✅ Balance Manager initialized successfully');
        }
    } catch (error) {
        console.error('❌ Failed to initialize Balance Manager:', error);
        // Set a placeholder to prevent other code from breaking
        window.balanceManager = {
            getBalance: () => 5000, // Demo balance fallback
            isUserAuthenticated: () => false,
            notifyBalanceChange: () => {},
            refresh: () => Promise.resolve(),
            destroy: () => {}
        };
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeBalanceManager);
} else {
    // DOM already ready
    initializeBalanceManager();
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthenticatedBalanceManager;
}