/**
 * Crash Game Client
 * WebSocket-based real-time multiplayer crash game
 */

class CrashGameManager {
    constructor() {
        this.ws = null;
        this.gameState = 'connecting';
        this.currentMultiplier = 1.00;
        this.userBet = null;
        this.activeBets = new Map();
        this.gameHistory = [];
        this.userBalance = 0;
    }

    async init() {
        console.log('[Crash] Initializing...');

        // Check authentication
        // Check authentication (optional for viewing/guest play)
        const token = localStorage.getItem('auth_token');
        if (!token) {
            console.log('[Crash] No auth token found, initializing as Guest/Viewer');
        }

        // Load balance
        await this.loadBalance();

        // Connect WebSocket
        this.connectWebSocket();

        // Load history
        await this.loadHistory();

        console.log('[Crash] Ready!');
    }

    connectWebSocket() {
        // WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/crash/ws`;

        console.log('[Crash] Connecting to WebSocket...');

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('[Crash] WebSocket connected');
            this.updateStatus('Connected');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.ws.onerror = (error) => {
            console.error('[Crash] WebSocket error:', error);
            this.updateStatus('Connection Error');
        };

        this.ws.onclose = () => {
            console.log('[Crash] WebSocket closed, reconnecting...');
            this.updateStatus('Reconnecting...');

            // Reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }

    handleWebSocketMessage(data) {
        console.log('[Crash] Message:', data);

        switch (data.type) {
            case 'connection_established':
                this.handleConnectionEstablished(data.current_state);
                break;
            case 'game_state':
                this.handleGameState(data);
                break;
            case 'game_started':
                this.handleGameStarted(data);
                break;
            case 'multiplier_update':
                this.handleMultiplierUpdate(data);
                break;
            case 'bet_placed':
                this.handleBetPlaced(data);
                break;
            case 'cashout':
                this.handleCashout(data);
                break;
            case 'game_crashed':
                this.handleGameCrashed(data);
                break;
        }
    }

    handleConnectionEstablished(state) {
        console.log('[Crash] Current state:', state);

        if (state.status === 'waiting') {
            this.gameState = 'waiting';
            this.updateStatus('Place Your Bets!');
            this.enableBetting();
        } else if (state.status === 'playing') {
            this.gameState = 'playing';
            this.currentMultiplier = state.multiplier || 1.00;
            this.updateMultiplierDisplay();
            this.updateStatus('Game in Progress');
        } else if (state.status === 'idle') {
            this.gameState = 'idle';
            this.updateStatus('Waiting for players...');
            this.disableBetting();
        }

        if (state.server_seed_hash) {
            document.getElementById('seed-hash').textContent = state.server_seed_hash.substring(0, 16) + '...';
        }
    }

    handleGameState(data) {
        this.gameState = data.status;

        if (data.status === 'waiting') {
            this.updateStatus('Place Your Bets!');
            this.currentMultiplier = 1.00;
            this.updateMultiplierDisplay();
            this.enableBetting();
            this.activeBets.clear();
            this.updatePlayersList();
        } else if (data.status === 'starting') {
            this.updateStatus('Starting...');
            this.disableBetting();
        } else if (data.status === 'idle') {
            this.updateStatus('Waiting for players...');
            this.disableBetting();
        }

        if (data.server_seed_hash) {
            document.getElementById('seed-hash').textContent = data.server_seed_hash.substring(0, 16) + '...';
        }
    }

    handleGameStarted(data) {
        this.gameState = 'playing';
        this.currentMultiplier = 1.00;
        this.updateStatus('🚀 Flying!');
        this.disableBetting();

        // If user has bet, show cashout button
        if (this.userBet) {
            this.showCashoutButton();
        }
    }

    handleMultiplierUpdate(data) {
        this.currentMultiplier = data.multiplier;
        this.updateMultiplierDisplay();

        // Update potential payout if user has bet
        if (this.userBet) {
            const potentialPayout = Math.floor(this.userBet * this.currentMultiplier);
            document.getElementById('potential-payout').style.display = 'block';
            document.getElementById('potential-payout').querySelector('span').textContent = potentialPayout.toLocaleString();
        }
    }

    handleBetPlaced(data) {
        // Add bet to active bets
        this.activeBets.set(data.username, {
            username: data.username,
            bet_amount: data.bet_amount,
            status: 'active'
        });

        this.updatePlayersList();
    }

    handleCashout(data) {
        // Update bet status
        const bet = this.activeBets.get(data.username);
        if (bet) {
            bet.status = 'cashed_out';
            bet.cashout_at = data.multiplier;
            bet.payout = data.payout;
            this.activeBets.set(data.username, bet);
            this.updatePlayersList();
        }
    }

    handleGameCrashed(data) {
        this.gameState = 'crashed';
        this.currentMultiplier = data.crash_point;
        this.updateStatus(`💥 Crashed at ${data.crash_point.toFixed(2)}x`);
        this.updateMultiplierDisplay(true);

        // Hide cashout button
        this.hideCashoutButton();

        // Clear user bet
        this.userBet = null;
        document.getElementById('potential-payout').style.display = 'none';

        // Add to history
        this.gameHistory.unshift(data.crash_point);
        if (this.gameHistory.length > 20) {
            this.gameHistory.pop();
        }
        this.updateHistoryDisplay();

        // Load updated balance
        setTimeout(() => this.loadBalance(), 1000);
    }

    async placeBet() {
        const betAmount = parseInt(document.getElementById('bet-amount').value);

        if (!betAmount || betAmount < 100) {
            this.showNotification('error', 'Minimum bet is 100 GEM');
            return;
        }

        if (betAmount > 100000) {
            this.showNotification('error', 'Maximum bet is 100,000 GEM');
            return;
        }

        console.log('[Crash] placeBet check: betAmount=', betAmount, 'userBalance=', this.userBalance, 'type=', typeof this.userBalance);

        if (betAmount > this.userBalance) {
            this.showNotification('error', `Insufficient balance (Bet: ${betAmount}, Have: ${this.userBalance})`);
            return;
        }

        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('/api/crash/bet', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ bet_amount: betAmount })
            });

            const data = await response.json();

            if (data.success) {
                this.userBet = betAmount;
                this.userBalance = data.new_balance;
                document.getElementById('user-balance').textContent = this.userBalance.toLocaleString();
                this.showNotification('success', data.message);
                this.disableBetting();
            } else {
                this.showNotification('error', data.message);
            }

        } catch (error) {
            console.error('[Crash] Error placing bet:', error);
            this.showNotification('error', 'Failed to place bet');
        }
    }

    async cashout() {
        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('/api/crash/cashout', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                this.userBalance = data.new_balance;
                document.getElementById('user-balance').textContent = this.userBalance.toLocaleString();
                this.showNotification('success', `${data.message} - Profit: ${data.profit.toLocaleString()} GEM`);
                this.hideCashoutButton();
                this.userBet = null;
                document.getElementById('potential-payout').style.display = 'none';
            } else {
                this.showNotification('error', data.message);
            }

        } catch (error) {
            console.error('[Crash] Error cashing out:', error);
            this.showNotification('error', 'Failed to cash out');
        }
    }

    async loadBalance() {
        // Try to get balance from global App state first (synced by auth.js)
        if (window.App && window.App.user && window.App.user.wallet_balance !== undefined) {
            console.log('[Crash] Using global App.user balance:', window.App.user.wallet_balance);
            this.userBalance = window.App.user.wallet_balance;
            const balanceEl = document.getElementById('user-balance');
            if (balanceEl) balanceEl.textContent = this.userBalance.toLocaleString();
            return;
        }

        console.log('[Crash] App.user not ready, falling back to API...');

        const token = localStorage.getItem('auth_token');
        if (!token) {
            console.log('[Crash] No token for balance load, user is guest');
            this.userBalance = 0;
            return;
        }

        try {
            console.log('[Crash] Fetching balance from API (/api/auth/me)...');
            const response = await fetch('/api/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) throw new Error('Failed to fetch user data');

            const data = await response.json();
            // API returns wallet_balance, frontend was looking for gem_balance
            this.userBalance = data.wallet_balance !== undefined ? data.wallet_balance : (data.gem_balance || 0);
            console.log('[Crash] Balance loaded from API:', this.userBalance);

            const balanceEl = document.getElementById('user-balance');
            if (balanceEl) balanceEl.textContent = this.userBalance.toLocaleString();

        } catch (error) {
            console.error('[Crash] Error loading balance:', error);
        }
    }

    async loadHistory() {
        try {
            const response = await fetch('/api/crash/history?limit=20');
            const data = await response.json();

            if (data.success && data.games) {
                this.gameHistory = data.games.map(g => g.crash_point);
                this.updateHistoryDisplay();
            }

        } catch (error) {
            console.error('[Crash] Error loading history:', error);
        }
    }

    updateMultiplierDisplay(crashed = false) {
        const display = document.getElementById('multiplier');
        display.textContent = `${this.currentMultiplier.toFixed(2)}x`;

        if (crashed) {
            display.classList.add('crashed');
            setTimeout(() => display.classList.remove('crashed'), 500);
        }

        // Color based on multiplier
        if (this.currentMultiplier < 2) {
            display.style.color = '#fff';
        } else if (this.currentMultiplier < 5) {
            display.style.color = '#f59e0b';
        } else {
            display.style.color = '#10b981';
        }
    }

    updateStatus(text) {
        const status = document.getElementById('game-status');
        status.textContent = text;

        // Update class
        status.classList.remove('waiting', 'playing', 'crashed');

        if (text.includes('Bet')) {
            status.classList.add('waiting');
        } else if (text.includes('Flying') || text.includes('Progress')) {
            status.classList.add('playing');
        } else if (text.includes('Crashed')) {
            status.classList.add('crashed');
        }
    }

    enableBetting() {
        const betBtn = document.getElementById('bet-btn');
        betBtn.disabled = false;
        betBtn.textContent = 'Place Bet';
    }

    disableBetting() {
        const betBtn = document.getElementById('bet-btn');
        betBtn.disabled = true;
        betBtn.textContent = 'Betting Closed';
    }

    showCashoutButton() {
        document.getElementById('cashout-btn').classList.add('active');
    }

    hideCashoutButton() {
        document.getElementById('cashout-btn').classList.remove('active');
    }

    updatePlayersList() {
        const container = document.getElementById('players-grid');

        if (this.activeBets.size === 0) {
            container.innerHTML = '<p class="text-secondary">No active bets</p>';
            return;
        }

        let html = '';
        this.activeBets.forEach((bet) => {
            const cashedOut = bet.status === 'cashed_out';

            html += `
                <div class="player-card ${cashedOut ? 'cashed-out' : ''}">
                    <div class="player-name">${bet.username}</div>
                    <div class="player-bet">Bet: ${bet.bet_amount.toLocaleString()} GEM</div>
                    ${cashedOut ? `
                        <div class="player-profit">
                            Cashed out at ${bet.cashout_at.toFixed(2)}x
                            <br>+${bet.payout.toLocaleString()} GEM
                        </div>
                    ` : `
                        <div class="text-secondary">Waiting...</div>
                    `}
                </div>
            `;
        });

        container.innerHTML = html;
    }

    updateHistoryDisplay() {
        const container = document.getElementById('history-row');

        if (this.gameHistory.length === 0) {
            container.innerHTML = '<span class="text-secondary">No history yet</span>';
            return;
        }

        let html = '';
        this.gameHistory.forEach((crashPoint) => {
            let className = 'low';
            if (crashPoint >= 2 && crashPoint < 10) className = 'medium';
            if (crashPoint >= 10) className = 'high';

            html += `<span class="history-item ${className}">${crashPoint.toFixed(2)}x</span>`;
        });

        container.innerHTML = html;
    }

    // Bet amount helpers
    setBet(amount) {
        document.getElementById('bet-amount').value = amount;
    }

    doubleBet() {
        const current = parseInt(document.getElementById('bet-amount').value) || 100;
        const doubled = Math.min(current * 2, 100000);
        document.getElementById('bet-amount').value = doubled;
    }

    halveBet() {
        const current = parseInt(document.getElementById('bet-amount').value) || 100;
        const halved = Math.max(Math.floor(current / 2), 100);
        document.getElementById('bet-amount').value = halved;
    }

    async maxBet() {
        // Ensure we have latest balance - try multiple sources
        let balance = this.userBalance;

        // If userBalance is 0 or undefined, try to get from App.user
        if (!balance && window.App && window.App.user) {
            balance = window.App.user.wallet_balance || 0;
            this.userBalance = balance;
            console.log('[Crash] maxBet: Using App.user balance:', balance);
        }

        // If still 0, reload from API
        if (!balance) {
            await this.loadBalance();
            balance = this.userBalance;
            console.log('[Crash] maxBet: Reloaded from API:', balance);
        }

        const maxAllowed = Math.min(balance, 100000);
        document.getElementById('bet-amount').value = maxAllowed > 0 ? Math.floor(maxAllowed) : 100;
        console.log('[Crash] maxBet set to:', maxAllowed);
    }

    minBet() {
        document.getElementById('bet-amount').value = 100;
    }

    showNotification(type, message) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: ${type === 'success' ? 'var(--success)' : 'var(--error)'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        notification.innerHTML = `
            <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            ${message}
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Create global instance
const CrashGame = new CrashGameManager();
