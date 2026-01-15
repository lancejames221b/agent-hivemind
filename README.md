# hAIveMind MCP Server

A distributed multi-agent DevOps memory system implementing the Model Context Protocol (MCP). Enables Claude and other AI agents to share knowledge, coordinate tasks, and maintain persistent memory across distributed infrastructure.

## Features

- **Persistent Memory Storage**: ChromaDB-backed vector storage with Redis caching
- **Multi-Agent Coordination**: Register agents, delegate tasks, and share discoveries
- **Teams & Vaults**: Secure collaborative workspaces with encrypted secret management
- **Confidentiality Controls**: PII/confidential data protection with sync/broadcast filtering
- **Token-Optimized Format**: 60-80% token reduction with v2 format system
- **Remote Access**: HTTP/SSE server for MCP clients over secure networks

## Version

**Current Release: v2.1.4**

### Recent Changes
- v2.1.4: PII/Confidential memory protection system
- v2.1.3: Agents directory support in vault system
- v2.1.2: Full toolset enabled in remote server
- v2.1.1: Vault sync tools restored

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd haivemind-mcp-server

# Install dependencies
pip install -r requirements.txt

# Start the local MCP server
python src/memory_server.py

# Or start the remote HTTP/SSE server
python src/remote_mcp_server.py
```

## Configuration

Copy `config/config.example.json` to `config/config.json` and configure:

```json
{
  "storage": {
    "chromadb": {
      "path": "/data/chroma/"
    }
  },
  "server": {
    "port": 8900
  }
}
```

## MCP Tools

### Core Memory Tools
- `store_memory` - Store memories with confidentiality controls
- `retrieve_memory` - Get specific memory by ID
- `update_memory` - Update memory content/metadata
- `search_memories` - Full-text and semantic search
- `get_recent_memories` - Time-windowed retrieval
- `update_memory_confidentiality` - Upgrade memory protection level

### Confidentiality Levels
| Level | Behavior |
|-------|----------|
| `normal` | Full sync, broadcast, search visibility |
| `internal` | No external sync, limited broadcast |
| `confidential` | Local only, no sync, no broadcast |
| `pii` | Local only, audit logged, blocked from all external distribution |

### Agent Coordination
- `register_agent` - Register with the collective
- `delegate_task` - Assign work to specialists
- `broadcast_discovery` - Share findings with all agents
- `query_agent_knowledge` - Query specific agent expertise

### Teams & Vaults
- `create_team` / `list_teams` - Collaborative workspaces
- `create_vault` / `store_in_vault` - Encrypted secret storage
- `share_vault` / `vault_audit_log` - Access control and auditing

## Usage Examples

### Store a Memory with Confidentiality
```python
# Normal memory (synced across network)
store_memory(content="API endpoint documented", category="infrastructure")

# PII memory (local only, never synced)
store_memory(
    content="User credentials: ...",
    category="security",
    confidentiality_level="pii"
)
```

### Upgrade Confidentiality
```python
# Mark existing memory as confidential (upgrade only)
update_memory_confidentiality(
    memory_id="abc123",
    confidentiality_level="confidential",
    reason="Contains sensitive customer data"
)
```

### Search with Filtering
```python
# Remote access automatically excludes confidential/pii
search_memories(query="deployment procedures", category="runbooks")
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  MCP Clients    │────▶│  Memory Server  │
│  (Claude, etc)  │     │  (stdio/HTTP)   │
└─────────────────┘     └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ ChromaDB │ │  Redis   │ │  Sync    │
              │ (Vector) │ │ (Cache)  │ │ Service  │
              └──────────┘ └──────────┘ └──────────┘
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Memory Server | stdio | Local MCP integration |
| Remote Server | 8900 | HTTP/SSE for remote clients |
| Sync Service | 8899 | Machine-to-machine sync |

## Requirements

- Python 3.10+
- Redis server
- ChromaDB

## License

MIT License

## Contributing

Contributions welcome. Please ensure:
- No PII or internal infrastructure details in commits
- Tests pass for confidentiality filtering
- Documentation updated for new features
