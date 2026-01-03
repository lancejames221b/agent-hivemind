---
description: Search and retrieve memories from hAIveMind collective knowledge base
allowed-tools: ["mcp__haivemind__search_memories", "mcp__haivemind__retrieve_memory"]
argument-hint: <search query> [category] [--recent=hours] [--limit=N] [--machine=name]
---

# recall - Search Collective Memory

## Purpose
Search and retrieve knowledge from the hAIveMind collective memory. Find solutions, procedures, and insights stored by you and other agents.

## Syntax
```
recall "<query>" [category] [options]
```

## Parameters
- **query** (required): Search terms (semantic search)
- **category** (optional): Limit to specific category
- **options**:
  - `--recent=24`: Only memories from last N hours
  - `--limit=10`: Max results (default: 5)
  - `--machine=name`: Filter by source machine

## Examples

### Find solutions
```
recall "elasticsearch out of memory"
```

### Search recent incidents
```
recall "database connection" incidents --recent=48
```

### Find runbooks
```
recall "nginx configuration" runbooks
```

### Search from specific machine
```
recall "deployment procedure" --machine=elastic1
```

## Output
```
🔍 Search Results for: "elasticsearch out of memory"

Found 3 relevant memories:

1. [incidents] Score: 0.92
   From: lance-dev (2025-01-24)
   "Fixed Elasticsearch OOM by increasing heap to 16GB and
    reducing field data cache to 10%"
   Tags: elasticsearch, oom, solution

2. [monitoring] Score: 0.85
   From: elastic1 (2025-01-23)
   "Set up heap usage alerts at 85% threshold to prevent OOM.
    Alert routes to #elasticsearch-alerts"
   Tags: elasticsearch, monitoring, alerts

3. [runbooks] Score: 0.78
   From: lance-dev (2025-01-20)
   "ES Memory Troubleshooting: 1) Check _cat/nodes?h=heap*
    2) Review field data usage 3) Check query cache..."
   Tags: elasticsearch, troubleshooting, memory

💡 Use memory IDs with retrieve_memory for full content
```

---

**Search Query**: $ARGUMENTS
