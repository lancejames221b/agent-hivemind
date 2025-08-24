#!/usr/bin/env python3
"""
hAIveMind MCP Server Hosting Service
Standalone server for MCP hosting with dashboard
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

import uvicorn

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mcp_hosting_dashboard import MCPHostingDashboard
from memory_server import MemoryStorage
from auth import AuthManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPHostingService:
    """Main MCP hosting service with dashboard"""
    
    def __init__(self, config_path: str = None):
        # Load configuration
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "config" / "config.json")
        
        with open(config_path) as f:
            self.config = json.load(f)
        
        # Initialize components
        self.storage = MemoryStorage(self.config)
        self.auth = AuthManager(self.config)
        self.dashboard = MCPHostingDashboard(self.config, self.storage, self.auth)
        
        # Get hosting config
        hosting_config = self.config.get('mcp_hosting', {})
        dashboard_config = hosting_config.get('dashboard', {})
        
        self.enabled = hosting_config.get('enabled', True)
        self.host = dashboard_config.get('host', '0.0.0.0')
        self.port = dashboard_config.get('port', 8910)
        self.debug = dashboard_config.get('debug', False)
        
        logger.info(f"🏭 MCP Hosting Service initialized on {self.host}:{self.port}")
    
    async def start(self):
        """Start the hosting service"""
        if not self.enabled:
            logger.info("🚫 MCP hosting service is disabled")
            return
        
        logger.info("🚀 Starting MCP hosting service...")
        
        # Start dashboard
        await self.dashboard.start()
        
        logger.info(f"✅ MCP hosting service started on http://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop the hosting service"""
        logger.info("🛑 Stopping MCP hosting service...")
        await self.dashboard.stop()
        logger.info("✅ MCP hosting service stopped")
    
    def run(self):
        """Run the hosting service with uvicorn"""
        try:
            logger.info("🏭 Starting hAIveMind MCP Server Hosting Service...")
            
            # Start the service
            asyncio.create_task(self.start())
            
            # Run with uvicorn
            uvicorn.run(
                self.dashboard.app,
                host=self.host,
                port=self.port,
                log_level="info" if not self.debug else "debug",
                access_log=True
            )
            
        except KeyboardInterrupt:
            logger.info("🛑 MCP hosting service stopped by user")
        except Exception as e:
            logger.error(f"💥 MCP hosting service error: {e}")
            raise

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="hAIveMind MCP Server Hosting Service")
    parser.add_argument(
        "--config", 
        type=str, 
        default=None,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind to (overrides config)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to (overrides config)"
    )
    
    args = parser.parse_args()
    
    # Print startup banner
    print("""
╭─────────────────────────────────────────────────────────────╮
│                                                             │
│    ██╗  ██╗ █████╗ ██╗██╗   ██╗███████╗███╗   ███╗██╗███╗   ██╗██████╗ │
│    ██║  ██║██╔══██╗██║██║   ██║██╔════╝████╗ ████║██║████╗  ██║██╔══██╗│
│    ███████║███████║██║██║   ██║█████╗  ██╔████╔██║██║██╔██╗ ██║██║  ██║│
│    ██╔══██║██╔══██║██║╚██╗ ██╔╝██╔══╝  ██║╚██╔╝██║██║██║╚██╗██║██║  ██║│
│    ██║  ██║██║  ██║██║ ╚████╔╝ ███████╗██║ ╚═╝ ██║██║██║ ╚████║██████╔╝│
│    ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝  ╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝ │
│                                                             │
│        🏭🤖 MCP Server Hosting Service - Starting 🤖🏭        │
│                                                             │
│             🔄 Initializing Server Hosting Platform...         │
│                                                             │
╰─────────────────────────────────────────────────────────────╯
    """)
    
    try:
        # Initialize service
        service = MCPHostingService(config_path=args.config)
        
        # Override host/port if provided
        if args.host:
            service.host = args.host
        if args.port:
            service.port = args.port
        
        # Run service
        service.run()
        
    except KeyboardInterrupt:
        logger.info("🛑 MCP hosting service stopped by user")
    except Exception as e:
        logger.error(f"💥 Critical hosting service error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()