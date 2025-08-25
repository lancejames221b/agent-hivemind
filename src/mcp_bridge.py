#!/usr/bin/env python3
"""
hAIveMind MCP Bridge Service
Bridges local MCP servers to remote access through hAIveMind network
Enables distributed MCP collaboration across machines
"""

import asyncio
import json
import logging
import os
import subprocess
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import aiohttp
from aiohttp import web
import asyncio
import signal
import psutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPServerBridge:
    """Represents a bridged MCP server"""
    
    def __init__(self, server_id: str, config: Dict[str, Any], storage=None):
        self.server_id = server_id
        self.config = config
        self.storage = storage
        self.process = None
        self.status = "stopped"
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.request_count = 0
        self.error_count = 0
        self.bridge_type = config.get('type', 'stdio')  # stdio, http, sse
        
        # Bridge configuration
        self.name = config.get('name', f'bridged-mcp-{server_id}')
        self.command = config.get('command', [])
        self.args = config.get('args', [])
        self.env = config.get('env', {})
        self.working_directory = config.get('working_directory', os.getcwd())
        self.bridge_endpoint = f"/mcp-bridge/{server_id}"
        
        # Local server connection details
        self.local_host = config.get('local_host', 'localhost')
        self.local_port = config.get('local_port')
        
        # Protocol translation settings
        self.translation_mode = config.get('translation_mode', 'auto')  # auto, stdio_to_http, http_to_sse
        
    async def start_bridge(self):
        """Start the bridge connection to local MCP server"""
        try:
            if self.bridge_type == 'stdio':
                await self._start_stdio_bridge()
            elif self.bridge_type == 'http':
                await self._start_http_bridge()
            else:
                raise ValueError(f"Unsupported bridge type: {self.bridge_type}")
            
            self.status = "running"
            logger.info(f"MCP Bridge {self.server_id} started successfully")
            
        except Exception as e:
            self.status = "failed"
            self.error_count += 1
            logger.error(f"Failed to start MCP Bridge {self.server_id}: {str(e)}")
            raise
    
    async def _start_stdio_bridge(self):
        """Start bridge for stdio-based MCP server"""
        if not self.command:
            raise ValueError("Command required for stdio bridge")
        
        # Start the local MCP server process
        cmd = [self.command] + self.args if isinstance(self.command, str) else self.command + self.args
        
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.working_directory,
            env={**os.environ, **self.env}
        )
        
        # Start background task to handle stdio communication
        asyncio.create_task(self._handle_stdio_communication())
        
    async def _start_http_bridge(self):
        """Start bridge for HTTP-based MCP server"""
        # For HTTP servers, we just need to validate the connection
        if not self.local_port:
            raise ValueError("Local port required for HTTP bridge")
        
        # Test connection to local HTTP server
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://{self.local_host}:{self.local_port}/health') as response:
                    if response.status != 200:
                        raise Exception(f"Local server not healthy: {response.status}")
        except Exception as e:
            logger.warning(f"Could not verify local HTTP server health: {str(e)}")
    
    async def _handle_stdio_communication(self):
        """Handle communication with stdio-based MCP server"""
        try:
            # Initialize MCP connection
            await self._initialize_mcp()
            
            # Keep process alive
            while self.process and self.process.returncode is None:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in stdio communication for {self.server_id}: {str(e)}")
            self.status = "error"
    
    async def _initialize_mcp(self):
        """Initialize MCP connection with proper handshake"""
        if not self.process:
            raise Exception("No process to initialize")
        
        # Send initialize request
        init_request = {
            "id": "init",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {}
                },
                "clientInfo": {
                    "name": "hAIveMind-Bridge",
                    "version": "1.0.0"
                }
            },
            "jsonrpc": "2.0"
        }
        
        request_json = json.dumps(init_request) + '\n'
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # Wait for initialize response
        response_line = await self.process.stdout.readline()
        if response_line:
            response = json.loads(response_line.decode())
            logger.info(f"MCP Bridge {self.server_id} initialized: {response}")
        
        # Send initialized notification
        initialized_notification = {
            "method": "notifications/initialized",
            "params": {},
            "jsonrpc": "2.0"
        }
        
        notification_json = json.dumps(initialized_notification) + '\n'
        self.process.stdin.write(notification_json.encode())
        await self.process.stdin.drain()
    
    async def proxy_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Proxy a request to the local MCP server"""
        self.request_count += 1
        self.last_activity = datetime.utcnow()
        
        try:
            if self.bridge_type == 'stdio':
                return await self._proxy_stdio_request(method, params)
            elif self.bridge_type == 'http':
                return await self._proxy_http_request(method, params)
            else:
                raise ValueError(f"Unsupported bridge type: {self.bridge_type}")
                
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error proxying request to {self.server_id}: {str(e)}")
            raise
    
    async def _proxy_stdio_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Proxy request to stdio MCP server"""
        if not self.process or self.process.returncode is not None:
            raise Exception("Local MCP server process not running")
        
        # Create JSON-RPC request
        request_id = str(uuid.uuid4())
        request = {
            "id": request_id,
            "method": method,
            "params": params,
            "jsonrpc": "2.0"
        }
        
        # Send request to stdin
        request_json = json.dumps(request) + '\n'
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # Read response from stdout
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise Exception("No response from local MCP server")
        
        response = json.loads(response_line.decode())
        return response
    
    async def _proxy_http_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Proxy request to HTTP MCP server"""
        url = f'http://{self.local_host}:{self.local_port}/mcp'
        
        request_data = {
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
            "jsonrpc": "2.0"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=request_data) as response:
                if response.status != 200:
                    raise Exception(f"HTTP request failed: {response.status}")
                return await response.json()
    
    async def stop_bridge(self):
        """Stop the bridge connection"""
        try:
            if self.process:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=10.0)
                except asyncio.TimeoutError:
                    self.process.kill()
                    await self.process.wait()
                self.process = None
            
            self.status = "stopped"
            logger.info(f"MCP Bridge {self.server_id} stopped")
            
        except Exception as e:
            logger.error(f"Error stopping MCP Bridge {self.server_id}: {str(e)}")
            self.status = "error"
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bridge status"""
        return {
            "server_id": self.server_id,
            "name": self.name,
            "status": self.status,
            "bridge_type": self.bridge_type,
            "bridge_endpoint": self.bridge_endpoint,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "request_count": self.request_count,
            "error_count": self.error_count,
            "process_running": self.process is not None and self.process.returncode is None,
            "config": {
                "command": self.command,
                "args": self.args,
                "working_directory": self.working_directory,
                "local_host": self.local_host,
                "local_port": self.local_port
            }
        }

class MCPBridgeManager:
    """Manages multiple MCP server bridges"""
    
    def __init__(self, storage=None):
        self.storage = storage
        self.bridges: Dict[str, MCPServerBridge] = {}
        self.discovery_paths = [
            Path.home() / '.claude' / 'claude_desktop_config.json',
            Path.cwd() / '.mcp.json',
            Path.cwd() / 'mcp.json',
        ]
        
    async def discover_local_servers(self) -> List[Dict[str, Any]]:
        """Discover local MCP servers from configuration files"""
        discovered = []
        
        for config_path in self.discovery_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    
                    # Handle different configuration formats
                    servers = config.get('mcpServers', {})
                    if not servers and 'servers' in config:
                        servers = config['servers']
                    
                    for server_name, server_config in servers.items():
                        discovered.append({
                            "name": server_name,
                            "config_file": str(config_path),
                            "command": server_config.get('command'),
                            "args": server_config.get('args', []),
                            "env": server_config.get('env', {}),
                            "type": self._detect_server_type(server_config)
                        })
                        
                except Exception as e:
                    logger.warning(f"Error reading config file {config_path}: {str(e)}")
        
        return discovered
    
    def _detect_server_type(self, server_config: Dict[str, Any]) -> str:
        """Detect the type of MCP server (stdio, http, sse)"""
        command = server_config.get('command', '')
        args = server_config.get('args', [])
        
        # Check if it's using HTTP transport
        if any('http://' in str(arg) for arg in args):
            return 'http'
        elif any('sse' in str(arg) for arg in args):
            return 'sse'
        else:
            return 'stdio'  # Default to stdio
    
    async def register_bridge(self, config: Dict[str, Any]) -> str:
        """Register a new MCP server bridge"""
        server_id = str(uuid.uuid4())
        
        # Create bridge instance
        bridge = MCPServerBridge(server_id, config, self.storage)
        self.bridges[server_id] = bridge
        
        # Start the bridge
        await bridge.start_bridge()
        
        # Store bridge configuration in memory if storage available
        if self.storage:
            await self._store_bridge_config(server_id, config)
        
        logger.info(f"Registered MCP Bridge: {bridge.name} ({server_id})")
        return server_id
    
    async def _store_bridge_config(self, server_id: str, config: Dict[str, Any]):
        """Store bridge configuration in hAIveMind memory"""
        try:
            memory_content = f"MCP Bridge registered: {config.get('name', server_id)}\n"
            memory_content += f"Bridge ID: {server_id}\n"
            memory_content += f"Type: {config.get('type', 'stdio')}\n"
            memory_content += f"Command: {config.get('command')}\n"
            memory_content += f"Endpoint: /mcp-bridge/{server_id}\n"
            memory_content += f"Configuration: {json.dumps(config, indent=2)}"
            
            await self.storage.store_memory(
                content=memory_content,
                category="infrastructure",
                context=f"MCP Bridge registration - {config.get('name')}",
                tags=["mcp-bridge", "infrastructure", "remote-access", config.get('name', server_id)]
            )
        except Exception as e:
            logger.warning(f"Could not store bridge config in memory: {str(e)}")
    
    async def get_bridge(self, server_id: str) -> Optional[MCPServerBridge]:
        """Get a bridge by server ID"""
        return self.bridges.get(server_id)
    
    async def list_bridges(self) -> List[Dict[str, Any]]:
        """List all registered bridges"""
        return [bridge.get_status() for bridge in self.bridges.values()]
    
    async def remove_bridge(self, server_id: str) -> bool:
        """Remove a bridge"""
        bridge = self.bridges.get(server_id)
        if not bridge:
            return False
        
        # Stop the bridge
        await bridge.stop_bridge()
        
        # Remove from registry
        del self.bridges[server_id]
        
        logger.info(f"Removed MCP Bridge: {server_id}")
        return True
    
    async def proxy_request(self, server_id: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Proxy a request to a specific bridge"""
        bridge = self.bridges.get(server_id)
        if not bridge:
            raise ValueError(f"Bridge not found: {server_id}")
        
        if bridge.status != "running":
            raise ValueError(f"Bridge not running: {server_id} (status: {bridge.status})")
        
        return await bridge.proxy_request(method, params)
    
    async def get_bridge_status(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific bridge"""
        bridge = self.bridges.get(server_id)
        return bridge.get_status() if bridge else None
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all bridges"""
        total_bridges = len(self.bridges)
        running_bridges = sum(1 for bridge in self.bridges.values() if bridge.status == "running")
        error_bridges = sum(1 for bridge in self.bridges.values() if bridge.status == "error")
        
        return {
            "total_bridges": total_bridges,
            "running_bridges": running_bridges,
            "error_bridges": error_bridges,
            "success_rate": running_bridges / total_bridges if total_bridges > 0 else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def cleanup_inactive_bridges(self, max_idle_hours: int = 24):
        """Clean up bridges that have been inactive"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_idle_hours)
        
        inactive_bridges = []
        for server_id, bridge in list(self.bridges.items()):
            if bridge.last_activity < cutoff_time and bridge.status != "running":
                inactive_bridges.append(server_id)
        
        for server_id in inactive_bridges:
            await self.remove_bridge(server_id)
            logger.info(f"Cleaned up inactive bridge: {server_id}")
        
        return len(inactive_bridges)

# Global bridge manager instance
bridge_manager = None

def get_bridge_manager(storage=None) -> MCPBridgeManager:
    """Get or create the global bridge manager"""
    global bridge_manager
    if bridge_manager is None:
        bridge_manager = MCPBridgeManager(storage)
    return bridge_manager

if __name__ == "__main__":
    # Test the bridge manager
    async def test_bridge():
        manager = get_bridge_manager()
        
        # Discover local servers
        discovered = await manager.discover_local_servers()
        print(f"Discovered {len(discovered)} local MCP servers:")
        for server in discovered:
            print(f"  - {server['name']}: {server['command']} {' '.join(server['args'])}")
        
        # Health check
        health = await manager.health_check()
        print(f"Bridge Manager Health: {health}")
    
    asyncio.run(test_bridge())