# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**hAIveMind** (v2.1.4) is a distributed multi-agent DevOps memory MCP server enabling Claude agents to collaborate across infrastructure. It provides persistent memory storage, real-time sync, agent coordination, and infrastructure management.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Claude Code    │────▶│  memory_server   │────▶│    ChromaDB     │
│  (stdio MCP)    │     │   (local MCP)    │     │ (vector storage)│
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ remote_mcp_server│   │   sync_service   │   │      Redis       │
│  (HTTP/SSE:8900) │   │   (REST:8899)    │   │ (cache/pub-sub)  │
└──────────────────┘   └──────────────────┘   └──────────────────┘
        │                       │
        └───────Tailscale VPN───┘
```

### Core Files
- `src/memory_server.py`: Main MCP server (stdio), core memory operations
- `src/remote_mcp_server.py`: FastMCP HTTP/SSE server with 100+ tools, admin dashboard
- `src/sync_service.py`: Machine-to-machine sync via REST/WebSocket
- `src/teams_and_vaults_system.py`: Encrypted vaults and team collaboration
- `src/confidence_system.py`: Memory confidence scoring and verification
- `config/config.json`: All configuration (ports, Redis, Tailscale machines, memory categories)

## Development Commands

```bash
# Start services
python src/memory_server.py                    # Local MCP server (stdio)
python src/remote_mcp_server.py                # Remote HTTP/SSE server (:8900)
python src/sync_service.py                     # Sync service (:8899)

# Install as systemd services
sudo bash services/install-services.sh

# Service management
sudo systemctl start haivemind-remote-mcp
sudo systemctl restart haivemind-remote-mcp
sudo journalctl -u haivemind-remote-mcp -f

# Health checks
curl http://localhost:8900/health
curl http://localhost:8899/api/status

# Install dependencies
pip install -r requirements.txt
```

## Configuration

| File | Purpose |
|------|---------|
| `config/config.json` | Main config: ports, storage paths, Redis, Tailscale machines |
| `.mcp.json` | Claude Code MCP server configuration |
| `services/*.service` | Systemd service definitions |

### Key Ports
- **8899**: Sync service (machine-to-machine)
- **8900**: Remote MCP server (HTTP/SSE, admin dashboard)

### Tailscale Network
Machines configured for sync: `lance-dev`, `ljs-macbook-pro`, `m2`, `max`, `chris-dev`

## Memory Categories

Core: `project`, `conversation`, `agent`, `global`
DevOps: `infrastructure`, `incidents`, `deployments`, `monitoring`, `runbooks`, `security`

## PII/Confidentiality Protection (v2.1.4+)

Memories support confidentiality levels that control distribution:

| Level | Behavior |
|-------|----------|
| `normal` | Full sync, broadcast, visibility |
| `internal` | No external sync, limited broadcast |
| `confidential` | Local only, no sync/broadcast |
| `pii` | Local only, audit logged, blocked from all distribution |

```python
# Store PII-protected memory
store_memory(content="...", confidentiality_level="pii")

# Upgrade existing memory's confidentiality (one-way, can only make more restrictive)
update_memory_confidentiality(memory_id="...", confidentiality_level="confidential")
```

## Key MCP Tools

### Memory Operations
- `store_memory`, `retrieve_memory`, `update_memory`, `search_memories`
- `delete_memory` (soft/hard), `recover_deleted_memory`
- `update_memory_confidentiality` (upgrade only)

### Agent Coordination
- `register_agent`, `get_agent_roster`, `delegate_task`
- `broadcast_discovery`, `query_agent_knowledge`

### Teams & Vaults
- `create_team`, `add_team_member`, `get_team`
- `create_vault`, `store_in_vault`, `retrieve_from_vault`
- `get_mode`, `set_mode` (solo/vault/team)

### Infrastructure
- `track_infrastructure_state`, `record_incident`, `generate_runbook`
- `sync_ssh_config`, `sync_infrastructure_config`

## Operating Modes

- **Solo** (default): Private work, no sharing
- **Vault**: Access encrypted secrets, audit logged
- **Team**: Collaborative workspace with RBAC

## Troubleshooting

- **MCP not connecting**: Ensure `enableAllProjectMcpServers: true` in Claude Code settings
- **Port conflicts**: Check for stale processes with `lsof -i :8900` and kill them
- **Sync failures**: Verify Tailscale connectivity and Redis is running
- **Service won't start**: Check `journalctl -u haivemind-remote-mcp -f` for errors

### Common Issues
```bash
# Kill stale processes blocking port 8900
sudo lsof -i :8900 -t | xargs -r sudo kill -9

# Restart cleanly
sudo systemctl stop haivemind-remote-mcp
sleep 2
sudo systemctl start haivemind-remote-mcp
```

## Remote Access Setup

### Claude Desktop
```json
{
  "mcpServers": {
    "haivemind": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-http", "http://lance-dev:8900/sse"]
    }
  }
}
```

### Claude Code CLI
```bash
claude mcp add --transport http haivemind http://lance-dev:8900/sse
```

## Token-Optimized Format (v2)

Memory system auto-teaches optimal format on first access. Use compact notation:
- Symbols: `→` (flow), `|` (or), `?` (optional), `!` (required), `::` (type)
- Tables over prose
- `get_format_guide` for reference

## Critical Rules

- Never put PII in Confluence or semi-public places
- Never post to Slack unless explicitly told
- If MCP fails for haivemind, stop and fix it before continuing
- When using xargs kill, avoid killing Claude Code session
