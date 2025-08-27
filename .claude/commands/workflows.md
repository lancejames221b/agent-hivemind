---
description: Show common hAIveMind command workflows and operational patterns
allowed-tools: ["help_workflows"]
argument-hint: [workflow_type]
---

# workflows - Command Workflows & Patterns

## Purpose
Comprehensive workflow system that provides step-by-step guidance for common operational patterns, showing how hAIveMind commands work together to accomplish complex tasks efficiently and reliably.

## When to Use
- **Complex Operations**: Multi-step procedures requiring coordination across multiple agents
- **Incident Response**: Structured approach to handling system outages and emergencies
- **Daily Operations**: Routine maintenance and monitoring workflows
- **Security Procedures**: Systematic security assessment and response workflows
- **Deployment Management**: Coordinated deployment and rollback procedures
- **Knowledge Transfer**: Learning operational best practices from collective experience

## Syntax
```
workflows [workflow_type]
```

## Parameters
- **workflow_type** (optional): Specific workflow category to display
  - `incident_response` - Emergency incident handling procedures
  - `daily_maintenance` - Regular system health and maintenance routines
  - `security_audit` - Comprehensive security assessment workflows
  - `deployment` - Application deployment and rollback procedures
  - `monitoring_setup` - Proactive monitoring and alerting configuration
  - `knowledge_management` - Information capture and sharing workflows

## Intelligent Workflow Features

### Context-Aware Recommendations
- **Incident Detection**: Automatically suggests incident response workflows during active issues
- **Project Type Adaptation**: Workflows adapted for Python, Node.js, Rust, Go projects
- **Agent Availability**: Adjusts workflows based on currently available specialist agents
- **Historical Success**: Prioritizes workflows with highest success rates
- **Time-Sensitive Operations**: Highlights urgent workflows during critical situations

### Success Metrics and Analytics
- **Completion Rates**: Shows workflow success percentages based on historical data
- **Time Estimates**: Realistic time estimates based on actual execution data
- **Bottleneck Identification**: Identifies common failure points and provides alternatives
- **Performance Optimization**: Suggests workflow improvements based on collective experience
- **Effectiveness Tracking**: Monitors which workflows lead to successful outcomes

## Real-World Examples

### Show All Available Workflows
```
workflows
```
**Result**: Complete catalog of available workflows with success rates, time estimates, and context-aware recommendations

### Incident Response Workflow
```
workflows incident_response
```
**Result**: Step-by-step incident handling procedures with decision trees and escalation paths

### Daily Maintenance Routine
```
workflows daily_maintenance
```
**Result**: Structured daily operational checklist with health monitoring and preventive maintenance

### Security Audit Workflow
```
workflows security_audit
```
**Result**: Comprehensive security assessment procedures with compliance verification

## Expected Output

### Complete Workflow Catalog
```
🔄 hAIveMind Command Workflows & Patterns - 2025-01-24 14:30:00

📊 Available Workflows (6 total):

🚨 Incident Response Workflow
   ↳ Handle system incidents and outages with coordinated team response
   ↳ Estimated Time: 15-30 minutes
   ↳ Success Rate: 94% (47 successful completions)
   ↳ Last Used: 2 hours ago (database connectivity incident)

🔧 Daily Maintenance Routine
   ↳ Regular health checks and preventive maintenance procedures
   ↳ Estimated Time: 5-10 minutes
   ↳ Success Rate: 98% (156 successful completions)
   ↳ Recommended: Every morning at 9:00 AM

🛡️ Security Audit Workflow
   ↳ Comprehensive security assessment and vulnerability management
   ↳ Estimated Time: 30-60 minutes
   ↳ Success Rate: 91% (23 successful completions)
   ↳ Recommended: Weekly on Fridays

🚀 Deployment Workflow
   ↳ Coordinated application deployment with rollback procedures
   ↳ Estimated Time: 10-25 minutes
   ↳ Success Rate: 96% (89 successful completions)
   ↳ Last Used: Yesterday (API v2.1.3 deployment)

📊 Monitoring Setup Workflow
   ↳ Proactive monitoring and alerting configuration
   ↳ Estimated Time: 20-45 minutes
   ↳ Success Rate: 89% (34 successful completions)
   ↳ Recommended: After infrastructure changes

🧠 Knowledge Management Workflow
   ↳ Information capture, documentation, and sharing procedures
   ↳ Estimated Time: 5-15 minutes
   ↳ Success Rate: 97% (78 successful completions)
   ↳ Recommended: After resolving issues or learning new procedures

🎯 Context Recommendations (Based on Current Situation):
   ↳ Active incident detected: Start with 'Incident Response Workflow'
   ↳ Python project: Include deployment workflow considerations
   ↳ Recent security queries: Consider 'Security Audit Workflow'
   ↳ Morning routine: 'Daily Maintenance Routine' recommended

📈 Popular Command Patterns (Last 30 Days):
   1. hv-status → hv-query → hv-delegate (used 23 times, 96% success)
   2. hv-broadcast → hv-delegate → hv-status (used 18 times, 94% success)
   3. remember → hv-broadcast → hv-query (used 15 times, 100% success)
   4. hv-query → recall → remember (used 12 times, 92% success)

💡 Workflow Optimization Tips:
   ↳ Workflows with >95% success rate are considered highly reliable
   ↳ Time estimates based on median completion times across all agents
   ↳ Success rates improve with practice - repeat workflows become faster
   ↳ Custom workflows can be created by documenting successful command sequences
```

### Incident Response Workflow Detail
```
🚨 Incident Response Workflow - Emergency System Recovery

📋 Overview:
   ↳ Purpose: Systematic approach to handling system incidents and outages
   ↳ Success Rate: 94% (47 completions)
   ↳ Average Duration: 22 minutes
   ↳ Last Updated: Based on collective experience from 156 incidents

🔄 Workflow Steps:

Step 1: 🔍 Initial Assessment (2-3 minutes)
   Command: hv-status --detailed
   Purpose: Assess collective health and identify scope of issue
   Success Criteria: ✓ Agent availability confirmed, ✓ Issue scope identified
   
   Expected Output:
   • Agent response times and availability
   • System resource utilization
   • Active alerts and warnings
   • Network connectivity status
   
   Decision Point: If >50% agents unresponsive → Escalate to critical

Step 2: 📢 Team Notification (1-2 minutes)
   Command: hv-broadcast "[incident description]" incident critical
   Purpose: Alert all agents and activate incident response team
   Success Criteria: ✓ All available agents notified, ✓ Response team activated
   
   Message Template:
   "System incident detected: [brief description] - investigating"
   
   Parameters:
   • Use 'critical' severity for customer-impacting issues
   • Use 'warning' severity for internal/performance issues
   • Include affected systems and initial impact assessment

Step 3: 🎯 Task Delegation (3-5 minutes)
   Command: hv-delegate "[specific investigation task]" [specialist_type]
   Purpose: Assign specific investigation and remediation tasks
   Success Criteria: ✓ Tasks assigned to appropriate specialists, ✓ Investigation begun
   
   Common Delegations:
   • "Investigate database connection issues" → database_ops
   • "Check load balancer health and routing" → infrastructure_management
   • "Analyze application error logs" → development
   • "Monitor network connectivity" → monitoring
   
   Parallel Execution: Delegate multiple tasks simultaneously for faster resolution

Step 4: 🔍 Knowledge Search (2-4 minutes)
   Command: hv-query "[incident keywords] similar issues resolution"
   Purpose: Find similar past incidents and proven solutions
   Success Criteria: ✓ Relevant past incidents found, ✓ Solution patterns identified
   
   Search Strategies:
   • Include error messages or symptoms
   • Search for component names (database, load balancer, etc.)
   • Look for time-based patterns (morning issues, deployment-related)
   • Review recent changes that might be related

Step 5: 🔧 Solution Implementation (5-15 minutes)
   Commands: Varies based on investigation findings
   Purpose: Execute remediation based on investigation results
   Success Criteria: ✓ Root cause identified, ✓ Solution implemented, ✓ Service restored
   
   Common Solutions:
   • Service restarts: hv-delegate "Restart [service]" infrastructure_management
   • Configuration rollbacks: hv-delegate "Rollback [config]" deployment
   • Resource scaling: hv-delegate "Scale [resource]" infrastructure_management
   • Database maintenance: hv-delegate "Clear [database issue]" database_ops

Step 6: ✅ Verification and Communication (2-3 minutes)
   Commands: hv-status → hv-broadcast
   Purpose: Verify resolution and communicate status to team
   Success Criteria: ✓ System health restored, ✓ Team notified of resolution
   
   Verification Checklist:
   • All agents responding normally
   • System metrics within normal ranges
   • No active alerts or warnings
   • Customer-facing services operational
   
   Resolution Message: "Incident resolved: [brief solution] - monitoring for stability"

Step 7: 📚 Documentation and Learning (3-5 minutes)
   Command: remember "[incident summary and resolution]" incidents
   Purpose: Document incident for future reference and learning
   Success Criteria: ✓ Incident documented, ✓ Solution preserved for collective knowledge
   
   Documentation Template:
   • Root Cause: [technical cause]
   • Impact: [affected systems and duration]
   • Resolution: [steps taken to resolve]
   • Prevention: [measures to prevent recurrence]
   • Timeline: [key timestamps]

🎯 Success Factors:
   ✓ Quick initial assessment prevents issue escalation
   ✓ Parallel task delegation reduces resolution time
   ✓ Knowledge search prevents reinventing solutions
   ✓ Clear communication keeps team coordinated
   ✓ Documentation prevents future similar incidents

⚠️ Common Pitfalls:
   ❌ Skipping initial assessment leads to misdirected efforts
   ❌ Broadcasting too frequently creates noise and confusion
   ❌ Not delegating tasks results in single-point bottlenecks
   ❌ Forgetting documentation loses valuable learning opportunities

📊 Performance Metrics:
   • Median Resolution Time: 18 minutes
   • 90th Percentile: 35 minutes
   • Customer Impact Reduction: 67% vs. ad-hoc response
   • Team Satisfaction: 4.2/5 (based on post-incident surveys)

🔗 Related Workflows:
   • Security Incident Response (for security-related issues)
   • Deployment Rollback (for deployment-related incidents)
   • Performance Investigation (for performance degradation)
```

### Daily Maintenance Routine
```
🔧 Daily Maintenance Routine - Proactive System Health

📋 Overview:
   ↳ Purpose: Regular health checks and preventive maintenance
   ↳ Success Rate: 98% (156 completions)
   ↳ Average Duration: 7 minutes
   ↳ Recommended Schedule: Every morning at 9:00 AM

🔄 Workflow Steps:

Step 1: 🌡️ System Health Check (2-3 minutes)
   Command: hv-status
   Purpose: Get overview of collective health and identify any issues
   Success Criteria: ✓ All critical agents responding, ✓ No critical alerts
   
   Health Indicators to Monitor:
   • Agent response times (should be <400ms)
   • Memory usage (should be <60%)
   • Network connectivity (should be >90% agents reachable)
   • Active incidents (should be 0 critical incidents)
   
   Action Triggers:
   • >3 agents offline → Investigate connectivity
   • Memory usage >80% → Schedule cleanup
   • Response times >800ms → Check system resources

Step 2: 🔄 Configuration Sync (1-2 minutes)
   Command: hv-sync
   Purpose: Ensure all agents have current configurations and commands
   Success Criteria: ✓ All configurations synchronized, ✓ No sync conflicts
   
   Sync Verification:
   • Command versions match across agents
   • Configuration files are current
   • No pending updates or conflicts
   • Agent registrations are up to date

Step 3: 📚 Recent Activity Review (2-3 minutes)
   Command: recall "important findings last 24 hours" incidents
   Purpose: Review recent incidents, solutions, and important discoveries
   Success Criteria: ✓ Recent incidents reviewed, ✓ Lessons learned identified
   
   Review Focus Areas:
   • Unresolved incidents or ongoing issues
   • Successful problem resolutions to share
   • Performance trends or degradation patterns
   • Security events or vulnerability reports
   
   Follow-up Actions:
   • Share important findings: hv-broadcast
   • Delegate follow-up tasks: hv-delegate
   • Document patterns: remember

Step 4: 🎯 Proactive Issue Detection (1-2 minutes)
   Command: hv-query "potential issues trending warnings"
   Purpose: Identify potential issues before they become critical
   Success Criteria: ✓ Trending issues identified, ✓ Preventive actions planned
   
   Proactive Monitoring:
   • Resource utilization trends
   • Error rate increases
   • Performance degradation patterns
   • Security vulnerability reports
   
   Prevention Actions:
   • Schedule maintenance: hv-delegate
   • Update monitoring thresholds
   • Plan capacity upgrades
   • Apply security patches

✅ Daily Maintenance Checklist:
   □ System health verified (all agents responding)
   □ Configurations synchronized across collective
   □ Recent incidents reviewed and documented
   □ Proactive issues identified and addressed
   □ Team notified of any important findings
   □ Preventive actions scheduled as needed

📊 Maintenance Metrics:
   • Issues Prevented: 23 potential incidents caught early this month
   • System Uptime: 99.7% (improved from 98.2% before routine)
   • Mean Time to Detection: Reduced by 45%
   • Team Satisfaction: 4.6/5 (routine provides confidence and clarity)

🎯 Optimization Tips:
   ↳ Run at consistent time daily for trend analysis
   ↳ Automate routine checks where possible
   ↳ Document patterns for continuous improvement
   ↳ Share findings with team for collective awareness
```

## Advanced Workflow Features

### Workflow Customization
- **Adaptive Steps**: Workflows adjust based on current system state and available agents
- **Conditional Logic**: Decision trees guide workflow execution based on intermediate results
- **Parallel Execution**: Multiple workflow steps can run simultaneously for efficiency
- **Rollback Procedures**: Each workflow includes rollback steps for failed operations
- **Success Validation**: Built-in verification steps ensure workflow objectives are met

### Learning and Improvement
- **Success Analytics**: Tracks which workflow variations lead to best outcomes
- **Bottleneck Analysis**: Identifies common failure points and suggests optimizations
- **Time Optimization**: Learns from execution times to provide better estimates
- **Pattern Recognition**: Identifies successful command sequences for new workflow creation
- **Collective Intelligence**: Workflows improve based on collective usage across all agents

## Performance Considerations
- **Execution Time**: Workflows optimized for parallel execution where possible
- **Resource Usage**: Considers agent availability and system load during execution
- **Network Efficiency**: Minimizes network calls through intelligent command batching
- **Cache Utilization**: Frequently used workflows cached for faster access
- **Monitoring Impact**: Workflow execution monitored for performance optimization

## Related Commands
- **Before starting workflow**: Use `hv-status` to verify system readiness
- **During workflow**: Use individual commands as specified in workflow steps
- **For customization**: Use `examples` to see variations of workflow commands
- **For validation**: Use `help validate` to check command parameters
- **After completion**: Use `remember` to document workflow outcomes and improvements

## Troubleshooting Workflows

### Workflow Execution Failures
```
❌ Workflow step failed or timed out
💡 Troubleshooting Steps:
   1. Check agent availability: hv-status
   2. Verify network connectivity: ping [agent-machines]
   3. Review command parameters for errors
   4. Check system resources: top, free -m
   5. Retry individual failed step
   6. Use alternative workflow path if available
```

### Incomplete Workflow Results
```
⚠️ Workflow completed but objectives not met
💡 Analysis Steps:
   1. Review workflow success criteria
   2. Check intermediate step results
   3. Verify agent responses and confirmations
   4. Look for environmental changes during execution
   5. Consider workflow customization for current situation
```

### Workflow Performance Issues
```
🐌 Workflow taking longer than expected
💡 Optimization Steps:
   1. Check agent response times: hv-status
   2. Identify bottleneck steps in workflow
   3. Consider parallel execution of independent steps
   4. Review system resource utilization
   5. Use workflow analytics to identify optimization opportunities
```

## Best Practices for Using Workflows
- **Understand Prerequisites**: Ensure system meets workflow requirements before starting
- **Follow Steps Sequentially**: Don't skip steps unless workflow explicitly allows it
- **Monitor Progress**: Check intermediate results to catch issues early
- **Document Variations**: Record successful workflow modifications for future use
- **Share Improvements**: Use `remember` to document workflow enhancements
- **Practice Regularly**: Regular workflow execution improves speed and reliability

---

**Operational Excellence**: Workflows represent collective operational wisdom, providing proven patterns for complex tasks while continuously improving through collective experience and analytics.