---
description: Push commands and configs from local machine to hAIveMind central vault
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
argument-hint: [--skills] [--docs] [--configs] [--dry-run] [--all]
---

# hivesink-push - Sync to hAIveMind Vault

## Purpose
Push skills, docs, and configs from your local machine to the central hAIveMind vault on lance-dev. Uses HTTP via Tailscale for cross-machine synchronization (no SSH key setup required).

## Syntax
```
hivesink-push [options]
```

## Options
- `--dry-run` - Preview what would be pushed without making changes
- `--skills` - Push only skill files (commands/*.md)
- `--docs` - Push only docs (CLAUDE.md, etc.)
- `--configs` - Push only config files
- `--all` - Push everything (default behavior)

## Central Vault Location
The hAIveMind vault is accessible via HTTP at lance-dev:8900:
- `http://lance-dev:8900/vault/upload/skills/` - Upload skill files
- `http://lance-dev:8900/vault/upload/docs/` - Upload documentation
- `http://lance-dev:8900/vault/upload/configs/` - Upload config files

## Execution Instructions

When this command is invoked, execute the following commands based on options:

### Check Current Vault State (--dry-run)
Preview what's in the vault and what would be pushed:
```bash
echo "=== Current Vault Contents ==="
curl -s http://lance-dev:8900/vault/list | python3 -m json.tool

echo ""
echo "=== Local Files to Push ==="
echo "Skills:"
ls -la ~/.claude/commands/*.md 2>/dev/null || echo "  No skill files found"
echo "Configs:"
ls -la ./.mcp.json ./config/*.json 2>/dev/null || echo "  No config files found"
echo "Docs:"
ls -la ./CLAUDE.md ./AGENT.md 2>/dev/null || echo "  No doc files found"
```

### Push Everything (default or --all)
Upload all local files to vault:
```bash
MACHINE_NAME=$(hostname)

echo "=== Pushing Skills ==="
for file in ~/.claude/commands/*.md; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        curl -s -X POST --data-binary @"$file" \
            -H "X-Source-Machine: $MACHINE_NAME" \
            "http://lance-dev:8900/vault/upload/skills/$filename" && \
            echo "✅ Uploaded: $filename"
    fi
done

echo ""
echo "=== Pushing Configs ==="
if [ -f "./.mcp.json" ]; then
    curl -s -X POST --data-binary @"./.mcp.json" \
        -H "X-Source-Machine: $MACHINE_NAME" \
        "http://lance-dev:8900/vault/upload/configs/.mcp.json" && \
        echo "✅ Uploaded: .mcp.json"
fi

for file in ./config/*.json; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        curl -s -X POST --data-binary @"$file" \
            -H "X-Source-Machine: $MACHINE_NAME" \
            "http://lance-dev:8900/vault/upload/configs/$filename" && \
            echo "✅ Uploaded: $filename"
    fi
done

echo ""
echo "=== Pushing Docs ==="
for doc in CLAUDE.md AGENT.md; do
    if [ -f "./$doc" ]; then
        curl -s -X POST --data-binary @"./$doc" \
            -H "X-Source-Machine: $MACHINE_NAME" \
            "http://lance-dev:8900/vault/upload/docs/$doc" && \
            echo "✅ Uploaded: $doc"
    fi
done

echo ""
echo "✅ Push complete"
```

### Push Skills Only (--skills)
Upload only skill files:
```bash
MACHINE_NAME=$(hostname)
for file in ~/.claude/commands/*.md; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        curl -s -X POST --data-binary @"$file" \
            -H "X-Source-Machine: $MACHINE_NAME" \
            "http://lance-dev:8900/vault/upload/skills/$filename" && \
            echo "✅ Uploaded: $filename"
    fi
done
```

### Push Configs Only (--configs)
Upload only config files:
```bash
MACHINE_NAME=$(hostname)

if [ -f "./.mcp.json" ]; then
    curl -s -X POST --data-binary @"./.mcp.json" \
        -H "X-Source-Machine: $MACHINE_NAME" \
        "http://lance-dev:8900/vault/upload/configs/.mcp.json" && \
        echo "✅ Uploaded: .mcp.json"
fi

for file in ./config/*.json; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        curl -s -X POST --data-binary @"$file" \
            -H "X-Source-Machine: $MACHINE_NAME" \
            "http://lance-dev:8900/vault/upload/configs/$filename" && \
            echo "✅ Uploaded: $filename"
    fi
done
```

### Push Docs Only (--docs)
Upload only documentation files:
```bash
MACHINE_NAME=$(hostname)
for doc in CLAUDE.md AGENT.md; do
    if [ -f "./$doc" ]; then
        curl -s -X POST --data-binary @"./$doc" \
            -H "X-Source-Machine: $MACHINE_NAME" \
            "http://lance-dev:8900/vault/upload/docs/$doc" && \
            echo "✅ Uploaded: $doc"
    fi
done
```

## Examples

### Push Everything
```
/hivesink-push
```
Uploads all local skills, docs, and configs to lance-dev vault.

### Preview First
```
/hivesink-push --dry-run
```
Shows current vault state and local files without uploading.

### Push Only Skills
```
/hivesink-push --skills
```
Only uploads your local command skill files to the vault.

### Push Single File
```bash
# Upload a specific skill directly
curl -X POST --data-binary @~/.claude/commands/my-skill.md \
    -H "X-Source-Machine: $(hostname)" \
    http://lance-dev:8900/vault/upload/skills/my-skill.md
```

## What Gets Pushed

| Type | Local Source | Destination URL |
|------|-------------|-----------------|
| skills | `~/.claude/commands/*.md` | `http://lance-dev:8900/vault/upload/skills/` |
| docs | Project `CLAUDE.md`, `AGENT.md` | `http://lance-dev:8900/vault/upload/docs/` |
| configs | `.mcp.json`, `config/*.json` | `http://lance-dev:8900/vault/upload/configs/` |

## Requirements
- Tailscale VPN connected (for lance-dev access)
- curl installed (standard on Mac/Linux)

## Manifest Update
The upload endpoint automatically updates the vault manifest with:
- File names and paths
- Last sync timestamp
- Source machine (from X-Source-Machine header)

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

### Upload Failed
```bash
# Check server response
curl -v -X POST --data-binary @~/.claude/commands/test.md \
    http://lance-dev:8900/vault/upload/skills/test.md
```

### curl Not Found
```bash
# Mac (usually pre-installed)
brew install curl

# Linux
sudo apt-get install curl
```

---

**HTTP-Based Sync**: This command uses HTTP over Tailscale VPN to sync to the central hAIveMind vault on lance-dev:8900. No SSH keys required - just Tailscale connectivity. Changes you push become available to all machines in the hAIveMind collective via /hivesink-pull.
