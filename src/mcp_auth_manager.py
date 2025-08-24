#!/usr/bin/env python3
"""
MCP Hub Authentication and Access Control Manager
Enterprise-grade security layer for MCP server hub with per-server auth,
role-based access control, tool-level permissions, and audit logging.
"""

import asyncio
import json
import jwt
import time
import secrets
import hashlib
import ipaddress
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
import redis
from functools import wraps
import bcrypt

logger = logging.getLogger(__name__)

@dataclass
class AuthContext:
    """Authentication context for requests"""
    user_id: str
    username: str
    role: str
    permissions: Set[str]
    server_access: Dict[str, Set[str]]  # server_id -> set of allowed tools
    client_ip: str
    session_id: str
    expires_at: datetime
    metadata: Dict[str, Any]

@dataclass
class ServerAuthConfig:
    """Per-server authentication configuration"""
    server_id: str
    auth_required: bool = True
    allowed_roles: Set[str] = None
    allowed_users: Set[str] = None
    tool_permissions: Dict[str, Set[str]] = None  # tool_name -> allowed_roles
    rate_limits: Dict[str, int] = None  # role -> requests_per_minute
    audit_level: str = "standard"  # minimal, standard, detailed

@dataclass
class AuditEvent:
    """Audit event for logging"""
    timestamp: datetime
    event_type: str
    user_id: str
    server_id: Optional[str]
    tool_name: Optional[str]
    client_ip: str
    success: bool
    details: Dict[str, Any]
    risk_level: str = "low"

class MCPAuthManager:
    """Enhanced authentication and access control manager for MCP Hub"""
    
    def __init__(self, config: Dict[str, Any], memory_storage=None):
        self.config = config.get('security', {})
        self.memory_storage = memory_storage
        
        # Core authentication settings
        self.enable_auth = self.config.get('enable_auth', True)
        self.jwt_secret = self._resolve_jwt_secret()
        self.session_timeout = self.config.get('session_timeout_hours', 24)
        
        # Database for auth data
        self.db_path = Path(config.get('storage', {}).get('auth_db', 'data/auth.db'))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Redis for session management and rate limiting
        self.redis_client = None
        if config.get('storage', {}).get('redis', {}).get('enable_cache'):
            self._init_redis(config['storage']['redis'])
        
        # Rate limiting configuration
        self.rate_limits = self.config.get('rate_limiting', {})
        self.default_rate_limit = self.rate_limits.get('requests_per_minute', 120)
        
        # IP whitelist and security
        self.ip_whitelist = self.config.get('ip_whitelist', ['127.0.0.1'])
        self.allowed_origins = self.config.get('allowed_origins', ['localhost'])
        
        # Server authentication configurations
        self.server_auth_configs: Dict[str, ServerAuthConfig] = {}
        
        # Active sessions
        self.active_sessions: Dict[str, AuthContext] = {}
        
        # Audit configuration
        self.audit_config = self.config.get('audit', {})
        self.audit_enabled = self.audit_config.get('enabled', True)
        self.audit_retention_days = self.audit_config.get('retention_days', 90)
        
        # Initialize hAIveMind security analytics (lazy initialization)
        self.security_haivemind = None
        
        logger.info(f"🔐 MCP Auth Manager initialized - auth {'enabled' if self.enable_auth else 'disabled'}")
    
    def _get_security_haivemind(self):
        """Lazy initialization of security hAIveMind"""
        if self.security_haivemind is None and self.memory_storage:
            from mcp_security_haivemind import MCPSecurityHAIveMind
            self.security_haivemind = MCPSecurityHAIveMind(self, self.memory_storage)
        return self.security_haivemind
    
    def _init_database(self):
        """Initialize SQLite database for authentication data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    permissions TEXT NOT NULL DEFAULT '[]',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    last_login INTEGER,
                    active BOOLEAN NOT NULL DEFAULT 1,
                    metadata TEXT DEFAULT '{}'
                );
                
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    key_hash TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    permissions TEXT NOT NULL DEFAULT '[]',
                    server_access TEXT DEFAULT '{}',
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER,
                    last_used INTEGER,
                    active BOOLEAN NOT NULL DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
                
                CREATE TABLE IF NOT EXISTS server_auth_configs (
                    server_id TEXT PRIMARY KEY,
                    auth_required BOOLEAN NOT NULL DEFAULT 1,
                    allowed_roles TEXT DEFAULT '[]',
                    allowed_users TEXT DEFAULT '[]',
                    tool_permissions TEXT DEFAULT '{}',
                    rate_limits TEXT DEFAULT '{}',
                    audit_level TEXT DEFAULT 'standard',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    server_id TEXT,
                    tool_name TEXT,
                    client_ip TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    details TEXT NOT NULL,
                    risk_level TEXT DEFAULT 'low'
                );
                
                CREATE TABLE IF NOT EXISTS rate_limit_violations (
                    violation_id TEXT PRIMARY KEY,
                    timestamp INTEGER NOT NULL,
                    client_ip TEXT NOT NULL,
                    user_id TEXT,
                    violation_type TEXT NOT NULL,
                    details TEXT NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
                CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
                CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
                CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id);
                CREATE INDEX IF NOT EXISTS idx_audit_server ON audit_events(server_id);
                CREATE INDEX IF NOT EXISTS idx_rate_violations_ip ON rate_limit_violations(client_ip);
            ''')
    
    def _init_redis(self, redis_config: Dict[str, Any]):
        """Initialize Redis client for session management"""
        try:
            self.redis_client = redis.Redis(
                host=redis_config['host'],
                port=redis_config['port'],
                db=redis_config.get('db', 1),  # Use different DB for auth
                password=redis_config.get('password'),
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("✅ Connected to Redis for authentication")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
    
    def _resolve_jwt_secret(self) -> str:
        """Resolve JWT secret from configuration"""
        secret = self.config.get('jwt_secret')
        if not secret or secret in ['change-this-secret-key', 'insecure-default-key']:
            secret = secrets.token_urlsafe(64)
            logger.warning("🔐 Using ephemeral JWT secret - sessions won't persist across restarts")
        return secret
    
    async def create_user(self, username: str, password: str, role: str = 'user', 
                         permissions: List[str] = None) -> Dict[str, Any]:
        """Create a new user account"""
        try:
            user_id = f"user_{secrets.token_urlsafe(16)}"
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            permissions = permissions or []
            
            now = int(time.time())
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO users (user_id, username, password_hash, role, permissions, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, username, password_hash, role, json.dumps(permissions), now, now))
            
            await self._audit_event(AuditEvent(
                timestamp=datetime.now(),
                event_type='user_created',
                user_id=user_id,
                server_id=None,
                tool_name=None,
                client_ip='system',
                success=True,
                details={'username': username, 'role': role}
            ))
            
            return {
                'success': True,
                'user_id': user_id,
                'username': username,
                'role': role
            }
        
        except sqlite3.IntegrityError:
            return {'success': False, 'error': 'Username already exists'}
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return {'success': False, 'error': str(e)}
    
    async def authenticate_user(self, username: str, password: str, client_ip: str) -> Tuple[bool, Optional[AuthContext]]:
        """Authenticate user with username/password"""
        if not self.enable_auth:
            # Create mock admin context when auth is disabled
            return True, AuthContext(
                user_id='admin',
                username='admin',
                role='admin',
                permissions={'*'},
                server_access={},
                client_ip=client_ip,
                session_id=secrets.token_urlsafe(32),
                expires_at=datetime.now() + timedelta(hours=24),
                metadata={}
            )
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT user_id, username, password_hash, role, permissions, active
                    FROM users WHERE username = ?
                ''', (username,))
                
                user_data = cursor.fetchone()
                if not user_data:
                    await self._audit_event(AuditEvent(
                        timestamp=datetime.now(),
                        event_type='login_failed',
                        user_id=username,
                        server_id=None,
                        tool_name=None,
                        client_ip=client_ip,
                        success=False,
                        details={'reason': 'user_not_found'},
                        risk_level='medium'
                    ))
                    return False, None
                
                user_id, db_username, password_hash, role, permissions_json, active = user_data
                
                if not active:
                    await self._audit_event(AuditEvent(
                        timestamp=datetime.now(),
                        event_type='login_failed',
                        user_id=user_id,
                        server_id=None,
                        tool_name=None,
                        client_ip=client_ip,
                        success=False,
                        details={'reason': 'account_disabled'},
                        risk_level='high'
                    ))
                    return False, None
                
                # Verify password
                if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                    await self._audit_event(AuditEvent(
                        timestamp=datetime.now(),
                        event_type='login_failed',
                        user_id=user_id,
                        server_id=None,
                        tool_name=None,
                        client_ip=client_ip,
                        success=False,
                        details={'reason': 'invalid_password'},
                        risk_level='high'
                    ))
                    return False, None
                
                # Create auth context
                permissions = set(json.loads(permissions_json))
                session_id = secrets.token_urlsafe(32)
                expires_at = datetime.now() + timedelta(hours=self.session_timeout)
                
                auth_context = AuthContext(
                    user_id=user_id,
                    username=db_username,
                    role=role,
                    permissions=permissions,
                    server_access=await self._get_user_server_access(user_id),
                    client_ip=client_ip,
                    session_id=session_id,
                    expires_at=expires_at,
                    metadata={}
                )
                
                # Store session
                await self._store_session(auth_context)
                
                # Update last login
                conn.execute('UPDATE users SET last_login = ? WHERE user_id = ?', 
                           (int(time.time()), user_id))
                
                await self._audit_event(AuditEvent(
                    timestamp=datetime.now(),
                    event_type='login_success',
                    user_id=user_id,
                    server_id=None,
                    tool_name=None,
                    client_ip=client_ip,
                    success=True,
                    details={'username': db_username, 'role': role}
                ))
                
                return True, auth_context
        
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False, None
    
    async def authenticate_api_key(self, api_key: str, client_ip: str) -> Tuple[bool, Optional[AuthContext]]:
        """Authenticate using API key"""
        if not self.enable_auth:
            return True, AuthContext(
                user_id='api_admin',
                username='api_admin',
                role='admin',
                permissions={'*'},
                server_access={},
                client_ip=client_ip,
                session_id=secrets.token_urlsafe(32),
                expires_at=datetime.now() + timedelta(hours=24),
                metadata={'auth_method': 'api_key'}
            )
        
        try:
            # Hash the provided key for lookup
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT ak.key_id, ak.user_id, ak.name, ak.role, ak.permissions, 
                           ak.server_access, ak.expires_at, ak.active,
                           u.username
                    FROM api_keys ak
                    JOIN users u ON ak.user_id = u.user_id
                    WHERE ak.key_hash = ? AND ak.active = 1 AND u.active = 1
                ''', (key_hash,))
                
                key_data = cursor.fetchone()
                if not key_data:
                    await self._audit_event(AuditEvent(
                        timestamp=datetime.now(),
                        event_type='api_auth_failed',
                        user_id='unknown',
                        server_id=None,
                        tool_name=None,
                        client_ip=client_ip,
                        success=False,
                        details={'reason': 'invalid_key'},
                        risk_level='high'
                    ))
                    return False, None
                
                (key_id, user_id, key_name, role, permissions_json, 
                 server_access_json, expires_at, active, username) = key_data
                
                # Check expiration
                if expires_at and expires_at < int(time.time()):
                    await self._audit_event(AuditEvent(
                        timestamp=datetime.now(),
                        event_type='api_auth_failed',
                        user_id=user_id,
                        server_id=None,
                        tool_name=None,
                        client_ip=client_ip,
                        success=False,
                        details={'reason': 'key_expired', 'key_name': key_name},
                        risk_level='medium'
                    ))
                    return False, None
                
                # Create auth context
                permissions = set(json.loads(permissions_json))
                server_access = json.loads(server_access_json) if server_access_json else {}
                
                auth_context = AuthContext(
                    user_id=user_id,
                    username=username,
                    role=role,
                    permissions=permissions,
                    server_access=server_access,
                    client_ip=client_ip,
                    session_id=key_id,  # Use key_id as session_id for API keys
                    expires_at=datetime.fromtimestamp(expires_at) if expires_at else datetime.now() + timedelta(days=365),
                    metadata={'auth_method': 'api_key', 'key_name': key_name}
                )
                
                # Update last used
                conn.execute('UPDATE api_keys SET last_used = ? WHERE key_id = ?', 
                           (int(time.time()), key_id))
                
                await self._audit_event(AuditEvent(
                    timestamp=datetime.now(),
                    event_type='api_auth_success',
                    user_id=user_id,
                    server_id=None,
                    tool_name=None,
                    client_ip=client_ip,
                    success=True,
                    details={'key_name': key_name, 'role': role}
                ))
                
                return True, auth_context
        
        except Exception as e:
            logger.error(f"API key authentication error: {e}")
            return False, None
    
    async def create_api_key(self, user_id: str, name: str, role: str = None, 
                           permissions: List[str] = None, server_access: Dict[str, List[str]] = None,
                           expires_days: int = None) -> Dict[str, Any]:
        """Create a new API key for a user"""
        try:
            # Generate API key
            api_key = f"mcp_{secrets.token_urlsafe(32)}"
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            key_id = f"key_{secrets.token_urlsafe(16)}"
            
            # Get user info for defaults
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT role, permissions FROM users WHERE user_id = ?', (user_id,))
                user_data = cursor.fetchone()
                if not user_data:
                    return {'success': False, 'error': 'User not found'}
                
                user_role, user_permissions = user_data
                
                # Use user defaults if not specified
                final_role = role or user_role
                final_permissions = permissions or json.loads(user_permissions)
                final_server_access = server_access or {}
                
                expires_at = None
                if expires_days:
                    expires_at = int(time.time()) + (expires_days * 24 * 3600)
                
                conn.execute('''
                    INSERT INTO api_keys 
                    (key_id, user_id, key_hash, name, role, permissions, server_access, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (key_id, user_id, key_hash, name, final_role, 
                      json.dumps(final_permissions), json.dumps(final_server_access),
                      int(time.time()), expires_at))
            
            await self._audit_event(AuditEvent(
                timestamp=datetime.now(),
                event_type='api_key_created',
                user_id=user_id,
                server_id=None,
                tool_name=None,
                client_ip='system',
                success=True,
                details={'key_name': name, 'role': final_role, 'expires_days': expires_days}
            ))
            
            return {
                'success': True,
                'key_id': key_id,
                'api_key': api_key,  # Only returned once!
                'name': name,
                'role': final_role,
                'expires_at': expires_at
            }
        
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            return {'success': False, 'error': str(e)}
    
    async def configure_server_auth(self, server_id: str, auth_config: ServerAuthConfig) -> bool:
        """Configure authentication settings for a specific MCP server"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO server_auth_configs
                    (server_id, auth_required, allowed_roles, allowed_users, tool_permissions, 
                     rate_limits, audit_level, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    server_id,
                    auth_config.auth_required,
                    json.dumps(list(auth_config.allowed_roles or [])),
                    json.dumps(list(auth_config.allowed_users or [])),
                    json.dumps(auth_config.tool_permissions or {}),
                    json.dumps(auth_config.rate_limits or {}),
                    auth_config.audit_level,
                    int(time.time()),
                    int(time.time())
                ))
            
            # Cache the config
            self.server_auth_configs[server_id] = auth_config
            
            await self._audit_event(AuditEvent(
                timestamp=datetime.now(),
                event_type='server_auth_configured',
                user_id='system',
                server_id=server_id,
                tool_name=None,
                client_ip='system',
                success=True,
                details={'auth_required': auth_config.auth_required, 'audit_level': auth_config.audit_level}
            ))
            
            return True
        
        except Exception as e:
            logger.error(f"Error configuring server auth: {e}")
            return False
    
    async def check_server_access(self, auth_context: AuthContext, server_id: str) -> bool:
        """Check if user has access to a specific MCP server"""
        if not self.enable_auth:
            return True
        
        # Get server auth config
        server_config = await self._get_server_auth_config(server_id)
        
        if not server_config.auth_required:
            return True
        
        # Check role-based access
        if server_config.allowed_roles and auth_context.role not in server_config.allowed_roles:
            return False
        
        # Check user-specific access
        if server_config.allowed_users and auth_context.user_id not in server_config.allowed_users:
            return False
        
        return True
    
    async def check_tool_permission(self, auth_context: AuthContext, server_id: str, tool_name: str) -> bool:
        """Check if user has permission to execute a specific tool"""
        if not self.enable_auth:
            return True
        
        # Admin role has access to everything
        if auth_context.role == 'admin' or '*' in auth_context.permissions:
            return True
        
        # Get server auth config
        server_config = await self._get_server_auth_config(server_id)
        
        # Check tool-level permissions
        if server_config.tool_permissions:
            tool_roles = server_config.tool_permissions.get(tool_name, set())
            if tool_roles and auth_context.role not in tool_roles:
                return False
        
        # Check user's server-specific access
        if server_id in auth_context.server_access:
            allowed_tools = auth_context.server_access[server_id]
            if allowed_tools and tool_name not in allowed_tools and '*' not in allowed_tools:
                return False
        
        return True
    
    async def check_rate_limit(self, auth_context: AuthContext, server_id: str) -> bool:
        """Check rate limiting for user/server combination"""
        if not self.enable_auth or not self.redis_client:
            return True
        
        try:
            # Get rate limit for user role
            server_config = await self._get_server_auth_config(server_id)
            rate_limit = server_config.rate_limits.get(auth_context.role, self.default_rate_limit)
            
            # Create rate limit key
            rate_key = f"rate_limit:{auth_context.user_id}:{server_id}"
            current_time = int(time.time())
            window_start = current_time - 60  # 1-minute window
            
            # Use Redis sorted set for sliding window rate limiting
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(rate_key, 0, window_start)  # Remove old entries
            pipe.zcard(rate_key)  # Count current requests
            pipe.zadd(rate_key, {str(current_time): current_time})  # Add current request
            pipe.expire(rate_key, 60)  # Set expiration
            
            results = pipe.execute()
            current_count = results[1]
            
            if current_count >= rate_limit:
                # Log rate limit violation
                await self._log_rate_limit_violation(auth_context, server_id, current_count, rate_limit)
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True  # Allow on error to avoid blocking legitimate requests
    
    async def audit_tool_execution(self, auth_context: AuthContext, server_id: str, 
                                 tool_name: str, arguments: Dict[str, Any], 
                                 success: bool, execution_time: float, 
                                 error: str = None) -> None:
        """Audit tool execution for security monitoring"""
        if not self.audit_enabled:
            return
        
        try:
            # Determine risk level based on tool and outcome
            risk_level = "low"
            if not success:
                risk_level = "medium"
            if tool_name in ['delete_memory', 'bulk_delete_memories', 'gdpr_delete_user_data']:
                risk_level = "high"
            
            details = {
                'tool_name': tool_name,
                'server_id': server_id,
                'execution_time_ms': execution_time * 1000,
                'argument_count': len(arguments),
                'auth_method': auth_context.metadata.get('auth_method', 'session')
            }
            
            if error:
                details['error'] = error
            
            # Store sensitive argument info securely
            sensitive_args = ['password', 'token', 'secret', 'key']
            if any(arg in str(arguments).lower() for arg in sensitive_args):
                details['contains_sensitive_data'] = True
                risk_level = "high"
            
            await self._audit_event(AuditEvent(
                timestamp=datetime.now(),
                event_type='tool_execution',
                user_id=auth_context.user_id,
                server_id=server_id,
                tool_name=tool_name,
                client_ip=auth_context.client_ip,
                success=success,
                details=details,
                risk_level=risk_level
            ))
            
            # Store in hAIveMind for security analytics
            if self.memory_storage:
                await self.memory_storage.store_memory(
                    content=f"MCP tool execution: {tool_name} on {server_id}",
                    category='security',
                    metadata={
                        'event_type': 'mcp_tool_execution_audit',
                        'user_id': auth_context.user_id,
                        'server_id': server_id,
                        'tool_name': tool_name,
                        'success': success,
                        'risk_level': risk_level,
                        'execution_time_ms': execution_time * 1000,
                        'timestamp': time.time()
                    },
                    scope='hive-shared'
                )
        
        except Exception as e:
            logger.error(f"Audit logging error: {e}")
    
    async def get_security_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get security analytics and insights"""
        try:
            cutoff_time = int(time.time()) - (days * 24 * 3600)
            
            with sqlite3.connect(self.db_path) as conn:
                # Failed authentication attempts
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM audit_events 
                    WHERE event_type IN ('login_failed', 'api_auth_failed') 
                    AND timestamp > ?
                ''', (cutoff_time,))
                failed_auths = cursor.fetchone()[0]
                
                # High-risk events
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM audit_events 
                    WHERE risk_level = 'high' AND timestamp > ?
                ''', (cutoff_time,))
                high_risk_events = cursor.fetchone()[0]
                
                # Top users by activity
                cursor = conn.execute('''
                    SELECT user_id, COUNT(*) as event_count
                    FROM audit_events 
                    WHERE timestamp > ?
                    GROUP BY user_id
                    ORDER BY event_count DESC
                    LIMIT 10
                ''', (cutoff_time,))
                top_users = cursor.fetchall()
                
                # Top tools executed
                cursor = conn.execute('''
                    SELECT tool_name, COUNT(*) as execution_count
                    FROM audit_events 
                    WHERE event_type = 'tool_execution' AND timestamp > ?
                    GROUP BY tool_name
                    ORDER BY execution_count DESC
                    LIMIT 10
                ''', (cutoff_time,))
                top_tools = cursor.fetchall()
                
                # Rate limit violations
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM rate_limit_violations 
                    WHERE timestamp > ?
                ''', (cutoff_time,))
                rate_violations = cursor.fetchone()[0]
            
            analytics = {
                'period_days': days,
                'failed_authentications': failed_auths,
                'high_risk_events': high_risk_events,
                'rate_limit_violations': rate_violations,
                'top_users': [{'user_id': u[0], 'event_count': u[1]} for u in top_users],
                'top_tools': [{'tool_name': t[0], 'execution_count': t[1]} for t in top_tools],
                'generated_at': datetime.now().isoformat()
            }
            
            # Store analytics in hAIveMind
            if self.memory_storage:
                await self.memory_storage.store_memory(
                    content=f"MCP Hub security analytics for {days} days",
                    category='security',
                    metadata={
                        'event_type': 'security_analytics',
                        'analytics_data': json.dumps(analytics),
                        'timestamp': time.time()
                    },
                    scope='hive-shared'
                )
            
            return analytics
        
        except Exception as e:
            logger.error(f"Error generating security analytics: {e}")
            return {'error': str(e)}
    
    # Private helper methods
    
    async def _get_server_auth_config(self, server_id: str) -> ServerAuthConfig:
        """Get authentication configuration for a server"""
        if server_id in self.server_auth_configs:
            return self.server_auth_configs[server_id]
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT auth_required, allowed_roles, allowed_users, tool_permissions, 
                           rate_limits, audit_level
                    FROM server_auth_configs WHERE server_id = ?
                ''', (server_id,))
                
                config_data = cursor.fetchone()
                if config_data:
                    auth_required, allowed_roles, allowed_users, tool_permissions, rate_limits, audit_level = config_data
                    
                    config = ServerAuthConfig(
                        server_id=server_id,
                        auth_required=bool(auth_required),
                        allowed_roles=set(json.loads(allowed_roles)) if allowed_roles else None,
                        allowed_users=set(json.loads(allowed_users)) if allowed_users else None,
                        tool_permissions=json.loads(tool_permissions) if tool_permissions else None,
                        rate_limits=json.loads(rate_limits) if rate_limits else None,
                        audit_level=audit_level
                    )
                else:
                    # Default configuration
                    config = ServerAuthConfig(server_id=server_id)
                
                self.server_auth_configs[server_id] = config
                return config
        
        except Exception as e:
            logger.error(f"Error loading server auth config: {e}")
            return ServerAuthConfig(server_id=server_id)
    
    async def _get_user_server_access(self, user_id: str) -> Dict[str, Set[str]]:
        """Get user's server-specific access permissions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT server_access FROM api_keys 
                    WHERE user_id = ? AND active = 1
                ''', (user_id,))
                
                server_access = {}
                for row in cursor.fetchall():
                    if row[0]:
                        access_data = json.loads(row[0])
                        for server_id, tools in access_data.items():
                            if server_id not in server_access:
                                server_access[server_id] = set()
                            server_access[server_id].update(tools)
                
                return server_access
        
        except Exception as e:
            logger.error(f"Error loading user server access: {e}")
            return {}
    
    async def _store_session(self, auth_context: AuthContext):
        """Store session in Redis or memory"""
        if self.redis_client:
            try:
                session_data = {
                    'user_id': auth_context.user_id,
                    'username': auth_context.username,
                    'role': auth_context.role,
                    'permissions': list(auth_context.permissions),
                    'server_access': {k: list(v) for k, v in auth_context.server_access.items()},
                    'client_ip': auth_context.client_ip,
                    'expires_at': auth_context.expires_at.timestamp(),
                    'metadata': auth_context.metadata
                }
                
                self.redis_client.setex(
                    f"session:{auth_context.session_id}",
                    int(self.session_timeout * 3600),
                    json.dumps(session_data)
                )
            except Exception as e:
                logger.error(f"Error storing session in Redis: {e}")
                # Fall back to memory storage
                self.active_sessions[auth_context.session_id] = auth_context
        else:
            self.active_sessions[auth_context.session_id] = auth_context
    
    async def _audit_event(self, event: AuditEvent):
        """Store audit event"""
        if not self.audit_enabled:
            return
        
        try:
            event_id = f"audit_{secrets.token_urlsafe(16)}"
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO audit_events
                    (event_id, timestamp, event_type, user_id, server_id, tool_name, 
                     client_ip, success, details, risk_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event_id,
                    int(event.timestamp.timestamp()),
                    event.event_type,
                    event.user_id,
                    event.server_id,
                    event.tool_name,
                    event.client_ip,
                    event.success,
                    json.dumps(event.details),
                    event.risk_level
                ))
            
            # Analyze event with hAIveMind security analytics
            haivemind = self._get_security_haivemind()
            if haivemind:
                event_data = {
                    'event_type': event.event_type,
                    'user_id': event.user_id,
                    'server_id': event.server_id,
                    'tool_name': event.tool_name,
                    'client_ip': event.client_ip,
                    'success': event.success,
                    'timestamp': event.timestamp.timestamp(),
                    'details': event.details,
                    'risk_level': event.risk_level
                }
                
                # Analyze authentication events
                if event.event_type in ['login_success', 'login_failed', 'api_auth_success', 'api_auth_failed']:
                    patterns = await haivemind.analyze_authentication_event(event_data)
                    if patterns:
                        logger.info(f"Security patterns detected: {[p.pattern_type for p in patterns]}")
                
                # Analyze tool execution events
                elif event.event_type == 'tool_execution':
                    patterns = await haivemind.analyze_tool_execution_event(event_data)
                    if patterns:
                        logger.info(f"Tool execution patterns detected: {[p.pattern_type for p in patterns]}")
        
        except Exception as e:
            logger.error(f"Error storing audit event: {e}")
    
    async def _log_rate_limit_violation(self, auth_context: AuthContext, server_id: str, 
                                      current_count: int, limit: int):
        """Log rate limit violation"""
        try:
            violation_id = f"violation_{secrets.token_urlsafe(16)}"
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO rate_limit_violations
                    (violation_id, timestamp, client_ip, user_id, violation_type, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    violation_id,
                    int(time.time()),
                    auth_context.client_ip,
                    auth_context.user_id,
                    'rate_limit_exceeded',
                    json.dumps({
                        'server_id': server_id,
                        'current_count': current_count,
                        'limit': limit,
                        'role': auth_context.role
                    })
                ))
            
            await self._audit_event(AuditEvent(
                timestamp=datetime.now(),
                event_type='rate_limit_violation',
                user_id=auth_context.user_id,
                server_id=server_id,
                tool_name=None,
                client_ip=auth_context.client_ip,
                success=False,
                details={'current_count': current_count, 'limit': limit},
                risk_level='medium'
            ))
        
        except Exception as e:
            logger.error(f"Error logging rate limit violation: {e}")