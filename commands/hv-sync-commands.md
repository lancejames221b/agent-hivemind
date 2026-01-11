---
description: Sync personal commands and skills across AI tools (Claude, Cursor, Kilo, Cline) and machines via hAIveMind
allowed-tools: ["mcp__haivemind__*", "Read", "Write"]
argument-hint: [push|pull|cross-tool|list|detect] [--tool <name>] [--filter <cmd1,cmd2>] [--force]
---

# hv-sync-commands - Personal Command Synchronization

## Purpose
Synchronize personal slash commands and skills across different AI coding assistants and machines using hAIveMind as the central hub.

## When to Use
- **New Machine Setup**: Pull your personal commands to a new workstation
- **Cross-Tool Sync**: Copy commands from Claude Code to Cursor, Kilo, or Cline
- **Team Sharing**: Share selected commands with team members
- **Backup Commands**: Push personal commands to hAIveMind for safekeeping
- **Multi-Machine Workflow**: Keep commands in sync across lance-dev, m2, max, etc.

## Syntax
```
hv-sync-commands <operation> [options]
```

## Operations

### `detect` - Detect AI Tools
Scan for installed AI coding assistants and their command directories.
```
hv-sync-commands detect
```

### `push` - Push to hAIveMind
Sync personal commands from local directory to hAIveMind memory.
```
hv-sync-commands push [--tool <name>] [--filter <commands>] [--scope <scope>]
```
- `--tool`: Source tool (claude|cursor|kilo|cline|codex), default: claude
- `--filter`: Only sync specific commands (comma-separated)
- `--scope`: Memory scope (project-shared|user-global|team-global)

### `pull` - Pull from hAIveMind
Sync commands from hAIveMind memory to local directory.
```
hv-sync-commands pull [--tool <name>] [--filter <commands>] [--force]
```
- `--tool`: Target tool (claude|cursor|kilo|cline|codex), default: claude
- `--filter`: Only sync specific commands (comma-separated)
- `--force`: Overwrite existing commands

### `cross-tool` - Cross-Tool Sync
Sync commands directly between AI tools without going through hAIveMind.
```
hv-sync-commands cross-tool --from <tool> [--to <tools>] [--force]
```
- `--from`: Source tool
- `--to`: Target tools (comma-separated), default: all others
- `--force`: Overwrite existing commands

### `list` - List Synced Commands
Show all commands synced in hAIveMind memory.
```
hv-sync-commands list [--scope <all|personal|hv>]
```

## Real-World Examples

### Detect Available Tools
```
hv-sync-commands detect
```
**Result**: Shows Claude Code, Cursor, Kilo, Cline with command counts

### Push All Personal Commands
```
hv-sync-commands push --tool claude
```
**Result**: Syncs all ~/.claude/commands/ to hAIveMind

### Push Specific Commands
```
hv-sync-commands push --filter "remember,recall,diagnose"
```
**Result**: Only syncs the specified commands

### Pull Commands to Cursor
```
hv-sync-commands pull --tool cursor --force
```
**Result**: Installs commands to ~/.cursor/commands/

### Copy Claude Commands to All Tools
```
hv-sync-commands cross-tool --from claude
```
**Result**: Copies to Cursor, Kilo, Cline, Codex

### List All Synced Commands
```
hv-sync-commands list
```
**Result**: Shows personal and hv-* commands in hAIveMind

## Expected Output

### Detection Result
```
AI Tool Detection Results

Claude
   Commands: /home/lj/.claude/commands (40 files)
   Skills: /home/lj/.claude/skills (0 files)

Cursor
   Commands: /home/lj/.cursor/commands (0 files)
   Skills: /home/lj/.cursor/skills (0 files)

Kilo
   Commands: /home/lj/.kilo/commands (0 files)

Cline
   Commands: /home/lj/.cline/commands (0 files)
```

### Push Result
```
Personal Commands Synced to hAIveMind

**Source Tool**: claude
**Total Found**: 40
**Synced**: 38
**Skipped**: 2 (hv-* commands)
**Errors**: 0

**Synced Commands**:
  remember (created)
  recall (created)
  diagnose (created)
  pr (created)
  jira (created)
  ... and 33 more
```

### Cross-Tool Sync Result
```
Cross-Tool Command Sync

**Source**: claude

cursor: 40/40 commands installed
   Path: /home/lj/.cursor/commands

kilo: 40/40 commands installed
   Path: /home/lj/.kilo/commands

cline: 40/40 commands installed
   Path: /home/lj/.cline/commands
```

## Supported Tools

| Tool | Commands Path | Skills Path |
|------|--------------|-------------|
| Claude Code | ~/.claude/commands | ~/.claude/skills |
| Cursor | ~/.cursor/commands | ~/.cursor/skills |
| Kilo | ~/.kilo/commands | ~/.kilo/skills |
| Cline | ~/.cline/commands | ~/.cline/skills |
| Codex | ~/.codex/commands | ~/.codex/skills |

## Sharing Scopes

| Scope | Description |
|-------|-------------|
| `project-shared` | Share with agents on same project |
| `user-global` | Share across all your machines |
| `team-global` | Share with entire team |

## Best Practices

1. **Initial Setup**: Run `detect` first to see what tools you have
2. **Push Before Pull**: Always push local changes before pulling from hAIveMind
3. **Filter Sensitive**: Use `--filter` to exclude commands with secrets
4. **Cross-Tool Testing**: Test commands work in target tool after sync
5. **Regular Sync**: Run push weekly to keep hAIveMind backup current

## Command Format

Commands must be in Markdown format with YAML frontmatter:
```markdown
---
description: What this command does
allowed-tools: ["Tool1", "Tool2"]
argument-hint: [arg1] [arg2]
---

# Command Name

## Purpose
...
```

## Related Commands
- `hv-sync`: Sync hAIveMind system commands
- `hv-install`: Install hAIveMind to new machine
- `hv-status`: Check sync status

---

**Operation**: $ARGUMENTS

This will synchronize your personal commands across AI tools and machines using hAIveMind as the synchronization hub.
