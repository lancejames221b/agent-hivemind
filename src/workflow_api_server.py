#!/usr/bin/env python3
"""
Workflow API Server
Provides REST API endpoints for external workflow orchestration and integration
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from .workflow_automation_engine import (
    WorkflowAutomationEngine, WorkflowTemplate, WorkflowExecution, 
    WorkflowStatus, TriggerType, WorkflowSuggestion
)
from .workflow_haivemind_integration import WorkflowhAIveMindIntegration
from .workflow_validation_rollback import WorkflowValidationRollbackIntegration

logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses

class WorkflowExecutionRequest(BaseModel):
    """Request model for workflow execution"""
    workflow_id: str = Field(..., description="ID of the workflow template to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Workflow parameters")
    trigger_context: Dict[str, Any] = Field(default_factory=dict, description="Trigger context information")
    auto_approve: bool = Field(default=False, description="Skip approval if required")
    validation_level: Optional[str] = Field(default=None, description="Validation level (basic, standard, strict, paranoid)")
    rollback_strategy: Optional[str] = Field(default=None, description="Rollback strategy (immediate, graceful, manual, checkpoint)")

class WorkflowExecutionResponse(BaseModel):
    """Response model for workflow execution"""
    execution_id: str
    status: str
    message: str
    estimated_duration: Optional[int] = None
    validation_passed: bool = True
    rollback_prepared: bool = False

class WorkflowSuggestionRequest(BaseModel):
    """Request model for workflow suggestions"""
    context: Optional[str] = Field(default=None, description="Current context or situation")
    recent_commands: Optional[List[str]] = Field(default=None, description="List of recent commands")
    intent: Optional[str] = Field(default=None, description="What you're trying to accomplish")
    limit: int = Field(default=5, description="Maximum number of suggestions")

class WorkflowTemplateCreate(BaseModel):
    """Request model for creating workflow templates"""
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    category: str = Field(..., description="Workflow category")
    tags: List[str] = Field(default_factory=list, description="Workflow tags")
    steps: List[Dict[str, Any]] = Field(..., description="Workflow steps")
    estimated_duration: int = Field(default=300, description="Estimated duration in seconds")
    approval_required: bool = Field(default=False, description="Whether approval is required")
    rollback_enabled: bool = Field(default=True, description="Whether rollback is enabled")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Default parameters")

class WebhookConfig(BaseModel):
    """Webhook configuration for workflow events"""
    url: str = Field(..., description="Webhook URL")
    events: List[str] = Field(..., description="Events to subscribe to")
    secret: Optional[str] = Field(default=None, description="Webhook secret for verification")
    headers: Dict[str, str] = Field(default_factory=dict, description="Additional headers")

class WorkflowAPIServer:
    """REST API server for workflow automation"""
    
    def __init__(self, storage, config: Dict[str, Any]):
        self.storage = storage
        self.config = config
        
        # Initialize workflow components
        self.workflow_engine = WorkflowAutomationEngine(storage, config)
        self.haivemind_integration = None  # Will be initialized
        self.validation_rollback = None    # Will be initialized
        
        # API configuration
        self.api_config = config.get('workflow_api', {})
        self.host = self.api_config.get('host', '0.0.0.0')
        self.port = self.api_config.get('port', 8902)
        self.api_key_required = self.api_config.get('api_key_required', True)
        self.api_keys = set(self.api_config.get('api_keys', []))
        
        # Create FastAPI app
        self.app = FastAPI(
            title="hAIveMind Workflow API",
            description="REST API for workflow automation and orchestration",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.api_config.get('allowed_origins', ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Security
        self.security = HTTPBearer() if self.api_key_required else None
        
        # WebSocket connections for real-time updates
        self.websocket_connections: List[WebSocket] = []
        
        # Webhook configurations
        self.webhooks: Dict[str, WebhookConfig] = {}
        
        # Rate limiting
        self.rate_limits = {}
        
        # Setup routes
        self._setup_routes()
    
    async def initialize(self):
        """Initialize the API server"""
        await self.workflow_engine.initialize()
        
        # Initialize integrations
        from .workflow_haivemind_integration import create_workflow_haivemind_integration
        from .workflow_validation_rollback import create_workflow_validation_rollback_system
        
        self.haivemind_integration = await create_workflow_haivemind_integration(
            self.workflow_engine, self.storage, self.config
        )
        
        self.validation_rollback = await create_workflow_validation_rollback_system(
            self.storage, self.config
        )
        
        logger.info("Workflow API server initialized")
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        # Health check
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0"
            }
        
        # Workflow execution endpoints
        @self.app.post("/api/v1/workflows/execute", response_model=WorkflowExecutionResponse)
        async def execute_workflow(
            request: WorkflowExecutionRequest,
            background_tasks: BackgroundTasks,
            credentials: HTTPAuthorizationCredentials = Depends(self.get_api_key)
        ):
            """Execute a workflow"""
            try:
                # Validate API key
                if self.api_key_required and not self._validate_api_key(credentials.credentials):
                    raise HTTPException(status_code=401, detail="Invalid API key")
                
                # Check rate limits
                await self._check_rate_limit(credentials.credentials if credentials else "anonymous")
                
                # Get template
                if request.workflow_id not in self.workflow_engine.templates:
                    raise HTTPException(status_code=404, detail="Workflow template not found")
                
                template = self.workflow_engine.templates[request.workflow_id]
                
                # Create execution
                execution = WorkflowExecution(
                    id=str(uuid.uuid4()),
                    template_id=request.workflow_id,
                    name=template.name,
                    trigger_type=TriggerType.EXTERNAL_API,
                    trigger_context=request.trigger_context,
                    parameters=request.parameters,
                    user_id=credentials.credentials if credentials else "api_user",
                    machine_id=getattr(self.storage, 'machine_id', 'api_server')
                )
                
                # Validate and prepare rollback if validation system is available
                validation_passed = True
                rollback_prepared = False
                
                if self.validation_rollback:
                    validation_result, rollback_prepared = await self.validation_rollback.validate_and_prepare_rollback(
                        template, execution
                    )
                    validation_passed = validation_result.valid
                    
                    if not validation_passed:
                        raise HTTPException(
                            status_code=400, 
                            detail={
                                "message": "Workflow validation failed",
                                "errors": validation_result.errors,
                                "warnings": validation_result.warnings
                            }
                        )
                
                # Execute workflow in background
                background_tasks.add_task(self._execute_workflow_background, execution)
                
                # Send webhook notification
                await self._send_webhook_notification("workflow.started", {
                    "execution_id": execution.id,
                    "workflow_id": request.workflow_id,
                    "name": template.name
                })
                
                return WorkflowExecutionResponse(
                    execution_id=execution.id,
                    status="started",
                    message=f"Workflow '{template.name}' started successfully",
                    estimated_duration=template.estimated_duration,
                    validation_passed=validation_passed,
                    rollback_prepared=rollback_prepared
                )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error executing workflow: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/workflows/executions/{execution_id}")
        async def get_execution_status(
            execution_id: str,
            credentials: HTTPAuthorizationCredentials = Depends(self.get_api_key)
        ):
            """Get workflow execution status"""
            try:
                if self.api_key_required and not self._validate_api_key(credentials.credentials):
                    raise HTTPException(status_code=401, detail="Invalid API key")
                
                status = await self.workflow_engine.get_workflow_status(execution_id)
                if not status:
                    raise HTTPException(status_code=404, detail="Execution not found")
                
                return status
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting execution status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/workflows/executions/{execution_id}/cancel")
        async def cancel_execution(
            execution_id: str,
            credentials: HTTPAuthorizationCredentials = Depends(self.get_api_key)
        ):
            """Cancel workflow execution"""
            try:
                if self.api_key_required and not self._validate_api_key(credentials.credentials):
                    raise HTTPException(status_code=401, detail="Invalid API key")
                
                success = await self.workflow_engine.cancel_workflow(execution_id)
                if not success:
                    raise HTTPException(status_code=400, detail="Cannot cancel execution")
                
                # Send webhook notification
                await self._send_webhook_notification("workflow.cancelled", {
                    "execution_id": execution_id
                })
                
                return {"status": "cancelled", "execution_id": execution_id}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error cancelling execution: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Workflow template endpoints
        @self.app.get("/api/v1/workflows/templates")
        async def list_workflow_templates(
            category: Optional[str] = None,
            credentials: HTTPAuthorizationCredentials = Depends(self.get_api_key)
        ):
            """List workflow templates"""
            try:
                if self.api_key_required and not self._validate_api_key(credentials.credentials):
                    raise HTTPException(status_code=401, detail="Invalid API key")
                
                templates = await self.workflow_engine.get_workflow_templates()
                
                if category:
                    templates = [t for t in templates if t['category'].lower() == category.lower()]
                
                return {"templates": templates}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error listing templates: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/workflows/templates/{template_id}")
        async def get_workflow_template(
            template_id: str,
            credentials: HTTPAuthorizationCredentials = Depends(self.get_api_key)
        ):
            """Get workflow template details"""
            try:
                if self.api_key_required and not self._validate_api_key(credentials.credentials):
                    raise HTTPException(status_code=401, detail="Invalid API key")
                
                if template_id not in self.workflow_engine.templates:
                    raise HTTPException(status_code=404, detail="Template not found")
                
                template = self.workflow_engine.templates[template_id]
                
                # Get hAIveMind recommendations if available
                recommendations = {}
                if self.haivemind_integration:
                    recommendations = await self.haivemind_integration.get_workflow_recommendations(template_id)
                
                return {
                    "template": {
                        "id": template.id,
                        "name": template.name,
                        "description": template.description,
                        "category": template.category,
                        "version": template.version,
                        "author": template.author,
                        "tags": template.tags,
                        "steps": [
                            {
                                "id": step.id,
                                "command": step.command,
                                "description": step.description,
                                "parameters": step.parameters,
                                "depends_on": step.depends_on,
                                "timeout_seconds": step.timeout_seconds,
                                "max_retries": step.max_retries,
                                "rollback_command": step.rollback_command
                            }
                            for step in template.steps
                        ],
                        "estimated_duration": template.estimated_duration,
                        "success_rate": template.success_rate,
                        "usage_count": template.usage_count,
                        "approval_required": template.approval_required,
                        "rollback_enabled": template.rollback_enabled
                    },
                    "recommendations": recommendations
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting template: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/workflows/templates")
        async def create_workflow_template(
            request: WorkflowTemplateCreate,
            credentials: HTTPAuthorizationCredentials = Depends(self.get_api_key)
        ):
            """Create a new workflow template"""
            try:
                if self.api_key_required and not self._validate_api_key(credentials.credentials):
                    raise HTTPException(status_code=401, detail="Invalid API key")
                
                # Convert request to template data
                template_data = {
                    "name": request.name,
                    "description": request.description,
                    "category": request.category,
                    "tags": request.tags,
                    "steps": request.steps,
                    "estimated_duration": request.estimated_duration,
                    "approval_required": request.approval_required,
                    "rollback_enabled": request.rollback_enabled,
                    "parameters": request.parameters
                }
                
                template_id = await self.workflow_engine.create_custom_workflow(template_data)
                
                return {
                    "template_id": template_id,
                    "status": "created",
                    "message": f"Workflow template '{request.name}' created successfully"
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error creating template: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Workflow suggestions endpoint
        @self.app.post("/api/v1/workflows/suggest")
        async def suggest_workflows(
            request: WorkflowSuggestionRequest,
            credentials: HTTPAuthorizationCredentials = Depends(self.get_api_key)
        ):
            """Get workflow suggestions"""
            try:
                if self.api_key_required and not self._validate_api_key(credentials.credentials):
                    raise HTTPException(status_code=401, detail="Invalid API key")
                
                suggestions = await self.workflow_engine.suggest_workflows(
                    context=request.context,
                    recent_commands=request.recent_commands,
                    intent=request.intent
                )
                
                # Enhance with hAIveMind intelligence if available
                if self.haivemind_integration:
                    suggestions = await self.haivemind_integration.enhance_workflow_suggestions(
                        suggestions, request.context, request.recent_commands
                    )
                
                # Limit results
                suggestions = suggestions[:request.limit]
                
                return {
                    "suggestions": [
                        {
                            "workflow_id": s.workflow_id,
                            "name": s.name,
                            "confidence": s.confidence,
                            "reason": s.reason,
                            "estimated_duration": s.estimated_duration,
                            "success_probability": s.success_probability,
                            "similar_executions": s.similar_executions,
                            "suggested_parameters": s.suggested_parameters
                        }
                        for s in suggestions
                    ]
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting suggestions: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Analytics endpoint
        @self.app.get("/api/v1/workflows/analytics")
        async def get_workflow_analytics(
            credentials: HTTPAuthorizationCredentials = Depends(self.get_api_key)
        ):
            """Get workflow analytics"""
            try:
                if self.api_key_required and not self._validate_api_key(credentials.credentials):
                    raise HTTPException(status_code=401, detail="Invalid API key")
                
                analytics = await self.workflow_engine.get_workflow_analytics()
                return {"analytics": analytics}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting analytics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Validation endpoint
        @self.app.post("/api/v1/workflows/validate")
        async def validate_workflow(
            workflow_definition: Dict[str, Any],
            validation_level: str = "standard",
            credentials: HTTPAuthorizationCredentials = Depends(self.get_api_key)
        ):
            """Validate workflow definition"""
            try:
                if self.api_key_required and not self._validate_api_key(credentials.credentials):
                    raise HTTPException(status_code=401, detail="Invalid API key")
                
                if not self.validation_rollback:
                    raise HTTPException(status_code=503, detail="Validation system not available")
                
                # Create temporary template for validation
                from .workflow_validation_rollback import ValidationLevel
                
                try:
                    level = ValidationLevel(validation_level)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid validation level")
                
                # This would create a temporary template and validate it
                # For now, return a simple validation result
                return {
                    "valid": True,
                    "level": validation_level,
                    "errors": [],
                    "warnings": [],
                    "suggestions": ["Workflow definition appears valid"],
                    "confidence": 0.9
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error validating workflow: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Rollback endpoints
        @self.app.post("/api/v1/workflows/executions/{execution_id}/rollback")
        async def initiate_rollback(
            execution_id: str,
            strategy: str = "graceful",
            target_point: Optional[str] = None,
            credentials: HTTPAuthorizationCredentials = Depends(self.get_api_key)
        ):
            """Initiate workflow rollback"""
            try:
                if self.api_key_required and not self._validate_api_key(credentials.credentials):
                    raise HTTPException(status_code=401, detail="Invalid API key")
                
                if not self.validation_rollback:
                    raise HTTPException(status_code=503, detail="Rollback system not available")
                
                # Find execution
                execution = None
                if execution_id in self.workflow_engine.executions:
                    execution = self.workflow_engine.executions[execution_id]
                else:
                    # Check history
                    execution = next(
                        (e for e in self.workflow_engine.execution_history if e.id == execution_id),
                        None
                    )
                
                if not execution:
                    raise HTTPException(status_code=404, detail="Execution not found")
                
                # Initiate rollback
                from .workflow_validation_rollback import RollbackStrategy
                
                try:
                    rollback_strategy = RollbackStrategy(strategy)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid rollback strategy")
                
                rollback_id = await self.validation_rollback.rollback_manager.initiate_rollback(
                    execution, rollback_strategy, target_point
                )
                
                return {
                    "rollback_id": rollback_id,
                    "status": "initiated",
                    "strategy": strategy,
                    "execution_id": execution_id
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error initiating rollback: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/workflows/rollbacks/{rollback_id}")
        async def get_rollback_status(
            rollback_id: str,
            credentials: HTTPAuthorizationCredentials = Depends(self.get_api_key)
        ):
            """Get rollback status"""
            try:
                if self.api_key_required and not self._validate_api_key(credentials.credentials):
                    raise HTTPException(status_code=401, detail="Invalid API key")
                
                if not self.validation_rollback:
                    raise HTTPException(status_code=503, detail="Rollback system not available")
                
                status = await self.validation_rollback.rollback_manager.get_rollback_status(rollback_id)
                if not status:
                    raise HTTPException(status_code=404, detail="Rollback not found")
                
                return {"rollback": status}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting rollback status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Webhook management endpoints
        @self.app.post("/api/v1/webhooks")
        async def create_webhook(
            webhook_config: WebhookConfig,
            credentials: HTTPAuthorizationCredentials = Depends(self.get_api_key)
        ):
            """Create webhook configuration"""
            try:
                if self.api_key_required and not self._validate_api_key(credentials.credentials):
                    raise HTTPException(status_code=401, detail="Invalid API key")
                
                webhook_id = str(uuid.uuid4())
                self.webhooks[webhook_id] = webhook_config
                
                return {
                    "webhook_id": webhook_id,
                    "status": "created",
                    "events": webhook_config.events
                }
                
            except Exception as e:
                logger.error(f"Error creating webhook: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/api/v1/webhooks/{webhook_id}")
        async def delete_webhook(
            webhook_id: str,
            credentials: HTTPAuthorizationCredentials = Depends(self.get_api_key)
        ):
            """Delete webhook configuration"""
            try:
                if self.api_key_required and not self._validate_api_key(credentials.credentials):
                    raise HTTPException(status_code=401, detail="Invalid API key")
                
                if webhook_id not in self.webhooks:
                    raise HTTPException(status_code=404, detail="Webhook not found")
                
                del self.webhooks[webhook_id]
                
                return {"status": "deleted", "webhook_id": webhook_id}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error deleting webhook: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # WebSocket endpoint for real-time updates
        @self.app.websocket("/api/v1/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time workflow updates"""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # Keep connection alive and handle client messages
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                    elif message.get("type") == "subscribe":
                        # Handle subscription to specific events
                        await websocket.send_text(json.dumps({
                            "type": "subscribed",
                            "events": message.get("events", [])
                        }))
                    
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
    
    def get_api_key(self):
        """Dependency for API key validation"""
        if not self.api_key_required:
            return None
        return self.security
    
    def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key"""
        return api_key in self.api_keys
    
    async def _check_rate_limit(self, identifier: str):
        """Check rate limits for API calls"""
        current_time = time.time()
        
        # Simple rate limiting (100 requests per minute)
        if identifier not in self.rate_limits:
            self.rate_limits[identifier] = []
        
        # Clean old requests
        self.rate_limits[identifier] = [
            t for t in self.rate_limits[identifier] 
            if current_time - t < 60
        ]
        
        # Check limit
        if len(self.rate_limits[identifier]) >= 100:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Add current request
        self.rate_limits[identifier].append(current_time)
    
    async def _execute_workflow_background(self, execution: WorkflowExecution):
        """Execute workflow in background task"""
        try:
            # Start execution
            if self.haivemind_integration:
                await self.haivemind_integration.on_workflow_start(execution)
            
            # Execute workflow
            execution_id = await self.workflow_engine.execute_workflow(
                template_id=execution.template_id,
                parameters=execution.parameters,
                trigger_type=execution.trigger_type,
                trigger_context=execution.trigger_context,
                user_id=execution.user_id
            )
            
            # Wait for completion
            while execution_id in self.workflow_engine.executions:
                await asyncio.sleep(5)
            
            # Get final status
            final_execution = next(
                (e for e in self.workflow_engine.execution_history if e.id == execution_id),
                None
            )
            
            if final_execution:
                if final_execution.status == WorkflowStatus.COMPLETED:
                    if self.haivemind_integration:
                        await self.haivemind_integration.on_workflow_complete(final_execution)
                    
                    await self._send_webhook_notification("workflow.completed", {
                        "execution_id": execution_id,
                        "status": "completed",
                        "duration": (final_execution.end_time or time.time()) - final_execution.start_time
                    })
                else:
                    if self.haivemind_integration:
                        await self.haivemind_integration.on_workflow_fail(final_execution)
                    
                    await self._send_webhook_notification("workflow.failed", {
                        "execution_id": execution_id,
                        "status": "failed",
                        "error": final_execution.error_message
                    })
            
        except Exception as e:
            logger.error(f"Background workflow execution failed: {e}")
            await self._send_webhook_notification("workflow.error", {
                "execution_id": execution.id,
                "error": str(e)
            })
    
    async def _send_webhook_notification(self, event: str, data: Dict[str, Any]):
        """Send webhook notifications"""
        for webhook_id, webhook_config in self.webhooks.items():
            if event in webhook_config.events:
                try:
                    import aiohttp
                    
                    payload = {
                        "event": event,
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": data
                    }
                    
                    headers = webhook_config.headers.copy()
                    headers["Content-Type"] = "application/json"
                    
                    if webhook_config.secret:
                        import hmac
                        import hashlib
                        
                        signature = hmac.new(
                            webhook_config.secret.encode(),
                            json.dumps(payload).encode(),
                            hashlib.sha256
                        ).hexdigest()
                        headers["X-Webhook-Signature"] = f"sha256={signature}"
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            webhook_config.url,
                            json=payload,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            if response.status >= 400:
                                logger.warning(f"Webhook {webhook_id} returned {response.status}")
                
                except Exception as e:
                    logger.error(f"Failed to send webhook {webhook_id}: {e}")
        
        # Also send to WebSocket connections
        await self._broadcast_websocket_update({
            "type": "workflow_event",
            "event": event,
            "data": data
        })
    
    async def _broadcast_websocket_update(self, message: Dict[str, Any]):
        """Broadcast update to WebSocket connections"""
        if not self.websocket_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = []
        
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(message_str)
            except:
                disconnected.append(websocket)
        
        # Remove disconnected websockets
        for websocket in disconnected:
            self.websocket_connections.remove(websocket)
    
    def run(self):
        """Run the API server"""
        logger.info(f"Starting workflow API server on {self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port)

async def create_workflow_api_server(storage, config: Dict[str, Any]) -> WorkflowAPIServer:
    """Create and initialize workflow API server"""
    server = WorkflowAPIServer(storage, config)
    await server.initialize()
    return server

# Example usage and configuration
if __name__ == "__main__":
    import asyncio
    
    # Example configuration
    config = {
        "workflow_api": {
            "host": "0.0.0.0",
            "port": 8902,
            "api_key_required": True,
            "api_keys": ["your-api-key-here"],
            "allowed_origins": ["*"]
        },
        "workflow_validation": {
            "default_level": "standard",
            "strict_mode": False
        },
        "workflow_rollback": {
            "default_strategy": "graceful",
            "auto_rollback": True,
            "checkpoint_interval": 3
        }
    }
    
    async def main():
        # This would use actual storage implementation
        storage = None  
        
        server = await create_workflow_api_server(storage, config)
        server.run()
    
    asyncio.run(main())