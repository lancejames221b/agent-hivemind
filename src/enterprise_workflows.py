#!/usr/bin/env python3
"""
Enterprise Workflows and Access Control for Playbook CRUD Operations
Story 5b Implementation - Enterprise-grade workflow management

This module provides enterprise features:
- Approval workflows for critical operations
- Role-based access control (RBAC)
- Change management and notifications
- Compliance and audit features
- Collaborative editing sessions
- Resource ownership and sharing
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ApprovalType(Enum):
    """Types of approval workflows"""
    CREATE_CRITICAL = "create_critical"
    UPDATE_PRODUCTION = "update_production"
    DELETE_SHARED = "delete_shared"
    BULK_OPERATION = "bulk_operation"
    SECURITY_CHANGE = "security_change"
    COMPLIANCE_REVIEW = "compliance_review"


class NotificationType(Enum):
    """Types of notifications"""
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    RESOURCE_CREATED = "resource_created"
    RESOURCE_UPDATED = "resource_updated"
    RESOURCE_DELETED = "resource_deleted"
    COLLABORATION_INVITE = "collaboration_invite"
    DEADLINE_WARNING = "deadline_warning"
    SYSTEM_ALERT = "system_alert"


class UserRole(Enum):
    """User roles for RBAC"""
    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"
    MAINTAINER = "maintainer"
    ADMIN = "admin"
    SECURITY_OFFICER = "security_officer"
    COMPLIANCE_OFFICER = "compliance_officer"


@dataclass
class ApprovalRequest:
    """Approval request for workflow operations"""
    request_id: str
    approval_type: ApprovalType
    resource_id: str
    requester_id: str
    operation_details: Dict[str, Any]
    required_approvers: List[str]
    optional_approvers: List[str]
    
    # Status tracking
    status: WorkflowStatus
    created_at: datetime
    deadline: Optional[datetime] = None
    
    # Approval tracking
    approvals: List[Dict[str, Any]] = field(default_factory=list)
    rejections: List[Dict[str, Any]] = field(default_factory=list)
    comments: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    priority: str = "normal"  # low, normal, high, critical
    compliance_tags: List[str] = field(default_factory=list)
    risk_assessment: Optional[Dict[str, Any]] = None


@dataclass
class EditSession:
    """Collaborative editing session"""
    session_id: str
    resource_id: str
    editor_id: str
    started_at: datetime
    last_activity: datetime
    status: str  # active, paused, completed, abandoned
    
    # Collaboration
    participants: List[str] = field(default_factory=list)
    changes: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Session metadata
    session_type: str = "individual"  # individual, collaborative, review
    lock_acquired: bool = False
    auto_save_enabled: bool = True


@dataclass
class AccessPolicy:
    """Access control policy for resources"""
    policy_id: str
    resource_pattern: str  # glob pattern for resource matching
    user_roles: List[UserRole]
    permissions: List[str]  # read, write, delete, admin, execute
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Policy metadata
    created_by: str = ""
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True


@dataclass
class Notification:
    """System notification"""
    notification_id: str
    notification_type: NotificationType
    recipient_id: str
    title: str
    message: str
    data: Dict[str, Any]
    
    # Status
    created_at: datetime
    read_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    
    # Delivery
    channels: List[str] = field(default_factory=lambda: ["in_app"])  # in_app, email, slack, webhook
    priority: str = "normal"
    expires_at: Optional[datetime] = None


class EnterpriseWorkflowManager:
    """Enterprise workflow and access control manager"""
    
    def __init__(self, memory_storage, config: Dict[str, Any]):
        self.memory_storage = memory_storage
        self.config = config
        
        # Workflow configuration
        self.enable_approval_workflows = config.get('enable_approval_workflows', True)
        self.default_approval_timeout = config.get('default_approval_timeout_hours', 72)
        self.auto_approve_low_risk = config.get('auto_approve_low_risk', False)
        
        # Access control configuration
        self.enable_rbac = config.get('enable_rbac', True)
        self.default_user_role = UserRole(config.get('default_user_role', 'contributor'))
        
        # Notification configuration
        self.enable_notifications = config.get('enable_notifications', True)
        self.notification_channels = config.get('notification_channels', ['in_app'])
        
        # Active sessions and workflows
        self.active_approvals: Dict[str, ApprovalRequest] = {}
        self.active_sessions: Dict[str, EditSession] = {}
        self.access_policies: List[AccessPolicy] = []
        
        # Load default policies
        self._load_default_policies()
        
        logger.info("🏢 EnterpriseWorkflowManager initialized")

    # ==================== APPROVAL WORKFLOWS ====================
    
    async def create_approval_request(self,
                                    approval_type: ApprovalType,
                                    resource_id: str,
                                    requester_id: str,
                                    operation_details: Dict[str, Any],
                                    priority: str = "normal") -> ApprovalRequest:
        """Create a new approval request"""
        try:
            request_id = f"approval_{uuid.uuid4().hex[:12]}"
            
            # Determine required approvers based on type and risk
            required_approvers = await self._determine_required_approvers(
                approval_type, resource_id, operation_details
            )
            
            # Calculate deadline
            deadline_hours = self._get_approval_deadline(approval_type, priority)
            deadline = datetime.now() + timedelta(hours=deadline_hours) if deadline_hours else None
            
            # Perform risk assessment
            risk_assessment = await self._assess_operation_risk(
                approval_type, resource_id, operation_details
            )
            
            # Create approval request
            approval_request = ApprovalRequest(
                request_id=request_id,
                approval_type=approval_type,
                resource_id=resource_id,
                requester_id=requester_id,
                operation_details=operation_details,
                required_approvers=required_approvers,
                optional_approvers=[],
                status=WorkflowStatus.PENDING,
                created_at=datetime.now(),
                deadline=deadline,
                priority=priority,
                risk_assessment=risk_assessment
            )
            
            # Store approval request
            await self._store_approval_request(approval_request)
            self.active_approvals[request_id] = approval_request
            
            # Send notifications to approvers
            if self.enable_notifications:
                await self._notify_approvers(approval_request)
            
            # Auto-approve if low risk and enabled
            if (self.auto_approve_low_risk and 
                risk_assessment.get('risk_level') == 'low' and
                approval_type not in [ApprovalType.SECURITY_CHANGE, ApprovalType.COMPLIANCE_REVIEW]):
                
                await self._auto_approve_request(approval_request)
            
            logger.info(f"📋 Created approval request {request_id} for {approval_type.value}")
            return approval_request
            
        except Exception as e:
            logger.error(f"Failed to create approval request: {e}")
            raise

    async def process_approval(self,
                             request_id: str,
                             approver_id: str,
                             decision: str,  # approve, reject
                             comments: str = "") -> Dict[str, Any]:
        """Process an approval decision"""
        try:
            if request_id not in self.active_approvals:
                # Try to load from storage
                approval_request = await self._load_approval_request(request_id)
                if not approval_request:
                    raise ValueError(f"Approval request {request_id} not found")
                self.active_approvals[request_id] = approval_request
            else:
                approval_request = self.active_approvals[request_id]
            
            # Check if approver is authorized
            if approver_id not in approval_request.required_approvers + approval_request.optional_approvers:
                raise PermissionError(f"User {approver_id} is not authorized to approve this request")
            
            # Check if request is still pending
            if approval_request.status != WorkflowStatus.PENDING:
                raise ValueError(f"Approval request is no longer pending (status: {approval_request.status.value})")
            
            # Record decision
            decision_record = {
                "approver_id": approver_id,
                "decision": decision,
                "comments": comments,
                "timestamp": datetime.now().isoformat()
            }
            
            if decision.lower() == "approve":
                approval_request.approvals.append(decision_record)
            else:
                approval_request.rejections.append(decision_record)
            
            # Check if we have enough approvals or any rejection
            if approval_request.rejections:
                approval_request.status = WorkflowStatus.REJECTED
                result_status = "rejected"
            elif len(approval_request.approvals) >= len(approval_request.required_approvers):
                approval_request.status = WorkflowStatus.APPROVED
                result_status = "approved"
            else:
                result_status = "pending_more_approvals"
            
            # Update stored request
            await self._store_approval_request(approval_request)
            
            # Send notifications
            if self.enable_notifications:
                await self._notify_approval_decision(approval_request, decision_record, result_status)
            
            # If approved, execute the operation
            if approval_request.status == WorkflowStatus.APPROVED:
                await self._execute_approved_operation(approval_request)
            
            logger.info(f"✅ Processed approval {request_id}: {decision} by {approver_id}")
            
            return {
                "request_id": request_id,
                "status": result_status,
                "approvals_needed": len(approval_request.required_approvers),
                "approvals_received": len(approval_request.approvals),
                "rejections": len(approval_request.rejections)
            }
            
        except Exception as e:
            logger.error(f"Failed to process approval: {e}")
            raise

    async def get_pending_approvals(self, approver_id: str) -> List[Dict[str, Any]]:
        """Get pending approval requests for a user"""
        try:
            # Search for pending approvals where user is an approver
            search_results = await self.memory_storage.search_memories(
                query=f"required_approvers:{approver_id} OR optional_approvers:{approver_id}",
                category="approval_requests",
                limit=100
            )
            
            pending_approvals = []
            for memory in search_results.get('memories', []):
                try:
                    approval_data = json.loads(memory.get('content', '{}'))
                    if approval_data.get('status') == 'pending':
                        # Check if user hasn't already approved/rejected
                        existing_decisions = (approval_data.get('approvals', []) + 
                                            approval_data.get('rejections', []))
                        
                        if not any(d.get('approver_id') == approver_id for d in existing_decisions):
                            pending_approvals.append({
                                "request_id": approval_data.get('request_id'),
                                "approval_type": approval_data.get('approval_type'),
                                "resource_id": approval_data.get('resource_id'),
                                "requester_id": approval_data.get('requester_id'),
                                "created_at": approval_data.get('created_at'),
                                "deadline": approval_data.get('deadline'),
                                "priority": approval_data.get('priority'),
                                "operation_details": approval_data.get('operation_details', {})
                            })
                except Exception as e:
                    logger.warning(f"Failed to parse approval request: {e}")
            
            return pending_approvals
            
        except Exception as e:
            logger.error(f"Failed to get pending approvals: {e}")
            return []

    # ==================== COLLABORATIVE EDITING ====================
    
    async def start_edit_session(self,
                               resource_id: str,
                               editor_id: str,
                               session_type: str = "individual") -> EditSession:
        """Start a collaborative editing session"""
        try:
            session_id = f"edit_{uuid.uuid4().hex[:12]}"
            
            # Check for existing active sessions
            existing_sessions = await self._get_active_edit_sessions(resource_id)
            
            # Create edit session
            session = EditSession(
                session_id=session_id,
                resource_id=resource_id,
                editor_id=editor_id,
                started_at=datetime.now(),
                last_activity=datetime.now(),
                status="active",
                session_type=session_type,
                participants=[editor_id]
            )
            
            # Try to acquire lock for exclusive editing
            if session_type == "individual" and not existing_sessions:
                session.lock_acquired = True
            
            # Store session
            await self._store_edit_session(session)
            self.active_sessions[session_id] = session
            
            # Notify other editors if there are conflicts
            if existing_sessions and self.enable_notifications:
                await self._notify_concurrent_editing(resource_id, session, existing_sessions)
            
            logger.info(f"✏️ Started edit session {session_id} for resource {resource_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to start edit session: {e}")
            raise

    async def update_edit_session(self,
                                session_id: str,
                                changes: Dict[str, Any],
                                editor_id: str) -> Dict[str, Any]:
        """Update an editing session with changes"""
        try:
            if session_id not in self.active_sessions:
                session = await self._load_edit_session(session_id)
                if not session:
                    raise ValueError(f"Edit session {session_id} not found")
                self.active_sessions[session_id] = session
            else:
                session = self.active_sessions[session_id]
            
            # Verify editor is authorized
            if editor_id not in session.participants:
                raise PermissionError(f"User {editor_id} is not a participant in this session")
            
            # Add change record
            change_record = {
                "editor_id": editor_id,
                "timestamp": datetime.now().isoformat(),
                "changes": changes,
                "change_id": uuid.uuid4().hex[:8]
            }
            
            session.changes.append(change_record)
            session.last_activity = datetime.now()
            
            # Check for conflicts with other sessions
            conflicts = await self._detect_edit_conflicts(session)
            if conflicts:
                session.conflicts.extend(conflicts)
            
            # Update stored session
            await self._store_edit_session(session)
            
            return {
                "session_id": session_id,
                "change_id": change_record["change_id"],
                "conflicts_detected": len(conflicts) > 0,
                "conflicts": conflicts
            }
            
        except Exception as e:
            logger.error(f"Failed to update edit session: {e}")
            raise

    async def resolve_edit_conflicts(self,
                                   session_id: str,
                                   resolution: Dict[str, Any],
                                   resolver_id: str) -> Dict[str, Any]:
        """Resolve editing conflicts between concurrent sessions"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                session = await self._load_edit_session(session_id)
                if not session:
                    raise ValueError(f"Edit session {session_id} not found")
            
            # Apply conflict resolution
            resolved_conflicts = []
            for conflict in session.conflicts:
                if conflict.get('conflict_id') in resolution.get('resolved_conflicts', []):
                    conflict['resolved'] = True
                    conflict['resolution'] = resolution.get('resolutions', {}).get(conflict['conflict_id'])
                    conflict['resolved_by'] = resolver_id
                    conflict['resolved_at'] = datetime.now().isoformat()
                    resolved_conflicts.append(conflict)
            
            # Update session
            await self._store_edit_session(session)
            
            logger.info(f"🔧 Resolved {len(resolved_conflicts)} conflicts in session {session_id}")
            
            return {
                "session_id": session_id,
                "resolved_conflicts": len(resolved_conflicts),
                "remaining_conflicts": len([c for c in session.conflicts if not c.get('resolved')])
            }
            
        except Exception as e:
            logger.error(f"Failed to resolve edit conflicts: {e}")
            raise

    async def end_edit_session(self,
                             session_id: str,
                             editor_id: str,
                             save_changes: bool = True) -> Dict[str, Any]:
        """End an editing session"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                session = await self._load_edit_session(session_id)
                if not session:
                    raise ValueError(f"Edit session {session_id} not found")
            
            # Verify editor is authorized
            if editor_id != session.editor_id and editor_id not in session.participants:
                raise PermissionError(f"User {editor_id} cannot end this session")
            
            # Update session status
            session.status = "completed" if save_changes else "abandoned"
            session.last_activity = datetime.now()
            
            # Store final session state
            await self._store_edit_session(session)
            
            # Remove from active sessions
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            logger.info(f"🏁 Ended edit session {session_id} ({'saved' if save_changes else 'abandoned'})")
            
            return {
                "session_id": session_id,
                "status": session.status,
                "total_changes": len(session.changes),
                "conflicts": len(session.conflicts),
                "duration_minutes": (session.last_activity - session.started_at).total_seconds() / 60
            }
            
        except Exception as e:
            logger.error(f"Failed to end edit session: {e}")
            raise

    # ==================== ACCESS CONTROL ====================
    
    async def check_user_permission(self,
                                  user_id: str,
                                  resource_id: str,
                                  permission: str) -> bool:
        """Check if user has specific permission for a resource"""
        try:
            if not self.enable_rbac:
                return True  # RBAC disabled, allow all
            
            # Get user role
            user_role = await self._get_user_role(user_id)
            
            # Check applicable policies
            applicable_policies = await self._get_applicable_policies(resource_id, user_role)
            
            # Check if any policy grants the permission
            for policy in applicable_policies:
                if permission in policy.permissions:
                    # Check additional conditions
                    if await self._check_policy_conditions(policy, user_id, resource_id):
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check user permission: {e}")
            return False

    async def create_access_policy(self,
                                 resource_pattern: str,
                                 user_roles: List[UserRole],
                                 permissions: List[str],
                                 creator_id: str,
                                 conditions: Optional[Dict[str, Any]] = None) -> AccessPolicy:
        """Create a new access control policy"""
        try:
            policy_id = f"policy_{uuid.uuid4().hex[:12]}"
            
            policy = AccessPolicy(
                policy_id=policy_id,
                resource_pattern=resource_pattern,
                user_roles=user_roles,
                permissions=permissions,
                conditions=conditions or {},
                created_by=creator_id,
                created_at=datetime.now()
            )
            
            # Store policy
            await self._store_access_policy(policy)
            self.access_policies.append(policy)
            
            logger.info(f"🔐 Created access policy {policy_id}")
            return policy
            
        except Exception as e:
            logger.error(f"Failed to create access policy: {e}")
            raise

    # ==================== NOTIFICATIONS ====================
    
    async def send_notification(self,
                              recipient_id: str,
                              notification_type: NotificationType,
                              title: str,
                              message: str,
                              data: Optional[Dict[str, Any]] = None,
                              channels: Optional[List[str]] = None,
                              priority: str = "normal") -> Notification:
        """Send a notification to a user"""
        try:
            if not self.enable_notifications:
                return None
            
            notification_id = f"notif_{uuid.uuid4().hex[:12]}"
            
            notification = Notification(
                notification_id=notification_id,
                notification_type=notification_type,
                recipient_id=recipient_id,
                title=title,
                message=message,
                data=data or {},
                created_at=datetime.now(),
                channels=channels or self.notification_channels,
                priority=priority
            )
            
            # Store notification
            await self._store_notification(notification)
            
            # Send via configured channels
            await self._deliver_notification(notification)
            
            logger.info(f"📬 Sent notification {notification_id} to {recipient_id}")
            return notification
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            raise

    async def get_user_notifications(self,
                                   user_id: str,
                                   unread_only: bool = False,
                                   limit: int = 50) -> List[Dict[str, Any]]:
        """Get notifications for a user"""
        try:
            query = f"recipient_id:{user_id}"
            if unread_only:
                query += " AND read_at:null"
            
            search_results = await self.memory_storage.search_memories(
                query=query,
                category="notifications",
                limit=limit
            )
            
            notifications = []
            for memory in search_results.get('memories', []):
                try:
                    notification_data = json.loads(memory.get('content', '{}'))
                    notifications.append(notification_data)
                except Exception as e:
                    logger.warning(f"Failed to parse notification: {e}")
            
            # Sort by created_at descending
            notifications.sort(key=lambda n: n.get('created_at', ''), reverse=True)
            
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to get user notifications: {e}")
            return []

    # ==================== HELPER METHODS ====================
    
    def _load_default_policies(self):
        """Load default access control policies"""
        try:
            # Admin policy - full access to everything
            admin_policy = AccessPolicy(
                policy_id="default_admin",
                resource_pattern="*",
                user_roles=[UserRole.ADMIN],
                permissions=["read", "write", "delete", "admin", "execute"],
                created_by="system",
                created_at=datetime.now()
            )
            
            # Contributor policy - read/write access to non-critical resources
            contributor_policy = AccessPolicy(
                policy_id="default_contributor",
                resource_pattern="*",
                user_roles=[UserRole.CONTRIBUTOR, UserRole.MAINTAINER],
                permissions=["read", "write", "execute"],
                conditions={"exclude_critical": True},
                created_by="system",
                created_at=datetime.now()
            )
            
            # Viewer policy - read-only access
            viewer_policy = AccessPolicy(
                policy_id="default_viewer",
                resource_pattern="*",
                user_roles=[UserRole.VIEWER],
                permissions=["read"],
                created_by="system",
                created_at=datetime.now()
            )
            
            self.access_policies = [admin_policy, contributor_policy, viewer_policy]
            
        except Exception as e:
            logger.error(f"Failed to load default policies: {e}")

    async def _determine_required_approvers(self,
                                          approval_type: ApprovalType,
                                          resource_id: str,
                                          operation_details: Dict[str, Any]) -> List[str]:
        """Determine required approvers based on operation type and risk"""
        try:
            approvers = []
            
            # Get resource metadata to determine criticality
            # This would integrate with the CRUD manager to get resource info
            
            if approval_type == ApprovalType.SECURITY_CHANGE:
                # Security changes require security officer approval
                security_officers = await self._get_users_by_role(UserRole.SECURITY_OFFICER)
                approvers.extend(security_officers[:1])  # At least one security officer
            
            elif approval_type == ApprovalType.COMPLIANCE_REVIEW:
                # Compliance changes require compliance officer approval
                compliance_officers = await self._get_users_by_role(UserRole.COMPLIANCE_OFFICER)
                approvers.extend(compliance_officers[:1])
            
            elif approval_type == ApprovalType.DELETE_SHARED:
                # Shared resource deletion requires maintainer approval
                maintainers = await self._get_users_by_role(UserRole.MAINTAINER)
                approvers.extend(maintainers[:1])
            
            elif approval_type == ApprovalType.BULK_OPERATION:
                # Bulk operations require admin approval
                admins = await self._get_users_by_role(UserRole.ADMIN)
                approvers.extend(admins[:1])
            
            else:
                # Default: require maintainer approval
                maintainers = await self._get_users_by_role(UserRole.MAINTAINER)
                approvers.extend(maintainers[:1])
            
            return approvers
            
        except Exception as e:
            logger.error(f"Failed to determine required approvers: {e}")
            return []

    async def _assess_operation_risk(self,
                                   approval_type: ApprovalType,
                                   resource_id: str,
                                   operation_details: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk level of an operation"""
        try:
            risk_factors = []
            risk_score = 0
            
            # Base risk by approval type
            type_risk = {
                ApprovalType.CREATE_CRITICAL: 3,
                ApprovalType.UPDATE_PRODUCTION: 4,
                ApprovalType.DELETE_SHARED: 5,
                ApprovalType.BULK_OPERATION: 4,
                ApprovalType.SECURITY_CHANGE: 5,
                ApprovalType.COMPLIANCE_REVIEW: 3
            }
            
            risk_score += type_risk.get(approval_type, 2)
            
            # Additional risk factors
            if operation_details.get('affects_production'):
                risk_score += 2
                risk_factors.append("affects_production")
            
            if operation_details.get('bulk_count', 0) > 10:
                risk_score += 1
                risk_factors.append("large_bulk_operation")
            
            if operation_details.get('has_dependencies'):
                risk_score += 1
                risk_factors.append("has_dependencies")
            
            # Determine risk level
            if risk_score <= 2:
                risk_level = "low"
            elif risk_score <= 4:
                risk_level = "medium"
            elif risk_score <= 6:
                risk_level = "high"
            else:
                risk_level = "critical"
            
            return {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "assessment_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to assess operation risk: {e}")
            return {"risk_level": "medium", "risk_score": 3, "risk_factors": []}

    async def _get_users_by_role(self, role: UserRole) -> List[str]:
        """Get list of users with a specific role"""
        try:
            # This would integrate with user management system
            # For now, return mock data
            role_users = {
                UserRole.ADMIN: ["admin1", "admin2"],
                UserRole.SECURITY_OFFICER: ["security1"],
                UserRole.COMPLIANCE_OFFICER: ["compliance1"],
                UserRole.MAINTAINER: ["maintainer1", "maintainer2"],
                UserRole.CONTRIBUTOR: ["contributor1", "contributor2"],
                UserRole.VIEWER: ["viewer1", "viewer2"]
            }
            
            return role_users.get(role, [])
            
        except Exception as e:
            logger.error(f"Failed to get users by role: {e}")
            return []

    async def _store_approval_request(self, approval_request: ApprovalRequest):
        """Store approval request in memory system"""
        try:
            await self.memory_storage.store_memory(
                content=json.dumps(asdict(approval_request), default=str),
                category="approval_requests",
                metadata={
                    "request_id": approval_request.request_id,
                    "approval_type": approval_request.approval_type.value,
                    "resource_id": approval_request.resource_id,
                    "requester_id": approval_request.requester_id,
                    "status": approval_request.status.value,
                    "priority": approval_request.priority
                },
                tags=["approval", "workflow", approval_request.approval_type.value]
            )
        except Exception as e:
            logger.error(f"Failed to store approval request: {e}")
            raise

    async def _store_edit_session(self, session: EditSession):
        """Store edit session in memory system"""
        try:
            await self.memory_storage.store_memory(
                content=json.dumps(asdict(session), default=str),
                category="edit_sessions",
                metadata={
                    "session_id": session.session_id,
                    "resource_id": session.resource_id,
                    "editor_id": session.editor_id,
                    "status": session.status,
                    "session_type": session.session_type
                },
                tags=["collaboration", "editing", session.session_type]
            )
        except Exception as e:
            logger.error(f"Failed to store edit session: {e}")
            raise

    async def _store_notification(self, notification: Notification):
        """Store notification in memory system"""
        try:
            await self.memory_storage.store_memory(
                content=json.dumps(asdict(notification), default=str),
                category="notifications",
                metadata={
                    "notification_id": notification.notification_id,
                    "notification_type": notification.notification_type.value,
                    "recipient_id": notification.recipient_id,
                    "priority": notification.priority,
                    "read": notification.read_at is not None
                },
                tags=["notification", notification.notification_type.value, notification.priority]
            )
        except Exception as e:
            logger.error(f"Failed to store notification: {e}")
            raise

    logger.info("🏢 EnterpriseWorkflowManager implementation completed")