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
        
        # Add admin interface routes
        self._add_admin_routes()
        
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
        
        logger.info("🤝 All hive mind tools synchronized with network portal - collective intelligence ready")
    
    def _add_admin_routes(self):
        """Add admin web interface routes"""
        from starlette.responses import HTMLResponse, JSONResponse, FileResponse
        from starlette.staticfiles import StaticFiles
        import os
        
        admin_dir = str(Path(__file__).parent.parent / "admin")
        
        # Serve static files
        @self.mcp.custom_route("/admin/static/{path:path}", methods=["GET"])
        async def admin_static(request):
            static_path = os.path.join(admin_dir, "static", request.path_params["path"])
            if os.path.exists(static_path):
                return FileResponse(static_path)
            return JSONResponse({"error": "File not found"}, status_code=404)
        
        # Serve admin HTML pages
        @self.mcp.custom_route("/admin/{page}", methods=["GET"])
        async def admin_pages(request):
            page = request.path_params["page"]
            if not page.endswith('.html'):
                page += '.html'
            
            page_path = os.path.join(admin_dir, page)
            if os.path.exists(page_path):
                return FileResponse(page_path)
            return JSONResponse({"error": "Page not found"}, status_code=404)
        
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
    
    async def _check_admin_auth(self, request):
        """Check if request has valid admin authentication"""
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return False
        
        token = auth_header.split(' ')[1]
        valid, payload = self.auth.validate_jwt_token(token)
        return valid and payload.get('role') == 'admin'
    
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