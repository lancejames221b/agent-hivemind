#!/usr/bin/env python3
"""
hAIveMind Agent Rules Integration - Real-time Rule Application and Compliance
Integrates rules engine with agent operations for consistent behavior enforcement
across the hAIveMind network with performance optimization and compliance monitoring.

Author: Lance James, Unit 221B Inc
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import threading
from functools import wraps

from .rules_engine import RulesEngine, Rule, RuleType, RuleScope
from .rules_database import RulesDatabase
from .rules_haivemind_integration import RulesHAIveMindIntegration
from .rule_management_service import RuleManagementService

logger = logging.getLogger(__name__)

class ComplianceLevel(Enum):
    """Agent compliance levels"""
    STRICT = "strict"           # All rules must be followed
    LENIENT = "lenient"         # Minor violations allowed
    ADVISORY = "advisory"       # Rules are suggestions only
    DISABLED = "disabled"       # Rules checking disabled

class RuleViolationType(Enum):
    """Types of rule violations"""
    BLOCKING = "blocking"       # Operation must be blocked
    WARNING = "warning"         # Log warning but allow
    ADVISORY = "advisory"       # Informational only
    PERFORMANCE = "performance" # Performance impact detected

@dataclass
class RuleEvaluationResult:
    """Result of rule evaluation for an agent operation"""
    operation_id: str
    agent_id: str
    machine_id: str
    context: Dict[str, Any]
    applicable_rules: List[str]
    configuration: Dict[str, Any]
    violations: List[Dict[str, Any]]
    compliance_score: float
    evaluation_time_ms: int
    recommendations: List[str]
    should_block: bool
    timestamp: datetime

@dataclass
class AgentBehaviorProfile:
    """Profile of agent behavior and rule compliance"""
    agent_id: str
    machine_id: str
    compliance_level: ComplianceLevel
    total_operations: int
    compliant_operations: int
    violations_count: int
    avg_compliance_score: float
    last_evaluation: datetime
    performance_metrics: Dict[str, float]
    rule_preferences: Dict[str, Any]

@dataclass
class RuleViolation:
    """Represents a rule violation"""
    violation_id: str
    rule_id: str
    agent_id: str
    machine_id: str
    violation_type: RuleViolationType
    operation_context: Dict[str, Any]
    violation_details: Dict[str, Any]
    severity: str
    timestamp: datetime
    resolved: bool = False

class AgentRulesIntegration:
    """Integration service for applying rules to agent operations"""
    
    def __init__(self, config: Dict[str, Any], memory_storage=None):
        self.config = config
        self.memory_storage = memory_storage
        self.machine_id = self._get_machine_id()
        
        # Initialize rules components
        rules_db_path = config.get('rules', {}).get('database_path', 'data/rules.db')
        self.rules_db = RulesDatabase(
            rules_db_path,
            getattr(memory_storage, 'chroma_client', None),
            getattr(memory_storage, 'redis_client', None)
        )
        
        self.rules_engine = RulesEngine(
            rules_db_path,
            getattr(memory_storage, 'chroma_client', None),
            getattr(memory_storage, 'redis_client', None),
            config
        )
        
        self.rule_service = RuleManagementService(
            rules_db_path,
            getattr(memory_storage, 'chroma_client', None),
            getattr(memory_storage, 'redis_client', None)
        )
        
        self.haivemind_integration = RulesHAIveMindIntegration(
            self.rule_service,
            memory_storage,
            getattr(memory_storage, 'redis_client', None)
        )
        
        # Agent tracking
        self.agent_profiles: Dict[str, AgentBehaviorProfile] = {}
        self.active_violations: Dict[str, RuleViolation] = {}
        self.evaluation_cache: Dict[str, RuleEvaluationResult] = {}
        
        # Performance optimization
        self.cache_ttl = config.get('rules', {}).get('performance', {}).get('cache_ttl', 300)
        self.enable_caching = config.get('rules', {}).get('performance', {}).get('enable_optimization', True)
        self.max_cache_size = config.get('rules', {}).get('performance', {}).get('cache_size', 1000)
        
        # Background tasks
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
    
    def _start_background_tasks(self):
        """Start background tasks for maintenance and optimization"""
        # Start cache cleanup task
        threading.Thread(target=self._cache_cleanup_worker, daemon=True).start()
        
        # Start compliance monitoring task
        threading.Thread(target=self._compliance_monitoring_worker, daemon=True).start()
        
        # Start performance optimization task
        threading.Thread(target=self._performance_optimization_worker, daemon=True).start()
    
    def evaluate_operation_rules(self, agent_id: str, operation_type: str, 
                                context: Dict[str, Any]) -> RuleEvaluationResult:
        """Evaluate rules for an agent operation"""
        start_time = time.time()
        operation_id = str(uuid.uuid4())
        
        try:
            # Check cache first if enabled
            if self.enable_caching:
                cache_key = self._generate_cache_key(agent_id, operation_type, context)
                cached_result = self.evaluation_cache.get(cache_key)
                if cached_result and self._is_cache_valid(cached_result):
                    logger.debug(f"Using cached rule evaluation for {agent_id}")
                    return cached_result
            
            # Build evaluation context
            evaluation_context = {
                'agent_id': agent_id,
                'machine_id': self.machine_id,
                'operation_type': operation_type,
                'project_id': context.get('project_id'),
                'task_type': context.get('task_type'),
                'user_id': context.get('user_id'),
                'timestamp': datetime.now().isoformat(),
                **context
            }
            
            # Evaluate rules
            rules_result = self.rules_engine.evaluate_rules(evaluation_context)
            
            # Analyze violations and compliance
            violations = self._analyze_violations(rules_result, evaluation_context)
            compliance_score = self._calculate_compliance_score(violations)
            should_block = any(v['type'] == RuleViolationType.BLOCKING.value for v in violations)
            
            # Generate recommendations
            recommendations = self._generate_operation_recommendations(
                rules_result, violations, evaluation_context
            )
            
            # Create evaluation result
            evaluation_time = int((time.time() - start_time) * 1000)
            result = RuleEvaluationResult(
                operation_id=operation_id,
                agent_id=agent_id,
                machine_id=self.machine_id,
                context=evaluation_context,
                applicable_rules=rules_result.get('applied_rules', []),
                configuration=rules_result.get('configuration', {}),
                violations=violations,
                compliance_score=compliance_score,
                evaluation_time_ms=evaluation_time,
                recommendations=recommendations,
                should_block=should_block,
                timestamp=datetime.now()
            )
            
            # Cache result if enabled
            if self.enable_caching:
                self._cache_evaluation_result(cache_key, result)
            
            # Update agent profile
            self._update_agent_profile(agent_id, result)
            
            # Store evaluation in hAIveMind memory
            if self.memory_storage:
                self._store_evaluation_memory(result)
            
            # Handle violations
            if violations:
                self._handle_rule_violations(result)
            
            logger.debug(f"Rule evaluation completed for {agent_id}: {compliance_score:.2f} compliance")
            return result
            
        except Exception as e:
            logger.error(f"Rule evaluation failed for {agent_id}: {e}")
            # Return safe default result
            return RuleEvaluationResult(
                operation_id=operation_id,
                agent_id=agent_id,
                machine_id=self.machine_id,
                context=context,
                applicable_rules=[],
                configuration={},
                violations=[],
                compliance_score=1.0,
                evaluation_time_ms=int((time.time() - start_time) * 1000),
                recommendations=[],
                should_block=False,
                timestamp=datetime.now()
            )
    
    def apply_rules_to_operation(self, agent_id: str, operation_type: str, 
                                operation_data: Dict[str, Any], 
                                context: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """Apply rules to modify operation data and determine if operation should proceed"""
        
        # Evaluate rules for this operation
        evaluation = self.evaluate_operation_rules(agent_id, operation_type, context)
        
        # Apply rule configuration to operation data
        modified_data = operation_data.copy()
        configuration = evaluation.configuration
        
        # Apply authorship rules
        if 'author' in configuration:
            modified_data['author'] = configuration['author']
        if 'organization' in configuration:
            modified_data['organization'] = configuration['organization']
        if 'disable_ai_attribution' in configuration:
            modified_data['disable_ai_attribution'] = configuration['disable_ai_attribution']
        
        # Apply coding style rules
        if 'add_comments' in configuration:
            modified_data['add_comments'] = configuration['add_comments']
        if 'response_style' in configuration:
            modified_data['response_style'] = configuration['response_style']
        if 'use_emojis' in configuration:
            modified_data['use_emojis'] = configuration['use_emojis']
        
        # Apply security rules
        if 'validate_content' in configuration:
            # Apply content validation rules
            validation_rules = configuration['validate_content']
            if isinstance(validation_rules, dict):
                for rule_type, rule_value in validation_rules.items():
                    if rule_type == 'no_secrets' and rule_value:
                        # Check for secrets in content
                        if self._contains_secrets(modified_data):
                            evaluation.should_block = True
                            evaluation.violations.append({
                                'rule_id': 'sec-001',
                                'type': RuleViolationType.BLOCKING.value,
                                'message': 'Content contains potential secrets',
                                'severity': 'critical'
                            })
        
        # Apply operational rules
        for key, value in configuration.items():
            if key.startswith('operational_'):
                setting_name = key.replace('operational_', '')
                modified_data[setting_name] = value
        
        return modified_data, not evaluation.should_block
    
    def check_compliance(self, agent_id: str) -> AgentBehaviorProfile:
        """Check overall compliance for an agent"""
        if agent_id not in self.agent_profiles:
            self.agent_profiles[agent_id] = AgentBehaviorProfile(
                agent_id=agent_id,
                machine_id=self.machine_id,
                compliance_level=ComplianceLevel.STRICT,
                total_operations=0,
                compliant_operations=0,
                violations_count=0,
                avg_compliance_score=1.0,
                last_evaluation=datetime.now(),
                performance_metrics={},
                rule_preferences={}
            )
        
        return self.agent_profiles[agent_id]
    
    def set_agent_compliance_level(self, agent_id: str, level: ComplianceLevel):
        """Set compliance level for an agent"""
        profile = self.check_compliance(agent_id)
        profile.compliance_level = level
        
        logger.info(f"Set compliance level for {agent_id} to {level.value}")
    
    def get_agent_violations(self, agent_id: str, days: int = 7) -> List[RuleViolation]:
        """Get recent violations for an agent"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        return [
            violation for violation in self.active_violations.values()
            if violation.agent_id == agent_id and violation.timestamp >= cutoff_date
        ]
    
    def resolve_violation(self, violation_id: str, resolved_by: str, 
                         resolution_notes: Optional[str] = None) -> bool:
        """Resolve a rule violation"""
        if violation_id not in self.active_violations:
            return False
        
        violation = self.active_violations[violation_id]
        violation.resolved = True
        
        # Store resolution in hAIveMind memory
        if self.memory_storage:
            self.memory_storage.store_memory(
                content=f"Rule violation resolved: {violation_id}",
                category="rules",
                metadata={
                    "violation_resolution": {
                        "violation_id": violation_id,
                        "rule_id": violation.rule_id,
                        "agent_id": violation.agent_id,
                        "resolved_by": resolved_by,
                        "resolution_notes": resolution_notes,
                        "resolved_at": datetime.now().isoformat()
                    },
                    "sharing_scope": "network-shared",
                    "importance": "medium",
                    "tags": ["violation", "resolution", "compliance"]
                }
            )
        
        logger.info(f"Violation {violation_id} resolved by {resolved_by}")
        return True
    
    def get_compliance_report(self, agent_id: Optional[str] = None, 
                             days: int = 30) -> Dict[str, Any]:
        """Generate compliance report for agent(s)"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        if agent_id:
            # Single agent report
            profile = self.check_compliance(agent_id)
            violations = self.get_agent_violations(agent_id, days)
            
            return {
                "agent_id": agent_id,
                "period_days": days,
                "profile": asdict(profile),
                "recent_violations": len(violations),
                "violation_types": self._analyze_violation_types(violations),
                "compliance_trend": self._calculate_compliance_trend(agent_id, days)
            }
        else:
            # Network-wide report
            all_violations = [
                v for v in self.active_violations.values()
                if v.timestamp >= cutoff_date
            ]
            
            agent_stats = {}
            for agent_id, profile in self.agent_profiles.items():
                agent_violations = [v for v in all_violations if v.agent_id == agent_id]
                agent_stats[agent_id] = {
                    "compliance_score": profile.avg_compliance_score,
                    "total_operations": profile.total_operations,
                    "violations": len(agent_violations),
                    "compliance_level": profile.compliance_level.value
                }
            
            return {
                "period_days": days,
                "total_agents": len(self.agent_profiles),
                "total_violations": len(all_violations),
                "agent_statistics": agent_stats,
                "violation_summary": self._analyze_violation_types(all_violations),
                "network_compliance_score": self._calculate_network_compliance_score()
            }
    
    def optimize_agent_rules(self, agent_id: str) -> Dict[str, Any]:
        """Optimize rules for a specific agent based on usage patterns"""
        profile = self.check_compliance(agent_id)
        
        # Analyze agent's rule usage patterns
        if self.memory_storage:
            insights = self.haivemind_integration.discover_rule_patterns(agent_id, days=30)
        else:
            insights = []
        
        optimizations = []
        
        # Performance optimizations
        if profile.performance_metrics.get('avg_evaluation_time', 0) > 100:
            optimizations.append({
                "type": "performance",
                "recommendation": "Consider caching frequently evaluated rules",
                "impact": "20-50% faster rule evaluation"
            })
        
        # Compliance optimizations
        if profile.avg_compliance_score < 0.8:
            optimizations.append({
                "type": "compliance",
                "recommendation": "Review and update rule conditions for better matching",
                "impact": "Improved compliance score"
            })
        
        # Usage-based optimizations
        if profile.total_operations > 1000:
            optimizations.append({
                "type": "efficiency",
                "recommendation": "Enable rule caching for this high-activity agent",
                "impact": "Reduced evaluation overhead"
            })
        
        return {
            "agent_id": agent_id,
            "current_performance": profile.performance_metrics,
            "optimization_recommendations": optimizations,
            "insights_analyzed": len(insights)
        }
    
    def _analyze_violations(self, rules_result: Dict[str, Any], 
                           context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze rule evaluation result for violations"""
        violations = []
        configuration = rules_result.get('configuration', {})
        
        # Check for blocking conditions
        for key, value in configuration.items():
            if isinstance(value, dict) and value.get('blocked'):
                violations.append({
                    'rule_id': key,
                    'type': RuleViolationType.BLOCKING.value,
                    'message': value.get('reason', 'Operation blocked by rule'),
                    'severity': 'high'
                })
            elif isinstance(value, dict) and 'validation' in value:
                validation = value['validation']
                if validation == 'no_secrets' and self._contains_secrets(context):
                    violations.append({
                        'rule_id': key,
                        'type': RuleViolationType.BLOCKING.value,
                        'message': 'Content contains potential secrets',
                        'severity': 'critical'
                    })
        
        return violations
    
    def _calculate_compliance_score(self, violations: List[Dict[str, Any]]) -> float:
        """Calculate compliance score based on violations"""
        if not violations:
            return 1.0
        
        # Weight violations by severity
        severity_weights = {
            'critical': 0.5,
            'high': 0.3,
            'medium': 0.15,
            'low': 0.05
        }
        
        total_penalty = 0.0
        for violation in violations:
            severity = violation.get('severity', 'medium')
            penalty = severity_weights.get(severity, 0.15)
            total_penalty += penalty
        
        # Ensure score doesn't go below 0
        return max(0.0, 1.0 - total_penalty)
    
    def _generate_operation_recommendations(self, rules_result: Dict[str, Any], 
                                          violations: List[Dict[str, Any]],
                                          context: Dict[str, Any]) -> List[str]:
        """Generate recommendations for the operation"""
        recommendations = []
        
        # Add recommendations based on violations
        for violation in violations:
            if violation['type'] == RuleViolationType.BLOCKING.value:
                recommendations.append(f"Address {violation['severity']} violation: {violation['message']}")
            elif violation['type'] == RuleViolationType.WARNING.value:
                recommendations.append(f"Consider fixing: {violation['message']}")
        
        # Add general recommendations
        configuration = rules_result.get('configuration', {})
        if 'add_comments' in configuration and not configuration['add_comments']:
            recommendations.append("Comments disabled by rule - ensure code is self-documenting")
        
        if 'response_style' in configuration and configuration['response_style'] == 'concise':
            recommendations.append("Keep responses brief and to the point")
        
        return recommendations
    
    def _update_agent_profile(self, agent_id: str, evaluation: RuleEvaluationResult):
        """Update agent behavior profile with evaluation results"""
        if agent_id not in self.agent_profiles:
            self.agent_profiles[agent_id] = AgentBehaviorProfile(
                agent_id=agent_id,
                machine_id=self.machine_id,
                compliance_level=ComplianceLevel.STRICT,
                total_operations=0,
                compliant_operations=0,
                violations_count=0,
                avg_compliance_score=1.0,
                last_evaluation=datetime.now(),
                performance_metrics={},
                rule_preferences={}
            )
        
        profile = self.agent_profiles[agent_id]
        profile.total_operations += 1
        profile.last_evaluation = evaluation.timestamp
        
        # Update compliance metrics
        if evaluation.compliance_score >= 0.8:
            profile.compliant_operations += 1
        
        if evaluation.violations:
            profile.violations_count += len(evaluation.violations)
        
        # Update average compliance score (exponential moving average)
        alpha = 0.1  # Smoothing factor
        profile.avg_compliance_score = (
            alpha * evaluation.compliance_score + 
            (1 - alpha) * profile.avg_compliance_score
        )
        
        # Update performance metrics
        if 'avg_evaluation_time' not in profile.performance_metrics:
            profile.performance_metrics['avg_evaluation_time'] = evaluation.evaluation_time_ms
        else:
            profile.performance_metrics['avg_evaluation_time'] = (
                alpha * evaluation.evaluation_time_ms +
                (1 - alpha) * profile.performance_metrics['avg_evaluation_time']
            )
    
    def _handle_rule_violations(self, evaluation: RuleEvaluationResult):
        """Handle rule violations from evaluation"""
        for violation_data in evaluation.violations:
            violation_id = str(uuid.uuid4())
            
            violation = RuleViolation(
                violation_id=violation_id,
                rule_id=violation_data.get('rule_id', 'unknown'),
                agent_id=evaluation.agent_id,
                machine_id=evaluation.machine_id,
                violation_type=RuleViolationType(violation_data.get('type', 'warning')),
                operation_context=evaluation.context,
                violation_details=violation_data,
                severity=violation_data.get('severity', 'medium'),
                timestamp=evaluation.timestamp
            )
            
            self.active_violations[violation_id] = violation
            
            # Log violation
            logger.warning(f"Rule violation detected: {violation.rule_id} for agent {violation.agent_id}")
    
    def _store_evaluation_memory(self, evaluation: RuleEvaluationResult):
        """Store rule evaluation in hAIveMind memory"""
        try:
            content = f"Rule evaluation for {evaluation.agent_id}: {evaluation.compliance_score:.2f} compliance"
            
            self.memory_storage.store_memory(
                content=content,
                category="rules",
                metadata={
                    "rule_evaluation": {
                        "operation_id": evaluation.operation_id,
                        "agent_id": evaluation.agent_id,
                        "machine_id": evaluation.machine_id,
                        "compliance_score": evaluation.compliance_score,
                        "violations_count": len(evaluation.violations),
                        "evaluation_time_ms": evaluation.evaluation_time_ms,
                        "should_block": evaluation.should_block
                    },
                    "sharing_scope": "machine-local",  # Keep evaluations local unless violations
                    "importance": "high" if evaluation.violations else "low",
                    "tags": ["evaluation", "compliance", "rules", evaluation.agent_id]
                }
            )
        except Exception as e:
            logger.error(f"Failed to store evaluation memory: {e}")
    
    def _contains_secrets(self, data: Dict[str, Any]) -> bool:
        """Check if data contains potential secrets (simplified implementation)"""
        import re
        
        # Convert data to string for pattern matching
        data_str = json.dumps(data, default=str).lower()
        
        # Common secret patterns
        secret_patterns = [
            r'password\s*[:=]\s*["\']?[^"\'\s]{8,}',
            r'api[_-]?key\s*[:=]\s*["\']?[^"\'\s]{20,}',
            r'secret\s*[:=]\s*["\']?[^"\'\s]{16,}',
            r'token\s*[:=]\s*["\']?[^"\'\s]{20,}',
            r'[a-f0-9]{32,}',  # Hex strings (potential hashes/keys)
            r'sk-[a-zA-Z0-9]{48,}',  # OpenAI API key pattern
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, data_str):
                return True
        
        return False
    
    def _generate_cache_key(self, agent_id: str, operation_type: str, 
                           context: Dict[str, Any]) -> str:
        """Generate cache key for rule evaluation"""
        # Create deterministic key from relevant context
        cache_context = {
            'agent_id': agent_id,
            'operation_type': operation_type,
            'project_id': context.get('project_id'),
            'task_type': context.get('task_type'),
            'user_id': context.get('user_id')
        }
        
        import hashlib
        key_str = json.dumps(cache_context, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _is_cache_valid(self, cached_result: RuleEvaluationResult) -> bool:
        """Check if cached result is still valid"""
        age = datetime.now() - cached_result.timestamp
        return age.total_seconds() < self.cache_ttl
    
    def _cache_evaluation_result(self, cache_key: str, result: RuleEvaluationResult):
        """Cache evaluation result with size management"""
        if len(self.evaluation_cache) >= self.max_cache_size:
            # Remove oldest entries
            oldest_keys = sorted(
                self.evaluation_cache.keys(),
                key=lambda k: self.evaluation_cache[k].timestamp
            )[:self.max_cache_size // 4]  # Remove 25% of cache
            
            for key in oldest_keys:
                del self.evaluation_cache[key]
        
        self.evaluation_cache[cache_key] = result
    
    def _cache_cleanup_worker(self):
        """Background worker to clean up expired cache entries"""
        while True:
            try:
                time.sleep(300)  # Run every 5 minutes
                
                current_time = datetime.now()
                expired_keys = []
                
                for key, result in self.evaluation_cache.items():
                    age = current_time - result.timestamp
                    if age.total_seconds() > self.cache_ttl:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.evaluation_cache[key]
                
                if expired_keys:
                    logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                    
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    def _compliance_monitoring_worker(self):
        """Background worker to monitor compliance and generate alerts"""
        while True:
            try:
                time.sleep(1800)  # Run every 30 minutes
                
                # Check for agents with low compliance
                low_compliance_agents = []
                for agent_id, profile in self.agent_profiles.items():
                    if profile.avg_compliance_score < 0.7:
                        low_compliance_agents.append(agent_id)
                
                if low_compliance_agents:
                    logger.warning(f"Low compliance detected for agents: {low_compliance_agents}")
                    
                    # Store alert in hAIveMind memory
                    if self.memory_storage:
                        self.memory_storage.store_memory(
                            content=f"Low compliance alert: {len(low_compliance_agents)} agents below threshold",
                            category="rules",
                            metadata={
                                "compliance_alert": {
                                    "type": "low_compliance",
                                    "affected_agents": low_compliance_agents,
                                    "threshold": 0.7,
                                    "timestamp": datetime.now().isoformat()
                                },
                                "sharing_scope": "network-shared",
                                "importance": "high",
                                "tags": ["alert", "compliance", "monitoring"]
                            }
                        )
                
            except Exception as e:
                logger.error(f"Compliance monitoring error: {e}")
    
    def _performance_optimization_worker(self):
        """Background worker to optimize performance based on usage patterns"""
        while True:
            try:
                time.sleep(3600)  # Run every hour
                
                # Analyze performance metrics
                slow_agents = []
                for agent_id, profile in self.agent_profiles.items():
                    avg_time = profile.performance_metrics.get('avg_evaluation_time', 0)
                    if avg_time > 200:  # More than 200ms average
                        slow_agents.append((agent_id, avg_time))
                
                if slow_agents:
                    logger.info(f"Performance optimization opportunities for {len(slow_agents)} agents")
                    
                    # Enable caching for slow agents
                    for agent_id, avg_time in slow_agents:
                        profile = self.agent_profiles[agent_id]
                        if 'caching_enabled' not in profile.rule_preferences:
                            profile.rule_preferences['caching_enabled'] = True
                            logger.info(f"Enabled caching for slow agent {agent_id} (avg: {avg_time:.1f}ms)")
                
            except Exception as e:
                logger.error(f"Performance optimization error: {e}")
    
    def _analyze_violation_types(self, violations: List[RuleViolation]) -> Dict[str, int]:
        """Analyze violation types and return counts"""
        type_counts = {}
        for violation in violations:
            violation_type = violation.violation_type.value
            type_counts[violation_type] = type_counts.get(violation_type, 0) + 1
        
        return type_counts
    
    def _calculate_compliance_trend(self, agent_id: str, days: int) -> Dict[str, float]:
        """Calculate compliance trend for an agent"""
        # This would typically analyze historical data
        # For now, return current metrics
        profile = self.check_compliance(agent_id)
        
        return {
            "current_score": profile.avg_compliance_score,
            "trend": "stable",  # Would calculate from historical data
            "improvement_rate": 0.0
        }
    
    def _calculate_network_compliance_score(self) -> float:
        """Calculate overall network compliance score"""
        if not self.agent_profiles:
            return 1.0
        
        total_score = sum(profile.avg_compliance_score for profile in self.agent_profiles.values())
        return total_score / len(self.agent_profiles)

# Decorator for automatic rule application
def apply_rules(operation_type: str, context_extractor: Optional[Callable] = None):
    """Decorator to automatically apply rules to function calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract agent_id and context
            agent_id = kwargs.get('agent_id', 'unknown')
            
            if context_extractor:
                context = context_extractor(*args, **kwargs)
            else:
                context = {'operation': operation_type}
            
            # Get rules integration instance (would be injected in real implementation)
            rules_integration = getattr(wrapper, '_rules_integration', None)
            if not rules_integration:
                # No rules integration available, proceed normally
                return func(*args, **kwargs)
            
            # Evaluate rules
            evaluation = rules_integration.evaluate_operation_rules(agent_id, operation_type, context)
            
            # Block operation if required
            if evaluation.should_block:
                raise RuntimeError(f"Operation blocked by rules: {evaluation.violations}")
            
            # Apply rule modifications to kwargs
            if 'operation_data' in kwargs:
                modified_data, should_proceed = rules_integration.apply_rules_to_operation(
                    agent_id, operation_type, kwargs['operation_data'], context
                )
                if not should_proceed:
                    raise RuntimeError("Operation blocked by rules")
                kwargs['operation_data'] = modified_data
            
            # Execute function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator