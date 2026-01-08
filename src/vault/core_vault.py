"""
Core Credential Vault Implementation
Secure, encrypted credential storage system with hierarchical organization.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
import hashlib
import secrets
import sqlite3
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import redis


class CredentialType(Enum):
    """Types of credentials that can be stored"""
    PASSWORD = "password"
    API_KEY = "api_key"
    CERTIFICATE = "certificate"
    SSH_KEY = "ssh_key"
    TOKEN = "token"
    DATABASE_CONNECTION = "database_connection"
    OAUTH_CREDENTIALS = "oauth_credentials"
    ENCRYPTION_KEY = "encryption_key"
    SIGNING_KEY = "signing_key"
    WEBHOOK_SECRET = "webhook_secret"


class AccessLevel(Enum):
    """Access levels for credentials"""
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"
    OWNER = "owner"
    EMERGENCY = "emergency"


class CredentialStatus(Enum):
    """Status of credentials"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    COMPROMISED = "compromised"
    PENDING_ROTATION = "pending_rotation"
    ARCHIVED = "archived"


@dataclass
class CredentialMetadata:
    """Metadata for stored credentials"""
    credential_id: str
    name: str
    description: str
    credential_type: CredentialType
    environment: str
    service: str
    project: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    last_accessed: datetime
    expires_at: Optional[datetime]
    rotation_schedule: Optional[str]
    status: CredentialStatus
    tags: List[str] = field(default_factory=list)
    access_restrictions: Dict[str, Any] = field(default_factory=dict)
    compliance_labels: List[str] = field(default_factory=list)
    audit_required: bool = False
    emergency_access: bool = False


@dataclass
class EncryptedCredential:
    """Encrypted credential data structure"""
    credential_id: str
    encrypted_data: bytes
    encryption_algorithm: str
    key_derivation_method: str
    salt: bytes
    nonce: bytes
    tag: bytes
    key_version: int
    created_at: datetime
    updated_at: datetime


@dataclass
class VaultAccess:
    """Access control for vault operations"""
    user_id: str
    credential_id: str
    access_level: AccessLevel
    granted_by: str
    granted_at: datetime
    expires_at: Optional[datetime]
    ip_restrictions: List[str] = field(default_factory=list)
    time_restrictions: Dict[str, Any] = field(default_factory=dict)
    purpose: Optional[str] = None


class CoreCredentialVault:
    """Core credential vault with secure encryption and hierarchical organization"""
    
    def __init__(self, config: Dict[str, Any], redis_client: Optional[redis.Redis]):
        self.config = config
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        
        # Vault configuration
        self.vault_config = config.get('vault', {})
        self.db_path = self.vault_config.get('database_path', 'data/vault.db')
        self.encryption_config = self.vault_config.get('encryption', {})
        
        # Encryption settings
        self.key_derivation_iterations = self.encryption_config.get('pbkdf2_iterations', 100000)
        self.scrypt_n = self.encryption_config.get('scrypt_n', 2**14)
        self.scrypt_r = self.encryption_config.get('scrypt_r', 8)
        self.scrypt_p = self.encryption_config.get('scrypt_p', 1)
        
        # Master key management
        self.master_key: Optional[bytes] = None
        self.key_version = 1
        
        # Initialize database
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the vault database schema"""
        try:
            # Ensure data directory exists
            db_dir = os.path.dirname(self.db_path)
            if db_dir:  # Only create directory if path has a directory component
                os.makedirs(db_dir, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Credential metadata table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS credential_metadata (
                        credential_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        credential_type TEXT NOT NULL,
                        environment TEXT NOT NULL,
                        service TEXT NOT NULL,
                        project TEXT NOT NULL,
                        owner_id TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        last_accessed TIMESTAMP,
                        expires_at TIMESTAMP,
                        rotation_schedule TEXT,
                        status TEXT NOT NULL DEFAULT 'active',
                        tags TEXT,
                        access_restrictions TEXT,
                        compliance_labels TEXT,
                        audit_required BOOLEAN DEFAULT FALSE,
                        emergency_access BOOLEAN DEFAULT FALSE
                    )
                ''')
                
                # Encrypted credentials table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS encrypted_credentials (
                        credential_id TEXT PRIMARY KEY,
                        encrypted_data BLOB NOT NULL,
                        encryption_algorithm TEXT NOT NULL,
                        key_derivation_method TEXT NOT NULL,
                        salt BLOB NOT NULL,
                        nonce BLOB NOT NULL,
                        tag BLOB NOT NULL,
                        key_version INTEGER NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        FOREIGN KEY (credential_id) REFERENCES credential_metadata (credential_id)
                    )
                ''')
                
                # Access control table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS vault_access (
                        access_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        credential_id TEXT NOT NULL,
                        access_level TEXT NOT NULL,
                        granted_by TEXT NOT NULL,
                        granted_at TIMESTAMP NOT NULL,
                        expires_at TIMESTAMP,
                        ip_restrictions TEXT,
                        time_restrictions TEXT,
                        purpose TEXT,
                        FOREIGN KEY (credential_id) REFERENCES credential_metadata (credential_id)
                    )
                ''')
                
                # Audit log table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS vault_audit_log (
                        audit_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        credential_id TEXT,
                        action TEXT NOT NULL,
                        details TEXT,
                        ip_address TEXT,
                        user_agent TEXT,
                        timestamp TIMESTAMP NOT NULL,
                        success BOOLEAN NOT NULL
                    )
                ''')
                
                # Key rotation history
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS key_rotation_history (
                        rotation_id TEXT PRIMARY KEY,
                        credential_id TEXT NOT NULL,
                        old_key_version INTEGER,
                        new_key_version INTEGER NOT NULL,
                        rotated_by TEXT NOT NULL,
                        rotated_at TIMESTAMP NOT NULL,
                        reason TEXT,
                        FOREIGN KEY (credential_id) REFERENCES credential_metadata (credential_id)
                    )
                ''')
                
                # Create indexes for performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_credential_environment ON credential_metadata (environment)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_credential_service ON credential_metadata (service)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_credential_project ON credential_metadata (project)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_credential_owner ON credential_metadata (owner_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_credential_type ON credential_metadata (credential_type)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_credential_status ON credential_metadata (status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_access_user ON vault_access (user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_access_credential ON vault_access (credential_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_user ON vault_audit_log (user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON vault_audit_log (timestamp)')
                
                conn.commit()
                self.logger.info("Vault database initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize vault database: {str(e)}")
            raise
    
    def derive_key_from_password(self, password: str, salt: bytes, method: str = "scrypt") -> bytes:
        """Derive encryption key from master password using secure key derivation"""
        try:
            password_bytes = password.encode('utf-8')
            
            if method == "scrypt":
                kdf = Scrypt(
                    length=32,
                    salt=salt,
                    n=self.scrypt_n,
                    r=self.scrypt_r,
                    p=self.scrypt_p
                )
            elif method == "pbkdf2":
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=self.key_derivation_iterations
                )
            else:
                raise ValueError(f"Unsupported key derivation method: {method}")
            
            return kdf.derive(password_bytes)
            
        except Exception as e:
            self.logger.error(f"Key derivation failed: {str(e)}")
            raise
    
    def encrypt_credential_data(self, data: Dict[str, Any], master_password: str) -> EncryptedCredential:
        """Encrypt credential data using AES-256-GCM"""
        try:
            # Generate unique salt and nonce for this credential
            salt = secrets.token_bytes(32)
            nonce = secrets.token_bytes(12)  # GCM nonce
            
            # Derive encryption key
            key = self.derive_key_from_password(master_password, salt, "scrypt")
            
            # Serialize credential data
            data_json = json.dumps(data, default=str)
            data_bytes = data_json.encode('utf-8')
            
            # Encrypt using AES-256-GCM
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce)
            )
            encryptor = cipher.encryptor()
            encrypted_data = encryptor.update(data_bytes) + encryptor.finalize()
            
            return EncryptedCredential(
                credential_id=data.get('credential_id', ''),
                encrypted_data=encrypted_data,
                encryption_algorithm="AES-256-GCM",
                key_derivation_method="scrypt",
                salt=salt,
                nonce=nonce,
                tag=encryptor.tag,
                key_version=self.key_version,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Credential encryption failed: {str(e)}")
            raise
    
    def decrypt_credential_data(self, encrypted_cred: EncryptedCredential, master_password: str) -> Dict[str, Any]:
        """Decrypt credential data"""
        try:
            # Derive decryption key
            key = self.derive_key_from_password(master_password, encrypted_cred.salt, encrypted_cred.key_derivation_method)
            
            # Decrypt using AES-256-GCM
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(encrypted_cred.nonce, encrypted_cred.tag)
            )
            decryptor = cipher.decryptor()
            decrypted_data = decryptor.update(encrypted_cred.encrypted_data) + decryptor.finalize()
            
            # Deserialize credential data
            data_json = decrypted_data.decode('utf-8')
            return json.loads(data_json)
            
        except Exception as e:
            self.logger.error(f"Credential decryption failed: {str(e)}")
            raise
    
    async def store_credential(self, metadata: CredentialMetadata, credential_data: Dict[str, Any], 
                             master_password: str, user_id: str) -> bool:
        """Store encrypted credential with metadata"""
        try:
            # Encrypt credential data
            encrypted_cred = self.encrypt_credential_data(credential_data, master_password)
            encrypted_cred.credential_id = metadata.credential_id
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Store metadata
                cursor.execute('''
                    INSERT OR REPLACE INTO credential_metadata 
                    (credential_id, name, description, credential_type, environment, service, project,
                     owner_id, created_at, updated_at, last_accessed, expires_at, rotation_schedule,
                     status, tags, access_restrictions, compliance_labels, audit_required, emergency_access)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metadata.credential_id, metadata.name, metadata.description,
                    metadata.credential_type.value, metadata.environment, metadata.service,
                    metadata.project, metadata.owner_id, metadata.created_at, metadata.updated_at,
                    metadata.last_accessed, metadata.expires_at, metadata.rotation_schedule,
                    metadata.status.value, json.dumps(metadata.tags),
                    json.dumps(metadata.access_restrictions), json.dumps(metadata.compliance_labels),
                    metadata.audit_required, metadata.emergency_access
                ))
                
                # Store encrypted credential
                cursor.execute('''
                    INSERT OR REPLACE INTO encrypted_credentials
                    (credential_id, encrypted_data, encryption_algorithm, key_derivation_method,
                     salt, nonce, tag, key_version, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    encrypted_cred.credential_id, encrypted_cred.encrypted_data,
                    encrypted_cred.encryption_algorithm, encrypted_cred.key_derivation_method,
                    encrypted_cred.salt, encrypted_cred.nonce, encrypted_cred.tag,
                    encrypted_cred.key_version, encrypted_cred.created_at, encrypted_cred.updated_at
                ))
                
                conn.commit()
            
            # Log audit event (SECURITY: Only log metadata, NEVER log credential_data)
            await self._log_audit_event(user_id, metadata.credential_id, "store_credential",
                                      {"credential_type": metadata.credential_type.value}, True)
            
            # Cache metadata in Redis for performance
            if self.redis:
                await self._cache_credential_metadata(metadata)
            
            self.logger.info(f"Credential {metadata.credential_id} stored successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store credential: {str(e)}")
            await self._log_audit_event(user_id, metadata.credential_id, "store_credential", 
                                      {"error": str(e)}, False)
            return False
    
    async def retrieve_credential(self, credential_id: str, master_password: str, 
                                user_id: str) -> Optional[Tuple[CredentialMetadata, Dict[str, Any]]]:
        """Retrieve and decrypt credential"""
        try:
            # Check access permissions
            if not await self._check_access_permission(user_id, credential_id, AccessLevel.VIEWER):
                await self._log_audit_event(user_id, credential_id, "retrieve_credential_denied", 
                                          {"reason": "insufficient_permissions"}, False)
                return None
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get metadata
                cursor.execute('''
                    SELECT * FROM credential_metadata WHERE credential_id = ?
                ''', (credential_id,))
                
                metadata_row = cursor.fetchone()
                if not metadata_row:
                    return None
                
                # Get encrypted credential
                cursor.execute('''
                    SELECT * FROM encrypted_credentials WHERE credential_id = ?
                ''', (credential_id,))
                
                encrypted_row = cursor.fetchone()
                if not encrypted_row:
                    return None
                
                # Parse metadata
                metadata = CredentialMetadata(
                    credential_id=metadata_row[0],
                    name=metadata_row[1],
                    description=metadata_row[2],
                    credential_type=CredentialType(metadata_row[3]),
                    environment=metadata_row[4],
                    service=metadata_row[5],
                    project=metadata_row[6],
                    owner_id=metadata_row[7],
                    created_at=datetime.fromisoformat(metadata_row[8]),
                    updated_at=datetime.fromisoformat(metadata_row[9]),
                    last_accessed=datetime.fromisoformat(metadata_row[10]) if metadata_row[10] else None,
                    expires_at=datetime.fromisoformat(metadata_row[11]) if metadata_row[11] else None,
                    rotation_schedule=metadata_row[12],
                    status=CredentialStatus(metadata_row[13]),
                    tags=json.loads(metadata_row[14]) if metadata_row[14] else [],
                    access_restrictions=json.loads(metadata_row[15]) if metadata_row[15] else {},
                    compliance_labels=json.loads(metadata_row[16]) if metadata_row[16] else [],
                    audit_required=bool(metadata_row[17]),
                    emergency_access=bool(metadata_row[18])
                )
                
                # Parse encrypted credential
                encrypted_cred = EncryptedCredential(
                    credential_id=encrypted_row[0],
                    encrypted_data=encrypted_row[1],
                    encryption_algorithm=encrypted_row[2],
                    key_derivation_method=encrypted_row[3],
                    salt=encrypted_row[4],
                    nonce=encrypted_row[5],
                    tag=encrypted_row[6],
                    key_version=encrypted_row[7],
                    created_at=datetime.fromisoformat(encrypted_row[8]),
                    updated_at=datetime.fromisoformat(encrypted_row[9])
                )
                
                # Decrypt credential data (SECURITY: DO NOT LOG - contains plaintext passwords/secrets)
                credential_data = self.decrypt_credential_data(encrypted_cred, master_password)

                # Update last accessed time
                cursor.execute('''
                    UPDATE credential_metadata SET last_accessed = ? WHERE credential_id = ?
                ''', (datetime.utcnow(), credential_id))
                conn.commit()

                # Log audit event (SECURITY: Only log metadata, NEVER log decrypted credential_data)
                await self._log_audit_event(user_id, credential_id, "retrieve_credential",
                                          {"credential_type": metadata.credential_type.value}, True)
                
                return metadata, credential_data
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve credential: {str(e)}")
            await self._log_audit_event(user_id, credential_id, "retrieve_credential", 
                                      {"error": str(e)}, False)
            return None
    
    async def list_credentials(self, user_id: str, filters: Dict[str, Any] = None) -> List[CredentialMetadata]:
        """List credentials accessible to user with optional filters"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build query with filters
                query = '''
                    SELECT cm.* FROM credential_metadata cm
                    LEFT JOIN vault_access va ON cm.credential_id = va.credential_id
                    WHERE (cm.owner_id = ? OR va.user_id = ?)
                '''
                params = [user_id, user_id]
                
                if filters:
                    if 'environment' in filters:
                        query += ' AND cm.environment = ?'
                        params.append(filters['environment'])
                    if 'service' in filters:
                        query += ' AND cm.service = ?'
                        params.append(filters['service'])
                    if 'project' in filters:
                        query += ' AND cm.project = ?'
                        params.append(filters['project'])
                    if 'credential_type' in filters:
                        query += ' AND cm.credential_type = ?'
                        params.append(filters['credential_type'])
                    if 'status' in filters:
                        query += ' AND cm.status = ?'
                        params.append(filters['status'])
                
                query += ' GROUP BY cm.credential_id ORDER BY cm.updated_at DESC'
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                credentials = []
                for row in rows:
                    metadata = CredentialMetadata(
                        credential_id=row[0],
                        name=row[1],
                        description=row[2],
                        credential_type=CredentialType(row[3]),
                        environment=row[4],
                        service=row[5],
                        project=row[6],
                        owner_id=row[7],
                        created_at=datetime.fromisoformat(row[8]),
                        updated_at=datetime.fromisoformat(row[9]),
                        last_accessed=datetime.fromisoformat(row[10]) if row[10] else None,
                        expires_at=datetime.fromisoformat(row[11]) if row[11] else None,
                        rotation_schedule=row[12],
                        status=CredentialStatus(row[13]),
                        tags=json.loads(row[14]) if row[14] else [],
                        access_restrictions=json.loads(row[15]) if row[15] else {},
                        compliance_labels=json.loads(row[16]) if row[16] else [],
                        audit_required=bool(row[17]),
                        emergency_access=bool(row[18])
                    )
                    credentials.append(metadata)
                
                return credentials
                
        except Exception as e:
            self.logger.error(f"Failed to list credentials: {str(e)}")
            return []
    
    async def grant_access(self, credential_id: str, user_id: str, access_level: AccessLevel,
                          granted_by: str, expires_at: Optional[datetime] = None,
                          ip_restrictions: List[str] = None, purpose: str = None) -> bool:
        """Grant access to a credential for a user"""
        try:
            access_id = secrets.token_urlsafe(32)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO vault_access
                    (access_id, user_id, credential_id, access_level, granted_by, granted_at,
                     expires_at, ip_restrictions, time_restrictions, purpose)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    access_id, user_id, credential_id, access_level.value, granted_by,
                    datetime.utcnow(), expires_at, json.dumps(ip_restrictions or []),
                    json.dumps({}), purpose
                ))
                
                conn.commit()
            
            # Log audit event
            await self._log_audit_event(granted_by, credential_id, "grant_access",
                                      {"target_user": user_id, "access_level": access_level.value}, True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to grant access: {str(e)}")
            return False
    
    async def _check_access_permission(self, user_id: str, credential_id: str, 
                                     required_level: AccessLevel) -> bool:
        """Check if user has required access level for credential"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if user is owner
                cursor.execute('''
                    SELECT owner_id FROM credential_metadata WHERE credential_id = ?
                ''', (credential_id,))
                
                owner_row = cursor.fetchone()
                if owner_row and owner_row[0] == user_id:
                    return True
                
                # Check explicit access grants
                cursor.execute('''
                    SELECT access_level, expires_at FROM vault_access 
                    WHERE user_id = ? AND credential_id = ? AND (expires_at IS NULL OR expires_at > ?)
                ''', (user_id, credential_id, datetime.utcnow()))
                
                access_row = cursor.fetchone()
                if access_row:
                    user_level = AccessLevel(access_row[0])
                    # Simple access level hierarchy check
                    level_hierarchy = {
                        AccessLevel.VIEWER: 1,
                        AccessLevel.OPERATOR: 2,
                        AccessLevel.ADMIN: 3,
                        AccessLevel.OWNER: 4,
                        AccessLevel.EMERGENCY: 5
                    }
                    return level_hierarchy.get(user_level, 0) >= level_hierarchy.get(required_level, 0)
                
                return False
                
        except Exception as e:
            self.logger.error(f"Access permission check failed: {str(e)}")
            return False
    
    async def _log_audit_event(self, user_id: str, credential_id: Optional[str], action: str,
                             details: Dict[str, Any], success: bool, ip_address: str = None,
                             user_agent: str = None):
        """
        Log audit event

        SECURITY: The details dict MUST contain only metadata (IDs, types, timestamps).
        NEVER include credential_data, passwords, API keys, decrypted values, or encryption artifacts.
        Audit logs are stored in plaintext and may be backed up, replicated, and archived.

        See docs/audit-log-security.md for safe vs unsafe patterns.
        """
        try:
            audit_id = secrets.token_urlsafe(32)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO vault_audit_log
                    (audit_id, user_id, credential_id, action, details, ip_address, user_agent, timestamp, success)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    audit_id, user_id, credential_id, action, json.dumps(details),
                    ip_address, user_agent, datetime.utcnow(), success
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {str(e)}")
    
    async def _cache_credential_metadata(self, metadata: CredentialMetadata):
        """Cache credential metadata in Redis for performance"""
        try:
            if not self.redis:
                return
                
            cache_key = f"vault:metadata:{metadata.credential_id}"
            cache_data = {
                'name': metadata.name,
                'credential_type': metadata.credential_type.value,
                'environment': metadata.environment,
                'service': metadata.service,
                'project': metadata.project,
                'status': metadata.status.value,
                'updated_at': metadata.updated_at.isoformat()
            }
            
            self.redis.hset(cache_key, mapping=cache_data)
            self.redis.expire(cache_key, 3600)  # 1 hour TTL
            
        except Exception as e:
            self.logger.error(f"Failed to cache metadata: {str(e)}")
    
    async def get_vault_statistics(self) -> Dict[str, Any]:
        """Get comprehensive vault statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total credentials
                cursor.execute('SELECT COUNT(*) FROM credential_metadata')
                total_credentials = cursor.fetchone()[0]
                
                # Credentials by type
                cursor.execute('''
                    SELECT credential_type, COUNT(*) FROM credential_metadata 
                    GROUP BY credential_type
                ''')
                by_type = dict(cursor.fetchall())
                
                # Credentials by environment
                cursor.execute('''
                    SELECT environment, COUNT(*) FROM credential_metadata 
                    GROUP BY environment
                ''')
                by_environment = dict(cursor.fetchall())
                
                # Credentials by status
                cursor.execute('''
                    SELECT status, COUNT(*) FROM credential_metadata 
                    GROUP BY status
                ''')
                by_status = dict(cursor.fetchall())
                
                # Expiring credentials (next 30 days)
                cursor.execute('''
                    SELECT COUNT(*) FROM credential_metadata 
                    WHERE expires_at IS NOT NULL AND expires_at <= ?
                ''', (datetime.utcnow() + timedelta(days=30),))
                expiring_soon = cursor.fetchone()[0]
                
                # Recent activity (last 24 hours)
                cursor.execute('''
                    SELECT COUNT(*) FROM vault_audit_log 
                    WHERE timestamp >= ?
                ''', (datetime.utcnow() - timedelta(hours=24),))
                recent_activity = cursor.fetchone()[0]
                
                return {
                    'total_credentials': total_credentials,
                    'by_type': by_type,
                    'by_environment': by_environment,
                    'by_status': by_status,
                    'expiring_soon': expiring_soon,
                    'recent_activity': recent_activity,
                    'last_updated': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get vault statistics: {str(e)}")
            return {}