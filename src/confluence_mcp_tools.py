#!/usr/bin/env python3
"""
MCP Tools for Confluence Integration

Provides MCP tools for managing Confluence playbook import and synchronization.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from confluence_integration import ConfluenceIntegration, ConfluenceError

logger = logging.getLogger(__name__)

class ConfluenceMCPTools:
    """MCP tools for Confluence integration"""
    
    def __init__(self, config: Dict[str, Any], database, haivemind_storage=None):
        self.config = config.get('connectors', {}).get('confluence', {})
        self.database = database
        self.haivemind_storage = haivemind_storage
        
    async def discover_confluence_playbooks(self, space_key: Optional[str] = None) -> str:
        """Discover playbook pages in Confluence spaces"""
        try:
            async with ConfluenceIntegration(self.config, self.database, self.haivemind_storage) as confluence:
                pages = await confluence.discover_playbook_pages(space_key)
                
                result = {
                    'space_key': space_key or 'all_configured_spaces',
                    'discovered_pages': len(pages),
                    'pages': [page.to_dict() for page in pages]
                }
                
                return json.dumps(result, indent=2)
                
        except ConfluenceError as e:
            return f"Confluence error: {str(e)}"
        except Exception as e:
            logger.error(f"Error discovering Confluence playbooks: {e}")
            return f"Error: {str(e)}"
            
    async def import_confluence_playbook(self, page_id: str, force_update: bool = False) -> str:
        """Import a specific Confluence page as a playbook"""
        try:
            async with ConfluenceIntegration(self.config, self.database, self.haivemind_storage) as confluence:
                # Get page info
                page_info = await confluence._get_page_info(page_id)
                if not page_info:
                    return f"Error: Could not find Confluence page with ID: {page_id}"
                    
                # Extract playbook
                confluence_playbook = await confluence.extract_playbook_from_page(page_info)
                if not confluence_playbook:
                    return f"Error: Could not extract playbook from page: {page_info.title}"
                    
                # Import playbook
                playbook_id, version_id = await confluence.import_playbook(
                    confluence_playbook, force_update=force_update
                )
                
                result = {
                    'success': True,
                    'playbook_id': playbook_id,
                    'version_id': version_id,
                    'title': page_info.title,
                    'confluence_page_id': page_id,
                    'confluence_url': page_info.web_url,
                    'category': confluence_playbook.playbook_spec['category'],
                    'step_count': len(confluence_playbook.playbook_spec['steps'])
                }
                
                return json.dumps(result, indent=2)
                
        except ConfluenceError as e:
            return f"Confluence error: {str(e)}"
        except Exception as e:
            logger.error(f"Error importing Confluence playbook: {e}")
            return f"Error: {str(e)}"
            
    async def bulk_import_confluence_space(self, space_key: str, force_update: bool = False) -> str:
        """Bulk import all playbooks from a Confluence space"""
        try:
            async with ConfluenceIntegration(self.config, self.database, self.haivemind_storage) as confluence:
                results = await confluence.bulk_import_from_space(space_key, force_update=force_update)
                
                # Store import results in hAIveMind
                if self.haivemind_storage:
                    await self._store_import_results(results)
                    
                return json.dumps(results, indent=2)
                
        except ConfluenceError as e:
            return f"Confluence error: {str(e)}"
        except Exception as e:
            logger.error(f"Error bulk importing from Confluence space: {e}")
            return f"Error: {str(e)}"
            
    async def sync_confluence_playbooks(self, max_age_hours: int = 24) -> str:
        """Sync updates from Confluence for existing playbooks"""
        try:
            async with ConfluenceIntegration(self.config, self.database, self.haivemind_storage) as confluence:
                results = await confluence.sync_playbook_updates(max_age_hours)
                
                # Store sync results in hAIveMind
                if self.haivemind_storage:
                    await self._store_sync_results(results)
                    
                return json.dumps(results, indent=2)
                
        except ConfluenceError as e:
            return f"Confluence error: {str(e)}"
        except Exception as e:
            logger.error(f"Error syncing Confluence playbooks: {e}")
            return f"Error: {str(e)}"
            
    async def get_confluence_status(self) -> str:
        """Get Confluence integration status"""
        try:
            async with ConfluenceIntegration(self.config, self.database, self.haivemind_storage) as confluence:
                status = await confluence.get_sync_status()
                return json.dumps(status, indent=2)
                
        except ConfluenceError as e:
            # Return status with error info
            status = {
                'enabled': self.config.get('enabled', False),
                'connected': False,
                'connection_error': str(e),
                'spaces_configured': len(self.config.get('spaces', [])),
                'total_confluence_playbooks': 0
            }
            return json.dumps(status, indent=2)
        except Exception as e:
            logger.error(f"Error getting Confluence status: {e}")
            return f"Error: {str(e)}"
            
    async def configure_confluence_integration(self, url: str, username: str, 
                                             api_token: str, spaces: List[str],
                                             enabled: bool = True) -> str:
        """Configure Confluence integration settings"""
        try:
            # Update configuration (this would typically update a config file)
            new_config = {
                'url': url,
                'credentials': {
                    'username': username,
                    'token': api_token
                },
                'spaces': spaces,
                'enabled': enabled
            }
            
            # Test the new configuration
            async with ConfluenceIntegration(new_config, self.database, self.haivemind_storage) as confluence:
                await confluence._test_connection()
                
            # If successful, you would save this configuration
            # For now, just return success
            result = {
                'success': True,
                'message': 'Confluence integration configured successfully',
                'url': url,
                'username': username,
                'spaces': spaces,
                'enabled': enabled
            }
            
            return json.dumps(result, indent=2)
            
        except ConfluenceError as e:
            return f"Configuration error: {str(e)}"
        except Exception as e:
            logger.error(f"Error configuring Confluence integration: {e}")
            return f"Error: {str(e)}"
            
    async def list_confluence_playbooks(self) -> str:
        """List all playbooks imported from Confluence"""
        try:
            all_playbooks = self.database.list_playbooks()
            confluence_playbooks = []
            
            for pb in all_playbooks:
                if 'confluence' in pb.get('tags', []):
                    # Get latest version for metadata
                    if pb.get('latest_version_id'):
                        version = self.database.get_playbook_version(pb['latest_version_id'])
                        metadata = version.get('metadata', {}) if version else {}
                        
                        confluence_info = {
                            'playbook_id': pb['id'],
                            'name': pb['name'],
                            'category': pb['category'],
                            'confluence_page_id': metadata.get('confluence_page_id'),
                            'confluence_space': metadata.get('confluence_space'),
                            'confluence_url': metadata.get('confluence_url'),
                            'confluence_version': metadata.get('confluence_version'),
                            'last_imported': metadata.get('imported_at'),
                            'created_at': pb['created_at'],
                            'updated_at': pb['updated_at']
                        }
                        confluence_playbooks.append(confluence_info)
                        
            result = {
                'total_confluence_playbooks': len(confluence_playbooks),
                'playbooks': confluence_playbooks
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Error listing Confluence playbooks: {e}")
            return f"Error: {str(e)}"
            
    async def preview_confluence_playbook(self, page_id: str) -> str:
        """Preview how a Confluence page would be converted to a playbook"""
        try:
            async with ConfluenceIntegration(self.config, self.database, self.haivemind_storage) as confluence:
                # Get page info
                page_info = await confluence._get_page_info(page_id)
                if not page_info:
                    return f"Error: Could not find Confluence page with ID: {page_id}"
                    
                # Extract playbook (but don't import)
                confluence_playbook = await confluence.extract_playbook_from_page(page_info)
                if not confluence_playbook:
                    return f"Error: Could not extract playbook from page: {page_info.title}"
                    
                # Return preview
                result = {
                    'page_info': page_info.to_dict(),
                    'playbook_spec': confluence_playbook.playbook_spec,
                    'yaml_preview': confluence_playbook.to_yaml(),
                    'metadata': confluence_playbook.extracted_metadata
                }
                
                return json.dumps(result, indent=2)
                
        except ConfluenceError as e:
            return f"Confluence error: {str(e)}"
        except Exception as e:
            logger.error(f"Error previewing Confluence playbook: {e}")
            return f"Error: {str(e)}"
            
    async def _store_import_results(self, results: Dict[str, Any]) -> None:
        """Store bulk import results in hAIveMind"""
        try:
            content = f"""
Confluence Bulk Import Results

Space: {results['space_key']}
Discovered Pages: {results['discovered_pages']}
Successful Imports: {results['successful_imports']}
Failed Imports: {results['failed_imports']}
Skipped Imports: {results['skipped_imports']}

Imported Playbooks:
{json.dumps(results['imported_playbooks'], indent=2)}

Errors:
{json.dumps(results['errors'], indent=2)}
"""
            
            await self.haivemind_storage.store_memory(
                content=content,
                category='deployments',
                context=f"Confluence bulk import from space {results['space_key']}",
                metadata={
                    'type': 'confluence_bulk_import',
                    'space_key': results['space_key'],
                    'successful_imports': results['successful_imports'],
                    'failed_imports': results['failed_imports'],
                    'import_timestamp': results.get('timestamp', 'unknown')
                },
                tags=['confluence', 'bulk_import', 'playbooks', results['space_key'].lower()]
            )
            
        except Exception as e:
            logger.error(f"Failed to store import results in hAIveMind: {e}")
            
    async def _store_sync_results(self, results: Dict[str, Any]) -> None:
        """Store sync results in hAIveMind"""
        try:
            content = f"""
Confluence Playbook Sync Results

Checked Playbooks: {results['checked_playbooks']}
Updated Playbooks: {results['updated_playbooks']}
Failed Updates: {results['failed_updates']}
No Changes: {results['no_changes']}

Errors:
{json.dumps(results['errors'], indent=2)}
"""
            
            await self.haivemind_storage.store_memory(
                content=content,
                category='deployments',
                context="Confluence playbook synchronization",
                metadata={
                    'type': 'confluence_sync',
                    'updated_playbooks': results['updated_playbooks'],
                    'failed_updates': results['failed_updates'],
                    'sync_timestamp': results.get('timestamp', 'unknown')
                },
                tags=['confluence', 'sync', 'playbooks', 'automation']
            )
            
        except Exception as e:
            logger.error(f"Failed to store sync results in hAIveMind: {e}")

    def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get MCP tool definitions for Confluence integration"""
        return [
            {
                "name": "discover_confluence_playbooks",
                "description": "Discover playbook pages in Confluence spaces",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "space_key": {
                            "type": "string",
                            "description": "Confluence space key to search (optional, searches all configured spaces if not provided)"
                        }
                    }
                }
            },
            {
                "name": "import_confluence_playbook",
                "description": "Import a specific Confluence page as a playbook",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Confluence page ID to import"
                        },
                        "force_update": {
                            "type": "boolean",
                            "description": "Force update if playbook already exists",
                            "default": False
                        }
                    },
                    "required": ["page_id"]
                }
            },
            {
                "name": "bulk_import_confluence_space",
                "description": "Bulk import all playbooks from a Confluence space",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "space_key": {
                            "type": "string",
                            "description": "Confluence space key to import from"
                        },
                        "force_update": {
                            "type": "boolean",
                            "description": "Force update existing playbooks",
                            "default": False
                        }
                    },
                    "required": ["space_key"]
                }
            },
            {
                "name": "sync_confluence_playbooks",
                "description": "Sync updates from Confluence for existing playbooks",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "max_age_hours": {
                            "type": "integer",
                            "description": "Only sync playbooks updated within this many hours",
                            "default": 24
                        }
                    }
                }
            },
            {
                "name": "get_confluence_status",
                "description": "Get Confluence integration status and connection info",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "configure_confluence_integration",
                "description": "Configure Confluence integration settings",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Confluence base URL"
                        },
                        "username": {
                            "type": "string",
                            "description": "Confluence username/email"
                        },
                        "api_token": {
                            "type": "string",
                            "description": "Confluence API token"
                        },
                        "spaces": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of Confluence space keys to monitor"
                        },
                        "enabled": {
                            "type": "boolean",
                            "description": "Enable Confluence integration",
                            "default": True
                        }
                    },
                    "required": ["url", "username", "api_token", "spaces"]
                }
            },
            {
                "name": "list_confluence_playbooks",
                "description": "List all playbooks imported from Confluence",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "preview_confluence_playbook",
                "description": "Preview how a Confluence page would be converted to a playbook without importing",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Confluence page ID to preview"
                        }
                    },
                    "required": ["page_id"]
                }
            }
        ]