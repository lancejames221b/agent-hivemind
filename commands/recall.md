---
description: Search and retrieve memories from hAIveMind collective knowledge base
allowed-tools: ["mcp__haivemind__search_memories", "mcp__haivemind__get_recent_memories"]
argument-hint: "search query" [category] [--recent=hours] [--limit=N] [--machine=name]
---

# recall - Memory Retrieval

## Purpose
Search and retrieve stored memories from the hAIveMind collective knowledge base using advanced semantic and text-based search capabilities.

## When to Use
- **Historical Research**: Find past incidents, solutions, or decisions
- **Learning from Experience**: Discover how similar problems were solved
- **Context Gathering**: Get background before starting new tasks
- **Documentation Lookup**: Find stored procedures, configs, or guides
- **Pattern Recognition**: Identify recurring issues or successful approaches
- **Knowledge Discovery**: Explore collective expertise on topics

## Syntax
```
recall "search query" [category] [options]
```

## Parameters
- **search query** (required): What to search for (can be natural language)
- **category** (optional): Narrow search to specific types
  - `infrastructure`, `incidents`, `security`, `deployments`, `monitoring`, `runbooks`
- **options** (optional):
  - `--recent=hours`: Limit to memories from last N hours
  - `--limit=N`: Maximum results to return (default: 10)
  - `--machine=name`: Search memories from specific machine
  - `--detailed`: Include full memory content in results
  - `--timeline`: Sort results chronologically

## Search Capabilities

### Semantic Search
- Understands context and meaning, not just keywords
- Finds conceptually related information
- Works with natural language queries
- Excellent for exploratory research

### Full-Text Search  
- Exact phrase matching with quotes: "error 502"
- Boolean operators: elasticsearch AND performance
- Wildcard matching: mysql*
- Technical term precision

### Hybrid Intelligence
- Combines semantic understanding with precise text matching
- Ranks results by relevance and recency
- Filters duplicate or near-duplicate memories
- Provides confidence scores

## Real-World Examples

### Incident Investigation
```
recall "database connection timeout errors" incidents --recent=168
```
**Result**: Recent database connectivity issues, solutions, and patterns

### Configuration Research
```
recall "nginx ssl configuration best practices" infrastructure
```
**Result**: SSL setup guides, security configurations, and lessons learned

### Security Analysis
```
recall "JWT vulnerability" security --detailed --timeline
```
**Result**: Chronological view of JWT-related security findings with full details

### Performance Optimization
```
recall "elasticsearch slow queries" --machine=elastic1 --limit=15
```
**Result**: Performance issues specific to elastic1 with comprehensive results

### Natural Language Query
```
recall "Why did the deployment fail last Tuesday?"
```
**Result**: Deployment-related failures around the specified timeframe

## Expected Output

### Standard Recall Results
```
📚 Memory Recall: "database connection timeout errors" (incidents, last 168 hours)

🔍 Search Results: 8 memories found (87% confidence)
🕑 Time Range: 2025-01-17 to 2025-01-24
🏷️  Category: incidents

🔴 [HIGH RELEVANCE] 2025-01-23 14:30:00 | elastic1
   ↳ Database Connection Pool Exhaustion - Production Impact
   ↳ MySQL connection timeouts during peak traffic, resolved with pool tuning
   ↳ Tags: mysql, connection-pool, performance, production
   ↳ Memory ID: mem-20250123-1430-001

🟡 [MEDIUM] 2025-01-22 09:15:00 | mysql-primary  
   ↳ Slow Query Causing Connection Backlog
   ↳ Long-running analytics query blocked connection pool
   ↳ Tags: mysql, slow-query, connection-timeout
   ↳ Memory ID: mem-20250122-0915-087

🟡 [MEDIUM] 2025-01-20 16:45:00 | auth-server
   ↳ Redis Connection Timeout Configuration
   ↳ Adjusted Redis timeout settings for auth service stability
   ↳ Tags: redis, timeout, configuration, auth-service
   ↳ Memory ID: mem-20250120-1645-234

🟠 [RELEVANT] 2025-01-19 11:20:00 | proxy1
   ↳ Network Latency Causing DB Timeouts
   ↳ High network latency between proxy and database servers
   ↳ Tags: network, latency, database, timeout
   ↳ Memory ID: mem-20250119-1120-156

📊 Related Patterns:
   ↳ Connection pool tuning: 4 memories
   ↳ Timeout configuration: 6 memories  
   ↳ Performance optimization: 12 memories

💡 Suggestions:
   ↳ Search "connection pool optimization" for tuning guides
   ↳ Search "mysql timeout configuration" for specific settings
   ↳ Check recent monitoring data with: recall "database metrics" monitoring --recent=24
```

### Detailed Memory Content
```
📚 Detailed Recall: "nginx ssl configuration" (infrastructure)

🔍 1 memory found with full content:

📜 [INFRASTRUCTURE] 2025-01-18 10:30:00 | lance-dev
   ↳ Title: Production Nginx SSL/TLS Configuration
   ↳ Author: lance-dev-agent
   ↳ Tags: nginx, ssl, tls, security, production
   ↳ Memory ID: mem-20250118-1030-445

📄 Full Content:
```
Production-ready Nginx SSL configuration:

server {
    listen 443 ssl http2;
    server_name example.com;
    
    # SSL Certificate Configuration
    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    
    # HSTS (HTTP Strict Transport Security)
    add_header Strict-Transport-Security "max-age=63072000" always;
    
    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Security notes:
- Disabled TLSv1.0 and TLSv1.1 for PCI compliance
- HSTS header prevents downgrade attacks
- OCSP stapling improves SSL handshake performance
- Tested with SSL Labs rating A+
```

🔗 Related Memories:
   ↳ SSL certificate renewal process (mem-20250115-0830-221)
   ↳ Nginx performance optimization (mem-20250112-1445-089)
   ↳ Security headers configuration (mem-20250110-0920-334)
```

## Advanced Search Techniques

### Time-Based Searches
```
recall "deployment issues" --recent=48  # Last 48 hours
recall "security patches" --recent=720   # Last 30 days
```

### Machine-Specific Searches
```
recall "performance issues" --machine=elastic1
recall "configuration changes" --machine=auth-server
```

### Category-Focused Searches
```
recall "backup procedures" runbooks
recall "vulnerability assessment" security
recall "load balancer config" infrastructure
```

### Boolean and Phrase Searches
```
recall "elasticsearch AND optimization"
recall '"502 bad gateway"'  # Exact phrase
recall "mysql NOT postgres"  # Exclude terms
```

## Performance Optimization
- **Search Speed**: ~200-500ms for most queries
- **Large Results**: Use --limit to control result size
- **Semantic Processing**: Slightly slower but more intelligent
- **Cache Benefits**: Repeated searches return faster
- **Network Efficiency**: Results compressed for fast transfer

## Error Scenarios and Solutions

### No Results Found
```
🚫 No memories found for: "rare-specific-term"
💡 Suggestions:
   ↳ Try broader terms: "database" instead of "mysql-5.7.33"
   ↳ Check other categories: try "infrastructure" or "incidents"
   ↳ Expand time range: remove --recent filter
   ↳ Use semantic search: natural language instead of keywords
```

### Too Many Results
```
⚠️  Search returned 247 results (showing top 10)
💡 Refinement options:
   ↳ Add category filter: recall "server" infrastructure
   ↳ Reduce time scope: --recent=72
   ↳ Be more specific: "server CPU usage" instead of "server"
   ↳ Increase limit: --limit=25 to see more results
```

### Low Confidence Results
```
🤔 Low confidence results (34% average)
💡 Improvement suggestions:
   ↳ Check spelling and try synonyms
   ↳ Use different search terms
   ↳ Try category-specific search
   ↳ Ask specialized agent: hv-query instead of recall
```

## Best Practices
- **Start Broad**: Begin with general terms, then narrow down
- **Use Categories**: Filter by category for focused results
- **Natural Language**: Don't hesitate to use conversational queries
- **Time Context**: Use --recent for current issue investigation
- **Follow Patterns**: Use "Related Patterns" suggestions for deeper research
- **Combine Approaches**: Use both recall and hv-query for comprehensive research

## Related Commands
- **For expert answers**: Use `hv-query` to consult specialized agents
- **To save findings**: Use `remember` to store your own discoveries
- **For real-time help**: Use `hv-delegate` to get immediate assistance
- **To share results**: Use `hv-broadcast` to inform collective

---

**Search Query**: $ARGUMENTS

This will search the collective memory using advanced semantic and text-based algorithms to find the most relevant historical information for your query.