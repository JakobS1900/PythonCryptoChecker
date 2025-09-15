/**
 * Enhanced Crypto Roulette Game
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
        this.betAmountSelected = false; // User must select bet amount
        this.selectedNumbers = [];
        this.activeBets = [];
        this.currentPosition = 0;
        this.isRolling = false;
        this.isMuted = false;
        this.isConnected = false;
        this.websocket = null;
        this.roomStats = {};
        this.userBalance = 1000; // Default balance
        this.committedAmount = 0; // Amount committed to current bets (not yet deducted)
        
        // Performance optimization: Throttling timestamps  
        this.lastBalanceSync = 0;
        this.lastManagerCheck = 0;
        
        // Create updateBalance method with balance manager integration
        this.updateBalance = (newBalance, source = 'roulette') => {
            console.log('🎰 Balance update called:', newBalance, source);
            const validBalance = parseFloat(newBalance) || 5000;
            
            // Update local balance immediately
            this.userBalance = validBalance;
            this.updateBalanceDisplay();
            this.updateBetAmountDisplay();
            
            // Sync with balance manager if available (for persistence)
            if (window.balanceManager && source !== 'balance-manager') {
                window.balanceManager.updateBalance(validBalance, source);
            }
            
            // Emit balance update event for other components
            window.dispatchEvent(new CustomEvent('balanceUpdated', {
                detail: { balance: validBalance, source: source }
            }));
        };
        
        this.init();
    }

    async init() {
        this.createWheelSegments();
        this.setupEventListeners();
        this.setupGlobalBalanceListener();
        await this.loadUserSession();
        this.updateBetAmountDisplay();
        this.setupBettingInterface();
        console.log('Enhanced roulette game initialized');
        
        // Run initialization validation
        this.validateInitialization();
    }
    
    setupGlobalBalanceListener() {
        // Wait for balance manager to be available
        const waitForBalanceManager = () => {
            if (window.balanceManager) {
                this.integrateWithBalanceManager();
            } else {
                setTimeout(waitForBalanceManager, 100);
            }
        };
        waitForBalanceManager();
        
        // Legacy fallback for external balance updates
        window.addEventListener('balanceUpdated', (event) => {
            if (event.detail && event.detail.source !== 'roulette' && event.detail.source !== 'balance-manager') {
                const externalBalance = parseFloat(event.detail.balance);
                if (!isNaN(externalBalance) && externalBalance >= 0) {
                    this.userBalance = externalBalance;
                    this.updateBalanceDisplay();
                    console.log('🎰 Roulette balance updated from external source:', externalBalance);
                }
            }
        });
    }
    
    integrateWithBalanceManager() {
        console.log('🔗 Integrating roulette with unified balance manager');
        
        // Get current balance from manager
        const currentBalance = window.balanceManager.getBalance();
        this.userBalance = currentBalance;
        console.log('💰 Initial balance from manager:', currentBalance);
        
        // Force update display immediately
        this.updateBalanceDisplay();
        
        // Trigger a full UI refresh to ensure everything is synced
        setTimeout(() => {
            this.updateBetAmountDisplay();
            this.validateInitialization();
        }, 100);
        
        // Listen for balance changes with improved synchronization
        window.balanceManager.addBalanceListener((event) => {
            if (event.type === 'updated' || event.type === 'loaded') {
                // CRITICAL FIX: Only update if the event is from external source
                // Prevent circular updates when roulette itself updates the balance
                const eventSource = event.source || 'unknown';
                if (eventSource !== 'roulette-correction' && eventSource !== 'spin_result' && eventSource !== 'bet_update') {
                    console.log('🎰 External balance update detected, syncing:', event.balance, 'from:', eventSource);
                    this.userBalance = event.balance;
                    this.updateBalanceDisplay();
                    this.updateBetAmountDisplay();
                } else {
                    console.log('🔄 Ignoring self-generated balance event from:', eventSource);
                }
            }
        });
        
        // Enhanced integration: Use balance manager for persistence only
        // The updateBalance method now works through events, no override needed
        console.log('🔗 Balance manager integration complete - using event-based updates');
    }
    
    validateInitialization() {
        const validationResults = {
            balanceElements: this.testBalanceElements(),
            customInput: this.testCustomInput(),
            betButtons: this.testBetButtons(),
            balanceSync: this.testBalanceSync()
        };
        
        const allValid = Object.values(validationResults).every(result => result);
        
        if (allValid) {
            console.log('✅ Roulette game validation passed - all systems operational');
        } else {
            console.warn('⚠️ Roulette game validation issues:', validationResults);
        }
        
        return validationResults;
    }
    
    testBalanceElements() {
        const elements = ['walletBalance', 'nav-gem-balance'];
        return elements.every(id => {
            const element = document.getElementById(id);
            return element !== null;
        });
    }
    
    testCustomInput() {
        const input = document.getElementById('custom-bet-amount');
        const setButton = document.getElementById('set-custom-amount');
        const feedback = document.getElementById('bet-validation-message');
        return input && setButton && feedback;
    }
    
    testBetButtons() {
        const buttons = document.querySelectorAll('.bet-amount-btn');
        const maxButton = document.getElementById('max-bet-btn');
        return buttons.length >= 6 && maxButton;
    }
    
    testBalanceSync() {
        return typeof this.getSafeBalance === 'function' && 
               typeof this.userBalance === 'number' && 
               this.userBalance > 0;
    }

    createWheelSegments() {
        const wheelsContent = document.getElementById('wheelsContent');
        if (!wheelsContent) return;

        // Create multiple repeated segments to simulate infinite scroll
        const REPEATS = 12; // number of repeated strips
        const html = Array.from({ length: REPEATS }).map(() => {
            return `<div class='wheel'>${
                NUMS.map(num => {
                    const colorClass = this.getColorClass(num);
                    return `<div class='${colorClass} chunk'><span>${num}</span></div>`;
                }).join('')
            }</div>`;
        }).join('');
        
        wheelsContent.innerHTML = html;
        // Reset any prior transform
        wheelsContent.style.transform = 'matrix(1, 0, 0, 1, 0, 0)';

        // Measure actual chunk width for precise alignment
        const firstChunk = wheelsContent.querySelector('.chunk');
        this.chunkWidth = firstChunk ? firstChunk.offsetWidth : 70;
    }

    getColorClass(number) {
        if (number === 0) return 'green-number';
        if (RED_NUMBERS.includes(number)) return 'red-number';
        if (BLACK_NUMBERS.includes(number)) return 'black-number';
        return 'black-number';
    }

    setupEventListeners() {
        // Bet amount buttons (including MAX button)
        document.querySelectorAll('.bet-amount-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                if (btn.id === 'max-bet-btn') {
                    this.setMaxBetAmount();
                    this.betAmountSelected = true;
                } else {
                    this.currentBetAmount = parseInt(e.target.dataset.amount) || MIN_BET;
                    this.betAmountSelected = true;
                    this.updateBetAmountDisplay();
                }
            });
        });
        
        // Custom bet amount input
        const customBetInput = document.getElementById('custom-bet-amount');
        const setCustomButton = document.getElementById('set-custom-amount');
        
        if (customBetInput) {
            customBetInput.addEventListener('input', () => {
                this.validateCustomBetAmount();
            });
            
            customBetInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.setCustomBetAmount();
                }
            });
        }
        
        if (setCustomButton) {
            setCustomButton.addEventListener('click', () => {
                this.setCustomBetAmount();
            });
        }

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
            display.textContent = this.betAmountSelected ? `${this.currentBetAmount} GEM` : '0 GEM';
        }
        
        // Update active bet amount buttons
        document.querySelectorAll('.bet-amount-btn').forEach(btn => {
            btn.classList.remove('active');
            if (this.betAmountSelected && parseInt(btn.dataset.amount) === this.currentBetAmount) {
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

        if (!this.betAmountSelected) {
            this.showNotification('Please select a bet amount', 'warning');
            return;
        }

        if (this.currentBetAmount < MIN_BET || this.currentBetAmount > MAX_BET) {
            this.showNotification(`Bet amount must be between ${MIN_BET} and ${MAX_BET} GEM`, 'error');
            return;
        }

        // Check available balance (total balance minus committed amount)
        const availableBalance = this.userBalance - this.committedAmount;
        if (availableBalance < this.currentBetAmount) {
            this.showNotification('Insufficient available balance', 'error');
            return;
        }

        try {
            // Check authentication - require login for all betting
            if (!localStorage.getItem('access_token') || localStorage.getItem('access_token') === 'null') {
                this.showErrorAlert('Please log in to place bets. <a href="/login" class="alert-link">Login here</a>');
                return;
            }
            
            const response = await fetch('/api/gaming/roulette/place_bet', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({
                    bet_type: betType,
                    bet_value: betValue,
                    amount: parseFloat(this.currentBetAmount) || MIN_BET,
                    bet_amount: parseFloat(this.currentBetAmount) || MIN_BET
                })
            });

            const result = await response.json();
            
            if (response.ok && result.success) {
                // API bet successful - use the amount from result for consistency
                console.log('API bet successful - Amount placed:', result.amount);
                this.handleBetPlaced(result);
                this.addVisualBetFeedback(betType, betValue);
            } else {
                // API bet failed - show error message
                const errorMsg = result?.error || result?.detail || response.statusText || 'Unknown error';
                console.error('API bet failed:', errorMsg);
                this.showErrorAlert(`Bet placement failed: ${errorMsg}`);
            }
        } catch (error) {
            console.error('Bet placement error:', error);
            this.showErrorAlert('Network error. Please check your connection and try again.');
        }
    }

    showErrorAlert(message) {
        // Create alert container if it doesn't exist
        let alertContainer = document.getElementById('alertContainer');
        if (!alertContainer) {
            alertContainer = document.createElement('div');
            alertContainer.id = 'alertContainer';
            alertContainer.className = 'container mt-3';
            document.querySelector('main').insertBefore(alertContainer, document.querySelector('main').firstChild);
        }

        // Create and show alert
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        alertContainer.appendChild(alert);

        // Auto-dismiss after 10 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.classList.remove('show');
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.parentNode.removeChild(alert);
                    }
                }, 300);
            }
        }, 10000);
    }
    
    calculatePotentialPayout(betType, betValue) {
        switch(betType) {
            case 'number': return this.currentBetAmount * 35;
            case 'color': return this.currentBetAmount * 2;
            case 'category': return this.currentBetAmount * 3;
            default: return this.currentBetAmount * 2;
        }
    }
    
    updateBalanceDisplay() {
        // Safe balance conversion with fallback
        const safeBalance = this.getSafeBalance();
        
        // Update all possible balance display elements
        this.syncAllBalanceElements(safeBalance);
        
        // Sync with auth manager for cross-component consistency
        this.syncWithAuthManager(safeBalance);
        
        // Update internal balance to ensure consistency
        this.userBalance = safeBalance;
        
        // Update custom input constraints
        this.updateCustomInputConstraints();
    }
    
    syncAllBalanceElements(balance) {
        // Array of possible balance element IDs
        const balanceElementIds = [
            'walletBalance',      // Roulette page main balance
            'user-balance',       // Fallback ID
            'nav-gem-balance'     // Navigation bar balance
        ];

        const availableBalance = balance - this.committedAmount;

        balanceElementIds.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                // Show available/committed breakdown for main wallet balance
                if (id === 'walletBalance' && this.committedAmount > 0) {
                    element.innerHTML = `
                        <div class="balance-breakdown">
                            <div class="total-balance">${balance.toLocaleString()} GEM</div>
                            <div class="balance-details">
                                <small class="text-success">Available: ${availableBalance.toLocaleString()} GEM</small>
                                <small class="text-warning">In Play: ${this.committedAmount.toLocaleString()} GEM</small>
                            </div>
                        </div>
                    `;
                } else if (id === 'nav-gem-balance') {
                    // Navigation shows available balance only
                    element.textContent = availableBalance.toLocaleString();
                } else {
                    element.textContent = balance.toLocaleString() + ' GEM';
                }
            }
        });
    }
    
    syncWithAuthManager(balance) {
        // Two-way sync with auth manager
        const authObj = window.authManager || window.auth;
        // Only sync back to auth manager if authenticated; avoid demo fallback overriding demo balance
        if (authObj && typeof authObj.isAuthenticated === 'function' && authObj.isAuthenticated()) {
            if (typeof authObj.updateBalance === 'function') {
                authObj.updateBalance(balance);
            } else {
                // Fallback: set property if method is missing
                authObj.userBalance = balance;
            }
        }
        
        // Trigger custom balance update event for other components
        window.dispatchEvent(new CustomEvent('balanceUpdated', {
            detail: { balance: balance, source: 'roulette' }
        }));
    }
    
    updateCustomInputConstraints() {
        const customInput = document.getElementById('custom-bet-amount');
        if (customInput) {
            const availableBalance = this.getSafeBalance() - this.committedAmount;
            const maxBet = Math.min(availableBalance, MAX_BET);
            customInput.max = maxBet;

            // If current input value exceeds new max, clear it
            if (customInput.value && parseFloat(customInput.value) > maxBet) {
                this.clearCustomBetInput();
            }
        }
    }
    
    getSafeBalance() {
        // PERFORMANCE FIX: Reduce balance manager calls and prevent refresh loops
        
        // PRIORITY 1: Use local userBalance if it's valid and recently set
        if (this.userBalance !== undefined && this.userBalance !== null) {
            const numBalance = parseFloat(this.userBalance);
            if (!isNaN(numBalance) && numBalance >= 0) {
                
                // PERFORMANCE: Only sync to balance manager occasionally, not on every call
                if (window.balanceManager && !this.lastBalanceSync || 
                    (Date.now() - this.lastBalanceSync) > 5000) { // 5 second throttle
                    
                    const managerBalance = window.balanceManager.getBalance();
                    if (Math.abs(managerBalance - numBalance) > 0.01) {
                        console.log('🔄 Syncing local balance to manager:', numBalance);
                        window.balanceManager.updateBalance(numBalance, 'roulette-correction');
                    }
                    this.lastBalanceSync = Date.now();
                }
                
                return numBalance;
            }
        }
        
        // PRIORITY 2: Try balance manager only as fallback (less frequently)
        if (window.balanceManager && (!this.lastManagerCheck || 
            (Date.now() - this.lastManagerCheck) > 2000)) { // 2 second throttle
            
            this.lastManagerCheck = Date.now();
            const managerBalance = window.balanceManager.getBalance();
            
            if (managerBalance >= 0) {
                console.log('💰 Fallback to balance manager:', managerBalance);
                this.userBalance = managerBalance;
                this.updateBalanceDisplay();
                return managerBalance;
            }
        }
        
        // PRIORITY 3: Return last known balance or default
        if (this.userBalance > 0) {
            console.log('📋 Using last known balance:', this.userBalance);
            return this.userBalance;
        }
        
        console.warn('⚠️ Using default balance fallback');
        return 5000; // Minimal fallback
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

        // Update balance if provided
        if (result.new_balance !== undefined && result.new_balance !== null) {
            this.userBalance = result.new_balance;
            this.updateBalanceDisplay();
        }
        
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

        // Reset committed amount when clearing bets
        this.committedAmount = 0;
        this.activeBets = [];
        this.selectedNumbers = [];
        this.updateBetDisplay();
        this.updateBalanceDisplay(); // Refresh balance display to remove "In Play" indicator
        this.showNotification('All bets cleared', 'info');
    }

    repeatLastBet() {
        // Implementation for repeating the last bet
        this.showNotification('Repeat last bet functionality coming soon', 'info');
    }


    async requestSpin() {
        // Prevent multiple simultaneous spin requests
        if (this.isSpinning) {
            console.warn('Spin already in progress, ignoring request');
            return;
        }

        if (this.gameState !== 'betting') {
            this.showNotification('Cannot spin at this time', 'warning');
            return;
        }

        if (this.activeBets.length === 0) {
            this.showNotification('Place at least one bet to spin', 'warning');
            return;
        }

        // Set spinning state to prevent race conditions
        this.isSpinning = true;

        try {
            // Clean activeBets data - only send fields expected by backend
            const cleanedBets = this.activeBets.map(bet => ({
                type: bet.type,
                value: bet.value,
                amount: bet.amount
            }));

            // Log request data for debugging
            console.log('Roulette spin request:', {
                betsCount: cleanedBets.length,
                bets: cleanedBets,
                gameState: this.gameState,
                timestamp: new Date().toISOString()
            });

            const response = await fetch('/api/gaming/roulette/spin', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
                },
                body: JSON.stringify({
                    bets: cleanedBets,
                    current_balance: this.getSafeBalance() // Send current balance for server sync
                })
            });

            const result = await response.json();
            
            // Log response for debugging
            console.log('Roulette spin response:', {
                status: response.status,
                ok: response.ok,
                result: result,
                timestamp: new Date().toISOString()
            });
            
            if (response.ok) {
                this.handleSpinResult(result);
            } else {
                console.error('Roulette spin failed:', {
                    status: response.status,
                    statusText: response.statusText,
                    error: result.error || result.message || 'Unknown error',
                    fullResponse: result
                });
                this.showNotification(result.error || result.message || 'Failed to spin wheel', 'error');
                // Reset spinning state on error
                this.isSpinning = false;
            }
        } catch (error) {
            console.error('Spin request error:', {
                error: error.message,
                stack: error.stack,
                activeBets: this.activeBets,
                gameState: this.gameState
            });
            this.showNotification('Network error during spin', 'error');
            // Reset spinning state on error
            this.isSpinning = false;
        }
    }

    handleSpinResult(result) {
        // Validate response structure
        if (!result || !result.data) {
            console.error('Invalid spin result structure:', result);
            this.showNotification('Invalid response from server', 'error');
            this.gameState = 'betting';
            // Reset spinning state on invalid response
            this.isSpinning = false;
            return;
        }

        this.gameState = 'spinning';
        
        // Access winning number from correct data structure
        const winningNumber = result.data.winning_number;
        this.spinToNumber(winningNumber);
        
        // Process the delayed balance update with bet deduction and winnings
        this.processDelayedBalanceUpdate(result.data);
        
        // Show result after animation
        setTimeout(() => {
            this.showGameResult(result);
            this.gameState = 'betting';
            // Reset spinning state after animation completes
            this.isSpinning = false;
        }, ROLL_TIME * 1000 + 1000);
    }

    processDelayedBalanceUpdate(resultData) {
        // Calculate the final balance based on committed bets and winnings
        const totalBetAmount = this.committedAmount;
        const totalWinnings = resultData.total_payout || resultData.total_winnings || 0;

        // Deduct committed amount and add winnings
        const newBalance = this.userBalance - totalBetAmount + totalWinnings;

        console.log('Processing delayed balance update:', {
            originalBalance: this.userBalance,
            totalBetAmount: totalBetAmount,
            totalWinnings: totalWinnings,
            newBalance: newBalance
        });

        // Reset committed amount since bets are now settled
        this.committedAmount = 0;

        // Update balance with server value if provided, otherwise use calculated value
        const finalBalance = resultData.new_balance !== undefined ? resultData.new_balance : newBalance;

        // Delay the balance update until after the spin animation completes
        setTimeout(() => {
            this.updateBalance(finalBalance, 'spin_result');
            console.log('Balance updated after spin result reveal');
        }, ROLL_TIME * 1000 + 1000); // Same timing as result display
    }

    spinToNumber(winningNumber) {
        const wheelsContent = document.getElementById('wheelsContent');
        const wheelsHolder = document.getElementById('wheelsHolder');
        if (!wheelsContent || !wheelsHolder) return;

        // Validate winning number
        if (winningNumber === undefined || winningNumber === null || isNaN(winningNumber)) {
            console.error('Invalid winning number for animation:', winningNumber);
            // Fallback: don't animate, just show a default state
            return;
        }

        // Ensure winning number is in valid range (0-36)
        if (winningNumber < 0 || winningNumber > 36) {
            console.error('Winning number out of range:', winningNumber);
            return;
        }

        const currentBox = NUMS.indexOf(this.currentPosition);
        const nextBox = NUMS.indexOf(winningNumber);
        
        // Additional validation for NUMS array
        if (nextBox === -1) {
            console.error('Winning number not found in NUMS array:', winningNumber);
            return;
        }
        
        // Calculate the shortest path to the winning number
        const boxShift = currentBox > nextBox 
            ? NUMS.length - currentBox + nextBox 
            : nextBox - currentBox;

        // Compute offsets on the content strip and align winning chunk center to holder center
        const itemWidth = this.chunkWidth || 70;
        const fullWheelWidth = NUMS.length * itemWidth; // width of one strip

        // Parse current transform X position
        let currentOffset = 0;
        const tr = wheelsContent.style.transform;
        if (tr && tr.startsWith('matrix')) {
            try {
                currentOffset = parseInt(tr.replace('matrix(1, 0, 0, 1, ', '').split(',')[0]) || 0;
            } catch (_) { currentOffset = 0; }
        }

        // Center of holder where the pointer is
        const holderCenter = wheelsHolder.clientWidth / 2;

        // Choose random full cycles to make spin feel real, and compute absolute target
        const cycles = 3 + Math.floor(Math.random() * 3); // 3..5 full rotations
        const nIndex = cycles * NUMS.length + nextBox; // absolute chunk index to land under center
        let targetOffset = holderCenter - ((nIndex + 0.5) * itemWidth);

        // Apply animation to content strip
        wheelsContent.style.transitionDuration = `${ROLL_TIME}s`;
        wheelsContent.style.transitionTimingFunction = 'cubic-bezier(0.25, 0.46, 0.45, 0.94)';
        wheelsContent.style.transform = `matrix(1, 0, 0, 1, ${targetOffset}, 0)`;

        this.currentPosition = winningNumber;
        this.isRolling = true;
        
        console.log(`Wheel animation: current=${currentOffset}, target=${targetOffset}, winning=${winningNumber}`);

        // Add spinning effects
        const wheelContainer = document.querySelector('.wheel-container');
        if (wheelContainer) {
            wheelContainer.classList.add('spinning-effects');
            setTimeout(() => {
                wheelContainer.classList.remove('spinning-effects');
            }, ROLL_TIME * 1000);
        }

        // Highlight winning segment and normalize position
        setTimeout(() => {
            this.isRolling = false; // Reset rolling state
            
            // After animation, normalize content position to a small range to prevent drift
            const currentTransform = wheelsContent.style.transform;
            if (currentTransform) {
                const currentPos = parseInt(currentTransform.replace('matrix(1, 0, 0, 1, ', '').split(',')[0] || '0');
                const normalizedPos = ((currentPos % fullWheelWidth) + fullWheelWidth) % fullWheelWidth - fullWheelWidth; // keep within [-full, 0]
                // Remove transition for snap normalization, then restore
                const prevDuration = wheelsContent.style.transitionDuration;
                wheelsContent.style.transitionDuration = '0s';
                wheelsContent.style.transform = `matrix(1, 0, 0, 1, ${normalizedPos}, 0)`;
                // Force reflow then restore duration for next spin
                void wheelsContent.offsetWidth;
                wheelsContent.style.transitionDuration = prevDuration;
                console.log(`Position normalized: ${currentPos} -> ${normalizedPos}`);
            }

            // Highlight the chunk under the center pointer
            const holderRect = wheelsHolder.getBoundingClientRect();
            const centerX = holderRect.left + holderRect.width / 2;
            const centerY = holderRect.top + holderRect.height / 2;
            const el = document.elementFromPoint(centerX, centerY);
            let chunkEl = el;
            if (chunkEl && !chunkEl.classList.contains('chunk')) {
                chunkEl = chunkEl.closest('.chunk');
            }
            if (chunkEl) {
                chunkEl.classList.add('winning-segment');
                setTimeout(() => {
                    chunkEl.classList.remove('winning-segment');
                }, 2000);
            }
            
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
        // Access data from correct structure (handle both formats)
        const data = result.data || result;
        const winning_number = data.winning_number;
        const winning_bets = data.winning_bets || data.payouts || [];
        const total_payout = data.total_payout || data.total_winnings || 0;
        const net_winnings = data.net_winnings || (total_payout > 0 ? total_payout - (data.total_bet || 0) : 0);
        const new_balance = data.new_balance;
        const is_winner = data.is_winner || total_payout > 0;
        
        // Update balance and ensure committed amount is cleared
        if (new_balance !== undefined) {
            this.userBalance = new_balance;
            this.committedAmount = 0; // Ensure committed amount is cleared
            this.updateBalanceDisplay();
        }

        // Update last numbers display
        this.updateLastNumbers(winning_number);

        // Show result modal with accurate information
        const resultContent = `
            <div class="result-info">
                <h3>Winning Number: <span class="${this.getColorClass(winning_number)}">${winning_number !== undefined ? winning_number : 'Error'}</span></h3>
                <h4>Total Win: ${net_winnings} GEM</h4>
                ${winning_bets && winning_bets.length > 0 ? winning_bets.map(p => `
                    <div class="payout-item">
                        <div>Bet: ${p.type || p.bet_type} ${p.value || p.bet_value}</div>
                        <div>Win: ${p.payout || p.amount} GEM</div>
                    </div>
                `).join('') : '<div class="no-wins">No winning bets this round</div>'}
                <div class="provably-fair">
                    <h5>Provably Fair Verification:</h5>
                    <small>Server Seed: ${data.server_seed || 'N/A'}</small><br>
                    <small>Client Seed: ${data.client_seed || 'N/A'}</small><br>
                    <small>Nonce: ${data.nonce || 'N/A'}</small>
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
            
            // Handle loading errors gracefully
            audio.addEventListener('error', (e) => {
                // Silently ignore audio loading errors - don't spam console
            });
            
            audio.play().catch(() => {
                // Silently ignore audio playback errors - don't spam console
            });
        } catch (error) {
            // Silently ignore audio initialization errors
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
            // Safe balance initialization with auth manager sync
            await this.initializeSafeBalance();
            
            // Try to load user session and connect to WebSocket
            const sessionId = window?.ROULETTE_SESSION_ID || 'demo-session';
            const token = localStorage.getItem('access_token') || 'undefined';
            
            if (sessionId && token && token !== 'undefined') {
                await this.connectWebSocket(sessionId, token);
                this.gameState = 'betting';
            } else {
                // No authentication - show login prompt
                console.log('No authentication detected - prompting for login');
                this.showErrorAlert('Please log in to play roulette. <a href="/login" class="alert-link">Login here</a>');
                this.gameState = 'requires_auth';
                return;
            }
            
            // Initialize balance and update display
            await this.initializeSafeBalance();
            this.updateBalanceDisplay();
            
        } catch (e) {
            console.warn('Session load failed, will retry balance from server:', e);
            this.gameState = 'betting';
            // Don't set fallback balance here - let initializeSafeBalance handle it
            await this.initializeSafeBalance(); // Ensure balance is loaded
            this.updateBalanceDisplay();
        }
    }
    
    async initializeSafeBalance() {
        // Enhanced balance initialization using server endpoint for persistence
        let balance = null; // No default - force server lookup
        
        try {
            // First priority: Get balance from server for both demo and authenticated users
            const response = await fetch('/api/gaming/roulette/balance');
            if (response.ok) {
                const result = await response.json();
                if (result.status === 'success' && result.data) {
                    balance = result.data.balance;
                    console.log('Balance loaded from server:', balance);
                    this.updateBalance(balance, 'server_sync');
                } else {
                    console.warn('Server balance request failed:', result);
                }
            } else {
                console.warn('Server balance endpoint unavailable:', response.status);
            }
        } catch (error) {
            console.warn('Failed to fetch balance from server, using fallback:', error);
        }
        
        // Use balance manager for fallback instead of sessionStorage
        if (balance === null && window.balanceManager) {
            const managerBalance = window.balanceManager.getBalance();
            if (managerBalance > 0) {
                balance = managerBalance;
                console.log('✅ Balance restored from balance manager:', balance);
            }
        }
        
        // Ensure balance is valid - use minimal fallback and trigger server refresh
        if (balance === null || isNaN(balance) || balance < 0) {
            balance = 1000; // Minimal fallback for demo users
            console.warn('No valid balance found, using minimal fallback and refreshing from server:', balance);
            // Trigger async server refresh without waiting
            setTimeout(() => this.refreshBalanceFromServer(), 100);
        }
        
        this.userBalance = balance;
        console.log('Initialized roulette balance:', balance);
    }
    
    async refreshBalanceFromServer() {
        // Refresh balance from server without fallbacks
        try {
            console.log('Refreshing balance from server...');
            const response = await fetch('/api/gaming/roulette/balance');
            if (response.ok) {
                const result = await response.json();
                if (result.status === 'success' && result.data && result.data.balance) {
                    const serverBalance = result.data.balance;
                    console.log('Server balance refreshed:', serverBalance);
                    // Update balance
                    this.updateBalance(serverBalance, 'server_load');
                    if (false) {
                        this.userBalance = serverBalance;
                        this.updateBalanceDisplay();
                    }
                    return serverBalance;
                } else {
                    console.warn('Server balance refresh failed:', result);
                }
            } else {
                console.warn('Server balance refresh request failed:', response.status);
            }
        } catch (error) {
            console.error('Error refreshing balance from server:', error);
        }
        return null;
    }
    
    setMaxBetAmount() {
        const availableBalance = this.getSafeBalance() - this.committedAmount;
        const maxAllowed = Math.min(availableBalance, MAX_BET);
        this.currentBetAmount = Math.max(MIN_BET, maxAllowed);
        this.betAmountSelected = true;
        this.updateBetAmountDisplay();
        this.clearCustomBetInput();
        this.showNotification(`Max bet set: ${this.currentBetAmount} GEM`, 'success');
    }
    
    validateCustomBetAmount() {
        const input = document.getElementById('custom-bet-amount');
        const feedback = document.getElementById('bet-validation-message');

        if (!input || !feedback) return false;

        const value = parseFloat(input.value);
        const balance = this.getSafeBalance() - this.committedAmount;
        
        // Clear previous classes
        feedback.className = 'bet-validation-feedback';
        
        if (!input.value) {
            feedback.textContent = '';
            return false;
        }
        
        if (isNaN(value) || value <= 0) {
            feedback.textContent = 'Please enter a valid amount';
            feedback.classList.add('invalid');
            return false;
        }
        
        if (value < MIN_BET) {
            feedback.textContent = `Minimum bet is ${MIN_BET} GEM`;
            feedback.classList.add('invalid');
            return false;
        }
        
        if (value > MAX_BET) {
            feedback.textContent = `Maximum bet is ${MAX_BET} GEM`;
            feedback.classList.add('invalid');
            return false;
        }
        
        if (value > balance) {
            feedback.textContent = 'Insufficient available balance';
            feedback.classList.add('invalid');
            return false;
        }
        
        // Valid amount
        feedback.textContent = `✓ Valid amount: ${value} GEM`;
        feedback.classList.add('valid');
        return true;
    }
    
    setCustomBetAmount() {
        if (!this.validateCustomBetAmount()) {
            return;
        }
        
        const input = document.getElementById('custom-bet-amount');
        const amount = parseFloat(input.value);
        
        this.currentBetAmount = amount;
        this.betAmountSelected = true;
        this.updateBetAmountDisplay();
        this.clearCustomBetInput();
        this.showNotification(`Custom bet set: ${amount} GEM`, 'success');
    }
    
    clearCustomBetInput() {
        const input = document.getElementById('custom-bet-amount');
        const feedback = document.getElementById('bet-validation-message');
        
        if (input) input.value = '';
        if (feedback) {
            feedback.textContent = '';
            feedback.className = 'bet-validation-feedback';
        }
    }
    
    updateBetAmountDisplay() {
        // Update the current bet amount display
        const display = document.getElementById('bet-amount-display');
        if (display) {
            display.textContent = this.betAmountSelected ? `${this.currentBetAmount} GEM` : '0 GEM';
        }
        
        // Update potential winnings for the most likely bet (color bet 2:1)
        const potentialWinnings = document.getElementById('potential-winnings');
        if (potentialWinnings) {
            const estimatedPayout = this.betAmountSelected ? (this.currentBetAmount * 2) : 0; // Most common payout
            potentialWinnings.textContent = `${estimatedPayout} GEM`;
        }
        
        // Update button active states
        document.querySelectorAll('.bet-amount-btn').forEach(btn => {
            const amount = parseInt(btn.dataset.amount);
            if (this.betAmountSelected && amount === this.currentBetAmount) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        
        // Update custom input max attribute based on current balance
        const customInput = document.getElementById('custom-bet-amount');
        if (customInput) {
            customInput.max = Math.min(this.getSafeBalance(), MAX_BET);
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
    console.log('Enhanced Crypto roulette system initialized with full functionality');
});
