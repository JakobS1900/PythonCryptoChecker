// Test achievements page authentication
const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext();
    const page = await context.newPage();

    // Enable console logging
    page.on('console', msg => {
        const text = msg.text();
        if (text.includes('[Achievements]') || text.includes('401') || text.includes('error')) {
            console.log(`[BROWSER] ${text}`);
        }
    });

    try {
        console.log('[TEST] Navigating to achievements page...');
        await page.goto('http://localhost:8000/achievements');
        await page.waitForLoadState('networkidle');

        // Check if login modal is visible
        const loginModalVisible = await page.locator('#authModal').isVisible();
        console.log(`[TEST] Login modal visible: ${loginModalVisible}`);

        if (loginModalVisible) {
            console.log('[TEST] Logging in as Emu...');
            await page.fill('#loginUsernameInput', 'Emu');
            await page.fill('#loginPasswordInput', 'EmuEmu');
            await page.click('button:has-text("Login")');
            await page.waitForTimeout(2000);
        }

        // Wait for achievements to load
        console.log('[TEST] Waiting for achievements...');
        await page.waitForTimeout(3000);

        // Check for error messages
        const errorVisible = await page.locator('.alert-danger').isVisible();
        console.log(`[TEST] Error message visible: ${errorVisible}`);

        if (errorVisible) {
            const errorText = await page.locator('.alert-danger').textContent();
            console.log(`[TEST] Error text: ${errorText}`);
        }

        // Count achievement cards
        const cardCount = await page.locator('.achievement-card').count();
        console.log(`[TEST] Achievement cards loaded: ${cardCount}`);

        // Check stats
        const statsText = await page.locator('.stats-section').textContent();
        console.log(`[TEST] Stats section: ${statsText.substring(0, 200)}`);

        // Keep browser open for 10 seconds
        console.log('[TEST] Keeping browser open for 10 seconds...');
        await page.waitForTimeout(10000);

    } catch (error) {
        console.error('[TEST] Error:', error.message);
    } finally {
        await browser.close();
        console.log('[TEST] Test complete!');
    }
})();
