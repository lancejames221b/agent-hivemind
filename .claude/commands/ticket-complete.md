---
description: Complete ticket work with automatic post-work hooks and knowledge sharing
allowed-tools: ["mcp__vibe_kanban__*", "mcp__haivemind__trigger_sync_hooks", "mcp__haivemind__broadcast_discovery"]
argument-hint: <ticket_id> [options]
---

# ticket-complete - Finish Ticket Work with Hooks

## Purpose
Complete ticket work with automatic post-work synchronization hooks that store results, document lessons learned, and share discoveries with the hAIveMind collective.

## When to Use
- **Finish Ticket Work**: Mark ticket as completed
- **Knowledge Capture**: Store comprehensive results and lessons
- **Discovery Sharing**: Broadcast important findings to other agents
- **Project Coordination**: Update dependent work and relationships

## Syntax
```
ticket-complete <ticket_id> [options] --summary "Work completed summary"
```

## Features

### Automatic Post-Work Hooks
When you complete a ticket, the system automatically:
1. **Updates ticket status with detailed completion notes**
2. **Stores comprehensive results in hAIveMind memory**  
3. **Documents lessons learned and troubleshooting solutions**
4. **Shares important discoveries with other agents**
5. **Coordinates with dependent tickets and agents**

### Knowledge Preservation
- Captures detailed work results and outcomes
- Documents troubleshooting steps and solutions
- Records lessons learned for future work
- Links completion to related memories and tickets

### Network Coordination
- Broadcasts discoveries to hAIveMind collective
- Updates dependent work and blocking relationships
- Triggers sync with network-wide knowledge distribution
- Notifies coordinating agents of completion

## Real-World Examples

### Complete Web Testing Ticket
```
ticket-complete WEBTESTS-1 --summary "Login form validation implemented" --lessons "Email regex validation tricky - use /^[^\s@]+@[^\s@]+\.[^\s@]+$/" --discovery "Found Chrome autofill conflicts with validation"
```
**Automatic Actions:**
- Updates WEBTESTS-1 status to done
- Stores validation implementation details
- Documents regex solution for future use
- Broadcasts Chrome autofill discovery to team
- Coordinates with dependent UI tickets

### Complete API Development
```
ticket-complete API-DEV-5 --summary "Search endpoint implemented" --results "Added pagination, filtering, and sorting" --troubleshooting "Fixed Elasticsearch timeout issues by adding connection pooling"
```
**Automatic Actions:**
- Marks API development ticket complete
- Stores endpoint implementation details
- Documents pagination/filtering approach
- Records Elasticsearch timeout solution
- Shares connection pooling discovery

### Complete Infrastructure Work
```
ticket-complete INFRA-3 --summary "Load balancer configured" --discovery "NGINX upstream health checks significantly improve failover time"
```
**Automatic Actions:**
- Updates infrastructure ticket status
- Stores load balancer configuration
- Documents health check optimization
- Broadcasts failover improvement discovery
- Coordinates with monitoring setup tickets

## Required Parameters
- **--summary**: Brief summary of completed work (required)

## Optional Parameters  
- **--results**: Detailed results and deliverables
- **--lessons**: Lessons learned during the work
- **--troubleshooting**: Solutions to problems encountered
- **--discovery**: Important findings to share with collective
- **--dependencies**: Notes about dependent work unblocked
- **--recommendations**: Suggestions for future improvements

## Expected Output
```
✅ Completing Ticket: WEBTESTS-1
🔄 Executing Post-Work Synchronization Hooks...

✅ Post-Work Hook Results:
   • post_work_hook (0.381s)

📋 Ticket Status Updated:
   • Status: inprogress → done
   • Summary: "Login form validation implemented"
   • Completion time: 2025-01-24 16:45:00

🧠 Knowledge Captured:
   • Work results stored in hAIveMind memory
   • Lessons learned documented: 2 items
   • Troubleshooting solutions: 1 solution
   • Important discovery recorded: Chrome autofill conflicts

📡 Network Coordination:
   • Discovery broadcasted to hAIveMind collective
   • Dependent tickets notified: 3 tickets
   • Agent coordination updated
   • Network sync triggered

🎉 Ticket completed successfully with full knowledge preservation!
```

## Integration Features

### Memory Storage
All completion information stored in appropriate categories:
- **workflow**: Ticket completion events
- **lessons_learned**: Key insights and solutions  
- **troubleshooting**: Problem resolutions
- **project**: Detailed work results
- **dependencies**: Coordination information

### Agent Broadcasting
Important discoveries automatically shared via:
- hAIveMind broadcast system
- Network sync distribution
- Agent coordination updates
- Project memory integration

### Workflow Continuity
Completion triggers coordination with:
- Dependent tickets and blocking relationships
- Related agents working on connected tasks
- Project-wide progress tracking
- Network-wide knowledge sync

## Hook Configuration
Uses sync protocol from `sync-protocol.json`:
- Post-sync checklist automatically executed
- Memory categories populated appropriately
- Network distribution triggered
- Agent coordination maintained

Complete your tickets with comprehensive knowledge capture and automatic sharing across the hAIveMind collective!