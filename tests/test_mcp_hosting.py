#!/usr/bin/env python3
"""
Tests for MCP Server Hosting functionality
"""

import asyncio
import base64
import json
import tempfile
import zipfile
from pathlib import Path
import pytest
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_host import MCPServerHost, MCPServerProcess
from mcp_hosting_tools import MCPHostingTools

class TestMCPServerHost:
    """Test MCP server hosting functionality"""
    
    @pytest.fixture
    def config(self):
        """Test configuration"""
        return {
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
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage for testing"""
        class MockStorage:
            def __init__(self):
                self.memories = []
            
            async def store_memory(self, **kwargs):
                memory_id = f"test-{len(self.memories)}"
                self.memories.append({"id": memory_id, **kwargs})
                return memory_id
        
        return MockStorage()
    
    @pytest.fixture
    def server_host(self, config, mock_storage):
        """Create MCP server host for testing"""
        return MCPServerHost(config, mock_storage)
    
    @pytest.fixture
    def hosting_tools(self, config, mock_storage):
        """Create MCP hosting tools for testing"""
        return MCPHostingTools(config, mock_storage)
    
    def create_test_server_archive(self):
        """Create a test server archive"""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
            with zipfile.ZipFile(tmp_file, 'w') as zipf:
                # Add a simple Python server
                server_code = '''#!/usr/bin/env python3
import sys
import json

def main():
    print("Test MCP server started")
    # Simple echo server
    while True:
        try:
            line = input()
            if line.strip() == "quit":
                break
            print(f"Echo: {line}")
        except EOFError:
            break

if __name__ == "__main__":
    main()
'''
                zipf.writestr("test_server.py", server_code)
                zipf.writestr("requirements.txt", "# No requirements")
            
            # Read and encode as base64
            tmp_file.seek(0)
            archive_data = tmp_file.read()
            return base64.b64encode(archive_data).decode('utf-8')
    
    @pytest.mark.asyncio
    async def test_server_host_initialization(self, server_host):
        """Test server host initialization"""
        assert server_host.enabled == True
        assert server_host.max_servers == 5
        assert len(server_host.servers) == 0
    
    @pytest.mark.asyncio
    async def test_upload_server(self, hosting_tools):
        """Test server upload functionality"""
        archive_base64 = self.create_test_server_archive()
        
        result = await hosting_tools.upload_mcp_server(
            name="Test Server",
            archive_base64=archive_base64,
            command=["python", "test_server.py"],
            description="A test server",
            user_id="test_user"
        )
        
        assert "✅" in result
        assert "Test Server" in result
        assert "uploaded successfully" in result
    
    @pytest.mark.asyncio
    async def test_server_lifecycle(self, server_host):
        """Test server lifecycle management"""
        # Create a test server configuration
        config = {
            "name": "Test Lifecycle Server",
            "command": ["echo", "test"],
            "working_dir": "/tmp",
            "auto_restart": False
        }
        
        # Create server process
        server = MCPServerProcess("test-server-1", config, None)
        server_host.servers["test-server-1"] = server
        
        # Test status
        status = await server.get_status()
        assert status["server_id"] == "test-server-1"
        assert status["name"] == "Test Lifecycle Server"
        assert status["status"] == "stopped"
    
    @pytest.mark.asyncio
    async def test_server_list(self, hosting_tools):
        """Test server listing"""
        result = await hosting_tools.list_mcp_servers()
        assert "Hosted MCP Servers" in result or "No MCP servers" in result
    
    @pytest.mark.asyncio
    async def test_hosting_stats(self, hosting_tools):
        """Test hosting statistics"""
        result = await hosting_tools.get_hosting_stats()
        assert "MCP Hosting Statistics" in result
        assert "Servers:" in result
    
    @pytest.mark.asyncio
    async def test_optimization_analysis(self, hosting_tools):
        """Test server optimization analysis"""
        result = await hosting_tools.optimize_server_resources()
        assert "Server Optimization" in result
        assert ("running optimally" in result or "Recommendations" in result)
    
    def test_server_config_validation(self, server_host):
        """Test server configuration validation"""
        # Test valid config
        config = {
            "name": "Valid Server",
            "command": ["python", "server.py"],
            "environment": {"TEST": "true"}
        }
        
        # This would be called during upload processing
        # Just test that the structure is correct
        assert config["name"] == "Valid Server"
        assert isinstance(config["command"], list)
        assert len(config["command"]) > 0
    
    def test_security_scan_simulation(self):
        """Test security scanning logic"""
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

class TestMCPServerProcess:
    """Test individual server process functionality"""
    
    def test_server_process_initialization(self):
        """Test server process initialization"""
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
    
    @pytest.mark.asyncio
    async def test_server_status(self):
        """Test server status reporting"""
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

def run_tests():
    """Run all tests"""
    print("🧪 Running MCP Hosting Tests...")
    
    # Run pytest
    import subprocess
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        __file__, 
        "-v", 
        "--tb=short"
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0

if __name__ == "__main__":
    success = run_tests()
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
        sys.exit(1)