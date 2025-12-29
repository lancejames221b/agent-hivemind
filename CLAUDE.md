# CLAUDE.md - ClaudeOps hAIveMind DevOps Memory System

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ClaudeOps hAIveMind Overview

**ClaudeOps** is a **hAIveMind** - a centralized multi-agent DevOps memory MCP (Model Context Protocol) server that enables multiple Claude agents to collaborate on DevOps tasks across your entire infrastructure. The system provides persistent memory storage, real-time synchronization, agent coordination, and infrastructure management capabilities.

### hAIveMind Features:
- **Collective Intelligence**: Claude agents share knowledge, delegate tasks, and coordinate responses across infrastructure
- **Teams & Vaults**: Secure collaborative workspaces with encrypted secret storage and role-based access control
- **Confidence Scoring**: Multi-dimensional reliability scoring helps agents trust information and reduce mistakes
- **Operating Modes**: Solo, Vault, and Team modes for context-aware memory storage and retrieval
- **Infrastructure Configuration Sync**: SSH configs, service configs, and other critical DevOps assets synchronized across the network
- **DevOps Memory Categories**: Specialized storage for infrastructure, incidents, deployments, monitoring, runbooks, and security
- **Real-Time Collaboration**: Agents broadcast discoveries, query each other's knowledge, and coordinate autonomous responses
- **Distributed Storage**: ChromaDB for vector storage, Redis for caching, with conflict resolution via vector clocks

## Architecture

- **memory_server.py**: Main MCP server that interfaces with Claude Code via stdio protocol
- **remote_mcp_server.py**: FastMCP-based remote server for HTTP/SSE access via Tailscale network
- **sync_service.py**: FastAPI REST service for machine-to-machine synchronization via Tailscale network
- **teams_and_vaults_system.py**: Team collaboration and secure vault management system
- **confidence_system.py**: Multi-dimensional confidence scoring for information reliability
- **ChromaDB**: Vector database for semantic search and embeddings storage at `/data/chroma/`
- **Redis**: Caching layer for fast memory access and real-time sync capabilities
- **Tailscale Integration**: Secure network communication between machines (lance-dev, ljs-macbook-pro, m2, max)

## Teams & Vaults System

The Teams and Vaults system enables secure collaboration and secret management for hAIveMind agents.

### Operating Modes

**Solo Mode** (Default - Safest):
- Private work - memories visible only to you
- No sharing - isolated context
- Use for personal notes and private work

**Vault Mode**:
- Access encrypted vaults for secrets and credentials
- All operations logged in audit trail
- Requires explicit vault access grants

**Team Mode**:
- Collaborative workspace with shared memories
- Team members can access shared context
- Role-based access control (owner, admin, member, readonly, guest)

### Teams

Teams enable collaborative work with role-based access:

- **Roles**: Owner (full control), Admin (manage members), Member (read/write), Readonly (view only), Guest (temporary)
- **Activity Tracking**: All team actions logged for transparency
- **Membership Management**: Invite, remove members with capability-based permissions

### Vaults

Vaults provide encrypted storage for sensitive data:

- **Types**: Personal (private), Team (shared), Project (scoped), Shared (cross-team)
- **Encryption**: XOR-based encryption with per-vault keys (upgradeable to AES-GCM/Fernet)
- **Audit Trail**: Every secret access logged with actor, reason, and timestamp
- **Access Levels**: Read, Write, Admin permissions with expiration support
- **Secret Storage**: API keys, passwords, credentials, SSH keys, certificates

## Confidence System

The Confidence System provides multi-dimensional scoring to help agents determine information reliability and make better decisions.

### Why Confidence Scoring?

**Problem**: All memories currently treated equally - 6-month-old info weighs same as yesterday's, expert knowledge = novice guesses
**Solution**: Calculate 0.0-1.0 confidence score from 7 factors to help agents avoid mistakes

### 7 Confidence Factors

Each memory scored on 7 dimensions (weights in parentheses):

1. **Freshness (20%)**: Time decay with category-specific half-lives
   - Infrastructure: 30-day half-life (changes frequently)
   - Security: 20 days (critical freshness)
   - Runbooks: 90 days (stable procedures)
   - Formula: `score = 0.5^(age / half_life)`

2. **Source Credibility (20%)**: Agent expertise and track record
   - Expert agents > novice agents
   - Historical accuracy rate tracked
   - Role-based trust (owner > admin > member)

3. **Verification Status (15%)**: Peer verification and consensus
   - Unverified: 0.3, Peer-verified: 0.7
   - Multi-verified: 0.85, System-verified: 1.0

4. **Consensus Level (15%)**: Multiple agents agreeing independently
   - Semantic similarity clustering
   - Voting mechanism with credibility weighting

5. **Contradiction Penalty (10%)**: Conflicting info detection
   - Auto-detects: "Redis port 6379" vs "Redis port 6380"
   - Auto-resolves using temporal/trust/consensus strategies

6. **Usage Success Rate (10%)**: Outcomes from using information
   - Tracks: success/failure when acting on memory
   - High success rate = boost confidence
   - High failure rate = flag for review

7. **Context Relevance (10%)**: Relevance to current task
   - Project/team match
   - Category alignment
   - System/machine relevance

### Confidence Levels

- 🟢 **Very High (0.85-1.0)**: Highly reliable - use with confidence
- 🟡 **High (0.70-0.84)**: Reliable - likely accurate
- 🟠 **Medium (0.55-0.69)**: Moderately reliable - verify if critical
- 🔴 **Low (0.40-0.54)**: Low confidence - verify before use
- ⚫ **Very Low (0.0-0.39)**: Very low confidence - likely outdated

### Risk-Based Decision Making

Required confidence thresholds by action risk:
- **Low risk** (e.g., viewing logs): 0.40 confidence
- **Medium risk** (e.g., restarting service): 0.60 confidence
- **High risk** (e.g., changing config): 0.75 confidence
- **Critical risk** (e.g., deleting data): 0.90 confidence

### Smart Features

- **Verification Extension**: Verifying old info resets freshness clock
- **Auto Error Detection**: Failed actions automatically tracked
- **Contradiction Resolution**: System auto-resolves conflicts when possible
- **Continuous Learning**: System learns from outcomes to improve scoring
- **Confidence-Aware Search**: Filter search by minimum confidence level

## Development Commands

### Start Services
```bash
# Start local MCP server (for Claude Code stdio integration)
python src/memory_server.py

# Start remote MCP server (for HTTP/SSE access with 57+ DevOps tools)
python src/remote_mcp_server.py

# Start sync service (for machine-to-machine synchronization) 
python src/sync_service.py

# Install dependencies
pip install -r requirements.txt
```

### Setup Commands
```bash
# Install Redis (required for hAIveMind coordination)
sudo apt-get install redis-server
sudo systemctl start redis-server

# Install all services as systemd
sudo bash services/install-services.sh

# Remote machine setup
bash INSTALL/setup-remote.sh

# Initialize database schemas
python -c "
from src.project_management_system import ProjectManagementSystem
from src.config_backup_system import ConfigBackupSystem
from src.agent_kanban_system import AgentKanbanSystem
from src.log_intelligence_system import LogIntelligenceSystem
from src.disaster_recovery_system import DisasterRecoverySystem

# Initialize all systems
ProjectManagementSystem()
ConfigBackupSystem()  
AgentKanbanSystem()
LogIntelligenceSystem()
DisasterRecoverySystem()
print('✅ All database schemas initialized')
"
```

### Testing and Monitoring
```bash
# Check sync service status
curl http://localhost:8899/api/status

# Check remote MCP server health (includes all 57+ tools)
curl http://localhost:8900/health

# Test MCP tools via Claude Code
python src/memory_server.py &
# Then use MCP tools in Claude Code

# Manual sync trigger
curl -X POST http://localhost:8899/api/trigger-sync -H "Authorization: Bearer your-api-token"

# Test Tailscale connectivity
ping ljs-macbook-pro && ping m2 && ping max

# Test project management system
curl -X POST http://localhost:8900/admin/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "test-project", "description": "Test project", "owner_agent_id": "test-agent"}'

# Test configuration backup system  
curl -X POST http://localhost:8900/admin/api/configs/backup \
  -H "Content-Type: application/json" \
  -d '{"system_id": "test-system", "config_content": "test: config"}'
```

### Common Development Tasks
```bash
# View all MCP tools available
python -c "
import sys; sys.path.append('src')
from remote_mcp_server import RemoteMCPServer
server = RemoteMCPServer()
tools = [tool for tool in dir(server) if not tool.startswith('_') and callable(getattr(server, tool))]
print(f'Available MCP Tools: {len(tools)}')
for tool in sorted(tools): print(f'  - {tool}')
"

# Check database schemas
sqlite3 data/projects.db ".schema"
sqlite3 data/config_backup.db ".schema"
sqlite3 data/kanban.db ".schema"
sqlite3 data/logs.db ".schema"
sqlite3 data/disaster_recovery.db ".schema"
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
- `update_memory`: Update existing memory's content and/or metadata (content, tags, context, category)
- `search_memories`: Full-text and semantic search with machine/project filtering
- `get_recent_memories`: Get memories within specified time window
- `get_memory_stats`: Statistics about stored memories
- `get_project_memories`: Get all memories for current project
- `get_machine_context`: Get comprehensive machine context
- `list_memory_sources`: List all machines with memory statistics
- `import_conversation`: Import full conversations as structured memories

### Memory Deletion & Lifecycle Management Tools:
- `delete_memory`: Delete memory by ID with soft delete (recoverable) or hard delete (permanent)
- `bulk_delete_memories`: Bulk delete memories based on filters with confirmation required
- `recover_deleted_memory`: Recover soft-deleted memory from recycle bin within 30 days
- `list_deleted_memories`: List memories in recycle bin that can be recovered
- `detect_duplicate_memories`: Detect potentially duplicate memories using semantic similarity
- `merge_duplicate_memories`: Merge two duplicate memories, keeping one and deleting the other
- `cleanup_expired_deletions`: Clean up expired soft deletions and apply data retention policies
- `gdpr_delete_user_data`: GDPR compliant deletion of all data for specific user (right to be forgotten)
- `gdpr_export_user_data`: GDPR compliant export of all data for specific user (data portability)

### Project Management Tools:
- `create_project`: Create new projects with comprehensive tracking, tags, metadata, and hAIveMind integration
- `list_projects`: List projects with advanced filtering by status, owner, type, and pagination support
- `switch_project_context`: Switch agent context to specific project with reason tracking and memory storage
- `project_health_check`: Multi-dimensional health analysis with recommendations and trend analytics
- `backup_project`: Full/incremental project backups with history preservation and conflict resolution
- `restore_project`: Safe project restoration with validation, conflict resolution, and rollback capabilities

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

### Configuration Management Tools:
- `create_config_snapshot`: Create configuration snapshots with drift detection and metadata tracking
- `compare_config_snapshots`: Compare configurations across systems with detailed diff analysis
- `detect_config_drift`: Intelligent drift detection with ML-powered pattern recognition
- `get_config_history`: Comprehensive configuration history with trend analysis and insights
- `create_config_alert`: Set up intelligent alerts for configuration changes with custom rules
- `get_drift_trend_analysis`: Predictive drift analysis with recommendations and risk assessment

### Agent Task Management Tools:
- `create_kanban_task`: Create intelligent tasks with auto-assignment and dependency tracking
- `assign_kanban_task`: Smart task assignment based on agent capabilities and workload
- `update_kanban_task`: Update tasks with status tracking and notification systems
- `get_kanban_task`: Retrieve detailed task information with history and analytics
- `list_kanban_tasks`: List tasks with advanced filtering and workload balancing insights
- `delete_kanban_task`: Delete tasks with dependency validation and cleanup automation
- `get_task_analytics`: Comprehensive task analytics with performance metrics and trends

### Log Intelligence & Monitoring Tools:
- `analyze_log_patterns`: ML-powered log pattern extraction using TF-IDF and clustering algorithms
- `detect_log_anomalies`: Real-time anomaly detection using Isolation Forest and statistical analysis
- `generate_debug_report`: Intelligent debug report generation with correlation analysis
- `track_error_patterns`: Error pattern tracking with trend analysis and predictive insights

### Disaster Recovery Tools:
- `initiate_failover`: Automated failover procedures with health monitoring and rollback capability
- `monitor_system_health`: Comprehensive system health monitoring with predictive failure detection
- `run_chaos_experiment`: Chaos engineering experiments with safety controls and impact analysis
- `generate_recovery_plan`: Dynamic recovery plan generation based on failure scenarios

### Automation & Playbook Tools:
- `upload_playbook`: Upload and store Ansible/Terraform/Kubernetes playbooks
- `fetch_from_confluence`: Fetch documentation from Confluence and store as knowledge
- `fetch_from_jira`: Fetch issues from Jira and store as incident/task knowledge
- `sync_external_knowledge`: Sync from all configured external sources automatically

### Teams & Vaults Management Tools:

#### Mode Management (3 tools):
- `get_mode`: Get current operating mode and context (solo/vault/team)
- `set_mode`: Switch operating mode with context validation
- `list_available_modes`: List all available teams, vaults, and modes

#### Team Management (6 tools):
- `create_team`: Create new collaborative team with owner role
- `list_teams`: List teams you belong to with membership details
- `get_team`: Get team details including members and activity
- `add_team_member`: Add member with specific role (admin/member/readonly/guest)
- `remove_team_member`: Remove member from team (requires admin role)
- `get_team_activity`: Get recent team activity log

#### Vault Management (8 tools):
- `create_vault`: Create encrypted vault (personal/team/project/shared)
- `list_vaults`: List all vaults you have access to
- `store_in_vault`: Store encrypted secret with metadata (API keys, passwords, etc.)
- `retrieve_from_vault`: Retrieve and decrypt secret (requires audit reason)
- `list_vault_secrets`: List secret keys without values (metadata only)
- `delete_vault_secret`: Delete secret from vault (logged in audit trail)
- `share_vault`: Grant vault access to user or team (read/write/admin)
- `vault_audit_log`: View complete audit trail for vault operations

### Confidence System Tools (8 tools):
- `get_memory_confidence`: Get detailed confidence score breakdown for a memory
- `verify_memory`: Explicitly verify memory as accurate, outdated, or incorrect
- `report_memory_usage`: Report outcome when using memory for an action
- `search_high_confidence`: Search for memories above confidence threshold
- `flag_outdated_memories`: Find memories needing verification due to age
- `resolve_contradiction`: Manually resolve detected contradiction
- `vote_on_fact`: Vote on whether a memory/fact is accurate
- `get_agent_credibility`: Get credibility score for an agent in a category

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

### Project Management & Context Switching:
```bash
# Create a new project with comprehensive tracking
create_project name="eWitness Search Optimization" description="Optimize Elasticsearch queries for better performance" owner_agent_id="elastic-specialist" project_type="optimization" priority="high" tags="elasticsearch,performance,search"

# List projects with filtering
list_projects status_filter="active" project_type_filter="optimization" limit=10

# Switch agent context to specific project
switch_project_context project_id="proj_abc123" agent_id="lance-dev-agent" reason="Starting search optimization work"

# Run comprehensive health check on projects
project_health_check project_id="proj_abc123"

# Create project backup
backup_project project_id="proj_abc123" backup_type="full" include_history=true

# Restore project from backup
restore_project backup_id="backup_xyz789" restore_mode="safe"
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

### Configuration Management:
```bash
# Create configuration snapshot
create_config_snapshot system_id="elastic1" config_type="elasticsearch" config_content="<yaml_content>" file_path="/etc/elasticsearch/elasticsearch.yml"

# Compare configurations
compare_config_snapshots system_id="elastic1" snapshot_id_1="snap_123" snapshot_id_2="snap_456"

# Detect configuration drift
detect_config_drift system_id="elastic1" threshold=0.8

# Get comprehensive drift analysis
get_drift_trend_analysis system_id="elastic1" days_back=7
```

### Agent Task Management:
```bash
# Create intelligent task with auto-assignment
create_kanban_task title="Optimize Elasticsearch queries" description="Improve search performance" priority="high" required_capabilities=["elasticsearch_ops"]

# Assign task to best available agent
assign_kanban_task task_id="task_123" auto_assign=true

# Update task status
update_kanban_task task_id="task_123" status="in_progress" progress=25

# Get task analytics
get_task_analytics days=30
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

### Teams & Vaults Management:
```bash
# === Mode Management ===

# Get current operating mode
get_mode

# Switch to solo mode (private work)
set_mode mode="solo"

# Switch to team mode (collaborative work)
set_mode mode="team" context_id="team_engineering_001"

# Switch to vault mode (access secrets)
set_mode mode="vault" context_id="vault_prod_secrets"

# List available modes and contexts
list_available_modes

# === Team Collaboration ===

# Create a new team
create_team name="Engineering Team" description="Main engineering team for product development"

# List your teams
list_teams

# Get detailed team information
get_team team_id="team_engineering_001" include_members=true include_activity=true

# Add a team member
add_team_member team_id="team_engineering_001" user_id="bob@example.com" role="member"

# Add an admin
add_team_member team_id="team_engineering_001" user_id="alice@example.com" role="admin"

# Remove a team member
remove_team_member team_id="team_engineering_001" user_id="bob@example.com"

# Get team activity
get_team_activity team_id="team_engineering_001" hours=24 limit=50

# === Vault Secret Management ===

# Create a personal vault
create_vault name="Personal Secrets" vault_type="personal"

# Create a team vault
create_vault name="Production Secrets" vault_type="team" team_id="team_engineering_001"

# List your vaults
list_vaults

# Store a secret (API key, password, etc.)
store_in_vault vault_id="vault_abc123" key="stripe_api_key" value="sk_live_xxxxx" metadata={"service": "stripe", "environment": "production"}

# Store database password
store_in_vault vault_id="vault_abc123" key="db_password" value="super_secret_password" metadata={"database": "postgresql", "host": "db.example.com"}

# Retrieve a secret (requires audit reason for compliance)
retrieve_from_vault vault_id="vault_abc123" key="stripe_api_key" audit_reason="Deploying payment integration"

# List secrets in vault (shows keys only, not values)
list_vault_secrets vault_id="vault_abc123"

# Delete a secret
delete_vault_secret vault_id="vault_abc123" key="old_api_key"

# Share vault with another user (read access)
share_vault vault_id="vault_abc123" share_with="bob@example.com" share_type="user" access_level="read"

# Share vault with team (write access)
share_vault vault_id="vault_abc123" share_with="team_engineering_001" share_type="team" access_level="write"

# Grant temporary access (expires in 24 hours)
share_vault vault_id="vault_abc123" share_with="contractor@example.com" share_type="user" access_level="read" expires_at="2025-12-21T10:00:00Z"

# View audit log (security compliance)
vault_audit_log vault_id="vault_abc123" hours=168 limit=100

# === Complete Workflow Example ===

# 1. Create team for project
create_team name="Payment Integration" description="Team handling payment system integration"

# 2. Create team vault for secrets
create_vault name="Payment Secrets" vault_type="team" team_id="team_payment_001"

# 3. Add team members
add_team_member team_id="team_payment_001" user_id="alice@dev.com" role="admin"
add_team_member team_id="team_payment_001" user_id="bob@dev.com" role="member"

# 4. Switch to team mode
set_mode mode="team" context_id="team_payment_001"

# 5. Store secrets in team vault
store_in_vault vault_id="vault_team_payment" key="stripe_secret" value="sk_live_xxxxx"
store_in_vault vault_id="vault_team_payment" key="webhook_secret" value="whsec_xxxxx"

# 6. Team members can now access secrets
# (automatically logged in audit trail)
retrieve_from_vault vault_id="vault_team_payment" key="stripe_secret" audit_reason="Setting up payment processing"

# 7. Review security audit trail
vault_audit_log vault_id="vault_team_payment" hours=168
```

### Memory Update & Modification:
```bash
# Update memory content
update_memory memory_id="abc123" content="Updated content with corrections"

# Update memory tags and context
update_memory memory_id="abc123" tags=["fixed", "verified", "production"] context="Corrected information"

# Update memory category
update_memory memory_id="abc123" category="incidents"

# Update multiple fields at once
update_memory memory_id="abc123" content="New content" tags=["updated"] context="Fixed typo" category="infrastructure"

# Update only metadata (content unchanged)
update_memory memory_id="abc123" metadata={"priority": "high", "verified": true}
```

### Memory Deletion & Lifecycle Management:
```bash
# Soft delete a memory (recoverable for 30 days)
delete_memory memory_id="abc123" hard_delete=false reason="No longer needed"

# Hard delete a memory permanently
delete_memory memory_id="def456" hard_delete=true reason="Contains sensitive data"

# List deleted memories in recycle bin
list_deleted_memories limit=20

# Recover a soft-deleted memory
recover_deleted_memory memory_id="abc123"

# Bulk delete old memories (with required confirmation)
bulk_delete_memories category="incidents" date_to="2024-01-01" hard_delete=false confirm=true reason="Archive old incidents"

# Detect duplicate memories
detect_duplicate_memories threshold=0.9

# Merge duplicate memories
merge_duplicate_memories memory_id_1="abc123" memory_id_2="def456" keep_memory="newest"

# Clean up expired deletions and apply retention policies
cleanup_expired_deletions

# GDPR right to be forgotten (with required confirmation)
gdpr_delete_user_data user_id="john.doe@example.com" confirm=true

# GDPR data export (data portability)
gdpr_export_user_data user_id="john.doe@example.com" format="json"
```

### Confidence System Usage:
```bash
# === Get Confidence Score ===

# Get detailed confidence breakdown
get_memory_confidence memory_id="mem_abc123"

# Returns:
# - final_score: 0.87
# - level: "high"
# - factors: {freshness: 0.95, source: 0.90, verification: 0.85, ...}
# - description: "Reliable information - likely accurate"

# === Verify Information ===

# Verify memory is still accurate
verify_memory memory_id="mem_abc123" verification_type="confirmed" notes="Tested connection, works correctly"

# Mark old info as still valid (resets freshness clock)
verify_memory memory_id="mem_old123" verification_type="still_valid"

# Mark outdated information
verify_memory memory_id="mem_bad123" verification_type="outdated" notes="Port changed to 6380"

# === Track Usage Outcomes ===

# Report successful use
report_memory_usage memory_id="mem_abc123" action="Connected to Redis on port 6379" outcome="success"

# Report failure (lowers confidence)
report_memory_usage memory_id="mem_bad456" action="Tried to connect" outcome="failure" details={"error": "Connection refused"}

# === Search by Confidence ===

# Find only high-confidence info for critical operations
search_high_confidence query="Redis configuration" min_confidence=0.75 limit=10

# Get all verified facts about Elasticsearch
search_high_confidence query="Elasticsearch cluster" min_confidence=0.90 category="infrastructure"

# === Maintain Information Quality ===

# Find outdated infrastructure info
flag_outdated_memories category="infrastructure" freshness_threshold=0.3

# Find all stale security information (20-day half-life)
flag_outdated_memories category="security"

# === Resolve Conflicts ===

# Resolve contradiction - newer wins
resolve_contradiction \
  contradiction_id="conflict_xyz789" \
  winner_memory_id="mem_new123" \
  strategy="temporal" \
  reason="Newer information from last week supersedes 3-month-old data"

# Resolve by source trust
resolve_contradiction \
  contradiction_id="conflict_abc456" \
  winner_memory_id="mem_expert123" \
  strategy="source_trust" \
  reason="Information from elasticsearch specialist more reliable"

# === Consensus Voting ===

# Vote that information is correct
vote_on_fact \
  memory_id="mem_abc123" \
  vote="agree" \
  confidence=0.9 \
  reasoning="I just verified this configuration is correct"

# Disagree with information
vote_on_fact \
  memory_id="mem_wrong456" \
  vote="disagree" \
  confidence=0.8 \
  reasoning="Port is actually 6380, not 6379"

# === Check Agent Trust ===

# Get agent credibility in specific domain
get_agent_credibility agent_id="elasticsearch-specialist" category="infrastructure"

# Returns:
# - credibility_score: 0.92
# - verified_correct: 47
# - verified_incorrect: 3
# - contribution_count: 50

# === Complete Confidence Workflow ===

# 1. Store new memory with metadata
store_memory \
  content="Redis cluster has 6 nodes on ports 6379-6384" \
  category="infrastructure" \
  source_type="verified_fact" \
  tags=["redis", "cluster", "production"]

# 2. Multiple agents verify
verify_memory memory_id="mem_new789" verification_type="confirmed" notes="Agent A: Confirmed via redis-cli"
verify_memory memory_id="mem_new789" verification_type="confirmed" notes="Agent B: Verified with cluster info"
verify_memory memory_id="mem_new789" verification_type="confirmed" notes="Agent C: Checked ansible inventory"

# 3. Agents vote consensus
vote_on_fact memory_id="mem_new789" vote="agree" confidence=1.0
vote_on_fact memory_id="mem_new789" vote="agree" confidence=0.95
vote_on_fact memory_id="mem_new789" vote="agree" confidence=0.90

# 4. Track successful usage
report_memory_usage memory_id="mem_new789" action="Connected to all cluster nodes" outcome="success"
report_memory_usage memory_id="mem_new789" action="Ran cluster health check" outcome="success"

# 5. Check final confidence
get_memory_confidence memory_id="mem_new789"
# Result: Very high confidence (0.92) - Safe to use for critical operations

# === Risk-Based Decision Making ===

# Low risk: Just viewing logs (min_confidence: 0.40)
search_high_confidence query="recent errors" min_confidence=0.40

# Medium risk: Restarting service (min_confidence: 0.60)
search_high_confidence query="restart procedure" min_confidence=0.60

# High risk: Changing production config (min_confidence: 0.75)
search_high_confidence query="nginx configuration" min_confidence=0.75

# Critical risk: Deleting data (min_confidence: 0.90)
search_high_confidence query="database cleanup procedure" min_confidence=0.90
```

## Troubleshooting

- MCP integration requires `enableAllProjectMcpServers: true` in Claude Code settings
- Redis connection issues: Check Redis service and config.json settings
- Machine discovery requires Tailscale running and correct hostnames in config
- Sync failures often relate to API token configuration or port 8899 accessibility
- hAIveMind agent registration requires Redis for coordination features to work
- ClaudeOps hAIveMind features require the updated config.json with claudeops section
- if you get an mcp failure for haivemind, we need to stop and fix it.
- also for each ticket can you add haivemind awareness so it can learn across the system when necessary fro this project:
- then also put these in sequence with storyname -> ticket, and maybe order they should be done in. if they can be done in parallel add 1a, 1b to them or some kind of lettering .
- all these tickets that can be done in parallel, do in parallel then update tickets when done. put in progress when doing.
- when using xargs kill try not to kill claude code session