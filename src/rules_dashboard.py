#!/usr/bin/env python3
"""
Rules Dashboard - Comprehensive CRUD Operations for hAIveMind Rules Management
Provides visual rule builder, templates, analytics, and full lifecycle management

Author: Lance James, Unit 221B Inc
"""

import os
import json
import uuid
import yaml
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Request, Form, UploadFile, File, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import jinja2

from .rules_database import RulesDatabase, RuleTemplate, RuleCategory, RuleAssignment, RuleDependency, RuleVersion, RuleChangeType
from .rules_engine import RulesEngine, Rule, RuleType, RuleScope, RulePriority, RuleStatus, ConflictResolution, RuleCondition, RuleAction
from .rule_validator import RuleValidator
from .rule_performance import RulePerformanceAnalyzer

# Request/Response Models
class RuleCreateRequest(BaseModel):
    name: str
    description: str
    rule_type: str
    scope: str = "global"
    priority: int = 500
    conditions: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    tags: List[str] = []
    parent_rule_id: Optional[str] = None
    conflict_resolution: str = "highest_priority"
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None
    metadata: Dict[str, Any] = {}

class RuleUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rule_type: Optional[str] = None
    scope: Optional[str] = None
    priority: Optional[int] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    parent_rule_id: Optional[str] = None
    conflict_resolution: Optional[str] = None
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    change_reason: Optional[str] = None

class RuleTemplateCreateRequest(BaseModel):
    name: str
    description: str
    rule_type: str
    template_data: Dict[str, Any]
    category: str
    tags: List[str] = []

class RuleFromTemplateRequest(BaseModel):
    template_id: str
    parameters: Dict[str, Any]
    scope: str = "global"
    priority: int = 500

class RuleBulkOperationRequest(BaseModel):
    rule_ids: List[str]
    operation: str  # activate, deactivate, delete, assign
    parameters: Dict[str, Any] = {}

class RuleAssignmentRequest(BaseModel):
    rule_id: str
    scope_type: str  # global, project, machine, agent, user
    scope_id: str
    priority_override: Optional[int] = None
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None

class RuleImportRequest(BaseModel):
    format: str = "yaml"  # yaml, json
    content: str
    overwrite: bool = False

class RuleConflictResolutionRequest(BaseModel):
    conflict_id: str
    resolution_strategy: str
    selected_rule_id: str

class RulesDashboard:
    """Comprehensive Rules Dashboard with full CRUD operations"""
    
    def __init__(self, db_path: str = "database/rules.db", chroma_client=None, redis_client=None, memory_storage=None):
        self.db = RulesDatabase(db_path, chroma_client, redis_client)
        self.engine = RulesEngine(db_path, chroma_client, redis_client)
        self.validator = RuleValidator(self.db)
        self.performance_analyzer = RulePerformanceAnalyzer(self.db)
        self.memory_storage = memory_storage
        
        # Setup Jinja2 templates
        self.templates = jinja2.Environment(
            loader=jinja2.FileSystemLoader("templates") if Path("templates").exists() 
            else jinja2.DictLoader(self._get_default_templates())
        )
        
        # Rule conflict cache
        self.conflict_cache = {}
        
    def get_router(self):
        """Get FastAPI router with all rules dashboard endpoints"""
        from fastapi import APIRouter
        router = APIRouter(prefix="/api/v1/rules", tags=["Rules Dashboard"])
        
        # ================= CREATE OPERATIONS =================
        
        @router.post("/")
        async def create_rule(request: RuleCreateRequest, current_user: dict = Depends(self._get_current_user)):
            """Create a new rule with validation"""
            try:
                # Convert request to Rule object
                rule = Rule(
                    id=str(uuid.uuid4()),
                    name=request.name,
                    description=request.description,
                    rule_type=RuleType(request.rule_type),
                    scope=RuleScope(request.scope),
                    priority=RulePriority(request.priority),
                    status=RuleStatus.ACTIVE,
                    conditions=[RuleCondition(**c) for c in request.conditions],
                    actions=[RuleAction(**a) for a in request.actions],
                    tags=request.tags,
                    created_at=datetime.now(),
                    created_by=current_user['username'],
                    updated_at=datetime.now(),
                    updated_by=current_user['username'],
                    version=1,
                    parent_rule_id=request.parent_rule_id,
                    conflict_resolution=ConflictResolution(request.conflict_resolution),
                    metadata=request.metadata
                )
                
                # Add effective dates if provided
                if request.effective_from:
                    rule.effective_from = datetime.fromisoformat(request.effective_from)
                if request.effective_until:
                    rule.effective_until = datetime.fromisoformat(request.effective_until)
                
                # Validate rule
                validation_result = await self.validator.validate_rule(rule)
                if not validation_result.is_valid:
                    raise HTTPException(status_code=400, detail={
                        "message": "Rule validation failed",
                        "errors": validation_result.errors,
                        "warnings": validation_result.warnings
                    })
                
                # Create rule
                rule_id = self.db.create_rule(rule, "Created via dashboard")
                
                # Store in hAIveMind memory
                await self._store_rule_memory(rule, "created", current_user['username'])
                
                return {
                    "rule_id": rule_id,
                    "validation": validation_result.to_dict(),
                    "message": "Rule created successfully"
                }
                
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/from-template")
        async def create_rule_from_template(request: RuleFromTemplateRequest, current_user: dict = Depends(self._get_current_user)):
            """Create a rule from a template with parameter substitution"""
            try:
                rule_id = self.db.create_rule_from_template(
                    request.template_id,
                    request.parameters,
                    current_user['username']
                )
                
                if not rule_id:
                    raise HTTPException(status_code=404, detail="Template not found")
                
                # Get created rule for memory storage
                rule = self.db.get_rule(rule_id)
                await self._store_rule_memory(rule, "created_from_template", current_user['username'])
                
                return {
                    "rule_id": rule_id,
                    "template_id": request.template_id,
                    "message": "Rule created from template successfully"
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/templates")
        async def create_rule_template(request: RuleTemplateCreateRequest, current_user: dict = Depends(self._get_current_user)):
            """Create a new rule template"""
            try:
                template = RuleTemplate(
                    id=str(uuid.uuid4()),
                    name=request.name,
                    description=request.description,
                    rule_type=RuleType(request.rule_type),
                    template_data=request.template_data,
                    category=request.category,
                    tags=request.tags,
                    created_by=current_user['username'],
                    created_at=datetime.now()
                )
                
                template_id = self.db.create_rule_template(template)
                
                return {
                    "template_id": template_id,
                    "message": "Rule template created successfully"
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/import")
        async def import_rules(request: RuleImportRequest, current_user: dict = Depends(self._get_current_user)):
            """Import rules from YAML or JSON format"""
            try:
                imported_rule_ids = self.db.import_rules(
                    request.content,
                    request.format,
                    current_user['username'],
                    request.overwrite
                )
                
                # Store import activity in hAIveMind memory
                if self.memory_storage:
                    await self.memory_storage.store_memory(
                        content=f"Imported {len(imported_rule_ids)} rules from {request.format} format",
                        category="rules",
                        context="Rule import operation",
                        metadata={
                            "imported_rule_ids": imported_rule_ids,
                            "format": request.format,
                            "overwrite": request.overwrite,
                            "imported_by": current_user['username']
                        },
                        tags=["rules", "import", request.format],
                        user_id=current_user['username']
                    )
                
                return {
                    "imported_rule_ids": imported_rule_ids,
                    "count": len(imported_rule_ids),
                    "message": f"Successfully imported {len(imported_rule_ids)} rules"
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # ================= READ OPERATIONS =================
        
        @router.get("/")
        async def list_rules(
            rule_type: Optional[str] = None,
            scope: Optional[str] = None,
            status: Optional[str] = None,
            category: Optional[str] = None,
            tags: Optional[str] = None,
            search: Optional[str] = None,
            limit: int = 100,
            offset: int = 0,
            sort_by: str = "created_at",
            sort_order: str = "desc",
            current_user: dict = Depends(self._get_current_user)
        ):
            """List rules with advanced filtering and search"""
            try:
                filters = {}
                if rule_type:
                    filters['rule_type'] = rule_type
                if scope:
                    filters['scope'] = scope
                if status:
                    filters['status'] = status
                if category:
                    filters['category'] = category
                if tags:
                    filters['tags'] = tags.split(',')
                
                rules = self.db.search_rules(
                    filters=filters,
                    search_query=search,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order
                )
                
                return {
                    "rules": [self._rule_to_dict(rule) for rule in rules],
                    "total": len(rules),
                    "filters": filters,
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "sort_by": sort_by,
                        "sort_order": sort_order
                    }
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.get("/{rule_id}")
        async def get_rule(rule_id: str, current_user: dict = Depends(self._get_current_user)):
            """Get a specific rule with full details"""
            try:
                rule = self.db.get_rule(rule_id)
                if not rule:
                    raise HTTPException(status_code=404, detail="Rule not found")
                
                # Get additional details
                version_history = self.db.get_rule_version_history(rule_id)
                dependencies = self.db.get_rule_dependencies(rule_id)
                assignments = self.db.get_rule_assignments(rule_id)
                analytics = self.performance_analyzer.get_rule_analytics(rule_id)
                
                return {
                    "rule": self._rule_to_dict(rule),
                    "version_history": [self._version_to_dict(v) for v in version_history],
                    "dependencies": [self._dependency_to_dict(d) for d in dependencies],
                    "assignments": [self._assignment_to_dict(a) for a in assignments],
                    "analytics": analytics
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.get("/{rule_id}/conflicts")
        async def get_rule_conflicts(rule_id: str, current_user: dict = Depends(self._get_current_user)):
            """Get potential conflicts for a rule"""
            try:
                rule = self.db.get_rule(rule_id)
                if not rule:
                    raise HTTPException(status_code=404, detail="Rule not found")
                
                conflicts = await self.validator.detect_rule_conflicts(rule)
                
                return {
                    "rule_id": rule_id,
                    "conflicts": conflicts,
                    "conflict_count": len(conflicts)
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.get("/templates")
        async def list_rule_templates(
            category: Optional[str] = None,
            rule_type: Optional[str] = None,
            current_user: dict = Depends(self._get_current_user)
        ):
            """List available rule templates"""
            try:
                templates = self.db.list_rule_templates(category)
                
                if rule_type:
                    templates = [t for t in templates if t.rule_type.value == rule_type]
                
                return {
                    "templates": [self._template_to_dict(t) for t in templates],
                    "categories": list(set(t.category for t in templates))
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.get("/analytics/dashboard")
        async def get_dashboard_analytics(current_user: dict = Depends(self._get_current_user)):
            """Get comprehensive dashboard analytics"""
            try:
                # Basic statistics
                stats = self.db.get_rule_statistics()
                
                # Performance analytics
                performance = self.performance_analyzer.get_overall_performance()
                
                # Recent activity
                recent_activity = self.db.get_recent_rule_activity(days=7)
                
                # Conflict analysis
                conflicts = await self.validator.detect_all_conflicts()
                
                # Usage patterns
                usage_patterns = self.performance_analyzer.get_usage_patterns()
                
                return {
                    "statistics": stats,
                    "performance": performance,
                    "recent_activity": recent_activity,
                    "conflicts": {
                        "total": len(conflicts),
                        "by_type": self._group_conflicts_by_type(conflicts)
                    },
                    "usage_patterns": usage_patterns,
                    "generated_at": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # ================= UPDATE OPERATIONS =================
        
        @router.put("/{rule_id}")
        async def update_rule(rule_id: str, request: RuleUpdateRequest, current_user: dict = Depends(self._get_current_user)):
            """Update an existing rule with version tracking"""
            try:
                rule = self.db.get_rule(rule_id)
                if not rule:
                    raise HTTPException(status_code=404, detail="Rule not found")
                
                # Update rule fields
                if request.name is not None:
                    rule.name = request.name
                if request.description is not None:
                    rule.description = request.description
                if request.rule_type is not None:
                    rule.rule_type = RuleType(request.rule_type)
                if request.scope is not None:
                    rule.scope = RuleScope(request.scope)
                if request.priority is not None:
                    rule.priority = RulePriority(request.priority)
                if request.conditions is not None:
                    rule.conditions = [RuleCondition(**c) for c in request.conditions]
                if request.actions is not None:
                    rule.actions = [RuleAction(**a) for a in request.actions]
                if request.tags is not None:
                    rule.tags = request.tags
                if request.parent_rule_id is not None:
                    rule.parent_rule_id = request.parent_rule_id
                if request.conflict_resolution is not None:
                    rule.conflict_resolution = ConflictResolution(request.conflict_resolution)
                if request.metadata is not None:
                    rule.metadata = request.metadata
                
                # Update timestamps
                rule.updated_at = datetime.now()
                rule.updated_by = current_user['username']
                
                # Validate updated rule
                validation_result = await self.validator.validate_rule(rule)
                if not validation_result.is_valid:
                    raise HTTPException(status_code=400, detail={
                        "message": "Rule validation failed",
                        "errors": validation_result.errors,
                        "warnings": validation_result.warnings
                    })
                
                # Update rule
                success = self.db.update_rule(rule, request.change_reason)
                if not success:
                    raise HTTPException(status_code=500, detail="Failed to update rule")
                
                # Store in hAIveMind memory
                await self._store_rule_memory(rule, "updated", current_user['username'])
                
                return {
                    "rule_id": rule_id,
                    "validation": validation_result.to_dict(),
                    "message": "Rule updated successfully"
                }
                
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/{rule_id}/activate")
        async def activate_rule(rule_id: str, effective_from: Optional[str] = None, current_user: dict = Depends(self._get_current_user)):
            """Activate a rule"""
            try:
                effective_date = datetime.fromisoformat(effective_from) if effective_from else None
                success = self.db.activate_rule(rule_id, current_user['username'], effective_date)
                
                if not success:
                    raise HTTPException(status_code=404, detail="Rule not found")
                
                # Store in hAIveMind memory
                rule = self.db.get_rule(rule_id)
                await self._store_rule_memory(rule, "activated", current_user['username'])
                
                return {"message": "Rule activated successfully"}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/{rule_id}/deactivate")
        async def deactivate_rule(rule_id: str, effective_until: Optional[str] = None, current_user: dict = Depends(self._get_current_user)):
            """Deactivate a rule"""
            try:
                effective_date = datetime.fromisoformat(effective_until) if effective_until else None
                success = self.db.deactivate_rule(rule_id, current_user['username'], effective_date)
                
                if not success:
                    raise HTTPException(status_code=404, detail="Rule not found")
                
                # Store in hAIveMind memory
                rule = self.db.get_rule(rule_id)
                await self._store_rule_memory(rule, "deactivated", current_user['username'])
                
                return {"message": "Rule deactivated successfully"}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/bulk-operations")
        async def bulk_rule_operations(request: RuleBulkOperationRequest, current_user: dict = Depends(self._get_current_user)):
            """Perform bulk operations on multiple rules"""
            try:
                results = []
                
                for rule_id in request.rule_ids:
                    try:
                        if request.operation == "activate":
                            success = self.db.activate_rule(rule_id, current_user['username'])
                        elif request.operation == "deactivate":
                            success = self.db.deactivate_rule(rule_id, current_user['username'])
                        elif request.operation == "delete":
                            success = self.db.delete_rule(rule_id, current_user['username'])
                        else:
                            success = False
                        
                        results.append({
                            "rule_id": rule_id,
                            "success": success,
                            "operation": request.operation
                        })
                        
                    except Exception as e:
                        results.append({
                            "rule_id": rule_id,
                            "success": False,
                            "operation": request.operation,
                            "error": str(e)
                        })
                
                # Store bulk operation in hAIveMind memory
                if self.memory_storage:
                    successful_ops = [r for r in results if r['success']]
                    await self.memory_storage.store_memory(
                        content=f"Bulk {request.operation} operation on {len(successful_ops)}/{len(request.rule_ids)} rules",
                        category="rules",
                        context="Bulk rule operation",
                        metadata={
                            "operation": request.operation,
                            "rule_ids": request.rule_ids,
                            "results": results,
                            "performed_by": current_user['username']
                        },
                        tags=["rules", "bulk", request.operation],
                        user_id=current_user['username']
                    )
                
                return {
                    "results": results,
                    "total": len(results),
                    "successful": len([r for r in results if r['success']]),
                    "failed": len([r for r in results if not r['success']])
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # ================= DELETE OPERATIONS =================
        
        @router.delete("/{rule_id}")
        async def delete_rule(
            rule_id: str, 
            hard_delete: bool = False,
            current_user: dict = Depends(self._get_current_user)
        ):
            """Delete a rule (soft delete by default)"""
            try:
                rule = self.db.get_rule(rule_id)
                if not rule:
                    raise HTTPException(status_code=404, detail="Rule not found")
                
                # Check for dependencies
                dependencies = self.db.get_rule_dependencies(rule_id)
                dependent_rules = [d for d in dependencies if d.depends_on_rule_id == rule_id]
                
                if dependent_rules and not hard_delete:
                    return {
                        "can_delete": False,
                        "dependencies": [self._dependency_to_dict(d) for d in dependent_rules],
                        "message": "Rule has dependencies. Use hard_delete=true to force deletion."
                    }
                
                # Perform deletion
                success = self.db.delete_rule(rule_id, current_user['username'], hard_delete)
                
                if not success:
                    raise HTTPException(status_code=500, detail="Failed to delete rule")
                
                # Store in hAIveMind memory
                await self._store_rule_memory(rule, "deleted", current_user['username'])
                
                return {
                    "rule_id": rule_id,
                    "hard_delete": hard_delete,
                    "message": f"Rule {'permanently deleted' if hard_delete else 'soft deleted'} successfully"
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/conflicts/{conflict_id}/resolve")
        async def resolve_rule_conflict(
            conflict_id: str,
            request: RuleConflictResolutionRequest,
            current_user: dict = Depends(self._get_current_user)
        ):
            """Resolve a rule conflict"""
            try:
                # Get conflict details
                conflict = self.conflict_cache.get(conflict_id)
                if not conflict:
                    raise HTTPException(status_code=404, detail="Conflict not found")
                
                # Apply resolution
                resolution_result = await self.validator.resolve_conflict(
                    conflict,
                    request.resolution_strategy,
                    request.selected_rule_id,
                    current_user['username']
                )
                
                # Store resolution in hAIveMind memory
                if self.memory_storage:
                    await self.memory_storage.store_memory(
                        content=f"Resolved rule conflict using {request.resolution_strategy} strategy",
                        category="rules",
                        context="Rule conflict resolution",
                        metadata={
                            "conflict_id": conflict_id,
                            "resolution_strategy": request.resolution_strategy,
                            "selected_rule_id": request.selected_rule_id,
                            "resolved_by": current_user['username'],
                            "resolution_result": resolution_result
                        },
                        tags=["rules", "conflict", "resolution"],
                        user_id=current_user['username']
                    )
                
                return {
                    "conflict_id": conflict_id,
                    "resolution": resolution_result,
                    "message": "Conflict resolved successfully"
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # ================= ASSIGNMENT OPERATIONS =================
        
        @router.post("/assignments")
        async def assign_rule(request: RuleAssignmentRequest, current_user: dict = Depends(self._get_current_user)):
            """Assign a rule to a specific scope"""
            try:
                effective_from = datetime.fromisoformat(request.effective_from) if request.effective_from else None
                effective_until = datetime.fromisoformat(request.effective_until) if request.effective_until else None
                
                assignment_id = self.db.assign_rule_to_scope(
                    request.rule_id,
                    request.scope_type,
                    request.scope_id,
                    request.priority_override,
                    effective_from,
                    effective_until
                )
                
                return {
                    "assignment_id": assignment_id,
                    "message": "Rule assigned successfully"
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # ================= EXPORT OPERATIONS =================
        
        @router.get("/export")
        async def export_rules(
            format: str = "yaml",
            rule_ids: Optional[str] = None,
            include_history: bool = False,
            current_user: dict = Depends(self._get_current_user)
        ):
            """Export rules in YAML or JSON format"""
            try:
                rule_id_list = rule_ids.split(',') if rule_ids else None
                
                export_data = self.db.export_rules(
                    format=format,
                    rule_ids=rule_id_list,
                    include_history=include_history
                )
                
                # Store export activity in hAIveMind memory
                if self.memory_storage:
                    await self.memory_storage.store_memory(
                        content=f"Exported rules in {format} format",
                        category="rules",
                        context="Rule export operation",
                        metadata={
                            "format": format,
                            "rule_ids": rule_id_list,
                            "include_history": include_history,
                            "exported_by": current_user['username']
                        },
                        tags=["rules", "export", format],
                        user_id=current_user['username']
                    )
                
                return {
                    "data": export_data,
                    "format": format,
                    "exported_at": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        return router
    
    # ================= HELPER METHODS =================
    
    def _get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))) -> dict:
        """Get current authenticated user (placeholder - implement based on your auth system)"""
        # This should be implemented based on your authentication system
        return {
            'user_id': 'system',
            'username': 'system',
            'role': 'admin'
        }
    
    def _rule_to_dict(self, rule: Rule) -> Dict[str, Any]:
        """Convert Rule object to dictionary"""
        return {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "rule_type": rule.rule_type.value,
            "scope": rule.scope.value,
            "priority": rule.priority.value,
            "status": rule.status.value,
            "conditions": [{"field": c.field, "operator": c.operator, "value": c.value, "case_sensitive": c.case_sensitive} for c in rule.conditions],
            "actions": [{"action_type": a.action_type, "target": a.target, "value": a.value, "parameters": a.parameters} for a in rule.actions],
            "tags": rule.tags,
            "created_at": rule.created_at.isoformat(),
            "created_by": rule.created_by,
            "updated_at": rule.updated_at.isoformat(),
            "updated_by": rule.updated_by,
            "version": rule.version,
            "parent_rule_id": rule.parent_rule_id,
            "conflict_resolution": rule.conflict_resolution.value,
            "effective_from": rule.effective_from.isoformat() if hasattr(rule, 'effective_from') and rule.effective_from else None,
            "effective_until": rule.effective_until.isoformat() if hasattr(rule, 'effective_until') and rule.effective_until else None,
            "metadata": rule.metadata
        }
    
    def _template_to_dict(self, template: RuleTemplate) -> Dict[str, Any]:
        """Convert RuleTemplate object to dictionary"""
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "rule_type": template.rule_type.value,
            "template_data": template.template_data,
            "category": template.category,
            "tags": template.tags,
            "created_by": template.created_by,
            "created_at": template.created_at.isoformat(),
            "metadata": template.metadata
        }
    
    def _version_to_dict(self, version: RuleVersion) -> Dict[str, Any]:
        """Convert RuleVersion object to dictionary"""
        return {
            "id": version.id,
            "rule_id": version.rule_id,
            "version": version.version,
            "change_type": version.change_type.value,
            "rule_data": version.rule_data,
            "changed_by": version.changed_by,
            "changed_at": version.changed_at.isoformat(),
            "change_reason": version.change_reason,
            "metadata": version.metadata
        }
    
    def _dependency_to_dict(self, dependency: RuleDependency) -> Dict[str, Any]:
        """Convert RuleDependency object to dictionary"""
        return {
            "id": dependency.id,
            "rule_id": dependency.rule_id,
            "depends_on_rule_id": dependency.depends_on_rule_id,
            "dependency_type": dependency.dependency_type,
            "created_at": dependency.created_at.isoformat(),
            "metadata": dependency.metadata
        }
    
    def _assignment_to_dict(self, assignment: RuleAssignment) -> Dict[str, Any]:
        """Convert RuleAssignment object to dictionary"""
        return {
            "id": assignment.id,
            "rule_id": assignment.rule_id,
            "scope_type": assignment.scope_type,
            "scope_id": assignment.scope_id,
            "priority_override": assignment.priority_override,
            "effective_from": assignment.effective_from.isoformat() if assignment.effective_from else None,
            "effective_until": assignment.effective_until.isoformat() if assignment.effective_until else None,
            "metadata": assignment.metadata
        }
    
    def _group_conflicts_by_type(self, conflicts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group conflicts by type for analytics"""
        conflict_types = {}
        for conflict in conflicts:
            conflict_type = conflict.get('type', 'unknown')
            conflict_types[conflict_type] = conflict_types.get(conflict_type, 0) + 1
        return conflict_types
    
    async def _store_rule_memory(self, rule: Rule, action: str, user: str):
        """Store rule operation in hAIveMind memory"""
        if not self.memory_storage:
            return
        
        try:
            await self.memory_storage.store_memory(
                content=f"Rule '{rule.name}' was {action} by {user}",
                category="rules",
                context=f"Rule {action}: {rule.name}",
                metadata={
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "rule_type": rule.rule_type.value,
                    "scope": rule.scope.value,
                    "action": action,
                    "user": user,
                    "version": rule.version
                },
                tags=["rules", action, rule.rule_type.value],
                user_id=user
            )
        except Exception as e:
            # Don't fail the main operation if memory storage fails
            print(f"Failed to store rule memory: {e}")
    
    def _get_default_templates(self) -> Dict[str, str]:
        """Return default Jinja2 templates"""
        return {
            "rules_dashboard.html": """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rules Dashboard - hAIveMind</title>
    <style>
        /* Dashboard styles will be added here */
    </style>
</head>
<body>
    <div id="rules-dashboard">
        <!-- Dashboard content will be rendered here -->
    </div>
    <script>
        // Dashboard JavaScript will be added here
    </script>
</body>
</html>
""".strip()
        }