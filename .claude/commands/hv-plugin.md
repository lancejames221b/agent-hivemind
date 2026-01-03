---
description: Manage hAIveMind plugins - install, list, sync, create, and distribute Claude Code plugins
allowed-tools: ["mcp__haivemind__*", "Write", "Read", "Edit", "Bash", "Glob"]
argument-hint: [list|install|uninstall|sync|create|publish|search|status] [plugin-name] [--force] [--group=<group>]
---

# hv-plugin - Claude Plugin Management

## Purpose
Manage Claude Code plugins across the hAIveMind collective. Plugins bundle commands, agents, skills, hooks, and MCP servers for easy distribution and synchronization.

## When to Use
- **Plugin Discovery**: Find plugins for specific capabilities
- **Plugin Installation**: Install plugins from the collective registry
- **Plugin Distribution**: Share plugins across hAIveMind machines
- **Plugin Creation**: Create new plugins from existing components
- **Plugin Sync**: Keep plugins synchronized across the collective
- **Plugin Management**: Update, uninstall, or check plugin status

## Syntax
```
hv-plugin <action> [plugin-name] [options]
```

## Actions

### list - List Available Plugins
```
hv-plugin list                     # List all published plugins
hv-plugin list --installed         # Show only installed plugins
hv-plugin list --group=elasticsearch  # Filter by machine group
```

### install - Install a Plugin
```
hv-plugin install <plugin-id>      # Install specific plugin
hv-plugin install <plugin-id> --force  # Reinstall even if present
```

### uninstall - Remove a Plugin
```
hv-plugin uninstall <plugin-id>    # Uninstall plugin
hv-plugin uninstall <plugin-id> --keep-data  # Keep configuration
```

### sync - Synchronize Plugins
```
hv-plugin sync                     # Check for and sync new plugins
hv-plugin sync --auto-install      # Auto-install compatible plugins
```

### create - Create New Plugin
```
hv-plugin create <name>            # Create plugin from template
hv-plugin create <name> --from-commands  # Bundle existing commands
```

### publish - Publish Plugin to Collective
```
hv-plugin publish <plugin-id>      # Publish registered plugin
hv-plugin publish <plugin-id> --groups=orchestrators,elasticsearch
```

### search - Search for Plugins
```
hv-plugin search "kubernetes"      # Search by keyword
hv-plugin search --capability=deployment  # Search by capability
```

### status - Check Plugin Status
```
hv-plugin status                   # Show installation status
hv-plugin status <plugin-id>       # Show specific plugin details
```

## Real-World Examples

### Find and Install Elasticsearch Plugin
```
hv-plugin search "elasticsearch"
hv-plugin install plugin_elasticsearch-ops_1_0_0
```
**Result**: Installs elasticsearch-ops plugin with specialized commands, agents, and skills for ES cluster management.

### Sync All Plugins Across Collective
```
hv-plugin sync --auto-install
```
**Result**: Discovers plugins compatible with this machine's groups and auto-installs them.

### Create DevOps Plugin from Existing Commands
```
hv-plugin create devops-essentials --from-commands
```
**Result**: Bundles your existing .claude/commands/ into a distributable plugin package.

### Distribute Plugin to Team Machines
```
hv-plugin publish plugin_my-plugin_1_0_0 --groups=dev_environments
```
**Result**: Makes plugin available to all machines in dev_environments group.

### Check What's Installed
```
hv-plugin status
```
**Result**: Shows all installed plugins, their versions, and available updates.

## Expected Output

### Plugin List
```
🔌 hAIveMind Plugin Registry - 2025-01-24

PUBLISHED PLUGINS:
┌────────────────────────────┬─────────┬────────────────────────────────┬───────────────────┐
│ Name                       │ Version │ Description                    │ Machine Groups    │
├────────────────────────────┼─────────┼────────────────────────────────┼───────────────────┤
│ haivemind-core            │ 1.0.0   │ Core hAIveMind commands        │ all               │
│ elasticsearch-ops         │ 1.2.0   │ ES cluster management          │ elasticsearch     │
│ devops-essentials         │ 1.1.0   │ Common DevOps workflows        │ orchestrators     │
│ incident-response         │ 1.0.0   │ Incident management suite      │ monitoring        │
│ security-auditor          │ 1.0.0   │ Security scanning & analysis   │ all               │
└────────────────────────────┴─────────┴────────────────────────────────┴───────────────────┘

INSTALLED ON THIS MACHINE: 3
- haivemind-core (v1.0.0) ✓ current
- devops-essentials (v1.1.0) ✓ current
- security-auditor (v1.0.0) ✓ current

UPDATES AVAILABLE: 0
```

### Plugin Installation
```
🔌 Installing Plugin: elasticsearch-ops v1.2.0

📦 Plugin Contents:
   Commands: 5 files
   Agents: 2 files
   Skills: 3 files
   Hooks: 1 file

📁 Installing to: ~/.claude/plugins/elasticsearch-ops/

✓ Commands installed:
  - es-health.md → ~/.claude/commands/elasticsearch-ops_es-health.md
  - es-reindex.md → ~/.claude/commands/elasticsearch-ops_es-reindex.md
  - es-snapshot.md → ~/.claude/commands/elasticsearch-ops_es-snapshot.md
  - es-optimize.md → ~/.claude/commands/elasticsearch-ops_es-optimize.md
  - es-diagnostics.md → ~/.claude/commands/elasticsearch-ops_es-diagnostics.md

✓ Agents installed:
  - es-specialist.md → ~/.claude/agents/elasticsearch-ops_es-specialist.md
  - es-troubleshooter.md → ~/.claude/agents/elasticsearch-ops_es-troubleshooter.md

✓ Skills installed:
  - elasticsearch-expertise/ → ~/.claude/skills/elasticsearch-ops_elasticsearch-expertise/

✓ Hooks merged into hooks.json

🎉 Plugin installed successfully!
   Use /es-health to check cluster status
   Agent 'es-specialist' now available for delegation
```

### Plugin Status
```
📊 hAIveMind Plugin Status - lance-dev

MACHINE INFO:
  Machine ID: lance-dev
  Groups: orchestrators, personal
  Total Installed: 4 plugins

INSTALLED PLUGINS:
┌───────────────────────┬───────────────┬──────────┬───────────────────┬─────────────────┐
│ Plugin                │ Version       │ Status   │ Install Path      │ Last Updated    │
├───────────────────────┼───────────────┼──────────┼───────────────────┼─────────────────┤
│ haivemind-core       │ 1.0.0         │ current  │ ~/.claude/plugins │ 2025-01-24      │
│ devops-essentials    │ 1.1.0         │ current  │ ~/.claude/plugins │ 2025-01-23      │
│ elasticsearch-ops    │ 1.2.0         │ current  │ ~/.claude/plugins │ 2025-01-24      │
│ security-auditor     │ 1.0.0 → 1.0.1 │ update   │ ~/.claude/plugins │ 2025-01-20      │
└───────────────────────┴───────────────┴──────────┴───────────────────┴─────────────────┘

UPDATES AVAILABLE: 1
  - security-auditor: 1.0.0 → 1.0.1

COMPATIBLE PLUGINS NOT INSTALLED: 2
  - incident-response (monitoring group)
  - kubernetes-ops (orchestrators group)
```

### Plugin Sync
```
🔄 hAIveMind Plugin Sync - 2025-01-24

SYNC STATUS:
  Machine: lance-dev
  Groups: orchestrators, personal
  Last Sync: 2025-01-24 10:30:00

CHECKING REGISTRY...
  ✓ Connected to collective registry
  ✓ 12 plugins available

COMPATIBLE PLUGINS:
  ✓ haivemind-core (installed, current)
  ✓ devops-essentials (installed, current)
  ⬆ security-auditor (update available: 1.0.0 → 1.0.1)
  ➕ kubernetes-ops (new, compatible)
  ➕ terraform-integration (new, compatible)

SYNC ACTIONS:
  - Updated: 1 plugin
  - Auto-installed: 2 plugins (--auto-install enabled)
  - Skipped: 0 plugins

🎉 Sync complete! 3 plugins updated/installed.
```

## Plugin Structure

### Standard Plugin Layout
```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # Required manifest
├── commands/                 # Slash commands
│   ├── my-command.md
│   └── another-command.md
├── agents/                   # Subagent definitions
│   └── specialist-agent.md
├── skills/                   # AI skills
│   └── my-skill/
│       └── SKILL.md
├── hooks/
│   └── hooks.json            # Event handlers
├── .mcp.json                 # MCP server config (optional)
└── README.md
```

### Plugin Manifest (plugin.json)
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "My awesome plugin",
  "author": {
    "name": "Your Name",
    "organization": "Your Org"
  },
  "haivemind": {
    "machine_groups": ["orchestrators", "dev_environments"],
    "required_capabilities": ["deployment"],
    "min_haivemind_version": "1.0.0"
  },
  "components": {
    "commands": "./commands/",
    "agents": "./agents/",
    "skills": "./skills/",
    "hooks": "./hooks/hooks.json"
  }
}
```

## Plugin Distribution Flow

### Create → Register → Publish → Install
```
1. Create plugin directory with manifest
2. Register: hv-plugin register ./my-plugin
3. Publish: hv-plugin publish plugin_my-plugin_1_0_0
4. Other machines: hv-plugin sync --auto-install
```

### Machine Group Targeting
Plugins specify compatible machine groups in manifest:
- `orchestrators`: Primary coordination machines
- `elasticsearch`: ES cluster nodes
- `databases`: Database servers
- `scrapers`: Data collection machines
- `dev_environments`: Developer workstations
- `monitoring`: Monitoring infrastructure
- `personal`: Personal devices

## Best Practices

### Plugin Naming
- Use kebab-case: `my-plugin-name`
- Be descriptive: `elasticsearch-cluster-ops`
- Version semantically: `1.0.0`, `1.1.0`, `2.0.0`

### Plugin Scope
- Keep plugins focused on specific capabilities
- Avoid monolithic "everything" plugins
- Create specialized plugins for machine groups

### Distribution Strategy
- Test locally before publishing
- Use machine groups for targeted distribution
- Version updates properly (don't overwrite)

### Security Considerations
- Review plugin contents before installing
- Plugins execute with Claude Code permissions
- Untrusted plugins can access filesystem

## Error Scenarios

### Plugin Not Found
```
❌ Error: Plugin not found: plugin_nonexistent_1_0_0
💡 Use 'hv-plugin search' to find available plugins
```

### Installation Failed
```
❌ Error: Failed to install plugin
→ Check plugin exists and is published
→ Verify network connectivity
→ Check disk space and permissions
→ Use --force to retry
```

### Sync Connectivity Issues
```
⚠️ Warning: Cannot connect to plugin registry
→ Check hAIveMind collective connectivity
→ Verify sync service is running
→ Check Tailscale connection
```

## Related Commands
- **hv-sync**: Sync general hAIveMind state
- **hv-status**: Check collective health
- **hv-install**: Install base hAIveMind commands
- **hv-broadcast**: Announce plugin availability

---

**Plugin Action**: $ARGUMENTS

This will manage Claude Code plugins across the hAIveMind collective, enabling distribution of commands, agents, skills, and hooks to all connected machines.
