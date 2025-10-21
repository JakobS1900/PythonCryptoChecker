/**
 * Clicker Phase 3B: Leaderboards System
 * Competitive rankings across multiple categories
 */

class LeaderboardsManager {
    constructor() {
        this.currentCategory = 'total_clicks';
        this.playerRanks = null;
        this.leaderboardData = null;
        this.refreshInterval = 30000; // Refresh every 30 seconds
        this.refreshTimer = null;

        this.init();
    }

    async init() {
        console.log('🏆 Initializing Leaderboards Manager...');

        // Setup category tabs
        this.setupTabs();

        // Load initial data
        await this.loadPlayerRanks();
        await this.loadLeaderboard(this.currentCategory);

        // Start auto-refresh
        this.startAutoRefresh();

        console.log('✅ Leaderboards Manager initialized');
    }

    setupTabs() {
        const tabs = document.querySelectorAll('.leaderboard-tab');

        tabs.forEach(tab => {
            tab.addEventListener('click', async () => {
                const category = tab.dataset.category;

                // Update active tab
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                // Load leaderboard for this category
                this.currentCategory = category;
                await this.loadLeaderboard(category);
            });
        });
    }

    async loadPlayerRanks() {
        try {
            const token = localStorage.getItem('token');
            if (!token) return;

            const response = await fetch('/api/clicker/leaderboards/player/ranks', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            const result = await response.json();
            if (result.success) {
                this.playerRanks = result.data.ranks;
                this.updateRanksSummary();
            }
        } catch (error) {
            console.error('Error loading player ranks:', error);
        }
    }

    updateRanksSummary() {
        const summaryEl = document.getElementById('player-ranks-summary');
        if (!summaryEl || !this.playerRanks) return;

        // Find best rank
        let bestRank = null;
        let bestCategory = null;

        for (const [category, data] of Object.entries(this.playerRanks)) {
            if (data.rank && (!bestRank || data.rank < bestRank)) {
                bestRank = data.rank;
                bestCategory = category;
            }
        }

        if (bestRank) {
            summaryEl.innerHTML = `
                <div>Best Rank: <strong>#${bestRank}</strong> in ${this.getCategoryName(bestCategory)}</div>
            `;
        } else {
            summaryEl.innerHTML = `<div>Start playing to earn your rank!</div>`;
        }
    }

    getCategoryName(category) {
        const names = {
            'total_clicks': 'Total Clicks',
            'best_combo': 'Best Combo',
            'total_gems': 'Total GEM',
            'prestige': 'Prestige',
            'daily_gems': 'Daily GEM',
            'speedrun': 'Race to 1M'
        };
        return names[category] || category;
    }

    async loadLeaderboard(category) {
        const contentEl = document.getElementById('leaderboard-content');
        if (!contentEl) return;

        // Show loading state
        contentEl.innerHTML = `
            <div class="leaderboard-loading">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;

        try {
            const response = await fetch(`/api/clicker/leaderboards/${category}?limit=100`);
            const result = await response.json();

            if (result.success) {
                this.leaderboardData = result.data;
                this.renderLeaderboard();
            } else {
                this.showError(result.error || 'Failed to load leaderboard');
            }
        } catch (error) {
            console.error('Error loading leaderboard:', error);
            this.showError('Failed to load leaderboard');
        }
    }

    renderLeaderboard() {
        const contentEl = document.getElementById('leaderboard-content');
        if (!contentEl || !this.leaderboardData) return;

        const players = this.leaderboardData.players;

        if (players.length === 0) {
            contentEl.innerHTML = `
                <div class="leaderboard-empty">
                    <i class="bi bi-trophy"></i>
                    <div>No players yet. Be the first!</div>
                </div>
            `;
            return;
        }

        // Get current user ID
        const token = localStorage.getItem('token');
        let currentUserId = null;
        if (token) {
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                currentUserId = payload.sub;
            } catch (e) {
                console.error('Error parsing token:', e);
            }
        }

        // Build table HTML
        let html = '<div class="leaderboard-table">';

        players.forEach(player => {
            const isCurrentPlayer = player.user_id === currentUserId;
            const rankClass = player.rank <= 3 ? `rank-${player.rank}` : '';
            const rowClass = isCurrentPlayer ? 'current-player' : '';

            const formattedValue = this.formatLeaderboardValue(
                this.currentCategory,
                player.value
            );

            const avatarUrl = player.avatar_url || '/static/images/default-avatar.png';

            html += `
                <div class="leaderboard-row ${rowClass}">
                    <div class="leaderboard-rank ${rankClass}">
                        ${this.getRankDisplay(player.rank)}
                    </div>
                    <div class="leaderboard-player">
                        <img src="${avatarUrl}"
                             alt="${player.username}"
                             class="leaderboard-player-avatar"
                             onerror="this.src='/static/images/default-avatar.png'">
                        <div class="leaderboard-player-name">
                            ${this.escapeHtml(player.username)}
                            ${isCurrentPlayer ? '<span style="color: var(--warning); margin-left: 8px;">(You)</span>' : ''}
                        </div>
                    </div>
                    <div class="leaderboard-value">
                        ${formattedValue}
                    </div>
                </div>
            `;
        });

        html += '</div>';
        contentEl.innerHTML = html;
    }

    getRankDisplay(rank) {
        if (rank === 1) return '🥇';
        if (rank === 2) return '🥈';
        if (rank === 3) return '🥉';
        return `#${rank}`;
    }

    formatLeaderboardValue(category, value) {
        if (category === 'total_clicks') {
            return this.formatNumber(value);
        } else if (category === 'best_combo') {
            return `${value}x`;
        } else if (category === 'total_gems' || category === 'daily_gems') {
            return this.formatGEM(value);
        } else if (category === 'prestige') {
            return `Level ${value}`;
        } else if (category === 'speedrun') {
            return this.formatTime(value);
        }
        return value;
    }

    formatNumber(num) {
        if (num >= 1000000000) {
            return (num / 1000000000).toFixed(2) + 'B';
        } else if (num >= 1000000) {
            return (num / 1000000).toFixed(2) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(2) + 'K';
        }
        return num.toLocaleString();
    }

    formatGEM(amount) {
        if (amount >= 1000000000) {
            return (amount / 1000000000).toFixed(2) + 'B GEM';
        } else if (amount >= 1000000) {
            return (amount / 1000000).toFixed(2) + 'M GEM';
        } else if (amount >= 1000) {
            return (amount / 1000).toFixed(2) + 'K GEM';
        }
        return amount.toLocaleString(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        }) + ' GEM';
    }

    formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showError(message) {
        const contentEl = document.getElementById('leaderboard-content');
        if (!contentEl) return;

        contentEl.innerHTML = `
            <div class="leaderboard-empty">
                <i class="bi bi-exclamation-triangle"></i>
                <div>${this.escapeHtml(message)}</div>
            </div>
        `;
    }

    startAutoRefresh() {
        // Clear existing timer
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }

        // Refresh every 30 seconds
        this.refreshTimer = setInterval(async () => {
            await this.loadPlayerRanks();
            await this.loadLeaderboard(this.currentCategory);
        }, this.refreshInterval);
    }

    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    // Public method to manually refresh
    async refresh() {
        await this.loadPlayerRanks();
        await this.loadLeaderboard(this.currentCategory);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if leaderboard elements exist
    if (document.getElementById('leaderboard-content')) {
        window.leaderboardsManager = new LeaderboardsManager();
    }
});
