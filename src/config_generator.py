#!/usr/bin/env python3
"""
Client Configuration Generator for hAIveMind MCP Servers
Generates .mcp.json files and other configuration formats for client connections
"""

import json
import yaml
import secrets
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ConfigFormat(Enum):
    """Supported configuration formats"""
    CLAUDE_DESKTOP = "claude_desktop"
    CLAUDE_CODE = "claude_code"
    MCP_JSON = "mcp_json"
    CUSTOM_JSON = "custom_json"
    YAML = "yaml"
    SHELL_SCRIPT = "shell_script"
    DOCKER_COMPOSE = "docker_compose"


class ConnectionType(Enum):
    """Connection transport types"""
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"
    WEBSOCKET = "websocket"


class AuthType(Enum):
    """Authentication types"""
    NONE = "none"
    API_KEY = "api_key"
    JWT = "jwt"
    BASIC = "basic"
    BEARER = "bearer"


@dataclass
class ServerEndpoint:
    """MCP Server endpoint configuration"""
    id: str
    name: str
    host: str
    port: int
    transport: ConnectionType
    path: str = ""
    ssl: bool = False
    priority: int = 100
    health_check: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    @property
    def base_url(self) -> str:
        """Get base URL for this endpoint"""
        protocol = "https" if self.ssl else "http"
        return f"{protocol}://{self.host}:{self.port}"
    
    @property
    def full_url(self) -> str:
        """Get full URL including path"""
        base = self.base_url
        if self.path:
            return f"{base}/{self.path.lstrip('/')}"
        return base


@dataclass
class AuthConfig:
    """Authentication configuration"""
    type: AuthType
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    header_name: str = "Authorization"
    token_prefix: str = "Bearer"
    scopes: List[str] = None
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.scopes is None:
            self.scopes = []
    
    @property
    def is_expired(self) -> bool:
        """Check if auth token is expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def get_header_value(self) -> Optional[str]:
        """Get the complete header value for authentication"""
        if self.type == AuthType.NONE:
            return None
        elif self.type in (AuthType.API_KEY, AuthType.BEARER):
            return f"{self.token_prefix} {self.token}" if self.token else None
        elif self.type == AuthType.JWT:
            return f"Bearer {self.token}" if self.token else None
        elif self.type == AuthType.BASIC:
            if self.username and self.password:
                import base64
                creds = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
                return f"Basic {creds}"
        return None


@dataclass
class ClientConfig:
    """Complete client configuration"""
    client_id: str
    user_id: str
    device_id: str
    format: ConfigFormat
    servers: List[ServerEndpoint]
    auth: Optional[AuthConfig] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    @property
    def is_expired(self) -> bool:
        """Check if configuration is expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class ConfigTemplate:
    """Configuration template system"""
    
    def __init__(self):
        self.templates = {
            ConfigFormat.CLAUDE_DESKTOP: self._claude_desktop_template,
            ConfigFormat.CLAUDE_CODE: self._claude_code_template,
            ConfigFormat.MCP_JSON: self._mcp_json_template,
            ConfigFormat.CUSTOM_JSON: self._custom_json_template,
            ConfigFormat.YAML: self._yaml_template,
            ConfigFormat.SHELL_SCRIPT: self._shell_script_template,
            ConfigFormat.DOCKER_COMPOSE: self._docker_compose_template,
        }
    
    def generate(self, config: ClientConfig) -> str:
        """Generate configuration string for the given format"""
        template_func = self.templates.get(config.format)
        if not template_func:
            raise ValueError(f"Unsupported format: {config.format}")
        
        return template_func(config)
    
    def _claude_desktop_template(self, config: ClientConfig) -> str:
        """Generate Claude Desktop configuration"""
        mcp_servers = {}
        
        for server in config.servers:
            server_config = {
                "command": "npx",
                "args": [
                    "@modelcontextprotocol/server-http",
                    f"{server.full_url}/sse"
                ],
                "env": {
                    "HTTP_TIMEOUT": "30000"
                }
            }
            
            # Add authentication if configured
            if config.auth and config.auth.type != AuthType.NONE:
                auth_header = config.auth.get_header_value()
                if auth_header:
                    server_config["env"]["AUTHORIZATION"] = auth_header
            
            mcp_servers[server.id] = server_config
        
        result = {
            "mcpServers": mcp_servers
        }
        
        return json.dumps(result, indent=2)
    
    def _claude_code_template(self, config: ClientConfig) -> str:
        """Generate Claude Code CLI configuration"""
        servers = {}
        
        for server in config.servers:
            server_config = {
                "transport": server.transport.value,
                "url": f"{server.full_url}/sse",
                "timeout": 30
            }
            
            # Add authentication headers
            if config.auth and config.auth.type != AuthType.NONE:
                auth_header = config.auth.get_header_value()
                if auth_header:
                    server_config["headers"] = {
                        config.auth.header_name: auth_header
                    }
            
            servers[server.id] = server_config
        
        result = {
            "mcp_servers": servers
        }
        
        return json.dumps(result, indent=2)
    
    def _mcp_json_template(self, config: ClientConfig) -> str:
        """Generate standard .mcp.json configuration"""
        mcp_servers = {}
        
        for server in config.servers:
            if server.transport == ConnectionType.STDIO:
                # Local stdio connection
                server_config = {
                    "command": "python3",
                    "args": ["/path/to/memory_server.py"],
                    "env": {
                        "PYTHONPATH": "/path/to/src"
                    }
                }
            else:
                # Remote connection
                server_config = {
                    "command": "npx",
                    "args": [
                        "@modelcontextprotocol/server-http",
                        f"{server.full_url}/sse"
                    ],
                    "env": {
                        "HTTP_TIMEOUT": "30000"
                    }
                }
                
                # Add authentication
                if config.auth and config.auth.type != AuthType.NONE:
                    auth_header = config.auth.get_header_value()
                    if auth_header:
                        server_config["env"]["AUTHORIZATION"] = auth_header
            
            mcp_servers[server.id] = server_config
        
        result = {
            "mcpServers": mcp_servers
        }
        
        return json.dumps(result, indent=2)
    
    def _custom_json_template(self, config: ClientConfig) -> str:
        """Generate custom JSON configuration with full metadata"""
        servers_data = []
        
        for server in config.servers:
            server_data = {
                "id": server.id,
                "name": server.name,
                "endpoints": {
                    "base": server.base_url,
                    "sse": f"{server.full_url}/sse",
                    "http": f"{server.full_url}/mcp",
                    "health": server.health_check or f"{server.full_url}/health"
                },
                "transport": server.transport.value,
                "priority": server.priority,
                "ssl": server.ssl,
                "tags": server.tags,
                "description": server.description
            }
            servers_data.append(server_data)
        
        result = {
            "client": {
                "id": config.client_id,
                "user_id": config.user_id,
                "device_id": config.device_id,
                "format": config.format.value,
                "created_at": config.created_at.isoformat(),
                "expires_at": config.expires_at.isoformat() if config.expires_at else None
            },
            "servers": servers_data,
            "auth": {
                "type": config.auth.type.value if config.auth else "none",
                "header_name": config.auth.header_name if config.auth else "Authorization",
                "token_prefix": config.auth.token_prefix if config.auth else "Bearer",
                "scopes": config.auth.scopes if config.auth else [],
                "expires_at": config.auth.expires_at.isoformat() if config.auth and config.auth.expires_at else None
            },
            "metadata": config.metadata,
            "features": {
                "memory_storage": True,
                "agent_coordination": True,
                "knowledge_sync": True,
                "broadcast_system": True,
                "aggregated_tools": True
            }
        }
        
        return json.dumps(result, indent=2)
    
    def _yaml_template(self, config: ClientConfig) -> str:
        """Generate YAML configuration"""
        # Convert custom JSON to YAML
        json_config = json.loads(self._custom_json_template(config))
        return yaml.dump(json_config, default_flow_style=False, indent=2)
    
    def _shell_script_template(self, config: ClientConfig) -> str:
        """Generate shell script for setup"""
        lines = [
            "#!/bin/bash",
            "# hAIveMind MCP Client Setup Script",
            f"# Generated for client: {config.client_id}",
            f"# Created: {config.created_at.isoformat()}",
            "",
            "set -e",
            "",
            "echo '🧠 Setting up hAIveMind MCP Client...'",
            "",
            "# Install dependencies",
            "if ! command -v npx &> /dev/null; then",
            "    echo 'Installing Node.js and npm...'",
            "    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -",
            "    sudo apt-get install -y nodejs",
            "fi",
            "",
            "# Install MCP HTTP proxy",
            "echo 'Installing MCP HTTP proxy...'",
            "npm install -g @modelcontextprotocol/server-http",
            "",
            "# Create configuration directory",
            "mkdir -p ~/.config/claude",
            "",
            "# Generate .mcp.json configuration",
            "cat > .mcp.json << 'EOF'",
            self._mcp_json_template(config),
            "EOF",
            "",
            "echo '✅ hAIveMind MCP Client setup complete!'",
            "echo '📋 Configuration saved to .mcp.json'",
            "",
            "# Test connections",
            "echo '🔍 Testing server connections...'",
        ]
        
        for server in config.servers:
            if server.health_check:
                lines.extend([
                    f"echo 'Testing {server.name}...'",
                    f"curl -s -f {server.health_check} > /dev/null && echo '✅ {server.name} is healthy' || echo '❌ {server.name} is unreachable'",
                ])
        
        lines.extend([
            "",
            "echo '🚀 Setup complete! You can now use hAIveMind MCP tools.'"
        ])
        
        return "\n".join(lines)
    
    def _docker_compose_template(self, config: ClientConfig) -> str:
        """Generate Docker Compose configuration"""
        services = {}
        
        for server in config.servers:
            service_name = f"haivemind-{server.id}"
            services[service_name] = {
                "image": "node:18-alpine",
                "command": [
                    "npx", "@modelcontextprotocol/server-http",
                    f"{server.full_url}/sse"
                ],
                "environment": {
                    "HTTP_TIMEOUT": "30000"
                },
                "networks": ["haivemind"],
                "restart": "unless-stopped",
                "healthcheck": {
                    "test": [
                        "CMD", "curl", "-f",
                        server.health_check or f"{server.full_url}/health"
                    ],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3
                }
            }
            
            # Add authentication environment variables
            if config.auth and config.auth.type != AuthType.NONE:
                auth_header = config.auth.get_header_value()
                if auth_header:
                    services[service_name]["environment"]["AUTHORIZATION"] = auth_header
        
        compose_config = {
            "version": "3.8",
            "services": services,
            "networks": {
                "haivemind": {
                    "driver": "bridge"
                }
            }
        }
        
        return yaml.dump(compose_config, default_flow_style=False, indent=2)


class ConfigGenerator:
    """Main configuration generator class"""
    
    def __init__(self, config: Dict[str, Any], memory_storage=None):
        self.config = config
        self.memory_storage = memory_storage
        self.template_engine = ConfigTemplate()
        
        # Get aggregator configuration
        self.aggregator_config = config.get('aggregator', {})
        self.default_host = self.aggregator_config.get('host', 'localhost')
        self.default_port = self.aggregator_config.get('port', 8950)
        
        # Server discovery
        self.discovered_servers = {}
        self._load_static_servers()
    
    def _load_static_servers(self):
        """Load static server configurations"""
        static_servers = self.aggregator_config.get('static_servers', [])
        
        for server_config in static_servers:
            endpoint = self._parse_endpoint(server_config)
            if endpoint:
                self.discovered_servers[endpoint.id] = endpoint
    
    def _parse_endpoint(self, server_config: Dict[str, Any]) -> Optional[ServerEndpoint]:
        """Parse server configuration into ServerEndpoint"""
        try:
            endpoint_url = server_config.get('endpoint', '')
            if not endpoint_url:
                return None
            
            # Parse URL
            import urllib.parse
            parsed = urllib.parse.urlparse(endpoint_url)
            
            return ServerEndpoint(
                id=server_config.get('id', ''),
                name=server_config.get('name', ''),
                host=parsed.hostname or 'localhost',
                port=parsed.port or (443 if parsed.scheme == 'https' else 8900),
                transport=ConnectionType.SSE,  # Default to SSE
                path=parsed.path.rstrip('/sse'),  # Remove /sse suffix
                ssl=parsed.scheme == 'https',
                priority=server_config.get('priority', 100),
                health_check=server_config.get('health_check'),
                description=server_config.get('description'),
                tags=server_config.get('tags', [])
            )
        except Exception as e:
            logger.warning(f"Failed to parse server config: {e}")
            return None
    
    def discover_servers(self) -> List[ServerEndpoint]:
        """Discover available MCP servers"""
        servers = list(self.discovered_servers.values())
        
        # Add aggregator endpoint itself
        aggregator_endpoint = ServerEndpoint(
            id="aggregator",
            name="MCP Aggregator",
            host=self.default_host,
            port=self.default_port,
            transport=ConnectionType.SSE,
            path="",
            priority=1,  # Highest priority
            health_check=f"http://{self.default_host}:{self.default_port}/health",
            description="Unified MCP tool aggregator",
            tags=["aggregator", "primary"]
        )
        servers.insert(0, aggregator_endpoint)
        
        return servers
    
    def generate_auth_config(self, user_id: str, device_id: str, scopes: List[str] = None, 
                           expires_hours: Optional[int] = None) -> AuthConfig:
        """Generate authentication configuration"""
        if scopes is None:
            scopes = ["mcp:read", "mcp:write"]
        
        # Generate API token
        token = secrets.token_urlsafe(32)
        
        # Set expiration
        expires_at = None
        if expires_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        return AuthConfig(
            type=AuthType.BEARER,
            token=token,
            scopes=scopes,
            expires_at=expires_at
        )
    
    def generate_client_config(self, user_id: str, device_id: str, format: ConfigFormat,
                             include_auth: bool = True, auth_expires_hours: Optional[int] = None,
                             server_filter: Optional[List[str]] = None) -> ClientConfig:
        """Generate complete client configuration"""
        
        # Generate unique client ID
        client_id = hashlib.sha256(f"{user_id}:{device_id}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]
        
        # Discover servers
        all_servers = self.discover_servers()
        
        # Filter servers if requested
        if server_filter:
            servers = [s for s in all_servers if s.id in server_filter]
        else:
            servers = all_servers
        
        # Generate authentication if requested
        auth = None
        if include_auth:
            auth = self.generate_auth_config(user_id, device_id, expires_hours=auth_expires_hours)
        
        # Create client configuration
        config = ClientConfig(
            client_id=client_id,
            user_id=user_id,
            device_id=device_id,
            format=format,
            servers=servers,
            auth=auth,
            metadata={
                "generator_version": "1.0.0",
                "generated_by": "haivemind-config-generator",
                "user_agent": f"haivemind-client/{client_id}"
            }
        )
        
        return config
    
    def generate_config_string(self, user_id: str, device_id: str, format: ConfigFormat,
                             include_auth: bool = True, auth_expires_hours: Optional[int] = None,
                             server_filter: Optional[List[str]] = None) -> str:
        """Generate configuration string in specified format"""
        
        client_config = self.generate_client_config(
            user_id=user_id,
            device_id=device_id,
            format=format,
            include_auth=include_auth,
            auth_expires_hours=auth_expires_hours,
            server_filter=server_filter
        )
        
        return self.template_engine.generate(client_config)
    
    def generate_multiple_formats(self, user_id: str, device_id: str, 
                                formats: List[ConfigFormat],
                                include_auth: bool = True,
                                auth_expires_hours: Optional[int] = None) -> Dict[str, str]:
        """Generate configurations in multiple formats"""
        
        results = {}
        
        for format_type in formats:
            try:
                config_string = self.generate_config_string(
                    user_id=user_id,
                    device_id=device_id,
                    format=format_type,
                    include_auth=include_auth,
                    auth_expires_hours=auth_expires_hours
                )
                results[format_type.value] = config_string
            except Exception as e:
                logger.error(f"Failed to generate {format_type.value} config: {e}")
                results[format_type.value] = f"Error: {str(e)}"
        
        return results
    
    async def store_config_memory(self, client_config: ClientConfig, action: str = "generated"):
        """Store configuration generation event in hAIveMind memory"""
        if not self.memory_storage:
            return
        
        try:
            memory_data = {
                'client_id': client_config.client_id,
                'user_id': client_config.user_id,
                'device_id': client_config.device_id,
                'format': client_config.format.value,
                'action': action,
                'server_count': len(client_config.servers),
                'servers': [s.id for s in client_config.servers],
                'auth_enabled': client_config.auth is not None,
                'auth_type': client_config.auth.type.value if client_config.auth else None,
                'expires_at': client_config.expires_at.isoformat() if client_config.expires_at else None,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            await self.memory_storage.store_memory(
                content=f"Client configuration {action} for {client_config.device_id}",
                category='infrastructure',
                metadata={
                    'event_type': 'client_config_generation',
                    'config_data': json.dumps(memory_data),
                    'aggregator_operation': True
                },
                tags=['config', 'client', action, client_config.format.value],
                scope='hive-shared'
            )
            
            # Broadcast configuration event
            await self.memory_storage.broadcast_discovery(
                message=f"New client configuration generated for {client_config.device_id}",
                category="client_config",
                severity="info"
            )
            
        except Exception as e:
            logger.warning(f"Failed to store config memory: {e}")
    
    async def analyze_client_usage_patterns(self) -> Dict[str, Any]:
        """Analyze client configuration usage patterns from hAIveMind memory"""
        if not self.memory_storage:
            return {}
        
        try:
            # Search for client configuration memories
            memories = await self.memory_storage.search_memories(
                query="client configuration",
                category="infrastructure",
                limit=100
            )
            
            # Analyze patterns
            format_usage = {}
            device_usage = {}
            auth_usage = {"enabled": 0, "disabled": 0}
            server_popularity = {}
            
            for memory in memories:
                metadata = memory.get('metadata', {})
                if metadata.get('event_type') == 'client_config_generation':
                    config_data = json.loads(metadata.get('config_data', '{}'))
                    
                    # Track format usage
                    format_type = config_data.get('format', 'unknown')
                    format_usage[format_type] = format_usage.get(format_type, 0) + 1
                    
                    # Track device usage
                    device_id = config_data.get('device_id', 'unknown')
                    device_usage[device_id] = device_usage.get(device_id, 0) + 1
                    
                    # Track auth usage
                    if config_data.get('auth_enabled'):
                        auth_usage["enabled"] += 1
                    else:
                        auth_usage["disabled"] += 1
                    
                    # Track server popularity
                    for server_id in config_data.get('servers', []):
                        server_popularity[server_id] = server_popularity.get(server_id, 0) + 1
            
            return {
                'total_configurations': len(memories),
                'format_usage': format_usage,
                'device_usage': device_usage,
                'auth_usage': auth_usage,
                'server_popularity': server_popularity,
                'most_popular_format': max(format_usage.items(), key=lambda x: x[1])[0] if format_usage else None,
                'most_used_server': max(server_popularity.items(), key=lambda x: x[1])[0] if server_popularity else None
            }
            
        except Exception as e:
            logger.warning(f"Failed to analyze usage patterns: {e}")
            return {}
    
    async def suggest_configuration_improvements(self, client_config: ClientConfig) -> List[Dict[str, str]]:
        """Suggest configuration improvements based on hAIveMind analysis"""
        if not self.memory_storage:
            return []
        
        suggestions = []
        
        try:
            # Analyze usage patterns
            patterns = await self.analyze_client_usage_patterns()
            
            # Suggest popular format if using less common one
            most_popular_format = patterns.get('most_popular_format')
            if most_popular_format and client_config.format.value != most_popular_format:
                suggestions.append({
                    'type': 'format',
                    'title': 'Consider Popular Format',
                    'description': f'Most users prefer {most_popular_format} format. Consider switching for better compatibility.',
                    'priority': 'low'
                })
            
            # Suggest authentication if disabled
            if not client_config.auth or client_config.auth.type == AuthType.NONE:
                auth_stats = patterns.get('auth_usage', {})
                if auth_stats.get('enabled', 0) > auth_stats.get('disabled', 0):
                    suggestions.append({
                        'type': 'security',
                        'title': 'Enable Authentication',
                        'description': 'Most configurations use authentication for better security.',
                        'priority': 'high'
                    })
            
            # Suggest popular servers
            server_popularity = patterns.get('server_popularity', {})
            current_servers = set(s.id for s in client_config.servers)
            popular_servers = set(sorted(server_popularity.keys(), key=lambda x: server_popularity[x], reverse=True)[:3])
            
            missing_popular = popular_servers - current_servers
            if missing_popular:
                suggestions.append({
                    'type': 'servers',
                    'title': 'Consider Popular Servers',
                    'description': f'Consider adding these popular servers: {", ".join(missing_popular)}',
                    'priority': 'medium'
                })
            
            # Check for expiring configurations
            if client_config.expires_at and client_config.expires_at < datetime.utcnow() + timedelta(days=7):
                suggestions.append({
                    'type': 'maintenance',
                    'title': 'Configuration Expiring Soon',
                    'description': 'Your configuration expires within 7 days. Consider generating a new one.',
                    'priority': 'high'
                })
            
        except Exception as e:
            logger.warning(f"Failed to generate suggestions: {e}")
        
        return suggestions
    
    async def learn_from_client_performance(self, client_id: str, performance_data: Dict[str, Any]):
        """Learn from client performance data to improve future configurations"""
        if not self.memory_storage:
            return
        
        try:
            await self.memory_storage.store_memory(
                content=f"Client performance data for {client_id}",
                category='infrastructure',
                metadata={
                    'event_type': 'client_performance',
                    'client_id': client_id,
                    'performance_data': json.dumps(performance_data),
                    'timestamp': datetime.utcnow().isoformat()
                },
                tags=['performance', 'client', 'analytics'],
                scope='hive-shared'
            )
            
            # Analyze performance and broadcast insights
            if performance_data.get('response_time', 0) > 5000:  # > 5 seconds
                await self.memory_storage.broadcast_discovery(
                    message=f"Client {client_id} experiencing slow response times",
                    category="performance_alert",
                    severity="warning"
                )
            
        except Exception as e:
            logger.warning(f"Failed to store performance data: {e}")
    
    def get_config_analytics(self) -> Dict[str, Any]:
        """Get configuration generation analytics"""
        # This would typically query stored memories for analytics
        # For now, return basic stats
        return {
            "total_servers": len(self.discovered_servers),
            "server_types": list(set(s.transport.value for s in self.discovered_servers.values())),
            "supported_formats": [f.value for f in ConfigFormat],
            "auth_types": [a.value for a in AuthType],
            "default_endpoint": f"http://{self.default_host}:{self.default_port}"
        }


def create_config_generator(config_path: str = None, memory_storage=None) -> ConfigGenerator:
    """Factory function to create ConfigGenerator instance"""
    if config_path is None:
        config_path = str(Path(__file__).parent.parent / "config" / "config.json")
    
    with open(config_path) as f:
        config = json.load(f)
    
    return ConfigGenerator(config, memory_storage)