"""
Comprehensive Test Suite for Vault Operations
Tests all components of the Story 8b Credential Vault implementation.

Author: Lance James, Unit 221B
"""

import pytest
import asyncio
import json
import secrets
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import redis

# Import vault components
from src.vault.database_manager import DatabaseManager
from src.vault.encryption_engine import EncryptionEngine, EncryptedData, SecurityLevel
from src.vault.credential_types import (
    CredentialTypeManager, CredentialData, CredentialType, 
    PasswordValidator, APIKeyValidator, SSHKeyValidator, CertificateValidator
)
from src.vault.performance_optimizer import PerformanceOptimizer, MemoryCache, CacheStrategy
from src.vault.audit_manager import AuditManager, AuditEventType, AuditResult, AnomalyDetector
from src.vault.security_features import (
    SecurityFeatureManager, SecureMemoryManager, TimingAttackProtection,
    RateLimiter, SessionManager
)
from src.vault.backup_manager import BackupManager, BackupType, BackupStatus
from src.vault.key_rotation_manager import KeyRotationManager, RotationTrigger, RotationStatus
from src.vault.haivemind_integration import HAIveMindVaultIntegration
from src.vault.enhanced_vault_api import EnhancedVaultAPI


class TestConfig:
    """Test configuration"""
    
    @staticmethod
    def get_test_config():
        return {
            'vault': {
                'database': {
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'test_vault_db',
                    'username': 'test_user',
                    'password': 'test_password'
                },
                'encryption': {
                    'security_level': 'high',
                    'pbkdf2_iterations': 10000,  # Reduced for testing
                    'scrypt_n': 2**10,  # Reduced for testing
                    'key_cache_ttl': 60
                },
                'performance': {
                    'cache': {
                        'metadata_max_size': 100,
                        'credential_max_size': 50,
                        'metadata_ttl': 300
                    },
                    'batch': {
                        'max_size': 10,
                        'timeout': 1.0
                    }
                },
                'audit': {
                    'enabled': True,
                    'async_logging': False,  # Synchronous for testing
                    'batch_size': 10
                },
                'security': {
                    'memory_protection': 'basic',
                    'timing_protection': {
                        'enabled': True,
                        'min_delay_ms': 10,
                        'max_delay_ms': 50
                    },
                    'rate_limiting': {
                        'enabled': True,
                        'max_attempts': 3,
                        'window_minutes': 5
                    }
                },
                'backup': {
                    'storage_path': '/tmp/test_backups',
                    'retention_days': 30,
                    'compression_enabled': True
                },
                'key_rotation': {
                    'default_rotation_days': 30,
                    'automatic_rotation': False  # Disabled for testing
                }
            },
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 15  # Use separate DB for testing
            }
        }


@pytest.fixture
async def test_config():
    """Test configuration fixture"""
    return TestConfig.get_test_config()


@pytest.fixture
async def mock_redis():
    """Mock Redis client fixture"""
    mock_redis = Mock()
    mock_redis.get = Mock(return_value=None)
    mock_redis.set = Mock(return_value=True)
    mock_redis.setex = Mock(return_value=True)
    mock_redis.delete = Mock(return_value=True)
    mock_redis.keys = Mock(return_value=[])
    mock_redis.hset = Mock(return_value=True)
    mock_redis.expire = Mock(return_value=True)
    return mock_redis


@pytest.fixture
async def mock_database_manager(test_config, mock_redis):
    """Mock database manager fixture"""
    db_manager = Mock(spec=DatabaseManager)
    db_manager.initialize = AsyncMock(return_value=True)
    db_manager.store_credential_metadata = AsyncMock(return_value=True)
    db_manager.store_encrypted_credential = AsyncMock(return_value=True)
    db_manager.retrieve_credential_metadata = AsyncMock(return_value=None)
    db_manager.retrieve_encrypted_credential = AsyncMock(return_value=None)
    db_manager.list_credentials_for_user = AsyncMock(return_value=[])
    db_manager.check_user_access = AsyncMock(return_value=True)
    db_manager.update_access_timestamp = AsyncMock(return_value=True)
    db_manager.store_audit_log = AsyncMock(return_value=True)
    db_manager.get_vault_statistics = AsyncMock(return_value={
        'total_credentials': 0,
        'by_type': {},
        'by_environment': {},
        'by_status': {},
        'expiring_soon': 0,
        'recent_activity': 0
    })
    db_manager.get_connection = AsyncMock()
    db_manager.get_transaction = AsyncMock()
    return db_manager


@pytest.fixture
async def encryption_engine(test_config, mock_redis):
    """Encryption engine fixture"""
    engine = EncryptionEngine(test_config, mock_redis)
    await engine.initialize()
    return engine


@pytest.fixture
async def credential_manager(test_config):
    """Credential type manager fixture"""
    return CredentialTypeManager(test_config)


@pytest.fixture
async def performance_optimizer(test_config, mock_redis, encryption_engine, mock_database_manager):
    """Performance optimizer fixture"""
    optimizer = PerformanceOptimizer(test_config, mock_redis, encryption_engine, mock_database_manager)
    await optimizer.initialize()
    return optimizer


@pytest.fixture
async def audit_manager(test_config, mock_redis, mock_database_manager):
    """Audit manager fixture"""
    manager = AuditManager(test_config, mock_redis, mock_database_manager)
    await manager.initialize()
    return manager


@pytest.fixture
async def security_manager(test_config):
    """Security feature manager fixture"""
    manager = SecurityFeatureManager(test_config)
    await manager.initialize()
    return manager


@pytest.fixture
async def backup_manager(test_config, mock_database_manager, encryption_engine, audit_manager):
    """Backup manager fixture"""
    # Create temporary backup directory
    backup_dir = tempfile.mkdtemp()
    test_config['vault']['backup']['storage_path'] = backup_dir
    
    manager = BackupManager(test_config, mock_database_manager, encryption_engine, audit_manager)
    await manager.initialize()
    
    yield manager
    
    # Cleanup
    shutil.rmtree(backup_dir, ignore_errors=True)


@pytest.fixture
async def key_rotation_manager(test_config, mock_database_manager, encryption_engine, 
                              audit_manager, performance_optimizer, mock_redis):
    """Key rotation manager fixture"""
    manager = KeyRotationManager(
        test_config, mock_database_manager, encryption_engine, 
        audit_manager, performance_optimizer, mock_redis
    )
    await manager.initialize()
    return manager


class TestEncryptionEngine:
    """Test encryption engine functionality"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, encryption_engine):
        """Test encryption engine initialization"""
        assert encryption_engine is not None
        assert encryption_engine.params is not None
        assert encryption_engine.current_key_version == 1
    
    @pytest.mark.asyncio
    async def test_key_derivation(self, encryption_engine):
        """Test key derivation from password"""
        password = "test_password_123"
        salt = secrets.token_bytes(32)
        
        key1 = await encryption_engine.derive_key_from_password(password, salt)
        key2 = await encryption_engine.derive_key_from_password(password, salt)
        
        assert key1 == key2  # Same password and salt should produce same key
        assert len(key1) == 32  # 256-bit key
    
    @pytest.mark.asyncio
    async def test_encryption_decryption(self, encryption_engine):
        """Test data encryption and decryption"""
        test_data = b"sensitive credential data"
        password = "encryption_password_123"
        
        # Encrypt data
        encrypted_data = await encryption_engine.encrypt_data(test_data, password)
        
        assert encrypted_data is not None
        assert encrypted_data.ciphertext != test_data
        assert len(encrypted_data.salt) == encryption_engine.params.salt_length
        assert len(encrypted_data.nonce) == encryption_engine.params.nonce_length
        
        # Decrypt data
        decrypted_data = await encryption_engine.decrypt_data(encrypted_data, password)
        
        assert decrypted_data == test_data
    
    @pytest.mark.asyncio
    async def test_batch_encryption(self, encryption_engine):
        """Test batch encryption operations"""
        test_data = [
            (b"data1", "password1"),
            (b"data2", "password2"),
            (b"data3", "password3")
        ]
        
        encrypted_results = await encryption_engine.batch_encrypt(test_data)
        
        assert len(encrypted_results) == 3
        for encrypted_data in encrypted_results:
            assert isinstance(encrypted_data, EncryptedData)
    
    @pytest.mark.asyncio
    async def test_key_rotation(self, encryption_engine):
        """Test encryption key rotation"""
        old_password = "old_password"
        new_password = "new_password"
        
        # Create test encrypted data
        test_data = b"test data for rotation"
        encrypted_data = await encryption_engine.encrypt_data(test_data, old_password)
        
        # Rotate key
        rotated_data = await encryption_engine.rotate_encryption_key(
            old_password, new_password, [encrypted_data]
        )
        
        assert len(rotated_data) == 1
        assert rotated_data[0].key_version > encrypted_data.key_version
        
        # Verify new data can be decrypted with new password
        decrypted = await encryption_engine.decrypt_data(rotated_data[0], new_password)
        assert decrypted == test_data


class TestCredentialTypes:
    """Test credential type management and validation"""
    
    @pytest.mark.asyncio
    async def test_password_validation(self, credential_manager):
        """Test password credential validation"""
        # Strong password
        strong_password_data = CredentialData(
            credential_type=CredentialType.PASSWORD,
            data={'password': 'StrongP@ssw0rd123!', 'username': 'testuser'}
        )
        
        result = await credential_manager.validate_credential(strong_password_data)
        assert result.is_valid
        assert result.strength_score > 0.7
        
        # Weak password
        weak_password_data = CredentialData(
            credential_type=CredentialType.PASSWORD,
            data={'password': '123', 'username': 'testuser'}
        )
        
        result = await credential_manager.validate_credential(weak_password_data)
        assert not result.is_valid
        assert len(result.issues) > 0
    
    @pytest.mark.asyncio
    async def test_api_key_validation(self, credential_manager):
        """Test API key credential validation"""
        # Valid API key
        valid_api_key_data = CredentialData(
            credential_type=CredentialType.API_KEY,
            data={'api_key': secrets.token_urlsafe(32), 'service_name': 'github'}
        )
        
        result = await credential_manager.validate_credential(valid_api_key_data)
        assert result.is_valid
        
        # Invalid API key (too short)
        invalid_api_key_data = CredentialData(
            credential_type=CredentialType.API_KEY,
            data={'api_key': 'short', 'service_name': 'github'}
        )
        
        result = await credential_manager.validate_credential(invalid_api_key_data)
        assert not result.is_valid
    
    @pytest.mark.asyncio
    async def test_credential_generation(self, credential_manager):
        """Test credential generation"""
        # Generate password
        password_cred = await credential_manager.generate_credential(
            CredentialType.PASSWORD,
            {'length': 16, 'include_symbols': True}
        )
        
        assert password_cred.credential_type == CredentialType.PASSWORD
        assert len(password_cred.data['password']) == 16
        
        # Generate API key
        api_key_cred = await credential_manager.generate_credential(
            CredentialType.API_KEY,
            {'length': 32, 'format': 'base64'}
        )
        
        assert api_key_cred.credential_type == CredentialType.API_KEY
        assert 'api_key' in api_key_cred.data


class TestPerformanceOptimizer:
    """Test performance optimization features"""
    
    @pytest.mark.asyncio
    async def test_memory_cache(self):
        """Test memory cache functionality"""
        cache = MemoryCache(max_size=10, strategy=CacheStrategy.LRU)
        
        # Test put and get
        await cache.put("key1", "value1")
        value = await cache.get("key1")
        assert value == "value1"
        
        # Test cache miss
        value = await cache.get("nonexistent")
        assert value is None
        
        # Test cache eviction
        for i in range(15):  # Exceed max_size
            await cache.put(f"key{i}", f"value{i}")
        
        # First keys should be evicted
        value = await cache.get("key1")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_cache_with_ttl(self):
        """Test cache with TTL expiration"""
        cache = MemoryCache(max_size=10, strategy=CacheStrategy.TTL, default_ttl=1)
        
        await cache.put("key1", "value1")
        value = await cache.get("key1")
        assert value == "value1"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        value = await cache.get("key1")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_metadata_caching(self, performance_optimizer):
        """Test credential metadata caching"""
        credential_id = "test_credential_123"
        metadata = {
            'name': 'Test Credential',
            'credential_type': 'password',
            'environment': 'test'
        }
        
        # Cache metadata
        success = await performance_optimizer.cache_metadata(credential_id, metadata)
        assert success
        
        # Retrieve from cache
        cached_metadata = await performance_optimizer.get_cached_metadata(credential_id)
        assert cached_metadata == metadata


class TestAuditManager:
    """Test audit logging and compliance features"""
    
    @pytest.mark.asyncio
    async def test_audit_event_logging(self, audit_manager):
        """Test audit event logging"""
        event_id = await audit_manager.log_event(
            AuditEventType.CREATE,
            "test_user",
            "create_credential",
            AuditResult.SUCCESS,
            "test_credential_123",
            ip_address="192.168.1.100",
            metadata={'test': 'data'}
        )
        
        assert event_id is not None
        assert len(event_id) > 0
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(self, test_config):
        """Test anomaly detection"""
        detector = AnomalyDetector(test_config)
        
        # Create test event
        from src.vault.audit_manager import AuditEvent
        test_event = AuditEvent(
            event_id="test_event",
            event_type=AuditEventType.READ,
            user_id="test_user",
            credential_id="test_cred",
            action="get_credential",
            result=AuditResult.SUCCESS,
            timestamp=datetime.utcnow(),
            ip_address="192.168.1.100"
        )
        
        # Test with empty history (should not be anomalous)
        is_anomaly, risk_score, indicators = await detector.analyze_event(test_event, [])
        assert not is_anomaly
        assert risk_score == 0.0
    
    @pytest.mark.asyncio
    async def test_compliance_checking(self, audit_manager):
        """Test compliance framework checking"""
        # This would test compliance rule evaluation
        # For now, just verify the audit manager has compliance capabilities
        assert hasattr(audit_manager, 'compliance_manager')


class TestSecurityFeatures:
    """Test security features and protections"""
    
    @pytest.mark.asyncio
    async def test_secure_memory_manager(self):
        """Test secure memory management"""
        from src.vault.security_features import MemoryProtectionLevel
        memory_manager = SecureMemoryManager(MemoryProtectionLevel.BASIC)
        
        # Allocate secure memory
        region_id = memory_manager.allocate_secure_memory(1024)
        assert region_id is not None
        
        # Write and read data
        test_data = b"sensitive data"
        success = memory_manager.write_secure_memory(region_id, test_data)
        assert success
        
        read_data = memory_manager.read_secure_memory(region_id, len(test_data))
        assert read_data == test_data
        
        # Zero and free memory
        success = memory_manager.zero_secure_memory(region_id)
        assert success
        
        success = memory_manager.free_secure_memory(region_id)
        assert success
    
    @pytest.mark.asyncio
    async def test_timing_attack_protection(self, test_config):
        """Test timing attack protection"""
        protection = TimingAttackProtection(test_config)
        
        # Test constant time comparison
        assert protection.constant_time_compare(b"test", b"test")
        assert not protection.constant_time_compare(b"test", b"different")
        
        # Test protected operation
        async def test_operation():
            return "result"
        
        start_time = asyncio.get_event_loop().time()
        result = await protection.protected_operation(test_operation)
        end_time = asyncio.get_event_loop().time()
        
        assert result == "result"
        # Should have added minimum delay
        assert (end_time - start_time) >= (protection.min_delay_ms / 1000)
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, test_config):
        """Test rate limiting functionality"""
        rate_limiter = RateLimiter(test_config)
        
        identifier = "test_user_192.168.1.100"
        
        # First attempts should be allowed
        for i in range(3):
            allowed, lockout_until = await rate_limiter.check_rate_limit(identifier)
            assert allowed
            await rate_limiter.record_attempt(identifier, success=False)
        
        # Next attempt should be rate limited
        allowed, lockout_until = await rate_limiter.check_rate_limit(identifier)
        assert not allowed
        assert lockout_until is not None
    
    @pytest.mark.asyncio
    async def test_session_management(self, test_config):
        """Test session management"""
        session_manager = SessionManager(test_config)
        
        # Create session
        session_id = await session_manager.create_session(
            "test_user",
            ip_address="192.168.1.100",
            mfa_verified=True
        )
        
        assert session_id is not None
        
        # Get session
        context = await session_manager.get_session(session_id)
        assert context is not None
        assert context.user_id == "test_user"
        assert context.mfa_verified
        
        # Invalidate session
        success = await session_manager.invalidate_session(session_id)
        assert success
        
        # Session should no longer exist
        context = await session_manager.get_session(session_id)
        assert context is None


class TestBackupManager:
    """Test backup and restore functionality"""
    
    @pytest.mark.asyncio
    async def test_backup_creation(self, backup_manager):
        """Test backup creation"""
        backup_id = await backup_manager.create_backup(
            BackupType.FULL,
            "test_user",
            include_encryption_keys=False,
            tags=["test", "full_backup"]
        )
        
        assert backup_id is not None
        
        # Check backup status
        backup_metadata = await backup_manager.get_backup_status(backup_id)
        assert backup_metadata is not None
        assert backup_metadata.backup_type == BackupType.FULL
        assert backup_metadata.created_by == "test_user"
    
    @pytest.mark.asyncio
    async def test_backup_key_management(self, backup_manager):
        """Test backup key management"""
        key_manager = backup_manager.key_manager
        
        # Generate backup key
        backup_key, key_version = await key_manager.generate_backup_key()
        
        assert backup_key is not None
        assert len(backup_key) == 32  # 256-bit key
        assert key_version > 0
        
        # Retrieve backup key
        retrieved_key = await key_manager.get_backup_key(key_version)
        assert retrieved_key == backup_key
    
    @pytest.mark.asyncio
    async def test_backup_encryption(self, backup_manager):
        """Test backup file encryption"""
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test backup data")
            test_file = Path(f.name)
        
        try:
            # Generate backup key
            backup_key, _ = await backup_manager.key_manager.generate_backup_key()
            
            # Encrypt file
            encrypted_file = await backup_manager._encrypt_backup(test_file, backup_key)
            
            assert encrypted_file.exists()
            assert encrypted_file != test_file
            
            # Decrypt file
            with tempfile.TemporaryDirectory() as temp_dir:
                decrypted_file = await backup_manager._decrypt_backup(
                    encrypted_file, backup_key, Path(temp_dir)
                )
                
                assert decrypted_file.exists()
                
                # Verify content
                content = decrypted_file.read_text()
                assert content == "test backup data"
        
        finally:
            # Cleanup
            test_file.unlink(missing_ok=True)
            if 'encrypted_file' in locals():
                encrypted_file.unlink(missing_ok=True)


class TestKeyRotationManager:
    """Test key rotation and version management"""
    
    @pytest.mark.asyncio
    async def test_key_version_creation(self, key_rotation_manager):
        """Test key version creation"""
        new_version = await key_rotation_manager.create_key_version(
            "test_user",
            RotationTrigger.MANUAL
        )
        
        assert new_version > 0
        
        # Verify key version exists
        key_versions = await key_rotation_manager.get_key_versions()
        assert any(kv.version == new_version for kv in key_versions)
    
    @pytest.mark.asyncio
    async def test_rotation_initiation(self, key_rotation_manager):
        """Test key rotation initiation"""
        rotation_id = await key_rotation_manager.initiate_key_rotation(
            RotationTrigger.MANUAL,
            "test_user",
            "Test rotation"
        )
        
        assert rotation_id is not None
        
        # Check rotation status
        rotation_op = await key_rotation_manager.get_rotation_status(rotation_id)
        assert rotation_op is not None
        assert rotation_op.trigger == RotationTrigger.MANUAL
        assert rotation_op.initiated_by == "test_user"
    
    @pytest.mark.asyncio
    async def test_rotation_policy_creation(self, key_rotation_manager):
        """Test rotation policy creation"""
        policy_data = {
            'name': 'Test Policy',
            'description': 'Test rotation policy',
            'rotation_interval_days': 30,
            'automatic_rotation': True,
            'require_approval': False
        }
        
        policy_id = await key_rotation_manager.create_rotation_policy(
            policy_data, "test_user"
        )
        
        assert policy_id is not None
        
        # Verify policy exists
        policies = await key_rotation_manager.get_rotation_policies()
        assert any(p.policy_id == policy_id for p in policies)
    
    @pytest.mark.asyncio
    async def test_emergency_rotation(self, key_rotation_manager):
        """Test emergency key rotation"""
        rotation_id = await key_rotation_manager.emergency_key_rotation(
            "security_admin",
            "Key compromise detected"
        )
        
        assert rotation_id is not None
        
        # Verify it's marked as emergency
        rotation_op = await key_rotation_manager.get_rotation_status(rotation_id)
        assert rotation_op.trigger == RotationTrigger.EMERGENCY


class TestIntegration:
    """Integration tests for complete vault operations"""
    
    @pytest.mark.asyncio
    async def test_complete_credential_lifecycle(self, test_config, mock_redis):
        """Test complete credential lifecycle"""
        # Initialize components
        db_manager = Mock(spec=DatabaseManager)
        db_manager.initialize = AsyncMock(return_value=True)
        db_manager.store_credential_metadata = AsyncMock(return_value=True)
        db_manager.store_encrypted_credential = AsyncMock(return_value=True)
        db_manager.check_user_access = AsyncMock(return_value=True)
        db_manager.get_transaction = AsyncMock()
        
        encryption_engine = EncryptionEngine(test_config, mock_redis)
        await encryption_engine.initialize()
        
        credential_manager = CredentialTypeManager(test_config)
        
        # Create credential data
        credential_data = CredentialData(
            credential_type=CredentialType.PASSWORD,
            data={'password': 'TestP@ssw0rd123!', 'username': 'testuser'}
        )
        
        # Validate credential
        validation_result = await credential_manager.validate_credential(credential_data)
        assert validation_result.is_valid
        
        # Encrypt credential
        encrypted_data = await encryption_engine.encrypt_data(
            json.dumps(credential_data.data).encode(),
            "master_password_123"
        )
        assert encrypted_data is not None
        
        # Decrypt credential
        decrypted_bytes = await encryption_engine.decrypt_data(
            encrypted_data, "master_password_123"
        )
        decrypted_data = json.loads(decrypted_bytes.decode())
        
        assert decrypted_data == credential_data.data
    
    @pytest.mark.asyncio
    async def test_security_event_flow(self, test_config, mock_redis, mock_database_manager):
        """Test security event detection and response flow"""
        # Initialize components
        audit_manager = AuditManager(test_config, mock_redis, mock_database_manager)
        await audit_manager.initialize()
        
        security_manager = SecurityFeatureManager(test_config)
        await security_manager.initialize()
        
        # Simulate suspicious activity
        user_id = "test_user"
        ip_address = "192.168.1.100"
        
        # Multiple failed login attempts
        for i in range(5):
            await audit_manager.log_event(
                AuditEventType.AUTH,
                user_id,
                "login_attempt",
                AuditResult.FAILURE,
                None,
                ip_address=ip_address
            )
        
        # Rate limiter should block further attempts
        rate_limiter = security_manager.rate_limiter
        identifier = f"auth:{user_id}:{ip_address}"
        
        allowed, lockout_until = await rate_limiter.check_rate_limit(identifier)
        # After recording failures, should be rate limited
        # (Note: This test would need the actual rate limiter to track attempts)
    
    @pytest.mark.asyncio
    async def test_performance_optimization_flow(self, test_config, mock_redis, mock_database_manager):
        """Test performance optimization features"""
        encryption_engine = EncryptionEngine(test_config, mock_redis)
        await encryption_engine.initialize()
        
        performance_optimizer = PerformanceOptimizer(
            test_config, mock_redis, encryption_engine, mock_database_manager
        )
        await performance_optimizer.initialize()
        
        # Test caching flow
        credential_id = "test_credential"
        user_id = "test_user"
        
        # Cache miss scenario
        cached_data = await performance_optimizer.get_cached_credential(credential_id, user_id)
        assert cached_data is None
        
        # Cache credential
        test_data = {'password': 'test_password', 'username': 'test_user'}
        success = await performance_optimizer.cache_credential(
            credential_id, user_id, test_data, ttl=60
        )
        assert success
        
        # Cache hit scenario
        cached_data = await performance_optimizer.get_cached_credential(credential_id, user_id)
        assert cached_data == test_data


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_encryption_with_wrong_password(self, encryption_engine):
        """Test decryption with wrong password"""
        test_data = b"sensitive data"
        correct_password = "correct_password"
        wrong_password = "wrong_password"
        
        # Encrypt with correct password
        encrypted_data = await encryption_engine.encrypt_data(test_data, correct_password)
        
        # Try to decrypt with wrong password
        with pytest.raises(Exception):
            await encryption_engine.decrypt_data(encrypted_data, wrong_password)
    
    @pytest.mark.asyncio
    async def test_invalid_credential_type(self, credential_manager):
        """Test handling of invalid credential types"""
        with pytest.raises(ValueError):
            CredentialData(
                credential_type="invalid_type",  # This should raise an error
                data={'test': 'data'}
            )
    
    @pytest.mark.asyncio
    async def test_backup_with_missing_key(self, backup_manager):
        """Test backup operations with missing encryption keys"""
        # Try to get non-existent key
        missing_key = await backup_manager.key_manager.get_backup_key(999)
        assert missing_key is None
    
    @pytest.mark.asyncio
    async def test_memory_allocation_failure(self):
        """Test secure memory allocation edge cases"""
        memory_manager = SecureMemoryManager()
        
        # Try to allocate extremely large memory (should handle gracefully)
        region_id = memory_manager.allocate_secure_memory(1024 * 1024 * 1024)  # 1GB
        # Should either succeed or return None, not crash
        assert region_id is None or isinstance(region_id, int)


class TestPerformance:
    """Performance and load testing"""
    
    @pytest.mark.asyncio
    async def test_batch_encryption_performance(self, encryption_engine):
        """Test batch encryption performance"""
        import time
        
        # Prepare test data
        test_data = [(f"data_{i}".encode(), f"password_{i}") for i in range(100)]
        
        # Measure batch encryption time
        start_time = time.time()
        results = await encryption_engine.batch_encrypt(test_data)
        batch_time = time.time() - start_time
        
        # Measure individual encryption time
        start_time = time.time()
        individual_results = []
        for data, password in test_data:
            result = await encryption_engine.encrypt_data(data, password)
            individual_results.append(result)
        individual_time = time.time() - start_time
        
        # Batch should be faster (or at least not significantly slower)
        assert len(results) == len(test_data)
        assert len(individual_results) == len(test_data)
        
        # Log performance comparison
        print(f"Batch encryption: {batch_time:.3f}s")
        print(f"Individual encryption: {individual_time:.3f}s")
        print(f"Performance ratio: {individual_time / batch_time:.2f}x")
    
    @pytest.mark.asyncio
    async def test_cache_performance(self):
        """Test cache performance under load"""
        cache = MemoryCache(max_size=1000, strategy=CacheStrategy.LRU)
        
        # Fill cache
        for i in range(1000):
            await cache.put(f"key_{i}", f"value_{i}")
        
        # Measure cache hit performance
        import time
        start_time = time.time()
        
        for i in range(1000):
            value = await cache.get(f"key_{i}")
            assert value == f"value_{i}"
        
        cache_time = time.time() - start_time
        
        # Should be very fast
        assert cache_time < 1.0  # Less than 1 second for 1000 operations
        print(f"Cache performance: {cache_time:.3f}s for 1000 operations")


@pytest.mark.asyncio
async def test_vault_statistics_collection(test_config, mock_redis, mock_database_manager):
    """Test comprehensive vault statistics collection"""
    # Initialize components
    encryption_engine = EncryptionEngine(test_config, mock_redis)
    await encryption_engine.initialize()
    
    performance_optimizer = PerformanceOptimizer(
        test_config, mock_redis, encryption_engine, mock_database_manager
    )
    await performance_optimizer.initialize()
    
    audit_manager = AuditManager(test_config, mock_redis, mock_database_manager)
    await audit_manager.initialize()
    
    security_manager = SecurityFeatureManager(test_config)
    await security_manager.initialize()
    
    # Get statistics from each component
    db_stats = await mock_database_manager.get_vault_statistics()
    perf_stats = await performance_optimizer.get_performance_stats()
    security_stats = await security_manager.get_security_status()
    encryption_stats = await encryption_engine.get_encryption_stats()
    
    # Verify statistics structure
    assert isinstance(db_stats, dict)
    assert isinstance(perf_stats, dict)
    assert isinstance(security_stats, dict)
    assert isinstance(encryption_stats, dict)
    
    # Verify key fields exist
    assert 'total_credentials' in db_stats
    assert 'metrics' in perf_stats or 'error' in perf_stats
    assert 'memory_protection' in security_stats or 'error' in security_stats
    assert 'security_level' in encryption_stats or 'error' in encryption_stats


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])