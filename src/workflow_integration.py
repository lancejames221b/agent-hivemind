#!/usr/bin/env python3
"""
Workflow Automation Integration
Main integration point for the complete workflow automation system
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from .workflow_automation_engine import WorkflowAutomationEngine
from .workflow_automation_mcp_tools import register_workflow_automation_tools
from .workflow_haivemind_integration import create_workflow_haivemind_integration
from .workflow_validation_rollback import create_workflow_validation_rollback_system
from .workflow_dashboard import create_workflow_dashboard
from .workflow_api_server import create_workflow_api_server

logger = logging.getLogger(__name__)

class WorkflowAutomationSystem:
    """Complete workflow automation system integration"""
    
    def __init__(self, storage, config: Dict[str, Any]):
        self.storage = storage
        self.config = config
        
        # Core components
        self.workflow_engine = None
        self.haivemind_integration = None
        self.validation_rollback = None
        self.dashboard = None
        self.api_server = None
        self.mcp_tools = None
        
        # Configuration
        self.enable_dashboard = config.get('workflow_dashboard', {}).get('enabled', True)
        self.enable_api = config.get('workflow_api', {}).get('enabled', True)
        self.enable_haivemind = config.get('workflow_learning', {}).get('enabled', True)
        self.enable_validation = config.get('workflow_validation', {}).get('enabled', True)
    
    async def initialize(self):
        """Initialize the complete workflow automation system"""
        logger.info("Initializing workflow automation system...")
        
        # 1. Initialize core workflow engine
        self.workflow_engine = WorkflowAutomationEngine(self.storage, self.config)
        await self.workflow_engine.initialize()
        logger.info("Workflow engine initialized")
        
        # 2. Initialize hAIveMind integration
        if self.enable_haivemind:
            self.haivemind_integration = await create_workflow_haivemind_integration(
                self.workflow_engine, self.storage, self.config
            )
            logger.info("hAIveMind integration initialized")
        
        # 3. Initialize validation and rollback system
        if self.enable_validation:
            self.validation_rollback = await create_workflow_validation_rollback_system(
                self.storage, self.config
            )
            logger.info("Validation and rollback system initialized")
        
        # 4. Initialize dashboard
        if self.enable_dashboard:
            self.dashboard = await create_workflow_dashboard(self.storage, self.config)
            logger.info("Workflow dashboard initialized")
        
        # 5. Initialize API server
        if self.enable_api:
            self.api_server = await create_workflow_api_server(self.storage, self.config)
            logger.info("Workflow API server initialized")
        
        logger.info("Workflow automation system fully initialized")
    
    async def register_mcp_tools(self, server):
        """Register workflow MCP tools with the server"""
        if not self.workflow_engine:
            raise RuntimeError("Workflow system not initialized")
        
        self.mcp_tools = await register_workflow_automation_tools(
            server, self.storage, self.config
        )
        logger.info("Workflow MCP tools registered")
        return self.mcp_tools
    
    def start_dashboard(self, host: str = None, port: int = None):
        """Start the workflow dashboard server"""
        if not self.dashboard:
            raise RuntimeError("Dashboard not initialized")
        
        dashboard_config = self.config.get('workflow_dashboard', {})
        host = host or dashboard_config.get('host', '0.0.0.0')
        port = port or dashboard_config.get('port', 8900)
        
        logger.info(f"Starting workflow dashboard on {host}:{port}")
        self.dashboard.run(host, port)
    
    def start_api_server(self):
        """Start the workflow API server"""
        if not self.api_server:
            raise RuntimeError("API server not initialized")
        
        logger.info("Starting workflow API server")
        self.api_server.run()
    
    async def shutdown(self):
        """Shutdown the workflow automation system"""
        logger.info("Shutting down workflow automation system...")
        
        # Cleanup resources
        if self.workflow_engine:
            # Cancel any running executions
            for execution_id in list(self.workflow_engine.executions.keys()):
                await self.workflow_engine.cancel_workflow(execution_id)
        
        logger.info("Workflow automation system shutdown complete")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status and health information"""
        status = {
            'initialized': self.workflow_engine is not None,
            'components': {
                'workflow_engine': self.workflow_engine is not None,
                'haivemind_integration': self.haivemind_integration is not None,
                'validation_rollback': self.validation_rollback is not None,
                'dashboard': self.dashboard is not None,
                'api_server': self.api_server is not None,
                'mcp_tools': self.mcp_tools is not None
            }
        }
        
        if self.workflow_engine:
            status.update({
                'total_templates': len(self.workflow_engine.templates),
                'active_executions': len(self.workflow_engine.executions),
                'execution_history': len(self.workflow_engine.execution_history),
                'command_sequences_learned': len(self.workflow_engine.command_sequences)
            })
        
        return status

async def create_workflow_automation_system(storage, config: Dict[str, Any]) -> WorkflowAutomationSystem:
    """Create and initialize the complete workflow automation system"""
    system = WorkflowAutomationSystem(storage, config)
    await system.initialize()
    return system

# Convenience functions for quick setup

async def setup_workflow_mcp_tools(server, storage, config: Dict[str, Any]):
    """Quick setup for MCP tools only"""
    system = await create_workflow_automation_system(storage, config)
    return await system.register_mcp_tools(server)

async def setup_workflow_dashboard(storage, config: Dict[str, Any], 
                                 host: str = '0.0.0.0', port: int = 8900):
    """Quick setup for dashboard only"""
    system = await create_workflow_automation_system(storage, config)
    system.start_dashboard(host, port)

async def setup_workflow_api(storage, config: Dict[str, Any]):
    """Quick setup for API server only"""
    system = await create_workflow_automation_system(storage, config)
    system.start_api_server()

# Example configuration
DEFAULT_CONFIG = {
    "workflow_learning": {
        "enabled": True,
        "pattern_analysis": True,
        "collective_intelligence": True
    },
    "workflow_sharing": {
        "enabled": True,
        "auto_share_success": True,
        "auto_share_failures": True
    },
    "workflow_optimization": {
        "enabled": True,
        "auto_optimize": True,
        "optimization_threshold": 0.8
    },
    "workflow_validation": {
        "enabled": True,
        "default_level": "standard",
        "strict_mode": False,
        "auto_validate": True
    },
    "workflow_rollback": {
        "enabled": True,
        "default_strategy": "graceful",
        "auto_rollback": True,
        "checkpoint_interval": 3
    },
    "workflow_dashboard": {
        "enabled": True,
        "host": "0.0.0.0",
        "port": 8900,
        "enable_designer": True,
        "enable_analytics": True,
        "real_time_updates": True
    },
    "workflow_api": {
        "enabled": True,
        "host": "0.0.0.0",
        "port": 8902,
        "api_key_required": True,
        "api_keys": [],
        "allowed_origins": ["*"],
        "rate_limit": 100,
        "enable_webhooks": True,
        "enable_websockets": True
    }
}

if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        # Mock storage for example
        class MockStorage:
            def __init__(self):
                self.memories = []
                self.agent_id = "example_agent"
                self.machine_id = "example_machine"
            
            async def store_memory(self, content, category, context="", metadata=None, tags=None):
                memory = {
                    'id': f"mem_{len(self.memories)}",
                    'content': content,
                    'category': category,
                    'context': context,
                    'metadata': metadata or {},
                    'tags': tags or []
                }
                self.memories.append(memory)
                return memory['id']
            
            async def search_memories(self, query, category=None, limit=10):
                return []
        
        storage = MockStorage()
        config = DEFAULT_CONFIG.copy()
        
        # Initialize system
        system = await create_workflow_automation_system(storage, config)
        
        # Get system status
        status = system.get_system_status()
        print(f"System Status: {status}")
        
        # Example: Get workflow suggestions
        suggestions = await system.workflow_engine.suggest_workflows(
            context="system maintenance required",
            intent="perform maintenance"
        )
        print(f"Workflow Suggestions: {len(suggestions)} found")
        
        # Example: Execute a workflow
        if suggestions:
            execution_id = await system.workflow_engine.execute_workflow(
                template_id=suggestions[0].workflow_id,
                parameters={"priority": "medium"}
            )
            print(f"Started workflow execution: {execution_id}")
        
        # Shutdown
        await system.shutdown()
    
    asyncio.run(main())