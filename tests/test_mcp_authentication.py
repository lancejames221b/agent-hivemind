#!/usr/bin/env python3
"""
Test suite for MCP Hub Authentication System
Tests authentication, authorization, rate limiting, and audit logging
"""

import asyncio
import json
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_auth_manager import MCPAuthManager, AuthContext, ServerAuthConfig
from mcp_auth_tools import MCPAuthTools
from mcp_auth_middleware import MCPToolAuthWrapper

class TestMCPAuthentication:
    """Test MCP authentication system"""
    
    @pytest.fixture
    async def auth_manager(self):
        """Create test auth manager"""
        config = {
            'security': {
                'enable_auth': True,
                'jwt_secret': 'test-secret-key-for-testing-only',
                'session_timeout_hours': 24,
                'rate_limiting': {
                    'enabled': True,
                    'requests_per_minute': 60
                },
                'ip_whitelist': ['127.0.0.1', '192.168.1.0/24'],
                'audit': {
                    'enabled': True,
                    'retention_days': 30
                }
            },
            'storage': {
                'auth_db': ':memory:',  # Use in-memory SQLite for testing
                'redis': {
                    'enable_cache': False  # Disable Redis for testing
                }
            }
        }
        
        memory_storage = Mock()
        memory_storage.store_memory = AsyncMock()
        memory_storage.broadcast_discovery = AsyncMock()
        
        auth_manager = MCPAuthManager(config, memory_storage)
        return auth_manager
    
    @pytest.fixture
    async def auth_tools(self, auth_manager):
        """Create test auth tools"""
        config = {
            'security': {
                'enable_auth': True,
                'jwt_secret': 'test-secret-key-for-testing-only'
            },
            'storage': {
                'auth_db': ':memory:'
            }
        }
        
        memory_storage = Mock()
        memory_storage.store_memory = AsyncMock()
        
        # Use the same auth manager to share database
        auth_tools = MCPAuthTools(config, memory_storage)
        auth_tools.auth_manager = auth_manager
        
        return auth_tools
    
    @pytest.mark.asyncio
    async def test_user_creation(self, auth_tools):
        """Test user account creation"""
        result = await auth_tools.create_user_account(
            username="testuser",
            password="testpassword123",
            role="user",
            permissions=["read", "write"]
        )
        
        assert "✅" in result
        assert "testuser" in result
        assert "User ID" in result
    
    @pytest.mark.asyncio
    async def test_user_authentication(self, auth_manager):
        """Test user authentication"""
        # Create a user first
        await auth_manager.create_user("testuser", "testpassword123", "user", ["read"])
        
        # Test successful authentication
        success, auth_context = await auth_manager.authenticate_user(
            "testuser", "testpassword123", "127.0.0.1"
        )
        
        assert success is True
        assert auth_context is not None
        assert auth_context.username == "testuser"
        assert auth_context.role == "user"
        assert "read" in auth_context.permissions
        
        # Test failed authentication
        success, auth_context = await auth_manager.authenticate_user(
            "testuser", "wrongpassword", "127.0.0.1"
        )
        
        assert success is False
        assert auth_context is None
    
    @pytest.mark.asyncio
    async def test_api_key_creation(self, auth_manager, auth_tools):
        """Test API key creation and authentication"""
        # Create a user first
        user_result = await auth_manager.create_user("apiuser", "password123", "admin", ["*"])
        user_id = user_result['user_id']
        
        # Create API key
        result = await auth_tools.create_api_key(
            user_id=user_id,
            key_name="Test API Key",
            role="admin",
            expires_days=30
        )
        
        assert "✅" in result
        assert "API Key" in result
        
        # Extract API key from result
        import re
        api_key_match = re.search(r'`([^`]+)`', result)
        assert api_key_match is not None
        api_key = api_key_match.group(1)
        
        # Test API key authentication
        success, auth_context = await auth_manager.authenticate_api_key(api_key, "127.0.0.1")
        
        assert success is True
        assert auth_context is not None
        assert auth_context.username == "apiuser"
        assert auth_context.role == "admin"
        assert "*" in auth_context.permissions
    
    @pytest.mark.asyncio
    async def test_server_auth_configuration(self, auth_manager, auth_tools):
        """Test server authentication configuration"""
        server_config = ServerAuthConfig(
            server_id="test-server",
            auth_required=True,
            allowed_roles={"admin", "user"},
            tool_permissions={
                "sensitive_tool": {"admin"},
                "read_tool": {"admin", "user", "readonly"}
            },
            rate_limits={"admin": 1000, "user": 100},
            audit_level="detailed"
        )
        
        success = await auth_manager.configure_server_auth("test-server", server_config)
        assert success is True
        
        # Test configuration retrieval
        retrieved_config = await auth_manager._get_server_auth_config("test-server")
        assert retrieved_config.server_id == "test-server"
        assert retrieved_config.auth_required is True
        assert "admin" in retrieved_config.allowed_roles
        assert "user" in retrieved_config.allowed_roles
    
    @pytest.mark.asyncio
    async def test_server_access_control(self, auth_manager):
        """Test server access control"""
        # Create user and auth context
        await auth_manager.create_user("testuser", "password123", "user", ["read"])
        success, auth_context = await auth_manager.authenticate_user(
            "testuser", "password123", "127.0.0.1"
        )
        
        # Configure server with role restrictions
        server_config = ServerAuthConfig(
            server_id="restricted-server",
            auth_required=True,
            allowed_roles={"admin"},  # Only admin allowed
        )
        await auth_manager.configure_server_auth("restricted-server", server_config)
        
        # Test access denied for user role
        has_access = await auth_manager.check_server_access(auth_context, "restricted-server")
        assert has_access is False
        
        # Configure server to allow user role
        server_config.allowed_roles = {"admin", "user"}
        await auth_manager.configure_server_auth("restricted-server", server_config)
        
        # Test access granted for user role
        has_access = await auth_manager.check_server_access(auth_context, "restricted-server")
        assert has_access is True
    
    @pytest.mark.asyncio
    async def test_tool_permissions(self, auth_manager):
        """Test tool-level permissions"""
        # Create user and auth context
        await auth_manager.create_user("testuser", "password123", "user", ["read"])
        success, auth_context = await auth_manager.authenticate_user(
            "testuser", "password123", "127.0.0.1"
        )
        
        # Configure server with tool permissions
        server_config = ServerAuthConfig(
            server_id="tool-server",
            auth_required=True,
            allowed_roles={"admin", "user"},
            tool_permissions={
                "admin_only_tool": {"admin"},
                "user_tool": {"admin", "user"},
                "public_tool": {"admin", "user", "readonly"}
            }
        )
        await auth_manager.configure_server_auth("tool-server", server_config)
        
        # Test tool permissions
        can_use_admin_tool = await auth_manager.check_tool_permission(
            auth_context, "tool-server", "admin_only_tool"
        )
        assert can_use_admin_tool is False
        
        can_use_user_tool = await auth_manager.check_tool_permission(
            auth_context, "tool-server", "user_tool"
        )
        assert can_use_user_tool is True
        
        can_use_public_tool = await auth_manager.check_tool_permission(
            auth_context, "tool-server", "public_tool"
        )
        assert can_use_public_tool is True
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, auth_manager):
        """Test rate limiting functionality"""
        # This test would require Redis in a real scenario
        # For now, test the basic logic
        
        # Create user and auth context
        await auth_manager.create_user("testuser", "password123", "user", ["read"])
        success, auth_context = await auth_manager.authenticate_user(
            "testuser", "password123", "127.0.0.1"
        )
        
        # Configure server with rate limits
        server_config = ServerAuthConfig(
            server_id="rate-limited-server",
            auth_required=True,
            rate_limits={"user": 5}  # Very low limit for testing
        )
        await auth_manager.configure_server_auth("rate-limited-server", server_config)
        
        # Without Redis, rate limiting should pass
        within_limit = await auth_manager.check_rate_limit(auth_context, "rate-limited-server")
        assert within_limit is True  # Should pass without Redis
    
    @pytest.mark.asyncio
    async def test_audit_logging(self, auth_manager):
        """Test audit logging functionality"""
        # Create user and auth context
        await auth_manager.create_user("testuser", "password123", "user", ["read"])
        success, auth_context = await auth_manager.authenticate_user(
            "testuser", "password123", "127.0.0.1"
        )
        
        # Test tool execution audit
        await auth_manager.audit_tool_execution(
            auth_context=auth_context,
            server_id="test-server",
            tool_name="test_tool",
            arguments={"param": "value"},
            success=True,
            execution_time=0.5,
            error=None
        )
        
        # Verify audit event was stored (check database)
        with auth_manager._get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT COUNT(*) FROM audit_events 
                WHERE event_type = 'tool_execution' AND user_id = ?
            ''', (auth_context.user_id,))
            count = cursor.fetchone()[0]
            assert count > 0
    
    @pytest.mark.asyncio
    async def test_security_analytics(self, auth_manager, auth_tools):
        """Test security analytics generation"""
        # Create some test data
        await auth_manager.create_user("testuser", "password123", "user", ["read"])
        
        # Generate some audit events
        from mcp_auth_manager import AuditEvent
        from datetime import datetime
        
        await auth_manager._audit_event(AuditEvent(
            timestamp=datetime.now(),
            event_type='login_failed',
            user_id='testuser',
            server_id=None,
            tool_name=None,
            client_ip='127.0.0.1',
            success=False,
            details={'reason': 'invalid_password'},
            risk_level='high'
        ))
        
        # Get analytics
        analytics = await auth_manager.get_security_analytics(days=1)
        
        assert 'failed_authentications' in analytics
        assert analytics['failed_authentications'] >= 1
        assert 'high_risk_events' in analytics
    
    @pytest.mark.asyncio
    async def test_tool_auth_wrapper(self, auth_manager):
        """Test tool authentication wrapper"""
        tool_wrapper = MCPToolAuthWrapper(auth_manager)
        
        # Create user and auth context
        await auth_manager.create_user("testuser", "password123", "user", ["read"])
        success, auth_context = await auth_manager.authenticate_user(
            "testuser", "password123", "127.0.0.1"
        )
        
        # Configure server
        server_config = ServerAuthConfig(
            server_id="wrapper-test-server",
            auth_required=True,
            allowed_roles={"admin", "user"},
            tool_permissions={"test_tool": {"admin", "user"}}
        )
        await auth_manager.configure_server_auth("wrapper-test-server", server_config)
        
        # Test tool call authentication
        auth_result = await tool_wrapper.authenticate_tool_call(
            server_id="wrapper-test-server",
            tool_name="test_tool",
            arguments={"param": "value"},
            auth_context=auth_context
        )
        
        assert auth_result[0] is True  # Should be authorized
        assert "Authorized" in auth_result[1]
    
    @pytest.mark.asyncio
    async def test_disabled_auth(self):
        """Test behavior when authentication is disabled"""
        config = {
            'security': {
                'enable_auth': False
            },
            'storage': {
                'auth_db': ':memory:'
            }
        }
        
        auth_manager = MCPAuthManager(config, Mock())
        
        # Authentication should always succeed when disabled
        success, auth_context = await auth_manager.authenticate_user(
            "anyuser", "anypassword", "127.0.0.1"
        )
        
        assert success is True
        assert auth_context is not None
        assert auth_context.role == "admin"
        assert "*" in auth_context.permissions

@pytest.mark.asyncio
async def test_integration_scenario():
    """Test a complete integration scenario"""
    # This test simulates a complete authentication flow
    config = {
        'security': {
            'enable_auth': True,
            'jwt_secret': 'test-integration-secret',
            'rate_limiting': {'enabled': True, 'requests_per_minute': 100},
            'audit': {'enabled': True}
        },
        'storage': {
            'auth_db': ':memory:',
            'redis': {'enable_cache': False}
        }
    }
    
    memory_storage = Mock()
    memory_storage.store_memory = AsyncMock()
    memory_storage.broadcast_discovery = AsyncMock()
    
    # Initialize components
    auth_manager = MCPAuthManager(config, memory_storage)
    auth_tools = MCPAuthTools(config, memory_storage)
    auth_tools.auth_manager = auth_manager
    tool_wrapper = MCPToolAuthWrapper(auth_manager)
    
    # 1. Create admin user
    admin_result = await auth_tools.create_user_account(
        "admin", "admin123", "admin", ["*"]
    )
    assert "✅" in admin_result
    
    # 2. Create regular user
    user_result = await auth_tools.create_user_account(
        "user1", "user123", "user", ["read", "write"]
    )
    assert "✅" in user_result
    
    # 3. Configure server authentication
    config_result = await auth_tools.configure_server_authentication(
        server_id="memory-server",
        auth_required=True,
        allowed_roles=["admin", "user"],
        tool_permissions={
            "store_memory": ["admin", "user"],
            "delete_memory": ["admin"]
        }
    )
    assert "✅" in config_result
    
    # 4. Authenticate users
    admin_success, admin_context = await auth_manager.authenticate_user(
        "admin", "admin123", "127.0.0.1"
    )
    assert admin_success is True
    
    user_success, user_context = await auth_manager.authenticate_user(
        "user1", "user123", "127.0.0.1"
    )
    assert user_success is True
    
    # 5. Test tool access
    # Admin should have access to delete_memory
    admin_auth = await tool_wrapper.authenticate_tool_call(
        "memory-server", "delete_memory", {}, admin_context
    )
    assert admin_auth[0] is True
    
    # User should NOT have access to delete_memory
    user_auth = await tool_wrapper.authenticate_tool_call(
        "memory-server", "delete_memory", {}, user_context
    )
    assert user_auth[0] is False
    
    # User should have access to store_memory
    user_store_auth = await tool_wrapper.authenticate_tool_call(
        "memory-server", "store_memory", {}, user_context
    )
    assert user_store_auth[0] is True
    
    # 6. Test audit logging
    await tool_wrapper.audit_tool_call(
        "memory-server", "store_memory", {"content": "test"}, 
        user_context, True, 0.1
    )
    
    # 7. Get security analytics
    analytics = await auth_manager.get_security_analytics(1)
    assert 'failed_authentications' in analytics

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])