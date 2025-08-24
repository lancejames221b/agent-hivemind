"""
Advanced Vault Security Framework with HSM Integration
Enterprise-grade security features for credential management.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import secrets
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import redis
import aiohttp


class HSMProvider(Enum):
    """Supported Hardware Security Module providers"""
    PKCS11 = "pkcs11"
    AWS_CLOUDHSM = "aws_cloudhsm"
    AZURE_HSM = "azure_hsm"
    THALES_LUNA = "thales_luna"
    SAFENET = "safenet"
    YubiHSM2 = "yubihsm2"


class SecurityLevel(Enum):
    """Security levels for different types of credentials"""
    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"
    TOP_SECRET = "top_secret"


@dataclass
class HSMConfiguration:
    """HSM configuration parameters"""
    provider: HSMProvider
    endpoint: str
    auth_token: str
    key_label: str
    slot_id: Optional[int] = None
    partition_name: Optional[str] = None
    ca_cert_path: Optional[str] = None
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None


@dataclass
class SecurityPolicy:
    """Security policy for credential operations"""
    min_security_level: SecurityLevel
    require_multi_auth: bool
    max_access_attempts: int
    session_timeout: int
    audit_required: bool
    encryption_algorithm: str
    key_rotation_days: int
    backup_encryption: bool
    geographic_restrictions: List[str]


class AdvancedSecurityFramework:
    """Advanced security framework with HSM integration"""
    
    def __init__(self, config: Dict[str, Any], redis_client: redis.Redis):
        self.config = config
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        self.hsm_configs: Dict[str, HSMConfiguration] = {}
        self.security_policies: Dict[str, SecurityPolicy] = {}
        self.active_sessions: Dict[str, Dict] = {}
        
    async def initialize_hsm_providers(self) -> bool:
        """Initialize all configured HSM providers"""
        try:
            hsm_config = self.config.get('vault', {}).get('hsm', {})
            
            for provider_name, provider_config in hsm_config.items():
                hsm_config_obj = HSMConfiguration(
                    provider=HSMProvider(provider_config['provider']),
                    endpoint=provider_config['endpoint'],
                    auth_token=provider_config['auth_token'],
                    key_label=provider_config['key_label'],
                    slot_id=provider_config.get('slot_id'),
                    partition_name=provider_config.get('partition_name'),
                    ca_cert_path=provider_config.get('ca_cert_path'),
                    client_cert_path=provider_config.get('client_cert_path'),
                    client_key_path=provider_config.get('client_key_path')
                )
                
                if await self._test_hsm_connection(hsm_config_obj):
                    self.hsm_configs[provider_name] = hsm_config_obj
                    self.logger.info(f"HSM provider {provider_name} initialized successfully")
                else:
                    self.logger.error(f"Failed to initialize HSM provider {provider_name}")
                    
            return len(self.hsm_configs) > 0
            
        except Exception as e:
            self.logger.error(f"HSM initialization failed: {str(e)}")
            return False
    
    async def _test_hsm_connection(self, hsm_config: HSMConfiguration) -> bool:
        """Test connection to HSM provider"""
        try:
            if hsm_config.provider == HSMProvider.AWS_CLOUDHSM:
                return await self._test_aws_cloudhsm(hsm_config)
            elif hsm_config.provider == HSMProvider.AZURE_HSM:
                return await self._test_azure_hsm(hsm_config)
            elif hsm_config.provider == HSMProvider.PKCS11:
                return await self._test_pkcs11_hsm(hsm_config)
            else:
                return await self._test_generic_hsm(hsm_config)
                
        except Exception as e:
            self.logger.error(f"HSM connection test failed: {str(e)}")
            return False
    
    async def _test_aws_cloudhsm(self, hsm_config: HSMConfiguration) -> bool:
        """Test AWS CloudHSM connection"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {hsm_config.auth_token}'}
                async with session.get(f"{hsm_config.endpoint}/health", headers=headers) as response:
                    return response.status == 200
        except:
            return False
    
    async def _test_azure_hsm(self, hsm_config: HSMConfiguration) -> bool:
        """Test Azure Key Vault HSM connection"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {hsm_config.auth_token}'}
                async with session.get(f"{hsm_config.endpoint}/keys?api-version=7.4", headers=headers) as response:
                    return response.status == 200
        except:
            return False
    
    async def _test_pkcs11_hsm(self, hsm_config: HSMConfiguration) -> bool:
        """Test PKCS#11 HSM connection"""
        try:
            import PyKCS11
            pkcs11 = PyKCS11.PyKCS11Lib()
            pkcs11.load(hsm_config.endpoint)
            slots = pkcs11.getSlotList()
            return len(slots) > 0
        except:
            return False
    
    async def _test_generic_hsm(self, hsm_config: HSMConfiguration) -> bool:
        """Test generic HSM connection"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{hsm_config.endpoint}/status") as response:
                    return response.status == 200
        except:
            return False
    
    async def generate_hsm_key(self, hsm_provider: str, key_type: str = "RSA", key_size: int = 4096) -> Optional[str]:
        """Generate cryptographic key using HSM"""
        try:
            if hsm_provider not in self.hsm_configs:
                raise ValueError(f"HSM provider {hsm_provider} not configured")
            
            hsm_config = self.hsm_configs[hsm_provider]
            key_id = f"vault_key_{secrets.token_hex(16)}"
            
            if hsm_config.provider == HSMProvider.AWS_CLOUDHSM:
                return await self._generate_aws_cloudhsm_key(hsm_config, key_id, key_type, key_size)
            elif hsm_config.provider == HSMProvider.AZURE_HSM:
                return await self._generate_azure_hsm_key(hsm_config, key_id, key_type, key_size)
            elif hsm_config.provider == HSMProvider.PKCS11:
                return await self._generate_pkcs11_key(hsm_config, key_id, key_type, key_size)
            else:
                return await self._generate_generic_hsm_key(hsm_config, key_id, key_type, key_size)
                
        except Exception as e:
            self.logger.error(f"HSM key generation failed: {str(e)}")
            return None
    
    async def _generate_aws_cloudhsm_key(self, hsm_config: HSMConfiguration, key_id: str, key_type: str, key_size: int) -> str:
        """Generate key using AWS CloudHSM"""
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {hsm_config.auth_token}', 'Content-Type': 'application/json'}
            payload = {
                'KeyId': key_id,
                'KeyType': key_type,
                'KeySize': key_size,
                'KeyLabel': hsm_config.key_label
            }
            
            async with session.post(f"{hsm_config.endpoint}/keys", headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['KeyId']
                else:
                    raise Exception(f"AWS CloudHSM key generation failed: {await response.text()}")
    
    async def _generate_azure_hsm_key(self, hsm_config: HSMConfiguration, key_id: str, key_type: str, key_size: int) -> str:
        """Generate key using Azure Key Vault HSM"""
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {hsm_config.auth_token}', 'Content-Type': 'application/json'}
            payload = {
                'kty': key_type,
                'key_size': key_size,
                'key_ops': ['encrypt', 'decrypt', 'sign', 'verify'],
                'attributes': {'enabled': True}
            }
            
            async with session.post(f"{hsm_config.endpoint}/keys/{key_id}/create?api-version=7.4", 
                                  headers=headers, json=payload) as response:
                if response.status == 200:
                    return key_id
                else:
                    raise Exception(f"Azure HSM key generation failed: {await response.text()}")
    
    async def _generate_pkcs11_key(self, hsm_config: HSMConfiguration, key_id: str, key_type: str, key_size: int) -> str:
        """Generate key using PKCS#11 HSM"""
        import PyKCS11
        
        pkcs11 = PyKCS11.PyKCS11Lib()
        pkcs11.load(hsm_config.endpoint)
        
        slots = pkcs11.getSlotList()
        if not slots:
            raise Exception("No PKCS#11 slots available")
        
        session = pkcs11.openSession(slots[hsm_config.slot_id or 0])
        session.login(hsm_config.auth_token)
        
        if key_type == "RSA":
            template = [
                (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
                (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_RSA),
                (PyKCS11.CKA_MODULUS_BITS, key_size),
                (PyKCS11.CKA_PRIVATE_EXPONENT, True),
                (PyKCS11.CKA_SIGN, True),
                (PyKCS11.CKA_DECRYPT, True),
                (PyKCS11.CKA_LABEL, key_id)
            ]
            
            key = session.generateKeyPair(template, template)
            session.logout()
            return key_id
        else:
            raise ValueError(f"Unsupported key type for PKCS#11: {key_type}")
    
    async def _generate_generic_hsm_key(self, hsm_config: HSMConfiguration, key_id: str, key_type: str, key_size: int) -> str:
        """Generate key using generic HSM API"""
        async with aiohttp.ClientSession() as session:
            payload = {
                'key_id': key_id,
                'key_type': key_type,
                'key_size': key_size,
                'auth_token': hsm_config.auth_token
            }
            
            async with session.post(f"{hsm_config.endpoint}/generate", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['key_id']
                else:
                    raise Exception(f"Generic HSM key generation failed: {await response.text()}")
    
    async def encrypt_with_hsm(self, hsm_provider: str, key_id: str, plaintext: bytes) -> Optional[bytes]:
        """Encrypt data using HSM"""
        try:
            if hsm_provider not in self.hsm_configs:
                raise ValueError(f"HSM provider {hsm_provider} not configured")
            
            hsm_config = self.hsm_configs[hsm_provider]
            
            if hsm_config.provider == HSMProvider.AWS_CLOUDHSM:
                return await self._encrypt_aws_cloudhsm(hsm_config, key_id, plaintext)
            elif hsm_config.provider == HSMProvider.AZURE_HSM:
                return await self._encrypt_azure_hsm(hsm_config, key_id, plaintext)
            elif hsm_config.provider == HSMProvider.PKCS11:
                return await self._encrypt_pkcs11(hsm_config, key_id, plaintext)
            else:
                return await self._encrypt_generic_hsm(hsm_config, key_id, plaintext)
                
        except Exception as e:
            self.logger.error(f"HSM encryption failed: {str(e)}")
            return None
    
    async def _encrypt_aws_cloudhsm(self, hsm_config: HSMConfiguration, key_id: str, plaintext: bytes) -> bytes:
        """Encrypt using AWS CloudHSM"""
        import base64
        
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {hsm_config.auth_token}', 'Content-Type': 'application/json'}
            payload = {
                'KeyId': key_id,
                'Plaintext': base64.b64encode(plaintext).decode('utf-8'),
                'Algorithm': 'RSA_OAEP_SHA256'
            }
            
            async with session.post(f"{hsm_config.endpoint}/encrypt", headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return base64.b64decode(result['CiphertextBlob'])
                else:
                    raise Exception(f"AWS CloudHSM encryption failed: {await response.text()}")
    
    async def _encrypt_azure_hsm(self, hsm_config: HSMConfiguration, key_id: str, plaintext: bytes) -> bytes:
        """Encrypt using Azure Key Vault HSM"""
        import base64
        
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {hsm_config.auth_token}', 'Content-Type': 'application/json'}
            payload = {
                'alg': 'RSA-OAEP-256',
                'value': base64.b64encode(plaintext).decode('utf-8')
            }
            
            async with session.post(f"{hsm_config.endpoint}/keys/{key_id}/encrypt?api-version=7.4", 
                                  headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return base64.b64decode(result['value'])
                else:
                    raise Exception(f"Azure HSM encryption failed: {await response.text()}")
    
    async def _encrypt_pkcs11(self, hsm_config: HSMConfiguration, key_id: str, plaintext: bytes) -> bytes:
        """Encrypt using PKCS#11 HSM"""
        import PyKCS11
        
        pkcs11 = PyKCS11.PyKCS11Lib()
        pkcs11.load(hsm_config.endpoint)
        
        slots = pkcs11.getSlotList()
        session = pkcs11.openSession(slots[hsm_config.slot_id or 0])
        session.login(hsm_config.auth_token)
        
        keys = session.findObjects([(PyKCS11.CKA_LABEL, key_id)])
        if not keys:
            raise Exception(f"Key {key_id} not found in PKCS#11 HSM")
        
        ciphertext = session.encrypt(keys[0], plaintext, PyKCS11.CKM_RSA_PKCS_OAEP)
        session.logout()
        
        return bytes(ciphertext)
    
    async def _encrypt_generic_hsm(self, hsm_config: HSMConfiguration, key_id: str, plaintext: bytes) -> bytes:
        """Encrypt using generic HSM API"""
        import base64
        
        async with aiohttp.ClientSession() as session:
            payload = {
                'key_id': key_id,
                'plaintext': base64.b64encode(plaintext).decode('utf-8'),
                'auth_token': hsm_config.auth_token
            }
            
            async with session.post(f"{hsm_config.endpoint}/encrypt", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return base64.b64decode(result['ciphertext'])
                else:
                    raise Exception(f"Generic HSM encryption failed: {await response.text()}")
    
    async def decrypt_with_hsm(self, hsm_provider: str, key_id: str, ciphertext: bytes) -> Optional[bytes]:
        """Decrypt data using HSM"""
        try:
            if hsm_provider not in self.hsm_configs:
                raise ValueError(f"HSM provider {hsm_provider} not configured")
            
            hsm_config = self.hsm_configs[hsm_provider]
            
            if hsm_config.provider == HSMProvider.AWS_CLOUDHSM:
                return await self._decrypt_aws_cloudhsm(hsm_config, key_id, ciphertext)
            elif hsm_config.provider == HSMProvider.AZURE_HSM:
                return await self._decrypt_azure_hsm(hsm_config, key_id, ciphertext)
            elif hsm_config.provider == HSMProvider.PKCS11:
                return await self._decrypt_pkcs11(hsm_config, key_id, ciphertext)
            else:
                return await self._decrypt_generic_hsm(hsm_config, key_id, ciphertext)
                
        except Exception as e:
            self.logger.error(f"HSM decryption failed: {str(e)}")
            return None
    
    async def _decrypt_aws_cloudhsm(self, hsm_config: HSMConfiguration, key_id: str, ciphertext: bytes) -> bytes:
        """Decrypt using AWS CloudHSM"""
        import base64
        
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {hsm_config.auth_token}', 'Content-Type': 'application/json'}
            payload = {
                'KeyId': key_id,
                'CiphertextBlob': base64.b64encode(ciphertext).decode('utf-8'),
                'Algorithm': 'RSA_OAEP_SHA256'
            }
            
            async with session.post(f"{hsm_config.endpoint}/decrypt", headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return base64.b64decode(result['Plaintext'])
                else:
                    raise Exception(f"AWS CloudHSM decryption failed: {await response.text()}")
    
    async def _decrypt_azure_hsm(self, hsm_config: HSMConfiguration, key_id: str, ciphertext: bytes) -> bytes:
        """Decrypt using Azure Key Vault HSM"""
        import base64
        
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {hsm_config.auth_token}', 'Content-Type': 'application/json'}
            payload = {
                'alg': 'RSA-OAEP-256',
                'value': base64.b64encode(ciphertext).decode('utf-8')
            }
            
            async with session.post(f"{hsm_config.endpoint}/keys/{key_id}/decrypt?api-version=7.4", 
                                  headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return base64.b64decode(result['value'])
                else:
                    raise Exception(f"Azure HSM decryption failed: {await response.text()}")
    
    async def _decrypt_pkcs11(self, hsm_config: HSMConfiguration, key_id: str, ciphertext: bytes) -> bytes:
        """Decrypt using PKCS#11 HSM"""
        import PyKCS11
        
        pkcs11 = PyKCS11.PyKCS11Lib()
        pkcs11.load(hsm_config.endpoint)
        
        slots = pkcs11.getSlotList()
        session = pkcs11.openSession(slots[hsm_config.slot_id or 0])
        session.login(hsm_config.auth_token)
        
        keys = session.findObjects([(PyKCS11.CKA_LABEL, key_id)])
        if not keys:
            raise Exception(f"Key {key_id} not found in PKCS#11 HSM")
        
        plaintext = session.decrypt(keys[0], list(ciphertext), PyKCS11.CKM_RSA_PKCS_OAEP)
        session.logout()
        
        return bytes(plaintext)
    
    async def _decrypt_generic_hsm(self, hsm_config: HSMConfiguration, key_id: str, ciphertext: bytes) -> bytes:
        """Decrypt using generic HSM API"""
        import base64
        
        async with aiohttp.ClientSession() as session:
            payload = {
                'key_id': key_id,
                'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
                'auth_token': hsm_config.auth_token
            }
            
            async with session.post(f"{hsm_config.endpoint}/decrypt", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return base64.b64decode(result['plaintext'])
                else:
                    raise Exception(f"Generic HSM decryption failed: {await response.text()}")
    
    async def create_security_session(self, user_id: str, security_level: SecurityLevel, duration_hours: int = 8) -> str:
        """Create a secure session with specified security level"""
        session_id = secrets.token_hex(32)
        session_data = {
            'user_id': user_id,
            'security_level': security_level.value,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(hours=duration_hours)).isoformat(),
            'access_count': 0,
            'last_access': datetime.utcnow().isoformat()
        }
        
        await self.redis.hset(f"vault_session:{session_id}", mapping=session_data)
        await self.redis.expire(f"vault_session:{session_id}", duration_hours * 3600)
        
        self.active_sessions[session_id] = session_data
        return session_id
    
    async def validate_security_session(self, session_id: str, required_level: SecurityLevel) -> bool:
        """Validate security session and check authorization level"""
        try:
            session_data = await self.redis.hgetall(f"vault_session:{session_id}")
            if not session_data:
                return False
            
            current_level = SecurityLevel(session_data[b'security_level'].decode())
            if self._security_level_value(current_level) < self._security_level_value(required_level):
                return False
            
            expires_at = datetime.fromisoformat(session_data[b'expires_at'].decode())
            if datetime.utcnow() > expires_at:
                await self.redis.delete(f"vault_session:{session_id}")
                return False
            
            access_count = int(session_data[b'access_count']) + 1
            await self.redis.hset(f"vault_session:{session_id}", 'access_count', access_count)
            await self.redis.hset(f"vault_session:{session_id}", 'last_access', datetime.utcnow().isoformat())
            
            return True
            
        except Exception as e:
            self.logger.error(f"Session validation failed: {str(e)}")
            return False
    
    def _security_level_value(self, level: SecurityLevel) -> int:
        """Get numeric value for security level comparison"""
        values = {
            SecurityLevel.STANDARD: 1,
            SecurityLevel.HIGH: 2,
            SecurityLevel.CRITICAL: 3,
            SecurityLevel.TOP_SECRET: 4
        }
        return values[level]
    
    async def audit_security_event(self, event_type: str, user_id: str, details: Dict[str, Any]) -> None:
        """Audit security events for compliance and monitoring"""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'details': json.dumps(details),
            'source_ip': details.get('source_ip', 'unknown'),
            'user_agent': details.get('user_agent', 'unknown'),
            'session_id': details.get('session_id', 'none')
        }
        
        audit_key = f"vault_audit:{datetime.utcnow().strftime('%Y-%m-%d')}"
        await self.redis.lpush(audit_key, json.dumps(audit_entry))
        await self.redis.expire(audit_key, 86400 * 365)  # Keep for 1 year
        
        self.logger.info(f"Security audit: {event_type} by {user_id}")
    
    async def get_security_metrics(self) -> Dict[str, Any]:
        """Get security framework metrics"""
        active_sessions = len(self.active_sessions)
        hsm_providers = len(self.hsm_configs)
        
        today_key = f"vault_audit:{datetime.utcnow().strftime('%Y-%m-%d')}"
        today_events = await self.redis.llen(today_key) or 0
        
        return {
            'active_sessions': active_sessions,
            'hsm_providers_configured': hsm_providers,
            'hsm_providers': list(self.hsm_configs.keys()),
            'audit_events_today': today_events,
            'framework_status': 'active',
            'last_updated': datetime.utcnow().isoformat()
        }