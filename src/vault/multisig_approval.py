"""
Multi-Signature Approval System for Sensitive Vault Operations
Implements cryptographic multi-signature approval for critical actions.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import secrets
import hashlib
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature, decode_dss_signature
import redis


class ApprovalLevel(Enum):
    """Different levels of approval required"""
    LOW = "low"           # 1 out of 2 approvers
    MEDIUM = "medium"     # 2 out of 3 approvers  
    HIGH = "high"         # 3 out of 5 approvers
    CRITICAL = "critical" # 5 out of 7 approvers


class OperationType(Enum):
    """Types of operations requiring approval"""
    CREDENTIAL_ACCESS = "credential_access"
    CREDENTIAL_CREATION = "credential_creation"
    CREDENTIAL_DELETION = "credential_deletion"
    CREDENTIAL_ROTATION = "credential_rotation"
    VAULT_CONFIGURATION = "vault_configuration"
    USER_MANAGEMENT = "user_management"
    BACKUP_RESTORATION = "backup_restoration"
    EMERGENCY_REVOCATION = "emergency_revocation"
    SHARE_RECOVERY = "share_recovery"
    HSM_OPERATIONS = "hsm_operations"


class ApprovalStatus(Enum):
    """Status of approval requests"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"


@dataclass
class ApprovalPolicy:
    """Policy defining approval requirements for operations"""
    operation_type: OperationType
    approval_level: ApprovalLevel
    required_approvers: int
    total_approvers: int
    approver_roles: List[str]
    timeout_hours: int
    emergency_bypass: bool
    geographic_restrictions: List[str]
    time_restrictions: Dict[str, Any]


@dataclass
class DigitalSignature:
    """Digital signature for approval"""
    signer_id: str
    signature: bytes
    public_key: bytes
    algorithm: str
    timestamp: datetime
    message_hash: str


@dataclass
class ApprovalRequest:
    """Request requiring multi-signature approval"""
    request_id: str
    operation_type: OperationType
    operation_details: Dict[str, Any]
    requesting_user: str
    required_approvals: int
    total_approvers: int
    eligible_approvers: List[str]
    current_approvals: List[DigitalSignature] = field(default_factory=list)
    rejections: List[DigitalSignature] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=24))
    status: ApprovalStatus = ApprovalStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiSignatureApproval:
    """Multi-signature approval system for sensitive vault operations"""
    
    def __init__(self, config: Dict[str, Any], redis_client: redis.Redis):
        self.config = config
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        self.approval_policies: Dict[OperationType, ApprovalPolicy] = {}
        self.pending_requests: Dict[str, ApprovalRequest] = {}
        self.approver_keys: Dict[str, Dict[str, Any]] = {}
        
    async def initialize_approval_policies(self) -> bool:
        """Initialize approval policies from configuration"""
        try:
            policies_config = self.config.get('vault', {}).get('approval_policies', {})
            
            default_policies = {
                OperationType.CREDENTIAL_ACCESS: ApprovalPolicy(
                    operation_type=OperationType.CREDENTIAL_ACCESS,
                    approval_level=ApprovalLevel.LOW,
                    required_approvers=1,
                    total_approvers=2,
                    approver_roles=['vault_admin', 'security_officer'],
                    timeout_hours=2,
                    emergency_bypass=True,
                    geographic_restrictions=[],
                    time_restrictions={'business_hours_only': False}
                ),
                OperationType.CREDENTIAL_DELETION: ApprovalPolicy(
                    operation_type=OperationType.CREDENTIAL_DELETION,
                    approval_level=ApprovalLevel.HIGH,
                    required_approvers=3,
                    total_approvers=5,
                    approver_roles=['vault_admin', 'security_officer', 'compliance_officer'],
                    timeout_hours=24,
                    emergency_bypass=False,
                    geographic_restrictions=[],
                    time_restrictions={'business_hours_only': True}
                ),
                OperationType.VAULT_CONFIGURATION: ApprovalPolicy(
                    operation_type=OperationType.VAULT_CONFIGURATION,
                    approval_level=ApprovalLevel.CRITICAL,
                    required_approvers=5,
                    total_approvers=7,
                    approver_roles=['vault_admin', 'security_officer', 'compliance_officer', 'ciso'],
                    timeout_hours=48,
                    emergency_bypass=False,
                    geographic_restrictions=[],
                    time_restrictions={'business_hours_only': True}
                )
            }
            
            for op_type, default_policy in default_policies.items():
                policy_config = policies_config.get(op_type.value, {})
                
                policy = ApprovalPolicy(
                    operation_type=op_type,
                    approval_level=ApprovalLevel(policy_config.get('approval_level', default_policy.approval_level.value)),
                    required_approvers=policy_config.get('required_approvers', default_policy.required_approvers),
                    total_approvers=policy_config.get('total_approvers', default_policy.total_approvers),
                    approver_roles=policy_config.get('approver_roles', default_policy.approver_roles),
                    timeout_hours=policy_config.get('timeout_hours', default_policy.timeout_hours),
                    emergency_bypass=policy_config.get('emergency_bypass', default_policy.emergency_bypass),
                    geographic_restrictions=policy_config.get('geographic_restrictions', []),
                    time_restrictions=policy_config.get('time_restrictions', {})
                )
                
                self.approval_policies[op_type] = policy
                await self._store_approval_policy(policy)
            
            self.logger.info(f"Initialized {len(self.approval_policies)} approval policies")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize approval policies: {str(e)}")
            return False
    
    async def _store_approval_policy(self, policy: ApprovalPolicy) -> None:
        """Store approval policy in Redis"""
        policy_data = {
            'operation_type': policy.operation_type.value,
            'approval_level': policy.approval_level.value,
            'required_approvers': policy.required_approvers,
            'total_approvers': policy.total_approvers,
            'approver_roles': json.dumps(policy.approver_roles),
            'timeout_hours': policy.timeout_hours,
            'emergency_bypass': policy.emergency_bypass,
            'geographic_restrictions': json.dumps(policy.geographic_restrictions),
            'time_restrictions': json.dumps(policy.time_restrictions)
        }
        
        await self.redis.hset(f"approval_policy:{policy.operation_type.value}", mapping=policy_data)
    
    async def register_approver(self, user_id: str, public_key: bytes, 
                              private_key: Optional[bytes] = None, 
                              roles: List[str] = None) -> bool:
        """Register an approver with their cryptographic keys"""
        try:
            approver_data = {
                'user_id': user_id,
                'public_key': public_key,
                'roles': roles or [],
                'registered_at': datetime.utcnow(),
                'status': 'active'
            }
            
            if private_key:
                approver_data['private_key'] = private_key
            
            self.approver_keys[user_id] = approver_data
            
            redis_data = {
                'public_key': public_key.hex(),
                'roles': json.dumps(roles or []),
                'registered_at': approver_data['registered_at'].isoformat(),
                'status': 'active'
            }
            
            await self.redis.hset(f"approver:{user_id}", mapping=redis_data)
            
            self.logger.info(f"Registered approver {user_id} with roles {roles}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register approver: {str(e)}")
            return False
    
    async def create_approval_request(self, operation_type: OperationType, 
                                    operation_details: Dict[str, Any],
                                    requesting_user: str) -> str:
        """Create a new approval request"""
        try:
            if operation_type not in self.approval_policies:
                raise ValueError(f"No policy defined for operation type {operation_type}")
            
            policy = self.approval_policies[operation_type]
            
            if not self._validate_time_restrictions(policy.time_restrictions):
                raise ValueError("Operation not allowed during current time restrictions")
            
            eligible_approvers = await self._get_eligible_approvers(policy.approver_roles)
            if len(eligible_approvers) < policy.total_approvers:
                raise ValueError(f"Insufficient eligible approvers ({len(eligible_approvers)} < {policy.total_approvers})")
            
            request_id = secrets.token_hex(16)
            expires_at = datetime.utcnow() + timedelta(hours=policy.timeout_hours)
            
            approval_request = ApprovalRequest(
                request_id=request_id,
                operation_type=operation_type,
                operation_details=operation_details,
                requesting_user=requesting_user,
                required_approvals=policy.required_approvers,
                total_approvers=policy.total_approvers,
                eligible_approvers=eligible_approvers,
                expires_at=expires_at,
                metadata={'policy': policy.__dict__}
            )
            
            self.pending_requests[request_id] = approval_request
            await self._store_approval_request(approval_request)
            
            self.logger.info(f"Created approval request {request_id} for {operation_type.value}")
            return request_id
            
        except Exception as e:
            self.logger.error(f"Failed to create approval request: {str(e)}")
            raise
    
    def _validate_time_restrictions(self, time_restrictions: Dict[str, Any]) -> bool:
        """Validate current time against restrictions"""
        if not time_restrictions.get('business_hours_only', False):
            return True
        
        now = datetime.utcnow()
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        hour = now.hour
        
        if weekday >= 5:  # Weekend
            return False
        
        if hour < 8 or hour > 18:  # Outside 8 AM - 6 PM
            return False
        
        return True
    
    async def _get_eligible_approvers(self, required_roles: List[str]) -> List[str]:
        """Get list of users eligible to approve based on roles"""
        eligible = []
        
        approver_keys = await self.redis.keys("approver:*")
        for key in approver_keys:
            user_id = key.decode().split(':', 1)[1] if isinstance(key, bytes) else key.split(':', 1)[1]
            approver_data = await self.redis.hgetall(key)
            
            if approver_data.get(b'status', b'').decode() == 'active':
                user_roles = json.loads(approver_data.get(b'roles', b'[]').decode())
                if any(role in required_roles for role in user_roles):
                    eligible.append(user_id)
        
        return eligible
    
    async def _store_approval_request(self, request: ApprovalRequest) -> None:
        """Store approval request in Redis"""
        request_data = {
            'operation_type': request.operation_type.value,
            'operation_details': json.dumps(request.operation_details),
            'requesting_user': request.requesting_user,
            'required_approvals': request.required_approvals,
            'total_approvers': request.total_approvers,
            'eligible_approvers': json.dumps(request.eligible_approvers),
            'created_at': request.created_at.isoformat(),
            'expires_at': request.expires_at.isoformat(),
            'status': request.status.value,
            'metadata': json.dumps(request.metadata)
        }
        
        await self.redis.hset(f"approval_request:{request.request_id}", mapping=request_data)
        await self.redis.expire(f"approval_request:{request.request_id}", 
                               int((request.expires_at - datetime.utcnow()).total_seconds()))
    
    async def submit_approval(self, request_id: str, approver_id: str, 
                            approve: bool, signature: bytes, 
                            reason: str = "") -> bool:
        """Submit approval or rejection with digital signature"""
        try:
            if request_id not in self.pending_requests:
                await self._load_approval_request(request_id)
            
            if request_id not in self.pending_requests:
                raise ValueError(f"Approval request {request_id} not found")
            
            request = self.pending_requests[request_id]
            
            if request.status != ApprovalStatus.PENDING:
                raise ValueError(f"Request is not pending (status: {request.status})")
            
            if datetime.utcnow() > request.expires_at:
                request.status = ApprovalStatus.EXPIRED
                raise ValueError("Approval request has expired")
            
            if approver_id not in request.eligible_approvers:
                raise ValueError("User is not eligible to approve this request")
            
            already_approved = any(sig.signer_id == approver_id for sig in request.current_approvals)
            already_rejected = any(sig.signer_id == approver_id for sig in request.rejections)
            
            if already_approved or already_rejected:
                raise ValueError("User has already provided approval/rejection")
            
            approver_data = await self.redis.hgetall(f"approver:{approver_id}")
            if not approver_data:
                raise ValueError("Approver not found or not registered")
            
            public_key_bytes = bytes.fromhex(approver_data[b'public_key'].decode())
            
            if not await self._verify_signature(request, signature, public_key_bytes):
                raise ValueError("Invalid signature")
            
            digital_signature = DigitalSignature(
                signer_id=approver_id,
                signature=signature,
                public_key=public_key_bytes,
                algorithm='RSA_PSS_SHA256',
                timestamp=datetime.utcnow(),
                message_hash=self._calculate_request_hash(request)
            )
            
            if approve:
                request.current_approvals.append(digital_signature)
                
                if len(request.current_approvals) >= request.required_approvals:
                    request.status = ApprovalStatus.APPROVED
                    await self._execute_approved_operation(request)
                
            else:
                request.rejections.append(digital_signature)
                request.status = ApprovalStatus.REJECTED
            
            await self._update_approval_request(request)
            
            action = "approved" if approve else "rejected"
            self.logger.info(f"Request {request_id} {action} by {approver_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to submit approval: {str(e)}")
            return False
    
    async def _load_approval_request(self, request_id: str) -> None:
        """Load approval request from Redis"""
        request_data = await self.redis.hgetall(f"approval_request:{request_id}")
        if not request_data:
            return
        
        operation_type = OperationType(request_data[b'operation_type'].decode())
        
        request = ApprovalRequest(
            request_id=request_id,
            operation_type=operation_type,
            operation_details=json.loads(request_data[b'operation_details'].decode()),
            requesting_user=request_data[b'requesting_user'].decode(),
            required_approvals=int(request_data[b'required_approvals']),
            total_approvers=int(request_data[b'total_approvers']),
            eligible_approvers=json.loads(request_data[b'eligible_approvers'].decode()),
            created_at=datetime.fromisoformat(request_data[b'created_at'].decode()),
            expires_at=datetime.fromisoformat(request_data[b'expires_at'].decode()),
            status=ApprovalStatus(request_data[b'status'].decode()),
            metadata=json.loads(request_data[b'metadata'].decode())
        )
        
        approvals_data = await self.redis.lrange(f"approvals:{request_id}", 0, -1)
        for approval_json in approvals_data:
            approval_data = json.loads(approval_json.decode() if isinstance(approval_json, bytes) else approval_json)
            signature = DigitalSignature(
                signer_id=approval_data['signer_id'],
                signature=bytes.fromhex(approval_data['signature']),
                public_key=bytes.fromhex(approval_data['public_key']),
                algorithm=approval_data['algorithm'],
                timestamp=datetime.fromisoformat(approval_data['timestamp']),
                message_hash=approval_data['message_hash']
            )
            
            if approval_data.get('is_rejection', False):
                request.rejections.append(signature)
            else:
                request.current_approvals.append(signature)
        
        self.pending_requests[request_id] = request
    
    async def _verify_signature(self, request: ApprovalRequest, signature: bytes, 
                               public_key_bytes: bytes) -> bool:
        """Verify digital signature against the approval request"""
        try:
            public_key = serialization.load_der_public_key(public_key_bytes)
            message_hash = self._calculate_request_hash(request).encode()
            
            if isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(
                    signature,
                    message_hash,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                return True
            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                public_key.verify(signature, message_hash, ec.ECDSA(hashes.SHA256()))
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Signature verification failed: {str(e)}")
            return False
    
    def _calculate_request_hash(self, request: ApprovalRequest) -> str:
        """Calculate hash of approval request for signature verification"""
        hash_data = {
            'request_id': request.request_id,
            'operation_type': request.operation_type.value,
            'operation_details': request.operation_details,
            'requesting_user': request.requesting_user,
            'created_at': request.created_at.isoformat()
        }
        
        hash_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    async def _update_approval_request(self, request: ApprovalRequest) -> None:
        """Update approval request in Redis"""
        await self.redis.hset(f"approval_request:{request.request_id}", 'status', request.status.value)
        
        for i, approval in enumerate(request.current_approvals):
            approval_data = {
                'signer_id': approval.signer_id,
                'signature': approval.signature.hex(),
                'public_key': approval.public_key.hex(),
                'algorithm': approval.algorithm,
                'timestamp': approval.timestamp.isoformat(),
                'message_hash': approval.message_hash,
                'is_rejection': False
            }
            await self.redis.lpush(f"approvals:{request.request_id}", json.dumps(approval_data))
        
        for i, rejection in enumerate(request.rejections):
            rejection_data = {
                'signer_id': rejection.signer_id,
                'signature': rejection.signature.hex(),
                'public_key': rejection.public_key.hex(),
                'algorithm': rejection.algorithm,
                'timestamp': rejection.timestamp.isoformat(),
                'message_hash': rejection.message_hash,
                'is_rejection': True
            }
            await self.redis.lpush(f"approvals:{request.request_id}", json.dumps(rejection_data))
    
    async def _execute_approved_operation(self, request: ApprovalRequest) -> bool:
        """Execute the approved operation"""
        try:
            operation_type = request.operation_type
            details = request.operation_details
            
            execution_result = {
                'request_id': request.request_id,
                'operation_type': operation_type.value,
                'executed_at': datetime.utcnow().isoformat(),
                'executed_by': 'multisig_system',
                'approvers': [sig.signer_id for sig in request.current_approvals],
                'result': 'success'
            }
            
            if operation_type == OperationType.CREDENTIAL_ACCESS:
                result = await self._execute_credential_access(details)
            elif operation_type == OperationType.CREDENTIAL_DELETION:
                result = await self._execute_credential_deletion(details)
            elif operation_type == OperationType.VAULT_CONFIGURATION:
                result = await self._execute_vault_configuration(details)
            elif operation_type == OperationType.EMERGENCY_REVOCATION:
                result = await self._execute_emergency_revocation(details)
            else:
                result = {'success': True, 'message': f'Operation {operation_type.value} queued for execution'}
            
            execution_result['operation_result'] = result
            request.status = ApprovalStatus.EXECUTED
            
            await self.redis.hset(f"execution_result:{request.request_id}", mapping=execution_result)
            
            self.logger.info(f"Executed approved operation {request.request_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to execute approved operation: {str(e)}")
            return False
    
    async def _execute_credential_access(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute credential access operation"""
        return {'success': True, 'message': 'Credential access granted'}
    
    async def _execute_credential_deletion(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute credential deletion operation"""
        return {'success': True, 'message': 'Credential deleted'}
    
    async def _execute_vault_configuration(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute vault configuration operation"""
        return {'success': True, 'message': 'Vault configuration updated'}
    
    async def _execute_emergency_revocation(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute emergency revocation operation"""
        return {'success': True, 'message': 'Emergency revocation completed'}
    
    async def get_pending_approvals(self, user_id: str) -> List[Dict[str, Any]]:
        """Get pending approval requests for a user"""
        pending_approvals = []
        
        approver_data = await self.redis.hgetall(f"approver:{user_id}")
        if not approver_data:
            return pending_approvals
        
        user_roles = json.loads(approver_data.get(b'roles', b'[]').decode())
        
        request_keys = await self.redis.keys("approval_request:*")
        for key in request_keys:
            request_id = key.decode().split(':', 1)[1] if isinstance(key, bytes) else key.split(':', 1)[1]
            
            if request_id not in self.pending_requests:
                await self._load_approval_request(request_id)
            
            if request_id in self.pending_requests:
                request = self.pending_requests[request_id]
                
                if (request.status == ApprovalStatus.PENDING and 
                    user_id in request.eligible_approvers and
                    not any(sig.signer_id == user_id for sig in request.current_approvals) and
                    not any(sig.signer_id == user_id for sig in request.rejections)):
                    
                    approval_info = {
                        'request_id': request.request_id,
                        'operation_type': request.operation_type.value,
                        'operation_details': request.operation_details,
                        'requesting_user': request.requesting_user,
                        'required_approvals': request.required_approvals,
                        'current_approvals': len(request.current_approvals),
                        'created_at': request.created_at.isoformat(),
                        'expires_at': request.expires_at.isoformat(),
                        'time_remaining_hours': (request.expires_at - datetime.utcnow()).total_seconds() / 3600
                    }
                    pending_approvals.append(approval_info)
        
        return pending_approvals
    
    async def get_approval_status(self, request_id: str) -> Dict[str, Any]:
        """Get status of an approval request"""
        if request_id not in self.pending_requests:
            await self._load_approval_request(request_id)
        
        if request_id not in self.pending_requests:
            return {'error': 'Request not found'}
        
        request = self.pending_requests[request_id]
        
        return {
            'request_id': request_id,
            'status': request.status.value,
            'operation_type': request.operation_type.value,
            'requesting_user': request.requesting_user,
            'required_approvals': request.required_approvals,
            'current_approvals': len(request.current_approvals),
            'approvers': [sig.signer_id for sig in request.current_approvals],
            'rejections': len(request.rejections),
            'rejecters': [sig.signer_id for sig in request.rejections],
            'created_at': request.created_at.isoformat(),
            'expires_at': request.expires_at.isoformat(),
            'time_remaining_hours': max(0, (request.expires_at - datetime.utcnow()).total_seconds() / 3600)
        }
    
    async def revoke_approval_request(self, request_id: str, revoking_user: str) -> bool:
        """Revoke a pending approval request"""
        try:
            if request_id not in self.pending_requests:
                await self._load_approval_request(request_id)
            
            if request_id not in self.pending_requests:
                raise ValueError("Request not found")
            
            request = self.pending_requests[request_id]
            
            if request.requesting_user != revoking_user:
                raise ValueError("Only the requesting user can revoke the request")
            
            if request.status != ApprovalStatus.PENDING:
                raise ValueError("Can only revoke pending requests")
            
            request.status = ApprovalStatus.REJECTED
            await self._update_approval_request(request)
            
            self.logger.info(f"Approval request {request_id} revoked by {revoking_user}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to revoke approval request: {str(e)}")
            return False