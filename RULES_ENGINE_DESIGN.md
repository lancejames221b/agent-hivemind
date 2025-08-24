# hAIveMind Rules Engine Architecture

## Overview

The hAIveMind Rules Engine provides intelligent agent behavior governance across the entire network. This system ensures consistent behavior, compliance, and adaptation through rule-based decision making with built-in learning and optimization capabilities.

## Core Components

### 1. Rules Engine (`src/rules_engine.py`)

**Features:**
- SQLite-based rules database with ChromaDB semantic search integration
- Rule categories: authorship, coding_style, security, compliance, operational, communication, workflow, integration
- Scope hierarchy: global → project → machine → agent → session
- Priority levels: CRITICAL (1000) → HIGH (750) → NORMAL (500) → LOW (250) → ADVISORY (100)
- Conflict resolution strategies: highest_priority, most_specific, latest_created, consensus, override

**Default Rules Included:**
- **Authorship**: Always attribute work to Lance James, Unit 221B Inc
- **Security**: Never expose secrets, defensive security only
- **Coding Style**: Minimal comments unless requested
- **Communication**: Concise responses, no emojis unless requested

### 2. Rule Inheritance System (`src/rule_inheritance.py`)

**Features:**
- Hierarchical rule inheritance with override mechanisms
- Context-aware rule application based on agent, machine, project, and session
- Rule merging with condition and action consolidation
- Inheritance validation and circular dependency detection
- Override creation for context-specific rule modifications

### 3. Rule Validation (`src/rule_validator.py`)

**Features:**
- Comprehensive syntax and logic validation
- Performance and security impact analysis
- Auto-fix capabilities for common issues
- Rule set conflict detection
- Compatibility checking with known context fields

**Validation Categories:**
- Syntax errors (malformed rules)
- Logic issues (contradictory conditions)
- Performance warnings (complex regex, large lists)
- Security implications (sensitive targets, broad conditions)
- Compatibility problems (deprecated features)

### 4. Performance Optimization (`src/rule_performance.py`)

**Features:**
- LRU cache for rule evaluation results with TTL
- Rule indexing by scope, type, priority, fields, and tags
- Condition optimization and short-circuit evaluation
- Performance metrics tracking and analytics
- Rule complexity analysis and optimization suggestions

**Performance Enhancements:**
- Condition reordering by evaluation cost
- Cache hit rate optimization
- Rule evaluation timing and profiling
- Memory usage optimization

### 5. hAIveMind Integration (`src/haivemind_rules_integration.py`)

**Features:**
- Rule evaluation with network awareness
- Pattern learning from evaluation history
- Cross-agent rule insight sharing
- Performance analytics and optimization suggestions
- Network rule synchronization

**Learning Capabilities:**
- Effectiveness pattern recognition
- Performance bottleneck identification
- Context pattern extraction
- Automated rule improvement suggestions

### 6. MCP Tools Interface (`src/rules_mcp_tools.py`)

**Available Tools:**
- `create_rule`: Create new governance rules
- `evaluate_rules`: Evaluate rules with hAIveMind awareness
- `validate_rule`: Validate rule syntax and logic
- `get_rule_suggestions`: Get AI-powered improvement suggestions
- `create_rule_override`: Create context-specific rule overrides
- `get_rules_performance`: Performance analytics and metrics
- `get_network_insights`: Network-wide rule insights
- `sync_rules_network`: Synchronize rules across network
- `learn_from_patterns`: Generate learning insights from patterns
- `get_inheritance_tree`: View rule inheritance hierarchies
- `validate_rule_set`: Validate multiple rules for conflicts

## Rule Structure

### Rule Definition
```json
{
  "id": "unique-rule-id",
  "name": "Human-readable name",
  "description": "Detailed description",
  "rule_type": "authorship|coding_style|security|compliance|operational|communication|workflow|integration",
  "scope": "global|project|machine|agent|session",
  "priority": "CRITICAL|HIGH|NORMAL|LOW|ADVISORY",
  "conditions": [
    {
      "field": "context_field",
      "operator": "eq|ne|in|regex|contains|startswith|endswith",
      "value": "comparison_value",
      "case_sensitive": true
    }
  ],
  "actions": [
    {
      "action_type": "set|append|merge|validate|block|transform|invoke",
      "target": "behavior_target",
      "value": "action_value",
      "parameters": {}
    }
  ],
  "tags": ["tag1", "tag2"],
  "conflict_resolution": "highest_priority|most_specific|latest_created|consensus|override"
}
```

### Context Fields
- `agent_id`, `machine_id`, `project_id`, `session_id`, `user_id`
- `capabilities`, `role`, `hostname`, `os`, `platform`
- `working_directory`, `git_branch`, `git_repo`, `file_type`
- `task_type`, `conversation_length`, `time_of_day`, `day_of_week`

## Integration with hAIveMind Memory System

### Memory Storage
- Rule evaluations stored as memories with category "rules"
- Learning patterns stored as structured memories
- Performance metrics tracked and shared across network
- Rule changes broadcast to all connected agents

### Network Awareness
- Real-time rule synchronization via Redis channels
- Shared learning across agent deployments
- Collective intelligence for rule optimization
- Cross-machine rule effectiveness tracking

## Usage Examples

### Creating a Security Rule
```python
create_rule({
    "name": "API Key Protection",
    "description": "Prevent exposure of API keys in code",
    "rule_type": "security",
    "scope": "global",
    "priority": "CRITICAL",
    "conditions": [
        {"field": "file_type", "operator": "in", "value": ["py", "js", "ts"]},
        {"field": "task_type", "operator": "eq", "value": "code_generation"}
    ],
    "actions": [
        {"action_type": "validate", "target": "code_content", "value": "no_api_keys"},
        {"action_type": "block", "target": "api_key_exposure", "value": True}
    ],
    "tags": ["security", "api_keys", "code_safety"]
})
```

### Evaluating Rules
```python
evaluate_rules({
    "context": {
        "agent_id": "claude-agent-001",
        "machine_id": "lance-dev",
        "project_id": "haivemind",
        "task_type": "code_generation",
        "file_type": "py"
    },
    "include_inheritance": True
})
```

### Getting Performance Insights
```python
get_rules_performance({
    "top_n": 10,
    "include_suggestions": True
})
```

## Architecture Benefits

### Consistency
- Uniform behavior across all hAIveMind agents
- Consistent application of authorship, security, and style rules
- Predictable agent responses and decision-making

### Compliance
- Automated enforcement of security policies
- Audit trail for all rule evaluations
- Compliance reporting and monitoring

### Adaptability
- Learning from usage patterns to optimize rules
- Automatic suggestion of rule improvements
- Context-aware rule application

### Performance
- Cached evaluations for fast response times
- Optimized rule matching and evaluation
- Minimal overhead for rule processing

### Scalability
- Network-wide rule distribution and synchronization
- Efficient indexing for large rule sets
- Distributed learning and optimization

## File Structure

```
src/
├── rules_engine.py              # Core rules engine
├── rule_inheritance.py          # Inheritance and override system
├── rule_validator.py            # Validation and syntax checking
├── rule_performance.py          # Performance optimization
├── haivemind_rules_integration.py # hAIveMind network integration
├── rules_mcp_tools.py           # MCP tools interface
└── memory_server.py            # Updated with rules integration
```

## Configuration

Rules engine configuration is part of the main `config/config.json`:

```json
{
  "rules_db_path": "data/rules.db",
  "cache_size": 1000,
  "cache_ttl": 300,
  "enable_caching": true,
  "enable_indexing": true,
  "enable_condition_optimization": true
}
```

## Future Enhancements

1. **Machine Learning Integration**: AI-powered rule generation from patterns
2. **Visual Rule Builder**: GUI for creating and managing rules
3. **A/B Testing**: Compare rule effectiveness across different configurations
4. **Rule Templates**: Pre-built rule sets for common scenarios
5. **External Integration**: Import rules from external policy systems
6. **Advanced Analytics**: Detailed rule impact analysis and reporting

---

**Author**: Lance James, Unit 221B Inc  
**Created**: 2025-08-24  
**Status**: Story 6a Implementation Complete