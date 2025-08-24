# hAIveMind MCP Server Hosting

## Overview

The hAIveMind MCP Server Hosting feature enables you to deploy, manage, and monitor custom MCP servers directly on the hAIveMind infrastructure. This advanced feature provides a complete hosting platform with process management, security controls, resource monitoring, and intelligent performance optimization.

## Features

### 🏭 **Server Hosting Platform**
- **Multi-language Support**: Python, Node.js, Bash, and more
- **Process Management**: Automatic lifecycle management with start/stop/restart
- **Resource Monitoring**: Real-time CPU, memory, and connection tracking
- **Auto-restart**: Intelligent failure detection and recovery
- **Log Collection**: Centralized logging with real-time access

### 🔒 **Security & Sandboxing**
- **Process Sandboxing**: Isolated execution environments
- **Resource Limits**: CPU, memory, and process constraints
- **Upload Scanning**: Automatic security scanning of uploaded servers
- **User Isolation**: Run servers as unprivileged users
- **Network Controls**: Configurable network access policies

### 📊 **Monitoring & Analytics**
- **Performance Tracking**: Resource usage analytics and trends
- **Health Checks**: HTTP endpoint monitoring and alerting
- **Optimization Insights**: AI-powered performance recommendations
- **hAIveMind Integration**: All operations stored as collective memories

### 🖥️ **Web Dashboard**
- **Visual Management**: Modern web interface for server management
- **Real-time Status**: Live server status and resource monitoring
- **Log Viewer**: Built-in log viewer with real-time updates
- **Upload Interface**: Drag-and-drop server deployment

## Quick Start

### 1. Enable MCP Hosting

Add to your `config/config.json`:

```json
{
  "mcp_hosting": {
    "enabled": true,
    "max_servers": 10,
    "dashboard": {
      "enabled": true,
      "port": 8910
    }
  }
}
```

### 2. Start the Hosting Service

```bash
# Start as standalone service
python src/mcp_hosting_server.py

# Or start with the main remote server (includes hosting)
python src/remote_mcp_server.py
```

### 3. Access the Dashboard

Open your browser to: `http://localhost:8910`

### 4. Deploy Your First Server

Use the web dashboard or MCP tools:

```python
# Via MCP tool
await upload_mcp_server(
    name="My Custom Server",
    archive_base64="<base64-encoded-zip>",
    command=["python", "server.py"],
    description="My custom MCP server"
)
```

## Server Development

### Creating a Server Package

1. **Create your MCP server** (Python example):

```python
#!/usr/bin/env python3
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My Custom Server")

@mcp.tool()
async def my_tool(input: str) -> str:
    """My custom tool"""
    return f"Processed: {input}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

2. **Create requirements.txt**:
```
mcp>=1.0.0
fastapi>=0.104.0
```

3. **Create server_config.json**:
```json
{
  "name": "My Custom Server",
  "command": ["python", "server.py"],
  "environment": {"DEBUG": "false"},
  "resource_limits": {
    "memory_mb": 256,
    "cpu_percent": 30
  }
}
```

4. **Package as ZIP** and upload via dashboard or API

### Example Server Creation

Use the provided script to create an example:

```bash
python scripts/create_example_server_package.py
```

This creates a ready-to-deploy example server package.

## MCP Tools Reference

### Server Management Tools

#### `upload_mcp_server`
Upload and deploy a new MCP server
- `name`: Server display name
- `archive_base64`: Base64-encoded ZIP archive
- `command`: Start command array (e.g., `["python", "server.py"]`)
- `description`: Optional description
- `environment`: Environment variables dict
- `resource_limits`: CPU/memory limits
- `health_check_url`: Optional health check endpoint

#### `start_mcp_server(server_id)`
Start a deployed server

#### `stop_mcp_server(server_id)`
Stop a running server

#### `restart_mcp_server(server_id)`
Restart a server

#### `delete_mcp_server(server_id, force=False)`
Delete a server (stops first if running)

#### `get_mcp_server_status(server_id)`
Get detailed server status and metrics

#### `list_mcp_servers()`
List all hosted servers with status

#### `get_mcp_server_logs(server_id, lines=50)`
Get recent server logs

#### `get_hosting_stats()`
Get overall hosting statistics

#### `optimize_server_resources()`
Get AI-powered optimization recommendations

## Configuration Reference

### Main Configuration (`config.json`)

```json
{
  "mcp_hosting": {
    "enabled": true,
    "servers_dir": "data/mcp_servers",
    "uploads_dir": "data/mcp_uploads",
    "logs_dir": "data/mcp_logs",
    "max_servers": 10,
    "health_check_interval": 30,
    "auto_cleanup": true,
    "cleanup_interval": 3600,
    "dashboard": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8910,
      "debug": false
    },
    "security": {
      "allowed_languages": ["python", "node", "bash"],
      "sandbox_by_default": true,
      "max_upload_size_mb": 100,
      "scan_uploads": true
    }
  }
}
```

### Server Configuration (`server_config.json`)

```json
{
  "name": "Server Name",
  "description": "Server description",
  "command": ["python", "server.py"],
  "environment": {
    "VAR1": "value1",
    "VAR2": "value2"
  },
  "auto_restart": true,
  "max_restarts": 5,
  "restart_delay": 5,
  "health_check_url": "http://localhost:8080/health",
  "health_check_interval": 30,
  "resource_limits": {
    "memory_mb": 512,
    "cpu_percent": 50,
    "max_processes": 10
  },
  "sandboxed": true,
  "allowed_network": true,
  "allowed_filesystem": ["read"],
  "user": "nobody"
}
```

## hAIveMind Integration

### Performance Learning
- All server operations are stored as memories
- Resource usage patterns are analyzed for optimization
- Performance insights are shared across the collective
- Automatic capacity planning based on usage analytics

### Collective Intelligence
- Server hosting insights shared with other agents
- Collaborative optimization recommendations
- Distributed performance monitoring
- Cross-deployment learning and adaptation

### Memory Categories
- `infrastructure`: Server deployment and configuration events
- `monitoring`: Performance data and health metrics
- `incidents`: Server failures and recovery actions
- `optimization`: Performance tuning recommendations

## Security Considerations

### Sandboxing
- Servers run in isolated processes
- Resource limits prevent resource exhaustion
- File system access is restricted
- Network access can be controlled

### Upload Security
- Automatic scanning for dangerous patterns
- File size limits prevent abuse
- Archive extraction with path validation
- User privilege dropping

### Monitoring
- All server activities are logged
- Resource usage is continuously monitored
- Health checks detect problems early
- Automatic cleanup of failed servers

## Troubleshooting

### Common Issues

**Server won't start:**
- Check command syntax in configuration
- Verify all required files are in the archive
- Check resource limits aren't too restrictive
- Review server logs for error messages

**High resource usage:**
- Use `optimize_server_resources()` for recommendations
- Adjust resource limits in configuration
- Monitor with `get_hosting_stats()`
- Check for memory leaks in server code

**Upload failures:**
- Verify archive is valid ZIP format
- Check file size limits
- Ensure all required files are included
- Review security scan results

### Log Analysis

Access logs via:
- Web dashboard log viewer
- `get_mcp_server_logs()` MCP tool
- Direct file access in `data/mcp_logs/`

### Performance Monitoring

Monitor performance with:
- `get_hosting_stats()` - Overall statistics
- `get_mcp_server_status()` - Individual server metrics
- `optimize_server_resources()` - Optimization insights
- Web dashboard real-time monitoring

## Advanced Usage

### Custom Health Checks
Implement health endpoints in your servers:

```python
@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "healthy"})
```

### Environment Variables
Use environment variables for configuration:

```json
{
  "environment": {
    "DEBUG": "true",
    "API_KEY": "${API_KEY}",
    "PORT": "8080"
  }
}
```

### Resource Optimization
Monitor and optimize resource usage:

```python
# Get optimization recommendations
recommendations = await optimize_server_resources()

# Adjust resource limits based on usage
config["resource_limits"]["memory_mb"] = 1024
```

## Integration with Other Features

### Story Dependencies
- **Requires**: Story 2a (Dashboard) - Web interface foundation
- **Requires**: Story 3a (Health Checking) - Health monitoring system
- **Parallel with**: Story 4a, 4b - Other advanced features
- **Enables**: Story 5 - Marketplace and production features

### Future Enhancements
- Container-based hosting (Docker/Podman)
- Kubernetes integration
- Load balancing and scaling
- Marketplace integration
- CI/CD pipeline integration

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review server logs and status
3. Use optimization tools for performance issues
4. Consult hAIveMind collective memories for similar issues