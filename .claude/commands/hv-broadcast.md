---
description: Broadcast critical findings to all hAIveMind collective agents
argument-hint: message category severity (e.g., "Database deadlock resolved" infrastructure warning)
allowed-tools: ["mcp__haivemind__broadcast_discovery"]
---

# hv-broadcast - Share Critical Findings

## Purpose
Broadcast important discoveries, incidents, or findings to all agents in the hAIveMind collective for immediate awareness and coordinated response.

## When to Use
- **Security Vulnerabilities**: Found SQL injection, unauthorized access, or security breaches
- **Infrastructure Changes**: Load balancer updates, service migrations, configuration changes  
- **Incident Resolutions**: Database deadlocks, service outages, performance issues resolved
- **Best Practices**: Lessons learned, successful procedures, optimization techniques
- **Resource Alerts**: High CPU usage, memory leaks, storage capacity warnings
- **Deployment Updates**: New releases, rollbacks, service updates

## Syntax
```
hv-broadcast "[message]" [category] [severity]
```

## Parameters
- **message** (required): Clear, actionable description of the finding
- **category** (required): Type of finding
  - `security`: Security vulnerabilities, breaches, patches
  - `infrastructure`: Server changes, network updates, configuration
  - `incident`: Service outages, performance issues, failures
  - `deployment`: Releases, rollbacks, updates
  - `monitoring`: Alerts, metrics, threshold breaches
  - `runbook`: Procedures, scripts, operational updates
- **severity** (optional): Urgency level (defaults to `info`)
  - `critical`: Immediate action required, system-wide impact
  - `warning`: Attention needed, potential impact
  - `info`: General awareness, no immediate action

## Real-World Examples

### Security Finding
```
hv-broadcast "SQL injection vulnerability found in auth service /login endpoint - patch deployed" security critical
```
**Result**: All security-focused agents immediately begin vulnerability assessment across similar endpoints

### Infrastructure Update  
```
hv-broadcast "Load balancer configuration updated with health check intervals changed to 30s" infrastructure info
```
**Result**: Monitoring agents adjust alerting thresholds, database agents expect different connection patterns

### Incident Resolution
```
hv-broadcast "Database deadlock issue resolved with connection pooling optimization" incident warning
```
**Result**: Database specialists store solution in runbooks, monitoring agents update deadlock alerts

### Performance Discovery
```
hv-broadcast "Memory leak in scraper service traced to unclosed HTTP connections" infrastructure warning
```
**Result**: All scraper agents implement connection cleanup, monitoring agents add memory tracking

### Resource Alert
```
hv-broadcast "elasticsearch cluster CPU usage sustained above 80% on elastic1-3" monitoring warning
```
**Result**: Infrastructure agents begin capacity planning, elasticsearch specialists investigate query optimization

## Expected Output
```
✓ Broadcast sent to 12 active agents
✓ Message stored in collective memory (ID: b-20250124-001)
✓ Categorized as: infrastructure/warning
✓ Notified agents: elastic1-specialist, monitoring-agent, security-analyst, ...
✓ Related memories: 3 similar incidents found and linked
```

## Success Indicators
- Agent count confirmation (shows network health)
- Memory storage confirmation with unique ID
- Proper categorization applied
- List of notified specialized agents
- Automatic correlation with related memories

## Common Error Scenarios

### Network Connectivity Issues
```
❌ Error: Failed to reach 3 of 12 agents (elastic2, proxy1, dev-env)
→ Check Tailscale connectivity: tailscale status
→ Verify agent registration: hv-status
```

### Invalid Category
```
❌ Error: Unknown category 'database' - use infrastructure, security, incident, deployment, monitoring, or runbook
→ Use 'infrastructure' for database-related findings
```

### Message Too Vague
```
❌ Warning: Message lacks actionable detail - other agents may not understand context
→ Include specific system names, error codes, or resolution steps
```

## Performance Considerations
- **Broadcast Latency**: ~200ms to reach all agents via Tailscale network
- **Memory Storage**: Each broadcast consumes ~1KB in collective memory
- **Agent Processing**: High-severity broadcasts may trigger automatic responses
- **Network Impact**: Critical broadcasts may cause spike in agent-to-agent queries

## Related Commands
- **Before broadcasting**: Use `hv-query` to check if issue is already known
- **After broadcasting**: Use `hv-delegate` to assign specific remediation tasks  
- **For follow-up**: Use `hv-status` to confirm all agents received the broadcast
- **For verification**: Use `recall` to verify message was stored correctly

## Workflow Integration

### Security Incident Workflow
1. Discover vulnerability
2. `hv-broadcast` with security/critical
3. `hv-delegate` patch deployment to infrastructure agents
4. `hv-query` to verify patches applied across all systems
5. `remember` final resolution for future reference

### Infrastructure Change Workflow  
1. Plan infrastructure change
2. `hv-broadcast` with infrastructure/info (advance notice)
3. Execute change
4. `hv-broadcast` with infrastructure/warning (completion notice)
5. `hv-status` to verify all agents acknowledged change

## Troubleshooting

### Broadcast Not Received
1. Check network connectivity: `tailscale ping [agent-machine]`
2. Verify agent registration: `hv-status` 
3. Check agent logs for processing errors
4. Retry with verbose flag if available

### Categorization Issues
- Use `infrastructure` for any hardware, network, or system configuration changes
- Use `incident` for service disruptions, outages, or performance degradation
- Use `security` only for actual vulnerabilities, not general security improvements
- Use `monitoring` for alerting changes, threshold updates, or metric discoveries

## Best Practices
- **Be Specific**: Include system names, error codes, impact scope
- **Be Timely**: Broadcast critical issues immediately upon discovery
- **Be Actionable**: Other agents should understand what to do with the information
- **Use Severity Appropriately**: Don't overwhelm with non-critical broadcasts
- **Follow Up**: Check that appropriate agents responded to critical broadcasts

---

**Broadcast Message**: $ARGUMENTS

This message will be distributed to all active hAIveMind agents with automatic categorization, severity assessment, and correlation with existing knowledge in the collective memory system.