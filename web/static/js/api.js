/**
 * API Client for Crypto Gamification Platform
 * Handles all API communications with proper error handling and token management
 */

class APIClient {
    constructor() {
        this.baseURL = '/api';
        this.token = localStorage.getItem('access_token');
        this.refreshToken = localStorage.getItem('refresh_token');
    }

    // ===== UTILITY METHODS =====

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            credentials: 'same-origin', // Include cookies for session-based auth
            ...options
        };

        // Add auth header if token exists
        if (this.token && !options.skipAuth) {
            config.headers.Authorization = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                // Handle token expiration
                if (response.status === 401 && this.refreshToken && !options.skipRefresh) {
                    const refreshed = await this.refreshAccessToken();
                    if (refreshed) {
                        // Retry original request with new token
                        return this.request(endpoint, { ...options, skipRefresh: true });
                    } else {
                        this.handleAuthError();
                        throw new Error('Authentication failed');
                    }
                }
                
                throw new Error(data.detail || data.message || `HTTP ${response.status}`);
            }

            return {
                success: true,
                data: data,
                status: response.status
            };
        } catch (error) {
            console.error('API request failed:', error);
            return {
                success: false,
                message: error.message,
                error: error
            };
        }
    }

    async refreshAccessToken() {
        try {
            const response = await this.request('/auth/refresh', {
                method: 'POST',
                body: JSON.stringify({ refresh_token: this.refreshToken }),
                skipAuth: true,
                skipRefresh: true
            });

            if (response.success) {
                this.token = response.data.access_token;
                this.refreshToken = response.data.refresh_token;
                localStorage.setItem('access_token', this.token);
                localStorage.setItem('refresh_token', this.refreshToken);
                return true;
            }
        } catch (error) {
            console.error('Token refresh failed:', error);
        }
        
        return false;
    }

    handleAuthError() {
        // Clear stored tokens
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_data');
        this.token = null;
        this.refreshToken = null;
        
        // Redirect to login if not already there
        if (window.location.pathname !== '/login') {
            window.location.href = '/login';
        }
    }

    // ===== AUTHENTICATION METHODS =====

    auth = {
        login: async (credentials) => {
            return this.request('/auth/login', {
                method: 'POST',
                body: JSON.stringify(credentials),
                skipAuth: true
            });
        },

        register: async (userData) => {
            return this.request('/auth/register', {
                method: 'POST',
                body: JSON.stringify(userData),
                skipAuth: true
            });
        },

        logout: async () => {
            const result = await this.request('/auth/logout', {
                method: 'POST'
            });
            
            if (result.success) {
                this.handleAuthError();
            }
            
            return result;
        },

        getProfile: async () => {
            return this.request('/auth/profile');
        },

        updateProfile: async (profileData) => {
            return this.request('/auth/profile', {
                method: 'PUT',
                body: JSON.stringify(profileData)
            });
        },

        changePassword: async (passwordData) => {
            return this.request('/auth/change-password', {
                method: 'POST',
                body: JSON.stringify(passwordData)
            });
        }
    };

    // ===== GAMING METHODS =====

    gaming = {
        createSession: async (gameData = {}) => {
            return this.request('/gaming/sessions', {
                method: 'POST',
                body: JSON.stringify(gameData)
            });
        },

        placeBet: async (gameId, betData) => {
            return this.request(`/gaming/sessions/${gameId}/bets`, {
                method: 'POST',
                body: JSON.stringify(betData)
            });
        },

        spinWheel: async (gameId) => {
            return this.request(`/gaming/sessions/${gameId}/spin`, {
                method: 'POST'
            });
        },

        verifyGame: async (gameId) => {
            return this.request(`/gaming/sessions/${gameId}/verify`);
        },

        getHistory: async (limit = 50, offset = 0) => {
            return this.request(`/gaming/history?limit=${limit}&offset=${offset}`);
        },

        getStats: async () => {
            return this.request('/gaming/stats');
        },

        getWheelInfo: async () => {
            return this.request('/gaming/wheel-info');
        },

        getBetTypes: async () => {
            return this.request('/gaming/bet-types');
        },

        // Tournament methods
        getTournaments: async () => {
            return this.request('/gaming/tournaments');
        },

        joinTournament: async (tournamentId) => {
            return this.request(`/gaming/tournaments/${tournamentId}/join`, {
                method: 'POST'
            });
        },

        getTournamentLeaderboard: async (tournamentId, limit = 50) => {
            return this.request(`/gaming/tournaments/${tournamentId}/leaderboard?limit=${limit}`);
        },

        // Price prediction
        createPricePrediction: async (predictionData) => {
            return this.request('/gaming/price-prediction', {
                method: 'POST',
                body: JSON.stringify(predictionData)
            });
        },

        getPricePredictionResult: async (gameId) => {
            return this.request(`/gaming/price-prediction/${gameId}/result`);
        }
    };

    // ===== INVENTORY METHODS =====

    inventory = {
        getItems: async (page = 1, rarity = null, category = null) => {
            let url = `/api/inventory/items?page=${page}`;
            if (rarity) url += `&rarity=${rarity}`;
            if (category) url += `&category=${category}`;
            return this.request(url);
        },

        getItem: async (itemId) => {
            return this.request(`/api/inventory/items/${itemId}`);
        },

        equipItem: async (itemId, slot = null) => {
            return this.request(`/api/inventory/items/${itemId}/equip`, {
                method: 'POST',
                body: JSON.stringify({ slot })
            });
        },

        unequipItem: async (itemId) => {
            return this.request(`/api/inventory/items/${itemId}/unequip`, {
                method: 'POST'
            });
        },

        useItem: async (itemId, quantity = 1) => {
            return this.request(`/api/inventory/items/${itemId}/use`, {
                method: 'POST',
                body: JSON.stringify({ quantity })
            });
        },

        sellItem: async (itemId, quantity = 1) => {
            return this.request(`/api/inventory/items/${itemId}/sell`, {
                method: 'POST',
                body: JSON.stringify({ quantity })
            });
        },

        // Trading methods
        createTrade: async (tradeData) => {
            return this.request('/api/inventory/trades', {
                method: 'POST',
                body: JSON.stringify(tradeData)
            });
        },

        getTrades: async (status = null) => {
            let url = '/api/inventory/trades';
            if (status) url += `?status=${status}`;
            return this.request(url);
        },

        respondToTrade: async (tradeId, action) => {
            return this.request(`/api/inventory/trades/${tradeId}`, {
                method: 'PUT',
                body: JSON.stringify({ action })
            });
        },

        cancelTrade: async (tradeId) => {
            return this.request(`/api/inventory/trades/${tradeId}`, {
                method: 'DELETE'
            });
        },

        // Marketplace
        getMarketplace: async (page = 1, rarity = null, category = null) => {
            let url = `/api/inventory/marketplace?page=${page}`;
            if (rarity) url += `&rarity=${rarity}`;
            if (category) url += `&category=${category}`;
            return this.request(url);
        },

        getWallet: async () => {
            return this.request('/api/inventory/wallet');
        }
    };

    // ===== SOCIAL METHODS =====

    social = {
        getFriends: async () => {
            return this.request('/social/friends');
        },

        sendFriendRequest: async (username) => {
            return this.request('/social/friends/request', {
                method: 'POST',
                body: JSON.stringify({ username })
            });
        },

        getFriendRequests: async () => {
            return this.request('/social/friends/requests');
        },

        respondToFriendRequest: async (requestId, action) => {
            return this.request(`/social/friends/requests/${requestId}`, {
                method: 'POST',
                body: JSON.stringify({ request_id: requestId, action })
            });
        },

        removeFriend: async (friendId) => {
            return this.request(`/social/friends/${friendId}`, {
                method: 'DELETE'
            });
        },

        getLeaderboard: async (type, limit = 50) => {
            return this.request(`/social/leaderboards/${type}?limit=${limit}`);
        },

        getMyRank: async (type) => {
            return this.request(`/social/leaderboards/${type}/my-rank`);
        },

        sendGift: async (giftData) => {
            return this.request('/social/gifts/send', {
                method: 'POST',
                body: JSON.stringify(giftData)
            });
        },

        getReceivedGifts: async (limit = 20) => {
            return this.request(`/social/gifts/received?limit=${limit}`);
        },

        getActivityFeed: async (limit = 50) => {
            return this.request(`/social/activity?limit=${limit}`);
        },

        updateStatus: async (status, mood = null) => {
            return this.request('/social/status', {
                method: 'PUT',
                body: JSON.stringify({ status, mood })
            });
        },

        getOnlineFriends: async () => {
            return this.request('/social/online-friends');
        },

        getSocialStats: async () => {
            return this.request('/social/stats');
        }
    };

    // ===== ADMIN METHODS =====

    admin = {
        getUsers: async (limit = 100, offset = 0, search = null, roleFilter = null) => {
            let url = `/admin/users?limit=${limit}&offset=${offset}`;
            if (search) url += `&search=${search}`;
            if (roleFilter) url += `&role_filter=${roleFilter}`;
            return this.request(url);
        },

        manageUser: async (userData) => {
            return this.request('/admin/users/manage', {
                method: 'POST',
                body: JSON.stringify(userData)
            });
        },

        bulkAdjustCurrency: async (adjustmentData) => {
            return this.request('/admin/currency/bulk-adjust', {
                method: 'POST',
                body: JSON.stringify(adjustmentData)
            });
        },

        createCustomItem: async (itemData) => {
            return this.request('/admin/items/create', {
                method: 'POST',
                body: JSON.stringify(itemData)
            });
        },

        createCustomAchievement: async (achievementData) => {
            return this.request('/admin/achievements/create', {
                method: 'POST',
                body: JSON.stringify(achievementData)
            });
        },

        getSystemOverview: async () => {
            return this.request('/admin/stats/overview');
        },

        scheduleMaintenance: async (maintenanceData) => {
            return this.request('/admin/maintenance', {
                method: 'POST',
                body: JSON.stringify(maintenanceData)
            });
        },

        getSystemLogs: async (level = 'INFO', limit = 100, search = null) => {
            let url = `/admin/logs?level=${level}&limit=${limit}`;
            if (search) url += `&search=${search}`;
            return this.request(url);
        }
    };

    // ===== HELPER METHODS =====

    async healthCheck() {
        return this.request('/health', { skipAuth: true });
    }

    isAuthenticated() {
        return !!this.token;
    }

    getCurrentUser() {
        const userData = localStorage.getItem('user_data');
        return userData ? JSON.parse(userData) : null;
    }

    updateCurrentUser(userData) {
        localStorage.setItem('user_data', JSON.stringify(userData));
    }
}

// Global API client instance
window.apiClient = new APIClient();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = APIClient;
}