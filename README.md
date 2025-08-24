```
    ╭─────────────────────────────────────────────────────────────────╮
    │                                                                 │
    │      ██╗  ██╗ █████╗ ██╗██╗   ██╗███████╗███╗   ███╗██╗███╗   ██╗██████╗   │
    │      ██║  ██║██╔══██╗██║██║   ██║██╔════╝████╗ ████║██║████╗  ██║██╔══██╗  │
    │      ███████║███████║██║██║   ██║█████╗  ██╔████╔██║██║██╔██╗ ██║██║  ██║  │
    │      ██╔══██║██╔══██║██║╚██╗ ██╔╝██╔══╝  ██║╚██╔╝██║██║██║╚██╗██║██║  ██║  │
    │      ██║  ██║██║  ██║██║ ╚████╔╝ ███████╗██║ ╚═╝ ██║██║██║ ╚████║██████╔╝  │
    │      ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝  ╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝   │
    │                                                                 │
    │    🧠🤖 Distributed AI Collective Memory for DevOps Automation 🤖🧠    │
    │                                                                 │
    │      ┌─[AGENT]─┐    ┌─[AGENT]─┐    ┌─[AGENT]─┐    ┌─[AGENT]─┐      │
    │      │ 🧠 ⚡ 🛠️ │◄──►│ 🧠 ⚡ 🛠️ │◄──►│ 🧠 ⚡ 🛠️ │◄──►│ 🧠 ⚡ 🛠️ │      │
    │      └─────────┘    └─────────┘    └─────────┘    └─────────┘      │
    │           ▲              ▲              ▲              ▲           │
    │           └──────────────┼──────────────┼──────────────┘           │
    │                     ┌────▼──────────────▼────┐                     │
    │                     │   🧠 COLLECTIVE 🧠    │                     │
    │                     │      MEMORY HUB       │                     │
    │                     └───────────────────────┘                     │
    │                                                                 │
    ╰─────────────────────────────────────────────────────────────────╯
```

# ClaudeOps hAIveMind - Distributed AI Memory & Coordination System

**A Model Context Protocol (MCP) server enabling distributed AI agent coordination with persistent collective memory across infrastructure networks.**

## Overview

**ClaudeOps hAIveMind** is a distributed memory and agent coordination system built on the Model Context Protocol (MCP). It enables multiple Claude agents to share knowledge, coordinate tasks, and maintain persistent memory across your entire infrastructure network.

### Key Features

🧠 **Collective Intelligence**: Agents share knowledge and coordinate responses across infrastructure  
🔄 **Real-Time Sync**: ChromaDB + Redis for distributed memory with conflict resolution  
🌐 **Network-Wide Access**: Secure communication via Tailscale VPN  
🛠️ **DevOps Integration**: Infrastructure tracking, incident management, runbook automation  
📊 **External Connectors**: Confluence, Jira, and custom API integrations  
🤖 **Agent Coordination**: Task delegation, knowledge queries, and broadcast messaging

## hAIveMind Architecture

```
        🧠 Distributed AI Collective Memory Network 🧠
                                                                                
   ┌─[node-alpha]─────────┐  ┌─[node-beta]─────────┐  ┌─[node-gamma]────────┐ 
   │  🤖 Claude Agent     │  │  🤖 Claude Agent    │  │  🤖 Claude Agent    │ 
   │  Role: Hive Mind     │  │  Role: Worker Drone │  │  Role: Worker Drone │ 
   │                      │  │                     │  │                     │ 
   │ ┌──🧠 Memory Hub──┐  │  │ ┌──🧠 Memory Hub──┐ │  │ ┌──🧠 Memory Hub──┐ │ 
   │ │  hAIveMind MCP  │  │  │ │  hAIveMind MCP  │ │  │ │  hAIveMind MCP  │ │ 
   │ │   Port: 8899    │◄─┼──┼►│   Port: 8899    │◄┼──┼►│   Port: 8899    │ │ 
   │ └─────────────────┘  │  │ └─────────────────┘ │  │ └─────────────────┘ │ 
   │          ║           │  │          ║          │  │          ║          │ 
   │ ┌──Vector Store───┐  │  │ ┌──Vector Store───┐ │  │ ┌──Vector Store───┐ │ 
   │ │ ChromaDB+Redis  │  │  │ │ ChromaDB+Redis  │ │  │ │ ChromaDB+Redis  │ │ 
   │ │ 🔍 Semantic     │  │  │ │ 🔍 Semantic     │ │  │ │ 🔍 Semantic     │ │ 
   │ │    Search       │  │  │ │    Search       │ │  │ │    Search       │ │ 
   │ └─────────────────┘  │  │ └─────────────────┘ │  │ └─────────────────┘ │ 
   └──────────────────────┘  └─────────────────────┘  └─────────────────────┘ 
              ║                          ║                          ║           
              ╚══════════════════════════╬══════════════════════════╝           
                                         ║                                      
                          🌐 Tailscale Encrypted VPN Network 🌐                
                                         ║                                      
              ┌──────────DevOps Infrastructure Fleet──────────┐                
              │                                               │                
    ┌─[db-cluster-01]─┐ ┌─[auth-gateway]─┐ ┌─[scraper-farm]─┐ ┌─[monitor-hub]─┐      
    │ 🔍 Data Hub     │ │ 🔐 Auth Hub    │ │ 🕷️ Scrapers    │ │ 📊 Insights   │      
    │ Capability:     │ │ Capability:    │ │ Capability:    │ │ Capability:   │      
    │ Data Storage    │ │ Security       │ │ Collection     │ │ Monitoring    │      
    └─────────────────┘ └────────────────┘ └────────────────┘ └───────────────┘      
                                         ║                                      
                          ⚡ Real-time Agent Collaboration ⚡                   
                                                                               
             🧠 Shared Knowledge • 🤝 Task Coordination • 📋 Runbooks          
```

## Installation

### Server Setup (Primary Node)

1. **Clone and setup hAIveMind**:
```bash
git clone https://github.com/lancejames221b/agent-hivemind.git
cd agent-hivemind
pip install -r requirements.txt
```

2. **Install Redis**:
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

3. **Configure the system**:
```bash
# Edit config/config.json for your setup
# Update machine IDs in discovery.machines to match your network
```

4. **Start hAIveMind server**:
```bash
# Start the memory server
python src/memory_server.py &

# Start the remote MCP server (for network access)
python src/remote_mcp_server.py --host 0.0.0.0 --port 8900 &
```

### Agent Setup (Claude Code Integration)

#### Option 1: Local Connection (Same Machine)
```bash
# Add to your project's .mcp.json
{
  "mcpServers": {
    "haivemind-local": {
      "command": "python",
      "args": ["/path/to/agent-hivemind/src/memory_server.py"],
      "env": {}
    }
  }
}
```

#### Option 2: Remote Connection (Network Access)
```bash
# Add hAIveMind to Claude Code
claude mcp add --transport sse haivemind http://node-alpha:8900/sse

# Or add to .mcp.json
{
  "mcpServers": {
    "haivemind-remote": {
      "command": "npx",
      "args": ["-y", "mcp-proxy", "--target", "http://node-alpha:8900/sse"],
      "env": {}
    }
  }
}
```

### First-Time Agent Sync

After connecting to hAIveMind, sync your agent:

```bash
# Option 1: Automatic installation (recommended)
# The system will auto-detect first connection and trigger sync

# Option 2: Manual installation
# Use the MCP tool to install commands and config
install_agent_commands target_location="auto" force=false

# Option 3: Install via command (after commands are synced)
/hv-install
```

**What gets installed:**
- All `hv-*` commands in your Claude commands directory
- Agent-specific CLAUDE.md configuration
- Automatic registration in the collective
- Sync preferences and machine identity

### Multi-Agent Network Setup

For distributed hAIveMind across multiple machines:

1. **Configure each node** in `config/config.json`:
```json
{
  "sync": {
    "discovery": {
      "machines": ["node-alpha", "node-beta", "node-gamma", "node-delta"]
    }
  }
}
```

2. **Start sync services** on each machine:
```bash
python src/sync_service.py --port 8899
```

3. **Connect agents** on each machine:
```bash
# Each agent connects to its local node
claude mcp add --transport sse haivemind http://localhost:8900/sse

# Then run first-time sync
install_agent_commands
```

## Configuration

Edit `config/config.json`:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8899
  },
  "sync": {
    "discovery": {
      "machines": ["node-alpha", "node-beta", "node-gamma", "node-delta"]
    }
  }
}
```

## Usage

### Start Memory MCP Server

```bash
# Start the MCP server (for Claude Code integration)
cd /path/to/agent-hivemind
python src/memory_server.py
```

### Start Sync Service

```bash
# Start the sync service (for remote machine communication)
cd /path/to/agent-hivemind
python src/sync_service.py
```

### hAIveMind Commands

Once your agent is synced, you'll have access to these commands:

#### Essential Commands
- `/hv-sync [force|status]` - Sync commands and configuration from collective
- `/hv-status` - Check collective status and network health  
- `/hv-install [personal|project|clean]` - Install/update hAIveMind system

#### Communication Commands
- `/hv-broadcast <message>` - Broadcast message to all collective agents
- `/hv-query <question>` - Query collective knowledge and expertise
- `/hv-delegate <task>` - Delegate task to most suitable agent

#### Usage Examples

**First-time setup:**
```bash
# After connecting to hAIveMind MCP server
/hv-install

# Check your agent status
/hv-status

# Sync latest commands  
/hv-sync
```

**Daily operations:**
```bash
# Share a discovery with the collective
/hv-broadcast "Found performance issue in database cluster - investigating"

# Query collective knowledge
/hv-query "How to optimize Elasticsearch memory usage?"

# Delegate a task to specialists
/hv-delegate "Investigate high CPU usage on web servers - requires monitoring expertise"

# Check collective status
/hv-status
```

### MCP Tools Integration  

The following MCP tools are available for programmatic access:

#### Core Memory Tools
- `store_memory`: Store new memories with categories and context
- `retrieve_memory`: Get specific memory by ID
- `search_memories`: Full-text and semantic search
- `get_recent_memories`: Get recent memories within time window

#### Agent Sync Tools
- `install_agent_commands`: Complete agent installation and setup
- `sync_agent_commands`: Sync commands to agent's Claude installation
- `sync_agent_config`: Sync agent-specific CLAUDE.md configuration
- `check_agent_sync_status`: Check current sync status
- `trigger_auto_sync`: Trigger automatic sync workflow

### Manual Sync

Trigger manual sync across machines:
```bash
curl -X POST http://localhost:8899/api/trigger-sync \
  -H "Authorization: Bearer your-api-token"
```

### WebSocket Monitoring

Connect to real-time updates:
```bash
# WebSocket endpoint: ws://localhost:8899/ws/{machine_id}
```

## Memory Categories

- **project**: Project-specific memories and context
- **conversation**: Conversation history and context
- **agent**: Agent-specific knowledge and preferences  
- **global**: Cross-project shared knowledge

## Security

- JWT authentication for API endpoints
- Encrypted credentials storage
- Tailscale VPN for secure machine communication
- Redis password protection (configure in config.json)

## Network Setup

Ensure machines can communicate via Tailscale:

```bash
# Check Tailscale status
tailscale status

# Test connectivity to other machines
ping node-beta
ping node-gamma
ping node-delta
```

## Monitoring

Check service status:
```bash
curl http://localhost:8899/api/status
```

View logs:
```bash
# MCP Server logs
python src/memory_server.py

# Sync Service logs  
python src/sync_service.py
```

## Troubleshooting

1. **MCP Server not connecting**:
   - Check Claude Code settings in `~/.claude/settings.json`
   - Verify `enableAllProjectMcpServers: true` is set
   - Check `.mcp.json` file exists in project root

2. **Redis connection failed**:
   - Install Redis: `sudo apt-get install redis-server`
   - Start Redis: `sudo systemctl start redis-server`
   - Check config.json Redis settings

3. **Machine discovery issues**:
   - Verify Tailscale is running: `tailscale status`
   - Check machine names in config.json match Tailscale hostnames
   - Test connectivity: `ping <machine-name>`

4. **Sync failures**:
   - Check API tokens are configured
   - Verify port 8899 is open on all machines
   - Check sync service logs for specific errors

## Development

Project structure:
```
agent-hivemind/
├── src/
│   ├── memory_server.py    # Main MCP server
│   └── sync_service.py     # Remote sync service
├── config/
│   └── config.json         # Configuration file
├── tests/                  # Test files
├── docs/                   # Documentation
├── requirements.txt        # Python dependencies
├── .mcp.json              # MCP server config
└── README.md              # This file
```

## API Reference

### MCP Tools

#### store_memory
```json
{
  "content": "string (required)",
  "category": "string (optional, default: general)", 
  "context": "string (optional)",
  "metadata": "object (optional)",
  "tags": "array of strings (optional)",
  "user_id": "string (optional, default: default)"
}
```

#### search_memories
```json
{
  "query": "string (required)",
  "category": "string (optional)",
  "user_id": "string (optional)", 
  "limit": "integer (optional, default: 10)",
  "semantic": "boolean (optional, default: true)"
}
```

### REST API

#### GET /api/status
Returns service status and machine information.

#### POST /api/sync
Handles sync requests from other machines.

#### POST /api/trigger-sync
Manually triggers sync with all known machines.

#### WebSocket /ws/{machine_id}
Real-time sync notifications and events.

## License

Created by Lance James, Unit 221B, Inc.