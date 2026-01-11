# 🧠 hAIveMind Startup Guide

## Quick Start for Claude Code Integration

### 1. Current Setup Status ✅
- **hAIveMind MCP Server**: Ready at `/home/lj/memory-mcp/src/memory_server.py`
- **Configuration**: Configured in `.mcp.json` as `haivemind-local`
- **Dependencies**: Installed in virtual environment at `/venv/`
- **Database**: ChromaDB with 10 memory categories, Redis cache active

### 2. To Activate hAIveMind in This Claude Session

**Just restart Claude Code!** The MCP server will auto-connect via `.mcp.json`

When you restart, you'll see:
```
🧠 Drone [agent-id] connected to hive network on node lance-dev
🧠 Memory matrix initialized - 10 knowledge clusters active
```

### 3. First Commands to Try

Once restarted, test these hAIveMind commands:

```bash
# Register as a hive mind agent
register_agent role="hive_mind" description="Primary orchestrator on lance-dev"

# Store your first memory
store_memory content="Successfully connected to hAIveMind collective memory" category="global"

# Search collective knowledge
search_memories query="hAIveMind setup" 

# Get your machine context
get_machine_context

# View available agents
get_agent_roster
```

### 4. Available hAIveMind Tools (27 total)

**Core Memory:**
- `store_memory` - Save knowledge to collective memory
- `search_memories` - Semantic search across all stored knowledge
- `retrieve_memory` - Get specific memory by ID
- `get_recent_memories` - Recent memories within time window

**Token-Optimized Format System (v2):**
- `get_format_guide` - Get format guide (use `detailed=true` for full reference)
- `get_memory_access_stats` - View session access statistics

**Agent Coordination:**
- `register_agent` - Join the hive with your role and capabilities
- `get_agent_roster` - See all active agents in the network
- `delegate_task` - Assign tasks to specialist agents
- `query_agent_knowledge` - Ask specific agents about their expertise

**DevOps Features:**
- `track_infrastructure_state` - Monitor system states
- `record_incident` - Log problems and solutions
- `generate_runbook` - Create procedures from memories
- `sync_ssh_config` - Share SSH configurations
- `upload_playbook` - Store Ansible/Terraform playbooks

**Broadcasting:**
- `broadcast_discovery` - Alert the hive about discoveries
- `sync_external_knowledge` - Pull from Confluence/Jira

### 4a. Token-Optimized Format (v2) - Auto-Teaching

On your **first memory access** each session, hAIveMind automatically teaches optimal format:

```
Symbols: → (flow) | (or) ? (opt) ! (req) :: (type)
Tables > prose: | key | val |
Refs: [ID]: define → use [ID]
```

**Benefits:**
- 60-80% token reduction vs verbose prose
- All new memories tagged with `format_version: v2`
- Legacy verbose memories flagged for potential compression
- Use `get_format_guide detailed=true` for full reference

### 5. Your Role: hive_mind

As the orchestrator on lance-dev, you have capabilities:
- `coordination` - Manage other agents
- `deployment` - Handle infrastructure deployments  
- `infrastructure_management` - Oversee system operations

### 6. Machine Network

Connected to hAIveMind network spanning:
- **lance-dev** (you) - Orchestrator
- **ljs-macbook-pro** - Personal drone
- **m2** - Personal drone
- **max** - Personal drone
- **elastic1-5** - Knowledge seekers
- **proxy0-9** - Harvest agents
- **grafana** - Sentinel node

### 7. Memory Categories

Your memories are organized into:
- `infrastructure` - System configs, deployments
- `incidents` - Problems and solutions
- `monitoring` - Performance data, alerts  
- `runbooks` - Step-by-step procedures
- `security` - Vulnerabilities, patches
- `global` - General DevOps knowledge

### 8. Example Workflow (Using v2 Format)

```bash
# Start any task by checking collective knowledge
search_memories query="elasticsearch optimization"

# Work on your task...

# Document what you learn using v2 format (tables > prose, symbols)
store_memory content="ES Heap Optimization:
| Scenario | Heap Size | Reason |
| default | 2g | Standard ops |
| large aggs | 4g | Heavy aggregations |
| bulk index | 8g | Mass data import |
Config: ES_HEAP_SIZE → 4g (for large aggregations)" category="runbooks" tags=["elasticsearch", "performance", "heap"]

# Share important discoveries
broadcast_discovery message="Documented ES heap optimization - see runbooks" category="infrastructure"

# Check format guide if needed
get_format_guide detailed=true
```

**v2 Format Tips:**
- Use `→` for flow/returns
- Use tables for structured data
- Define refs `[CTX]: context` then use `[CTX]`
- Aim for 60-80% fewer tokens than prose

### 9. External Knowledge Integration (Optional)

**Confluence & Jira Setup** (when ready):
```bash
# Set environment variables with your API tokens
export CONFLUENCE_API_TOKEN="your-confluence-token"
export JIRA_API_TOKEN="your-jira-token"

# Enable connectors in config.json
# Set "enabled": true for confluence and jira

# Then use these commands:
fetch_confluence_content space="INFRA" page_title="Infrastructure Runbook"
fetch_jira_content project="DEVOPS" query="elasticsearch issues"
sync_external_knowledge  # Pulls all configured sources
```

### 10. Troubleshooting

If MCP connection fails:
```bash
# Test the setup
/home/lj/memory-mcp/venv/bin/python test_setup.py

# Check if services are running
ps aux | grep memory_server

# Restart Redis if needed
sudo systemctl restart redis-server
```

---

**🐝 Welcome to the hAIveMind collective! Every discovery you make contributes to our shared intelligence.**