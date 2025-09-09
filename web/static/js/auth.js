/**
 * Authentication Management
 * Handles user authentication state and UI updates
 */

class AuthManager {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
        this.init();
    }

    init() {
        this.checkAuthState();
        this.updateUI();
        
        // Listen for storage changes (logout from other tabs)
        window.addEventListener('storage', (e) => {
            if (e.key === 'access_token' || e.key === 'user_data') {
                this.checkAuthState();
                this.updateUI();
            }
        });
    }

    checkAuthState() {
        const token = localStorage.getItem('access_token');
        const userData = localStorage.getItem('user_data');
        
        this.isAuthenticated = !!token;
        this.user = userData ? JSON.parse(userData) : null;
        
        // Update API client token
        if (window.apiClient) {
            window.apiClient.token = token;
            window.apiClient.refreshToken = localStorage.getItem('refresh_token');
        }
    }

    updateUI() {
        const userMenu = document.getElementById('userMenu');
        if (!userMenu) return;

        const authenticatedMenu = userMenu.querySelector('.user-authenticated');
        const guestMenu = userMenu.querySelector('.user-guest');

        if (this.isAuthenticated && this.user) {
            // Show authenticated user menu
            authenticatedMenu.classList.remove('d-none');
            guestMenu.classList.add('d-none');
            
            // Update user information
            this.updateUserDisplay();
            this.setupLogoutHandler();
        } else {
            // Show guest menu
            authenticatedMenu.classList.add('d-none');
            guestMenu.classList.remove('d-none');
        }
    }

    updateUserDisplay() {
        const userName = document.getElementById('userName');
        const userLevel = document.getElementById('userLevel');
        const userGems = document.getElementById('userGems');
        const userAvatar = document.getElementById('userAvatar');

        if (userName) {
            userName.textContent = this.user.display_name || this.user.username;
        }
        
        if (userLevel) {
            userLevel.textContent = this.user.current_level || 1;
        }
        
        if (userGems && this.user.wallet) {
            userGems.textContent = this.formatNumber(this.user.wallet.gem_coins || 0);
        }
        
        if (userAvatar && this.user.avatar_url) {
            userAvatar.src = this.user.avatar_url;
        }
    }

    setupLogoutHandler() {
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.onclick = (e) => {
                e.preventDefault();
                this.logout();
            };
        }
    }

    async logout() {
        try {
            // Call logout API
            if (window.apiClient) {
                await window.apiClient.auth.logout();
            }
        } catch (error) {
            console.error('Logout API call failed:', error);
        } finally {
            // Clear local storage regardless of API success
            this.clearAuthData();
            
            // Show success message
            if (window.showAlert) {
                showAlert('Logged out successfully', 'success');
            }
            
            // Redirect to login page
            setTimeout(() => {
                window.location.href = '/login';
            }, 1000);
        }
    }

    clearAuthData() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_data');
        
        this.user = null;
        this.isAuthenticated = false;
        
        if (window.apiClient) {
            window.apiClient.token = null;
            window.apiClient.refreshToken = null;
        }
    }

    async refreshUserData() {
        if (!this.isAuthenticated) return;
        
        try {
            const response = await window.apiClient.auth.getProfile();
            if (response.success) {
                this.user = response.data;
                localStorage.setItem('user_data', JSON.stringify(this.user));
                this.updateUserDisplay();
            }
        } catch (error) {
            console.error('Failed to refresh user data:', error);
        }
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    // Route protection
    requireAuth(redirectPath = '/login') {
        if (!this.isAuthenticated) {
            window.location.href = redirectPath;
            return false;
        }
        return true;
    }

    requireGuest(redirectPath = '/dashboard') {
        if (this.isAuthenticated) {
            window.location.href = redirectPath;
            return false;
        }
        return true;
    }

    hasRole(requiredRole) {
        if (!this.user) return false;
        
        const roleHierarchy = {
            'USER': 1,
            'MODERATOR': 2,
            'ADMIN': 3
        };
        
        const userRoleLevel = roleHierarchy[this.user.role] || 0;
        const requiredRoleLevel = roleHierarchy[requiredRole] || 0;
        
        return userRoleLevel >= requiredRoleLevel;
    }
}

// Initialize auth manager
document.addEventListener('DOMContentLoaded', function() {
    window.authManager = new AuthManager();
    
    // Auto-refresh user data every 5 minutes
    setInterval(() => {
        if (window.authManager.isAuthenticated) {
            window.authManager.refreshUserData();
        }
    }, 5 * 60 * 1000);
});

// Route-specific authentication checks
document.addEventListener('DOMContentLoaded', function() {
    const currentPath = window.location.pathname;
    
    // Pages that require authentication
    const protectedPaths = [
        '/dashboard',
        '/gaming',
        '/inventory',
        '/social',
        '/profile',
        '/settings',
        '/achievements'
    ];
    
    // Pages that require guest status (redirect if logged in)
    const guestOnlyPaths = [
        '/login',
        '/register'
    ];
    
    // Admin-only paths
    const adminPaths = [
        '/admin'
    ];
    
    // Wait for auth manager to initialize
    setTimeout(() => {
        if (!window.authManager) return;
        
        // Check protected routes
        if (protectedPaths.some(path => currentPath.startsWith(path))) {
            window.authManager.requireAuth();
        }
        
        // Check guest-only routes
        if (guestOnlyPaths.includes(currentPath)) {
            window.authManager.requireGuest();
        }
        
        // Check admin routes
        if (adminPaths.some(path => currentPath.startsWith(path))) {
            if (!window.authManager.requireAuth()) return;
            
            if (!window.authManager.hasRole('ADMIN')) {
                if (window.showAlert) {
                    showAlert('Access denied. Admin privileges required.', 'danger');
                }
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 2000);
            }
        }
    }, 100);
});

// Utility functions for authentication
window.auth = {
    isAuthenticated: () => window.authManager?.isAuthenticated || false,
    getUser: () => window.authManager?.user || null,
    hasRole: (role) => window.authManager?.hasRole(role) || false,
    logout: () => window.authManager?.logout(),
    refreshUserData: () => window.authManager?.refreshUserData()
};