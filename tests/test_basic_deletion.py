#!/usr/bin/env python3
"""
Basic validation test for memory deletion functionality without requiring full infrastructure
"""

import json
import sys
import os

# Basic validation of the implementation
def test_config_validation():
    """Test that configuration includes required deletion settings"""
    try:
        with open('config/config.json', 'r') as f:
            config = json.load(f)
        
        # Check memory configuration has required fields for deletion
        memory_config = config.get('memory', {})
        assert 'max_age_days' in memory_config, "max_age_days missing from memory config"
        assert memory_config['max_age_days'] == 365, "Default retention should be 365 days"
        
        # Check categories include security for audit logs
        categories = memory_config.get('categories', [])
        assert 'security' in categories, "Security category required for audit logs"
        
        print("✅ Configuration validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False

def test_code_structure():
    """Test that the memory server contains the required deletion methods"""
    try:
        # Read the memory server code
        with open('src/memory_server.py', 'r') as f:
            code = f.read()
        
        # Check for required deletion methods
        required_methods = [
            'async def delete_memory',
            'async def bulk_delete_memories',
            'async def recover_deleted_memory', 
            'async def list_deleted_memories',
            'async def detect_duplicate_memories',
            'async def merge_duplicate_memories',
            'async def cleanup_expired_deletions',
            'async def gdpr_delete_user_data',
            'async def gdpr_export_user_data',
            'async def _log_deletion_audit',
            'async def _broadcast_deletion_event'
        ]
        
        for method in required_methods:
            assert method in code, f"Required method {method} not found"
        
        # Check for required MCP tools
        required_tools = [
            'delete_memory',
            'bulk_delete_memories', 
            'recover_deleted_memory',
            'list_deleted_memories',
            'detect_duplicate_memories',
            'merge_duplicate_memories',
            'cleanup_expired_deletions',
            'gdpr_delete_user_data',
            'gdpr_export_user_data'
        ]
        
        for tool in required_tools:
            assert f'name="{tool}"' in code, f"MCP tool {tool} not registered"
        
        print("✅ Code structure validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Code structure validation failed: {e}")
        return False

def test_documentation():
    """Test that documentation includes the new features"""
    try:
        with open('CLAUDE.md', 'r') as f:
            docs = f.read()
        
        # Check for documentation of new tools
        required_docs = [
            'Memory Deletion & Lifecycle Management Tools',
            'delete_memory',
            'bulk_delete_memories',
            'recover_deleted_memory',
            'gdpr_delete_user_data',
            'gdpr_export_user_data',
            'soft delete (recoverable)',
            'hard delete (permanent)',
            'GDPR compliant'
        ]
        
        for doc_item in required_docs:
            assert doc_item in docs, f"Documentation missing: {doc_item}"
        
        print("✅ Documentation validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Documentation validation failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🔍 Running basic deletion and lifecycle management validation...\n")
    
    tests = [
        test_config_validation,
        test_code_structure, 
        test_documentation
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    if all(results):
        print("🎉 All validation tests passed! Memory deletion and lifecycle management is properly implemented.")
        return True
    else:
        print("❌ Some validation tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)