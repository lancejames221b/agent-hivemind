---
description: Query hAIveMind collective knowledge and specialized agent expertise
argument-hint: "question or topic" [category] [--agent=name] [--recent=hours]
allowed-tools: ["mcp__haivemind__search_memories", "mcp__haivemind__query_agent_knowledge"]
---

# hv-query - Collective Knowledge Search

## Purpose
Search the hAIveMind collective memory and query specialized agents for comprehensive answers combining stored knowledge with real-time expertise.

## When to Use
- **Troubleshooting Issues**: Find solutions to problems encountered before
- **Best Practices**: Learn how other agents handle similar situations
- **Configuration Guidance**: Get infrastructure setup recommendations
- **Incident Research**: Find related incidents and their resolutions
- **Technical Questions**: Tap into specialized agent knowledge
- **Historical Context**: Understand past decisions and their outcomes

## Syntax
```
hv-query "question or topic" [category] [options]
```

## Parameters
- **question** (required): Clear, specific question or topic to search
- **category** (optional): Narrow search to specific memory types
  - `infrastructure`: Server configs, network topology, hardware
  - `incidents`: Outage reports, resolutions, post-mortems
  - `deployments`: Release procedures, rollbacks, configurations
  - `security`: Vulnerabilities, patches, compliance, audits
  - `monitoring`: Alerts, metrics, dashboards, thresholds
  - `runbooks`: Procedures, scripts, operational guides
- **options** (optional):
  - `--agent=name`: Query specific agent directly (e.g., --agent=elastic1-specialist)
  - `--recent=hours`: Limit to memories from last N hours (e.g., --recent=24)
  - `--semantic`: Use semantic search only (default: hybrid)
  - `--exact`: Use exact text matching only

## Query Intelligence Features

### Hybrid Search Strategy
1. **Semantic Search**: Finds conceptually related information
2. **Full-Text Search**: Locates exact phrases and technical terms
3. **Agent Expertise**: Routes questions to specialists
4. **Context Correlation**: Links related memories automatically

### Agent Expertise Routing
- **Database Issues** → mysql-specialist, mongodb-specialist
- **Elasticsearch Problems** → elastic1-specialist, cluster-manager
- **Security Questions** → security-analyst, auth-specialist
- **Network Issues** → infrastructure-manager, network-specialist
- **Code Questions** → development-team, code-reviewer

## Real-World Examples

### Infrastructure Troubleshooting
```
hv-query "elasticsearch high CPU usage solutions" infrastructure
```
**Result**: Finds previous incidents, configuration changes, and expert recommendations for CPU optimization

### Security Best Practices
```
hv-query "JWT token expiration best practices" security --agent=security-analyst
```
**Result**: Security specialist provides current best practices plus related security memories

### Database Performance Issues
```
hv-query "mysql slow query optimization techniques" --agent=mysql-specialist --recent=168
```
**Result**: MySQL expert analyzes recent performance issues and provides targeted optimization advice

### Deployment Procedures
```
hv-query "safe rolling deployment process for microservices" deployments
```
**Result**: Comprehensive deployment runbooks and lessons learned from previous rollouts

### Incident Investigation
```
hv-query "memory leak patterns in Node.js applications" incidents --recent=720
```
**Result**: Past memory leak incidents, resolution patterns, and monitoring recommendations

## Expected Output

### Comprehensive Query Response
```
🔍 hAIveMind Collective Query: "elasticsearch high CPU usage solutions"

📊 Search Results Summary:
✓ 12 memories found across 3 categories
✓ 4 specialized agents consulted
✓ 3 exact matches, 9 semantic matches
✓ Confidence: High (87%)

🧠 Agent Expertise (elastic1-specialist):
"High CPU in elasticsearch typically stems from:
1. Inefficient queries with wildcards or regex
2. Large aggregations without proper field data cache
3. Concurrent indexing during peak query times
4. JVM heap pressure causing excessive GC

Immediate actions:
- Check slow query log: GET /_nodes/hot_threads
- Review field data circuit breaker: GET /_cluster/settings
- Implement index throttling during peak hours"

📚 Collective Memory Matches:

🔴 [INCIDENT-2025-01-20] elasticsearch CPU spike to 95% on elastic1
   Resolution: Implemented query timeout of 30s, optimized wildcard queries
   → Full details: memory-id-001

🟡 [RUNBOOK-2025-01-15] Elasticsearch Performance Optimization Checklist  
   Includes: JVM tuning, query optimization, index management
   → Full details: memory-id-087

🔵 [CONFIG-2025-01-18] Production elasticsearch.yml optimization
   Settings: heap size, field data cache, circuit breakers
   → Full details: memory-id-034

💡 Related Recommendations:
- Consider upgrading to elasticsearch 8.x for better CPU efficiency
- Implement index lifecycle management for older indices
- Set up proactive monitoring for query response times

🔗 Related Queries:
- "elasticsearch JVM heap optimization" (8 memories)
- "slow query optimization elasticsearch" (12 memories)  
- "elasticsearch monitoring best practices" (15 memories)
```

### Agent-Specific Query Response  
```
🎯 Direct Agent Query: security-analyst

Question: "JWT token expiration best practices"

🔒 Security Analysis:
"Current industry standards for JWT expiration:

Access Tokens: 15-30 minutes maximum
- Short lifespan limits exposure if compromised
- Forces regular rotation through refresh cycle
- Balances security with user experience

Refresh Tokens: 1-7 days depending on sensitivity
- Longer lifespan for seamless user experience  
- Should be rotated on each use (sliding window)
- Store securely, revoke immediately on suspicious activity

Implementation recommendations:
1. Use 'exp' claim for automatic expiration
2. Implement token blacklisting for immediate revocation
3. Set 'nbf' (not before) for delayed activation
4. Monitor for unusual token usage patterns"

📋 Related Security Memories:
- JWT security audit findings (2025-01-22)
- OAuth2 token management guidelines (2025-01-20)  
- Session management security review (2025-01-19)

⚠️  Security Alerts:
- No active JWT-related security incidents
- Last security review: 2025-01-20 (passed)
```

## Search Categories Deep Dive

### Infrastructure Category
- **Server Configurations**: nginx, apache, load balancer settings
- **Network Topology**: VPC setup, firewall rules, DNS configurations  
- **Hardware Issues**: CPU, memory, disk, network performance
- **Service Dependencies**: How services interact and affect each other

### Incidents Category
- **Outage Reports**: Root cause analysis, timeline, impact assessment
- **Performance Degradations**: Slow response times, high error rates
- **Security Breaches**: Attack vectors, containment, remediation
- **Recovery Procedures**: How incidents were resolved, lessons learned

### Security Category
- **Vulnerability Reports**: CVE details, patch status, risk assessment
- **Compliance Audits**: SOC2, PCI-DSS, GDPR compliance findings
- **Access Control**: User permissions, API keys, authentication issues
- **Security Best Practices**: Industry standards, internal guidelines

## Performance Considerations
- **Search Latency**: 200-500ms for simple queries, 1-2s for complex
- **Agent Response Time**: 1-5 seconds depending on agent availability
- **Memory Scan**: Searches across ~10,000 stored memories efficiently  
- **Concurrent Queries**: System handles 10+ simultaneous queries
- **Cache Efficiency**: Repeated queries return faster (Redis caching)

## Advanced Query Techniques

### Natural Language Queries
```
hv-query "Why did elasticsearch crash last Tuesday?"
hv-query "How do I prevent SQL injection in the auth service?"
hv-query "What's the standard procedure for database backups?"
```

### Technical Specific Queries
```
hv-query "nginx 502 bad gateway troubleshooting" infrastructure
hv-query "redis memory optimization settings" --agent=redis-specialist  
hv-query "kubernetes pod restart loop debugging" incidents --recent=48
```

### Comparative Queries
```
hv-query "mysql vs postgresql for high-write workloads"
hv-query "docker vs kubernetes for microservice deployment"
hv-query "nginx vs apache performance comparison"
```

## Error Scenarios and Solutions

### No Results Found
```
❌ No memories found for: "rare-technical-term"
💡 Suggestions:
- Try broader search terms: "database" instead of "postgresql-13.2"
- Search different categories: try "infrastructure" if "incidents" returns nothing
- Ask specific agents: --agent=database-specialist
- Check spelling and try synonyms
```

### Agent Unavailable
```
❌ Agent 'elasticsearch-expert' not responding
✓ Falling back to collective memory search
✓ Found 8 related memories from other sources
💡 Try again later or query similar agent: elastic1-specialist
```

### Ambiguous Query
```
⚠️  Query too broad: "server issues" 
📊 Found 247 potentially relevant memories
💡 Suggestions to narrow down:
- Add category: "server issues" infrastructure
- Be more specific: "server high CPU usage"
- Add time constraint: --recent=24
```

## Best Practices
- **Be Specific**: Include system names, error codes, context
- **Use Categories**: Narrow searches for faster, more relevant results
- **Query Experts**: Use --agent= for specialized technical questions
- **Follow Suggestions**: Use "Related Queries" to discover more information
- **Check Recency**: Use --recent= for time-sensitive issues
- **Combine Results**: Use both memory search and agent expertise
- **Learn from History**: Query past similar situations before asking agents

## Related Commands
- **Before querying**: Use `hv-status` to see available agents
- **After finding info**: Use `remember` to store your own learnings
- **For urgent issues**: Use `hv-delegate` to assign resolution tasks
- **To share findings**: Use `hv-broadcast` to inform collective

## Troubleshooting

### Slow Query Performance
1. Use more specific search terms to reduce result set
2. Add category filters to limit search scope  
3. Check network connectivity to agents: `hv-status`
4. Clear query cache if results seem stale

### Irrelevant Results
1. Use exact phrase matching with quotes: "exact error message"
2. Add negative terms: elasticsearch NOT jenkins  
3. Specify category to filter out unrelated memories
4. Query specific agents instead of general search

### Missing Expected Information
1. Information might be stored in different category
2. Try different search terms or synonyms
3. Query specific agents who might have undocumented knowledge
4. Check if information was recently added with --recent

---

**Query Topic**: $ARGUMENTS

This will search collective memory and consult specialized agents to provide comprehensive answers combining historical knowledge with current expertise.