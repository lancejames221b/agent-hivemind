#!/usr/bin/env python3
"""
Simple script to store a memory in the hAIveMind system
"""
import sys
import os
import asyncio
import json
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from memory_store import MemoryStore
except ImportError as e:
    print(f"Error importing MemoryStore: {e}")
    sys.exit(1)

async def main():
    """Store the memory about hAIveMind MCP client working with cursor-agent"""
    try:
        # Initialize memory store
        store = MemoryStore()
        await store.initialize()
        
        # Memory data
        memory_data = {
            'content': 'hAIveMind MCP client is now working perfectly with cursor-agent',
            'category': 'infrastructure',
            'project': 'memory-mcp',
            'tags': ['haivemind', 'mcp', 'cursor-agent', 'success', 'integration'],
            'scope': 'project-shared',
            'machine_id': 'lance-dev',
            'user_id': 'lj'
        }
        
        # Store the memory
        result = await store.store_memory(**memory_data)
        
        print("✅ Memory stored successfully!")
        print(f"Memory ID: {result.get('memory_id', 'Unknown')}")
        print(f"Content: {memory_data['content']}")
        print(f"Category: {memory_data['category']}")
        print(f"Project: {memory_data['project']}")
        print(f"Tags: {', '.join(memory_data['tags'])}")
        print(f"Scope: {memory_data['scope']}")
        
        # Close the store
        await store.close()
        
    except Exception as e:
        print(f"❌ Error storing memory: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())