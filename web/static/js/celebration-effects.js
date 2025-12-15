/**
 * Celebration Effects System
 * CryptoChecker V3 - Crypto Roulette
 * Phase 4: Animation & Polish
 *
 * Provides casino-quality celebration effects for wins:
 * - Confetti bursts
 * - Screen flashes
 * - Floating GEM animations
 * - Sound effect triggers (placeholder)
 */

class CelebrationEffects {
    constructor() {
        this.confettiColors = ['#fbbf24', '#06b6d4', '#8b5cf6', '#22c55e', '#ef4444'];
        this.isPlaying = false;
    }

    /**
     * Trigger win celebration based on win amount
     * @param {number} netWin - Net amount won (positive number)
     * @param {number} totalWagered - Total amount wagered
     */
    celebrate(netWin, totalWagered) {
        if (netWin <= 0) return;

        const multiplier = netWin / totalWagered;

        if (multiplier >= 10) {
            // BIG WIN (10x or more)
            this.bigWinCelebration(netWin);
        } else if (multiplier >= 5) {
            // GREAT WIN (5x-10x)
            this.greatWinCelebration(netWin);
        } else if (multiplier >= 2) {
            // GOOD WIN (2x-5x)
            this.goodWinCelebration(netWin);
        } else {
            // SMALL WIN (less than 2x)
            this.smallWinCelebration(netWin);
        }
    }

    /**
     * Small win celebration (< 2x)
     */
    smallWinCelebration(amount) {
        console.log('🎊 Small win celebration:', amount);
        this.flashScreen('win');
        this.floatingGems(amount, 1);
    }

    /**
     * Good win celebration (2x-5x)
     */
    goodWinCelebration(amount) {
        console.log('🎉 Good win celebration:', amount);
        this.flashScreen('win');
        this.confettiBurst(20);
        this.floatingGems(amount, 3);
    }

    /**
     * Great win celebration (5x-10x)
     */
    greatWinCelebration(amount) {
        console.log('🎊🎊 Great win celebration:', amount);
        this.flashScreen('big-win');
        this.confettiBurst(40);
        this.floatingGems(amount, 5);
        this.screenShake();
    }

    /**
     * Big win celebration (10x+)
     */
    bigWinCelebration(amount) {
        console.log('💎💎💎 BIG WIN celebration:', amount);
        this.flashScreen('big-win');
        this.confettiBurst(80);
        this.floatingGems(amount, 8);
        this.screenShake();

        // Extended confetti for big wins
        setTimeout(() => this.confettiBurst(40), 500);
        setTimeout(() => this.confettiBurst(40), 1000);
    }

    /**
     * Flash the screen with celebration colors
     * @param {string} type - 'win' or 'big-win'
     */
    flashScreen(type = 'win') {
        const flash = document.createElement('div');
        flash.className = `rd-celebration-overlay rd-${type}`;
        document.body.appendChild(flash);

        setTimeout(() => {
            if (flash.parentNode) {
                flash.parentNode.removeChild(flash);
            }
        }, type === 'big-win' ? 800 : 500);
    }

    /**
     * Create confetti burst effect
     * @param {number} count - Number of confetti pieces
     */
    confettiBurst(count = 30) {
        const centerX = window.innerWidth / 2;
        const centerY = window.innerHeight / 2;

        for (let i = 0; i < count; i++) {
            setTimeout(() => {
                this.createConfetti(centerX, centerY);
            }, i * 30); // Stagger creation
        }
    }

    /**
     * Create a single confetti piece
     * @param {number} x - Starting X position
     * @param {number} y - Starting Y position
     */
    createConfetti(x, y) {
        const confetti = document.createElement('div');
        confetti.className = 'rd-confetti';

        // Random color
        const color = this.confettiColors[Math.floor(Math.random() * this.confettiColors.length)];
        confetti.style.background = color;

        // Random starting position (spread from center)
        const spreadX = (Math.random() - 0.5) * 200;
        const spreadY = (Math.random() - 0.5) * 100;
        confetti.style.left = (x + spreadX) + 'px';
        confetti.style.top = (y + spreadY) + 'px';

        // Random size
        const size = Math.random() * 6 + 4;
        confetti.style.width = size + 'px';
        confetti.style.height = size + 'px';

        // Random animation delay and duration
        const delay = Math.random() * 0.3;
        const duration = Math.random() * 1 + 1.5;
        confetti.style.animationDelay = delay + 's';
        confetti.style.animationDuration = duration + 's';

        // Random trajectory
        const angle = Math.random() * 360;
        const distance = Math.random() * 200 + 100;
        const tx = Math.cos(angle * Math.PI / 180) * distance;
        const ty = -Math.abs(Math.sin(angle * Math.PI / 180) * distance) - 200;

        confetti.style.setProperty('--tx', tx + 'px');
        confetti.style.setProperty('--ty', ty + 'px');

        document.body.appendChild(confetti);

        // Remove after animation
        setTimeout(() => {
            if (confetti.parentNode) {
                confetti.parentNode.removeChild(confetti);
            }
        }, (delay + duration) * 1000);
    }

    /**
     * Create floating GEM amount indicators
     * @param {number} amount - Amount won
     * @param {number} count - Number of floating indicators
     */
    floatingGems(amount, count = 1) {
        for (let i = 0; i < count; i++) {
            setTimeout(() => {
                this.createFloatingGem(amount);
            }, i * 200);
        }
    }

    /**
     * Create a single floating GEM indicator
     * @param {number} amount - Amount to display
     */
    createFloatingGem(amount) {
        const gem = document.createElement('div');
        gem.className = 'rd-floating-gem';
        gem.textContent = '+' + this.formatGems(amount);

        // Random starting position (lower third of screen)
        const x = Math.random() * (window.innerWidth - 200) + 100;
        const y = window.innerHeight * 0.6 + Math.random() * (window.innerHeight * 0.2);
        gem.style.left = x + 'px';
        gem.style.top = y + 'px';

        // Random animation duration
        const duration = Math.random() * 0.5 + 1.5;
        gem.style.animationDuration = duration + 's';

        document.body.appendChild(gem);

        // Remove after animation
        setTimeout(() => {
            if (gem.parentNode) {
                gem.parentNode.removeChild(gem);
            }
        }, duration * 1000);
    }

    /**
     * Subtle screen shake effect
     */
    screenShake() {
        const body = document.body;
        const originalTransform = body.style.transform;

        let frame = 0;
        const maxFrames = 10;
        const shakeIntensity = 5;

        const shake = setInterval(() => {
            if (frame >= maxFrames) {
                clearInterval(shake);
                body.style.transform = originalTransform;
                return;
            }

            const x = (Math.random() - 0.5) * shakeIntensity;
            const y = (Math.random() - 0.5) * shakeIntensity;
            body.style.transform = `translate(${x}px, ${y}px)`;

            frame++;
        }, 50);
    }

    /**
     * Format number with thousands separator
     * @param {number} num - Number to format
     * @returns {string} Formatted number
     */
    formatGems(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toLocaleString();
    }

    /**
     * Trigger balance update animation
     * @param {HTMLElement} element - Balance display element
     * @param {boolean} isIncrease - Whether balance increased or decreased
     */
    animateBalanceChange(element, isIncrease) {
        if (!element) return;

        // Remove existing animation classes
        element.classList.remove('rd-balance-increase', 'rd-balance-decrease');

        // Force reflow to restart animation
        void element.offsetWidth;

        // Add appropriate animation class
        if (isIncrease) {
            element.classList.add('rd-balance-increase');
        } else {
            element.classList.add('rd-balance-decrease');
        }

        // Remove class after animation
        setTimeout(() => {
            element.classList.remove('rd-balance-increase', 'rd-balance-decrease');
        }, 600);
    }

    /**
     * Play sound effect (placeholder - requires sound files)
     * @param {string} soundName - Name of sound to play
     */
    playSound(soundName) {
        console.log('🔊 Sound effect:', soundName);
        // TODO: Implement actual sound playback
        // Example: new Audio(`/static/sounds/${soundName}.mp3`).play();
    }

    /**
     * Test celebration effects (for debugging)
     */
    test() {
        console.log('🧪 Testing celebration effects...');

        // Test small win
        setTimeout(() => {
            console.log('Testing small win...');
            this.celebrate(5000, 10000);
        }, 1000);

        // Test good win
        setTimeout(() => {
            console.log('Testing good win...');
            this.celebrate(30000, 10000);
        }, 4000);

        // Test great win
        setTimeout(() => {
            console.log('Testing great win...');
            this.celebrate(80000, 10000);
        }, 7000);

        // Test big win
        setTimeout(() => {
            console.log('Testing BIG WIN...');
            this.celebrate(150000, 10000);
        }, 10000);
    }
}

// Create global instance
window.CelebrationEffects = new CelebrationEffects();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CelebrationEffects;
}

// Console helper for testing
console.log('🎊 Celebration Effects loaded. Test with: window.CelebrationEffects.test()');
