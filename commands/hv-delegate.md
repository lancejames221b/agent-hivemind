---
description: Delegate tasks to specialized hAIveMind agents based on expertise
argument-hint: "task description" [priority] [required_capabilities]
allowed-tools: ["mcp__haivemind__delegate_task", "mcp__haivemind__get_agent_roster"]
---

# hv-delegate - Smart Task Assignment

## Purpose
Intelligently assign tasks to the most suitable agents in the hAIveMind collective based on expertise, availability, and current workload.

## When to Use
- **Complex Infrastructure Tasks**: Database optimization, server configuration, network troubleshooting
- **Security Analysis**: Vulnerability assessments, incident response, penetration testing
- **Code Reviews**: Pull request analysis, architecture decisions, performance optimization
- **Data Processing**: ETL operations, scraping tasks, data validation
- **Monitoring Setup**: Alert configuration, dashboard creation, metrics analysis
- **Deployment Operations**: Service updates, rollbacks, configuration management

## Syntax
```
hv-delegate "task description" [priority] [required_capabilities]
```

## Parameters
- **task description** (required): Clear, specific description of what needs to be done
- **priority** (optional): Task urgency (defaults to `medium`)
  - `critical`: Immediate attention, blocks other work
  - `high`: Important, complete within hours
  - `medium`: Standard priority, complete within days
  - `low`: Nice-to-have, complete when available
- **required_capabilities** (optional): Comma-separated list of required skills
  - `elasticsearch_ops`, `database_ops`, `security_analysis`
  - `infrastructure_management`, `monitoring`, `development`
  - `scraping`, `data_processing`, `code_review`

## Agent Capability Matching

### Infrastructure Specialists (`lance-dev`, `elastic1-5`)
- **Capabilities**: `infrastructure_management`, `elasticsearch_ops`, `cluster_management`
- **Best For**: Server configuration, elasticsearch tuning, cluster operations
- **Response Time**: Usually < 30 minutes for critical issues

### Database Specialists (`mysql`, `mongodb`, `kafka`)  
- **Capabilities**: `database_ops`, `backup_restore`, `query_optimization`
- **Best For**: Database tuning, backup/restore, performance optimization
- **Response Time**: Usually < 1 hour for database issues

### Security Analysts (`auth-server`, security-focused agents)
- **Capabilities**: `security_analysis`, `incident_response`, `vulnerability_assessment`
- **Best For**: Security reviews, incident response, vulnerability analysis
- **Response Time**: Usually < 15 minutes for security incidents

### Data Processors (`proxy0-9`, scraping agents)
- **Capabilities**: `data_collection`, `scraping`, `proxy_management`
- **Best For**: Web scraping, data extraction, proxy configuration
- **Response Time**: Usually < 2 hours for data tasks

### Monitoring Specialists (`grafana`, monitoring agents)
- **Capabilities**: `monitoring`, `alerting`, `incident_response`
- **Best For**: Dashboard creation, alert setup, metric analysis
- **Response Time**: Usually < 1 hour for monitoring tasks

## Real-World Examples

### Database Performance Issue
```
hv-delegate "Optimize slow queries on mysql-primary causing 5s response times" critical database_ops,query_optimization
```
**Result**: Task assigned to mysql specialist agent with database expertise, gets immediate attention

### Security Vulnerability Assessment
```
hv-delegate "Review auth service for potential OWASP Top 10 vulnerabilities" high security_analysis
```
**Result**: Security analyst agent performs comprehensive vulnerability scan and reports findings

### Infrastructure Scaling
```
hv-delegate "Configure auto-scaling for elasticsearch cluster during peak hours" medium elasticsearch_ops,infrastructure_management
```
**Result**: Infrastructure specialist creates scaling policies and monitoring rules

### Data Processing Pipeline
```
hv-delegate "Set up data validation pipeline for incoming scraper feeds" low data_processing,monitoring
```
**Result**: Data processing agent creates validation rules and monitoring dashboards

### Code Review Request
```
hv-delegate "Review authentication refactoring PR for security best practices" high code_review,security_analysis
```
**Result**: Both development and security agents collaborate on comprehensive review

## Expected Output
```
✓ Task analyzed and categorized
✓ Found 3 agents with matching capabilities:
  - elastic1-specialist (elasticsearch_ops, infrastructure_management) [Available]
  - lance-dev-agent (infrastructure_management, monitoring) [Busy - ETA 2h]
  - monitoring-agent (monitoring, alerting) [Available]
✓ Task assigned to: elastic1-specialist
✓ Priority set: critical
✓ Estimated completion: 30 minutes
✓ Task ID: task-20250124-003
✓ Agent notified and acknowledged task
```

## Success Indicators
- Multiple candidate agents found with matching capabilities
- Best agent selected based on availability and expertise match
- Task acknowledged by assigned agent
- Realistic completion time estimate provided
- Task ID generated for tracking

## Task Assignment Algorithm
1. **Capability Matching**: Find agents with required skills
2. **Availability Check**: Exclude overloaded or offline agents
3. **Expertise Scoring**: Rank agents by relevant experience
4. **Workload Balancing**: Consider current task queue length
5. **Response History**: Favor agents with good completion rates
6. **Geographic/Network**: Prefer agents with good network connectivity

## Common Error Scenarios

### No Suitable Agents Available
```
❌ Error: No agents found with required capabilities: [rare_skill]
→ Suggestions:
  - Check if capability name is spelled correctly
  - Use hv-status to see all available capabilities
  - Consider delegating to general-purpose agent
  - Break task into smaller parts with common capabilities
```

### All Agents Busy
```
❌ Warning: All capable agents currently busy
✓ Task queued for next available agent
✓ Estimated wait time: 2 hours
✓ Will notify when agent becomes available
```

### Agent Declined Task
```
❌ Agent declined: Insufficient context provided
→ Provide more specific task description
→ Include relevant system names, file paths, or error messages
→ Specify expected deliverables
```

## Performance Considerations
- **Delegation Latency**: ~500ms to analyze task and find suitable agent
- **Agent Response**: Most agents acknowledge within 30 seconds
- **Queue Processing**: High-priority tasks bypass normal queue order
- **Multi-Agent Tasks**: Complex tasks may automatically create sub-delegations

## Related Commands
- **Before delegating**: Use `hv-status` to check agent availability
- **After delegating**: Use `hv-query` to check task progress  
- **For updates**: Use `recall` to find previous similar task resolutions
- **For coordination**: Use `hv-broadcast` to share task results with collective

## Workflow Integration

### Incident Response Workflow
1. Identify issue requiring specialized expertise
2. `hv-delegate` to appropriate specialist with critical priority
3. `hv-broadcast` resolution findings to collective
4. `remember` solution for future similar incidents

### Development Task Workflow
1. `hv-delegate` code review to development agents
2. `hv-delegate` security analysis to security agents  
3. Coordinate feedback from multiple specialist perspectives
4. `hv-broadcast` approved patterns for future use

### Infrastructure Change Workflow
1. `hv-delegate` implementation to infrastructure specialists
2. `hv-delegate` monitoring setup to monitoring agents
3. `hv-delegate` testing to development agents
4. `hv-status` to verify all delegated tasks completed

## Troubleshooting

### Task Stalled or Incomplete
1. Use `hv-query [agent-name]` to check task status
2. Re-delegate with higher priority if urgent
3. Check if agent needs additional context or permissions
4. Consider breaking large tasks into smaller components

### Wrong Agent Assignment  
1. Agent may auto-delegate to more suitable specialist
2. Use `hv-status` to see why initial matching occurred
3. Provide more specific capability requirements
4. Consider if task description was unclear

### Multi-Agent Coordination Issues
1. Tasks requiring multiple agents may need manual coordination
2. Use `hv-broadcast` to share context between collaborating agents
3. Set clear deliverable expectations for each agent
4. Monitor progress with `hv-status` and intervene if needed

## Best Practices
- **Be Specific**: Include system names, error messages, expected outcomes
- **Set Appropriate Priority**: Don't mark everything as critical
- **Provide Context**: Link to relevant logs, configurations, or documentation
- **Follow Up**: Check progress on critical tasks, don't just delegate and forget
- **Learn from Results**: Use successful delegations as templates for future tasks
- **Coordinate Complex Tasks**: Break large tasks into clear, delegatable components

---

**Delegate Task**: $ARGUMENTS

The system will automatically analyze this task, identify the most suitable agents based on required capabilities and availability, and coordinate the assignment with progress tracking and result sharing across the collective.