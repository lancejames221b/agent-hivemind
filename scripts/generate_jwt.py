#!/usr/bin/env python3
"""
Generate JWT tokens for hAIveMind MCP access
"""
import jwt
import os
import sys
from datetime import datetime, timedelta

def generate_token(secret, payload=None, expires_hours=24*30):  # 30 days default
    if not payload:
        payload = {
            'sub': 'claude-code-mcp',
            'iss': 'haivemind',
            'aud': 'mcp-client',
            'agent_id': 'claude-code',
            'machine_id': 'lance-dev',
            'scope': 'mcp:read mcp:write'
        }
    
    payload['exp'] = datetime.utcnow() + timedelta(hours=expires_hours)
    payload['iat'] = datetime.utcnow()
    
    return jwt.encode(payload, secret, algorithm='HS256')

if __name__ == '__main__':
    secret = os.environ.get('HAIVEMIND_JWT_SECRET')
    if not secret:
        print("Error: HAIVEMIND_JWT_SECRET not set")
        sys.exit(1)
    
    token = generate_token(secret)
    print(f"JWT Token: {token}")
    print(f"\nAdd this to your MCP configuration:")
    print(f'Authorization: Bearer {token}')