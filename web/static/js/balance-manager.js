/**
 * Unified Balance Manager for Crypto Gaming Platform
 * Handles balance persistence for both authenticated and demo users
 * Provides single source of truth for all balance operations
 */

class UnifiedBalanceManager {
    constructor() {
        this.currentBalance = 0;
        this.isDemo = true;
        this.isAuthenticated = false;
        this.balanceListeners = [];
        this.syncInProgress = false;
        this.lastSyncTime = null;
        this.autoSaveTimer = null;
        this.heartbeatTimer = null;
        
        // Performance optimization: Rate limiting for stale detection
        this.lastStaleCheck = 0;
        this.lastForceRefresh = 0;
        this.refreshAttempts = 0;
        this.refreshCooldownActive = false;
        
        // Configuration
        this.config = {
            defaultDemoBalance: 5000,
            autoSaveInterval: 30000, // 30 seconds
            heartbeatInterval: 60000, // 1 minute
            maxRetries: 3,
            // Performance optimization thresholds
            staleThreshold: 30000, // 30 seconds (increased from 5 seconds)
            refreshCooldown: 2000, // 2 seconds minimum between refreshes
            maxRefreshAttempts: 3, // Maximum refresh attempts per cooldown period
            cooldownResetTime: 10000, // 10 seconds to reset refresh attempts
            storageKeys: {
                demoBalance: 'cc_demo_balance_v2',
                balanceTimestamp: 'cc_balance_timestamp',
                authToken: 'access_token',
                isLoggedIn: 'is_logged_in'
            }
        };
        
        this.init();
    }

    async init() {
        console.log('🎯 Initializing Unified Balance Manager...');
        
        // Detect authentication status
        await this.detectAuthStatus();
        
        // Load initial balance
        await this.loadBalance();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Start background processes
        this.startAutoSave();
        this.startHeartbeat();
        
        console.log(`✅ Balance Manager initialized - Demo: ${this.isDemo}, Balance: ${this.currentBalance} GEM`);
        
        // ✅ Set flag to prevent other components from overriding
        window.balanceManagerAuthority = true;
        
        // PERFORMANCE FIX: Set sync time on initialization to prevent immediate stale detection
        this.lastSyncTime = Date.now();
        
        // Notify all listeners that balance is loaded
        this.notifyBalanceChange('loaded', null, null, 'initialization');
    }

    async detectAuthStatus() {
        try {
            // Check for access token
            const token = localStorage.getItem(this.config.storageKeys.authToken);
            const isLoggedIn = localStorage.getItem(this.config.storageKeys.isLoggedIn) === 'true';
            
            this.isAuthenticated = !!(token && token !== 'null' && token !== 'undefined' && isLoggedIn);
            this.isDemo = !this.isAuthenticated;
            
            console.log(`🔍 Auth Status Detected - Authenticated: ${this.isAuthenticated}, Demo: ${this.isDemo}`);
        } catch (error) {
            console.warn('⚠️ Auth detection failed, defaulting to demo mode:', error);
            this.isAuthenticated = false;
            this.isDemo = true;
        }
    }

    async loadBalance() {
        try {
            if (this.isAuthenticated) {
                await this.loadAuthenticatedBalance();
            } else {
                await this.loadDemoBalance();
            }
        } catch (error) {
            console.error('❌ Failed to load balance:', error);
            this.currentBalance = this.config.defaultDemoBalance;
            this.notifyBalanceChange('error', error.message, null, 'load-error');
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
                this.isDemo = data.data.is_demo_mode || false;
                console.log(`💰 Authenticated balance loaded: ${this.currentBalance} GEM`);
            } else {
                throw new Error(data.error || 'Failed to load authenticated balance');
            }
        } catch (error) {
            console.error('❌ Authenticated balance load failed:', error);
            // Fallback to demo mode on auth failure
            this.isAuthenticated = false;
            this.isDemo = true;
            await this.loadDemoBalance();
        }
    }

    async loadDemoBalance() {
        try {
            // Priority chain: localStorage → Server → Cookie → Default
            let loadedBalance = null;
            let source = 'default';

            // 1. Try localStorage first (most reliable for demo)
            const localStorageBalance = localStorage.getItem(this.config.storageKeys.demoBalance);
            if (localStorageBalance) {
                try {
                    loadedBalance = parseFloat(localStorageBalance);
                    source = 'localStorage';
                } catch (e) {
                    console.warn('⚠️ Invalid localStorage balance, trying server...');
                }
            }

            // 2. If no localStorage, try server restoration
            if (loadedBalance === null) {
                try {
                    const serverBalance = await this.restoreFromServer();
                    if (serverBalance !== null) {
                        loadedBalance = serverBalance;
                        source = 'server';
                    }
                } catch (e) {
                    console.warn('⚠️ Server restoration failed, trying cookie...');
                }
            }

            // 3. Cookie fallback
            if (loadedBalance === null) {
                const cookieBalance = this.getCookie('cc_demo_balance');
                if (cookieBalance) {
                    try {
                        loadedBalance = parseFloat(cookieBalance);
                        source = 'cookie';
                    } catch (e) {
                        console.warn('⚠️ Invalid cookie balance, using default...');
                    }
                }
            }

            // 4. Use default if all else fails
            if (loadedBalance === null || isNaN(loadedBalance) || loadedBalance < 0) {
                loadedBalance = this.config.defaultDemoBalance;
                source = 'default';
            }

            this.currentBalance = loadedBalance;
            this.isDemo = true;

            // Always sync to localStorage for consistency
            this.saveToLocalStorage(loadedBalance);

            console.log(`🎮 Demo balance loaded: ${loadedBalance} GEM (source: ${source})`);
            
            // Auto-save to server for cross-session persistence
            this.saveToServer();

        } catch (error) {
            console.error('❌ Demo balance load failed:', error);
            this.currentBalance = this.config.defaultDemoBalance;
            this.saveToLocalStorage(this.currentBalance);
        }
    }

    async restoreFromServer() {
        try {
            const response = await fetch('/api/gaming/roulette/sync_balance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    action: 'restore'
                })
            });

            const data = await response.json();
            
            if (data.status === 'success' && data.data) {
                return parseFloat(data.data.balance);
            }
        } catch (error) {
            console.warn('⚠️ Server balance restoration failed:', error);
        }
        return null;
    }

    async updateBalance(newBalance, source = 'manual') {
        try {
            // Validate input
            const validBalance = Math.max(0, parseFloat(newBalance) || 0);
            
            if (validBalance === this.currentBalance) {
                // Even if balance is same, update sync time to prevent stale state detection
                this.lastSyncTime = Date.now();
                return; // No change needed
            }

            const oldBalance = this.currentBalance;
            
            // CRITICAL FIX: Update balance immediately and synchronously
            this.currentBalance = validBalance;
            this.lastSyncTime = Date.now(); // Mark as fresh

            // Save to appropriate storage IMMEDIATELY
            if (this.isDemo) {
                this.saveToLocalStorage(validBalance);
                // Save to server in background
                this.saveToServer();
            } else {
                // For authenticated users, save to server
                await this.saveAuthenticatedBalance(validBalance);
            }

            // Notify all listeners AFTER balance is fully updated
            this.notifyBalanceChange('updated', null, oldBalance, source);

            console.log(`💰 Balance updated: ${oldBalance} → ${validBalance} GEM (${source})`);

        } catch (error) {
            console.error('❌ Balance update failed:', error);
            this.notifyBalanceChange('error', error.message, null, 'update-error');
        }
    }

    saveToLocalStorage(balance) {
        try {
            localStorage.setItem(this.config.storageKeys.demoBalance, balance.toString());
            localStorage.setItem(this.config.storageKeys.balanceTimestamp, Date.now().toString());
        } catch (error) {
            console.warn('⚠️ Failed to save to localStorage:', error);
        }
    }

    async saveToServer() {
        if (!this.isDemo || this.syncInProgress) return;
        
        try {
            this.syncInProgress = true;
            
            const response = await fetch('/api/gaming/roulette/sync_balance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    action: 'save',
                    frontend_balance: this.currentBalance
                })
            });

            const data = await response.json();
            
            if (data.status === 'success') {
                this.lastSyncTime = Date.now();
                console.log('💾 Demo balance synced to server successfully');
            } else {
                console.warn('⚠️ Server sync failed:', data.message);
            }
        } catch (error) {
            console.warn('⚠️ Server sync error:', error);
        } finally {
            this.syncInProgress = false;
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
        const event = {
            type: type, // 'updated', 'error', 'loaded', 'refreshed'
            balance: this.currentBalance,
            oldBalance: oldBalance,
            isDemo: this.isDemo,
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
        window.dispatchEvent(new CustomEvent('balanceUpdated', {
            detail: {
                balance: this.currentBalance,
                source: event.source,
                isDemo: this.isDemo,
                type: type
            }
        }));
    }

    setupEventListeners() {
        // Listen for auth status changes
        window.addEventListener('authStatusChanged', (event) => {
            console.log('🔄 Auth status changed, reloading balance...');
            this.detectAuthStatus().then(() => this.loadBalance());
        });

        // Listen for storage events (cross-tab sync)
        window.addEventListener('storage', (event) => {
            if (event.key === this.config.storageKeys.demoBalance && event.newValue) {
                try {
                    const newBalance = parseFloat(event.newValue);
                    if (!isNaN(newBalance) && newBalance !== this.currentBalance) {
                        console.log('🔄 Cross-tab balance sync detected');
                        this.currentBalance = newBalance;
                        this.notifyBalanceChange('updated');
                    }
                } catch (error) {
                    console.warn('⚠️ Cross-tab sync error:', error);
                }
            }
        });

        // Page visibility change handling
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                console.log('🔄 Page became visible, syncing balance...');
                this.loadBalance();
            }
        });
    }

    startAutoSave() {
        if (this.autoSaveTimer) clearInterval(this.autoSaveTimer);
        
        this.autoSaveTimer = setInterval(() => {
            if (this.isDemo) {
                this.saveToServer();
            }
        }, this.config.autoSaveInterval);
    }

    startHeartbeat() {
        if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
        
        this.heartbeatTimer = setInterval(() => {
            // Periodic balance refresh to catch external changes
            this.loadBalance();
        }, this.config.heartbeatInterval);
    }

    // Utility methods
    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    // Public API
    getBalance() {
        // PERFORMANCE FIX: Smart rate limiting to prevent refresh loops
        const now = Date.now();
        
        // Reset refresh attempts if cooldown period has passed
        if (now - this.lastForceRefresh > this.config.cooldownResetTime) {
            this.refreshAttempts = 0;
            this.refreshCooldownActive = false;
        }
        
        // Only check for stale state if not in cooldown and haven't exceeded attempts
        if (!this.refreshCooldownActive && 
            this.refreshAttempts < this.config.maxRefreshAttempts &&
            now - this.lastStaleCheck > this.config.refreshCooldown) {
            
            this.lastStaleCheck = now;
            
            if (this.syncInProgress || this.hasStaleState()) {
                console.warn('⚠️ Stale balance detected, refreshing... (attempt ' + (this.refreshAttempts + 1) + ')');
                this.forceBalanceRefresh();
            }
        }
        
        return this.currentBalance;
    }
    
    hasStaleState() {
        // PERFORMANCE FIX: More reasonable stale detection threshold
        const timeSinceLastSync = Date.now() - (this.lastSyncTime || 0);
        return timeSinceLastSync > this.config.staleThreshold; // 30 seconds threshold (was 5 seconds)
    }
    
    forceBalanceRefresh() {
        // PERFORMANCE FIX: Implement refresh rate limiting
        const now = Date.now();
        
        // Increment refresh attempts and update cooldown state
        this.refreshAttempts++;
        this.lastForceRefresh = now;
        
        // Enter cooldown if we've reached max attempts
        if (this.refreshAttempts >= this.config.maxRefreshAttempts) {
            this.refreshCooldownActive = true;
            console.warn('🚫 Balance refresh cooldown activated (too many attempts)');
        }
        
        // Synchronous balance validation - don't return stale values
        const localBalance = parseFloat(localStorage.getItem(this.config.storageKeys.demoBalance));
        if (!isNaN(localBalance) && localBalance !== this.currentBalance) {
            console.log('🔄 Force refreshing balance from localStorage:', localBalance);
            const oldBalance = this.currentBalance;
            this.currentBalance = localBalance;
            this.lastSyncTime = now; // Update sync time
            this.notifyBalanceChange('refreshed', null, oldBalance, 'force-refresh');
        } else {
            // Even if no change, update sync time to prevent repeated stale detections
            this.lastSyncTime = now;
        }
    }

    isInDemoMode() {
        return this.isDemo;
    }

    isUserAuthenticated() {
        return this.isAuthenticated;
    }

    async refresh() {
        console.log('🔄 Manual balance refresh requested');
        await this.detectAuthStatus();
        await this.loadBalance();
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

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.balanceManager = new UnifiedBalanceManager();
    });
} else {
    // DOM already ready
    window.balanceManager = new UnifiedBalanceManager();
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UnifiedBalanceManager;
}