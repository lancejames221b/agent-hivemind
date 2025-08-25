#!/usr/bin/env python3
"""
hAIveMind Rules Sync Service - Network-wide Rules Distribution and Governance
Extends the existing sync service to include comprehensive rules synchronization
across the hAIveMind network with conflict resolution and governance features.

Author: Lance James, Unit 221B Inc
"""

import asyncio
import json
import logging
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import redis
import httpx
from fastapi import HTTPException

from .rules_engine import RulesEngine, Rule, RuleType, RuleScope, RulePriority, RuleStatus
from .rules_database import RulesDatabase, RuleChangeType
from .rules_haivemind_integration import RulesHAIveMindIntegration
from .rule_management_service import RuleManagementService

logger = logging.getLogger(__name__)

class RuleSyncOperation(Enum):
    """Types of rule sync operations"""
    CREATE = "create"
    UPDATE = "update" 
    DELETE = "delete"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    BULK_SYNC = "bulk_sync"
    EMERGENCY_UPDATE = "emergency_update"

class RuleSyncPriority(Enum):
    """Priority levels for rule sync operations"""
    EMERGENCY = 1000    # Critical security/compliance updates
    HIGH = 750         # Important governance changes
    NORMAL = 500       # Standard rule updates
    LOW = 250         # Minor optimizations
    BACKGROUND = 100   # Bulk sync operations

class ConflictResolutionStrategy(Enum):
    """Strategies for resolving rule conflicts during sync"""
    TIMESTAMP = "timestamp"           # Latest timestamp wins
    PRIORITY = "priority"            # Higher priority rule wins
    SOURCE_AUTHORITY = "source_authority"  # Designated authority wins
    MANUAL_REVIEW = "manual_review"  # Flag for manual resolution
    MERGE = "merge"                  # Attempt to merge changes

@dataclass
class RuleSyncMessage:
    """Message format for rule synchronization"""
    sync_id: str
    operation: RuleSyncOperation
    priority: RuleSyncPriority
    source_machine: str
    target_machines: Optional[List[str]]
    rule_data: Dict[str, Any]
    timestamp: datetime
    checksum: str
    metadata: Dict[str, Any]
    requires_acknowledgment: bool = False
    expires_at: Optional[datetime] = None

@dataclass
class RuleSyncConflict:
    """Represents a rule synchronization conflict"""
    conflict_id: str
    rule_id: str
    local_rule: Dict[str, Any]
    remote_rule: Dict[str, Any]
    conflict_type: str
    resolution_strategy: ConflictResolutionStrategy
    created_at: datetime
    resolved: bool = False
    resolution_data: Optional[Dict[str, Any]] = None

@dataclass
class RuleSyncStatus:
    """Status of rule sync operation"""
    sync_id: str
    machine_id: str
    status: str  # pending, in_progress, completed, failed, conflict
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    rules_processed: int = 0
    conflicts_detected: int = 0

class RulesSyncService:
    """Enhanced sync service for rules distribution across hAIveMind network"""
    
    def __init__(self, config: Dict[str, Any], memory_storage=None):
        self.config = config
        self.memory_storage = memory_storage
        self.machine_id = self._get_machine_id()
        
        # Initialize components
        self.redis_client = self._init_redis()
        self.rules_db = RulesDatabase(
            config.get('rules', {}).get('database_path', 'data/rules.db'),
            getattr(memory_storage, 'chroma_client', None),
            self.redis_client
        )
        
        self.rule_service = RuleManagementService(
            config.get('rules', {}).get('database_path', 'data/rules.db'),
            getattr(memory_storage, 'chroma_client', None),
            self.redis_client
        )
        
        self.haivemind_integration = RulesHAIveMindIntegration(
            self.rule_service,
            memory_storage,
            self.redis_client
        )
        
        # Sync state management
        self.active_syncs: Dict[str, RuleSyncStatus] = {}
        self.pending_conflicts: Dict[str, RuleSyncConflict] = {}
        self.sync_history: List[RuleSyncStatus] = []
        
        # Network discovery
        self.known_machines: Set[str] = set()
        self.machine_authorities: Dict[str, List[str]] = {}  # machine -> rule types it's authoritative for
        
        # Performance tracking
        self.sync_metrics = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'conflicts_resolved': 0,
            'avg_sync_time': 0.0
        }
        
        # Start background tasks
        self._start_background_tasks()
    
    def _get_machine_id(self) -> str:
        """Get unique machine identifier"""
        try:
            import subprocess
            result = subprocess.run(['tailscale', 'status', '--json'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                status = json.loads(result.stdout)
                return status.get('Self', {}).get('HostName', 'unknown')
        except Exception:
            pass
        
        import socket
        return socket.gethostname()
    
    def _init_redis(self) -> Optional[redis.Redis]:
        """Initialize Redis connection for sync coordination"""
        try:
            redis_config = self.config['storage']['redis']
            client = redis.Redis(
                host=redis_config['host'],
                port=redis_config['port'],
                db=redis_config['db'],
                password=redis_config.get('password'),
                decode_responses=True
            )
            client.ping()
            logger.info("Redis connection established for rules sync")
            return client
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for rules sync: {e}")
            return None
    
    def _start_background_tasks(self):
        """Start background sync tasks"""
        if self.redis_client:
            asyncio.create_task(self._listen_for_sync_messages())
            asyncio.create_task(self._periodic_sync_health_check())
            asyncio.create_task(self._cleanup_expired_syncs())
    
    async def sync_rule_to_network(self, rule_id: str, operation: RuleSyncOperation, 
                                  priority: RuleSyncPriority = RuleSyncPriority.NORMAL,
                                  target_machines: Optional[List[str]] = None,
                                  metadata: Optional[Dict[str, Any]] = None) -> str:
        """Sync a specific rule to the network"""
        sync_id = str(hashlib.md5(f"{rule_id}:{operation.value}:{time.time()}".encode()).hexdigest())
        
        try:
            # Get rule data
            rule = self.rules_db.get_rule(rule_id)
            if not rule and operation not in [RuleSyncOperation.DELETE]:
                raise ValueError(f"Rule {rule_id} not found")
            
            # Prepare rule data for sync
            if rule:
                rule_data = self.rule_service._rule_to_export_dict(rule)
            else:
                rule_data = {"id": rule_id, "operation": operation.value}
            
            # Create sync message
            sync_message = RuleSyncMessage(
                sync_id=sync_id,
                operation=operation,
                priority=priority,
                source_machine=self.machine_id,
                target_machines=target_machines,
                rule_data=rule_data,
                timestamp=datetime.now(),
                checksum=self._calculate_rule_checksum(rule_data),
                metadata=metadata or {},
                requires_acknowledgment=priority.value >= RuleSyncPriority.HIGH.value,
                expires_at=datetime.now() + timedelta(hours=24) if priority == RuleSyncPriority.BACKGROUND else None
            )
            
            # Track sync status
            self.active_syncs[sync_id] = RuleSyncStatus(
                sync_id=sync_id,
                machine_id=self.machine_id,
                status="pending",
                started_at=datetime.now(),
                rules_processed=1
            )
            
            # Broadcast sync message
            await self._broadcast_sync_message(sync_message)
            
            # Store sync operation in hAIveMind memory
            if self.memory_storage:
                await self._store_sync_memory(sync_message, "initiated")
            
            logger.info(f"Rule sync initiated: {sync_id} for rule {rule_id}")
            return sync_id
            
        except Exception as e:
            logger.error(f"Failed to sync rule {rule_id}: {e}")
            if sync_id in self.active_syncs:
                self.active_syncs[sync_id].status = "failed"
                self.active_syncs[sync_id].error_message = str(e)
            raise
    
    async def bulk_sync_rules(self, rule_ids: Optional[List[str]] = None,
                             target_machines: Optional[List[str]] = None,
                             priority: RuleSyncPriority = RuleSyncPriority.BACKGROUND) -> str:
        """Perform bulk synchronization of rules"""
        sync_id = str(hashlib.md5(f"bulk_sync:{time.time()}".encode()).hexdigest())
        
        try:
            # Get rules to sync
            if rule_ids:
                rules_data = []
                for rule_id in rule_ids:
                    rule = self.rules_db.get_rule(rule_id)
                    if rule:
                        rules_data.append(self.rule_service._rule_to_export_dict(rule))
            else:
                # Export all active rules
                export_data = self.rules_db.export_rules("json")
                rules_data = json.loads(export_data).get('rules', [])
            
            # Create bulk sync message
            sync_message = RuleSyncMessage(
                sync_id=sync_id,
                operation=RuleSyncOperation.BULK_SYNC,
                priority=priority,
                source_machine=self.machine_id,
                target_machines=target_machines,
                rule_data={"rules": rules_data, "count": len(rules_data)},
                timestamp=datetime.now(),
                checksum=self._calculate_bulk_checksum(rules_data),
                metadata={"bulk_sync": True, "rule_count": len(rules_data)},
                requires_acknowledgment=len(rules_data) > 50,  # Require ack for large syncs
                expires_at=datetime.now() + timedelta(hours=48)  # Longer expiry for bulk
            )
            
            # Track sync status
            self.active_syncs[sync_id] = RuleSyncStatus(
                sync_id=sync_id,
                machine_id=self.machine_id,
                status="pending",
                started_at=datetime.now(),
                rules_processed=len(rules_data)
            )
            
            # Broadcast sync message
            await self._broadcast_sync_message(sync_message)
            
            # Store sync operation in hAIveMind memory
            if self.memory_storage:
                await self._store_sync_memory(sync_message, "bulk_initiated")
            
            logger.info(f"Bulk rule sync initiated: {sync_id} for {len(rules_data)} rules")
            return sync_id
            
        except Exception as e:
            logger.error(f"Failed to perform bulk sync: {e}")
            if sync_id in self.active_syncs:
                self.active_syncs[sync_id].status = "failed"
                self.active_syncs[sync_id].error_message = str(e)
            raise
    
    async def emergency_rule_update(self, rule_id: str, rule_data: Dict[str, Any],
                                   reason: str, target_machines: Optional[List[str]] = None) -> str:
        """Emergency rule update with immediate network distribution"""
        sync_id = str(hashlib.md5(f"emergency:{rule_id}:{time.time()}".encode()).hexdigest())
        
        try:
            # Create emergency sync message
            sync_message = RuleSyncMessage(
                sync_id=sync_id,
                operation=RuleSyncOperation.EMERGENCY_UPDATE,
                priority=RuleSyncPriority.EMERGENCY,
                source_machine=self.machine_id,
                target_machines=target_machines,
                rule_data=rule_data,
                timestamp=datetime.now(),
                checksum=self._calculate_rule_checksum(rule_data),
                metadata={"emergency": True, "reason": reason},
                requires_acknowledgment=True,
                expires_at=datetime.now() + timedelta(minutes=30)  # Short expiry for emergency
            )
            
            # Track sync status
            self.active_syncs[sync_id] = RuleSyncStatus(
                sync_id=sync_id,
                machine_id=self.machine_id,
                status="pending",
                started_at=datetime.now(),
                rules_processed=1
            )
            
            # Broadcast with high priority
            await self._broadcast_sync_message(sync_message, immediate=True)
            
            # Store emergency sync in memory with high importance
            if self.memory_storage:
                await self._store_sync_memory(sync_message, "emergency_initiated", importance="critical")
            
            logger.warning(f"Emergency rule update initiated: {sync_id} for rule {rule_id} - {reason}")
            return sync_id
            
        except Exception as e:
            logger.error(f"Failed to perform emergency rule update: {e}")
            if sync_id in self.active_syncs:
                self.active_syncs[sync_id].status = "failed"
                self.active_syncs[sync_id].error_message = str(e)
            raise
    
    async def _broadcast_sync_message(self, message: RuleSyncMessage, immediate: bool = False):
        """Broadcast sync message to the network"""
        if not self.redis_client:
            raise RuntimeError("Redis client not available for sync broadcasting")
        
        try:
            # Serialize message
            message_data = {
                "sync_id": message.sync_id,
                "operation": message.operation.value,
                "priority": message.priority.value,
                "source_machine": message.source_machine,
                "target_machines": message.target_machines,
                "rule_data": message.rule_data,
                "timestamp": message.timestamp.isoformat(),
                "checksum": message.checksum,
                "metadata": message.metadata,
                "requires_acknowledgment": message.requires_acknowledgment,
                "expires_at": message.expires_at.isoformat() if message.expires_at else None
            }
            
            # Choose channel based on priority
            if message.priority == RuleSyncPriority.EMERGENCY:
                channel = "haivemind:rules:emergency"
            elif message.priority.value >= RuleSyncPriority.HIGH.value:
                channel = "haivemind:rules:priority"
            else:
                channel = "haivemind:rules:sync"
            
            # Broadcast message
            self.redis_client.publish(channel, json.dumps(message_data))
            
            # For emergency updates, also send direct HTTP requests
            if immediate and message.priority == RuleSyncPriority.EMERGENCY:
                await self._send_direct_emergency_sync(message)
            
            logger.info(f"Sync message broadcasted on {channel}: {message.sync_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast sync message: {e}")
            raise
    
    async def _send_direct_emergency_sync(self, message: RuleSyncMessage):
        """Send emergency sync directly to known machines via HTTP"""
        target_machines = message.target_machines or list(self.known_machines)
        
        for machine in target_machines:
            if machine == self.machine_id:
                continue
                
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    url = f"http://{machine}:8899/api/rules/emergency-sync"
                    response = await client.post(url, json={
                        "sync_message": asdict(message),
                        "source": self.machine_id
                    })
                    
                    if response.status_code == 200:
                        logger.info(f"Emergency sync sent directly to {machine}")
                    else:
                        logger.warning(f"Failed to send emergency sync to {machine}: {response.status_code}")
                        
            except Exception as e:
                logger.error(f"Failed to send direct emergency sync to {machine}: {e}")
    
    async def _listen_for_sync_messages(self):
        """Listen for incoming sync messages from the network"""
        if not self.redis_client:
            return
        
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("haivemind:rules:sync", "haivemind:rules:priority", "haivemind:rules:emergency")
        
        logger.info("Started listening for rule sync messages")
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        await self._process_incoming_sync_message(message)
                    except Exception as e:
                        logger.error(f"Error processing sync message: {e}")
        except Exception as e:
            logger.error(f"Error in sync message listener: {e}")
        finally:
            pubsub.close()
    
    async def _process_incoming_sync_message(self, redis_message):
        """Process incoming sync message"""
        try:
            message_data = json.loads(redis_message['data'])
            
            # Skip messages from self
            if message_data.get('source_machine') == self.machine_id:
                return
            
            # Check if message is targeted to this machine
            target_machines = message_data.get('target_machines')
            if target_machines and self.machine_id not in target_machines:
                return
            
            # Check if message has expired
            expires_at = message_data.get('expires_at')
            if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
                logger.warning(f"Received expired sync message: {message_data.get('sync_id')}")
                return
            
            # Parse sync message
            sync_message = RuleSyncMessage(
                sync_id=message_data['sync_id'],
                operation=RuleSyncOperation(message_data['operation']),
                priority=RuleSyncPriority(message_data['priority']),
                source_machine=message_data['source_machine'],
                target_machines=message_data.get('target_machines'),
                rule_data=message_data['rule_data'],
                timestamp=datetime.fromisoformat(message_data['timestamp']),
                checksum=message_data['checksum'],
                metadata=message_data.get('metadata', {}),
                requires_acknowledgment=message_data.get('requires_acknowledgment', False),
                expires_at=datetime.fromisoformat(expires_at) if expires_at else None
            )
            
            # Process the sync operation
            await self._apply_sync_operation(sync_message)
            
        except Exception as e:
            logger.error(f"Failed to process incoming sync message: {e}")
    
    async def _apply_sync_operation(self, sync_message: RuleSyncMessage):
        """Apply sync operation to local rules database"""
        try:
            operation = sync_message.operation
            rule_data = sync_message.rule_data
            
            if operation == RuleSyncOperation.BULK_SYNC:
                await self._apply_bulk_sync(sync_message)
            elif operation == RuleSyncOperation.CREATE:
                await self._apply_rule_create(sync_message)
            elif operation == RuleSyncOperation.UPDATE:
                await self._apply_rule_update(sync_message)
            elif operation == RuleSyncOperation.DELETE:
                await self._apply_rule_delete(sync_message)
            elif operation == RuleSyncOperation.ACTIVATE:
                await self._apply_rule_activate(sync_message)
            elif operation == RuleSyncOperation.DEACTIVATE:
                await self._apply_rule_deactivate(sync_message)
            elif operation == RuleSyncOperation.EMERGENCY_UPDATE:
                await self._apply_emergency_update(sync_message)
            
            # Send acknowledgment if required
            if sync_message.requires_acknowledgment:
                await self._send_sync_acknowledgment(sync_message, "success")
            
            # Store sync operation in memory
            if self.memory_storage:
                await self._store_sync_memory(sync_message, "applied")
            
            logger.info(f"Applied sync operation {operation.value}: {sync_message.sync_id}")
            
        except Exception as e:
            logger.error(f"Failed to apply sync operation: {e}")
            
            # Send failure acknowledgment if required
            if sync_message.requires_acknowledgment:
                await self._send_sync_acknowledgment(sync_message, "failed", str(e))
    
    async def _apply_bulk_sync(self, sync_message: RuleSyncMessage):
        """Apply bulk sync operation"""
        rules_data = sync_message.rule_data.get('rules', [])
        conflicts = []
        applied_count = 0
        
        for rule_data in rules_data:
            try:
                rule_id = rule_data.get('id')
                existing_rule = self.rules_db.get_rule(rule_id) if rule_id else None
                
                if existing_rule:
                    # Check for conflicts
                    conflict = await self._detect_rule_conflict(existing_rule, rule_data, sync_message)
                    if conflict:
                        conflicts.append(conflict)
                        continue
                    
                    # Update existing rule
                    updated_rule = self.rule_service._dict_to_rule(rule_data)
                    self.rules_db.update_rule(updated_rule, f"Bulk sync from {sync_message.source_machine}")
                else:
                    # Create new rule
                    new_rule = self.rule_service._dict_to_rule(rule_data)
                    self.rules_db.create_rule(new_rule, f"Bulk sync from {sync_message.source_machine}")
                
                applied_count += 1
                
            except Exception as e:
                logger.error(f"Failed to apply rule in bulk sync: {e}")
        
        # Handle conflicts
        if conflicts:
            await self._handle_sync_conflicts(conflicts)
        
        logger.info(f"Bulk sync applied: {applied_count} rules, {len(conflicts)} conflicts")
    
    async def _apply_rule_create(self, sync_message: RuleSyncMessage):
        """Apply rule create operation"""
        rule_data = sync_message.rule_data
        rule_id = rule_data.get('id')
        
        # Check if rule already exists
        existing_rule = self.rules_db.get_rule(rule_id) if rule_id else None
        if existing_rule:
            # Detect conflict
            conflict = await self._detect_rule_conflict(existing_rule, rule_data, sync_message)
            if conflict:
                await self._handle_sync_conflicts([conflict])
                return
        
        # Create new rule
        new_rule = self.rule_service._dict_to_rule(rule_data)
        self.rules_db.create_rule(new_rule, f"Sync create from {sync_message.source_machine}")
    
    async def _apply_rule_update(self, sync_message: RuleSyncMessage):
        """Apply rule update operation"""
        rule_data = sync_message.rule_data
        rule_id = rule_data.get('id')
        
        existing_rule = self.rules_db.get_rule(rule_id) if rule_id else None
        if not existing_rule:
            # Rule doesn't exist locally, treat as create
            await self._apply_rule_create(sync_message)
            return
        
        # Check for conflicts
        conflict = await self._detect_rule_conflict(existing_rule, rule_data, sync_message)
        if conflict:
            await self._handle_sync_conflicts([conflict])
            return
        
        # Update rule
        updated_rule = self.rule_service._dict_to_rule(rule_data)
        self.rules_db.update_rule(updated_rule, f"Sync update from {sync_message.source_machine}")
    
    async def _apply_rule_delete(self, sync_message: RuleSyncMessage):
        """Apply rule delete operation"""
        rule_id = sync_message.rule_data.get('id')
        
        existing_rule = self.rules_db.get_rule(rule_id) if rule_id else None
        if existing_rule:
            # Deactivate instead of delete to preserve history
            self.rules_db.deactivate_rule(rule_id, f"sync_delete_{sync_message.source_machine}")
    
    async def _apply_rule_activate(self, sync_message: RuleSyncMessage):
        """Apply rule activate operation"""
        rule_id = sync_message.rule_data.get('id')
        effective_from = sync_message.metadata.get('effective_from')
        
        if effective_from:
            effective_from = datetime.fromisoformat(effective_from)
        
        self.rules_db.activate_rule(rule_id, f"sync_activate_{sync_message.source_machine}", effective_from)
    
    async def _apply_rule_deactivate(self, sync_message: RuleSyncMessage):
        """Apply rule deactivate operation"""
        rule_id = sync_message.rule_data.get('id')
        effective_until = sync_message.metadata.get('effective_until')
        
        if effective_until:
            effective_until = datetime.fromisoformat(effective_until)
        
        self.rules_db.deactivate_rule(rule_id, f"sync_deactivate_{sync_message.source_machine}", effective_until)
    
    async def _apply_emergency_update(self, sync_message: RuleSyncMessage):
        """Apply emergency rule update with priority handling"""
        rule_data = sync_message.rule_data
        rule_id = rule_data.get('id')
        
        # Emergency updates override conflicts
        if rule_id:
            existing_rule = self.rules_db.get_rule(rule_id)
            if existing_rule:
                updated_rule = self.rule_service._dict_to_rule(rule_data)
                self.rules_db.update_rule(updated_rule, f"EMERGENCY sync from {sync_message.source_machine}: {sync_message.metadata.get('reason', 'No reason provided')}")
            else:
                new_rule = self.rule_service._dict_to_rule(rule_data)
                self.rules_db.create_rule(new_rule, f"EMERGENCY sync from {sync_message.source_machine}")
        
        # Log emergency update
        logger.warning(f"Applied emergency rule update: {rule_id} from {sync_message.source_machine}")
    
    async def _detect_rule_conflict(self, existing_rule: Rule, incoming_rule_data: Dict[str, Any], 
                                   sync_message: RuleSyncMessage) -> Optional[RuleSyncConflict]:
        """Detect conflicts between existing and incoming rules"""
        try:
            # Convert existing rule to dict for comparison
            existing_dict = self.rule_service._rule_to_export_dict(existing_rule)
            
            # Check for version conflicts
            existing_version = existing_dict.get('version', 1)
            incoming_version = incoming_rule_data.get('version', 1)
            
            # Check for timestamp conflicts
            existing_updated = datetime.fromisoformat(existing_dict.get('updated_at', '1970-01-01T00:00:00'))
            incoming_updated = datetime.fromisoformat(incoming_rule_data.get('updated_at', '1970-01-01T00:00:00'))
            
            # Check for content conflicts
            content_changed = (
                existing_dict.get('name') != incoming_rule_data.get('name') or
                existing_dict.get('description') != incoming_rule_data.get('description') or
                existing_dict.get('conditions') != incoming_rule_data.get('conditions') or
                existing_dict.get('actions') != incoming_rule_data.get('actions')
            )
            
            # Determine conflict type and resolution strategy
            conflict_type = None
            resolution_strategy = ConflictResolutionStrategy.TIMESTAMP
            
            if incoming_version < existing_version:
                conflict_type = "version_downgrade"
                resolution_strategy = ConflictResolutionStrategy.MANUAL_REVIEW
            elif incoming_version == existing_version and content_changed:
                conflict_type = "concurrent_modification"
                resolution_strategy = ConflictResolutionStrategy.TIMESTAMP
            elif incoming_updated < existing_updated and content_changed:
                conflict_type = "stale_update"
                resolution_strategy = ConflictResolutionStrategy.TIMESTAMP
            
            if conflict_type:
                conflict_id = str(hashlib.md5(f"{existing_rule.id}:{sync_message.sync_id}".encode()).hexdigest())
                return RuleSyncConflict(
                    conflict_id=conflict_id,
                    rule_id=existing_rule.id,
                    local_rule=existing_dict,
                    remote_rule=incoming_rule_data,
                    conflict_type=conflict_type,
                    resolution_strategy=resolution_strategy,
                    created_at=datetime.now()
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting rule conflict: {e}")
            return None
    
    async def _handle_sync_conflicts(self, conflicts: List[RuleSyncConflict]):
        """Handle rule synchronization conflicts"""
        for conflict in conflicts:
            try:
                self.pending_conflicts[conflict.conflict_id] = conflict
                
                # Apply resolution strategy
                if conflict.resolution_strategy == ConflictResolutionStrategy.TIMESTAMP:
                    await self._resolve_conflict_by_timestamp(conflict)
                elif conflict.resolution_strategy == ConflictResolutionStrategy.PRIORITY:
                    await self._resolve_conflict_by_priority(conflict)
                elif conflict.resolution_strategy == ConflictResolutionStrategy.MANUAL_REVIEW:
                    await self._flag_for_manual_review(conflict)
                
                # Store conflict in hAIveMind memory
                if self.memory_storage:
                    await self._store_conflict_memory(conflict)
                
            except Exception as e:
                logger.error(f"Failed to handle sync conflict {conflict.conflict_id}: {e}")
    
    async def _resolve_conflict_by_timestamp(self, conflict: RuleSyncConflict):
        """Resolve conflict using timestamp comparison"""
        local_updated = datetime.fromisoformat(conflict.local_rule.get('updated_at', '1970-01-01T00:00:00'))
        remote_updated = datetime.fromisoformat(conflict.remote_rule.get('updated_at', '1970-01-01T00:00:00'))
        
        if remote_updated > local_updated:
            # Remote rule is newer, apply it
            updated_rule = self.rule_service._dict_to_rule(conflict.remote_rule)
            self.rules_db.update_rule(updated_rule, f"Conflict resolution: timestamp (remote newer)")
            conflict.resolved = True
            conflict.resolution_data = {"winner": "remote", "reason": "newer_timestamp"}
        else:
            # Local rule is newer or same, keep it
            conflict.resolved = True
            conflict.resolution_data = {"winner": "local", "reason": "newer_or_same_timestamp"}
        
        logger.info(f"Resolved conflict {conflict.conflict_id} by timestamp")
    
    async def _resolve_conflict_by_priority(self, conflict: RuleSyncConflict):
        """Resolve conflict using rule priority"""
        local_priority = conflict.local_rule.get('priority', 500)
        remote_priority = conflict.remote_rule.get('priority', 500)
        
        if remote_priority > local_priority:
            # Remote rule has higher priority
            updated_rule = self.rule_service._dict_to_rule(conflict.remote_rule)
            self.rules_db.update_rule(updated_rule, f"Conflict resolution: priority (remote higher)")
            conflict.resolved = True
            conflict.resolution_data = {"winner": "remote", "reason": "higher_priority"}
        else:
            # Local rule has higher or same priority
            conflict.resolved = True
            conflict.resolution_data = {"winner": "local", "reason": "higher_or_same_priority"}
        
        logger.info(f"Resolved conflict {conflict.conflict_id} by priority")
    
    async def _flag_for_manual_review(self, conflict: RuleSyncConflict):
        """Flag conflict for manual review"""
        # Store conflict for manual resolution
        conflict.resolution_data = {"status": "pending_manual_review", "flagged_at": datetime.now().isoformat()}
        
        # Broadcast conflict notification
        if self.redis_client:
            conflict_notification = {
                "type": "rule_conflict",
                "conflict_id": conflict.conflict_id,
                "rule_id": conflict.rule_id,
                "conflict_type": conflict.conflict_type,
                "machine_id": self.machine_id,
                "timestamp": datetime.now().isoformat()
            }
            self.redis_client.publish("haivemind:rules:conflicts", json.dumps(conflict_notification))
        
        logger.warning(f"Rule conflict flagged for manual review: {conflict.conflict_id}")
    
    async def _send_sync_acknowledgment(self, sync_message: RuleSyncMessage, status: str, error: Optional[str] = None):
        """Send acknowledgment for sync operation"""
        if not self.redis_client:
            return
        
        ack_message = {
            "sync_id": sync_message.sync_id,
            "source_machine": sync_message.source_machine,
            "responding_machine": self.machine_id,
            "status": status,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        self.redis_client.publish("haivemind:rules:acknowledgments", json.dumps(ack_message))
    
    async def _store_sync_memory(self, sync_message: RuleSyncMessage, operation_status: str, importance: str = "medium"):
        """Store sync operation in hAIveMind memory"""
        try:
            content = f"Rules sync {operation_status}: {sync_message.operation.value} from {sync_message.source_machine}"
            
            self.memory_storage.store_memory(
                content=content,
                category="rules",
                metadata={
                    "sync_operation": {
                        "sync_id": sync_message.sync_id,
                        "operation": sync_message.operation.value,
                        "priority": sync_message.priority.value,
                        "source_machine": sync_message.source_machine,
                        "status": operation_status,
                        "rule_count": len(sync_message.rule_data.get('rules', [])) if sync_message.operation == RuleSyncOperation.BULK_SYNC else 1
                    },
                    "sharing_scope": "network-shared",
                    "importance": importance,
                    "tags": ["sync", "rules", "network", sync_message.operation.value]
                }
            )
        except Exception as e:
            logger.error(f"Failed to store sync memory: {e}")
    
    async def _store_conflict_memory(self, conflict: RuleSyncConflict):
        """Store conflict information in hAIveMind memory"""
        try:
            content = f"Rule sync conflict detected: {conflict.conflict_type} for rule {conflict.rule_id}"
            
            self.memory_storage.store_memory(
                content=content,
                category="rules",
                metadata={
                    "conflict_data": {
                        "conflict_id": conflict.conflict_id,
                        "rule_id": conflict.rule_id,
                        "conflict_type": conflict.conflict_type,
                        "resolution_strategy": conflict.resolution_strategy.value,
                        "resolved": conflict.resolved
                    },
                    "sharing_scope": "network-shared",
                    "importance": "high",
                    "tags": ["conflict", "rules", "sync", "governance"]
                }
            )
        except Exception as e:
            logger.error(f"Failed to store conflict memory: {e}")
    
    async def _periodic_sync_health_check(self):
        """Periodic health check for sync operations"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Clean up completed syncs
                current_time = datetime.now()
                completed_syncs = []
                
                for sync_id, status in list(self.active_syncs.items()):
                    if status.status in ["completed", "failed"]:
                        if current_time - status.started_at > timedelta(hours=1):
                            completed_syncs.append(sync_id)
                            self.sync_history.append(status)
                
                for sync_id in completed_syncs:
                    del self.active_syncs[sync_id]
                
                # Update metrics
                self._update_sync_metrics()
                
                # Check for stale conflicts
                await self._check_stale_conflicts()
                
            except Exception as e:
                logger.error(f"Error in sync health check: {e}")
    
    async def _cleanup_expired_syncs(self):
        """Clean up expired sync operations"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                current_time = datetime.now()
                expired_syncs = []
                
                for sync_id, status in list(self.active_syncs.items()):
                    if current_time - status.started_at > timedelta(hours=24):
                        expired_syncs.append(sync_id)
                        status.status = "expired"
                        self.sync_history.append(status)
                
                for sync_id in expired_syncs:
                    del self.active_syncs[sync_id]
                
                logger.info(f"Cleaned up {len(expired_syncs)} expired sync operations")
                
            except Exception as e:
                logger.error(f"Error in sync cleanup: {e}")
    
    async def _check_stale_conflicts(self):
        """Check for stale conflicts that need attention"""
        current_time = datetime.now()
        stale_conflicts = []
        
        for conflict_id, conflict in self.pending_conflicts.items():
            if not conflict.resolved and current_time - conflict.created_at > timedelta(hours=24):
                stale_conflicts.append(conflict)
        
        if stale_conflicts:
            logger.warning(f"Found {len(stale_conflicts)} stale rule conflicts requiring attention")
            
            # Broadcast stale conflict alert
            if self.redis_client:
                alert = {
                    "type": "stale_conflicts",
                    "count": len(stale_conflicts),
                    "machine_id": self.machine_id,
                    "timestamp": current_time.isoformat()
                }
                self.redis_client.publish("haivemind:rules:alerts", json.dumps(alert))
    
    def _update_sync_metrics(self):
        """Update sync performance metrics"""
        total_syncs = len(self.sync_history) + len(self.active_syncs)
        successful_syncs = len([s for s in self.sync_history if s.status == "completed"])
        failed_syncs = len([s for s in self.sync_history if s.status == "failed"])
        
        # Calculate average sync time
        completed_syncs = [s for s in self.sync_history if s.status == "completed" and s.completed_at]
        if completed_syncs:
            total_time = sum((s.completed_at - s.started_at).total_seconds() for s in completed_syncs)
            avg_sync_time = total_time / len(completed_syncs)
        else:
            avg_sync_time = 0.0
        
        self.sync_metrics.update({
            'total_syncs': total_syncs,
            'successful_syncs': successful_syncs,
            'failed_syncs': failed_syncs,
            'conflicts_resolved': len([c for c in self.pending_conflicts.values() if c.resolved]),
            'avg_sync_time': avg_sync_time
        })
    
    def _calculate_rule_checksum(self, rule_data: Dict[str, Any]) -> str:
        """Calculate checksum for rule data"""
        # Create deterministic string representation
        rule_str = json.dumps(rule_data, sort_keys=True)
        return hashlib.sha256(rule_str.encode()).hexdigest()
    
    def _calculate_bulk_checksum(self, rules_data: List[Dict[str, Any]]) -> str:
        """Calculate checksum for bulk rule data"""
        # Sort rules by ID for deterministic checksum
        sorted_rules = sorted(rules_data, key=lambda r: r.get('id', ''))
        bulk_str = json.dumps(sorted_rules, sort_keys=True)
        return hashlib.sha256(bulk_str.encode()).hexdigest()
    
    def get_sync_status(self, sync_id: Optional[str] = None) -> Dict[str, Any]:
        """Get sync operation status"""
        if sync_id:
            if sync_id in self.active_syncs:
                return asdict(self.active_syncs[sync_id])
            else:
                # Check history
                for status in self.sync_history:
                    if status.sync_id == sync_id:
                        return asdict(status)
                return {"error": f"Sync {sync_id} not found"}
        else:
            return {
                "active_syncs": {sid: asdict(status) for sid, status in self.active_syncs.items()},
                "pending_conflicts": len(self.pending_conflicts),
                "metrics": self.sync_metrics
            }
    
    def get_conflict_status(self, conflict_id: Optional[str] = None) -> Dict[str, Any]:
        """Get conflict resolution status"""
        if conflict_id:
            if conflict_id in self.pending_conflicts:
                return asdict(self.pending_conflicts[conflict_id])
            else:
                return {"error": f"Conflict {conflict_id} not found"}
        else:
            return {
                "pending_conflicts": {cid: asdict(conflict) for cid, conflict in self.pending_conflicts.items()},
                "total_conflicts": len(self.pending_conflicts),
                "resolved_conflicts": len([c for c in self.pending_conflicts.values() if c.resolved])
            }
    
    async def resolve_conflict_manually(self, conflict_id: str, resolution: str, resolved_by: str) -> bool:
        """Manually resolve a rule conflict"""
        if conflict_id not in self.pending_conflicts:
            return False
        
        conflict = self.pending_conflicts[conflict_id]
        
        try:
            if resolution == "use_local":
                # Keep local rule
                conflict.resolved = True
                conflict.resolution_data = {"winner": "local", "reason": "manual_resolution", "resolved_by": resolved_by}
            elif resolution == "use_remote":
                # Apply remote rule
                updated_rule = self.rule_service._dict_to_rule(conflict.remote_rule)
                self.rules_db.update_rule(updated_rule, f"Manual conflict resolution by {resolved_by}")
                conflict.resolved = True
                conflict.resolution_data = {"winner": "remote", "reason": "manual_resolution", "resolved_by": resolved_by}
            elif resolution == "merge":
                # Attempt to merge rules (simplified implementation)
                merged_rule_data = self._merge_rule_data(conflict.local_rule, conflict.remote_rule)
                merged_rule = self.rule_service._dict_to_rule(merged_rule_data)
                self.rules_db.update_rule(merged_rule, f"Manual conflict merge by {resolved_by}")
                conflict.resolved = True
                conflict.resolution_data = {"winner": "merged", "reason": "manual_merge", "resolved_by": resolved_by}
            else:
                return False
            
            # Store resolution in memory
            if self.memory_storage:
                await self._store_conflict_resolution_memory(conflict, resolved_by)
            
            logger.info(f"Manually resolved conflict {conflict_id} with resolution: {resolution}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to manually resolve conflict {conflict_id}: {e}")
            return False
    
    def _merge_rule_data(self, local_rule: Dict[str, Any], remote_rule: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two rule data dictionaries (simplified implementation)"""
        # This is a basic merge strategy - in production, this would be more sophisticated
        merged = local_rule.copy()
        
        # Use remote rule's timestamp if it's newer
        local_updated = datetime.fromisoformat(local_rule.get('updated_at', '1970-01-01T00:00:00'))
        remote_updated = datetime.fromisoformat(remote_rule.get('updated_at', '1970-01-01T00:00:00'))
        
        if remote_updated > local_updated:
            merged['updated_at'] = remote_rule['updated_at']
            merged['updated_by'] = f"merge_{remote_rule.get('updated_by', 'unknown')}"
        
        # Merge tags
        local_tags = set(local_rule.get('tags', []))
        remote_tags = set(remote_rule.get('tags', []))
        merged['tags'] = list(local_tags.union(remote_tags))
        
        # Increment version
        merged['version'] = max(local_rule.get('version', 1), remote_rule.get('version', 1)) + 1
        
        return merged
    
    async def _store_conflict_resolution_memory(self, conflict: RuleSyncConflict, resolved_by: str):
        """Store conflict resolution in hAIveMind memory"""
        try:
            content = f"Rule conflict resolved: {conflict.conflict_id} by {resolved_by}"
            
            self.memory_storage.store_memory(
                content=content,
                category="rules",
                metadata={
                    "conflict_resolution": {
                        "conflict_id": conflict.conflict_id,
                        "rule_id": conflict.rule_id,
                        "resolution_data": conflict.resolution_data,
                        "resolved_by": resolved_by,
                        "resolved_at": datetime.now().isoformat()
                    },
                    "sharing_scope": "network-shared",
                    "importance": "medium",
                    "tags": ["conflict", "resolution", "rules", "governance"]
                }
            )
        except Exception as e:
            logger.error(f"Failed to store conflict resolution memory: {e}")