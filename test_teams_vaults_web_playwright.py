"""
Teams & Vaults Web Interface - Playwright Smoke Tests

Comprehensive E2E tests for the Teams & Vaults web interface.
"""

import pytest
import subprocess
import time
import sys
from playwright.sync_api import sync_playwright, expect


# Test configuration
BASE_URL = "http://localhost:8901"
TIMEOUT = 30000  # 30 seconds


@pytest.fixture(scope="session")
def web_server():
    """Start the web server for testing"""
    print("\n🚀 Starting Teams & Vaults web server...")

    # Start server in background
    server_process = subprocess.Popen(
        [sys.executable, "src/teams_vaults_web.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server to start
    print("⏳ Waiting for server to be ready...")
    time.sleep(5)

    # Check if server is running
    try:
        import requests
        for _ in range(10):
            try:
                response = requests.get(f"{BASE_URL}/health", timeout=2)
                if response.status_code == 200:
                    print("✓ Server is ready")
                    break
            except:
                time.sleep(1)
    except ImportError:
        print("⚠ requests module not available, skipping health check")

    yield server_process

    # Cleanup
    print("\n🛑 Stopping web server...")
    server_process.terminate()
    server_process.wait(timeout=5)
    print("✓ Server stopped")


@pytest.fixture
def browser_context():
    """Create a browser context for tests"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        yield context
        context.close()
        browser.close()


def test_dashboard_loads(web_server, browser_context):
    """Test 1: Dashboard page loads successfully"""
    print("\n" + "=" * 70)
    print("TEST 1: Dashboard Page Load")
    print("=" * 70)

    page = browser_context.new_page()

    try:
        # Navigate to dashboard
        print(f"Navigating to {BASE_URL}...")
        page.goto(BASE_URL, timeout=TIMEOUT)

        # Check title
        print("Checking page title...")
        expect(page).to_have_title("Teams & Vaults Dashboard", timeout=TIMEOUT)
        print("✓ Title matches")

        # Check header
        print("Checking header...")
        header = page.locator(".header h1")
        expect(header).to_contain_text("Teams & Vaults Dashboard")
        print("✓ Header present")

        # Check navigation
        print("Checking navigation...")
        nav = page.locator("nav")
        expect(nav).to_be_visible()
        print("✓ Navigation visible")

        # Check stats cards
        print("Checking stats cards...")
        stats = page.locator(".stats-grid")
        expect(stats).to_be_visible()
        print("✓ Stats grid visible")

        print("\n✅ TEST 1 PASSED: Dashboard loads successfully")

    finally:
        page.close()


def test_teams_page(web_server, browser_context):
    """Test 2: Teams page and team creation"""
    print("\n" + "=" * 70)
    print("TEST 2: Teams Page and Team Creation")
    print("=" * 70)

    page = browser_context.new_page()

    try:
        # Navigate to teams page
        print(f"Navigating to {BASE_URL}/teams...")
        page.goto(f"{BASE_URL}/teams", timeout=TIMEOUT)

        # Check title
        print("Checking page title...")
        expect(page).to_have_title("Teams Management", timeout=TIMEOUT)
        print("✓ Title matches")

        # Find create button
        print("Looking for 'Create New Team' button...")
        create_button = page.locator("button:has-text('Create New Team')")
        expect(create_button).to_be_visible()
        print("✓ Create button found")

        # Click create button
        print("Clicking create button...")
        create_button.click()

        # Check modal appeared
        print("Checking for modal...")
        modal = page.locator("#createModal")
        expect(modal).to_be_visible()
        print("✓ Modal visible")

        # Fill form
        print("Filling team creation form...")
        page.fill("input[name='name']", "Playwright Test Team")
        page.fill("textarea[name='description']", "Created by Playwright smoke test")
        print("✓ Form filled")

        # Submit form
        print("Submitting form...")
        page.click("button[type='submit']")

        # Wait for navigation
        print("Waiting for redirect...")
        page.wait_for_url(f"{BASE_URL}/teams/*", timeout=TIMEOUT)
        print("✓ Redirected to team detail page")

        # Verify team was created
        print("Verifying team name on detail page...")
        expect(page.locator("h3")).to_contain_text("Playwright Test Team")
        print("✓ Team created successfully")

        print("\n✅ TEST 2 PASSED: Teams page and creation working")

    finally:
        page.close()


def test_vaults_page(web_server, browser_context):
    """Test 3: Vaults page and vault creation"""
    print("\n" + "=" * 70)
    print("TEST 3: Vaults Page and Vault Creation")
    print("=" * 70)

    page = browser_context.new_page()

    try:
        # Navigate to vaults page
        print(f"Navigating to {BASE_URL}/vaults...")
        page.goto(f"{BASE_URL}/vaults", timeout=TIMEOUT)

        # Check title
        print("Checking page title...")
        expect(page).to_have_title("Vaults Management", timeout=TIMEOUT)
        print("✓ Title matches")

        # Find create button
        print("Looking for 'Create New Vault' button...")
        create_button = page.locator("button:has-text('Create New Vault')")
        expect(create_button).to_be_visible()
        print("✓ Create button found")

        # Click create button
        print("Clicking create button...")
        create_button.click()

        # Check modal
        print("Checking for modal...")
        modal = page.locator("#createModal")
        expect(modal).to_be_visible()
        print("✓ Modal visible")

        # Fill form
        print("Filling vault creation form...")
        page.fill("input[name='name']", "Playwright Test Vault")
        page.select_option("select[name='vault_type']", "personal")
        print("✓ Form filled")

        # Submit form
        print("Submitting form...")
        page.click("button[type='submit']")

        # Wait for navigation
        print("Waiting for redirect...")
        page.wait_for_url(f"{BASE_URL}/vaults/*", timeout=TIMEOUT)
        print("✓ Redirected to vault detail page")

        # Verify vault was created
        print("Verifying vault name on detail page...")
        expect(page.locator("h1")).to_contain_text("Playwright Test Vault")
        print("✓ Vault created successfully")

        print("\n✅ TEST 3 PASSED: Vaults page and creation working")

    finally:
        page.close()


def test_secret_storage(web_server, browser_context):
    """Test 4: Secret storage and retrieval"""
    print("\n" + "=" * 70)
    print("TEST 4: Secret Storage and Retrieval")
    print("=" * 70)

    page = browser_context.new_page()

    try:
        # First create a vault
        print("Creating test vault...")
        page.goto(f"{BASE_URL}/vaults", timeout=TIMEOUT)
        page.click("button:has-text('Create New Vault')")
        page.fill("input[name='name']", "Secret Test Vault")
        page.select_option("select[name='vault_type']", "personal")
        page.click("button[type='submit']")
        page.wait_for_url(f"{BASE_URL}/vaults/*", timeout=TIMEOUT)
        print("✓ Vault created")

        # Store a secret
        print("Storing test secret...")
        page.click("button:has-text('Store New Secret')")
        page.fill("input[name='key']", "test_api_key")
        page.fill("textarea[name='value']", "sk_test_playwright_12345")
        page.click("button[type='submit']")

        # Wait for page reload
        print("Waiting for page reload...")
        time.sleep(2)
        page.reload()
        print("✓ Secret stored")

        # Verify secret appears in table
        print("Verifying secret in table...")
        expect(page.locator("td:has-text('test_api_key')")).to_be_visible()
        print("✓ Secret visible in table")

        print("\n✅ TEST 4 PASSED: Secret storage working")

    finally:
        page.close()


def test_navigation(web_server, browser_context):
    """Test 5: Navigation between pages"""
    print("\n" + "=" * 70)
    print("TEST 5: Navigation Flow")
    print("=" * 70)

    page = browser_context.new_page()

    try:
        # Start at dashboard
        print("Starting at dashboard...")
        page.goto(BASE_URL, timeout=TIMEOUT)
        expect(page).to_have_url(BASE_URL + "/")
        print("✓ At dashboard")

        # Navigate to teams
        print("Navigating to teams...")
        page.click("a[href='/teams']")
        expect(page).to_have_url(f"{BASE_URL}/teams")
        print("✓ At teams page")

        # Navigate to vaults
        print("Navigating to vaults...")
        page.click("a[href='/vaults']")
        expect(page).to_have_url(f"{BASE_URL}/vaults")
        print("✓ At vaults page")

        # Navigate back to dashboard
        print("Navigating back to dashboard...")
        page.click("a[href='/']")
        expect(page).to_have_url(BASE_URL + "/")
        print("✓ Back at dashboard")

        print("\n✅ TEST 5 PASSED: Navigation working")

    finally:
        page.close()


def test_health_endpoint(web_server):
    """Test 6: Health check API endpoint"""
    print("\n" + "=" * 70)
    print("TEST 6: Health Check API")
    print("=" * 70)

    try:
        import requests

        print(f"Calling {BASE_URL}/health...")
        response = requests.get(f"{BASE_URL}/health", timeout=5)

        print(f"Status code: {response.status_code}")
        assert response.status_code == 200, "Health check failed"
        print("✓ Status 200")

        data = response.json()
        print(f"Response: {data}")

        assert data["status"] == "healthy", "Status not healthy"
        print("✓ Status is healthy")

        assert "encryption_enabled" in data, "Missing encryption status"
        print(f"✓ Encryption enabled: {data['encryption_enabled']}")

        print("\n✅ TEST 6 PASSED: Health endpoint working")

    except ImportError:
        print("⚠ Skipping health check test (requests module not available)")


def run_all_tests():
    """Run all tests"""
    print("\n" + "╔" + "=" * 70 + "╗")
    print("║" + " " * 15 + "Teams & Vaults Web Interface" + " " * 27 + "║")
    print("║" + " " * 20 + "Playwright Smoke Tests" + " " * 28 + "║")
    print("╚" + "=" * 70 + "╝\n")

    # Run with pytest
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short"
    ])


if __name__ == "__main__":
    run_all_tests()
