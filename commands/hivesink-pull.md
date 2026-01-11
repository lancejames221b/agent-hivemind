---
description: Quick pull from hAIveMind vault (shortcut for hivesink-init down --all)
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "mcp__haivemind__*"]
argument-hint: [--scope personal|team|global] [--dry-run]
---

# hivesink-pull - Quick Vault Pull

## Purpose
Quick shortcut to pull everything from your hAIveMind vault. Equivalent to `hivesink-init down --all`.

## Syntax
```
hivesink-pull [options]
```

## Options
- `--scope <personal|team|global>` - Choose vault scope (prompts if not specified)
- `--dry-run` - Preview what would be pulled without making changes
- `--skills` - Pull only skills
- `--docs` - Pull only docs
- `--configs` - Pull only configs

## Examples

### Pull Everything (Interactive Scope)
```
hivesink-pull
```
Prompts for scope, then pulls all content.

### Pull from Personal Vault
```
hivesink-pull --scope personal
```
Pulls all content from `~/.haivemind/vault/`.

### Preview First
```
hivesink-pull --dry-run
```
Shows what would be pulled without making changes.

## What Gets Pulled

| Type | Files | Destination |
|------|-------|-------------|
| skills | `*.md` commands | `.claude/commands/` |
| docs | CLAUDE.md, AGENT.md | Project root |
| configs | mcp.json, *.json | `.mcp.json`, `config/` |

## Conflict Handling

When local files differ from vault:
1. Shows diff between local and vault versions
2. Asks: overwrite, skip, or apply to all
3. Preserves your choice for remaining files

## Quick Reference

| Command | Description |
|---------|-------------|
| `hivesink-pull` | Pull all, prompt for scope |
| `hivesink-pull --scope personal` | Pull all from personal vault |
| `hivesink-pull --skills` | Pull only skill files |
| `hivesink-pull --dry-run` | Preview without changes |

---

**Executing**: hivesink-init down --all $ARGUMENTS

This is a shortcut for `hivesink-init down --all`. Use `hivesink-init` directly for more control.
