# MCP Server Parity Matrix

**Generated**: 2026-01-09
**Updated**: 2026-01-09 (Phase 2, 4 complete)
**Purpose**: Track MCP server configuration status across all AI coding tools

## Summary

| Tool | Active Servers | Disabled | Notes |
|------|----------------|----------|-------|
| **Claude Code** | 9 | 0 | Reference implementation |
| **Cursor** | 10 | 0 | Has Figma (unique) |
| **Kilo Code** | 2 | 0 | Project-level only |
| **Cline** | 9 | 0 | Fully configured ✅ |
| **Codex** | 9 | 0 | Wrapper scripts working ✅ |

---

## Detailed Server Matrix

| MCP Server | Claude Code | Cursor | Kilo Code | Cline | Codex |
|------------|:-----------:|:------:|:---------:|:-----:|:-----:|
| **haivemind** | ✅ SSE | ✅ SSE | ❌ | ✅ SSE | ✅ Wrapper |
| **slack** | ✅ SSE | ✅ SSE | ❌ | ✅ SSE | ✅ Wrapper |
| **trello** | ✅ SSE | ✅ SSE | ❌ | ✅ SSE | ✅ Wrapper |
| **notion** | ✅ SSE | ✅ SSE | ❌ | ✅ SSE | ✅ Wrapper |
| **atlassian** | ✅ npx | ✅ npx | ❌ | ✅ npx | ✅ npx |
| **vibe_kanban** | ✅ npx | ✅ npx | ❌ | ✅ npx | ✅ npx |
| **playwright** | ✅ npx | ✅ npx | ✅ npx | ✅ npx | ✅ npx |
| **puppeteer** | ✅ npx | ✅ npx | ✅ npx | ✅ npx | ✅ npx |
| **google-workspace** | ✅ uvx | ✅ uvx | ❌ | ✅ uvx | ✅ uvx |
| **Figma** | ❌ | ✅ URL | ❌ | ❌ | ❌ |

### Legend
- ✅ = Active and working
- ⚠️ = Configured but disabled/broken
- ❌ = Not configured

---

## Server Configuration Details

### haivemind (Distributed Memory)
- **Purpose**: Shared AI memory system for cross-tool context
- **Endpoint**: `{HAIVEMIND_URL}/sse`
- **Priority**: P0 (Critical for workflow parity)

| Tool | Config Method | Status |
|------|---------------|--------|
| Claude Code | `mcp-client-sse` wrapper | ✅ Working |
| Cursor | Native SSE support | ✅ Working |
| Kilo Code | Not configured | ❌ Gap |
| Cline | `mcp-client-sse` wrapper | ✅ Working |
| Codex | Wrapper script | ✅ Working |

### slack (Team Communication)
- **Purpose**: Read/post Slack messages
- **Endpoint**: `{SLACK_MCP_URL}/sse`
- **Priority**: P0

| Tool | Config Method | Status |
|------|---------------|--------|
| Claude Code | `mcp-client-sse` wrapper | ✅ Working |
| Cursor | Native SSE support | ✅ Working |
| Kilo Code | Not configured | ❌ Gap |
| Cline | `mcp-client-sse` wrapper | ✅ Working |
| Codex | Wrapper script | ✅ Working |

### trello (Task Management)
- **Purpose**: Trello board operations
- **Endpoint**: `{TRELLO_URL}/sse`
- **Priority**: P1

| Tool | Config Method | Status |
|------|---------------|--------|
| Claude Code | `mcp-client-sse` wrapper | ✅ Working |
| Cursor | Native SSE support | ✅ Working |
| Kilo Code | Not configured | ❌ Gap |
| Cline | `mcp-client-sse` wrapper | ✅ Working |
| Codex | Wrapper script | ✅ Working |

### atlassian (Jira/Confluence)
- **Purpose**: Jira tickets, Confluence docs
- **Endpoint**: `https://mcp.atlassian.com/v1/sse`
- **Priority**: P0

| Tool | Config Method | Status |
|------|---------------|--------|
| Claude Code | `npx mcp-remote` | ✅ Working |
| Cursor | `npx mcp-remote` | ✅ Working |
| Kilo Code | Not configured | ❌ Gap |
| Cline | `npx mcp-remote` | ✅ Working |
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
| Cline | `mcp-client-sse` wrapper | ✅ Working |
| Codex | Wrapper script | ✅ Working |

### vibe_kanban (Project Management)
- **Purpose**: Vibe Kanban task management
- **Command**: `npx -y vibe-kanban@latest --mcp`
- **Priority**: P1

| Tool | Config Method | Status |
|------|---------------|--------|
| Claude Code | npx command | ✅ Working |
| Cursor | npx command | ✅ Working |
| Kilo Code | Not configured | ❌ Gap |
| Cline | npx command | ✅ Working |
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
| Cline | uvx command | ✅ Working |
| Codex | uvx command | ✅ Working |

### playwright / puppeteer (Browser Automation)
- **Purpose**: Web testing, screenshots, automation
- **Priority**: P2

| Tool | playwright | puppeteer |
|------|:----------:|:---------:|
| Claude Code | ✅ | ✅ |
| Cursor | ✅ | ✅ |
| Kilo Code | ✅ | ✅ |
| Cline | ✅ | ✅ |
| Codex | ✅ | ✅ |

---

## Codex Wrapper Scripts

Codex CLI requires `command` field for SSE servers. Wrapper scripts created at `{HOME}/.codex/wrappers/`:

```bash
# haivemind-wrapper.sh
#!/bin/bash
exec mcp-client-sse "{HAIVEMIND_URL}/sse"
```

Similar wrappers for: `slack-wrapper.sh`, `trello-wrapper.sh`, `notion-wrapper.sh`

---

## Remaining Gaps

### Kilo Code (P1)
Missing 7 MCP servers:
- haivemind, slack, trello, notion, atlassian, vibe_kanban, google-workspace

**Reason**: Lower priority - tool less frequently used

---

*Last Updated: 2026-01-09*
