# hAIveMind Rules Database and Management System

## Overview

The hAIveMind Rules Database and Management System provides comprehensive governance for AI agent behavior across the entire network. This system implements Story 6b requirements with full database storage, versioning, import/export, templates, and hAIveMind network awareness.

## Architecture Components

### Core Components

1. **RulesDatabase** (`src/rules_database.py`)
   - SQLite-based storage with comprehensive schema
   - Version tracking and change history
   - Rule dependencies and relationships
   - Scope assignments and effective dates
   - Template storage and management
   - ChromaDB integration for semantic search

2. **RuleManagementService** (`src/rule_management_service.py`)
   - High-level rule management operations
   - YAML/JSON format support
   - Validation and error handling
   - Search and filtering capabilities
   - Rule cloning and inheritance

3. **RulesHAIveMindIntegration** (`src/rules_haivemind_integration.py`)
   - Network awareness and collaboration
   - Pattern discovery and learning
   - Effectiveness analytics
   - Cross-network synchronization
   - Memory system integration

4. **Enhanced MCP Tools** (`src/rules_mcp_tools_enhanced.py`)
   - Comprehensive MCP interface
   - All CRUD operations
   - Import/export functionality
   - Network insights and analytics

## Database Schema

### Core Tables

#### rules
- **id**: Unique rule identifier
- **name**: Human-readable rule name
- **description**: Detailed rule description
- **rule_type**: Category (authorship, security, coding_style, etc.)
- **scope**: Application scope (global, project, machine, agent, session)
- **priority**: Execution priority (100-1000)
- **status**: Lifecycle status (active, inactive, deprecated, testing)
- **conditions**: JSON array of rule conditions
- **actions**: JSON array of rule actions
- **tags**: JSON array of categorization tags
- **created_at/updated_at**: Timestamps
- **created_by/updated_by**: User tracking
- **version**: Version number
- **parent_rule_id**: Inheritance relationship
- **conflict_resolution**: Strategy for handling conflicts
- **effective_from/until**: Scheduling dates
- **metadata**: Additional rule metadata

#### rule_versions
- **id**: Version entry identifier
- **rule_id**: Reference to parent rule
- **version**: Version number
- **change_type**: Type of change (created, updated, activated, etc.)
- **rule_data**: Complete rule data at this version
- **changed_by**: User who made the change
- **changed_at**: Timestamp of change
- **change_reason**: Optional reason for change
- **metadata**: Change-specific metadata

#### rule_assignments
- **id**: Assignment identifier
- **rule_id**: Reference to rule
- **scope_type**: Type of scope (global, project, machine, agent, user)
- **scope_id**: Specific scope identifier
- **priority_override**: Override priority for this assignment
- **effective_from/until**: Assignment scheduling
- **metadata**: Assignment-specific metadata

#### rule_dependencies
- **id**: Dependency identifier
- **rule_id**: Dependent rule
- **depends_on_rule_id**: Required rule
- **dependency_type**: Type (requires, conflicts, enhances, replaces)
- **metadata**: Dependency-specific data

#### rule_templates
- **id**: Template identifier
- **name**: Template name
- **description**: Template description
- **rule_type**: Category of rules this template creates
- **template_data**: Template structure with placeholders
- **category**: Template category
- **tags**: Template tags
- **created_by**: Template creator
- **metadata**: Template-specific data

#### rule_categories
- **id**: Category identifier
- **name**: Category name
- **description**: Category description
- **parent_id**: Hierarchical parent category
- **metadata**: Category-specific data

## Rule Definition Format

### YAML Format
```yaml
name: "Rule Name"
description: "Detailed description"
rule_type: "authorship|security|coding_style|compliance|operational|communication|workflow|integration"
scope: "global|project|machine|agent|session"
priority: 100-1000
status: "active|inactive|deprecated|testing"

conditions:
  - field: "context_field"
    operator: "eq|ne|in|regex|contains|startswith|endswith|gt|lt|gte|lte"
    value: "comparison_value"
    case_sensitive: true

actions:
  - action_type: "set|append|merge|validate|block|transform|invoke"
    target: "behavior_target"
    value: "action_value"
    parameters: {}

tags: ["tag1", "tag2"]
effective_from: "2025-08-24T00:00:00Z"  # Optional
effective_until: null  # Optional
conflict_resolution: "highest_priority|most_specific|latest_created|consensus|override"
metadata: {}
```

### JSON Format
```json
{
  "name": "Rule Name",
  "description": "Detailed description",
  "rule_type": "security",
  "scope": "global",
  "priority": 1000,
  "status": "active",
  "conditions": [
    {
      "field": "task_type",
      "operator": "eq",
      "value": "code_generation",
      "case_sensitive": false
    }
  ],
  "actions": [
    {
      "action_type": "validate",
      "target": "code_content",
      "value": "no_secrets",
      "parameters": {
        "patterns": [".*api.*key.*", ".*secret.*"]
      }
    }
  ],
  "tags": ["security", "validation"],
  "metadata": {}
}
```

## Core Rule Types

### Authorship Rules
- Control code and content attribution
- Enforce organizational policies
- Disable AI attribution when required

### Security Rules
- Prevent secret exposure
- Enforce defensive security practices
- Block malicious code patterns

### Coding Style Rules
- Control comment policies
- Enforce formatting standards
- Manage documentation requirements

### Communication Rules
- Set response style and format
- Control emoji and formatting usage
- Manage verbosity levels

### Compliance Rules
- Enforce regulatory requirements
- Implement audit policies
- Manage data handling rules

### Workflow Rules
- Control development processes
- Manage tool usage patterns
- Enforce review requirements

### Integration Rules
- Manage API usage patterns
- Control service connections
- Handle external dependencies

### Operational Rules
- Set logging and monitoring levels
- Control performance requirements
- Manage error handling

## Rule Scope Hierarchy

1. **Global**: Network-wide rules that apply everywhere
2. **Project**: Project-specific rules
3. **Machine**: Machine-specific rules  
4. **Agent**: Agent-specific rules
5. **Session**: Session-specific rules

Rules at more specific scopes can override broader scopes based on conflict resolution strategy.

## Priority Levels

- **CRITICAL (1000)**: System-critical rules (security, compliance)
- **HIGH (750)**: Important behavior rules (authorship, workflows)
- **NORMAL (500)**: Standard preferences (coding style, communication)
- **LOW (250)**: Convenience rules (operational preferences)
- **ADVISORY (100)**: Suggestions and recommendations

## MCP Tools Available

### Core Rule Management
- `create_rule`: Create new rules from parameters
- `create_rule_from_yaml`: Create from YAML format
- `create_rule_from_json`: Create from JSON format
- `update_rule`: Update existing rules with versioning
- `get_rule`: Retrieve rules in various formats
- `activate_rule`/`deactivate_rule`: Control rule lifecycle
- `clone_rule`: Clone rules with modifications

### Version and History Management
- `get_rule_version_history`: View complete change history
- `create_rule_dependency`: Define rule relationships
- `assign_rule_to_scope`: Assign rules to specific scopes

### Import/Export Operations
- `export_rules`: Export to YAML/JSON with optional history
- `import_rules`: Import from YAML/JSON with validation
- `backup_rules_database`: Create database backups

### Template Management
- `create_rule_from_template`: Create rules from templates
- `list_rule_templates`: View available templates

### Search and Analytics
- `search_rules`: Text and semantic search with filters
- `get_rule_statistics`: Comprehensive system statistics

### hAIveMind Integration
- `analyze_rule_effectiveness`: Performance analytics
- `discover_rule_patterns`: Network pattern discovery
- `recommend_rule_improvements`: AI-powered suggestions
- `sync_rules_network`: Network synchronization
- `get_network_rule_insights`: Cross-network analytics
- `learn_from_rule_patterns`: Machine learning insights
- `get_rule_inheritance_tree`: Inheritance visualization

## hAIveMind Network Features

### Memory Integration
- All rule operations stored as structured memories
- Cross-network pattern sharing
- Collaborative learning from rule usage
- Audit trails for compliance

### Pattern Discovery
- Automatic detection of usage patterns
- Identification of performance bottlenecks
- Discovery of configuration anomalies
- Effectiveness trend analysis

### Network Synchronization
- Real-time rule distribution via Redis
- Conflict-free network updates
- Machine-specific rule assignments
- Distributed analytics aggregation

### Learning and Optimization
- Historical performance analysis
- AI-powered improvement suggestions
- Automatic optimization recommendations
- Collective intelligence insights

## Configuration

Rules system configuration in `config/config.json`:

```json
{
  "rules": {
    "database_path": "data/rules.db",
    "enable_versioning": true,
    "enable_dependencies": true,
    "enable_scheduling": true,
    "enable_haivemind_integration": true,
    "backup_interval": 86400,
    "backup_path": "data/backups/rules",
    "export_formats": ["yaml", "json"],
    "import_validation": "strict",
    "performance": {
      "cache_size": 1000,
      "cache_ttl": 300,
      "enable_indexing": true,
      "enable_optimization": true
    }
  }
}
```

## Examples and Templates

### Default Templates Available
1. **Basic Authorship Rule**: Set author attribution
2. **No Secrets Exposure**: Security template for secret detection
3. **Comment Policy**: Control code commenting behavior

### Rule Examples
- See `examples/rules/` directory for complete examples
- `authorship_rule.yaml`: Global authorship enforcement
- `security_rule.json`: API key protection
- `coding_style_rule.yaml`: Comment policy
- `project_specific_rule.yaml`: Project-scoped logging
- `complete_rule_set.yaml`: Comprehensive rule set

## Usage Examples

### Creating a Basic Rule
```bash
# Via YAML
create_rule_from_yaml:
  yaml_content: |
    name: "Test Rule"
    description: "Test rule description"
    rule_type: "operational"
    scope: "global"
    priority: 500
    conditions: []
    actions:
      - action_type: "set"
        target: "test_setting"
        value: true
    tags: ["test"]
```

### Importing a Rule Set
```bash
import_rules:
  import_data: "$(cat examples/rules/complete_rule_set.yaml)"
  format: "yaml"
  imported_by: "admin"
  overwrite: false
```

### Analyzing Rule Effectiveness
```bash
analyze_rule_effectiveness:
  rule_id: "auth-global-001"
  days: 30
```

### Network Synchronization
```bash
sync_rules_network:
  rule_ids: ["auth-global-001", "sec-global-001"]
```

## Integration with hAIveMind Memory System

The rules system is fully integrated with the hAIveMind memory system:

- **Memory Category**: All rule operations stored under "rules" category
- **Network Sharing**: Rule memories shared across network with "network-shared" scope
- **Pattern Learning**: Historical patterns analyzed for optimization suggestions
- **Audit Trails**: Complete operation history for compliance and debugging
- **Cross-Machine Analytics**: Usage patterns tracked across all network machines

## Performance and Optimization

### Database Optimization
- Comprehensive indexing on frequently queried fields
- Connection pooling for high-throughput operations
- Lazy loading for large rule sets
- Efficient JSON field handling

### Caching Strategy
- LRU cache for frequently accessed rules
- TTL-based cache invalidation
- Network-aware cache coherence
- Performance metric tracking

### Semantic Search
- ChromaDB integration for intelligent rule discovery
- Vector embeddings for rule similarity
- Context-aware search results
- Machine learning enhanced matching

## Security and Compliance

### Access Control
- User-based rule creation and modification tracking
- Audit logs for all rule changes
- Role-based access control integration
- Secure backup and recovery

### Data Protection
- Encrypted storage for sensitive rule data
- Secure network communication via Tailscale
- PII protection in rule definitions
- Compliance with data retention policies

## Monitoring and Alerting

### Rule Performance Monitoring
- Execution time tracking
- Success/failure rate analysis
- Resource usage monitoring
- Performance trend analysis

### Network Health Monitoring
- Cross-machine rule distribution status
- Synchronization health metrics
- Pattern anomaly detection
- System performance dashboards

## Future Enhancements

1. **Machine Learning Integration**: AI-powered rule generation from patterns
2. **Visual Rule Builder**: GUI for creating and managing rules
3. **A/B Testing**: Compare rule effectiveness across configurations
4. **Advanced Analytics**: Detailed rule impact analysis and reporting
5. **External Integration**: Import rules from external policy systems
6. **Real-time Notifications**: Instant alerts for rule violations and changes

---

**Author**: Lance James, Unit 221B Inc  
**Created**: 2025-08-24  
**Status**: Story 6b Implementation Complete