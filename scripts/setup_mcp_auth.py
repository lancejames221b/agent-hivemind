#!/usr/bin/env python3
"""
MCP Hub Authentication Setup Script
Initialize authentication system, create admin user, and configure security
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_auth_manager import MCPAuthManager
from mcp_auth_tools import MCPAuthTools
from memory_server import MemoryStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_authentication():
    """Setup MCP Hub authentication system"""
    
    print("""
╭─────────────────────────────────────────────────────────────╮
│                                                             │
│    🔐 MCP Hub Authentication Setup                          │
│                                                             │
│    This script will initialize the authentication system   │
│    and create the initial admin user and API keys.         │
│                                                             │
╰─────────────────────────────────────────────────────────────╯
    """)
    
    # Load configuration
    config_path = Path(__file__).parent.parent / "config" / "config.json"
    
    if not config_path.exists():
        print("❌ Configuration file not found. Please ensure config/config.json exists.")
        return False
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Initialize components
    print("🔧 Initializing authentication components...")
    memory_storage = MemoryStorage(config)
    auth_manager = MCPAuthManager(config, memory_storage)
    auth_tools = MCPAuthTools(config, memory_storage)
    
    print("✅ Authentication system initialized")
    
    # Create admin user
    print("\n👤 Creating admin user...")
    admin_username = input("Enter admin username (default: admin): ").strip() or "admin"
    
    # Generate secure password or get from user
    import secrets
    import string
    
    use_generated = input("Generate secure password? (y/n, default: y): ").strip().lower()
    if use_generated != 'n':
        # Generate secure password
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        admin_password = ''.join(secrets.choice(alphabet) for i in range(16))
        print(f"🔑 Generated admin password: {admin_password}")
        print("⚠️  Please save this password securely!")
    else:
        admin_password = input("Enter admin password: ").strip()
        if len(admin_password) < 8:
            print("❌ Password must be at least 8 characters long")
            return False
    
    # Create admin user
    result = await auth_tools.create_user_account(
        username=admin_username,
        password=admin_password,
        role="admin",
        permissions=["*"]
    )
    
    if "✅" in result:
        print("✅ Admin user created successfully")
        
        # Extract user ID from result
        import re
        user_id_match = re.search(r'\*\*User ID\*\*: ([^\n]+)', result)
        if user_id_match:
            admin_user_id = user_id_match.group(1)
            
            # Create admin API key
            print("\n🔑 Creating admin API key...")
            api_key_result = await auth_tools.create_api_key(
                user_id=admin_user_id,
                key_name="Admin API Key",
                role="admin",
                permissions=["*"],
                expires_days=None  # No expiration
            )
            
            if "✅" in api_key_result:
                print("✅ Admin API key created successfully")
                
                # Extract API key from result
                api_key_match = re.search(r'`([^`]+)`', api_key_result)
                if api_key_match:
                    admin_api_key = api_key_match.group(1)
                    print(f"🔑 Admin API Key: {admin_api_key}")
                    print("⚠️  Please save this API key securely!")
            else:
                print(f"❌ Failed to create admin API key: {api_key_result}")
        else:
            print("⚠️  Could not extract user ID from result")
    else:
        print(f"❌ Failed to create admin user: {result}")
        return False
    
    # Configure default server authentication
    print("\n🖥️  Configuring default server authentication...")
    
    # Configure memory server
    memory_server_result = await auth_tools.configure_server_authentication(
        server_id="memory-server",
        auth_required=True,
        allowed_roles=["admin", "user"],
        tool_permissions={
            "store_memory": ["admin", "user"],
            "retrieve_memory": ["admin", "user", "readonly"],
            "search_memories": ["admin", "user", "readonly"],
            "delete_memory": ["admin"],
            "bulk_delete_memories": ["admin"],
            "gdpr_delete_user_data": ["admin"]
        },
        rate_limits={
            "admin": 1000,
            "user": 200,
            "readonly": 100
        },
        audit_level="standard"
    )
    
    if "✅" in memory_server_result:
        print("✅ Memory server authentication configured")
    else:
        print(f"⚠️  Memory server configuration: {memory_server_result}")
    
    # Update configuration with secure settings
    print("\n⚙️  Updating configuration with secure settings...")
    
    # Generate secure tokens if not already set
    security_config = config.get('security', {})
    
    if not security_config.get('jwt_secret') or security_config.get('jwt_secret') == 'change-this-secret-key':
        security_config['jwt_secret'] = secrets.token_urlsafe(64)
        print("🔐 Generated new JWT secret")
    
    # Ensure authentication is enabled
    security_config['enable_auth'] = True
    
    # Set secure defaults
    security_config.setdefault('rate_limiting', {
        'enabled': True,
        'requests_per_minute': 120,
        'burst_limit': 10
    })
    
    security_config.setdefault('audit', {
        'enabled': True,
        'retention_days': 90
    })
    
    config['security'] = security_config
    
    # Save updated configuration
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ Configuration updated with secure settings")
    
    # Store setup completion in hAIveMind
    await memory_storage.store_memory(
        content="MCP Hub authentication system setup completed",
        category='security',
        metadata={
            'event_type': 'auth_system_setup',
            'admin_username': admin_username,
            'setup_timestamp': asyncio.get_event_loop().time(),
            'version': '1.0.0'
        },
        scope='hive-shared'
    )
    
    print("\n🎉 MCP Hub Authentication Setup Complete!")
    print("\n📋 Summary:")
    print(f"   • Admin Username: {admin_username}")
    print(f"   • Admin Password: {admin_password}")
    if 'admin_api_key' in locals():
        print(f"   • Admin API Key: {admin_api_key}")
    print("   • Authentication: Enabled")
    print("   • Rate Limiting: Enabled")
    print("   • Audit Logging: Enabled")
    
    print("\n🚀 Next Steps:")
    print("   1. Save the admin credentials securely")
    print("   2. Start the MCP aggregator: python src/mcp_aggregator.py")
    print("   3. Access the auth dashboard at: http://localhost:8910/auth")
    print("   4. Create additional users and API keys as needed")
    
    return True

async def main():
    """Main setup function"""
    try:
        success = await setup_authentication()
        if success:
            print("\n✅ Setup completed successfully!")
            return 0
        else:
            print("\n❌ Setup failed!")
            return 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        logger.exception("Setup error")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)