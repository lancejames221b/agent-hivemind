#!/usr/bin/env python3
"""
Example: Simple Python MCP Server
This is a basic example of a Python-based MCP server that can be hosted on hAIveMind
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import TextContent
except ImportError:
    print("Error: MCP package not found. Install with: pip install mcp")
    sys.exit(1)

# Initialize FastMCP server
mcp = FastMCP("Simple Example Server")

@mcp.tool()
async def hello_world(name: str = "World") -> str:
    """Say hello to someone"""
    return f"Hello, {name}! This message is from a hosted MCP server on hAIveMind."

@mcp.tool()
async def add_numbers(a: float, b: float) -> str:
    """Add two numbers together"""
    result = a + b
    return f"The sum of {a} and {b} is {result}"

@mcp.tool()
async def get_server_info() -> str:
    """Get information about this MCP server"""
    return json.dumps({
        "name": "Simple Example Server",
        "version": "1.0.0",
        "description": "A basic example MCP server hosted on hAIveMind",
        "tools": ["hello_world", "add_numbers", "get_server_info"],
        "hosted_on": "hAIveMind MCP Server Hosting Platform"
    }, indent=2)

@mcp.resource("example://info")
async def server_info() -> str:
    """Server information resource"""
    return "This is a simple example MCP server running on hAIveMind hosting platform."

if __name__ == "__main__":
    print("🚀 Starting Simple Example MCP Server...")
    print("📡 Server will be available on stdio transport")
    
    # Add health endpoint for monitoring
    @mcp.custom_route("/health", methods=["GET"])
    async def health(request):
        from starlette.responses import JSONResponse
        return JSONResponse({
            "status": "healthy",
            "server": "simple-example",
            "version": "1.0.0"
        })
    
    # Run the server
    mcp.run(transport="stdio")