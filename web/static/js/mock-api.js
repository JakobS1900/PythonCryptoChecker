/**
 * Mock API Implementation for Development
 * Development mock layer to avoid 404s during integration.
 * Provides realistic mock data for dashboard features
 */

class MockAPIClient {
    constructor() {
        this.isDevelopmentMode = true; // Set to false when real API is ready
        this.mockDelay = 300; // Simulate network delay
        console.log('🎭 Mock API Client initialized.');
    }

    // ===== MOCK DATA GENERATORS =====

    generateMockUser() {
        return {
            id: 'user-123',
            username: 'CryptoGamer2025',
            display_name: 'Crypto Gamer',
            email: 'cryptogamer@example.com',
            avatar_url: '/static/images/default-avatar.png',
            gem_coins: 15750,
            current_level: 8,
            total_experience: 12500,
            created_at: '2024-12-01T10:00:00Z',
            last_login: new Date().toISOString(),
            status: 'online',
            rank: 42
        };
    }

    generateMockFriends() {
        return [
            {
                id: 'friend-1',
                username: 'CryptoMaster',
                display_name: 'Crypto Master',
                avatar_url: '/static/images/default-avatar.png',
                status: 'online',
                level: 12,
                last_seen: new Date().toISOString()
            },
            {
                id: 'friend-2', 
                username: 'DiamondHands',
                display_name: 'Diamond Hands',
                avatar_url: '/static/images/default-avatar.png',
                status: 'online',
                level: 9,
                last_seen: new Date(Date.now() - 5 * 60000).toISOString()
            },
            {
                id: 'friend-3',
                username: 'MoonLander',
                display_name: 'Moon Lander',
                avatar_url: '/static/images/default-avatar.png',
                status: 'online',
                level: 15,
                last_seen: new Date(Date.now() - 2 * 60000).toISOString()
            },
            {
                id: 'friend-4',
                username: 'HODLKing',
                display_name: 'HODL King',
                avatar_url: '/static/images/default-avatar.png',
                status: 'online',
                level: 7,
                last_seen: new Date().toISOString()
            }
        ];
    }

    generateMockLeaderboard() {
        return [
            {
                rank: 1,
                user: {
                    id: 'leader-1',
                    username: 'CryptoLegend',
                    display_name: 'Crypto Legend',
                    avatar_url: '/static/images/default-avatar.png'
                },
                score: 25000,
                level: 20
            },
            {
                rank: 2,
                user: {
                    id: 'leader-2',
                    username: 'GamingGuru',
                    display_name: 'Gaming Guru',
                    avatar_url: '/static/images/default-avatar.png'
                },
                score: 22500,
                level: 18
            },
            {
                rank: 3,
                user: {
                    id: 'leader-3',
                    username: 'RouletteRoyalty',
                    display_name: 'Roulette Royalty',
                    avatar_url: '/static/images/default-avatar.png'
                },
                score: 20000,
                level: 17
            },
            {
                rank: 4,
                user: {
                    id: 'leader-4',
                    username: 'LuckySeven',
                    display_name: 'Lucky Seven',
                    avatar_url: '/static/images/default-avatar.png'
                },
                score: 18750,
                level: 16
            },
            {
                rank: 5,
                user: {
                    id: 'leader-5',
                    username: 'HighRoller',
                    display_name: 'High Roller',
                    avatar_url: '/static/images/default-avatar.png'
                },
                score: 17250,
                level: 15
            }
        ];
    }

    generateMockActivity() {
        return [
            {
                id: 'activity-1',
                user: {
                    id: 'friend-1',
                    username: 'CryptoMaster',
                    display_name: 'Crypto Master',
                    avatar_url: '/static/images/default-avatar.png'
                },
                activity_type: 'game_won',
                content: {
                    winnings: 2500,
                    game_type: 'roulette'
                },
                timestamp: new Date(Date.now() - 5 * 60000).toISOString()
            },
            {
                id: 'activity-2',
                user: {
                    id: 'friend-2',
                    username: 'DiamondHands',
                    display_name: 'Diamond Hands',
                    avatar_url: '/static/images/default-avatar.png'
                },
                activity_type: 'achievement_unlocked',
                content: {
                    achievement_name: 'High Roller',
                    description: 'Win 10 games in a row'
                },
                timestamp: new Date(Date.now() - 15 * 60000).toISOString()
            },
            {
                id: 'activity-3',
                user: {
                    id: 'friend-3',
                    username: 'MoonLander',
                    display_name: 'Moon Lander',
                    avatar_url: '/static/images/default-avatar.png'
                },
                activity_type: 'level_up',
                content: {
                    new_level: 15,
                    experience_gained: 1500
                },
                timestamp: new Date(Date.now() - 30 * 60000).toISOString()
            },
            {
                id: 'activity-4',
                user: {
                    id: 'friend-4',
                    username: 'HODLKing',
                    display_name: 'HODL King',
                    avatar_url: '/static/images/default-avatar.png'
                },
                activity_type: 'item_obtained',
                content: {
                    item_name: 'Golden Dice',
                    rarity: 'legendary'
                },
                timestamp: new Date(Date.now() - 45 * 60000).toISOString()
            },
            {
                id: 'activity-5',
                user: {
                    id: 'user-123',
                    username: 'CryptoGamer2025',
                    display_name: 'Crypto Gamer',
                    avatar_url: '/static/images/default-avatar.png'
                },
                activity_type: 'friend_added',
                content: {
                    friend_name: 'NewPlayer123'
                },
                timestamp: new Date(Date.now() - 60 * 60000).toISOString()
            }
        ];
    }

    generateMockGamingStats() {
        return {
            total_games: 157,
            total_wins: 89,
            total_losses: 68,
            win_rate: 56.7,
            total_winnings: 45250,
            biggest_win: 8500,
            current_streak: 3,
            longest_win_streak: 12,
            longest_loss_streak: 5,
            favorite_game: 'roulette',
            achievements_count: 23,
            level_progress: {
                current_level: 8,
                current_exp: 2500,
                required_exp: 3000,
                progress_percentage: 83.3
            }
        };
    }

    // ===== MOCK API DELAY SIMULATION =====
    async delay(ms = this.mockDelay) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // ===== MOCK API METHODS =====

    async getActivityFeed(limit = 10) {
        console.log('🎭 Mock API: getActivityFeed called');
        await this.delay();
        
        const activities = this.generateMockActivity();
        return {
            success: true,
            data: activities.slice(0, limit),
            pagination: {
                page: 1,
                limit: limit,
                total: activities.length,
                has_more: activities.length > limit
            }
        };
    }

    async getOnlineFriends() {
        console.log('🎭 Mock API: getOnlineFriends called');
        await this.delay();
        
        const friends = this.generateMockFriends();
        return {
            success: true,
            data: {
                online_friends: friends,
                total_online: friends.length,
                total_friends: friends.length + 8 // Some offline friends
            }
        };
    }

    async getLeaderboard(type = 'level', limit = 5) {
        console.log(`🎭 Mock API: getLeaderboard(${type}) called`);
        await this.delay();
        
        const leaderboard = this.generateMockLeaderboard();
        return {
            success: true,
            data: leaderboard.slice(0, limit),
            pagination: {
                page: 1,
                limit: limit,
                total: leaderboard.length,
                has_more: leaderboard.length > limit
            },
            leaderboard_type: type
        };
    }

    async getGamingStats() {
        console.log('🎭 Mock API: getGamingStats called');
        await this.delay();
        
        return {
            success: true,
            data: this.generateMockGamingStats()
        };
    }

    async getUserProfile() {
        console.log('🎭 Mock API: getUserProfile called');
        await this.delay();
        
        return {
            success: true,
            data: this.generateMockUser()
        };
    }

    async getSocialStats() {
        console.log('🎭 Mock API: getSocialStats called');
        await this.delay();
        
        return {
            success: true,
            data: {
                total_friends: 12,
                online_friends: 4,
                pending_requests: 2,
                sent_requests: 1,
                referrals: 5,
                gifts_sent: 15,
                gifts_received: 8
            }
        };
    }

    // ===== MOCK ERROR SIMULATION =====
    async simulateError(errorType = '500') {
        await this.delay(100);
        
        const errors = {
            '404': { success: false, error: 'Not Found', status: 404 },
            '500': { success: false, error: 'Internal Server Error', status: 500 },
            'network': { success: false, error: 'Network Error', status: 0 }
        };
        
        return errors[errorType] || errors['500'];
    }
}

// ===== INTEGRATION WITH EXISTING API CLIENT =====

class EnhancedAPIClient {
    constructor() {
        this.realAPI = new APIClient();
        this.mockAPI = new MockAPIClient();
        this.useMockData = false; // Default to real APIs
        
        console.log('🚀 Enhanced API Client initialized!');
        if (this.useMockData) {
            console.log('🎭 Using MOCK DATA for development.');
        } else {
            console.log('🔥 Using REAL APIs.');
        }
    }
    
    // ===== AUTHENTICATION METHODS (PROXY TO REAL API) =====
    auth = {
        login: async (credentials) => {
            console.log('🔐 Enhanced API: Proxying login to real API');
            return await this.realAPI.auth.login(credentials);
        },
        
        register: async (userData) => {
            console.log('🔐 Enhanced API: Proxying register to real API');
            return await this.realAPI.auth.register(userData);
        },
        
        logout: async () => {
            console.log('🔐 Enhanced API: Proxying logout to real API');
            return await this.realAPI.auth.logout();
        },
        
        getProfile: async () => {
            console.log('🔐 Enhanced API: Proxying getProfile to real API');
            return await this.realAPI.auth.getProfile();
        },
        
        updateProfile: async (profileData) => {
            console.log('🔐 Enhanced API: Proxying updateProfile to real API');
            return await this.realAPI.auth.updateProfile(profileData);
        },
        
        changePassword: async (passwordData) => {
            console.log('🔐 Enhanced API: Proxying changePassword to real API');
            return await this.realAPI.auth.changePassword(passwordData);
        }
    };

    // ===== ENHANCED SOCIAL METHODS WITH FALLBACK =====
    
    social = {
        getActivityFeed: async (limit = 10) => {
            if (this.useMockData) {
                return await this.mockAPI.getActivityFeed(limit);
            }
            
            try {
                return await this.realAPI.social.getActivityFeed(limit);
            } catch (error) {
                console.warn('⚠️ Real API failed, falling back to mock data.');
                return await this.mockAPI.getActivityFeed(limit);
            }
        },

        getOnlineFriends: async () => {
            if (this.useMockData) {
                return await this.mockAPI.getOnlineFriends();
            }
            
            try {
                return await this.realAPI.social.getOnlineFriends();
            } catch (error) {
                console.warn('⚠️ Real API failed, falling back to mock data.');
                return await this.mockAPI.getOnlineFriends();
            }
        },

        getLeaderboard: async (type = 'level', limit = 5) => {
            if (this.useMockData) {
                return await this.mockAPI.getLeaderboard(type, limit);
            }
            
            try {
                return await this.realAPI.social.getLeaderboard(type, limit);
            } catch (error) {
                console.warn('⚠️ Real API failed, falling back to mock data.');
                return await this.mockAPI.getLeaderboard(type, limit);
            }
        },

        getSocialStats: async () => {
            if (this.useMockData) {
                return await this.mockAPI.getSocialStats();
            }
            
            try {
                return await this.realAPI.social.getSocialStats();
            } catch (error) {
                console.warn('⚠️ Real API failed, falling back to mock data.');
                return await this.mockAPI.getSocialStats();
            }
        }
    };

    // ===== ENHANCED GAMING METHODS WITH FALLBACK =====
    
    gaming = {
        getStats: async () => {
            if (this.useMockData) {
                return await this.mockAPI.getGamingStats();
            }
            
            try {
                return await this.realAPI.gaming.getStats();
            } catch (error) {
                console.warn('⚠️ Real API failed, falling back to mock data.');
                return await this.mockAPI.getGamingStats();
            }
        }
    };

    // ===== ENHANCED INVENTORY METHODS WITH FALLBACK =====
    
    inventory = {
        getItems: async (page = 1, rarity = null, category = null) => {
            console.log('🎒 Fetching inventory items...', { page, rarity, category });
            try {
                return await this.realAPI.inventory.getItems(page, rarity, category);
            } catch (error) {
                console.warn('⚠️ Inventory API failed:', error);
                // Return empty inventory as fallback
                return {
                    success: true,
                    data: {
                        items: [],
                        pagination: {
                            current_page: 1,
                            total_pages: 1,
                            total_items: 0
                        }
                    }
                };
            }
        },

        getItem: async (itemId) => {
            try {
                return await this.realAPI.inventory.getItem(itemId);
            } catch (error) {
                console.warn('⚠️ Get item API failed:', error);
                return { success: false, error: error.message };
            }
        },

        equipItem: async (itemId, slot = null) => {
            try {
                return await this.realAPI.inventory.equipItem(itemId, slot);
            } catch (error) {
                console.warn('⚠️ Equip item API failed:', error);
                return { success: false, error: error.message };
            }
        },

        useItem: async (itemId, quantity = 1) => {
            try {
                return await this.realAPI.inventory.useItem(itemId, quantity);
            } catch (error) {
                console.warn('⚠️ Use item API failed:', error);
                return { success: false, error: error.message };
            }
        },

        sellItem: async (itemId, quantity = 1) => {
            try {
                return await this.realAPI.inventory.sellItem(itemId, quantity);
            } catch (error) {
                console.warn('⚠️ Sell item API failed:', error);
                return { success: false, error: error.message };
            }
        },

        getTrades: async (status = null) => {
            try {
                return await this.realAPI.inventory.getTrades(status);
            } catch (error) {
                console.warn('⚠️ Get trades API failed:', error);
                return {
                    success: true,
                    data: []
                };
            }
        },

        respondToTrade: async (tradeId, action) => {
            try {
                return await this.realAPI.inventory.respondToTrade(tradeId, action);
            } catch (error) {
                console.warn('⚠️ Respond to trade API failed:', error);
                return { success: false, error: error.message };
            }
        },

        cancelTrade: async (tradeId) => {
            try {
                return await this.realAPI.inventory.cancelTrade(tradeId);
            } catch (error) {
                console.warn('⚠️ Cancel trade API failed:', error);
                return { success: false, error: error.message };
            }
        },

        getMarketplace: async (page = 1, rarity = null, category = null) => {
            try {
                return await this.realAPI.inventory.getMarketplace(page, rarity, category);
            } catch (error) {
                console.warn('⚠️ Marketplace API failed:', error);
                return {
                    success: true,
                    data: {
                        items: [],
                        pagination: {
                            current_page: 1,
                            total_pages: 1,
                            total_items: 0
                        }
                    }
                };
            }
        }
    };

    // ===== USER PROFILE METHODS =====
    
    async getUserProfile() {
        if (this.useMockData) {
            return await this.mockAPI.getUserProfile();
        }
        
        try {
            return await this.realAPI.auth.getProfile();
        } catch (error) {
            console.warn('⚠️ Real API failed, falling back to mock data.');
            return await this.mockAPI.getUserProfile();
        }
    }

    // ===== DEVELOPMENT UTILITIES =====
    
    toggleMockMode(useMock = true) {
        this.useMockData = useMock;
        console.log(`🔄 Mock mode ${useMock ? 'ENABLED' : 'DISABLED'}`);
    }

    setMockDelay(ms) {
        this.mockAPI.mockDelay = ms;
        console.log(`⏱️ Mock delay set to ${ms}ms`);
    }
}

// ===== GLOBAL INITIALIZATION =====

// Only initialize EnhancedAPIClient if no existing apiClient exists
if (typeof window !== 'undefined') {
    // Don't override existing apiClient to prevent double API prefix issues
    if (!window.apiClient) {
        window.apiClient = new EnhancedAPIClient();
    } else {
        console.log('🔄 Existing APIClient found, skipping EnhancedAPIClient initialization');
    }
    
    // Add global utilities for debugging
    window.mockAPI = {
        enable: () => window.apiClient.toggleMockMode(true),
        disable: () => window.apiClient.toggleMockMode(false),
        setDelay: (ms) => window.apiClient.setMockDelay(ms),
        test: async () => {
            console.log('🧪 Testing Mock API');
            const activity = await window.apiClient.social.getActivityFeed(3);
            const friends = await window.apiClient.social.getOnlineFriends();
            const leaderboard = await window.apiClient.social.getLeaderboard('level', 3);
            console.log('✅ Mock API test results:', { activity, friends, leaderboard });
        }
    };
    
    console.log('🎉 Enhanced API Client ready! Use window.mockAPI.test() to test.');
}

// Export for module environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EnhancedAPIClient, MockAPIClient };
}
