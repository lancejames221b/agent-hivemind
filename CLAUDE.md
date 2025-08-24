# CLAUDE.md - ClaudeOps hAIveMind DevOps Memory System

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ClaudeOps hAIveMind Overview

**ClaudeOps** is a **hAIveMind** - a centralized multi-agent DevOps memory MCP (Model Context Protocol) server that enables multiple Claude agents to collaborate on DevOps tasks across your entire infrastructure. The system provides persistent memory storage, real-time synchronization, agent coordination, and infrastructure management capabilities.

### hAIveMind Features:
- **Collective Intelligence**: Claude agents share knowledge, delegate tasks, and coordinate responses across infrastructure
- **Infrastructure Configuration Sync**: SSH configs, service configs, and other critical DevOps assets synchronized across the network
- **DevOps Memory Categories**: Specialized storage for infrastructure, incidents, deployments, monitoring, runbooks, and security
- **Real-Time Collaboration**: Agents broadcast discoveries, query each other's knowledge, and coordinate autonomous responses
- **Distributed Storage**: ChromaDB for vector storage, Redis for caching, with conflict resolution via vector clocks

## Architecture

- **memory_server.py**: Main MCP server that interfaces with Claude Code via stdio protocol
- **remote_mcp_server.py**: FastMCP-based remote server for HTTP/SSE access via Tailscale network
- **sync_service.py**: FastAPI REST service for machine-to-machine synchronization via Tailscale network
- **ChromaDB**: Vector database for semantic search and embeddings storage at `/data/chroma/`
- **Redis**: Caching layer for fast memory access and real-time sync capabilities
- **Tailscale Integration**: Secure network communication between machines (lance-dev, ljs-macbook-pro, m2, max)

## Development Commands

### Start Services
```bash
# Start local MCP server (for Claude Code stdio integration)
python src/memory_server.py

# Start remote MCP server (for HTTP/SSE access)
python src/remote_mcp_server.py

# Start sync service (for machine-to-machine synchronization) 
python src/sync_service.py

# Install dependencies
pip install -r requirements.txt
```

### Setup Commands
```bash
# Install Redis
sudo apt-get install redis-server
sudo systemctl start redis-server

# Install all services as systemd
sudo bash services/install-services.sh

# Remote machine setup
bash INSTALL/setup-remote.sh
```

### Testing and Monitoring
```bash
# Check sync service status
curl http://localhost:8899/api/status

# Check remote MCP server health
curl http://localhost:8900/health

# Manual sync trigger
curl -X POST http://localhost:8899/api/trigger-sync -H "Authorization: Bearer your-api-token"

# Test Tailscale connectivity
ping ljs-macbook-pro && ping m2 && ping max
```

## Configuration

- **config/config.json**: Main configuration file with server, storage, sync, remote server, and security settings
- **.mcp.json**: MCP server configuration for Claude Code integration
- **Port 8899**: Sync service API port for machine-to-machine communication
- **Port 8900**: Remote MCP server port for HTTP/SSE client access
- **Machine Discovery**: Configured in sync.discovery.machines for Tailscale hostnames

## Remote Access

### For Claude Desktop
```json
{
  "mcpServers": {
    "remote-memory": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-http", "http://lance-dev:8900/sse"],
      "env": {"HTTP_TIMEOUT": "30000"}
    }
  }
}
```

### For Claude Code CLI
```bash
claude mcp add --transport http remote-memory http://lance-dev:8900/sse
```

## ClaudeOps Memory Categories

The system supports comprehensive memory categories for DevOps operations:

### Core Categories:
- `project`: Project-specific memories and context
- `conversation`: Conversation history and context  
- `agent`: Agent-specific knowledge and preferences
- `global`: Cross-project shared knowledge

### DevOps Categories:
- `infrastructure`: Server configs, network topology, service dependencies, SSH configurations
- `incidents`: Outage reports, resolutions, post-mortems, lessons learned
- `deployments`: Release notes, rollback procedures, deployment history
- `monitoring`: Alerts, metrics, thresholds, patterns, dashboard configs
- `runbooks`: Automated procedures, scripts, troubleshooting guides
- `security`: Vulnerabilities, patches, audit logs, compliance data

## ClaudeOps MCP Tools Available

### Core Memory Tools:
- `store_memory`: Store memories with comprehensive machine tracking and sharing control
- `retrieve_memory`: Get specific memory by ID
- `search_memories`: Full-text and semantic search with machine/project filtering
- `get_recent_memories`: Get memories within specified time window
- `get_memory_stats`: Statistics about stored memories
- `get_project_memories`: Get all memories for current project
- `get_machine_context`: Get comprehensive machine context
- `list_memory_sources`: List all machines with memory statistics
- `import_conversation`: Import full conversations as structured memories

### ClaudeOps hAIveMind Management Tools:
- `register_agent`: Register new hAIveMind agent with role and capabilities
- `get_agent_roster`: List all active hAIveMind agents and their current status
- `delegate_task`: Assign tasks to specific agents or find best available agent
- `query_agent_knowledge`: Query what a specific agent knows about topics/systems
- `broadcast_discovery`: Share important findings with all hAIveMind agents

### Infrastructure & DevOps Tools:
- `track_infrastructure_state`: Record infrastructure state snapshots for monitoring
- `record_incident`: Record DevOps incidents with automatic correlation
- `generate_runbook`: Create reusable runbooks from successful procedures
- `sync_ssh_config`: Sync SSH configuration across ClaudeOps infrastructure
- `sync_infrastructure_config`: Sync any infrastructure configuration across network

### Automation & Playbook Tools:
- `upload_playbook`: Upload and store Ansible/Terraform/Kubernetes playbooks
- `fetch_from_confluence`: Fetch documentation from Confluence and store as knowledge
- `fetch_from_jira`: Fetch issues from Jira and store as incident/task knowledge  
- `sync_external_knowledge`: Sync from all configured external sources automatically

### Agent Capabilities by Machine Group:
- **Orchestrators** (`lance-dev`): `coordination`, `deployment`, `infrastructure_management`
- **Elasticsearch** (`elastic1-5`): `elasticsearch_ops`, `search_tuning`, `cluster_management`
- **Databases** (`mysql`, `mongodb`, `kafka`): `database_ops`, `backup_restore`, `query_optimization`
- **Scrapers** (`proxy0-9`, `telegram-scraper`): `data_collection`, `scraping`, `proxy_management`
- **Dev Environments** (`tony-dev`, `mike-dev`, etc.): `development`, `testing`, `code_review`
- **Monitoring** (`grafana`, `auth-server`): `monitoring`, `alerting`, `incident_response`

## Network Architecture

Uses vector clocks for conflict resolution during sync. Each machine maintains:
- Local ChromaDB instance with vector embeddings
- Redis cache for performance
- REST API endpoint for sync communication
- WebSocket endpoint at `/ws/{machine_id}` for real-time updates

## Security

- JWT authentication for API endpoints
- Encrypted credentials storage at `/home/lj/Credentials/keys.txt.enc`
- Tailscale VPN for secure machine-to-machine communication
- Redis password protection (configurable in config.json)

## ClaudeOps hAIveMind Usage Examples

### hAIveMind Registration and Coordination:
```bash
# Register as a hive_mind agent on lance-dev
register_agent role="hive_mind" description="Primary hAIveMind orchestrator"

# View all active hAIveMind agents
get_agent_roster

# Delegate a task to elasticsearch specialists
delegate_task task_description="Optimize search performance on elastic1" required_capabilities=["elasticsearch_ops"]
```

### Infrastructure Management:
```bash
# Sync SSH configuration across all machines
sync_ssh_config config_content="<ssh_config_content>" target_machines=["elastic1", "elastic2"]

# Track infrastructure state
track_infrastructure_state machine_id="elastic1" state_type="service_status" state_data={"elasticsearch": "running", "cpu": "65%"}

# Record an incident
record_incident title="Elasticsearch cluster degraded" description="High CPU on elastic1" severity="high" affected_systems=["elastic1"]
```

### hAIveMind Knowledge Sharing:
```bash
# Broadcast important discovery to the hAIveMind
broadcast_discovery message="Found memory leak in scraper service" category="infrastructure" severity="warning"

# Query what another hAIveMind agent knows
query_agent_knowledge agent_id="elastic1-specialist" query="memory optimization techniques"

# Generate runbook from successful procedure
generate_runbook title="Elasticsearch Restart Procedure" procedure="1. Stop service 2. Clear cache 3. Start service" system="elasticsearch"
```

### Playbook & Automation Management:
```bash
# Upload Ansible playbook
upload_playbook playbook_name="Deploy Nginx" playbook_content="<yaml_content>" playbook_type="ansible" target_systems=["web-servers"]

# Fetch documentation from Confluence  
fetch_from_confluence space_key="DEVOPS" page_title="Deployment Guide"

# Fetch incidents from Jira
fetch_from_jira project_key="INFRA" issue_types=["Bug", "Incident"] limit=25

# Sync all external knowledge sources
sync_external_knowledge sources=["confluence", "jira"]
```

## Troubleshooting

- MCP integration requires `enableAllProjectMcpServers: true` in Claude Code settings
- Redis connection issues: Check Redis service and config.json settings
- Machine discovery requires Tailscale running and correct hostnames in config
- Sync failures often relate to API token configuration or port 8899 accessibility
- hAIveMind agent registration requires Redis for coordination features to work
- ClaudeOps hAIveMind features require the updated config.json with claudeops section
- if you get an mcp failure for haivemind, we need to stop and fix it.