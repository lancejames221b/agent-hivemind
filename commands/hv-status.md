---
description: Monitor hAIveMind collective health, agent status, and system performance
allowed-tools: ["mcp__haivemind__get_agent_roster", "mcp__haivemind__get_memory_stats", "mcp__haivemind__get_machine_context"]
argument-hint: [--detailed] [--agents] [--memory] [--network] [--json]
---

# hv-status - Collective Health Monitor

## Purpose
Comprehensive monitoring of hAIveMind collective health including agent availability, memory utilization, network connectivity, and system performance metrics.

## When to Use
- **Daily Health Checks**: Monitor collective operational status
- **Troubleshooting Issues**: Diagnose connectivity or performance problems
- **Capacity Planning**: Monitor memory usage and agent workload
- **Network Monitoring**: Check Tailscale connectivity between agents
- **Before Delegating**: Verify target agents are available and responsive
- **Performance Analysis**: Understand collective resource utilization

## Syntax
```
hv-status [options]
```

## Parameters
- **options** (optional): Display filtering and formatting
  - `--detailed`: Show comprehensive information for all sections
  - `--agents`: Show only agent roster and availability
  - `--memory`: Show only memory statistics and usage
  - `--network`: Show only network connectivity status
  - `--json`: Output in JSON format for programmatic use
  - `--quiet`: Show only critical issues, minimal output

## Status Information Sections

### Agent Roster and Availability
- **Active Agents**: Currently online and responding
- **Agent Capabilities**: Skills and expertise each agent provides
- **Response Times**: Average response latency for each agent
- **Workload Status**: Current task queue and availability
- **Last Seen**: When each agent was last active

### Memory Statistics
- **Storage Utilization**: ChromaDB and Redis usage metrics
- **Memory Categories**: Distribution across infrastructure, incidents, etc.
- **Growth Trends**: Memory usage over time
- **Cache Performance**: Redis hit rates and efficiency
- **Cleanup Status**: Old memory removal and optimization

### Network Health
- **Tailscale Connectivity**: Connection status to each machine
- **API Endpoints**: Health check status for MCP servers
- **Sync Performance**: Inter-machine synchronization latency
- **Certificate Status**: SSL/TLS certificate validity
- **Firewall Status**: Port accessibility between nodes

## Real-World Examples

### Quick Health Check
```
hv-status
```
**Result**: Overview of collective health with key metrics and any issues highlighted

### Detailed System Analysis
```
hv-status --detailed
```
**Result**: Comprehensive report suitable for troubleshooting or performance analysis

### Agent Availability Check
```
hv-status --agents
```
**Result**: Focus on which agents are available for task delegation

### Memory Usage Analysis
```
hv-status --memory
```
**Result**: Storage metrics for capacity planning and cleanup decisions

### Programmatic Monitoring
```
hv-status --json --quiet
```
**Result**: JSON output for automated monitoring scripts, errors only

## Expected Output

### Standard Status Overview
```
🌐 hAIveMind Collective Status - 2025-01-24 14:30:00

🎯 Collective Health: ✓ OPERATIONAL
   ↳ 12 of 14 agents responding (85.7%)
   ↳ 2 agents offline: tony-dev, mike-dev (non-critical)
   ↳ Average response time: 245ms
   ↳ No critical issues detected

🤖 Agent Roster (Top 5 by Activity):
┌─────────────────────┬──────────────────┬────────────┬─────────────┬─────────────┐
│ Agent Name          │ Capabilities     │ Status     │ Response    │ Workload    │
├─────────────────────┼──────────────────┼────────────┼─────────────┼─────────────┤
│ elastic1-specialist │ elasticsearch    │ ✓ Online   │ 180ms       │ ░░░░░░░░░░  │
│ lance-dev-agent     │ coordination     │ ✓ Online   │ 120ms       │ ███░░░░░░░  │
│ security-analyst    │ security         │ ✓ Online   │ 290ms       │ ░░░░░░░░░░  │
│ mysql-specialist    │ database_ops     │ ✓ Online   │ 340ms       │ █░░░░░░░░░  │
│ monitoring-agent    │ monitoring       │ ✓ Online   │ 205ms       │ ██░░░░░░░░  │
└─────────────────────┴──────────────────┴────────────┴─────────────┴─────────────┘

💾 Memory Statistics:
   ↳ Total Memories: 8,742 (↑ 127 today)
   ↳ Storage Usage: 2.3 GB / 50 GB (4.6%)
   ↳ Categories: Infrastructure 35%, Incidents 28%, Security 18%, Other 19%
   ↳ Redis Cache: 89% hit rate, 512 MB used

🌐 Network Health:
   ↳ Tailscale: ✓ Connected to 11 nodes  
   ↳ MCP Servers: ✓ All endpoints responding
   ↳ Sync Status: ✓ Last sync 14 minutes ago
   ↳ Certificate: Valid until 2025-06-15

📊 Recent Activity (Last 24h):
   ↳ Broadcasts: 23 (↑ 8 from yesterday)
   ↳ Delegations: 45 (↑ 12 from yesterday)
   ↳ Queries: 156 (↓ 3 from yesterday)
   ↳ Memory Stores: 89 (↑ 15 from yesterday)

⚠️  Warnings:
   ↳ elastic2 response time increased 40% (480ms avg)
   ↳ Memory growth rate above normal (↑ 18% this week)

💡 Recommendations:
   ↳ Consider restarting elastic2 agent to improve response time
   ↳ Schedule memory cleanup for memories older than 6 months
   ↳ Monitor tony-dev and mike-dev connectivity issues
```

### Agents-Only View
```
🤖 hAIveMind Agent Roster - 2025-01-24 14:30:00

📋 12 Active Agents | 2 Offline | 14 Total Registered

🟢 ONLINE AGENTS:
┌─────────────────────┬──────────────────────────────┬─────────────┬─────────────┬─────────────┐
│ Agent               │ Capabilities                 │ Response    │ Workload    │ Last Task   │
├─────────────────────┼──────────────────────────────┼─────────────┼─────────────┼─────────────┤
│ lance-dev-agent     │ coordination, infrastructure │ 120ms       │ ███░░░░░░░  │ 12 min ago  │
│ elastic1-specialist │ elasticsearch_ops, cluster  │ 180ms       │ ░░░░░░░░░░  │ 45 min ago  │
│ security-analyst    │ security, incident_response  │ 290ms       │ ░░░░░░░░░░  │ 2 hours ago │
│ mysql-specialist    │ database_ops, optimization  │ 340ms       │ █░░░░░░░░░  │ 30 min ago  │
│ monitoring-agent    │ monitoring, alerting        │ 205ms       │ ██░░░░░░░░  │ 8 min ago   │
│ proxy1-agent        │ scraping, data_collection   │ 410ms       │ ████░░░░░░  │ 3 min ago   │
│ auth-specialist     │ security, authentication    │ 198ms       │ ░░░░░░░░░░  │ 1 hour ago  │
│ grafana-agent       │ monitoring, visualization   │ 234ms       │ █░░░░░░░░░  │ 25 min ago  │
│ elastic3-specialist │ elasticsearch_ops           │ 267ms       │ ░░░░░░░░░░  │ 18 min ago  │
│ dev-coordinator     │ development, code_review    │ 156ms       │ ░░░░░░░░░░  │ 1.5 hr ago  │
│ kafka-specialist    │ data_processing, streaming  │ 445ms       │ ███░░░░░░░  │ 22 min ago  │
│ redis-specialist    │ caching, performance        │ 189ms       │ ░░░░░░░░░░  │ 38 min ago  │
└─────────────────────┴──────────────────────────────┴─────────────┴─────────────┴─────────────┘

🔴 OFFLINE AGENTS:
   ↳ tony-dev (development) - Last seen: 6 hours ago
   ↳ mike-dev (development) - Last seen: 2 days ago

🎯 CAPABILITY DISTRIBUTION:
   ↳ Development: 3 agents (2 offline)
   ↳ Infrastructure: 4 agents  
   ↳ Database: 3 agents
   ↳ Security: 2 agents
   ↳ Monitoring: 2 agents
   ↳ Data Processing: 2 agents

✨ TOP PERFORMERS (Last 24h):
   1. lance-dev-agent: 23 tasks completed
   2. monitoring-agent: 18 tasks completed  
   3. proxy1-agent: 15 tasks completed
```

### Memory Statistics Detail
```
💾 hAIveMind Memory Statistics - 2025-01-24 14:30:00

📊 STORAGE OVERVIEW:
   ↳ Total Memories: 8,742 items
   ↳ Storage Size: 2.3 GB (compressed)
   ↳ Growth Rate: +127 memories today (+18% this week)
   ↳ Oldest Memory: 2024-06-15 (223 days ago)

📚 CATEGORY BREAKDOWN:
┌─────────────────┬─────────┬─────────────┬─────────────┬─────────────────┐
│ Category        │ Count   │ Size (MB)   │ Avg Size    │ Growth (7 days) │
├─────────────────┼─────────┼─────────────┼─────────────┼─────────────────┤
│ infrastructure  │ 3,059   │ 847         │ 284 KB      │ +156 (+5.4%)    │
│ incidents       │ 2,448   │ 623         │ 261 KB      │ +89  (+3.8%)    │
│ security        │ 1,573   │ 412         │ 269 KB      │ +45  (+2.9%)    │
│ deployments     │ 874     │ 198         │ 232 KB      │ +23  (+2.7%)    │
│ monitoring      │ 523     │ 134         │ 263 KB      │ +34  (+7.0%)    │
│ runbooks        │ 265     │ 89          │ 344 KB      │ +12  (+4.7%)    │
└─────────────────┴─────────┴─────────────┴─────────────┴─────────────────┘

🏃 PERFORMANCE METRICS:
   ↳ Search Latency: 287ms average (↓ 15ms from last week)
   ↳ Insert Rate: 43.2 memories/hour
   ↳ Redis Hit Rate: 89.3% (excellent)
   ↳ Vector Index: 94.1% efficiency

🧹 CLEANUP STATUS:
   ↳ Last Cleanup: 2025-01-20 02:00:00
   ↳ Eligible for Cleanup: 234 memories (older than 180 days)
   ↳ Estimated Space Recovery: 67 MB
   ↳ Next Scheduled Cleanup: 2025-01-27 02:00:00

📈 TRENDING TOPICS (Last 7 days):
   1. elasticsearch performance (47 memories)
   2. security vulnerability patches (31 memories)
   3. database optimization (28 memories)
   4. network connectivity issues (22 memories)
   5. deployment automation (19 memories)
```

## Performance Metrics and Thresholds

### Agent Response Time Classifications
- **Excellent**: < 200ms (immediate response)
- **Good**: 200-400ms (normal operation)
- **Slow**: 400-800ms (potential issues)
- **Critical**: > 800ms (needs investigation)

### Memory Usage Thresholds
- **Normal**: < 60% of allocated storage
- **Warning**: 60-80% of allocated storage  
- **Critical**: > 80% of allocated storage
- **Emergency**: > 95% of allocated storage

### Network Health Indicators
- **All Green**: > 90% agents responsive
- **Warning**: 70-90% agents responsive
- **Degraded**: 50-70% agents responsive
- **Critical**: < 50% agents responsive

## Common Status Issues and Solutions

### Offline Agents
```
🔴 OFFLINE: elastic2-specialist (Last seen: 2 hours ago)
💡 Troubleshooting Steps:
   1. Check machine connectivity: ping elastic2
   2. Verify MCP server: curl http://elastic2:8900/health
   3. Check system resources: ssh elastic2 'top -bn1'
   4. Restart services: ssh elastic2 'sudo systemctl restart memory-mcp-server'
```

### High Memory Usage
```
⚠️  Memory usage at 78% (Warning threshold)
💡 Recommended Actions:
   1. Run memory cleanup: hv-sync clean --memory
   2. Archive old memories: memories older than 6 months
   3. Review memory retention policies
   4. Consider storage expansion if growth continues
```

### Network Connectivity Issues
```
❌ Tailscale connectivity degraded (67% nodes reachable)
💡 Diagnostic Steps:
   1. Check Tailscale status: tailscale status
   2. Restart Tailscale: sudo systemctl restart tailscaled
   3. Verify routing: tailscale ping elastic1
   4. Check firewall rules on affected machines
```

### Poor Performance
```
🐌 Average response time: 847ms (Above normal threshold)
💡 Performance Optimization:
   1. Check system resources on slow agents
   2. Review network latency between machines
   3. Consider Redis cache optimization
   4. Restart high-latency agents
```

## Best Practices for Status Monitoring
- **Daily Checks**: Run `hv-status` as part of daily routine
- **Performance Baselines**: Track response times and memory growth trends
- **Proactive Maintenance**: Address warnings before they become critical
- **Automation**: Use `--json` output for automated monitoring scripts
- **Documentation**: Record recurring issues and solutions in collective memory

## Related Commands
- **After finding issues**: Use `hv-delegate` to assign resolution tasks
- **For connectivity issues**: Use `hv-sync` to refresh configurations
- **Performance problems**: Use `hv-query` to find similar past incidents
- **Share findings**: Use `hv-broadcast` to inform collective about status changes

## Troubleshooting Status Command Issues

### Command Not Responding
1. Check local MCP server: `curl http://localhost:8900/health`
2. Verify Redis connectivity: `redis-cli ping`
3. Check system resources: `top`, `df -h`, `free -m`
4. Restart local services if needed

### Incomplete Data
1. Some agents may be temporarily unreachable (normal)
2. Network partitions can affect data collection
3. Check Tailscale connectivity to affected machines
4. Wait 1-2 minutes and retry for transient issues

### Outdated Information
1. Status data cached for 60 seconds for performance
2. Use `--detailed` to force fresh data collection
3. Check last sync timestamp in output
4. Network delays may affect data freshness

---

This command provides comprehensive health monitoring for the hAIveMind collective, helping you maintain optimal performance and quickly identify issues requiring attention.