# Remote Memory MCP Setup

The Memory MCP server is now running on `lance-dev` and accessible via Tailscale network.

## Status

✅ **Memory MCP Server**: Running and connected to ChromaDB + Redis  
✅ **Sync Service**: Running on `http://lance-dev:8899`  
✅ **Tailscale Access**: Available at `lance-dev:8899`  
✅ **API Endpoints**: `/api/status`, `/api/sync`, `/ws/{machine_id}`

## Quick Setup for Remote Machines

### Option 1: Use Claude Code CLI
```bash
# Add remote MCP server via Claude Code
claude mcp add --transport http remote-memory http://lance-dev:8899
```

### Option 2: Manual .mcp.json Configuration
Copy this to your project's `.mcp.json`:
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

### Option 3: Use Setup Script
```bash
# Run the automated setup script
curl -s http://lance-dev:8899/setup.sh | bash
# or
bash INSTALL/setup-remote.sh
```

## Available Tools

Once connected, these MCP tools will be available in Claude Code:

- `store_memory` - Store memories with categories and context
- `search_memories` - Semantic and full-text search  
- `retrieve_memory` - Get specific memory by ID
- `get_recent_memories` - Recent memories within time window
- `get_memory_stats` - Statistics about stored memories
- `import_conversation` - Import full conversations

## Prerequisites

- **Tailscale**: Must be connected to the same network
- **Node.js**: Required for HTTP MCP transport (`npm install -g @modelcontextprotocol/server-http`)
- **Network**: Ensure `lance-dev` hostname resolves

## Test Connection

```bash
# Test API access
curl http://lance-dev:8899/api/status

# Should return:
{
  "machine_id": "lance-dev",
  "known_machines": ["generic-C246-WU4", "localhost", "LJ's MacBook Pro"],
  "vector_clock": {"lance-dev": 0},
  "connected_websockets": 0
}
```

## Memory Categories

- `project` - Project-specific memories
- `conversation` - Conversation history  
- `agent` - Agent-specific knowledge
- `global` - Cross-project shared knowledge

The memory server automatically syncs across all connected machines via vector clocks and conflict resolution.