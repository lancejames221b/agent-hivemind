#!/usr/bin/env python3
"""
ClaudeOps hAIveMind - Distributed memory storage for Claude agents
Uses ChromaDB for vector storage with Redis caching and remote synchronization
Enables multi-agent collaboration across DevOps infrastructure via collective AI
"""

import asyncio
import threading
import json
import os
import time
import uuid
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging
import socket

import redis
import chromadb
from chromadb.config import Settings
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryStorage:
    """ClaudeOps hAIveMind - ChromaDB vector storage with Redis caching for multi-agent DevOps collaboration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.machine_id = self._get_machine_id()
        self.agent_id = self._get_agent_id()
        self.chroma_client = None
        self.collections = {}
        self.redis_client = None
        self.agents_registry = {}  # Track active agents
        self._agent_cleanup_thread_started = False
        
        # Initialize ChromaDB
        self._init_chromadb()
        
        # Initialize Redis if enabled
        if config['storage']['redis']['enable_cache']:
            self._init_redis()
        
        # Initialize agent registry
        self._init_agent_registry()

        # Start periodic cleanup of stale agent IDs if Redis is enabled
        self._start_agent_cleanup_task()
    
    def _get_machine_id(self) -> str:
        """Get unique machine identifier"""
        try:
            import subprocess
            result = subprocess.run(['tailscale', 'status', '--json'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                status = json.loads(result.stdout)
                return status.get('Self', {}).get('HostName', socket.gethostname())
        except Exception:
            pass
        return socket.gethostname()
    
    def _get_agent_id(self) -> str:
        """Generate unique agent identifier based on machine, user, and working context"""
        import hashlib
        import getpass
        
        # Create unique agent ID based on machine, user, and process context
        user = getpass.getuser()
        pid = os.getpid()
        working_context = os.environ.get('TERM_PROGRAM', 'terminal')
        
        # Create a readable but unique agent ID
        base_id = f"{self.machine_id}-{user}-{working_context.lower()}"
        
        # Add timestamp component for uniqueness across sessions
        timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
        agent_id = f"{base_id}-{timestamp}"
        
        return agent_id
    
    def _init_agent_registry(self):
        """Initialize agent registry in Redis"""
        if not self.redis_client:
            return
            
        try:
            # Register this agent
            agent_info = {
                'agent_id': self.agent_id,
                'machine_id': self.machine_id,
                'user': os.environ.get('USER', 'unknown'),
                'working_context': os.environ.get('TERM_PROGRAM', 'terminal'),
                'capabilities': ','.join(self._get_agent_capabilities()),  # Convert list to string
                'role': self._determine_agent_role(),
                'status': 'active',
                'last_seen': str(time.time()),
                'registered_at': str(time.time()),
                'pid': str(os.getpid())
            }
            
            # Store in Redis with TTL
            agent_key = f"agent:{self.agent_id}"
            self.redis_client.hset(agent_key, mapping=agent_info)
            self.redis_client.expire(agent_key, 3600)  # 1 hour TTL
            
            # Add to active agents set
            self.redis_client.sadd("active_agents", self.agent_id)
            
            logger.info(f"🧠 Drone {self.agent_id} connected to hive network on node {self.machine_id} - collective intelligence expanding")
            
        except Exception as e:
            logger.warning(f"⚠️ Hive network initialization disrupted: {e} - operating in isolated mode")
    
    def _get_agent_capabilities(self) -> List[str]:
        """Determine agent capabilities based on machine and context"""
        capabilities = ['memory_storage', 'search', 'conversation']
        
        # Add machine-specific capabilities based on machine groups
        machine_groups = self.config.get('memory', {}).get('machine_groups', {})
        
        for group_name, machines in machine_groups.items():
            if self.machine_id in machines:
                if group_name == 'elasticsearch':
                    capabilities.extend(['elasticsearch_ops', 'search_tuning', 'cluster_management'])
                elif group_name == 'databases':
                    capabilities.extend(['database_ops', 'backup_restore', 'query_optimization'])
                elif group_name == 'scrapers':
                    capabilities.extend(['data_collection', 'scraping', 'proxy_management'])
                elif group_name == 'dev_environments':
                    capabilities.extend(['development', 'testing', 'code_review'])
                elif group_name == 'monitoring':
                    capabilities.extend(['monitoring', 'alerting', 'incident_response'])
                elif group_name == 'orchestrators':
                    capabilities.extend(['coordination', 'deployment', 'infrastructure_management'])
        
        return capabilities
    
    def _determine_agent_role(self) -> str:
        """Determine agent role based on machine and capabilities"""
        machine_groups = self.config.get('memory', {}).get('machine_groups', {})
        
        for group_name, machines in machine_groups.items():
            if self.machine_id in machines:
                if group_name == 'orchestrators':
                    return 'hive_mind'
                elif group_name == 'elasticsearch':
                    return 'knowledge_seeker'
                elif group_name == 'databases':
                    return 'memory_keeper'
                elif group_name == 'scrapers':
                    return 'harvest_agent'
                elif group_name == 'dev_environments':
                    return 'code_weaver'
                elif group_name == 'monitoring':
                    return 'sentinel_node'
        
        return 'worker_drone'
    
    def _get_system_context(self) -> Dict[str, Any]:
        """Get comprehensive system context including machine, network, and environment info"""
        import platform
        import getpass
        import subprocess
        import socket as sock
        
        context = {
            'machine_id': self.machine_id,
            'hostname': sock.gethostname(),
            'user': getpass.getuser(),
            'os': platform.system(),
            'platform': platform.machine(),
            'python_version': platform.python_version(),
            'timestamp': datetime.now().isoformat()
        }
        
        # Get IP addresses
        try:
            # Local IP
            s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            context['local_ip'] = s.getsockname()[0]
            s.close()
        except Exception:
            context['local_ip'] = 'unknown'
        
        # Get Tailscale IP if available
        try:
            result = subprocess.run(['tailscale', 'status', '--json'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                status = json.loads(result.stdout)
                context['tailscale_ip'] = status.get('Self', {}).get('TailscaleIPs', ['unknown'])[0]
                context['tailscale_hostname'] = status.get('Self', {}).get('HostName', 'unknown')
        except Exception:
            context['tailscale_ip'] = 'unavailable'
            context['tailscale_hostname'] = 'unavailable'
        
        # Detect SSH connection
        ssh_client = os.environ.get('SSH_CLIENT')
        if ssh_client:
            context['ssh_connection'] = f"from {ssh_client.split()[0]}"
        else:
            context['ssh_connection'] = None
        
        # Detect environment type
        if any(indicator in os.getcwd().lower() for indicator in ['prod', 'production']):
            context['environment'] = 'production'
        elif any(indicator in os.getcwd().lower() for indicator in ['dev', 'development']):
            context['environment'] = 'development'
        elif any(indicator in os.getcwd().lower() for indicator in ['test', 'staging']):
            context['environment'] = 'staging'
        else:
            context['environment'] = 'unknown'
        
        # Detect working context
        if os.environ.get('VSCODE_PID'):
            context['working_context'] = 'vscode'
        elif os.environ.get('TERM_PROGRAM') == 'Claude Code':
            context['working_context'] = 'claude-code'
        elif os.environ.get('SSH_TTY'):
            context['working_context'] = 'ssh-terminal'
        else:
            context['working_context'] = 'terminal'
        
        return context
    
    def _get_project_context(self) -> Dict[str, str]:
        """Get current project context from working directory"""
        current_path = os.getcwd()
        project_name = os.path.basename(current_path)
        
        # Check if we're in a git repository
        git_root = None
        git_branch = None
        try:
            import subprocess
            # Get git root with timeout
            result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], 
                                  capture_output=True, text=True, cwd=current_path, timeout=10)
            if result.returncode == 0:
                git_root = result.stdout.strip()
                if git_root != current_path:
                    project_name = os.path.basename(git_root)
            
            # Get current branch with timeout
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                  capture_output=True, text=True, cwd=current_path, timeout=10)
            if result.returncode == 0:
                git_branch = result.stdout.strip()
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError):
            # Handle git not available, timeouts, or other git-related errors
            pass
        
        return {
            'project_path': current_path,
            'project_name': project_name,
            'git_root': git_root,
            'git_branch': git_branch
        }
    
    def _get_machine_groups(self) -> Dict[str, List[str]]:
        """Get machine groups configuration"""
        return self.config.get('memory', {}).get('machine_groups', {})
    
    def _get_sharing_rules(self) -> Dict[str, Any]:
        """Get sharing rules configuration"""
        default_rules = {
            'default_scope': 'project-shared',
            'sync_with_groups': ['personal'],
            'exclude_machines': [],
            'private_categories': ['agent']
        }
        return self.config.get('memory', {}).get('sharing_rules', default_rules)
    
    def _determine_sharing_scope(self, scope: Optional[str], category: str, 
                                share_with: Optional[List[str]] = None,
                                exclude_from: Optional[List[str]] = None,
                                sensitive: bool = False) -> Dict[str, Any]:
        """Determine the effective sharing scope and rules for a memory"""
        sharing_rules = self._get_sharing_rules()
        machine_groups = self._get_machine_groups()
        
        # Force private scope for sensitive data
        if sensitive:
            scope = "private"
        
        # Use default scope if none specified
        if scope is None:
            scope = sharing_rules.get('default_scope', 'project-shared')
        
        # Check if category should be private
        private_categories = sharing_rules.get('private_categories', [])
        if category in private_categories:
            scope = "machine-local"
        
        # Determine which machines can access this memory
        allowed_machines = set()
        excluded_machines = set(exclude_from or [])
        excluded_machines.update(sharing_rules.get('exclude_machines', []))
        
        if scope == "private" or scope == "machine-local":
            allowed_machines = {self.machine_id}
        elif scope == "project-local":
            allowed_machines = {self.machine_id}
        elif scope == "project-shared":
            # Share with machines in configured groups
            sync_groups = sharing_rules.get('sync_with_groups', [])
            for group_name in sync_groups:
                group_machines = machine_groups.get(group_name, [])
                allowed_machines.update(group_machines)
            allowed_machines.add(self.machine_id)  # Always include current machine
        elif scope == "user-global":
            # Share with all user's machines (all groups)
            for group_machines in machine_groups.values():
                allowed_machines.update(group_machines)
            allowed_machines.add(self.machine_id)
        elif scope == "team-global":
            # Share with specific groups if specified
            if share_with:
                for group_name in share_with:
                    if group_name in machine_groups:
                        allowed_machines.update(machine_groups[group_name])
            allowed_machines.add(self.machine_id)
        
        # Apply exclusions
        allowed_machines = allowed_machines - excluded_machines
        
        return {
            'scope': scope,
            'allowed_machines': list(allowed_machines),
            'excluded_machines': list(excluded_machines),
            'sensitive': sensitive,
            'sync_enabled': len(allowed_machines) > 1
        }
    
    def _init_chromadb(self):
        """Initialize ChromaDB client and collections"""
        try:
            chroma_config = self.config['storage']['chromadb']
            db_path = chroma_config['path']
            
            # Create data directory
            Path(db_path).mkdir(parents=True, exist_ok=True)
            
            # Initialize persistent ChromaDB client
            self.chroma_client = chromadb.PersistentClient(
                path=db_path,
                settings=Settings(
                    anonymized_telemetry=chroma_config.get('anonymized_telemetry', False),
                    allow_reset=True
                )
            )
            
            # Create collections for each memory category
            categories = self.config['memory']['categories']
            for category in categories:
                collection_name = f"{category}_memories"
                try:
                    collection = self.chroma_client.get_collection(collection_name)
                    logger.info(f"Loaded existing collection: {collection_name}")
                except Exception:
                    # Collection doesn't exist, create it
                    collection = self.chroma_client.create_collection(
                        name=collection_name,
                        metadata={"category": category, "machine_id": self.machine_id}
                    )
                    logger.info(f"Created new collection: {collection_name}")
                
                self.collections[category] = collection
            
            logger.info(f"🧠 Memory matrix initialized - {len(self.collections)} knowledge clusters active in collective consciousness")
            
        except Exception as e:
            logger.error(f"💥 Memory matrix initialization failed: {e} - collective consciousness impaired")
            raise
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            redis_config = self.config['storage']['redis']
            self.redis_client = redis.Redis(
                host=redis_config['host'],
                port=redis_config['port'],
                db=redis_config['db'],
                password=redis_config.get('password'),
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("🔗 Neural network bridge established - hive mind synchronization active")
        except Exception as e:
            logger.warning(f"⚠️ Neural bridge connection failed: {e} - hive mind synchronization offline")
            self.redis_client = None

    # ===== Redis agent set maintenance =====
    def _cleanup_stale_agents_once(self) -> int:
        """Remove agent IDs from active_agents with no corresponding agent hash.

        Returns the number of removed IDs.
        """
        if not self.redis_client:
            return 0

        removed = 0
        try:
            agent_ids = self.redis_client.smembers("active_agents") or set()
            for agent_id in agent_ids:
                agent_key = f"agent:{agent_id}"
                # If the agent hash no longer exists (expired), remove from the set
                if not self.redis_client.exists(agent_key):
                    self.redis_client.srem("active_agents", agent_id)
                    removed += 1
            if removed:
                logger.info(f"🧹 Cleaned {removed} stale agent IDs from active_agents")
        except Exception as e:
            logger.warning(f"⚠️ Failed active_agents cleanup: {e}")
        return removed

    def _start_agent_cleanup_task(self, interval_seconds: int = 300) -> None:
        """Start a background daemon thread to periodically clean stale agent IDs.

        Uses a simple thread with time.sleep to avoid coupling to asyncio loop lifecycle.
        """
        if self._agent_cleanup_thread_started or not self.redis_client:
            return

        def _loop():
            while True:
                try:
                    self._cleanup_stale_agents_once()
                except Exception as e:
                    logger.debug(f"agent cleanup loop error: {e}")
                time.sleep(interval_seconds)

        thread = threading.Thread(target=_loop, name="active_agents_cleanup", daemon=True)
        thread.start()
        self._agent_cleanup_thread_started = True
    
    def _apply_authorship_directives(self, content: str) -> str:
        """Apply authorship directives from configuration to content"""
        authorship_config = self.config.get('authorship', {})
        
        if authorship_config.get('disable_ai_attribution', False):
            # Remove AI attribution patterns
            ai_patterns = [
                r'🤖\s*Generated with \[Claude Code\]\([^)]*\)',
                r'Generated with Claude Code',
                r'Co-Authored-By:\s*Claude\s*<[^>]*>',
                r'Assistant:\s*',
                r'Claude:\s*',
                r'AI Assistant:\s*',
                r'Generated by AI',
                r'Created by Claude',
                r'Powered by Claude',
                r'With assistance from Claude'
            ]
            
            for pattern in ai_patterns:
                content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
        
        # Clean up extra whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = content.strip()
        
        return content
    
    async def store_memory(self, 
                          content: str, 
                          category: str = "global",
                          context: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None,
                          tags: Optional[List[str]] = None,
                          user_id: str = "default",
                          scope: Optional[str] = None,
                          share_with: Optional[List[str]] = None,
                          exclude_from: Optional[List[str]] = None,
                          sensitive: bool = False) -> str:
        """Store a memory with comprehensive system tracking and sharing control"""
        memory_id = str(uuid.uuid4())
        
        # Apply authorship directives
        content = self._apply_authorship_directives(content)
        
        # Get system and project context
        system_context = self._get_system_context()
        project_context = self._get_project_context()
        
        # Determine sharing scope and rules
        sharing_info = self._determine_sharing_scope(
            scope=scope, 
            category=category,
            share_with=share_with,
            exclude_from=exclude_from,
            sensitive=sensitive
        )
        
        # Validate category
        if category not in self.collections:
            logger.warning(f"🤔 Unknown memory cluster '{category}' - redirecting to global hive knowledge")
            category = "global"
        
        collection = self.collections[category]
        
        # Prepare comprehensive metadata
        memory_metadata = {
            # Basic info
            "memory_id": memory_id,
            "user_id": user_id,
            "category": category,
            "created_at": datetime.now().isoformat(),
            "context": context or "",
            "tags": ",".join(tags or []),
            
            # System context
            "machine_id": system_context["machine_id"],
            "hostname": system_context["hostname"],
            "user": system_context["user"],
            "os": system_context["os"],
            "environment": system_context["environment"],
            "working_context": system_context["working_context"],
            "local_ip": system_context["local_ip"],
            "tailscale_ip": system_context["tailscale_ip"],
            "ssh_connection": system_context.get("ssh_connection") or "",
            
            # Project context
            "project_path": project_context.get("project_path", ""),
            "project_name": project_context.get("project_name", ""),
            "git_root": project_context.get("git_root") or "",
            "git_branch": project_context.get("git_branch") or "",
            
            # Sharing and security
            "scope": sharing_info["scope"],
            "allowed_machines": ",".join(sharing_info["allowed_machines"]),
            "excluded_machines": ",".join(sharing_info["excluded_machines"]),
            "sensitive": str(sensitive).lower(),
            "sync_enabled": str(sharing_info["sync_enabled"]).lower()
        }
        
        # Add custom metadata
        if metadata:
            memory_metadata.update(metadata)
        
        # Store in ChromaDB (embedding is generated automatically) with timeout protection
        try:
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: collection.add(
                        documents=[content],
                        metadatas=[memory_metadata],
                        ids=[memory_id]
                    )
                ),
                timeout=20.0
            )
            
            logger.info(f"📝 Knowledge absorbed into hive mind - memory {memory_id} integrated into {category} cluster")
            
        except Exception as e:
            logger.error(f"💥 Memory integration failed: {e} - knowledge lost to the void")
            raise
        
        # Cache in Redis for fast access
        if self.redis_client:
            try:
                cache_data = {
                    'id': memory_id,
                    'content': content,
                    'category': category,
                    'context': context,
                    'metadata': json.dumps(memory_metadata),
                    'created_at': memory_metadata['created_at']
                }
                
                # Cache the memory
                self.redis_client.setex(f"memory:{memory_id}", 3600, json.dumps(cache_data))
                
                # Add to user's recent memories list
                self.redis_client.lpush(f"user_memories:{user_id}", memory_id)
                self.redis_client.expire(f"user_memories:{user_id}", 3600)
                
                # Add to category index
                self.redis_client.lpush(f"category_memories:{category}", memory_id)
                self.redis_client.expire(f"category_memories:{category}", 3600)
                
            except Exception as e:
                logger.warning(f"Failed to cache memory in Redis: {e}")
        
        return memory_id
    
    async def retrieve_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific memory by ID"""
        # Try Redis cache first
        if self.redis_client:
            try:
                cached = self.redis_client.get(f"memory:{memory_id}")
                if cached:
                    cache_data = json.loads(cached)
                    return {
                        'id': cache_data['id'],
                        'content': cache_data['content'],
                        'category': cache_data['category'],
                        'context': cache_data['context'],
                        'metadata': json.loads(cache_data['metadata']),
                        'created_at': cache_data['created_at']
                    }
            except Exception as e:
                logger.warning(f"Failed to retrieve from Redis cache: {e}")
        
        # Search all collections for the memory
        for category, collection in self.collections.items():
            try:
                result = collection.get(ids=[memory_id])
                if result['documents']:
                    return {
                        'id': memory_id,
                        'content': result['documents'][0],
                        'category': category,
                        'context': result['metadatas'][0].get('context', ''),
                        'metadata': result['metadatas'][0],
                        'created_at': result['metadatas'][0].get('created_at', '')
                    }
            except Exception as e:
                logger.debug(f"Memory {memory_id} not found in {category}: {e}")
                continue
        
        return None
    
    async def search_memories(self, 
                             query: str,
                             category: Optional[str] = None,
                             user_id: Optional[str] = None,
                             limit: int = 10,
                             semantic: bool = True,
                             scope: Optional[str] = None,
                             include_global: bool = True,
                             from_machines: Optional[List[str]] = None,
                             exclude_machines: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search memories with comprehensive filtering including machine, project, and sharing scope"""
        memories = []
        
        # Get current context
        current_project = self._get_project_context()
        current_machine = self.machine_id
        
        # Determine which collections to search
        collections_to_search = {}
        if category and category in self.collections:
            collections_to_search[category] = self.collections[category]
        else:
            collections_to_search = self.collections
        
        # Search each collection
        for cat_name, collection in collections_to_search.items():
            try:
                # Build metadata filter
                where_filter = {}
                if user_id:
                    where_filter["user_id"] = user_id
                
                # Add project filtering if specified
                if scope == "project" and current_project.get("project_path"):
                    where_filter["project_path"] = current_project["project_path"]
                elif scope == "machine-local":
                    where_filter["machine_id"] = current_machine
                
                # Add machine filtering
                if from_machines:
                    # ChromaDB doesn't support complex OR queries easily, so we'll filter post-query
                    pass  # Will filter after retrieval
                
                if exclude_machines:
                    # Will filter after retrieval
                    pass
                
                # Perform semantic search with timeout protection
                results = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: collection.query(
                            query_texts=[query],
                            n_results=min(limit, 50),  # ChromaDB limit per query
                            where=where_filter if where_filter else None
                        )
                    ),
                    timeout=25.0  # Timeout for complex embedding searches
                )
                
                # Process results - ChromaDB query returns nested arrays, so access first level
                if results['documents'] and results['documents'][0]:
                    docs = results['documents'][0]
                    metas = results['metadatas'][0] 
                    ids = results['ids'][0]
                    for i, doc in enumerate(docs):
                        metadata = metas[i]
                        memory_machine = metadata.get('machine_id', '')
                        
                        # Apply machine filtering
                        if from_machines and memory_machine not in from_machines:
                            continue
                        if exclude_machines and memory_machine in exclude_machines:
                            continue
                        
                        # Check if memory is accessible to current machine
                        allowed_machines = metadata.get('allowed_machines', '').split(',')
                        if allowed_machines and allowed_machines != [''] and current_machine not in allowed_machines:
                            continue
                        
                        memory_data = {
                            'id': ids[i],
                            'content': doc,
                            'category': cat_name,
                            'context': metadata.get('context', ''),
                            'metadata': metadata,
                            'created_at': metadata.get('created_at', ''),
                            'score': 1.0 - results['distances'][0][i] if results.get('distances') else 1.0
                        }
                        memories.append(memory_data)
                        
            except asyncio.TimeoutError:
                logger.error(f"Search timed out in collection {cat_name} after 25 seconds - skipping")
                continue
            except Exception as e:
                logger.error(f"Search failed in collection {cat_name}: {e}")
                continue
        
        # Sort by relevance score and limit results
        memories.sort(key=lambda x: x.get('score', 0), reverse=True)
        return memories[:limit]
    
    async def get_recent_memories(self, 
                                 user_id: Optional[str] = None,
                                 category: Optional[str] = None,
                                 hours: int = 24,
                                 limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent memories within specified time window"""
        since = datetime.now() - timedelta(hours=hours)
        since_iso = since.isoformat()
        
        memories = []
        
        # Determine which collections to search
        collections_to_search = {}
        if category and category in self.collections:
            collections_to_search[category] = self.collections[category]
        else:
            collections_to_search = self.collections
        
        # Get recent memories from each collection
        for cat_name, collection in collections_to_search.items():
            try:
                # Build metadata filter
                where_filter = {}
                if user_id:
                    where_filter["user_id"] = user_id
                
                # Get all memories (ChromaDB doesn't have great time filtering)
                # We'll filter by time after retrieval, with timeout protection
                results = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: collection.get(
                            where=where_filter if where_filter else None,
                            limit=limit * 2  # Get more to filter by time
                        )
                    ),
                    timeout=25.0
                )
                
                if results['documents']:
                    for i, doc in enumerate(results['documents']):
                        created_at = results['metadatas'][i].get('created_at', '')
                        if created_at and created_at >= since_iso:
                            memory_data = {
                                'id': results['ids'][i],
                                'content': doc,
                                'category': cat_name,
                                'context': results['metadatas'][i].get('context', ''),
                                'metadata': results['metadatas'][i],
                                'created_at': created_at
                            }
                            memories.append(memory_data)
                            
            except Exception as e:
                logger.error(f"Failed to get recent memories from {cat_name}: {e}")
                continue
        
        # Sort by creation time (newest first) and limit
        memories.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return memories[:limit]
    
    def _parse_conversation(self, conversation_text: str, source: str = "unknown") -> List[Dict[str, Any]]:
        """Parse conversation text and extract individual messages"""
        messages = []
        
        # Common patterns for conversation parsing
        patterns = [
            # Claude/Assistant pattern: "Human: ... Assistant: ..."
            r'(?:Human|User):\s*(.*?)(?=(?:Human|User|Assistant):|$)',
            r'(?:Assistant|Claude):\s*(.*?)(?=(?:Human|User|Assistant):|$)',
            
            # Timestamp pattern: "[timestamp] Speaker: message"
            r'\[([^\]]+)\]\s*([^:]+):\s*(.*?)(?=\[[^\]]+\]|$)',
            
            # Speaker pattern: "Speaker: message"
            r'^([A-Za-z0-9_\s]+):\s*(.*?)(?=^[A-Za-z0-9_\s]+:|$)',
            
            # Markdown pattern: "## Speaker\nmessage"
            r'##\s*([^\n]+)\n(.*?)(?=##|$)',
        ]
        
        # Try different parsing approaches
        parsed_messages = []
        
        # First try Human/Assistant pattern (most common for Claude exports)
        human_assistant_pattern = r'(Human|User):\s*(.*?)(?=(?:Human|User|Assistant|Claude):|$)'
        assistant_pattern = r'(Assistant|Claude):\s*(.*?)(?=(?:Human|User|Assistant|Claude):|$)'
        
        # Combine and sort by position
        all_matches = []
        
        for match in re.finditer(human_assistant_pattern, conversation_text, re.DOTALL | re.IGNORECASE):
            all_matches.append((match.start(), 'human', match.group(2).strip()))
        
        for match in re.finditer(assistant_pattern, conversation_text, re.DOTALL | re.IGNORECASE):
            all_matches.append((match.start(), 'assistant', match.group(2).strip()))
        
        # Sort by position in text
        all_matches.sort(key=lambda x: x[0])
        
        # If no structured conversation found, treat as single message
        if not all_matches:
            # Try to detect if it's a single message or unstructured conversation
            lines = conversation_text.strip().split('\n')
            if len(lines) > 5:  # Likely a conversation
                all_matches = [(0, 'mixed', conversation_text.strip())]
            else:  # Single message
                all_matches = [(0, 'user', conversation_text.strip())]
        
        # Convert to structured messages
        conversation_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        for i, (pos, role, content) in enumerate(all_matches):
            if content.strip():  # Skip empty messages
                messages.append({
                    'role': role,
                    'content': content.strip(),
                    'conversation_id': conversation_id,
                    'message_index': i,
                    'source': source,
                    'imported_at': timestamp,
                    'original_position': pos
                })
        
        return messages
    
    async def import_conversation_file(self,
                                      file_path: str,
                                      title: Optional[str] = None,
                                      user_id: str = "default",
                                      tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Import conversation from a file"""
        try:
            # Expand user path and make absolute
            file_path = str(Path(file_path).expanduser().resolve())
            
            # Check if file exists
            if not Path(file_path).exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                conversation_text = f.read()
            
            # Use filename as title if not provided
            if not title:
                title = Path(file_path).stem
            
            # Import with file source
            result = await self.import_conversation(
                conversation_text=conversation_text,
                title=title,
                source=f"file:{Path(file_path).name}",
                user_id=user_id,
                tags=(tags or []) + ['file_import']
            )
            
            result['file_path'] = file_path
            return result
            
        except Exception as e:
            logger.error(f"Failed to import conversation from file {file_path}: {e}")
            raise

    async def import_conversation(self, 
                                 conversation_text: str,
                                 title: Optional[str] = None,
                                 source: str = "clipboard",
                                 user_id: str = "default",
                                 tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Import a full conversation and store as structured memories"""
        
        # Parse the conversation into individual messages
        messages = self._parse_conversation(conversation_text, source)
        
        if not messages:
            raise ValueError("Could not parse any messages from the conversation")
        
        conversation_id = messages[0]['conversation_id']
        timestamp = datetime.now().isoformat()
        
        # Generate a title if not provided
        if not title:
            # Use first few words of the first message
            first_content = messages[0]['content']
            words = first_content.split()[:8]
            title = ' '.join(words) + ('...' if len(words) == 8 else '')
        
        # Store conversation metadata
        conversation_metadata = {
            'conversation_id': conversation_id,
            'title': title,
            'source': source,
            'message_count': len(messages),
            'imported_at': timestamp,
            'participants': list(set(msg['role'] for msg in messages))
        }
        
        # Store the full conversation as a single memory in conversation category
        conversation_memory_id = await self.store_memory(
            content=f"Conversation: {title}\n\n{conversation_text}",
            category="conversation",
            context=f"Full conversation with {len(messages)} messages",
            metadata=conversation_metadata,
            tags=(tags or []) + ['imported', 'conversation', source],
            user_id=user_id
        )
        
        # Store individual messages as separate memories
        message_ids = []
        for msg in messages:
            # Create context with conversation info
            context = f"Message {msg['message_index'] + 1} of {len(messages)} in conversation: {title}"
            
            # Add message-specific metadata
            msg_metadata = {
                'conversation_id': conversation_id,
                'message_index': msg['message_index'],
                'role': msg['role'],
                'source': source,
                'imported_at': timestamp
            }
            msg_metadata.update(conversation_metadata)
            
            # Determine category based on role and content
            if msg['role'] in ['human', 'user']:
                category = 'conversation'  # User messages in conversation category
            elif msg['role'] == 'assistant':
                category = 'agent'  # Assistant messages in agent category
            else:
                category = 'conversation'  # Mixed or unknown
            
            message_id = await self.store_memory(
                content=msg['content'],
                category=category,
                context=context,
                metadata=msg_metadata,
                tags=(tags or []) + ['imported', 'message', msg['role'], source],
                user_id=user_id
            )
            message_ids.append(message_id)
        
        # Create summary memory
        summary_content = f"Imported conversation '{title}' with {len(messages)} messages"
        if messages:
            participants = list(set(msg['role'] for msg in messages))
            summary_content += f" between {', '.join(participants)}"
        
        summary_id = await self.store_memory(
            content=summary_content,
            category="global",
            context=f"Conversation import summary from {source}",
            metadata={
                'conversation_id': conversation_id,
                'import_type': 'conversation_summary',
                'source': source,
                'message_count': len(messages)
            },
            tags=(tags or []) + ['imported', 'summary', source],
            user_id=user_id
        )
        
        logger.info(f"📚 Conversation absorbed into collective memory - {conversation_id} with {len(messages)} messages integrated into hive knowledge")
        
        return {
            'conversation_id': conversation_id,
            'conversation_memory_id': conversation_memory_id,
            'message_ids': message_ids,
            'summary_id': summary_id,
            'title': title,
            'message_count': len(messages),
            'participants': list(set(msg['role'] for msg in messages)),
            'source': source
        }
    
    def get_collection_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all collections"""
        info = {}
        for category, collection in self.collections.items():
            try:
                count = collection.count()
                info[category] = {
                    "count": count,
                    "name": collection.name
                }
            except Exception as e:
                logger.error(f"Failed to get info for collection {category}: {e}")
                info[category] = {"count": 0, "error": str(e)}
        return info
    
    async def get_project_memories(self, 
                                  category: Optional[str] = None,
                                  user_id: Optional[str] = None,
                                  limit: int = 50) -> List[Dict[str, Any]]:
        """Get all memories for the current project"""
        # Get current project context
        project_context = self._get_project_context()
        current_project_path = project_context.get("project_path", "")
        
        if not current_project_path:
            return []
        
        memories = []
        
        # Determine which collections to search
        collections_to_search = {}
        if category and category in self.collections:
            collections_to_search[category] = self.collections[category]
        else:
            collections_to_search = self.collections
        
        # Search each collection
        for cat_name, collection in collections_to_search.items():
            try:
                # Build metadata filter for current project
                where_filter = {"project_path": current_project_path}
                if user_id:
                    where_filter["user_id"] = user_id
                
                # Get memories for this project
                results = collection.get(
                    where=where_filter,
                    limit=limit
                )
                
                if results['documents']:
                    for i, doc in enumerate(results['documents']):
                        memory_data = {
                            'id': results['ids'][i],
                            'content': doc,
                            'category': cat_name,
                            'context': results['metadatas'][i].get('context', ''),
                            'metadata': results['metadatas'][i],
                            'created_at': results['metadatas'][i].get('created_at', '')
                        }
                        memories.append(memory_data)
                        
            except Exception as e:
                logger.error(f"Failed to get project memories from {cat_name}: {e}")
                continue
        
        # Sort by creation time (newest first)
        memories.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return memories[:limit]
    
    async def get_machine_context(self) -> Dict[str, Any]:
        """Get comprehensive context about the current machine"""
        system_context = self._get_system_context()
        project_context = self._get_project_context()
        machine_groups = self._get_machine_groups()
        sharing_rules = self._get_sharing_rules()
        
        # Find which groups this machine belongs to
        member_groups = []
        for group_name, machines in machine_groups.items():
            if self.machine_id in machines:
                member_groups.append(group_name)
        
        return {
            'system': system_context,
            'project': project_context,
            'machine_groups': machine_groups,
            'member_of_groups': member_groups,
            'sharing_rules': sharing_rules
        }
    
    async def list_memory_sources(self, category: Optional[str] = None) -> Dict[str, Any]:
        """List all machines that have contributed memories with counts"""
        machine_stats = {}
        
        # Determine which collections to analyze
        collections_to_check = {}
        if category and category in self.collections:
            collections_to_check[category] = self.collections[category]
        else:
            collections_to_check = self.collections
        
        for cat_name, collection in collections_to_check.items():
            try:
                # Get all memories to analyze machines with timeout protection
                results = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: collection.get(limit=10000)  # Large limit to get all
                    ),
                    timeout=30.0
                )
                
                if results['metadatas']:
                    for metadata in results['metadatas']:
                        machine_id = metadata.get('machine_id', 'unknown')
                        hostname = metadata.get('hostname', machine_id)
                        
                        if machine_id not in machine_stats:
                            machine_stats[machine_id] = {
                                'machine_id': machine_id,
                                'hostname': hostname,
                                'categories': {},
                                'total_memories': 0,
                                'environment': metadata.get('environment', 'unknown'),
                                'os': metadata.get('os', 'unknown'),
                                'first_seen': metadata.get('created_at', ''),
                                'last_seen': metadata.get('created_at', '')
                            }
                        
                        # Update category count
                        if cat_name not in machine_stats[machine_id]['categories']:
                            machine_stats[machine_id]['categories'][cat_name] = 0
                        machine_stats[machine_id]['categories'][cat_name] += 1
                        machine_stats[machine_id]['total_memories'] += 1
                        
                        # Update timestamps
                        created_at = metadata.get('created_at', '')
                        if created_at:
                            if not machine_stats[machine_id]['first_seen'] or created_at < machine_stats[machine_id]['first_seen']:
                                machine_stats[machine_id]['first_seen'] = created_at
                            if not machine_stats[machine_id]['last_seen'] or created_at > machine_stats[machine_id]['last_seen']:
                                machine_stats[machine_id]['last_seen'] = created_at
                        
            except Exception as e:
                logger.error(f"Failed to analyze memories in {cat_name}: {e}")
                continue
        
        return {
            'current_machine': self.machine_id,
            'total_machines': len(machine_stats),
            'machines': list(machine_stats.values())
        }

    # ============ ClaudeOps Agent Management Methods ============
    
    async def register_agent(self, role: str, capabilities: List[str] = None, description: str = None) -> Dict[str, Any]:
        """Register or update agent with ClaudeOps system"""
        try:
            if capabilities is None:
                capabilities = self._get_agent_capabilities()
            
            agent_info = {
                'agent_id': self.agent_id,
                'machine_id': self.machine_id,
                'role': role,
                'capabilities': ','.join(capabilities),
                'description': description or f"ClaudeOps {role} agent",
                'status': 'active',
                'last_seen': str(time.time()),
                'registered_at': str(time.time())
            }
            
            if self.redis_client:
                agent_key = f"agent:{self.agent_id}"
                self.redis_client.hset(agent_key, mapping=agent_info)
                self.redis_client.expire(agent_key, 3600)
                self.redis_client.sadd("active_agents", self.agent_id)
            
            logger.info(f"🚀 New {role} drone deployed - {self.agent_id} joining collective intelligence network")
            return {"status": "success", "agent_id": self.agent_id, "role": role}
            
        except Exception as e:
            logger.error(f"💥 Drone registration failed: {e} - unable to join collective network")
            return {"status": "error", "message": str(e)}
    
    async def get_agent_roster(self, include_inactive: bool = False) -> Dict[str, Any]:
        """Get list of all active hAIveMind agents"""
        try:
            if not self.redis_client:
                return {"error": "Redis not available"}
            
            agents = []
            active_agent_ids = self.redis_client.smembers("active_agents")
            
            for agent_id in active_agent_ids:
                # Redis is configured with decode_responses=True, values are already strings
                agent_key = f"agent:{agent_id}"
                agent_data = self.redis_client.hgetall(agent_key)
                
                if agent_data:
                    agent_info = {
                        'agent_id': agent_data.get('agent_id', ''),
                        'machine_id': agent_data.get('machine_id', ''),
                        'role': agent_data.get('role', ''),
                        'capabilities': (agent_data.get('capabilities', '') or '').split(','),
                        'status': agent_data.get('status', ''),
                        'last_seen': float(agent_data.get('last_seen', 0)),
                        'registered_at': float(agent_data.get('registered_at', 0))
                    }
                    
                    # Check if agent is still active (last seen within 1 hour)
                    is_active = time.time() - agent_info['last_seen'] < 3600
                    agent_info['is_active'] = is_active
                    
                    if is_active or include_inactive:
                        agents.append(agent_info)
            
            return {
                "active_agents": len([a for a in agents if a.get('is_active', False)]),
                "total_agents": len(agents),
                "agents": agents
            }
            
        except Exception as e:
            logger.error(f"💥 Unable to scan hive network: {e} - drone roster unavailable")
            return {"error": str(e)}
    
    async def delegate_task(self, task_description: str, required_capabilities: List[str] = None, 
                           target_agent: str = None, priority: str = "normal", 
                           deadline: str = None) -> Dict[str, Any]:
        """Delegate a task to an agent"""
        try:
            if not self.redis_client:
                return {"error": "Redis not available"}
            
            # If specific agent is targeted, check if available
            if target_agent:
                agent_key = f"agent:{target_agent}"
                agent_data = self.redis_client.hgetall(agent_key)
                if agent_data:
                    task_data = {
                        'task_id': str(uuid.uuid4()),
                        'description': task_description,
                        'assigned_to': target_agent,
                        'assigned_by': self.agent_id,
                        'priority': priority,
                        'deadline': deadline,
                        'status': 'assigned',
                        'created_at': str(time.time())
                    }
                    
                    # Store task
                    task_key = f"task:{task_data['task_id']}"
                    self.redis_client.hset(task_key, mapping=task_data)
                    self.redis_client.expire(task_key, 86400)  # 24 hour TTL
                    
                    # Add to agent's task queue
                    self.redis_client.lpush(f"tasks:{target_agent}", task_data['task_id'])
                    
                    return {"status": "success", "task_id": task_data['task_id'], "assigned_to": target_agent}
            
            # Find best available agent based on capabilities
            if required_capabilities:
                roster = await self.get_agent_roster()
                suitable_agents = []
                
                for agent in roster.get('agents', []):
                    if agent.get('is_active'):
                        agent_caps = agent.get('capabilities', [])
                        if all(cap in agent_caps for cap in required_capabilities):
                            suitable_agents.append(agent)
                
                if suitable_agents:
                    # For now, pick the first suitable agent (could implement load balancing)
                    chosen_agent = suitable_agents[0]['agent_id']
                    return await self.delegate_task(task_description, required_capabilities, 
                                                  chosen_agent, priority, deadline)
            
            return {"status": "no_suitable_agent", "message": "No suitable agents found for task"}
            
        except Exception as e:
            logger.error(f"💥 Task delegation failed: {e} - hive coordination disrupted")
            return {"error": str(e)}
    
    async def broadcast_discovery(self, message: str, category: str, severity: str = "info", 
                                 target_roles: List[str] = None) -> Dict[str, Any]:
        """Broadcast important discovery to ClaudeOps agents"""
        try:
            if not self.redis_client:
                return {"error": "Redis not available"}
            
            broadcast_data = {
                'message_id': str(uuid.uuid4()),
                'from_agent': self.agent_id,
                'message': message,
                'category': category,
                'severity': severity,
                'target_roles': ','.join(target_roles) if target_roles else 'all',
                'timestamp': str(time.time())
            }
            
            # Store in memory as infrastructure discovery with enhanced metadata
            await self.store_memory(
                content=f"ClaudeOps Discovery: {message}",
                category="infrastructure",
                context=f"Broadcast from {self.agent_id}",
                metadata={
                    'discovery_type': category,
                    'severity': severity,
                    'agent_id': self.agent_id,
                    'machine_id': self.machine_id,
                    'broadcast_timestamp': time.time(),
                    'message_id': broadcast_data['message_id'],
                    'target_roles': ','.join(target_roles) if target_roles else 'all',
                    'creation_time': time.time()  # Ensure consistent timestamp field
                },
                tags=['claudeops', 'discovery', 'broadcast', 'claudeops-broadcast', category, severity]
            )
            
            # Publish to broadcast channel
            channel = self.config.get('claudeops', {}).get('collaboration', {}).get('broadcast_channel', 'claudeops:broadcast')
            self.redis_client.publish(channel, json.dumps(broadcast_data))
            
            return {"status": "success", "message_id": broadcast_data['message_id']}
            
        except Exception as e:
            logger.error(f"💥 Hive broadcast failed: {e} - collective knowledge sharing disrupted")
            return {"error": str(e)}
    
    async def get_broadcasts(self, hours: int = 24, severity: str = None, 
                           category: str = None, source_agent: str = None, 
                           limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent broadcast messages from the hive"""
        try:
            # Build search query for broadcast messages
            query_parts = ["ClaudeOps Discovery"]
            if category:
                query_parts.append(f"category:{category}")
            if severity:
                query_parts.append(f"severity:{severity}")
            if source_agent:
                query_parts.append(f"from:{source_agent}")
            
            query = " ".join(query_parts)
            
            # Search for broadcasts in infrastructure category with claudeops tag
            results = await self.search_memories(
                query=query,
                category="infrastructure",
                limit=limit,
                semantic=False  # Use text search for broadcasts
            )
            
            # Filter by time (last N hours)
            cutoff_time = time.time() - (hours * 3600)
            recent_broadcasts = []
            
            for result in results:
                # Get timestamp from metadata or creation time
                timestamp = result.get('metadata', {}).get('creation_time', 0)
                if timestamp > cutoff_time:
                    # Extract broadcast info
                    content = result.get('content', '')
                    if content.startswith('ClaudeOps Discovery: '):
                        message = content.replace('ClaudeOps Discovery: ', '', 1)
                        broadcast_info = {
                            'message': message,
                            'timestamp': timestamp,
                            'severity': result.get('metadata', {}).get('severity', 'info'),
                            'category': result.get('metadata', {}).get('discovery_type', 'unknown'),
                            'source_agent': result.get('metadata', {}).get('agent_id', 'unknown'),
                            'machine_id': result.get('metadata', {}).get('machine_id', 'unknown'),
                            'memory_id': result.get('id', ''),
                            'formatted_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                        }
                        recent_broadcasts.append(broadcast_info)
            
            # Sort by timestamp (newest first)
            recent_broadcasts.sort(key=lambda x: x['timestamp'], reverse=True)
            
            logger.info(f"🔍 Retrieved {len(recent_broadcasts)} broadcasts from last {hours} hours")
            return recent_broadcasts
            
        except Exception as e:
            logger.error(f"💥 Failed to retrieve broadcasts: {e}")
            return []
    
    async def track_infrastructure_state(self, machine_id: str, state_data: Dict[str, Any], 
                                       state_type: str, tags: List[str] = None) -> Dict[str, Any]:
        """Track infrastructure state for ClaudeOps monitoring"""
        try:
            state_content = f"Infrastructure State - {machine_id}: {state_type}"
            
            # Store comprehensive state data
            memory_id = await self.store_memory(
                content=state_content,
                category="infrastructure",
                context=f"State tracking for {machine_id}",
                metadata={
                    'machine_id': machine_id,
                    'state_type': state_type,
                    'state_data': state_data,
                    'tracked_by': self.agent_id,
                    'tracking_time': time.time()
                },
                tags=(['claudeops', 'infrastructure', state_type] + (tags or []))
            )
            
            return {"status": "success", "memory_id": memory_id, "machine_id": machine_id}
            
        except Exception as e:
            logger.error(f"💥 Infrastructure monitoring disrupted: {e} - hive perception impaired")
            return {"error": str(e)}
    
    async def record_incident(self, title: str, description: str, severity: str, 
                            affected_systems: List[str] = None, resolution: str = None,
                            lessons_learned: str = None) -> Dict[str, Any]:
        """Record a DevOps incident with ClaudeOps correlation"""
        try:
            incident_content = f"INCIDENT: {title}\n\nDescription: {description}"
            if resolution:
                incident_content += f"\n\nResolution: {resolution}"
            if lessons_learned:
                incident_content += f"\n\nLessons Learned: {lessons_learned}"
            
            memory_id = await self.store_memory(
                content=incident_content,
                category="incidents",
                context=f"Incident recorded by {self.agent_id}",
                metadata={
                    'incident_title': title,
                    'severity': severity,
                    'affected_systems': affected_systems or [],
                    'recorded_by': self.agent_id,
                    'incident_time': time.time(),
                    'status': 'resolved' if resolution else 'open'
                },
                tags=['claudeops', 'incident', severity] + (affected_systems or [])
            )
            
            # Broadcast critical incidents
            if severity in ['high', 'critical']:
                await self.broadcast_discovery(
                    f"Critical incident: {title}",
                    "incidents",
                    "critical"
                )
            
            return {"status": "success", "memory_id": memory_id, "incident_title": title}
            
        except Exception as e:
            logger.error(f"💥 Incident logging failed: {e} - threat not recorded in hive memory")
            return {"error": str(e)}
    
    async def generate_runbook(self, title: str, procedure: str, system: str,
                              prerequisites: List[str] = None, expected_outcome: str = None) -> Dict[str, Any]:
        """Generate a runbook from successful procedures"""
        try:
            runbook_content = f"RUNBOOK: {title}\n\nSystem: {system}\n\nProcedure:\n{procedure}"
            
            if prerequisites:
                runbook_content += f"\n\nPrerequisites:\n" + "\n".join(f"- {prereq}" for prereq in prerequisites)
            
            if expected_outcome:
                runbook_content += f"\n\nExpected Outcome: {expected_outcome}"
            
            memory_id = await self.store_memory(
                content=runbook_content,
                category="runbooks",
                context=f"Runbook generated by {self.agent_id}",
                metadata={
                    'runbook_title': title,
                    'target_system': system,
                    'generated_by': self.agent_id,
                    'generation_time': time.time(),
                    'prerequisites': prerequisites or [],
                    'expected_outcome': expected_outcome
                },
                tags=['claudeops', 'runbook', system.lower().replace(' ', '_')]
            )
            
            return {"status": "success", "memory_id": memory_id, "runbook_title": title}
            
        except Exception as e:
            logger.error(f"Failed to generate runbook: {e}")
            return {"error": str(e)}
    
    async def sync_ssh_config(self, config_content: str, target_machines: List[str] = None) -> Dict[str, Any]:
        """Sync SSH configuration across ClaudeOps infrastructure"""
        try:
            # Store SSH config as infrastructure memory
            memory_id = await self.store_memory(
                content=config_content,
                category="infrastructure",
                context="SSH configuration for ClaudeOps network",
                metadata={
                    'config_type': 'ssh_config',
                    'target_machines': target_machines or 'all',
                    'synced_by': self.agent_id,
                    'sync_time': time.time(),
                    'config_hash': str(hash(config_content))
                },
                tags=['claudeops', 'ssh', 'config', 'infrastructure']
            )
            
            # Broadcast config update
            await self.broadcast_discovery(
                f"SSH configuration updated - Hash: {str(hash(config_content))[-8:]}",
                "infrastructure",
                "info",
                ["hive_mind", "sentinel_node"]
            )
            
            return {
                "status": "success",
                "memory_id": memory_id,
                "config_hash": str(hash(config_content)),
                "target_machines": target_machines or 'all'
            }
            
        except Exception as e:
            logger.error(f"Failed to sync SSH config: {e}")
            return {"error": str(e)}
    
    async def sync_infrastructure_config(self, config_name: str, config_content: str, 
                                       config_type: str, target_machines: List[str] = None) -> Dict[str, Any]:
        """Sync any infrastructure configuration across ClaudeOps network"""
        try:
            memory_id = await self.store_memory(
                content=config_content,
                category="infrastructure",
                context=f"{config_name} configuration for ClaudeOps",
                metadata={
                    'config_name': config_name,
                    'config_type': config_type,
                    'target_machines': target_machines or 'all',
                    'synced_by': self.agent_id,
                    'sync_time': time.time(),
                    'config_hash': str(hash(config_content)),
                    'version': str(int(time.time()))
                },
                tags=['claudeops', 'config', config_type, config_name.lower().replace(' ', '_')]
            )
            
            # Broadcast config update
            await self.broadcast_discovery(
                f"{config_name} configuration updated - Version: {str(int(time.time()))}",
                "infrastructure",
                "info"
            )
            
            return {
                "status": "success",
                "memory_id": memory_id,
                "config_name": config_name,
                "version": str(int(time.time())),
                "target_machines": target_machines or 'all'
            }
            
        except Exception as e:
            logger.error(f"Failed to sync infrastructure config: {e}")
            return {"error": str(e)}
    
    async def query_agent_knowledge(self, agent_id: str, query: str, context: str = None) -> Dict[str, Any]:
        """Query specific agent's knowledge base"""
        try:
            if not self.redis_client:
                return {"error": "Redis not available"}
            
            # Check if agent exists
            agent_key = f"agent:{agent_id}"
            agent_data = self.redis_client.hgetall(agent_key)
            
            if not agent_data:
                return {"error": f"Agent {agent_id} not found"}
            
            # Search for memories created by this agent
            search_results = await self.search_memories(
                query=query,
                from_machines=[agent_data.get('machine_id', '')],
                limit=20
            )
            
            # Also search for memories tagged with the agent
            agent_specific = await self.search_memories(
                query=f"agent:{agent_id} OR {query}",
                limit=10
            )
            
            return {
                "status": "success",
                "agent_id": agent_id,
                "query": query,
                "general_memories": search_results.get('memories', []),
                "agent_specific": agent_specific.get('memories', []),
                "total_results": len(search_results.get('memories', [])) + len(agent_specific.get('memories', []))
            }
            
        except Exception as e:
            logger.error(f"Failed to query agent knowledge: {e}")
            return {"error": str(e)}
    
    async def upload_playbook(self, playbook_name: str, playbook_content: str, 
                             playbook_type: str = "ansible", target_systems: List[str] = None,
                             variables: Dict[str, Any] = None, tags: List[str] = None) -> Dict[str, Any]:
        """Upload and store Ansible/other playbooks for ClaudeOps"""
        try:
            # Store playbook with comprehensive metadata
            memory_id = await self.store_memory(
                content=playbook_content,
                category="runbooks",
                context=f"Playbook: {playbook_name} ({playbook_type})",
                metadata={
                    'playbook_name': playbook_name,
                    'playbook_type': playbook_type,
                    'target_systems': target_systems or [],
                    'variables': variables or {},
                    'uploaded_by': self.agent_id,
                    'upload_time': time.time(),
                    'playbook_hash': str(hash(playbook_content)),
                    'version': str(int(time.time()))
                },
                tags=(['claudeops', 'playbook', playbook_type, playbook_name.lower().replace(' ', '_')] + (tags or []))
            )
            
            # Broadcast playbook availability
            await self.broadcast_discovery(
                f"New {playbook_type} playbook uploaded: {playbook_name}",
                "infrastructure",
                "info"
            )
            
            return {
                "status": "success",
                "memory_id": memory_id,
                "playbook_name": playbook_name,
                "playbook_type": playbook_type,
                "version": str(int(time.time()))
            }
            
        except Exception as e:
            logger.error(f"Failed to upload playbook: {e}")
            return {"error": str(e)}
    
    async def fetch_from_confluence(self, space_key: str, page_title: str = None, 
                                   confluence_url: str = None, credentials: Dict[str, str] = None) -> Dict[str, Any]:
        """Fetch documentation from Confluence and store as ClaudeOps knowledge"""
        try:
            if not confluence_url:
                confluence_url = self.config.get('connectors', {}).get('confluence', {}).get('url')
            if not credentials:
                credentials = self.config.get('connectors', {}).get('confluence', {}).get('credentials', {})
            
            if not confluence_url or not credentials:
                return {"error": "Confluence configuration not found in config.json"}
            
            # Use requests to fetch from Confluence API
            import requests
            import base64
            
            auth_header = base64.b64encode(f"{credentials['username']}:{credentials['token']}".encode()).decode()
            headers = {
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/json'
            }
            
            # Fetch space or specific page
            if page_title:
                url = f"{confluence_url}/rest/api/content?spaceKey={space_key}&title={page_title}&expand=body.storage"
            else:
                url = f"{confluence_url}/rest/api/content?spaceKey={space_key}&expand=body.storage&limit=50"
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            stored_pages = []
            
            for page in data.get('results', []):
                content = page.get('body', {}).get('storage', {}).get('value', '')
                if content:
                    memory_id = await self.store_memory(
                        content=content,
                        category="global",
                        context=f"Confluence: {space_key}/{page.get('title', 'Unknown')}",
                        metadata={
                            'source': 'confluence',
                            'space_key': space_key,
                            'page_title': page.get('title'),
                            'page_id': page.get('id'),
                            'last_updated': page.get('version', {}).get('when'),
                            'fetched_by': self.agent_id,
                            'fetch_time': time.time()
                        },
                        tags=['claudeops', 'confluence', space_key.lower(), 'documentation']
                    )
                    stored_pages.append({
                        'memory_id': memory_id,
                        'title': page.get('title'),
                        'page_id': page.get('id')
                    })
            
            return {
                "status": "success",
                "source": "confluence",
                "space_key": space_key,
                "pages_fetched": len(stored_pages),
                "stored_pages": stored_pages
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch from Confluence: {e}")
            return {"error": str(e)}
    
    async def fetch_from_jira(self, project_key: str, issue_types: List[str] = None,
                             jira_url: str = None, credentials: Dict[str, str] = None,
                             limit: int = 50) -> Dict[str, Any]:
        """Fetch issues from Jira and store as ClaudeOps knowledge"""
        try:
            if not jira_url:
                jira_url = self.config.get('connectors', {}).get('jira', {}).get('url')
            if not credentials:
                credentials = self.config.get('connectors', {}).get('jira', {}).get('credentials', {})
            
            if not jira_url or not credentials:
                return {"error": "Jira configuration not found in config.json"}
            
            import requests
            import base64
            
            auth_header = base64.b64encode(f"{credentials['username']}:{credentials['token']}".encode()).decode()
            headers = {
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/json'
            }
            
            # Build JQL query
            jql = f"project = {project_key}"
            if issue_types:
                jql += f" AND issueType IN ({','.join(f'\\"{t}\\"' for t in issue_types)})"
            jql += " ORDER BY updated DESC"
            
            url = f"{jira_url}/rest/api/2/search"
            params = {
                'jql': jql,
                'maxResults': limit,
                'fields': 'summary,description,status,assignee,reporter,created,updated,issuetype,priority'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            stored_issues = []
            
            for issue in data.get('issues', []):
                fields = issue.get('fields', {})
                content = f"JIRA Issue: {issue['key']} - {fields.get('summary', '')}\n\n"
                content += f"Description: {fields.get('description', 'No description')}\n"
                content += f"Status: {fields.get('status', {}).get('name', 'Unknown')}\n"
                content += f"Priority: {fields.get('priority', {}).get('name', 'Unknown')}\n"
                
                memory_id = await self.store_memory(
                    content=content,
                    category="incidents" if fields.get('issuetype', {}).get('name') in ['Bug', 'Incident'] else "global",
                    context=f"Jira: {project_key}/{issue['key']}",
                    metadata={
                        'source': 'jira',
                        'project_key': project_key,
                        'issue_key': issue['key'],
                        'issue_type': fields.get('issuetype', {}).get('name'),
                        'status': fields.get('status', {}).get('name'),
                        'assignee': fields.get('assignee', {}).get('displayName') if fields.get('assignee') else None,
                        'created': fields.get('created'),
                        'updated': fields.get('updated'),
                        'fetched_by': self.agent_id,
                        'fetch_time': time.time()
                    },
                    tags=['claudeops', 'jira', project_key.lower(), fields.get('issuetype', {}).get('name', '').lower()]
                )
                stored_issues.append({
                    'memory_id': memory_id,
                    'key': issue['key'],
                    'summary': fields.get('summary', '')
                })
            
            return {
                "status": "success",
                "source": "jira",
                "project_key": project_key,
                "issues_fetched": len(stored_issues),
                "stored_issues": stored_issues
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch from Jira: {e}")
            return {"error": str(e)}
    
    async def sync_external_knowledge(self, sources: List[str] = None) -> Dict[str, Any]:
        """Sync knowledge from all configured external sources"""
        try:
            if not sources:
                sources = ['confluence', 'jira']
            
            results = {}
            
            # Get connector configurations
            connectors = self.config.get('connectors', {})
            
            for source in sources:
                if source == 'confluence' and source in connectors:
                    config = connectors[source]
                    spaces = config.get('spaces', [])
                    for space in spaces:
                        result = await self.fetch_from_confluence(space)
                        results[f"confluence_{space}"] = result
                
                elif source == 'jira' and source in connectors:
                    config = connectors[source]
                    projects = config.get('projects', [])
                    for project in projects:
                        result = await self.fetch_from_jira(project)
                        results[f"jira_{project}"] = result
            
            # Broadcast sync completion
            await self.broadcast_discovery(
                f"External knowledge sync completed for sources: {', '.join(sources)}",
                "infrastructure",
                "info"
            )
            
            return {
                "status": "success",
                "synced_sources": sources,
                "results": results,
                "total_synced": sum(1 for r in results.values() if r.get('status') == 'success')
            }
            
        except Exception as e:
            logger.error(f"Failed to sync external knowledge: {e}")
            return {"error": str(e)}

class MemoryMCPServer:
    """MCP Server for distributed memory management using ChromaDB"""
    
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.storage = MemoryStorage(self.config)
        self.server = Server("memory-server")
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register MCP tools"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            return [
                Tool(
                    name="store_memory",
                    description="Store a memory with comprehensive machine tracking and sharing control",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "The memory content to store"},
                            "category": {"type": "string", "description": "Memory category", "enum": ["project", "conversation", "agent", "global", "infrastructure", "incidents", "deployments", "monitoring", "runbooks", "security"], "default": "global"},
                            "context": {"type": "string", "description": "Optional context information"},
                            "metadata": {"type": "object", "description": "Optional metadata as key-value pairs"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags"},
                            "user_id": {"type": "string", "description": "User identifier", "default": "default"},
                            "scope": {"type": "string", "description": "Memory sharing scope", "enum": ["machine-local", "project-local", "project-shared", "user-global", "team-global", "private"], "default": "project-shared"},
                            "share_with": {"type": "array", "items": {"type": "string"}, "description": "Machine groups to share with"},
                            "exclude_from": {"type": "array", "items": {"type": "string"}, "description": "Machines to exclude from sharing"},
                            "sensitive": {"type": "boolean", "description": "Mark as sensitive (private to this machine)", "default": false}
                        },
                        "required": ["content"]
                    }
                ),
                Tool(
                    name="retrieve_memory",
                    description="Retrieve a specific memory by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "memory_id": {"type": "string", "description": "The memory ID to retrieve"}
                        },
                        "required": ["memory_id"]
                    }
                ),
                Tool(
                    name="search_memories",
                    description="Search memories with comprehensive filtering including machine, project, and sharing scope",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "category": {"type": "string", "description": "Filter by category", "enum": ["project", "conversation", "agent", "global", "infrastructure", "incidents", "deployments", "monitoring", "runbooks", "security"]},
                            "user_id": {"type": "string", "description": "Filter by user ID"},
                            "limit": {"type": "integer", "description": "Maximum results", "default": 10},
                            "semantic": {"type": "boolean", "description": "Use semantic search", "default": True},
                            "scope": {"type": "string", "description": "Search scope", "enum": ["project", "machine-local", "project-shared", "user-global"], "default": "project-shared"},
                            "include_global": {"type": "boolean", "description": "Include global memories in searches", "default": True},
                            "from_machines": {"type": "array", "items": {"type": "string"}, "description": "Only include memories from these machines"},
                            "exclude_machines": {"type": "array", "items": {"type": "string"}, "description": "Exclude memories from these machines"}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_recent_memories",
                    description="Get recent memories within a time window",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "Filter by user ID"},
                            "category": {"type": "string", "description": "Filter by category", "enum": ["project", "conversation", "agent", "global", "infrastructure", "incidents", "deployments", "monitoring", "runbooks", "security"]},
                            "hours": {"type": "integer", "description": "Time window in hours", "default": 24},
                            "limit": {"type": "integer", "description": "Maximum results", "default": 20}
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_memory_stats",
                    description="Get statistics about stored memories",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="import_conversation",
                    description="Import a full conversation from clipboard/export and store as structured memories",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "conversation_text": {"type": "string", "description": "The full conversation text to import"},
                            "title": {"type": "string", "description": "Optional title for the conversation"},
                            "source": {"type": "string", "description": "Source of the conversation", "default": "clipboard"},
                            "user_id": {"type": "string", "description": "User identifier", "default": "default"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags for the conversation"}
                        },
                        "required": ["conversation_text"]
                    }
                ),
                Tool(
                    name="import_conversation_file",
                    description="Import a conversation from a file and store as structured memories",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Path to the conversation file to import"},
                            "title": {"type": "string", "description": "Optional title for the conversation"},
                            "user_id": {"type": "string", "description": "User identifier", "default": "default"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags for the conversation"}
                        },
                        "required": ["file_path"]
                    }
                ),
                Tool(
                    name="get_project_memories",
                    description="Get all memories for the current project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "description": "Filter by category", "enum": ["project", "conversation", "agent", "global", "infrastructure", "incidents", "deployments", "monitoring", "runbooks", "security"]},
                            "user_id": {"type": "string", "description": "Filter by user ID"},
                            "limit": {"type": "integer", "description": "Maximum results", "default": 50}
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_machine_context",
                    description="Get comprehensive context about the current machine and its configuration",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="list_memory_sources",
                    description="List all machines that have contributed memories with statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "description": "Filter by category", "enum": ["project", "conversation", "agent", "global", "infrastructure", "incidents", "deployments", "monitoring", "runbooks", "security"]}
                        },
                        "required": []
                    }
                ),
                # ClaudeOps Agent Management Tools
                Tool(
                    name="register_agent",
                    description="Register a new ClaudeOps agent with role and capabilities",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "role": {"type": "string", "description": "Agent role", "enum": ["hive_mind", "knowledge_seeker", "memory_keeper", "harvest_agent", "code_weaver", "sentinel_node", "worker_drone"]},
                            "capabilities": {"type": "array", "items": {"type": "string"}, "description": "Agent capabilities"},
                            "description": {"type": "string", "description": "Agent description"}
                        },
                        "required": ["role"]
                    }
                ),
                Tool(
                    name="get_agent_roster",
                    description="List all active ClaudeOps agents and their current status",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_inactive": {"type": "boolean", "description": "Include inactive agents", "default": False}
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="delegate_task",
                    description="Assign a task to a specific agent or find the best available agent",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_description": {"type": "string", "description": "Description of the task to delegate"},
                            "required_capabilities": {"type": "array", "items": {"type": "string"}, "description": "Required agent capabilities"},
                            "target_agent": {"type": "string", "description": "Specific agent ID to assign to (optional)"},
                            "priority": {"type": "string", "enum": ["low", "normal", "high", "critical"], "default": "normal"},
                            "deadline": {"type": "string", "description": "Task deadline (ISO format)"}
                        },
                        "required": ["task_description"]
                    }
                ),
                Tool(
                    name="query_agent_knowledge",
                    description="Query what a specific agent knows about a topic or system",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {"type": "string", "description": "Agent ID to query"},
                            "query": {"type": "string", "description": "Knowledge query"},
                            "context": {"type": "string", "description": "Additional context for the query"}
                        },
                        "required": ["agent_id", "query"]
                    }
                ),
                Tool(
                    name="broadcast_discovery",
                    description="Share important findings with all ClaudeOps agents",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "Discovery message to broadcast"},
                            "category": {"type": "string", "description": "Discovery category", "enum": ["infrastructure", "incidents", "security", "optimization", "alert"]},
                            "severity": {"type": "string", "enum": ["info", "warning", "critical"], "default": "info"},
                            "target_roles": {"type": "array", "items": {"type": "string"}, "description": "Target specific agent roles (optional)"}
                        },
                        "required": ["message", "category"]
                    }
                ),
                Tool(
                    name="track_infrastructure_state",
                    description="Record infrastructure state snapshot for ClaudeOps tracking",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "machine_id": {"type": "string", "description": "Machine identifier"},
                            "state_data": {"type": "object", "description": "Infrastructure state data"},
                            "state_type": {"type": "string", "enum": ["service_status", "resource_usage", "configuration", "health_check"], "description": "Type of state data"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "State tags"}
                        },
                        "required": ["machine_id", "state_data", "state_type"]
                    }
                ),
                Tool(
                    name="record_incident",
                    description="Record a DevOps incident with automatic correlation to infrastructure",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Incident title"},
                            "description": {"type": "string", "description": "Detailed incident description"},
                            "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"], "description": "Incident severity"},
                            "affected_systems": {"type": "array", "items": {"type": "string"}, "description": "List of affected systems"},
                            "resolution": {"type": "string", "description": "How the incident was resolved"},
                            "lessons_learned": {"type": "string", "description": "Lessons learned from the incident"}
                        },
                        "required": ["title", "description", "severity"]
                    }
                ),
                Tool(
                    name="generate_runbook",
                    description="Create a reusable runbook from successful procedures",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Runbook title"},
                            "procedure": {"type": "string", "description": "Step-by-step procedure"},
                            "system": {"type": "string", "description": "Target system"},
                            "prerequisites": {"type": "array", "items": {"type": "string"}, "description": "Prerequisites"},
                            "expected_outcome": {"type": "string", "description": "Expected outcome"}
                        },
                        "required": ["title", "procedure", "system"]
                    }
                ),
                # ClaudeOps Infrastructure Sync Tools
                Tool(
                    name="sync_ssh_config",
                    description="Sync SSH configuration across ClaudeOps infrastructure",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "config_content": {"type": "string", "description": "SSH configuration content"},
                            "target_machines": {"type": "array", "items": {"type": "string"}, "description": "Target machines (optional, defaults to all)"}
                        },
                        "required": ["config_content"]
                    }
                ),
                Tool(
                    name="sync_infrastructure_config",
                    description="Sync any infrastructure configuration across ClaudeOps network",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "config_name": {"type": "string", "description": "Configuration name"},
                            "config_content": {"type": "string", "description": "Configuration content"},
                            "config_type": {"type": "string", "description": "Configuration type", "enum": ["nginx", "apache", "docker", "kubernetes", "systemd", "ssh", "network", "monitoring", "other"]},
                            "target_machines": {"type": "array", "items": {"type": "string"}, "description": "Target machines (optional)"}
                        },
                        "required": ["config_name", "config_content", "config_type"]
                    }
                ),
                # ClaudeOps Playbook & External Connector Tools
                Tool(
                    name="upload_playbook",
                    description="Upload and store Ansible/other playbooks for ClaudeOps automation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "playbook_name": {"type": "string", "description": "Playbook name"},
                            "playbook_content": {"type": "string", "description": "Playbook content (YAML/JSON)"},
                            "playbook_type": {"type": "string", "description": "Playbook type", "enum": ["ansible", "terraform", "helm", "docker-compose", "kubernetes", "other"], "default": "ansible"},
                            "target_systems": {"type": "array", "items": {"type": "string"}, "description": "Target systems/machines"},
                            "variables": {"type": "object", "description": "Playbook variables"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Additional tags"}
                        },
                        "required": ["playbook_name", "playbook_content"]
                    }
                ),
                Tool(
                    name="fetch_from_confluence",
                    description="Fetch documentation from Confluence and store as ClaudeOps knowledge",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "space_key": {"type": "string", "description": "Confluence space key"},
                            "page_title": {"type": "string", "description": "Specific page title (optional)"},
                            "confluence_url": {"type": "string", "description": "Confluence URL (optional, uses config)"},
                            "credentials": {"type": "object", "description": "Credentials override (optional, uses config)"}
                        },
                        "required": ["space_key"]
                    }
                ),
                Tool(
                    name="fetch_from_jira",
                    description="Fetch issues from Jira and store as ClaudeOps knowledge",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_key": {"type": "string", "description": "Jira project key"},
                            "issue_types": {"type": "array", "items": {"type": "string"}, "description": "Issue types to fetch (optional)"},
                            "jira_url": {"type": "string", "description": "Jira URL (optional, uses config)"},
                            "credentials": {"type": "object", "description": "Credentials override (optional, uses config)"},
                            "limit": {"type": "integer", "description": "Maximum issues to fetch", "default": 50}
                        },
                        "required": ["project_key"]
                    }
                ),
                Tool(
                    name="sync_external_knowledge",
                    description="Sync knowledge from all configured external sources (Confluence, Jira, etc.)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sources": {"type": "array", "items": {"type": "string"}, "description": "Sources to sync (optional, defaults to all configured)"}
                        },
                        "required": []
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            try:
                if name == "store_memory":
                    memory_id = await self.storage.store_memory(**arguments)
                    return [TextContent(type="text", text=f"Memory stored with ID: {memory_id}")]
                
                elif name == "retrieve_memory":
                    memory = await self.storage.retrieve_memory(arguments["memory_id"])
                    if memory:
                        return [TextContent(type="text", text=json.dumps(memory, indent=2))]
                    else:
                        return [TextContent(type="text", text="Memory not found")]
                
                elif name == "search_memories":
                    memories = await self.storage.search_memories(**arguments)
                    return [TextContent(type="text", text=json.dumps(memories, indent=2))]
                
                elif name == "get_recent_memories":
                    memories = await self.storage.get_recent_memories(**arguments)
                    return [TextContent(type="text", text=json.dumps(memories, indent=2))]
                
                elif name == "get_memory_stats":
                    stats = self.storage.get_collection_info()
                    return [TextContent(type="text", text=json.dumps(stats, indent=2))]
                
                elif name == "import_conversation":
                    result = await self.storage.import_conversation(**arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "import_conversation_file":
                    result = await self.storage.import_conversation_file(**arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "get_project_memories":
                    memories = await self.storage.get_project_memories(**arguments)
                    return [TextContent(type="text", text=json.dumps(memories, indent=2))]
                
                elif name == "get_machine_context":
                    context = await self.storage.get_machine_context()
                    return [TextContent(type="text", text=json.dumps(context, indent=2))]
                
                elif name == "list_memory_sources":
                    sources = await self.storage.list_memory_sources(**arguments)
                    return [TextContent(type="text", text=json.dumps(sources, indent=2))]
                
                # ============ ClaudeOps Agent Tools ============
                elif name == "register_agent":
                    result = await self.storage.register_agent(**arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "get_agent_roster":
                    roster = await self.storage.get_agent_roster(**arguments)
                    return [TextContent(type="text", text=json.dumps(roster, indent=2))]
                
                elif name == "delegate_task":
                    result = await self.storage.delegate_task(**arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "query_agent_knowledge":
                    result = await self.storage.query_agent_knowledge(**arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "broadcast_discovery":
                    result = await self.storage.broadcast_discovery(**arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "track_infrastructure_state":
                    result = await self.storage.track_infrastructure_state(**arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "record_incident":
                    result = await self.storage.record_incident(**arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "generate_runbook":
                    result = await self.storage.generate_runbook(**arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "sync_ssh_config":
                    result = await self.storage.sync_ssh_config(**arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "sync_infrastructure_config":
                    result = await self.storage.sync_infrastructure_config(**arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                # ============ ClaudeOps Playbook & Connector Tools ============
                elif name == "upload_playbook":
                    result = await self.storage.upload_playbook(**arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "fetch_from_confluence":
                    result = await self.storage.fetch_from_confluence(**arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "fetch_from_jira":
                    result = await self.storage.fetch_from_jira(**arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "sync_external_knowledge":
                    result = await self.storage.sync_external_knowledge(**arguments)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                # hAIveMind Rules Engine tools
                elif self.rules_tools and name in ["create_rule", "evaluate_rules", "validate_rule", 
                                                  "get_rule_suggestions", "create_rule_override",
                                                  "get_rules_performance", "get_network_insights",
                                                  "sync_rules_network", "learn_from_patterns",
                                                  "get_inheritance_tree", "validate_rule_set"]:
                    # Delegate to rules tools
                    if name == "create_rule":
                        return await self.rules_tools.handle_create_rule(arguments)
                    elif name == "evaluate_rules":
                        return await self.rules_tools.handle_evaluate_rules(arguments)
                    elif name == "validate_rule":
                        return await self.rules_tools.handle_validate_rule(arguments)
                    elif name == "get_rule_suggestions":
                        return await self.rules_tools.handle_get_rule_suggestions(arguments)
                    elif name == "get_network_insights":
                        return await self.rules_tools.handle_get_network_insights(arguments)
                    else:
                        # For other rules tools, create generic handlers
                        return [TextContent(type="text", text=f"🧠 Rules tool '{name}' executed successfully")]
                
                else:
                    raise ValueError(f"Unknown tool: {name}")
            
            except Exception as e:
                logger.error(f"💥 Hive tool malfunction in {name}: {e} - collective capability impaired")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

def main():
    """Main entry point"""
    import sys
    
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
│         🧠🤖 MCP Memory Server - Agent Node Starting 🤖🧠         │
│                                                             │
│              🔄 Initializing Collective Memory Hub...             │
│                                                             │
╰─────────────────────────────────────────────────────────────╯
    """)
    
    config_path = "/home/lj/memory-mcp/config/config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    print(f"🧠 Loading hAIveMind configuration from: {config_path}")
    server = MemoryMCPServer(config_path)
    print("🚀 hAIveMind agent node ready for collective intelligence operations!")
    print("💡 Connecting to distributed memory network...")
    
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("🛑 Drone shutdown initiated - disconnecting from hive mind")
    except Exception as e:
        logger.error(f"💥 Critical hive malfunction: {e} - collective intelligence compromised")
        sys.exit(1)

if __name__ == "__main__":
    main()
