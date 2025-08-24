#!/usr/bin/env python3
"""
MCP Tools for Marketplace Operations
Provides comprehensive MCP tools for interacting with the MCP Server Marketplace
with hAIveMind awareness integration.

Author: Lance James, Unit 221B, Inc
Date: August 24, 2025
Version: 1.0.0
"""

import json
import uuid
import base64
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from mcp_marketplace import MCPMarketplace, ServerMetadata, ServerReview, ServerStatus, CompatibilityLevel

# Import hAIveMind components
try:
    from memory_server import store_memory
    HAIVEMIND_AVAILABLE = True
except ImportError:
    HAIVEMIND_AVAILABLE = False

class MarketplaceMCPTools:
    """MCP Tools for marketplace operations with hAIveMind integration"""
    
    def __init__(self, marketplace: MCPMarketplace):
        self.marketplace = marketplace
    
    async def search_marketplace_servers(self, 
                                       query: str = None,
                                       category: str = None,
                                       language: str = None,
                                       min_rating: float = None,
                                       verified_only: bool = False,
                                       featured_only: bool = False,
                                       limit: int = 20,
                                       sort_by: str = "rating") -> Dict[str, Any]:
        """
        Search for MCP servers in the marketplace
        
        Args:
            query: Search query for server names, descriptions, or keywords
            category: Filter by server category (e.g., 'ai-tools', 'data-processing')
            language: Filter by programming language (e.g., 'python', 'javascript')
            min_rating: Minimum rating filter (0.0 to 5.0)
            verified_only: Show only verified servers
            featured_only: Show only featured servers
            limit: Maximum number of results (1-100)
            sort_by: Sort order ('rating', 'downloads', 'newest', 'updated', 'name')
        
        Returns:
            Dictionary containing search results and metadata
        """
        try:
            result = await self.marketplace.search_servers(
                query=query,
                category=category,
                language=language,
                min_rating=min_rating,
                verified_only=verified_only,
                featured_only=featured_only,
                limit=min(limit, 100),
                sort_by=sort_by
            )
            
            # Store search in hAIveMind for analytics
            if HAIVEMIND_AVAILABLE:
                await store_memory(
                    content=f"Marketplace search: '{query}' in category '{category}' returned {len(result['servers'])} results",
                    category="marketplace",
                    metadata={
                        "action": "search_performed",
                        "query": query,
                        "category": category,
                        "language": language,
                        "results_count": len(result["servers"]),
                        "filters": {
                            "min_rating": min_rating,
                            "verified_only": verified_only,
                            "featured_only": featured_only
                        }
                    },
                    project="mcp-marketplace",
                    scope="project-shared"
                )
            
            return {
                "success": True,
                "servers": result["servers"],
                "total_results": result["total"],
                "has_more": result["has_more"],
                "search_metadata": {
                    "query": query,
                    "category": category,
                    "language": language,
                    "sort_by": sort_by,
                    "filters_applied": {
                        "min_rating": min_rating,
                        "verified_only": verified_only,
                        "featured_only": featured_only
                    }
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "servers": [],
                "total_results": 0
            }
    
    async def get_server_details(self, server_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific MCP server
        
        Args:
            server_id: Unique identifier of the server
        
        Returns:
            Dictionary containing complete server information
        """
        try:
            server = await self.marketplace.get_server_details(server_id)
            
            if not server:
                return {
                    "success": False,
                    "error": f"Server {server_id} not found",
                    "server": None
                }
            
            return {
                "success": True,
                "server": server,
                "compatibility_info": {
                    "claude_versions": server.get("claude_compatibility", {}),
                    "platforms": server.get("platform_compatibility", []),
                    "min_claude_version": server.get("min_claude_version"),
                    "max_claude_version": server.get("max_claude_version")
                },
                "security_info": {
                    "security_scan_passed": server.get("security_scan_passed", False),
                    "security_scan_date": server.get("security_scan_date"),
                    "verified": server.get("verified", False)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "server": None
            }
    
    async def install_marketplace_server(self, 
                                       server_id: str,
                                       device_id: str = "default",
                                       installation_method: str = "one_click",
                                       target_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Install an MCP server from the marketplace
        
        Args:
            server_id: Unique identifier of the server to install
            device_id: Target device identifier
            installation_method: Installation method ('one_click', 'manual', 'cli')
            target_config: Additional configuration for installation
        
        Returns:
            Dictionary containing installation result and details
        """
        try:
            # Get current user context (would be provided by MCP framework)
            user_id = "current_user"  # This would come from authentication context
            
            installation_id = await self.marketplace.install_server(
                server_id=server_id,
                user_id=user_id,
                device_id=device_id,
                installation_method=installation_method,
                target_config=target_config or {}
            )
            
            # Get server details for response
            server = await self.marketplace.get_server_details(server_id)
            
            return {
                "success": True,
                "installation_id": installation_id,
                "server_name": server["name"] if server else "Unknown",
                "server_version": server["version"] if server else "Unknown",
                "device_id": device_id,
                "installation_method": installation_method,
                "message": f"Server installed successfully with ID: {installation_id}",
                "next_steps": [
                    "Check installation status using get_installation_status",
                    "Configure server settings if needed",
                    "Test server functionality"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "installation_id": None,
                "message": f"Installation failed: {str(e)}"
            }
    
    async def get_installation_status(self, installation_id: str) -> Dict[str, Any]:
        """
        Get the status of a server installation
        
        Args:
            installation_id: Unique identifier of the installation
        
        Returns:
            Dictionary containing installation status and details
        """
        try:
            import sqlite3
            
            with sqlite3.connect(self.marketplace.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                installation = conn.execute(
                    "SELECT * FROM installations WHERE id = ?",
                    (installation_id,)
                ).fetchone()
                
                if not installation:
                    return {
                        "success": False,
                        "error": f"Installation {installation_id} not found",
                        "status": None
                    }
                
                result = dict(installation)
                result["installed_at"] = datetime.fromtimestamp(result["installed_at"]).isoformat()
                
                return {
                    "success": True,
                    "installation": result,
                    "status_description": {
                        "success": "Installation completed successfully",
                        "failed": "Installation failed - check error message",
                        "pending": "Installation in progress"
                    }.get(result["status"], "Unknown status")
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": None
            }
    
    async def add_server_review(self, 
                              server_id: str,
                              rating: int,
                              title: str,
                              content: str,
                              username: str = "Anonymous") -> Dict[str, Any]:
        """
        Add a review and rating for an MCP server
        
        Args:
            server_id: Unique identifier of the server
            rating: Rating from 1 to 5 stars
            title: Review title/summary
            content: Detailed review content
            username: Username of the reviewer
        
        Returns:
            Dictionary containing review submission result
        """
        try:
            # Validate inputs
            if not (1 <= rating <= 5):
                return {
                    "success": False,
                    "error": "Rating must be between 1 and 5",
                    "review_id": None
                }
            
            if len(content) < 10:
                return {
                    "success": False,
                    "error": "Review content must be at least 10 characters",
                    "review_id": None
                }
            
            # Check if server exists
            server = await self.marketplace.get_server_details(server_id)
            if not server:
                return {
                    "success": False,
                    "error": f"Server {server_id} not found",
                    "review_id": None
                }
            
            # Create review
            review = ServerReview(
                id=f"review_{uuid.uuid4().hex[:12]}",
                server_id=server_id,
                user_id="current_user",  # Would come from authentication context
                username=username,
                rating=rating,
                title=title,
                content=content
            )
            
            review_id = await self.marketplace.add_review(review)
            
            return {
                "success": True,
                "review_id": review_id,
                "server_name": server["name"],
                "rating": rating,
                "title": title,
                "message": f"Review added successfully for {server['name']}",
                "impact": {
                    "previous_rating": server.get("rating", 0),
                    "review_count": server.get("rating_count", 0) + 1
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "review_id": None
            }
    
    async def get_server_reviews(self, 
                               server_id: str,
                               limit: int = 20,
                               offset: int = 0) -> Dict[str, Any]:
        """
        Get reviews for a specific MCP server
        
        Args:
            server_id: Unique identifier of the server
            limit: Maximum number of reviews to return
            offset: Number of reviews to skip (for pagination)
        
        Returns:
            Dictionary containing server reviews
        """
        try:
            import sqlite3
            
            with sqlite3.connect(self.marketplace.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get total count
                total = conn.execute(
                    "SELECT COUNT(*) as count FROM reviews WHERE server_id = ?",
                    (server_id,)
                ).fetchone()["count"]
                
                # Get reviews
                reviews = conn.execute("""
                    SELECT * FROM reviews WHERE server_id = ?
                    ORDER BY created_at DESC LIMIT ? OFFSET ?
                """, (server_id, limit, offset)).fetchall()
                
                result_reviews = []
                for review in reviews:
                    review_data = dict(review)
                    review_data["created_at"] = datetime.fromtimestamp(review_data["created_at"]).isoformat()
                    review_data["updated_at"] = datetime.fromtimestamp(review_data["updated_at"]).isoformat()
                    result_reviews.append(review_data)
                
                # Get server name for context
                server = await self.marketplace.get_server_details(server_id)
                server_name = server["name"] if server else "Unknown Server"
                
                return {
                    "success": True,
                    "server_id": server_id,
                    "server_name": server_name,
                    "reviews": result_reviews,
                    "total_reviews": total,
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "has_more": offset + len(reviews) < total
                    },
                    "rating_summary": {
                        "average_rating": server.get("rating", 0) if server else 0,
                        "total_ratings": server.get("rating_count", 0) if server else 0
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "reviews": []
            }
    
    async def get_marketplace_recommendations(self, 
                                            based_on_server: str = None,
                                            category: str = None,
                                            limit: int = 5) -> Dict[str, Any]:
        """
        Get AI-powered server recommendations from the marketplace
        
        Args:
            based_on_server: Get recommendations similar to this server
            category: Focus recommendations on specific category
            limit: Maximum number of recommendations
        
        Returns:
            Dictionary containing personalized recommendations
        """
        try:
            recommendations = await self.marketplace.get_recommendations(
                user_id="current_user",  # Would come from authentication context
                device_id="current_device",
                based_on_server=based_on_server,
                limit=limit
            )
            
            # Add category filtering if specified
            if category:
                recommendations = [
                    rec for rec in recommendations 
                    if rec.get("category") == category
                ][:limit]
            
            return {
                "success": True,
                "recommendations": recommendations,
                "recommendation_context": {
                    "based_on_server": based_on_server,
                    "category_filter": category,
                    "total_recommendations": len(recommendations)
                },
                "recommendation_reasons": [
                    "High user ratings and reviews",
                    "Popular in your category of interest",
                    "Compatible with your setup",
                    "Recently updated and maintained",
                    "Similar to servers you've used"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "recommendations": []
            }
    
    async def get_marketplace_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive marketplace analytics and statistics
        
        Returns:
            Dictionary containing marketplace analytics
        """
        try:
            analytics = await self.marketplace.get_marketplace_analytics()
            
            return {
                "success": True,
                "analytics": analytics,
                "insights": {
                    "most_popular_category": max(analytics["categories"], key=lambda x: x["count"])["category"] if analytics["categories"] else "N/A",
                    "most_popular_language": max(analytics["languages"], key=lambda x: x["count"])["language"] if analytics["languages"] else "N/A",
                    "total_downloads": analytics["overview"].get("total_downloads", 0),
                    "average_rating": round(analytics["overview"].get("average_rating", 0), 2),
                    "growth_trend": "positive" if analytics["recent_activity"] else "stable"
                },
                "recommendations_for_developers": [
                    f"Consider developing in {max(analytics['languages'], key=lambda x: x['count'])['language']} - most popular language" if analytics["languages"] else "Focus on Python development",
                    f"Target the {max(analytics['categories'], key=lambda x: x['count'])['category']} category - highest demand" if analytics["categories"] else "Focus on general-purpose tools",
                    "Ensure high code quality for better ratings",
                    "Provide comprehensive documentation",
                    "Regular updates increase user adoption"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "analytics": None
            }
    
    async def register_new_server(self, 
                                server_data: Dict[str, Any],
                                package_base64: str = None) -> Dict[str, Any]:
        """
        Register a new MCP server in the marketplace
        
        Args:
            server_data: Complete server metadata including name, description, version, etc.
            package_base64: Base64-encoded server package (ZIP file)
        
        Returns:
            Dictionary containing registration result
        """
        try:
            # Validate required fields
            required_fields = ["name", "description", "version", "author", "author_email"]
            for field in required_fields:
                if field not in server_data:
                    return {
                        "success": False,
                        "error": f"Missing required field: {field}",
                        "server_id": None
                    }
            
            # Create server metadata
            server_id = f"server_{uuid.uuid4().hex[:12]}"
            metadata = ServerMetadata(
                id=server_id,
                name=server_data["name"],
                description=server_data["description"],
                version=server_data["version"],
                author=server_data["author"],
                author_email=server_data["author_email"],
                organization=server_data.get("organization"),
                homepage=server_data.get("homepage"),
                repository=server_data.get("repository"),
                license=server_data.get("license", "MIT"),
                keywords=server_data.get("keywords", []),
                category=server_data.get("category", "general"),
                subcategory=server_data.get("subcategory"),
                language=server_data.get("language", "python"),
                runtime_requirements=server_data.get("runtime_requirements", {}),
                dependencies=server_data.get("dependencies", []),
                tools=server_data.get("tools", []),
                resources=server_data.get("resources", []),
                prompts=server_data.get("prompts", []),
                platform_compatibility=server_data.get("platform_compatibility", ["linux", "macos", "windows"]),
                installation_script=server_data.get("installation_script")
            )
            
            # Handle package data
            package_data = None
            if package_base64:
                try:
                    package_data = base64.b64decode(package_base64)
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Invalid base64 package data: {str(e)}",
                        "server_id": None
                    }
            
            # Register server
            result_id = await self.marketplace.register_server(metadata, package_data)
            
            return {
                "success": True,
                "server_id": result_id,
                "server_name": metadata.name,
                "version": metadata.version,
                "status": "registered",
                "message": f"Server '{metadata.name}' registered successfully. Pending approval.",
                "next_steps": [
                    "Server will undergo security review",
                    "You'll be notified when approved",
                    "Monitor your server's status in the dashboard",
                    "Consider adding documentation and examples"
                ],
                "approval_process": {
                    "security_scan": "Automated security scan will be performed",
                    "manual_review": "Manual review by marketplace moderators",
                    "estimated_time": "1-3 business days"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "server_id": None
            }
    
    async def get_my_servers(self, user_email: str) -> Dict[str, Any]:
        """
        Get servers registered by the current user
        
        Args:
            user_email: Email address of the user
        
        Returns:
            Dictionary containing user's registered servers
        """
        try:
            import sqlite3
            
            with sqlite3.connect(self.marketplace.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                servers = conn.execute("""
                    SELECT * FROM servers WHERE author_email = ?
                    ORDER BY created_at DESC
                """, (user_email,)).fetchall()
                
                result_servers = []
                for server in servers:
                    server_data = dict(server)
                    server_data["created_at"] = datetime.fromtimestamp(server_data["created_at"]).isoformat()
                    server_data["updated_at"] = datetime.fromtimestamp(server_data["updated_at"]).isoformat()
                    
                    # Parse JSON fields
                    for field in ["keywords", "tools", "resources", "prompts"]:
                        if server_data[field]:
                            server_data[field] = json.loads(server_data[field])
                    
                    result_servers.append(server_data)
                
                return {
                    "success": True,
                    "servers": result_servers,
                    "total_servers": len(result_servers),
                    "summary": {
                        "approved": len([s for s in result_servers if s["status"] == "approved"]),
                        "pending": len([s for s in result_servers if s["status"] == "pending"]),
                        "rejected": len([s for s in result_servers if s["status"] == "rejected"]),
                        "total_downloads": sum(s["downloads"] for s in result_servers),
                        "average_rating": sum(s["rating"] for s in result_servers) / len(result_servers) if result_servers else 0
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "servers": []
            }

# Tool registration functions for MCP framework
def get_marketplace_tools(marketplace: MCPMarketplace) -> Dict[str, Any]:
    """Get all marketplace MCP tools"""
    tools = MarketplaceMCPTools(marketplace)
    
    return {
        "search_marketplace_servers": tools.search_marketplace_servers,
        "get_server_details": tools.get_server_details,
        "install_marketplace_server": tools.install_marketplace_server,
        "get_installation_status": tools.get_installation_status,
        "add_server_review": tools.add_server_review,
        "get_server_reviews": tools.get_server_reviews,
        "get_marketplace_recommendations": tools.get_marketplace_recommendations,
        "get_marketplace_analytics": tools.get_marketplace_analytics,
        "register_new_server": tools.register_new_server,
        "get_my_servers": tools.get_my_servers
    }

if __name__ == "__main__":
    # Example usage
    from mcp_marketplace import create_marketplace
    
    config = {
        "database_path": "data/marketplace.db",
        "storage_path": "data/marketplace_storage",
        "redis": {"host": "localhost", "port": 6379, "db": 2},
        "haivemind_integration": True
    }
    
    marketplace = create_marketplace(config)
    tools = get_marketplace_tools(marketplace)
    
    print("MCP Marketplace Tools initialized successfully")
    print(f"Available tools: {list(tools.keys())}")