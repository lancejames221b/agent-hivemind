---
description: Interactive help system for hAIveMind commands with context-aware suggestions
allowed-tools: ["help_show"]
argument-hint: [command] [--detailed]
---

# help - Interactive Command Help

## Purpose
Intelligent, context-aware help system that provides comprehensive guidance for hAIveMind commands with smart suggestions based on your current situation and usage patterns.

## When to Use
- **Learning hAIveMind**: New users discovering available commands and capabilities
- **Command Reference**: Quick lookup of syntax, parameters, and usage patterns
- **Troubleshooting**: When commands aren't working as expected
- **Context Guidance**: Get suggestions relevant to your current project or situation
- **Workflow Planning**: Understand how commands work together
- **Best Practices**: Learn optimal usage patterns from collective experience

## Syntax
```
help [command] [--detailed]
```

## Parameters
- **command** (optional): Specific command to get detailed help for
  - Examples: `hv-broadcast`, `hv-status`, `remember`, `recall`
- **--detailed** (optional): Show comprehensive help with examples, troubleshooting, and related commands

## Interactive Help Features

### Smart Context Awareness
- **Project Detection**: Automatically detects Python, Node.js, Rust, Go projects
- **Incident Response**: Prioritizes incident-related commands during active issues
- **Usage Patterns**: Learns from your command history to provide relevant suggestions
- **Agent Status**: Considers collective health when suggesting commands
- **Recent Activity**: Adapts suggestions based on your recent command usage

### Intelligent Suggestions
- **Command Completion**: Fuzzy matching for partial command names (e.g., "broad" → "hv-broadcast")
- **Parameter Guidance**: Context-aware parameter suggestions and validation
- **Workflow Recommendations**: Suggests logical next steps based on current command
- **Error Prevention**: Warns about common mistakes before execution
- **Related Commands**: Shows commands that work well together

## Real-World Examples

### General Help Overview
```
help
```
**Result**: Interactive dashboard showing all available commands, categorized by function, with context-aware suggestions based on your current situation

### Specific Command Help
```
help hv-broadcast
```
**Result**: Detailed help for hv-broadcast including syntax, parameters, examples, and context-specific usage tips

### Comprehensive Command Documentation
```
help hv-status --detailed
```
**Result**: Full documentation with troubleshooting guides, performance considerations, related workflows, and real-world usage patterns

### Context-Aware Suggestions During Incidents
```
help
```
**During Active Incident**: Prioritizes incident response commands (hv-status, hv-broadcast, hv-delegate) with emergency workflow guidance

### Project-Specific Guidance
```
help
```
**In Python Project**: Suggests commands relevant to Python development workflows, deployment patterns, and common infrastructure needs

## Expected Output

### General Help Dashboard
```
🤖 hAIveMind Interactive Help System - 2025-01-24 14:30:00

📋 Available Commands (8 total):

🔧 Core Operations:
   • hv-status    - Monitor collective health and agent availability
   • hv-sync      - Synchronize configurations and commands
   • hv-install   - Install and update hAIveMind components

💬 Communication:
   • hv-broadcast - Share critical findings with all agents
   • hv-query     - Search collective knowledge and expertise
   • hv-delegate  - Assign tasks to specialized agents

🧠 Memory Management:
   • remember     - Store knowledge in collective memory
   • recall       - Retrieve stored memories and insights

🎯 Context Suggestions (Based on Current Situation):
   ↳ Start with: hv-status (check collective health)
   ↳ Active incident detected: Consider hv-broadcast for team coordination
   ↳ Python project: Use remember to document deployment configurations

📊 Recent Usage:
   ↳ 12 commands used today (92% success rate)
   ↳ Most used: hv-status (5x), remember (3x), hv-query (2x)

🚀 Quick Start Guide:
   1. hv-status     → Check collective health
   2. hv-query      → Search for relevant knowledge
   3. hv-delegate   → Assign tasks to specialists
   4. hv-broadcast  → Share important findings
   5. remember      → Document solutions for future

💡 Interactive Help Commands:
   • help <command>  - Detailed help for specific command
   • examples        - Show contextual examples
   • workflows       - Common command patterns
   • recent          - Your command history and patterns
   • suggest         - AI-powered command recommendations
```

### Specific Command Help
```
📖 Help: hv-broadcast

🎯 Purpose: Broadcast critical findings to all hAIveMind collective agents

📝 Usage: hv-broadcast "[message]" [category] [severity]

🔧 Parameters:
   • message (required)  - Clear, actionable description of finding
   • category (required) - Type: security, infrastructure, incident, deployment, monitoring, runbook
   • severity (optional) - Level: critical, warning, info (default: info)

💡 Context Suggestions:
   ↳ Active incident detected: Consider using 'critical' severity
   ↳ Recent hv-query usage: Share findings from your research
   ↳ Security context: Use 'security' category for vulnerability reports

🔗 Related Commands:
   • hv-delegate - Assign follow-up tasks after broadcasting
   • hv-status   - Check if broadcast reached all agents
   • remember    - Document the issue for future reference

⚡ Quick Examples:
   • hv-broadcast "Database deadlock resolved" incident warning
   • hv-broadcast "Security patch deployed" security info
   • hv-broadcast "Load balancer updated" infrastructure info

📚 For detailed examples and troubleshooting: help hv-broadcast --detailed
```

### Context-Aware Error Guidance
```
❓ Command Not Found: "brodcast"

🔍 Did you mean one of these?
   1. hv-broadcast  - Share critical findings (90% match)
   2. hv-delegate   - Assign tasks to agents (30% match)

💡 Tip: Use fuzzy matching - partial names work too!
   • Type "broad" to get "hv-broadcast"
   • Type "stat" to get "hv-status"
   • Type "del" to get "hv-delegate"

🎯 Based on your recent activity, you might want:
   • hv-broadcast - You recently used hv-query, consider sharing findings
   • hv-status    - Check system health before broadcasting
```

## Advanced Features

### Learning and Adaptation
- **Usage Analytics**: Tracks which help topics are most accessed
- **Effectiveness Monitoring**: Learns which suggestions lead to successful outcomes
- **Pattern Recognition**: Identifies common user confusion points
- **Collective Intelligence**: Shares effective help patterns across agents
- **Continuous Improvement**: Updates suggestions based on collective usage data

### Integration with hAIveMind
- **Memory Storage**: All help interactions stored for system learning
- **Cross-Agent Learning**: Effective help patterns shared across collective
- **Context Synchronization**: Help system aware of collective status and incidents
- **Performance Optimization**: Caches frequently accessed help content
- **Analytics Dashboard**: Tracks help system effectiveness and usage patterns

## Performance Considerations
- **Response Time**: < 200ms for cached help content
- **Memory Usage**: Help content cached for 1 hour to improve performance
- **Network Impact**: Minimal - most help content served locally
- **Learning Overhead**: Usage tracking adds ~50ms per interaction
- **Cache Efficiency**: 95%+ hit rate for frequently accessed commands

## Related Commands
- **After getting help**: Use the suggested command with proper parameters
- **For examples**: Use `examples <command>` for practical usage scenarios
- **For workflows**: Use `workflows` to see command sequences and patterns
- **For recent activity**: Use `recent` to analyze your usage patterns
- **For suggestions**: Use `suggest` for AI-powered recommendations

## Troubleshooting Help System Issues

### Help Command Not Responding
```
❌ Help system timeout or error
💡 Troubleshooting Steps:
   1. Check MCP server: curl http://localhost:8900/health
   2. Verify help system initialization: help analytics
   3. Clear help cache: help --detailed (forces refresh)
   4. Check system resources: top, free -m
```

### Outdated or Incorrect Help Content
```
⚠️  Help content seems outdated
💡 Resolution Steps:
   1. Force help system refresh: help --detailed
   2. Check for system updates: hv-sync
   3. Verify command documentation: ls commands/
   4. Report issue: remember "Help system issue: [description]" infrastructure
```

### Missing Context Suggestions
```
❓ No context-aware suggestions shown
💡 Possible Causes:
   1. New installation - context builds over time
   2. No recent command usage tracked
   3. Help system learning in progress
   4. Use commands and suggestions will improve
```

## Best Practices for Using Help System
- **Start Broad**: Use `help` without parameters to get overview and suggestions
- **Be Specific**: Use `help <command>` for detailed guidance on specific commands
- **Use Context**: Help system gets smarter as you use it - provide feedback
- **Explore Examples**: Use `examples` command for practical usage scenarios
- **Follow Workflows**: Use `workflows` for step-by-step guidance on complex tasks
- **Track Progress**: Help system learns from your usage to provide better suggestions

---

**Interactive Help**: The help system adapts to your usage patterns and current context to provide increasingly relevant and useful guidance. The more you use it, the smarter it becomes.