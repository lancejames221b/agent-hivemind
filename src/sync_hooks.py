#!/usr/bin/env python3
"""
hAIveMind Sync Hooks - Automated pre/post sync operations for ticket-memory synchronization
Integrates with existing sync infrastructure to provide zero-overhead knowledge capture
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Callable
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SyncHooks:
    """Manages automated sync hooks for ticket-memory synchronization"""
    
    def __init__(self, storage, config: Dict[str, Any], command_installer=None):
        self.storage = storage
        self.config = config
        self.command_installer = command_installer
        self.hooks_registry = {}
        self.protocol_config = self._load_sync_protocol()
        
    def _load_sync_protocol(self) -> Dict[str, Any]:
        """Load sync protocol configuration"""
        try:
            protocol_file = Path(__file__).parent.parent / "sync-protocol.json"
            if protocol_file.exists():
                with open(protocol_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load sync protocol config: {e}")
        
        # Default protocol configuration
        return {
            "protocol_version": "1.0",
            "compliance_level": "REQUIRED",
            "auto_remind": True,
            "pre_sync_checklist": [
                "Read ticket description and current status",
                "Check hAIveMind memory for related context", 
                "Store work intention with expected outcomes",
                "Identify dependencies and blocking issues",
                "Review lessons learned from similar work"
            ],
            "post_sync_checklist": [
                "Update ticket status with detailed completion notes",
                "Store comprehensive results in hAIveMind memory",
                "Document lessons learned and troubleshooting solutions",
                "Share important discoveries with other agents",
                "Coordinate with dependent tickets and agents"
            ],
            "memory_categories": [
                "workflow - Ticket synchronization events",
                "lessons_learned - Key insights from completed work", 
                "troubleshooting - Solutions to common problems",
                "dependencies - Cross-ticket relationships",
                "agent_coordination - Multi-agent collaboration"
            ]
        }
    
    def register_hook(self, event_type: str, hook_function: Callable, priority: int = 50):
        """Register a sync hook for specific events"""
        if event_type not in self.hooks_registry:
            self.hooks_registry[event_type] = []
        
        self.hooks_registry[event_type].append({
            'function': hook_function,
            'priority': priority,
            'registered_at': time.time()
        })
        
        # Sort by priority (lower numbers execute first)
        self.hooks_registry[event_type].sort(key=lambda x: x['priority'])
        
        logger.info(f"Registered {event_type} hook with priority {priority}")
    
    async def trigger_hooks(self, event_type: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Trigger all registered hooks for an event type"""
        if event_type not in self.hooks_registry:
            return []
        
        results = []
        hooks = self.hooks_registry[event_type]
        
        logger.info(f"Triggering {len(hooks)} hooks for {event_type}")
        
        for hook_info in hooks:
            try:
                start_time = time.time()
                result = await hook_info['function'](context)
                execution_time = time.time() - start_time
                
                results.append({
                    'hook_function': hook_info['function'].__name__,
                    'execution_time': execution_time,
                    'result': result,
                    'success': True
                })
                
                logger.debug(f"Hook {hook_info['function'].__name__} completed in {execution_time:.3f}s")
                
            except Exception as e:
                logger.error(f"Hook {hook_info['function'].__name__} failed: {e}")
                results.append({
                    'hook_function': hook_info['function'].__name__,
                    'error': str(e),
                    'success': False
                })
        
        return results
    
    async def pre_work_hook(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Pre-work synchronization hook"""
        ticket_id = context.get('ticket_id')
        project_id = context.get('project_id')
        agent_id = context.get('agent_id', self.storage.agent_id)
        
        logger.info(f"Executing pre-work hook for ticket {ticket_id}")
        
        result = {
            'event': 'pre_work_sync',
            'ticket_id': ticket_id,
            'project_id': project_id,
            'agent_id': agent_id,
            'timestamp': time.time(),
            'operations': []
        }
        
        try:
            # 1. Read ticket description and current status
            if hasattr(context, 'ticket_data'):
                ticket_data = context['ticket_data']
                result['operations'].append("Retrieved ticket data from context")
            else:
                # Would need to integrate with kanban system to fetch ticket
                result['operations'].append("Ticket data not available in context")
            
            # 2. Check hAIveMind memory for related context
            if ticket_id:
                related_memories = await self.storage.search_memories(
                    query=f"ticket_id:{ticket_id} OR project_id:{project_id}",
                    category="workflow",
                    limit=10
                )
                result['related_memories_found'] = len(related_memories)
                result['operations'].append(f"Found {len(related_memories)} related memories")
            
            # 3. Store work intention
            intention_memory = await self.storage.store_memory(
                content=f"Starting work on ticket {ticket_id} in project {project_id}",
                category="workflow", 
                context=f"Pre-work sync for {agent_id}",
                metadata={
                    'ticket_id': ticket_id,
                    'project_id': project_id,
                    'agent_id': agent_id,
                    'sync_type': 'pre_work',
                    'protocol_version': self.protocol_config.get('protocol_version')
                },
                tags=['pre-work', 'sync-protocol', ticket_id, project_id, agent_id]
            )
            result['intention_memory_id'] = intention_memory
            result['operations'].append("Stored work intention in hAIveMind memory")
            
            # 4. Check for dependencies
            if project_id:
                dependency_memories = await self.storage.search_memories(
                    query=f"project_id:{project_id} dependency",
                    category="dependencies", 
                    limit=5
                )
                result['dependencies_found'] = len(dependency_memories)
                result['operations'].append(f"Found {len(dependency_memories)} potential dependencies")
            
            # 5. Review lessons learned
            lessons_memories = await self.storage.search_memories(
                query="lessons_learned troubleshooting",
                category="lessons_learned",
                limit=3
            )
            result['lessons_available'] = len(lessons_memories)
            result['operations'].append(f"Retrieved {len(lessons_memories)} relevant lessons")
            
            result['status'] = 'success'
            logger.info(f"Pre-work hook completed successfully for ticket {ticket_id}")
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            logger.error(f"Pre-work hook failed for ticket {ticket_id}: {e}")
        
        return result
    
    async def post_work_hook(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Post-work synchronization hook"""
        ticket_id = context.get('ticket_id')
        project_id = context.get('project_id') 
        agent_id = context.get('agent_id', self.storage.agent_id)
        work_results = context.get('work_results', {})
        
        logger.info(f"Executing post-work hook for ticket {ticket_id}")
        
        result = {
            'event': 'post_work_sync',
            'ticket_id': ticket_id,
            'project_id': project_id,
            'agent_id': agent_id,
            'timestamp': time.time(),
            'operations': []
        }
        
        try:
            # 1. Update ticket status with detailed completion notes
            if work_results:
                completion_memory = await self.storage.store_memory(
                    content=f"Completed work on ticket {ticket_id}: {work_results.get('summary', 'Work completed')}",
                    category="workflow",
                    context=f"Post-work sync for {agent_id}",
                    metadata={
                        'ticket_id': ticket_id,
                        'project_id': project_id,
                        'agent_id': agent_id,
                        'sync_type': 'post_work',
                        'work_results': str(work_results),
                        'protocol_version': self.protocol_config.get('protocol_version')
                    },
                    tags=['post-work', 'sync-protocol', 'completed', ticket_id, project_id, agent_id]
                )
                result['completion_memory_id'] = completion_memory
                result['operations'].append("Stored work completion details")
            
            # 2. Store comprehensive results in hAIveMind memory
            if work_results.get('details'):
                details_memory = await self.storage.store_memory(
                    content=work_results['details'],
                    category="project",
                    context=f"Detailed results for ticket {ticket_id}",
                    metadata={
                        'ticket_id': ticket_id,
                        'project_id': project_id,
                        'agent_id': agent_id,
                        'result_type': 'detailed_completion'
                    },
                    tags=['work-results', ticket_id, project_id, agent_id]
                )
                result['details_memory_id'] = details_memory
                result['operations'].append("Stored detailed results")
            
            # 3. Document lessons learned and troubleshooting solutions
            if work_results.get('lessons_learned'):
                lessons_memory = await self.storage.store_memory(
                    content=work_results['lessons_learned'],
                    category="lessons_learned",
                    context=f"Lessons from ticket {ticket_id}",
                    metadata={
                        'ticket_id': ticket_id,
                        'project_id': project_id,
                        'agent_id': agent_id,
                        'lesson_type': 'ticket_completion'
                    },
                    tags=['lessons', 'troubleshooting', ticket_id, project_id]
                )
                result['lessons_memory_id'] = lessons_memory
                result['operations'].append("Documented lessons learned")
            
            # 4. Share important discoveries with other agents via broadcast
            if work_results.get('important_discovery'):
                try:
                    if hasattr(self.storage, 'broadcast_discovery'):
                        await self.storage.broadcast_discovery(
                            message=work_results['important_discovery'],
                            category="workflow",
                            severity="info",
                            metadata={'source_ticket': ticket_id, 'project_id': project_id}
                        )
                        result['operations'].append("Broadcasted discovery to hAIveMind collective")
                except Exception as e:
                    logger.warning(f"Failed to broadcast discovery: {e}")
                    result['operations'].append("Discovery broadcast failed")
            
            # 5. Coordinate with dependent tickets and agents
            if project_id:
                # Store coordination info for dependent work
                coordination_memory = await self.storage.store_memory(
                    content=f"Ticket {ticket_id} completed - may affect dependent work",
                    category="dependencies",
                    context=f"Coordination info from {agent_id}",
                    metadata={
                        'source_ticket': ticket_id,
                        'project_id': project_id,
                        'completion_time': time.time(),
                        'available_for_dependents': True
                    },
                    tags=['coordination', 'dependencies', ticket_id, project_id]
                )
                result['coordination_memory_id'] = coordination_memory
                result['operations'].append("Updated coordination information")
            
            # 6. Trigger network sync if configured and available
            if self.command_installer and self.config.get('sync', {}).get('enable_remote_sync'):
                try:
                    # This would trigger the existing sync infrastructure
                    result['operations'].append("Network sync integration available")
                    # Could trigger: await self.command_installer.sync_agent_installation()
                except Exception as e:
                    logger.warning(f"Network sync integration failed: {e}")
            
            result['status'] = 'success'
            logger.info(f"Post-work hook completed successfully for ticket {ticket_id}")
            
        except Exception as e:
            result['status'] = 'error' 
            result['error'] = str(e)
            logger.error(f"Post-work hook failed for ticket {ticket_id}: {e}")
        
        return result
    
    async def integrate_with_sync_commands(self, command_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Integration point for existing sync commands (install_sync, install_commands)"""
        
        result = {
            'command_type': command_type,
            'timestamp': time.time(),
            'hooks_triggered': [],
            'sync_operations': []
        }
        
        logger.info(f"Integrating hooks with {command_type} command")
        
        try:
            # Pre-sync hooks
            pre_sync_context = {
                **context,
                'command_type': command_type,
                'phase': 'pre_sync'
            }
            
            pre_results = await self.trigger_hooks('pre_sync', pre_sync_context)
            result['hooks_triggered'].extend(pre_results)
            
            # Execute the original sync command if command_installer is available
            if self.command_installer:
                if command_type == 'install_sync':
                    sync_result = await self.command_installer.sync_agent_installation(
                        agent_id=context.get('agent_id'),
                        force=context.get('force', False),
                        verbose=context.get('verbose', False)
                    )
                    result['sync_operations'].append(sync_result)
            
            # Post-sync hooks
            post_sync_context = {
                **context,
                'command_type': command_type,
                'phase': 'post_sync',
                'sync_results': result.get('sync_operations', [])
            }
            
            post_results = await self.trigger_hooks('post_sync', post_sync_context)
            result['hooks_triggered'].extend(post_results)
            
            # Store integration record in memory
            integration_memory = await self.storage.store_memory(
                content=f"Sync command {command_type} executed with automated hooks",
                category="infrastructure",
                context=f"Sync integration for {context.get('agent_id', 'unknown')}",
                metadata={
                    'command_type': command_type,
                    'hooks_count': len(result['hooks_triggered']),
                    'integration_time': time.time(),
                    'agent_id': context.get('agent_id'),
                    'machine_id': context.get('machine_id')
                },
                tags=['sync-integration', 'hooks', command_type, 'automation']
            )
            result['integration_memory_id'] = integration_memory
            
            result['status'] = 'success'
            logger.info(f"Successfully integrated hooks with {command_type}")
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            logger.error(f"Hook integration failed for {command_type}: {e}")
        
        return result
    
    def setup_default_hooks(self):
        """Set up default hooks for common events"""
        
        # Register pre-work hook
        self.register_hook('ticket_start', self.pre_work_hook, priority=10)
        self.register_hook('pre_sync', self.pre_work_hook, priority=10)
        
        # Register post-work hook  
        self.register_hook('ticket_complete', self.post_work_hook, priority=10)
        self.register_hook('post_sync', self.post_work_hook, priority=10)
        
        # Register sync integration hooks
        async def network_sync_hook(context):
            """Hook for network-wide sync operations"""
            return await self.integrate_with_sync_commands('network_sync', context)
        
        self.register_hook('network_sync', network_sync_hook, priority=20)
        
        logger.info("Default sync hooks registered successfully")
    
    async def get_hook_status(self) -> Dict[str, Any]:
        """Get current status of registered hooks"""
        
        status = {
            'protocol_version': self.protocol_config.get('protocol_version'),
            'compliance_level': self.protocol_config.get('compliance_level'),
            'hooks_registered': {},
            'total_hooks': 0,
            'last_execution': None
        }
        
        for event_type, hooks in self.hooks_registry.items():
            status['hooks_registered'][event_type] = [
                {
                    'function_name': hook['function'].__name__,
                    'priority': hook['priority'],
                    'registered_at': hook['registered_at']
                }
                for hook in hooks
            ]
            status['total_hooks'] += len(hooks)
        
        # Get last execution from memory
        try:
            recent_executions = await self.storage.search_memories(
                query="sync-protocol hooks",
                category="workflow",
                limit=1
            )
            if recent_executions:
                status['last_execution'] = recent_executions[0].get('timestamp')
        except Exception as e:
            logger.warning(f"Could not retrieve hook execution history: {e}")
        
        return status