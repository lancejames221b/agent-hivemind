#!/usr/bin/env python3
"""
Test script to verify hAIveMind setup is ready for Claude Code integration
"""

import sys
import os
sys.path.append('/home/lj/memory-mcp/src')

def test_imports():
    """Test that all required modules can be imported"""
    try:
        import redis
        import chromadb
        from mcp.server import Server
        from memory_server import MemoryStorage, MemoryMCPServer
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config():
    """Test that configuration file is accessible"""
    config_path = "/home/lj/memory-mcp/config/config.json"
    if os.path.exists(config_path):
        print("✅ Configuration file found")
        return True
    else:
        print("❌ Configuration file not found")
        return False

def test_redis():
    """Test Redis connection"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def test_chromadb():
    """Test ChromaDB initialization"""
    try:
        import chromadb
        from pathlib import Path
        
        chroma_path = Path("/home/lj/memory-mcp/data/chroma")
        chroma_path.mkdir(parents=True, exist_ok=True)
        
        client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=chromadb.Settings(anonymized_telemetry=False)
        )
        collections = client.list_collections()
        print(f"✅ ChromaDB connection successful ({len(collections)} collections)")
        return True
    except Exception as e:
        print(f"❌ ChromaDB connection failed: {e}")
        return False

def main():
    print("🧠 Testing hAIveMind setup for Claude Code integration...\n")
    
    tests = [
        ("Module imports", test_imports),
        ("Configuration", test_config), 
        ("Redis connection", test_redis),
        ("ChromaDB connection", test_chromadb)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"Testing {name}...")
        result = test_func()
        results.append(result)
        print()
    
    if all(results):
        print("🚀 hAIveMind is ready for Claude Code integration!")
        print("📝 To activate, restart Claude Code and the MCP server will auto-connect")
        print("🧠 Available tools: store_memory, search_memories, register_agent, delegate_task, and more!")
    else:
        print("⚠️  Some tests failed. Please fix issues before using with Claude Code.")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)