#!/usr/bin/env python3
"""
Comprehensive Tests for Advanced Rules System
Tests all advanced rule types, templates, enterprise features, and hAIveMind integration

Author: Lance James, Unit 221B Inc
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
import sqlite3

# Import all the modules we're testing
from src.advanced_rule_types import (
    AdvancedRulesEngine, AdvancedRuleType, TriggerType, ComplianceFramework,
    AdvancedRule, TimeBasedSchedule, ConditionalTrigger, ComplianceRule
)
from src.rule_template_system import (
    RuleTemplateSystem, TemplateCategory, IndustryType, TemplateStatus,
    RuleTemplate, TemplateMetadata, TemplateParameter
)
from src.compliance_rule_templates import ComplianceTemplateLibrary
from src.enterprise_rule_features import (
    EnterpriseRuleManager, TenantType, ApprovalStatus, WorkflowStage,
    Tenant, ApprovalWorkflow, ApprovalRequest
)
from src.specialized_rule_categories import (
    SpecializedRuleManager, SpecializedRuleCategory,
    AuthorshipConfig, CodeQualityConfig, SecurityPostureConfig
)
from src.haivemind_advanced_rules_integration import (
    hAIveMindAdvancedRulesIntegration, LearningType, InsightType,
    LearningPattern, NetworkInsight
)
from src.advanced_rules_mcp_tools import AdvancedRulesMCPTools
from src.rules_engine import Rule, RuleType, RuleScope, RulePriority, RuleStatus, RuleCondition, RuleAction

class MockMemoryStorage:
    """Mock memory storage for testing"""
    
    def __init__(self):
        self.memories = []
        self.agent_id = "test-agent"
        self.machine_id = "test-machine"
        self.redis_client = None
    
    def store_memory(self, content: str, category: str, metadata: dict = None):
        memory = {
            'id': str(uuid.uuid4()),
            'content': content,
            'category': category,
            'metadata': metadata or {},
            'created_at': datetime.now()
        }
        self.memories.append(memory)
        return memory['id']
    
    def search_memories(self, query: str = "", category: str = None, limit: int = 50):
        results = []
        for memory in self.memories:
            if category and memory['category'] != category:
                continue
            if query and query.lower() not in memory['content'].lower():
                continue
            results.append(type('Memory', (), memory))
        return results[:limit]

class MockRulesEngine:
    """Mock rules engine for testing"""
    
    def __init__(self):
        self.db = MockRulesDatabase()
    
    def evaluate_rules(self, context):
        return {
            'configuration': {'test': True},
            'applied_rules': ['rule-1', 'rule-2'],
            'evaluation_time_ms': 50
        }

class MockRulesDatabase:
    """Mock rules database for testing"""
    
    def __init__(self):
        self.rules = {}
    
    def create_rule(self, rule):
        rule_id = rule.id or str(uuid.uuid4())
        self.rules[rule_id] = rule
        return rule_id
    
    def get_rule(self, rule_id):
        return self.rules.get(rule_id)
    
    def get_applicable_rules(self, context):
        return list(self.rules.values())

@pytest.fixture
def mock_memory_storage():
    """Fixture for mock memory storage"""
    return MockMemoryStorage()

@pytest.fixture
def mock_rules_engine():
    """Fixture for mock rules engine"""
    return MockRulesEngine()

@pytest.fixture
def temp_db():
    """Fixture for temporary database"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        yield f.name
    Path(f.name).unlink(missing_ok=True)

@pytest.fixture
def temp_dir():
    """Fixture for temporary directory"""
    with tempfile.TemporaryDirectory() as d:
        yield d

class TestAdvancedRuleTypes:
    """Test advanced rule types functionality"""
    
    @pytest.mark.asyncio
    async def test_advanced_rules_engine_initialization(self, mock_memory_storage, mock_rules_engine):
        """Test advanced rules engine initialization"""
        engine = AdvancedRulesEngine(mock_rules_engine, mock_memory_storage)
        
        assert engine.base_engine == mock_rules_engine
        assert engine.memory_storage == mock_memory_storage
        assert engine.cascading_queue is not None
        assert engine.compliance_auditor is not None
        assert engine.security_monitor is not None
    
    @pytest.mark.asyncio
    async def test_conditional_rule_evaluation(self, mock_memory_storage, mock_rules_engine):
        """Test conditional rule evaluation"""
        engine = AdvancedRulesEngine(mock_rules_engine, mock_memory_storage)
        
        # Create a conditional rule
        conditional_rule = AdvancedRule(
            id="test-conditional",
            name="Test Conditional Rule",
            description="Test conditional rule",
            rule_type=RuleType.SECURITY,
            advanced_type=AdvancedRuleType.CONDITIONAL,
            scope=RuleScope.GLOBAL,
            priority=RulePriority.HIGH,
            status=RuleStatus.ACTIVE,
            conditions=[],
            actions=[],
            tags=["test"],
            created_at=datetime.now(),
            created_by="test",
            updated_at=datetime.now(),
            updated_by="test",
            conditional_trigger=ConditionalTrigger(
                condition_expression="context.get('test_condition') == True",
                required_context_fields=["test_condition"],
                evaluation_interval=60,
                cooldown_period=300
            )
        )
        
        # Test evaluation with matching context
        context = {"test_condition": True}
        
        # Mock the _get_applicable_advanced_rules method
        with patch.object(engine, '_get_applicable_advanced_rules', return_value=[conditional_rule]):
            result = await engine.evaluate_advanced_rules(context)
        
        assert 'conditional' in result['advanced_results']
        assert result['evaluation_time_ms'] > 0
    
    @pytest.mark.asyncio
    async def test_time_based_rule_scheduling(self, mock_memory_storage, mock_rules_engine):
        """Test time-based rule scheduling"""
        engine = AdvancedRulesEngine(mock_rules_engine, mock_memory_storage)
        
        # Create a time-based rule
        time_rule = AdvancedRule(
            id="test-time-based",
            name="Test Time-Based Rule",
            description="Test time-based rule",
            rule_type=RuleType.OPERATIONAL,
            advanced_type=AdvancedRuleType.TIME_BASED,
            scope=RuleScope.GLOBAL,
            priority=RulePriority.NORMAL,
            status=RuleStatus.ACTIVE,
            conditions=[],
            actions=[],
            tags=["test"],
            created_at=datetime.now(),
            created_by="test",
            updated_at=datetime.now(),
            updated_by="test",
            schedule=TimeBasedSchedule(
                cron_expression="0 0 * * *",  # Daily at midnight
                timezone="UTC",
                max_executions=10
            )
        )
        
        context = {"task_type": "scheduled_task"}
        
        with patch.object(engine, '_get_applicable_advanced_rules', return_value=[time_rule]):
            result = await engine.evaluate_advanced_rules(context)
        
        assert 'time_based' in result['advanced_results']

class TestRuleTemplateSystem:
    """Test rule template system functionality"""
    
    def test_template_system_initialization(self, temp_db, temp_dir, mock_memory_storage):
        """Test template system initialization"""
        config = {"test": True}
        template_system = RuleTemplateSystem(temp_db, temp_dir, mock_memory_storage, config)
        
        assert template_system.db_path.exists()
        assert template_system.templates_dir.exists()
        assert (template_system.templates_dir / "community").exists()
        assert (template_system.templates_dir / "custom").exists()
    
    def test_create_template(self, temp_db, temp_dir, mock_memory_storage):
        """Test template creation"""
        template_system = RuleTemplateSystem(temp_db, temp_dir, mock_memory_storage, {})
        
        # Create a test template
        template = RuleTemplate(
            metadata=TemplateMetadata(
                id="test-template",
                name="Test Template",
                description="A test template",
                version="1.0.0",
                author="Test Author",
                organization="Test Org",
                category=TemplateCategory.SECURITY,
                industry=IndustryType.TECHNOLOGY,
                status=TemplateStatus.ACTIVE,
                tags=["test"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="test_param",
                    type="string",
                    description="Test parameter",
                    required=True
                )
            ],
            template_content={
                "name": "Test Rule from Template",
                "description": "Generated from test template",
                "rule_type": "security",
                "actions": [{"action_type": "set", "target": "test", "value": "{{ test_param }}"}]
            }
        )
        
        template_id = template_system.create_template(template)
        assert template_id == "test-template"
        
        # Verify template was stored
        stored_template = template_system.get_template(template_id)
        assert stored_template is not None
        assert stored_template.metadata.name == "Test Template"
    
    def test_template_instantiation(self, temp_db, temp_dir, mock_memory_storage):
        """Test template instantiation"""
        template_system = RuleTemplateSystem(temp_db, temp_dir, mock_memory_storage, {})
        
        # Create and store a template first
        template = RuleTemplate(
            metadata=TemplateMetadata(
                id="instantiation-test",
                name="Instantiation Test Template",
                description="Template for testing instantiation",
                version="1.0.0",
                author="Test Author",
                organization="Test Org",
                category=TemplateCategory.CODING,
                industry=IndustryType.GENERIC,
                status=TemplateStatus.ACTIVE,
                tags=["test"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="rule_name",
                    type="string",
                    description="Name of the rule",
                    required=True
                ),
                TemplateParameter(
                    name="target_value",
                    type="string",
                    description="Target value",
                    required=True
                )
            ],
            template_content={
                "name": "{{ rule_name }}",
                "description": "Rule created from template",
                "rule_type": "coding_style",
                "scope": "global",
                "priority": "NORMAL",
                "actions": [{"action_type": "set", "target": "test", "value": "{{ target_value }}"}]
            }
        )
        
        template_system.create_template(template)
        
        # Instantiate the template
        parameters = {
            "rule_name": "Test Instantiated Rule",
            "target_value": "test_value"
        }
        
        rule = template_system.instantiate_template("instantiation-test", parameters, "test_user")
        
        assert rule is not None
        assert rule.name == "Test Instantiated Rule"
        assert len(rule.actions) == 1
        assert rule.actions[0].value == "test_value"
    
    def test_template_search(self, temp_db, temp_dir, mock_memory_storage):
        """Test template search functionality"""
        template_system = RuleTemplateSystem(temp_db, temp_dir, mock_memory_storage, {})
        
        # Create multiple templates
        for i in range(3):
            template = RuleTemplate(
                metadata=TemplateMetadata(
                    id=f"search-test-{i}",
                    name=f"Search Test Template {i}",
                    description=f"Template {i} for testing search",
                    version="1.0.0",
                    author="Test Author",
                    organization="Test Org",
                    category=TemplateCategory.SECURITY if i % 2 == 0 else TemplateCategory.COMPLIANCE,
                    industry=IndustryType.TECHNOLOGY,
                    status=TemplateStatus.ACTIVE,
                    tags=["test", f"tag{i}"],
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                ),
                parameters=[],
                template_content={"name": f"Template {i}"}
            )
            template_system.create_template(template)
        
        # Test search by category
        security_templates = template_system.search_templates(category=TemplateCategory.SECURITY)
        assert len(security_templates) == 2  # Templates 0 and 2
        
        # Test search by query
        search_results = template_system.search_templates(query="Template 1")
        assert len(search_results) == 1
        assert search_results[0].metadata.name == "Search Test Template 1"

class TestComplianceTemplates:
    """Test compliance rule templates"""
    
    def test_compliance_library_initialization(self):
        """Test compliance template library initialization"""
        library = ComplianceTemplateLibrary()
        
        assert len(library.templates) > 0
        assert library.get_template("gdpr-article-6-lawful-processing") is not None
        assert library.get_template("soc2-security-access-controls") is not None
        assert library.get_template("hipaa-security-access-control") is not None
    
    def test_gdpr_templates(self):
        """Test GDPR compliance templates"""
        library = ComplianceTemplateLibrary()
        gdpr_templates = library.get_templates_by_framework(ComplianceFramework.GDPR)
        
        assert len(gdpr_templates) > 0
        
        # Check specific GDPR templates
        article_6_template = library.get_template("gdpr-article-6-lawful-processing")
        assert article_6_template is not None
        assert "gdpr" in article_6_template.metadata.tags
        assert len(article_6_template.parameters) > 0
    
    def test_soc2_templates(self):
        """Test SOC 2 compliance templates"""
        library = ComplianceTemplateLibrary()
        soc2_templates = library.get_templates_by_framework(ComplianceFramework.SOC2)
        
        assert len(soc2_templates) > 0
        
        # Check SOC 2 access control template
        access_template = library.get_template("soc2-security-access-controls")
        assert access_template is not None
        assert "soc2" in access_template.metadata.tags
    
    def test_hipaa_templates(self):
        """Test HIPAA compliance templates"""
        library = ComplianceTemplateLibrary()
        hipaa_templates = library.get_templates_by_framework(ComplianceFramework.HIPAA)
        
        assert len(hipaa_templates) > 0
        
        # Check HIPAA access control template
        access_template = library.get_template("hipaa-security-access-control")
        assert access_template is not None
        assert "hipaa" in access_template.metadata.tags
        assert access_template.metadata.industry == IndustryType.HEALTHCARE

class TestEnterpriseFeatures:
    """Test enterprise rule features"""
    
    @pytest.mark.asyncio
    async def test_enterprise_manager_initialization(self, temp_db, mock_memory_storage):
        """Test enterprise manager initialization"""
        manager = EnterpriseRuleManager(temp_db, mock_memory_storage, config={})
        
        assert manager.db_path.exists()
        assert manager.workflow_engine is not None
        assert manager.audit_system is not None
        assert manager.impact_analyzer is not None
        assert manager.tenant_manager is not None
    
    @pytest.mark.asyncio
    async def test_tenant_creation(self, temp_db, mock_memory_storage):
        """Test tenant creation"""
        manager = EnterpriseRuleManager(temp_db, mock_memory_storage, config={})
        
        tenant = Tenant(
            id="test-tenant",
            name="Test Tenant",
            type=TenantType.ENTERPRISE,
            parent_tenant_id=None,
            settings={"test": True},
            created_at=datetime.now(),
            created_by="test_user"
        )
        
        tenant_id = await manager.tenant_manager.create_tenant(tenant)
        assert tenant_id == "test-tenant"
    
    @pytest.mark.asyncio
    async def test_rule_approval_workflow(self, temp_db, mock_memory_storage):
        """Test rule approval workflow"""
        manager = EnterpriseRuleManager(temp_db, mock_memory_storage, config={})
        
        # Create a test rule
        test_rule = AdvancedRule(
            id="approval-test-rule",
            name="Test Approval Rule",
            description="Rule for testing approval workflow",
            rule_type=RuleType.SECURITY,
            advanced_type=AdvancedRuleType.CONDITIONAL,
            scope=RuleScope.GLOBAL,
            priority=RulePriority.HIGH,
            status=RuleStatus.TESTING,
            conditions=[],
            actions=[],
            tags=["test"],
            created_at=datetime.now(),
            created_by="test_user",
            updated_at=datetime.now(),
            updated_by="test_user"
        )
        
        # Mock the impact analyzer
        with patch.object(manager.impact_analyzer, 'analyze_rule_impact') as mock_analyze:
            mock_analyze.return_value = Mock(
                rule_id="approval-test-rule",
                affected_systems=["system1"],
                affected_users=10,
                risk_level="medium"
            )
            
            # Request approval
            request_id = await manager.create_rule_with_approval(
                test_rule, "test_user", "workflow-1", "tenant-1"
            )
            
            assert request_id is not None
            assert len(mock_memory_storage.memories) > 0

class TestSpecializedRuleCategories:
    """Test specialized rule categories"""
    
    def test_specialized_manager_initialization(self, mock_memory_storage, mock_rules_engine):
        """Test specialized rule manager initialization"""
        manager = SpecializedRuleManager(mock_memory_storage, mock_rules_engine)
        
        assert manager.memory_storage == mock_memory_storage
        assert manager.rules_engine == mock_rules_engine
        assert manager.factory is not None
    
    def test_lance_james_rules_deployment(self, mock_memory_storage, mock_rules_engine):
        """Test Lance James specific rule deployment"""
        manager = SpecializedRuleManager(mock_memory_storage, mock_rules_engine)
        
        deployed_rules = manager.deploy_lance_james_rules()
        
        assert len(deployed_rules) > 0
        assert len(mock_memory_storage.memories) > 0
        
        # Check that memory was stored
        deployment_memory = next(
            (m for m in mock_memory_storage.memories if "Lance James" in m['content']), 
            None
        )
        assert deployment_memory is not None
    
    def test_authorship_rules_creation(self, mock_memory_storage):
        """Test authorship rules creation"""
        from src.specialized_rule_categories import SpecializedRuleFactory
        
        factory = SpecializedRuleFactory(mock_memory_storage)
        
        config = AuthorshipConfig(
            default_author="Lance James",
            organization="Unit 221B Inc",
            copyright_template="# Author: {author}, {organization}",
            license_header="# Licensed under MIT",
            disable_ai_attribution=True
        )
        
        rules = factory.create_authorship_rules(config)
        
        assert len(rules) >= 1
        assert any("Lance James" in rule.description for rule in rules)
        assert any(rule.rule_type == RuleType.AUTHORSHIP for rule in rules)
    
    def test_code_quality_rules_creation(self, mock_memory_storage):
        """Test code quality rules creation"""
        from src.specialized_rule_categories import SpecializedRuleFactory
        
        factory = SpecializedRuleFactory(mock_memory_storage)
        
        config = CodeQualityConfig(
            max_complexity=10,
            max_line_length=120,
            min_test_coverage=0.8,
            enforce_naming_conventions=True
        )
        
        rules = factory.create_code_quality_rules(config)
        
        assert len(rules) >= 1
        assert any(rule.rule_type == RuleType.CODING_STYLE for rule in rules)
        assert any("complexity" in rule.name.lower() for rule in rules)
    
    def test_security_posture_rules_creation(self, mock_memory_storage):
        """Test security posture rules creation"""
        from src.specialized_rule_categories import SpecializedRuleFactory
        
        factory = SpecializedRuleFactory(mock_memory_storage)
        
        config = SecurityPostureConfig(
            threat_level_threshold=0.5,
            require_input_validation=True,
            block_dangerous_functions=["eval", "exec"],
            enforce_https=True
        )
        
        rules = factory.create_security_posture_rules(config)
        
        assert len(rules) >= 1
        assert any(rule.rule_type == RuleType.SECURITY for rule in rules)
        assert any(rule.advanced_type == AdvancedRuleType.SECURITY_ADAPTIVE for rule in rules)

class TesthAIveMindIntegration:
    """Test hAIveMind advanced rules integration"""
    
    @pytest.mark.asyncio
    async def test_haivemind_integration_initialization(self, mock_memory_storage, mock_rules_engine):
        """Test hAIveMind integration initialization"""
        integration = hAIveMindAdvancedRulesIntegration(
            mock_rules_engine, mock_memory_storage
        )
        
        assert integration.rules_engine == mock_rules_engine
        assert integration.memory_storage == mock_memory_storage
        assert integration.pattern_learner is not None
        assert integration.effectiveness_analyzer is not None
        assert integration.network_intelligence is not None
    
    @pytest.mark.asyncio
    async def test_enhanced_rule_evaluation(self, mock_memory_storage, mock_rules_engine):
        """Test enhanced rule evaluation with hAIveMind awareness"""
        integration = hAIveMindAdvancedRulesIntegration(
            mock_rules_engine, mock_memory_storage
        )
        
        context = {
            "task_type": "code_generation",
            "file_type": "py",
            "agent_id": "test-agent"
        }
        
        # Mock the awareness data gathering
        with patch.object(integration, '_gather_awareness_data') as mock_awareness:
            mock_awareness.return_value = {
                'network_status': {'status': 'connected'},
                'cross_agent_patterns': {},
                'historical_context': {}
            }
            
            result = await integration.evaluate_with_advanced_awareness(context)
            
            assert 'haivemind_awareness' in result
            assert 'awareness_data' in result['haivemind_awareness']
            assert 'processing_time_ms' in result['haivemind_awareness']
    
    @pytest.mark.asyncio
    async def test_learning_pattern_discovery(self, mock_memory_storage):
        """Test learning pattern discovery"""
        from src.haivemind_advanced_rules_integration import RulePatternLearner
        
        learner = RulePatternLearner(mock_memory_storage)
        
        context = {"task_type": "code_generation", "file_type": "py"}
        learning_signals = {"execution_time": 500, "success": True, "rules_applied": 5}
        
        await learner.update_patterns(context, learning_signals)
        
        # Check that pattern was stored in memory
        pattern_memories = mock_memory_storage.search_memories(category="rule_learning")
        assert len(pattern_memories) > 0
    
    @pytest.mark.asyncio
    async def test_rule_effectiveness_analysis(self, mock_memory_storage):
        """Test rule effectiveness analysis"""
        from src.haivemind_advanced_rules_integration import RuleEffectivenessAnalyzer
        
        analyzer = RuleEffectivenessAnalyzer(mock_memory_storage)
        
        # Add some test evaluation data
        for i in range(5):
            mock_memory_storage.store_memory(
                content=f"Rule evaluation {i}",
                category="advanced_rules",
                metadata={
                    'result': {'success': True if i % 2 == 0 else False},
                    'learning_signals': {'execution_time': 100 + i * 50, 'success': True if i % 2 == 0 else False}
                }
            )
        
        metrics = await analyzer.get_rule_metrics("test-rule")
        
        # Since we don't have real rule evaluation data, metrics might be None
        # but the method should not raise an exception
        assert metrics is None or hasattr(metrics, 'success_rate')

class TestAdvancedRulesMCPTools:
    """Test advanced rules MCP tools"""
    
    def test_mcp_tools_initialization(self, mock_memory_storage, mock_rules_engine):
        """Test MCP tools initialization"""
        config = {"test": True}
        tools = AdvancedRulesMCPTools(mock_memory_storage, mock_rules_engine, config)
        
        assert tools.memory_storage == mock_memory_storage
        assert tools.base_rules_engine == mock_rules_engine
        assert tools.advanced_engine is not None
        assert tools.template_system is not None
        assert tools.compliance_library is not None
    
    def test_get_tools(self, mock_memory_storage, mock_rules_engine):
        """Test getting MCP tools list"""
        config = {"test": True}
        tools = AdvancedRulesMCPTools(mock_memory_storage, mock_rules_engine, config)
        
        tool_list = tools.get_tools()
        
        assert len(tool_list) > 0
        
        # Check for specific tools
        tool_names = [tool.name for tool in tool_list]
        assert "create_advanced_rule" in tool_names
        assert "evaluate_advanced_rules" in tool_names
        assert "create_rule_template" in tool_names
        assert "search_templates" in tool_names
        assert "get_compliance_templates" in tool_names
        assert "deploy_specialized_rules" in tool_names
    
    @pytest.mark.asyncio
    async def test_create_advanced_rule_handler(self, mock_memory_storage, mock_rules_engine):
        """Test create advanced rule handler"""
        config = {"test": True}
        tools = AdvancedRulesMCPTools(mock_memory_storage, mock_rules_engine, config)
        
        arguments = {
            "rule_definition": {
                "name": "Test Advanced Rule",
                "description": "A test advanced rule"
            },
            "advanced_type": "conditional",
            "trigger_config": {
                "trigger_type": "event_driven",
                "conditions": {"test": True}
            }
        }
        
        result = await tools.handle_create_advanced_rule(arguments)
        
        assert len(result) == 1
        assert "Advanced Rule Creation" in result[0].text
        assert "successfully" in result[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_search_templates_handler(self, mock_memory_storage, mock_rules_engine):
        """Test search templates handler"""
        config = {"test": True}
        tools = AdvancedRulesMCPTools(mock_memory_storage, mock_rules_engine, config)
        
        arguments = {
            "query": "security",
            "category": "security",
            "limit": 10
        }
        
        result = await tools.handle_search_templates(arguments)
        
        assert len(result) == 1
        assert "Template Search Results" in result[0].text
    
    @pytest.mark.asyncio
    async def test_deploy_specialized_rules_handler(self, mock_memory_storage, mock_rules_engine):
        """Test deploy specialized rules handler"""
        config = {"test": True}
        tools = AdvancedRulesMCPTools(mock_memory_storage, mock_rules_engine, config)
        
        arguments = {
            "rule_set": "lance_james",
            "categories": ["authorship_attribution", "code_quality_enforcement"]
        }
        
        result = await tools.handle_deploy_specialized_rules(arguments)
        
        assert len(result) == 1
        assert "Lance James Rule Set Deployed" in result[0].text
        assert "successfully" in result[0].text.lower()

class TestIntegrationScenarios:
    """Test integration scenarios across multiple components"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_template_to_rule_creation(self, temp_db, temp_dir, mock_memory_storage):
        """Test end-to-end template creation and rule instantiation"""
        # Initialize template system
        template_system = RuleTemplateSystem(temp_db, temp_dir, mock_memory_storage, {})
        
        # Create a template
        template = RuleTemplate(
            metadata=TemplateMetadata(
                id="e2e-test-template",
                name="End-to-End Test Template",
                description="Template for end-to-end testing",
                version="1.0.0",
                author="Test Author",
                organization="Test Org",
                category=TemplateCategory.SECURITY,
                industry=IndustryType.TECHNOLOGY,
                status=TemplateStatus.ACTIVE,
                tags=["test", "e2e"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            parameters=[
                TemplateParameter(
                    name="security_level",
                    type="string",
                    description="Security level",
                    required=True,
                    allowed_values=["low", "medium", "high"]
                )
            ],
            template_content={
                "name": "Security Rule - {{ security_level | title }}",
                "description": "Security rule with {{ security_level }} level protection",
                "rule_type": "security",
                "scope": "global",
                "priority": "{% if security_level == 'high' %}CRITICAL{% else %}HIGH{% endif %}",
                "actions": [
                    {"action_type": "validate", "target": "security_level", "value": "{{ security_level }}"}
                ]
            }
        )
        
        # Store template
        template_id = template_system.create_template(template)
        
        # Instantiate template
        parameters = {"security_level": "high"}
        rule = template_system.instantiate_template(template_id, parameters, "test_user")
        
        # Verify rule was created correctly
        assert rule is not None
        assert rule.name == "Security Rule - High"
        assert "high level protection" in rule.description
        assert rule.rule_type == RuleType.SECURITY
        assert rule.priority == RulePriority.CRITICAL
        assert len(rule.actions) == 1
        assert rule.actions[0].value == "high"
    
    @pytest.mark.asyncio
    async def test_compliance_template_to_enterprise_workflow(self, temp_db, mock_memory_storage):
        """Test compliance template integration with enterprise workflow"""
        # Initialize components
        compliance_library = ComplianceTemplateLibrary()
        enterprise_manager = EnterpriseRuleManager(temp_db, mock_memory_storage, config={})
        
        # Get a GDPR template
        gdpr_template = compliance_library.get_template("gdpr-article-6-lawful-processing")
        assert gdpr_template is not None
        
        # Create a tenant
        tenant = Tenant(
            id="compliance-test-tenant",
            name="Compliance Test Tenant",
            type=TenantType.ENTERPRISE,
            parent_tenant_id=None,
            settings={"compliance_required": True},
            created_at=datetime.now(),
            created_by="test_user"
        )
        
        tenant_id = await enterprise_manager.tenant_manager.create_tenant(tenant)
        
        # Verify tenant was created
        assert tenant_id == "compliance-test-tenant"
        
        # This demonstrates how compliance templates would integrate
        # with enterprise workflows in a real scenario
    
    @pytest.mark.asyncio
    async def test_specialized_rules_with_haivemind_learning(self, mock_memory_storage, mock_rules_engine):
        """Test specialized rules integration with hAIveMind learning"""
        # Initialize components
        specialized_manager = SpecializedRuleManager(mock_memory_storage, mock_rules_engine)
        haivemind_integration = hAIveMindAdvancedRulesIntegration(
            mock_rules_engine, mock_memory_storage
        )
        
        # Deploy Lance James rules
        deployed_rules = specialized_manager.deploy_lance_james_rules()
        assert len(deployed_rules) > 0
        
        # Simulate rule evaluation with learning
        context = {
            "task_type": "code_generation",
            "file_type": "py",
            "author_required": True
        }
        
        # Mock awareness data
        with patch.object(haivemind_integration, '_gather_awareness_data') as mock_awareness:
            mock_awareness.return_value = {
                'network_status': {'status': 'connected'},
                'cross_agent_patterns': {},
                'historical_context': {}
            }
            
            result = await haivemind_integration.evaluate_with_advanced_awareness(context)
            
            # Verify enhanced evaluation
            assert 'haivemind_awareness' in result
            assert result['haivemind_awareness']['learning_applied'] is not None
        
        # Check that memories were stored
        rule_memories = mock_memory_storage.search_memories(category="rules")
        learning_memories = mock_memory_storage.search_memories(category="advanced_rules")
        
        assert len(rule_memories) > 0 or len(learning_memories) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])