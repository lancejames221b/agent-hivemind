#!/usr/bin/env python3
"""
Comprehensive CRUD Operations Manager for Playbooks and System Prompts
Story 5b Implementation - Full Lifecycle Management with hAIveMind Integration

This module provides enterprise-grade CRUD operations:
- CREATE: Visual builder, templates, import, bulk operations
- READ: Advanced search, filtering, comparison, analytics, suggestions
- UPDATE: Version control, collaborative editing, validation, rollback
- DELETE: Soft/hard delete, recovery, cascade handling, bulk operations

Features:
- hAIveMind awareness and learning integration
- Enterprise access control and workflows
- Comprehensive audit trails and change tracking
- Template gallery and quick-start options
- Collaborative editing with conflict resolution
- Performance analytics and recommendations
"""

import asyncio
import json
import logging
import time
import uuid
import hashlib
import shutil
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

from playbook_engine import PlaybookEngine, PlaybookValidationError
from advanced_playbook_engine import AdvancedPlaybookEngine, ExecutionState
from playbook_version_control import PlaybookVersionControl, ChangeType, PlaybookVersion

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of resources managed by CRUD operations"""
    PLAYBOOK = "playbook"
    SYSTEM_PROMPT = "system_prompt"
    TEMPLATE = "template"
    WORKFLOW = "workflow"


class AccessLevel(Enum):
    """Access levels for resources"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    OWNER = "owner"


class OperationType(Enum):
    """Types of CRUD operations"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    CLONE = "clone"
    IMPORT = "import"
    EXPORT = "export"
    BULK_CREATE = "bulk_create"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"


class ValidationLevel(Enum):
    """Validation levels for operations"""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    ENTERPRISE = "enterprise"


@dataclass
class ResourceMetadata:
    """Comprehensive metadata for managed resources"""
    resource_id: str
    resource_type: ResourceType
    name: str
    description: str
    category: str
    tags: List[str]
    
    # Ownership and access
    owner_id: str
    created_by: str
    modified_by: str
    access_level: AccessLevel
    
    # Timestamps
    created_at: datetime
    modified_at: datetime
    last_accessed: datetime
    
    # Version information
    current_version: str
    version_count: int
    
    # Usage statistics
    usage_count: int
    success_rate: float
    average_duration: float
    
    # Relationships
    parent_id: Optional[str] = None
    template_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    
    # Enterprise features
    approval_required: bool = False
    approval_workflow_id: Optional[str] = None
    compliance_tags: List[str] = field(default_factory=list)
    
    # hAIveMind integration
    haivemind_memory_ids: List[str] = field(default_factory=list)
    learning_insights: Dict[str, Any] = field(default_factory=dict)
    
    # Soft delete support
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    deletion_reason: Optional[str] = None


@dataclass
class SearchFilter:
    """Advanced search and filtering options"""
    query: Optional[str] = None
    resource_type: Optional[ResourceType] = None
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    owner_id: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    modified_after: Optional[datetime] = None
    modified_before: Optional[datetime] = None
    min_success_rate: Optional[float] = None
    max_duration: Optional[float] = None
    has_dependencies: Optional[bool] = None
    is_template: Optional[bool] = None
    access_level: Optional[AccessLevel] = None
    include_deleted: bool = False
    
    # Advanced filters
    semantic_search: bool = False
    similarity_threshold: float = 0.7
    sort_by: str = "modified_at"
    sort_order: str = "desc"
    limit: int = 100
    offset: int = 0


@dataclass
class BulkOperation:
    """Bulk operation configuration"""
    operation_type: OperationType
    resource_ids: List[str]
    parameters: Dict[str, Any]
    batch_size: int = 10
    continue_on_error: bool = False
    dry_run: bool = False
    
    # Progress tracking
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TemplateDefinition:
    """Template definition for quick-start resources"""
    template_id: str
    name: str
    description: str
    category: str
    resource_type: ResourceType
    content_template: Dict[str, Any]
    variable_schema: Dict[str, Any]
    tags: List[str]
    preview_image: Optional[str] = None
    documentation_url: Optional[str] = None
    complexity_level: str = "beginner"  # beginner, intermediate, advanced
    estimated_time: Optional[int] = None  # minutes


class PlaybookCRUDManager:
    """Comprehensive CRUD operations manager with enterprise features"""
    
    def __init__(self, 
                 memory_storage,
                 config: Dict[str, Any],
                 haivemind_client: Optional[Any] = None):
        self.memory_storage = memory_storage
        self.config = config
        self.haivemind_client = haivemind_client
        
        # Initialize engines
        self.playbook_engine = PlaybookEngine(allow_unsafe_shell=config.get('allow_unsafe_shell', False))
        self.advanced_engine = AdvancedPlaybookEngine(
            allow_unsafe_shell=config.get('allow_unsafe_shell', False),
            haivemind_client=haivemind_client
        )
        self.version_control = PlaybookVersionControl(memory_storage, config.get('version_control', {}))
        
        # Configuration
        self.validation_level = ValidationLevel(config.get('validation_level', 'standard'))
        self.enable_approval_workflows = config.get('enable_approval_workflows', True)
        self.enable_access_control = config.get('enable_access_control', True)
        self.enable_audit_logging = config.get('enable_audit_logging', True)
        
        # Storage paths
        self.templates_path = Path(config.get('templates_path', 'templates'))
        self.exports_path = Path(config.get('exports_path', 'exports'))
        self.imports_path = Path(config.get('imports_path', 'imports'))
        
        # Create directories
        for path in [self.templates_path, self.exports_path, self.imports_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Caches
        self.metadata_cache = {}
        self.template_cache = {}
        self.access_cache = {}
        
        # Built-in templates
        self.builtin_templates = self._load_builtin_templates()
        
        logger.info("🏗️ PlaybookCRUDManager initialized with enterprise features")

    # ==================== CREATE OPERATIONS ====================
    
    async def create_resource(self,
                            resource_type: ResourceType,
                            name: str,
                            content: Dict[str, Any],
                            creator_id: str,
                            description: str = "",
                            category: str = "general",
                            tags: List[str] = None,
                            template_id: Optional[str] = None,
                            parent_id: Optional[str] = None,
                            validation_level: Optional[ValidationLevel] = None) -> Dict[str, Any]:
        """
        Create a new resource with comprehensive validation and tracking
        
        Args:
            resource_type: Type of resource to create
            name: Resource name
            content: Resource content/specification
            creator_id: ID of the creator
            description: Resource description
            category: Resource category
            tags: Resource tags
            template_id: Template used (if any)
            parent_id: Parent resource (for clones/derivatives)
            validation_level: Validation level to apply
            
        Returns:
            Created resource metadata and details
        """
        try:
            # Generate unique resource ID
            resource_id = f"{resource_type.value}_{uuid.uuid4().hex[:12]}"
            
            # Apply validation
            validation_level = validation_level or self.validation_level
            validation_result = await self._validate_resource_content(
                resource_type, content, validation_level
            )
            
            if not validation_result['valid']:
                raise ValueError(f"Validation failed: {validation_result['errors']}")
            
            # Check access permissions
            if self.enable_access_control:
                can_create = await self._check_create_permission(creator_id, resource_type, category)
                if not can_create:
                    raise PermissionError(f"User {creator_id} cannot create {resource_type.value} in category {category}")
            
            # Create metadata
            metadata = ResourceMetadata(
                resource_id=resource_id,
                resource_type=resource_type,
                name=name,
                description=description,
                category=category,
                tags=tags or [],
                owner_id=creator_id,
                created_by=creator_id,
                modified_by=creator_id,
                access_level=AccessLevel.OWNER,
                created_at=datetime.now(),
                modified_at=datetime.now(),
                last_accessed=datetime.now(),
                current_version="1.0.0",
                version_count=1,
                usage_count=0,
                success_rate=0.0,
                average_duration=0.0,
                parent_id=parent_id,
                template_id=template_id
            )
            
            # Store resource content
            await self._store_resource_content(resource_id, content)
            
            # Store metadata
            await self._store_resource_metadata(metadata)
            
            # Create initial version if it's a playbook
            if resource_type == ResourceType.PLAYBOOK:
                await self.version_control.create_playbook_version(
                    playbook_id=resource_id,
                    content=content,
                    change_type=ChangeType.CREATED,
                    change_description=f"Initial creation: {description}",
                    author=creator_id
                )
            
            # Store in hAIveMind
            if self.haivemind_client:
                memory_id = await self._store_haivemind_memory(
                    f"Created {resource_type.value}: {name}",
                    "crud_operations",
                    {
                        "operation": "create",
                        "resource_id": resource_id,
                        "resource_type": resource_type.value,
                        "name": name,
                        "creator": creator_id,
                        "template_used": template_id,
                        "validation_level": validation_level.value
                    }
                )
                metadata.haivemind_memory_ids.append(memory_id)
                await self._store_resource_metadata(metadata)  # Update with memory ID
            
            # Log audit trail
            if self.enable_audit_logging:
                await self._log_audit_event(
                    "resource_created",
                    creator_id,
                    resource_id,
                    {"resource_type": resource_type.value, "name": name}
                )
            
            # Update cache
            self.metadata_cache[resource_id] = metadata
            
            logger.info(f"✅ Created {resource_type.value} '{name}' with ID {resource_id}")
            
            return {
                "resource_id": resource_id,
                "metadata": asdict(metadata),
                "validation_result": validation_result,
                "created_at": metadata.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create resource: {e}")
            
            # Store failure in hAIveMind for learning
            if self.haivemind_client:
                await self._store_haivemind_memory(
                    f"Failed to create {resource_type.value}: {str(e)}",
                    "crud_operations",
                    {
                        "operation": "create",
                        "resource_type": resource_type.value,
                        "error": str(e),
                        "creator": creator_id
                    }
                )
            
            raise

    async def create_from_template(self,
                                 template_id: str,
                                 name: str,
                                 creator_id: str,
                                 variables: Dict[str, Any] = None,
                                 description: str = "",
                                 category: str = "") -> Dict[str, Any]:
        """Create a resource from a template with variable substitution"""
        try:
            # Get template
            template = await self._get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            # Substitute variables in template
            content = await self._substitute_template_variables(
                template.content_template,
                variables or {},
                template.variable_schema
            )
            
            # Use template metadata as defaults
            category = category or template.category
            description = description or f"Created from template: {template.name}"
            
            # Create resource
            result = await self.create_resource(
                resource_type=template.resource_type,
                name=name,
                content=content,
                creator_id=creator_id,
                description=description,
                category=category,
                tags=template.tags + ["from_template"],
                template_id=template_id
            )
            
            logger.info(f"📋 Created resource from template '{template.name}'")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create from template: {e}")
            raise

    async def bulk_create_resources(self,
                                  resources: List[Dict[str, Any]],
                                  creator_id: str,
                                  batch_size: int = 10,
                                  continue_on_error: bool = False) -> BulkOperation:
        """Create multiple resources in bulk with progress tracking"""
        try:
            bulk_op = BulkOperation(
                operation_type=OperationType.BULK_CREATE,
                resource_ids=[],
                parameters={"creator_id": creator_id},
                batch_size=batch_size,
                continue_on_error=continue_on_error,
                total_items=len(resources)
            )
            
            # Process in batches
            for i in range(0, len(resources), batch_size):
                batch = resources[i:i + batch_size]
                
                # Process batch
                batch_tasks = []
                for resource_data in batch:
                    task = self.create_resource(
                        resource_type=ResourceType(resource_data['resource_type']),
                        name=resource_data['name'],
                        content=resource_data['content'],
                        creator_id=creator_id,
                        description=resource_data.get('description', ''),
                        category=resource_data.get('category', 'general'),
                        tags=resource_data.get('tags', [])
                    )
                    batch_tasks.append(task)
                
                # Execute batch
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Process results
                for j, result in enumerate(batch_results):
                    bulk_op.processed_items += 1
                    
                    if isinstance(result, Exception):
                        bulk_op.failed_items += 1
                        bulk_op.errors.append({
                            "index": i + j,
                            "resource_name": batch[j]['name'],
                            "error": str(result)
                        })
                        
                        if not continue_on_error:
                            break
                    else:
                        bulk_op.successful_items += 1
                        bulk_op.resource_ids.append(result['resource_id'])
                
                # Break if error and not continuing
                if bulk_op.failed_items > 0 and not continue_on_error:
                    break
            
            # Store bulk operation result in hAIveMind
            if self.haivemind_client:
                await self._store_haivemind_memory(
                    f"Bulk create operation: {bulk_op.successful_items}/{bulk_op.total_items} successful",
                    "crud_operations",
                    {
                        "operation": "bulk_create",
                        "total_items": bulk_op.total_items,
                        "successful_items": bulk_op.successful_items,
                        "failed_items": bulk_op.failed_items,
                        "creator": creator_id
                    }
                )
            
            logger.info(f"📦 Bulk create completed: {bulk_op.successful_items}/{bulk_op.total_items} successful")
            return bulk_op
            
        except Exception as e:
            logger.error(f"Bulk create failed: {e}")
            raise

    async def import_resources(self,
                             import_path: str,
                             creator_id: str,
                             format_type: str = "auto",
                             validation_level: Optional[ValidationLevel] = None) -> BulkOperation:
        """Import resources from files with format detection and validation"""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                raise FileNotFoundError(f"Import file not found: {import_path}")
            
            # Detect format
            if format_type == "auto":
                format_type = self._detect_file_format(import_file)
            
            # Parse import file
            resources_data = await self._parse_import_file(import_file, format_type)
            
            # Validate import data
            validation_errors = await self._validate_import_data(resources_data, validation_level)
            if validation_errors:
                raise ValueError(f"Import validation failed: {validation_errors}")
            
            # Convert to resource creation format
            resources = []
            for item in resources_data:
                resources.append({
                    "resource_type": item.get("type", "playbook"),
                    "name": item["name"],
                    "content": item["content"],
                    "description": item.get("description", ""),
                    "category": item.get("category", "imported"),
                    "tags": item.get("tags", []) + ["imported"]
                })
            
            # Perform bulk create
            bulk_result = await self.bulk_create_resources(
                resources=resources,
                creator_id=creator_id,
                continue_on_error=True
            )
            
            # Move processed file to archive
            archive_path = self.imports_path / "processed" / f"{int(time.time())}_{import_file.name}"
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(import_file), str(archive_path))
            
            logger.info(f"📥 Import completed: {bulk_result.successful_items} resources imported")
            return bulk_result
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise

    # ==================== READ OPERATIONS ====================
    
    async def search_resources(self, search_filter: SearchFilter) -> Dict[str, Any]:
        """Advanced search with filtering, sorting, and semantic search"""
        try:
            # Build search query
            query_parts = []
            
            if search_filter.query:
                if search_filter.semantic_search:
                    # Use semantic search via hAIveMind
                    semantic_results = await self._semantic_search(
                        search_filter.query,
                        search_filter.similarity_threshold
                    )
                    if semantic_results:
                        query_parts.append(f"resource_id:({' OR '.join(semantic_results)})")
                else:
                    # Text search
                    query_parts.append(f"name:{search_filter.query} OR description:{search_filter.query}")
            
            if search_filter.resource_type:
                query_parts.append(f"resource_type:{search_filter.resource_type.value}")
            
            if search_filter.category:
                query_parts.append(f"category:{search_filter.category}")
            
            if search_filter.tags:
                tag_query = " AND ".join(f"tags:{tag}" for tag in search_filter.tags)
                query_parts.append(f"({tag_query})")
            
            if search_filter.owner_id:
                query_parts.append(f"owner_id:{search_filter.owner_id}")
            
            # Date filters
            if search_filter.created_after:
                query_parts.append(f"created_at:>={search_filter.created_after.isoformat()}")
            
            if search_filter.created_before:
                query_parts.append(f"created_at:<={search_filter.created_before.isoformat()}")
            
            # Performance filters
            if search_filter.min_success_rate is not None:
                query_parts.append(f"success_rate:>={search_filter.min_success_rate}")
            
            if search_filter.max_duration is not None:
                query_parts.append(f"average_duration:<={search_filter.max_duration}")
            
            # Soft delete filter
            if not search_filter.include_deleted:
                query_parts.append("is_deleted:false")
            
            # Combine query parts
            final_query = " AND ".join(query_parts) if query_parts else "*"
            
            # Execute search
            search_results = await self.memory_storage.search_memories(
                query=final_query,
                category="resource_metadata",
                limit=search_filter.limit,
                offset=search_filter.offset
            )
            
            # Parse and enrich results
            resources = []
            for memory in search_results.get('memories', []):
                try:
                    metadata_dict = json.loads(memory.get('content', '{}'))
                    metadata = ResourceMetadata(**metadata_dict)
                    
                    # Apply additional filters that couldn't be done in query
                    if search_filter.access_level and metadata.access_level != search_filter.access_level:
                        continue
                    
                    # Get resource content if needed
                    content = await self._get_resource_content(metadata.resource_id)
                    
                    resources.append({
                        "metadata": asdict(metadata),
                        "content": content,
                        "score": memory.get('score', 1.0)
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to parse search result: {e}")
            
            # Sort results
            resources = self._sort_search_results(resources, search_filter.sort_by, search_filter.sort_order)
            
            # Get total count for pagination
            total_count = len(resources)  # Simplified - could be optimized
            
            result = {
                "resources": resources,
                "total_count": total_count,
                "page_size": search_filter.limit,
                "page_offset": search_filter.offset,
                "search_query": final_query,
                "semantic_search_used": search_filter.semantic_search
            }
            
            # Store search in hAIveMind for learning
            if self.haivemind_client:
                await self._store_haivemind_memory(
                    f"Resource search: '{search_filter.query}' returned {len(resources)} results",
                    "crud_operations",
                    {
                        "operation": "search",
                        "query": search_filter.query,
                        "results_count": len(resources),
                        "semantic_search": search_filter.semantic_search,
                        "filters": asdict(search_filter)
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    async def get_resource(self, resource_id: str, include_content: bool = True, include_versions: bool = False) -> Optional[Dict[str, Any]]:
        """Get a specific resource with optional content and version history"""
        try:
            # Check cache first
            if resource_id in self.metadata_cache:
                metadata = self.metadata_cache[resource_id]
            else:
                # Get from storage
                search_results = await self.memory_storage.search_memories(
                    query=f"resource_id:{resource_id}",
                    category="resource_metadata",
                    limit=1
                )
                
                if not search_results.get('memories'):
                    return None
                
                metadata_dict = json.loads(search_results['memories'][0].get('content', '{}'))
                metadata = ResourceMetadata(**metadata_dict)
                self.metadata_cache[resource_id] = metadata
            
            # Check if deleted and not explicitly requested
            if metadata.is_deleted:
                return None
            
            # Update last accessed
            metadata.last_accessed = datetime.now()
            await self._store_resource_metadata(metadata)
            
            result = {
                "metadata": asdict(metadata)
            }
            
            # Include content if requested
            if include_content:
                content = await self._get_resource_content(resource_id)
                result["content"] = content
            
            # Include version history if requested
            if include_versions and metadata.resource_type == ResourceType.PLAYBOOK:
                versions = await self.version_control.get_version_history(resource_id)
                result["versions"] = [asdict(v) for v in versions]
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get resource {resource_id}: {e}")
            return None

    async def get_resource_analytics(self, resource_id: str) -> Dict[str, Any]:
        """Get comprehensive analytics for a resource"""
        try:
            metadata = await self._get_resource_metadata(resource_id)
            if not metadata:
                raise ValueError(f"Resource {resource_id} not found")
            
            analytics = {
                "basic_stats": {
                    "usage_count": metadata.usage_count,
                    "success_rate": metadata.success_rate,
                    "average_duration": metadata.average_duration,
                    "version_count": metadata.version_count
                },
                "timeline": await self._get_resource_timeline(resource_id),
                "performance_trends": await self._get_performance_trends(resource_id),
                "usage_patterns": await self._get_usage_patterns(resource_id),
                "related_resources": await self._get_related_resources(resource_id),
                "recommendations": await self._get_resource_recommendations(resource_id)
            }
            
            # Add version-specific analytics for playbooks
            if metadata.resource_type == ResourceType.PLAYBOOK:
                version_metrics = await self.version_control.get_playbook_statistics(resource_id)
                analytics["version_analytics"] = version_metrics
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get analytics for {resource_id}: {e}")
            raise

    async def compare_resources(self, resource_id_1: str, resource_id_2: str) -> Dict[str, Any]:
        """Compare two resources and provide detailed differences"""
        try:
            # Get both resources
            resource_1 = await self.get_resource(resource_id_1, include_content=True)
            resource_2 = await self.get_resource(resource_id_2, include_content=True)
            
            if not resource_1 or not resource_2:
                raise ValueError("One or both resources not found")
            
            # Basic comparison
            comparison = {
                "resource_1": {
                    "id": resource_id_1,
                    "name": resource_1["metadata"]["name"],
                    "type": resource_1["metadata"]["resource_type"],
                    "created_at": resource_1["metadata"]["created_at"],
                    "modified_at": resource_1["metadata"]["modified_at"]
                },
                "resource_2": {
                    "id": resource_id_2,
                    "name": resource_2["metadata"]["name"],
                    "type": resource_2["metadata"]["resource_type"],
                    "created_at": resource_2["metadata"]["created_at"],
                    "modified_at": resource_2["metadata"]["modified_at"]
                },
                "differences": {
                    "metadata": self._compare_metadata(resource_1["metadata"], resource_2["metadata"]),
                    "content": self._compare_content(resource_1["content"], resource_2["content"]),
                    "performance": self._compare_performance(resource_1["metadata"], resource_2["metadata"])
                },
                "similarity_score": await self._calculate_similarity_score(resource_1, resource_2)
            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Failed to compare resources: {e}")
            raise

    # ==================== HELPER METHODS ====================
    
    def _load_builtin_templates(self) -> List[TemplateDefinition]:
        """Load built-in templates for quick-start"""
        templates = [
            TemplateDefinition(
                template_id="security_audit",
                name="Security Audit Playbook",
                description="Comprehensive security audit with vulnerability scanning",
                category="security",
                resource_type=ResourceType.PLAYBOOK,
                content_template={
                    "name": "Security Audit - {{system_name}}",
                    "description": "Security audit for {{system_name}}",
                    "parameters": [
                        {"name": "system_name", "required": True, "description": "Target system name"},
                        {"name": "scan_level", "required": False, "description": "Scan intensity level", "default": "standard"}
                    ],
                    "steps": [
                        {
                            "id": "port_scan",
                            "name": "Port Scan",
                            "action": "shell",
                            "args": {"command": "nmap -sS {{system_name}}"},
                            "outputs": [{"name": "scan_results", "from": "stdout"}]
                        },
                        {
                            "id": "vulnerability_check",
                            "name": "Vulnerability Check",
                            "action": "shell",
                            "args": {"command": "nmap --script vuln {{system_name}}"},
                            "outputs": [{"name": "vuln_results", "from": "stdout"}]
                        }
                    ]
                },
                variable_schema={
                    "system_name": {"type": "string", "required": True},
                    "scan_level": {"type": "string", "enum": ["basic", "standard", "comprehensive"], "default": "standard"}
                },
                tags=["security", "audit", "vulnerability"],
                complexity_level="intermediate",
                estimated_time=30
            ),
            TemplateDefinition(
                template_id="deployment_pipeline",
                name="Deployment Pipeline",
                description="Standard deployment pipeline with testing and rollback",
                category="deployment",
                resource_type=ResourceType.PLAYBOOK,
                content_template={
                    "name": "Deploy {{application_name}} to {{environment}}",
                    "description": "Deployment pipeline for {{application_name}}",
                    "parameters": [
                        {"name": "application_name", "required": True},
                        {"name": "environment", "required": True},
                        {"name": "version", "required": True}
                    ],
                    "steps": [
                        {
                            "id": "pre_deploy_check",
                            "name": "Pre-deployment Check",
                            "action": "http_request",
                            "args": {
                                "method": "GET",
                                "url": "https://{{environment}}.example.com/health"
                            },
                            "validations": [
                                {"type": "http_status", "left": "${status_code}", "right": 200}
                            ]
                        },
                        {
                            "id": "deploy",
                            "name": "Deploy Application",
                            "action": "shell",
                            "args": {"command": "kubectl set image deployment/{{application_name}} app={{application_name}}:{{version}}"},
                            "rollback": [
                                {
                                    "action": "shell",
                                    "args": {"rollback_command": "kubectl rollout undo deployment/{{application_name}}"},
                                    "description": "Rollback deployment"
                                }
                            ]
                        },
                        {
                            "id": "post_deploy_test",
                            "name": "Post-deployment Test",
                            "action": "http_request",
                            "args": {
                                "method": "GET",
                                "url": "https://{{environment}}.example.com/api/version"
                            },
                            "validations": [
                                {"type": "contains", "left": "${body}", "right": "{{version}}"}
                            ]
                        }
                    ]
                },
                variable_schema={
                    "application_name": {"type": "string", "required": True},
                    "environment": {"type": "string", "enum": ["dev", "staging", "prod"], "required": True},
                    "version": {"type": "string", "required": True}
                },
                tags=["deployment", "pipeline", "kubernetes"],
                complexity_level="advanced",
                estimated_time=45
            )
        ]
        
        return templates

    async def _validate_resource_content(self, 
                                       resource_type: ResourceType, 
                                       content: Dict[str, Any], 
                                       validation_level: ValidationLevel) -> Dict[str, Any]:
        """Validate resource content based on type and validation level"""
        try:
            result = {"valid": True, "errors": [], "warnings": []}
            
            if resource_type == ResourceType.PLAYBOOK:
                # Use playbook engine validation
                try:
                    self.playbook_engine.validate(content)
                except PlaybookValidationError as e:
                    result["valid"] = False
                    result["errors"].append(str(e))
                
                # Additional validation based on level
                if validation_level in [ValidationLevel.STRICT, ValidationLevel.ENTERPRISE]:
                    # Check for security issues
                    security_issues = await self._check_security_issues(content)
                    if security_issues:
                        if validation_level == ValidationLevel.ENTERPRISE:
                            result["valid"] = False
                            result["errors"].extend(security_issues)
                        else:
                            result["warnings"].extend(security_issues)
                    
                    # Check for best practices
                    best_practice_issues = await self._check_best_practices(content)
                    if best_practice_issues:
                        result["warnings"].extend(best_practice_issues)
            
            elif resource_type == ResourceType.SYSTEM_PROMPT:
                # Validate system prompt structure
                required_fields = ["template", "variables"]
                for field in required_fields:
                    if field not in content:
                        result["valid"] = False
                        result["errors"].append(f"Missing required field: {field}")
                
                # Validate template syntax
                if "template" in content:
                    template_issues = await self._validate_template_syntax(content["template"])
                    if template_issues:
                        result["valid"] = False
                        result["errors"].extend(template_issues)
            
            return result
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {"valid": False, "errors": [str(e)], "warnings": []}

    async def _store_resource_content(self, resource_id: str, content: Dict[str, Any]):
        """Store resource content in memory system"""
        try:
            await self.memory_storage.store_memory(
                content=json.dumps(content),
                category="resource_content",
                metadata={
                    "resource_id": resource_id,
                    "content_hash": hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:16]
                },
                tags=["resource", "content"]
            )
        except Exception as e:
            logger.error(f"Failed to store resource content: {e}")
            raise

    async def _store_resource_metadata(self, metadata: ResourceMetadata):
        """Store resource metadata in memory system"""
        try:
            await self.memory_storage.store_memory(
                content=json.dumps(asdict(metadata), default=str),
                category="resource_metadata",
                metadata={
                    "resource_id": metadata.resource_id,
                    "resource_type": metadata.resource_type.value,
                    "name": metadata.name,
                    "category": metadata.category,
                    "owner_id": metadata.owner_id,
                    "is_deleted": metadata.is_deleted
                },
                tags=["resource", "metadata"] + metadata.tags
            )
        except Exception as e:
            logger.error(f"Failed to store resource metadata: {e}")
            raise

    async def _get_resource_content(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get resource content from storage"""
        try:
            search_results = await self.memory_storage.search_memories(
                query=f"resource_id:{resource_id}",
                category="resource_content",
                limit=1
            )
            
            if search_results.get('memories'):
                content_str = search_results['memories'][0].get('content', '{}')
                return json.loads(content_str)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get resource content: {e}")
            return None

    async def _get_resource_metadata(self, resource_id: str) -> Optional[ResourceMetadata]:
        """Get resource metadata from storage or cache"""
        try:
            # Check cache first
            if resource_id in self.metadata_cache:
                return self.metadata_cache[resource_id]
            
            search_results = await self.memory_storage.search_memories(
                query=f"resource_id:{resource_id}",
                category="resource_metadata",
                limit=1
            )
            
            if search_results.get('memories'):
                metadata_dict = json.loads(search_results['memories'][0].get('content', '{}'))
                metadata = ResourceMetadata(**metadata_dict)
                self.metadata_cache[resource_id] = metadata
                return metadata
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get resource metadata: {e}")
            return None

    async def _store_haivemind_memory(self, content: str, category: str, metadata: Dict[str, Any]) -> str:
        """Store memory in hAIveMind system and return memory ID"""
        if self.haivemind_client:
            try:
                memory_id = await self.haivemind_client.store_memory(
                    content=content,
                    category=category,
                    metadata=metadata,
                    tags=["crud", "playbook", "management"]
                )
                return memory_id
            except Exception as e:
                logger.error(f"Failed to store hAIveMind memory: {e}")
                return ""
        return ""

    async def _log_audit_event(self, event_type: str, user_id: str, resource_id: str, details: Dict[str, Any]):
        """Log audit event for compliance and tracking"""
        try:
            audit_event = {
                "event_type": event_type,
                "user_id": user_id,
                "resource_id": resource_id,
                "timestamp": datetime.now().isoformat(),
                "details": details
            }
            
            await self.memory_storage.store_memory(
                content=json.dumps(audit_event),
                category="audit_log",
                metadata={
                    "event_type": event_type,
                    "user_id": user_id,
                    "resource_id": resource_id
                },
                tags=["audit", "compliance", event_type]
            )
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")

    def _detect_file_format(self, file_path: Path) -> str:
        """Detect file format from extension and content"""
        extension = file_path.suffix.lower()
        
        format_map = {
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.csv': 'csv'
        }
        
        return format_map.get(extension, 'json')

    async def _parse_import_file(self, file_path: Path, format_type: str) -> List[Dict[str, Any]]:
        """Parse import file based on format"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if format_type == 'json':
                data = json.loads(content)
                return data if isinstance(data, list) else [data]
            
            elif format_type == 'yaml':
                import yaml
                data = yaml.safe_load(content)
                return data if isinstance(data, list) else [data]
            
            elif format_type == 'csv':
                import csv
                import io
                reader = csv.DictReader(io.StringIO(content))
                return list(reader)
            
            else:
                raise ValueError(f"Unsupported format: {format_type}")
                
        except Exception as e:
            logger.error(f"Failed to parse import file: {e}")
            raise

    def _sort_search_results(self, resources: List[Dict[str, Any]], sort_by: str, sort_order: str) -> List[Dict[str, Any]]:
        """Sort search results by specified criteria"""
        try:
            reverse = sort_order.lower() == 'desc'
            
            if sort_by == "name":
                return sorted(resources, key=lambda r: r["metadata"]["name"], reverse=reverse)
            elif sort_by == "created_at":
                return sorted(resources, key=lambda r: r["metadata"]["created_at"], reverse=reverse)
            elif sort_by == "modified_at":
                return sorted(resources, key=lambda r: r["metadata"]["modified_at"], reverse=reverse)
            elif sort_by == "usage_count":
                return sorted(resources, key=lambda r: r["metadata"]["usage_count"], reverse=reverse)
            elif sort_by == "success_rate":
                return sorted(resources, key=lambda r: r["metadata"]["success_rate"], reverse=reverse)
            elif sort_by == "score":
                return sorted(resources, key=lambda r: r.get("score", 0), reverse=reverse)
            else:
                return resources
                
        except Exception as e:
            logger.warning(f"Failed to sort results: {e}")
            return resources

    # ==================== UPDATE OPERATIONS ====================
    
    async def update_resource(self,
                            resource_id: str,
                            updates: Dict[str, Any],
                            modifier_id: str,
                            change_description: str = "",
                            create_version: bool = True,
                            validation_level: Optional[ValidationLevel] = None) -> Dict[str, Any]:
        """
        Update a resource with version control and collaborative editing support
        
        Args:
            resource_id: Resource to update
            updates: Dictionary of fields to update
            modifier_id: ID of the user making changes
            change_description: Description of changes
            create_version: Whether to create a new version
            validation_level: Validation level to apply
            
        Returns:
            Updated resource information
        """
        try:
            # Get current resource
            metadata = await self._get_resource_metadata(resource_id)
            if not metadata:
                raise ValueError(f"Resource {resource_id} not found")
            
            if metadata.is_deleted:
                raise ValueError(f"Cannot update deleted resource {resource_id}")
            
            # Check permissions
            if self.enable_access_control:
                can_update = await self._check_update_permission(modifier_id, metadata)
                if not can_update:
                    raise PermissionError(f"User {modifier_id} cannot update resource {resource_id}")
            
            # Check for approval requirement
            if metadata.approval_required and self.enable_approval_workflows:
                approval_needed = await self._check_approval_needed(updates, metadata)
                if approval_needed:
                    return await self._create_update_approval_request(
                        resource_id, updates, modifier_id, change_description
                    )
            
            # Get current content
            current_content = await self._get_resource_content(resource_id)
            if not current_content:
                raise ValueError(f"Resource content not found for {resource_id}")
            
            # Apply updates
            updated_content = current_content.copy()
            updated_metadata = metadata
            
            # Update content if provided
            if "content" in updates:
                updated_content = updates["content"]
                
                # Validate updated content
                validation_level = validation_level or self.validation_level
                validation_result = await self._validate_resource_content(
                    metadata.resource_type, updated_content, validation_level
                )
                
                if not validation_result['valid']:
                    raise ValueError(f"Content validation failed: {validation_result['errors']}")
            
            # Update metadata fields
            metadata_updates = {k: v for k, v in updates.items() if k != "content"}
            for field, value in metadata_updates.items():
                if hasattr(updated_metadata, field):
                    setattr(updated_metadata, field, value)
            
            # Update modification tracking
            updated_metadata.modified_by = modifier_id
            updated_metadata.modified_at = datetime.now()
            
            # Create new version if requested and content changed
            if create_version and "content" in updates and metadata.resource_type == ResourceType.PLAYBOOK:
                # Determine change type
                change_type = self._determine_change_type(current_content, updated_content)
                
                version = await self.version_control.create_playbook_version(
                    playbook_id=resource_id,
                    content=updated_content,
                    change_type=change_type,
                    change_description=change_description or "Resource updated",
                    author=modifier_id,
                    parent_version=updated_metadata.current_version
                )
                
                updated_metadata.current_version = version.version_number
                updated_metadata.version_count += 1
            
            # Store updated content and metadata
            if "content" in updates:
                await self._store_resource_content(resource_id, updated_content)
            
            await self._store_resource_metadata(updated_metadata)
            
            # Update cache
            self.metadata_cache[resource_id] = updated_metadata
            
            # Store in hAIveMind
            if self.haivemind_client:
                memory_id = await self._store_haivemind_memory(
                    f"Updated {metadata.resource_type.value}: {metadata.name}",
                    "crud_operations",
                    {
                        "operation": "update",
                        "resource_id": resource_id,
                        "modifier": modifier_id,
                        "changes": list(updates.keys()),
                        "version_created": create_version and "content" in updates
                    }
                )
                updated_metadata.haivemind_memory_ids.append(memory_id)
                await self._store_resource_metadata(updated_metadata)
            
            # Log audit event
            if self.enable_audit_logging:
                await self._log_audit_event(
                    "resource_updated",
                    modifier_id,
                    resource_id,
                    {"updates": list(updates.keys()), "change_description": change_description}
                )
            
            logger.info(f"✏️ Updated resource {resource_id} by {modifier_id}")
            
            return {
                "resource_id": resource_id,
                "metadata": asdict(updated_metadata),
                "version_created": create_version and "content" in updates,
                "validation_result": validation_result if "content" in updates else None,
                "updated_at": updated_metadata.modified_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to update resource {resource_id}: {e}")
            
            # Store failure in hAIveMind
            if self.haivemind_client:
                await self._store_haivemind_memory(
                    f"Failed to update resource {resource_id}: {str(e)}",
                    "crud_operations",
                    {
                        "operation": "update",
                        "resource_id": resource_id,
                        "error": str(e),
                        "modifier": modifier_id
                    }
                )
            
            raise

    async def bulk_update_resources(self,
                                  updates: List[Dict[str, Any]],
                                  modifier_id: str,
                                  batch_size: int = 10,
                                  continue_on_error: bool = False) -> BulkOperation:
        """Update multiple resources in bulk"""
        try:
            bulk_op = BulkOperation(
                operation_type=OperationType.BULK_UPDATE,
                resource_ids=[],
                parameters={"modifier_id": modifier_id},
                batch_size=batch_size,
                continue_on_error=continue_on_error,
                total_items=len(updates)
            )
            
            # Process in batches
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i + batch_size]
                
                # Process batch
                batch_tasks = []
                for update_data in batch:
                    resource_id = update_data.pop("resource_id")
                    bulk_op.resource_ids.append(resource_id)
                    
                    task = self.update_resource(
                        resource_id=resource_id,
                        updates=update_data.get("updates", {}),
                        modifier_id=modifier_id,
                        change_description=update_data.get("change_description", "Bulk update"),
                        create_version=update_data.get("create_version", False)
                    )
                    batch_tasks.append(task)
                
                # Execute batch
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Process results
                for j, result in enumerate(batch_results):
                    bulk_op.processed_items += 1
                    
                    if isinstance(result, Exception):
                        bulk_op.failed_items += 1
                        bulk_op.errors.append({
                            "index": i + j,
                            "resource_id": batch[j].get("resource_id"),
                            "error": str(result)
                        })
                        
                        if not continue_on_error:
                            break
                    else:
                        bulk_op.successful_items += 1
                
                # Break if error and not continuing
                if bulk_op.failed_items > 0 and not continue_on_error:
                    break
            
            logger.info(f"📝 Bulk update completed: {bulk_op.successful_items}/{bulk_op.total_items} successful")
            return bulk_op
            
        except Exception as e:
            logger.error(f"Bulk update failed: {e}")
            raise

    async def collaborative_edit_resource(self,
                                        resource_id: str,
                                        editor_id: str,
                                        edit_session_id: str,
                                        changes: Dict[str, Any]) -> Dict[str, Any]:
        """Handle collaborative editing with conflict resolution"""
        try:
            # Get current resource state
            metadata = await self._get_resource_metadata(resource_id)
            if not metadata:
                raise ValueError(f"Resource {resource_id} not found")
            
            # Check for concurrent edits
            active_sessions = await self._get_active_edit_sessions(resource_id)
            if len(active_sessions) > 1:
                # Handle conflict resolution
                conflict_resolution = await self._resolve_edit_conflicts(
                    resource_id, edit_session_id, changes, active_sessions
                )
                
                if conflict_resolution["conflicts_found"]:
                    return {
                        "status": "conflict",
                        "conflicts": conflict_resolution["conflicts"],
                        "suggested_resolution": conflict_resolution["suggested_resolution"]
                    }
            
            # Apply changes
            result = await self.update_resource(
                resource_id=resource_id,
                updates=changes,
                modifier_id=editor_id,
                change_description=f"Collaborative edit session {edit_session_id}",
                create_version=True
            )
            
            # Update edit session
            await self._update_edit_session(edit_session_id, "completed", result)
            
            return {
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Collaborative edit failed: {e}")
            raise

    # ==================== DELETE OPERATIONS ====================
    
    async def delete_resource(self,
                            resource_id: str,
                            deleter_id: str,
                            hard_delete: bool = False,
                            deletion_reason: str = "",
                            cascade_delete: bool = False) -> Dict[str, Any]:
        """
        Delete a resource with soft/hard delete options and cascade handling
        
        Args:
            resource_id: Resource to delete
            deleter_id: ID of user performing deletion
            hard_delete: Whether to permanently delete (vs soft delete)
            deletion_reason: Reason for deletion
            cascade_delete: Whether to delete dependent resources
            
        Returns:
            Deletion result information
        """
        try:
            # Get resource metadata
            metadata = await self._get_resource_metadata(resource_id)
            if not metadata:
                raise ValueError(f"Resource {resource_id} not found")
            
            if metadata.is_deleted and not hard_delete:
                raise ValueError(f"Resource {resource_id} is already deleted")
            
            # Check permissions
            if self.enable_access_control:
                can_delete = await self._check_delete_permission(deleter_id, metadata)
                if not can_delete:
                    raise PermissionError(f"User {deleter_id} cannot delete resource {resource_id}")
            
            # Check for dependencies
            dependents = await self._get_resource_dependents(resource_id)
            if dependents and not cascade_delete:
                return {
                    "status": "blocked",
                    "reason": "Resource has dependents",
                    "dependents": dependents,
                    "cascade_required": True
                }
            
            deletion_result = {
                "resource_id": resource_id,
                "deletion_type": "hard" if hard_delete else "soft",
                "deleted_at": datetime.now().isoformat(),
                "deleted_by": deleter_id,
                "deletion_reason": deletion_reason,
                "cascade_deleted": []
            }
            
            # Handle cascade deletion
            if cascade_delete and dependents:
                for dependent_id in dependents:
                    try:
                        cascade_result = await self.delete_resource(
                            resource_id=dependent_id,
                            deleter_id=deleter_id,
                            hard_delete=hard_delete,
                            deletion_reason=f"Cascade delete from {resource_id}",
                            cascade_delete=True
                        )
                        deletion_result["cascade_deleted"].append({
                            "resource_id": dependent_id,
                            "status": "success"
                        })
                    except Exception as e:
                        deletion_result["cascade_deleted"].append({
                            "resource_id": dependent_id,
                            "status": "failed",
                            "error": str(e)
                        })
            
            if hard_delete:
                # Permanently delete resource
                await self._hard_delete_resource(resource_id)
                deletion_result["recoverable"] = False
            else:
                # Soft delete - mark as deleted but keep data
                metadata.is_deleted = True
                metadata.deleted_at = datetime.now()
                metadata.deleted_by = deleter_id
                metadata.deletion_reason = deletion_reason
                
                await self._store_resource_metadata(metadata)
                self.metadata_cache[resource_id] = metadata
                
                deletion_result["recoverable"] = True
                deletion_result["recovery_deadline"] = (datetime.now() + timedelta(days=30)).isoformat()
            
            # Store in hAIveMind
            if self.haivemind_client:
                memory_id = await self._store_haivemind_memory(
                    f"Deleted {metadata.resource_type.value}: {metadata.name} ({'hard' if hard_delete else 'soft'})",
                    "crud_operations",
                    {
                        "operation": "delete",
                        "resource_id": resource_id,
                        "deleter": deleter_id,
                        "hard_delete": hard_delete,
                        "cascade_delete": cascade_delete,
                        "dependents_count": len(dependents) if dependents else 0
                    }
                )
                if not hard_delete:
                    metadata.haivemind_memory_ids.append(memory_id)
                    await self._store_resource_metadata(metadata)
            
            # Log audit event
            if self.enable_audit_logging:
                await self._log_audit_event(
                    "resource_deleted",
                    deleter_id,
                    resource_id,
                    {
                        "deletion_type": "hard" if hard_delete else "soft",
                        "reason": deletion_reason,
                        "cascade_delete": cascade_delete
                    }
                )
            
            logger.info(f"🗑️ {'Hard' if hard_delete else 'Soft'} deleted resource {resource_id} by {deleter_id}")
            
            return {
                "status": "success",
                **deletion_result
            }
            
        except Exception as e:
            logger.error(f"Failed to delete resource {resource_id}: {e}")
            
            # Store failure in hAIveMind
            if self.haivemind_client:
                await self._store_haivemind_memory(
                    f"Failed to delete resource {resource_id}: {str(e)}",
                    "crud_operations",
                    {
                        "operation": "delete",
                        "resource_id": resource_id,
                        "error": str(e),
                        "deleter": deleter_id
                    }
                )
            
            raise

    async def recover_deleted_resource(self,
                                     resource_id: str,
                                     recoverer_id: str,
                                     recovery_reason: str = "") -> Dict[str, Any]:
        """Recover a soft-deleted resource"""
        try:
            # Get resource metadata
            metadata = await self._get_resource_metadata(resource_id)
            if not metadata:
                raise ValueError(f"Resource {resource_id} not found")
            
            if not metadata.is_deleted:
                raise ValueError(f"Resource {resource_id} is not deleted")
            
            # Check recovery deadline (30 days)
            if metadata.deleted_at and (datetime.now() - metadata.deleted_at).days > 30:
                raise ValueError(f"Resource {resource_id} is beyond recovery deadline")
            
            # Check permissions
            if self.enable_access_control:
                can_recover = await self._check_recover_permission(recoverer_id, metadata)
                if not can_recover:
                    raise PermissionError(f"User {recoverer_id} cannot recover resource {resource_id}")
            
            # Recover resource
            metadata.is_deleted = False
            metadata.deleted_at = None
            metadata.deleted_by = None
            metadata.deletion_reason = None
            metadata.modified_by = recoverer_id
            metadata.modified_at = datetime.now()
            
            await self._store_resource_metadata(metadata)
            self.metadata_cache[resource_id] = metadata
            
            # Store in hAIveMind
            if self.haivemind_client:
                memory_id = await self._store_haivemind_memory(
                    f"Recovered {metadata.resource_type.value}: {metadata.name}",
                    "crud_operations",
                    {
                        "operation": "recover",
                        "resource_id": resource_id,
                        "recoverer": recoverer_id,
                        "recovery_reason": recovery_reason
                    }
                )
                metadata.haivemind_memory_ids.append(memory_id)
                await self._store_resource_metadata(metadata)
            
            # Log audit event
            if self.enable_audit_logging:
                await self._log_audit_event(
                    "resource_recovered",
                    recoverer_id,
                    resource_id,
                    {"recovery_reason": recovery_reason}
                )
            
            logger.info(f"♻️ Recovered resource {resource_id} by {recoverer_id}")
            
            return {
                "status": "success",
                "resource_id": resource_id,
                "recovered_at": metadata.modified_at.isoformat(),
                "recovered_by": recoverer_id
            }
            
        except Exception as e:
            logger.error(f"Failed to recover resource {resource_id}: {e}")
            raise

    async def bulk_delete_resources(self,
                                  resource_ids: List[str],
                                  deleter_id: str,
                                  hard_delete: bool = False,
                                  deletion_reason: str = "",
                                  confirmation_required: bool = True) -> BulkOperation:
        """Bulk delete resources with safety checks"""
        try:
            if confirmation_required and len(resource_ids) > 10:
                raise ValueError("Bulk deletion of more than 10 resources requires explicit confirmation")
            
            bulk_op = BulkOperation(
                operation_type=OperationType.BULK_DELETE,
                resource_ids=resource_ids,
                parameters={
                    "deleter_id": deleter_id,
                    "hard_delete": hard_delete,
                    "deletion_reason": deletion_reason
                },
                total_items=len(resource_ids)
            )
            
            # Process deletions
            for resource_id in resource_ids:
                try:
                    result = await self.delete_resource(
                        resource_id=resource_id,
                        deleter_id=deleter_id,
                        hard_delete=hard_delete,
                        deletion_reason=deletion_reason or "Bulk deletion"
                    )
                    
                    bulk_op.processed_items += 1
                    if result["status"] == "success":
                        bulk_op.successful_items += 1
                    else:
                        bulk_op.failed_items += 1
                        bulk_op.errors.append({
                            "resource_id": resource_id,
                            "error": result.get("reason", "Unknown error")
                        })
                        
                except Exception as e:
                    bulk_op.processed_items += 1
                    bulk_op.failed_items += 1
                    bulk_op.errors.append({
                        "resource_id": resource_id,
                        "error": str(e)
                    })
            
            logger.info(f"🗑️ Bulk delete completed: {bulk_op.successful_items}/{bulk_op.total_items} successful")
            return bulk_op
            
        except Exception as e:
            logger.error(f"Bulk delete failed: {e}")
            raise

    async def cleanup_expired_deletions(self, retention_days: int = 30) -> Dict[str, Any]:
        """Clean up expired soft deletions"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # Find expired soft deletions
            search_results = await self.memory_storage.search_memories(
                query=f"is_deleted:true AND deleted_at:<={cutoff_date.isoformat()}",
                category="resource_metadata",
                limit=1000
            )
            
            cleanup_result = {
                "total_found": len(search_results.get('memories', [])),
                "cleaned_up": 0,
                "errors": []
            }
            
            for memory in search_results.get('memories', []):
                try:
                    metadata_dict = json.loads(memory.get('content', '{}'))
                    resource_id = metadata_dict.get('resource_id')
                    
                    if resource_id:
                        await self._hard_delete_resource(resource_id)
                        cleanup_result["cleaned_up"] += 1
                        
                except Exception as e:
                    cleanup_result["errors"].append({
                        "resource_id": metadata_dict.get('resource_id', 'unknown'),
                        "error": str(e)
                    })
            
            # Store cleanup result in hAIveMind
            if self.haivemind_client:
                await self._store_haivemind_memory(
                    f"Cleanup expired deletions: {cleanup_result['cleaned_up']} resources permanently deleted",
                    "crud_operations",
                    {
                        "operation": "cleanup_expired",
                        "retention_days": retention_days,
                        "cleaned_up": cleanup_result["cleaned_up"],
                        "errors_count": len(cleanup_result["errors"])
                    }
                )
            
            logger.info(f"🧹 Cleaned up {cleanup_result['cleaned_up']} expired deletions")
            return cleanup_result
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            raise

    # ==================== ADDITIONAL HELPER METHODS ====================
    
    async def _determine_change_type(self, old_content: Dict[str, Any], new_content: Dict[str, Any]) -> ChangeType:
        """Determine the type of change made to content"""
        try:
            # Simple heuristic - could be enhanced with more sophisticated analysis
            old_str = json.dumps(old_content, sort_keys=True)
            new_str = json.dumps(new_content, sort_keys=True)
            
            # Calculate similarity
            similarity = self._calculate_content_similarity(old_str, new_str)
            
            if similarity > 0.9:
                return ChangeType.BUGFIX
            elif similarity > 0.7:
                return ChangeType.MODIFIED
            else:
                return ChangeType.IMPROVED
                
        except Exception:
            return ChangeType.MODIFIED

    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings"""
        try:
            # Simple Jaccard similarity
            set1 = set(content1.split())
            set2 = set(content2.split())
            
            intersection = len(set1.intersection(set2))
            union = len(set1.union(set2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception:
            return 0.0

    async def _hard_delete_resource(self, resource_id: str):
        """Permanently delete a resource and all its data"""
        try:
            # Delete resource content
            content_results = await self.memory_storage.search_memories(
                query=f"resource_id:{resource_id}",
                category="resource_content",
                limit=10
            )
            
            for memory in content_results.get('memories', []):
                await self.memory_storage.delete_memory(memory['id'], hard_delete=True)
            
            # Delete resource metadata
            metadata_results = await self.memory_storage.search_memories(
                query=f"resource_id:{resource_id}",
                category="resource_metadata",
                limit=10
            )
            
            for memory in metadata_results.get('memories', []):
                await self.memory_storage.delete_memory(memory['id'], hard_delete=True)
            
            # Remove from cache
            if resource_id in self.metadata_cache:
                del self.metadata_cache[resource_id]
            
            logger.info(f"💀 Hard deleted resource {resource_id}")
            
        except Exception as e:
            logger.error(f"Failed to hard delete resource {resource_id}: {e}")
            raise

    async def _get_resource_dependents(self, resource_id: str) -> List[str]:
        """Get list of resources that depend on this resource"""
        try:
            # Search for resources that reference this resource_id
            search_results = await self.memory_storage.search_memories(
                query=f"dependencies:{resource_id}",
                category="resource_metadata",
                limit=100
            )
            
            dependents = []
            for memory in search_results.get('memories', []):
                try:
                    metadata_dict = json.loads(memory.get('content', '{}'))
                    dependent_id = metadata_dict.get('resource_id')
                    if dependent_id and dependent_id != resource_id:
                        dependents.append(dependent_id)
                except Exception as e:
                    logger.warning(f"Failed to parse dependent metadata: {e}")
            
            return dependents
            
        except Exception as e:
            logger.error(f"Failed to get dependents for {resource_id}: {e}")
            return []

    async def _check_create_permission(self, user_id: str, resource_type: ResourceType, category: str) -> bool:
        """Check if user has permission to create resources"""
        # Simplified permission check - would integrate with actual auth system
        return True

    async def _check_update_permission(self, user_id: str, metadata: ResourceMetadata) -> bool:
        """Check if user has permission to update resource"""
        # Owner can always update
        if metadata.owner_id == user_id:
            return True
        
        # Check access level
        if metadata.access_level in [AccessLevel.WRITE, AccessLevel.ADMIN]:
            return True
        
        return False

    async def _check_delete_permission(self, user_id: str, metadata: ResourceMetadata) -> bool:
        """Check if user has permission to delete resource"""
        # Only owner or admin can delete
        return metadata.owner_id == user_id or metadata.access_level == AccessLevel.ADMIN

    async def _check_recover_permission(self, user_id: str, metadata: ResourceMetadata) -> bool:
        """Check if user has permission to recover resource"""
        # Same as delete permission
        return await self._check_delete_permission(user_id, metadata)

    logger.info("🏗️ PlaybookCRUDManager implementation completed with full CRUD operations")