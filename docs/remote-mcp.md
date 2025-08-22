# Remote MCP Server Implementation Guide

## Overview

This document provides comprehensive guidance for implementing and using the Remote Memory MCP Server, which enables access to the distributed memory system from any machine on the Tailscale network via HTTP/SSE transport.

## Architecture

### Transport Options

The Remote MCP Server supports both current and future transport methods:

1. **SSE (Server-Sent Events)** - Current standard, being deprecated
   - Endpoint: `http://lance-dev:8900/sse`
   - Uses two endpoints: one for listening, one for sending
   - Supported by Claude Desktop and Claude Code

2. **Streamable HTTP** - Future standard, recommended for new implementations
   - Endpoint: `http://lance-dev:8900/mcp`
   - Single bidirectional endpoint
   - More efficient and simpler to implement

### Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     lance-dev Server                        │
├─────────────────────────────────────────────────────────────┤
│ Port 8899: Sync Service (Machine-to-Machine)               │
│ - REST API for memory synchronization                      │
│ - WebSocket support for real-time updates                  │
│ - Status and health endpoints                              │
├─────────────────────────────────────────────────────────────┤
│ Port 8900: Remote MCP Server (Client Access)               │
│ - FastMCP-based implementation                             │
│ - SSE transport: /sse                                      │
│ - Streamable HTTP: /mcp                                    │
│ - Full memory operations via MCP protocol                  │
├─────────────────────────────────────────────────────────────┤
│ Stdio: Local MCP Server (Local Claude Code)                │
│ - Direct stdio communication                               │
│ - Same tools as remote server                              │
│ - Project-local when needed                                │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Details

### FastMCP Integration

The Remote MCP Server uses the official MCP Python SDK with FastMCP for high-level implementation:

```python
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp_server = FastMCP("Memory MCP Server")

# Mount both transports
# SSE (backward compatibility)
sse_app = mcp_server.sse_app()  # Available at /sse

# Streamable HTTP (future-ready)  
http_app = mcp_server.app        # Available at /mcp
```

### Memory System Integration

The remote server integrates with the existing memory system by:

1. **Importing MemoryStorage**: Reuses the same storage class
2. **Wrapping Tools**: All memory operations exposed as FastMCP tools
3. **Context Preservation**: Maintains machine tracking and project context
4. **Sharing Rules**: Enforces the same sharing and security rules

### Tool Mapping

All tools from the stdio server are available remotely:

| Tool Name | Description | Remote Access |
|-----------|-------------|---------------|
| `store_memory` | Store memory with machine tracking | ✅ Full support |
| `search_memories` | Search with machine/project filtering | ✅ Full support |
| `retrieve_memory` | Get specific memory by ID | ✅ Full support |
| `get_recent_memories` | Recent memories within time window | ✅ Full support |
| `get_memory_stats` | Memory statistics and counts | ✅ Full support |
| `get_project_memories` | Current project memories only | ✅ Full support |
| `get_machine_context` | Comprehensive machine information | ✅ Full support |
| `list_memory_sources` | All machines with memory statistics | ✅ Full support |
| `import_conversation` | Import conversation as memories | ✅ Full support |

## Configuration

### Server Configuration

Add to `config/config.json`:

```json
{
  "remote_server": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8900,
    "cors_enabled": true,
    "allowed_origins": ["*"],
    "mount_paths": {
      "sse": "/sse",
      "streamable_http": "/mcp"
    }
  }
}
```

### Client Configuration

#### For Claude Desktop

Add to Claude Desktop config:

```json
{
  "mcpServers": {
    "remote-memory": {
      "command": "npx",
      "args": [
        "@modelcontextprotocol/server-http",
        "http://lance-dev:8900/sse"
      ],
      "env": {
        "HTTP_TIMEOUT": "30000"
      }
    }
  }
}
```

#### For Claude Code

Create `.mcp.json` in project root:

```json
{
  "mcpServers": {
    "remote-memory": {
      "command": "npx",
      "args": [
        "@modelcontextprotocol/server-http",
        "http://lance-dev:8900/sse"
      ],
      "env": {
        "HTTP_TIMEOUT": "30000"
      }
    }
  }
}
```

Or use CLI:
```bash
claude mcp add --transport sse remote-memory http://lance-dev:8900/sse
```

## Security & Authentication

### Current Implementation

- **Network Security**: Protected by Tailscale VPN
- **Machine Validation**: Enforces allowed machine lists
- **Sharing Rules**: Respects configured sharing scopes
- **Context Isolation**: Maintains machine and project context

### Future Enhancements

- **OAuth 2.1**: For external access beyond Tailscale
- **API Keys**: Machine-specific authentication
- **Rate Limiting**: Prevent abuse from remote clients
- **Audit Logging**: Track all remote access

## Deployment

### Systemd Service

The remote server runs as a systemd service:

```ini
[Unit]
Description=Memory MCP Remote Server
After=network.target redis.service
Wants=redis.service

[Service]
Type=simple
User=lj
WorkingDirectory=/home/lj/memory-mcp
ExecStart=/usr/bin/python3 /home/lj/memory-mcp/src/remote_mcp_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Service Management

```bash
# Start remote server
sudo systemctl start memory-remote-mcp

# Enable auto-start
sudo systemctl enable memory-remote-mcp

# Check status
sudo systemctl status memory-remote-mcp

# View logs
sudo journalctl -u memory-remote-mcp -f
```

## Testing & Validation

### Health Checks

```bash
# Check server health
curl http://lance-dev:8900/health

# Check SSE endpoint
curl http://lance-dev:8900/sse

# Check Streamable HTTP endpoint  
curl http://lance-dev:8900/mcp
```

### MCP Protocol Testing

```bash
# Install MCP Inspector (optional)
npm install -g @modelcontextprotocol/inspector

# Connect to remote server
mcp-inspector http://lance-dev:8900/sse
```

### Client Testing

1. **Claude Desktop**: Add server and verify tools appear
2. **Claude Code**: Test with `claude mcp list` and tool usage
3. **Direct API**: Use MCP client libraries for custom testing

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check Tailscale connectivity: `ping lance-dev`
   - Verify server is running: `curl http://lance-dev:8900/health`
   - Check firewall settings

2. **Tools Not Available**
   - Verify MCP client transport matches server endpoint
   - Check Claude configuration for typos
   - Restart Claude application after config changes

3. **Memory Access Issues**
   - Check machine sharing rules in config
   - Verify project context detection
   - Review memory scope settings

4. **Performance Issues**
   - Monitor Redis connection
   - Check ChromaDB performance
   - Review network latency to lance-dev

### Debugging

```bash
# Check server logs
sudo journalctl -u memory-remote-mcp -f

# Test memory operations
curl -X POST http://lance-dev:8900/test-memory-operation

# Verify machine context
curl http://lance-dev:8900/debug/machine-context
```

## Migration Path

### From SSE to Streamable HTTP

When Claude clients support Streamable HTTP:

1. Update client configuration to use `/mcp` endpoint
2. Verify compatibility with new transport
3. Remove SSE endpoints once all clients migrated
4. Monitor for deprecation notices from Anthropic

### Backward Compatibility

The server maintains support for:
- Existing SSE clients
- Legacy MCP protocol versions  
- Original stdio interface for local use

## Performance Considerations

### Scaling

- **Single Instance**: Suitable for personal/team use (5-50 users)
- **Load Balancing**: Multiple instances behind proxy for larger deployments
- **Database Scaling**: ChromaDB and Redis optimization for high loads

### Monitoring

Key metrics to monitor:
- Response time per tool call
- Memory usage trends
- Network bandwidth to ChromaDB
- Redis cache hit rates
- Concurrent client connections

## Future Roadmap

1. **Q1 2025**: Full Streamable HTTP support
2. **Q2 2025**: OAuth 2.1 authentication
3. **Q3 2025**: Multi-tenant support
4. **Q4 2025**: Advanced analytics and monitoring

This implementation provides a production-ready Remote MCP Server that maintains full compatibility with the local stdio server while enabling secure, efficient remote access to the distributed memory system.