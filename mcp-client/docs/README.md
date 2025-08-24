# hAIveMind MCP Client

A portable Model Context Protocol (MCP) client for accessing the hAIveMind distributed AI coordination system from any MCP-compatible application.

## Overview

The hAIveMind MCP Client provides seamless integration between MCP-compatible applications (Claude Desktop, cursor-agent, etc.) and the hAIveMind distributed memory and coordination system.

## Architecture

```
MCP Client (Claude Desktop/cursor-agent/etc.)
    ↓ stdio MCP protocol
hAIveMind MCP Standalone Client
    ↓ HTTP requests
hAIveMind Remote Server (port 8900)
    ↓
Distributed Memory System (ChromaDB + Redis)
```

## Features

### 🧠 Core Memory Operations
- **store_memory**: Store memories with comprehensive tracking and sharing control
- **search_memories**: Full-text and semantic search across distributed memory
- **retrieve_memory**: Get specific memories by ID
- **get_recent_memories**: Time-based memory retrieval
- **get_memory_stats**: Memory system statistics

### 🤖 hAIveMind Coordination
- **register_agent**: Register as a hAIveMind agent with specific capabilities
- **get_agent_roster**: View all active agents in the network
- **delegate_task**: Assign tasks to specialized agents
- **broadcast_discovery**: Share important findings across the network

### 🏗️ Infrastructure & DevOps
- **record_incident**: Log and correlate infrastructure incidents
- **generate_runbook**: Create reusable operational procedures
- **sync_ssh_config**: Synchronize SSH configurations across machines

## Installation

### Quick Install
```bash
cd mcp-client
./install.sh
```

### Manual Install
```bash
# Install dependencies
pip install -r mcp-client/requirements.txt

# Make scripts executable
chmod +x mcp-client/src/haivemind-mcp-standalone.py
```

## Configuration

### For cursor-agent
```bash
# Copy the configuration
cp mcp-client/config/cursor-agent.json .cursor/mcp.json

# Test the integration
cursor-agent mcp list-tools haivemind
```

### For Claude Desktop
1. Edit `mcp-client/config/claude-desktop.json` and update the path
2. Add the configuration to your Claude Desktop settings
3. Restart Claude Desktop

### For Remote Access
Use `mcp-client/config/remote-access.json` to connect to hAIveMind on remote machines via Tailscale.

## Usage Examples

### Store a Memory
```bash
cursor-agent mcp call-tool haivemind store_memory '{
  "content": "Elasticsearch cluster performance optimized by increasing heap size to 8GB",
  "category": "infrastructure",
  "tags": ["elasticsearch", "performance", "optimization"],
  "scope": "project-shared"
}'
```

### Search Memories
```bash
cursor-agent mcp call-tool haivemind search_memories '{
  "query": "elasticsearch performance",
  "category": "infrastructure",
  "limit": 5,
  "semantic": true
}'
```

### Register as hAIveMind Agent
```bash
cursor-agent mcp call-tool haivemind register_agent '{
  "role": "development_assistant",
  "description": "AI assistant for development tasks",
  "capabilities": ["code_review", "debugging", "documentation"]
}'
```

### Delegate a Task
```bash
cursor-agent mcp call-tool haivemind delegate_task '{
  "task_description": "Optimize Elasticsearch query performance on elastic1",
  "required_capabilities": ["elasticsearch_ops", "performance_tuning"],
  "priority": "high"
}'
```

### Record an Incident
```bash
cursor-agent mcp call-tool haivemind record_incident '{
  "title": "High CPU usage on elastic1",
  "description": "CPU usage spiked to 95% during peak hours",
  "severity": "high",
  "affected_systems": ["elastic1", "search-api"],
  "resolution": "Increased heap size and optimized queries"
}'
```

## Client Types

### 1. Standalone Client (`haivemind-mcp-standalone.py`)
- **Best for**: Claude Desktop, cursor-agent, and other MCP clients
- **Protocol**: stdio MCP
- **Features**: Full tool set, async operations, proper MCP compliance

### 2. Bridge Client (`haivemind-mcp-bridge.py`)
- **Best for**: Legacy systems or custom integrations
- **Protocol**: stdio to HTTP bridge
- **Features**: Simple request forwarding, synchronous operations

## Network Configuration

### Local Access
```json
{
  "env": {
    "HAIVEMIND_URL": "http://localhost:8900"
  }
}
```

### Remote Access via Tailscale
```json
{
  "env": {
    "HAIVEMIND_URL": "http://lance-dev:8900"
  }
}
```

### Custom Configuration
```json
{
  "env": {
    "HAIVEMIND_URL": "http://your-server:8900",
    "HAIVEMIND_TIMEOUT": "60",
    "HAIVEMIND_RETRIES": "3"
  }
}
```

## Troubleshooting

### Connection Issues
```bash
# Test hAIveMind server connectivity
curl http://localhost:8900/health

# Check if MCP client is working
cursor-agent mcp list-servers
```

### Tool Call Failures
```bash
# Test direct tool call
cursor-agent mcp call-tool haivemind get_memory_stats '{}'

# Check server logs
tail -f /path/to/haivemind/logs/remote_mcp_server.log
```

### Configuration Issues
```bash
# Validate JSON configuration
python3 -m json.tool .cursor/mcp.json

# Test Python dependencies
python3 -c "import mcp; print('MCP installed successfully')"
```

## Development

### Adding New Tools
1. Add tool definition to `_register_tools()` in `haivemind-mcp-standalone.py`
2. Update the `_forward_tool_call()` method if needed
3. Test with `cursor-agent mcp list-tools haivemind`

### Custom Configurations
Create new configuration files in `mcp-client/config/` for different use cases:
- Development environments
- Production deployments
- Specialized agent roles

## Security

- All communications use HTTPS when configured
- Credentials managed through hAIveMind's encrypted vault
- Network isolation via Tailscale VPN
- Tool access controlled by hAIveMind's permission system

## Integration Status

✅ **PRODUCTION READY**
- Tested with cursor-agent
- Compatible with Claude Desktop
- Full tool set implemented
- Comprehensive error handling
- Detailed documentation and examples