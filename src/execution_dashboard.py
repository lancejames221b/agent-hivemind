#!/usr/bin/env python3
"""
Execution Dashboard for Advanced Playbook Engine

Provides web-based dashboard for monitoring active executions and history.
Includes real-time updates, execution control, and detailed logging views.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

from advanced_playbook_engine import AdvancedPlaybookEngine, ExecutionState, StepState

logger = logging.getLogger(__name__)


class ExecutionControlRequest(BaseModel):
    """Request model for execution control operations"""
    action: str  # "pause", "resume", "cancel", "rollback"
    run_id: str


class ApprovalRequest(BaseModel):
    """Request model for step approvals"""
    run_id: str
    step_id: str
    approver: str
    approved: bool = True


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
            
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_execution_update(self, run_id: str, status: Dict[str, Any]):
        """Send execution status update"""
        await self.broadcast({
            "type": "execution_update",
            "run_id": run_id,
            "data": status
        })
    
    async def send_step_update(self, run_id: str, step_id: str, step_data: Dict[str, Any]):
        """Send step status update"""
        await self.broadcast({
            "type": "step_update",
            "run_id": run_id,
            "step_id": step_id,
            "data": step_data
        })


class ExecutionDashboard:
    """Dashboard for monitoring playbook executions"""
    
    def __init__(self, execution_engine: AdvancedPlaybookEngine, host: str = "0.0.0.0", port: int = 8080):
        self.engine = execution_engine
        self.host = host
        self.port = port
        
        # FastAPI app
        self.app = FastAPI(
            title="Playbook Execution Dashboard",
            description="Real-time monitoring and control of playbook executions",
            version="1.0.0"
        )
        
        # WebSocket manager
        self.ws_manager = WebSocketManager()
        
        # Templates and static files
        self.templates = Jinja2Templates(directory="templates")
        
        # Setup routes
        self._setup_routes()
        
        # Background task for monitoring
        self._monitoring_task = None
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home(request: Request):
            """Main dashboard page"""
            return self.templates.TemplateResponse("dashboard.html", {
                "request": request,
                "title": "Playbook Execution Dashboard"
            })
        
        @self.app.get("/api/executions")
        async def list_executions():
            """List all active executions"""
            try:
                executions = self.engine.list_active_executions()
                return {"executions": executions}
            except Exception as e:
                logger.error(f"Error listing executions: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/executions/{run_id}")
        async def get_execution_status(run_id: str):
            """Get detailed execution status"""
            try:
                status = self.engine.get_execution_status(run_id)
                if not status:
                    raise HTTPException(status_code=404, detail="Execution not found")
                return status
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting execution status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/executions/control")
        async def control_execution(request: ExecutionControlRequest):
            """Control execution (pause, resume, cancel, rollback)"""
            try:
                action = request.action.lower()
                run_id = request.run_id
                
                if action == "pause":
                    success = await self.engine.pause_execution(run_id)
                elif action == "resume":
                    success = await self.engine.resume_execution(run_id)
                elif action == "cancel":
                    success = await self.engine.cancel_execution(run_id)
                elif action == "rollback":
                    success = await self.engine.rollback_execution(run_id)
                else:
                    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
                
                if success:
                    # Send update via WebSocket
                    status = self.engine.get_execution_status(run_id)
                    if status:
                        await self.ws_manager.send_execution_update(run_id, status)
                    
                    return {"success": True, "message": f"Execution {action} successful"}
                else:
                    return {"success": False, "message": f"Failed to {action} execution"}
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error controlling execution: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/executions/approve")
        async def approve_step(request: ApprovalRequest):
            """Approve a step waiting for approval"""
            try:
                success = await self.engine.approve_step(
                    request.run_id,
                    request.step_id,
                    request.approver
                )
                
                if success:
                    # Send update via WebSocket
                    status = self.engine.get_execution_status(request.run_id)
                    if status:
                        await self.ws_manager.send_execution_update(request.run_id, status)
                    
                    return {"success": True, "message": "Step approved successfully"}
                else:
                    return {"success": False, "message": "Failed to approve step"}
                    
            except Exception as e:
                logger.error(f"Error approving step: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/executions/{run_id}/logs")
        async def get_execution_logs(run_id: str):
            """Get execution logs"""
            try:
                status = self.engine.get_execution_status(run_id)
                if not status:
                    raise HTTPException(status_code=404, detail="Execution not found")
                
                # Format logs for display
                logs = []
                
                # Add execution-level logs
                for error in status.get("error_log", []):
                    logs.append({
                        "timestamp": datetime.now().isoformat(),
                        "level": "ERROR",
                        "source": "execution",
                        "message": error
                    })
                
                # Add step-level logs
                for step_id, step_result in status.get("step_results", {}).items():
                    if step_result.get("error"):
                        logs.append({
                            "timestamp": datetime.fromtimestamp(step_result.get("started_at", 0)).isoformat(),
                            "level": "ERROR",
                            "source": f"step:{step_id}",
                            "message": step_result["error"]
                        })
                    
                    # Add completion logs
                    if step_result.get("state") == "completed":
                        logs.append({
                            "timestamp": datetime.fromtimestamp(step_result.get("finished_at", 0)).isoformat(),
                            "level": "INFO",
                            "source": f"step:{step_id}",
                            "message": f"Step completed in {step_result.get('duration', 0):.2f}s"
                        })
                
                # Sort by timestamp
                logs.sort(key=lambda x: x["timestamp"])
                
                return {"logs": logs}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting execution logs: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/stats")
        async def get_dashboard_stats():
            """Get dashboard statistics"""
            try:
                executions = self.engine.list_active_executions()
                
                stats = {
                    "total_executions": len(executions),
                    "running_executions": len([e for e in executions if e["state"] == "running"]),
                    "paused_executions": len([e for e in executions if e["state"] == "paused"]),
                    "failed_executions": len([e for e in executions if e["state"] == "failed"]),
                    "completed_executions": len([e for e in executions if e["state"] == "completed"]),
                    "waiting_approval": len([e for e in executions if e["state"] == "waiting_approval"]),
                }
                
                return stats
                
            except Exception as e:
                logger.error(f"Error getting dashboard stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await self.ws_manager.connect(websocket)
            try:
                while True:
                    # Keep connection alive and handle client messages
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Handle client requests
                    if message.get("type") == "subscribe":
                        # Client wants to subscribe to specific execution updates
                        run_id = message.get("run_id")
                        if run_id:
                            status = self.engine.get_execution_status(run_id)
                            if status:
                                await websocket.send_json({
                                    "type": "execution_update",
                                    "run_id": run_id,
                                    "data": status
                                })
                    
            except WebSocketDisconnect:
                self.ws_manager.disconnect(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.ws_manager.disconnect(websocket)
    
    async def start_monitoring(self):
        """Start background monitoring task"""
        self._monitoring_task = asyncio.create_task(self._monitor_executions())
    
    async def stop_monitoring(self):
        """Stop background monitoring task"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_executions(self):
        """Background task to monitor executions and send updates"""
        last_states = {}
        
        while True:
            try:
                executions = self.engine.list_active_executions()
                
                for execution in executions:
                    run_id = execution["run_id"]
                    current_state = execution["state"]
                    
                    # Check if state changed
                    if run_id not in last_states or last_states[run_id] != current_state:
                        last_states[run_id] = current_state
                        
                        # Get detailed status and broadcast
                        detailed_status = self.engine.get_execution_status(run_id)
                        if detailed_status:
                            await self.ws_manager.send_execution_update(run_id, detailed_status)
                
                # Clean up old states
                current_run_ids = {e["run_id"] for e in executions}
                old_run_ids = set(last_states.keys()) - current_run_ids
                for old_run_id in old_run_ids:
                    del last_states[old_run_id]
                
                await asyncio.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring task: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def run(self):
        """Run the dashboard server"""
        # Start monitoring
        await self.start_monitoring()
        
        try:
            config = uvicorn.Config(
                app=self.app,
                host=self.host,
                port=self.port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
        finally:
            await self.stop_monitoring()


# HTML Template for the dashboard
DASHBOARD_HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        
        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .stat-card h3 {
            font-size: 2rem;
            margin-bottom: 0.5rem;
            color: #667eea;
        }
        
        .stat-card p {
            color: #666;
            font-weight: 500;
        }
        
        .executions-section {
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .section-header {
            background: #f8f9fa;
            padding: 1.5rem;
            border-bottom: 1px solid #e9ecef;
        }
        
        .section-header h2 {
            font-size: 1.5rem;
            color: #333;
        }
        
        .executions-list {
            padding: 1rem;
        }
        
        .execution-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            margin-bottom: 1rem;
            transition: all 0.2s ease;
        }
        
        .execution-item:hover {
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transform: translateY(-1px);
        }
        
        .execution-info h4 {
            margin-bottom: 0.5rem;
            color: #333;
        }
        
        .execution-info p {
            color: #666;
            font-size: 0.9rem;
        }
        
        .execution-status {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        .status-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-running { background: #d4edda; color: #155724; }
        .status-paused { background: #fff3cd; color: #856404; }
        .status-completed { background: #d1ecf1; color: #0c5460; }
        .status-failed { background: #f8d7da; color: #721c24; }
        .status-waiting_approval { background: #e2e3e5; color: #383d41; }
        
        .control-buttons {
            display: flex;
            gap: 0.5rem;
        }
        
        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        
        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        
        .btn-primary { background: #007bff; color: white; }
        .btn-warning { background: #ffc107; color: #212529; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-secondary { background: #6c757d; color: white; }
        
        .connection-status {
            position: fixed;
            top: 1rem;
            right: 1rem;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .connected { background: #d4edda; color: #155724; }
        .disconnected { background: #f8d7da; color: #721c24; }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: #666;
        }
        
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(102, 126, 234, 0.3);
            border-radius: 50%;
            border-top-color: #667eea;
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .empty-state {
            text-align: center;
            padding: 3rem;
            color: #666;
        }
        
        .empty-state h3 {
            margin-bottom: 1rem;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="connection-status" id="connectionStatus">
        <span class="spinner"></span> Connecting...
    </div>
    
    <div class="header">
        <h1>{{ title }}</h1>
        <p>Real-time monitoring and control of playbook executions</p>
    </div>
    
    <div class="container">
        <div class="stats-grid" id="statsGrid">
            <!-- Stats will be populated by JavaScript -->
        </div>
        
        <div class="executions-section">
            <div class="section-header">
                <h2>Active Executions</h2>
            </div>
            <div class="executions-list" id="executionsList">
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Loading executions...</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        class ExecutionDashboard {
            constructor() {
                this.ws = null;
                this.executions = new Map();
                this.stats = {};
                this.init();
            }
            
            init() {
                this.connectWebSocket();
                this.loadInitialData();
                
                // Refresh data every 30 seconds as fallback
                setInterval(() => this.loadInitialData(), 30000);
            }
            
            connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                
                this.ws = new WebSocket(wsUrl);
                
                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.updateConnectionStatus(true);
                };
                
                this.ws.onclose = () => {
                    console.log('WebSocket disconnected');
                    this.updateConnectionStatus(false);
                    
                    // Reconnect after 5 seconds
                    setTimeout(() => this.connectWebSocket(), 5000);
                };
                
                this.ws.onmessage = (event) => {
                    const message = JSON.parse(event.data);
                    this.handleWebSocketMessage(message);
                };
                
                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    this.updateConnectionStatus(false);
                };
            }
            
            handleWebSocketMessage(message) {
                if (message.type === 'execution_update') {
                    this.executions.set(message.run_id, message.data);
                    this.renderExecutions();
                    this.updateStats();
                } else if (message.type === 'step_update') {
                    const execution = this.executions.get(message.run_id);
                    if (execution && execution.step_results) {
                        execution.step_results[message.step_id] = message.data;
                        this.renderExecutions();
                    }
                }
            }
            
            async loadInitialData() {
                try {
                    const [executionsResponse, statsResponse] = await Promise.all([
                        fetch('/api/executions'),
                        fetch('/api/stats')
                    ]);
                    
                    const executionsData = await executionsResponse.json();
                    const statsData = await statsResponse.json();
                    
                    // Load detailed data for each execution
                    for (const execution of executionsData.executions) {
                        const detailResponse = await fetch(`/api/executions/${execution.run_id}`);
                        const detailData = await detailResponse.json();
                        this.executions.set(execution.run_id, detailData);
                    }
                    
                    this.stats = statsData;
                    this.renderStats();
                    this.renderExecutions();
                    
                } catch (error) {
                    console.error('Error loading data:', error);
                }
            }
            
            renderStats() {
                const statsGrid = document.getElementById('statsGrid');
                statsGrid.innerHTML = `
                    <div class="stat-card">
                        <h3>${this.stats.total_executions || 0}</h3>
                        <p>Total Executions</p>
                    </div>
                    <div class="stat-card">
                        <h3>${this.stats.running_executions || 0}</h3>
                        <p>Running</p>
                    </div>
                    <div class="stat-card">
                        <h3>${this.stats.paused_executions || 0}</h3>
                        <p>Paused</p>
                    </div>
                    <div class="stat-card">
                        <h3>${this.stats.completed_executions || 0}</h3>
                        <p>Completed</p>
                    </div>
                    <div class="stat-card">
                        <h3>${this.stats.failed_executions || 0}</h3>
                        <p>Failed</p>
                    </div>
                    <div class="stat-card">
                        <h3>${this.stats.waiting_approval || 0}</h3>
                        <p>Waiting Approval</p>
                    </div>
                `;
            }
            
            renderExecutions() {
                const executionsList = document.getElementById('executionsList');
                
                if (this.executions.size === 0) {
                    executionsList.innerHTML = `
                        <div class="empty-state">
                            <h3>No Active Executions</h3>
                            <p>Start a playbook execution to see it here.</p>
                        </div>
                    `;
                    return;
                }
                
                const executionsArray = Array.from(this.executions.values());
                executionsArray.sort((a, b) => b.started_at - a.started_at);
                
                executionsList.innerHTML = executionsArray.map(execution => {
                    const duration = execution.duration ? 
                        `${execution.duration.toFixed(1)}s` : 
                        `${((Date.now() / 1000) - execution.started_at).toFixed(1)}s`;
                    
                    const progress = execution.total_steps > 0 ? 
                        Math.round((execution.completed_steps / execution.total_steps) * 100) : 0;
                    
                    return `
                        <div class="execution-item">
                            <div class="execution-info">
                                <h4>Execution ${execution.run_id.substring(0, 8)}</h4>
                                <p>Duration: ${duration} | Progress: ${progress}% (${execution.completed_steps}/${execution.total_steps})</p>
                                <p>Started: ${new Date(execution.started_at * 1000).toLocaleString()}</p>
                            </div>
                            <div class="execution-status">
                                <span class="status-badge status-${execution.state}">${execution.state.replace('_', ' ')}</span>
                                <div class="control-buttons">
                                    ${this.getControlButtons(execution)}
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
            }
            
            getControlButtons(execution) {
                const buttons = [];
                
                if (execution.state === 'running') {
                    buttons.push(`<button class="btn btn-warning" onclick="dashboard.controlExecution('${execution.run_id}', 'pause')">Pause</button>`);
                    buttons.push(`<button class="btn btn-danger" onclick="dashboard.controlExecution('${execution.run_id}', 'cancel')">Cancel</button>`);
                } else if (execution.state === 'paused') {
                    buttons.push(`<button class="btn btn-primary" onclick="dashboard.controlExecution('${execution.run_id}', 'resume')">Resume</button>`);
                    buttons.push(`<button class="btn btn-danger" onclick="dashboard.controlExecution('${execution.run_id}', 'cancel')">Cancel</button>`);
                } else if (execution.state === 'failed' || execution.state === 'completed') {
                    buttons.push(`<button class="btn btn-secondary" onclick="dashboard.controlExecution('${execution.run_id}', 'rollback')">Rollback</button>`);
                }
                
                buttons.push(`<button class="btn btn-primary" onclick="dashboard.viewDetails('${execution.run_id}')">Details</button>`);
                
                return buttons.join('');
            }
            
            async controlExecution(runId, action) {
                try {
                    const response = await fetch('/api/executions/control', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            run_id: runId,
                            action: action
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        console.log(`${action} successful for execution ${runId}`);
                    } else {
                        alert(`Failed to ${action} execution: ${result.message}`);
                    }
                    
                } catch (error) {
                    console.error(`Error ${action} execution:`, error);
                    alert(`Error ${action} execution: ${error.message}`);
                }
            }
            
            viewDetails(runId) {
                // Open details in new window/tab
                window.open(`/execution/${runId}`, '_blank');
            }
            
            updateConnectionStatus(connected) {
                const status = document.getElementById('connectionStatus');
                if (connected) {
                    status.innerHTML = '🟢 Connected';
                    status.className = 'connection-status connected';
                } else {
                    status.innerHTML = '🔴 Disconnected';
                    status.className = 'connection-status disconnected';
                }
            }
            
            updateStats() {
                const executions = Array.from(this.executions.values());
                this.stats = {
                    total_executions: executions.length,
                    running_executions: executions.filter(e => e.state === 'running').length,
                    paused_executions: executions.filter(e => e.state === 'paused').length,
                    completed_executions: executions.filter(e => e.state === 'completed').length,
                    failed_executions: executions.filter(e => e.state === 'failed').length,
                    waiting_approval: executions.filter(e => e.state === 'waiting_approval').length,
                };
                this.renderStats();
            }
        }
        
        // Initialize dashboard
        const dashboard = new ExecutionDashboard();
    </script>
</body>
</html>
'''


def create_templates_directory():
    """Create templates directory and dashboard template"""
    import os
    
    templates_dir = "templates"
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    with open(os.path.join(templates_dir, "dashboard.html"), "w") as f:
        f.write(DASHBOARD_HTML_TEMPLATE)


if __name__ == "__main__":
    # Example usage
    from advanced_playbook_engine import AdvancedPlaybookEngine
    
    # Create templates directory
    create_templates_directory()
    
    # Create engine and dashboard
    engine = AdvancedPlaybookEngine()
    dashboard = ExecutionDashboard(engine)
    
    # Run dashboard
    import asyncio
    asyncio.run(dashboard.run())