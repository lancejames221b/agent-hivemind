#!/usr/bin/env python3
"""
Database models and management for hAIveMind Control Dashboard
"""
import sqlite3
import bcrypt
import secrets
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

class UserRole(Enum):
    ADMIN = "admin"
    OPERATOR = "operator" 
    VIEWER = "viewer"
    AGENT = "agent"

class DeviceStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"

class KeyStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"

class MCPServerType(Enum):
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"
    WEBSOCKET = "websocket"

class MCPServerStatus(Enum):
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    DISABLED = "disabled"

@dataclass
class User:
    id: Optional[int]
    username: str
    email: str
    password_hash: str
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    mfa_secret: Optional[str] = None

@dataclass
class Device:
    id: Optional[int]
    device_id: str
    machine_id: str
    hostname: str
    fingerprint: str
    owner_id: int
    status: DeviceStatus
    metadata: Dict[str, Any]
    created_at: datetime
    approved_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    ip_address: Optional[str] = None

@dataclass
class APIKey:
    id: Optional[int]
    key_id: str
    key_hash: str
    device_id: int
    user_id: int
    name: str
    scopes: List[str]
    status: KeyStatus
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0

@dataclass
class MCPServer:
    id: Optional[int]
    name: str
    server_type: MCPServerType
    endpoint: str
    description: Optional[str]
    config: Dict[str, Any]  # JSON config for server-specific settings
    auth_config: Optional[Dict[str, Any]]  # Authentication configuration
    enabled: bool
    created_at: datetime
    created_by: int  # user_id
    priority: int = 100  # Lower number = higher priority
    tags: List[str] = None

@dataclass
class MCPServerHealth:
    id: Optional[int]
    server_id: int
    status: MCPServerStatus
    response_time_ms: Optional[float]
    error_message: Optional[str]
    tools_available: List[str]  # JSON array of tool names
    last_check: datetime
    consecutive_failures: int = 0

class ControlDatabase:
    def __init__(self, db_path: str = "database/haivemind.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            # Users table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    mfa_secret TEXT
                )
            """)
            
            # Devices table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT UNIQUE NOT NULL,
                    machine_id TEXT NOT NULL,
                    hostname TEXT NOT NULL,
                    fingerprint TEXT UNIQUE NOT NULL,
                    owner_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP,
                    last_seen TIMESTAMP,
                    ip_address TEXT,
                    FOREIGN KEY (owner_id) REFERENCES users (id)
                )
            """)
            
            # API Keys table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_id TEXT UNIQUE NOT NULL,
                    key_hash TEXT NOT NULL,
                    device_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    scopes TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    last_used TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    FOREIGN KEY (device_id) REFERENCES devices (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Access logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    device_id INTEGER,
                    api_key_id INTEGER,
                    action TEXT NOT NULL,
                    resource TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (device_id) REFERENCES devices (id),
                    FOREIGN KEY (api_key_id) REFERENCES api_keys (id)
                )
            """)
            
            # Device groups table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS device_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    device_ids TEXT NOT NULL DEFAULT '[]',
                    permissions TEXT NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # IP whitelist table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ip_whitelist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    ip_range TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices (id)
                )
            """)
            
            # MCP servers table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mcp_servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    server_type TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    description TEXT,
                    config TEXT NOT NULL DEFAULT '{}',
                    auth_config TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER NOT NULL,
                    priority INTEGER DEFAULT 100,
                    tags TEXT DEFAULT '[]',
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            """)
            
            # MCP server health table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mcp_server_health (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'unknown',
                    response_time_ms REAL,
                    error_message TEXT,
                    tools_available TEXT DEFAULT '[]',
                    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    consecutive_failures INTEGER DEFAULT 0,
                    FOREIGN KEY (server_id) REFERENCES mcp_servers (id)
                )
            """)
            
            # Create default admin user if none exists
            self._create_default_admin()
    
    def _create_default_admin(self):
        """Create default admin user if no users exist"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            if user_count == 0:
                # Create default admin
                admin_password = secrets.token_urlsafe(16)
                password_hash = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt()).decode()
                
                conn.execute("""
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (?, ?, ?, ?)
                """, ("admin", "admin@haivemind.local", password_hash, "admin"))
                
                print(f"✅ Default admin user created:")
                print(f"   Username: admin")
                print(f"   Password: {admin_password}")
                print(f"   ⚠️  Change this password immediately after first login!")
    
    # User Management Methods
    def create_user(self, username: str, email: str, password: str, role: UserRole) -> int:
        """Create a new user"""
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (?, ?, ?, ?)
            """, (username, email, password_hash, role.value))
            return cursor.lastrowid
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM users WHERE username = ? AND is_active = 1
            """, (username,))
            row = cursor.fetchone()
            if row:
                return User(
                    id=row['id'],
                    username=row['username'],
                    email=row['email'],
                    password_hash=row['password_hash'],
                    role=UserRole(row['role']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None,
                    is_active=bool(row['is_active']),
                    mfa_secret=row['mfa_secret']
                )
        return None
    
    def verify_password(self, username: str, password: str) -> bool:
        """Verify user password"""
        user = self.get_user_by_username(username)
        if user:
            return bcrypt.checkpw(password.encode(), user.password_hash.encode())
        return False
    
    def update_last_login(self, user_id: int):
        """Update user's last login timestamp"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            """, (user_id,))
    
    # Device Management Methods
    def register_device(self, device_id: str, machine_id: str, hostname: str, 
                       owner_id: int, metadata: Dict[str, Any], ip_address: str) -> int:
        """Register a new device"""
        # Generate device fingerprint
        fingerprint_data = f"{device_id}{machine_id}{hostname}{json.dumps(metadata, sort_keys=True)}"
        fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO devices (device_id, machine_id, hostname, fingerprint, 
                                   owner_id, metadata, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (device_id, machine_id, hostname, fingerprint, owner_id, 
                  json.dumps(metadata), ip_address))
            return cursor.lastrowid
    
    def get_device(self, device_id: str) -> Optional[Device]:
        """Get device by device_id"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM devices WHERE device_id = ?
            """, (device_id,))
            row = cursor.fetchone()
            if row:
                return Device(
                    id=row['id'],
                    device_id=row['device_id'],
                    machine_id=row['machine_id'],
                    hostname=row['hostname'],
                    fingerprint=row['fingerprint'],
                    owner_id=row['owner_id'],
                    status=DeviceStatus(row['status']),
                    metadata=json.loads(row['metadata']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    approved_at=datetime.fromisoformat(row['approved_at']) if row['approved_at'] else None,
                    last_seen=datetime.fromisoformat(row['last_seen']) if row['last_seen'] else None,
                    ip_address=row['ip_address']
                )
        return None
    
    def approve_device(self, device_id: str, approved_by: int) -> bool:
        """Approve a pending device"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE devices SET status = 'approved', approved_at = CURRENT_TIMESTAMP
                WHERE device_id = ? AND status = 'pending'
            """, (device_id,))
            return cursor.rowcount > 0
    
    def list_devices(self, status: Optional[DeviceStatus] = None, owner_id: Optional[int] = None) -> List[Device]:
        """List devices with optional filtering"""
        query = "SELECT * FROM devices WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        if owner_id:
            query += " AND owner_id = ?"
            params.append(owner_id)
        
        query += " ORDER BY created_at DESC"
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            devices = []
            for row in cursor.fetchall():
                devices.append(Device(
                    id=row['id'],
                    device_id=row['device_id'],
                    machine_id=row['machine_id'],
                    hostname=row['hostname'],
                    fingerprint=row['fingerprint'],
                    owner_id=row['owner_id'],
                    status=DeviceStatus(row['status']),
                    metadata=json.loads(row['metadata']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    approved_at=datetime.fromisoformat(row['approved_at']) if row['approved_at'] else None,
                    last_seen=datetime.fromisoformat(row['last_seen']) if row['last_seen'] else None,
                    ip_address=row['ip_address']
                ))
            return devices
    
    # API Key Management Methods
    def generate_api_key(self, device_id: int, user_id: int, name: str, 
                        scopes: List[str], expires_hours: Optional[int] = None) -> tuple[str, str]:
        """Generate a new API key and return (key_id, raw_key)"""
        key_id = f"hv_{secrets.token_urlsafe(12)}"
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        expires_at = None
        if expires_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO api_keys (key_id, key_hash, device_id, user_id, name, scopes, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (key_id, key_hash, device_id, user_id, name, json.dumps(scopes), expires_at))
        
        return key_id, raw_key
    
    def validate_api_key(self, raw_key: str) -> Optional[APIKey]:
        """Validate API key and return key info"""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM api_keys 
                WHERE key_hash = ? AND status = 'active'
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """, (key_hash,))
            row = cursor.fetchone()
            if row:
                # Update usage
                conn.execute("""
                    UPDATE api_keys SET usage_count = usage_count + 1, last_used = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (row['id'],))
                
                return APIKey(
                    id=row['id'],
                    key_id=row['key_id'],
                    key_hash=row['key_hash'],
                    device_id=row['device_id'],
                    user_id=row['user_id'],
                    name=row['name'],
                    scopes=json.loads(row['scopes']),
                    status=KeyStatus(row['status']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                    last_used=datetime.fromisoformat(row['last_used']) if row['last_used'] else None,
                    usage_count=row['usage_count']
                )
        return None
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE api_keys SET status = 'revoked' WHERE key_id = ?
            """, (key_id,))
            return cursor.rowcount > 0
    
    def log_access(self, user_id: Optional[int], device_id: Optional[int], 
                  api_key_id: Optional[int], action: str, resource: Optional[str],
                  ip_address: str, user_agent: str, success: bool, 
                  error_message: Optional[str] = None):
        """Log access attempt"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO access_logs (user_id, device_id, api_key_id, action, resource,
                                       ip_address, user_agent, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, device_id, api_key_id, action, resource, 
                  ip_address, user_agent, success, error_message))
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        with self.get_connection() as conn:
            stats = {}
            
            # User stats
            cursor = conn.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            stats['active_users'] = cursor.fetchone()[0]
            
            # Device stats
            cursor = conn.execute("SELECT status, COUNT(*) FROM devices GROUP BY status")
            device_stats = {row[0]: row[1] for row in cursor.fetchall()}
            stats['devices'] = device_stats
            stats['total_devices'] = sum(device_stats.values())
            
            # API key stats
            cursor = conn.execute("SELECT COUNT(*) FROM api_keys WHERE status = 'active'")
            stats['active_keys'] = cursor.fetchone()[0]
            
            # Recent activity
            cursor = conn.execute("""
                SELECT COUNT(*) FROM access_logs 
                WHERE created_at > datetime('now', '-24 hours')
            """)
            stats['recent_activity'] = cursor.fetchone()[0]
            
            return stats
    
    # MCP Server Management Methods
    
    def add_mcp_server(self, name: str, server_type: MCPServerType, endpoint: str,
                       description: Optional[str], config: Dict[str, Any],
                       auth_config: Optional[Dict[str, Any]], created_by: int,
                       priority: int = 100, tags: List[str] = None) -> int:
        """Add a new MCP server"""
        if tags is None:
            tags = []
            
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO mcp_servers (name, server_type, endpoint, description, config, 
                                       auth_config, created_by, priority, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, server_type.value, endpoint, description, json.dumps(config),
                  json.dumps(auth_config) if auth_config else None, created_by, priority, json.dumps(tags)))
            return cursor.lastrowid
    
    def get_mcp_servers(self, enabled_only: bool = False) -> List[MCPServer]:
        """Get all MCP servers"""
        query = "SELECT * FROM mcp_servers"
        params = ()
        
        if enabled_only:
            query += " WHERE enabled = 1"
        
        query += " ORDER BY priority ASC, name ASC"
        
        servers = []
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            for row in cursor.fetchall():
                servers.append(MCPServer(
                    id=row['id'],
                    name=row['name'],
                    server_type=MCPServerType(row['server_type']),
                    endpoint=row['endpoint'],
                    description=row['description'],
                    config=json.loads(row['config']),
                    auth_config=json.loads(row['auth_config']) if row['auth_config'] else None,
                    enabled=bool(row['enabled']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    created_by=row['created_by'],
                    priority=row['priority'],
                    tags=json.loads(row['tags'])
                ))
        return servers
    
    def get_mcp_server(self, server_id: int) -> Optional[MCPServer]:
        """Get specific MCP server by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM mcp_servers WHERE id = ?", (server_id,))
            row = cursor.fetchone()
            if row:
                return MCPServer(
                    id=row['id'],
                    name=row['name'],
                    server_type=MCPServerType(row['server_type']),
                    endpoint=row['endpoint'],
                    description=row['description'],
                    config=json.loads(row['config']),
                    auth_config=json.loads(row['auth_config']) if row['auth_config'] else None,
                    enabled=bool(row['enabled']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    created_by=row['created_by'],
                    priority=row['priority'],
                    tags=json.loads(row['tags'])
                )
        return None
    
    def update_mcp_server(self, server_id: int, name: Optional[str] = None,
                          server_type: Optional[MCPServerType] = None,
                          endpoint: Optional[str] = None,
                          description: Optional[str] = None,
                          config: Optional[Dict[str, Any]] = None,
                          auth_config: Optional[Dict[str, Any]] = None,
                          enabled: Optional[bool] = None,
                          priority: Optional[int] = None,
                          tags: Optional[List[str]] = None) -> bool:
        """Update MCP server configuration"""
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if server_type is not None:
            updates.append("server_type = ?")
            params.append(server_type.value)
        if endpoint is not None:
            updates.append("endpoint = ?")
            params.append(endpoint)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if config is not None:
            updates.append("config = ?")
            params.append(json.dumps(config))
        if auth_config is not None:
            updates.append("auth_config = ?")
            params.append(json.dumps(auth_config))
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(enabled)
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))
        
        if not updates:
            return False
        
        params.append(server_id)
        
        with self.get_connection() as conn:
            cursor = conn.execute(f"""
                UPDATE mcp_servers SET {', '.join(updates)} WHERE id = ?
            """, params)
            return cursor.rowcount > 0
    
    def delete_mcp_server(self, server_id: int) -> bool:
        """Delete MCP server and related health records"""
        with self.get_connection() as conn:
            # Delete health records first (foreign key constraint)
            conn.execute("DELETE FROM mcp_server_health WHERE server_id = ?", (server_id,))
            # Delete server
            cursor = conn.execute("DELETE FROM mcp_servers WHERE id = ?", (server_id,))
            return cursor.rowcount > 0
    
    def update_server_health(self, server_id: int, status: MCPServerStatus,
                           response_time_ms: Optional[float] = None,
                           error_message: Optional[str] = None,
                           tools_available: List[str] = None,
                           consecutive_failures: int = 0) -> None:
        """Update or insert server health record"""
        if tools_available is None:
            tools_available = []
            
        with self.get_connection() as conn:
            # Try to update existing health record
            cursor = conn.execute("""
                UPDATE mcp_server_health 
                SET status = ?, response_time_ms = ?, error_message = ?, 
                    tools_available = ?, last_check = CURRENT_TIMESTAMP,
                    consecutive_failures = ?
                WHERE server_id = ?
            """, (status.value, response_time_ms, error_message, 
                  json.dumps(tools_available), consecutive_failures, server_id))
            
            # If no existing record, insert new one
            if cursor.rowcount == 0:
                conn.execute("""
                    INSERT INTO mcp_server_health (server_id, status, response_time_ms, 
                                                 error_message, tools_available, consecutive_failures)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (server_id, status.value, response_time_ms, error_message,
                      json.dumps(tools_available), consecutive_failures))
    
    def get_server_health(self, server_id: int) -> Optional[MCPServerHealth]:
        """Get current health status for a server"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM mcp_server_health WHERE server_id = ?
                ORDER BY last_check DESC LIMIT 1
            """, (server_id,))
            row = cursor.fetchone()
            if row:
                return MCPServerHealth(
                    id=row['id'],
                    server_id=row['server_id'],
                    status=MCPServerStatus(row['status']),
                    response_time_ms=row['response_time_ms'],
                    error_message=row['error_message'],
                    tools_available=json.loads(row['tools_available']),
                    last_check=datetime.fromisoformat(row['last_check']),
                    consecutive_failures=row['consecutive_failures']
                )
        return None
    
    def get_all_server_health(self) -> List[MCPServerHealth]:
        """Get health status for all servers"""
        health_records = []
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT h.* FROM mcp_server_health h
                INNER JOIN (
                    SELECT server_id, MAX(last_check) as max_check
                    FROM mcp_server_health
                    GROUP BY server_id
                ) latest ON h.server_id = latest.server_id AND h.last_check = latest.max_check
                ORDER BY h.server_id
            """)
            for row in cursor.fetchall():
                health_records.append(MCPServerHealth(
                    id=row['id'],
                    server_id=row['server_id'],
                    status=MCPServerStatus(row['status']),
                    response_time_ms=row['response_time_ms'],
                    error_message=row['error_message'],
                    tools_available=json.loads(row['tools_available']),
                    last_check=datetime.fromisoformat(row['last_check']),
                    consecutive_failures=row['consecutive_failures']
                ))
        return health_records