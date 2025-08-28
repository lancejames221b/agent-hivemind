# Enhanced Ticket Listing Command

## Description
List tickets with advanced filtering, status breakdown, and comprehensive ticket details.

## Usage
```bash
# List all tickets in project
list_tickets project_id="<project_id>"

# Filter by status
list_tickets project_id="<project_id>" status="in_progress"

# Filter by priority and assignee
list_tickets project_id="<project_id>" priority="high" assignee="<agent_id>"

# Filter by type and limit results
list_tickets project_id="<project_id>" ticket_type="bug" limit=10

# Multiple filters combined
list_tickets project_id="<project_id>" status="in_progress" priority="critical" ticket_type="bug" limit=5
```

## Parameters
- **project_id**: Project ID from Vibe Kanban (required)
- **status**: Filter by status - new/in_progress/review/done/blocked/cancelled (optional)
- **priority**: Filter by priority - low/medium/high/critical/emergency (optional)
- **assignee**: Filter by assignee agent ID (optional)
- **ticket_type**: Filter by type - bug/feature/task/epic/story/incident/request (optional)
- **limit**: Maximum tickets to return (default: 20, max: 100)

## Status Values
- **new**: Newly created tickets
- **in_progress**: Currently being worked on
- **review**: Under review/testing
- **done**: Completed tickets
- **blocked**: Blocked tickets waiting on dependencies
- **cancelled**: Cancelled/won't fix tickets

## Priority Values
- **low**: 🟢 Low priority
- **medium**: 🟡 Medium priority (default)
- **high**: 🟠 High priority
- **critical**: 🔴 Critical priority
- **emergency**: 🚨 Emergency priority

## Output Format
```
🎫 Found 15 tickets
Filters: {'status': 'in_progress', 'priority': 'high', 'limit': 20}

📊 Status Breakdown:
  in_progress: 15

📋 Ticket List:
  #1001 🔴 Fix critical authentication bug
    Status: in_progress | Type: bug | Assignee: security-dev
  #1002 🟠 Implement user dashboard
    Status: in_progress | Type: feature | Assignee: frontend-dev
  #1003 🚨 Database connection pool exhaustion
    Status: in_progress | Type: incident | Assignee: backend-dev
```

## Features
- ✅ Advanced multi-field filtering
- ✅ Status breakdown overview
- ✅ Priority visual indicators
- ✅ Assignee information
- ✅ Ticket type classification
- ✅ Ticket numbering display
- ✅ Pagination support
- ✅ Real-time status counts

## Common Filter Examples

### View all high-priority work
```bash
list_tickets project_id="proj_123" priority="high"
```

### Check your assigned tickets
```bash
list_tickets project_id="proj_123" assignee="your-agent-id"
```

### Review completed work
```bash
list_tickets project_id="proj_123" status="done" limit=10
```

### Find all bugs
```bash
list_tickets project_id="proj_123" ticket_type="bug"
```

### Critical issues only
```bash
list_tickets project_id="proj_123" priority="critical"
```

### Work in progress
```bash
list_tickets project_id="proj_123" status="in_progress"
```

### Emergency incidents
```bash
list_tickets project_id="proj_123" ticket_type="incident" priority="emergency"
```

The listing provides comprehensive overview with status breakdowns and detailed ticket information for efficient project management.