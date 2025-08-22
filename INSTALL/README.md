# Memory MCP Server - Installation Guide

Distributed memory storage and synchronization for Claude and AI agents across multiple machines.

## Quick Setup

### For Remote Machines (Mac, other servers)

**Option 1: Automated Setup**
```bash
# Copy and run the setup script
curl -O http://lance-dev:8899/static/setup-remote.sh
bash setup-remote.sh
```

**Option 2: Manual Setup**
1. Install the HTTP MCP server:
   ```bash
   npm install -g @modelcontextprotocol/server-http
   ```

2. Create `.mcp.json` in your project directory:
   ```json
   {
     "mcpServers": {
       "remote-memory": {
         "command": "npx",
         "args": [
           "@modelcontextprotocol/server-http",
           "http://lance-dev:8899"
         ],
         "env": {
           "HTTP_TIMEOUT": "30000"
         }
       }
     }
   }
   ```

3. Test connection:
   ```bash
   curl http://lance-dev:8899/api/status
   ```

### For Local Machine (lance-dev)

The local machine already has the MCP server configured. Services are running as systemd services:

```bash
# Check service status
sudo systemctl status memory-mcp memory-sync

# View logs
sudo journalctl -u memory-sync -f

# Restart services
sudo systemctl restart memory-mcp memory-sync
```

## Network Configuration

The setup script will automatically detect the best connection method:

1. **Tailscale (Recommended)**: `http://lance-dev:8899`
2. **External IP**: `http://34.72.136.20:8899` 
3. **Local Network**: `http://10.128.0.3:8899`

## Available Memory Tools

Once configured, Claude Code will have access to:

- **`store_memory`** - Store memories with categories (project, conversation, agent, global)
- **`search_memories`** - Semantic search across all memories using ChromaDB
- **`retrieve_memory`** - Get specific memory by ID
- **`get_recent_memories`** - Get recent memories within time window
- **`get_memory_stats`** - View memory collection statistics
- **`import_conversation`** - Import full conversations from clipboard/text and store as structured memories
- **`import_conversation_file`** - Import conversations from files (supports various export formats)

## Memory Categories

- **project**: Project-specific memories and context
- **conversation**: Conversation history and context  
- **agent**: Agent-specific knowledge and preferences
- **global**: Cross-project shared knowledge

## API Endpoints

- `GET /api/status` - Service status and machine information
- `POST /api/sync` - Manual sync between machines
- `POST /api/trigger-sync` - Trigger sync with all known machines
- `WebSocket /ws/{machine_id}` - Real-time sync notifications

## Troubleshooting

### Connection Issues
```bash
# Test direct connection
curl http://lance-dev:8899/api/status

# Check if port is open
telnet lance-dev 8899

# Verify Tailscale connectivity
tailscale status
ping lance-dev
```

### Service Issues (lance-dev only)
```bash
# Check service logs
sudo journalctl -u memory-sync -n 50

# Restart services
sudo systemctl restart memory-sync

# Check port usage
sudo lsof -i :8899
```

### MCP Integration Issues
```bash
# Verify .mcp.json syntax
cat .mcp.json | jq .

# Test HTTP MCP server
npx @modelcontextprotocol/server-http http://lance-dev:8899

# Check Claude Code settings
cat ~/.claude/settings.json
```

## Files in This Directory

- **`remote-mcp.json`** - Configuration template for remote machines
- **`local-mcp.json`** - Configuration template for local machine
- **`setup-remote.sh`** - Automated setup script for remote machines
- **`README.md`** - This installation guide

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Remote Machine  │    │   lance-dev     │    │ Remote Machine  │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Claude Code │ │    │ │ Claude Code │ │    │ │ Claude Code │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│        │        │    │        │        │    │        │        │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ HTTP Client │◄┼────┼►│ Memory MCP  │◄┼────┼►│ HTTP Client │ │
│ │    (npx)    │ │    │ │   Server    │ │    │ │    (npx)    │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │        │        │    │                 │
│                 │    │ ┌─────────────┐ │    │                 │
│                 │    │ │Sync Service │ │    │                 │
│                 │    │ │   :8899     │ │    │                 │
│                 │    │ └─────────────┘ │    │                 │
│                 │    │        │        │    │                 │
│                 │    │ ┌─────────────┐ │    │                 │
│                 │    │ │ChromaDB +   │ │    │                 │
│                 │    │ │Redis Cache  │ │    │                 │
│                 │    │ └─────────────┘ │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                        Tailscale Network
```

## Security

- Services run as user `lj` (not root)
- Redis password protection (configure in config.json)
- Tailscale VPN for secure machine communication
- Firewall rule allows port 8899 only

## Support

For issues or questions:
1. Check service logs: `sudo journalctl -u memory-sync -f`
2. Test API endpoints: `curl http://lance-dev:8899/api/status`
3. Verify network connectivity between machines
4. Ensure Tailscale is running on all machines

Memory synchronization happens automatically when tools are used across machines!