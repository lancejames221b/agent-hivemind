#!/usr/bin/env python3
"""
Comprehensive Playbook Storage Testing Script
Tests all 6 playbook storage MCP tools with correct method names

Author: Lance James, Unit 221B, Inc
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playbook_storage_manager import PlaybookStorageManager

# Test configuration
TEST_DB_PATH = "data/test_playbooks.db"
TEST_CHROMA_PATH = "data/test_chroma"
REDIS_HOST = "localhost"
REDIS_PORT = 6379


async def setup_test_environment():
    """Set up test environment"""
    print("Setting up test environment...")

    # Create test data directory
    Path("data").mkdir(exist_ok=True)

    # Remove old test database if exists
    if Path(TEST_DB_PATH).exists():
        Path(TEST_DB_PATH).unlink()
        print(f"✅ Removed old test database")

    # Remove old ChromaDB data
    import shutil
    if Path(TEST_CHROMA_PATH).exists():
        shutil.rmtree(TEST_CHROMA_PATH)
        print(f"✅ Removed old ChromaDB data")

    # Initialize PlaybookStorageManager
    manager = PlaybookStorageManager(
        db_path=TEST_DB_PATH,
        chroma_path=TEST_CHROMA_PATH,
        redis_host=REDIS_HOST,
        redis_port=REDIS_PORT,
        redis_db=1,  # Use test DB
        redis_password=None,
        embedding_model="all-MiniLM-L6-v2"
    )

    print("✅ Test environment ready\n")
    return manager


async def test_store_playbook(manager):
    """Test 1.1: store_playbook_with_labels - Basic storage"""
    print("=" * 60)
    print("TEST 1.1: store_playbook_with_labels - Basic storage")
    print("=" * 60)

    playbook_content = {
        "name": "Deploy Nginx",
        "hosts": "web_servers",
        "tasks": [
            {"name": "Install nginx", "apt": {"name": "nginx", "state": "present"}},
            {"name": "Start nginx", "service": {"name": "nginx", "state": "started"}}
        ]
    }

    try:
        result = await manager.store_playbook(
            name="Deploy Nginx to Web Servers",
            content=playbook_content,
            category="deployment",
            labels=["nginx", "web", "production"],
            format_type="ansible"
        )

        print(f"✅ Stored playbook successfully")
        print(f"   Playbook ID: {result['playbook_id']}")
        print(f"   Slug: {result['slug']}")
        print(f"   Labels: {len(result.get('labels', []))}")
        print()

        return result['playbook_id']

    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        raise


async def test_search_playbooks_semantic(manager):
    """Test 1.2: search_playbooks - Semantic search"""
    print("=" * 60)
    print("TEST 1.2: search_playbooks - Semantic search")
    print("=" * 60)

    # Add more playbooks for better search testing
    playbooks_to_add = [
        {
            "name": "Elasticsearch Cluster Setup",
            "content": {"tasks": [{"name": "Install elasticsearch cluster"}]},
            "category": "elasticsearch",
            "labels": ["elasticsearch", "cluster", "database"]
        },
        {
            "name": "MySQL Backup Procedure",
            "content": {"tasks": [{"name": "Backup MySQL databases"}]},
            "category": "database",
            "labels": ["mysql", "backup", "database"]
        },
        {
            "name": "Redis Cache Configuration",
            "content": {"tasks": [{"name": "Configure Redis caching"}]},
            "category": "database",
            "labels": ["redis", "cache", "performance"]
        }
    ]

    # Add test playbooks
    for pb in playbooks_to_add:
        await manager.store_playbook(
            name=pb["name"],
            content=pb["content"],
            category=pb["category"],
            labels=pb["labels"],
            format_type="ansible"
        )

    print("Added 3 additional playbooks for search testing\n")

    # Test semantic search
    queries = [
        ("database cluster setup", "Should find Elasticsearch cluster"),
        ("backup database", "Should find MySQL backup"),
        ("web server deployment", "Should find Nginx deploy")
    ]

    for query, expected in queries:
        try:
            result = await manager.search_playbooks(
                query=query,
                semantic_search=True,
                similarity_threshold=0.5,
                limit=3
            )

            # Handle both dict and list return types
            playbooks = result if isinstance(result, list) else result.get('playbooks', [])
            print(f"Query: '{query}'")
            print(f"Expected: {expected}")
            print(f"Found {len(playbooks)} playbooks:")
            for p in playbooks[:3]:
                score = p.get('similarity_score', 'N/A')
                print(f"  - {p['name']} (score: {score})")
            print()

        except Exception as e:
            print(f"❌ FAILED for query '{query}': {e}\n")
            raise


async def test_search_playbooks_labels(manager):
    """Test 1.3: search_playbooks - Label filtering (AND/OR logic)"""
    print("=" * 60)
    print("TEST 1.3: search_playbooks - Label filtering")
    print("=" * 60)

    # Test AND logic (must match all labels)
    try:
        result = await manager.search_playbooks(
            labels=["database", "backup"],
            match_all_labels=True,  # AND logic
            limit=10
        )

        playbooks = result if isinstance(result, list) else result.get('playbooks', [])
        print(f"AND Search: labels=['database', 'backup']")
        print(f"Found {len(playbooks)} playbooks (should find MySQL Backup):")
        for p in playbooks:
            print(f"  - {p['name']}: labels={p.get('labels', [])}")
        print()

    except Exception as e:
        print(f"❌ FAILED AND search: {e}\n")
        raise

    # Test OR logic (match any label)
    try:
        result = await manager.search_playbooks(
            labels=["redis", "nginx"],
            match_all_labels=False,  # OR logic
            limit=10
        )

        playbooks = result if isinstance(result, list) else result.get('playbooks', [])
        print(f"OR Search: labels=['redis', 'nginx']")
        print(f"Found {len(playbooks)} playbooks (should find Redis and Nginx):")
        for p in playbooks:
            print(f"  - {p['name']}: labels={p.get('labels', [])}")
        print()

    except Exception as e:
        print(f"❌ FAILED OR search: {e}\n")
        raise


async def test_get_playbook(manager, playbook_id):
    """Test 1.4: get_playbook - Retrieve by multiple identifiers"""
    print("=" * 60)
    print("TEST 1.4: get_playbook - Retrieve by ID/slug")
    print("=" * 60)

    # Test retrieval by ID
    try:
        result = await manager.get_playbook(playbook_id=playbook_id)
        print(f"✅ Retrieved by ID: {playbook_id}")
        print(f"   Name: {result['name']}")
        print(f"   Category: {result['category']}")
        print(f"   Labels: {len(result.get('labels', []))} labels")
        print()

    except Exception as e:
        print(f"❌ FAILED retrieval by ID: {e}\n")
        raise

    # Test retrieval by slug
    try:
        result = await manager.get_playbook(slug="deploy-nginx-to-web-servers")
        print(f"✅ Retrieved by slug: deploy-nginx-to-web-servers")
        print(f"   Playbook ID: {result['id']}")
        print()

    except Exception as e:
        print(f"❌ FAILED retrieval by slug: {e}\n")
        raise


async def test_label_management(manager, playbook_id):
    """Test 1.5: add_labels & remove_labels"""
    print("=" * 60)
    print("TEST 1.5: Label management (add/remove)")
    print("=" * 60)

    # Add labels
    try:
        result = await manager.add_playbook_labels(
            playbook_id=playbook_id,
            labels=["verified", "critical", "team:devops"]
        )

        print(f"✅ Added labels successfully")
        print(f"   Labels added: {result.get('added_labels', [])}")
        print()

    except Exception as e:
        print(f"❌ FAILED adding labels: {e}\n")
        raise

    # Verify labels were added
    playbook = await manager.get_playbook(playbook_id=playbook_id)
    print(f"Current labels: {playbook.get('labels', [])}\n")

    # Remove labels
    try:
        result = await manager.remove_playbook_labels(
            playbook_id=playbook_id,
            labels=["team:devops"]
        )

        print(f"✅ Removed labels successfully")
        print(f"   Labels removed: {result.get('removed_labels', [])}")
        print()

    except Exception as e:
        print(f"❌ FAILED removing labels: {e}\n")
        raise


async def test_list_playbook_labels(manager):
    """Test 1.6: list_all_labels - Statistics"""
    print("=" * 60)
    print("TEST 1.6: list_all_labels - Label statistics")
    print("=" * 60)

    try:
        result = await manager.list_playbook_labels(
            category="deployment"
        )

        print(f"✅ Retrieved label statistics")
        if isinstance(result, list):
            print(f"   Total labels found: {len(result)}")
            print(f"   Label usage:")
            for label in result[:10]:  # Show top 10
                label_str = label.get('label', 'unknown')
                count = label.get('usage_count', 0)
                print(f"     - {label_str}: {count} playbooks")
        else:
            print(f"   Total labels found: {result.get('count', 0)}")
            print(f"   Label usage:")
            for label in result.get('labels', [])[:10]:  # Show top 10
                name = label.get('name', 'unknown')
                count = label.get('usage_count', 0)
                print(f"     - {name}: {count} playbooks")
        print()

    except Exception as e:
        print(f"❌ FAILED listing labels: {e}\n")
        raise


async def test_caching(manager, playbook_id):
    """Test caching performance"""
    print("=" * 60)
    print("TEST: Redis caching performance")
    print("=" * 60)

    import time

    # First retrieval (not cached)
    start = time.time()
    await manager.get_playbook(playbook_id=playbook_id)
    first_time = time.time() - start

    # Second retrieval (should be cached)
    start = time.time()
    await manager.get_playbook(playbook_id=playbook_id)
    cached_time = time.time() - start

    speedup = first_time / cached_time if cached_time > 0 else 0
    print(f"First retrieval: {first_time*1000:.2f}ms")
    print(f"Cached retrieval: {cached_time*1000:.2f}ms")
    print(f"Speedup: {speedup:.1f}x faster\n")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("PLAYBOOK STORAGE COMPREHENSIVE TEST SUITE")
    print("=" * 60 + "\n")

    manager = None

    try:
        # Setup
        manager = await setup_test_environment()

        # Run tests in sequence
        playbook_id = await test_store_playbook(manager)
        await test_search_playbooks_semantic(manager)
        await test_search_playbooks_labels(manager)
        await test_get_playbook(manager, playbook_id)
        await test_label_management(manager, playbook_id)
        await test_list_playbook_labels(manager)
        await test_caching(manager, playbook_id)

        print("=" * 60)
        print("✅ ALL TESTS PASSED (6/6)")
        print("=" * 60 + "\n")

        return 0

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST SUITE FAILED: {e}")
        print("=" * 60 + "\n")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Cleanup
        if manager and hasattr(manager, 'redis_client') and manager.redis_client:
            try:
                await manager.redis_client.aclose()
            except:
                pass


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
