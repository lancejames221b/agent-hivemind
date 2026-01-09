# MCP Server Parity Matrix

**Generated**: 2026-01-09
**Purpose**: Track MCP server configuration status across all AI coding tools

## Summary

| Tool | Active Servers | Disabled | Notes |
|------|----------------|----------|-------|
| **Claude Code** | 9 | 0 | Reference implementation |
| **Cursor** | 10 | 0 | Has Figma (unique) |
| **Kilo Code** | 2 | 0 | Project-level only |
| **Cline** | 0 | 0 | Empty config |
| **Codex** | 4 | 4 | URL-based server bug |

---

## Detailed Server Matrix

| MCP Server | Claude Code | Cursor | Kilo Code | Cline | Codex |
|------------|:-----------:|:------:|:---------:|:-----:|:-----:|
| **haivemind** | ✅ SSE | ✅ SSE | ❌ | ❌ | ⚠️ Disabled |
| **slack** | ✅ SSE | ✅ SSE | ❌ | ❌ | ⚠️ Disabled |
| **trello** | ✅ SSE | ✅ SSE | ❌ | ❌ | ⚠️ Disabled |
| **notion** | ✅ SSE | ✅ SSE | ❌ | ❌ | ⚠️ Disabled |
| **atlassian** | ✅ npx | ✅ npx | ❌ | ❌ | ✅ npx |
| **vibe_kanban** | ✅ npx | ✅ npx | ❌ | ❌ | ✅ npx |
| **playwright** | ✅ npx | ✅ npx | ✅ npx | ❌ | ✅ npx |
| **puppeteer** | ✅ npx | ✅ npx | ✅ npx | ❌ | ✅ npx |
| **google-workspace** | ✅ uvx | ✅ uvx | ❌ | ❌ | ❌ |
| **Figma** | ❌ | ✅ URL | ❌ | ❌ | ❌ |

### Legend
- ✅ = Active and working
- ⚠️ = Configured but disabled/broken
- ❌ = Not configured

---

## Server Configuration Details

### haivemind (Distributed Memory)
- **Purpose**: Shared AI memory system for cross-tool context
- **Endpoint**: `http://{HAIVEMIND_URL}/sse`
- **Priority**: P0 (Critical for workflow parity)

| Tool | Config Method | Status |
|------|---------------|--------|
| Claude Code | `mcp-client-sse` wrapper | ✅ Working |
| Cursor | Native SSE support | ✅ Working |
| Kilo Code | Not configured | ❌ Gap |
| Cline | Not configured | ❌ Gap |
| Codex | Disabled (CLI bug) | ⚠️ Needs wrapper |

### slack (Team Communication)
- **Purpose**: Read/post Slack messages
- **Endpoint**: `http://{SLACK_MCP_URL}/sse`
- **Priority**: P0

| Tool | Config Method | Status |
|------|---------------|--------|
| Claude Code | `mcp-client-sse` wrapper | ✅ Working |
| Cursor | Native SSE support | ✅ Working |
| Kilo Code | Not configured | ❌ Gap |
| Cline | Not configured | ❌ Gap |
| Codex | Disabled (CLI bug) | ⚠️ Needs wrapper |

### trello (Task Management)
- **Purpose**: Trello board operations
- **Endpoint**: `http://{TRELLO_URL}/sse`
- **Priority**: P1

| Tool | Config Method | Status |
|------|---------------|--------|
| Claude Code | `mcp-client-sse` wrapper | ✅ Working |
| Cursor | Native SSE support | ✅ Working |
| Kilo Code | Not configured | ❌ Gap |
| Cline | Not configured | ❌ Gap |
| Codex | Disabled (CLI bug) | ⚠️ Needs wrapper |

### atlassian (Jira/Confluence)
- **Purpose**: Jira tickets, Confluence docs
- **Endpoint**: `https://mcp.atlassian.com/v1/sse`
- **Priority**: P0

| Tool | Config Method | Status |
|------|---------------|--------|
| Claude Code | `npx mcp-remote` | ✅ Working |
| Cursor | `npx mcp-remote` | ✅ Working |
| Kilo Code | Not configured | ❌ Gap |
| Cline | Not configured | ❌ Gap |
| Codex | `npx mcp-remote` | ✅ Working |

### notion (Documentation)
- **Purpose**: Notion workspace access
- **Endpoint**: `https://mcp.notion.com/sse`
- **Priority**: P1

| Tool | Config Method | Status |
|------|---------------|--------|
| Claude Code | `mcp-client-sse` wrapper | ✅ Working |
| Cursor | Native SSE support | ✅ Working |
| Kilo Code | Not configured | ❌ Gap |
| Cline | Not configured | ❌ Gap |
| Codex | Disabled (CLI bug) | ⚠️ Needs wrapper |

### vibe_kanban (Project Management)
- **Purpose**: Vibe Kanban task management
- **Command**: `npx -y vibe-kanban@latest --mcp`
- **Priority**: P1

| Tool | Config Method | Status |
|------|---------------|--------|
| Claude Code | npx command | ✅ Working |
| Cursor | npx command | ✅ Working |
| Kilo Code | Not configured | ❌ Gap |
| Cline | Not configured | ❌ Gap |
| Codex | npx command | ✅ Working |

### google-workspace (Google Apps)
- **Purpose**: Gmail, Calendar, Drive, Docs
- **Command**: `uvx workspace-mcp --tool-tier complete`
- **Priority**: P1

| Tool | Config Method | Status |
|------|---------------|--------|
| Claude Code | uvx command | ✅ Working |
| Cursor | uvx command | ✅ Working |
| Kilo Code | Not configured | ❌ Gap |
| Cline | Not configured | ❌ Gap |
| Codex | Not configured | ❌ Gap |

### playwright / puppeteer (Browser Automation)
- **Purpose**: Web testing, screenshots, automation
- **Priority**: P2

| Tool | playwright | puppeteer |
|------|:----------:|:---------:|
| Claude Code | ✅ | ✅ |
| Cursor | ✅ | ✅ |
| Kilo Code | ✅ | ✅ |
| Cline | ❌ | ❌ |
| Codex | ✅ | ✅ |

---

## Known Issues

### Codex CLI URL-Based Server Bug
**Issue**: Codex CLI 0.21.0 requires `command` field even for URL-based SSE servers
**Affected Servers**: haivemind, slack, trello, notion
**Workaround**: Create wrapper scripts that call `mcp-client-sse`

```toml
# Currently disabled in ~/.codex/config.toml:
# [mcp_servers.haivemind]
# url = "http://{HAIVEMIND_URL}/mcp"

# Workaround (wrapper script):
[mcp_servers.haivemind]
command = "{HOME}/.codex/wrappers/haivemind-wrapper.sh"
```

### Cline Empty Configuration
**Issue**: `~/.cline/data/settings/cline_mcp_settings.json` contains no servers
**Impact**: Cline cannot access any external services
**Fix**: Bootstrap with full server list (Phase 2)

---

## Remediation Priority

### P0 - Critical (Required for workflow parity)
1. **Cline**: Add all 9 MCP servers
2. **Codex**: Create wrapper scripts for 4 URL-based servers

### P1 - Important
1. **Kilo Code**: Add 7 missing MCP servers (all except playwright/puppeteer)

### P2 - Nice to Have
1. **Claude Code**: Consider adding Figma if needed
2. **Codex**: Add google-workspace

---

*Last Updated: 2026-01-09*
