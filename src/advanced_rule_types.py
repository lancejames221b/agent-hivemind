#!/usr/bin/env python3
"""
Advanced Rule Types for hAIveMind Rules Engine
Implements conditional, cascading, time-based, and context-aware rules

Author: Lance James, Unit 221B Inc
"""

import json
import uuid
import time
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, asdict
import logging
import re
try:
    import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False
    croniter = None
from pathlib import Path

from rules_engine import Rule, RuleCondition, RuleAction, RuleType, RuleScope, RulePriority, RuleStatus

logger = logging.getLogger(__name__)

class AdvancedRuleType(Enum):
    """Advanced rule types extending base functionality"""
    CONDITIONAL = "conditional"
    CASCADING = "cascading"
    TIME_BASED = "time_based"
    CONTEXT_AWARE = "context_aware"
    COMPLIANCE = "compliance"
    SECURITY_ADAPTIVE = "security_adaptive"
    WORKFLOW_TRIGGERED = "workflow_triggered"
    PERFORMANCE_BASED = "performance_based"

class TriggerType(Enum):
    """Rule trigger mechanisms"""
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    EVENT_DRIVEN = "event_driven"
    THRESHOLD_BASED = "threshold_based"
    PATTERN_MATCHED = "pattern_matched"
    CONTEXT_CHANGED = "context_changed"

class ComplianceFramework(Enum):
    """Supported compliance frameworks"""
    GDPR = "gdpr"
    SOC2 = "soc2"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"
    NIST = "nist"
    CUSTOM = "custom"

@dataclass
class TimeBasedSchedule:
    """Time-based rule scheduling configuration"""
    cron_expression: str
    timezone: str = "UTC"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_executions: Optional[int] = None
    execution_count: int = 0

@dataclass
class ConditionalTrigger:
    """Conditional rule trigger configuration"""
    condition_expression: str  # Python expression
    required_context_fields: List[str]
    evaluation_interval: int = 60  # seconds
    cooldown_period: int = 300  # seconds
    last_triggered: Optional[datetime] = None

@dataclass
class CascadingAction:
    """Cascading rule action that triggers other rules"""
    target_rule_ids: List[str]
    trigger_delay: int = 0  # seconds
    pass_context: bool = True
    condition_override: Optional[Dict[str, Any]] = None

@dataclass
class ContextAdaptation:
    """Context-aware rule adaptation configuration"""
    adaptation_fields: List[str]
    learning_enabled: bool = True
    adaptation_threshold: float = 0.8
    historical_window: int = 86400  # seconds (24 hours)
    adaptation_rules: Dict[str, Any] = None

@dataclass
class ComplianceRule:
    """Compliance-specific rule configuration"""
    framework: ComplianceFramework
    control_id: str
    severity_level: str
    audit_required: bool = True
    documentation_required: bool = True
    evidence_collection: bool = True
    remediation_actions: List[str] = None

@dataclass
class SecurityAdaptiveRule:
    """Security-adaptive rule configuration"""
    threat_level_threshold: float = 0.5
    adaptive_response: bool = True
    escalation_rules: List[str] = None
    threat_indicators: List[str] = None
    response_actions: Dict[str, List[str]] = None

@dataclass
class AdvancedRule(Rule):
    """Extended rule with advanced capabilities"""
    advanced_type: AdvancedRuleType = AdvancedRuleType.CONDITIONAL
    trigger_type: TriggerType = TriggerType.IMMEDIATE
    schedule: Optional[TimeBasedSchedule] = None
    conditional_trigger: Optional[ConditionalTrigger] = None
    cascading_actions: List[CascadingAction] = None
    context_adaptation: Optional[ContextAdaptation] = None
    compliance_config: Optional[ComplianceRule] = None
    security_config: Optional[SecurityAdaptiveRule] = None
    performance_thresholds: Dict[str, float] = None
    execution_history: List[Dict[str, Any]] = None

class AdvancedRulesEngine:
    """Advanced rules engine with enhanced capabilities"""
    
    def __init__(self, base_engine, memory_storage, redis_client=None):
        self.base_engine = base_engine
        self.memory_storage = memory_storage
        self.redis_client = redis_client
        self.scheduled_rules = {}
        self.conditional_monitors = {}
        self.cascading_queue = asyncio.Queue()
        self.context_adapters = {}
        self.compliance_auditor = ComplianceAuditor(memory_storage)
        self.security_monitor = SecurityMonitor(redis_client)
        
    async def evaluate_advanced_rules(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate advanced rules with enhanced logic"""
        start_time = time.time()
        
        # Get applicable advanced rules
        advanced_rules = await self._get_applicable_advanced_rules(context)
        
        # Process different rule types
        results = {
            'conditional': await self._process_conditional_rules(advanced_rules, context),
            'cascading': await self._process_cascading_rules(advanced_rules, context),
            'time_based': await self._process_time_based_rules(advanced_rules, context),
            'context_aware': await self._process_context_aware_rules(advanced_rules, context),
            'compliance': await self._process_compliance_rules(advanced_rules, context),
            'security_adaptive': await self._process_security_adaptive_rules(advanced_rules, context)
        }
        
        # Build consolidated configuration
        configuration = await self._build_advanced_configuration(results, context)
        
        # Store evaluation results
        evaluation_time = int((time.time() - start_time) * 1000)
        await self._store_advanced_evaluation(advanced_rules, context, results, evaluation_time)
        
        return {
            'configuration': configuration,
            'advanced_results': results,
            'evaluation_time_ms': evaluation_time,
            'rules_processed': len(advanced_rules)
        }
    
    async def _get_applicable_advanced_rules(self, context: Dict[str, Any]) -> List[AdvancedRule]:
        """Get advanced rules applicable to context"""
        # This would query the database for advanced rules
        # For now, return empty list as placeholder
        return []
    
    async def _process_conditional_rules(self, rules: List[AdvancedRule], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process conditional rules based on dynamic conditions"""
        results = []
        
        for rule in rules:
            if rule.advanced_type != AdvancedRuleType.CONDITIONAL:
                continue
                
            if not rule.conditional_trigger:
                continue
            
            # Check cooldown period
            if (rule.conditional_trigger.last_triggered and 
                (datetime.now() - rule.conditional_trigger.last_triggered).total_seconds() < rule.conditional_trigger.cooldown_period):
                continue
            
            # Evaluate condition expression
            try:
                # Prepare safe evaluation context
                eval_context = {key: context.get(key) for key in rule.conditional_trigger.required_context_fields}
                eval_context.update({
                    'datetime': datetime,
                    'time': time,
                    're': re,
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool
                })
                
                # Evaluate condition safely
                condition_result = eval(rule.conditional_trigger.condition_expression, {"__builtins__": {}}, eval_context)
                
                if condition_result:
                    # Update last triggered time
                    rule.conditional_trigger.last_triggered = datetime.now()
                    
                    # Apply rule actions
                    rule_result = await self._apply_advanced_actions(rule, context)
                    results.append({
                        'rule_id': rule.id,
                        'triggered': True,
                        'result': rule_result,
                        'trigger_time': datetime.now().isoformat()
                    })
                    
                    # Store in hAIveMind memory
                    self.memory_storage.store_memory(
                        content=f"Conditional rule triggered: {rule.name}",
                        category="rules",
                        metadata={
                            'rule_id': rule.id,
                            'rule_type': 'conditional',
                            'condition': rule.conditional_trigger.condition_expression,
                            'context': context
                        }
                    )
                    
            except Exception as e:
                logger.error(f"Error evaluating conditional rule {rule.id}: {e}")
                results.append({
                    'rule_id': rule.id,
                    'triggered': False,
                    'error': str(e)
                })
        
        return {'triggered_rules': results}
    
    async def _process_cascading_rules(self, rules: List[AdvancedRule], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process cascading rules that trigger other rules"""
        cascading_results = []
        
        for rule in rules:
            if rule.advanced_type != AdvancedRuleType.CASCADING:
                continue
            
            if not rule.cascading_actions:
                continue
            
            # Apply primary rule
            primary_result = await self._apply_advanced_actions(rule, context)
            
            # Queue cascading actions
            for cascade_action in rule.cascading_actions:
                cascade_context = context.copy() if cascade_action.pass_context else {}
                
                if cascade_action.condition_override:
                    cascade_context.update(cascade_action.condition_override)
                
                # Schedule cascading rule execution
                asyncio.create_task(
                    self._execute_cascading_action(cascade_action, cascade_context, cascade_action.trigger_delay)
                )
                
                cascading_results.append({
                    'primary_rule_id': rule.id,
                    'cascading_rule_ids': cascade_action.target_rule_ids,
                    'delay': cascade_action.trigger_delay,
                    'scheduled_time': (datetime.now() + timedelta(seconds=cascade_action.trigger_delay)).isoformat()
                })
        
        return {'cascading_executions': cascading_results}
    
    async def _process_time_based_rules(self, rules: List[AdvancedRule], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process time-based scheduled rules"""
        scheduled_results = []
        
        for rule in rules:
            if rule.advanced_type != AdvancedRuleType.TIME_BASED:
                continue
                
            if not rule.schedule:
                continue
            
            # Check if rule should execute now
            if not CRONITER_AVAILABLE:
                logger.warning("croniter not available, skipping time-based rule evaluation")
                continue
                
            cron = croniter.croniter(rule.schedule.cron_expression, datetime.now())
            next_execution = cron.get_next(datetime)
            
            # If within execution window (next 60 seconds), execute
            if (next_execution - datetime.now()).total_seconds() <= 60:
                # Check execution limits
                if (rule.schedule.max_executions and 
                    rule.schedule.execution_count >= rule.schedule.max_executions):
                    continue
                
                # Execute rule
                execution_result = await self._apply_advanced_actions(rule, context)
                rule.schedule.execution_count += 1
                
                scheduled_results.append({
                    'rule_id': rule.id,
                    'executed': True,
                    'execution_time': datetime.now().isoformat(),
                    'next_execution': cron.get_next(datetime).isoformat(),
                    'execution_count': rule.schedule.execution_count,
                    'result': execution_result
                })
                
                # Store execution in memory
                self.memory_storage.store_memory(
                    content=f"Scheduled rule executed: {rule.name}",
                    category="rules",
                    metadata={
                        'rule_id': rule.id,
                        'rule_type': 'time_based',
                        'cron_expression': rule.schedule.cron_expression,
                        'execution_count': rule.schedule.execution_count
                    }
                )
        
        return {'scheduled_executions': scheduled_results}
    
    async def _process_context_aware_rules(self, rules: List[AdvancedRule], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process context-aware adaptive rules"""
        adaptive_results = []
        
        for rule in rules:
            if rule.advanced_type != AdvancedRuleType.CONTEXT_AWARE:
                continue
                
            if not rule.context_adaptation:
                continue
            
            # Analyze context patterns
            context_patterns = await self._analyze_context_patterns(rule, context)
            
            # Check if adaptation is needed
            if context_patterns['adaptation_score'] >= rule.context_adaptation.adaptation_threshold:
                # Adapt rule based on patterns
                adapted_rule = await self._adapt_rule_to_context(rule, context_patterns)
                
                # Apply adapted rule
                adaptation_result = await self._apply_advanced_actions(adapted_rule, context)
                
                adaptive_results.append({
                    'rule_id': rule.id,
                    'adapted': True,
                    'adaptation_score': context_patterns['adaptation_score'],
                    'adaptations_made': context_patterns['suggested_adaptations'],
                    'result': adaptation_result
                })
                
                # Store adaptation learning
                if rule.context_adaptation.learning_enabled:
                    self.memory_storage.store_memory(
                        content=f"Rule adapted to context: {rule.name}",
                        category="rules",
                        metadata={
                            'rule_id': rule.id,
                            'rule_type': 'context_aware',
                            'adaptation_score': context_patterns['adaptation_score'],
                            'context_patterns': context_patterns,
                            'adaptations': context_patterns['suggested_adaptations']
                        }
                    )
            else:
                # Apply rule without adaptation
                standard_result = await self._apply_advanced_actions(rule, context)
                adaptive_results.append({
                    'rule_id': rule.id,
                    'adapted': False,
                    'adaptation_score': context_patterns['adaptation_score'],
                    'result': standard_result
                })
        
        return {'adaptive_executions': adaptive_results}
    
    async def _process_compliance_rules(self, rules: List[AdvancedRule], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process compliance framework rules"""
        compliance_results = []
        
        for rule in rules:
            if rule.advanced_type != AdvancedRuleType.COMPLIANCE:
                continue
                
            if not rule.compliance_config:
                continue
            
            # Execute compliance rule
            compliance_result = await self._apply_advanced_actions(rule, context)
            
            # Audit compliance execution
            audit_result = await self.compliance_auditor.audit_rule_execution(
                rule, context, compliance_result
            )
            
            compliance_results.append({
                'rule_id': rule.id,
                'framework': rule.compliance_config.framework.value,
                'control_id': rule.compliance_config.control_id,
                'severity': rule.compliance_config.severity_level,
                'compliance_result': compliance_result,
                'audit_result': audit_result,
                'evidence_collected': rule.compliance_config.evidence_collection
            })
            
            # Store compliance execution
            self.memory_storage.store_memory(
                content=f"Compliance rule executed: {rule.name}",
                category="compliance",
                metadata={
                    'rule_id': rule.id,
                    'framework': rule.compliance_config.framework.value,
                    'control_id': rule.compliance_config.control_id,
                    'severity': rule.compliance_config.severity_level,
                    'audit_result': audit_result
                }
            )
        
        return {'compliance_executions': compliance_results}
    
    async def _process_security_adaptive_rules(self, rules: List[AdvancedRule], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process security-adaptive rules that respond to threats"""
        security_results = []
        
        for rule in rules:
            if rule.advanced_type != AdvancedRuleType.SECURITY_ADAPTIVE:
                continue
                
            if not rule.security_config:
                continue
            
            # Get current threat level
            threat_level = await self.security_monitor.get_current_threat_level(context)
            
            # Check if threat level exceeds threshold
            if threat_level >= rule.security_config.threat_level_threshold:
                # Apply enhanced security actions
                security_actions = rule.security_config.response_actions.get(
                    self._categorize_threat_level(threat_level), 
                    rule.actions
                )
                
                # Execute security response
                security_result = await self._apply_security_actions(security_actions, context)
                
                # Check for escalation
                if rule.security_config.escalation_rules and threat_level > 0.8:
                    await self._trigger_security_escalation(rule.security_config.escalation_rules, context)
                
                security_results.append({
                    'rule_id': rule.id,
                    'threat_level': threat_level,
                    'threshold_exceeded': True,
                    'response_level': self._categorize_threat_level(threat_level),
                    'security_result': security_result,
                    'escalated': threat_level > 0.8
                })
                
                # Store security event
                self.memory_storage.store_memory(
                    content=f"Security adaptive rule triggered: {rule.name}",
                    category="security",
                    metadata={
                        'rule_id': rule.id,
                        'threat_level': threat_level,
                        'response_level': self._categorize_threat_level(threat_level),
                        'context': context
                    }
                )
            else:
                # Apply standard actions
                standard_result = await self._apply_advanced_actions(rule, context)
                security_results.append({
                    'rule_id': rule.id,
                    'threat_level': threat_level,
                    'threshold_exceeded': False,
                    'security_result': standard_result
                })
        
        return {'security_executions': security_results}
    
    async def _apply_advanced_actions(self, rule: AdvancedRule, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply advanced rule actions with enhanced capabilities"""
        results = []
        
        for action in rule.actions:
            try:
                if action.action_type == "transform":
                    result = await self._apply_transform_action(action, context)
                elif action.action_type == "invoke":
                    result = await self._apply_invoke_action(action, context)
                elif action.action_type == "conditional_set":
                    result = await self._apply_conditional_set_action(action, context)
                elif action.action_type == "aggregate":
                    result = await self._apply_aggregate_action(action, context)
                else:
                    # Use base engine for standard actions
                    result = self.base_engine._apply_action(action, context.get(action.target))
                
                results.append({
                    'action_type': action.action_type,
                    'target': action.target,
                    'result': result,
                    'success': True
                })
                
            except Exception as e:
                logger.error(f"Error applying action {action.action_type}: {e}")
                results.append({
                    'action_type': action.action_type,
                    'target': action.target,
                    'error': str(e),
                    'success': False
                })
        
        return {'action_results': results}
    
    async def _execute_cascading_action(self, cascade_action: CascadingAction, context: Dict[str, Any], delay: int):
        """Execute cascading action after delay"""
        if delay > 0:
            await asyncio.sleep(delay)
        
        for target_rule_id in cascade_action.target_rule_ids:
            try:
                # Get target rule and execute
                target_rule = await self._get_rule_by_id(target_rule_id)
                if target_rule:
                    await self._apply_advanced_actions(target_rule, context)
                    
                    # Store cascading execution
                    self.memory_storage.store_memory(
                        content=f"Cascading rule executed: {target_rule.name}",
                        category="rules",
                        metadata={
                            'rule_id': target_rule_id,
                            'rule_type': 'cascading',
                            'triggered_by': cascade_action,
                            'context': context
                        }
                    )
                    
            except Exception as e:
                logger.error(f"Error executing cascading rule {target_rule_id}: {e}")
    
    def _categorize_threat_level(self, threat_level: float) -> str:
        """Categorize threat level into response categories"""
        if threat_level >= 0.9:
            return "critical"
        elif threat_level >= 0.7:
            return "high"
        elif threat_level >= 0.5:
            return "medium"
        else:
            return "low"


class ComplianceAuditor:
    """Compliance auditing and evidence collection"""
    
    def __init__(self, memory_storage):
        self.memory_storage = memory_storage
    
    async def audit_rule_execution(self, rule: AdvancedRule, context: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Audit compliance rule execution"""
        audit_data = {
            'audit_id': str(uuid.uuid4()),
            'rule_id': rule.id,
            'framework': rule.compliance_config.framework.value,
            'control_id': rule.compliance_config.control_id,
            'execution_time': datetime.now().isoformat(),
            'context': context,
            'result': result,
            'compliance_status': 'compliant' if result.get('success', True) else 'non_compliant'
        }
        
        # Store audit trail
        self.memory_storage.store_memory(
            content=f"Compliance audit: {rule.compliance_config.framework.value} {rule.compliance_config.control_id}",
            category="audit",
            metadata=audit_data
        )
        
        return audit_data


class SecurityMonitor:
    """Security threat monitoring and adaptive response"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
    
    async def get_current_threat_level(self, context: Dict[str, Any]) -> float:
        """Get current threat level based on context and monitoring data"""
        # This would integrate with security monitoring systems
        # For now, return a baseline threat level
        base_threat = 0.1
        
        # Analyze context for threat indicators
        threat_indicators = 0
        
        # Check for suspicious patterns
        if context.get('task_type') == 'code_generation':
            if any(keyword in str(context).lower() for keyword in ['password', 'secret', 'key', 'token']):
                threat_indicators += 0.3
        
        if context.get('file_type') in ['sh', 'bat', 'ps1']:
            threat_indicators += 0.2
        
        # Check time-based factors
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:  # Outside business hours
            threat_indicators += 0.1
        
        return min(base_threat + threat_indicators, 1.0)