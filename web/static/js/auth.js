/**
 * Authentication Module for CryptoChecker v3
 */

window.Auth = {
    currentUser: null,
    isAuthenticated: false,
    authModal: null,

    // Initialize authentication
    init() {
        this.setupEventListeners();
        this.checkAuthStatus();
    },

    // Set up event listeners
    setupEventListeners() {
        // Login form submission
        document.getElementById('loginForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        // Register form submission
        document.getElementById('registerForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleRegister();
        });

        // Toggle between login and register
        document.getElementById('toggleAuthForm')?.addEventListener('click', () => {
            this.toggleAuthForms();
        });

        // Initialize modal
        const modalElement = document.getElementById('authModal');
        if (modalElement) {
            this.authModal = new bootstrap.Modal(modalElement);
        }
    },

    // Check current authentication status
    async checkAuthStatus() {
        try {
            // First check if we have a valid stored token
            const storedToken = this.getStoredToken();
            if (!storedToken) {
                console.log('No valid auth token found, setting guest mode');
                this.handleUnauthenticated();
                return;
            }

            // Validate token with server
            const response = await App.api.get('/auth/status');

            if (response.authenticated && response.user) {
                console.log('User authenticated successfully:', response.user.username);
                this.currentUser = response.user;
                this.isAuthenticated = true;
                this.updateUserInterface();
            } else {
                console.log('Token validation failed, clearing stored token');
                this.clearStoredToken();
                this.currentUser = response.guest_user;
                this.isAuthenticated = false;
                this.updateUserInterface();
            }

            // Update global app state
            App.user = this.currentUser;
            App.isAuthenticated = this.isAuthenticated;
            App.isGuest = !this.isAuthenticated;

        } catch (error) {
            console.warn('Auth status check failed:', error);
            // If the token is invalid, remove it
            if (error.message.includes('401') || error.message.includes('Unauthorized')) {
                console.log('Removing invalid auth token');
                this.clearStoredToken();
            }
            this.handleUnauthenticated();
        }
    },

    // Handle login form submission
    async handleLogin() {
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;

        try {
            this.showAuthLoading(true);

            // Store guest balance before login for potential migration
            const guestBalance = App.user?.wallet_balance || 5000;
            const hasPlayedAsGuest = guestBalance !== 5000; // Check if guest has played games

            const response = await App.api.post('/auth/login', {
                username,
                password
            });

            // Store token with expiration
            this.storeAuthToken(response.access_token, response.expires_in);

            // Update state immediately
            this.currentUser = response.user;
            this.isAuthenticated = true;

            // Update global app state
            App.user = this.currentUser;
            App.isAuthenticated = this.isAuthenticated;
            App.isGuest = false;

            console.log('🎉 Login successful, updating UI...', {
                currentUser: this.currentUser,
                isAuthenticated: this.isAuthenticated,
                username: this.currentUser.username
            });

            // Force UI update immediately
            this.updateUserInterface();

            // Close modal after short delay to ensure UI update completes
            setTimeout(() => {
                this.authModal.hide();
                console.log('✅ Modal hidden after login');
            }, 100);

            // Show appropriate welcome message
            if (hasPlayedAsGuest) {
                console.log(`Guest balance was ${guestBalance}, user balance is ${response.user.wallet_balance}`);
                setTimeout(() => {
                    App.showAlert('info', `Welcome back! Your authenticated account balance is ${this.formatBalance(response.user.wallet_balance)} GEM.`);
                }, 500);
            } else {
                setTimeout(() => {
                    App.showAlert('success', `Welcome back, ${response.user.username}!`);
                }, 500);
            }

        } catch (error) {
            App.showAlert('danger', error.message || 'Login failed');
        } finally {
            this.showAuthLoading(false);
        }
    },

    // Handle register form submission
    async handleRegister() {
        const username = document.getElementById('registerUsername').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        const confirmPassword = document.getElementById('registerConfirmPassword').value;

        // Validate passwords match
        if (password !== confirmPassword) {
            App.showAlert('danger', 'Passwords do not match');
            return;
        }

        try {
            this.showAuthLoading(true);

            // Store guest balance before registration
            const guestBalance = App.user?.wallet_balance || 5000;
            const hasPlayedAsGuest = guestBalance !== 5000;

            const response = await App.api.post('/auth/register', {
                username,
                email,
                password
            });

            // Store token with expiration
            await this.storeAuthToken(response.access_token, response.expires_in);

            // Set secure session cookie
            document.cookie = `auth_token=${response.access_token}; path=/; max-age=${response.expires_in}; SameSite=Strict`;

            // Update state
            this.currentUser = response.user;
            this.isAuthenticated = true;

            // Verify session is active
            const sessionCheck = await fetch('/api/auth/check', {
                credentials: 'include'
            });
            
            if (!sessionCheck.ok) {
                throw new Error('Session verification failed');
            }

            // Update global app state
            App.user = this.currentUser;
            App.isAuthenticated = this.isAuthenticated;
            App.isGuest = false;

            // Close modal and update UI
            this.authModal.hide();
            this.updateUserInterface();

            // Show appropriate welcome message
            if (hasPlayedAsGuest) {
                App.showAlert('success', `Welcome to CryptoChecker, ${response.user.username}! Your account starts with ${this.formatBalance(response.user.wallet_balance)} GEM.`);
            } else {
                App.showAlert('success', `Welcome to CryptoChecker, ${response.user.username}!`);
            }

        } catch (error) {
            App.showAlert('danger', error.message || 'Registration failed');
        } finally {
            this.showAuthLoading(false);
        }
    },

    // Logout user
    async logout() {
        try {
            await App.api.post('/auth/logout');
        } catch (error) {
            console.warn('Logout API call failed:', error);
        } finally {
            // Clear stored tokens
            this.clearStoredToken();

            // Reset state
            this.handleUnauthenticated();

            App.showAlert('info', 'You have been logged out');
        }
    },

    // Handle unauthenticated state
    async handleUnauthenticated() {
        this.currentUser = null;
        this.isAuthenticated = false;

        try {
            // Get guest mode data from server to ensure consistency
            const guestResponse = await App.api.get('/auth/guest');
            const guestUser = guestResponse.guest_user;

            // Set guest mode with server-provided data
            App.user = {
                id: guestUser.id || 'guest',
                username: guestUser.username || 'Guest',
                wallet_balance: guestUser.wallet_balance || 5000,
                is_guest: true
            };
        } catch (error) {
            console.warn('Failed to get guest data from server, using fallback:', error);
            // Fallback to default guest data
            App.user = {
                id: 'guest',
                username: 'Guest',
                wallet_balance: 5000,
                is_guest: true
            };
        }

        App.isAuthenticated = false;
        App.isGuest = true;

        this.updateUserInterface();
    },

    // Update user interface based on auth state
    updateUserInterface() {
        const userInfo = document.getElementById('user-info');
        if (!userInfo) {
            console.warn('❌ user-info element not found in DOM');
            return;
        }

        console.log('🔄 Updating user interface:', {
            isAuthenticated: this.isAuthenticated,
            currentUser: this.currentUser?.username,
            appUser: App.user?.username,
            walletBalance: this.currentUser?.wallet_balance || App.user?.wallet_balance
        });

        if (this.isAuthenticated && this.currentUser) {
            // Authenticated user UI - always replace the entire content
            userInfo.innerHTML = `
                <div class="d-flex align-items-center gap-3">
                    <div class="text-end">
                        <div class="fw-bold text-light">${this.currentUser.username}</div>
                        <div class="small text-light-emphasis">
                            <i class="bi bi-gem"></i> ${this.formatBalance(this.currentUser.wallet_balance)} GEM
                        </div>
                    </div>
                    <div class="dropdown">
                        <button class="btn btn-outline-light btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown">
                            <i class="bi bi-person-circle"></i>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="/portfolio">
                                <i class="bi bi-wallet2"></i> Portfolio
                            </a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><button class="dropdown-item" onclick="Auth.logout()">
                                <i class="bi bi-box-arrow-right"></i> Logout
                            </button></li>
                        </ul>
                    </div>
                </div>
            `;
            console.log(`✅ Updated navbar for user: ${this.currentUser.username}, balance: ${this.currentUser.wallet_balance} GEM`);
        } else {
            // Guest mode UI - always replace the entire content
            const guestBalance = App.user?.wallet_balance || 5000;
            userInfo.innerHTML = `
                <div class="d-flex align-items-center gap-3">
                    <div class="text-end">
                        <div class="fw-bold text-light">Guest Mode</div>
                        <div class="small text-light-emphasis">
                            <i class="bi bi-gem"></i> ${this.formatBalance(guestBalance)} GEM (temp)
                        </div>
                    </div>
                    <button class="btn btn-primary btn-sm" onclick="Auth.showLoginModal()">
                        <i class="bi bi-person-plus"></i> Sign In
                    </button>
                </div>
            `;
            console.log(`✅ Updated navbar for guest mode: ${guestBalance} GEM`);
        }

        // Update balance displays throughout the app
        this.updateBalanceDisplays();

        // Dispatch balance update event
        document.dispatchEvent(new CustomEvent('balanceUpdated', {
            detail: {
                balance: this.currentUser?.wallet_balance || App.user?.wallet_balance || 5000,
                isGuest: !this.isAuthenticated
            }
        }));
    },

    // Update balance displays
    updateBalanceDisplays() {
        const balance = this.currentUser?.wallet_balance || App.user?.wallet_balance || 5000;
        const balanceUsd = (balance * 0.01).toFixed(2);

        App.updateElement('user-balance', this.formatBalance(balance) + ' GEM');
        App.updateElement('balance-usd', balanceUsd);
    },

    // Format balance for display
    formatBalance(balance) {
        return new Intl.NumberFormat('en-US').format(balance);
    },

    // Show login modal
    showLoginModal() {
        console.log('🔑 Auth.showLoginModal called');

        // Try to initialize modal if not already done (handles timing issues)
        if (!this.authModal) {
            const modalElement = document.getElementById('authModal');
            if (modalElement) {
                console.log('🔧 Initializing Bootstrap modal...');
                // Initialize modal and set up event listeners if not already done
                this.authModal = new bootstrap.Modal(modalElement);
                this.setupEventListeners();
            } else {
                console.error('❌ Auth modal element not found in DOM');
                return;
            }
        }

        if (this.authModal) {
            console.log('📍 Showing login form and auth modal');
            this.showLoginForm();
            this.authModal.show();
        } else {
            console.error('❌ Failed to initialize auth modal');
        }
    },

    // Show registration modal
    showRegisterModal() {
        if (this.authModal) {
            this.showRegisterForm();
            this.authModal.show();
        }
    },

    // Toggle between login and register forms
    toggleAuthForms() {
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');
        const title = document.getElementById('authModalTitle');
        const toggleText = document.getElementById('toggleAuthText');

        if (loginForm.style.display === 'none') {
            // Switch to login
            this.showLoginForm();
        } else {
            // Switch to register
            this.showRegisterForm();
        }
    },

    // Show login form
    showLoginForm() {
        document.getElementById('loginForm').style.display = 'block';
        document.getElementById('registerForm').style.display = 'none';
        document.getElementById('authModalTitle').textContent = 'Sign In';
        document.getElementById('toggleAuthText').textContent = "Don't have an account? Sign up";

        // Clear forms
        this.clearAuthForms();
    },

    // Show register form
    showRegisterForm() {
        document.getElementById('loginForm').style.display = 'none';
        document.getElementById('registerForm').style.display = 'block';
        document.getElementById('authModalTitle').textContent = 'Create Account';
        document.getElementById('toggleAuthText').textContent = 'Already have an account? Sign in';

        // Clear forms
        this.clearAuthForms();
    },

    // Clear authentication forms
    clearAuthForms() {
        const forms = ['loginForm', 'registerForm'];
        forms.forEach(formId => {
            const form = document.getElementById(formId);
            if (form) {
                form.reset();
            }
        });
    },

    // Show loading state in auth forms
    showAuthLoading(isLoading) {
        const loginBtn = document.querySelector('#loginForm button[type="submit"]');
        const registerBtn = document.querySelector('#registerForm button[type="submit"]');

        if (isLoading) {
            if (loginBtn) {
                loginBtn.disabled = true;
                loginBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Signing In...';
            }
            if (registerBtn) {
                registerBtn.disabled = true;
                registerBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Creating Account...';
            }
        } else {
            if (loginBtn) {
                loginBtn.disabled = false;
                loginBtn.innerHTML = '<i class="bi bi-box-arrow-in-right"></i> Sign In';
            }
            if (registerBtn) {
                registerBtn.disabled = false;
                registerBtn.innerHTML = '<i class="bi bi-person-plus"></i> Create Account';
            }
        }
    },

    // Check if user is authenticated
    isUserAuthenticated() {
        return this.isAuthenticated;
    },

    // Get current user
    getCurrentUser() {
        return this.currentUser;
    },

    // Require authentication (redirect to login if not authenticated)
    requireAuth() {
        if (!this.isAuthenticated) {
            this.showLoginModal();
            return false;
        }
        return true;
    },

    // Token management utilities
    storeAuthToken(token, expiresIn) {
        const expirationTime = Date.now() + (expiresIn * 1000); // Convert seconds to milliseconds
        const tokenData = {
            token: token,
            expires: expirationTime
        };
        localStorage.setItem('auth_token', token);
        localStorage.setItem('auth_token_data', JSON.stringify(tokenData));
        console.log('Auth token stored with expiration:', new Date(expirationTime));
    },

    getStoredToken() {
        try {
            const token = localStorage.getItem('auth_token');
            const tokenDataStr = localStorage.getItem('auth_token_data');

            if (!token || !tokenDataStr) {
                return null;
            }

            const tokenData = JSON.parse(tokenDataStr);

            // Check if token is expired
            if (Date.now() >= tokenData.expires) {
                console.log('Stored auth token has expired');
                this.clearStoredToken();
                return null;
            }

            return token;
        } catch (error) {
            console.warn('Error reading stored token:', error);
            this.clearStoredToken();
            return null;
        }
    },

    clearStoredToken() {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_token_data');
        console.log('Auth token cleared from storage');
    },

    // Enhanced authentication check with auto-refresh
    async validateAndRefreshToken() {
        const token = this.getStoredToken();
        if (!token) {
            return false;
        }

        try {
            // Try to use the current token
            const response = await App.api.get('/auth/status');
            return response.authenticated;
        } catch (error) {
            // If token is invalid, clear it
            if (error.message.includes('401') || error.message.includes('Unauthorized')) {
                console.log('Token validation failed, clearing stored token');
                this.clearStoredToken();
            }
            return false;
        }
    },

    // Refresh user balance from server
    async refreshBalance() {
        try {
            const response = await App.api.get('/auth/status');

            if (response.authenticated && response.user) {
                // Update authenticated user balance
                this.currentUser = response.user;
                App.user = this.currentUser;
                this.updateUserInterface();
                console.log(`Balance refreshed: ${response.user.wallet_balance} GEM`);
            } else if (response.guest_mode && response.guest_user) {
                // Update guest mode balance
                App.user = {
                    ...response.guest_user,
                    is_guest: true
                };
                this.updateUserInterface();
                console.log(`Guest balance refreshed: ${response.guest_user.wallet_balance} GEM`);
            }

            return true;
        } catch (error) {
            console.warn('Failed to refresh balance:', error);
            return false;
        }
    },

    // Set guest mode manually (for button clicks)
    setGuestMode() {
        console.log('Setting guest mode manually');
        this.clearStoredToken(); // Ensure no tokens are lingering
        this.handleUnauthenticated();
    },

    // Handle guest login (legacy method for templates)
    async handleGuestLogin() {
        console.log('Handle guest login called');
        this.setGuestMode();
    },

    // Periodically refresh balance (useful for gaming sessions)
    startBalanceRefresh(intervalMs = 30000) {
        if (this.balanceRefreshInterval) {
            clearInterval(this.balanceRefreshInterval);
        }

        this.balanceRefreshInterval = setInterval(async () => {
            if (this.isAuthenticated) {
                await this.refreshBalance();
            }
        }, intervalMs);
    },

    stopBalanceRefresh() {
        if (this.balanceRefreshInterval) {
            clearInterval(this.balanceRefreshInterval);
            this.balanceRefreshInterval = null;
        }
    },

    // Global balance refresh function (can be called from anywhere)
    async refreshBalanceGlobally() {
        try {
            console.log('🔄 Starting global balance refresh...');
            const response = await App.api.get('/auth/status');
            console.log('📡 Auth status response:', response);

            if (response.authenticated && response.user) {
                const oldBalance = this.currentUser?.wallet_balance || 'unknown';
                // Update authenticated user balance
                this.currentUser = response.user;
                App.user = this.currentUser;
                this.updateUserInterface();
                console.log(`✅ Global balance refresh: ${oldBalance} → ${response.user.wallet_balance} GEM`);
                return response.user.wallet_balance;
            } else if (response.guest_mode && response.guest_user) {
                const oldBalance = App.user?.wallet_balance || 'unknown';
                // Update guest mode balance
                App.user = {
                    ...response.guest_user,
                    is_guest: true
                };
                this.updateUserInterface();
                console.log(`✅ Global guest balance refresh: ${oldBalance} → ${response.guest_user.wallet_balance} GEM`);
                return response.guest_user.wallet_balance;
            }

            console.warn('⚠️ No user data in auth status response');
            return null;
        } catch (error) {
            console.error('❌ Failed to refresh global balance:', error);
            return null;
        }
    }
};

// Global utility function to trigger balance updates from anywhere
window.updateBalanceGlobally = async function() {
    if (window.Auth && typeof window.Auth.refreshBalanceGlobally === 'function') {
        return await window.Auth.refreshBalanceGlobally();
    }
    return null;
};

// Direct balance update function for immediate UI updates
window.updateNavbarBalance = function(newBalance) {
    console.log('💎 Direct navbar balance update:', newBalance);

    // Find all balance displays in the navbar
    const balanceElements = document.querySelectorAll('#user-info .small.text-light-emphasis');

    balanceElements.forEach(element => {
        if (newBalance !== null && newBalance !== undefined) {
            element.innerHTML = `<i class="bi bi-gem"></i> ${window.Auth?.formatBalance(newBalance) || newBalance.toLocaleString()} GEM`;
            console.log('✅ Updated navbar balance element:', element);
        }
    });

    return balanceElements.length;
};

// Gaming system balance sync
window.syncGamingBalance = function() {
    console.log('🎮 Syncing gaming balance...');

    // Update gaming page balance displays
    const gamingBalanceElements = [
        document.getElementById('gaming-balance'),
        document.getElementById('available-balance')
    ];

    const currentBalance = window.Auth?.currentUser?.wallet_balance || window.App?.user?.wallet_balance || 5000;

    gamingBalanceElements.forEach(element => {
        if (element) {
            const text = element.textContent || element.innerText || '';
            if (text.includes('Loading') || text.includes('0') || text.includes('5,000')) {
                element.textContent = window.Auth?.formatBalance(currentBalance) || currentBalance.toLocaleString();
                console.log('✅ Updated gaming balance display:', element);
            }
        }
    });

    return currentBalance;
};

// Test function to manually trigger balance updates (for debugging)
window.testBalanceUpdate = async function() {
    console.log('🧪 Testing balance update...');
    console.log('Auth.isAuthenticated:', window.Auth?.isAuthenticated);
    console.log('Auth.currentUser:', window.Auth?.currentUser);
    console.log('App.user:', window.App?.user);

    const result = await window.updateBalanceGlobally();
    console.log('🧪 Test result:', result);
    return result;
};

// Balance animation state and controls
Auth.animateNavbarBalance = function(change, isPositive) {
    console.log(`🎨 Animating navbar balance: ${change > 0 ? '+' : ''}${change} GEM`);

    // Find the balance element in navbar
    const navbarBalanceElements = document.querySelectorAll('#user-info .small.text-light-emphasis');

    navbarBalanceElements.forEach(element => {
        if (element.innerHTML.includes('GEM')) {
            // Skip animation for very small changes
            if (Math.abs(change) < 10) return;

            // Flash color animation
            element.style.transition = 'none';
            if (isPositive) {
                // Green flash for wins
                element.style.color = '#10b981';
                element.style.textShadow = '0 0 10px rgba(16, 185, 129, 0.5)';
            } else {
                // Red flash for losses
                element.style.color = '#ef4444';
                element.style.textShadow = '0 0 10px rgba(239, 68, 68, 0.5)';
            }

            // Remove flash after short delay
            setTimeout(() => {
                element.style.transition = 'color 0.5s ease, text-shadow 0.5s ease';
                element.style.color = '';
                element.style.textShadow = '';
            }, 300);
        }
    });

    // Update balance displays throughout the app
    setTimeout(() => {
        Auth.updateBalanceDisplays();
    }, 100);
};

// Force update of gaming page balance displays
Auth.updateGamingBalanceDisplays = function(newBalance) {
    console.log('🎮 Updating gaming page balance displays:', newBalance);

    // Update all gaming page balance elements
    const gamingElements = [
        document.getElementById('gaming-balance'),
        document.getElementById('available-balance'),
        document.getElementById('walletBalance')
    ];

    const displayBalance = newBalance || this.currentUser?.wallet_balance || window.App?.user?.wallet_balance || 5000;

    gamingElements.forEach(element => {
        if (element) {
            element.textContent = this.formatBalance(displayBalance) + (element.id === 'walletBalance' ? ' GEM' : '');
            console.log(`✅ Updated ${element.id}: ${displayBalance} GEM`);
        }
    });
};

// Initialize authentication when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    Auth.init();

    // Listen for global balance update events
    document.addEventListener('balanceUpdateRequested', async () => {
        await Auth.refreshBalanceGlobally();
    });

    // Listen for roulette balance change events and animate navbar
    document.addEventListener('balanceUpdated', async (event) => {
        const { detail } = event;
        if (!detail) return;

        const change = detail.change;
        const isPositive = change > 0;
        const isFromRoulette = detail.source === 'roulette';
        const isSignificantChange = Math.abs(change) >= 10;

        // Only animate for significant roulette changes
        if (isFromRoulette && isSignificantChange) {
            Auth.animateNavbarBalance(change, isPositive);

            // Also ensure gaming page displays are updated
            if (detail.balance) {
                Auth.updateGamingBalanceDisplays(detail.balance);
            }
        }

        // Update navbar balance display
        setTimeout(() => {
            Auth.updateUserInterface();
        }, 350); // Delay to allow animation to complete
    });

    // Listen for clicker game events
    document.addEventListener('clickerRewardEarned', async (event) => {
        const newBalance = event.detail?.newBalance;
        if (newBalance) {
            console.log(`Clicker reward earned: ${newBalance} GEM`);
            await Auth.refreshBalanceGlobally();
        }
    });
});
