---
description: Store knowledge and experiences in hAIveMind collective memory
allowed-tools: ["mcp__haivemind__store_memory", "mcp__haivemind__search_memories"]
argument-hint: <memory content> [category] [--tags="tag1,tag2"] [--private] [--important]
---

# remember - Store Collective Memory

## Purpose
Store knowledge, experiences, solutions, and discoveries in the hAIveMind collective memory for future reference by you and other agents.

## Syntax
```
remember "<content>" [category] [options]
```

## Parameters
- **content** (required): The memory content to store (in quotes for multi-word)
- **category** (optional): Memory category (default: global)
  - `infrastructure`: Server configs, network topology
  - `incidents`: Outages, resolutions, post-mortems
  - `deployments`: Release notes, rollback procedures
  - `monitoring`: Alerts, metrics, thresholds
  - `runbooks`: Procedures, scripts, guides
  - `security`: Vulnerabilities, patches, audits
  - `global`: Cross-project shared knowledge
- **options**:
  - `--tags="tag1,tag2"`: Add searchable tags
  - `--private`: Store only for this machine
  - `--important`: Mark as high-priority memory

## Examples

### Store a solution
```
remember "Fixed Elasticsearch OOM by increasing heap to 16GB and reducing field data cache to 10%" incidents --tags="elasticsearch,oom,solution"
```

### Store infrastructure knowledge
```
remember "Production database primary is mysql-prod-01, replica is mysql-prod-02, failover takes ~30 seconds" infrastructure
```

### Store a runbook
```
remember "To restart nginx gracefully: sudo nginx -t && sudo systemctl reload nginx" runbooks --tags="nginx,restart"
```

### Private note
```
remember "API key rotates on 1st of each month, update in vault" security --private
```

## Output
```
💾 Memory Stored Successfully

ID: mem_abc123xyz
Category: incidents
Tags: elasticsearch, oom, solution
Scope: collective
Machine: lance-dev
Timestamp: 2025-01-24 10:30:00

Content Preview:
"Fixed Elasticsearch OOM by increasing heap to 16GB..."

✓ Synced to 12 collective agents
```

---

**Memory to Store**: $ARGUMENTS
