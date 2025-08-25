#!/usr/bin/env python3
"""
Workflow Management Dashboard
Visual interface for workflow automation and management
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from .workflow_automation_engine import WorkflowAutomationEngine, WorkflowStatus, TriggerType

logger = logging.getLogger(__name__)

class WorkflowDashboard:
    """Web dashboard for workflow management"""
    
    def __init__(self, storage, config: Dict[str, Any]):
        self.storage = storage
        self.config = config
        self.workflow_engine = WorkflowAutomationEngine(storage, config)
        
        # FastAPI app
        self.app = FastAPI(title="hAIveMind Workflow Dashboard", version="1.0.0")
        
        # WebSocket connections for real-time updates
        self.websocket_connections: List[WebSocket] = []
        
        # Setup routes
        self._setup_routes()
        
        # Dashboard data cache
        self._dashboard_cache = {}
        self._cache_expiry = 0
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home(request: Request):
            """Main dashboard page"""
            return await self._render_dashboard(request)
        
        @self.app.get("/api/workflows", response_class=JSONResponse)
        async def get_workflows():
            """Get all workflow templates"""
            await self._ensure_initialized()
            templates = await self.workflow_engine.get_workflow_templates()
            return {"workflows": templates}
        
        @self.app.get("/api/workflows/{workflow_id}", response_class=JSONResponse)
        async def get_workflow_details(workflow_id: str):
            """Get detailed workflow template information"""
            await self._ensure_initialized()
            
            if workflow_id not in self.workflow_engine.templates:
                raise HTTPException(status_code=404, detail="Workflow not found")
            
            template = self.workflow_engine.templates[workflow_id]
            return {
                "workflow": {
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
                            "parallel_group": step.parallel_group,
                            "timeout_seconds": step.timeout_seconds,
                            "max_retries": step.max_retries
                        }
                        for step in template.steps
                    ],
                    "estimated_duration": template.estimated_duration,
                    "success_rate": template.success_rate,
                    "usage_count": template.usage_count,
                    "approval_required": template.approval_required,
                    "rollback_enabled": template.rollback_enabled
                }
            }
        
        @self.app.post("/api/workflows/{workflow_id}/execute")
        async def execute_workflow(workflow_id: str, request: Request):
            """Execute a workflow"""
            await self._ensure_initialized()
            
            body = await request.json()
            parameters = body.get("parameters", {})
            auto_approve = body.get("auto_approve", False)
            
            try:
                execution_id = await self.workflow_engine.execute_workflow(
                    template_id=workflow_id,
                    parameters=parameters,
                    trigger_type=TriggerType.MANUAL,
                    trigger_context={"source": "dashboard", "auto_approve": auto_approve}
                )
                
                # Notify WebSocket clients
                await self._broadcast_update({
                    "type": "workflow_started",
                    "execution_id": execution_id,
                    "workflow_id": workflow_id
                })
                
                return {"execution_id": execution_id, "status": "started"}
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/executions", response_class=JSONResponse)
        async def get_executions():
            """Get all workflow executions"""
            await self._ensure_initialized()
            
            active_executions = []
            for execution in self.workflow_engine.executions.values():
                status = await self.workflow_engine.get_workflow_status(execution.id)
                if status:
                    active_executions.append(status)
            
            recent_history = []
            for execution in self.workflow_engine.execution_history[-20:]:
                status = await self.workflow_engine.get_workflow_status(execution.id)
                if status:
                    recent_history.append(status)
            
            return {
                "active_executions": active_executions,
                "recent_history": recent_history
            }
        
        @self.app.get("/api/executions/{execution_id}", response_class=JSONResponse)
        async def get_execution_status(execution_id: str):
            """Get detailed execution status"""
            await self._ensure_initialized()
            
            status = await self.workflow_engine.get_workflow_status(execution_id)
            if not status:
                raise HTTPException(status_code=404, detail="Execution not found")
            
            return {"execution": status}
        
        @self.app.post("/api/executions/{execution_id}/cancel")
        async def cancel_execution(execution_id: str):
            """Cancel a workflow execution"""
            await self._ensure_initialized()
            
            success = await self.workflow_engine.cancel_workflow(execution_id)
            if not success:
                raise HTTPException(status_code=400, detail="Cannot cancel execution")
            
            # Notify WebSocket clients
            await self._broadcast_update({
                "type": "workflow_cancelled",
                "execution_id": execution_id
            })
            
            return {"status": "cancelled"}
        
        @self.app.get("/api/suggestions", response_class=JSONResponse)
        async def get_workflow_suggestions(context: Optional[str] = None,
                                         recent_commands: Optional[str] = None,
                                         intent: Optional[str] = None):
            """Get workflow suggestions"""
            await self._ensure_initialized()
            
            recent_cmd_list = []
            if recent_commands:
                recent_cmd_list = [cmd.strip() for cmd in recent_commands.split(',')]
            
            suggestions = await self.workflow_engine.suggest_workflows(
                context=context,
                recent_commands=recent_cmd_list,
                intent=intent
            )
            
            return {
                "suggestions": [
                    {
                        "workflow_id": s.workflow_id,
                        "name": s.name,
                        "confidence": s.confidence,
                        "reason": s.reason,
                        "estimated_duration": s.estimated_duration,
                        "success_probability": s.success_probability
                    }
                    for s in suggestions
                ]
            }
        
        @self.app.post("/api/workflows")
        async def create_workflow(request: Request):
            """Create a custom workflow"""
            await self._ensure_initialized()
            
            workflow_data = await request.json()
            
            try:
                template_id = await self.workflow_engine.create_custom_workflow(workflow_data)
                return {"template_id": template_id, "status": "created"}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/analytics", response_class=JSONResponse)
        async def get_analytics():
            """Get workflow analytics"""
            await self._ensure_initialized()
            
            analytics = await self.workflow_engine.get_workflow_analytics()
            return {"analytics": analytics}
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # Keep connection alive and handle client messages
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                    
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
    
    async def _ensure_initialized(self):
        """Ensure workflow engine is initialized"""
        if not hasattr(self.workflow_engine, '_initialized') or not self.workflow_engine._initialized:
            await self.workflow_engine.initialize()
            self.workflow_engine._initialized = True
    
    async def _render_dashboard(self, request: Request) -> str:
        """Render the main dashboard HTML"""
        # Get dashboard data
        dashboard_data = await self._get_dashboard_data()
        
        # Generate HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>hAIveMind Workflow Dashboard</title>
    <style>
        {self._get_dashboard_css()}
    </style>
</head>
<body>
    <div class="dashboard">
        <header class="dashboard-header">
            <h1>🤖 hAIveMind Workflow Dashboard</h1>
            <div class="status-indicators">
                <div class="status-item">
                    <span class="status-label">Active Workflows:</span>
                    <span class="status-value" id="active-count">{dashboard_data['active_executions']}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Success Rate:</span>
                    <span class="status-value" id="success-rate">{dashboard_data['success_rate']:.0%}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Templates:</span>
                    <span class="status-value" id="template-count">{dashboard_data['total_templates']}</span>
                </div>
            </div>
        </header>
        
        <div class="dashboard-content">
            <div class="sidebar">
                <div class="sidebar-section">
                    <h3>Quick Actions</h3>
                    <button class="action-btn" onclick="showWorkflowSuggestions()">
                        🎯 Get Suggestions
                    </button>
                    <button class="action-btn" onclick="showCreateWorkflow()">
                        ➕ Create Workflow
                    </button>
                    <button class="action-btn" onclick="refreshDashboard()">
                        🔄 Refresh
                    </button>
                </div>
                
                <div class="sidebar-section">
                    <h3>Categories</h3>
                    <div class="category-filters">
                        <button class="filter-btn active" onclick="filterByCategory('all')">All</button>
                        <button class="filter-btn" onclick="filterByCategory('incident_management')">Incidents</button>
                        <button class="filter-btn" onclick="filterByCategory('security')">Security</button>
                        <button class="filter-btn" onclick="filterByCategory('maintenance')">Maintenance</button>
                        <button class="filter-btn" onclick="filterByCategory('custom')">Custom</button>
                    </div>
                </div>
            </div>
            
            <div class="main-content">
                <div class="content-tabs">
                    <button class="tab-btn active" onclick="showTab('workflows')">Workflows</button>
                    <button class="tab-btn" onclick="showTab('executions')">Executions</button>
                    <button class="tab-btn" onclick="showTab('analytics')">Analytics</button>
                </div>
                
                <div id="workflows-tab" class="tab-content active">
                    <div class="workflows-grid" id="workflows-grid">
                        <!-- Workflows will be loaded here -->
                    </div>
                </div>
                
                <div id="executions-tab" class="tab-content">
                    <div class="executions-list" id="executions-list">
                        <!-- Executions will be loaded here -->
                    </div>
                </div>
                
                <div id="analytics-tab" class="tab-content">
                    <div class="analytics-dashboard" id="analytics-dashboard">
                        <!-- Analytics will be loaded here -->
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Modals -->
    <div id="modal-overlay" class="modal-overlay" onclick="closeModal()">
        <div class="modal" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h3 id="modal-title">Modal Title</h3>
                <button class="close-btn" onclick="closeModal()">×</button>
            </div>
            <div class="modal-content" id="modal-content">
                <!-- Modal content will be loaded here -->
            </div>
        </div>
    </div>
    
    <script>
        {self._get_dashboard_javascript()}
    </script>
</body>
</html>
        """
        
        return html_content
    
    def _get_dashboard_css(self) -> str:
        """Get CSS styles for the dashboard"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .dashboard {
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        
        .dashboard-header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
        }
        
        .dashboard-header h1 {
            color: #4a5568;
            font-size: 1.8rem;
            font-weight: 600;
        }
        
        .status-indicators {
            display: flex;
            gap: 2rem;
        }
        
        .status-item {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        
        .status-label {
            font-size: 0.8rem;
            color: #718096;
            margin-bottom: 0.25rem;
        }
        
        .status-value {
            font-size: 1.2rem;
            font-weight: 600;
            color: #2d3748;
        }
        
        .dashboard-content {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        
        .sidebar {
            width: 280px;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            padding: 1.5rem;
            overflow-y: auto;
        }
        
        .sidebar-section {
            margin-bottom: 2rem;
        }
        
        .sidebar-section h3 {
            color: #4a5568;
            margin-bottom: 1rem;
            font-size: 1.1rem;
        }
        
        .action-btn {
            display: block;
            width: 100%;
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        .category-filters {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .filter-btn {
            padding: 0.5rem;
            background: transparent;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .filter-btn:hover, .filter-btn.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        
        .main-content {
            flex: 1;
            padding: 1.5rem;
            overflow-y: auto;
        }
        
        .content-tabs {
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .tab-btn {
            padding: 0.75rem 1.5rem;
            background: rgba(255, 255, 255, 0.7);
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s;
        }
        
        .tab-btn:hover, .tab-btn.active {
            background: rgba(255, 255, 255, 0.95);
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .workflows-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 1.5rem;
        }
        
        .workflow-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .workflow-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
        }
        
        .workflow-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }
        
        .workflow-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 0.5rem;
        }
        
        .workflow-category {
            background: #667eea;
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.8rem;
        }
        
        .workflow-description {
            color: #718096;
            margin-bottom: 1rem;
            line-height: 1.5;
        }
        
        .workflow-stats {
            display: flex;
            justify-content: space-between;
            margin-bottom: 1rem;
            font-size: 0.9rem;
        }
        
        .stat-item {
            text-align: center;
        }
        
        .stat-value {
            font-weight: 600;
            color: #2d3748;
        }
        
        .stat-label {
            color: #718096;
            font-size: 0.8rem;
        }
        
        .workflow-actions {
            display: flex;
            gap: 0.5rem;
        }
        
        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
        }
        
        .btn-primary {
            background: #667eea;
            color: white;
        }
        
        .btn-secondary {
            background: #e2e8f0;
            color: #4a5568;
        }
        
        .btn:hover {
            transform: translateY(-1px);
        }
        
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .modal-overlay.active {
            display: flex;
        }
        
        .modal {
            background: white;
            border-radius: 12px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.5rem;
            border-bottom: 1px solid #e2e8f0;
        }
        
        .close-btn {
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: #718096;
        }
        
        .modal-content {
            padding: 1.5rem;
        }
        
        .execution-item {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .execution-info h4 {
            color: #2d3748;
            margin-bottom: 0.5rem;
        }
        
        .execution-status {
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        .status-running {
            background: #fef5e7;
            color: #d69e2e;
        }
        
        .status-completed {
            background: #f0fff4;
            color: #38a169;
        }
        
        .status-failed {
            background: #fed7d7;
            color: #e53e3e;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
            margin: 0.5rem 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s ease;
        }
        """
    
    def _get_dashboard_javascript(self) -> str:
        """Get JavaScript for the dashboard"""
        return """
        let ws = null;
        let currentFilter = 'all';
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            initWebSocket();
            loadWorkflows();
            loadExecutions();
        });
        
        // WebSocket connection
        function initWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                console.log('WebSocket connected');
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };
            
            ws.onclose = function() {
                console.log('WebSocket disconnected, reconnecting...');
                setTimeout(initWebSocket, 3000);
            };
        }
        
        function handleWebSocketMessage(data) {
            if (data.type === 'workflow_started' || data.type === 'workflow_completed' || data.type === 'workflow_cancelled') {
                loadExecutions();
                updateStatusIndicators();
            }
        }
        
        // Tab management
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName + '-tab').classList.add('active');
            event.target.classList.add('active');
            
            // Load tab content
            if (tabName === 'workflows') {
                loadWorkflows();
            } else if (tabName === 'executions') {
                loadExecutions();
            } else if (tabName === 'analytics') {
                loadAnalytics();
            }
        }
        
        // Load workflows
        async function loadWorkflows() {
            try {
                const response = await fetch('/api/workflows');
                const data = await response.json();
                renderWorkflows(data.workflows);
            } catch (error) {
                console.error('Error loading workflows:', error);
            }
        }
        
        function renderWorkflows(workflows) {
            const grid = document.getElementById('workflows-grid');
            
            // Filter workflows
            const filteredWorkflows = currentFilter === 'all' 
                ? workflows 
                : workflows.filter(w => w.category === currentFilter);
            
            grid.innerHTML = filteredWorkflows.map(workflow => `
                <div class="workflow-card" data-category="${workflow.category}">
                    <div class="workflow-header">
                        <div>
                            <div class="workflow-title">${workflow.name}</div>
                            <div class="workflow-category">${workflow.category}</div>
                        </div>
                    </div>
                    <div class="workflow-description">${workflow.description}</div>
                    <div class="workflow-stats">
                        <div class="stat-item">
                            <div class="stat-value">${workflow.step_count}</div>
                            <div class="stat-label">Steps</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${Math.round(workflow.success_rate * 100)}%</div>
                            <div class="stat-label">Success</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${workflow.usage_count}</div>
                            <div class="stat-label">Uses</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${formatDuration(workflow.estimated_duration)}</div>
                            <div class="stat-label">Duration</div>
                        </div>
                    </div>
                    <div class="workflow-actions">
                        <button class="btn btn-primary" onclick="executeWorkflow('${workflow.id}')">
                            Execute
                        </button>
                        <button class="btn btn-secondary" onclick="showWorkflowDetails('${workflow.id}')">
                            Details
                        </button>
                    </div>
                </div>
            `).join('');
        }
        
        // Load executions
        async function loadExecutions() {
            try {
                const response = await fetch('/api/executions');
                const data = await response.json();
                renderExecutions(data.active_executions, data.recent_history);
            } catch (error) {
                console.error('Error loading executions:', error);
            }
        }
        
        function renderExecutions(activeExecutions, recentHistory) {
            const list = document.getElementById('executions-list');
            
            let html = '<h3>Active Executions</h3>';
            
            if (activeExecutions.length === 0) {
                html += '<p>No active executions</p>';
            } else {
                html += activeExecutions.map(execution => `
                    <div class="execution-item">
                        <div class="execution-info">
                            <h4>${execution.name}</h4>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${execution.progress * 100}%"></div>
                            </div>
                            <small>Step ${execution.completed_steps + 1} of ${execution.total_steps}</small>
                        </div>
                        <div>
                            <div class="execution-status status-${execution.status.toLowerCase()}">
                                ${execution.status}
                            </div>
                            <button class="btn btn-secondary" onclick="cancelExecution('${execution.execution_id}')">
                                Cancel
                            </button>
                        </div>
                    </div>
                `).join('');
            }
            
            html += '<h3>Recent History</h3>';
            html += recentHistory.map(execution => `
                <div class="execution-item">
                    <div class="execution-info">
                        <h4>${execution.name}</h4>
                        <small>Completed ${execution.completed_steps} of ${execution.total_steps} steps</small>
                    </div>
                    <div class="execution-status status-${execution.status.toLowerCase()}">
                        ${execution.status}
                    </div>
                </div>
            `).join('');
            
            list.innerHTML = html;
        }
        
        // Load analytics
        async function loadAnalytics() {
            try {
                const response = await fetch('/api/analytics');
                const data = await response.json();
                renderAnalytics(data.analytics);
            } catch (error) {
                console.error('Error loading analytics:', error);
            }
        }
        
        function renderAnalytics(analytics) {
            const dashboard = document.getElementById('analytics-dashboard');
            
            dashboard.innerHTML = `
                <div class="analytics-grid">
                    <div class="analytics-card">
                        <h3>System Overview</h3>
                        <div class="analytics-stats">
                            <div class="stat-item">
                                <div class="stat-value">${analytics.total_templates}</div>
                                <div class="stat-label">Total Templates</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${analytics.total_executions}</div>
                                <div class="stat-label">Total Executions</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${Math.round(analytics.success_rate * 100)}%</div>
                                <div class="stat-label">Success Rate</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${analytics.recent_executions_24h}</div>
                                <div class="stat-label">Last 24h</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="analytics-card">
                        <h3>Most Popular Templates</h3>
                        <div class="popular-templates">
                            ${analytics.most_popular_templates.map(([id, stats]) => `
                                <div class="template-stat">
                                    <span class="template-name">${stats.name}</span>
                                    <span class="template-usage">${stats.usage_count} uses</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Workflow actions
        async function executeWorkflow(workflowId) {
            try {
                const response = await fetch(`/api/workflows/${workflowId}/execute`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        parameters: {},
                        auto_approve: false
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    alert(`Workflow started successfully! Execution ID: ${data.execution_id}`);
                    showTab('executions');
                } else {
                    alert(`Error: ${data.detail}`);
                }
            } catch (error) {
                alert(`Error executing workflow: ${error.message}`);
            }
        }
        
        async function cancelExecution(executionId) {
            if (!confirm('Are you sure you want to cancel this execution?')) {
                return;
            }
            
            try {
                const response = await fetch(`/api/executions/${executionId}/cancel`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    alert('Execution cancelled successfully');
                    loadExecutions();
                } else {
                    const data = await response.json();
                    alert(`Error: ${data.detail}`);
                }
            } catch (error) {
                alert(`Error cancelling execution: ${error.message}`);
            }
        }
        
        async function showWorkflowDetails(workflowId) {
            try {
                const response = await fetch(`/api/workflows/${workflowId}`);
                const data = await response.json();
                
                const workflow = data.workflow;
                
                const modalContent = `
                    <h4>${workflow.name}</h4>
                    <p><strong>Description:</strong> ${workflow.description}</p>
                    <p><strong>Category:</strong> ${workflow.category}</p>
                    <p><strong>Version:</strong> ${workflow.version}</p>
                    <p><strong>Author:</strong> ${workflow.author}</p>
                    <p><strong>Tags:</strong> ${workflow.tags.join(', ')}</p>
                    
                    <h5>Steps:</h5>
                    <ol>
                        ${workflow.steps.map(step => `
                            <li>
                                <strong>${step.command}</strong> - ${step.description}
                                ${step.depends_on.length > 0 ? `<br><small>Depends on: ${step.depends_on.join(', ')}</small>` : ''}
                            </li>
                        `).join('')}
                    </ol>
                    
                    <div class="workflow-meta">
                        <p><strong>Estimated Duration:</strong> ${formatDuration(workflow.estimated_duration)}</p>
                        <p><strong>Success Rate:</strong> ${Math.round(workflow.success_rate * 100)}%</p>
                        <p><strong>Usage Count:</strong> ${workflow.usage_count}</p>
                        <p><strong>Approval Required:</strong> ${workflow.approval_required ? 'Yes' : 'No'}</p>
                        <p><strong>Rollback Enabled:</strong> ${workflow.rollback_enabled ? 'Yes' : 'No'}</p>
                    </div>
                `;
                
                showModal('Workflow Details', modalContent);
            } catch (error) {
                alert(`Error loading workflow details: ${error.message}`);
            }
        }
        
        // Filter functions
        function filterByCategory(category) {
            currentFilter = category;
            
            // Update filter buttons
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Reload workflows with filter
            loadWorkflows();
        }
        
        // Modal functions
        function showModal(title, content) {
            document.getElementById('modal-title').textContent = title;
            document.getElementById('modal-content').innerHTML = content;
            document.getElementById('modal-overlay').classList.add('active');
        }
        
        function closeModal() {
            document.getElementById('modal-overlay').classList.remove('active');
        }
        
        // Utility functions
        function formatDuration(seconds) {
            if (seconds < 60) {
                return `${seconds}s`;
            } else if (seconds < 3600) {
                return `${Math.floor(seconds / 60)}m`;
            } else {
                const hours = Math.floor(seconds / 3600);
                const minutes = Math.floor((seconds % 3600) / 60);
                return `${hours}h ${minutes}m`;
            }
        }
        
        function refreshDashboard() {
            loadWorkflows();
            loadExecutions();
            updateStatusIndicators();
        }
        
        async function updateStatusIndicators() {
            try {
                const [workflowsResponse, executionsResponse, analyticsResponse] = await Promise.all([
                    fetch('/api/workflows'),
                    fetch('/api/executions'),
                    fetch('/api/analytics')
                ]);
                
                const workflows = await workflowsResponse.json();
                const executions = await executionsResponse.json();
                const analytics = await analyticsResponse.json();
                
                document.getElementById('active-count').textContent = executions.active_executions.length;
                document.getElementById('success-rate').textContent = Math.round(analytics.analytics.success_rate * 100) + '%';
                document.getElementById('template-count').textContent = workflows.workflows.length;
            } catch (error) {
                console.error('Error updating status indicators:', error);
            }
        }
        
        // Workflow suggestions
        async function showWorkflowSuggestions() {
            const context = prompt('Enter context (optional):');
            const recentCommands = prompt('Enter recent commands (comma-separated, optional):');
            const intent = prompt('Enter intent (optional):');
            
            try {
                const params = new URLSearchParams();
                if (context) params.append('context', context);
                if (recentCommands) params.append('recent_commands', recentCommands);
                if (intent) params.append('intent', intent);
                
                const response = await fetch(`/api/suggestions?${params}`);
                const data = await response.json();
                
                const suggestions = data.suggestions;
                
                if (suggestions.length === 0) {
                    alert('No workflow suggestions found for the given context.');
                    return;
                }
                
                const modalContent = `
                    <h4>Workflow Suggestions</h4>
                    <div class="suggestions-list">
                        ${suggestions.map((suggestion, index) => `
                            <div class="suggestion-item">
                                <h5>${suggestion.name}</h5>
                                <p><strong>Confidence:</strong> ${Math.round(suggestion.confidence * 100)}%</p>
                                <p><strong>Reason:</strong> ${suggestion.reason}</p>
                                <p><strong>Duration:</strong> ${formatDuration(suggestion.estimated_duration)}</p>
                                <button class="btn btn-primary" onclick="executeWorkflow('${suggestion.workflow_id}'); closeModal();">
                                    Execute This Workflow
                                </button>
                            </div>
                        `).join('')}
                    </div>
                `;
                
                showModal('Workflow Suggestions', modalContent);
            } catch (error) {
                alert(`Error getting suggestions: ${error.message}`);
            }
        }
        
        // Create workflow
        function showCreateWorkflow() {
            const modalContent = `
                <h4>Create Custom Workflow</h4>
                <form id="create-workflow-form">
                    <div class="form-group">
                        <label>Name:</label>
                        <input type="text" name="name" required>
                    </div>
                    <div class="form-group">
                        <label>Description:</label>
                        <textarea name="description" required></textarea>
                    </div>
                    <div class="form-group">
                        <label>Category:</label>
                        <input type="text" name="category" required>
                    </div>
                    <div class="form-group">
                        <label>Tags (comma-separated):</label>
                        <input type="text" name="tags">
                    </div>
                    <div class="form-group">
                        <label>Workflow Definition (JSON):</label>
                        <textarea name="definition" rows="10" placeholder='{"steps": [{"id": "step1", "command": "hv-status", "description": "Check status"}]}' required></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary">Create Workflow</button>
                </form>
            `;
            
            showModal('Create Workflow', modalContent);
            
            document.getElementById('create-workflow-form').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData(e.target);
                const workflowData = {
                    name: formData.get('name'),
                    description: formData.get('description'),
                    category: formData.get('category'),
                    tags: formData.get('tags').split(',').map(t => t.trim()).filter(t => t),
                };
                
                try {
                    const definition = JSON.parse(formData.get('definition'));
                    Object.assign(workflowData, definition);
                } catch (error) {
                    alert('Invalid JSON in workflow definition');
                    return;
                }
                
                try {
                    const response = await fetch('/api/workflows', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(workflowData)
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        alert(`Workflow created successfully! Template ID: ${data.template_id}`);
                        closeModal();
                        loadWorkflows();
                    } else {
                        alert(`Error: ${data.detail}`);
                    }
                } catch (error) {
                    alert(`Error creating workflow: ${error.message}`);
                }
            });
        }
        """
    
    async def _get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data with caching"""
        current_time = time.time()
        
        # Check cache
        if current_time - self._cache_expiry < 30:  # 30 second cache
            return self._dashboard_cache
        
        # Refresh data
        await self._ensure_initialized()
        
        analytics = await self.workflow_engine.get_workflow_analytics()
        
        dashboard_data = {
            'total_templates': analytics['total_templates'],
            'total_executions': analytics['total_executions'],
            'success_rate': analytics['success_rate'],
            'active_executions': analytics['active_executions'],
            'recent_executions_24h': analytics['recent_executions_24h']
        }
        
        self._dashboard_cache = dashboard_data
        self._cache_expiry = current_time
        
        return dashboard_data
    
    async def _broadcast_update(self, message: Dict[str, Any]):
        """Broadcast update to all WebSocket connections"""
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
    
    def run(self, host: str = "0.0.0.0", port: int = 8901):
        """Run the dashboard server"""
        logger.info(f"Starting workflow dashboard on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)

async def create_workflow_dashboard(storage, config: Dict[str, Any]) -> WorkflowDashboard:
    """Create and initialize workflow dashboard"""
    dashboard = WorkflowDashboard(storage, config)
    await dashboard._ensure_initialized()
    return dashboard