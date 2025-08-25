---
description: Show recently used hAIveMind commands with outcomes and pattern analysis
allowed-tools: ["help_recent"]
argument-hint: [limit]
---

# recent - Command History & Pattern Analysis

## Purpose
Intelligent command history system that shows your recently used hAIveMind commands with success rates, execution times, and pattern analysis to help optimize your workflow and identify improvement opportunities.

## When to Use
- **Performance Analysis**: Review command success rates and execution times
- **Workflow Optimization**: Identify patterns in your command usage for efficiency improvements
- **Troubleshooting**: Analyze recent failures to identify recurring issues
- **Learning**: Understand your usage patterns and discover optimization opportunities
- **Audit Trail**: Review recent actions for compliance or debugging purposes
- **Pattern Recognition**: Discover successful command sequences for future use

## Syntax
```
recent [limit]
```

## Parameters
- **limit** (optional): Number of recent commands to display (default: 10, max: 50)
  - Examples: `recent 5`, `recent 20`, `recent 50`

## Intelligent Analysis Features

### Usage Pattern Recognition
- **Command Sequences**: Identifies common command patterns and their success rates
- **Timing Analysis**: Analyzes time between commands to identify workflow efficiency
- **Success Correlation**: Shows which command combinations lead to best outcomes
- **Context Awareness**: Correlates command usage with project types and situations
- **Trend Analysis**: Identifies changes in usage patterns over time

### Performance Insights
- **Execution Time Tracking**: Shows how long each command took to complete
- **Success Rate Analysis**: Tracks which commands succeed most often
- **Error Pattern Detection**: Identifies recurring failure patterns
- **Efficiency Metrics**: Calculates workflow efficiency and suggests improvements
- **Comparative Analysis**: Compares your patterns with collective best practices

## Real-World Examples

### Basic Recent Command History
```
recent
```
**Result**: Last 10 commands with timestamps, success status, execution times, and context

### Extended History Analysis
```
recent 25
```
**Result**: Last 25 commands with detailed pattern analysis, success trends, and optimization suggestions

### Quick Recent Check
```
recent 5
```
**Result**: Last 5 commands with focus on immediate recent activity and quick insights

## Expected Output

### Standard Recent Commands View
```
⏱️ Recent Command History - 2025-01-24 14:30:00

📊 Usage Summary (Last 10 commands):
   ↳ Total Commands: 10
   ↳ Success Rate: 90% (9 successful, 1 failed)
   ↳ Average Execution Time: 1.8 seconds
   ↳ Most Used: hv-status (3x), remember (2x), hv-query (2x)

🔄 Recent Commands:

1. ✓ hv-status --detailed                    14:28:45  1.2s  general
   ↳ Success: Checked collective health, found 2 agents with high response times
   ↳ Context: Routine health monitoring
   ↳ Follow-up: Led to investigation of performance issues

2. ✓ hv-broadcast "Database optimization completed" infrastructure info  14:25:30  0.8s  infrastructure
   ↳ Success: Notified 12 agents about database improvements
   ↳ Context: Completing database optimization project
   ↳ Impact: Team aware of performance improvements

3. ✓ remember "Database query optimization reduced response time by 60%" infrastructure  14:23:15  0.5s  documentation
   ↳ Success: Documented optimization results for future reference
   ↳ Context: Preserving successful optimization techniques
   ↳ Tags: database, optimization, performance

4. ✓ hv-delegate "Monitor database performance metrics" monitoring  14:20:45  2.1s  task_assignment
   ↳ Success: Assigned monitoring task to monitoring specialists
   ↳ Context: Ensuring optimization results are tracked
   ↳ Assigned to: monitoring-agent, grafana-agent

5. ✓ hv-query "database performance optimization techniques"  14:18:30  3.2s  research
   ↳ Success: Found 8 relevant memories with optimization strategies
   ↳ Context: Researching before implementing database changes
   ↳ Results: Query indexing, connection pooling, cache strategies

6. ✗ hv-sync --force                         14:15:20  timeout  system_maintenance
   ↳ Failed: Timeout during configuration synchronization
   ↳ Context: Attempting to update agent configurations
   ↳ Error: Network connectivity issues with 3 agents
   ↳ Resolution: Retry succeeded after network stabilized

7. ✓ recall "database issues last 7 days" incidents  14:12:10  1.9s  investigation
   ↳ Success: Retrieved 4 recent database-related incidents
   ↳ Context: Understanding recent database problems before optimization
   ↳ Findings: Connection pool issues, slow query patterns

8. ✓ hv-status                               14:10:05  0.9s  general
   ↳ Success: Quick health check before starting database work
   ↳ Context: Verifying system stability before changes
   ↳ Status: All systems operational, ready for optimization

9. ✓ help hv-delegate                        14:08:30  0.3s  learning
   ↳ Success: Reviewed delegation syntax and best practices
   ↳ Context: Learning proper task delegation techniques
   ↳ Outcome: Better understanding of specialist assignment

10. ✓ remember "Starting database optimization project" infrastructure  14:05:15  0.4s  documentation
    ↳ Success: Documented project initiation for tracking
    ↳ Context: Beginning systematic database performance improvement
    ↳ Project: Database optimization initiative

📈 Pattern Analysis:

🎯 Successful Command Sequences (Last 24 hours):
   1. help → hv-query → hv-delegate → hv-broadcast (Success Rate: 100%, Used 3 times)
      ↳ Pattern: Learn → Research → Assign → Communicate
      ↳ Average Duration: 8.2 minutes
      ↳ Effectiveness: High - leads to well-informed actions

   2. hv-status → recall → remember (Success Rate: 95%, Used 4 times)
      ↳ Pattern: Check → Research → Document
      ↳ Average Duration: 4.1 minutes
      ↳ Effectiveness: High - good for investigation workflows

   3. remember → hv-broadcast → hv-delegate (Success Rate: 90%, Used 2 times)
      ↳ Pattern: Document → Communicate → Assign
      ↳ Average Duration: 3.8 minutes
      ↳ Effectiveness: Good - effective for sharing and follow-up

⏱️ Timing Patterns:
   ↳ Average time between commands: 3.2 minutes
   ↳ Fastest sequence: help → hv-query (30 seconds)
   ↳ Longest gap: 15 minutes (between investigation and action)
   ↳ Most efficient hour: 14:00-15:00 (current session)

🚀 Performance Insights:
   ↳ Commands with <1s execution time: 60% (very efficient)
   ↳ Commands with >3s execution time: 20% (investigate optimization)
   ↳ Network-dependent commands: 30% (consider local caching)
   ↳ Documentation commands: 30% (good knowledge preservation)

💡 Optimization Recommendations:

1. 🎯 Workflow Efficiency
   ↳ Your "help → research → act" pattern is highly effective (100% success)
   ↳ Consider standardizing this approach for complex tasks
   ↳ Time savings: ~15% by following proven patterns

2. ⚡ Command Performance
   ↳ hv-query commands taking >3s - consider more specific search terms
   ↳ hv-sync timeout suggests network optimization needed
   ↳ Batch similar commands to reduce context switching

3. 📚 Documentation Habits
   ↳ Good documentation frequency (30% of commands)
   ↳ Consider adding more context tags to remember commands
   ↳ Document failed attempts for collective learning

4. 🔄 Pattern Optimization
   ↳ Your command sequences show good planning and follow-through
   ↳ Consider using workflows command for complex multi-step procedures
   ↳ Share successful patterns with team via hv-broadcast

📊 Comparative Analysis:
   ↳ Your success rate (90%) is above collective average (87%)
   ↳ Your documentation rate (30%) is excellent (collective: 18%)
   ↳ Your command diversity shows good tool utilization
   ↳ Time between commands suggests thoughtful execution

🎯 Recommended Next Steps:
   1. Continue current documentation practices - they're excellent
   2. Investigate hv-sync timeout issues for better reliability
   3. Consider using workflows for your successful command patterns
   4. Share your effective patterns with team via hv-broadcast
```

### Extended History with Deep Analysis
```
⏱️ Extended Command History Analysis - Last 25 Commands

📊 Comprehensive Usage Statistics:
   ↳ Total Commands: 25 (last 4 hours)
   ↳ Success Rate: 88% (22 successful, 3 failed)
   ↳ Average Execution Time: 2.1 seconds
   ↳ Command Diversity: 7 different commands used
   ↳ Most Active Period: 14:00-15:00 (12 commands)

🔍 Command Frequency Analysis:
   1. hv-status: 8 uses (32%) - Avg: 1.1s, Success: 100%
   2. remember: 5 uses (20%) - Avg: 0.6s, Success: 100%
   3. hv-query: 4 uses (16%) - Avg: 2.8s, Success: 75%
   4. hv-broadcast: 3 uses (12%) - Avg: 0.9s, Success: 100%
   5. hv-delegate: 2 uses (8%) - Avg: 2.3s, Success: 100%
   6. recall: 2 uses (8%) - Avg: 1.7s, Success: 100%
   7. hv-sync: 1 use (4%) - Avg: timeout, Success: 0%

📈 Trend Analysis (4-hour window):
   ↳ Command frequency increasing (2 → 5 → 8 → 10 per hour)
   ↳ Success rate stable around 88-92%
   ↳ Documentation rate increasing (good trend)
   ↳ Research-heavy period (multiple hv-query commands)

🎯 Advanced Pattern Recognition:

Workflow Pattern: "Database Optimization Project"
   Timeline: 14:05 - 14:30 (25 minutes)
   Commands: remember → help → hv-query → recall → hv-delegate → remember → hv-broadcast → hv-status
   Success Rate: 87.5% (7/8 successful)
   Outcome: Successful database optimization with team coordination
   
   Pattern Breakdown:
   1. Project initiation (remember) ✓
   2. Learning phase (help) ✓
   3. Research phase (hv-query) ✓
   4. Historical analysis (recall) ✓
   5. Task assignment (hv-delegate) ✓
   6. Documentation (remember) ✓
   7. Team communication (hv-broadcast) ✓
   8. Verification (hv-status) ✓

Success Factors:
   ✓ Systematic approach with clear phases
   ✓ Good balance of research and action
   ✓ Proper documentation at key points
   ✓ Team communication and coordination
   ✓ Verification of outcomes

🚨 Failure Analysis:

Failed Command: hv-sync --force (14:15:20)
   ↳ Error Type: Network timeout
   ↳ Context: System maintenance during active work
   ↳ Impact: Delayed workflow by 5 minutes
   ↳ Resolution: Retry after network stabilization
   ↳ Prevention: Check network status before sync operations

Failed Commands Pattern:
   ↳ 3 failures out of 25 commands (12% failure rate)
   ↳ All failures were network-related (hv-sync, hv-query timeouts)
   ↳ Failures clustered around 14:15-14:20 (network issue period)
   ↳ No command logic or parameter errors

🎯 Optimization Opportunities:

1. Network Reliability (Priority: High)
   ↳ 100% of failures were network-related
   ↳ Consider network diagnostics before critical operations
   ↳ Implement retry logic for network-dependent commands
   ↳ Monitor network status: hv-status --network

2. Query Optimization (Priority: Medium)
   ↳ hv-query commands averaging 2.8s (above optimal)
   ↳ Use more specific search terms to reduce search time
   ↳ Consider caching frequently accessed information
   ↳ Break complex queries into smaller, focused searches

3. Workflow Standardization (Priority: Low)
   ↳ Your successful patterns could be formalized into workflows
   ↳ Database optimization pattern highly successful (87.5%)
   ↳ Consider creating custom workflow templates
   ↳ Share successful patterns with collective via documentation

📊 Performance Benchmarking:

Your Performance vs. Collective Averages:
   ↳ Success Rate: 88% (You) vs 87% (Collective) - Above Average ✓
   ↳ Execution Time: 2.1s (You) vs 1.8s (Collective) - Slightly Slower
   ↳ Documentation Rate: 20% (You) vs 18% (Collective) - Above Average ✓
   ↳ Command Diversity: 7 types (You) vs 5.2 (Collective) - Above Average ✓

Strengths:
   ✓ Excellent documentation habits
   ✓ Good command diversity and tool utilization
   ✓ Systematic approach to complex tasks
   ✓ Strong success rate despite network challenges

Improvement Areas:
   ↳ Network connectivity optimization
   ↳ Query efficiency improvement
   ↳ Command execution speed optimization
```

## Advanced Analysis Features

### Pattern Learning and Prediction
- **Success Prediction**: Predicts likelihood of command success based on context and history
- **Workflow Recognition**: Automatically identifies recurring workflow patterns
- **Optimization Suggestions**: Recommends command sequence improvements
- **Timing Optimization**: Suggests optimal timing for command execution
- **Context Correlation**: Links command success to environmental factors

### Collective Intelligence Integration
- **Benchmark Comparison**: Compares your patterns with collective best practices
- **Success Rate Analysis**: Shows how your success rates compare to other agents
- **Pattern Sharing**: Identifies successful patterns worth sharing with collective
- **Learning Opportunities**: Suggests areas for improvement based on collective data
- **Best Practice Adoption**: Recommends proven patterns from high-performing agents

## Performance Considerations
- **History Storage**: Command history stored locally and in collective memory
- **Analysis Speed**: Pattern analysis completed in <500ms for typical history sizes
- **Memory Usage**: Optimized storage of command metadata and outcomes
- **Privacy**: Personal command history separate from collective analytics
- **Retention**: Command history retained for 30 days, patterns preserved longer

## Related Commands
- **For workflow optimization**: Use `workflows` to see formalized patterns
- **For command help**: Use `help <command>` to understand failed commands
- **For examples**: Use `examples` to see successful usage patterns
- **For suggestions**: Use `suggest` to get recommendations based on recent patterns
- **For analytics**: Use `help analytics` to see broader usage statistics

## Troubleshooting Recent Command Analysis

### Missing Command History
```
❓ No recent commands shown or incomplete history
💡 Possible Causes:
   1. New installation - history builds over time
   2. Command tracking not enabled
   3. History storage issues
   4. Use commands to build history for analysis
```

### Inaccurate Success Rates
```
⚠️ Success rates don't match actual experience
💡 Troubleshooting:
   1. Success tracking depends on command completion detection
   2. Network timeouts may be misclassified
   3. Manual verification of recent command outcomes
   4. Report discrepancies for system improvement
```

### Performance Analysis Issues
```
🐌 Pattern analysis taking too long or failing
💡 Resolution Steps:
   1. Reduce history limit for faster analysis
   2. Check system resources during analysis
   3. Clear analysis cache if available
   4. Report performance issues for optimization
```

## Best Practices for Command History Analysis
- **Regular Review**: Check recent commands daily to identify patterns and issues
- **Learn from Failures**: Analyze failed commands to prevent future issues
- **Optimize Patterns**: Use successful patterns as templates for future work
- **Share Insights**: Document and share successful patterns with team
- **Track Improvements**: Monitor how changes affect success rates and efficiency
- **Use for Planning**: Let recent patterns inform future workflow planning

---

**Continuous Improvement**: The recent command analysis system learns from your usage patterns to provide increasingly accurate insights and optimization recommendations, helping you become more effective over time.