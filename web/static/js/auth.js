// Simple Authentication System for Demo
class AuthManager {
    constructor() {
        this.user = null;
        this.isLoggedIn = false;
        this.balanceTimer = null;
        this.balancePollMs = 30000; // 30s polling to prevent desync
        this.userBalance = 5000; // Demo balance
        this.init();
    }

    init() {
        // Check if user is already logged in
        this.checkAuthStatus();
        
        // Setup event listeners
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Use event delegation for dynamically created buttons
        document.addEventListener('click', (e) => {
            // Demo login button
            const demoBtn = e.target.closest('#demo-login-btn');
            if (demoBtn) {
                e.preventDefault();
                console.log('Demo login button clicked');
                this.demoLogin();
                return;
            }

            // Strict logout click handling only for explicit logout controls
            const logoutEl = e.target.closest('#logout-btn, a[data-action="logout"], button[data-action="logout"]');
            if (logoutEl) {
                e.preventDefault();
                console.log('Logout button clicked');
                this.logout();
                return;
            }
        });
        
        // Also listen for logout function calls from navbar
        window.logout = () => {
            console.log('Global logout function called');
            this.logout();
        };

        // Keep wallet balance in sync when tab regains focus
        window.addEventListener('focus', () => {
            try {
                if (this.isAuthenticated()) {
                    this.loadWalletBalance();
                }
            } catch (err) {
                console.debug('Focus sync skipped:', err);
            }
        });

        // Also react to visibility changes (e.g., switching tabs)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.isAuthenticated()) {
                this.loadWalletBalance();
            }
        });
    }

    async demoLogin() {
        try {
            console.log('Starting demo login...');
            
            // REAL API CALL - Now that backend is ready!
            const response = await fetch('/api/auth/demo-login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();
            console.log('Demo login response:', data);
            
            if (data.status === 'success') {
                this.user = data.user;
                this.isLoggedIn = true;
                
                // Store user data for persistence  
                localStorage.setItem('demo_user', JSON.stringify(data.user));
                localStorage.setItem('is_logged_in', 'true');
                
                // Initialize demo balance in balance manager
                if (data.user && data.user.gem_coins && window.balanceManager) {
                    window.balanceManager.updateBalance(data.user.gem_coins, 'demo_login');
                }
                
                // Trigger auth status change event for balance manager
                window.dispatchEvent(new CustomEvent('authStatusChanged', {
                    detail: { authenticated: true, demo: true, user: data.user }
                }));
                
                this.updateUI();
                this.showAlert('Demo login successful! Welcome to CryptoChecker.', 'success');
                
                // Trigger dashboard reload if we're on the home page
                if (window.location.pathname === '/' || window.location.pathname === '/dashboard') {
                    if (window.checkAuthenticationAndInitialize) {
                        window.checkAuthenticationAndInitialize();
                    }
                }

                // Start balance polling after successful login
                this.startBalancePolling();
                
                return { success: true, user: data.user };
            } else {
                this.showAlert('Login failed: ' + data.message, 'error');
                return { success: false, error: data.message };
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showAlert('Login failed. Please try again.', 'error');
            return { success: false, error: error.message };
        }
    }

    async logout() {
        try {
            console.log('Logging out...');
            
            // REAL API LOGOUT - Now that backend is ready!
            const response = await fetch('/api/auth/logout', {
                method: 'GET',  // Using GET as defined in the backend
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();
            
            if (data.status === 'success') {
                this.user = null;
                this.isLoggedIn = false;
                
                // Clear local storage
                localStorage.removeItem('demo_user');
                localStorage.removeItem('is_logged_in');
                
            this.updateUI();
            this.showAlert('Logged out successfully.', 'info');
            
            // Redirect to home if on protected page
            if (window.location.pathname !== '/' && window.location.pathname !== '/login' && window.location.pathname !== '/register') {
                window.location.href = '/';
            }
            
            // Trigger page reload for guest view
            if (window.location.pathname === '/' || window.location.pathname === '/dashboard') {
                if (window.checkAuthenticationAndInitialize) {
                    window.checkAuthenticationAndInitialize();
                }
            }

            // Stop polling on logout
            this.stopBalancePolling();
        }
    } catch (error) {
            console.error('Logout error:', error);
            // Fallback logout
            this.user = null;
            this.isLoggedIn = false;
            localStorage.removeItem('demo_user');
            localStorage.removeItem('is_logged_in');
            this.updateUI();
            this.showAlert('Logged out.', 'info');
        }
    }

    async checkAuthStatus() {
        try {
            console.log('Checking auth status...');
            
            // REAL API AUTH CHECK - Now that backend is ready!
            const response = await fetch('/api/auth/me');
            if (response.ok) {
                const data = await response.json();
                console.log('Auth status response:', data);
                if (data.status === 'success' && data.user) {
                    this.user = data.user;
                    this.isLoggedIn = true;
                    console.log('✅ User is authenticated:', this.user);
                    this.updateUI();
                    return;
                } else {
                    console.log('❌ User not authenticated from API');
                }
            } else {
                console.log('❌ Auth check failed with status:', response.status);
            }
            
            // Fallback to localStorage if API fails
            const isLoggedIn = localStorage.getItem('is_logged_in');
            const userData = localStorage.getItem('demo_user');
            
            if (isLoggedIn === 'true' && userData) {
                this.user = JSON.parse(userData);
                this.isLoggedIn = true;
                console.log('✅ User is authenticated (localStorage fallback):', this.user);
                this.updateUI();
                return;
            }
            
            console.log('❌ User not authenticated');
        } catch (error) {
            // User not logged in, which is fine
            console.log('❌ User not authenticated - error:', error);
            
            // Try localStorage fallback
            const isLoggedIn = localStorage.getItem('is_logged_in');
            const userData = localStorage.getItem('demo_user');
            
            if (isLoggedIn === 'true' && userData) {
                this.user = JSON.parse(userData);
                this.isLoggedIn = true;
                console.log('✅ User is authenticated (localStorage fallback):', this.user);
                this.updateUI();
            }
        }
    }

    updateUI() {
        // Update authentication buttons
        const authButtons = document.getElementById('auth-buttons');
        const userMenu = document.getElementById('user-menu');
        const walletDisplay = document.getElementById('wallet-display');
        
        if (this.isLoggedIn && this.user) {
            // Hide auth buttons, show user menu
            if (authButtons) {
                authButtons.style.display = 'none';
            }
            if (userMenu) {
                userMenu.style.display = 'block';
            }
            
            // Always try to load wallet balance; wallet pill is optional
            if (walletDisplay) {
                walletDisplay.style.display = 'flex';
            }
            this.loadWalletBalance();
            this.startBalancePolling();

            // Update username and avatar if available
            const usernameDisplay = document.getElementById('username-display');
            if (usernameDisplay && this.user && this.user.username) {
                usernameDisplay.textContent = this.user.username;
            }
            if (this.user && this.user.avatar_url) {
                const avatar = document.getElementById('userAvatar');
                if (avatar) avatar.src = this.user.avatar_url;
                document.querySelectorAll('#user-menu img').forEach(img => {
                    try { img.src = this.user.avatar_url; } catch(e) {}
                });
            }
            
            // Username display is already handled above
            
        } else {
            // Show auth buttons, hide user menu
            if (authButtons) {
                authButtons.style.display = 'block';
                authButtons.innerHTML = `
                    <button class="btn btn-outline-light me-2" id="demo-login-btn">
                        <i class="fas fa-sign-in-alt me-2"></i>Demo Login
                    </button>
                    <a href="/login" class="btn btn-primary" style="border-radius: 20px; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); border: none;">
                        <i class="fas fa-user-plus me-2"></i>Sign Up
                    </a>
                `;
            }
            if (userMenu) {
                userMenu.style.display = 'none';
            }
            
            // Hide wallet display
            if (walletDisplay) {
                walletDisplay.style.display = 'none';
            }

            // Stop polling when not authenticated
            this.stopBalancePolling();
        }
    }

    async loadWalletBalance() {
        try {
            const response = await fetch('/api/trading/gamification/wallet');
            if (response.ok) {
                const data = await response.json();
                if (data.status === 'success' && data.data && data.data.gem_coins !== undefined) {
                    const balance = data.data.gem_coins;
                    // Ensure balance is a number
                    const safeBalance = typeof balance === 'number' ? balance : 5000;
                    
                    const balanceElement = document.getElementById('nav-gem-balance');
                    if (balanceElement) {
                        balanceElement.textContent = safeBalance.toLocaleString();
                    }
                    
                    // Also update wallet balance on roulette page
                    const walletBalanceElement = document.getElementById('walletBalance');
                    if (walletBalanceElement) {
                        walletBalanceElement.textContent = safeBalance.toLocaleString() + ' GEM';
                    }
                    
                    // Store balance for roulette game
                    this.userBalance = safeBalance;
                    return;
                }
            }
            
            // Fallback for demo - use consistent balance
            this.setFallbackBalance();
            
        } catch (error) {
            console.error('Failed to load wallet balance:', error);
            // Fallback for demo - use consistent balance
            this.setFallbackBalance();
        }
    }
    
    setFallbackBalance() {
        // ✅ FIXED: Get balance from balance manager instead of hardcoded value
        const balance = window.balanceManager ? window.balanceManager.getBalance() : 5000;
        this.userBalance = balance;
        
        // ✅ FIXED: Don't update UI elements directly - let balance manager handle it
        // The balance manager will notify all listeners including this component
        if (window.balanceManager) {
            window.balanceManager.updateBalance(balance, 'auth_fallback');
        } else {
            // Only update UI if balance manager isn't available (legacy fallback)
            const balanceElement = document.getElementById('nav-gem-balance');
            if (balanceElement) {
                balanceElement.textContent = balance.toLocaleString();
            }
            
            const walletBalanceElement = document.getElementById('walletBalance');
            if (walletBalanceElement) {
                walletBalanceElement.textContent = balance.toLocaleString() + ' GEM';
            }
        }
    }
    
    updateBalance(newBalance) {
        this.userBalance = newBalance;
        
        const balanceElement = document.getElementById('nav-gem-balance');
        if (balanceElement) {
            balanceElement.textContent = newBalance.toLocaleString();
        }
        
        const walletBalanceElement = document.getElementById('walletBalance');
        if (walletBalanceElement) {
            walletBalanceElement.textContent = newBalance.toLocaleString() + ' GEM';
        }
    }
    
    getBalance() {
        return this.userBalance;
    }

    showAlert(message, type = 'info') {
        // Use existing alert system if available
        if (window.showAlert) {
            window.showAlert(message, type);
        } else if (window.animationManager) {
            window.animationManager.animateNotification(message, type, 5000);
        } else {
            // Fallback to simple alert
            alert(message);
        }
    }

    isAuthenticated() {
        return this.isLoggedIn;
    }

    getUserData() {
        return this.user;
    }

    getUser() {
        return this.user;
    }

    startBalancePolling() {
        try {
            if (this.balanceTimer) return; // already polling
            this.balanceTimer = setInterval(() => {
                if (this.isAuthenticated()) {
                    this.loadWalletBalance();
                }
            }, this.balancePollMs);
        } catch (e) {
            console.debug('Balance polling not started:', e);
        }
    }

    stopBalancePolling() {
        if (this.balanceTimer) {
            clearInterval(this.balanceTimer);
            this.balanceTimer = null;
        }
    }
}

// Initialize auth manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.auth = new AuthManager();
});

// Export for use in other scripts
window.AuthManager = AuthManager;
