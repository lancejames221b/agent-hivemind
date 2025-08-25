#!/usr/bin/env python3
"""
hAIveMind Network Governance Service - Centralized Rule Enforcement and Monitoring
Provides network-wide governance, compliance monitoring, and policy enforcement
across the entire hAIveMind agent network with real-time analytics and alerting.

Author: Lance James, Unit 221B Inc
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import threading
from collections import defaultdict

import redis

from .rules_engine import RulesEngine, Rule, RuleType, RuleScope, RulePriority
from .rules_database import RulesDatabase
from .rules_sync_service import RulesSyncService, RuleSyncPriority, RuleSyncOperation
from .agent_rules_integration import AgentRulesIntegration, ComplianceLevel, RuleViolation

logger = logging.getLogger(__name__)

class GovernancePolicy(Enum):
    """Network governance policy types"""
    STRICT_ENFORCEMENT = "strict_enforcement"
    GRADUAL_ROLLOUT = "gradual_rollout"
    ADVISORY_MODE = "advisory_mode"
    EMERGENCY_LOCKDOWN = "emergency_lockdown"

class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class NetworkHealthStatus(Enum):
    """Network health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class GovernanceAlert:
    """Network governance alert"""
    alert_id: str
    alert_type: str
    severity: AlertSeverity
    title: str
    description: str
    affected_machines: List[str]
    affected_agents: List[str]
    rule_ids: List[str]
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class NetworkComplianceMetrics:
    """Network-wide compliance metrics"""
    timestamp: datetime
    total_machines: int
    active_agents: int
    total_rules: int
    active_rules: int
    overall_compliance_score: float
    machine_compliance: Dict[str, float]
    agent_compliance: Dict[str, float]
    rule_effectiveness: Dict[str, float]
    violation_counts: Dict[str, int]
    performance_metrics: Dict[str, float]

@dataclass
class PolicyEnforcementResult:
    """Result of policy enforcement action"""
    policy_id: str
    action_type: str
    target_machines: List[str]
    target_agents: List[str]
    success: bool
    affected_rules: List[str]
    execution_time_ms: int
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

class NetworkGovernanceService:
    """Centralized network governance and policy enforcement service"""
    
    def __init__(self, config: Dict[str, Any], memory_storage=None):
        self.config = config
        self.memory_storage = memory_storage
        self.machine_id = self._get_machine_id()
        
        # Initialize Redis for network communication
        self.redis_client = self._init_redis()
        
        # Initialize component services
        self.rules_sync_service = RulesSyncService(config, memory_storage)
        
        # Network state tracking
        self.known_machines: Set[str] = set()
        self.active_agents: Dict[str, Dict[str, Any]] = {}  # machine_id -> {agent_id: info}
        self.machine_health: Dict[str, Dict[str, Any]] = {}
        self.network_policies: Dict[str, Dict[str, Any]] = {}
        
        # Governance state
        self.active_alerts: Dict[str, GovernanceAlert] = {}
        self.compliance_history: List[NetworkComplianceMetrics] = []
        self.policy_enforcement_log: List[PolicyEnforcementResult] = []
        
        # Configuration
        self.governance_policy = GovernancePolicy(
            config.get('rules', {}).get('governance_policy', 'strict_enforcement')
        )
        self.compliance_threshold = config.get('rules', {}).get('compliance_threshold', 0.8)
        self.alert_cooldown = config.get('rules', {}).get('alert_cooldown_minutes', 30)
        
        # Performance tracking
        self.metrics_collection_interval = 300  # 5 minutes
        self.health_check_interval = 60  # 1 minute
        self.policy_enforcement_interval = 900  # 15 minutes
        
        # Start background services
        self._start_background_services()
    
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
        """Initialize Redis connection for network communication"""
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
            logger.info("Redis connection established for network governance")
            return client
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for network governance: {e}")
            return None
    
    def _start_background_services(self):
        """Start background services for governance monitoring"""
        if self.redis_client:
            # Start network monitoring
            threading.Thread(target=self._network_monitoring_worker, daemon=True).start()
            threading.Thread(target=self._compliance_monitoring_worker, daemon=True).start()
            threading.Thread(target=self._policy_enforcement_worker, daemon=True).start()
            threading.Thread(target=self._alert_management_worker, daemon=True).start()
            
            # Start Redis listeners
            asyncio.create_task(self._listen_for_agent_heartbeats())
            asyncio.create_task(self._listen_for_compliance_reports())
            asyncio.create_task(self._listen_for_governance_events())
    
    async def register_agent(self, agent_id: str, machine_id: str, 
                           agent_info: Dict[str, Any]) -> bool:
        """Register an agent with the governance system"""
        try:
            if machine_id not in self.active_agents:
                self.active_agents[machine_id] = {}
            
            self.active_agents[machine_id][agent_id] = {
                **agent_info,
                'registered_at': datetime.now().isoformat(),
                'last_heartbeat': datetime.now().isoformat(),
                'compliance_level': ComplianceLevel.STRICT.value,
                'status': 'active'
            }
            
            self.known_machines.add(machine_id)
            
            # Broadcast agent registration
            if self.redis_client:
                registration_event = {
                    'type': 'agent_registration',
                    'agent_id': agent_id,
                    'machine_id': machine_id,
                    'agent_info': agent_info,
                    'timestamp': datetime.now().isoformat()
                }
                self.redis_client.publish('haivemind:governance:events', json.dumps(registration_event))
            
            # Store registration in hAIveMind memory
            if self.memory_storage:
                self.memory_storage.store_memory(
                    content=f"Agent registered: {agent_id} on {machine_id}",
                    category="governance",
                    metadata={
                        "agent_registration": {
                            "agent_id": agent_id,
                            "machine_id": machine_id,
                            "agent_info": agent_info
                        },
                        "sharing_scope": "network-shared",
                        "importance": "medium",
                        "tags": ["registration", "governance", "agent"]
                    }
                )
            
            logger.info(f"Agent {agent_id} registered on {machine_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False
    
    async def unregister_agent(self, agent_id: str, machine_id: str) -> bool:
        """Unregister an agent from the governance system"""
        try:
            if machine_id in self.active_agents and agent_id in self.active_agents[machine_id]:
                del self.active_agents[machine_id][agent_id]
                
                # Clean up empty machine entries
                if not self.active_agents[machine_id]:
                    del self.active_agents[machine_id]
                    self.known_machines.discard(machine_id)
                
                # Broadcast agent unregistration
                if self.redis_client:
                    unregistration_event = {
                        'type': 'agent_unregistration',
                        'agent_id': agent_id,
                        'machine_id': machine_id,
                        'timestamp': datetime.now().isoformat()
                    }
                    self.redis_client.publish('haivemind:governance:events', json.dumps(unregistration_event))
                
                logger.info(f"Agent {agent_id} unregistered from {machine_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False
    
    async def enforce_network_policy(self, policy_type: str, policy_data: Dict[str, Any],
                                   target_machines: Optional[List[str]] = None,
                                   target_agents: Optional[List[str]] = None) -> PolicyEnforcementResult:
        """Enforce a network-wide governance policy"""
        policy_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Determine targets
            if not target_machines:
                target_machines = list(self.known_machines)
            
            if not target_agents:
                target_agents = []
                for machine_id in target_machines:
                    if machine_id in self.active_agents:
                        target_agents.extend(self.active_agents[machine_id].keys())
            
            affected_rules = []
            
            # Apply policy based on type
            if policy_type == "compliance_enforcement":
                affected_rules = await self._enforce_compliance_policy(policy_data, target_machines, target_agents)
            elif policy_type == "emergency_lockdown":
                affected_rules = await self._enforce_emergency_lockdown(policy_data, target_machines, target_agents)
            elif policy_type == "rule_rollout":
                affected_rules = await self._enforce_rule_rollout(policy_data, target_machines, target_agents)
            elif policy_type == "performance_optimization":
                affected_rules = await self._enforce_performance_optimization(policy_data, target_machines, target_agents)
            else:
                raise ValueError(f"Unknown policy type: {policy_type}")
            
            execution_time = int((time.time() - start_time) * 1000)
            
            result = PolicyEnforcementResult(
                policy_id=policy_id,
                action_type=policy_type,
                target_machines=target_machines,
                target_agents=target_agents,
                success=True,
                affected_rules=affected_rules,
                execution_time_ms=execution_time,
                metadata=policy_data
            )
            
            self.policy_enforcement_log.append(result)
            
            # Store policy enforcement in memory
            if self.memory_storage:
                await self._store_policy_enforcement_memory(result)
            
            logger.info(f"Policy {policy_type} enforced successfully: {policy_id}")
            return result
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            
            result = PolicyEnforcementResult(
                policy_id=policy_id,
                action_type=policy_type,
                target_machines=target_machines or [],
                target_agents=target_agents or [],
                success=False,
                affected_rules=[],
                execution_time_ms=execution_time,
                error_message=str(e),
                metadata=policy_data
            )
            
            self.policy_enforcement_log.append(result)
            logger.error(f"Policy enforcement failed: {e}")
            return result
    
    async def create_governance_alert(self, alert_type: str, severity: AlertSeverity,
                                    title: str, description: str,
                                    affected_machines: List[str] = None,
                                    affected_agents: List[str] = None,
                                    rule_ids: List[str] = None,
                                    metadata: Dict[str, Any] = None) -> str:
        """Create a governance alert"""
        alert_id = str(uuid.uuid4())
        
        alert = GovernanceAlert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            affected_machines=affected_machines or [],
            affected_agents=affected_agents or [],
            rule_ids=rule_ids or [],
            created_at=datetime.now(),
            metadata=metadata or {}
        )
        
        self.active_alerts[alert_id] = alert
        
        # Broadcast alert
        if self.redis_client:
            alert_event = {
                'type': 'governance_alert',
                'alert': asdict(alert),
                'timestamp': datetime.now().isoformat()
            }
            self.redis_client.publish('haivemind:governance:alerts', json.dumps(alert_event, default=str))
        
        # Store alert in hAIveMind memory
        if self.memory_storage:
            importance = "critical" if severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH] else "medium"
            
            self.memory_storage.store_memory(
                content=f"Governance alert: {title}",
                category="governance",
                metadata={
                    "governance_alert": asdict(alert),
                    "sharing_scope": "network-shared",
                    "importance": importance,
                    "tags": ["alert", "governance", alert_type, severity.value]
                }
            )
        
        logger.warning(f"Governance alert created: {alert_type} - {title}")
        return alert_id
    
    async def resolve_alert(self, alert_id: str, resolved_by: str, 
                          resolution_notes: Optional[str] = None) -> bool:
        """Resolve a governance alert"""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.resolved_at = datetime.now()
        alert.resolution_notes = resolution_notes
        
        # Broadcast alert resolution
        if self.redis_client:
            resolution_event = {
                'type': 'alert_resolution',
                'alert_id': alert_id,
                'resolved_by': resolved_by,
                'resolution_notes': resolution_notes,
                'timestamp': datetime.now().isoformat()
            }
            self.redis_client.publish('haivemind:governance:events', json.dumps(resolution_event))
        
        # Store resolution in memory
        if self.memory_storage:
            self.memory_storage.store_memory(
                content=f"Alert resolved: {alert.title}",
                category="governance",
                metadata={
                    "alert_resolution": {
                        "alert_id": alert_id,
                        "alert_type": alert.alert_type,
                        "resolved_by": resolved_by,
                        "resolution_notes": resolution_notes
                    },
                    "sharing_scope": "network-shared",
                    "importance": "medium",
                    "tags": ["resolution", "governance", "alert"]
                }
            )
        
        logger.info(f"Alert {alert_id} resolved by {resolved_by}")
        return True
    
    async def get_network_compliance_metrics(self) -> NetworkComplianceMetrics:
        """Get current network-wide compliance metrics"""
        try:
            # Collect metrics from all machines
            machine_compliance = {}
            agent_compliance = {}
            total_agents = 0
            
            for machine_id, agents in self.active_agents.items():
                machine_scores = []
                
                for agent_id, agent_info in agents.items():
                    # Get compliance score (would come from agent reports in real implementation)
                    compliance_score = agent_info.get('compliance_score', 1.0)
                    agent_compliance[f"{machine_id}:{agent_id}"] = compliance_score
                    machine_scores.append(compliance_score)
                    total_agents += 1
                
                if machine_scores:
                    machine_compliance[machine_id] = sum(machine_scores) / len(machine_scores)
                else:
                    machine_compliance[machine_id] = 1.0
            
            # Calculate overall compliance
            if agent_compliance:
                overall_compliance = sum(agent_compliance.values()) / len(agent_compliance)
            else:
                overall_compliance = 1.0
            
            # Get rule effectiveness (simplified)
            rule_effectiveness = {}
            
            # Count violations by type
            violation_counts = defaultdict(int)
            
            # Performance metrics
            performance_metrics = {
                'avg_response_time': 0.0,
                'network_latency': 0.0,
                'rule_evaluation_time': 0.0
            }
            
            metrics = NetworkComplianceMetrics(
                timestamp=datetime.now(),
                total_machines=len(self.known_machines),
                active_agents=total_agents,
                total_rules=0,  # Would get from rules database
                active_rules=0,  # Would get from rules database
                overall_compliance_score=overall_compliance,
                machine_compliance=machine_compliance,
                agent_compliance=agent_compliance,
                rule_effectiveness=rule_effectiveness,
                violation_counts=dict(violation_counts),
                performance_metrics=performance_metrics
            )
            
            self.compliance_history.append(metrics)
            
            # Keep only last 24 hours of history
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.compliance_history = [
                m for m in self.compliance_history 
                if m.timestamp >= cutoff_time
            ]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect network compliance metrics: {e}")
            # Return default metrics
            return NetworkComplianceMetrics(
                timestamp=datetime.now(),
                total_machines=len(self.known_machines),
                active_agents=0,
                total_rules=0,
                active_rules=0,
                overall_compliance_score=1.0,
                machine_compliance={},
                agent_compliance={},
                rule_effectiveness={},
                violation_counts={},
                performance_metrics={}
            )
    
    async def get_network_health_status(self) -> Dict[str, Any]:
        """Get overall network health status"""
        try:
            metrics = await self.get_network_compliance_metrics()
            
            # Determine health status
            if metrics.overall_compliance_score >= 0.95:
                health_status = NetworkHealthStatus.HEALTHY
            elif metrics.overall_compliance_score >= 0.8:
                health_status = NetworkHealthStatus.DEGRADED
            elif metrics.overall_compliance_score >= 0.6:
                health_status = NetworkHealthStatus.CRITICAL
            else:
                health_status = NetworkHealthStatus.EMERGENCY
            
            # Count active alerts by severity
            alert_counts = defaultdict(int)
            for alert in self.active_alerts.values():
                if not alert.resolved_at:
                    alert_counts[alert.severity.value] += 1
            
            # Calculate uptime and availability
            total_machines = len(self.known_machines)
            healthy_machines = len([
                m for m, score in metrics.machine_compliance.items() 
                if score >= 0.8
            ])
            
            availability = healthy_machines / max(total_machines, 1) if total_machines > 0 else 1.0
            
            return {
                "health_status": health_status.value,
                "overall_compliance_score": metrics.overall_compliance_score,
                "availability": availability,
                "total_machines": total_machines,
                "healthy_machines": healthy_machines,
                "active_agents": metrics.active_agents,
                "active_alerts": dict(alert_counts),
                "last_updated": metrics.timestamp.isoformat(),
                "governance_policy": self.governance_policy.value,
                "performance_metrics": metrics.performance_metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to get network health status: {e}")
            return {
                "health_status": NetworkHealthStatus.CRITICAL.value,
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            }
    
    def get_governance_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive data for governance dashboard"""
        try:
            # Get latest metrics
            if self.compliance_history:
                latest_metrics = self.compliance_history[-1]
            else:
                latest_metrics = None
            
            # Get recent policy enforcements
            recent_policies = self.policy_enforcement_log[-10:] if self.policy_enforcement_log else []
            
            # Get active alerts
            active_alerts = [
                asdict(alert) for alert in self.active_alerts.values()
                if not alert.resolved_at
            ]
            
            # Get machine status
            machine_status = {}
            for machine_id in self.known_machines:
                agents = self.active_agents.get(machine_id, {})
                machine_status[machine_id] = {
                    "active_agents": len(agents),
                    "last_seen": max([
                        datetime.fromisoformat(agent.get('last_heartbeat', '1970-01-01T00:00:00'))
                        for agent in agents.values()
                    ], default=datetime.min).isoformat() if agents else None,
                    "status": "online" if agents else "offline"
                }
            
            return {
                "network_overview": {
                    "total_machines": len(self.known_machines),
                    "active_agents": sum(len(agents) for agents in self.active_agents.values()),
                    "governance_policy": self.governance_policy.value,
                    "compliance_threshold": self.compliance_threshold
                },
                "latest_metrics": asdict(latest_metrics) if latest_metrics else None,
                "machine_status": machine_status,
                "active_alerts": active_alerts,
                "recent_policy_enforcements": [asdict(p) for p in recent_policies],
                "compliance_trend": self._calculate_compliance_trend(),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate dashboard data: {e}")
            return {"error": str(e), "generated_at": datetime.now().isoformat()}
    
    async def _enforce_compliance_policy(self, policy_data: Dict[str, Any],
                                       target_machines: List[str],
                                       target_agents: List[str]) -> List[str]:
        """Enforce compliance policy across the network"""
        affected_rules = []
        
        # Get compliance requirements
        min_compliance = policy_data.get('min_compliance_score', 0.8)
        enforcement_actions = policy_data.get('actions', ['warn', 'restrict'])
        
        # Check each agent's compliance
        for machine_id in target_machines:
            if machine_id not in self.active_agents:
                continue
            
            for agent_id, agent_info in self.active_agents[machine_id].items():
                if f"{machine_id}:{agent_id}" not in target_agents:
                    continue
                
                compliance_score = agent_info.get('compliance_score', 1.0)
                
                if compliance_score < min_compliance:
                    # Apply enforcement actions
                    if 'warn' in enforcement_actions:
                        await self.create_governance_alert(
                            alert_type="low_compliance",
                            severity=AlertSeverity.HIGH,
                            title=f"Low compliance detected: {agent_id}",
                            description=f"Agent compliance score ({compliance_score:.2f}) below threshold ({min_compliance})",
                            affected_machines=[machine_id],
                            affected_agents=[agent_id]
                        )
                    
                    if 'restrict' in enforcement_actions:
                        # Set agent to advisory mode
                        agent_info['compliance_level'] = ComplianceLevel.ADVISORY.value
                        logger.warning(f"Agent {agent_id} restricted to advisory mode due to low compliance")
        
        return affected_rules
    
    async def _enforce_emergency_lockdown(self, policy_data: Dict[str, Any],
                                        target_machines: List[str],
                                        target_agents: List[str]) -> List[str]:
        """Enforce emergency lockdown policy"""
        affected_rules = []
        
        lockdown_reason = policy_data.get('reason', 'Emergency lockdown initiated')
        
        # Create emergency alert
        await self.create_governance_alert(
            alert_type="emergency_lockdown",
            severity=AlertSeverity.CRITICAL,
            title="Emergency Lockdown Activated",
            description=lockdown_reason,
            affected_machines=target_machines,
            affected_agents=target_agents
        )
        
        # Set all agents to strict compliance
        for machine_id in target_machines:
            if machine_id not in self.active_agents:
                continue
            
            for agent_id, agent_info in self.active_agents[machine_id].items():
                agent_info['compliance_level'] = ComplianceLevel.STRICT.value
                agent_info['emergency_mode'] = True
        
        # Sync critical security rules immediately
        security_rules = policy_data.get('security_rules', [])
        if security_rules:
            for rule_id in security_rules:
                sync_id = await self.rules_sync_service.sync_rule_to_network(
                    rule_id=rule_id,
                    operation=RuleSyncOperation.EMERGENCY_UPDATE,
                    priority=RuleSyncPriority.EMERGENCY,
                    target_machines=target_machines,
                    metadata={"emergency_lockdown": True, "reason": lockdown_reason}
                )
                affected_rules.append(rule_id)
        
        logger.critical(f"Emergency lockdown enforced: {lockdown_reason}")
        return affected_rules
    
    async def _enforce_rule_rollout(self, policy_data: Dict[str, Any],
                                  target_machines: List[str],
                                  target_agents: List[str]) -> List[str]:
        """Enforce gradual rule rollout policy"""
        affected_rules = []
        
        rule_ids = policy_data.get('rule_ids', [])
        rollout_strategy = policy_data.get('strategy', 'gradual')
        rollout_percentage = policy_data.get('percentage', 100)
        
        if rollout_strategy == 'gradual' and rollout_percentage < 100:
            # Select subset of targets for gradual rollout
            import random
            target_count = int(len(target_machines) * rollout_percentage / 100)
            selected_machines = random.sample(target_machines, min(target_count, len(target_machines)))
        else:
            selected_machines = target_machines
        
        # Sync rules to selected machines
        for rule_id in rule_ids:
            sync_id = await self.rules_sync_service.sync_rule_to_network(
                rule_id=rule_id,
                operation=RuleSyncOperation.UPDATE,
                priority=RuleSyncPriority.NORMAL,
                target_machines=selected_machines,
                metadata={"rollout_policy": True, "strategy": rollout_strategy}
            )
            affected_rules.append(rule_id)
        
        logger.info(f"Rule rollout enforced: {len(rule_ids)} rules to {len(selected_machines)} machines")
        return affected_rules
    
    async def _enforce_performance_optimization(self, policy_data: Dict[str, Any],
                                              target_machines: List[str],
                                              target_agents: List[str]) -> List[str]:
        """Enforce performance optimization policy"""
        affected_rules = []
        
        optimization_type = policy_data.get('type', 'caching')
        
        if optimization_type == 'caching':
            # Enable caching for high-activity agents
            for machine_id in target_machines:
                if machine_id not in self.active_agents:
                    continue
                
                for agent_id, agent_info in self.active_agents[machine_id].items():
                    operation_count = agent_info.get('total_operations', 0)
                    if operation_count > 1000:  # High activity threshold
                        agent_info['caching_enabled'] = True
                        logger.info(f"Enabled caching for high-activity agent {agent_id}")
        
        elif optimization_type == 'rule_simplification':
            # Identify and optimize complex rules
            complex_rules = policy_data.get('complex_rules', [])
            for rule_id in complex_rules:
                # This would trigger rule optimization
                affected_rules.append(rule_id)
        
        return affected_rules
    
    async def _store_policy_enforcement_memory(self, result: PolicyEnforcementResult):
        """Store policy enforcement result in hAIveMind memory"""
        try:
            content = f"Policy enforced: {result.action_type} - {'Success' if result.success else 'Failed'}"
            
            self.memory_storage.store_memory(
                content=content,
                category="governance",
                metadata={
                    "policy_enforcement": asdict(result),
                    "sharing_scope": "network-shared",
                    "importance": "high" if not result.success else "medium",
                    "tags": ["policy", "enforcement", "governance", result.action_type]
                }
            )
        except Exception as e:
            logger.error(f"Failed to store policy enforcement memory: {e}")
    
    def _calculate_compliance_trend(self) -> Dict[str, Any]:
        """Calculate compliance trend from historical data"""
        if len(self.compliance_history) < 2:
            return {"trend": "stable", "change": 0.0}
        
        recent_scores = [m.overall_compliance_score for m in self.compliance_history[-10:]]
        
        if len(recent_scores) >= 2:
            change = recent_scores[-1] - recent_scores[0]
            
            if change > 0.05:
                trend = "improving"
            elif change < -0.05:
                trend = "declining"
            else:
                trend = "stable"
            
            return {"trend": trend, "change": change}
        
        return {"trend": "stable", "change": 0.0}
    
    def _network_monitoring_worker(self):
        """Background worker for network monitoring"""
        while True:
            try:
                time.sleep(self.health_check_interval)
                
                # Check machine health
                current_time = datetime.now()
                offline_machines = []
                
                for machine_id in list(self.known_machines):
                    if machine_id not in self.active_agents:
                        offline_machines.append(machine_id)
                        continue
                    
                    # Check agent heartbeats
                    agents = self.active_agents[machine_id]
                    stale_agents = []
                    
                    for agent_id, agent_info in agents.items():
                        last_heartbeat = datetime.fromisoformat(agent_info.get('last_heartbeat', '1970-01-01T00:00:00'))
                        if current_time - last_heartbeat > timedelta(minutes=10):
                            stale_agents.append(agent_id)
                    
                    # Remove stale agents
                    for agent_id in stale_agents:
                        del agents[agent_id]
                        logger.warning(f"Agent {agent_id} on {machine_id} marked as stale")
                    
                    # Remove empty machines
                    if not agents:
                        offline_machines.append(machine_id)
                
                # Remove offline machines
                for machine_id in offline_machines:
                    self.known_machines.discard(machine_id)
                    if machine_id in self.active_agents:
                        del self.active_agents[machine_id]
                
                if offline_machines:
                    logger.info(f"Removed offline machines: {offline_machines}")
                
            except Exception as e:
                logger.error(f"Network monitoring error: {e}")
    
    def _compliance_monitoring_worker(self):
        """Background worker for compliance monitoring"""
        while True:
            try:
                time.sleep(self.metrics_collection_interval)
                
                # Collect network compliance metrics
                asyncio.run(self.get_network_compliance_metrics())
                
                # Check for compliance violations
                for machine_id, agents in self.active_agents.items():
                    for agent_id, agent_info in agents.items():
                        compliance_score = agent_info.get('compliance_score', 1.0)
                        
                        if compliance_score < self.compliance_threshold:
                            # Check if we already have an active alert for this agent
                            existing_alert = any(
                                alert.alert_type == "low_compliance" and
                                agent_id in alert.affected_agents and
                                not alert.resolved_at
                                for alert in self.active_alerts.values()
                            )
                            
                            if not existing_alert:
                                asyncio.run(self.create_governance_alert(
                                    alert_type="low_compliance",
                                    severity=AlertSeverity.MEDIUM,
                                    title=f"Compliance threshold violation: {agent_id}",
                                    description=f"Agent compliance score ({compliance_score:.2f}) below threshold ({self.compliance_threshold})",
                                    affected_machines=[machine_id],
                                    affected_agents=[agent_id]
                                ))
                
            except Exception as e:
                logger.error(f"Compliance monitoring error: {e}")
    
    def _policy_enforcement_worker(self):
        """Background worker for automatic policy enforcement"""
        while True:
            try:
                time.sleep(self.policy_enforcement_interval)
                
                # Check if automatic policy enforcement is needed
                if self.governance_policy == GovernancePolicy.STRICT_ENFORCEMENT:
                    # Enforce compliance policies automatically
                    low_compliance_agents = []
                    
                    for machine_id, agents in self.active_agents.items():
                        for agent_id, agent_info in agents.items():
                            compliance_score = agent_info.get('compliance_score', 1.0)
                            if compliance_score < self.compliance_threshold:
                                low_compliance_agents.append(f"{machine_id}:{agent_id}")
                    
                    if low_compliance_agents:
                        asyncio.run(self.enforce_network_policy(
                            policy_type="compliance_enforcement",
                            policy_data={
                                "min_compliance_score": self.compliance_threshold,
                                "actions": ["warn", "restrict"]
                            },
                            target_agents=low_compliance_agents
                        ))
                
            except Exception as e:
                logger.error(f"Policy enforcement worker error: {e}")
    
    def _alert_management_worker(self):
        """Background worker for alert management"""
        while True:
            try:
                time.sleep(300)  # Check every 5 minutes
                
                # Auto-resolve old alerts based on conditions
                current_time = datetime.now()
                auto_resolved = []
                
                for alert_id, alert in list(self.active_alerts.items()):
                    if alert.resolved_at:
                        continue
                    
                    # Auto-resolve compliance alerts if agents are now compliant
                    if alert.alert_type == "low_compliance":
                        all_compliant = True
                        for agent_id in alert.affected_agents:
                            # Find agent in active_agents
                            agent_found = False
                            for machine_id, agents in self.active_agents.items():
                                if agent_id in agents:
                                    compliance_score = agents[agent_id].get('compliance_score', 1.0)
                                    if compliance_score < self.compliance_threshold:
                                        all_compliant = False
                                    agent_found = True
                                    break
                            
                            if not agent_found:
                                # Agent no longer active, can resolve
                                continue
                        
                        if all_compliant:
                            alert.resolved_at = current_time
                            alert.resolution_notes = "Auto-resolved: agents now compliant"
                            auto_resolved.append(alert_id)
                
                if auto_resolved:
                    logger.info(f"Auto-resolved {len(auto_resolved)} compliance alerts")
                
            except Exception as e:
                logger.error(f"Alert management worker error: {e}")
    
    async def _listen_for_agent_heartbeats(self):
        """Listen for agent heartbeat messages"""
        if not self.redis_client:
            return
        
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("haivemind:agent:heartbeats")
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        heartbeat_data = json.loads(message['data'])
                        agent_id = heartbeat_data.get('agent_id')
                        machine_id = heartbeat_data.get('machine_id')
                        
                        if machine_id in self.active_agents and agent_id in self.active_agents[machine_id]:
                            self.active_agents[machine_id][agent_id]['last_heartbeat'] = datetime.now().isoformat()
                            
                            # Update compliance score if provided
                            if 'compliance_score' in heartbeat_data:
                                self.active_agents[machine_id][agent_id]['compliance_score'] = heartbeat_data['compliance_score']
                        
                    except Exception as e:
                        logger.error(f"Error processing heartbeat: {e}")
        except Exception as e:
            logger.error(f"Error in heartbeat listener: {e}")
        finally:
            pubsub.close()
    
    async def _listen_for_compliance_reports(self):
        """Listen for compliance report messages"""
        if not self.redis_client:
            return
        
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("haivemind:compliance:reports")
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        report_data = json.loads(message['data'])
                        agent_id = report_data.get('agent_id')
                        machine_id = report_data.get('machine_id')
                        
                        if machine_id in self.active_agents and agent_id in self.active_agents[machine_id]:
                            # Update agent compliance data
                            agent_info = self.active_agents[machine_id][agent_id]
                            agent_info.update({
                                'compliance_score': report_data.get('compliance_score', 1.0),
                                'total_operations': report_data.get('total_operations', 0),
                                'violations_count': report_data.get('violations_count', 0),
                                'last_report': datetime.now().isoformat()
                            })
                        
                    except Exception as e:
                        logger.error(f"Error processing compliance report: {e}")
        except Exception as e:
            logger.error(f"Error in compliance report listener: {e}")
        finally:
            pubsub.close()
    
    async def _listen_for_governance_events(self):
        """Listen for general governance events"""
        if not self.redis_client:
            return
        
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("haivemind:governance:events")
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        event_data = json.loads(message['data'])
                        event_type = event_data.get('type')
                        
                        if event_type == 'policy_change':
                            # Handle policy changes from other governance nodes
                            logger.info(f"Received policy change event: {event_data}")
                        elif event_type == 'emergency_alert':
                            # Handle emergency alerts
                            logger.critical(f"Emergency alert received: {event_data}")
                        
                    except Exception as e:
                        logger.error(f"Error processing governance event: {e}")
        except Exception as e:
            logger.error(f"Error in governance event listener: {e}")
        finally:
            pubsub.close()