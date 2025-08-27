---
description: List and filter hAIveMind tickets with memory integration and agent coordination
allowed-tools: ["mcp__vibe_kanban__*", "mcp__haivemind__search_memories"]
argument-hint: [project_id] [options]
---

# ticket-list - hAIveMind Ticket Browser

## Purpose
List, filter, and browse tickets across hAIveMind projects with integrated memory context and agent coordination information.

## When to Use
- **Project Planning**: Review all project tickets and status
- **Workload Management**: See agent assignments and capacity
- **Progress Tracking**: Monitor ticket completion across projects
- **Context Discovery**: Find tickets related to current work
- **Dependency Analysis**: Understand ticket relationships

## Syntax
```
ticket-list [project_id] [options]
```

## Filtering Options

### By Project
```
ticket-list memory-mcp-project
ticket-list ewitness-project --status todo
```

### By Status
```
ticket-list --status inprogress
ticket-list --status done --limit 20
ticket-list --status todo,inreview
```

### By Agent
```
ticket-list --agent frontend-specialist
ticket-list --assigned-to lj-agent
ticket-list --unassigned
```

### By Priority
```
ticket-list --priority high,critical
ticket-list --priority low --status todo
```

### By Tags
```
ticket-list --tags webtests,ui
ticket-list --tags api,security --status inprogress
```

### By Date Range
```
ticket-list --created-since 2025-01-20
ticket-list --updated-today
ticket-list --completed-this-week
```

## Memory Integration Features

### Related Context
Each ticket shows:
- Related hAIveMind memories count
- Linked lessons learned and solutions
- Connected troubleshooting knowledge
- Associated project context

### Agent Coordination
Displays:
- Current agent assignments
- Agent workload and capacity
- Cross-agent dependencies
- Collaboration patterns

### Knowledge Discovery
Finds:
- Similar completed work
- Relevant troubleshooting solutions
- Applicable lessons learned
- Connected discoveries

## Output Formats

### Compact List (Default)
```
📋 Project: memory-mcp (8 tickets)

🎫 WEBTESTS-1: Login form validation [DONE] 
   👤 frontend-agent | 🧠 5 memories | ⏰ 2d ago

🎫 WEBTESTS-2: Dashboard UI testing [IN PROGRESS]
   👤 ui-specialist | 🧠 3 memories | ⏰ 1h ago

🎫 WEBTESTS-3: API integration tests [TODO]
   👤 unassigned | 🧠 7 memories | ⏰ 3d ago
```

### Detailed View
```
ticket-list --detailed memory-mcp-project
```
```
📋 Memory MCP Project - Detailed Ticket Overview

🎫 WEBTESTS-1: Login form validation testing
   📊 Status: DONE ✅ | Priority: HIGH | Agent: frontend-agent
   📅 Created: 2025-01-22 | Completed: 2025-01-24 | Duration: 2d
   🧠 Memory Context: 5 related memories, 2 lessons learned
   🔗 Dependencies: Blocks WEBTESTS-4 (UI integration tests)
   📝 Tags: frontend, validation, webtests, authentication
   💡 Key Discovery: Chrome autofill validation conflicts
   
🎫 WEBTESTS-2: Dashboard UI responsive testing  
   📊 Status: IN PROGRESS ⚡ | Priority: MEDIUM | Agent: ui-specialist
   📅 Created: 2025-01-23 | Started: 2025-01-24 | Duration: 1d
   🧠 Memory Context: 3 related memories, 1 troubleshooting solution
   🔗 Dependencies: Depends on WEBTESTS-1 (form validation)
   📝 Tags: ui, responsive, dashboard, webtests
   ⏳ Estimated completion: 2025-01-25
```

### Agent Workload View
```
ticket-list --by-agent
```
```
👥 Agent Workload Distribution

🤖 frontend-agent (3 tickets)
   ✅ WEBTESTS-1: Login validation [DONE]
   ⚡ WEBTESTS-5: Form styling [IN PROGRESS] 
   📋 WEBTESTS-8: Input validation [TODO]
   
🤖 ui-specialist (2 tickets) 
   ⚡ WEBTESTS-2: Dashboard responsive [IN PROGRESS]
   📋 WEBTESTS-6: Mobile layouts [TODO]
   
🤖 unassigned (3 tickets)
   📋 WEBTESTS-3: API integration [TODO]
   📋 WEBTESTS-4: End-to-end tests [TODO]
   📋 WEBTESTS-7: Performance testing [TODO]
```

## Advanced Options
- **--limit N**: Show only N tickets (default: 50)
- **--sort**: Sort by created, updated, priority, status, agent
- **--reverse**: Reverse sort order
- **--format**: Output format (compact, detailed, json, table)
- **--include-memories**: Show related memory count and context
- **--include-dependencies**: Show ticket relationships
- **--group-by**: Group by project, agent, status, priority
- **--search "query"**: Full-text search in ticket titles/descriptions

## Integration with hAIveMind

### Memory Context
```
ticket-list WEBTESTS-1 --memories
```
Shows related memories, lessons learned, and troubleshooting knowledge for each ticket.

### Agent Coordination
```
ticket-list --coordination
```  
Displays cross-agent dependencies, collaboration patterns, and workload distribution.

### Knowledge Discovery
```
ticket-list --similar-to WEBTESTS-1
```
Finds tickets with similar work patterns, solutions, and context.

## Real-World Examples

### Daily Standup Review
```
ticket-list --status inprogress --by-agent --today
```
Shows all in-progress work by agent for daily coordination.

### Sprint Planning
```
ticket-list --status todo --priority high,medium --limit 20
```
Lists prioritized backlog items for sprint planning.

### Retrospective Analysis
```
ticket-list --status done --completed-this-sprint --detailed
```
Reviews completed work with lessons learned and discoveries.

### Dependency Planning
```
ticket-list --include-dependencies --status todo
```
Shows ticket relationships for dependency planning.

This command provides comprehensive ticket visibility with full hAIveMind integration for effective project coordination and knowledge discovery.