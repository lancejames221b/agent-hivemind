#!/usr/bin/env python3
"""
Enhanced Dashboard Server for hAIveMind Control System
Extends the remote MCP server with comprehensive management capabilities
"""
import os
import asyncio
import json
import jwt
import secrets
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, Request, Form, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import jinja2

from database import ControlDatabase, UserRole, DeviceStatus, KeyStatus
from playbook_engine import PlaybookEngine, load_playbook_content, PlaybookValidationError
from config_generator import ConfigGenerator, ConfigFormat, create_config_generator
from pathlib import Path
import uuid

# Import Confluence dashboard if available
try:
    from confluence_dashboard import ConfluenceDashboard
    CONFLUENCE_DASHBOARD_AVAILABLE = True
except ImportError:
    CONFLUENCE_DASHBOARD_AVAILABLE = False

# Request/Response Models
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterDeviceRequest(BaseModel):
    device_id: str
    machine_id: str
    hostname: str
    metadata: Dict[str, Any] = {}

class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "viewer"

class GenerateKeyRequest(BaseModel):
    device_id: str
    name: str
    scopes: List[str] = ["mcp:read", "mcp:write"]
    expires_hours: Optional[int] = None

class MCPConfigRequest(BaseModel):
    device_id: str
    format: str = "claude_desktop"  # or "claude_code", "custom", "mcp_json", "yaml", "shell_script", "docker_compose"
    include_auth: bool = True
    auth_expires_hours: Optional[int] = None
    server_filter: Optional[List[str]] = None

class ConfigGenerateRequest(BaseModel):
    user_id: str
    device_id: str
    formats: List[str]
    include_auth: bool = True
    auth_expires_hours: Optional[int] = None
    server_filter: Optional[List[str]] = None

class ConfigDownloadRequest(BaseModel):
    config_id: str
    format: str

class DashboardServer:
    def __init__(self, db_path: str = "database/haivemind.db"):
        self.db = ControlDatabase(db_path)
        self.app = FastAPI(title="hAIveMind Control Dashboard", version="2.0.0")
        self.security = HTTPBearer(auto_error=False)
        
        # JWT configuration
        self.jwt_secret = os.environ.get('HAIVEMIND_JWT_SECRET', 'change-this-secret-key')
        
        # Setup Jinja2 templates
        self.templates = jinja2.Environment(
            loader=jinja2.FileSystemLoader("admin/templates") if Path("admin/templates").exists() 
            else jinja2.DictLoader(self._get_default_templates())
        )
        
        # Initialize Confluence dashboard if available
        self.confluence_dashboard = None
        if CONFLUENCE_DASHBOARD_AVAILABLE:
            try:
                # Load config for Confluence integration
                config_path = Path("config/config.json")
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    
                    self.confluence_dashboard = ConfluenceDashboard(
                        config, self.db, None  # haivemind_storage will be set later
                    )
            except Exception as e:
                print(f"Failed to initialize Confluence dashboard: {e}")
        
        self.setup_routes()
        self.mount_static_files()
        # Lazy-init playbook engine (shell disabled by default)
        self.playbook_engine = PlaybookEngine(allow_unsafe_shell=False)
        # Memory storage for hAIveMind awareness (initialized lazily when needed)
        self._memory_storage = None
        # Configuration generator (initialized lazily when needed)
        self._config_generator = None

    def _get_config(self) -> dict:
        try:
            cfg_path = Path(__file__).parent.parent / "config" / "config.json"
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _get_memory_storage(self):
        if self._memory_storage is not None:
            return self._memory_storage
        try:
            from memory_server import MemoryStorage
            cfg = self._get_config()
            self._memory_storage = MemoryStorage(cfg)
            return self._memory_storage
        except Exception:
            return None
    
    def _get_config_generator(self):
        if self._config_generator is not None:
            return self._config_generator
        try:
            cfg = self._get_config()
            memory_storage = self._get_memory_storage()
            self._config_generator = ConfigGenerator(cfg, memory_storage)
            return self._config_generator
        except Exception as e:
            print(f"Failed to initialize config generator: {e}")
            return None
    
    def setup_routes(self):
        """Setup all dashboard routes"""
        
        # Include Confluence dashboard routes if available
        if self.confluence_dashboard:
            self.app.include_router(self.confluence_dashboard.get_router())
        
        # Static file serving
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            return FileResponse("admin/login.html")
        
        @self.app.get("/admin/{file_path:path}")
        async def serve_admin_files(file_path: str):
            file_full_path = Path(f"admin/{file_path}")
            if file_full_path.exists() and file_full_path.is_file():
                return FileResponse(file_full_path)
            raise HTTPException(status_code=404, detail="File not found")
        
        # Authentication Routes
        @self.app.post("/api/v1/auth/login")
        async def login(request: LoginRequest, req: Request):
            """User login endpoint"""
            try:
                if not self.db.verify_password(request.username, request.password):
                    self.db.log_access(
                        None, None, None, "login", None,
                        req.client.host, req.headers.get("user-agent", ""),
                        False, "Invalid credentials"
                    )
                    raise HTTPException(status_code=401, detail="Invalid credentials")
                
                user = self.db.get_user_by_username(request.username)
                if not user:
                    raise HTTPException(status_code=401, detail="User not found")
                
                # Generate JWT token
                token_payload = {
                    'user_id': user.id,
                    'username': user.username,
                    'role': user.role.value,
                    'exp': datetime.utcnow() + timedelta(hours=24),
                    'iat': datetime.utcnow(),
                    'iss': 'haivemind-dashboard'
                }
                
                token = jwt.encode(token_payload, self.jwt_secret, algorithm='HS256')
                
                # Update last login
                self.db.update_last_login(user.id)
                
                # Log successful login
                self.db.log_access(
                    user.id, None, None, "login", None,
                    req.client.host, req.headers.get("user-agent", ""),
                    True
                )
                
                return {
                    "token": token,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "role": user.role.value
                    }
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/auth/verify")
        async def verify_token(current_user: dict = Depends(self.get_current_user)):
            """Verify JWT token and return user info"""
            return {
                "user": {
                    "id": current_user['user_id'],
                    "username": current_user['username'],
                    "role": current_user['role']
                }
            }
        
        @self.app.post("/api/v1/auth/register")
        async def register_user(request: CreateUserRequest, current_user: dict = Depends(self.get_current_user)):
            """Register new user (admin only)"""
            if current_user['role'] != 'admin':
                raise HTTPException(status_code=403, detail="Admin access required")
            
            try:
                role = UserRole(request.role)
                user_id = self.db.create_user(request.username, request.email, request.password, role)
                return {"success": True, "user_id": user_id}
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # Device Management Routes
        @self.app.post("/api/v1/devices/register")
        async def register_device(request: RegisterDeviceRequest, req: Request,
                                current_user: dict = Depends(self.get_current_user)):
            """Register a new device"""
            try:
                device_id = self.db.register_device(
                    request.device_id,
                    request.machine_id,
                    request.hostname,
                    current_user['user_id'],
                    request.metadata,
                    req.client.host
                )
                return {"success": True, "device_id": device_id, "status": "pending_approval"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/devices")
        async def list_devices(status: Optional[str] = None, 
                             current_user: dict = Depends(self.get_current_user)):
            """List devices"""
            try:
                device_status = DeviceStatus(status) if status else None
                owner_id = None if current_user['role'] == 'admin' else current_user['user_id']
                
                devices = self.db.list_devices(device_status, owner_id)
                return [
                    {
                        "id": d.id,
                        "device_id": d.device_id,
                        "machine_id": d.machine_id,
                        "hostname": d.hostname,
                        "status": d.status.value,
                        "metadata": d.metadata,
                        "created_at": d.created_at.isoformat(),
                        "approved_at": d.approved_at.isoformat() if d.approved_at else None,
                        "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                        "ip_address": d.ip_address
                    }
                    for d in devices
                ]
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/devices/{device_id}/approve")
        async def approve_device(device_id: str, current_user: dict = Depends(self.get_current_user)):
            """Approve a pending device (admin only)"""
            if current_user['role'] != 'admin':
                raise HTTPException(status_code=403, detail="Admin access required")
            
            success = self.db.approve_device(device_id, current_user['user_id'])
            if not success:
                raise HTTPException(status_code=404, detail="Device not found or already approved")
            
            return {"success": True}
        
        # API Key Management Routes
        @self.app.post("/api/v1/keys/generate")
        async def generate_api_key(request: GenerateKeyRequest, 
                                 current_user: dict = Depends(self.get_current_user)):
            """Generate new API key for device"""
            try:
                # Get device and verify ownership/permissions
                device = self.db.get_device(request.device_id)
                if not device:
                    raise HTTPException(status_code=404, detail="Device not found")
                
                if current_user['role'] != 'admin' and device.owner_id != current_user['user_id']:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                if device.status != DeviceStatus.APPROVED:
                    raise HTTPException(status_code=400, detail="Device must be approved first")
                
                key_id, raw_key = self.db.generate_api_key(
                    device.id, current_user['user_id'], request.name,
                    request.scopes, request.expires_hours
                )
                
                return {
                    "key_id": key_id,
                    "key": raw_key,
                    "scopes": request.scopes,
                    "expires_hours": request.expires_hours,
                    "warning": "Save this key securely - it won't be shown again!"
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/api/v1/keys/{key_id}")
        async def revoke_api_key(key_id: str, current_user: dict = Depends(self.get_current_user)):
            """Revoke an API key"""
            success = self.db.revoke_api_key(key_id)
            if not success:
                raise HTTPException(status_code=404, detail="API key not found")
            
            return {"success": True}
        
        # MCP Configuration Routes
        @self.app.post("/api/v1/config/generate")
        async def generate_mcp_config(request: MCPConfigRequest,
                                    current_user: dict = Depends(self.get_current_user)):
            """Generate MCP configuration file"""
            try:
                device = self.db.get_device(request.device_id)
                if not device:
                    raise HTTPException(status_code=404, detail="Device not found")
                
                if current_user['role'] != 'admin' and device.owner_id != current_user['user_id']:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Use new configuration generator
                config_generator = self._get_config_generator()
                if not config_generator:
                    raise HTTPException(status_code=500, detail="Configuration generator not available")
                
                # Map format string to enum
                format_map = {
                    "claude_desktop": ConfigFormat.CLAUDE_DESKTOP,
                    "claude_code": ConfigFormat.CLAUDE_CODE,
                    "custom": ConfigFormat.CUSTOM_JSON,
                    "mcp_json": ConfigFormat.MCP_JSON,
                    "yaml": ConfigFormat.YAML,
                    "shell_script": ConfigFormat.SHELL_SCRIPT,
                    "docker_compose": ConfigFormat.DOCKER_COMPOSE
                }
                
                config_format = format_map.get(request.format, ConfigFormat.CLAUDE_DESKTOP)
                
                # Generate configuration
                client_config = config_generator.generate_client_config(
                    user_id=str(current_user['user_id']),
                    device_id=request.device_id,
                    format=config_format,
                    include_auth=request.include_auth,
                    auth_expires_hours=request.auth_expires_hours,
                    server_filter=request.server_filter
                )
                
                config_string = config_generator.template_engine.generate(client_config)
                
                # Store in hAIveMind memory
                await config_generator.store_config_memory(client_config, "generated")
                
                # Get suggestions for improvement
                suggestions = await config_generator.suggest_configuration_improvements(client_config)
                
                # Parse config for JSON response (if it's JSON format)
                config_data = config_string
                if request.format in ["claude_desktop", "claude_code", "custom", "mcp_json"]:
                    try:
                        config_data = json.loads(config_string)
                    except:
                        pass
                
                return {
                    "config": config_data,
                    "config_string": config_string,
                    "format": request.format,
                    "device_id": device.device_id,
                    "client_id": client_config.client_id,
                    "suggestions": suggestions,
                    "generated_at": datetime.utcnow().isoformat()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/config/generate-multiple")
        async def generate_multiple_configs(request: ConfigGenerateRequest,
                                          current_user: dict = Depends(self.get_current_user)):
            """Generate configurations in multiple formats"""
            try:
                # Verify device access
                device = self.db.get_device(request.device_id)
                if not device:
                    raise HTTPException(status_code=404, detail="Device not found")
                
                if current_user['role'] != 'admin' and device.owner_id != current_user['user_id']:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                config_generator = self._get_config_generator()
                if not config_generator:
                    raise HTTPException(status_code=500, detail="Configuration generator not available")
                
                # Map format strings to enums
                format_map = {
                    "claude_desktop": ConfigFormat.CLAUDE_DESKTOP,
                    "claude_code": ConfigFormat.CLAUDE_CODE,
                    "custom": ConfigFormat.CUSTOM_JSON,
                    "mcp_json": ConfigFormat.MCP_JSON,
                    "yaml": ConfigFormat.YAML,
                    "shell_script": ConfigFormat.SHELL_SCRIPT,
                    "docker_compose": ConfigFormat.DOCKER_COMPOSE
                }
                
                formats = [format_map.get(f, ConfigFormat.CLAUDE_DESKTOP) for f in request.formats]
                
                # Generate multiple configurations
                configs = config_generator.generate_multiple_formats(
                    user_id=request.user_id,
                    device_id=request.device_id,
                    formats=formats,
                    include_auth=request.include_auth,
                    auth_expires_hours=request.auth_expires_hours
                )
                
                return {
                    "configs": configs,
                    "device_id": request.device_id,
                    "generated_at": datetime.utcnow().isoformat()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/config/download/{format}")
        async def download_config(format: str, device_id: str,
                                current_user: dict = Depends(self.get_current_user)):
            """Download configuration file"""
            try:
                device = self.db.get_device(device_id)
                if not device:
                    raise HTTPException(status_code=404, detail="Device not found")
                
                if current_user['role'] != 'admin' and device.owner_id != current_user['user_id']:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                config_generator = self._get_config_generator()
                if not config_generator:
                    raise HTTPException(status_code=500, detail="Configuration generator not available")
                
                # Map format to enum
                format_map = {
                    "claude_desktop": ConfigFormat.CLAUDE_DESKTOP,
                    "claude_code": ConfigFormat.CLAUDE_CODE,
                    "custom": ConfigFormat.CUSTOM_JSON,
                    "mcp_json": ConfigFormat.MCP_JSON,
                    "yaml": ConfigFormat.YAML,
                    "shell_script": ConfigFormat.SHELL_SCRIPT,
                    "docker_compose": ConfigFormat.DOCKER_COMPOSE
                }
                
                config_format = format_map.get(format, ConfigFormat.CLAUDE_DESKTOP)
                
                # Generate configuration
                config_string = config_generator.generate_config_string(
                    user_id=str(current_user['user_id']),
                    device_id=device_id,
                    format=config_format,
                    include_auth=True
                )
                
                # Determine file extension and content type
                extensions = {
                    "claude_desktop": ".json",
                    "claude_code": ".json", 
                    "custom": ".json",
                    "mcp_json": ".json",
                    "yaml": ".yaml",
                    "shell_script": ".sh",
                    "docker_compose": ".yml"
                }
                
                content_types = {
                    "claude_desktop": "application/json",
                    "claude_code": "application/json",
                    "custom": "application/json", 
                    "mcp_json": "application/json",
                    "yaml": "application/x-yaml",
                    "shell_script": "application/x-sh",
                    "docker_compose": "application/x-yaml"
                }
                
                filename = f"haivemind-{device_id}-{format}{extensions.get(format, '.txt')}"
                content_type = content_types.get(format, "text/plain")
                
                from fastapi.responses import Response
                return Response(
                    content=config_string,
                    media_type=content_type,
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/config/servers")
        async def list_available_servers(current_user: dict = Depends(self.get_current_user)):
            """List available MCP servers for configuration"""
            try:
                config_generator = self._get_config_generator()
                if not config_generator:
                    raise HTTPException(status_code=500, detail="Configuration generator not available")
                
                servers = config_generator.discover_servers()
                
                return {
                    "servers": [
                        {
                            "id": s.id,
                            "name": s.name,
                            "host": s.host,
                            "port": s.port,
                            "transport": s.transport.value,
                            "ssl": s.ssl,
                            "priority": s.priority,
                            "description": s.description,
                            "tags": s.tags,
                            "health_check": s.health_check
                        }
                        for s in servers
                    ]
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/config/analytics")
        async def get_config_analytics(current_user: dict = Depends(self.get_current_user)):
            """Get configuration generation analytics"""
            try:
                config_generator = self._get_config_generator()
                if not config_generator:
                    raise HTTPException(status_code=500, detail="Configuration generator not available")
                
                # Get basic analytics
                analytics = config_generator.get_config_analytics()
                
                # Get hAIveMind usage patterns
                usage_patterns = await config_generator.analyze_client_usage_patterns()
                analytics.update(usage_patterns)
                
                return analytics
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/config/suggestions/{device_id}")
        async def get_config_suggestions(device_id: str, format: str = "claude_desktop",
                                       current_user: dict = Depends(self.get_current_user)):
            """Get configuration improvement suggestions"""
            try:
                device = self.db.get_device(device_id)
                if not device:
                    raise HTTPException(status_code=404, detail="Device not found")
                
                if current_user['role'] != 'admin' and device.owner_id != current_user['user_id']:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                config_generator = self._get_config_generator()
                if not config_generator:
                    raise HTTPException(status_code=500, detail="Configuration generator not available")
                
                # Create a sample config to analyze
                format_map = {
                    "claude_desktop": ConfigFormat.CLAUDE_DESKTOP,
                    "claude_code": ConfigFormat.CLAUDE_CODE,
                    "custom": ConfigFormat.CUSTOM_JSON,
                    "mcp_json": ConfigFormat.MCP_JSON,
                    "yaml": ConfigFormat.YAML,
                    "shell_script": ConfigFormat.SHELL_SCRIPT,
                    "docker_compose": ConfigFormat.DOCKER_COMPOSE
                }
                
                config_format = format_map.get(format, ConfigFormat.CLAUDE_DESKTOP)
                
                client_config = config_generator.generate_client_config(
                    user_id=str(current_user['user_id']),
                    device_id=device_id,
                    format=config_format,
                    include_auth=True
                )
                
                suggestions = await config_generator.suggest_configuration_improvements(client_config)
                
                return {
                    "device_id": device_id,
                    "suggestions": suggestions,
                    "generated_at": datetime.utcnow().isoformat()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/config/performance")
        async def report_client_performance(request: dict, current_user: dict = Depends(self.get_current_user)):
            """Report client performance data for hAIveMind learning"""
            try:
                config_generator = self._get_config_generator()
                if not config_generator:
                    raise HTTPException(status_code=500, detail="Configuration generator not available")
                
                client_id = request.get('client_id')
                performance_data = request.get('performance_data', {})
                
                if not client_id:
                    raise HTTPException(status_code=400, detail="client_id is required")
                
                await config_generator.learn_from_client_performance(client_id, performance_data)
                
                return {
                    "success": True,
                    "message": "Performance data recorded successfully"
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Dashboard Stats
        @self.app.get("/api/v1/admin/stats")
        async def get_dashboard_stats(current_user: dict = Depends(self.get_current_user)):
            """Get dashboard statistics"""
            stats = self.db.get_dashboard_stats()
            return stats
        
        @self.app.get("/admin/api/stats")
        async def get_dashboard_stats_legacy(current_user: dict = Depends(self.get_current_user)):
            """Get dashboard statistics (legacy route)"""
            stats = self.db.get_dashboard_stats()
            return stats
        
        # MCP Server Management Endpoints
        @self.app.get("/api/v1/mcp/servers")
        async def get_mcp_servers(current_user: dict = Depends(self.get_current_user)):
            """Get all MCP servers with health status"""
            try:
                servers = self.db.get_mcp_servers()
                health_records = {h.server_id: h for h in self.db.get_all_server_health()}
                
                server_list = []
                for server in servers:
                    health = health_records.get(server.id)
                    server_data = {
                        "id": server.id,
                        "name": server.name,
                        "server_type": server.server_type.value,
                        "endpoint": server.endpoint,
                        "description": server.description,
                        "enabled": server.enabled,
                        "priority": server.priority,
                        "tags": server.tags,
                        "created_at": server.created_at.isoformat(),
                        "health": {
                            "status": health.status.value if health else "unknown",
                            "response_time_ms": health.response_time_ms if health else None,
                            "error_message": health.error_message if health else None,
                            "tools_available": health.tools_available if health else [],
                            "last_check": health.last_check.isoformat() if health else None,
                            "consecutive_failures": health.consecutive_failures if health else 0
                        }
                    }
                    server_list.append(server_data)
                
                return {"servers": server_list}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/mcp/servers")
        async def create_mcp_server(request: dict, current_user: dict = Depends(self.get_current_user)):
            """Create a new MCP server"""
            try:
                from database import MCPServerType
                
                # Validate required fields
                required_fields = ['name', 'server_type', 'endpoint']
                for field in required_fields:
                    if field not in request:
                        raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
                
                # Validate server_type
                try:
                    server_type = MCPServerType(request['server_type'])
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid server_type")
                
                server_id = self.db.add_mcp_server(
                    name=request['name'],
                    server_type=server_type,
                    endpoint=request['endpoint'],
                    description=request.get('description'),
                    config=request.get('config', {}),
                    auth_config=request.get('auth_config'),
                    created_by=current_user['user_id'],
                    priority=request.get('priority', 100),
                    tags=request.get('tags', [])
                )
                
                return {"server_id": server_id, "message": "MCP server created successfully"}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/mcp/servers/{server_id}")
        async def get_mcp_server(server_id: int, current_user: dict = Depends(self.get_current_user)):
            """Get specific MCP server details"""
            try:
                server = self.db.get_mcp_server(server_id)
                if not server:
                    raise HTTPException(status_code=404, detail="MCP server not found")
                
                health = self.db.get_server_health(server_id)
                
                server_data = {
                    "id": server.id,
                    "name": server.name,
                    "server_type": server.server_type.value,
                    "endpoint": server.endpoint,
                    "description": server.description,
                    "config": server.config,
                    "auth_config": server.auth_config,
                    "enabled": server.enabled,
                    "priority": server.priority,
                    "tags": server.tags,
                    "created_at": server.created_at.isoformat(),
                    "created_by": server.created_by,
                    "health": {
                        "status": health.status.value if health else "unknown",
                        "response_time_ms": health.response_time_ms if health else None,
                        "error_message": health.error_message if health else None,
                        "tools_available": health.tools_available if health else [],
                        "last_check": health.last_check.isoformat() if health else None,
                        "consecutive_failures": health.consecutive_failures if health else 0
                    }
                }
                
                return server_data
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.put("/api/v1/mcp/servers/{server_id}")
        async def update_mcp_server(server_id: int, request: dict, current_user: dict = Depends(self.get_current_user)):
            """Update MCP server configuration"""
            try:
                from database import MCPServerType
                
                server = self.db.get_mcp_server(server_id)
                if not server:
                    raise HTTPException(status_code=404, detail="MCP server not found")
                
                # Validate server_type if provided
                server_type = None
                if 'server_type' in request:
                    try:
                        server_type = MCPServerType(request['server_type'])
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid server_type")
                
                success = self.db.update_mcp_server(
                    server_id=server_id,
                    name=request.get('name'),
                    server_type=server_type,
                    endpoint=request.get('endpoint'),
                    description=request.get('description'),
                    config=request.get('config'),
                    auth_config=request.get('auth_config'),
                    enabled=request.get('enabled'),
                    priority=request.get('priority'),
                    tags=request.get('tags')
                )
                
                if success:
                    return {"message": "MCP server updated successfully"}
                else:
                    raise HTTPException(status_code=400, detail="No fields to update")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/api/v1/mcp/servers/{server_id}")
        async def delete_mcp_server(server_id: int, current_user: dict = Depends(self.get_current_user)):
            """Delete MCP server"""
            try:
                server = self.db.get_mcp_server(server_id)
                if not server:
                    raise HTTPException(status_code=404, detail="MCP server not found")
                
                success = self.db.delete_mcp_server(server_id)
                if success:
                    return {"message": "MCP server deleted successfully"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to delete MCP server")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/mcp/servers/{server_id}/toggle")
        async def toggle_mcp_server(server_id: int, current_user: dict = Depends(self.get_current_user)):
            """Toggle MCP server enabled/disabled state"""
            try:
                server = self.db.get_mcp_server(server_id)
                if not server:
                    raise HTTPException(status_code=404, detail="MCP server not found")
                
                new_state = not server.enabled
                success = self.db.update_mcp_server(server_id, enabled=new_state)
                
                if success:
                    return {
                        "message": f"MCP server {'enabled' if new_state else 'disabled'} successfully",
                        "enabled": new_state
                    }
                else:
                    raise HTTPException(status_code=500, detail="Failed to toggle MCP server")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # ================= Playbook Management =================

        class PlaybookCreate(BaseModel):
            name: str
            category: str
            tags: Optional[List[str]] = None

        class PlaybookVersionCreate(BaseModel):
            content: str
            format: str = "yaml"  # yaml|json
            metadata: Optional[Dict[str, Any]] = None
            changelog: Optional[str] = None

        class PlaybookExecuteRequest(BaseModel):
            version_id: Optional[int] = None  # default: latest
            parameters: Optional[Dict[str, Any]] = None
            dry_run: bool = False
            allow_unsafe_shell: bool = False

        class PlaybookImportRequest(BaseModel):
            name: str
            category: str
            content: str
            format: str = "yaml"
            tags: Optional[List[str]] = None
            changelog: Optional[str] = None

        @self.app.post("/api/v1/playbooks")
        async def create_playbook_endpoint(req: PlaybookCreate, current_user: dict = Depends(self.get_current_user)):
            try:
                pb_id = self.db.create_playbook(req.name, req.category, current_user['user_id'], req.tags or [])
                return {"playbook_id": pb_id}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/playbooks")
        async def list_playbooks_endpoint(category: Optional[str] = None, q: Optional[str] = None, current_user: dict = Depends(self.get_current_user)):
            try:
                return self.db.list_playbooks(category, q)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/playbooks/{playbook_id}")
        async def get_playbook_endpoint(playbook_id: int, current_user: dict = Depends(self.get_current_user)):
            pb = self.db.get_playbook(playbook_id)
            if not pb:
                raise HTTPException(status_code=404, detail="Playbook not found")
            return pb

        @self.app.delete("/api/v1/playbooks/{playbook_id}")
        async def delete_playbook_endpoint(playbook_id: int, current_user: dict = Depends(self.get_current_user)):
            if current_user['role'] != 'admin':
                raise HTTPException(status_code=403, detail="Admin access required")
            try:
                ok = self.db.delete_playbook(playbook_id)
                if not ok:
                    raise HTTPException(status_code=404, detail="Playbook not found")
                return {"success": True}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/v1/playbooks/{playbook_id}/versions")
        async def add_playbook_version_endpoint(playbook_id: int, req: PlaybookVersionCreate, current_user: dict = Depends(self.get_current_user)):
            try:
                # Validate content early
                try:
                    load_playbook_content(req.content)
                except PlaybookValidationError as ve:
                    raise HTTPException(status_code=400, detail=str(ve))
                version_id = self.db.add_playbook_version(
                    playbook_id=playbook_id,
                    content=req.content,
                    format=req.format,
                    metadata=req.metadata or {},
                    changelog=req.changelog,
                    created_by=current_user['user_id']
                )
                return {"version_id": version_id}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/v1/playbooks/{playbook_id}/execute")
        async def execute_playbook_endpoint(playbook_id: int, req: PlaybookExecuteRequest, current_user: dict = Depends(self.get_current_user)):
            pb = self.db.get_playbook(playbook_id)
            if not pb:
                raise HTTPException(status_code=404, detail="Playbook not found")
            version_id = req.version_id or pb.get('latest_version_id')
            if not version_id:
                raise HTTPException(status_code=400, detail="No versions available for this playbook")
            version = self.db.get_playbook_version(version_id)
            if not version:
                raise HTTPException(status_code=404, detail="Playbook version not found")

            # Parse content
            try:
                spec = load_playbook_content(version['content'])
            except PlaybookValidationError as ve:
                raise HTTPException(status_code=400, detail=str(ve))

            # Start execution record
            run_id = str(uuid.uuid4())
            self.db.start_playbook_execution(
                playbook_id=playbook_id,
                version_id=version_id,
                run_id=run_id,
                parameters=req.parameters or {},
                context={"triggered_by_username": current_user['username']},
                triggered_by=current_user['user_id']
            )

            async def _runner():
                engine = PlaybookEngine(allow_unsafe_shell=bool(req.allow_unsafe_shell))
                if req.dry_run:
                    # Validate only
                    try:
                        engine.validate(spec)
                        self.db.complete_playbook_execution(run_id, status="success", success=True, step_results=[], log_text="Dry-run validation passed")
                    except Exception as e:
                        self.db.complete_playbook_execution(run_id, status="failed", success=False, step_results=[], log_text=f"Dry-run validation failed: {e}")
                    return
                try:
                    ok, step_results, out_vars = await engine.execute(spec, req.parameters or {})
                    # Serialize results
                    sr = [r.__dict__ for r in step_results]
                    self.db.complete_playbook_execution(run_id, status=("success" if ok else "failed"), success=ok, step_results=sr, log_text="")
                    # hAIveMind memory recording
                    storage = self._get_memory_storage()
                    if storage is not None:
                        summary = f"Playbook '{pb['name']}' v{version['version']} {'succeeded' if ok else 'failed'} in {len(step_results)} step(s)."
                        metadata = {
                            'playbook_id': playbook_id,
                            'version_id': version_id,
                            'run_id': run_id,
                            'category': pb['category'],
                            'success': ok,
                            'steps': [
                                {
                                    'id': r.step_id,
                                    'name': r.name,
                                    'status': r.status,
                                    'duration_ms': int((r.finished_at - r.started_at) * 1000),
                                    'error': r.error,
                                }
                                for r in step_results
                            ],
                            'parameters': req.parameters or {},
                        }
                        try:
                            await storage.store_memory(
                                content=summary,
                                category="runbooks",
                                context=f"Playbook execution: {pb['name']} (run {run_id})",
                                metadata=metadata,
                                tags=["playbook", pb['category'], "success" if ok else "failure"],
                                user_id=str(current_user['user_id'])
                            )
                        except Exception:
                            pass
                except Exception as e:
                    self.db.complete_playbook_execution(run_id, status="failed", success=False, step_results=[], log_text=str(e))

            # Fire and forget execution (non-blocking)
            asyncio.create_task(_runner())
            return {"run_id": run_id, "status": "started"}

        @self.app.get("/api/v1/playbooks/{playbook_id}/executions")
        async def list_executions_endpoint(playbook_id: int, current_user: dict = Depends(self.get_current_user)):
            return self.db.list_executions(playbook_id)

        @self.app.get("/api/v1/playbook-executions/{run_id}")
        async def get_execution_endpoint(run_id: str, current_user: dict = Depends(self.get_current_user)):
            ex = self.db.get_execution(run_id)
            if not ex:
                raise HTTPException(status_code=404, detail="Execution not found")
            return ex

        @self.app.post("/api/v1/playbooks/import")
        async def import_playbook_endpoint(req: PlaybookImportRequest, current_user: dict = Depends(self.get_current_user)):
            try:
                # Validate content parses
                load_playbook_content(req.content)
                pb_id = self.db.create_playbook(req.name, req.category, current_user['user_id'], req.tags or [])
                version_id = self.db.add_playbook_version(pb_id, req.content, req.format, {}, req.changelog, current_user['user_id'])
                return {"playbook_id": pb_id, "version_id": version_id}
            except PlaybookValidationError as ve:
                raise HTTPException(status_code=400, detail=str(ve))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/playbooks/{playbook_id}/export")
        async def export_playbook_endpoint(playbook_id: int, current_user: dict = Depends(self.get_current_user)):
            pb = self.db.get_playbook(playbook_id)
            if not pb:
                raise HTTPException(status_code=404, detail="Playbook not found")
            vid = pb.get('latest_version_id')
            if not vid:
                raise HTTPException(status_code=400, detail="No versions available")
            v = self.db.get_playbook_version(vid)
            return {"name": pb['name'], "category": pb['category'], "format": v['format'], "content": v['content']}

        @self.app.get("/api/v1/playbook-templates")
        async def list_playbook_templates(category: Optional[str] = None, current_user: dict = Depends(self.get_current_user)):
            return self.db.list_templates(category)

        class TemplateCreate(BaseModel):
            name: str
            category: str
            description: Optional[str] = None
            format: str = "yaml"
            content: str
            tags: Optional[List[str]] = None

        @self.app.post("/api/v1/playbook-templates")
        async def create_playbook_template(req: TemplateCreate, current_user: dict = Depends(self.get_current_user)):
            try:
                # just basic parse check
                load_playbook_content(req.content)
                tid = self.db.add_template(req.name, req.category, req.format, req.content, req.description, req.tags or [], current_user['user_id'])
                return {"template_id": tid}
            except PlaybookValidationError as ve:
                raise HTTPException(status_code=400, detail=str(ve))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    def mount_static_files(self):
        """Mount static file directories"""
        if Path("admin/static").exists():
            self.app.mount("/admin/static", StaticFiles(directory="admin/static"), name="static")
        if Path(".vibe-images").exists():
            self.app.mount("/.vibe-images", StaticFiles(directory=".vibe-images"), name="vibe-images")
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))) -> dict:
        """Get current authenticated user"""
        if not credentials:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        try:
            payload = jwt.decode(credentials.credentials, self.jwt_secret, algorithms=['HS256'])
            return {
                'user_id': payload['user_id'],
                'username': payload['username'],
                'role': payload['role']
            }
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def _generate_claude_desktop_config(self, device, include_auth: bool) -> dict:
        """Generate Claude Desktop MCP configuration"""
        config = {
            "mcpServers": {
                "haivemind": {
                    "command": "npx",
                    "args": [
                        "@modelcontextprotocol/server-http",
                        f"http://{device.machine_id}:8900/sse"
                    ],
                    "env": {
                        "HTTP_TIMEOUT": "30000"
                    }
                }
            }
        }
        
        if include_auth:
            # Add authentication headers if needed
            config["mcpServers"]["haivemind"]["env"]["AUTHORIZATION"] = "Bearer <your-api-key>"
        
        return config
    
    def _generate_claude_code_config(self, device, include_auth: bool) -> dict:
        """Generate Claude Code CLI configuration"""
        config = {
            "mcp_servers": {
                "haivemind": {
                    "transport": "sse",
                    "url": f"http://{device.machine_id}:8900/sse",
                    "timeout": 30
                }
            }
        }
        
        if include_auth:
            config["mcp_servers"]["haivemind"]["headers"] = {
                "Authorization": "Bearer <your-api-key>"
            }
        
        return config
    
    def _generate_custom_config(self, device, include_auth: bool) -> dict:
        """Generate custom MCP configuration"""
        return {
            "server": {
                "name": "haivemind",
                "version": "2.0.0",
                "endpoints": {
                    "sse": f"http://{device.machine_id}:8900/sse",
                    "http": f"http://{device.machine_id}:8900/mcp",
                    "health": f"http://{device.machine_id}:8900/health"
                }
            },
            "auth": {
                "enabled": include_auth,
                "type": "bearer_token",
                "header": "Authorization"
            } if include_auth else {"enabled": False},
            "features": {
                "memory_storage": True,
                "agent_coordination": True,
                "knowledge_sync": True,
                "broadcast_system": True
            }
        }
    
    def _get_default_templates(self) -> Dict[str, str]:
        """Return default Jinja2 templates if template directory doesn't exist"""
        return {
            "mcp_config.json": """
{
  "mcpServers": {
    "haivemind": {
      "command": "npx",
      "args": [
        "@modelcontextprotocol/server-http", 
        "{{ endpoint }}"
      ],
      "env": {
        "HTTP_TIMEOUT": "30000"
        {% if auth_token %},"AUTHORIZATION": "Bearer {{ auth_token }}"{% endif %}
      }
    }
  }
}
""".strip()
        }

# Standalone server runner
def main():
    import uvicorn
    
    dashboard = DashboardServer()
    print("🚀 Starting hAIveMind Control Dashboard...")
    print("📊 Dashboard: http://localhost:8901/admin/dashboard.html")
    print("🔑 API Docs: http://localhost:8901/docs")
    
    uvicorn.run(dashboard.app, host="0.0.0.0", port=8901)

if __name__ == "__main__":
    main()