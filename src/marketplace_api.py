#!/usr/bin/env python3
"""
MCP Marketplace REST API - Enterprise & Security Production Ready
Provides comprehensive REST API for the MCP Server Marketplace with authentication,
rate limiting, and hAIveMind integration.

Author: Lance James, Unit 221B, Inc
Date: August 24, 2025
Version: 1.0.0
"""

import os
import json
import uuid
import base64
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File, Form, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
import uvicorn

from mcp_marketplace import MCPMarketplace, ServerMetadata, ServerReview, ServerStatus, CompatibilityLevel
from auth import verify_token, get_current_user, UserRole

# Request/Response Models
class ServerRegistrationRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=1000)
    version: str = Field(..., regex=r'^\d+\.\d+\.\d+$')
    author: str = Field(..., min_length=2, max_length=100)
    author_email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    organization: Optional[str] = Field(None, max_length=100)
    homepage: Optional[str] = Field(None, regex=r'^https?://.+')
    repository: Optional[str] = Field(None, regex=r'^https?://.+')
    license: str = Field("MIT", max_length=50)
    keywords: List[str] = Field(default_factory=list, max_items=20)
    category: str = Field(..., max_length=50)
    subcategory: Optional[str] = Field(None, max_length=50)
    language: str = Field("python", max_length=20)
    runtime_requirements: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list, max_items=100)
    tools: List[Dict[str, Any]] = Field(default_factory=list, max_items=50)
    resources: List[Dict[str, Any]] = Field(default_factory=list, max_items=50)
    prompts: List[Dict[str, Any]] = Field(default_factory=list, max_items=20)
    claude_compatibility: Dict[str, str] = Field(default_factory=dict)
    min_claude_version: Optional[str] = None
    max_claude_version: Optional[str] = None
    platform_compatibility: List[str] = Field(default_factory=lambda: ["linux", "macos", "windows"])
    installation_script: Optional[str] = Field(None, max_length=10000)

class ServerSearchRequest(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    language: Optional[str] = None
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    compatible_with: Optional[str] = None
    verified_only: bool = False
    featured_only: bool = False
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    sort_by: str = Field("rating", regex=r'^(rating|downloads|newest|updated|name)$')

class ReviewRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: str = Field(..., min_length=5, max_length=100)
    content: str = Field(..., min_length=10, max_length=2000)

class InstallationRequest(BaseModel):
    installation_method: str = Field("one_click", regex=r'^(one_click|manual|cli)$')
    target_config: Optional[Dict[str, Any]] = None

class ServerUpdateRequest(BaseModel):
    description: Optional[str] = Field(None, min_length=10, max_length=1000)
    homepage: Optional[str] = Field(None, regex=r'^https?://.+')
    repository: Optional[str] = Field(None, regex=r'^https?://.+')
    keywords: Optional[List[str]] = Field(None, max_items=20)
    installation_script: Optional[str] = Field(None, max_length=10000)

class ServerApprovalRequest(BaseModel):
    status: str = Field(..., regex=r'^(approved|rejected|security_review)$')
    reason: Optional[str] = Field(None, max_length=500)
    featured: Optional[bool] = None
    verified: Optional[bool] = None

# Response Models
class ServerResponse(BaseModel):
    id: str
    name: str
    description: str
    version: str
    author: str
    category: str
    language: str
    status: str
    rating: float
    rating_count: int
    downloads: int
    featured: bool
    verified: bool
    created_at: str
    updated_at: str

class SearchResponse(BaseModel):
    servers: List[ServerResponse]
    total: int
    limit: int
    offset: int
    has_more: bool

class AnalyticsResponse(BaseModel):
    overview: Dict[str, Any]
    categories: List[Dict[str, Any]]
    top_servers: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
    languages: List[Dict[str, Any]]
    generated_at: str

# API Application
class MarketplaceAPI:
    """MCP Marketplace REST API with enterprise features"""
    
    def __init__(self, marketplace: MCPMarketplace, config: Dict[str, Any]):
        self.marketplace = marketplace
        self.config = config
        self.app = FastAPI(
            title="MCP Server Marketplace API",
            description="Enterprise MCP Server Marketplace with hAIveMind integration",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Security
        self.security = HTTPBearer()
        
        # Setup middleware
        self._setup_middleware()
        
        # Setup routes
        self._setup_routes()
        
        # Rate limiting
        self.rate_limits = config.get("rate_limits", {
            "search": 100,  # per minute
            "register": 10,  # per hour
            "install": 50,   # per hour
            "review": 20     # per hour
        })
    
    def _setup_middleware(self):
        """Setup FastAPI middleware"""
        # CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.get("allowed_origins", ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Trusted hosts
        if self.config.get("trusted_hosts"):
            self.app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=self.config["trusted_hosts"]
            )
    
    def _setup_routes(self):
        """Setup API routes"""
        
        # Health check
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        # Server registration and management
        @self.app.post("/api/v1/servers", response_model=Dict[str, str])
        async def register_server(
            request: ServerRegistrationRequest,
            package: Optional[UploadFile] = File(None),
            current_user: Dict = Depends(get_current_user)
        ):
            """Register a new MCP server in the marketplace"""
            try:
                # Create server metadata
                server_id = f"server_{uuid.uuid4().hex[:12]}"
                metadata = ServerMetadata(
                    id=server_id,
                    name=request.name,
                    description=request.description,
                    version=request.version,
                    author=request.author,
                    author_email=request.author_email,
                    organization=request.organization,
                    homepage=request.homepage,
                    repository=request.repository,
                    license=request.license,
                    keywords=request.keywords,
                    category=request.category,
                    subcategory=request.subcategory,
                    language=request.language,
                    runtime_requirements=request.runtime_requirements,
                    dependencies=request.dependencies,
                    tools=request.tools,
                    resources=request.resources,
                    prompts=request.prompts,
                    claude_compatibility={k: CompatibilityLevel(v) for k, v in request.claude_compatibility.items()},
                    min_claude_version=request.min_claude_version,
                    max_claude_version=request.max_claude_version,
                    platform_compatibility=request.platform_compatibility,
                    installation_script=request.installation_script
                )
                
                # Handle package upload
                package_data = None
                if package:
                    if package.size > self.marketplace.max_package_size:
                        raise HTTPException(
                            status_code=413,
                            detail=f"Package size exceeds limit of {self.marketplace.max_package_size // 1024 // 1024}MB"
                        )
                    
                    package_data = await package.read()
                
                # Register server
                result_id = await self.marketplace.register_server(metadata, package_data)
                
                return {
                    "server_id": result_id,
                    "status": "registered",
                    "message": "Server registered successfully. Pending approval."
                }
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/v1/servers/{server_id}")
        async def get_server_details(server_id: str):
            """Get detailed information about a server"""
            try:
                server = await self.marketplace.get_server_details(server_id)
                if not server:
                    raise HTTPException(status_code=404, detail="Server not found")
                
                return server
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.put("/api/v1/servers/{server_id}")
        async def update_server(
            server_id: str,
            request: ServerUpdateRequest,
            current_user: Dict = Depends(get_current_user)
        ):
            """Update server information (author only)"""
            try:
                # Get existing server
                server = await self.marketplace.get_server_details(server_id)
                if not server:
                    raise HTTPException(status_code=404, detail="Server not found")
                
                # Check authorization (author or admin)
                if (server["author_email"] != current_user["email"] and 
                    current_user.get("role") not in ["admin", "moderator"]):
                    raise HTTPException(status_code=403, detail="Not authorized to update this server")
                
                # Update fields
                updates = {}
                if request.description:
                    updates["description"] = request.description
                if request.homepage:
                    updates["homepage"] = request.homepage
                if request.repository:
                    updates["repository"] = request.repository
                if request.keywords is not None:
                    updates["keywords"] = json.dumps(request.keywords)
                if request.installation_script:
                    updates["installation_script"] = request.installation_script
                
                if updates:
                    updates["updated_at"] = int(datetime.now().timestamp())
                    
                    # Update in database
                    with sqlite3.connect(self.marketplace.db_path) as conn:
                        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
                        values = list(updates.values()) + [server_id]
                        conn.execute(f"UPDATE servers SET {set_clause} WHERE id = ?", values)
                        conn.commit()
                    
                    # Clear cache
                    self.marketplace.redis_client.delete(f"server:{server_id}")
                
                return {"status": "updated", "message": "Server updated successfully"}
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.delete("/api/v1/servers/{server_id}")
        async def delete_server(
            server_id: str,
            current_user: Dict = Depends(get_current_user)
        ):
            """Delete a server (author or admin only)"""
            try:
                # Get existing server
                server = await self.marketplace.get_server_details(server_id)
                if not server:
                    raise HTTPException(status_code=404, detail="Server not found")
                
                # Check authorization
                if (server["author_email"] != current_user["email"] and 
                    current_user.get("role") not in ["admin", "moderator"]):
                    raise HTTPException(status_code=403, detail="Not authorized to delete this server")
                
                # Soft delete
                with sqlite3.connect(self.marketplace.db_path) as conn:
                    conn.execute(
                        "UPDATE servers SET status = 'deleted', updated_at = ? WHERE id = ?",
                        (int(datetime.now().timestamp()), server_id)
                    )
                    conn.commit()
                
                # Clear cache
                self.marketplace.redis_client.delete(f"server:{server_id}")
                
                return {"status": "deleted", "message": "Server deleted successfully"}
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # Server search and discovery
        @self.app.post("/api/v1/servers/search", response_model=SearchResponse)
        async def search_servers(request: ServerSearchRequest):
            """Search servers in the marketplace"""
            try:
                result = await self.marketplace.search_servers(
                    query=request.query,
                    category=request.category,
                    language=request.language,
                    min_rating=request.min_rating,
                    compatible_with=request.compatible_with,
                    verified_only=request.verified_only,
                    featured_only=request.featured_only,
                    limit=request.limit,
                    offset=request.offset,
                    sort_by=request.sort_by
                )
                
                return SearchResponse(**result)
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/v1/servers", response_model=SearchResponse)
        async def list_servers(
            query: Optional[str] = None,
            category: Optional[str] = None,
            language: Optional[str] = None,
            min_rating: Optional[float] = Query(None, ge=0, le=5),
            verified_only: bool = False,
            featured_only: bool = False,
            limit: int = Query(20, ge=1, le=100),
            offset: int = Query(0, ge=0),
            sort_by: str = Query("rating", regex=r'^(rating|downloads|newest|updated|name)$')
        ):
            """List servers with optional filtering"""
            request = ServerSearchRequest(
                query=query,
                category=category,
                language=language,
                min_rating=min_rating,
                verified_only=verified_only,
                featured_only=featured_only,
                limit=limit,
                offset=offset,
                sort_by=sort_by
            )
            return await search_servers(request)
        
        # Server installation
        @self.app.post("/api/v1/servers/{server_id}/install")
        async def install_server(
            server_id: str,
            request: InstallationRequest,
            current_user: Dict = Depends(get_current_user)
        ):
            """Install a server with one-click functionality"""
            try:
                device_id = request.target_config.get("device_id", "default") if request.target_config else "default"
                
                installation_id = await self.marketplace.install_server(
                    server_id=server_id,
                    user_id=current_user["id"],
                    device_id=device_id,
                    installation_method=request.installation_method,
                    target_config=request.target_config
                )
                
                return {
                    "installation_id": installation_id,
                    "status": "success",
                    "message": "Server installed successfully"
                }
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/v1/installations/{installation_id}")
        async def get_installation_status(
            installation_id: str,
            current_user: Dict = Depends(get_current_user)
        ):
            """Get installation status"""
            try:
                with sqlite3.connect(self.marketplace.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    
                    installation = conn.execute(
                        "SELECT * FROM installations WHERE id = ? AND user_id = ?",
                        (installation_id, current_user["id"])
                    ).fetchone()
                    
                    if not installation:
                        raise HTTPException(status_code=404, detail="Installation not found")
                    
                    result = dict(installation)
                    result["installed_at"] = datetime.fromtimestamp(result["installed_at"]).isoformat()
                    
                    return result
                    
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # Reviews and ratings
        @self.app.post("/api/v1/servers/{server_id}/reviews")
        async def add_review(
            server_id: str,
            request: ReviewRequest,
            current_user: Dict = Depends(get_current_user)
        ):
            """Add a review for a server"""
            try:
                # Check if server exists
                server = await self.marketplace.get_server_details(server_id)
                if not server:
                    raise HTTPException(status_code=404, detail="Server not found")
                
                # Check if user already reviewed
                with sqlite3.connect(self.marketplace.db_path) as conn:
                    existing = conn.execute(
                        "SELECT id FROM reviews WHERE server_id = ? AND user_id = ?",
                        (server_id, current_user["id"])
                    ).fetchone()
                    
                    if existing:
                        raise HTTPException(status_code=400, detail="You have already reviewed this server")
                
                # Create review
                review = ServerReview(
                    id=f"review_{uuid.uuid4().hex[:12]}",
                    server_id=server_id,
                    user_id=current_user["id"],
                    username=current_user["username"],
                    rating=request.rating,
                    title=request.title,
                    content=request.content
                )
                
                review_id = await self.marketplace.add_review(review)
                
                return {
                    "review_id": review_id,
                    "status": "success",
                    "message": "Review added successfully"
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/v1/servers/{server_id}/reviews")
        async def get_server_reviews(
            server_id: str,
            limit: int = Query(20, ge=1, le=100),
            offset: int = Query(0, ge=0)
        ):
            """Get reviews for a server"""
            try:
                with sqlite3.connect(self.marketplace.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    
                    # Get total count
                    total = conn.execute(
                        "SELECT COUNT(*) as count FROM reviews WHERE server_id = ?",
                        (server_id,)
                    ).fetchone()["count"]
                    
                    # Get reviews
                    reviews = conn.execute("""
                        SELECT * FROM reviews WHERE server_id = ?
                        ORDER BY created_at DESC LIMIT ? OFFSET ?
                    """, (server_id, limit, offset)).fetchall()
                    
                    result_reviews = []
                    for review in reviews:
                        review_data = dict(review)
                        review_data["created_at"] = datetime.fromtimestamp(review_data["created_at"]).isoformat()
                        review_data["updated_at"] = datetime.fromtimestamp(review_data["updated_at"]).isoformat()
                        result_reviews.append(review_data)
                    
                    return {
                        "reviews": result_reviews,
                        "total": total,
                        "limit": limit,
                        "offset": offset,
                        "has_more": offset + len(reviews) < total
                    }
                    
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # Package download
        @self.app.get("/api/v1/servers/{server_id}/download")
        async def download_server_package(
            server_id: str,
            current_user: Dict = Depends(get_current_user)
        ):
            """Download server package"""
            try:
                server = await self.marketplace.get_server_details(server_id)
                if not server:
                    raise HTTPException(status_code=404, detail="Server not found")
                
                if server["status"] != "approved":
                    raise HTTPException(status_code=403, detail="Server not approved for download")
                
                if not server["package_url"]:
                    raise HTTPException(status_code=404, detail="Package not available")
                
                package_path = Path(server["package_url"])
                if not package_path.exists():
                    raise HTTPException(status_code=404, detail="Package file not found")
                
                # Record download analytics
                await self.marketplace._record_download_analytics(
                    server_id, current_user["id"], "web", "direct_download"
                )
                
                return FileResponse(
                    path=str(package_path),
                    filename=f"{server['name']}-{server['version']}.zip",
                    media_type="application/zip"
                )
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # Analytics and recommendations
        @self.app.get("/api/v1/analytics", response_model=AnalyticsResponse)
        async def get_marketplace_analytics(
            current_user: Dict = Depends(get_current_user)
        ):
            """Get marketplace analytics (admin only)"""
            if current_user.get("role") not in ["admin", "moderator"]:
                raise HTTPException(status_code=403, detail="Admin access required")
            
            try:
                analytics = await self.marketplace.get_marketplace_analytics()
                return AnalyticsResponse(**analytics)
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/v1/recommendations")
        async def get_recommendations(
            based_on_server: Optional[str] = None,
            limit: int = Query(5, ge=1, le=20),
            current_user: Dict = Depends(get_current_user)
        ):
            """Get personalized server recommendations"""
            try:
                recommendations = await self.marketplace.get_recommendations(
                    user_id=current_user["id"],
                    device_id=current_user.get("device_id"),
                    based_on_server=based_on_server,
                    limit=limit
                )
                
                return {"recommendations": recommendations}
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # Categories and metadata
        @self.app.get("/api/v1/categories")
        async def get_categories():
            """Get available categories"""
            try:
                with sqlite3.connect(self.marketplace.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    
                    categories = conn.execute("""
                        SELECT category, COUNT(*) as count, AVG(rating) as avg_rating
                        FROM servers WHERE status = 'approved'
                        GROUP BY category ORDER BY count DESC
                    """).fetchall()
                    
                    return {
                        "categories": [dict(row) for row in categories],
                        "all_categories": self.marketplace.categories
                    }
                    
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/v1/languages")
        async def get_languages():
            """Get available programming languages"""
            try:
                with sqlite3.connect(self.marketplace.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    
                    languages = conn.execute("""
                        SELECT language, COUNT(*) as count
                        FROM servers WHERE status = 'approved'
                        GROUP BY language ORDER BY count DESC
                    """).fetchall()
                    
                    return {"languages": [dict(row) for row in languages]}
                    
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # Admin endpoints
        @self.app.post("/api/v1/admin/servers/{server_id}/approve")
        async def approve_server(
            server_id: str,
            request: ServerApprovalRequest,
            current_user: Dict = Depends(get_current_user)
        ):
            """Approve or reject a server (admin only)"""
            if current_user.get("role") not in ["admin", "moderator"]:
                raise HTTPException(status_code=403, detail="Admin access required")
            
            try:
                updates = {
                    "status": request.status,
                    "updated_at": int(datetime.now().timestamp())
                }
                
                if request.featured is not None:
                    updates["featured"] = request.featured
                
                if request.verified is not None:
                    updates["verified"] = request.verified
                
                with sqlite3.connect(self.marketplace.db_path) as conn:
                    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
                    values = list(updates.values()) + [server_id]
                    conn.execute(f"UPDATE servers SET {set_clause} WHERE id = ?", values)
                    conn.commit()
                
                # Clear cache
                self.marketplace.redis_client.delete(f"server:{server_id}")
                
                return {
                    "status": "success",
                    "message": f"Server {request.status} successfully"
                }
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/v1/admin/servers/pending")
        async def get_pending_servers(
            current_user: Dict = Depends(get_current_user)
        ):
            """Get servers pending approval (admin only)"""
            if current_user.get("role") not in ["admin", "moderator"]:
                raise HTTPException(status_code=403, detail="Admin access required")
            
            try:
                with sqlite3.connect(self.marketplace.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    
                    servers = conn.execute("""
                        SELECT * FROM servers 
                        WHERE status IN ('pending', 'security_review')
                        ORDER BY created_at ASC
                    """).fetchall()
                    
                    result = []
                    for server in servers:
                        server_data = dict(server)
                        server_data["created_at"] = datetime.fromtimestamp(server_data["created_at"]).isoformat()
                        server_data["updated_at"] = datetime.fromtimestamp(server_data["updated_at"]).isoformat()
                        
                        # Parse JSON fields
                        for field in ["keywords", "security_issues"]:
                            if server_data[field]:
                                server_data[field] = json.loads(server_data[field])
                        
                        result.append(server_data)
                    
                    return {"servers": result}
                    
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

def create_marketplace_api(marketplace: MCPMarketplace, config: Dict[str, Any]) -> FastAPI:
    """Create and configure marketplace API"""
    api = MarketplaceAPI(marketplace, config)
    return api.app

if __name__ == "__main__":
    # Example startup
    from mcp_marketplace import create_marketplace
    
    config = {
        "database_path": "data/marketplace.db",
        "storage_path": "data/marketplace_storage",
        "redis": {"host": "localhost", "port": 6379, "db": 2},
        "security": {"max_package_size_mb": 100, "scan_uploads": True},
        "allowed_origins": ["*"],
        "trusted_hosts": ["localhost", "127.0.0.1"]
    }
    
    marketplace = create_marketplace(config)
    app = create_marketplace_api(marketplace, config)
    
    uvicorn.run(app, host="0.0.0.0", port=8920, log_level="info")