class RouletteGame {
    // Round phases - sequential, prevent concurrent operations
    static ROUND_PHASES = {
        BETTING: 'betting',
        SPINNING: 'spinning',
        RESULTS: 'results',
        CLEANUP: 'cleanup'
    };

    constructor() {
        this.MIN_BET = 10;
        this.MAX_BET = 10000;
        this.ROUND_DURATION = 15000;

        // Core game state - streamlined
        this.gameId = null;
        this.balance = 0;
        this.currentAmount = 100;
        this.currentBets = [];
        this.isProcessing = false;
        this.isSpinning = false;
        this.roundTimer = null;

            // Round state management - PREVENTS timing conflicts and multi-spin issues
        this.roundPhase = RouletteGame.ROUND_PHASES.BETTING;
        this.roundId = 1;
        this.spinInProgress = false; // Prevent multiple simultaneous spin attempts
        this.spinLockActive = false; // Guards against rapid multiple spin requests

        // Balance management - critical fixes (enhanced)
        this.pendingBalanceSync = false;
        this.lastServerBalance = 0;
        this.balanceSyncQueue = [];
        this.betTransactionId = null;
        this.balanceOperationLock = false; // Prevent concurrent balance operations
        this.transactionQueue = []; // Queue for sequential balance transactions

        // Visual elements cache
        this.elements = {};

        // Bot system state
        this.botActivityInterval = null;
        this.liveBetFeed = [];
        this.roundBots = [];

        // Server-managed round system (SSE)
        this.sseConnection = null;
        this.sseReconnectAttempts = 0;
        this.pollingFallbackInterval = null;
        this.serverRoundState = null;

        // Auto-bet state
        this.autoBetEnabled = false;
        this.bettingStrategy = 'manual';
        this.autoBetRoundsLeft = 0;
        this.sessionProfit = 0;
        this.sessionRounds = 0;
        this.consecutiveWins = 0;

        // Achievement state
        this.achievements = {
            firstWin: false,
            bigBet: false,
            consecutiveWins5: false,
            profit1000: false,
            spins100: false
        };
        this.totalRounds = 0;
        this.biggestBet = 0;

        // ===== FUNNY USERNAME & AVATAR DATA =====

        // Name components for generating funny usernames
        this.namePrefixes = [
            'Bob', 'Joe', 'Sally', 'Tom', 'Jenny', 'Mike', 'Dave', 'Steve',
            'Chris', 'Pat', 'Alex', 'Taylor', 'Jordan', 'Morgan', 'Riley', 'Casey',
            'Sam', 'Jamie', 'Lee', 'Robin', 'Robin', 'Jesse', 'Patty', 'Terry',
            'Robin', 'Frank', 'Harry', 'Charlie', 'Max', 'Buddy', 'Sparky', 'Coco',
            'Biscuit', 'Noodle', 'Pickle', 'Waffles', 'Cupcake', 'Marshmallow', 'Jello'
        ];

        this.nameSuffixes = [
            'Bob', 'Joe', 'Smith', 'Jones', 'Brown', 'Davis', 'Miller', 'Wilson',
            'Moore', 'Taylor', 'Anderson', 'Thomas', 'Jackson', 'White', 'Harris', 'Martin',
            'Thompson', 'Garcia', 'Martinez', 'Robinson', 'Clark', 'Rodriguez', 'Lewis', 'Lee',
            'Walker', 'Hall', 'Allen', 'Young', 'Hernandez', 'King', 'Wright', 'Lopez',
            'Hill', 'Scott', 'Green', 'Adams', 'Baker', 'Gonzalez', 'Nelson', 'Carter',
            'Mitchell', 'Perez', 'Roberts', 'Turner', 'Phillips', 'Campbell', 'Parker', 'Evans'
        ];

        this.nameWords = [
            'Dog', 'Cat', 'Bread', 'Cheese', 'Tree', 'Rock', 'Cloud', 'Mountain',
            'River', 'Ocean', 'Star', 'Moon', 'Sun', 'Rain', 'Snow', 'Fire',
            'Ice', 'Wind', 'Thunder', 'Storm', 'Lightning', 'Rainbow', 'Bridge', 'Castle',
            'Forest', 'Garden', 'Island', 'Desert', 'Candy', 'Cookie', 'Cake', 'Pie',
            'Pizza', 'Burger', 'Hotdog', 'Taco', 'Nacho', 'Fries', 'Chicken', 'Duck',
            'Bear', 'Wolf', 'Fox', 'Rabbit', 'Deer', 'Eagle', 'Owl', 'Hawk',
            'Sword', 'Shield', 'Crown', 'Castle', 'Dragon', 'Wizard', 'Magic', 'Potion'
        ];

        // Avatar emojis for bot players
        this.playerAvatars = [
            '🤖', '💎', '⚡', '🚀', '🦄', '🌟', '🎯', '🔥', '💰', '🤑', '🎰', '🎲',
            '🤡', '👻', '🧙', '🧌', '🧛', '🧟', '🦹', '🦸', '🦺', '🦴', '🦷', '🦊',
            '🐺', '🐱', '🐶', '🐭', '🐹', '🐰', '🦌', '🐯', '🐱', '🐶', '🐭', '🐹',
            '🦆', '🦢', '🦉', '🦅', '🦜', '🐔', '🐧', '🐦', '🐤', '🐣', '🦉', '🦅'
        ];

        this.init();
    }

    async init() {
        this.cacheElements();
        this.bindEventListeners();
        this.generateNumberGrid();
        this.initializeWheelLoop(); // NEW: Initialize seamless wheel scrolling
        this.syncInitialBalance();
        this.updateBetAmountDisplay();
        this.updateBetSummary();

        try {
            await this.ensureGameSession();
        } catch (error) {
            console.error('Failed to create roulette session', error);
            this.showNotification('Unable to create game session. Using demo mode.', 'error');
        }

        // Initialize bots when game loads
        await this.initializeBotSystem();

        // Initialize bot arena
        this.initializeBotArena();

        // Connect to server-managed rounds (SSE)
        this.connectToRoundStream();

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

    initializeWheelLoop() {
        // IMPORTANT: For now, skip wheel duplication to keep it simple
        // The existing HTML already has all 37 numbers visible
        // We'll add duplication later only if needed for seamless looping

        const wheelNumbers = document.getElementById('wheelNumbers');
        if (!wheelNumbers) {
            console.warn('⚠️ wheelNumbers element not found - wheel initialization skipped');
            return;
        }

        // Get all existing wheel number elements
        const numbers = Array.from(wheelNumbers.children);
        console.log(`🎡 Wheel ready with ${numbers.length} numbers (duplication disabled for debugging)`);

        if (numbers.length === 0) {
            console.warn('⚠️ No wheel numbers found in wheelNumbers container');
            return;
        }

        // Clone all numbers to create seamless looping (prevents blank spaces during animation)
        const originalNumbers = Array.from(numbers);
        originalNumbers.forEach(number => {
            const clone = number.cloneNode(true);
            wheelNumbers.appendChild(clone);
        });

        console.log(`✅ Wheel visible with ${numbers.length} numbers (${originalNumbers.length} original + ${originalNumbers.length} cloned for seamless looping)`);
    }

    // ===== BOT SYSTEM INTEGRATION =====

    // Initialize bot system when game loads
    async initializeBotSystem() {
        try {
            console.log('🤖 Initializing bot system...');

            // Load bot stats and population
            await this.loadBotStats();

            // Start bot activity feed (replaces fake bet feed)
            this.startBotActivityFeed();

            console.log('✅ Bot system initialized');
        } catch (error) {
            console.error('❌ Failed to initialize bot system:', error);
        }
    }

    // Initialize the bot arena UI
    initializeBotArena() {
        console.log('🎭 Initializing bot arena...');

        try {
            // Create bot arena container in the game area
            let arena = document.getElementById('bot-activity-arena');
            if (!arena) {
                arena = document.createElement('div');
                arena.id = 'bot-activity-arena';
                arena.className = 'bot-activity-arena';
                arena.innerHTML = `
                    <div class="arena-header">
                        <span class="arena-title">🤖 Bot Arena</span>
                        <span class="player-count" id="arena-player-count">0 players</span>
                    </div>
                    <div class="arena-participants">
                        <div class="arena-placeholder">
                            <div class="placeholder-icon">🎭</div>
                            <div class="placeholder-text">Bot participants will appear here during betting rounds</div>
                        </div>
                    </div>
                `;

                // Add to the game interface - find a good spot
                const gameContainer = document.querySelector('.game-container') ||
                                    document.querySelector('.roulette-container') ||
                                    document.querySelector('.game-interface');

                if (gameContainer) {
                    // Try to add after the betting controls or before the spin button
                    const spinButton = document.getElementById('spinWheel');
                    if (spinButton) {
                        spinButton.parentNode.insertBefore(arena, spinButton);
                    } else {
                        gameContainer.appendChild(arena);
                    }

                    console.log('✅ Bot arena UI created');
                } else {
                    console.warn('⚠️ Could not find game container to add bot arena');
                }
            }

            // Add CSS styles for bot arena
            this.addBotArenaStyles();

        } catch (error) {
            console.error('❌ Failed to initialize bot arena:', error);
        }
    }

    // Add CSS styles for bot arena - isolated to preserve professional styling
    addBotArenaStyles() {
        if (document.querySelector('#bot-arena-styles')) return;

        // Use CSS variables from existing professional theme to maintain consistency
        const primaryColor = getComputedStyle(document.documentElement).getPropertyValue('--gaming-primary') || '#fbbf24';
        const secondaryColor = getComputedStyle(document.documentElement).getPropertyValue('--gaming-secondary') || '#10b981';
        const bgSecondary = getComputedStyle(document.documentElement).getPropertyValue('--gaming-bg-secondary') || '#1e293b';
        const bgTertiary = getComputedStyle(document.documentElement).getPropertyValue('--gaming-bg-tertiary') || '#334155';

        const style = document.createElement('style');
        style.id = 'bot-arena-styles';
        style.textContent = `
            /* Visual Preservation: Bot Arena Styles */
            .bot-activity-arena {
                background: linear-gradient(135deg, #1a1a2e, #16213e);
                border: 2px solid rgba(251, 191, 36, 0.3);
                border-radius: 15px;
                margin: 20px 0;
                padding: 15px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                position: relative;
                overflow: hidden;
                /* Modal Compatibility: Ensure proper layering */
                z-index: 10;
            }

            /* Wins Overlay: Highest Priority */
            .win-celebration-overlay,
            .persistent-result-notification,
            .casino-result-overlay {
                z-index: 9999 !important;
            }

            /* Result Modals: High Priority */
            .result-summary-modal,
            .achievement-modal,
            .session-summary-modal {
                z-index: 9000 !important;
            }

            /* Notifications: Medium Priority */
            .toast-notification-container,
            .bet-announcement {
                z-index: 8000 !important;
            }

            /* Bot Elements: Low Priority */
            .bet-feed-container {
                z-index: 1000 !important;
            }

            .bot-activity-arena::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(45deg,
                    rgba(251, 191, 36, 0.02),
                    rgba(34, 197, 94, 0.02),
                    rgba(251, 191, 36, 0.02));
                pointer-events: none;
            }

            .arena-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                position: relative;
                z-index: 1;
            }

            .arena-title {
                color: #fbbf24;
                font-weight: 700;
                font-size: 1.1rem;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .player-count {
                color: #9ca3af;
                font-size: 0.9rem;
                font-weight: 500;
                padding: 4px 12px;
                background: rgba(251, 191, 36, 0.1);
                border-radius: 20px;
                border: 1px solid rgba(251, 191, 36, 0.2);
            }

            .arena-participants {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                position: relative;
                z-index: 1;
                min-height: 60px;
            }

            .arena-placeholder {
                width: 100%;
                text-align: center;
                color: #6b7280;
                padding: 20px;
                background: rgba(255, 255, 255, 0.02);
                border-radius: 10px;
                border: 1px dashed rgba(251, 191, 36, 0.2);
            }

            .placeholder-icon {
                font-size: 2rem;
                margin-bottom: 10px;
                opacity: 0.5;
            }

            .placeholder-text {
                font-size: 0.9rem;
                font-style: italic;
            }

            .bot-participant {
                background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(251, 191, 36, 0.1));
                border: 1px solid rgba(34, 197, 94, 0.3);
                border-radius: 12px;
                padding: 12px;
                min-width: 160px;
                display: flex;
                align-items: center;
                gap: 10px;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
                animation: botJoin 0.5s ease-out;
            }

            @keyframes botJoin {
                from {
                    opacity: 0;
                    transform: scale(0.8) translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: scale(1) translateY(0);
                }
            }

            .bot-participant::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg,
                    transparent,
                    rgba(34, 197, 94, 0.1),
                    transparent);
                transition: left 0.5s ease;
            }

            .bot-participant:hover::before {
                left: 100%;
            }

            .bot-participant.betting {
                animation: botBetting 1.5s ease-in-out infinite;
            }

            @keyframes botBetting {
                0%, 100% {
                    box-shadow: 0 0 10px rgba(34, 197, 94, 0.3);
                }
                50% {
                    box-shadow: 0 0 20px rgba(34, 197, 94, 0.6);
                }
            }

            .bot-participant .bot-avatar {
                font-size: 2.2rem;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                background: linear-gradient(135deg, rgba(251, 191, 36, 0.2), rgba(34, 197, 94, 0.2));
                border: 1px solid rgba(251, 191, 36, 0.3);
                flex-shrink: 0;
            }

            .bot-info {
                flex: 1;
                min-width: 0;
            }

            .bot-name {
                color: #fbbf24;
                font-weight: 600;
                font-size: 0.95rem;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                margin-bottom: 2px;
                display: block;
            }

            .bot-status {
                color: #9ca3af;
                font-size: 0.8rem;
                font-style: italic;
                transition: all 0.3s ease;
            }

            .bot-status.active-bet {
                color: #22d3ee;
                font-weight: 500;
                animation: betActive 2s ease-in-out infinite;
            }

            @keyframes betActive {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }

            /* Responsive design */
            @media (max-width: 768px) {
                .arena-participants {
                    flex-direction: column;
                }

                .bot-participant {
                    min-width: auto;
                    width: 100%;
                }

                .arena-header {
                    flex-direction: column;
                    gap: 8px;
                    align-items: flex-start;
                }

                .player-count {
                    align-self: flex-end;
                }
            }
        `;
        document.head.appendChild(style);
    }

    // Load bot statistics and count
    async loadBotStats() {
        try {
            // Try to get bot population stats from API
            // Note: We'll simulate this for now as the API might not be ready
            const mockStats = {
                total_bots: 22,
                personalities: {
                    'PREDICTABLE_GAMBLER': 5,
                    'OPPORTUNISTIC': 3,
                    'TREND_FOLLOWER': 4,
                    'CONSERVATIVE': 6,
                    'AGGRESSIVE': 1,
                    'HIGHROLLER': 1,
                    'TIMID': 2
                }
            };

            this.updateBotCounter(mockStats.total_bots);
            console.log(`🤖 Loaded ${mockStats.total_bots} bots`);
            return mockStats;

        } catch (error) {
            console.warn('⚠️ Bot stats API not available, using defaults');
            this.updateBotCounter(22); // Default to 22 bots
            return { total_bots: 22 };
        }
    }

    // Update the bot counter in the header
    updateBotCounter(count) {
        const counterElement = document.getElementById('bots-online-count');
        if (counterElement) {
            counterElement.textContent = count;

            // Update indicator status
            const indicator = document.getElementById('bots-indicator');
            if (indicator) {
                const dot = indicator.querySelector('.pulse-dot');
                if (count > 0) {
                    indicator.classList.remove('offline');
                    indicator.classList.add('online');
                    dot.classList.remove('red');
                    dot.classList.add('green');
                } else {
                    indicator.classList.remove('online');
                    indicator.classList.add('offline');
                    dot.classList.remove('green');
                    dot.classList.add('red');
                }
            }
        }
    }

    // Start showing real bot activities in the live feed
    startBotActivityFeed() {
        if (this.botActivityInterval) return;

        // Clear any existing fake interval
        this.stopLiveBetFeed();

        console.log('🤖 Starting bot activity feed...');

        // Generate initial bot activities
        this.generateBotActivity('DiamondHands', Math.floor(Math.random() * 300) + 50, 'RED');
        this.generateBotActivity('CryptoKing', Math.floor(Math.random() * 200) + 25, 'BLACK');

        // Add bot activities every 6-12 seconds (realistic interval)
        this.botActivityInterval = setInterval(() => {
            this.generateRandomBotActivity();
        }, 6000 + Math.random() * 6000);
    }

    // Stop bot activity feed
    stopBotActivityFeed() {
        if (this.botActivityInterval) {
            clearInterval(this.botActivityInterval);
            this.botActivityInterval = null;
        }
    }

    // Generate a random bot activity
    generateRandomBotActivity() {
        // Bot names from our bot system
        const botNames = [
            'bob', 'bob joe', 'billybob', 'dogbob', 'cryptojoe',
            'cryptobob', 'bitcoinbob', 'satoshisbet', 'hodlbob',
            'hodlbilly', 'moonbob', 'nimblebob', 'cypherpunk',
            'diamondjoe', 'hodljr', 'cryptoking', 'gemhunter',
            'luckycharm', 'diamondhands', 'paperpro', 'hodlmaxwell', 'bitbro'
        ];

        const betTypes = ['RED', 'BLACK', '1-18', '19-36', 'EVEN', 'ODD', 'GREEN'];

        const name = botNames[Math.floor(Math.random() * botNames.length)];
        const amount = Math.floor(Math.random() * 500) + 10; // 10-510 GEM range
        const type = betTypes[Math.floor(Math.random() * betTypes.length)];

        this.generateBotActivity(name, amount, type);
    }

    // Create bot participants for the round when betting starts
    createBotParticipants() {
        // Clear existing participants
        const arena = document.getElementById('bot-activity-arena');
        if (arena) {
            arena.innerHTML = '';
        }

        // Hide the spinning wheel
        const spinningWheel = document.getElementById('bot-spinning-wheel');
        if (spinningWheel) {
            spinningWheel.style.display = 'none';
        }

        // Create 3-5 bot participants for this round
        const numBots = 3 + Math.floor(Math.random() * 3); // 3-5 bots
        const botNames = [
            'DiamondHands', 'CryptoKing', 'LuckyCharm', 'MoonBob', 'NimbleBob',
            'HodlMaxwell', 'BitBro', 'SatoshisBet', 'CryptoJoe', 'DiamondJoe'
        ];

        this.roundBots = [];

        for (let i = 0; i < numBots; i++) {
            const botName = botNames[i];
            const personality = this.getBotPersonality(botName);
            const avatar = this.getRandomBotAvatar(botName);

            const botParticipant = {
                name: botName,
                personality: personality,
                avatar: avatar,
                bet: null,
                element: this.createBotParticipantElement(botName, avatar, personality)
            };

            this.roundBots.push(botParticipant);
            this.addBotToArena(botParticipant);
        }

        // Update player count
        const playerCount = document.getElementById('arena-player-count');
        if (playerCount) {
            playerCount.textContent = `${this.roundBots.length} players`;
        }
    }

    // Create HTML element for a bot participant
    createBotParticipantElement(name, avatar, personality) {
        const element = document.createElement('div');
        element.className = 'bot-participant';
        element.innerHTML = `
            <div class="bot-avatar">${avatar}</div>
            <div class="bot-info">
                <div class="bot-name">${name}</div>
                <div class="bot-status">Deciding...</div>
                <div class="bot-bet-info" style="display: none; font-size: 0.75rem; color: #10b981; margin-top: 2px;">
                    <span class="bet-details"></span>
                </div>
            </div>
        `;
        return element;
    }

    // Add bot to the arena
    addBotToArena(botParticipant) {
        const arena = document.getElementById('bot-activity-arena');
        if (arena) {
            arena.appendChild(botParticipant.element);
        }
    }

    // Make bots place bets during the betting round
    // FIX: Synchronize with round timer (15s) instead of fixed delays
    botsPlaceBets() {
        console.log(`🤖 Bots starting to place bets synchronized with round timer... (Current bets before: ${this.currentBets.length})`);

        // Update arena placeholder to show activity
        const placeholder = document.querySelector('.arena-placeholder');
        if (placeholder) {
            const placeholderText = placeholder.querySelector('.placeholder-text');
            if (placeholderText) {
                placeholderText.textContent = 'Bots are thinking...';
            }
        }

        // FIX: Spread bot bets across first 10 seconds of 15s round
        // This ensures bots finish betting before round timer expires
        const roundDuration = this.ROUND_DURATION || 15000; // 15 seconds
        const bettingWindow = roundDuration * 0.67; // Use first 10 seconds (67% of round)
        const botCount = this.roundBots.length;
        const timeBetweenBots = bettingWindow / (botCount + 1); // Evenly space bot bets

        this.roundBots.forEach((bot, index) => {
            // Calculate delay for this bot (staggered throughout betting window)
            const botDelay = timeBetweenBots * (index + 1);

            setTimeout(() => {
                console.log(`🤖 ${bot.name} placing bet at ${(botDelay/1000).toFixed(1)}s into round...`);
                this.botPlaceSpecificBet(bot);

                // Update bot status during thinking phase
                if (bot.element) {
                    const statusElement = bot.element.querySelector('.bot-status');
                    if (statusElement) {
                        statusElement.textContent = 'Deciding...';
                    }
                }
            }, botDelay);
        });

        console.log(`🤖 ${botCount} bots will place bets over ${(bettingWindow/1000).toFixed(1)} seconds`);

        // Log final bet count after all bots finish
        setTimeout(() => {
            console.log(`✅ Bots finished betting - Total bets now: ${this.currentBets.length}`);
        }, bettingWindow + 1000);
    }

    // Have a specific bot place a bet
    botPlaceSpecificBet(bot) {
        // Generate bot bet based on personality
        const amount = this.generateBotBetAmount(bot.personality);
        const betType = this.generateBotBetType(bot.personality);

        // Convert to API-compatible bet format
        const betMap = {
            'RED': 'RED_BLACK',
            'BLACK': 'RED_BLACK',
            'GREEN': 'RED_BLACK',  // Green still uses RED_BLACK type but with 'green' value
            '1-18': 'HIGH_LOW',
            '19-36': 'HIGH_LOW',
            'EVEN': 'EVEN_ODD',
            'ODD': 'EVEN_ODD'
        };

        const betValueMap = {
            'RED': 'red',
            'BLACK': 'black',
            'GREEN': 'green',
            '1-18': 'low',
            '19-36': 'high',
            'EVEN': 'even',
            'ODD': 'odd'
        };

        // Create the bet
        const betData = {
            type: betMap[betType],
            value: betValueMap[betType],
            amount: amount,
            botName: bot.name
        };

        // Register the bot bet
        this.registerBotBet(betData);

        // Update bot element to show bet
        this.updateBotElementBet(bot, betType, amount);
    }

    // Register bot bet in the system
    registerBotBet(betData) {
        // Actually place the bet through the API
        this.placeBotBetOnServer(betData);

        // Add to our current bets tracking (for UI)
        const betObj = {
            type: betData.type,
            value: betData.value,
            amount: betData.amount,
            betId: `bot-${Date.now()}-${Math.random()}`,
            isBot: true,
            botName: betData.botName
        };

        this.currentBets.push(betObj);

        // Update UI to show bot bets
        this.updateBetSummary();

        // Show announcement
        this.showBetAnnouncement(`${betData.botName} bet ${this.formatAmount(betData.amount)} GEM on ${betData.value.toUpperCase()}`, false);
    }

    // Place bot bet on server (this would integrate with your backend)
    async placeBotBetOnServer(betData) {
        // FIX: Bots should NOT use the player's balance or API!
        // Bots are visual only - they don't actually place real bets
        // Real bot betting would need a separate backend system with bot accounts

        console.log(`🤖 Bot ${betData.botName} bet SIMULATED: ${betData.amount} GEM on ${betData.value} (visual only)`);

        // Return a fake bet ID for UI purposes
        return `bot-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    // Update bot element to show active bet
    updateBotElementBet(bot, betType, amount) {
        // Update status to show they placed a bet
        const statusElement = bot.element.querySelector('.bot-status');
        if (statusElement) {
            statusElement.textContent = 'Bet Placed';
            statusElement.classList.add('active-bet');
        }

        // Show bet details
        const betInfoElement = bot.element.querySelector('.bot-bet-info');
        const betDetailsElement = bot.element.querySelector('.bet-details');
        if (betInfoElement && betDetailsElement) {
            betDetailsElement.textContent = `${betType}: ${this.formatAmount(amount)} GEM`;
            betInfoElement.style.display = 'block';
        }

        bot.element.classList.add('betting');
        bot.bet = { type: betType, amount: amount };
    }

    // Generate appropriate bet amount based on bot personality
    generateBotBetAmount(personality) {
        const baseAmounts = {
            'CONSERVATIVE': [10, 25, 50, 75],
            'TREND_FOLLOWER': [20, 50, 100, 150],
            'OPPORTUNISTIC': [15, 75, 150, 250],
            'AGGRESSIVE': [50, 150, 300, 500],
            'HIGHROLLER': [100, 250, 500, 1000],
            'TIMID': [5, 10, 15, 25],
            'PREDICTABLE_GAMBLER': [25, 50, 100, 200]
        };

        const amounts = baseAmounts[personality] || [20, 50, 100, 200];
        return amounts[Math.floor(Math.random() * amounts.length)];
    }

    // Generate appropriate bet type based on bot personality
    generateBotBetType(personality) {
        const typePreferences = {
            'CONSERVATIVE': ['RED', 'BLACK', 'EVEN', 'ODD', '1-18', '19-36'],
            'TREND_FOLLOWER': ['RED', 'BLACK', '1-18', '19-36'],
            'OPPORTUNISTIC': ['RED', 'BLACK', 'GREEN'],
            'AGGRESSIVE': ['RED', 'BLACK', 'GREEN'],
            'HIGHROLLER': ['GREEN', 'RED', 'BLACK'],
            'TIMID': ['RED', 'BLACK'],
            'PREDICTABLE_GAMBLER': ['EVEN', 'ODD', '1-18', '19-36']
        };

        const types = typePreferences[personality] || ['RED', 'BLACK'];
        return types[Math.floor(Math.random() * types.length)];
    }

    // Add bot activity to feed (replaces fake bets)
    generateBotActivity(playerName, amount, betType) {
        const botEntry = {
            player: playerName,
            amount: amount,
            type: betType,
            timestamp: Date.now(),
            isBot: true,
            avatar: this.getRandomBotAvatar(playerName),
            personality: this.getBotPersonality(playerName)
        };

        this.liveBetFeed.unshift(botEntry);

        // Keep only last 8 entries (more than before since bots are more active)
        if (this.liveBetFeed.length > 8) {
            this.liveBetFeed = this.liveBetFeed.slice(0, 8);
        }

        // Show bet announcement for big bets (>200 GEM)
        if (amount >= 200) {
            this.showBetAnnouncement(`${playerName} bet ${this.formatAmount(amount)} GEM on ${betType}`, true);
        }

        this.updateBetFeedDisplay();
    }

    // Get appropriate avatar for bot name
    getRandomBotAvatar(botName) {
        // Generate consistent avatar based on bot name for recognition
        const emojiSet = ['🤖', '💎', '⚡', '🚀', '🦄', '🌟', '🎯', '🔥', '💰', '🤑', '🎰', '🎲'];
        const hash = botName.split('').reduce((a, b) => {
            a = ((a << 5) - a) + b.charCodeAt(0);
            return a & a;
        }, 0);
        return emojiSet[Math.abs(hash) % emojiSet.length];
    }

    // Get bot personality based on name (from our bot system)
    getBotPersonality(botName) {
        const personalityMap = {
            'bob': 'CONSERVATIVE',
            'cryptojoe': 'TREND_FOLLOWER',
            'cryptobob': 'OPPORTUNISTIC',
            'bitcoinbob': 'CONSERVATIVE',
            'satoshisbet': 'TREND_FOLLOWER',
            'hodlbob': 'CONSERVATIVE',
            'hodlbilly': 'TREND_FOLLOWER',
            'moonbob': 'AGGRESSIVE',
            'nimblebob': 'HIGHROLLER',
            'cypherpunk': 'CONSERVATIVE',
            'diamondjoe': 'CONSERVATIVE',
            'hodljr': 'PREDICTABLE_GAMBLER',
            'cryptoking': 'PREDICTABLE_GAMBLER',
            'gemhunter': 'CONSERVATIVE',
            'luckycharm': 'TREND_FOLLOWER',
            'diamondhands': 'TIMID',
            'paperpro': 'CONSERVATIVE',
            'hodlmaxwell': 'OPPORTUNISTIC',
            'bitbro': 'TIMID'
        };

        return personalityMap[botName.toLowerCase()] || 'PREDICTABLE_GAMBLER';
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
            autoSpinTimerText: document.getElementById('auto-spin-timer-text'),
            autoSpinTimerBar: document.getElementById('auto-spin-timer-progress'),
            previousRolls: document.getElementById('previous-rolls'),
            rollsHistory: document.getElementById('rollsHistory')
        };

        // DEBUG: Verify timer elements were found
        console.log('🎮 Timer elements cached:', {
            timerText: !!this.elements.timerText,
            timerBar: !!this.elements.timerBar,
            timerBarElement: this.elements.timerBar
        });

        // If timer bar not found, try to find it again after a delay
        if (!this.elements.timerBar) {
            console.warn('⚠️ Timer bar not found initially, retrying in 1 second...');
            setTimeout(() => {
                this.elements.timerBar = document.getElementById('timer-progress');
                console.log('🔄 Retry result:', !!this.elements.timerBar);
            }, 1000);
        }
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
        // FIXED: Match backend crypto_wheel configuration from gaming/roulette.py
        // RED numbers: all odd numbers from 1-35
        const redNumbers = new Set([1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35]);
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

    // ===== TRANSACTION LOCKING SYSTEM =====

    // Execute balance operation with proper locking to prevent race conditions
    async executeBalanceTransaction(operation, options = {}) {
        return new Promise((resolve, reject) => {
            // Add operation to transaction queue
            this.transactionQueue.push({
                operation,
                options,
                resolve,
                reject,
                timestamp: Date.now()
            });

            // Process queue if not currently locked
            this.processTransactionQueue();
        });
    }

    // Process the transaction queue sequentially
    async processTransactionQueue() {
        if (this.balanceOperationLock || this.transactionQueue.length === 0) {
            return; // Already processing or queue empty
        }

        this.balanceOperationLock = true;

        while (this.transactionQueue.length > 0) {
            const transaction = this.transactionQueue.shift();

            // Check for transaction timeout (30 seconds)
            if (Date.now() - transaction.timestamp > 30000) {
                console.warn('⚠️ Transaction timeout, skipping:', transaction.operation.name);
                transaction.reject(new Error('Transaction timeout'));
                continue;
            }

            try {
                console.log('🔒 Processing balance transaction:', transaction.operation.name);
                const result = await transaction.operation.call(this, transaction.options);
                transaction.resolve(result);
                console.log('✅ Balance transaction completed successfully');
            } catch (error) {
                console.error('❌ Balance transaction failed:', error);
                transaction.reject(error);
            }

            // Small delay between transactions to prevent overwhelming the server
            await this.delay(100);
        }

        this.balanceOperationLock = false;
    }

    setBalance(amount, { source } = {}) {
        // Use transaction system for critical balance operations
        if (source === 'server-sync' || source === 'roulette') {
            return this.executeBalanceTransaction(this._setBalanceInternal, { amount, source });
        }

        // For non-critical operations, execute immediately
        return this._setBalanceInternal({ amount, source });
    }

    _setBalanceInternal({ amount, source }) {
        const numeric = Number(amount);
        if (!Number.isFinite(numeric)) {
            return false;
        }
        const oldBalance = this.balance;
        const change = numeric - oldBalance;
        this.balance = Math.max(0, numeric);

        // Skip animation for sync operations to prevent visual glitches
        if (source !== 'server-sync' && source !== 'auth' && oldBalance !== this.balance && Math.abs(change) > 0) {
            this.animateBalanceChange(change, source);
        }

        this.updateBalanceDisplay();
        if (this.elements.availableBalance) {
            this.elements.availableBalance.textContent = this.formatAmount(this.balance);
        }

        // Only update bet amount if not from roulette operations to prevent conflicts
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

            // Update Auth module balance immediately (but not during roulette operations)
            if (window.Auth && window.Auth.currentUser && source !== 'roulette') {
                window.Auth.currentUser.wallet_balance = this.balance;
                window.Auth.updateUserInterface();
            }
        }

        return true;
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
        const response = await this.post('/api/gaming/roulette/create', {});
        if (response && response.game_id) {
            this.gameId = response.game_id;
            console.log('Roulette session created', this.gameId);
        }
    }

    async handleBet(type, rawValue, sourceButton) {
        // FIX: Don't block multiple bets with isProcessing during betting phase
        if (this.isProcessing && this.roundPhase !== RouletteGame.ROUND_PHASES.BETTING) {
            console.log('🚫 Bet blocked - processing other operation');
            return;
        }

        const amount = this.currentAmount;
        const betType = this.normalizeBetType(type);
        const betValue = String(rawValue).toLowerCase();

        // Validate balance before proceeding
        if (this.balance < amount) {
            this.showNotification('Insufficient balance!', 'error');
            return;
        }

        const betData = {
            type: betType,
            value: betValue,
            amount,
            source: sourceButton,
            isPlayerBet: true,
            playerName: window.Auth?.currentUser?.username || 'You',
            playerAvatar: window.Auth?.currentUser?.avatar || '👤'
        };

        // Place bet immediately (simplified flow)
        await this.placeBet(betData);
    }

    async placeBet(betData) {
        // FIX: Snapshot balance before bet to detect phantom deductions
        const balanceBeforeBet = this.balance;

        console.log(`🎯 placeBet called - isProcessing: ${this.isProcessing}, phase: ${this.roundPhase}`);

        try {
            await this.ensureGameSession();
            if (!this.gameId) {
                this.showNotification('Game session unavailable.', 'error');
                return;
            }

            // FIX: Check sufficient balance before attempting bet
            if (this.balance < betData.amount) {
                this.showNotification(`Insufficient balance! Need ${betData.amount} GEM, have ${this.balance} GEM`, 'error');
                return;
            }

            const betPayload = {
                bet_type: betData.type,
                bet_value: betData.value,
                amount: betData.amount
            };

            console.log(`💰 Placing bet - Balance before: ${balanceBeforeBet} GEM`);
            const response = await this.post(`/api/gaming/roulette/${this.gameId}/bet`, betPayload);

            if (response && response.success) {
                // Register the bet locally
                // FIX: Explicitly set isPlayerBet and isBot flags for proper detection
                const localBet = {
                    type: betPayload.bet_type,
                    value: betPayload.bet_value,
                    amount: betData.amount,
                    betId: response.bet_id || crypto.randomUUID(),
                    isPlayerBet: true,  // CRITICAL: Must be explicitly true
                    isBot: false,        // CRITICAL: Must be explicitly false
                    playerName: betData.playerName || 'Unknown',
                    playerAvatar: betData.playerAvatar || '👤'
                };

                this.registerBet(localBet);

                // DEBUG: Verify the bet was registered correctly
                console.log(`🔍 DEBUG: Bet registered. localBet =`, JSON.stringify(localBet, null, 2));
                console.log(`🔍 DEBUG: currentBets.length = ${this.currentBets.length}`);
                console.log(`🔍 DEBUG: All currentBets =`, JSON.stringify(this.currentBets, null, 2));

                // FIX: Sync balance from server after successful bet
                await this.refreshBalanceFromServer();
                console.log(`✅ Bet placed successfully - Balance after: ${this.balance} GEM (deducted: ${balanceBeforeBet - this.balance} GEM)`);

                // FIX: Force UI refresh after balance sync
                this.updateBalanceDisplay();
                this.updateBetAmountDisplay();

                this.showNotification(`Bet placed: ${betData.amount} GEM on ${this.formatBetLabel(betData)}`, 'success');

                // DEBUG: Check spin button state after bet
                console.log(`🔍 DEBUG: About to update spin button state...`);
                this.updateSpinButtonState();
                console.log(`🔍 DEBUG: Spin button state updated. Button disabled? ${this.elements.spinButton?.disabled}, Text: ${this.elements.spinButton?.textContent}`);

                console.log(`✅ placeBet completed - ready for next bet`);
            } else {
                const message = response?.error || 'Failed to place bet.';
                console.error(`❌ Bet failed: ${message} - Balance unchanged: ${this.balance} GEM`);
                this.showNotification(`Bet failed: ${message}`, 'error');
            }
        } catch (error) {
            console.error('❌ Bet placement error:', error);
            // FIX: Rollback balance if bet failed but balance changed
            if (this.balance < balanceBeforeBet) {
                console.warn(`⚠️ Balance mismatch detected! Rolling back from ${this.balance} to ${balanceBeforeBet}`);
                this.setBalance(balanceBeforeBet, { source: 'rollback' });
            }
            this.showNotification(`Network error: ${error.message || 'Unknown error'}`, 'error');
        } finally {
            // FIX: Always ensure isProcessing is reset
            this.isProcessing = false;
            console.log(`🏁 placeBet finally block - isProcessing reset to false`);
        }
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
            console.log('🚫 confirmPendingBet blocked:', { pendingLength: this.pendingBets.length, isProcessing: this.isProcessing });
            return;
        }

        const betData = this.pendingBets[0];
        console.log('🤖 confirmPendingBet starting with betData:', betData);
        this.isProcessing = true;

        try {
            // Remove highlight immediately
            if (betData.source) {
                betData.source.classList.remove('bet-pending', 'bet-highlighted');
                console.log('✅ Removed bet highlighting');
            }

            console.log('🎰 Ensuring game session...');
            await this.ensureGameSession();
            console.log('🎰 Game session result:', { gameId: this.gameId });
            if (!this.gameId) {
                console.error('❌ No game session available');
                this.showNotification('Game session unavailable.', 'error');
                this.clearPendingBets();
                return;
            }

            const betPayload = {
                bet_type: betData.type,
                bet_value: betData.value,
                amount: betData.amount
            };

            const apiUrl = `/api/gaming/roulette/${this.gameId}/bet`;
            console.log('🚀 [DEBUG] About to call API:', apiUrl);
            console.log('📤 [DEBUG] Bet payload:', JSON.stringify(betPayload, null, 2));

            // Get auth status
            const authToken = localStorage.getItem('auth_token');
            console.log('🔐 [DEBUG] Auth token exists:', !!authToken);
            if (authToken) {
                const tokenParts = authToken.split('.');
                if (tokenParts.length === 3) {
                    try {
                        const response = await this.post('/api/gaming/roulette/create', {});
                        if (response && response.game_id) {
                            this.gameId = response.game_id;
                            console.log('Roulette session created', this.gameId);
                        }
                    } catch (error) {
                        console.warn('⚠️ Failed to create session during bet confirm:', error);
                    }
                }
            }

            const response = await this.post(apiUrl, betPayload);
            console.log('📥 [DEBUG] Raw API response:', response);

            if (response && response.success) {
                console.log('✅ Bet placement successful, bet_id:', response.bet_id);

                // Register the bet locally
                // FIX: Explicitly set isPlayerBet and isBot flags for proper detection
                const localBet = {
                    type: betPayload.bet_type,
                    value: betPayload.bet_value,
                    amount: betData.amount,
                    betId: response.bet_id || crypto.randomUUID(),
                    isPlayerBet: true,  // CRITICAL: Must be explicitly true
                    isBot: false,        // CRITICAL: Must be explicitly false
                    playerName: betData.playerName || 'Unknown',
                    playerAvatar: betData.playerAvatar || '👤'
                };

                console.log('🎯 [DEBUG] Registering local bet:', localBet);
                this.registerBet(localBet);

                // Sync balance from server after successful bet placement
                console.log('💰 Refreshing balance from server...');
                await this.refreshBalanceFromServer();

                this.showNotification(`Bet confirmed: ${betData.amount} GEM on ${this.formatBetLabel(betData)}`, 'success');
                this.updateSpinButtonState(); // Enable spin button when bets are active
                console.log('🎯 Human bet registration complete');
            } else {
                const message = response?.error || response?.message || 'Failed to place bet.';
                console.error('❌ [DEBUG] Bet placement failed:', { response, message });
                console.error('❌ [DEBUG] Response details:', JSON.stringify(response, null, 2));

                // More specific error messages
                if (response?.error?.toLowerCase().includes('balance')) {
                    this.showNotification('❌ Insufficient balance! Check your GEM amount.', 'error');
                } else if (response?.error?.toLowerCase().includes('session')) {
                    this.showNotification('❌ Game session expired - refreshing...', 'error');
                    this.gameId = null; // Force new session
                } else {
                    this.showNotification(`❌ Bet failed: ${message}`, 'error');
                }

                // Refresh balance on bet failure to ensure UI is in sync
                await this.refreshBalanceFromServer();
            }
        } catch (error) {
            console.error('❌ [DEBUG] Bet confirmation error details:', {
                error: error,
                stack: error.stack,
                message: error.message
            });

            // More specific error handling
            if (error.message?.includes('401')) {
                this.showNotification('❌ Please log in again - authentication expired', 'error');
            } else if (error.message?.includes('403')) {
                this.showNotification('❌ Access denied - check authentication', 'error');
            } else if (error.message?.includes('404')) {
                this.showNotification('❌ Bet API not found - check server connection', 'error');
            } else if (error.message?.includes('500')) {
                this.showNotification('❌ Server error - please try again', 'error');
            } else {
                this.showNotification(`❌ Network error: ${error.message || 'Unknown error'}`, 'error');
            }
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
            // Sort bets so player bets appear first, then bot bets
            const sortedBets = [...this.currentBets].sort((a, b) => {
                if (a.isPlayerBet && !b.isPlayerBet) return -1;
                if (!a.isPlayerBet && b.isPlayerBet) return 1;
                return 0;
            });

            const fragment = document.createDocumentFragment();
            sortedBets.forEach((bet, originalIndex) => {  // Use sorted array, but pass original index for removal
                const item = document.createElement('div');
                const isPlayerBet = bet.isPlayerBet || false;
                item.className = `bet-item ${isPlayerBet ? 'player-bet' : 'bot-bet'}`;

                if (isPlayerBet) {
                    // Player's bet - highlight and show their info
                    item.innerHTML = `
                        <div class="bet-info">
                            <div class="bet-player-info">
                                <span class="player-avatar">${bet.playerAvatar || '👤'}</span>
                                <span class="player-name">${bet.playerName || 'You'}</span>
                            </div>
                            <span class="bet-label">${this.formatBetLabel(bet)}</span>
                        </div>
                        <div class="bet-details">
                            <span class="bet-amount">${this.formatAmount(bet.amount)} GEM</span>
                            <button class="remove-bet" aria-label="Remove bet" title="Remove your bet">
                                <i class="bi bi-x"></i>
                            </button>
                        </div>
                    `;
                    item.querySelector('.remove-bet').addEventListener('click', () => {
                        this.removeBet(originalIndex);
                    });
                } else {
                    // Bot's bet - show as read-only (immersion: don't show "Bot")
                    item.innerHTML = `
                        <div class="bet-info">
                            <div class="bet-player-info">
                                <span class="player-avatar">${this.getRandomAvatar(bet.botName || 'Player')}</span>
                                <span class="player-name">${bet.botName || 'Player'}</span>
                            </div>
                            <span class="bet-label">${this.formatBetLabel(bet)}</span>
                        </div>
                        <div class="bet-details">
                            <span class="bet-amount">${this.formatAmount(bet.amount)} GEM</span>
                        </div>
                    `;
                }

                fragment.appendChild(item);
            });
            this.elements.betsList.appendChild(fragment);
        }

        // Add CSS styles for enhanced bet items if not already present
        this.addBetItemStyles();

        const total = this.currentBets.reduce((acc, bet) => acc + bet.amount, 0);
        const potential = this.currentBets.reduce((acc, bet) => acc + (bet.amount * this.getPayoutMultiplier(bet.type, bet.value)), 0);

        this.elements.totalBet.textContent = `${this.formatAmount(total)} GEM`;
        this.elements.potentialWin.textContent = `${this.formatAmount(potential)} GEM`;
    }

    // Add styles for enhanced bet items
    addBetItemStyles() {
        if (document.querySelector('#enhanced-bet-styles')) return;

        const style = document.createElement('style');
        style.id = 'enhanced-bet-styles';
        style.textContent = `
            .bet-item {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 12px 16px;
                margin-bottom: 8px;
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                transition: all 0.3s ease;
            }

            .bet-item:hover {
                background: rgba(255, 255, 255, 0.08);
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            }

            .player-bet {
                background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(251, 191, 36, 0.05));
                border: 1px solid rgba(16, 185, 129, 0.3);
                box-shadow: 0 2px 8px rgba(16, 185, 129, 0.1);
            }

            .player-bet:hover {
                background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(251, 191, 36, 0.08));
                border-color: rgba(16, 185, 129, 0.5);
                box-shadow: 0 4px 16px rgba(16, 185, 129, 0.2);
            }

            .bot-bet {
                background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.05));
                border: 1px solid rgba(59, 130, 246, 0.3);
                box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
                opacity: 0.85;
            }

            .bot-bet:hover {
                background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(139, 92, 246, 0.08));
                border-color: rgba(59, 130, 246, 0.5);
                box-shadow: 0 4px 16px rgba(59, 130, 246, 0.2);
            }

            .bet-info {
                display: flex;
                flex-direction: column;
                gap: 6px;
                flex: 1;
            }

            .bet-player-info {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 0.9rem;
            }

            .player-avatar {
                font-size: 1.5rem;
                width: 28px;
                height: 28px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }

            .player-name {
                color: #fbbf24;
                font-weight: 600;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
            }

            .bot-bet .player-name {
                color: #60a5fa;
            }

            .bet-label {
                color: #ffffff;
                font-weight: 500;
                font-size: 0.95rem;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
            }

            .bet-details {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .bet-amount {
                color: #10b981;
                font-weight: 600;
                font-size: 1rem;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
            }

            .bot-bet .bet-amount {
                color: #60a5fa;
            }

            .remove-bet {
                background: linear-gradient(45deg, #ef4444, #dc2626);
                border: none;
                border-radius: 50%;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                cursor: pointer;
                transition: all 0.2s ease;
                font-size: 0.8rem;
            }

            .remove-bet:hover {
                background: linear-gradient(45deg, #dc2626, #b91c1c);
                transform: scale(1.1);
                box-shadow: 0 2px 8px rgba(239, 68, 68, 0.4);
            }

            .remove-bet:active {
                transform: scale(0.95);
            }

            .empty-state {
                text-align: center;
                color: #9ca3af;
                font-style: italic;
                padding: 20px;
                margin: 0;
            }

            /* Mobile responsiveness */
            @media (max-width: 768px) {
                .bet-item {
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 8px;
                    padding: 10px 12px;
                }

                .bet-details {
                    width: 100%;
                    justify-content: space-between;
                }

                .player-avatar {
                    font-size: 1.3rem;
                    width: 24px;
                    height: 24px;
                }

                .bet-amount {
                    font-size: 0.9rem;
                }
            }
        `;
        document.head.appendChild(style);
    }

    removeBet(index) {
        const [removed] = this.currentBets.splice(index, 1);
        if (removed) {
            // Only refund if it's a player bet, not a bot bet
            if (removed.isPlayerBet) {
                this.setBalance(this.balance + removed.amount, { source: 'roulette' });
            }
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
        // SERVER-MANAGED SPIN: Trigger the server's round manager to advance to SPINNING phase
        console.log('[Spin] Requesting server-managed spin...');

        // Validate current state
        if (this.roundPhase !== RouletteGame.ROUND_PHASES.BETTING) {
            console.warn(`🚫 Can't spin during ${this.roundPhase} phase`);
            this.showNotification(`Cannot spin during ${this.roundPhase} phase`, 'warning');
            return;
        }

        if (this.spinInProgress || this.spinLockActive) {
            console.warn('🚫 Spin already in progress (lock active)');
            return;
        }

        if (this.currentBets.length === 0) {
            this.showNotification('Place a bet before spinning.', 'warning');
            return;
        }

        // ACTIVATE SPIN LOCK to prevent rapid multiple requests
        this.spinLockActive = true;
        this.spinInProgress = true;

        console.log(`[Spin] Triggering server round manager spin...`);

        this.elements.spinButton?.classList.add('processing');
        this.elements.spinButton.disabled = true;
        this.showNotification('Requesting spin...', 'info');

        try {
            // Call server-managed round spin endpoint (NOT the old game-session spin)
            const response = await this.post('/api/gaming/roulette/round/spin', {});

            if (response && response.success) {
                console.log('✅ Server spin triggered successfully');
                this.showNotification('Spin triggered! Watch the wheel...', 'success');
                // Server will broadcast phase change via polling/SSE
                // UI will update automatically when server transitions to SPINNING phase
            } else {
                const message = response?.error || 'Failed to trigger spin';
                console.error('❌ Server spin failed:', message);
                this.showNotification(message, 'error');
            }
        } catch (error) {
            console.error('❌ Spin request error:', error);
            this.showNotification('Error requesting spin from server', 'error');
        } finally {
            // RELEASE SPIN LOCK after server request completes
            // Note: We don't manually change phase here - let server polling handle it
            this.spinLockActive = false;
            this.spinInProgress = false;
            this.elements.spinButton?.classList.remove('processing');
            this.updateSpinButtonState();
        }
    }

    // ============================================================================
    // LEGACY CODE: This is the OLD handleSpinResult function - DO NOT USE
    // The ACTIVE version is at line ~4835
    // Keeping this for reference only - it can be deleted after testing
    // ============================================================================
    /*
    async handleSpinResult(result) {
        const outcome = result?.result;
        if (!outcome || typeof outcome.number !== 'number') {
            console.error('Invalid spin result', result);
            this.showNotification('Invalid spin result', 'error');
            this.startNewRound();
            return;
        }

        // Start wheel animation immediately - separate from balance operations
        this.animateWheel(outcome.number);

        // Process bets but DON'T SHOW RESULTS YET
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

        // Pre-calculate statistics
        const isWin = totalWinnings > 0;
        const netResult = totalWinnings - totalLosses;
        const multiplier = bets.find(b => b.is_winner)?.multiplier || 1;

        // CRITICAL FIX: Wait for animation to complete before showing ANY results
        const waitForAnimation = () => {
            return new Promise(resolve => {
                const checkAnimationEnd = () => {
                    const now = Date.now();
                    if (this.wheelAnimationEndTime && now >= this.wheelAnimationEndTime) {
                        resolve();
                    } else {
                        setTimeout(checkAnimationEnd, 50); // Check every 50ms
                    }
                };
                checkAnimationEnd();
            });
        };

        try {
            // Wait for wheel animation to complete
            await waitForAnimation();

            // NOW we can update history and show results
            this.updateHistory(outcome.number, outcome.color || 'red');

            // Update session statistics
            this.sessionRounds++;
            this.sessionProfit += netResult;
            this.updateAchievements(totalWinnings, totalLosses);

            // Handle auto-betting
            if (this.autoBetEnabled) {
                if (totalWinnings === 0) { // Loss occurred
                    this.handleAutoBetLoss();
                } else if (totalWinnings > 0) { // Win occurred
                    this.handleAutoBetWin();
                }

                // Check auto-bet stop conditions
                if (this.shouldStopAutoBet()) {
                    this.stopAutoBet();
                } else if (this.autoBetRoundsLeft > 0) {
                    this.autoBetRoundsLeft--;
                    if (this.autoBetRoundsLeft === 0) {
                        this.stopAutoBet();
                    }
                }
            }

            // Sync balance from server AFTER animation completes
            await this.refreshBalanceFromServer();

            // NOW show results - winner number was already displayed during animation
            this.showPersistentResult(isWin, isWin ? totalWinnings : totalLosses);

            // TRANSITION TO CLEANUP PHASE - PREVENT STUCK ROUNDS
            this.roundPhase = RouletteGame.ROUND_PHASES.CLEANUP;
            console.log(`🧹 Round ${this.roundId} entering CLEANUP phase`);

            // Show detailed result modal
            // FIX: Don't wait for modal - show it but continue immediately
            this.showResultSummary(totalWinnings, totalLosses, outcome).catch(err => {
                console.error('❌ Result modal error (ignored):', err);
            });

            // Wait 2 seconds to show result, then continue
            await this.delay(2000);

            // COMPLETE CLEANUP PHASE - RESET FOR NEXT ROUND
            console.log(`🐣 Round ${this.roundId} completed, resetting for next round`);

            // Clear the "CALCULATING RESULTS..." message
            this.updateGamePhase('Round Complete');

            // FIX: Clean up bets AFTER result modal is dismissed by user
            // This prevents visual glitches where bet summary disappears before user sees results
            console.log(`🧹 Clearing ${this.currentBets.length} bets from current round`);
            this.currentBets = [];
            this.updateBetSummary();
            this.updateSpinButtonState();

            // CRITICAL FIX: Reset all phase flags and locks
            this.spinInProgress = false;
            this.spinLockActive = false;

            // TRANSITION TO BETTING PHASE - READY FOR NEXT ROUND
            this.roundPhase = RouletteGame.ROUND_PHASES.BETTING;
            console.log(`🎰 Round ${this.roundId + 1} ready - PHASE: ${this.roundPhase}`);

            // Ensure controls are re-enabled
            this.reEnableBetting();

            // Start next round countdown
            this.startNewRound();

        } catch (error) {
            console.error('Error handling spin result:', error);
            // Fallback - force reset to betting phase even on error
            this.roundPhase = RouletteGame.ROUND_PHASES.BETTING;
            this.spinInProgress = false;
            this.spinLockActive = false;
            this.reEnableBetting();
            this.showNotification('Error displaying results, refresh if needed', 'warning');
            this.startNewRound();
        }
    }
    */
    // ============================================================================

    // Casino-style horizontal roulette bar animation with realistic physics
    animateWheel(number) {
        console.log('🎰 [ANIMATION START] animateWheel called with number:', number);

        const wheelNumbers = document.getElementById('wheelNumbers');
        const wheelContainer = document.querySelector('.wheel-container');
        const pointer = document.querySelector('.wheel-pointer');

        if (!wheelNumbers || !wheelContainer || !pointer) {
            console.warn('❌ [ANIMATION] Roulette elements not found, skipping animation');
            return Promise.resolve();
        }

        console.log('✅ [ANIMATION] Elements found, starting wheel animation to number:', number);

        // Clear any existing animations and reset to neutral starting position
        wheelContainer.classList.remove('wheel-spinning');

        // Casino-style horizontal sliding constants
        const segmentWidth = 70; // px per number
        const totalNumbers = 37; // 0-36
        const containerWidth = wheelContainer.clientWidth;
        const containerCenterX = containerWidth / 2;

        // Calculate final position: center the winning number under the pointer
        const targetNumberOffset = number * segmentWidth; // How far right the number is
        const centeringAdjustment = containerCenterX - (segmentWidth / 2); // Center of container minus half a segment

        // Move wheel left to bring winning number to center
        const finalPosition = centeringAdjustment - targetNumberOffset;

        // Add extra spinning distance for excitement (spin past 3-5 full wheel lengths)
        const fullWheelWidth = totalNumbers * segmentWidth; // 37 × 70 = 2590px
        const extraCycles = 3 + Math.floor(Math.random() * 3); // Random 3-5 full cycles for variety
        const startPosition = finalPosition + (extraCycles * fullWheelWidth);

        console.log(`🎯 [ANIMATION] Targeting number ${number}:
            - Container width: ${containerWidth}px, center: ${containerCenterX}px
            - Target offset: ${targetNumberOffset}px
            - Final position: ${finalPosition}px
            - Start position: ${startPosition}px (${extraCycles} extra cycles)
            - Will spin through ${extraCycles * totalNumbers} numbers`);

        // IMPORTANT: Reset to start position WITHOUT transition (instant jump)
        wheelNumbers.style.setProperty('transition', 'none', 'important');
        wheelNumbers.style.setProperty('transform', `translateX(${startPosition}px)`, 'important');
        wheelNumbers.style.setProperty('filter', 'none', 'important');

        console.log(`📍 [DEBUG] Initial position set to: ${startPosition}px`);
        console.log(`📍 [DEBUG] Current transform: ${wheelNumbers.style.transform}`);
        console.log(`📍 [DEBUG] wheelNumbers actual width: ${wheelNumbers.offsetWidth}px`);
        console.log(`📍 [DEBUG] wheelNumbers scroll width: ${wheelNumbers.scrollWidth}px`);
        console.log(`📍 [DEBUG] Computed transform:`, window.getComputedStyle(wheelNumbers).transform);

        // Two-stage animation timing for realistic casino feel
        const fastSpinDuration = 2000;  // 2s - SUPER FAST initial spin
        const slowdownDuration = 3000;  // 3s - Gradual deceleration to winning number
        const totalDuration = fastSpinDuration + slowdownDuration;

        // Calculate intermediate position (80% of the way through)
        const fastSpinDistance = (startPosition - finalPosition) * 0.80;
        const intermediatePosition = startPosition - fastSpinDistance;

        // Force browser to apply the instant position change before animating
        wheelNumbers.offsetHeight; // Trigger reflow

        // STAGE 1: SUPER FAST SPIN
        setTimeout(() => {
            console.log(`🚀 [ANIMATION STAGE 1] FAST SPIN - Rolling through ${extraCycles} cycles at high speed`);
            console.log(`📍 [DEBUG] Intermediate position: ${intermediatePosition}px`);

            // Heavy blur for super fast spinning
            wheelNumbers.style.setProperty('filter', 'blur(4px) brightness(1.2)', 'important');
            wheelContainer.style.boxShadow = '0 0 40px rgba(0, 245, 255, 0.6)';

            // Fast linear spin (almost no easing - constant high speed)
            wheelNumbers.style.setProperty('transition', `transform ${fastSpinDuration / 1000}s linear`, 'important');
            wheelNumbers.style.setProperty('transform', `translateX(${intermediatePosition}px)`, 'important');

            console.log(`📍 [DEBUG] Stage 1 transform applied: ${wheelNumbers.style.transform}`);
            console.log(`📍 [DEBUG] Stage 1 transition: ${wheelNumbers.style.transition}`);

            // STAGE 2: GRADUAL SLOWDOWN
            setTimeout(() => {
                console.log(`🎯 [ANIMATION STAGE 2] SLOWDOWN - Decelerating to winning number ${number}`);
                console.log(`📍 [DEBUG] Final position: ${finalPosition}px`);

                // Reduce blur as we enter slowdown phase
                wheelNumbers.style.setProperty('filter', 'blur(2px) brightness(1.1)', 'important');

                // Smooth deceleration with strong ease-out (realistic physics)
                wheelNumbers.style.setProperty('transition', `transform ${slowdownDuration / 1000}s cubic-bezier(0.15, 0.7, 0.2, 1)`, 'important');
                wheelNumbers.style.setProperty('transform', `translateX(${finalPosition}px)`, 'important');

                console.log(`📍 [DEBUG] Stage 2 transform applied: ${wheelNumbers.style.transform}`);
                console.log(`📍 [DEBUG] Stage 2 transition: ${wheelNumbers.style.transition}`);

                // Progressive blur reduction during slowdown
                setTimeout(() => {
                    wheelNumbers.style.setProperty('filter', 'blur(1px) brightness(1.05)', 'important');
                }, slowdownDuration * 0.5);

                // Final stop - no blur
                setTimeout(() => {
                    wheelNumbers.style.setProperty('filter', 'none', 'important');
                }, slowdownDuration * 0.8);

            }, fastSpinDuration);

            // Final cleanup and celebration (after both stages complete)
            setTimeout(() => {
                wheelNumbers.style.filter = 'none';
                wheelContainer.style.boxShadow = '';

                console.log('🎉 [ANIMATION] Wheel stopped on number:', number);
                // Store the last winning number so we can keep the wheel positioned on it
                this.lastWinningNumber = number;
                this.playWinningCelebration(number, wheelNumbers, pointer, wheelContainer);
            }, totalDuration - 200);

        }, 50);

        // Store animation completion time
        this.wheelAnimationEndTime = Date.now() + totalDuration;

        // Return Promise that resolves when animation completes
        return new Promise(resolve => {
            setTimeout(() => {
                console.log('✅ [ANIMATION END] Animation completed, resolving promise');
                resolve();
            }, totalDuration + 500); // +500ms buffer for celebration effects
        });
    }

    // Play casino-style winning celebration
    playWinningCelebration(number, wheel, pointer, wheelContainer) {
        // Highlight winning number with casino effects
        const winningNumberElement = wheel.querySelector(`[data-value="${number}"]`);
        if (winningNumberElement) {
            // Casino gold highlight
            winningNumberElement.style.boxShadow = '0 0 30px rgba(251, 191, 36, 1)';
            winningNumberElement.style.transform = 'scale(1.2)';
            winningNumberElement.style.zIndex = '20';

            // Remove highlight after celebration
            setTimeout(() => {
                winningNumberElement.style.boxShadow = '';
                winningNumberElement.style.transform = '';
                winningNumberElement.style.zIndex = '';
            }, 2000);
        }

        // Casino pointer celebration
        if (pointer) {
            pointer.style.animation = 'pointerWinPulse 1.5s ease-in-out';
            setTimeout(() => {
                if (pointer) pointer.style.animation = '';
            }, 1500);
        }

        // Add casino confetti effect
        this.createCasinoSparkle(wheelContainer);
    }

    // Stop all wheel animations (for safety)
    stopWheelAnimations() {
        // Stop any ongoing wheel animations and reset to default position
        const wheelNumbers = document.getElementById('wheelNumbers');
        const wheelContainer = document.querySelector('.wheel-container');

        if (wheelNumbers) {
            // Reset wheel-numbers to starting position
            wheelNumbers.style.transition = 'none';
            wheelNumbers.style.transform = 'translateX(0px)';
            wheelNumbers.style.filter = '';
        }

        if (wheelContainer) {
            wheelContainer.style.boxShadow = '';
            wheelContainer.classList.remove('spinning');
        }

        // DON'T touch .wheel-positioner - it has inline transform that needs to stay
    }

    // Create casino sparkle effects
    createCasinoSparkle(container) {
        for (let i = 0; i < 12; i++) {
            setTimeout(() => {
                const sparkle = document.createElement('div');
                sparkle.className = 'casino-sparkle';
                sparkle.style.cssText = `
                    position: absolute;
                    top: ${30 + Math.random() * 40}%;
                    left: ${40 + Math.random() * 20}%;
                    width: 6px;
                    height: 6px;
                    background: ${Math.random() > 0.5 ? '#fbbf24' : '#22d3ee'};
                    border-radius: 50%;
                    pointer-events: none;
                    animation: casinoSparkle 1s ease-out forwards;
                    z-index: 15;
                `;

                container.style.position = 'relative';
                container.appendChild(sparkle);

                setTimeout(() => {
                    if (sparkle.parentNode) {
                        sparkle.parentNode.removeChild(sparkle);
                    }
                }, 1000);
            }, i * 100);
        }

        // Add sparkle animation CSS if not exists
        if (!document.querySelector('#casino-sparkle-styles')) {
            const style = document.createElement('style');
            style.id = 'casino-sparkle-styles';
            style.textContent = `
                @keyframes casinoSparkle {
                    0% {
                        opacity: 1;
                        transform: scale(0) rotate(0deg);
                    }
                    50% {
                        opacity: 1;
                        transform: scale(1.5) rotate(180deg);
                    }
                    100% {
                        opacity: 0;
                        transform: scale(2) rotate(360deg);
                    }
                }
                @keyframes pointerWinPulse {
                    0%, 100% {
                        transform: translateX(-1px);
                    }
                    50% {
                        transform: translateX(-1px) scale(1.3);
                        filter: drop-shadow(0 0 20px rgba(251, 191, 36, 0.8));
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }

    updateHistory(number, color) {
        // Update top display (above wheel)
        if (this.elements.previousRolls) {
            const entry = document.createElement('div');
            entry.className = `previous-roll ${color || 'red'}`;
            entry.textContent = String(number);
            this.elements.previousRolls.prepend(entry);
            while (this.elements.previousRolls.children.length > 10) {
                this.elements.previousRolls.removeChild(this.elements.previousRolls.lastElementChild);
            }
        }

        // Also update bottom "Previous Results" section
        if (this.elements.rollsHistory) {
            const historyEntry = document.createElement('div');
            historyEntry.className = `history-number ${color || 'red'}`;
            historyEntry.textContent = String(number);
            this.elements.rollsHistory.prepend(historyEntry);
            // Keep last 20 results in the bottom history
            while (this.elements.rollsHistory.children.length > 20) {
                this.elements.rollsHistory.removeChild(this.elements.rollsHistory.lastElementChild);
            }
        }
    }

    // ===== SERVER-MANAGED ROUNDS (SSE) =====

    connectToRoundStream() {
        console.log('[Round Sync] Starting polling-based round sync (SSE temporarily disabled)...');

        // TEMPORARY: Use polling instead of SSE due to authentication issues
        // EventSource doesn't send cookies/auth headers properly in all browsers
        this.fallbackToPolling();
        return;  // Skip SSE for now

        // EventSource for Server-Sent Events (DISABLED TEMPORARILY)
        console.log('[SSE] Connecting to server round stream...');
        this.sseConnection = new EventSource('/api/gaming/roulette/round/stream');

        this.sseConnection.addEventListener('round_started', (event) => {
            const data = JSON.parse(event.data);
            console.log('[SSE] Round started:', data);
            this.handleRoundStarted(data);
        });

        this.sseConnection.addEventListener('phase_changed', (event) => {
            const data = JSON.parse(event.data);
            console.log('[SSE] Phase changed:', data);
            this.handlePhaseChanged(data);
        });

        this.sseConnection.addEventListener('round_results', (event) => {
            const data = JSON.parse(event.data);
            console.log('[SSE] Round results:', data);
            this.handleRoundResults(data);
        });

        this.sseConnection.addEventListener('round_ended', (event) => {
            const data = JSON.parse(event.data);
            console.log('[SSE] Round ended:', data);
            this.handleRoundEnded(data);
        });

        this.sseConnection.addEventListener('round_current', (event) => {
            const data = JSON.parse(event.data);
            console.log('[SSE] Current round state:', data);
            this.handleRoundCurrent(data);
        });

        this.sseConnection.onerror = (error) => {
            console.error('[SSE] Connection error:', error);
            this.sseConnection.close();
            this.fallbackToPolling();
        };

        this.sseConnection.onopen = () => {
            console.log('[SSE] Connection established');
            this.sseReconnectAttempts = 0;
            if (this.pollingFallbackInterval) {
                clearInterval(this.pollingFallbackInterval);
                this.pollingFallbackInterval = null;
            }
        };
    }

    fallbackToPolling() {
        console.log('[Round Sync] Using polling mode (checking server every 2s)');
        if (!this.pollingFallbackInterval) {
            // Fetch immediately
            this.fetchCurrentRound();

            // Then poll every 2 seconds
            this.pollingFallbackInterval = setInterval(() => {
                this.fetchCurrentRound();
            }, 2000);
        }

        // DON'T attempt SSE reconnection since we disabled it
        // (Uncomment below when SSE auth is fixed)
        /*
        setTimeout(() => {
            this.sseReconnectAttempts++;
            if (this.sseReconnectAttempts < 5) {
                console.log(`[SSE] Attempting reconnection (${this.sseReconnectAttempts}/5)...`);
                this.connectToRoundStream();
            }
        }, 10000);
        */
    }

    async fetchCurrentRound() {
        try {
            const response = await this.get('/api/gaming/roulette/round/current');
            if (response && response.round) {
                this.handleRoundCurrent(response.round);
            }
        } catch (error) {
            console.error('[Polling] Failed to fetch current round:', error);
        }
    }

    handleRoundStarted(data) {
        this.serverRoundState = data;
        this.roundId = data.round_number;

        // Clear previous round's bets (server-driven)
        this.currentBets = [];
        this.updateBetSummary();

        // Reset UI
        this.updateGamePhase('Place Your Bets');
        this.updateSpinButtonState();

        // Start server-synchronized timer
        this.startServerSyncedTimer(data.betting_duration, data.started_at, data.ends_at);

        // Re-enable betting controls
        this.reEnableBetting();

        // Trigger bot activity (visual only, synced to round)
        this.createBotParticipants();
        setTimeout(() => this.botsPlaceBets(), 500);
    }

    handlePhaseChanged(data) {
        this.serverRoundState = data;

        if (data.phase === 'SPINNING') {
            // Disable betting immediately
            this.disableBetting();
            this.updateGamePhase('Wheel Spinning...');

            // Stop timer
            if (this.roundTimer) {
                clearInterval(this.roundTimer);
                this.roundTimer = null;
            }

            // Trigger wheel animation with server's outcome
            if (data.outcome !== undefined) {
                this.animateWheel(data.outcome);
            }
        }
    }

    handleRoundResults(data) {
        this.serverRoundState = data;
        this.updateGamePhase('Calculating Results...');

        // Update history
        this.updateHistory(data.outcome, data.color);

        // Show results notification
        setTimeout(() => {
            this.updateGamePhase('Round Complete');
        }, 2000);
    }

    handleRoundEnded(data) {
        // Round completed, waiting for new round to start
        // Server will send round_started event shortly
        console.log('[SSE] Round ending, next round starting soon...');
    }

    handleRoundCurrent(data) {
        // Received current round state (on connection or polling)
        this.serverRoundState = data;

        // Track old phase for transition detection
        const oldPhase = this.roundPhase;
        const oldRoundId = this.roundId;

        // Update round number if it changed (new round started)
        if (data.round_number !== this.roundId) {
            console.log(`[Round Sync] New round detected: ${this.roundId} → ${data.round_number}`);
            this.roundId = data.round_number;
        }

        // Update local phase to match server (server is single source of truth)
        const serverPhase = data.phase;

        switch (serverPhase) {
            case 'betting':
                // Enable betting UI
                this.updateGamePhase('Place Your Bets');
                this.reEnableBetting();
                this.updateSpinButtonState();

                // Update timer display with remaining time from server
                if (data.time_remaining > 0) {
                    this.startPollingTimer(data.time_remaining * 1000);
                }

                // If transitioning FROM results TO betting, clear bets and reset UI
                if (oldPhase === 'results' || oldPhase === 'spinning') {
                    console.log('[Round Sync] Transitioning to BETTING - clearing old bets and resetting UI');
                    this.currentBets = [];
                    this.updateBetSummary();

                    // Reset spin locks for new round
                    this.spinInProgress = false;
                    this.spinLockActive = false;
                    this.isProcessing = false;

                    // Keep wheel on last winning number (don't reset between rounds)
                    const wheelNumbers = document.getElementById('wheelNumbers');
                    if (wheelNumbers && this.lastWinningNumber !== undefined) {
                        // Keep the wheel positioned on the last winning number
                        // The wheel already landed on this number, so just keep it there
                        console.log(`🎯 [Wheel Position] Keeping wheel on last winning number: ${this.lastWinningNumber}`);
                        // Clear any filters but keep the position
                        wheelNumbers.style.setProperty('filter', 'none', 'important');
                    } else if (wheelNumbers) {
                        // First round or no previous winner - center the wheel
                        const segmentWidth = 70;
                        const totalNumbers = 37;
                        const containerWidth = wheelNumbers.parentElement.clientWidth;
                        const containerCenterX = containerWidth / 2;
                        const centerPosition = containerCenterX - (segmentWidth / 2);
                        wheelNumbers.style.setProperty('transition', 'none', 'important');
                        wheelNumbers.style.setProperty('transform', `translateX(${centerPosition}px)`, 'important');
                        console.log(`🔄 [Wheel Reset] First round - centering wheel at ${centerPosition}px`);
                    }

                    // Create new bot participants for this round
                    if (typeof this.createBotParticipants === 'function') {
                        this.createBotParticipants();
                        setTimeout(() => {
                            if (typeof this.botsPlaceBets === 'function') {
                                this.botsPlaceBets();
                            }
                        }, 500);
                    }
                }
                break;

            case 'spinning':
                // Disable betting, show spinning UI
                this.updateGamePhase('Spinning...');
                this.disableBetting();
                this.spinInProgress = true;
                this.updateSpinButtonState();

                // Trigger wheel animation if we have outcome data and weren't already spinning
                console.log('[Round Sync] SPINNING phase - oldPhase:', oldPhase, 'data.outcome:', data.outcome, 'data:', data);

                if (oldPhase !== 'spinning') {
                    // Extract outcome number from server data
                    let outcomeNumber = null;

                    // Server might send outcome_number directly
                    if (typeof data.outcome_number === 'number') {
                        outcomeNumber = data.outcome_number;
                    }
                    // Or nested in outcome object
                    else if (data.outcome && typeof data.outcome.number === 'number') {
                        outcomeNumber = data.outcome.number;
                    }
                    // Or just outcome as number
                    else if (typeof data.outcome === 'number') {
                        outcomeNumber = data.outcome;
                    }

                    if (outcomeNumber !== null) {
                        console.log(`🎰 [Round Sync] Triggering wheel animation to number: ${outcomeNumber}`);
                        this.animateWheel(outcomeNumber);
                    } else {
                        console.warn('⚠️ [Round Sync] SPINNING phase but no outcome number found in data:', data);
                    }
                }
                break;

            case 'results':
                // Show results phase
                this.disableBetting();

                // CRITICAL FIX: Clear spin locks when entering results phase
                this.spinInProgress = false;
                this.spinLockActive = false;

                this.updateSpinButtonState();

                // Only display result details if we have outcome data
                if (data.outcome) {
                    this.updateGamePhase(`Result: ${data.outcome.number} (${data.outcome.color})`);

                    // Update history if not already added
                    if (oldPhase !== 'results') {
                        this.updateHistory(data.outcome.number, data.outcome.color);

                        // CRITICAL FIX: Show result modal when entering results phase with user bets
                        const userBets = this.currentBets.filter(bet => !bet.isBot && !bet.is_bot);
                        if (userBets.length > 0) {
                            console.log('🎯 [Round Sync] User had bets, fetching results and showing modal...');
                            this.fetchAndShowRoundResults(data.round_id, data.outcome, userBets);
                        }
                    }
                } else {
                    this.updateGamePhase('Round Complete');
                }
                break;
        }

        // Update local phase to match server
        this.roundPhase = serverPhase;
    }

    startPollingTimer(remainingMs) {
        // Update timer display using server's time_remaining
        if (this.roundTimer) {
            clearInterval(this.roundTimer);
        }

        this.updateRoundTimer(remainingMs);

        this.roundTimer = setInterval(() => {
            remainingMs -= 200;
            if (remainingMs <= 0) {
                clearInterval(this.roundTimer);
                this.roundTimer = null;
                remainingMs = 0;
            }
            this.updateRoundTimer(remainingMs);
        }, 200);
    }

    startServerSyncedTimer(duration, startedAt, endsAt) {
        // Calculate time remaining based on SERVER time, not local time
        const serverStartTime = new Date(startedAt).getTime();
        const serverEndTime = new Date(endsAt).getTime();

        if (this.roundTimer) {
            clearInterval(this.roundTimer);
        }

        this.roundTimer = setInterval(() => {
            const now = Date.now();
            const remaining = Math.max(0, serverEndTime - now);

            this.updateRoundTimer(remaining);

            if (remaining <= 0) {
                clearInterval(this.roundTimer);
                this.roundTimer = null;
                this.updateGamePhase('Waiting for spin...');
            }
        }, 200);
    }

    // FIX: Consolidated startNewRound - handles timer AND bot logic
    startNewRound() {
        // CRITICAL FIX: Only block during SPINNING (wheel animation)
        // Allow transition from RESULTS → BETTING (this is how rounds progress)
        if (this.roundPhase === RouletteGame.ROUND_PHASES.SPINNING) {
            console.log(`⚠️ startNewRound blocked - currently in ${this.roundPhase} phase`);
            return;
        }

        // CRITICAL FIX: Clear ALL bets from previous round FIRST (only if not already cleared)
        // This prevents infinite bet accumulation bug
        if (this.currentBets.length > 0) {
            console.log(`🔄 startNewRound - Clearing ${this.currentBets.length} bets from previous round`);
            this.currentBets = [];
            this.updateBetSummary();
        } else {
            console.log(`✓ startNewRound - Bets already cleared (likely by server sync)`);
        }

        // CRITICAL FIX: Reset ALL spin locks that were stuck
        console.log(`🔓 Resetting spin locks - Before: spinInProgress=${this.spinInProgress}, spinLockActive=${this.spinLockActive}`);
        this.spinInProgress = false;
        this.spinLockActive = false;
        this.isProcessing = false;
        console.log(`✅ Spin locks reset - After: spinInProgress=${this.spinInProgress}, spinLockActive=${this.spinLockActive}`);

        this.updateSpinButtonState();

        // Clear any previous timer
        if (this.roundTimer) {
            clearInterval(this.roundTimer);
        }

        // Clear any previous bot participants from the UI
        if (typeof this.clearBotArena === 'function') {
            this.clearBotArena();
        }

        // Create bot participants for this round
        if (typeof this.createBotParticipants === 'function') {
            this.createBotParticipants();

            // Start bot betting with synchronized timing
            setTimeout(() => {
                if (typeof this.botsPlaceBets === 'function') {
                    this.botsPlaceBets();
                }
            }, 500);
        }

        // Restart bot activity feed
        if (typeof this.stopBotActivityFeed === 'function') {
            this.stopBotActivityFeed();
        }
        if (typeof this.startBotActivityFeed === 'function') {
            this.startBotActivityFeed();
        }

        // Set round phase to betting
        this.roundPhase = RouletteGame.ROUND_PHASES.BETTING;
        console.log(`✅ Round phase set to BETTING`);

        // Clear "Round Complete" message and show betting phase
        this.updateGamePhase('Place Your Bets');

        // Re-enable betting controls
        if (typeof this.reEnableBetting === 'function') {
            this.reEnableBetting();
        }
        this.updateSpinButtonState();

        // FIX: Force-enable all bet buttons to ensure they're clickable
        const betButtons = document.querySelectorAll('.bet-btn');
        betButtons.forEach(btn => {
            btn.disabled = false;
            btn.classList.remove('disabled');
        });
        console.log(`✅ Force-enabled ${betButtons.length} bet buttons`);

        // Start countdown timer
        const startTime = Date.now();
        this.updateRoundTimer(this.ROUND_DURATION);

        this.roundTimer = setInterval(() => {
            const elapsed = Date.now() - startTime;
            const remaining = Math.max(this.ROUND_DURATION - elapsed, 0);
            this.updateRoundTimer(remaining);

            // When countdown reaches 0, handle next round
            if (remaining === 0) {
                clearInterval(this.roundTimer);
                this.roundTimer = null;

                // Check if we should auto-spin or restart round
                if (this.autoBetEnabled && this.currentBets.length > 0) {
                    // Auto-betting mode - spin automatically
                    if (typeof this.startSpinSequence === 'function') {
                        this.startSpinSequence();
                    }
                } else if (this.currentBets.length > 0) {
                    // Player has bets but hasn't spun - could auto-spin here
                    // For now, just restart the round
                    this.startNewRound();
                } else {
                    // No bets placed, restart round
                    this.startNewRound();
                }
            }
        }, 200);
    }

    updateRoundTimer(remainingMs) {
        if (!this.elements.timerText || !this.elements.timerBar) {
            console.warn('⚠️ Timer elements not found:', {
                timerText: !!this.elements.timerText,
                timerBar: !!this.elements.timerBar
            });
            return;
        }
        const seconds = Math.max(0, remainingMs / 1000);
        const percent = Math.min(100, Math.max(0, (remainingMs / this.ROUND_DURATION) * 100));

        // Update top timer (circular)
        this.elements.timerText.textContent = `${seconds.toFixed(1)}s`;
        this.elements.timerBar.style.width = `${percent}%`;

        // Update auto-spin timer bar (horizontal gradient bar)
        if (this.elements.autoSpinTimerText && this.elements.autoSpinTimerBar) {
            this.elements.autoSpinTimerText.textContent = `${seconds.toFixed(1)}s`;
            this.elements.autoSpinTimerBar.style.width = `${percent}%`;

            // Apply same color classes to auto-spin timer
            this.elements.autoSpinTimerBar.classList.remove('warning', 'critical');
            if (seconds <= 3) {
                this.elements.autoSpinTimerBar.classList.add('critical');
            } else if (seconds <= 7) {
                this.elements.autoSpinTimerBar.classList.add('warning');
            }
        }

        // DEBUG: Log timer state every 5 seconds
        if (Math.floor(seconds) % 5 === 0 && Math.abs(seconds - Math.floor(seconds)) < 0.2) {
            console.log(`⏱️ Timer: ${seconds.toFixed(1)}s | Progress: ${percent.toFixed(1)}% | Width: ${this.elements.timerBar.style.width}`);
        }

        // Change timer color based on remaining time
        this.elements.timerBar.classList.remove('warning', 'critical');
        if (seconds <= 3) {
            this.elements.timerBar.classList.add('critical');
            console.log('🔴 Timer CRITICAL');
        } else if (seconds <= 7) {
            this.elements.timerBar.classList.add('warning');
            console.log('🟡 Timer WARNING');
        }

        // Store current timer for button display
        this.currentTimerSeconds = Math.ceil(seconds);

        // Update spin button with realtime countdown
        this.updateSpinButtonState();
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

    // ===== ENHANCED BALANCE SYNC MANAGEMENT =====

    async refreshBalanceFromServer() {
        // Prevent multiple concurrent sync operations (deduplication)
        if (this.pendingBalanceSync) {
            console.log('🛡️ Balance sync already in progress, skipping duplicate request');
            return this.lastSyncPromise || null; // Return existing promise if available
        }

        this.pendingBalanceSync = true;
        const syncId = Date.now(); // Track this sync operation

        // Store the promise for deduplication
        this.lastSyncPromise = this._performBalanceSync(syncId);

        try {
            const result = await this.lastSyncPromise;
            return result;
        } finally {
            // Clean up when this sync completes (only if it's still the active one)
            if (this.pendingBalanceSync && !--this.activeSyncCount) {
                this.pendingBalanceSync = false;
                this.lastSyncPromise = null;
            }
        }
    }

    async _performBalanceSync(syncId) {
        try {
            // Initialize sync tracking
            this.activeSyncCount = (this.activeSyncCount || 0) + 1;

            console.log(`🔄 [${syncId}] Refreshing roulette balance from server...`);
            const response = await this.get('/api/auth/status');

            if (response && response.authenticated && response.user) {
                const serverBalance = response.user.wallet_balance;
                this.setBalance(serverBalance, { source: 'server-sync' });

                // Update last known server balance for validation
                this.lastServerBalance = serverBalance;

                console.log(`✅ [${syncId}] Server balance synced: ${serverBalance} GEM`);
                return serverBalance;
            } else if (response && response.guest_mode && response.guest_user) {
                const serverBalance = response.guest_user.wallet_balance;
                this.setBalance(serverBalance, { source: 'server-sync' });

                // Update last known server balance
                this.lastServerBalance = serverBalance;

                console.log(`✅ [${syncId}] Guest server balance synced: ${serverBalance} GEM`);
                return serverBalance;
            }

            console.warn(`⚠️ [${syncId}] No balance data in server response`);
            return null;
        } catch (error) {
            console.error(`❌ [${syncId}] Failed to refresh balance from server:`, error);

            // Enhanced error recovery
            return await this._handleBalanceSyncFailure(syncId, error);
        }
    }

    async _handleBalanceSyncFailure(syncId, originalError) {
        console.warn(`🔄 [${syncId}] Attempting fallback balance sync...`);

        // Try Auth module fallback
        if (window.Auth && typeof window.Auth.refreshBalanceGlobally === 'function') {
            try {
                const fallbackBalance = await window.Auth.refreshBalanceGlobally();
                if (fallbackBalance !== null) {
                    console.log(`✅ [${syncId}] Fallback balance sync successful: ${fallbackBalance} GEM`);
                    return fallbackBalance;
                }
            } catch (authError) {
                console.error(`❌ [${syncId}] Auth module fallback also failed:`, authError);
            }
        }

        // If both primary and fallback fail, use last known good balance
        if (this.lastServerBalance && this.lastServerBalance > 0) {
            console.warn(`🛡️ [${syncId}] Using last known balance as emergency fallback: ${this.lastServerBalance} GEM`);
            this.setBalance(this.lastServerBalance, { source: 'emergency-fallback' });
            return this.lastServerBalance;
        }

        console.error(`💥 [${syncId}] All balance sync methods failed, balance may be out of sync`);
        throw new Error(`Balance sync failure: ${originalError.message}`);
    }

    // Validate balance operations before executing
    validateBalanceOperation(amount, operation) {
        const currentBalance = this.balance;
        const requestedAmount = Math.abs(amount);

        // Basic validation
        if (!Number.isFinite(amount) || amount <= 0) {
            throw new Error(`Invalid amount: ${amount}`);
        }

        if (amount > this.MAX_BET) {
            throw new Error(`Amount exceeds maximum bet limit: ${amount} > ${this.MAX_BET}`);
        }

        // Insufficient balance check (with small buffer for race conditions)
        if (requestedAmount > currentBalance + 10) { // 10 GEM buffer
            throw new Error(`Insufficient balance: ${currentBalance} GEM available, ${requestedAmount} GEM required`);
        }

        // Check against minimum bet
        if (amount < this.MIN_BET) {
            throw new Error(`Amount below minimum bet: ${amount} < ${this.MIN_BET}`);
        }

        // Additional validation based on operation type
        if (operation === 'bet' && currentBalance < requestedAmount) {
            // Force balance sync before critical operations
            console.warn('💰 Suspicious balance state detected, forcing immediate sync');
            this.refreshBalanceFromServer();
            throw new Error('Balance validation failed - forcing sync');
        }

        return true;
    }

    updateSpinButtonState() {
        if (!this.elements.spinButton) {
            return;
        }

        // FIX: Only count PLAYER bets for spin button, not bot bets
        // Check for player bets properly - bets without isBot flag OR isBot === false
        const playerBets = this.currentBets.filter(bet => {
            // A bet is a player bet if it's explicitly marked OR if it has neither isBot nor isPlayerBet flags
            // (since user-placed bets may not have these flags set)
            const isNotBot = !bet.isBot && !bet.botName;
            const isExplicitlyPlayer = bet.isPlayerBet === true;
            return isNotBot || isExplicitlyPlayer;
        });
        const hasPlayerBets = playerBets.length > 0;

        // ROUND STATE MANAGEMENT: Check SERVER round state if available (server-managed rounds)
        const serverPhaseCheck = this.serverRoundState
            ? this.serverRoundState.phase === 'betting'
            : this.roundPhase === RouletteGame.ROUND_PHASES.BETTING;

        const canSpin = serverPhaseCheck &&
                       hasPlayerBets &&
                       !this.spinInProgress &&
                       !this.spinLockActive;

        const isCurrentlySpinning = this.roundPhase === RouletteGame.ROUND_PHASES.SPINNING ||
                                    this.roundPhase === 'spinning';

        // Update button to show it's an info display, not an action button
        // The button is always disabled since server auto-spins
        this.elements.spinButton.disabled = true;

        // Show clear status messages with realtime countdown
        if (isCurrentlySpinning) {
            // Use realtime timer if available, otherwise fall back to server state
            const remainingTime = this.currentTimerSeconds || this.serverRoundState?.time_remaining || 0;
            if (remainingTime > 0) {
                this.elements.spinButton.textContent = `⏱️ SPINNING IN ${remainingTime}s`;
            } else {
                this.elements.spinButton.textContent = '🎰 SPINNING NOW...';
            }
        } else if (hasPlayerBets) {
            // Player has bets placed - show countdown to auto-spin
            const remainingTime = this.currentTimerSeconds || 0;
            if (remainingTime > 0) {
                this.elements.spinButton.textContent = `✅ AUTO-SPIN IN ${remainingTime}s`;
            } else {
                this.elements.spinButton.textContent = '✅ BETS PLACED - WAITING FOR SPIN';
            }
        } else {
            // No bets yet
            this.elements.spinButton.textContent = '📍 PLACE YOUR BETS';
        }
    }

    async apiRequest(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        };

        const token = localStorage.getItem('auth_token');
        if (token) {
            defaultOptions.headers['Authorization'] = `Bearer ${token}`;
        }

        const finalOptions = { ...defaultOptions, ...options };
        if (finalOptions.body && typeof finalOptions.body === 'object') {
            finalOptions.body = JSON.stringify(finalOptions.body);
        }

        const response = await fetch(url, finalOptions);
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || `Request failed with status ${response.status}`);
        }
        return response.json();
    }

    async get(url) {
        return this.apiRequest(url, { method: 'GET' });
    }

    async post(url, data = null) {
        return this.apiRequest(url, {
            method: 'POST',
            body: data
        });
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
        // DISABLED: Live Bets popup removed per user request
        return;

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

    // FIX: REMOVED DUPLICATE - using consolidated startNewRound() at line 2167

    // Clear the bot arena between rounds
    clearBotArena() {
        // Remove all bot participants from the arena
        this.roundBots = []; // Clear the bot array
        const arena = document.getElementById('bot-activity-arena');
        if (arena) {
            arena.innerHTML = `
                <div class="arena-header">
                    <span class="arena-title">🤖 Bot Arena</span>
                    <span class="player-count" id="arena-player-count">0 players</span>
                </div>
                <div class="arena-participants">
                    <div class="arena-placeholder">
                        <div class="placeholder-icon">🎭</div>
                        <div class="placeholder-text">Bots are thinking...</div>
                    </div>
                </div>
            `;
        }
    }

    // ENHANCED SYNCED SPIN SEQUENCE - PREVENTS CHAOS
    async startSpinSequence() {
        console.log('🎰 Starting synced spin sequence...');

        // CRITICAL FIX: Clear the round timer IMMEDIATELY to prevent race condition
        // This stops the timer from calling startNewRound() while spin is processing
        if (this.roundTimer) {
            console.log('⏹️ Clearing round timer to prevent double startNewRound() race condition');
            clearInterval(this.roundTimer);
            this.roundTimer = null;
        }

        // FIX: Use only roundPhase system
        this.roundPhase = RouletteGame.ROUND_PHASES.SPINNING;
        this.updateGamePhase('Wheel Spinning...');
        this.updateSpinButtonState();

        // CRITICAL: Disable ALL betting during spin - no exceptions
        this.disableBetting();

        // Stop bot announcements during spin
        this.stopBotActivityFeed();
        this.stopLiveBetFeed();

        try {
            // FIRE API CALL IMMEDIATELY - don't wait for animation
            const spinPromise = this.post(`/api/gaming/roulette/${this.gameId}/spin`, {});

            // Start wheel animation at SAME TIME as API call
            await this.delay(50); // Tiny delay for smooth start
            const animationPromise = this.startUnifiedWheelAnimation();

            // Wait for API to complete (this is usually faster than animation)
            const response = await spinPromise;

            if (response && response.success) {
                console.log('✅ Spin API success, waiting for animation to complete...');

                // CRITICAL FIX: Wait for animation to complete BEFORE showing results
                await animationPromise;
                console.log('🎨 Animation complete, now showing results...');

                // NOW handle the results
                await this.handleSpinResult(response);
            } else {
                const message = response?.error || 'Spin failed.';
                console.error('❌ Spin failed:', message);

                // FORCE cleanup on failure - no stuck states
                this.roundPhase = RouletteGame.ROUND_PHASES.BETTING;
                this.spinInProgress = false;
                this.spinLockActive = false;

                this.showNotification(message, 'error');
                this.statusForceReEnable();
            }
        } catch (error) {
            console.error('❌ Spin sequence error:', error);

            // ULTIMATE FAILSAFE - force reset all state
            this.roundPhase = RouletteGame.ROUND_PHASES.BETTING;
            this.spinInProgress = false;
            this.spinLockActive = false;

            this.showNotification('Error during spin.', 'error');
            this.statusForceReEnable();
        }
    }

    // Enhanced spin result handling with proper timing
    async handleSpinResult(result) {
        console.log('🎰 Processing spin results...');

        try {
            const outcome = result?.result;
            if (outcome && typeof outcome.number === 'number') {
                // CRITICAL FIX: Animate wheel to winning number and WAIT for animation to complete
                const animationPromise = this.animateWheel(outcome.number);
                this.updateHistory(outcome.number, outcome.color || 'red');

                // FIX: Use roundPhase system consistently
                this.roundPhase = RouletteGame.ROUND_PHASES.RESULTS;
                this.updateGamePhase('Calculating Results...');

                // CRITICAL: Wait for wheel animation to complete before showing results
                await animationPromise;

            // Update session statistics and auto-betting logic
            this.sessionRounds++;

            // Show detailed win/lose notifications based on individual bets
            const bets = result?.bets || [];
            let totalWinnings = 0;  // Net profit (not including original bet)
            let totalLosses = 0;
            let winningBets = 0;

            bets.forEach(bet => {
                if (bet.is_winner && bet.payout > 0) {
                    winningBets++;
                    // FIX: Backend payout includes original bet (amount * (multiplier + 1))
                    // We want NET PROFIT for display, so subtract the original bet amount
                    const netProfit = bet.payout - bet.amount;
                    totalWinnings += netProfit;
                } else {
                    totalLosses += bet.amount;
                }
            });

            // Update session profit (now using net profit)
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

            // CRITICAL FIX: Capture user bet info BEFORE clearing bets and merge with server results
            const userBetsSnapshot = this.currentBets
                .filter(bet => !bet.isBot && !bet.is_bot)
                .map(bet => {
                    // Find matching result from server bets array
                    const serverBet = bets.find(b =>
                        (b.bet_id === bet.betId) ||
                        (b.bet_type?.toUpperCase() === bet.type?.toUpperCase() &&
                         b.bet_value?.toLowerCase() === bet.value?.toLowerCase())
                    );

                    return {
                        ...bet,
                        is_winner: serverBet?.is_winner || false,
                        payout: serverBet?.payout || 0
                    };
                });
            const userWagered = userBetsSnapshot.reduce((sum, bet) => sum + bet.amount, 0);

            console.log('🎲 User bets with results:', userBetsSnapshot);

            // Show results screen with OK button
            // Pass captured bet data to avoid reading from cleared array
            this.showResultSummary(totalWinnings, totalLosses, outcome, userWagered, userBetsSnapshot).catch(err => {
                console.error('❌ Result modal error (ignored):', err);
            });

            // Wait 2 seconds to show result number, then continue
            await this.delay(2000);

            // Clear the "CALCULATING RESULTS..." message
            this.updateGamePhase('Round Complete');

            // CRITICAL FIX: Don't clear bets here - let startNewRound() handle it
            // Clearing here causes race condition where new bets can't be placed
            // this.currentBets = []; // ← REMOVED: Was causing "can only bet once" bug

            // FIX: Re-enable betting controls and start new round
            // startNewRound() will clear bets at the RIGHT time
            this.reEnableBetting();
            this.startNewRound();
            } else {
                console.error('Invalid spin result', result);
                this.showNotification('Invalid spin result', 'error');
                this.reEnableBetting();
                this.startNewRound();
            }
        } catch (error) {
            console.error('❌ Error in handleSpinResult:', error);
            this.showNotification('Error processing results - continuing anyway', 'error');

            // FAILSAFE: Force reset to betting phase
            this.roundPhase = RouletteGame.ROUND_PHASES.BETTING;
            this.currentBets = [];
            this.updateBetSummary();
            this.reEnableBetting();
            this.startNewRound();
        }
    }

    // Fetch round results from server and show modal (for round sync flow)
    async fetchAndShowRoundResults(roundId, outcome, userBets) {
        try {
            console.log('📊 Fetching round results from server for round:', roundId);

            // Make API call to get the round results with bet details
            const response = await this.apiRequest(`/api/gaming/roulette/round/${roundId}/results`, 'GET');

            if (!response || !response.bets) {
                console.warn('⚠️ No bet results returned from server, showing modal without details');
                // Show modal anyway with calculated results
                const userWagered = userBets.reduce((sum, bet) => sum + bet.amount, 0);
                await this.showResultSummary(0, userWagered, outcome, userWagered, userBets);
                return;
            }

            // Process results similar to handleSpinResult
            const bets = response.bets || [];
            let totalWinnings = 0;
            let totalLosses = 0;
            let totalWagered = 0;

            // Merge server bet results with local user bets
            const userBetsWithResults = userBets.map(localBet => {
                const serverBet = bets.find(b =>
                    b.bet_id === localBet.betId ||
                    (b.bet_type?.toUpperCase() === localBet.type?.toUpperCase() &&
                     b.bet_value?.toLowerCase() === localBet.value?.toLowerCase())
                );

                if (serverBet) {
                    // Track total wagered
                    totalWagered += serverBet.amount;

                    // If winner, add to winnings; if loser, add to losses
                    if (serverBet.is_winner && serverBet.payout > 0) {
                        // totalWinnings = what you got back (includes original bet)
                        totalWinnings += serverBet.payout;
                        console.log(`✅ WIN: Bet ${serverBet.bet_type} ${serverBet.bet_value} - Amount: ${serverBet.amount}, Payout: ${serverBet.payout}`);
                    } else {
                        // Lost bet - track the amount lost
                        totalLosses += serverBet.amount;
                        console.log(`❌ LOSS: Bet ${serverBet.bet_type} ${serverBet.bet_value} - Amount: ${serverBet.amount}`);
                    }

                    return {
                        ...localBet,
                        is_winner: serverBet.is_winner,
                        payout: serverBet.payout
                    };
                }

                // Bet not found in server response, assume loss
                totalWagered += localBet.amount;
                totalLosses += localBet.amount;
                return {
                    ...localBet,
                    is_winner: false,
                    payout: 0
                };
            });

            console.log('📊 Round results processed:', {
                totalWinnings,
                totalLosses,
                totalWagered,
                netResult: totalWinnings - totalWagered,
                betsWithResults: userBetsWithResults.length
            });

            // Show the modal
            // totalWinnings = total payouts received (includes original bets)
            // totalWagered = total amount bet
            // totalLosses = amount lost on losing bets (redundant, kept for compatibility)
            // Net result = what you got back - what you wagered
            await this.showResultSummary(totalWinnings, totalLosses, outcome, totalWagered, userBetsWithResults);

        } catch (error) {
            console.error('❌ Error fetching round results:', error);
            // Show modal anyway with basic info
            const userWagered = userBets.reduce((sum, bet) => sum + bet.amount, 0);
            await this.showResultSummary(0, userWagered, outcome, userWagered, userBets);
        }
    }

    // Show detailed result summary with OK button
    async showResultSummary(winnings, losses, outcome, userWagered = 0, userBetsSnapshot = []) {
        console.log('🎯 showResultSummary called', {
            winnings,
            losses,
            outcome,
            userWagered,
            userBetsSnapshot_length: userBetsSnapshot.length,
            currentBets_length: this.currentBets.length
        });

        try {
            // Calculate NET result (what you got back - what you wagered)
            // winnings = total payouts (includes original bets)
            // userWagered = total amount bet
            const netResult = winnings - userWagered;
            const isWin = netResult > 0;

            // FIX: Use passed snapshot instead of reading from currentBets (which may be cleared)
            const userBets = userBetsSnapshot.length > 0 ? userBetsSnapshot : this.currentBets.filter(bet => !bet.isBot && !bet.is_bot);
            const actualWagered = userWagered > 0 ? userWagered : userBets.reduce((sum, bet) => sum + bet.amount, 0);
            const potentialWin = userBets.reduce((sum, bet) => sum + (bet.amount * this.getPayoutMultiplier(bet.type, bet.value)), 0);

            console.log('📊 Modal data prepared:', { isWin, netResult, winnings, losses, userBets_count: userBets.length, actualWagered, potentialWin });

            // Create detailed result modal
            const resultModal = document.createElement('div');
            resultModal.className = 'result-summary-modal';
        resultModal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-content">
                <div class="result-header">
                    <h2 class="result-title">${isWin ? '🎉 YOU WON!' : '💔 BETTER LUCK NEXT TIME'}</h2>
                    <div class="result-crypto-info">
                        <div class="winning-number">Number: <span class="number">${outcome.number}</span></div>
                        <div class="crypto-name">${outcome.crypto || 'Unknown'}</div>
                    </div>
                </div>

                <div class="result-breakdown">
                    <div class="user-summary-stats">
                        <div class="stat-box">
                            <div class="stat-label">You Wagered:</div>
                            <div class="stat-value">${this.formatAmount(actualWagered)} GEM</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Potential Win:</div>
                            <div class="stat-value">${this.formatAmount(potentialWin)} GEM</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Net Result:</div>
                            <div class="stat-value ${isWin ? 'win-amount' : 'loss-amount'}">${netResult >= 0 ? '+' : ''}${this.formatAmount(netResult)} GEM</div>
                        </div>
                    </div>

                    <div class="breakdown-section">
                        <h3>Your Bets</h3>
                        <div class="bet-breakdown" id="result-bet-breakdown">
                            <!-- Will be populated by JavaScript -->
                        </div>
                    </div>

                    <div class="pot-contribution">
                        <div class="pot-label">Total Pot This Round</div>
                        <div class="pot-amount" id="round-pot-amount">$0</div>
                        <div class="contribution-breakdown">
                            <div class="contribution-item">
                                <span class="label">Your Contribution:</span>
                                <span class="amount">${this.formatAmount(actualWagered)} GEM</span>
                            </div>
                            <div class="contribution-item">
                                <span class="label">Bot Contributions:</span>
                                <span class="amount" id="bot-contributions">$0</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="result-actions">
                    <button class="continue-btn" id="result-continue-btn">
                        ${isWin ? '🎰 PLAY AGAIN 🎰' : '🔄 TRY AGAIN 🔄'}
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(resultModal);

        // Populate bet breakdown with actual user bets and outcome
        this.populateResultBetBreakdown(resultModal, userBets, outcome);

        // Calculate and show total pot (all bets from users and bots)
        this.calculateRoundPot(resultModal);

        // Style the modal based on win/loss
        if (isWin) {
            resultModal.classList.add('win-result');
            // Trigger confetti celebration for wins
            this.triggerConfetti();
            // Play win sound
            this.playWinSound();
        } else {
            resultModal.classList.add('loss-result');
            // Play loss sound
            this.playLossSound();
        }

        // Add result summary styles
        this.addResultSummaryStyles();

        return new Promise((resolve) => {
            const continueBtn = resultModal.querySelector('#result-continue-btn');
            const overlay = resultModal.querySelector('.modal-overlay');

            let autoClosed = false;

            const closeModal = (manual = false) => {
                if (autoClosed && manual) return; // Prevent double-clicking after auto-close

                resultModal.classList.add('fade-out');
                setTimeout(() => {
                    if (resultModal.parentNode) {
                        resultModal.parentNode.removeChild(resultModal);
                    }
                    resolve();
                }, 300);
            };

            continueBtn.addEventListener('click', () => closeModal(true));
            overlay.addEventListener('click', () => closeModal(true));

            // Auto-continue after 10 seconds for better user experience
            const autoContinueTimeout = setTimeout(() => {
                autoClosed = true;
                closeModal();

                // Show a brief notification that the game continues automatically
                this.showNotification('Continuing to next round...', 'info');
            }, 10000);

            // Add countdown indicator to the continue button
            let countdownSeconds = 10;
            continueBtn.textContent = `${continueBtn.textContent} (${countdownSeconds}s)`;

            const countdownInterval = setInterval(() => {
                countdownSeconds--;
                if (countdownSeconds > 0 && !autoClosed) {
                    continueBtn.textContent = `${isWin ? '🎰 PLAY AGAIN 🎰' : '🔄 TRY AGAIN 🔄'} (${countdownSeconds}s)`;
                } else {
                    clearInterval(countdownInterval);
                    if (countdownSeconds <= 0 && !autoClosed) {
                        continueBtn.textContent = isWin ? '🎰 PLAY AGAIN 🎰' : '🔄 TRY AGAIN 🔄';
                    }
                }
            }, 1000);

            // Clear intervals if modal closed manually
            const originalResolve = resolve;
            resolve = (...args) => {
                clearTimeout(autoContinueTimeout);
                clearInterval(countdownInterval);
                return originalResolve.apply(this, args);
            };
        });

        } catch (error) {
            console.error('❌ CRITICAL: showResultSummary failed:', error);
            console.error('Stack trace:', error.stack);
            // Show a simple alert as fallback
            const resultMsg = winnings > 0 ? `WON ${winnings} GEM` : `LOST ${losses} GEM`;
            alert(`🎰 Spin Result: ${resultMsg} on number ${outcome?.number || '?'}`);
            throw error; // Re-throw so caller knows it failed
        }
    }

    // Populate the bet breakdown in result modal
    populateResultBetBreakdown(modal, userBets, outcome) {
        const breakdownContainer = modal.querySelector('#result-bet-breakdown');

        // Safety check
        if (!userBets || userBets.length === 0) {
            breakdownContainer.innerHTML = '<p style="text-align: center; color: #9ca3af; padding: 1rem;">No bets placed this round</p>';
            return;
        }

        console.log('📊 Populating bet breakdown:', { userBets, outcome });

        // Group bets by type and calculate results
        const betGroups = {};
        userBets.forEach(bet => {
            if (!betGroups[bet.type]) {
                betGroups[bet.type] = [];
            }
            betGroups[bet.type].push(bet);
        });

        let breakdownHTML = '';
        Object.keys(betGroups).forEach(type => {
            const bets = betGroups[type];
            const totalAmount = bets.reduce((sum, bet) => sum + bet.amount, 0);

            // Use actual bet results from server data
            const isWinner = bets.some(bet => bet.is_winner || false);
            const payout = bets.reduce((sum, bet) => sum + (bet.payout || 0), 0);

            breakdownHTML += `
                <div class="bet-result-item ${isWinner ? 'winner' : 'loser'}">
                    <div class="bet-info">
                        <span class="bet-type">${this.formatBetLabel({type: type, value: bets[0].value})}</span>
                        <span class="bet-amount">${this.formatAmount(totalAmount)} GEM</span>
                    </div>
                    <div class="bet-outcome">
                        ${isWinner ?
                            `<span class="win-amount">+${this.formatAmount(payout)} GEM</span>` :
                            `<span class="loss-amount">-${this.formatAmount(totalAmount)} GEM</span>`
                        }
                    </div>
                </div>
            `;
        });

        breakdownContainer.innerHTML = breakdownHTML;
    }

    // Calculate and display round pot
    calculateRoundPot(modal) {
        // Simulate bot contributions (in real implementation this would be tracked)
        const yourContribution = this.currentBets.reduce((sum, bet) => sum + bet.amount, 0);

        // Simulate bot contributions based on active bots
        const botContribution = this.roundBots ?
            this.roundBots.reduce((sum, bot) => sum + (bot.bet ? bot.bet.amount : 0), 0) :
            0;

        const totalPot = yourContribution + botContribution;

        modal.querySelector('#round-pot-amount').textContent = `$${this.formatAmount(totalPot)}`;
        modal.querySelector('#bot-contributions').textContent = `${this.formatAmount(botContribution)} GEM`;
    }

    // Add styles for result summary modal
    addResultSummaryStyles() {
        if (document.querySelector('#result-summary-styles')) return;

        const style = document.createElement('style');
        style.id = 'result-summary-styles';
        style.textContent = `
            .result-summary-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            }

            .result-summary-modal.fade-out {
                animation: modalFadeOut 0.3s ease-out forwards;
            }

            @keyframes modalFadeOut {
                from { opacity: 1; }
                to { opacity: 0; transform: scale(0.95); }
            }

            .result-summary-modal .modal-overlay {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                backdrop-filter: blur(5px);
            }

            .result-summary-modal .modal-content {
                background: linear-gradient(135deg, #1e293b, #334155);
                border: 3px solid;
                border-radius: 20px;
                max-width: 500px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
                position: relative;
                z-index: 1;
                animation: resultModalEnter 0.5s ease-out;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
            }

            @keyframes resultModalEnter {
                from {
                    opacity: 0;
                    transform: scale(0.8) translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: scale(1) translateY(0);
                }
            }

            .result-summary-modal.win-result .modal-content {
                border-color: #10b981;
                box-shadow: 0 20px 40px rgba(16, 185, 129, 0.3);
                animation: winBorderGlow 2s ease-in-out infinite;
            }

            .result-summary-modal.loss-result .modal-content {
                border-color: #ef4444;
                box-shadow: 0 20px 40px rgba(239, 68, 68, 0.3);
            }

            @keyframes winBorderGlow {
                0%, 100% {
                    border-color: #10b981;
                    box-shadow: 0 20px 40px rgba(16, 185, 129, 0.3),
                                0 0 20px rgba(16, 185, 129, 0.5) inset;
                }
                50% {
                    border-color: #34d399;
                    box-shadow: 0 20px 60px rgba(16, 185, 129, 0.6),
                                0 0 40px rgba(16, 185, 129, 0.8) inset,
                                0 0 60px rgba(16, 185, 129, 0.4);
                }
            }

            .result-header {
                text-align: center;
                padding: 2rem 2rem 1rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }

            .result-title {
                font-size: 2.5rem;
                font-weight: 900;
                margin: 0 0 1rem;
                text-transform: uppercase;
                letter-spacing: 2px;
                animation: titlePulse 1.5s ease-in-out infinite;
            }

            .win-result .result-title {
                color: #10b981;
                text-shadow: 0 0 20px rgba(16, 185, 129, 0.8), 0 0 40px rgba(16, 185, 129, 0.5);
            }
            .loss-result .result-title {
                color: #ef4444;
                animation: none;
            }

            @keyframes titlePulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.1); }
            }

            .result-crypto-info {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 1rem;
            }

            .winning-number {
                font-size: 1.1rem;
                color: #fbbf24;
                font-weight: 600;
            }

            .number {
                font-size: 1.3rem;
                font-weight: 900;
                color: #ffffff;
            }

            .crypto-name {
                font-size: 1rem;
                color: #9ca3af;
                font-weight: 500;
            }

            .result-breakdown {
                padding: 1.5rem 2rem;
            }

            .user-summary-stats {
                display: flex;
                justify-content: space-between;
                gap: 1rem;
                margin-bottom: 2rem;
                padding: 1.5rem;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 12px;
            }

            .stat-box {
                text-align: center;
                flex: 1;
            }

            .stat-label {
                font-size: 0.9rem;
                color: #9ca3af;
                margin-bottom: 0.5rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            .stat-value {
                font-size: 1.4rem;
                font-weight: 700;
                color: #fbbf24;
            }

            .stat-value.win-amount {
                color: #10b981;
                font-size: 2.5rem;
                animation: winAmountPulse 1s ease-in-out infinite;
                text-shadow: 0 0 15px rgba(16, 185, 129, 0.8);
            }

            .stat-value.loss-amount {
                color: #ef4444;
                font-size: 1.8rem;
            }

            @keyframes winAmountPulse {
                0%, 100% {
                    transform: scale(1);
                    text-shadow: 0 0 15px rgba(16, 185, 129, 0.8);
                }
                50% {
                    transform: scale(1.15);
                    text-shadow: 0 0 25px rgba(16, 185, 129, 1), 0 0 40px rgba(16, 185, 129, 0.6);
                }
            }

            .breakdown-section h3 {
                color: #fbbf24;
                margin-bottom: 1rem;
                font-size: 1.2rem;
                text-align: center;
            }

            .bet-result-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem;
                margin-bottom: 0.5rem;
                border-radius: 8px;
                background: rgba(0, 0, 0, 0.3);
            }

            .bet-result-item.winner {
                border-left: 4px solid #10b981;
                background: rgba(16, 185, 129, 0.1);
            }

            .bet-result-item.loser {
                border-left: 4px solid #ef4444;
                background: rgba(239, 68, 68, 0.1);
            }

            .bet-info {
                display: flex;
                flex-direction: column;
                gap: 0.25rem;
            }

            .bet-type {
                font-weight: 600;
                color: #ffffff;
                font-size: 0.9rem;
            }

            .bet-amount {
                color: #9ca3af;
                font-size: 0.8rem;
            }

            .bet-outcome {
                text-align: right;
            }

            .win-amount {
                color: #10b981;
                font-weight: 700;
                font-size: 1.1rem;
            }

            .loss-amount {
                color: #ef4444;
                font-weight: 700;
                font-size: 1.1rem;
            }

            .pot-contribution {
                margin-top: 2rem;
                text-align: center;
                padding: 1rem;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 12px;
            }

            .pot-label {
                font-size: 0.9rem;
                color: #9ca3af;
                margin-bottom: 0.5rem;
            }

            .pot-amount {
                font-size: 1.8rem;
                font-weight: 900;
                color: #fbbf24;
                margin-bottom: 0.5rem;
            }

            .contribution-breakdown {
                display: flex;
                justify-content: space-between;
                gap: 1rem;
            }

            .contribution-item {
                display: flex;
                flex-direction: column;
                align-items: center;
                flex: 1;
            }

            .contribution-item .label {
                font-size: 0.75rem;
                color: #9ca3af;
                margin-bottom: 0.25rem;
            }

            .contribution-item .amount {
                font-size: 0.9rem;
                font-weight: 600;
                color: #fbbf24;
            }

            .result-actions {
                padding: 1rem 2rem 2rem;
                text-align: center;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
            }

            .continue-btn {
                background: linear-gradient(45deg, #10b981, #059669);
                border: none;
                padding: 1rem 3rem;
                border-radius: 12px;
                color: white;
                font-weight: 700;
                font-size: 1.1rem;
                cursor: pointer;
                transition: all 0.3s ease;
                text-transform: uppercase;
                letter-spacing: 1px;
            }

            .loss-result .continue-btn {
                background: linear-gradient(45deg, #ef4444, #dc2626);
            }

            .continue-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
            }

            @media (max-width: 768px) {
                .result-summary-modal .modal-content {
                    max-width: 95%;
                    margin: 1rem;
                }

                .result-title {
                    font-size: 1.5rem;
                }

                .contribution-breakdown {
                    flex-direction: column;
                    gap: 0.5rem;
                }

                .pot-amount {
                    font-size: 1.5rem;
                }
            }
        `;
        document.head.appendChild(style);
    }

    // UNIFIED WHEEL ANIMATION - PREVENTS CHAOS
    startUnifiedWheelAnimation() {
        console.log('🎰 Starting unified wheel animation...');

        // Don't animate yet - just add visual "waiting" indicator
        const wheelContainer = document.querySelector('.wheel-container');
        if (wheelContainer) {
            wheelContainer.classList.add('spinning');
            wheelContainer.style.boxShadow = '0 0 30px rgba(0, 245, 255, 0.6)';
        }

        // Update game phase display
        this.updateGamePhase('🎰 Wheel Spinning...');

        // Return a Promise that resolves immediately
        // The actual wheel animation will happen in handleSpinResult() when we know the winning number
        return Promise.resolve();
    }

    // Utility delay function
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Update game phase display
    updateGamePhase(phase) {
        const phaseElement = document.getElementById('game-phase');
        if (phaseElement) {
            const phaseText = phaseElement.querySelector('.phase-text');
            if (phaseText) {
                phaseText.textContent = phase;
            }
        }
    }

    // Disable betting controls during spin
    disableBetting() {
        // Disable bet buttons
        const betButtons = document.querySelectorAll('.bet-btn');
        betButtons.forEach(btn => {
            btn.disabled = true;
            btn.classList.add('disabled');
        });

        // Disable chip buttons
        const chipButtons = document.querySelectorAll('.chip-btn');
        chipButtons.forEach(btn => {
            btn.disabled = true;
            btn.classList.add('disabled');
        });

        // Disable spin button initially
        if (this.elements.spinButton) {
            this.elements.spinButton.disabled = true;
        }
    }

    // Re-enable betting controls
    reEnableBetting() {
        // Re-enable bet buttons
        const betButtons = document.querySelectorAll('.bet-btn');
        betButtons.forEach(btn => {
            btn.disabled = false;
            btn.classList.remove('disabled');
        });

        // Re-enable chip buttons
        const chipButtons = document.querySelectorAll('.chip-btn');
        chipButtons.forEach(btn => {
            btn.disabled = false;
            btn.classList.remove('disabled');
        });

        // Update spin button
        this.updateSpinButtonState();
    }

    // FORCE re-enable ALL controls (ultimate failsafe)
    statusForceReEnable() {
        console.log('🚨 FORCE RE-ENABLING ALL CONTROLS (ultimate failsafe)');

        // FIX: Force reset all state flags (use only roundPhase)
        this.roundPhase = RouletteGame.ROUND_PHASES.BETTING;
        this.spinInProgress = false;
        this.spinLockActive = false;
        this.isProcessing = false;

        // Force re-enable all controls
        this.reEnableBetting();
        this.updateSpinButtonState();

        // Clear any ongoing timers
        if (this.roundTimer) {
            clearInterval(this.roundTimer);
            this.roundTimer = null;
        }

        // Restart normal countdown if we're not in a spin
        if (this.currentBets.length > 0) {
            this.startNewRound();
        }

        this.updateGamePhase('Ready to Play');
        this.stopWheelAnimations();

        console.log('✅ All controls force-re-enabled successfully');
    }

    // ===== FUNNY USERNAME & AVATAR SYSTEM =====

    // Generate a funny random username
    generateFunnyUsername() {
        // Safety check to prevent undefined array errors
        if (!this.namePrefixes || !Array.isArray(this.namePrefixes) ||
            !this.nameSuffixes || !Array.isArray(this.nameSuffixes) ||
            !this.nameWords || !Array.isArray(this.nameWords)) {
            return 'BobRoss'; // Fallback
        }

        const nameMethods = Math.floor(Math.random() * 4);

        switch (nameMethods) {
            case 0: // Prefix + Suffix (JoeBob, BreadCheese)
                const prefix = this.namePrefixes[Math.floor(Math.random() * this.namePrefixes.length)];
                const suffix = this.nameSuffixes[Math.floor(Math.random() * this.nameSuffixes.length)];
                return prefix + suffix;

            case 1: // Name + Number (Bob42, Sally7)
                const combinedNames = [...this.namePrefixes, ...this.nameSuffixes];
                const singleName = combinedNames[Math.floor(Math.random() * combinedNames.length)];
                const number = Math.floor(Math.random() * 999) + 1;
                return singleName + number;

            case 2: // Word combinations (DogBread, CheeseCat, TreeRock)
                const word1 = this.nameWords[Math.floor(Math.random() * this.nameWords.length)];
                const word2 = this.nameWords[Math.floor(Math.random() * this.nameWords.length)];
                return word1 + word2;

            case 3: // Mixed combinations (BobBread, CheeseSteve, Dog42)
                const combinedNamesAgain = [...this.namePrefixes, ...this.nameSuffixes];
                const namePart = combinedNamesAgain[Math.floor(Math.random() * combinedNamesAgain.length)];
                const wordPart = this.nameWords[Math.floor(Math.random() * this.nameWords.length)];
                return Math.random() > 0.5 ? namePart + wordPart : wordPart + namePart;

            default:
                return 'BobRoss'; // Fallback
        }
    }

    // Get random avatar emoji
    getRandomAvatar() {
        if (!this.playerAvatars || !Array.isArray(this.playerAvatars)) {
            return '🤖'; // Fallback
        }
        return this.playerAvatars[Math.floor(Math.random() * this.playerAvatars.length)];
    }

    // Update bet feed display (enhanced with avatars)
    updateBetFeedDisplay() {
        // DISABLED: Live Bets popup removed per user request
        return;

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

    // Play win sound effect
    playWinSound() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            // Victory fanfare sequence
            const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
            let time = audioContext.currentTime;

            notes.forEach((freq, i) => {
                oscillator.frequency.setValueAtTime(freq, time + i * 0.15);
            });

            oscillator.type = 'sine';
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.8);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.8);
        } catch (e) {
            console.log('Sound not available:', e);
        }
    }

    // Play loss sound effect
    playLossSound() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            // Descending sad sound
            oscillator.frequency.setValueAtTime(400, audioContext.currentTime);
            oscillator.frequency.exponentialRampToValueAtTime(200, audioContext.currentTime + 0.5);

            oscillator.type = 'sine';
            gainNode.gain.setValueAtTime(0.2, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
        } catch (e) {
            console.log('Sound not available:', e);
        }
    }

    // Trigger confetti celebration effect
    triggerConfetti() {
        const colors = ['#FFD700', '#FFA500', '#FF6347', '#00FF00', '#1E90FF', '#FF69B4'];
        const confettiCount = 100;

        for (let i = 0; i < confettiCount; i++) {
            setTimeout(() => {
                const confetti = document.createElement('div');
                confetti.className = 'confetti-piece';
                confetti.style.cssText = `
                    position: fixed;
                    width: ${Math.random() * 10 + 5}px;
                    height: ${Math.random() * 10 + 5}px;
                    background-color: ${colors[Math.floor(Math.random() * colors.length)]};
                    left: ${Math.random() * 100}vw;
                    top: -20px;
                    z-index: 100000;
                    border-radius: ${Math.random() > 0.5 ? '50%' : '0'};
                    opacity: ${Math.random() * 0.5 + 0.5};
                    transform: rotate(${Math.random() * 360}deg);
                    animation: confetti-fall ${Math.random() * 3 + 2}s linear forwards;
                    pointer-events: none;
                `;
                document.body.appendChild(confetti);

                setTimeout(() => confetti.remove(), 5000);
            }, i * 30);
        }

        // Add confetti animation if not already present
        if (!document.getElementById('confetti-animation-style')) {
            const style = document.createElement('style');
            style.id = 'confetti-animation-style';
            style.textContent = `
                @keyframes confetti-fall {
                    0% {
                        transform: translateY(0) rotate(0deg);
                        opacity: 1;
                    }
                    100% {
                        transform: translateY(100vh) rotate(720deg);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    try {
        new RouletteGame();
    } catch (error) {
        console.error('Failed to initialize roulette game', error);
    }
});
