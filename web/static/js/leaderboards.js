/**
 * Leaderboards Manager
 * Handles leaderboard display across categories and timeframes
 */

class LeaderboardsManager {
    constructor() {
        this.currentCategory = 'wealth';
        this.currentTimeframe = 'all_time';
        this.refreshInterval = null;
    }

    async init() {
        console.log('[Leaderboards] Initializing...');
        await this.loadLeaderboard();
        await this.loadMyRank();

        // Auto-refresh every 60 seconds
        this.refreshInterval = setInterval(() => {
            this.loadLeaderboard();
            this.loadMyRank();
        }, 60000);

        console.log('[Leaderboards] Ready!');
    }

    switchCategory(category) {
        this.currentCategory = category;

        // Update tab states
        document.querySelectorAll('.category-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        event.target.closest('.category-tab').classList.add('active');

        // Update title
        const titles = {
            'wealth': 'Wealth Leaderboard',
            'minigames': 'Mini-Games Leaderboard',
            'trading': 'Trading Leaderboard',
            'roulette': 'Roulette Leaderboard'
        };
        document.getElementById('leaderboard-title').textContent = titles[category];

        this.loadLeaderboard();
        this.loadMyRank();
    }

    switchTimeframe(timeframe) {
        this.currentTimeframe = timeframe;

        // Update button states
        document.querySelectorAll('.timeframe-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');

        this.loadLeaderboard();
        this.loadMyRank();
    }

    async loadLeaderboard() {
        const container = document.getElementById('leaderboard-content');

        try {
            const response = await fetch(`/api/leaderboards/${this.currentCategory}/${this.currentTimeframe}`);
            const data = await response.json();

            this.renderLeaderboard(data.entries);

        } catch (error) {
            console.error('[Leaderboards] Error loading:', error);
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-exclamation-circle" style="font-size: 3rem; color: var(--error);"></i>
                    <p class="mt-3">Failed to load leaderboard</p>
                </div>
            `;
        }
    }

    renderLeaderboard(entries) {
        const container = document.getElementById('leaderboard-content');

        if (entries.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-inbox" style="font-size: 3rem; color: var(--text-secondary);"></i>
                    <p class="mt-3">No leaderboard data yet</p>
                </div>
            `;
            return;
        }

        const token = localStorage.getItem('token');
        let currentUserId = null;
        if (token) {
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                currentUserId = payload.sub;
            } catch (e) {}
        }

        let html = `
            <div class="table-responsive">
                <table class="table-modern">
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Player</th>
                            <th>${this.getScoreLabel()}</th>
                            ${this.getExtraColumns()}
                        </tr>
                    </thead>
                    <tbody>
        `;

        entries.forEach(entry => {
            const rankClass = entry.rank === 1 ? 'rank-1' : entry.rank === 2 ? 'rank-2' : entry.rank === 3 ? 'rank-3' : 'rank-other';
            const isCurrentUser = currentUserId && entry.user_id === currentUserId;

            html += `
                <tr class="user-row ${isCurrentUser ? 'my-rank' : ''}">
                    <td>
                        <div class="rank-badge ${rankClass}">${entry.rank <= 3 ? ['🥇', '🥈', '🥉'][entry.rank - 1] : '#' + entry.rank}</div>
                    </td>
                    <td>
                        <strong>${entry.stats.username || 'Unknown'}</strong>
                        ${isCurrentUser ? '<span class="badge badge-modern badge-modern-primary ms-2">YOU</span>' : ''}
                    </td>
                    <td>
                        <strong style="color: var(--gem);">${this.formatNumber(entry.score)}</strong>
                    </td>
                    ${this.getExtraColumnValues(entry)}
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = html;
    }

    getScoreLabel() {
        const labels = {
            'wealth': 'GEM Balance',
            'minigames': 'Total Profit',
            'trading': 'Volume Traded',
            'roulette': 'Total Wagered'
        };
        return labels[this.currentCategory];
    }

    getExtraColumns() {
        if (this.currentCategory === 'minigames') {
            return '<th>Wins</th><th>Games</th>';
        }
        return '';
    }

    getExtraColumnValues(entry) {
        if (this.currentCategory === 'minigames') {
            return `
                <td>${this.formatNumber(entry.stats.wins || 0)}</td>
                <td>${this.formatNumber(entry.stats.games || 0)}</td>
            `;
        }
        return '';
    }

    async loadMyRank() {
        const token = localStorage.getItem('token');
        if (!token) {
            document.getElementById('my-rank-card').style.display = 'none';
            return;
        }

        try {
            const response = await fetch(
                `/api/leaderboards/my-rank/${this.currentCategory}/${this.currentTimeframe}`,
                { headers: { 'Authorization': `Bearer ${token}` } }
            );

            const data = await response.json();

            if (data.rank) {
                document.getElementById('my-rank-card').style.display = 'block';
                document.getElementById('my-rank-badge').textContent = '#' + data.rank;
                document.getElementById('my-rank-score').textContent = this.formatNumber(data.score);

                const labels = {
                    'wealth': 'GEM',
                    'minigames': 'Profit',
                    'trading': 'Volume',
                    'roulette': 'Wagered'
                };
                document.getElementById('my-rank-label').textContent = labels[this.currentCategory];

                // Update badge color
                const badge = document.getElementById('my-rank-badge');
                badge.className = 'rank-badge';
                if (data.rank === 1) badge.classList.add('rank-1');
                else if (data.rank === 2) badge.classList.add('rank-2');
                else if (data.rank === 3) badge.classList.add('rank-3');
                else badge.classList.add('rank-other');
            } else {
                document.getElementById('my-rank-card').style.display = 'none';
            }

        } catch (error) {
            console.error('[Leaderboards] Error loading rank:', error);
            document.getElementById('my-rank-card').style.display = 'none';
        }
    }

    formatNumber(num) {
        return new Intl.NumberFormat('en-US').format(num);
    }

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
}

const Leaderboards = new LeaderboardsManager();

window.addEventListener('beforeunload', () => {
    Leaderboards.destroy();
});
