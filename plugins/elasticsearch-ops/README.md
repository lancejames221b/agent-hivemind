# Elasticsearch Ops Plugin

Elasticsearch cluster management, monitoring, and troubleshooting for hAIveMind agents.

## Components

### Commands
- **es-health** - Cluster health check and diagnostics

### Agents
- **es-specialist** - Expert agent for ES cluster operations

### Skills
- **elasticsearch-expertise** - Deep knowledge for ES troubleshooting

## Machine Groups

This plugin is designed for:
- `elasticsearch` - ES cluster nodes
- `orchestrators` - Central coordination machines

## Installation

```bash
# Via hv-plugin command
hv-plugin install plugin_elasticsearch-ops_1_0_0

# The plugin will auto-install on machines in compatible groups
hv-plugin sync --auto-install
```

## Requirements

- hAIveMind Core plugin (haivemind-core)
- Access to Elasticsearch cluster (localhost:9200 by default)

## Usage

### Health Check
```
/es-health
/es-health --detailed
/es-health --fix
```

### Specialist Agent
The es-specialist agent is automatically available for delegation:
```
delegate_task task_description="Check Elasticsearch cluster health" required_capabilities=["elasticsearch_ops"]
```

### Skill Activation
The elasticsearch-expertise skill auto-activates when discussing:
- Cluster health issues
- Search performance
- Shard allocation
- JVM/heap problems

## Compatibility

Compatible with Elasticsearch 7.x and 8.x clusters.
