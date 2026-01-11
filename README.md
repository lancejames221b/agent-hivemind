# hAIveMind - Distributed AI DevOps Intelligence Platform

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
    │    🧠 Distributed AI Collective Memory & DevOps Automation 🚀    │
    │                                                                 │
    │      ┌─[AGENT]─┐    ┌─[AGENT]─┐    ┌─[AGENT]─┐    ┌─[AGENT]─┐      │
    │      │ 🧠 ⚡ 🛠️ │◄──►│ 🧠 ⚡ 🛠️ │◄──►│ 🧠 ⚡ 🛠️ │◄──►│ 🧠 ⚡ 🛠️ │      │
    │      └─────────┘    └─────────┘    └─────────┘    └─────────┘      │
    │           ▲              ▲              ▲              ▲           │
    │           └──────────────┼──────────────┼──────────────┘           │
    │                     ┌────▼──────────────▼────┐                     │
    │                     │   🧠 COLLECTIVE 🧠    │                     │
    │                     │    MEMORY & RULES     │                     │
    │                     └───────────────────────┘                     │
    │                                                                 │
    ╰─────────────────────────────────────────────────────────────────╯
```

**Enterprise-grade Model Context Protocol (MCP) server enabling distributed AI agent coordination, persistent collective memory, intelligent automation, and comprehensive DevOps orchestration across infrastructure networks.**

**Author:** Lance James, Unit 221B, Inc
**License:** MIT
**Version:** 2.0.0
**Status:** Production Ready

---

## 🎯 Overview

hAIveMind is a comprehensive distributed intelligence platform that enables multiple AI agents to collaborate seamlessly across infrastructure networks with persistent memory, intelligent automation, and advanced DevOps capabilities. Built on the Model Context Protocol (MCP), it provides a unified framework for:

- **Collective Memory**: Persistent, searchable knowledge shared across all agents
- **Agent Coordination**: Task delegation, knowledge sharing, and collaborative problem-solving
- **Infrastructure Automation**: Configuration management, deployment orchestration, and monitoring
- **Intelligent Rules Engine**: Dynamic rule execution with dependency management and compliance
- **Playbook Automation**: Auto-generated runbooks from successful operational patterns
- **Credential Vault**: Enterprise-grade secure credential storage with encryption
- **External Integrations**: Confluence, Jira, and custom API connectors

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/lancejames221b/haivemind-mcp-server.git
cd haivemind-mcp-server

# Install dependencies
pip install -r requirements.txt

# Install Redis (required for coordination)
sudo apt-get install redis-server
sudo systemctl start redis-server
```

### Start Services

```bash
# Start all hAIveMind services
python src/remote_mcp_server.py &    # MCP/SSE server on port 8900
python src/sync_service.py &         # Sync service on port 8899
python src/dashboard_server.py &     # Dashboard on port 8901

# Verify services are running
curl http://localhost:8900/health
curl http://localhost:8899/api/status
```

### Configure MCP Client

```bash
# For Claude Desktop
cat > ~/.config/claude/claude_desktop_config.json <<EOF
{
  "mcpServers": {
    "haivemind": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-http", "http://localhost:8900/sse"]
    }
  }
}
EOF

# For Cursor AI
cp mcp-client/config/cursor-agent.json .cursor/mcp.json

# Test connection
curl http://localhost:8900/sse
```

---

## 📁 Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     FastMCP HTTP/SSE Server                     │
│                      (Port 8900) - 6 Active Tools               │
├─────────────────────────────────────────────────────────────────┤
│           Memory Management  │  Agent Coordination              │
├─────────────────────────────────────────────────────────────────┤
│            Sync Service (Port 8899) - REST API                  │
│          Machine-to-Machine Synchronization                     │
├─────────────────────────────────────────────────────────────────┤
│              Storage Layer                                      │
│  ChromaDB (Vectors) │ Redis (Cache) │ SQLite (Rules/Projects)  │
└─────────────────────────────────────────────────────────────────┘
```

### Network Topology

hAIveMind operates across multiple machine groups via Tailscale VPN:

- **Orchestrators** (lance-dev): Primary coordination and memory hubs
- **Elasticsearch** (elastic1-5): Search specialists with cluster management
- **Databases** (mysql, mongodb, kafka): Data operation specialists
- **Scrapers** (proxy0-9, telegram/discord-scraper): Data collection agents
- **Dev Environments** (tony-dev, mike-dev, oleg-dev, chris-dev): Development testing
- **Monitoring** (grafana, auth-server): Infrastructure monitoring specialists
- **Personal** (ljs-macbook-pro, m2, max): Development and administration

### Data Flow

```
AI Agent → MCP Client → HTTP/SSE (Port 8900) → FastMCP Server → Tools
                                                    ↓
                        ChromaDB ← Redis Cache → Memory Storage
                                                    ↓
                        Sync Service (Port 8899) → Network Machines
```

---

## ✨ Key Features

### 🧠 Collective Memory System

- **Persistent Storage**: ChromaDB for vector embeddings + Redis for caching
- **Semantic Search**: Full-text and vector similarity search across all memories
- **Category Management**: 14+ specialized categories (infrastructure, incidents, deployments, etc.)
- **Machine Context**: Comprehensive tracking of which agents store what knowledge
- **Sharing Control**: Fine-grained control over memory sharing and synchronization
- **Project Tracking**: Automatic project context detection and scoping
- **Token-Optimized Format (v2)**: Auto-teaches optimal compression on first memory access - 60-80% token reduction

**Active Tools:**
- `store_memory` - Store memories with machine tracking and sharing control
- `retrieve_memory` - Get specific memory by ID
- `search_memories` - Full-text and semantic search with filters
- `get_recent_memories` - Time-based memory retrieval
- `get_memory_stats` - Statistics about stored memories
- `get_format_guide` - Get format guide for token-optimized memory storage
- `get_memory_access_stats` - View session access statistics

### 🤖 Agent Coordination

- **Agent Registry**: Central registry of all active hAIveMind agents
- **Task Delegation**: Smart task routing based on agent capabilities
- **Knowledge Sharing**: Broadcast discoveries network-wide in real-time
- **Expertise Routing**: Automatic routing to specialist agents
- **Collaborative Problem-Solving**: Multi-agent consensus for complex decisions

**Active Tools:**
- `register_agent` - Register as hAIveMind agent with role and capabilities
- `get_agent_roster` - View all active agents and their status
- `delegate_task` - Assign tasks to specialized agents
- `broadcast_discovery` - Share findings with all agents
- `get_broadcasts` - Retrieve recent broadcasts

### 🔧 Infrastructure Configuration Management

- **Configuration Snapshots**: Version-controlled config tracking with drift detection
- **State Tracking**: Infrastructure state snapshots for monitoring
- **Drift Detection**: ML-powered detection of configuration drift
- **Alert System**: Intelligent alerts for configuration changes
- **Pattern Analysis**: Automated analysis of configuration patterns
- **Compliance Checking**: Framework-specific validation (SOX, HIPAA, PCI-DSS, GDPR)

**Active Tools:**
- `create_config_snapshot` - Create configuration snapshots with metadata
- `get_config_history` - Comprehensive configuration history
- `detect_config_drift` - Intelligent drift detection with ML
- `create_config_alert` - Set up alerts for configuration changes
- `analyze_config_patterns` - Analyze patterns across configurations
- `track_infrastructure_state` - Record infrastructure state snapshots

### 📋 Rules Engine

- **Dynamic Rule Execution**: Execute rules with dependency management
- **Rule Templates**: Pre-built templates for common scenarios
- **Compliance Rules**: Framework-specific compliance validation
- **Rule Versioning**: Complete rule lifecycle management
- **Dependency Tracking**: Automatic dependency resolution
- **Performance Optimization**: Cached rule execution with indexing

**Features:**
- 11 core rules management tools
- 14 advanced rules tools
- REST API synchronization (port 8899)
- Template library for common patterns
- Compliance frameworks support

### 📚 Playbook Automation

- **Auto-Generation**: Automatically create playbooks from successful operations
- **Pattern Recognition**: ML-based pattern extraction from operational history
- **Smart Recommendations**: Context-aware playbook suggestions
- **Execution Engine**: Validate and execute playbooks with rollback support
- **Confluence Integration**: Import/export playbooks to Confluence
- **Feedback Loop**: Continuous improvement from execution results

**Features:**
- 20 playbook CRUD tools
- 8 execution and control tools
- 9 auto-generation tools
- 8 Confluence integration tools
- Version control and approval workflows

### 💼 Backup & Disaster Recovery

- **Automated Backups**: Scheduled backups with retention policies
- **Multiple Backup Types**: Full, incremental, differential, metadata-only
- **Verification System**: Automatic integrity verification and corruption detection
- **Rotation Management**: Smart backup rotation with S3 archiving
- **Disaster Recovery**: Automated recovery procedures with health monitoring
- **Cross-System Coordination**: Coordinated backups across infrastructure

**Active Tools:**
- `create_full_backup` - Create comprehensive system backups
- `verify_backup` - Verify backup integrity with checksums
- `list_backups` - List all backups with metadata
- `compare_backups` - Compare backups to detect changes
- `restore_backup` - Restore from backup with validation
- `rotate_backups` - Smart backup rotation with retention
- `archive_backup_to_s3` - Archive backups to S3 storage

### 🖥️ MCP Server Hosting

- **Dynamic Hosting**: Upload and host custom MCP servers
- **Lifecycle Management**: Start, stop, restart, and delete hosted servers
- **Health Monitoring**: Real-time server health and performance monitoring
- **Resource Optimization**: Automatic resource management and cleanup
- **Dashboard Interface**: Web-based management dashboard (port 8910)
- **Security Sandbox**: Isolated execution environment for hosted servers

**Active Tools:**
- `upload_mcp_server` - Upload custom MCP server code
- `start_mcp_server` - Start hosted MCP server
- `stop_mcp_server` - Stop running MCP server
- `restart_mcp_server` - Restart MCP server
- `get_mcp_server_status` - Get server status and metrics
- `get_mcp_server_logs` - Retrieve server logs
- `delete_mcp_server` - Remove hosted server
- `get_hosting_stats` - Overall hosting statistics

### 🔒 Credential Vault (Story 8b)

- **Enterprise Encryption**: AES-256-GCM authenticated encryption
- **Multiple Key Derivation**: PBKDF2, Scrypt, HKDF support
- **Access Control**: Role-based access with multi-signature approval
- **Audit Trail**: Comprehensive logging with anomaly detection
- **Key Rotation**: Automated key rotation with version management
- **Compliance**: SOX, HIPAA, PCI-DSS, GDPR support
- **hAIveMind Integration**: Threat intelligence and collaborative security

**Features:**
- 15 vault security tools
- PostgreSQL with row-level security
- HSM integration support
- Automated backup and recovery
- Multi-factor authentication

### 🔄 Workflow Automation

- **Visual Workflows**: Define multi-step automation workflows
- **Conditional Execution**: Branch logic based on execution results
- **Error Handling**: Comprehensive error handling with retry logic
- **Workflow Suggestions**: AI-powered workflow recommendations
- **Execution History**: Complete audit trail of workflow executions
- **Performance Analytics**: Detailed metrics and trend analysis

**Features:**
- 14 workflow automation tools
- Visual workflow designer
- Template library
- Integration with playbooks and rules
- Real-time execution monitoring

### 🌐 External Integrations

- **Confluence**: Import/export playbooks, sync documentation
- **Jira**: Import issues as incidents, sync tickets
- **Custom APIs**: Extensible connector framework
- **Webhook Support**: Real-time event notifications
- **SSO Integration**: LDAP, Active Directory, SAML support

**Active Tools:**
- `sync_external_knowledge` - Sync from all configured sources
- `fetch_from_confluence` - Import Confluence documentation
- `fetch_from_jira` - Import Jira issues
- `upload_playbook` - Upload external playbooks

### 🎨 Comet# AI Browser Portal

Ultra-lightweight interface optimized for AI browser automation:

- **90% Smaller**: Minimal HTML/CSS optimized for AI parsing
- **JSON-LD Structured Data**: Instant AI comprehension
- **Auto-Tagging**: All interactions tagged with #comet-ai
- **Bidirectional Exchange**: Unified data exchange endpoint
- **Session Continuity**: Agent handoff with state preservation
- **Real-Time Streaming**: SSE for live updates

**Endpoints:**
- `GET /comet#` - AI-optimized portal interface
- `POST /comet#/auth` - Lightweight authentication
- `GET /comet#/context` - System context for AI
- `POST /comet#/exchange` - Unified data exchange
- `GET /comet#/stream` - SSE real-time updates

---

## 📊 MCP Tools Reference

### Active Tools (8 Total)

hAIveMind currently exposes 8 core MCP tools via FastMCP HTTP/SSE server:

| Tool | Category | Description |
|------|----------|-------------|
| `store_memory` | Memory | Store persistent knowledge with tags and categories |
| `retrieve_memory` | Memory | Get specific memory by ID |
| `search_memories` | Memory | Full-text and semantic search across memories |
| `get_recent_memories` | Memory | Retrieve memories within time window |
| `get_format_guide` | Format System | Get token-optimized format guide (compact or detailed) |
| `get_memory_access_stats` | Format System | View session access statistics |
| `broadcast_discovery` | Agent Coordination | Share findings with all network agents |
| `get_broadcasts` | Agent Coordination | Retrieve recent broadcast messages |

### Tool Categories

**Core Memory (4 tools)**
- Persistent storage with ChromaDB vector embeddings
- Full-text and semantic search
- Category-based organization
- Machine context tracking

**Token-Optimized Format System (2 tools)**
- Auto-teaches optimal compression format on first memory access
- Symbols: `→` (flow) `|` (or) `?` (opt) `!` (req) `::` (type)
- Tables > prose for structured data
- Reference pattern: `[ID]: define → use [ID]`
- Target: 60-80% token reduction vs verbose prose
- New memories tagged with `format_version: v2`

**Agent Coordination (2 tools)**
- Network-wide broadcasts
- Discovery sharing
- Real-time agent communication

---

## 🛠️ Configuration

### Primary Configuration File

`config/config.json` contains comprehensive configuration for all subsystems:

```json
{
  "server": {
    "name": "memory-server",
    "host": "0.0.0.0",
    "port": 8899
  },
  "storage": {
    "chromadb": {"path": "/data/chroma"},
    "redis": {"host": "localhost", "port": 6379}
  },
  "sync": {
    "enable_remote_sync": true,
    "sync_interval": 30,
    "discovery": {
      "tailscale_enabled": true,
      "machines": ["lance-dev", "elastic1", "elastic2"]
    }
  },
  "memory": {
    "categories": ["infrastructure", "incidents", "deployments"],
    "max_age_days": 365
  },
  "remote_server": {
    "enabled": true,
    "port": 8900
  },
  "mcp_hosting": {
    "enabled": true,
    "max_servers": 10
  },
  "comet": {
    "enabled": true,
    "authentication": {"password": "your-secure-password"}
  }
}
```

### Environment Variables

```bash
# JWT secret for authentication
export HAIVEMIND_JWT_SECRET="your-secret-key"

# Admin API token
export HAIVEMIND_ADMIN_TOKEN="your-admin-token"

# Confluence/Jira tokens
export CONFLUENCE_API_TOKEN="your-confluence-token"
export JIRA_API_TOKEN="your-jira-token"
```

### Machine Groups

Define machine groups in `config.json` for specialized capabilities:

```json
{
  "memory": {
    "machine_groups": {
      "orchestrators": ["lance-dev"],
      "elasticsearch": ["elastic1", "elastic2", "elastic3"],
      "databases": ["mysql", "mongodb", "kafka"],
      "scrapers": ["proxy0", "proxy1", "telegram-scraper"],
      "monitoring": ["grafana", "auth-server"]
    }
  }
}
```

---

## 🚀 Usage Examples

### Example 1: Store and Search Memories (Token-Optimized v2)

```python
# Store infrastructure knowledge using v2 format conventions
# Format: Tables > prose, use symbols → | ? ! ::
store_memory(
    content="""ES Requirements:
| Node | RAM | Heap | Disk |
| data | 32GB | 16GB | 1TB |
| master | 8GB | 4GB | 100GB |
Config: cluster.name → ES_CLUSTER_NAME
        discovery.type → multi-node""",
    category="infrastructure",
    tags=["elasticsearch", "memory", "requirements"],
    importance=8
)
# Note: Memory will be tagged with format_version: v2 automatically

# Search across collective memory
results = search_memories(
    query="elasticsearch memory requirements",
    category="infrastructure",
    limit=10
)

# Get format guide for optimal memory storage
get_format_guide(detailed=True)  # Returns full format reference

# Check session access statistics
get_memory_access_stats()  # Returns session usage stats
```

### Example 2: Agent Coordination

```python
# Register as specialized agent
register_agent(
    role="elasticsearch_specialist",
    description="Elasticsearch cluster management expert",
    capabilities=["elasticsearch_ops", "cluster_management"]
)

# Delegate task to specialist
delegate_task(
    task_description="Optimize Elasticsearch query performance",
    required_capabilities=["elasticsearch_ops"],
    priority="high"
)

# Broadcast important discovery
broadcast_discovery(
    message="Found memory leak in scraper service",
    category="infrastructure",
    severity="warning"
)
```

### Example 3: Configuration Management

```python
# Create configuration snapshot
create_config_snapshot(
    system_id="elastic1",
    config_type="elasticsearch",
    config_content=yaml_content,
    file_path="/etc/elasticsearch/elasticsearch.yml"
)

# Detect configuration drift
drift = detect_config_drift(
    system_id="elastic1",
    threshold=0.8
)

# Create alert for changes
create_config_alert(
    system_id="elastic1",
    alert_type="drift",
    threshold=0.7,
    notification_channels=["slack", "email"]
)
```

### Example 4: Playbook Automation

```python
# Auto-generate playbook from successful operations
analyze_patterns(
    category="deployments",
    time_window_hours=168,  # Last week
    min_frequency=3
)

# Execute generated playbook
execute_playbook(
    playbook_id="deploy-elasticsearch-cluster",
    environment="production",
    parameters={"cluster_size": 5}
)

# Get execution status
get_execution_status(execution_id="exec-123")
```

### Example 5: Backup & Recovery

```python
# Create full system backup
create_full_backup(
    backup_type="full",
    include_history=True,
    compression="gzip"
)

# Verify backup integrity
verify_backup(backup_id="backup-123")

# Rotate old backups
rotate_backups(
    retention_days=90,
    keep_count=10
)

# Archive to S3
archive_backup_to_s3(
    backup_id="backup-123",
    bucket="haivemind-backups",
    prefix="production/"
)
```

---

## 📈 Production Deployment

### System Requirements

- **OS**: Linux (Ubuntu 20.04+ recommended)
- **Python**: 3.9+
- **Redis**: 6.0+
- **PostgreSQL**: 13+ (for credential vault)
- **RAM**: 4GB minimum, 16GB recommended
- **Storage**: 50GB minimum for ChromaDB

### Systemd Services

Install as system services:

```bash
# Install all services
sudo bash services/install-services.sh

# Enable on boot
sudo systemctl enable haivemind-mcp
sudo systemctl enable haivemind-sync
sudo systemctl enable haivemind-dashboard

# Start services
sudo systemctl start haivemind-mcp
sudo systemctl start haivemind-sync
sudo systemctl start haivemind-dashboard

# Check status
sudo systemctl status haivemind-*
```

### Docker Deployment

```bash
# Build images
docker-compose -f docker-compose.vault.yml build

# Start all services
docker-compose -f docker-compose.vault.yml up -d

# View logs
docker-compose logs -f
```

### Monitoring

- **Health Endpoints**:
  - MCP Server: `http://localhost:8900/health`
  - Sync Service: `http://localhost:8899/api/status`
  - Dashboard: `http://localhost:8901/health`

- **Metrics Collection**: Prometheus metrics at `/metrics` endpoint
- **Log Aggregation**: Logs in `logs/` directory and systemd journal
- **Alerting**: Configure alerts in `config/config.json`

### Security Hardening

1. **Enable TLS/SSL**: Configure certificates in `config.json`
2. **JWT Authentication**: Set strong JWT secret
3. **IP Whitelisting**: Restrict access by IP
4. **Rate Limiting**: Configure in security section
5. **Audit Logging**: Enable comprehensive audit trail
6. **Network Isolation**: Use Tailscale VPN for inter-machine communication

---

## 📚 Documentation

### Core Documentation
- **[CLAUDE.md](CLAUDE.md)** - Complete system guide for AI agents
- **[MCP_INTEGRATION.md](MCP_INTEGRATION.md)** - MCP client integration guide
- **[STARTUP_GUIDE.md](STARTUP_GUIDE.md)** - Quick start for new deployments
- **[REMOTE_SETUP.md](REMOTE_SETUP.md)** - Remote machine configuration

### Subsystem Documentation
- **[RULES_ENGINE_DESIGN.md](RULES_ENGINE_DESIGN.md)** - Rules engine architecture
- **[WORKFLOW_AUTOMATION_GUIDE.md](WORKFLOW_AUTOMATION_GUIDE.md)** - Workflow system guide
- **[CONFLUENCE_INTEGRATION.md](CONFLUENCE_INTEGRATION.md)** - Confluence setup
- **[VAULT_DASHBOARD_IMPLEMENTATION_SUMMARY.md](VAULT_DASHBOARD_IMPLEMENTATION_SUMMARY.md)** - Credential vault guide

### Implementation Stories
- **[STORY_8A_IMPLEMENTATION_SUMMARY.md](STORY_8A_IMPLEMENTATION_SUMMARY.md)** - Vault API
- **[STORY_8B_IMPLEMENTATION_SUMMARY.md](STORY_8B_IMPLEMENTATION_SUMMARY.md)** - Vault database & encryption
- **[STORY_7C_IMPLEMENTATION_SUMMARY.md](STORY_7C_IMPLEMENTATION_SUMMARY.md)** - Advanced execution
- **[STORY_7B_IMPLEMENTATION_SUMMARY.md](STORY_7B_IMPLEMENTATION_SUMMARY.md)** - Playbook auto-generation

---

## 🧪 Testing

### Run Test Suite

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest tests/ -v

# Run specific test suites
pytest tests/test_memory_storage.py -v
pytest tests/test_enhanced_memory.py -v
pytest tests/test_vault_comprehensive.py -v
pytest tests/test_deletion_lifecycle.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Manual Testing

```bash
# Test MCP server
curl http://localhost:8900/health

# Test memory operations
python -c "
from src.remote_mcp_server import RemoteMCPServer
server = RemoteMCPServer()
print('Server initialized successfully')
"

# Test sync service
curl -X POST http://localhost:8899/api/trigger-sync \
  -H "Authorization: Bearer $HAIVEMIND_ADMIN_TOKEN"
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Add tests**: Ensure new functionality is tested
4. **Update documentation**: Add docs for new features
5. **Follow code style**: Use Black formatter and type hints
6. **Submit pull request**: Provide clear description of changes

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/haivemind-mcp-server.git
cd haivemind-mcp-server

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install pytest black mypy flake8

# Run pre-commit checks
black src/ tests/
mypy src/
flake8 src/ tests/
pytest tests/
```

---

## 🎯 Roadmap

### Version 2.1 (Q1 2025)
- [ ] Enhanced ML-based anomaly detection
- [ ] GraphQL API for complex queries
- [ ] Multi-region synchronization
- [ ] Advanced workflow visual designer
- [ ] Mobile dashboard application

### Version 2.2 (Q2 2025)
- [ ] Quantum-resistant encryption support
- [ ] Blockchain-based audit trails
- [ ] Advanced compliance reporting
- [ ] Horizontal scaling support
- [ ] Global CDN for distributed deployments

### Version 3.0 (Q3 2025)
- [ ] Multi-tenant architecture
- [ ] Advanced AI/ML integration
- [ ] Real-time collaborative editing
- [ ] Plugin marketplace
- [ ] Enterprise SSO integration

---

## 📞 Support

### Getting Help

- **GitHub Issues**: [Report bugs or request features](https://github.com/lancejames221b/haivemind-mcp-server/issues)
- **Documentation**: Comprehensive guides in `docs/` directory
- **Examples**: Working configurations in `examples/` directory

### Troubleshooting

**MCP Connection Issues:**
```bash
# Check service status
curl http://localhost:8900/health

# Verify Redis connection
redis-cli ping

# Check logs
journalctl -u haivemind-mcp -f
```

**Memory Sync Issues:**
```bash
# Check sync service
curl http://localhost:8899/api/status

# Trigger manual sync
curl -X POST http://localhost:8899/api/trigger-sync

# Verify Tailscale connectivity
ping lance-dev && ping elastic1
```

**Performance Issues:**
```bash
# Check ChromaDB size
du -sh data/chroma/

# Clear Redis cache
redis-cli FLUSHDB

# Optimize database
sqlite3 database/rules.db "VACUUM;"
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Lance James, Unit 221B, Inc

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Redis](https://redis.io/) - In-memory data store
- [MCP Protocol](https://modelcontextprotocol.io/) - Model Context Protocol
- [Tailscale](https://tailscale.com/) - Secure networking

---

## 📊 Statistics

- **Lines of Code**: 94 Python source files
- **MCP Tools**: 8 active tools (Memory + Format System + Agent Coordination)
- **Test Coverage**: Comprehensive test suites
- **Documentation**: 20+ detailed guides
- **Machine Groups**: 7 specialized groups
- **Network Machines**: 25+ production machines
- **Memory Categories**: 14 specialized categories
- **Storage**: ChromaDB (vectors) + Redis (cache) + SQLite (metadata)
- **Token Optimization**: v2 format system - 60-80% token reduction

---

**hAIveMind** - Enabling distributed AI coordination for the future of DevOps automation.

Built with ❤️ by Lance James, Unit 221B, Inc
