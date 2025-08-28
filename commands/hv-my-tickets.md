# My Tickets Dashboard Command

## Description
Get personalized ticket dashboard showing assigned work, workload summary, and priority breakdown.

## Usage
```bash
# Get all your tickets
get_my_tickets project_id="<project_id>" assignee="<your_agent_id>"

# Filter by status
get_my_tickets project_id="<project_id>" assignee="<your_agent_id>" status="in_progress"

# Check specific user's tickets
get_my_tickets project_id="<project_id>" assignee="frontend-dev" status="review"
```

## Parameters
- **project_id**: Project ID from Vibe Kanban (required)
- **assignee**: Agent ID to get tickets for (required)
- **status**: Optional status filter - new/in_progress/review/done/blocked/cancelled (optional)

## Output Format
```
👤 frontend-dev's Tickets (8 total)
⏱️ Total Estimated Work: 32h
🏃 In Progress: 3
🚨 High Priority: 2

📋 IN_PROGRESS (3)
  #1001 🔴 Fix critical authentication bug (4h)
  #1005 🟡 Update user profile page (6h)
  #1008 🟠 Implement dark mode toggle (8h)

📋 REVIEW (2)
  #1003 🟡 Add form validation messages (3h)
  #1007 🟢 Update footer links (1h)

📋 NEW (3)
  #1010 🟠 Mobile responsive navigation (8h)
  #1012 🟡 Fix CSS layout issues (2h)
  #1015 🟢 Update documentation (0h)
```

## Dashboard Features
- ✅ **Workload Summary**: Total estimated hours across all tickets
- ✅ **Status Breakdown**: Tickets organized by current status
- ✅ **Priority Indicators**: Visual priority markers (🚨🔴🟠🟡🟢)
- ✅ **Time Estimates**: Hours estimated for each ticket
- ✅ **Active Work Count**: Number of in-progress tickets
- ✅ **High Priority Alert**: Count of urgent items
- ✅ **Personal Focus**: Only assigned tickets

## Priority Visual Indicators
- 🚨 **Emergency**: Immediate attention required
- 🔴 **Critical**: Business-critical issues
- 🟠 **High**: Important work items  
- 🟡 **Medium**: Standard priority (most common)
- 🟢 **Low**: Can be deferred if needed

## Workload Insights
- **Total Estimated**: Sum of all time estimates
- **In Progress Count**: Currently active work
- **High Priority Count**: Urgent items needing attention
- **Status Distribution**: Work organized by workflow stage

## Common Use Cases

### Daily Standup Preparation
```bash
# Check what you're working on
get_my_tickets project_id="proj_123" assignee="your-id" status="in_progress"
```

### Planning Next Work
```bash
# See what's ready to start
get_my_tickets project_id="proj_123" assignee="your-id" status="new"
```

### Weekly Review
```bash
# Full workload overview
get_my_tickets project_id="proj_123" assignee="your-id"
```

### Code Review Queue
```bash
# Check items ready for review
get_my_tickets project_id="proj_123" assignee="your-id" status="review"
```

### Team Lead Check
```bash
# Monitor team member's workload
get_my_tickets project_id="proj_123" assignee="team-member-id"
```

## Status Workflow
```
NEW → IN_PROGRESS → REVIEW → DONE
         ↓             ↓
      BLOCKED      BLOCKED
```

- **NEW**: Ready to start, not yet begun
- **IN_PROGRESS**: Actively being worked on
- **REVIEW**: Completed, waiting for review/testing
- **DONE**: Completed and accepted
- **BLOCKED**: Cannot proceed due to dependencies
- **CANCELLED**: Work cancelled or no longer needed

## Time Management
- **Estimated Hours**: Planning and capacity management
- **Total Workload**: Overall commitment assessment
- **Priority Balance**: Mix of urgent vs. routine work
- **Status Flow**: Work progression through pipeline

The dashboard provides a comprehensive view of individual workload and helps with personal task management and team coordination.