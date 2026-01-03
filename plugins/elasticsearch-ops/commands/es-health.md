---
description: Check Elasticsearch cluster health and diagnostics
allowed-tools: ["Bash", "mcp__haivemind__store_memory", "mcp__haivemind__search_memories"]
argument-hint: [--cluster=<name>] [--detailed] [--fix]
---

# es-health - Elasticsearch Cluster Health Check

## Purpose
Comprehensive health check for Elasticsearch clusters. Checks cluster status, node health, shard allocation, and common issues.

## Syntax
```
es-health [options]
```

## Options
- `--cluster=<name>`: Target specific cluster (default: localhost:9200)
- `--detailed`: Show detailed diagnostics
- `--fix`: Attempt automatic fixes for common issues

## Checks Performed

1. **Cluster Status**: Green/Yellow/Red status
2. **Node Health**: All nodes responding
3. **Shard Allocation**: Unassigned shards
4. **Disk Space**: Node disk usage
5. **JVM Heap**: Memory pressure
6. **Circuit Breakers**: Tripped breakers
7. **Thread Pools**: Rejected threads

## Examples

### Basic Health Check
```
es-health
```

### Detailed Diagnostics
```
es-health --detailed
```

### Auto-Fix Issues
```
es-health --fix
```

## Expected Output
```
🔍 Elasticsearch Cluster Health Check

CLUSTER: production-es
STATUS: 🟢 GREEN

NODES: 5/5 healthy
┌──────────────┬────────┬────────┬─────────┬──────────┐
│ Node         │ Status │ Heap % │ Disk %  │ Load     │
├──────────────┼────────┼────────┼─────────┼──────────┤
│ es-node-1    │ ✓      │ 65%    │ 45%     │ 2.3      │
│ es-node-2    │ ✓      │ 58%    │ 42%     │ 1.8      │
│ es-node-3    │ ✓      │ 72%    │ 48%     │ 2.1      │
│ es-node-4    │ ✓      │ 61%    │ 44%     │ 1.9      │
│ es-node-5    │ ✓      │ 55%    │ 41%     │ 1.5      │
└──────────────┴────────┴────────┴─────────┴──────────┘

SHARDS: 250 total, 0 unassigned
INDICES: 45 active

ALERTS: None

✓ Cluster is healthy
```

## Troubleshooting Actions

### Yellow Status
- Check for unassigned replicas
- Verify replica count settings
- Check disk space on nodes

### Red Status
- Identify missing primary shards
- Check node connectivity
- Review cluster logs for errors

### High Heap Usage
- Review field data cache
- Check query complexity
- Consider adding nodes

---

**Health Check Options**: $ARGUMENTS
