#!/usr/bin/env python3
"""
Enterprise Rule Features for hAIveMind Rules Engine
Provides multi-tenant isolation, approval workflows, audit trails, and enterprise governance

Author: Lance James, Unit 221B Inc
"""

import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
from dataclasses import dataclass, asdict
import logging
import hashlib
from pathlib import Path

from rules_engine import Rule, RuleStatus
from advanced_rule_types import AdvancedRule

logger = logging.getLogger(__name__)

class TenantType(Enum):
    """Types of tenants in multi-tenant environment"""
    ENTERPRISE = "enterprise"
    DEPARTMENT = "department"
    PROJECT = "project"
    TEAM = "team"
    INDIVIDUAL = "individual"

class ApprovalStatus(Enum):
    """Approval workflow status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"

class WorkflowStage(Enum):
    """Workflow approval stages"""
    INITIAL_REVIEW = "initial_review"
    TECHNICAL_REVIEW = "technical_review"
    SECURITY_REVIEW = "security_review"
    COMPLIANCE_REVIEW = "compliance_review"
    MANAGEMENT_APPROVAL = "management_approval"
    FINAL_APPROVAL = "final_approval"

class AuditEventType(Enum):
    """Types of audit events"""
    RULE_CREATED = "rule_created"
    RULE_UPDATED = "rule_updated"
    RULE_ACTIVATED = "rule_activated"
    RULE_DEACTIVATED = "rule_deactivated"
    RULE_DELETED = "rule_deleted"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    RULE_EVALUATED = "rule_evaluated"
    POLICY_VIOLATION = "policy_violation"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"

@dataclass
class Tenant:
    """Multi-tenant organization unit"""
    id: str
    name: str
    type: TenantType
    created_at: datetime
    created_by: str
    parent_tenant_id: Optional[str] = None
    settings: Dict[str, Any] = None
    metadata: Dict[str, Any] = None

@dataclass
class ApprovalWorkflow:
    """Rule approval workflow configuration"""
    id: str
    name: str
    description: str
    stages: List[WorkflowStage]
    approvers: Dict[WorkflowStage, List[str]]
    created_at: datetime
    created_by: str
    auto_approval_conditions: Optional[Dict[str, Any]] = None
    escalation_rules: Optional[Dict[str, Any]] = None
    timeout_hours: int = 72

@dataclass
class ApprovalRequest:
    """Rule approval request"""
    id: str
    rule_id: str
    workflow_id: str
    requester_id: str
    current_stage: WorkflowStage
    status: ApprovalStatus
    requested_at: datetime
    completed_at: Optional[datetime] = None
    approvals: List[Dict[str, Any]] = None
    comments: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

@dataclass
class AuditEvent:
    """Audit trail event"""
    id: str
    event_type: AuditEventType
    tenant_id: str
    user_id: str
    resource_id: str
    resource_type: str
    event_data: Dict[str, Any]
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class RuleImpactAnalysis:
    """Rule change impact analysis"""
    rule_id: str
    affected_systems: List[str]
    affected_users: int
    risk_level: str
    performance_impact: Dict[str, Any]
    compliance_impact: Dict[str, Any]
    rollback_plan: str
    testing_requirements: List[str]
    analysis_date: datetime

class EnterpriseRuleManager:
    """Enterprise-grade rule management with multi-tenancy and governance"""
    
    def __init__(self, db_path: str, memory_storage, redis_client=None, config: Dict[str, Any] = None):
        self.db_path = Path(db_path)
        self.memory_storage = memory_storage
        self.redis_client = redis_client
        self.config = config or {}
        
        # Initialize enterprise database
        self._init_enterprise_database()
        
        # Initialize workflow engine
        self.workflow_engine = ApprovalWorkflowEngine(self.db_path, memory_storage)
        
        # Initialize audit system
        self.audit_system = AuditSystem(self.db_path, memory_storage)
        
        # Initialize impact analyzer
        self.impact_analyzer = RuleImpactAnalyzer(memory_storage)
        
        # Initialize tenant manager
        self.tenant_manager = TenantManager(self.db_path, memory_storage)
    
    def _init_enterprise_database(self):
        """Initialize enterprise database schema"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            # Tenants table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    parent_tenant_id TEXT,
                    settings TEXT NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP NOT NULL,
                    created_by TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (parent_tenant_id) REFERENCES tenants (id)
                )
            """)
            
            # Approval workflows table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS approval_workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    stages TEXT NOT NULL,
                    approvers TEXT NOT NULL,
                    auto_approval_conditions TEXT,
                    escalation_rules TEXT,
                    timeout_hours INTEGER DEFAULT 72,
                    created_at TIMESTAMP NOT NULL,
                    created_by TEXT NOT NULL
                )
            """)
            
            # Approval requests table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS approval_requests (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    requester_id TEXT NOT NULL,
                    current_stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    approvals TEXT DEFAULT '[]',
                    comments TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (workflow_id) REFERENCES approval_workflows (id)
                )
            """)
            
            # Audit events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    event_data TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (tenant_id) REFERENCES tenants (id)
                )
            """)
            
            # Rule impact analysis table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rule_impact_analysis (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    affected_systems TEXT NOT NULL,
                    affected_users INTEGER NOT NULL,
                    risk_level TEXT NOT NULL,
                    performance_impact TEXT NOT NULL,
                    compliance_impact TEXT NOT NULL,
                    rollback_plan TEXT NOT NULL,
                    testing_requirements TEXT NOT NULL,
                    analysis_date TIMESTAMP NOT NULL
                )
            """)
            
            # Tenant rule assignments table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenant_rule_assignments (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    rule_id TEXT NOT NULL,
                    inherited BOOLEAN DEFAULT FALSE,
                    override_settings TEXT DEFAULT '{}',
                    assigned_at TIMESTAMP NOT NULL,
                    assigned_by TEXT NOT NULL,
                    FOREIGN KEY (tenant_id) REFERENCES tenants (id),
                    UNIQUE(tenant_id, rule_id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tenants_parent ON tenants (parent_tenant_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests (status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_tenant ON audit_events (tenant_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events (timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tenant_assignments ON tenant_rule_assignments (tenant_id)")
    
    async def create_rule_with_approval(self, rule: AdvancedRule, requester_id: str, 
                                       workflow_id: str, tenant_id: str) -> str:
        """Create rule with approval workflow"""
        # Perform impact analysis
        impact_analysis = await self.impact_analyzer.analyze_rule_impact(rule, tenant_id)
        
        # Create approval request
        approval_request = ApprovalRequest(
            id=str(uuid.uuid4()),
            rule_id=rule.id,
            workflow_id=workflow_id,
            requester_id=requester_id,
            current_stage=WorkflowStage.INITIAL_REVIEW,
            status=ApprovalStatus.PENDING,
            requested_at=datetime.now(),
            metadata={
                'tenant_id': tenant_id,
                'impact_analysis': asdict(impact_analysis),
                'rule_data': asdict(rule)
            }
        )
        
        # Store approval request
        request_id = await self.workflow_engine.create_approval_request(approval_request)
        
        # Audit the request
        await self.audit_system.log_event(AuditEvent(
            id=str(uuid.uuid4()),
            event_type=AuditEventType.APPROVAL_REQUESTED,
            tenant_id=tenant_id,
            user_id=requester_id,
            resource_id=rule.id,
            resource_type="rule",
            event_data={
                'workflow_id': workflow_id,
                'approval_request_id': request_id,
                'impact_analysis': asdict(impact_analysis)
            },
            timestamp=datetime.now()
        ))
        
        # Store in hAIveMind memory
        self.memory_storage.store_memory(
            content=f"Rule approval requested: {rule.name}",
            category="enterprise",
            metadata={
                'rule_id': rule.id,
                'approval_request_id': request_id,
                'tenant_id': tenant_id,
                'workflow_id': workflow_id,
                'impact_analysis': asdict(impact_analysis)
            }
        )
        
        # Start approval workflow
        await self.workflow_engine.start_workflow(request_id)
        
        return request_id
    
    async def get_tenant_rules(self, tenant_id: str, include_inherited: bool = True) -> List[Rule]:
        """Get all rules applicable to a tenant"""
        import sqlite3
        
        rules = []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get directly assigned rules
            cursor = conn.execute("""
                SELECT r.*, tra.override_settings, tra.inherited
                FROM rules r
                JOIN tenant_rule_assignments tra ON r.id = tra.rule_id
                WHERE tra.tenant_id = ?
            """, (tenant_id,))
            
            for row in cursor.fetchall():
                rule = self._row_to_rule(row)
                # Apply tenant-specific overrides
                if row['override_settings']:
                    overrides = json.loads(row['override_settings'])
                    self._apply_tenant_overrides(rule, overrides)
                rules.append(rule)
            
            # Get inherited rules if requested
            if include_inherited:
                inherited_rules = await self._get_inherited_rules(tenant_id)
                rules.extend(inherited_rules)
        
        return rules
    
    async def assign_rule_to_tenant(self, rule_id: str, tenant_id: str, 
                                   assigned_by: str, override_settings: Dict[str, Any] = None) -> bool:
        """Assign a rule to a tenant"""
        import sqlite3
        
        assignment_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tenant_rule_assignments
                (id, tenant_id, rule_id, inherited, override_settings, assigned_at, assigned_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                assignment_id, tenant_id, rule_id, False,
                json.dumps(override_settings or {}),
                datetime.now().isoformat(), assigned_by
            ))
        
        # Audit the assignment
        await self.audit_system.log_event(AuditEvent(
            id=str(uuid.uuid4()),
            event_type=AuditEventType.RULE_CREATED,
            tenant_id=tenant_id,
            user_id=assigned_by,
            resource_id=rule_id,
            resource_type="rule_assignment",
            event_data={
                'assignment_id': assignment_id,
                'override_settings': override_settings
            },
            timestamp=datetime.now()
        ))
        
        return True
    
    async def get_compliance_report(self, tenant_id: str, framework: str = None, 
                                   start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Generate compliance report for tenant"""
        import sqlite3
        
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        report = {
            'tenant_id': tenant_id,
            'framework': framework,
            'report_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'compliance_status': {},
            'rule_evaluations': {},
            'violations': [],
            'recommendations': []
        }
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get compliance-related audit events
            cursor = conn.execute("""
                SELECT * FROM audit_events 
                WHERE tenant_id = ? 
                AND timestamp BETWEEN ? AND ?
                AND event_type IN ('rule_evaluated', 'policy_violation')
                ORDER BY timestamp DESC
            """, (tenant_id, start_date.isoformat(), end_date.isoformat()))
            
            evaluations = []
            violations = []
            
            for row in cursor.fetchall():
                event_data = json.loads(row['event_data'])
                
                if row['event_type'] == 'rule_evaluated':
                    evaluations.append({
                        'rule_id': row['resource_id'],
                        'timestamp': row['timestamp'],
                        'result': event_data.get('result'),
                        'compliance_status': event_data.get('compliance_status')
                    })
                elif row['event_type'] == 'policy_violation':
                    violations.append({
                        'rule_id': row['resource_id'],
                        'timestamp': row['timestamp'],
                        'violation_type': event_data.get('violation_type'),
                        'severity': event_data.get('severity'),
                        'description': event_data.get('description')
                    })
            
            report['rule_evaluations'] = evaluations
            report['violations'] = violations
            
            # Calculate compliance metrics
            total_evaluations = len(evaluations)
            compliant_evaluations = len([e for e in evaluations if e.get('compliance_status') == 'compliant'])
            
            report['compliance_status'] = {
                'total_evaluations': total_evaluations,
                'compliant_evaluations': compliant_evaluations,
                'compliance_rate': compliant_evaluations / total_evaluations if total_evaluations > 0 else 0,
                'total_violations': len(violations),
                'critical_violations': len([v for v in violations if v.get('severity') == 'critical'])
            }
        
        # Generate recommendations
        if report['compliance_status']['compliance_rate'] < 0.95:
            report['recommendations'].append({
                'type': 'compliance_improvement',
                'priority': 'high',
                'description': 'Compliance rate below 95%. Review and update rule configurations.',
                'actions': ['review_failed_evaluations', 'update_rule_conditions', 'provide_training']
            })
        
        if report['compliance_status']['critical_violations'] > 0:
            report['recommendations'].append({
                'type': 'critical_violations',
                'priority': 'critical',
                'description': f"{report['compliance_status']['critical_violations']} critical violations found.",
                'actions': ['immediate_remediation', 'root_cause_analysis', 'process_improvement']
            })
        
        return report
    
    async def _get_inherited_rules(self, tenant_id: str) -> List[Rule]:
        """Get rules inherited from parent tenants"""
        import sqlite3
        
        inherited_rules = []
        
        # Get tenant hierarchy
        tenant_hierarchy = await self.tenant_manager.get_tenant_hierarchy(tenant_id)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            for parent_tenant_id in tenant_hierarchy:
                cursor = conn.execute("""
                    SELECT r.*, tra.override_settings
                    FROM rules r
                    JOIN tenant_rule_assignments tra ON r.id = tra.rule_id
                    WHERE tra.tenant_id = ? AND tra.inherited = TRUE
                """, (parent_tenant_id,))
                
                for row in cursor.fetchall():
                    rule = self._row_to_rule(row)
                    # Mark as inherited
                    rule.metadata = rule.metadata or {}
                    rule.metadata['inherited_from'] = parent_tenant_id
                    inherited_rules.append(rule)
        
        return inherited_rules
    
    def _apply_tenant_overrides(self, rule: Rule, overrides: Dict[str, Any]):
        """Apply tenant-specific rule overrides"""
        for key, value in overrides.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
            elif rule.metadata:
                rule.metadata[key] = value
    
    def _row_to_rule(self, row) -> Rule:
        """Convert database row to Rule object"""
        # This would use the existing rule conversion logic
        # Placeholder implementation
        return Rule(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            # ... other fields
        )


class ApprovalWorkflowEngine:
    """Manages rule approval workflows"""
    
    def __init__(self, db_path: Path, memory_storage):
        self.db_path = db_path
        self.memory_storage = memory_storage
    
    async def create_approval_request(self, request: ApprovalRequest) -> str:
        """Create a new approval request"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO approval_requests
                (id, rule_id, workflow_id, requester_id, current_stage, status, requested_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.id, request.rule_id, request.workflow_id, request.requester_id,
                request.current_stage.value, request.status.value,
                request.requested_at.isoformat(), json.dumps(request.metadata or {})
            ))
        
        return request.id
    
    async def start_workflow(self, request_id: str) -> bool:
        """Start the approval workflow"""
        # Get workflow definition
        workflow = await self._get_workflow(request_id)
        if not workflow:
            return False
        
        # Notify first stage approvers
        await self._notify_approvers(request_id, workflow.stages[0])
        
        return True
    
    async def process_approval(self, request_id: str, approver_id: str, 
                              approved: bool, comments: str = "") -> bool:
        """Process an approval decision"""
        import sqlite3
        
        # Get current request
        request = await self._get_approval_request(request_id)
        if not request:
            return False
        
        # Record approval
        approval_record = {
            'approver_id': approver_id,
            'stage': request.current_stage.value,
            'approved': approved,
            'comments': comments,
            'timestamp': datetime.now().isoformat()
        }
        
        if not request.approvals:
            request.approvals = []
        request.approvals.append(approval_record)
        
        # Update request
        with sqlite3.connect(self.db_path) as conn:
            if approved:
                # Move to next stage or complete
                workflow = await self._get_workflow_by_id(request.workflow_id)
                current_stage_index = workflow.stages.index(request.current_stage)
                
                if current_stage_index < len(workflow.stages) - 1:
                    # Move to next stage
                    next_stage = workflow.stages[current_stage_index + 1]
                    conn.execute("""
                        UPDATE approval_requests 
                        SET current_stage = ?, approvals = ?
                        WHERE id = ?
                    """, (next_stage.value, json.dumps(request.approvals), request_id))
                    
                    # Notify next stage approvers
                    await self._notify_approvers(request_id, next_stage)
                else:
                    # Complete approval
                    conn.execute("""
                        UPDATE approval_requests 
                        SET status = ?, completed_at = ?, approvals = ?
                        WHERE id = ?
                    """, (ApprovalStatus.APPROVED.value, datetime.now().isoformat(),
                          json.dumps(request.approvals), request_id))
                    
                    # Activate the rule
                    await self._activate_approved_rule(request_id)
            else:
                # Reject request
                conn.execute("""
                    UPDATE approval_requests 
                    SET status = ?, completed_at = ?, approvals = ?
                    WHERE id = ?
                """, (ApprovalStatus.REJECTED.value, datetime.now().isoformat(),
                      json.dumps(request.approvals), request_id))
        
        return True


class AuditSystem:
    """Comprehensive audit trail system"""
    
    def __init__(self, db_path: Path, memory_storage):
        self.db_path = db_path
        self.memory_storage = memory_storage
    
    async def log_event(self, event: AuditEvent) -> str:
        """Log an audit event"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO audit_events
                (id, event_type, tenant_id, user_id, resource_id, resource_type, 
                 event_data, timestamp, ip_address, user_agent, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.id, event.event_type.value, event.tenant_id, event.user_id,
                event.resource_id, event.resource_type, json.dumps(event.event_data),
                event.timestamp.isoformat(), event.ip_address, event.user_agent,
                json.dumps(event.metadata or {})
            ))
        
        # Store in hAIveMind memory for network awareness
        self.memory_storage.store_memory(
            content=f"Audit event: {event.event_type.value}",
            category="audit",
            metadata={
                'event_id': event.id,
                'event_type': event.event_type.value,
                'tenant_id': event.tenant_id,
                'resource_id': event.resource_id,
                'resource_type': event.resource_type
            }
        )
        
        return event.id
    
    async def get_audit_trail(self, resource_id: str, resource_type: str = None,
                             start_date: datetime = None, end_date: datetime = None) -> List[AuditEvent]:
        """Get audit trail for a resource"""
        import sqlite3
        
        conditions = ["resource_id = ?"]
        params = [resource_id]
        
        if resource_type:
            conditions.append("resource_type = ?")
            params.append(resource_type)
        
        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date.isoformat())
        
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date.isoformat())
        
        where_clause = " AND ".join(conditions)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f"""
                SELECT * FROM audit_events 
                WHERE {where_clause}
                ORDER BY timestamp DESC
            """, params)
            
            events = []
            for row in cursor.fetchall():
                events.append(AuditEvent(
                    id=row['id'],
                    event_type=AuditEventType(row['event_type']),
                    tenant_id=row['tenant_id'],
                    user_id=row['user_id'],
                    resource_id=row['resource_id'],
                    resource_type=row['resource_type'],
                    event_data=json.loads(row['event_data']),
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    ip_address=row['ip_address'],
                    user_agent=row['user_agent'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                ))
            
            return events


class RuleImpactAnalyzer:
    """Analyzes impact of rule changes"""
    
    def __init__(self, memory_storage):
        self.memory_storage = memory_storage
    
    async def analyze_rule_impact(self, rule: AdvancedRule, tenant_id: str) -> RuleImpactAnalysis:
        """Analyze the impact of a rule change"""
        # Analyze affected systems
        affected_systems = await self._analyze_affected_systems(rule, tenant_id)
        
        # Estimate affected users
        affected_users = await self._estimate_affected_users(rule, tenant_id)
        
        # Assess risk level
        risk_level = await self._assess_risk_level(rule, affected_systems, affected_users)
        
        # Analyze performance impact
        performance_impact = await self._analyze_performance_impact(rule)
        
        # Analyze compliance impact
        compliance_impact = await self._analyze_compliance_impact(rule)
        
        # Generate rollback plan
        rollback_plan = await self._generate_rollback_plan(rule)
        
        # Define testing requirements
        testing_requirements = await self._define_testing_requirements(rule, risk_level)
        
        return RuleImpactAnalysis(
            rule_id=rule.id,
            affected_systems=affected_systems,
            affected_users=affected_users,
            risk_level=risk_level,
            performance_impact=performance_impact,
            compliance_impact=compliance_impact,
            rollback_plan=rollback_plan,
            testing_requirements=testing_requirements,
            analysis_date=datetime.now()
        )
    
    async def _analyze_affected_systems(self, rule: AdvancedRule, tenant_id: str) -> List[str]:
        """Analyze which systems will be affected by the rule"""
        affected_systems = []
        
        # Analyze rule scope and conditions
        if rule.scope.value == "global":
            affected_systems.append("all_systems")
        elif rule.scope.value == "project":
            # Query for project-specific systems
            affected_systems.extend(await self._get_project_systems(tenant_id))
        
        # Analyze rule actions for system dependencies
        for action in rule.actions:
            if action.target in ["database", "api", "file_system"]:
                affected_systems.append(action.target)
        
        return list(set(affected_systems))
    
    async def _estimate_affected_users(self, rule: AdvancedRule, tenant_id: str) -> int:
        """Estimate number of users affected by the rule"""
        # This would query user data based on rule conditions
        # Placeholder implementation
        base_users = 100
        
        if rule.scope.value == "global":
            return base_users * 10
        elif rule.scope.value == "project":
            return base_users * 2
        else:
            return base_users
    
    async def _assess_risk_level(self, rule: AdvancedRule, affected_systems: List[str], 
                                affected_users: int) -> str:
        """Assess the risk level of the rule change"""
        risk_score = 0
        
        # System impact factor
        if "all_systems" in affected_systems:
            risk_score += 3
        elif len(affected_systems) > 5:
            risk_score += 2
        elif len(affected_systems) > 2:
            risk_score += 1
        
        # User impact factor
        if affected_users > 1000:
            risk_score += 3
        elif affected_users > 100:
            risk_score += 2
        elif affected_users > 10:
            risk_score += 1
        
        # Rule priority factor
        if rule.priority.value >= 1000:  # CRITICAL
            risk_score += 2
        elif rule.priority.value >= 750:  # HIGH
            risk_score += 1
        
        # Rule type factor
        if rule.rule_type.value in ["security", "compliance"]:
            risk_score += 2
        
        if risk_score >= 7:
            return "critical"
        elif risk_score >= 5:
            return "high"
        elif risk_score >= 3:
            return "medium"
        else:
            return "low"


class TenantManager:
    """Manages multi-tenant organization structure"""
    
    def __init__(self, db_path: Path, memory_storage):
        self.db_path = db_path
        self.memory_storage = memory_storage
    
    async def create_tenant(self, tenant: Tenant) -> str:
        """Create a new tenant"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO tenants
                (id, name, type, parent_tenant_id, settings, created_at, created_by, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tenant.id, tenant.name, tenant.type.value, tenant.parent_tenant_id,
                json.dumps(tenant.settings), tenant.created_at.isoformat(),
                tenant.created_by, json.dumps(tenant.metadata or {})
            ))
        
        return tenant.id
    
    async def get_tenant_hierarchy(self, tenant_id: str) -> List[str]:
        """Get the hierarchy of parent tenants"""
        import sqlite3
        
        hierarchy = []
        current_tenant_id = tenant_id
        
        with sqlite3.connect(self.db_path) as conn:
            while current_tenant_id:
                cursor = conn.execute(
                    "SELECT parent_tenant_id FROM tenants WHERE id = ?",
                    (current_tenant_id,)
                )
                result = cursor.fetchone()
                
                if result and result[0]:
                    hierarchy.append(result[0])
                    current_tenant_id = result[0]
                else:
                    break
        
        return hierarchy