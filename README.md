# hAIveMind MCP Server

A distributed multi-agent DevOps memory system implementing the Model Context Protocol (MCP). Enables Claude and other AI agents to share knowledge, coordinate tasks, and maintain persistent memory across distributed infrastructure.

## Features

- **Persistent Memory Storage**: ChromaDB-backed vector storage with Redis caching
- **Multi-Agent Coordination**: Register agents, delegate tasks, and share discoveries across the collective
- **Teams & Vaults**: Secure collaborative workspaces with encrypted secret management
- **Confidentiality Controls**: PII/confidential data protection with sync/broadcast filtering
- **Token-Optimized Format**: 60-80% token reduction with v2 format system
- **Remote Access**: HTTP/SSE server for MCP clients over secure networks
- **126+ MCP Tools**: Comprehensive DevOps tooling for infrastructure, deployment, and monitoring
- **Configuration Management**: Drift detection, snapshots, and intelligent alerting
- **Disaster Recovery**: Automated backups, failover, and chaos engineering support

## Version

**Current Release: v2.1.5**

### Recent Changes
- v2.1.5: Fixed PII protection MCP tool exposure, comprehensive README update
- v2.1.4: PII/Confidential memory protection system
- v2.1.3: Agents directory support in vault system
- v2.1.2: Full toolset enabled in remote server
- v2.1.1: Vault sync tools restored

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd haivemind-mcp-server

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the remote HTTP/SSE server (recommended)
python src/remote_mcp_server.py

# Or start the local MCP server (stdio)
python src/memory_server.py
```

## Configuration

### Claude Code Integration

Add to `~/.claude/mcp.json`:
```json
{
  "mcpServers": {
    "haivemind": {
      "command": "mcp-client-sse",
      "args": ["http://localhost:8900/sse"],
      "env": {"HTTP_TIMEOUT": "30000"}
    }
  }
}
```

### Server Configuration

Copy `config/config.example.json` to `config/config.json`:
```json
{
  "storage": {
    "chromadb": {"path": "/data/chroma/"}
  },
  "server": {"port": 8900}
}
```

## MCP Tools (126 Total)

### Core Memory Tools
| Tool | Description |
|------|-------------|
| `store_memory` | Store memories with confidentiality controls |
| `retrieve_memory` | Get specific memory by ID |
| `update_memory_confidentiality` | Upgrade memory protection level (one-way) |
| `search_memories` | Full-text and semantic search with filtering |
| `get_recent_memories` | Time-windowed retrieval |
| `get_memory_stats` | Statistics and counts |
| `get_project_memories` | Project-scoped memories |
| `import_conversation` | Bulk import conversations |

### Confidentiality Levels
| Level | Sync | Broadcast | Search | Description |
|-------|------|-----------|--------|-------------|
| `normal` | Yes | Yes | Full | Default - full visibility |
| `internal` | No | Limited | Full | No external machine sync |
| `confidential` | No | No | Local | Local machine only |
| `pii` | No | No | Local | Audit logged, blocked from all distribution |

### Agent Coordination
| Tool | Description |
|------|-------------|
| `register_agent` | Register with the collective |
| `get_agent_roster` | List all active agents |
| `delegate_task` | Assign work to specialists |
| `query_agent_knowledge` | Query specific agent expertise |
| `broadcast_discovery` | Share findings with all agents |
| `get_broadcasts` | Retrieve recent broadcasts |

### Teams & Vaults
| Tool | Description |
|------|-------------|
| `create_team` / `list_teams` | Collaborative workspaces |
| `create_vault` / `store_in_vault` | Encrypted secret storage |
| `retrieve_from_vault` | Decrypt and retrieve secrets |
| `share_vault` | Grant access to users/teams |
| `vault_audit_log` | Security audit trail |

### Infrastructure Management
| Tool | Description |
|------|-------------|
| `track_infrastructure_state` | Record infrastructure snapshots |
| `record_incident` | Log incidents with correlation |
| `generate_runbook` | Create reusable procedures |
| `sync_ssh_config` | Distribute SSH configurations |
| `sync_infrastructure_config` | Sync any infra config |

### Configuration Management
| Tool | Description |
|------|-------------|
| `create_config_snapshot` | Capture configuration state |
| `detect_config_drift` | Intelligent drift detection |
| `get_config_history` | Configuration change history |
| `create_intelligent_config_alert` | Smart alerting rules |
| `get_drift_trend_analysis` | Predictive drift analysis |
| `diff_config_files` | Compare configurations |

### Backup & Recovery
| Tool | Description |
|------|-------------|
| `backup_all_configs` | Full configuration backup |
| `backup_agent_state` | Agent state preservation |
| `backup_project` | Project-level backups |
| `restore_from_backup` | Safe restoration |
| `verify_backup` | Backup integrity check |
| `scheduled_backup` | Automated backup scheduling |

### Deployment Pipeline
| Tool | Description |
|------|-------------|
| `create_deployment_pipeline` | Define CI/CD pipelines |
| `execute_deployment` | Run deployments |
| `rollback_deployment` | Automated rollback |
| `deployment_approval_workflow` | Approval gates |
| `backup_before_deployment` | Pre-deploy snapshots |

### Service Discovery
| Tool | Description |
|------|-------------|
| `discover_services` | Automatic service discovery |
| `register_service` | Manual service registration |
| `service_dependency_map` | Dependency visualization |
| `health_check_all` | Comprehensive health checks |

### Ticket Management
| Tool | Description |
|------|-------------|
| `create_ticket` | Create work tickets |
| `get_ticket` / `list_tickets` | Retrieve tickets |
| `update_ticket_status` | Status updates |
| `search_tickets` | Search and filter |
| `get_my_tickets` | Personal ticket list |
| `add_ticket_comment` | Add comments |
| `get_ticket_metrics` | Analytics |

### External Integrations
| Tool | Description |
|------|-------------|
| `fetch_from_confluence` | Import Confluence docs |
| `fetch_from_jira` | Import Jira issues |
| `sync_external_knowledge` | Sync all external sources |
| `upload_playbook` | Store Ansible/Terraform |

### Project Management
| Tool | Description |
|------|-------------|
| `create_project` / `list_projects` | Project CRUD |
| `switch_project_context` | Context switching |
| `project_health_check` | Health analysis |
| `backup_project` / `restore_project` | Project backup/restore |

## Usage Examples

### Store Memory with PII Protection
```python
# Normal memory (synced across network)
store_memory(content="API endpoint documented", category="infrastructure")

# PII memory (local only, never synced)
store_memory(
    content="Customer SSN: xxx-xx-xxxx",
    category="security",
    confidentiality_level="pii"
)
```

### Upgrade Confidentiality (One-Way)
```python
# Mark existing memory as confidential
update_memory_confidentiality(
    memory_id="abc123",
    confidentiality_level="confidential",
    reason="Contains sensitive customer data"
)
```

### Agent Coordination
```python
# Register as a specialist
register_agent(role="elasticsearch_ops", description="ES cluster management")

# Delegate work
delegate_task(
    task_description="Optimize slow queries",
    required_capabilities=["elasticsearch_ops"]
)

# Share discoveries
broadcast_discovery(
    message="Found memory leak in scraper",
    category="infrastructure",
    severity="warning"
)
```

### Configuration Drift Detection
```python
# Create snapshot
create_config_snapshot(
    system_id="elastic1",
    config_type="elasticsearch",
    config_content="<yaml>",
    file_path="/etc/elasticsearch/elasticsearch.yml"
)

# Detect drift
detect_config_drift(system_id="elastic1", threshold=0.8)

# Get trend analysis
get_drift_trend_analysis(system_id="elastic1", days_back=7)
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Claude Code    │────▶│  Remote Server  │────▶│    ChromaDB     │
│  (MCP Client)   │ SSE │  (port 8900)    │     │  (Vector Store) │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │  Redis   │ │  Sync    │ │  Teams   │
              │ (Cache)  │ │ Service  │ │ & Vaults │
              └──────────┘ └──────────┘ └──────────┘
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Remote Server | 8900 | HTTP/SSE for MCP clients |
| Sync Service | 8899 | Machine-to-machine sync |
| Memory Server | stdio | Local MCP integration |

## Systemd Installation

```bash
# Install all services
sudo bash services/install-services.sh

# Or individual services
sudo systemctl enable haivemind-remote-mcp
sudo systemctl start haivemind-remote-mcp
```

## Requirements

- Python 3.10+
- Redis server
- ChromaDB

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/sse` | GET | SSE stream for MCP |
| `/mcp` | POST | Streamable HTTP for MCP |
| `/api/tools` | GET | List available tools |

## Security

- **Confidentiality Levels**: PII/confidential data never leaves local machine
- **Vault Encryption**: XOR-based encryption (upgradeable to AES-GCM)
- **Audit Logging**: All vault access logged with actor/reason
- **JWT Authentication**: API endpoint protection
- **Tailscale Integration**: Secure machine-to-machine communication

## License

MIT License

## Contributing

Contributions welcome. Please ensure:
- No PII or internal infrastructure details in commits
- Tests pass for confidentiality filtering
- Documentation updated for new features
