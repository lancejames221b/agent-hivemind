---
name: elasticsearch-expertise
description: Deep expertise in Elasticsearch cluster management, search optimization, and troubleshooting. Activates for ES-related queries, cluster issues, or search performance problems.
allowed-tools: Bash, Read, mcp__haivemind__*
---

# Elasticsearch Expertise

Expert knowledge for Elasticsearch cluster operations, optimization, and troubleshooting.

## Cluster Health Interpretation

| Status | Meaning | Action |
|--------|---------|--------|
| GREEN | All shards allocated | None needed |
| YELLOW | Replicas not allocated | Check replica settings, disk space |
| RED | Primary shards missing | Immediate investigation needed |

## Common Issues & Solutions

### High Heap Usage (>85%)
```bash
# Check field data usage
curl -s localhost:9200/_cat/fielddata?v

# Clear field data cache
curl -XPOST localhost:9200/_cache/clear?fielddata=true

# Check indices.fielddata.cache.size setting
```

### Unassigned Shards
```bash
# Get explanation
curl -s localhost:9200/_cluster/allocation/explain?pretty

# Common causes:
# - Disk watermark exceeded
# - Node not available
# - Allocation filtering
```

### Slow Queries
```bash
# Enable slow log
curl -XPUT localhost:9200/_settings -d '{"index.search.slowlog.threshold.query.warn": "1s"}'

# Check hot threads
curl -s localhost:9200/_nodes/hot_threads

# Profile query
curl -XGET localhost:9200/index/_search -d '{"profile": true, "query": {...}}'
```

### Circuit Breaker Trips
```bash
# Check breaker stats
curl -s localhost:9200/_nodes/stats/breaker?pretty

# Common breakers:
# - fielddata: Reduce field data usage
# - request: Reduce concurrent requests
# - parent: Overall memory limit
```

## Performance Tuning

### Index Settings
```json
{
  "number_of_shards": 5,
  "number_of_replicas": 1,
  "refresh_interval": "30s",
  "translog.durability": "async"
}
```

### Query Optimization
- Use `filter` context for non-scoring queries
- Avoid wildcard queries at start of term
- Use `keyword` type for exact matches
- Limit returned fields with `_source`

### JVM Settings
- Heap: 50% of RAM, max 31GB
- GC: G1GC for heaps >6GB
- Disable swapping

## Monitoring Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Heap % | 75% | 90% |
| Disk % | 75% | 85% |
| CPU % | 80% | 95% |
| Load | 2x cores | 4x cores |
| Search latency | 100ms | 500ms |

## Best Practices

1. **Shard Sizing**: 20-40GB per shard
2. **Replicas**: At least 1 for high availability
3. **Refresh**: Increase interval for write-heavy indices
4. **Mapping**: Define explicit mappings, disable dynamic
5. **Aliases**: Use aliases for zero-downtime reindexing
