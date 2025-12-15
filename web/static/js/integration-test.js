/**
 * Integration Test Suite
 * CryptoChecker V3 - Premium Roulette UI
 *
 * Run this in browser console to verify all Phase 3-4 features are loaded correctly.
 * Usage: Copy and paste into browser console, or run: IntegrationTest.runAll()
 */

const IntegrationTest = {
    results: [],

    /**
     * Run all integration tests
     */
    async runAll() {
        console.log('🧪 Starting Integration Tests...\n');
        this.results = [];

        // System checks
        this.testGlobalObjects();
        this.testCSSFiles();
        this.testDOMElements();

        // Feature tests
        this.testResultsDisplay();
        this.testCelebrationEffects();

        // Report results
        this.reportResults();

        return this.results;
    },

    /**
     * Test that global objects exist
     */
    testGlobalObjects() {
        console.log('📦 Testing Global Objects...');

        this.test('window.ResultsDisplay exists',
            typeof window.ResultsDisplay !== 'undefined');

        this.test('window.CelebrationEffects exists',
            typeof window.CelebrationEffects !== 'undefined');

        this.test('ResultsDisplay has show method',
            typeof window.ResultsDisplay?.show === 'function');

        this.test('ResultsDisplay has hide method',
            typeof window.ResultsDisplay?.hide === 'function');

        this.test('CelebrationEffects has celebrate method',
            typeof window.CelebrationEffects?.celebrate === 'function');

        this.test('CelebrationEffects has confettiBurst method',
            typeof window.CelebrationEffects?.confettiBurst === 'function');
    },

    /**
     * Test that CSS files are loaded
     */
    testCSSFiles() {
        console.log('\n🎨 Testing CSS Files...');

        const stylesheets = Array.from(document.styleSheets);

        const hasResultsDisplayCSS = stylesheets.some(sheet =>
            sheet.href && sheet.href.includes('results-display.css'));
        this.test('results-display.css loaded', hasResultsDisplayCSS);

        const hasPolishCSS = stylesheets.some(sheet =>
            sheet.href && sheet.href.includes('roulette-polish.css'));
        this.test('roulette-polish.css loaded', hasPolishCSS);

        const hasComponentsCSS = stylesheets.some(sheet =>
            sheet.href && sheet.href.includes('roulette-components.css'));
        this.test('roulette-components.css loaded', hasComponentsCSS);
    },

    /**
     * Test DOM elements
     */
    testDOMElements() {
        console.log('\n🏗️ Testing DOM Elements...');

        // Wheel elements
        const wheelContainer = document.querySelector('.rd-wheel-container');
        this.test('Wheel container exists', wheelContainer !== null);

        const wheelPointer = document.querySelector('.rd-wheel-pointer');
        this.test('Wheel pointer exists', wheelPointer !== null);

        const wheelNumbers = document.getElementById('wheelNumbers');
        this.test('Wheel numbers container exists', wheelNumbers !== null);

        // Status bar
        const statusBar = document.querySelector('.rd-status-bar');
        this.test('Status bar exists', statusBar !== null);

        // Balance display
        const balance = document.getElementById('available-balance');
        this.test('Balance display exists', balance !== null);
    },

    /**
     * Test Results Display functionality
     */
    testResultsDisplay() {
        console.log('\n🎊 Testing Results Display...');

        if (!window.ResultsDisplay) {
            this.test('Results Display - SKIPPED (not loaded)', false);
            return;
        }

        // Test overlay creation
        let overlay = document.getElementById('resultsOverlay');
        const overlayExistsOrCreatable = overlay !== null || typeof window.ResultsDisplay.createOverlay === 'function';
        this.test('Results overlay exists or can be created', overlayExistsOrCreatable);

        // Test show method doesn't crash
        try {
            // Quick show/hide test
            window.ResultsDisplay.show({
                number: 17,
                color: 'red',
                totalWagered: 1000,
                totalWon: 2000,
                netResult: 1000
            });

            const overlayActive = window.ResultsDisplay.isActive;
            this.test('Results display can show', overlayActive);

            // Hide immediately
            window.ResultsDisplay.hide();

            const overlayHidden = !window.ResultsDisplay.isActive;
            this.test('Results display can hide', overlayHidden);

        } catch (error) {
            this.test('Results display show/hide', false, error.message);
        }
    },

    /**
     * Test Celebration Effects functionality
     */
    testCelebrationEffects() {
        console.log('\n🎉 Testing Celebration Effects...');

        if (!window.CelebrationEffects) {
            this.test('Celebration Effects - SKIPPED (not loaded)', false);
            return;
        }

        // Test confetti method doesn't crash
        try {
            window.CelebrationEffects.confettiBurst(5);
            this.test('Confetti burst executes', true);

            // Clean up confetti
            setTimeout(() => {
                document.querySelectorAll('.rd-confetti').forEach(el => el.remove());
            }, 100);
        } catch (error) {
            this.test('Confetti burst executes', false, error.message);
        }

        // Test screen flash
        try {
            window.CelebrationEffects.flashScreen('win');
            this.test('Screen flash executes', true);

            // Clean up flash
            setTimeout(() => {
                document.querySelectorAll('.rd-celebration-overlay').forEach(el => el.remove());
            }, 600);
        } catch (error) {
            this.test('Screen flash executes', false, error.message);
        }

        // Test floating gems
        try {
            window.CelebrationEffects.floatingGems(1000, 1);
            this.test('Floating GEMs execute', true);

            // Clean up gems
            setTimeout(() => {
                document.querySelectorAll('.rd-floating-gem').forEach(el => el.remove());
            }, 100);
        } catch (error) {
            this.test('Floating GEMs execute', false, error.message);
        }

        // Test celebrate method
        try {
            window.CelebrationEffects.celebrate(2000, 1000); // 2x win
            this.test('Celebrate method executes', true);

            // Clean up
            setTimeout(() => {
                document.querySelectorAll('.rd-confetti, .rd-celebration-overlay, .rd-floating-gem')
                    .forEach(el => el.remove());
            }, 1000);
        } catch (error) {
            this.test('Celebrate method executes', false, error.message);
        }
    },

    /**
     * Record test result
     */
    test(name, passed, error = null) {
        const result = {
            name,
            passed,
            error
        };

        this.results.push(result);

        const icon = passed ? '✅' : '❌';
        const message = error ? ` (${error})` : '';
        console.log(`  ${icon} ${name}${message}`);
    },

    /**
     * Report all test results
     */
    reportResults() {
        console.log('\n' + '='.repeat(60));
        console.log('📊 INTEGRATION TEST RESULTS');
        console.log('='.repeat(60));

        const total = this.results.length;
        const passed = this.results.filter(r => r.passed).length;
        const failed = total - passed;
        const passRate = ((passed / total) * 100).toFixed(1);

        console.log(`\nTotal Tests: ${total}`);
        console.log(`✅ Passed: ${passed}`);
        console.log(`❌ Failed: ${failed}`);
        console.log(`📈 Pass Rate: ${passRate}%`);

        if (failed > 0) {
            console.log('\n❌ FAILED TESTS:');
            this.results.filter(r => !r.passed).forEach(r => {
                console.log(`  - ${r.name}${r.error ? ` (${r.error})` : ''}`);
            });
        }

        console.log('\n' + '='.repeat(60));

        if (failed === 0) {
            console.log('🎉 ALL TESTS PASSED! System is ready for use.');
        } else {
            console.log('⚠️ Some tests failed. Check the errors above.');
        }

        console.log('='.repeat(60) + '\n');
    },

    /**
     * Run visual demo of all features
     */
    async runDemo() {
        console.log('🎬 Starting Visual Demo...\n');

        // Demo 1: Results Display - RED Win
        console.log('Demo 1: Results Display - RED Number Win');
        await this.sleep(1000);
        if (window.ResultsDisplay) {
            window.ResultsDisplay.show({
                number: 17,
                color: 'red',
                totalWagered: 50000,
                totalWon: 175000,
                netResult: 125000
            });
            await this.waitForUserDismiss();
        }

        // Demo 2: Results Display - BLACK Loss
        console.log('Demo 2: Results Display - BLACK Number Loss');
        await this.sleep(500);
        if (window.ResultsDisplay) {
            window.ResultsDisplay.show({
                number: 4,
                color: 'black',
                totalWagered: 100000,
                totalWon: 0,
                netResult: -100000
            });
            await this.waitForUserDismiss();
        }

        // Demo 3: Results Display - GREEN Jackpot
        console.log('Demo 3: Results Display - GREEN (0) Jackpot');
        await this.sleep(500);
        if (window.ResultsDisplay) {
            window.ResultsDisplay.show({
                number: 0,
                color: 'green',
                totalWagered: 10000,
                totalWon: 360000,
                netResult: 350000
            });
            await this.waitForUserDismiss();
        }

        // Demo 4: Celebration Effects
        if (window.CelebrationEffects) {
            console.log('Demo 4: Celebration Effects - All Tiers');
            await this.sleep(500);
            window.CelebrationEffects.test();
        }

        console.log('\n🎬 Demo Complete!');
    },

    /**
     * Wait for user to dismiss overlay
     */
    async waitForUserDismiss() {
        return new Promise(resolve => {
            const checkInterval = setInterval(() => {
                if (!window.ResultsDisplay || !window.ResultsDisplay.isActive) {
                    clearInterval(checkInterval);
                    resolve();
                }
            }, 100);

            // Timeout after 30 seconds
            setTimeout(() => {
                clearInterval(checkInterval);
                if (window.ResultsDisplay) {
                    window.ResultsDisplay.hide();
                }
                resolve();
            }, 30000);
        });
    },

    /**
     * Sleep helper
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
};

// Auto-run on load if in test mode
if (window.location.search.includes('test=1')) {
    window.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => {
            IntegrationTest.runAll();
        }, 2000);
    });
}

// Make available globally
window.IntegrationTest = IntegrationTest;

console.log('🧪 Integration Test Suite Loaded');
console.log('Run tests with: IntegrationTest.runAll()');
console.log('Run visual demo with: IntegrationTest.runDemo()');
