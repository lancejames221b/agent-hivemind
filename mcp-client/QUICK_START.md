# hAIveMind MCP Client - Quick Start

## 🚀 One-Command Setup

```bash
# Install the MCP client
cd mcp-client && ./install.sh

# Configure for cursor-agent
cp config/cursor-agent.json ../.cursor/mcp.json

# Test the integration
cursor-agent mcp list-tools haivemind
```

## ✅ Verified Working

- **12 tools available** via `cursor-agent mcp list-tools haivemind`
- **Standalone MCP client** works with any MCP system
- **Multiple configurations** for different environments
- **Complete documentation** and examples

## 🔧 Available Tools

1. **store_memory** - Store memories with sharing control
2. **search_memories** - Full-text and semantic search  
3. **retrieve_memory** - Get specific memory by ID
4. **get_recent_memories** - Time-based memory retrieval
5. **get_memory_stats** - Memory system statistics
6. **register_agent** - Register as hAIveMind agent
7. **get_agent_roster** - View active agents
8. **delegate_task** - Assign tasks to agents
9. **broadcast_discovery** - Share findings network-wide
10. **record_incident** - Log infrastructure incidents
11. **generate_runbook** - Create operational procedures
12. **sync_ssh_config** - Sync SSH configurations

## 📋 Ready-to-Use Configurations

- `config/cursor-agent.json` - For cursor-agent integration
- `config/claude-desktop.json` - For Claude Desktop
- `config/remote-access.json` - For Tailscale remote access
- `examples/development.json` - Development environment
- `examples/production.json` - Production deployment
- `examples/multi-environment.json` - Multiple hAIveMind instances

## 🎯 Status: PRODUCTION READY

The hAIveMind MCP client is fully operational and can be imported into any MCP-compatible system for instant access to the distributed AI coordination network.