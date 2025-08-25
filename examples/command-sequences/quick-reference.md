# hAIveMind Quick Reference Guide

## Common Command Sequences

### Emergency Response (5 minutes)
```bash
# Critical security incident
remember "CRITICAL: [incident details]" security --important
hv-broadcast "[incident summary]" security critical
hv-delegate "[immediate action needed]" critical security_analysis

# System outage
remember "OUTAGE: [system] down - [impact]" incidents --important
hv-broadcast "[system] outage - investigating" incident critical
hv-delegate "Restore [system] service" critical infrastructure_management
```

### Daily Operations (15-30 minutes)
```bash
# Morning health check
hv-status --detailed
hv-sync status
recall "issues" incidents --recent=24

# Performance monitoring
hv-query "performance metrics [system]" monitoring --recent=24
hv-status --agents

# Knowledge sharing
remember "[daily learning or solution]" [category] --tags="[relevant-tags]"
hv-broadcast "[important update]" [category] info
```

### Investigation Workflow (1-2 hours)
```bash
# Problem investigation
remember "[problem description and context]" incidents --tags="[system],[issue-type]"
hv-query "[similar problems]" incidents --recent=720
hv-delegate "Investigate [specific aspect]" high [relevant-capability]
hv-status --agents
recall "[investigation results]" --recent=2
```

### Deployment Workflow (2-4 hours)
```bash
# Pre-deployment
hv-sync force --verbose
hv-status --agents --detailed
remember "[deployment plan]" deployments --important
hv-broadcast "Deployment starting" deployments warning

# Execution
hv-delegate "[deployment tasks]" critical deployment
hv-status --detailed
hv-delegate "Validate deployment" high testing

# Post-deployment
remember "[deployment results]" deployments --tags="results"
hv-broadcast "Deployment completed" deployments info
```

## Command Patterns by Role

### Infrastructure Engineer
```bash
# Server maintenance
remember "Server maintenance: [details]" infrastructure
hv-broadcast "Maintenance window starting" infrastructure warning
hv-delegate "Execute maintenance tasks" high infrastructure_management
hv-status --network

# Capacity planning
hv-query "capacity trends [system]" infrastructure --recent=720
remember "Capacity analysis: [findings]" infrastructure --tags="capacity"
hv-delegate "Implement scaling solution" medium infrastructure_management
```

### Security Analyst
```bash
# Vulnerability assessment
remember "Vulnerability found: [details]" security --important
hv-query "similar vulnerabilities" security --recent=2160
hv-delegate "Assess vulnerability impact" high security_analysis
hv-broadcast "Security advisory" security warning

# Compliance check
hv-query "compliance requirements [standard]" security
remember "Compliance status: [findings]" security --tags="compliance"
hv-delegate "Address compliance gaps" medium security_analysis
```

### Database Administrator
```bash
# Performance tuning
remember "Database performance issue: [symptoms]" incidents
hv-query "database optimization [database-type]" infrastructure
hv-delegate "Optimize database performance" high database_ops
remember "Optimization results: [improvements]" infrastructure

# Backup verification
hv-query "backup procedures [database]" runbooks
hv-delegate "Verify backup integrity" medium database_ops
remember "Backup status: [results]" infrastructure --tags="backup"
```

### Development Team Lead
```bash
# Code review coordination
remember "Code review needed: [PR details]" project
hv-delegate "Review code quality" medium code_review
hv-delegate "Security review" high security_analysis
remember "Review results: [findings]" project --tags="code-review"

# Architecture decisions
remember "Architecture decision: [context]" project --important
hv-query "similar architecture decisions" project --recent=4320
hv-broadcast "Architecture discussion" project info
remember "Decision: [outcome and rationale]" project --tags="architecture"
```

## Troubleshooting Quick Fixes

### Commands Not Responding
```bash
hv-status --detailed
hv-sync force --verbose
hv-sync clean  # If force sync fails
```

### Agents Offline
```bash
hv-status --agents --network
# Check Tailscale connectivity
hv-sync --verbose
hv-broadcast "Network connectivity issues" infrastructure warning
```

### Memory/Storage Issues
```bash
hv-status --memory
recall "cleanup procedures" runbooks
hv-delegate "Clean up old memories" low infrastructure_management
```

### Sync Failures
```bash
hv-sync status
hv-sync clean --verbose
hv-status --network
```

## Time-Based Command Patterns

### Immediate (< 5 minutes)
- `remember` critical information
- `hv-broadcast` urgent alerts
- `hv-status` quick health check
- `hv-delegate` critical tasks

### Short-term (5-30 minutes)
- `hv-query` for research
- `hv-sync` for updates
- `recall` for recent information
- Multiple `hv-delegate` for parallel work

### Medium-term (30 minutes - 2 hours)
- Complex investigation workflows
- Multi-agent coordination
- Detailed analysis and documentation
- Implementation and validation

### Long-term (2+ hours)
- Major deployments
- Comprehensive security reviews
- Architecture decisions
- System migrations

## Efficiency Tips

### Batch Operations
```bash
# Good: Parallel delegation
hv-delegate "Task A" high capability1 &
hv-delegate "Task B" high capability2 &
hv-delegate "Task C" medium capability3 &

# Good: Combined queries
hv-query "topic" category1 --recent=24
hv-query "related topic" category2 --recent=24
```

### Smart Tagging
```bash
# Use consistent, searchable tags
remember "solution" category --tags="system,issue-type,solution"
remember "config change" infrastructure --tags="nginx,ssl,production"
```

### Context Preservation
```bash
# Always include context in memories
remember "Problem: [what] Context: [when/where] Solution: [how] Result: [outcome]"
```

### Follow-up Patterns
```bash
# After delegation, always monitor
hv-delegate "task" priority capability
# Wait appropriate time
hv-status --agents
# Check results
recall "task results" --recent=1
```

## Common Mistakes to Avoid

❌ **Don't**: Delegate without checking agent availability
✅ **Do**: `hv-status --agents` before `hv-delegate`

❌ **Don't**: Broadcast without documenting first
✅ **Do**: `remember` then `hv-broadcast`

❌ **Don't**: Use vague descriptions
✅ **Do**: Include specific systems, errors, timelines

❌ **Don't**: Forget to document outcomes
✅ **Do**: Always `remember` results and lessons learned

❌ **Don't**: Skip querying existing knowledge
✅ **Do**: `hv-query` before starting new investigations

❌ **Don't**: Work in isolation
✅ **Do**: Use `hv-broadcast` to keep collective informed