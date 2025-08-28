# Ticket Metrics and Analytics Command

## Description
Get comprehensive ticket metrics, analytics, and performance insights for project management.

## Usage
```bash
# Get 30-day metrics (default)
get_ticket_metrics project_id="<project_id>"

# Get metrics for specific time period
get_ticket_metrics project_id="<project_id>" days=7

# Get quarterly metrics
get_ticket_metrics project_id="<project_id>" days=90
```

## Parameters
- **project_id**: Project ID from Vibe Kanban (required)
- **days**: Time period for metrics calculation (default: 30, max: 365)

## Output Format
```
📊 Ticket Metrics (30 days)
Generated: 2024-08-27T18:00:00Z

📈 Overview:
  Total Tickets: 45
  Created in Period: 12
  Closed in Period: 8
  Average Resolution: 18.5h

📊 By Status:
  in_progress: 15
  review: 8
  done: 18
  new: 4

🚨 By Priority:
  medium: 22
  high: 12
  critical: 8
  low: 3

🎯 By Type:
  task: 18
  bug: 15
  feature: 8
  incident: 4

⚠️ Alerts:
  Critical Tickets: 8
  Overdue Tickets: 3
```

## Metrics Included

### Overview Metrics
- **Total Tickets**: All tickets in the project
- **Created in Period**: New tickets in specified timeframe
- **Closed in Period**: Completed tickets in timeframe
- **Average Resolution Time**: Mean time from creation to completion

### Status Distribution
- **new**: Newly created, not yet started
- **in_progress**: Currently being worked on
- **review**: Under review or testing
- **done**: Completed and closed
- **blocked**: Waiting on dependencies
- **cancelled**: Cancelled or won't fix

### Priority Analysis
- **low** 🟢: Low impact, can be deferred
- **medium** 🟡: Standard priority work
- **high** 🟠: Important, should be prioritized
- **critical** 🔴: Business-critical issues
- **emergency** 🚨: Immediate attention required

### Type Breakdown
- **task**: General work items
- **bug**: Defects and issues
- **feature**: New functionality
- **epic**: Large initiatives
- **story**: User stories
- **incident**: Production issues
- **request**: User requests

### Alert Conditions
- **Critical Tickets**: High/critical/emergency priority items
- **Overdue Tickets**: Past due date with incomplete status
- **Stale Tickets**: No activity for extended period
- **Blocked Tickets**: Dependencies preventing progress

## Use Cases

### Sprint Planning
```bash
# Get current sprint metrics
get_ticket_metrics project_id="proj_123" days=14
```

### Monthly Review
```bash
# Monthly team performance
get_ticket_metrics project_id="proj_123" days=30
```

### Quarterly Analysis
```bash
# Quarterly project health
get_ticket_metrics project_id="proj_123" days=90
```

### Weekly Standup
```bash
# Weekly progress check
get_ticket_metrics project_id="proj_123" days=7
```

## Key Performance Indicators (KPIs)
- **Throughput**: Tickets closed per time period
- **Cycle Time**: Average resolution time
- **Work Distribution**: Balance across types and priorities
- **Quality Metrics**: Bug-to-feature ratio
- **Bottleneck Identification**: Status distribution analysis
- **Team Utilization**: Work assignment balance

## Insights and Actions
- **High Critical Count**: Focus on priority management
- **Long Resolution Time**: Review process efficiency
- **Many Overdue**: Improve estimation or capacity
- **Status Imbalance**: Address workflow bottlenecks
- **Type Concentration**: Balance feature vs. maintenance work

The metrics provide data-driven insights for improving team performance and project delivery.