#!/usr/bin/env python3
"""
ClaudeOps hAIveMind Authentication & Security Module
Provides JWT tokens, API key validation, and access control
"""

import json
import jwt
import time
import secrets
import hashlib
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class AuthManager:
    """Manages authentication and authorization for hAIveMind servers"""
    
    def __init__(self, config: Dict):
        self.config = config.get('security', {})
        self.enable_auth = self.config.get('enable_auth', True)
        self.jwt_secret = self.config.get('jwt_secret', 'insecure-default-key')
        
        # Default admin credentials
        self.admin_username = "admin"
        self.admin_password = "Unit221B"
        
        # API token configuration
        self.api_tokens = self.config.get('api_tokens', {})
        self.admin_token = self.api_tokens.get('admin_token')
        self.readonly_token = self.api_tokens.get('read_only_token') 
        self.agent_token = self.api_tokens.get('agent_token')
        
        # Access control
        self.allowed_origins = self.config.get('allowed_origins', ['localhost'])
        self.ip_whitelist = self.config.get('ip_whitelist', ['127.0.0.1'])
        
        # Rate limiting
        self.rate_limit_config = self.config.get('rate_limiting', {})
        self.rate_limits = {}  # IP -> (count, last_reset)
        
        logger.info(f"🔐 hAIveMind security initialized - auth {'enabled' if self.enable_auth else 'disabled'}")
    
    def validate_admin_login(self, username: str, password: str) -> bool:
        """Validate admin login credentials"""
        return username == self.admin_username and password == self.admin_password
    
    def generate_secure_tokens(self) -> Dict[str, str]:
        """Generate secure API tokens for initial setup"""
        return {
            'admin_token': f"haiv_admin_{secrets.token_urlsafe(32)}",
            'readonly_token': f"haiv_readonly_{secrets.token_urlsafe(32)}", 
            'agent_token': f"haiv_agent_{secrets.token_urlsafe(32)}",
            'jwt_secret': secrets.token_urlsafe(64)
        }
    
    def validate_api_token(self, token: str) -> Tuple[bool, str]:
        """Validate API token and return (valid, role)"""
        if not self.enable_auth:
            return True, 'admin'
            
        if not token:
            return False, 'none'
            
        # Check token types
        if token == self.admin_token:
            return True, 'admin'
        elif token == self.readonly_token:
            return True, 'readonly'
        elif token == self.agent_token:
            return True, 'agent'
        
        return False, 'none'
    
    def generate_jwt_token(self, payload: Dict, expires_hours: int = 24) -> str:
        """Generate JWT token with expiration"""
        payload.update({
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=expires_hours),
            'iss': 'haivemind-auth'
        })
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def validate_jwt_token(self, token: str) -> Tuple[bool, Dict]:
        """Validate JWT token and return (valid, payload)"""
        if not self.enable_auth:
            return True, {'role': 'admin'}
            
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return True, payload
        except jwt.ExpiredSignatureError:
            logger.warning("🔐 JWT token expired")
            return False, {}
        except jwt.InvalidTokenError as e:
            logger.warning(f"🔐 Invalid JWT token: {e}")
            return False, {}
    
    def check_ip_whitelist(self, client_ip: str) -> bool:
        """Check if client IP is in whitelist"""
        if not self.enable_auth:
            return True
            
        try:
            client_addr = ipaddress.ip_address(client_ip)
            
            for allowed_range in self.ip_whitelist:
                if '/' in allowed_range:
                    # CIDR notation
                    if client_addr in ipaddress.ip_network(allowed_range):
                        return True
                else:
                    # Single IP
                    if client_addr == ipaddress.ip_address(allowed_range):
                        return True
            
            logger.warning(f"🔐 IP {client_ip} not in whitelist")
            return False
            
        except Exception as e:
            logger.error(f"🔐 IP validation error: {e}")
            return False
    
    def check_rate_limit(self, client_ip: str) -> bool:
        """Check rate limiting for client IP"""
        if not self.rate_limit_config.get('enabled', False):
            return True
            
        current_time = time.time()
        rpm_limit = self.rate_limit_config.get('requests_per_minute', 60)
        
        if client_ip not in self.rate_limits:
            self.rate_limits[client_ip] = [1, current_time]
            return True
        
        count, last_reset = self.rate_limits[client_ip]
        
        # Reset counter every minute
        if current_time - last_reset > 60:
            self.rate_limits[client_ip] = [1, current_time]
            return True
        
        # Check if over limit
        if count >= rpm_limit:
            logger.warning(f"🔐 Rate limit exceeded for {client_ip}")
            return False
        
        # Increment counter
        self.rate_limits[client_ip][0] += 1
        return True