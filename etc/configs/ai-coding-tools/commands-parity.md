# Commands Parity Matrix

**Generated**: 2026-01-09
**Purpose**: Map command availability across AI coding tools

## Summary

| Tool | Commands | Format | Notes |
|------|----------|--------|-------|
| **Claude Code** | 39 | `/commands/*.md` | Reference implementation |
| **Cursor** | 34 | `/commands/*.md` | Near parity |
| **Kilo Code** | 0 | Rules-based | Uses markdown rules instead |
| **Cline** | 0 | TBD | No command system |
| **Codex** | 0 | Skills | Different paradigm |

---

## Command Mapping Matrix

### P0 - Critical Workflow Commands

| Command | Description | Claude | Cursor | Kilo | Cline | Codex |
|---------|-------------|:------:|:------:|:----:|:-----:|:-----:|
| `/recall` | Search hAIveMind memory | ✅ | ✅ | ⚠️ | ❌ | ❌ |
| `/remember` | Store to hAIveMind | ✅ | ✅ | ⚠️ | ❌ | ❌ |
| `/diagnose` | System diagnostics | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/pr` | Create pull request | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/jira` | Jira ticket operations | ✅ | ✅ | ❌ | ❌ | ❌ |

### P1 - Important Operations Commands

| Command | Description | Claude | Cursor | Kilo | Cline | Codex |
|---------|-------------|:------:|:------:|:----:|:-----:|:-----:|
| `/catch-up` | Get recent activity | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/incident` | Incident response | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/k8s-debug` | Kubernetes debugging | ✅ | ✅ (k8s) | ❌ | ❌ | ❌ |
| `/es-ops` | Elasticsearch ops | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/db-ops` | Database operations | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/gitops` | ArgoCD/K8s workflow | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/notion` | Notion documentation | ✅ | ❌ | ❌ | ❌ | ❌ |

### P1 - Slack/Communication Commands

| Command | Description | Claude | Cursor | Kilo | Cline | Codex |
|---------|-------------|:------:|:------:|:----:|:-----:|:-----:|
| `/slack-read` | Read Slack messages | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/slack-post` | Post to Slack | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/slack-dms` | Check direct messages | ✅ | ❌ | ❌ | ❌ | ❌ |

### P1 - Documentation Commands

| Command | Description | Claude | Cursor | Kilo | Cline | Codex |
|---------|-------------|:------:|:------:|:----:|:-----:|:-----:|
| `/document` | Create documentation | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/read` | Search {DOCS_REPO} | ✅ | ✅ | ❌ | ❌ | ❌ |
| `/docs-adr` | Create ADR | ❌ | ✅ | ❌ | ❌ | ❌ |
| `/docs-rca` | Create RCA | ❌ | ✅ | ❌ | ❌ | ❌ |
| `/docs-runbook` | Create runbook | ❌ | ✅ | ❌ | ❌ | ❌ |
| `/docs-config` | Document config | ❌ | ✅ | ❌ | ❌ | ❌ |
| `/docs-status` | Doc system status | ❌ | ✅ | ❌ | ❌ | ❌ |
| `/docs-ai` | AI-generated docs | ❌ | ✅ | ❌ | ❌ | ❌ |
| `/docs-repo` | Repo documentation | ❌ | ✅ | ❌ | ❌ | ❌ |

### P2 - Specialized Operations

| Command | Description | Claude | Cursor | Kilo | Cline | Codex |
|---------|-------------|:------:|:------:|:----:|:-----:|:-----:|
| `/auth-ops` | Auth server ops | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/discord-ops` | Discord scraper ops | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/gcloud-ops` | GCP operations | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/indexer-ops` | Indexer operations | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/kafka-ops` | Kafka operations | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/deploy-telegram` | Telegram deploy | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/scraper-debug` | Scraper debugging | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/enroll` | Telegram enrollment | ✅ | ❌ | ❌ | ❌ | ❌ |

### P2 - Development Workflow

| Command | Description | Claude | Cursor | Kilo | Cline | Codex |
|---------|-------------|:------:|:------:|:----:|:-----:|:-----:|
| `/review-pr` | PR code review | ✅ | ✅ (reviewpr) | ❌ | ❌ | ❌ |
| `/lookup` | Research & context | ✅ | ✅ (research) | ❌ | ❌ | ❌ |
| `/update` | Update Confluence/Jira | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/hand-off` | Context handoff | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/continue` | Pick up work session | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/reset` | Reset session context | ✅ | ❌ | ❌ | ❌ | ❌ |

### P2 - Utility Commands

| Command | Description | Claude | Cursor | Kilo | Cline | Codex |
|---------|-------------|:------:|:------:|:----:|:-----:|:-----:|
| `/me` | Personal dashboard | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/do` | DigitalOcean CLI | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/lance` | Lance James AI | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/allison` | Allison Bridge | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/edit-image` | Gemini image edit | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/p` | Parallel task exec | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/task` | Add task to todo | ✅ | ❌ | ❌ | ❌ | ❌ |
| `/taskp` | Parallel task add | ✅ | ❌ | ❌ | ❌ | ❌ |

### Cursor-Only Commands

| Command | Description | Equivalent in Claude |
|---------|-------------|---------------------|
| `/adr` | Architecture decision | - |
| `/cleanup-pr` | Clean up PR | - |
| `/docker` | Docker operations | - |
| `/feature-flag` | Feature flags | - |
| `/haivemind` | hAIveMind direct | `/recall` + `/remember` |
| `/mem` | Memory operations | `/recall` |
| `/mimic` | Style mimicry | - |
| `/prompt-designer` | Prompt design | - |
| `/rca` | Root cause analysis | - |
| `/rule` | Create rules | - |
| `/security` | Security audit | - |
| `/standup` | Standup report | - |
| `/start` | Start session | `/continue` |
| `/sub-task` | Sub-task creation | - |
| `/vibe` | Vibe Kanban | - |

---

## Legend

- ✅ = Available and working
- ⚠️ = Partial (via rules/docs, not native command)
- ❌ = Not available

---

## Kilo Code Rules Equivalent

Kilo Code uses markdown rules files instead of commands. Available at `~/.kilocode/rules/`:

| Rule File | Equivalent Commands |
|-----------|-------------------|
| `HAIVEMIND.MD` | `/recall`, `/remember` (documentation only) |

**Note**: These are instructional documents, not executable commands. The AI reads them for context but cannot invoke them like Claude Code commands.

---

## Remediation Plan

### Phase 1: P0 Commands (Critical)
Port these 5 commands to all tools:
1. `/recall` - Memory retrieval
2. `/remember` - Memory storage
3. `/diagnose` - System diagnostics
4. `/pr` - Pull request creation
5. `/jira` - Jira operations

### Phase 2: P1 Commands (Important)
Port key operational commands:
- `/catch-up`, `/incident`, `/document`, `/read`

### Phase 3: Tool-Specific Equivalents
- **Cline**: Research native command format
- **Codex**: Create equivalent skills
- **Kilo Code**: Consider if commands are needed (rules may suffice)

---

## Command Format Differences

### Claude Code / Cursor
```markdown
# ~/.claude/commands/recall.md
---
description: Search hAIveMind memory
---
Search for: $ARGUMENTS
Category: $CATEGORY
```

### Kilo Code (Rules-based)
```markdown
# ~/.kilocode/rules/HAIVEMIND.MD
## Memory Search
When searching memory, use mcp__haivemind__search_memories...
```

### Codex (Skills)
```toml
# Skills are defined in system prompts, not files
# Codex uses natural language skill definitions
```

### Cline
**TBD** - Need to research Cline's command/skill format

---

*Last Updated: 2026-01-09*
