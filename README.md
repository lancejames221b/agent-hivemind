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
        
                  ┌─────────────── TAILSCALE VPN ───────────────┐
                  │          🔒 Encrypted Network Layer          │
                  │                                              │
                  │    ┌─[primary-node]───────┐                 │
                  │    │  🤖 Claude Agent     │  tag:primary    │
                  │    │  Role: Orchestrator  │                 │
                  │    │  IP: 100.x.x.x       │                 │
                  │    │ ┌──🧠 Memory Hub──┐  │                 │
                  │    │ │  hAIveMind MCP  │  │                 │
                  │    │ │   :8899 :8900   │◄─┼─────────────┐   │
                  │    │ └─────────────────┘  │             │   │
                  │    │ ┌──Vector Store───┐  │             │   │
                  │    │ │ ChromaDB+Redis  │  │             │   │
                  │    │ │ 🔍 Auth Required│  │             │   │
                  │    │ └─────────────────┘  │             │   │
                  │    └──────────────────────┘             │   │
                  │                                         │   │
        ┌─────────┼─────────────────────────────────────────┘   │
        │         │   ┌─[worker-node]────────┐                 │
        │         │   │  🤖 Claude Agent     │  tag:worker     │
        │         │   │  Role: ES Specialist │                 │
        │         │   │  IP: 100.x.x.x       │                 │
        │         │   │ ┌──🧠 Memory Hub──┐  │                 │
        │         │   │ │  hAIveMind MCP  │◄─┼─────────────────┘
        │         │   │ │   :8899 :8900   │  │
        │         │   │ └─────────────────┘  │
        │         │   │ ┌──Vector Store───┐  │
        │         │   │ │ ChromaDB+Redis  │  │
        │         │   │ │ 🔐 Whitelisted  │  │
        │         │   │ └─────────────────┘  │
        │         │   └──────────────────────┘
        │         │
        │         └─ ✅ ACL PROTECTED PORTS:
        │            • 8899: Sync Service
        │            • 8900: MCP Remote  
        │            • 6379: Redis Cache
        │
        │   🛡️ SECURITY LAYERS:
        │   ┌─────────────────────────────────────┐
        │   │ 1. Tailscale Network Encryption     │
        │   │ 2. Machine Tags & ACL Whitelisting  │
        │   │ 3. Firewall Port Restrictions       │
        │   │ 4. API Token Authentication         │
        │   │ 5. Redis Password Protection        │
        │   └─────────────────────────────────────┘
        │
        └─── COORDINATED INFRASTRUCTURE FLEET ───
                         │                        
        ┌─[elastic1-5]─┐ ┌─[proxy0-9]─┐ ┌─[auth-server]─┐ ┌─[monitoring]─┐
        │ 🔍 Search    │ │ 🕷️ Scrapers│ │ 🔐 Auth       │ │ 📊 Grafana   │
        │ Capability:  │ │ Capability: │ │ Capability:   │ │ Capability:  │
        │ elasticsearch│ │ data_collect│ │ security      │ │ monitoring   │
        └──────────────┘ └─────────────┘ └───────────────┘ └──────────────┘
                         
             ⚡ Secure Multi-Agent Coordination via Tailscale ⚡
                                                           
          🧠 Encrypted Knowledge • 🤝 Authenticated Tasks • 📋 Secure Runbooks
```

## Installation

### SECURITY-FIRST Installation

⚠️ **MANDATORY**: Complete Tailscale setup BEFORE installing hAIveMind services.

#### Prerequisites (All Machines)

1. **Install and configure Tailscale**:
```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Tag your machines for hAIveMind access
sudo tailscale set --advertise-tags=tag:haivemind-primary  # Primary node
sudo tailscale set --advertise-tags=tag:haivemind-node     # Worker nodes

# Verify connectivity
tailscale status
```

2. **Configure Tailscale ACLs** (see Security section for full ACL configuration)

3. **Setup firewall protection**:
```bash
# Restrict hAIveMind ports to Tailscale interface ONLY
sudo ufw allow in on tailscale0 to any port 8899 proto tcp
sudo ufw allow in on tailscale0 to any port 8900 proto tcp
sudo ufw allow in on tailscale0 to any port 6379 proto tcp

# Block public access
sudo ufw deny 8899
sudo ufw deny 8900  
sudo ufw deny 6379

sudo ufw enable
```

#### Server Setup (Primary Node)

1. **Clone and setup hAIveMind**:
```bash
git clone https://github.com/lancejames221b/agent-hivemind.git
cd agent-hivemind
pip install -r requirements.txt
```

2. **Install and secure Redis**:
```bash
sudo apt-get install redis-server

# Set Redis password
sudo redis-cli CONFIG SET requirepass "$(openssl rand -hex 32)"

# Configure Redis to bind localhost only
sudo sed -i 's/bind 127.0.0.1/bind 127.0.0.1/' /etc/redis/redis.conf

sudo systemctl restart redis-server
```

3. **Generate security credentials**:
```bash
# Generate API token
mkdir -p /etc/haivemind
openssl rand -hex 32 > /etc/haivemind/api-token
chmod 600 /etc/haivemind/api-token

# Optional: Generate TLS certificates
openssl req -x509 -newkey rsa:4096 -keyout haivemind.key -out haivemind.crt -days 365 -nodes
```

4. **Configure secure system settings**:
```bash
# Edit config/config.json with your Tailscale network info
# See Security section for complete configuration template
```

5. **Start hAIveMind server with security**:
```bash
# Start the memory server
python src/memory_server.py &

# Start the remote MCP server (bound to Tailscale interface)
python src/remote_mcp_server.py --host 100.x.x.x --port 8900 &

# Start sync service for machine coordination
python src/sync_service.py --host 100.x.x.x --port 8899 &
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
claude mcp add --transport sse haivemind http://primary-node:8900/sse

# Or add to .mcp.json
{
  "mcpServers": {
    "haivemind-remote": {
      "command": "npx",
      "args": ["-y", "mcp-proxy", "--target", "http://primary-node:8900/sse"],
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
      "machines": ["primary-node", "worker-node-1", "worker-node-2", "worker-node-3"]
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
      "machines": ["primary-node", "worker-node-1", "worker-node-2", "worker-node-3"]
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

## Security & Tailscale Configuration

### ⚠️ CRITICAL SECURITY REQUIREMENTS

**hAIveMind operates as a distributed system across your infrastructure network. Proper security configuration is MANDATORY for safe operation.**

### Tailscale VPN Setup (Required)

Tailscale provides the secure networking foundation for hAIveMind. All inter-machine communication MUST go through Tailscale.

#### 1. Install Tailscale on All Machines

**Ubuntu/Debian:**
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

**macOS:**
```bash
brew install tailscale
sudo tailscale up
```

**After installation, authenticate with your Tailscale account and note the assigned IP addresses.**

#### 2. Configure Tailscale Access Controls (ACLs)

**CRITICAL**: Configure Tailscale ACLs to whitelist only authorized hAIveMind communication.

In your Tailscale admin console, add this ACL configuration:

```json
{
  "tagOwners": {
    "tag:haivemind-node": ["your-email@domain.com"],
    "tag:haivemind-primary": ["your-email@domain.com"]
  },
  "acls": [
    {
      "action": "accept",
      "src": ["tag:haivemind-node", "tag:haivemind-primary"],
      "dst": ["tag:haivemind-node:8899", "tag:haivemind-primary:8899"],
      "proto": "tcp"
    },
    {
      "action": "accept", 
      "src": ["tag:haivemind-node", "tag:haivemind-primary"],
      "dst": ["tag:haivemind-node:8900", "tag:haivemind-primary:8900"],
      "proto": "tcp"
    },
    {
      "action": "accept",
      "src": ["tag:haivemind-node", "tag:haivemind-primary"], 
      "dst": ["tag:haivemind-node:6379", "tag:haivemind-primary:6379"],
      "proto": "tcp"
    }
  ]
}
```

#### 3. Tag Your hAIveMind Machines

```bash
# Primary hAIveMind node (coordinator)
sudo tailscale set --advertise-tags=tag:haivemind-primary

# Worker nodes  
sudo tailscale set --advertise-tags=tag:haivemind-node
```

#### 4. Verify Secure Connectivity

```bash
# Check Tailscale status and IPs
tailscale status

# Test connectivity to other hAIveMind machines (use Tailscale IPs)
ping 100.x.x.x  # Example Tailscale IP
ping worker-node.your-tailnet.ts.net

# Verify port access
nc -zv worker-node.your-tailnet.ts.net 8899
nc -zv worker-node.your-tailnet.ts.net 8900
```

### Network Security Requirements

#### Firewall Configuration
```bash
# Only allow hAIveMind ports from Tailscale interface
sudo ufw allow in on tailscale0 to any port 8899 proto tcp
sudo ufw allow in on tailscale0 to any port 8900 proto tcp  
sudo ufw allow in on tailscale0 to any port 6379 proto tcp

# Deny these ports from all other interfaces
sudo ufw deny 8899
sudo ufw deny 8900
sudo ufw deny 6379
```

#### Required Ports
- **8899**: hAIveMind sync service (machine-to-machine coordination)
- **8900**: Remote MCP server (Claude agent connections)
- **6379**: Redis (memory storage and caching)

### Authentication & Authorization

#### API Token Configuration
```bash
# Generate secure API tokens for each machine
openssl rand -hex 32 > /etc/haivemind/api-token

# Configure in config.json
{
  "security": {
    "api_token": "your-generated-token-here",
    "require_auth": true,
    "allowed_origins": ["tailscale"]
  }
}
```

#### Machine Whitelisting
```json
{
  "sync": {
    "discovery": {
      "machines": {
        "primary-node": {
          "tailscale_ip": "100.x.x.x",
          "roles": ["primary", "orchestrator"],
          "capabilities": ["coordination", "deployment"]
        },
        "worker-node": {
          "tailscale_ip": "100.y.y.y", 
          "roles": ["worker"],
          "capabilities": ["elasticsearch_ops", "search_tuning"]
        }
      }
    },
    "security": {
      "whitelist_only": true,
      "verify_certificates": true,
      "max_sync_attempts": 3
    }
  }
}
```

### Additional Security Measures

#### 1. Redis Security
```bash
# Set Redis password
redis-cli CONFIG SET requirepass "your-secure-redis-password"

# Configure in config.json
{
  "storage": {
    "redis": {
      "password": "your-secure-redis-password",
      "bind": "127.0.0.1"  // Only localhost access
    }
  }
}
```

#### 2. Certificate Verification
```bash
# Generate TLS certificates for hAIveMind services
openssl req -x509 -newkey rsa:4096 -keyout haivemind.key -out haivemind.crt -days 365 -nodes
```

#### 3. Logging & Monitoring
```json
{
  "logging": {
    "audit_enabled": true,
    "log_auth_failures": true,
    "log_sync_events": true,
    "max_log_size": "100MB"
  }
}
```

### Deployment Security Checklist

- [ ] Tailscale installed and configured on all machines
- [ ] Tailscale ACLs configured with machine tags
- [ ] Firewall rules restrict hAIveMind ports to Tailscale interface only
- [ ] API tokens generated and configured
- [ ] Machine whitelist configured in config.json
- [ ] Redis password protection enabled
- [ ] TLS certificates generated (optional but recommended)
- [ ] Audit logging enabled
- [ ] All machines can ping each other via Tailscale IPs
- [ ] Port connectivity verified (8899, 8900, 6379)

### Security Best Practices

1. **Never expose hAIveMind ports to the public internet**
2. **Always use Tailscale hostnames/IPs for machine discovery**
3. **Regularly rotate API tokens and Redis passwords**
4. **Monitor authentication failures and unusual sync activity**
5. **Keep Tailscale client updated on all machines**
6. **Use machine tags for granular access control**
7. **Implement network segmentation for production environments**

### Network Verification Commands

```bash
# Verify Tailscale connectivity
tailscale status | grep -E "(primary-node|worker-node-1|worker-node-2)"

# Test hAIveMind service connectivity  
curl -s http://worker-node.tailnet.ts.net:8899/api/status

# Verify secure Redis connection
redis-cli -h worker-node.tailnet.ts.net -a your-password ping

# Check firewall rules
sudo ufw status numbered | grep -E "(8899|8900|6379)"
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