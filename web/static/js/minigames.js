/**
 * Mini-Games Manager
 * Handles Coin Flip, Dice Roll, and Higher/Lower games
 */

class MiniGamesManager {
    constructor() {
        this.currentGame = null;
        this.userBalance = 0;
        this.stats = {};
    }

    async init() {
        console.log('[MiniGames] Initializing...');
        await this.loadBalance();
        await this.loadStats();
        await this.loadHistory();
        console.log('[MiniGames] Ready!');
    }

    async loadBalance() {
        try {
            const token = localStorage.getItem('auth_token');
            if (!token) return;

            const response = await fetch('/api/auth/status', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                this.userBalance = data.gem_balance || 0;
                document.getElementById('user-balance-display').textContent = this.formatNumber(this.userBalance);
            }
        } catch (error) {
            console.error('[MiniGames] Error loading balance:', error);
        }
    }

    async loadStats() {
        try {
            const token = localStorage.getItem('auth_token');
            if (!token) return;

            const response = await fetch('/api/minigames/stats', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                this.stats = data.stats;

                document.getElementById('stat-games').textContent = this.formatNumber(this.stats.total_games_played);
                document.getElementById('stat-winrate').textContent = this.stats.win_rate + '%';
                document.getElementById('stat-profit').textContent = this.formatNumber(this.stats.net_profit);
                document.getElementById('stat-streak').textContent = this.stats.current_win_streak + ' 🔥';
            }
        } catch (error) {
            console.error('[MiniGames] Error loading stats:', error);
        }
    }

    async loadHistory() {
        try {
            const token = localStorage.getItem('auth_token');
            if (!token) {
                document.getElementById('history-list').innerHTML = '<p class="text-center">Login to view history</p>';
                return;
            }

            const response = await fetch('/api/minigames/history?limit=10', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                this.renderHistory(data.games);
            }
        } catch (error) {
            console.error('[MiniGames] Error loading history:', error);
        }
    }

    renderHistory(games) {
        const container = document.getElementById('history-list');

        if (games.length === 0) {
            container.innerHTML = '<p class="text-center">No games played yet</p>';
            return;
        }

        let html = '<div class="table-responsive"><table class="table-modern"><thead><tr>' +
            '<th>Game</th><th>Bet</th><th>Result</th><th>Profit</th><th>Time</th></tr></thead><tbody>';

        games.forEach(game => {
            const gameIcon = game.game_type === 'coinflip' ? '🪙' : game.game_type === 'dice' ? '🎲' : '🃏';
            const resultClass = game.won ? 'text-success' : 'text-danger';
            const profitClass = game.profit >= 0 ? 'text-success' : 'text-danger';

            html += `<tr>
                <td>${gameIcon} ${game.game_type}</td>
                <td>${this.formatNumber(game.bet_amount)} GEM</td>
                <td class="${resultClass}">${game.won ? 'WIN' : 'LOSS'}</td>
                <td class="${profitClass}">${game.profit >= 0 ? '+' : ''}${this.formatNumber(game.profit)} GEM</td>
                <td><small>${this.formatTimeAgo(new Date(game.played_at))}</small></td>
            </tr>`;
        });

        html += '</tbody></table></div>';
        container.innerHTML = html;
    }

    showGame(gameType) {
        const token = localStorage.getItem('auth_token');
        if (!token) {
            window.location.href = '/login?redirect=/minigames';
            return;
        }

        this.currentGame = gameType;
        document.getElementById('game-area').style.display = 'block';
        document.getElementById('result-area').style.display = 'none';

        const titles = {
            'coinflip': '🪙 Coin Flip',
            'dice': '🎲 Dice Roll',
            'higherlower': '🃏 Higher or Lower'
        };

        document.getElementById('game-title').textContent = titles[gameType];

        if (gameType === 'coinflip') this.renderCoinFlip();
        else if (gameType === 'dice') this.renderDice();
        else if (gameType === 'higherlower') this.renderHigherLower();

        window.scrollTo({ top: document.getElementById('game-area').offsetTop - 100, behavior: 'smooth' });
    }

    renderCoinFlip() {
        document.getElementById('game-content').innerHTML = `
            <div class="text-center mb-4">
                <h5 class="mb-3">Choose Your Side</h5>
                <div class="d-flex gap-3">
                    <button class="btn-modern btn-modern-primary choice-btn" onclick="MiniGames.playCoinFlip('heads')">
                        <div style="font-size: 2rem;">🪙</div>
                        <div class="mt-2">HEADS</div>
                    </button>
                    <button class="btn-modern btn-modern-success choice-btn" onclick="MiniGames.playCoinFlip('tails')">
                        <div style="font-size: 2rem;">🪙</div>
                        <div class="mt-2">TAILS</div>
                    </button>
                </div>
            </div>
        `;
    }

    renderDice() {
        document.getElementById('game-content').innerHTML = `
            <div class="mb-4">
                <h5 class="mb-3">Choose Your Bet</h5>
                <div class="row g-3">
                    ${[1,2,3,4,5,6].map(n => `
                        <div class="col-6 col-md-4">
                            <div class="dice-option" onclick="MiniGames.playDice('exact', ${n})">
                                <div style="font-size: 2rem; text-align: center;">${n}</div>
                                <div class="text-center mt-2"><small>6x payout</small></div>
                            </div>
                        </div>
                    `).join('')}
                    <div class="col-6 col-md-3">
                        <div class="dice-option" onclick="MiniGames.playDice('even', null)">
                            <div class="text-center"><strong>EVEN</strong></div>
                            <div class="text-center mt-2"><small>2x payout</small></div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="dice-option" onclick="MiniGames.playDice('odd', null)">
                            <div class="text-center"><strong>ODD</strong></div>
                            <div class="text-center mt-2"><small>2x payout</small></div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="dice-option" onclick="MiniGames.playDice('high', null)">
                            <div class="text-center"><strong>HIGH (4-6)</strong></div>
                            <div class="text-center mt-2"><small>2x payout</small></div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="dice-option" onclick="MiniGames.playDice('low', null)">
                            <div class="text-center"><strong>LOW (1-3)</strong></div>
                            <div class="text-center mt-2"><small>2x payout</small></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderHigherLower() {
        document.getElementById('game-content').innerHTML = `
            <div class="text-center mb-4">
                <h5 class="mb-3">Will the next card be higher, lower, or the same?</h5>
                <div class="d-flex gap-3 justify-content-center">
                    <button class="btn-modern btn-modern-success choice-btn" onclick="MiniGames.playHigherLower('higher')">
                        <div style="font-size: 2rem;">⬆️</div>
                        <div class="mt-2">HIGHER (2x)</div>
                    </button>
                    <button class="btn-modern btn-modern-warning choice-btn" onclick="MiniGames.playHigherLower('same')">
                        <div style="font-size: 2rem;">↔️</div>
                        <div class="mt-2">SAME (5x)</div>
                    </button>
                    <button class="btn-modern btn-modern-danger choice-btn" onclick="MiniGames.playHigherLower('lower')">
                        <div style="font-size: 2rem;">⬇️</div>
                        <div class="mt-2">LOWER (2x)</div>
                    </button>
                </div>
            </div>
        `;
    }

    async playCoinFlip(choice) {
        const betAmount = parseInt(document.getElementById('bet-amount').value);
        if (betAmount < 100 || betAmount > 100000) {
            this.showError('Bet must be between 100 and 100,000 GEM');
            return;
        }

        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('/api/minigames/coinflip', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ bet_amount: betAmount, choice: choice })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Game failed');

            this.showResult(data.result, data.message);
            await this.loadBalance();
            await this.loadStats();
            await this.loadHistory();

        } catch (error) {
            this.showError(error.message);
        }
    }

    async playDice(betType, betValue) {
        const betAmount = parseInt(document.getElementById('bet-amount').value);
        if (betAmount < 100 || betAmount > 100000) {
            this.showError('Bet must be between 100 and 100,000 GEM');
            return;
        }

        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('/api/minigames/dice', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ bet_amount: betAmount, bet_type: betType, bet_value: betValue })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Game failed');

            this.showResult(data.result, data.message);
            await this.loadBalance();
            await this.loadStats();
            await this.loadHistory();

        } catch (error) {
            this.showError(error.message);
        }
    }

    async playHigherLower(guess) {
        const betAmount = parseInt(document.getElementById('bet-amount').value);
        if (betAmount < 100 || betAmount > 100000) {
            this.showError('Bet must be between 100 and 100,000 GEM');
            return;
        }

        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('/api/minigames/higherlower', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ bet_amount: betAmount, guess: guess })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Game failed');

            this.showResult(data.result, data.message);
            await this.loadBalance();
            await this.loadStats();
            await this.loadHistory();

        } catch (error) {
            this.showError(error.message);
        }
    }

    showResult(result, message) {
        const resultArea = document.getElementById('result-area');
        const resultClass = result.won ? 'result-win' : 'result-lose';

        let gameDetails = '';
        if (this.currentGame === 'coinflip') {
            gameDetails = `You chose <strong>${result.choice}</strong><br>Result: <strong>${result.result}</strong>`;
        } else if (this.currentGame === 'dice') {
            gameDetails = `You bet <strong>${result.bet_type}${result.bet_value ? ' '+result.bet_value : ''}</strong><br>Rolled: <strong>${result.roll}</strong>`;
        } else if (this.currentGame === 'higherlower') {
            gameDetails = `Card 1: <strong>${result.card1}</strong> → Card 2: <strong>${result.card2}</strong><br>You guessed: <strong>${result.guess}</strong>`;
        }

        resultArea.innerHTML = `
            <div class="result-display ${resultClass}">
                <div style="font-size: 3rem;">${result.won ? '🎉' : '💔'}</div>
                <h4 class="mt-3">${result.won ? 'YOU WON!' : 'YOU LOST'}</h4>
                <div class="mt-3">${gameDetails}</div>
                <div class="mt-3" style="font-size: 1.5rem; color: var(--gem);">
                    ${result.won ? '+' : ''}${this.formatNumber(result.profit)} GEM
                </div>
                <div class="mt-2"><small>New Balance: ${this.formatNumber(result.new_balance)} GEM</small></div>
                <button class="btn-modern btn-modern-primary mt-4" onclick="MiniGames.showGame('${this.currentGame}')">
                    Play Again
                </button>
            </div>
        `;
        resultArea.style.display = 'block';
        window.scrollTo({ top: resultArea.offsetTop - 100, behavior: 'smooth' });
    }

    closeGame() {
        document.getElementById('game-area').style.display = 'none';
        this.currentGame = null;
    }

    formatNumber(num) {
        return new Intl.NumberFormat('en-US').format(num);
    }

    formatTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        if (seconds < 60) return `${seconds}s ago`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        return `${Math.floor(seconds / 86400)}d ago`;
    }

    showError(message) {
        if (window.Toast) {
            Toast.error(message);
        } else if (window.showAlert) {
            window.showAlert(message, 'danger');
        } else {
            console.error('[ERROR]', message);
        }
    }
}

const MiniGames = new MiniGamesManager();
