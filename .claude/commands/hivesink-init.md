---
description: Initialize hAIveMind vault sync - pull or push skills, docs, and configs
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "mcp__haivemind__*"]
argument-hint: <down|up> [--all|--interactive|--skills|--docs|--configs] [--dry-run]
---

# hivesink-init - Simple Vault Sync

## Purpose
Simple bi-directional sync for hAIveMind content. Pull from vault to start fresh, push to vault to share your setup.

## Syntax
```
hivesink-init <direction> [options]
```

## Direction (Required)
- `down` - Pull from vault to local (like git pull)
- `up` - Push from local to vault (like git push)

## Selection Options (Pick One)
- `--all` - Sync everything without prompts
- `--interactive` - Prompt for each type (default)
- `--skills` - Only skill files (.claude/commands/*.md)
- `--docs` - Only CLAUDE.md and AGENT.md
- `--configs` - Only config files (.mcp.json, config/*.json)

## Additional Options
- `--dry-run` - Show what would sync without making changes
- `--scope <personal|team|global>` - Choose vault scope (will prompt if not specified)

## Vault Storage Locations

### By Scope
- **personal**: `~/.haivemind/vault/` - Your private vault
- **team**: `~/.haivemind/team/<team_name>/` - Shared with team
- **global**: Via hAIveMind MCP sync service - Entire collective

### Structure
```
~/.haivemind/vault/
├── skills/           # .claude/commands/*.md files
│   ├── hv-sync.md
│   ├── remember.md
│   └── ...
├── docs/             # Documentation files
│   ├── CLAUDE.md
│   └── AGENT.md
├── configs/          # Configuration files
│   ├── mcp.json
│   └── sync-protocol.json
└── manifest.json     # Vault contents index
```

## Examples

### Fresh Start - Pull Everything
```
hivesink-init down --all
```
Pull all skills, docs, and configs from vault. No prompts.

### Interactive Pull
```
hivesink-init down
```
Prompts: Which scope? What content types? Approve each?

### Share Your Setup
```
hivesink-init up --all
```
Push your entire setup to vault for backup/sharing.

### Just Get Skills
```
hivesink-init down --skills --scope personal
```
Pull only skill files from personal vault.

### Preview Changes
```
hivesink-init down --all --dry-run
```
See what would be synced without making changes.

## Interactive Flow

When run without `--all`, you'll see:

```
🐝 HiveSink Init - Pull from Vault

Select scope:
  [1] personal - Your private vault
  [2] team     - Team shared vault
  [3] global   - hAIveMind collective

Scope (1-3): 1

What would you like to sync?
  [1] skills  - 19 commands available
  [2] docs    - CLAUDE.md, AGENT.md
  [3] configs - MCP config, sync protocol
  [4] all     - Everything above

Select (1-4, comma-separated ok): 1,2

Syncing skills...
  📄 hv-sync.md
     Local:  2025-01-20 (1.0.7)
     Vault:  2025-01-24 (1.0.8)
     [o]verwrite / [s]kip / [d]iff / [a]ll? d

--- DIFF: hv-sync.md ---
- version: 1.0.7
+ version: 1.0.8
+ Added --hooks parameter for sync hooks
---

     [o]verwrite / [s]kip? o
  ✓ hv-sync.md updated

Done! 19 skills, 2 docs synced.
```

## Conflict Handling

When local file exists and differs from vault:
1. **Show diff** - Display what changed
2. **Ask action** - Overwrite, skip, or view full diff
3. **Remember choice** - Option to apply same action to all

## Shortcuts

Use these for quick operations:
- `/hivesink pull` → `hivesink-init down --all`
- `/hivesink push` → `hivesink-init up --all`

## Implementation Notes

Execute the hivesink-init operation with the following process:

### Step 1: Parse Arguments
```
ARGS: $ARGUMENTS

Parse direction (down/up), options (--all, --skills, etc.), and scope
```

### Step 2: Determine Scope
If `--scope` not provided and not `--all`, prompt:
```
Select scope:
  [1] personal - ~/.haivemind/vault/
  [2] team     - ~/.haivemind/team/<name>/
  [3] global   - hAIveMind collective sync
```

### Step 3: Determine Content Types
If specific type not provided (`--skills`, `--docs`, `--configs`), and not `--all`, prompt:
```
What to sync?
  [1] skills  - Command files
  [2] docs    - CLAUDE.md, AGENT.md
  [3] configs - Configuration files
  [4] all     - Everything
```

### Step 4: Execute Sync

**For DOWN (pull):**
1. Read vault manifest to get available files
2. For each file in selected types:
   - If local doesn't exist: copy from vault
   - If local exists and differs: show diff, ask action
   - If local exists and same: skip (already current)
3. Update local manifest with sync timestamp

**For UP (push):**
1. Scan local files for selected types
2. For each file:
   - If vault doesn't have: copy to vault
   - If vault differs: show diff, ask to update
   - If same: skip
3. Update vault manifest

### Step 5: Report Results
```
✓ Sync complete!
  Skills:  15 synced, 2 skipped, 2 new
  Docs:    2 synced
  Configs: 1 synced

Vault: ~/.haivemind/vault/ (personal)
```

## File Mappings

| Type | Local Path | Vault Path |
|------|------------|------------|
| skills | `.claude/commands/*.md` | `vault/skills/*.md` |
| docs | `CLAUDE.md` | `vault/docs/CLAUDE.md` |
| docs | `AGENT.md` | `vault/docs/AGENT.md` |
| configs | `.mcp.json` | `vault/configs/mcp.json` |
| configs | `config/*.json` | `vault/configs/*.json` |
| configs | `sync-protocol.json` | `vault/configs/sync-protocol.json` |

## Error Handling

### Vault Not Initialized
```
❌ Vault not found at ~/.haivemind/vault/

Initialize with: hivesink-init up --all --scope personal
This will create the vault from your current setup.
```

### No Files to Sync
```
⚠️ No files found for selected types.

Check:
  - skills: .claude/commands/*.md
  - docs: CLAUDE.md, AGENT.md
  - configs: .mcp.json, config/*.json
```

### Permission Issues
```
❌ Cannot write to ~/.haivemind/vault/

Fix: mkdir -p ~/.haivemind/vault && chmod 700 ~/.haivemind
```

---

**Command**: $ARGUMENTS
