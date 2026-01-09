# CLAUDE.md - hAIveMind DevOps Memory System (Compact)

Multi-agent DevOps memory MCP server. Agents share knowledge, delegate tasks, coordinate via ChromaDB + Redis.

## Quick Reference

**Ports**: 8899 (sync), 8900 (MCP) | **Config**: config/config.json | **Data**: /data/chroma/

**Start**: `python src/memory_server.py` (stdio) | `python src/remote_mcp_server.py` (HTTP/SSE)

## Operating Modes
- **Solo** (default): Private work, no sharing
- **Team**: Collaborative workspace with roles (owner/admin/member/readonly/guest)
- **Vault**: Encrypted secrets with audit trail

## Memory Categories
Core: `project`, `conversation`, `agent`, `global`
DevOps: `infrastructure`, `incidents`, `deployments`, `monitoring`, `runbooks`, `security`

## MCP Tools (57+)

**Memory**: store_memory, retrieve_memory, update_memory, search_memories, get_recent_memories, delete_memory, bulk_delete_memories, recover_deleted_memory, detect_duplicate_memories, merge_duplicate_memories

**Projects**: create_project, list_projects, switch_project_context, project_health_check, backup_project, restore_project

**Agents**: register_agent, get_agent_roster, delegate_task, query_agent_knowledge, broadcast_discovery

**Infrastructure**: track_infrastructure_state, record_incident, generate_runbook, sync_ssh_config, sync_infrastructure_config

**Config Mgmt**: create_config_snapshot, compare_config_snapshots, detect_config_drift, get_config_history, create_config_alert, get_drift_trend_analysis

**Kanban**: create_kanban_task, assign_kanban_task, update_kanban_task, get_kanban_task, list_kanban_tasks, delete_kanban_task, get_task_analytics

**Logs**: analyze_log_patterns, detect_log_anomalies, generate_debug_report, track_error_patterns

**DR**: initiate_failover, monitor_system_health, run_chaos_experiment, generate_recovery_plan

**Teams**: get_mode, set_mode, list_available_modes, create_team, list_teams, get_team, add_team_member, remove_team_member, get_team_activity

**Vaults**: create_vault, list_vaults, store_in_vault, retrieve_from_vault, list_vault_secrets, delete_vault_secret, share_vault, vault_audit_log

**External**: upload_playbook, fetch_from_confluence, fetch_from_jira, sync_external_knowledge

**GDPR**: gdpr_delete_user_data, gdpr_export_user_data

## Machine Groups
- **Orchestrators** (lance-dev): coordination, deployment
- **Elasticsearch** (elastic1-5): search_tuning, cluster_management
- **Databases** (mysql, mongodb, kafka): backup_restore, query_optimization
- **Scrapers** (proxy0-9): data_collection, proxy_management

## Troubleshooting
- MCP fails: Check Redis running, config.json valid
- Sync fails: Verify Tailscale, port 8899 accessible
- Use `/help <tool>` for detailed examples

**Full docs**: Run `/hv-help` or see examples/command-sequences/
