#!/usr/bin/env python3
"""
Store the success message about hAIveMind MCP client working with cursor-agent
"""
import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from memory_server import MemoryStorage
except ImportError as e:
    print(f"❌ Error importing MemoryStorage: {e}")
    print("Make sure you're running this from the memory-mcp directory")
    sys.exit(1)

async def store_success_memory():
    """Store the memory about hAIveMind MCP client success"""
    
    # Load config
    config_path = Path(__file__).parent / "config" / "config.json"
    try:
        with open(config_path) as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        sys.exit(1)
    
    # Initialize storage
    try:
        storage = MemoryStorage(config)
        print("✅ MemoryStorage initialized successfully")
        print(f"   Machine ID: {storage.machine_id}")
        print(f"   Agent ID: {storage.agent_id}")
    except Exception as e:
        print(f"❌ Failed to initialize MemoryStorage: {e}")
        print("This might be due to missing dependencies or Redis not running.")
        print("The memory will still be stored in ChromaDB even if Redis is unavailable.")
        try:
            # Try to initialize without Redis
            config['storage']['redis']['enable_cache'] = False
            storage = MemoryStorage(config)
            print("✅ MemoryStorage initialized successfully (without Redis)")
            print(f"   Machine ID: {storage.machine_id}")
            print(f"   Agent ID: {storage.agent_id}")
        except Exception as e2:
            print(f"❌ Failed to initialize even without Redis: {e2}")
            sys.exit(1)
    
    print("\n🧠 Storing hAIveMind MCP Client Success Memory")
    print("=" * 50)
    
    try:
        # Store the memory
        memory_id = await storage.store_memory(
            content="hAIveMind MCP client is now working perfectly with cursor-agent",
            category="infrastructure",
            context="MCP integration success - cursor-agent can now access hAIveMind memory system",
            project="memory-mcp",
            tags=["haivemind", "mcp", "cursor-agent", "success", "integration", "working"],
            scope="project-shared",
            sensitive=False
        )
        
        print(f"✅ Memory stored successfully!")
        print(f"   Memory ID: {memory_id}")
        print(f"   Content: hAIveMind MCP client is now working perfectly with cursor-agent")
        print(f"   Category: infrastructure")
        print(f"   Project: memory-mcp")
        print(f"   Tags: haivemind, mcp, cursor-agent, success, integration, working")
        print(f"   Scope: project-shared")
        
        # Get machine context to show where it was stored
        context = await storage.get_machine_context()
        print(f"\n📍 Stored on machine: {context['system']['machine_id']}")
        print(f"   Hostname: {context['system']['hostname']}")
        print(f"   Environment: {context['system']['environment']}")
        
        # Try to retrieve the memory to verify it was stored
        print(f"\n🔍 Verifying memory was stored...")
        retrieved = await storage.retrieve_memory(memory_id)
        if retrieved:
            print(f"✅ Memory verification successful!")
            print(f"   Retrieved content: {retrieved.get('content', 'N/A')[:80]}...")
        else:
            print(f"⚠️  Could not retrieve memory for verification")
        
    except Exception as e:
        print(f"❌ Error storing memory: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print(f"\n🎉 hAIveMind memory storage completed successfully!")
    print(f"The success message has been stored in the hAIveMind collective memory.")

if __name__ == "__main__":
    asyncio.run(store_success_memory())