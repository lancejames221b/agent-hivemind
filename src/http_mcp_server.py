#!/usr/bin/env python3
"""
HTTP MCP Server - Provides MCP-over-HTTP for remote access
Proxies requests to the local stdio MCP server
"""

import asyncio
import json
import subprocess
import uuid
from typing import Any, Dict, List
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Load config
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

# Pydantic models for MCP-over-HTTP
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = {}
    id: str = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str = None
    result: Any = None
    error: Dict[str, Any] = None

class HTTPMCPServer:
    def __init__(self):
        self.app = FastAPI(title="Memory MCP HTTP Server")
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.setup_routes()
        
    def setup_routes(self):
        @self.app.post("/mcp")
        async def handle_mcp_request(request: MCPRequest) -> MCPResponse:
            try:
                # Proxy request to local stdio MCP server
                result = await self.proxy_to_stdio_mcp(request)
                return MCPResponse(
                    id=request.id,
                    result=result
                )
            except Exception as e:
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": -32603,
                        "message": str(e)
                    }
                )
        
        @self.app.get("/mcp/capabilities")
        async def get_capabilities():
            """Return MCP server capabilities"""
            return {
                "capabilities": {
                    "tools": True,
                    "resources": False,
                    "prompts": False
                },
                "serverInfo": {
                    "name": "memory-mcp-http",
                    "version": "1.0.0"
                }
            }
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    async def proxy_to_stdio_mcp(self, request: MCPRequest) -> Any:
        """Proxy MCP request to local stdio server"""
        
        # Create the JSON-RPC request
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "method": request.method,
            "params": request.params,
            "id": request.id or str(uuid.uuid4())
        }
        
        # Start the stdio MCP server process
        process = await asyncio.create_subprocess_exec(
            "python3", "/home/lj/memory-mcp/src/memory_server.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            # Send request to stdio server
            request_data = json.dumps(jsonrpc_request) + "\n"
            stdout, stderr = await process.communicate(input=request_data.encode())
            
            if process.returncode != 0:
                raise Exception(f"MCP server error: {stderr.decode()}")
            
            # Parse response
            response_text = stdout.decode().strip()
            if response_text:
                response_data = json.loads(response_text)
                if "error" in response_data:
                    raise Exception(response_data["error"]["message"])
                return response_data.get("result")
            else:
                raise Exception("No response from MCP server")
                
        except Exception as e:
            # Ensure process is terminated
            if process.returncode is None:
                process.terminate()
                await process.wait()
            raise e
    
    def run(self, host: str = "0.0.0.0", port: int = 8900):
        """Run the HTTP MCP server"""
        uvicorn.run(self.app, host=host, port=port)

def main():
    server = HTTPMCPServer()
    print("Starting HTTP MCP Server on port 8900...")
    print("MCP endpoint: http://lance-dev:8900/mcp")
    print("Health check: http://lance-dev:8900/health")
    server.run(port=8900)

if __name__ == "__main__":
    main()