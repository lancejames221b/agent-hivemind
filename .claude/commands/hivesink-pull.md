---
description: Pull commands and configs from hAIveMind central vault to local machine
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
argument-hint: [--skills] [--docs] [--configs] [--dry-run] [--all]
---

# hivesink-pull - Sync from hAIveMind Vault

## Purpose
Pull skills, docs, and configs from the central hAIveMind vault on lance-dev to your local machine. Uses HTTP via Tailscale for cross-machine synchronization (no SSH key setup required).

## Syntax
```
hivesink-pull [options]
```

## Options
- `--dry-run` - Preview what would be synced without making changes
- `--skills` - Pull only skill files (commands/*.md)
- `--docs` - Pull only docs (CLAUDE.md, etc.)
- `--configs` - Pull only config files
- `--all` - Pull everything (default behavior)

## Central Vault Location
The hAIveMind vault is served via HTTP from lance-dev:8900:
- `http://lance-dev:8900/vault/skills/` - Command skill files
- `http://lance-dev:8900/vault/docs/` - Documentation
- `http://lance-dev:8900/vault/configs/` - Configuration files

## Execution Instructions

When this command is invoked, execute the following commands based on options:

### Setup Local Directories
```bash
mkdir -p ~/.claude/commands
mkdir -p ./config
```

### Check What's Available (--dry-run)
Preview vault contents without downloading:
```bash
# List all available files
curl -s http://lance-dev:8900/vault/list | python3 -m json.tool

# Check manifest for sync timestamps
curl -s http://lance-dev:8900/vault/manifest | python3 -m json.tool
```

### Pull Everything (default or --all)
Download entire vault as zip and extract:
```bash
# Download vault zip
curl -o /tmp/haivemind-vault.zip http://lance-dev:8900/vault/download.zip

# Extract to temp directory
rm -rf /tmp/haivemind-vault
unzip -o /tmp/haivemind-vault.zip -d /tmp/haivemind-vault/

# Copy skills to local commands
cp /tmp/haivemind-vault/skills/*.md ~/.claude/commands/ 2>/dev/null || true

# Copy configs
cp /tmp/haivemind-vault/configs/.mcp.json ~/.mcp.json 2>/dev/null || true
cp /tmp/haivemind-vault/configs/*.json ./config/ 2>/dev/null || true

# Copy docs to project root
cp /tmp/haivemind-vault/docs/*.md ./ 2>/dev/null || true

# Cleanup
rm -rf /tmp/haivemind-vault.zip /tmp/haivemind-vault/

echo "✅ Vault sync complete"
```

### Pull Skills Only (--skills)
Download only skill files:
```bash
# Get list of skills
SKILLS=$(curl -s http://lance-dev:8900/vault/list | python3 -c "import sys,json; print('\n'.join(json.load(sys.stdin)['skills']))")

# Download each skill
mkdir -p ~/.claude/commands
for skill in $SKILLS; do
    curl -s -o ~/.claude/commands/$skill "http://lance-dev:8900/vault/skills/$skill"
    echo "Downloaded: $skill"
done
```

### Pull Configs Only (--configs)
Download only config files:
```bash
# Get list of configs
CONFIGS=$(curl -s http://lance-dev:8900/vault/list | python3 -c "import sys,json; print('\n'.join(json.load(sys.stdin)['configs']))")

mkdir -p ./config
for config in $CONFIGS; do
    if [ "$config" = ".mcp.json" ]; then
        curl -s -o ~/.mcp.json "http://lance-dev:8900/vault/configs/$config"
    else
        curl -s -o "./config/$config" "http://lance-dev:8900/vault/configs/$config"
    fi
    echo "Downloaded: $config"
done
```

### Pull Docs Only (--docs)
Download only documentation files:
```bash
# Get list of docs
DOCS=$(curl -s http://lance-dev:8900/vault/list | python3 -c "import sys,json; print('\n'.join(json.load(sys.stdin)['docs']))")

for doc in $DOCS; do
    curl -s -o "./$doc" "http://lance-dev:8900/vault/docs/$doc"
    echo "Downloaded: $doc"
done
```

## Examples

### Pull Everything
```
/hivesink-pull
```
Downloads entire vault and extracts to local paths.

### Preview First
```
/hivesink-pull --dry-run
```
Shows vault contents without downloading.

### Pull Only Skills
```
/hivesink-pull --skills
```
Only downloads skill files to ~/.claude/commands/

### Pull Single File
```bash
# Download a specific skill directly
curl -o ~/.claude/commands/help.md http://lance-dev:8900/vault/skills/help.md
```

## What Gets Pulled

| Type | Source URL | Local Destination |
|------|-----------|-------------------|
| skills | `http://lance-dev:8900/vault/skills/*.md` | `~/.claude/commands/` |
| docs | `http://lance-dev:8900/vault/docs/` | Project root |
| configs | `http://lance-dev:8900/vault/configs/` | `~/.mcp.json`, `./config/` |

## Requirements
- Tailscale VPN connected (for lance-dev access)
- curl installed (standard on Mac/Linux)
- unzip installed (for full vault download)

## Troubleshooting

### Connection Failed
```bash
# Test HTTP connectivity
curl -s http://lance-dev:8900/health

# Check Tailscale status
tailscale status | grep lance-dev

# Verify vault endpoint
curl -s http://lance-dev:8900/vault/list
```

### curl Not Found
```bash
# Mac (usually pre-installed)
brew install curl

# Linux
sudo apt-get install curl
```

### unzip Not Found
```bash
# Mac (usually pre-installed)
brew install unzip

# Linux
sudo apt-get install unzip
```

---

**HTTP-Based Sync**: This command uses HTTP over Tailscale VPN to sync from the central hAIveMind vault on lance-dev:8900. No SSH keys required - just Tailscale connectivity.
