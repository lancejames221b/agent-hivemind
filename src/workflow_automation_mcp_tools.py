#!/usr/bin/env python3
"""
MCP Tools for Workflow Automation System
Provides intelligent workflow automation and command sequence management
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union
import logging

from .workflow_automation_engine import (
    WorkflowAutomationEngine, WorkflowSuggestion, TriggerType, WorkflowStatus
)

logger = logging.getLogger(__name__)

class WorkflowAutomationMCPTools:
    """MCP tools for workflow automation system"""
    
    def __init__(self, storage, config: Dict[str, Any]):
        self.storage = storage
        self.config = config
        self.workflow_engine = WorkflowAutomationEngine(storage, config)
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure workflow engine is initialized"""
        if not self._initialized:
            await self.workflow_engine.initialize()
            self._initialized = True
    
    async def suggest_workflows(self, context: Optional[str] = None, 
                               recent_commands: Optional[str] = None,
                               intent: Optional[str] = None) -> Dict[str, Any]:
        """
        Get intelligent workflow suggestions based on current context
        
        Args:
            context: Current situation or context description
            recent_commands: Comma-separated list of recent commands
            intent: What you're trying to accomplish
            
        Returns:
            Smart workflow suggestions with confidence scores and reasoning
        """
        await self._ensure_initialized()
        
        try:
            # Parse recent commands
            recent_cmd_list = []
            if recent_commands:
                recent_cmd_list = [cmd.strip() for cmd in recent_commands.split(',')]
            
            suggestions = await self.workflow_engine.suggest_workflows(
                context=context,
                recent_commands=recent_cmd_list,
                intent=intent
            )
            
            return await self._format_workflow_suggestions(suggestions, context, intent)
            
        except Exception as e:
            logger.error(f"Error in suggest_workflows: {e}")
            return {
                'error': f"Workflow suggestion error: {str(e)}",
                'suggestions': []
            }
    
    async def execute_workflow(self, workflow_id: str, parameters: Optional[str] = None,
                              auto_approve: bool = False) -> Dict[str, Any]:
        """
        Execute a workflow with optional parameters
        
        Args:
            workflow_id: ID of the workflow template to execute
            parameters: JSON string of workflow parameters
            auto_approve: Skip approval for workflows that require it
            
        Returns:
            Workflow execution details and status
        """
        await self._ensure_initialized()
        
        try:
            # Parse parameters
            workflow_params = {}
            if parameters:
                try:
                    workflow_params = json.loads(parameters)
                except json.JSONDecodeError:
                    return {
                        'error': 'Invalid parameters JSON format',
                        'example': '{"param1": "value1", "param2": "value2"}'
                    }
            
            # Execute workflow
            execution_id = await self.workflow_engine.execute_workflow(
                template_id=workflow_id,
                parameters=workflow_params,
                trigger_type=TriggerType.MANUAL,
                trigger_context={'auto_approve': auto_approve}
            )
            
            # Get initial status
            status = await self.workflow_engine.get_workflow_status(execution_id)
            
            return {
                'status': 'success',
                'execution_id': execution_id,
                'workflow_id': workflow_id,
                'execution_status': status,
                'message': f'Workflow "{workflow_id}" started successfully',
                'monitoring': f'Use workflow_status with execution_id "{execution_id}" to track progress'
            }
            
        except ValueError as e:
            return {
                'error': f'Workflow not found: {str(e)}',
                'suggestion': 'Use list_workflows to see available workflows'
            }
        except Exception as e:
            logger.error(f"Error in execute_workflow: {e}")
            return {
                'error': f'Workflow execution error: {str(e)}',
                'workflow_id': workflow_id
            }
    
    async def workflow_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get the status of a running or completed workflow
        
        Args:
            execution_id: ID of the workflow execution to check
            
        Returns:
            Detailed workflow execution status and progress
        """
        await self._ensure_initialized()
        
        try:
            status = await self.workflow_engine.get_workflow_status(execution_id)
            
            if not status:
                return {
                    'error': f'Workflow execution not found: {execution_id}',
                    'suggestion': 'Check the execution ID or use list_executions to see active workflows'
                }
            
            return await self._format_workflow_status(status)
            
        except Exception as e:
            logger.error(f"Error in workflow_status: {e}")
            return {
                'error': f'Status check error: {str(e)}',
                'execution_id': execution_id
            }
    
    async def cancel_workflow(self, execution_id: str) -> Dict[str, Any]:
        """
        Cancel a running workflow execution
        
        Args:
            execution_id: ID of the workflow execution to cancel
            
        Returns:
            Cancellation confirmation and status
        """
        await self._ensure_initialized()
        
        try:
            success = await self.workflow_engine.cancel_workflow(execution_id)
            
            if success:
                return {
                    'status': 'success',
                    'message': f'Workflow execution {execution_id} cancelled successfully',
                    'execution_id': execution_id
                }
            else:
                return {
                    'error': f'Cannot cancel workflow {execution_id}',
                    'reason': 'Workflow not found, already completed, or not cancellable'
                }
                
        except Exception as e:
            logger.error(f"Error in cancel_workflow: {e}")
            return {
                'error': f'Cancellation error: {str(e)}',
                'execution_id': execution_id
            }
    
    async def list_workflows(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        List all available workflow templates
        
        Args:
            category: Filter by workflow category (optional)
            
        Returns:
            List of available workflow templates with details
        """
        await self._ensure_initialized()
        
        try:
            templates = await self.workflow_engine.get_workflow_templates()
            
            # Filter by category if specified
            if category:
                templates = [t for t in templates if t['category'].lower() == category.lower()]
            
            return await self._format_workflow_list(templates, category)
            
        except Exception as e:
            logger.error(f"Error in list_workflows: {e}")
            return {
                'error': f'Workflow listing error: {str(e)}',
                'templates': []
            }
    
    async def create_workflow(self, workflow_definition: str) -> Dict[str, Any]:
        """
        Create a custom workflow template
        
        Args:
            workflow_definition: JSON string defining the workflow template
            
        Returns:
            Created workflow template details
        """
        await self._ensure_initialized()
        
        try:
            # Parse workflow definition
            try:
                workflow_data = json.loads(workflow_definition)
            except json.JSONDecodeError as e:
                return {
                    'error': f'Invalid workflow definition JSON: {str(e)}',
                    'example': {
                        'name': 'My Custom Workflow',
                        'description': 'Description of what this workflow does',
                        'category': 'custom',
                        'steps': [
                            {
                                'id': 'step1',
                                'command': 'hv-status',
                                'description': 'Check system status',
                                'parameters': {}
                            }
                        ]
                    }
                }
            
            # Create workflow template
            template_id = await self.workflow_engine.create_custom_workflow(workflow_data)
            
            return {
                'status': 'success',
                'template_id': template_id,
                'name': workflow_data.get('name', 'Unnamed Workflow'),
                'message': f'Custom workflow "{template_id}" created successfully',
                'usage': f'Execute with: execute_workflow("{template_id}")'
            }
            
        except ValueError as e:
            return {
                'error': f'Workflow validation error: {str(e)}',
                'suggestion': 'Check required fields: name, description, category, steps'
            }
        except Exception as e:
            logger.error(f"Error in create_workflow: {e}")
            return {
                'error': f'Workflow creation error: {str(e)}'
            }
    
    async def workflow_analytics(self) -> Dict[str, Any]:
        """
        Get workflow system analytics and usage statistics
        
        Returns:
            Comprehensive analytics about workflow usage and performance
        """
        await self._ensure_initialized()
        
        try:
            analytics = await self.workflow_engine.get_workflow_analytics()
            return await self._format_workflow_analytics(analytics)
            
        except Exception as e:
            logger.error(f"Error in workflow_analytics: {e}")
            return {
                'error': f'Analytics error: {str(e)}',
                'suggestion': 'Analytics may be limited if system is newly initialized'
            }
    
    async def auto_complete_workflow(self, partial_sequence: str) -> Dict[str, Any]:
        """
        Get workflow completion suggestions for partial command sequences
        
        Args:
            partial_sequence: Comma-separated list of commands already executed
            
        Returns:
            Suggested next steps and workflow completions
        """
        await self._ensure_initialized()
        
        try:
            # Parse partial sequence
            commands = [cmd.strip() for cmd in partial_sequence.split(',') if cmd.strip()]
            
            if not commands:
                return {
                    'error': 'No commands provided',
                    'suggestion': 'Provide a comma-separated list of commands like: "hv-status,hv-broadcast"'
                }
            
            # Get workflow suggestions based on the sequence
            suggestions = await self.workflow_engine.suggest_workflows(
                recent_commands=commands,
                context="workflow_completion"
            )
            
            return await self._format_completion_suggestions(suggestions, commands)
            
        except Exception as e:
            logger.error(f"Error in auto_complete_workflow: {e}")
            return {
                'error': f'Auto-completion error: {str(e)}',
                'suggestions': []
            }
    
    async def validate_workflow(self, workflow_definition: str) -> Dict[str, Any]:
        """
        Validate a workflow definition without creating it
        
        Args:
            workflow_definition: JSON string of workflow definition to validate
            
        Returns:
            Validation results with warnings and suggestions
        """
        await self._ensure_initialized()
        
        try:
            # Parse definition
            try:
                workflow_data = json.loads(workflow_definition)
            except json.JSONDecodeError as e:
                return {
                    'valid': False,
                    'error': f'Invalid JSON: {str(e)}',
                    'suggestion': 'Check JSON syntax and formatting'
                }
            
            # Validate structure
            validation_result = await self._validate_workflow_structure(workflow_data)
            return validation_result
            
        except Exception as e:
            logger.error(f"Error in validate_workflow: {e}")
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}'
            }
    
    async def workflow_history(self, limit: int = 10, status_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Get workflow execution history
        
        Args:
            limit: Maximum number of executions to return
            status_filter: Filter by execution status (completed, failed, cancelled)
            
        Returns:
            Recent workflow execution history with details
        """
        await self._ensure_initialized()
        
        try:
            # Get execution history
            history = self.workflow_engine.execution_history
            
            # Filter by status if specified
            if status_filter:
                status_enum = WorkflowStatus(status_filter.lower())
                history = [e for e in history if e.status == status_enum]
            
            # Sort by start time and limit
            history = sorted(history, key=lambda x: x.start_time or 0, reverse=True)[:limit]
            
            return await self._format_workflow_history(history, status_filter)
            
        except ValueError:
            return {
                'error': f'Invalid status filter: {status_filter}',
                'valid_statuses': ['completed', 'failed', 'cancelled', 'running']
            }
        except Exception as e:
            logger.error(f"Error in workflow_history: {e}")
            return {
                'error': f'History retrieval error: {str(e)}',
                'history': []
            }
    
    # Formatting methods for user-friendly output
    
    async def _format_workflow_suggestions(self, suggestions: List[WorkflowSuggestion], 
                                         context: Optional[str], intent: Optional[str]) -> Dict[str, Any]:
        """Format workflow suggestions for display"""
        formatted = {
            'title': '🔄 Smart Workflow Suggestions',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'context': context,
            'intent': intent,
            'total_suggestions': len(suggestions),
            'suggestions': []
        }
        
        for i, suggestion in enumerate(suggestions, 1):
            formatted_suggestion = {
                'rank': i,
                'workflow_id': suggestion.workflow_id,
                'name': suggestion.name,
                'confidence': f"{suggestion.confidence:.0%}",
                'reason': suggestion.reason,
                'estimated_duration': self._format_duration(suggestion.estimated_duration),
                'success_probability': f"{suggestion.success_probability:.0%}",
                'similar_executions': suggestion.similar_executions,
                'suggested_parameters': suggestion.suggested_parameters
            }
            formatted['suggestions'].append(formatted_suggestion)
        
        if not suggestions:
            formatted['message'] = 'No workflow suggestions found for the given context'
            formatted['tip'] = 'Try providing more specific context or recent commands'
        
        return formatted
    
    async def _format_workflow_status(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """Format workflow status for display"""
        formatted = {
            'title': f'📊 Workflow Status: {status["name"]}',
            'execution_id': status['execution_id'],
            'template_id': status['template_id'],
            'status': status['status'].upper(),
            'progress': f"{status['progress']:.0%}",
            'current_step': status.get('current_step', 'N/A'),
            'completed_steps': len(status.get('completed_steps', [])),
            'failed_steps': len(status.get('failed_steps', [])),
            'total_steps': status['total_steps']
        }
        
        if status.get('start_time'):
            formatted['started_at'] = time.strftime('%Y-%m-%d %H:%M:%S', 
                                                   time.localtime(status['start_time']))
        
        if status.get('end_time'):
            formatted['ended_at'] = time.strftime('%Y-%m-%d %H:%M:%S', 
                                                 time.localtime(status['end_time']))
            duration = status['end_time'] - status['start_time']
            formatted['duration'] = self._format_duration(duration)
        
        if status.get('error_message'):
            formatted['error'] = status['error_message']
        
        # Add progress indicator
        progress_bar = self._create_progress_bar(status['progress'])
        formatted['progress_bar'] = progress_bar
        
        return formatted
    
    async def _format_workflow_list(self, templates: List[Dict[str, Any]], 
                                   category: Optional[str]) -> Dict[str, Any]:
        """Format workflow template list"""
        formatted = {
            'title': '📋 Available Workflow Templates',
            'category_filter': category,
            'total_templates': len(templates),
            'templates': []
        }
        
        for template in templates:
            formatted_template = {
                'id': template['id'],
                'name': template['name'],
                'description': template['description'],
                'category': template['category'],
                'tags': template['tags'],
                'estimated_duration': self._format_duration(template['estimated_duration']),
                'success_rate': f"{template['success_rate']:.0%}",
                'usage_count': template['usage_count'],
                'steps': template['step_count'],
                'approval_required': '✓' if template['approval_required'] else '✗',
                'rollback_enabled': '✓' if template['rollback_enabled'] else '✗'
            }
            formatted['templates'].append(formatted_template)
        
        # Group by category
        categories = {}
        for template in formatted['templates']:
            cat = template['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(template)
        
        formatted['by_category'] = categories
        
        return formatted
    
    async def _format_workflow_analytics(self, analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Format workflow analytics"""
        formatted = {
            'title': '📈 Workflow System Analytics',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'overview': {
                'total_templates': analytics['total_templates'],
                'total_executions': analytics['total_executions'],
                'success_rate': f"{analytics['success_rate']:.0%}",
                'active_executions': analytics['active_executions'],
                'recent_executions_24h': analytics['recent_executions_24h']
            },
            'most_popular_templates': [],
            'template_performance': analytics['template_statistics'],
            'learning_metrics': {
                'command_sequences_learned': analytics['command_sequences_learned']
            }
        }
        
        # Format popular templates
        for template_id, stats in analytics['most_popular_templates']:
            formatted['most_popular_templates'].append({
                'id': template_id,
                'name': stats['name'],
                'category': stats['category'],
                'usage_count': stats['usage_count'],
                'success_rate': f"{stats['success_rate']:.0%}"
            })
        
        return formatted
    
    async def _format_completion_suggestions(self, suggestions: List[WorkflowSuggestion], 
                                           commands: List[str]) -> Dict[str, Any]:
        """Format workflow completion suggestions"""
        formatted = {
            'title': '🎯 Workflow Auto-Completion',
            'partial_sequence': ' → '.join(commands),
            'suggestions': []
        }
        
        for suggestion in suggestions:
            # Get next steps for this workflow
            template = self.workflow_engine.templates.get(suggestion.workflow_id)
            if template:
                template_commands = [step.command for step in template.steps]
                
                # Find where we are in the workflow
                next_steps = []
                for i, cmd in enumerate(template_commands):
                    if i < len(commands):
                        continue
                    next_steps.append(cmd)
                    if len(next_steps) >= 3:  # Show next 3 steps
                        break
                
                formatted_suggestion = {
                    'workflow_id': suggestion.workflow_id,
                    'name': suggestion.name,
                    'confidence': f"{suggestion.confidence:.0%}",
                    'next_steps': next_steps,
                    'completion_estimate': self._format_duration(suggestion.estimated_duration)
                }
                formatted['suggestions'].append(formatted_suggestion)
        
        return formatted
    
    async def _format_workflow_history(self, history: List, status_filter: Optional[str]) -> Dict[str, Any]:
        """Format workflow execution history"""
        formatted = {
            'title': '📜 Workflow Execution History',
            'status_filter': status_filter,
            'total_executions': len(history),
            'executions': []
        }
        
        for execution in history:
            formatted_execution = {
                'execution_id': execution.id,
                'template_id': execution.template_id,
                'name': execution.name,
                'status': execution.status.value,
                'trigger_type': execution.trigger_type.value,
                'completed_steps': len(execution.completed_steps),
                'failed_steps': len(execution.failed_steps)
            }
            
            if execution.start_time:
                formatted_execution['started_at'] = time.strftime(
                    '%Y-%m-%d %H:%M:%S', time.localtime(execution.start_time)
                )
            
            if execution.end_time and execution.start_time:
                duration = execution.end_time - execution.start_time
                formatted_execution['duration'] = self._format_duration(duration)
            
            if execution.error_message:
                formatted_execution['error'] = execution.error_message
            
            formatted['executions'].append(formatted_execution)
        
        return formatted
    
    async def _validate_workflow_structure(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow structure"""
        validation = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'suggestions': []
        }
        
        # Check required fields
        required_fields = ['name', 'description', 'category', 'steps']
        for field in required_fields:
            if field not in workflow_data:
                validation['errors'].append(f"Missing required field: {field}")
                validation['valid'] = False
        
        # Validate steps
        if 'steps' in workflow_data:
            steps = workflow_data['steps']
            if not isinstance(steps, list) or len(steps) == 0:
                validation['errors'].append("Steps must be a non-empty list")
                validation['valid'] = False
            else:
                step_ids = set()
                for i, step in enumerate(steps):
                    if not isinstance(step, dict):
                        validation['errors'].append(f"Step {i} must be an object")
                        validation['valid'] = False
                        continue
                    
                    # Check required step fields
                    step_required = ['id', 'command', 'description']
                    for field in step_required:
                        if field not in step:
                            validation['errors'].append(f"Step {i} missing required field: {field}")
                            validation['valid'] = False
                    
                    # Check for duplicate step IDs
                    step_id = step.get('id')
                    if step_id in step_ids:
                        validation['errors'].append(f"Duplicate step ID: {step_id}")
                        validation['valid'] = False
                    step_ids.add(step_id)
                    
                    # Validate dependencies
                    depends_on = step.get('depends_on', [])
                    for dep in depends_on:
                        if dep not in step_ids and dep not in [s.get('id') for s in steps[:i]]:
                            validation['warnings'].append(f"Step {step_id} depends on undefined step: {dep}")
        
        # Add suggestions
        if validation['valid']:
            validation['suggestions'].append("Workflow structure is valid")
            if not workflow_data.get('tags'):
                validation['suggestions'].append("Consider adding tags for better discoverability")
            if not workflow_data.get('estimated_duration'):
                validation['suggestions'].append("Consider adding estimated_duration for better planning")
        
        return validation
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def _create_progress_bar(self, progress: float, width: int = 20) -> str:
        """Create a text-based progress bar"""
        filled = int(progress * width)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}] {progress:.0%}"

# Tool registration functions for MCP server
async def register_workflow_automation_tools(server, storage, config):
    """Register all workflow automation tools with the MCP server"""
    tools = WorkflowAutomationMCPTools(storage, config)
    
    @server.tool("workflow_suggest")
    async def workflow_suggest(context: Optional[str] = None, 
                              recent_commands: Optional[str] = None,
                              intent: Optional[str] = None):
        """Get intelligent workflow suggestions based on current context and recent commands"""
        return await tools.suggest_workflows(context, recent_commands, intent)
    
    @server.tool("workflow_execute")
    async def workflow_execute(workflow_id: str, parameters: Optional[str] = None,
                              auto_approve: bool = False):
        """Execute a workflow with optional parameters and approval settings"""
        return await tools.execute_workflow(workflow_id, parameters, auto_approve)
    
    @server.tool("workflow_status")
    async def workflow_status(execution_id: str):
        """Get detailed status and progress of a workflow execution"""
        return await tools.workflow_status(execution_id)
    
    @server.tool("workflow_cancel")
    async def workflow_cancel(execution_id: str):
        """Cancel a running workflow execution"""
        return await tools.cancel_workflow(execution_id)
    
    @server.tool("workflow_list")
    async def workflow_list(category: Optional[str] = None):
        """List all available workflow templates, optionally filtered by category"""
        return await tools.list_workflows(category)
    
    @server.tool("workflow_create")
    async def workflow_create(workflow_definition: str):
        """Create a custom workflow template from JSON definition"""
        return await tools.create_workflow(workflow_definition)
    
    @server.tool("workflow_analytics")
    async def workflow_analytics():
        """Get comprehensive workflow system analytics and usage statistics"""
        return await tools.workflow_analytics()
    
    @server.tool("workflow_autocomplete")
    async def workflow_autocomplete(partial_sequence: str):
        """Get workflow completion suggestions for partial command sequences"""
        return await tools.auto_complete_workflow(partial_sequence)
    
    @server.tool("workflow_validate")
    async def workflow_validate(workflow_definition: str):
        """Validate a workflow definition without creating it"""
        return await tools.validate_workflow(workflow_definition)
    
    @server.tool("workflow_history")
    async def workflow_history(limit: int = 10, status_filter: Optional[str] = None):
        """Get workflow execution history with optional status filtering"""
        return await tools.workflow_history(limit, status_filter)
    
    logger.info("Registered 10 workflow automation MCP tools")
    return tools