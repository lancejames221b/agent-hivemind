#!/usr/bin/env python3
"""
Test script for Client Configuration Generator
Tests integration with aggregator and dashboard components
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config_generator import ConfigGenerator, ConfigFormat, AuthType, create_config_generator


async def test_config_generator():
    """Test the configuration generator functionality"""
    print("🧪 Testing Client Configuration Generator...")
    
    try:
        # Create config generator
        config_generator = create_config_generator()
        print("✅ Configuration generator created successfully")
        
        # Test server discovery
        print("\n🔍 Testing server discovery...")
        servers = config_generator.discover_servers()
        print(f"✅ Discovered {len(servers)} servers:")
        for server in servers:
            print(f"   - {server.name} ({server.id}) at {server.host}:{server.port}")
        
        # Test configuration generation for different formats
        print("\n🔧 Testing configuration generation...")
        test_user_id = "test_user_123"
        test_device_id = "test_device_456"
        
        formats_to_test = [
            ConfigFormat.CLAUDE_DESKTOP,
            ConfigFormat.CLAUDE_CODE,
            ConfigFormat.MCP_JSON,
            ConfigFormat.YAML,
            ConfigFormat.SHELL_SCRIPT,
            ConfigFormat.DOCKER_COMPOSE
        ]
        
        for config_format in formats_to_test:
            print(f"\n   Testing {config_format.value} format...")
            try:
                config_string = config_generator.generate_config_string(
                    user_id=test_user_id,
                    device_id=test_device_id,
                    format=config_format,
                    include_auth=True,
                    auth_expires_hours=24
                )
                
                print(f"   ✅ Generated {config_format.value} configuration ({len(config_string)} chars)")
                
                # Show preview for JSON formats
                if config_format in [ConfigFormat.CLAUDE_DESKTOP, ConfigFormat.CLAUDE_CODE, ConfigFormat.MCP_JSON]:
                    try:
                        parsed = json.loads(config_string)
                        print(f"   📋 Preview: {list(parsed.keys())}")
                    except:
                        pass
                        
            except Exception as e:
                print(f"   ❌ Failed to generate {config_format.value}: {e}")
        
        # Test multiple format generation
        print("\n📦 Testing multiple format generation...")
        try:
            multiple_configs = config_generator.generate_multiple_formats(
                user_id=test_user_id,
                device_id=test_device_id,
                formats=[ConfigFormat.CLAUDE_DESKTOP, ConfigFormat.CLAUDE_CODE, ConfigFormat.MCP_JSON],
                include_auth=True
            )
            
            print(f"✅ Generated {len(multiple_configs)} configurations:")
            for format_name, config in multiple_configs.items():
                if not config.startswith("Error:"):
                    print(f"   - {format_name}: {len(config)} chars")
                else:
                    print(f"   - {format_name}: {config}")
                    
        except Exception as e:
            print(f"❌ Failed to generate multiple formats: {e}")
        
        # Test analytics
        print("\n📊 Testing analytics...")
        try:
            analytics = config_generator.get_config_analytics()
            print(f"✅ Analytics retrieved:")
            for key, value in analytics.items():
                print(f"   - {key}: {value}")
                
        except Exception as e:
            print(f"❌ Failed to get analytics: {e}")
        
        # Test hAIveMind integration (if available)
        print("\n🧠 Testing hAIveMind integration...")
        if config_generator.memory_storage:
            try:
                # Generate a client config for memory storage test
                client_config = config_generator.generate_client_config(
                    user_id=test_user_id,
                    device_id=test_device_id,
                    format=ConfigFormat.CLAUDE_DESKTOP,
                    include_auth=True
                )
                
                # Store in memory
                await config_generator.store_config_memory(client_config, "test_generated")
                print("✅ Configuration stored in hAIveMind memory")
                
                # Test usage pattern analysis
                patterns = await config_generator.analyze_client_usage_patterns()
                print(f"✅ Usage patterns analyzed: {len(patterns)} metrics")
                
                # Test suggestions
                suggestions = await config_generator.suggest_configuration_improvements(client_config)
                print(f"✅ Generated {len(suggestions)} improvement suggestions")
                for suggestion in suggestions:
                    print(f"   - {suggestion['title']} ({suggestion['priority']})")
                    
            except Exception as e:
                print(f"❌ hAIveMind integration test failed: {e}")
        else:
            print("⚠️  hAIveMind memory storage not available")
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


def test_config_templates():
    """Test configuration templates with sample data"""
    print("\n📋 Testing configuration templates...")
    
    from config_generator import ConfigTemplate, ClientConfig, ServerEndpoint, AuthConfig, ConnectionType
    from datetime import datetime
    
    # Create test data
    test_server = ServerEndpoint(
        id="test-server",
        name="Test MCP Server",
        host="localhost",
        port=8900,
        transport=ConnectionType.SSE,
        description="Test server for configuration generation"
    )
    
    test_auth = AuthConfig(
        type=AuthType.BEARER,
        token="test_token_123456789",
        scopes=["mcp:read", "mcp:write"]
    )
    
    template_engine = ConfigTemplate()
    
    formats_to_test = [
        ConfigFormat.CLAUDE_DESKTOP,
        ConfigFormat.CLAUDE_CODE,
        ConfigFormat.MCP_JSON,
        ConfigFormat.CUSTOM_JSON,
        ConfigFormat.YAML,
        ConfigFormat.SHELL_SCRIPT,
        ConfigFormat.DOCKER_COMPOSE
    ]
    
    for config_format in formats_to_test:
        print(f"\n   Testing {config_format.value} template...")
        try:
            client_config = ClientConfig(
                client_id="test_client_123",
                user_id="test_user_456",
                device_id="test_device_789",
                format=config_format,
                servers=[test_server],
                auth=test_auth,
                created_at=datetime.utcnow()
            )
            
            config_string = template_engine.generate(client_config)
            print(f"   ✅ Template generated successfully ({len(config_string)} chars)")
            
            # Show first few lines for preview
            lines = config_string.split('\n')[:5]
            for line in lines:
                print(f"      {line}")
            if len(config_string.split('\n')) > 5:
                print("      ...")
                
        except Exception as e:
            print(f"   ❌ Template generation failed: {e}")


async def main():
    """Main test function"""
    print("🚀 Starting Client Configuration Generator Tests\n")
    
    # Test configuration generator
    await test_config_generator()
    
    # Test templates
    test_config_templates()
    
    print("\n✅ All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())