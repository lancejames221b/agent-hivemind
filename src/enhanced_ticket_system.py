#!/usr/bin/env python3
"""
Enhanced Ticket Management System for hAIveMind
Built on top of Vibe Kanban with advanced features for hAIveMind collective intelligence
"""

import asyncio
import json
import logging
import re
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

class TicketType(Enum):
    BUG = "bug"
    FEATURE = "feature"
    TASK = "task"
    EPIC = "epic"
    STORY = "story"
    INCIDENT = "incident"
    REQUEST = "request"

class TicketPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class TicketSeverity(Enum):
    TRIVIAL = "trivial"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"
    BLOCKER = "blocker"

# Map Vibe Kanban statuses to our workflow
VIBE_STATUS_MAPPING = {
    'todo': 'new',
    'inprogress': 'in_progress', 
    'inreview': 'review',
    'done': 'done',
    'cancelled': 'cancelled'
}

REVERSE_STATUS_MAPPING = {v: k for k, v in VIBE_STATUS_MAPPING.items()}

@dataclass
class TicketMetadata:
    """Enhanced metadata for tickets"""
    ticket_type: str = "task"
    priority: str = "medium"
    severity: str = "minor"
    assignee: Optional[str] = None
    reporter: str = "system"
    watchers: List[str] = None
    labels: List[str] = None
    components: List[str] = None
    affected_versions: List[str] = None
    fix_versions: List[str] = None
    environment: str = ""
    resolution: str = ""
    resolution_date: Optional[str] = None
    due_date: Optional[str] = None
    sla_deadline: Optional[str] = None
    time_estimate: Optional[int] = None
    time_spent: Optional[int] = None
    time_remaining: Optional[int] = None
    parent_ticket: Optional[str] = None
    epic_link: Optional[str] = None
    
    def __post_init__(self):
        if self.watchers is None:
            self.watchers = []
        if self.labels is None:
            self.labels = []
        if self.components is None:
            self.components = []
        if self.affected_versions is None:
            self.affected_versions = []
        if self.fix_versions is None:
            self.fix_versions = []

@dataclass
class TicketComment:
    id: str
    content: str
    author: str
    created_at: str
    updated_at: Optional[str] = None

@dataclass
class TicketHistory:
    id: str
    field_name: str
    old_value: str
    new_value: str
    changed_by: str
    changed_at: str
    change_type: str = "update"

class EnhancedTicketSystem:
    """Enhanced ticket management system using Vibe Kanban as foundation"""
    
    def __init__(self, vibe_kanban_tools, memory_storage, config):
        self.vibe = vibe_kanban_tools
        self.storage = memory_storage
        self.config = config
        self.ticket_counter = 1000  # Start ticket numbers at 1000
        logger.info("🎫 Enhanced ticket system initialized with Vibe Kanban backend")
    
    def _generate_ticket_number(self) -> int:
        """Generate sequential ticket numbers"""
        self.ticket_counter += 1
        return self.ticket_counter
    
    def _parse_ticket_metadata(self, description: str) -> Tuple[str, TicketMetadata]:
        """Parse enhanced metadata from ticket description"""
        metadata = TicketMetadata()
        lines = description.split('\n')
        clean_lines = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('Type:'):
                metadata.ticket_type = line.split(':', 1)[1].strip().lower()
            elif line.startswith('Priority:'):
                metadata.priority = line.split(':', 1)[1].strip().lower()
            elif line.startswith('Severity:'):
                metadata.severity = line.split(':', 1)[1].strip().lower()
            elif line.startswith('Assignee:'):
                metadata.assignee = line.split(':', 1)[1].strip()
            elif line.startswith('Reporter:'):
                metadata.reporter = line.split(':', 1)[1].strip()
            elif line.startswith('Labels:'):
                labels_str = line.split(':', 1)[1].strip()
                metadata.labels = [l.strip() for l in labels_str.split(',') if l.strip()]
            elif line.startswith('Components:'):
                comp_str = line.split(':', 1)[1].strip()
                metadata.components = [c.strip() for c in comp_str.split(',') if c.strip()]
            elif line.startswith('Due Date:'):
                metadata.due_date = line.split(':', 1)[1].strip()
            elif line.startswith('Time Estimate:'):
                try:
                    metadata.time_estimate = int(line.split(':', 1)[1].strip().replace('h', ''))
                except ValueError:
                    pass
            elif line.startswith('Parent:'):
                metadata.parent_ticket = line.split(':', 1)[1].strip()
            elif line.startswith('Epic:'):
                metadata.epic_link = line.split(':', 1)[1].strip()
            else:
                clean_lines.append(line)
        
        clean_description = '\n'.join(clean_lines).strip()
        return clean_description, metadata
    
    def _format_ticket_description(self, description: str, metadata: TicketMetadata) -> str:
        """Format ticket with embedded metadata"""
        lines = [f"Type: {metadata.ticket_type}"]
        lines.append(f"Priority: {metadata.priority}")
        
        if metadata.severity != "minor":
            lines.append(f"Severity: {metadata.severity}")
        if metadata.assignee:
            lines.append(f"Assignee: {metadata.assignee}")
        if metadata.reporter != "system":
            lines.append(f"Reporter: {metadata.reporter}")
        if metadata.labels:
            lines.append(f"Labels: {', '.join(metadata.labels)}")
        if metadata.components:
            lines.append(f"Components: {', '.join(metadata.components)}")
        if metadata.due_date:
            lines.append(f"Due Date: {metadata.due_date}")
        if metadata.time_estimate:
            lines.append(f"Time Estimate: {metadata.time_estimate}h")
        if metadata.parent_ticket:
            lines.append(f"Parent: {metadata.parent_ticket}")
        if metadata.epic_link:
            lines.append(f"Epic: {metadata.epic_link}")
        
        lines.append("")  # Blank line separator
        lines.append(description)
        
        return '\n'.join(lines)
    
    async def create_ticket(self, project_id: str, title: str, description: str = "",
                          ticket_type: str = "task", priority: str = "medium",
                          assignee: str = None, labels: List[str] = None,
                          due_date: str = None, time_estimate: int = None,
                          parent_ticket: str = None, reporter: str = "system") -> Dict[str, Any]:
        """Create enhanced ticket using Vibe Kanban backend"""
        
        # Create metadata
        metadata = TicketMetadata(
            ticket_type=ticket_type,
            priority=priority,
            assignee=assignee,
            reporter=reporter,
            labels=labels or [],
            due_date=due_date,
            time_estimate=time_estimate,
            parent_ticket=parent_ticket
        )
        
        # Format description with metadata
        formatted_description = self._format_ticket_description(description, metadata)
        
        # Generate ticket number
        ticket_number = self._generate_ticket_number()
        enhanced_title = f"#{ticket_number}: {title}"
        
        try:
            # Create ticket in Vibe Kanban
            result = await self.vibe.create_task(
                project_id=project_id,
                title=enhanced_title,
                description=formatted_description
            )
            
            if result.get('success'):
                ticket_id = result['task']['id']
                
                # Store in hAIveMind memory for search and analytics
                await self._store_ticket_memory(ticket_id, {
                    'ticket_number': ticket_number,
                    'title': title,
                    'description': description,
                    'project_id': project_id,
                    'metadata': asdict(metadata),
                    'created_at': datetime.now().isoformat(),
                    'action': 'created'
                })
                
                # Trigger creation hooks
                await self._trigger_ticket_hooks('ticket_created', {
                    'ticket_id': ticket_id,
                    'ticket_number': ticket_number,
                    'title': title,
                    'project_id': project_id,
                    'metadata': asdict(metadata)
                })
                
                logger.info(f"🎫 Created ticket #{ticket_number}: {title}")
                
                return {
                    'success': True,
                    'ticket_id': ticket_id,
                    'ticket_number': ticket_number,
                    'title': enhanced_title,
                    'metadata': asdict(metadata)
                }
            else:
                logger.error(f"Failed to create ticket: {result}")
                return {'success': False, 'error': result.get('error', 'Unknown error')}
                
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_ticket(self, project_id: str, ticket_id: str) -> Dict[str, Any]:
        """Get enhanced ticket details"""
        try:
            result = await self.vibe.get_task(project_id=project_id, task_id=ticket_id)
            
            if result.get('success'):
                task = result['task']
                
                # Parse metadata from description
                clean_desc, metadata = self._parse_ticket_metadata(task.get('description', ''))
                
                # Extract ticket number from title
                title = task.get('title', '')
                ticket_match = re.match(r'#(\d+):\s*(.*)', title)
                if ticket_match:
                    ticket_number = int(ticket_match.group(1))
                    clean_title = ticket_match.group(2)
                else:
                    ticket_number = None
                    clean_title = title
                
                # Get memory context
                memory_context = await self._get_ticket_memory(ticket_id)
                
                enhanced_ticket = {
                    'id': ticket_id,
                    'ticket_number': ticket_number,
                    'title': clean_title,
                    'description': clean_desc,
                    'status': VIBE_STATUS_MAPPING.get(task.get('status'), task.get('status')),
                    'vibe_status': task.get('status'),
                    'project_id': project_id,
                    'metadata': asdict(metadata),
                    'created_at': task.get('created_at'),
                    'updated_at': task.get('updated_at'),
                    'memory_context': memory_context
                }
                
                return {'success': True, 'ticket': enhanced_ticket}
            else:
                return {'success': False, 'error': result.get('error', 'Ticket not found')}
                
        except Exception as e:
            logger.error(f"Error getting ticket {ticket_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def update_ticket_status(self, project_id: str, ticket_id: str, 
                                 new_status: str, updated_by: str = "system",
                                 comment: str = "") -> Dict[str, Any]:
        """Update ticket status with workflow validation"""
        try:
            # Map our status to Vibe Kanban status
            vibe_status = REVERSE_STATUS_MAPPING.get(new_status, new_status)
            
            # Update in Vibe Kanban
            result = await self.vibe.update_task(
                project_id=project_id,
                task_id=ticket_id,
                status=vibe_status
            )
            
            if result.get('success'):
                # Store status change in memory
                await self._store_ticket_memory(ticket_id, {
                    'action': 'status_changed',
                    'old_status': result.get('old_status'),
                    'new_status': new_status,
                    'vibe_status': vibe_status,
                    'changed_by': updated_by,
                    'comment': comment,
                    'changed_at': datetime.now().isoformat()
                })
                
                # Trigger status hooks
                await self._trigger_ticket_hooks('status_changed', {
                    'ticket_id': ticket_id,
                    'old_status': result.get('old_status'),
                    'new_status': new_status,
                    'changed_by': updated_by,
                    'comment': comment
                })
                
                logger.info(f"🎫 Updated ticket {ticket_id} status: {new_status}")
                return {'success': True, 'new_status': new_status}
            else:
                return {'success': False, 'error': result.get('error', 'Update failed')}
                
        except Exception as e:
            logger.error(f"Error updating ticket status: {e}")
            return {'success': False, 'error': str(e)}
    
    async def list_tickets(self, project_id: str, status: str = None, 
                         priority: str = None, assignee: str = None,
                         ticket_type: str = None, limit: int = 50) -> Dict[str, Any]:
        """List tickets with enhanced filtering"""
        try:
            # Get tasks from Vibe Kanban
            vibe_status = REVERSE_STATUS_MAPPING.get(status) if status else None
            result = await self.vibe.list_tasks(
                project_id=project_id,
                status=vibe_status,
                limit=limit
            )
            
            if result.get('success'):
                tasks = result['tasks']
                enhanced_tickets = []
                
                for task in tasks:
                    # Parse metadata
                    clean_desc, metadata = self._parse_ticket_metadata(task.get('description', ''))
                    
                    # Apply enhanced filters
                    if priority and metadata.priority != priority:
                        continue
                    if assignee and metadata.assignee != assignee:
                        continue
                    if ticket_type and metadata.ticket_type != ticket_type:
                        continue
                    
                    # Extract ticket number
                    title = task.get('title', '')
                    ticket_match = re.match(r'#(\d+):\s*(.*)', title)
                    if ticket_match:
                        ticket_number = int(ticket_match.group(1))
                        clean_title = ticket_match.group(2)
                    else:
                        ticket_number = None
                        clean_title = title
                    
                    enhanced_ticket = {
                        'id': task['id'],
                        'ticket_number': ticket_number,
                        'title': clean_title,
                        'status': VIBE_STATUS_MAPPING.get(task.get('status'), task.get('status')),
                        'vibe_status': task.get('status'),
                        'metadata': asdict(metadata),
                        'created_at': task.get('created_at'),
                        'updated_at': task.get('updated_at')
                    }
                    enhanced_tickets.append(enhanced_ticket)
                
                # Sort by ticket number if available
                enhanced_tickets.sort(key=lambda x: x['ticket_number'] or 0, reverse=True)
                
                return {
                    'success': True,
                    'tickets': enhanced_tickets,
                    'count': len(enhanced_tickets),
                    'project_id': project_id,
                    'applied_filters': {
                        'status': status,
                        'priority': priority,
                        'assignee': assignee,
                        'ticket_type': ticket_type,
                        'limit': limit
                    }
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to list tickets')}
                
        except Exception as e:
            logger.error(f"Error listing tickets: {e}")
            return {'success': False, 'error': str(e)}
    
    async def search_tickets(self, project_id: str, query: str, 
                           limit: int = 20) -> Dict[str, Any]:
        """Search tickets using hAIveMind memory and Vibe Kanban data"""
        try:
            # Search in hAIveMind memory
            memory_results = await self.storage.search_memories(
                query=f"ticket {query} project:{project_id}",
                category='workflow',
                limit=limit * 2  # Get more for filtering
            )
            
            # Get all tickets from project for text search
            all_tickets_result = await self.list_tickets(project_id, limit=200)
            
            search_results = []
            found_ticket_ids = set()
            
            # Add memory-based results
            for memory in memory_results.get('memories', []):
                content = memory.get('content', {})
                if 'ticket_id' in content:
                    ticket_id = content['ticket_id']
                    if ticket_id not in found_ticket_ids:
                        ticket_result = await self.get_ticket(project_id, ticket_id)
                        if ticket_result.get('success'):
                            ticket_result['ticket']['relevance_score'] = memory.get('score', 0.0)
                            search_results.append(ticket_result['ticket'])
                            found_ticket_ids.add(ticket_id)
            
            # Add text-based search from ticket data
            if all_tickets_result.get('success'):
                query_lower = query.lower()
                for ticket in all_tickets_result['tickets']:
                    if ticket['id'] not in found_ticket_ids:
                        # Simple text search in title and description
                        title_match = query_lower in ticket['title'].lower()
                        desc_match = query_lower in ticket.get('description', '').lower()
                        
                        if title_match or desc_match:
                            ticket['relevance_score'] = 1.0 if title_match else 0.5
                            search_results.append(ticket)
                            found_ticket_ids.add(ticket['id'])
            
            # Sort by relevance score
            search_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            return {
                'success': True,
                'tickets': search_results[:limit],
                'total_found': len(search_results),
                'query': query,
                'project_id': project_id
            }
            
        except Exception as e:
            logger.error(f"Error searching tickets: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_my_tickets(self, project_id: str, assignee: str, 
                           status: str = None) -> Dict[str, Any]:
        """Get tickets assigned to specific user"""
        return await self.list_tickets(
            project_id=project_id,
            assignee=assignee,
            status=status,
            limit=100
        )
    
    async def add_ticket_comment(self, project_id: str, ticket_id: str,
                               comment: str, author: str = "system") -> Dict[str, Any]:
        """Add comment to ticket (stored in hAIveMind memory)"""
        try:
            comment_data = {
                'ticket_id': ticket_id,
                'action': 'comment_added',
                'comment': comment,
                'author': author,
                'created_at': datetime.now().isoformat()
            }
            
            await self._store_ticket_memory(ticket_id, comment_data)
            
            # Also update the ticket description with comment if needed
            # This could be enhanced to maintain comment threads
            
            logger.info(f"💬 Added comment to ticket {ticket_id}")
            return {'success': True, 'comment_id': str(uuid.uuid4())}
            
        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_ticket_metrics(self, project_id: str, days: int = 30) -> Dict[str, Any]:
        """Get ticket metrics and analytics"""
        try:
            # Get all tickets for the project
            all_tickets = await self.list_tickets(project_id, limit=1000)
            
            if not all_tickets.get('success'):
                return {'success': False, 'error': 'Could not fetch tickets'}
            
            tickets = all_tickets['tickets']
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Calculate metrics
            metrics = {
                'total_tickets': len(tickets),
                'by_status': {},
                'by_priority': {},
                'by_type': {},
                'created_in_period': 0,
                'closed_in_period': 0,
                'average_resolution_time': 0,
                'overdue_tickets': 0,
                'critical_tickets': 0
            }
            
            resolution_times = []
            
            for ticket in tickets:
                status = ticket['status']
                metadata = ticket['metadata']
                
                # Count by status
                metrics['by_status'][status] = metrics['by_status'].get(status, 0) + 1
                
                # Count by priority
                priority = metadata.get('priority', 'medium')
                metrics['by_priority'][priority] = metrics['by_priority'].get(priority, 0) + 1
                
                # Count by type
                ticket_type = metadata.get('ticket_type', 'task')
                metrics['by_type'][ticket_type] = metrics['by_type'].get(ticket_type, 0) + 1
                
                # Created in period
                created_at = datetime.fromisoformat(ticket['created_at'].replace('Z', '+00:00'))
                if created_at >= cutoff_date:
                    metrics['created_in_period'] += 1
                
                # Closed in period
                if status == 'done' and ticket['updated_at']:
                    updated_at = datetime.fromisoformat(ticket['updated_at'].replace('Z', '+00:00'))
                    if updated_at >= cutoff_date:
                        metrics['closed_in_period'] += 1
                        
                        # Calculate resolution time
                        resolution_time = (updated_at - created_at).total_seconds() / 3600  # hours
                        resolution_times.append(resolution_time)
                
                # Critical tickets
                if priority in ['critical', 'emergency']:
                    metrics['critical_tickets'] += 1
                
                # Overdue tickets
                due_date_str = metadata.get('due_date')
                if due_date_str and status != 'done':
                    try:
                        due_date = datetime.fromisoformat(due_date_str)
                        if due_date < datetime.now():
                            metrics['overdue_tickets'] += 1
                    except:
                        pass
            
            # Calculate average resolution time
            if resolution_times:
                metrics['average_resolution_time'] = sum(resolution_times) / len(resolution_times)
            
            return {
                'success': True,
                'metrics': metrics,
                'project_id': project_id,
                'period_days': days,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _store_ticket_memory(self, ticket_id: str, data: Dict[str, Any]):
        """Store ticket event in hAIveMind memory"""
        try:
            memory_content = f"Ticket {ticket_id}: {data.get('action', 'update')}"
            if 'title' in data:
                memory_content = f"Ticket #{data.get('ticket_number', 'Unknown')}: {data['title']} - {data.get('action', 'update')}"
            
            await self.storage.store_memory(
                content=memory_content,
                context=json.dumps(data),
                category='workflow',
                tags=[f"ticket_{ticket_id}", "ticket_management", data.get('action', 'update')]
            )
        except Exception as e:
            logger.warning(f"Failed to store ticket memory: {e}")
    
    async def _get_ticket_memory(self, ticket_id: str) -> List[Dict[str, Any]]:
        """Get ticket-related memories"""
        try:
            results = await self.storage.search_memories(
                query=f"ticket {ticket_id}",
                category='workflow',
                limit=50
            )
            return results.get('memories', [])
        except Exception as e:
            logger.warning(f"Failed to get ticket memory: {e}")
            return []
    
    async def _trigger_ticket_hooks(self, event_type: str, context: Dict[str, Any]):
        """Trigger ticket-related hooks"""
        try:
            # This would integrate with the existing sync_hooks system
            # For now, just log the event
            logger.info(f"🪝 Ticket hook triggered: {event_type} for ticket {context.get('ticket_id')}")
        except Exception as e:
            logger.warning(f"Failed to trigger ticket hooks: {e}")