---
description: Synchronize hAIveMind commands, configurations, and agent state with collective
allowed-tools: ["mcp__haivemind__*", "Write", "Read", "Edit"]
argument-hint: [force|status|clean] [--verbose] [--commands] [--config] [--memory]
---

# hv-sync - Collective Synchronization

## Purpose
Synchronize local hAIveMind installation with the collective, ensuring commands, configurations, and agent state are up-to-date across all nodes.

## When to Use
- **Regular Updates**: Keep commands and configs current with collective
- **After Network Issues**: Resync after connectivity problems
- **New Agent Setup**: Initial sync for new agent registration
- **Troubleshooting**: Clean sync to resolve configuration issues
- **Manual Updates**: Force sync when automatic updates fail
- **Status Checking**: Verify current sync state and version info

## Syntax
```
hv-sync [operation] [options]
```

## Parameters
- **operation** (optional): Sync operation type
  - `force`: Force full resync regardless of current state
  - `status`: Show sync status without making changes
  - `clean`: Remove local state and perform fresh sync
  - (no operation): Smart sync based on current state
- **options** (optional):
  - `--verbose`: Show detailed progress during sync
  - `--commands`: Sync only command files
  - `--config`: Sync only configuration files
  - `--memory`: Sync only memory/agent state
  - `--dry-run`: Show what would be synced without making changes

## Real-World Examples

### Regular Update Check
```
hv-sync
```
**Result**: Smart sync that only updates changed components

### Force Complete Resync
```
hv-sync force --verbose
```
**Result**: Downloads all commands and configs regardless of current versions

### Check Sync Status Only
```
hv-sync status
```
**Result**: Shows version comparisons and sync timestamps without making changes

### Clean Slate Resync
```
hv-sync clean
```
**Result**: Removes local state and performs complete fresh installation

### Commands-Only Update
```
hv-sync --commands --verbose
```
**Result**: Updates only hv-* command files with detailed progress

## Expected Output

### Smart Sync (Default)
```
🔄 hAIveMind Synchronization - 2025-01-24 15:45:00

🔍 Checking collective for updates...
✓ Connected to collective (lance-dev orchestrator)
✓ Local version: 2025-01-20, Collective version: 2025-01-24
✓ 3 updates available

📦 Syncing Commands:
✓ hv-broadcast.md - Updated (v1.2.3 → v1.2.4)
✓ hv-query.md - Updated (v1.0.5 → v1.0.6) 
⚪ hv-delegate.md - Current (v1.1.0)
⚪ hv-status.md - Current (v1.1.2)
✓ recall.md - Updated (v2.0.1 → v2.0.2)
⚪ remember.md - Current (v2.0.1)
⚪ hv-sync.md - Current (v1.0.8)

🔧 Agent Configuration:
✓ Agent registration refreshed
✓ Capabilities updated: +monitoring, +incident_response
✓ Network mesh updated (2 new nodes discovered)

📝 CLAUDE.md Integration:
⚪ No updates needed (current version)

🎉 Sync Complete!
   ↳ 3 commands updated
   ↳ Agent capabilities refreshed
   ↳ Network mesh updated
   ↳ Next automatic sync: 2025-01-24 21:45:00
```

### Status Check Output
```
📊 hAIveMind Sync Status - 2025-01-24 15:45:00

🏷️  VERSIONS:
   ↳ Local Version: 2025-01-20 14:30:00
   ↳ Collective Version: 2025-01-24 12:15:00
   ↳ Status: 3 updates available
   ↳ Last Sync: 2025-01-23 09:20:00 (1 day ago)

📦 COMMAND STATUS:
┌─────────────────┬─────────────┬─────────────┬──────────────────┐
│ Command         │ Local       │ Collective  │ Status           │
├─────────────────┼─────────────┼─────────────┼──────────────────┤
│ hv-broadcast    │ v1.2.3      │ v1.2.4      │ ⬆️ Update Available │
│ hv-delegate     │ v1.1.0      │ v1.1.0      │ ✅ Current        │
│ hv-install      │ v1.0.3      │ v1.0.3      │ ✅ Current        │
│ hv-query        │ v1.0.5      │ v1.0.6      │ ⬆️ Update Available │
│ hv-status       │ v1.1.2      │ v1.1.2      │ ✅ Current        │
│ hv-sync         │ v1.0.8      │ v1.0.8      │ ✅ Current        │
│ recall          │ v2.0.1      │ v2.0.2      │ ⬆️ Update Available │
│ remember        │ v2.0.1      │ v2.0.1      │ ✅ Current        │
└─────────────────┴─────────────┴─────────────┴──────────────────┘

🤖 AGENT STATUS:
   ↳ Registration: Active (lance-dev-development-agent)
   ↳ Capabilities: development, infrastructure_management, coordination
   ↳ Network Nodes: 12 connected, 2 offline
   ↳ Last Heartbeat: 45 seconds ago

⚡ SYNC SCHEDULE:
   ↳ Auto-sync: Enabled (every 6 hours)
   ↳ Next Check: 2025-01-24 21:45:00
   ↳ Force Sync Available: Yes
```

## Sync Operations Deep Dive

### Smart Sync (Default)
- Compares local versions with collective versions
- Only downloads changed files
- Updates agent registration if needed
- Preserves local customizations where possible
- Fast and network-efficient

### Force Sync
- Downloads all commands regardless of version
- Completely refreshes agent registration
- Overwrites local customizations
- Use when experiencing unexplained issues
- Longer operation but ensures consistency

### Clean Sync
- Removes all local hAIveMind state
- Performs fresh installation from scratch
- Reregisters agent with new identity if needed
- Use as last resort for corrupted installations
- Equivalent to uninstall + install

## Performance Considerations
- **Smart Sync**: ~5-15 seconds, minimal network usage
- **Force Sync**: ~30-60 seconds, full download
- **Clean Sync**: ~45-90 seconds, complete reinstall
- **Status Check**: ~2-5 seconds, minimal data transfer
- **Network Impact**: Syncs use efficient delta compression

## Error Scenarios and Solutions

### Network Connectivity Issues
```
❌ Error: Cannot connect to collective orchestrator
💡 Troubleshooting:
   1. Check Tailscale: tailscale status
   2. Verify orchestrator: ping lance-dev
   3. Check MCP server: curl http://lance-dev:8900/health
   4. Retry with: hv-sync force
```

### Version Conflicts
```
⚠️  Warning: Local modifications detected in hv-broadcast.md
💡 Options:
   1. Backup and allow overwrite: hv-sync force
   2. Skip this file: choose 'skip' when prompted
   3. Manual merge: review differences before sync
```

### Agent Registration Issues
```
❌ Error: Agent registration failed (duplicate ID)
💡 Resolution:
   1. Clean registration: hv-sync clean
   2. Check for duplicate agents: hv-status --agents
   3. Manual cleanup may be required
```

## Best Practices
- **Regular Sync**: Run weekly or after system changes
- **Before Important Work**: Sync before major tasks
- **After Network Issues**: Sync after connectivity problems
- **Status Monitoring**: Check status before manual sync
- **Backup Customizations**: Save custom changes before force sync
- **Scheduled Sync**: Enable automatic sync for convenience

## Related Commands
- **Before syncing**: Use `hv-status` to check collective health
- **After syncing**: Use `hv-install status` to verify installation
- **For issues**: Use `hv-query` to find sync-related solutions
- **Share updates**: Use `hv-broadcast` to inform others of sync results

---

**Sync Operation**: $ARGUMENTS

This will synchronize your local hAIveMind installation with the collective, ensuring you have the latest commands, configurations, and agent state for optimal collaborative intelligence.