#!/usr/bin/env python3
"""
hAIveMind MCP Standalone Client
A portable MCP server that bridges to the hAIveMind remote server.
Can be used with any MCP client system (Claude Desktop, cursor-agent, etc.)
"""

import asyncio
import json
import logging
import sys
import requests
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

# MCP imports
try:
    from mcp.server import Server
    from mcp.types import (
        Resource, Tool, TextContent, ImageContent, EmbeddedResource,
        LoggingLevel, CallToolResult, ListResourcesResult, ListToolsResult,
        ReadResourceResult
    )
    import mcp.server.stdio
except ImportError:
    print("Error: MCP package not found. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("haivemind-mcp")

class HAIveMindMCPStandalone:
    """Standalone MCP server that bridges to hAIveMind remote server"""
    
    def __init__(self, haivemind_url: str = "http://localhost:8900"):
        self.haivemind_url = haivemind_url
        self.server = Server("haivemind-standalone")
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Register tools
        self._register_tools()
        
    def _register_tools(self):
        """Register all hAIveMind tools with the MCP server"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available hAIveMind tools"""
            return [
                # Core Memory Tools
                Tool(
                    name="store_memory",
                    description="Store a memory in the hAIveMind system with comprehensive tracking",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "The memory content to store"},
                            "category": {"type": "string", "description": "Memory category", "default": "general"},
                            "project": {"type": "string", "description": "Project identifier"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
                            "scope": {"type": "string", "enum": ["machine-local", "project-local", "project-shared", "user-global", "team-global", "private"], "default": "project-shared"},
                            "share_with": {"type": "array", "items": {"type": "string"}, "description": "Machine groups to share with"},
                            "exclude_from": {"type": "array", "items": {"type": "string"}, "description": "Machines to exclude from sharing"},
                            "sensitive": {"type": "boolean", "description": "Mark as sensitive (private to this machine)", "default": False}
                        },
                        "required": ["content"]
                    }
                ),
                Tool(
                    name="search_memories",
                    description="Search memories using full-text and semantic search",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "category": {"type": "string", "description": "Filter by category"},
                            "project": {"type": "string", "description": "Filter by project"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                            "machine_id": {"type": "string", "description": "Filter by machine"},
                            "limit": {"type": "integer", "description": "Maximum results", "default": 10},
                            "semantic": {"type": "boolean", "description": "Use semantic search", "default": True}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="retrieve_memory",
                    description="Retrieve a specific memory by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "memory_id": {"type": "string", "description": "Memory ID to retrieve"}
                        },
                        "required": ["memory_id"]
                    }
                ),
                Tool(
                    name="get_recent_memories",
                    description="Get recent memories within a time window",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "hours": {"type": "integer", "description": "Hours to look back", "default": 24},
                            "category": {"type": "string", "description": "Filter by category"},
                            "project": {"type": "string", "description": "Filter by project"},
                            "limit": {"type": "integer", "description": "Maximum results", "default": 20}
                        }
                    }
                ),
                Tool(
                    name="get_memory_stats",
                    description="Get statistics about stored memories",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                
                # hAIveMind Coordination Tools
                Tool(
                    name="register_agent",
                    description="Register as a hAIveMind agent with specific capabilities",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "role": {"type": "string", "description": "Agent role (e.g., 'hive_mind', 'elasticsearch_ops')"},
                            "description": {"type": "string", "description": "Agent description"},
                            "capabilities": {"type": "array", "items": {"type": "string"}, "description": "Agent capabilities"},
                            "machine_group": {"type": "string", "description": "Machine group identifier"}
                        },
                        "required": ["role"]
                    }
                ),
                Tool(
                    name="get_agent_roster",
                    description="Get list of all active hAIveMind agents",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_inactive": {"type": "boolean", "description": "Include inactive agents", "default": False}
                        }
                    }
                ),
                Tool(
                    name="delegate_task",
                    description="Delegate a task to another hAIveMind agent",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_description": {"type": "string", "description": "Description of the task"},
                            "required_capabilities": {"type": "array", "items": {"type": "string"}, "description": "Required capabilities"},
                            "target_agent": {"type": "string", "description": "Specific agent to delegate to"},
                            "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "default": "medium"}
                        },
                        "required": ["task_description"]
                    }
                ),
                Tool(
                    name="broadcast_discovery",
                    description="Broadcast an important discovery to all hAIveMind agents",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "Discovery message"},
                            "category": {"type": "string", "description": "Discovery category"},
                            "severity": {"type": "string", "enum": ["info", "warning", "critical"], "default": "info"},
                            "affected_systems": {"type": "array", "items": {"type": "string"}, "description": "Affected systems"}
                        },
                        "required": ["message"]
                    }
                ),
                
                # Infrastructure & DevOps Tools
                Tool(
                    name="record_incident",
                    description="Record a DevOps incident with automatic correlation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Incident title"},
                            "description": {"type": "string", "description": "Incident description"},
                            "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"},
                            "affected_systems": {"type": "array", "items": {"type": "string"}, "description": "Affected systems"},
                            "resolution": {"type": "string", "description": "Resolution steps taken"}
                        },
                        "required": ["title", "description"]
                    }
                ),
                Tool(
                    name="generate_runbook",
                    description="Generate a reusable runbook from successful procedures",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Runbook title"},
                            "procedure": {"type": "string", "description": "Step-by-step procedure"},
                            "system": {"type": "string", "description": "Target system"},
                            "prerequisites": {"type": "array", "items": {"type": "string"}, "description": "Prerequisites"}
                        },
                        "required": ["title", "procedure"]
                    }
                ),
                Tool(
                    name="sync_ssh_config",
                    description="Sync SSH configuration across hAIveMind infrastructure",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "config_content": {"type": "string", "description": "SSH config content"},
                            "target_machines": {"type": "array", "items": {"type": "string"}, "description": "Target machines"}
                        },
                        "required": ["config_content"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Call a hAIveMind tool"""
            try:
                # Forward the tool call to the hAIveMind remote server
                result = await self._forward_tool_call(name, arguments)
                
                if "error" in result:
                    return [TextContent(
                        type="text",
                        text=f"Error: {result['error'].get('message', 'Unknown error')}"
                    )]
                
                # Format the result as text
                result_text = json.dumps(result.get("result", result), indent=2)
                return [TextContent(type="text", text=result_text)]
                
            except Exception as e:
                logger.error(f"Tool call failed: {e}")
                return [TextContent(
                    type="text",
                    text=f"Error calling tool {name}: {str(e)}"
                )]
    
    async def _forward_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Forward tool call to hAIveMind remote server"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                },
                "id": 1
            }
            
            # Use asyncio to run the synchronous request
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.session.post(
                    f"{self.haivemind_url}/mcp",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": {
                        "code": -32000,
                        "message": f"HTTP {response.status_code}: {response.text}"
                    }
                }
                
        except Exception as e:
            return {
                "error": {
                    "code": -32000,
                    "message": f"Connection error: {str(e)}"
                }
            }
    
    async def run(self):
        """Run the MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="hAIveMind MCP Standalone Client")
    parser.add_argument(
        "--haivemind-url",
        default="http://localhost:8900",
        help="hAIveMind remote server URL"
    )
    
    args = parser.parse_args()
    
    # Create and run the server
    server = HAIveMindMCPStandalone(args.haivemind_url)
    asyncio.run(server.run())

if __name__ == "__main__":
    main()