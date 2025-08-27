---
description: Store knowledge and experiences in hAIveMind collective memory
allowed-tools: ["mcp__haivemind__store_memory"]
argument-hint: "memory content" [category] [--tags="tag1,tag2"] [--private] [--important]
---

# remember - Knowledge Storage

## Purpose
Store valuable knowledge, experiences, solutions, and insights in the hAIveMind collective memory for future reference by all agents.

## When to Use
- **Problem Solutions**: Save successful fixes and workarounds
- **Configuration Changes**: Document important system modifications
- **Lessons Learned**: Record insights from incidents or projects
- **Best Practices**: Share effective procedures and approaches
- **Important Discoveries**: Save research findings or optimization techniques
- **Team Knowledge**: Preserve expertise that others can benefit from

## Syntax
```
remember "content to store" [category] [options]
```

## Parameters
- **content** (required): The knowledge, solution, or information to store
- **category** (optional): Memory classification for better organization
  - `infrastructure`: System configs, hardware, network setup
  - `incidents`: Problem reports, root causes, resolutions
  - `security`: Vulnerabilities, patches, security procedures
  - `deployments`: Release processes, rollback procedures
  - `monitoring`: Alert configs, dashboard setups, metrics
  - `runbooks`: Step-by-step procedures, automation scripts
  - `project`: Project-specific knowledge and context
- **options** (optional):
  - `--tags="tag1,tag2"`: Manual tags for better searchability
  - `--private`: Store only for this machine (not shared)
  - `--important`: Mark as high-priority memory
  - `--expires=days`: Auto-delete after N days (default: never)

## Memory Processing Intelligence

### Automatic Content Analysis
- **Smart Categorization**: AI determines most appropriate category
- **Tag Generation**: Automatically extracts relevant keywords
- **Sentiment Analysis**: Identifies success/failure patterns
- **Technical Extraction**: Parses commands, configs, error codes
- **Relationship Mapping**: Links to related existing memories

### Content Enhancement
- **Context Addition**: Adds timestamp, machine, agent info
- **Search Optimization**: Processes content for better discoverability
- **Version Tracking**: Links to previous versions if updated
- **Cross-References**: Identifies connections to other memories

## Real-World Examples

### Solution Documentation
```
remember "Fixed elasticsearch high CPU by adding query timeout of 30s in elasticsearch.yml: search.default_search_timeout: 30s. CPU dropped from 95% to 45% within 10 minutes" infrastructure --tags="elasticsearch,performance,timeout"
```
**Result**: Solution stored with infrastructure category and searchable tags

### Incident Resolution
```
remember "Database deadlock resolved by optimizing transaction order in user registration flow. Changed to: 1) create user record 2) update profile 3) send email. Eliminated 90% of deadlock errors" incidents --important
```
**Result**: Critical incident solution marked as high-priority

### Configuration Change
```
remember "Updated nginx worker_processes to auto and worker_connections to 2048 for better performance on 8-core servers. Load time improved by 40%" infrastructure
```
**Result**: Performance optimization documented for future reference

### Security Finding
```
remember "JWT tokens should expire in 15 minutes for API access, 7 days for refresh tokens. Implemented sliding window refresh to maintain UX while improving security" security --tags="jwt,authentication,tokens"
```
**Result**: Security best practice stored with appropriate classification

### Troubleshooting Discovery
```
remember "502 bad gateway errors from nginx always indicate upstream server issues. Check: 1) backend service status 2) port connectivity 3) firewall rules 4) backend health endpoints" runbooks
```
**Result**: Troubleshooting procedure stored as operational runbook

## Expected Output

### Successful Storage
```
📦 Storing Memory in hAIveMind Collective...

🧠 Content Analysis:
   ↳ Length: 847 characters
   ↳ Technical terms detected: elasticsearch, CPU, query timeout, elasticsearch.yml
   ↳ Suggested category: infrastructure (confidence: 94%)
   ↳ Auto-generated tags: elasticsearch, performance, optimization, CPU, timeout

🏷️  Memory Classification:
   ↳ Category: infrastructure
   ↳ Priority: normal  
   ↳ Sharing: collective (all agents)
   ↳ Retention: permanent

💾 Storage Complete:
   ↳ Memory ID: mem-20250124-1530-789
   ↳ Stored on: lance-dev
   ↳ Synced to: 11 other agents
   ↳ Search ready: ~30 seconds

🔗 Related Memories Found:
   ↳ elasticsearch performance tuning (3 similar memories)
   ↳ query optimization techniques (5 related memories)
   ↳ CPU usage troubleshooting (8 connected memories)

✅ Memory successfully added to collective knowledge!
   Use: recall "elasticsearch CPU performance" to find this memory
```

### Memory with Manual Tags
```
📦 Storing Tagged Memory...

🏷️  Manual Tags Applied: jwt, authentication, tokens
🧠 AI-Generated Tags: security, expiration, refresh-token, sliding-window
📊 Combined Tags: jwt, authentication, tokens, security, expiration, refresh-token, sliding-window

💾 Storage Details:
   ↳ Memory ID: mem-20250124-1535-234
   ↳ Category: security (auto-detected)
   ↳ Priority: normal
   ↳ Searchability: Enhanced with 7 tags

✅ Memory stored and ready for collective access!
```

### Private Memory Storage
```
🔒 Storing Private Memory (local only)...

⚠️  Note: This memory will only be accessible from this machine
💾 Storage: Local ChromaDB only (not shared with collective)

✅ Private memory stored locally
   Use: recall "query" --machine=lance-dev to find this memory
```

## Memory Categories and Use Cases

### Infrastructure Category
- Server configurations and optimizations
- Network setup and troubleshooting
- Performance tuning discoveries
- Hardware-related solutions
- Service deployment configurations

### Incidents Category  
- Problem descriptions and root causes
- Resolution steps and outcomes
- Post-mortem findings
- Recurring issue patterns
- Emergency response procedures

### Security Category
- Vulnerability findings and patches
- Security configuration best practices
- Compliance requirements and audits
- Authentication and authorization setups
- Security incident responses

### Runbooks Category
- Step-by-step operational procedures
- Automation scripts and their usage
- Maintenance schedules and checklists
- Recovery procedures
- Standard operating procedures

## Memory Quality Guidelines

### Effective Memory Content
- **Be Specific**: Include exact commands, file paths, error messages
- **Provide Context**: Explain when/why solution was needed
- **Include Outcomes**: Describe results and impact
- **Add Details**: Version numbers, system specs, timing info
- **Use Clear Language**: Write for future readers who lack context

### Examples of Good vs Poor Memories

**Good Memory:**
```
remember "Fixed Redis memory leak by upgrading from 6.0.9 to 6.2.6 and adding 'maxmemory-policy allkeys-lru' to redis.conf. Memory usage dropped from 8GB to 2GB constant. Applied to redis-primary and redis-replica on 2025-01-24." infrastructure
```

**Poor Memory:**  
```
remember "Fixed Redis issue" infrastructure
```

## Performance Considerations
- **Storage Time**: ~2-5 seconds for typical memories
- **Sync Time**: ~10-30 seconds to propagate to all agents
- **Search Availability**: ~30 seconds after storage
- **Storage Size**: ~1-5KB per memory (text compressed)
- **Network Impact**: Minimal, uses efficient delta sync

## Error Scenarios and Solutions

### Storage Failures
```
❌ Error: Failed to store memory (network timeout)
💡 Solutions:
   1. Check collective connectivity: hv-status
   2. Retry with simpler content
   3. Try private storage: remember "content" --private
   4. Check disk space and permissions
```

### Content Too Large
```
⚠️  Warning: Memory content exceeds recommended size (5000 chars)
💡 Recommendations:
   1. Summarize key points instead of full logs
   2. Store detailed info in external docs, reference in memory
   3. Split into multiple focused memories
   4. Use --expires option for temporary large content
```

### Categorization Issues
```
🤔 AI uncertain about category (45% confidence)
💡 Suggestions:
   1. Manually specify category: remember "content" infrastructure
   2. Add more context to help AI classification
   3. Use specific technical terms in content
   4. Review and correct after storage if needed
```

## Best Practices for Memory Storage
- **Document Solutions**: Always remember successful fixes
- **Include Commands**: Store exact commands that worked
- **Add Context**: Explain the situation and environment
- **Use Good Tags**: Help future searches find your memory
- **Be Detailed**: Future you will thank present you
- **Share Knowledge**: Don't use --private unless truly sensitive
- **Update When Needed**: Remember improvements to existing solutions

## Related Commands
- **Before storing**: Use `recall` to check if similar memory exists
- **After storing**: Use `hv-broadcast` to announce important discoveries
- **For verification**: Use `recall` to confirm memory was stored correctly
- **For sharing**: Use `hv-query` to help others find your stored knowledge

---

**Memory to Store**: $ARGUMENTS

This will process, categorize, and store your memory in the hAIveMind collective knowledge base where it will be available for instant recall by all connected agents.