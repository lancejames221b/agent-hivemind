---
description: Start work on a ticket with automatic pre-work hooks and memory synchronization
allowed-tools: ["mcp__vibe_kanban__*", "mcp__haivemind__trigger_sync_hooks"]
argument-hint: <ticket_id> [options]
---

# ticket-start - Begin Ticket Work with Hooks

## Purpose
Start work on a ticket with automatic pre-work synchronization hooks that capture context, check related memories, and store work intentions in the hAIveMind collective.

## When to Use
- **Begin New Work**: Starting any ticket or task
- **Context Capture**: Automatically gather related information
- **Memory Integration**: Link ticket work to collective knowledge
- **Agent Coordination**: Notify other agents of work beginning

## Syntax
```
ticket-start <ticket_id> [project_id] [options]
```

## Features

### Automatic Pre-Work Hooks
When you start a ticket, the system automatically:
1. **Reads ticket description and current status**
2. **Checks hAIveMind memory for related context**
3. **Stores work intention with expected outcomes**
4. **Identifies dependencies and blocking issues** 
5. **Reviews lessons learned from similar work**

### Memory Integration
- Searches collective memory for related work
- Stores work context for other agents
- Links dependencies and relationships
- Captures lessons learned from similar tickets

## Real-World Examples

### Start Web Testing Ticket
```
ticket-start WEBTESTS-1 memory-mcp-project
```
**Automatic Actions:**
- Reads WEBTESTS-1 ticket details
- Searches for related web testing memories
- Stores intention to start web testing work
- Checks for UI/UX testing dependencies
- Reviews lessons from previous web testing

### Start API Development
```
ticket-start API-DEV-5 ewitness-project --verbose
```
**Automatic Actions:**
- Captures API development context
- Links to related API memories
- Stores development work intention
- Identifies authentication dependencies
- Reviews API development best practices

### Resume Previous Work
```
ticket-start INFRA-3 --resume
```
**Automatic Actions:**
- Checks previous work context
- Reviews any blocking issues resolved
- Updates work intention
- Syncs with latest infrastructure state

## Expected Output
```
🚀 Starting Work on Ticket: WEBTESTS-1
🔄 Executing Pre-Work Synchronization Hooks...

✅ Pre-Work Hook Results:
   • pre_work_hook (0.245s)

📋 Ticket Context Captured:
   • Title: "Login form validation testing"
   • Status: todo → inprogress
   • Project: memory-mcp-project

🧠 Memory Integration:
   • Related memories found: 7
   • Dependencies identified: 2
   • Lessons learned retrieved: 3

💾 Work intention stored in hAIveMind collective
🤖 Other agents notified of work beginning

🎯 Ready to begin work! Use ticket-complete when finished.
```

## Options
- **--verbose**: Show detailed hook execution information
- **--resume**: Resume previously started work
- **--force**: Start work even if ticket already in progress
- **--sync**: Force immediate sync with collective before starting

## Integration with Workflow
This command works seamlessly with:
- **ticket-complete**: Automatically triggers post-work hooks
- **hv-sync-hooks**: Uses the same hook system for consistency
- **hAIveMind memory**: All context stored in collective intelligence
- **Agent coordination**: Other agents see work status changes

## Hook Configuration
Uses sync protocol defined in `sync-protocol.json`:
- Pre-sync checklist automatically executed
- Memory categories populated appropriately
- Agent coordination triggered
- Network sync integration enabled

Start your ticket work with full hAIveMind integration and automatic knowledge capture!