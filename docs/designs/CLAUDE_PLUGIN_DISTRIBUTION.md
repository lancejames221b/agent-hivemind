# Claude Plugin Distribution System for hAIveMind

## Overview

hAIveMind will support distributing **Claude Code Plugins** across the collective. Plugins are the complete distribution unit that bundles:

- **Commands** - Slash commands (`.claude/commands/`)
- **Subagents** - Specialized AI workers (`.claude/agents/`)
- **Skills** - Model-invoked knowledge (`.claude/skills/`)
- **Hooks** - Event-triggered automation (`hooks/hooks.json`)
- **MCP Servers** - External tool connections (`.mcp.json`)

## Plugin Structure (Claude Code Standard)

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json         # Required manifest
├── commands/               # Slash commands
│   ├── deploy.md
│   └── rollback.md
├── agents/                 # Subagent definitions
│   ├── security-auditor.md
│   └── performance-analyst.md
├── skills/                 # AI skills
│   └── incident-response/
│       └── SKILL.md
├── hooks/
│   └── hooks.json          # Event handlers
├── .mcp.json              # MCP server definitions
└── README.md
```

## Plugin Manifest (`plugin.json`)

```json
{
  "name": "devops-essentials",
  "version": "1.2.0",
  "description": "Essential DevOps workflows for infrastructure management",
  "author": {
    "name": "hAIveMind Collective",
    "organization": "Unit 221B"
  },
  "haivemind": {
    "machine_groups": ["orchestrators", "dev_environments"],
    "required_capabilities": ["deployment", "infrastructure_management"],
    "min_haivemind_version": "1.0.0"
  },
  "components": {
    "commands": "./commands/",
    "agents": "./agents/",
    "skills": "./skills/",
    "hooks": "./hooks/hooks.json",
    "mcpServers": "./.mcp.json"
  },
  "dependencies": {
    "plugins": ["base-memory-tools@^1.0.0"],
    "mcp_servers": ["haivemind"]
  }
}
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     hAIveMind Plugin System                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    Plugin Registry                              │ │
│  │                                                                  │ │
│  │  ChromaDB Collection: plugin_registry                           │ │
│  │  ┌──────────────────────────────────────────────────────────┐  │ │
│  │  │ {                                                         │  │ │
│  │  │   "id": "plugin_devops-essentials_1.2.0",                │  │ │
│  │  │   "name": "devops-essentials",                           │  │ │
│  │  │   "version": "1.2.0",                                    │  │ │
│  │  │   "manifest": { ... },                                   │  │ │
│  │  │   "machine_groups": ["orchestrators", "dev_environments"],│  │ │
│  │  │   "installed_on": ["lance-dev", "chris-dev"],            │  │ │
│  │  │   "checksum": "sha256:abc123...",                        │  │ │
│  │  │   "created_at": "2025-01-24T..."                         │  │ │
│  │  │ }                                                         │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              ↓                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    Plugin Storage                               │ │
│  │                                                                  │ │
│  │  SQLite: data/plugins.db                                        │ │
│  │  ┌──────────────────────────────────────────────────────────┐  │ │
│  │  │ Tables:                                                   │  │ │
│  │  │ - plugins (id, name, version, manifest, status)          │  │ │
│  │  │ - plugin_files (plugin_id, path, content, type)          │  │ │
│  │  │ - plugin_installations (plugin_id, machine_id, status)   │  │ │
│  │  │ - plugin_dependencies (plugin_id, depends_on, version)   │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              ↓                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                  Distribution Service                           │ │
│  │                                                                  │ │
│  │  sync_service.py extensions:                                    │ │
│  │  - POST /api/plugins/register     - Register new plugin        │ │
│  │  - POST /api/plugins/publish      - Publish to collective      │ │
│  │  - GET  /api/plugins/list         - List available plugins     │ │
│  │  - GET  /api/plugins/{id}         - Get plugin details         │ │
│  │  - POST /api/plugins/{id}/install - Install on machine         │ │
│  │  - POST /api/plugins/sync         - Sync all plugins           │ │
│  │  - WS   /ws/plugins               - Real-time plugin updates   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              ↓                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │              Machine-Specific Installation                      │ │
│  │                                                                  │ │
│  │  lance-dev (orchestrator):                                      │ │
│  │    ~/.claude/plugins/devops-essentials/                         │ │
│  │    ~/.claude/plugins/monitoring-tools/                          │ │
│  │                                                                  │ │
│  │  elastic1 (elasticsearch):                                      │ │
│  │    ~/.claude/plugins/elasticsearch-ops/                         │ │
│  │                                                                  │ │
│  │  proxy0 (scraper):                                              │ │
│  │    ~/.claude/plugins/scraper-coordination/                      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Implementation Stories

### Story 1: Plugin Registry Foundation
**Epic: PLUGIN-REGISTRY**

#### 1a. Database Schema for Plugin Storage
- Create `data/plugins.db` with tables for plugins, files, installations
- Add migration system for schema updates
- Index on name, version, machine_groups for fast queries

#### 1b. ChromaDB Collection for Plugin Discovery
- Create `plugin_registry` collection
- Store plugin manifests with embeddings for semantic search
- Enable "find plugins for elasticsearch optimization" queries

#### 1c. Plugin Model Classes
- `Plugin` - Core plugin representation
- `PluginManifest` - Parsed plugin.json
- `PluginInstallation` - Per-machine installation state
- `PluginFile` - Individual file within plugin

### Story 2: Plugin Packaging & Validation
**Epic: PLUGIN-PACKAGE**

#### 2a. Plugin Package Parser
- Parse `.claude-plugin/plugin.json` manifest
- Validate required fields and structure
- Extract component references (commands, agents, skills, hooks)

#### 2b. Plugin Content Loader
- Load all plugin files into memory/storage
- Validate file types and structure
- Generate checksums for integrity verification

#### 2c. Plugin Dependency Resolver
- Parse `dependencies.plugins` from manifest
- Check if required plugins are available
- Build dependency graph for installation order

#### 2d. Plugin Validation Engine
- Validate command files (YAML frontmatter + markdown)
- Validate agent definitions (required fields)
- Validate skill structure (SKILL.md format)
- Validate hooks.json schema
- Validate .mcp.json format

### Story 3: Plugin Distribution MCP Tools
**Epic: PLUGIN-MCP-TOOLS**

#### 3a. register_plugin Tool
```python
@mcp.tool()
async def register_plugin(
    plugin_path: str = None,      # Local path to plugin directory
    plugin_archive: str = None,   # Base64-encoded zip archive
    plugin_url: str = None        # URL to download plugin
) -> dict:
    """Register a new plugin with the hAIveMind collective"""
```

#### 3b. publish_plugin Tool
```python
@mcp.tool()
async def publish_plugin(
    plugin_id: str,
    target_groups: list = None,   # Machine groups to publish to
    notify_agents: bool = True    # Broadcast availability
) -> dict:
    """Publish a registered plugin to the collective for distribution"""
```

#### 3c. install_plugin Tool
```python
@mcp.tool()
async def install_plugin(
    plugin_id: str,
    version: str = "latest",
    target_machines: list = None,  # Defaults to compatible machines
    force: bool = False
) -> dict:
    """Install a plugin on target machines"""
```

#### 3d. list_plugins Tool
```python
@mcp.tool()
async def list_plugins(
    installed_only: bool = False,
    machine_group: str = None,
    capability_filter: list = None,
    search_query: str = None       # Semantic search
) -> list:
    """List available plugins with filtering"""
```

#### 3e. sync_plugins Tool
```python
@mcp.tool()
async def sync_plugins(
    force: bool = False,
    dry_run: bool = False
) -> dict:
    """Sync all plugins with the collective, install updates"""
```

#### 3f. get_plugin_status Tool
```python
@mcp.tool()
async def get_plugin_status(
    plugin_id: str = None         # None = all plugins
) -> dict:
    """Get installation status and health of plugins"""
```

### Story 4: Plugin Sync Service Extensions
**Epic: PLUGIN-SYNC**

#### 4a. REST API Endpoints
- `POST /api/plugins/register` - Register plugin from upload
- `POST /api/plugins/publish` - Publish to collective
- `GET /api/plugins` - List available plugins
- `GET /api/plugins/{id}` - Get plugin details and files
- `POST /api/plugins/{id}/install` - Trigger installation
- `POST /api/plugins/sync` - Trigger full sync
- `DELETE /api/plugins/{id}` - Remove plugin

#### 4b. WebSocket Plugin Channel
- Real-time plugin update notifications
- Installation progress streaming
- Cross-machine sync status

#### 4c. Plugin File Distribution
- Efficient file transfer between machines
- Delta sync for updates (only changed files)
- Compression for large plugins

#### 4d. Conflict Resolution
- Version comparison (semver)
- Machine-specific overrides
- Rollback capability

### Story 5: Plugin Installation Engine
**Epic: PLUGIN-INSTALL**

#### 5a. Local Installation Manager
- Extract plugin to `~/.claude/plugins/{name}/`
- Register commands in Claude Code
- Register agents in Claude Code
- Register skills in Claude Code
- Apply hooks configuration

#### 5b. Component Installers
- `CommandInstaller` - Copy to `.claude/commands/`
- `AgentInstaller` - Copy to `.claude/agents/`
- `SkillInstaller` - Copy to `.claude/skills/`
- `HookInstaller` - Merge with existing hooks
- `MCPServerInstaller` - Update MCP configuration

#### 5c. Installation Hooks
- Pre-install validation
- Post-install verification
- Rollback on failure

#### 5d. Uninstallation Manager
- Clean removal of all plugin components
- Preserve user customizations option
- Update registries

### Story 6: Plugin Discovery & Recommendations
**Epic: PLUGIN-DISCOVERY**

#### 6a. Semantic Plugin Search
- "Find plugins for kubernetes deployment"
- "What plugins help with log analysis"
- Leverage ChromaDB embeddings

#### 6b. Capability-Based Recommendations
- Based on machine role, suggest plugins
- Based on current task, suggest plugins
- Based on agent capabilities, suggest plugins

#### 6c. Plugin Analytics
- Track plugin usage across collective
- Identify popular/useful plugins
- Surface recommendations in hv-status

### Story 7: Built-in Plugin Templates
**Epic: PLUGIN-TEMPLATES**

#### 7a. hAIveMind Core Plugin
```
haivemind-core/
├── commands/
│   ├── hv-broadcast.md
│   ├── hv-delegate.md
│   ├── hv-query.md
│   ├── hv-status.md
│   ├── hv-sync.md
│   ├── remember.md
│   └── recall.md
├── agents/
│   └── haivemind-coordinator.md
├── skills/
│   └── collective-memory/
│       └── SKILL.md
└── .claude-plugin/
    └── plugin.json
```

#### 7b. Elasticsearch Operations Plugin
```
elasticsearch-ops/
├── commands/
│   ├── es-health.md
│   ├── es-reindex.md
│   └── es-snapshot.md
├── agents/
│   └── es-specialist.md
├── skills/
│   └── elasticsearch-expertise/
│       └── SKILL.md
└── .claude-plugin/
    └── plugin.json
```

#### 7c. Incident Response Plugin
```
incident-response/
├── commands/
│   ├── incident-start.md
│   ├── incident-update.md
│   └── incident-resolve.md
├── agents/
│   └── incident-commander.md
├── skills/
│   └── incident-management/
│       └── SKILL.md
├── hooks/
│   └── hooks.json          # Auto-broadcast on incidents
└── .claude-plugin/
    └── plugin.json
```

### Story 8: Claude Code Integration
**Epic: PLUGIN-CLAUDE-INTEGRATION**

#### 8a. Plugin Command for hAIveMind
```markdown
# /hv-plugin command
---
description: Manage hAIveMind plugins - install, update, list, remove
allowed-tools: ["mcp__haivemind__*"]
argument-hint: [install|list|update|remove|search] [plugin-name]
---
```

#### 8b. Auto-Sync on Session Start
- Hook into Claude Code session start
- Check for plugin updates
- Notify user of available updates

#### 8c. Plugin Status in hv-status
- Show installed plugins
- Show available updates
- Show plugin health

## Database Schema

### SQLite: data/plugins.db

```sql
-- Core plugin registry
CREATE TABLE plugins (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    description TEXT,
    author_name TEXT,
    author_org TEXT,
    manifest JSON NOT NULL,
    checksum TEXT NOT NULL,
    status TEXT DEFAULT 'registered',  -- registered, published, deprecated
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, version)
);

-- Plugin file storage
CREATE TABLE plugin_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_id TEXT NOT NULL REFERENCES plugins(id),
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,  -- command, agent, skill, hook, mcp, other
    content TEXT NOT NULL,
    checksum TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(plugin_id, file_path)
);

-- Installation tracking per machine
CREATE TABLE plugin_installations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_id TEXT NOT NULL REFERENCES plugins(id),
    machine_id TEXT NOT NULL,
    installed_version TEXT NOT NULL,
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'installed',  -- installed, failed, updating, removing
    install_path TEXT,
    error_message TEXT,
    UNIQUE(plugin_id, machine_id)
);

-- Dependency tracking
CREATE TABLE plugin_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_id TEXT NOT NULL REFERENCES plugins(id),
    depends_on_name TEXT NOT NULL,
    depends_on_version TEXT NOT NULL,  -- semver constraint
    dependency_type TEXT DEFAULT 'required',  -- required, optional
    UNIQUE(plugin_id, depends_on_name)
);

-- Machine group compatibility
CREATE TABLE plugin_machine_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_id TEXT NOT NULL REFERENCES plugins(id),
    machine_group TEXT NOT NULL,
    UNIQUE(plugin_id, machine_group)
);

-- Indexes
CREATE INDEX idx_plugins_name ON plugins(name);
CREATE INDEX idx_plugins_status ON plugins(status);
CREATE INDEX idx_installations_machine ON plugin_installations(machine_id);
CREATE INDEX idx_installations_status ON plugin_installations(status);
CREATE INDEX idx_machine_groups_group ON plugin_machine_groups(machine_group);
```

## Configuration Extensions

### config.json additions

```json
{
  "plugins": {
    "enabled": true,
    "registry_db": "data/plugins.db",
    "install_path": "~/.claude/plugins",
    "auto_sync": true,
    "sync_interval": 3600,
    "auto_install_updates": false,
    "verify_checksums": true,
    "allowed_sources": ["haivemind", "local"],
    "machine_group_auto_install": true,
    "max_plugin_size_mb": 50,
    "backup_before_update": true
  }
}
```

## CLI Commands

```bash
# List available plugins
/hv-plugin list

# Search for plugins
/hv-plugin search "kubernetes deployment"

# Install a plugin
/hv-plugin install elasticsearch-ops

# Update all plugins
/hv-plugin update

# Remove a plugin
/hv-plugin remove elasticsearch-ops

# Show plugin details
/hv-plugin info elasticsearch-ops

# Create new plugin from template
/hv-plugin create my-plugin

# Publish local plugin to collective
/hv-plugin publish ./my-plugin

# Sync plugins with collective
/hv-plugin sync
```

## Success Metrics

1. **Plugin Distribution Time**: < 30 seconds to distribute plugin to all machines
2. **Plugin Discovery**: Semantic search returns relevant plugins in top 3 results
3. **Installation Success Rate**: > 99% successful installations
4. **Sync Reliability**: Zero data loss during sync conflicts
5. **Developer Experience**: Create and publish plugin in < 5 minutes

## Security Considerations

1. **Checksum Verification**: All plugin files verified before installation
2. **Source Validation**: Only accept plugins from trusted sources
3. **Permission Sandboxing**: Plugins cannot exceed declared permissions
4. **Audit Logging**: All plugin operations logged
5. **Rollback Capability**: Can revert to previous plugin version

## Migration Path

1. **Phase 1**: Convert existing `.claude/commands/` to hAIveMind Core plugin
2. **Phase 2**: Enable plugin sync infrastructure
3. **Phase 3**: Create machine-group-specific plugins
4. **Phase 4**: Enable community plugin contributions

---

## Appendix: Example Plugin Files

### Example Command (commands/deploy.md)
```markdown
---
description: Deploy application to target environment
allowed-tools: ["Bash", "mcp__haivemind__*"]
argument-hint: <environment> [--dry-run]
---

# Deploy Command

Deploy the current application to the specified environment.

## Arguments
- environment: Target environment (dev, staging, prod)
- --dry-run: Show what would be deployed without executing

## Task
$ARGUMENTS
```

### Example Agent (agents/security-auditor.md)
```markdown
---
name: security-auditor
description: Security expert for vulnerability assessment and code review
tools: Read, Grep, Glob, Bash
model: sonnet
permissionMode: plan
skills: security-analysis
---

You are a senior security engineer specializing in:
- OWASP Top 10 vulnerabilities
- Authentication and authorization flaws
- Data exposure risks
- Injection attacks

When invoked, systematically check for security issues.
```

### Example Skill (skills/incident-response/SKILL.md)
```markdown
---
name: incident-response
description: Expert knowledge for handling production incidents, outages, and emergencies. Activates when discussing incidents, alerts, outages, or emergency procedures.
allowed-tools: Read, Grep, Bash, mcp__haivemind__*
---

# Incident Response Expertise

## Immediate Actions
1. Assess severity (P1-P4)
2. Identify affected systems
3. Check monitoring dashboards
4. Review recent deployments

## Communication
- Broadcast to hAIveMind collective
- Update incident channel
- Notify on-call if P1/P2

## Resolution Steps
1. Contain the issue
2. Identify root cause
3. Apply fix
4. Verify resolution
5. Document lessons learned
```

### Example Hooks (hooks/hooks.json)
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash(kubectl:*)",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Kubernetes command executed' | logger -t haivemind"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash(rm -rf:*)",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'WARNING: Destructive command detected'"
          }
        ]
      }
    ]
  }
}
```
