#!/usr/bin/env python3
"""
hAIveMind Rules Engine MCP Tools
Provides MCP tool interface for rules management and evaluation

Author: Lance James, Unit 221B Inc  
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

from mcp.types import Tool, TextContent
from .rules_engine import (
    RulesEngine, Rule, RuleCondition, RuleAction, 
    RuleType, RuleScope, RulePriority, RuleStatus, ConflictResolution
)
from .rule_inheritance import RuleInheritanceManager, InheritanceContext
from .rule_validator import RuleValidator, ValidationLevel
from .haivemind_rules_integration import hAIveMindRulesIntegration

logger = logging.getLogger(__name__)

class RulesMCPTools:
    """MCP Tools for hAIveMind Rules Engine"""
    
    def __init__(self, memory_storage, config: Dict[str, Any]):
        self.memory_storage = memory_storage
        self.config = config
        
        # Initialize rules engine components
        db_path = config.get('rules_db_path', 'data/rules.db')
        self.rules_engine = RulesEngine(
            db_path=db_path,
            chroma_client=getattr(memory_storage, 'chroma_client', None),
            redis_client=getattr(memory_storage, 'redis_client', None),
            config=config
        )
        
        self.inheritance_manager = RuleInheritanceManager(self.rules_engine.db)
        self.validator = RuleValidator(config)
        self.haivemind_integration = hAIveMindRulesIntegration(
            self.rules_engine, 
            memory_storage,
            getattr(memory_storage, 'redis_client', None)
        )
    
    def get_tools(self) -> List[Tool]:
        """Get all rules engine MCP tools"""
        return [
            # Core rule management
            Tool(
                name="create_rule",
                description="Create a new governance rule for agent behavior",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Rule name"},
                        "description": {"type": "string", "description": "Rule description"},
                        "rule_type": {
                            "type": "string", 
                            "enum": [rt.value for rt in RuleType],
                            "description": "Type of rule"
                        },
                        "scope": {
                            "type": "string",
                            "enum": [rs.value for rs in RuleScope], 
                            "description": "Rule scope"
                        },
                        "priority": {
                            "type": "string",
                            "enum": [rp.name for rp in RulePriority],
                            "description": "Rule priority level"
                        },
                        "conditions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "field": {"type": "string"},
                                    "operator": {"type": "string"},
                                    "value": {},
                                    "case_sensitive": {"type": "boolean", "default": True}
                                },
                                "required": ["field", "operator", "value"]
                            },
                            "description": "Rule conditions"
                        },
                        "actions": {
                            "type": "array", 
                            "items": {
                                "type": "object",
                                "properties": {
                                    "action_type": {"type": "string"},
                                    "target": {"type": "string"},
                                    "value": {},
                                    "parameters": {"type": "object"}
                                },
                                "required": ["action_type", "target", "value"]
                            },
                            "description": "Rule actions"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Rule tags"
                        }
                    },
                    "required": ["name", "description", "rule_type", "scope", "priority", "actions"]
                }
            ),
            
            Tool(
                name="evaluate_rules",
                description="Evaluate rules for given context with hAIveMind awareness",
                inputSchema={
                    "type": "object", 
                    "properties": {
                        "context": {
                            "type": "object",
                            "description": "Evaluation context (agent_id, machine_id, project_id, etc.)"
                        },
                        "include_inheritance": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include rule inheritance processing"
                        }
                    },
                    "required": ["context"]
                }
            ),
            
            Tool(
                name="validate_rule",
                description="Validate rule definition for syntax and logic errors",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_definition": {
                            "type": "object",
                            "description": "Complete rule definition to validate"
                        },
                        "auto_fix": {
                            "type": "boolean", 
                            "default": False,
                            "description": "Attempt automatic fixes for validation issues"
                        }
                    },
                    "required": ["rule_definition"]
                }
            ),
            
            Tool(
                name="get_rule_suggestions",
                description="Get AI-powered suggestions for improving specific rules",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {
                            "type": "string",
                            "description": "ID of rule to analyze"
                        }
                    },
                    "required": ["rule_id"]
                }
            ),
            
            Tool(
                name="create_rule_override", 
                description="Create context-specific override for existing rule",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "base_rule_id": {"type": "string", "description": "Rule to override"},
                        "override_scope": {
                            "type": "string",
                            "enum": [rs.value for rs in RuleScope],
                            "description": "Scope for override"
                        },
                        "context_filters": {
                            "type": "object",
                            "description": "Context conditions for override"
                        },
                        "override_actions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "action_type": {"type": "string"},
                                    "target": {"type": "string"},
                                    "value": {}
                                }
                            },
                            "description": "Override actions"
                        },
                        "created_by": {"type": "string", "description": "Creator identifier"}
                    },
                    "required": ["base_rule_id", "override_scope", "context_filters", "override_actions", "created_by"]
                }
            ),
            
            Tool(
                name="get_rules_performance",
                description="Get performance analytics for rules evaluation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "top_n": {
                            "type": "integer",
                            "default": 10,
                            "description": "Number of top results to return"
                        },
                        "include_suggestions": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include optimization suggestions"
                        }
                    }
                }
            ),
            
            Tool(
                name="get_network_insights",
                description="Get rule insights from across hAIveMind network",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            ),
            
            Tool(
                name="sync_rules_network",
                description="Synchronize rules across hAIveMind network", 
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific rules to sync (empty for all)"
                        }
                    }
                }
            ),
            
            Tool(
                name="learn_from_patterns",
                description="Analyze rule usage patterns and generate learning insights",
                inputSchema={
                    "type": "object", 
                    "properties": {},
                    "additionalProperties": False
                }
            ),
            
            Tool(
                name="get_inheritance_tree",
                description="Get rule inheritance hierarchy tree",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "root_rule_id": {
                            "type": "string",
                            "description": "Root rule to trace inheritance from"
                        }
                    },
                    "required": ["root_rule_id"]
                }
            ),
            
            Tool(
                name="validate_rule_set",
                description="Validate a set of rules for conflicts and consistency",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_ids": {
                            "type": "array", 
                            "items": {"type": "string"},
                            "description": "Rule IDs to validate together"
                        }
                    },
                    "required": ["rule_ids"]
                }
            )
        ]
    
    async def handle_create_rule(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle create_rule tool call"""
        try:
            # Parse rule definition
            rule_data = arguments.copy()
            
            # Convert enum strings to objects
            rule_data['rule_type'] = RuleType(rule_data['rule_type'])
            rule_data['scope'] = RuleScope(rule_data['scope'])
            rule_data['priority'] = RulePriority[rule_data['priority']]
            
            # Create condition and action objects
            conditions = []
            for cond_data in rule_data.get('conditions', []):
                conditions.append(RuleCondition(**cond_data))
            
            actions = []
            for action_data in rule_data['actions']:
                actions.append(RuleAction(**action_data))
            
            # Create rule
            rule = Rule(
                id=str(uuid.uuid4()),
                name=rule_data['name'],
                description=rule_data['description'],
                rule_type=rule_data['rule_type'],
                scope=rule_data['scope'],
                priority=rule_data['priority'],
                status=RuleStatus.ACTIVE,
                conditions=conditions,
                actions=actions,
                tags=rule_data.get('tags', []),
                created_at=datetime.now(),
                created_by=getattr(self.memory_storage, 'agent_id', 'system'),
                updated_at=datetime.now(),
                updated_by=getattr(self.memory_storage, 'agent_id', 'system')
            )
            
            # Validate rule
            validation_results = self.validator.validate_rule(rule)
            errors = [r for r in validation_results if r.level == ValidationLevel.ERROR]
            
            if errors:
                error_messages = [r.message for r in errors]
                return [TextContent(
                    type="text",
                    text=f"❌ Rule validation failed:\n" + "\n".join(f"• {msg}" for msg in error_messages)
                )]
            
            # Create rule
            rule_id = self.rules_engine.db.create_rule(rule)
            
            # Add to performance indexes
            self.haivemind_integration.performance_manager.add_rule_to_index(rule)
            
            # Store as hAIveMind memory
            self.memory_storage.store_memory(
                content=f"Created governance rule: {rule.name}",
                category="rules",
                metadata={
                    'rule_id': rule_id,
                    'rule_type': rule.rule_type.value,
                    'scope': rule.scope.value,
                    'action': 'create_rule'
                }
            )
            
            return [TextContent(
                type="text", 
                text=f"✅ Successfully created rule '{rule.name}' (ID: {rule_id})\n" +
                     f"Type: {rule.rule_type.value}, Scope: {rule.scope.value}, Priority: {rule.priority.name}"
            )]
            
        except Exception as e:
            logger.error(f"Failed to create rule: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Failed to create rule: {str(e)}"
            )]
    
    async def handle_evaluate_rules(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle evaluate_rules tool call"""
        try:
            context = arguments['context']
            include_inheritance = arguments.get('include_inheritance', True)
            
            # Add system context
            context.update({
                'agent_id': getattr(self.memory_storage, 'agent_id', 'unknown'),
                'machine_id': getattr(self.memory_storage, 'machine_id', 'unknown')
            })
            
            if include_inheritance:
                # Use inheritance-aware evaluation
                inheritance_context = InheritanceContext(
                    agent_id=context['agent_id'],
                    machine_id=context['machine_id'],
                    project_id=context.get('project_id'),
                    session_id=context.get('session_id'),
                    capabilities=context.get('capabilities', []),
                    role=context.get('role')
                )
                
                effective_rules = self.inheritance_manager.get_effective_rules(inheritance_context)
                context['effective_rules'] = [r.id for r in effective_rules]
            
            # Evaluate with hAIveMind awareness
            result = self.haivemind_integration.evaluate_with_awareness(context)
            
            # Format response
            config = result['configuration']
            applied_rules = result['applied_rules']
            eval_time = result['evaluation_time_ms']
            
            response = f"🧠 hAIveMind Rules Evaluation Complete\n\n"
            response += f"⏱️  Evaluation Time: {eval_time:.1f}ms\n"
            response += f"📋 Applied Rules: {len(applied_rules)}\n"
            
            if applied_rules:
                response += f"\n🎯 Active Rules:\n"
                for rule_id in applied_rules[:5]:  # Show first 5
                    response += f"  • {rule_id}\n"
                if len(applied_rules) > 5:
                    response += f"  ... and {len(applied_rules) - 5} more\n"
            
            # Show key configuration settings
            if config:
                response += f"\n⚙️  Key Settings:\n"
                for key, value in list(config.items())[:5]:
                    if not key.startswith('_'):
                        response += f"  • {key}: {value}\n"
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            logger.error(f"Failed to evaluate rules: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Rules evaluation failed: {str(e)}"
            )]
    
    async def handle_validate_rule(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle validate_rule tool call"""
        try:
            rule_definition = arguments['rule_definition']
            auto_fix = arguments.get('auto_fix', False)
            
            # Convert dict to Rule object
            rule = self._dict_to_rule(rule_definition)
            
            # Validate
            validation_results = self.validator.validate_rule(rule)
            
            # Apply auto-fixes if requested
            applied_fixes = []
            if auto_fix:
                fixed_rule, fixes = self.validator.auto_fix_rule(rule, validation_results)
                applied_fixes = fixes
                # Re-validate after fixes
                validation_results = self.validator.validate_rule(fixed_rule)
            
            # Format response
            errors = [r for r in validation_results if r.level == ValidationLevel.ERROR]
            warnings = [r for r in validation_results if r.level == ValidationLevel.WARNING]
            
            response = f"🔍 Rule Validation Results\n\n"
            
            if not errors:
                response += "✅ Rule is valid!\n"
            else:
                response += f"❌ {len(errors)} error(s) found:\n"
                for error in errors:
                    response += f"  • {error.message}\n"
            
            if warnings:
                response += f"\n⚠️  {len(warnings)} warning(s):\n"
                for warning in warnings[:3]:  # Show first 3
                    response += f"  • {warning.message}\n"
            
            if applied_fixes:
                response += f"\n🔧 Auto-fixes applied:\n"
                for fix in applied_fixes:
                    response += f"  • {fix}\n"
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            logger.error(f"Rule validation failed: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Rule validation failed: {str(e)}"
            )]
    
    async def handle_get_rule_suggestions(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get_rule_suggestions tool call"""
        try:
            rule_id = arguments['rule_id']
            
            suggestions = self.haivemind_integration.suggest_rule_improvements(rule_id)
            
            if not suggestions:
                return [TextContent(
                    type="text",
                    text=f"✅ No improvement suggestions found for rule {rule_id}"
                )]
            
            response = f"💡 Improvement Suggestions for Rule {rule_id}\n\n"
            
            for suggestion in suggestions:
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    suggestion['priority'], "🔵"
                )
                response += f"{priority_emoji} **{suggestion['type'].title()}**\n"
                response += f"   {suggestion['message']}\n"
                
                if suggestion.get('recommendations'):
                    response += f"   📋 Recommendations:\n"
                    for rec in suggestion['recommendations'][:3]:
                        response += f"     • {rec}\n"
                response += "\n"
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            logger.error(f"Failed to get rule suggestions: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Failed to get suggestions: {str(e)}"
            )]
    
    async def handle_get_network_insights(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get_network_insights tool call"""
        try:
            insights = self.haivemind_integration.get_network_rule_insights()
            
            response = f"🌐 hAIveMind Network Rule Insights\n\n"
            response += f"📊 Local Statistics:\n"
            response += f"  • Rules: {insights['local_rules']}\n"
            response += f"  • Evaluations: {insights['local_evaluations']}\n" 
            response += f"  • Learning Patterns: {insights['learning_patterns']}\n"
            
            if insights.get('shared_learnings', 0) > 0:
                response += f"  • Shared Learnings: {insights['shared_learnings']}\n"
            
            if insights.get('network_insights'):
                response += f"\n🔗 Network Activity:\n"
                for insight in insights['network_insights'][:3]:
                    response += f"  • {insight}\n"
            else:
                response += f"\n🔗 Network: Operating in local mode\n"
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            logger.error(f"Failed to get network insights: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Failed to get network insights: {str(e)}"
            )]
    
    def _dict_to_rule(self, rule_dict: Dict[str, Any]) -> Rule:
        """Convert dictionary to Rule object"""
        # Convert conditions
        conditions = []
        for cond in rule_dict.get('conditions', []):
            conditions.append(RuleCondition(**cond))
        
        # Convert actions
        actions = []
        for action in rule_dict.get('actions', []):
            actions.append(RuleAction(**action))
        
        return Rule(
            id=rule_dict.get('id', str(uuid.uuid4())),
            name=rule_dict['name'],
            description=rule_dict['description'],
            rule_type=RuleType(rule_dict['rule_type']),
            scope=RuleScope(rule_dict['scope']),
            priority=RulePriority[rule_dict['priority']] if isinstance(rule_dict['priority'], str) else rule_dict['priority'],
            status=RuleStatus(rule_dict.get('status', 'active')),
            conditions=conditions,
            actions=actions,
            tags=rule_dict.get('tags', []),
            created_at=datetime.now(),
            created_by=rule_dict.get('created_by', 'system'),
            updated_at=datetime.now(),
            updated_by=rule_dict.get('updated_by', 'system'),
            metadata=rule_dict.get('metadata', {})
        )