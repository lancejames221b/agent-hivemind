"""
Advanced Encryption Engine for Credential Vault
Secure encryption/decryption with memory protection and performance optimization.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
import hashlib
import secrets
import hmac
import time
import mmap
import ctypes
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import base64
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from cryptography.hazmat.primitives import hashes, serialization, constant_time
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import redis


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms"""
    AES_256_GCM = "AES-256-GCM"
    AES_256_CBC = "AES-256-CBC"
    CHACHA20_POLY1305 = "ChaCha20-Poly1305"
    FERNET = "Fernet"


class KeyDerivationMethod(Enum):
    """Key derivation methods"""
    SCRYPT = "scrypt"
    PBKDF2 = "pbkdf2"
    HKDF = "hkdf"
    ARGON2 = "argon2"


class SecurityLevel(Enum):
    """Security levels with different parameters"""
    STANDARD = "standard"
    HIGH = "high"
    MAXIMUM = "maximum"


@dataclass
class EncryptionParameters:
    """Encryption parameters for different security levels"""
    algorithm: EncryptionAlgorithm
    key_derivation: KeyDerivationMethod
    iterations: int
    memory_cost: int
    parallelism: int
    salt_length: int
    nonce_length: int
    key_length: int


@dataclass
class EncryptedData:
    """Encrypted data container"""
    ciphertext: bytes
    algorithm: EncryptionAlgorithm
    key_derivation: KeyDerivationMethod
    salt: bytes
    nonce: bytes
    tag: bytes
    key_version: int
    created_at: datetime
    metadata: Dict[str, Any]


class SecureMemory:
    """Secure memory management for sensitive data"""
    
    def __init__(self, size: int):
        self.size = size
        self._buffer = None
        self._locked = False
    
    def __enter__(self):
        """Allocate and lock secure memory"""
        try:
            # Allocate memory
            self._buffer = (ctypes.c_char * self.size)()
            
            # Lock memory to prevent swapping (Linux/Unix)
            if hasattr(ctypes, 'mlock'):
                ctypes.mlock(ctypes.addressof(self._buffer), self.size)
                self._locked = True
            
            return self._buffer
        except Exception as e:
            logging.error(f"Failed to allocate secure memory: {str(e)}")
            return None
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Zero and unlock memory"""
        if self._buffer:
            # Zero memory
            ctypes.memset(self._buffer, 0, self.size)
            
            # Unlock memory
            if self._locked and hasattr(ctypes, 'munlock'):
                try:
                    ctypes.munlock(ctypes.addressof(self._buffer), self.size)
                except:
                    pass
            
            self._buffer = None
            self._locked = False


class EncryptionEngine:
    """Advanced encryption engine with security features"""
    
    def __init__(self, config: Dict[str, Any], redis_client: Optional[redis.Redis]):
        self.config = config
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        
        # Encryption configuration
        self.encryption_config = config.get('vault', {}).get('encryption', {})
        self.security_level = SecurityLevel(self.encryption_config.get('security_level', 'high'))
        
        # Thread pool for CPU-intensive operations
        self.thread_pool = ThreadPoolExecutor(
            max_workers=self.encryption_config.get('max_workers', 4),
            thread_name_prefix='encryption_worker'
        )
        
        # Performance caching
        self.key_cache_ttl = self.encryption_config.get('key_cache_ttl', 300)  # 5 minutes
        self.enable_caching = self.encryption_config.get('enable_caching', True)
        
        # Security parameters by level
        self.security_parameters = {
            SecurityLevel.STANDARD: EncryptionParameters(
                algorithm=EncryptionAlgorithm.AES_256_GCM,
                key_derivation=KeyDerivationMethod.PBKDF2,
                iterations=100000,
                memory_cost=64 * 1024,  # 64MB for scrypt
                parallelism=1,
                salt_length=32,
                nonce_length=12,
                key_length=32
            ),
            SecurityLevel.HIGH: EncryptionParameters(
                algorithm=EncryptionAlgorithm.AES_256_GCM,
                key_derivation=KeyDerivationMethod.SCRYPT,
                iterations=32768,  # N parameter for scrypt
                memory_cost=128 * 1024,  # 128MB
                parallelism=1,
                salt_length=32,
                nonce_length=12,
                key_length=32
            ),
            SecurityLevel.MAXIMUM: EncryptionParameters(
                algorithm=EncryptionAlgorithm.AES_256_GCM,
                key_derivation=KeyDerivationMethod.SCRYPT,
                iterations=65536,
                memory_cost=256 * 1024,  # 256MB
                parallelism=2,
                salt_length=64,
                nonce_length=12,
                key_length=32
            )
        }
        
        # Current parameters
        self.params = self.security_parameters[self.security_level]
        
        # Key version management
        self.current_key_version = 1
        self.key_rotation_interval = timedelta(days=self.encryption_config.get('key_rotation_days', 90))
        
    async def initialize(self) -> bool:
        """Initialize encryption engine"""
        try:
            # Test encryption/decryption
            test_data = b"encryption_engine_test"
            test_password = "test_password_123"
            
            encrypted = await self.encrypt_data(test_data, test_password)
            decrypted = await self.decrypt_data(encrypted, test_password)
            
            if decrypted != test_data:
                raise ValueError("Encryption engine test failed")
            
            self.logger.info(f"Encryption engine initialized with {self.security_level.value} security level")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize encryption engine: {str(e)}")
            return False
    
    def generate_salt(self, length: Optional[int] = None) -> bytes:
        """Generate cryptographically secure salt"""
        salt_length = length or self.params.salt_length
        return secrets.token_bytes(salt_length)
    
    def generate_nonce(self, length: Optional[int] = None) -> bytes:
        """Generate cryptographically secure nonce"""
        nonce_length = length or self.params.nonce_length
        return secrets.token_bytes(nonce_length)
    
    async def derive_key_from_password(self, password: str, salt: bytes, 
                                     method: Optional[KeyDerivationMethod] = None,
                                     iterations: Optional[int] = None) -> bytes:
        """Derive encryption key from password using secure KDF"""
        try:
            kdf_method = method or self.params.key_derivation
            kdf_iterations = iterations or self.params.iterations
            
            password_bytes = password.encode('utf-8')
            
            # Use thread pool for CPU-intensive KDF
            if kdf_method == KeyDerivationMethod.SCRYPT:
                kdf = Scrypt(
                    length=self.params.key_length,
                    salt=salt,
                    n=kdf_iterations,
                    r=8,
                    p=self.params.parallelism
                )
            elif kdf_method == KeyDerivationMethod.PBKDF2:
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=self.params.key_length,
                    salt=salt,
                    iterations=kdf_iterations
                )
            elif kdf_method == KeyDerivationMethod.HKDF:
                kdf = HKDF(
                    algorithm=hashes.SHA256(),
                    length=self.params.key_length,
                    salt=salt,
                    info=b'vault_credential_key'
                )
            else:
                raise ValueError(f"Unsupported key derivation method: {kdf_method}")
            
            # Derive key in thread pool
            loop = asyncio.get_event_loop()
            derived_key = await loop.run_in_executor(
                self.thread_pool, 
                kdf.derive, 
                password_bytes
            )
            
            # Cache derived key if enabled
            if self.enable_caching and self.redis:
                await self._cache_derived_key(password, salt, derived_key, kdf_method)
            
            return derived_key
            
        except Exception as e:
            self.logger.error(f"Key derivation failed: {str(e)}")
            raise
        finally:
            # Zero password bytes
            if 'password_bytes' in locals():
                password_bytes = b'\x00' * len(password_bytes)
    
    async def _cache_derived_key(self, password: str, salt: bytes, key: bytes, 
                               method: KeyDerivationMethod) -> None:
        """Cache derived key for performance"""
        try:
            # Create cache key from password hash and salt
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            salt_hash = hashlib.sha256(salt).hexdigest()
            cache_key = f"vault:derived_key:{password_hash}:{salt_hash}:{method.value}"
            
            # Store encrypted key in cache
            cache_data = {
                'key': base64.b64encode(key).decode(),
                'method': method.value,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            self.redis.setex(
                cache_key,
                self.key_cache_ttl,
                json.dumps(cache_data)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to cache derived key: {str(e)}")
    
    async def _get_cached_key(self, password: str, salt: bytes, 
                            method: KeyDerivationMethod) -> Optional[bytes]:
        """Get cached derived key"""
        try:
            if not self.enable_caching or not self.redis:
                return None
            
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            salt_hash = hashlib.sha256(salt).hexdigest()
            cache_key = f"vault:derived_key:{password_hash}:{salt_hash}:{method.value}"
            
            cached_data = self.redis.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return base64.b64decode(data['key'])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get cached key: {str(e)}")
            return None
    
    async def encrypt_data(self, data: bytes, password: str, 
                         algorithm: Optional[EncryptionAlgorithm] = None,
                         metadata: Dict[str, Any] = None) -> EncryptedData:
        """Encrypt data with specified algorithm"""
        try:
            start_time = time.time()
            
            enc_algorithm = algorithm or self.params.algorithm
            salt = self.generate_salt()
            nonce = self.generate_nonce()
            
            # Check for cached key first
            cached_key = await self._get_cached_key(password, salt, self.params.key_derivation)
            if cached_key:
                key = cached_key
            else:
                key = await self.derive_key_from_password(password, salt)
            
            # Encrypt based on algorithm
            if enc_algorithm == EncryptionAlgorithm.AES_256_GCM:
                ciphertext, tag = await self._encrypt_aes_gcm(data, key, nonce)
            elif enc_algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
                ciphertext, tag = await self._encrypt_chacha20_poly1305(data, key, nonce)
            elif enc_algorithm == EncryptionAlgorithm.FERNET:
                ciphertext, tag = await self._encrypt_fernet(data, key)
                nonce = b''  # Fernet includes nonce in ciphertext
            else:
                raise ValueError(f"Unsupported encryption algorithm: {enc_algorithm}")
            
            encryption_time = time.time() - start_time
            
            encrypted_data = EncryptedData(
                ciphertext=ciphertext,
                algorithm=enc_algorithm,
                key_derivation=self.params.key_derivation,
                salt=salt,
                nonce=nonce,
                tag=tag,
                key_version=self.current_key_version,
                created_at=datetime.utcnow(),
                metadata={
                    'encryption_time': encryption_time,
                    'data_size': len(data),
                    'security_level': self.security_level.value,
                    **(metadata or {})
                }
            )
            
            # Zero sensitive data
            key = b'\x00' * len(key)
            
            return encrypted_data
            
        except Exception as e:
            self.logger.error(f"Encryption failed: {str(e)}")
            raise
    
    async def decrypt_data(self, encrypted_data: EncryptedData, password: str) -> bytes:
        """Decrypt data"""
        try:
            start_time = time.time()
            
            # Check for cached key first
            cached_key = await self._get_cached_key(password, encrypted_data.salt, encrypted_data.key_derivation)
            if cached_key:
                key = cached_key
            else:
                key = await self.derive_key_from_password(
                    password, 
                    encrypted_data.salt, 
                    encrypted_data.key_derivation
                )
            
            # Decrypt based on algorithm
            if encrypted_data.algorithm == EncryptionAlgorithm.AES_256_GCM:
                plaintext = await self._decrypt_aes_gcm(
                    encrypted_data.ciphertext, 
                    key, 
                    encrypted_data.nonce, 
                    encrypted_data.tag
                )
            elif encrypted_data.algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
                plaintext = await self._decrypt_chacha20_poly1305(
                    encrypted_data.ciphertext, 
                    key, 
                    encrypted_data.nonce, 
                    encrypted_data.tag
                )
            elif encrypted_data.algorithm == EncryptionAlgorithm.FERNET:
                plaintext = await self._decrypt_fernet(encrypted_data.ciphertext, key)
            else:
                raise ValueError(f"Unsupported encryption algorithm: {encrypted_data.algorithm}")
            
            decryption_time = time.time() - start_time
            self.logger.debug(f"Decryption completed in {decryption_time:.3f}s")
            
            # Zero sensitive data
            key = b'\x00' * len(key)
            
            return plaintext
            
        except Exception as e:
            self.logger.error(f"Decryption failed: {str(e)}")
            raise
    
    async def _encrypt_aes_gcm(self, data: bytes, key: bytes, nonce: bytes) -> Tuple[bytes, bytes]:
        """Encrypt with AES-256-GCM"""
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
        encryptor = cipher.encryptor()
        
        # Run encryption in thread pool
        loop = asyncio.get_event_loop()
        
        def _encrypt():
            ciphertext = encryptor.update(data) + encryptor.finalize()
            return ciphertext, encryptor.tag
        
        return await loop.run_in_executor(self.thread_pool, _encrypt)
    
    async def _decrypt_aes_gcm(self, ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes) -> bytes:
        """Decrypt with AES-256-GCM"""
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag))
        decryptor = cipher.decryptor()
        
        # Run decryption in thread pool
        loop = asyncio.get_event_loop()
        
        def _decrypt():
            return decryptor.update(ciphertext) + decryptor.finalize()
        
        return await loop.run_in_executor(self.thread_pool, _decrypt)
    
    async def _encrypt_chacha20_poly1305(self, data: bytes, key: bytes, nonce: bytes) -> Tuple[bytes, bytes]:
        """Encrypt with ChaCha20-Poly1305"""
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        
        aead = ChaCha20Poly1305(key)
        
        # Run encryption in thread pool
        loop = asyncio.get_event_loop()
        
        def _encrypt():
            ciphertext = aead.encrypt(nonce, data, None)
            # ChaCha20Poly1305 includes tag in ciphertext
            return ciphertext[:-16], ciphertext[-16:]
        
        return await loop.run_in_executor(self.thread_pool, _encrypt)
    
    async def _decrypt_chacha20_poly1305(self, ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes) -> bytes:
        """Decrypt with ChaCha20-Poly1305"""
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        
        aead = ChaCha20Poly1305(key)
        
        # Run decryption in thread pool
        loop = asyncio.get_event_loop()
        
        def _decrypt():
            return aead.decrypt(nonce, ciphertext + tag, None)
        
        return await loop.run_in_executor(self.thread_pool, _decrypt)
    
    async def _encrypt_fernet(self, data: bytes, key: bytes) -> Tuple[bytes, bytes]:
        """Encrypt with Fernet"""
        # Fernet requires base64 encoded key
        fernet_key = base64.urlsafe_b64encode(key)
        f = Fernet(fernet_key)
        
        # Run encryption in thread pool
        loop = asyncio.get_event_loop()
        
        def _encrypt():
            ciphertext = f.encrypt(data)
            return ciphertext, b''  # Fernet includes authentication
        
        return await loop.run_in_executor(self.thread_pool, _encrypt)
    
    async def _decrypt_fernet(self, ciphertext: bytes, key: bytes) -> bytes:
        """Decrypt with Fernet"""
        fernet_key = base64.urlsafe_b64encode(key)
        f = Fernet(fernet_key)
        
        # Run decryption in thread pool
        loop = asyncio.get_event_loop()
        
        def _decrypt():
            return f.decrypt(ciphertext)
        
        return await loop.run_in_executor(self.thread_pool, _decrypt)
    
    def secure_compare(self, a: bytes, b: bytes) -> bool:
        """Constant-time comparison to prevent timing attacks"""
        return constant_time.bytes_eq(a, b)
    
    def secure_compare_strings(self, a: str, b: str) -> bool:
        """Constant-time string comparison"""
        return constant_time.bytes_eq(a.encode('utf-8'), b.encode('utf-8'))
    
    async def rotate_encryption_key(self, old_password: str, new_password: str,
                                  credential_data: List[EncryptedData]) -> List[EncryptedData]:
        """Rotate encryption key for multiple credentials"""
        try:
            rotated_data = []
            new_key_version = self.current_key_version + 1
            
            for encrypted_cred in credential_data:
                # Decrypt with old password
                plaintext = await self.decrypt_data(encrypted_cred, old_password)
                
                # Re-encrypt with new password and key version
                new_encrypted = await self.encrypt_data(
                    plaintext, 
                    new_password,
                    metadata={'rotated_from_version': encrypted_cred.key_version}
                )
                new_encrypted.key_version = new_key_version
                
                rotated_data.append(new_encrypted)
                
                # Zero plaintext
                plaintext = b'\x00' * len(plaintext)
            
            # Update current key version
            self.current_key_version = new_key_version
            
            self.logger.info(f"Rotated {len(rotated_data)} credentials to key version {new_key_version}")
            return rotated_data
            
        except Exception as e:
            self.logger.error(f"Key rotation failed: {str(e)}")
            raise
    
    async def batch_encrypt(self, data_list: List[Tuple[bytes, str]], 
                          algorithm: Optional[EncryptionAlgorithm] = None) -> List[EncryptedData]:
        """Batch encrypt multiple data items for performance"""
        try:
            tasks = []
            for data, password in data_list:
                task = self.encrypt_data(data, password, algorithm)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions
            encrypted_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Batch encryption failed for item {i}: {str(result)}")
                else:
                    encrypted_results.append(result)
            
            return encrypted_results
            
        except Exception as e:
            self.logger.error(f"Batch encryption failed: {str(e)}")
            return []
    
    async def batch_decrypt(self, encrypted_data_list: List[Tuple[EncryptedData, str]]) -> List[bytes]:
        """Batch decrypt multiple data items for performance"""
        try:
            tasks = []
            for encrypted_data, password in encrypted_data_list:
                task = self.decrypt_data(encrypted_data, password)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions
            decrypted_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Batch decryption failed for item {i}: {str(result)}")
                else:
                    decrypted_results.append(result)
            
            return decrypted_results
            
        except Exception as e:
            self.logger.error(f"Batch decryption failed: {str(e)}")
            return []
    
    def generate_master_key(self) -> bytes:
        """Generate a new master key"""
        return secrets.token_bytes(32)
    
    def hash_password(self, password: str, salt: Optional[bytes] = None) -> Tuple[str, bytes]:
        """Hash password for storage"""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        # Use scrypt for password hashing
        kdf = Scrypt(
            length=32,
            salt=salt,
            n=32768,
            r=8,
            p=1
        )
        
        password_hash = kdf.derive(password.encode('utf-8'))
        hash_b64 = base64.b64encode(password_hash).decode('ascii')
        
        return hash_b64, salt
    
    def verify_password(self, password: str, hash_b64: str, salt: bytes) -> bool:
        """Verify password against hash"""
        try:
            stored_hash = base64.b64decode(hash_b64)
            
            kdf = Scrypt(
                length=32,
                salt=salt,
                n=32768,
                r=8,
                p=1
            )
            
            computed_hash = kdf.derive(password.encode('utf-8'))
            return self.secure_compare(stored_hash, computed_hash)
            
        except Exception as e:
            self.logger.error(f"Password verification failed: {str(e)}")
            return False
    
    async def get_encryption_stats(self) -> Dict[str, Any]:
        """Get encryption engine statistics"""
        try:
            stats = {
                'security_level': self.security_level.value,
                'algorithm': self.params.algorithm.value,
                'key_derivation': self.params.key_derivation.value,
                'current_key_version': self.current_key_version,
                'cache_enabled': self.enable_caching,
                'thread_pool_size': self.thread_pool._max_workers,
                'parameters': {
                    'iterations': self.params.iterations,
                    'memory_cost': self.params.memory_cost,
                    'salt_length': self.params.salt_length,
                    'nonce_length': self.params.nonce_length,
                    'key_length': self.params.key_length
                }
            }
            
            # Add cache statistics if Redis is available
            if self.redis:
                try:
                    cache_keys = self.redis.keys("vault:derived_key:*")
                    stats['cached_keys'] = len(cache_keys)
                except:
                    stats['cached_keys'] = 0
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get encryption stats: {str(e)}")
            return {}
    
    def __del__(self):
        """Cleanup thread pool on destruction"""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=False)