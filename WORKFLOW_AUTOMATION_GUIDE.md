# hAIveMind Workflow Automation System

## Overview

The hAIveMind Workflow Automation System provides intelligent automation for common command sequences, enabling users to create, execute, and manage complex workflows with advanced features like auto-suggestions, validation, rollback capabilities, and collective learning.

## Architecture

### Core Components

1. **Workflow Automation Engine** (`workflow_automation_engine.py`)
   - Core workflow execution and management
   - Template system with predefined workflows
   - Pattern recognition and learning
   - Execution tracking and analytics

2. **MCP Tools** (`workflow_automation_mcp_tools.py`)
   - Integration with hAIveMind command system
   - User-friendly workflow operations
   - Formatted output and error handling

3. **hAIveMind Integration** (`workflow_haivemind_integration.py`)
   - Collective learning and intelligence
   - Pattern analysis and optimization
   - Knowledge sharing across agents
   - Context-aware suggestions

4. **Validation & Rollback** (`workflow_validation_rollback.py`)
   - Comprehensive workflow validation
   - Automated rollback capabilities
   - Checkpoint management
   - Error recovery

5. **Visual Dashboard** (`workflow_dashboard.py`)
   - Web-based workflow management
   - Real-time execution monitoring
   - Visual workflow designer
   - Analytics and reporting

6. **API Server** (`workflow_api_server.py`)
   - REST API for external integration
   - Webhook notifications
   - WebSocket real-time updates
   - Authentication and rate limiting

## Features

### 🔄 Smart Workflow Suggestions

The system automatically suggests relevant workflows based on:
- Current context and situation
- Recent command history
- User intent and goals
- Historical success patterns
- Collective intelligence from other agents

```python
# Get workflow suggestions
suggestions = await workflow_suggest(
    context="security incident detected",
    recent_commands="hv-status,hv-broadcast",
    intent="handle security threat"
)
```

### 🚀 One-Click Workflow Execution

Execute complex workflows with a single command:

```python
# Execute incident response workflow
result = await workflow_execute(
    workflow_id="incident_response",
    parameters='{"severity": "critical", "category": "security"}'
)
```

### 📋 Pre-built Workflow Templates

#### Incident Response Workflow
- **Purpose**: Handle system incidents and outages
- **Steps**: Status check → Broadcast alert → Delegate tasks → Search solutions → Document resolution
- **Duration**: ~30 minutes
- **Success Rate**: 94%

#### Security Alert Workflow
- **Purpose**: Respond to security threats and vulnerabilities
- **Steps**: Document alert → Check awareness → Broadcast threat → Delegate analysis
- **Duration**: ~40 minutes
- **Success Rate**: 91%

#### Maintenance Window Workflow
- **Purpose**: Coordinate planned maintenance activities
- **Steps**: Sync configs → Document maintenance → Broadcast start → Check status → Broadcast completion
- **Duration**: ~60 minutes
- **Success Rate**: 98%

#### Knowledge Sharing Workflow
- **Purpose**: Share discoveries across the collective
- **Steps**: Search existing → Broadcast discovery → Verify receipt
- **Duration**: ~5 minutes
- **Success Rate**: 96%

#### Configuration Update Workflow
- **Purpose**: Safely update and distribute configuration changes
- **Steps**: Sync current → Document changes → Broadcast update → Verify agents
- **Duration**: ~15 minutes
- **Success Rate**: 92%

#### Task Delegation Workflow
- **Purpose**: Efficiently delegate and track task completion
- **Steps**: Document task → Find agent → Delegate task → Check status
- **Duration**: ~10 minutes
- **Success Rate**: 89%

### 🧠 Intelligent Parameter Pre-filling

The system automatically suggests optimal parameters based on:
- Historical successful executions
- Current context analysis
- Collective experience
- Best practices learned from the network

### ✅ Comprehensive Validation

Multi-level validation ensures workflow reliability:

#### Validation Levels
- **Basic**: Required fields, step dependencies
- **Standard**: Command existence, parameter types, timeouts
- **Strict**: Resource availability, security constraints, rollback commands
- **Paranoid**: Execution simulation, network connectivity, system load

```python
# Validate workflow before execution
validation = await workflow_validate(
    workflow_definition='{"name": "My Workflow", "steps": [...]}',
    validation_level="strict"
)
```

### 🔄 Rollback Capabilities

Automated rollback with multiple strategies:

#### Rollback Strategies
- **Immediate**: Reverse all completed steps immediately
- **Graceful**: Allow current step to complete, then rollback
- **Checkpoint**: Rollback to specific checkpoint
- **Manual**: Provide manual rollback instructions

```python
# Initiate rollback
rollback = await workflow_rollback(
    execution_id="exec_123",
    strategy="graceful"
)
```

### 📊 Visual Dashboard

Access the web dashboard at `http://localhost:8900/admin/`:

- **Workflow Library**: Browse and execute templates
- **Real-time Monitoring**: Track active executions
- **Analytics Dashboard**: Performance metrics and insights
- **Visual Designer**: Create workflows with drag-and-drop
- **Execution History**: Review past workflow runs

### 🌐 REST API

External integration via REST API at `http://localhost:8902`:

#### Key Endpoints

```bash
# Execute workflow
POST /api/v1/workflows/execute
{
  "workflow_id": "incident_response",
  "parameters": {"severity": "critical"},
  "auto_approve": false
}

# Get execution status
GET /api/v1/workflows/executions/{execution_id}

# List templates
GET /api/v1/workflows/templates

# Get suggestions
POST /api/v1/workflows/suggest
{
  "context": "security incident",
  "intent": "handle threat"
}

# Create custom workflow
POST /api/v1/workflows/templates
{
  "name": "Custom Workflow",
  "description": "My custom workflow",
  "category": "custom",
  "steps": [...]
}
```

### 🔗 Webhook Integration

Real-time notifications for external systems:

```python
# Configure webhook
webhook_config = {
    "url": "https://your-system.com/webhook",
    "events": ["workflow.started", "workflow.completed", "workflow.failed"],
    "secret": "your-webhook-secret"
}
```

## Usage Examples

### Basic Workflow Operations

```python
# List available workflows
workflows = await workflow_list()

# Get workflow suggestions
suggestions = await workflow_suggest(
    context="database performance issues",
    intent="optimize database"
)

# Execute suggested workflow
result = await workflow_execute(
    workflow_id=suggestions['suggestions'][0]['workflow_id'],
    parameters='{"database": "mysql-primary"}'
)

# Monitor execution
status = await workflow_status(result['execution_id'])

# Get execution history
history = await workflow_history(limit=10)
```

### Advanced Features

```python
# Create custom workflow
custom_workflow = await workflow_create('''{
    "name": "Database Maintenance",
    "description": "Comprehensive database maintenance routine",
    "category": "maintenance",
    "tags": ["database", "maintenance", "optimization"],
    "steps": [
        {
            "id": "backup_db",
            "command": "hv-delegate",
            "description": "Create database backup",
            "parameters": {"task": "backup database", "priority": "high"},
            "timeout_seconds": 1800
        },
        {
            "id": "optimize_tables",
            "command": "hv-delegate",
            "description": "Optimize database tables",
            "parameters": {"task": "optimize tables", "priority": "medium"},
            "depends_on": ["backup_db"],
            "timeout_seconds": 3600
        },
        {
            "id": "update_stats",
            "command": "hv-delegate",
            "description": "Update table statistics",
            "parameters": {"task": "update statistics", "priority": "low"},
            "depends_on": ["optimize_tables"],
            "timeout_seconds": 900
        },
        {
            "id": "document_results",
            "command": "remember",
            "description": "Document maintenance results",
            "parameters": {"category": "infrastructure"},
            "depends_on": ["update_stats"],
            "timeout_seconds": 300
        }
    ],
    "estimated_duration": 7200,
    "approval_required": true,
    "rollback_enabled": true
}''')

# Auto-complete workflow sequences
completion = await workflow_autocomplete(
    partial_sequence="hv-status,hv-broadcast"
)

# Get workflow analytics
analytics = await workflow_analytics()
```

### Integration with Existing Commands

The workflow system seamlessly integrates with existing hAIveMind commands:

```bash
# Traditional command sequence
hv-status
hv-broadcast "Database issue detected" infrastructure critical
hv-delegate "Investigate database performance" critical database_ops
hv-query "database performance optimization"
remember "Applied index optimization - 40% performance improvement" infrastructure

# Equivalent workflow execution
workflow_execute incident_response '{"issue_type": "database", "severity": "critical"}'
```

## Configuration

### Workflow Engine Configuration

```json
{
  "workflow_learning": {
    "enabled": true,
    "pattern_analysis": true,
    "collective_intelligence": true
  },
  "workflow_validation": {
    "default_level": "standard",
    "strict_mode": false,
    "auto_validate": true
  },
  "workflow_rollback": {
    "default_strategy": "graceful",
    "auto_rollback": true,
    "checkpoint_interval": 3
  },
  "workflow_api": {
    "host": "0.0.0.0",
    "port": 8902,
    "api_key_required": true,
    "api_keys": ["your-api-key"],
    "allowed_origins": ["*"]
  }
}
```

### Dashboard Configuration

```json
{
  "workflow_dashboard": {
    "host": "0.0.0.0",
    "port": 8900,
    "enable_designer": true,
    "enable_analytics": true,
    "real_time_updates": true
  }
}
```

## hAIveMind Integration

### Collective Learning

The system learns from all workflow executions across the hAIveMind network:

- **Success Patterns**: Identifies what makes workflows successful
- **Failure Analysis**: Learns from failures to prevent recurrence
- **Parameter Optimization**: Discovers optimal parameter combinations
- **Context Awareness**: Understands when workflows work best

### Knowledge Sharing

Workflow insights are automatically shared across the collective:

- **Successful Patterns**: Broadcast effective workflow sequences
- **Optimization Tips**: Share performance improvements
- **Failure Warnings**: Alert about problematic patterns
- **Best Practices**: Distribute learned best practices

### Adaptive Optimization

Workflows continuously improve through collective intelligence:

- **Auto-tuning**: Parameters automatically adjust based on success rates
- **Step Optimization**: Inefficient steps are identified and improved
- **Timing Optimization**: Execution timing adapts to system load
- **Resource Optimization**: Resource usage is optimized based on availability

## Performance Considerations

### Execution Performance

- **Parallel Execution**: Steps with no dependencies run in parallel
- **Resource Management**: Automatic resource allocation and monitoring
- **Load Balancing**: Distributes workflow load across available agents
- **Caching**: Frequently used templates and results are cached

### Scalability

- **Horizontal Scaling**: Supports multiple workflow engine instances
- **Agent Distribution**: Workflows can span multiple hAIveMind agents
- **Database Optimization**: Efficient storage and retrieval of workflow data
- **Network Optimization**: Minimizes network overhead for distributed execution

### Memory Management

- **Template Caching**: Workflow templates are cached in memory
- **Execution Cleanup**: Completed executions are archived automatically
- **Pattern Compression**: Learning patterns are compressed for efficiency
- **Garbage Collection**: Automatic cleanup of expired data

## Troubleshooting

### Common Issues

#### Workflow Execution Fails
```bash
# Check workflow status
workflow_status execution_id

# Review execution logs
workflow_history --status=failed

# Validate workflow template
workflow_validate workflow_definition
```

#### Validation Errors
```bash
# Check validation details
workflow_validate workflow_definition --level=strict

# Review validation history
workflow_analytics | grep validation

# Fix common issues
# - Missing required fields
# - Invalid step dependencies
# - Incorrect parameter types
```

#### Rollback Issues
```bash
# Check rollback status
GET /api/v1/workflows/rollbacks/{rollback_id}

# List available rollback points
GET /api/v1/workflows/executions/{execution_id}/rollback-points

# Manual rollback if needed
workflow_rollback execution_id --strategy=manual
```

### Performance Issues

#### Slow Workflow Execution
- Check system resources (CPU, memory, disk)
- Review step timeouts and dependencies
- Analyze network connectivity between agents
- Consider parallel execution optimization

#### High Memory Usage
- Review workflow template complexity
- Check for memory leaks in custom steps
- Optimize parameter sizes
- Enable automatic cleanup

#### Network Issues
- Verify hAIveMind agent connectivity
- Check Tailscale network status
- Review firewall configurations
- Test inter-agent communication

### Debugging

#### Enable Debug Logging
```python
import logging
logging.getLogger('workflow_automation').setLevel(logging.DEBUG)
```

#### Workflow Execution Tracing
```python
# Enable execution tracing
config['workflow_debug'] = {
    'trace_execution': True,
    'log_step_details': True,
    'capture_state': True
}
```

#### Performance Profiling
```python
# Enable performance profiling
config['workflow_profiling'] = {
    'enabled': True,
    'profile_steps': True,
    'measure_memory': True
}
```

## Best Practices

### Workflow Design

1. **Keep Steps Atomic**: Each step should perform a single, well-defined action
2. **Use Clear Dependencies**: Explicitly define step dependencies
3. **Set Appropriate Timeouts**: Balance between reliability and responsiveness
4. **Enable Rollback**: Always provide rollback commands for reversible operations
5. **Document Thoroughly**: Include clear descriptions and examples

### Parameter Management

1. **Use Default Values**: Provide sensible defaults for optional parameters
2. **Validate Input**: Always validate parameters before execution
3. **Type Consistency**: Maintain consistent parameter types across steps
4. **Secure Sensitive Data**: Never store secrets in workflow templates

### Error Handling

1. **Implement Retry Logic**: Use appropriate retry counts and backoff strategies
2. **Graceful Degradation**: Design workflows to handle partial failures
3. **Clear Error Messages**: Provide actionable error messages
4. **Log Everything**: Comprehensive logging for debugging and analysis

### Performance Optimization

1. **Parallel Execution**: Use parallel groups for independent steps
2. **Resource Efficiency**: Minimize resource usage per step
3. **Caching**: Cache frequently used data and results
4. **Batch Operations**: Combine related operations when possible

### Security

1. **Approval Gates**: Require approval for sensitive operations
2. **Access Control**: Implement proper access controls
3. **Audit Logging**: Log all workflow executions and changes
4. **Secure Communication**: Use encrypted communication between agents

## API Reference

### MCP Tools

#### workflow_suggest
```python
await workflow_suggest(
    context: Optional[str] = None,
    recent_commands: Optional[str] = None,
    intent: Optional[str] = None
) -> Dict[str, Any]
```

#### workflow_execute
```python
await workflow_execute(
    workflow_id: str,
    parameters: Optional[str] = None,
    auto_approve: bool = False
) -> Dict[str, Any]
```

#### workflow_status
```python
await workflow_status(execution_id: str) -> Dict[str, Any]
```

#### workflow_cancel
```python
await workflow_cancel(execution_id: str) -> Dict[str, Any]
```

#### workflow_list
```python
await workflow_list(category: Optional[str] = None) -> Dict[str, Any]
```

#### workflow_create
```python
await workflow_create(workflow_definition: str) -> Dict[str, Any]
```

#### workflow_analytics
```python
await workflow_analytics() -> Dict[str, Any]
```

#### workflow_autocomplete
```python
await workflow_autocomplete(partial_sequence: str) -> Dict[str, Any]
```

#### workflow_validate
```python
await workflow_validate(workflow_definition: str) -> Dict[str, Any]
```

#### workflow_history
```python
await workflow_history(
    limit: int = 10,
    status_filter: Optional[str] = None
) -> Dict[str, Any]
```

### REST API Endpoints

#### POST /api/v1/workflows/execute
Execute a workflow with parameters.

#### GET /api/v1/workflows/executions/{execution_id}
Get workflow execution status and progress.

#### POST /api/v1/workflows/executions/{execution_id}/cancel
Cancel a running workflow execution.

#### GET /api/v1/workflows/templates
List all available workflow templates.

#### GET /api/v1/workflows/templates/{template_id}
Get detailed workflow template information.

#### POST /api/v1/workflows/templates
Create a new workflow template.

#### POST /api/v1/workflows/suggest
Get intelligent workflow suggestions.

#### GET /api/v1/workflows/analytics
Get workflow system analytics and metrics.

#### POST /api/v1/workflows/validate
Validate a workflow definition.

#### POST /api/v1/workflows/executions/{execution_id}/rollback
Initiate workflow rollback.

#### GET /api/v1/workflows/rollbacks/{rollback_id}
Get rollback execution status.

#### POST /api/v1/webhooks
Create webhook configuration for event notifications.

#### DELETE /api/v1/webhooks/{webhook_id}
Delete webhook configuration.

## Contributing

### Adding New Workflow Templates

1. Define the workflow structure in `workflow_automation_engine.py`
2. Add validation rules if needed
3. Include rollback commands for reversible operations
4. Test thoroughly with various parameters
5. Document the workflow purpose and usage

### Extending Validation

1. Add new validation checks in `workflow_validation_rollback.py`
2. Update validation levels as appropriate
3. Include comprehensive error messages
4. Test with various workflow configurations

### Enhancing hAIveMind Integration

1. Implement new learning algorithms in `workflow_haivemind_integration.py`
2. Add pattern recognition capabilities
3. Enhance collective intelligence features
4. Test across multiple hAIveMind agents

## License

This workflow automation system is part of the hAIveMind project and follows the same licensing terms.

## Support

For support, issues, or feature requests:
1. Check the troubleshooting guide above
2. Review the API documentation
3. Examine the integration tests for examples
4. Consult the hAIveMind collective memory for similar issues