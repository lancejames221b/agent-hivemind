```
    ╭─────────────────────────────────────────────────────────────────╮
    │                                                                 │
    │      ██╗  ██╗ █████╗ ██╗██╗   ██╗███████╗███╗   ███╗██╗███╗   ██╗██████╗   │
    │      ██║  ██║██╔══██╗██║██║   ██║██╔════╝████╗ ████║██║████╗  ██║██╔══██╗  │
    │      ███████║███████║██║██║   ██║█████╗  ██╔████╔██║██║██╔██╗ ██║██║  ██║  │
    │      ██╔══██║██╔══██║██║╚██╗ ██╔╝██╔══╝  ██║╚██╔╝██║██║██║╚██╗██║██║  ██║  │
    │      ██║  ██║██║  ██║██║ ╚████╔╝ ███████╗██║ ╚═╝ ██║██║██║ ╚████║██████╔╝  │
    │      ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝  ╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝   │
    │                                                                 │
    │    🧠🤖 Distributed AI Collective Memory for DevOps Automation 🤖🧠    │
    │                                                                 │
    │      ┌─[AGENT]─┐    ┌─[AGENT]─┐    ┌─[AGENT]─┐    ┌─[AGENT]─┐      │
    │      │ 🧠 ⚡ 🛠️ │◄──►│ 🧠 ⚡ 🛠️ │◄──►│ 🧠 ⚡ 🛠️ │◄──►│ 🧠 ⚡ 🛠️ │      │
    │      └─────────┘    └─────────┘    └─────────┘    └─────────┘      │
    │           ▲              ▲              ▲              ▲           │
    │           └──────────────┼──────────────┼──────────────┘           │
    │                     ┌────▼──────────────▼────┐                     │
    │                     │   🧠 COLLECTIVE 🧠    │                     │
    │                     │      MEMORY HUB       │                     │
    │                     └───────────────────────┘                     │
    │                                                                 │
    ╰─────────────────────────────────────────────────────────────────╯
```

# ClaudeOps hAIveMind - Distributed AI Memory & Coordination System

**A Model Context Protocol (MCP) server enabling distributed AI agent coordination with persistent collective memory across infrastructure networks.**

**Author:** Lance James, Unit 221B, Inc

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start hAIveMind services
python src/memory_server.py &
python src/remote_mcp_server.py &  # MCP/SSE endpoints on port 8900
python src/dashboard_server.py &   # Dashboard on port 8901

# 3. Access the services
# Dashboard: http://localhost:8901/admin/    ⚠️ INCONSISTENT - NEEDS FIX
# MCP SSE:   http://localhost:8900/sse
# Health:    http://localhost:8900/health

# ⚠️ WARNING: Architecture inconsistency - see ticket for unified port plan

# 4. Install MCP client
cd mcp-client && ./install.sh

# 5. Test integration
cursor-agent mcp list-tools haivemind
```

## 📁 Repository Structure

```
memory-mcp/
├── 🧠 Core System
│   ├── src/                    # Main hAIveMind server code
│   ├── config/                 # System configuration files
│   └── services/               # Systemd service definitions
│
├── 🔌 MCP Integration
│   ├── mcp-client/             # Portable MCP client for any system
│   │   ├── src/                # Client implementations
│   │   ├── config/             # Ready-to-use configurations
│   │   ├── examples/           # Environment-specific examples
│   │   └── docs/               # Complete documentation
│   └── .cursor/                # Cursor-agent configuration
│
├── 🛠️ Tools & Scripts
│   ├── scripts/                # Utility and setup scripts
│   ├── tools/                  # Standalone tools and installers
│   └── admin/                  # Web admin interface
│
├── 📚 Documentation
│   ├── docs/                   # Main documentation
│   │   └── stories/            # Implementation stories
│   ├── commands/               # Command documentation
│   └── examples/               # Configuration examples
│
├── 🧪 Testing & Development
│   ├── tests/                  # Test suites
│   └── INSTALL/                # Installation guides
│
└── 📊 Data & Logs
    ├── data/                   # ChromaDB storage
    ├── database/               # SQLite databases
    └── logs/                   # System logs
```

## ✨ Key Features

### 🧠 Collective Intelligence
- **Distributed Memory**: ChromaDB + Redis for persistent, searchable memory
- **Agent Coordination**: Task delegation and knowledge sharing across the network
- **Real-Time Sync**: Vector clocks for conflict resolution during synchronization

### 🔌 Universal MCP Integration
- **Portable Client**: Works with Claude Desktop, cursor-agent, and any MCP system
- **12 Core Tools**: Memory operations, agent coordination, infrastructure management
- **Multiple Configurations**: Development, production, and multi-environment setups

### 🌐 Network Architecture
- **Tailscale VPN**: Secure machine-to-machine communication
- **Multi-Machine Support**: Elasticsearch clusters, proxy fleets, development environments
- **Service Discovery**: Automatic agent registration and capability detection

### 🛠️ DevOps Integration
- **Infrastructure Tracking**: State snapshots and configuration synchronization
- **Incident Management**: Automated correlation and resolution tracking
- **Runbook Generation**: Reusable procedures from successful operations
- **External Connectors**: Confluence, Jira, and custom API integrations

## 🎯 Production Status

✅ **PRODUCTION READY** - Successfully deployed and tested:
- **MCP Integration**: 12 tools available via cursor-agent
- **Distributed Memory**: Multi-machine synchronization operational
- **Agent Coordination**: Task delegation and knowledge sharing active
- **Infrastructure Management**: SSH configs, service monitoring, incident tracking

## 📖 Documentation

- **[MCP Integration Guide](mcp-client/docs/README.md)** - Complete MCP client documentation
- **[Quick Start Guide](mcp-client/QUICK_START.md)** - One-command setup
- **[Installation Guide](INSTALL/)** - Detailed setup instructions
- **[Command Reference](commands/)** - All available commands and tools

## 🚀 Getting Started

### Local Development
```bash
# Start all services
./tools/start-haivemind.sh

# Install MCP client
cd mcp-client && ./install.sh

# Configure cursor-agent
cp mcp-client/config/cursor-agent.json .cursor/mcp.json
```

### Remote Access
```bash
# Use Tailscale configuration
cp mcp-client/config/remote-access.json .cursor/mcp.json

# Test remote connection
cursor-agent mcp list-tools haivemind-remote
```

### Production Deployment
```bash
# Install as systemd services
sudo ./services/install-services.sh

# Configure for production
cp mcp-client/examples/production.json .cursor/mcp.json
```

## 🤖 Available Tools

### Core Memory Operations
- `store_memory` - Store memories with comprehensive tracking
- `search_memories` - Full-text and semantic search
- `retrieve_memory` - Get specific memory by ID
- `get_recent_memories` - Time-based memory retrieval
- `get_memory_stats` - Memory system statistics

### Agent Coordination
- `register_agent` - Register as hAIveMind agent
- `get_agent_roster` - View all active agents
- `delegate_task` - Assign tasks to specialized agents
- `broadcast_discovery` - Share findings network-wide

### Infrastructure & DevOps
- `record_incident` - Log infrastructure incidents
- `generate_runbook` - Create operational procedures
- `sync_ssh_config` - Synchronize SSH configurations

## 🔧 Configuration

The system supports multiple deployment scenarios:

- **Development**: Local services with file-based storage
- **Production**: Distributed services with Redis clustering
- **Hybrid**: Mix of local and remote hAIveMind instances
- **Multi-Environment**: Separate dev/staging/prod coordination

See `mcp-client/examples/` for ready-to-use configurations.

## 🛡️ Security

- **Encrypted Storage**: All credentials encrypted with AES-256-CBC
- **Network Security**: Tailscale VPN for all inter-machine communication
- **Access Control**: JWT authentication and role-based permissions
- **Data Privacy**: GDPR-compliant deletion and export tools

## 📊 Network Topology

The hAIveMind system operates across multiple machine groups:

- **Orchestrators** (`lance-dev`): Primary coordination and memory hubs
- **Elasticsearch** (`elastic1-5`): Search specialists with cluster management
- **Databases** (`mysql`, `mongodb`): Data operation specialists
- **Scrapers** (`proxy0-9`): Data collection and processing agents
- **Monitoring** (`grafana`, `auth-server`): Infrastructure monitoring specialists

Each machine maintains local memory with network-wide synchronization capabilities.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙋 Support

- **Issues**: GitHub Issues for bug reports and feature requests
- **Documentation**: Comprehensive guides in `docs/` directory
- **Examples**: Working configurations in `examples/` directory

---

**ClaudeOps hAIveMind** - Enabling distributed AI coordination for the future of DevOps automation.