#!/usr/bin/env python3
"""
Test script to store memory using the hAIveMind system
"""
import requests
import json
import sys

def store_memory_via_http():
    """Store memory via HTTP request to hAIveMind remote server"""
    
    # Memory content to store
    memory_data = {
        "content": "hAIveMind MCP client is now working perfectly with cursor-agent",
        "category": "infrastructure", 
        "project": "memory-mcp",
        "tags": ["haivemind", "mcp", "cursor-agent", "success", "integration"],
        "scope": "project-shared"
    }
    
    # MCP JSON-RPC payload
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "store_memory",
            "arguments": memory_data
        },
        "id": 1
    }
    
    try:
        # Try to connect to hAIveMind remote server
        response = requests.post(
            "http://localhost:8900/mcp",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if "error" in result:
                print(f"❌ Error from hAIveMind: {result['error']}")
                return False
            else:
                print("✅ Memory stored successfully via HTTP!")
                print(f"Result: {json.dumps(result.get('result', {}), indent=2)}")
                return True
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to hAIveMind server at http://localhost:8900")
        print("   Make sure the hAIveMind remote server is running:")
        print("   python src/remote_mcp_server.py")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main function"""
    print("🧠 Testing hAIveMind Memory Storage")
    print("=" * 40)
    
    success = store_memory_via_http()
    
    if success:
        print("\n🎉 Memory storage test completed successfully!")
        print("The message 'hAIveMind MCP client is now working perfectly with cursor-agent' has been stored.")
    else:
        print("\n💥 Memory storage test failed.")
        print("Please ensure hAIveMind services are running.")
        sys.exit(1)

if __name__ == "__main__":
    main()