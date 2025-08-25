"""
Encrypted Backup Manager for Credential Vault
Provides secure backup and restore capabilities with separate key management.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
import secrets
import hashlib
import gzip
import tarfile
import tempfile
import shutil
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import redis

from .database_manager import DatabaseManager
from .encryption_engine import EncryptionEngine
from .audit_manager import AuditManager, AuditEventType, AuditResult


class BackupType(Enum):
    """Types of backups"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    METADATA_ONLY = "metadata_only"


class BackupStatus(Enum):
    """Backup operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CORRUPTED = "corrupted"
    RESTORED = "restored"


class CompressionType(Enum):
    """Compression types for backups"""
    NONE = "none"
    GZIP = "gzip"
    BZIP2 = "bzip2"
    LZMA = "lzma"


@dataclass
class BackupMetadata:
    """Backup metadata"""
    backup_id: str
    backup_type: BackupType
    created_at: datetime
    created_by: str
    file_path: str
    file_size: int
    compressed_size: int
    compression_type: CompressionType
    encryption_algorithm: str
    key_version: int
    checksum: str
    status: BackupStatus
    credential_count: int
    includes_encryption_keys: bool = False
    retention_until: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RestoreOperation:
    """Restore operation tracking"""
    restore_id: str
    backup_id: str
    initiated_by: str
    initiated_at: datetime
    target_environment: str
    status: BackupStatus
    progress_percent: float = 0.0
    restored_credentials: int = 0
    total_credentials: int = 0
    errors: List[str] = field(default_factory=list)
    completed_at: Optional[datetime] = None


class BackupKeyManager:
    """Separate key management for backup encryption"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('backup', {}).get('key_management', {})
        self.key_storage_path = self.config.get('key_storage_path', 'data/backup_keys')
        self.key_rotation_days = self.config.get('key_rotation_days', 365)
        self.use_hsm = self.config.get('use_hsm', False)
        self.hsm_config = self.config.get('hsm_config', {})
        self.logger = logging.getLogger(__name__)
        
        # Ensure key storage directory exists
        os.makedirs(self.key_storage_path, exist_ok=True)
        
        # Current key version
        self.current_key_version = self._get_current_key_version()
    
    def _get_current_key_version(self) -> int:
        """Get current key version"""
        try:
            version_file = Path(self.key_storage_path) / 'current_version'
            if version_file.exists():
                return int(version_file.read_text().strip())
            return 1
        except Exception:
            return 1
    
    def _set_current_key_version(self, version: int) -> None:
        """Set current key version"""
        try:
            version_file = Path(self.key_storage_path) / 'current_version'
            version_file.write_text(str(version))
        except Exception as e:
            self.logger.error(f"Failed to set current key version: {str(e)}")
    
    async def generate_backup_key(self) -> Tuple[bytes, int]:
        """Generate new backup encryption key"""
        try:
            # Generate new key
            backup_key = secrets.token_bytes(32)  # 256-bit key
            key_version = self.current_key_version + 1
            
            if self.use_hsm:
                # Store in HSM (placeholder implementation)
                await self._store_key_in_hsm(backup_key, key_version)
            else:
                # Store encrypted key on disk
                await self._store_key_on_disk(backup_key, key_version)
            
            # Update current version
            self.current_key_version = key_version
            self._set_current_key_version(key_version)
            
            self.logger.info(f"Generated backup key version {key_version}")
            return backup_key, key_version
            
        except Exception as e:
            self.logger.error(f"Failed to generate backup key: {str(e)}")
            raise
    
    async def get_backup_key(self, key_version: int) -> Optional[bytes]:
        """Get backup key by version"""
        try:
            if self.use_hsm:
                return await self._get_key_from_hsm(key_version)
            else:
                return await self._get_key_from_disk(key_version)
                
        except Exception as e:
            self.logger.error(f"Failed to get backup key version {key_version}: {str(e)}")
            return None
    
    async def _store_key_on_disk(self, key: bytes, version: int) -> None:
        """Store encrypted key on disk"""
        try:
            # Derive key encryption key from master password (would be provided securely)
            master_password = self.config.get('master_password', 'default_master_password')
            salt = secrets.token_bytes(32)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            kek = kdf.derive(master_password.encode())
            
            # Encrypt the backup key
            fernet = Fernet(Fernet.generate_key())
            encrypted_key = fernet.encrypt(key)
            
            # Store key and metadata
            key_file = Path(self.key_storage_path) / f'backup_key_v{version}.enc'
            key_data = {
                'version': version,
                'encrypted_key': encrypted_key.hex(),
                'salt': salt.hex(),
                'created_at': datetime.utcnow().isoformat(),
                'algorithm': 'AES-256-GCM'
            }
            
            key_file.write_text(json.dumps(key_data))
            
        except Exception as e:
            self.logger.error(f"Failed to store key on disk: {str(e)}")
            raise
    
    async def _get_key_from_disk(self, version: int) -> Optional[bytes]:
        """Get encrypted key from disk"""
        try:
            key_file = Path(self.key_storage_path) / f'backup_key_v{version}.enc'
            if not key_file.exists():
                return None
            
            key_data = json.loads(key_file.read_text())
            
            # Derive key encryption key
            master_password = self.config.get('master_password', 'default_master_password')
            salt = bytes.fromhex(key_data['salt'])
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            kek = kdf.derive(master_password.encode())
            
            # Decrypt the backup key
            encrypted_key = bytes.fromhex(key_data['encrypted_key'])
            fernet = Fernet(kek)
            backup_key = fernet.decrypt(encrypted_key)
            
            return backup_key
            
        except Exception as e:
            self.logger.error(f"Failed to get key from disk: {str(e)}")
            return None
    
    async def _store_key_in_hsm(self, key: bytes, version: int) -> None:
        """Store key in Hardware Security Module (placeholder)"""
        # This would integrate with actual HSM APIs
        self.logger.info(f"Would store key version {version} in HSM")
    
    async def _get_key_from_hsm(self, version: int) -> Optional[bytes]:
        """Get key from Hardware Security Module (placeholder)"""
        # This would integrate with actual HSM APIs
        self.logger.info(f"Would retrieve key version {version} from HSM")
        return None
    
    async def rotate_backup_keys(self) -> bool:
        """Rotate backup encryption keys"""
        try:
            # Generate new key
            new_key, new_version = await self.generate_backup_key()
            
            # Mark old keys for retirement (but keep them for restore operations)
            # In production, you'd implement a key retirement schedule
            
            self.logger.info(f"Rotated backup keys to version {new_version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rotate backup keys: {str(e)}")
            return False


class BackupManager:
    """Comprehensive backup manager for vault data"""
    
    def __init__(self, config: Dict[str, Any], database_manager: DatabaseManager,
                 encryption_engine: EncryptionEngine, audit_manager: AuditManager):
        self.config = config
        self.database_manager = database_manager
        self.encryption_engine = encryption_engine
        self.audit_manager = audit_manager
        self.logger = logging.getLogger(__name__)
        
        # Backup configuration
        backup_config = config.get('vault', {}).get('backup', {})
        self.backup_storage_path = backup_config.get('storage_path', 'data/backups')
        self.retention_days = backup_config.get('retention_days', 90)
        self.compression_enabled = backup_config.get('compression_enabled', True)
        self.compression_type = CompressionType(backup_config.get('compression_type', 'gzip'))
        self.backup_schedule = backup_config.get('schedule', '0 2 * * *')  # Daily at 2 AM
        self.max_backup_size = backup_config.get('max_backup_size_mb', 1024)  # 1GB
        
        # Initialize key manager
        self.key_manager = BackupKeyManager(config)
        
        # Backup tracking
        self.active_backups: Dict[str, BackupMetadata] = {}
        self.active_restores: Dict[str, RestoreOperation] = {}
        
        # Ensure backup directory exists
        os.makedirs(self.backup_storage_path, exist_ok=True)
    
    async def initialize(self) -> bool:
        """Initialize backup manager"""
        try:
            # Load existing backup metadata
            await self._load_backup_metadata()
            
            # Start background tasks
            asyncio.create_task(self._backup_scheduler())
            asyncio.create_task(self._cleanup_old_backups())
            
            self.logger.info("Backup manager initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize backup manager: {str(e)}")
            return False
    
    async def create_backup(self, backup_type: BackupType, user_id: str,
                          include_encryption_keys: bool = False,
                          tags: List[str] = None) -> str:
        """Create encrypted backup"""
        backup_id = secrets.token_urlsafe(16)
        start_time = datetime.utcnow()
        
        try:
            # Create backup metadata
            backup_metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type=backup_type,
                created_at=start_time,
                created_by=user_id,
                file_path="",  # Will be set after creation
                file_size=0,
                compressed_size=0,
                compression_type=self.compression_type,
                encryption_algorithm="AES-256-GCM",
                key_version=self.key_manager.current_key_version,
                checksum="",
                status=BackupStatus.IN_PROGRESS,
                credential_count=0,
                includes_encryption_keys=include_encryption_keys,
                retention_until=start_time + timedelta(days=self.retention_days),
                tags=tags or []
            )
            
            self.active_backups[backup_id] = backup_metadata
            
            # Log audit event
            await self.audit_manager.log_event(
                AuditEventType.BACKUP, user_id, "create_backup",
                AuditResult.SUCCESS, None,
                metadata={
                    'backup_id': backup_id,
                    'backup_type': backup_type.value,
                    'include_encryption_keys': include_encryption_keys
                }
            )
            
            # Create backup in background
            asyncio.create_task(self._create_backup_async(backup_metadata))
            
            return backup_id
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {str(e)}")
            if backup_id in self.active_backups:
                self.active_backups[backup_id].status = BackupStatus.FAILED
            raise
    
    async def _create_backup_async(self, backup_metadata: BackupMetadata) -> None:
        """Create backup asynchronously"""
        try:
            # Get backup encryption key
            backup_key = await self.key_manager.get_backup_key(backup_metadata.key_version)
            if not backup_key:
                backup_key, key_version = await self.key_manager.generate_backup_key()
                backup_metadata.key_version = key_version
            
            # Create temporary directory for backup data
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Export vault data
                vault_data = await self._export_vault_data(
                    backup_metadata.backup_type,
                    backup_metadata.includes_encryption_keys
                )
                
                backup_metadata.credential_count = len(vault_data.get('credentials', []))
                
                # Write data to temporary file
                data_file = temp_path / 'vault_data.json'
                with data_file.open('w') as f:
                    json.dump(vault_data, f, indent=2, default=str)
                
                # Compress if enabled
                if self.compression_enabled:
                    compressed_file = await self._compress_backup(data_file, self.compression_type)
                    source_file = compressed_file
                else:
                    source_file = data_file
                
                # Encrypt backup
                encrypted_file = await self._encrypt_backup(source_file, backup_key)
                
                # Move to final location
                backup_filename = f"vault_backup_{backup_metadata.backup_id}_{backup_metadata.created_at.strftime('%Y%m%d_%H%M%S')}.enc"
                final_path = Path(self.backup_storage_path) / backup_filename
                shutil.move(str(encrypted_file), str(final_path))
                
                # Update metadata
                backup_metadata.file_path = str(final_path)
                backup_metadata.file_size = data_file.stat().st_size
                backup_metadata.compressed_size = final_path.stat().st_size
                backup_metadata.checksum = await self._calculate_checksum(final_path)
                backup_metadata.status = BackupStatus.COMPLETED
                
                # Save backup metadata
                await self._save_backup_metadata(backup_metadata)
                
                self.logger.info(f"Backup {backup_metadata.backup_id} completed successfully")
                
        except Exception as e:
            self.logger.error(f"Backup creation failed: {str(e)}")
            backup_metadata.status = BackupStatus.FAILED
            backup_metadata.metadata['error'] = str(e)
    
    async def _export_vault_data(self, backup_type: BackupType, 
                               include_encryption_keys: bool) -> Dict[str, Any]:
        """Export vault data for backup"""
        try:
            vault_data = {
                'backup_type': backup_type.value,
                'created_at': datetime.utcnow().isoformat(),
                'include_encryption_keys': include_encryption_keys,
                'credentials': [],
                'metadata': {},
                'audit_logs': []
            }
            
            # Export credentials based on backup type
            if backup_type == BackupType.FULL:
                # Export all credentials
                vault_data['credentials'] = await self._export_all_credentials()
                vault_data['audit_logs'] = await self._export_audit_logs()
                
            elif backup_type == BackupType.INCREMENTAL:
                # Export only changed credentials since last backup
                last_backup_time = await self._get_last_backup_time()
                vault_data['credentials'] = await self._export_changed_credentials(last_backup_time)
                
            elif backup_type == BackupType.METADATA_ONLY:
                # Export only metadata, no credential data
                vault_data['credentials'] = await self._export_credential_metadata()
            
            # Export encryption keys if requested
            if include_encryption_keys:
                vault_data['encryption_keys'] = await self._export_encryption_keys()
            
            # Export vault statistics
            vault_data['statistics'] = await self.database_manager.get_vault_statistics()
            
            return vault_data
            
        except Exception as e:
            self.logger.error(f"Failed to export vault data: {str(e)}")
            raise
    
    async def _export_all_credentials(self) -> List[Dict[str, Any]]:
        """Export all credentials"""
        try:
            # This would query the database for all credentials
            # For now, return placeholder data
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to export credentials: {str(e)}")
            return []
    
    async def _export_audit_logs(self, days: int = 30) -> List[Dict[str, Any]]:
        """Export audit logs"""
        try:
            # This would query the audit logs
            # For now, return placeholder data
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to export audit logs: {str(e)}")
            return []
    
    async def _export_changed_credentials(self, since: datetime) -> List[Dict[str, Any]]:
        """Export credentials changed since specified time"""
        try:
            # This would query for changed credentials
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to export changed credentials: {str(e)}")
            return []
    
    async def _export_credential_metadata(self) -> List[Dict[str, Any]]:
        """Export credential metadata only"""
        try:
            # This would export metadata without sensitive data
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to export credential metadata: {str(e)}")
            return []
    
    async def _export_encryption_keys(self) -> Dict[str, Any]:
        """Export encryption keys (highly sensitive)"""
        try:
            # This would export encryption key metadata
            # Actual keys would be encrypted with backup key
            return {'key_versions': [], 'current_version': self.encryption_engine.current_key_version}
            
        except Exception as e:
            self.logger.error(f"Failed to export encryption keys: {str(e)}")
            return {}
    
    async def _compress_backup(self, file_path: Path, compression_type: CompressionType) -> Path:
        """Compress backup file"""
        try:
            if compression_type == CompressionType.GZIP:
                compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
                with file_path.open('rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                return compressed_path
            
            # Add support for other compression types as needed
            return file_path
            
        except Exception as e:
            self.logger.error(f"Failed to compress backup: {str(e)}")
            return file_path
    
    async def _encrypt_backup(self, file_path: Path, backup_key: bytes) -> Path:
        """Encrypt backup file"""
        try:
            encrypted_path = file_path.with_suffix(file_path.suffix + '.enc')
            
            # Generate nonce for GCM
            nonce = secrets.token_bytes(12)
            
            # Create cipher
            cipher = Cipher(algorithms.AES(backup_key), modes.GCM(nonce))
            encryptor = cipher.encryptor()
            
            # Encrypt file
            with file_path.open('rb') as f_in:
                with encrypted_path.open('wb') as f_out:
                    # Write nonce first
                    f_out.write(nonce)
                    
                    # Encrypt and write data
                    while True:
                        chunk = f_in.read(8192)
                        if not chunk:
                            break
                        encrypted_chunk = encryptor.update(chunk)
                        f_out.write(encrypted_chunk)
                    
                    # Finalize and write tag
                    encryptor.finalize()
                    f_out.write(encryptor.tag)
            
            return encrypted_path
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt backup: {str(e)}")
            raise
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        try:
            sha256_hash = hashlib.sha256()
            with file_path.open('rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
            
        except Exception as e:
            self.logger.error(f"Failed to calculate checksum: {str(e)}")
            return ""
    
    async def restore_backup(self, backup_id: str, user_id: str, 
                           target_environment: str = "current") -> str:
        """Restore from encrypted backup"""
        restore_id = secrets.token_urlsafe(16)
        
        try:
            # Get backup metadata
            backup_metadata = await self._get_backup_metadata(backup_id)
            if not backup_metadata:
                raise ValueError(f"Backup {backup_id} not found")
            
            # Create restore operation
            restore_op = RestoreOperation(
                restore_id=restore_id,
                backup_id=backup_id,
                initiated_by=user_id,
                initiated_at=datetime.utcnow(),
                target_environment=target_environment,
                status=BackupStatus.IN_PROGRESS,
                total_credentials=backup_metadata.credential_count
            )
            
            self.active_restores[restore_id] = restore_op
            
            # Log audit event
            await self.audit_manager.log_event(
                AuditEventType.RESTORE, user_id, "restore_backup",
                AuditResult.SUCCESS, None,
                metadata={
                    'restore_id': restore_id,
                    'backup_id': backup_id,
                    'target_environment': target_environment
                }
            )
            
            # Start restore in background
            asyncio.create_task(self._restore_backup_async(restore_op, backup_metadata))
            
            return restore_id
            
        except Exception as e:
            self.logger.error(f"Failed to start restore: {str(e)}")
            if restore_id in self.active_restores:
                self.active_restores[restore_id].status = BackupStatus.FAILED
                self.active_restores[restore_id].errors.append(str(e))
            raise
    
    async def _restore_backup_async(self, restore_op: RestoreOperation, 
                                  backup_metadata: BackupMetadata) -> None:
        """Restore backup asynchronously"""
        try:
            # Get backup decryption key
            backup_key = await self.key_manager.get_backup_key(backup_metadata.key_version)
            if not backup_key:
                raise ValueError(f"Backup key version {backup_metadata.key_version} not found")
            
            # Verify backup integrity
            if not await self._verify_backup_integrity(backup_metadata):
                raise ValueError("Backup integrity verification failed")
            
            # Decrypt backup
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                decrypted_file = await self._decrypt_backup(
                    Path(backup_metadata.file_path), backup_key, temp_path
                )
                
                # Decompress if needed
                if backup_metadata.compression_type != CompressionType.NONE:
                    decompressed_file = await self._decompress_backup(
                        decrypted_file, backup_metadata.compression_type
                    )
                else:
                    decompressed_file = decrypted_file
                
                # Load vault data
                with decompressed_file.open('r') as f:
                    vault_data = json.load(f)
                
                # Restore credentials
                await self._restore_vault_data(vault_data, restore_op)
                
                restore_op.status = BackupStatus.COMPLETED
                restore_op.completed_at = datetime.utcnow()
                
                self.logger.info(f"Restore {restore_op.restore_id} completed successfully")
                
        except Exception as e:
            self.logger.error(f"Restore failed: {str(e)}")
            restore_op.status = BackupStatus.FAILED
            restore_op.errors.append(str(e))
    
    async def _decrypt_backup(self, encrypted_file: Path, backup_key: bytes, 
                            output_dir: Path) -> Path:
        """Decrypt backup file"""
        try:
            decrypted_file = output_dir / 'decrypted_backup'
            
            with encrypted_file.open('rb') as f_in:
                # Read nonce
                nonce = f_in.read(12)
                
                # Read encrypted data and tag
                encrypted_data = f_in.read()
                tag = encrypted_data[-16:]  # Last 16 bytes are the tag
                ciphertext = encrypted_data[:-16]
                
                # Create cipher
                cipher = Cipher(algorithms.AES(backup_key), modes.GCM(nonce, tag))
                decryptor = cipher.decryptor()
                
                # Decrypt data
                with decrypted_file.open('wb') as f_out:
                    f_out.write(decryptor.update(ciphertext) + decryptor.finalize())
            
            return decrypted_file
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt backup: {str(e)}")
            raise
    
    async def _decompress_backup(self, compressed_file: Path, 
                               compression_type: CompressionType) -> Path:
        """Decompress backup file"""
        try:
            if compression_type == CompressionType.GZIP:
                decompressed_file = compressed_file.with_suffix('')
                with gzip.open(compressed_file, 'rb') as f_in:
                    with decompressed_file.open('wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                return decompressed_file
            
            return compressed_file
            
        except Exception as e:
            self.logger.error(f"Failed to decompress backup: {str(e)}")
            return compressed_file
    
    async def _restore_vault_data(self, vault_data: Dict[str, Any], 
                                restore_op: RestoreOperation) -> None:
        """Restore vault data from backup"""
        try:
            credentials = vault_data.get('credentials', [])
            
            for i, credential_data in enumerate(credentials):
                try:
                    # Restore individual credential
                    await self._restore_credential(credential_data)
                    restore_op.restored_credentials += 1
                    restore_op.progress_percent = (i + 1) / len(credentials) * 100
                    
                except Exception as e:
                    restore_op.errors.append(f"Failed to restore credential {credential_data.get('id', 'unknown')}: {str(e)}")
            
            # Restore audit logs if present
            if 'audit_logs' in vault_data:
                await self._restore_audit_logs(vault_data['audit_logs'])
            
        except Exception as e:
            self.logger.error(f"Failed to restore vault data: {str(e)}")
            raise
    
    async def _restore_credential(self, credential_data: Dict[str, Any]) -> None:
        """Restore individual credential"""
        try:
            # This would restore the credential to the database
            # Implementation depends on the credential data structure
            pass
            
        except Exception as e:
            self.logger.error(f"Failed to restore credential: {str(e)}")
            raise
    
    async def _restore_audit_logs(self, audit_logs: List[Dict[str, Any]]) -> None:
        """Restore audit logs"""
        try:
            # This would restore audit logs to the database
            pass
            
        except Exception as e:
            self.logger.error(f"Failed to restore audit logs: {str(e)}")
    
    async def _verify_backup_integrity(self, backup_metadata: BackupMetadata) -> bool:
        """Verify backup file integrity"""
        try:
            backup_file = Path(backup_metadata.file_path)
            if not backup_file.exists():
                return False
            
            # Verify checksum
            current_checksum = await self._calculate_checksum(backup_file)
            return current_checksum == backup_metadata.checksum
            
        except Exception as e:
            self.logger.error(f"Failed to verify backup integrity: {str(e)}")
            return False
    
    async def list_backups(self, user_id: str) -> List[BackupMetadata]:
        """List available backups"""
        try:
            # This would query backup metadata from storage
            return list(self.active_backups.values())
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {str(e)}")
            return []
    
    async def get_backup_status(self, backup_id: str) -> Optional[BackupMetadata]:
        """Get backup status"""
        return self.active_backups.get(backup_id)
    
    async def get_restore_status(self, restore_id: str) -> Optional[RestoreOperation]:
        """Get restore operation status"""
        return self.active_restores.get(restore_id)
    
    async def delete_backup(self, backup_id: str, user_id: str) -> bool:
        """Delete backup file and metadata"""
        try:
            backup_metadata = await self._get_backup_metadata(backup_id)
            if not backup_metadata:
                return False
            
            # Delete backup file
            backup_file = Path(backup_metadata.file_path)
            if backup_file.exists():
                backup_file.unlink()
            
            # Remove from tracking
            if backup_id in self.active_backups:
                del self.active_backups[backup_id]
            
            # Log audit event
            await self.audit_manager.log_event(
                AuditEventType.DELETE, user_id, "delete_backup",
                AuditResult.SUCCESS, None,
                metadata={'backup_id': backup_id}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete backup: {str(e)}")
            return False
    
    async def _get_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """Get backup metadata"""
        return self.active_backups.get(backup_id)
    
    async def _save_backup_metadata(self, backup_metadata: BackupMetadata) -> None:
        """Save backup metadata"""
        try:
            metadata_file = Path(self.backup_storage_path) / f"{backup_metadata.backup_id}.metadata"
            with metadata_file.open('w') as f:
                json.dump(backup_metadata.__dict__, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Failed to save backup metadata: {str(e)}")
    
    async def _load_backup_metadata(self) -> None:
        """Load existing backup metadata"""
        try:
            backup_dir = Path(self.backup_storage_path)
            for metadata_file in backup_dir.glob('*.metadata'):
                try:
                    with metadata_file.open('r') as f:
                        metadata_dict = json.load(f)
                    
                    # Convert dict to BackupMetadata object
                    backup_metadata = BackupMetadata(**metadata_dict)
                    self.active_backups[backup_metadata.backup_id] = backup_metadata
                    
                except Exception as e:
                    self.logger.error(f"Failed to load metadata from {metadata_file}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Failed to load backup metadata: {str(e)}")
    
    async def _get_last_backup_time(self) -> datetime:
        """Get timestamp of last backup"""
        try:
            if not self.active_backups:
                return datetime.utcnow() - timedelta(days=365)  # Default to 1 year ago
            
            return max(backup.created_at for backup in self.active_backups.values())
            
        except Exception:
            return datetime.utcnow() - timedelta(days=365)
    
    async def _backup_scheduler(self) -> None:
        """Background task for scheduled backups"""
        while True:
            try:
                # This would implement cron-like scheduling
                # For now, just wait and check periodically
                await asyncio.sleep(3600)  # Check every hour
                
                # Check if it's time for a scheduled backup
                # Implementation would depend on cron parsing
                
            except Exception as e:
                self.logger.error(f"Backup scheduler error: {str(e)}")
                await asyncio.sleep(300)
    
    async def _cleanup_old_backups(self) -> None:
        """Background task to clean up old backups"""
        while True:
            try:
                current_time = datetime.utcnow()
                expired_backups = []
                
                for backup_id, backup_metadata in self.active_backups.items():
                    if (backup_metadata.retention_until and 
                        current_time > backup_metadata.retention_until):
                        expired_backups.append(backup_id)
                
                for backup_id in expired_backups:
                    await self.delete_backup(backup_id, "system")
                    self.logger.info(f"Cleaned up expired backup {backup_id}")
                
                await asyncio.sleep(86400)  # Check daily
                
            except Exception as e:
                self.logger.error(f"Backup cleanup error: {str(e)}")
                await asyncio.sleep(3600)
    
    async def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup system statistics"""
        try:
            total_backups = len(self.active_backups)
            total_size = sum(backup.compressed_size for backup in self.active_backups.values())
            
            by_type = {}
            by_status = {}
            
            for backup in self.active_backups.values():
                by_type[backup.backup_type.value] = by_type.get(backup.backup_type.value, 0) + 1
                by_status[backup.status.value] = by_status.get(backup.status.value, 0) + 1
            
            return {
                'total_backups': total_backups,
                'total_size_bytes': total_size,
                'by_type': by_type,
                'by_status': by_status,
                'active_restores': len(self.active_restores),
                'key_version': self.key_manager.current_key_version,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get backup statistics: {str(e)}")
            return {'error': str(e)}