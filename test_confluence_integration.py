#!/usr/bin/env python3
"""
Test script for Confluence Integration

This script tests the basic functionality of the Confluence integration
without requiring actual Confluence credentials.
"""

import asyncio
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_confluence_integration():
    """Test the Confluence integration components"""
    
    print("🧪 Testing Confluence Integration Components")
    print("=" * 50)
    
    # Test 1: Import modules
    print("\n1. Testing module imports...")
    try:
        from src.confluence_integration import ConfluenceIntegration, ConfluencePageInfo, ConfluencePlaybook
        from src.confluence_mcp_tools import ConfluenceMCPTools
        from src.confluence_sync_service import ConfluenceSyncService, ConfluenceSyncScheduler
        from src.confluence_dashboard import ConfluenceDashboard
        print("✅ All modules imported successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Test configuration parsing
    print("\n2. Testing configuration...")
    try:
        config_path = Path("config/config.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            confluence_config = config.get('connectors', {}).get('confluence', {})
            print(f"✅ Configuration loaded: {len(confluence_config)} settings")
            print(f"   - URL: {confluence_config.get('url', 'Not set')}")
            print(f"   - Enabled: {confluence_config.get('enabled', False)}")
            print(f"   - Spaces: {confluence_config.get('spaces', [])}")
        else:
            print("⚠️  Config file not found, using defaults")
            confluence_config = {
                'url': 'https://example.atlassian.net',
                'enabled': False,
                'spaces': ['TEST']
            }
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False
    
    # Test 3: Test database integration
    print("\n3. Testing database integration...")
    try:
        from src.database import ControlDatabase
        
        # Use in-memory database for testing
        db = ControlDatabase(":memory:")
        
        # Test playbook creation
        playbook_id = db.create_playbook(
            name="Test Confluence Playbook",
            category="test",
            tags=["confluence", "test"]
        )
        
        version_id = db.add_playbook_version(
            playbook_id=playbook_id,
            content="version: 1\nname: Test\nsteps: []",
            format="yaml",
            metadata={
                'source': 'confluence',
                'confluence_page_id': 'test123',
                'confluence_space': 'TEST'
            }
        )
        
        print(f"✅ Database integration working: playbook_id={playbook_id}, version_id={version_id}")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    # Test 4: Test MCP tools initialization
    print("\n4. Testing MCP tools...")
    try:
        mcp_tools = ConfluenceMCPTools(config, db, None)
        tools = mcp_tools.get_mcp_tools()
        
        print(f"✅ MCP tools initialized: {len(tools)} tools available")
        for tool in tools:
            print(f"   - {tool['name']}: {tool['description'][:50]}...")
            
    except Exception as e:
        print(f"❌ MCP tools test failed: {e}")
        return False
    
    # Test 5: Test playbook parsing (mock)
    print("\n5. Testing playbook parsing...")
    try:
        from bs4 import BeautifulSoup
        
        # Test HTML parsing
        test_html = """
        <h1>Test Runbook</h1>
        <p>This is a test procedure for deployment.</p>
        <ol>
            <li>Step 1: Check prerequisites</li>
            <li>Step 2: Deploy application</li>
            <li>Step 3: Verify deployment</li>
        </ol>
        """
        
        soup = BeautifulSoup(test_html, 'html.parser')
        steps = soup.find_all('li')
        
        print(f"✅ HTML parsing working: extracted {len(steps)} steps")
        for i, step in enumerate(steps, 1):
            print(f"   - Step {i}: {step.get_text().strip()}")
            
    except Exception as e:
        print(f"❌ Parsing test failed: {e}")
        return False
    
    # Test 6: Test sync service initialization
    print("\n6. Testing sync service...")
    try:
        sync_service = ConfluenceSyncService(config, db, None)
        status = await sync_service.get_status()
        
        print(f"✅ Sync service initialized")
        print(f"   - Running: {status['running']}")
        print(f"   - Enabled: {status['enabled']}")
        print(f"   - Sync interval: {status['sync_interval']}s")
        
    except Exception as e:
        print(f"❌ Sync service test failed: {e}")
        return False
    
    # Test 7: Test dashboard integration
    print("\n7. Testing dashboard integration...")
    try:
        dashboard = ConfluenceDashboard(config, db, None)
        router = dashboard.get_router()
        
        print(f"✅ Dashboard initialized")
        print(f"   - Router prefix: {router.prefix}")
        print(f"   - Routes: {len(router.routes)} endpoints")
        
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All Confluence integration tests passed!")
    print("\nNext steps:")
    print("1. Configure Confluence credentials in config/config.json")
    print("2. Enable Confluence integration (set enabled: true)")
    print("3. Add your Confluence spaces to the spaces array")
    print("4. Restart the hAIveMind server to load the integration")
    print("5. Use the new Confluence MCP tools to import playbooks")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_confluence_integration())
    exit(0 if success else 1)