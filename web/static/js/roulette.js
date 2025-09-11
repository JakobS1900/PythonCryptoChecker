class RouletteGame {
    constructor() {
        // Game constants
        this.ROLL_TIME = 6; // seconds
        this.BET_TIME = 20; // seconds
        this.MIN_BET = 10;
        this.MAX_BET = 10000;
        this.NUMBERS = Array.from({length: 37}, (_, i) => i); // 0-36
        
        // Game state
        this.currentBets = [];
        this.isSpinning = false;
        this.currentAmount = 10;
        this.balance = parseInt(document.getElementById('user-balance').textContent);
        
        // Audio
        this.sounds = {
            start: new Audio('/static/sounds/start.mp3'),
            finish: new Audio('/static/sounds/finish.wav')
        };
        this.isMuted = false;
        
        // Initialize the game
        this.initializeSocket();
        this.setupEventListeners();
        this.generateNumberGrid();
        this.startNewRound();
    }
    
    initializeSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to server');
        });
        
        this.socket.on('timer', (data) => {
            this.updateTimer(data.timeLeft);
        });
        
        this.socket.on('spin_result', (data) => {
            this.spinWheel(data.number);
            this.processResults(data);
        });
        
        this.socket.on('balance_update', (data) => {
            this.updateBalance(data.balance);
        });
    }
    
    setupEventListeners() {
        // Amount buttons
        document.querySelectorAll('.amount-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.currentAmount = parseInt(btn.dataset.amount);
                document.getElementById('betAmount').value = this.currentAmount;
            });
        });
        
        // Custom amount input
        const betInput = document.getElementById('betAmount');
        betInput.addEventListener('change', () => {
            this.currentAmount = Math.min(Math.max(betInput.value, this.MIN_BET), this.MAX_BET);
            betInput.value = this.currentAmount;
        });
        
        // Betting buttons
        document.querySelectorAll('.bet-btn').forEach(btn => {
            btn.addEventListener('click', () => this.placeBet(btn.dataset.type, btn.dataset.value));
        });
        
        // Action buttons
        document.getElementById('clearBets').addEventListener('click', () => this.clearBets());
        document.getElementById('spinWheel').addEventListener('click', () => this.requestSpin());
        
        // Quick bet controls
        document.getElementById('halfBtn').addEventListener('click', () => this.modifyBetAmount(0.5));
        document.getElementById('doubleBtn').addEventListener('click', () => this.modifyBetAmount(2));
        document.getElementById('maxBtn').addEventListener('click', () => this.setBetToMax());
    }
    
    generateNumberGrid() {
        const grid = document.querySelector('.number-grid');
        if (!grid) return;
        
        this.NUMBERS.forEach(num => {
            if (num === 0) return; // Handle zero separately
            const btn = document.createElement('button');
            btn.className = 'number-btn ' + this.getNumberClass(num);
            btn.dataset.type = 'number';
            btn.dataset.value = num;
            btn.textContent = num;
            btn.addEventListener('click', () => this.placeBet('number', num));
            grid.appendChild(btn);
        });
        
        // Add zero button separately
        const zeroBtn = document.createElement('button');
        zeroBtn.className = 'number-btn green';
        zeroBtn.dataset.type = 'number';
        zeroBtn.dataset.value = 0;
        zeroBtn.textContent = '0';
        zeroBtn.addEventListener('click', () => this.placeBet('number', 0));
        grid.insertBefore(zeroBtn, grid.firstChild);
    }
    
    getNumberClass(num) {
        if (num === 0) return 'green';
        return num % 2 === 0 ? 'black' : 'red';
    }
    
    placeBet(type, value) {
        if (this.isSpinning) {
            this.showNotification('Betting is closed', 'error');
            return;
        }
        
        if (this.currentAmount > this.balance) {
            this.showNotification('Insufficient balance', 'error');
            return;
        }
        
        const bet = {
            type,
            value,
            amount: this.currentAmount,
            multiplier: this.getBetMultiplier(type)
        };
        
        this.currentBets.push(bet);
        this.updateBetsDisplay();
        this.showNotification(`Bet placed: ${this.currentAmount} on ${value}`, 'success');
    }
    
    getBetMultiplier(type) {
        switch (type) {
            case 'number': return 35;
            case 'color': return value === 'green' ? 14 : 2;
            case 'parity':
            case 'range': return 2;
            default: return 2;
        }
    }
    
    updateBetsDisplay() {
        const list = document.getElementById('betsList');
        const totalBet = document.getElementById('totalBet');
        const potentialWin = document.getElementById('potentialWin');
        
        if (!list || !totalBet || !potentialWin) return;
        
        list.innerHTML = '';
        let total = 0;
        let maxWin = 0;
        
        this.currentBets.forEach((bet, index) => {
            total += bet.amount;
            maxWin += bet.amount * bet.multiplier;
            
            const item = document.createElement('div');
            item.className = 'bet-item';
            item.innerHTML = `
                <span>${bet.value} (${bet.multiplier}×)</span>
                <span>${bet.amount} GEM</span>
                <button class="remove-bet" onclick="game.removeBet(${index})">×</button>
            `;
            list.appendChild(item);
        });
        
        totalBet.textContent = `${total} GEM`;
        potentialWin.textContent = `${maxWin} GEM`;
    }
    
    removeBet(index) {
        this.currentBets.splice(index, 1);
        this.updateBetsDisplay();
    }
    
    clearBets() {
        this.currentBets = [];
        this.updateBetsDisplay();
        this.showNotification('All bets cleared', 'info');
    }
    
    requestSpin() {
        if (this.currentBets.length === 0) {
            this.showNotification('Place at least one bet', 'warning');
            return;
        }
        
        this.socket.emit('place_bets', {
            bets: this.currentBets
        });
    }
    
    spinWheel(number) {
        this.isSpinning = true;
        const wheel = document.getElementById('wheelNumbers');
        if (!wheel) return;
        
        // Play spin sound
        if (!this.isMuted) {
            this.sounds.start.play();
        }
        
        // Calculate spin parameters
        const finalPosition = this.calculateSpinPosition(number);
        wheel.style.transform = `translateX(${finalPosition}px)`;
        
        // Reset after animation
        setTimeout(() => {
            if (!this.isMuted) {
                this.sounds.finish.play();
            }
            this.isSpinning = false;
            this.addToHistory(number);
        }, this.ROLL_TIME * 1000);
    }
    
    calculateSpinPosition(number) {
        // Implementation will depend on your wheel layout
        // This is a placeholder calculation
        return -(number * 70 + Math.random() * 20);
    }
    
    addToHistory(number) {
        const history = document.querySelector('.rolls-history');
        if (!history) return;
        
        const item = document.createElement('div');
        item.className = `history-item ${this.getNumberClass(number)}`;
        item.textContent = number;
        
        if (history.children.length >= 10) {
            history.removeChild(history.lastChild);
        }
        history.insertBefore(item, history.firstChild);
    }
    
    updateTimer(seconds) {
        const timer = document.querySelector('.timer-text');
        const progress = document.querySelector('.timer-progress');
        if (!timer || !progress) return;
        
        timer.textContent = `${seconds.toFixed(1)}s`;
        progress.style.width = `${(seconds / this.BET_TIME) * 100}%`;
    }
    
    updateBalance(newBalance) {
        this.balance = newBalance;
        const display = document.getElementById('balanceAmount');
        if (display) {
            display.textContent = `${newBalance} GEM`;
        }
    }
    
    modifyBetAmount(multiplier) {
        const input = document.getElementById('betAmount');
        if (!input) return;
        
        this.currentAmount = Math.min(
            Math.max(Math.floor(this.currentAmount * multiplier), this.MIN_BET),
            this.MAX_BET
        );
        input.value = this.currentAmount;
    }
    
    setBetToMax() {
        const input = document.getElementById('betAmount');
        if (!input) return;
        
        this.currentAmount = Math.min(this.balance, this.MAX_BET);
        input.value = this.currentAmount;
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    startNewRound() {
        this.isSpinning = false;
        this.currentBets = [];
        this.updateBetsDisplay();
        this.updateTimer(this.BET_TIME);
    }
}

// Initialize the game when the document is ready
document.addEventListener('DOMContentLoaded', () => {
    window.game = new RouletteGame();
});
