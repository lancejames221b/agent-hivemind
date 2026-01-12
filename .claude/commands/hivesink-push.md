---
description: Quick push to hAIveMind vault (shortcut for hivesink-init up --all)
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "mcp__haivemind__*"]
argument-hint: [--scope personal|team|global] [--dry-run]
---

# hivesink-push - Quick Vault Push

## Purpose
Quick shortcut to push your current setup to hAIveMind vault. Equivalent to `hivesink-init up --all`.

## Syntax
```
hivesink-push [options]
```

## Options
- `--scope <personal|team|global>` - Choose vault scope (prompts if not specified)
- `--dry-run` - Preview what would be pushed without making changes
- `--skills` - Push only skills
- `--docs` - Push only docs
- `--configs` - Push only configs

## Examples

### Push Everything (Interactive Scope)
```
hivesink-push
```
Prompts for scope, then pushes all content to vault.

### Push to Personal Vault
```
hivesink-push --scope personal
```
Pushes all content to `~/.haivemind/vault/`.

### Backup Skills Only
```
hivesink-push --skills --scope personal
```
Backs up only your skill files.

### Preview First
```
hivesink-push --dry-run
```
Shows what would be pushed without making changes.

## What Gets Pushed

| Type | Source | Vault Destination |
|------|--------|-------------------|
| skills | `.claude/commands/*.md` | `vault/skills/` |
| docs | `CLAUDE.md`, `AGENT.md` | `vault/docs/` |
| configs | `.mcp.json`, `config/*.json` | `vault/configs/` |

## Vault Creation

If vault doesn't exist, it will be created:
```
📁 Creating vault at ~/.haivemind/vault/
├── skills/
├── docs/
├── configs/
└── manifest.json

✓ Vault initialized
```

## Conflict Handling

When vault files differ from local:
1. Shows diff between local and vault versions
2. Asks: overwrite vault, skip, or apply to all
3. Preserves your choice for remaining files

## Quick Reference

| Command | Description |
|---------|-------------|
| `hivesink-push` | Push all, prompt for scope |
| `hivesink-push --scope personal` | Push all to personal vault |
| `hivesink-push --skills` | Push only skill files |
| `hivesink-push --dry-run` | Preview without changes |

---

**Executing**: hivesink-init up --all $ARGUMENTS

This is a shortcut for `hivesink-init up --all`. Use `hivesink-init` directly for more control.
