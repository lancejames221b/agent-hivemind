#!/usr/bin/env python3
"""
Comprehensive Test Suite for Playbook CRUD Operations
Story 5b Implementation - Full test coverage for enterprise CRUD features

This test suite covers:
- All CRUD operations (Create, Read, Update, Delete)
- Enterprise features (workflows, access control, notifications)
- hAIveMind integration and learning
- Error handling and edge cases
- Performance and scalability
- Security and compliance
"""

import asyncio
import json
import pytest
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Import the modules to test
from src.playbook_crud_manager import (
    PlaybookCRUDManager, ResourceType, AccessLevel, SearchFilter, 
    BulkOperation, ValidationLevel, OperationType, ResourceMetadata
)
from src.playbook_crud_mcp_tools import PlaybookCRUDMCPTools
from src.enterprise_workflows import (
    EnterpriseWorkflowManager, ApprovalType, WorkflowStatus, 
    NotificationType, UserRole
)


class MockMemoryStorage:
    """Mock memory storage for testing"""
    
    def __init__(self):
        self.memories = {}
        self.deleted_memories = {}
        self.memory_counter = 0
    
    async def store_memory(self, content, category, metadata=None, tags=None):
        self.memory_counter += 1
        memory_id = f"mem_{self.memory_counter}"
        
        self.memories[memory_id] = {
            'id': memory_id,
            'content': content,
            'category': category,
            'metadata': metadata or {},
            'tags': tags or [],
            'created_at': datetime.now().isoformat()
        }
        
        return memory_id
    
    async def search_memories(self, query, category=None, limit=100, offset=0):
        results = []
        
        for memory_id, memory in self.memories.items():
            if category and memory['category'] != category:
                continue
            
            # Simple query matching
            if query == "*" or query in memory['content'] or any(query in str(v) for v in memory['metadata'].values()):
                results.append(memory)
        
        # Sort by created_at descending
        results.sort(key=lambda m: m['created_at'], reverse=True)
        
        return {
            'memories': results[offset:offset + limit],
            'total': len(results)
        }
    
    async def delete_memory(self, memory_id, hard_delete=False):
        if memory_id in self.memories:
            if hard_delete:
                del self.memories[memory_id]
            else:
                self.deleted_memories[memory_id] = self.memories.pop(memory_id)
                self.deleted_memories[memory_id]['deleted_at'] = datetime.now().isoformat()


class MockHAIveMindClient:
    """Mock hAIveMind client for testing"""
    
    def __init__(self):
        self.stored_memories = []
    
    async def store_memory(self, content, category, metadata=None, tags=None):
        memory_id = f"haive_{uuid.uuid4().hex[:8]}"
        self.stored_memories.append({
            'id': memory_id,
            'content': content,
            'category': category,
            'metadata': metadata,
            'tags': tags
        })
        return memory_id


@pytest.fixture
def mock_memory_storage():
    """Fixture for mock memory storage"""
    return MockMemoryStorage()


@pytest.fixture
def mock_haivemind_client():
    """Fixture for mock hAIveMind client"""
    return MockHAIveMindClient()


@pytest.fixture
def crud_config():
    """Configuration for CRUD manager"""
    return {
        'allow_unsafe_shell': False,
        'validation_level': 'standard',
        'enable_approval_workflows': True,
        'enable_access_control': True,
        'enable_audit_logging': True,
        'templates_path': 'test_templates',
        'exports_path': 'test_exports',
        'imports_path': 'test_imports',
        'version_control': {
            'auto_version_on_change': True,
            'max_versions_per_playbook': 10,
            'version_retention_days': 365
        }
    }


@pytest.fixture
async def crud_manager(mock_memory_storage, mock_haivemind_client, crud_config):
    """Fixture for CRUD manager"""
    manager = PlaybookCRUDManager(
        memory_storage=mock_memory_storage,
        config=crud_config,
        haivemind_client=mock_haivemind_client
    )
    return manager


@pytest.fixture
async def mcp_tools(crud_manager):
    """Fixture for MCP tools"""
    return PlaybookCRUDMCPTools(crud_manager)


@pytest.fixture
def workflow_config():
    """Configuration for workflow manager"""
    return {
        'enable_approval_workflows': True,
        'default_approval_timeout_hours': 72,
        'auto_approve_low_risk': True,
        'enable_rbac': True,
        'default_user_role': 'contributor',
        'enable_notifications': True,
        'notification_channels': ['in_app', 'email']
    }


@pytest.fixture
async def workflow_manager(mock_memory_storage, workflow_config):
    """Fixture for workflow manager"""
    return EnterpriseWorkflowManager(
        memory_storage=mock_memory_storage,
        config=workflow_config
    )


class TestCRUDOperations:
    """Test suite for CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_playbook_success(self, crud_manager):
        """Test successful playbook creation"""
        playbook_content = {
            "name": "Test Playbook",
            "description": "A test playbook",
            "steps": [
                {
                    "id": "test_step",
                    "name": "Test Step",
                    "action": "noop",
                    "args": {"message": "Hello World"}
                }
            ]
        }
        
        result = await crud_manager.create_resource(
            resource_type=ResourceType.PLAYBOOK,
            name="Test Playbook",
            content=playbook_content,
            creator_id="test_user",
            description="A test playbook",
            category="testing",
            tags=["test", "example"]
        )
        
        assert result["resource_id"] is not None
        assert result["metadata"]["name"] == "Test Playbook"
        assert result["metadata"]["resource_type"] == ResourceType.PLAYBOOK
        assert result["metadata"]["creator_id"] == "test_user"
        assert result["validation_result"]["valid"] is True
    
    @pytest.mark.asyncio
    async def test_create_playbook_validation_failure(self, crud_manager):
        """Test playbook creation with validation failure"""
        invalid_content = {
            "name": "Invalid Playbook",
            # Missing required 'steps' field
        }
        
        with pytest.raises(ValueError, match="Validation failed"):
            await crud_manager.create_resource(
                resource_type=ResourceType.PLAYBOOK,
                name="Invalid Playbook",
                content=invalid_content,
                creator_id="test_user"
            )
    
    @pytest.mark.asyncio
    async def test_create_system_prompt_success(self, crud_manager):
        """Test successful system prompt creation"""
        prompt_content = {
            "template": "You are a helpful assistant for {{domain}} tasks. {{additional_context}}",
            "variables": {
                "domain": {"type": "string", "required": True},
                "additional_context": {"type": "string", "required": False}
            },
            "type": "system_prompt"
        }
        
        result = await crud_manager.create_resource(
            resource_type=ResourceType.SYSTEM_PROMPT,
            name="Test System Prompt",
            content=prompt_content,
            creator_id="test_user",
            description="A test system prompt",
            category="general"
        )
        
        assert result["resource_id"] is not None
        assert result["metadata"]["name"] == "Test System Prompt"
        assert result["metadata"]["resource_type"] == ResourceType.SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_create_from_template(self, crud_manager):
        """Test creating resource from template"""
        # Use built-in security audit template
        result = await crud_manager.create_from_template(
            template_id="security_audit",
            name="Security Audit - Production",
            creator_id="test_user",
            variables={
                "system_name": "production-server",
                "scan_level": "comprehensive"
            },
            description="Security audit for production server"
        )
        
        assert result["resource_id"] is not None
        assert result["metadata"]["name"] == "Security Audit - Production"
        assert result["metadata"]["template_id"] == "security_audit"
    
    @pytest.mark.asyncio
    async def test_search_resources(self, crud_manager):
        """Test resource search functionality"""
        # Create test resources first
        for i in range(5):
            await crud_manager.create_resource(
                resource_type=ResourceType.PLAYBOOK,
                name=f"Test Playbook {i}",
                content={
                    "name": f"Test Playbook {i}",
                    "steps": [{"id": "step1", "action": "noop"}]
                },
                creator_id="test_user",
                category="testing" if i % 2 == 0 else "production",
                tags=["test", f"batch_{i}"]
            )
        
        # Test basic search
        search_filter = SearchFilter(
            query="Test Playbook",
            resource_type=ResourceType.PLAYBOOK,
            limit=10
        )
        
        result = await crud_manager.search_resources(search_filter)
        
        assert len(result["resources"]) == 5
        assert result["total_count"] == 5
        
        # Test category filter
        search_filter.category = "testing"
        result = await crud_manager.search_resources(search_filter)
        
        assert len(result["resources"]) == 3  # 0, 2, 4
    
    @pytest.mark.asyncio
    async def test_get_resource(self, crud_manager):
        """Test getting a specific resource"""
        # Create a test resource
        create_result = await crud_manager.create_resource(
            resource_type=ResourceType.PLAYBOOK,
            name="Get Test Playbook",
            content={
                "name": "Get Test Playbook",
                "steps": [{"id": "step1", "action": "noop"}]
            },
            creator_id="test_user"
        )
        
        resource_id = create_result["resource_id"]
        
        # Get the resource
        result = await crud_manager.get_resource(
            resource_id=resource_id,
            include_content=True,
            include_versions=False
        )
        
        assert result is not None
        assert result["metadata"]["resource_id"] == resource_id
        assert result["metadata"]["name"] == "Get Test Playbook"
        assert "content" in result
    
    @pytest.mark.asyncio
    async def test_update_resource(self, crud_manager):
        """Test resource update functionality"""
        # Create a test resource
        create_result = await crud_manager.create_resource(
            resource_type=ResourceType.PLAYBOOK,
            name="Update Test Playbook",
            content={
                "name": "Update Test Playbook",
                "steps": [{"id": "step1", "action": "noop"}]
            },
            creator_id="test_user"
        )
        
        resource_id = create_result["resource_id"]
        
        # Update the resource
        updates = {
            "description": "Updated description",
            "tags": ["updated", "test"],
            "content": {
                "name": "Updated Test Playbook",
                "steps": [
                    {"id": "step1", "action": "noop"},
                    {"id": "step2", "action": "wait", "args": {"seconds": 1}}
                ]
            }
        }
        
        result = await crud_manager.update_resource(
            resource_id=resource_id,
            updates=updates,
            modifier_id="test_user",
            change_description="Added new step",
            create_version=True
        )
        
        assert result["resource_id"] == resource_id
        assert result["version_created"] is True
        assert result["metadata"]["description"] == "Updated description"
    
    @pytest.mark.asyncio
    async def test_delete_resource_soft(self, crud_manager):
        """Test soft delete functionality"""
        # Create a test resource
        create_result = await crud_manager.create_resource(
            resource_type=ResourceType.PLAYBOOK,
            name="Delete Test Playbook",
            content={
                "name": "Delete Test Playbook",
                "steps": [{"id": "step1", "action": "noop"}]
            },
            creator_id="test_user"
        )
        
        resource_id = create_result["resource_id"]
        
        # Soft delete the resource
        result = await crud_manager.delete_resource(
            resource_id=resource_id,
            deleter_id="test_user",
            hard_delete=False,
            deletion_reason="Testing soft delete"
        )
        
        assert result["status"] == "success"
        assert result["deletion_type"] == "soft"
        assert result["recoverable"] is True
        
        # Verify resource is marked as deleted
        resource = await crud_manager.get_resource(resource_id)
        assert resource is None  # Should not return deleted resources
    
    @pytest.mark.asyncio
    async def test_recover_deleted_resource(self, crud_manager):
        """Test recovery of soft-deleted resource"""
        # Create and soft delete a resource
        create_result = await crud_manager.create_resource(
            resource_type=ResourceType.PLAYBOOK,
            name="Recover Test Playbook",
            content={
                "name": "Recover Test Playbook",
                "steps": [{"id": "step1", "action": "noop"}]
            },
            creator_id="test_user"
        )
        
        resource_id = create_result["resource_id"]
        
        await crud_manager.delete_resource(
            resource_id=resource_id,
            deleter_id="test_user",
            hard_delete=False
        )
        
        # Recover the resource
        result = await crud_manager.recover_deleted_resource(
            resource_id=resource_id,
            recoverer_id="test_user",
            recovery_reason="Testing recovery"
        )
        
        assert result["status"] == "success"
        assert result["resource_id"] == resource_id
        
        # Verify resource is accessible again
        resource = await crud_manager.get_resource(resource_id)
        assert resource is not None
        assert resource["metadata"]["name"] == "Recover Test Playbook"
    
    @pytest.mark.asyncio
    async def test_bulk_create_resources(self, crud_manager):
        """Test bulk resource creation"""
        resources = []
        for i in range(3):
            resources.append({
                "resource_type": "playbook",
                "name": f"Bulk Test Playbook {i}",
                "content": {
                    "name": f"Bulk Test Playbook {i}",
                    "steps": [{"id": "step1", "action": "noop"}]
                },
                "description": f"Bulk created playbook {i}",
                "category": "bulk_test",
                "tags": ["bulk", "test"]
            })
        
        result = await crud_manager.bulk_create_resources(
            resources=resources,
            creator_id="test_user",
            batch_size=2,
            continue_on_error=True
        )
        
        assert result.total_items == 3
        assert result.successful_items == 3
        assert result.failed_items == 0
        assert len(result.resource_ids) == 3
    
    @pytest.mark.asyncio
    async def test_bulk_delete_resources(self, crud_manager):
        """Test bulk resource deletion"""
        # Create test resources
        resource_ids = []
        for i in range(3):
            create_result = await crud_manager.create_resource(
                resource_type=ResourceType.PLAYBOOK,
                name=f"Bulk Delete Test {i}",
                content={
                    "name": f"Bulk Delete Test {i}",
                    "steps": [{"id": "step1", "action": "noop"}]
                },
                creator_id="test_user"
            )
            resource_ids.append(create_result["resource_id"])
        
        # Bulk delete
        result = await crud_manager.bulk_delete_resources(
            resource_ids=resource_ids,
            deleter_id="test_user",
            hard_delete=False,
            deletion_reason="Bulk delete test",
            confirmation_required=False
        )
        
        assert result.total_items == 3
        assert result.successful_items == 3
        assert result.failed_items == 0


class TestMCPTools:
    """Test suite for MCP tools"""
    
    @pytest.mark.asyncio
    async def test_create_playbook_mcp(self, mcp_tools):
        """Test playbook creation via MCP tools"""
        result = await mcp_tools.create_playbook(
            name="MCP Test Playbook",
            content={
                "name": "MCP Test Playbook",
                "steps": [{"id": "step1", "action": "noop"}]
            },
            creator_id="test_user",
            description="Created via MCP tools",
            category="mcp_test",
            tags=["mcp", "test"]
        )
        
        assert result["success"] is True
        assert "Playbook 'MCP Test Playbook' created successfully" in result["message"]
        assert result["data"]["resource_id"] is not None
    
    @pytest.mark.asyncio
    async def test_create_system_prompt_mcp(self, mcp_tools):
        """Test system prompt creation via MCP tools"""
        result = await mcp_tools.create_system_prompt(
            name="MCP Test Prompt",
            template="You are a {{role}} assistant. {{context}}",
            variables={
                "role": {"type": "string", "required": True},
                "context": {"type": "string", "required": False}
            },
            creator_id="test_user",
            description="Created via MCP tools"
        )
        
        assert result["success"] is True
        assert "System prompt 'MCP Test Prompt' created successfully" in result["message"]
    
    @pytest.mark.asyncio
    async def test_search_resources_mcp(self, mcp_tools, crud_manager):
        """Test resource search via MCP tools"""
        # Create test resources first
        await crud_manager.create_resource(
            resource_type=ResourceType.PLAYBOOK,
            name="MCP Search Test",
            content={
                "name": "MCP Search Test",
                "steps": [{"id": "step1", "action": "noop"}]
            },
            creator_id="test_user",
            category="search_test"
        )
        
        result = await mcp_tools.search_resources(
            query="MCP Search",
            resource_type="playbook",
            category="search_test",
            limit=10
        )
        
        assert result["success"] is True
        assert len(result["data"]["resources"]) >= 1
    
    @pytest.mark.asyncio
    async def test_list_templates_mcp(self, mcp_tools):
        """Test template listing via MCP tools"""
        result = await mcp_tools.list_templates()
        
        assert result["success"] is True
        assert len(result["data"]["templates"]) >= 2  # Built-in templates
        
        # Check for security audit template
        templates = result["data"]["templates"]
        security_template = next(
            (t for t in templates if t["template_id"] == "security_audit"), 
            None
        )
        assert security_template is not None
        assert security_template["name"] == "Security Audit Playbook"


class TestEnterpriseWorkflows:
    """Test suite for enterprise workflows"""
    
    @pytest.mark.asyncio
    async def test_create_approval_request(self, workflow_manager):
        """Test approval request creation"""
        approval_request = await workflow_manager.create_approval_request(
            approval_type=ApprovalType.UPDATE_PRODUCTION,
            resource_id="test_resource_123",
            requester_id="test_user",
            operation_details={
                "operation": "update",
                "affects_production": True,
                "changes": ["content", "metadata"]
            },
            priority="high"
        )
        
        assert approval_request.request_id is not None
        assert approval_request.approval_type == ApprovalType.UPDATE_PRODUCTION
        assert approval_request.status == WorkflowStatus.PENDING
        assert approval_request.priority == "high"
        assert len(approval_request.required_approvers) > 0
    
    @pytest.mark.asyncio
    async def test_process_approval_approve(self, workflow_manager):
        """Test approval processing - approve"""
        # Create approval request
        approval_request = await workflow_manager.create_approval_request(
            approval_type=ApprovalType.DELETE_SHARED,
            resource_id="test_resource_456",
            requester_id="test_user",
            operation_details={"operation": "delete"}
        )
        
        request_id = approval_request.request_id
        approver_id = approval_request.required_approvers[0]
        
        # Process approval
        result = await workflow_manager.process_approval(
            request_id=request_id,
            approver_id=approver_id,
            decision="approve",
            comments="Looks good to proceed"
        )
        
        assert result["status"] == "approved"
        assert result["approvals_received"] == 1
    
    @pytest.mark.asyncio
    async def test_process_approval_reject(self, workflow_manager):
        """Test approval processing - reject"""
        # Create approval request
        approval_request = await workflow_manager.create_approval_request(
            approval_type=ApprovalType.SECURITY_CHANGE,
            resource_id="test_resource_789",
            requester_id="test_user",
            operation_details={"operation": "security_update"}
        )
        
        request_id = approval_request.request_id
        approver_id = approval_request.required_approvers[0]
        
        # Process rejection
        result = await workflow_manager.process_approval(
            request_id=request_id,
            approver_id=approver_id,
            decision="reject",
            comments="Security concerns need to be addressed"
        )
        
        assert result["status"] == "rejected"
        assert result["rejections"] == 1
    
    @pytest.mark.asyncio
    async def test_start_edit_session(self, workflow_manager):
        """Test collaborative editing session"""
        session = await workflow_manager.start_edit_session(
            resource_id="test_resource_edit",
            editor_id="test_editor",
            session_type="collaborative"
        )
        
        assert session.session_id is not None
        assert session.resource_id == "test_resource_edit"
        assert session.editor_id == "test_editor"
        assert session.status == "active"
        assert session.session_type == "collaborative"
    
    @pytest.mark.asyncio
    async def test_update_edit_session(self, workflow_manager):
        """Test editing session updates"""
        # Start session
        session = await workflow_manager.start_edit_session(
            resource_id="test_resource_edit2",
            editor_id="test_editor"
        )
        
        # Update session with changes
        changes = {
            "content": {
                "name": "Updated Resource",
                "description": "Updated via collaborative editing"
            }
        }
        
        result = await workflow_manager.update_edit_session(
            session_id=session.session_id,
            changes=changes,
            editor_id="test_editor"
        )
        
        assert result["session_id"] == session.session_id
        assert result["change_id"] is not None
        assert result["conflicts_detected"] is False
    
    @pytest.mark.asyncio
    async def test_send_notification(self, workflow_manager):
        """Test notification system"""
        notification = await workflow_manager.send_notification(
            recipient_id="test_user",
            notification_type=NotificationType.APPROVAL_REQUEST,
            title="Approval Required",
            message="Your approval is required for a critical operation",
            data={"request_id": "test_request_123"},
            priority="high"
        )
        
        assert notification.notification_id is not None
        assert notification.notification_type == NotificationType.APPROVAL_REQUEST
        assert notification.recipient_id == "test_user"
        assert notification.priority == "high"
    
    @pytest.mark.asyncio
    async def test_get_user_notifications(self, workflow_manager):
        """Test getting user notifications"""
        # Send a test notification
        await workflow_manager.send_notification(
            recipient_id="test_user_notif",
            notification_type=NotificationType.RESOURCE_CREATED,
            title="Resource Created",
            message="A new resource has been created",
            data={"resource_id": "test_123"}
        )
        
        # Get notifications
        notifications = await workflow_manager.get_user_notifications(
            user_id="test_user_notif",
            unread_only=True,
            limit=10
        )
        
        assert len(notifications) >= 1
        assert notifications[0]["recipient_id"] == "test_user_notif"
        assert notifications[0]["title"] == "Resource Created"


class TestErrorHandling:
    """Test suite for error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_create_resource_invalid_type(self, crud_manager):
        """Test creating resource with invalid type"""
        with pytest.raises(Exception):
            await crud_manager.create_resource(
                resource_type="invalid_type",  # Invalid type
                name="Test",
                content={},
                creator_id="test_user"
            )
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_resource(self, crud_manager):
        """Test getting non-existent resource"""
        result = await crud_manager.get_resource("nonexistent_id")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_resource(self, crud_manager):
        """Test updating non-existent resource"""
        with pytest.raises(ValueError, match="Resource .* not found"):
            await crud_manager.update_resource(
                resource_id="nonexistent_id",
                updates={"description": "test"},
                modifier_id="test_user"
            )
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_resource(self, crud_manager):
        """Test deleting non-existent resource"""
        with pytest.raises(ValueError, match="Resource .* not found"):
            await crud_manager.delete_resource(
                resource_id="nonexistent_id",
                deleter_id="test_user"
            )
    
    @pytest.mark.asyncio
    async def test_recover_nonexistent_resource(self, crud_manager):
        """Test recovering non-existent resource"""
        with pytest.raises(ValueError, match="Resource .* not found"):
            await crud_manager.recover_deleted_resource(
                resource_id="nonexistent_id",
                recoverer_id="test_user"
            )
    
    @pytest.mark.asyncio
    async def test_bulk_create_with_errors(self, crud_manager):
        """Test bulk create with some invalid resources"""
        resources = [
            {
                "resource_type": "playbook",
                "name": "Valid Playbook",
                "content": {
                    "name": "Valid Playbook",
                    "steps": [{"id": "step1", "action": "noop"}]
                }
            },
            {
                "resource_type": "playbook",
                "name": "Invalid Playbook",
                "content": {
                    "name": "Invalid Playbook"
                    # Missing required 'steps' field
                }
            }
        ]
        
        result = await crud_manager.bulk_create_resources(
            resources=resources,
            creator_id="test_user",
            continue_on_error=True
        )
        
        assert result.total_items == 2
        assert result.successful_items == 1
        assert result.failed_items == 1
        assert len(result.errors) == 1


class TestPerformanceAndScalability:
    """Test suite for performance and scalability"""
    
    @pytest.mark.asyncio
    async def test_large_bulk_create(self, crud_manager):
        """Test creating many resources at once"""
        # Create 50 resources
        resources = []
        for i in range(50):
            resources.append({
                "resource_type": "playbook",
                "name": f"Performance Test Playbook {i}",
                "content": {
                    "name": f"Performance Test Playbook {i}",
                    "steps": [{"id": "step1", "action": "noop"}]
                },
                "category": "performance_test"
            })
        
        import time
        start_time = time.time()
        
        result = await crud_manager.bulk_create_resources(
            resources=resources,
            creator_id="test_user",
            batch_size=10,
            continue_on_error=True
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert result.total_items == 50
        assert result.successful_items == 50
        assert duration < 30  # Should complete within 30 seconds
        
        print(f"Created 50 resources in {duration:.2f} seconds")
    
    @pytest.mark.asyncio
    async def test_search_performance(self, crud_manager):
        """Test search performance with many resources"""
        # Create test resources (if not already created)
        for i in range(20):
            await crud_manager.create_resource(
                resource_type=ResourceType.PLAYBOOK,
                name=f"Search Performance Test {i}",
                content={
                    "name": f"Search Performance Test {i}",
                    "steps": [{"id": "step1", "action": "noop"}]
                },
                creator_id="test_user",
                category="search_perf_test"
            )
        
        import time
        start_time = time.time()
        
        # Perform search
        search_filter = SearchFilter(
            query="Search Performance",
            category="search_perf_test",
            limit=100
        )
        
        result = await crud_manager.search_resources(search_filter)
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(result["resources"]) >= 20
        assert duration < 5  # Should complete within 5 seconds
        
        print(f"Searched {len(result['resources'])} resources in {duration:.2f} seconds")


class TestHAIveMindIntegration:
    """Test suite for hAIveMind integration"""
    
    @pytest.mark.asyncio
    async def test_haivemind_memory_storage(self, crud_manager, mock_haivemind_client):
        """Test that operations are stored in hAIveMind"""
        # Create a resource
        result = await crud_manager.create_resource(
            resource_type=ResourceType.PLAYBOOK,
            name="hAIveMind Test Playbook",
            content={
                "name": "hAIveMind Test Playbook",
                "steps": [{"id": "step1", "action": "noop"}]
            },
            creator_id="test_user"
        )
        
        # Check that memory was stored in hAIveMind
        assert len(mock_haivemind_client.stored_memories) > 0
        
        # Find the creation memory
        creation_memory = next(
            (m for m in mock_haivemind_client.stored_memories 
             if "Created playbook" in m['content']),
            None
        )
        
        assert creation_memory is not None
        assert creation_memory['category'] == "crud_operations"
        assert creation_memory['metadata']['operation'] == "create"
        assert creation_memory['metadata']['resource_id'] == result['resource_id']
    
    @pytest.mark.asyncio
    async def test_haivemind_learning_insights(self, mcp_tools, crud_manager, mock_haivemind_client):
        """Test hAIveMind insights generation"""
        # Create a test resource
        create_result = await crud_manager.create_resource(
            resource_type=ResourceType.PLAYBOOK,
            name="Insights Test Playbook",
            content={
                "name": "Insights Test Playbook",
                "steps": [{"id": "step1", "action": "noop"}]
            },
            creator_id="test_user"
        )
        
        resource_id = create_result["resource_id"]
        
        # Get hAIveMind insights
        result = await mcp_tools.get_haivemind_insights(resource_id)
        
        assert result["success"] is True
        assert result["data"]["resource_id"] == resource_id
        assert "usage_patterns" in result["data"]
        assert "performance_trends" in result["data"]
        assert "recommendations" in result["data"]


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])