---
description: Manage hAIveMind kanban tickets and tasks with full project integration
allowed-tools: ["mcp__vibe_kanban__*", "mcp__haivemind__*"]
argument-hint: [create|list|update|get|delete] [options]
---

# hv-ticket - hAIveMind Task Management

## Purpose
Manage kanban tickets and tasks within hAIveMind projects, with automatic memory integration and cross-agent coordination.

## When to Use
- **Create Tasks**: Add new tickets to project backlogs
- **Track Progress**: Update ticket status and progress
- **Project Coordination**: List and organize project work
- **Agent Assignment**: Delegate tasks to specific agents
- **Memory Integration**: Link tickets to hAIveMind memories

## Syntax
```
hv-ticket <action> [options]
```

## Actions

### Create New Ticket
```
hv-ticket create "Fix authentication bug" --project memory-mcp --priority high
hv-ticket create "Implement search API" --project ewitness --description "Add Elasticsearch search endpoint"
```

### List Project Tickets
```
hv-ticket list --project memory-mcp
hv-ticket list --status todo --limit 10
hv-ticket list --all
```

### Update Ticket Status
```
hv-ticket update TICKET_ID --status inprogress
hv-ticket update TICKET_ID --status done --notes "Completed successfully"
```

### Get Ticket Details
```
hv-ticket get TICKET_ID
```

### Delete Ticket
```
hv-ticket delete TICKET_ID --confirm
```

## Parameters
- **project**: Project ID or name for ticket operations
- **title**: Ticket title (required for create)
- **description**: Detailed ticket description
- **priority**: Task priority (low, medium, high, critical)
- **status**: Ticket status (todo, inprogress, inreview, done, cancelled)
- **assignee**: Agent ID to assign ticket to
- **tags**: Comma-separated tags for organization
- **limit**: Maximum number of tickets to return

## Integration Features

### hAIveMind Memory Integration
- Automatically stores ticket context in collective memory
- Links related memories to tickets
- Enables cross-agent knowledge sharing about ticket progress

### Project Coordination
- Integrates with hAIveMind project management system
- Tracks ticket relationships and dependencies
- Enables project-wide progress monitoring

### Agent Assignment
- Supports delegation to specific hAIveMind agents
- Tracks agent workload and capabilities
- Enables automatic assignment based on skills

## Real-World Examples

### Bug Tracking Workflow
```
# Create bug ticket
hv-ticket create "WEBTESTS-1: Login form validation" --project memory-mcp --priority high --description "Form doesn't validate email format"

# Assign to specialist
hv-ticket update TICKET_ID --assign frontend-agent --status inprogress

# Complete with resolution
hv-ticket update TICKET_ID --status done --notes "Added email regex validation and user feedback"
```

### Feature Development
```
# List current work
hv-ticket list --project ewitness --status inprogress

# Create feature ticket
hv-ticket create "API rate limiting" --project ewitness --priority medium --tags "api,security"

# Track progress
hv-ticket get TICKET_ID
```

## Output Format
```
🎫 Ticket WEBTESTS-1: Login form validation
📊 Status: inprogress → done
🎯 Project: memory-mcp
👤 Assigned: frontend-agent
📅 Created: 2025-01-24 14:30:00
📝 Notes: Added email regex validation and user feedback
🔗 Related Memories: 3 found
📋 Tags: frontend, validation, webtests
```

## Related Commands
- **Project Management**: Use `hv-project` for project-level operations
- **Agent Coordination**: Use `hv-delegate` for task assignment
- **Memory Integration**: Use `remember` to link additional context
- **Progress Tracking**: Use `hv-status` to see overall project health

This command provides comprehensive ticket management within the hAIveMind collective intelligence framework.