"""
Enhanced Database Manager for Credential Vault
PostgreSQL-based database operations with comprehensive schema support.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
import secrets
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import asyncpg
import redis
from contextlib import asynccontextmanager

from .core_vault import CredentialMetadata, CredentialType, AccessLevel, CredentialStatus


class DatabaseManager:
    """Enhanced database manager for vault operations with PostgreSQL"""
    
    def __init__(self, config: Dict[str, Any], redis_client: Optional[redis.Redis]):
        self.config = config
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        
        # Database configuration
        self.db_config = config.get('vault', {}).get('database', {})
        self.connection_pool: Optional[asyncpg.Pool] = None
        
        # Connection settings
        self.host = self.db_config.get('host', 'localhost')
        self.port = self.db_config.get('port', 5432)
        self.database = self.db_config.get('database', 'vault_db')
        self.username = self.db_config.get('username', 'vault_user')
        self.password = self.db_config.get('password', 'secure_password')
        self.ssl_mode = self.db_config.get('ssl_mode', 'prefer')
        
        # Connection pool settings
        self.min_connections = self.db_config.get('min_connections', 5)
        self.max_connections = self.db_config.get('max_connections', 20)
        self.connection_timeout = self.db_config.get('connection_timeout', 30)
        
    async def initialize(self) -> bool:
        """Initialize database connection pool and schema"""
        try:
            # Create connection pool
            self.connection_pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                ssl=self.ssl_mode,
                min_size=self.min_connections,
                max_size=self.max_connections,
                command_timeout=self.connection_timeout
            )
            
            # Test connection
            async with self.connection_pool.acquire() as conn:
                await conn.execute('SELECT 1')
            
            self.logger.info("Database connection pool initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {str(e)}")
            return False
    
    async def close(self):
        """Close database connection pool"""
        if self.connection_pool:
            await self.connection_pool.close()
            self.logger.info("Database connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool"""
        if not self.connection_pool:
            raise RuntimeError("Database not initialized")
        
        async with self.connection_pool.acquire() as conn:
            yield conn
    
    @asynccontextmanager
    async def get_transaction(self):
        """Get database transaction"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                yield conn
    
    async def store_credential_metadata(self, metadata: CredentialMetadata, 
                                      connection: Optional[asyncpg.Connection] = None) -> bool:
        """Store credential metadata"""
        try:
            query = """
                INSERT INTO credentials 
                (id, name, description, credential_type, organization_id, environment_id, 
                 project_id, service_id, owner_id, created_by, created_at, updated_at, 
                 expires_at, rotation_interval_days, next_rotation, auto_rotate, 
                 risk_level, compliance_labels, tags, access_count, backup_enabled, 
                 audit_enabled, is_active, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, 
                        $16, $17, $18, $19, $20, $21, $22, $23, $24)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    updated_at = EXCLUDED.updated_at,
                    expires_at = EXCLUDED.expires_at,
                    rotation_interval_days = EXCLUDED.rotation_interval_days,
                    next_rotation = EXCLUDED.next_rotation,
                    auto_rotate = EXCLUDED.auto_rotate,
                    risk_level = EXCLUDED.risk_level,
                    compliance_labels = EXCLUDED.compliance_labels,
                    tags = EXCLUDED.tags,
                    backup_enabled = EXCLUDED.backup_enabled,
                    audit_enabled = EXCLUDED.audit_enabled,
                    metadata = EXCLUDED.metadata
            """
            
            # Convert metadata to database format
            values = (
                metadata.credential_id,
                metadata.name,
                metadata.description,
                metadata.credential_type.value,
                metadata.organization_id if hasattr(metadata, 'organization_id') else None,
                metadata.environment_id if hasattr(metadata, 'environment_id') else None,
                metadata.project_id if hasattr(metadata, 'project_id') else None,
                metadata.service_id if hasattr(metadata, 'service_id') else None,
                metadata.owner_id,
                metadata.owner_id,  # created_by same as owner for now
                metadata.created_at,
                metadata.updated_at,
                metadata.expires_at,
                getattr(metadata, 'rotation_interval_days', 90),
                getattr(metadata, 'next_rotation', None),
                getattr(metadata, 'auto_rotate', False),
                getattr(metadata, 'risk_level', 'medium'),
                metadata.compliance_labels,
                metadata.tags,
                0,  # access_count
                True,  # backup_enabled
                metadata.audit_required,
                metadata.status == CredentialStatus.ACTIVE,
                json.dumps(getattr(metadata, 'additional_metadata', {}))
            )
            
            if connection:
                await connection.execute(query, *values)
            else:
                async with self.get_connection() as conn:
                    await conn.execute(query, *values)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store credential metadata: {str(e)}")
            return False
    
    async def store_encrypted_credential(self, credential_id: str, encrypted_data: bytes,
                                       encryption_key_version: int, salt: bytes, nonce: bytes,
                                       auth_tag: bytes, connection: Optional[asyncpg.Connection] = None) -> bool:
        """Store encrypted credential data"""
        try:
            query = """
                INSERT INTO credentials 
                (encrypted_data, encryption_key_version, salt, nonce, auth_tag)
                VALUES ($1, $2, $3, $4, $5)
                WHERE id = $6
            """
            
            # Note: This is a simplified approach. In the full schema, encrypted data 
            # would be stored in the same table with the metadata
            update_query = """
                UPDATE credentials 
                SET encrypted_data = $1, encryption_key_version = $2, salt = $3, 
                    nonce = $4, auth_tag = $5, updated_at = NOW()
                WHERE id = $6
            """
            
            if connection:
                await connection.execute(update_query, encrypted_data, encryption_key_version,
                                       salt, nonce, auth_tag, credential_id)
            else:
                async with self.get_connection() as conn:
                    await conn.execute(update_query, encrypted_data, encryption_key_version,
                                     salt, nonce, auth_tag, credential_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store encrypted credential: {str(e)}")
            return False
    
    async def retrieve_credential_metadata(self, credential_id: str,
                                         connection: Optional[asyncpg.Connection] = None) -> Optional[CredentialMetadata]:
        """Retrieve credential metadata"""
        try:
            query = """
                SELECT c.*, o.name as organization_name, e.name as environment_name,
                       p.name as project_name, s.name as service_name, u.email as owner_email
                FROM credentials c
                LEFT JOIN organizations o ON c.organization_id = o.id
                LEFT JOIN environments e ON c.environment_id = e.id
                LEFT JOIN projects p ON c.project_id = p.id
                LEFT JOIN services s ON c.service_id = s.id
                LEFT JOIN users u ON c.owner_id = u.id
                WHERE c.id = $1 AND c.is_active = true AND c.is_deleted = false
            """
            
            if connection:
                row = await connection.fetchrow(query, credential_id)
            else:
                async with self.get_connection() as conn:
                    row = await conn.fetchrow(query, credential_id)
            
            if not row:
                return None
            
            # Convert database row to CredentialMetadata
            metadata = CredentialMetadata(
                credential_id=row['id'],
                name=row['name'],
                description=row['description'],
                credential_type=CredentialType(row['credential_type']),
                environment=row['environment_name'] or 'unknown',
                service=row['service_name'] or 'unknown',
                project=row['project_name'] or 'unknown',
                owner_id=row['owner_id'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                last_accessed=row['last_accessed'],
                expires_at=row['expires_at'],
                rotation_schedule=None,  # Would map from rotation_interval_days
                status=CredentialStatus.ACTIVE if row['is_active'] else CredentialStatus.INACTIVE,
                tags=row['tags'] or [],
                compliance_labels=row['compliance_labels'] or [],
                audit_required=row['audit_enabled'],
                emergency_access=row.get('emergency_access', False)
            )
            
            # Add additional attributes
            setattr(metadata, 'organization_id', row['organization_id'])
            setattr(metadata, 'environment_id', row['environment_id'])
            setattr(metadata, 'project_id', row['project_id'])
            setattr(metadata, 'service_id', row['service_id'])
            setattr(metadata, 'risk_level', row['risk_level'])
            setattr(metadata, 'access_count', row['access_count'])
            setattr(metadata, 'rotation_interval_days', row['rotation_interval_days'])
            setattr(metadata, 'next_rotation', row['next_rotation'])
            setattr(metadata, 'auto_rotate', row['auto_rotate'])
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve credential metadata: {str(e)}")
            return None
    
    async def retrieve_encrypted_credential(self, credential_id: str,
                                          connection: Optional[asyncpg.Connection] = None) -> Optional[Tuple[bytes, int, bytes, bytes, bytes]]:
        """Retrieve encrypted credential data"""
        try:
            query = """
                SELECT encrypted_data, encryption_key_version, salt, nonce, auth_tag
                FROM credentials
                WHERE id = $1 AND is_active = true AND is_deleted = false
            """
            
            if connection:
                row = await connection.fetchrow(query, credential_id)
            else:
                async with self.get_connection() as conn:
                    row = await conn.fetchrow(query, credential_id)
            
            if not row or not row['encrypted_data']:
                return None
            
            return (
                row['encrypted_data'],
                row['encryption_key_version'],
                row['salt'],
                row['nonce'],
                row['auth_tag']
            )
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve encrypted credential: {str(e)}")
            return None
    
    async def list_credentials_for_user(self, user_id: str, filters: Dict[str, Any] = None,
                                      connection: Optional[asyncpg.Connection] = None) -> List[CredentialMetadata]:
        """List credentials accessible to user"""
        try:
            # Base query with access control
            base_query = """
                SELECT DISTINCT c.*, o.name as organization_name, e.name as environment_name,
                       p.name as project_name, s.name as service_name, u.email as owner_email
                FROM credentials c
                LEFT JOIN organizations o ON c.organization_id = o.id
                LEFT JOIN environments e ON c.environment_id = e.id
                LEFT JOIN projects p ON c.project_id = p.id
                LEFT JOIN services s ON c.service_id = s.id
                LEFT JOIN users u ON c.owner_id = u.id
                LEFT JOIN credential_shares cs ON c.id = cs.credential_id
                LEFT JOIN user_roles ur ON (
                    ur.user_id = $1 AND ur.is_active = true AND
                    (ur.expires_at IS NULL OR ur.expires_at > NOW()) AND
                    (ur.organization_id = c.organization_id OR
                     ur.environment_id = c.environment_id OR
                     ur.project_id = c.project_id OR
                     ur.service_id = c.service_id OR
                     ur.role IN ('super_admin', 'security_admin', 'audit_admin'))
                )
                WHERE c.is_active = true AND c.is_deleted = false AND (
                    c.owner_id = $1 OR
                    (cs.shared_with_user_id = $1 AND cs.is_active = true AND
                     (cs.expires_at IS NULL OR cs.expires_at > NOW())) OR
                    ur.user_id IS NOT NULL
                )
            """
            
            params = [user_id]
            param_count = 1
            
            # Add filters
            if filters:
                if 'environment' in filters:
                    param_count += 1
                    base_query += f" AND e.name = ${param_count}"
                    params.append(filters['environment'])
                
                if 'service' in filters:
                    param_count += 1
                    base_query += f" AND s.name = ${param_count}"
                    params.append(filters['service'])
                
                if 'project' in filters:
                    param_count += 1
                    base_query += f" AND p.name = ${param_count}"
                    params.append(filters['project'])
                
                if 'credential_type' in filters:
                    param_count += 1
                    base_query += f" AND c.credential_type = ${param_count}"
                    params.append(filters['credential_type'])
                
                if 'status' in filters:
                    if filters['status'] == 'active':
                        base_query += " AND c.is_active = true"
                    elif filters['status'] == 'inactive':
                        base_query += " AND c.is_active = false"
            
            base_query += " ORDER BY c.updated_at DESC"
            
            if connection:
                rows = await connection.fetch(base_query, *params)
            else:
                async with self.get_connection() as conn:
                    rows = await conn.fetch(base_query, *params)
            
            credentials = []
            for row in rows:
                metadata = CredentialMetadata(
                    credential_id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    credential_type=CredentialType(row['credential_type']),
                    environment=row['environment_name'] or 'unknown',
                    service=row['service_name'] or 'unknown',
                    project=row['project_name'] or 'unknown',
                    owner_id=row['owner_id'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    last_accessed=row['last_accessed'],
                    expires_at=row['expires_at'],
                    rotation_schedule=None,
                    status=CredentialStatus.ACTIVE if row['is_active'] else CredentialStatus.INACTIVE,
                    tags=row['tags'] or [],
                    compliance_labels=row['compliance_labels'] or [],
                    audit_required=row['audit_enabled'],
                    emergency_access=row.get('emergency_access', False)
                )
                
                # Add additional attributes
                setattr(metadata, 'organization_id', row['organization_id'])
                setattr(metadata, 'environment_id', row['environment_id'])
                setattr(metadata, 'project_id', row['project_id'])
                setattr(metadata, 'service_id', row['service_id'])
                setattr(metadata, 'risk_level', row['risk_level'])
                setattr(metadata, 'access_count', row['access_count'])
                
                credentials.append(metadata)
            
            return credentials
            
        except Exception as e:
            self.logger.error(f"Failed to list credentials: {str(e)}")
            return []
    
    async def update_access_timestamp(self, credential_id: str,
                                    connection: Optional[asyncpg.Connection] = None) -> bool:
        """Update last accessed timestamp and increment access count"""
        try:
            query = """
                UPDATE credentials 
                SET last_accessed = NOW(), access_count = access_count + 1
                WHERE id = $1
            """
            
            if connection:
                await connection.execute(query, credential_id)
            else:
                async with self.get_connection() as conn:
                    await conn.execute(query, credential_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update access timestamp: {str(e)}")
            return False
    
    async def store_audit_log(self, user_id: str, credential_id: Optional[str], 
                            event_type: str, action: str, result: str,
                            ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                            metadata: Dict[str, Any] = None, risk_score: float = 0.0,
                            connection: Optional[asyncpg.Connection] = None) -> bool:
        """Store audit log entry"""
        try:
            query = """
                INSERT INTO audit_log 
                (id, event_type, user_id, credential_id, action, result, ip_address, 
                 user_agent, timestamp, risk_score, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), $9, $10)
            """
            
            audit_id = secrets.token_urlsafe(32)
            
            if connection:
                await connection.execute(query, audit_id, event_type, user_id, credential_id,
                                       action, result, ip_address, user_agent, risk_score,
                                       json.dumps(metadata or {}))
            else:
                async with self.get_connection() as conn:
                    await conn.execute(query, audit_id, event_type, user_id, credential_id,
                                     action, result, ip_address, user_agent, risk_score,
                                     json.dumps(metadata or {}))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store audit log: {str(e)}")
            return False
    
    async def grant_credential_access(self, credential_id: str, user_id: str, 
                                    access_level: str, granted_by: str,
                                    expires_at: Optional[datetime] = None,
                                    permissions: Dict[str, Any] = None,
                                    connection: Optional[asyncpg.Connection] = None) -> bool:
        """Grant access to credential for user"""
        try:
            query = """
                INSERT INTO credential_shares 
                (id, credential_id, shared_with_user_id, shared_by, created_at, 
                 expires_at, permissions, is_active)
                VALUES ($1, $2, $3, $4, NOW(), $5, $6, true)
                ON CONFLICT (credential_id, shared_with_user_id) DO UPDATE SET
                    shared_by = EXCLUDED.shared_by,
                    expires_at = EXCLUDED.expires_at,
                    permissions = EXCLUDED.permissions,
                    is_active = true
            """
            
            share_id = secrets.token_urlsafe(32)
            default_permissions = {"read": True, "write": False}
            if access_level in ['admin', 'owner']:
                default_permissions["write"] = True
            
            if connection:
                await connection.execute(query, share_id, credential_id, user_id, granted_by,
                                       expires_at, json.dumps(permissions or default_permissions))
            else:
                async with self.get_connection() as conn:
                    await conn.execute(query, share_id, credential_id, user_id, granted_by,
                                     expires_at, json.dumps(permissions or default_permissions))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to grant credential access: {str(e)}")
            return False
    
    async def check_user_access(self, user_id: str, credential_id: str,
                              required_permission: str = "read",
                              connection: Optional[asyncpg.Connection] = None) -> bool:
        """Check if user has required access to credential"""
        try:
            query = """
                SELECT 1 FROM credentials c
                LEFT JOIN credential_shares cs ON c.id = cs.credential_id
                LEFT JOIN user_roles ur ON (
                    ur.user_id = $1 AND ur.is_active = true AND
                    (ur.expires_at IS NULL OR ur.expires_at > NOW()) AND
                    (ur.organization_id = c.organization_id OR
                     ur.environment_id = c.environment_id OR
                     ur.project_id = c.project_id OR
                     ur.service_id = c.service_id OR
                     ur.role IN ('super_admin', 'security_admin', 'audit_admin'))
                )
                WHERE c.id = $2 AND c.is_active = true AND c.is_deleted = false AND (
                    c.owner_id = $1 OR
                    (cs.shared_with_user_id = $1 AND cs.is_active = true AND
                     (cs.expires_at IS NULL OR cs.expires_at > NOW()) AND
                     (cs.permissions->$3)::boolean = true) OR
                    ur.user_id IS NOT NULL
                )
                LIMIT 1
            """
            
            if connection:
                result = await connection.fetchval(query, user_id, credential_id, required_permission)
            else:
                async with self.get_connection() as conn:
                    result = await conn.fetchval(query, user_id, credential_id, required_permission)
            
            return result is not None
            
        except Exception as e:
            self.logger.error(f"Failed to check user access: {str(e)}")
            return False
    
    async def get_vault_statistics(self, connection: Optional[asyncpg.Connection] = None) -> Dict[str, Any]:
        """Get comprehensive vault statistics"""
        try:
            stats = {}
            
            queries = {
                'total_credentials': "SELECT COUNT(*) FROM credentials WHERE is_active = true AND is_deleted = false",
                'by_type': """
                    SELECT credential_type, COUNT(*) 
                    FROM credentials 
                    WHERE is_active = true AND is_deleted = false
                    GROUP BY credential_type
                """,
                'by_risk_level': """
                    SELECT risk_level, COUNT(*) 
                    FROM credentials 
                    WHERE is_active = true AND is_deleted = false
                    GROUP BY risk_level
                """,
                'expiring_soon': """
                    SELECT COUNT(*) FROM credentials 
                    WHERE is_active = true AND is_deleted = false 
                    AND expires_at IS NOT NULL AND expires_at <= NOW() + INTERVAL '30 days'
                """,
                'recent_activity': """
                    SELECT COUNT(*) FROM audit_log 
                    WHERE timestamp >= NOW() - INTERVAL '24 hours'
                """
            }
            
            if connection:
                conn = connection
            else:
                conn = await self.connection_pool.acquire()
            
            try:
                # Total credentials
                stats['total_credentials'] = await conn.fetchval(queries['total_credentials'])
                
                # By type
                type_rows = await conn.fetch(queries['by_type'])
                stats['by_type'] = {row['credential_type']: row['count'] for row in type_rows}
                
                # By risk level
                risk_rows = await conn.fetch(queries['by_risk_level'])
                stats['by_risk_level'] = {row['risk_level']: row['count'] for row in risk_rows}
                
                # Expiring soon
                stats['expiring_soon'] = await conn.fetchval(queries['expiring_soon'])
                
                # Recent activity
                stats['recent_activity'] = await conn.fetchval(queries['recent_activity'])
                
                stats['last_updated'] = datetime.utcnow().isoformat()
                
            finally:
                if not connection:
                    await self.connection_pool.release(conn)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get vault statistics: {str(e)}")
            return {}
    
    async def store_encryption_key(self, key_version: int, key_hash: str, 
                                 algorithm: str = "AES-256-GCM",
                                 expires_at: Optional[datetime] = None,
                                 hsm_key_id: Optional[str] = None,
                                 metadata: Dict[str, Any] = None,
                                 connection: Optional[asyncpg.Connection] = None) -> bool:
        """Store encryption key metadata"""
        try:
            query = """
                INSERT INTO encryption_keys 
                (id, key_version, key_hash, algorithm, created_at, expires_at, 
                 is_active, hsm_key_id, key_metadata)
                VALUES ($1, $2, $3, $4, NOW(), $5, true, $6, $7)
                ON CONFLICT (key_version) DO UPDATE SET
                    key_hash = EXCLUDED.key_hash,
                    algorithm = EXCLUDED.algorithm,
                    expires_at = EXCLUDED.expires_at,
                    hsm_key_id = EXCLUDED.hsm_key_id,
                    key_metadata = EXCLUDED.key_metadata
            """
            
            key_id = secrets.token_urlsafe(32)
            
            if connection:
                await connection.execute(query, key_id, key_version, key_hash, algorithm,
                                       expires_at, hsm_key_id, json.dumps(metadata or {}))
            else:
                async with self.get_connection() as conn:
                    await conn.execute(query, key_id, key_version, key_hash, algorithm,
                                     expires_at, hsm_key_id, json.dumps(metadata or {}))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store encryption key: {str(e)}")
            return False
    
    async def get_active_encryption_key(self, connection: Optional[asyncpg.Connection] = None) -> Optional[Tuple[int, str]]:
        """Get active encryption key version and hash"""
        try:
            query = """
                SELECT key_version, key_hash 
                FROM encryption_keys 
                WHERE is_active = true AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY key_version DESC
                LIMIT 1
            """
            
            if connection:
                row = await connection.fetchrow(query)
            else:
                async with self.get_connection() as conn:
                    row = await conn.fetchrow(query)
            
            if row:
                return (row['key_version'], row['key_hash'])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get active encryption key: {str(e)}")
            return None