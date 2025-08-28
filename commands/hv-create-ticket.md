# Enhanced Ticket Creation Command

## Description
Create comprehensive tickets with metadata, priority, assignment, and hAIveMind integration.

## Usage
```bash
# Basic ticket creation
create_ticket project_id="<project_id>" title="<title>" description="<description>"

# Full ticket with all metadata
create_ticket project_id="<project_id>" title="<title>" description="<description>" ticket_type="bug" priority="high" assignee="<agent_id>" labels="[\"label1\", \"label2\"]" due_date="2024-12-31T23:59:59" time_estimate=8 reporter="<user_id>"

# Epic creation
create_ticket project_id="<project_id>" title="User Authentication Epic" description="Complete user authentication system" ticket_type="epic" priority="high" time_estimate=40

# Bug report with assignee
create_ticket project_id="<project_id>" title="Login form validation error" description="Email validation not working on login form" ticket_type="bug" priority="critical" assignee="frontend-dev" labels="[\"ui\", \"validation\"]"

# Feature request
create_ticket project_id="<project_id>" title="Add dark mode theme" description="Users request dark mode for better usability" ticket_type="feature" priority="medium" labels="[\"ui\", \"enhancement\"]" time_estimate=12
```

## Parameters
- **project_id**: Project ID from Vibe Kanban (required)
- **title**: Ticket title (required)  
- **description**: Detailed description (optional)
- **ticket_type**: Type - bug/feature/task/epic/story/incident/request (default: task)
- **priority**: Priority - low/medium/high/critical/emergency (default: medium)
- **assignee**: Agent ID to assign ticket to (optional)
- **labels**: JSON array of labels ["label1", "label2"] (optional)
- **due_date**: Due date in ISO format (optional)
- **time_estimate**: Estimated hours as integer (optional)
- **parent_ticket**: Parent ticket ID for subtasks (optional)
- **reporter**: Reporter/creator ID (default: system)

## Features
- ✅ Comprehensive metadata support
- ✅ Priority and type classification
- ✅ Time estimation and tracking
- ✅ Label categorization
- ✅ Agent assignment
- ✅ Due date management
- ✅ Parent-child relationships
- ✅ hAIveMind memory integration
- ✅ Automatic ticket numbering

## Examples

### Bug Report Template
```bash
create_ticket project_id="proj_123" title="API timeout on user search" description="Search API times out after 30 seconds when searching for users with special characters. Error: 504 Gateway Timeout. Affects all users." ticket_type="bug" priority="high" assignee="backend-dev" labels="[\"api\", \"performance\", \"search\"]" time_estimate=4
```

### Feature Request Template
```bash
create_ticket project_id="proj_123" title="Export data to CSV" description="Users need ability to export their data in CSV format for analysis. Should include all fields and respect user permissions." ticket_type="feature" priority="medium" labels="[\"export\", \"csv\", \"data\"]" time_estimate=8 due_date="2024-12-15T17:00:00"
```

### Epic Template
```bash
create_ticket project_id="proj_123" title="Mobile App Authentication" description="Complete authentication system for mobile app including login, registration, password reset, and social login integration." ticket_type="epic" priority="high" time_estimate=120 labels="[\"mobile\", \"auth\", \"epic\"]"
```

The ticket will be created in Vibe Kanban with enhanced metadata and automatically indexed in hAIveMind for search and analytics.