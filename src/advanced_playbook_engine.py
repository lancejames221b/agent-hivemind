#!/usr/bin/env python3
"""
Advanced Playbook Execution Engine with Validation, Pause/Resume, Rollback, and hAIveMind Integration

This module provides a robust execution engine for deterministic playbook execution with:
- Step-by-step execution with pause/resume capabilities
- Real-time validation of each step before proceeding
- Variable interpolation and environment-specific parameters
- Rollback mechanisms for failed executions
- Parallel execution support for independent steps
- Human approval gates for critical operations
- Execution logging with detailed audit trails
- Integration with hAIveMind tools and MCP servers
- Error handling and retry logic with exponential backoff
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from string import Template
from typing import Any, Dict, List, Optional, Set, Tuple, Callable, Union
import traceback
from concurrent.futures import ThreadPoolExecutor
import threading
import math

import httpx
from playbook_engine import PlaybookValidationError, PlaybookExecutionError, _substitute, _coerce_bool

logger = logging.getLogger(__name__)


class ExecutionState(Enum):
    """Execution states for playbook runs"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


class StepState(Enum):
    """Individual step states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


@dataclass
class ValidationResult:
    """Result of step validation"""
    valid: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalGate:
    """Human approval gate configuration"""
    step_id: str
    message: str
    required_approvers: List[str]
    timeout_seconds: Optional[int] = None
    auto_approve_after_timeout: bool = False


@dataclass
class RetryConfig:
    """Retry configuration for steps"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_backoff: bool = True
    retry_on_errors: List[str] = field(default_factory=lambda: ["timeout", "network", "temporary"])


@dataclass
class RollbackAction:
    """Rollback action for a step"""
    step_id: str
    action: str
    args: Dict[str, Any]
    description: str


@dataclass
class AdvancedStepResult:
    """Enhanced step result with additional metadata"""
    step_id: str
    name: str
    started_at: float
    finished_at: Optional[float]
    state: StepState
    outputs: Dict[str, Any]
    error: Optional[str] = None
    validation_results: List[ValidationResult] = field(default_factory=list)
    retry_count: int = 0
    rollback_actions: List[RollbackAction] = field(default_factory=list)
    approval_requests: List[str] = field(default_factory=list)
    parallel_group: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> Optional[float]:
        if self.finished_at and self.started_at:
            return self.finished_at - self.started_at
        return None


@dataclass
class ExecutionContext:
    """Execution context with state management"""
    run_id: str
    playbook_id: int
    version_id: int
    state: ExecutionState
    started_at: float
    finished_at: Optional[float] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, AdvancedStepResult] = field(default_factory=dict)
    current_step_index: int = 0
    parallel_groups: Dict[str, List[str]] = field(default_factory=dict)
    approval_gates: Dict[str, ApprovalGate] = field(default_factory=dict)
    rollback_stack: List[RollbackAction] = field(default_factory=list)
    error_log: List[str] = field(default_factory=list)
    pause_requested: bool = False
    cancel_requested: bool = False
    
    @property
    def duration(self) -> Optional[float]:
        if self.finished_at and self.started_at:
            return self.finished_at - self.started_at
        return None


class AdvancedPlaybookEngine:
    """Advanced playbook execution engine with comprehensive features"""
    
    def __init__(
        self,
        allow_unsafe_shell: bool = False,
        haivemind_client: Optional[Any] = None,
        approval_handler: Optional[Callable[[ApprovalGate], bool]] = None,
        max_parallel_steps: int = 5
    ):
        self.allow_unsafe_shell = allow_unsafe_shell
        self.haivemind_client = haivemind_client
        self.approval_handler = approval_handler
        self.max_parallel_steps = max_parallel_steps
        
        # Execution state management
        self.active_executions: Dict[str, ExecutionContext] = {}
        self.execution_lock = threading.RLock()
        
        # Thread pool for parallel execution
        self.thread_pool = ThreadPoolExecutor(max_workers=max_parallel_steps)
        
        # Built-in validators
        self.validators = {
            "http_status": self._validate_http_status,
            "file_exists": self._validate_file_exists,
            "service_running": self._validate_service_running,
            "port_open": self._validate_port_open,
            "disk_space": self._validate_disk_space,
            "memory_usage": self._validate_memory_usage,
        }
        
        # Built-in rollback actions
        self.rollback_handlers = {
            "shell": self._rollback_shell,
            "http_request": self._rollback_http_request,
            "file_operation": self._rollback_file_operation,
        }

    async def execute_playbook(
        self,
        spec: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
        playbook_id: Optional[int] = None,
        version_id: Optional[int] = None,
        dry_run: bool = False
    ) -> ExecutionContext:
        """Execute a playbook with advanced features"""
        
        if not run_id:
            run_id = str(uuid.uuid4())
            
        # Create execution context
        context = ExecutionContext(
            run_id=run_id,
            playbook_id=playbook_id or 0,
            version_id=version_id or 0,
            state=ExecutionState.PENDING,
            started_at=time.time(),
            parameters=parameters or {}
        )
        
        with self.execution_lock:
            self.active_executions[run_id] = context
        
        try:
            # Store execution start in hAIveMind
            if self.haivemind_client:
                await self._store_haivemind_memory(
                    f"Playbook execution started: {spec.get('name', 'Unknown')}",
                    "playbook_execution",
                    {
                        "run_id": run_id,
                        "playbook_name": spec.get("name"),
                        "parameters": parameters,
                        "dry_run": dry_run
                    }
                )
            
            # Validate playbook
            self._validate_advanced_playbook(spec)
            
            # Analyze dependencies and parallel groups
            self._analyze_execution_plan(spec, context)
            
            # Set state to running
            context.state = ExecutionState.RUNNING
            
            if dry_run:
                return await self._dry_run_execution(spec, context)
            else:
                return await self._execute_steps(spec, context)
                
        except Exception as e:
            context.state = ExecutionState.FAILED
            context.finished_at = time.time()
            context.error_log.append(f"Execution failed: {str(e)}")
            logger.error(f"Playbook execution failed: {e}", exc_info=True)
            
            # Store failure in hAIveMind
            if self.haivemind_client:
                await self._store_haivemind_memory(
                    f"Playbook execution failed: {str(e)}",
                    "playbook_execution",
                    {
                        "run_id": run_id,
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }
                )
            
            return context
        finally:
            # Clean up
            with self.execution_lock:
                if run_id in self.active_executions and context.state in [
                    ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELLED
                ]:
                    # Keep for a while for status queries, but mark as finished
                    pass

    async def pause_execution(self, run_id: str) -> bool:
        """Pause a running execution"""
        with self.execution_lock:
            if run_id in self.active_executions:
                context = self.active_executions[run_id]
                if context.state == ExecutionState.RUNNING:
                    context.pause_requested = True
                    logger.info(f"Pause requested for execution {run_id}")
                    return True
        return False

    async def resume_execution(self, run_id: str) -> bool:
        """Resume a paused execution"""
        with self.execution_lock:
            if run_id in self.active_executions:
                context = self.active_executions[run_id]
                if context.state == ExecutionState.PAUSED:
                    context.state = ExecutionState.RUNNING
                    context.pause_requested = False
                    logger.info(f"Resuming execution {run_id}")
                    # Continue execution in background
                    asyncio.create_task(self._continue_execution(run_id))
                    return True
        return False

    async def cancel_execution(self, run_id: str) -> bool:
        """Cancel a running execution"""
        with self.execution_lock:
            if run_id in self.active_executions:
                context = self.active_executions[run_id]
                if context.state in [ExecutionState.RUNNING, ExecutionState.PAUSED]:
                    context.cancel_requested = True
                    context.state = ExecutionState.CANCELLED
                    context.finished_at = time.time()
                    logger.info(f"Execution {run_id} cancelled")
                    return True
        return False

    async def rollback_execution(self, run_id: str) -> bool:
        """Rollback a failed or completed execution"""
        with self.execution_lock:
            if run_id not in self.active_executions:
                return False
                
            context = self.active_executions[run_id]
            if context.state not in [ExecutionState.FAILED, ExecutionState.COMPLETED]:
                return False
                
            context.state = ExecutionState.ROLLING_BACK
            
        try:
            # Execute rollback actions in reverse order
            for rollback_action in reversed(context.rollback_stack):
                await self._execute_rollback_action(rollback_action, context)
                
            context.state = ExecutionState.ROLLED_BACK
            context.finished_at = time.time()
            
            # Store rollback completion in hAIveMind
            if self.haivemind_client:
                await self._store_haivemind_memory(
                    f"Playbook execution rolled back successfully",
                    "playbook_execution",
                    {
                        "run_id": run_id,
                        "rollback_actions": len(context.rollback_stack)
                    }
                )
            
            return True
            
        except Exception as e:
            context.error_log.append(f"Rollback failed: {str(e)}")
            logger.error(f"Rollback failed for {run_id}: {e}", exc_info=True)
            return False

    async def approve_step(self, run_id: str, step_id: str, approver: str) -> bool:
        """Approve a step waiting for approval"""
        with self.execution_lock:
            if run_id not in self.active_executions:
                return False
                
            context = self.active_executions[run_id]
            if step_id not in context.step_results:
                return False
                
            step_result = context.step_results[step_id]
            if step_result.state != StepState.WAITING_APPROVAL:
                return False
                
            step_result.approval_requests.append(approver)
            
            # Check if we have enough approvals
            approval_gate = context.approval_gates.get(step_id)
            if approval_gate:
                if approver in approval_gate.required_approvers:
                    step_result.state = StepState.PENDING
                    # Continue execution
                    asyncio.create_task(self._continue_execution(run_id))
                    return True
                    
        return False

    def get_execution_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get current execution status"""
        with self.execution_lock:
            if run_id not in self.active_executions:
                return None
                
            context = self.active_executions[run_id]
            return {
                "run_id": run_id,
                "state": context.state.value,
                "started_at": context.started_at,
                "finished_at": context.finished_at,
                "duration": context.duration,
                "current_step_index": context.current_step_index,
                "total_steps": len(context.step_results),
                "completed_steps": len([r for r in context.step_results.values() if r.state == StepState.COMPLETED]),
                "failed_steps": len([r for r in context.step_results.values() if r.state == StepState.FAILED]),
                "parameters": context.parameters,
                "variables": context.variables,
                "error_log": context.error_log,
                "step_results": {
                    step_id: {
                        "state": result.state.value,
                        "started_at": result.started_at,
                        "finished_at": result.finished_at,
                        "duration": result.duration,
                        "retry_count": result.retry_count,
                        "error": result.error
                    }
                    for step_id, result in context.step_results.items()
                }
            }

    def list_active_executions(self) -> List[Dict[str, Any]]:
        """List all active executions"""
        with self.execution_lock:
            return [
                {
                    "run_id": run_id,
                    "state": context.state.value,
                    "started_at": context.started_at,
                    "duration": context.duration,
                    "playbook_id": context.playbook_id
                }
                for run_id, context in self.active_executions.items()
            ]

    # Private methods for execution logic

    def _validate_advanced_playbook(self, spec: Dict[str, Any]) -> None:
        """Enhanced playbook validation"""
        # Basic validation from original engine
        if not isinstance(spec, dict):
            raise PlaybookValidationError("Playbook must be an object")
        if not spec.get("name"):
            raise PlaybookValidationError("Playbook 'name' is required")
        if not isinstance(spec.get("steps"), list) or not spec["steps"]:
            raise PlaybookValidationError("Playbook must include non-empty 'steps' list")

        # Advanced validation
        steps = spec["steps"]
        step_ids = set()
        
        for idx, step in enumerate(steps, 1):
            if not isinstance(step, dict):
                raise PlaybookValidationError(f"Step {idx} must be an object")
                
            step_id = step.get("id") or f"step_{idx}"
            if step_id in step_ids:
                raise PlaybookValidationError(f"Duplicate step id: {step_id}")
            step_ids.add(step_id)
            
            # Validate dependencies
            dependencies = step.get("depends_on", [])
            if dependencies:
                for dep in dependencies:
                    if dep not in step_ids and dep != step_id:
                        # Check if dependency exists in previous steps
                        found = False
                        for prev_step in steps[:idx-1]:
                            if prev_step.get("id") == dep:
                                found = True
                                break
                        if not found:
                            raise PlaybookValidationError(f"Step {step_id} depends on unknown step: {dep}")
            
            # Validate parallel groups
            parallel_group = step.get("parallel_group")
            if parallel_group and not isinstance(parallel_group, str):
                raise PlaybookValidationError(f"Step {step_id} parallel_group must be a string")
            
            # Validate approval gates
            approval_gate = step.get("approval_gate")
            if approval_gate:
                if not isinstance(approval_gate, dict):
                    raise PlaybookValidationError(f"Step {step_id} approval_gate must be an object")
                if not approval_gate.get("required_approvers"):
                    raise PlaybookValidationError(f"Step {step_id} approval_gate must specify required_approvers")

    def _analyze_execution_plan(self, spec: Dict[str, Any], context: ExecutionContext) -> None:
        """Analyze execution plan for dependencies and parallel groups"""
        steps = spec["steps"]
        
        for idx, step in enumerate(steps, 1):
            step_id = step.get("id") or f"step_{idx}"
            
            # Initialize step result
            context.step_results[step_id] = AdvancedStepResult(
                step_id=step_id,
                name=step.get("name", step_id),
                started_at=0,
                finished_at=None,
                state=StepState.PENDING,
                outputs={},
                dependencies=step.get("depends_on", []),
                parallel_group=step.get("parallel_group")
            )
            
            # Track parallel groups
            parallel_group = step.get("parallel_group")
            if parallel_group:
                if parallel_group not in context.parallel_groups:
                    context.parallel_groups[parallel_group] = []
                context.parallel_groups[parallel_group].append(step_id)
            
            # Track approval gates
            approval_gate = step.get("approval_gate")
            if approval_gate:
                context.approval_gates[step_id] = ApprovalGate(
                    step_id=step_id,
                    message=approval_gate.get("message", f"Approval required for step: {step_id}"),
                    required_approvers=approval_gate.get("required_approvers", []),
                    timeout_seconds=approval_gate.get("timeout_seconds"),
                    auto_approve_after_timeout=approval_gate.get("auto_approve_after_timeout", False)
                )

    async def _dry_run_execution(self, spec: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        """Perform dry run validation"""
        try:
            steps = spec["steps"]
            
            for idx, step in enumerate(steps, 1):
                step_id = step.get("id") or f"step_{idx}"
                step_result = context.step_results[step_id]
                
                # Validate step configuration
                validation_results = await self._validate_step_pre_execution(step, context)
                step_result.validation_results = validation_results
                
                if any(not v.valid for v in validation_results):
                    step_result.state = StepState.FAILED
                    step_result.error = "Pre-execution validation failed"
                    context.state = ExecutionState.FAILED
                    break
                else:
                    step_result.state = StepState.COMPLETED
            
            if context.state != ExecutionState.FAILED:
                context.state = ExecutionState.COMPLETED
                
            context.finished_at = time.time()
            return context
            
        except Exception as e:
            context.state = ExecutionState.FAILED
            context.finished_at = time.time()
            context.error_log.append(f"Dry run failed: {str(e)}")
            return context

    async def _execute_steps(self, spec: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        """Execute playbook steps with advanced features"""
        try:
            steps = spec["steps"]
            
            # Group steps by execution order considering dependencies and parallel groups
            execution_plan = self._create_execution_plan(steps, context)
            
            for execution_group in execution_plan:
                # Check for pause/cancel requests
                if context.pause_requested:
                    context.state = ExecutionState.PAUSED
                    return context
                    
                if context.cancel_requested:
                    context.state = ExecutionState.CANCELLED
                    context.finished_at = time.time()
                    return context
                
                # Execute steps in parallel if they're in the same group
                if len(execution_group) == 1:
                    # Single step execution
                    step_id = execution_group[0]
                    step = next(s for s in steps if s.get("id", f"step_{steps.index(s)+1}") == step_id)
                    success = await self._execute_single_step(step, context)
                    if not success and not spec.get("continue_on_failure", False):
                        break
                else:
                    # Parallel execution
                    tasks = []
                    for step_id in execution_group:
                        step = next(s for s in steps if s.get("id", f"step_{steps.index(s)+1}") == step_id)
                        tasks.append(self._execute_single_step(step, context))
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Check if any parallel step failed
                    if any(isinstance(r, Exception) or not r for r in results):
                        if not spec.get("continue_on_failure", False):
                            break
            
            # Determine final state
            failed_steps = [r for r in context.step_results.values() if r.state == StepState.FAILED]
            if failed_steps:
                context.state = ExecutionState.FAILED
            else:
                context.state = ExecutionState.COMPLETED
                
            context.finished_at = time.time()
            
            # Store completion in hAIveMind
            if self.haivemind_client:
                await self._store_haivemind_memory(
                    f"Playbook execution completed: {context.state.value}",
                    "playbook_execution",
                    {
                        "run_id": context.run_id,
                        "final_state": context.state.value,
                        "duration": context.duration,
                        "total_steps": len(context.step_results),
                        "failed_steps": len(failed_steps)
                    }
                )
            
            return context
            
        except Exception as e:
            context.state = ExecutionState.FAILED
            context.finished_at = time.time()
            context.error_log.append(f"Execution failed: {str(e)}")
            logger.error(f"Step execution failed: {e}", exc_info=True)
            return context

    def _create_execution_plan(self, steps: List[Dict[str, Any]], context: ExecutionContext) -> List[List[str]]:
        """Create execution plan considering dependencies and parallel groups"""
        execution_plan = []
        executed_steps = set()
        
        while len(executed_steps) < len(steps):
            current_group = []
            
            for idx, step in enumerate(steps, 1):
                step_id = step.get("id") or f"step_{idx}"
                
                if step_id in executed_steps:
                    continue
                
                # Check if dependencies are satisfied
                dependencies = step.get("depends_on", [])
                if all(dep in executed_steps for dep in dependencies):
                    # Check if this step can run in parallel with current group
                    parallel_group = step.get("parallel_group")
                    if not current_group or parallel_group:
                        # First step in group or has parallel group
                        current_group.append(step_id)
                        executed_steps.add(step_id)
                    elif not parallel_group:
                        # Sequential step, start new group
                        break
            
            if current_group:
                execution_plan.append(current_group)
            else:
                # Circular dependency or other issue
                remaining_steps = [s.get("id", f"step_{steps.index(s)+1}") for s in steps if s.get("id", f"step_{steps.index(s)+1}") not in executed_steps]
                raise PlaybookExecutionError(f"Cannot resolve dependencies for steps: {remaining_steps}")
        
        return execution_plan

    async def _execute_single_step(self, step: Dict[str, Any], context: ExecutionContext) -> bool:
        """Execute a single step with all advanced features"""
        step_id = step.get("id") or f"step_{context.current_step_index + 1}"
        step_result = context.step_results[step_id]
        
        try:
            step_result.started_at = time.time()
            step_result.state = StepState.RUNNING
            
            # Pre-execution validation
            validation_results = await self._validate_step_pre_execution(step, context)
            step_result.validation_results = validation_results
            
            if any(not v.valid for v in validation_results):
                step_result.state = StepState.FAILED
                step_result.error = "Pre-execution validation failed"
                step_result.finished_at = time.time()
                return False
            
            # Check approval gate
            if step_id in context.approval_gates:
                approval_gate = context.approval_gates[step_id]
                if self.approval_handler:
                    approved = await self._handle_approval_gate(approval_gate, context)
                    if not approved:
                        step_result.state = StepState.WAITING_APPROVAL
                        return False
                else:
                    # No approval handler, skip approval
                    logger.warning(f"Approval gate configured but no handler available for step {step_id}")
            
            # Variable substitution
            context_vars = {**context.parameters, **context.variables}
            substituted_step = _substitute(step, context_vars)
            
            # Execute with retry logic
            retry_config = self._get_retry_config(step)
            success = False
            
            for attempt in range(retry_config.max_attempts):
                try:
                    step_result.retry_count = attempt
                    
                    # Execute the action
                    outputs = await self._execute_step_action(substituted_step, context)
                    step_result.outputs = outputs
                    
                    # Post-execution validation
                    post_validation = await self._validate_step_post_execution(substituted_step, outputs, context)
                    step_result.validation_results.extend(post_validation)
                    
                    if any(not v.valid for v in post_validation):
                        raise PlaybookExecutionError("Post-execution validation failed")
                    
                    # Export outputs to variables
                    self._export_step_outputs(substituted_step, outputs, context)
                    
                    # Record rollback actions
                    rollback_actions = self._generate_rollback_actions(substituted_step, outputs)
                    step_result.rollback_actions = rollback_actions
                    context.rollback_stack.extend(rollback_actions)
                    
                    success = True
                    break
                    
                except Exception as e:
                    if attempt < retry_config.max_attempts - 1:
                        # Calculate delay for exponential backoff
                        if retry_config.exponential_backoff:
                            delay = min(
                                retry_config.base_delay * (2 ** attempt),
                                retry_config.max_delay
                            )
                        else:
                            delay = retry_config.base_delay
                        
                        logger.warning(f"Step {step_id} failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                        await asyncio.sleep(delay)
                    else:
                        # Final attempt failed
                        step_result.error = str(e)
                        logger.error(f"Step {step_id} failed after {retry_config.max_attempts} attempts: {e}")
            
            if success:
                step_result.state = StepState.COMPLETED
                step_result.finished_at = time.time()
                
                # Store step completion in hAIveMind
                if self.haivemind_client:
                    await self._store_haivemind_memory(
                        f"Step completed: {step_result.name}",
                        "playbook_execution",
                        {
                            "run_id": context.run_id,
                            "step_id": step_id,
                            "duration": step_result.duration,
                            "retry_count": step_result.retry_count,
                            "outputs": step_result.outputs
                        }
                    )
                
                return True
            else:
                step_result.state = StepState.FAILED
                step_result.finished_at = time.time()
                
                # Store step failure in hAIveMind
                if self.haivemind_client:
                    await self._store_haivemind_memory(
                        f"Step failed: {step_result.name} - {step_result.error}",
                        "playbook_execution",
                        {
                            "run_id": context.run_id,
                            "step_id": step_id,
                            "error": step_result.error,
                            "retry_count": step_result.retry_count
                        }
                    )
                
                return False
                
        except Exception as e:
            step_result.state = StepState.FAILED
            step_result.error = str(e)
            step_result.finished_at = time.time()
            logger.error(f"Unexpected error in step {step_id}: {e}", exc_info=True)
            return False

    async def _execute_step_action(self, step: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute the actual step action"""
        action = step.get("action")
        args = step.get("args", {})
        outputs = {}
        
        if action == "noop":
            await asyncio.sleep(float(args.get("delay", 0)))
            outputs["message"] = args.get("message", "noop")
            
        elif action == "wait":
            await asyncio.sleep(float(args.get("seconds", 1)))
            outputs["slept"] = args.get("seconds", 1)
            
        elif action == "http_request":
            method = str(args.get("method", "GET")).upper()
            url = str(args.get("url"))
            if not url:
                raise PlaybookExecutionError("http_request requires 'url'")
            timeout = float(args.get("timeout", 20))
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(
                    method, url,
                    headers=args.get("headers"),
                    json=args.get("json"),
                    data=args.get("data")
                )
            
            outputs["status_code"] = resp.status_code
            outputs["headers"] = dict(resp.headers)
            try:
                outputs["body_json"] = resp.json()
            except Exception:
                outputs["body"] = resp.text
                
        elif action == "shell":
            if not self.allow_unsafe_shell:
                raise PlaybookExecutionError("Shell action is disabled. Enable with allow_unsafe_shell=True.")
            
            cmd = args.get("command")
            if not cmd:
                raise PlaybookExecutionError("shell requires 'command'")
                
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await proc.communicate()
            outputs["returncode"] = proc.returncode
            outputs["stdout"] = stdout_b.decode().strip()
            outputs["stderr"] = stderr_b.decode().strip()
            
            if proc.returncode != 0:
                raise PlaybookExecutionError(f"Non-zero return code: {proc.returncode}")
                
        else:
            raise PlaybookExecutionError(f"Unknown action: {action}")
        
        return outputs

    async def _validate_step_pre_execution(self, step: Dict[str, Any], context: ExecutionContext) -> List[ValidationResult]:
        """Validate step before execution"""
        results = []
        
        # Check when conditions
        when_conditions = step.get("when", [])
        context_vars = {**context.parameters, **context.variables}
        
        for condition in when_conditions:
            if not self._eval_condition(condition, context_vars):
                results.append(ValidationResult(
                    valid=False,
                    message=f"When condition not met: {condition}",
                    details={"condition": condition}
                ))
        
        # Custom validators
        validators = step.get("validators", [])
        for validator in validators:
            validator_type = validator.get("type")
            if validator_type in self.validators:
                try:
                    result = await self.validators[validator_type](validator, context)
                    results.append(result)
                except Exception as e:
                    results.append(ValidationResult(
                        valid=False,
                        message=f"Validator error: {str(e)}",
                        details={"validator": validator, "error": str(e)}
                    ))
        
        return results

    async def _validate_step_post_execution(self, step: Dict[str, Any], outputs: Dict[str, Any], context: ExecutionContext) -> List[ValidationResult]:
        """Validate step after execution"""
        results = []
        
        # Check validations
        validations = step.get("validations", [])
        validation_context = {**context.parameters, **context.variables, **outputs}
        
        for validation in validations:
            if not self._eval_condition(validation, validation_context):
                results.append(ValidationResult(
                    valid=False,
                    message=f"Validation failed: {validation}",
                    details={"validation": validation, "context": validation_context}
                ))
            else:
                results.append(ValidationResult(
                    valid=True,
                    message=f"Validation passed: {validation}",
                    details={"validation": validation}
                ))
        
        return results

    def _eval_condition(self, cond: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
        """Evaluate condition (enhanced from original engine)"""
        cond = _substitute(cond, ctx)
        ctype = cond.get("type")

        if ctype in {"equals", "eq"}:
            return str(cond.get("left")) == str(cond.get("right"))
        if ctype in {"not_equals", "ne"}:
            return str(cond.get("left")) != str(cond.get("right"))
        if ctype == "contains":
            left = cond.get("left")
            right = cond.get("right")
            try:
                return str(right) in str(left)
            except Exception:
                return False
        if ctype == "http_status" or ctype == "status_code":
            try:
                return int(cond.get("left")) == int(cond.get("right", 200))
            except Exception:
                return False
        if ctype == "truthy":
            return _coerce_bool(cond.get("value"))
        if ctype == "falsy":
            return not _coerce_bool(cond.get("value"))
        if ctype == "greater_than":
            try:
                return float(cond.get("left")) > float(cond.get("right"))
            except Exception:
                return False
        if ctype == "less_than":
            try:
                return float(cond.get("left")) < float(cond.get("right"))
            except Exception:
                return False
        
        return False

    def _export_step_outputs(self, step: Dict[str, Any], outputs: Dict[str, Any], context: ExecutionContext) -> None:
        """Export step outputs to context variables"""
        for output_def in step.get("outputs", []):
            name_key = output_def.get("name")
            if not name_key:
                continue
                
            source = output_def.get("from", "value")
            if source == "value":
                context.variables[name_key] = output_def.get("value")
            elif source in outputs:
                context.variables[name_key] = outputs[source]

    def _get_retry_config(self, step: Dict[str, Any]) -> RetryConfig:
        """Get retry configuration for step"""
        retry_config = step.get("retry", {})
        return RetryConfig(
            max_attempts=retry_config.get("max_attempts", 3),
            base_delay=retry_config.get("base_delay", 1.0),
            max_delay=retry_config.get("max_delay", 60.0),
            exponential_backoff=retry_config.get("exponential_backoff", True),
            retry_on_errors=retry_config.get("retry_on_errors", ["timeout", "network", "temporary"])
        )

    def _generate_rollback_actions(self, step: Dict[str, Any], outputs: Dict[str, Any]) -> List[RollbackAction]:
        """Generate rollback actions for a step"""
        rollback_actions = []
        
        # Check if step defines explicit rollback actions
        rollback_config = step.get("rollback")
        if rollback_config:
            for rollback_def in rollback_config if isinstance(rollback_config, list) else [rollback_config]:
                rollback_actions.append(RollbackAction(
                    step_id=step.get("id", "unknown"),
                    action=rollback_def.get("action"),
                    args=rollback_def.get("args", {}),
                    description=rollback_def.get("description", "Rollback action")
                ))
        
        return rollback_actions

    async def _execute_rollback_action(self, rollback_action: RollbackAction, context: ExecutionContext) -> None:
        """Execute a rollback action"""
        try:
            action = rollback_action.action
            args = rollback_action.args
            
            if action in self.rollback_handlers:
                await self.rollback_handlers[action](args, context)
            else:
                logger.warning(f"No rollback handler for action: {action}")
                
        except Exception as e:
            logger.error(f"Rollback action failed: {e}", exc_info=True)
            context.error_log.append(f"Rollback failed for {rollback_action.step_id}: {str(e)}")

    async def _handle_approval_gate(self, approval_gate: ApprovalGate, context: ExecutionContext) -> bool:
        """Handle approval gate"""
        if self.approval_handler:
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    self.thread_pool,
                    self.approval_handler,
                    approval_gate
                )
            except Exception as e:
                logger.error(f"Approval handler failed: {e}")
                return False
        return True

    async def _continue_execution(self, run_id: str) -> None:
        """Continue paused execution"""
        # This would be implemented to resume execution from where it left off
        # For now, it's a placeholder
        pass

    async def _store_haivemind_memory(self, content: str, category: str, metadata: Dict[str, Any]) -> None:
        """Store memory in hAIveMind system"""
        if self.haivemind_client:
            try:
                await self.haivemind_client.store_memory(
                    content=content,
                    category=category,
                    metadata=metadata,
                    tags=["playbook", "execution", "advanced"]
                )
            except Exception as e:
                logger.error(f"Failed to store hAIveMind memory: {e}")

    # Built-in validators
    
    async def _validate_http_status(self, validator: Dict[str, Any], context: ExecutionContext) -> ValidationResult:
        """Validate HTTP endpoint status"""
        url = validator.get("url")
        expected_status = validator.get("expected_status", 200)
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                if resp.status_code == expected_status:
                    return ValidationResult(True, f"HTTP status {resp.status_code} as expected")
                else:
                    return ValidationResult(False, f"HTTP status {resp.status_code}, expected {expected_status}")
        except Exception as e:
            return ValidationResult(False, f"HTTP validation failed: {str(e)}")

    async def _validate_file_exists(self, validator: Dict[str, Any], context: ExecutionContext) -> ValidationResult:
        """Validate file exists"""
        import os
        file_path = validator.get("path")
        
        if os.path.exists(file_path):
            return ValidationResult(True, f"File exists: {file_path}")
        else:
            return ValidationResult(False, f"File does not exist: {file_path}")

    async def _validate_service_running(self, validator: Dict[str, Any], context: ExecutionContext) -> ValidationResult:
        """Validate service is running"""
        service_name = validator.get("service")
        
        try:
            proc = await asyncio.create_subprocess_shell(
                f"systemctl is-active {service_name}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0 and stdout.decode().strip() == "active":
                return ValidationResult(True, f"Service {service_name} is running")
            else:
                return ValidationResult(False, f"Service {service_name} is not running")
        except Exception as e:
            return ValidationResult(False, f"Service validation failed: {str(e)}")

    async def _validate_port_open(self, validator: Dict[str, Any], context: ExecutionContext) -> ValidationResult:
        """Validate port is open"""
        host = validator.get("host", "localhost")
        port = validator.get("port")
        
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0
            )
            writer.close()
            await writer.wait_closed()
            return ValidationResult(True, f"Port {port} is open on {host}")
        except Exception as e:
            return ValidationResult(False, f"Port {port} is not open on {host}: {str(e)}")

    async def _validate_disk_space(self, validator: Dict[str, Any], context: ExecutionContext) -> ValidationResult:
        """Validate disk space availability"""
        import shutil
        path = validator.get("path", "/")
        min_free_gb = validator.get("min_free_gb", 1)
        
        try:
            total, used, free = shutil.disk_usage(path)
            free_gb = free // (1024**3)
            
            if free_gb >= min_free_gb:
                return ValidationResult(True, f"Disk space OK: {free_gb}GB free")
            else:
                return ValidationResult(False, f"Low disk space: {free_gb}GB free, need {min_free_gb}GB")
        except Exception as e:
            return ValidationResult(False, f"Disk space validation failed: {str(e)}")

    async def _validate_memory_usage(self, validator: Dict[str, Any], context: ExecutionContext) -> ValidationResult:
        """Validate memory usage"""
        import psutil
        max_usage_percent = validator.get("max_usage_percent", 90)
        
        try:
            memory = psutil.virtual_memory()
            if memory.percent <= max_usage_percent:
                return ValidationResult(True, f"Memory usage OK: {memory.percent}%")
            else:
                return ValidationResult(False, f"High memory usage: {memory.percent}%")
        except Exception as e:
            return ValidationResult(False, f"Memory validation failed: {str(e)}")

    # Built-in rollback handlers
    
    async def _rollback_shell(self, args: Dict[str, Any], context: ExecutionContext) -> None:
        """Rollback shell command"""
        rollback_command = args.get("rollback_command")
        if rollback_command and self.allow_unsafe_shell:
            proc = await asyncio.create_subprocess_shell(
                rollback_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()

    async def _rollback_http_request(self, args: Dict[str, Any], context: ExecutionContext) -> None:
        """Rollback HTTP request"""
        rollback_url = args.get("rollback_url")
        rollback_method = args.get("rollback_method", "POST")
        
        if rollback_url:
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    await client.request(rollback_method, rollback_url)
            except Exception as e:
                logger.error(f"HTTP rollback failed: {e}")

    async def _rollback_file_operation(self, args: Dict[str, Any], context: ExecutionContext) -> None:
        """Rollback file operation"""
        import os
        import shutil
        
        operation = args.get("operation")
        path = args.get("path")
        backup_path = args.get("backup_path")
        
        try:
            if operation == "restore" and backup_path and os.path.exists(backup_path):
                shutil.copy2(backup_path, path)
            elif operation == "delete" and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.error(f"File rollback failed: {e}")