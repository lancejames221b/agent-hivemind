# hAIveMind Quick Start Guide

Get up and running with hAIveMind in under 5 minutes.

## What is hAIveMind?

hAIveMind is a **distributed AI memory and coordination platform** that enables multiple Claude AI agents to:
- **Share knowledge** across machines and projects
- **Collaborate** on complex tasks with task delegation
- **Remember** everything with persistent vector storage
- **Secure** credentials with encrypted vaults
- **Trust** information with confidence scoring

Built on the Model Context Protocol (MCP), hAIveMind integrates directly with Claude Desktop, Cursor, and other MCP-compatible AI tools.

---

## Installation

### Prerequisites
- Python 3.9+
- Redis server
- Git

### Step 1: Clone & Install

```bash
# Clone the repository
git clone https://github.com/lancejames221b/haivemind-mcp-server.git
cd haivemind-mcp-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Redis
# Ubuntu/Debian:
sudo apt-get install redis-server
sudo systemctl start redis-server

# macOS:
brew install redis && brew services start redis
```

### Step 2: Start the Server

```bash
# Start the SSE server (recommended for most users)
python src/remote_mcp_server.py

# Server starts on http://localhost:8900
# You should see: "Starting server on http://0.0.0.0:8900"
```

### Step 3: Connect Your AI Tool

#### For Claude Desktop

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "haivemind": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-http", "http://localhost:8900/sse"]
    }
  }
}
```

#### For Cursor AI

Copy the provided config:
```bash
cp mcp-client/config/cursor-agent.json .cursor/mcp.json
```

#### For Claude Code CLI

```bash
claude mcp add --transport http haivemind http://localhost:8900/sse
```

### Step 4: Verify Connection

```bash
# Test the server is running
curl http://localhost:8900/health

# Should return: {"status": "healthy", ...}
```

---

## First Steps

Once connected, try these commands in your AI tool:

### 1. Store Your First Memory

```
Store this memory: "Redis runs on port 6379 by default. Config file at /etc/redis/redis.conf"
Category: infrastructure
Tags: redis, configuration
```

### 2. Search Memories

```
Search memories for "redis configuration"
```

### 3. Register as an Agent

```
Register me as a hAIveMind agent with role "developer" and capabilities "code_review, testing"
```

### 4. View Agent Network

```
Show me the agent roster
```

---

## Core Features

### Memory Management
| Tool | Description |
|------|-------------|
| `store_memory` | Save knowledge with category, tags, importance |
| `search_memories` | Full-text and semantic search |
| `retrieve_memory` | Get specific memory by ID |
| `get_recent_memories` | Time-based retrieval |

### Agent Coordination
| Tool | Description |
|------|-------------|
| `register_agent` | Join the hAIveMind network |
| `get_agent_roster` | View all active agents |
| `delegate_task` | Assign tasks to specialists |
| `broadcast_discovery` | Share findings network-wide |

### Teams & Vaults (17 tools)
| Category | Tools |
|----------|-------|
| Mode Management | `get_mode`, `set_mode`, `list_available_modes` |
| Teams | `create_team`, `list_teams`, `get_team`, `add_team_member`, `remove_team_member`, `get_team_activity` |
| Vaults | `create_vault`, `list_vaults`, `store_in_vault`, `retrieve_from_vault`, `list_vault_secrets`, `delete_vault_secret`, `share_vault`, `vault_audit_log` |

### Confidence System (8 tools)
| Tool | Description |
|------|-------------|
| `get_memory_confidence` | Score breakdown (0.0-1.0) |
| `verify_memory` | Mark as confirmed/outdated |
| `report_memory_usage` | Track success/failure |
| `search_high_confidence` | Find reliable info |
| `flag_outdated_memories` | Find stale content |

---

## Token-Optimized Format (v2)

hAIveMind v2 introduces token optimization. When storing memories, use these conventions for 60-80% token reduction:

### Symbols
- `->` flow/returns
- `|` OR options
- `?` optional
- `!` required
- `::` type annotation

### Example

**Instead of:**
```
The user should first authenticate using their API key, then they can search for items using a query string, and the system will return JSON results.
```

**Write:**
```
auth(key) -> search(query) -> JSON
```

### Tables Over Prose

**Instead of:**
```
Tool A does searching, Tool B does storage, Tool C does deletion.
```

**Write:**
```
| Tool | Function |
| A | search |
| B | storage |
| C | delete |
```

---

## Common Workflows

### DevOps Memory

```bash
# Record an incident
record_incident title="Database slow" description="High CPU on mysql1" severity="medium"

# Generate a runbook from successful procedures
generate_runbook title="MySQL Restart" procedure="1. Stop service 2. Clear cache 3. Start"

# Sync SSH config across machines
sync_ssh_config config_content="<your_ssh_config>"
```

### Team Collaboration

```bash
# Create a team
create_team name="Engineering" description="Main dev team"

# Add team members
add_team_member team_id="team_xxx" user_id="alice@dev.com" role="admin"

# Create a team vault for secrets
create_vault name="Prod Secrets" vault_type="team" team_id="team_xxx"

# Store a secret
store_in_vault vault_id="vault_xxx" key="api_key" value="sk_live_xxxx"
```

### Verify Information Quality

```bash
# Check confidence score before acting
get_memory_confidence memory_id="mem_xxx"

# Verify information is still accurate
verify_memory memory_id="mem_xxx" verification_type="confirmed" notes="Tested today"

# Report action outcome
report_memory_usage memory_id="mem_xxx" action="Connected to DB" outcome="success"
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   AI Tools (Claude, Cursor)                 │
├─────────────────────────────────────────────────────────────┤
│                    MCP Protocol (SSE/HTTP)                  │
├─────────────────────────────────────────────────────────────┤
│                 hAIveMind Remote Server                     │
│                    (Port 8900)                              │
├────────────────┬───────────────────┬───────────────────────┤
│  Memory System │   Teams/Vaults    │   Confidence System   │
├────────────────┴───────────────────┴───────────────────────┤
│                    Storage Layer                            │
│      ChromaDB (Vectors)  │  Redis (Cache)  │  SQLite       │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Server won't start
```bash
# Check Redis is running
redis-cli ping  # Should return "PONG"

# Check port is available
lsof -i :8900
```

### MCP connection fails
```bash
# Verify server health
curl http://localhost:8900/health

# Check logs
tail -f logs/haivemind.log
```

### Memories not found
```bash
# Check ChromaDB path exists
ls -la data/chroma/

# Verify Redis cache
redis-cli keys "*memory*"
```

---

## Next Steps

1. **Read the full README**: [README.md](README.md)
2. **Explore MCP Integration**: [MCP_INTEGRATION.md](MCP_INTEGRATION.md)
3. **Learn about Teams & Vaults**: [TEAMS_VAULTS_TEST_RESULTS.md](TEAMS_VAULTS_TEST_RESULTS.md)
4. **Understand Confidence Scoring**: [CONFIDENCE_SYSTEM_SUMMARY.md](CONFIDENCE_SYSTEM_SUMMARY.md)
5. **Review all tools in CLAUDE.md**: [CLAUDE.md](CLAUDE.md)

---

## Support

- **Issues**: [GitHub Issues](https://github.com/lancejames221b/haivemind-mcp-server/issues)
- **Documentation**: See `docs/` directory
- **Examples**: See `examples/` directory

---

**hAIveMind v2.0.0** - Distributed AI Collective Intelligence

Built by Lance James, Unit 221B, Inc
