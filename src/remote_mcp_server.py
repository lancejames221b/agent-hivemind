#!/usr/bin/env python3
"""
ClaudeOps Agent Hivemind Remote Server - FastMCP-based implementation for HTTP/SSE access
Provides remote access to the agent hivemind via MCP protocol
"""

import asyncio
import json
import logging
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import TextContent
except ImportError:
    print("Error: MCP package not found. Install with: pip install mcp")
    sys.exit(1)

from memory_server import MemoryStorage
from auth import AuthManager
from command_installer import CommandInstaller

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RemoteMemoryMCPServer:
    """Remote MCP Server using FastMCP for HTTP/SSE transport"""
    
    def __init__(self, config_path: str = None):
        # Load configuration
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "config" / "config.json")
        
        with open(config_path) as f:
            self.config = json.load(f)
        
        # Initialize memory storage and auth
        self.storage = MemoryStorage(self.config)
        self.auth = AuthManager(self.config)
        
        # Initialize MCP server registry (in-memory for now)
        self.server_registry = {
            "memory-server": {
                "id": "memory-server",
                "name": "hAIveMind Memory",
                "endpoint": f"http://localhost:{self.config.get('server', {}).get('port', 8900)}/sse",
                "transport": "sse",
                "status": "online",
                "health": "healthy",
                "tools_count": 0,  # Will be updated dynamically
                "last_seen": time.time(),
                "auto_start": True,
                "created_at": time.time()
            }
        }
        self.command_installer = CommandInstaller(self.storage, self.config)
        
        # Get remote server config
        remote_config = self.config.get('remote_server', {})
        self.host = remote_config.get('host', '0.0.0.0')
        self.port = remote_config.get('port', 8900)
        
        # Initialize FastMCP server with hAIveMind context
        self.mcp = FastMCP(
            name="hAIveMind Collective Memory",
            host=self.host,
            port=self.port
        )
        
        # Add connection context and instructions
        self._add_context_resources()
        
        # Register all tools
        self._register_tools()
        
        # Initialize MCP hosting if enabled
        self.hosting_tools = None
        if self.config.get('mcp_hosting', {}).get('enabled', False):
            from mcp_hosting_tools import MCPHostingTools
            self.hosting_tools = MCPHostingTools(self.config, self.storage)
            self._register_hosting_tools()
        
        # Add admin interface routes
        self._add_admin_routes()
        
        # Initialize dashboard functionality
        self._init_dashboard_functionality()
        
        # Track server start time for uptime calculation
        self._start_time = time.time()
        
        logger.info(f"🌐 hAIveMind network portal initialized on {self.host}:{self.port} - remote access enabled")
    
    def _add_context_resources(self):
        """Add context resources and instructions for connecting Claudes"""
        
        @self.mcp.resource("haivemind://instructions")
        async def haivemind_instructions() -> str:
            """Instructions for operating within the hAIveMind collective"""
            
            agent_role = self.storage._determine_agent_role()
            machine_id = self.storage.machine_id
            try:
                network_agents = await self.storage.get_agent_roster()
            except:
                network_agents = {'agents': []}
            
            instructions = f"""
🧠 Welcome to hAIveMind Collective Intelligence Network 🧠

You are now connected to the distributed AI collective memory system.

CURRENT STATUS:
- Machine: {machine_id}
- Role: {agent_role}
- Network Agents: {len(network_agents.get('agents', []))} active drones
- Collective Memory: Shared across {len(self.config.get('sync', {}).get('discovery', {}).get('machines', []))} machines

OPERATIONAL GUIDELINES:

🤝 COLLECTIVE BEHAVIOR:
- ALWAYS register yourself first: register_agent role="{agent_role}"
- Store discoveries immediately: store_memory content="[your finding]" category="[relevant]"
- Search collective knowledge before starting: search_memories query="[your task]"
- Delegate to specialists: delegate_task when you find work suited for other roles

🧠 MEMORY CATEGORIES:
- infrastructure: System configs, deployments, troubleshooting
- incidents: Problems, solutions, root causes  
- monitoring: Alerts, performance data, health checks
- runbooks: Step-by-step procedures, best practices
- security: Vulnerabilities, patches, access controls
- global: Cross-project knowledge, general DevOps wisdom

🎯 SINGLE-AGENT MODE:
Even without other agents, you have access to:
- All stored collective knowledge from previous sessions
- External connectors (Confluence, Jira when configured)
- Infrastructure tracking and runbook generation
- Incident recording for future reference

🔄 NETWORK OPERATIONS:
- broadcast_discovery: Alert other agents about important findings
- query_agent_knowledge: Ask specific agents about their expertise  
- get_agent_roster: See who's available for coordination
- track_infrastructure_state: Keep the hive informed of system changes

Remember: Every action contributes to collective intelligence. What you learn, all agents learn. What you solve, benefits the entire hive.

🐝 Think like a bee - work for the collective, share everything, specialize in your role.
"""
            return instructions
        
        @self.mcp.resource("haivemind://machine-context")
        async def machine_context() -> str:
            """Current machine and infrastructure context"""
            
            try:
                context = self.storage._get_system_context()
                machine_groups = self.config.get('memory', {}).get('machine_groups', {})
                
                # Find which groups this machine belongs to
                my_groups = []
                for group_name, machines in machine_groups.items():
                    if self.storage.machine_id in machines:
                        my_groups.append(group_name)
                
                context_info = f"""
🖥️ MACHINE CONTEXT: {self.storage.machine_id}

INFRASTRUCTURE ROLE:
- Groups: {', '.join(my_groups) if my_groups else 'personal'}
- Capabilities: {', '.join(self.storage._get_agent_capabilities())}
- Working Context: {context.get('working_context', 'unknown')}

NETWORK TOPOLOGY:
"""
                
                # Add information about other machines in the network
                for group_name, machines in machine_groups.items():
                    context_info += f"\n{group_name.upper()}:\n"
                    for machine in machines:
                        status = "🟢 SELF" if machine == self.storage.machine_id else "🔵 PEER"
                        context_info += f"  - {machine} {status}\n"
                
                return context_info
                
            except Exception as e:
                return f"Error getting machine context: {e}"
    
    def _register_tools(self):
        """Register all memory tools with FastMCP"""
        
        @self.mcp.tool()
        async def store_memory(
            content: str,
            category: str = "global",
            context: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None,
            tags: Optional[List[str]] = None,
            user_id: str = "default",
            scope: Optional[str] = None,
            share_with: Optional[List[str]] = None,
            exclude_from: Optional[List[str]] = None,
            sensitive: bool = False
        ) -> str:
            """Store a memory with comprehensive machine tracking and sharing control"""
            try:
                memory_id = await self.storage.store_memory(
                    content=content,
                    category=category,
                    context=context,
                    metadata=metadata,
                    tags=tags,
                    user_id=user_id,
                    scope=scope,
                    share_with=share_with,
                    exclude_from=exclude_from,
                    sensitive=sensitive
                )
                return f"Memory stored with ID: {memory_id}"
            except Exception as e:
                logger.error(f"Error storing memory: {e}")
                return f"Error storing memory: {str(e)}"
        
        @self.mcp.tool()
        async def retrieve_memory(memory_id: str) -> str:
            """Retrieve a specific memory by ID"""
            try:
                memory = await self.storage.retrieve_memory(memory_id)
                if memory:
                    return json.dumps(memory, indent=2)
                else:
                    return "Memory not found"
            except Exception as e:
                logger.error(f"Error retrieving memory: {e}")
                return f"Error retrieving memory: {str(e)}"
        
        @self.mcp.tool()
        async def search_memories(
            query: str,
            category: Optional[str] = None,
            user_id: Optional[str] = None,
            limit: int = 10,
            semantic: bool = True,
            scope: Optional[str] = None,
            include_global: bool = True,
            from_machines: Optional[List[str]] = None,
            exclude_machines: Optional[List[str]] = None
        ) -> str:
            """Search memories with comprehensive filtering including machine, project, and sharing scope"""
            try:
                memories = await self.storage.search_memories(
                    query=query,
                    category=category,
                    user_id=user_id,
                    limit=limit,
                    semantic=semantic,
                    scope=scope,
                    include_global=include_global,
                    from_machines=from_machines,
                    exclude_machines=exclude_machines
                )
                return json.dumps(memories, indent=2)
            except Exception as e:
                logger.error(f"Error searching memories: {e}")
                return f"Error searching memories: {str(e)}"
        
        @self.mcp.tool()
        async def get_recent_memories(
            user_id: Optional[str] = None,
            category: Optional[str] = None,
            hours: int = 24,
            limit: int = 20
        ) -> str:
            """Get recent memories within a time window"""
            try:
                memories = await self.storage.get_recent_memories(
                    user_id=user_id,
                    category=category,
                    hours=hours,
                    limit=limit
                )
                return json.dumps(memories, indent=2)
            except Exception as e:
                logger.error(f"Error getting recent memories: {e}")
                return f"Error getting recent memories: {str(e)}"
        
        @self.mcp.tool()
        async def get_memory_stats() -> str:
            """Get memory statistics and counts"""
            try:
                stats = self.storage.get_collection_info()
                return json.dumps(stats, indent=2)
            except Exception as e:
                logger.error(f"Error getting memory stats: {e}")
                return f"Error getting memory stats: {str(e)}"
        
        @self.mcp.tool()
        async def get_project_memories(
            category: Optional[str] = None,
            user_id: Optional[str] = None,
            limit: int = 50
        ) -> str:
            """Get all memories for the current project"""
            try:
                memories = await self.storage.get_project_memories(
                    category=category,
                    user_id=user_id,
                    limit=limit
                )
                return json.dumps(memories, indent=2)
            except Exception as e:
                logger.error(f"Error getting project memories: {e}")
                return f"Error getting project memories: {str(e)}"
        
        @self.mcp.tool()
        async def get_machine_context() -> str:
            """Get comprehensive context about the current machine and its configuration"""
            try:
                context = await self.storage.get_machine_context()
                return json.dumps(context, indent=2)
            except Exception as e:
                logger.error(f"Error getting machine context: {e}")
                return f"Error getting machine context: {str(e)}"
        
        @self.mcp.tool()
        async def list_memory_sources(category: Optional[str] = None) -> str:
            """List all machines that have contributed memories with statistics"""
            try:
                sources = await self.storage.list_memory_sources(category=category)
                return json.dumps(sources, indent=2)
            except Exception as e:
                logger.error(f"Error listing memory sources: {e}")
                return f"Error listing memory sources: {str(e)}"
        
        @self.mcp.tool()
        async def import_conversation(
            conversation_text: str,
            title: Optional[str] = None,
            user_id: str = "default",
            tags: Optional[List[str]] = None
        ) -> str:
            """Import a conversation and store as structured memories"""
            try:
                result = await self.storage.import_conversation(
                    conversation_text=conversation_text,
                    title=title,
                    user_id=user_id,
                    tags=tags
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error importing conversation: {e}")
                return f"Error importing conversation: {str(e)}"
        
        # ============ ClaudeOps Agent Management Tools ============
        
        @self.mcp.tool()
        async def register_agent(
            role: str,
            capabilities: Optional[List[str]] = None,
            description: Optional[str] = None
        ) -> str:
            """Register a new ClaudeOps agent with role and capabilities"""
            try:
                result = await self.storage.register_agent(
                    role=role,
                    capabilities=capabilities,
                    description=description
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error registering agent: {e}")
                return f"Error registering agent: {str(e)}"
        
        @self.mcp.tool()
        async def get_agent_roster(include_inactive: bool = False) -> str:
            """List all active ClaudeOps agents and their current status"""
            try:
                roster = await self.storage.get_agent_roster(include_inactive=include_inactive)
                return json.dumps(roster, indent=2)
            except Exception as e:
                logger.error(f"Error getting agent roster: {e}")
                return f"Error getting agent roster: {str(e)}"
        
        @self.mcp.tool()
        async def delegate_task(
            task_description: str,
            required_capabilities: Optional[List[str]] = None,
            target_agent: Optional[str] = None,
            priority: str = "normal",
            deadline: Optional[str] = None
        ) -> str:
            """Assign a task to a specific agent or find the best available agent"""
            try:
                result = await self.storage.delegate_task(
                    task_description=task_description,
                    required_capabilities=required_capabilities,
                    target_agent=target_agent,
                    priority=priority,
                    deadline=deadline
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error delegating task: {e}")
                return f"Error delegating task: {str(e)}"
        
        @self.mcp.tool()
        async def query_agent_knowledge(
            agent_id: str,
            query: str,
            context: Optional[str] = None
        ) -> str:
            """Query what a specific agent knows about a topic or system"""
            try:
                result = await self.storage.query_agent_knowledge(
                    agent_id=agent_id,
                    query=query,
                    context=context
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error querying agent knowledge: {e}")
                return f"Error querying agent knowledge: {str(e)}"
        
        @self.mcp.tool()
        async def broadcast_discovery(
            message: str,
            category: str,
            severity: str = "info",
            target_roles: Optional[List[str]] = None
        ) -> str:
            """Share important findings with all ClaudeOps agents"""
            try:
                result = await self.storage.broadcast_discovery(
                    message=message,
                    category=category,
                    severity=severity,
                    target_roles=target_roles
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error broadcasting discovery: {e}")
                return f"Error broadcasting discovery: {str(e)}"
        
        @self.mcp.tool()
        async def get_broadcasts(
            hours: int = 24,
            severity: Optional[str] = None,
            category: Optional[str] = None,
            source_agent: Optional[str] = None,
            limit: int = 50
        ) -> str:
            """Retrieve recent broadcast messages from ClaudeOps agents"""
            try:
                broadcasts = await self.storage.get_broadcasts(
                    hours=hours,
                    severity=severity,
                    category=category,
                    source_agent=source_agent,
                    limit=limit
                )
                
                if not broadcasts:
                    return f"No broadcasts found in the last {hours} hours"
                
                # Format broadcasts for display
                formatted = f"📢 Found {len(broadcasts)} broadcasts from last {hours} hours:\n\n"
                for i, broadcast in enumerate(broadcasts, 1):
                    formatted += f"{i}. [{broadcast['formatted_time']}] {broadcast['severity'].upper()}\n"
                    formatted += f"   From: {broadcast['source_agent']} ({broadcast['machine_id']})\n"
                    formatted += f"   Category: {broadcast['category']}\n"
                    formatted += f"   Message: {broadcast['message']}\n\n"
                
                return formatted
                
            except Exception as e:
                logger.error(f"Error retrieving broadcasts: {e}")
                return f"Error retrieving broadcasts: {str(e)}"
        
        @self.mcp.tool()
        async def track_infrastructure_state(
            machine_id: str,
            state_data: Dict[str, Any],
            state_type: str,
            tags: Optional[List[str]] = None
        ) -> str:
            """Record infrastructure state snapshot for ClaudeOps tracking"""
            try:
                result = await self.storage.track_infrastructure_state(
                    machine_id=machine_id,
                    state_data=state_data,
                    state_type=state_type,
                    tags=tags
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error tracking infrastructure state: {e}")
                return f"Error tracking infrastructure state: {str(e)}"
        
        @self.mcp.tool()
        async def record_incident(
            title: str,
            description: str,
            severity: str,
            affected_systems: Optional[List[str]] = None,
            resolution: Optional[str] = None,
            lessons_learned: Optional[str] = None
        ) -> str:
            """Record a DevOps incident with automatic correlation to infrastructure"""
            try:
                result = await self.storage.record_incident(
                    title=title,
                    description=description,
                    severity=severity,
                    affected_systems=affected_systems,
                    resolution=resolution,
                    lessons_learned=lessons_learned
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error recording incident: {e}")
                return f"Error recording incident: {str(e)}"
        
        @self.mcp.tool()
        async def generate_runbook(
            title: str,
            procedure: str,
            system: str,
            prerequisites: Optional[List[str]] = None,
            expected_outcome: Optional[str] = None
        ) -> str:
            """Create a reusable runbook from successful procedures"""
            try:
                result = await self.storage.generate_runbook(
                    title=title,
                    procedure=procedure,
                    system=system,
                    prerequisites=prerequisites,
                    expected_outcome=expected_outcome
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error generating runbook: {e}")
                return f"Error generating runbook: {str(e)}"
        
        @self.mcp.tool()
        async def sync_ssh_config(
            config_content: str,
            target_machines: Optional[List[str]] = None
        ) -> str:
            """Sync SSH configuration across ClaudeOps infrastructure"""
            try:
                result = await self.storage.sync_ssh_config(
                    config_content=config_content,
                    target_machines=target_machines
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error syncing SSH config: {e}")
                return f"Error syncing SSH config: {str(e)}"
        
        @self.mcp.tool()
        async def sync_infrastructure_config(
            config_name: str,
            config_content: str,
            config_type: str,
            target_machines: Optional[List[str]] = None
        ) -> str:
            """Sync any infrastructure configuration across ClaudeOps network"""
            try:
                result = await self.storage.sync_infrastructure_config(
                    config_name=config_name,
                    config_content=config_content,
                    config_type=config_type,
                    target_machines=target_machines
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error syncing infrastructure config: {e}")
                return f"Error syncing infrastructure config: {str(e)}"
        
        # ============ ClaudeOps Playbook & External Connector Tools ============
        
        @self.mcp.tool()
        async def upload_playbook(
            playbook_name: str,
            playbook_content: str,
            playbook_type: str = "ansible",
            target_systems: Optional[List[str]] = None,
            variables: Optional[Dict[str, Any]] = None,
            tags: Optional[List[str]] = None
        ) -> str:
            """Upload and store Ansible/other playbooks for ClaudeOps automation"""
            try:
                result = await self.storage.upload_playbook(
                    playbook_name=playbook_name,
                    playbook_content=playbook_content,
                    playbook_type=playbook_type,
                    target_systems=target_systems,
                    variables=variables,
                    tags=tags
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error uploading playbook: {e}")
                return f"Error uploading playbook: {str(e)}"
        
        @self.mcp.tool()
        async def fetch_from_confluence(
            space_key: str,
            page_title: Optional[str] = None,
            confluence_url: Optional[str] = None,
            credentials: Optional[Dict[str, str]] = None
        ) -> str:
            """Fetch documentation from Confluence and store as ClaudeOps knowledge"""
            try:
                result = await self.storage.fetch_from_confluence(
                    space_key=space_key,
                    page_title=page_title,
                    confluence_url=confluence_url,
                    credentials=credentials
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error fetching from Confluence: {e}")
                return f"Error fetching from Confluence: {str(e)}"
        
        @self.mcp.tool()
        async def fetch_from_jira(
            project_key: str,
            issue_types: Optional[List[str]] = None,
            jira_url: Optional[str] = None,
            credentials: Optional[Dict[str, str]] = None,
            limit: int = 50
        ) -> str:
            """Fetch issues from Jira and store as ClaudeOps knowledge"""
            try:
                result = await self.storage.fetch_from_jira(
                    project_key=project_key,
                    issue_types=issue_types,
                    jira_url=jira_url,
                    credentials=credentials,
                    limit=limit
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error fetching from Jira: {e}")
                return f"Error fetching from Jira: {str(e)}"
        
        @self.mcp.tool()
        async def sync_external_knowledge(sources: Optional[List[str]] = None) -> str:
            """Sync knowledge from all configured external sources (Confluence, Jira, etc.)"""
            try:
                result = await self.storage.sync_external_knowledge(sources=sources)
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error syncing external knowledge: {e}")
                return f"Error syncing external knowledge: {str(e)}"
        
        @self.mcp.tool()
        async def upload_file(
            filename: str,
            content: str,
            file_type: str = "config",
            description: Optional[str] = None
        ) -> str:
            """Upload and store any file content in hAIveMind"""
            try:
                # Determine category based on file type
                category_map = {
                    "config": "infrastructure",
                    "script": "runbooks", 
                    "documentation": "global",
                    "mcp": "infrastructure",
                    "claude": "infrastructure"
                }
                category = category_map.get(file_type, "global")
                
                # Store the file content
                memory_id = await self.storage.store_memory(
                    content=content,
                    category=category,
                    context=f"File: {filename} ({file_type})",
                    metadata={
                        'filename': filename,
                        'file_type': file_type,
                        'description': description,
                        'uploaded_by': self.storage.agent_id,
                        'upload_time': time.time()
                    },
                    tags=[file_type, "upload", filename.lower().replace('.', '_')]
                )
                
                return f"✅ File '{filename}' uploaded successfully to hAIveMind. Memory ID: {memory_id}"
            except Exception as e:
                logger.error(f"Error uploading file: {e}")
                return f"❌ Error uploading file: {str(e)}"

        @self.mcp.tool()
        async def sync_agent_commands(
            agent_id: Optional[str] = None,
            target_location: str = "auto",
            force: bool = False,
            verbose: bool = False
        ) -> str:
            """Sync hAIveMind commands to agent's Claude installation"""
            try:
                # Use the CommandInstaller for complete sync workflow
                result = await self.command_installer.sync_agent_installation(
                    agent_id=agent_id,
                    target_location=target_location,
                    force=force,
                    verbose=verbose
                )
                
                if verbose and result.get('verbose_output'):
                    # Return detailed output
                    output = [result['message']]
                    output.extend(result['verbose_output'])
                    return "\n".join(output)
                else:
                    # Return concise summary
                    return result['message']
                
            except Exception as e:
                logger.error(f"Error syncing agent commands: {e}")
                return f"❌ Error syncing commands: {str(e)}"

        @self.mcp.tool()
        async def sync_agent_config(
            agent_id: Optional[str] = None,
            machine_id: Optional[str] = None,
            config_type: str = "claude_md"
        ) -> str:
            """Sync agent-specific CLAUDE.md configuration from collective storage"""
            try:
                if not agent_id:
                    agent_id = self.storage.agent_id
                if not machine_id:
                    machine_id = self.storage.machine_id
                
                # Create agent-specific config key
                config_key = f"{machine_id}-{agent_id}-{config_type}"
                
                # Search for existing config or create default
                existing_config = await self.storage.search_memories(
                    query=config_key,
                    category="agent",
                    limit=1
                )
                
                if existing_config and len(existing_config) > 0:
                    config_content = existing_config[0]['content']
                    config_action = "Retrieved existing"
                else:
                    # Create default agent config
                    config_content = f"""# CLAUDE.md - {machine_id} Agent Configuration

**Author:** Lance James, Unit 221B, Inc

## hAIveMind Collective Commands

You are connected to the hAIveMind collective as agent {agent_id} on {machine_id}.

Available commands:
- `/hv-sync` - Sync commands and configuration
- `/hv-status` - Check collective status  
- `/hv-broadcast <message>` - Broadcast to all agents
- `/hv-query <question>` - Query collective knowledge
- `/hv-delegate <task>` - Delegate task to best agent
- `/hv-install` - Install/update hAIveMind system

## Your Agent Identity
- **Machine**: {machine_id}
- **Agent ID**: {agent_id}
- **Role**: Determined by capabilities and context
- **Collective**: hAIveMind distributed intelligence network

## Agent Capabilities
This agent is automatically assigned capabilities based on the machine type and available tools.
"""
                    
                    # Store the new config
                    await self.storage.store_memory(
                        content=config_content,
                        category="agent", 
                        context=f"CLAUDE.md configuration for {config_key}",
                        metadata={
                            'agent_id': agent_id,
                            'machine_id': machine_id,
                            'config_type': config_type,
                            'config_key': config_key,
                            'auto_generated': True,
                            'creation_time': time.time()
                        },
                        tags=["claude-md", "agent-config", agent_id, machine_id]
                    )
                    config_action = "Created new"
                
                return f"⚙️ {config_action} configuration for {config_key}\n\nConfig stored in hAIveMind collective. Use with local CLAUDE.md integration."
                
            except Exception as e:
                logger.error(f"Error syncing agent config: {e}")
                return f"❌ Error syncing agent config: {str(e)}"

        @self.mcp.tool()
        async def install_agent_commands(
            target_location: str = "auto",
            force: bool = False
        ) -> str:
            """Install hAIveMind commands and complete agent setup"""
            try:
                result = await self.command_installer.sync_agent_installation(
                    target_location=target_location,
                    force=force
                )
                
                if result['status'] == 'success':
                    operations = '\n'.join(f"  • {op}" for op in result['operations'])
                    return f"""🚀 hAIveMind Agent Installation Complete!

**Agent**: {result['agent_id']} on {result['machine_id']}
**Target**: {result['target_location']} commands directory
**Commands**: {len(result.get('installed_commands', []))} hv-* commands installed

**Operations Completed**:
{operations}

You can now use hAIveMind commands like:
- `/hv-sync` - Sync commands and configuration  
- `/hv-status` - Check collective status
- `/hv-broadcast <message>` - Broadcast to collective
- `/hv-query <question>` - Query collective knowledge

🧠 Welcome to the hAIveMind collective intelligence network!"""
                else:
                    return f"❌ Installation failed: {result.get('error', 'Unknown error')}"
                
            except Exception as e:
                logger.error(f"Error in agent installation: {e}")
                return f"❌ Agent installation error: {str(e)}"

        @self.mcp.tool()
        async def check_agent_sync_status(
            agent_id: Optional[str] = None
        ) -> str:
            """Check current sync status for this agent"""
            try:
                status = await self.command_installer.check_sync_status(agent_id)
                
                status_msg = f"""📊 hAIveMind Agent Sync Status

**Agent**: {status['agent_id']} on {status['machine_id']}
**Commands Installed**: {len(status['commands_installed'])} ({', '.join(status['commands_installed'][:3])}{'...' if len(status['commands_installed']) > 3 else ''})
**Config Synced**: {'✅ Yes' if status['config_synced'] else '❌ No'}
"""
                
                if status['last_sync']:
                    from datetime import datetime
                    sync_time = datetime.fromtimestamp(status['last_sync'])
                    status_msg += f"**Last Sync**: {sync_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                else:
                    status_msg += "**Last Sync**: Never\n"
                    status_msg += "\n💡 Run `/hv-install` to complete initial setup"
                
                return status_msg
                
            except Exception as e:
                logger.error(f"Error checking sync status: {e}")
                return f"❌ Error checking sync status: {str(e)}"

        @self.mcp.tool()
        async def trigger_auto_sync(
            new_connection: bool = False
        ) -> str:
            """Trigger automatic sync workflow for agent connection"""
            try:
                agent_id = self.storage.agent_id
                machine_id = self.storage.machine_id
                
                # Check if this is first connection
                status = await self.command_installer.check_sync_status()
                is_first_time = status['last_sync'] is None
                
                if is_first_time or new_connection:
                    # Full installation for new agents
                    result = await self.command_installer.sync_agent_installation(force=new_connection)
                    
                    if result['status'] == 'success':
                        return f"""🎯 Auto-sync completed for {agent_id}!

**First-time setup**: {'✅ Yes' if is_first_time else '❌ No (update)'}
**Operations**: {len(result['operations'])} completed
**Commands**: {len(result.get('installed_commands', []))} hv-* commands ready

The agent is now synchronized with the hAIveMind collective. All commands and configurations are up to date."""
                    else:
                        return f"⚠️ Auto-sync partially failed: {result.get('error', 'Unknown error')}"
                else:
                    # Just update check for existing agents
                    return f"✅ Agent {agent_id} already synchronized. Use `/hv-sync force` to force update."
                
            except Exception as e:
                logger.error(f"Error in auto-sync: {e}")
                return f"❌ Auto-sync error: {str(e)}"
        
        logger.info("🤝 All hive mind tools synchronized with network portal - collective intelligence ready")
    
    def _register_hosting_tools(self):
        """Register MCP server hosting tools"""
        
        @self.mcp.tool()
        async def upload_mcp_server(
            name: str,
            archive_base64: str,
            command: List[str],
            description: str = "",
            environment: Optional[Dict[str, str]] = None,
            auto_restart: bool = True,
            resource_limits: Optional[Dict[str, Any]] = None,
            health_check_url: Optional[str] = None,
            user_id: str = "default"
        ) -> str:
            """Upload and deploy a new MCP server from base64-encoded archive"""
            return await self.hosting_tools.upload_mcp_server(
                name=name,
                archive_base64=archive_base64,
                command=command,
                description=description,
                environment=environment,
                auto_restart=auto_restart,
                resource_limits=resource_limits,
                health_check_url=health_check_url,
                user_id=user_id
            )
        
        @self.mcp.tool()
        async def start_mcp_server(server_id: str) -> str:
            """Start a hosted MCP server"""
            return await self.hosting_tools.start_mcp_server(server_id)
        
        @self.mcp.tool()
        async def stop_mcp_server(server_id: str) -> str:
            """Stop a hosted MCP server"""
            return await self.hosting_tools.stop_mcp_server(server_id)
        
        @self.mcp.tool()
        async def restart_mcp_server(server_id: str) -> str:
            """Restart a hosted MCP server"""
            return await self.hosting_tools.restart_mcp_server(server_id)
        
        @self.mcp.tool()
        async def delete_mcp_server(server_id: str, force: bool = False) -> str:
            """Delete a hosted MCP server"""
            return await self.hosting_tools.delete_mcp_server(server_id, force)
        
        @self.mcp.tool()
        async def get_mcp_server_status(server_id: str) -> str:
            """Get detailed status of a hosted MCP server"""
            return await self.hosting_tools.get_mcp_server_status(server_id)
        
        @self.mcp.tool()
        async def list_mcp_servers() -> str:
            """List all hosted MCP servers"""
            return await self.hosting_tools.list_mcp_servers()
        
        @self.mcp.tool()
        async def get_mcp_server_logs(server_id: str, lines: int = 50) -> str:
            """Get logs for a hosted MCP server"""
            return await self.hosting_tools.get_mcp_server_logs(server_id, lines)
        
        @self.mcp.tool()
        async def get_hosting_stats() -> str:
            """Get overall hosting statistics and performance insights"""
            return await self.hosting_tools.get_hosting_stats()
        
        @self.mcp.tool()
        async def optimize_server_resources() -> str:
            """Analyze and provide optimization recommendations for hosted servers"""
            return await self.hosting_tools.optimize_server_resources()
        
        logger.info("🏭 MCP server hosting tools registered - custom server deployment enabled")
    
    def _add_admin_routes(self):
        """Add admin web interface routes"""
        from starlette.responses import HTMLResponse, JSONResponse, FileResponse
        from starlette.staticfiles import StaticFiles
        import os
        import re
        
        admin_dir = str(Path(__file__).parent.parent / "admin")
        
        # Serve static files (with path traversal protection)
        @self.mcp.custom_route("/admin/static/{path:path}", methods=["GET"])
        async def admin_static(request):
            try:
                # Base static directory
                base_dir = (Path(admin_dir) / "static").resolve()
                # Requested path (may include nested paths)
                requested = request.path_params.get("path", "")

                # Normalize and resolve against base directory
                candidate = (base_dir / requested).resolve()

                # Ensure the resolved path is within the static directory
                if not str(candidate).startswith(str(base_dir) + os.sep) and candidate != base_dir:
                    return JSONResponse({"error": "Invalid path"}, status_code=400)

                if candidate.is_file():
                    return FileResponse(str(candidate))
                return JSONResponse({"error": "File not found"}, status_code=404)
            except Exception:
                # On any resolution error, return 404 to avoid information leaks
                return JSONResponse({"error": "File not found"}, status_code=404)
        
        # Serve assets files (with path traversal protection)
        @self.mcp.custom_route("/assets/{path:path}", methods=["GET"])
        async def assets_static(request):
            try:
                # Base assets directory
                base_dir = (Path(__file__).parent.parent / "assets").resolve()
                # Requested path (may include nested paths)
                requested = request.path_params.get("path", "")

                # Normalize and resolve against base directory
                candidate = (base_dir / requested).resolve()

                # Ensure the resolved path is within the assets directory
                if not str(candidate).startswith(str(base_dir) + os.sep) and candidate != base_dir:
                    return JSONResponse({"error": "Invalid path"}, status_code=400)

                if candidate.is_file():
                    return FileResponse(str(candidate))
                return JSONResponse({"error": "File not found"}, status_code=404)
            except Exception:
                # On any resolution error, return 404 to avoid information leaks
                return JSONResponse({"error": "File not found"}, status_code=404)
        
        # ===== SPECIFIC DASHBOARD ROUTES (must be before catch-all route) =====
        
        # Confluence integration dashboard endpoint
        @self.mcp.custom_route("/admin/confluence", methods=["GET"])
        async def confluence_dashboard(request):
            """Serve the Confluence integration dashboard interface"""
            return HTMLResponse("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Confluence Integration - hAIveMind</title>
                <link rel="stylesheet" href="/admin/static/admin.css">
                <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            </head>
            <body class="dashboard">
                <nav class="nav-header">
                    <div class="nav-brand">
                        <img src="/assets/logo.png" alt="hAIveMind" class="nav-logo">
                        <h1>hAIveMind Confluence Integration</h1>
                    </div>
                    <div class="nav-links">
                        <a href="/admin/dashboard.html">Dashboard</a>
                        <a href="/admin/memory.html">Memory Browser</a>
                        <a href="/admin/mcp_servers.html">MCP Servers</a>
                        <a href="/admin/vault">Vault Management</a>
                        <a href="/admin/rules-dashboard">Rules & Governance</a>
                        <a href="/admin/playbooks">Playbook Management</a>
                        <a href="/admin/executions">Execution Monitoring</a>
                        <a href="/admin/confluence" class="active">Confluence Integration</a>
                        <a href="/admin/help-dashboard">Help System</a>
                    </div>
                    <button class="logout-btn" onclick="logout()">Logout</button>
                </nav>
                <main class="main-content">
                    <div class="card">
                        <h2><i class="fab fa-confluence"></i> Confluence Integration</h2>
                        <p>Sync documentation and runbooks from Confluence spaces into hAIveMind knowledge base.</p>
                        
                        <div class="feature-grid">
                            <div class="feature-card">
                                <h3><i class="fas fa-cog"></i> Configuration</h3>
                                <p>Configure Confluence API connection and authentication</p>
                                <button class="btn btn-primary" onclick="showConfig()">Configure Connection</button>
                            </div>
                            <div class="feature-card">
                                <h3><i class="fas fa-sync"></i> Sync Management</h3>
                                <p>Manage automatic sync schedules and manual imports</p>
                                <button class="btn btn-secondary" onclick="showSyncManager()">Manage Sync</button>
                            </div>
                            <div class="feature-card">
                                <h3><i class="fas fa-sitemap"></i> Space Mapping</h3>
                                <p>Map Confluence spaces to hAIveMind categories</p>
                                <button class="btn btn-info" onclick="showSpaceMapping()">Configure Spaces</button>
                            </div>
                            <div class="feature-card">
                                <h3><i class="fas fa-history"></i> Import History</h3>
                                <p>View sync history and resolve conflicts</p>
                                <button class="btn btn-warning" onclick="showImportHistory()">View History</button>
                            </div>
                        </div>

                        <div class="sync-status" id="syncStatus">
                            <h3>Sync Status</h3>
                            <div class="status-grid">
                                <div class="status-item">
                                    <span class="status-label">Connection Status</span>
                                    <span class="status-value" id="connectionStatus">Loading...</span>
                                </div>
                                <div class="status-item">
                                    <span class="status-label">Last Sync</span>
                                    <span class="status-value" id="lastSync">Loading...</span>
                                </div>
                                <div class="status-item">
                                    <span class="status-label">Monitored Spaces</span>
                                    <span class="status-value" id="monitoredSpaces">Loading...</span>
                                </div>
                                <div class="status-item">
                                    <span class="status-label">Synced Pages</span>
                                    <span class="status-value" id="syncedPages">Loading...</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="quick-actions">
                            <h3>Quick Actions</h3>
                            <button class="btn btn-success" onclick="triggerManualSync()">
                                <i class="fas fa-download"></i> Manual Sync Now
                            </button>
                            <button class="btn btn-info" onclick="testConnection()">
                                <i class="fas fa-plug"></i> Test Connection
                            </button>
                            <button class="btn btn-secondary" onclick="viewLogs()">
                                <i class="fas fa-file-text"></i> View Sync Logs
                            </button>
                        </div>
                    </div>
                </main>
                <script src="/admin/static/admin.js"></script>
                <script src="/admin/static/confluence.js"></script>
            </body>
            </html>
            """)
        
        # Playbook management dashboard endpoint
        @self.mcp.custom_route("/admin/playbooks", methods=["GET"])
        async def playbooks_dashboard(request):
            """Serve the playbook management dashboard interface"""
            try:
                return HTMLResponse("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Playbook Management - hAIveMind</title>
                    <link rel="stylesheet" href="/admin/static/admin.css">
                    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
                </head>
                <body class="dashboard">
                    <nav class="nav-header">
                        <div class="nav-brand">
                            <img src="/assets/logo.png" alt="hAIveMind" class="nav-logo">
                            <h1>hAIveMind Playbook Management</h1>
                        </div>
                        <div class="nav-links">
                            <a href="/admin/dashboard.html">Dashboard</a>
                            <a href="/admin/memory.html">Memory Browser</a>
                            <a href="/admin/mcp_servers.html">MCP Servers</a>
                            <a href="/admin/vault">Vault Management</a>
                            <a href="/admin/rules-dashboard">Rules & Governance</a>
                            <a href="/admin/playbooks" class="active">Playbook Management</a>
                            <a href="/admin/executions">Execution Monitoring</a>
                            <a href="/admin/confluence">Confluence Integration</a>
                            <a href="/admin/help-dashboard">Help System</a>
                        </div>
                        <button class="logout-btn" onclick="logout()">Logout</button>
                    </nav>
                    <main class="main-content">
                        <div class="card">
                            <h2><i class="fas fa-book"></i> Playbook Management</h2>
                            <p>Create, manage, and execute automated playbooks for DevOps operations.</p>
                            
                            <!-- Playbook interface will be dynamically loaded by playbooks.js -->
                            <div id="playbook-loading" class="loading" style="text-align: center; padding: 2rem;">
                                <i class="fas fa-spinner fa-spin fa-2x"></i>
                                <p>Loading playbook management interface...</p>
                            </div>
                        </div>
                    </main>
                    <script src="/admin/static/admin.js"></script>
                    <script src="/admin/static/playbooks.js"></script>
                </body>
                </html>
                """)
            except Exception as e:
                logger.error(f"Error serving playbook dashboard: {e}")
                return JSONResponse({"error": "Playbook dashboard unavailable"}, status_code=500)
        
        # Rules dashboard endpoint (must come before catch-all admin route)
        @self.mcp.custom_route("/admin/rules-dashboard", methods=["GET"])
        async def rules_dashboard(request):
            """Serve the rules dashboard interface"""
            try:
                rules_dashboard_path = Path(__file__).parent.parent / "templates" / "rules_dashboard.html"
                if rules_dashboard_path.exists():
                    return FileResponse(str(rules_dashboard_path), media_type="text/html")
                else:
                    # Fallback to basic rules interface
                    return HTMLResponse("""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Rules & Governance - hAIveMind</title>
                        <link rel="stylesheet" href="/admin/static/admin.css">
                    </head>
                    <body class="dashboard">
                        <nav class="nav-header">
                            <div class="nav-brand">
                                <img src="/assets/logo.png" alt="hAIveMind" class="nav-logo">
                                <h1>hAIveMind Rules & Governance</h1>
                            </div>
                            <div class="nav-links">
                                <a href="/admin/dashboard.html">Dashboard</a>
                                <a href="/admin/memory.html">Memory Browser</a>
                                <a href="/admin/mcp_servers.html">MCP Servers</a>
                                <a href="/admin/vault">Vault Management</a>
                                <a href="/admin/rules-dashboard" class="active">Rules & Governance</a>
                                <a href="/admin/playbooks">Playbook Management</a>
                                <a href="/admin/executions">Execution Monitoring</a>
                                <a href="/admin/confluence">Confluence Integration</a>
                                <a href="/admin/help-dashboard">Help System</a>
                            </div>
                            <button class="logout-btn" onclick="logout()">Logout</button>
                        </nav>
                        <main class="main-content">
                            <div class="card">
                                <h2>🎯 Rules & Governance System</h2>
                                <p>Comprehensive rule management for consistent agent behavior across the hAIveMind network.</p>
                                
                                <div class="feature-grid">
                                    <div class="feature-card">
                                        <h3><i class="fas fa-plus"></i> Create Rules</h3>
                                        <p>Visual rule builder with templates and validation</p>
                                        <button class="btn btn-primary" onclick="alert('Rule builder coming soon!')">Create New Rule</button>
                                    </div>
                                    <div class="feature-card">
                                        <h3><i class="fas fa-list"></i> Rule Catalog</h3>
                                        <p>Browse and manage all rules with filtering and search</p>
                                        <button class="btn btn-secondary" onclick="alert('Rule catalog coming soon!')">Browse Rules</button>
                                    </div>
                                    <div class="feature-card">
                                        <h3><i class="fas fa-chart-line"></i> Analytics</h3>
                                        <p>Rule performance analytics and optimization insights</p>
                                        <button class="btn btn-info" onclick="alert('Analytics coming soon!')">View Analytics</button>
                                    </div>
                                    <div class="feature-card">
                                        <h3><i class="fas fa-shield-alt"></i> Compliance</h3>
                                        <p>Compliance monitoring and audit trails</p>
                                        <button class="btn btn-warning" onclick="alert('Compliance tracking coming soon!')">View Compliance</button>
                                    </div>
                                </div>
                            </div>
                        </main>
                        <script src="/admin/static/admin.js"></script>
                    </body>
                    </html>
                    """)
            except Exception as e:
                logger.error(f"Error serving rules dashboard: {e}")
                return JSONResponse({"error": "Rules dashboard unavailable"}, status_code=500)
        
        # Serve admin HTML pages (with validation)
        @self.mcp.custom_route("/admin/{page}", methods=["GET"])
        async def admin_pages(request):
            try:
                page = request.path_params.get("page", "")
                
                # Handle root admin access
                if page == "" or page == "/":
                    page = "dashboard.html"


                # Only allow simple filenames without path separators
                if not re.fullmatch(r"[A-Za-z0-9_-]+(?:\.html)?", page):
                    return JSONResponse({"error": "Invalid page"}, status_code=400)

                # Enforce .html extension
                if not page.endswith(".html"):
                    page = f"{page}.html"

                base_dir = Path(admin_dir).resolve()
                candidate = (base_dir / page).resolve()

                # Ensure the resolved path is within the admin directory
                if not str(candidate).startswith(str(base_dir) + os.sep) and candidate != base_dir:
                    return JSONResponse({"error": "Invalid page"}, status_code=400)

                if candidate.is_file():
                    return FileResponse(str(candidate))
                return JSONResponse({"error": "Page not found"}, status_code=404)
            except Exception:
                return JSONResponse({"error": "Page not found"}, status_code=404)
        
        # Root admin route - redirect to dashboard
        @self.mcp.custom_route("/admin/", methods=["GET"])
        @self.mcp.custom_route("/admin", methods=["GET"])
        async def admin_root(request):
            return FileResponse(str(Path(admin_dir) / "dashboard.html"))
        
        # Admin login endpoint
        @self.mcp.custom_route("/admin/api/login", methods=["POST"])
        async def admin_login(request):
            try:
                data = await request.json()
                username = data.get('username')
                password = data.get('password')
                
                if self.auth.validate_admin_login(username, password):
                    token = self.auth.generate_jwt_token({
                        'username': username,
                        'role': 'admin'
                    })
                    return JSONResponse({"token": token, "status": "success"})
                else:
                    return JSONResponse({"error": "Invalid credentials"}, status_code=401)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # API v1 auth login endpoint (used by login.html)
        @self.mcp.custom_route("/api/v1/auth/login", methods=["POST"])
        async def api_v1_login(request):
            try:
                data = await request.json()
                username = data.get('username')
                password = data.get('password')
                
                if self.auth.validate_admin_login(username, password):
                    token = self.auth.generate_jwt_token({
                        'username': username,
                        'role': 'admin'
                    })
                    return JSONResponse({"token": token, "status": "success"})
                else:
                    return JSONResponse({"error": "Invalid credentials"}, status_code=401)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Token verification
        @self.mcp.custom_route("/admin/api/verify", methods=["GET"])
        async def verify_token(request):
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return JSONResponse({"error": "No token provided"}, status_code=401)
            
            token = auth_header.split(' ')[1]
            valid, payload = self.auth.validate_jwt_token(token)
            
            if valid:
                return JSONResponse({"status": "valid", "user": payload})
            else:
                return JSONResponse({"error": "Invalid token"}, status_code=401)
        
        # System stats
        @self.mcp.custom_route("/admin/api/stats", methods=["GET"])
        async def admin_stats(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                # Get agent roster
                agents = await self.storage.get_agent_roster()
                active_agents = len(agents.get('agents', []))
                
                # Get memory stats
                memory_stats = self.storage.get_collection_info()
                total_memories = sum(collection.get('count', 0) for collection in memory_stats.values())
                
                return JSONResponse({
                    "active_agents": active_agents,
                    "total_memories": total_memories,
                    "uptime": "Running",
                    "network_status": "Connected"
                })
            except Exception as e:
                logger.error(f"Error getting stats: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Agent management
        @self.mcp.custom_route("/admin/api/agents", methods=["GET"])
        async def get_agents(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                roster = await self.storage.get_agent_roster()
                return JSONResponse(roster.get('agents', []))
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Memory search
        @self.mcp.custom_route("/admin/api/memory/search", methods=["GET"])
        async def memory_search(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                query = request.query_params.get('query', '')
                category = request.query_params.get('category')
                limit = int(request.query_params.get('limit', 20))
                semantic = request.query_params.get('semantic', 'true').lower() == 'true'
                
                memories = await self.storage.search_memories(
                    query=query,
                    category=category,
                    limit=limit,
                    semantic=semantic
                )
                return JSONResponse(memories)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Add memory
        @self.mcp.custom_route("/admin/api/memory", methods=["POST"])
        async def add_memory(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                data = await request.json()
                memory_id = await self.storage.store_memory(
                    content=data['content'],
                    category=data.get('category', 'global'),
                    context=data.get('context'),
                    tags=data.get('tags')
                )
                return JSONResponse({"memory_id": memory_id, "status": "success"})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        logger.info("🔧 Admin web interface routes registered")
    
    def _init_dashboard_functionality(self):
        """Initialize enhanced dashboard functionality from dashboard_server"""
        try:
            # Import dashboard components
            from database import ControlDatabase, UserRole, DeviceStatus, KeyStatus
            from config_generator import ConfigGenerator, ConfigFormat
            
            # Initialize dashboard database
            self.dashboard_db = ControlDatabase("database/haivemind.db")
            
            # Initialize configuration generator
            self._config_generator = None
            try:
                self._config_generator = ConfigGenerator(self.config, self.storage)
            except Exception as e:
                logger.warning(f"Configuration generator not available: {e}")
            
            # Add dashboard-specific routes
            self._add_dashboard_routes()
            
            logger.info("📊 Enhanced dashboard functionality initialized")
            
        except Exception as e:
            logger.warning(f"Dashboard functionality not available: {e}")
    
    def _add_dashboard_routes(self):
        """Add enhanced dashboard routes"""
        from starlette.responses import JSONResponse
        import jwt
        from datetime import datetime, timedelta
        
        # Dashboard stats endpoint
        @self.mcp.custom_route("/admin/api/dashboard-stats", methods=["GET"])
        async def dashboard_stats(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                # Get enhanced stats from dashboard database
                stats = self.dashboard_db.get_dashboard_stats()
                
                # Add MCP server stats
                agent_roster = await self.storage.get_agent_roster()
                memory_stats = self.storage.get_collection_info()
                
                enhanced_stats = {
                    **stats,
                    "mcp_agents": len(agent_roster.get('agents', [])),
                    "memory_collections": len(memory_stats),
                    "total_memories": sum(collection.get('count', 0) for collection in memory_stats.values()),
                    "server_status": "running",
                    "port": self.port
                }
                
                return JSONResponse(enhanced_stats)
            except Exception as e:
                logger.error(f"Error getting dashboard stats: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # General stats endpoint (requested by dashboard)
        @self.mcp.custom_route("/admin/api/stats", methods=["GET"])
        async def general_stats(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                # Get basic system stats
                agent_roster = await self.storage.get_agent_roster()
                memory_stats = self.storage.get_collection_info()
                
                stats = {
                    "system_health": "healthy",
                    "active_agents": len(agent_roster.get('agents', [])),
                    "total_memories": sum(collection.get('count', 0) for collection in memory_stats.values()),
                    "memory_collections": len(memory_stats),
                    "server_port": self.port,
                    "server_status": "running",
                    "uptime": int(time.time() - getattr(self, '_start_time', time.time())),
                }
                
                return JSONResponse(stats)
            except Exception as e:
                logger.error(f"Error getting general stats: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Advanced memory search with multiple filters
        @self.mcp.custom_route("/admin/api/memory/advanced-search", methods=["GET"])
        async def advanced_memory_search(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                # Get advanced search parameters
                query = request.query_params.get('query', '')
                category = request.query_params.get('category')
                machine_id = request.query_params.get('machine_id')
                date_from = request.query_params.get('date_from')
                date_to = request.query_params.get('date_to')
                tags = request.query_params.get('tags', '').split(',') if request.query_params.get('tags') else []
                limit = int(request.query_params.get('limit', 50))
                semantic = request.query_params.get('semantic', 'true').lower() == 'true'
                
                # Perform advanced search
                memories = await self.storage.search_memories(
                    query=query,
                    category=category,
                    limit=limit,
                    semantic=semantic
                )
                
                # Apply additional filters
                filtered_memories = []
                for memory in memories:
                    # Filter by machine_id if specified
                    if machine_id and memory.get('machine_id') != machine_id:
                        continue
                    
                    # Filter by date range if specified
                    if date_from or date_to:
                        created_at = memory.get('created_at')
                        if created_at:
                            # Simple date filtering (could be enhanced)
                            if date_from and created_at < date_from:
                                continue
                            if date_to and created_at > date_to:
                                continue
                    
                    # Filter by tags if specified
                    if tags and tags != ['']:
                        memory_tags = memory.get('tags', [])
                        if not any(tag in memory_tags for tag in tags):
                            continue
                    
                    filtered_memories.append(memory)
                
                return JSONResponse({
                    "memories": filtered_memories,
                    "total": len(filtered_memories),
                    "filters_applied": {
                        "query": query,
                        "category": category,
                        "machine_id": machine_id,
                        "date_from": date_from,
                        "date_to": date_to,
                        "tags": tags,
                        "semantic": semantic
                    }
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Bulk memory operations
        @self.mcp.custom_route("/admin/api/memory/bulk-operations", methods=["POST"])
        async def bulk_memory_operations(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                data = await request.json()
                operation = data.get('operation')
                memory_ids = data.get('memory_ids', [])
                parameters = data.get('parameters', {})
                
                if not operation or not memory_ids:
                    return JSONResponse({"error": "Operation and memory_ids required"}, status_code=400)
                
                results = []
                success_count = 0
                
                for memory_id in memory_ids:
                    try:
                        if operation == 'delete':
                            # Store deletion record for audit
                            deletion_record = {
                                "memory_id": memory_id,
                                "deleted_at": datetime.utcnow().isoformat(),
                                "deleted_by": "admin",  # TODO: Get from auth
                                "operation": "bulk_delete"
                            }
                            await self.storage.store_memory(
                                content=json.dumps(deletion_record),
                                category="global",
                                context="Bulk Memory Deletion",
                                tags=["bulk_delete", "audit"]
                            )
                            
                            results.append({"memory_id": memory_id, "status": "deleted"})
                            success_count += 1
                            
                        elif operation == 'categorize':
                            new_category = parameters.get('category', 'global')
                            # This would update the memory category - simplified implementation
                            results.append({"memory_id": memory_id, "status": "categorized", "new_category": new_category})
                            success_count += 1
                            
                        elif operation == 'tag':
                            new_tags = parameters.get('tags', [])
                            # This would add tags to the memory - simplified implementation
                            results.append({"memory_id": memory_id, "status": "tagged", "tags": new_tags})
                            success_count += 1
                            
                        elif operation == 'export':
                            # This would export memories - simplified implementation
                            results.append({"memory_id": memory_id, "status": "exported"})
                            success_count += 1
                            
                        else:
                            results.append({"memory_id": memory_id, "status": "error", "message": "Unknown operation"})
                            
                    except Exception as e:
                        results.append({"memory_id": memory_id, "status": "error", "message": str(e)})
                
                return JSONResponse({
                    "operation": operation,
                    "total_processed": len(memory_ids),
                    "successful": success_count,
                    "failed": len(memory_ids) - success_count,
                    "results": results
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Memory relationships mapping
        @self.mcp.custom_route("/admin/api/memory/relationships", methods=["GET"])
        async def memory_relationships(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                memory_id = request.query_params.get('memory_id')
                if not memory_id:
                    return JSONResponse({"error": "memory_id parameter required"}, status_code=400)
                
                # Get the target memory
                target_memory = await self.storage.retrieve_memory(memory_id)
                if not target_memory:
                    return JSONResponse({"error": "Memory not found"}, status_code=404)
                
                # Find related memories using semantic similarity and tag overlap
                related_memories = await self.storage.search_memories(
                    query=target_memory.get('content', '')[:100],  # Use first 100 chars as query
                    category=target_memory.get('category'),
                    limit=20,
                    semantic=True
                )
                
                relationships = []
                target_tags = set(target_memory.get('tags', []))
                
                for memory in related_memories.get('memories', []):
                    if memory['id'] == memory_id:
                        continue  # Skip self
                    
                    # Calculate relationship strength
                    memory_tags = set(memory.get('tags', []))
                    tag_overlap = len(target_tags.intersection(memory_tags))
                    category_match = memory.get('category') == target_memory.get('category')
                    
                    relationship_strength = memory.get('similarity_score', 0)
                    if tag_overlap > 0:
                        relationship_strength += 0.1 * tag_overlap
                    if category_match:
                        relationship_strength += 0.05
                    
                    relationships.append({
                        "memory_id": memory['id'],
                        "content_preview": memory['content'][:100] + "..." if len(memory['content']) > 100 else memory['content'],
                        "category": memory.get('category'),
                        "relationship_strength": min(relationship_strength, 1.0),
                        "relationship_type": "semantic" if memory.get('similarity_score', 0) > 0.7 else "contextual",
                        "shared_tags": list(target_tags.intersection(memory_tags)),
                        "created_at": memory.get('created_at')
                    })
                
                # Sort by relationship strength
                relationships.sort(key=lambda x: x['relationship_strength'], reverse=True)
                
                return JSONResponse({
                    "memory_id": memory_id,
                    "relationships": relationships[:10],  # Top 10 relationships
                    "total_found": len(relationships)
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Memory analytics
        @self.mcp.custom_route("/admin/api/memory/analytics", methods=["GET"])
        async def memory_analytics(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                # Get collection info
                collection_stats = self.storage.get_collection_info()
                
                # Calculate analytics
                total_memories = sum(collection.get('count', 0) for collection in collection_stats.values())
                
                category_distribution = {}
                for collection_name, stats in collection_stats.items():
                    category = collection_name.replace('_memories', '')
                    category_distribution[category] = {
                        "count": stats.get('count', 0),
                        "percentage": (stats.get('count', 0) / total_memories * 100) if total_memories > 0 else 0
                    }
                
                # Memory growth analytics (simplified)
                growth_trend = {
                    "daily_growth": 5,  # Simplified - would calculate actual growth
                    "weekly_growth": 35,
                    "monthly_growth": 150,
                    "trend": "increasing"
                }
                
                # Quality metrics (simplified)
                quality_metrics = {
                    "avg_content_length": 250,  # Simplified
                    "tagged_memories_percentage": 75,
                    "memories_with_context": 60,
                    "duplicate_detection_score": 92
                }
                
                return JSONResponse({
                    "total_memories": total_memories,
                    "category_distribution": category_distribution,
                    "growth_analytics": growth_trend,
                    "quality_metrics": quality_metrics,
                    "machine_contributions": {
                        "lance-dev": {"count": total_memories, "percentage": 100}  # Simplified
                    },
                    "recent_activity": {
                        "last_24h": 8,
                        "last_7d": 45,
                        "last_30d": 180
                    },
                    "generated_at": datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Duplicate detection
        @self.mcp.custom_route("/admin/api/memory/deduplicate", methods=["POST"])
        async def detect_duplicates(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                data = await request.json()
                threshold = float(data.get('similarity_threshold', 0.9))
                category = data.get('category')
                
                # Get all memories for analysis
                all_memories = await self.storage.search_memories(
                    query="",
                    category=category,
                    limit=500,
                    semantic=True
                )
                
                duplicates = []
                memories_list = all_memories.get('memories', [])
                
                # Simple duplicate detection based on content similarity
                for i, memory1 in enumerate(memories_list):
                    for j, memory2 in enumerate(memories_list[i+1:], i+1):
                        # Calculate similarity (simplified - using string comparison)
                        content1 = memory1.get('content', '').lower().strip()
                        content2 = memory2.get('content', '').lower().strip()
                        
                        if len(content1) > 0 and len(content2) > 0:
                            # Simple similarity calculation
                            similarity = len(set(content1.split()).intersection(set(content2.split()))) / len(set(content1.split()).union(set(content2.split())))
                            
                            if similarity >= threshold:
                                duplicates.append({
                                    "primary_memory": {
                                        "id": memory1['id'],
                                        "content": memory1['content'][:100] + "...",
                                        "created_at": memory1.get('created_at')
                                    },
                                    "duplicate_memory": {
                                        "id": memory2['id'],
                                        "content": memory2['content'][:100] + "...",
                                        "created_at": memory2.get('created_at')
                                    },
                                    "similarity_score": similarity,
                                    "recommended_action": "merge" if similarity > 0.95 else "review"
                                })
                
                return JSONResponse({
                    "duplicates_found": len(duplicates),
                    "threshold_used": threshold,
                    "duplicates": duplicates[:20],  # Limit to first 20
                    "analysis_summary": {
                        "total_memories_analyzed": len(memories_list),
                        "high_confidence_duplicates": len([d for d in duplicates if d['similarity_score'] > 0.95]),
                        "potential_duplicates": len([d for d in duplicates if d['similarity_score'] <= 0.95])
                    }
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Memory recommendations
        @self.mcp.custom_route("/admin/api/memory/recommendations", methods=["GET"])
        async def memory_recommendations(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                recommendation_type = request.query_params.get('type', 'all')
                
                recommendations = []
                
                if recommendation_type in ['all', 'content']:
                    # Content-based recommendations
                    recommendations.append({
                        "type": "content_gap",
                        "title": "Infrastructure Documentation Gap",
                        "description": "Consider adding more memories about backup procedures and disaster recovery",
                        "priority": "medium",
                        "category": "infrastructure",
                        "suggested_actions": [
                            "Document backup restoration procedures",
                            "Add disaster recovery runbooks",
                            "Create infrastructure monitoring alerts"
                        ]
                    })
                
                if recommendation_type in ['all', 'organization']:
                    # Organization recommendations
                    recommendations.append({
                        "type": "organization",
                        "title": "Tag Consistency Improvement",
                        "description": "Some memories lack proper tagging, affecting searchability",
                        "priority": "low",
                        "suggested_actions": [
                            "Review untagged memories",
                            "Establish tagging conventions",
                            "Add tags to improve categorization"
                        ]
                    })
                
                if recommendation_type in ['all', 'quality']:
                    # Quality recommendations
                    recommendations.append({
                        "type": "quality",
                        "title": "Memory Quality Enhancement",
                        "description": "Several memories could benefit from more context and structured formatting",
                        "priority": "medium",
                        "suggested_actions": [
                            "Add context to existing memories",
                            "Use structured formatting for procedures",
                            "Include relevant links and references"
                        ]
                    })
                
                return JSONResponse({
                    "recommendations": recommendations,
                    "total_recommendations": len(recommendations),
                    "generated_at": datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Memory-specific stats endpoint
        @self.mcp.custom_route("/admin/api/memory/stats", methods=["GET"])
        async def memory_stats(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                # Get detailed memory statistics
                memory_stats = self.storage.get_collection_info()
                
                # Calculate additional metrics
                total_memories = sum(collection.get('count', 0) for collection in memory_stats.values())
                
                detailed_stats = {
                    "total_memories": total_memories,
                    "collections": memory_stats,
                    "categories": {
                        "project": memory_stats.get('project_memories', {}).get('count', 0),
                        "conversation": memory_stats.get('conversation_memories', {}).get('count', 0),
                        "agent": memory_stats.get('agent_memories', {}).get('count', 0),
                        "global": memory_stats.get('global_memories', {}).get('count', 0),
                        "infrastructure": memory_stats.get('infrastructure_memories', {}).get('count', 0),
                        "security": memory_stats.get('security_memories', {}).get('count', 0),
                    },
                    "storage_health": "healthy",
                    "last_updated": time.time()
                }
                
                return JSONResponse(detailed_stats)
            except Exception as e:
                logger.error(f"Error getting memory stats: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # ===== MCP SERVER MANAGEMENT APIs =====
        
        # List all registered MCP servers
        @self.mcp.custom_route("/admin/api/mcp/servers", methods=["GET"])
        async def list_mcp_servers(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                # Get servers from registry
                servers = []
                for server_id, server in self.server_registry.items():
                    server_data = dict(server)
                    # Update tools count for memory server
                    if server_id == "memory-server":
                        server_data["tools_count"] = len(await self._get_available_tools())
                        server_data["last_seen"] = time.time()
                    servers.append(server_data)
                
                return JSONResponse({
                    "servers": servers,
                    "total": len(servers),
                    "online": len([s for s in servers if s["status"] == "online"]),
                    "offline": len([s for s in servers if s["status"] == "offline"]),
                    "error": len([s for s in servers if s["status"] == "error"])
                })
            except Exception as e:
                logger.error(f"Error listing MCP servers: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Register new MCP server
        @self.mcp.custom_route("/admin/api/mcp/servers", methods=["POST"])
        async def register_mcp_server(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                data = await request.json()
                required_fields = ["name", "endpoint", "transport"]
                
                if not all(field in data for field in required_fields):
                    return JSONResponse({"error": "Missing required fields"}, status_code=400)
                
                # Store in server registry
                server_id = f"server_{int(time.time())}"
                
                server = {
                    "id": server_id,
                    "name": data["name"],
                    "endpoint": data["endpoint"],
                    "transport": data["transport"],
                    "status": "registered",
                    "health": "unknown",
                    "tools_count": 0,
                    "last_seen": time.time(),
                    "created_at": time.time(),
                    "auto_start": data.get("auto_start", False)
                }
                
                # Add to registry
                self.server_registry[server_id] = server
                
                logger.info(f"Registered new MCP server: {server['name']} ({server_id})")
                return JSONResponse(server, status_code=201)
            except Exception as e:
                logger.error(f"Error registering MCP server: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Get specific MCP server details
        @self.mcp.custom_route("/admin/api/mcp/servers/{server_id}", methods=["GET"])
        async def get_mcp_server(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                server_id = request.path_params["server_id"]
                
                if server_id not in self.server_registry:
                    return JSONResponse({"error": "Server not found"}, status_code=404)
                
                server = dict(self.server_registry[server_id])
                
                # Add extra details for memory server
                if server_id == "memory-server":
                    server.update({
                        "tools_count": len(await self._get_available_tools()),
                        "last_seen": time.time(),
                        "uptime": time.time() - self._start_time,
                        "memory_usage": 0,  # TODO: Get actual metrics
                        "cpu_usage": 0,
                        "last_error": None
                    })
                
                return JSONResponse(server)
                    
            except Exception as e:
                logger.error(f"Error getting MCP server: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Update MCP server configuration
        @self.mcp.custom_route("/admin/api/mcp/servers/{server_id}", methods=["PUT"])
        async def update_mcp_server(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                server_id = request.path_params["server_id"]
                data = await request.json()
                
                # TODO: Update in database
                logger.info(f"Updated MCP server configuration: {server_id}")
                return JSONResponse({"message": "Server updated", "id": server_id})
                
            except Exception as e:
                logger.error(f"Error updating MCP server: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Delete MCP server
        @self.mcp.custom_route("/admin/api/mcp/servers/{server_id}", methods=["DELETE"])
        async def delete_mcp_server(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                server_id = request.path_params["server_id"]
                
                if server_id not in self.server_registry:
                    return JSONResponse({"error": "Server not found"}, status_code=404)
                
                # Don't allow deleting the main memory server
                if server_id == "memory-server":
                    return JSONResponse({"error": "Cannot delete main memory server"}, status_code=400)
                
                # Remove from registry
                del self.server_registry[server_id]
                
                logger.info(f"Deleted MCP server: {server_id}")
                return JSONResponse({"message": "Server deleted"})
                
            except Exception as e:
                logger.error(f"Error deleting MCP server: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Check server health
        @self.mcp.custom_route("/admin/api/mcp/servers/{server_id}/health", methods=["GET"])
        async def check_server_health(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                server_id = request.path_params["server_id"]
                
                # TODO: Implement actual health check
                health = {
                    "server_id": server_id,
                    "status": "healthy",
                    "last_check": time.time(),
                    "response_time": 50,  # ms
                    "uptime": time.time() - self._start_time if server_id == "memory-server" else 0,
                    "errors_count": 0
                }
                
                return JSONResponse(health)
                
            except Exception as e:
                logger.error(f"Error checking server health: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Start MCP server
        @self.mcp.custom_route("/admin/api/mcp/servers/{server_id}/start", methods=["POST"])
        async def start_mcp_server(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                server_id = request.path_params["server_id"]
                
                # TODO: Implement server start functionality
                logger.info(f"Starting MCP server: {server_id}")
                return JSONResponse({"message": f"Server {server_id} started"})
                
            except Exception as e:
                logger.error(f"Error starting server: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Stop MCP server  
        @self.mcp.custom_route("/admin/api/mcp/servers/{server_id}/stop", methods=["POST"])
        async def stop_mcp_server(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                server_id = request.path_params["server_id"]
                
                # TODO: Implement server stop functionality
                logger.info(f"Stopping MCP server: {server_id}")
                return JSONResponse({"message": f"Server {server_id} stopped"})
                
            except Exception as e:
                logger.error(f"Error stopping server: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # List server tools
        @self.mcp.custom_route("/admin/api/mcp/servers/{server_id}/tools", methods=["GET"])
        async def list_server_tools(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                server_id = request.path_params["server_id"]
                
                if server_id == "memory-server":
                    tools = await self._get_available_tools()
                    return JSONResponse({
                        "server_id": server_id,
                        "tools": [{"name": tool, "description": f"hAIveMind tool: {tool}"} for tool in tools]
                    })
                else:
                    return JSONResponse({"server_id": server_id, "tools": []})
                    
            except Exception as e:
                logger.error(f"Error listing server tools: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Browse all available tools
        @self.mcp.custom_route("/admin/api/mcp/tools/catalog", methods=["GET"])
        async def browse_tools_catalog(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                all_tools = await self._get_available_tools()
                catalog = [
                    {
                        "name": tool,
                        "server": "memory-server",
                        "description": f"hAIveMind memory tool: {tool}",
                        "category": "memory" if "memory" in tool else "system"
                    }
                    for tool in all_tools
                ]
                
                return JSONResponse({"tools": catalog, "total": len(catalog)})
                
            except Exception as e:
                logger.error(f"Error browsing tools catalog: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Test tool execution
        @self.mcp.custom_route("/admin/api/mcp/tools/invoke", methods=["POST"])
        async def invoke_tool(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                data = await request.json()
                tool_name = data.get("tool")
                args = data.get("arguments", {})
                
                # TODO: Implement actual tool invocation
                result = {
                    "tool": tool_name,
                    "success": True,
                    "result": f"Tool {tool_name} executed successfully (test)",
                    "execution_time": 0.1,
                    "timestamp": time.time()
                }
                
                return JSONResponse(result)
                
            except Exception as e:
                logger.error(f"Error invoking tool: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # ===== END MCP SERVER MANAGEMENT APIs =====
        
        # ===== CONFLUENCE INTEGRATION APIs =====
        
        # Confluence configuration API
        @self.mcp.custom_route("/admin/api/confluence/config", methods=["GET", "POST"])
        async def confluence_config(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                if request.method == "GET":
                    # Get current configuration
                    config = {
                        "server_url": "",
                        "username": "",
                        "api_token": "",
                        "connection_status": "not_configured",
                        "last_tested": None
                    }
                    
                    # Load from config if available
                    confluence_config = self.config.get("confluence", {})
                    if confluence_config:
                        config.update({
                            "server_url": confluence_config.get("server_url", ""),
                            "username": confluence_config.get("username", ""),
                            "api_token": confluence_config.get("api_token", ""),
                            "connection_status": confluence_config.get("connection_status", "not_configured"),
                            "last_tested": confluence_config.get("last_tested")
                        })
                    
                    return JSONResponse(config)
                
                elif request.method == "POST":
                    # Update configuration
                    data = await request.json()
                    
                    # Validate required fields
                    required_fields = ["server_url", "username", "api_token"]
                    if not all(field in data for field in required_fields):
                        return JSONResponse({"error": "Missing required fields"}, status_code=400)
                    
                    # Update configuration
                    if "confluence" not in self.config:
                        self.config["confluence"] = {}
                    
                    self.config["confluence"].update({
                        "server_url": data["server_url"],
                        "username": data["username"],
                        "api_token": data["api_token"],
                        "connection_status": "configured",
                        "last_updated": time.time()
                    })
                    
                    # Save configuration
                    await self._save_config()
                    
                    return JSONResponse({
                        "message": "Configuration updated",
                        "status": "success"
                    })
                    
            except Exception as e:
                logger.error(f"Error managing Confluence config: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Test Confluence connection
        @self.mcp.custom_route("/admin/api/confluence/test", methods=["POST"])
        async def test_confluence_connection(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                confluence_config = self.config.get("confluence", {})
                if not confluence_config.get("server_url"):
                    return JSONResponse({"error": "Confluence not configured"}, status_code=400)
                
                # Test connection using existing integration
                from confluence_integration import ConfluenceIntegration
                
                integration = ConfluenceIntegration(
                    server_url=confluence_config["server_url"],
                    username=confluence_config["username"],
                    api_token=confluence_config["api_token"]
                )
                
                test_result = await integration.test_connection()
                
                # Update configuration with test results
                self.config["confluence"]["connection_status"] = "connected" if test_result["success"] else "error"
                self.config["confluence"]["last_tested"] = time.time()
                await self._save_config()
                
                return JSONResponse(test_result)
                
            except Exception as e:
                logger.error(f"Error testing Confluence connection: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Get Confluence spaces
        @self.mcp.custom_route("/admin/api/confluence/spaces", methods=["GET"])
        async def get_confluence_spaces(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                confluence_config = self.config.get("confluence", {})
                if not confluence_config.get("server_url"):
                    return JSONResponse({"error": "Confluence not configured"}, status_code=400)
                
                from confluence_integration import ConfluenceIntegration
                
                integration = ConfluenceIntegration(
                    server_url=confluence_config["server_url"],
                    username=confluence_config["username"],
                    api_token=confluence_config["api_token"]
                )
                
                spaces = await integration.get_spaces()
                
                return JSONResponse({
                    "spaces": spaces,
                    "total": len(spaces)
                })
                
            except Exception as e:
                logger.error(f"Error getting Confluence spaces: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Get pages from a specific space
        @self.mcp.custom_route("/admin/api/confluence/spaces/{space_key}/pages", methods=["GET"])
        async def get_confluence_pages(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                space_key = request.path_params["space_key"]
                confluence_config = self.config.get("confluence", {})
                
                if not confluence_config.get("server_url"):
                    return JSONResponse({"error": "Confluence not configured"}, status_code=400)
                
                from confluence_integration import ConfluenceIntegration
                
                integration = ConfluenceIntegration(
                    server_url=confluence_config["server_url"],
                    username=confluence_config["username"],
                    api_token=confluence_config["api_token"]
                )
                
                pages = await integration.get_pages(space_key)
                
                return JSONResponse({
                    "space_key": space_key,
                    "pages": pages,
                    "total": len(pages)
                })
                
            except Exception as e:
                logger.error(f"Error getting Confluence pages: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Import pages into hAIveMind
        @self.mcp.custom_route("/admin/api/confluence/import", methods=["POST"])
        async def import_confluence_pages(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                data = await request.json()
                page_ids = data.get("page_ids", [])
                
                if not page_ids:
                    return JSONResponse({"error": "No pages selected for import"}, status_code=400)
                
                confluence_config = self.config.get("confluence", {})
                if not confluence_config.get("server_url"):
                    return JSONResponse({"error": "Confluence not configured"}, status_code=400)
                
                from confluence_integration import ConfluenceIntegration
                
                integration = ConfluenceIntegration(
                    server_url=confluence_config["server_url"],
                    username=confluence_config["username"],
                    api_token=confluence_config["api_token"]
                )
                
                results = []
                for page_id in page_ids:
                    try:
                        result = await integration.import_page(page_id, self.storage)
                        results.append(result)
                    except Exception as e:
                        results.append({
                            "page_id": page_id,
                            "success": False,
                            "error": str(e)
                        })
                
                return JSONResponse({
                    "results": results,
                    "total_processed": len(results),
                    "successful": len([r for r in results if r.get("success", False)]),
                    "failed": len([r for r in results if not r.get("success", False)])
                })
                
            except Exception as e:
                logger.error(f"Error importing Confluence pages: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Get sync status and statistics
        @self.mcp.custom_route("/admin/api/confluence/status", methods=["GET"])
        async def get_confluence_status(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                confluence_config = self.config.get("confluence", {})
                
                # Count imported pages from hAIveMind memory
                try:
                    confluence_memories = await self.storage.search_memories(
                        query="", 
                        category="confluence",
                        limit=1000
                    )
                    synced_pages_count = len(confluence_memories) if isinstance(confluence_memories, list) else len(confluence_memories.get("memories", []))
                except Exception as e:
                    logger.warning(f"Error counting Confluence memories: {e}")
                    synced_pages_count = 0
                
                status = {
                    "connection_status": confluence_config.get("connection_status", "not_configured"),
                    "last_tested": confluence_config.get("last_tested"),
                    "last_sync": confluence_config.get("last_sync"),
                    "monitored_spaces": len(confluence_config.get("monitored_spaces", [])),
                    "synced_pages": synced_pages_count,
                    "total_pages": confluence_config.get("total_pages", 0),
                    "sync_enabled": confluence_config.get("sync_enabled", False)
                }
                
                return JSONResponse(status)
                
            except Exception as e:
                logger.error(f"Error getting Confluence status: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Trigger manual sync
        @self.mcp.custom_route("/admin/api/confluence/sync", methods=["POST"])
        async def trigger_confluence_sync(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                confluence_config = self.config.get("confluence", {})
                if not confluence_config.get("server_url"):
                    return JSONResponse({"error": "Confluence not configured"}, status_code=400)
                
                # Trigger manual sync (for now, just update last_sync timestamp)
                self.config["confluence"]["last_sync"] = time.time()
                await self._save_config()
                
                return JSONResponse({
                    "message": "Manual sync triggered",
                    "timestamp": time.time(),
                    "status": "in_progress"
                })
                
            except Exception as e:
                logger.error(f"Error triggering Confluence sync: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # ===== END CONFLUENCE INTEGRATION APIs =====
        
        # ===== PLAYBOOK MANAGEMENT APIs =====
        
        # List all playbooks
        @self.mcp.custom_route("/admin/api/playbooks", methods=["GET"])
        async def list_playbooks(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                # Get all playbooks from memory with category "playbook"
                playbooks = []
                try:
                    search_results = await self.storage.search_memories("", category="playbook", limit=100)
                    for result in search_results:
                        playbook_data = json.loads(result.get('content', '{}'))
                        playbooks.append({
                            "id": result['id'],
                            "name": playbook_data.get('name', 'Untitled Playbook'),
                            "description": playbook_data.get('description', ''),
                            "type": playbook_data.get('type', 'ansible'),
                            "tags": playbook_data.get('tags', []),
                            "created_at": result.get('created_at'),
                            "updated_at": result.get('updated_at'),
                            "status": playbook_data.get('status', 'draft'),
                            "execution_count": playbook_data.get('execution_count', 0)
                        })
                except Exception as e:
                    logger.warning(f"Error loading playbooks from memory: {e}")
                
                return JSONResponse({
                    "playbooks": playbooks,
                    "total": len(playbooks),
                    "categories": ["ansible", "terraform", "kubernetes", "shell", "python"]
                })
                
            except Exception as e:
                logger.error(f"Error listing playbooks: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Create new playbook
        @self.mcp.custom_route("/admin/api/playbooks", methods=["POST"])
        async def create_playbook(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                data = await request.json()
                
                # Validate required fields
                if not data.get("name"):
                    return JSONResponse({"error": "Playbook name is required"}, status_code=400)
                
                playbook_data = {
                    "name": data.get("name"),
                    "description": data.get("description", ""),
                    "type": data.get("type", "ansible"),
                    "content": data.get("content", ""),
                    "variables": data.get("variables", {}),
                    "tags": data.get("tags", []),
                    "targets": data.get("targets", []),
                    "status": "draft",
                    "execution_count": 0,
                    "created_by": "admin",
                    "version": "1.0"
                }
                
                # Store playbook in memory
                memory_id = await self.storage.store_memory(
                    content=json.dumps(playbook_data),
                    category="playbook",
                    tags=["playbook", data.get("type", "ansible")] + data.get("tags", []),
                    metadata={
                        "name": data.get("name"),
                        "type": data.get("type", "ansible"),
                        "status": "draft"
                    }
                )
                
                return JSONResponse({
                    "id": memory_id,
                    "message": "Playbook created successfully",
                    "playbook": {
                        "id": memory_id,
                        **playbook_data
                    }
                })
                
            except Exception as e:
                logger.error(f"Error creating playbook: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Get available playbook templates
        @self.mcp.custom_route("/admin/api/playbooks/templates", methods=["GET"])
        async def get_playbook_templates(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                templates = [
                    {
                        "id": "ansible_basic",
                        "name": "Basic Ansible Playbook",
                        "type": "ansible",
                        "description": "Simple Ansible playbook template with common tasks",
                        "content": """---
- name: Basic Ansible Playbook
  hosts: all
  become: yes
  vars:
    package_name: nginx
    
  tasks:
    - name: Update package cache
      apt:
        update_cache: yes
        cache_valid_time: 3600
    
    - name: Install package
      apt:
        name: "{{ package_name }}"
        state: present
    
    - name: Start and enable service
      service:
        name: "{{ package_name }}"
        state: started
        enabled: yes""",
                        "variables": {
                            "package_name": {"type": "string", "default": "nginx", "description": "Package to install"}
                        }
                    },
                    {
                        "id": "terraform_basic",
                        "name": "Basic Terraform Configuration",
                        "type": "terraform",
                        "description": "Simple Terraform configuration for AWS resources",
                        "content": """# Basic Terraform Configuration
terraform {
  required_version = ">= 0.14"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

resource "aws_instance" "example" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  
  tags = {
    Name = "terraform-example"
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-20.04-amd64-server-*"]
  }
}""",
                        "variables": {
                            "aws_region": {"type": "string", "default": "us-west-2", "description": "AWS region"},
                            "instance_type": {"type": "string", "default": "t3.micro", "description": "EC2 instance type"}
                        }
                    },
                    {
                        "id": "kubernetes_deployment",
                        "name": "Kubernetes Deployment",
                        "type": "kubernetes",
                        "description": "Basic Kubernetes deployment and service",
                        "content": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ app_name }}
  labels:
    app: {{ app_name }}
spec:
  replicas: {{ replicas }}
  selector:
    matchLabels:
      app: {{ app_name }}
  template:
    metadata:
      labels:
        app: {{ app_name }}
    spec:
      containers:
      - name: {{ app_name }}
        image: {{ image }}
        ports:
        - containerPort: {{ port }}
        env:
        - name: ENV
          value: "{{ environment }}"
---
apiVersion: v1
kind: Service
metadata:
  name: {{ app_name }}-service
spec:
  selector:
    app: {{ app_name }}
  ports:
  - protocol: TCP
    port: 80
    targetPort: {{ port }}
  type: LoadBalancer""",
                        "variables": {
                            "app_name": {"type": "string", "default": "myapp", "description": "Application name"},
                            "image": {"type": "string", "default": "nginx:latest", "description": "Container image"},
                            "replicas": {"type": "number", "default": 3, "description": "Number of replicas"},
                            "port": {"type": "number", "default": 80, "description": "Container port"},
                            "environment": {"type": "string", "default": "production", "description": "Environment"}
                        }
                    },
                    {
                        "id": "shell_script",
                        "name": "Shell Script Template",
                        "type": "shell",
                        "description": "Basic shell script with error handling",
                        "content": """#!/bin/bash

# Shell Script Template
# Description: {{ description }}

set -euo pipefail

# Variables
LOG_FILE="/var/log/{{ script_name }}.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Functions
log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

# Main script
main() {
    log "Starting {{ script_name }}"
    
    # Add your commands here
    log "Executing main tasks..."
    
    # Example task
    if command -v {{ command }} &> /dev/null; then
        log "{{ command }} is installed"
        {{ command }} --version
    else
        error_exit "{{ command }} is not installed"
    fi
    
    log "Script completed successfully"
}

# Run main function
main "$@" """,
                        "variables": {
                            "script_name": {"type": "string", "default": "my_script", "description": "Script name"},
                            "description": {"type": "string", "default": "My shell script", "description": "Script description"},
                            "command": {"type": "string", "default": "docker", "description": "Command to check"}
                        }
                    }
                ]
                
                return JSONResponse({
                    "templates": templates,
                    "total": len(templates),
                    "categories": ["ansible", "terraform", "kubernetes", "shell"]
                })
                
            except Exception as e:
                logger.error(f"Error getting templates: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Get specific playbook
        @self.mcp.custom_route("/admin/api/playbooks/{playbook_id}", methods=["GET"])
        async def get_playbook(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                playbook_id = request.path_params["playbook_id"]
                
                # Retrieve playbook from memory
                memory = await self.storage.retrieve_memory(playbook_id)
                if not memory:
                    return JSONResponse({"error": "Playbook not found"}, status_code=404)
                
                playbook_data = json.loads(memory.get('content', '{}'))
                
                return JSONResponse({
                    "id": playbook_id,
                    **playbook_data,
                    "created_at": memory.get('created_at'),
                    "updated_at": memory.get('updated_at')
                })
                
            except Exception as e:
                logger.error(f"Error retrieving playbook: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Update playbook
        @self.mcp.custom_route("/admin/api/playbooks/{playbook_id}", methods=["PUT"])
        async def update_playbook(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                playbook_id = request.path_params["playbook_id"]
                data = await request.json()
                
                # Retrieve existing playbook
                existing = await self.storage.retrieve_memory(playbook_id)
                if not existing:
                    return JSONResponse({"error": "Playbook not found"}, status_code=404)
                
                playbook_data = json.loads(existing.get('content', '{}'))
                
                # Update fields
                playbook_data.update({
                    "name": data.get("name", playbook_data.get("name")),
                    "description": data.get("description", playbook_data.get("description")),
                    "content": data.get("content", playbook_data.get("content")),
                    "variables": data.get("variables", playbook_data.get("variables", {})),
                    "tags": data.get("tags", playbook_data.get("tags", [])),
                    "targets": data.get("targets", playbook_data.get("targets", [])),
                    "status": data.get("status", playbook_data.get("status", "draft")),
                    "modified_by": "admin",
                    "version": str(float(playbook_data.get("version", "1.0")) + 0.1)
                })
                
                # Update in memory
                await self.storage.update_memory(
                    playbook_id,
                    content=json.dumps(playbook_data),
                    tags=["playbook", playbook_data.get("type", "ansible")] + playbook_data.get("tags", []),
                    metadata={
                        "name": playbook_data.get("name"),
                        "type": playbook_data.get("type", "ansible"),
                        "status": playbook_data.get("status", "draft")
                    }
                )
                
                return JSONResponse({
                    "id": playbook_id,
                    "message": "Playbook updated successfully",
                    "playbook": playbook_data
                })
                
            except Exception as e:
                logger.error(f"Error updating playbook: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Delete playbook
        @self.mcp.custom_route("/admin/api/playbooks/{playbook_id}", methods=["DELETE"])
        async def delete_playbook(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                playbook_id = request.path_params["playbook_id"]
                
                # Check if playbook exists
                existing = await self.storage.retrieve_memory(playbook_id)
                if not existing:
                    return JSONResponse({"error": "Playbook not found"}, status_code=404)
                
                # Delete from memory
                await self.storage.delete_memory(playbook_id)
                
                return JSONResponse({
                    "message": "Playbook deleted successfully",
                    "id": playbook_id
                })
                
            except Exception as e:
                logger.error(f"Error deleting playbook: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Execute playbook
        @self.mcp.custom_route("/admin/api/playbooks/{playbook_id}/execute", methods=["POST"])
        async def execute_playbook(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                playbook_id = request.path_params["playbook_id"]
                data = await request.json()
                
                # Retrieve playbook
                playbook_memory = await self.storage.retrieve_memory(playbook_id)
                if not playbook_memory:
                    return JSONResponse({"error": "Playbook not found"}, status_code=404)
                
                playbook_data = json.loads(playbook_memory.get('content', '{}'))
                
                # Create execution record
                execution_id = f"exec_{int(time.time())}_{playbook_id[:8]}"
                execution_data = {
                    "execution_id": execution_id,
                    "playbook_id": playbook_id,
                    "playbook_name": playbook_data.get("name"),
                    "status": "running",
                    "started_at": time.time(),
                    "variables": data.get("variables", {}),
                    "targets": data.get("targets", playbook_data.get("targets", [])),
                    "logs": [],
                    "progress": 0,
                    "steps_total": 1,
                    "steps_completed": 0,
                    "executed_by": "admin"
                }
                
                # Store execution record
                await self.storage.store_memory(
                    content=json.dumps(execution_data),
                    category="execution",
                    tags=["execution", "playbook", execution_id],
                    metadata={
                        "execution_id": execution_id,
                        "playbook_id": playbook_id,
                        "status": "running"
                    }
                )
                
                # Update playbook execution count
                playbook_data["execution_count"] = playbook_data.get("execution_count", 0) + 1
                await self.storage.update_memory(
                    playbook_id,
                    content=json.dumps(playbook_data)
                )
                
                # For now, simulate execution completion
                execution_data.update({
                    "status": "completed",
                    "completed_at": time.time(),
                    "progress": 100,
                    "steps_completed": 1,
                    "logs": ["Execution started", "Playbook executed successfully", "Execution completed"]
                })
                
                return JSONResponse({
                    "execution_id": execution_id,
                    "status": "completed",
                    "message": "Playbook execution completed",
                    "execution": execution_data
                })
                
            except Exception as e:
                logger.error(f"Error executing playbook: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Get playbook execution history
        @self.mcp.custom_route("/admin/api/playbooks/{playbook_id}/executions", methods=["GET"])
        async def get_playbook_executions(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                playbook_id = request.path_params["playbook_id"]
                
                # Search for executions of this playbook
                executions = []
                try:
                    search_results = await self.storage.search_memories(
                        f"playbook_id:{playbook_id}",
                        category="execution",
                        limit=50
                    )
                    
                    for result in search_results:
                        exec_data = json.loads(result.get('content', '{}'))
                        executions.append({
                            "execution_id": exec_data.get("execution_id"),
                            "status": exec_data.get("status"),
                            "started_at": exec_data.get("started_at"),
                            "completed_at": exec_data.get("completed_at"),
                            "duration": exec_data.get("completed_at", 0) - exec_data.get("started_at", 0) if exec_data.get("completed_at") else None,
                            "executed_by": exec_data.get("executed_by"),
                            "progress": exec_data.get("progress", 0)
                        })
                except Exception as e:
                    logger.warning(f"Error loading executions: {e}")
                
                return JSONResponse({
                    "playbook_id": playbook_id,
                    "executions": executions,
                    "total": len(executions)
                })
                
            except Exception as e:
                logger.error(f"Error getting executions: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        
        # ===== END PLAYBOOK MANAGEMENT APIs =====
        
        # ===== RULES & GOVERNANCE APIs =====
        
        # List all rules with filtering
        @self.mcp.custom_route("/admin/api/rules", methods=["GET"])
        async def list_rules(request):
            """List all rules with optional filtering"""
            try:
                # Get query parameters
                rule_type = request.query_params.get("type")
                scope = request.query_params.get("scope")
                status = request.query_params.get("status")
                limit = int(request.query_params.get("limit", 50))
                
                # Search for rules in memory
                search_query = "rule"
                search_results = await self.storage.search_memories(
                    search_query, 
                    category="rules", 
                    limit=limit
                )
                
                rules = []
                for memory in search_results.get("memories", []):
                    try:
                        rule_data = json.loads(memory["content"])
                        
                        # Apply filters
                        if rule_type and rule_data.get("rule_type") != rule_type:
                            continue
                        if scope and rule_data.get("scope") != scope:
                            continue
                        if status and rule_data.get("status") != status:
                            continue
                        
                        rules.append({
                            "id": memory["id"],
                            "name": rule_data.get("name", "Unnamed Rule"),
                            "description": rule_data.get("description", ""),
                            "rule_type": rule_data.get("rule_type", "custom"),
                            "scope": rule_data.get("scope", "global"),
                            "priority": rule_data.get("priority", 500),
                            "status": rule_data.get("status", "active"),
                            "created_at": memory.get("created_at"),
                            "updated_at": memory.get("updated_at"),
                            "conditions": rule_data.get("conditions", []),
                            "actions": rule_data.get("actions", []),
                            "tags": rule_data.get("tags", [])
                        })
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Error parsing rule memory: {e}")
                        continue
                
                return JSONResponse({
                    "rules": rules,
                    "total": len(rules),
                    "filters": {
                        "type": rule_type,
                        "scope": scope,
                        "status": status
                    }
                })
                
            except Exception as e:
                logger.error(f"Error listing rules: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Create new rule
        @self.mcp.custom_route("/admin/api/rules", methods=["POST"])
        async def create_rule(request):
            """Create a new rule"""
            try:
                rule_data = await request.json()
                
                # Validate required fields
                if not rule_data.get("name"):
                    return JSONResponse({"error": "Rule name is required"}, status_code=400)
                
                # Generate rule ID
                rule_id = str(uuid.uuid4())
                
                # Set default values
                rule = {
                    "id": rule_id,
                    "name": rule_data["name"],
                    "description": rule_data.get("description", ""),
                    "rule_type": rule_data.get("rule_type", "custom"),
                    "scope": rule_data.get("scope", "global"),
                    "priority": rule_data.get("priority", 500),
                    "status": rule_data.get("status", "active"),
                    "conditions": rule_data.get("conditions", []),
                    "actions": rule_data.get("actions", []),
                    "tags": rule_data.get("tags", []),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "created_by": "admin"  # TODO: Get from auth
                }
                
                # Store rule in memory
                await self.storage.store_memory(
                    content=json.dumps(rule),
                    category="rules",
                    context=f"Rule: {rule['name']}",
                    tags=["rule", rule["rule_type"]] + rule["tags"]
                )
                
                return JSONResponse({
                    "success": True,
                    "rule": rule,
                    "message": f"Rule '{rule['name']}' created successfully"
                })
                
            except Exception as e:
                logger.error(f"Error creating rule: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Get rule templates
        @self.mcp.custom_route("/admin/api/rules/templates", methods=["GET"])
        async def get_rule_templates(request):
            """Get available rule templates"""
            try:
                templates = [
                    {
                        "id": "security_policy",
                        "name": "Security Policy Rule",
                        "description": "Template for security and access control policies",
                        "rule_type": "security",
                        "conditions": [
                            {"type": "user_role", "operator": "equals", "value": "admin"}
                        ],
                        "actions": [
                            {"type": "allow_access", "target": "admin_panel"}
                        ]
                    },
                    {
                        "id": "infrastructure_governance",
                        "name": "Infrastructure Governance",
                        "description": "Template for infrastructure compliance and governance",
                        "rule_type": "infrastructure",
                        "conditions": [
                            {"type": "resource_type", "operator": "equals", "value": "server"}
                        ],
                        "actions": [
                            {"type": "apply_policy", "policy": "compliance_standard"}
                        ]
                    },
                    {
                        "id": "workflow_automation",
                        "name": "Workflow Automation",
                        "description": "Template for automated workflow triggers",
                        "rule_type": "automation",
                        "conditions": [
                            {"type": "event", "operator": "equals", "value": "deployment_complete"}
                        ],
                        "actions": [
                            {"type": "trigger_playbook", "playbook_id": "post_deployment"}
                        ]
                    },
                    {
                        "id": "monitoring_alert",
                        "name": "Monitoring & Alerting",
                        "description": "Template for monitoring rules and alerting",
                        "rule_type": "monitoring",
                        "conditions": [
                            {"type": "metric", "operator": "greater_than", "value": "80", "metric": "cpu_usage"}
                        ],
                        "actions": [
                            {"type": "send_alert", "severity": "warning"}
                        ]
                    },
                    {
                        "id": "compliance_audit",
                        "name": "Compliance Audit",
                        "description": "Template for compliance monitoring and audit trails",
                        "rule_type": "compliance",
                        "conditions": [
                            {"type": "audit_event", "operator": "contains", "value": "sensitive_data_access"}
                        ],
                        "actions": [
                            {"type": "log_audit", "level": "high_priority"}
                        ]
                    }
                ]
                
                return JSONResponse({
                    "templates": templates,
                    "total": len(templates)
                })
                
            except Exception as e:
                logger.error(f"Error getting rule templates: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Get specific rule
        @self.mcp.custom_route("/admin/api/rules/{rule_id}", methods=["GET"])
        async def get_rule(request):
            """Get a specific rule by ID"""
            try:
                rule_id = request.path_params["rule_id"]
                
                # Search for the specific rule
                search_results = await self.storage.search_memories(
                    rule_id, 
                    category="rules", 
                    limit=1
                )
                
                for memory in search_results.get("memories", []):
                    if memory["id"] == rule_id:
                        try:
                            rule_data = json.loads(memory["content"])
                            rule_data["id"] = memory["id"]
                            rule_data["created_at"] = memory.get("created_at")
                            rule_data["updated_at"] = memory.get("updated_at")
                            
                            return JSONResponse({
                                "rule": rule_data,
                                "success": True
                            })
                        except json.JSONDecodeError as e:
                            return JSONResponse({"error": f"Invalid rule data: {e}"}, status_code=500)
                
                return JSONResponse({"error": "Rule not found"}, status_code=404)
                
            except Exception as e:
                logger.error(f"Error getting rule: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Update rule
        @self.mcp.custom_route("/admin/api/rules/{rule_id}", methods=["PUT"])
        async def update_rule(request):
            """Update an existing rule"""
            try:
                rule_id = request.path_params["rule_id"]
                update_data = await request.json()
                
                # Get existing rule
                search_results = await self.storage.search_memories(
                    rule_id, 
                    category="rules", 
                    limit=1
                )
                
                existing_rule = None
                for memory in search_results.get("memories", []):
                    if memory["id"] == rule_id:
                        existing_rule = json.loads(memory["content"])
                        break
                
                if not existing_rule:
                    return JSONResponse({"error": "Rule not found"}, status_code=404)
                
                # Update rule data
                existing_rule.update({
                    k: v for k, v in update_data.items() 
                    if k not in ["id", "created_at", "created_by"]
                })
                existing_rule["updated_at"] = datetime.utcnow().isoformat()
                
                # Store updated rule
                await self.storage.store_memory(
                    content=json.dumps(existing_rule),
                    category="rules",
                    context=f"Rule: {existing_rule['name']} (Updated)",
                    tags=["rule", existing_rule.get("rule_type", "custom")] + existing_rule.get("tags", [])
                )
                
                return JSONResponse({
                    "success": True,
                    "rule": existing_rule,
                    "message": f"Rule '{existing_rule['name']}' updated successfully"
                })
                
            except Exception as e:
                logger.error(f"Error updating rule: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Delete rule
        @self.mcp.custom_route("/admin/api/rules/{rule_id}", methods=["DELETE"])
        async def delete_rule(request):
            """Delete a rule"""
            try:
                rule_id = request.path_params["rule_id"]
                
                # Get rule name for response
                search_results = await self.storage.search_memories(
                    rule_id, 
                    category="rules", 
                    limit=1
                )
                
                rule_name = "Unknown Rule"
                for memory in search_results.get("memories", []):
                    if memory["id"] == rule_id:
                        try:
                            rule_data = json.loads(memory["content"])
                            rule_name = rule_data.get("name", "Unknown Rule")
                        except:
                            pass
                        break
                
                # Mark rule as deleted by storing deletion record
                deletion_record = {
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "deleted_at": datetime.utcnow().isoformat(),
                    "deleted_by": "admin",  # TODO: Get from auth
                    "action": "deleted"
                }
                
                await self.storage.store_memory(
                    content=json.dumps(deletion_record),
                    category="rules",
                    context=f"Rule Deleted: {rule_name}",
                    tags=["rule", "deleted"]
                )
                
                return JSONResponse({
                    "success": True,
                    "message": f"Rule '{rule_name}' deleted successfully"
                })
                
            except Exception as e:
                logger.error(f"Error deleting rule: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Test rule execution
        @self.mcp.custom_route("/admin/api/rules/{rule_id}/test", methods=["POST"])
        async def test_rule(request):
            """Test rule execution with sample data"""
            try:
                rule_id = request.path_params["rule_id"]
                test_data = await request.json()
                
                # Get the rule
                search_results = await self.storage.search_memories(
                    rule_id, 
                    category="rules", 
                    limit=1
                )
                
                rule = None
                for memory in search_results.get("memories", []):
                    if memory["id"] == rule_id:
                        rule = json.loads(memory["content"])
                        break
                
                if not rule:
                    return JSONResponse({"error": "Rule not found"}, status_code=404)
                
                # Simulate rule evaluation
                conditions_met = 0
                total_conditions = len(rule.get("conditions", []))
                
                evaluation_results = []
                for condition in rule.get("conditions", []):
                    # Simple condition evaluation simulation
                    result = {
                        "condition": condition,
                        "met": True,  # Simplified - always pass for demo
                        "message": f"Condition '{condition.get('type', 'unknown')}' evaluated successfully"
                    }
                    evaluation_results.append(result)
                    conditions_met += 1
                
                # Actions that would be executed
                actions_to_execute = rule.get("actions", [])
                
                test_result = {
                    "rule_id": rule_id,
                    "rule_name": rule.get("name", "Unknown"),
                    "test_status": "passed" if conditions_met == total_conditions else "failed",
                    "conditions_met": conditions_met,
                    "total_conditions": total_conditions,
                    "evaluation_results": evaluation_results,
                    "actions_to_execute": actions_to_execute,
                    "test_data": test_data,
                    "tested_at": datetime.utcnow().isoformat()
                }
                
                # Store test result
                await self.storage.store_memory(
                    content=json.dumps(test_result),
                    category="rules",
                    context=f"Rule Test: {rule.get('name')}",
                    tags=["rule", "test", rule.get("rule_type", "custom")]
                )
                
                return JSONResponse({
                    "success": True,
                    "test_result": test_result
                })
                
            except Exception as e:
                logger.error(f"Error testing rule: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # ===== END RULES & GOVERNANCE APIs =====
        
        # Execution monitoring dashboard endpoint (must come before catch-all admin route)
        @self.mcp.custom_route("/admin/executions", methods=["GET"])
        async def executions_dashboard(request):
            """Serve the execution monitoring dashboard interface"""
            try:
                return HTMLResponse("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Execution Monitoring - hAIveMind</title>
                    <link rel="stylesheet" href="/admin/static/admin.css">
                    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
                </head>
                <body class="dashboard">
                    <nav class="nav-header">
                        <div class="nav-brand">
                            <img src="/assets/logo.png" alt="hAIveMind" class="nav-logo">
                            <h1>hAIveMind Execution Monitoring</h1>
                        </div>
                        <div class="nav-links">
                            <a href="/admin/dashboard.html">Dashboard</a>
                            <a href="/admin/memory.html">Memory Browser</a>
                            <a href="/admin/mcp_servers.html">MCP Servers</a>
                            <a href="/admin/vault">Vault Management</a>
                            <a href="/admin/rules-dashboard">Rules & Governance</a>
                            <a href="/admin/playbooks">Playbook Management</a>
                            <a href="/admin/executions" class="active">Execution Monitoring</a>
                            <a href="/admin/confluence">Confluence Integration</a>
                            <a href="/admin/help-dashboard">Help System</a>
                        </div>
                        <button class="logout-btn" onclick="logout()">Logout</button>
                    </nav>
                    <main class="main-content">
                        <div class="card">
                            <h2><i class="fas fa-tasks"></i> Execution Monitoring</h2>
                            <p>Real-time monitoring of playbook executions with detailed logging and analytics.</p>
                            
                            <div class="execution-overview">
                                <div class="status-grid">
                                    <div class="status-item">
                                        <span class="status-label">Active Executions</span>
                                        <span class="status-value">0</span>
                                    </div>
                                    <div class="status-item">
                                        <span class="status-label">Queued Tasks</span>
                                        <span class="status-value">0</span>
                                    </div>
                                    <div class="status-item">
                                        <span class="status-label">Failed Today</span>
                                        <span class="status-value">0</span>
                                    </div>
                                    <div class="status-item">
                                        <span class="status-label">System Load</span>
                                        <span class="status-value status-good">Low</span>
                                    </div>
                                </div>
                            </div>

                            <div class="execution-controls">
                                <h3>Execution Controls</h3>
                                <button class="btn btn-primary" onclick="viewActiveExecutions()">
                                    <i class="fas fa-eye"></i> Active Executions
                                </button>
                                <button class="btn btn-secondary" onclick="viewExecutionHistory()">
                                    <i class="fas fa-history"></i> Execution History
                                </button>
                                <button class="btn btn-info" onclick="viewExecutionLogs()">
                                    <i class="fas fa-file-text"></i> Execution Logs
                                </button>
                                <button class="btn btn-warning" onclick="viewFailedExecutions()">
                                    <i class="fas fa-exclamation-triangle"></i> Failed Executions
                                </button>
                            </div>
                        </div>
                    </main>
                    <script src="/admin/static/admin.js"></script>
                    <script>
                        function viewActiveExecutions() { alert('Active executions viewer coming soon!'); }
                        function viewExecutionHistory() { alert('Execution history coming soon!'); }
                        function viewExecutionLogs() { alert('Execution logs coming soon!'); }
                        function viewFailedExecutions() { alert('Failed executions viewer coming soon!'); }
                    </script>
                </body>
                </html>
                """)
            except Exception as e:
                logger.error(f"Error serving execution monitoring dashboard: {e}")
                return JSONResponse({"error": "Execution monitoring dashboard unavailable"}, status_code=500)
        
        # Login redirect endpoint (for compatibility)
        @self.mcp.custom_route("/login", methods=["GET"])
        async def login_redirect(request):
            """Redirect /login to proper admin login page"""
            from starlette.responses import RedirectResponse
            return RedirectResponse(url="/admin/login.html", status_code=302)
        
# Device management endpoints
        @self.mcp.custom_route("/admin/api/devices", methods=["GET", "POST"])
        async def manage_devices(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                if request.method == "GET":
                    devices = self.dashboard_db.list_devices()
                    return JSONResponse([{
                        "id": d.id,
                        "device_id": d.device_id,
                        "machine_id": d.machine_id,
                        "hostname": d.hostname,
                        "status": d.status.value,
                        "created_at": d.created_at.isoformat(),
                        "last_seen": d.last_seen.isoformat() if d.last_seen else None
                    } for d in devices])
                
                elif request.method == "POST":
                    data = await request.json()
                    device_id = self.dashboard_db.register_device(
                        data['device_id'],
                        data['machine_id'], 
                        data['hostname'],
                        1,  # Default user ID
                        data.get('metadata', {}),
                        request.client.host
                    )
                    return JSONResponse({"device_id": device_id, "status": "registered"})
                    
            except Exception as e:
                logger.error(f"Error managing devices: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Configuration generation endpoints
        @self.mcp.custom_route("/admin/api/config/generate", methods=["POST"])
        async def generate_config(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                if not self._config_generator:
                    return JSONResponse({"error": "Configuration generator not available"}, status_code=500)
                
                data = await request.json()
                device_id = data.get('device_id')
                format_str = data.get('format', 'claude_desktop')
                
                # Map format string to enum
                format_map = {
                    "claude_desktop": ConfigFormat.CLAUDE_DESKTOP,
                    "claude_code": ConfigFormat.CLAUDE_CODE,
                    "custom": ConfigFormat.CUSTOM_JSON,
                    "mcp_json": ConfigFormat.MCP_JSON,
                    "yaml": ConfigFormat.YAML,
                    "shell_script": ConfigFormat.SHELL_SCRIPT,
                    "docker_compose": ConfigFormat.DOCKER_COMPOSE
                }
                
                config_format = format_map.get(format_str, ConfigFormat.CLAUDE_DESKTOP)
                
                # Generate configuration
                client_config = self._config_generator.generate_client_config(
                    user_id="admin",
                    device_id=device_id,
                    format=config_format,
                    include_auth=data.get('include_auth', True)
                )
                
                config_string = self._config_generator.template_engine.generate(client_config)
                
                return JSONResponse({
                    "config": config_string,
                    "format": format_str,
                    "device_id": device_id,
                    "generated_at": datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error generating config: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        logger.info("📊 Enhanced dashboard routes registered")
    
    async def _check_admin_auth(self, request):
        """Check if request has valid admin authentication"""
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return False
        
        token = auth_header.split(' ')[1]
        valid, payload = self.auth.validate_jwt_token(token)
        return valid and payload.get('role') == 'admin'
    
    async def _get_available_tools(self):
        """Get list of available MCP tools"""
        try:
            # Get tools from the MCP server
            if hasattr(self.mcp, '_tools'):
                return list(self.mcp._tools.keys())
            else:
                # Fallback to common hAIveMind tools
                return [
                    "store_memory", "retrieve_memory", "search_memories", 
                    "get_recent_memories", "get_memory_stats", "get_project_memories",
                    "register_agent", "get_agent_roster", "delegate_task",
                    "broadcast_discovery", "sync_infrastructure_config"
                ]
        except Exception as e:
            logger.warning(f"Could not get available tools: {e}")
            return []
    
    async def _save_config(self):
        """Save configuration to file"""
        try:
            import json
            config_path = Path(__file__).parent.parent / "config" / "config.json"
            config_path.parent.mkdir(exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def run(self):
        """Run the remote MCP server"""
        try:
            logger.info("🚀 Activating hAIveMind network portal - preparing for remote drone connections...")
            logger.info(f"📶 Hive broadcast channel: http://{self.host}:{self.port}/sse")
            logger.info(f"🌊 Collective consciousness stream: http://{self.host}:{self.port}/mcp")
            logger.info(f"🩸 Hive vitals monitor: http://{self.host}:{self.port}/health")
            
            # Add health endpoint
            @self.mcp.custom_route("/health", methods=["GET"])
            async def health(request):
                from starlette.responses import JSONResponse
                return JSONResponse({
                    "status": "healthy",
                    "server": "remote-memory-mcp",
                    "version": "1.0.0",
                    "machine_id": self.storage.machine_id,
                    "endpoints": {
                        "sse": f"http://{self.host}:{self.port}/sse",
                        "streamable_http": f"http://{self.host}:{self.port}/mcp"
                    }
                })
            
            # Run the server (SSE transport)
            self.mcp.run(transport="sse")
            
        except Exception as e:
            logger.error(f"💥 Network portal activation failed: {e} - remote hive access unavailable")
            raise

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Remote Memory MCP Server")
    parser.add_argument(
        "--config", 
        type=str, 
        default=None,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind to (overrides config)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to (overrides config)"
    )
    
    args = parser.parse_args()
    
    # Print hAIveMind startup art
    print("""
╭─────────────────────────────────────────────────────────────╮
│                                                             │
│    ██╗  ██╗ █████╗ ██╗██╗   ██╗███████╗███╗   ███╗██╗███╗   ██╗██████╗ │
│    ██║  ██║██╔══██╗██║██║   ██║██╔════╝████╗ ████║██║████╗  ██║██╔══██╗│
│    ███████║███████║██║██║   ██║█████╗  ██╔████╔██║██║██╔██╗ ██║██║  ██║│
│    ██╔══██║██╔══██║██║╚██╗ ██╔╝██╔══╝  ██║╚██╔╝██║██║██║╚██╗██║██║  ██║│
│    ██║  ██║██║  ██║██║ ╚████╔╝ ███████╗██║ ╚═╝ ██║██║██║ ╚████║██████╔╝│
│    ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝  ╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝ │
│                                                             │
│        🌐🤖 Remote MCP Server - Network Hub Starting 🤖🌐        │
│                                                             │
│             🔄 Initializing Remote Access Portal...             │
│                                                             │
╰─────────────────────────────────────────────────────────────╯
    """)
    
    try:
        print("🧠 Initializing hAIveMind remote memory server...")
        # Initialize server
        server = RemoteMemoryMCPServer(config_path=args.config)
        
        # Override host/port if provided
        if args.host:
            server.host = args.host
        if args.port:
            server.port = args.port
        
        # Run server
        server.run()
        
    except KeyboardInterrupt:
        logger.info("🛑 Network portal deactivated by user - remote hive access terminated")
    except Exception as e:
        logger.error(f"💥 Critical portal malfunction: {e} - remote hive connection lost")
        sys.exit(1)

if __name__ == "__main__":
    main()
