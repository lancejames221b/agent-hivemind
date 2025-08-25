#!/usr/bin/env python3
"""
Test script for WebSocket authentication
Tests the WebSocket endpoint with various authentication scenarios
"""

import asyncio
import websockets
import json
import jwt
import sys
from datetime import datetime, timedelta

# Test configuration
WEBSOCKET_URL = "ws://localhost:8901/admin/ws"
JWT_SECRET = "change-this-secret-key"  # Default secret from dashboard_server.py

def create_test_token(user_id=1, username="admin", role="admin", expired=False):
    """Create a test JWT token"""
    exp_time = datetime.utcnow() - timedelta(hours=1) if expired else datetime.utcnow() + timedelta(hours=24)
    
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': exp_time,
        'iat': datetime.utcnow(),
        'iss': 'haivemind-dashboard'
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

async def test_websocket_connection(token=None, test_name=""):
    """Test WebSocket connection with given token"""
    print(f"\n--- Testing: {test_name} ---")
    
    url = WEBSOCKET_URL
    if token:
        url += f"?token={token}"
    
    try:
        async with websockets.connect(url) as websocket:
            print("✅ WebSocket connection established")
            
            # Send a ping message
            await websocket.send(json.dumps({"type": "ping"}))
            print("📤 Sent ping message")
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)
            print(f"📥 Received: {data}")
            
            # Request stats
            await websocket.send(json.dumps({"type": "get_stats"}))
            print("📤 Requested stats")
            
            # Wait for stats response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)
            print(f"📥 Received: {data.get('type', 'unknown')}")
            
            print("✅ Test passed")
            
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ Connection closed: {e.code} - {e.reason}")
    except asyncio.TimeoutError:
        print("❌ Timeout waiting for response")
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    """Run all WebSocket authentication tests"""
    print("🔧 Testing WebSocket Authentication")
    print("=" * 50)
    
    # Test 1: No token
    await test_websocket_connection(None, "No token provided")
    
    # Test 2: Valid token
    valid_token = create_test_token()
    await test_websocket_connection(valid_token, "Valid token")
    
    # Test 3: Expired token
    expired_token = create_test_token(expired=True)
    await test_websocket_connection(expired_token, "Expired token")
    
    # Test 4: Invalid token
    invalid_token = "invalid.token.here"
    await test_websocket_connection(invalid_token, "Invalid token")
    
    # Test 5: Valid token with different user
    user_token = create_test_token(user_id=2, username="testuser", role="viewer")
    await test_websocket_connection(user_token, "Valid token - different user")
    
    print("\n" + "=" * 50)
    print("🏁 WebSocket authentication tests completed")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage: python test_websocket_auth.py")
        print("This script tests WebSocket authentication with various scenarios.")
        print("Make sure the dashboard server is running on localhost:8901")
        sys.exit(0)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        sys.exit(1)