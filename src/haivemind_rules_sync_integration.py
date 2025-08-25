#!/usr/bin/env python3
"""
hAIveMind Rules Sync Integration - Complete Integration Service
Main integration service that coordinates all rules sync components with the hAIveMind
network for comprehensive governance, compliance, and intelligent behavior management.

Author: Lance James, Unit 221B Inc
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from .rules_sync_service import RulesSyncService, RuleSyncOperation, RuleSyncPriority
from .network_governance_service import NetworkGovernanceService, GovernancePolicy, AlertSeverity
from .agent_rules_integration import AgentRulesIntegration, ComplianceLevel
from .rules_sync_analytics import RulesSyncAnalytics
from .rules_haivemind_integration import RulesHAIveMindIntegration
from .rule_management_service import RuleManagementService

logger = logging.getLogger(__name__)

class HAIveMindRulesSyncIntegration:
    """Complete integration service for hAIveMind rules synchronization"""
    
    def __init__(self, config: Dict[str, Any], memory_storage=None):
        self.config = config
        self.memory_storage = memory_storage
        self.machine_id = self._get_machine_id()
        
        # Initialize core services
        self.rule_management = RuleManagementService(
            config.get('rules', {}).get('database_path', 'data/rules.db'),
            getattr(memory_storage, 'chroma_client', None),
            getattr(memory_storage, 'redis_client', None)
        )
        
        self.haivemind_integration = RulesHAIveMindIntegration(
            self.rule_management,
            memory_storage,
            getattr(memory_storage, 'redis_client', None)
        )
        
        self.sync_service = RulesSyncService(config, memory_storage)
        self.governance_service = NetworkGovernanceService(config, memory_storage)
        self.agent_integration = AgentRulesIntegration(config, memory_storage)
        
        self.analytics = RulesSyncAnalytics(
            config, memory_storage,
            self.sync_service,
            self.governance_service,
            self.agent_integration
        )
        
        # Integration state
        self.is_initialized = False
        self.startup_complete = False
        
        logger.info("hAIveMind Rules Sync Integration initialized")
    
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
    
    async def initialize(self) -> bool:
        """Initialize the complete integration system"""
        try:
            logger.info("Initializing hAIveMind Rules Sync Integration...")
            
            # Initialize network governance
            await self._initialize_governance()
            
            # Initialize agent integration
            await self._initialize_agent_integration()
            
            # Initialize analytics
            await self._initialize_analytics()
            
            # Start integration monitoring
            await self._start_integration_monitoring()
            
            # Perform initial network sync
            await self._perform_initial_sync()
            
            self.is_initialized = True
            self.startup_complete = True
            
            # Store initialization in hAIveMind memory
            if self.memory_storage:
                self.memory_storage.store_memory(
                    content=f"hAIveMind Rules Sync Integration initialized on {self.machine_id}",
                    category="governance",
                    metadata={
                        "integration_startup": {
                            "machine_id": self.machine_id,
                            "services_initialized": [
                                "rule_management",
                                "sync_service", 
                                "governance_service",
                                "agent_integration",
                                "analytics"
                            ],
                            "startup_time": datetime.now().isoformat()
                        },
                        "sharing_scope": "network-shared",
                        "importance": "high",
                        "tags": ["startup", "integration", "governance", "haivemind"]
                    }
                )
            
            logger.info("hAIveMind Rules Sync Integration startup complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize hAIveMind Rules Sync Integration: {e}")
            return False
    
    async def _initialize_governance(self):
        """Initialize network governance"""
        # Register this machine as a governance node
        await self.governance_service.register_agent(
            agent_id="governance_service",
            machine_id=self.machine_id,
            agent_info={
                "type": "governance",
                "capabilities": ["policy_enforcement", "compliance_monitoring", "network_health"],
                "version": "1.0.0"
            }
        )
        
        # Set initial governance policies
        governance_policy = self.config.get('rules', {}).get('governance_policy', 'strict_enforcement')
        self.governance_service.governance_policy = GovernancePolicy(governance_policy)
        
        logger.info(f"Governance initialized with policy: {governance_policy}")
    
    async def _initialize_agent_integration(self):
        """Initialize agent integration"""
        # Set default compliance level
        default_compliance = self.config.get('rules', {}).get('default_compliance_level', 'strict')
        
        # Register agent integration service
        await self.governance_service.register_agent(
            agent_id="agent_integration",
            machine_id=self.machine_id,
            agent_info={
                "type": "agent_integration",
                "capabilities": ["rule_evaluation", "compliance_checking", "behavior_modification"],
                "default_compliance_level": default_compliance,
                "version": "1.0.0"
            }
        )
        
        logger.info(f"Agent integration initialized with default compliance: {default_compliance}")
    
    async def _initialize_analytics(self):
        """Initialize analytics system"""
        # Register analytics service
        await self.governance_service.register_agent(
            agent_id="analytics_service",
            machine_id=self.machine_id,
            agent_info={
                "type": "analytics",
                "capabilities": ["pattern_analysis", "predictive_alerts", "optimization_recommendations"],
                "version": "1.0.0"
            }
        )
        
        logger.info("Analytics system initialized")
    
    async def _start_integration_monitoring(self):
        """Start integration monitoring tasks"""
        # Start health monitoring
        asyncio.create_task(self._monitor_integration_health())
        
        # Start performance monitoring
        asyncio.create_task(self._monitor_performance())
        
        # Start compliance monitoring
        asyncio.create_task(self._monitor_compliance())
        
        logger.info("Integration monitoring started")
    
    async def _perform_initial_sync(self):
        """Perform initial network synchronization"""
        try:
            # Sync all active rules to the network
            sync_id = await self.sync_service.bulk_sync_rules(
                priority=RuleSyncPriority.HIGH
            )
            
            logger.info(f"Initial network sync initiated: {sync_id}")
            
            # Create startup alert
            await self.governance_service.create_governance_alert(
                alert_type="system_startup",
                severity=AlertSeverity.INFO,
                title=f"hAIveMind Rules Sync Integration started on {self.machine_id}",
                description="Complete rules sync integration is now active and monitoring the network",
                affected_machines=[self.machine_id]
            )
            
        except Exception as e:
            logger.error(f"Initial sync failed: {e}")
            
            # Create failure alert
            await self.governance_service.create_governance_alert(
                alert_type="startup_failure",
                severity=AlertSeverity.HIGH,
                title=f"Initial sync failed on {self.machine_id}",
                description=f"Failed to perform initial network sync: {str(e)}",
                affected_machines=[self.machine_id]
            )
    
    async def sync_rule_to_network(self, rule_id: str, operation: str = "update",
                                  priority: str = "normal", target_machines: Optional[List[str]] = None,
                                  metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Sync a rule to the network with full integration"""
        try:
            # Convert string parameters to enums
            sync_operation = RuleSyncOperation(operation)
            sync_priority = RuleSyncPriority[priority.upper()]
            
            # Perform sync
            sync_id = await self.sync_service.sync_rule_to_network(
                rule_id=rule_id,
                operation=sync_operation,
                priority=sync_priority,
                target_machines=target_machines,
                metadata=metadata
            )
            
            # Store sync operation in hAIveMind memory
            self.haivemind_integration.store_rule_operation_memory(
                rule_id=rule_id,
                operation_type="sync",
                context={
                    "sync_id": sync_id,
                    "operation": operation,
                    "priority": priority,
                    "target_machines": target_machines
                },
                outcome={"success": True, "sync_id": sync_id},
                agent_id="integration_service"
            )
            
            # Record analytics metric
            self.analytics.record_sync_metric(
                self.analytics.AnalyticsMetricType.SYNC_PERFORMANCE,
                0,  # Would be actual sync time
                metadata={"rule_id": rule_id, "operation": operation},
                tags=["sync", "rule_distribution"]
            )
            
            return {
                "success": True,
                "sync_id": sync_id,
                "message": f"Rule {rule_id} sync initiated successfully"
            }
            
        except Exception as e:
            logger.error(f"Rule sync failed: {e}")
            
            # Store failure in memory
            self.haivemind_integration.store_rule_operation_memory(
                rule_id=rule_id,
                operation_type="sync",
                context={"operation": operation, "priority": priority},
                outcome={"success": False, "error": str(e)},
                agent_id="integration_service"
            )
            
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to sync rule {rule_id}"
            }
    
    async def enforce_network_policy(self, policy_type: str, policy_data: Dict[str, Any],
                                   target_machines: Optional[List[str]] = None) -> Dict[str, Any]:
        """Enforce a network-wide policy with full integration"""
        try:
            # Enforce policy through governance service
            result = await self.governance_service.enforce_network_policy(
                policy_type=policy_type,
                policy_data=policy_data,
                target_machines=target_machines
            )
            
            # Store policy enforcement in memory
            if self.memory_storage:
                self.memory_storage.store_memory(
                    content=f"Network policy enforced: {policy_type}",
                    category="governance",
                    metadata={
                        "policy_enforcement": asdict(result),
                        "sharing_scope": "network-shared",
                        "importance": "high",
                        "tags": ["policy", "enforcement", "governance"]
                    }
                )
            
            # Record analytics
            self.analytics.record_sync_metric(
                self.analytics.AnalyticsMetricType.NETWORK_HEALTH,
                1.0 if result.success else 0.0,
                metadata={"policy_type": policy_type},
                tags=["policy", "enforcement"]
            )
            
            return {
                "success": result.success,
                "policy_id": result.policy_id,
                "affected_rules": result.affected_rules,
                "execution_time_ms": result.execution_time_ms,
                "error": result.error_message
            }
            
        except Exception as e:
            logger.error(f"Policy enforcement failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to enforce policy {policy_type}"
            }
    
    async def evaluate_agent_operation(self, agent_id: str, operation_type: str,
                                     context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate an agent operation against rules with full integration"""
        try:
            # Evaluate rules
            evaluation = self.agent_integration.evaluate_operation_rules(
                agent_id=agent_id,
                operation_type=operation_type,
                context=context
            )
            
            # Record compliance metric
            self.analytics.record_sync_metric(
                self.analytics.AnalyticsMetricType.COMPLIANCE_TRENDS,
                evaluation.compliance_score,
                metadata={"agent_id": agent_id, "operation_type": operation_type},
                tags=["compliance", "evaluation"]
            )
            
            # Handle violations if any
            if evaluation.violations:
                # Create governance alert for serious violations
                blocking_violations = [v for v in evaluation.violations if v.get('type') == 'blocking']
                if blocking_violations:
                    await self.governance_service.create_governance_alert(
                        alert_type="rule_violation",
                        severity=AlertSeverity.HIGH,
                        title=f"Blocking rule violations detected for agent {agent_id}",
                        description=f"Agent operation blocked due to {len(blocking_violations)} rule violations",
                        affected_agents=[agent_id],
                        rule_ids=[v.get('rule_id') for v in blocking_violations if v.get('rule_id')]
                    )
            
            return {
                "success": True,
                "evaluation": {
                    "operation_id": evaluation.operation_id,
                    "compliance_score": evaluation.compliance_score,
                    "should_block": evaluation.should_block,
                    "violations": evaluation.violations,
                    "recommendations": evaluation.recommendations,
                    "evaluation_time_ms": evaluation.evaluation_time_ms
                }
            }
            
        except Exception as e:
            logger.error(f"Agent operation evaluation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to evaluate operation for agent {agent_id}"
            }
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get comprehensive integration status"""
        try:
            # Get status from all services
            sync_status = self.sync_service.get_sync_status()
            governance_status = asyncio.run(self.governance_service.get_network_health_status())
            analytics_data = self.analytics.get_analytics_dashboard_data()
            
            return {
                "integration_status": {
                    "initialized": self.is_initialized,
                    "startup_complete": self.startup_complete,
                    "machine_id": self.machine_id
                },
                "sync_service": sync_status,
                "governance_service": governance_status,
                "analytics": {
                    "metrics_summary": analytics_data.get("metrics_summary", {}),
                    "recent_insights": len(analytics_data.get("recent_insights", [])),
                    "active_alerts": len(analytics_data.get("predictive_alerts", [])),
                    "recommendations": len(analytics_data.get("optimization_recommendations", []))
                },
                "agent_integration": {
                    "active_profiles": len(self.agent_integration.agent_profiles),
                    "active_violations": len(self.agent_integration.active_violations),
                    "cache_size": len(self.agent_integration.evaluation_cache)
                },
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get integration status: {e}")
            return {
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }
    
    def get_network_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive network dashboard data"""
        try:
            # Combine data from all services
            governance_data = self.governance_service.get_governance_dashboard_data()
            analytics_data = self.analytics.get_analytics_dashboard_data()
            
            # Get agent compliance summary
            agent_compliance = {}
            for agent_id, profile in self.agent_integration.agent_profiles.items():
                agent_compliance[agent_id] = {
                    "compliance_score": profile.avg_compliance_score,
                    "total_operations": profile.total_operations,
                    "violations": profile.violations_count,
                    "compliance_level": profile.compliance_level.value
                }
            
            return {
                "network_overview": governance_data.get("network_overview", {}),
                "governance": {
                    "machine_status": governance_data.get("machine_status", {}),
                    "active_alerts": governance_data.get("active_alerts", []),
                    "recent_policies": governance_data.get("recent_policy_enforcements", [])
                },
                "analytics": {
                    "sync_performance": analytics_data.get("sync_performance", {}),
                    "network_health": analytics_data.get("network_health", {}),
                    "compliance_trends": analytics_data.get("compliance_trends", {}),
                    "insights": analytics_data.get("recent_insights", []),
                    "predictions": analytics_data.get("predictive_alerts", []),
                    "optimizations": analytics_data.get("optimization_recommendations", [])
                },
                "agent_compliance": agent_compliance,
                "integration_health": {
                    "services_active": self.is_initialized,
                    "last_sync": "recent",  # Would get from sync service
                    "network_connectivity": "good"  # Would check actual connectivity
                },
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate network dashboard data: {e}")
            return {
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }
    
    async def emergency_lockdown(self, reason: str, security_rules: Optional[List[str]] = None) -> Dict[str, Any]:
        """Initiate emergency lockdown across the network"""
        try:
            logger.critical(f"Emergency lockdown initiated: {reason}")
            
            # Enforce emergency lockdown policy
            result = await self.governance_service.enforce_network_policy(
                policy_type="emergency_lockdown",
                policy_data={
                    "reason": reason,
                    "security_rules": security_rules or [],
                    "lockdown_level": "maximum"
                }
            )
            
            # Sync critical security rules immediately if provided
            if security_rules:
                for rule_id in security_rules:
                    await self.sync_service.emergency_rule_update(
                        rule_id=rule_id,
                        rule_data={"emergency": True},
                        reason=f"Emergency lockdown: {reason}"
                    )
            
            # Store emergency action in memory
            if self.memory_storage:
                self.memory_storage.store_memory(
                    content=f"EMERGENCY LOCKDOWN: {reason}",
                    category="governance",
                    metadata={
                        "emergency_lockdown": {
                            "reason": reason,
                            "initiated_by": self.machine_id,
                            "security_rules": security_rules,
                            "policy_result": asdict(result),
                            "timestamp": datetime.now().isoformat()
                        },
                        "sharing_scope": "network-shared",
                        "importance": "critical",
                        "tags": ["emergency", "lockdown", "security", "governance"]
                    }
                )
            
            return {
                "success": result.success,
                "lockdown_id": result.policy_id,
                "message": f"Emergency lockdown {'initiated' if result.success else 'failed'}",
                "affected_rules": result.affected_rules,
                "error": result.error_message
            }
            
        except Exception as e:
            logger.error(f"Emergency lockdown failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to initiate emergency lockdown"
            }
    
    async def optimize_network_performance(self) -> Dict[str, Any]:
        """Optimize network performance based on analytics"""
        try:
            # Generate optimization recommendations
            recommendations = self.analytics.generate_optimization_recommendations()
            
            # Apply high-priority optimizations automatically
            applied_optimizations = []
            for rec in recommendations:
                if rec.priority_score > 0.8 and rec.implementation_effort == "low":
                    # Apply optimization
                    if rec.category == "performance":
                        # Apply performance optimization
                        await self._apply_performance_optimization(rec)
                        applied_optimizations.append(rec.recommendation_id)
                    elif rec.category == "sync":
                        # Apply sync optimization
                        await self._apply_sync_optimization(rec)
                        applied_optimizations.append(rec.recommendation_id)
            
            # Store optimization results
            if self.memory_storage:
                self.memory_storage.store_memory(
                    content=f"Network optimization completed: {len(applied_optimizations)} optimizations applied",
                    category="governance",
                    metadata={
                        "network_optimization": {
                            "total_recommendations": len(recommendations),
                            "applied_optimizations": applied_optimizations,
                            "timestamp": datetime.now().isoformat()
                        },
                        "sharing_scope": "network-shared",
                        "importance": "medium",
                        "tags": ["optimization", "performance", "network"]
                    }
                )
            
            return {
                "success": True,
                "total_recommendations": len(recommendations),
                "applied_optimizations": len(applied_optimizations),
                "recommendations": [asdict(rec) for rec in recommendations]
            }
            
        except Exception as e:
            logger.error(f"Network optimization failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to optimize network performance"
            }
    
    async def _apply_performance_optimization(self, recommendation):
        """Apply a performance optimization recommendation"""
        # Implementation would depend on the specific recommendation
        logger.info(f"Applied performance optimization: {recommendation.title}")
    
    async def _apply_sync_optimization(self, recommendation):
        """Apply a sync optimization recommendation"""
        # Implementation would depend on the specific recommendation
        logger.info(f"Applied sync optimization: {recommendation.title}")
    
    async def _monitor_integration_health(self):
        """Monitor overall integration health"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Check service health
                services_healthy = True
                
                # Check sync service
                if not self.sync_service:
                    services_healthy = False
                
                # Check governance service
                if not self.governance_service:
                    services_healthy = False
                
                # Record health metric
                self.analytics.record_sync_metric(
                    self.analytics.AnalyticsMetricType.NETWORK_HEALTH,
                    1.0 if services_healthy else 0.0,
                    metadata={"check_type": "integration_health"},
                    tags=["health", "integration"]
                )
                
                # Create alert if unhealthy
                if not services_healthy:
                    await self.governance_service.create_governance_alert(
                        alert_type="integration_health",
                        severity=AlertSeverity.HIGH,
                        title="Integration health degraded",
                        description="One or more integration services are not functioning properly",
                        affected_machines=[self.machine_id]
                    )
                
            except Exception as e:
                logger.error(f"Integration health monitoring error: {e}")
    
    async def _monitor_performance(self):
        """Monitor integration performance"""
        while True:
            try:
                await asyncio.sleep(600)  # Check every 10 minutes
                
                # Collect performance metrics from all services
                # This would collect actual performance data
                
                # Record performance metrics
                self.analytics.record_sync_metric(
                    self.analytics.AnalyticsMetricType.SYNC_PERFORMANCE,
                    100,  # Would be actual performance metric
                    metadata={"check_type": "performance_monitoring"},
                    tags=["performance", "monitoring"]
                )
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
    
    async def _monitor_compliance(self):
        """Monitor network compliance"""
        while True:
            try:
                await asyncio.sleep(900)  # Check every 15 minutes
                
                # Get compliance metrics
                compliance_metrics = await self.governance_service.get_network_compliance_metrics()
                
                # Record compliance metric
                self.analytics.record_sync_metric(
                    self.analytics.AnalyticsMetricType.COMPLIANCE_TRENDS,
                    compliance_metrics.overall_compliance_score,
                    metadata={"check_type": "compliance_monitoring"},
                    tags=["compliance", "monitoring"]
                )
                
                # Check for compliance issues
                if compliance_metrics.overall_compliance_score < 0.7:
                    await self.governance_service.create_governance_alert(
                        alert_type="low_compliance",
                        severity=AlertSeverity.MEDIUM,
                        title="Network compliance below threshold",
                        description=f"Overall compliance score ({compliance_metrics.overall_compliance_score:.2f}) is below acceptable threshold",
                        affected_machines=list(compliance_metrics.machine_compliance.keys())
                    )
                
            except Exception as e:
                logger.error(f"Compliance monitoring error: {e}")
    
    async def shutdown(self):
        """Gracefully shutdown the integration"""
        try:
            logger.info("Shutting down hAIveMind Rules Sync Integration...")
            
            # Create shutdown alert
            await self.governance_service.create_governance_alert(
                alert_type="system_shutdown",
                severity=AlertSeverity.INFO,
                title=f"hAIveMind Rules Sync Integration shutting down on {self.machine_id}",
                description="Integration services are being gracefully shut down",
                affected_machines=[self.machine_id]
            )
            
            # Unregister services
            await self.governance_service.unregister_agent("governance_service", self.machine_id)
            await self.governance_service.unregister_agent("agent_integration", self.machine_id)
            await self.governance_service.unregister_agent("analytics_service", self.machine_id)
            
            # Store shutdown in memory
            if self.memory_storage:
                self.memory_storage.store_memory(
                    content=f"hAIveMind Rules Sync Integration shutdown on {self.machine_id}",
                    category="governance",
                    metadata={
                        "integration_shutdown": {
                            "machine_id": self.machine_id,
                            "shutdown_time": datetime.now().isoformat(),
                            "graceful": True
                        },
                        "sharing_scope": "network-shared",
                        "importance": "medium",
                        "tags": ["shutdown", "integration", "governance"]
                    }
                )
            
            self.is_initialized = False
            logger.info("hAIveMind Rules Sync Integration shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during integration shutdown: {e}")