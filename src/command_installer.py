#!/usr/bin/env python3
"""
hAIveMind Command Installer - Manages sync of commands and configurations across Claude agents
Handles installation, updates, and synchronization of hv-* commands and CLAUDE.md configs
"""

import asyncio
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class CommandInstaller:
    """Manages installation and sync of hAIveMind commands across agents"""

    # Cross-tool path mappings for different AI coding assistants
    TOOL_PATHS = {
        "claude": ".claude/commands",
        "cursor": ".cursor/commands",
        "kilo": ".kilo/commands",
        "cline": ".cline/commands",
        "codex": ".codex/commands",
    }

    # Skill directory paths
    SKILL_PATHS = {
        "claude": ".claude/skills",
        "cursor": ".cursor/skills",
        "kilo": ".kilo/skills",
        "cline": ".cline/skills",
        "codex": ".codex/skills",
    }

    def __init__(self, storage, config: Dict[str, Any]):
        self.storage = storage
        self.config = config
        self.commands_dir = Path(__file__).parent.parent / "commands"
        self.version = "2.0.0"  # Upgraded for cross-tool sync

    async def detect_claude_paths(self) -> Dict[str, str]:
        """Detect available Claude command installation paths"""
        paths = {}

        # Project-level commands
        project_path = Path(".claude/commands")
        if project_path.exists() or Path(".claude").exists():
            paths["project"] = str(project_path.absolute())

        # Personal commands
        home = Path.home()
        personal_path = home / ".claude" / "commands"
        if personal_path.exists() or (home / ".claude").exists():
            paths["personal"] = str(personal_path)

        return paths

    async def detect_all_tool_paths(self) -> Dict[str, Dict[str, str]]:
        """Detect command/skill paths for all supported AI tools"""
        home = Path.home()
        detected = {}

        for tool_name, rel_path in self.TOOL_PATHS.items():
            tool_path = home / rel_path
            skill_rel_path = self.SKILL_PATHS.get(tool_name, "")
            skill_path = home / skill_rel_path if skill_rel_path else None

            tool_info = {
                "commands_path": str(tool_path),
                "commands_exists": tool_path.exists(),
                "skills_path": str(skill_path) if skill_path else None,
                "skills_exists": skill_path.exists() if skill_path else False,
                "command_count": len(list(tool_path.glob("*.md"))) if tool_path.exists() else 0,
                "skill_count": len(list(skill_path.glob("*.md"))) if skill_path and skill_path.exists() else 0,
            }
            detected[tool_name] = tool_info

        return detected

    async def get_personal_commands(self, tool: str = "claude") -> Dict[str, str]:
        """Load personal commands from a specific tool's directory"""
        home = Path.home()
        rel_path = self.TOOL_PATHS.get(tool, ".claude/commands")
        commands_path = home / rel_path

        commands = {}
        if not commands_path.exists():
            logger.warning(f"Personal commands path not found: {commands_path}")
            return commands

        for cmd_file in commands_path.glob("*.md"):
            cmd_name = cmd_file.stem
            try:
                with open(cmd_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                commands[cmd_name] = content
                logger.debug(f"Loaded personal command: {cmd_name}")
            except Exception as e:
                logger.error(f"Error loading personal command {cmd_file}: {e}")

        return commands

    async def sync_personal_commands_to_haivemind(
        self,
        tool: str = "claude",
        commands_filter: List[str] = None,
        scope: str = "project-shared",
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """Sync personal commands from local tool directory to hAIveMind memory"""
        result = {
            "tool": tool,
            "synced": [],
            "skipped": [],
            "errors": [],
            "total": 0
        }

        personal_commands = await self.get_personal_commands(tool)
        result["total"] = len(personal_commands)

        for cmd_name, content in personal_commands.items():
            # Apply filter if specified
            if commands_filter and cmd_name not in commands_filter:
                result["skipped"].append({"name": cmd_name, "reason": "not in filter"})
                continue

            # Skip hv-* commands (they come from haivemind repo, not personal)
            if cmd_name.startswith("hv-"):
                result["skipped"].append({"name": cmd_name, "reason": "hAIveMind command"})
                continue

            try:
                # Check if command already exists in memory
                existing = await self.storage.search_memories(
                    query=f"command_name:{cmd_name} command_type:personal",
                    category="agent",
                    limit=1
                )

                # Create metadata
                cmd_tags = ["personal-command", f"tool:{tool}", cmd_name]
                if tags:
                    cmd_tags.extend(tags)

                metadata = {
                    "command_name": cmd_name,
                    "command_type": "personal",
                    "source_tool": tool,
                    "sync_time": time.time(),
                    "machine_id": self.storage.machine_id,
                    "version": self.version,
                    "content_hash": hash(content) % (10**10)
                }

                if existing and len(existing) > 0:
                    # Update existing
                    memory_id = existing[0].get("id")
                    if memory_id:
                        await self.storage.update_memory(
                            memory_id=memory_id,
                            content=content,
                            metadata=metadata,
                            tags=cmd_tags
                        )
                        result["synced"].append({"name": cmd_name, "action": "updated"})
                    else:
                        # Store new if no ID
                        await self.storage.store_memory(
                            content=content,
                            category="agent",
                            context=f"Personal command: {cmd_name}",
                            metadata=metadata,
                            tags=cmd_tags,
                            scope=scope
                        )
                        result["synced"].append({"name": cmd_name, "action": "created"})
                else:
                    # Store new command
                    await self.storage.store_memory(
                        content=content,
                        category="agent",
                        context=f"Personal command: {cmd_name}",
                        metadata=metadata,
                        tags=cmd_tags,
                        scope=scope
                    )
                    result["synced"].append({"name": cmd_name, "action": "created"})

            except Exception as e:
                result["errors"].append({"name": cmd_name, "error": str(e)})
                logger.error(f"Error syncing command {cmd_name}: {e}")

        return result

    async def sync_haivemind_commands_to_local(
        self,
        tool: str = "claude",
        commands_filter: List[str] = None,
        include_personal: bool = True,
        include_hv: bool = True,
        force: bool = False
    ) -> Dict[str, Any]:
        """Sync commands from hAIveMind memory to local tool directory"""
        result = {
            "tool": tool,
            "installed": [],
            "skipped": [],
            "errors": [],
            "target_path": ""
        }

        home = Path.home()
        rel_path = self.TOOL_PATHS.get(tool, ".claude/commands")
        target_path = home / rel_path
        target_path.mkdir(parents=True, exist_ok=True)
        result["target_path"] = str(target_path)

        commands_to_install = {}

        # Get hv-* commands from haivemind repo
        if include_hv:
            hv_templates = await self.get_command_templates()
            for name, content in hv_templates.items():
                if commands_filter and name not in commands_filter:
                    continue
                commands_to_install[name] = content

        # Get personal commands from hAIveMind memory
        if include_personal:
            personal_memories = await self.storage.search_memories(
                query="command_type:personal",
                category="agent",
                limit=100
            )

            for memory in personal_memories:
                cmd_name = memory.get("metadata", {}).get("command_name", "")
                if not cmd_name:
                    continue
                if commands_filter and cmd_name not in commands_filter:
                    continue
                commands_to_install[cmd_name] = memory.get("content", "")

        # Install commands
        installed = await self.install_commands_to_path(
            str(target_path),
            commands_to_install,
            force=force
        )

        result["installed"] = installed
        result["skipped"] = [
            name for name in commands_to_install.keys()
            if name not in installed
        ]

        return result

    async def sync_commands_cross_tool(
        self,
        source_tool: str = "claude",
        target_tools: List[str] = None,
        commands_filter: List[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """Sync commands from one tool to other tools"""
        if target_tools is None:
            # Default: sync to all other tools
            target_tools = [t for t in self.TOOL_PATHS.keys() if t != source_tool]

        result = {
            "source_tool": source_tool,
            "results": {}
        }

        # Get commands from source
        source_commands = await self.get_personal_commands(source_tool)
        if commands_filter:
            source_commands = {
                k: v for k, v in source_commands.items()
                if k in commands_filter
            }

        home = Path.home()

        for target_tool in target_tools:
            rel_path = self.TOOL_PATHS.get(target_tool)
            if not rel_path:
                result["results"][target_tool] = {"error": "Unknown tool"}
                continue

            target_path = home / rel_path
            target_path.mkdir(parents=True, exist_ok=True)

            installed = await self.install_commands_to_path(
                str(target_path),
                source_commands,
                force=force
            )

            result["results"][target_tool] = {
                "path": str(target_path),
                "installed": installed,
                "total": len(source_commands)
            }

        return result

    async def list_synced_commands(self, scope: str = "all") -> Dict[str, Any]:
        """List all commands synced in hAIveMind memory"""
        result = {
            "personal_commands": [],
            "hv_commands": [],
            "total": 0
        }

        # Get personal commands from memory
        personal_memories = await self.storage.search_memories(
            query="command_type:personal",
            category="agent",
            limit=100
        )

        for memory in personal_memories:
            cmd_name = memory.get("metadata", {}).get("command_name", "")
            source_tool = memory.get("metadata", {}).get("source_tool", "unknown")
            sync_time = memory.get("metadata", {}).get("sync_time", 0)

            result["personal_commands"].append({
                "name": cmd_name,
                "source_tool": source_tool,
                "sync_time": sync_time,
                "memory_id": memory.get("id", "")
            })

        # Get hv-* commands from repo
        hv_templates = await self.get_command_templates()
        result["hv_commands"] = list(hv_templates.keys())

        result["total"] = len(result["personal_commands"]) + len(result["hv_commands"])

        return result

    async def get_command_templates(self) -> Dict[str, str]:
        """Load all command templates from filesystem"""
        templates = {}
        
        if not self.commands_dir.exists():
            logger.warning(f"Commands directory not found: {self.commands_dir}")
            return templates
            
        for cmd_file in self.commands_dir.glob("*.md"):
            cmd_name = cmd_file.stem
            try:
                with open(cmd_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                templates[cmd_name] = content
                logger.debug(f"Loaded template for {cmd_name}")
            except Exception as e:
                logger.error(f"Error loading template {cmd_file}: {e}")
                
        return templates

    async def install_commands_to_path(self, target_path: str, commands: Dict[str, str], force: bool = False) -> List[str]:
        """Install commands to specified path"""
        installed = []
        target_dir = Path(target_path)
        
        # Create directory if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)
        
        for cmd_name, content in commands.items():
            cmd_file = target_dir / f"{cmd_name}.md"
            
            # Check if update needed
            if cmd_file.exists() and not force:
                try:
                    with open(cmd_file, 'r', encoding='utf-8') as f:
                        existing_content = f.read()
                    if existing_content == content:
                        logger.debug(f"Command {cmd_name} already up to date")
                        continue
                except Exception as e:
                    logger.warning(f"Error reading existing command {cmd_name}: {e}")
            
            # Write/update command
            try:
                with open(cmd_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                installed.append(cmd_name)
                logger.info(f"Installed command {cmd_name} to {target_path}")
            except Exception as e:
                logger.error(f"Error installing command {cmd_name}: {e}")
        
        return installed

    async def sync_claude_md_config(self, agent_id: str, machine_id: str, target_location: str) -> str:
        """Generate and sync CLAUDE.md configuration for agent"""
        config_key = f"{machine_id}-{agent_id}-claude_md"
        
        # Check for existing config in collective
        existing_config = await self.storage.search_memories(
            query=f"config_key:{config_key}",
            category="agent",
            limit=1
        )
        
        if existing_config and len(existing_config) > 0:
            config_content = existing_config[0]['content']
            action = "Retrieved existing"
        else:
            # Generate new config
            config_content = await self._generate_claude_md_config(agent_id, machine_id)
            
            # Store in collective
            await self.storage.store_memory(
                content=config_content,
                category="agent",
                context=f"CLAUDE.md configuration for {config_key}",
                metadata={
                    'agent_id': agent_id,
                    'machine_id': machine_id,
                    'config_key': config_key,
                    'config_type': 'claude_md',
                    'auto_generated': True,
                    'creation_time': time.time(),
                    'version': self.version
                },
                tags=["claude-md", "agent-config", agent_id, machine_id, "haivemind"]
            )
            action = "Created new"
        
        return f"{action} CLAUDE.md config for {config_key}"

    async def _generate_claude_md_config(self, agent_id: str, machine_id: str) -> str:
        """Generate CLAUDE.md configuration content for agent"""
        
        # Determine agent role based on machine_id patterns
        role = self._determine_agent_role(machine_id)
        capabilities = self._determine_agent_capabilities(machine_id, role)
        
        config_content = f"""# CLAUDE.md - hAIveMind Agent Configuration

**Author:** Lance James, Unit 221B, Inc

## hAIveMind Collective Connection

You are connected to the **hAIveMind collective intelligence network** as:
- **Agent ID**: {agent_id}
- **Machine**: {machine_id}  
- **Role**: {role}
- **Collective Network**: Distributed AI coordination system

## hAIveMind Commands

Essential commands for collective operations:

### Core Commands
- `/hv-sync` - Sync commands and configuration from collective
- `/hv-status` - Check collective status and network health
- `/hv-install` - Install/update hAIveMind system components

### Communication Commands  
- `/hv-broadcast <message>` - Broadcast message to all collective agents
- `/hv-query <question>` - Query collective knowledge and expertise
- `/hv-delegate <task>` - Delegate task to most suitable agent

## Agent Identity & Capabilities

**Primary Role**: {role}

**Capabilities**: {', '.join(capabilities)}

**Machine Context**: This agent operates on {machine_id} and is specialized for {role.lower().replace('_', ' ')} operations within the collective infrastructure.

## Collective Memory Categories

When storing memories, use these categories for optimal collective intelligence:
- `infrastructure` - Server configs, network topology, service dependencies
- `incidents` - Outage reports, resolutions, post-mortems, lessons learned  
- `deployments` - Release notes, rollback procedures, deployment history
- `monitoring` - Alerts, metrics, thresholds, patterns, dashboard configs
- `runbooks` - Automated procedures, scripts, troubleshooting guides
- `security` - Vulnerabilities, patches, audit logs, compliance data

## Network Coordination

The collective uses:
- **Real-time sync** across all connected agents
- **Semantic search** for knowledge retrieval
- **Task delegation** based on agent capabilities
- **Broadcast messaging** for urgent coordination
- **Centralized memory** with distributed access

Always consider the collective context when making decisions and share relevant discoveries with the network using broadcast or memory storage.
"""
        
        return config_content

    def _determine_agent_role(self, machine_id: str) -> str:
        """Determine agent role based on machine ID patterns"""
        machine_lower = machine_id.lower()
        
        if any(pattern in machine_lower for pattern in ['alpha', 'primary', 'master', 'orchestrator']):
            return "hive_mind_coordinator"
        elif any(pattern in machine_lower for pattern in ['db', 'database', 'elastic', 'mongo']):
            return "database_specialist"
        elif any(pattern in machine_lower for pattern in ['auth', 'security', 'gateway']):
            return "security_specialist"  
        elif any(pattern in machine_lower for pattern in ['scraper', 'collector', 'proxy']):
            return "data_collection_specialist"
        elif any(pattern in machine_lower for pattern in ['monitor', 'grafana', 'alert']):
            return "monitoring_specialist"
        elif any(pattern in machine_lower for pattern in ['dev', 'development', 'test']):
            return "development_specialist"
        else:
            return "general_purpose_agent"

    def _determine_agent_capabilities(self, machine_id: str, role: str) -> List[str]:
        """Determine agent capabilities based on machine and role"""
        base_capabilities = ["memory_management", "collective_communication", "task_coordination"]
        
        role_capabilities = {
            "hive_mind_coordinator": ["orchestration", "deployment", "infrastructure_management", "agent_coordination"],
            "database_specialist": ["database_ops", "backup_restore", "query_optimization", "cluster_management"],
            "security_specialist": ["security_analysis", "incident_response", "compliance_monitoring", "access_control"],
            "data_collection_specialist": ["data_collection", "scraping", "proxy_management", "data_processing"],
            "monitoring_specialist": ["monitoring", "alerting", "incident_response", "metrics_analysis"],
            "development_specialist": ["development", "testing", "code_review", "ci_cd"],
            "general_purpose_agent": ["general_operations", "support", "documentation", "analysis"]
        }
        
        specific_capabilities = role_capabilities.get(role, [])
        return base_capabilities + specific_capabilities

    async def sync_agent_installation(self, agent_id: str = None, target_location: str = "auto", force: bool = False, verbose: bool = False) -> Dict[str, Any]:
        """Complete agent installation and sync workflow"""
        if not agent_id:
            agent_id = self.storage.agent_id
        
        machine_id = self.storage.machine_id
        result = {
            'agent_id': agent_id,
            'machine_id': machine_id, 
            'sync_time': time.time(),
            'status': 'in_progress',
            'operations': [],
            'verbose_output': [] if verbose else None
        }
        
        def log_verbose(message: str):
            if verbose:
                result['verbose_output'].append(message)
                logger.info(f"VERBOSE: {message}")
        
        try:
            log_verbose("Starting hAIveMind agent synchronization...")
            
            # 1. Detect Claude paths
            log_verbose("Detecting Claude command installation paths...")
            claude_paths = await self.detect_claude_paths()
            result['available_paths'] = claude_paths
            log_verbose(f"Found paths: {list(claude_paths.keys())}")
            
            # 2. Determine target location
            log_verbose("Determining target installation location...")
            if target_location == "auto":
                # Check if user already has commands installed somewhere
                personal_has_commands = False
                project_has_commands = False
                
                if "personal" in claude_paths:
                    personal_dir = Path(claude_paths["personal"])
                    personal_has_commands = any(personal_dir.glob("hv-*.md"))
                    
                if "project" in claude_paths:
                    project_dir = Path(claude_paths["project"])
                    project_has_commands = any(project_dir.glob("hv-*.md"))
                
                # Priority logic for auto-detection:
                # 1. If personal directory has existing hAIveMind commands, use it
                # 2. If project directory has existing hAIveMind commands, use it  
                # 3. For orchestrator/server machines (like lance-dev), prefer project
                # 4. For other machines, prefer personal directory
                
                is_orchestrator = machine_id in ["lance-dev", "orchestrator", "primary"]
                
                if personal_has_commands:
                    target_location = "personal"
                    log_verbose("Using personal commands (existing commands detected)")
                elif project_has_commands:
                    target_location = "project" 
                    log_verbose("Using project commands (existing commands detected)")
                elif is_orchestrator and "project" in claude_paths:
                    target_location = "project"
                    log_verbose("Using project-level commands (orchestrator machine)")
                elif "personal" in claude_paths:
                    target_location = "personal"
                    log_verbose("Using personal commands (~/.claude/commands)")
                else:
                    # Create personal path as fallback for non-orchestrator machines
                    personal_path = Path.home() / ".claude" / "commands"
                    personal_path.mkdir(parents=True, exist_ok=True)
                    claude_paths["personal"] = str(personal_path)
                    target_location = "personal"
                    log_verbose("Created personal commands directory (default for new installations)")
            else:
                log_verbose(f"Using specified location: {target_location}")
            
            result['target_location'] = target_location
            target_path = claude_paths[target_location]
            log_verbose(f"Target path: {target_path}")
            
            # 3. Load command templates
            log_verbose("Loading hv-* command templates from collective...")
            templates = await self.get_command_templates()
            result['available_commands'] = list(templates.keys())
            log_verbose(f"Found {len(templates)} command templates: {list(templates.keys())}")
            
            # 4. Install commands
            if templates:
                log_verbose("Installing/updating commands...")
                installed_commands = await self.install_commands_to_path(target_path, templates, force)
                result['installed_commands'] = installed_commands
                if installed_commands:
                    log_verbose(f"Updated commands: {installed_commands}")
                    result['operations'].append(f"Installed {len(installed_commands)} commands to {target_location}")
                else:
                    log_verbose("All commands are up to date")
                    result['operations'].append("All commands already up to date")
            else:
                log_verbose("No command templates found")
            
            # 5. Sync CLAUDE.md config
            log_verbose("Syncing CLAUDE.md configuration...")
            config_result = await self.sync_claude_md_config(agent_id, machine_id, target_location)
            result['operations'].append(config_result)
            log_verbose(f"Config sync: {config_result}")
            
            # 6. Register/update agent in collective
            log_verbose("Updating agent registration in collective...")
            role = self._determine_agent_role(machine_id)
            capabilities = self._determine_agent_capabilities(machine_id, role)
            await self.storage.register_agent(
                role=role,
                description=f"hAIveMind agent on {machine_id}",
                capabilities=capabilities
            )
            result['operations'].append("Updated agent registration")
            log_verbose(f"Registered as {role} with capabilities: {capabilities}")
            
            # 7. Store sync record
            log_verbose("Storing sync record in collective memory...")
            # Create clean metadata with only primitive types
            clean_metadata = {
                'agent_id': result['agent_id'],
                'machine_id': result['machine_id'],
                'sync_time': result['sync_time'],
                'status': result['status'],
                'target_location': result.get('target_location', ''),
                'operations_summary': ', '.join(result.get('operations', [])),
                'installed_commands': ', '.join(result.get('installed_commands', [])),
                'available_commands': ', '.join(result.get('available_commands', [])),
                'available_paths': str(result.get('available_paths', {}))
            }
            
            await self.storage.store_memory(
                content=f"Agent {agent_id} completed installation sync: {', '.join(result['operations'])}",
                category="agent",
                context=f"Installation sync for {machine_id}-{agent_id}",
                metadata=clean_metadata,
                tags=["agent-sync", "installation", agent_id, machine_id]
            )
            log_verbose("Sync record stored successfully")
            
            result['status'] = 'success'
            result['message'] = f"✅ hAIveMind sync completed for {agent_id}"
            log_verbose("Synchronization completed successfully!")
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            result['message'] = f"❌ Sync failed: {e}"
            logger.error(f"Agent sync failed: {e}")
        
        return result

    async def check_sync_status(self, agent_id: str = None) -> Dict[str, Any]:
        """Check current sync status for agent"""
        if not agent_id:
            agent_id = self.storage.agent_id
            
        machine_id = self.storage.machine_id
        
        # Search for recent sync records
        recent_sync = await self.storage.search_memories(
            query=f"agent_id:{agent_id} installation sync",
            category="agent",
            limit=1
        )
        
        status = {
            'agent_id': agent_id,
            'machine_id': machine_id,
            'last_sync': None,
            'commands_installed': [],
            'config_synced': False
        }
        
        if recent_sync and len(recent_sync) > 0:
            last_sync_memory = recent_sync[0]
            status['last_sync'] = last_sync_memory.get('metadata', {}).get('sync_time')
            # Handle both old list format and new string format
            commands_str = last_sync_memory.get('metadata', {}).get('installed_commands', '')
            if isinstance(commands_str, str) and commands_str:
                status['commands_installed'] = [cmd.strip() for cmd in commands_str.split(',') if cmd.strip()]
            else:
                status['commands_installed'] = []
        
        # Check for config
        config_search = await self.storage.search_memories(
            query=f"{machine_id}-{agent_id}-claude_md",
            category="agent",
            limit=1
        )
        status['config_synced'] = bool(config_search and len(config_search) > 0)
        
        return status
