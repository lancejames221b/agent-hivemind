#!/usr/bin/env python3
"""
Command Workflow Automation Engine for hAIveMind
Provides intelligent workflow automation for common command sequences
"""

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict, Counter
import logging
import re

logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running" 
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLBACK_REQUIRED = "rollback_required"

class StepStatus(Enum):
    """Individual step status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLBACK = "rollback"

class TriggerType(Enum):
    """Workflow trigger types"""
    MANUAL = "manual"
    CONTEXT_DETECTED = "context_detected"
    PATTERN_MATCHED = "pattern_matched"
    SCHEDULED = "scheduled"
    EXTERNAL_API = "external_api"
    MONITORING_ALERT = "monitoring_alert"

@dataclass
class WorkflowStep:
    """Individual step in a workflow"""
    id: str
    command: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    depends_on: List[str] = field(default_factory=list)
    parallel_group: Optional[str] = None
    rollback_command: Optional[str] = None
    rollback_parameters: Dict[str, Any] = field(default_factory=dict)
    validation_checks: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

@dataclass
class WorkflowTemplate:
    """Template for workflow automation"""
    id: str
    name: str
    description: str
    category: str
    version: str = "1.0.0"
    author: str = "system"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    steps: List[WorkflowStep] = field(default_factory=list)
    trigger_conditions: List[Dict[str, Any]] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    estimated_duration: int = 0  # seconds
    success_rate: float = 0.0
    usage_count: int = 0
    last_used: Optional[float] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    environment_requirements: List[str] = field(default_factory=list)
    approval_required: bool = False
    rollback_enabled: bool = True
    notification_settings: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowExecution:
    """Active workflow execution instance"""
    id: str
    template_id: str
    name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    trigger_type: TriggerType = TriggerType.MANUAL
    trigger_context: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    current_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    step_results: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    machine_id: Optional[str] = None
    error_message: Optional[str] = None
    rollback_steps: List[str] = field(default_factory=list)
    notifications_sent: List[str] = field(default_factory=list)
    approval_status: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[float] = None

@dataclass
class WorkflowSuggestion:
    """Smart workflow suggestion"""
    workflow_id: str
    name: str
    confidence: float
    reason: str
    context_match: Dict[str, Any]
    suggested_parameters: Dict[str, Any] = field(default_factory=dict)
    estimated_duration: int = 0
    success_probability: float = 0.0
    similar_executions: int = 0

class WorkflowAutomationEngine:
    """Core workflow automation engine"""
    
    def __init__(self, storage, config: Dict[str, Any]):
        self.storage = storage
        self.config = config
        
        # Core data structures
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.execution_history: List[WorkflowExecution] = []
        
        # Pattern learning
        self.command_sequences: List[List[str]] = []
        self.context_patterns: Dict[str, List[str]] = defaultdict(list)
        self.success_patterns: Dict[str, float] = {}
        
        # Performance tracking
        self.execution_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.performance_metrics: Dict[str, List[float]] = defaultdict(list)
        
        # Cache and optimization
        self._suggestion_cache: Dict[str, List[WorkflowSuggestion]] = {}
        self._pattern_cache: Dict[str, Any] = {}
        self._last_cache_update: float = 0
        
        # Load predefined templates
        self._load_predefined_templates()
    
    async def initialize(self):
        """Initialize the workflow engine"""
        await self._load_templates_from_storage()
        await self._load_execution_history()
        await self._analyze_command_patterns()
        await self._update_success_rates()
        logger.info("Workflow automation engine initialized")
    
    def _load_predefined_templates(self):
        """Load predefined workflow templates"""
        
        # Incident Response Workflow
        incident_response = WorkflowTemplate(
            id="incident_response",
            name="Incident Response Workflow",
            description="Handle system incidents and outages with coordinated response",
            category="incident_management",
            tags=["incident", "emergency", "response", "critical"],
            estimated_duration=1800,  # 30 minutes
            steps=[
                WorkflowStep(
                    id="assess_situation",
                    command="hv-status",
                    description="Check collective health and identify issues",
                    parameters={"detailed": True},
                    timeout_seconds=60,
                    validation_checks=["agent_count > 0", "response_time < 30"],
                    success_criteria=["status_received", "agents_responsive"]
                ),
                WorkflowStep(
                    id="broadcast_incident",
                    command="hv-broadcast",
                    description="Alert all agents about the incident",
                    parameters={"severity": "critical", "category": "incident"},
                    depends_on=["assess_situation"],
                    timeout_seconds=30,
                    validation_checks=["broadcast_sent", "agents_notified"],
                    success_criteria=["message_delivered", "acknowledgments_received"]
                ),
                WorkflowStep(
                    id="delegate_resolution",
                    command="hv-delegate",
                    description="Assign specific resolution tasks to specialists",
                    parameters={"priority": "critical"},
                    depends_on=["broadcast_incident"],
                    required_capabilities=["incident_response"],
                    timeout_seconds=120,
                    validation_checks=["task_assigned", "agent_acknowledged"],
                    success_criteria=["specialist_assigned", "task_accepted"]
                ),
                WorkflowStep(
                    id="search_solutions",
                    command="hv-query",
                    description="Search for similar past incidents and solutions",
                    parameters={"category": "incidents"},
                    depends_on=["assess_situation"],
                    parallel_group="analysis",
                    timeout_seconds=60,
                    validation_checks=["search_completed"],
                    success_criteria=["relevant_results_found"]
                ),
                WorkflowStep(
                    id="document_resolution",
                    command="remember",
                    description="Document resolution for future reference",
                    parameters={"category": "incidents", "important": True},
                    depends_on=["delegate_resolution"],
                    timeout_seconds=60,
                    validation_checks=["memory_stored"],
                    success_criteria=["documentation_complete"]
                )
            ],
            trigger_conditions=[
                {"type": "keyword_match", "keywords": ["incident", "outage", "down", "critical"]},
                {"type": "severity_level", "min_severity": "critical"},
                {"type": "agent_count", "threshold": 0.7}  # Less than 70% agents responding
            ],
            rollback_enabled=False,  # Incident response shouldn't be rolled back
            approval_required=False,  # Emergency response should be immediate
            notification_settings={
                "notify_on_start": True,
                "notify_on_completion": True,
                "notify_on_failure": True
            }
        )
        
        # Security Alert Workflow
        security_alert = WorkflowTemplate(
            id="security_alert",
            name="Security Alert Workflow",
            description="Respond to security threats and vulnerabilities",
            category="security",
            tags=["security", "vulnerability", "threat", "alert"],
            estimated_duration=2400,  # 40 minutes
            steps=[
                WorkflowStep(
                    id="document_alert",
                    command="remember",
                    description="Document the security alert details",
                    parameters={"category": "security", "important": True},
                    timeout_seconds=60,
                    validation_checks=["memory_stored"],
                    success_criteria=["alert_documented"]
                ),
                WorkflowStep(
                    id="check_awareness",
                    command="hv-query",
                    description="Check if threat is already known to collective",
                    parameters={"category": "security"},
                    depends_on=["document_alert"],
                    timeout_seconds=60,
                    validation_checks=["search_completed"],
                    success_criteria=["awareness_checked"]
                ),
                WorkflowStep(
                    id="broadcast_threat",
                    command="hv-broadcast",
                    description="Alert all agents about security threat",
                    parameters={"severity": "critical", "category": "security"},
                    depends_on=["check_awareness"],
                    timeout_seconds=30,
                    validation_checks=["broadcast_sent"],
                    success_criteria=["security_team_notified"]
                ),
                WorkflowStep(
                    id="delegate_analysis",
                    command="hv-delegate",
                    description="Assign security analysis to specialists",
                    parameters={"priority": "critical"},
                    depends_on=["broadcast_threat"],
                    required_capabilities=["security_analysis", "vulnerability_assessment"],
                    timeout_seconds=120,
                    validation_checks=["task_assigned"],
                    success_criteria=["security_specialist_assigned"]
                )
            ],
            trigger_conditions=[
                {"type": "keyword_match", "keywords": ["vulnerability", "breach", "attack", "exploit"]},
                {"type": "category_match", "categories": ["security"]},
                {"type": "severity_level", "min_severity": "warning"}
            ],
            approval_required=False,  # Security alerts need immediate response
            rollback_enabled=True
        )
        
        # Maintenance Window Workflow
        maintenance_window = WorkflowTemplate(
            id="maintenance_window",
            name="Maintenance Window Workflow",
            description="Coordinate planned maintenance activities",
            category="maintenance",
            tags=["maintenance", "planned", "coordination", "infrastructure"],
            estimated_duration=3600,  # 60 minutes
            steps=[
                WorkflowStep(
                    id="sync_configs",
                    command="hv-sync",
                    description="Ensure all configurations are current",
                    timeout_seconds=300,
                    validation_checks=["sync_completed", "configs_updated"],
                    success_criteria=["all_agents_synced"]
                ),
                WorkflowStep(
                    id="document_maintenance",
                    command="remember",
                    description="Document maintenance window details",
                    parameters={"category": "infrastructure"},
                    depends_on=["sync_configs"],
                    timeout_seconds=60,
                    validation_checks=["memory_stored"],
                    success_criteria=["maintenance_documented"]
                ),
                WorkflowStep(
                    id="broadcast_start",
                    command="hv-broadcast",
                    description="Announce maintenance window start",
                    parameters={"severity": "info", "category": "infrastructure"},
                    depends_on=["document_maintenance"],
                    timeout_seconds=30,
                    validation_checks=["broadcast_sent"],
                    success_criteria=["team_notified"]
                ),
                WorkflowStep(
                    id="check_status",
                    command="hv-status",
                    description="Verify system status during maintenance",
                    depends_on=["broadcast_start"],
                    timeout_seconds=60,
                    validation_checks=["status_received"],
                    success_criteria=["systems_stable"]
                ),
                WorkflowStep(
                    id="broadcast_completion",
                    command="hv-broadcast",
                    description="Announce maintenance completion",
                    parameters={"severity": "info", "category": "infrastructure"},
                    depends_on=["check_status"],
                    timeout_seconds=30,
                    validation_checks=["broadcast_sent"],
                    success_criteria=["completion_announced"]
                )
            ],
            trigger_conditions=[
                {"type": "keyword_match", "keywords": ["maintenance", "update", "upgrade"]},
                {"type": "scheduled", "schedule_pattern": "maintenance_window"}
            ],
            approval_required=True,  # Planned maintenance should be approved
            rollback_enabled=True
        )
        
        # Knowledge Sharing Workflow
        knowledge_sharing = WorkflowTemplate(
            id="knowledge_sharing",
            name="Knowledge Sharing Workflow", 
            description="Share important discoveries across the collective",
            category="knowledge_management",
            tags=["knowledge", "sharing", "discovery", "learning"],
            estimated_duration=300,  # 5 minutes
            steps=[
                WorkflowStep(
                    id="search_existing",
                    command="recall",
                    description="Check if similar knowledge already exists",
                    timeout_seconds=60,
                    validation_checks=["search_completed"],
                    success_criteria=["duplicates_checked"]
                ),
                WorkflowStep(
                    id="broadcast_discovery",
                    command="hv-broadcast",
                    description="Share discovery with collective",
                    parameters={"severity": "info"},
                    depends_on=["search_existing"],
                    timeout_seconds=30,
                    validation_checks=["broadcast_sent"],
                    success_criteria=["knowledge_shared"]
                ),
                WorkflowStep(
                    id="verify_receipt",
                    command="hv-query",
                    description="Verify agents received the knowledge",
                    depends_on=["broadcast_discovery"],
                    timeout_seconds=60,
                    validation_checks=["query_completed"],
                    success_criteria=["receipt_verified"]
                )
            ],
            trigger_conditions=[
                {"type": "keyword_match", "keywords": ["discovery", "solution", "found", "learned"]},
                {"type": "success_pattern", "pattern": "problem_solved"}
            ],
            approval_required=False,
            rollback_enabled=False  # Knowledge sharing doesn't need rollback
        )
        
        # Configuration Update Workflow
        config_update = WorkflowTemplate(
            id="config_update",
            name="Configuration Update Workflow",
            description="Safely update and distribute configuration changes",
            category="configuration",
            tags=["configuration", "update", "sync", "deployment"],
            estimated_duration=900,  # 15 minutes
            steps=[
                WorkflowStep(
                    id="sync_current_config",
                    command="hv-sync",
                    description="Sync current configuration state",
                    timeout_seconds=120,
                    validation_checks=["sync_completed"],
                    success_criteria=["configs_synced"],
                    rollback_command="hv-sync",
                    rollback_parameters={"restore": True}
                ),
                WorkflowStep(
                    id="document_changes",
                    command="remember",
                    description="Document configuration changes",
                    parameters={"category": "infrastructure"},
                    depends_on=["sync_current_config"],
                    timeout_seconds=60,
                    validation_checks=["memory_stored"],
                    success_criteria=["changes_documented"]
                ),
                WorkflowStep(
                    id="broadcast_update",
                    command="hv-broadcast",
                    description="Announce configuration update",
                    parameters={"severity": "info", "category": "infrastructure"},
                    depends_on=["document_changes"],
                    timeout_seconds=30,
                    validation_checks=["broadcast_sent"],
                    success_criteria=["update_announced"]
                ),
                WorkflowStep(
                    id="verify_agents",
                    command="hv-query",
                    description="Verify all agents received update",
                    depends_on=["broadcast_update"],
                    timeout_seconds=90,
                    validation_checks=["query_completed"],
                    success_criteria=["all_agents_updated"]
                )
            ],
            trigger_conditions=[
                {"type": "keyword_match", "keywords": ["config", "configuration", "update", "change"]},
                {"type": "file_change", "patterns": ["*.conf", "*.yaml", "*.json"]}
            ],
            approval_required=True,
            rollback_enabled=True
        )
        
        # Task Delegation Workflow
        task_delegation = WorkflowTemplate(
            id="task_delegation",
            name="Task Delegation Workflow",
            description="Efficiently delegate and track task completion",
            category="task_management",
            tags=["delegation", "task", "assignment", "tracking"],
            estimated_duration=600,  # 10 minutes
            steps=[
                WorkflowStep(
                    id="document_task",
                    command="remember",
                    description="Document the task requirements",
                    parameters={"category": "project"},
                    timeout_seconds=60,
                    validation_checks=["memory_stored"],
                    success_criteria=["task_documented"]
                ),
                WorkflowStep(
                    id="find_agent",
                    command="hv-query",
                    description="Find suitable agent for task",
                    depends_on=["document_task"],
                    timeout_seconds=60,
                    validation_checks=["search_completed"],
                    success_criteria=["suitable_agent_found"]
                ),
                WorkflowStep(
                    id="delegate_task",
                    command="hv-delegate",
                    description="Assign task to selected agent",
                    depends_on=["find_agent"],
                    timeout_seconds=120,
                    validation_checks=["task_assigned"],
                    success_criteria=["agent_accepted_task"]
                ),
                WorkflowStep(
                    id="check_status",
                    command="hv-status",
                    description="Check task progress and agent status",
                    depends_on=["delegate_task"],
                    timeout_seconds=60,
                    validation_checks=["status_received"],
                    success_criteria=["progress_tracked"]
                )
            ],
            trigger_conditions=[
                {"type": "keyword_match", "keywords": ["delegate", "assign", "task", "help"]},
                {"type": "workload_threshold", "max_workload": 0.8}
            ],
            approval_required=False,
            rollback_enabled=True
        )
        
        # Store all templates
        templates = [
            incident_response, security_alert, maintenance_window,
            knowledge_sharing, config_update, task_delegation
        ]
        
        for template in templates:
            self.templates[template.id] = template
            logger.debug(f"Loaded workflow template: {template.name}")
    
    async def _load_templates_from_storage(self):
        """Load custom workflow templates from storage"""
        try:
            # Search for stored workflow templates
            template_memories = await self.storage.search_memories(
                query="workflow template",
                category="agent",
                limit=100
            )
            
            for memory in template_memories:
                if 'workflow_template' in memory.get('metadata', {}):
                    template_data = memory['metadata']['workflow_template']
                    if isinstance(template_data, str):
                        try:
                            template_data = json.loads(template_data)
                        except:
                            continue
                    
                    # Convert to WorkflowTemplate object
                    template = self._dict_to_workflow_template(template_data)
                    if template:
                        self.templates[template.id] = template
                        logger.debug(f"Loaded custom workflow template: {template.name}")
                        
        except Exception as e:
            logger.error(f"Error loading workflow templates from storage: {e}")
    
    async def _load_execution_history(self):
        """Load workflow execution history"""
        try:
            execution_memories = await self.storage.search_memories(
                query="workflow execution",
                category="agent",
                limit=200
            )
            
            for memory in execution_memories:
                if 'workflow_execution' in memory.get('metadata', {}):
                    execution_data = memory['metadata']['workflow_execution']
                    if isinstance(execution_data, str):
                        try:
                            execution_data = json.loads(execution_data)
                        except:
                            continue
                    
                    execution = self._dict_to_workflow_execution(execution_data)
                    if execution:
                        self.execution_history.append(execution)
                        
        except Exception as e:
            logger.error(f"Error loading execution history: {e}")
    
    async def _analyze_command_patterns(self):
        """Analyze command usage patterns for workflow suggestions"""
        try:
            # Get recent command usage
            usage_memories = await self.storage.search_memories(
                query="command usage",
                category="agent",
                limit=500
            )
            
            sequences = []
            for memory in usage_memories:
                if 'command_usage' in memory.get('metadata', {}):
                    usage_data = memory['metadata']['command_usage']
                    if isinstance(usage_data, str):
                        try:
                            usage_data = json.loads(usage_data)
                        except:
                            continue
                    
                    command = usage_data.get('command', '')
                    context = usage_data.get('context', '')
                    timestamp = usage_data.get('timestamp', 0)
                    
                    if command:
                        sequences.append({
                            'command': command,
                            'context': context,
                            'timestamp': timestamp
                        })
            
            # Sort by timestamp and group into sequences
            sequences.sort(key=lambda x: x['timestamp'])
            
            # Find command sequences (commands within 5 minutes of each other)
            current_sequence = []
            last_timestamp = 0
            
            for seq in sequences:
                if seq['timestamp'] - last_timestamp < 300:  # 5 minutes
                    current_sequence.append(seq['command'])
                else:
                    if len(current_sequence) >= 2:
                        self.command_sequences.append(current_sequence.copy())
                    current_sequence = [seq['command']]
                
                last_timestamp = seq['timestamp']
            
            # Add final sequence
            if len(current_sequence) >= 2:
                self.command_sequences.append(current_sequence)
            
            logger.debug(f"Analyzed {len(self.command_sequences)} command sequences")
            
        except Exception as e:
            logger.error(f"Error analyzing command patterns: {e}")
    
    async def _update_success_rates(self):
        """Update workflow success rates based on execution history"""
        template_stats = defaultdict(lambda: {'total': 0, 'successful': 0})
        
        for execution in self.execution_history:
            template_stats[execution.template_id]['total'] += 1
            if execution.status == WorkflowStatus.COMPLETED:
                template_stats[execution.template_id]['successful'] += 1
        
        # Update template success rates
        for template_id, stats in template_stats.items():
            if template_id in self.templates:
                if stats['total'] > 0:
                    success_rate = stats['successful'] / stats['total']
                    self.templates[template_id].success_rate = success_rate
                    self.templates[template_id].usage_count = stats['total']
    
    async def suggest_workflows(self, context: Optional[str] = None, 
                              recent_commands: Optional[List[str]] = None,
                              intent: Optional[str] = None) -> List[WorkflowSuggestion]:
        """Suggest relevant workflows based on context"""
        suggestions = []
        
        # Context-based suggestions
        if context:
            context_suggestions = await self._get_context_based_suggestions(context)
            suggestions.extend(context_suggestions)
        
        # Pattern-based suggestions
        if recent_commands:
            pattern_suggestions = await self._get_pattern_based_suggestions(recent_commands)
            suggestions.extend(pattern_suggestions)
        
        # Intent-based suggestions
        if intent:
            intent_suggestions = await self._get_intent_based_suggestions(intent)
            suggestions.extend(intent_suggestions)
        
        # Default suggestions based on current state
        if not suggestions:
            suggestions = await self._get_default_suggestions()
        
        # Rank and deduplicate suggestions
        ranked_suggestions = await self._rank_workflow_suggestions(suggestions)
        
        return ranked_suggestions[:8]  # Top 8 suggestions
    
    async def _get_context_based_suggestions(self, context: str) -> List[WorkflowSuggestion]:
        """Get workflow suggestions based on context"""
        suggestions = []
        context_lower = context.lower()
        
        for template in self.templates.values():
            confidence = 0.0
            match_reasons = []
            
            # Check trigger conditions
            for condition in template.trigger_conditions:
                if condition.get('type') == 'keyword_match':
                    keywords = condition.get('keywords', [])
                    matched_keywords = [kw for kw in keywords if kw.lower() in context_lower]
                    if matched_keywords:
                        confidence += 0.3 * (len(matched_keywords) / len(keywords))
                        match_reasons.append(f"Keywords matched: {', '.join(matched_keywords)}")
                
                elif condition.get('type') == 'category_match':
                    categories = condition.get('categories', [])
                    if any(cat.lower() in context_lower for cat in categories):
                        confidence += 0.4
                        match_reasons.append("Category match detected")
            
            # Check template tags
            matched_tags = [tag for tag in template.tags if tag.lower() in context_lower]
            if matched_tags:
                confidence += 0.2 * (len(matched_tags) / len(template.tags))
                match_reasons.append(f"Tags matched: {', '.join(matched_tags)}")
            
            # Check description similarity
            if any(word in template.description.lower() for word in context_lower.split()):
                confidence += 0.1
                match_reasons.append("Description similarity")
            
            if confidence > 0.2:  # Minimum confidence threshold
                suggestions.append(WorkflowSuggestion(
                    workflow_id=template.id,
                    name=template.name,
                    confidence=min(confidence, 1.0),
                    reason="; ".join(match_reasons),
                    context_match={'context': context, 'matched_elements': match_reasons},
                    estimated_duration=template.estimated_duration,
                    success_probability=template.success_rate,
                    similar_executions=template.usage_count
                ))
        
        return suggestions
    
    async def _get_pattern_based_suggestions(self, recent_commands: List[str]) -> List[WorkflowSuggestion]:
        """Get suggestions based on recent command patterns"""
        suggestions = []
        
        # Check if recent commands match workflow patterns
        for template in self.templates.values():
            template_commands = [step.command for step in template.steps]
            
            # Calculate pattern similarity
            similarity = self._calculate_command_similarity(recent_commands, template_commands)
            
            if similarity > 0.3:  # Minimum similarity threshold
                # Check if this looks like a partial workflow execution
                partial_match = self._check_partial_workflow_match(recent_commands, template_commands)
                
                confidence = similarity
                reason = f"Command pattern similarity: {similarity:.0%}"
                
                if partial_match:
                    confidence += 0.2
                    reason += "; Partial workflow detected"
                
                suggestions.append(WorkflowSuggestion(
                    workflow_id=template.id,
                    name=template.name,
                    confidence=min(confidence, 1.0),
                    reason=reason,
                    context_match={'recent_commands': recent_commands, 'similarity': similarity},
                    estimated_duration=template.estimated_duration,
                    success_probability=template.success_rate,
                    similar_executions=template.usage_count
                ))
        
        return suggestions
    
    async def _get_intent_based_suggestions(self, intent: str) -> List[WorkflowSuggestion]:
        """Get suggestions based on user intent"""
        suggestions = []
        intent_lower = intent.lower()
        
        # Intent mapping to workflow categories
        intent_mappings = {
            'incident': ['incident_management', 'emergency'],
            'security': ['security', 'vulnerability'],
            'maintenance': ['maintenance', 'infrastructure'],
            'deploy': ['deployment', 'configuration'],
            'monitor': ['monitoring', 'alerting'],
            'delegate': ['task_management', 'delegation'],
            'share': ['knowledge_management', 'communication']
        }
        
        for intent_key, categories in intent_mappings.items():
            if intent_key in intent_lower:
                for template in self.templates.values():
                    if template.category in categories:
                        confidence = 0.7  # High confidence for intent matches
                        
                        # Boost confidence for exact matches
                        if intent_key in template.name.lower():
                            confidence += 0.2
                        
                        suggestions.append(WorkflowSuggestion(
                            workflow_id=template.id,
                            name=template.name,
                            confidence=min(confidence, 1.0),
                            reason=f"Intent match: {intent_key}",
                            context_match={'intent': intent, 'category': template.category},
                            estimated_duration=template.estimated_duration,
                            success_probability=template.success_rate,
                            similar_executions=template.usage_count
                        ))
        
        return suggestions
    
    async def _get_default_suggestions(self) -> List[WorkflowSuggestion]:
        """Get default workflow suggestions"""
        suggestions = []
        
        # Suggest most successful and frequently used workflows
        sorted_templates = sorted(
            self.templates.values(),
            key=lambda t: (t.success_rate * t.usage_count, t.usage_count),
            reverse=True
        )
        
        for template in sorted_templates[:3]:  # Top 3 templates
            confidence = 0.3 + (template.success_rate * 0.3) + (min(template.usage_count / 10, 0.4))
            
            suggestions.append(WorkflowSuggestion(
                workflow_id=template.id,
                name=template.name,
                confidence=min(confidence, 1.0),
                reason="Popular and reliable workflow",
                context_match={'type': 'default', 'rank': len(suggestions) + 1},
                estimated_duration=template.estimated_duration,
                success_probability=template.success_rate,
                similar_executions=template.usage_count
            ))
        
        return suggestions
    
    async def _rank_workflow_suggestions(self, suggestions: List[WorkflowSuggestion]) -> List[WorkflowSuggestion]:
        """Rank workflow suggestions by relevance and quality"""
        def suggestion_score(suggestion: WorkflowSuggestion) -> float:
            score = suggestion.confidence * 0.4
            score += suggestion.success_probability * 0.3
            score += min(suggestion.similar_executions / 10, 0.2) * 0.2
            score += (1.0 - min(suggestion.estimated_duration / 3600, 1.0)) * 0.1  # Prefer shorter workflows
            return score
        
        # Remove duplicates and sort by score
        unique_suggestions = {}
        for suggestion in suggestions:
            if suggestion.workflow_id not in unique_suggestions:
                unique_suggestions[suggestion.workflow_id] = suggestion
            else:
                # Keep the one with higher confidence
                if suggestion.confidence > unique_suggestions[suggestion.workflow_id].confidence:
                    unique_suggestions[suggestion.workflow_id] = suggestion
        
        ranked = sorted(unique_suggestions.values(), key=suggestion_score, reverse=True)
        return ranked
    
    def _calculate_command_similarity(self, commands1: List[str], commands2: List[str]) -> float:
        """Calculate similarity between two command sequences"""
        if not commands1 or not commands2:
            return 0.0
        
        # Simple Jaccard similarity
        set1 = set(commands1)
        set2 = set(commands2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _check_partial_workflow_match(self, recent_commands: List[str], template_commands: List[str]) -> bool:
        """Check if recent commands represent a partial workflow execution"""
        if len(recent_commands) < 2:
            return False
        
        # Check if recent commands appear in sequence in template
        for i in range(len(template_commands) - len(recent_commands) + 1):
            template_slice = template_commands[i:i + len(recent_commands)]
            if template_slice == recent_commands:
                return True
        
        return False
    
    async def execute_workflow(self, template_id: str, parameters: Dict[str, Any] = None,
                             trigger_type: TriggerType = TriggerType.MANUAL,
                             trigger_context: Dict[str, Any] = None,
                             user_id: Optional[str] = None) -> str:
        """Execute a workflow and return execution ID"""
        if template_id not in self.templates:
            raise ValueError(f"Workflow template not found: {template_id}")
        
        template = self.templates[template_id]
        
        # Create execution instance
        execution_id = str(uuid.uuid4())
        execution = WorkflowExecution(
            id=execution_id,
            template_id=template_id,
            name=template.name,
            trigger_type=trigger_type,
            trigger_context=trigger_context or {},
            parameters=parameters or {},
            user_id=user_id,
            machine_id=getattr(self.storage, 'machine_id', 'unknown')
        )
        
        self.executions[execution_id] = execution
        
        # Check if approval is required
        if template.approval_required:
            execution.status = WorkflowStatus.PENDING
            await self._request_approval(execution)
            return execution_id
        
        # Start execution
        await self._start_workflow_execution(execution)
        return execution_id
    
    async def _start_workflow_execution(self, execution: WorkflowExecution):
        """Start workflow execution"""
        execution.status = WorkflowStatus.RUNNING
        execution.start_time = time.time()
        
        template = self.templates[execution.template_id]
        
        # Store execution start in memory
        await self.storage.store_memory(
            content=f"Started workflow execution: {execution.name}",
            category="agent",
            context=f"Workflow execution {execution.id}",
            metadata={
                'workflow_execution': json.dumps(asdict(execution)),
                'workflow_id': execution.template_id,
                'execution_id': execution.id,
                'status': 'started'
            },
            tags=['workflow', 'execution', 'started', execution.template_id]
        )
        
        # Execute workflow steps
        try:
            await self._execute_workflow_steps(execution, template)
            
            # Mark as completed
            execution.status = WorkflowStatus.COMPLETED
            execution.end_time = time.time()
            
            # Update template statistics
            template.usage_count += 1
            template.last_used = execution.end_time
            
            # Store completion
            await self._store_workflow_completion(execution)
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            execution.end_time = time.time()
            
            logger.error(f"Workflow execution failed: {e}")
            
            # Attempt rollback if enabled
            if template.rollback_enabled:
                await self._rollback_workflow(execution)
            
            # Store failure
            await self._store_workflow_failure(execution)
        
        # Move to history
        self.execution_history.append(execution)
        if execution.id in self.executions:
            del self.executions[execution.id]
    
    async def _execute_workflow_steps(self, execution: WorkflowExecution, template: WorkflowTemplate):
        """Execute individual workflow steps"""
        # Build dependency graph
        step_dependencies = {}
        parallel_groups = defaultdict(list)
        
        for step in template.steps:
            step_dependencies[step.id] = step.depends_on.copy()
            if step.parallel_group:
                parallel_groups[step.parallel_group].append(step.id)
        
        completed_steps = set()
        
        while len(completed_steps) < len(template.steps):
            # Find steps ready to execute
            ready_steps = []
            for step in template.steps:
                if (step.id not in completed_steps and 
                    all(dep in completed_steps for dep in step.depends_on)):
                    ready_steps.append(step)
            
            if not ready_steps:
                raise Exception("Workflow deadlock: no steps ready to execute")
            
            # Group steps by parallel execution
            execution_groups = defaultdict(list)
            for step in ready_steps:
                group_key = step.parallel_group or step.id
                execution_groups[group_key].append(step)
            
            # Execute groups
            for group_steps in execution_groups.values():
                if len(group_steps) == 1:
                    # Single step execution
                    step = group_steps[0]
                    await self._execute_single_step(execution, step)
                    completed_steps.add(step.id)
                else:
                    # Parallel execution
                    tasks = []
                    for step in group_steps:
                        tasks.append(self._execute_single_step(execution, step))
                    
                    # Wait for all parallel steps to complete
                    await asyncio.gather(*tasks)
                    for step in group_steps:
                        completed_steps.add(step.id)
    
    async def _execute_single_step(self, execution: WorkflowExecution, step: WorkflowStep):
        """Execute a single workflow step"""
        step.status = StepStatus.RUNNING
        step.start_time = time.time()
        execution.current_step = step.id
        
        logger.info(f"Executing step {step.id}: {step.command}")
        
        try:
            # Prepare parameters
            step_params = step.parameters.copy()
            step_params.update(execution.parameters)
            
            # Execute command (this would integrate with the actual command system)
            result = await self._execute_command(step.command, step_params)
            
            # Validate result
            if step.validation_checks:
                await self._validate_step_result(step, result)
            
            # Check success criteria
            if step.success_criteria:
                await self._check_success_criteria(step, result)
            
            step.status = StepStatus.COMPLETED
            step.result = result
            execution.completed_steps.append(step.id)
            execution.step_results[step.id] = result
            
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error_message = str(e)
            execution.failed_steps.append(step.id)
            
            # Retry logic
            if step.retry_count < step.max_retries:
                step.retry_count += 1
                step.status = StepStatus.PENDING
                logger.warning(f"Step {step.id} failed, retrying ({step.retry_count}/{step.max_retries})")
                await asyncio.sleep(2 ** step.retry_count)  # Exponential backoff
                await self._execute_single_step(execution, step)
            else:
                logger.error(f"Step {step.id} failed after {step.max_retries} retries: {e}")
                raise
        
        finally:
            step.end_time = time.time()
    
    async def _execute_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command (placeholder for actual command execution)"""
        # This would integrate with the actual command execution system
        # For now, return a mock result
        await asyncio.sleep(0.1)  # Simulate execution time
        
        return {
            'command': command,
            'parameters': parameters,
            'status': 'success',
            'timestamp': time.time(),
            'result': f"Mock result for {command}"
        }
    
    async def _validate_step_result(self, step: WorkflowStep, result: Dict[str, Any]):
        """Validate step execution result"""
        for check in step.validation_checks:
            # Simple validation logic (would be more sophisticated in practice)
            if check == "status_success" and result.get('status') != 'success':
                raise Exception(f"Validation failed: {check}")
    
    async def _check_success_criteria(self, step: WorkflowStep, result: Dict[str, Any]):
        """Check if step meets success criteria"""
        for criteria in step.success_criteria:
            # Simple criteria checking (would be more sophisticated in practice)
            if criteria not in str(result):
                logger.warning(f"Success criteria not met: {criteria}")
    
    async def _rollback_workflow(self, execution: WorkflowExecution):
        """Rollback failed workflow execution"""
        execution.status = WorkflowStatus.ROLLBACK_REQUIRED
        
        # Execute rollback steps in reverse order
        template = self.templates[execution.template_id]
        
        for step_id in reversed(execution.completed_steps):
            step = next((s for s in template.steps if s.id == step_id), None)
            if step and step.rollback_command:
                try:
                    await self._execute_command(step.rollback_command, step.rollback_parameters)
                    execution.rollback_steps.append(step_id)
                except Exception as e:
                    logger.error(f"Rollback failed for step {step_id}: {e}")
    
    async def _store_workflow_completion(self, execution: WorkflowExecution):
        """Store workflow completion in memory"""
        duration = execution.end_time - execution.start_time
        
        await self.storage.store_memory(
            content=f"Completed workflow: {execution.name} in {duration:.1f}s",
            category="agent",
            context=f"Workflow execution {execution.id} completed",
            metadata={
                'workflow_execution': json.dumps(asdict(execution)),
                'workflow_id': execution.template_id,
                'execution_id': execution.id,
                'status': 'completed',
                'duration': duration,
                'steps_completed': len(execution.completed_steps),
                'success_rate': len(execution.completed_steps) / len(self.templates[execution.template_id].steps)
            },
            tags=['workflow', 'execution', 'completed', execution.template_id]
        )
    
    async def _store_workflow_failure(self, execution: WorkflowExecution):
        """Store workflow failure in memory"""
        duration = (execution.end_time or time.time()) - execution.start_time
        
        await self.storage.store_memory(
            content=f"Failed workflow: {execution.name} after {duration:.1f}s - {execution.error_message}",
            category="agent",
            context=f"Workflow execution {execution.id} failed",
            metadata={
                'workflow_execution': json.dumps(asdict(execution)),
                'workflow_id': execution.template_id,
                'execution_id': execution.id,
                'status': 'failed',
                'error': execution.error_message,
                'duration': duration,
                'steps_completed': len(execution.completed_steps),
                'steps_failed': len(execution.failed_steps)
            },
            tags=['workflow', 'execution', 'failed', execution.template_id]
        )
    
    async def _request_approval(self, execution: WorkflowExecution):
        """Request approval for workflow execution"""
        # This would integrate with approval system
        # For now, just log the request
        logger.info(f"Approval requested for workflow: {execution.name}")
    
    def _dict_to_workflow_template(self, data: Dict[str, Any]) -> Optional[WorkflowTemplate]:
        """Convert dictionary to WorkflowTemplate object"""
        try:
            # Convert steps
            steps = []
            for step_data in data.get('steps', []):
                step = WorkflowStep(**step_data)
                steps.append(step)
            
            data['steps'] = steps
            return WorkflowTemplate(**data)
        except Exception as e:
            logger.error(f"Error converting dict to WorkflowTemplate: {e}")
            return None
    
    def _dict_to_workflow_execution(self, data: Dict[str, Any]) -> Optional[WorkflowExecution]:
        """Convert dictionary to WorkflowExecution object"""
        try:
            return WorkflowExecution(**data)
        except Exception as e:
            logger.error(f"Error converting dict to WorkflowExecution: {e}")
            return None
    
    async def get_workflow_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get status of workflow execution"""
        if execution_id in self.executions:
            execution = self.executions[execution_id]
        else:
            # Check history
            execution = next((e for e in self.execution_history if e.id == execution_id), None)
        
        if not execution:
            return None
        
        template = self.templates.get(execution.template_id)
        if not template:
            return None
        
        # Calculate progress
        total_steps = len(template.steps)
        completed_steps = len(execution.completed_steps)
        progress = completed_steps / total_steps if total_steps > 0 else 0
        
        return {
            'execution_id': execution.id,
            'template_id': execution.template_id,
            'name': execution.name,
            'status': execution.status.value,
            'progress': progress,
            'current_step': execution.current_step,
            'completed_steps': execution.completed_steps,
            'failed_steps': execution.failed_steps,
            'start_time': execution.start_time,
            'end_time': execution.end_time,
            'error_message': execution.error_message,
            'total_steps': total_steps
        }
    
    async def cancel_workflow(self, execution_id: str) -> bool:
        """Cancel running workflow execution"""
        if execution_id not in self.executions:
            return False
        
        execution = self.executions[execution_id]
        if execution.status not in [WorkflowStatus.RUNNING, WorkflowStatus.PENDING]:
            return False
        
        execution.status = WorkflowStatus.CANCELLED
        execution.end_time = time.time()
        
        # Store cancellation
        await self.storage.store_memory(
            content=f"Cancelled workflow: {execution.name}",
            category="agent",
            context=f"Workflow execution {execution.id} cancelled",
            metadata={
                'workflow_execution': json.dumps(asdict(execution)),
                'workflow_id': execution.template_id,
                'execution_id': execution.id,
                'status': 'cancelled'
            },
            tags=['workflow', 'execution', 'cancelled', execution.template_id]
        )
        
        # Move to history
        self.execution_history.append(execution)
        del self.executions[execution_id]
        
        return True
    
    async def get_workflow_templates(self) -> List[Dict[str, Any]]:
        """Get all available workflow templates"""
        templates = []
        for template in self.templates.values():
            templates.append({
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'category': template.category,
                'tags': template.tags,
                'estimated_duration': template.estimated_duration,
                'success_rate': template.success_rate,
                'usage_count': template.usage_count,
                'step_count': len(template.steps),
                'approval_required': template.approval_required,
                'rollback_enabled': template.rollback_enabled
            })
        
        return sorted(templates, key=lambda x: (x['usage_count'], x['success_rate']), reverse=True)
    
    async def create_custom_workflow(self, template_data: Dict[str, Any]) -> str:
        """Create a custom workflow template"""
        # Validate template data
        required_fields = ['name', 'description', 'category', 'steps']
        for field in required_fields:
            if field not in template_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Generate ID
        template_id = template_data.get('id') or f"custom_{int(time.time())}"
        
        # Convert steps
        steps = []
        for step_data in template_data['steps']:
            step = WorkflowStep(**step_data)
            steps.append(step)
        
        # Create template
        template = WorkflowTemplate(
            id=template_id,
            steps=steps,
            **{k: v for k, v in template_data.items() if k not in ['id', 'steps']}
        )
        
        self.templates[template_id] = template
        
        # Store in memory
        await self.storage.store_memory(
            content=f"Created custom workflow template: {template.name}",
            category="agent",
            context=f"Custom workflow template {template_id}",
            metadata={
                'workflow_template': json.dumps(asdict(template)),
                'template_id': template_id,
                'custom': True
            },
            tags=['workflow', 'template', 'custom', template.category]
        )
        
        return template_id
    
    async def get_workflow_analytics(self) -> Dict[str, Any]:
        """Get workflow system analytics"""
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for e in self.execution_history if e.status == WorkflowStatus.COMPLETED)
        
        # Template usage statistics
        template_stats = {}
        for template in self.templates.values():
            template_stats[template.id] = {
                'name': template.name,
                'usage_count': template.usage_count,
                'success_rate': template.success_rate,
                'category': template.category
            }
        
        # Recent execution trends
        recent_executions = [e for e in self.execution_history if e.start_time and e.start_time > time.time() - 86400]
        
        return {
            'total_templates': len(self.templates),
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'success_rate': successful_executions / total_executions if total_executions > 0 else 0,
            'active_executions': len(self.executions),
            'recent_executions_24h': len(recent_executions),
            'template_statistics': template_stats,
            'most_popular_templates': sorted(
                template_stats.items(),
                key=lambda x: x[1]['usage_count'],
                reverse=True
            )[:5],
            'command_sequences_learned': len(self.command_sequences)
        }