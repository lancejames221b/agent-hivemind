# hAIveMind Core Plugin

Core commands, agents, and skills for the hAIveMind collective intelligence network.

## Components

### Commands
- **remember** - Store knowledge in collective memory
- **recall** - Search and retrieve memories

### Agents
- **coordinator** - Central coordinator for multi-agent operations

### Skills
- **collective-memory** - Expertise in using the hAIveMind memory system

## Installation

```bash
# Using hv-plugin command
hv-plugin install plugin_haivemind-core_1_0_0

# Or via MCP tools
register_plugin plugin_path="./plugins/haivemind-core"
publish_plugin plugin_id="plugin_haivemind-core_1_0_0"
install_plugin plugin_id="plugin_haivemind-core_1_0_0"
```

## Requirements

- hAIveMind MCP server running
- Redis for agent coordination
- ChromaDB for vector storage

## Usage

After installation, the following are available:

### Commands
```
/remember "API key rotation on 1st of month" security --tags="api,rotation"
/recall "api key rotation"
```

### Agent
The coordinator agent activates for:
- Multi-agent task delegation
- Cross-team knowledge queries
- Collective decision-making

### Skill
The collective-memory skill auto-activates when:
- Storing or searching memories
- Coordinating with other agents
- Managing collective knowledge

## Compatibility

This plugin is compatible with all machine groups (no restrictions).
