#!/usr/bin/env python3
"""
Confluence Sync Service

Provides scheduled synchronization of Confluence playbooks and automated monitoring.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from confluence_integration import ConfluenceIntegration, ConfluenceError

logger = logging.getLogger(__name__)

class ConfluenceSyncService:
    """Service for scheduled Confluence synchronization"""
    
    def __init__(self, config: Dict[str, Any], database, haivemind_storage=None):
        self.config = config.get('connectors', {}).get('confluence', {})
        self.database = database
        self.haivemind_storage = haivemind_storage
        
        # Sync configuration
        self.sync_interval = config.get('sync_interval', 3600)  # 1 hour default
        self.max_age_hours = config.get('max_age_hours', 24)
        self.auto_import_new = config.get('auto_import_new', True)
        self.auto_update_existing = config.get('auto_update_existing', True)
        
        # State tracking
        self.is_running = False
        self.last_sync = None
        self.sync_stats = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'last_error': None
        }
        
    async def start(self) -> None:
        """Start the sync service"""
        if self.is_running:
            logger.warning("Confluence sync service is already running")
            return
            
        if not self.config.get('enabled', False):
            logger.info("Confluence integration is disabled, not starting sync service")
            return
            
        self.is_running = True
        logger.info(f"Starting Confluence sync service (interval: {self.sync_interval}s)")
        
        # Store service start in hAIveMind
        if self.haivemind_storage:
            await self._store_service_event('started', {
                'sync_interval': self.sync_interval,
                'max_age_hours': self.max_age_hours,
                'auto_import_new': self.auto_import_new,
                'auto_update_existing': self.auto_update_existing
            })
        
        # Start background sync loop
        asyncio.create_task(self._sync_loop())
        
    async def stop(self) -> None:
        """Stop the sync service"""
        if not self.is_running:
            return
            
        self.is_running = False
        logger.info("Stopping Confluence sync service")
        
        # Store service stop in hAIveMind
        if self.haivemind_storage:
            await self._store_service_event('stopped', self.sync_stats)
            
    async def _sync_loop(self) -> None:
        """Main sync loop"""
        while self.is_running:
            try:
                await self.perform_sync()
                await asyncio.sleep(self.sync_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                self.sync_stats['failed_syncs'] += 1
                self.sync_stats['last_error'] = str(e)
                
                # Wait before retrying
                await asyncio.sleep(min(self.sync_interval, 300))  # Max 5 min retry delay
                
    async def perform_sync(self) -> Dict[str, Any]:
        """Perform a complete synchronization"""
        sync_start = time.time()
        sync_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'duration_seconds': 0,
            'success': False,
            'updated_playbooks': 0,
            'new_playbooks': 0,
            'failed_operations': 0,
            'errors': []
        }
        
        try:
            logger.info("Starting Confluence sync")
            
            async with ConfluenceIntegration(self.config, self.database, self.haivemind_storage) as confluence:
                
                # 1. Sync existing playbooks for updates
                if self.auto_update_existing:
                    logger.info("Syncing existing playbooks for updates")
                    update_results = await confluence.sync_playbook_updates(self.max_age_hours)
                    
                    sync_results['updated_playbooks'] = update_results['updated_playbooks']
                    sync_results['failed_operations'] += update_results['failed_updates']
                    sync_results['errors'].extend(update_results['errors'])
                    
                # 2. Discover and import new playbooks
                if self.auto_import_new:
                    logger.info("Discovering new playbooks")
                    
                    for space_key in self.config.get('spaces', []):
                        try:
                            # Discover pages in space
                            pages = await confluence.discover_playbook_pages(space_key)
                            
                            # Check which pages are not yet imported
                            existing_page_ids = await self._get_existing_confluence_page_ids()
                            new_pages = [p for p in pages if p.page_id not in existing_page_ids]
                            
                            logger.info(f"Found {len(new_pages)} new pages in space {space_key}")
                            
                            # Import new pages
                            for page_info in new_pages:
                                try:
                                    confluence_playbook = await confluence.extract_playbook_from_page(page_info)
                                    if confluence_playbook:
                                        await confluence.import_playbook(confluence_playbook)
                                        sync_results['new_playbooks'] += 1
                                        logger.info(f"Imported new playbook: {page_info.title}")
                                        
                                except Exception as e:
                                    sync_results['failed_operations'] += 1
                                    error_msg = f"Failed to import new page '{page_info.title}': {str(e)}"
                                    sync_results['errors'].append(error_msg)
                                    logger.error(error_msg)
                                    
                        except Exception as e:
                            sync_results['failed_operations'] += 1
                            error_msg = f"Failed to process space '{space_key}': {str(e)}"
                            sync_results['errors'].append(error_msg)
                            logger.error(error_msg)
                            
                sync_results['success'] = True
                self.sync_stats['successful_syncs'] += 1
                
        except ConfluenceError as e:
            sync_results['errors'].append(f"Confluence error: {str(e)}")
            self.sync_stats['failed_syncs'] += 1
            self.sync_stats['last_error'] = str(e)
            logger.error(f"Confluence sync failed: {e}")
            
        except Exception as e:
            sync_results['errors'].append(f"Sync error: {str(e)}")
            self.sync_stats['failed_syncs'] += 1
            self.sync_stats['last_error'] = str(e)
            logger.error(f"Sync failed: {e}")
            
        finally:
            sync_results['duration_seconds'] = time.time() - sync_start
            self.sync_stats['total_syncs'] += 1
            self.last_sync = datetime.utcnow()
            
            # Store sync results
            if self.haivemind_storage:
                await self._store_sync_results(sync_results)
                
            logger.info(f"Confluence sync completed in {sync_results['duration_seconds']:.2f}s: "
                       f"{sync_results['updated_playbooks']} updated, "
                       f"{sync_results['new_playbooks']} new, "
                       f"{sync_results['failed_operations']} failed")
                       
        return sync_results
        
    async def _get_existing_confluence_page_ids(self) -> set:
        """Get set of Confluence page IDs that are already imported"""
        page_ids = set()
        
        try:
            all_playbooks = self.database.list_playbooks()
            
            for pb in all_playbooks:
                if 'confluence' in pb.get('tags', []) and pb.get('latest_version_id'):
                    version = self.database.get_playbook_version(pb['latest_version_id'])
                    if version:
                        metadata = version.get('metadata', {})
                        page_id = metadata.get('confluence_page_id')
                        if page_id:
                            page_ids.add(page_id)
                            
        except Exception as e:
            logger.error(f"Error getting existing Confluence page IDs: {e}")
            
        return page_ids
        
    async def _store_service_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Store service events in hAIveMind"""
        try:
            content = f"""
Confluence Sync Service Event: {event_type.title()}

Event Details:
{json.dumps(details, indent=2)}

Service Statistics:
{json.dumps(self.sync_stats, indent=2)}
"""
            
            await self.haivemind_storage.store_memory(
                content=content,
                category='deployments',
                context=f"Confluence sync service {event_type}",
                metadata={
                    'type': 'confluence_service_event',
                    'event_type': event_type,
                    'service': 'confluence_sync',
                    'timestamp': datetime.utcnow().isoformat(),
                    **details
                },
                tags=['confluence', 'sync_service', event_type, 'automation']
            )
            
        except Exception as e:
            logger.error(f"Failed to store service event in hAIveMind: {e}")
            
    async def _store_sync_results(self, results: Dict[str, Any]) -> None:
        """Store sync results in hAIveMind"""
        try:
            content = f"""
Confluence Scheduled Sync Results

Timestamp: {results['timestamp']}
Duration: {results['duration_seconds']:.2f} seconds
Success: {results['success']}

Results:
- Updated Playbooks: {results['updated_playbooks']}
- New Playbooks: {results['new_playbooks']}
- Failed Operations: {results['failed_operations']}

Errors:
{json.dumps(results['errors'], indent=2)}

Service Statistics:
- Total Syncs: {self.sync_stats['total_syncs']}
- Successful Syncs: {self.sync_stats['successful_syncs']}
- Failed Syncs: {self.sync_stats['failed_syncs']}
"""
            
            await self.haivemind_storage.store_memory(
                content=content,
                category='deployments',
                context="Confluence scheduled synchronization",
                metadata={
                    'type': 'confluence_scheduled_sync',
                    'success': results['success'],
                    'updated_playbooks': results['updated_playbooks'],
                    'new_playbooks': results['new_playbooks'],
                    'failed_operations': results['failed_operations'],
                    'duration_seconds': results['duration_seconds'],
                    'sync_timestamp': results['timestamp']
                },
                tags=['confluence', 'scheduled_sync', 'playbooks', 'automation']
            )
            
            # Broadcast significant sync events
            if results['new_playbooks'] > 0 or results['updated_playbooks'] > 0:
                await self.haivemind_storage.broadcast_discovery(
                    message=f"Confluence sync completed: {results['new_playbooks']} new, {results['updated_playbooks']} updated playbooks",
                    category='deployments',
                    severity='info',
                    details={
                        'new_playbooks': results['new_playbooks'],
                        'updated_playbooks': results['updated_playbooks'],
                        'sync_duration': results['duration_seconds']
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to store sync results in hAIveMind: {e}")
            
    async def get_status(self) -> Dict[str, Any]:
        """Get sync service status"""
        return {
            'running': self.is_running,
            'enabled': self.config.get('enabled', False),
            'sync_interval': self.sync_interval,
            'max_age_hours': self.max_age_hours,
            'auto_import_new': self.auto_import_new,
            'auto_update_existing': self.auto_update_existing,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'statistics': self.sync_stats.copy()
        }
        
    async def trigger_manual_sync(self) -> Dict[str, Any]:
        """Trigger a manual sync outside of the scheduled interval"""
        if not self.config.get('enabled', False):
            return {
                'success': False,
                'error': 'Confluence integration is disabled'
            }
            
        logger.info("Triggering manual Confluence sync")
        
        try:
            results = await self.perform_sync()
            
            # Store manual sync trigger in hAIveMind
            if self.haivemind_storage:
                await self._store_service_event('manual_sync_triggered', {
                    'trigger_time': datetime.utcnow().isoformat(),
                    'results': results
                })
                
            return results
            
        except Exception as e:
            error_msg = f"Manual sync failed: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'timestamp': datetime.utcnow().isoformat()
            }

class ConfluenceSyncScheduler:
    """Scheduler for managing Confluence sync service lifecycle"""
    
    def __init__(self, config: Dict[str, Any], database, haivemind_storage=None):
        self.config = config
        self.database = database
        self.haivemind_storage = haivemind_storage
        self.sync_service = None
        
    async def initialize(self) -> None:
        """Initialize the sync scheduler"""
        confluence_config = self.config.get('connectors', {}).get('confluence', {})
        
        if confluence_config.get('enabled', False):
            self.sync_service = ConfluenceSyncService(
                self.config, self.database, self.haivemind_storage
            )
            await self.sync_service.start()
            logger.info("Confluence sync scheduler initialized")
        else:
            logger.info("Confluence integration disabled, sync scheduler not started")
            
    async def shutdown(self) -> None:
        """Shutdown the sync scheduler"""
        if self.sync_service:
            await self.sync_service.stop()
            logger.info("Confluence sync scheduler shutdown")
            
    async def get_status(self) -> Dict[str, Any]:
        """Get scheduler and service status"""
        if self.sync_service:
            return await self.sync_service.get_status()
        else:
            return {
                'running': False,
                'enabled': False,
                'reason': 'Confluence integration is disabled'
            }
            
    async def trigger_sync(self) -> Dict[str, Any]:
        """Trigger manual sync"""
        if self.sync_service:
            return await self.sync_service.trigger_manual_sync()
        else:
            return {
                'success': False,
                'error': 'Confluence sync service is not running'
            }