#!/usr/bin/env python3
"""
MCP Tools for Advanced Playbook Execution Engine

Provides MCP tool integration for the advanced playbook execution engine,
including execution control, monitoring, and hAIveMind integration.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from advanced_playbook_engine import AdvancedPlaybookEngine, ExecutionState, StepState
from execution_error_handler import ExecutionErrorHandler, ErrorContext, create_default_error_handler
from playbook_engine import load_playbook_content, PlaybookValidationError

logger = logging.getLogger(__name__)


class AdvancedExecutionMCPTools:
    """MCP tools for advanced playbook execution"""
    
    def __init__(self, database, haivemind_client: Optional[Any] = None):
        self.db = database
        self.haivemind_client = haivemind_client
        
        # Create execution engine with error handler
        self.error_handler = create_default_error_handler(haivemind_client)
        self.execution_engine = AdvancedPlaybookEngine(
            haivemind_client=haivemind_client,
            approval_handler=self._default_approval_handler
        )
        
        # Track active executions
        self.active_executions = {}
    
    async def execute_playbook_advanced(
        self,
        playbook_id: int,
        parameters: Optional[Dict[str, Any]] = None,
        version_id: Optional[int] = None,
        dry_run: bool = False,
        allow_unsafe_shell: bool = False,
        continue_on_failure: bool = False,
        approval_required: bool = False,
        environment: str = "default"
    ) -> Dict[str, Any]:
        """Execute a playbook with advanced features"""
        try:
            # Get playbook data
            playbook = self.db.get_playbook(playbook_id)
            if not playbook:
                return {"success": False, "error": "Playbook not found"}
            
            # Get version
            if version_id:
                version = self.db.get_playbook_version(version_id)
            else:
                version_id = playbook["latest_version_id"]
                version = self.db.get_playbook_version(version_id)
            
            if not version:
                return {"success": False, "error": "Playbook version not found"}
            
            # Parse playbook content
            try:
                spec = load_playbook_content(version["content"])
            except PlaybookValidationError as e:
                return {"success": False, "error": f"Playbook validation failed: {str(e)}"}
            
            # Add execution configuration
            spec["continue_on_failure"] = continue_on_failure
            
            # Configure engine
            self.execution_engine.allow_unsafe_shell = allow_unsafe_shell
            
            # Generate run ID
            import uuid
            run_id = str(uuid.uuid4())
            
            # Start execution in database
            self.db.start_playbook_execution(
                run_id=run_id,
                playbook_id=playbook_id,
                version_id=version_id,
                parameters=parameters or {},
                context={
                    "environment": environment,
                    "dry_run": dry_run,
                    "allow_unsafe_shell": allow_unsafe_shell,
                    "continue_on_failure": continue_on_failure,
                    "approval_required": approval_required
                }
            )
            
            # Execute playbook
            context = await self.execution_engine.execute_playbook(
                spec=spec,
                parameters=parameters,
                run_id=run_id,
                playbook_id=playbook_id,
                version_id=version_id,
                dry_run=dry_run
            )
            
            # Store execution in tracking
            self.active_executions[run_id] = context
            
            # Update database with results
            step_results = []
            for step_id, step_result in context.step_results.items():
                step_results.append({
                    "step_id": step_id,
                    "name": step_result.name,
                    "state": step_result.state.value,
                    "started_at": step_result.started_at,
                    "finished_at": step_result.finished_at,
                    "duration": step_result.duration,
                    "outputs": step_result.outputs,
                    "error": step_result.error,
                    "retry_count": step_result.retry_count
                })
            
            success = context.state == ExecutionState.COMPLETED
            self.db.complete_playbook_execution(
                run_id=run_id,
                status=context.state.value,
                success=success,
                step_results=step_results,
                log_text="\n".join(context.error_log)
            )
            
            # Store execution summary in hAIveMind
            if self.haivemind_client:
                await self.haivemind_client.store_memory(
                    content=f"Advanced playbook execution completed: {playbook['name']}",
                    category="playbook_execution",
                    metadata={
                        "run_id": run_id,
                        "playbook_id": playbook_id,
                        "playbook_name": playbook["name"],
                        "final_state": context.state.value,
                        "success": success,
                        "duration": context.duration,
                        "total_steps": len(context.step_results),
                        "completed_steps": len([r for r in context.step_results.values() if r.state == StepState.COMPLETED]),
                        "failed_steps": len([r for r in context.step_results.values() if r.state == StepState.FAILED]),
                        "environment": environment,
                        "dry_run": dry_run
                    },
                    tags=["playbook", "execution", "advanced", environment]
                )
            
            return {
                "success": True,
                "run_id": run_id,
                "state": context.state.value,
                "duration": context.duration,
                "total_steps": len(context.step_results),
                "completed_steps": len([r for r in context.step_results.values() if r.state == StepState.COMPLETED]),
                "failed_steps": len([r for r in context.step_results.values() if r.state == StepState.FAILED]),
                "step_results": step_results
            }
            
        except Exception as e:
            logger.error(f"Advanced playbook execution failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def control_execution(self, run_id: str, action: str) -> Dict[str, Any]:
        """Control a running execution"""
        try:
            action = action.lower()
            
            if action == "pause":
                success = await self.execution_engine.pause_execution(run_id)
                message = "Execution paused" if success else "Failed to pause execution"
            elif action == "resume":
                success = await self.execution_engine.resume_execution(run_id)
                message = "Execution resumed" if success else "Failed to resume execution"
            elif action == "cancel":
                success = await self.execution_engine.cancel_execution(run_id)
                message = "Execution cancelled" if success else "Failed to cancel execution"
            elif action == "rollback":
                success = await self.execution_engine.rollback_execution(run_id)
                message = "Execution rolled back" if success else "Failed to rollback execution"
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
            
            # Update database if needed
            if success and action in ["cancel", "rollback"]:
                execution = self.db.get_execution(run_id)
                if execution:
                    self.db.complete_playbook_execution(
                        run_id=run_id,
                        status=action,
                        success=False,
                        step_results=execution.get("step_results", []),
                        log_text=f"Execution {action} by user"
                    )
            
            # Store control action in hAIveMind
            if self.haivemind_client:
                await self.haivemind_client.store_memory(
                    content=f"Execution control action: {action} on {run_id}",
                    category="playbook_execution",
                    metadata={
                        "run_id": run_id,
                        "action": action,
                        "success": success,
                        "timestamp": time.time()
                    },
                    tags=["execution_control", action]
                )
            
            return {"success": success, "message": message, "action": action}
            
        except Exception as e:
            logger.error(f"Execution control failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def get_execution_status(self, run_id: str) -> Dict[str, Any]:
        """Get detailed execution status"""
        try:
            # Try to get from active executions first
            status = self.execution_engine.get_execution_status(run_id)
            if status:
                return {"success": True, "status": status}
            
            # Fall back to database
            execution = self.db.get_execution(run_id)
            if execution:
                return {"success": True, "status": execution}
            
            return {"success": False, "error": "Execution not found"}
            
        except Exception as e:
            logger.error(f"Failed to get execution status: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def list_active_executions(self) -> Dict[str, Any]:
        """List all active executions"""
        try:
            executions = self.execution_engine.list_active_executions()
            return {"success": True, "executions": executions}
            
        except Exception as e:
            logger.error(f"Failed to list executions: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def approve_execution_step(self, run_id: str, step_id: str, approver: str) -> Dict[str, Any]:
        """Approve a step waiting for approval"""
        try:
            success = await self.execution_engine.approve_step(run_id, step_id, approver)
            
            if success:
                # Store approval in hAIveMind
                if self.haivemind_client:
                    await self.haivemind_client.store_memory(
                        content=f"Step approved: {step_id} in execution {run_id}",
                        category="playbook_execution",
                        metadata={
                            "run_id": run_id,
                            "step_id": step_id,
                            "approver": approver,
                            "timestamp": time.time()
                        },
                        tags=["approval", "step_approval"]
                    )
                
                return {"success": True, "message": f"Step {step_id} approved by {approver}"}
            else:
                return {"success": False, "error": "Failed to approve step"}
                
        except Exception as e:
            logger.error(f"Step approval failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def get_execution_logs(self, run_id: str, level: str = "all") -> Dict[str, Any]:
        """Get execution logs"""
        try:
            status = self.execution_engine.get_execution_status(run_id)
            if not status:
                # Try database
                execution = self.db.get_execution(run_id)
                if not execution:
                    return {"success": False, "error": "Execution not found"}
                status = execution
            
            logs = []
            
            # Add execution-level logs
            for error in status.get("error_log", []):
                logs.append({
                    "timestamp": time.time(),
                    "level": "ERROR",
                    "source": "execution",
                    "message": error
                })
            
            # Add step-level logs
            for step_id, step_result in status.get("step_results", {}).items():
                if isinstance(step_result, dict):
                    if step_result.get("error") and level in ["all", "error"]:
                        logs.append({
                            "timestamp": step_result.get("started_at", time.time()),
                            "level": "ERROR",
                            "source": f"step:{step_id}",
                            "message": step_result["error"]
                        })
                    
                    if step_result.get("state") == "completed" and level in ["all", "info"]:
                        logs.append({
                            "timestamp": step_result.get("finished_at", time.time()),
                            "level": "INFO",
                            "source": f"step:{step_id}",
                            "message": f"Step completed in {step_result.get('duration', 0):.2f}s"
                        })
            
            # Sort by timestamp
            logs.sort(key=lambda x: x["timestamp"])
            
            return {"success": True, "logs": logs}
            
        except Exception as e:
            logger.error(f"Failed to get execution logs: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def get_execution_metrics(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """Get execution metrics and statistics"""
        try:
            if run_id:
                # Metrics for specific execution
                status = self.execution_engine.get_execution_status(run_id)
                if not status:
                    return {"success": False, "error": "Execution not found"}
                
                metrics = {
                    "run_id": run_id,
                    "duration": status.get("duration"),
                    "total_steps": status.get("total_steps", 0),
                    "completed_steps": status.get("completed_steps", 0),
                    "failed_steps": status.get("failed_steps", 0),
                    "success_rate": (status.get("completed_steps", 0) / max(status.get("total_steps", 1), 1)) * 100,
                    "state": status.get("state")
                }
                
                # Add step-level metrics
                step_metrics = []
                for step_id, step_result in status.get("step_results", {}).items():
                    if isinstance(step_result, dict):
                        step_metrics.append({
                            "step_id": step_id,
                            "duration": step_result.get("duration"),
                            "retry_count": step_result.get("retry_count", 0),
                            "state": step_result.get("state")
                        })
                
                metrics["step_metrics"] = step_metrics
                
            else:
                # Overall metrics
                executions = self.execution_engine.list_active_executions()
                
                total_executions = len(executions)
                running = len([e for e in executions if e["state"] == "running"])
                completed = len([e for e in executions if e["state"] == "completed"])
                failed = len([e for e in executions if e["state"] == "failed"])
                paused = len([e for e in executions if e["state"] == "paused"])
                
                metrics = {
                    "total_executions": total_executions,
                    "running_executions": running,
                    "completed_executions": completed,
                    "failed_executions": failed,
                    "paused_executions": paused,
                    "success_rate": (completed / max(total_executions, 1)) * 100 if total_executions > 0 else 0
                }
                
                # Add error handler statistics
                error_stats = self.error_handler.get_error_statistics()
                metrics["error_statistics"] = error_stats
            
            return {"success": True, "metrics": metrics}
            
        except Exception as e:
            logger.error(f"Failed to get execution metrics: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def validate_playbook_advanced(self, playbook_content: str) -> Dict[str, Any]:
        """Validate playbook with advanced checks"""
        try:
            # Parse content
            spec = load_playbook_content(playbook_content)
            
            # Basic validation
            self.execution_engine.validate(spec)
            
            # Advanced validation checks
            validation_results = []
            
            # Check for security issues
            security_issues = self._check_security_issues(spec)
            validation_results.extend(security_issues)
            
            # Check for performance issues
            performance_issues = self._check_performance_issues(spec)
            validation_results.extend(performance_issues)
            
            # Check for best practices
            best_practice_issues = self._check_best_practices(spec)
            validation_results.extend(best_practice_issues)
            
            # Categorize issues
            errors = [r for r in validation_results if r["severity"] == "error"]
            warnings = [r for r in validation_results if r["severity"] == "warning"]
            info = [r for r in validation_results if r["severity"] == "info"]
            
            return {
                "success": True,
                "valid": len(errors) == 0,
                "validation_results": {
                    "errors": errors,
                    "warnings": warnings,
                    "info": info,
                    "total_issues": len(validation_results)
                }
            }
            
        except PlaybookValidationError as e:
            return {
                "success": True,
                "valid": False,
                "validation_results": {
                    "errors": [{"message": str(e), "severity": "error", "type": "validation"}],
                    "warnings": [],
                    "info": [],
                    "total_issues": 1
                }
            }
        except Exception as e:
            logger.error(f"Playbook validation failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _check_security_issues(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for security issues in playbook"""
        issues = []
        
        for idx, step in enumerate(spec.get("steps", []), 1):
            step_id = step.get("id", f"step_{idx}")
            
            # Check for shell commands without proper validation
            if step.get("action") == "shell":
                command = step.get("args", {}).get("command", "")
                if any(dangerous in command.lower() for dangerous in ["rm -rf", "dd if=", "format", "mkfs"]):
                    issues.append({
                        "step_id": step_id,
                        "message": f"Potentially dangerous shell command in step {step_id}",
                        "severity": "error",
                        "type": "security"
                    })
                
                if "${" in command and not step.get("validations"):
                    issues.append({
                        "step_id": step_id,
                        "message": f"Shell command with variables but no validation in step {step_id}",
                        "severity": "warning",
                        "type": "security"
                    })
            
            # Check for hardcoded credentials
            step_str = json.dumps(step)
            if any(keyword in step_str.lower() for keyword in ["password", "secret", "key", "token"]):
                if any(value in step_str for value in ["=", ":"]):
                    issues.append({
                        "step_id": step_id,
                        "message": f"Possible hardcoded credentials in step {step_id}",
                        "severity": "warning",
                        "type": "security"
                    })
        
        return issues
    
    def _check_performance_issues(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for performance issues in playbook"""
        issues = []
        
        # Check for too many sequential steps
        steps = spec.get("steps", [])
        sequential_steps = [s for s in steps if not s.get("parallel_group")]
        if len(sequential_steps) > 20:
            issues.append({
                "message": f"Large number of sequential steps ({len(sequential_steps)}) may impact performance",
                "severity": "info",
                "type": "performance"
            })
        
        # Check for long waits
        for idx, step in enumerate(steps, 1):
            step_id = step.get("id", f"step_{idx}")
            
            if step.get("action") == "wait":
                seconds = step.get("args", {}).get("seconds", 0)
                if seconds > 300:  # 5 minutes
                    issues.append({
                        "step_id": step_id,
                        "message": f"Long wait time ({seconds}s) in step {step_id}",
                        "severity": "warning",
                        "type": "performance"
                    })
        
        return issues
    
    def _check_best_practices(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for best practice violations"""
        issues = []
        
        # Check for missing descriptions
        if not spec.get("description"):
            issues.append({
                "message": "Playbook missing description",
                "severity": "info",
                "type": "best_practice"
            })
        
        # Check for steps without names
        for idx, step in enumerate(spec.get("steps", []), 1):
            step_id = step.get("id", f"step_{idx}")
            
            if not step.get("name"):
                issues.append({
                    "step_id": step_id,
                    "message": f"Step {step_id} missing descriptive name",
                    "severity": "info",
                    "type": "best_practice"
                })
            
            # Check for missing error handling
            if step.get("action") in ["shell", "http_request"] and not step.get("retry"):
                issues.append({
                    "step_id": step_id,
                    "message": f"Step {step_id} missing retry configuration",
                    "severity": "info",
                    "type": "best_practice"
                })
        
        return issues
    
    async def _default_approval_handler(self, approval_gate) -> bool:
        """Default approval handler - always approve for now"""
        logger.info(f"Auto-approving step {approval_gate.step_id}: {approval_gate.message}")
        return True