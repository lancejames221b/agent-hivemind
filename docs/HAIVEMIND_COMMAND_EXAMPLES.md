# hAIveMind Command Examples and Use Cases

## Overview

This comprehensive guide provides real-world scenarios, command sequences, and workflow patterns for the hAIveMind collective intelligence system. Each example demonstrates practical usage patterns that can be adapted to your specific infrastructure and operational needs.

## Table of Contents

1. [DevOps Workflows](#devops-workflows)
2. [Development Workflows](#development-workflows)
3. [Monitoring & Maintenance](#monitoring--maintenance)
4. [Security Operations](#security-operations)
5. [Command Interaction Patterns](#command-interaction-patterns)
6. [Advanced Scenarios](#advanced-scenarios)
7. [Troubleshooting Workflows](#troubleshooting-workflows)

---

## DevOps Workflows

### Scenario 1: Security Vulnerability Discovery and Response

**Context**: SQL injection vulnerability discovered in authentication service

**Full Command Sequence**:
```bash
# 1. Document the discovery immediately
remember "SQL injection vulnerability found in /api/users endpoint - affects user authentication. Discovered via automated security scan. Allows bypassing login validation with payload: ' OR '1'='1' -- " security --important --tags="sql-injection,authentication,critical"

# 2. Broadcast critical security alert to all agents
hv-broadcast "Critical SQL injection vulnerability discovered in user authentication API - immediate patch required" security critical

# 3. Delegate patching to security team with high priority
hv-delegate "Patch SQL injection vulnerability in /api/users endpoint - implement parameterized queries and input validation" critical security_analysis,development

# 4. Monitor patch deployment progress
hv-status --agents

# 5. Query for similar vulnerabilities across the system
hv-query "SQL injection vulnerabilities in authentication services" security --recent=720

# 6. Verify patch completion and document resolution
recall "SQL injection /api/users" --recent=24 --detailed

# 7. Broadcast successful resolution
hv-broadcast "SQL injection vulnerability in user API successfully patched - all authentication endpoints secured" security info

# 8. Store lessons learned
remember "SQL injection prevention: Always use parameterized queries, implement input validation, regular security scans. Patch deployed in 2 hours with zero downtime using blue-green deployment" security --tags="lessons-learned,sql-injection,prevention"
```

**Expected Timeline**: 2-4 hours from discovery to resolution
**Key Learning**: Memory-first approach ensures knowledge preservation

### Scenario 2: Infrastructure Maintenance Window

**Context**: Database maintenance requiring coordinated service updates

**Full Command Sequence**:
```bash
# 1. Pre-maintenance sync and status check
hv-sync status
hv-status --detailed

# 2. Document maintenance plan
remember "Database maintenance scheduled 2025-01-24 02:00-04:00 UTC. Plan: 1) Enable read replicas 2) Stop write services 3) Run VACUUM and REINDEX 4) Update statistics 5) Restart services. Expected downtime: 30 minutes maximum" infrastructure --tags="maintenance,database,planned-downtime"

# 3. Sync configurations before maintenance
hv-sync --config --verbose

# 4. Broadcast maintenance start notification
hv-broadcast "Database maintenance starting - switching to read-only mode for 30 minutes" infrastructure warning

# 5. Delegate monitoring during maintenance
hv-delegate "Monitor database performance metrics during maintenance window - alert if any issues detected" high monitoring,database_ops

# 6. Query for similar maintenance procedures
hv-query "database maintenance best practices VACUUM REINDEX" runbooks --recent=8760

# 7. Monitor agent status during maintenance
hv-status --agents --network

# 8. Document any issues encountered
remember "During maintenance: VACUUM took longer than expected (45 min vs 20 min planned) due to table bloat. No service impact due to read replica failover working correctly" incidents --tags="maintenance,vacuum,performance"

# 9. Broadcast successful completion
hv-broadcast "Database maintenance completed successfully - all services restored to normal operation" infrastructure info

# 10. Store updated procedures
remember "Updated database maintenance procedure: 1) Check table bloat first 2) Allocate 60 min for VACUUM 3) Monitor replica lag 4) Test failover before maintenance. Zero downtime achieved with proper replica setup" runbooks --tags="database,maintenance,procedure"
```

**Expected Timeline**: 4-6 hours including preparation and documentation
**Key Learning**: Proactive communication prevents confusion during maintenance

### Scenario 3: Performance Degradation Investigation

**Context**: Application response times increased from 200ms to 2000ms

**Full Command Sequence**:
```bash
# 1. Document the performance issue
remember "Application response time degraded from 200ms to 2000ms starting 2025-01-24 14:30. Affects all API endpoints. Users reporting timeouts. CPU usage normal, memory usage increased 40%" incidents --important --tags="performance,response-time,degradation"

# 2. Broadcast performance alert
hv-broadcast "Critical performance degradation - API response times increased 10x" incident critical

# 3. Query historical performance issues
hv-query "API response time degradation causes" incidents --recent=2160

# 4. Delegate investigation to multiple specialists
hv-delegate "Investigate database query performance - check for slow queries and blocking" critical database_ops,monitoring
hv-delegate "Analyze application memory usage patterns - possible memory leak" critical development,monitoring
hv-delegate "Review load balancer and network latency metrics" high infrastructure_management,monitoring

# 5. Check agent availability for investigation
hv-status --agents

# 6. Query for similar memory usage patterns
hv-query "memory usage increased 40% performance impact" infrastructure --agent=monitoring-agent

# 7. Monitor investigation progress
hv-status --detailed

# 8. Document root cause when found
remember "Root cause identified: Database connection pool exhaustion due to long-running analytics queries. Connection pool size was 20, but analytics queries were holding connections for 5+ minutes. Increased pool size to 50 and implemented query timeout of 60 seconds" incidents --tags="database,connection-pool,analytics,root-cause"

# 9. Broadcast resolution
hv-broadcast "Performance issue resolved - connection pool optimization restored normal response times" incident info

# 10. Store prevention measures
remember "Performance monitoring improvements: 1) Added connection pool utilization alerts 2) Implemented query timeout monitoring 3) Separated analytics queries to dedicated read replica 4) Set up automated scaling for connection pools" monitoring --tags="performance,prevention,connection-pool"
```

**Expected Timeline**: 1-3 hours depending on complexity
**Key Learning**: Parallel investigation by specialists accelerates resolution

---

## Development Workflows

### Scenario 4: Code Review and Security Analysis

**Context**: Authentication refactoring pull request needs comprehensive review

**Full Command Sequence**:
```bash
# 1. Document the code review request
remember "Authentication refactoring PR #234 submitted - migrating from custom JWT to OAuth2 with PKCE. Changes affect login, logout, token refresh, and session management. 847 lines changed across 12 files" project --tags="code-review,authentication,oauth2,pr-234"

# 2. Query for authentication best practices
hv-query "OAuth2 PKCE implementation security best practices" security --agent=security-analyst

# 3. Delegate security review
hv-delegate "Review authentication refactoring PR #234 for OWASP Top 10 vulnerabilities and OAuth2 security best practices" high security_analysis,code_review

# 4. Delegate code quality review
hv-delegate "Review PR #234 code quality - check error handling, logging, test coverage, and maintainability" medium code_review,development

# 5. Query for similar refactoring experiences
hv-query "JWT to OAuth2 migration lessons learned" project --recent=4320

# 6. Check review progress
hv-status --agents

# 7. Document security review findings
remember "Security review PR #234 findings: 1) PKCE implementation correct 2) Token storage secure (httpOnly cookies) 3) Proper CSRF protection 4) Missing rate limiting on token endpoint 5) Recommend adding token introspection logging" security --tags="code-review,oauth2,security-findings"

# 8. Document code quality findings
remember "Code quality review PR #234: 1) Excellent test coverage 95% 2) Proper error handling with user-friendly messages 3) Good logging for debugging 4) Suggest extracting token validation to middleware 5) Consider adding metrics for token operations" project --tags="code-review,code-quality,pr-234"

# 9. Broadcast review completion
hv-broadcast "Authentication refactoring PR #234 reviewed - minor security improvements needed before merge" project info

# 10. Store review template for future use
remember "Code review checklist for authentication changes: 1) Security analysis (OWASP Top 10) 2) Token handling security 3) Rate limiting implementation 4) Logging and monitoring 5) Test coverage >90% 6) Error handling 7) Performance impact assessment" runbooks --tags="code-review,authentication,checklist"
```

**Expected Timeline**: 4-8 hours for comprehensive review
**Key Learning**: Multi-agent review provides comprehensive coverage

### Scenario 5: Architecture Decision Documentation

**Context**: Deciding between microservices vs monolith for new feature

**Full Command Sequence**:
```bash
# 1. Document the architectural decision context
remember "Architecture decision needed: User notification system. Options: 1) Add to existing monolith 2) Create new microservice 3) Hybrid approach. Considerations: scalability, complexity, team expertise, deployment overhead" project --tags="architecture,notifications,decision"

# 2. Query for similar architectural decisions
hv-query "microservices vs monolith decision criteria" project --recent=8760

# 3. Delegate analysis to architecture specialists
hv-delegate "Analyze notification system architecture options - provide pros/cons for microservice vs monolith approach" medium development,infrastructure_management

# 4. Query for notification system implementations
hv-query "notification system architecture patterns scalability" infrastructure --agent=elastic1-specialist

# 5. Broadcast decision discussion
hv-broadcast "Architectural decision in progress for notification system - seeking input from development teams" project info

# 6. Document analysis results
remember "Architecture analysis results: Monolith approach recommended. Reasons: 1) Team size (3 developers) insufficient for microservice overhead 2) Notification volume low (<1000/day) 3) Tight coupling with user management 4) Deployment complexity not justified 5) Can extract later if needed" project --tags="architecture,decision,monolith,notifications"

# 7. Query for monolith best practices
hv-query "monolith architecture notification system best practices" project

# 8. Document final decision
remember "DECISION: Implement notification system as monolith module. Implementation plan: 1) Create notifications table 2) Add notification service layer 3) Implement email/SMS providers 4) Add admin interface 5) Set up monitoring. Timeline: 3 weeks" project --important --tags="architecture,decision,implementation-plan"

# 9. Broadcast decision
hv-broadcast "Architecture decision finalized - notification system will be implemented as monolith module" project info

# 10. Store decision template
remember "Architecture decision template: 1) Define problem and constraints 2) List options with pros/cons 3) Consider team capacity and expertise 4) Evaluate complexity vs benefit 5) Plan for future changes 6) Document decision rationale 7) Create implementation plan" runbooks --tags="architecture,decision-making,template"
```

**Expected Timeline**: 2-5 days for thorough analysis
**Key Learning**: Structured decision-making prevents future regrets

---

## Monitoring & Maintenance

### Scenario 6: System Health Monitoring and Alerting

**Context**: Setting up proactive monitoring for new service deployment

**Full Command Sequence**:
```bash
# 1. Document monitoring requirements
remember "New payment service deployed - requires comprehensive monitoring. SLA: 99.9% uptime, <500ms response time, <0.1% error rate. Critical business function requiring 24/7 monitoring" monitoring --important --tags="payment-service,sla,monitoring-setup"

# 2. Query for monitoring best practices
hv-query "payment service monitoring best practices SLA alerting" monitoring --agent=monitoring-agent

# 3. Delegate monitoring setup
hv-delegate "Configure comprehensive monitoring for payment service - metrics, alerts, dashboards, and SLA tracking" high monitoring,infrastructure_management

# 4. Query for similar service monitoring
hv-query "financial service monitoring patterns alerting thresholds" monitoring --recent=2160

# 5. Check monitoring agent availability
hv-status --agents

# 6. Document monitoring implementation
remember "Payment service monitoring implemented: 1) Response time alerts >400ms (warning) >800ms (critical) 2) Error rate alerts >0.05% (warning) >0.1% (critical) 3) Availability monitoring every 30s 4) Business metrics: transaction volume, success rate 5) Infrastructure: CPU, memory, disk, network" monitoring --tags="payment-service,alerts,thresholds"

# 7. Test alerting system
hv-delegate "Test payment service alerting system - simulate various failure scenarios and verify alert delivery" medium monitoring,testing

# 8. Query for alert fatigue prevention
hv-query "alert fatigue prevention monitoring best practices" monitoring

# 9. Document alert escalation procedures
remember "Payment service alert escalation: Level 1 (warning): Slack notification, auto-ticket. Level 2 (critical): PagerDuty, SMS to on-call engineer. Level 3 (SLA breach): Escalate to management, incident commander assigned. Response times: L1=30min, L2=15min, L3=5min" runbooks --tags="payment-service,escalation,incident-response"

# 10. Broadcast monitoring completion
hv-broadcast "Payment service monitoring fully configured - comprehensive alerting and dashboards operational" monitoring info

# 11. Store monitoring template
remember "Service monitoring template: 1) Define SLA requirements 2) Set response time thresholds (warn/critical) 3) Configure error rate alerts 4) Monitor business metrics 5) Infrastructure monitoring 6) Test alert delivery 7) Document escalation procedures 8) Regular review and tuning" runbooks --tags="monitoring,template,sla"
```

**Expected Timeline**: 1-2 days for complete setup
**Key Learning**: Proactive monitoring prevents reactive firefighting

### Scenario 7: Capacity Planning and Scaling

**Context**: Elasticsearch cluster approaching capacity limits

**Full Command Sequence**:
```bash
# 1. Document capacity issue
remember "Elasticsearch cluster capacity warning: 78% disk usage on elastic1-3, query response time increased 25%, indexing rate decreased 15%. Current: 3 nodes, 2TB each. Growth rate: 50GB/week" infrastructure --important --tags="elasticsearch,capacity,scaling"

# 2. Broadcast capacity warning
hv-broadcast "Elasticsearch cluster approaching capacity limits - scaling planning required" infrastructure warning

# 3. Query for scaling strategies
hv-query "elasticsearch cluster scaling strategies capacity planning" infrastructure --agent=elastic1-specialist

# 4. Delegate capacity analysis
hv-delegate "Analyze elasticsearch cluster growth patterns and recommend scaling strategy - consider performance vs cost" high elasticsearch_ops,infrastructure_management

# 5. Query for similar scaling experiences
hv-query "elasticsearch horizontal scaling 3 to 5 nodes experience" infrastructure --recent=4320

# 6. Check infrastructure agent availability
hv-status --agents

# 7. Document scaling analysis
remember "Elasticsearch scaling analysis: Current growth 50GB/week will reach 90% capacity in 6 weeks. Options: 1) Add 2 nodes (horizontal scaling) - better performance, higher cost 2) Upgrade storage to 4TB - cheaper, limited performance gain 3) Implement data lifecycle management - reduce storage needs. Recommendation: Add 2 nodes + implement ILM" infrastructure --tags="elasticsearch,scaling,analysis,recommendation"

# 8. Delegate implementation planning
hv-delegate "Create elasticsearch cluster scaling implementation plan - node addition, data rebalancing, and ILM setup" medium elasticsearch_ops,infrastructure_management

# 9. Query for data lifecycle management
hv-query "elasticsearch index lifecycle management best practices" infrastructure

# 10. Document implementation plan
remember "Elasticsearch scaling implementation plan: Week 1: Set up ILM policies (delete indices >90 days, move to cold storage >30 days). Week 2: Add 2 new nodes (elastic4, elastic5). Week 3: Rebalance shards, optimize allocation. Week 4: Monitor and tune. Expected result: 40% capacity utilization, 30% performance improvement" infrastructure --tags="elasticsearch,implementation-plan,scaling"

# 11. Broadcast scaling plan
hv-broadcast "Elasticsearch scaling plan approved - adding 2 nodes and implementing data lifecycle management" infrastructure info

# 12. Store capacity planning template
remember "Capacity planning template: 1) Monitor growth trends 2) Calculate time to capacity 3) Evaluate scaling options (vertical/horizontal) 4) Consider cost vs performance 5) Plan data lifecycle management 6) Create implementation timeline 7) Set up monitoring for new capacity" runbooks --tags="capacity-planning,template,elasticsearch"
```

**Expected Timeline**: 2-3 weeks for complete implementation
**Key Learning**: Early capacity planning prevents emergency scaling

---

## Security Operations

### Scenario 8: Security Incident Response

**Context**: Suspicious login activity detected from unusual geographic locations

**Full Command Sequence**:
```bash
# 1. Document security incident
remember "Security incident: Suspicious login activity detected. 47 login attempts from IP ranges in Eastern Europe for user accounts that typically login from US/Canada. Timeframe: 2025-01-24 02:00-04:00 UTC. No successful logins yet due to MFA" security --important --tags="security-incident,suspicious-login,geographic-anomaly"

# 2. Broadcast security alert
hv-broadcast "Security incident in progress - suspicious geographic login attempts detected" security critical

# 3. Query for similar incidents
hv-query "suspicious login geographic anomaly incident response" security --recent=2160

# 4. Delegate immediate response
hv-delegate "Implement immediate security measures - block suspicious IP ranges and notify affected users" critical security_analysis,incident_response

# 5. Delegate forensic analysis
hv-delegate "Perform forensic analysis of login attempts - identify attack patterns and potential data exposure" high security_analysis,monitoring

# 6. Check security team availability
hv-status --agents

# 7. Query for IP blocking procedures
hv-query "IP range blocking procedures geographic login attacks" security --agent=security-analyst

# 8. Document immediate response actions
remember "Immediate response actions taken: 1) Blocked IP ranges 203.45.67.0/24 and 198.51.100.0/24 2) Enabled additional MFA verification for affected accounts 3) Sent security notifications to 23 targeted users 4) Increased login monitoring sensitivity 5) Activated incident response team" security --tags="incident-response,ip-blocking,mfa,notifications"

# 9. Monitor ongoing attack
hv-status --detailed

# 10. Document forensic findings
remember "Forensic analysis results: Attack originated from compromised residential IP addresses (likely botnet). Targeted accounts: high-privilege users (admin, finance, HR). Attack pattern: credential stuffing using common passwords. No successful breaches due to MFA. Likely data source: previous data breach from external service" security --tags="forensic-analysis,botnet,credential-stuffing,mfa-effective"

# 11. Delegate long-term improvements
hv-delegate "Implement enhanced security measures based on incident findings - geographic login restrictions and improved monitoring" medium security_analysis,development

# 12. Query for prevention strategies
hv-query "credential stuffing attack prevention geographic restrictions" security

# 13. Document lessons learned
remember "Security incident lessons learned: 1) MFA prevented successful breaches 2) Geographic monitoring effective for early detection 3) Need automated IP blocking for suspicious patterns 4) User notification system worked well 5) Consider implementing CAPTCHA for unusual login locations" security --tags="lessons-learned,mfa,geographic-monitoring,prevention"

# 14. Broadcast incident resolution
hv-broadcast "Security incident resolved - no data breach occurred, enhanced monitoring implemented" security info

# 15. Store incident response template
remember "Security incident response template: 1) Document incident details immediately 2) Broadcast critical alert 3) Implement immediate containment 4) Perform forensic analysis 5) Notify affected users 6) Monitor for ongoing activity 7) Implement long-term improvements 8) Document lessons learned 9) Update response procedures" runbooks --tags="security,incident-response,template"
```

**Expected Timeline**: 4-8 hours for initial response, 1-2 weeks for complete resolution
**Key Learning**: Rapid response and documentation prevent incident escalation

---

## Command Interaction Patterns

### Pattern 1: Memory-First Workflow

**Best Practice**: Always document before broadcasting or delegating

```bash
# ✅ GOOD: Document first, then act
remember "Database connection timeout issue affecting user login - 30% of attempts failing"
hv-broadcast "Database connectivity issue detected - investigating"
hv-delegate "Investigate database connection timeout root cause"

# ❌ POOR: Act without documentation
hv-broadcast "Something wrong with database"
hv-delegate "Fix database"
```

### Pattern 2: Query-Before-Delegate

**Best Practice**: Check agent availability and expertise before delegating

```bash
# ✅ GOOD: Check availability first
hv-status --agents
hv-query "elasticsearch performance optimization" --agent=elastic1-specialist
hv-delegate "Optimize elasticsearch query performance" high elasticsearch_ops

# ❌ POOR: Delegate blindly
hv-delegate "Fix elasticsearch" critical
```

### Pattern 3: Status Monitoring During Operations

**Best Practice**: Regular status checks during long-running operations

```bash
# ✅ GOOD: Monitor progress
hv-delegate "Database migration task" critical database_ops
# Wait 30 minutes
hv-status --agents
# Check specific agent
hv-query "migration progress" --agent=mysql-specialist
# Continue monitoring
```

### Pattern 4: Sync-Before-Critical-Operations

**Best Practice**: Ensure all agents are synchronized before important work

```bash
# ✅ GOOD: Sync before critical operations
hv-sync status
hv-sync --verbose
hv-status --detailed
# Proceed with critical operation
hv-delegate "Production deployment" critical
```

### Pattern 5: Broadcast-After-Resolution

**Best Practice**: Share successful resolutions with the collective

```bash
# ✅ GOOD: Share knowledge after resolution
remember "SSL certificate renewal automated with Let's Encrypt"
hv-broadcast "SSL certificate auto-renewal implemented - manual renewals no longer needed" infrastructure info
```

---

## Advanced Scenarios

### Scenario 9: Multi-Agent Coordination for Complex Deployment

**Context**: Microservices deployment requiring database, cache, and load balancer updates

**Full Command Sequence**:
```bash
# 1. Document deployment plan
remember "Complex deployment v2.4.0: Requires coordinated updates to 5 microservices, database schema changes, Redis cache updates, and load balancer reconfiguration. Zero-downtime requirement. Rollback plan prepared" deployments --important --tags="v2.4.0,microservices,zero-downtime,coordination"

# 2. Pre-deployment sync
hv-sync force --verbose

# 3. Check all agent availability
hv-status --agents --detailed

# 4. Query for similar complex deployments
hv-query "microservices zero downtime deployment coordination" deployments --recent=2160

# 5. Delegate pre-deployment tasks in parallel
hv-delegate "Prepare database schema migration scripts and test on staging" high database_ops,development
hv-delegate "Configure new load balancer rules for service routing" high infrastructure_management,networking
hv-delegate "Prepare Redis cache warming scripts for new data structures" medium caching,development
hv-delegate "Set up deployment monitoring and health checks" high monitoring,deployment

# 6. Monitor preparation progress
hv-status --agents

# 7. Document preparation completion
remember "Deployment preparation completed: 1) Database migration tested on staging 2) Load balancer rules configured and tested 3) Cache warming scripts ready 4) Health checks configured 5) Rollback procedures verified. Ready for production deployment" deployments --tags="v2.4.0,preparation,ready"

# 8. Coordinate deployment sequence
hv-broadcast "Starting coordinated deployment v2.4.0 - all teams standby" deployments warning

# 9. Execute deployment in sequence
hv-delegate "Execute database schema migration - coordinate with application deployment" critical database_ops
# Wait for database completion
hv-delegate "Deploy microservices in blue-green pattern - coordinate with load balancer" critical deployment,infrastructure_management
hv-delegate "Update load balancer routing to new services" critical infrastructure_management,networking
hv-delegate "Execute cache warming and validation" medium caching,monitoring

# 10. Monitor deployment progress
hv-status --detailed

# 11. Validate deployment success
hv-delegate "Perform comprehensive deployment validation - all services and integrations" high testing,monitoring

# 12. Document deployment results
remember "Deployment v2.4.0 completed successfully: Zero downtime achieved, all services healthy, performance improved 15%, no rollback required. Total deployment time: 45 minutes. Key success factors: thorough preparation, agent coordination, monitoring" deployments --tags="v2.4.0,success,zero-downtime,coordination"

# 13. Broadcast successful completion
hv-broadcast "Deployment v2.4.0 completed successfully - all services operational with improved performance" deployments info

# 14. Store coordination template
remember "Complex deployment coordination template: 1) Document comprehensive plan 2) Sync all agents 3) Check agent availability 4) Delegate preparation tasks in parallel 5) Monitor preparation progress 6) Coordinate execution sequence 7) Monitor deployment progress 8) Validate success 9) Document results and lessons learned" runbooks --tags="deployment,coordination,template,microservices"
```

**Expected Timeline**: 4-6 hours including preparation
**Key Learning**: Coordination and preparation are critical for complex deployments

### Scenario 10: Knowledge Discovery and Sharing

**Context**: Research new technology adoption across the organization

**Full Command Sequence**:
```bash
# 1. Document research initiative
remember "Technology research: Evaluating Kubernetes adoption for microservices deployment. Current state: Docker Compose on VMs. Goals: improved scalability, better resource utilization, simplified deployments. Timeline: 2 months evaluation" project --tags="kubernetes,research,microservices,adoption"

# 2. Query existing knowledge
hv-query "Kubernetes adoption microservices experience lessons learned" infrastructure --recent=8760

# 3. Broadcast research initiative
hv-broadcast "Starting Kubernetes adoption research - seeking input from all teams with container experience" project info

# 4. Delegate research tasks to specialists
hv-delegate "Research Kubernetes cluster setup and management requirements for our infrastructure" medium infrastructure_management,development
hv-delegate "Evaluate Kubernetes security implications and best practices" medium security_analysis,infrastructure_management
hv-delegate "Analyze cost implications of Kubernetes vs current Docker Compose setup" low infrastructure_management,monitoring

# 5. Query for container orchestration comparisons
hv-query "Kubernetes vs Docker Compose production comparison" infrastructure --agent=elastic1-specialist

# 6. Collect research findings
hv-status --agents

# 7. Document research findings
remember "Kubernetes research findings: Pros: Better scaling, service discovery, rolling deployments, resource efficiency. Cons: Complexity increase, learning curve, operational overhead. Cost: 20% reduction in infrastructure costs. Security: Improved with proper RBAC and network policies. Recommendation: Proceed with pilot project" project --tags="kubernetes,research-findings,recommendation,pilot"

# 8. Query for pilot project approaches
hv-query "Kubernetes pilot project implementation strategy" project

# 9. Delegate pilot project planning
hv-delegate "Create Kubernetes pilot project plan - select services, timeline, success criteria" medium development,infrastructure_management

# 10. Document pilot project plan
remember "Kubernetes pilot project plan: Phase 1 (4 weeks): Set up dev cluster, migrate 2 non-critical services. Phase 2 (4 weeks): Production cluster setup, migrate 1 critical service. Phase 3 (4 weeks): Evaluation, documentation, go/no-go decision. Success criteria: <5% performance degradation, <2 hours additional deployment time, team comfort level >7/10" project --tags="kubernetes,pilot-project,plan,phases"

# 11. Broadcast research completion
hv-broadcast "Kubernetes research completed - pilot project approved and planned" project info

# 12. Store research methodology
remember "Technology research methodology: 1) Document research goals and timeline 2) Query existing collective knowledge 3) Broadcast initiative for input 4) Delegate specialized research tasks 5) Collect and analyze findings 6) Make data-driven recommendations 7) Plan pilot project if approved 8) Share findings with collective" runbooks --tags="research,methodology,technology-adoption"

# 13. Schedule knowledge sharing session
hv-delegate "Organize Kubernetes knowledge sharing session - present research findings to all teams" low development,coordination

# 14. Document knowledge sharing results
remember "Kubernetes knowledge sharing session results: 15 attendees, high interest level, 3 volunteers for pilot project team, concerns about complexity addressed, timeline approved by management. Next steps: Form pilot team, set up development environment" project --tags="kubernetes,knowledge-sharing,pilot-team,next-steps"
```

**Expected Timeline**: 2-3 months for complete evaluation
**Key Learning**: Systematic research and knowledge sharing improve adoption success

---

## Troubleshooting Workflows

### Scenario 11: hAIveMind System Issues

**Context**: Commands not responding, agents offline, sync failures

**Full Command Sequence**:
```bash
# 1. Document the system issues
remember "hAIveMind system issues: Commands timing out, 5 agents offline (elastic2, proxy1, dev-env, tony-dev, mike-dev), sync failing with network errors. Started around 2025-01-24 08:00 UTC" infrastructure --important --tags="haivemind,system-issues,network,agents-offline"

# 2. Check basic system status
hv-status --detailed

# 3. Try force sync to refresh connections
hv-sync force --verbose

# 4. Query for similar system issues
hv-query "hAIveMind agents offline network connectivity issues" infrastructure --recent=720

# 5. Check Tailscale connectivity
# (This would be done via shell commands in practice)
remember "Tailscale status check: 3 nodes unreachable (elastic2, proxy1, dev-env), 2 nodes timeout (tony-dev, mike-dev). Suggests network connectivity issues rather than agent problems" infrastructure --tags="tailscale,connectivity,network-diagnosis"

# 6. Broadcast system issues
hv-broadcast "hAIveMind system experiencing connectivity issues - investigating network problems" infrastructure critical

# 7. Delegate network troubleshooting
hv-delegate "Investigate Tailscale network connectivity issues - check routing, DNS, and firewall rules" critical infrastructure_management,networking

# 8. Try alternative sync methods
hv-sync clean --verbose

# 9. Check individual agent health
hv-query "agent health check procedures" infrastructure --agent=monitoring-agent

# 10. Document troubleshooting steps
remember "hAIveMind troubleshooting steps taken: 1) Status check revealed 5 offline agents 2) Force sync failed with network errors 3) Tailscale connectivity issues identified 4) Clean sync attempted 5) Network team investigating routing issues. Root cause: Tailscale subnet routing misconfiguration after network maintenance" infrastructure --tags="troubleshooting,network,tailscale,root-cause"

# 11. Monitor recovery progress
hv-status --network --agents

# 12. Document resolution
remember "hAIveMind system recovery: Network team fixed Tailscale subnet routing configuration. All agents came back online within 10 minutes. Sync completed successfully. System fully operational. Prevention: Add Tailscale connectivity monitoring to prevent future issues" infrastructure --tags="recovery,tailscale,subnet-routing,prevention"

# 13. Broadcast system recovery
hv-broadcast "hAIveMind system fully recovered - all agents online and operational" infrastructure info

# 14. Store troubleshooting runbook
remember "hAIveMind system troubleshooting runbook: 1) Check hv-status for agent availability 2) Try hv-sync force to refresh connections 3) Check Tailscale connectivity (tailscale status) 4) Investigate network routing and DNS 5) Try hv-sync clean for corrupted state 6) Check individual agent health 7) Escalate to network team if needed 8) Monitor recovery progress 9) Document root cause and prevention" runbooks --tags="haivemind,troubleshooting,runbook,network"
```

**Expected Timeline**: 1-4 hours depending on network complexity
**Key Learning**: Network connectivity is critical for hAIveMind operation

---

## hAIveMind Awareness Integration

### Automatic Learning and Optimization

The hAIveMind system automatically learns from successful workflow patterns:

1. **Pattern Recognition**: Identifies successful command sequences and timing
2. **Workflow Optimization**: Suggests improvements based on historical success rates
3. **Agent Performance**: Tracks which agents excel at specific task types
4. **Knowledge Gaps**: Identifies areas where collective knowledge is lacking
5. **Automation Opportunities**: Suggests workflows that could be automated

### Example Learning Scenarios

```bash
# System learns that security incidents require this pattern:
remember → hv-broadcast (critical) → hv-delegate (security_analysis) → hv-status → recall → hv-broadcast (resolution)

# System learns that deployment coordination works best with:
hv-sync → hv-status → parallel hv-delegate → monitor → validate → document

# System learns that performance issues benefit from:
remember → hv-query (historical) → parallel hv-delegate (multiple specialists) → correlate findings
```

### Proactive Suggestions

Based on context and patterns, hAIveMind may suggest:

- "Similar incidents were resolved faster when database and network teams collaborated"
- "This type of deployment historically benefits from staging validation first"
- "Security incidents like this typically require 3-4 hours; consider notifying stakeholders"

### Cross-Project Knowledge Sharing

- Successful patterns from one project automatically become available to others
- Agent expertise grows through exposure to different problem types
- Best practices evolve based on collective experience
- Failure patterns help prevent similar issues in other contexts

---

## Token-Optimized Format System (v2)

### Overview

The hAIveMind memory system uses a token-optimized format (v2) that reduces storage costs by 60-80% while maintaining semantic clarity. The format is automatically taught on your first memory access each session.

### Format Conventions

```
Symbols: → (flow) | (or) ? (opt) ! (req) :: (type)
Tables > prose: | key | val |
Refs: [ID]: define → use [ID]
Compact: auth(key) → search(q) → JSON
```

### New Format Tools

- `get_format_guide` - Get format guide (use `detailed=true` for full reference)
- `get_memory_access_stats` - View session access statistics

### Format v2 Examples

**Before (verbose prose):**
```bash
remember "When deploying Elasticsearch, you should first make sure that the heap size is set correctly. The heap size should be set to half of the available RAM, but not more than 32GB. You also need to ensure that the cluster name is configured properly and that the discovery type is set correctly for your environment."
```

**After (v2 format):**
```bash
remember "ES Deploy:
| Setting | Value | Notes |
| heap | RAM/2 | max 32GB |
| cluster.name | ES_CLUSTER |
| discovery.type | multi-node | single-node for dev |
Config: export ES_HEAP_SIZE=$((RAM/2))
Flow: configure → validate → start → verify"
```

### Auto-Teaching Behavior

1. **First memory access** each session includes `_haivemind_meta.format_guide`
2. All stored memories tagged with `format_version: v2`
3. Legacy verbose memories flagged with `legacy_content_detected: true`
4. Use `get_format_guide detailed=true` for complete format reference

### Using v2 Format in Workflows

```bash
# Store infrastructure knowledge with v2 format
remember "DB Backup Procedure:
| Step | Action | Duration |
| 1 | stop writes | 5min |
| 2 | snapshot | 15min |
| 3 | verify | 5min |
| 4 | resume | 1min |
Prereqs: disk space > 2x DB size
Rollback: restore from previous snapshot" runbooks --tags="database,backup,procedure"

# Check format guide if needed
get_format_guide detailed=true

# View session access statistics
get_memory_access_stats
```

### Migration from Legacy Format

When you encounter legacy verbose memories:
1. System flags them with `legacy_content_detected: true`
2. Read as normal - they still work perfectly
3. When updating, compress to v2 format for token savings
4. Use `get_format_guide` as reference when compressing

---

## Best Practices Summary

### Command Sequencing
1. **Document First**: Always `remember` before `hv-broadcast` or `hv-delegate`
2. **Query Before Action**: Use `hv-query` to check existing knowledge
3. **Status Before Delegation**: Use `hv-status` to verify agent availability
4. **Sync Before Critical Work**: Use `hv-sync` to ensure consistency
5. **Use v2 Format**: Tables > prose, symbols for flow, refs for repetition

### Workflow Patterns
1. **Incident Response**: remember → hv-broadcast → hv-delegate → monitor → resolve → document
2. **Deployment**: plan → sync → delegate preparation → coordinate execution → validate → document
3. **Research**: document goals → query existing → delegate research → analyze → decide → share

### Knowledge Management
1. **Be Specific**: Include system names, error codes, timelines
2. **Tag Appropriately**: Use consistent tags for searchability
3. **Document Outcomes**: Always record results and lessons learned
4. **Share Success**: Broadcast successful resolutions for collective benefit

### Agent Coordination
1. **Parallel Delegation**: Use multiple agents for complex problems
2. **Specialist Routing**: Match tasks to agent capabilities
3. **Progress Monitoring**: Regular status checks during long operations
4. **Clear Communication**: Specific task descriptions and expected outcomes

---

This comprehensive guide provides the foundation for effective hAIveMind usage across all operational scenarios. Adapt these patterns to your specific infrastructure and team needs while maintaining the core principles of documentation, coordination, and knowledge sharing.