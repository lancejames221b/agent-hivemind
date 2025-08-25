#!/usr/bin/env python3
"""
Rules Dashboard Integration - Integrates Rules Dashboard with main hAIveMind Dashboard
Provides seamless integration of rules management into the existing dashboard system

Author: Lance James, Unit 221B Inc
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .rules_dashboard import RulesDashboard
from .dashboard_server import DashboardServer

class RulesDashboardIntegration:
    """Integration layer for Rules Dashboard with main hAIveMind Dashboard"""
    
    def __init__(self, dashboard_server: DashboardServer, db_path: str = "database/rules.db"):
        self.dashboard_server = dashboard_server
        self.rules_dashboard = RulesDashboard(
            db_path=db_path,
            chroma_client=dashboard_server._get_config().get('chroma_client'),
            redis_client=dashboard_server._get_config().get('redis_client'),
            memory_storage=dashboard_server._get_memory_storage()
        )
        
        # Integrate rules dashboard routes
        self._integrate_routes()
        
        # Add rules dashboard to navigation
        self._add_navigation_items()
    
    def _integrate_routes(self):
        """Integrate rules dashboard routes into main dashboard"""
        
        # Get rules dashboard router
        rules_router = self.rules_dashboard.get_router()
        
        # Include the router in the main app
        self.dashboard_server.app.include_router(rules_router)
        
        # Add rules dashboard HTML route
        @self.dashboard_server.app.get("/admin/rules", response_class=HTMLResponse)
        async def rules_dashboard_page(current_user: dict = Depends(self.dashboard_server.get_current_user)):
            """Serve the rules dashboard HTML page"""
            try:
                # Read the rules dashboard template
                template_path = Path("templates/rules_dashboard.html")
                if template_path.exists():
                    with open(template_path, 'r') as f:
                        html_content = f.read()
                    return HTMLResponse(content=html_content)
                else:
                    # Return a basic HTML page if template doesn't exist
                    return HTMLResponse(content=self._get_fallback_html())
                    
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error loading rules dashboard: {str(e)}")
        
        # Add rules dashboard API status endpoint
        @self.dashboard_server.app.get("/api/v1/rules/status")
        async def rules_dashboard_status():
            """Get rules dashboard status"""
            try:
                stats = self.rules_dashboard.db.get_rule_statistics()
                return {
                    "status": "active",
                    "total_rules": stats.get('total_rules', 0),
                    "active_rules": stats.get('by_status', {}).get('active', 0),
                    "templates_available": len(self.rules_dashboard.db.list_rule_templates()),
                    "database_path": str(self.rules_dashboard.db.db_path),
                    "features": {
                        "visual_builder": True,
                        "templates": True,
                        "import_export": True,
                        "conflict_detection": True,
                        "analytics": True,
                        "haivemind_integration": True
                    }
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e)
                }
        
        # Add rules widget for main dashboard
        @self.dashboard_server.app.get("/api/v1/dashboard/rules-widget")
        async def rules_widget_data(current_user: dict = Depends(self.dashboard_server.get_current_user)):
            """Get rules data for dashboard widget"""
            try:
                stats = self.rules_dashboard.db.get_rule_statistics()
                recent_activity = self.rules_dashboard.db.get_recent_rule_activity(days=7)
                conflicts = await self.rules_dashboard.validator.detect_all_conflicts()
                
                return {
                    "stats": {
                        "total_rules": stats.get('total_rules', 0),
                        "active_rules": stats.get('by_status', {}).get('active', 0),
                        "inactive_rules": stats.get('by_status', {}).get('inactive', 0),
                        "conflicts": len(conflicts)
                    },
                    "recent_activity": recent_activity[:5],  # Last 5 activities
                    "top_rule_types": stats.get('by_type', {}),
                    "performance_summary": self.rules_dashboard.performance_analyzer.get_overall_performance(days=7)
                }
            except Exception as e:
                return {
                    "error": str(e),
                    "stats": {"total_rules": 0, "active_rules": 0, "inactive_rules": 0, "conflicts": 0}
                }
    
    def _add_navigation_items(self):
        """Add rules dashboard items to main navigation"""
        # This would integrate with the main dashboard's navigation system
        # Implementation depends on how the main dashboard handles navigation
        pass
    
    def _get_fallback_html(self) -> str:
        """Get fallback HTML if template file is not available"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rules Dashboard - hAIveMind</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8f9fa;
            margin: 0;
            padding: 2rem;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .error {
            color: #dc3545;
            margin-bottom: 1rem;
        }
        .btn {
            background: #007bff;
            color: white;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 5px;
            text-decoration: none;
            display: inline-block;
            margin: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Rules Dashboard</h1>
        <div class="error">
            <p>Rules dashboard template not found. Please ensure the template file is available.</p>
        </div>
        <p>The Rules Dashboard provides comprehensive CRUD operations for hAIveMind rules management.</p>
        <a href="/api/v1/rules/" class="btn">Rules API</a>
        <a href="/admin/dashboard.html" class="btn">Main Dashboard</a>
    </div>
</body>
</html>
        """.strip()
    
    def get_dashboard_integration_info(self) -> Dict[str, Any]:
        """Get information about the rules dashboard integration"""
        return {
            "integration_status": "active",
            "rules_dashboard_url": "/admin/rules",
            "api_base_url": "/api/v1/rules",
            "features": {
                "visual_rule_builder": True,
                "rule_templates": True,
                "import_export": True,
                "conflict_detection": True,
                "performance_analytics": True,
                "haivemind_awareness": True
            },
            "navigation_items": [
                {
                    "name": "Rules Dashboard",
                    "url": "/admin/rules",
                    "icon": "fas fa-cogs",
                    "description": "Manage hAIveMind rules with full CRUD operations"
                },
                {
                    "name": "Rule Templates",
                    "url": "/admin/rules#templates",
                    "icon": "fas fa-copy",
                    "description": "Browse and use rule templates"
                },
                {
                    "name": "Rule Analytics",
                    "url": "/admin/rules#analytics",
                    "icon": "fas fa-chart-bar",
                    "description": "View rule performance and usage analytics"
                }
            ]
        }

def integrate_rules_dashboard(dashboard_server: DashboardServer, db_path: str = "database/rules.db") -> RulesDashboardIntegration:
    """
    Integrate Rules Dashboard with the main hAIveMind Dashboard
    
    Args:
        dashboard_server: The main dashboard server instance
        db_path: Path to the rules database
    
    Returns:
        RulesDashboardIntegration instance
    """
    integration = RulesDashboardIntegration(dashboard_server, db_path)
    
    # Store reference in dashboard server for access
    dashboard_server.rules_dashboard_integration = integration
    
    return integration

# Enhanced Dashboard Server with Rules Integration
class EnhancedDashboardServer(DashboardServer):
    """Enhanced Dashboard Server with integrated Rules Dashboard"""
    
    def __init__(self, db_path: str = "database/haivemind.db", rules_db_path: str = "database/rules.db"):
        super().__init__(db_path)
        
        # Initialize rules dashboard integration
        self.rules_integration = integrate_rules_dashboard(self, rules_db_path)
        
        # Add rules dashboard to main navigation
        self._add_rules_navigation()
        
        # Enhanced dashboard stats including rules
        self._enhance_dashboard_stats()
    
    def _add_rules_navigation(self):
        """Add rules dashboard to main navigation"""
        # Add rules dashboard routes to main navigation
        @self.app.get("/api/v1/navigation/items")
        async def get_navigation_items(current_user: dict = Depends(self.get_current_user)):
            """Get navigation items including rules dashboard"""
            base_items = [
                {
                    "name": "Dashboard",
                    "url": "/admin/dashboard.html",
                    "icon": "fas fa-tachometer-alt",
                    "description": "Main dashboard overview"
                },
                {
                    "name": "Devices",
                    "url": "/admin/devices.html",
                    "icon": "fas fa-laptop",
                    "description": "Manage connected devices"
                },
                {
                    "name": "API Keys",
                    "url": "/admin/keys.html",
                    "icon": "fas fa-key",
                    "description": "Manage API keys"
                },
                {
                    "name": "Configurations",
                    "url": "/admin/configs.html",
                    "icon": "fas fa-cog",
                    "description": "Generate MCP configurations"
                }
            ]
            
            # Add rules dashboard items
            rules_items = self.rules_integration.get_dashboard_integration_info()["navigation_items"]
            
            return {
                "items": base_items + rules_items,
                "total": len(base_items) + len(rules_items)
            }
    
    def _enhance_dashboard_stats(self):
        """Enhance dashboard stats to include rules information"""
        original_get_stats = self.app.routes
        
        @self.app.get("/api/v1/admin/enhanced-stats")
        async def get_enhanced_dashboard_stats(current_user: dict = Depends(self.get_current_user)):
            """Get enhanced dashboard statistics including rules"""
            try:
                # Get base stats
                base_stats = self.db.get_dashboard_stats()
                
                # Get rules stats
                rules_stats = await self.rules_integration.rules_dashboard.db.get_rule_statistics()
                
                # Get rules performance
                rules_performance = self.rules_integration.rules_dashboard.performance_analyzer.get_overall_performance(days=7)
                
                # Combine stats
                enhanced_stats = {
                    **base_stats,
                    "rules": {
                        "total_rules": rules_stats.get('total_rules', 0),
                        "active_rules": rules_stats.get('by_status', {}).get('active', 0),
                        "rule_types": rules_stats.get('by_type', {}),
                        "recent_changes": rules_stats.get('recent_changes', 0),
                        "performance": {
                            "total_evaluations": rules_performance.get('total_evaluations', 0),
                            "average_execution_time": rules_performance.get('overall_performance', {}).get('average_execution_time_ms', 0)
                        }
                    },
                    "integration": {
                        "rules_dashboard_active": True,
                        "features_enabled": [
                            "visual_builder",
                            "templates",
                            "analytics",
                            "conflict_detection",
                            "haivemind_awareness"
                        ]
                    }
                }
                
                return enhanced_stats
                
            except Exception as e:
                # Fallback to base stats if rules integration fails
                base_stats = self.db.get_dashboard_stats()
                base_stats["rules_error"] = str(e)
                return base_stats

# Standalone enhanced server runner
def main():
    import uvicorn
    
    # Create enhanced dashboard with rules integration
    dashboard = EnhancedDashboardServer()
    
    print("🚀 Starting Enhanced hAIveMind Dashboard with Rules Management...")
    print("📊 Main Dashboard: http://localhost:8900/admin/dashboard.html")
    print("⚙️  Rules Dashboard: http://localhost:8900/admin/rules")
    print("🔧 API Documentation: http://localhost:8900/docs")
    print("📈 Rules API: http://localhost:8900/api/v1/rules/")
    
    uvicorn.run(dashboard.app, host="0.0.0.0", port=8900)

if __name__ == "__main__":
    main()