#!/usr/bin/env python3
"""
Integration Tests for Workflow Automation System
Tests the complete workflow automation system with hAIveMind integration
"""

import asyncio
import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

# Import workflow automation components
from src.workflow_automation_engine import (
    WorkflowAutomationEngine, WorkflowTemplate, WorkflowStep, WorkflowExecution,
    WorkflowStatus, TriggerType, WorkflowSuggestion
)
from src.workflow_automation_mcp_tools import WorkflowAutomationMCPTools
from src.workflow_haivemind_integration import WorkflowhAIveMindIntegration
from src.workflow_validation_rollback import WorkflowValidationRollbackIntegration
from src.workflow_api_server import WorkflowAPIServer

class MockStorage:
    """Mock storage for testing"""
    
    def __init__(self):
        self.memories = []
        self.agent_id = "test_agent"
        self.machine_id = "test_machine"
    
    async def store_memory(self, content: str, category: str, context: str = "", 
                          metadata: Dict[str, Any] = None, tags: List[str] = None):
        """Store memory mock"""
        memory = {
            'id': f"mem_{len(self.memories)}",
            'content': content,
            'category': category,
            'context': context,
            'metadata': metadata or {},
            'tags': tags or [],
            'timestamp': time.time()
        }
        self.memories.append(memory)
        return memory['id']
    
    async def search_memories(self, query: str, category: str = None, limit: int = 10):
        """Search memories mock"""
        results = []
        for memory in self.memories:
            if query.lower() in memory['content'].lower():
                if not category or memory['category'] == category:
                    results.append(memory)
                    if len(results) >= limit:
                        break
        return results

@pytest.fixture
async def mock_storage():
    """Create mock storage"""
    return MockStorage()

@pytest.fixture
async def test_config():
    """Test configuration"""
    return {
        "workflow_learning": {"enabled": True},
        "workflow_sharing": {"enabled": True},
        "workflow_optimization": {"enabled": True},
        "workflow_validation": {
            "default_level": "standard",
            "strict_mode": False
        },
        "workflow_rollback": {
            "default_strategy": "graceful",
            "auto_rollback": True,
            "checkpoint_interval": 3
        },
        "workflow_api": {
            "host": "localhost",
            "port": 8902,
            "api_key_required": False,
            "api_keys": ["test-key"],
            "allowed_origins": ["*"]
        }
    }

@pytest.fixture
async def workflow_engine(mock_storage, test_config):
    """Create workflow engine for testing"""
    engine = WorkflowAutomationEngine(mock_storage, test_config)
    await engine.initialize()
    return engine

@pytest.fixture
async def workflow_mcp_tools(mock_storage, test_config):
    """Create workflow MCP tools for testing"""
    tools = WorkflowAutomationMCPTools(mock_storage, test_config)
    await tools._ensure_initialized()
    return tools

@pytest.fixture
async def haivemind_integration(workflow_engine, mock_storage, test_config):
    """Create hAIveMind integration for testing"""
    integration = WorkflowhAIveMindIntegration(workflow_engine, mock_storage, test_config)
    await integration.initialize()
    return integration

@pytest.fixture
async def validation_rollback(mock_storage, test_config):
    """Create validation and rollback system for testing"""
    system = WorkflowValidationRollbackIntegration(mock_storage, test_config)
    return system

class TestWorkflowAutomationEngine:
    """Test workflow automation engine"""
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, workflow_engine):
        """Test engine initialization"""
        assert workflow_engine is not None
        assert len(workflow_engine.templates) > 0
        assert "incident_response" in workflow_engine.templates
        assert "security_alert" in workflow_engine.templates
    
    @pytest.mark.asyncio
    async def test_workflow_suggestions(self, workflow_engine):
        """Test workflow suggestions"""
        suggestions = await workflow_engine.suggest_workflows(
            context="security incident detected",
            recent_commands=["hv-status", "hv-broadcast"],
            intent="handle security threat"
        )
        
        assert len(suggestions) > 0
        assert any(s.workflow_id == "security_alert" for s in suggestions)
        assert all(s.confidence > 0 for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_workflow_execution(self, workflow_engine):
        """Test workflow execution"""
        # Execute incident response workflow
        execution_id = await workflow_engine.execute_workflow(
            template_id="incident_response",
            parameters={"severity": "critical"},
            trigger_type=TriggerType.MANUAL,
            user_id="test_user"
        )
        
        assert execution_id is not None
        
        # Check execution status
        status = await workflow_engine.get_workflow_status(execution_id)
        assert status is not None
        assert status['execution_id'] == execution_id
        assert status['template_id'] == "incident_response"
    
    @pytest.mark.asyncio
    async def test_custom_workflow_creation(self, workflow_engine):
        """Test custom workflow creation"""
        workflow_data = {
            "name": "Test Custom Workflow",
            "description": "A test workflow",
            "category": "testing",
            "steps": [
                {
                    "id": "test_step",
                    "command": "hv-status",
                    "description": "Test step",
                    "parameters": {}
                }
            ]
        }
        
        template_id = await workflow_engine.create_custom_workflow(workflow_data)
        assert template_id is not None
        assert template_id in workflow_engine.templates
        
        template = workflow_engine.templates[template_id]
        assert template.name == "Test Custom Workflow"
        assert len(template.steps) == 1

class TestWorkflowMCPTools:
    """Test workflow MCP tools"""
    
    @pytest.mark.asyncio
    async def test_suggest_workflows_tool(self, workflow_mcp_tools):
        """Test workflow suggestions MCP tool"""
        result = await workflow_mcp_tools.suggest_workflows(
            context="incident response needed",
            intent="handle emergency"
        )
        
        assert result is not None
        assert 'suggestions' in result
        assert len(result['suggestions']) > 0
        assert result['title'] == '🔄 Smart Workflow Suggestions'
    
    @pytest.mark.asyncio
    async def test_execute_workflow_tool(self, workflow_mcp_tools):
        """Test workflow execution MCP tool"""
        result = await workflow_mcp_tools.execute_workflow(
            workflow_id="incident_response",
            parameters='{"severity": "warning"}'
        )
        
        assert result is not None
        assert result['status'] == 'success'
        assert 'execution_id' in result
    
    @pytest.mark.asyncio
    async def test_list_workflows_tool(self, workflow_mcp_tools):
        """Test list workflows MCP tool"""
        result = await workflow_mcp_tools.list_workflows()
        
        assert result is not None
        assert 'templates' in result
        assert len(result['templates']) > 0
        assert result['title'] == '📋 Available Workflow Templates'
    
    @pytest.mark.asyncio
    async def test_workflow_analytics_tool(self, workflow_mcp_tools):
        """Test workflow analytics MCP tool"""
        result = await workflow_mcp_tools.workflow_analytics()
        
        assert result is not None
        assert 'overview' in result
        assert 'total_templates' in result['overview']
        assert result['title'] == '📈 Workflow System Analytics'

class TesthAIveMindIntegration:
    """Test hAIveMind integration"""
    
    @pytest.mark.asyncio
    async def test_workflow_start_integration(self, haivemind_integration, workflow_engine):
        """Test workflow start integration with hAIveMind"""
        # Create test execution
        execution = WorkflowExecution(
            id="test_execution",
            template_id="incident_response",
            name="Test Execution",
            trigger_type=TriggerType.MANUAL,
            start_time=time.time()
        )
        
        # Test workflow start handling
        await haivemind_integration.on_workflow_start(execution)
        
        # Check that memory was stored
        memories = haivemind_integration.storage.memories
        assert len(memories) > 0
        
        start_memory = next((m for m in memories if 'workflow_execution_start' in m['metadata']), None)
        assert start_memory is not None
        assert 'haivemind-learning' in start_memory['tags']
    
    @pytest.mark.asyncio
    async def test_workflow_completion_integration(self, haivemind_integration, workflow_engine):
        """Test workflow completion integration"""
        # Create test execution
        execution = WorkflowExecution(
            id="test_execution",
            template_id="incident_response",
            name="Test Execution",
            trigger_type=TriggerType.MANUAL,
            start_time=time.time(),
            end_time=time.time() + 300,
            status=WorkflowStatus.COMPLETED,
            completed_steps=["step1", "step2"]
        )
        
        # Test workflow completion handling
        await haivemind_integration.on_workflow_complete(execution)
        
        # Check that completion memory was stored
        memories = haivemind_integration.storage.memories
        completion_memory = next((m for m in memories if 'workflow_execution_complete' in m['metadata']), None)
        assert completion_memory is not None
    
    @pytest.mark.asyncio
    async def test_enhanced_suggestions(self, haivemind_integration, workflow_engine):
        """Test enhanced workflow suggestions"""
        # Create base suggestions
        base_suggestions = [
            WorkflowSuggestion(
                workflow_id="incident_response",
                name="Incident Response",
                confidence=0.7,
                reason="Test suggestion",
                context_match={},
                estimated_duration=300,
                success_probability=0.8
            )
        ]
        
        # Enhance with hAIveMind intelligence
        enhanced = await haivemind_integration.enhance_workflow_suggestions(
            base_suggestions,
            context="security incident"
        )
        
        assert len(enhanced) == len(base_suggestions)
        # Enhanced suggestions should maintain or improve confidence
        assert enhanced[0].confidence >= base_suggestions[0].confidence
    
    @pytest.mark.asyncio
    async def test_command_sequence_learning(self, haivemind_integration):
        """Test learning from command sequences"""
        sequences = [
            ["hv-status", "hv-broadcast", "hv-delegate"],
            ["hv-query", "remember", "hv-broadcast"],
            ["hv-sync", "hv-status", "remember"]
        ]
        
        learned_patterns = await haivemind_integration.learn_from_command_sequences(sequences)
        
        assert isinstance(learned_patterns, list)
        # Should learn at least some patterns
        if learned_patterns:
            pattern = learned_patterns[0]
            assert 'type' in pattern
            assert pattern['type'] == 'learned_workflow'
            assert 'steps' in pattern

class TestWorkflowValidationRollback:
    """Test workflow validation and rollback"""
    
    @pytest.mark.asyncio
    async def test_workflow_template_validation(self, validation_rollback, workflow_engine):
        """Test workflow template validation"""
        template = workflow_engine.templates["incident_response"]
        
        result = await validation_rollback.validator.validate_workflow_template(template)
        
        assert result is not None
        assert result.valid is True
        assert len(result.checks_performed) > 0
        assert result.confidence > 0
    
    @pytest.mark.asyncio
    async def test_workflow_execution_validation(self, validation_rollback, workflow_engine):
        """Test workflow execution validation"""
        template = workflow_engine.templates["incident_response"]
        execution = WorkflowExecution(
            id="test_execution",
            template_id="incident_response",
            name="Test Execution",
            parameters={"severity": "critical"}
        )
        
        result = await validation_rollback.validator.validate_workflow_execution(execution, template)
        
        assert result is not None
        assert isinstance(result.valid, bool)
        assert result.confidence >= 0
    
    @pytest.mark.asyncio
    async def test_rollback_point_creation(self, validation_rollback):
        """Test rollback point creation"""
        execution = WorkflowExecution(
            id="test_execution",
            template_id="incident_response",
            name="Test Execution"
        )
        
        system_state = {"test": "state"}
        
        rollback_point_id = await validation_rollback.rollback_manager.create_rollback_point(
            execution, "test_step", system_state
        )
        
        assert rollback_point_id is not None
        assert execution.id in validation_rollback.rollback_manager.rollback_points
        
        rollback_points = validation_rollback.rollback_manager.rollback_points[execution.id]
        assert len(rollback_points) == 1
        assert rollback_points[0].step_id == "test_step"

class TestWorkflowAPIIntegration:
    """Test workflow API integration"""
    
    @pytest.mark.asyncio
    async def test_api_server_initialization(self, mock_storage, test_config):
        """Test API server initialization"""
        from src.workflow_api_server import WorkflowAPIServer
        
        server = WorkflowAPIServer(mock_storage, test_config)
        await server.initialize()
        
        assert server.workflow_engine is not None
        assert server.haivemind_integration is not None
        assert server.validation_rollback is not None
    
    @pytest.mark.asyncio
    async def test_webhook_notification(self, mock_storage, test_config):
        """Test webhook notifications"""
        from src.workflow_api_server import WorkflowAPIServer, WebhookConfig
        
        server = WorkflowAPIServer(mock_storage, test_config)
        await server.initialize()
        
        # Add test webhook
        webhook_config = WebhookConfig(
            url="http://test.example.com/webhook",
            events=["workflow.started", "workflow.completed"],
            secret="test_secret"
        )
        server.webhooks["test_webhook"] = webhook_config
        
        # Mock aiohttp to avoid actual HTTP calls
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            # Send test notification
            await server._send_webhook_notification("workflow.started", {
                "execution_id": "test_execution",
                "workflow_id": "test_workflow"
            })
            
            # Verify webhook was called
            mock_session.return_value.__aenter__.return_value.post.assert_called_once()

class TestEndToEndWorkflow:
    """End-to-end workflow tests"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_lifecycle(self, mock_storage, test_config):
        """Test complete workflow lifecycle from suggestion to completion"""
        # Initialize all components
        engine = WorkflowAutomationEngine(mock_storage, test_config)
        await engine.initialize()
        
        integration = WorkflowhAIveMindIntegration(engine, mock_storage, test_config)
        await integration.initialize()
        
        validation_rollback = WorkflowValidationRollbackIntegration(mock_storage, test_config)
        
        # 1. Get workflow suggestions
        suggestions = await engine.suggest_workflows(
            context="security incident detected",
            intent="handle security threat"
        )
        
        assert len(suggestions) > 0
        security_workflow = next((s for s in suggestions if "security" in s.workflow_id), None)
        assert security_workflow is not None
        
        # 2. Validate workflow template
        template = engine.templates[security_workflow.workflow_id]
        validation_result = await validation_rollback.validator.validate_workflow_template(template)
        assert validation_result.valid
        
        # 3. Create and validate execution
        execution = WorkflowExecution(
            id="test_execution",
            template_id=security_workflow.workflow_id,
            name=template.name,
            trigger_type=TriggerType.MANUAL,
            parameters={"severity": "critical"}
        )
        
        execution_validation = await validation_rollback.validator.validate_workflow_execution(execution, template)
        assert execution_validation.valid
        
        # 4. Create rollback point
        rollback_point_id = await validation_rollback.rollback_manager.create_rollback_point(
            execution, "initial", {"state": "initial"}
        )
        assert rollback_point_id is not None
        
        # 5. Start workflow with hAIveMind integration
        await integration.on_workflow_start(execution)
        
        # 6. Simulate workflow completion
        execution.status = WorkflowStatus.COMPLETED
        execution.end_time = time.time()
        execution.completed_steps = ["step1", "step2"]
        
        await integration.on_workflow_complete(execution)
        
        # 7. Verify memories were stored
        memories = mock_storage.memories
        assert len(memories) > 0
        
        # Check for start memory
        start_memory = next((m for m in memories if 'workflow_execution_start' in m['metadata']), None)
        assert start_memory is not None
        
        # Check for completion memory
        completion_memory = next((m for m in memories if 'workflow_execution_complete' in m['metadata']), None)
        assert completion_memory is not None
        
        # Check for rollback point memory
        rollback_memory = next((m for m in memories if 'rollback_point' in m['metadata']), None)
        assert rollback_memory is not None
    
    @pytest.mark.asyncio
    async def test_workflow_failure_and_rollback(self, mock_storage, test_config):
        """Test workflow failure handling and rollback"""
        # Initialize components
        engine = WorkflowAutomationEngine(mock_storage, test_config)
        await engine.initialize()
        
        integration = WorkflowhAIveMindIntegration(engine, mock_storage, test_config)
        await integration.initialize()
        
        validation_rollback = WorkflowValidationRollbackIntegration(mock_storage, test_config)
        
        # Create execution
        template = engine.templates["incident_response"]
        execution = WorkflowExecution(
            id="test_execution",
            template_id="incident_response",
            name=template.name,
            trigger_type=TriggerType.MANUAL,
            start_time=time.time()
        )
        
        # Create rollback point
        await validation_rollback.rollback_manager.create_rollback_point(
            execution, "step1", {"state": "after_step1"}
        )
        
        # Simulate failure
        execution.status = WorkflowStatus.FAILED
        execution.error_message = "Test failure"
        execution.end_time = time.time()
        execution.current_step = "step2"
        
        # Handle failure with hAIveMind integration
        await integration.on_workflow_fail(execution)
        
        # Initiate rollback
        rollback_id = await validation_rollback.rollback_manager.initiate_rollback(execution)
        assert rollback_id is not None
        
        # Check rollback status
        rollback_status = await validation_rollback.rollback_manager.get_rollback_status(rollback_id)
        assert rollback_status is not None
        assert rollback_status['execution_id'] == execution.id
        
        # Verify failure memory was stored
        memories = mock_storage.memories
        failure_memory = next((m for m in memories if 'workflow_execution_failure' in m['metadata']), None)
        assert failure_memory is not None
        assert failure_memory['category'] == 'incidents'

# Performance and stress tests
class TestWorkflowPerformance:
    """Test workflow system performance"""
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_suggestions(self, workflow_engine):
        """Test concurrent workflow suggestions"""
        tasks = []
        for i in range(10):
            task = workflow_engine.suggest_workflows(
                context=f"test context {i}",
                intent=f"test intent {i}"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert all(isinstance(result, list) for result in results)
    
    @pytest.mark.asyncio
    async def test_memory_storage_performance(self, mock_storage):
        """Test memory storage performance"""
        start_time = time.time()
        
        # Store 100 memories
        tasks = []
        for i in range(100):
            task = mock_storage.store_memory(
                content=f"Test memory {i}",
                category="test",
                metadata={"test_id": i}
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time
        assert duration < 5.0  # 5 seconds max
        assert len(mock_storage.memories) == 100

# Integration with existing command system
class TestCommandSystemIntegration:
    """Test integration with existing hAIveMind command system"""
    
    @pytest.mark.asyncio
    async def test_command_sequence_detection(self, haivemind_integration):
        """Test detection of command sequences for workflow creation"""
        # Simulate command usage patterns
        sequences = [
            ["hv-status", "hv-broadcast", "hv-delegate", "remember"],  # Incident response pattern
            ["hv-query", "hv-delegate", "hv-status"],                  # Task delegation pattern
            ["hv-sync", "remember", "hv-broadcast"]                    # Maintenance pattern
        ]
        
        learned_patterns = await haivemind_integration.learn_from_command_sequences(sequences)
        
        # Should detect at least some workflow patterns
        assert isinstance(learned_patterns, list)
        
        # If patterns are detected, they should be well-formed
        for pattern in learned_patterns:
            assert 'name' in pattern
            assert 'steps' in pattern
            assert 'confidence' in pattern
            assert pattern['confidence'] > 0.5  # Should have reasonable confidence

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])