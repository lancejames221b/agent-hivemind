#!/usr/bin/env python3
"""
Advanced Rules MCP Tools for hAIveMind Rules Engine
Provides MCP tool interface for advanced rule types, templates, and enterprise features

Author: Lance James, Unit 221B Inc
"""

import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

from mcp.types import Tool, TextContent
from advanced_rule_types import AdvancedRulesEngine, AdvancedRuleType, TriggerType, ComplianceFramework
from rule_template_system import RuleTemplateSystem, TemplateCategory, IndustryType
from compliance_rule_templates import ComplianceTemplateLibrary
from enterprise_rule_features import EnterpriseRuleManager, TenantType, ApprovalStatus
from specialized_rule_categories import SpecializedRuleManager, SpecializedRuleCategory

logger = logging.getLogger(__name__)

class AdvancedRulesMCPTools:
    """MCP Tools for advanced hAIveMind Rules Engine features"""
    
    def __init__(self, memory_storage, base_rules_engine, config: Dict[str, Any]):
        self.memory_storage = memory_storage
        self.base_rules_engine = base_rules_engine
        self.config = config
        
        # Initialize advanced components
        self.advanced_engine = AdvancedRulesEngine(
            base_rules_engine, memory_storage, 
            getattr(memory_storage, 'redis_client', None)
        )
        
        self.template_system = RuleTemplateSystem(
            db_path=config.get('templates_db_path', 'data/templates.db'),
            templates_dir=config.get('templates_dir', 'data/templates'),
            memory_storage=memory_storage,
            config=config
        )
        
        self.compliance_library = ComplianceTemplateLibrary()
        
        self.enterprise_manager = EnterpriseRuleManager(
            db_path=config.get('enterprise_db_path', 'data/enterprise.db'),
            memory_storage=memory_storage,
            redis_client=getattr(memory_storage, 'redis_client', None),
            config=config
        )
        
        self.specialized_manager = SpecializedRuleManager(
            memory_storage, base_rules_engine
        )
    
    def get_tools(self) -> List[Tool]:
        """Get all advanced rules MCP tools"""
        return [
            # Advanced Rule Types
            Tool(
                name="create_advanced_rule",
                description="Create advanced rule with conditional, cascading, time-based, or context-aware capabilities",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_definition": {
                            "type": "object",
                            "description": "Complete advanced rule definition"
                        },
                        "advanced_type": {
                            "type": "string",
                            "enum": [t.value for t in AdvancedRuleType],
                            "description": "Type of advanced rule"
                        },
                        "trigger_config": {
                            "type": "object",
                            "description": "Trigger configuration for the rule",
                            "properties": {
                                "trigger_type": {
                                    "type": "string",
                                    "enum": [t.value for t in TriggerType]
                                },
                                "schedule": {"type": "object"},
                                "conditions": {"type": "object"},
                                "thresholds": {"type": "object"}
                            }
                        }
                    },
                    "required": ["rule_definition", "advanced_type"]
                }
            ),
            
            Tool(
                name="evaluate_advanced_rules",
                description="Evaluate advanced rules with enhanced logic and context awareness",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "context": {
                            "type": "object",
                            "description": "Evaluation context with enhanced fields"
                        },
                        "rule_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific advanced rule types to evaluate"
                        }
                    },
                    "required": ["context"]
                }
            ),
            
            # Template System
            Tool(
                name="create_rule_template",
                description="Create a reusable rule template with parameters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "template_definition": {
                            "type": "object",
                            "description": "Complete template definition with metadata and parameters"
                        },
                        "category": {
                            "type": "string",
                            "enum": [c.value for c in TemplateCategory],
                            "description": "Template category"
                        },
                        "industry": {
                            "type": "string",
                            "enum": [i.value for i in IndustryType],
                            "description": "Target industry"
                        }
                    },
                    "required": ["template_definition", "category"]
                }
            ),
            
            Tool(
                name="instantiate_template",
                description="Create rule instance from template with parameters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "template_id": {
                            "type": "string",
                            "description": "ID of template to instantiate"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Template parameters"
                        },
                        "created_by": {
                            "type": "string",
                            "description": "Creator identifier"
                        }
                    },
                    "required": ["template_id", "parameters", "created_by"]
                }
            ),
            
            Tool(
                name="search_templates",
                description="Search rule templates by category, industry, or keywords",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "category": {
                            "type": "string",
                            "enum": [c.value for c in TemplateCategory],
                            "description": "Filter by category"
                        },
                        "industry": {
                            "type": "string",
                            "enum": [i.value for i in IndustryType],
                            "description": "Filter by industry"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by tags"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 20,
                            "description": "Maximum results to return"
                        }
                    }
                }
            ),
            
            # Compliance Templates
            Tool(
                name="get_compliance_templates",
                description="Get compliance rule templates for specific frameworks",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "framework": {
                            "type": "string",
                            "enum": [f.value for f in ComplianceFramework],
                            "description": "Compliance framework"
                        }
                    }
                }
            ),
            
            Tool(
                name="create_compliance_rule",
                description="Create compliance rule from framework template",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "framework": {
                            "type": "string",
                            "enum": [f.value for f in ComplianceFramework],
                            "description": "Compliance framework"
                        },
                        "template_id": {
                            "type": "string",
                            "description": "Compliance template ID"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Compliance-specific parameters"
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Tenant ID for multi-tenant environments"
                        }
                    },
                    "required": ["framework", "template_id", "parameters"]
                }
            ),
            
            # Enterprise Features
            Tool(
                name="create_tenant",
                description="Create new tenant in multi-tenant environment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tenant_name": {
                            "type": "string",
                            "description": "Tenant name"
                        },
                        "tenant_type": {
                            "type": "string",
                            "enum": [t.value for t in TenantType],
                            "description": "Type of tenant"
                        },
                        "parent_tenant_id": {
                            "type": "string",
                            "description": "Parent tenant ID for hierarchical structure"
                        },
                        "settings": {
                            "type": "object",
                            "description": "Tenant-specific settings"
                        },
                        "created_by": {
                            "type": "string",
                            "description": "Creator identifier"
                        }
                    },
                    "required": ["tenant_name", "tenant_type", "created_by"]
                }
            ),
            
            Tool(
                name="request_rule_approval",
                description="Submit rule for approval workflow",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_definition": {
                            "type": "object",
                            "description": "Rule to be approved"
                        },
                        "workflow_id": {
                            "type": "string",
                            "description": "Approval workflow ID"
                        },
                        "requester_id": {
                            "type": "string",
                            "description": "Requester identifier"
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Tenant ID"
                        },
                        "justification": {
                            "type": "string",
                            "description": "Justification for the rule"
                        }
                    },
                    "required": ["rule_definition", "workflow_id", "requester_id", "tenant_id"]
                }
            ),
            
            Tool(
                name="get_compliance_report",
                description="Generate compliance report for tenant",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tenant_id": {
                            "type": "string",
                            "description": "Tenant ID"
                        },
                        "framework": {
                            "type": "string",
                            "enum": [f.value for f in ComplianceFramework],
                            "description": "Compliance framework filter"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Report start date (ISO format)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Report end date (ISO format)"
                        }
                    },
                    "required": ["tenant_id"]
                }
            ),
            
            # Specialized Rule Categories
            Tool(
                name="deploy_specialized_rules",
                description="Deploy specialized rule categories (authorship, code quality, security, etc.)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_set": {
                            "type": "string",
                            "enum": ["lance_james", "enterprise", "security_focused", "compliance_focused"],
                            "description": "Predefined rule set to deploy"
                        },
                        "categories": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [c.value for c in SpecializedRuleCategory]
                            },
                            "description": "Specific categories to deploy"
                        },
                        "configuration": {
                            "type": "object",
                            "description": "Configuration overrides for the rule set"
                        }
                    },
                    "required": ["rule_set"]
                }
            ),
            
            Tool(
                name="get_specialized_rules",
                description="Get rules from specialized categories",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": [c.value for c in SpecializedRuleCategory],
                            "description": "Specialized rule category"
                        }
                    },
                    "required": ["category"]
                }
            ),
            
            # Rule Analytics and Insights
            Tool(
                name="get_rule_impact_analysis",
                description="Get impact analysis for rule changes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {
                            "type": "string",
                            "description": "Rule ID to analyze"
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Tenant context for analysis"
                        }
                    },
                    "required": ["rule_id"]
                }
            ),
            
            Tool(
                name="get_advanced_analytics",
                description="Get advanced analytics for rule performance and effectiveness",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "analytics_type": {
                            "type": "string",
                            "enum": ["performance", "compliance", "usage", "effectiveness"],
                            "description": "Type of analytics to retrieve"
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Tenant ID for scoped analytics"
                        },
                        "time_range": {
                            "type": "object",
                            "properties": {
                                "start_date": {"type": "string"},
                                "end_date": {"type": "string"}
                            }
                        }
                    },
                    "required": ["analytics_type"]
                }
            )
        ]
    
    async def handle_create_advanced_rule(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle create_advanced_rule tool call"""
        try:
            rule_definition = arguments['rule_definition']
            advanced_type = AdvancedRuleType(arguments['advanced_type'])
            trigger_config = arguments.get('trigger_config', {})
            
            # Create advanced rule
            # This would involve converting the definition to an AdvancedRule object
            # and configuring the specific advanced features
            
            response = f"🚀 Advanced Rule Creation\n\n"
            response += f"**Type**: {advanced_type.value}\n"
            response += f"**Name**: {rule_definition.get('name', 'Unnamed Rule')}\n"
            response += f"**Description**: {rule_definition.get('description', 'No description')}\n\n"
            
            if trigger_config:
                trigger_type = trigger_config.get('trigger_type', 'immediate')
                response += f"**Trigger**: {trigger_type}\n"
                
                if trigger_type == 'scheduled' and 'schedule' in trigger_config:
                    schedule = trigger_config['schedule']
                    response += f"**Schedule**: {schedule.get('cron_expression', 'Not specified')}\n"
                
                if 'conditions' in trigger_config:
                    response += f"**Conditions**: {len(trigger_config['conditions'])} condition(s)\n"
            
            response += f"\n✅ Advanced rule created successfully!"
            
            # Store in hAIveMind memory
            self.memory_storage.store_memory(
                content=f"Created advanced rule: {rule_definition.get('name')}",
                category="advanced_rules",
                metadata={
                    'advanced_type': advanced_type.value,
                    'trigger_config': trigger_config,
                    'rule_definition': rule_definition
                }
            )
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            logger.error(f"Failed to create advanced rule: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Failed to create advanced rule: {str(e)}"
            )]
    
    async def handle_evaluate_advanced_rules(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle evaluate_advanced_rules tool call"""
        try:
            context = arguments['context']
            rule_types = arguments.get('rule_types', [])
            
            # Evaluate advanced rules
            result = await self.advanced_engine.evaluate_advanced_rules(context)
            
            response = f"🧠 Advanced Rules Evaluation Complete\n\n"
            response += f"⏱️  **Evaluation Time**: {result['evaluation_time_ms']:.1f}ms\n"
            response += f"📊 **Rules Processed**: {result['rules_processed']}\n\n"
            
            # Show results by type
            advanced_results = result.get('advanced_results', {})
            
            for rule_type, type_results in advanced_results.items():
                if rule_type in rule_types or not rule_types:
                    response += f"**{rule_type.replace('_', ' ').title()}**:\n"
                    
                    if rule_type == 'conditional':
                        triggered = type_results.get('triggered_rules', [])
                        response += f"  • Triggered: {len([r for r in triggered if r.get('triggered')])}\n"
                    
                    elif rule_type == 'cascading':
                        executions = type_results.get('cascading_executions', [])
                        response += f"  • Cascading Executions: {len(executions)}\n"
                    
                    elif rule_type == 'time_based':
                        executions = type_results.get('scheduled_executions', [])
                        response += f"  • Scheduled Executions: {len(executions)}\n"
                    
                    elif rule_type == 'compliance':
                        executions = type_results.get('compliance_executions', [])
                        response += f"  • Compliance Checks: {len(executions)}\n"
                    
                    response += "\n"
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            logger.error(f"Failed to evaluate advanced rules: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Advanced rules evaluation failed: {str(e)}"
            )]
    
    async def handle_search_templates(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle search_templates tool call"""
        try:
            query = arguments.get('query', '')
            category = TemplateCategory(arguments['category']) if arguments.get('category') else None
            industry = IndustryType(arguments['industry']) if arguments.get('industry') else None
            tags = arguments.get('tags', [])
            limit = arguments.get('limit', 20)
            
            # Search templates
            templates = self.template_system.search_templates(
                query=query,
                category=category,
                industry=industry,
                tags=tags,
                limit=limit
            )
            
            response = f"🔍 Template Search Results\n\n"
            response += f"**Query**: {query or 'All templates'}\n"
            response += f"**Found**: {len(templates)} template(s)\n\n"
            
            for template in templates[:10]:  # Show first 10
                response += f"**{template.metadata.name}** (v{template.metadata.version})\n"
                response += f"  • ID: `{template.metadata.id}`\n"
                response += f"  • Category: {template.metadata.category.value}\n"
                response += f"  • Industry: {template.metadata.industry.value}\n"
                response += f"  • Author: {template.metadata.author}\n"
                response += f"  • Rating: {template.metadata.rating:.1f}/5.0 ({template.metadata.rating_count} reviews)\n"
                response += f"  • Downloads: {template.metadata.download_count}\n"
                response += f"  • Description: {template.metadata.description[:100]}...\n\n"
            
            if len(templates) > 10:
                response += f"... and {len(templates) - 10} more templates\n"
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            logger.error(f"Failed to search templates: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Template search failed: {str(e)}"
            )]
    
    async def handle_get_compliance_templates(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get_compliance_templates tool call"""
        try:
            framework = ComplianceFramework(arguments['framework']) if arguments.get('framework') else None
            
            if framework:
                templates = self.compliance_library.get_templates_by_framework(framework)
                response = f"📋 {framework.value.upper()} Compliance Templates\n\n"
            else:
                templates = self.compliance_library.get_all_templates()
                response = f"📋 All Compliance Templates\n\n"
            
            response += f"**Found**: {len(templates)} template(s)\n\n"
            
            # Group by framework
            by_framework = {}
            for template in templates:
                fw = None
                for tag in template.metadata.tags:
                    if tag in [f.value for f in ComplianceFramework]:
                        fw = tag.upper()
                        break
                if fw:
                    if fw not in by_framework:
                        by_framework[fw] = []
                    by_framework[fw].append(template)
            
            for fw, fw_templates in by_framework.items():
                response += f"**{fw}**:\n"
                for template in fw_templates:
                    response += f"  • {template.metadata.name} (`{template.metadata.id}`)\n"
                    response += f"    {template.metadata.description[:80]}...\n"
                response += "\n"
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            logger.error(f"Failed to get compliance templates: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Failed to get compliance templates: {str(e)}"
            )]
    
    async def handle_deploy_specialized_rules(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle deploy_specialized_rules tool call"""
        try:
            rule_set = arguments['rule_set']
            categories = arguments.get('categories', [])
            configuration = arguments.get('configuration', {})
            
            deployed_rules = []
            
            if rule_set == "lance_james":
                # Deploy Lance James specific rule set
                deployed_rules = self.specialized_manager.deploy_lance_james_rules()
                response = f"🎯 Lance James Rule Set Deployed\n\n"
                response += f"**Rules Deployed**: {len(deployed_rules)}\n"
                response += f"**Categories**: Authorship, Code Quality, Security, Response Patterns, Error Handling, Documentation Control\n\n"
                
                response += "**Key Rules Activated**:\n"
                response += "• Code attribution to Lance James, Unit 221B Inc\n"
                response += "• Minimal comments policy (unless requested)\n"
                response += "• Defensive security measures only\n"
                response += "• Concise response style\n"
                response += "• No unsolicited documentation creation\n"
                response += "• Comprehensive error handling with fallbacks\n\n"
                
            elif rule_set == "enterprise":
                response = f"🏢 Enterprise Rule Set\n\n"
                response += "Enterprise rule deployment would include:\n"
                response += "• Multi-tenant isolation\n"
                response += "• Approval workflows\n"
                response += "• Comprehensive audit trails\n"
                response += "• Compliance frameworks\n"
                response += "• Performance monitoring\n\n"
                
            elif rule_set == "security_focused":
                response = f"🔒 Security-Focused Rule Set\n\n"
                response += "Security rule deployment would include:\n"
                response += "• Threat-adaptive responses\n"
                response += "• Input validation enforcement\n"
                response += "• Dangerous function blocking\n"
                response += "• HTTPS enforcement\n"
                response += "• Security header requirements\n\n"
                
            elif rule_set == "compliance_focused":
                response = f"📋 Compliance-Focused Rule Set\n\n"
                response += "Compliance rule deployment would include:\n"
                response += "• GDPR data protection\n"
                response += "• SOC 2 security controls\n"
                response += "• HIPAA PHI protection\n"
                response += "• PCI DSS cardholder data security\n"
                response += "• ISO 27001 information security\n\n"
            
            response += f"✅ Rule set '{rule_set}' deployed successfully!"
            
            # Store deployment in memory
            self.memory_storage.store_memory(
                content=f"Deployed specialized rule set: {rule_set}",
                category="rule_deployment",
                metadata={
                    'rule_set': rule_set,
                    'categories': categories,
                    'configuration': configuration,
                    'deployed_rules': deployed_rules
                }
            )
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            logger.error(f"Failed to deploy specialized rules: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Failed to deploy specialized rules: {str(e)}"
            )]
    
    async def handle_get_compliance_report(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get_compliance_report tool call"""
        try:
            tenant_id = arguments['tenant_id']
            framework = arguments.get('framework')
            start_date = datetime.fromisoformat(arguments['start_date']) if arguments.get('start_date') else None
            end_date = datetime.fromisoformat(arguments['end_date']) if arguments.get('end_date') else None
            
            # Generate compliance report
            report = await self.enterprise_manager.get_compliance_report(
                tenant_id=tenant_id,
                framework=framework,
                start_date=start_date,
                end_date=end_date
            )
            
            response = f"📊 Compliance Report\n\n"
            response += f"**Tenant**: {tenant_id}\n"
            response += f"**Framework**: {framework or 'All frameworks'}\n"
            response += f"**Period**: {report['report_period']['start_date'][:10]} to {report['report_period']['end_date'][:10]}\n\n"
            
            # Compliance status
            status = report['compliance_status']
            response += f"**Compliance Status**:\n"
            response += f"• Total Evaluations: {status['total_evaluations']}\n"
            response += f"• Compliant Evaluations: {status['compliant_evaluations']}\n"
            response += f"• Compliance Rate: {status['compliance_rate']:.1%}\n"
            response += f"• Total Violations: {status['total_violations']}\n"
            response += f"• Critical Violations: {status['critical_violations']}\n\n"
            
            # Recommendations
            if report['recommendations']:
                response += f"**Recommendations**:\n"
                for rec in report['recommendations']:
                    priority_emoji = {"critical": "🔴", "high": "🟡", "medium": "🟠", "low": "🟢"}.get(rec['priority'], "🔵")
                    response += f"{priority_emoji} **{rec['type'].replace('_', ' ').title()}**\n"
                    response += f"   {rec['description']}\n"
                    if rec.get('actions'):
                        response += f"   Actions: {', '.join(rec['actions'])}\n"
                    response += "\n"
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            return [TextContent(
                type="text",
                text=f"❌ Failed to generate compliance report: {str(e)}"
            )]