---
description: Install or update hAIveMind commands and agent configuration
allowed-tools: ["mcp__haivemind__*", "Write", "Read", "Edit", "LS", "Bash"]
argument-hint: [personal|project|clean|status] [--force] [--quiet]
---

# hv-install - hAIveMind Setup and Updates

## Purpose
Install, update, or manage hAIveMind command suite and agent configuration for seamless integration with the collective intelligence system.

## When to Use
- **First Time Setup**: Initialize hAIveMind on new development environment
- **Command Updates**: Install latest command versions from collective
- **Project Integration**: Set up hAIveMind for specific projects
- **Troubleshooting**: Clean install to resolve command issues
- **Agent Registration**: Register new agent with specialized capabilities
- **Configuration Sync**: Update CLAUDE.md with hAIveMind integration

## Syntax
```
hv-install [target] [options]
```

## Parameters
- **target** (optional): Installation scope
  - `personal`: Install to personal commands (~/.claude/commands/)
  - `project`: Install to project commands (.claude/commands/)  
  - `clean`: Remove and reinstall all commands fresh
  - `status`: Show current installation status only
  - (no target): Smart detection based on current directory
- **options** (optional):
  - `--force`: Force reinstall even if up-to-date
  - `--quiet`: Minimal output, errors only
  - `--dry-run`: Show what would be installed without making changes

## Installation Process

### Smart Detection (No Arguments)
1. **Context Analysis**: Check if in project directory or personal environment
2. **Existing Installation**: Detect current commands and versions
3. **Capability Assessment**: Determine agent role based on system type
4. **Optimal Configuration**: Choose best installation strategy

### Location-Specific Installation
- **Personal (~/.claude/commands/)**: Global commands available across all projects
- **Project (.claude/commands/)**: Project-specific commands with custom configuration
- **Hybrid**: Personal base + project-specific overrides

## Real-World Examples

### First Time Setup on Development Machine
```
hv-install personal
```
**Result**: Installs all hv-* commands to personal directory, registers as development agent, sets up collective connectivity

### Project-Specific Integration
```
hv-install project
```
**Result**: Installs commands with project-specific CLAUDE.md integration, configures project memory categories

### Clean Reinstall After Issues
```
hv-install clean --force
```
**Result**: Removes all existing commands, downloads fresh copies, reconfigures agent registration

### Check Current Status
```
hv-install status
```
**Result**: Shows installed versions, agent registration status, collective connectivity health

### Quiet Update Check
```
hv-install --quiet
```
**Result**: Updates commands if needed, minimal output unless errors occur

## Expected Output

### Successful Installation
```
🔧 hAIveMind Installation Starting...

✓ Location: ~/.claude/commands/ (personal)
✓ Agent Detection: development environment on lance-dev
✓ Collective Connectivity: 12 agents reachable via Tailscale

📦 Installing Commands:
✓ hv-broadcast.md (v1.2.3) - updated
✓ hv-delegate.md (v1.1.0) - updated  
✓ hv-query.md (v1.0.5) - new
✓ hv-status.md (v1.1.2) - up-to-date
✓ hv-sync.md (v1.0.8) - updated
✓ recall.md (v2.0.1) - updated
✓ remember.md (v2.0.1) - updated

🔗 Agent Registration:
✓ Registered as: lance-dev-development-agent  
✓ Capabilities: [development, infrastructure_management, coordination]
✓ Role: hive_mind orchestrator
✓ Network: Connected to 12 collective agents

📝 CLAUDE.md Integration:
✓ hAIveMind sections added to CLAUDE.md
✓ Command usage patterns documented
✓ Agent coordination instructions added

🎉 Installation Complete! 
   Use 'hv-status' to verify collective connectivity
   Use 'hv-sync' to pull latest updates
```

### Status Check Output
```
📊 hAIveMind Installation Status

📍 Installation Location: ~/.claude/commands/ (personal)
🤖 Agent Identity: lance-dev-development-agent
🌐 Collective Status: Connected (12 agents)
📅 Last Update: 2025-01-24 10:30:00

📦 Installed Commands:
Command         Version    Status      Last Updated
hv-broadcast    v1.2.3     current     2025-01-24
hv-delegate     v1.1.0     current     2025-01-24
hv-query        v1.0.5     current     2025-01-24
hv-status       v1.1.2     current     2025-01-23
hv-sync         v1.0.8     current     2025-01-24
recall          v2.0.1     current     2025-01-24
remember        v2.0.1     current     2025-01-24

🔄 Available Updates: None
🚦 System Health: All systems operational
```

## Installation Locations

### Personal Installation (~/.claude/commands/)
- **Pros**: Available across all projects, single maintenance point
- **Cons**: No project-specific customization
- **Best For**: Individual developers, consistent environment

### Project Installation (.claude/commands/)  
- **Pros**: Project-specific configuration, team collaboration
- **Cons**: Must install per project, potential version drift
- **Best For**: Team projects, specialized configurations

### Hybrid Approach (Personal + Project Overrides)
- Personal installation provides base commands
- Project installation overrides specific commands
- Best of both worlds for complex environments

## Agent Registration Process

### Automatic Capability Detection
- **Machine Type**: Development, production, monitoring, database
- **Installed Software**: elasticsearch, mysql, nginx, docker
- **Network Role**: Coordinator, specialist, worker
- **Access Permissions**: SSH keys, API tokens, admin rights

### Capability Categories
- `development`: Code review, testing, build processes
- `infrastructure_management`: Server admin, deployment, scaling  
- `elasticsearch_ops`: Cluster management, search optimization
- `database_ops`: Query optimization, backup/restore
- `monitoring`: Alerting, dashboards, metrics analysis
- `security_analysis`: Vulnerability assessment, incident response
- `coordination`: Task delegation, agent management

## Common Installation Scenarios

### New Developer Onboarding
1. `hv-install personal` - Set up personal commands
2. `hv-status` - Verify collective connectivity  
3. `hv-broadcast "New developer joined: [name]" infrastructure info`
4. `hv-query "onboarding checklist"` - Get team-specific setup tasks

### Production Server Setup
1. `hv-install personal --quiet` - Minimal installation
2. Agent auto-registers with production capabilities
3. Limited command set for security
4. Monitoring and incident response focused

### Project Team Setup
1. Team lead: `hv-install project` in shared repository
2. Team members: `git pull` to get .claude/commands/
3. Auto-sync keeps everyone updated
4. Project-specific memory categories configured

## Error Scenarios and Solutions

### Permission Denied
```
❌ Error: Permission denied writing to ~/.claude/commands/
→ Check directory permissions: ls -la ~/.claude/
→ Create directory: mkdir -p ~/.claude/commands
→ Fix ownership: sudo chown $USER:$USER ~/.claude/commands
```

### Collective Connectivity Issues
```
❌ Warning: Cannot connect to hAIveMind collective
→ Check Tailscale: tailscale status
→ Check MCP server: curl http://localhost:8900/health
→ Verify configuration: cat config/config.json
→ Retry with: hv-install --force
```

### Version Conflicts
```
❌ Error: Command version conflict detected
→ Use clean install: hv-install clean
→ Check for manual modifications in commands/
→ Backup custom changes before clean install
```

### Agent Registration Failures
```
❌ Error: Failed to register agent with collective
→ Check Redis connectivity: redis-cli ping
→ Verify API tokens in config.json
→ Check network connectivity to other agents
→ Manual registration: use MCP tools directly
```

## Performance Considerations
- **Installation Time**: ~30 seconds for full install
- **Network Usage**: ~100KB for all commands  
- **Storage**: ~50KB per command set
- **Registration**: ~2 seconds to register with collective
- **Sync Frequency**: Commands check for updates every 6 hours

## Security Considerations
- Commands stored as plain text (no sensitive data)
- Agent capabilities determined by system access
- Network communication encrypted via Tailscale
- Redis connections password-protected
- API tokens required for collective access

## Best Practices
- **Regular Updates**: Use `hv-sync` weekly to get latest commands
- **Status Monitoring**: Check `hv-status` daily for collective health
- **Clean Installs**: Use `clean` option if experiencing strange behavior
- **Backup Customizations**: Save custom command modifications before updates
- **Team Coordination**: Use project installation for team environments
- **Documentation**: Keep CLAUDE.md updated with installation choices

## Troubleshooting

### Commands Not Found After Installation
1. Check installation location matches expectation
2. Verify Claude Code settings for command directories
3. Restart Claude Code to pick up new commands
4. Use `hv-install status` to confirm installation

### Agent Not Appearing in Collective
1. Check network connectivity: `hv-status`
2. Verify registration: check Redis for agent entry
3. Confirm unique agent ID (no duplicates)
4. Re-register: `hv-install clean --force`

### CLAUDE.md Integration Issues
1. Backup existing CLAUDE.md before installation
2. Check for syntax errors in generated sections
3. Manual integration may be needed for complex existing files
4. Use `--dry-run` to preview changes first

---

**Installation Command**: $ARGUMENTS

This will set up or update your hAIveMind integration with automatic agent registration, command installation, and collective connectivity configuration.