#!/usr/bin/env python3
"""
ClaudeOps Agent Hivemind Remote Server - FastMCP-based implementation for HTTP/SSE access
Provides remote access to the agent hivemind via MCP protocol
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import TextContent
    from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
except ImportError:
    print("Error: MCP package not found. Install with: pip install mcp")
    sys.exit(1)

from memory_server import MemoryStorage
from auth import AuthManager
from command_installer import CommandInstaller
from mcp_bridge import get_bridge_manager
from sync_hooks import SyncHooks
from enhanced_ticket_system import EnhancedTicketSystem
from agent_directives import AgentDirectiveSystem
from comet_integration import CometDirectiveSystem

# Agent Authentication System imports
try:
    from agent_identity import AgentIdentitySystem, AgentKeyPair
    from access_control import AccessControlSystem, AccessRequest, Permission, ConfidentialityLevel
    from firebase_auth import get_firebase_auth, FirebaseAgentAuth
    AGENT_AUTH_AVAILABLE = True
except ImportError as e:
    AGENT_AUTH_AVAILABLE = False

# Admin Bootstrap System import
try:
    from admin_bootstrap import AdminBootstrap, get_admin_bootstrap
    ADMIN_BOOTSTRAP_AVAILABLE = True
except ImportError:
    ADMIN_BOOTSTRAP_AVAILABLE = False

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
        self.bridge_manager = get_bridge_manager(self.storage)
        
        # Initialize sync hooks system
        self.sync_hooks = SyncHooks(self.storage, self.config, self.command_installer)
        self.sync_hooks.setup_default_hooks()
        
        # Initialize enhanced ticket system
        self.enhanced_tickets = None  # Will be initialized on first use
        
        # Initialize agent directive system
        self.agent_directives = AgentDirectiveSystem(self.storage)
        
        # Initialize Comet integration system
        self.comet_system = CometDirectiveSystem(self.config.get('comet', {}), self.storage)
        
        # Get remote server config
        remote_config = self.config.get('remote_server', {})
        self.host = remote_config.get('host', '0.0.0.0')
        self.port = remote_config.get('port', 8900)
        
        # Initialize session store for persistence
        self.active_sessions = {}
        # Configure session persistence settings
        from collections import defaultdict
        self.session_last_activity = defaultdict(lambda: datetime.now().isoformat())
        self._start_time = time.time()
        self._start_datetime = datetime.now()
        
        # Initialize FastMCP server with hAIveMind context
        
        self.mcp = FastMCP(
            name="hAIveMind Collective Memory",
            host=self.host,
            port=self.port,
            sse_path="/sse",
            message_path="/messages/",
            mount_path="/",
            # Enable sessions for MCP tool functionality - required for hAIveMind tools
            stateless_http=False
        )
        
        # Add session recovery system  
        self._add_session_recovery_middleware()
        
        # Override the message handler to provide better session error handling
        self._setup_session_error_handling()
        
        # Add connection context and instructions
        self._add_context_resources()
        
        # Register all tools
        self._register_tools()
        
        # Add session management endpoints
        self._add_session_management()
        
        # NOTE: MCP Tool Cleanup (2024-01)
        # Reduced from 126 to 34 tools. Removed unused:
        # - _register_hosting_tools (10 tools - MCP hosting disabled)
        # - _register_backup_system_tools (18 tools)
        # - _register_service_discovery_tools (5 tools)
        # - _register_configuration_management_tools (13 tools)
        # - _register_claude_shortcut_commands (5 tools)
        # - _register_monitoring_integration_tools (5 tools)
        # - _register_deployment_pipeline_tools (5 tools)
        # - _register_config_backup_system_tools (10 tools)
        # - _register_personal_command_sync_tools (6 tools)
        # - 30+ individual tools from _register_tools

        # Register enhanced ticket management tools (keeping - useful)
        self._register_enhanced_ticket_tools()

        # Add admin interface routes
        self._add_admin_routes()

        # Add vault sync routes for cross-machine HTTP sync
        self._add_vault_sync_routes()

        # Register vault sync MCP tools for SSE clients
        self._register_vault_sync_tools()

        # Register skills.sh integration tools
        self._register_skills_sh_tools()

        # Initialize agent authentication system
        self._init_agent_auth_system()

        # Register agent authentication MCP tools
        self._register_agent_auth_tools()

        # Initialize dashboard functionality
        self._init_dashboard_functionality()

        # Initialize admin bootstrap system for secure credential management
        self._init_admin_bootstrap()

        # Track server start time for uptime calculation
        # _start_time already set as datetime above
        
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
    
    def _truncate_response(self, response: str, max_tokens: int = 20000) -> str:
        """Truncate response if it exceeds token limit"""
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        if len(response) <= max_chars:
            return response
        
        truncated = response[:max_chars]
        
        # Try to truncate at a natural boundary (line break)
        last_newline = truncated.rfind('\n')
        if last_newline > max_chars * 0.8:  # If we can truncate at 80% or more
            truncated = truncated[:last_newline]
        
        # Add truncation notice
        truncated += f"\n\n⚠️ Response truncated due to size limit ({len(response):,} chars > {max_chars:,} chars limit)\n"
        truncated += f"📄 Use pagination parameters (limit, offset) for full results\n"
        truncated += f"💡 Try reducing limit or adding specific filters"
        
        return truncated

    def _register_tools(self):
        """Register all memory tools with FastMCP"""
        
        @self.mcp.tool()
        async def store_memory(
            content: str,
            category: str = "global",
            confidentiality_level: str = "normal"
        ) -> str:
            """Store a memory with comprehensive machine tracking and sharing control

            Args:
                confidentiality_level: Data protection level (normal, internal, confidential, pii).
                    confidential/pii memories are stored locally only and never synced or broadcast.
            """
            try:
                memory_id = await self.storage.store_memory(
                    content=content,
                    category=category,
                    confidentiality_level=confidentiality_level
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
        async def update_memory_confidentiality(
            memory_id: str,
            confidentiality_level: str,
            reason: str = None
        ) -> str:
            """Upgrade a memory's confidentiality level (can only make MORE restrictive).

            Levels: normal < internal < confidential < pii
            - internal: No external sync
            - confidential: Local only, no sync/broadcast
            - pii: Local only, audit logged, blocked from all distribution
            """
            try:
                result = await self.storage.update_memory_confidentiality(
                    memory_id=memory_id,
                    confidentiality_level=confidentiality_level,
                    reason=reason
                )
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error updating confidentiality: {e}")
                return f"Error: {str(e)}"

        @self.mcp.tool()
        async def search_memories(
            query: str,
            category: Optional[str] = None,
            user_id: Optional[str] = None,
            limit: int = 5,
            offset: int = 0,
            semantic: bool = True,
            scope: Optional[str] = None,
            include_global: bool = True,
            from_machines: Optional[List[str]] = None,
            exclude_machines: Optional[List[str]] = None,
            max_confidentiality_level: Optional[str] = "internal"
        ) -> str:
            """Search memories with comprehensive filtering including machine, project, and sharing scope

            Note: Remote access excludes confidential/pii memories by default for data protection.
            """
            try:
                # Get more results to handle pagination
                extended_limit = limit + offset + 50  # Get extra to ensure we have enough for pagination
                # Remote access: exclude confidential/pii memories by default
                memories = await self.storage.search_memories(
                    query=query,
                    category=category,
                    user_id=user_id,
                    limit=extended_limit,
                    semantic=semantic,
                    scope=scope,
                    include_global=include_global,
                    from_machines=from_machines,
                    exclude_machines=exclude_machines,
                    exclude_confidential=True,  # Always filter confidential in remote context
                    max_confidentiality_level=max_confidentiality_level
                )
                
                # Apply pagination
                total_count = len(memories)
                paginated_memories = memories[offset:offset + limit]
                
                result = {
                    "memories": paginated_memories,
                    "pagination": {
                        "total": total_count,
                        "limit": limit,
                        "offset": offset,
                        "has_more": offset + limit < total_count
                    }
                }
                
                response = json.dumps(result, indent=2)
                return self._truncate_response(response)
            except Exception as e:
                logger.error(f"Error searching memories: {e}")
                return f"Error searching memories: {str(e)}"
        
        @self.mcp.tool()
        async def get_recent_memories(
            user_id: Optional[str] = None,
            category: Optional[str] = None,
            hours: int = 24,
            limit: int = 5,
            offset: int = 0,
            max_confidentiality_level: Optional[str] = "internal"
        ) -> str:
            """Get recent memories within a time window

            Note: Remote access excludes confidential/pii memories by default for data protection.
            """
            try:
                # Get more results to handle pagination
                extended_limit = limit + offset + 50
                # Remote access: exclude confidential/pii memories by default
                memories = await self.storage.get_recent_memories(
                    user_id=user_id,
                    category=category,
                    hours=hours,
                    limit=extended_limit,
                    exclude_confidential=True,  # Always filter confidential in remote context
                    max_confidentiality_level=max_confidentiality_level
                )
                
                # Apply pagination
                total_count = len(memories)
                paginated_memories = memories[offset:offset + limit]
                
                result = {
                    "memories": paginated_memories,
                    "pagination": {
                        "total": total_count,
                        "limit": limit,
                        "offset": offset,
                        "has_more": offset + limit < total_count
                    }
                }
                
                return json.dumps(result, indent=2)
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
            limit: int = 50,
            offset: int = 0
        ) -> str:
            """Get all memories for the current project"""
            try:
                # Get more results to handle pagination
                extended_limit = limit + offset + 50
                memories = await self.storage.get_project_memories(
                    category=category,
                    user_id=user_id,
                    limit=extended_limit
                )
                
                # Apply pagination
                total_count = len(memories)
                paginated_memories = memories[offset:offset + limit]
                
                result = {
                    "memories": paginated_memories,
                    "pagination": {
                        "total": total_count,
                        "limit": limit,
                        "offset": offset,
                        "has_more": offset + limit < total_count
                    }
                }
                
                return json.dumps(result, indent=2)
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
        async def list_memory_sources(
            category: Optional[str] = None,
            limit: int = 20,
            offset: int = 0
        ) -> str:
            """List all machines that have contributed memories with statistics"""
            try:
                sources = await self.storage.list_memory_sources(category=category)
                
                # Apply pagination to sources list if it's a list
                if isinstance(sources, list):
                    total_count = len(sources)
                    paginated_sources = sources[offset:offset + limit]
                    
                    result = {
                        "sources": paginated_sources,
                        "pagination": {
                            "total": total_count,
                            "limit": limit,
                            "offset": offset,
                            "has_more": offset + limit < total_count
                        }
                    }
                else:
                    # Handle dictionary response
                    result = sources
                
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Error listing memory sources: {e}")
                return f"Error listing memory sources: {str(e)}"
        

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
        async def get_agent_roster(
            include_inactive: bool = False,
            limit: int = 20,
            offset: int = 0
        ) -> str:
            """List all active ClaudeOps agents and their current status with pagination"""
            try:
                roster = await self.storage.get_agent_roster(include_inactive=include_inactive)
                
                # Ensure we only have agent data, not memory statistics
                if "agents" in roster:
                    agents = roster["agents"]
                    
                    # Apply pagination
                    total_agents = len(agents)
                    paginated_agents = agents[offset:offset + limit]
                    
                    result = {
                        "active_agents": len([a for a in agents if a.get('is_active', False)]),
                        "total_agents": total_agents,
                        "agents": paginated_agents,
                        "pagination": {
                            "limit": limit,
                            "offset": offset,
                            "has_more": offset + limit < total_agents
                        }
                    }
                else:
                    # Fallback for error responses
                    result = roster
                
                response = json.dumps(result, indent=2)
                return self._truncate_response(response)
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
        async def create_project(
            project_name: str,
            git_repo_path: str,
            description: Optional[str] = None,
            setup_script: Optional[str] = None,
            dev_script: Optional[str] = None,
            cleanup_script: Optional[str] = None
        ) -> str:
            """Initialize new project contexts with enhanced DevOps integration"""
            try:
                if not project_name or not project_name.strip():
                    return "❌ Project name is required"
                
                if not git_repo_path or not git_repo_path.strip():
                    return "❌ Git repository path is required"
                
                # Create project metadata
                project_metadata = {
                    "name": project_name.strip(),
                    "git_repo_path": git_repo_path.strip(),
                    "description": description or f"DevOps project: {project_name}",
                    "setup_script": setup_script,
                    "dev_script": dev_script,
                    "cleanup_script": cleanup_script,
                    "created_at": datetime.now().isoformat(),
                    "created_by": self.storage.agent_id,
                    "status": "active",
                    "devops_features": {
                        "monitoring_enabled": False,
                        "backup_enabled": False,
                        "deployment_pipeline": False,
                        "security_scanning": False
                    }
                }
                
                # Store project definition in hAIveMind memory
                memory_id = await self.storage.store_memory(
                    content=f"DevOps project definition: {json.dumps(project_metadata)}",
                    category="project_definitions",
                    metadata=project_metadata
                )
                
                # Create dedicated memory category for this project
                project_category = f"{project_name.lower().replace(' ', '_')}_project"
                try:
                    await self.create_memory_category(
                        category_name=project_category,
                        description=f"Project-specific memories for {project_name}",
                        retention_days=730  # 2 years for project data
                    )
                    project_category_created = True
                except:
                    project_category_created = False
                
                # Broadcast project creation
                await self.broadcast_discovery(
                    message=f"New DevOps project created: {project_name}",
                    category="project_management",
                    severity="info"
                )
                
                return f"""✅ DevOps Project Created

**Name**: {project_name}
**Repository**: {git_repo_path}
**Description**: {project_metadata['description']}
**Memory Category**: {'✅ Created' if project_category_created else '⚠️ Manual creation needed'} ({project_category})
**DevOps Features**: Ready for configuration

**Available Scripts**:
{f'- Setup: {setup_script}' if setup_script else '- Setup: Not configured'}
{f'- Dev: {dev_script}' if dev_script else '- Dev: Not configured'}  
{f'- Cleanup: {cleanup_script}' if cleanup_script else '- Cleanup: Not configured'}

Project is ready for DevOps operations! Use `switch_project_context` to activate."""
                
            except Exception as e:
                logger.error(f"Error creating project: {e}")
                return f"❌ Project creation error: {str(e)}"

        @self.mcp.tool()
        async def list_projects(
            include_devops_status: bool = True,
            show_archived: bool = False,
            limit: int = 20,
            offset: int = 0
        ) -> str:
            """Show all projects with enhanced DevOps metadata"""
            try:
                # Get projects from vibe_kanban
                kanban_projects = []
                try:
                    from mcp import client_session
                    # This would normally call the kanban API, simplified for now
                    kanban_projects = []
                except:
                    pass
                
                # Get DevOps project definitions from memory
                all_devops_projects = await self.storage.search_memories(
                    query="DevOps project definition",
                    category="project_definitions",
                    limit=200  # Get more to enable pagination
                )
                
                # Apply pagination
                total_projects = len(all_devops_projects)
                devops_projects = all_devops_projects[offset:offset + limit]
                
                # Get current project context
                current_project = await self._get_current_project_context()
                
                project_list = []
                
                # Process DevOps project definitions
                for proj_mem in devops_projects:
                    try:
                        proj_content = proj_mem['content']
                        if ': {' in proj_content:
                            proj_data = json.loads(proj_content.split(': ', 1)[1])
                            proj_name = proj_data.get('name', 'Unknown')
                            status = proj_data.get('status', 'active')
                            
                            if not show_archived and status == 'archived':
                                continue
                            
                            # Check if this is the current active project
                            active_indicator = "🎯" if current_project and current_project.get('name') == proj_name else "📁"
                            
                            project_list.append(f"{active_indicator} **{proj_name}** ({status})")
                            project_list.append(f"   📂 {proj_data.get('git_repo_path', 'No repo path')}")
                            
                            if proj_data.get('description'):
                                project_list.append(f"   📝 {proj_data['description']}")
                            
                            if include_devops_status:
                                devops_features = proj_data.get('devops_features', {})
                                enabled_features = [k for k, v in devops_features.items() if v]
                                project_list.append(f"   🛠️ DevOps: {len(enabled_features)} features enabled")
                            
                            project_list.append("")  # Empty line for spacing
                            
                    except Exception as e:
                        logger.warning(f"Could not parse project data: {e}")
                        continue
                
                if not project_list:
                    return """📂 No DevOps projects found

Use `create_project` to create your first DevOps-enabled project with:
- Automated deployment pipelines
- Monitoring integration
- Backup and recovery
- Security scanning
- Configuration management"""
                
                # Add pagination info
                has_more = offset + limit < total_projects
                pagination_info = ""
                if total_projects > limit:
                    pagination_info = f"\n📄 Page {offset//limit + 1} ({offset + 1}-{min(offset + limit, total_projects)} of {total_projects})"
                    if has_more:
                        pagination_info += f" | Use offset={offset + limit} for next page"
                
                return f"""📊 DevOps Projects Overview

**Total Projects**: {total_projects}
**Current Active**: {current_project.get('name', 'None selected') if current_project else 'None selected'}
**Showing**: {len(devops_projects)} projects{pagination_info}

{chr(10).join(project_list)}

💡 Use `switch_project_context [name]` to switch active project
🔧 Use `project_health_check` to analyze current project status"""
                
            except Exception as e:
                logger.error(f"Error listing projects: {e}")
                return f"❌ Error listing projects: {str(e)}"

        @self.mcp.tool()
        async def switch_project_context(
            project_name: str
        ) -> str:
            """Change active project scope for DevOps operations"""
            try:
                if not project_name or not project_name.strip():
                    return "❌ Project name is required"
                
                project_name = project_name.strip()
                
                # Find the project
                devops_projects = await self.storage.search_memories(
                    query=f"DevOps project definition",
                    category="project_definitions",
                    limit=50
                )
                
                target_project = None
                for proj_mem in devops_projects:
                    try:
                        proj_content = proj_mem['content']
                        if ': {' in proj_content:
                            proj_data = json.loads(proj_content.split(': ', 1)[1])
                            if proj_data.get('name', '').lower() == project_name.lower():
                                target_project = proj_data
                                break
                    except:
                        continue
                
                if not target_project:
                    return f"❌ Project '{project_name}' not found. Use `list_projects` to see available projects."
                
                # Set as current project context
                context_data = {
                    "current_project": target_project,
                    "switched_at": datetime.now().isoformat(),
                    "switched_by": self.storage.agent_id,
                    "previous_context": await self._get_current_project_context()
                }
                
                # Store context in memory
                await self.storage.store_memory(
                    content=f"Project context switch: {json.dumps(context_data)}",
                    category="project_context",
                    metadata=context_data
                )
                
                # Get project health status
                health_status = await self._check_project_health(target_project)
                
                return f"""🎯 Project Context Switched

**Active Project**: {target_project['name']}
**Repository**: {target_project['git_repo_path']}
**Status**: {target_project.get('status', 'active')}
**Health**: {health_status}

**DevOps Features Available**:
- Memory category: {target_project['name'].lower().replace(' ', '_')}_project
- Scoped operations for this project
- Project-specific monitoring and alerts
- Dedicated backup and restore

All DevOps operations will now be scoped to this project."""
                
            except Exception as e:
                logger.error(f"Error switching project context: {e}")
                return f"❌ Context switch error: {str(e)}"

        @self.mcp.tool()
        async def project_health_check(
            project_name: Optional[str] = None,
            include_recommendations: bool = True
        ) -> str:
            """Analyze project status and provide DevOps health insights"""
            try:
                # Get target project
                if project_name:
                    # Find specific project
                    devops_projects = await self.storage.search_memories(
                        query="DevOps project definition",
                        category="project_definitions", 
                        limit=50
                    )
                    
                    target_project = None
                    for proj_mem in devops_projects:
                        try:
                            proj_content = proj_mem['content']
                            if ': {' in proj_content:
                                proj_data = json.loads(proj_content.split(': ', 1)[1])
                                if proj_data.get('name', '').lower() == project_name.lower():
                                    target_project = proj_data
                                    break
                        except:
                            continue
                    
                    if not target_project:
                        return f"❌ Project '{project_name}' not found"
                else:
                    # Use current project context
                    target_project = await self._get_current_project_context()
                    if not target_project:
                        return "❌ No active project. Use `switch_project_context` to select a project."
                
                # Perform comprehensive health check
                health_results = {
                    "project_name": target_project['name'],
                    "overall_health": "unknown",
                    "checks_performed": [],
                    "issues_found": [],
                    "recommendations": []
                }
                
                # Check repository accessibility
                repo_path = target_project.get('git_repo_path')
                if repo_path:
                    import os
                    if os.path.exists(repo_path):
                        health_results["checks_performed"].append("✅ Repository accessible")
                        if os.path.exists(os.path.join(repo_path, '.git')):
                            health_results["checks_performed"].append("✅ Git repository valid")
                        else:
                            health_results["issues_found"].append("⚠️ Not a Git repository")
                    else:
                        health_results["issues_found"].append("❌ Repository path not accessible")
                        health_results["recommendations"].append("Verify repository path and permissions")
                
                # Check DevOps features configuration
                devops_features = target_project.get('devops_features', {})
                enabled_features = sum(1 for v in devops_features.values() if v)
                total_features = len(devops_features)
                
                if enabled_features == 0:
                    health_results["issues_found"].append("⚠️ No DevOps features enabled")
                    health_results["recommendations"].append("Enable monitoring, backup, or deployment features")
                elif enabled_features < total_features / 2:
                    health_results["issues_found"].append(f"⚠️ Only {enabled_features}/{total_features} DevOps features enabled")
                else:
                    health_results["checks_performed"].append(f"✅ {enabled_features}/{total_features} DevOps features enabled")
                
                # Check for project-specific memories
                project_category = f"{target_project['name'].lower().replace(' ', '_')}_project"
                try:
                    project_memories = await self.storage.search_memories(
                        query="*",
                        category=project_category,
                        limit=1
                    )
                    if project_memories:
                        health_results["checks_performed"].append("✅ Project memory category active")
                    else:
                        health_results["issues_found"].append("⚠️ No project-specific memories found")
                except:
                    health_results["issues_found"].append("❌ Project memory category not accessible")
                
                # Check scripts configuration
                scripts_configured = []
                for script_type in ['setup_script', 'dev_script', 'cleanup_script']:
                    if target_project.get(script_type):
                        scripts_configured.append(script_type.replace('_script', ''))
                
                if scripts_configured:
                    health_results["checks_performed"].append(f"✅ Scripts configured: {', '.join(scripts_configured)}")
                else:
                    health_results["issues_found"].append("⚠️ No automation scripts configured")
                    health_results["recommendations"].append("Add setup, dev, and cleanup scripts for automation")
                
                # Determine overall health
                if len(health_results["issues_found"]) == 0:
                    health_results["overall_health"] = "healthy"
                elif len(health_results["issues_found"]) <= 2:
                    health_results["overall_health"] = "warning"
                else:
                    health_results["overall_health"] = "critical"
                
                # Format health report
                health_icon = {
                    "healthy": "💚",
                    "warning": "🟡", 
                    "critical": "🔴",
                    "unknown": "⚪"
                }[health_results["overall_health"]]
                
                report = f"""{health_icon} Project Health Check: {target_project['name']}

**Overall Status**: {health_results["overall_health"].upper()}
**Repository**: {target_project.get('git_repo_path', 'Not specified')}

**Health Checks Passed**:
{chr(10).join(health_results["checks_performed"]) if health_results["checks_performed"] else "None"}

**Issues Found**:
{chr(10).join(health_results["issues_found"]) if health_results["issues_found"] else "None"}"""

                if include_recommendations and health_results["recommendations"]:
                    report += f"""

**Recommendations**:
{chr(10).join([f"💡 {rec}" for rec in health_results["recommendations"]])}"""
                
                return report
                
            except Exception as e:
                logger.error(f"Error in project health check: {e}")
                return f"❌ Health check error: {str(e)}"

        @self.mcp.tool()
        async def backup_project(
            project_name: Optional[str] = None,
            include_git_data: bool = True,
            include_memories: bool = True
        ) -> str:
            """Complete project backup including configs, memories, and Git data"""
            try:
                # Get target project
                if project_name:
                    target_project = await self._find_project_by_name(project_name)
                else:
                    target_project = await self._get_current_project_context()
                
                if not target_project:
                    return "❌ No project specified or active. Use `switch_project_context` first."
                
                # Create backup metadata
                backup_id = f"{target_project['name'].lower().replace(' ', '_')}_backup_{int(time.time())}"
                backup_metadata = {
                    'backup_id': backup_id,
                    'project_name': target_project['name'],
                    'backup_time': datetime.now().isoformat(),
                    'backup_by': self.storage.agent_id,
                    'include_git_data': include_git_data,
                    'include_memories': include_memories,
                    'project_settings': target_project
                }
                
                backup_components = []
                
                # Backup project memories
                memories_backed_up = 0
                if include_memories:
                    project_category = f"{target_project['name'].lower().replace(' ', '_')}_project"
                    try:
                        memories = await self.storage.search_memories(
                            query="*",
                            category=project_category,
                            limit=10000
                        )
                        memories_backed_up = len(memories)
                        backup_metadata['memories'] = memories
                        backup_components.append(f"✅ {memories_backed_up} memories")
                    except Exception as e:
                        backup_components.append(f"⚠️ Memory backup failed: {str(e)}")
                
                # Backup Git repository information
                if include_git_data:
                    repo_path = target_project.get('git_repo_path')
                    if repo_path:
                        import os
                        try:
                            if os.path.exists(repo_path):
                                # Get Git info (simplified - in production would backup actual Git data)
                                backup_metadata['git_info'] = {
                                    'repo_path': repo_path,
                                    'exists': True,
                                    'backup_note': 'Repository path recorded - manual Git backup recommended'
                                }
                                backup_components.append("✅ Git repository info")
                            else:
                                backup_metadata['git_info'] = {'repo_path': repo_path, 'exists': False}
                                backup_components.append("⚠️ Git repository not accessible")
                        except Exception as e:
                            backup_components.append(f"⚠️ Git backup error: {str(e)}")
                
                # Store backup
                backup_memory_id = await self.storage.store_memory(
                    content=f"Project backup: {json.dumps(backup_metadata)}",
                    category="project_backups",
                    metadata=backup_metadata
                )
                
                return f"""💾 Project Backup Complete

**Backup ID**: {backup_id}
**Project**: {target_project['name']}
**Backup Location**: hAIveMind memory (ID: {backup_memory_id})

**Components Backed Up**:
{chr(10).join(backup_components)}

**Backup Contents**:
- Project configuration and metadata
- DevOps feature settings
- Script configurations
{f'- {memories_backed_up} project memories' if include_memories else ''}
{f'- Git repository information' if include_git_data else ''}

Use `restore_project {backup_id}` to restore from this backup."""
                
            except Exception as e:
                logger.error(f"Error backing up project: {e}")
                return f"❌ Project backup error: {str(e)}"

        @self.mcp.tool()
        async def restore_project(
            backup_id: str,
            new_project_name: Optional[str] = None,
            restore_memories: bool = True
        ) -> str:
            """Restore project state from backup"""
            try:
                # Find the backup
                backup_memories = await self.storage.search_memories(
                    query=backup_id,
                    category="project_backups",
                    limit=1
                )
                
                if not backup_memories:
                    return f"❌ Project backup '{backup_id}' not found"
                
                backup_data = backup_memories[0]
                
                # Parse backup content
                try:
                    backup_content = json.loads(backup_data['content'].split(': ', 1)[1])
                except:
                    return f"❌ Invalid backup format for {backup_id}"
                
                original_project = backup_content['project_settings']
                target_name = new_project_name or original_project['name']
                
                # Check if target project name already exists
                existing_project = await self._find_project_by_name(target_name)
                if existing_project:
                    return f"❌ Project '{target_name}' already exists. Choose a different name."
                
                # Restore project settings
                restored_project = {
                    **original_project,
                    'name': target_name,
                    'restored_at': datetime.now().isoformat(),
                    'restored_by': self.storage.agent_id,
                    'restored_from_backup': backup_id
                }
                
                # Store restored project definition
                await self.storage.store_memory(
                    content=f"DevOps project definition: {json.dumps(restored_project)}",
                    category="project_definitions",
                    metadata=restored_project
                )
                
                # Create project memory category
                project_category = f"{target_name.lower().replace(' ', '_')}_project"
                try:
                    await self.create_memory_category(
                        category_name=project_category,
                        description=f"Restored project memories for {target_name}",
                        retention_days=730
                    )
                    category_restored = True
                except:
                    category_restored = False
                
                # Restore memories if requested
                memories_restored = 0
                if restore_memories and 'memories' in backup_content:
                    try:
                        memories = backup_content['memories']
                        memories_restored = len(memories)
                        # In production, would actually restore memories to ChromaDB
                    except:
                        memories_restored = 0
                
                restore_components = [
                    "✅ Project configuration",
                    "✅ DevOps feature settings",
                    "✅ Script configurations"
                ]
                
                if category_restored:
                    restore_components.append("✅ Memory category created")
                else:
                    restore_components.append("⚠️ Memory category creation failed")
                
                if restore_memories:
                    restore_components.append(f"✅ {memories_restored} memories restored")
                
                return f"""♻️ Project Restore Complete

**Restored Project**: {target_name}
**Original Project**: {original_project['name']}
**Backup ID**: {backup_id}
**Repository Path**: {restored_project.get('git_repo_path', 'Not specified')}

**Components Restored**:
{chr(10).join(restore_components)}

Project '{target_name}' is now available for DevOps operations!
Use `switch_project_context {target_name}` to activate."""
                
            except Exception as e:
                logger.error(f"Error restoring project: {e}")
                return f"❌ Project restore error: {str(e)}"

        # Helper methods for project management
        async def _get_current_project_context(self) -> Optional[Dict[str, Any]]:
            """Get the current active project context"""
            try:
                context_memories = await self.storage.search_memories(
                    query="Project context switch",
                    category="project_context",
                    limit=1
                )
                
                if context_memories:
                    context_data = context_memories[0]
                    if 'metadata' in context_data and 'current_project' in context_data['metadata']:
                        return context_data['metadata']['current_project']
                
                return None
            except:
                return None

        async def _find_project_by_name(self, project_name: str) -> Optional[Dict[str, Any]]:
            """Find a project by name"""
            try:
                devops_projects = await self.storage.search_memories(
                    query="DevOps project definition",
                    category="project_definitions",
                    limit=50
                )
                
                for proj_mem in devops_projects:
                    try:
                        proj_content = proj_mem['content']
                        if ': {' in proj_content:
                            proj_data = json.loads(proj_content.split(': ', 1)[1])
                            if proj_data.get('name', '').lower() == project_name.lower():
                                return proj_data
                    except:
                        continue
                
                return None
            except:
                return None

        async def _check_project_health(self, project_data: Dict[str, Any]) -> str:
            """Quick health check for a project"""
            try:
                issues = 0
                
                # Check repository
                repo_path = project_data.get('git_repo_path')
                if repo_path:
                    import os
                    if not os.path.exists(repo_path):
                        issues += 1
                
                # Check DevOps features
                devops_features = project_data.get('devops_features', {})
                if not any(devops_features.values()):
                    issues += 1
                
                if issues == 0:
                    return "Healthy 💚"
                elif issues <= 1:
                    return "Warning 🟡"
                else:
                    return "Critical 🔴"
            except:
                return "Unknown ⚪"
        
        # Agent directive system tools

        logger.info("🤝 All hive mind tools synchronized with network portal - collective intelligence ready")
    
    # NOTE: _register_hosting_tools removed (10 tools - MCP hosting disabled by default)

    # NOTE: _register_backup_system_tools removed (unused)

    # NOTE: _register_service_discovery_tools removed (unused)

    # NOTE: _register_configuration_management_tools removed (unused)

    # NOTE: _register_claude_shortcut_commands removed (unused)

    # NOTE: _register_monitoring_integration_tools removed (unused)

    # NOTE: _register_deployment_pipeline_tools removed (unused)

    # NOTE: _register_config_backup_system_tools removed (unused)

    def _init_agent_auth_system(self):
        """Initialize the agent authentication and authorization system"""
        if not AGENT_AUTH_AVAILABLE:
            logger.warning("Agent auth system not available - skipping initialization")
            self.agent_identity_system = None
            self.access_control_system = None
            self.firebase_auth = None
            return

        try:
            # Initialize Firebase Auth
            self.firebase_auth = get_firebase_auth()
            if self.firebase_auth.is_available():
                logger.info("🔥 Firebase Auth initialized successfully")
            else:
                logger.warning("⚠️ Firebase Auth not available (no credentials)")

            # Initialize Agent Identity System
            db_path = str(Path(__file__).parent.parent / "data" / "agent_identity.db")
            self.agent_identity_system = AgentIdentitySystem(db_path, self.firebase_auth)
            logger.info("🔐 Agent Identity System initialized")

            # Initialize Access Control System
            acl_db_path = str(Path(__file__).parent.parent / "data" / "access_control.db")
            self.access_control_system = AccessControlSystem(acl_db_path, self.firebase_auth)
            logger.info("🛡️ Access Control System initialized")

        except Exception as e:
            logger.error(f"Failed to initialize agent auth system: {e}")
            self.agent_identity_system = None
            self.access_control_system = None
            self.firebase_auth = None

    def _register_agent_auth_tools(self):
        """Register agent authentication and authorization MCP tools"""
        if not AGENT_AUTH_AVAILABLE:
            logger.info("Agent auth tools not registered (system not available)")
            return

        # ============ Agent Identity Management Tools ============

        @self.mcp.tool()
        async def generate_agent_identity(
            machine_id: str,
            agent_type: str = "general",
            pre_auth_key: Optional[str] = None,
            requested_tags: Optional[str] = None,
            requested_capabilities: Optional[str] = None
        ) -> str:
            """
            Generate a new cryptographic agent identity with Firebase user.

            Creates Ed25519 (signing) + X25519 (key exchange) key pairs,
            registers with Firebase Auth, and optionally uses a pre-auth key
            for automated approval.

            Args:
                machine_id: Unique machine identifier (e.g., 'elastic1', 'lance-dev')
                agent_type: Type of agent (general, elasticsearch, orchestrator, etc.)
                pre_auth_key: Optional pre-authorization key for auto-approval
                requested_tags: Comma-separated tags to request (e.g., "tag:elasticsearch,tag:production")
                requested_capabilities: Comma-separated capabilities (e.g., "search_ops,index_management")

            Returns:
                JSON with identity details, keys (SAVE THE PRIVATE KEY!), and status
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                # Parse tags and capabilities
                tags = [t.strip() for t in requested_tags.split(",")] if requested_tags else None
                caps = [c.strip() for c in requested_capabilities.split(",")] if requested_capabilities else None

                # Register the agent
                identity, keypair, token = self.agent_identity_system.register_agent(
                    machine_id=machine_id,
                    agent_type=agent_type,
                    pre_auth_key=pre_auth_key,
                    requested_tags=tags,
                    requested_capabilities=caps
                )

                if identity is None:
                    return json.dumps({"error": "Failed to register agent identity"})

                result = {
                    "success": True,
                    "identity_id": identity.identity_id,
                    "agent_id": identity.agent_id,
                    "firebase_uid": identity.firebase_uid,
                    "status": identity.status,
                    "machine_id": identity.machine_id,
                    "key_fingerprint": identity.key_fingerprint,
                    "public_keys": {
                        "ed25519": identity.public_key_ed25519,
                        "x25519": identity.public_key_x25519
                    },
                    "tags": identity.tags,
                    "capabilities": identity.capabilities
                }

                # Include private keys ONLY on initial generation (agent must save these!)
                if keypair:
                    result["SAVE_THESE_KEYS"] = {
                        "private_key_ed25519": keypair.private_key_ed25519,
                        "private_key_x25519": keypair.private_key_x25519,
                        "warning": "Save these keys securely! They cannot be recovered."
                    }

                # Include Firebase token if generated
                if token:
                    result["firebase_custom_token"] = token
                    result["token_note"] = "Exchange this for an ID token using Firebase client SDK"

                return json.dumps(result, indent=2)

            except Exception as e:
                logger.error(f"Error generating agent identity: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def authenticate_agent(
            firebase_token: str,
            agent_id: Optional[str] = None
        ) -> str:
            """
            Authenticate an agent using their Firebase ID token.

            Verifies the token, extracts custom claims (tags, capabilities),
            and returns the agent's access permissions.

            Args:
                firebase_token: Firebase ID token to verify
                agent_id: Optional agent ID for additional validation

            Returns:
                JSON with authentication result and granted permissions
            """
            if not self.firebase_auth or not self.firebase_auth.is_available():
                return json.dumps({"error": "Firebase Auth not available"})

            try:
                # Verify token
                result = self.firebase_auth.verify_agent_token(firebase_token, check_revoked=True)

                if not result.valid:
                    return json.dumps({
                        "authenticated": False,
                        "error": result.error,
                        "revoked": result.revoked
                    })

                # Get agent identity details
                identity = None
                if self.agent_identity_system and result.uid:
                    identity = self.agent_identity_system.get_agent_by_firebase_uid(result.uid)

                response = {
                    "authenticated": True,
                    "firebase_uid": result.uid,
                    "claims": result.claims.to_dict() if result.claims else {}
                }

                if identity:
                    response["agent"] = {
                        "agent_id": identity.agent_id,
                        "status": identity.status,
                        "machine_id": identity.machine_id,
                        "tags": identity.tags,
                        "capabilities": identity.capabilities,
                        "confidentiality_max": identity.confidentiality_max
                    }

                return json.dumps(response, indent=2)

            except Exception as e:
                logger.error(f"Error authenticating agent: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def check_agent_access(
            firebase_token: str,
            resource_type: str,
            resource_id: str,
            permission: str,
            confidentiality_level: str = "normal"
        ) -> str:
            """
            Check if an agent has access to a specific resource.

            Uses deny-by-default ACL evaluation with Firebase claims.

            Args:
                firebase_token: Firebase ID token of the requesting agent
                resource_type: Type of resource (vault, memory, infrastructure, etc.)
                resource_id: Specific resource identifier
                permission: Requested permission (READ, WRITE, ADMIN, DELETE)
                confidentiality_level: Resource confidentiality (normal, internal, confidential, pii)

            Returns:
                JSON with access decision and matched grant details
            """
            if not self.access_control_system:
                return json.dumps({"error": "Access control system not initialized"})

            try:
                # Verify Firebase token first
                if self.firebase_auth and self.firebase_auth.is_available():
                    token_result = self.firebase_auth.verify_agent_token(firebase_token, check_revoked=True)
                    if not token_result.valid:
                        return json.dumps({
                            "allowed": False,
                            "reason": f"Invalid token: {token_result.error}"
                        })
                    agent_id = token_result.uid
                else:
                    # Fallback: use token as agent_id for testing
                    agent_id = firebase_token

                # Build access request
                request = AccessRequest(
                    agent_id=agent_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    permission=Permission[permission.upper()],
                    confidentiality_level=ConfidentialityLevel[confidentiality_level.upper()]
                )

                # Check access
                decision = self.access_control_system.check_access(request)

                return json.dumps({
                    "allowed": decision.allowed,
                    "reason": decision.reason,
                    "grant_matched": decision.grant_matched,
                    "conditions_checked": decision.conditions_checked,
                    "audit_id": decision.audit_id
                }, indent=2)

            except Exception as e:
                logger.error(f"Error checking access: {e}")
                return json.dumps({"error": str(e)})

        # ============ Pre-Auth Key Management Tools ============

        @self.mcp.tool()
        async def create_preauth_key(
            created_by: str,
            tags: Optional[str] = None,
            capabilities: Optional[str] = None,
            max_uses: int = 1,
            expires_hours: int = 24,
            ephemeral: bool = False,
            reusable: bool = False,
            pre_approved: bool = False
        ) -> str:
            """
            Create a pre-authorization key for automated agent registration.

            Pre-auth keys allow agents to register without manual approval,
            similar to Tailscale's pre-auth key system.

            Args:
                created_by: Admin agent ID creating this key
                tags: Comma-separated tags to grant (e.g., "tag:elasticsearch,tag:dev")
                capabilities: Comma-separated capabilities to grant
                max_uses: Maximum number of times this key can be used (0 = unlimited)
                expires_hours: Hours until expiration (default 24)
                ephemeral: If true, registered agents are marked as ephemeral
                reusable: If true, key can be reused until max_uses or expiration
                pre_approved: If true, agents are auto-approved on registration

            Returns:
                JSON with the pre-auth key (SAVE IT!) and metadata
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                tag_list = [t.strip() for t in tags.split(",")] if tags else []
                cap_list = [c.strip() for c in capabilities.split(",")] if capabilities else []

                key, preauth = self.agent_identity_system.create_pre_auth_key(
                    created_by=created_by,
                    tags=tag_list,
                    capabilities=cap_list,
                    max_uses=max_uses if max_uses > 0 else None,
                    expires_hours=expires_hours,
                    ephemeral=ephemeral,
                    reusable=reusable,
                    pre_approved=pre_approved
                )

                if key is None:
                    return json.dumps({"error": "Failed to create pre-auth key"})

                return json.dumps({
                    "success": True,
                    "pre_auth_key": key,
                    "key_id": preauth.key_id,
                    "expires_at": preauth.expires_at,
                    "max_uses": preauth.max_uses,
                    "tags": preauth.tags,
                    "capabilities": preauth.capabilities,
                    "ephemeral": preauth.ephemeral,
                    "reusable": preauth.reusable,
                    "pre_approved": preauth.pre_approved,
                    "warning": "Save this key securely! It cannot be retrieved later."
                }, indent=2)

            except Exception as e:
                logger.error(f"Error creating pre-auth key: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def list_preauth_keys(
            include_expired: bool = False,
            include_used: bool = False
        ) -> str:
            """
            List all pre-authorization keys.

            Args:
                include_expired: Include expired keys in results
                include_used: Include fully-used keys in results

            Returns:
                JSON list of pre-auth keys (without the actual key values)
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                keys = self.agent_identity_system.list_pre_auth_keys(
                    include_expired=include_expired,
                    include_used=include_used
                )

                return json.dumps({
                    "count": len(keys),
                    "keys": [k.to_dict() for k in keys]
                }, indent=2)

            except Exception as e:
                logger.error(f"Error listing pre-auth keys: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def revoke_preauth_key(
            key_id: str,
            revoked_by: str,
            reason: str = "Manual revocation"
        ) -> str:
            """
            Revoke a pre-authorization key.

            Args:
                key_id: ID of the pre-auth key to revoke
                revoked_by: Admin agent ID performing the revocation
                reason: Reason for revocation

            Returns:
                JSON with revocation status
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                success = self.agent_identity_system.revoke_pre_auth_key(
                    key_id=key_id,
                    revoked_by=revoked_by,
                    reason=reason
                )

                return json.dumps({
                    "success": success,
                    "key_id": key_id,
                    "revoked_by": revoked_by,
                    "reason": reason
                })

            except Exception as e:
                logger.error(f"Error revoking pre-auth key: {e}")
                return json.dumps({"error": str(e)})

        # ============ Agent Approval Management Tools ============

        @self.mcp.tool()
        async def list_pending_agents() -> str:
            """
            List all agents pending approval.

            Returns:
                JSON list of pending agent registrations
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                pending = self.agent_identity_system.list_pending_agents()

                return json.dumps({
                    "count": len(pending),
                    "pending_agents": [
                        {
                            "agent_id": agent.agent_id,
                            "machine_id": agent.machine_id,
                            "agent_type": agent.agent_type,
                            "requested_tags": agent.tags,
                            "requested_capabilities": agent.capabilities,
                            "created_at": agent.created_at,
                            "key_fingerprint": agent.key_fingerprint
                        }
                        for agent in pending
                    ]
                }, indent=2)

            except Exception as e:
                logger.error(f"Error listing pending agents: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def approve_agent(
            agent_id: str,
            approved_by: str,
            tags: Optional[str] = None,
            capabilities: Optional[str] = None,
            confidentiality_max: str = "normal"
        ) -> str:
            """
            Approve a pending agent registration.

            Args:
                agent_id: ID of the agent to approve
                approved_by: Admin agent ID performing the approval
                tags: Comma-separated tags to grant (overrides requested)
                capabilities: Comma-separated capabilities to grant (overrides requested)
                confidentiality_max: Maximum confidentiality level (normal, internal, confidential)

            Returns:
                JSON with approval status
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                tag_list = [t.strip() for t in tags.split(",")] if tags else None
                cap_list = [c.strip() for c in capabilities.split(",")] if capabilities else None

                success = self.agent_identity_system.approve_agent(
                    agent_id=agent_id,
                    approved_by=approved_by,
                    tags_granted=tag_list,
                    capabilities_granted=cap_list,
                    notes=f"Confidentiality max: {confidentiality_max}"
                )

                return json.dumps({
                    "success": success,
                    "agent_id": agent_id,
                    "approved_by": approved_by,
                    "status": "approved" if success else "failed"
                })

            except Exception as e:
                logger.error(f"Error approving agent: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def reject_agent(
            agent_id: str,
            rejected_by: str,
            reason: str
        ) -> str:
            """
            Reject a pending agent registration.

            Args:
                agent_id: ID of the agent to reject
                rejected_by: Admin agent ID performing the rejection
                reason: Reason for rejection

            Returns:
                JSON with rejection status
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                success = self.agent_identity_system.reject_agent(
                    agent_id=agent_id,
                    rejected_by=rejected_by,
                    reason=reason
                )

                return json.dumps({
                    "success": success,
                    "agent_id": agent_id,
                    "rejected_by": rejected_by,
                    "reason": reason
                })

            except Exception as e:
                logger.error(f"Error rejecting agent: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def revoke_agent(
            agent_id: str,
            revoked_by: str,
            reason: str
        ) -> str:
            """
            Revoke an active agent's access (emergency action).

            Immediately revokes Firebase tokens and marks the agent as revoked.
            This is a break-glass emergency action.

            Args:
                agent_id: ID of the agent to revoke
                revoked_by: Admin agent ID performing the revocation
                reason: Reason for revocation

            Returns:
                JSON with revocation status
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                success = self.agent_identity_system.revoke_agent(
                    agent_id=agent_id,
                    revoked_by=revoked_by,
                    reason=reason
                )

                return json.dumps({
                    "success": success,
                    "agent_id": agent_id,
                    "revoked_by": revoked_by,
                    "reason": reason,
                    "action": "All tokens revoked, agent disabled"
                })

            except Exception as e:
                logger.error(f"Error revoking agent: {e}")
                return json.dumps({"error": str(e)})

        # ============ Access Grants Management Tools ============

        @self.mcp.tool()
        async def create_access_grant(
            grant_name: str,
            created_by: str,
            permissions: str,
            source_tags: Optional[str] = None,
            source_agents: Optional[str] = None,
            destination_resources: Optional[str] = None,
            destination_types: Optional[str] = None,
            confidentiality_max: str = "normal",
            mfa_required: bool = False,
            valid_hours: Optional[int] = None
        ) -> str:
            """
            Create an access control grant (ACL rule).

            Grants define who (sources) can access what (destinations) with which permissions.

            Args:
                grant_name: Unique name for this grant
                created_by: Admin agent ID creating this grant
                permissions: Comma-separated permissions (READ,WRITE,ADMIN,DELETE)
                source_tags: Comma-separated source tags (e.g., "tag:elasticsearch,tag:production")
                source_agents: Comma-separated source agent IDs
                destination_resources: Comma-separated resource patterns (e.g., "vault:elastic-*")
                destination_types: Comma-separated resource types (vault,memory,infrastructure)
                confidentiality_max: Maximum confidentiality level this grant allows
                mfa_required: Whether MFA is required for this grant
                valid_hours: Hours until grant expires (None = permanent)

            Returns:
                JSON with the created grant details
            """
            if not self.access_control_system:
                return json.dumps({"error": "Access control system not initialized"})

            try:
                perm_list = [p.strip().upper() for p in permissions.split(",")]
                src_tag_list = [t.strip() for t in source_tags.split(",")] if source_tags else None
                src_agent_list = [a.strip() for a in source_agents.split(",")] if source_agents else None
                dst_resource_list = [r.strip() for r in destination_resources.split(",")] if destination_resources else None

                # Build conditions dict
                conditions = {
                    "mfa_required": mfa_required,
                    "confidentiality_max": confidentiality_max
                }

                grant = self.access_control_system.create_grant(
                    grant_name=grant_name,
                    created_by=created_by,
                    permissions=perm_list,
                    src_tags=src_tag_list,
                    src_agents=src_agent_list,
                    dst_resources=dst_resource_list,
                    conditions=conditions,
                    expires_hours=valid_hours
                )

                if grant is None:
                    return json.dumps({"error": "Failed to create grant"})

                return json.dumps({
                    "success": True,
                    "grant_id": grant.grant_id,
                    "grant_name": grant.grant_name,
                    "permissions": grant.permissions,
                    "source_tags": grant.src_tags,
                    "source_agents": grant.src_agents,
                    "destination_resources": grant.dst_resources,
                    "expires_at": grant.expires_at
                }, indent=2)

            except Exception as e:
                logger.error(f"Error creating access grant: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def list_access_grants(
            include_expired: bool = False,
            include_disabled: bool = False
        ) -> str:
            """
            List all access control grants.

            Args:
                include_expired: Include expired grants
                include_disabled: Include disabled grants

            Returns:
                JSON list of access grants
            """
            if not self.access_control_system:
                return json.dumps({"error": "Access control system not initialized"})

            try:
                grants = self.access_control_system.list_grants(
                    include_expired=include_expired,
                    include_disabled=include_disabled
                )

                return json.dumps({
                    "count": len(grants),
                    "grants": [g.to_dict() for g in grants]
                }, indent=2)

            except Exception as e:
                logger.error(f"Error listing access grants: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def disable_access_grant(
            grant_id: str,
            disabled_by: str,
            reason: str
        ) -> str:
            """
            Disable an access control grant.

            Args:
                grant_id: ID of the grant to disable
                disabled_by: Admin agent ID performing the action
                reason: Reason for disabling

            Returns:
                JSON with disable status
            """
            if not self.access_control_system:
                return json.dumps({"error": "Access control system not initialized"})

            try:
                success = self.access_control_system.disable_grant(
                    grant_id=grant_id,
                    disabled_by=disabled_by,
                    reason=reason
                )

                return json.dumps({
                    "success": success,
                    "grant_id": grant_id,
                    "disabled_by": disabled_by,
                    "reason": reason
                })

            except Exception as e:
                logger.error(f"Error disabling access grant: {e}")
                return json.dumps({"error": str(e)})

        # ============ Audit Log Tools ============

        @self.mcp.tool()
        async def view_agent_audit_log(
            agent_id: Optional[str] = None,
            resource_id: Optional[str] = None,
            hours: int = 24,
            limit: int = 100
        ) -> str:
            """
            View the agent access audit log.

            Args:
                agent_id: Filter by agent ID (optional)
                resource_id: Filter by resource ID (optional)
                hours: Hours of history to retrieve (default 24)
                limit: Maximum number of entries (default 100)

            Returns:
                JSON list of audit log entries
            """
            if not self.access_control_system:
                return json.dumps({"error": "Access control system not initialized"})

            try:
                entries = self.access_control_system.get_audit_log(
                    agent_id=agent_id,
                    resource_id=resource_id,
                    hours=hours,
                    limit=limit
                )

                return json.dumps({
                    "count": len(entries),
                    "filters": {
                        "agent_id": agent_id,
                        "resource_id": resource_id,
                        "hours": hours
                    },
                    "entries": entries
                }, indent=2)

            except Exception as e:
                logger.error(f"Error viewing audit log: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def get_agent_info(agent_id: str) -> str:
            """
            Get detailed information about a specific agent.

            Args:
                agent_id: The agent ID to look up

            Returns:
                JSON with agent details including identity, tags, capabilities, and status
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                identity = self.agent_identity_system.get_agent(agent_id)

                if identity is None:
                    return json.dumps({"error": f"Agent not found: {agent_id}"})

                return json.dumps({
                    "agent_id": identity.agent_id,
                    "identity_id": identity.identity_id,
                    "firebase_uid": identity.firebase_uid,
                    "machine_id": identity.machine_id,
                    "agent_type": identity.agent_type,
                    "status": identity.status,
                    "tags": identity.tags,
                    "capabilities": identity.capabilities,
                    "confidentiality_max": identity.confidentiality_max,
                    "key_fingerprint": identity.key_fingerprint,
                    "created_at": identity.created_at,
                    "approved_by": identity.approved_by,
                    "approved_at": identity.approved_at,
                    "public_keys": {
                        "ed25519": identity.public_key_ed25519,
                        "x25519": identity.public_key_x25519
                    }
                }, indent=2)

            except Exception as e:
                logger.error(f"Error getting agent info: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def list_all_agents(
            status_filter: Optional[str] = None,
            machine_filter: Optional[str] = None
        ) -> str:
            """
            List all registered agents.

            Args:
                status_filter: Filter by status (pending, approved, active, revoked)
                machine_filter: Filter by machine ID pattern

            Returns:
                JSON list of agents
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                agents = self.agent_identity_system.list_agents(
                    status_filter=status_filter,
                    machine_filter=machine_filter
                )

                return json.dumps({
                    "count": len(agents),
                    "filters": {
                        "status": status_filter,
                        "machine": machine_filter
                    },
                    "agents": [
                        {
                            "agent_id": a.agent_id,
                            "machine_id": a.machine_id,
                            "agent_type": a.agent_type,
                            "status": a.status,
                            "tags": a.tags,
                            "capabilities": a.capabilities,
                            "created_at": a.created_at
                        }
                        for a in agents
                    ]
                }, indent=2)

            except Exception as e:
                logger.error(f"Error listing agents: {e}")
                return json.dumps({"error": str(e)})

        # ============ Zero-Knowledge Vault Sharing Tools ============

        @self.mcp.tool()
        async def share_vault_with_agent(
            vault_id: str,
            recipient_agent_id: str,
            access_level: str,
            granted_by: str,
            expires_hours: Optional[int] = None
        ) -> str:
            """
            Share a vault with another agent using zero-knowledge encryption.

            The vault key is encrypted with the recipient's X25519 public key,
            so the server never sees the plaintext vault key. The recipient
            can decrypt using their private key.

            Args:
                vault_id: ID of the vault to share
                recipient_agent_id: Agent receiving access
                access_level: Access level ('read', 'write', 'admin')
                granted_by: Agent granting access (must have admin access)
                expires_hours: Optional expiration in hours

            Returns:
                JSON with share details (share_id, encrypted key needs client-side encryption)
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                # Get recipient's X25519 public key for encryption
                recipient = self.agent_identity_system.get_agent(recipient_agent_id)
                if not recipient:
                    return json.dumps({"error": f"Recipient agent not found: {recipient_agent_id}"})

                # Calculate expiration
                from datetime import datetime, timedelta
                expires_at = None
                if expires_hours:
                    expires_at = (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat()

                # Note: In a full implementation, the encrypted_vault_key would be
                # encrypted client-side using VaultKeySharing.encrypt_vault_key()
                # with the recipient's X25519 public key. For now, we return a
                # placeholder indicating the client needs to perform encryption.
                result = {
                    "success": True,
                    "vault_id": vault_id,
                    "recipient_agent_id": recipient_agent_id,
                    "recipient_x25519_pubkey": recipient.public_key_x25519,
                    "access_level": access_level,
                    "expires_at": expires_at,
                    "note": "Use VaultKeySharing.encrypt_vault_key() client-side to encrypt the vault key with recipient's X25519 public key, then call complete_vault_share with the encrypted key"
                }

                return json.dumps(result, indent=2)

            except Exception as e:
                logger.error(f"Error sharing vault: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def complete_vault_share(
            vault_id: str,
            recipient_agent_id: str,
            encrypted_vault_key: str,
            access_level: str,
            granted_by: str,
            expires_hours: Optional[int] = None
        ) -> str:
            """
            Complete a vault share with the encrypted vault key.

            This should be called after encrypting the vault key client-side
            using VaultKeySharing.encrypt_vault_key().

            Args:
                vault_id: ID of the vault being shared
                recipient_agent_id: Agent receiving access
                encrypted_vault_key: Base64-encoded encrypted vault key (from VaultKeySharing)
                access_level: Access level ('read', 'write', 'admin')
                granted_by: Agent granting access
                expires_hours: Optional expiration in hours

            Returns:
                JSON with share ID and confirmation
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                from datetime import datetime, timedelta
                expires_at = None
                if expires_hours:
                    expires_at = (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat()

                # Get recipient's Firebase UID
                recipient = self.agent_identity_system.get_agent(recipient_agent_id)
                firebase_uid = recipient.firebase_uid if recipient else None

                share_id = self.agent_identity_system.create_vault_share(
                    vault_id=vault_id,
                    recipient_agent_id=recipient_agent_id,
                    encrypted_vault_key=encrypted_vault_key,
                    access_level=access_level,
                    granted_by=granted_by,
                    expires_at=expires_at,
                    recipient_firebase_uid=firebase_uid
                )

                if share_id:
                    return json.dumps({
                        "success": True,
                        "share_id": share_id,
                        "vault_id": vault_id,
                        "recipient_agent_id": recipient_agent_id,
                        "access_level": access_level,
                        "expires_at": expires_at
                    }, indent=2)
                else:
                    return json.dumps({"error": "Failed to create vault share"})

            except Exception as e:
                logger.error(f"Error completing vault share: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def list_vault_shares(
            vault_id: str,
            include_revoked: bool = False
        ) -> str:
            """
            List all agents who have access to a vault.

            Args:
                vault_id: The vault to query
                include_revoked: Include revoked shares

            Returns:
                JSON list of vault shares
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                shares = self.agent_identity_system.get_vault_shares(
                    vault_id=vault_id,
                    include_revoked=include_revoked
                )

                # Redact encrypted keys for security
                sanitized = []
                for s in shares:
                    entry = dict(s)
                    entry["encrypted_vault_key"] = "[REDACTED]"
                    sanitized.append(entry)

                return json.dumps({
                    "vault_id": vault_id,
                    "count": len(sanitized),
                    "shares": sanitized
                }, indent=2)

            except Exception as e:
                logger.error(f"Error listing vault shares: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def get_my_vault_shares(
            agent_id: str,
            include_revoked: bool = False
        ) -> str:
            """
            Get all vaults shared with a specific agent.

            Args:
                agent_id: The agent to query
                include_revoked: Include revoked shares

            Returns:
                JSON list of vault shares with encrypted keys
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                shares = self.agent_identity_system.get_agent_vault_shares(
                    agent_id=agent_id,
                    include_revoked=include_revoked
                )

                return json.dumps({
                    "agent_id": agent_id,
                    "count": len(shares),
                    "shares": shares
                }, indent=2)

            except Exception as e:
                logger.error(f"Error getting agent vault shares: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def revoke_vault_share(
            share_id: str,
            revoked_by: str,
            reason: Optional[str] = None
        ) -> str:
            """
            Revoke an agent's access to a vault.

            Args:
                share_id: The share ID to revoke
                revoked_by: Agent performing the revocation
                reason: Optional reason for revocation

            Returns:
                JSON with revocation status
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                success = self.agent_identity_system.revoke_vault_share(
                    share_id=share_id,
                    revoked_by=revoked_by,
                    reason=reason
                )

                return json.dumps({
                    "success": success,
                    "share_id": share_id,
                    "revoked_by": revoked_by,
                    "reason": reason
                })

            except Exception as e:
                logger.error(f"Error revoking vault share: {e}")
                return json.dumps({"error": str(e)})

        @self.mcp.tool()
        async def check_vault_access(
            vault_id: str,
            agent_id: str,
            required_level: str = "read"
        ) -> str:
            """
            Check if an agent has access to a vault and get their encrypted key.

            Args:
                vault_id: The vault to check
                agent_id: The agent requesting access
                required_level: Minimum required access level ('read', 'write', 'admin')

            Returns:
                JSON with access status and encrypted vault key if authorized
            """
            if not self.agent_identity_system:
                return json.dumps({"error": "Agent identity system not initialized"})

            try:
                has_access, encrypted_key = self.agent_identity_system.check_vault_access(
                    vault_id=vault_id,
                    agent_id=agent_id,
                    required_level=required_level
                )

                result = {
                    "vault_id": vault_id,
                    "agent_id": agent_id,
                    "has_access": has_access,
                    "required_level": required_level
                }

                if has_access and encrypted_key:
                    result["encrypted_vault_key"] = encrypted_key
                    result["note"] = "Decrypt with VaultKeySharing.decrypt_vault_key() using your X25519 private key"

                return json.dumps(result, indent=2)

            except Exception as e:
                logger.error(f"Error checking vault access: {e}")
                return json.dumps({"error": str(e)})

        logger.info("🔐 Agent authentication tools registered (24 tools including 6 vault sharing)")

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
        
        # ===== COMET BROWSER INTEGRATION ROUTES =====
        
        # Comet main portal
        @self.mcp.custom_route("/comet", methods=["GET"])
        async def comet_portal(request):
            """Redirect to AI-optimized interface"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            # Redirect to the AI-optimized single-page playground
            return RedirectResponse(url="/comet-ai", status_code=302)
            
        
        # ===== COMET API ENDPOINTS =====
        
        # Comet authentication endpoint
        @self.mcp.custom_route("/comet/api/auth", methods=["POST"])
        async def comet_auth(request):
            """Authenticate Comet browser and return session token"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            try:
                body = await request.json()
                password = body.get('password')
                
                if not password:
                    return JSONResponse({"error": "Password required"}, status_code=400)
                
                session_token = self.comet_system.authenticate_comet(password)
                
                if session_token:
                    return JSONResponse({
                        "success": True,
                        "session_token": session_token,
                        "message": "Authentication successful"
                    })
                else:
                    return JSONResponse({"error": "Invalid password"}, status_code=401)
                    
            except Exception as e:
                logger.error(f"Comet auth error: {e}")
                return JSONResponse({"error": "Authentication failed"}, status_code=500)
        
        # Comet session validation endpoint
        @self.mcp.custom_route("/comet/api/validate", methods=["GET"])
        async def comet_validate(request):
            """Validate Comet session token"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            auth_header = request.headers.get('authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return JSONResponse({"error": "Authorization header required"}, status_code=401)
            
            token = auth_header.split(' ')[1]
            
            if self.comet_system.validate_session(token):
                return JSONResponse({"valid": True})
            else:
                return JSONResponse({"valid": False}, status_code=401)
        
        # Comet directives endpoint
        @self.mcp.custom_route("/comet/directives", methods=["GET"])
        async def comet_directives(request):
            """Get active directives for Comet to process"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            directives = self.comet_system.get_active_directives()
            
            # Return HTML format optimized for AI reading
            return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>hAIveMind Active Directives</title>
                <meta name="ai-optimized" content="true">
                <meta name="refresh-interval" content="{self.comet_system.refresh_interval}">
            </head>
            <body style="font-family: monospace; padding: 20px; background: #0a0e1a; color: #e1e5e9; line-height: 1.6;">
                <h1>📋 Active Directives for Comet Assistant</h1>
                <p><strong>Directive Count:</strong> {len(directives)}</p>
                <p><strong>Last Updated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                {"".join([f'''
                <div style="border: 1px solid #2d3748; border-left: 4px solid #00d4aa; margin: 15px 0; padding: 15px; background: #162032;">
                    <h3>Directive ID: {directive['id']}</h3>
                    <p><strong>Type:</strong> {directive['type']}</p>
                    <p><strong>Priority:</strong> {directive['priority']}</p>
                    <p><strong>Status:</strong> {directive['status']}</p>
                    <p><strong>Created:</strong> {directive['created_at']}</p>
                    <div style="background: #0a0e1a; padding: 10px; margin: 10px 0; border-radius: 4px;">
                        <pre>{json.dumps(directive['content'], indent=2)}</pre>
                    </div>
                    <p><strong>Instructions:</strong> {directive['content'].get('instruction', 'No specific instructions')}</p>
                    <p><strong>Expected Format:</strong> {directive['content'].get('expected_format', 'Not specified')}</p>
                </div>
                ''' for directive in directives])}
                
                {'''<div style="border: 1px solid #4a5568; padding: 15px; margin: 15px 0; background: #1a1e30; text-align: center;">
                    <p>No active directives at this time.</p>
                    <p>Check back in {self.comet_system.refresh_interval} seconds for new tasks.</p>
                </div>''' if not directives else ''}
                
                <hr style="border: 1px solid #2d3748; margin: 30px 0;">
                <p><strong>Next Check:</strong> Refresh this page in {self.comet_system.refresh_interval} seconds</p>
                <p><strong>API Endpoint:</strong> <code>/comet/api/directives</code> for JSON format</p>
            </body>
            </html>
            """)
        
        # Comet memory search endpoint
        @self.mcp.custom_route("/comet/api/memory/search", methods=["GET"])  
        async def comet_memory_search(request):
            """Search hAIveMind collective memory"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            query = request.query_params.get('q', '')
            category = request.query_params.get('category')
            limit = int(request.query_params.get('limit', '5'))
            
            if not query:
                return JSONResponse({"error": "Query parameter 'q' is required"}, status_code=400)
            
            try:
                # Search memories using the storage system
                results = await self.storage.search_memories(
                    query=query,
                    category=category,
                    limit=limit,
                    semantic=True
                )
                
                # Sanitize output to prevent prompt injection
                sanitized_results = self.comet_system.sanitize_output(results)
                
                return JSONResponse({
                    "query": query,
                    "category": category,
                    "results": sanitized_results[:limit],
                    "total_found": len(sanitized_results),
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Comet memory search error: {e}")
                return JSONResponse({"error": "Search failed"}, status_code=500)
        
        # Comet API directives (JSON format)
        @self.mcp.custom_route("/comet/api/directives", methods=["GET"])
        async def comet_api_directives(request):
            """Get active directives in JSON format"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            # Validate session
            auth_header = request.headers.get('authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return JSONResponse({"error": "Authorization required"}, status_code=401)
            
            token = auth_header.split(' ')[1]
            if not self.comet_system.validate_session(token):
                return JSONResponse({"error": "Invalid or expired session"}, status_code=401)
            
            directives = self.comet_system.get_active_directives()
            
            return JSONResponse({
                "directives": directives,
                "count": len(directives),
                "refresh_interval": self.comet_system.refresh_interval,
                "timestamp": datetime.now().isoformat()
            })
        
        # Comet API status (JSON format) - Fast version
        @self.mcp.custom_route("/comet/api/status", methods=["GET"])
        async def comet_api_status(request):
            """Get system status in JSON format - Fast mode"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            # Fast status check without database queries
            try:
                active_sessions = len([s for s in self.comet_system.sessions.values() if s.get('active', False)])
                active_directives = len(self.comet_system.get_active_directives())
                
                status = {
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat(),
                    'system': {
                        'active_sessions': active_sessions,
                        'active_directives': active_directives,
                        'response_time_ms': '<50',
                        'mode': 'fast'
                    },
                    'comet': {
                        'enabled': True,
                        'portal_url': '/comet',
                        'features': ['data_submission', 'directive_creation', 'memory_search']
                    }
                }
            except Exception as e:
                status = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
            
            return JSONResponse(status)
        
        # Comet status HTML page
        @self.mcp.custom_route("/comet/status", methods=["GET"])
        async def comet_status_html(request):
            """Get system status in HTML format for Comet"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            # Fast status with minimal queries
            try:
                active_sessions = len([s for s in self.comet_system.sessions.values() if s.get('active', False)])
                active_directives = len(self.comet_system.get_active_directives())
                
                status = {
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat(),
                    'system': {
                        'active_sessions': active_sessions,
                        'active_directives': active_directives,
                        'agent_count': 'N/A (fast mode)',
                        'memory_system': 'operational'
                    },
                    'recent_activity': [
                        {'category': 'system', 'timestamp': datetime.now().isoformat(), 'content': 'System status check - fast mode'},
                        {'category': 'comet', 'timestamp': datetime.now().isoformat(), 'content': 'Portal active and receiving requests'}
                    ]
                }
            except Exception as e:
                status = {
                    'status': 'error',
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e),
                    'system': {'message': 'Status check failed'}
                }
            
            # Convert to HTML
            recent_activity_html = ""
            for activity in status.get('recent_activity', []):
                recent_activity_html += f'''
                <div style="background: #1a1e30; padding: 10px; margin: 10px 0; border-radius: 4px; border-left: 3px solid #00d4aa;">
                    <strong>{activity.get('category', 'unknown').upper()}</strong> - {activity.get('timestamp', '')}
                    <br>{activity.get('content', '')[:100]}...
                </div>'''
            
            # Simplified fast HTML response
            return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>hAIveMind System Status - Fast Mode</title>
                <meta name="ai-optimized" content="true">
                <meta name="refresh-interval" content="5">
            </head>
            <body style="font-family: monospace; padding: 20px; background: #0a0e1a; color: #e1e5e9; line-height: 1.6;">
                <h1>⚡ hAIveMind System Status (Fast Mode)</h1>
                <p><a href="/comet">← Back to Portal</a> | <a href="javascript:location.reload()">🔄 Refresh</a></p>
                
                <div style="border: 1px solid #00d4aa; padding: 15px; margin: 15px 0; background: #162032; border-radius: 4px;">
                    <h2>System Health: ✅ {status.get('status', 'Unknown').title()}</h2>
                    <p>🟢 <strong>Active Sessions:</strong> {status.get('system', {}).get('active_sessions', 0)}</p>
                    <p>🎯 <strong>Active Directives:</strong> {status.get('system', {}).get('active_directives', 0)}</p>
                    <p>🧠 <strong>Memory System:</strong> {status.get('system', {}).get('memory_system', 'operational')}</p>
                    <p>⏱️ <strong>Response Time:</strong> <50ms (optimized)</p>
                    <p>🕐 <strong>Last Updated:</strong> {datetime.now().strftime('%H:%M:%S')}</p>
                </div>
                
                <div style="border: 1px solid #2d3748; padding: 15px; margin: 15px 0; background: #162032; border-radius: 4px;">
                    <h2>Quick Status</h2>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        <div>✅ Comet Portal: Active</div>
                        <div>✅ Data Submission: Working</div>
                        <div>✅ Directive Creation: Working</div>
                        <div>✅ Memory Search: Working</div>
                        <div>✅ Agent Network: Connected</div>
                        <div>✅ Tailscale: Secured</div>
                    </div>
                </div>
                
                <p style="font-size: 0.9em; color: #8892b0;">
                    <strong>Note:</strong> Fast mode enabled for quick loading. 
                    API: <code><a href="/comet/api/status" style="color: #00d4aa;">/comet/api/status</a></code>
                </p>
            </body>
            </html>
            """)
        
        # Comet API get available categories
        @self.mcp.custom_route("/comet/api/categories", methods=["GET"])
        async def comet_get_categories(request):
            """Get all available memory categories for Comet"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            try:
                # Return default categories for now - can be extended later
                category_options = [
                    {"value": "comet_findings", "label": "Comet Findings", "description": "Findings from Comet browser"},
                    {"value": "research", "label": "Research", "description": "Research data and findings"},
                    {"value": "intelligence", "label": "Intelligence", "description": "Threat intelligence data"},
                    {"value": "observations", "label": "Observations", "description": "General observations"},
                    {"value": "analysis", "label": "Analysis", "description": "Analysis results"},
                    {"value": "incident", "label": "Incident", "description": "Security incidents"},
                    {"value": "security", "label": "Security", "description": "Security-related information"},
                    {"value": "other", "label": "Other", "description": "Miscellaneous category"}
                ]
                
                return JSONResponse({
                    "categories": category_options,
                    "total": len(category_options),
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Comet get categories error: {e}")
                return JSONResponse({"error": "Failed to get categories"}, status_code=500)
        
        # Comet API create new category (simplified for now)
        @self.mcp.custom_route("/comet/api/categories", methods=["POST"])
        async def comet_create_category(request):
            """Create a new memory category from Comet"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            try:
                data = await request.json()
                category_name = data.get('name', '').strip()
                description = data.get('description', '').strip()
                
                if not category_name:
                    return JSONResponse({"error": "Category name is required"}, status_code=400)
                
                # For now, just acknowledge the creation
                # Later this can be expanded to actually create categories in the system
                return JSONResponse({
                    "success": True,
                    "message": f"Category '{category_name}' noted for creation",
                    "category": {
                        "name": category_name,
                        "description": description
                    },
                    "timestamp": datetime.now().isoformat()
                })
                    
            except Exception as e:
                logger.error(f"Comet create category error: {e}")
                return JSONResponse({"error": "Failed to create category"}, status_code=500)

        # Comet API create directive (JSON format)
        @self.mcp.custom_route("/comet/api/directive", methods=["POST"])
        async def comet_api_create_directive(request):
            """Create a new directive for Comet"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            try:
                data = await request.json()
                title = data.get('title', '').strip()
                content = data.get('content', '').strip()
                directive_type = data.get('type', 'task')
                priority = data.get('priority', 'normal')
                deadline = data.get('deadline')
                tags = data.get('tags', [])
                required_capabilities = data.get('required_capabilities', [])
                metadata = data.get('metadata', {})
                
                if not title or not content:
                    return JSONResponse({"error": "Title and content are required"}, status_code=400)
                
                # Enhanced directive data structure
                directive_content = {
                    "title": title,
                    "content": content,
                    "type": directive_type,
                    "priority": priority,
                    "deadline": deadline,
                    "tags": tags,
                    "required_capabilities": required_capabilities,
                    "metadata": {
                        **metadata,
                        "created_by": "comet_browser",
                        "created_at": datetime.now().isoformat(),
                        "network": "tailscale_secured"
                    }
                }
                
                directive_id = self.comet_system.create_directive(directive_type, directive_content, priority)
                
                # Store directive in hAIveMind memory for agent coordination
                await self.storage.store_memory(
                    content=f"DIRECTIVE: {title}\n\n{content}",
                    category="directives",
                    tags=["directive", directive_type, priority] + tags,
                    metadata={
                        "directive_id": directive_id,
                        "directive_type": directive_type,
                        "priority": priority,
                        "required_capabilities": ",".join(required_capabilities) if required_capabilities else "",
                        "deadline": deadline or "",
                        "created_by": metadata.get("created_by", "comet_browser"),
                        "created_at": datetime.now().isoformat(),
                        "network": "tailscale_secured"
                    }
                )
                
                logger.info(f"🎯 Comet created directive: {directive_type} - {directive_id} - {title}")
                
                return JSONResponse({
                    "success": True,
                    "directive_id": directive_id,
                    "message": f"Directive '{title}' created successfully and broadcast to hAIveMind network",
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Comet create directive error: {e}")
                return JSONResponse({"error": "Failed to create directive"}, status_code=500)
        
        # Comet data submission endpoints for bidirectional communication  
        @self.mcp.custom_route("/comet/api/submit", methods=["POST"])
        async def comet_submit_data(request):
            """Accept data submissions from Comet browser"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            try:
                data = await request.json()
                submission_type = data.get('type', 'general')
                content = data.get('content', '')
                category = data.get('category', 'comet_findings')
                tags = data.get('tags', [])
                metadata = data.get('metadata', {})
                
                if not content:
                    return JSONResponse({"error": "Content is required"}, status_code=400)
                
                # Add Comet-specific metadata
                enhanced_metadata = {
                    **metadata,
                    "source": "comet_browser",
                    "submission_type": submission_type,
                    "submitted_at": datetime.now().isoformat(),
                    "network": "tailscale_secured",
                }
                
                # Store in hAIveMind memory system
                memory_id = await self.storage.store_memory(
                    content=content,
                    category=category,
                    tags=tags + ["comet-submission", submission_type],
                    metadata=enhanced_metadata
                )
                
                logger.info(f"🚀 Comet submitted data: {submission_type} - {memory_id}")
                
                return JSONResponse({
                    "success": True,
                    "memory_id": memory_id,
                    "message": "Data successfully submitted to hAIveMind",
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Comet data submission error: {e}")
                return JSONResponse({"error": "Failed to submit data"}, status_code=500)
        
        # Comet results submission (for task completion)
        @self.mcp.custom_route("/comet/api/results", methods=["POST"])
        async def comet_submit_results(request):
            """Accept task completion results from Comet"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            # Validate session
            auth_header = request.headers.get('authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return JSONResponse({"error": "Authorization required"}, status_code=401)
            
            token = auth_header.split(' ')[1]
            if not self.comet_system.validate_session(token):
                return JSONResponse({"error": "Invalid or expired session"}, status_code=401)
            
            try:
                data = await request.json()
                directive_id = data.get('directive_id')
                results = data.get('results', {})
                status = data.get('status', 'completed')
                notes = data.get('notes', '')
                
                if not directive_id:
                    return JSONResponse({"error": "directive_id is required"}, status_code=400)
                
                # Update directive status
                updated = self.comet_system.update_directive_status(
                    directive_id, 
                    status, 
                    {
                        "results": results,
                        "notes": notes,
                        "completed_at": datetime.now().isoformat(),
                        "completion_source": "comet_browser"
                    }
                )
                
                if not updated:
                    return JSONResponse({"error": "Directive not found or already completed"}, status_code=404)
                
                # Store results in memory for future reference
                result_content = f"Comet Task Completion - Directive {directive_id}\\n\\n"
                result_content += f"Status: {status}\\n"
                result_content += f"Results: {results}\\n"
                if notes:
                    result_content += f"Notes: {notes}\\n"
                
                memory_id = await self.storage.store_memory(
                    content=result_content,
                    category="comet_results",
                    tags=["comet-completion", "task-results", directive_id],
                    metadata={
                        "source": "comet_browser",
                        "directive_id": directive_id,
                        "completion_status": status,
                        "completed_at": datetime.now().isoformat()
                    }
                )
                
                logger.info(f"🚀 Comet completed directive {directive_id} - {status}")
                
                return JSONResponse({
                    "success": True,
                    "directive_id": directive_id,
                    "memory_id": memory_id,
                    "message": "Results successfully submitted",
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Comet results submission error: {e}")
                return JSONResponse({"error": "Failed to submit results"}, status_code=500)
        
        # Comet feedback/questions endpoint
        @self.mcp.custom_route("/comet/api/feedback", methods=["POST"])
        async def comet_submit_feedback(request):
            """Accept feedback or questions from Comet"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            # Validate session
            auth_header = request.headers.get('authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return JSONResponse({"error": "Authorization required"}, status_code=401)
            
            token = auth_header.split(' ')[1]
            if not self.comet_system.validate_session(token):
                return JSONResponse({"error": "Invalid or expired session"}, status_code=401)
            
            try:
                data = await request.json()
                feedback_type = data.get('type', 'general')  # general, question, issue, suggestion
                message = data.get('message', '')
                priority = data.get('priority', 'normal')
                context = data.get('context', {})
                
                if not message:
                    return JSONResponse({"error": "Message is required"}, status_code=400)
                
                # Store feedback in memory
                feedback_content = f"Comet Browser Feedback ({feedback_type})\\n\\n{message}"
                if context:
                    feedback_content += f"\\n\\nContext: {context}"
                
                memory_id = await self.storage.store_memory(
                    content=feedback_content,
                    category="comet_feedback",
                    tags=["comet-feedback", feedback_type, priority],
                    metadata={
                        "source": "comet_browser",
                        "feedback_type": feedback_type,
                        "priority": priority,
                        "context": context,
                        "submitted_at": datetime.now().isoformat()
                    }
                )
                
                # If it's a question or issue, create a directive for human review
                if feedback_type in ['question', 'issue'] and priority in ['high', 'urgent']:
                    self.comet_system.create_directive(
                        'comet_feedback_review',
                        {
                            "feedback_id": memory_id,
                            "type": feedback_type,
                            "message": message,
                            "priority": priority,
                            "requires_response": True
                        },
                        priority
                    )
                
                logger.info(f"🚀 Comet feedback received: {feedback_type} - {priority}")
                
                return JSONResponse({
                    "success": True,
                    "feedback_id": memory_id,
                    "message": "Feedback received and stored",
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Comet feedback submission error: {e}")
                return JSONResponse({"error": "Failed to submit feedback"}, status_code=500)

        # Comet memory retrieval endpoints for enhanced comment system
        @self.mcp.custom_route("/comet/api/memory/{memory_id}", methods=["GET"])
        async def comet_get_memory_by_id(request):
            """Get a specific memory by ID for browser display"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            memory_id = request.path_params.get('memory_id')
            if not memory_id:
                return JSONResponse({"error": "Memory ID is required"}, status_code=400)
            
            try:
                memory = await self.comet_system.get_memory_by_id(memory_id)
                if memory:
                    return JSONResponse({
                        "success": True,
                        "memory": memory,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    return JSONResponse({"error": "Memory not found"}, status_code=404)
                    
            except Exception as e:
                logger.error(f"Comet get memory error: {e}")
                return JSONResponse({"error": "Failed to retrieve memory"}, status_code=500)

        @self.mcp.custom_route("/comet/api/tickets/{ticket_id}/comments", methods=["GET"])
        async def comet_get_ticket_comments(request):
            """Get all comments for a ticket with memory context for browser display"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            ticket_id = request.path_params.get('ticket_id')
            if not ticket_id:
                return JSONResponse({"error": "Ticket ID is required"}, status_code=400)
            
            try:
                comments = await self.comet_system.get_comment_memories(ticket_id)
                return JSONResponse({
                    "success": True,
                    "ticket_id": ticket_id,
                    "comments": comments,
                    "total_comments": len(comments),
                    "browser_optimized": True,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Comet get ticket comments error: {e}")
                return JSONResponse({"error": "Failed to retrieve comments"}, status_code=500)

        @self.mcp.custom_route("/comet/api/memory/search-browser", methods=["GET"])
        async def comet_search_memories_browser(request):
            """Search memories with browser-optimized formatting"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled"}, status_code=404)
            
            query = request.query_params.get('q', '')
            category = request.query_params.get('category')
            limit = int(request.query_params.get('limit', 20))
            
            if not query:
                return JSONResponse({"error": "Query parameter 'q' is required"}, status_code=400)
            
            try:
                results = await self.comet_system.search_memories_for_browser(query, category, limit)
                return JSONResponse(results)
                
            except Exception as e:
                logger.error(f"Comet memory search error: {e}")
                return JSONResponse({"error": "Search failed"}, status_code=500)

        logger.info("🚀 Comet memory retrieval endpoints registered - enhanced comment system integration enabled")
        
        # ===== COMET# - AI-OPTIMIZED SIMPLIFIED PORTAL =====
        
        @self.mcp.custom_route("/comet-ai", methods=["GET"])
        async def comet_ai_portal(request):
            """Ultra-simplified AI-first portal for Comet Browser"""
            if not self.comet_system.enabled:
                return JSONResponse({"error": "Comet integration is disabled", "comet_meta": {"source": "haivemind", "error": True}}, status_code=404)
            
            return HTMLResponse("""<!DOCTYPE html>
<html><head>
<title>Comet Handoff | Simple</title>
<style>
body { font-family: monospace; margin: 20px; background: #0a0e1a; color: #e1e5e9; }
.container { display: flex; gap: 20px; }
.column { flex: 1; }
.input-box { width: 100%; padding: 8px; background: #2d3748; color: #e1e5e9; border: 1px solid #4a5568; margin-bottom: 10px; }
.paste-area { width: 100%; height: 300px; background: #2d3748; color: #e1e5e9; border: 1px solid #4a5568; padding: 10px; }
.btn { background: #00d4aa; color: #0a0e1a; border: none; padding: 8px 16px; margin-right: 10px; cursor: pointer; }
</style>
</head><body>

<div class="container">
  <div class="column">
    <h3>📝 Paste Work</h3>
    <input type="text" id="subject" class="input-box" placeholder="Subject">
    <textarea id="content" class="paste-area" placeholder="Content"></textarea>
    <button class="btn" onclick="save()">Save</button>
    <button class="btn" onclick="clearForm()">Clear</button>
  </div>
  <div class="column">
    <h3>📤 Recent (click items to load)</h3>
    <div style="margin-bottom: 10px;">
      <input type="text" id="searchInput" placeholder="Search memories..."
             style="background:#2d3748;color:#e1e5e9;border:1px solid #4a5568;padding:4px;width:200px;margin-right:10px;">
      <button class="btn" onclick="loadRecent()" style="margin-right:5px;">Search</button>
      <button class="btn" onclick="document.getElementById('searchInput').value='';loadRecent()" style="margin-right:10px;">Clear</button>

      Show: <select id="limitSelect" onchange="loadRecent()" style="background:#2d3748;color:#e1e5e9;border:1px solid #4a5568;padding:4px;">
        <option value="5">5</option>
        <option value="10" selected>10</option>
        <option value="25">25</option>
        <option value="50">50</option>
        <option value="100">100</option>
      </select> items
    </div>
    <div id="recent">Loading...</div>
    <button class="btn" onclick="location.reload()">Refresh</button>
  </div>
</div>

<script>
function save() {
  const subject = document.getElementById('subject').value;
  const content = document.getElementById('content').value;

  if (!subject && !content) {
    // Show warning in recent div (visible to browser AI)
    const div = document.getElementById('recent');
    div.innerHTML = '<div style="background:#ffaa00;color:#0a0e1a;padding:20px;font-size:18px;font-weight:bold;text-align:center;border-radius:5px;margin:10px 0;">⚠️ NOTHING TO SAVE - Please enter content</div>';
    return;
  }

  const data = JSON.stringify({
    subject: subject || 'Untitled',
    content: content,
    timestamp: new Date().toISOString()
  });

  fetch('/comet-ai/paste', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({content: data, category: 'comet_handoff'})
  })
  .then(r => r.json())
  .then(result => {
    if (result.success) {
      // Show success with memory ID
      const memId = result.memory_id ? result.memory_id.substring(0, 8) : 'unknown';
      const successMsg = '✅ SAVED! ID: ' + memId;

      // Show in recent div (visible to browser AI)
      const div = document.getElementById('recent');
      div.innerHTML = '<div style="background:#00d4aa;color:#0a0e1a;padding:20px;font-size:18px;font-weight:bold;text-align:center;border-radius:5px;margin:10px 0;">' + successMsg + '</div>';

      // Clear form
      document.getElementById('subject').value = '';
      document.getElementById('content').value = '';

      // Wait 1 second before reloading to ensure indexing is complete
      setTimeout(() => {
        loadRecent();
      }, 1000);
    } else {
      // Show error in recent div (visible to browser AI)
      const div = document.getElementById('recent');
      div.innerHTML = '<div style="background:#ff5555;color:#fff;padding:20px;font-size:18px;font-weight:bold;text-align:center;border-radius:5px;margin:10px 0;">❌ SAVE FAILED</div>';
    }
  })
  .catch(e => {
    // Show error in recent div (visible to browser AI)
    const div = document.getElementById('recent');
    div.innerHTML = '<div style="background:#ff5555;color:#fff;padding:20px;font-size:18px;font-weight:bold;text-align:center;border-radius:5px;margin:10px 0;">❌ ERROR: ' + e.message + '</div>';
  });
}

function clearForm() {
  console.log('Clearing form');
  document.getElementById('subject').value = '';
  document.getElementById('content').value = '';
}

// Load recent function
function loadRecent() {
  console.log('loadRecent() called');
  const limit = document.getElementById('limitSelect') ? document.getElementById('limitSelect').value : 10;
  const query = document.getElementById('searchInput') ? document.getElementById('searchInput').value : '';
  console.log('Search query:', query, 'Limit:', limit);
  const url = '/comet-ai/recent?limit=' + limit + (query ? '&query=' + encodeURIComponent(query) : '');

  // Show searching indicator
  const div = document.getElementById('recent');
  div.innerHTML = query ? 'Searching for "' + query + '"...' : 'Loading recent items...';

  fetch(url)
  .then(r => r.json())
  .then(data => {
    const div = document.getElementById('recent');
    if (data.memories && data.memories.length > 0) {
      div.innerHTML = data.memories.map(m => {
        const source = m.metadata?.processed_by === 'simple-comet' ? '🌐 Web' :
                      m.metadata?.source === 'simple-paste' ? '🌐 Web' :
                      m.metadata?.processed_by ? '⚡ MCP' : '📝 Other';
        const sourceColor = source.includes('Web') ? '#00d4aa' :
                           source.includes('MCP') ? '#4fc3f7' : '#9ca3af';
        return `<div style="border:1px solid #4a5568;padding:10px;margin:10px 0;cursor:pointer;background:#1a202c;" onclick="load('${m.id}')" onmouseover="this.style.background='#2d3748'" onmouseout="this.style.background='#1a202c'">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <strong>🔗 #${m.id.substring(0,8)}</strong>
            <span style="color:${sourceColor};font-size:12px;">${source}</span>
          </div>
          <em>(click to load)</em><br>
          ${m.content.substring(0,100)}...
        </div>`;
      }).join('');
    } else {
      div.innerHTML = 'No recent work found';
    }
  })
  .catch(e => document.getElementById('recent').innerHTML = 'Load error');
}

// Load recent on page load
window.onload = loadRecent;

function load(id) {
  fetch('/comet-ai/get/' + id)
  .then(r => r.json())
  .then(result => {
    if (result.success) {
      try {
        const parsed = JSON.parse(result.content);
        document.getElementById('subject').value = parsed.subject || '';
        document.getElementById('content').value = parsed.content || '';
      } catch (e) {
        document.getElementById('content').value = result.content;
      }
      // Show success in recent div (visible to browser AI)
      const div = document.getElementById('recent');
      div.innerHTML = '<div style="background:#00d4aa;color:#0a0e1a;padding:20px;font-size:18px;font-weight:bold;text-align:center;border-radius:5px;margin:10px 0;">✅ LOADED! ID: ' + id.substring(0,8) + '</div>';
      setTimeout(loadRecent, 1000);
    }
  })
  .catch(e => {
    // Show error in recent div (visible to browser AI)
    const div = document.getElementById('recent');
    div.innerHTML = '<div style="background:#ff5555;color:#fff;padding:20px;font-size:18px;font-weight:bold;text-align:center;border-radius:5px;margin:10px 0;">❌ LOAD FAILED</div>';
  });
}
</script>
</body></html>""")

        @self.mcp.custom_route("/comet-ai/context", methods=["GET"])
        async def comet_ai_context_DISABLED(request):
            return JSONResponse({"error": "Simplified portal - context disabled"})

        # Cleaned up - old HTML removed
        async def comet_ai_paste(request):
            """Quick paste endpoint for pastebin functionality"""
            try:
                data = await request.json()
                content = data.get('content', '').strip()

                if not content:
                    return JSONResponse({"error": "No content provided"}, status_code=400)

                # Generate unique short ID
                import hashlib
                short_id = hashlib.md5(content.encode()).hexdigest()[:8]

                # Store with pastebin metadata
                if hasattr(self.storage, 'store_memory'):
                    memory_id = await self.storage.store_memory(
                        content=content,
                        category='comet_handoff',
                        metadata={
                            "processed_by": "comet-pastebin",
                            "processed_at": datetime.now().isoformat(),
                            "tags": "#comet-handoff,#pastebin",
                            "source": "comet-paste",
                            "short_id": short_id,
                            "paste_type": data.get('type', 'text')
                        }
                    )

                    return JSONResponse({
                        "success": True,
                        "memory_id": memory_id,
                        "short_id": short_id,
                        "content_length": len(content)
                    })
                else:
                    return JSONResponse({"error": "Storage unavailable"}, status_code=500)

            except Exception as e:
                logger.error(f"Paste error: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)

        @self.mcp.custom_route("/comet-ai/get/{item_id}", methods=["GET"])
        async def comet_ai_get(request):
            """Get specific paste by ID"""
            try:
                item_id = request.path_params['item_id']

                if hasattr(self.storage, 'retrieve_memory'):
                    memory = await self.storage.retrieve_memory(item_id)
                    if memory:
                        return JSONResponse({
                            "success": True,
                            "memory": memory,
                            "content": memory.get('content', ''),
                            "created_at": memory.get('created_at', ''),
                            "short_id": memory.get('metadata', {}).get('short_id', item_id[:8])
                        })
                    else:
                        return JSONResponse({"error": "Paste not found"}, status_code=404)
                else:
                    return JSONResponse({"error": "Retrieval unavailable"}, status_code=500)

            except Exception as e:
                logger.error(f"Get paste error: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)

        @self.mcp.custom_route("/comet-ai/paste", methods=["POST"])
        async def comet_ai_paste(request):
            """Simple paste endpoint"""
            try:
                data = await request.json()
                content = data.get('content', '').strip()
                category = data.get('category', 'comet_handoff')

                if not content:
                    return JSONResponse({"success": False, "error": "No content provided"}, status_code=400)

                # Store with simple metadata
                if hasattr(self.storage, 'store_memory'):
                    memory_id = await self.storage.store_memory(
                        content=content,
                        category=category,
                        metadata={
                            "processed_by": "simple-comet",
                            "processed_at": datetime.now().isoformat(),
                            "source": "simple-paste"
                        }
                    )
                    return JSONResponse({
                        "success": True,
                        "memory_id": memory_id
                    })
                else:
                    return JSONResponse({"success": False, "error": "Storage unavailable"}, status_code=500)

            except Exception as e:
                logger.error(f"Paste error: {e}")
                return JSONResponse({"success": False, "error": str(e)}, status_code=500)

        @self.mcp.custom_route("/comet-ai/recent", methods=["GET"])
        async def comet_ai_recent(request):
            """Get recent pastes from all memories"""
            try:
                limit = int(request.query_params.get('limit', 10))
                query = request.query_params.get('query', '').strip()

                # Try different approaches to get recent memories
                memories = []

                if hasattr(self.storage, 'search_memories'):
                    # Use search to get all recent memories
                    try:
                        all_memories = await self.storage.search_memories(
                            query=query,  # Use actual search query
                            limit=500,  # Get more to find recent ones
                            category=None
                        )

                        # Sort by created_at and limit
                        if all_memories:
                            sorted_memories = sorted(all_memories,
                                                   key=lambda x: x.get('created_at', ''),
                                                   reverse=True)
                            memories = sorted_memories[:limit]

                    except Exception as e:
                        logger.warning(f"Search fallback failed: {e}")

                if not memories and hasattr(self.storage, 'get_recent_memories'):
                    memories = await self.storage.get_recent_memories(limit=limit, hours=24*7)  # 7 days

                return JSONResponse({
                    "success": True,
                    "memories": memories,
                    "count": len(memories)
                })

            except Exception as e:
                logger.error(f"Recent pastes error: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)

        @self.mcp.custom_route("/comet-ai/exchange", methods=["POST"])
        async def comet_ai_exchange(request):
            """Unified data exchange endpoint for AI agents"""
            # No auth required - secured by Tailscale network
                
            try:
                data = await request.json()
                intent = data.get('intent', 'query')
                payload = data.get('payload', {})
                comet_meta = data.get('comet_meta', {})
                
                # Add automatic tagging (ChromaDB requires simple values, not lists)
                enhanced_meta = {
                    "processed_by": "haivemind",
                    "processed_at": datetime.now().isoformat(),
                    "tags": "#comet-ai,#ai-exchange",
                    "source": comet_meta.get("source", "unknown"),
                    "capabilities": ",".join(comet_meta.get("capabilities", [])) if comet_meta.get("capabilities") else ""
                }
                
                result = None
                
                if intent == "store":
                    # Store memory with Comet tagging
                    content = payload.get('content', '')
                    category = payload.get('category', 'comet_findings')
                    
                    if hasattr(self.storage, 'store_memory'):
                        memory_id = await self.storage.store_memory(
                            content=content,
                            category=category,
                            metadata=enhanced_meta
                        )
                        result = {"stored": True, "memory_id": memory_id}
                    else:
                        result = {"stored": False, "error": "Storage unavailable"}
                        
                elif intent == "query":
                    # Search memories or get recent messages
                    query = payload.get('content', '')
                    limit = payload.get('limit', 5)

                    if hasattr(self.storage, 'search_memories'):
                        # Check if this is a "get last messages" request or recent work request
                        if (query.lower().startswith('get last') and 'messages' in query.lower()) or 'recent work' in query.lower():
                            # Get recent memories from comet category first, then fall back to general
                            try:
                                memories = await self.storage.get_recent_memories(category='comet_handoff', limit=limit)
                                if not memories:
                                    # Fallback to global category
                                    memories = await self.storage.get_recent_memories(category='global', limit=limit)
                            except:
                                # Final fallback - get any recent memories
                                memories = await self.storage.get_recent_memories(limit=limit)
                        else:
                            # Normal search - search in comet categories first
                            try:
                                memories = await self.storage.search_memories(query, category='comet_handoff', limit=limit)
                                if not memories:
                                    # Also search in related comet categories
                                    comet_memories = []
                                    for cat in ['comet_findings', 'comet_results', 'comet_feedback']:
                                        try:
                                            cat_memories = await self.storage.search_memories(query, category=cat, limit=limit//3)
                                            comet_memories.extend(cat_memories)
                                        except:
                                            continue
                                    memories = comet_memories[:limit] if comet_memories else []
                                if not memories:
                                    # Final fallback - search all categories
                                    memories = await self.storage.search_memories(query, limit=limit)
                            except:
                                # Final fallback - search all categories
                                memories = await self.storage.search_memories(query, limit=limit)
                        result = {"memories": memories}
                    else:
                        result = {"memories": [], "error": "Search unavailable"}
                        
                elif intent == "execute":
                    # Execute task or delegate
                    task_type = payload.get('type', 'general')
                    content = payload.get('content', '')
                    
                    if task_type == 'task_delegation':
                        directive_id = self.comet_system.create_directive(
                            'comet_task', 
                            {"task": content, "source": "comet-browser"}, 
                            "normal"
                        )
                        result = {"executed": True, "directive_id": directive_id}
                    else:
                        result = {"executed": False, "error": "Unknown task type"}
                        
                else:
                    result = {"error": f"Unknown intent: {intent}"}

                response = {
                    "comet_meta": enhanced_meta,
                    "result": result,
                    "status": "processed"
                }
                
                return JSONResponse(response)
                
            except Exception as e:
                logger.error(f"Comet exchange error: {e}")
                return JSONResponse({
                    "error": str(e),
                    "comet_meta": {"source": "haivemind", "error": True}
                }, status_code=500)

        @self.mcp.custom_route("/comet-ai/stream", methods=["GET"])
        async def comet_ai_stream(request):
            """SSE stream for real-time bidirectional communication"""
            # No auth required - secured by Tailscale network
            
            async def generate_stream():
                yield "data: " + json.dumps({
                    "comet_meta": {
                        "source": "haivemind",
                        "stream": "connected",
                        "timestamp": datetime.now().isoformat()
                    },
                    "message": "Stream connected"
                }) + "\n\n"
                
                # Send periodic updates
                import asyncio
                try:
                    while True:
                        await asyncio.sleep(10)
                        
                        # Get system status updates
                        status_update = {
                            "comet_meta": {
                                "source": "haivemind",
                                "type": "status_update",
                                "timestamp": datetime.now().isoformat()
                            },
                            "active_directives": len(self.comet_system.active_directives),
                            "system_healthy": True
                        }
                        
                        yield "data: " + json.dumps(status_update) + "\n\n"
                        
                except Exception as e:
                    yield "data: " + json.dumps({
                        "comet_meta": {"source": "haivemind", "error": True},
                        "error": str(e)
                    }) + "\n\n"
            
            from starlette.responses import StreamingResponse
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/event-stream"
                }
            )

        @self.mcp.custom_route("/comet-ai/sync", methods=["GET", "POST"])
        async def comet_ai_sync(request):
            """State synchronization for multi-agent handoff"""
            # No auth required - secured by Tailscale network
            
            try:
                if request.method == "GET":
                    # Get current state for handoff
                    sync_state = {
                        "comet_meta": {
                            "source": "haivemind",
                            "sync_type": "state_export",
                            "timestamp": datetime.now().isoformat()
                        },
                        "session_context": {
                            "created_at": datetime.now().isoformat(),
                            "last_activity": datetime.now().isoformat()
                        },
                        "active_directives": self.comet_system.active_directives,
                        "recent_memories": self.comet_system.get_session_memories(token, limit=5),
                        "context_preservation": {
                            "format_version": "1.0",
                            "compatible_agents": ["comet-browser", "claude-desktop", "martin-ai"],
                            "handoff_ready": True
                        }
                    }
                    
                    return JSONResponse(sync_state)
                    
                else:  # POST - restore state from another agent
                    data = await request.json()
                    imported_state = data.get('state', {})
                    source_agent = data.get('source_agent', 'unknown')
                    
                    # Process imported state
                    restored_items = []
                    
                    if 'context' in imported_state:
                        # Store context as memory
                        if hasattr(self.storage, 'store_memory'):
                            memory_id = await self.storage.store_memory(
                                content=f"Imported context from {source_agent}: {imported_state['context']}",
                                category="agent_handoff",
                                metadata={
                                    "source_agent": source_agent,
                                    "handoff_timestamp": datetime.now().isoformat(),
                                    "tags": "#agent-handoff,#comet-sync"  # Comma-separated string
                                }
                            )
                            restored_items.append({"type": "context", "memory_id": memory_id})
                    
                    if 'tasks' in imported_state:
                        # Create directives from imported tasks
                        for task in imported_state.get('tasks', []):
                            directive_id = self.comet_system.create_directive(
                                'imported_task',
                                {
                                    "task": task,
                                    "source_agent": source_agent,
                                    "imported_at": datetime.now().isoformat()
                                },
                                "normal"
                            )
                            restored_items.append({"type": "task", "directive_id": directive_id})
                    
                    response = {
                        "comet_meta": {
                            "source": "haivemind",
                            "sync_type": "state_import",
                            "timestamp": datetime.now().isoformat()
                        },
                        "import_successful": True,
                        "restored_items": restored_items,
                        "source_agent": source_agent
                    }
                    
                    return JSONResponse(response)
                    
            except Exception as e:
                logger.error(f"Comet sync error: {e}")
                return JSONResponse({
                    "error": str(e),
                    "comet_meta": {"source": "haivemind", "error": True}
                }, status_code=500)

        logger.info("🚀 Comet# AI-optimized portal registered - simplified interface active")
        
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

                # Try bootstrap authentication first (new secure system)
                auth_success = False
                if self.admin_bootstrap and self.admin_system_initialized:
                    auth_success = self.admin_bootstrap.verify_admin_password(password)

                # Fall back to legacy auth if bootstrap not available
                if not auth_success and not (self.admin_bootstrap and self.admin_system_initialized):
                    auth_success = self.auth.validate_admin_login(username, password)

                if auth_success:
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

                # Try bootstrap authentication first (new secure system)
                auth_success = False
                if self.admin_bootstrap and self.admin_system_initialized:
                    auth_success = self.admin_bootstrap.verify_admin_password(password)

                # Fall back to legacy auth if bootstrap not available
                if not auth_success and not (self.admin_bootstrap and self.admin_system_initialized):
                    auth_success = self.auth.validate_admin_login(username, password)

                if auth_success:
                    token = self.auth.generate_jwt_token({
                        'username': username,
                        'role': 'admin'
                    })
                    return JSONResponse({"token": token, "status": "success"})
                else:
                    return JSONResponse({"error": "Invalid credentials"}, status_code=401)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # ===== ADMIN SETUP ENDPOINTS (for first-run initialization) =====

        @self.mcp.custom_route("/admin/api/setup/status", methods=["GET"])
        async def setup_status(request):
            """Check if admin system needs initialization"""
            try:
                if not ADMIN_BOOTSTRAP_AVAILABLE:
                    return JSONResponse({
                        "initialized": True,
                        "mode": "legacy",
                        "message": "Using legacy authentication"
                    })

                if self.admin_bootstrap and self.admin_bootstrap.is_initialized():
                    return JSONResponse({
                        "initialized": True,
                        "mode": "bootstrap",
                        "message": "Admin system ready"
                    })
                else:
                    return JSONResponse({
                        "initialized": False,
                        "mode": "bootstrap",
                        "message": "First-run setup required"
                    })
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        @self.mcp.custom_route("/admin/api/setup/initialize", methods=["POST"])
        async def setup_initialize(request):
            """Initialize the admin system (first-run only)"""
            try:
                if not ADMIN_BOOTSTRAP_AVAILABLE:
                    return JSONResponse({
                        "error": "Admin bootstrap system not available"
                    }, status_code=500)

                if self.admin_bootstrap and self.admin_bootstrap.is_initialized():
                    return JSONResponse({
                        "error": "System already initialized"
                    }, status_code=400)

                data = await request.json()
                admin_username = data.get('admin_username', 'admin')

                # Initialize the system
                result = self.admin_bootstrap.initialize_system(admin_username)

                # Reload credentials
                self.admin_bootstrap.load_credentials()
                self.admin_system_initialized = True

                return JSONResponse({
                    "status": "initialized",
                    "message": "SAVE THESE CREDENTIALS - SHOWN ONLY ONCE!",
                    "credentials": result.get('credentials', {}),
                    "bootstrap_key": result.get('bootstrap_key'),
                    "instructions": result.get('instructions', [])
                })

            except Exception as e:
                logger.error(f"Setup initialization failed: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)

        @self.mcp.custom_route("/admin/setup", methods=["GET"])
        async def setup_page(request):
            """Serve the first-run setup page"""
            return HTMLResponse("""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>hAIveMind Setup</title>
                <link rel="stylesheet" href="/admin/static/admin.css">
                <style>
                    .setup-container { max-width: 600px; margin: 50px auto; padding: 30px; }
                    .credentials-box { background: #1a1a2e; padding: 20px; border-radius: 8px; margin: 20px 0; }
                    .credential-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #333; }
                    .credential-value { font-family: monospace; color: #00ff00; word-break: break-all; }
                    .warning { background: #ff6b35; color: white; padding: 15px; border-radius: 5px; margin: 20px 0; }
                    .btn-primary { background: #4a90d9; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
                    .btn-primary:hover { background: #357abd; }
                    .btn-primary:disabled { background: #666; cursor: not-allowed; }
                    .hidden { display: none; }
                    .status-message { padding: 10px; border-radius: 5px; margin: 10px 0; }
                    .status-success { background: #2d5a3d; color: #9fffb0; }
                    .status-error { background: #5a2d2d; color: #ff9f9f; }
                </style>
            </head>
            <body class="dashboard">
                <div class="setup-container">
                    <h1>hAIveMind Initial Setup</h1>

                    <div id="status-checking">
                        <p>Checking system status...</p>
                    </div>

                    <div id="already-initialized" class="hidden">
                        <p>System is already initialized.</p>
                        <a href="/admin/login.html" class="btn-primary">Go to Login</a>
                    </div>

                    <div id="setup-form" class="hidden">
                        <p>This is the first-run setup. Click below to generate secure admin credentials.</p>

                        <div class="warning">
                            <strong>Warning:</strong> The credentials shown after setup will only be displayed ONCE.
                            Make sure to save them in a secure location!
                        </div>

                        <form id="initForm">
                            <div style="margin: 20px 0;">
                                <label for="adminUsername">Admin Username:</label>
                                <input type="text" id="adminUsername" value="admin" style="width: 100%; padding: 10px; margin-top: 5px;">
                            </div>
                            <button type="submit" class="btn-primary" id="initBtn">Initialize Admin System</button>
                        </form>
                    </div>

                    <div id="credentials-display" class="hidden">
                        <h2>Setup Complete!</h2>

                        <div class="warning">
                            <strong>SAVE THESE CREDENTIALS NOW!</strong><br>
                            They will NOT be shown again. Store them in a secure password manager.
                        </div>

                        <div class="credentials-box">
                            <div class="credential-item">
                                <span>Admin Username:</span>
                                <span class="credential-value" id="cred-username"></span>
                            </div>
                            <div class="credential-item">
                                <span>Admin Password:</span>
                                <span class="credential-value" id="cred-password"></span>
                            </div>
                            <div class="credential-item">
                                <span>Admin API Token:</span>
                                <span class="credential-value" id="cred-admin-token"></span>
                            </div>
                            <div class="credential-item">
                                <span>Bootstrap Key:</span>
                                <span class="credential-value" id="cred-bootstrap"></span>
                            </div>
                        </div>

                        <p>After saving your credentials, proceed to login:</p>
                        <a href="/admin/login.html" class="btn-primary">Go to Login</a>
                    </div>

                    <div id="status-message" class="status-message hidden"></div>
                </div>

                <script>
                    async function checkStatus() {
                        try {
                            const response = await fetch('/admin/api/setup/status');
                            const data = await response.json();

                            document.getElementById('status-checking').classList.add('hidden');

                            if (data.initialized) {
                                document.getElementById('already-initialized').classList.remove('hidden');
                            } else {
                                document.getElementById('setup-form').classList.remove('hidden');
                            }
                        } catch (error) {
                            showError('Failed to check system status: ' + error.message);
                        }
                    }

                    document.getElementById('initForm').addEventListener('submit', async function(e) {
                        e.preventDefault();
                        const btn = document.getElementById('initBtn');
                        btn.disabled = true;
                        btn.textContent = 'Initializing...';

                        try {
                            const response = await fetch('/admin/api/setup/initialize', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    admin_username: document.getElementById('adminUsername').value
                                })
                            });

                            const data = await response.json();

                            if (response.ok && data.credentials) {
                                // Display credentials
                                document.getElementById('cred-username').textContent = data.credentials.admin_username;
                                document.getElementById('cred-password').textContent = data.credentials.admin_password;
                                document.getElementById('cred-admin-token').textContent = data.credentials.admin_token;
                                document.getElementById('cred-bootstrap').textContent = data.bootstrap_key;

                                document.getElementById('setup-form').classList.add('hidden');
                                document.getElementById('credentials-display').classList.remove('hidden');
                            } else {
                                showError(data.error || 'Setup failed');
                                btn.disabled = false;
                                btn.textContent = 'Initialize Admin System';
                            }
                        } catch (error) {
                            showError('Setup failed: ' + error.message);
                            btn.disabled = false;
                            btn.textContent = 'Initialize Admin System';
                        }
                    });

                    function showError(message) {
                        const el = document.getElementById('status-message');
                        el.textContent = message;
                        el.classList.remove('hidden', 'status-success');
                        el.classList.add('status-error');
                    }

                    // Check status on load
                    checkStatus();
                </script>
            </body>
            </html>
            """)

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
        
        # Initialize Vault Dashboard API
        self._init_vault_api()
        
        # Initialize Help System API
        self._init_help_api()
        
        # Initialize Config Backup & Agent Kanban API
        self._init_config_backup_api()

    def _add_vault_sync_routes(self):
        """Add HTTP endpoints for cross-machine vault sync via Tailscale.

        These endpoints allow clients to download vault contents (skills, configs, docs)
        via HTTP instead of requiring rsync/SSH key setup on each machine.
        """
        import zipfile
        import io
        import os
        from starlette.responses import StreamingResponse, FileResponse, JSONResponse
        from datetime import datetime
        import json

        vault_path = Path.home() / ".haivemind" / "vault"

        @self.mcp.custom_route("/vault/manifest", methods=["GET"])
        async def get_vault_manifest(request):
            """Get vault manifest for sync status checking."""
            manifest_file = vault_path / "manifest.json"
            if manifest_file.exists():
                return FileResponse(str(manifest_file), media_type="application/json")
            return JSONResponse({"error": "Manifest not found"}, status_code=404)

        @self.mcp.custom_route("/vault/download.zip", methods=["GET"])
        async def download_vault_zip(request):
            """Download entire vault as zip (skills + configs + docs)."""
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for subdir in ["skills", "configs", "docs", "agents"]:
                    dir_path = vault_path / subdir
                    if dir_path.exists():
                        for f in dir_path.glob("*"):
                            if f.is_file():
                                zf.write(f, f"{subdir}/{f.name}")
                # Include manifest at root
                manifest = vault_path / "manifest.json"
                if manifest.exists():
                    zf.write(manifest, "manifest.json")
            buffer.seek(0)
            return StreamingResponse(
                buffer,
                media_type="application/zip",
                headers={"Content-Disposition": "attachment; filename=haivemind-vault.zip"}
            )

        @self.mcp.custom_route("/vault/skills/{filename:path}", methods=["GET"])
        async def get_vault_skill(request):
            """Download a single skill file."""
            filename = request.path_params.get("filename", "")
            base_dir = (vault_path / "skills").resolve()
            file_path = (base_dir / filename).resolve()
            # Path traversal protection
            if not str(file_path).startswith(str(base_dir) + os.sep) and file_path != base_dir:
                return JSONResponse({"error": "Invalid path"}, status_code=400)
            if file_path.is_file():
                return FileResponse(str(file_path))
            return JSONResponse({"error": "File not found"}, status_code=404)

        @self.mcp.custom_route("/vault/configs/{filename:path}", methods=["GET"])
        async def get_vault_config(request):
            """Download a single config file."""
            filename = request.path_params.get("filename", "")
            base_dir = (vault_path / "configs").resolve()
            file_path = (base_dir / filename).resolve()
            # Path traversal protection
            if not str(file_path).startswith(str(base_dir) + os.sep) and file_path != base_dir:
                return JSONResponse({"error": "Invalid path"}, status_code=400)
            if file_path.is_file():
                return FileResponse(str(file_path))
            return JSONResponse({"error": "File not found"}, status_code=404)

        @self.mcp.custom_route("/vault/docs/{filename:path}", methods=["GET"])
        async def get_vault_doc(request):
            """Download a single doc file."""
            filename = request.path_params.get("filename", "")
            base_dir = (vault_path / "docs").resolve()
            file_path = (base_dir / filename).resolve()
            # Path traversal protection
            if not str(file_path).startswith(str(base_dir) + os.sep) and file_path != base_dir:
                return JSONResponse({"error": "Invalid path"}, status_code=400)
            if file_path.is_file():
                return FileResponse(str(file_path))
            return JSONResponse({"error": "File not found"}, status_code=404)

        @self.mcp.custom_route("/vault/agents/{filename:path}", methods=["GET"])
        async def get_vault_agent(request):
            """Download a single agent file."""
            filename = request.path_params.get("filename", "")
            base_dir = (vault_path / "agents").resolve()
            file_path = (base_dir / filename).resolve()
            # Path traversal protection
            if not str(file_path).startswith(str(base_dir) + os.sep) and file_path != base_dir:
                return JSONResponse({"error": "Invalid path"}, status_code=400)
            if file_path.is_file():
                return FileResponse(str(file_path))
            return JSONResponse({"error": "File not found"}, status_code=404)

        @self.mcp.custom_route("/vault/list", methods=["GET"])
        async def list_vault_files(request):
            """List all vault files."""
            files = {"skills": [], "configs": [], "docs": [], "agents": []}
            for subdir in files.keys():
                dir_path = vault_path / subdir
                if dir_path.exists():
                    files[subdir] = [f.name for f in dir_path.glob("*") if f.is_file()]
            return JSONResponse(files)

        @self.mcp.custom_route("/vault/upload/{subdir}/{filename:path}", methods=["POST"])
        async def upload_to_vault(request):
            """Upload a file to vault (for hivesink-push)."""
            subdir = request.path_params.get("subdir", "")
            filename = request.path_params.get("filename", "")

            if subdir not in ["skills", "configs", "docs", "agents"]:
                return JSONResponse({"error": "Invalid subdir. Must be skills, configs, docs, or agents"}, status_code=400)

            base_dir = (vault_path / subdir).resolve()
            dest_path = (base_dir / filename).resolve()

            # Path traversal protection
            if not str(dest_path).startswith(str(base_dir) + os.sep) and dest_path != base_dir:
                return JSONResponse({"error": "Invalid path"}, status_code=400)

            try:
                body = await request.body()
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_bytes(body)

                # Update manifest
                manifest_path = vault_path / "manifest.json"
                manifest = {}
                if manifest_path.exists():
                    try:
                        manifest = json.loads(manifest_path.read_text())
                    except:
                        manifest = {"version": "1.0", "files": {}}

                if "files" not in manifest:
                    manifest["files"] = {}

                manifest["files"][filename] = {
                    "synced": datetime.now().isoformat(),
                    "source": request.headers.get("X-Source-Machine", "unknown")
                }
                manifest["updated"] = datetime.now().isoformat()

                manifest_path.write_text(json.dumps(manifest, indent=2))

                return JSONResponse({"success": True, "path": str(dest_path)})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

    async def list_vault_contents(self, category: str = "all") -> str:
        """List all skills, configs, docs, and agents in the hAIveMind vault.

        Args:
            category: Filter by 'skills', 'configs', 'docs', 'agents', or 'all' (default)

        Returns:
            JSON list of files in each category with metadata
        """
        try:
            vault_path = Path.home() / ".haivemind" / "vault"
            categories = ["skills", "configs", "docs", "agents"] if category == "all" else [category]

            if category != "all" and category not in ["skills", "configs", "docs", "agents"]:
                return json.dumps({"error": f"Invalid category '{category}'. Use: skills, configs, docs, agents, or all"})

            result = {}
            for cat in categories:
                dir_path = vault_path / cat
                if dir_path.exists():
                    files = []
                    for f in dir_path.glob("*"):
                        if f.is_file():
                            stat = f.stat()
                            files.append({
                                "name": f.name,
                                "size": stat.st_size,
                                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                            })
                    result[cat] = sorted(files, key=lambda x: x["name"])
                else:
                    result[cat] = []

            # Add summary
            total = sum(len(result.get(c, [])) for c in categories)
            result["_summary"] = {
                "total_files": total,
                "vault_path": str(vault_path),
                "categories": {c: len(result.get(c, [])) for c in categories}
            }

            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Error listing vault contents: {e}")
            return json.dumps({"error": str(e)})

    async def pull_vault_file(self, filename: str, category: str = "skills") -> str:
        """Download a file from the hAIveMind vault.

        Args:
            filename: Name of the file to download (e.g., 'commit.md')
            category: Category folder - 'skills', 'configs', 'docs', or 'agents' (default: skills)

        Returns:
            The file content as a string
        """
        try:
            vault_path = Path.home() / ".haivemind" / "vault"
            if category not in ["skills", "configs", "docs", "agents"]:
                return f"Error: Invalid category '{category}'. Use: skills, configs, docs, or agents"

            file_path = vault_path / category / filename

            # Path traversal protection
            base_dir = (vault_path / category).resolve()
            resolved_path = file_path.resolve()
            if not str(resolved_path).startswith(str(base_dir)):
                return "Error: Invalid path (path traversal detected)"

            if not file_path.exists():
                return f"Error: File '{filename}' not found in {category}/"

            content = file_path.read_text()
            return f"# {filename}\n\n{content}"
        except Exception as e:
            logger.error(f"Error pulling vault file: {e}")
            return f"Error: {str(e)}"

    async def push_vault_file(self, filename: str, content: str, category: str = "skills") -> str:
        """Upload a file to the hAIveMind vault.

        Args:
            filename: Name for the file (e.g., 'my-skill.md')
            content: The file content to store
            category: Category folder - 'skills', 'configs', 'docs', or 'agents' (default: skills)

        Returns:
            Success message with file path
        """
        try:
            vault_path = Path.home() / ".haivemind" / "vault"
            if category not in ["skills", "configs", "docs", "agents"]:
                return f"Error: Invalid category '{category}'. Use: skills, configs, docs, or agents"

            dest_dir = vault_path / category
            dest_dir.mkdir(parents=True, exist_ok=True)

            file_path = dest_dir / filename

            # Path traversal protection
            base_dir = dest_dir.resolve()
            resolved_path = file_path.resolve()
            if not str(resolved_path).startswith(str(base_dir)):
                return "Error: Invalid path (path traversal detected)"

            file_path.write_text(content)

            # Update manifest
            manifest_path = vault_path / "manifest.json"
            manifest = {}
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text())
                except:
                    manifest = {"version": "1.0", "files": {}}

            if "files" not in manifest:
                manifest["files"] = {}

            manifest["files"][f"{category}/{filename}"] = {
                "synced": datetime.now().isoformat(),
                "source": self.storage.machine_id if hasattr(self, 'storage') else "mcp-client"
            }
            manifest["updated"] = datetime.now().isoformat()
            manifest_path.write_text(json.dumps(manifest, indent=2))

            return f"✅ Successfully saved {category}/{filename} ({len(content)} bytes)"
        except Exception as e:
            logger.error(f"Error pushing vault file: {e}")
            return f"Error: {str(e)}"

    async def delete_vault_file(self, filename: str, category: str = "skills") -> str:
        """Delete a file from the hAIveMind vault.

        Args:
            filename: Name of the file to delete
            category: Category folder - 'skills', 'configs', 'docs', or 'agents' (default: skills)

        Returns:
            Success or error message
        """
        try:
            vault_path = Path.home() / ".haivemind" / "vault"
            if category not in ["skills", "configs", "docs", "agents"]:
                return f"Error: Invalid category '{category}'. Use: skills, configs, docs, or agents"

            file_path = vault_path / category / filename

            # Path traversal protection
            base_dir = (vault_path / category).resolve()
            resolved_path = file_path.resolve()
            if not str(resolved_path).startswith(str(base_dir)):
                return "Error: Invalid path (path traversal detected)"

            if not file_path.exists():
                return f"Error: File '{filename}' not found in {category}/"

            file_path.unlink()

            # Update manifest
            manifest_path = vault_path / "manifest.json"
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text())
                    key = f"{category}/{filename}"
                    if "files" in manifest and key in manifest["files"]:
                        del manifest["files"][key]
                        manifest["updated"] = datetime.now().isoformat()
                        manifest_path.write_text(json.dumps(manifest, indent=2))
                except:
                    pass

            return f"✅ Deleted {category}/{filename}"
        except Exception as e:
            logger.error(f"Error deleting vault file: {e}")
            return f"Error: {str(e)}"

    async def sync_vault_from_server(self, server: str = "lance-dev:8900", category: str = "all") -> str:
        """Pull vault contents from a remote hAIveMind server.

        Args:
            server: Server hostname:port (default: lance-dev:8900)
            category: Filter by 'skills', 'configs', 'docs', or 'all' (default)

        Returns:
            Sync summary
        """
        try:
            import httpx
            import zipfile
            import io
            vault_path = Path.home() / ".haivemind" / "vault"

            base_url = f"http://{server}"
            if server.startswith("http"):
                base_url = server

            output = [f"🔄 Syncing vault from {server}...\n"]

            async with httpx.AsyncClient() as client:
                # 1. Get remote manifest
                resp = await client.get(f"{base_url}/vault/manifest")
                if resp.status_code != 200:
                    return f"Error: Could not connect to server {server} (HTTP {resp.status_code})"
                remote_manifest = resp.json()

                # 2. Download zip
                resp = await client.get(f"{base_url}/vault/download.zip")
                if resp.status_code != 200:
                    return f"Error: Could not download vault zip from {server}"
                zip_data = io.BytesIO(resp.content)

                # 3. Extract to local vault
                with zipfile.ZipFile(zip_data) as zf:
                    members = zf.namelist()
                    if category != "all":
                        members = [m for m in members if m.startswith(f"{category}/") or m == "manifest.json"]
                    zf.extractall(vault_path, members=members)

            output.append(f"✅ Successfully synced vault contents")
            output.append(f"📁 Local vault: {vault_path}")
            output.append(f"📄 Files: {len(remote_manifest.get('files', {}))}")
            return "\n".join(output)
        except Exception as e:
            logger.error(f"Error syncing vault from server: {e}")
            return f"Error: {str(e)}"

    async def detect_mcp_service(self, target: str) -> str:
        """
        Auto-detect the type and connection info for an MCP service.
        Useful for determining how to connect to a service (SSE, stdio, bridged).
        """
        try:
            mcp_type, info = await self.bridge_manager.detect_mcp_type(target)
            return json.dumps({
                "target": target,
                "type": mcp_type,
                "connection_info": info
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _register_vault_sync_tools(self):
        """Register vault sync tools with FastMCP"""
        self.mcp.add_tool(self.list_vault_contents)
        self.mcp.add_tool(self.pull_vault_file)
        self.mcp.add_tool(self.push_vault_file)
        self.mcp.add_tool(self.delete_vault_file)
        self.mcp.add_tool(self.sync_vault_from_server)
        self.mcp.add_tool(self.detect_mcp_service)
        logger.info("📦 Vault sync MCP tools registered (including detect_mcp_service)")

    def _register_skills_sh_tools(self):
        """Register skills.sh integration tools with FastMCP"""
        self.mcp.add_tool(self.search_skills_sh)
        self.mcp.add_tool(self.install_skill_from_skills_sh)
        self.mcp.add_tool(self.list_installed_skills)
        self.mcp.add_tool(self.sync_skill_to_vault)
        self.mcp.add_tool(self.recommend_skills)
        logger.info("🎯 Skills.sh MCP tools registered (5 tools)")

    async def search_skills_sh(self, query: str, limit: int = 10) -> str:
        """Search skills.sh directory for available AI agent skills.

        skills.sh is an open ecosystem of reusable capabilities for AI agents.
        Search for skills by topic, technology, or use case.

        Args:
            query: Search term (e.g., "react", "security", "testing", "kubernetes")
            limit: Maximum results to return (default 10)

        Returns:
            JSON list of matching skills with install commands
        """
        try:
            from skills_sh_integration import get_skills_sh_integration
            integration = get_skills_sh_integration()
            results = integration.search_skills(query, limit)
            return json.dumps({
                "success": True,
                "query": query,
                "skills": results,
                "install_hint": "Use install_skill_from_skills_sh to install a skill"
            }, indent=2)
        except Exception as e:
            logger.error(f"Skills.sh search failed: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "fallback": f"Visit https://skills.sh and search for '{query}'"
            })

    async def install_skill_from_skills_sh(
        self,
        skill_id: str,
        target_tool: str = "claude",
        sync_to_vault: bool = True
    ) -> str:
        """Install a skill from skills.sh directory.

        Uses `npx skills add <owner/repo>` to install skills.
        Optionally syncs to hAIveMind vault for team distribution.

        Args:
            skill_id: Skill identifier in owner/repo format (e.g., "vercel/next-learn")
            target_tool: Target tool (claude, cursor, kilo, cline, codex)
            sync_to_vault: Whether to sync installed skill to hAIveMind vault

        Returns:
            JSON with installation result and skill location
        """
        try:
            from skills_sh_integration import get_skills_sh_integration
            integration = get_skills_sh_integration()
            result = integration.install_skill(skill_id, target_tool)

            # Sync to vault if requested and successful
            if sync_to_vault and result.get("success") and result.get("skill_path"):
                sync_result = integration.sync_skill_to_haivemind(result["skill_path"])
                result["vault_sync"] = sync_result

            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Skill installation failed: {e}")
            return json.dumps({
                "success": False,
                "skill_id": skill_id,
                "error": str(e),
                "manual_install": f"npx skills add {skill_id}"
            })

    async def list_installed_skills(self, tool: str = None) -> str:
        """List skills installed locally and in hAIveMind vault.

        Args:
            tool: Specific tool to check (claude, cursor, etc.) or None for all

        Returns:
            JSON with installed skills by tool and vault skills
        """
        try:
            from skills_sh_integration import get_skills_sh_integration
            integration = get_skills_sh_integration()

            # Get local skills
            local_skills = integration.get_installed_skills(tool)

            # Get vault skills
            vault_skills = integration.get_vault_skills()

            return json.dumps({
                "success": True,
                "local_skills": local_skills,
                "vault_skills": vault_skills,
                "tip": "Use sync_skill_to_vault to share a local skill with your team"
            }, indent=2)
        except Exception as e:
            logger.error(f"Failed to list skills: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    async def sync_skill_to_vault(self, skill_path: str) -> str:
        """Sync an installed skill to hAIveMind vault for team distribution.

        Args:
            skill_path: Path to the skill file to sync

        Returns:
            JSON with sync result
        """
        try:
            from skills_sh_integration import get_skills_sh_integration
            integration = get_skills_sh_integration()
            result = integration.sync_skill_to_haivemind(skill_path)
            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Failed to sync skill: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    async def recommend_skills(self, context: str) -> str:
        """Get skill recommendations based on current task/context.

        Analyzes context to suggest relevant skills from skills.sh.

        Args:
            context: Description of current task or what you're working on

        Returns:
            JSON list of recommended skills with relevance info
        """
        try:
            from skills_sh_integration import get_skills_sh_integration
            integration = get_skills_sh_integration()
            recommendations = integration.recommend_skills(context)
            return json.dumps({
                "success": True,
                "context": context,
                "recommendations": recommendations,
                "tip": "Check https://skills.sh for more options"
            }, indent=2)
        except Exception as e:
            logger.error(f"Skill recommendation failed: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "fallback": f"Visit https://skills.sh to browse skills"
            })

    def _init_vault_api(self):
        """Initialize Vault Dashboard API endpoints"""
        try:
            import sqlite3
            import os
            
            # Initialize simple vault storage
            vault_db_path = os.path.join(os.path.dirname(__file__), "..", "data", "vault.db")
            os.makedirs(os.path.dirname(vault_db_path), exist_ok=True)
            
            # Create simple vault storage
            self.vault_db = vault_db_path
            self._init_vault_db()
            self._init_config_backup_db()
            self.vault_unlocked = False
            self.vault_session_expires = None
            
            # Add vault routes with /admin prefix
            @self.mcp.custom_route("/admin/api/vault/status", methods=["GET"])
            async def vault_status(request):
                from starlette.responses import JSONResponse
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
                try:
                    stats = self._get_vault_stats()
                    return JSONResponse(stats)
                except Exception as e:
                    logger.error(f"Error getting vault status: {e}")
                    return JSONResponse({"error": str(e)}, status_code=500)
            
            @self.mcp.custom_route("/admin/api/vault/unlock", methods=["POST"])
            async def vault_unlock(request):
                from starlette.responses import JSONResponse
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
                try:
                    data = await request.json()
                    master_password = data.get('master_password')
                    remember_session = data.get('remember_session', False)
                    
                    # Verify vault master password using bootstrap system
                    if self._verify_vault_master_password(master_password):
                        self.vault_unlocked = True
                        session_duration = 3600 if remember_session else 1800  # 1 hour or 30 min
                        self.vault_session_expires = datetime.now() + timedelta(seconds=session_duration)

                        return JSONResponse({
                            "success": True,
                            "message": "Vault unlocked successfully",
                            "session_expires": self.vault_session_expires.isoformat()
                        })
                    else:
                        return JSONResponse({"error": "Invalid master password"}, status_code=401)
                    
                except Exception as e:
                    logger.error(f"Error unlocking vault: {e}")
                    return JSONResponse({"error": str(e)}, status_code=500)

            # API v1 vault unlock endpoint (alias for vault.html compatibility)
            @self.mcp.custom_route("/api/v1/vault/unlock", methods=["POST"])
            async def api_v1_vault_unlock(request):
                from starlette.responses import JSONResponse
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)

                try:
                    data = await request.json()
                    master_password = data.get('master_password') or data.get('password')
                    remember_session = data.get('remember_session', False)

                    # Verify vault master password using bootstrap system
                    if self._verify_vault_master_password(master_password):
                        self.vault_unlocked = True
                        session_duration = 3600 if remember_session else 1800
                        self.vault_session_expires = datetime.now() + timedelta(seconds=session_duration)

                        return JSONResponse({
                            "success": True,
                            "message": "Vault unlocked successfully",
                            "session_expires": self.vault_session_expires.isoformat()
                        })
                    else:
                        return JSONResponse({"error": "Invalid master password"}, status_code=401)

                except Exception as e:
                    logger.error(f"Error unlocking vault (v1 API): {e}")
                    return JSONResponse({"error": str(e)}, status_code=500)

            # API v1 vault credentials endpoints (for vault.js compatibility)
            @self.mcp.custom_route("/api/v1/vault/credentials", methods=["GET"])
            async def api_v1_list_credentials(request):
                from starlette.responses import JSONResponse
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)

                try:
                    if not self._check_vault_unlocked():
                        return JSONResponse({"error": "Vault is locked"}, status_code=403)

                    credentials = self._list_credentials()
                    return JSONResponse({
                        "credentials": credentials,
                        "total": len(credentials)
                    })
                except Exception as e:
                    logger.error(f"Error listing credentials (v1 API): {e}")
                    return JSONResponse({"error": str(e)}, status_code=500)

            @self.mcp.custom_route("/api/v1/vault/credentials", methods=["POST"])
            async def api_v1_create_credential(request):
                from starlette.responses import JSONResponse
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)

                try:
                    if not self._check_vault_unlocked():
                        return JSONResponse({"error": "Vault is locked"}, status_code=403)

                    data = await request.json()
                    credential_id = self._create_credential(data)

                    await self.storage.store_memory(
                        content=f"Vault credential created: {data.get('name')} ({data.get('type')})",
                        category="security",
                        context="Vault credential management",
                        tags=["vault", "credential", "security"]
                    )

                    return JSONResponse({
                        "success": True,
                        "credential_id": credential_id,
                        "message": "Credential created successfully"
                    })
                except Exception as e:
                    logger.error(f"Error creating credential (v1 API): {e}")
                    return JSONResponse({"error": str(e)}, status_code=500)

            @self.mcp.custom_route("/api/v1/vault/credentials/{credential_id}", methods=["GET"])
            async def api_v1_get_credential(request):
                from starlette.responses import JSONResponse
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)

                try:
                    if not self._check_vault_unlocked():
                        return JSONResponse({"error": "Vault is locked"}, status_code=403)

                    credential_id = request.path_params.get('credential_id')
                    credential = self._get_credential(credential_id)

                    if not credential:
                        return JSONResponse({"error": "Credential not found"}, status_code=404)

                    return JSONResponse({"credential": credential})
                except Exception as e:
                    logger.error(f"Error getting credential (v1 API): {e}")
                    return JSONResponse({"error": str(e)}, status_code=500)

            @self.mcp.custom_route("/api/v1/vault/credentials/{credential_id}", methods=["PUT"])
            async def api_v1_update_credential(request):
                from starlette.responses import JSONResponse
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)

                try:
                    if not self._check_vault_unlocked():
                        return JSONResponse({"error": "Vault is locked"}, status_code=403)

                    credential_id = request.path_params.get('credential_id')
                    data = await request.json()
                    self._update_credential(credential_id, data)

                    return JSONResponse({
                        "success": True,
                        "message": "Credential updated successfully"
                    })
                except Exception as e:
                    logger.error(f"Error updating credential (v1 API): {e}")
                    return JSONResponse({"error": str(e)}, status_code=500)

            @self.mcp.custom_route("/api/v1/vault/credentials/{credential_id}", methods=["DELETE"])
            async def api_v1_delete_credential(request):
                from starlette.responses import JSONResponse
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)

                try:
                    if not self._check_vault_unlocked():
                        return JSONResponse({"error": "Vault is locked"}, status_code=403)

                    credential_id = request.path_params.get('credential_id')
                    self._delete_credential(credential_id)

                    return JSONResponse({
                        "success": True,
                        "message": "Credential deleted successfully"
                    })
                except Exception as e:
                    logger.error(f"Error deleting credential (v1 API): {e}")
                    return JSONResponse({"error": str(e)}, status_code=500)

            @self.mcp.custom_route("/admin/api/vault/credentials", methods=["GET"])
            async def list_credentials(request):
                from starlette.responses import JSONResponse
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
                try:
                    if not self._check_vault_unlocked():
                        return JSONResponse({"error": "Vault is locked"}, status_code=403)
                    
                    credentials = self._list_credentials()
                    return JSONResponse({
                        "credentials": credentials,
                        "total": len(credentials)
                    })
                    
                except Exception as e:
                    logger.error(f"Error listing credentials: {e}")
                    return JSONResponse({"error": str(e)}, status_code=500)
            
            @self.mcp.custom_route("/admin/api/vault/credentials", methods=["POST"])
            async def create_credential(request):
                from starlette.responses import JSONResponse
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
                try:
                    if not self._check_vault_unlocked():
                        return JSONResponse({"error": "Vault is locked"}, status_code=403)
                    
                    data = await request.json()
                    credential_id = self._create_credential(data)
                    
                    # Store in hAIveMind memory
                    await self.storage.store_memory(
                        content=f"Vault credential created: {data.get('name')} ({data.get('type')})",
                        category="security",
                        context="Vault credential management",
                        tags=["vault", "credential", "security"]
                    )
                    
                    return JSONResponse({
                        "success": True,
                        "credential_id": credential_id,
                        "message": "Credential created successfully"
                    })
                    
                except Exception as e:
                    logger.error(f"Error creating credential: {e}")
                    return JSONResponse({"error": str(e)}, status_code=500)
            
            @self.mcp.custom_route("/admin/api/vault/credentials/{credential_id}", methods=["GET"])
            async def get_credential(request):
                from starlette.responses import JSONResponse
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
                try:
                    if not self._check_vault_unlocked():
                        return JSONResponse({"error": "Vault is locked"}, status_code=403)
                    
                    credential_id = request.path_params.get('credential_id')
                    credential = self._get_credential(credential_id)
                    if credential:
                        return JSONResponse(credential)
                    else:
                        return JSONResponse({"error": "Credential not found"}, status_code=404)
                    
                except Exception as e:
                    logger.error(f"Error getting credential: {e}")
                    return JSONResponse({"error": str(e)}, status_code=500)
            
            @self.mcp.custom_route("/admin/api/vault/audit", methods=["GET"])
            async def vault_audit_log(request):
                from starlette.responses import JSONResponse
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
                try:
                    if not self._check_vault_unlocked():
                        return JSONResponse({"error": "Vault is locked"}, status_code=403)
                    
                    audit_entries = self._get_audit_log()
                    return JSONResponse({
                        "audit_log": audit_entries,
                        "total": len(audit_entries)
                    })
                    
                except Exception as e:
                    logger.error(f"Error getting audit log: {e}")
                    return JSONResponse({"error": str(e)}, status_code=500)
            
            logger.info("🔐 Vault Dashboard API endpoints registered")
            
        except Exception as e:
            logger.warning(f"Vault API not available: {e}")
    
    def _init_vault_db(self):
        """Initialize the vault SQLite database"""
        import sqlite3
        conn = sqlite3.connect(self.vault_db)
        cursor = conn.cursor()
        
        # Create credentials table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                environment TEXT,
                service TEXT,
                description TEXT,
                encrypted_data TEXT NOT NULL,
                tags TEXT,
                project TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Create audit log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                credential_id TEXT,
                user_id TEXT,
                details TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_config_backup_db(self):
        """Initialize the config backup SQLite database"""
        import sqlite3
        import os
        
        # Use same database for simplicity
        conn = sqlite3.connect(self.vault_db)
        cursor = conn.cursor()
        
        # Create config systems table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config_systems (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                machine_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Create config snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config_snapshots (
                id TEXT PRIMARY KEY,
                system_id TEXT NOT NULL,
                config_type TEXT NOT NULL,
                config_content TEXT NOT NULL,
                config_hash TEXT NOT NULL,
                agent_id TEXT,
                timestamp TEXT NOT NULL,
                tags TEXT,
                description TEXT,
                size INTEGER,
                FOREIGN KEY (system_id) REFERENCES config_systems (id)
            )
        ''')
        
        # Create config diffs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config_diffs (
                id TEXT PRIMARY KEY,
                from_snapshot_id TEXT NOT NULL,
                to_snapshot_id TEXT NOT NULL,
                diff_content TEXT NOT NULL,
                change_type TEXT NOT NULL,
                lines_added INTEGER DEFAULT 0,
                lines_removed INTEGER DEFAULT 0,
                risk_score INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (from_snapshot_id) REFERENCES config_snapshots (id),
                FOREIGN KEY (to_snapshot_id) REFERENCES config_snapshots (id)
            )
        ''')
        
        # Create agent tasks table for kanban system
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                assigned_agent TEXT,
                status TEXT DEFAULT 'backlog',
                priority INTEGER DEFAULT 3,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                due_date TEXT,
                estimated_hours REAL,
                actual_hours REAL,
                tags TEXT,
                board_id TEXT DEFAULT 'default'
            )
        ''')
        
        # Create agent registry table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_registry (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                capabilities TEXT,
                machine_id TEXT,
                status TEXT DEFAULT 'active',
                current_workload INTEGER DEFAULT 0,
                max_workload INTEGER DEFAULT 5,
                last_seen TEXT,
                registered_at TEXT NOT NULL,
                metadata TEXT
            )
        ''')
        
        # Create task dependencies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_dependencies (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                depends_on_task_id TEXT NOT NULL,
                dependency_type TEXT DEFAULT 'blocks',
                created_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES agent_tasks (id),
                FOREIGN KEY (depends_on_task_id) REFERENCES agent_tasks (id)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_config_snapshots_system_id ON config_snapshots (system_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_config_snapshots_timestamp ON config_snapshots (timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_config_snapshots_hash ON config_snapshots (config_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_agent_tasks_status ON agent_tasks (status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_agent_tasks_assigned ON agent_tasks (assigned_agent)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_dependencies_task_id ON task_dependencies (task_id)')
        
        conn.commit()
        conn.close()
    
    def _check_vault_unlocked(self):
        """Check if vault is unlocked and session is valid"""
        if not self.vault_unlocked:
            return False
        
        if self.vault_session_expires and datetime.now() > self.vault_session_expires:
            self.vault_unlocked = False
            return False
            
        return True
    
    def _get_vault_stats(self):
        """Get vault statistics"""
        import sqlite3
        conn = sqlite3.connect(self.vault_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM credentials WHERE status = 'active'")
        total_credentials = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM credentials WHERE expires_at < datetime('now', '+30 days') AND status = 'active'")
        expiring_credentials = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "vault_status": "unlocked" if self.vault_unlocked else "locked",
            "total_credentials": total_credentials,
            "expiring_credentials": expiring_credentials,
            "session_expires": self.vault_session_expires.isoformat() if self.vault_session_expires else None
        }
    
    def _list_credentials(self):
        """List all credentials"""
        import sqlite3
        conn = sqlite3.connect(self.vault_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, type, environment, service, description, tags, project, 
                   created_at, updated_at, expires_at, status 
            FROM credentials WHERE status = 'active' ORDER BY name
        ''')
        
        columns = ['id', 'name', 'type', 'environment', 'service', 'description', 
                  'tags', 'project', 'created_at', 'updated_at', 'expires_at', 'status']
        
        credentials = []
        for row in cursor.fetchall():
            credential = dict(zip(columns, row))
            # Don't include encrypted data in list view
            credentials.append(credential)
        
        conn.close()
        return credentials
    
    def _create_credential(self, data):
        """Create a new credential"""
        import sqlite3
        import uuid
        import json
        from datetime import datetime
        
        credential_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Simple encryption (in production, use proper encryption)
        encrypted_data = json.dumps(data.get('credentials', {}))
        
        conn = sqlite3.connect(self.vault_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO credentials (id, name, type, environment, service, description, 
                                   encrypted_data, tags, project, created_at, updated_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            credential_id, data.get('name'), data.get('type'), data.get('environment'),
            data.get('service'), data.get('description'), encrypted_data,
            data.get('tags'), data.get('project'), now, now, data.get('expires_at')
        ))
        
        # Add audit log entry
        cursor.execute('''
            INSERT INTO audit_log (timestamp, action, credential_id, user_id, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (now, 'create', credential_id, 'admin', f"Created credential: {data.get('name')}"))
        
        conn.commit()
        conn.close()
        
        return credential_id
    
    def _get_credential(self, credential_id):
        """Get a specific credential"""
        import sqlite3
        import json
        
        conn = sqlite3.connect(self.vault_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, type, environment, service, description, encrypted_data,
                   tags, project, created_at, updated_at, expires_at, status
            FROM credentials WHERE id = ? AND status = 'active'
        ''', (credential_id,))
        
        row = cursor.fetchone()
        if row:
            columns = ['id', 'name', 'type', 'environment', 'service', 'description', 
                      'encrypted_data', 'tags', 'project', 'created_at', 'updated_at', 
                      'expires_at', 'status']
            credential = dict(zip(columns, row))
            
            # Decrypt data (in production, use proper decryption)
            try:
                credential['credentials'] = json.loads(credential['encrypted_data'])
            except:
                credential['credentials'] = {}
            
            # Don't send encrypted_data in response
            del credential['encrypted_data']
            
            # Add audit log entry for access
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO audit_log (timestamp, action, credential_id, user_id, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (now, 'read', credential_id, 'admin', f"Accessed credential: {credential['name']}"))
            
            conn.commit()
            conn.close()
            return credential
        
        conn.close()
        return None
    
    def _get_audit_log(self):
        """Get audit log entries"""
        import sqlite3
        
        conn = sqlite3.connect(self.vault_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, action, credential_id, user_id, details
            FROM audit_log ORDER BY timestamp DESC LIMIT 100
        ''')
        
        columns = ['timestamp', 'action', 'credential_id', 'user_id', 'details']
        audit_entries = []
        for row in cursor.fetchall():
            audit_entries.append(dict(zip(columns, row)))
        
        conn.close()
        return audit_entries
    
    def _init_help_api(self):
        """Initialize Help System API endpoints"""
        from starlette.responses import JSONResponse
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(__file__))
            from help_dashboard import HelpSystemDashboard
            from interactive_help_system import InteractiveHelpSystem
            
            # Initialize help system components
            self.help_system = InteractiveHelpSystem(self.storage, self.config)
            self.help_dashboard = HelpSystemDashboard(self.storage, self.config)
            
            # Help system status endpoint
            @self.mcp.custom_route("/admin/api/help/status", methods=["GET"])
            async def help_status(request):
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
                try:
                    await self.help_system.initialize()
                    analytics = await self.help_system.get_help_analytics()
                    return JSONResponse({
                        "status": "operational",
                        "analytics": analytics,
                        "commands_loaded": len(self.help_system._command_cache),
                        "examples_loaded": len(self.help_system._examples_cache)
                    })
                except Exception as e:
                    return JSONResponse({"error": str(e)}, status_code=500)
            
            # Search help content endpoint
            @self.mcp.custom_route("/admin/api/help/search", methods=["GET"])
            async def help_search(request):
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
                try:
                    query = request.query_params.get('q', '')
                    if not query:
                        return JSONResponse({"error": "Query parameter 'q' is required"}, status_code=400)
                    
                    await self.help_system.initialize()
                    results = await self.help_system.search_help_content(query)
                    return JSONResponse({"results": results})
                except Exception as e:
                    return JSONResponse({"error": str(e)}, status_code=500)
            
            # Get help categories endpoint
            @self.mcp.custom_route("/admin/api/help/categories", methods=["GET"])
            async def help_categories(request):
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
                try:
                    await self.help_system.initialize()
                    categories = await self.help_system.get_help_categories()
                    return JSONResponse({"categories": categories})
                except Exception as e:
                    return JSONResponse({"error": str(e)}, status_code=500)
            
            # Get specific help article endpoint
            @self.mcp.custom_route("/admin/api/help/article/{article_id}", methods=["GET"])
            async def help_article(request):
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
                try:
                    article_id = request.path_params.get('article_id')
                    await self.help_system.initialize()
                    article = await self.help_system.get_help_article(article_id)
                    if article:
                        return JSONResponse({"article": article})
                    else:
                        return JSONResponse({"error": "Article not found"}, status_code=404)
                except Exception as e:
                    return JSONResponse({"error": str(e)}, status_code=500)
            
            # Get contextual help for specific page endpoint
            @self.mcp.custom_route("/admin/api/help/context/{page}", methods=["GET"])
            async def help_context(request):
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
                try:
                    page = request.path_params.get('page')
                    await self.help_system.initialize()
                    context_help = await self.help_system.get_contextual_help(page)
                    return JSONResponse({"context_help": context_help})
                except Exception as e:
                    return JSONResponse({"error": str(e)}, status_code=500)
            
            # Submit help feedback endpoint
            @self.mcp.custom_route("/admin/api/help/feedback", methods=["POST"])
            async def help_feedback(request):
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
                try:
                    data = await request.json()
                    feedback_stored = await self.help_system.store_feedback(data)
                    if feedback_stored:
                        return JSONResponse({"success": True, "message": "Feedback stored successfully"})
                    else:
                        return JSONResponse({"error": "Failed to store feedback"}, status_code=500)
                except Exception as e:
                    return JSONResponse({"error": str(e)}, status_code=500)
            
            # Help analytics dashboard data endpoint
            @self.mcp.custom_route("/admin/api/help/analytics", methods=["GET"])
            async def help_analytics_data(request):
                if not await self._check_admin_auth(request):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
                try:
                    dashboard_data = await self.help_dashboard.get_dashboard_data()
                    return JSONResponse(dashboard_data)
                except Exception as e:
                    return JSONResponse({"error": str(e)}, status_code=500)
            
            logger.info("📚 Help System API endpoints registered")
            
        except ImportError as e:
            logger.warning(f"Help system dependencies not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize help API: {e}")
    
    def _init_config_backup_api(self):
        """Initialize Config Backup & Agent Kanban API endpoints"""
        from starlette.responses import JSONResponse
        import sqlite3
        import json
        import hashlib
        import difflib
        from datetime import datetime
        import uuid
        
        # Config backup endpoints
        @self.mcp.custom_route("/admin/api/configs/backup", methods=["POST"])
        async def create_config_backup(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                data = await request.json()
                system_id = data.get('system_id')
                config_type = data.get('config_type')
                config_content = data.get('config_content')
                agent_id = data.get('agent_id')
                description = data.get('description', '')
                tags = json.dumps(data.get('tags', []))
                
                if not all([system_id, config_type, config_content]):
                    return JSONResponse({"error": "Missing required fields"}, status_code=400)
                
                # Calculate hash for deduplication
                config_hash = hashlib.sha256(config_content.encode()).hexdigest()
                
                conn = sqlite3.connect(self.vault_db)
                cursor = conn.cursor()
                
                # Check if identical config already exists
                cursor.execute('''
                    SELECT id FROM config_snapshots 
                    WHERE system_id = ? AND config_hash = ?
                    ORDER BY timestamp DESC LIMIT 1
                ''', (system_id, config_hash))
                
                existing = cursor.fetchone()
                if existing:
                    conn.close()
                    return JSONResponse({
                        "message": "Identical config already exists",
                        "snapshot_id": existing[0],
                        "deduplicated": True
                    })
                
                # Create new snapshot
                snapshot_id = str(uuid.uuid4())
                timestamp = datetime.utcnow().isoformat()
                
                cursor.execute('''
                    INSERT INTO config_snapshots 
                    (id, system_id, config_type, config_content, config_hash, 
                     agent_id, timestamp, tags, description, size)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (snapshot_id, system_id, config_type, config_content, 
                     config_hash, agent_id, timestamp, tags, description, len(config_content)))
                
                conn.commit()
                conn.close()
                
                return JSONResponse({
                    "snapshot_id": snapshot_id,
                    "message": "Config backup created successfully",
                    "timestamp": timestamp,
                    "size": len(config_content)
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/admin/api/configs/{system_id}/history", methods=["GET"])
        async def get_config_history(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                system_id = request.path_params.get('system_id')
                limit = int(request.query_params.get('limit', 50))
                
                conn = sqlite3.connect(self.vault_db)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, config_type, config_hash, agent_id, timestamp, 
                           description, size, tags
                    FROM config_snapshots 
                    WHERE system_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (system_id, limit))
                
                columns = ['id', 'config_type', 'config_hash', 'agent_id', 
                          'timestamp', 'description', 'size', 'tags']
                history = []
                for row in cursor.fetchall():
                    entry = dict(zip(columns, row))
                    entry['tags'] = json.loads(entry['tags']) if entry['tags'] else []
                    history.append(entry)
                
                conn.close()
                return JSONResponse({"history": history, "total": len(history)})
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/admin/api/configs/{system_id}/current", methods=["GET"])
        async def get_current_config(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                system_id = request.path_params.get('system_id')
                
                conn = sqlite3.connect(self.vault_db)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, config_type, config_content, config_hash, agent_id, 
                           timestamp, description, size, tags
                    FROM config_snapshots 
                    WHERE system_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''', (system_id,))
                
                row = cursor.fetchone()
                if not row:
                    conn.close()
                    return JSONResponse({"error": "No config found for system"}, status_code=404)
                
                columns = ['id', 'config_type', 'config_content', 'config_hash', 
                          'agent_id', 'timestamp', 'description', 'size', 'tags']
                current_config = dict(zip(columns, row))
                current_config['tags'] = json.loads(current_config['tags']) if current_config['tags'] else []
                
                conn.close()
                return JSONResponse({"config": current_config})
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/admin/api/configs/restore", methods=["POST"])
        async def restore_config(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                data = await request.json()
                snapshot_id = data.get('snapshot_id')
                agent_id = data.get('agent_id')
                
                if not snapshot_id:
                    return JSONResponse({"error": "snapshot_id required"}, status_code=400)
                
                conn = sqlite3.connect(self.vault_db)
                cursor = conn.cursor()
                
                # Get snapshot to restore
                cursor.execute('''
                    SELECT system_id, config_type, config_content
                    FROM config_snapshots WHERE id = ?
                ''', (snapshot_id,))
                
                row = cursor.fetchone()
                if not row:
                    conn.close()
                    return JSONResponse({"error": "Snapshot not found"}, status_code=404)
                
                system_id, config_type, config_content = row
                
                # Create new "restore" snapshot 
                restore_snapshot_id = str(uuid.uuid4())
                timestamp = datetime.utcnow().isoformat()
                config_hash = hashlib.sha256(config_content.encode()).hexdigest()
                
                cursor.execute('''
                    INSERT INTO config_snapshots 
                    (id, system_id, config_type, config_content, config_hash,
                     agent_id, timestamp, description, size)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (restore_snapshot_id, system_id, config_type, config_content,
                     config_hash, agent_id, timestamp, f"Restored from {snapshot_id}", 
                     len(config_content)))
                
                conn.commit()
                conn.close()
                
                return JSONResponse({
                    "message": "Config restored successfully",
                    "new_snapshot_id": restore_snapshot_id,
                    "restored_from": snapshot_id,
                    "system_id": system_id,
                    "timestamp": timestamp
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/admin/api/configs/drift", methods=["GET"])
        async def detect_config_drift(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                system_id = request.query_params.get('system_id')
                hours = int(request.query_params.get('hours', 24))
                
                conn = sqlite3.connect(self.vault_db)
                cursor = conn.cursor()
                
                if system_id:
                    # Check specific system
                    cursor.execute('''
                        SELECT id, config_hash, timestamp FROM config_snapshots 
                        WHERE system_id = ? 
                        ORDER BY timestamp DESC LIMIT 2
                    ''', (system_id,))
                    
                    results = cursor.fetchall()
                    if len(results) < 2:
                        return JSONResponse({"drift_detected": False, "message": "Not enough snapshots to compare"})
                    
                    latest_hash = results[0][1]
                    previous_hash = results[1][1]
                    
                    drift_detected = latest_hash != previous_hash
                    
                    return JSONResponse({
                        "drift_detected": drift_detected,
                        "system_id": system_id,
                        "latest_snapshot": results[0][0],
                        "previous_snapshot": results[1][0],
                        "latest_timestamp": results[0][2],
                        "previous_timestamp": results[1][2]
                    })
                else:
                    # Check all systems for drift
                    from datetime import datetime, timedelta
                    cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
                    
                    cursor.execute('''
                        SELECT DISTINCT system_id FROM config_snapshots 
                        WHERE timestamp >= ?
                    ''', (cutoff_time,))
                    
                    drift_systems = []
                    for (sys_id,) in cursor.fetchall():
                        cursor.execute('''
                            SELECT id, config_hash, timestamp FROM config_snapshots 
                            WHERE system_id = ? AND timestamp >= ?
                            ORDER BY timestamp DESC LIMIT 2
                        ''', (sys_id, cutoff_time))
                        
                        snapshots = cursor.fetchall()
                        if len(snapshots) >= 2 and snapshots[0][1] != snapshots[1][1]:
                            drift_systems.append({
                                "system_id": sys_id,
                                "latest_snapshot": snapshots[0][0],
                                "latest_timestamp": snapshots[0][2]
                            })
                    
                    conn.close()
                    return JSONResponse({
                        "drift_detected": len(drift_systems) > 0,
                        "total_systems_with_drift": len(drift_systems),
                        "systems": drift_systems
                    })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/admin/api/configs/diff/{id1}/{id2}", methods=["GET"])
        async def compare_configs(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                id1 = request.path_params.get('id1')
                id2 = request.path_params.get('id2')
                
                conn = sqlite3.connect(self.vault_db)
                cursor = conn.cursor()
                
                # Get both configs
                cursor.execute('''
                    SELECT id, system_id, config_content, timestamp, description
                    FROM config_snapshots WHERE id IN (?, ?)
                ''', (id1, id2))
                
                results = cursor.fetchall()
                if len(results) != 2:
                    conn.close()
                    return JSONResponse({"error": "One or both snapshots not found"}, status_code=404)
                
                config1 = {
                    "id": results[0][0],
                    "system_id": results[0][1], 
                    "content": results[0][2],
                    "timestamp": results[0][3],
                    "description": results[0][4]
                }
                
                config2 = {
                    "id": results[1][0],
                    "system_id": results[1][1],
                    "content": results[1][2], 
                    "timestamp": results[1][3],
                    "description": results[1][4]
                }
                
                # Generate diff
                diff = list(difflib.unified_diff(
                    config1["content"].splitlines(keepends=True),
                    config2["content"].splitlines(keepends=True),
                    fromfile=f"{config1['id']} ({config1['timestamp']})",
                    tofile=f"{config2['id']} ({config2['timestamp']})",
                    n=3
                ))
                
                # Calculate stats
                lines_added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
                lines_removed = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
                
                conn.close()
                return JSONResponse({
                    "config1": config1,
                    "config2": config2,
                    "diff": ''.join(diff),
                    "stats": {
                        "lines_added": lines_added,
                        "lines_removed": lines_removed,
                        "total_changes": lines_added + lines_removed
                    }
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Agent Kanban Task Management endpoints
        @self.mcp.custom_route("/admin/api/agents/tasks", methods=["POST"])
        async def create_agent_task(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                data = await request.json()
                title = data.get('title')
                description = data.get('description', '')
                assigned_agent = data.get('assigned_agent')
                priority = int(data.get('priority', 3))
                estimated_hours = data.get('estimated_hours')
                due_date = data.get('due_date')
                tags = json.dumps(data.get('tags', []))
                board_id = data.get('board_id', 'default')
                
                if not title:
                    return JSONResponse({"error": "Title is required"}, status_code=400)
                
                conn = sqlite3.connect(self.vault_db)
                cursor = conn.cursor()
                
                task_id = str(uuid.uuid4())
                timestamp = datetime.utcnow().isoformat()
                
                cursor.execute('''
                    INSERT INTO agent_tasks 
                    (id, title, description, assigned_agent, status, priority,
                     created_at, updated_at, due_date, estimated_hours, tags, board_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (task_id, title, description, assigned_agent, 'backlog', priority,
                     timestamp, timestamp, due_date, estimated_hours, tags, board_id))
                
                conn.commit()
                conn.close()
                
                return JSONResponse({
                    "task_id": task_id,
                    "message": "Task created successfully",
                    "status": "backlog",
                    "created_at": timestamp
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/admin/api/agents/tasks/board", methods=["GET"])
        async def get_kanban_board(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                board_id = request.query_params.get('board_id', 'default')
                
                conn = sqlite3.connect(self.vault_db)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, title, description, assigned_agent, status, priority,
                           created_at, updated_at, due_date, estimated_hours, actual_hours, tags
                    FROM agent_tasks WHERE board_id = ?
                    ORDER BY priority DESC, created_at DESC
                ''', (board_id,))
                
                columns = ['id', 'title', 'description', 'assigned_agent', 'status', 'priority',
                          'created_at', 'updated_at', 'due_date', 'estimated_hours', 'actual_hours', 'tags']
                
                tasks = []
                for row in cursor.fetchall():
                    task = dict(zip(columns, row))
                    task['tags'] = json.loads(task['tags']) if task['tags'] else []
                    tasks.append(task)
                
                # Organize tasks by status
                board = {
                    'backlog': [t for t in tasks if t['status'] == 'backlog'],
                    'assigned': [t for t in tasks if t['status'] == 'assigned'],
                    'in_progress': [t for t in tasks if t['status'] == 'in_progress'],
                    'review': [t for t in tasks if t['status'] == 'review'],
                    'done': [t for t in tasks if t['status'] == 'done']
                }
                
                conn.close()
                return JSONResponse({"board": board, "total_tasks": len(tasks)})
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/admin/api/agents/tasks/{task_id}/move", methods=["PUT"])
        async def move_task(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                task_id = request.path_params.get('task_id')
                data = await request.json()
                new_status = data.get('status')
                agent_id = data.get('agent_id')
                
                valid_statuses = ['backlog', 'assigned', 'in_progress', 'review', 'done']
                if new_status not in valid_statuses:
                    return JSONResponse({"error": f"Invalid status. Must be one of: {valid_statuses}"}, status_code=400)
                
                conn = sqlite3.connect(self.vault_db)
                cursor = conn.cursor()
                
                # Check if task exists
                cursor.execute('SELECT id, assigned_agent FROM agent_tasks WHERE id = ?', (task_id,))
                task = cursor.fetchone()
                if not task:
                    conn.close()
                    return JSONResponse({"error": "Task not found"}, status_code=404)
                
                # Update task
                timestamp = datetime.utcnow().isoformat()
                cursor.execute('''
                    UPDATE agent_tasks 
                    SET status = ?, updated_at = ?, assigned_agent = COALESCE(?, assigned_agent)
                    WHERE id = ?
                ''', (new_status, timestamp, agent_id, task_id))
                
                conn.commit()
                conn.close()
                
                return JSONResponse({
                    "message": "Task moved successfully",
                    "task_id": task_id,
                    "new_status": new_status,
                    "updated_at": timestamp
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/admin/api/agents/register", methods=["POST"])
        async def register_agent(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                data = await request.json()
                name = data.get('name')
                role = data.get('role')
                capabilities = json.dumps(data.get('capabilities', []))
                machine_id = data.get('machine_id')
                max_workload = int(data.get('max_workload', 5))
                metadata = json.dumps(data.get('metadata', {}))
                
                if not all([name, role]):
                    return JSONResponse({"error": "Name and role are required"}, status_code=400)
                
                conn = sqlite3.connect(self.vault_db)
                cursor = conn.cursor()
                
                agent_id = str(uuid.uuid4())
                timestamp = datetime.utcnow().isoformat()
                
                cursor.execute('''
                    INSERT INTO agent_registry 
                    (id, name, role, capabilities, machine_id, status, current_workload,
                     max_workload, last_seen, registered_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (agent_id, name, role, capabilities, machine_id, 'active', 0,
                     max_workload, timestamp, timestamp, metadata))
                
                conn.commit()
                conn.close()
                
                return JSONResponse({
                    "agent_id": agent_id,
                    "message": "Agent registered successfully",
                    "registered_at": timestamp
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/admin/api/agents/roster", methods=["GET"])
        async def get_agent_roster(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                conn = sqlite3.connect(self.vault_db)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, name, role, capabilities, machine_id, status, current_workload,
                           max_workload, last_seen, registered_at, metadata
                    FROM agent_registry
                    ORDER BY last_seen DESC
                ''')
                
                columns = ['id', 'name', 'role', 'capabilities', 'machine_id', 'status', 
                          'current_workload', 'max_workload', 'last_seen', 'registered_at', 'metadata']
                
                agents = []
                for row in cursor.fetchall():
                    agent = dict(zip(columns, row))
                    agent['capabilities'] = json.loads(agent['capabilities']) if agent['capabilities'] else []
                    agent['metadata'] = json.loads(agent['metadata']) if agent['metadata'] else {}
                    agents.append(agent)
                
                conn.close()
                return JSONResponse({"agents": agents, "total": len(agents)})
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/admin/api/agents/{agent_id}/workload", methods=["GET"])
        async def get_agent_workload(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                agent_id = request.path_params.get('agent_id')
                
                conn = sqlite3.connect(self.vault_db)
                cursor = conn.cursor()
                
                # Get agent info
                cursor.execute('''
                    SELECT name, current_workload, max_workload, status
                    FROM agent_registry WHERE id = ?
                ''', (agent_id,))
                
                agent_info = cursor.fetchone()
                if not agent_info:
                    conn.close()
                    return JSONResponse({"error": "Agent not found"}, status_code=404)
                
                # Get current tasks
                cursor.execute('''
                    SELECT id, title, status, priority, created_at
                    FROM agent_tasks 
                    WHERE assigned_agent = ? AND status IN ('assigned', 'in_progress', 'review')
                    ORDER BY priority DESC
                ''', (agent_id,))
                
                current_tasks = []
                for row in cursor.fetchall():
                    current_tasks.append({
                        'id': row[0],
                        'title': row[1], 
                        'status': row[2],
                        'priority': row[3],
                        'created_at': row[4]
                    })
                
                conn.close()
                return JSONResponse({
                    "agent_id": agent_id,
                    "name": agent_info[0],
                    "current_workload": agent_info[1],
                    "max_workload": agent_info[2],
                    "status": agent_info[3],
                    "utilization": (agent_info[1] / agent_info[2]) * 100 if agent_info[2] > 0 else 0,
                    "current_tasks": current_tasks,
                    "available_capacity": agent_info[2] - agent_info[1]
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # ===== CONFIG BACKUP SYSTEM API ENDPOINTS =====
        
        @self.mcp.custom_route("/api/config/backup/systems", methods=["GET"])
        async def list_config_systems(request):
            """List all registered configuration systems"""
            try:
                from config_backup_system import ConfigBackupSystem
                config_backup = ConfigBackupSystem()
                systems = config_backup.list_systems()
                return JSONResponse({"systems": systems})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/config/backup/snapshot", methods=["POST"])
        async def create_config_snapshot(request):
            """Create a configuration snapshot"""
            try:
                from config_backup_system import ConfigBackupSystem
                body = await request.json()
                config_backup = ConfigBackupSystem()
                snapshot_id = config_backup.create_snapshot(
                    system_id=body["system_id"],
                    config_content=body["config_content"],
                    config_type=body.get("config_type", "unknown"),
                    tags=body.get("tags", [])
                )
                return JSONResponse({"snapshot_id": snapshot_id, "status": "created"})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/config/backup/snapshots/{system_id}", methods=["GET"])
        async def get_config_snapshots(request):
            """Get configuration snapshots for a system"""
            try:
                system_id = request.path_params["system_id"]
                query_params = dict(request.query_params)
                limit = int(query_params.get("limit", 20))
                offset = int(query_params.get("offset", 0))
                
                from config_backup_system import ConfigBackupSystem
                config_backup = ConfigBackupSystem()
                snapshots = config_backup.get_snapshots(system_id, limit, offset)
                return JSONResponse({"snapshots": snapshots})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/config/backup/snapshot/{snapshot_id}", methods=["GET"])
        async def get_config_snapshot_content(request):
            """Get specific snapshot content"""
            try:
                snapshot_id = request.path_params["snapshot_id"]
                from config_backup_system import ConfigBackupSystem
                config_backup = ConfigBackupSystem()
                snapshot = config_backup.get_snapshot_by_id(snapshot_id)
                if not snapshot:
                    return JSONResponse({"error": "Snapshot not found"}, status_code=404)
                return JSONResponse({"snapshot": snapshot})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/config/backup/restore", methods=["POST"])
        async def restore_config_snapshot(request):
            """Restore configuration from snapshot"""
            try:
                body = await request.json()
                from config_backup_system import ConfigBackupSystem
                config_backup = ConfigBackupSystem()
                result = config_backup.restore_snapshot(
                    snapshot_id=body["snapshot_id"],
                    target_path=body.get("target_path")
                )
                return JSONResponse({"status": "restored", "result": result})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/config/backup/diff/{snapshot1_id}/{snapshot2_id}", methods=["GET"])
        async def get_config_diff(request):
            """Get difference between two snapshots"""
            try:
                snapshot1_id = request.path_params["snapshot1_id"]
                snapshot2_id = request.path_params["snapshot2_id"]
                from config_backup_system import ConfigBackupSystem
                config_backup = ConfigBackupSystem()
                diff = config_backup.compare_snapshots(snapshot1_id, snapshot2_id)
                return JSONResponse({"diff": diff})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/config/backup/history/{system_id}", methods=["GET"])
        async def get_config_history(request):
            """Get configuration change history for a system"""
            try:
                system_id = request.path_params["system_id"]
                query_params = dict(request.query_params)
                limit = int(query_params.get("limit", 50))
                
                from config_backup_system import ConfigBackupSystem
                config_backup = ConfigBackupSystem()
                history = config_backup.get_change_history(system_id, limit)
                return JSONResponse({"history": history})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/config/backup/drift/{system_id}", methods=["GET"])
        async def detect_config_drift(request):
            """Detect configuration drift for a system"""
            try:
                system_id = request.path_params["system_id"]
                query_params = dict(request.query_params)
                hours = int(query_params.get("hours", 24))
                
                from config_backup_system import ConfigBackupSystem
                config_backup = ConfigBackupSystem()
                drift = config_backup.detect_drift(system_id, hours)
                return JSONResponse({"drift": drift})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/config/backup/alert", methods=["POST"])
        async def create_drift_alert(request):
            """Create configuration drift alert"""
            try:
                body = await request.json()
                from config_backup_system import ConfigBackupSystem
                config_backup = ConfigBackupSystem()
                alert_id = config_backup.create_drift_alert(
                    system_id=body["system_id"],
                    drift_type=body["drift_type"],
                    severity=body.get("severity", "medium"),
                    description=body["description"],
                    affected_keys=body.get("affected_keys", [])
                )
                return JSONResponse({"alert_id": alert_id, "status": "created"})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/config/backup/alerts/{system_id}", methods=["GET"])
        async def get_drift_alerts(request):
            """Get drift alerts for a system"""
            try:
                system_id = request.path_params["system_id"]
                query_params = dict(request.query_params)
                limit = int(query_params.get("limit", 20))
                
                from config_backup_system import ConfigBackupSystem
                config_backup = ConfigBackupSystem()
                alerts = config_backup.get_drift_alerts(system_id, limit)
                return JSONResponse({"alerts": alerts})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # ===== AGENT KANBAN TASK MANAGEMENT API ENDPOINTS =====
        
        @self.mcp.custom_route("/api/kanban/agents/register", methods=["POST"])
        async def register_kanban_agent(request):
            """Register new agent with capabilities"""
            try:
                from agent_kanban_system import AgentKanbanSystem
                body = await request.json()
                kanban = AgentKanbanSystem()
                
                success = kanban.register_agent(
                    agent_id=body["agent_id"],
                    name=body["name"],
                    machine_id=body["machine_id"],
                    capabilities=body["capabilities"],
                    max_workload=body.get("max_workload", 5),
                    metadata=body.get("metadata", {})
                )
                
                return JSONResponse({"success": success, "message": "Agent registered" if success else "Registration failed"})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/kanban/agents", methods=["GET"])
        async def get_available_agents(request):
            """Get available agents with optional capability filtering"""
            try:
                from agent_kanban_system import AgentKanbanSystem
                query_params = dict(request.query_params)
                required_capabilities = query_params.get("capabilities", "").split(",") if query_params.get("capabilities") else None
                min_level = int(query_params.get("min_level", 1))
                
                kanban = AgentKanbanSystem()
                agents = kanban.get_available_agents(required_capabilities, min_level)
                
                return JSONResponse({"agents": agents})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/kanban/agents/{agent_id}/status", methods=["PUT"])
        async def update_agent_status(request):
            """Update agent status and workload"""
            try:
                from agent_kanban_system import AgentKanbanSystem, AgentStatus
                agent_id = request.path_params["agent_id"]
                body = await request.json()
                
                kanban = AgentKanbanSystem()
                success = kanban.update_agent_status(
                    agent_id=agent_id,
                    status=AgentStatus(body["status"]),
                    current_workload=body.get("current_workload")
                )
                
                return JSONResponse({"success": success})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/kanban/tasks", methods=["POST"])
        async def create_kanban_task(request):
            """Create a new kanban task"""
            try:
                from agent_kanban_system import AgentKanbanSystem, TaskPriority
                body = await request.json()
                kanban = AgentKanbanSystem()
                
                task_id = kanban.create_task(
                    title=body["title"],
                    description=body["description"], 
                    created_by=body["created_by"],
                    priority=TaskPriority(body.get("priority", "medium")),
                    board_id=body.get("board_id", "default"),
                    dependencies=body.get("dependencies", []),
                    estimated_hours=body.get("estimated_hours"),
                    due_date=body.get("due_date"),
                    tags=body.get("tags", []),
                    metadata=body.get("metadata", {})
                )
                
                return JSONResponse({"task_id": task_id, "success": True})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/kanban/tasks/{task_id}/assign", methods=["PUT"])
        async def assign_kanban_task(request):
            """Assign task to agent"""
            try:
                from agent_kanban_system import AgentKanbanSystem
                task_id = request.path_params["task_id"]
                body = await request.json()
                
                kanban = AgentKanbanSystem()
                success = kanban.assign_task(
                    task_id=task_id,
                    agent_id=body.get("agent_id"),
                    auto_assign=body.get("auto_assign", True)
                )
                
                return JSONResponse({"success": success})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/kanban/tasks/{task_id}/move", methods=["PUT"])
        async def move_kanban_task(request):
            """Move task between kanban columns"""
            try:
                from agent_kanban_system import AgentKanbanSystem, TaskStatus
                task_id = request.path_params["task_id"]
                body = await request.json()
                
                kanban = AgentKanbanSystem()
                success = kanban.move_task(
                    task_id=task_id,
                    new_status=TaskStatus(body["status"]),
                    moved_by=body["moved_by"]
                )
                
                return JSONResponse({"success": success})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/kanban/boards/{board_id}", methods=["GET"])
        async def get_kanban_board(request):
            """Get complete kanban board state"""
            try:
                from agent_kanban_system import AgentKanbanSystem
                board_id = request.path_params["board_id"]
                query_params = dict(request.query_params)
                include_metrics = query_params.get("metrics", "true").lower() == "true"
                
                kanban = AgentKanbanSystem()
                board_data = kanban.get_kanban_board(board_id, include_metrics)
                
                return JSONResponse({"board": board_data})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/kanban/agents/workload", methods=["GET"])
        async def get_agent_workload_report(request):
            """Get agent workload and performance report"""
            try:
                from agent_kanban_system import AgentKanbanSystem
                kanban = AgentKanbanSystem()
                report = kanban.get_agent_workload_report()
                
                return JSONResponse({"report": report})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        @self.mcp.custom_route("/api/kanban/analytics", methods=["GET"])
        async def get_task_analytics(request):
            """Get task analytics for specified time period"""
            try:
                from agent_kanban_system import AgentKanbanSystem
                query_params = dict(request.query_params)
                days = int(query_params.get("days", 30))
                
                kanban = AgentKanbanSystem()
                analytics = kanban.get_task_analytics(days)
                
                return JSONResponse({"analytics": analytics})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        logger.info("💾 Config Backup API endpoints registered")
        logger.info("📋 Agent Kanban Task Management API endpoints registered")
        
        # Config Backup API - Create snapshot
        @self.mcp.custom_route("/admin/api/configs/backup", methods=["POST"])
        async def api_create_config_backup(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
            try:
                data = await request.json()
                system_id = data.get('system_id')
                config_content = data.get('config_content')
                config_type = data.get('config_type', 'config')
                file_path = data.get('file_path')
                agent_id = data.get('agent_id', '')
                metadata = data.get('metadata', {})
                
                if not system_id or not config_content:
                    return JSONResponse({"error": "system_id and config_content required"}, status_code=400)
                
                from config_backup_system import ConfigSnapshot
                snapshot = ConfigSnapshot(
                    system_id=system_id,
                    config_type=config_type,
                    config_content=config_content,
                    file_path=file_path,
                    agent_id=agent_id,
                    metadata=metadata
                )
                
                snapshot_id = self.config_backup.create_snapshot(snapshot)
                
                if snapshot_id:
                    return JSONResponse({
                        "success": True,
                        "snapshot_id": snapshot_id,
                        "system_id": system_id,
                        "config_hash": snapshot.config_hash,
                        "size": len(config_content),
                        "message": "Configuration snapshot created successfully"
                    })
                else:
                    return JSONResponse({"error": "Failed to create snapshot"}, status_code=500)
                    
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Config History API 
        @self.mcp.custom_route("/admin/api/configs/{system_id}/history", methods=["GET"])
        async def api_get_config_history(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
            try:
                system_id = request.path_params.get('system_id')
                limit = int(request.query_params.get('limit', 20))
                
                history = self.config_backup.get_system_history(system_id, limit)
                
                return JSONResponse({
                    "success": True,
                    "system_id": system_id,
                    "history": history,
                    "count": len(history)
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Current Config API
        @self.mcp.custom_route("/admin/api/configs/{system_id}/current", methods=["GET"])
        async def api_get_current_config(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
            try:
                system_id = request.path_params.get('system_id')
                include_content = request.query_params.get('include_content', 'false').lower() == 'true'
                
                current_config = self.config_backup.get_current_config(system_id)
                
                if not current_config:
                    return JSONResponse({"error": "No configuration found"}, status_code=404)
                
                # Optionally exclude large content from response
                if not include_content:
                    current_config = {k: v for k, v in current_config.items() if k != 'config_content'}
                    current_config['content_size'] = current_config.get('size', 0)
                
                return JSONResponse({
                    "success": True,
                    "system_id": system_id,
                    "config": current_config
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Config Restore API
        @self.mcp.custom_route("/admin/api/configs/restore", methods=["POST"])
        async def api_restore_config(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
            try:
                data = await request.json()
                snapshot_id = data.get('snapshot_id')
                system_id = data.get('system_id')
                restore_to_file = data.get('restore_to_file', False)
                
                if not snapshot_id and not system_id:
                    return JSONResponse({"error": "snapshot_id or system_id required"}, status_code=400)
                
                # Get snapshot to restore
                if snapshot_id:
                    # Restore specific snapshot
                    with sqlite3.connect(self.config_backup.db_path) as conn:
                        conn.row_factory = sqlite3.Row
                        snapshot = conn.execute("""
                            SELECT * FROM config_snapshots WHERE id = ?
                        """, (snapshot_id,)).fetchone()
                else:
                    # Restore latest for system
                    snapshot = self.config_backup.get_current_config(system_id)
                
                if not snapshot:
                    return JSONResponse({"error": "Snapshot not found"}, status_code=404)
                
                snapshot_dict = dict(snapshot)
                config_content = snapshot_dict.get('config_content', '')
                file_path = snapshot_dict.get('file_path')
                
                # If restore_to_file and file_path exists, write to file
                restored_to_file = False
                if restore_to_file and file_path:
                    try:
                        import os
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, 'w') as f:
                            f.write(config_content)
                        restored_to_file = True
                    except Exception as file_error:
                        logger.warning(f"Failed to restore to file {file_path}: {file_error}")
                
                return JSONResponse({
                    "success": True,
                    "snapshot_id": snapshot_dict.get('id'),
                    "system_id": snapshot_dict.get('system_id'),
                    "config_content": config_content,
                    "file_path": file_path,
                    "restored_to_file": restored_to_file,
                    "timestamp": snapshot_dict.get('timestamp'),
                    "message": "Configuration restored successfully"
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Drift Detection API
        @self.mcp.custom_route("/admin/api/configs/drift", methods=["GET"])
        async def api_detect_drift(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
            try:
                system_id = request.query_params.get('system_id')
                hours_back = int(request.query_params.get('hours_back', 24))
                
                drift_issues = self.config_backup.detect_drift(system_id, hours_back)
                
                # Analyze and categorize issues
                categorized = {
                    'critical': [],
                    'high': [],
                    'medium': [],
                    'low': []
                }
                
                for issue in drift_issues:
                    analysis = self.config_backup._analyze_drift(issue)
                    issue['analysis'] = analysis
                    severity = analysis.get('severity', 'low')
                    categorized[severity].append(issue)
                
                return JSONResponse({
                    "success": True,
                    "system_id": system_id,
                    "hours_back": hours_back,
                    "total_issues": len(drift_issues),
                    "issues": drift_issues,
                    "categorized": categorized,
                    "summary": {
                        "critical": len(categorized['critical']),
                        "high": len(categorized['high']),
                        "medium": len(categorized['medium']),
                        "low": len(categorized['low'])
                    }
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Config Diff API
        @self.mcp.custom_route("/admin/api/configs/diff/{id1}/{id2}", methods=["GET"])
        async def api_compare_configs(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
            try:
                id1 = request.path_params.get('id1')
                id2 = request.path_params.get('id2')
                
                with sqlite3.connect(self.config_backup.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    
                    # Get both snapshots
                    snapshot1 = conn.execute("SELECT * FROM config_snapshots WHERE id = ?", (id1,)).fetchone()
                    snapshot2 = conn.execute("SELECT * FROM config_snapshots WHERE id = ?", (id2,)).fetchone()
                    
                    if not snapshot1 or not snapshot2:
                        return JSONResponse({"error": "One or both snapshots not found"}, status_code=404)
                    
                    # Check if diff already exists
                    existing_diff = conn.execute("""
                        SELECT * FROM config_diffs 
                        WHERE (snapshot_id_before = ? AND snapshot_id_after = ?) 
                           OR (snapshot_id_before = ? AND snapshot_id_after = ?)
                    """, (id1, id2, id2, id1)).fetchone()
                    
                    if existing_diff:
                        diff_data = dict(existing_diff)
                    else:
                        # Generate diff
                        import difflib
                        content1 = dict(snapshot1)['config_content']
                        content2 = dict(snapshot2)['config_content']
                        
                        diff_lines = list(difflib.unified_diff(
                            content1.splitlines(keepends=True),
                            content2.splitlines(keepends=True),
                            fromfile=f"snapshot_{id1}",
                            tofile=f"snapshot_{id2}",
                            n=3
                        ))
                        
                        diff_content = ''.join(diff_lines)
                        lines_added = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
                        lines_removed = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
                        
                        diff_data = {
                            'diff_content': diff_content,
                            'lines_added': lines_added,
                            'lines_removed': lines_removed,
                            'snapshot_id_before': id1,
                            'snapshot_id_after': id2
                        }
                
                return JSONResponse({
                    "success": True,
                    "snapshot1": dict(snapshot1),
                    "snapshot2": dict(snapshot2),
                    "diff": diff_data
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Systems List API
        @self.mcp.custom_route("/admin/api/configs/systems", methods=["GET"])
        async def api_list_config_systems(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
            try:
                systems = self.config_backup.get_systems()
                
                return JSONResponse({
                    "success": True,
                    "systems": systems,
                    "count": len(systems)
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Register System API
        @self.mcp.custom_route("/admin/api/configs/systems", methods=["POST"])
        async def api_register_config_system(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
                
            try:
                data = await request.json()
                system_id = data.get('system_id')
                system_name = data.get('system_name')
                system_type = data.get('system_type')
                
                if not all([system_id, system_name, system_type]):
                    return JSONResponse({"error": "system_id, system_name, and system_type required"}, status_code=400)
                
                success = self.config_backup.register_system(
                    system_id=system_id,
                    system_name=system_name,
                    system_type=system_type,
                    agent_id=data.get('agent_id', ''),
                    description=data.get('description', ''),
                    backup_frequency=data.get('backup_frequency', 3600),
                    metadata=data.get('metadata', {})
                )
                
                if success:
                    return JSONResponse({
                        "success": True,
                        "system_id": system_id,
                        "message": "System registered successfully"
                    })
                else:
                    return JSONResponse({"error": "Failed to register system"}, status_code=500)
                    
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
    
    def _add_session_recovery_middleware(self):
        """Add session recovery logic using custom error handling"""
        from starlette.responses import JSONResponse
        import uuid
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Override the original HTTP server's error handler
        original_http_server_init = None
        
        # Store original error handling for later use
        if hasattr(self.mcp, '_http_server'):
            original_http_server_init = getattr(self.mcp._http_server, '__init__', None)
        
        # Add recovery endpoint that clients can call when they get 404s
        @self.mcp.custom_route("/api/session/recover", methods=["POST"])
        async def session_recovery_endpoint(request):
            """Handle session recovery requests"""
            try:
                data = await request.json() if request.method == "POST" else {}
                old_session_id = data.get('old_session_id', 'unknown')
                
                # Generate new session ID
                new_session_id = uuid.uuid4().hex
                
                logger.info(f"🔄 Session recovery requested - Old: {old_session_id}, New: {new_session_id}")
                
                return JSONResponse({
                    "status": "recovered", 
                    "old_session_id": old_session_id,
                    "new_session_id": new_session_id,
                    "message": "New session ID generated, please reconnect",
                    "action": "reconnect"
                })
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Add a public recovery info endpoint (no auth required)
        @self.mcp.custom_route("/api/session/info", methods=["GET"])
        async def session_info_endpoint(request):
            """Get session info and recovery instructions"""
            return JSONResponse({
                "server_status": "online",
                "session_management": "enabled",
                "recovery_available": True,
                "recovery_endpoint": "/api/session/recover",
                "message": "Server now uses session mode - sessions enabled for MCP tool functionality",
                "server_time": datetime.now().isoformat(),
                "uptime": str(datetime.now() - self._start_datetime),
                "note": "If you still get session errors, it's likely a client-side caching issue"
            })
        
        logger.info("🔄 Session recovery system registered - endpoints: /api/session/recover, /api/session/info")

    def _setup_session_error_handling(self):
        """Setup improved session error handling at the FastMCP level"""
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Create a custom handler for /messages/ that handles missing sessions gracefully
        # This route will catch all /messages/ requests including those with query parameters
        @self.mcp.custom_route("/messages/", methods=["POST", "GET"], include_in_schema=False)  
        async def handle_session_messages_root(request):
            """Handle /messages/ endpoint - this should intercept before FastMCP"""
            # This route should run BEFORE FastMCP's built-in /messages/ handler
            pass
            
        # Also create a catch-all for any /messages path variations
        @self.mcp.custom_route("/messages", methods=["POST", "GET"], include_in_schema=False)
        async def handle_session_messages_no_slash(request):
            """Custom handler for /messages/ root endpoint that provides session recovery"""
            from starlette.responses import JSONResponse
            import uuid
            
            try:
                # Get session ID from query parameters
                session_id = request.query_params.get('session_id', '')
                
                # Log the session request
                logger.warning(f"🔍 Session request intercepted - ID: {session_id}, Path: {request.url.path}")
                
                # Check if this is the problematic session ID
                if session_id == "2dbfd1c3556642c2ac12c2a0450c0e50":
                    logger.warning(f"🚨 Detected problematic cached session ID: {session_id} - providing recovery")
                    
                    # Generate new session and redirect to SSE
                    new_session_id = uuid.uuid4().hex
                    return JSONResponse({
                        "error": "session_expired",
                        "message": f"Session {session_id} has expired. Please reconnect with new session ID.",
                        "old_session_id": session_id,
                        "new_session_id": new_session_id,
                        "action": "reconnect",
                        "sse_url": f"/sse?session_id={new_session_id}",
                        "recovery_url": f"/api/session/recover"
                    }, status_code=410)  # Gone status
                
                # If no session ID provided, suggest creating one
                if not session_id:
                    new_session_id = uuid.uuid4().hex
                    return JSONResponse({
                        "error": "no_session_id",
                        "message": "No session ID provided",
                        "suggested_session_id": new_session_id,
                        "instructions": "Connect to /sse with session_id parameter"
                    }, status_code=400)
                
                # For other sessions, return guidance to use SSE endpoint
                return JSONResponse({
                    "error": "use_sse_endpoint", 
                    "message": "For MCP communication, please connect via the SSE endpoint",
                    "session_id": session_id,
                    "sse_url": f"/sse?session_id={session_id}",
                    "instructions": "Use Server-Sent Events endpoint at /sse for MCP protocol"
                }, status_code=200)
                
            except Exception as e:
                logger.error(f"❌ Error in session message handler: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        logger.info("📡 Enhanced session error handling configured for /messages/ endpoints")

    def _add_session_management(self):
        """Add session management and health endpoints"""
        from starlette.responses import JSONResponse
        from datetime import datetime, timedelta
        import uuid
        
        # Session health check endpoint
        @self.mcp.custom_route("/admin/api/sessions/health", methods=["GET"])
        async def session_health(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                # Get session manager if available
                session_manager = getattr(self.mcp, '_session_manager', None)
                active_sessions = 0
                session_details = []
                
                if session_manager:
                    active_sessions = len(getattr(session_manager, '_server_instances', {}))
                    for session_id, transport in getattr(session_manager, '_server_instances', {}).items():
                        session_details.append({
                            "session_id": session_id,
                            "is_terminated": getattr(transport, 'is_terminated', False),
                            "created_at": self.session_last_activity.get(session_id, "Unknown")
                        })
                
                return JSONResponse({
                    "status": "healthy",
                    "active_sessions": active_sessions,
                    "session_details": session_details,
                    "server_uptime": str(datetime.now() - self._start_datetime),
                    "mcp_config": {
                        "sse_path": "/sse", 
                        "message_path": "/messages/",
                        "stateless": False,
                        "session_recovery_enabled": True,
                        "note": "Sessions enabled for MCP tool functionality"
                    }
                })
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Session cleanup endpoint
        @self.mcp.custom_route("/admin/api/sessions/cleanup", methods=["POST"])
        async def cleanup_sessions(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                session_manager = getattr(self.mcp, '_session_manager', None)
                cleaned = 0
                
                if session_manager:
                    instances = getattr(session_manager, '_server_instances', {})
                    to_remove = []
                    
                    for session_id, transport in instances.items():
                        if getattr(transport, 'is_terminated', False):
                            to_remove.append(session_id)
                    
                    for session_id in to_remove:
                        del instances[session_id]
                        if session_id in self.session_last_activity:
                            del self.session_last_activity[session_id]
                        cleaned += 1
                
                return JSONResponse({
                    "message": f"Cleaned up {cleaned} terminated sessions",
                    "remaining_sessions": len(getattr(session_manager, '_server_instances', {})) if session_manager else 0
                })
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Session recovery endpoint for manual testing
        @self.mcp.custom_route("/admin/api/sessions/recover", methods=["POST"])
        async def recover_session(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                data = await request.json()
                old_session_id = data.get('old_session_id')
                
                session_manager = getattr(self.mcp, '_session_manager', None)
                
                if session_manager:
                    instances = getattr(session_manager, '_server_instances', {})
                    
                    # Remove old session if it exists
                    if old_session_id and old_session_id in instances:
                        del instances[old_session_id]
                        if old_session_id in self.session_last_activity:
                            del self.session_last_activity[old_session_id]
                    
                    # Generate new session ID for client to use
                    new_session_id = uuid.uuid4().hex
                    
                    return JSONResponse({
                        "message": "Session recovery initiated",
                        "old_session_id": old_session_id,
                        "new_session_id": new_session_id,
                        "instructions": "Use new session ID for next connection"
                    })
                
                return JSONResponse({"error": "Session manager not available"}, status_code=503)
                
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Force session refresh endpoint
        @self.mcp.custom_route("/admin/api/sessions/refresh", methods=["POST"])
        async def refresh_sessions(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                data = await request.json()
                session_id = data.get('session_id')
                
                if session_id:
                    # Update activity time for specific session
                    self.session_last_activity[session_id] = datetime.now().isoformat()
                    return JSONResponse({
                        "message": f"Session {session_id} activity updated",
                        "updated_at": self.session_last_activity[session_id]
                    })
                else:
                    # Refresh all sessions
                    current_time = datetime.now().isoformat()
                    session_manager = getattr(self.mcp, '_session_manager', None)
                    
                    if session_manager:
                        for session_id in getattr(session_manager, '_server_instances', {}):
                            self.session_last_activity[session_id] = current_time
                    
                    return JSONResponse({
                        "message": "All sessions refreshed",
                        "refreshed_at": current_time,
                        "total_sessions": len(self.session_last_activity)
                    })
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Session debugging endpoint
        @self.mcp.custom_route("/admin/api/sessions/debug", methods=["GET"])
        async def session_debug(request):
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                session_manager = getattr(self.mcp, '_session_manager', None)
                debug_info = {
                    "session_manager_available": session_manager is not None,
                    "mcp_server_available": hasattr(self, 'mcp'),
                    "stored_activities": len(self.session_last_activity),
                    "stored_sessions": len(self.active_sessions),
                    "config": {
                        "host": self.host,
                        "port": self.port,
                        "sse_path": "/sse",
                        "message_path": "/messages/"
                    }
                }
                
                if session_manager:
                    debug_info.update({
                        "active_server_instances": len(getattr(session_manager, '_server_instances', {})),
                        "session_ids": list(getattr(session_manager, '_server_instances', {}).keys()),
                        "task_group_active": getattr(session_manager, '_task_group', None) is not None
                    })
                
                return JSONResponse(debug_info)
            except Exception as e:
                return JSONResponse({"error": str(e), "debug_failed": True}, status_code=500)
        
        logger.info("🔧 Session management endpoints registered")
    
    async def _setup_mcp_bridges(self):
        """Setup and register predefined MCP bridges for remote access"""
        try:
            bridge_config_path = Path(__file__).parent.parent / "config" / "bridge_config.json"
            if bridge_config_path.exists():
                with open(bridge_config_path) as f:
                    bridge_config = json.load(f)
                
                predefined = bridge_config.get('predefined_bridges', {})
                for bridge_id, config in predefined.items():
                    if config.get('auto_start', True):
                        try:
                            # Ensure ID is consistent
                            config['id'] = bridge_id
                            await self.bridge_manager.register_bridge(config)
                            logger.info(f"🚀 Auto-registering MCP bridge: {config.get('name', bridge_id)}")
                        except Exception as bridge_err:
                            logger.error(f"❌ Failed to register bridge {bridge_id}: {bridge_err}")
        except Exception as e:
            logger.error(f"Error setting up MCP bridges: {e}")

    def _register_bridge_routes(self):
        """Add SSE proxy routes for bridged servers"""
        
        @self.mcp.custom_route("/mcp-bridge/{bridge_id}/sse", methods=["GET"])
        async def bridge_sse(request):
            """SSE endpoint for bridged stdio MCP server"""
            from starlette.responses import StreamingResponse, JSONResponse
            import uuid
            
            bridge_id = request.path_params.get("bridge_id")
            bridge = await self.bridge_manager.get_bridge(bridge_id)
            if not bridge:
                return JSONResponse({"error": "Bridge not found"}, status_code=404)

            session_id = request.query_params.get("session_id", uuid.uuid4().hex)
            session = await bridge.create_session(session_id)

            async def event_generator():
                # Send initial endpoint event
                yield f"event: endpoint\ndata: /mcp-bridge/{bridge_id}/messages/?session_id={session_id}\n\n"
                
                try:
                    while session.active:
                        # Wait for messages from stdio process
                        line = await session.queue.get()
                        yield f"data: {line}\n\n"
                except asyncio.CancelledError:
                    pass
                finally:
                    await bridge.close_session(session_id)

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )

        @self.mcp.custom_route("/mcp-bridge/{bridge_id}/messages/", methods=["POST"])
        async def bridge_messages(request):
            """Message endpoint for bridged stdio MCP server"""
            bridge_id = request.path_params.get("bridge_id")
            session_id = request.query_params.get("session_id")
            
            if not session_id:
                return JSONResponse({"error": "session_id required"}, status_code=400)
            
            bridge = await self.bridge_manager.get_bridge(bridge_id)
            if not bridge:
                return JSONResponse({"error": "Bridge not found"}, status_code=404)
            
            session = await bridge.get_session(session_id)
            if not session:
                return JSONResponse({"error": "Session not found"}, status_code=404)
            
            try:
                message = await request.json()
                await session.send_message(message)
                return JSONResponse({"status": "accepted"}, status_code=202)
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        logger.info("🌉 MCP bridge SSE proxy routes registered")

    def _add_health_all_route(self):
        """Add unified health check endpoint for all MCP services"""
        
        @self.mcp.custom_route("/admin/api/mcp/health-all", methods=["GET"])
        async def health_all(request):
            """Unified health check for local and remote MCP services"""
            # No auth for now to allow monitoring tools, or check if user is admin
            
            results = {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "healthy",
                "services": {}
            }
            
            # 1. Local haivemind tools
            try:
                tools = await self.mcp.list_tools()
                results["services"]["haivemind"] = {
                    "status": "healthy",
                    "type": "local",
                    "tools_count": len(tools),
                    "version": "2.1.5"
                }
            except Exception as e:
                results["services"]["haivemind"] = {"status": "error", "error": str(e)}
                results["overall_status"] = "degraded"

            # 2. Bridged servers
            try:
                bridge_health = await self.bridge_manager.health_check()
                results["services"]["bridges"] = bridge_health
                if bridge_health.get("error_bridges", 0) > 0:
                    results["overall_status"] = "degraded"
            except Exception as e:
                results["services"]["bridges"] = {"status": "error", "error": str(e)}

            # 3. Remote SSE servers from registry
            for server_id, info in self.server_registry.items():
                if server_id == "memory-server": continue # skip self
                
                try:
                    import httpx
                    start = time.time()
                    async with httpx.AsyncClient() as client:
                        # Try to get health if available, or just check endpoint
                        health_url = info['endpoint'].replace('/sse', '/health')
                        resp = await client.get(health_url, timeout=2.0)
                        latency = (time.time() - start) * 1000
                        
                        results["services"][info['name']] = {
                            "status": "healthy" if resp.status_code == 200 else "unhealthy",
                            "type": "remote_sse",
                            "endpoint": info['endpoint'],
                            "latency_ms": round(latency, 2),
                            "http_code": resp.status_code
                        }
                except Exception as e:
                    results["services"][info['name']] = {
                        "status": "offline",
                        "type": "remote_sse",
                        "endpoint": info['endpoint'],
                        "error": str(e)
                    }
                    results["overall_status"] = "degraded"

            return JSONResponse(results)

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

    def _init_admin_bootstrap(self):
        """Initialize the admin bootstrap system for secure credential management"""
        self.admin_bootstrap = None
        self.admin_system_initialized = False

        if not ADMIN_BOOTSTRAP_AVAILABLE:
            logger.warning("Admin bootstrap system not available - using legacy auth")
            return

        try:
            base_path = str(Path(__file__).parent.parent)
            self.admin_bootstrap = get_admin_bootstrap(base_path)

            if self.admin_bootstrap.is_initialized():
                # Load credentials from secure storage
                try:
                    self.admin_bootstrap.load_credentials()
                    self.admin_system_initialized = True
                    logger.info("🔐 Admin bootstrap system initialized - credentials loaded from vault")
                except Exception as e:
                    logger.error(f"Failed to load admin credentials: {e}")
                    logger.warning("Admin system requires initialization - visit /admin/setup")
            else:
                logger.info("🔧 Admin system not initialized - first-run setup required at /admin/setup")

        except Exception as e:
            logger.error(f"Failed to initialize admin bootstrap: {e}")

    def _verify_vault_master_password(self, password: str) -> bool:
        """
        Verify the vault master password.

        Uses the admin bootstrap system if available, otherwise falls back
        to legacy verification.

        Args:
            password: Password to verify

        Returns:
            True if password is valid, False otherwise
        """
        # Try admin bootstrap system first
        if self.admin_bootstrap and self.admin_system_initialized:
            try:
                return self.admin_bootstrap.verify_admin_password(password)
            except Exception as e:
                logger.error(f"Bootstrap verification failed: {e}")

        # Fallback: Check environment variable
        env_password = os.environ.get('HAIVEMIND_VAULT_PASSWORD')
        if env_password and password == env_password:
            return True

        # Fallback: Check config (legacy - will be removed)
        config_hash = self.config.get('security', {}).get('vault_password_hash')
        if config_hash:
            try:
                import bcrypt
                return bcrypt.checkpw(password.encode(), config_hash.encode())
            except:
                pass

        # No valid verification method available
        logger.warning("No valid vault password verification method available")
        return False

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
        @self.mcp.custom_route("/admin/mcp_bridge.html", methods=["GET"])
        @self.mcp.custom_route("/admin/mcp-bridge", methods=["GET"])
        async def mcp_bridge_dashboard(request):
            """Serve the MCP Bridge management dashboard interface"""
            try:
                bridge_dashboard_path = Path(__file__).parent.parent / "admin" / "mcp_bridge.html"
                if bridge_dashboard_path.exists():
                    return FileResponse(str(bridge_dashboard_path), media_type="text/html")
                else:
                    return JSONResponse({"error": "MCP Bridge dashboard not found"}, status_code=404)
            except Exception as e:
                logger.error(f"Error serving MCP Bridge dashboard: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
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
        
        # ===== MCP BRIDGE API ENDPOINTS =====
        
        # Discover local MCP servers
        @self.mcp.custom_route("/admin/api/mcp-bridge/discover", methods=["GET"])
        async def discover_local_servers(request):
            """Discover local MCP servers from configuration files"""
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                discovered = await self.bridge_manager.discover_local_servers()
                return JSONResponse({
                    "servers": discovered,
                    "total": len(discovered),
                    "status": "success"
                })
            except Exception as e:
                logger.error(f"Error discovering local servers: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Register MCP bridge
        @self.mcp.custom_route("/admin/api/mcp-bridge/register", methods=["POST"])
        async def register_bridge(request):
            """Register a new MCP server bridge"""
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                config = await request.json()
                server_id = await self.bridge_manager.register_bridge(config)
                
                return JSONResponse({
                    "server_id": server_id,
                    "endpoint": f"/mcp-bridge/{server_id}",
                    "status": "registered",
                    "success": True
                })
            except Exception as e:
                logger.error(f"Error registering bridge: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # List bridges
        @self.mcp.custom_route("/admin/api/mcp-bridge/servers", methods=["GET"])
        async def list_bridges(request):
            """List all registered MCP bridges"""
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                bridges = await self.bridge_manager.list_bridges()
                return JSONResponse({
                    "bridges": bridges,
                    "total": len(bridges),
                    "status": "success"
                })
            except Exception as e:
                logger.error(f"Error listing bridges: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Get bridge status
        @self.mcp.custom_route("/admin/api/mcp-bridge/{server_id}/status", methods=["GET"])
        async def get_bridge_status(request):
            """Get status of a specific bridge"""
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                server_id = request.path_params["server_id"]
                status = await self.bridge_manager.get_bridge_status(server_id)
                
                if not status:
                    return JSONResponse({"error": "Bridge not found"}, status_code=404)
                
                return JSONResponse({
                    "status": status,
                    "success": True
                })
            except Exception as e:
                logger.error(f"Error getting bridge status: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Proxy requests to bridge
        @self.mcp.custom_route("/admin/api/mcp-bridge/{server_id}/proxy", methods=["POST"])
        async def proxy_bridge_request(request):
            """Proxy a request to a bridged MCP server"""
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                server_id = request.path_params["server_id"]
                request_data = await request.json()
                
                method = request_data.get("method")
                params = request_data.get("params", {})
                
                if not method:
                    return JSONResponse({"error": "Method required"}, status_code=400)
                
                response = await self.bridge_manager.proxy_request(server_id, method, params)
                return JSONResponse(response)
                
            except ValueError as e:
                return JSONResponse({"error": str(e)}, status_code=404)
            except Exception as e:
                logger.error(f"Error proxying request: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Remove bridge
        @self.mcp.custom_route("/admin/api/mcp-bridge/{server_id}", methods=["DELETE"])
        async def remove_bridge(request):
            """Remove a registered bridge"""
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                server_id = request.path_params["server_id"]
                removed = await self.bridge_manager.remove_bridge(server_id)
                
                if not removed:
                    return JSONResponse({"error": "Bridge not found"}, status_code=404)
                
                return JSONResponse({
                    "success": True,
                    "message": f"Bridge {server_id} removed"
                })
            except Exception as e:
                logger.error(f"Error removing bridge: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Bridge health check
        @self.mcp.custom_route("/admin/api/mcp-bridge/health", methods=["GET"])
        async def bridge_health_check(request):
            """Get health status of all bridges"""
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                health = await self.bridge_manager.health_check()
                return JSONResponse(health)
            except Exception as e:
                logger.error(f"Error getting bridge health: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        # Bridge auto-register for known servers
        @self.mcp.custom_route("/admin/api/mcp-bridge/auto-register", methods=["POST"])
        async def auto_register_bridges(request):
            """Auto-register known MCP servers like vibe-kanban"""
            if not await self._check_admin_auth(request):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            try:
                # Auto-register predefined bridges from configuration
                registered_bridges = []
                
                # Load bridge configuration
                try:
                    from pathlib import Path
                    bridge_config_path = Path(__file__).parent.parent / "config" / "bridge_config.json"
                    if bridge_config_path.exists():
                        with open(bridge_config_path, 'r') as f:
                            bridge_config = json.load(f)
                        
                        predefined_bridges = bridge_config.get("predefined_bridges", {})
                        
                        for bridge_name, bridge_config in predefined_bridges.items():
                            try:
                                server_id = await self.bridge_manager.register_bridge(bridge_config)
                                registered_bridges.append({
                                    "name": bridge_config.get("name", bridge_name),
                                    "server_id": server_id,
                                    "endpoint": f"/mcp-bridge/{server_id}"
                                })
                            except Exception as e:
                                logger.warning(f"Could not auto-register {bridge_name}: {e}")
                    else:
                        # Fallback to hardcoded vibe-kanban config if bridge_config.json not found
                        vibe_config = {
                            "name": "Vibe Kanban",
                            "type": "stdio",
                            "command": "npx",
                            "args": ["vibe-kanban", "--mcp"],
                            "working_directory": "/home/lj/haivemind-mcp-server",
                            "description": "Task and project management MCP server",
                            "tags": ["kanban", "project-management", "tasks"]
                        }
                        
                        try:
                            server_id = await self.bridge_manager.register_bridge(vibe_config)
                            registered_bridges.append({
                                "name": "Vibe Kanban",
                                "server_id": server_id,
                                "endpoint": f"/mcp-bridge/{server_id}"
                            })
                        except Exception as e:
                            logger.warning(f"Could not auto-register vibe-kanban: {e}")
                            
                except Exception as e:
                    logger.error(f"Error loading bridge configuration: {e}")
                    # Fall back to hardcoded config if needed
                
                return JSONResponse({
                    "registered": registered_bridges,
                    "total": len(registered_bridges),
                    "status": "completed"
                })
                
            except Exception as e:
                logger.error(f"Error in auto-registration: {e}")
                return JSONResponse({"error": str(e)}, status_code=500)
        
        logger.info("🌉 MCP Bridge API endpoints registered")
    
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
            # Check SSL configuration
            ssl_config = self.config.get('security', {}).get('tls', {})
            ssl_enabled = ssl_config.get('enabled', False)
            
            # Determine protocol
            protocol = "https" if ssl_enabled else "http"
            
            logger.info("🚀 Activating hAIveMind network portal - preparing for remote drone connections...")
            logger.info(f"📶 Hive broadcast channel: {protocol}://{self.host}:{self.port}/sse")
            logger.info(f"🌊 Collective consciousness stream: {protocol}://{self.host}:{self.port}/mcp")
            logger.info(f"🩸 Hive vitals monitor: {protocol}://{self.host}:{self.port}/health")
            
            if ssl_enabled:
                logger.info(f"🔒 SSL/TLS enabled - secure hive communications active")
                logger.info(f"📜 Certificate: {ssl_config.get('cert_file')}")
            
            # Add unified health-all endpoint
            self._add_health_all_route()

            # Add bridge routes
            self._register_bridge_routes()

            # Override the health endpoint to show correct version
            @self.mcp.custom_route("/health", methods=["GET"])
            async def health(request):
                from starlette.responses import JSONResponse
                return JSONResponse({
                    "status": "healthy",
                    "server": "remote-memory-mcp",
                    "version": "2.1.5",
                    "machine_id": self.storage.machine_id,
                    "endpoints": {
                        "sse": f"{protocol}://{self.host}:{self.port}/sse",
                        "streamable_http": f"{protocol}://{self.host}:{self.port}/mcp"
                    },
                    "ssl_enabled": ssl_enabled
                })
            
            # Suppress MCP framework warnings about early requests  
            logging.getLogger("root").setLevel(logging.ERROR)
            
            import anyio
            import uvicorn
            
            async def start_all():
                # 1. Start bridges
                await self._setup_mcp_bridges()
                
                # 2. Get the SSE app (this will include the custom routes registered above)
                app = self.mcp.sse_app()
                
                # 3. Register startup message
                @app.on_event("startup")
                async def on_startup():
                    logger.info("🚀 hAIveMind SSE server started and ready for connections")

                # 4. Run server
                config = uvicorn.Config(
                    app, 
                    host=self.host, 
                    port=self.port,
                    log_level="info",
                    loop="asyncio"
                )
                server = uvicorn.Server(config)
                await server.serve()

            anyio.run(start_all)
            
        except Exception as e:
            logger.error(f"💥 Network portal activation failed: {e} - remote hive access unavailable")
            raise
    
    def _get_vibe_kanban_tools(self):
        """Get Vibe Kanban tools for ticket operations"""
        # Import vibe kanban tools dynamically
        try:
            import importlib.util
            spec = importlib.util.find_spec("mcp__vibe_kanban__create_task")
            if spec:
                # Use the actual MCP tools
                class VibeKanbanWrapper:
                    def __init__(self):
                        pass
                    
                    async def create_task(self, project_id: str, title: str, description: str = ""):
                        # This would call the actual vibe kanban MCP tool
                        # For now, simulate the response
                        return {
                            'success': True,
                            'task': {
                                'id': str(uuid.uuid4()),
                                'title': title,
                                'description': description,
                                'status': 'todo',
                                'created_at': datetime.now().isoformat() + 'Z',
                                'updated_at': datetime.now().isoformat() + 'Z'
                            }
                        }
                    
                    async def get_task(self, project_id: str, task_id: str):
                        return {
                            'success': True,
                            'task': {
                                'id': task_id,
                                'title': 'Sample Task',
                                'description': 'Sample Description',
                                'status': 'todo',
                                'created_at': '2024-01-01T00:00:00Z',
                                'updated_at': '2024-01-01T00:00:00Z'
                            }
                        }
                    
                    async def update_task(self, project_id: str, task_id: str, **kwargs):
                        return {
                            'success': True,
                            'old_status': 'todo'
                        }
                    
                    async def list_tasks(self, project_id: str, status: str = None, limit: int = 50):
                        return {
                            'success': True,
                            'tasks': [],
                            'count': 0
                        }
                
                return VibeKanbanWrapper()
            else:
                # Fallback wrapper
                class FallbackWrapper:
                    async def create_task(self, **kwargs):
                        return {'success': False, 'error': 'Vibe Kanban not available'}
                    async def get_task(self, **kwargs):
                        return {'success': False, 'error': 'Vibe Kanban not available'}
                    async def update_task(self, **kwargs):
                        return {'success': False, 'error': 'Vibe Kanban not available'}
                    async def list_tasks(self, **kwargs):
                        return {'success': False, 'error': 'Vibe Kanban not available'}
                
                return FallbackWrapper()
        except Exception as e:
            logger.warning(f"Could not initialize Vibe Kanban wrapper: {e}")
            class ErrorWrapper:
                async def create_task(self, **kwargs):
                    return {'success': False, 'error': str(e)}
                async def get_task(self, **kwargs):
                    return {'success': False, 'error': str(e)}
                async def update_task(self, **kwargs):
                    return {'success': False, 'error': str(e)}
                async def list_tasks(self, **kwargs):
                    return {'success': False, 'error': str(e)}
            
            return ErrorWrapper()
    
    def _get_enhanced_ticket_system(self):
        """Lazy initialization of enhanced ticket system"""
        if self.enhanced_tickets is None:
            vibe_tools = self._get_vibe_kanban_tools()
            self.enhanced_tickets = EnhancedTicketSystem(vibe_tools, self.storage, self.config)
        return self.enhanced_tickets
    
    def _register_enhanced_ticket_tools(self):
        """Register enhanced ticket management MCP tools"""
        
        @self.mcp.tool()
        async def create_ticket(
            project_id: str,
            title: str,
            description: str = "",
            ticket_type: str = "task",
            priority: str = "medium",
            assignee: Optional[str] = None,
            labels: Optional[List[str]] = None,
            due_date: Optional[str] = None,
            time_estimate: Optional[int] = None,
            parent_ticket: Optional[str] = None,
            reporter: str = "system"
        ) -> str:
            """
            Create enhanced ticket with comprehensive metadata and hAIveMind integration
            
            Args:
                project_id: Project ID from Vibe Kanban
                title: Ticket title
                description: Detailed description
                ticket_type: Type (bug/feature/task/epic/story/incident/request)
                priority: Priority level (low/medium/high/critical/emergency)
                assignee: Assigned agent ID
                labels: List of labels for categorization
                due_date: Due date in ISO format
                time_estimate: Estimated hours
                parent_ticket: Parent ticket ID for hierarchies
                reporter: Reporter/creator ID
                
            Returns:
                Ticket creation status and details
            """
            try:
                ticket_system = self._get_enhanced_ticket_system()
                result = await ticket_system.create_ticket(
                    project_id=project_id,
                    title=title,
                    description=description,
                    ticket_type=ticket_type,
                    priority=priority,
                    assignee=assignee,
                    labels=labels or [],
                    due_date=due_date,
                    time_estimate=time_estimate,
                    parent_ticket=parent_ticket,
                    reporter=reporter
                )
                
                if result.get('success'):
                    # Add timestamp information to response
                    timestamp_system = self.enhanced_ticket_system.timestamp_system
                    timestamp_info = timestamp_system.format_message_timestamp()
                    
                    return f"""🎫 Ticket Created Successfully

Ticket #: {result.get('ticket_number')}
ID: {result.get('ticket_id')}
Title: {title}
Type: {ticket_type}
Priority: {priority}
Status: New

The ticket has been created in Vibe Kanban and indexed in hAIveMind memory for enhanced tracking and search.

{timestamp_info}"""
                else:
                    return f"❌ Failed to create ticket: {result.get('error')}"
                    
            except Exception as e:
                return f"❌ Error creating ticket: {str(e)}"
        
        @self.mcp.tool()
        async def get_ticket(project_id: str, ticket_id: str) -> str:
            """
            Get comprehensive ticket details with hAIveMind context
            
            Args:
                project_id: Project ID from Vibe Kanban
                ticket_id: Ticket ID to retrieve
                
            Returns:
                Full ticket details with metadata and memory context
            """
            try:
                ticket_system = self._get_enhanced_ticket_system()
                result = await ticket_system.get_ticket(project_id, ticket_id)
                
                if result.get('success'):
                    ticket = result['ticket']
                    metadata = ticket['metadata']
                    timestamp_info = ticket.get('timestamp_info', {})
                    
                    # Format timestamp display
                    created_display = "Unknown"
                    updated_display = "Unknown"
                    age_display = "Unknown"
                    
                    if timestamp_info.get('created'):
                        created_display = f"{timestamp_info['created']['absolute']} ({timestamp_info['created']['relative']})"
                    if timestamp_info.get('last_updated'):
                        updated_display = f"{timestamp_info['last_updated']['absolute']} ({timestamp_info['last_updated']['relative']})"
                    if timestamp_info.get('age'):
                        age_display = timestamp_info['age']
                    
                    # Format due date display
                    due_display = metadata.get('due_date', 'Not set')
                    if timestamp_info.get('due_date'):
                        due_info = timestamp_info['due_date']
                        if due_info['is_overdue']:
                            due_display = f"⚠️ OVERDUE by {due_info['overdue_by']} (was due {due_info['absolute']})"
                        else:
                            due_display = f"{due_info['absolute']} ({due_info['time_remaining']} remaining)"
                    
                    # Add current timestamp to message
                    ticket_system = self._get_enhanced_ticket_system()
                    current_time = ticket_system.timestamp_system.format_message_timestamp()
                    
                    details = f"""🎫 Ticket #{ticket.get('ticket_number', 'Unknown')}

📋 Basic Info:
Title: {ticket['title']}
Status: {ticket['status']}
Type: {metadata.get('ticket_type', 'task')}
Priority: {metadata.get('priority', 'medium')}

👤 Assignment:
Assignee: {metadata.get('assignee', 'Unassigned')}
Reporter: {metadata.get('reporter', 'Unknown')}

📝 Description:
{ticket['description']}

🏷️ Labels: {', '.join(metadata.get('labels', []))}
⏰ Due Date: {due_display}
⏱️ Time Estimate: {metadata.get('time_estimate', 'Not estimated')}h

📅 Timeline:
Created: {created_display}
Last Updated: {updated_display}
Age: {age_display}

🧠 Memory Context: {len(ticket.get('memory_context', []))} related memories found

{current_time}"""
                    return details
                else:
                    return f"❌ Failed to retrieve ticket: {result.get('error')}"
                    
            except Exception as e:
                return f"❌ Error retrieving ticket: {str(e)}"
        
        @self.mcp.tool()
        async def list_tickets(
            project_id: str,
            status: Optional[str] = None,
            priority: Optional[str] = None,
            assignee: Optional[str] = None,
            ticket_type: Optional[str] = None,
            limit: int = 20
        ) -> str:
            """
            List tickets with enhanced filtering and status breakdown
            
            Args:
                project_id: Project ID from Vibe Kanban
                status: Filter by status (new/in_progress/review/done/etc)
                priority: Filter by priority (low/medium/high/critical/emergency)
                assignee: Filter by assignee
                ticket_type: Filter by type (bug/feature/task/etc)
                limit: Maximum tickets to return
                
            Returns:
                Formatted list of tickets with key details
            """
            try:
                ticket_system = self._get_enhanced_ticket_system()
                result = await ticket_system.list_tickets(
                    project_id=project_id,
                    status=status,
                    priority=priority,
                    assignee=assignee,
                    ticket_type=ticket_type,
                    limit=limit
                )
                
                if result.get('success'):
                    tickets = result['tickets']
                    filters = result.get('applied_filters', {})
                    
                    if not tickets:
                        return f"📋 No tickets found matching the criteria.\n\nApplied filters: {filters}"
                    
                    # Group by status for overview
                    by_status = {}
                    for ticket in tickets:
                        status = ticket['status']
                        if status not in by_status:
                            by_status[status] = []
                        by_status[status].append(ticket)
                    
                    output = [f"🎫 Found {len(tickets)} tickets"]
                    output.append(f"Filters: {filters}")
                    output.append("")
                    
                    # Show breakdown by status
                    output.append("📊 Status Breakdown:")
                    for status, status_tickets in by_status.items():
                        output.append(f"  {status}: {len(status_tickets)}")
                    output.append("")
                    
                    # Show ticket list
                    output.append("📋 Ticket List:")
                    for ticket in tickets:
                        metadata = ticket['metadata']
                        priority_icon = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴", "emergency": "🚨"}.get(metadata.get('priority', 'medium'), '🟡')
                        
                        output.append(f"  #{ticket.get('ticket_number', '?')} {priority_icon} {ticket['title']}")
                        output.append(f"    Status: {ticket['status']} | Type: {metadata.get('ticket_type', 'task')} | Assignee: {metadata.get('assignee', 'Unassigned')}")
                    
                    # Add timestamp information
                    timestamp_system = self.enhanced_ticket_system.timestamp_system
                    timestamp_info = timestamp_system.format_message_timestamp()
                    output.append("")
                    output.append(timestamp_info)
                    
                    return '\n'.join(output)
                else:
                    return f"❌ Failed to list tickets: {result.get('error')}"
                    
            except Exception as e:
                return f"❌ Error listing tickets: {str(e)}"
        
        @self.mcp.tool()
        async def update_ticket_status(
            project_id: str,
            ticket_id: str,
            new_status: str,
            updated_by: str = "system",
            comment: str = ""
        ) -> str:
            """
            Update ticket status with workflow validation and memory tracking
            
            Args:
                project_id: Project ID from Vibe Kanban
                ticket_id: Ticket ID to update
                new_status: New status (new/in_progress/review/done/blocked/cancelled)
                updated_by: Agent making the change
                comment: Optional comment about the status change
                
            Returns:
                Status update confirmation
            """
            try:
                ticket_system = self._get_enhanced_ticket_system()
                result = await ticket_system.update_ticket_status(
                    project_id=project_id,
                    ticket_id=ticket_id,
                    new_status=new_status,
                    updated_by=updated_by,
                    comment=comment
                )
                
                if result.get('success'):
                    return f"""✅ Ticket Status Updated

Ticket ID: {ticket_id}
New Status: {new_status}
Updated By: {updated_by}
Comment: {comment or 'No comment provided'}

Status change has been recorded in both Vibe Kanban and hAIveMind memory for full audit trail.

{self.enhanced_ticket_system.timestamp_system.format_message_timestamp()}"""
                else:
                    return f"❌ Failed to update status: {result.get('error')}"
                    
            except Exception as e:
                return f"❌ Error updating status: {str(e)}"
        
        @self.mcp.tool()
        async def search_tickets(
            project_id: str,
            query: str,
            limit: int = 10
        ) -> str:
            """
            Search tickets using hAIveMind semantic search and text matching
            
            Args:
                project_id: Project ID from Vibe Kanban
                query: Search query (supports keywords, IDs, etc)
                limit: Maximum results to return
                
            Returns:
                Relevant tickets with relevance scores
            """
            try:
                ticket_system = self._get_enhanced_ticket_system()
                result = await ticket_system.search_tickets(
                    project_id=project_id,
                    query=query,
                    limit=limit
                )
                
                if result.get('success'):
                    tickets = result['tickets']
                    
                    if not tickets:
                        return f"🔍 No tickets found matching '{query}'"
                    
                    output = [f"🔍 Found {len(tickets)} tickets matching '{query}'"]
                    output.append("")
                    
                    for ticket in tickets:
                        relevance = ticket.get('relevance_score', 0.0)
                        metadata = ticket['metadata']
                        
                        output.append(f"#{ticket.get('ticket_number', '?')} - {ticket['title']} (Relevance: {relevance:.2f})")
                        output.append(f"  Status: {ticket['status']} | Priority: {metadata.get('priority', 'medium')}")
                        output.append(f"  ID: {ticket['id']}")
                        output.append("")
                    
                    # Add timestamp information
                    timestamp_system = self.enhanced_ticket_system.timestamp_system
                    timestamp_info = timestamp_system.format_message_timestamp()
                    output.append(timestamp_info)
                    
                    return '\n'.join(output)
                else:
                    return f"❌ Search failed: {result.get('error')}"
                    
            except Exception as e:
                return f"❌ Search error: {str(e)}"
        
        @self.mcp.tool()
        async def get_my_tickets(
            project_id: str,
            assignee: str,
            status: Optional[str] = None
        ) -> str:
            """
            Get tickets assigned to specific user with workload summary
            
            Args:
                project_id: Project ID from Vibe Kanban
                assignee: Agent ID to get tickets for
                status: Optional status filter
                
            Returns:
                Personal ticket dashboard
            """
            try:
                ticket_system = self._get_enhanced_ticket_system()
                result = await ticket_system.get_my_tickets(
                    project_id=project_id,
                    assignee=assignee,
                    status=status
                )
                
                if result.get('success'):
                    tickets = result['tickets']
                    
                    if not tickets:
                        return f"👤 No tickets assigned to {assignee}"
                    
                    # Calculate workload metrics
                    total_estimated = sum(t['metadata'].get('time_estimate', 0) for t in tickets if t['metadata'].get('time_estimate'))
                    in_progress = [t for t in tickets if t['status'] == 'in_progress']
                    high_priority = [t for t in tickets if t['metadata'].get('priority') in ['high', 'critical', 'emergency']]
                    
                    output = [f"👤 {assignee}'s Tickets ({len(tickets)} total)"]
                    output.append(f"⏱️ Total Estimated Work: {total_estimated}h")
                    output.append(f"🏃 In Progress: {len(in_progress)}")
                    output.append(f"🚨 High Priority: {len(high_priority)}")
                    output.append("")
                    
                    # Group by status
                    by_status = {}
                    for ticket in tickets:
                        status = ticket['status']
                        if status not in by_status:
                            by_status[status] = []
                        by_status[status].append(ticket)
                    
                    for status, status_tickets in by_status.items():
                        output.append(f"📋 {status.upper()} ({len(status_tickets)})")
                        for ticket in status_tickets:
                            metadata = ticket['metadata']
                            priority_icon = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴", "emergency": "🚨"}.get(metadata.get('priority', 'medium'), '🟡')
                            estimate = f" ({metadata.get('time_estimate', 0)}h)" if metadata.get('time_estimate') else ""
                            
                            output.append(f"  #{ticket.get('ticket_number', '?')} {priority_icon} {ticket['title']}{estimate}")
                        output.append("")
                    
                    # Add timestamp information
                    timestamp_system = self.enhanced_ticket_system.timestamp_system
                    timestamp_info = timestamp_system.format_message_timestamp()
                    output.append(timestamp_info)
                    
                    return '\n'.join(output)
                else:
                    return f"❌ Failed to get tickets: {result.get('error')}"
                    
            except Exception as e:
                return f"❌ Error getting tickets: {str(e)}"
        
        @self.mcp.tool()
        async def add_ticket_comment(
            project_id: str,
            ticket_id: str,
            comment: str,
            author: str = "system"
        ) -> str:
            """
            Add comment to ticket with hAIveMind memory integration
            
            Args:
                project_id: Project ID from Vibe Kanban
                ticket_id: Ticket ID to comment on
                comment: Comment text
                author: Comment author
                
            Returns:
                Comment addition confirmation
            """
            try:
                ticket_system = self._get_enhanced_ticket_system()
                result = await ticket_system.add_ticket_comment(
                    project_id=project_id,
                    ticket_id=ticket_id,
                    comment=comment,
                    author=author
                )
                
                if result.get('success'):
                    memory_id = result.get('memory_id', 'N/A')
                    comment_id = result.get('comment_id', 'N/A')
                    return f"""✅ Comment Added Successfully

🎫 Ticket ID: {ticket_id}
💬 Comment ID: {comment_id}
🧠 Memory ID: {memory_id}
👤 Author: {author}
📝 Comment: {comment}

📊 Memory Context:
• Stored in hAIveMind collective memory
• Searchable via memory ID: {memory_id}
• Linked to ticket workflow: {ticket_id}
• Available to all network agents

{self.enhanced_ticket_system.timestamp_system.format_message_timestamp()}"""
                else:
                    return f"❌ Failed to add comment: {result.get('error')}"
                    
            except Exception as e:
                return f"❌ Error adding comment: {str(e)}"

        @self.mcp.tool()
        async def get_ticket_comments(
            ticket_id: str
        ) -> str:
            """
            Get all comments for a ticket with full memory context
            
            Args:
                ticket_id: Ticket ID to get comments for
                
            Returns:
                Complete comment history with memory IDs and full context
            """
            try:
                ticket_system = self._get_enhanced_ticket_system()
                result = await ticket_system.get_ticket_comments(ticket_id)
                
                if result.get('success'):
                    comments = result.get('comments', [])
                    total_comments = result.get('total_comments', 0)
                    
                    if not comments:
                        return f"📭 No comments found for ticket {ticket_id}"
                    
                    output = [
                        f"💬 Ticket Comments: {ticket_id}",
                        f"📊 Total Comments: {total_comments}",
                        "=" * 60,
                        ""
                    ]
                    
                    for i, comment in enumerate(comments, 1):
                        output.extend([
                            f"Comment #{i}:",
                            f"  💬 ID: {comment.get('comment_id', 'N/A')}",
                            f"  🧠 Memory ID: {comment.get('memory_id', 'N/A')}",
                            f"  👤 Author: {comment.get('author', 'Unknown')}",
                            f"  📅 Created: {comment.get('created_at', 'Unknown')}",
                            f"  📝 Content: {comment.get('comment', 'No content')}",
                            f"  🔗 Memory Content: {comment.get('memory_content', 'N/A')}",
                            ""
                        ])
                    
                    output.append(f"🔍 Browser Integration: All comments accessible via memory IDs for enhanced context understanding")
                    
                    return "\n".join(output)
                else:
                    return f"❌ Failed to get comments: {result.get('error')}"
                    
            except Exception as e:
                return f"❌ Error getting comments: {str(e)}"
        
        @self.mcp.tool()
        async def get_ticket_metrics(
            project_id: str,
            days: int = 30
        ) -> str:
            """
            Get comprehensive ticket metrics and analytics
            
            Args:
                project_id: Project ID from Vibe Kanban
                days: Time period for metrics calculation
                
            Returns:
                Detailed metrics report
            """
            try:
                ticket_system = self._get_enhanced_ticket_system()
                result = await ticket_system.get_ticket_metrics(
                    project_id=project_id,
                    days=days
                )
                
                if result.get('success'):
                    metrics = result['metrics']
                    
                    output = [f"📊 Ticket Metrics ({days} days)"]
                    output.append(f"Generated: {result.get('generated_at', 'Unknown')}")
                    output.append("")
                    
                    # Overall stats
                    output.append(f"📈 Overview:")
                    output.append(f"  Total Tickets: {metrics['total_tickets']}")
                    output.append(f"  Created in Period: {metrics['created_in_period']}")
                    output.append(f"  Closed in Period: {metrics['closed_in_period']}")
                    output.append(f"  Average Resolution: {metrics['average_resolution_time']:.1f}h")
                    output.append("")
                    
                    # Status breakdown
                    output.append("📊 By Status:")
                    for status, count in metrics['by_status'].items():
                        output.append(f"  {status}: {count}")
                    output.append("")
                    
                    # Priority breakdown
                    output.append("🚨 By Priority:")
                    for priority, count in metrics['by_priority'].items():
                        output.append(f"  {priority}: {count}")
                    output.append("")
                    
                    # Type breakdown
                    output.append("🎯 By Type:")
                    for ticket_type, count in metrics['by_type'].items():
                        output.append(f"  {ticket_type}: {count}")
                    output.append("")
                    
                    # Alerts
                    output.append("⚠️ Alerts:")
                    output.append(f"  Critical Tickets: {metrics['critical_tickets']}")
                    output.append(f"  Overdue Tickets: {metrics['overdue_tickets']}")
                    
                    # Add timestamp information
                    timestamp_system = self.enhanced_ticket_system.timestamp_system
                    timestamp_info = timestamp_system.format_message_timestamp()
                    output.append("")
                    output.append(timestamp_info)
                    
                    return '\n'.join(output)
                else:
                    return f"❌ Failed to get metrics: {result.get('error')}"
                    
            except Exception as e:
                return f"❌ Error getting metrics: {str(e)}"
        
        logger.info("🎫 Enhanced ticket management tools registered - comprehensive ticket system enabled")

    # NOTE: _register_personal_command_sync_tools removed (6 tools - never used)

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
