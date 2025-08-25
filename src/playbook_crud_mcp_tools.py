#!/usr/bin/env python3
"""
MCP Tools for Playbook CRUD Operations with hAIveMind Integration
Story 5b Implementation - Enterprise-grade CRUD operations exposed as MCP tools

This module provides MCP tools for comprehensive playbook and system prompt management:
- Full CRUD operations with enterprise features
- hAIveMind awareness and learning integration
- Template gallery and visual builder support
- Collaborative editing and version control
- Advanced search and analytics
- Bulk operations and import/export
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from playbook_crud_manager import (
    PlaybookCRUDManager, ResourceType, AccessLevel, SearchFilter, 
    BulkOperation, ValidationLevel, OperationType
)

logger = logging.getLogger(__name__)


class PlaybookCRUDMCPTools:
    """MCP tools for comprehensive playbook CRUD operations"""
    
    def __init__(self, crud_manager: PlaybookCRUDManager):
        self.crud_manager = crud_manager
        logger.info("🔧 PlaybookCRUDMCPTools initialized")

    # ==================== CREATE OPERATIONS ====================
    
    async def create_playbook(self,
                            name: str,
                            content: Dict[str, Any],
                            creator_id: str,
                            description: str = "",
                            category: str = "general",
                            tags: Optional[List[str]] = None,
                            template_id: Optional[str] = None,
                            validation_level: str = "standard") -> Dict[str, Any]:
        """
        Create a new playbook with comprehensive validation
        
        Args:
            name: Playbook name
            content: Playbook specification (YAML/JSON format)
            creator_id: ID of the creator
            description: Playbook description
            category: Playbook category
            tags: List of tags
            template_id: Template used (if any)
            validation_level: Validation level (basic, standard, strict, enterprise)
            
        Returns:
            Created playbook information
        """
        try:
            validation_enum = ValidationLevel(validation_level)
            
            result = await self.crud_manager.create_resource(
                resource_type=ResourceType.PLAYBOOK,
                name=name,
                content=content,
                creator_id=creator_id,
                description=description,
                category=category,
                tags=tags or [],
                template_id=template_id,
                validation_level=validation_enum
            )
            
            return {
                "success": True,
                "message": f"Playbook '{name}' created successfully",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Failed to create playbook: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to create playbook '{name}'"
            }

    async def create_system_prompt(self,
                                 name: str,
                                 template: str,
                                 variables: Dict[str, Any],
                                 creator_id: str,
                                 description: str = "",
                                 category: str = "general",
                                 tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a new system prompt template
        
        Args:
            name: Prompt name
            template: Prompt template with variable placeholders
            variables: Variable schema definition
            creator_id: ID of the creator
            description: Prompt description
            category: Prompt category
            tags: List of tags
            
        Returns:
            Created prompt information
        """
        try:
            content = {
                "template": template,
                "variables": variables,
                "type": "system_prompt"
            }
            
            result = await self.crud_manager.create_resource(
                resource_type=ResourceType.SYSTEM_PROMPT,
                name=name,
                content=content,
                creator_id=creator_id,
                description=description,
                category=category,
                tags=tags or []
            )
            
            return {
                "success": True,
                "message": f"System prompt '{name}' created successfully",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Failed to create system prompt: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to create system prompt '{name}'"
            }

    async def create_from_template(self,
                                 template_id: str,
                                 name: str,
                                 creator_id: str,
                                 variables: Optional[Dict[str, Any]] = None,
                                 description: str = "",
                                 category: str = "") -> Dict[str, Any]:
        """
        Create a resource from a template with variable substitution
        
        Args:
            template_id: Template identifier
            name: New resource name
            creator_id: ID of the creator
            variables: Variables to substitute in template
            description: Resource description
            category: Resource category
            
        Returns:
            Created resource information
        """
        try:
            result = await self.crud_manager.create_from_template(
                template_id=template_id,
                name=name,
                creator_id=creator_id,
                variables=variables or {},
                description=description,
                category=category
            )
            
            return {
                "success": True,
                "message": f"Resource '{name}' created from template successfully",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Failed to create from template: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to create resource from template '{template_id}'"
            }

    async def bulk_create_resources(self,
                                  resources: List[Dict[str, Any]],
                                  creator_id: str,
                                  batch_size: int = 10,
                                  continue_on_error: bool = False) -> Dict[str, Any]:
        """
        Create multiple resources in bulk
        
        Args:
            resources: List of resource definitions
            creator_id: ID of the creator
            batch_size: Number of resources to process per batch
            continue_on_error: Whether to continue if some resources fail
            
        Returns:
            Bulk operation results
        """
        try:
            result = await self.crud_manager.bulk_create_resources(
                resources=resources,
                creator_id=creator_id,
                batch_size=batch_size,
                continue_on_error=continue_on_error
            )
            
            return {
                "success": True,
                "message": f"Bulk create completed: {result.successful_items}/{result.total_items} successful",
                "data": {
                    "total_items": result.total_items,
                    "successful_items": result.successful_items,
                    "failed_items": result.failed_items,
                    "resource_ids": result.resource_ids,
                    "errors": result.errors
                }
            }
            
        except Exception as e:
            logger.error(f"Bulk create failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Bulk create operation failed"
            }

    async def import_resources(self,
                             import_path: str,
                             creator_id: str,
                             format_type: str = "auto",
                             validation_level: str = "standard") -> Dict[str, Any]:
        """
        Import resources from files
        
        Args:
            import_path: Path to import file
            creator_id: ID of the creator
            format_type: File format (auto, json, yaml, csv)
            validation_level: Validation level to apply
            
        Returns:
            Import operation results
        """
        try:
            validation_enum = ValidationLevel(validation_level)
            
            result = await self.crud_manager.import_resources(
                import_path=import_path,
                creator_id=creator_id,
                format_type=format_type,
                validation_level=validation_enum
            )
            
            return {
                "success": True,
                "message": f"Import completed: {result.successful_items}/{result.total_items} resources imported",
                "data": {
                    "total_items": result.total_items,
                    "successful_items": result.successful_items,
                    "failed_items": result.failed_items,
                    "resource_ids": result.resource_ids,
                    "errors": result.errors
                }
            }
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to import from '{import_path}'"
            }

    # ==================== READ OPERATIONS ====================
    
    async def search_resources(self,
                             query: Optional[str] = None,
                             resource_type: Optional[str] = None,
                             category: Optional[str] = None,
                             tags: Optional[List[str]] = None,
                             owner_id: Optional[str] = None,
                             semantic_search: bool = False,
                             similarity_threshold: float = 0.7,
                             sort_by: str = "modified_at",
                             sort_order: str = "desc",
                             limit: int = 100,
                             offset: int = 0) -> Dict[str, Any]:
        """
        Advanced search for resources with filtering and sorting
        
        Args:
            query: Search query text
            resource_type: Filter by resource type
            category: Filter by category
            tags: Filter by tags
            owner_id: Filter by owner
            semantic_search: Use semantic search
            similarity_threshold: Similarity threshold for semantic search
            sort_by: Sort field
            sort_order: Sort order (asc, desc)
            limit: Maximum results to return
            offset: Results offset for pagination
            
        Returns:
            Search results with metadata
        """
        try:
            search_filter = SearchFilter(
                query=query,
                resource_type=ResourceType(resource_type) if resource_type else None,
                category=category,
                tags=tags or [],
                owner_id=owner_id,
                semantic_search=semantic_search,
                similarity_threshold=similarity_threshold,
                sort_by=sort_by,
                sort_order=sort_order,
                limit=limit,
                offset=offset
            )
            
            result = await self.crud_manager.search_resources(search_filter)
            
            return {
                "success": True,
                "message": f"Found {len(result['resources'])} resources",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Search operation failed"
            }

    async def get_resource(self,
                         resource_id: str,
                         include_content: bool = True,
                         include_versions: bool = False) -> Dict[str, Any]:
        """
        Get a specific resource by ID
        
        Args:
            resource_id: Resource identifier
            include_content: Whether to include resource content
            include_versions: Whether to include version history
            
        Returns:
            Resource information
        """
        try:
            result = await self.crud_manager.get_resource(
                resource_id=resource_id,
                include_content=include_content,
                include_versions=include_versions
            )
            
            if result:
                return {
                    "success": True,
                    "message": f"Resource '{resource_id}' retrieved successfully",
                    "data": result
                }
            else:
                return {
                    "success": False,
                    "error": "Resource not found",
                    "message": f"Resource '{resource_id}' not found"
                }
                
        except Exception as e:
            logger.error(f"Failed to get resource: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to retrieve resource '{resource_id}'"
            }

    async def get_resource_analytics(self, resource_id: str) -> Dict[str, Any]:
        """
        Get comprehensive analytics for a resource
        
        Args:
            resource_id: Resource identifier
            
        Returns:
            Resource analytics and performance metrics
        """
        try:
            result = await self.crud_manager.get_resource_analytics(resource_id)
            
            return {
                "success": True,
                "message": f"Analytics retrieved for resource '{resource_id}'",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to retrieve analytics for resource '{resource_id}'"
            }

    async def compare_resources(self,
                              resource_id_1: str,
                              resource_id_2: str) -> Dict[str, Any]:
        """
        Compare two resources and show differences
        
        Args:
            resource_id_1: First resource ID
            resource_id_2: Second resource ID
            
        Returns:
            Detailed comparison results
        """
        try:
            result = await self.crud_manager.compare_resources(resource_id_1, resource_id_2)
            
            return {
                "success": True,
                "message": f"Comparison completed between '{resource_id_1}' and '{resource_id_2}'",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Failed to compare resources: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to compare resources '{resource_id_1}' and '{resource_id_2}'"
            }

    async def list_templates(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        List available templates for quick-start
        
        Args:
            category: Filter by category
            
        Returns:
            List of available templates
        """
        try:
            templates = self.crud_manager.builtin_templates
            
            if category:
                templates = [t for t in templates if t.category == category]
            
            template_data = []
            for template in templates:
                template_data.append({
                    "template_id": template.template_id,
                    "name": template.name,
                    "description": template.description,
                    "category": template.category,
                    "resource_type": template.resource_type.value,
                    "tags": template.tags,
                    "complexity_level": template.complexity_level,
                    "estimated_time": template.estimated_time,
                    "variable_schema": template.variable_schema
                })
            
            return {
                "success": True,
                "message": f"Found {len(template_data)} templates",
                "data": {
                    "templates": template_data,
                    "total_count": len(template_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to list templates"
            }

    # ==================== UPDATE OPERATIONS ====================
    
    async def update_resource(self,
                            resource_id: str,
                            updates: Dict[str, Any],
                            modifier_id: str,
                            change_description: str = "",
                            create_version: bool = True,
                            validation_level: str = "standard") -> Dict[str, Any]:
        """
        Update a resource with version control
        
        Args:
            resource_id: Resource to update
            updates: Dictionary of fields to update
            modifier_id: ID of the user making changes
            change_description: Description of changes
            create_version: Whether to create a new version
            validation_level: Validation level to apply
            
        Returns:
            Update operation results
        """
        try:
            validation_enum = ValidationLevel(validation_level)
            
            result = await self.crud_manager.update_resource(
                resource_id=resource_id,
                updates=updates,
                modifier_id=modifier_id,
                change_description=change_description,
                create_version=create_version,
                validation_level=validation_enum
            )
            
            return {
                "success": True,
                "message": f"Resource '{resource_id}' updated successfully",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Failed to update resource: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to update resource '{resource_id}'"
            }

    async def bulk_update_resources(self,
                                  updates: List[Dict[str, Any]],
                                  modifier_id: str,
                                  batch_size: int = 10,
                                  continue_on_error: bool = False) -> Dict[str, Any]:
        """
        Update multiple resources in bulk
        
        Args:
            updates: List of update operations
            modifier_id: ID of the user making changes
            batch_size: Number of resources to process per batch
            continue_on_error: Whether to continue if some updates fail
            
        Returns:
            Bulk update operation results
        """
        try:
            result = await self.crud_manager.bulk_update_resources(
                updates=updates,
                modifier_id=modifier_id,
                batch_size=batch_size,
                continue_on_error=continue_on_error
            )
            
            return {
                "success": True,
                "message": f"Bulk update completed: {result.successful_items}/{result.total_items} successful",
                "data": {
                    "total_items": result.total_items,
                    "successful_items": result.successful_items,
                    "failed_items": result.failed_items,
                    "errors": result.errors
                }
            }
            
        except Exception as e:
            logger.error(f"Bulk update failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Bulk update operation failed"
            }

    async def collaborative_edit_resource(self,
                                        resource_id: str,
                                        editor_id: str,
                                        edit_session_id: str,
                                        changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle collaborative editing with conflict resolution
        
        Args:
            resource_id: Resource to edit
            editor_id: ID of the editor
            edit_session_id: Unique edit session identifier
            changes: Changes to apply
            
        Returns:
            Collaborative edit results
        """
        try:
            result = await self.crud_manager.collaborative_edit_resource(
                resource_id=resource_id,
                editor_id=editor_id,
                edit_session_id=edit_session_id,
                changes=changes
            )
            
            return {
                "success": True,
                "message": f"Collaborative edit completed for resource '{resource_id}'",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Collaborative edit failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to perform collaborative edit on resource '{resource_id}'"
            }

    # ==================== DELETE OPERATIONS ====================
    
    async def delete_resource(self,
                            resource_id: str,
                            deleter_id: str,
                            hard_delete: bool = False,
                            deletion_reason: str = "",
                            cascade_delete: bool = False) -> Dict[str, Any]:
        """
        Delete a resource with soft/hard delete options
        
        Args:
            resource_id: Resource to delete
            deleter_id: ID of user performing deletion
            hard_delete: Whether to permanently delete
            deletion_reason: Reason for deletion
            cascade_delete: Whether to delete dependent resources
            
        Returns:
            Deletion operation results
        """
        try:
            result = await self.crud_manager.delete_resource(
                resource_id=resource_id,
                deleter_id=deleter_id,
                hard_delete=hard_delete,
                deletion_reason=deletion_reason,
                cascade_delete=cascade_delete
            )
            
            return {
                "success": True,
                "message": f"Resource '{resource_id}' {'permanently' if hard_delete else 'soft'} deleted",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Failed to delete resource: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to delete resource '{resource_id}'"
            }

    async def recover_deleted_resource(self,
                                     resource_id: str,
                                     recoverer_id: str,
                                     recovery_reason: str = "") -> Dict[str, Any]:
        """
        Recover a soft-deleted resource
        
        Args:
            resource_id: Resource to recover
            recoverer_id: ID of user performing recovery
            recovery_reason: Reason for recovery
            
        Returns:
            Recovery operation results
        """
        try:
            result = await self.crud_manager.recover_deleted_resource(
                resource_id=resource_id,
                recoverer_id=recoverer_id,
                recovery_reason=recovery_reason
            )
            
            return {
                "success": True,
                "message": f"Resource '{resource_id}' recovered successfully",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Failed to recover resource: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to recover resource '{resource_id}'"
            }

    async def bulk_delete_resources(self,
                                  resource_ids: List[str],
                                  deleter_id: str,
                                  hard_delete: bool = False,
                                  deletion_reason: str = "",
                                  confirmation_required: bool = True) -> Dict[str, Any]:
        """
        Delete multiple resources in bulk
        
        Args:
            resource_ids: List of resource IDs to delete
            deleter_id: ID of user performing deletion
            hard_delete: Whether to permanently delete
            deletion_reason: Reason for deletion
            confirmation_required: Whether confirmation is required for large batches
            
        Returns:
            Bulk deletion operation results
        """
        try:
            result = await self.crud_manager.bulk_delete_resources(
                resource_ids=resource_ids,
                deleter_id=deleter_id,
                hard_delete=hard_delete,
                deletion_reason=deletion_reason,
                confirmation_required=confirmation_required
            )
            
            return {
                "success": True,
                "message": f"Bulk delete completed: {result.successful_items}/{result.total_items} successful",
                "data": {
                    "total_items": result.total_items,
                    "successful_items": result.successful_items,
                    "failed_items": result.failed_items,
                    "errors": result.errors
                }
            }
            
        except Exception as e:
            logger.error(f"Bulk delete failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Bulk delete operation failed"
            }

    async def cleanup_expired_deletions(self, retention_days: int = 30) -> Dict[str, Any]:
        """
        Clean up expired soft deletions
        
        Args:
            retention_days: Number of days to retain soft-deleted resources
            
        Returns:
            Cleanup operation results
        """
        try:
            result = await self.crud_manager.cleanup_expired_deletions(retention_days)
            
            return {
                "success": True,
                "message": f"Cleanup completed: {result['cleaned_up']} resources permanently deleted",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Cleanup operation failed"
            }

    # ==================== ENTERPRISE FEATURES ====================
    
    async def get_resource_permissions(self, resource_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get user permissions for a resource
        
        Args:
            resource_id: Resource identifier
            user_id: User identifier
            
        Returns:
            User permissions for the resource
        """
        try:
            metadata = await self.crud_manager._get_resource_metadata(resource_id)
            if not metadata:
                return {
                    "success": False,
                    "error": "Resource not found",
                    "message": f"Resource '{resource_id}' not found"
                }
            
            permissions = {
                "can_read": True,  # Basic read access
                "can_write": await self.crud_manager._check_update_permission(user_id, metadata),
                "can_delete": await self.crud_manager._check_delete_permission(user_id, metadata),
                "can_admin": metadata.access_level == AccessLevel.ADMIN or metadata.owner_id == user_id,
                "is_owner": metadata.owner_id == user_id,
                "access_level": metadata.access_level.value
            }
            
            return {
                "success": True,
                "message": f"Permissions retrieved for resource '{resource_id}'",
                "data": permissions
            }
            
        except Exception as e:
            logger.error(f"Failed to get permissions: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to retrieve permissions for resource '{resource_id}'"
            }

    async def get_audit_trail(self,
                            resource_id: Optional[str] = None,
                            user_id: Optional[str] = None,
                            event_type: Optional[str] = None,
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None,
                            limit: int = 100) -> Dict[str, Any]:
        """
        Get audit trail for resources and operations
        
        Args:
            resource_id: Filter by resource ID
            user_id: Filter by user ID
            event_type: Filter by event type
            start_date: Start date filter (ISO format)
            end_date: End date filter (ISO format)
            limit: Maximum results to return
            
        Returns:
            Audit trail entries
        """
        try:
            # Build search query for audit logs
            query_parts = []
            
            if resource_id:
                query_parts.append(f"resource_id:{resource_id}")
            if user_id:
                query_parts.append(f"user_id:{user_id}")
            if event_type:
                query_parts.append(f"event_type:{event_type}")
            if start_date:
                query_parts.append(f"timestamp:>={start_date}")
            if end_date:
                query_parts.append(f"timestamp:<={end_date}")
            
            query = " AND ".join(query_parts) if query_parts else "*"
            
            # Search audit logs
            search_results = await self.crud_manager.memory_storage.search_memories(
                query=query,
                category="audit_log",
                limit=limit
            )
            
            audit_entries = []
            for memory in search_results.get('memories', []):
                try:
                    audit_data = json.loads(memory.get('content', '{}'))
                    audit_entries.append(audit_data)
                except Exception as e:
                    logger.warning(f"Failed to parse audit entry: {e}")
            
            return {
                "success": True,
                "message": f"Found {len(audit_entries)} audit entries",
                "data": {
                    "audit_entries": audit_entries,
                    "total_count": len(audit_entries)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get audit trail: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve audit trail"
            }

    async def get_usage_statistics(self,
                                 resource_id: Optional[str] = None,
                                 time_period: str = "30d") -> Dict[str, Any]:
        """
        Get usage statistics for resources
        
        Args:
            resource_id: Specific resource ID (optional)
            time_period: Time period for statistics (7d, 30d, 90d, 1y)
            
        Returns:
            Usage statistics and trends
        """
        try:
            # Calculate date range based on time period
            from datetime import datetime, timedelta
            
            period_map = {
                "7d": 7,
                "30d": 30,
                "90d": 90,
                "1y": 365
            }
            
            days = period_map.get(time_period, 30)
            start_date = datetime.now() - timedelta(days=days)
            
            # Build query
            query_parts = [f"timestamp:>={start_date.isoformat()}"]
            if resource_id:
                query_parts.append(f"resource_id:{resource_id}")
            
            query = " AND ".join(query_parts)
            
            # Search for usage events
            search_results = await self.crud_manager.memory_storage.search_memories(
                query=query,
                category="crud_operations",
                limit=1000
            )
            
            # Analyze usage patterns
            operations = {}
            resources = {}
            daily_usage = {}
            
            for memory in search_results.get('memories', []):
                try:
                    event_data = json.loads(memory.get('content', '{}'))
                    metadata = memory.get('metadata', {})
                    
                    operation = metadata.get('operation', 'unknown')
                    res_id = metadata.get('resource_id', 'unknown')
                    timestamp = metadata.get('timestamp', '')
                    
                    # Count operations
                    operations[operation] = operations.get(operation, 0) + 1
                    
                    # Count resource usage
                    resources[res_id] = resources.get(res_id, 0) + 1
                    
                    # Daily usage
                    if timestamp:
                        date_key = timestamp[:10]  # YYYY-MM-DD
                        daily_usage[date_key] = daily_usage.get(date_key, 0) + 1
                        
                except Exception as e:
                    logger.warning(f"Failed to parse usage event: {e}")
            
            statistics = {
                "time_period": time_period,
                "total_operations": sum(operations.values()),
                "operations_breakdown": operations,
                "top_resources": dict(sorted(resources.items(), key=lambda x: x[1], reverse=True)[:10]),
                "daily_usage": daily_usage,
                "unique_resources": len(resources)
            }
            
            return {
                "success": True,
                "message": f"Usage statistics retrieved for {time_period}",
                "data": statistics
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage statistics: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve usage statistics"
            }

    # ==================== HAIVEMIND INTEGRATION ====================
    
    async def get_haivemind_insights(self, resource_id: str) -> Dict[str, Any]:
        """
        Get hAIveMind insights and recommendations for a resource
        
        Args:
            resource_id: Resource identifier
            
        Returns:
            hAIveMind insights and learning data
        """
        try:
            metadata = await self.crud_manager._get_resource_metadata(resource_id)
            if not metadata:
                return {
                    "success": False,
                    "error": "Resource not found",
                    "message": f"Resource '{resource_id}' not found"
                }
            
            insights = {
                "resource_id": resource_id,
                "haivemind_memory_ids": metadata.haivemind_memory_ids,
                "learning_insights": metadata.learning_insights,
                "usage_patterns": await self._analyze_usage_patterns(resource_id),
                "performance_trends": await self._analyze_performance_trends(resource_id),
                "recommendations": await self._generate_recommendations(resource_id)
            }
            
            return {
                "success": True,
                "message": f"hAIveMind insights retrieved for resource '{resource_id}'",
                "data": insights
            }
            
        except Exception as e:
            logger.error(f"Failed to get hAIveMind insights: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to retrieve hAIveMind insights for resource '{resource_id}'"
            }

    async def _analyze_usage_patterns(self, resource_id: str) -> Dict[str, Any]:
        """Analyze usage patterns for a resource"""
        try:
            # Search for usage events
            search_results = await self.crud_manager.memory_storage.search_memories(
                query=f"resource_id:{resource_id}",
                category="crud_operations",
                limit=100
            )
            
            patterns = {
                "total_operations": len(search_results.get('memories', [])),
                "operation_types": {},
                "time_distribution": {},
                "user_activity": {}
            }
            
            for memory in search_results.get('memories', []):
                try:
                    metadata = memory.get('metadata', {})
                    operation = metadata.get('operation', 'unknown')
                    user = metadata.get('user_id', 'unknown')
                    timestamp = metadata.get('timestamp', '')
                    
                    # Count operation types
                    patterns["operation_types"][operation] = patterns["operation_types"].get(operation, 0) + 1
                    
                    # Count user activity
                    patterns["user_activity"][user] = patterns["user_activity"].get(user, 0) + 1
                    
                    # Time distribution (by hour)
                    if timestamp:
                        hour = timestamp[11:13]  # Extract hour
                        patterns["time_distribution"][hour] = patterns["time_distribution"].get(hour, 0) + 1
                        
                except Exception as e:
                    logger.warning(f"Failed to analyze usage pattern: {e}")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to analyze usage patterns: {e}")
            return {}

    async def _analyze_performance_trends(self, resource_id: str) -> Dict[str, Any]:
        """Analyze performance trends for a resource"""
        try:
            metadata = await self.crud_manager._get_resource_metadata(resource_id)
            if not metadata:
                return {}
            
            trends = {
                "current_success_rate": metadata.success_rate,
                "current_avg_duration": metadata.average_duration,
                "usage_count": metadata.usage_count,
                "version_count": metadata.version_count,
                "last_accessed": metadata.last_accessed.isoformat() if metadata.last_accessed else None
            }
            
            # Get version-specific trends for playbooks
            if metadata.resource_type == ResourceType.PLAYBOOK:
                version_stats = await self.crud_manager.version_control.get_playbook_statistics(resource_id)
                if version_stats and "error" not in version_stats:
                    trends["version_analytics"] = version_stats
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to analyze performance trends: {e}")
            return {}

    async def _generate_recommendations(self, resource_id: str) -> List[str]:
        """Generate AI-powered recommendations for a resource"""
        try:
            metadata = await self.crud_manager._get_resource_metadata(resource_id)
            if not metadata:
                return []
            
            recommendations = []
            
            # Performance-based recommendations
            if metadata.success_rate < 0.8:
                recommendations.append("Consider reviewing and improving this resource - success rate is below 80%")
            
            if metadata.average_duration > 300:  # 5 minutes
                recommendations.append("This resource takes longer than average to execute - consider optimization")
            
            if metadata.usage_count == 0:
                recommendations.append("This resource hasn't been used yet - consider promoting it or reviewing its relevance")
            
            # Version-based recommendations
            if metadata.version_count > 10:
                recommendations.append("This resource has many versions - consider consolidating or archiving old versions")
            
            # Age-based recommendations
            if metadata.modified_at and (datetime.now() - metadata.modified_at).days > 90:
                recommendations.append("This resource hasn't been updated in 90+ days - consider reviewing for relevance")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return []

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of all available MCP tools"""
        return [
            {
                "name": "create_playbook",
                "description": "Create a new playbook with comprehensive validation",
                "parameters": {
                    "name": {"type": "string", "required": True},
                    "content": {"type": "object", "required": True},
                    "creator_id": {"type": "string", "required": True},
                    "description": {"type": "string"},
                    "category": {"type": "string"},
                    "tags": {"type": "array"},
                    "template_id": {"type": "string"},
                    "validation_level": {"type": "string", "enum": ["basic", "standard", "strict", "enterprise"]}
                }
            },
            {
                "name": "create_system_prompt",
                "description": "Create a new system prompt template",
                "parameters": {
                    "name": {"type": "string", "required": True},
                    "template": {"type": "string", "required": True},
                    "variables": {"type": "object", "required": True},
                    "creator_id": {"type": "string", "required": True},
                    "description": {"type": "string"},
                    "category": {"type": "string"},
                    "tags": {"type": "array"}
                }
            },
            {
                "name": "search_resources",
                "description": "Advanced search for resources with filtering and sorting",
                "parameters": {
                    "query": {"type": "string"},
                    "resource_type": {"type": "string"},
                    "category": {"type": "string"},
                    "tags": {"type": "array"},
                    "semantic_search": {"type": "boolean"},
                    "limit": {"type": "integer"},
                    "offset": {"type": "integer"}
                }
            },
            {
                "name": "get_resource",
                "description": "Get a specific resource by ID",
                "parameters": {
                    "resource_id": {"type": "string", "required": True},
                    "include_content": {"type": "boolean"},
                    "include_versions": {"type": "boolean"}
                }
            },
            {
                "name": "update_resource",
                "description": "Update a resource with version control",
                "parameters": {
                    "resource_id": {"type": "string", "required": True},
                    "updates": {"type": "object", "required": True},
                    "modifier_id": {"type": "string", "required": True},
                    "change_description": {"type": "string"},
                    "create_version": {"type": "boolean"},
                    "validation_level": {"type": "string"}
                }
            },
            {
                "name": "delete_resource",
                "description": "Delete a resource with soft/hard delete options",
                "parameters": {
                    "resource_id": {"type": "string", "required": True},
                    "deleter_id": {"type": "string", "required": True},
                    "hard_delete": {"type": "boolean"},
                    "deletion_reason": {"type": "string"},
                    "cascade_delete": {"type": "boolean"}
                }
            },
            {
                "name": "get_haivemind_insights",
                "description": "Get hAIveMind insights and recommendations for a resource",
                "parameters": {
                    "resource_id": {"type": "string", "required": True}
                }
            }
        ]

logger.info("🔧 PlaybookCRUDMCPTools implementation completed")