#!/usr/bin/env python3
"""
Simple memory storage attempt for hAIveMind success message
"""
import os
import sys
import json
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    print("🧠 hAIveMind Memory Storage Attempt")
    print("=" * 40)
    
    # Check if we can import the memory system
    try:
        print("📦 Attempting to import memory system...")
        from memory_server import MemoryStorage
        print("✅ Successfully imported MemoryStorage")
    except ImportError as e:
        print(f"❌ Failed to import MemoryStorage: {e}")
        print("This might be due to missing dependencies.")
        return False
    
    # Load configuration
    try:
        print("📋 Loading configuration...")
        config_path = Path(__file__).parent / "config" / "config.json"
        with open(config_path) as f:
            config = json.load(f)
        print("✅ Configuration loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return False
    
    # Try to create storage instance
    try:
        print("🔧 Initializing memory storage...")
        # Disable Redis to avoid connection issues
        config['storage']['redis']['enable_cache'] = False
        storage = MemoryStorage(config)
        print(f"✅ Memory storage initialized")
        print(f"   Machine ID: {storage.machine_id}")
        print(f"   Agent ID: {storage.agent_id}")
    except Exception as e:
        print(f"❌ Failed to initialize storage: {e}")
        return False
    
    # Try to store the memory
    try:
        print("💾 Storing success memory...")
        
        # We need to use asyncio for the async method
        import asyncio
        
        async def store_async():
            memory_id = await storage.store_memory(
                content="hAIveMind MCP client is now working perfectly with cursor-agent",
                category="infrastructure",
                context="MCP integration success with cursor-agent",
                project="memory-mcp",
                tags=["haivemind", "mcp", "cursor-agent", "success", "integration"],
                scope="project-shared",
                sensitive=False
            )
            return memory_id
        
        memory_id = asyncio.run(store_async())
        print(f"✅ Memory stored successfully!")
        print(f"   Memory ID: {memory_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to store memory: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 SUCCESS: Memory stored in hAIveMind system!")
        print("The message 'hAIveMind MCP client is now working perfectly with cursor-agent' has been stored.")
    else:
        print("\n💥 FAILED: Could not store memory in hAIveMind system.")
        print("The message has been documented in HAIVEMIND_MCP_SUCCESS.md instead.")
    
    print("\n📄 Documentation created: HAIVEMIND_MCP_SUCCESS.md")
    print("📝 Storage scripts created for future use:")
    print("   - store_haivemind_success.py")
    print("   - simple_memory_store.py")
    print("   - test_memory_storage.py")
    print("   - quick_start_haivemind.py")