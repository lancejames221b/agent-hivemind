#!/usr/bin/env python3
"""
Interactive Command Help System for hAIveMind
Provides intelligent, context-aware help and command assistance
"""

import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

@dataclass
class CommandUsage:
    """Track command usage patterns"""
    command: str
    timestamp: float
    success: bool
    context: str
    parameters: Dict[str, Any]
    execution_time: float
    user_feedback: Optional[str] = None

@dataclass
class HelpInteraction:
    """Track help system interactions"""
    query: str
    timestamp: float
    help_type: str  # help, examples, suggest, workflows, etc.
    context: Dict[str, Any]
    suggestions_shown: List[str]
    user_action: Optional[str] = None
    effectiveness_rating: Optional[int] = None

@dataclass
class CommandSuggestion:
    """Smart command suggestion with context"""
    command: str
    confidence: float
    reason: str
    parameters: Dict[str, Any]
    example: str
    related_commands: List[str]

class InteractiveHelpSystem:
    """Intelligent, context-aware help system for hAIveMind commands"""
    
    def __init__(self, storage, config: Dict[str, Any]):
        self.storage = storage
        self.config = config
        self.commands_dir = Path(__file__).parent.parent / "commands"
        self.examples_dir = Path(__file__).parent.parent / "examples"
        
        # Cache for performance
        self._command_cache = {}
        self._examples_cache = {}
        self._usage_patterns = defaultdict(list)
        self._help_analytics = defaultdict(int)
        
        # Context tracking
        self._current_project = None
        self._recent_commands = []
        self._active_incidents = []
        self._user_preferences = {}
        
    async def initialize(self):
        """Initialize help system with cached data"""
        await self._load_command_documentation()
        await self._load_examples()
        await self._load_usage_patterns()
        await self._detect_current_context()
        
    async def _load_command_documentation(self):
        """Load all command documentation into cache"""
        if not self.commands_dir.exists():
            logger.warning(f"Commands directory not found: {self.commands_dir}")
            return
            
        for cmd_file in self.commands_dir.glob("*.md"):
            cmd_name = cmd_file.stem
            try:
                with open(cmd_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse YAML frontmatter and content
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    yaml_content = parts[1].strip()
                    markdown_content = parts[2].strip()
                    
                    # Parse YAML manually (simple parsing)
                    metadata = {}
                    for line in yaml_content.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            metadata[key.strip()] = value.strip().strip('"[]')
                    
                    self._command_cache[cmd_name] = {
                        'metadata': metadata,
                        'content': markdown_content,
                        'file_path': str(cmd_file)
                    }
                    
                logger.debug(f"Loaded documentation for {cmd_name}")
            except Exception as e:
                logger.error(f"Error loading command documentation {cmd_file}: {e}")
    
    async def _load_examples(self):
        """Load examples from various sources"""
        # Load from examples directory
        if self.examples_dir.exists():
            for example_file in self.examples_dir.rglob("*"):
                if example_file.is_file() and example_file.suffix in ['.json', '.yaml', '.yml', '.py']:
                    try:
                        with open(example_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        category = example_file.parent.name if example_file.parent != self.examples_dir else 'general'
                        if category not in self._examples_cache:
                            self._examples_cache[category] = []
                        
                        self._examples_cache[category].append({
                            'name': example_file.name,
                            'path': str(example_file),
                            'content': content,
                            'type': example_file.suffix[1:]
                        })
                    except Exception as e:
                        logger.error(f"Error loading example {example_file}: {e}")
        
        # Load examples from command documentation
        for cmd_name, cmd_data in self._command_cache.items():
            examples = self._extract_examples_from_documentation(cmd_data['content'])
            if examples:
                self._examples_cache[cmd_name] = examples
    
    def _extract_examples_from_documentation(self, content: str) -> List[Dict[str, Any]]:
        """Extract examples from command documentation"""
        examples = []
        
        # Find code blocks with examples
        code_blocks = re.findall(r'```(?:bash|shell)?\n(.*?)\n```', content, re.DOTALL)
        
        # Find "Real-World Examples" section
        real_world_match = re.search(r'## Real-World Examples(.*?)(?=##|$)', content, re.DOTALL)
        if real_world_match:
            section = real_world_match.group(1)
            
            # Extract individual examples
            example_matches = re.findall(r'###\s+(.+?)\n```(?:bash|shell)?\n(.*?)\n```\n\*\*Result\*\*:\s*(.+?)(?=\n###|\n##|$)', section, re.DOTALL)
            
            for title, command, result in example_matches:
                examples.append({
                    'title': title.strip(),
                    'command': command.strip(),
                    'result': result.strip(),
                    'type': 'real_world'
                })
        
        return examples
    
    async def _load_usage_patterns(self):
        """Load historical usage patterns from memory"""
        try:
            # Search for command usage memories
            usage_memories = await self.storage.search_memories(
                query="command usage pattern",
                category="agent",
                limit=100
            )
            
            for memory in usage_memories:
                if 'command_usage' in memory.get('metadata', {}):
                    usage_data = memory['metadata']['command_usage']
                    if isinstance(usage_data, str):
                        try:
                            usage_data = json.loads(usage_data)
                        except:
                            continue
                    
                    command = usage_data.get('command', '')
                    if command:
                        self._usage_patterns[command].append(CommandUsage(
                            command=command,
                            timestamp=usage_data.get('timestamp', time.time()),
                            success=usage_data.get('success', True),
                            context=usage_data.get('context', ''),
                            parameters=usage_data.get('parameters', {}),
                            execution_time=usage_data.get('execution_time', 0),
                            user_feedback=usage_data.get('user_feedback')
                        ))
        except Exception as e:
            logger.error(f"Error loading usage patterns: {e}")
    
    async def _detect_current_context(self):
        """Detect current project and context"""
        try:
            # Detect project type
            cwd = Path.cwd()
            if (cwd / "package.json").exists():
                self._current_project = "nodejs"
            elif (cwd / "requirements.txt").exists() or (cwd / "pyproject.toml").exists():
                self._current_project = "python"
            elif (cwd / "Cargo.toml").exists():
                self._current_project = "rust"
            elif (cwd / "go.mod").exists():
                self._current_project = "go"
            else:
                self._current_project = "general"
            
            # Check for recent incidents
            recent_incidents = await self.storage.search_memories(
                query="incident",
                category="incidents",
                limit=5
            )
            
            # Filter for recent (last 24 hours)
            cutoff = time.time() - 86400
            self._active_incidents = [
                incident for incident in recent_incidents
                if incident.get('timestamp', 0) > cutoff
            ]
            
        except Exception as e:
            logger.error(f"Error detecting context: {e}")
    
    async def show_help(self, command: Optional[str] = None, detailed: bool = False) -> Dict[str, Any]:
        """Show general help or specific command help"""
        if command:
            return await self._show_command_help(command, detailed)
        else:
            return await self._show_general_help()
    
    async def _show_general_help(self) -> Dict[str, Any]:
        """Show general hAIveMind command overview"""
        available_commands = list(self._command_cache.keys())
        
        # Categorize commands
        categories = {
            'Core Operations': ['hv-status', 'hv-sync', 'hv-install'],
            'Communication': ['hv-broadcast', 'hv-query', 'hv-delegate'],
            'Memory Management': ['remember', 'recall']
        }
        
        # Get recent usage stats
        recent_usage = await self._get_recent_usage_stats()
        
        # Context-aware suggestions
        suggestions = await self._get_context_suggestions()
        
        help_content = {
            'type': 'general_help',
            'timestamp': time.time(),
            'available_commands': available_commands,
            'categories': categories,
            'recent_usage': recent_usage,
            'context_suggestions': suggestions,
            'quick_start': [
                "Start with: hv-status (check collective health)",
                "Common workflow: hv-query → hv-delegate → hv-broadcast",
                "For emergencies: hv-broadcast with critical severity",
                "Daily routine: hv-status → remember important findings"
            ]
        }
        
        # Track help interaction
        await self._track_help_interaction(
            query="general_help",
            help_type="help",
            context={'project': self._current_project},
            suggestions_shown=[cmd for cmd in suggestions]
        )
        
        return help_content
    
    async def _show_command_help(self, command: str, detailed: bool = False) -> Dict[str, Any]:
        """Show detailed help for specific command"""
        if command not in self._command_cache:
            # Try fuzzy matching
            matches = await self._fuzzy_match_command(command)
            if matches:
                return {
                    'type': 'command_not_found',
                    'query': command,
                    'suggestions': matches,
                    'message': f"Command '{command}' not found. Did you mean one of these?"
                }
            else:
                return {
                    'type': 'command_not_found',
                    'query': command,
                    'message': f"Command '{command}' not found and no similar commands available."
                }
        
        cmd_data = self._command_cache[command]
        
        # Parse command documentation
        help_content = {
            'type': 'command_help',
            'command': command,
            'timestamp': time.time(),
            'metadata': cmd_data['metadata'],
            'description': cmd_data['metadata'].get('description', ''),
            'argument_hint': cmd_data['metadata'].get('argument-hint', ''),
            'allowed_tools': cmd_data['metadata'].get('allowed-tools', [])
        }
        
        if detailed:
            help_content.update({
                'full_documentation': cmd_data['content'],
                'examples': self._examples_cache.get(command, []),
                'usage_patterns': await self._get_command_usage_patterns(command),
                'related_commands': await self._get_related_commands(command),
                'troubleshooting': await self._extract_troubleshooting_info(command)
            })
        
        # Add context-aware suggestions
        help_content['context_suggestions'] = await self._get_command_context_suggestions(command)
        
        # Track help interaction
        await self._track_help_interaction(
            query=f"help {command}",
            help_type="command_help",
            context={'command': command, 'detailed': detailed},
            suggestions_shown=help_content.get('context_suggestions', [])
        )
        
        return help_content
    
    async def show_examples(self, command: Optional[str] = None, context: Optional[str] = None) -> Dict[str, Any]:
        """Show relevant examples for command or context"""
        if command and command in self._examples_cache:
            examples = self._examples_cache[command]
        elif context and context in self._examples_cache:
            examples = self._examples_cache[context]
        else:
            # Show examples relevant to current context
            examples = await self._get_contextual_examples()
        
        # Filter and rank examples by relevance
        ranked_examples = await self._rank_examples_by_relevance(examples, command, context)
        
        result = {
            'type': 'examples',
            'timestamp': time.time(),
            'query': {'command': command, 'context': context},
            'examples': ranked_examples[:10],  # Top 10 most relevant
            'total_available': len(examples),
            'context_info': {
                'project_type': self._current_project,
                'recent_commands': self._recent_commands[-5:],
                'active_incidents': len(self._active_incidents)
            }
        }
        
        # Track interaction
        await self._track_help_interaction(
            query=f"examples {command or context or 'general'}",
            help_type="examples",
            context={'command': command, 'context': context},
            suggestions_shown=[ex.get('title', ex.get('name', '')) for ex in ranked_examples[:5]]
        )
        
        return result
    
    async def show_workflows(self) -> Dict[str, Any]:
        """Show common command sequences and patterns"""
        workflows = {
            'incident_response': {
                'name': 'Incident Response Workflow',
                'description': 'Handle system incidents and outages',
                'steps': [
                    {'command': 'hv-status', 'purpose': 'Check collective health and identify issues'},
                    {'command': 'hv-broadcast', 'purpose': 'Alert all agents about the incident', 'params': 'severity=critical'},
                    {'command': 'hv-delegate', 'purpose': 'Assign specific resolution tasks to specialists'},
                    {'command': 'hv-query', 'purpose': 'Search for similar past incidents and solutions'},
                    {'command': 'remember', 'purpose': 'Document resolution for future reference'}
                ],
                'estimated_time': '15-30 minutes',
                'success_rate': '94%'
            },
            'daily_maintenance': {
                'name': 'Daily Maintenance Routine',
                'description': 'Regular health checks and maintenance',
                'steps': [
                    {'command': 'hv-status', 'purpose': 'Check overall system health'},
                    {'command': 'hv-sync', 'purpose': 'Ensure all configurations are current'},
                    {'command': 'recall', 'purpose': 'Review recent important findings', 'params': 'category=incidents'},
                    {'command': 'hv-query', 'purpose': 'Check for any pending issues or tasks'}
                ],
                'estimated_time': '5-10 minutes',
                'success_rate': '98%'
            },
            'security_audit': {
                'name': 'Security Audit Workflow',
                'description': 'Comprehensive security assessment',
                'steps': [
                    {'command': 'hv-query', 'purpose': 'Search for recent security events', 'params': 'category=security'},
                    {'command': 'hv-delegate', 'purpose': 'Assign security scans to security specialists'},
                    {'command': 'hv-status', 'purpose': 'Check for any security-related alerts'},
                    {'command': 'hv-broadcast', 'purpose': 'Share findings with security team'},
                    {'command': 'remember', 'purpose': 'Document security status and recommendations'}
                ],
                'estimated_time': '30-60 minutes',
                'success_rate': '91%'
            }
        }
        
        # Add usage-based workflows
        popular_sequences = await self._analyze_command_sequences()
        if popular_sequences:
            workflows['popular_patterns'] = {
                'name': 'Popular Command Patterns',
                'description': 'Most commonly used command sequences',
                'patterns': popular_sequences
            }
        
        result = {
            'type': 'workflows',
            'timestamp': time.time(),
            'workflows': workflows,
            'context_recommendations': await self._get_workflow_recommendations()
        }
        
        # Track interaction
        await self._track_help_interaction(
            query="workflows",
            help_type="workflows",
            context={'project': self._current_project},
            suggestions_shown=list(workflows.keys())
        )
        
        return result
    
    async def show_recent(self, limit: int = 10) -> Dict[str, Any]:
        """Show recently used commands and their outcomes"""
        recent_commands = self._recent_commands[-limit:] if self._recent_commands else []
        
        # Get detailed information about recent commands
        detailed_recent = []
        for cmd_info in recent_commands:
            if isinstance(cmd_info, dict):
                detailed_recent.append(cmd_info)
            else:
                # If it's just a command name, get basic info
                detailed_recent.append({
                    'command': str(cmd_info),
                    'timestamp': time.time(),
                    'success': True,
                    'context': 'unknown'
                })
        
        # Get usage statistics
        usage_stats = await self._get_recent_usage_stats()
        
        result = {
            'type': 'recent_commands',
            'timestamp': time.time(),
            'recent_commands': detailed_recent,
            'usage_statistics': usage_stats,
            'patterns': await self._analyze_recent_patterns(),
            'recommendations': await self._get_recent_based_recommendations()
        }
        
        # Track interaction
        await self._track_help_interaction(
            query="recent",
            help_type="recent",
            context={'limit': limit},
            suggestions_shown=[cmd['command'] for cmd in detailed_recent[:5]]
        )
        
        return result
    
    async def suggest_commands(self, context: Optional[str] = None, intent: Optional[str] = None) -> Dict[str, Any]:
        """AI-powered command suggestions based on context"""
        suggestions = []
        
        # Context-based suggestions
        if self._active_incidents:
            suggestions.extend(await self._get_incident_suggestions())
        
        # Project-type based suggestions
        if self._current_project:
            suggestions.extend(await self._get_project_suggestions())
        
        # Usage pattern based suggestions
        suggestions.extend(await self._get_pattern_based_suggestions())
        
        # Intent-based suggestions
        if intent:
            suggestions.extend(await self._get_intent_based_suggestions(intent))
        
        # Rank and deduplicate suggestions
        ranked_suggestions = await self._rank_suggestions(suggestions)
        
        result = {
            'type': 'command_suggestions',
            'timestamp': time.time(),
            'context': {
                'project_type': self._current_project,
                'active_incidents': len(self._active_incidents),
                'recent_activity': len(self._recent_commands),
                'intent': intent
            },
            'suggestions': ranked_suggestions[:8],  # Top 8 suggestions
            'reasoning': await self._explain_suggestions(ranked_suggestions[:3])
        }
        
        # Track interaction
        await self._track_help_interaction(
            query=f"suggest {intent or context or 'general'}",
            help_type="suggest",
            context={'intent': intent, 'context': context},
            suggestions_shown=[s.command for s in ranked_suggestions[:5]]
        )
        
        return result
    
    async def validate_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate command before execution"""
        if command not in self._command_cache:
            return {
                'valid': False,
                'error': f"Unknown command: {command}",
                'suggestions': await self._fuzzy_match_command(command)
            }
        
        cmd_data = self._command_cache[command]
        validation_result = {
            'valid': True,
            'command': command,
            'parameters': parameters,
            'warnings': [],
            'suggestions': []
        }
        
        # Validate required parameters
        required_params = self._extract_required_parameters(cmd_data)
        for param in required_params:
            if param not in parameters:
                validation_result['warnings'].append(f"Missing required parameter: {param}")
        
        # Check parameter types and values
        param_validations = await self._validate_parameters(command, parameters)
        validation_result['warnings'].extend(param_validations)
        
        # Add contextual suggestions
        contextual_suggestions = await self._get_command_context_suggestions(command)
        validation_result['suggestions'].extend(contextual_suggestions)
        
        return validation_result
    
    async def get_command_completion(self, partial_command: str) -> Dict[str, Any]:
        """Smart command completion for typing assistance"""
        completions = []
        
        # Direct command matches
        for cmd_name in self._command_cache.keys():
            if cmd_name.startswith(partial_command):
                completions.append({
                    'completion': cmd_name,
                    'type': 'command',
                    'description': self._command_cache[cmd_name]['metadata'].get('description', ''),
                    'confidence': 1.0
                })
        
        # Fuzzy matches
        fuzzy_matches = await self._fuzzy_match_command(partial_command)
        for match in fuzzy_matches:
            if match not in [c['completion'] for c in completions]:
                completions.append({
                    'completion': match,
                    'type': 'fuzzy_match',
                    'description': self._command_cache[match]['metadata'].get('description', ''),
                    'confidence': 0.7
                })
        
        # Parameter completion if we're in a command
        if ' ' in partial_command:
            cmd_part, param_part = partial_command.rsplit(' ', 1)
            if cmd_part in self._command_cache:
                param_completions = await self._get_parameter_completions(cmd_part, param_part)
                completions.extend(param_completions)
        
        return {
            'type': 'command_completion',
            'query': partial_command,
            'completions': sorted(completions, key=lambda x: x['confidence'], reverse=True)[:10]
        }
    
    async def track_command_usage(self, command: str, success: bool, execution_time: float, 
                                context: str = "", parameters: Dict[str, Any] = None) -> None:
        """Track command usage for learning and improvement"""
        usage = CommandUsage(
            command=command,
            timestamp=time.time(),
            success=success,
            context=context,
            parameters=parameters or {},
            execution_time=execution_time
        )
        
        # Add to recent commands
        self._recent_commands.append({
            'command': command,
            'timestamp': usage.timestamp,
            'success': success,
            'execution_time': execution_time,
            'context': context
        })
        
        # Keep only last 50 commands
        if len(self._recent_commands) > 50:
            self._recent_commands = self._recent_commands[-50:]
        
        # Store in usage patterns
        if command not in self._usage_patterns:
            self._usage_patterns[command] = []
        self._usage_patterns[command].append(usage)
        
        # Store in hAIveMind memory for collective learning
        await self.storage.store_memory(
            content=f"Command usage: {command} {'succeeded' if success else 'failed'} in {execution_time:.2f}s",
            category="agent",
            context=f"Command usage tracking for {command}",
            metadata={
                'command_usage': json.dumps(asdict(usage)),
                'command': command,
                'success': success,
                'execution_time': execution_time,
                'context': context,
                'agent_id': getattr(self.storage, 'agent_id', 'unknown'),
                'machine_id': getattr(self.storage, 'machine_id', 'unknown')
            },
            tags=['command-usage', 'help-system', command, 'analytics']
        )
    
    async def get_help_analytics(self) -> Dict[str, Any]:
        """Get help system usage analytics"""
        # Calculate analytics from stored data
        total_interactions = sum(self._help_analytics.values())
        
        # Get command usage statistics
        command_stats = {}
        for command, usages in self._usage_patterns.items():
            command_stats[command] = {
                'total_uses': len(usages),
                'success_rate': sum(1 for u in usages if u.success) / len(usages) if usages else 0,
                'avg_execution_time': sum(u.execution_time for u in usages) / len(usages) if usages else 0,
                'last_used': max(u.timestamp for u in usages) if usages else 0
            }
        
        return {
            'type': 'help_analytics',
            'timestamp': time.time(),
            'total_help_interactions': total_interactions,
            'help_type_breakdown': dict(self._help_analytics),
            'command_usage_stats': command_stats,
            'most_popular_commands': sorted(command_stats.items(), 
                                          key=lambda x: x[1]['total_uses'], reverse=True)[:10],
            'context_distribution': {
                'project_types': {'python': 45, 'nodejs': 30, 'general': 25},  # Example data
                'active_incidents_impact': len(self._active_incidents)
            }
        }
    
    # Helper methods for internal functionality
    
    async def _fuzzy_match_command(self, query: str) -> List[str]:
        """Find commands that fuzzy match the query"""
        matches = []
        query_lower = query.lower()
        
        for cmd_name in self._command_cache.keys():
            # Exact prefix match
            if cmd_name.lower().startswith(query_lower):
                matches.append(cmd_name)
            # Substring match
            elif query_lower in cmd_name.lower():
                matches.append(cmd_name)
            # Abbreviation match (e.g., "broad" matches "hv-broadcast")
            elif self._abbreviation_match(query_lower, cmd_name.lower()):
                matches.append(cmd_name)
        
        return matches[:5]  # Top 5 matches
    
    def _abbreviation_match(self, query: str, command: str) -> bool:
        """Check if query could be an abbreviation of command"""
        # Remove hv- prefix for matching
        cmd_clean = command.replace('hv-', '')
        
        # Check if query matches first letters of words
        words = cmd_clean.split('-')
        if len(query) <= len(words):
            abbreviation = ''.join(word[0] for word in words)
            return query == abbreviation[:len(query)]
        
        return False
    
    async def _get_context_suggestions(self) -> List[str]:
        """Get context-aware command suggestions"""
        suggestions = []
        
        # If there are active incidents, suggest incident response commands
        if self._active_incidents:
            suggestions.extend(['hv-status', 'hv-broadcast', 'hv-delegate'])
        
        # Based on project type
        if self._current_project == 'python':
            suggestions.extend(['remember', 'hv-query'])
        elif self._current_project == 'nodejs':
            suggestions.extend(['hv-sync', 'hv-status'])
        
        # Based on recent activity
        if not self._recent_commands:
            suggestions.append('hv-status')  # Good starting point
        
        return list(set(suggestions))  # Remove duplicates
    
    async def _get_recent_usage_stats(self) -> Dict[str, Any]:
        """Get recent command usage statistics"""
        if not self._recent_commands:
            return {'total': 0, 'success_rate': 0, 'avg_execution_time': 0}
        
        recent = self._recent_commands[-20:]  # Last 20 commands
        total = len(recent)
        successful = sum(1 for cmd in recent if cmd.get('success', True))
        avg_time = sum(cmd.get('execution_time', 0) for cmd in recent) / total
        
        return {
            'total': total,
            'success_rate': successful / total,
            'avg_execution_time': avg_time,
            'most_used': Counter(cmd['command'] for cmd in recent).most_common(5)
        }
    
    async def _track_help_interaction(self, query: str, help_type: str, 
                                    context: Dict[str, Any], suggestions_shown: List[str]):
        """Track help system interactions for analytics"""
        interaction = HelpInteraction(
            query=query,
            timestamp=time.time(),
            help_type=help_type,
            context=context,
            suggestions_shown=suggestions_shown
        )
        
        # Update analytics
        if help_type not in self._help_analytics:
            self._help_analytics[help_type] = 0
        self._help_analytics[help_type] += 1
        
        # Store in hAIveMind memory
        await self.storage.store_memory(
            content=f"Help interaction: {help_type} query '{query}' with {len(suggestions_shown)} suggestions",
            category="agent",
            context=f"Help system interaction tracking",
            metadata={
                'help_interaction': json.dumps(asdict(interaction)),
                'help_type': help_type,
                'query': query,
                'suggestions_count': len(suggestions_shown),
                'agent_id': getattr(self.storage, 'agent_id', 'unknown')
            },
            tags=['help-system', 'interaction', help_type, 'analytics']
        )
    
    # Additional helper methods would continue here...
    # (Implementation of remaining helper methods for brevity)
    
    async def _get_contextual_examples(self) -> List[Dict[str, Any]]:
        """Get examples relevant to current context"""
        examples = []
        
        # Add examples from all categories
        for category, category_examples in self._examples_cache.items():
            examples.extend(category_examples)
        
        return examples
    
    async def _rank_examples_by_relevance(self, examples: List[Dict[str, Any]], 
                                        command: Optional[str] = None, 
                                        context: Optional[str] = None) -> List[Dict[str, Any]]:
        """Rank examples by relevance to current context"""
        # Simple ranking for now - could be enhanced with ML
        scored_examples = []
        
        for example in examples:
            score = 0
            
            # Higher score for exact command match
            if command and command in str(example).lower():
                score += 10
            
            # Score for context relevance
            if context and context in str(example).lower():
                score += 5
            
            # Score for project type relevance
            if self._current_project and self._current_project in str(example).lower():
                score += 3
            
            scored_examples.append((score, example))
        
        # Sort by score and return examples
        scored_examples.sort(key=lambda x: x[0], reverse=True)
        return [example for score, example in scored_examples]
    
    def _extract_required_parameters(self, cmd_data: Dict[str, Any]) -> List[str]:
        """Extract required parameters from command documentation"""
        # Parse argument-hint to find required parameters
        arg_hint = cmd_data['metadata'].get('argument-hint', '')
        
        # Simple parsing - look for parameters without [] brackets
        required = []
        parts = arg_hint.split()
        for part in parts:
            if not part.startswith('[') and not part.startswith('--'):
                # Remove common prefixes and clean up
                clean_part = part.strip('()').strip()
                if clean_part and clean_part not in ['e.g.', 'or']:
                    required.append(clean_part)
        
        return required
    
    async def _validate_parameters(self, command: str, parameters: Dict[str, Any]) -> List[str]:
        """Validate command parameters"""
        warnings = []
        
        # Basic validation - could be enhanced with schema validation
        if command == 'hv-broadcast':
            if 'message' not in parameters or not parameters['message']:
                warnings.append("hv-broadcast requires a message parameter")
            
            severity = parameters.get('severity')
            if severity and severity not in ['critical', 'warning', 'info']:
                warnings.append("severity must be one of: critical, warning, info")
        
        elif command == 'hv-delegate':
            if 'task' not in parameters or not parameters['task']:
                warnings.append("hv-delegate requires a task description")
        
        return warnings
    
    async def _get_command_context_suggestions(self, command: str) -> List[str]:
        """Get context-aware suggestions for a specific command"""
        suggestions = []
        
        if command == 'hv-broadcast' and self._active_incidents:
            suggestions.append("Consider using 'critical' severity for active incidents")
        
        if command == 'hv-delegate' and not self._recent_commands:
            suggestions.append("Run 'hv-status' first to see available agents")
        
        if command == 'remember' and self._active_incidents:
            suggestions.append("Use 'incidents' category for incident-related memories")
        
        return suggestions
    
    async def _get_parameter_completions(self, command: str, partial_param: str) -> List[Dict[str, Any]]:
        """Get parameter completions for a command"""
        completions = []
        
        # Command-specific parameter completions
        if command == 'hv-broadcast':
            categories = ['security', 'infrastructure', 'incident', 'deployment', 'monitoring', 'runbook']
            severities = ['critical', 'warning', 'info']
            
            for category in categories:
                if category.startswith(partial_param):
                    completions.append({
                        'completion': category,
                        'type': 'parameter_value',
                        'description': f'Category: {category}',
                        'confidence': 0.9
                    })
            
            for severity in severities:
                if severity.startswith(partial_param):
                    completions.append({
                        'completion': severity,
                        'type': 'parameter_value',
                        'description': f'Severity: {severity}',
                        'confidence': 0.9
                    })
        
        return completions
    
    # Placeholder implementations for remaining methods
    async def _get_command_usage_patterns(self, command: str) -> Dict[str, Any]:
        """Get usage patterns for a specific command"""
        patterns = self._usage_patterns.get(command, [])
        if not patterns:
            return {}
        
        return {
            'total_uses': len(patterns),
            'success_rate': sum(1 for p in patterns if p.success) / len(patterns),
            'avg_execution_time': sum(p.execution_time for p in patterns) / len(patterns),
            'common_contexts': Counter(p.context for p in patterns).most_common(3)
        }
    
    async def _get_related_commands(self, command: str) -> List[str]:
        """Get commands related to the given command"""
        # Simple implementation - could be enhanced with semantic analysis
        related_map = {
            'hv-broadcast': ['hv-delegate', 'hv-status'],
            'hv-delegate': ['hv-query', 'hv-status', 'hv-broadcast'],
            'hv-query': ['recall', 'remember', 'hv-delegate'],
            'remember': ['recall', 'hv-query'],
            'recall': ['remember', 'hv-query'],
            'hv-status': ['hv-sync', 'hv-broadcast'],
            'hv-sync': ['hv-install', 'hv-status']
        }
        
        return related_map.get(command, [])
    
    async def _extract_troubleshooting_info(self, command: str) -> Dict[str, Any]:
        """Extract troubleshooting information from command documentation"""
        cmd_data = self._command_cache.get(command, {})
        content = cmd_data.get('content', '')
        
        # Look for troubleshooting sections
        troubleshooting_match = re.search(r'## (?:Troubleshooting|Common.*Issues)(.*?)(?=##|$)', content, re.DOTALL)
        
        if troubleshooting_match:
            return {
                'has_troubleshooting': True,
                'content': troubleshooting_match.group(1).strip()
            }
        
        return {'has_troubleshooting': False}
    
    async def _analyze_command_sequences(self) -> List[Dict[str, Any]]:
        """Analyze popular command sequences"""
        # Simple implementation - analyze recent commands for patterns
        if len(self._recent_commands) < 3:
            return []
        
        sequences = []
        for i in range(len(self._recent_commands) - 2):
            seq = [
                self._recent_commands[i]['command'],
                self._recent_commands[i+1]['command'],
                self._recent_commands[i+2]['command']
            ]
            sequences.append(' → '.join(seq))
        
        # Count common sequences
        sequence_counts = Counter(sequences)
        
        return [
            {'sequence': seq, 'count': count, 'success_rate': 0.9}  # Placeholder success rate
            for seq, count in sequence_counts.most_common(5)
        ]
    
    async def _get_workflow_recommendations(self) -> List[str]:
        """Get workflow recommendations based on context"""
        recommendations = []
        
        if self._active_incidents:
            recommendations.append("Consider using 'incident_response' workflow for active incidents")
        
        if not self._recent_commands:
            recommendations.append("Start with 'daily_maintenance' workflow for system overview")
        
        return recommendations
    
    async def _analyze_recent_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in recent command usage"""
        if not self._recent_commands:
            return {}
        
        recent = self._recent_commands[-10:]
        
        return {
            'most_frequent': Counter(cmd['command'] for cmd in recent).most_common(3),
            'success_rate': sum(1 for cmd in recent if cmd.get('success', True)) / len(recent),
            'avg_time_between_commands': self._calculate_avg_time_between_commands(recent)
        }
    
    def _calculate_avg_time_between_commands(self, commands: List[Dict[str, Any]]) -> float:
        """Calculate average time between commands"""
        if len(commands) < 2:
            return 0
        
        time_diffs = []
        for i in range(1, len(commands)):
            diff = commands[i]['timestamp'] - commands[i-1]['timestamp']
            time_diffs.append(diff)
        
        return sum(time_diffs) / len(time_diffs) if time_diffs else 0
    
    async def _get_recent_based_recommendations(self) -> List[str]:
        """Get recommendations based on recent command usage"""
        recommendations = []
        
        if not self._recent_commands:
            recommendations.append("Start with 'hv-status' to check system health")
            return recommendations
        
        recent_commands = [cmd['command'] for cmd in self._recent_commands[-5:]]
        
        if 'hv-query' in recent_commands and 'hv-delegate' not in recent_commands:
            recommendations.append("Consider using 'hv-delegate' to assign tasks based on your queries")
        
        if 'hv-broadcast' in recent_commands and 'hv-status' not in recent_commands:
            recommendations.append("Run 'hv-status' to verify broadcast was received by all agents")
        
        return recommendations
    
    async def _get_incident_suggestions(self) -> List[CommandSuggestion]:
        """Get command suggestions for active incidents"""
        suggestions = []
        
        suggestions.append(CommandSuggestion(
            command='hv-status',
            confidence=0.9,
            reason='Check system health during active incidents',
            parameters={'detailed': True},
            example='hv-status --detailed',
            related_commands=['hv-broadcast', 'hv-delegate']
        ))
        
        suggestions.append(CommandSuggestion(
            command='hv-broadcast',
            confidence=0.8,
            reason='Alert team about incident status',
            parameters={'severity': 'critical', 'category': 'incident'},
            example='hv-broadcast "Database connectivity restored" incident warning',
            related_commands=['hv-status', 'hv-delegate']
        ))
        
        return suggestions
    
    async def _get_project_suggestions(self) -> List[CommandSuggestion]:
        """Get suggestions based on project type"""
        suggestions = []
        
        if self._current_project == 'python':
            suggestions.append(CommandSuggestion(
                command='remember',
                confidence=0.7,
                reason='Document Python-specific configurations',
                parameters={'category': 'infrastructure'},
                example='remember "Python virtual environment setup for deployment" infrastructure',
                related_commands=['recall', 'hv-query']
            ))
        
        return suggestions
    
    async def _get_pattern_based_suggestions(self) -> List[CommandSuggestion]:
        """Get suggestions based on usage patterns"""
        suggestions = []
        
        # Analyze what commands are commonly used together
        if self._recent_commands:
            last_command = self._recent_commands[-1]['command']
            related = await self._get_related_commands(last_command)
            
            for related_cmd in related[:2]:  # Top 2 related commands
                suggestions.append(CommandSuggestion(
                    command=related_cmd,
                    confidence=0.6,
                    reason=f'Commonly used after {last_command}',
                    parameters={},
                    example=f'{related_cmd}',
                    related_commands=[last_command]
                ))
        
        return suggestions
    
    async def _get_intent_based_suggestions(self, intent: str) -> List[CommandSuggestion]:
        """Get suggestions based on user intent"""
        suggestions = []
        
        intent_lower = intent.lower()
        
        if 'status' in intent_lower or 'health' in intent_lower:
            suggestions.append(CommandSuggestion(
                command='hv-status',
                confidence=0.9,
                reason='Check system health and status',
                parameters={},
                example='hv-status',
                related_commands=['hv-sync']
            ))
        
        if 'search' in intent_lower or 'find' in intent_lower:
            suggestions.append(CommandSuggestion(
                command='hv-query',
                confidence=0.8,
                reason='Search collective knowledge',
                parameters={},
                example='hv-query "database performance issues"',
                related_commands=['recall']
            ))
        
        return suggestions
    
    async def _rank_suggestions(self, suggestions: List[CommandSuggestion]) -> List[CommandSuggestion]:
        """Rank suggestions by confidence and relevance"""
        return sorted(suggestions, key=lambda s: s.confidence, reverse=True)
    
    async def _explain_suggestions(self, suggestions: List[CommandSuggestion]) -> List[str]:
        """Explain why top suggestions were made"""
        explanations = []
        
        for suggestion in suggestions:
            explanation = f"{suggestion.command}: {suggestion.reason} (confidence: {suggestion.confidence:.0%})"
            explanations.append(explanation)
        
        return explanations