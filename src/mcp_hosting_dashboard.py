#!/usr/bin/env python3
"""
hAIveMind MCP Server Hosting Dashboard
Web interface for managing hosted MCP servers
"""

import asyncio
import base64
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse, FileResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from mcp_server_host import MCPServerHost

logger = logging.getLogger(__name__)

class MCPHostingDashboard:
    """Web dashboard for MCP server hosting"""
    
    def __init__(self, config: Dict[str, Any], storage=None, auth_manager=None):
        self.config = config
        self.storage = storage
        self.auth_manager = auth_manager
        self.host = MCPServerHost(config, storage)
        
        # Dashboard configuration
        dashboard_config = config.get('mcp_hosting', {}).get('dashboard', {})
        self.enabled = dashboard_config.get('enabled', True)
        self.host_addr = dashboard_config.get('host', '0.0.0.0')
        self.port = dashboard_config.get('port', 8910)
        self.debug = dashboard_config.get('debug', False)
        
        # Create Starlette app
        middleware = [
            Middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
        ]
        
        routes = [
            Route('/', self.dashboard_home, methods=['GET']),
            Route('/api/servers', self.api_list_servers, methods=['GET']),
            Route('/api/servers/{server_id}', self.api_get_server, methods=['GET']),
            Route('/api/servers/{server_id}/start', self.api_start_server, methods=['POST']),
            Route('/api/servers/{server_id}/stop', self.api_stop_server, methods=['POST']),
            Route('/api/servers/{server_id}/restart', self.api_restart_server, methods=['POST']),
            Route('/api/servers/{server_id}/delete', self.api_delete_server, methods=['DELETE']),
            Route('/api/servers/{server_id}/logs', self.api_get_logs, methods=['GET']),
            Route('/api/upload', self.api_upload_server, methods=['POST']),
            Route('/api/stats', self.api_get_stats, methods=['GET']),
            Route('/api/optimize', self.api_optimize_servers, methods=['GET']),
            Mount('/static', StaticFiles(directory=str(Path(__file__).parent.parent / 'admin' / 'static')), name='static')
        ]
        
        self.app = Starlette(debug=self.debug, routes=routes, middleware=middleware)
        
        logger.info(f"🖥️ MCP Hosting Dashboard initialized on {self.host_addr}:{self.port}")
    
    async def start(self):
        """Start the hosting service and dashboard"""
        if not self.enabled:
            logger.info("🚫 MCP hosting dashboard is disabled")
            return
        
        await self.host.start()
        logger.info("✅ MCP hosting dashboard ready")
    
    async def stop(self):
        """Stop the hosting service"""
        await self.host.stop()
        logger.info("🛑 MCP hosting dashboard stopped")
    
    async def dashboard_home(self, request: Request):
        """Serve the main dashboard page"""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>hAIveMind MCP Server Hosting</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .header h1 {
            font-size: 2.5em;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        .header p { color: #666; font-size: 1.1em; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }
        .stat-label { color: #666; font-size: 1.1em; }
        .main-content {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
        }
        .servers-section, .upload-section {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .section-title {
            font-size: 1.5em;
            margin-bottom: 20px;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .server-card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
        }
        .server-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .server-name {
            font-weight: bold;
            font-size: 1.2em;
            color: #333;
        }
        .server-status {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        .status-running { background: #d4edda; color: #155724; }
        .status-stopped { background: #f8d7da; color: #721c24; }
        .status-starting { background: #fff3cd; color: #856404; }
        .status-failed { background: #f5c6cb; color: #721c24; }
        .server-info { color: #666; font-size: 0.9em; }
        .server-actions {
            margin-top: 15px;
            display: flex;
            gap: 10px;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-secondary { background: #6c757d; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        .upload-form {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        .form-label {
            font-weight: bold;
            color: #333;
        }
        .form-input, .form-textarea {
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s ease;
        }
        .form-input:focus, .form-textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
            color: #667eea;
        }
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .logs-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
        }
        .logs-content {
            background: white;
            margin: 5% auto;
            padding: 20px;
            width: 90%;
            max-width: 800px;
            border-radius: 15px;
            max-height: 80vh;
            overflow-y: auto;
        }
        .logs-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .close-btn {
            background: none;
            border: none;
            font-size: 1.5em;
            cursor: pointer;
            color: #666;
        }
        .logs-text {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 hAIveMind MCP Server Hosting</h1>
            <p>Deploy, manage, and monitor custom MCP servers with intelligent resource optimization</p>
        </div>
        
        <div class="alert alert-success" id="successAlert"></div>
        <div class="alert alert-error" id="errorAlert"></div>
        
        <div class="stats-grid" id="statsGrid">
            <div class="stat-card">
                <div class="stat-number" id="totalServers">-</div>
                <div class="stat-label">Total Servers</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="runningServers">-</div>
                <div class="stat-label">Running</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalMemory">-</div>
                <div class="stat-label">Memory (MB)</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="avgCpu">-</div>
                <div class="stat-label">Avg CPU %</div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="servers-section">
                <h2 class="section-title">🖥️ Hosted Servers</h2>
                <div class="loading" id="serversLoading">
                    <div class="spinner"></div>
                    <div>Loading servers...</div>
                </div>
                <div id="serversList"></div>
            </div>
            
            <div class="upload-section">
                <h2 class="section-title">📦 Deploy New Server</h2>
                <form class="upload-form" id="uploadForm">
                    <div class="form-group">
                        <label class="form-label">Server Name</label>
                        <input type="text" class="form-input" id="serverName" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Description</label>
                        <textarea class="form-textarea" id="serverDescription" rows="3"></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Server Archive (ZIP)</label>
                        <input type="file" class="form-input" id="serverArchive" accept=".zip" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Start Command (JSON array)</label>
                        <input type="text" class="form-input" id="serverCommand" 
                               placeholder='["python", "server.py"]' required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Environment Variables (JSON)</label>
                        <textarea class="form-textarea" id="serverEnv" rows="3" 
                                  placeholder='{"PORT": "8080", "DEBUG": "true"}'></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Health Check URL (optional)</label>
                        <input type="text" class="form-input" id="healthCheckUrl" 
                               placeholder="http://localhost:8080/health">
                    </div>
                    
                    <button type="submit" class="btn btn-primary">🚀 Deploy Server</button>
                </form>
                
                <div class="loading" id="uploadLoading">
                    <div class="spinner"></div>
                    <div>Deploying server...</div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Logs Modal -->
    <div class="logs-modal" id="logsModal">
        <div class="logs-content">
            <div class="logs-header">
                <h3 id="logsTitle">Server Logs</h3>
                <button class="close-btn" onclick="closeLogs()">&times;</button>
            </div>
            <div class="logs-text" id="logsText"></div>
        </div>
    </div>
    
    <script>
        let servers = [];
        
        // Load initial data
        document.addEventListener('DOMContentLoaded', function() {
            loadServers();
            loadStats();
            
            // Refresh every 30 seconds
            setInterval(() => {
                loadServers();
                loadStats();
            }, 30000);
        });
        
        // Load servers list
        async function loadServers() {
            try {
                document.getElementById('serversLoading').style.display = 'block';
                const response = await fetch('/api/servers');
                servers = await response.json();
                
                const serversList = document.getElementById('serversList');
                if (servers.length === 0) {
                    serversList.innerHTML = '<p style="text-align: center; color: #666; padding: 40px;">No servers deployed yet. Upload your first MCP server!</p>';
                } else {
                    serversList.innerHTML = servers.map(server => createServerCard(server)).join('');
                }
            } catch (error) {
                showError('Failed to load servers: ' + error.message);
            } finally {
                document.getElementById('serversLoading').style.display = 'none';
            }
        }
        
        // Load statistics
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                
                document.getElementById('totalServers').textContent = stats.total_servers || 0;
                document.getElementById('runningServers').textContent = stats.running_servers || 0;
                document.getElementById('totalMemory').textContent = Math.round(stats.total_memory || 0);
                document.getElementById('avgCpu').textContent = Math.round(stats.avg_cpu || 0) + '%';
            } catch (error) {
                console.error('Failed to load stats:', error);
            }
        }
        
        // Create server card HTML
        function createServerCard(server) {
            const statusClass = `status-${server.status}`;
            const statusText = server.status.charAt(0).toUpperCase() + server.status.slice(1);
            
            let uptime = '';
            if (server.uptime_seconds > 0) {
                const hours = Math.floor(server.uptime_seconds / 3600);
                const minutes = Math.floor((server.uptime_seconds % 3600) / 60);
                uptime = `Uptime: ${hours}h ${minutes}m`;
            }
            
            let resources = '';
            if (server.resource_usage) {
                const res = server.resource_usage;
                resources = `CPU: ${Math.round(res.cpu_percent || 0)}% | RAM: ${Math.round(res.memory_mb || 0)}MB`;
            }
            
            const canStart = server.status === 'stopped' || server.status === 'failed';
            const canStop = server.status === 'running' || server.status === 'starting';
            
            return `
                <div class="server-card">
                    <div class="server-header">
                        <div class="server-name">${server.name}</div>
                        <div class="server-status ${statusClass}">${statusText}</div>
                    </div>
                    <div class="server-info">
                        <div>ID: ${server.server_id}</div>
                        <div>${server.description || 'No description'}</div>
                        <div>${uptime} ${resources ? '| ' + resources : ''}</div>
                        <div>Restarts: ${server.restart_count || 0}</div>
                    </div>
                    <div class="server-actions">
                        ${canStart ? `<button class="btn btn-success" onclick="startServer('${server.server_id}')">▶️ Start</button>` : ''}
                        ${canStop ? `<button class="btn btn-secondary" onclick="stopServer('${server.server_id}')">⏹️ Stop</button>` : ''}
                        <button class="btn btn-primary" onclick="restartServer('${server.server_id}')">🔄 Restart</button>
                        <button class="btn btn-secondary" onclick="showLogs('${server.server_id}', '${server.name}')">📝 Logs</button>
                        <button class="btn btn-danger" onclick="deleteServer('${server.server_id}', '${server.name}')">🗑️ Delete</button>
                    </div>
                </div>
            `;
        }
        
        // Server actions
        async function startServer(serverId) {
            try {
                const response = await fetch(`/api/servers/${serverId}/start`, { method: 'POST' });
                const result = await response.json();
                if (response.ok) {
                    showSuccess(result.message);
                    loadServers();
                } else {
                    showError(result.error || 'Failed to start server');
                }
            } catch (error) {
                showError('Failed to start server: ' + error.message);
            }
        }
        
        async function stopServer(serverId) {
            try {
                const response = await fetch(`/api/servers/${serverId}/stop`, { method: 'POST' });
                const result = await response.json();
                if (response.ok) {
                    showSuccess(result.message);
                    loadServers();
                } else {
                    showError(result.error || 'Failed to stop server');
                }
            } catch (error) {
                showError('Failed to stop server: ' + error.message);
            }
        }
        
        async function restartServer(serverId) {
            try {
                const response = await fetch(`/api/servers/${serverId}/restart`, { method: 'POST' });
                const result = await response.json();
                if (response.ok) {
                    showSuccess(result.message);
                    loadServers();
                } else {
                    showError(result.error || 'Failed to restart server');
                }
            } catch (error) {
                showError('Failed to restart server: ' + error.message);
            }
        }
        
        async function deleteServer(serverId, serverName) {
            if (!confirm(`Are you sure you want to delete server "${serverName}"? This action cannot be undone.`)) {
                return;
            }
            
            try {
                const response = await fetch(`/api/servers/${serverId}/delete`, { method: 'DELETE' });
                const result = await response.json();
                if (response.ok) {
                    showSuccess(result.message);
                    loadServers();
                } else {
                    showError(result.error || 'Failed to delete server');
                }
            } catch (error) {
                showError('Failed to delete server: ' + error.message);
            }
        }
        
        // Show server logs
        async function showLogs(serverId, serverName) {
            try {
                const response = await fetch(`/api/servers/${serverId}/logs`);
                const logs = await response.json();
                
                document.getElementById('logsTitle').textContent = `Logs: ${serverName}`;
                
                if (logs.length === 0) {
                    document.getElementById('logsText').textContent = 'No logs available';
                } else {
                    const logsText = logs.map(log => {
                        const timestamp = new Date(log.timestamp * 1000).toLocaleString();
                        const stream = log.stream === 'stdout' ? '📤' : '🔴';
                        return `${stream} [${timestamp}] ${log.message}`;
                    }).join('\\n');
                    document.getElementById('logsText').textContent = logsText;
                }
                
                document.getElementById('logsModal').style.display = 'block';
            } catch (error) {
                showError('Failed to load logs: ' + error.message);
            }
        }
        
        function closeLogs() {
            document.getElementById('logsModal').style.display = 'none';
        }
        
        // Upload form handling
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData();
            const archiveFile = document.getElementById('serverArchive').files[0];
            
            if (!archiveFile) {
                showError('Please select a server archive file');
                return;
            }
            
            try {
                // Convert file to base64
                const base64Archive = await fileToBase64(archiveFile);
                
                const serverData = {
                    name: document.getElementById('serverName').value,
                    description: document.getElementById('serverDescription').value,
                    archive_base64: base64Archive,
                    command: JSON.parse(document.getElementById('serverCommand').value),
                    environment: document.getElementById('serverEnv').value ? 
                                JSON.parse(document.getElementById('serverEnv').value) : {},
                    health_check_url: document.getElementById('healthCheckUrl').value || null
                };
                
                document.getElementById('uploadLoading').style.display = 'block';
                
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(serverData)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showSuccess(result.message);
                    document.getElementById('uploadForm').reset();
                    loadServers();
                } else {
                    showError(result.error || 'Failed to upload server');
                }
            } catch (error) {
                showError('Failed to upload server: ' + error.message);
            } finally {
                document.getElementById('uploadLoading').style.display = 'none';
            }
        });
        
        // Utility functions
        function fileToBase64(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.readAsDataURL(file);
                reader.onload = () => resolve(reader.result.split(',')[1]);
                reader.onerror = error => reject(error);
            });
        }
        
        function showSuccess(message) {
            const alert = document.getElementById('successAlert');
            alert.textContent = message;
            alert.style.display = 'block';
            setTimeout(() => alert.style.display = 'none', 5000);
        }
        
        function showError(message) {
            const alert = document.getElementById('errorAlert');
            alert.textContent = message;
            alert.style.display = 'block';
            setTimeout(() => alert.style.display = 'none', 8000);
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('logsModal');
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        }
    </script>
</body>
</html>
        """
        return HTMLResponse(html_content)
    
    async def api_list_servers(self, request: Request):
        """API endpoint to list all servers"""
        try:
            servers = await self.host.list_servers()
            return JSONResponse(servers)
        except Exception as e:
            logger.error(f"Error listing servers: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def api_get_server(self, request: Request):
        """API endpoint to get server details"""
        try:
            server_id = request.path_params['server_id']
            status = await self.host.get_server_status(server_id)
            return JSONResponse(status)
        except Exception as e:
            logger.error(f"Error getting server: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def api_start_server(self, request: Request):
        """API endpoint to start a server"""
        try:
            server_id = request.path_params['server_id']
            result = await self.host.start_server(server_id)
            return JSONResponse(result)
        except Exception as e:
            logger.error(f"Error starting server: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def api_stop_server(self, request: Request):
        """API endpoint to stop a server"""
        try:
            server_id = request.path_params['server_id']
            result = await self.host.stop_server(server_id)
            return JSONResponse(result)
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def api_restart_server(self, request: Request):
        """API endpoint to restart a server"""
        try:
            server_id = request.path_params['server_id']
            result = await self.host.restart_server(server_id)
            return JSONResponse(result)
        except Exception as e:
            logger.error(f"Error restarting server: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def api_delete_server(self, request: Request):
        """API endpoint to delete a server"""
        try:
            server_id = request.path_params['server_id']
            result = await self.host.delete_server(server_id, force=True)
            return JSONResponse(result)
        except Exception as e:
            logger.error(f"Error deleting server: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def api_get_logs(self, request: Request):
        """API endpoint to get server logs"""
        try:
            server_id = request.path_params['server_id']
            lines = int(request.query_params.get('lines', 100))
            logs = await self.host.get_server_logs(server_id, lines)
            return JSONResponse(logs)
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def api_upload_server(self, request: Request):
        """API endpoint to upload a new server"""
        try:
            data = await request.json()
            
            result = await self.host.upload_server(
                name=data['name'],
                archive_data=base64.b64decode(data['archive_base64']),
                config={
                    'name': data['name'],
                    'description': data.get('description', ''),
                    'command': data['command'],
                    'environment': data.get('environment', {}),
                    'health_check_url': data.get('health_check_url')
                },
                user_id=data.get('user_id', 'dashboard')
            )
            
            return JSONResponse(result)
        except Exception as e:
            logger.error(f"Error uploading server: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def api_get_stats(self, request: Request):
        """API endpoint to get hosting statistics"""
        try:
            servers = await self.host.list_servers()
            
            total_servers = len(servers)
            running_servers = len([s for s in servers if s.get('status') == 'running'])
            total_memory = sum(s.get('resource_usage', {}).get('memory_mb', 0) for s in servers)
            avg_cpu = sum(s.get('resource_usage', {}).get('cpu_percent', 0) for s in servers) / max(total_servers, 1)
            
            stats = {
                'total_servers': total_servers,
                'running_servers': running_servers,
                'stopped_servers': len([s for s in servers if s.get('status') == 'stopped']),
                'failed_servers': len([s for s in servers if s.get('status') == 'failed']),
                'total_memory': total_memory,
                'avg_cpu': avg_cpu,
                'total_restarts': sum(s.get('restart_count', 0) for s in servers),
                'total_uptime': sum(s.get('uptime_seconds', 0) for s in servers)
            }
            
            return JSONResponse(stats)
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def api_optimize_servers(self, request: Request):
        """API endpoint to get optimization recommendations"""
        try:
            servers = await self.host.list_servers()
            recommendations = []
            
            for server in servers:
                server_name = server.get('name', 'Unknown')
                resource_usage = server.get('resource_usage', {})
                
                # Memory optimization
                memory_mb = resource_usage.get('memory_mb', 0)
                if memory_mb > 500:
                    recommendations.append({
                        'type': 'warning',
                        'server': server_name,
                        'message': f'High memory usage ({memory_mb:.1f}MB) - consider memory limits'
                    })
                
                # CPU optimization
                cpu_percent = resource_usage.get('cpu_percent', 0)
                if cpu_percent > 80:
                    recommendations.append({
                        'type': 'error',
                        'server': server_name,
                        'message': f'High CPU usage ({cpu_percent:.1f}%) - investigate performance'
                    })
                
                # Restart optimization
                restart_count = server.get('restart_count', 0)
                uptime_hours = server.get('uptime_seconds', 0) / 3600
                if restart_count > 5 and uptime_hours < 24:
                    recommendations.append({
                        'type': 'error',
                        'server': server_name,
                        'message': f'Frequent restarts ({restart_count} in {uptime_hours:.1f}h) - check stability'
                    })
            
            return JSONResponse({
                'recommendations': recommendations,
                'total_servers': len(servers),
                'analyzed_at': time.time()
            })
        except Exception as e:
            logger.error(f"Error getting optimization data: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)