"""
Credential Escrow and Business Continuity System
Provides secure credential escrow and recovery for business continuity planning.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import secrets
import hashlib
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import redis


class EscrowType(Enum):
    """Types of credential escrow"""
    INDIVIDUAL = "individual"        # Single user credential escrow
    DEPARTMENT = "department"        # Department-wide escrow
    EMERGENCY = "emergency"          # Emergency access escrow
    SUCCESSION = "succession"        # Succession planning escrow
    REGULATORY = "regulatory"        # Regulatory compliance escrow
    VENDOR = "vendor"               # Third-party vendor escrow


class EscrowStatus(Enum):
    """Status of escrowed credentials"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    RECOVERED = "recovered"
    REVOKED = "revoked"


class RecoveryReason(Enum):
    """Reasons for credential recovery"""
    EMPLOYEE_DEPARTURE = "employee_departure"
    EMERGENCY_ACCESS = "emergency_access"
    SYSTEM_MAINTENANCE = "system_maintenance"
    SECURITY_INCIDENT = "security_incident"
    AUDIT_COMPLIANCE = "audit_compliance"
    DISASTER_RECOVERY = "disaster_recovery"
    BUSINESS_CONTINUITY = "business_continuity"


@dataclass
class EscrowPolicy:
    """Policy governing credential escrow"""
    escrow_type: EscrowType
    retention_days: int
    auto_recovery_triggers: List[str]
    required_approvers: int
    authorized_recovery_roles: List[str]
    encryption_level: str
    geographic_restrictions: List[str]
    notification_requirements: List[str]
    audit_frequency_days: int
    compliance_requirements: List[str]


@dataclass
class EscrowedCredential:
    """Escrowed credential with metadata"""
    escrow_id: str
    credential_id: str
    original_owner: str
    escrow_type: EscrowType
    encrypted_credential: bytes
    encryption_key_id: str
    created_at: datetime
    expires_at: Optional[datetime]
    status: EscrowStatus
    recovery_contacts: List[str]
    business_justification: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryRequest:
    """Request to recover escrowed credentials"""
    recovery_id: str
    escrow_id: str
    requesting_user: str
    recovery_reason: RecoveryReason
    business_justification: str
    emergency_override: bool
    approvals_required: int
    approvals_received: List[str]
    created_at: datetime
    expires_at: datetime
    status: str
    recovered_at: Optional[datetime] = None


class CredentialEscrowSystem:
    """Credential escrow and business continuity system"""
    
    def __init__(self, config: Dict[str, Any], redis_client: redis.Redis):
        self.config = config
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        self.escrow_policies: Dict[EscrowType, EscrowPolicy] = {}
        self.escrowed_credentials: Dict[str, EscrowedCredential] = {}
        self.recovery_requests: Dict[str, RecoveryRequest] = {}
        
    async def initialize_escrow_policies(self) -> bool:
        """Initialize escrow policies from configuration"""
        try:
            policies_config = self.config.get('vault', {}).get('escrow_policies', {})
            
            default_policies = {
                EscrowType.INDIVIDUAL: EscrowPolicy(
                    escrow_type=EscrowType.INDIVIDUAL,
                    retention_days=90,
                    auto_recovery_triggers=['user_disabled', 'termination_date'],
                    required_approvers=1,
                    authorized_recovery_roles=['manager', 'hr_admin'],
                    encryption_level='AES-256-GCM',
                    geographic_restrictions=[],
                    notification_requirements=['manager', 'security_team'],
                    audit_frequency_days=30,
                    compliance_requirements=['SOX', 'PCI']
                ),
                EscrowType.DEPARTMENT: EscrowPolicy(
                    escrow_type=EscrowType.DEPARTMENT,
                    retention_days=365,
                    auto_recovery_triggers=['department_restructure'],
                    required_approvers=2,
                    authorized_recovery_roles=['department_head', 'security_officer'],
                    encryption_level='AES-256-GCM',
                    geographic_restrictions=[],
                    notification_requirements=['department_head', 'compliance_team'],
                    audit_frequency_days=90,
                    compliance_requirements=['SOX', 'GDPR']
                ),
                EscrowType.EMERGENCY: EscrowPolicy(
                    escrow_type=EscrowType.EMERGENCY,
                    retention_days=1095,  # 3 years
                    auto_recovery_triggers=['disaster_declared', 'emergency_activation'],
                    required_approvers=3,
                    authorized_recovery_roles=['incident_commander', 'ciso', 'ceo'],
                    encryption_level='AES-256-GCM',
                    geographic_restrictions=[],
                    notification_requirements=['executive_team', 'legal_counsel'],
                    audit_frequency_days=7,
                    compliance_requirements=['SOX', 'HIPAA', 'PCI']
                )
            }
            
            for escrow_type, default_policy in default_policies.items():
                policy_config = policies_config.get(escrow_type.value, {})
                
                policy = EscrowPolicy(
                    escrow_type=escrow_type,
                    retention_days=policy_config.get('retention_days', default_policy.retention_days),
                    auto_recovery_triggers=policy_config.get('auto_recovery_triggers', default_policy.auto_recovery_triggers),
                    required_approvers=policy_config.get('required_approvers', default_policy.required_approvers),
                    authorized_recovery_roles=policy_config.get('authorized_recovery_roles', default_policy.authorized_recovery_roles),
                    encryption_level=policy_config.get('encryption_level', default_policy.encryption_level),
                    geographic_restrictions=policy_config.get('geographic_restrictions', default_policy.geographic_restrictions),
                    notification_requirements=policy_config.get('notification_requirements', default_policy.notification_requirements),
                    audit_frequency_days=policy_config.get('audit_frequency_days', default_policy.audit_frequency_days),
                    compliance_requirements=policy_config.get('compliance_requirements', default_policy.compliance_requirements)
                )
                
                self.escrow_policies[escrow_type] = policy
                await self._store_escrow_policy(policy)
            
            self.logger.info(f"Initialized {len(self.escrow_policies)} escrow policies")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize escrow policies: {str(e)}")
            return False
    
    async def _store_escrow_policy(self, policy: EscrowPolicy) -> None:
        """Store escrow policy in Redis"""
        policy_data = {
            'escrow_type': policy.escrow_type.value,
            'retention_days': policy.retention_days,
            'auto_recovery_triggers': json.dumps(policy.auto_recovery_triggers),
            'required_approvers': policy.required_approvers,
            'authorized_recovery_roles': json.dumps(policy.authorized_recovery_roles),
            'encryption_level': policy.encryption_level,
            'geographic_restrictions': json.dumps(policy.geographic_restrictions),
            'notification_requirements': json.dumps(policy.notification_requirements),
            'audit_frequency_days': policy.audit_frequency_days,
            'compliance_requirements': json.dumps(policy.compliance_requirements)
        }
        
        await self.redis.hset(f"escrow_policy:{policy.escrow_type.value}", mapping=policy_data)
    
    async def escrow_credential(self, credential_id: str, credential_data: Dict[str, Any],
                               owner_id: str, escrow_type: EscrowType,
                               business_justification: str,
                               recovery_contacts: List[str] = None) -> str:
        """Escrow a credential for business continuity"""
        try:
            if escrow_type not in self.escrow_policies:
                raise ValueError(f"No policy defined for escrow type {escrow_type}")
            
            policy = self.escrow_policies[escrow_type]
            escrow_id = secrets.token_hex(16)
            
            encryption_key = secrets.token_bytes(32)
            encrypted_data, nonce = await self._encrypt_credential(credential_data, encryption_key)
            
            encryption_key_id = await self._store_encryption_key(encryption_key, escrow_id)
            
            expires_at = datetime.utcnow() + timedelta(days=policy.retention_days) if policy.retention_days > 0 else None
            
            escrowed_credential = EscrowedCredential(
                escrow_id=escrow_id,
                credential_id=credential_id,
                original_owner=owner_id,
                escrow_type=escrow_type,
                encrypted_credential=encrypted_data,
                encryption_key_id=encryption_key_id,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                status=EscrowStatus.ACTIVE,
                recovery_contacts=recovery_contacts or [],
                business_justification=business_justification,
                metadata={
                    'policy': policy.__dict__,
                    'nonce': nonce.hex(),
                    'encryption_algorithm': policy.encryption_level,
                    'compliance_flags': policy.compliance_requirements
                }
            )
            
            self.escrowed_credentials[escrow_id] = escrowed_credential
            await self._store_escrowed_credential(escrowed_credential)
            
            await self._send_escrow_notifications(escrowed_credential, 'created')
            await self._audit_escrow_event('credential_escrowed', escrow_id, owner_id, 
                                         {'credential_id': credential_id, 'escrow_type': escrow_type.value})
            
            self.logger.info(f"Credential {credential_id} escrowed with ID {escrow_id}")
            return escrow_id
            
        except Exception as e:
            self.logger.error(f"Failed to escrow credential: {str(e)}")
            raise
    
    async def _encrypt_credential(self, credential_data: Dict[str, Any], 
                                 encryption_key: bytes) -> Tuple[bytes, bytes]:
        """Encrypt credential data using AES-256-GCM"""
        nonce = secrets.token_bytes(12)
        cipher = Cipher(algorithms.AES(encryption_key), modes.GCM(nonce))
        encryptor = cipher.encryptor()
        
        plaintext = json.dumps(credential_data).encode('utf-8')
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        encrypted_data = nonce + encryptor.tag + ciphertext
        return encrypted_data, nonce
    
    async def _decrypt_credential(self, encrypted_data: bytes, 
                                 encryption_key: bytes) -> Dict[str, Any]:
        """Decrypt credential data using AES-256-GCM"""
        nonce = encrypted_data[:12]
        tag = encrypted_data[12:28]
        ciphertext = encrypted_data[28:]
        
        cipher = Cipher(algorithms.AES(encryption_key), modes.GCM(nonce, tag))
        decryptor = cipher.decryptor()
        
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        return json.loads(plaintext.decode('utf-8'))
    
    async def _store_encryption_key(self, encryption_key: bytes, escrow_id: str) -> str:
        """Store encryption key securely (would integrate with HSM in production)"""
        key_id = secrets.token_hex(16)
        
        key_data = {
            'key_id': key_id,
            'encryption_key': encryption_key.hex(),
            'escrow_id': escrow_id,
            'created_at': datetime.utcnow().isoformat(),
            'algorithm': 'AES-256-GCM'
        }
        
        await self.redis.hset(f"escrow_key:{key_id}", mapping={
            k: v if isinstance(v, str) else str(v) for k, v in key_data.items()
        })
        await self.redis.expire(f"escrow_key:{key_id}", 86400 * 1095)  # 3 years max
        
        return key_id
    
    async def _get_encryption_key(self, key_id: str) -> Optional[bytes]:
        """Retrieve encryption key for decryption"""
        key_data = await self.redis.hgetall(f"escrow_key:{key_id}")
        if not key_data:
            return None
        
        return bytes.fromhex(key_data[b'encryption_key'].decode())
    
    async def _store_escrowed_credential(self, escrowed_credential: EscrowedCredential) -> None:
        """Store escrowed credential in Redis"""
        credential_data = {
            'credential_id': escrowed_credential.credential_id,
            'original_owner': escrowed_credential.original_owner,
            'escrow_type': escrowed_credential.escrow_type.value,
            'encrypted_credential': escrowed_credential.encrypted_credential.hex(),
            'encryption_key_id': escrowed_credential.encryption_key_id,
            'created_at': escrowed_credential.created_at.isoformat(),
            'expires_at': escrowed_credential.expires_at.isoformat() if escrowed_credential.expires_at else '',
            'status': escrowed_credential.status.value,
            'recovery_contacts': json.dumps(escrowed_credential.recovery_contacts),
            'business_justification': escrowed_credential.business_justification,
            'metadata': json.dumps(escrowed_credential.metadata)
        }
        
        await self.redis.hset(f"escrowed_credential:{escrowed_credential.escrow_id}", mapping=credential_data)
        
        if escrowed_credential.expires_at:
            expires_seconds = int((escrowed_credential.expires_at - datetime.utcnow()).total_seconds())
            if expires_seconds > 0:
                await self.redis.expire(f"escrowed_credential:{escrowed_credential.escrow_id}", expires_seconds)
        
        await self.redis.sadd("active_escrows", escrowed_credential.escrow_id)
        await self.redis.sadd(f"user_escrows:{escrowed_credential.original_owner}", escrowed_credential.escrow_id)
    
    async def initiate_credential_recovery(self, escrow_id: str, requesting_user: str,
                                         recovery_reason: RecoveryReason,
                                         business_justification: str,
                                         emergency_override: bool = False) -> str:
        """Initiate recovery of escrowed credentials"""
        try:
            if escrow_id not in self.escrowed_credentials:
                await self._load_escrowed_credential(escrow_id)
            
            if escrow_id not in self.escrowed_credentials:
                raise ValueError(f"Escrowed credential {escrow_id} not found")
            
            escrowed_credential = self.escrowed_credentials[escrow_id]
            
            if escrowed_credential.status != EscrowStatus.ACTIVE:
                raise ValueError(f"Credential escrow is not active (status: {escrowed_credential.status})")
            
            if escrowed_credential.expires_at and datetime.utcnow() > escrowed_credential.expires_at:
                escrowed_credential.status = EscrowStatus.EXPIRED
                raise ValueError("Escrowed credential has expired")
            
            policy = self.escrow_policies[escrowed_credential.escrow_type]
            
            if not emergency_override and not await self._validate_recovery_authorization(requesting_user, policy):
                raise ValueError("User is not authorized to request recovery")
            
            recovery_id = secrets.token_hex(16)
            approvals_required = 0 if emergency_override else policy.required_approvers
            
            recovery_request = RecoveryRequest(
                recovery_id=recovery_id,
                escrow_id=escrow_id,
                requesting_user=requesting_user,
                recovery_reason=recovery_reason,
                business_justification=business_justification,
                emergency_override=emergency_override,
                approvals_required=approvals_required,
                approvals_received=[],
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=24),
                status='pending'
            )
            
            self.recovery_requests[recovery_id] = recovery_request
            await self._store_recovery_request(recovery_request)
            
            if emergency_override:
                await self._complete_recovery(recovery_request)
            else:
                await self._send_recovery_notifications(recovery_request)
            
            await self._audit_escrow_event('recovery_requested', escrow_id, requesting_user, {
                'recovery_id': recovery_id,
                'reason': recovery_reason.value,
                'emergency_override': emergency_override
            })
            
            self.logger.info(f"Recovery request {recovery_id} initiated for escrow {escrow_id}")
            return recovery_id
            
        except Exception as e:
            self.logger.error(f"Failed to initiate recovery: {str(e)}")
            raise
    
    async def _validate_recovery_authorization(self, user_id: str, policy: EscrowPolicy) -> bool:
        """Validate if user is authorized to request recovery"""
        user_data = await self.redis.hgetall(f"user:{user_id}")
        if not user_data:
            return False
        
        user_roles = json.loads(user_data.get(b'roles', b'[]').decode())
        return any(role in policy.authorized_recovery_roles for role in user_roles)
    
    async def _load_escrowed_credential(self, escrow_id: str) -> None:
        """Load escrowed credential from Redis"""
        credential_data = await self.redis.hgetall(f"escrowed_credential:{escrow_id}")
        if not credential_data:
            return
        
        escrowed_credential = EscrowedCredential(
            escrow_id=escrow_id,
            credential_id=credential_data[b'credential_id'].decode(),
            original_owner=credential_data[b'original_owner'].decode(),
            escrow_type=EscrowType(credential_data[b'escrow_type'].decode()),
            encrypted_credential=bytes.fromhex(credential_data[b'encrypted_credential'].decode()),
            encryption_key_id=credential_data[b'encryption_key_id'].decode(),
            created_at=datetime.fromisoformat(credential_data[b'created_at'].decode()),
            expires_at=datetime.fromisoformat(credential_data[b'expires_at'].decode()) if credential_data[b'expires_at'].decode() else None,
            status=EscrowStatus(credential_data[b'status'].decode()),
            recovery_contacts=json.loads(credential_data[b'recovery_contacts'].decode()),
            business_justification=credential_data[b'business_justification'].decode(),
            metadata=json.loads(credential_data[b'metadata'].decode())
        )
        
        self.escrowed_credentials[escrow_id] = escrowed_credential
    
    async def _store_recovery_request(self, recovery_request: RecoveryRequest) -> None:
        """Store recovery request in Redis"""
        request_data = {
            'escrow_id': recovery_request.escrow_id,
            'requesting_user': recovery_request.requesting_user,
            'recovery_reason': recovery_request.recovery_reason.value,
            'business_justification': recovery_request.business_justification,
            'emergency_override': recovery_request.emergency_override,
            'approvals_required': recovery_request.approvals_required,
            'approvals_received': json.dumps(recovery_request.approvals_received),
            'created_at': recovery_request.created_at.isoformat(),
            'expires_at': recovery_request.expires_at.isoformat(),
            'status': recovery_request.status,
            'recovered_at': recovery_request.recovered_at.isoformat() if recovery_request.recovered_at else ''
        }
        
        await self.redis.hset(f"recovery_request:{recovery_request.recovery_id}", mapping=request_data)
        await self.redis.expire(f"recovery_request:{recovery_request.recovery_id}", 86400)  # 24 hours
    
    async def approve_recovery_request(self, recovery_id: str, approving_user: str) -> bool:
        """Approve a credential recovery request"""
        try:
            if recovery_id not in self.recovery_requests:
                await self._load_recovery_request(recovery_id)
            
            if recovery_id not in self.recovery_requests:
                raise ValueError(f"Recovery request {recovery_id} not found")
            
            recovery_request = self.recovery_requests[recovery_id]
            
            if recovery_request.status != 'pending':
                raise ValueError(f"Recovery request is not pending (status: {recovery_request.status})")
            
            if approving_user in recovery_request.approvals_received:
                raise ValueError("User has already approved this request")
            
            if datetime.utcnow() > recovery_request.expires_at:
                recovery_request.status = 'expired'
                raise ValueError("Recovery request has expired")
            
            recovery_request.approvals_received.append(approving_user)
            
            if len(recovery_request.approvals_received) >= recovery_request.approvals_required:
                await self._complete_recovery(recovery_request)
            
            await self._store_recovery_request(recovery_request)
            
            await self._audit_escrow_event('recovery_approved', recovery_request.escrow_id, approving_user, {
                'recovery_id': recovery_id,
                'approvals_received': len(recovery_request.approvals_received),
                'approvals_required': recovery_request.approvals_required
            })
            
            self.logger.info(f"Recovery request {recovery_id} approved by {approving_user}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to approve recovery: {str(e)}")
            return False
    
    async def _complete_recovery(self, recovery_request: RecoveryRequest) -> Dict[str, Any]:
        """Complete credential recovery and return decrypted credential"""
        try:
            escrow_id = recovery_request.escrow_id
            escrowed_credential = self.escrowed_credentials[escrow_id]
            
            encryption_key = await self._get_encryption_key(escrowed_credential.encryption_key_id)
            if not encryption_key:
                raise ValueError("Encryption key not found")
            
            decrypted_credential = await self._decrypt_credential(
                escrowed_credential.encrypted_credential, encryption_key
            )
            
            recovery_request.status = 'completed'
            recovery_request.recovered_at = datetime.utcnow()
            escrowed_credential.status = EscrowStatus.RECOVERED
            
            await self._store_recovery_request(recovery_request)
            await self._store_escrowed_credential(escrowed_credential)
            
            recovery_result = {
                'recovery_id': recovery_request.recovery_id,
                'escrow_id': escrow_id,
                'recovered_credential': decrypted_credential,
                'recovered_at': recovery_request.recovered_at.isoformat(),
                'original_owner': escrowed_credential.original_owner,
                'recovery_reason': recovery_request.recovery_reason.value
            }
            
            await self.redis.hset(f"recovery_result:{recovery_request.recovery_id}", mapping={
                'recovery_data': json.dumps(recovery_result),
                'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat()
            })
            await self.redis.expire(f"recovery_result:{recovery_request.recovery_id}", 3600)  # 1 hour
            
            await self._send_recovery_notifications(recovery_request)
            await self._audit_escrow_event('credential_recovered', escrow_id, recovery_request.requesting_user, {
                'recovery_id': recovery_request.recovery_id,
                'approvers': recovery_request.approvals_received
            })
            
            self.logger.info(f"Credential recovery completed for escrow {escrow_id}")
            return recovery_result
            
        except Exception as e:
            self.logger.error(f"Failed to complete recovery: {str(e)}")
            raise
    
    async def _load_recovery_request(self, recovery_id: str) -> None:
        """Load recovery request from Redis"""
        request_data = await self.redis.hgetall(f"recovery_request:{recovery_id}")
        if not request_data:
            return
        
        recovery_request = RecoveryRequest(
            recovery_id=recovery_id,
            escrow_id=request_data[b'escrow_id'].decode(),
            requesting_user=request_data[b'requesting_user'].decode(),
            recovery_reason=RecoveryReason(request_data[b'recovery_reason'].decode()),
            business_justification=request_data[b'business_justification'].decode(),
            emergency_override=request_data[b'emergency_override'].decode().lower() == 'true',
            approvals_required=int(request_data[b'approvals_required']),
            approvals_received=json.loads(request_data[b'approvals_received'].decode()),
            created_at=datetime.fromisoformat(request_data[b'created_at'].decode()),
            expires_at=datetime.fromisoformat(request_data[b'expires_at'].decode()),
            status=request_data[b'status'].decode(),
            recovered_at=datetime.fromisoformat(request_data[b'recovered_at'].decode()) if request_data[b'recovered_at'].decode() else None
        )
        
        self.recovery_requests[recovery_id] = recovery_request
    
    async def get_recovered_credential(self, recovery_id: str, requesting_user: str) -> Optional[Dict[str, Any]]:
        """Get recovered credential data (one-time access)"""
        try:
            recovery_data = await self.redis.hgetall(f"recovery_result:{recovery_id}")
            if not recovery_data:
                return None
            
            recovery_result = json.loads(recovery_data[b'recovery_data'].decode())
            
            if recovery_id not in self.recovery_requests:
                await self._load_recovery_request(recovery_id)
            
            if (recovery_id in self.recovery_requests and 
                self.recovery_requests[recovery_id].requesting_user != requesting_user):
                raise ValueError("Unauthorized access to recovery result")
            
            await self.redis.delete(f"recovery_result:{recovery_id}")
            
            return recovery_result
            
        except Exception as e:
            self.logger.error(f"Failed to get recovered credential: {str(e)}")
            return None
    
    async def _send_escrow_notifications(self, escrowed_credential: EscrowedCredential, 
                                       event_type: str) -> None:
        """Send notifications about escrow events"""
        try:
            policy = self.escrow_policies[escrowed_credential.escrow_type]
            
            notification_data = {
                'escrow_id': escrowed_credential.escrow_id,
                'credential_id': escrowed_credential.credential_id,
                'original_owner': escrowed_credential.original_owner,
                'event_type': event_type,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            for requirement in policy.notification_requirements:
                await self.redis.lpush(f"notifications:{requirement}", json.dumps(notification_data))
            
            for contact in escrowed_credential.recovery_contacts:
                await self.redis.lpush(f"notifications:{contact}", json.dumps(notification_data))
                
        except Exception as e:
            self.logger.error(f"Failed to send escrow notifications: {str(e)}")
    
    async def _send_recovery_notifications(self, recovery_request: RecoveryRequest) -> None:
        """Send notifications about recovery events"""
        try:
            notification_data = {
                'recovery_id': recovery_request.recovery_id,
                'escrow_id': recovery_request.escrow_id,
                'requesting_user': recovery_request.requesting_user,
                'recovery_reason': recovery_request.recovery_reason.value,
                'status': recovery_request.status,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            await self.redis.lpush("notifications:security_team", json.dumps(notification_data))
            await self.redis.lpush("notifications:compliance_team", json.dumps(notification_data))
            
        except Exception as e:
            self.logger.error(f"Failed to send recovery notifications: {str(e)}")
    
    async def _audit_escrow_event(self, event_type: str, escrow_id: str, user_id: str, 
                                details: Dict[str, Any]) -> None:
        """Audit escrow-related events"""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'escrow_id': escrow_id,
            'user_id': user_id,
            'details': details,
            'audit_id': secrets.token_hex(8)
        }
        
        audit_key = f"escrow_audit:{datetime.utcnow().strftime('%Y-%m-%d')}"
        await self.redis.lpush(audit_key, json.dumps(audit_entry))
        await self.redis.expire(audit_key, 86400 * 2555)  # 7 years retention
        
        self.logger.info(f"Escrow audit: {event_type} for {escrow_id} by {user_id}")
    
    async def get_user_escrows(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all escrows for a user"""
        try:
            user_escrows = []
            escrow_ids = await self.redis.smembers(f"user_escrows:{user_id}")
            
            for escrow_id in escrow_ids:
                escrow_id_str = escrow_id.decode() if isinstance(escrow_id, bytes) else escrow_id
                
                if escrow_id_str not in self.escrowed_credentials:
                    await self._load_escrowed_credential(escrow_id_str)
                
                if escrow_id_str in self.escrowed_credentials:
                    escrow = self.escrowed_credentials[escrow_id_str]
                    escrow_info = {
                        'escrow_id': escrow.escrow_id,
                        'credential_id': escrow.credential_id,
                        'escrow_type': escrow.escrow_type.value,
                        'status': escrow.status.value,
                        'created_at': escrow.created_at.isoformat(),
                        'expires_at': escrow.expires_at.isoformat() if escrow.expires_at else None,
                        'business_justification': escrow.business_justification
                    }
                    user_escrows.append(escrow_info)
            
            return user_escrows
            
        except Exception as e:
            self.logger.error(f"Failed to get user escrows: {str(e)}")
            return []
    
    async def get_escrow_metrics(self) -> Dict[str, Any]:
        """Get escrow system metrics"""
        try:
            active_escrows = await self.redis.scard("active_escrows")
            
            metrics = {
                'active_escrows': active_escrows,
                'escrow_types': {},
                'pending_recoveries': len([r for r in self.recovery_requests.values() if r.status == 'pending']),
                'completed_recoveries_today': 0,
                'compliance_status': 'compliant'
            }
            
            for escrow_type in EscrowType:
                type_count = len([e for e in self.escrowed_credentials.values() 
                                if e.escrow_type == escrow_type and e.status == EscrowStatus.ACTIVE])
                metrics['escrow_types'][escrow_type.value] = type_count
            
            today_key = f"escrow_audit:{datetime.utcnow().strftime('%Y-%m-%d')}"
            today_events = await self.redis.llen(today_key) or 0
            metrics['audit_events_today'] = today_events
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get escrow metrics: {str(e)}")
            return {'error': str(e)}