#!/usr/bin/env python3
"""
hAIveMind MCP Server Hosting Service
Enables hosting of custom MCP servers directly on hAIveMind infrastructure
"""

import asyncio
import json
import logging
import os
import psutil
import signal
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import shutil
import zipfile
import tarfile

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPServerProcess:
    """Represents a hosted MCP server process"""
    
    def __init__(self, server_id: str, config: Dict[str, Any], storage=None):
        self.server_id = server_id
        self.config = config
        self.storage = storage
        self.process = None
        self.start_time = None
        self.restart_count = 0
        self.last_restart = None
        self.status = "stopped"
        self.health_check_failures = 0
        self.resource_usage = {}
        self.logs = []
        self.max_log_entries = 1000
        
        # Server configuration
        self.name = config.get('name', f'mcp-server-{server_id}')
        self.description = config.get('description', '')
        self.command = config.get('command', [])
        self.working_dir = config.get('working_dir')
        self.env_vars = config.get('environment', {})
        self.auto_restart = config.get('auto_restart', True)
        self.max_restarts = config.get('max_restarts', 5)
        self.restart_delay = config.get('restart_delay', 5)
        self.health_check_url = config.get('health_check_url')
        self.health_check_interval = config.get('health_check_interval', 30)
        self.resource_limits = config.get('resource_limits', {})
        
        # Security settings
        self.sandboxed = config.get('sandboxed', True)
        self.allowed_network = config.get('allowed_network', True)
        self.allowed_filesystem = config.get('allowed_filesystem', ['read'])
        self.user = config.get('user', 'nobody')
        
        logger.info(f"🏗️ MCP server process initialized: {self.name} ({self.server_id})")
    
    async def start(self) -> bool:
        """Start the MCP server process"""
        try:
            if self.process and self.process.poll() is None:
                logger.warning(f"⚠️ MCP server {self.name} is already running")
                return True
            
            logger.info(f"🚀 Starting MCP server: {self.name}")
            
            # Prepare environment
            env = os.environ.copy()
            env.update(self.env_vars)
            
            # Security: Set up sandboxing if enabled
            preexec_fn = None
            if self.sandboxed:
                preexec_fn = self._setup_sandbox
            
            # Start the process
            self.process = subprocess.Popen(
                self.command,
                cwd=self.working_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=preexec_fn,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.start_time = time.time()
            self.status = "starting"
            
            # Wait a moment to check if it started successfully
            await asyncio.sleep(1)
            
            if self.process.poll() is None:
                self.status = "running"
                logger.info(f"✅ MCP server {self.name} started successfully (PID: {self.process.pid})")
                
                # Store server start event in hAIveMind
                if self.storage:
                    await self._store_server_event("started", {
                        "pid": self.process.pid,
                        "command": self.command,
                        "working_dir": self.working_dir
                    })
                
                # Start log monitoring
                asyncio.create_task(self._monitor_logs())
                
                return True
            else:
                self.status = "failed"
                return_code = self.process.poll()
                logger.error(f"❌ MCP server {self.name} failed to start (exit code: {return_code})")
                return False
                
        except Exception as e:
            self.status = "error"
            logger.error(f"💥 Error starting MCP server {self.name}: {e}")
            return False
    
    async def stop(self, timeout: int = 10) -> bool:
        """Stop the MCP server process"""
        try:
            if not self.process or self.process.poll() is not None:
                logger.info(f"🛑 MCP server {self.name} is not running")
                self.status = "stopped"
                return True
            
            logger.info(f"🛑 Stopping MCP server: {self.name}")
            
            # Try graceful shutdown first
            self.process.terminate()
            
            try:
                self.process.wait(timeout=timeout)
                logger.info(f"✅ MCP server {self.name} stopped gracefully")
            except subprocess.TimeoutExpired:
                logger.warning(f"⚠️ MCP server {self.name} didn't stop gracefully, forcing...")
                self.process.kill()
                self.process.wait()
                logger.info(f"💀 MCP server {self.name} force stopped")
            
            self.status = "stopped"
            
            # Store server stop event in hAIveMind
            if self.storage:
                await self._store_server_event("stopped", {
                    "uptime_seconds": time.time() - self.start_time if self.start_time else 0,
                    "restart_count": self.restart_count
                })
            
            return True
            
        except Exception as e:
            logger.error(f"💥 Error stopping MCP server {self.name}: {e}")
            return False
    
    async def restart(self) -> bool:
        """Restart the MCP server process"""
        logger.info(f"🔄 Restarting MCP server: {self.name}")
        
        # Check restart limits
        if self.restart_count >= self.max_restarts:
            logger.error(f"❌ MCP server {self.name} has exceeded max restarts ({self.max_restarts})")
            self.status = "failed"
            return False
        
        # Stop current process
        await self.stop()
        
        # Wait restart delay
        if self.restart_delay > 0:
            logger.info(f"⏳ Waiting {self.restart_delay}s before restart...")
            await asyncio.sleep(self.restart_delay)
        
        # Increment restart count
        self.restart_count += 1
        self.last_restart = time.time()
        
        # Start again
        success = await self.start()
        
        if success:
            logger.info(f"✅ MCP server {self.name} restarted successfully (attempt {self.restart_count})")
        else:
            logger.error(f"❌ MCP server {self.name} restart failed (attempt {self.restart_count})")
        
        return success
    
    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the MCP server"""
        status = {
            "server_id": self.server_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "pid": self.process.pid if self.process and self.process.poll() is None else None,
            "start_time": self.start_time,
            "uptime_seconds": time.time() - self.start_time if self.start_time else 0,
            "restart_count": self.restart_count,
            "last_restart": self.last_restart,
            "health_check_failures": self.health_check_failures,
            "resource_usage": self.resource_usage,
            "recent_logs": self.logs[-10:] if self.logs else []
        }
        
        # Get current resource usage if running
        if self.process and self.process.poll() is None:
            try:
                proc = psutil.Process(self.process.pid)
                self.resource_usage = {
                    "cpu_percent": proc.cpu_percent(),
                    "memory_mb": proc.memory_info().rss / 1024 / 1024,
                    "memory_percent": proc.memory_percent(),
                    "num_threads": proc.num_threads(),
                    "open_files": len(proc.open_files()),
                    "connections": len(proc.connections())
                }
                status["resource_usage"] = self.resource_usage
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return status
    
    async def health_check(self) -> bool:
        """Perform health check on the MCP server"""
        try:
            # Basic process check
            if not self.process or self.process.poll() is not None:
                return False
            
            # HTTP health check if configured
            if self.health_check_url:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(self.health_check_url, timeout=5) as response:
                            if response.status == 200:
                                self.health_check_failures = 0
                                return True
                            else:
                                self.health_check_failures += 1
                                return False
                    except:
                        self.health_check_failures += 1
                        return False
            
            # Resource limit checks
            if self.resource_limits:
                try:
                    proc = psutil.Process(self.process.pid)
                    
                    # Check memory limit
                    if "memory_mb" in self.resource_limits:
                        memory_mb = proc.memory_info().rss / 1024 / 1024
                        if memory_mb > self.resource_limits["memory_mb"]:
                            logger.warning(f"⚠️ MCP server {self.name} exceeds memory limit: {memory_mb:.1f}MB > {self.resource_limits['memory_mb']}MB")
                            return False
                    
                    # Check CPU limit
                    if "cpu_percent" in self.resource_limits:
                        cpu_percent = proc.cpu_percent()
                        if cpu_percent > self.resource_limits["cpu_percent"]:
                            logger.warning(f"⚠️ MCP server {self.name} exceeds CPU limit: {cpu_percent:.1f}% > {self.resource_limits['cpu_percent']}%")
                            return False
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return False
            
            self.health_check_failures = 0
            return True
            
        except Exception as e:
            logger.error(f"💥 Health check error for {self.name}: {e}")
            self.health_check_failures += 1
            return False
    
    def _setup_sandbox(self):
        """Set up process sandboxing (called in child process)"""
        try:
            # Drop privileges if running as root
            if os.getuid() == 0 and self.user != 'root':
                import pwd
                try:
                    pw_record = pwd.getpwnam(self.user)
                    os.setgid(pw_record.pw_gid)
                    os.setuid(pw_record.pw_uid)
                except KeyError:
                    logger.warning(f"⚠️ User {self.user} not found, running as current user")
            
            # Set resource limits
            import resource
            
            # Limit memory if specified
            if "memory_mb" in self.resource_limits:
                memory_bytes = self.resource_limits["memory_mb"] * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
            
            # Limit CPU time if specified
            if "cpu_seconds" in self.resource_limits:
                cpu_seconds = self.resource_limits["cpu_seconds"]
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
            
            # Limit number of processes
            if "max_processes" in self.resource_limits:
                max_proc = self.resource_limits["max_processes"]
                resource.setrlimit(resource.RLIMIT_NPROC, (max_proc, max_proc))
            
        except Exception as e:
            logger.error(f"💥 Sandbox setup error: {e}")
    
    async def _monitor_logs(self):
        """Monitor process logs and store them"""
        try:
            while self.process and self.process.poll() is None:
                # Read stdout
                if self.process.stdout:
                    line = self.process.stdout.readline()
                    if line:
                        self._add_log_entry("stdout", line.strip())
                
                # Read stderr
                if self.process.stderr:
                    line = self.process.stderr.readline()
                    if line:
                        self._add_log_entry("stderr", line.strip())
                
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"💥 Log monitoring error for {self.name}: {e}")
    
    def _add_log_entry(self, stream: str, message: str):
        """Add a log entry"""
        entry = {
            "timestamp": time.time(),
            "stream": stream,
            "message": message
        }
        
        self.logs.append(entry)
        
        # Keep only recent logs
        if len(self.logs) > self.max_log_entries:
            self.logs = self.logs[-self.max_log_entries:]
        
        # Log important messages
        if stream == "stderr" or "error" in message.lower():
            logger.warning(f"🔴 {self.name} [{stream}]: {message}")
        elif logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"📝 {self.name} [{stream}]: {message}")
    
    async def _store_server_event(self, event_type: str, data: Dict[str, Any]):
        """Store server event in hAIveMind memory"""
        try:
            if self.storage:
                await self.storage.store_memory(
                    content=f"MCP server {self.name} {event_type}",
                    category="infrastructure",
                    context=f"MCP server hosting event: {event_type}",
                    metadata={
                        "server_id": self.server_id,
                        "server_name": self.name,
                        "event_type": event_type,
                        "timestamp": time.time(),
                        **data
                    },
                    tags=["mcp-hosting", "server-event", event_type, self.server_id]
                )
        except Exception as e:
            logger.error(f"💥 Error storing server event: {e}")


class MCPServerHost:
    """Main MCP Server Hosting Service"""
    
    def __init__(self, config: Dict[str, Any], storage=None):
        self.config = config
        self.storage = storage
        self.servers = {}  # server_id -> MCPServerProcess
        self.host_config = config.get('mcp_hosting', {})
        
        # Host configuration
        self.enabled = self.host_config.get('enabled', True)
        self.servers_dir = Path(self.host_config.get('servers_dir', 'data/mcp_servers'))
        self.uploads_dir = Path(self.host_config.get('uploads_dir', 'data/mcp_uploads'))
        self.logs_dir = Path(self.host_config.get('logs_dir', 'data/mcp_logs'))
        self.max_servers = self.host_config.get('max_servers', 10)
        self.health_check_interval = self.host_config.get('health_check_interval', 30)
        self.auto_cleanup = self.host_config.get('auto_cleanup', True)
        self.cleanup_interval = self.host_config.get('cleanup_interval', 3600)
        
        # Security settings
        self.security = self.host_config.get('security', {})
        self.allowed_languages = self.security.get('allowed_languages', ['python', 'node', 'bash'])
        self.sandbox_by_default = self.security.get('sandbox_by_default', True)
        self.max_upload_size = self.security.get('max_upload_size_mb', 100) * 1024 * 1024
        self.scan_uploads = self.security.get('scan_uploads', True)
        
        # Create directories
        self.servers_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Background tasks
        self._health_check_task = None
        self._cleanup_task = None
        
        logger.info(f"🏭 MCP Server Host initialized - max servers: {self.max_servers}")
    
    async def start(self):
        """Start the MCP server hosting service"""
        if not self.enabled:
            logger.info("🚫 MCP server hosting is disabled")
            return
        
        logger.info("🚀 Starting MCP server hosting service...")
        
        # Start background tasks
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        if self.auto_cleanup:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Load existing servers
        await self._load_existing_servers()
        
        logger.info(f"✅ MCP server hosting service started - {len(self.servers)} servers loaded")
    
    async def stop(self):
        """Stop the MCP server hosting service"""
        logger.info("🛑 Stopping MCP server hosting service...")
        
        # Cancel background tasks
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Stop all servers
        for server in self.servers.values():
            await server.stop()
        
        logger.info("✅ MCP server hosting service stopped")
    
    async def upload_server(self, 
                           name: str,
                           archive_data: bytes,
                           config: Dict[str, Any],
                           user_id: str = "default") -> Dict[str, Any]:
        """Upload and deploy a new MCP server"""
        try:
            # Validate upload size
            if len(archive_data) > self.max_upload_size:
                raise ValueError(f"Upload too large: {len(archive_data)} bytes > {self.max_upload_size} bytes")
            
            # Check server limit
            if len(self.servers) >= self.max_servers:
                raise ValueError(f"Maximum number of servers reached: {self.max_servers}")
            
            # Generate server ID
            server_id = str(uuid.uuid4())
            
            # Create server directory
            server_dir = self.servers_dir / server_id
            server_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract archive
            archive_path = self.uploads_dir / f"{server_id}.zip"
            with open(archive_path, 'wb') as f:
                f.write(archive_data)
            
            await self._extract_archive(archive_path, server_dir)
            
            # Validate and process configuration
            server_config = await self._process_server_config(config, server_dir, user_id)
            
            # Security scan if enabled
            if self.scan_uploads:
                scan_result = await self._security_scan(server_dir)
                if not scan_result['safe']:
                    raise ValueError(f"Security scan failed: {scan_result['reason']}")
            
            # Create server process
            server = MCPServerProcess(server_id, server_config, self.storage)
            self.servers[server_id] = server
            
            # Save server configuration
            config_path = server_dir / "server_config.json"
            with open(config_path, 'w') as f:
                json.dump(server_config, f, indent=2)
            
            # Store deployment event in hAIveMind
            if self.storage:
                await self.storage.store_memory(
                    content=f"MCP server '{name}' uploaded and deployed",
                    category="infrastructure",
                    context="MCP server deployment",
                    metadata={
                        "server_id": server_id,
                        "server_name": name,
                        "user_id": user_id,
                        "config": server_config,
                        "deployment_time": time.time()
                    },
                    tags=["mcp-hosting", "deployment", server_id, name.lower().replace(' ', '-')]
                )
            
            logger.info(f"📦 MCP server '{name}' uploaded successfully (ID: {server_id})")
            
            return {
                "server_id": server_id,
                "name": name,
                "status": "deployed",
                "message": f"Server '{name}' uploaded and ready to start"
            }
            
        except Exception as e:
            logger.error(f"💥 Error uploading MCP server '{name}': {e}")
            raise
    
    async def start_server(self, server_id: str) -> Dict[str, Any]:
        """Start a hosted MCP server"""
        try:
            if server_id not in self.servers:
                raise ValueError(f"Server not found: {server_id}")
            
            server = self.servers[server_id]
            success = await server.start()
            
            if success:
                logger.info(f"✅ MCP server {server.name} started successfully")
                return {
                    "server_id": server_id,
                    "status": "started",
                    "message": f"Server {server.name} started successfully"
                }
            else:
                logger.error(f"❌ Failed to start MCP server {server.name}")
                return {
                    "server_id": server_id,
                    "status": "failed",
                    "message": f"Failed to start server {server.name}"
                }
                
        except Exception as e:
            logger.error(f"💥 Error starting server {server_id}: {e}")
            raise
    
    async def stop_server(self, server_id: str) -> Dict[str, Any]:
        """Stop a hosted MCP server"""
        try:
            if server_id not in self.servers:
                raise ValueError(f"Server not found: {server_id}")
            
            server = self.servers[server_id]
            success = await server.stop()
            
            if success:
                logger.info(f"🛑 MCP server {server.name} stopped successfully")
                return {
                    "server_id": server_id,
                    "status": "stopped",
                    "message": f"Server {server.name} stopped successfully"
                }
            else:
                logger.error(f"❌ Failed to stop MCP server {server.name}")
                return {
                    "server_id": server_id,
                    "status": "error",
                    "message": f"Failed to stop server {server.name}"
                }
                
        except Exception as e:
            logger.error(f"💥 Error stopping server {server_id}: {e}")
            raise
    
    async def restart_server(self, server_id: str) -> Dict[str, Any]:
        """Restart a hosted MCP server"""
        try:
            if server_id not in self.servers:
                raise ValueError(f"Server not found: {server_id}")
            
            server = self.servers[server_id]
            success = await server.restart()
            
            if success:
                logger.info(f"🔄 MCP server {server.name} restarted successfully")
                return {
                    "server_id": server_id,
                    "status": "restarted",
                    "message": f"Server {server.name} restarted successfully"
                }
            else:
                logger.error(f"❌ Failed to restart MCP server {server.name}")
                return {
                    "server_id": server_id,
                    "status": "failed",
                    "message": f"Failed to restart server {server.name}"
                }
                
        except Exception as e:
            logger.error(f"💥 Error restarting server {server_id}: {e}")
            raise
    
    async def delete_server(self, server_id: str, force: bool = False) -> Dict[str, Any]:
        """Delete a hosted MCP server"""
        try:
            if server_id not in self.servers:
                raise ValueError(f"Server not found: {server_id}")
            
            server = self.servers[server_id]
            
            # Stop server if running
            if server.status == "running" and not force:
                raise ValueError("Server is running. Stop it first or use force=True")
            
            if server.status == "running":
                await server.stop()
            
            # Remove from active servers
            del self.servers[server_id]
            
            # Clean up files
            server_dir = self.servers_dir / server_id
            if server_dir.exists():
                shutil.rmtree(server_dir)
            
            # Store deletion event in hAIveMind
            if self.storage:
                await self.storage.store_memory(
                    content=f"MCP server '{server.name}' deleted",
                    category="infrastructure",
                    context="MCP server deletion",
                    metadata={
                        "server_id": server_id,
                        "server_name": server.name,
                        "deletion_time": time.time(),
                        "forced": force
                    },
                    tags=["mcp-hosting", "deletion", server_id]
                )
            
            logger.info(f"🗑️ MCP server {server.name} deleted successfully")
            
            return {
                "server_id": server_id,
                "status": "deleted",
                "message": f"Server {server.name} deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"💥 Error deleting server {server_id}: {e}")
            raise
    
    async def get_server_status(self, server_id: str) -> Dict[str, Any]:
        """Get status of a hosted MCP server"""
        try:
            if server_id not in self.servers:
                raise ValueError(f"Server not found: {server_id}")
            
            return await self.servers[server_id].get_status()
            
        except Exception as e:
            logger.error(f"💥 Error getting server status {server_id}: {e}")
            raise
    
    async def list_servers(self) -> List[Dict[str, Any]]:
        """List all hosted MCP servers"""
        try:
            servers = []
            for server_id, server in self.servers.items():
                status = await server.get_status()
                servers.append(status)
            
            return sorted(servers, key=lambda x: x.get('start_time', 0), reverse=True)
            
        except Exception as e:
            logger.error(f"💥 Error listing servers: {e}")
            raise
    
    async def get_server_logs(self, server_id: str, lines: int = 100) -> List[Dict[str, Any]]:
        """Get logs for a hosted MCP server"""
        try:
            if server_id not in self.servers:
                raise ValueError(f"Server not found: {server_id}")
            
            server = self.servers[server_id]
            return server.logs[-lines:] if server.logs else []
            
        except Exception as e:
            logger.error(f"💥 Error getting server logs {server_id}: {e}")
            raise
    
    async def _load_existing_servers(self):
        """Load existing servers from disk"""
        try:
            for server_dir in self.servers_dir.iterdir():
                if server_dir.is_dir():
                    config_path = server_dir / "server_config.json"
                    if config_path.exists():
                        try:
                            with open(config_path) as f:
                                config = json.load(f)
                            
                            server_id = server_dir.name
                            server = MCPServerProcess(server_id, config, self.storage)
                            self.servers[server_id] = server
                            
                            logger.info(f"📂 Loaded existing server: {server.name} ({server_id})")
                            
                        except Exception as e:
                            logger.error(f"💥 Error loading server from {server_dir}: {e}")
                            
        except Exception as e:
            logger.error(f"💥 Error loading existing servers: {e}")
    
    async def _extract_archive(self, archive_path: Path, extract_dir: Path):
        """Extract uploaded archive"""
        try:
            if archive_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif archive_path.suffix.lower() in ['.tar', '.tar.gz', '.tgz']:
                with tarfile.open(archive_path, 'r:*') as tar_ref:
                    tar_ref.extractall(extract_dir)
            else:
                raise ValueError(f"Unsupported archive format: {archive_path.suffix}")
            
            # Clean up archive
            archive_path.unlink()
            
        except Exception as e:
            logger.error(f"💥 Error extracting archive: {e}")
            raise
    
    async def _process_server_config(self, config: Dict[str, Any], server_dir: Path, user_id: str) -> Dict[str, Any]:
        """Process and validate server configuration"""
        try:
            # Set defaults
            processed_config = {
                "name": config.get("name", "Unnamed MCP Server"),
                "description": config.get("description", ""),
                "command": config.get("command", []),
                "working_dir": str(server_dir),
                "environment": config.get("environment", {}),
                "auto_restart": config.get("auto_restart", True),
                "max_restarts": min(config.get("max_restarts", 5), 10),
                "restart_delay": max(config.get("restart_delay", 5), 1),
                "health_check_url": config.get("health_check_url"),
                "health_check_interval": max(config.get("health_check_interval", 30), 10),
                "resource_limits": config.get("resource_limits", {}),
                "sandboxed": config.get("sandboxed", self.sandbox_by_default),
                "allowed_network": config.get("allowed_network", True),
                "allowed_filesystem": config.get("allowed_filesystem", ["read"]),
                "user": config.get("user", "nobody"),
                "uploaded_by": user_id,
                "upload_time": time.time()
            }
            
            # Validate command
            if not processed_config["command"]:
                raise ValueError("Command is required")
            
            # Detect language and set appropriate defaults
            command_str = " ".join(processed_config["command"])
            if "python" in command_str.lower():
                language = "python"
            elif "node" in command_str.lower() or "npm" in command_str.lower():
                language = "node"
            elif "bash" in command_str.lower() or "sh" in command_str.lower():
                language = "bash"
            else:
                language = "unknown"
            
            if language not in self.allowed_languages:
                raise ValueError(f"Language '{language}' not allowed. Allowed: {self.allowed_languages}")
            
            processed_config["detected_language"] = language
            
            # Set resource limits if not specified
            if not processed_config["resource_limits"]:
                default_limits = {
                    "python": {"memory_mb": 512, "cpu_percent": 50},
                    "node": {"memory_mb": 256, "cpu_percent": 30},
                    "bash": {"memory_mb": 128, "cpu_percent": 20}
                }
                processed_config["resource_limits"] = default_limits.get(language, {"memory_mb": 256, "cpu_percent": 30})
            
            return processed_config
            
        except Exception as e:
            logger.error(f"💥 Error processing server config: {e}")
            raise
    
    async def _security_scan(self, server_dir: Path) -> Dict[str, Any]:
        """Perform basic security scan on uploaded server"""
        try:
            # List of potentially dangerous patterns
            dangerous_patterns = [
                "rm -rf",
                "sudo",
                "chmod 777",
                "eval(",
                "exec(",
                "system(",
                "shell_exec",
                "passthru",
                "__import__",
                "subprocess.call",
                "os.system"
            ]
            
            # Scan all text files
            for file_path in server_dir.rglob("*"):
                if file_path.is_file() and file_path.stat().st_size < 1024 * 1024:  # Max 1MB files
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                            for pattern in dangerous_patterns:
                                if pattern in content:
                                    return {
                                        "safe": False,
                                        "reason": f"Dangerous pattern '{pattern}' found in {file_path.name}"
                                    }
                    except:
                        continue  # Skip binary or unreadable files
            
            return {"safe": True, "reason": "No dangerous patterns detected"}
            
        except Exception as e:
            logger.error(f"💥 Security scan error: {e}")
            return {"safe": False, "reason": f"Security scan failed: {e}"}
    
    async def _health_check_loop(self):
        """Background health check loop"""
        try:
            while True:
                await asyncio.sleep(self.health_check_interval)
                
                for server_id, server in list(self.servers.items()):
                    try:
                        is_healthy = await server.health_check()
                        
                        if not is_healthy and server.auto_restart:
                            logger.warning(f"⚠️ MCP server {server.name} is unhealthy, attempting restart...")
                            await server.restart()
                        
                    except Exception as e:
                        logger.error(f"💥 Health check error for {server.name}: {e}")
                        
        except asyncio.CancelledError:
            logger.info("🛑 Health check loop cancelled")
        except Exception as e:
            logger.error(f"💥 Health check loop error: {e}")
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval)
                
                # Clean up old log files
                try:
                    cutoff_time = time.time() - (7 * 24 * 3600)  # 7 days
                    for log_file in self.logs_dir.glob("*.log"):
                        if log_file.stat().st_mtime < cutoff_time:
                            log_file.unlink()
                            logger.debug(f"🧹 Cleaned up old log file: {log_file}")
                except Exception as e:
                    logger.error(f"💥 Log cleanup error: {e}")
                
                # Clean up failed servers
                try:
                    for server_id, server in list(self.servers.items()):
                        if server.status == "failed" and server.restart_count >= server.max_restarts:
                            logger.info(f"🧹 Cleaning up failed server: {server.name}")
                            await self.delete_server(server_id, force=True)
                except Exception as e:
                    logger.error(f"💥 Server cleanup error: {e}")
                        
        except asyncio.CancelledError:
            logger.info("🛑 Cleanup loop cancelled")
        except Exception as e:
            logger.error(f"💥 Cleanup loop error: {e}")