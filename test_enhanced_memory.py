#!/usr/bin/env python3
"""Test script for enhanced memory system with machine tracking and sharing"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from memory_server import MemoryStorage

async def test_enhanced_memory():
    # Load config
    config_path = Path(__file__).parent / "config" / "config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    # Initialize storage
    storage = MemoryStorage(config)
    
    print("=== Testing Enhanced Memory System ===\n")
    
    # Test 1: Get machine context
    print("1. Getting machine context...")
    context = await storage.get_machine_context()
    print(f"Machine ID: {context['system']['machine_id']}")
    print(f"Hostname: {context['system']['hostname']}")
    print(f"Environment: {context['system']['environment']}")
    print(f"Member of groups: {context['member_of_groups']}")
    print()
    
    # Test 2: Store memory with enhanced tracking
    print("2. Storing memory with enhanced tracking...")
    memory_id = await storage.store_memory(
        content="Test memory with enhanced machine tracking and sharing control",
        category="project",
        context="Testing enhanced system",
        scope="project-shared",
        tags=["test", "enhanced", "machine-tracking"],
        sensitive=False
    )
    print(f"Stored memory ID: {memory_id}")
    print()
    
    # Test 3: Store sensitive memory
    print("3. Storing sensitive memory (machine-local)...")
    sensitive_id = await storage.store_memory(
        content="Sensitive test data that should stay on this machine only",
        category="project", 
        context="Testing sensitive data",
        scope="machine-local",
        sensitive=True,
        tags=["test", "sensitive"]
    )
    print(f"Stored sensitive memory ID: {sensitive_id}")
    print()
    
    # Test 4: Search memories
    print("4. Searching memories...")
    results = await storage.search_memories(
        query="enhanced tracking",
        limit=5
    )
    print(f"Found {len(results)} memories:")
    for result in results:
        metadata = result.get('metadata', {})
        print(f"  - {result['id'][:8]}... from {metadata.get('machine_id', 'unknown')}")
        print(f"    Scope: {metadata.get('scope', 'unknown')}")
        print(f"    Environment: {metadata.get('environment', 'unknown')}")
        print()
    
    # Test 5: List memory sources
    print("5. Listing memory sources...")
    sources = await storage.list_memory_sources()
    print(f"Total machines: {sources['total_machines']}")
    print(f"Current machine: {sources['current_machine']}")
    for machine in sources['machines']:
        print(f"  - {machine['machine_id']} ({machine['hostname']})")
        print(f"    Total memories: {machine['total_memories']}")
        print(f"    Environment: {machine['environment']}")
        print()

if __name__ == "__main__":
    asyncio.run(test_enhanced_memory())