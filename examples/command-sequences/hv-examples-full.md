# hAIveMind Complete Examples Reference

Load this file on-demand with `/help <topic>` when you need detailed examples.

## Memory Operations

```bash
# Store with machine tracking
store_memory content="..." category="infrastructure" tags=["elastic","prod"]

# Search semantically
search_memories query="elasticsearch optimization" category="infrastructure" limit=10

# Update memory
update_memory memory_id="abc123" content="Updated" tags=["fixed"]

# Delete (soft=recoverable 30 days)
delete_memory memory_id="abc123" hard_delete=false reason="No longer needed"

# Recover deleted
recover_deleted_memory memory_id="abc123"

# Find duplicates
detect_duplicate_memories threshold=0.9
merge_duplicate_memories memory_id_1="abc123" memory_id_2="def456" keep_memory="newest"
```

## Project Management

```bash
# Create project
create_project name="Search Optimization" description="Improve ES queries" owner_agent_id="elastic-agent" project_type="optimization" priority="high" tags="elasticsearch,performance"

# List with filters
list_projects status_filter="active" project_type_filter="optimization" limit=10

# Switch context
switch_project_context project_id="proj_abc123" agent_id="agent-1" reason="Starting work"

# Health check
project_health_check project_id="proj_abc123"

# Backup/restore
backup_project project_id="proj_abc123" backup_type="full" include_history=true
restore_project backup_id="backup_xyz789" restore_mode="safe"
```

## Agent Coordination

```bash
# Register agent
register_agent role="hive_mind" description="Primary orchestrator"

# View roster
get_agent_roster

# Delegate task
delegate_task task_description="Optimize search on elastic1" required_capabilities=["elasticsearch_ops"]

# Query knowledge
query_agent_knowledge agent_id="elastic1-specialist" query="memory optimization"

# Broadcast discovery
broadcast_discovery message="Found memory leak" category="infrastructure" severity="warning"
```

## Infrastructure

```bash
# Track state
track_infrastructure_state machine_id="elastic1" state_type="service_status" state_data={"elasticsearch":"running","cpu":"65%"}

# Record incident
record_incident title="ES cluster degraded" description="High CPU" severity="high" affected_systems=["elastic1"]

# Sync SSH config
sync_ssh_config config_content="<content>" target_machines=["elastic1","elastic2"]

# Generate runbook
generate_runbook title="ES Restart" procedure="1. Stop 2. Clear cache 3. Start" system="elasticsearch"
```

## Config Management

```bash
# Snapshot
create_config_snapshot system_id="elastic1" config_type="elasticsearch" config_content="<yaml>" file_path="/etc/elasticsearch/elasticsearch.yml"

# Compare
compare_config_snapshots system_id="elastic1" snapshot_id_1="snap_123" snapshot_id_2="snap_456"

# Drift detection
detect_config_drift system_id="elastic1" threshold=0.8
get_drift_trend_analysis system_id="elastic1" days_back=7
```

## Kanban Tasks

```bash
# Create task
create_kanban_task title="Optimize queries" description="Improve performance" priority="high" required_capabilities=["elasticsearch_ops"]

# Auto-assign
assign_kanban_task task_id="task_123" auto_assign=true

# Update status
update_kanban_task task_id="task_123" status="in_progress" progress=25

# Analytics
get_task_analytics days=30
```

## Teams & Vaults

```bash
# Mode management
get_mode
set_mode mode="team" context_id="team_engineering_001"
list_available_modes

# Team ops
create_team name="Engineering" description="Main team"
add_team_member team_id="team_001" user_id="bob@example.com" role="member"
get_team_activity team_id="team_001" hours=24

# Vault ops
create_vault name="Prod Secrets" vault_type="team" team_id="team_001"
store_in_vault vault_id="vault_abc" key="api_key" value="sk_xxx" metadata={"service":"stripe"}
retrieve_from_vault vault_id="vault_abc" key="api_key" audit_reason="Deploying"
share_vault vault_id="vault_abc" share_with="team_002" share_type="team" access_level="read"
vault_audit_log vault_id="vault_abc" hours=168
```

## GDPR Compliance

```bash
# Right to be forgotten
gdpr_delete_user_data user_id="john@example.com" confirm=true

# Data portability
gdpr_export_user_data user_id="john@example.com" format="json"
```

## External Integrations

```bash
# Playbooks
upload_playbook playbook_name="Deploy Nginx" playbook_content="<yaml>" playbook_type="ansible" target_systems=["web-servers"]

# Confluence/Jira
fetch_from_confluence space_key="DEVOPS" page_title="Deployment Guide"
fetch_from_jira project_key="INFRA" issue_types=["Bug","Incident"] limit=25

# Sync all
sync_external_knowledge sources=["confluence","jira"]
```
