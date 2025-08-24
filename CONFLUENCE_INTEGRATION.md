# Confluence Integration for Playbook Import

## Overview

The Confluence Integration provides seamless automated playbook ingestion from Atlassian Confluence. This integration is part of **Story 3b** and enables automatic detection, parsing, and import of runbooks and procedures from Confluence spaces into the hAIveMind playbook system.

## Features

### ✅ Core Integration Features
- **Confluence API Integration**: Full authentication and API access management
- **Automatic Detection**: Smart detection of runbooks/procedures in Confluence pages
- **Content Parsing**: Convert Confluence pages to structured playbook format
- **Scheduled Sync**: Keep playbooks up to date with automatic synchronization
- **Space Mapping**: Map Confluence spaces to playbook categories
- **Content Handling**: Process embedded images, tables, and formatting
- **Version Control**: Track changes from Confluence with version history
- **Bulk Import**: Import entire spaces with conflict resolution
- **Management Dashboard**: Web UI for managing connections and sync status

### 🧠 hAIveMind Awareness Integration
- **Memory Storage**: Store all imported playbooks as searchable memories
- **Learning**: Learn which Confluence pages are most valuable and prioritize them
- **Outdated Detection**: Automatically detect when Confluence content becomes outdated
- **Pattern Sharing**: Share successful import patterns across different Confluence instances
- **Analytics Storage**: Store integration analytics to improve parsing algorithms
- **Agent Broadcasting**: Broadcast newly discovered playbooks to relevant agents

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Confluence Integration                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │ Confluence API  │    │ Content Parser  │    │ Sync Service │ │
│  │ - Authentication│    │ - HTML to YAML  │    │ - Scheduled  │ │
│  │ - Page Discovery│    │ - Step Extract  │    │ - Manual     │ │
│  │ - Content Fetch │    │ - Metadata      │    │ - Conflict   │ │
│  └─────────────────┘    └─────────────────┘    └──────────────┘ │
│           │                       │                       │     │
│           └───────────────────────┼───────────────────────┘     │
│                                   │                             │
│  ┌─────────────────┐    ┌─────────▼─────────┐    ┌──────────────┐ │
│  │ MCP Tools       │    │ Playbook Engine   │    │ Dashboard    │ │
│  │ - Import        │    │ - Validation      │    │ - Status     │ │
│  │ - Discover      │    │ - Execution       │    │ - Config     │ │
│  │ - Sync          │    │ - Storage         │    │ - Analytics  │ │
│  └─────────────────┘    └───────────────────┘    └──────────────┘ │
│           │                       │                       │     │
│           └───────────────────────┼───────────────────────┘     │
│                                   │                             │
│  ┌─────────────────────────────────▼─────────────────────────────┐ │
│  │                    hAIveMind Storage                         │ │
│  │  - Playbook Database  - Memory Storage  - Agent Broadcast   │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Installation & Setup

### 1. Install Dependencies

The Confluence integration requires additional Python packages:

```bash
pip install beautifulsoup4>=4.12.0
```

### 2. Configure Confluence Connection

Edit `config/config.json` to add your Confluence settings:

```json
{
  "connectors": {
    "confluence": {
      "url": "https://your-domain.atlassian.net",
      "credentials": {
        "username": "your-email@domain.com",
        "token": "${CONFLUENCE_API_TOKEN}"
      },
      "spaces": ["INFRA", "DEVOPS", "DOCS"],
      "enabled": true,
      "space_category_mapping": {
        "INFRA": "infrastructure",
        "DEVOPS": "devops",
        "DOCS": "documentation"
      },
      "sync_interval": 3600,
      "max_age_hours": 24,
      "auto_import_new": true,
      "auto_update_existing": true
    }
  }
}
```

### 3. Set Environment Variables

Create a Confluence API token and set it as an environment variable:

```bash
export CONFLUENCE_API_TOKEN="your-api-token-here"
```

### 4. Test the Integration

Run the test script to verify everything is working:

```bash
python test_confluence_integration.py
```

## Usage

### MCP Tools

The integration provides several MCP tools for Claude agents:

#### Discovery Tools

**`discover_confluence_playbooks`**
```json
{
  "space_key": "INFRA"  // Optional: specific space to search
}
```
Discovers playbook pages in Confluence spaces.

**`preview_confluence_playbook`**
```json
{
  "page_id": "123456789"
}
```
Preview how a Confluence page would be converted to a playbook without importing.

#### Import Tools

**`import_confluence_playbook`**
```json
{
  "page_id": "123456789",
  "force_update": false
}
```
Import a specific Confluence page as a playbook.

**`bulk_import_confluence_space`**
```json
{
  "space_key": "INFRA",
  "force_update": false
}
```
Bulk import all playbooks from a Confluence space.

#### Sync Tools

**`sync_confluence_playbooks`**
```json
{
  "max_age_hours": 24
}
```
Sync updates from Confluence for existing playbooks.

**`get_confluence_status`**
```json
{}
```
Get Confluence integration status and connection info.

#### Management Tools

**`list_confluence_playbooks`**
```json
{}
```
List all playbooks imported from Confluence.

**`configure_confluence_integration`**
```json
{
  "url": "https://domain.atlassian.net",
  "username": "user@domain.com",
  "api_token": "token",
  "spaces": ["SPACE1", "SPACE2"],
  "enabled": true
}
```
Configure Confluence integration settings.

### Dashboard API

The integration provides REST API endpoints for web management:

- `GET /api/v1/confluence/status` - Get integration status
- `POST /api/v1/confluence/configure` - Configure integration
- `GET /api/v1/confluence/playbooks` - List imported playbooks
- `GET /api/v1/confluence/discover` - Discover playbooks
- `GET /api/v1/confluence/preview/{page_id}` - Preview playbook conversion
- `POST /api/v1/confluence/import` - Import specific playbook
- `POST /api/v1/confluence/bulk-import` - Bulk import from space
- `POST /api/v1/confluence/sync` - Sync existing playbooks
- `POST /api/v1/confluence/sync/trigger` - Trigger manual sync
- `GET /api/v1/confluence/sync/status` - Get sync service status
- `GET /api/v1/confluence/spaces` - Get configured spaces
- `GET /api/v1/confluence/analytics` - Get import analytics

### Automatic Sync Service

The sync service runs in the background and:

1. **Monitors Changes**: Checks for updates to existing imported playbooks
2. **Discovers New Content**: Finds new playbooks in configured spaces
3. **Imports Automatically**: Imports new playbooks based on configuration
4. **Updates Existing**: Updates playbooks when Confluence content changes
5. **Reports Status**: Stores sync results in hAIveMind for tracking

## Content Parsing

### Supported Confluence Content

The integration can parse various Confluence content types:

#### Page Structure
- **Headings**: Used for step organization and playbook sections
- **Paragraphs**: Converted to descriptions and documentation
- **Lists**: Ordered lists become playbook steps
- **Tables**: Parameter tables and structured data
- **Code Blocks**: Shell commands and scripts
- **Macros**: Info panels, warnings, and structured content

#### Playbook Detection

Pages are identified as playbooks if they contain:
- Keywords: "runbook", "playbook", "procedure", "how to", "troubleshoot"
- Structured content: Numbered steps, ordered lists
- Operational content: Deployment, installation, maintenance procedures

#### Step Extraction

Steps are extracted from:
1. **Ordered Lists**: `<ol>` elements with `<li>` items
2. **Numbered Headings**: Headers starting with numbers (1., 2., etc.)
3. **Procedure Sections**: Sections with step-by-step content

#### Action Detection

The parser attempts to detect action types:
- **Shell Commands**: Code blocks with command-line content
- **HTTP Requests**: URLs and API calls
- **Manual Steps**: General instructions and procedures

### Example Conversion

**Confluence Content:**
```html
<h1>Deploy Application</h1>
<p>This procedure deploys the application to production.</p>

<h2>Prerequisites</h2>
<ul>
  <li>Access to production servers</li>
  <li>Application build ready</li>
</ul>

<h2>Steps</h2>
<ol>
  <li>Connect to server: <code>ssh user@prod-server</code></li>
  <li>Stop application: <code>systemctl stop myapp</code></li>
  <li>Deploy new version</li>
  <li>Start application: <code>systemctl start myapp</code></li>
  <li>Verify deployment: <code>curl http://localhost:8080/health</code></li>
</ol>
```

**Generated Playbook:**
```yaml
version: 1
name: "Deploy Application"
category: "infrastructure"
description: "This procedure deploys the application to production."
prerequisites:
  - type: "manual_check"
    description: "Access to production servers"
  - type: "manual_check"
    description: "Application build ready"
steps:
  - id: "step_1"
    name: "Connect to server"
    action: "shell"
    args:
      command: "ssh user@prod-server"
  - id: "step_2"
    name: "Stop application"
    action: "shell"
    args:
      command: "systemctl stop myapp"
  - id: "step_3"
    name: "Deploy new version"
    action: "noop"
    args:
      message: "Deploy new version"
  - id: "step_4"
    name: "Start application"
    action: "shell"
    args:
      command: "systemctl start myapp"
  - id: "step_5"
    name: "Verify deployment"
    action: "http_request"
    args:
      url: "http://localhost:8080/health"
      method: "GET"
metadata:
  source: "confluence"
  confluence_page_id: "123456789"
  confluence_space: "INFRA"
  confluence_url: "https://domain.atlassian.net/wiki/spaces/INFRA/pages/123456789"
```

## hAIveMind Integration

### Memory Storage

All imported playbooks are stored in hAIveMind as searchable memories:

```python
# Example memory content
content = f"""
Confluence Playbook: {playbook_title}

Source: {confluence_url}
Space: {space_key}
Category: {category}
Description: {description}

Steps:
{yaml_steps}

Full Playbook Specification:
{full_yaml}
"""
```

### Agent Broadcasting

When new playbooks are imported, the system broadcasts to relevant agents:

```python
await haivemind.broadcast_discovery(
    message=f"New Confluence playbook imported: {title}",
    category='runbooks',
    severity='info',
    details={
        'playbook_name': title,
        'confluence_space': space,
        'confluence_url': url,
        'category': category,
        'step_count': len(steps)
    }
)
```

### Learning and Analytics

The integration tracks:
- **Import Success Rates**: Which pages import successfully
- **Usage Patterns**: Which playbooks are executed most often
- **Content Quality**: Which Confluence pages produce the best playbooks
- **Update Frequency**: How often pages change and need re-import
- **Space Effectiveness**: Which spaces contain the most valuable content

## Troubleshooting

### Common Issues

**1. Authentication Errors**
```
ConfluenceAuthError: Invalid Confluence credentials
```
- Verify your API token is correct
- Check that the username matches the token owner
- Ensure the token has appropriate permissions

**2. Connection Errors**
```
ConfluenceError: Failed to connect to Confluence
```
- Verify the Confluence URL is correct
- Check network connectivity
- Ensure Confluence is accessible from your server

**3. Parsing Errors**
```
ConfluenceParseError: Invalid playbook structure
```
- Check that the Confluence page has structured content
- Verify the page contains steps or procedures
- Review the HTML structure of the page

**4. Import Failures**
```
PlaybookValidationError: Playbook must include non-empty 'steps' list
```
- The page doesn't contain recognizable steps
- Try manually structuring the content with ordered lists
- Check if the page is actually a runbook/procedure

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing Connection

Test your Confluence connection:

```python
from src.confluence_integration import ConfluenceIntegration

async def test_connection():
    config = {
        'url': 'https://your-domain.atlassian.net',
        'credentials': {
            'username': 'your-email@domain.com',
            'token': 'your-api-token'
        },
        'enabled': True
    }
    
    async with ConfluenceIntegration(config, None, None) as confluence:
        print("✅ Connection successful!")

asyncio.run(test_connection())
```

## Security Considerations

### API Token Security
- Store API tokens as environment variables
- Use tokens with minimal required permissions
- Rotate tokens regularly
- Never commit tokens to version control

### Network Security
- Use HTTPS for all Confluence connections
- Consider IP whitelisting if available
- Monitor API usage for anomalies

### Data Privacy
- Review what content is being imported
- Ensure sensitive information is not exposed
- Consider data retention policies
- Implement access controls on imported playbooks

## Performance Optimization

### Sync Optimization
- Adjust sync intervals based on content change frequency
- Use incremental sync for large spaces
- Monitor API rate limits
- Cache frequently accessed content

### Parsing Optimization
- Pre-filter pages by title patterns
- Skip non-procedure pages early
- Batch API requests when possible
- Use parallel processing for bulk imports

## Future Enhancements

### Planned Features
- **Advanced Content Detection**: ML-based playbook identification
- **Rich Media Support**: Images, diagrams, and attachments
- **Template Generation**: Create Confluence templates for better parsing
- **Bidirectional Sync**: Update Confluence from playbook changes
- **Multi-Instance Support**: Connect to multiple Confluence instances
- **Custom Parsers**: Plugin system for specialized content types

### Integration Opportunities
- **Jira Integration**: Link playbooks to incidents and tickets
- **Slack Integration**: Notifications for new playbooks
- **Git Integration**: Version control for playbook content
- **Monitoring Integration**: Trigger playbooks from alerts

## Contributing

To contribute to the Confluence integration:

1. **Test Changes**: Run `python test_confluence_integration.py`
2. **Add Tests**: Include tests for new functionality
3. **Update Documentation**: Keep this README current
4. **Follow Patterns**: Use existing code patterns and conventions
5. **hAIveMind Awareness**: Ensure new features integrate with hAIveMind

## Support

For issues with the Confluence integration:

1. Check the troubleshooting section above
2. Review the logs for error details
3. Test with the provided test script
4. Verify your Confluence configuration
5. Check hAIveMind memory storage for import results

The integration is designed to be robust and self-healing, with comprehensive error handling and logging to help diagnose issues quickly.