# hAIveMind MCP Integration Guide

## Overview

The hAIveMind system now provides full MCP (Model Context Protocol) integration, enabling Claude agents to access the distributed memory system through both local stdio and remote HTTP/SSE transports.

## Architecture

```
Claude Agent (cursor-agent) 
    ↓ stdio
hAIveMind MCP Bridge Client (/home/lj/.local/bin/haivemind-mcp-client)
    ↓ HTTP JSON-RPC
hAIveMind Remote MCP Server (localhost:8900)
    ↓
Memory Storage (ChromaDB + Redis)
```

## Components

### 1. hAIveMind MCP Bridge Client
**Location**: `/home/lj/.local/bin/haivemind-mcp-client`

A Python bridge that converts stdio MCP protocol to HTTP requests, enabling cursor-agent (which only supports stdio transport) to communicate with the hAIveMind remote server.

**Features**:
- Converts JSON-RPC stdio ↔ HTTP requests
- Handles MCP protocol methods: `initialize`, `tools/list`, `tools/call`
- Error handling and logging
- 30-second timeout for requests

### 2. Remote MCP Server
**Location**: `src/remote_mcp_server.py`
**Port**: 8900
**Endpoints**:
- `/health` - Health check
- `/sse` - Server-Sent Events endpoint
- `/mcp` - HTTP JSON-RPC endpoint

### 3. MCP Configuration
**Location**: `.cursor/mcp.json`

Configures cursor-agent to use the bridge client for hAIveMind access.

## Installation & Setup

### 1. Start hAIveMind Services

```bash
# Start all services
python src/memory_server.py &        # Local MCP server
python src/remote_mcp_server.py &    # Remote HTTP/SSE server  
python src/sync_service.py &         # Machine-to-machine sync
```

### 2. Verify Services

```bash
# Check service health
curl http://localhost:8900/health
curl http://localhost:8899/api/status

# Verify processes
ps aux | grep -E "(memory_server|remote_mcp_server|sync_service)"
```

### 3. Test MCP Integration

```bash
# List available tools
cursor-agent mcp list-tools haivemind

# Test with interactive mode
cursor-agent mcp call-tool haivemind store_memory '{"content": "Test memory", "category": "test"}'
```

## Available MCP Tools

### Core Memory Tools
- `store_memory` - Store memories with machine tracking and sharing control
- `retrieve_memory` - Get specific memory by ID
- `search_memories` - Full-text and semantic search with filtering
- `get_recent_memories` - Get memories within time window
- `get_memory_stats` - Statistics about stored memories
- `get_project_memories` - Get all memories for current project
- `get_machine_context` - Get comprehensive machine context
- `list_memory_sources` - List all machines with memory statistics
- `import_conversation` - Import full conversations as structured memories

### Token-Optimized Format System (v2)
- `get_format_guide` - Get format guide (compact or detailed) for token-optimized storage
- `get_memory_access_stats` - View session access statistics

**Auto-Teaching**: On first memory access each session, the format guide is automatically injected:
```
Symbols: → (flow) | (or) ? (opt) ! (req) :: (type)
Tables > prose: | key | val |
Refs: [ID]: define → use [ID]
Target: 60-80% token reduction
```

All new memories are tagged with `format_version: v2`. Legacy verbose memories are flagged for potential compression.

### Memory Lifecycle Management
- `delete_memory` - Delete memory with soft/hard delete options
- `bulk_delete_memories` - Bulk delete with confirmation
- `recover_deleted_memory` - Recover from recycle bin
- `list_deleted_memories` - List recoverable memories
- `detect_duplicate_memories` - Find potential duplicates
- `merge_duplicate_memories` - Merge duplicate memories
- `cleanup_expired_deletions` - Clean up expired deletions
- `gdpr_delete_user_data` - GDPR compliant deletion
- `gdpr_export_user_data` - GDPR compliant export

### hAIveMind Coordination
- `register_agent` - Register new hAIveMind agent
- `get_agent_roster` - List all active agents
- `delegate_task` - Assign tasks to agents
- `query_agent_knowledge` - Query agent knowledge
- `broadcast_discovery` - Share findings with all agents

### Infrastructure & DevOps
- `track_infrastructure_state` - Record infrastructure snapshots
- `record_incident` - Record DevOps incidents
- `generate_runbook` - Create reusable runbooks
- `sync_ssh_config` - Sync SSH configuration
- `sync_infrastructure_config` - Sync infrastructure configs

### Automation & Playbooks
- `upload_playbook` - Store Ansible/Terraform playbooks
- `fetch_from_confluence` - Import Confluence documentation
- `fetch_from_jira` - Import Jira issues
- `sync_external_knowledge` - Sync all external sources

## Usage Examples

### Store Memory
```bash
cursor-agent --print -m sonnet-4 "Use store_memory to save information about the new deployment process"
```

### Search Memories
```bash
cursor-agent mcp call-tool haivemind search_memories '{"query": "elasticsearch configuration", "limit": 5}'
```

### Interactive Mode
```bash
cursor-agent mcp list-tools haivemind
cursor-agent mcp call-tool haivemind get_memory_stats '{}'
```

## Troubleshooting

### Connection Issues
```bash
# Check if services are running
ps aux | grep -E "(memory_server|remote_mcp_server)"

# Test endpoints directly
curl http://localhost:8900/health
curl http://localhost:8899/api/status
```

### Bridge Client Issues
```bash
# Test bridge client directly
echo '{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}' | /home/lj/.local/bin/haivemind-mcp-client

# Check bridge client permissions
ls -la /home/lj/.local/bin/haivemind-mcp-client
```

### Configuration Issues
```bash
# Verify MCP configuration
cat .cursor/mcp.json

# Check cursor-agent MCP status
cursor-agent mcp list-servers
```

## Network Architecture

The hAIveMind system operates across multiple machines via Tailscale VPN:

- **lance-dev**: Primary orchestrator with full hAIveMind services
- **elastic1-5**: Elasticsearch specialists with search optimization capabilities  
- **proxy0-9**: Data collection agents with scraping capabilities
- **auth-server, grafana**: Monitoring and authentication specialists

Each machine runs local memory storage with sync capabilities, enabling distributed AI coordination across the entire infrastructure.

## Security

- JWT authentication for API endpoints
- Encrypted credentials storage
- Tailscale VPN for secure communication
- Redis password protection
- Soft delete with 30-day recovery window
- GDPR compliance tools for data management

## Integration Status

✅ **PRODUCTION READY** - All components tested and operational:
- MCP Server running on lance-dev:8900
- Bridge client configured and executable
- cursor-agent integration verified
- Memory storage and search confirmed working
- hAIveMind coordination features active