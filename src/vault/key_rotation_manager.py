"""
Key Rotation and Version Management System
Manages encryption key lifecycle, rotation, and versioning for the credential vault.

Author: Lance James, Unit 221B
"""

import asyncio
import logging
import json
import secrets
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import redis

from .database_manager import DatabaseManager
from .encryption_engine import EncryptionEngine, EncryptedData
from .audit_manager import AuditManager, AuditEventType, AuditResult
from .performance_optimizer import PerformanceOptimizer


class RotationTrigger(Enum):
    """Triggers for key rotation"""
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    COMPROMISE = "compromise"
    POLICY = "policy"
    EMERGENCY = "emergency"


class RotationStatus(Enum):
    """Status of key rotation operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK = "rollback"


class KeyStatus(Enum):
    """Status of encryption keys"""
    ACTIVE = "active"
    RETIRED = "retired"
    COMPROMISED = "compromised"
    PENDING_RETIREMENT = "pending_retirement"


@dataclass
class KeyVersion:
    """Encryption key version metadata"""
    version: int
    key_hash: str
    algorithm: str
    created_at: datetime
    activated_at: Optional[datetime]
    retired_at: Optional[datetime]
    status: KeyStatus
    created_by: str
    rotation_trigger: Optional[RotationTrigger] = None
    credentials_encrypted: int = 0
    hsm_key_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RotationOperation:
    """Key rotation operation tracking"""
    rotation_id: str
    old_key_version: int
    new_key_version: int
    trigger: RotationTrigger
    initiated_by: str
    initiated_at: datetime
    status: RotationStatus
    progress_percent: float = 0.0
    credentials_rotated: int = 0
    total_credentials: int = 0
    errors: List[str] = field(default_factory=list)
    completed_at: Optional[datetime] = None
    rollback_reason: Optional[str] = None


@dataclass
class RotationPolicy:
    """Key rotation policy configuration"""
    policy_id: str
    name: str
    description: str
    rotation_interval_days: int
    max_key_age_days: int
    max_credentials_per_key: int
    automatic_rotation: bool
    require_approval: bool
    notification_days_before: int
    emergency_rotation_enabled: bool
    compliance_frameworks: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)


class KeyRotationManager:
    """Comprehensive key rotation and version management"""
    
    def __init__(self, config: Dict[str, Any], database_manager: DatabaseManager,
                 encryption_engine: EncryptionEngine, audit_manager: AuditManager,
                 performance_optimizer: PerformanceOptimizer, redis_client: Optional[redis.Redis]):
        self.config = config
        self.database_manager = database_manager
        self.encryption_engine = encryption_engine
        self.audit_manager = audit_manager
        self.performance_optimizer = performance_optimizer
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        
        # Rotation configuration
        rotation_config = config.get('vault', {}).get('key_rotation', {})
        self.default_rotation_days = rotation_config.get('default_rotation_days', 90)
        self.max_key_age_days = rotation_config.get('max_key_age_days', 365)
        self.max_credentials_per_key = rotation_config.get('max_credentials_per_key', 10000)
        self.automatic_rotation = rotation_config.get('automatic_rotation', True)
        self.require_approval = rotation_config.get('require_approval', True)
        self.notification_days = rotation_config.get('notification_days_before', 7)
        
        # Key version tracking
        self.key_versions: Dict[int, KeyVersion] = {}
        self.active_rotations: Dict[str, RotationOperation] = {}
        self.rotation_policies: Dict[str, RotationPolicy] = {}
        
        # Current key version
        self.current_key_version = 1
        
        # Rotation queue
        self.rotation_queue = asyncio.Queue()
        
    async def initialize(self) -> bool:
        """Initialize key rotation manager"""
        try:
            # Load existing key versions
            await self._load_key_versions()
            
            # Load rotation policies
            await self._load_rotation_policies()
            
            # Initialize default policy if none exist
            if not self.rotation_policies:
                await self._create_default_rotation_policy()
            
            # Start background tasks
            asyncio.create_task(self._rotation_scheduler())
            asyncio.create_task(self._rotation_processor())
            asyncio.create_task(self._key_lifecycle_monitor())
            
            self.logger.info("Key rotation manager initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize key rotation manager: {str(e)}")
            return False
    
    async def create_key_version(self, created_by: str, trigger: RotationTrigger = RotationTrigger.MANUAL,
                               algorithm: str = "AES-256-GCM") -> int:
        """Create new key version"""
        try:
            new_version = max(self.key_versions.keys(), default=0) + 1
            
            # Generate new key (this would integrate with the encryption engine)
            key_material = secrets.token_bytes(32)  # 256-bit key
            key_hash = hashlib.sha256(key_material).hexdigest()
            
            # Create key version metadata
            key_version = KeyVersion(
                version=new_version,
                key_hash=key_hash,
                algorithm=algorithm,
                created_at=datetime.utcnow(),
                activated_at=None,
                retired_at=None,
                status=KeyStatus.PENDING_RETIREMENT,  # Not active until rotation completes
                created_by=created_by,
                rotation_trigger=trigger
            )
            
            # Store key version
            self.key_versions[new_version] = key_version
            
            # Store in database
            await self.database_manager.store_encryption_key(
                key_version=new_version,
                key_hash=key_hash,
                algorithm=algorithm,
                metadata=key_version.__dict__
            )
            
            # Log audit event
            await self.audit_manager.log_event(
                AuditEventType.CREATE, created_by, "create_key_version",
                AuditResult.SUCCESS, None,
                metadata={
                    'key_version': new_version,
                    'algorithm': algorithm,
                    'trigger': trigger.value
                }
            )
            
            self.logger.info(f"Created key version {new_version}")
            return new_version
            
        except Exception as e:
            self.logger.error(f"Failed to create key version: {str(e)}")
            raise
    
    async def initiate_key_rotation(self, trigger: RotationTrigger, initiated_by: str,
                                  reason: str = "", target_credentials: List[str] = None) -> str:
        """Initiate key rotation operation"""
        try:
            rotation_id = secrets.token_urlsafe(16)
            
            # Get current active key version
            current_version = await self._get_active_key_version()
            if not current_version:
                raise ValueError("No active key version found")
            
            # Create new key version
            new_version = await self.create_key_version(initiated_by, trigger)
            
            # Count credentials to rotate
            if target_credentials:
                total_credentials = len(target_credentials)
            else:
                # Count all credentials using current key version
                total_credentials = await self._count_credentials_for_key_version(current_version)
            
            # Create rotation operation
            rotation_op = RotationOperation(
                rotation_id=rotation_id,
                old_key_version=current_version,
                new_key_version=new_version,
                trigger=trigger,
                initiated_by=initiated_by,
                initiated_at=datetime.utcnow(),
                status=RotationStatus.PENDING,
                total_credentials=total_credentials
            )
            
            self.active_rotations[rotation_id] = rotation_op
            
            # Add to rotation queue
            await self.rotation_queue.put({
                'rotation_id': rotation_id,
                'target_credentials': target_credentials,
                'reason': reason
            })
            
            # Log audit event
            await self.audit_manager.log_event(
                AuditEventType.ROTATE, initiated_by, "initiate_key_rotation",
                AuditResult.SUCCESS, None,
                metadata={
                    'rotation_id': rotation_id,
                    'old_key_version': current_version,
                    'new_key_version': new_version,
                    'trigger': trigger.value,
                    'total_credentials': total_credentials,
                    'reason': reason
                }
            )
            
            self.logger.info(f"Initiated key rotation {rotation_id}: v{current_version} -> v{new_version}")
            return rotation_id
            
        except Exception as e:
            self.logger.error(f"Failed to initiate key rotation: {str(e)}")
            raise
    
    async def _rotation_processor(self) -> None:
        """Background task to process rotation queue"""
        while True:
            try:
                # Get rotation request from queue
                rotation_request = await self.rotation_queue.get()
                rotation_id = rotation_request['rotation_id']
                
                rotation_op = self.active_rotations.get(rotation_id)
                if not rotation_op:
                    continue
                
                # Process rotation
                await self._process_key_rotation(rotation_op, rotation_request)
                
            except Exception as e:
                self.logger.error(f"Rotation processor error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _process_key_rotation(self, rotation_op: RotationOperation, 
                                  rotation_request: Dict[str, Any]) -> None:
        """Process key rotation operation"""
        try:
            rotation_op.status = RotationStatus.IN_PROGRESS
            
            # Get credentials to rotate
            target_credentials = rotation_request.get('target_credentials')
            if target_credentials:
                credentials_to_rotate = target_credentials
            else:
                credentials_to_rotate = await self._get_credentials_for_key_version(
                    rotation_op.old_key_version
                )
            
            # Rotate credentials in batches
            batch_size = 50  # Process 50 credentials at a time
            total_batches = (len(credentials_to_rotate) + batch_size - 1) // batch_size
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(credentials_to_rotate))
                batch = credentials_to_rotate[start_idx:end_idx]
                
                try:
                    # Rotate batch of credentials
                    await self._rotate_credential_batch(batch, rotation_op)
                    
                    # Update progress
                    rotation_op.credentials_rotated += len(batch)
                    rotation_op.progress_percent = (rotation_op.credentials_rotated / 
                                                  rotation_op.total_credentials) * 100
                    
                    # Small delay between batches to avoid overwhelming the system
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    error_msg = f"Failed to rotate batch {batch_idx}: {str(e)}"
                    rotation_op.errors.append(error_msg)
                    self.logger.error(error_msg)
            
            # Complete rotation
            if len(rotation_op.errors) == 0:
                await self._complete_key_rotation(rotation_op)
            else:
                await self._handle_rotation_failure(rotation_op)
            
        except Exception as e:
            self.logger.error(f"Key rotation processing failed: {str(e)}")
            rotation_op.status = RotationStatus.FAILED
            rotation_op.errors.append(str(e))
    
    async def _rotate_credential_batch(self, credential_ids: List[str], 
                                     rotation_op: RotationOperation) -> None:
        """Rotate a batch of credentials to new key version"""
        try:
            # This would involve:
            # 1. Retrieving encrypted credentials
            # 2. Decrypting with old key
            # 3. Re-encrypting with new key
            # 4. Updating database with new encrypted data
            
            # For now, simulate the process
            for credential_id in credential_ids:
                try:
                    # Get encrypted credential data
                    encrypted_data_tuple = await self.database_manager.retrieve_encrypted_credential(
                        credential_id
                    )
                    
                    if not encrypted_data_tuple:
                        continue
                    
                    # Simulate re-encryption (would use actual encryption engine)
                    # Update database with new key version
                    # This is a placeholder - actual implementation would decrypt and re-encrypt
                    
                    # Update key version in database
                    # await self.database_manager.update_credential_key_version(
                    #     credential_id, rotation_op.new_key_version
                    # )
                    
                except Exception as e:
                    rotation_op.errors.append(f"Failed to rotate credential {credential_id}: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Failed to rotate credential batch: {str(e)}")
            raise
    
    async def _complete_key_rotation(self, rotation_op: RotationOperation) -> None:
        """Complete key rotation operation"""
        try:
            # Activate new key version
            new_key = self.key_versions[rotation_op.new_key_version]
            new_key.status = KeyStatus.ACTIVE
            new_key.activated_at = datetime.utcnow()
            new_key.credentials_encrypted = rotation_op.credentials_rotated
            
            # Retire old key version
            old_key = self.key_versions[rotation_op.old_key_version]
            old_key.status = KeyStatus.RETIRED
            old_key.retired_at = datetime.utcnow()
            
            # Update current key version
            self.current_key_version = rotation_op.new_key_version
            self.encryption_engine.current_key_version = rotation_op.new_key_version
            
            # Complete rotation operation
            rotation_op.status = RotationStatus.COMPLETED
            rotation_op.completed_at = datetime.utcnow()
            
            # Clear caches that might contain old encrypted data
            if self.performance_optimizer:
                # This would clear relevant caches
                pass
            
            # Log completion
            await self.audit_manager.log_event(
                AuditEventType.ROTATE, rotation_op.initiated_by, "complete_key_rotation",
                AuditResult.SUCCESS, None,
                metadata={
                    'rotation_id': rotation_op.rotation_id,
                    'old_key_version': rotation_op.old_key_version,
                    'new_key_version': rotation_op.new_key_version,
                    'credentials_rotated': rotation_op.credentials_rotated,
                    'duration_minutes': (rotation_op.completed_at - rotation_op.initiated_at).total_seconds() / 60
                }
            )
            
            self.logger.info(f"Completed key rotation {rotation_op.rotation_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to complete key rotation: {str(e)}")
            await self._handle_rotation_failure(rotation_op)
    
    async def _handle_rotation_failure(self, rotation_op: RotationOperation) -> None:
        """Handle key rotation failure"""
        try:
            rotation_op.status = RotationStatus.FAILED
            
            # Log failure
            await self.audit_manager.log_event(
                AuditEventType.ROTATE, rotation_op.initiated_by, "key_rotation_failed",
                AuditResult.FAILURE, None,
                metadata={
                    'rotation_id': rotation_op.rotation_id,
                    'errors': rotation_op.errors,
                    'credentials_rotated': rotation_op.credentials_rotated,
                    'total_credentials': rotation_op.total_credentials
                }
            )
            
            # Optionally initiate rollback
            if rotation_op.credentials_rotated > 0:
                await self._initiate_rollback(rotation_op)
            
            self.logger.error(f"Key rotation {rotation_op.rotation_id} failed")
            
        except Exception as e:
            self.logger.error(f"Failed to handle rotation failure: {str(e)}")
    
    async def _initiate_rollback(self, rotation_op: RotationOperation) -> None:
        """Initiate rollback of partial rotation"""
        try:
            # Create rollback operation
            rollback_id = secrets.token_urlsafe(16)
            
            rollback_op = RotationOperation(
                rotation_id=rollback_id,
                old_key_version=rotation_op.new_key_version,
                new_key_version=rotation_op.old_key_version,
                trigger=RotationTrigger.EMERGENCY,
                initiated_by="system",
                initiated_at=datetime.utcnow(),
                status=RotationStatus.ROLLBACK,
                total_credentials=rotation_op.credentials_rotated,
                rollback_reason=f"Rollback of failed rotation {rotation_op.rotation_id}"
            )
            
            self.active_rotations[rollback_id] = rollback_op
            
            # Add to rotation queue for processing
            await self.rotation_queue.put({
                'rotation_id': rollback_id,
                'target_credentials': None,  # Will be determined during processing
                'reason': rollback_op.rollback_reason
            })
            
            self.logger.info(f"Initiated rollback {rollback_id} for failed rotation {rotation_op.rotation_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to initiate rollback: {str(e)}")
    
    async def emergency_key_rotation(self, initiated_by: str, reason: str) -> str:
        """Emergency key rotation for compromised keys"""
        try:
            self.logger.warning(f"Emergency key rotation initiated by {initiated_by}: {reason}")
            
            # Mark current key as compromised
            current_version = await self._get_active_key_version()
            if current_version and current_version in self.key_versions:
                self.key_versions[current_version].status = KeyStatus.COMPROMISED
            
            # Initiate immediate rotation
            rotation_id = await self.initiate_key_rotation(
                RotationTrigger.EMERGENCY, initiated_by, reason
            )
            
            # Prioritize this rotation (move to front of queue)
            # This would require queue priority implementation
            
            return rotation_id
            
        except Exception as e:
            self.logger.error(f"Emergency key rotation failed: {str(e)}")
            raise
    
    async def schedule_key_rotation(self, schedule_time: datetime, trigger: RotationTrigger,
                                  initiated_by: str, reason: str = "") -> str:
        """Schedule key rotation for future execution"""
        try:
            # This would integrate with a job scheduler
            # For now, store the schedule and check in the scheduler task
            
            schedule_id = secrets.token_urlsafe(16)
            schedule_data = {
                'schedule_id': schedule_id,
                'schedule_time': schedule_time.isoformat(),
                'trigger': trigger.value,
                'initiated_by': initiated_by,
                'reason': reason,
                'status': 'scheduled'
            }
            
            # Store schedule (would use persistent storage)
            if self.redis:
                self.redis.setex(
                    f"vault:rotation_schedule:{schedule_id}",
                    int((schedule_time - datetime.utcnow()).total_seconds()),
                    json.dumps(schedule_data)
                )
            
            self.logger.info(f"Scheduled key rotation {schedule_id} for {schedule_time}")
            return schedule_id
            
        except Exception as e:
            self.logger.error(f"Failed to schedule key rotation: {str(e)}")
            raise
    
    async def _rotation_scheduler(self) -> None:
        """Background task for scheduled rotations"""
        while True:
            try:
                current_time = datetime.utcnow()
                
                # Check for scheduled rotations
                if self.redis:
                    # Get scheduled rotations
                    schedule_keys = self.redis.keys("vault:rotation_schedule:*")
                    
                    for key in schedule_keys:
                        try:
                            schedule_data = json.loads(self.redis.get(key))
                            schedule_time = datetime.fromisoformat(schedule_data['schedule_time'])
                            
                            if current_time >= schedule_time:
                                # Execute scheduled rotation
                                await self.initiate_key_rotation(
                                    RotationTrigger(schedule_data['trigger']),
                                    schedule_data['initiated_by'],
                                    schedule_data['reason']
                                )
                                
                                # Remove from schedule
                                self.redis.delete(key)
                                
                        except Exception as e:
                            self.logger.error(f"Failed to process scheduled rotation: {str(e)}")
                
                # Check rotation policies
                await self._check_rotation_policies()
                
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                self.logger.error(f"Rotation scheduler error: {str(e)}")
                await asyncio.sleep(300)
    
    async def _check_rotation_policies(self) -> None:
        """Check if any rotation policies require action"""
        try:
            for policy_id, policy in self.rotation_policies.items():
                if not policy.automatic_rotation:
                    continue
                
                # Check if rotation is needed based on policy
                needs_rotation = await self._evaluate_rotation_policy(policy)
                
                if needs_rotation:
                    self.logger.info(f"Policy {policy.name} triggered automatic rotation")
                    
                    await self.initiate_key_rotation(
                        RotationTrigger.POLICY,
                        "system",
                        f"Automatic rotation triggered by policy: {policy.name}"
                    )
                    
        except Exception as e:
            self.logger.error(f"Failed to check rotation policies: {str(e)}")
    
    async def _evaluate_rotation_policy(self, policy: RotationPolicy) -> bool:
        """Evaluate if rotation policy conditions are met"""
        try:
            current_version = await self._get_active_key_version()
            if not current_version or current_version not in self.key_versions:
                return False
            
            current_key = self.key_versions[current_version]
            
            # Check key age
            if current_key.activated_at:
                key_age_days = (datetime.utcnow() - current_key.activated_at).days
                if key_age_days >= policy.rotation_interval_days:
                    return True
            
            # Check maximum key age
            key_creation_age = (datetime.utcnow() - current_key.created_at).days
            if key_creation_age >= policy.max_key_age_days:
                return True
            
            # Check credentials per key limit
            if current_key.credentials_encrypted >= policy.max_credentials_per_key:
                return True
            
            # Check custom conditions
            for condition_name, condition_value in policy.conditions.items():
                if await self._evaluate_custom_condition(condition_name, condition_value):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate rotation policy: {str(e)}")
            return False
    
    async def _evaluate_custom_condition(self, condition_name: str, condition_value: Any) -> bool:
        """Evaluate custom rotation condition"""
        try:
            # Implement custom condition logic
            # This could check various metrics, security events, etc.
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate custom condition {condition_name}: {str(e)}")
            return False
    
    async def _key_lifecycle_monitor(self) -> None:
        """Monitor key lifecycle and send notifications"""
        while True:
            try:
                current_time = datetime.utcnow()
                
                for version, key in self.key_versions.items():
                    if key.status != KeyStatus.ACTIVE:
                        continue
                    
                    # Check if key is approaching rotation time
                    if key.activated_at:
                        days_since_activation = (current_time - key.activated_at).days
                        
                        # Send notification if approaching rotation
                        for policy in self.rotation_policies.values():
                            if policy.automatic_rotation and policy.notification_days_before > 0:
                                days_until_rotation = policy.rotation_interval_days - days_since_activation
                                
                                if days_until_rotation <= policy.notification_days_before and days_until_rotation > 0:
                                    await self._send_rotation_notification(key, policy, days_until_rotation)
                
                await asyncio.sleep(86400)  # Check daily
                
            except Exception as e:
                self.logger.error(f"Key lifecycle monitor error: {str(e)}")
                await asyncio.sleep(3600)
    
    async def _send_rotation_notification(self, key: KeyVersion, policy: RotationPolicy, 
                                        days_until: int) -> None:
        """Send key rotation notification"""
        try:
            notification_data = {
                'type': 'key_rotation_notification',
                'key_version': key.version,
                'policy_name': policy.name,
                'days_until_rotation': days_until,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # This would integrate with notification system
            self.logger.info(f"Key rotation notification: Version {key.version} needs rotation in {days_until} days")
            
        except Exception as e:
            self.logger.error(f"Failed to send rotation notification: {str(e)}")
    
    async def create_rotation_policy(self, policy_data: Dict[str, Any], created_by: str) -> str:
        """Create new rotation policy"""
        try:
            policy_id = secrets.token_urlsafe(16)
            
            policy = RotationPolicy(
                policy_id=policy_id,
                name=policy_data['name'],
                description=policy_data.get('description', ''),
                rotation_interval_days=policy_data.get('rotation_interval_days', self.default_rotation_days),
                max_key_age_days=policy_data.get('max_key_age_days', self.max_key_age_days),
                max_credentials_per_key=policy_data.get('max_credentials_per_key', self.max_credentials_per_key),
                automatic_rotation=policy_data.get('automatic_rotation', self.automatic_rotation),
                require_approval=policy_data.get('require_approval', self.require_approval),
                notification_days_before=policy_data.get('notification_days_before', self.notification_days),
                emergency_rotation_enabled=policy_data.get('emergency_rotation_enabled', True),
                compliance_frameworks=policy_data.get('compliance_frameworks', []),
                conditions=policy_data.get('conditions', {})
            )
            
            self.rotation_policies[policy_id] = policy
            
            # Store policy (would use persistent storage)
            await self._save_rotation_policy(policy)
            
            # Log audit event
            await self.audit_manager.log_event(
                AuditEventType.CREATE, created_by, "create_rotation_policy",
                AuditResult.SUCCESS, None,
                metadata={
                    'policy_id': policy_id,
                    'policy_name': policy.name,
                    'rotation_interval_days': policy.rotation_interval_days
                }
            )
            
            self.logger.info(f"Created rotation policy {policy.name}")
            return policy_id
            
        except Exception as e:
            self.logger.error(f"Failed to create rotation policy: {str(e)}")
            raise
    
    async def get_key_versions(self) -> List[KeyVersion]:
        """Get all key versions"""
        return list(self.key_versions.values())
    
    async def get_rotation_status(self, rotation_id: str) -> Optional[RotationOperation]:
        """Get rotation operation status"""
        return self.active_rotations.get(rotation_id)
    
    async def get_rotation_policies(self) -> List[RotationPolicy]:
        """Get all rotation policies"""
        return list(self.rotation_policies.values())
    
    async def get_key_rotation_statistics(self) -> Dict[str, Any]:
        """Get key rotation statistics"""
        try:
            active_rotations = len([r for r in self.active_rotations.values() 
                                 if r.status == RotationStatus.IN_PROGRESS])
            
            completed_rotations = len([r for r in self.active_rotations.values() 
                                    if r.status == RotationStatus.COMPLETED])
            
            failed_rotations = len([r for r in self.active_rotations.values() 
                                 if r.status == RotationStatus.FAILED])
            
            key_status_counts = {}
            for key in self.key_versions.values():
                key_status_counts[key.status.value] = key_status_counts.get(key.status.value, 0) + 1
            
            return {
                'total_key_versions': len(self.key_versions),
                'current_key_version': self.current_key_version,
                'active_rotations': active_rotations,
                'completed_rotations': completed_rotations,
                'failed_rotations': failed_rotations,
                'key_status_counts': key_status_counts,
                'rotation_policies': len(self.rotation_policies),
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get rotation statistics: {str(e)}")
            return {'error': str(e)}
    
    async def _get_active_key_version(self) -> Optional[int]:
        """Get currently active key version"""
        for version, key in self.key_versions.items():
            if key.status == KeyStatus.ACTIVE:
                return version
        return None
    
    async def _count_credentials_for_key_version(self, key_version: int) -> int:
        """Count credentials encrypted with specific key version"""
        try:
            # This would query the database
            # For now, return placeholder
            return 0
            
        except Exception as e:
            self.logger.error(f"Failed to count credentials for key version: {str(e)}")
            return 0
    
    async def _get_credentials_for_key_version(self, key_version: int) -> List[str]:
        """Get list of credential IDs encrypted with specific key version"""
        try:
            # This would query the database
            # For now, return empty list
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get credentials for key version: {str(e)}")
            return []
    
    async def _load_key_versions(self) -> None:
        """Load existing key versions from database"""
        try:
            # This would query the database for existing key versions
            # For now, create initial key version if none exist
            if not self.key_versions:
                initial_key = KeyVersion(
                    version=1,
                    key_hash=hashlib.sha256(b"initial_key").hexdigest(),
                    algorithm="AES-256-GCM",
                    created_at=datetime.utcnow(),
                    activated_at=datetime.utcnow(),
                    retired_at=None,
                    status=KeyStatus.ACTIVE,
                    created_by="system"
                )
                self.key_versions[1] = initial_key
                self.current_key_version = 1
                
        except Exception as e:
            self.logger.error(f"Failed to load key versions: {str(e)}")
    
    async def _load_rotation_policies(self) -> None:
        """Load rotation policies from storage"""
        try:
            # This would load policies from persistent storage
            pass
            
        except Exception as e:
            self.logger.error(f"Failed to load rotation policies: {str(e)}")
    
    async def _create_default_rotation_policy(self) -> None:
        """Create default rotation policy"""
        try:
            default_policy_data = {
                'name': 'Default Rotation Policy',
                'description': 'Default key rotation policy for the vault',
                'rotation_interval_days': self.default_rotation_days,
                'max_key_age_days': self.max_key_age_days,
                'max_credentials_per_key': self.max_credentials_per_key,
                'automatic_rotation': self.automatic_rotation,
                'require_approval': self.require_approval,
                'notification_days_before': self.notification_days,
                'emergency_rotation_enabled': True
            }
            
            await self.create_rotation_policy(default_policy_data, "system")
            
        except Exception as e:
            self.logger.error(f"Failed to create default rotation policy: {str(e)}")
    
    async def _save_rotation_policy(self, policy: RotationPolicy) -> None:
        """Save rotation policy to persistent storage"""
        try:
            # This would save to database or file system
            pass
            
        except Exception as e:
            self.logger.error(f"Failed to save rotation policy: {str(e)}")