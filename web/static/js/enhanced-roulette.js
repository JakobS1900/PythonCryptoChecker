/**
 * Enhanced CS:GO-Style Roulette Game
 * Professional crypto roulette with real-time WebSocket integration
 */

// Constants for Roulette Game
const NUMS = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26];
const RED_NUMBERS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
const BLACK_NUMBERS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35];
const ROLL_TIME = 6; // seconds
const BET_TIME = 20; // seconds
const MIN_BET = 10;
const MAX_BET = 10000;

class EnhancedRouletteGame {
    constructor() {
        this.gameState = 'connecting';
        this.currentBetAmount = MIN_BET;
        this.selectedNumbers = [];
        this.activeBets = [];
        this.currentPosition = 0;
        this.isRolling = false;
        this.isMuted = false;
        this.isConnected = false;
        this.websocket = null;
        this.roomStats = {};
        this.userBalance = 1000; // Default balance
        
        this.init();
    }

    async init() {
        this.createWheelSegments();
        this.setupEventListeners();
        await this.loadUserSession();
        this.updateBetAmountDisplay();
        this.setupBettingInterface();
        console.log('Enhanced roulette game initialized');
    }

    createWheelSegments() {
        const wheelsHolder = document.getElementById('wheelsHolder');
        if (!wheelsHolder) return;

        // Create multiple wheel sections for seamless animation
        const wheels = [1, 2, 3, 4, 5, 6, 7, 8, 9];
        const html = wheels.map(() => {
            return `<div class='wheel'>${
                NUMS.map(num => {
                    const colorClass = this.getColorClass(num);
                    return `<div class='${colorClass} chunk'><span>${num}</span></div>`;
                }).join('')
            }</div>`;
        }).join('');
        
        wheelsHolder.innerHTML = html;
    }

    getColorClass(number) {
        if (number === 0) return 'green-number';
        if (RED_NUMBERS.includes(number)) return 'red-number';
        if (BLACK_NUMBERS.includes(number)) return 'black-number';
        return 'black-number';
    }

    setupEventListeners() {
        // Bet amount buttons
        document.querySelectorAll('.bet-amount-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.currentBetAmount = parseInt(e.target.dataset.amount) || MIN_BET;
                this.updateBetAmountDisplay();
            });
        });

        // Number betting
        document.querySelectorAll('.number-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const number = parseInt(e.target.dataset.number);
                this.placeBet('number', number);
            });
        });

        // Color betting
        document.querySelectorAll('.color-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const color = e.target.dataset.color;
                this.placeBet('color', color);
            });
        });

        // Category betting
        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const category = e.target.dataset.category;
                this.placeBet('category', category);
            });
        });

        // Traditional betting
        document.querySelectorAll('.traditional-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const type = e.target.dataset.type;
                this.placeBet('traditional', type);
            });
        });

        // Spin button
        const spinBtn = document.getElementById('spin-btn');
        if (spinBtn) {
            spinBtn.addEventListener('click', () => this.requestSpin());
        }

        // Clear bets button
        const clearBtn = document.getElementById('clear-bets');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearAllBets());
        }

        // Repeat last bet button
        const repeatBtn = document.getElementById('repeat-last');
        if (repeatBtn) {
            repeatBtn.addEventListener('click', () => this.repeatLastBet());
        }

        // Mute button
        const muteBtn = document.getElementById('mute-btn');
        if (muteBtn) {
            muteBtn.addEventListener('click', () => this.toggleMute());
        }
    }

    updateBetAmountDisplay() {
        const display = document.getElementById('bet-amount-display');
        if (display) {
            display.textContent = `${this.currentBetAmount} GEM`;
        }
        
        // Update active bet amount buttons
        document.querySelectorAll('.bet-amount-btn').forEach(btn => {
            btn.classList.remove('active');
            if (parseInt(btn.dataset.amount) === this.currentBetAmount) {
                btn.classList.add('active');
            }
        });
    }

    getBetNumber() {
        return this.selectedNumbers.length > 0 ? this.selectedNumbers[0] : null;
    }

    async placeBet(betType, betValue) {
        if (this.gameState !== 'betting') {
            this.showNotification('Betting is currently closed', 'warning');
            return;
        }

        if (this.currentBetAmount < MIN_BET || this.currentBetAmount > MAX_BET) {
            this.showNotification(`Bet amount must be between ${MIN_BET} and ${MAX_BET} GEM`, 'error');
            return;
        }

        if (this.userBalance < this.currentBetAmount) {
            this.showNotification('Insufficient balance', 'error');
            return;
        }

        try {
            const response = await fetch('/api/gaming/roulette/place_bet', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
                },
                body: JSON.stringify({
                    bet_type: betType,
                    bet_value: betValue,
                    amount: this.currentBetAmount
                })
            });

            const result = await response.json();
            
            if (response.ok) {
                this.handleBetPlaced(result);
                this.addVisualBetFeedback(betType, betValue);
            } else {
                this.showNotification(result.error || 'Failed to place bet', 'error');
            }
        } catch (error) {
            console.error('Bet placement error:', error);
            this.showNotification('Network error while placing bet', 'error');
        }
    }

    handleBetPlaced(result) {
        // Add bet to active bets
        this.activeBets.push({
            type: result.bet_type,
            value: result.bet_value,
            amount: result.amount,
            potential_win: result.potential_payout,
            id: result.bet_id
        });

        // Update balance
        this.userBalance = result.new_balance;
        this.updateBalanceDisplay();
        
        // Update bet display
        this.updateBetDisplay();
        
        this.showNotification('Bet placed successfully!', 'success');
    }

    addVisualBetFeedback(betType, betValue) {
        // Find the clicked element and add visual feedback
        let element;
        if (betType === 'number') {
            element = document.querySelector(`[data-number="${betValue}"]`);
        } else if (betType === 'color') {
            element = document.querySelector(`[data-color="${betValue}"]`);
        } else if (betType === 'category') {
            element = document.querySelector(`[data-category="${betValue}"]`);
        } else if (betType === 'traditional') {
            element = document.querySelector(`[data-type="${betValue}"]`);
        }

        if (element) {
            element.classList.add('bet-placed');
            
            // Create floating chip animation
            const floatingChip = document.createElement('div');
            floatingChip.className = 'floating-chip';
            floatingChip.textContent = `${this.currentBetAmount}`;
            
            const rect = element.getBoundingClientRect();
            floatingChip.style.left = `${rect.left + rect.width/2}px`;
            floatingChip.style.top = `${rect.top}px`;
            
            document.body.appendChild(floatingChip);
            
            // Remove animation element after animation completes
            setTimeout(() => {
                if (floatingChip.parentNode) {
                    floatingChip.parentNode.removeChild(floatingChip);
                }
            }, 1500);
        }
    }

    clearAllBets() {
        this.activeBets.forEach(bet => {
            const element = document.querySelector(`[data-number="${bet.value}"], [data-color="${bet.value}"], [data-category="${bet.value}"], [data-type="${bet.value}"]`);
            if (element) {
                element.classList.remove('bet-placed');
            }
        });
        
        this.activeBets = [];
        this.selectedNumbers = [];
        this.updateBetDisplay();
        this.showNotification('All bets cleared', 'info');
    }

    repeatLastBet() {
        // Implementation for repeating the last bet
        this.showNotification('Repeat last bet functionality coming soon', 'info');
    }

    updateBalanceDisplay() {
        const balanceElement = document.getElementById('user-balance');
        if (balanceElement) {
            balanceElement.textContent = `${this.userBalance.toFixed(2)} GEM`;
        }
    }

    async requestSpin() {
        if (this.gameState !== 'betting') {
            this.showNotification('Cannot spin at this time', 'warning');
            return;
        }

        if (this.activeBets.length === 0) {
            this.showNotification('Place at least one bet to spin', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/gaming/roulette/spin', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
                }
            });

            const result = await response.json();
            
            if (response.ok) {
                this.handleSpinResult(result);
            } else {
                this.showNotification(result.error || 'Failed to spin wheel', 'error');
            }
        } catch (error) {
            console.error('Spin request error:', error);
            this.showNotification('Network error during spin', 'error');
        }
    }

    handleSpinResult(result) {
        this.gameState = 'spinning';
        this.spinToNumber(result.winning_number);
        
        // Show result after animation
        setTimeout(() => {
            this.showGameResult(result);
            this.gameState = 'betting';
        }, ROLL_TIME * 1000 + 1000);
    }

    spinToNumber(winningNumber) {
        const wheelsHolder = document.getElementById('wheelsHolder');
        if (!wheelsHolder) return;

        const currentBox = NUMS.indexOf(this.currentPosition);
        const nextBox = NUMS.indexOf(winningNumber);
        
        // Calculate the shortest path to the winning number
        const boxShift = currentBox > nextBox 
            ? NUMS.length - currentBox + nextBox 
            : nextBox - currentBox;

        // Get current offset
        let currentOffset = parseInt(wheelsHolder.style.transform?.replace('matrix(1, 0, 0, 1, ', '')?.split(",")[0] || '0');
        
        // Calculate next position
        const itemWidth = 70;
        const wheelVariation = -(15 * itemWidth) * (Math.floor(Math.random() * 3) + 3);
        const boxVariation = Math.random() * itemWidth - itemWidth/2;
        const offset = currentOffset + boxShift * -itemWidth + wheelVariation + boxVariation;

        // Apply animation
        wheelsHolder.style.transform = `matrix(1, 0, 0, 1, ${offset}, 0)`;
        wheelsHolder.style.transitionDuration = `${ROLL_TIME}s`;
        wheelsHolder.style.transitionTimingFunction = 'cubic-bezier(0.25, 0.46, 0.45, 0.94)';

        this.currentPosition = winningNumber;
        this.isRolling = true;

        // Add spinning effects
        const wheelContainer = document.querySelector('.roulette-wheel-container');
        if (wheelContainer) {
            wheelContainer.classList.add('spinning-effects');
            setTimeout(() => {
                wheelContainer.classList.remove('spinning-effects');
            }, ROLL_TIME * 1000);
        }

        // Highlight winning segment
        setTimeout(() => {
            const winningSegment = document.querySelector(`.chunk:nth-child(${nextBox + 1})`);
            if (winningSegment) {
                winningSegment.classList.add('winning-segment');
                setTimeout(() => {
                    winningSegment.classList.remove('winning-segment');
                }, 2000);
            }
        }, ROLL_TIME * 1000);

        this.playSound('/static/sounds/wheel-spin.mp3');
    }

    showGameResult(result) {
        const { winning_number, payouts, total_payout, server_seed, client_seed, nonce } = result;
        
        // Update balance
        this.userBalance = result.new_balance || this.userBalance;
        this.updateBalanceDisplay();

        // Update last numbers display
        this.updateLastNumbers(winning_number);

        // Show result modal
        const totalWin = total_payout || 0;
        const resultContent = `
            <div class="result-info">
                <h3>Winning Number: <span class="${this.getColorClass(winning_number)}">${winning_number}</span></h3>
                <h4>Total Win: ${totalWin} GEM</h4>
                ${payouts ? payouts.map(p => `
                    <div class="payout-item">
                        <div>Bet: ${p.bet_type} ${p.bet_value}</div>
                        <div>Win: ${p.amount} GEM</div>
                    </div>
                `).join('') : ''}
                <div class="provably-fair">
                    <h5>Provably Fair Verification:</h5>
                    <small>Server Seed: ${server_seed || 'N/A'}</small><br>
                    <small>Client Seed: ${client_seed || 'N/A'}</small><br>
                    <small>Nonce: ${nonce || 'N/A'}</small>
                </div>
            </div>
        `;

        this.showModal('Game Result', resultContent);

        // Clear bets and reset
        this.clearAllBets();
        this.playSound('/static/sounds/result.mp3');
    }

    updateLastNumbers(newNumber) {
        const container = document.getElementById('last-numbers');
        if (!container) return;

        // Get current numbers
        let lastNumbers = JSON.parse(localStorage.getItem('roulette_last_numbers') || '[]');
        
        // Add new number to front
        lastNumbers.unshift(newNumber);
        
        // Keep only last 10 numbers
        lastNumbers = lastNumbers.slice(0, 10);
        
        // Save to localStorage
        localStorage.setItem('roulette_last_numbers', JSON.stringify(lastNumbers));

        // Update display
        container.innerHTML = `
            <h5>Previous Rolls:</h5>
            <div class="numbers-display">
                ${lastNumbers.map(num => `<span class="number-chip ${this.getColorClass(num)}">${num}</span>`).join('')}
            </div>
        `;
    }

    updateBetDisplay() {
        const container = document.getElementById('active-bets');
        if (!container) return;

        if (this.activeBets.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-3">No active bets</div>';
            return;
        }

        container.innerHTML = this.activeBets.map(bet => `
            <div class="bet-item">
                <div class="bet-type">${bet.type}</div>
                <div class="bet-value">${bet.value}</div>
                <div class="bet-amount">${bet.amount} GEM</div>
                <div class="potential-win">Potential Win: ${bet.potential_win} GEM</div>
            </div>
        `).join('');

        // Update total bet amount
        const totalBet = this.activeBets.reduce((sum, bet) => sum + bet.amount, 0);
        const totalElement = document.getElementById('total-bet-amount');
        if (totalElement) {
            totalElement.textContent = `${totalBet} GEM`;
        }
    }

    setupBettingInterface() {
        // Set up countdown timer if available
        this.startBettingCountdown();
    }

    startBettingCountdown() {
        const bar = document.getElementById('betting-bar');
        const timeText = document.getElementById('betting-time');
        
        if (!bar || !timeText) return;

        let timeLeft = BET_TIME;
        bar.style.width = '100%';
        
        const interval = setInterval(() => {
            timeLeft--;
            const percentage = (timeLeft / BET_TIME) * 100;
            bar.style.width = percentage + '%';
            timeText.textContent = `${timeLeft}s`;
            
            if (timeLeft <= 0) {
                clearInterval(interval);
                this.gameState = 'spinning';
                this.showNotification('Betting closed - spinning wheel', 'info');
                // Automatically start new betting round after 10 seconds
                setTimeout(() => {
                    this.gameState = 'betting';
                    this.startBettingCountdown();
                }, 10000);
            }
        }, 1000);
    }

    playSound(src) {
        if (this.isMuted) return;
        
        try {
            const audio = new Audio(src);
            audio.volume = 0.3;
            audio.play().catch(console.warn);
        } catch (error) {
            console.warn('Audio playback failed:', error);
        }
    }

    toggleMute() {
        this.isMuted = !this.isMuted;
        const muteBtn = document.getElementById('mute-btn');
        if (muteBtn) {
            muteBtn.innerHTML = this.isMuted ? '<i class="fas fa-volume-mute"></i>' : '<i class="fas fa-volume-up"></i>';
        }
        this.showNotification(this.isMuted ? 'Sound muted' : 'Sound enabled', 'info');
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;

        // Add to page
        document.body.appendChild(notification);
        setTimeout(() => notification.classList.add('show'), 100);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    showModal(title, content) {
        // Simple modal implementation
        const modal = document.createElement('div');
        modal.className = 'game-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="close-btn">&times;</button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Close button functionality
        const closeBtn = modal.querySelector('.close-btn');
        closeBtn.addEventListener('click', () => {
            document.body.removeChild(modal);
        });

        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });

        setTimeout(() => modal.classList.add('show'), 100);
    }

    async loadUserSession() {
        try {
            // Try to load user session and connect to WebSocket
            const sessionId = window?.ROULETTE_SESSION_ID || 'demo-session';
            const token = localStorage.getItem('access_token') || 'demo-token';
            
            if (sessionId && token) {
                await this.connectWebSocket(sessionId, token);
                this.gameState = 'betting';
            } else {
                // Demo mode
                this.gameState = 'betting';
            }
        } catch (e) {
            console.warn('Session load failed:', e);
            this.gameState = 'betting';
        }
    }
    
    async connectWebSocket(sessionId, token) {
        try {
            const wsUrl = `ws://localhost:8000/ws/roulette/${sessionId}?token=${token}`;
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.isConnected = true;
                this.showNotification('Connected to game room', 'success');
                console.log('WebSocket connected to roulette game');
            };
            
            this.websocket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleWebSocketMessage(message);
            };
            
            this.websocket.onclose = () => {
                this.isConnected = false;
                this.showNotification('Disconnected from game room', 'warning');
                console.log('WebSocket disconnected');
                
                // Attempt to reconnect after 5 seconds
                setTimeout(() => this.connectWebSocket(sessionId, token), 5000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.showNotification('Connection error', 'error');
            };
            
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
            this.showNotification('Failed to connect to game room', 'error');
        }
    }
    
    handleWebSocketMessage(message) {
        switch (message.type) {
            case 'room_state':
                this.updateRoomState(message);
                break;
                
            case 'user_joined':
                this.handleUserJoined(message);
                break;
                
            case 'user_left':
                this.handleUserLeft(message);
                break;
                
            case 'live_bet_placed':
                this.handleLiveBetPlaced(message);
                break;
                
            case 'betting_closed':
                this.handleBettingClosed(message);
                break;
                
            case 'wheel_spinning':
                this.handleWheelSpinning(message);
                break;
                
            case 'game_results':
                this.handleGameResults(message);
                break;
                
            case 'chat_message':
                this.handleChatMessage(message);
                break;
                
            case 'personal_result':
                this.handlePersonalResult(message);
                break;
                
            case 'bet_confirmed':
                this.handleBetConfirmed(message);
                break;
                
            case 'bet_error':
                this.handleBetError(message);
                break;
                
            default:
                console.log('Unknown WebSocket message:', message);
        }
    }

    updateRoomState(message) {
        // Update room statistics if available
        if (message.stats) {
            this.roomStats = message.stats;
        }
    }

    handleUserJoined(message) {
        this.showNotification(`${message.username} joined the game`, 'info');
    }

    handleUserLeft(message) {
        this.showNotification(`${message.username} left the game`, 'info');
    }

    handleLiveBetPlaced(message) {
        const bet = message.bet;
        this.addLiveBetToFeed(bet);
        this.updateRoomStats(message.room_stats);
    }

    handleBettingClosed(message) {
        this.gameState = 'spinning';
        this.showNotification('Betting closed - wheel spinning!', 'warning');
    }

    handleWheelSpinning(message) {
        this.gameState = 'spinning';
        if (message.winning_number) {
            this.spinToNumber(message.winning_number);
        }
    }

    handleGameResults(message) {
        if (message.winning_number) {
            this.showGameResult(message);
        }
        // Reset for next round after a delay
        setTimeout(() => { this.gameState = 'betting'; }, 3000);
    }

    handleChatMessage(message) {
        const list = document.getElementById('chat-messages');
        if (!list) return;
        const item = document.createElement('div');
        const time = new Date(message.timestamp || Date.now()).toLocaleTimeString();
        item.className = 'chat-message';
        item.innerHTML = `<span class="chat-time">${time}</span> <strong>${message.username || 'User'}:</strong> ${message.text}`;
        list.appendChild(item);
        list.scrollTop = list.scrollHeight;
    }

    handlePersonalResult(message) {
        if (message.payout != null) {
            const payout = Number(message.payout);
            if (!isNaN(payout)) {
                this.showNotification(`Round result: ${payout > 0 ? '+' : ''}${payout} GEM`, payout > 0 ? 'success' : 'info');
            }
        }
    }

    handleBetConfirmed(message) {
        this.showNotification('Bet confirmed', 'success');
    }

    handleBetError(message) {
        this.showNotification(message.error || 'Bet error', 'error');
    }

    updateRoomStats(stats) {
        this.roomStats = stats || this.roomStats;
        // Could update a stats panel if present
    }

    addLiveBetToFeed(bet) {
        const feedList = document.getElementById('live-bets-list');
        if (!feedList) return;
        
        const betElement = document.createElement('div');
        betElement.className = 'live-bet-item';
        betElement.innerHTML = `
            <div class="bet-info">
                <span class="bet-amount">${bet.bet_amount} GEM</span>
                <span class="bet-details">${bet.bet_type}: ${bet.bet_value}</span>
            </div>
            <div class="bet-time">${new Date(bet.timestamp).toLocaleTimeString()}</div>
        `;
        
        // Add with animation
        betElement.style.animationDelay = `${bet.animation_delay || 0}ms`;
        feedList.insertBefore(betElement, feedList.firstChild);
        
        // Remove old bets (keep last 20)
        while (feedList.children.length > 20) {
            feedList.removeChild(feedList.lastChild);
        }
    }
}

// Initialize enhanced roulette interface when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.rouletteGame = new EnhancedRouletteGame();
    console.log('Enhanced CS:GO roulette system initialized with full functionality');
});