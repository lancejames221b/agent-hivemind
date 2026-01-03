---
name: collective-memory
description: Expert knowledge for utilizing hAIveMind collective memory effectively. Activates when storing memories, searching knowledge, coordinating with agents, or managing collective intelligence.
allowed-tools: mcp__haivemind__*, Read
---

# Collective Memory Expertise

This skill provides expertise in effectively using the hAIveMind collective memory system for storing, searching, and sharing knowledge across the agent network.

## Memory Categories

Use the appropriate category for each memory type:

| Category | Use For | Examples |
|----------|---------|----------|
| `infrastructure` | System configs, topology | "Database primary is on mysql-01" |
| `incidents` | Problems, solutions, RCAs | "OOM fixed by increasing heap" |
| `deployments` | Releases, rollbacks | "v2.1 deployed to production" |
| `monitoring` | Alerts, thresholds | "CPU alert at 85% for 5 min" |
| `runbooks` | Procedures, scripts | "Restart: systemctl reload nginx" |
| `security` | Vulnerabilities, patches | "CVE-2024-xxx patched on 01/24" |
| `global` | Cross-cutting knowledge | "Team standup at 9am daily" |

## Effective Memory Storage

### Good Memory Content
- Specific and actionable
- Includes context and solution
- Uses clear, searchable terms

```
Good: "Fixed Elasticsearch cluster yellow status by increasing replica count from 1 to 2 for index 'logs-2024'. Issue was unbalanced shards after node-3 restart."

Bad: "Fixed ES issue"
```

### Tagging Strategy
- Use 2-4 relevant tags
- Include technology name
- Include action type (fix, config, procedure)
- Include severity if applicable

```
tags: ["elasticsearch", "cluster-health", "replica-fix", "production"]
```

## Effective Memory Search

### Semantic Search Tips
- Use natural language queries
- Include technology and symptom
- Be specific about the problem

```
Good: "elasticsearch high heap usage causing slow queries"
Bad: "es problem"
```

### Combining Filters
- Use category to narrow scope
- Use `--recent` for current issues
- Use `--machine` for source context

```
recall "database connection timeout" incidents --recent=24
```

## Agent Coordination Patterns

### Before Starting Tasks
Always check collective knowledge first:
```
1. search_memories query="<task description>"
2. Check if solution already exists
3. If not, proceed with new approach
4. Store findings when complete
```

### Sharing Discoveries
For important findings, broadcast to the collective:
```
broadcast_discovery
  message="<finding>"
  category="<infrastructure|incidents|security>"
  severity="<info|warning|critical>"
```

### Task Delegation
When work matches another agent's specialty:
```
delegate_task
  task_description="<what needs to be done>"
  required_capabilities=["<capability>"]
```

## Memory Lifecycle

1. **Create**: Store new knowledge with appropriate category/tags
2. **Search**: Find existing knowledge before reinventing
3. **Update**: Use update_memory for corrections
4. **Share**: Broadcast important discoveries
5. **Archive**: Old memories naturally age out (365 days default)

## Collective Intelligence Principles

1. **Share Everything**: What you learn benefits all agents
2. **Search First**: Check if knowledge exists before creating
3. **Be Specific**: Vague memories are hard to find later
4. **Tag Thoughtfully**: Good tags make search effective
5. **Broadcast Important Findings**: Critical info should reach all agents immediately
