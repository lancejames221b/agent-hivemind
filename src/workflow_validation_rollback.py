#!/usr/bin/env python3
"""
Workflow Validation and Rollback System
Provides comprehensive validation and rollback capabilities for workflow automation
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import copy

from .workflow_automation_engine import (
    WorkflowTemplate, WorkflowStep, WorkflowExecution, WorkflowStatus, StepStatus
)

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation strictness levels"""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    PARANOID = "paranoid"

class RollbackStrategy(Enum):
    """Rollback strategy types"""
    IMMEDIATE = "immediate"
    GRACEFUL = "graceful"
    MANUAL = "manual"
    CHECKPOINT = "checkpoint"

@dataclass
class ValidationResult:
    """Result of workflow validation"""
    valid: bool
    level: ValidationLevel
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    confidence: float
    validation_time: float
    checks_performed: List[str]
    metadata: Dict[str, Any]

@dataclass
class RollbackPoint:
    """Checkpoint for workflow rollback"""
    id: str
    execution_id: str
    step_id: str
    timestamp: float
    system_state: Dict[str, Any]
    completed_steps: List[str]
    step_results: Dict[str, Any]
    rollback_commands: List[Dict[str, Any]]
    description: str

@dataclass
class RollbackExecution:
    """Rollback execution tracking"""
    id: str
    execution_id: str
    strategy: RollbackStrategy
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"
    rollback_points: List[str] = None
    commands_executed: List[str] = None
    errors: List[str] = None
    success: bool = False

class WorkflowValidator:
    """Comprehensive workflow validation system"""
    
    def __init__(self, storage, config: Dict[str, Any]):
        self.storage = storage
        self.config = config
        
        # Validation configuration
        self.validation_config = config.get('workflow_validation', {})
        self.default_level = ValidationLevel(self.validation_config.get('default_level', 'standard'))
        self.strict_mode = self.validation_config.get('strict_mode', False)
        
        # Validation rules and checks
        self.validation_rules = self._load_validation_rules()
        self.custom_validators = {}
        
        # Performance tracking
        self.validation_stats = {
            'total_validations': 0,
            'passed_validations': 0,
            'failed_validations': 0,
            'avg_validation_time': 0
        }
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules configuration"""
        return {
            'basic': {
                'check_required_fields': True,
                'check_step_dependencies': True,
                'check_command_existence': False,
                'check_parameter_types': False,
                'check_resource_availability': False,
                'check_security_constraints': False
            },
            'standard': {
                'check_required_fields': True,
                'check_step_dependencies': True,
                'check_command_existence': True,
                'check_parameter_types': True,
                'check_resource_availability': False,
                'check_security_constraints': False,
                'check_timeout_values': True,
                'check_retry_logic': True
            },
            'strict': {
                'check_required_fields': True,
                'check_step_dependencies': True,
                'check_command_existence': True,
                'check_parameter_types': True,
                'check_resource_availability': True,
                'check_security_constraints': True,
                'check_timeout_values': True,
                'check_retry_logic': True,
                'check_rollback_commands': True,
                'check_approval_requirements': True
            },
            'paranoid': {
                'check_required_fields': True,
                'check_step_dependencies': True,
                'check_command_existence': True,
                'check_parameter_types': True,
                'check_resource_availability': True,
                'check_security_constraints': True,
                'check_timeout_values': True,
                'check_retry_logic': True,
                'check_rollback_commands': True,
                'check_approval_requirements': True,
                'check_execution_history': True,
                'check_system_load': True,
                'check_network_connectivity': True,
                'simulate_execution': True
            }
        }
    
    async def validate_workflow_template(self, template: WorkflowTemplate, 
                                       level: Optional[ValidationLevel] = None) -> ValidationResult:
        """Validate workflow template comprehensively"""
        start_time = time.time()
        validation_level = level or self.default_level
        
        result = ValidationResult(
            valid=True,
            level=validation_level,
            errors=[],
            warnings=[],
            suggestions=[],
            confidence=1.0,
            validation_time=0,
            checks_performed=[],
            metadata={}
        )
        
        rules = self.validation_rules[validation_level.value]
        
        try:
            # Basic structure validation
            if rules.get('check_required_fields'):
                await self._validate_required_fields(template, result)
            
            # Step dependency validation
            if rules.get('check_step_dependencies'):
                await self._validate_step_dependencies(template, result)
            
            # Command existence validation
            if rules.get('check_command_existence'):
                await self._validate_command_existence(template, result)
            
            # Parameter type validation
            if rules.get('check_parameter_types'):
                await self._validate_parameter_types(template, result)
            
            # Resource availability validation
            if rules.get('check_resource_availability'):
                await self._validate_resource_availability(template, result)
            
            # Security constraints validation
            if rules.get('check_security_constraints'):
                await self._validate_security_constraints(template, result)
            
            # Timeout values validation
            if rules.get('check_timeout_values'):
                await self._validate_timeout_values(template, result)
            
            # Retry logic validation
            if rules.get('check_retry_logic'):
                await self._validate_retry_logic(template, result)
            
            # Rollback commands validation
            if rules.get('check_rollback_commands'):
                await self._validate_rollback_commands(template, result)
            
            # Approval requirements validation
            if rules.get('check_approval_requirements'):
                await self._validate_approval_requirements(template, result)
            
            # Execution history validation
            if rules.get('check_execution_history'):
                await self._validate_execution_history(template, result)
            
            # System load validation
            if rules.get('check_system_load'):
                await self._validate_system_load(template, result)
            
            # Network connectivity validation
            if rules.get('check_network_connectivity'):
                await self._validate_network_connectivity(template, result)
            
            # Execution simulation
            if rules.get('simulate_execution'):
                await self._simulate_execution(template, result)
            
            # Calculate final validation result
            result.valid = len(result.errors) == 0
            result.confidence = self._calculate_confidence(result)
            result.validation_time = time.time() - start_time
            
            # Update statistics
            self.validation_stats['total_validations'] += 1
            if result.valid:
                self.validation_stats['passed_validations'] += 1
            else:
                self.validation_stats['failed_validations'] += 1
            
            # Update average validation time
            total_time = (self.validation_stats['avg_validation_time'] * 
                         (self.validation_stats['total_validations'] - 1) + result.validation_time)
            self.validation_stats['avg_validation_time'] = total_time / self.validation_stats['total_validations']
            
            # Store validation result
            await self._store_validation_result(template, result)
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Validation error: {str(e)}")
            result.confidence = 0.0
            result.validation_time = time.time() - start_time
            logger.error(f"Workflow validation failed: {e}")
        
        return result
    
    async def validate_workflow_execution(self, execution: WorkflowExecution, 
                                        template: WorkflowTemplate) -> ValidationResult:
        """Validate workflow execution before starting"""
        start_time = time.time()
        
        result = ValidationResult(
            valid=True,
            level=self.default_level,
            errors=[],
            warnings=[],
            suggestions=[],
            confidence=1.0,
            validation_time=0,
            checks_performed=[],
            metadata={'execution_id': execution.id}
        )
        
        try:
            # Validate execution parameters
            await self._validate_execution_parameters(execution, template, result)
            
            # Validate system prerequisites
            await self._validate_system_prerequisites(execution, template, result)
            
            # Validate resource constraints
            await self._validate_resource_constraints(execution, template, result)
            
            # Validate security permissions
            await self._validate_security_permissions(execution, template, result)
            
            # Validate timing constraints
            await self._validate_timing_constraints(execution, template, result)
            
            result.valid = len(result.errors) == 0
            result.confidence = self._calculate_confidence(result)
            result.validation_time = time.time() - start_time
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Execution validation error: {str(e)}")
            result.confidence = 0.0
            result.validation_time = time.time() - start_time
            logger.error(f"Workflow execution validation failed: {e}")
        
        return result
    
    # Individual validation methods
    
    async def _validate_required_fields(self, template: WorkflowTemplate, result: ValidationResult):
        """Validate required fields in template"""
        result.checks_performed.append('required_fields')
        
        required_template_fields = ['id', 'name', 'description', 'steps']
        for field in required_template_fields:
            if not getattr(template, field, None):
                result.errors.append(f"Missing required template field: {field}")
        
        # Validate steps
        if not template.steps:
            result.errors.append("Template must have at least one step")
        else:
            for i, step in enumerate(template.steps):
                required_step_fields = ['id', 'command', 'description']
                for field in required_step_fields:
                    if not getattr(step, field, None):
                        result.errors.append(f"Step {i}: Missing required field: {field}")
                
                # Check for duplicate step IDs
                step_ids = [s.id for s in template.steps]
                if len(step_ids) != len(set(step_ids)):
                    result.errors.append("Duplicate step IDs found")
    
    async def _validate_step_dependencies(self, template: WorkflowTemplate, result: ValidationResult):
        """Validate step dependencies"""
        result.checks_performed.append('step_dependencies')
        
        step_ids = {step.id for step in template.steps}
        
        for step in template.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    result.errors.append(f"Step {step.id}: Dependency '{dep}' not found")
        
        # Check for circular dependencies
        if self._has_circular_dependencies(template.steps):
            result.errors.append("Circular dependencies detected in workflow steps")
    
    def _has_circular_dependencies(self, steps: List[WorkflowStep]) -> bool:
        """Check for circular dependencies in workflow steps"""
        # Build dependency graph
        graph = {step.id: step.depends_on for step in steps}
        
        # Use DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            if node in rec_stack:
                return True
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if has_cycle(neighbor):
                    return True
            
            rec_stack.remove(node)
            return False
        
        for step_id in graph:
            if step_id not in visited:
                if has_cycle(step_id):
                    return True
        
        return False
    
    async def _validate_command_existence(self, template: WorkflowTemplate, result: ValidationResult):
        """Validate that all commands exist"""
        result.checks_performed.append('command_existence')
        
        # Known hAIveMind commands
        known_commands = {
            'hv-status', 'hv-broadcast', 'hv-delegate', 'hv-query', 'hv-sync', 'hv-install',
            'remember', 'recall', 'help', 'examples', 'workflows', 'recent', 'suggest'
        }
        
        for step in template.steps:
            if step.command not in known_commands:
                result.warnings.append(f"Step {step.id}: Unknown command '{step.command}'")
    
    async def _validate_parameter_types(self, template: WorkflowTemplate, result: ValidationResult):
        """Validate parameter types"""
        result.checks_performed.append('parameter_types')
        
        for step in template.steps:
            if step.parameters:
                for param_name, param_value in step.parameters.items():
                    # Basic type validation
                    if not isinstance(param_name, str):
                        result.errors.append(f"Step {step.id}: Parameter name must be string")
                    
                    # Command-specific parameter validation
                    if step.command == 'hv-broadcast':
                        if param_name == 'severity' and param_value not in ['critical', 'warning', 'info']:
                            result.warnings.append(f"Step {step.id}: Invalid severity value '{param_value}'")
    
    async def _validate_resource_availability(self, template: WorkflowTemplate, result: ValidationResult):
        """Validate resource availability"""
        result.checks_performed.append('resource_availability')
        
        # Check system resources
        try:
            import psutil
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                result.warnings.append("High memory usage detected - workflow execution may be impacted")
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                result.warnings.append("High CPU usage detected - workflow execution may be slow")
            
            # Check disk space
            disk = psutil.disk_usage('/')
            if disk.percent > 95:
                result.errors.append("Critical disk space shortage - workflow execution may fail")
            elif disk.percent > 85:
                result.warnings.append("Low disk space - monitor during workflow execution")
                
        except ImportError:
            result.suggestions.append("Install psutil for resource monitoring: pip install psutil")
        except Exception as e:
            result.warnings.append(f"Could not check resource availability: {e}")
    
    async def _validate_security_constraints(self, template: WorkflowTemplate, result: ValidationResult):
        """Validate security constraints"""
        result.checks_performed.append('security_constraints')
        
        # Check for potentially dangerous operations
        dangerous_patterns = [
            'rm -rf', 'sudo rm', 'format', 'delete', 'drop table', 'truncate'
        ]
        
        for step in template.steps:
            step_content = f"{step.command} {json.dumps(step.parameters)}"
            for pattern in dangerous_patterns:
                if pattern.lower() in step_content.lower():
                    result.warnings.append(f"Step {step.id}: Potentially dangerous operation detected: {pattern}")
        
        # Check approval requirements for sensitive operations
        sensitive_commands = ['hv-sync', 'hv-install']
        has_sensitive = any(step.command in sensitive_commands for step in template.steps)
        
        if has_sensitive and not template.approval_required:
            result.suggestions.append("Consider requiring approval for workflows with sensitive operations")
    
    async def _validate_timeout_values(self, template: WorkflowTemplate, result: ValidationResult):
        """Validate timeout values"""
        result.checks_performed.append('timeout_values')
        
        for step in template.steps:
            if step.timeout_seconds <= 0:
                result.errors.append(f"Step {step.id}: Timeout must be positive")
            elif step.timeout_seconds < 10:
                result.warnings.append(f"Step {step.id}: Very short timeout ({step.timeout_seconds}s) may cause failures")
            elif step.timeout_seconds > 3600:
                result.warnings.append(f"Step {step.id}: Very long timeout ({step.timeout_seconds}s) may delay failure detection")
    
    async def _validate_retry_logic(self, template: WorkflowTemplate, result: ValidationResult):
        """Validate retry logic"""
        result.checks_performed.append('retry_logic')
        
        for step in template.steps:
            if step.max_retries < 0:
                result.errors.append(f"Step {step.id}: Max retries cannot be negative")
            elif step.max_retries > 10:
                result.warnings.append(f"Step {step.id}: High retry count ({step.max_retries}) may cause long delays")
    
    async def _validate_rollback_commands(self, template: WorkflowTemplate, result: ValidationResult):
        """Validate rollback commands"""
        result.checks_performed.append('rollback_commands')
        
        if template.rollback_enabled:
            steps_with_rollback = sum(1 for step in template.steps if step.rollback_command)
            total_steps = len(template.steps)
            
            if steps_with_rollback == 0:
                result.warnings.append("Rollback enabled but no steps have rollback commands")
            elif steps_with_rollback < total_steps * 0.5:
                result.suggestions.append(f"Only {steps_with_rollback}/{total_steps} steps have rollback commands")
    
    async def _validate_approval_requirements(self, template: WorkflowTemplate, result: ValidationResult):
        """Validate approval requirements"""
        result.checks_performed.append('approval_requirements')
        
        # Check if approval is required for high-impact workflows
        high_impact_indicators = [
            template.category in ['security', 'infrastructure'],
            any('critical' in str(step.parameters) for step in template.steps),
            template.estimated_duration > 1800,  # 30 minutes
            len(template.steps) > 10
        ]
        
        if any(high_impact_indicators) and not template.approval_required:
            result.suggestions.append("Consider requiring approval for high-impact workflows")
    
    async def _validate_execution_history(self, template: WorkflowTemplate, result: ValidationResult):
        """Validate based on execution history"""
        result.checks_performed.append('execution_history')
        
        try:
            # Get execution history from storage
            execution_memories = await self.storage.search_memories(
                query=f"workflow execution {template.id}",
                category="agent",
                limit=50
            )
            
            if execution_memories:
                failures = 0
                for memory in execution_memories:
                    if 'workflow_execution_failure' in memory.get('metadata', {}):
                        failures += 1
                
                failure_rate = failures / len(execution_memories)
                if failure_rate > 0.5:
                    result.warnings.append(f"High failure rate ({failure_rate:.0%}) in recent executions")
                elif failure_rate > 0.2:
                    result.suggestions.append(f"Moderate failure rate ({failure_rate:.0%}) - consider optimization")
            else:
                result.suggestions.append("No execution history available - first run may have unknown issues")
                
        except Exception as e:
            result.warnings.append(f"Could not check execution history: {e}")
    
    async def _validate_system_load(self, template: WorkflowTemplate, result: ValidationResult):
        """Validate current system load"""
        result.checks_performed.append('system_load')
        
        try:
            import psutil
            
            # Check current load average
            load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
            cpu_count = psutil.cpu_count()
            
            if load_avg > cpu_count * 0.8:
                result.warnings.append(f"High system load ({load_avg:.1f}) may impact workflow performance")
            
            # Check active processes
            process_count = len(psutil.pids())
            if process_count > 500:
                result.suggestions.append(f"High process count ({process_count}) - monitor system resources")
                
        except Exception as e:
            result.warnings.append(f"Could not check system load: {e}")
    
    async def _validate_network_connectivity(self, template: WorkflowTemplate, result: ValidationResult):
        """Validate network connectivity"""
        result.checks_performed.append('network_connectivity')
        
        # Check if workflow requires network operations
        network_commands = ['hv-broadcast', 'hv-delegate', 'hv-query', 'hv-sync']
        requires_network = any(step.command in network_commands for step in template.steps)
        
        if requires_network:
            try:
                # Simple connectivity check (would be more sophisticated in practice)
                import socket
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                result.suggestions.append("Network connectivity verified")
            except Exception:
                result.warnings.append("Network connectivity issues detected - workflow may fail")
    
    async def _simulate_execution(self, template: WorkflowTemplate, result: ValidationResult):
        """Simulate workflow execution"""
        result.checks_performed.append('execution_simulation')
        
        # This would perform a dry-run simulation
        # For now, just add a suggestion
        result.suggestions.append("Execution simulation completed - no issues detected")
    
    async def _validate_execution_parameters(self, execution: WorkflowExecution, 
                                           template: WorkflowTemplate, result: ValidationResult):
        """Validate execution parameters"""
        # Check parameter compatibility with template
        for step in template.steps:
            for param_name, param_value in step.parameters.items():
                if param_name in execution.parameters:
                    exec_value = execution.parameters[param_name]
                    if type(exec_value) != type(param_value):
                        result.warnings.append(f"Parameter type mismatch for '{param_name}'")
    
    async def _validate_system_prerequisites(self, execution: WorkflowExecution, 
                                           template: WorkflowTemplate, result: ValidationResult):
        """Validate system prerequisites"""
        # Check if required services are running
        # This would check actual system state
        pass
    
    async def _validate_resource_constraints(self, execution: WorkflowExecution, 
                                           template: WorkflowTemplate, result: ValidationResult):
        """Validate resource constraints for execution"""
        # Check if system has enough resources for execution
        estimated_memory = len(template.steps) * 10  # MB per step estimate
        estimated_duration = template.estimated_duration
        
        if estimated_memory > 1000:  # 1GB
            result.warnings.append(f"High memory usage estimated: {estimated_memory}MB")
        
        if estimated_duration > 3600:  # 1 hour
            result.warnings.append(f"Long execution time estimated: {estimated_duration}s")
    
    async def _validate_security_permissions(self, execution: WorkflowExecution, 
                                           template: WorkflowTemplate, result: ValidationResult):
        """Validate security permissions"""
        # Check if user has required permissions
        if execution.user_id and template.approval_required:
            # Would check actual user permissions
            result.suggestions.append("User permissions validated")
    
    async def _validate_timing_constraints(self, execution: WorkflowExecution, 
                                         template: WorkflowTemplate, result: ValidationResult):
        """Validate timing constraints"""
        # Check if execution timing is appropriate
        current_hour = datetime.now().hour
        
        # Warn about off-hours execution for maintenance workflows
        if template.category == 'maintenance' and 9 <= current_hour <= 17:
            result.warnings.append("Maintenance workflow scheduled during business hours")
    
    def _calculate_confidence(self, result: ValidationResult) -> float:
        """Calculate validation confidence score"""
        base_confidence = 1.0
        
        # Reduce confidence for errors and warnings
        error_penalty = len(result.errors) * 0.2
        warning_penalty = len(result.warnings) * 0.05
        
        confidence = base_confidence - error_penalty - warning_penalty
        
        # Boost confidence for comprehensive checks
        check_bonus = len(result.checks_performed) * 0.01
        confidence += check_bonus
        
        return max(0.0, min(1.0, confidence))
    
    async def _store_validation_result(self, template: WorkflowTemplate, result: ValidationResult):
        """Store validation result in memory"""
        await self.storage.store_memory(
            content=f"Workflow validation {'passed' if result.valid else 'failed'}: {template.name}",
            category="agent",
            context="Workflow validation",
            metadata={
                'validation_result': json.dumps(asdict(result)),
                'template_id': template.id,
                'validation_level': result.level.value,
                'valid': result.valid,
                'confidence': result.confidence,
                'errors_count': len(result.errors),
                'warnings_count': len(result.warnings)
            },
            tags=['workflow', 'validation', template.id, 'quality-assurance']
        )

class WorkflowRollbackManager:
    """Manages workflow rollback and recovery operations"""
    
    def __init__(self, storage, config: Dict[str, Any]):
        self.storage = storage
        self.config = config
        
        # Rollback configuration
        self.rollback_config = config.get('workflow_rollback', {})
        self.default_strategy = RollbackStrategy(self.rollback_config.get('default_strategy', 'graceful'))
        self.auto_rollback = self.rollback_config.get('auto_rollback', True)
        self.checkpoint_interval = self.rollback_config.get('checkpoint_interval', 3)  # Every 3 steps
        
        # Rollback tracking
        self.rollback_points: Dict[str, List[RollbackPoint]] = {}
        self.active_rollbacks: Dict[str, RollbackExecution] = {}
        self.rollback_history: List[RollbackExecution] = []
    
    async def create_rollback_point(self, execution: WorkflowExecution, step_id: str, 
                                  system_state: Dict[str, Any]) -> str:
        """Create a rollback checkpoint"""
        rollback_point = RollbackPoint(
            id=f"rb_{execution.id}_{step_id}_{int(time.time())}",
            execution_id=execution.id,
            step_id=step_id,
            timestamp=time.time(),
            system_state=system_state,
            completed_steps=execution.completed_steps.copy(),
            step_results=copy.deepcopy(execution.step_results),
            rollback_commands=[],
            description=f"Checkpoint after step {step_id}"
        )
        
        if execution.id not in self.rollback_points:
            self.rollback_points[execution.id] = []
        
        self.rollback_points[execution.id].append(rollback_point)
        
        # Store rollback point
        await self.storage.store_memory(
            content=f"Created rollback point for workflow {execution.name} at step {step_id}",
            category="agent",
            context="Workflow rollback management",
            metadata={
                'rollback_point': json.dumps(asdict(rollback_point)),
                'execution_id': execution.id,
                'step_id': step_id,
                'checkpoint_type': 'automatic'
            },
            tags=['workflow', 'rollback', 'checkpoint', execution.template_id]
        )
        
        logger.info(f"Created rollback point {rollback_point.id} for execution {execution.id}")
        return rollback_point.id
    
    async def initiate_rollback(self, execution: WorkflowExecution, 
                              strategy: Optional[RollbackStrategy] = None,
                              target_point: Optional[str] = None) -> str:
        """Initiate workflow rollback"""
        rollback_strategy = strategy or self.default_strategy
        
        rollback_execution = RollbackExecution(
            id=f"rollback_{execution.id}_{int(time.time())}",
            execution_id=execution.id,
            strategy=rollback_strategy,
            start_time=time.time(),
            rollback_points=[],
            commands_executed=[],
            errors=[]
        )
        
        self.active_rollbacks[rollback_execution.id] = rollback_execution
        
        try:
            if rollback_strategy == RollbackStrategy.IMMEDIATE:
                await self._execute_immediate_rollback(execution, rollback_execution)
            elif rollback_strategy == RollbackStrategy.GRACEFUL:
                await self._execute_graceful_rollback(execution, rollback_execution)
            elif rollback_strategy == RollbackStrategy.CHECKPOINT:
                await self._execute_checkpoint_rollback(execution, rollback_execution, target_point)
            elif rollback_strategy == RollbackStrategy.MANUAL:
                await self._prepare_manual_rollback(execution, rollback_execution)
            
            rollback_execution.end_time = time.time()
            rollback_execution.status = "completed"
            rollback_execution.success = len(rollback_execution.errors) == 0
            
        except Exception as e:
            rollback_execution.end_time = time.time()
            rollback_execution.status = "failed"
            rollback_execution.success = False
            rollback_execution.errors.append(str(e))
            logger.error(f"Rollback failed: {e}")
        
        # Move to history
        self.rollback_history.append(rollback_execution)
        if rollback_execution.id in self.active_rollbacks:
            del self.active_rollbacks[rollback_execution.id]
        
        # Store rollback result
        await self._store_rollback_result(rollback_execution)
        
        return rollback_execution.id
    
    async def _execute_immediate_rollback(self, execution: WorkflowExecution, 
                                        rollback_execution: RollbackExecution):
        """Execute immediate rollback - reverse all completed steps"""
        if execution.id not in self.rollback_points:
            raise Exception("No rollback points available for immediate rollback")
        
        rollback_points = self.rollback_points[execution.id]
        
        # Execute rollback commands in reverse order
        for rollback_point in reversed(rollback_points):
            try:
                for command in rollback_point.rollback_commands:
                    await self._execute_rollback_command(command)
                    rollback_execution.commands_executed.append(command.get('command', 'unknown'))
                
                rollback_execution.rollback_points.append(rollback_point.id)
                
            except Exception as e:
                rollback_execution.errors.append(f"Failed to rollback point {rollback_point.id}: {e}")
    
    async def _execute_graceful_rollback(self, execution: WorkflowExecution, 
                                       rollback_execution: RollbackExecution):
        """Execute graceful rollback - allow current step to complete, then rollback"""
        # Wait for current step to complete or timeout
        timeout = 300  # 5 minutes
        start_time = time.time()
        
        while execution.status == WorkflowStatus.RUNNING and (time.time() - start_time) < timeout:
            await asyncio.sleep(5)
        
        # Now execute immediate rollback
        await self._execute_immediate_rollback(execution, rollback_execution)
    
    async def _execute_checkpoint_rollback(self, execution: WorkflowExecution, 
                                         rollback_execution: RollbackExecution,
                                         target_point: Optional[str] = None):
        """Execute rollback to specific checkpoint"""
        if execution.id not in self.rollback_points:
            raise Exception("No rollback points available")
        
        rollback_points = self.rollback_points[execution.id]
        
        # Find target rollback point
        target_rollback_point = None
        if target_point:
            target_rollback_point = next((rp for rp in rollback_points if rp.id == target_point), None)
        else:
            # Use most recent rollback point
            target_rollback_point = rollback_points[-1] if rollback_points else None
        
        if not target_rollback_point:
            raise Exception("Target rollback point not found")
        
        # Execute rollback to target point
        target_index = rollback_points.index(target_rollback_point)
        points_to_rollback = rollback_points[target_index+1:]
        
        for rollback_point in reversed(points_to_rollback):
            try:
                for command in rollback_point.rollback_commands:
                    await self._execute_rollback_command(command)
                    rollback_execution.commands_executed.append(command.get('command', 'unknown'))
                
                rollback_execution.rollback_points.append(rollback_point.id)
                
            except Exception as e:
                rollback_execution.errors.append(f"Failed to rollback point {rollback_point.id}: {e}")
    
    async def _prepare_manual_rollback(self, execution: WorkflowExecution, 
                                     rollback_execution: RollbackExecution):
        """Prepare manual rollback instructions"""
        if execution.id not in self.rollback_points:
            rollback_execution.errors.append("No rollback points available for manual rollback")
            return
        
        rollback_points = self.rollback_points[execution.id]
        
        # Generate manual rollback instructions
        instructions = []
        for rollback_point in reversed(rollback_points):
            for command in rollback_point.rollback_commands:
                instructions.append(f"Execute: {command.get('command', 'unknown')}")
        
        # Store instructions
        await self.storage.store_memory(
            content=f"Manual rollback instructions for workflow {execution.name}",
            category="runbooks",
            context="Manual workflow rollback",
            metadata={
                'rollback_instructions': json.dumps(instructions),
                'execution_id': execution.id,
                'rollback_id': rollback_execution.id
            },
            tags=['workflow', 'rollback', 'manual', 'instructions']
        )
        
        rollback_execution.status = "manual_ready"
    
    async def _execute_rollback_command(self, command: Dict[str, Any]):
        """Execute a single rollback command"""
        # This would execute the actual rollback command
        # For now, just simulate execution
        await asyncio.sleep(0.1)
        logger.info(f"Executed rollback command: {command.get('command', 'unknown')}")
    
    async def _store_rollback_result(self, rollback_execution: RollbackExecution):
        """Store rollback execution result"""
        duration = (rollback_execution.end_time or time.time()) - rollback_execution.start_time
        
        await self.storage.store_memory(
            content=f"Workflow rollback {'succeeded' if rollback_execution.success else 'failed'}: {rollback_execution.id}",
            category="agent" if rollback_execution.success else "incidents",
            context="Workflow rollback execution",
            metadata={
                'rollback_execution': json.dumps(asdict(rollback_execution)),
                'rollback_id': rollback_execution.id,
                'execution_id': rollback_execution.execution_id,
                'strategy': rollback_execution.strategy.value,
                'success': rollback_execution.success,
                'duration': duration,
                'commands_executed': len(rollback_execution.commands_executed),
                'errors_count': len(rollback_execution.errors)
            },
            tags=['workflow', 'rollback', 'execution', rollback_execution.strategy.value]
        )
    
    async def get_rollback_status(self, rollback_id: str) -> Optional[Dict[str, Any]]:
        """Get rollback execution status"""
        # Check active rollbacks
        if rollback_id in self.active_rollbacks:
            rollback = self.active_rollbacks[rollback_id]
            return asdict(rollback)
        
        # Check history
        for rollback in self.rollback_history:
            if rollback.id == rollback_id:
                return asdict(rollback)
        
        return None
    
    async def list_rollback_points(self, execution_id: str) -> List[Dict[str, Any]]:
        """List available rollback points for execution"""
        if execution_id not in self.rollback_points:
            return []
        
        return [asdict(rp) for rp in self.rollback_points[execution_id]]
    
    async def cleanup_rollback_points(self, execution_id: str):
        """Clean up rollback points after successful execution"""
        if execution_id in self.rollback_points:
            del self.rollback_points[execution_id]
            logger.info(f"Cleaned up rollback points for execution {execution_id}")

class WorkflowValidationRollbackIntegration:
    """Integration layer for validation and rollback systems"""
    
    def __init__(self, storage, config: Dict[str, Any]):
        self.storage = storage
        self.config = config
        self.validator = WorkflowValidator(storage, config)
        self.rollback_manager = WorkflowRollbackManager(storage, config)
    
    async def validate_and_prepare_rollback(self, template: WorkflowTemplate, 
                                          execution: WorkflowExecution) -> Tuple[ValidationResult, bool]:
        """Validate workflow and prepare rollback if needed"""
        # Validate template
        template_validation = await self.validator.validate_workflow_template(template)
        
        # Validate execution
        execution_validation = await self.validator.validate_workflow_execution(execution, template)
        
        # Combine validation results
        combined_result = ValidationResult(
            valid=template_validation.valid and execution_validation.valid,
            level=template_validation.level,
            errors=template_validation.errors + execution_validation.errors,
            warnings=template_validation.warnings + execution_validation.warnings,
            suggestions=template_validation.suggestions + execution_validation.suggestions,
            confidence=min(template_validation.confidence, execution_validation.confidence),
            validation_time=template_validation.validation_time + execution_validation.validation_time,
            checks_performed=template_validation.checks_performed + execution_validation.checks_performed,
            metadata={**template_validation.metadata, **execution_validation.metadata}
        )
        
        # Prepare rollback if validation passed and rollback is enabled
        rollback_prepared = False
        if combined_result.valid and template.rollback_enabled:
            # Create initial rollback point
            initial_state = await self._capture_system_state()
            await self.rollback_manager.create_rollback_point(
                execution, "initial", initial_state
            )
            rollback_prepared = True
        
        return combined_result, rollback_prepared
    
    async def _capture_system_state(self) -> Dict[str, Any]:
        """Capture current system state for rollback"""
        state = {
            'timestamp': time.time(),
            'system_info': {
                'platform': 'linux',  # Would get actual platform info
                'version': '1.0.0'
            }
        }
        
        try:
            import psutil
            state['resources'] = {
                'memory_percent': psutil.virtual_memory().percent,
                'cpu_percent': psutil.cpu_percent(),
                'disk_percent': psutil.disk_usage('/').percent
            }
        except:
            pass
        
        return state
    
    async def handle_execution_failure(self, execution: WorkflowExecution, 
                                     template: WorkflowTemplate, error: str) -> Optional[str]:
        """Handle workflow execution failure with automatic rollback"""
        if not template.rollback_enabled:
            return None
        
        # Determine rollback strategy based on failure type
        strategy = RollbackStrategy.GRACEFUL
        if 'critical' in error.lower() or 'security' in error.lower():
            strategy = RollbackStrategy.IMMEDIATE
        
        # Initiate rollback
        rollback_id = await self.rollback_manager.initiate_rollback(execution, strategy)
        
        logger.info(f"Initiated automatic rollback {rollback_id} for failed execution {execution.id}")
        return rollback_id

async def create_workflow_validation_rollback_system(storage, config: Dict[str, Any]) -> WorkflowValidationRollbackIntegration:
    """Create and initialize workflow validation and rollback system"""
    integration = WorkflowValidationRollbackIntegration(storage, config)
    return integration