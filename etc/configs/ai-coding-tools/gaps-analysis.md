# Gaps Analysis - AI Coding Tools Interoperability

**Generated**: 2026-01-09
**Purpose**: Prioritized list of missing features and remediation plan

---

## Executive Summary

| Tool | Parity Score | Critical Gaps | Effort to Fix |
|------|-------------|---------------|---------------|
| **Claude Code** | 100% | Reference | - |
| **Cursor** | 95% | Minor (5 commands) | Low |
| **Kilo Code** | 20% | 7 MCP servers, commands | Medium |
| **Cline** | 0% | Everything | High |
| **Codex** | 40% | 4 MCP servers (bug), commands | Medium |

---

## Critical Gaps by Tool

### Cline - CRITICAL (P0)

**Status**: Completely unconfigured - cannot perform any integrated workflows

#### MCP Servers (0/9 configured)
| Server | Priority | Impact |
|--------|----------|--------|
| haivemind | P0 | No shared memory access |
| slack | P0 | No team communication |
| atlassian | P0 | No Jira/Confluence |
| trello | P1 | No task management |
| notion | P1 | No documentation |
| vibe_kanban | P1 | No project tracking |
| google-workspace | P1 | No Google apps |
| playwright | P2 | No browser testing |
| puppeteer | P2 | No browser automation |

#### Commands (0/39)
- No command system configured
- Need to research Cline's native command format

#### Remediation
```json
// ~/.cline/data/settings/cline_mcp_settings.json
{
  "mcpServers": {
    "haivemind": {
      "command": "mcp-client-sse",
      "args": ["http://{HAIVEMIND_URL}/sse"]
    },
    "slack": {
      "command": "mcp-client-sse",
      "args": ["http://{SLACK_MCP_URL}/sse"]
    },
    "trello": {
      "command": "mcp-client-sse",
      "args": ["http://{TRELLO_URL}/sse"]
    },
    "notion": {
      "command": "mcp-client-sse",
      "args": ["https://mcp.notion.com/sse"]
    },
    "atlassian": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.atlassian.com/v1/sse"]
    },
    "vibe_kanban": {
      "command": "npx",
      "args": ["-y", "vibe-kanban@latest", "--mcp"]
    },
    "google-workspace": {
      "command": "{HOME}/.local/bin/uvx",
      "args": ["workspace-mcp", "--tool-tier", "complete"]
    },
    "playwright": {
      "command": "npx",
      "args": ["@executeautomation/playwright-mcp-server"]
    },
    "puppeteer": {
      "command": "npx",
      "args": ["puppeteer-mcp-server"]
    }
  }
}
```

**Estimated Effort**: 1 hour

---

### Codex - HIGH (P1)

**Status**: Partially working, but URL-based MCP servers disabled due to CLI bug

#### MCP Servers (4/9 working, 4 disabled)

| Server | Status | Issue |
|--------|--------|-------|
| haivemind | ⚠️ Disabled | CLI requires `command` field |
| slack | ⚠️ Disabled | CLI requires `command` field |
| trello | ⚠️ Disabled | CLI requires `command` field |
| notion | ⚠️ Disabled | CLI requires `command` field |
| atlassian | ✅ Working | Uses `npx mcp-remote` |
| vibe_kanban | ✅ Working | Uses `npx` |
| playwright | ✅ Working | Uses `npx` |
| puppeteer | ✅ Working | Uses `npx` |
| google-workspace | ❌ Missing | Not configured |

#### Commands (0/39)
- Codex uses "skills" not commands
- Different paradigm - natural language prompts

#### Remediation

**Step 1**: Create wrapper scripts for URL-based servers

```bash
# ~/.codex/wrappers/haivemind-wrapper.sh
#!/bin/bash
exec mcp-client-sse "http://{HAIVEMIND_URL}/sse"
```

```bash
# ~/.codex/wrappers/slack-wrapper.sh
#!/bin/bash
exec mcp-client-sse "http://{SLACK_MCP_URL}/sse"
```

```bash
# ~/.codex/wrappers/trello-wrapper.sh
#!/bin/bash
exec mcp-client-sse "http://{TRELLO_URL}/sse"
```

```bash
# ~/.codex/wrappers/notion-wrapper.sh
#!/bin/bash
exec mcp-client-sse "https://mcp.notion.com/sse"
```

**Step 2**: Update config.toml

```toml
# ~/.codex/config.toml additions

[mcp_servers.haivemind]
command = "{HOME}/.codex/wrappers/haivemind-wrapper.sh"

[mcp_servers.slack]
command = "{HOME}/.codex/wrappers/slack-wrapper.sh"

[mcp_servers.trello]
command = "{HOME}/.codex/wrappers/trello-wrapper.sh"

[mcp_servers.notion]
command = "{HOME}/.codex/wrappers/notion-wrapper.sh"

[mcp_servers.google-workspace]
command = "{HOME}/.local/bin/uvx"
args = ["workspace-mcp", "--tool-tier", "complete"]
```

**Estimated Effort**: 2 hours

---

### Kilo Code - MEDIUM (P1)

**Status**: Minimal MCP config, relies on rules-based system

#### MCP Servers (2/9 configured)

| Server | Status | Location |
|--------|--------|----------|
| puppeteer | ✅ | Project-level |
| playwright | ✅ | Project-level |
| haivemind | ❌ | Not configured |
| slack | ❌ | Not configured |
| trello | ❌ | Not configured |
| notion | ❌ | Not configured |
| atlassian | ❌ | Not configured |
| vibe_kanban | ❌ | Not configured |
| google-workspace | ❌ | Not configured |

#### Commands
- Uses rules files (`~/.kilocode/rules/*.MD`) instead of commands
- HAIVEMIND.MD provides documentation but not integration
- May not support full command paradigm

#### Remediation

**Step 1**: Expand project-level MCP config

```json
// ~/dev/ewitness-stack/.kilocode/mcp-servers.json
{
  "mcpServers": {
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "puppeteer-mcp-server"],
      "env": {
        "PUPPETEER_LAUNCH_ARGS": "--no-sandbox --disable-setuid-sandbox"
      }
    },
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    },
    "haivemind": {
      "command": "mcp-client-sse",
      "args": ["http://{HAIVEMIND_URL}/sse"]
    },
    "slack": {
      "command": "mcp-client-sse",
      "args": ["http://{SLACK_MCP_URL}/sse"]
    },
    "trello": {
      "command": "mcp-client-sse",
      "args": ["http://{TRELLO_URL}/sse"]
    },
    "notion": {
      "command": "mcp-client-sse",
      "args": ["https://mcp.notion.com/sse"]
    },
    "atlassian": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.atlassian.com/v1/sse"]
    },
    "vibe_kanban": {
      "command": "npx",
      "args": ["-y", "vibe-kanban@latest", "--mcp"]
    },
    "google-workspace": {
      "command": "{HOME}/.local/bin/uvx",
      "args": ["workspace-mcp", "--tool-tier", "complete"]
    }
  }
}
```

**Estimated Effort**: 1 hour

---

### Cursor - LOW (P2)

**Status**: Near parity with Claude Code

#### MCP Servers (10/10 - includes Figma)
- ✅ All servers working
- Has Figma (unique to Cursor)

#### Commands (34/39)
Missing Claude Code commands:
- `/auth-ops`
- `/discord-ops`
- `/do`
- `/enroll`
- `/es-ops`
- `/gcloud-ops`
- `/gitops`
- `/indexer-ops`
- `/kafka-ops`
- `/lance`
- `/me`
- `/notion`
- `/scraper-debug`
- `/slack-dms`
- `/slack-post`
- `/slack-read`
- `/update`

Has commands Claude Code doesn't have:
- `/adr`, `/cleanup-pr`, `/docker`, `/feature-flag`
- `/docs-*` series (7 commands)
- `/haivemind`, `/mem`, `/mimic`, `/prompt-designer`
- `/rca`, `/rule`, `/security`, `/standup`
- `/start`, `/sub-task`, `/vibe`

#### Remediation
- Most missing commands are eWitness-specific operations
- Consider selective porting based on workflow needs
- Low priority as Cursor is already functional

**Estimated Effort**: 4 hours (if full parity desired)

---

## Priority Matrix

### Immediate (This Week)
| Task | Tool | Effort | Impact |
|------|------|--------|--------|
| Bootstrap all MCP servers | Cline | 1h | Critical |
| Create wrapper scripts | Codex | 2h | High |
| Expand MCP config | Kilo Code | 1h | Medium |

### Short-Term (This Month)
| Task | Tool | Effort | Impact |
|------|------|--------|--------|
| Port P0 commands | All | 4h | High |
| Research Cline command format | Cline | 2h | Medium |
| Document Codex skills equivalent | Codex | 2h | Medium |

### Long-Term (Quarterly)
| Task | Tool | Effort | Impact |
|------|------|--------|--------|
| Full command parity | All | 8h | Low |
| Unified config management | All | 4h | Medium |
| Automated sync system | All | 4h | Medium |

---

## Risk Assessment

### High Risk
- **Codex CLI Bug**: Wrapper workaround may break on updates
  - Mitigation: Monitor Codex GitHub issues, test after updates

- **Cline Empty State**: No MCP means no external integrations
  - Mitigation: Immediate bootstrap (Phase 2)

### Medium Risk
- **Config Drift**: Tools may diverge over time
  - Mitigation: Weekly snapshots, automated comparison

- **Command Format Differences**: Each tool has different paradigm
  - Mitigation: Document equivalents, create translation layer

### Low Risk
- **Cursor/Claude Code Divergence**: Minor differences acceptable
  - Mitigation: Periodic review of critical commands

---

## Success Criteria

### Phase 1 Complete When:
- [ ] All 5 tools can connect to hAIveMind
- [ ] All 5 tools can access Slack MCP
- [ ] All 5 tools can access Atlassian MCP

### Phase 2 Complete When:
- [ ] `/recall` works in all 5 tools
- [ ] `/remember` works in all 5 tools
- [ ] Cross-tool memory test passes

### Full Parity When:
- [ ] All P0 commands available in all tools
- [ ] All P1 MCP servers configured in all tools
- [ ] Automated parity checking in place

---

## Appendix: Configuration File Locations

| Tool | MCP Config | Commands |
|------|------------|----------|
| Claude Code | `~/.claude/mcp.json` | `~/.claude/commands/*.md` |
| Cursor | `~/.cursor/mcp.json` | `~/.cursor/commands/*.md` |
| Kilo Code | `~/.kilocode/mcp-servers.json` | `~/.kilocode/rules/*.MD` |
| Cline | `~/.cline/data/settings/cline_mcp_settings.json` | TBD |
| Codex | `~/.codex/config.toml` | Skills (in prompts) |

---

*Last Updated: 2026-01-09*
