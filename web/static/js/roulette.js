class RouletteGame {
    constructor() {
        this.MIN_BET = 10;
        this.MAX_BET = 10000;
        this.ROUND_DURATION = 20000; // milliseconds
        this.SPIN_ANIMATION_MS = 6000;

        this.gameId = null;
        this.balance = 0;
        this.currentAmount = 100;
        this.currentBets = [];
        this.pendingBets = []; // New: confirmation queue
        this.isProcessing = false;
        this.isSpinning = false;
        this.roundTimer = null;

        // Auto-betting system
        this.bettingStrategy = 'manual'; // 'manual', 'martingale', 'fibonacci'
        this.autoBetEnabled = false;
        this.autoBetRoundsLeft = 0;
        this.autoBetTarget = 1000; // Profit target
        this.autoBetMaxLoss = 500; // Stop loss
        this.baseBet = 100; // Original bet amount
        this.strategyStep = 0; // Current step in progression
        this.sessionProfit = 0; // Track profit for the session
        this.sessionRounds = 0;

        // Social & Live Features
        this.liveBetFeed = [];
        this.betFeedInterval = null;

        // Funny random name system
        this.namePrefixes = ['Bob', 'Joe', 'Sally', 'Mike', 'Linda', 'Dave', 'Karen', 'Steve', 'Betty', 'Frank', 'Helen', 'George'];
        this.nameSuffixes = ['Bob', 'Joe', 'Sally', 'Mike', 'Linda', 'Dave', 'Karen', 'Steve', 'Betty', 'Frank', 'Helen', 'George'];
        this.nameWords = ['Bread', 'Cheese', 'Dog', 'Cat', 'Tree', 'Rock', 'Car', 'House', 'Chair', 'Table', 'Phone', 'Computer'];

        // Avatar system
        this.playerAvatars = [
            '🐕', '🐈', '🐄', '🐖', '🐑', '🦆', '🐔', '🦉', '🦋', '🐝',
            '🍕', '🍔', '🍟', '🌭', '🍿', '🥨', '🍪', '🎂', '🍰', '🧁',
            '🚗', '🚕', '🚙', '🚌', '🚎', '🏎️', '🚓', '🚑', '🚒', '🚐',
            '👨', '👩', '👴', '👵', '🧑', '👨‍💼', '👩‍💼', '👨‍🔬', '👩‍🔬', '👨‍🍳'
        ];

        // Achievement System
        this.achievements = {
            firstWin: false,
            consecutiveWins5: false,
            bigBet: false,
            profit1000: false,
            spins100: false
        };
        this.consecutiveWins = 0;
        this.totalRounds = 0;
        this.biggestBet = 0;

        this.elements = {};

        this.init();
    }

    async init() {
        this.cacheElements();
        this.bindEventListeners();
        this.generateNumberGrid();
        this.syncInitialBalance();
        this.updateBetAmountDisplay();
        this.updateBetSummary();

        try {
            await this.ensureGameSession();
        } catch (error) {
            console.error('Failed to create roulette session', error);
            this.showNotification('Unable to create game session. Using demo mode.', 'error');
        }

        this.startNewRound();
        window.addEventListener('balanceUpdated', (event) => {
            const { detail } = event;
            if (!detail) {
                return;
            }
            if (typeof detail.balance === 'number') {
                this.setBalance(detail.balance, { source: detail.source || 'external' });
            }
        });

        window.rouletteGame = this;
        console.log('RouletteGame ready');
    }

    cacheElements() {
        const $ = (selector) => document.querySelector(selector);
        const $$ = (selector) => Array.from(document.querySelectorAll(selector));

        this.elements = {
            chips: $$('.chip-btn'),
            betInput: $('#betAmount'),
            betButtons: $$('.bet-btn'),
            numberGrid: $('.number-grid'),
            betsList: $('#betsList'),
            totalBet: $('#totalBet'),
            potentialWin: $('#potentialWin'),
            spinButton: $('#spinWheel'),
            clearButton: $('#clearBets'),
            halfButton: $('#halfBtn'),
            doubleButton: $('#doubleBtn'),
            maxButton: $('#maxBtn'),
            availableBalance: $('#available-balance'),
            gamingBalance: $('#gaming-balance'),
            roundIndicator: $('#round-number'),
            timerText: document.getElementById('timer-text'),
            timerBar: document.getElementById('timer-progress'),
            previousRolls: document.getElementById('previous-rolls')
        };
    }

    bindEventListeners() {
        this.elements.chips.forEach((chip) => {
            chip.addEventListener('click', () => {
                const amount = parseInt(chip.dataset.amount, 10);
                if (Number.isFinite(amount)) {
                    this.setCurrentAmount(amount);
                }
            });
        });

        if (this.elements.betInput) {
            this.elements.betInput.addEventListener('change', () => {
                const value = parseInt(this.elements.betInput.value, 10);
                if (Number.isFinite(value)) {
                    this.setCurrentAmount(value, { updateInput: false });
                }
                this.updateBetAmountDisplay();
            });

            this.elements.betInput.addEventListener('blur', () => {
                this.updateBetAmountDisplay();
            });
        }

        this.elements.betButtons.forEach((button) => {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                if (button.disabled) {
                    return;
                }
                const { type, value } = button.dataset;
                if (!type || value === undefined) {
                    return;
                }
                this.handleBet(type, value, button);
            });

            // Add visual feedback when clicking bet positions
            button.addEventListener('mousedown', (event) => {
                if (button.disabled) {
                    return;
                }
                button.classList.add('bet-highlighted');
            });

            button.addEventListener('mouseup', (event) => {
                button.classList.remove('bet-highlighted');
            });

            button.addEventListener('mouseleave', (event) => {
                button.classList.remove('bet-highlighted');
            });
        });

        if (this.elements.numberGrid) {
            this.elements.numberGrid.addEventListener('click', (event) => {
                const target = event.target.closest('.number-btn');
                if (!target || target.disabled) {
                    return;
                }
                const value = target.dataset.value;
                this.handleBet('number', value, target);
            });
        }

        this.elements.clearButton?.addEventListener('click', () => {
            this.clearBets();
        });

        this.elements.spinButton?.addEventListener('click', () => {
            this.requestSpin();
        });

        this.elements.halfButton?.addEventListener('click', () => {
            this.modifyBetAmount(0.5);
        });

        this.elements.doubleButton?.addEventListener('click', () => {
            this.modifyBetAmount(2);
        });

        this.elements.maxButton?.addEventListener('click', () => {
            this.setBetToMax();
        });

        // Auto-betting event listeners
        const toggleAutoBetBtn = document.getElementById('toggleAutoBet');
        const autoBetControls = document.getElementById('autoBetControls');
        const startAutoBetBtn = document.getElementById('startAutoBet');
        const stopAutoBetBtn = document.getElementById('stopAutoBet');

        if (toggleAutoBetBtn && autoBetControls) {
            toggleAutoBetBtn.addEventListener('click', () => {
                const isVisible = autoBetControls.style.display !== 'none';
                autoBetControls.style.display = isVisible ? 'none' : 'block';
                toggleAutoBetBtn.textContent = isVisible ? '🤖 Auto-Bet' : '❌ Hide Auto-Bet';
            });
        }

        if (startAutoBetBtn) {
            startAutoBetBtn.addEventListener('click', () => {
                this.handleStartAutoBet();
            });
        }

        if (stopAutoBetBtn) {
            stopAutoBetBtn.addEventListener('click', () => {
                this.stopAutoBet('Manual stop');
            });
        }

        // Update auto-bet UI when state changes
        this.updateAutoBetUI();
    }

    generateNumberGrid() {
        if (!this.elements.numberGrid) {
            return;
        }

        const numbers = Array.from({ length: 37 }, (_, index) => index);
        const fragment = document.createDocumentFragment();

        numbers.forEach((number) => {
            const button = document.createElement('button');
            button.className = `number-btn ${this.getNumberClass(number)}`;
            button.dataset.type = 'number';
            button.dataset.value = String(number);
            button.textContent = String(number);
            fragment.appendChild(button);
        });

        this.elements.numberGrid.innerHTML = '';
        this.elements.numberGrid.appendChild(fragment);
    }

    getNumberClass(number) {
        if (number === 0) {
            return 'green';
        }
        const redNumbers = new Set([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]);
        return redNumbers.has(number) ? 'red' : 'black';
    }

    syncInitialBalance() {
        if (window.Auth && window.Auth.currentUser && typeof window.Auth.currentUser.wallet_balance === 'number') {
            this.setBalance(window.Auth.currentUser.wallet_balance, { source: 'auth' });
            return;
        }
        if (window.App && window.App.user && typeof window.App.user.wallet_balance === 'number') {
            this.setBalance(window.App.user.wallet_balance, { source: 'app' });
            return;
        }
        this.setBalance(5000, { source: 'guest-default' });
    }

    setBalance(amount, { source } = {}) {
        const numeric = Number(amount);
        if (!Number.isFinite(numeric)) {
            return;
        }
        const oldBalance = this.balance;
        const change = numeric - oldBalance;
        this.balance = Math.max(0, numeric);

        // Animate balance change if it's a significant update
        if (oldBalance !== this.balance && Math.abs(change) > 0) {
            this.animateBalanceChange(change, source);
        }

        this.updateBalanceDisplay();
        if (this.elements.availableBalance) {
            this.elements.availableBalance.textContent = this.formatAmount(this.balance);
        }
        if (source !== 'roulette') {
            this.updateBetAmountDisplay();
        }

        // Broadcast balance change to other components when balance actually changes
        if (oldBalance !== this.balance) {
            console.log(`🎰 Roulette balance updated: ${oldBalance} → ${this.balance} GEM (source: ${source})`);
            document.dispatchEvent(new CustomEvent('balanceUpdated', {
                detail: {
                    balance: this.balance,
                    source: 'roulette',
                    change: change
                }
            }));

            // Update Auth module balance immediately
            if (window.Auth && window.Auth.currentUser) {
                window.Auth.currentUser.wallet_balance = this.balance;
                if (source === 'roulette') {
                    window.Auth.updateUserInterface();
                }
            }
        }
    }

    updateBalanceDisplay() {
        if (this.elements.gamingBalance) {
            this.elements.gamingBalance.textContent = `${this.formatAmount(this.balance)} GEM`;
        }
    }

    setCurrentAmount(amount, { updateInput = true } = {}) {
        const numeric = Math.floor(Number(amount));
        if (!Number.isFinite(numeric)) {
            return;
        }
        const clamped = Math.min(Math.max(numeric, this.MIN_BET), this.MAX_BET);
        this.currentAmount = clamped;
        if (updateInput && this.elements.betInput) {
            this.elements.betInput.value = String(clamped);
        }
        this.highlightActiveChip(clamped);
    }

    highlightActiveChip(amount) {
        this.elements.chips.forEach((chip) => {
            const chipAmount = parseInt(chip.dataset.amount, 10);
            chip.classList.toggle('active', chipAmount === amount);
        });
    }

    updateBetAmountDisplay() {
        this.setCurrentAmount(this.currentAmount, { updateInput: true });
        if (this.elements.betInput) {
            this.elements.betInput.value = String(this.currentAmount);
        }
    }

    modifyBetAmount(multiplier) {
        const next = Math.round(this.currentAmount * multiplier);
        this.setCurrentAmount(next);
    }

    setBetToMax() {
        const target = Math.min(this.balance, this.MAX_BET);
        this.setCurrentAmount(target);
    }

    async ensureGameSession() {
        if (this.gameId) {
            return;
        }
        const response = await this.postJson('/api/gaming/roulette/create', {});
        if (response && response.game_id) {
            this.gameId = response.game_id;
            console.log('Roulette session created', this.gameId);
        }
    }

    async handleBet(type, rawValue, sourceButton) {
        if (this.isProcessing || this.currentBets.length > 0) {
            return;
        }

        const amount = this.currentAmount;
        // Check balance server-side instead of local balance
        try {
            const validation = await this.fetch('/api/gaming/validate-bet?amount=' + encodeURIComponent(amount));
            if (!validation.valid) {
                this.showNotification(validation.message, 'error');
                // Refresh balance to show current amount
                await this.refreshBalanceFromServer();
                return;
            }
        } catch (error) {
            this.showNotification('Unable to validate balance. Please refresh the page.', 'error');
            return;
        }

        const betData = {
            type: this.normalizeBetType(type),
            value: String(rawValue).toLowerCase(),
            amount,
            source: sourceButton
        };

        // Add to pending queue for confirmation
        this.addToPendingBets(betData);
        this.showNotification(`${amount} GEM bet on ${this.formatBetLabel(betData)} added. Confirm to place order.`, 'info');

        // Auto-confirm after 2 seconds if not manually confirmed
        setTimeout(() => {
            this.confirmPendingBet();
        }, 2000);
    }

    addToPendingBets(betData) {
        // Only allow one pending bet at a time
        this.pendingBets = [betData];

        // Highlight the bet button to show it's pending
        if (betData.source) {
            betData.source.classList.add('bet-pending');
        }

        // Update UI to show pending bet
        this.updatePendingBetDisplay();
    }

    async confirmPendingBet() {
        if (this.pendingBets.length === 0 || this.isProcessing) {
            return;
        }

        const betData = this.pendingBets[0];
        this.isProcessing = true;

        try {
            // Remove highlight immediately
            if (betData.source) {
                betData.source.classList.remove('bet-pending', 'bet-highlighted');
            }

            await this.ensureGameSession();
            if (!this.gameId) {
                this.showNotification('Game session unavailable.', 'error');
                this.clearPendingBets();
                return;
            }

            const betPayload = {
                bet_type: betData.type,
                bet_value: betData.value,
                amount: betData.amount
            };

            const response = await this.postJson(`/api/gaming/roulette/${this.gameId}/bet`, betPayload);
            if (response && response.success) {
                this.registerBet({
                    type: betPayload.bet_type,
                    value: betPayload.bet_value,
                    amount: betData.amount,
                    betId: response.bet_id || crypto.randomUUID()
                });

                // Sync balance from server after successful bet placement
                await this.refreshBalanceFromServer();

                this.showNotification(`Bet confirmed: ${betData.amount} GEM on ${this.formatBetLabel(betData)}`, 'success');
                this.updateSpinButtonState(); // Enable spin button when bets are active
            } else {
                const message = response?.error || response?.message || 'Failed to place bet.';
                this.showNotification(message, 'error');

                // Refresh balance on bet failure to ensure UI is in sync
                await this.refreshBalanceFromServer();
            }
        } catch (error) {
            console.error('Bet confirmation error', error);
            this.showNotification('Error confirming bet. Please try again.', 'error');
        } finally {
            this.clearPendingBets();
            this.isProcessing = false;
        }
    }

    clearPendingBets() {
        this.pendingBets.forEach(bet => {
            if (bet.source) {
                bet.source.classList.remove('bet-pending', 'bet-highlighted');
            }
        });
        this.pendingBets = [];
        this.updatePendingBetDisplay();
    }

    updatePendingBetDisplay() {
        // Visual feedback for pending bets - could add UI indicator here
        const hasPendingBets = this.pendingBets.length > 0;
        document.body.classList.toggle('has-pending-bets', hasPendingBets);
    }

    normalizeBetType(type) {
        switch (String(type).toLowerCase()) {
            case 'number':
            case 'single_number':
                return 'SINGLE_NUMBER';
            case 'color':
                return 'RED_BLACK';
            case 'parity':
                return 'EVEN_ODD';
            case 'range':
                return 'HIGH_LOW';
            case 'crypto_category':
                return 'CRYPTO_CATEGORY';
            default:
                return String(type).toUpperCase();
        }
    }

    registerBet(bet) {
        this.currentBets.push(bet);
        this.updateBetSummary();
        this.updateSpinButtonState();
    }

    updateBetSummary() {
        if (!this.elements.betsList || !this.elements.totalBet || !this.elements.potentialWin) {
            return;
        }

        this.elements.betsList.innerHTML = '';
        if (this.currentBets.length === 0) {
            this.elements.betsList.innerHTML = '<p class="empty-state">No bets placed yet.</p>';
        } else {
            const fragment = document.createDocumentFragment();
            this.currentBets.forEach((bet, index) => {
                const item = document.createElement('div');
                item.className = 'bet-item';
                item.innerHTML = `
                    <span class="bet-label">${this.formatBetLabel(bet)}</span>
                    <span class="bet-amount">${this.formatAmount(bet.amount)} GEM</span>
                    <button class="remove-bet" aria-label="Remove bet">
                        <i class="bi bi-x"></i>
                    </button>
                `;
                item.querySelector('.remove-bet').addEventListener('click', () => {
                    this.removeBet(index);
                });
                fragment.appendChild(item);
            });
            this.elements.betsList.appendChild(fragment);
        }

        const total = this.currentBets.reduce((acc, bet) => acc + bet.amount, 0);
        const potential = this.currentBets.reduce((acc, bet) => acc + (bet.amount * this.getPayoutMultiplier(bet.type, bet.value)), 0);

        this.elements.totalBet.textContent = `${this.formatAmount(total)} GEM`;
        this.elements.potentialWin.textContent = `${this.formatAmount(potential)} GEM`;
    }

    removeBet(index) {
        const [removed] = this.currentBets.splice(index, 1);
        if (removed) {
            this.setBalance(this.balance + removed.amount, { source: 'roulette' });
        }
        this.updateBetSummary();
    }

    clearBets() {
        if (this.currentBets.length === 0) {
            return;
        }
        const refund = this.currentBets.reduce((acc, bet) => acc + bet.amount, 0);
        this.currentBets = [];
        this.setBalance(this.balance + refund, { source: 'roulette' });
        this.updateBetSummary();
        this.showNotification('All bets cleared.', 'info');
    }

    async requestSpin() {
        if (this.isSpinning) {
            return;
        }
        if (this.currentBets.length === 0) {
            this.showNotification('Place a bet before spinning.', 'warning');
            return;
        }
        await this.ensureGameSession();
        if (!this.gameId) {
            this.showNotification('Game session unavailable.', 'error');
            return;
        }

        this.isSpinning = true;
        this.elements.spinButton?.classList.add('processing');

        try {
            const response = await this.postJson(`/api/gaming/roulette/${this.gameId}/spin`, {});
            if (response && response.success) {
                this.handleSpinResult(response);
            } else {
                const message = response?.error || 'Spin failed.';
                this.showNotification(message, 'error');
            }
        } catch (error) {
            console.error('Spin error', error);
            this.showNotification('Error spinning the wheel.', 'error');
        } finally {
            this.isSpinning = false;
            this.elements.spinButton?.classList.remove('processing');
        }
    }

    async handleSpinResult(result) {
        const outcome = result?.result;
        if (outcome && typeof outcome.number === 'number') {
            this.animateWheel(outcome.number);
            this.updateHistory(outcome.number, outcome.color || 'red');
        }

        // Update session statistics and auto-betting logic
        this.sessionRounds++;

        // Show detailed win/lose notifications based on individual bets
        const bets = result?.bets || [];
        let totalWinnings = 0;
        let totalLosses = 0;
        let winningBets = 0;

        bets.forEach(bet => {
            if (bet.is_winner && bet.payout > 0) {
                winningBets++;
                totalWinnings += bet.payout;
            } else {
                totalLosses += bet.amount;
            }
        });

        // Update session profit
        this.sessionProfit += totalWinnings - totalLosses;

        // Update achievements
        this.updateAchievements(totalWinnings, totalLosses);

        // Handle auto-betting progression
        if (this.autoBetEnabled && totalWinnings === 0) { // Loss occurred
            this.handleAutoBetLoss();
        } else if (this.autoBetEnabled && totalWinnings > 0) { // Win occurred
            this.handleAutoBetWin();
        }

        // Check auto-bet stop conditions
        if (this.autoBetEnabled) {
            if (this.shouldStopAutoBet()) {
                this.stopAutoBet();
            } else if (this.autoBetRoundsLeft > 0) {
                this.autoBetRoundsLeft--;
                if (this.autoBetRoundsLeft === 0) {
                    this.stopAutoBet();
                }
            }
        }

        // Sync balance from server after spin results
        await this.refreshBalanceFromServer();

    // Show persistent result notification first - instant feedback
    this.showPersistentResult(totalWinnings > 0, totalWinnings > 0 ? totalWinnings : totalLosses);

    // Show flashy casino-style result overlay with delay for maximum impact
    if (totalWinnings > 0) {
        const multiplier = bets.find(b => b.is_winner)?.multiplier || 1;
        setTimeout(() => {
            this.showCasinoStyleResult('win', {
                winnings: totalWinnings,
                multiplier: multiplier,
                number: outcome?.number || '0',
                crypto: outcome?.crypto || 'Unknown'
            });
        }, 1000); // Dramatic delay for wheel animation completion

        // Only show JACKPOT overlay for significant wins (>=100 GEM)
        if (totalWinnings >= 100) {
            setTimeout(() => {
                this.showWinNotification(totalWinnings, multiplier, winningBets);
            }, 1500);
        }
    } else {
        setTimeout(() => {
            this.showCasinoStyleResult('loss', {
                losses: totalLosses,
                number: outcome?.number || '0',
                crypto: outcome?.crypto || 'Unknown'
            });
        }, 1000); // Show after wheel animation
    }

        this.currentBets = [];
        this.updateBetSummary();
        this.updateSpinButtonState();
        this.startNewRound();
    }

    animateWheel(number) {
        const wheel = document.getElementById('wheelNumbers');
        const wheelContainer = document.querySelector('.wheel-container');
        const pointer = document.querySelector('.roulette-pointer');

        if (!wheel || !wheelContainer || !pointer) {
            console.warn('Roulette wheel elements not found, skipping animation');
            return;
        }

        // Create speed indicator if it doesn't exist
        let speedIndicator = document.querySelector('.speed-indicator');
        if (!speedIndicator) {
            speedIndicator = document.createElement('div');
            speedIndicator.className = 'speed-indicator';
            speedIndicator.innerHTML = '<div class="speed-bar"></div><span class="speed-text">RPM</span>';
            wheelContainer.appendChild(speedIndicator);

            // Add CSS for speed indicator
            if (!document.querySelector('#speed-indicator-styles')) {
                const style = document.createElement('style');
                style.id = 'speed-indicator-styles';
                style.textContent = `
                    .speed-indicator {
                        position: absolute;
                        top: 20px;
                        right: 20px;
                        width: 60px;
                        height: 60px;
                        border-radius: 50%;
                        background: rgba(0, 0, 0, 0.7);
                        border: 2px solid rgba(251, 191, 36, 0.5);
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        z-index: 10;
                        opacity: 0;
                        transform: scale(0.8);
                        transition: all 0.3s ease;
                    }
                    .speed-indicator.active {
                        opacity: 1;
                        transform: scale(1);
                    }
                    .speed-bar {
                        width: 6px;
                        height: 20px;
                        background: linear-gradient(180deg, #fbbf24, #f97316);
                        border-radius: 3px;
                        margin-bottom: 2px;
                        transform-origin: bottom;
                    }
                    .speed-text {
                        font-size: 0.7rem;
                        color: #fbbf24;
                        font-weight: bold;
                    }
                `;
                document.head.appendChild(style);
            }
        }

        // Reset any existing animation and styles
        wheel.style.transition = 'none';
        wheel.style.transform = 'translateX(0)';
        wheel.style.filter = '';
        wheel.style.boxShadow = '';
        speedIndicator.classList.remove('active');

        // Multi-phase wheel animation with realistic physics and visual effects
        const segmentWidth = 70;
        const baseOffset = number * segmentWidth;
        // Add extra rotations for realistic spin (5-8 full rotations)
        const rotations = 5 + Math.random() * 3;
        const finalOffset = -(rotations * 37 * segmentWidth + baseOffset);

        let currentSpeed = 0;
        let phase = 1;

        // Phase 1: Fast initial spin with quick acceleration (0-2s)
        setTimeout(() => {
            phase = 1;
            speedIndicator.classList.add('active');
            const phase1Distance = finalOffset * 0.7;

            wheel.style.transition = 'transform 2s cubic-bezier(0.1, 0.8, 0.3, 1)';
            wheel.style.transform = `translateX(${phase1Distance}px)`;
            wheel.style.filter = 'blur(1px)';
            wheel.style.boxShadow = 'inset 0 0 20px rgba(251, 191, 36, 0.3)';

            // Animate speed indicator for phase 1
            let phase1Speed = 8000; // RPM
            const phase1Interval = setInterval(() => {
                if (phase !== 1) {
                    clearInterval(phase1Interval);
                    return;
                }
                phase1Speed = Math.max(2000, phase1Speed - 200);
                currentSpeed = phase1Speed;
                speedIndicator.querySelector('.speed-bar').style.transform = `scaleY(${Math.min(1, currentSpeed / 10000)})`;
            }, 100);

            // Phase 2: Gradual deceleration (2-4s)
            setTimeout(() => {
                phase = 2;
                const phase2Distance = finalOffset * 0.9;

                wheel.style.transition = 'transform 2s cubic-bezier(0.4, 0.0, 0.6, 0.3)';
                wheel.style.transform = `translateX(${phase2Distance}px)`;
                wheel.style.filter = 'blur(0.5px)';

                // Animate speed indicator for phase 2
                const phase2Interval = setInterval(() => {
                    if (phase !== 2) {
                        clearInterval(phase2Interval);
                        return;
                    }
                    phase1Speed = Math.max(500, phase1Speed - 50);
                    currentSpeed = phase1Speed;
                    speedIndicator.querySelector('.speed-bar').style.transform = `scaleY(${Math.min(1, currentSpeed / 10000)})`;
                }, 100);

                // Add streak effect during slow down
                wheelContainer.style.boxShadow = '0 0 30px rgba(251, 191, 36, 0.4)';

                // Phase 3: Slow final approach (4-5s)
                setTimeout(() => {
                    phase = 3;
                    wheel.style.transition = 'transform 1s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
                    wheel.style.transform = `translateX(${finalOffset}px)`;
                    wheel.style.filter = 'none';
                    wheel.style.boxShadow = '';
                    wheelContainer.style.boxShadow = '';

                    // Final highlight effect
                    setTimeout(() => {
                        // Highlight the winning number
                        const winningNumberElement = wheel.querySelector(`[data-value="${number}"]`);
                        if (winningNumberElement) {
                            winningNumberElement.style.animation = 'winningPulse 2s ease-in-out';
                            setTimeout(() => {
                                winningNumberElement.style.animation = '';
                            }, 2000);
                        }

                        // Final celebration effect
                        pointer.style.animation = 'pointerCelebration 1s ease-in-out';
                        setTimeout(() => {
                            pointer.style.animation = '';
                        }, 1000);

                        // Hide speed indicator
                        speedIndicator.classList.remove('active');
                    }, 1000);

                    // Clean up after animation completes
                    setTimeout(() => {
                        wheel.style.transition = '';
                        wheel.style.filter = '';
                        wheel.style.boxShadow = '';
                        wheelContainer.style.boxShadow = '';
                    }, 1100);
                }, 2000);
            }, 2000);
        }, 10); // Small delay to ensure transition reset

        // Add CSS animations for final effects
        if (!document.querySelector('#wheel-celebration-styles')) {
            const style = document.createElement('style');
            style.id = 'wheel-celebration-styles';
            style.textContent = `
                @keyframes pointerCelebration {
                    0%, 100% { transform: translateX(-1px); }
                    50% { transform: translateX(-1px) scale(1.2); box-shadow: 0 0 20px rgba(251, 191, 36, 0.8); }
                }
                @keyframes finalGlow {
                    0%, 100% {
                        box-shadow: 0 0 20px rgba(251, 191, 36, 0.5),
                                    inset 0 0 20px rgba(251, 191, 36, 0.2);
                    }
                    50% {
                        box-shadow: 0 0 40px rgba(251, 191, 36, 0.8),
                                    inset 0 0 40px rgba(251, 191, 36, 0.4);
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }

    updateHistory(number, color) {
        if (!this.elements.previousRolls) {
            return;
        }
        const entry = document.createElement('div');
        entry.className = `previous-roll ${color || 'red'}`;
        entry.textContent = String(number);
        this.elements.previousRolls.prepend(entry);
        while (this.elements.previousRolls.children.length > 10) {
            this.elements.previousRolls.removeChild(this.elements.previousRolls.lastElementChild);
        }
    }

    startNewRound() {
        if (this.roundTimer) {
            clearInterval(this.roundTimer);
        }
        const startTime = Date.now();
        this.updateRoundTimer(this.ROUND_DURATION);

        this.roundTimer = setInterval(() => {
            const elapsed = Date.now() - startTime;
            const remaining = Math.max(this.ROUND_DURATION - elapsed, 0);
            this.updateRoundTimer(remaining);

            // When countdown reaches 0, simply restart the timer (no auto-spin)
            if (remaining === 0) {
                clearInterval(this.roundTimer);
                this.roundTimer = null;
                this.startNewRound(); // Restart timer
            }
        }, 200);
    }

    updateRoundTimer(remainingMs) {
        if (!this.elements.timerText || !this.elements.timerBar) {
            return;
        }
        const seconds = Math.max(0, remainingMs / 1000);
        this.elements.timerText.textContent = `${seconds.toFixed(1)}s`;
        const percent = Math.min(100, Math.max(0, (remainingMs / this.ROUND_DURATION) * 100));
        this.elements.timerBar.style.width = `${percent}%`;
    }

    getPayoutMultiplier(type, value) {
        switch (type) {
            case 'SINGLE_NUMBER':
                return 35;
            case 'RED_BLACK':
                return value === 'green' ? 14 : 2;
            case 'EVEN_ODD':
            case 'HIGH_LOW':
                return 2;
            default:
                return 2;
        }
    }

    formatBetLabel(bet) {
        switch (bet.type) {
            case 'SINGLE_NUMBER':
                return `Number ${bet.value}`;
            case 'RED_BLACK':
                return `Color ${bet.value.toUpperCase()}`;
            case 'EVEN_ODD':
                return bet.value === 'even' ? 'Even' : 'Odd';
            case 'HIGH_LOW':
                return bet.value === 'low' ? '1-18' : '19-36';
            default:
                return `${bet.type} ${bet.value}`;
        }
    }

    formatAmount(value) {
        return Number(value).toLocaleString('en-US');
    }

    async refreshBalanceFromServer() {
        try {
            console.log('🔄 Refreshing roulette balance from server...');
            const response = await this.fetch('/api/auth/status');

            if (response && response.authenticated && response.user) {
                const serverBalance = response.user.wallet_balance;
                this.setBalance(serverBalance, { source: 'server-sync' });
                console.log(`✅ Server balance synced: ${serverBalance} GEM`);
                return serverBalance;
            } else if (response && response.guest_mode && response.guest_user) {
                const serverBalance = response.guest_user.wallet_balance;
                this.setBalance(serverBalance, { source: 'server-sync' });
                console.log(`✅ Guest server balance synced: ${serverBalance} GEM`);
                return serverBalance;
            }

            console.warn('⚠️ No balance data in server response');
            return null;
        } catch (error) {
            console.error('❌ Failed to refresh balance from server:', error);
            // Fall back to Auth module if available
            if (window.Auth && typeof window.Auth.refreshBalanceGlobally === 'function') {
                try {
                    return await window.Auth.refreshBalanceGlobally();
                } catch (authError) {
                    console.error('❌ Auth module sync also failed:', authError);
                }
            }
            return null;
        }
    }

    updateSpinButtonState() {
        if (!this.elements.spinButton) {
            return;
        }

        const hasBets = this.currentBets.length > 0;
        const isSpinning = this.isSpinning;

        this.elements.spinButton.disabled = !hasBets || isSpinning;
        this.elements.spinButton.textContent = isSpinning ? 'SPINNING...' : 'SPIN TO WIN';
    }

    async fetch(url) {
        const headers = {};
        const token = localStorage.getItem('auth_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        const response = await fetch(url, { method: 'GET', headers });
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || `Request failed with status ${response.status}`);
        }
        return response.json();
    }

    async postJson(url, payload) {
        const headers = { 'Content-Type': 'application/json' };
        const token = localStorage.getItem('auth_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        const response = await fetch(url, {
            method: 'POST',
            headers,
            body: JSON.stringify(payload)
        });
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || `Request failed with status ${response.status}`);
        }
        return response.json();
    }

    showWinNotification(amount, multiplier, betCount = 1) {
        const message = `🎉 BIG WIN! +${this.formatAmount(amount)} GEM (${multiplier}x payout)`;
        this.showNotification(message, 'success');

        // Also trigger win animation overlay
        this.showWinOverlay(amount, multiplier);
    }

    showLossNotification(amount, crypto, number) {
        const message = `💔 Lost ${this.formatAmount(amount)} GEM - ${crypto} (${number})`;
        this.showNotification(message, 'error');
    }

    showWinOverlay(amount, multiplier) {
        // Create a quick celebration overlay
        let overlay = document.querySelector('.win-celebration-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'win-celebration-overlay';
            overlay.innerHTML = `
                <div class="win-firework">🎆</div>
                <div class="win-text">JACKPOT!</div>
                <div class="win-amount">+${this.formatAmount(amount)} GEM</div>
            `;
            document.body.appendChild(overlay);
        }

        // Show animation
        overlay.classList.add('active');
        setTimeout(() => {
            overlay.classList.remove('active');
        }, 3000);
    }

    showResultModal(resultType, data) {
        // Create modal container if it doesn't exist
        let modal = document.querySelector('.result-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.className = 'result-modal game-modal';
            modal.innerHTML = `
                <div class="modal-content result-modal-content">
                    <div class="modal-header">
                        <h3 id="result-title"></h3>
                        <button class="close-btn" onclick="this.closest('.result-modal').classList.remove('show')">
                            <i class="bi bi-x"></i>
                        </button>
                    </div>
                    <div class="result-content">
                        <div class="result-icon" id="result-icon"></div>
                        <div class="result-amount" id="result-amount"></div>
                        <div class="result-details" id="result-details"></div>
                        <button class="continue-btn" onclick="this.closest('.result-modal').classList.remove('show'); window.rouletteGame?.startNewRound?.()">
                            Continue Playing
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            // Add styles for the result modal
            const style = document.createElement('style');
            style.textContent = `
                .result-modal-content {
                    max-width: 450px;
                }
                .result-content {
                    text-align: center;
                    padding: 20px 0;
                }
                .result-icon {
                    font-size: 4rem;
                    margin-bottom: 15px;
                }
                .result-amount {
                    font-size: 2.2rem;
                    font-weight: bold;
                    margin-bottom: 15px;
                }
                .result-details {
                    margin-bottom: 25px;
                    color: #ccc;
                }
                .continue-btn {
                    background: linear-gradient(45deg, #10b981, #059669);
                    color: white;
                    border: none;
                    padding: 12px 30px;
                    border-radius: 25px;
                    font-weight: bold;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    margin-top: 10px;
                }
                .continue-btn:hover {
                    background: linear-gradient(45deg, #059669, #047857);
                    transform: translateY(-2px);
                }
                .win-result .result-amount {
                    color: #10b981;
                }
                .win-result .result-icon {
                    color: #10b981;
                }
                .loss-result .result-amount {
                    color: #ef4444;
                }
                .loss-result .result-icon {
                    color: #ef4444;
                }
            `;
            document.head.appendChild(style);
        }

        // Update modal content based on result type
        const title = modal.querySelector('#result-title');
        const icon = modal.querySelector('#result-icon');
        const amount = modal.querySelector('#result-amount');
        const details = modal.querySelector('#result-details');
        const modalContent = modal.querySelector('.modal-content');

        modalContent.classList.remove('win-result', 'loss-result');

        if (resultType === 'win') {
            modalContent.classList.add('win-result');
            title.textContent = '🎉 WINNER!';
            icon.textContent = '🏆';
            amount.textContent = `+${this.formatAmount(data.winnings)} GEM`;
            details.innerHTML = `
                <div>Multiplier: ${data.multiplier}x</div>
                <div style="margin-top: 5px;">Winning Number: ${data.number}</div>
                <div style="margin-top: 5px;">${data.crypto}</div>
            `;
        } else if (resultType === 'loss') {
            modalContent.classList.add('loss-result');
            title.textContent = '💔 Better Luck Next Time';
            icon.textContent = '🎲';
            amount.textContent = `-${this.formatAmount(data.losses)} GEM`;
            details.innerHTML = `
                <div>Losing Number: ${data.number}</div>
                <div style="margin-top: 5px;">${data.crypto}</div>
                <div style="margin-top: 10px; color: #888;">Don't give up! Every spin is a new opportunity.</div>
            `;
        }

        // Show modal
        modal.classList.add('show');
    }

    animateBalanceChange(change, source) {
        // Skip animation for non-roulette sources that are just syncing
        if (source === 'server-sync' || source === 'auth') {
            return;
        }

        const balanceElement = this.elements.gamingBalance;
        if (!balanceElement) return;

        const isPositive = change > 0;
        const absChange = Math.abs(change);

        // Skip animation for very small changes (< 10)
        if (absChange < 10) return;

        // Flash color animation
        balanceElement.style.transition = 'none';
        if (isPositive) {
            // Green flash for wins
            balanceElement.style.color = '#10b981';
            balanceElement.style.textShadow = '0 0 10px rgba(16, 185, 129, 0.5)';
        } else {
            // Red flash for losses
            balanceElement.style.color = '#ef4444';
            balanceElement.style.textShadow = '0 0 10px rgba(239, 68, 68, 0.5)';
        }

        // Remove flash after short delay
        setTimeout(() => {
            balanceElement.style.transition = 'color 0.5s ease, text-shadow 0.5s ease';
            balanceElement.style.color = '';
            balanceElement.style.textShadow = '';
        }, 300);

        // Number counting animation for large changes
        if (absChange >= 50) {
            this.animateNumberChange(change);
        }
    }

    animateNumberChange(change) {
        // Create floating number animation
        const container = document.querySelector('.gaming-balance') || document.querySelector('.balance-display');
        if (!container) return;

        const floatingNumber = document.createElement('div');
        floatingNumber.className = 'floating-balance-change';
        floatingNumber.textContent = (change > 0 ? '+' : '-') + this.formatAmount(Math.abs(change));
        floatingNumber.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 1.5rem;
            font-weight: bold;
            z-index: 1000;
            pointer-events: none;
            opacity: 1;
            color: ${change > 0 ? '#10b981' : '#ef4444'};
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            animation: floatUp 2s ease-out forwards;
        `;

        // Add CSS animation if it doesn't exist
        if (!document.querySelector('#floating-balance-animation')) {
            const style = document.createElement('style');
            style.id = 'floating-balance-animation';
            style.textContent = `
                @keyframes floatUp {
                    0% {
                        opacity: 1;
                        transform: translate(-50%, -50%) scale(1);
                    }
                    50% {
                        opacity: 1;
                        transform: translate(-50%, -150%) scale(1.2);
                    }
                    100% {
                        opacity: 0;
                        transform: translate(-50%, -200%) scale(1);
                    }
                }
            `;
            document.head.appendChild(style);
        }

        container.style.position = 'relative';
        container.appendChild(floatingNumber);

        // Remove element after animation
        setTimeout(() => {
            if (floatingNumber.parentNode) {
                floatingNumber.parentNode.removeChild(floatingNumber);
            }
        }, 2100);
    }

    // Show persistent result notification - stays visible until users sees it
    showPersistentResult(isWin, amount) {
        // Remove any existing persistent result
        const existingPersistent = document.querySelector('.persistent-result-notification');
        if (existingPersistent) {
            existingPersistent.remove();
        }

        // Create persistent result notification that stays visible
        const persistentResult = document.createElement('div');
        persistentResult.className = 'persistent-result-notification';
        if (isWin) {
            persistentResult.classList.add('win-result');
            persistentResult.innerHTML = `
                <div class="result-icon">🎉</div>
                <div class="result-message">YOU WON ${this.formatAmount(amount)} GEM${amount === 1 ? '' : 'S'}!</div>
                <button class="result-close" onclick="this.closest('.persistent-result-notification').remove()">
                    <i class="bi bi-x"></i>
                </button>
            `;
        } else {
            persistentResult.classList.add('loss-result');
            persistentResult.innerHTML = `
                <div class="result-icon">💔</div>
                <div class="result-message">YOU LOST ${this.formatAmount(amount)} GEM${amount === 1 ? '' : 'S'}</div>
                <button class="result-close" onclick="this.closest('.persistent-result-notification').remove()">
                    <i class="bi bi-x"></i>
                </button>
            `;
        }

        document.body.appendChild(persistentResult);

        // Add CSS for persistent result if not exists
        if (!document.querySelector('#persistent-result-styles')) {
            const style = document.createElement('style');
            style.id = 'persistent-result-styles';
            style.textContent = `
                .persistent-result-notification {
                    position: fixed;
                    top: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: rgba(0, 0, 0, 0.9);
                    border-radius: 15px;
                    padding: 15px 25px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    z-index: 10000;
                    animation: slideDownResult 0.5s ease-out;
                    border: 2px solid;
                    min-width: 300px;
                    max-width: 500px;
                }

                .persistent-result-notification.win-result {
                    border-color: #10b981;
                    background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(0, 0, 0, 0.9));
                }

                .persistent-result-notification.loss-result {
                    border-color: #ef4444;
                    background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(0, 0, 0, 0.9));
                }

                @keyframes slideDownResult {
                    from {
                        transform: translateX(-50%) translateY(-100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(-50%) translateY(0);
                        opacity: 1;
                    }
                }

                .persistent-result-notification .result-icon {
                    font-size: 2.5rem;
                    line-height: 1;
                }

                .persistent-result-notification .result-message {
                    font-size: 1.4rem;
                    font-weight: bold;
                    color: white;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.7);
                    flex-grow: 1;
                    text-align: center;
                }

                .persistent-result-notification.win-result .result-message {
                    color: #10b981;
                }

                .persistent-result-notification.loss-result .result-message {
                    color: #ef4444;
                }

                .persistent-result-notification .result-close {
                    background: none;
                    border: none;
                    color: #666;
                    font-size: 1.2rem;
                    cursor: pointer;
                    padding: 5px;
                    border-radius: 50%;
                    transition: all 0.2s ease;
                    opacity: 0.7;
                }

                .persistent-result-notification .result-close:hover {
                    opacity: 1;
                    background: rgba(255, 255, 255, 0.1);
                    color: white;
                }

                /* Auto-hide after 8 seconds with fade */
                .persistent-result-notification.fade-out {
                    animation: fadeOutResult 2s ease-out forwards;
                }

                @keyframes fadeOutResult {
                    from {
                        opacity: 1;
                        transform: translateX(-50%) translateY(0);
                    }
                    to {
                        opacity: 0;
                        transform: translateX(-50%) translateY(-20px);
                    }
                }
            `;
            document.head.appendChild(style);
        }

        // Auto-remove after 8 seconds with fade
        setTimeout(() => {
            persistentResult.classList.add('fade-out');
            setTimeout(() => {
                if (persistentResult.parentNode) {
                    persistentResult.parentNode.removeChild(persistentResult);
                }
            }, 2000);
        }, 8000);

        // Also make it disappear when user clicks anywhere on it (except close button)
        persistentResult.addEventListener('click', (event) => {
            if (!event.target.closest('.result-close')) {
                persistentResult.classList.add('fade-out');
                setTimeout(() => {
                    if (persistentResult.parentNode) {
                        persistentResult.remove();
                    }
                }, 1000);
            }
        });
    }

    // Casino-style flashy result overlay - full screen experience
    showCasinoStyleResult(resultType, data) {
        // Remove any existing casino result overlay
        const existingOverlay = document.querySelector('.casino-result-overlay');
        if (existingOverlay) {
            existingOverlay.remove();
        }

        // Create the flashy casino-style overlay
        const overlay = document.createElement('div');
        overlay.className = 'casino-result-overlay';

        let overlayContent = '';

        if (resultType === 'win') {
            overlay.classList.add('win-overlay');
            overlayContent = `
                <div class="casino-result-content">
                    <div class="result-header">
                        <div class="celebration-emoji">🎆</div>
                        <h1 class="result-title glow-text">WINNER!</h1>
                        <div class="celebration-emoji">🎆</div>
                    </div>

                    <div class="result-amount-section">
                        <div class="amount-wrapper">
                            <div class="amount-glow"></div>
                            <div class="amount-text pulse">+${this.formatAmount(data.winnings)}</div>
                            <div class="currency-text">GEM</div>
                        </div>
                        <div class="multiplier-badge">×${data.multiplier} MULTIPLIER</div>
                    </div>

                    <div class="result-details-section">
                        <div class="detail-card">
                            <div class="detail-icon">🎲</div>
                            <div class="detail-content">
                                <div class="detail-label">Winning Number</div>
                                <div class="detail-value">${data.number}</div>
                            </div>
                        </div>
                        <div class="detail-card">
                            <div class="detail-icon">₿</div>
                            <div class="detail-content">
                                <div class="detail-label">Crypto</div>
                                <div class="detail-value">${data.crypto}</div>
                            </div>
                        </div>
                    </div>

                    <div class="continue-section">
                        <button class="casino-continue-btn glow-effect" onclick="this.closest('.casino-result-overlay').classList.add('fade-out'); setTimeout(() => { this.closest('.casino-result-overlay').remove(); if (window.rouletteGame?.startNewRound) window.rouletteGame.startNewRound(); }, 500);">
                            🎰 CONTINUE GAMBLING 🎰
                        </button>
                    </div>
                </div>
            `;
        } else {
            overlay.classList.add('loss-overlay');
            overlayContent = `
                <div class="casino-result-content">
                    <div class="result-header">
                        <div class="sad-emoji">😞</div>
                        <h1 class="result-title loss-glow-text">BETTER LUCK NEXT TIME</h1>
                        <div class="sad-emoji">😞</div>
                    </div>

                    <div class="result-amount-section loss-amount">
                        <div class="amount-wrapper loss-wrapper">
                            <div class="amount-glow loss-glow"></div>
                            <div class="amount-text loss-pulse">-${this.formatAmount(data.losses)}</div>
                            <div class="currency-text loss-text">GEM</div>
                        </div>
                        <div class="loss-message">Don't give up! Every spin is a new opportunity.</div>
                    </div>

                    <div class="result-details-section">
                        <div class="detail-card loss-detail">
                            <div class="detail-icon">🎲</div>
                            <div class="detail-content">
                                <div class="detail-label">Losing Number</div>
                                <div class="detail-value">${data.number}</div>
                            </div>
                        </div>
                        <div class="detail-card loss-detail">
                            <div class="detail-icon">₿</div>
                            <div class="detail-content">
                                <div class="detail-label">Crypto</div>
                                <div class="detail-value">${data.crypto}</div>
                            </div>
                        </div>
                    </div>

                    <div class="continue-section">
                        <button class="casino-continue-btn loss-continue glow-effect" onclick="this.closest('.casino-result-overlay').classList.add('fade-out'); setTimeout(() => { this.closest('.casino-result-overlay').remove(); if (window.rouletteGame?.startNewRound) window.rouletteGame.startNewRound(); }, 500);">
                            🔄 TRY AGAIN 🔄
                        </button>
                    </div>
                </div>
            `;
        }

        overlay.innerHTML = overlayContent;
        document.body.appendChild(overlay);

        // Add CSS for casino-style overlays if not exists
        if (!document.querySelector('#casino-result-styles')) {
            const style = document.createElement('style');
            style.id = 'casino-result-styles';
            style.textContent = `
                .casino-result-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100vw;
                    height: 100vh;
                    background: radial-gradient(circle at center, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.97) 100%);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 9999;
                    animation: casinoOverlayEnter 0.5s ease-out;
                }

                .casino-result-overlay.fade-out {
                    animation: casinoOverlayExit 0.5s ease-in forwards;
                }

                @keyframes casinoOverlayEnter {
                    from {
                        opacity: 0;
                        backdrop-filter: blur(0px);
                    }
                    to {
                        opacity: 1;
                        backdrop-filter: blur(3px);
                    }
                }

                @keyframes casinoOverlayExit {
                    from {
                        opacity: 1;
                        transform: scale(1);
                    }
                    to {
                        opacity: 0;
                        transform: scale(1.1);
                    }
                }

                .casino-result-content {
                    text-align: center;
                    max-width: 600px;
                    width: 90%;
                    padding: 40px;
                    border-radius: 20px;
                    position: relative;
                    animation: contentEnter 0.8s ease-out 0.2s both;
                }

                @keyframes contentEnter {
                    from {
                        transform: scale(0.8) translateY(50px);
                        opacity: 0;
                    }
                    to {
                        transform: scale(1) translateY(0);
                        opacity: 1;
                    }
                }

                .win-overlay .casino-result-content {
                    background: linear-gradient(135deg, #0f0f0f, #1a1a2e);
                    border: 3px solid #10b981;
                    box-shadow:
                        0 0 50px rgba(16, 185, 129, 0.5),
                        inset 0 0 50px rgba(16, 185, 129, 0.1);
                }

                .loss-overlay .casino-result-content {
                    background: linear-gradient(135deg, #1a0a0a, #2a0a0a);
                    border: 3px solid #ef4444;
                    box-shadow:
                        0 0 50px rgba(239, 68, 68, 0.5),
                        inset 0 0 50px rgba(239, 68, 68, 0.1);
                }

                .result-header {
                    margin-bottom: 30px;
                }

                .celebration-emoji, .sad-emoji {
                    display: inline-block;
                    font-size: 2.5rem;
                    margin: 0 20px;
                    animation: emojiBounce 1s ease-in-out infinite alternate;
                }

                @keyframes emojiBounce {
                    from { transform: translateY(0); }
                    to { transform: translateY(-10px); }
                }

                .result-title {
                    font-size: 3rem;
                    font-weight: 900;
                    margin: 20px 0;
                    text-transform: uppercase;
                    letter-spacing: 3px;
                }

                .glow-text {
                    background: linear-gradient(45deg, #10b981, #fbbf24, #10b981);
                    background-size: 200% 200%;
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    animation: textShine 2s ease-in-out infinite;
                }

                .loss-glow-text {
                    background: linear-gradient(45deg, #ef4444, #f97316, #ef4444);
                    background-size: 200% 200%;
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    animation: textShine 2s ease-in-out infinite;
                }

                @keyframes textShine {
                    0% { background-position: 0% 50%; }
                    50% { background-position: 100% 50%; }
                    100% { background-position: 0% 50%; }
                }

                .result-amount-section {
                    margin: 40px 0;
                }

                .amount-wrapper {
                    position: relative;
                    display: inline-block;
                    margin-bottom: 20px;
                }

                .amount-glow {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    width: 200px;
                    height: 200px;
                    background: radial-gradient(circle, rgba(16, 185, 129, 0.3) 0%, transparent 70%);
                    border-radius: 50%;
                    animation: amountGlowPulse 2s ease-in-out infinite;
                }

                .loss-glow {
                    background: radial-gradient(circle, rgba(239, 68, 68, 0.3) 0%, transparent 70%);
                }

                @keyframes amountGlowPulse {
                    0%, 100% {
                        transform: translate(-50%, -50%) scale(1);
                        opacity: 1;
                    }
                    50% {
                        transform: translate(-50%, -50%) scale(1.2);
                        opacity: 0.7;
                    }
                }

                .amount-text {
                    font-size: 4rem;
                    font-weight: 900;
                    position: relative;
                    z-index: 2;
                    color: #10b981;
                    text-shadow: 0 0 30px rgba(16, 185, 129, 0.8);
                }

                .loss-pulse {
                    color: #ef4444;
                    text-shadow: 0 0 30px rgba(239, 68, 68, 0.8);
                }

                .currency-text {
                    font-size: 1.5rem;
                    font-weight: 600;
                    color: #fbbf24;
                    margin-top: 10px;
                }

                .loss-text {
                    color: #f97316;
                }

                .multiplier-badge {
                    background: linear-gradient(45deg, #fbbf24, #f59e0b);
                    color: #000;
                    padding: 10px 20px;
                    border-radius: 25px;
                    font-weight: bold;
                    font-size: 1.1rem;
                    margin-top: 15px;
                    display: inline-block;
                    box-shadow: 0 5px 15px rgba(251, 191, 36, 0.4);
                }

                .loss-message {
                    color: #ccc;
                    font-style: italic;
                    margin-top: 15px;
                    font-size: 1.1rem;
                }

                .result-details-section {
                    display: flex;
                    justify-content: center;
                    gap: 30px;
                    margin: 40px 0;
                }

                .detail-card {
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 15px;
                    padding: 20px;
                    text-align: center;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    min-width: 150px;
                }

                .loss-detail {
                    background: rgba(239, 68, 68, 0.05);
                    border-color: rgba(239, 68, 68, 0.2);
                }

                .detail-icon {
                    font-size: 3rem;
                    margin-bottom: 10px;
                }

                .detail-label {
                    font-size: 0.9rem;
                    color: #ccc;
                    margin-bottom: 5px;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }

                .detail-value {
                    font-size: 1.5rem;
                    font-weight: bold;
                    color: #cbb;
                }

                .continue-section {
                    margin-top: 40px;
                }

                .casino-continue-btn {
                    background: linear-gradient(45deg, #22d3ee, #3b82f6, #8b5cf6);
                    color: white;
                    border: none;
                    padding: 15px 40px;
                    border-radius: 30px;
                    font-size: 1.2rem;
                    font-weight: bold;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                    box-shadow: 0 10px 30px rgba(59, 130, 246, 0.4);
                    animation: buttonGlow 2s ease-in-out infinite alternate;
                }

                .casino-continue-btn:hover {
                    transform: translateY(-3px);
                    box-shadow: 0 15px 40px rgba(59, 130, 246, 0.6);
                    animation-play-state: paused;
                }

                .loss-continue {
                    background: linear-gradient(45deg, #ef4444, #f97316, #dc2626);
                    box-shadow: 0 10px 30px rgba(239, 68, 68, 0.4);
                }

                .loss-continue:hover {
                    box-shadow: 0 15px 40px rgba(239, 68, 68, 0.6);
                }

                .glow-effect {
                    animation: buttonGlow 2s ease-in-out infinite alternate;
                }

                @keyframes buttonGlow {
                    from {
                        box-shadow: 0 10px 30px rgba(59, 130, 246, 0.4);
                    }
                    to {
                        box-shadow: 0 10px 30px rgba(59, 130, 246, 0.8);
                    }
                }

                /* Responsive adjustments */
                @media (max-width: 768px) {
                    .result-title {
                        font-size: 2rem;
                    }

                    .amount-text {
                        font-size: 3rem;
                    }

                    .result-details-section {
                        flex-direction: column;
                        gap: 15px;
                    }

                    .casino-result-content {
                        padding: 20px;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        // Trigger confetti for wins
        if (resultType === 'win') {
            this.createCasinoConfetti();
        }

        // Auto-hide after 15 seconds (longer for immersive experience)
        setTimeout(() => {
            if (!overlay.classList.contains('fade-out')) {
                overlay.classList.add('fade-out');
                setTimeout(() => {
                    if (overlay.parentNode) {
                        overlay.parentNode.removeChild(overlay);
                    }
                }, 500);
            }
        }, 15000);
    }

    // Enhanced confetti for casino wins
    createCasinoConfetti() {
        setTimeout(() => {
            for (let i = 0; i < 100; i++) {
                setTimeout(() => {
                    const confetti = document.createElement('div');
                    confetti.innerHTML = ['💰', '💎', '⭐', '🎯', '🏆'][Math.floor(Math.random() * 5)];
                    confetti.style.cssText = `
                        position: fixed;
                        left: ${Math.random() * 100}%;
                        top: -50px;
                        font-size: ${20 + Math.random() * 20}px;
                        color: ${['#fbbf24', '#10b981', '#22d3ee', '#8b5cf6', '#ef4444'][Math.floor(Math.random() * 5)]};
                        pointer-events: none;
                        z-index: 10000;
                        animation: casinoConfetti ${3 + Math.random() * 2}s linear forwards;
                        transform: rotate(${Math.random() * 360}deg);
                    `;

                    if (!document.querySelector('#casino-confetti-styles')) {
                        const style = document.createElement('style');
                        style.id = 'casino-confetti-styles';
                        style.textContent = `
                            @keyframes casinoConfetti {
                                0% {
                                    transform: translateY(0) rotate(0deg);
                                    opacity: 1;
                                }
                                100% {
                                    transform: translateY(120vh) rotate(720deg);
                                    opacity: 0;
                                }
                            }
                        `;
                        document.head.appendChild(style);
                    }

                    document.body.appendChild(confetti);
                    setTimeout(() => {
                        if (confetti.parentNode) {
                            confetti.parentNode.removeChild(confetti);
                        }
                    }, 5000);
                }, i * 30);
            }
        }, 500);
    }

    showNotification(message, type = 'info') {
        let container = document.querySelector('.toast-notification-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-notification-container';
            document.body.appendChild(container);
        }
        const toast = document.createElement('div');
        toast.className = `toast-notification ${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        requestAnimationFrame(() => {
            toast.classList.add('visible');
        });
        setTimeout(() => {
            toast.classList.remove('visible');
            setTimeout(() => toast.remove(), 300);
        }, 4000); // Extended duration for wins
    }

    // ===== AUTO-BETTING STRATEGIES =====

    // Start auto-betting with specified strategy
    startAutoBet(strategy, rounds, targetProfit, stopLoss) {
        if (this.autoBetEnabled) {
            this.showNotification('Auto-betting already running!', 'warning');
            return false;
        }

        this.bettingStrategy = strategy;
        this.autoBetEnabled = true;
        this.autoBetRoundsLeft = rounds || 50;
        this.autoBetTarget = targetProfit || 1000;
        this.autoBetMaxLoss = stopLoss || 500;
        this.baseBet = this.currentAmount;
        this.strategyStep = 0;

        // Reset session statistics
        this.sessionProfit = 0;
        this.sessionRounds = 0;

        // Show auto-bet indicator on spin button
        this.updateSpinButtonForAutoBet();

        this.showNotification(`Auto-betting started! ${rounds} rounds with ${strategy} strategy`, 'info');
        console.log(`🎰 Auto-betting started: ${strategy}, ${rounds} rounds, target: ${targetProfit}, stop: ${stopLoss}`);

        // Start live bet feed simulation
        this.startLiveBetFeed();

        return true;
    }

    // Stop auto-betting
    stopAutoBet(reason = 'Manual stop') {
        if (!this.autoBetEnabled) return;

        this.autoBetEnabled = false;
        this.bettingStrategy = 'manual';
        this.strategyStep = 0;

        this.updateSpinButtonForAutoBet();
        this.stopLiveBetFeed();

        this.showNotification(`Auto-betting stopped: ${reason}`, 'info');
        console.log(`🎰 Auto-betting stopped: ${reason}`);

        // Show session summary
        this.showSessionSummary();
    }

    // Handle auto-betting progression on loss
    handleAutoBetLoss() {
        if (!this.autoBetEnabled) return;

        let nextBet = this.baseBet;

        switch (this.bettingStrategy) {
            case 'martingale':
                this.strategyStep++;
                nextBet = this.baseBet * Math.pow(2, this.strategyStep);
                break;
            case 'fibonacci':
                this.strategyStep++;
                // Fibonacci sequence: 1, 1, 2, 3, 5, 8, 13, 21, 34...
                const fib = this.getFibonacciNumber(this.strategyStep);
                nextBet = this.baseBet * fib;
                break;
        }

        // Apply caps and limits
        nextBet = Math.min(nextBet, this.MAX_BET);
        nextBet = Math.min(nextBet, this.balance * 0.1); // Don't bet more than 10% of balance

        if (nextBet < this.MIN_BET) {
            this.stopAutoBet('Bet too small - strategy failed');
            return;
        }

        this.setCurrentAmount(Math.floor(nextBet));
    }

    // Handle auto-betting progression on win
    handleAutoBetWin() {
        if (!this.autoBetEnabled) return;

        switch (this.bettingStrategy) {
            case 'martingale':
                // Reset to base bet after any win
                this.strategyStep = 0;
                this.setCurrentAmount(this.baseBet);
                break;
            case 'fibonacci':
                if (this.strategyStep > 2) {
                    // Move back 2 steps on win
                    this.strategyStep = Math.max(0, this.strategyStep - 2);
                } else {
                    this.strategyStep = 0;
                }
                const fib = this.getFibonacciNumber(this.strategyStep);
                this.setCurrentAmount(Math.floor(this.baseBet * fib));
                break;
        }

        // Store consecutive wins
        this.consecutiveWins++;
    }

    // Check if auto-betting should stop
    shouldStopAutoBet() {
        if (!this.autoBetEnabled) return false;

        // Check profit target
        if (this.sessionProfit >= this.autoBetTarget) {
            return 'Profit target reached! 🎉';
        }

        // Check stop loss
        if (this.sessionProfit <= -this.autoBetMaxLoss) {
            return 'Stop loss triggered 💸';
        }

        // Check if balance is too low
        if (this.balance < this.MIN_BET * 2) {
            return 'Insufficient balance 🚫';
        }

        return false;
    }

    // Get Fibonacci number by index
    getFibonacciNumber(n) {
        if (n <= 1) return 1;
        let a = 1, b = 1;
        for (let i = 2; i <= n; i++) {
            const temp = a + b;
            a = b;
            b = temp;
        }
        return b;
    }

    // Update spin button to show auto-bet status
    updateSpinButtonForAutoBet() {
        if (!this.elements.spinButton) return;

        if (this.autoBetEnabled) {
            this.elements.spinButton.textContent = `AUTO-BET (${this.autoBetRoundsLeft})`;
            this.elements.spinButton.style.background = 'linear-gradient(45deg, #f59e0b, #d97706)';
        } else {
            this.elements.spinButton.textContent = 'SPIN TO WIN';
            this.elements.spinButton.style.background = '';
        }
    }

    // ===== ACHIEVEMENT SYSTEM =====

    // Update achievements based on performance
    updateAchievements(winnings, losses) {
        // Track total rounds
        this.totalRounds++;

        // First win achievement
        if (winnings > 0 && !this.achievements.firstWin) {
            this.achievements.firstWin = true;
            this.showAchievementNotification('First Win!', 'Welcome to the roulette winners club! 🎉');
        }

        // Track biggest bet
        const currentBetSize = losses || winnings;
        if (currentBetSize > this.biggestBet) {
            this.biggestBet = currentBetSize;
            if (this.biggestBet >= 500 && !this.achievements.bigBet) {
                this.achievements.bigBet = true;
                this.showAchievementNotification('High Roller!', 'Placed a bet of 500+ GEM 🤑');
            }
        }

        // Consecutive wins achievement
        if (winnings > 0) {
            this.consecutiveWins++;
            if (this.consecutiveWins >= 5 && !this.achievements.consecutiveWins5) {
                this.achievements.consecutiveWins5 = true;
                this.showAchievementNotification('Hot Streak!', 'Won 5 rounds in a row! 🔥');
            }
        } else {
            this.consecutiveWins = 0;
        }

        // Profit achievement
        if (this.sessionProfit >= 1000 && !this.achievements.profit1000) {
            this.achievements.profit1000 = true;
            this.showAchievementNotification('Thousandaire!', 'Made 1000+ GEM profit! 💰');
        }

        // Spins achievement
        if (this.totalRounds >= 100 && !this.achievements.spins100) {
            this.achievements.spins100 = true;
            this.showAchievementNotification('Dedication!', 'Played 100+ roulette rounds! 🎲');
        }
    }

    // Show achievement unlock notification
    showAchievementNotification(title, description) {
        // Create fancy achievement overlay
        const achievement = document.createElement('div');
        achievement.className = 'achievement-notification';
        achievement.innerHTML = `
            <div class="achievement-icon">🏆</div>
            <div class="achievement-content">
                <div class="achievement-title">${title}</div>
                <div class="achievement-description">${description}</div>
            </div>
        `;

        // Add CSS if not exists
        if (!document.querySelector('#achievement-styles')) {
            const style = document.createElement('style');
            style.id = 'achievement-styles';
            style.textContent = `
                .achievement-notification {
                    position: fixed;
                    top: 100px;
                    right: 20px;
                    background: linear-gradient(135deg, #1e293b, #334155);
                    border: 2px solid #fbbf24;
                    border-radius: 15px;
                    padding: 20px;
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    z-index: 10001;
                    animation: slideInAchievement 0.8s ease-out;
                    box-shadow: 0 10px 30px rgba(251, 191, 36, 0.3);
                    color: white;
                    min-width: 300px;
                }

                @keyframes slideInAchievement {
                    from {
                        transform: translateX(400px);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }

                .achievement-icon {
                    font-size: 3rem;
                    animation: achievementBounce 1s ease-in-out infinite alternate;
                }

                @keyframes achievementBounce {
                    from { transform: scale(1); }
                    to { transform: scale(1.1); }
                }

                .achievement-title {
                    font-size: 1.4rem;
                    font-weight: bold;
                    color: #fbbf24;
                    margin-bottom: 5px;
                }

                .achievement-description {
                    font-size: 0.9rem;
                    color: #cbd5e1;
                }

                .achievement-notification.fade-out {
                    animation: slideOutAchievement 0.8s ease-in forwards;
                }

                @keyframes slideOutAchievement {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(400px);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(achievement);

        // Auto-remove after 6 seconds
        setTimeout(() => {
            achievement.classList.add('fade-out');
            setTimeout(() => {
                if (achievement.parentNode) {
                    achievement.parentNode.removeChild(achievement);
                }
            }, 800);
        }, 6000);
    }

    // ===== LIVE BET FEED SYSTEM =====

    // Start live bet feed simulation
    startLiveBetFeed() {
        if (this.betFeedInterval) return;

        this.addFakeBet('CryptoKing', Math.floor(Math.random() * 500) + 50, 'RED');
        this.addFakeBet('DeFiDragon', Math.floor(Math.random() * 300) + 25, 'BLACK');

        // Add fake bets every 8-15 seconds
        this.betFeedInterval = setInterval(() => {
            const names = ['BitcoinBaron', 'CryptoKing', 'DeFiDragon', 'GamerGirl', 'StakingStar'];
            const betTypes = ['RED', 'BLACK', '1-18', '19-36', 'EVEN', 'ODD'];

            const name = names[Math.floor(Math.random() * names.length)];
            const amount = Math.floor(Math.random() * 1000) + 10;
            const type = betTypes[Math.floor(Math.random() * betTypes.length)];

            this.addFakeBet(name, amount, type);
        }, 8000 + Math.random() * 7000);
    }

    // Stop live bet feed
    stopLiveBetFeed() {
        if (this.betFeedInterval) {
            clearInterval(this.betFeedInterval);
            this.betFeedInterval = null;
        }
    }

    // Add fake bet to feed (simulates other players)
    addFakeBet(playerName, amount, betType) {
        const betEntry = {
            player: playerName,
            amount: amount,
            type: betType,
            timestamp: Date.now()
        };

        this.liveBetFeed.unshift(betEntry);

        // Keep only last 5 bets
        if (this.liveBetFeed.length > 5) {
            this.liveBetFeed.pop();
        }

        // Show bet announcement briefly
        this.showBetAnnouncement(`${playerName} bet ${this.formatAmount(amount)} GEM on ${betType}`, Math.random() > 0.7);

        this.updateBetFeedDisplay();
    }

    // Show bet announcement (like big bet alerts)
    showBetAnnouncement(message, isBigBet = false) {
        const announcement = document.createElement('div');
        announcement.className = `bet-announcement ${isBigBet ? 'big-bet' : ''}`;
        announcement.textContent = message;

        // Add CSS if not exists
        if (!document.querySelector('#bet-announcement-styles')) {
            const style = document.createElement('style');
            style.id = 'bet-announcement-styles';
            style.textContent = `
                .bet-announcement {
                    position: fixed;
                    top: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: rgba(0, 0, 0, 0.9);
                    color: #fbbf24;
                    padding: 10px 20px;
                    border-radius: 25px;
                    border: 1px solid #fbbf24;
                    z-index: 10002;
                    animation: betAnnouncementSlide 3s ease-out;
                    font-size: 0.9rem;
                    font-weight: bold;
                }

                .bet-announcement.big-bet {
                    background: linear-gradient(45deg, #fbbf24, #f59e0b);
                    color: #0f1419;
                    border-color: #d97706;
                    font-size: 1rem;
                    padding: 12px 24px;
                    animation: bigBetAnnouncement 4s ease-out;
                }

                @keyframes betAnnouncementSlide {
                    0% {
                        transform: translateX(-50%) translateY(-100%);
                        opacity: 0;
                    }
                    10%, 90% {
                        transform: translateX(-50%) translateY(0);
                        opacity: 1;
                    }
                    100% {
                        transform: translateX(-50%) translateY(-100%);
                        opacity: 0;
                    }
                }

                @keyframes bigBetAnnouncement {
                    0% {
                        transform: translateX(-50%) translateY(-100%) scale(0.8);
                        opacity: 0;
                    }
                    10%, 90% {
                        transform: translateX(-50%) translateY(0) scale(1);
                        opacity: 1;
                    }
                    100% {
                        transform: translateX(-50%) translateY(-100%) scale(0.8);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(announcement);

        // Auto-remove after animation
        setTimeout(() => {
            if (announcement.parentNode) {
                announcement.parentNode.removeChild(announcement);
            }
        }, 4000);
    }

    // Update bet feed display
    updateBetFeedDisplay() {
        // Create floating bet feed in bottom left
        let feedContainer = document.querySelector('.bet-feed-container');
        if (!feedContainer) {
            feedContainer = document.createElement('div');
            feedContainer.className = 'bet-feed-container';
            feedContainer.innerHTML = '<div class="feed-header">🎰 Live Bets</div><div class="feed-items"></div>';

            // Add CSS if not exists
            if (!document.querySelector('#bet-feed-styles')) {
                const style = document.createElement('style');
                style.id = 'bet-feed-styles';
                style.textContent = `
                    .bet-feed-container {
                        position: fixed;
                        bottom: 20px;
                        left: 20px;
                        background: rgba(0, 0, 0, 0.8);
                        border: 1px solid rgba(251, 191, 36, 0.3);
                        border-radius: 10px;
                        padding: 15px;
                        z-index: 10000;
                        min-width: 250px;
                        max-width: 350px;
                        animation: feedSlideIn 0.5s ease-out;
                    }

                    @keyframes feedSlideIn {
                        from {
                            transform: translateX(-100%);
                            opacity: 0;
                        }
                        to {
                            transform: translateX(0);
                            opacity: 1;
                        }
                    }

                    .feed-header {
                        color: #fbbf24;
                        font-weight: bold;
                        font-size: 1rem;
                        margin-bottom: 10px;
                        text-align: center;
                    }

                    .feed-items {
                        max-height: 150px;
                        overflow-y: auto;
                    }

                    .bet-feed-item {
                        background: rgba(22, 33, 62, 0.6);
                        border-radius: 5px;
                        padding: 8px;
                        margin-bottom: 5px;
                        font-size: 0.8rem;
                        animation: itemSlideIn 0.3s ease-out;
                        border-left: 3px solid #fbbf24;
                    }

                    @keyframes itemSlideIn {
                        from {
                            transform: translateX(-20px);
                            opacity: 0;
                        }
                        to {
                            transform: translateX(0);
                            opacity: 1;
                        }
                    }

                    .bet-feed-item .player-name {
                        color: #fbbf24;
                        font-weight: bold;
                    }

                    .bet-feed-item .bet-amount {
                        color: #10b981;
                        float: right;
                    }

                    .bet-feed-item .bet-type {
                        color: #cbd5e1;
                        font-size: 0.75rem;
                    }
                `;
                document.head.appendChild(style);
            }

            document.body.appendChild(feedContainer);
        }

        const feedItems = feedContainer.querySelector('.feed-items');
        feedItems.innerHTML = '';

        this.liveBetFeed.forEach(bet => {
            const item = document.createElement('div');
            item.className = 'bet-feed-item';
            item.innerHTML = `
                <div class="player-name">${bet.player}</div>
                <div class="bet-type">${bet.type}</div>
                <div class="bet-amount">${this.formatAmount(bet.amount)} GEM</div>
            `;
            feedItems.appendChild(item);
        });
    }

    // Show session summary when auto-betting ends
    showSessionSummary() {
        const summary = document.createElement('div');
        summary.className = 'session-summary-modal';
        summary.innerHTML = `
            <div class="modal-overlay" onclick="this.closest('.session-summary-modal').remove()"></div>
            <div class="modal-content">
                <h3>🎰 Session Summary</h3>
                <div class="summary-stats">
                    <div class="stat-item">
                        <span class="stat-label">Rounds Played:</span>
                        <span class="stat-value">${this.sessionRounds}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Total Profit:</span>
                        <span class="stat-value ${this.sessionProfit >= 0 ? 'positive' : 'negative'}">${this.sessionProfit >= 0 ? '+' : ''}${this.formatAmount(this.sessionProfit)} GEM</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Best Streak:</span>
                        <span class="stat-value">${this.consecutiveWins}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Strategy Used:</span>
                        <span class="stat-value">${this.bettingStrategy.toUpperCase()}</span>
                    </div>
                </div>
                <button class="close-summary-btn" onclick="this.closest('.session-summary-modal').remove()">Close</button>
            </div>
        `;

        // Add CSS if not exists
        if (!document.querySelector('#session-summary-styles')) {
            const style = document.createElement('style');
            style.id = 'session-summary-styles';
            style.textContent = `
                .session-summary-modal {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100vw;
                    height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 99999;
                }

                .session-summary-modal .modal-overlay {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.8);
                }

                .session-summary-modal .modal-content {
                    background: linear-gradient(135deg, #1a1a2e, #16213e);
                    border: 2px solid #fbbf24;
                    border-radius: 15px;
                    padding: 30px;
                    max-width: 400px;
                    width: 90%;
                    text-align: center;
                    position: relative;
                    z-index: 1;
                    animation: modalEnter 0.5s ease-out;
                }

                @keyframes modalEnter {
                    from {
                        transform: scale(0.8) translateY(50px);
                        opacity: 0;
                    }
                    to {
                        transform: scale(1) translateY(0);
                        opacity: 1;
                    }
                }

                .session-summary-modal h3 {
                    color: #fbbf24;
                    margin-bottom: 20px;
                    font-size: 1.8rem;
                }

                .summary-stats {
                    margin-bottom: 25px;
                    text-align: left;
                }

                .stat-item {
                    display: flex;
                    justify-content: space-between;
                    padding: 10px;
                    background: rgba(0, 0, 0, 0.3);
                    border-radius: 8px;
                    margin-bottom: 10px;
                }

                .stat-label {
                    color: #cbd5e1;
                    font-weight: bold;
                }

                .stat-value {
                    color: #fbbf24;
                    font-weight: bold;
                }

                .stat-value.positive {
                    color: #10b981;
                }

                .stat-value.negative {
                    color: #ef4444;
                }

                .close-summary-btn {
                    background: linear-gradient(45deg, #10b981, #059669);
                    color: white;
                    border: none;
                    padding: 10px 30px;
                    border-radius: 25px;
                    font-weight: bold;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }

                .close-summary-btn:hover {
                    background: linear-gradient(45deg, #059669, #047857);
                    transform: translateY(-2px);
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(summary);
    }

    // Handle start auto-betting from UI
    handleStartAutoBet() {
        const strategy = document.getElementById('bettingStrategy')?.value;
        const rounds = parseInt(document.getElementById('autoBetRounds')?.value) || 10;
        const profitTarget = parseInt(document.getElementById('profitTarget')?.value) || 1000;
        const stopLoss = parseInt(document.getElementById('stopLoss')?.value) || 500;

        if (!strategy) {
            this.showNotification('Please select a betting strategy.', 'warning');
            return;
        }

        if (rounds < 5 || rounds > 100) {
            this.showNotification('Rounds must be between 5 and 100.', 'warning');
            return;
        }

        if (profitTarget < 100 || profitTarget > 10000) {
            this.showNotification('Profit target must be between 100 and 10,000.', 'warning');
            return;
        }

        if (stopLoss < 100 || stopLoss > 5000) {
            this.showNotification('Stop loss must be between 100 and 5,000.', 'warning');
            return;
        }

        if (this.currentAmount <= 0 || this.balance < this.currentAmount) {
            this.showNotification('Insufficient balance for selected bet amount.', 'error');
            return;
        }

        const success = this.startAutoBet(strategy, rounds, profitTarget, stopLoss);

        if (success) {
            // Update UI elements
            const controls = document.getElementById('autoBetControls');
            const startBtn = document.getElementById('startAutoBet');
            const stopBtn = document.getElementById('stopAutoBet');

            if (controls && startBtn && stopBtn) {
                controls.classList.add('active'); // Add visual indicator that it's running
                startBtn.style.display = 'none';
                stopBtn.style.display = 'block';

                // Show risk warning is still visible
                controls.querySelector('.risk-warning')?.classList.add('auto-running');
            }
        }
    }

    // Update auto-betting UI state
    updateAutoBetUI() {
        const controls = document.getElementById('autoBetControls');
        const startBtn = document.getElementById('startAutoBet');
        const stopBtn = document.getElementById('stopAutoBet');

        if (!controls || !startBtn || !stopBtn) return;

        if (this.autoBetEnabled) {
            controls.classList.add('active');
            startBtn.style.display = 'none';
            stopBtn.style.display = 'block';

            // Update rounds display
            this.updateSpinButtonForAutoBet();
        } else {
            controls.classList.remove('active');
            startBtn.style.display = 'block';
            stopBtn.style.display = 'none';
        }
    }

    // Override the startNewRound method for auto-betting
    startNewRound() {
        if (this.roundTimer) {
            clearInterval(this.roundTimer);
        }
        const startTime = Date.now();
        this.updateRoundTimer(this.ROUND_DURATION);

        this.roundTimer = setInterval(() => {
            const elapsed = Date.now() - startTime;
            const remaining = Math.max(this.ROUND_DURATION - elapsed, 0);
            this.updateRoundTimer(remaining);

            // When countdown reaches 0, handle auto-betting logic
            if (remaining === 0) {
                clearInterval(this.roundTimer);
                this.roundTimer = null;

                // If auto-betting is enabled and we have bets placed, auto-spin
                if (this.autoBetEnabled && this.currentBets.length > 0) {
                    this.requestSpin();
                } else {
                    // Regular behavior: just restart countdown
                    this.startNewRound();
                }
            }
        }, 200);
    }

    // ===== FUNNY USERNAME & AVATAR SYSTEM =====

    // Generate a funny random username
    generateFunnyUsername() {
        const nameMethods = Math.floor(Math.random() * 4);

        switch (nameMethods) {
            case 0: // Prefix + Suffix (JoeBob, BreadCheese)
                const prefix = this.namePrefixes[Math.floor(Math.random() * this.namePrefixes.length)];
                const suffix = this.nameSuffixes[Math.floor(Math.random() * this.nameSuffixes.length)];
                return prefix + suffix;

            case 1: // Name + Number (Bob42, Sally7)
                const singleName = [...this.namePrefixes, ...this.nameSuffixes][Math.floor(Math.random() * (this.namePrefixes.length + this.nameSuffixes.length))];
                const number = Math.floor(Math.random() * 999) + 1;
                return singleName + number;

            case 2: // Word combinations (DogBread, CheeseCat, TreeRock)
                const word1 = this.nameWords[Math.floor(Math.random() * this.nameWords.length)];
                const word2 = this.nameWords[Math.floor(Math.random() * this.nameWords.length)];
                return word1 + word2;

            case 3: // Mixed combinations (BobBread, CheeseSteve, Dog42)
                const namePart = [...this.namePrefixes, ...this.nameSuffixes][Math.floor(Math.random() * (this.namePrefixes.length + this.nameSuffixes.length))];
                const wordPart = this.nameWords[Math.floor(Math.random() * this.nameWords.length)];
                return Math.random() > 0.5 ? namePart + wordPart : wordPart + namePart;

            default:
                return 'BobRoss'; // Fallback
        }
    }

    // Get random avatar emoji
    getRandomAvatar() {
        return this.playerAvatars[Math.floor(Math.random() * this.playerAvatars.length)];
    }

    // Update bet feed display (enhanced with avatars)
    updateBetFeedDisplay() {
        // Create floating bet feed in bottom left
        let feedContainer = document.querySelector('.bet-feed-container');
        if (!feedContainer) {
            feedContainer = document.createElement('div');
            feedContainer.className = 'bet-feed-container';
            feedContainer.innerHTML = '<div class="feed-header">🎰 Live Bets</div><div class="feed-items"></div>';

            // Enhanced CSS with avatar support
            if (!document.querySelector('#bet-feed-styles')) {
                const style = document.createElement('style');
                style.id = 'bet-feed-styles';
                style.textContent = `
                    .bet-feed-container {
                        position: fixed;
                        bottom: 20px;
                        left: 20px;
                        background: rgba(0, 0, 0, 0.8);
                        border: 1px solid rgba(251, 191, 36, 0.3);
                        border-radius: 10px;
                        padding: 15px;
                        z-index: 10000;
                        min-width: 280px;
                        max-width: 380px;
                        animation: feedSlideIn 0.5s ease-out;
                    }

                    @keyframes feedSlideIn {
                        from {
                            transform: translateX(-100%);
                            opacity: 0;
                        }
                        to {
                            transform: translateX(0);
                            opacity: 1;
                        }
                    }

                    .feed-header {
                        color: #fbbf24;
                        font-weight: bold;
                        font-size: 1rem;
                        margin-bottom: 10px;
                        text-align: center;
                    }

                    .feed-items {
                        max-height: 200px;
                        overflow-y: auto;
                    }

                    .bet-feed-item {
                        background: rgba(22, 33, 62, 0.6);
                        border-radius: 8px;
                        padding: 10px;
                        margin-bottom: 8px;
                        font-size: 0.8rem;
                        animation: itemSlideIn 0.3s ease-out;
                        border-left: 4px solid #fbbf24;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }

                    @keyframes itemSlideIn {
                        from {
                            transform: translateX(-20px);
                            opacity: 0;
                        }
                        to {
                            transform: translateX(0);
                            opacity: 1;
                        }
                    }

                    .bet-feed-item .player-avatar {
                        font-size: 2rem;
                        width: 35px;
                        height: 35px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        background: rgba(251, 191, 36, 0.1);
                        border-radius: 50%;
                        border: 1px solid rgba(251, 191, 36, 0.3);
                    }

                    .bet-feed-item .player-info {
                        flex-grow: 1;
                    }

                    .bet-feed-item .player-name {
                        color: #fbbf24;
                        font-weight: bold;
                        font-size: 0.9rem;
                    }

                    .bet-feed-item .bet-amount {
                        color: #10b981;
                        font-weight: bold;
                        font-size: 1rem;
                        margin-top: 3px;
                    }

                    .bet-feed-item .bet-type {
                        color: #cbd5e1;
                        font-size: 0.7rem;
                        opacity: 0.8;
                    }
                `;
                document.head.appendChild(style);
            }

            document.body.appendChild(feedContainer);
        }

        const feedItems = feedContainer.querySelector('.feed-items');
        feedItems.innerHTML = '';

        this.liveBetFeed.forEach(bet => {
            // Generate avatar and name if not already set
            if (!bet.avatar) bet.avatar = this.getRandomAvatar();
            if (!bet.funnyName) bet.funnyName = this.generateFunnyUsername();

            const item = document.createElement('div');
            item.className = 'bet-feed-item';
            item.innerHTML = `
                <div class="player-avatar">${bet.avatar}</div>
                <div class="player-info">
                    <div class="player-name">${bet.funnyName}</div>
                    <div class="bet-amount">${this.formatAmount(bet.amount)} GEM</div>
                    <div class="bet-type">on ${bet.type}</div>
                </div>
            `;
            feedItems.appendChild(item);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    try {
        new RouletteGame();
    } catch (error) {
        console.error('Failed to initialize roulette game', error);
    }
});
