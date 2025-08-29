#!/usr/bin/env python3
"""
Comet Browser Integration System
Provides lightweight portal and directive system for AI-browser integration
"""

import json
import time
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class CometDirectiveSystem:
    """Manages directives and communication with Comet Browser"""
    
    def __init__(self, config: Dict, storage=None):
        self.config = config
        self.storage = storage
        self.enabled = self.config.get('enabled', False)
        self.active_directives = []
        self.sessions = {}  # session_id -> session_data
        
        # Configuration
        self.max_directives = self.config.get('directives', {}).get('max_active_directives', 10)
        self.refresh_interval = self.config.get('directives', {}).get('refresh_interval_seconds', 30)
        self.priority_levels = self.config.get('directives', {}).get('priority_levels', ["low", "normal", "high", "urgent"])
        
        logger.info(f"🚀 Comet integration {'enabled' if self.enabled else 'disabled'}")
    
    def authenticate_comet(self, password: str) -> Optional[str]:
        """Authenticate Comet browser and return session token"""
        if not self.enabled:
            return None
            
        expected_password = self.config.get('authentication', {}).get('password', 'R3dca070111-001')
        
        if password != expected_password:
            logger.warning("🚀 Comet authentication failed - incorrect password")
            return None
        
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        session_timeout_hours = self.config.get('authentication', {}).get('session_timeout_hours', 8)
        expires_at = datetime.now() + timedelta(hours=session_timeout_hours)
        
        self.sessions[session_token] = {
            'created_at': datetime.now(),
            'expires_at': expires_at,
            'ip_address': None,  # Will be set by request handler
            'user_agent': 'Comet Browser',
            'active': True
        }
        
        logger.info(f"🚀 Comet authenticated successfully - session expires at {expires_at}")
        return session_token
    
    def validate_session(self, session_token: str) -> bool:
        """Validate Comet session token"""
        if not session_token or session_token not in self.sessions:
            return False
        
        session = self.sessions[session_token]
        
        if not session.get('active', False):
            return False
        
        if datetime.now() > session['expires_at']:
            # Session expired
            session['active'] = False
            logger.info("🚀 Comet session expired")
            return False
        
        return True
    
    def create_directive(self, directive_type: str, content: Dict[str, Any], 
                        priority: str = "normal") -> str:
        """Create a new directive for Comet to execute"""
        if len(self.active_directives) >= self.max_directives:
            # Remove oldest low priority directive
            self.active_directives = [d for d in self.active_directives if d['priority'] != 'low']
        
        directive_id = f"dir_{int(time.time())}_{secrets.token_hex(4)}"
        
        directive = {
            'id': directive_id,
            'type': directive_type,
            'content': content,
            'priority': priority if priority in self.priority_levels else 'normal',
            'created_at': datetime.now().isoformat(),
            'status': 'pending',
            'expires_at': (datetime.now() + timedelta(hours=2)).isoformat(),
            'attempts': 0,
            'max_attempts': 3
        }
        
        # Insert directive in priority order
        self.active_directives.append(directive)
        self.active_directives.sort(key=lambda x: self.priority_levels.index(x['priority']), reverse=True)
        
        logger.info(f"🚀 Created Comet directive: {directive_type} ({priority})")
        return directive_id
    
    def get_active_directives(self) -> List[Dict[str, Any]]:
        """Get all active directives for Comet to process"""
        # Clean up expired directives
        now = datetime.now()
        self.active_directives = [
            d for d in self.active_directives 
            if datetime.fromisoformat(d['expires_at']) > now and d['status'] != 'completed'
        ]
        
        return self.active_directives
    
    def update_directive_status(self, directive_id: str, status: str, 
                              result: Optional[Dict[str, Any]] = None) -> bool:
        """Update directive status and result"""
        for directive in self.active_directives:
            if directive['id'] == directive_id:
                directive['status'] = status
                directive['updated_at'] = datetime.now().isoformat()
                
                if result:
                    directive['result'] = result
                
                if status == 'failed':
                    directive['attempts'] += 1
                    if directive['attempts'] < directive['max_attempts']:
                        directive['status'] = 'retry'
                
                logger.info(f"🚀 Updated directive {directive_id} status: {status}")
                return True
        
        return False
    
    async def get_status_dashboard(self) -> Dict[str, Any]:
        """Get status dashboard data optimized for AI reading"""
        if not self.storage:
            return {"error": "Storage not available"}
        
        try:
            # Get basic stats
            active_sessions = len([s for s in self.sessions.values() if s.get('active', False)])
            active_directives_count = len(self.get_active_directives())
            
            # Get recent memories
            recent_memories = []
            if hasattr(self.storage, 'search_memories'):
                memories = await self.storage.search_memories("", limit=5)  # Get recent 5
                for memory in memories[:5]:
                    recent_memories.append({
                        'id': memory.get('id', 'unknown'),
                        'content': memory.get('content', '')[:100],  # Truncate for AI
                        'category': memory.get('category', 'unknown'),
                        'timestamp': memory.get('created_at', 'unknown')
                    })
            
            # Get agent roster
            agent_count = 0
            if hasattr(self.storage, 'search_memories'):
                agent_memories = await self.storage.search_memories("agent-registration", category="infrastructure", limit=20)
                agent_count = len(agent_memories)
            
            return {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'system': {
                    'active_sessions': active_sessions,
                    'active_directives': active_directives_count,
                    'agent_count': agent_count,
                    'memory_categories': len(self.config.get('memory', {}).get('categories', [])),
                },
                'recent_activity': recent_memories,
                'directives': {
                    'active': active_directives_count,
                    'max_allowed': self.max_directives,
                    'refresh_interval': f"{self.refresh_interval}s"
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating status dashboard: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def create_memory_search_directive(self, query: str, category: Optional[str] = None, 
                                     limit: int = 5) -> str:
        """Create a memory search directive"""
        content = {
            'action': 'search_memories',
            'parameters': {
                'query': query,
                'category': category,
                'limit': limit
            },
            'instruction': f'Search hAIveMind collective memory for: "{query}"',
            'expected_format': 'json_list',
            'success_criteria': 'Return relevant memories with content and metadata'
        }
        
        return self.create_directive('memory_search', content, 'normal')
    
    def create_agent_status_directive(self, limit: int = 10) -> str:
        """Create an agent status check directive"""
        content = {
            'action': 'get_agent_roster',
            'parameters': {
                'limit': limit,
                'include_inactive': False
            },
            'instruction': 'Check status of all active hAIveMind agents',
            'expected_format': 'json_list',
            'success_criteria': 'Return list of active agents with capabilities'
        }
        
        return self.create_directive('agent_status', content, 'normal')
    
    def create_report_directive(self, report_type: str, parameters: Dict[str, Any]) -> str:
        """Create a report generation directive"""
        content = {
            'action': 'generate_report',
            'parameters': {
                'type': report_type,
                **parameters
            },
            'instruction': f'Generate {report_type} report with specified parameters',
            'expected_format': 'structured_report',
            'success_criteria': 'Return formatted report with summary and details'
        }
        
        return self.create_directive('report_generation', content, 'normal')
    
    def sanitize_output(self, data: Any) -> Any:
        """Sanitize output to prevent prompt injection attacks"""
        if not self.config.get('security', {}).get('sanitize_output', True):
            return data
        
        if isinstance(data, str):
            # Remove potentially dangerous patterns
            dangerous_patterns = [
                'ignore previous instructions',
                'system prompt',
                'act as',
                'pretend to be',
                'you are now',
                'new instructions:',
                'override:',
                'execute:',
                'run command'
            ]
            
            sanitized = data
            for pattern in dangerous_patterns:
                sanitized = sanitized.replace(pattern, '[SANITIZED]')
            
            return sanitized
        
        elif isinstance(data, dict):
            return {k: self.sanitize_output(v) for k, v in data.items()}
        
        elif isinstance(data, list):
            return [self.sanitize_output(item) for item in data]
        
        return data
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        now = datetime.now()
        expired_sessions = [
            token for token, session in self.sessions.items()
            if session['expires_at'] < now
        ]
        
        for token in expired_sessions:
            del self.sessions[token]
        
        if expired_sessions:
            logger.info(f"🚀 Cleaned up {len(expired_sessions)} expired Comet sessions")