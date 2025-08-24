#!/usr/bin/env python3
"""
Confluence Dashboard Integration

Provides web dashboard endpoints for managing Confluence integration.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from confluence_integration import ConfluenceIntegration, ConfluenceError
from confluence_mcp_tools import ConfluenceMCPTools
from confluence_sync_service import ConfluenceSyncScheduler

logger = logging.getLogger(__name__)

# Pydantic models for API requests
class ConfluenceConfigRequest(BaseModel):
    url: str
    username: str
    api_token: str
    spaces: List[str]
    enabled: bool = True

class ConfluenceImportRequest(BaseModel):
    page_id: str
    force_update: bool = False

class ConfluenceBulkImportRequest(BaseModel):
    space_key: str
    force_update: bool = False

class ConfluenceSyncRequest(BaseModel):
    max_age_hours: int = 24

class ConfluenceDashboard:
    """Dashboard integration for Confluence management"""
    
    def __init__(self, config: Dict[str, Any], database, haivemind_storage=None):
        self.config = config
        self.database = database
        self.haivemind_storage = haivemind_storage
        
        # Initialize components
        self.mcp_tools = ConfluenceMCPTools(config, database, haivemind_storage)
        self.sync_scheduler = ConfluenceSyncScheduler(config, database, haivemind_storage)
        
        # Create router
        self.router = APIRouter(prefix="/api/v1/confluence", tags=["confluence"])
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup FastAPI routes for Confluence management"""
        
        @self.router.get("/status")
        async def get_confluence_status():
            """Get Confluence integration status"""
            try:
                status_json = await self.mcp_tools.get_confluence_status()
                status = json.loads(status_json)
                
                # Add sync service status
                sync_status = await self.sync_scheduler.get_status()
                status['sync_service'] = sync_status
                
                return status
                
            except Exception as e:
                logger.error(f"Error getting Confluence status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.router.post("/configure")
        async def configure_confluence(request: ConfluenceConfigRequest):
            """Configure Confluence integration"""
            try:
                result_json = await self.mcp_tools.configure_confluence_integration(
                    url=request.url,
                    username=request.username,
                    api_token=request.api_token,
                    spaces=request.spaces,
                    enabled=request.enabled
                )
                
                result = json.loads(result_json)
                
                if result.get('success'):
                    # Restart sync service if configuration changed
                    if request.enabled:
                        await self.sync_scheduler.shutdown()
                        await self.sync_scheduler.initialize()
                        
                return result
                
            except Exception as e:
                logger.error(f"Error configuring Confluence: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.router.get("/playbooks")
        async def list_confluence_playbooks():
            """List all playbooks imported from Confluence"""
            try:
                result_json = await self.mcp_tools.list_confluence_playbooks()
                return json.loads(result_json)
                
            except Exception as e:
                logger.error(f"Error listing Confluence playbooks: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.router.get("/discover")
        async def discover_playbooks(space_key: Optional[str] = None):
            """Discover playbook pages in Confluence"""
            try:
                result_json = await self.mcp_tools.discover_confluence_playbooks(space_key)
                return json.loads(result_json)
                
            except Exception as e:
                logger.error(f"Error discovering Confluence playbooks: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.router.get("/preview/{page_id}")
        async def preview_playbook(page_id: str):
            """Preview how a Confluence page would be converted to a playbook"""
            try:
                result_json = await self.mcp_tools.preview_confluence_playbook(page_id)
                return json.loads(result_json)
                
            except Exception as e:
                logger.error(f"Error previewing Confluence playbook: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.router.post("/import")
        async def import_playbook(request: ConfluenceImportRequest):
            """Import a specific Confluence page as a playbook"""
            try:
                result_json = await self.mcp_tools.import_confluence_playbook(
                    page_id=request.page_id,
                    force_update=request.force_update
                )
                
                result = json.loads(result_json)
                
                if result.get('success'):
                    return result
                else:
                    raise HTTPException(status_code=400, detail=result_json)
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error importing Confluence playbook: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.router.post("/bulk-import")
        async def bulk_import_space(request: ConfluenceBulkImportRequest):
            """Bulk import all playbooks from a Confluence space"""
            try:
                result_json = await self.mcp_tools.bulk_import_confluence_space(
                    space_key=request.space_key,
                    force_update=request.force_update
                )
                
                return json.loads(result_json)
                
            except Exception as e:
                logger.error(f"Error bulk importing from Confluence: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.router.post("/sync")
        async def sync_playbooks(request: ConfluenceSyncRequest):
            """Sync updates from Confluence for existing playbooks"""
            try:
                result_json = await self.mcp_tools.sync_confluence_playbooks(
                    max_age_hours=request.max_age_hours
                )
                
                return json.loads(result_json)
                
            except Exception as e:
                logger.error(f"Error syncing Confluence playbooks: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.router.post("/sync/trigger")
        async def trigger_manual_sync():
            """Trigger a manual sync outside of the scheduled interval"""
            try:
                result = await self.sync_scheduler.trigger_sync()
                return result
                
            except Exception as e:
                logger.error(f"Error triggering manual sync: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.router.get("/sync/status")
        async def get_sync_status():
            """Get sync service status"""
            try:
                return await self.sync_scheduler.get_status()
                
            except Exception as e:
                logger.error(f"Error getting sync status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.router.get("/spaces")
        async def get_confluence_spaces():
            """Get list of configured Confluence spaces"""
            try:
                confluence_config = self.config.get('connectors', {}).get('confluence', {})
                spaces = confluence_config.get('spaces', [])
                
                # Get space info if Confluence is configured
                space_info = []
                if confluence_config.get('enabled', False):
                    try:
                        async with ConfluenceIntegration(confluence_config, self.database, self.haivemind_storage) as confluence:
                            for space_key in spaces:
                                # Get basic space info
                                url = f"{confluence.base_url}/rest/api/space/{space_key}"
                                response = await confluence.client.get(url)
                                
                                if response.status_code == 200:
                                    space_data = response.json()
                                    space_info.append({
                                        'key': space_data['key'],
                                        'name': space_data['name'],
                                        'type': space_data.get('type', 'unknown'),
                                        'homepage': space_data.get('homepage', {}).get('title', ''),
                                        'url': f"{confluence.base_url}/wiki/spaces/{space_key}"
                                    })
                                else:
                                    space_info.append({
                                        'key': space_key,
                                        'name': space_key,
                                        'error': f"Could not fetch space info (HTTP {response.status_code})"
                                    })
                                    
                    except Exception as e:
                        logger.error(f"Error fetching space info: {e}")
                        # Return basic info without details
                        space_info = [{'key': key, 'name': key} for key in spaces]
                else:
                    space_info = [{'key': key, 'name': key} for key in spaces]
                    
                return {
                    'configured_spaces': spaces,
                    'space_details': space_info,
                    'total_spaces': len(spaces)
                }
                
            except Exception as e:
                logger.error(f"Error getting Confluence spaces: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.router.get("/analytics")
        async def get_confluence_analytics():
            """Get analytics about Confluence playbook imports"""
            try:
                # Get all Confluence playbooks
                all_playbooks = self.database.list_playbooks()
                confluence_playbooks = [pb for pb in all_playbooks if 'confluence' in pb.get('tags', [])]
                
                # Analyze by space
                space_stats = {}
                category_stats = {}
                import_timeline = {}
                
                for pb in confluence_playbooks:
                    # Get version metadata
                    if pb.get('latest_version_id'):
                        version = self.database.get_playbook_version(pb['latest_version_id'])
                        if version:
                            metadata = version.get('metadata', {})
                            space = metadata.get('confluence_space', 'unknown')
                            
                            # Space statistics
                            if space not in space_stats:
                                space_stats[space] = {
                                    'total_playbooks': 0,
                                    'categories': set()
                                }
                            space_stats[space]['total_playbooks'] += 1
                            space_stats[space]['categories'].add(pb['category'])
                            
                            # Category statistics
                            category = pb['category']
                            if category not in category_stats:
                                category_stats[category] = 0
                            category_stats[category] += 1
                            
                            # Import timeline (by month)
                            import_date = metadata.get('imported_at', pb['created_at'])
                            if import_date:
                                try:
                                    date_obj = datetime.fromisoformat(import_date.replace('Z', '+00:00'))
                                    month_key = date_obj.strftime('%Y-%m')
                                    if month_key not in import_timeline:
                                        import_timeline[month_key] = 0
                                    import_timeline[month_key] += 1
                                except:
                                    pass
                                    
                # Convert sets to lists for JSON serialization
                for space_data in space_stats.values():
                    space_data['categories'] = list(space_data['categories'])
                    
                return {
                    'total_confluence_playbooks': len(confluence_playbooks),
                    'space_statistics': space_stats,
                    'category_statistics': category_stats,
                    'import_timeline': import_timeline,
                    'last_updated': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error getting Confluence analytics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
    async def initialize(self):
        """Initialize the dashboard components"""
        try:
            await self.sync_scheduler.initialize()
            logger.info("Confluence dashboard initialized")
        except Exception as e:
            logger.error(f"Error initializing Confluence dashboard: {e}")
            
    async def shutdown(self):
        """Shutdown the dashboard components"""
        try:
            await self.sync_scheduler.shutdown()
            logger.info("Confluence dashboard shutdown")
        except Exception as e:
            logger.error(f"Error shutting down Confluence dashboard: {e}")
            
    def get_router(self) -> APIRouter:
        """Get the FastAPI router for Confluence endpoints"""
        return self.router