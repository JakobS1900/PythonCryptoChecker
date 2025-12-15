/**
 * Premium Results Display System
 * CryptoChecker V3 - Crypto Roulette
 *
 * Provides casino-quality winning number announcements with:
 * - Dramatic full-screen overlay
 * - Animated number badge with color-specific glows
 * - Payout calculations and display
 * - Smooth entrance/exit animations
 */

class ResultsDisplay {
    constructor() {
        this.overlay = null;
        this.isActive = false;
        this.init();
    }

    init() {
        // Create overlay element if it doesn't exist
        if (!document.getElementById('resultsOverlay')) {
            this.createOverlay();
        } else {
            this.overlay = document.getElementById('resultsOverlay');
            this.attachEventListeners();
        }
    }

    createOverlay() {
        const overlayHTML = `
            <div class="rd-results-overlay" id="resultsOverlay">
                <div class="rd-winning-number-display">
                    <div class="rd-winning-label">WINNING NUMBER</div>
                    <div class="rd-premium-number-badge" id="winningNumberBadge">
                        <span id="winningNumber">0</span>
                    </div>
                    <div class="rd-color-name" id="winningColorName">RED</div>
                    <div class="rd-payout-info" id="payoutInfo">
                        <div class="rd-payout-row">
                            <span class="rd-payout-label">Total Wagered</span>
                            <span class="rd-payout-value" id="totalWagered">0 GEM</span>
                        </div>
                        <div class="rd-payout-row">
                            <span class="rd-payout-label">Result</span>
                            <span class="rd-payout-value" id="payoutResult">+0 GEM</span>
                        </div>
                        <div class="rd-payout-row">
                            <span class="rd-payout-label">Total Payout</span>
                            <span class="rd-payout-value" id="totalPayout">0 GEM</span>
                        </div>
                    </div>
                    <button class="rd-continue-btn" id="continueBtn">Continue</button>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', overlayHTML);
        this.overlay = document.getElementById('resultsOverlay');
        this.attachEventListeners();
    }

    attachEventListeners() {
        const continueBtn = document.getElementById('continueBtn');
        if (continueBtn) {
            continueBtn.addEventListener('click', () => this.hide());
        }

        // Click overlay backdrop to close
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.hide();
            }
        });

        // ESC key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isActive) {
                this.hide();
            }
        });
    }

    /**
     * Show results overlay with winning number and payout information
     * @param {Object} data - Results data
     * @param {number} data.number - Winning number (0-36)
     * @param {string} data.color - Winning color ('red', 'black', 'green')
     * @param {number} data.totalWagered - Total amount wagered by player
     * @param {number} data.totalWon - Total amount won by player
     * @param {number} data.netResult - Net result (won - wagered)
     */
    show(data) {
        if (this.isActive) return;

        const { number, color, totalWagered = 0, totalWon = 0, netResult = 0 } = data;

        // Update winning number
        const winningNumber = document.getElementById('winningNumber');
        const winningNumberBadge = document.getElementById('winningNumberBadge');
        const winningColorName = document.getElementById('winningColorName');

        if (winningNumber) winningNumber.textContent = number;

        // Set color classes
        if (winningNumberBadge) {
            winningNumberBadge.className = 'rd-premium-number-badge';
            winningNumberBadge.classList.add(`rd-${color}`);
        }

        if (winningColorName) {
            winningColorName.className = 'rd-color-name';
            winningColorName.classList.add(`rd-${color}`);
            winningColorName.textContent = color.toUpperCase();
        }

        // Update payout information
        const totalWageredEl = document.getElementById('totalWagered');
        const payoutResultEl = document.getElementById('payoutResult');
        const totalPayoutEl = document.getElementById('totalPayout');

        if (totalWageredEl) {
            totalWageredEl.textContent = this.formatGems(totalWagered);
        }

        if (payoutResultEl) {
            const isWin = netResult > 0;
            payoutResultEl.className = 'rd-payout-value';
            payoutResultEl.classList.add(isWin ? 'rd-win' : 'rd-loss');
            payoutResultEl.textContent = (netResult >= 0 ? '+' : '') + this.formatGems(netResult);
        }

        if (totalPayoutEl) {
            const isWin = netResult > 0;
            totalPayoutEl.className = 'rd-payout-value';
            totalPayoutEl.classList.add(isWin ? 'rd-win' : 'rd-loss');
            totalPayoutEl.textContent = this.formatGems(totalWon);
        }

        // Show overlay
        this.overlay.classList.add('rd-active');
        this.isActive = true;

        // Prevent body scroll
        document.body.style.overflow = 'hidden';

        console.log('🎊 [Results Display] Showing results:', data);
    }

    /**
     * Hide results overlay
     */
    hide() {
        if (!this.isActive) return;

        this.overlay.classList.remove('rd-active');
        this.isActive = false;

        // Restore body scroll
        document.body.style.overflow = '';

        console.log('🎊 [Results Display] Hidden');
    }

    /**
     * Format gems with thousands separator
     * @param {number} amount - Amount in gems
     * @returns {string} Formatted string
     */
    formatGems(amount) {
        return amount.toLocaleString() + ' GEM';
    }
}

// Create global instance
window.ResultsDisplay = new ResultsDisplay();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ResultsDisplay;
}
