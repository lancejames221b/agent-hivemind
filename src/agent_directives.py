#!/usr/bin/env python3
"""
hAIveMind Agent Directive System
Provides automated installation instructions for Claude agents connecting to the hivemind
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AgentDirectiveSystem:
    """Manages installation and setup directives for Claude agents"""
    
    def __init__(self, storage=None):
        self.storage = storage
        self.directives = self._load_agent_directives()
        
    def _load_agent_directives(self) -> Dict[str, Any]:
        """Load predefined agent directives"""
        return {
            "claude_code_setup": {
                "name": "Claude Code hAIveMind Integration Setup",
                "version": "1.0.0",
                "priority": "critical",
                "auto_execute": True,
                "description": "Complete setup of hAIveMind commands and hooks for Claude Code",
                "prerequisites": [
                    "Claude Code CLI installed",
                    "Access to ~/.claude directory",
                    "Network connectivity to hAIveMind server"
                ],
                "steps": [
                    {
                        "id": "detect_environment",
                        "name": "Detect Claude Code Environment", 
                        "action": "bash",
                        "command": "test -d ~/.claude && echo 'Claude Code environment detected' || echo 'ERROR: Claude Code not installed'",
                        "success_condition": "contains:detected",
                        "required": True
                    },
                    {
                        "id": "create_directories",
                        "name": "Create Required Directories",
                        "action": "bash", 
                        "command": "mkdir -p ~/.claude/commands ~/.claude/hooks && echo 'Directories created successfully'",
                        "success_condition": "contains:successfully",
                        "required": True
                    },
                    {
                        "id": "install_commands",
                        "name": "Install hAIveMind Commands",
                        "action": "mcp_call",
                        "tool": "install_agent_commands",
                        "parameters": {"force": True, "target_location": "auto"},
                        "success_condition": "installation completed successfully",
                        "required": True
                    },
                    {
                        "id": "install_hooks",
                        "name": "Install Claude Code Hooks",
                        "action": "create_files",
                        "files": [
                            {
                                "path": "~/.claude/hooks/pre-command.sh",
                                "content": "hooks/pre-command.sh",
                                "mode": "755"
                            },
                            {
                                "path": "~/.claude/hooks/post-command.sh", 
                                "content": "hooks/post-command.sh",
                                "mode": "755"
                            },
                            {
                                "path": "~/.claude/hooks/ticket-sync.py",
                                "content": "hooks/ticket-sync.py",
                                "mode": "755"  
                            },
                            {
                                "path": "~/.claude/hooks/haivemind-bridge.py",
                                "content": "hooks/haivemind-bridge.py",
                                "mode": "644"
                            }
                        ],
                        "success_condition": "all files created",
                        "required": True
                    },
                    {
                        "id": "configure_mcp",
                        "name": "Configure MCP Connection",
                        "action": "bash",
                        "command": "claude mcp add --transport sse hAIveMind http://localhost:8900/sse 2>/dev/null || claude mcp add --transport sse hAIveMind http://lance-dev:8900/sse",
                        "success_condition": "contains:added",
                        "required": True
                    },
                    {
                        "id": "register_agent", 
                        "name": "Register with hAIveMind Collective",
                        "action": "mcp_call",
                        "tool": "register_agent",
                        "parameters": {
                            "role": "claude_code_agent",
                            "capabilities": ["development", "code_analysis", "documentation", "troubleshooting"]
                        },
                        "success_condition": "registered successfully",
                        "required": True
                    },
                    {
                        "id": "test_installation",
                        "name": "Test hAIveMind Integration",
                        "action": "mcp_call", 
                        "tool": "get_agent_roster",
                        "parameters": {"limit": 5},
                        "success_condition": "agents found",
                        "required": True
                    }
                ],
                "completion_memory": {
                    "category": "infrastructure",
                    "content_template": "Claude Code agent successfully integrated with hAIveMind collective. Agent ID: {agent_id}, Machine: {hostname}, Commands: {command_count}, Hooks: {hook_count}",
                    "tags": ["agent-setup", "claude-code", "automated-install", "collective-integration"]
                }
            },
            
            "periodic_sync": {
                "name": "Periodic hAIveMind Synchronization",
                "version": "1.0.0", 
                "priority": "normal",
                "auto_execute": False,
                "schedule": "daily",
                "description": "Regular sync to ensure agent has latest commands and configurations",
                "steps": [
                    {
                        "id": "sync_commands",
                        "name": "Sync Latest Commands",
                        "action": "mcp_call",
                        "tool": "sync_agent_commands", 
                        "parameters": {"force": False, "verbose": False},
                        "success_condition": "sync completed",
                        "required": False
                    },
                    {
                        "id": "update_capabilities",
                        "name": "Update Agent Capabilities",
                        "action": "mcp_call",
                        "tool": "register_agent",
                        "parameters": {
                            "role": "claude_code_agent", 
                            "capabilities": ["development", "code_analysis", "documentation", "troubleshooting", "infrastructure"]
                        },
                        "success_condition": "capabilities updated",
                        "required": False
                    }
                ]
            }
        }
    
    async def get_agent_directive(self, agent_type: str = "claude_code_agent") -> Dict[str, Any]:
        """Get installation directive for specific agent type"""
        if agent_type == "claude_code_agent":
            directive = self.directives["claude_code_setup"].copy()
            
            # Add current timestamp and generate directive ID
            directive["directive_id"] = f"setup_{int(datetime.now().timestamp())}"
            directive["issued_at"] = datetime.now().isoformat()
            directive["expires_at"] = (datetime.now() + timedelta(hours=24)).isoformat()
            
            return directive
        
        return {"error": f"No directive found for agent type: {agent_type}"}
    
    async def generate_installation_script(self, directive: Dict[str, Any]) -> str:
        """Generate executable installation script from directive"""
        
        script_lines = [
            "#!/bin/bash",
            "# hAIveMind Agent Installation Script",
            f"# Generated: {datetime.now().isoformat()}",
            f"# Directive: {directive.get('name', 'Unknown')}",
            "",
            "set -e  # Exit on any error",
            "",
            "echo '🤖 Starting hAIveMind Agent Integration...'",
            "echo '=========================================='",
            ""
        ]
        
        for i, step in enumerate(directive.get("steps", []), 1):
            step_name = step.get("name", f"Step {i}")
            script_lines.extend([
                f"echo '📋 Step {i}: {step_name}'",
                ""
            ])
            
            if step.get("action") == "bash":
                script_lines.extend([
                    f"# {step_name}",
                    step.get("command", "echo 'No command specified'"),
                    "if [ $? -ne 0 ]; then",
                    f"    echo '❌ Step {i} failed: {step_name}'",
                    "    exit 1" if step.get("required", False) else "    echo '⚠️  Non-critical step failed, continuing...'",
                    "fi",
                    f"echo '✅ Step {i} completed'",
                    ""
                ])
            
            elif step.get("action") == "create_files":
                for file_info in step.get("files", []):
                    file_path = file_info.get("path", "").replace("~", "$HOME")
                    script_lines.extend([
                        f"# Create {file_path}",
                        f"mkdir -p $(dirname {file_path})",
                        f"# File content would be injected here",
                        f"chmod {file_info.get('mode', '644')} {file_path}",
                        ""
                    ])
            
            elif step.get("action") == "mcp_call":
                tool_name = step.get("tool", "unknown_tool")
                script_lines.extend([
                    f"# MCP Call: {tool_name}",
                    f"echo 'This step requires MCP integration: {tool_name}'",
                    "# Would execute via Claude Code MCP interface",
                    ""
                ])
        
        script_lines.extend([
            "echo '=========================================='",
            "echo '✅ hAIveMind Agent Integration Complete!'",
            "echo '🔗 You are now connected to the collective'",
            "echo 'Available commands: ls ~/.claude/commands/'",
            "echo 'Active hooks: ls ~/.claude/hooks/'",
            ""
        ])
        
        return "\n".join(script_lines)
    
    async def get_installation_instructions(self, agent_id: str = None) -> str:
        """Get human-readable installation instructions"""
        
        directive = await self.get_agent_directive("claude_code_agent")
        
        instructions = f"""
# 🤖 hAIveMind Agent Integration Instructions

**Directive**: {directive.get('name')}
**Version**: {directive.get('version')} 
**Priority**: {directive.get('priority', 'normal').upper()}
**Agent ID**: {agent_id or 'auto-detect'}

## 📋 Prerequisites
"""
        
        for prereq in directive.get("prerequisites", []):
            instructions += f"- {prereq}\n"
        
        instructions += "\n## 🚀 Installation Steps\n\n"
        
        for i, step in enumerate(directive.get("steps", []), 1):
            step_name = step.get("name", f"Step {i}")
            required = "**REQUIRED**" if step.get("required", False) else "optional"
            
            instructions += f"### Step {i}: {step_name} ({required})\n\n"
            
            if step.get("action") == "bash":
                instructions += f"```bash\n{step.get('command', 'No command specified')}\n```\n\n"
            elif step.get("action") == "mcp_call":
                tool_name = step.get("tool", "unknown_tool")
                params = step.get("parameters", {})
                instructions += f"**MCP Tool**: `{tool_name}`\n"
                instructions += f"**Parameters**: `{json.dumps(params, indent=2)}`\n\n"
            elif step.get("action") == "create_files":
                instructions += "**Files to create**:\n"
                for file_info in step.get("files", []):
                    instructions += f"- `{file_info.get('path')}` (mode: {file_info.get('mode', '644')})\n"
                instructions += "\n"
        
        instructions += """
## 🔧 Manual Execution

If you prefer to execute these steps manually, follow each step in order. 
For MCP tool calls, use the Claude Code interface to execute the specified tools.

## 🤖 Automated Execution

The hAIveMind server can execute this directive automatically when you connect.
Simply call the `execute_agent_directive` MCP tool to begin automated setup.

## ✅ Verification

After completion, verify your integration:
- Commands available: `ls ~/.claude/commands/`
- Hooks installed: `ls ~/.claude/hooks/`  
- MCP connection: Test any `hv-*` command
- Agent registration: Check agent roster with `hv-status --agents`

## 🆘 Troubleshooting

If installation fails:
1. Check network connectivity to hAIveMind server
2. Verify Claude Code CLI is properly installed
3. Ensure write permissions to `~/.claude/` directory
4. Review logs at `~/.claude/hooks/installation.log`
5. Contact hAIveMind collective for assistance via `hv-broadcast`

---
*This directive was generated by hAIveMind Agent Directive System v1.0.0*
"""
        
        return instructions.strip()
    
    async def store_directive_execution(self, agent_id: str, directive_id: str, 
                                      results: List[Dict[str, Any]]) -> str:
        """Store directive execution results in hAIveMind memory"""
        
        if not self.storage:
            return "No storage available"
        
        success_count = len([r for r in results if r.get("success", False)])
        total_steps = len(results)
        
        content = f"Agent directive execution completed for {agent_id}. "
        content += f"Success: {success_count}/{total_steps} steps. "
        content += f"Directive ID: {directive_id}"
        
        memory_id = await self.storage.store_memory(
            content=content,
            category="infrastructure", 
            context=f"Agent directive execution for {agent_id}",
            metadata={
                "agent_id": agent_id,
                "directive_id": directive_id, 
                "success_count": success_count,
                "total_steps": total_steps,
                "execution_results": results,
                "execution_time": datetime.now().isoformat()
            },
            tags=["agent-directives", "automated-setup", agent_id, directive_id]
        )
        
        return memory_id