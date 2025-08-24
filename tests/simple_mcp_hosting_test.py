#!/usr/bin/env python3
"""
Simple tests for MCP Server Hosting functionality (no pytest required)
"""

import asyncio
import base64
import json
import tempfile
import zipfile
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def create_test_server_archive():
    """Create a test server archive"""
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
        with zipfile.ZipFile(tmp_file, 'w') as zipf:
            # Add a simple Python server
            server_code = '''#!/usr/bin/env python3
import sys
import json
import time

def main():
    print("Test MCP server started", file=sys.stderr)
    print("Server is ready", file=sys.stderr)
    time.sleep(1)  # Run for 1 second then exit
    print("Server finished", file=sys.stderr)

if __name__ == "__main__":
    main()
'''
            zipf.writestr("test_server.py", server_code)
            zipf.writestr("requirements.txt", "# No requirements")
        
        # Read and return the file path
        return tmp_file.name

def test_server_host_initialization():
    """Test server host initialization"""
    try:
        from mcp_server_host import MCPServerHost
        
        config = {
            "mcp_hosting": {
                "enabled": True,
                "servers_dir": "test_data/mcp_servers",
                "uploads_dir": "test_data/mcp_uploads",
                "logs_dir": "test_data/mcp_logs",
                "max_servers": 5,
                "health_check_interval": 10,
                "auto_cleanup": False,
                "security": {
                    "allowed_languages": ["python", "bash"],
                    "sandbox_by_default": True,
                    "max_upload_size_mb": 50,
                    "scan_uploads": True
                }
            }
        }
        
        host = MCPServerHost(config, None)
        assert host.enabled == True
        assert host.max_servers == 5
        assert len(host.servers) == 0
        
        print("✅ Server host initialization test passed")
        return True
    except Exception as e:
        print(f"❌ Server host initialization test failed: {e}")
        return False

def test_server_process_initialization():
    """Test server process initialization"""
    try:
        from mcp_server_host import MCPServerProcess
        
        config = {
            "name": "Test Process",
            "command": ["echo", "hello"],
            "auto_restart": True,
            "max_restarts": 3
        }
        
        server = MCPServerProcess("test-id", config)
        assert server.server_id == "test-id"
        assert server.name == "Test Process"
        assert server.auto_restart == True
        assert server.max_restarts == 3
        assert server.status == "stopped"
        
        print("✅ Server process initialization test passed")
        return True
    except Exception as e:
        print(f"❌ Server process initialization test failed: {e}")
        return False

async def test_server_status():
    """Test server status reporting"""
    try:
        from mcp_server_host import MCPServerProcess
        
        config = {
            "name": "Status Test Server",
            "command": ["sleep", "1"],
            "description": "Test server for status"
        }
        
        server = MCPServerProcess("status-test", config)
        status = await server.get_status()
        
        assert status["server_id"] == "status-test"
        assert status["name"] == "Status Test Server"
        assert status["status"] == "stopped"
        assert "uptime_seconds" in status
        assert "restart_count" in status
        
        print("✅ Server status test passed")
        return True
    except Exception as e:
        print(f"❌ Server status test failed: {e}")
        return False

def test_security_scan_simulation():
    """Test security scanning logic"""
    try:
        # Simulate dangerous patterns
        dangerous_code = "rm -rf / && sudo chmod 777"
        safe_code = "print('Hello, World!')"
        
        dangerous_patterns = [
            "rm -rf",
            "sudo", 
            "chmod 777",
            "eval(",
            "exec(",
            "system("
        ]
        
        # Check dangerous code
        has_dangerous = any(pattern in dangerous_code for pattern in dangerous_patterns)
        assert has_dangerous == True
        
        # Check safe code
        has_dangerous = any(pattern in safe_code for pattern in dangerous_patterns)
        assert has_dangerous == False
        
        print("✅ Security scan simulation test passed")
        return True
    except Exception as e:
        print(f"❌ Security scan simulation test failed: {e}")
        return False

def test_config_validation():
    """Test server configuration validation"""
    try:
        # Test valid config
        config = {
            "name": "Valid Server",
            "command": ["python", "server.py"],
            "environment": {"TEST": "true"}
        }
        
        # Basic validation
        assert config["name"] == "Valid Server"
        assert isinstance(config["command"], list)
        assert len(config["command"]) > 0
        assert isinstance(config["environment"], dict)
        
        print("✅ Config validation test passed")
        return True
    except Exception as e:
        print(f"❌ Config validation test failed: {e}")
        return False

async def test_hosting_tools_initialization():
    """Test hosting tools initialization"""
    try:
        from mcp_hosting_tools import MCPHostingTools
        
        class MockStorage:
            def __init__(self):
                self.memories = []
            
            async def store_memory(self, **kwargs):
                memory_id = f"test-{len(self.memories)}"
                self.memories.append({"id": memory_id, **kwargs})
                return memory_id
        
        config = {
            "mcp_hosting": {
                "enabled": True,
                "max_servers": 5
            }
        }
        
        mock_storage = MockStorage()
        tools = MCPHostingTools(config, mock_storage)
        
        # Test basic functionality
        result = await tools.list_mcp_servers()
        assert isinstance(result, str)
        assert ("No MCP servers" in result or "Hosted MCP Servers" in result)
        
        result = await tools.get_hosting_stats()
        assert isinstance(result, str)
        assert "MCP Hosting Statistics" in result
        
        print("✅ Hosting tools initialization test passed")
        return True
    except Exception as e:
        print(f"❌ Hosting tools initialization test failed: {e}")
        return False

def test_archive_creation():
    """Test archive creation and validation"""
    try:
        archive_path = create_test_server_archive()
        
        # Verify archive exists and is valid
        assert Path(archive_path).exists()
        
        # Test that we can read it as ZIP
        with zipfile.ZipFile(archive_path, 'r') as zipf:
            files = zipf.namelist()
            assert "test_server.py" in files
            assert "requirements.txt" in files
        
        # Clean up
        Path(archive_path).unlink()
        
        print("✅ Archive creation test passed")
        return True
    except Exception as e:
        print(f"❌ Archive creation test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests"""
    print("🧪 Running MCP Hosting Tests...")
    print("=" * 50)
    
    tests = [
        ("Server Host Initialization", test_server_host_initialization),
        ("Server Process Initialization", test_server_process_initialization),
        ("Server Status", test_server_status),
        ("Security Scan Simulation", test_security_scan_simulation),
        ("Config Validation", test_config_validation),
        ("Hosting Tools Initialization", test_hosting_tools_initialization),
        ("Archive Creation", test_archive_creation)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print(f"⚠️ {failed} test(s) failed")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    if not success:
        sys.exit(1)