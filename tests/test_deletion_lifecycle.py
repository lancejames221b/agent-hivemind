#!/usr/bin/env python3
"""
Test script for memory deletion and lifecycle management functionality
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from memory_server import MemoryStorage

async def test_deletion_lifecycle():
    """Test memory deletion and lifecycle management features"""
    
    # Initialize memory storage
    with open('config/config.json', 'r') as f:
        config = json.load(f)
    
    storage = MemoryStorage(config)
    print("✅ Memory storage initialized")
    
    # Test 1: Store a test memory
    print("\n=== Test 1: Store test memories ===")
    memory_id_1 = await storage.store_memory(
        content="This is a test memory for deletion",
        category="global",
        context="deletion_test",
        user_id="test_user",
        tags=["test", "deletion"]
    )
    print(f"Stored memory 1: {memory_id_1}")
    
    memory_id_2 = await storage.store_memory(
        content="This is another test memory",
        category="global", 
        context="deletion_test",
        user_id="test_user",
        tags=["test", "lifecycle"]
    )
    print(f"Stored memory 2: {memory_id_2}")
    
    # Test 2: Soft delete a memory
    print("\n=== Test 2: Soft delete memory ===")
    delete_result = await storage.delete_memory(
        memory_id_1,
        hard_delete=False,
        reason="Testing soft deletion"
    )
    print(f"Soft delete result: {json.dumps(delete_result, indent=2)}")
    
    # Test 3: Try to retrieve deleted memory (should return None)
    print("\n=== Test 3: Try to retrieve soft deleted memory ===")
    retrieved = await storage.retrieve_memory(memory_id_1)
    print(f"Retrieved deleted memory: {retrieved}")
    
    # Test 4: List deleted memories
    print("\n=== Test 4: List deleted memories ===")
    deleted_list = await storage.list_deleted_memories()
    print(f"Deleted memories: {json.dumps(deleted_list, indent=2)}")
    
    # Test 5: Recover deleted memory
    print("\n=== Test 5: Recover deleted memory ===")
    recovery_result = await storage.recover_deleted_memory(memory_id_1)
    print(f"Recovery result: {json.dumps(recovery_result, indent=2)}")
    
    # Test 6: Retrieve recovered memory
    print("\n=== Test 6: Retrieve recovered memory ===")
    recovered = await storage.retrieve_memory(memory_id_1)
    print(f"Recovered memory: {recovered is not None}")
    if recovered:
        print(f"Content: {recovered['content'][:50]}...")
    
    # Test 7: Detect duplicate memories (create a duplicate first)
    print("\n=== Test 7: Create duplicate and detect ===")
    duplicate_id = await storage.store_memory(
        content="This is another test memory",  # Same as memory_id_2
        category="global",
        context="duplicate_test",
        user_id="test_user",
        tags=["test", "duplicate"]
    )
    print(f"Created potential duplicate: {duplicate_id}")
    
    duplicates = await storage.detect_duplicate_memories(threshold=0.8)
    print(f"Duplicate detection: {json.dumps(duplicates, indent=2)}")
    
    # Test 8: GDPR export user data
    print("\n=== Test 8: GDPR export user data ===")
    export_result = await storage.gdpr_export_user_data("test_user", format="json")
    print(f"Export result success: {export_result.get('success', False)}")
    if export_result.get('success'):
        export_data = export_result['export_data']
        print(f"Exported memories count: {export_data['total_active_memories']}")
    
    # Test 9: Bulk delete memories
    print("\n=== Test 9: Bulk delete test memories ===")
    bulk_delete_result = await storage.bulk_delete_memories(
        user_id="test_user",
        tags=["test"],
        hard_delete=True,
        reason="Cleanup test memories",
        confirm=True
    )
    print(f"Bulk delete result: {json.dumps(bulk_delete_result, indent=2)}")
    
    # Test 10: Cleanup expired deletions
    print("\n=== Test 10: Cleanup expired deletions ===")
    cleanup_result = await storage.cleanup_expired_deletions()
    print(f"Cleanup result: {json.dumps(cleanup_result, indent=2)}")
    
    print("\n✅ All deletion and lifecycle tests completed!")

if __name__ == "__main__":
    asyncio.run(test_deletion_lifecycle())