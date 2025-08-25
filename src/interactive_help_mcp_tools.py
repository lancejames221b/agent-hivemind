#!/usr/bin/env python3
"""
MCP Tools for Interactive Help System
Provides intelligent command assistance and context-aware help
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
import logging

from .interactive_help_system import InteractiveHelpSystem

logger = logging.getLogger(__name__)

class InteractiveHelpMCPTools:
    """MCP tools for the interactive help system"""
    
    def __init__(self, storage, config: Dict[str, Any]):
        self.storage = storage
        self.config = config
        self.help_system = InteractiveHelpSystem(storage, config)
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure help system is initialized"""
        if not self._initialized:
            await self.help_system.initialize()
            self._initialized = True
    
    async def show_help(self, command: Optional[str] = None, detailed: bool = False) -> Dict[str, Any]:
        """
        Show interactive help for hAIveMind commands
        
        Args:
            command: Specific command to get help for (optional)
            detailed: Show detailed help with examples and troubleshooting
            
        Returns:
            Comprehensive help information with context-aware suggestions
        """
        await self._ensure_initialized()
        
        try:
            result = await self.help_system.show_help(command, detailed)
            
            # Format output for user display
            if result['type'] == 'general_help':
                return await self._format_general_help(result)
            elif result['type'] == 'command_help':
                return await self._format_command_help(result)
            elif result['type'] == 'command_not_found':
                return await self._format_command_not_found(result)
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error in show_help: {e}")
            return {
                'error': f"Help system error: {str(e)}",
                'suggestion': "Try 'hv-status' to check system health"
            }
    
    async def show_examples(self, command: Optional[str] = None, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Show relevant examples for commands or contexts
        
        Args:
            command: Command to show examples for
            context: Context to find relevant examples (e.g., 'incident', 'security')
            
        Returns:
            Contextual examples with explanations and expected outcomes
        """
        await self._ensure_initialized()
        
        try:
            result = await self.help_system.show_examples(command, context)
            return await self._format_examples(result)
            
        except Exception as e:
            logger.error(f"Error in show_examples: {e}")
            return {
                'error': f"Examples system error: {str(e)}",
                'suggestion': "Try specifying a specific command like 'hv-broadcast'"
            }
    
    async def show_workflows(self) -> Dict[str, Any]:
        """
        Show common command workflows and patterns
        
        Returns:
            Workflow templates with step-by-step guidance
        """
        await self._ensure_initialized()
        
        try:
            result = await self.help_system.show_workflows()
            return await self._format_workflows(result)
            
        except Exception as e:
            logger.error(f"Error in show_workflows: {e}")
            return {
                'error': f"Workflows system error: {str(e)}",
                'suggestion': "Try individual commands like 'hv-status' for basic operations"
            }
    
    async def show_recent(self, limit: int = 10) -> Dict[str, Any]:
        """
        Show recently used commands and their outcomes
        
        Args:
            limit: Number of recent commands to show (default: 10)
            
        Returns:
            Recent command history with success rates and patterns
        """
        await self._ensure_initialized()
        
        try:
            result = await self.help_system.show_recent(limit)
            return await self._format_recent(result)
            
        except Exception as e:
            logger.error(f"Error in show_recent: {e}")
            return {
                'error': f"Recent commands error: {str(e)}",
                'suggestion': "Command history may be empty if no commands have been tracked"
            }
    
    async def suggest_commands(self, context: Optional[str] = None, intent: Optional[str] = None) -> Dict[str, Any]:
        """
        Get AI-powered command suggestions based on current context
        
        Args:
            context: Current context or situation
            intent: What you're trying to accomplish
            
        Returns:
            Smart command suggestions with reasoning and examples
        """
        await self._ensure_initialized()
        
        try:
            result = await self.help_system.suggest_commands(context, intent)
            return await self._format_suggestions(result)
            
        except Exception as e:
            logger.error(f"Error in suggest_commands: {e}")
            return {
                'error': f"Suggestions system error: {str(e)}",
                'suggestion': "Try 'hv-status' as a good starting point"
            }
    
    async def validate_command(self, command: str, **parameters) -> Dict[str, Any]:
        """
        Validate command syntax and parameters before execution
        
        Args:
            command: Command to validate
            **parameters: Command parameters to validate
            
        Returns:
            Validation results with warnings and suggestions
        """
        await self._ensure_initialized()
        
        try:
            result = await self.help_system.validate_command(command, parameters)
            return await self._format_validation(result)
            
        except Exception as e:
            logger.error(f"Error in validate_command: {e}")
            return {
                'error': f"Validation error: {str(e)}",
                'suggestion': "Check command spelling and required parameters"
            }
    
    async def get_command_completion(self, partial_command: str) -> Dict[str, Any]:
        """
        Get smart command completion suggestions
        
        Args:
            partial_command: Partial command being typed
            
        Returns:
            Command completion suggestions with confidence scores
        """
        await self._ensure_initialized()
        
        try:
            result = await self.help_system.get_command_completion(partial_command)
            return await self._format_completion(result)
            
        except Exception as e:
            logger.error(f"Error in get_command_completion: {e}")
            return {
                'error': f"Completion error: {str(e)}",
                'completions': []
            }
    
    async def track_command_usage(self, command: str, success: bool = True, 
                                execution_time: float = 0, context: str = "", 
                                **parameters) -> Dict[str, Any]:
        """
        Track command usage for learning and improvement
        
        Args:
            command: Command that was executed
            success: Whether the command succeeded
            execution_time: How long the command took to execute
            context: Context in which command was used
            **parameters: Command parameters that were used
            
        Returns:
            Confirmation of usage tracking
        """
        await self._ensure_initialized()
        
        try:
            await self.help_system.track_command_usage(
                command, success, execution_time, context, parameters
            )
            
            return {
                'status': 'success',
                'message': f"Tracked usage of '{command}' command",
                'success': success,
                'execution_time': execution_time,
                'learning_impact': 'Command patterns updated for improved suggestions'
            }
            
        except Exception as e:
            logger.error(f"Error in track_command_usage: {e}")
            return {
                'error': f"Usage tracking error: {str(e)}",
                'status': 'failed'
            }
    
    async def get_help_analytics(self) -> Dict[str, Any]:
        """
        Get help system usage analytics and effectiveness metrics
        
        Returns:
            Analytics dashboard with usage patterns and system performance
        """
        await self._ensure_initialized()
        
        try:
            result = await self.help_system.get_help_analytics()
            return await self._format_analytics(result)
            
        except Exception as e:
            logger.error(f"Error in get_help_analytics: {e}")
            return {
                'error': f"Analytics error: {str(e)}",
                'suggestion': "Analytics may be limited if system is newly initialized"
            }
    
    # Formatting methods for user-friendly output
    
    async def _format_general_help(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format general help output"""
        categories = result.get('categories', {})
        suggestions = result.get('context_suggestions', [])
        
        formatted = {
            'title': '🤖 hAIveMind Interactive Help System',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result['timestamp'])),
            'available_commands': len(result.get('available_commands', [])),
            'categories': categories,
            'quick_start': result.get('quick_start', []),
            'context_suggestions': suggestions,
            'usage_stats': result.get('recent_usage', {}),
            'help_commands': {
                '/help <command>': 'Get detailed help for specific command',
                '/examples <command>': 'Show examples for command or context',
                '/workflows': 'Show common command patterns and workflows',
                '/recent': 'Show recently used commands and outcomes',
                '/suggest': 'Get AI-powered command suggestions'
            }
        }
        
        return formatted
    
    async def _format_command_help(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format command-specific help output"""
        command = result['command']
        
        formatted = {
            'title': f'📖 Help: {command}',
            'command': command,
            'description': result.get('description', ''),
            'usage': result.get('argument_hint', ''),
            'allowed_tools': result.get('allowed_tools', []),
            'context_suggestions': result.get('context_suggestions', [])
        }
        
        if result.get('full_documentation'):
            formatted['detailed_help'] = result['full_documentation']
        
        if result.get('examples'):
            formatted['examples'] = result['examples']
        
        if result.get('related_commands'):
            formatted['related_commands'] = result['related_commands']
        
        if result.get('troubleshooting', {}).get('has_troubleshooting'):
            formatted['troubleshooting'] = result['troubleshooting']['content']
        
        return formatted
    
    async def _format_command_not_found(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format command not found output"""
        return {
            'title': '❓ Command Not Found',
            'query': result['query'],
            'message': result['message'],
            'suggestions': result.get('suggestions', []),
            'tip': 'Use fuzzy matching - try typing partial command names'
        }
    
    async def _format_examples(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format examples output"""
        examples = result.get('examples', [])
        
        formatted = {
            'title': '💡 Command Examples',
            'query': result.get('query', {}),
            'total_examples': result.get('total_available', 0),
            'showing': len(examples),
            'context': result.get('context_info', {}),
            'examples': []
        }
        
        for i, example in enumerate(examples[:10], 1):
            formatted_example = {
                'number': i,
                'title': example.get('title', example.get('name', f'Example {i}')),
                'type': example.get('type', 'general')
            }
            
            if 'command' in example:
                formatted_example['command'] = example['command']
            
            if 'result' in example:
                formatted_example['expected_result'] = example['result']
            
            if 'content' in example:
                formatted_example['content'] = example['content'][:500] + '...' if len(example['content']) > 500 else example['content']
            
            formatted['examples'].append(formatted_example)
        
        return formatted
    
    async def _format_workflows(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format workflows output"""
        workflows = result.get('workflows', {})
        
        formatted = {
            'title': '🔄 Command Workflows & Patterns',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result['timestamp'])),
            'total_workflows': len(workflows),
            'workflows': {},
            'recommendations': result.get('context_recommendations', [])
        }
        
        for workflow_id, workflow in workflows.items():
            formatted_workflow = {
                'name': workflow.get('name', workflow_id),
                'description': workflow.get('description', ''),
                'estimated_time': workflow.get('estimated_time', 'Unknown'),
                'success_rate': workflow.get('success_rate', 'Unknown')
            }
            
            if 'steps' in workflow:
                formatted_workflow['steps'] = []
                for i, step in enumerate(workflow['steps'], 1):
                    formatted_step = {
                        'step': i,
                        'command': step.get('command', ''),
                        'purpose': step.get('purpose', ''),
                        'parameters': step.get('params', '')
                    }
                    formatted_workflow['steps'].append(formatted_step)
            
            if 'patterns' in workflow:
                formatted_workflow['patterns'] = workflow['patterns']
            
            formatted['workflows'][workflow_id] = formatted_workflow
        
        return formatted
    
    async def _format_recent(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format recent commands output"""
        recent_commands = result.get('recent_commands', [])
        
        formatted = {
            'title': '⏱️ Recent Command History',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result['timestamp'])),
            'total_commands': len(recent_commands),
            'usage_statistics': result.get('usage_statistics', {}),
            'patterns': result.get('patterns', {}),
            'recommendations': result.get('recommendations', []),
            'recent_commands': []
        }
        
        for i, cmd in enumerate(recent_commands, 1):
            formatted_cmd = {
                'number': i,
                'command': cmd.get('command', 'unknown'),
                'timestamp': time.strftime('%H:%M:%S', time.localtime(cmd.get('timestamp', time.time()))),
                'success': '✓' if cmd.get('success', True) else '✗',
                'execution_time': f"{cmd.get('execution_time', 0):.2f}s",
                'context': cmd.get('context', 'general')
            }
            formatted['recent_commands'].append(formatted_cmd)
        
        return formatted
    
    async def _format_suggestions(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format command suggestions output"""
        suggestions = result.get('suggestions', [])
        
        formatted = {
            'title': '🎯 Smart Command Suggestions',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result['timestamp'])),
            'context': result.get('context', {}),
            'total_suggestions': len(suggestions),
            'reasoning': result.get('reasoning', []),
            'suggestions': []
        }
        
        for i, suggestion in enumerate(suggestions, 1):
            formatted_suggestion = {
                'rank': i,
                'command': suggestion.command,
                'confidence': f"{suggestion.confidence:.0%}",
                'reason': suggestion.reason,
                'example': suggestion.example,
                'related_commands': suggestion.related_commands
            }
            
            if suggestion.parameters:
                formatted_suggestion['suggested_parameters'] = suggestion.parameters
            
            formatted['suggestions'].append(formatted_suggestion)
        
        return formatted
    
    async def _format_validation(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format command validation output"""
        formatted = {
            'title': '✅ Command Validation',
            'command': result.get('command', ''),
            'valid': result.get('valid', False),
            'parameters': result.get('parameters', {}),
            'status': '✓ Valid' if result.get('valid') else '✗ Invalid'
        }
        
        if result.get('error'):
            formatted['error'] = result['error']
        
        if result.get('warnings'):
            formatted['warnings'] = result['warnings']
        
        if result.get('suggestions'):
            formatted['suggestions'] = result['suggestions']
        
        return formatted
    
    async def _format_completion(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format command completion output"""
        completions = result.get('completions', [])
        
        formatted = {
            'title': '⌨️ Command Completion',
            'query': result.get('query', ''),
            'total_completions': len(completions),
            'completions': []
        }
        
        for completion in completions:
            formatted_completion = {
                'completion': completion.get('completion', ''),
                'type': completion.get('type', 'unknown'),
                'description': completion.get('description', ''),
                'confidence': f"{completion.get('confidence', 0):.0%}"
            }
            formatted['completions'].append(formatted_completion)
        
        return formatted
    
    async def _format_analytics(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format help analytics output"""
        formatted = {
            'title': '📊 Help System Analytics',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result['timestamp'])),
            'total_interactions': result.get('total_help_interactions', 0),
            'help_types': result.get('help_type_breakdown', {}),
            'command_stats': result.get('command_usage_stats', {}),
            'popular_commands': result.get('most_popular_commands', []),
            'context_distribution': result.get('context_distribution', {})
        }
        
        return formatted

# Tool registration functions for MCP server
async def register_interactive_help_tools(server, storage, config):
    """Register all interactive help tools with the MCP server"""
    tools = InteractiveHelpMCPTools(storage, config)
    
    @server.tool("help_show")
    async def help_show(command: Optional[str] = None, detailed: bool = False):
        """Show interactive help for hAIveMind commands with context-aware suggestions"""
        return await tools.show_help(command, detailed)
    
    @server.tool("help_examples")
    async def help_examples(command: Optional[str] = None, context: Optional[str] = None):
        """Show relevant examples for commands or contexts with explanations"""
        return await tools.show_examples(command, context)
    
    @server.tool("help_workflows")
    async def help_workflows():
        """Show common command workflows and patterns with step-by-step guidance"""
        return await tools.show_workflows()
    
    @server.tool("help_recent")
    async def help_recent(limit: int = 10):
        """Show recently used commands and their outcomes with pattern analysis"""
        return await tools.show_recent(limit)
    
    @server.tool("help_suggest")
    async def help_suggest(context: Optional[str] = None, intent: Optional[str] = None):
        """Get AI-powered command suggestions based on current context and intent"""
        return await tools.suggest_commands(context, intent)
    
    @server.tool("help_validate")
    async def help_validate(command: str, **parameters):
        """Validate command syntax and parameters before execution"""
        return await tools.validate_command(command, **parameters)
    
    @server.tool("help_complete")
    async def help_complete(partial_command: str):
        """Get smart command completion suggestions with confidence scores"""
        return await tools.get_command_completion(partial_command)
    
    @server.tool("help_track_usage")
    async def help_track_usage(command: str, success: bool = True, 
                              execution_time: float = 0, context: str = "", 
                              **parameters):
        """Track command usage for learning and improvement"""
        return await tools.track_command_usage(command, success, execution_time, context, **parameters)
    
    @server.tool("help_analytics")
    async def help_analytics():
        """Get help system usage analytics and effectiveness metrics"""
        return await tools.get_help_analytics()
    
    logger.info("Registered 9 interactive help MCP tools")
    return tools