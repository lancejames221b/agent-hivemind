#!/usr/bin/env python3
"""
MCP Hub Authentication Dashboard
Web interface for managing authentication, users, API keys, and security
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.authentication import AuthenticationMiddleware
from starlette.middleware.sessions import SessionMiddleware

from mcp_auth_manager import MCPAuthManager
from mcp_auth_middleware import MCPAuthMiddleware
from mcp_auth_tools import MCPAuthTools

logger = logging.getLogger(__name__)

class MCPAuthDashboard:
    """Web dashboard for MCP authentication management"""
    
    def __init__(self, config: Dict[str, Any], memory_storage=None):
        self.config = config
        self.memory_storage = memory_storage
        self.auth_manager = MCPAuthManager(config, memory_storage)
        self.auth_tools = MCPAuthTools(config, memory_storage)
        
        # Dashboard configuration
        dashboard_config = config.get('mcp_hosting', {}).get('dashboard', {})
        self.enabled = dashboard_config.get('enabled', True)
        self.host_addr = dashboard_config.get('host', '0.0.0.0')
        self.port = dashboard_config.get('port', 8910)
        self.debug = dashboard_config.get('debug', False)
        
        # Create Starlette app with authentication
        middleware = [
            Middleware(SessionMiddleware, secret_key=self.auth_manager.jwt_secret),
            Middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*']),
            Middleware(MCPAuthMiddleware, auth_manager=self.auth_manager)
        ]
        
        routes = [
            # Authentication routes
            Route('/auth/login', self.auth_login, methods=['GET', 'POST']),
            Route('/auth/logout', self.auth_logout, methods=['POST']),
            Route('/auth/status', self.auth_status, methods=['GET']),
            
            # Dashboard routes
            Route('/auth', self.auth_dashboard, methods=['GET']),
            Route('/auth/users', self.users_page, methods=['GET']),
            Route('/auth/api-keys', self.api_keys_page, methods=['GET']),
            Route('/auth/servers', self.servers_auth_page, methods=['GET']),
            Route('/auth/security', self.security_page, methods=['GET']),
            
            # API routes
            Route('/api/auth/users', self.api_list_users, methods=['GET']),
            Route('/api/auth/users', self.api_create_user, methods=['POST']),
            Route('/api/auth/api-keys', self.api_list_api_keys, methods=['GET']),
            Route('/api/auth/api-keys', self.api_create_api_key, methods=['POST']),
            Route('/api/auth/api-keys/{key_id}', self.api_revoke_api_key, methods=['DELETE']),
            Route('/api/auth/servers/{server_id}/config', self.api_configure_server_auth, methods=['POST']),
            Route('/api/auth/security/analytics', self.api_security_analytics, methods=['GET']),
            Route('/api/auth/security/events', self.api_audit_events, methods=['GET']),
        ]
        
        self.app = Starlette(debug=self.debug, routes=routes, middleware=middleware)
        
        logger.info(f"🔐 MCP Auth Dashboard initialized on {self.host_addr}:{self.port}")
    
    async def auth_login(self, request: Request):
        """Handle login page and authentication"""
        if request.method == 'GET':
            return HTMLResponse(self._get_login_html())
        
        # Handle POST login
        try:
            form_data = await request.form()
            username = form_data.get('username')
            password = form_data.get('password')
            
            if not username or not password:
                return HTMLResponse(self._get_login_html(error="Username and password required"))
            
            client_ip = self._get_client_ip(request)
            success, auth_context = await self.auth_manager.authenticate_user(username, password, client_ip)
            
            if success:
                # Store session
                request.session['user_id'] = auth_context.user_id
                request.session['session_id'] = auth_context.session_id
                
                return RedirectResponse(url='/auth', status_code=302)
            else:
                return HTMLResponse(self._get_login_html(error="Invalid username or password"))
        
        except Exception as e:
            logger.error(f"Login error: {e}")
            return HTMLResponse(self._get_login_html(error="Login failed"))
    
    async def auth_logout(self, request: Request):
        """Handle logout"""
        request.session.clear()
        return RedirectResponse(url='/auth/login', status_code=302)
    
    async def auth_status(self, request: Request):
        """Get authentication status"""
        auth_context = getattr(request.state, 'auth_context', None)
        if auth_context:
            return JSONResponse({
                'authenticated': True,
                'user_id': auth_context.user_id,
                'username': auth_context.username,
                'role': auth_context.role,
                'permissions': list(auth_context.permissions)
            })
        else:
            return JSONResponse({'authenticated': False})
    
    async def auth_dashboard(self, request: Request):
        """Main authentication dashboard"""
        return HTMLResponse(self._get_dashboard_html())
    
    async def users_page(self, request: Request):
        """Users management page"""
        return HTMLResponse(self._get_users_html())
    
    async def api_keys_page(self, request: Request):
        """API keys management page"""
        return HTMLResponse(self._get_api_keys_html())
    
    async def servers_auth_page(self, request: Request):
        """Server authentication configuration page"""
        return HTMLResponse(self._get_servers_auth_html())
    
    async def security_page(self, request: Request):
        """Security analytics and audit page"""
        return HTMLResponse(self._get_security_html())
    
    # API endpoints
    
    async def api_list_users(self, request: Request):
        """API endpoint to list users"""
        try:
            active_only = request.query_params.get('active_only', 'true').lower() == 'true'
            result = await self.auth_tools.list_users(active_only)
            return JSONResponse({'success': True, 'data': result})
        except Exception as e:
            return JSONResponse({'success': False, 'error': str(e)}, status_code=500)
    
    async def api_create_user(self, request: Request):
        """API endpoint to create user"""
        try:
            data = await request.json()
            result = await self.auth_tools.create_user_account(
                username=data['username'],
                password=data['password'],
                role=data.get('role', 'user'),
                permissions=data.get('permissions', [])
            )
            return JSONResponse({'success': True, 'data': result})
        except Exception as e:
            return JSONResponse({'success': False, 'error': str(e)}, status_code=500)
    
    async def api_list_api_keys(self, request: Request):
        """API endpoint to list API keys"""
        try:
            user_id = request.query_params.get('user_id')
            active_only = request.query_params.get('active_only', 'true').lower() == 'true'
            result = await self.auth_tools.list_api_keys(user_id, active_only)
            return JSONResponse({'success': True, 'data': result})
        except Exception as e:
            return JSONResponse({'success': False, 'error': str(e)}, status_code=500)
    
    async def api_create_api_key(self, request: Request):
        """API endpoint to create API key"""
        try:
            data = await request.json()
            result = await self.auth_tools.create_api_key(
                user_id=data['user_id'],
                key_name=data['key_name'],
                role=data.get('role'),
                permissions=data.get('permissions'),
                server_access=data.get('server_access'),
                expires_days=data.get('expires_days')
            )
            return JSONResponse({'success': True, 'data': result})
        except Exception as e:
            return JSONResponse({'success': False, 'error': str(e)}, status_code=500)
    
    async def api_revoke_api_key(self, request: Request):
        """API endpoint to revoke API key"""
        try:
            key_id = request.path_params['key_id']
            result = await self.auth_tools.revoke_api_key(key_id)
            return JSONResponse({'success': True, 'data': result})
        except Exception as e:
            return JSONResponse({'success': False, 'error': str(e)}, status_code=500)
    
    async def api_configure_server_auth(self, request: Request):
        """API endpoint to configure server authentication"""
        try:
            server_id = request.path_params['server_id']
            data = await request.json()
            result = await self.auth_tools.configure_server_authentication(
                server_id=server_id,
                auth_required=data.get('auth_required', True),
                allowed_roles=data.get('allowed_roles'),
                allowed_users=data.get('allowed_users'),
                tool_permissions=data.get('tool_permissions'),
                rate_limits=data.get('rate_limits'),
                audit_level=data.get('audit_level', 'standard')
            )
            return JSONResponse({'success': True, 'data': result})
        except Exception as e:
            return JSONResponse({'success': False, 'error': str(e)}, status_code=500)
    
    async def api_security_analytics(self, request: Request):
        """API endpoint to get security analytics"""
        try:
            days = int(request.query_params.get('days', 7))
            result = await self.auth_tools.get_security_analytics(days)
            return JSONResponse({'success': True, 'data': result})
        except Exception as e:
            return JSONResponse({'success': False, 'error': str(e)}, status_code=500)
    
    async def api_audit_events(self, request: Request):
        """API endpoint to get audit events"""
        try:
            event_type = request.query_params.get('event_type')
            user_id = request.query_params.get('user_id')
            hours = int(request.query_params.get('hours', 24))
            risk_level = request.query_params.get('risk_level')
            
            result = await self.auth_tools.audit_security_events(event_type, user_id, hours, risk_level)
            return JSONResponse({'success': True, 'data': result})
        except Exception as e:
            return JSONResponse({'success': False, 'error': str(e)}, status_code=500)
    
    # Helper methods
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else 'unknown'
    
    def _get_login_html(self, error: str = None) -> str:
        """Generate login page HTML"""
        error_html = f'<div class="alert alert-error">{error}</div>' if error else ''
        
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Hub - Login</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .login-container {{
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
        }}
        .login-header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .login-header h1 {{
            font-size: 2em;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        .form-label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #333;
        }}
        .form-input {{
            width: 100%;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s ease;
        }}
        .form-input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        .btn {{
            width: 100%;
            padding: 12px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            transition: transform 0.3s ease;
        }}
        .btn:hover {{
            transform: translateY(-2px);
        }}
        .alert {{
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .alert-error {{
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }}
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1>🔐 MCP Hub</h1>
            <p>Authentication Required</p>
        </div>
        
        {error_html}
        
        <form method="post">
            <div class="form-group">
                <label class="form-label">Username</label>
                <input type="text" name="username" class="form-input" required>
            </div>
            
            <div class="form-group">
                <label class="form-label">Password</label>
                <input type="password" name="password" class="form-input" required>
            </div>
            
            <button type="submit" class="btn">Login</button>
        </form>
    </div>
</body>
</html>
        """
    
    def _get_dashboard_html(self) -> str:
        """Generate main dashboard HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Hub - Authentication Dashboard</title>
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
        .nav-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .nav-card {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
            text-decoration: none;
            color: #333;
        }
        .nav-card:hover { transform: translateY(-5px); }
        .nav-icon { font-size: 3em; margin-bottom: 15px; }
        .nav-title { font-size: 1.5em; font-weight: bold; margin-bottom: 10px; }
        .nav-description { color: #666; }
        .logout-btn {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <form method="post" action="/auth/logout" style="display: inline;">
        <button type="submit" class="logout-btn">Logout</button>
    </form>
    
    <div class="container">
        <div class="header">
            <h1>🔐 Authentication Dashboard</h1>
            <p>Manage users, API keys, server authentication, and security</p>
        </div>
        
        <div class="nav-grid">
            <a href="/auth/users" class="nav-card">
                <div class="nav-icon">👥</div>
                <div class="nav-title">User Management</div>
                <div class="nav-description">Create and manage user accounts</div>
            </a>
            
            <a href="/auth/api-keys" class="nav-card">
                <div class="nav-icon">🔑</div>
                <div class="nav-title">API Keys</div>
                <div class="nav-description">Generate and manage API keys</div>
            </a>
            
            <a href="/auth/servers" class="nav-card">
                <div class="nav-icon">🖥️</div>
                <div class="nav-title">Server Authentication</div>
                <div class="nav-description">Configure per-server access control</div>
            </a>
            
            <a href="/auth/security" class="nav-card">
                <div class="nav-icon">📊</div>
                <div class="nav-title">Security Analytics</div>
                <div class="nav-description">View audit logs and security insights</div>
            </a>
        </div>
    </div>
</body>
</html>
        """
    
    def _get_users_html(self) -> str:
        """Generate users management HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Hub - User Management</title>
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
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .back-btn {
            display: inline-block;
            margin-bottom: 20px;
            padding: 10px 20px;
            background: #6c757d;
            color: white;
            text-decoration: none;
            border-radius: 8px;
        }
        .main-content {
            display: grid;
            grid-template-columns: 1fr 400px;
            gap: 30px;
        }
        .users-section, .create-section {
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
        .user-card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #333;
        }
        .form-input, .form-select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 1em;
        }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            transition: transform 0.3s ease;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn:hover { transform: translateY(-2px); }
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/auth" class="back-btn">← Back to Dashboard</a>
        
        <div class="header">
            <h1>👥 User Management</h1>
            <p>Create and manage user accounts for MCP Hub access</p>
        </div>
        
        <div class="alert alert-success" id="successAlert"></div>
        <div class="alert alert-error" id="errorAlert"></div>
        
        <div class="main-content">
            <div class="users-section">
                <h2 class="section-title">Existing Users</h2>
                <div id="usersList">Loading users...</div>
            </div>
            
            <div class="create-section">
                <h2 class="section-title">Create New User</h2>
                <form id="createUserForm">
                    <div class="form-group">
                        <label class="form-label">Username</label>
                        <input type="text" id="username" class="form-input" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Password</label>
                        <input type="password" id="password" class="form-input" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Role</label>
                        <select id="role" class="form-select">
                            <option value="user">User</option>
                            <option value="admin">Admin</option>
                            <option value="readonly">Read Only</option>
                        </select>
                    </div>
                    
                    <button type="submit" class="btn btn-primary">Create User</button>
                </form>
            </div>
        </div>
    </div>
    
    <script>
        // Load users on page load
        document.addEventListener('DOMContentLoaded', loadUsers);
        
        async function loadUsers() {
            try {
                const response = await fetch('/api/auth/users');
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('usersList').innerHTML = 
                        '<pre style="white-space: pre-wrap;">' + result.data + '</pre>';
                } else {
                    showError('Failed to load users: ' + result.error);
                }
            } catch (error) {
                showError('Error loading users: ' + error.message);
            }
        }
        
        // Handle form submission
        document.getElementById('createUserForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = {
                username: document.getElementById('username').value,
                password: document.getElementById('password').value,
                role: document.getElementById('role').value
            };
            
            try {
                const response = await fetch('/api/auth/users', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showSuccess('User created successfully');
                    document.getElementById('createUserForm').reset();
                    loadUsers();
                } else {
                    showError('Failed to create user: ' + result.error);
                }
            } catch (error) {
                showError('Error creating user: ' + error.message);
            }
        });
        
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
    </script>
</body>
</html>
        """
    
    def _get_api_keys_html(self) -> str:
        """Generate API keys management HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Hub - API Key Management</title>
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
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .back-btn {
            display: inline-block;
            margin-bottom: 20px;
            padding: 10px 20px;
            background: #6c757d;
            color: white;
            text-decoration: none;
            border-radius: 8px;
        }
        .main-content {
            display: grid;
            grid-template-columns: 1fr 400px;
            gap: 30px;
        }
        .keys-section, .create-section {
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
        .form-group {
            margin-bottom: 20px;
        }
        .form-label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #333;
        }
        .form-input, .form-select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 1em;
        }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            transition: transform 0.3s ease;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn:hover { transform: translateY(-2px); }
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-error { background: #f8d7da; color: #721c24; }
        .key-display {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            word-break: break-all;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/auth" class="back-btn">← Back to Dashboard</a>
        
        <div class="header">
            <h1>🔑 API Key Management</h1>
            <p>Generate and manage API keys for MCP Hub access</p>
        </div>
        
        <div class="alert alert-success" id="successAlert"></div>
        <div class="alert alert-error" id="errorAlert"></div>
        
        <div class="main-content">
            <div class="keys-section">
                <h2 class="section-title">Existing API Keys</h2>
                <div id="keysList">Loading API keys...</div>
            </div>
            
            <div class="create-section">
                <h2 class="section-title">Create New API Key</h2>
                <form id="createKeyForm">
                    <div class="form-group">
                        <label class="form-label">User ID</label>
                        <input type="text" id="userId" class="form-input" required 
                               placeholder="Enter user ID">
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Key Name</label>
                        <input type="text" id="keyName" class="form-input" required
                               placeholder="e.g., Production API Key">
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Role</label>
                        <select id="keyRole" class="form-select">
                            <option value="">Use user's role</option>
                            <option value="user">User</option>
                            <option value="admin">Admin</option>
                            <option value="readonly">Read Only</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Expires (days)</label>
                        <input type="number" id="expiresDays" class="form-input" 
                               placeholder="Leave empty for no expiration">
                    </div>
                    
                    <button type="submit" class="btn btn-primary">Create API Key</button>
                </form>
                
                <div id="newKeyDisplay" style="display: none;">
                    <h3>⚠️ New API Key Created</h3>
                    <p>Save this key securely - it will not be shown again!</p>
                    <div class="key-display" id="newKeyValue"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Load API keys on page load
        document.addEventListener('DOMContentLoaded', loadApiKeys);
        
        async function loadApiKeys() {
            try {
                const response = await fetch('/api/auth/api-keys');
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('keysList').innerHTML = 
                        '<pre style="white-space: pre-wrap;">' + result.data + '</pre>';
                } else {
                    showError('Failed to load API keys: ' + result.error);
                }
            } catch (error) {
                showError('Error loading API keys: ' + error.message);
            }
        }
        
        // Handle form submission
        document.getElementById('createKeyForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = {
                user_id: document.getElementById('userId').value,
                key_name: document.getElementById('keyName').value,
                role: document.getElementById('keyRole').value || null,
                expires_days: document.getElementById('expiresDays').value ? 
                              parseInt(document.getElementById('expiresDays').value) : null
            };
            
            try {
                const response = await fetch('/api/auth/api-keys', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showSuccess('API key created successfully');
                    document.getElementById('createKeyForm').reset();
                    
                    // Show the new key
                    const keyDisplay = document.getElementById('newKeyDisplay');
                    const keyValue = document.getElementById('newKeyValue');
                    keyValue.textContent = result.data.match(/API Key.*: `(.+?)`/)[1];
                    keyDisplay.style.display = 'block';
                    
                    loadApiKeys();
                } else {
                    showError('Failed to create API key: ' + result.error);
                }
            } catch (error) {
                showError('Error creating API key: ' + error.message);
            }
        });
        
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
    </script>
</body>
</html>
        """
    
    def _get_servers_auth_html(self) -> str:
        """Generate server authentication configuration HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Hub - Server Authentication</title>
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
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .back-btn {
            display: inline-block;
            margin-bottom: 20px;
            padding: 10px 20px;
            background: #6c757d;
            color: white;
            text-decoration: none;
            border-radius: 8px;
        }
        .config-section {
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
        .form-group {
            margin-bottom: 20px;
        }
        .form-label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #333;
        }
        .form-input, .form-select, .form-textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 1em;
        }
        .form-checkbox {
            margin-right: 10px;
        }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            transition: transform 0.3s ease;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn:hover { transform: translateY(-2px); }
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/auth" class="back-btn">← Back to Dashboard</a>
        
        <div class="header">
            <h1>🖥️ Server Authentication Configuration</h1>
            <p>Configure per-server access control and permissions</p>
        </div>
        
        <div class="alert alert-success" id="successAlert"></div>
        <div class="alert alert-error" id="errorAlert"></div>
        
        <div class="config-section">
            <h2 class="section-title">Configure Server Authentication</h2>
            <form id="configForm">
                <div class="form-group">
                    <label class="form-label">Server ID</label>
                    <input type="text" id="serverId" class="form-input" required
                           placeholder="e.g., memory-server">
                </div>
                
                <div class="form-group">
                    <label class="form-label">
                        <input type="checkbox" id="authRequired" class="form-checkbox" checked>
                        Authentication Required
                    </label>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Allowed Roles (comma-separated)</label>
                    <input type="text" id="allowedRoles" class="form-input"
                           placeholder="admin,user">
                </div>
                
                <div class="form-group">
                    <label class="form-label">Allowed Users (comma-separated user IDs)</label>
                    <input type="text" id="allowedUsers" class="form-input"
                           placeholder="user_123,user_456">
                </div>
                
                <div class="form-group">
                    <label class="form-label">Tool Permissions (JSON format)</label>
                    <textarea id="toolPermissions" class="form-textarea" rows="4"
                              placeholder='{"store_memory": ["admin", "user"], "delete_memory": ["admin"]}'></textarea>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Rate Limits (JSON format)</label>
                    <textarea id="rateLimits" class="form-textarea" rows="3"
                              placeholder='{"admin": 1000, "user": 100, "readonly": 50}'></textarea>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Audit Level</label>
                    <select id="auditLevel" class="form-select">
                        <option value="minimal">Minimal</option>
                        <option value="standard" selected>Standard</option>
                        <option value="detailed">Detailed</option>
                    </select>
                </div>
                
                <button type="submit" class="btn btn-primary">Configure Server</button>
            </form>
        </div>
    </div>
    
    <script>
        // Handle form submission
        document.getElementById('configForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const serverId = document.getElementById('serverId').value;
            
            // Parse JSON fields
            let toolPermissions = {};
            let rateLimits = {};
            
            try {
                const toolPermsText = document.getElementById('toolPermissions').value;
                if (toolPermsText) {
                    toolPermissions = JSON.parse(toolPermsText);
                }
            } catch (e) {
                showError('Invalid JSON in Tool Permissions field');
                return;
            }
            
            try {
                const rateLimitsText = document.getElementById('rateLimits').value;
                if (rateLimitsText) {
                    rateLimits = JSON.parse(rateLimitsText);
                }
            } catch (e) {
                showError('Invalid JSON in Rate Limits field');
                return;
            }
            
            const formData = {
                auth_required: document.getElementById('authRequired').checked,
                allowed_roles: document.getElementById('allowedRoles').value ? 
                              document.getElementById('allowedRoles').value.split(',').map(s => s.trim()) : null,
                allowed_users: document.getElementById('allowedUsers').value ? 
                              document.getElementById('allowedUsers').value.split(',').map(s => s.trim()) : null,
                tool_permissions: Object.keys(toolPermissions).length > 0 ? toolPermissions : null,
                rate_limits: Object.keys(rateLimits).length > 0 ? rateLimits : null,
                audit_level: document.getElementById('auditLevel').value
            };
            
            try {
                const response = await fetch(`/api/auth/servers/${serverId}/config`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showSuccess('Server authentication configured successfully');
                    document.getElementById('configForm').reset();
                } else {
                    showError('Failed to configure server: ' + result.error);
                }
            } catch (error) {
                showError('Error configuring server: ' + error.message);
            }
        });
        
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
    </script>
</body>
</html>
        """
    
    def _get_security_html(self) -> str:
        """Generate security analytics HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Hub - Security Analytics</title>
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
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .back-btn {
            display: inline-block;
            margin-bottom: 20px;
            padding: 10px 20px;
            background: #6c757d;
            color: white;
            text-decoration: none;
            border-radius: 8px;
        }
        .analytics-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        .analytics-section, .audit-section {
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
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            transition: transform 0.3s ease;
            margin-right: 10px;
            margin-bottom: 10px;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-secondary { background: #6c757d; color: white; }
        .btn:hover { transform: translateY(-2px); }
        .data-display {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 15px;
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 0.9em;
            max-height: 400px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/auth" class="back-btn">← Back to Dashboard</a>
        
        <div class="header">
            <h1>📊 Security Analytics</h1>
            <p>Monitor security events, analyze patterns, and review audit logs</p>
        </div>
        
        <div class="analytics-grid">
            <div class="analytics-section">
                <h2 class="section-title">Security Analytics</h2>
                <button class="btn btn-primary" onclick="loadAnalytics(7)">Last 7 Days</button>
                <button class="btn btn-secondary" onclick="loadAnalytics(30)">Last 30 Days</button>
                <button class="btn btn-secondary" onclick="loadAnalytics(1)">Last 24 Hours</button>
                
                <div id="analyticsDisplay" class="data-display">
                    Click a button above to load security analytics...
                </div>
            </div>
            
            <div class="audit-section">
                <h2 class="section-title">Audit Events</h2>
                <button class="btn btn-primary" onclick="loadAuditEvents()">All Events</button>
                <button class="btn btn-secondary" onclick="loadAuditEvents('login_failed')">Failed Logins</button>
                <button class="btn btn-secondary" onclick="loadAuditEvents(null, null, null, 'high')">High Risk</button>
                
                <div id="auditDisplay" class="data-display">
                    Click a button above to load audit events...
                </div>
            </div>
        </div>
    </div>
    
    <script>
        async function loadAnalytics(days) {
            const display = document.getElementById('analyticsDisplay');
            display.textContent = 'Loading analytics...';
            
            try {
                const response = await fetch(`/api/auth/security/analytics?days=${days}`);
                const result = await response.json();
                
                if (result.success) {
                    display.textContent = result.data;
                } else {
                    display.textContent = 'Error loading analytics: ' + result.error;
                }
            } catch (error) {
                display.textContent = 'Error loading analytics: ' + error.message;
            }
        }
        
        async function loadAuditEvents(eventType = null, userId = null, hours = 24, riskLevel = null) {
            const display = document.getElementById('auditDisplay');
            display.textContent = 'Loading audit events...';
            
            const params = new URLSearchParams();
            if (eventType) params.append('event_type', eventType);
            if (userId) params.append('user_id', userId);
            if (hours) params.append('hours', hours);
            if (riskLevel) params.append('risk_level', riskLevel);
            
            try {
                const response = await fetch(`/api/auth/security/events?${params}`);
                const result = await response.json();
                
                if (result.success) {
                    display.textContent = result.data;
                } else {
                    display.textContent = 'Error loading audit events: ' + result.error;
                }
            } catch (error) {
                display.textContent = 'Error loading audit events: ' + error.message;
            }
        }
        
        // Load initial analytics
        document.addEventListener('DOMContentLoaded', () => {
            loadAnalytics(7);
            loadAuditEvents();
        });
    </script>
</body>
</html>
        """