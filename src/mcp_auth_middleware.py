#!/usr/bin/env python3
"""
MCP Hub Authentication Middleware
Provides authentication and authorization middleware for MCP requests
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, Callable, Tuple
from functools import wraps
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from mcp_auth_manager import MCPAuthManager, AuthContext

logger = logging.getLogger(__name__)

class MCPAuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for MCP Hub requests"""
    
    def __init__(self, app, auth_manager: MCPAuthManager):
        super().__init__(app)
        self.auth_manager = auth_manager
        
        # Paths that don't require authentication
        self.public_paths = {
            '/health',
            '/docs',
            '/openapi.json',
            '/login',
            '/auth/login',
            '/auth/status'
        }
        
        # Paths that require admin access
        self.admin_paths = {
            '/admin',
            '/api/admin',
            '/auth/users',
            '/auth/api-keys'
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request through authentication middleware"""
        start_time = time.time()
        
        # Skip auth for public paths
        if request.url.path in self.public_paths:
            return await call_next(request)
        
        # Skip auth if disabled
        if not self.auth_manager.enable_auth:
            # Add mock auth context for internal use
            request.state.auth_context = AuthContext(
                user_id='system',
                username='system',
                role='admin',
                permissions={'*'},
                server_access={},
                client_ip=self._get_client_ip(request),
                session_id='system',
                expires_at=None,
                metadata={'auth_disabled': True}
            )
            return await call_next(request)
        
        # Extract authentication credentials
        auth_result = await self._authenticate_request(request)
        
        if not auth_result[0]:  # Authentication failed
            return JSONResponse(
                content={'error': 'Authentication required', 'code': 'AUTH_REQUIRED'},
                status_code=401,
                headers={'WWW-Authenticate': 'Bearer'}
            )
        
        auth_context = auth_result[1]
        request.state.auth_context = auth_context
        
        # Check IP whitelist
        if not await self._check_ip_whitelist(auth_context.client_ip):
            await self.auth_manager._audit_event({
                'timestamp': time.time(),
                'event_type': 'ip_blocked',
                'user_id': auth_context.user_id,
                'client_ip': auth_context.client_ip,
                'success': False,
                'details': {'reason': 'ip_not_whitelisted'}
            })
            return JSONResponse(
                content={'error': 'Access denied from this IP', 'code': 'IP_BLOCKED'},
                status_code=403
            )
        
        # Check admin access for admin paths
        if request.url.path.startswith(tuple(self.admin_paths)):
            if auth_context.role != 'admin' and '*' not in auth_context.permissions:
                return JSONResponse(
                    content={'error': 'Admin access required', 'code': 'ADMIN_REQUIRED'},
                    status_code=403
                )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Log successful request
            processing_time = time.time() - start_time
            await self._log_request(request, auth_context, True, processing_time)
            
            return response
        
        except Exception as e:
            # Log failed request
            processing_time = time.time() - start_time
            await self._log_request(request, auth_context, False, processing_time, str(e))
            raise
    
    async def _authenticate_request(self, request: Request) -> Tuple[bool, Optional[AuthContext]]:
        """Authenticate incoming request"""
        client_ip = self._get_client_ip(request)
        
        # Try Bearer token authentication
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            
            # Try JWT token first
            if token.count('.') == 2:  # JWT format
                return await self._authenticate_jwt(token, client_ip)
            else:
                # Try API key
                return await self.auth_manager.authenticate_api_key(token, client_ip)
        
        # Try API key from query parameter
        api_key = request.query_params.get('api_key')
        if api_key:
            return await self.auth_manager.authenticate_api_key(api_key, client_ip)
        
        # Try session authentication
        session_id = request.cookies.get('session_id')
        if session_id:
            return await self._authenticate_session(session_id, client_ip)
        
        return False, None
    
    async def _authenticate_jwt(self, token: str, client_ip: str) -> Tuple[bool, Optional[AuthContext]]:
        """Authenticate JWT token"""
        try:
            valid, payload = self.auth_manager.validate_jwt_token(token)
            if not valid:
                return False, None
            
            # Create auth context from JWT payload
            auth_context = AuthContext(
                user_id=payload.get('user_id', 'jwt_user'),
                username=payload.get('username', 'jwt_user'),
                role=payload.get('role', 'user'),
                permissions=set(payload.get('permissions', [])),
                server_access=payload.get('server_access', {}),
                client_ip=client_ip,
                session_id=payload.get('jti', token[:16]),
                expires_at=payload.get('exp'),
                metadata={'auth_method': 'jwt'}
            )
            
            return True, auth_context
        
        except Exception as e:
            logger.error(f"JWT authentication error: {e}")
            return False, None
    
    async def _authenticate_session(self, session_id: str, client_ip: str) -> Tuple[bool, Optional[AuthContext]]:
        """Authenticate session ID"""
        try:
            # Try Redis first
            if self.auth_manager.redis_client:
                session_data = self.auth_manager.redis_client.get(f"session:{session_id}")
                if session_data:
                    data = json.loads(session_data)
                    
                    # Verify IP hasn't changed (security check)
                    if data.get('client_ip') != client_ip:
                        logger.warning(f"Session IP mismatch: {data.get('client_ip')} vs {client_ip}")
                        return False, None
                    
                    auth_context = AuthContext(
                        user_id=data['user_id'],
                        username=data['username'],
                        role=data['role'],
                        permissions=set(data['permissions']),
                        server_access={k: set(v) for k, v in data['server_access'].items()},
                        client_ip=client_ip,
                        session_id=session_id,
                        expires_at=data['expires_at'],
                        metadata=data.get('metadata', {})
                    )
                    
                    return True, auth_context
            
            # Fall back to memory sessions
            if session_id in self.auth_manager.active_sessions:
                auth_context = self.auth_manager.active_sessions[session_id]
                if auth_context.client_ip == client_ip:
                    return True, auth_context
            
            return False, None
        
        except Exception as e:
            logger.error(f"Session authentication error: {e}")
            return False, None
    
    async def _check_ip_whitelist(self, client_ip: str) -> bool:
        """Check if client IP is whitelisted"""
        return self.auth_manager.check_ip_whitelist(client_ip)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check X-Forwarded-For header first (for proxies)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else 'unknown'
    
    async def _log_request(self, request: Request, auth_context: AuthContext, 
                          success: bool, processing_time: float, error: str = None):
        """Log request for audit purposes"""
        try:
            details = {
                'method': request.method,
                'path': request.url.path,
                'processing_time_ms': processing_time * 1000,
                'user_agent': request.headers.get('User-Agent', 'unknown')
            }
            
            if error:
                details['error'] = error
            
            await self.auth_manager._audit_event({
                'timestamp': time.time(),
                'event_type': 'http_request',
                'user_id': auth_context.user_id,
                'client_ip': auth_context.client_ip,
                'success': success,
                'details': details,
                'risk_level': 'low' if success else 'medium'
            })
        
        except Exception as e:
            logger.error(f"Request logging error: {e}")


def require_auth(auth_manager: MCPAuthManager):
    """Decorator to require authentication for MCP tool functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract auth context from the current request context
            # This would need to be adapted based on how MCP tools receive context
            auth_context = getattr(wrapper, '_auth_context', None)
            
            if not auth_context and auth_manager.enable_auth:
                raise Exception("Authentication required")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_role(required_role: str, auth_manager: MCPAuthManager):
    """Decorator to require specific role for MCP tool functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            auth_context = getattr(wrapper, '_auth_context', None)
            
            if auth_manager.enable_auth:
                if not auth_context:
                    raise Exception("Authentication required")
                
                if auth_context.role != required_role and auth_context.role != 'admin':
                    raise Exception(f"Role '{required_role}' required")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_permission(required_permission: str, auth_manager: MCPAuthManager):
    """Decorator to require specific permission for MCP tool functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            auth_context = getattr(wrapper, '_auth_context', None)
            
            if auth_manager.enable_auth:
                if not auth_context:
                    raise Exception("Authentication required")
                
                if (required_permission not in auth_context.permissions and 
                    '*' not in auth_context.permissions):
                    raise Exception(f"Permission '{required_permission}' required")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class MCPToolAuthWrapper:
    """Wrapper to add authentication to MCP tool calls"""
    
    def __init__(self, auth_manager: MCPAuthManager):
        self.auth_manager = auth_manager
    
    async def authenticate_tool_call(self, server_id: str, tool_name: str, 
                                   arguments: Dict[str, Any], auth_context: AuthContext) -> Tuple[bool, str]:
        """Authenticate and authorize a tool call"""
        try:
            # Check server access
            if not await self.auth_manager.check_server_access(auth_context, server_id):
                return False, f"Access denied to server '{server_id}'"
            
            # Check tool permission
            if not await self.auth_manager.check_tool_permission(auth_context, server_id, tool_name):
                return False, f"Permission denied for tool '{tool_name}' on server '{server_id}'"
            
            # Check rate limiting
            if not await self.auth_manager.check_rate_limit(auth_context, server_id):
                return False, f"Rate limit exceeded for server '{server_id}'"
            
            return True, "Authorized"
        
        except Exception as e:
            logger.error(f"Tool call authentication error: {e}")
            return False, f"Authentication error: {str(e)}"
    
    async def audit_tool_call(self, server_id: str, tool_name: str, arguments: Dict[str, Any],
                            auth_context: AuthContext, success: bool, execution_time: float,
                            error: str = None):
        """Audit tool call execution"""
        await self.auth_manager.audit_tool_execution(
            auth_context, server_id, tool_name, arguments, 
            success, execution_time, error
        )