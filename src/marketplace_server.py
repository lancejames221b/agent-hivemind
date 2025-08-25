#!/usr/bin/env python3
"""
MCP Marketplace Server - Complete Integration
Main server that integrates all marketplace components with hAIveMind awareness,
providing a comprehensive marketplace platform for MCP servers.

Author: Lance James, Unit 221B, Inc
Date: August 24, 2025
Version: 1.0.0
"""

import os
import json
import asyncio
import uvicorn
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Import all marketplace components
from mcp_marketplace import create_marketplace
from marketplace_api import create_marketplace_api
from marketplace_installer import create_marketplace_installer
from marketplace_templates import create_marketplace_templates
from compatibility_matrix import create_compatibility_matrix
from marketplace_import_export import create_import_export_system
from marketplace_mcp_tools import get_marketplace_tools

# Import hAIveMind components
try:
    from memory_server import store_memory, search_memories
    from remote_mcp_server import FastMCPServer
    HAIVEMIND_AVAILABLE = True
except ImportError:
    HAIVEMIND_AVAILABLE = False

class MarketplaceServer:
    """
    Complete MCP Marketplace Server with hAIveMind integration
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.marketplace_config = config.get("marketplace", {})
        
        # Initialize core components
        self.marketplace = create_marketplace(self.marketplace_config)
        self.installer = create_marketplace_installer(config.get("installer", {}))
        self.templates = create_marketplace_templates(config.get("templates", {}))
        self.compatibility = create_compatibility_matrix(config.get("compatibility", {}))
        self.import_export = create_import_export_system(self.marketplace, config.get("import_export", {}))
        
        # Create FastAPI app
        self.app = create_marketplace_api(self.marketplace, config.get("api", {}))
        
        # Add marketplace-specific routes
        self._setup_additional_routes()
        
        # Setup static files
        self._setup_static_files()
        
        # Initialize hAIveMind integration
        self.haivemind_enabled = HAIVEMIND_AVAILABLE and config.get("haivemind_integration", True)
        if self.haivemind_enabled:
            self._setup_haivemind_integration()
        
        # Background tasks
        self.background_tasks = []
        
        # Start background services
        if config.get("auto_start_services", True):
            self._schedule_background_tasks()
    
    def _setup_additional_routes(self):
        """Setup additional marketplace routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def marketplace_home():
            """Serve marketplace homepage"""
            return FileResponse("admin/marketplace.html")
        
        @self.app.get("/docs-viewer", response_class=HTMLResponse)
        async def documentation_viewer():
            """Serve documentation viewer"""
            return FileResponse("admin/documentation_viewer.html")
        
        # Template management endpoints
        @self.app.get("/api/v1/templates")
        async def list_templates():
            """List all available server templates"""
            try:
                templates = self.templates.list_templates()
                return {
                    "success": True,
                    "templates": templates,
                    "total": len(templates)
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/templates/{template_id}")
        async def get_template(template_id: str):
            """Get specific template details"""
            try:
                template = self.templates.get_template(template_id)
                if not template:
                    raise HTTPException(status_code=404, detail="Template not found")
                
                return {
                    "success": True,
                    "template": {
                        "id": template_id,
                        "name": template.name,
                        "description": template.description,
                        "language": template.language,
                        "category": template.category,
                        "files": list(template.files.keys()),
                        "metadata": template.metadata
                    }
                }
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/templates/{template_id}/generate")
        async def generate_template_package(template_id: str):
            """Generate a package from a template"""
            try:
                package_path = self.templates.generate_template_package(template_id)
                if not package_path:
                    raise HTTPException(status_code=404, detail="Template not found")
                
                return FileResponse(
                    path=str(package_path),
                    filename=f"{template_id}_template.zip",
                    media_type="application/zip"
                )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Compatibility endpoints
        @self.app.get("/api/v1/compatibility/{server_id}")
        async def get_compatibility_matrix(server_id: str):
            """Get compatibility matrix for a server"""
            try:
                matrix = await self.compatibility.get_compatibility_matrix(server_id)
                return {
                    "success": True,
                    "compatibility_matrix": matrix
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/compatibility/{server_id}/test")
        async def test_server_compatibility(server_id: str, background_tasks: BackgroundTasks):
            """Test server compatibility"""
            try:
                # Get server details
                server = await self.marketplace.get_server_details(server_id)
                if not server:
                    raise HTTPException(status_code=404, detail="Server not found")
                
                # Start compatibility testing in background
                background_tasks.add_task(
                    self._run_compatibility_test, 
                    server_id, 
                    server.get("package_url")
                )
                
                return {
                    "success": True,
                    "message": "Compatibility testing started",
                    "server_id": server_id
                }
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Import/Export endpoints
        @self.app.post("/api/v1/export")
        async def export_servers(export_request: Dict[str, Any]):
            """Export servers"""
            try:
                from marketplace_import_export import ExportConfig
                
                export_config = ExportConfig(
                    format=export_request.get("format", "json"),
                    include_metadata=export_request.get("include_metadata", True),
                    include_reviews=export_request.get("include_reviews", False),
                    include_analytics=export_request.get("include_analytics", False),
                    include_packages=export_request.get("include_packages", False)
                )
                
                result = await self.import_export.export_servers(
                    server_ids=export_request.get("server_ids"),
                    export_config=export_config
                )
                
                return result
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/import")
        async def import_servers(import_request: Dict[str, Any]):
            """Import servers"""
            try:
                from marketplace_import_export import ImportConfig
                
                import_config = ImportConfig(
                    format=import_request.get("format", "json"),
                    validate_schema=import_request.get("validate_schema", True),
                    merge_strategy=import_request.get("merge_strategy", "update"),
                    auto_approve=import_request.get("auto_approve", False),
                    backup_existing=import_request.get("backup_existing", True)
                )
                
                result = await self.import_export.import_servers(
                    file_path=import_request["file_path"],
                    import_config=import_config
                )
                
                return result
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # hAIveMind integration endpoints
        if self.haivemind_enabled:
            @self.app.get("/api/v1/haivemind/recommendations/{user_id}")
            async def get_haivemind_recommendations(user_id: str):
                """Get AI-powered recommendations from hAIveMind"""
                try:
                    recommendations = await self._get_haivemind_recommendations(user_id)
                    return {
                        "success": True,
                        "recommendations": recommendations,
                        "generated_at": datetime.now().isoformat()
                    }
                except Exception as e:
                    raise HTTPException(status_code=500, detail=str(e))
            
            @self.app.get("/api/v1/haivemind/analytics")
            async def get_haivemind_analytics():
                """Get marketplace analytics from hAIveMind"""
                try:
                    analytics = await self._get_haivemind_analytics()
                    return {
                        "success": True,
                        "analytics": analytics,
                        "generated_at": datetime.now().isoformat()
                    }
                except Exception as e:
                    raise HTTPException(status_code=500, detail=str(e))
    
    def _setup_static_files(self):
        """Setup static file serving"""
        # Mount admin interface
        admin_path = Path("admin")
        if admin_path.exists():
            self.app.mount("/admin", StaticFiles(directory="admin"), name="admin")
        
        # Mount assets directory
        assets_path = Path("assets")
        if assets_path.exists():
            self.app.mount("/assets", StaticFiles(directory="assets"), name="assets")
        
        # Mount documentation assets
        docs_path = Path("docs")
        if docs_path.exists():
            self.app.mount("/docs", StaticFiles(directory="docs"), name="docs")
    
    def _setup_haivemind_integration(self):
        """Setup hAIveMind integration"""
        if not HAIVEMIND_AVAILABLE:
            return
        
        # Register marketplace tools with hAIveMind
        self.mcp_tools = get_marketplace_tools(self.marketplace)
        
        # Setup MCP server for hAIveMind integration
        self.mcp_server = FastMCPServer("marketplace-server")
        
        # Register all marketplace tools
        for tool_name, tool_func in self.mcp_tools.items():
            self.mcp_server.tool(tool_name)(tool_func)
        
        # Add marketplace-specific resources
        @self.mcp_server.resource("marketplace://status")
        async def marketplace_status():
            """Get marketplace status"""
            analytics = await self.marketplace.get_marketplace_analytics()
            return json.dumps({
                "status": "operational",
                "servers": analytics["overview"]["total_servers"],
                "approved_servers": analytics["overview"]["approved_servers"],
                "total_downloads": analytics["overview"]["total_downloads"],
                "average_rating": analytics["overview"]["average_rating"],
                "last_updated": datetime.now().isoformat()
            }, indent=2)
        
        @self.mcp_server.resource("marketplace://categories")
        async def marketplace_categories():
            """Get marketplace categories"""
            analytics = await self.marketplace.get_marketplace_analytics()
            return json.dumps({
                "categories": analytics["categories"],
                "total_categories": len(analytics["categories"])
            }, indent=2)
    
    def _schedule_background_tasks(self):
        """Schedule background tasks"""
        # Analytics collection
        if self.config.get("collect_analytics", True):
            self.background_tasks.append(
                asyncio.create_task(self._analytics_collection_loop())
            )
        
        # Compatibility testing
        if self.config.get("auto_compatibility_testing", True):
            self.background_tasks.append(
                asyncio.create_task(self._compatibility_testing_loop())
            )
        
        # hAIveMind sync
        if self.haivemind_enabled and self.config.get("haivemind_sync", True):
            self.background_tasks.append(
                asyncio.create_task(self._haivemind_sync_loop())
            )
    
    async def _analytics_collection_loop(self):
        """Background task for analytics collection"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Collect marketplace analytics
                analytics = await self.marketplace.get_marketplace_analytics()
                
                # Store in hAIveMind if available
                if self.haivemind_enabled:
                    await store_memory(
                        content=f"Marketplace analytics collected: {analytics['overview']['total_servers']} servers, {analytics['overview']['total_downloads']} downloads",
                        category="marketplace",
                        metadata={
                            "action": "analytics_collected",
                            "analytics": analytics["overview"],
                            "timestamp": datetime.now().isoformat()
                        },
                        project="mcp-marketplace",
                        scope="project-shared"
                    )
                
            except Exception as e:
                print(f"Analytics collection error: {e}")
    
    async def _compatibility_testing_loop(self):
        """Background task for compatibility testing"""
        while True:
            try:
                await asyncio.sleep(86400)  # Run daily
                
                # Get servers that need compatibility testing
                search_result = await self.marketplace.search_servers(limit=100)
                servers = search_result["servers"]
                
                for server in servers:
                    if server.get("package_url"):
                        try:
                            await self._run_compatibility_test(server["id"], server["package_url"])
                        except Exception as e:
                            print(f"Compatibility test error for {server['id']}: {e}")
                
            except Exception as e:
                print(f"Compatibility testing loop error: {e}")
    
    async def _haivemind_sync_loop(self):
        """Background task for hAIveMind synchronization"""
        if not self.haivemind_enabled:
            return
        
        while True:
            try:
                await asyncio.sleep(1800)  # Run every 30 minutes
                
                # Sync marketplace insights
                await self._sync_marketplace_insights()
                
                # Update recommendations
                await self._update_recommendations()
                
            except Exception as e:
                print(f"hAIveMind sync error: {e}")
    
    async def _run_compatibility_test(self, server_id: str, package_path: str):
        """Run compatibility test for a server"""
        try:
            if package_path and Path(package_path).exists():
                result = await self.compatibility.test_server_compatibility(
                    server_id, package_path
                )
                
                # Store results in hAIveMind
                if self.haivemind_enabled:
                    await store_memory(
                        content=f"Compatibility test completed for {server_id}: score {result.get('overall_score', 0):.2f}",
                        category="marketplace",
                        metadata={
                            "action": "compatibility_test_completed",
                            "server_id": server_id,
                            "test_results": result,
                            "timestamp": datetime.now().isoformat()
                        },
                        project="mcp-marketplace",
                        scope="project-shared"
                    )
        except Exception as e:
            print(f"Compatibility test failed for {server_id}: {e}")
    
    async def _get_haivemind_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get AI-powered recommendations from hAIveMind"""
        if not self.haivemind_enabled:
            return []
        
        try:
            # Search for user's interaction patterns
            user_memories = await search_memories(
                query=f"user:{user_id}",
                category="marketplace",
                limit=50
            )
            
            # Analyze patterns and generate recommendations
            recommendations = []
            
            # Get popular servers in user's categories of interest
            categories_of_interest = set()
            for memory in user_memories.get("memories", []):
                metadata = memory.get("metadata", {})
                if "category" in metadata:
                    categories_of_interest.add(metadata["category"])
            
            for category in categories_of_interest:
                search_result = await self.marketplace.search_servers(
                    category=category,
                    sort_by="rating",
                    limit=3
                )
                
                for server in search_result["servers"]:
                    recommendations.append({
                        "server_id": server["id"],
                        "name": server["name"],
                        "description": server["description"],
                        "rating": server["rating"],
                        "reason": f"Popular in {category} category",
                        "confidence": 0.8
                    })
            
            return recommendations[:10]  # Limit to top 10
            
        except Exception as e:
            print(f"hAIveMind recommendations error: {e}")
            return []
    
    async def _get_haivemind_analytics(self) -> Dict[str, Any]:
        """Get marketplace analytics from hAIveMind"""
        if not self.haivemind_enabled:
            return {}
        
        try:
            # Search for marketplace memories
            memories = await search_memories(
                query="marketplace",
                category="marketplace",
                limit=1000
            )
            
            # Analyze patterns
            analytics = {
                "total_interactions": len(memories.get("memories", [])),
                "popular_actions": {},
                "trending_categories": {},
                "user_patterns": {},
                "performance_insights": []
            }
            
            # Count actions
            for memory in memories.get("memories", []):
                metadata = memory.get("metadata", {})
                action = metadata.get("action", "unknown")
                analytics["popular_actions"][action] = analytics["popular_actions"].get(action, 0) + 1
                
                category = metadata.get("category")
                if category:
                    analytics["trending_categories"][category] = analytics["trending_categories"].get(category, 0) + 1
            
            return analytics
            
        except Exception as e:
            print(f"hAIveMind analytics error: {e}")
            return {}
    
    async def _sync_marketplace_insights(self):
        """Sync marketplace insights with hAIveMind"""
        try:
            # Get current marketplace state
            analytics = await self.marketplace.get_marketplace_analytics()
            
            # Store insights
            await store_memory(
                content=f"Marketplace insights: {analytics['overview']['total_servers']} servers, avg rating {analytics['overview']['average_rating']:.2f}",
                category="marketplace",
                metadata={
                    "action": "insights_sync",
                    "insights": {
                        "server_growth": analytics["overview"]["total_servers"],
                        "quality_trend": analytics["overview"]["average_rating"],
                        "popular_categories": [cat["category"] for cat in analytics["categories"][:5]],
                        "download_trend": analytics["overview"]["total_downloads"]
                    },
                    "timestamp": datetime.now().isoformat()
                },
                project="mcp-marketplace",
                scope="project-shared"
            )
            
        except Exception as e:
            print(f"Insights sync error: {e}")
    
    async def _update_recommendations(self):
        """Update recommendation models based on marketplace data"""
        try:
            # This would implement ML-based recommendation updates
            # For now, just log the activity
            await store_memory(
                content="Recommendation models updated based on latest marketplace activity",
                category="marketplace",
                metadata={
                    "action": "recommendations_updated",
                    "timestamp": datetime.now().isoformat()
                },
                project="mcp-marketplace",
                scope="project-shared"
            )
            
        except Exception as e:
            print(f"Recommendations update error: {e}")
    
    async def start(self):
        """Start the marketplace server"""
        try:
            # Store startup event in hAIveMind
            if self.haivemind_enabled:
                await store_memory(
                    content="MCP Marketplace server started successfully",
                    category="marketplace",
                    metadata={
                        "action": "server_started",
                        "components": [
                            "marketplace_core",
                            "api_server", 
                            "installer",
                            "templates",
                            "compatibility_matrix",
                            "import_export",
                            "haivemind_integration" if self.haivemind_enabled else None
                        ],
                        "timestamp": datetime.now().isoformat()
                    },
                    project="mcp-marketplace",
                    scope="project-shared"
                )
            
            print("🚀 MCP Marketplace Server started successfully!")
            print(f"📊 Dashboard: http://localhost:{self.config.get('port', 8920)}/")
            print(f"📚 Documentation: http://localhost:{self.config.get('port', 8920)}/docs-viewer")
            print(f"🔧 API Docs: http://localhost:{self.config.get('port', 8920)}/docs")
            
        except Exception as e:
            print(f"Failed to start marketplace server: {e}")
            raise
    
    async def stop(self):
        """Stop the marketplace server"""
        try:
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
            
            # Store shutdown event in hAIveMind
            if self.haivemind_enabled:
                await store_memory(
                    content="MCP Marketplace server stopped",
                    category="marketplace",
                    metadata={
                        "action": "server_stopped",
                        "timestamp": datetime.now().isoformat()
                    },
                    project="mcp-marketplace",
                    scope="project-shared"
                )
            
            print("🛑 MCP Marketplace Server stopped")
            
        except Exception as e:
            print(f"Error stopping marketplace server: {e}")

def create_marketplace_server(config: Dict[str, Any]) -> MarketplaceServer:
    """Create and configure marketplace server"""
    return MarketplaceServer(config)

async def main():
    """Main entry point"""
    # Load configuration
    config_path = Path("config/marketplace_config.json")
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        # Default configuration
        config = {
            "host": "0.0.0.0",
            "port": 8920,
            "marketplace": {
                "database_path": "data/marketplace.db",
                "storage_path": "data/marketplace_storage",
                "redis": {
                    "host": "localhost",
                    "port": 6379,
                    "db": 2
                },
                "security": {
                    "max_package_size_mb": 100,
                    "scan_uploads": True
                },
                "haivemind_integration": True
            },
            "api": {
                "allowed_origins": ["*"],
                "trusted_hosts": ["localhost", "127.0.0.1"]
            },
            "installer": {
                "install_directory": "data/marketplace_installs",
                "use_mcp_hosting": True,
                "auto_generate_config": True
            },
            "templates": {
                "templates_directory": "templates/marketplace"
            },
            "compatibility": {
                "database_path": "data/compatibility.db",
                "auto_test": True,
                "test_timeout": 60
            },
            "import_export": {
                "export_directory": "data/marketplace_exports",
                "import_directory": "data/marketplace_imports",
                "backup_directory": "data/marketplace_backups"
            },
            "haivemind_integration": True,
            "auto_start_services": True,
            "collect_analytics": True,
            "auto_compatibility_testing": True,
            "haivemind_sync": True
        }
    
    # Create and start server
    server = create_marketplace_server(config)
    await server.start()
    
    # Run with uvicorn
    uvicorn_config = uvicorn.Config(
        server.app,
        host=config.get("host", "0.0.0.0"),
        port=config.get("port", 8920),
        log_level="info"
    )
    
    uvicorn_server = uvicorn.Server(uvicorn_config)
    
    try:
        await uvicorn_server.serve()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down marketplace server...")
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())