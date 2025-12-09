#!/usr/bin/env python3
"""Test memory storage functionality"""

import sys
import json
import asyncio
from memory_server import MemoryStorage

async def test_memory_storage():
    """Test storing and retrieving memories"""

    # Load config
    with open('../config/config.json') as f:
        config = json.load(f)

    # Initialize storage
    storage = MemoryStorage(config)
    print('✅ MemoryStorage initialized successfully')
    print(f'   Machine ID: {storage.machine_id}')
    print(f'   Collections: {len(storage.collections)}')
    print()

    # Test storing a memory
    print('📝 Testing memory storage...')
    result = await storage.store_memory(
        content='Test memory: hAIveMind server successfully started on lance-dev',
        category='infrastructure',
        tags=['test', 'haivemind', 'server', 'success'],
        context='Testing memory storage after successful server startup'
    )
    print(f'✅ Memory stored successfully!')
    print(f'   Memory ID: {result["memory_id"]}')
    print(f'   Category: {result["category"]}')
    print(f'   Machine: {result["machine_id"]}')
    print(f'   Tags: {result["tags"]}')
    print()

    # Test retrieving the memory
    print('🔍 Testing memory retrieval...')
    retrieved = storage.get_memory(result["memory_id"])
    if retrieved:
        print(f'✅ Memory retrieved successfully!')
        print(f'   Content: {retrieved["content"][:80]}...')
        print(f'   Category: {retrieved["category"]}')
    else:
        print(f'❌ Failed to retrieve memory')
        return False

    return True

if __name__ == '__main__':
    success = asyncio.run(test_memory_storage())
    sys.exit(0 if success else 1)
