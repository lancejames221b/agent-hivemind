#!/usr/bin/env python3
"""
hAIveMind MCP Server Hosting Tools
MCP tools for managing hosted MCP servers
"""

import asyncio
import base64
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp_server_host import MCPServerHost

logger = logging.getLogger(__name__)

class MCPHostingTools:
    """MCP tools for server hosting functionality"""
    
    def __init__(self, config: Dict[str, Any], storage=None):
        self.config = config
        self.storage = storage
        self.host = MCPServerHost(config, storage)
        self._started = False
    
    async def ensure_started(self):
        """Ensure the hosting service is started"""
        if not self._started:
            await self.host.start()
            self._started = True
    
    async def upload_mcp_server(self,
                               name: str,
                               archive_base64: str,
                               command: List[str],
                               description: str = "",
                               environment: Optional[Dict[str, str]] = None,
                               auto_restart: bool = True,
                               resource_limits: Optional[Dict[str, Any]] = None,
                               health_check_url: Optional[str] = None,
                               user_id: str = "default") -> str:
        """Upload and deploy a new MCP server from base64-encoded archive"""
        try:
            await self.ensure_started()
            
            # Decode archive data
            try:
                archive_data = base64.b64decode(archive_base64)
            except Exception as e:
                return f"❌ Error decoding archive: {e}"
            
            # Prepare configuration
            config = {
                "name": name,
                "description": description,
                "command": command,
                "environment": environment or {},
                "auto_restart": auto_restart,
                "resource_limits": resource_limits or {},
                "health_check_url": health_check_url
            }
            
            # Upload server
            result = await self.host.upload_server(name, archive_data, config, user_id)
            
            # Store upload event in hAIveMind
            if self.storage:
                await self.storage.store_memory(
                    content=f"MCP server '{name}' uploaded via hAIveMind hosting",
                    category="infrastructure",
                    context="MCP server hosting - upload",
                    metadata={
                        "server_id": result["server_id"],
                        "server_name": name,
                        "command": command,
                        "user_id": user_id,
                        "upload_timestamp": time.time()
                    },
                    tags=["mcp-hosting", "upload", "server-deployment", name.lower().replace(' ', '-')]
                )
            
            return f"✅ MCP server '{name}' uploaded successfully!\n\n" \
                   f"**Server ID**: {result['server_id']}\n" \
                   f"**Status**: {result['status']}\n" \
                   f"**Message**: {result['message']}\n\n" \
                   f"Use `start_mcp_server` to start the server."
            
        except Exception as e:
            logger.error(f"Error uploading MCP server: {e}")
            return f"❌ Error uploading MCP server '{name}': {str(e)}"
    
    async def start_mcp_server(self, server_id: str) -> str:
        """Start a hosted MCP server"""
        try:
            await self.ensure_started()
            
            result = await self.host.start_server(server_id)
            
            # Store start event in hAIveMind with performance tracking
            if self.storage:
                server_status = await self.host.get_server_status(server_id)
                await self.storage.store_memory(
                    content=f"MCP server started: {server_status.get('name', server_id)}",
                    category="infrastructure",
                    context="MCP server hosting - start",
                    metadata={
                        "server_id": server_id,
                        "server_name": server_status.get('name'),
                        "start_timestamp": time.time(),
                        "pid": server_status.get('pid'),
                        "restart_count": server_status.get('restart_count', 0)
                    },
                    tags=["mcp-hosting", "start", "server-lifecycle", server_id]
                )
            
            return f"✅ {result['message']}\n\n" \
                   f"**Server ID**: {result['server_id']}\n" \
                   f"**Status**: {result['status']}"
            
        except Exception as e:
            logger.error(f"Error starting MCP server: {e}")
            return f"❌ Error starting MCP server: {str(e)}"
    
    async def stop_mcp_server(self, server_id: str) -> str:
        """Stop a hosted MCP server"""
        try:
            await self.ensure_started()
            
            # Get status before stopping for performance tracking
            server_status = await self.host.get_server_status(server_id)
            uptime = server_status.get('uptime_seconds', 0)
            
            result = await self.host.stop_server(server_id)
            
            # Store stop event in hAIveMind with performance data
            if self.storage:
                await self.storage.store_memory(
                    content=f"MCP server stopped: {server_status.get('name', server_id)}",
                    category="infrastructure",
                    context="MCP server hosting - stop",
                    metadata={
                        "server_id": server_id,
                        "server_name": server_status.get('name'),
                        "stop_timestamp": time.time(),
                        "uptime_seconds": uptime,
                        "restart_count": server_status.get('restart_count', 0),
                        "resource_usage": server_status.get('resource_usage', {})
                    },
                    tags=["mcp-hosting", "stop", "server-lifecycle", "performance-data", server_id]
                )
            
            return f"🛑 {result['message']}\n\n" \
                   f"**Server ID**: {result['server_id']}\n" \
                   f"**Status**: {result['status']}\n" \
                   f"**Uptime**: {uptime:.1f} seconds"
            
        except Exception as e:
            logger.error(f"Error stopping MCP server: {e}")
            return f"❌ Error stopping MCP server: {str(e)}"
    
    async def restart_mcp_server(self, server_id: str) -> str:
        """Restart a hosted MCP server"""
        try:
            await self.ensure_started()
            
            result = await self.host.restart_server(server_id)
            
            # Store restart event in hAIveMind
            if self.storage:
                server_status = await self.host.get_server_status(server_id)
                await self.storage.store_memory(
                    content=f"MCP server restarted: {server_status.get('name', server_id)}",
                    category="infrastructure",
                    context="MCP server hosting - restart",
                    metadata={
                        "server_id": server_id,
                        "server_name": server_status.get('name'),
                        "restart_timestamp": time.time(),
                        "restart_count": server_status.get('restart_count', 0),
                        "reason": "manual_restart"
                    },
                    tags=["mcp-hosting", "restart", "server-lifecycle", server_id]
                )
            
            return f"🔄 {result['message']}\n\n" \
                   f"**Server ID**: {result['server_id']}\n" \
                   f"**Status**: {result['status']}"
            
        except Exception as e:
            logger.error(f"Error restarting MCP server: {e}")
            return f"❌ Error restarting MCP server: {str(e)}"
    
    async def delete_mcp_server(self, server_id: str, force: bool = False) -> str:
        """Delete a hosted MCP server"""
        try:
            await self.ensure_started()
            
            # Get server info before deletion
            server_status = await self.host.get_server_status(server_id)
            
            result = await self.host.delete_server(server_id, force)
            
            # Store deletion event in hAIveMind
            if self.storage:
                await self.storage.store_memory(
                    content=f"MCP server deleted: {server_status.get('name', server_id)}",
                    category="infrastructure",
                    context="MCP server hosting - deletion",
                    metadata={
                        "server_id": server_id,
                        "server_name": server_status.get('name'),
                        "deletion_timestamp": time.time(),
                        "forced": force,
                        "total_uptime": server_status.get('uptime_seconds', 0),
                        "total_restarts": server_status.get('restart_count', 0)
                    },
                    tags=["mcp-hosting", "deletion", "server-lifecycle", server_id]
                )
            
            return f"🗑️ {result['message']}\n\n" \
                   f"**Server ID**: {result['server_id']}\n" \
                   f"**Status**: {result['status']}"
            
        except Exception as e:
            logger.error(f"Error deleting MCP server: {e}")
            return f"❌ Error deleting MCP server: {str(e)}"
    
    async def get_mcp_server_status(self, server_id: str) -> str:
        """Get detailed status of a hosted MCP server"""
        try:
            await self.ensure_started()
            
            status = await self.host.get_server_status(server_id)
            
            # Format status for display
            status_emoji = {
                "running": "🟢",
                "stopped": "🔴",
                "starting": "🟡",
                "failed": "❌",
                "error": "💥"
            }.get(status.get('status', 'unknown'), "❓")
            
            uptime_str = ""
            if status.get('uptime_seconds'):
                uptime = status['uptime_seconds']
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                seconds = int(uptime % 60)
                uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            resource_info = ""
            if status.get('resource_usage'):
                res = status['resource_usage']
                resource_info = f"\n**Resource Usage**:\n" \
                               f"  • CPU: {res.get('cpu_percent', 0):.1f}%\n" \
                               f"  • Memory: {res.get('memory_mb', 0):.1f} MB ({res.get('memory_percent', 0):.1f}%)\n" \
                               f"  • Threads: {res.get('num_threads', 0)}\n" \
                               f"  • Open Files: {res.get('open_files', 0)}\n" \
                               f"  • Connections: {res.get('connections', 0)}"
            
            recent_logs = ""
            if status.get('recent_logs'):
                recent_logs = "\n**Recent Logs**:\n"
                for log in status['recent_logs'][-5:]:  # Last 5 entries
                    timestamp = time.strftime('%H:%M:%S', time.localtime(log['timestamp']))
                    stream_emoji = "📤" if log['stream'] == 'stdout' else "🔴"
                    recent_logs += f"  {stream_emoji} [{timestamp}] {log['message'][:100]}...\n"
            
            result = f"{status_emoji} **MCP Server Status**\n\n" \
                    f"**Name**: {status.get('name', 'Unknown')}\n" \
                    f"**Server ID**: {status.get('server_id')}\n" \
                    f"**Status**: {status.get('status', 'unknown')}\n" \
                    f"**PID**: {status.get('pid', 'N/A')}\n" \
                    f"**Uptime**: {uptime_str or 'N/A'}\n" \
                    f"**Restart Count**: {status.get('restart_count', 0)}\n" \
                    f"**Health Check Failures**: {status.get('health_check_failures', 0)}" \
                    f"{resource_info}" \
                    f"{recent_logs}"
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting MCP server status: {e}")
            return f"❌ Error getting server status: {str(e)}"
    
    async def list_mcp_servers(self) -> str:
        """List all hosted MCP servers"""
        try:
            await self.ensure_started()
            
            servers = await self.host.list_servers()
            
            if not servers:
                return "📋 No MCP servers are currently hosted."
            
            result = f"📋 **Hosted MCP Servers** ({len(servers)} total)\n\n"
            
            for server in servers:
                status_emoji = {
                    "running": "🟢",
                    "stopped": "🔴", 
                    "starting": "🟡",
                    "failed": "❌",
                    "error": "💥"
                }.get(server.get('status', 'unknown'), "❓")
                
                uptime = ""
                if server.get('uptime_seconds'):
                    hours = int(server['uptime_seconds'] // 3600)
                    minutes = int((server['uptime_seconds'] % 3600) // 60)
                    uptime = f" (up {hours:02d}:{minutes:02d})"
                
                resource_summary = ""
                if server.get('resource_usage'):
                    res = server['resource_usage']
                    resource_summary = f" | CPU: {res.get('cpu_percent', 0):.1f}% | RAM: {res.get('memory_mb', 0):.0f}MB"
                
                result += f"{status_emoji} **{server.get('name', 'Unknown')}**\n" \
                         f"   ID: `{server.get('server_id')}`\n" \
                         f"   Status: {server.get('status', 'unknown')}{uptime}\n" \
                         f"   Restarts: {server.get('restart_count', 0)}{resource_summary}\n\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing MCP servers: {e}")
            return f"❌ Error listing servers: {str(e)}"
    
    async def get_mcp_server_logs(self, server_id: str, lines: int = 50) -> str:
        """Get logs for a hosted MCP server"""
        try:
            await self.ensure_started()
            
            logs = await self.host.get_server_logs(server_id, lines)
            
            if not logs:
                return f"📝 No logs available for server {server_id}"
            
            # Get server name for display
            try:
                status = await self.host.get_server_status(server_id)
                server_name = status.get('name', server_id)
            except:
                server_name = server_id
            
            result = f"📝 **Logs for {server_name}** (last {len(logs)} entries)\n\n"
            
            for log in logs:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(log['timestamp']))
                stream_emoji = "📤" if log['stream'] == 'stdout' else "🔴"
                result += f"{stream_emoji} [{timestamp}] {log['message']}\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting MCP server logs: {e}")
            return f"❌ Error getting server logs: {str(e)}"
    
    async def get_hosting_stats(self) -> str:
        """Get overall hosting statistics and performance insights"""
        try:
            await self.ensure_started()
            
            servers = await self.host.list_servers()
            
            # Calculate statistics
            total_servers = len(servers)
            running_servers = len([s for s in servers if s.get('status') == 'running'])
            failed_servers = len([s for s in servers if s.get('status') == 'failed'])
            
            total_memory = sum(s.get('resource_usage', {}).get('memory_mb', 0) for s in servers)
            avg_cpu = sum(s.get('resource_usage', {}).get('cpu_percent', 0) for s in servers) / max(total_servers, 1)
            
            total_restarts = sum(s.get('restart_count', 0) for s in servers)
            total_uptime = sum(s.get('uptime_seconds', 0) for s in servers)
            
            # Store performance analytics in hAIveMind
            if self.storage:
                await self.storage.store_memory(
                    content="MCP hosting performance analytics snapshot",
                    category="monitoring",
                    context="MCP server hosting - performance analytics",
                    metadata={
                        "timestamp": time.time(),
                        "total_servers": total_servers,
                        "running_servers": running_servers,
                        "failed_servers": failed_servers,
                        "total_memory_mb": total_memory,
                        "average_cpu_percent": avg_cpu,
                        "total_restarts": total_restarts,
                        "total_uptime_seconds": total_uptime,
                        "max_servers": self.host.max_servers
                    },
                    tags=["mcp-hosting", "performance", "analytics", "monitoring"]
                )
            
            result = f"📊 **MCP Hosting Statistics**\n\n" \
                    f"**Servers**: {running_servers}/{total_servers} running (max: {self.host.max_servers})\n" \
                    f"**Failed**: {failed_servers} servers\n" \
                    f"**Total Memory**: {total_memory:.1f} MB\n" \
                    f"**Average CPU**: {avg_cpu:.1f}%\n" \
                    f"**Total Restarts**: {total_restarts}\n" \
                    f"**Combined Uptime**: {total_uptime/3600:.1f} hours\n\n"
            
            if servers:
                result += "**Top Resource Users**:\n"
                # Sort by memory usage
                top_servers = sorted(servers, 
                                   key=lambda x: x.get('resource_usage', {}).get('memory_mb', 0), 
                                   reverse=True)[:3]
                
                for server in top_servers:
                    if server.get('resource_usage'):
                        res = server['resource_usage']
                        result += f"  • {server.get('name', 'Unknown')}: " \
                                 f"{res.get('memory_mb', 0):.1f}MB, " \
                                 f"{res.get('cpu_percent', 0):.1f}% CPU\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting hosting stats: {e}")
            return f"❌ Error getting hosting statistics: {str(e)}"
    
    async def optimize_server_resources(self) -> str:
        """Analyze and provide optimization recommendations for hosted servers"""
        try:
            await self.ensure_started()
            
            servers = await self.host.list_servers()
            
            if not servers:
                return "📊 No servers to optimize."
            
            recommendations = []
            
            for server in servers:
                server_name = server.get('name', 'Unknown')
                resource_usage = server.get('resource_usage', {})
                
                # Memory optimization
                memory_mb = resource_usage.get('memory_mb', 0)
                if memory_mb > 500:
                    recommendations.append(f"🔴 {server_name}: High memory usage ({memory_mb:.1f}MB) - consider memory limits")
                elif memory_mb < 50 and server.get('status') == 'running':
                    recommendations.append(f"🟡 {server_name}: Low memory usage ({memory_mb:.1f}MB) - could reduce limits")
                
                # CPU optimization
                cpu_percent = resource_usage.get('cpu_percent', 0)
                if cpu_percent > 80:
                    recommendations.append(f"🔴 {server_name}: High CPU usage ({cpu_percent:.1f}%) - investigate performance")
                
                # Restart optimization
                restart_count = server.get('restart_count', 0)
                uptime_hours = server.get('uptime_seconds', 0) / 3600
                if restart_count > 5 and uptime_hours < 24:
                    recommendations.append(f"🔴 {server_name}: Frequent restarts ({restart_count} in {uptime_hours:.1f}h) - check stability")
                
                # Health check optimization
                health_failures = server.get('health_check_failures', 0)
                if health_failures > 3:
                    recommendations.append(f"🟡 {server_name}: Health check issues ({health_failures} failures) - review configuration")
            
            # Store optimization insights in hAIveMind
            if self.storage:
                await self.storage.store_memory(
                    content="MCP server hosting optimization analysis",
                    category="monitoring",
                    context="MCP server hosting - optimization recommendations",
                    metadata={
                        "timestamp": time.time(),
                        "servers_analyzed": len(servers),
                        "recommendations_count": len(recommendations),
                        "recommendations": recommendations
                    },
                    tags=["mcp-hosting", "optimization", "performance", "recommendations"]
                )
            
            if not recommendations:
                return "✅ **Server Optimization Analysis**\n\nAll servers are running optimally! No recommendations at this time."
            
            result = f"📊 **Server Optimization Recommendations** ({len(recommendations)} items)\n\n"
            for i, rec in enumerate(recommendations, 1):
                result += f"{i}. {rec}\n"
            
            result += f"\n💡 **General Tips**:\n" \
                     f"• Monitor resource usage regularly\n" \
                     f"• Set appropriate resource limits\n" \
                     f"• Review frequently restarting servers\n" \
                     f"• Use health checks for early problem detection"
            
            return result
            
        except Exception as e:
            logger.error(f"Error optimizing server resources: {e}")
            return f"❌ Error analyzing server optimization: {str(e)}"