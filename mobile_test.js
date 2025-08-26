const puppeteer = require('puppeteer');

async function testMobileLogin() {
    console.log('🔍 Testing mobile login...');
    
    const browser = await puppeteer.launch({
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor'
        ]
    });
    
    const page = await browser.newPage();
    
    // Set mobile viewport (iPhone 12 Pro)
    await page.setViewport({
        width: 390,
        height: 844,
        deviceScaleFactor: 3,
        isMobile: true,
        hasTouch: true,
        isLandscape: false
    });
    
    // Set mobile user agent
    await page.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1');
    
    try {
        // Navigate to login page
        console.log('📱 Opening login page...');
        await page.goto('http://localhost:8900/admin/login.html', { waitUntil: 'networkidle2' });
        
        // Take screenshot
        await page.screenshot({ path: '/home/lj/memory-mcp/mobile-login-before.png', fullPage: true });
        console.log('📸 Screenshot saved: mobile-login-before.png');
        
        // Fill login form
        console.log('✏️  Filling login form...');
        await page.type('#username', 'admin');
        await page.type('#password', 'admin123');
        
        // Take screenshot before clicking
        await page.screenshot({ path: '/home/lj/memory-mcp/mobile-login-filled.png', fullPage: true });
        console.log('📸 Screenshot saved: mobile-login-filled.png');
        
        // Click login button
        console.log('🔘 Clicking login button...');
        await page.click('#loginButton');
        
        // Wait for either success redirect or error
        console.log('⏳ Waiting for login response...');
        await Promise.race([
            page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 5000 }),
            page.waitForSelector('.error-message', { visible: true, timeout: 5000 })
        ]).catch(() => {
            console.log('⚠️  No immediate redirect or error message');
        });
        
        const currentUrl = page.url();
        console.log('🌐 Current URL:', currentUrl);
        
        // Take final screenshot
        await page.screenshot({ path: '/home/lj/memory-mcp/mobile-login-after.png', fullPage: true });
        console.log('📸 Screenshot saved: mobile-login-after.png');
        
        // Check if login was successful
        if (currentUrl.includes('dashboard.html')) {
            console.log('✅ Mobile login successful - redirected to dashboard');
        } else if (currentUrl.includes('login.html')) {
            console.log('❌ Mobile login failed - still on login page');
            
            // Check for error messages
            const errorMessage = await page.$eval('.error-message', el => el.textContent).catch(() => null);
            if (errorMessage) {
                console.log('📢 Error message:', errorMessage);
            }
        }
        
        // Check console logs
        const logs = await page.evaluate(() => {
            const logs = window.console.log.toString();
            return logs;
        });
        
    } catch (error) {
        console.error('🚨 Test failed:', error.message);
        await page.screenshot({ path: '/home/lj/memory-mcp/mobile-error.png', fullPage: true });
    } finally {
        await browser.close();
        console.log('🔚 Test completed');
    }
}

// Run the test
testMobileLogin().catch(console.error);