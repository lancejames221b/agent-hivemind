---
description: Show contextual examples for hAIveMind commands with real-world scenarios
allowed-tools: ["help_examples"]
argument-hint: [command] [context]
---

# examples - Contextual Command Examples

## Purpose
Intelligent example system that shows relevant, real-world usage scenarios for hAIveMind commands, automatically adapted to your current project type, active incidents, and usage patterns.

## When to Use
- **Learning Commands**: See practical examples of how commands work in real situations
- **Troubleshooting**: Find examples similar to your current problem
- **Best Practices**: Discover optimal usage patterns from successful implementations
- **Context Adaptation**: Get examples relevant to your specific environment
- **Workflow Planning**: See how commands fit into larger operational workflows
- **Parameter Guidance**: Understand proper parameter usage through examples

## Syntax
```
examples [command] [context]
```

## Parameters
- **command** (optional): Specific command to show examples for
  - Examples: `hv-broadcast`, `hv-delegate`, `remember`, `recall`
- **context** (optional): Situation or domain to find relevant examples
  - Examples: `incident`, `security`, `deployment`, `monitoring`, `python`, `nodejs`

## Intelligent Example Features

### Context-Aware Selection
- **Project Type Detection**: Shows examples relevant to Python, Node.js, Rust, Go projects
- **Incident Response**: Prioritizes emergency response examples during active incidents
- **Usage History**: Adapts examples based on your recent command patterns
- **Success Patterns**: Highlights examples from successful past operations
- **Complexity Matching**: Shows examples appropriate to your experience level

### Real-World Scenarios
- **Production Incidents**: Actual incident response workflows and resolutions
- **Security Events**: Real security vulnerability handling and patch deployment
- **Infrastructure Changes**: Live infrastructure updates and configuration changes
- **Performance Issues**: Database optimization, memory leak fixes, scaling operations
- **Deployment Workflows**: CI/CD pipeline integration and rollback procedures

## Real-World Examples

### Command-Specific Examples
```
examples hv-broadcast
```
**Result**: Comprehensive examples of hv-broadcast usage across different scenarios (security alerts, infrastructure changes, incident updates)

### Context-Based Examples
```
examples incident
```
**Result**: All commands relevant to incident response with step-by-step examples and expected outcomes

### Current Context Examples
```
examples
```
**Result**: Examples automatically selected based on your current project type, recent commands, and active incidents

### Security Context Examples
```
examples security
```
**Result**: Security-focused examples including vulnerability reporting, patch deployment, and incident response

### Project-Specific Examples
```
examples python
```
**Result**: Examples tailored to Python development workflows, deployment patterns, and common infrastructure needs

## Expected Output

### Command-Specific Examples
```
💡 Command Examples: hv-broadcast

🔍 Query: command=hv-broadcast, context=auto-detected
📊 Showing: 8 examples (12 total available)

🎯 Context Info:
   ↳ Project Type: Python
   ↳ Recent Commands: hv-query, hv-status, remember
   ↳ Active Incidents: 1 (database connectivity)

📚 Examples (Ranked by Relevance):

1. 🚨 Critical Security Alert
   Command: hv-broadcast "SQL injection vulnerability patched in auth service" security critical
   Expected Result: ✓ All 12 agents notified, security team activated, patch verification initiated
   Context: Production security incident requiring immediate team coordination

2. 🔧 Infrastructure Update Notification
   Command: hv-broadcast "Database connection pool increased to 50 connections" infrastructure info
   Expected Result: ✓ Monitoring agents update thresholds, application teams adjust expectations
   Context: Proactive infrastructure scaling to prevent connection exhaustion

3. 📊 Performance Issue Resolution
   Command: hv-broadcast "Memory leak in Python scraper service fixed via connection cleanup" infrastructure warning
   Expected Result: ✓ All scraper agents implement fix, monitoring agents add memory tracking
   Context: Performance degradation resolved through code optimization

4. 🚀 Deployment Completion
   Command: hv-broadcast "API v2.1.3 deployed successfully across all environments" deployment info
   Expected Result: ✓ Testing teams notified, monitoring agents update version tracking
   Context: Successful production deployment requiring team awareness

5. 🔍 Incident Status Update
   Command: hv-broadcast "Database connectivity restored, investigating root cause" incident warning
   Expected Result: ✓ All agents aware of status change, investigation team coordinated
   Context: Active incident resolution with ongoing investigation

6. 🛡️ Security Patch Deployment
   Command: hv-broadcast "OpenSSL security patches applied to all web servers" security info
   Expected Result: ✓ Security team confirms coverage, compliance team updates records
   Context: Routine security maintenance with compliance requirements

7. 📈 Monitoring Threshold Update
   Command: hv-broadcast "CPU alert threshold raised to 85% after infrastructure upgrade" monitoring info
   Expected Result: ✓ All monitoring agents update alerting rules, false positives reduced
   Context: Monitoring optimization following infrastructure improvements

8. 🔄 Runbook Update
   Command: hv-broadcast "New database failover procedure documented and tested" runbook info
   Expected Result: ✓ All database specialists access updated procedures, training scheduled
   Context: Operational procedure improvement for better incident response

💡 Pro Tips:
   ↳ Use 'critical' severity sparingly - reserve for system-wide emergencies
   ↳ Include specific system names and impact scope in messages
   ↳ Follow up with hv-delegate for specific remediation tasks
   ↳ Use hv-status to verify broadcast reached all intended agents

🔗 Related Examples:
   • examples hv-delegate  - Task assignment after broadcasting
   • examples incident     - Complete incident response workflows
   • examples security     - Security-focused communication patterns
```

### Context-Based Examples
```
💡 Context Examples: Incident Response

🔍 Query: context=incident, auto-adapted to current situation
📊 Showing: 10 examples (15 total available)

🎯 Current Context:
   ↳ Active Incidents: 1 (database connectivity issues)
   ↳ Project Type: Python application
   ↳ Recent Activity: Database troubleshooting, performance monitoring

📚 Incident Response Examples:

1. 🚨 Initial Incident Detection and Alert
   Workflow: hv-status → hv-broadcast → hv-delegate
   
   Step 1: hv-status --detailed
   Result: Identifies 3 database agents offline, high response times
   
   Step 2: hv-broadcast "Database connectivity issues detected, investigating" incident critical
   Result: All 12 agents notified, incident response team activated
   
   Step 3: hv-delegate "Investigate database connection pool exhaustion" database_ops
   Result: Database specialists assigned, investigation begins

2. 🔧 Service Degradation Response
   Command Sequence: hv-query → remember → hv-broadcast
   
   Step 1: hv-query "similar database connection issues last 30 days"
   Result: Found 3 similar incidents with documented solutions
   
   Step 2: remember "Database connection pool at 95% capacity, needs scaling" infrastructure
   Result: Issue documented for trend analysis
   
   Step 3: hv-broadcast "Database connection pool scaling in progress" incident warning
   Result: Team updated on remediation status

3. 🎯 Incident Resolution and Documentation
   Final Workflow: hv-broadcast → remember → hv-delegate
   
   Step 1: hv-broadcast "Database connectivity restored via connection pool restart" incident info
   Result: All agents notified of resolution
   
   Step 2: remember "Root cause: connection pool memory leak, fixed via restart + monitoring" incidents
   Result: Solution documented for future reference
   
   Step 3: hv-delegate "Implement connection pool monitoring alerts" monitoring
   Result: Prevention measures assigned to monitoring team

4. 🔍 Multi-System Incident Coordination
   Complex Scenario: Load balancer + database + application issues
   
   Commands Used:
   • hv-status --network (check connectivity)
   • hv-broadcast "Multi-system outage detected" incident critical
   • hv-delegate "Check load balancer health" infrastructure_management
   • hv-delegate "Investigate database locks" database_ops
   • hv-delegate "Review application error logs" development
   • hv-query "multi-system outage procedures"
   • remember "Cascading failure: LB timeout → DB locks → app errors" incidents

5. 🚀 Emergency Rollback Procedure
   Deployment Gone Wrong:
   
   Step 1: hv-broadcast "Deployment v2.1.4 causing 500 errors, initiating rollback" deployment critical
   Step 2: hv-delegate "Execute rollback to v2.1.3" deployment
   Step 3: hv-status --detailed (verify rollback success)
   Step 4: hv-broadcast "Rollback completed, service restored" deployment info
   Step 5: remember "v2.1.4 rollback due to database migration issue" deployments

💡 Incident Response Best Practices:
   ↳ Always start with hv-status to assess scope
   ↳ Use 'critical' severity for customer-impacting issues
   ↳ Delegate specific tasks to appropriate specialists
   ↳ Document resolution immediately while details are fresh
   ↳ Follow up with prevention measures and monitoring

🔗 Related Workflows:
   • examples security     - Security incident procedures
   • examples monitoring   - Proactive issue detection
   • workflows            - Complete incident response templates
```

### Auto-Context Examples
```
💡 Smart Context Examples

🔍 Auto-detected context based on your current situation:
📊 Showing: 6 examples (20 total available)

🎯 Context Analysis:
   ↳ Project: Python application with database components
   ↳ Recent Commands: hv-query (database issues), hv-status, remember
   ↳ Active Concerns: Database performance, connection management
   ↳ Suggested Focus: Database optimization and monitoring

📚 Contextual Examples:

1. 🐍 Python Application Database Optimization
   Scenario: High database connection usage in Python app
   
   Command: remember "Python connection pooling configured with SQLAlchemy, max_overflow=20" infrastructure
   Context: Documenting database configuration for team reference
   Follow-up: hv-broadcast "Database connection optimization implemented" infrastructure info

2. 📊 Database Performance Monitoring
   Scenario: Setting up proactive database monitoring
   
   Command: hv-delegate "Implement database connection pool monitoring" monitoring
   Context: Preventing connection exhaustion issues
   Follow-up: hv-query "database monitoring best practices"

3. 🔍 Troubleshooting Database Issues
   Scenario: Investigating slow database queries
   
   Workflow:
   • hv-query "slow database query optimization techniques"
   • hv-delegate "Analyze slow query logs" database_ops
   • remember "Query optimization reduced response time by 60%" infrastructure

4. 🚨 Database Incident Response
   Scenario: Database connection pool exhaustion
   
   Emergency Workflow:
   • hv-status --detailed (check database agent availability)
   • hv-broadcast "Database connection pool at capacity" incident warning
   • hv-delegate "Restart database connection pool" database_ops
   • remember "Connection pool restart resolved issue temporarily" incidents

5. 🔧 Python Deployment with Database Migration
   Scenario: Deploying Python app with database schema changes
   
   Deployment Sequence:
   • hv-broadcast "Starting deployment with database migration" deployment info
   • hv-delegate "Execute database migration scripts" database_ops
   • hv-status (verify migration success)
   • hv-broadcast "Deployment completed successfully" deployment info

6. 📈 Performance Trend Analysis
   Scenario: Analyzing database performance over time
   
   Analysis Workflow:
   • recall "database performance metrics last 30 days" infrastructure
   • hv-query "database performance trends and patterns"
   • remember "Database response time increased 15% over month" monitoring
   • hv-delegate "Investigate database performance degradation" database_ops

💡 Smart Suggestions Based on Your Activity:
   ↳ Your recent hv-query suggests you're troubleshooting - consider hv-delegate next
   ↳ Database focus detected - examples prioritize database operations
   ↳ Python project context - examples include Python-specific considerations
   ↳ Recent remember usage - examples show documentation patterns

🎯 Recommended Next Steps:
   1. Use hv-delegate to assign database investigation tasks
   2. Set up monitoring with database specialists
   3. Document findings with remember for future reference
   4. Share solutions with hv-broadcast when resolved
```

## Advanced Example Features

### Learning and Adaptation
- **Success Tracking**: Prioritizes examples from successful past operations
- **Failure Analysis**: Shows examples of what to avoid based on past failures
- **Pattern Recognition**: Identifies common usage patterns and suggests similar examples
- **Effectiveness Scoring**: Ranks examples by how often they lead to successful outcomes
- **Collective Intelligence**: Learns from examples across all agents in the collective

### Integration with hAIveMind
- **Memory Integration**: Examples drawn from actual stored memories and experiences
- **Cross-Agent Learning**: Examples include successful patterns from other agents
- **Real-Time Adaptation**: Examples update based on current collective status
- **Performance Analytics**: Tracks which examples are most helpful
- **Continuous Improvement**: Example relevance improves based on user feedback

## Performance Considerations
- **Response Time**: < 300ms for example retrieval and ranking
- **Relevance Scoring**: AI-powered ranking based on context similarity
- **Cache Efficiency**: Frequently accessed examples cached for performance
- **Memory Usage**: Example content optimized for quick loading
- **Network Impact**: Minimal - examples served from local cache when possible

## Related Commands
- **After viewing examples**: Execute the commands shown in examples
- **For detailed help**: Use `help <command>` for comprehensive documentation
- **For workflows**: Use `workflows` to see complete operational procedures
- **For suggestions**: Use `suggest` for AI-powered command recommendations
- **For validation**: Use `help validate <command>` before executing examples

## Troubleshooting Examples System

### No Relevant Examples Found
```
❓ No examples found for your query
💡 Troubleshooting:
   1. Try broader context terms (e.g., 'incident' instead of 'database-incident')
   2. Use command names without prefixes (e.g., 'broadcast' instead of 'hv-broadcast')
   3. Check available contexts: examples (shows all available)
   4. Examples build over time - use commands to generate more examples
```

### Examples Seem Outdated
```
⚠️  Examples don't match current system state
💡 Resolution:
   1. Examples reflect actual usage - outdated examples indicate system changes
   2. Use current commands to generate fresh examples
   3. Check system updates: hv-sync
   4. Report issues: remember "Examples system needs update for [context]" infrastructure
```

### Missing Context Detection
```
❓ Examples not adapting to current situation
💡 Possible Causes:
   1. Context detection requires recent command usage
   2. New installation - context builds over time
   3. Use help system more to improve context detection
   4. Manually specify context: examples [context]
```

## Best Practices for Using Examples
- **Start General**: Use `examples` without parameters to see context-aware suggestions
- **Be Specific**: Use `examples <command>` for focused command examples
- **Use Context**: Specify context for domain-specific examples
- **Follow Patterns**: Examples show proven successful patterns - follow them closely
- **Adapt to Situation**: Use examples as templates, adapt parameters to your specific needs
- **Provide Feedback**: Success/failure of examples improves future recommendations

---

**Contextual Intelligence**: The examples system learns from actual usage patterns and adapts to your specific environment, making examples increasingly relevant and useful over time.