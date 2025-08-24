#!/usr/bin/env python3
"""
hAIveMind Rules Database Management MCP Tools
Comprehensive MCP interface for rules management, versioning, and hAIveMind integration

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
from .rules_database import RulesDatabase
from .rule_management_service import RuleManagementService, RuleValidationError
from .rules_haivemind_integration import RulesHAIveMindIntegration

logger = logging.getLogger(__name__)

class RulesMCPToolsEnhanced:
    """Comprehensive MCP Tools for hAIveMind Rules Database Management"""
    
    def __init__(self, memory_storage, config: Dict[str, Any]):
        self.memory_storage = memory_storage
        self.config = config
        
        # Initialize enhanced rules components
        db_path = config.get('rules_db_path', 'data/rules.db')
        self.rules_db = RulesDatabase(
            db_path=db_path,
            chroma_client=getattr(memory_storage, 'chroma_client', None),
            redis_client=getattr(memory_storage, 'redis_client', None)
        )
        
        self.rule_service = RuleManagementService(
            db_path=db_path,
            chroma_client=getattr(memory_storage, 'chroma_client', None),
            redis_client=getattr(memory_storage, 'redis_client', None)
        )
        
        self.haivemind_integration = RulesHAIveMindIntegration(
            self.rule_service,
            memory_storage,
            getattr(memory_storage, 'redis_client', None)
        )
    
    def get_tools(self) -> List[Tool]:
        """Get all comprehensive rules management MCP tools"""
        return [
            # Core rule management
            Tool(
                name="create_rule",
                description="Create a new governance rule with comprehensive management features",
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
                            "description": "Rule scope",
                            "default": "global"
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Rule priority (100-1000)",
                            "default": 500
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
                            "description": "Rule conditions",
                            "default": []
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
                            "description": "Rule actions",
                            "default": []
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Rule tags for categorization",
                            "default": []
                        },
                        "effective_from": {
                            "type": "string",
                            "description": "ISO datetime when rule becomes effective"
                        },
                        "effective_until": {
                            "type": "string",
                            "description": "ISO datetime when rule expires"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Additional rule metadata",
                            "default": {}
                        }
                    },
                    "required": ["name", "description", "rule_type"]
                }
            ),
            
            Tool(
                name="create_rule_from_yaml",
                description="Create a rule from YAML format",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "yaml_content": {"type": "string", "description": "YAML rule definition"},
                        "created_by": {"type": "string", "description": "Creator identifier", "default": "system"}
                    },
                    "required": ["yaml_content"]
                }
            ),
            
            Tool(
                name="create_rule_from_json",
                description="Create a rule from JSON format",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "json_content": {"type": "string", "description": "JSON rule definition"},
                        "created_by": {"type": "string", "description": "Creator identifier", "default": "system"}
                    },
                    "required": ["json_content"]
                }
            ),
            
            Tool(
                name="update_rule",
                description="Update an existing rule with version tracking",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "string", "description": "Rule ID to update"},
                        "updates": {"type": "object", "description": "Fields to update"},
                        "updated_by": {"type": "string", "description": "Updater identifier", "default": "system"},
                        "change_reason": {"type": "string", "description": "Reason for the change"}
                    },
                    "required": ["rule_id", "updates"]
                }
            ),
            
            Tool(
                name="get_rule",
                description="Get a rule by ID with optional format",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "string", "description": "Rule ID"},
                        "format": {
                            "type": "string",
                            "enum": ["dict", "yaml", "json"],
                            "description": "Output format",
                            "default": "dict"
                        }
                    },
                    "required": ["rule_id"]
                }
            ),
            
            Tool(
                name="activate_rule",
                description="Activate a rule with optional effective date",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "string", "description": "Rule ID"},
                        "activated_by": {"type": "string", "description": "Activator identifier", "default": "system"},
                        "effective_from": {"type": "string", "description": "ISO datetime when rule becomes effective"}
                    },
                    "required": ["rule_id"]
                }
            ),
            
            Tool(
                name="deactivate_rule",
                description="Deactivate a rule with optional effective date",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "string", "description": "Rule ID"},
                        "deactivated_by": {"type": "string", "description": "Deactivator identifier", "default": "system"},
                        "effective_until": {"type": "string", "description": "ISO datetime when rule expires"}
                    },
                    "required": ["rule_id"]
                }
            ),
            
            Tool(
                name="get_rule_version_history",
                description="Get version history for a rule",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "string", "description": "Rule ID"}
                    },
                    "required": ["rule_id"]
                }
            ),
            
            Tool(
                name="create_rule_dependency",
                description="Create a dependency relationship between rules",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "string", "description": "Rule ID"},
                        "depends_on_rule_id": {"type": "string", "description": "Rule ID this rule depends on"},
                        "dependency_type": {
                            "type": "string",
                            "enum": ["requires", "conflicts", "enhances", "replaces"],
                            "description": "Type of dependency",
                            "default": "requires"
                        },
                        "metadata": {"type": "object", "description": "Additional dependency metadata"}
                    },
                    "required": ["rule_id", "depends_on_rule_id"]
                }
            ),
            
            Tool(
                name="assign_rule_to_scope",
                description="Assign a rule to a specific scope (project, agent, etc.)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "string", "description": "Rule ID"},
                        "scope_type": {
                            "type": "string",
                            "enum": ["global", "project", "machine", "agent", "user"],
                            "description": "Type of scope"
                        },
                        "scope_id": {"type": "string", "description": "Specific ID for the scope"},
                        "priority_override": {"type": "integer", "description": "Override priority for this assignment"},
                        "effective_from": {"type": "string", "description": "ISO datetime when assignment becomes effective"},
                        "effective_until": {"type": "string", "description": "ISO datetime when assignment expires"}
                    },
                    "required": ["rule_id", "scope_type", "scope_id"]
                }
            ),
            
            Tool(
                name="export_rules",
                description="Export rules in YAML or JSON format",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "format": {
                            "type": "string",
                            "enum": ["yaml", "json"],
                            "description": "Export format",
                            "default": "yaml"
                        },
                        "rule_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific rule IDs to export (all if not specified)"
                        },
                        "include_history": {
                            "type": "boolean",
                            "description": "Include version history",
                            "default": False
                        }
                    }
                }
            ),
            
            Tool(
                name="import_rules",
                description="Import rules from YAML or JSON format",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "import_data": {"type": "string", "description": "YAML or JSON rule data"},
                        "format": {
                            "type": "string",
                            "enum": ["yaml", "json"],
                            "description": "Import format",
                            "default": "yaml"
                        },
                        "imported_by": {"type": "string", "description": "Importer identifier", "default": "system"},
                        "overwrite": {
                            "type": "boolean",
                            "description": "Overwrite existing rules",
                            "default": False
                        }
                    },
                    "required": ["import_data"]
                }
            ),
            
            Tool(
                name="create_rule_from_template",
                description="Create a rule from a template with parameter substitution",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "template_id": {"type": "string", "description": "Template ID"},
                        "parameters": {"type": "object", "description": "Template parameters"},
                        "created_by": {"type": "string", "description": "Creator identifier", "default": "system"}
                    },
                    "required": ["template_id", "parameters"]
                }
            ),
            
            Tool(
                name="list_rule_templates",
                description="List available rule templates",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Filter by category"}
                    }
                }
            ),
            
            Tool(
                name="clone_rule",
                description="Clone an existing rule with optional modifications",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "string", "description": "Rule ID to clone"},
                        "new_name": {"type": "string", "description": "Name for the cloned rule"},
                        "cloned_by": {"type": "string", "description": "Cloner identifier", "default": "system"},
                        "modifications": {"type": "object", "description": "Modifications to apply to the clone"}
                    },
                    "required": ["rule_id", "new_name"]
                }
            ),
            
            Tool(
                name="search_rules",
                description="Search rules using text query and filters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "filters": {"type": "object", "description": "Search filters"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 20}
                    },
                    "required": ["query"]
                }
            ),
            
            Tool(
                name="get_rule_statistics",
                description="Get comprehensive rule statistics",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            
            # hAIveMind integration tools
            Tool(
                name="analyze_rule_effectiveness",
                description="Analyze rule effectiveness based on historical data",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "string", "description": "Rule ID"},
                        "days": {"type": "integer", "description": "Analysis period in days", "default": 30}
                    },
                    "required": ["rule_id"]
                }
            ),
            
            Tool(
                name="discover_rule_patterns",
                description="Discover patterns in rule usage across the network",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string", "description": "Filter by specific agent"},
                        "days": {"type": "integer", "description": "Analysis period in days", "default": 14}
                    }
                }
            ),
            
            Tool(
                name="recommend_rule_improvements",
                description="Get AI-powered recommendations for rule improvements",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "string", "description": "Rule ID"}
                    },
                    "required": ["rule_id"]
                }
            ),
            
            Tool(
                name="sync_rules_network",
                description="Synchronize rules across the hAIveMind network",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific rule IDs to sync (all if not specified)"
                        }
                    }
                }
            ),
            
            Tool(
                name="get_network_rule_insights",
                description="Get insights about rule usage across the network",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer", "description": "Analysis period in days", "default": 7}
                    }
                }
            ),
            
            Tool(
                name="learn_from_rule_patterns",
                description="Learn from historical patterns to improve rule",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "string", "description": "Rule ID"}
                    },
                    "required": ["rule_id"]
                }
            ),
            
            Tool(
                name="get_rule_inheritance_tree",
                description="Get the inheritance tree for a rule",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "string", "description": "Rule ID"}
                    },
                    "required": ["rule_id"]
                }
            ),
            
            Tool(
                name="backup_rules_database",
                description="Create a backup of the rules database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "backup_path": {"type": "string", "description": "Backup file path"}
                    },
                    "required": ["backup_path"]
                }
            )
        ]
    
    def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle MCP tool calls for rules management"""
        try:
            if name == "create_rule":
                return self._create_rule(arguments)
            elif name == "create_rule_from_yaml":
                return self._create_rule_from_yaml(arguments)
            elif name == "create_rule_from_json":
                return self._create_rule_from_json(arguments)
            elif name == "update_rule":
                return self._update_rule(arguments)
            elif name == "get_rule":
                return self._get_rule(arguments)
            elif name == "activate_rule":
                return self._activate_rule(arguments)
            elif name == "deactivate_rule":
                return self._deactivate_rule(arguments)
            elif name == "get_rule_version_history":
                return self._get_rule_version_history(arguments)
            elif name == "create_rule_dependency":
                return self._create_rule_dependency(arguments)
            elif name == "assign_rule_to_scope":
                return self._assign_rule_to_scope(arguments)
            elif name == "export_rules":
                return self._export_rules(arguments)
            elif name == "import_rules":
                return self._import_rules(arguments)
            elif name == "create_rule_from_template":
                return self._create_rule_from_template(arguments)
            elif name == "list_rule_templates":
                return self._list_rule_templates(arguments)
            elif name == "clone_rule":
                return self._clone_rule(arguments)
            elif name == "search_rules":
                return self._search_rules(arguments)
            elif name == "get_rule_statistics":
                return self._get_rule_statistics(arguments)
            elif name == "analyze_rule_effectiveness":
                return self._analyze_rule_effectiveness(arguments)
            elif name == "discover_rule_patterns":
                return self._discover_rule_patterns(arguments)
            elif name == "recommend_rule_improvements":
                return self._recommend_rule_improvements(arguments)
            elif name == "sync_rules_network":
                return self._sync_rules_network(arguments)
            elif name == "get_network_rule_insights":
                return self._get_network_rule_insights(arguments)
            elif name == "learn_from_rule_patterns":
                return self._learn_from_rule_patterns(arguments)
            elif name == "get_rule_inheritance_tree":
                return self._get_rule_inheritance_tree(arguments)
            elif name == "backup_rules_database":
                return self._backup_rules_database(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
                
        except Exception as e:
            logger.error(f"Error handling tool {name}: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    def _create_rule(self, args: Dict[str, Any]) -> List[TextContent]:
        """Create a new rule"""
        try:
            rule_id = self.rule_service.create_rule_from_dict(args, args.get('created_by', 'system'))
            
            # Store hAIveMind memory
            self.haivemind_integration.store_rule_operation_memory(
                rule_id, "created", args, {"success": True, "rule_id": rule_id}, 
                args.get('created_by', 'system')
            )
            
            return [TextContent(type="text", text=f"Rule created successfully with ID: {rule_id}")]
            
        except RuleValidationError as e:
            return [TextContent(type="text", text=f"Validation error: {e}")]
    
    def _create_rule_from_yaml(self, args: Dict[str, Any]) -> List[TextContent]:
        """Create rule from YAML"""
        try:
            rule_id = self.rule_service.create_rule_from_yaml(
                args['yaml_content'], args.get('created_by', 'system')
            )
            
            self.haivemind_integration.store_rule_operation_memory(
                rule_id, "created", {"format": "yaml"}, {"success": True, "rule_id": rule_id},
                args.get('created_by', 'system')
            )
            
            return [TextContent(type="text", text=f"Rule created from YAML with ID: {rule_id}")]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating rule from YAML: {e}")]
    
    def _create_rule_from_json(self, args: Dict[str, Any]) -> List[TextContent]:
        """Create rule from JSON"""
        try:
            rule_id = self.rule_service.create_rule_from_json(
                args['json_content'], args.get('created_by', 'system')
            )
            
            self.haivemind_integration.store_rule_operation_memory(
                rule_id, "created", {"format": "json"}, {"success": True, "rule_id": rule_id},
                args.get('created_by', 'system')
            )
            
            return [TextContent(type="text", text=f"Rule created from JSON with ID: {rule_id}")]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating rule from JSON: {e}")]
    
    def _update_rule(self, args: Dict[str, Any]) -> List[TextContent]:
        """Update an existing rule"""
        try:
            success = self.rule_service.update_rule_from_dict(
                args['rule_id'], args['updates'], args.get('updated_by', 'system')
            )
            
            if success:
                self.haivemind_integration.store_rule_operation_memory(
                    args['rule_id'], "updated", args['updates'], 
                    {"success": True}, args.get('updated_by', 'system')
                )
                return [TextContent(type="text", text=f"Rule {args['rule_id']} updated successfully")]
            else:
                return [TextContent(type="text", text=f"Failed to update rule {args['rule_id']}")]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Error updating rule: {e}")]
    
    def _get_rule(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get a rule by ID"""
        try:
            format_type = args.get('format', 'dict')
            
            if format_type == 'yaml':
                result = self.rule_service.get_rule_as_yaml(args['rule_id'])
            elif format_type == 'json':
                result = self.rule_service.get_rule_as_json(args['rule_id'])
            else:
                rule = self.rules_db.get_rule(args['rule_id'])
                result = self.rule_service._rule_to_export_dict(rule) if rule else None
            
            if result:
                return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
            else:
                return [TextContent(type="text", text=f"Rule {args['rule_id']} not found")]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting rule: {e}")]
    
    def _activate_rule(self, args: Dict[str, Any]) -> List[TextContent]:
        """Activate a rule"""
        try:
            effective_from = None
            if args.get('effective_from'):
                effective_from = datetime.fromisoformat(args['effective_from'])
            
            success = self.rules_db.activate_rule(
                args['rule_id'], args.get('activated_by', 'system'), effective_from
            )
            
            if success:
                self.haivemind_integration.store_rule_operation_memory(
                    args['rule_id'], "activated", {"effective_from": args.get('effective_from')},
                    {"success": True}, args.get('activated_by', 'system')
                )
                return [TextContent(type="text", text=f"Rule {args['rule_id']} activated successfully")]
            else:
                return [TextContent(type="text", text=f"Failed to activate rule {args['rule_id']}")]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Error activating rule: {e}")]
    
    def _deactivate_rule(self, args: Dict[str, Any]) -> List[TextContent]:
        """Deactivate a rule"""
        try:
            effective_until = None
            if args.get('effective_until'):
                effective_until = datetime.fromisoformat(args['effective_until'])
            
            success = self.rules_db.deactivate_rule(
                args['rule_id'], args.get('deactivated_by', 'system'), effective_until
            )
            
            if success:
                self.haivemind_integration.store_rule_operation_memory(
                    args['rule_id'], "deactivated", {"effective_until": args.get('effective_until')},
                    {"success": True}, args.get('deactivated_by', 'system')
                )
                return [TextContent(type="text", text=f"Rule {args['rule_id']} deactivated successfully")]
            else:
                return [TextContent(type="text", text=f"Failed to deactivate rule {args['rule_id']}")]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Error deactivating rule: {e}")]
    
    def _get_rule_version_history(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get rule version history"""
        try:
            history = self.rules_db.get_rule_version_history(args['rule_id'])
            history_data = [
                {
                    "version": v.version,
                    "change_type": v.change_type.value,
                    "changed_by": v.changed_by,
                    "changed_at": v.changed_at.isoformat(),
                    "change_reason": v.change_reason
                }
                for v in history
            ]
            
            return [TextContent(type="text", text=json.dumps({
                "rule_id": args['rule_id'],
                "version_history": history_data
            }, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting version history: {e}")]
    
    def _create_rule_dependency(self, args: Dict[str, Any]) -> List[TextContent]:
        """Create rule dependency"""
        try:
            dependency_id = self.rules_db.create_rule_dependency(
                args['rule_id'], 
                args['depends_on_rule_id'],
                args.get('dependency_type', 'requires'),
                args.get('metadata')
            )
            
            return [TextContent(type="text", text=f"Dependency created with ID: {dependency_id}")]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating dependency: {e}")]
    
    def _assign_rule_to_scope(self, args: Dict[str, Any]) -> List[TextContent]:
        """Assign rule to scope"""
        try:
            effective_from = None
            effective_until = None
            
            if args.get('effective_from'):
                effective_from = datetime.fromisoformat(args['effective_from'])
            if args.get('effective_until'):
                effective_until = datetime.fromisoformat(args['effective_until'])
            
            assignment_id = self.rules_db.assign_rule_to_scope(
                args['rule_id'],
                args['scope_type'],
                args['scope_id'],
                args.get('priority_override'),
                effective_from,
                effective_until
            )
            
            return [TextContent(type="text", text=f"Rule assigned to scope with ID: {assignment_id}")]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error assigning rule to scope: {e}")]
    
    def _export_rules(self, args: Dict[str, Any]) -> List[TextContent]:
        """Export rules"""
        try:
            export_data = self.rules_db.export_rules(
                args.get('format', 'yaml'),
                args.get('rule_ids'),
                args.get('include_history', False)
            )
            
            return [TextContent(type="text", text=export_data)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error exporting rules: {e}")]
    
    def _import_rules(self, args: Dict[str, Any]) -> List[TextContent]:
        """Import rules"""
        try:
            imported_rule_ids = self.rules_db.import_rules(
                args['import_data'],
                args.get('format', 'yaml'),
                args.get('imported_by', 'system'),
                args.get('overwrite', False)
            )
            
            return [TextContent(type="text", text=json.dumps({
                "imported_count": len(imported_rule_ids),
                "imported_rule_ids": imported_rule_ids
            }, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error importing rules: {e}")]
    
    def _create_rule_from_template(self, args: Dict[str, Any]) -> List[TextContent]:
        """Create rule from template"""
        try:
            rule_id = self.rules_db.create_rule_from_template(
                args['template_id'],
                args['parameters'],
                args.get('created_by', 'system')
            )
            
            if rule_id:
                return [TextContent(type="text", text=f"Rule created from template with ID: {rule_id}")]
            else:
                return [TextContent(type="text", text=f"Template {args['template_id']} not found")]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating rule from template: {e}")]
    
    def _list_rule_templates(self, args: Dict[str, Any]) -> List[TextContent]:
        """List rule templates"""
        try:
            templates = self.rules_db.list_rule_templates(args.get('category'))
            template_list = [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "category": t.category,
                    "rule_type": t.rule_type.value,
                    "tags": t.tags
                }
                for t in templates
            ]
            
            return [TextContent(type="text", text=json.dumps(template_list, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error listing templates: {e}")]
    
    def _clone_rule(self, args: Dict[str, Any]) -> List[TextContent]:
        """Clone a rule"""
        try:
            rule_id = self.rule_service.clone_rule(
                args['rule_id'],
                args['new_name'],
                args.get('cloned_by', 'system'),
                args.get('modifications')
            )
            
            return [TextContent(type="text", text=f"Rule cloned with ID: {rule_id}")]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error cloning rule: {e}")]
    
    def _search_rules(self, args: Dict[str, Any]) -> List[TextContent]:
        """Search rules"""
        try:
            results = self.rule_service.search_rules(
                args['query'],
                args.get('filters'),
            )
            
            # Limit results
            limit = args.get('limit', 20)
            limited_results = results[:limit]
            
            return [TextContent(type="text", text=json.dumps({
                "query": args['query'],
                "total_found": len(results),
                "results_shown": len(limited_results),
                "results": limited_results
            }, indent=2, default=str))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error searching rules: {e}")]
    
    def _get_rule_statistics(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get rule statistics"""
        try:
            stats = self.rules_db.get_rule_statistics()
            return [TextContent(type="text", text=json.dumps(stats, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting statistics: {e}")]
    
    def _analyze_rule_effectiveness(self, args: Dict[str, Any]) -> List[TextContent]:
        """Analyze rule effectiveness"""
        try:
            effectiveness = self.haivemind_integration.analyze_rule_effectiveness(
                args['rule_id'], args.get('days', 30)
            )
            
            result = {
                "rule_id": effectiveness.rule_id,
                "success_count": effectiveness.success_count,
                "failure_count": effectiveness.failure_count,
                "avg_execution_time": effectiveness.avg_execution_time,
                "effectiveness_score": effectiveness.effectiveness_score,
                "recommendations": effectiveness.recommendations
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error analyzing effectiveness: {e}")]
    
    def _discover_rule_patterns(self, args: Dict[str, Any]) -> List[TextContent]:
        """Discover rule patterns"""
        try:
            patterns = self.haivemind_integration.discover_rule_patterns(
                args.get('agent_id'), args.get('days', 14)
            )
            
            pattern_data = [
                {
                    "insight_id": p.insight_id,
                    "rule_id": p.rule_id,
                    "insight_type": p.insight_type,
                    "description": p.description,
                    "confidence": p.confidence,
                    "suggested_actions": p.suggested_actions
                }
                for p in patterns
            ]
            
            return [TextContent(type="text", text=json.dumps({
                "patterns_found": len(patterns),
                "patterns": pattern_data
            }, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error discovering patterns: {e}")]
    
    def _recommend_rule_improvements(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get rule improvement recommendations"""
        try:
            recommendations = self.haivemind_integration.recommend_rule_improvements(args['rule_id'])
            
            return [TextContent(type="text", text=json.dumps({
                "rule_id": args['rule_id'],
                "recommendations": recommendations
            }, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting recommendations: {e}")]
    
    def _sync_rules_network(self, args: Dict[str, Any]) -> List[TextContent]:
        """Sync rules across network"""
        try:
            result = self.haivemind_integration.sync_rules_across_network(args.get('rule_ids'))
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error syncing rules: {e}")]
    
    def _get_network_rule_insights(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get network rule insights"""
        try:
            insights = self.haivemind_integration.get_network_rule_insights(args.get('days', 7))
            return [TextContent(type="text", text=json.dumps(insights, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting network insights: {e}")]
    
    def _learn_from_rule_patterns(self, args: Dict[str, Any]) -> List[TextContent]:
        """Learn from rule patterns"""
        try:
            learning = self.haivemind_integration.learn_from_rule_patterns(args['rule_id'])
            return [TextContent(type="text", text=json.dumps(learning, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error learning from patterns: {e}")]
    
    def _get_rule_inheritance_tree(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get rule inheritance tree"""
        try:
            tree = self.rule_service.get_rule_inheritance_tree(args['rule_id'])
            return [TextContent(type="text", text=json.dumps(tree, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting inheritance tree: {e}")]
    
    def _backup_rules_database(self, args: Dict[str, Any]) -> List[TextContent]:
        """Backup rules database"""
        try:
            success = self.rules_db.backup_database(args['backup_path'])
            
            if success:
                return [TextContent(type="text", text=f"Database backed up to: {args['backup_path']}")]
            else:
                return [TextContent(type="text", text="Failed to backup database")]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Error backing up database: {e}")]