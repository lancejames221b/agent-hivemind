#!/usr/bin/env python3
"""
MCP SSE Aggregator Service - ClaudeOps hAIveMind Core Infrastructure
Aggregates multiple MCP servers via SSE and provides unified tool catalog
"""

import asyncio
import json
import logging
import sys
import time
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import aiohttp
from aiohttp import web, ClientSession, ClientTimeout
import redis

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import (
        TextContent, 
        Tool, 
        CallToolRequest, 
        CallToolResult,
        ListToolsRequest,
        ListToolsResult,
        GetPromptRequest,
        GetPromptResult,
        ListPromptsRequest,
        ListPromptsResult,
        ListResourcesRequest,
        ListResourcesResult,
        ReadResourceRequest,
        ReadResourceResult,
    )
except ImportError:
    print("Error: MCP package not found. Install with: pip install mcp")
    sys.exit(1)

from memory_server import MemoryStorage
from auth import AuthManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ServerHealth:
    """Track health status of MCP servers"""
    
    def __init__(self, server_id: str, endpoint: str):
        self.server_id = server_id
        self.endpoint = endpoint
        self.status = 'unknown'
        self.last_check = None
        self.response_time = 0
        self.error_count = 0
        self.consecutive_failures = 0
        self.capabilities = {}
        self.metrics = {
            'requests_per_minute': 0,
            'success_rate': 0,
            'average_response_time': 0
        }


class ServerConnection:
    """Manages connection to a single MCP server"""
    
    def __init__(self, server_id: str, config: Dict[str, Any], memory_storage: Optional[MemoryStorage] = None):
        self.server_id = server_id
        self.config = config
        self.endpoint = config['endpoint']
        self.transport = config.get('transport', 'sse')
        self.priority = config.get('priority', 5)
        self.tools = {}
        self.resources = {}
        self.prompts = {}
        self.health = ServerHealth(server_id, self.endpoint)
        self.session = None
        self.memory_storage = memory_storage
        self._connection_lock = asyncio.Lock()
        self._request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0
        }
    
    async def connect(self) -> bool:
        """Establish connection to MCP server"""
        async with self._connection_lock:
            try:
                timeout = ClientTimeout(total=30)
                self.session = ClientSession(timeout=timeout)
                
                # Test connection and get capabilities
                await self._fetch_capabilities()
                
                self.health.status = 'healthy'
                self.health.last_check = datetime.now()
                self.health.consecutive_failures = 0
                
                # Store connection memory if available
                if self.memory_storage:
                    await self._store_connection_memory('connected')
                
                logger.info(f"✅ Connected to MCP server {self.server_id} at {self.endpoint}")
                return True
                
            except Exception as e:
                self.health.status = 'unreachable'
                self.health.consecutive_failures += 1
                
                if self.memory_storage:
                    await self._store_connection_memory('failed', str(e))
                
                logger.error(f"❌ Failed to connect to {self.server_id}: {e}")
                return False
    
    async def _fetch_capabilities(self):
        """Fetch available tools, resources, and prompts from server"""
        if not self.session:
            return
        
        start_time = time.time()
        
        try:
            # Get tools
            async with self.session.post(f"{self.endpoint.rstrip('/sse')}/message", 
                                       json={"method": "tools/list", "params": {}}) as response:
                if response.status == 200:
                    result = await response.json()
                    if 'result' in result and 'tools' in result['result']:
                        self.tools = {tool['name']: tool for tool in result['result']['tools']}
            
            # Get resources
            try:
                async with self.session.post(f"{self.endpoint.rstrip('/sse')}/message",
                                           json={"method": "resources/list", "params": {}}) as response:
                    if response.status == 200:
                        result = await response.json()
                        if 'result' in result and 'resources' in result['result']:
                            self.resources = {res['uri']: res for res in result['result']['resources']}
            except Exception:
                pass  # Resources are optional
            
            # Get prompts
            try:
                async with self.session.post(f"{self.endpoint.rstrip('/sse')}/message",
                                           json={"method": "prompts/list", "params": {}}) as response:
                    if response.status == 200:
                        result = await response.json()
                        if 'result' in result and 'prompts' in result['result']:
                            self.prompts = {prompt['name']: prompt for prompt in result['result']['prompts']}
            except Exception:
                pass  # Prompts are optional
            
            response_time = (time.time() - start_time) * 1000
            self.health.response_time = response_time
            
            # Update capabilities in health
            self.health.capabilities = {
                'tools': len(self.tools),
                'resources': len(self.resources),
                'prompts': len(self.prompts)
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch capabilities from {self.server_id}: {e}")
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool call on this server"""
        if not self.session:
            raise Exception(f"No connection to server {self.server_id}")
        
        start_time = time.time()
        self._request_stats['total_requests'] += 1
        
        try:
            async with self.session.post(f"{self.endpoint.rstrip('/sse')}/message",
                                       json={
                                           "method": "tools/call",
                                           "params": {
                                               "name": tool_name,
                                               "arguments": arguments
                                           }
                                       }) as response:
                
                response_time = (time.time() - start_time) * 1000
                self._request_stats['total_response_time'] += response_time
                
                if response.status == 200:
                    result = await response.json()
                    self._request_stats['successful_requests'] += 1
                    
                    # Store execution memory
                    if self.memory_storage:
                        await self._store_execution_memory(tool_name, arguments, 'success', response_time)
                    
                    return result.get('result', {})
                else:
                    self._request_stats['failed_requests'] += 1
                    error_text = await response.text()
                    
                    if self.memory_storage:
                        await self._store_execution_memory(tool_name, arguments, 'error', response_time, error_text)
                    
                    raise Exception(f"Server returned {response.status}: {error_text}")
        
        except Exception as e:
            self._request_stats['failed_requests'] += 1
            
            if self.memory_storage:
                await self._store_execution_memory(tool_name, arguments, 'exception', 0, str(e))
            
            raise
    
    async def _store_connection_memory(self, status: str, error: str = None):
        """Store connection event in hAIveMind memory"""
        try:
            memory_data = {
                'server_id': self.server_id,
                'endpoint': self.endpoint,
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'capabilities': self.health.capabilities
            }
            
            if error:
                memory_data['error'] = error
            
            await self.memory_storage.store_memory(
                content=f"MCP server {self.server_id} connection {status}",
                category='infrastructure',
                metadata={
                    'event_type': 'mcp_server_connection',
                    'server_data': json.dumps(memory_data),
                    'aggregator_operation': True
                },
                scope='hive-shared'
            )
        except Exception as e:
            logger.warning(f"Failed to store connection memory: {e}")
    
    async def _store_execution_memory(self, tool_name: str, arguments: Dict, status: str, response_time: float, error: str = None):
        """Store tool execution analytics in hAIveMind memory"""
        try:
            execution_data = {
                'server_id': self.server_id,
                'tool_name': tool_name,
                'status': status,
                'response_time': response_time,
                'timestamp': datetime.now().isoformat(),
                'arguments_hash': hash(str(sorted(arguments.items())))
            }
            
            if error:
                execution_data['error'] = error
            
            await self.memory_storage.store_memory(
                content=f"Tool {tool_name} executed on {self.server_id} - {status}",
                category='infrastructure',
                metadata={
                    'event_type': 'mcp_tool_execution',
                    'execution_data': json.dumps(execution_data),
                    'performance_analytics': True,
                    'aggregator_operation': True
                },
                scope='hive-shared'
            )
        except Exception as e:
            logger.warning(f"Failed to store execution memory: {e}")
    
    async def health_check(self) -> bool:
        """Perform health check on server"""
        try:
            if not self.session:
                await self.connect()
                return self.health.status == 'healthy'
            
            start_time = time.time()
            
            # Try a simple ping or capabilities fetch
            async with self.session.post(f"{self.endpoint.rstrip('/sse')}/message",
                                       json={"method": "tools/list", "params": {}}) as response:
                
                response_time = (time.time() - start_time) * 1000
                self.health.response_time = response_time
                self.health.last_check = datetime.now()
                
                if response.status == 200:
                    self.health.status = 'healthy'
                    self.health.consecutive_failures = 0
                    return True
                else:
                    self.health.status = 'degraded'
                    self.health.consecutive_failures += 1
                    return False
        
        except Exception as e:
            self.health.status = 'unreachable'
            self.health.consecutive_failures += 1
            logger.warning(f"Health check failed for {self.server_id}: {e}")
            return False
    
    async def disconnect(self):
        """Close connection to server"""
        if self.session:
            await self.session.close()
            self.session = None
        
        if self.memory_storage:
            await self._store_connection_memory('disconnected')


class MCPRegistry:
    """Registry for managing MCP servers and routing"""
    
    def __init__(self, config: Dict[str, Any], memory_storage: MemoryStorage):
        self.config = config
        self.memory_storage = memory_storage
        self.servers: Dict[str, ServerConnection] = {}
        self.tool_routing: Dict[str, str] = {}  # tool_name -> server_id
        self.namespace_prefixes: Dict[str, str] = {}  # server_id -> prefix
        
        # Initialize database
        self.db_path = Path(config.get('storage', {}).get('registry_db', 'data/registry.db'))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Initialize Redis if available
        self.redis_client = None
        if config.get('storage', {}).get('redis', {}).get('enable_cache'):
            self._init_redis()
    
    def _init_database(self):
        """Initialize SQLite database for server registry"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS servers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    transport TEXT NOT NULL DEFAULT 'sse',
                    status TEXT NOT NULL DEFAULT 'unknown',
                    priority INTEGER NOT NULL DEFAULT 5,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    config_json TEXT,
                    metadata_json TEXT
                );
                
                CREATE TABLE IF NOT EXISTS server_capabilities (
                    server_id TEXT NOT NULL,
                    capability_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    namespace_prefix TEXT,
                    description TEXT,
                    parameters_json TEXT,
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY (server_id, capability_type, name),
                    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS server_health (
                    server_id TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    response_time INTEGER,
                    error_message TEXT,
                    metrics_json TEXT,
                    PRIMARY KEY (server_id, timestamp),
                    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status);
                CREATE INDEX IF NOT EXISTS idx_servers_priority ON servers(priority);
                CREATE INDEX IF NOT EXISTS idx_capabilities_type ON server_capabilities(capability_type);
                CREATE INDEX IF NOT EXISTS idx_capabilities_name ON server_capabilities(name);
                CREATE INDEX IF NOT EXISTS idx_health_timestamp ON server_health(timestamp);
            ''')
    
    def _init_redis(self):
        """Initialize Redis client"""
        try:
            redis_config = self.config['storage']['redis']
            self.redis_client = redis.Redis(
                host=redis_config['host'],
                port=redis_config['port'],
                db=redis_config['db'],
                password=redis_config.get('password'),
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("✅ Connected to Redis for registry caching")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
    
    async def register_server(self, server_id: str, config: Dict[str, Any]) -> bool:
        """Register a new MCP server"""
        try:
            # Create server connection
            connection = ServerConnection(server_id, config, self.memory_storage)
            
            # Attempt to connect
            if await connection.connect():
                self.servers[server_id] = connection
                
                # Assign namespace prefix
                prefix = self._assign_namespace_prefix(server_id)
                self.namespace_prefixes[server_id] = prefix
                
                # Update tool routing
                await self._update_tool_routing(server_id, connection)
                
                # Store in database
                await self._store_server_config(server_id, config, connection)
                
                # Store registration memory
                await self._store_registration_memory(server_id, 'registered', connection.health.capabilities)
                
                logger.info(f"✅ Registered MCP server {server_id} with prefix {prefix}")
                return True
            else:
                logger.error(f"❌ Failed to register server {server_id} - connection failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to register server {server_id}: {e}")
            await self._store_registration_memory(server_id, 'failed', {}, str(e))
            return False
    
    def _assign_namespace_prefix(self, server_id: str) -> str:
        """Assign namespace prefix to avoid tool name conflicts"""
        # Use server_id as base, with special aliases for common servers
        aliases = {
            'memory-server': 'memory__',
            'haivemind-memory': 'hv__',
            'file-server': 'file__',
            'web-server': 'web__'
        }
        
        return aliases.get(server_id, f"{server_id.replace('-', '_')}__")
    
    async def _update_tool_routing(self, server_id: str, connection: ServerConnection):
        """Update tool routing table"""
        prefix = self.namespace_prefixes[server_id]
        
        # Register tools with and without prefix
        for tool_name, tool_def in connection.tools.items():
            # Prefixed version (always available)
            prefixed_name = f"{prefix}{tool_name}"
            self.tool_routing[prefixed_name] = server_id
            
            # Unprefixed version (only if no conflict)
            if tool_name not in self.tool_routing:
                self.tool_routing[tool_name] = server_id
            
            # Cache in Redis if available
            if self.redis_client:
                self.redis_client.hset(f"tool:routing:{prefixed_name}", 
                                     mapping={"server_id": server_id, "original_name": tool_name})
                if tool_name not in [k for k in self.tool_routing.keys() if not k.startswith(prefix)]:
                    self.redis_client.hset(f"tool:routing:{tool_name}",
                                         mapping={"server_id": server_id, "original_name": tool_name})
    
    async def _store_server_config(self, server_id: str, config: Dict[str, Any], connection: ServerConnection):
        """Store server configuration in database"""
        now = int(time.time())
        
        with sqlite3.connect(self.db_path) as conn:
            # Store server record
            conn.execute('''
                INSERT OR REPLACE INTO servers 
                (id, name, endpoint, transport, status, priority, created_at, updated_at, config_json, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                server_id,
                config.get('name', server_id),
                config['endpoint'],
                config.get('transport', 'sse'),
                connection.health.status,
                config.get('priority', 5),
                now,
                now,
                json.dumps(config),
                json.dumps({'capabilities': connection.health.capabilities})
            ))
            
            # Store capabilities
            for tool_name, tool_def in connection.tools.items():
                conn.execute('''
                    INSERT OR REPLACE INTO server_capabilities
                    (server_id, capability_type, name, original_name, namespace_prefix, description, parameters_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    server_id,
                    'tool',
                    f"{self.namespace_prefixes[server_id]}{tool_name}",
                    tool_name,
                    self.namespace_prefixes[server_id],
                    tool_def.get('description', ''),
                    json.dumps(tool_def.get('inputSchema', {})),
                    now
                ))
    
    async def _store_registration_memory(self, server_id: str, status: str, capabilities: Dict, error: str = None):
        """Store server registration event in hAIveMind memory"""
        try:
            registration_data = {
                'server_id': server_id,
                'status': status,
                'capabilities': capabilities,
                'timestamp': datetime.now().isoformat(),
                'namespace_prefix': self.namespace_prefixes.get(server_id, '')
            }
            
            if error:
                registration_data['error'] = error
            
            await self.memory_storage.store_memory(
                content=f"MCP server {server_id} registration {status}",
                category='infrastructure',
                metadata={
                    'event_type': 'mcp_server_registration',
                    'registration_data': json.dumps(registration_data),
                    'aggregator_operation': True
                },
                scope='hive-shared'
            )
        except Exception as e:
            logger.warning(f"Failed to store registration memory: {e}")
    
    async def route_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route tool call to appropriate server"""
        server_id = self.tool_routing.get(tool_name)
        if not server_id or server_id not in self.servers:
            raise Exception(f"Tool {tool_name} not found or server unavailable")
        
        connection = self.servers[server_id]
        
        # Extract original tool name if prefixed
        original_name = tool_name
        prefix = self.namespace_prefixes.get(server_id, '')
        if tool_name.startswith(prefix):
            original_name = tool_name[len(prefix):]
        
        return await connection.call_tool(original_name, arguments)
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get unified tool catalog from all servers"""
        tools = []
        
        for server_id, connection in self.servers.items():
            prefix = self.namespace_prefixes[server_id]
            
            for tool_name, tool_def in connection.tools.items():
                # Add prefixed version
                prefixed_tool = tool_def.copy()
                prefixed_tool['name'] = f"{prefix}{tool_name}"
                prefixed_tool['server_id'] = server_id
                prefixed_tool['canonical_name'] = f"{prefix}{tool_name}"
                tools.append(prefixed_tool)
                
                # Add unprefixed version if no conflict
                if tool_name in self.tool_routing and self.tool_routing[tool_name] == server_id:
                    unprefixed_tool = tool_def.copy()
                    unprefixed_tool['name'] = tool_name
                    unprefixed_tool['server_id'] = server_id
                    unprefixed_tool['canonical_name'] = f"{prefix}{tool_name}"
                    tools.append(unprefixed_tool)
        
        return tools
    
    async def health_check_all(self) -> Dict[str, Dict]:
        """Perform health checks on all registered servers"""
        health_results = {}
        
        for server_id, connection in self.servers.items():
            is_healthy = await connection.health_check()
            health_results[server_id] = {
                'healthy': is_healthy,
                'status': connection.health.status,
                'response_time': connection.health.response_time,
                'last_check': connection.health.last_check.isoformat() if connection.health.last_check else None,
                'consecutive_failures': connection.health.consecutive_failures,
                'capabilities': connection.health.capabilities
            }
            
            # Store health record
            await self._store_health_record(server_id, connection.health)
        
        return health_results
    
    async def _store_health_record(self, server_id: str, health: ServerHealth):
        """Store health check result in database"""
        now = int(time.time())
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO server_health 
                    (server_id, timestamp, status, response_time, error_message, metrics_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    server_id,
                    now,
                    health.status,
                    int(health.response_time),
                    None,  # No error message for now
                    json.dumps(health.metrics)
                ))
                
                # Clean up old health records (keep last 24 hours)
                cutoff = now - (24 * 3600)
                conn.execute('DELETE FROM server_health WHERE timestamp < ?', (cutoff,))
        
        except Exception as e:
            logger.warning(f"Failed to store health record: {e}")


class MCPAggregatorService:
    """Main MCP SSE Aggregator service"""
    
    def __init__(self, config_path: str = None):
        # Load configuration
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "config" / "config.json")
        
        with open(config_path) as f:
            self.config = json.load(f)
        
        # Initialize components
        self.memory_storage = MemoryStorage(self.config)
        self.auth = AuthManager(self.config)
        self.registry = MCPRegistry(self.config, self.memory_storage)
        
        # Get aggregator config
        aggregator_config = self.config.get('aggregator', {})
        self.host = aggregator_config.get('host', '0.0.0.0')
        self.port = aggregator_config.get('port', 8950)
        
        # Initialize FastMCP server
        self.mcp = FastMCP(
            name="MCP SSE Aggregator",
            host=self.host,
            port=self.port
        )
        
        # Register aggregator tools
        self._register_aggregator_tools()
        
        # Health check task
        self._health_check_task = None
        
        logger.info(f"🔄 MCP SSE Aggregator initialized on {self.host}:{self.port}")
    
    def _register_aggregator_tools(self):
        """Register aggregator management tools"""
        
        @self.mcp.tool()
        async def list_aggregated_tools() -> List[Dict[str, Any]]:
            """List all tools available across registered MCP servers"""
            return self.registry.get_all_tools()
        
        @self.mcp.tool()
        async def get_server_health() -> Dict[str, Dict]:
            """Get health status of all registered MCP servers"""
            return await self.registry.health_check_all()
        
        @self.mcp.tool()
        async def register_mcp_server(server_id: str, endpoint: str, transport: str = "sse", priority: int = 5) -> Dict[str, Any]:
            """Register a new MCP server with the aggregator"""
            config = {
                'endpoint': endpoint,
                'transport': transport,
                'priority': priority,
                'name': server_id
            }
            
            success = await self.registry.register_server(server_id, config)
            return {
                'success': success,
                'server_id': server_id,
                'endpoint': endpoint
            }
        
        # Proxy all registered tools through the aggregator
        async def proxy_tool_call(call_request):
            """Proxy tool calls to appropriate backend servers"""
            tool_name = call_request.params.name
            arguments = call_request.params.arguments or {}
            
            try:
                result = await self.registry.route_tool_call(tool_name, arguments)
                return CallToolResult(content=[TextContent(type="text", text=json.dumps(result))])
            except Exception as e:
                logger.error(f"Tool call failed for {tool_name}: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )
        
        # Override the tool calling mechanism
        self.mcp._handle_call_tool = proxy_tool_call
    
    async def load_static_servers(self):
        """Load servers from static configuration"""
        static_servers = self.config.get('aggregator', {}).get('static_servers', [])
        
        for server_config in static_servers:
            server_id = server_config.get('id')
            if server_id and server_config.get('auto_start', True):
                logger.info(f"Loading static server: {server_id}")
                await self.registry.register_server(server_id, server_config)
    
    async def start_health_monitoring(self):
        """Start background health monitoring"""
        async def health_monitor():
            while True:
                try:
                    await self.registry.health_check_all()
                    await asyncio.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    logger.error(f"Health monitoring error: {e}")
                    await asyncio.sleep(60)  # Wait longer on error
        
        self._health_check_task = asyncio.create_task(health_monitor())
    
    async def run(self):
        """Start the aggregator service"""
        try:
            # Load static servers
            await self.load_static_servers()
            
            # Start health monitoring
            await self.start_health_monitoring()
            
            # Store startup memory
            await self._store_startup_memory()
            
            # Run the MCP server using stdio server approach
            logger.info(f"🚀 Starting MCP SSE Aggregator on {self.host}:{self.port}")
            
            # Use stdio server instead of direct FastMCP run to avoid event loop conflicts
            from mcp.server.stdio import stdio_server
            from mcp.server import Server
            
            # Create a basic MCP server for stdio
            server = Server("mcp-aggregator")
            
            @server.list_tools()
            async def list_tools():
                """List all aggregated tools"""
                tools = []
                for tool_info in self.registry.get_all_tools():
                    tools.append(Tool(
                        name=tool_info['name'],
                        description=tool_info.get('description', ''),
                        inputSchema=tool_info.get('inputSchema', {})
                    ))
                return tools
            
            @server.call_tool()
            async def call_tool(name: str, arguments: dict = None) -> list[TextContent]:
                """Route tool calls to appropriate backend servers"""
                try:
                    result = await self.registry.route_tool_call(name, arguments or {})
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                except Exception as e:
                    return [TextContent(type="text", text=f"Error: {str(e)}")]
            
            # Run stdio server
            async with stdio_server() as streams:
                await server.run(streams[0], streams[1], {})
            
        except Exception as e:
            logger.error(f"Failed to start aggregator service: {e}")
            raise
    
    async def _store_startup_memory(self):
        """Store aggregator startup event in hAIveMind memory"""
        try:
            startup_data = {
                'service': 'mcp_aggregator',
                'endpoint': f"http://{self.host}:{self.port}",
                'registered_servers': list(self.registry.servers.keys()),
                'total_tools': len(self.registry.tool_routing),
                'timestamp': datetime.now().isoformat()
            }
            
            await self.memory_storage.store_memory(
                content=f"MCP SSE Aggregator started on port {self.port}",
                category='infrastructure',
                metadata={
                    'event_type': 'aggregator_startup',
                    'startup_data': json.dumps(startup_data),
                    'aggregator_operation': True
                },
                scope='hive-shared'
            )
        except Exception as e:
            logger.warning(f"Failed to store startup memory: {e}")
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down MCP SSE Aggregator")
        
        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect from all servers
        for connection in self.registry.servers.values():
            await connection.disconnect()


async def main():
    """Main entry point"""
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    aggregator = MCPAggregatorService(config_path)
    
    try:
        await aggregator.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await aggregator.shutdown()


if __name__ == "__main__":
    asyncio.run(main())