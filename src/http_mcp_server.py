#!/usr/bin/env python3
"""
HTTP MCP Server - Provides MCP-over-HTTP for remote access
CRITICAL SECURITY FIXES:
- Add JWT authentication (Bearer token)
- Restrict allowed MCP methods and block file-operation tools
- Add request size limits
- Remove open CORS with credentials

This mitigates unauthenticated remote code execution vectors.
"""

import os
import re
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from starlette.responses import PlainTextResponse

# Load config
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

try:
    # Prefer shared auth manager if available
    from auth import AuthManager  # type: ignore
except Exception:
    AuthManager = None  # Fallback to local JWT handling

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

        # ---- Security configuration ----
        self.max_request_size = int(os.environ.get("MCP_HTTP_MAX_REQUEST_BYTES", str(1024 * 1024)))  # 1MB default

        # JWT secret from env or config; do NOT allow empty
        self.jwt_secret = os.environ.get("HAIVEMIND_JWT_SECRET") or os.environ.get("MCP_HTTP_JWT_SECRET")
        if not self.jwt_secret and AuthManager is None:
            # As a last resort (no shared AuthManager), use an explicit default but warn by raising on first use
            self.jwt_secret = None

        # Allowed JSON-RPC methods (restrict to safe MCP surface)
        self.allowed_methods = {"tools/list", "tools/call"}

        # Blocklist of tool names associated with filesystem or RCE risk
        self.blocked_tool_patterns = [
            re.compile(pat, re.IGNORECASE)
            for pat in [
                r"file", r"path", r"fs", r"read", r"write", r"delete", r"remove",
                r"chmod", r"chown", r"exec", r"shell", r"spawn", r"process", r"command",
                r"upload", r"download", r"copy", r"move"
            ]
        ]

        # Optionally load config for auth and CORS if present
        config = self._load_config()
        self.auth_manager = AuthManager(config) if (AuthManager is not None) else None

        # ---- CORS hardening ----
        # Remove open CORS with credentials; restrict origins if configured
        allowed_origins = self._get_allowed_origins(config)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=False,  # never allow credentials with wide origins
            allow_methods=["POST", "GET"],
            allow_headers=["authorization", "content-type"],
        )

        # ---- Request size limit middleware (header-based) ----
        @self.app.middleware("http")
        async def limit_request_size(request: Request, call_next):
            cl = request.headers.get("content-length")
            if cl is not None:
                try:
                    if int(cl) > self.max_request_size:
                        return PlainTextResponse("Request too large", status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
                except ValueError:
                    # Ignore invalid header, let downstream parse but still safe
                    pass
            return await call_next(request)

        self.setup_routes()

    def _load_config(self) -> Dict[str, Any]:
        try:
            cfg_path = Path(__file__).parent.parent / "config" / "config.json"
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data
        except Exception:
            pass
        return {}

    def _get_allowed_origins(self, config: Dict[str, Any]) -> List[str]:
        # Env overrides
        env_csv = os.environ.get("MCP_HTTP_ALLOWED_ORIGINS")
        if env_csv:
            return [o.strip() for o in env_csv.split(",") if o.strip()]
        # Config fallbacks
        try:
            origins = (
                config.get("remote_server", {})
                .get("allowed_origins", ["http://localhost", "http://127.0.0.1"])
            )
            # Never return ["*"] here
            return [o for o in origins if o != "*"] or ["http://localhost", "http://127.0.0.1"]
        except Exception:
            return ["http://localhost", "http://127.0.0.1"]

    # ---- Authentication dependency ----
    def _require_jwt(self, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
        token = None
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
        if not token:
            raise HTTPException(status_code=401, detail="Missing Bearer token")

        # Prefer shared AuthManager if available
        if self.auth_manager is not None:
            valid, payload = self.auth_manager.validate_jwt_token(token)
            if not valid:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            return payload

        # Local validation fallback using PyJWT if secret available
        if not self.jwt_secret:
            raise HTTPException(status_code=500, detail="JWT not configured")
        try:
            import jwt  # PyJWT
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
    def setup_routes(self):
        @self.app.post("/mcp")
        async def handle_mcp_request(request: MCPRequest, _: Dict[str, Any] = Depends(self._require_jwt)) -> MCPResponse:
            try:
                # Enforce allowed methods only
                if request.method not in self.allowed_methods:
                    raise HTTPException(status_code=403, detail=f"Method '{request.method}' not allowed")

                # Block file-operation tools or suspicious params
                if request.method == "tools/call":
                    tool_name = (request.params or {}).get("name", "")
                    args = (request.params or {}).get("arguments", {}) or {}
                    # Reject by heuristic patterns
                    if any(p.search(tool_name) for p in self.blocked_tool_patterns):
                        raise HTTPException(status_code=403, detail="Tool not permitted")
                    # Explicitly block file path style args
                    if any(k.lower() in ("file_path", "path", "filepath") for k in args.keys()):
                        raise HTTPException(status_code=403, detail="File operations are not permitted")

                # Proxy request to local stdio MCP server
                result = await self.proxy_to_stdio_mcp(request)
                return MCPResponse(
                    id=request.id,
                    result=result
                )
            except Exception as e:
                if isinstance(e, HTTPException):
                    # Convert to JSON-RPC error response while preserving HTTP semantics in dependency
                    return MCPResponse(
                        id=request.id,
                        error={"code": e.status_code, "message": e.detail},
                    )
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": -32603,
                        "message": "Internal server error",
                    },
                )
        
        @self.app.get("/mcp/capabilities")
        async def get_capabilities(_: Dict[str, Any] = Depends(self._require_jwt)):
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
            "python3", "/home/lj/haivemind-mcp-server/src/memory_server.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            # Send request to stdio server with timeout
            request_data = json.dumps(jsonrpc_request) + "\n"
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=request_data.encode()),
                timeout=30.0  # 30 second timeout for MCP operations
            )
            
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
                
        except asyncio.TimeoutError:
            # Handle timeout specifically
            if process.returncode is None:
                process.kill()  # Use kill() for timeout cases
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    pass  # Process might be stuck, continue
            raise Exception("MCP server request timed out after 30 seconds")
        except Exception as e:
            # Ensure process is terminated for other exceptions
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()  # Force kill if terminate doesn't work
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
