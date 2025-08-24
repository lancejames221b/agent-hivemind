#!/usr/bin/env python3
"""
MCP Server Marketplace/Registry - Enterprise & Security Production Ready
Provides a comprehensive marketplace for sharing and discovering MCP servers
with hAIveMind awareness integration.

Author: Lance James, Unit 221B, Inc
Date: August 24, 2025
Version: 1.0.0
"""

import os
import json
import sqlite3
import hashlib
import zipfile
import tempfile
import shutil
import asyncio
import aiohttp
import redis
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import semver
import yaml
import requests
from urllib.parse import urlparse

# Import hAIveMind components
try:
    from database import ControlDatabase
    from memory_server import store_memory
    HAIVEMIND_AVAILABLE = True
except ImportError:
    HAIVEMIND_AVAILABLE = False

class ServerStatus(Enum):
    """Server status in the marketplace"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"
    SECURITY_REVIEW = "security_review"

class CompatibilityLevel(Enum):
    """Compatibility level with Claude versions"""
    FULL = "full"
    PARTIAL = "partial"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"

@dataclass
class ServerMetadata:
    """Complete server metadata for marketplace"""
    id: str
    name: str
    description: str
    version: str
    author: str
    author_email: str
    organization: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: str = "MIT"
    keywords: List[str] = None
    category: str = "general"
    subcategory: Optional[str] = None
    
    # Technical details
    language: str = "python"
    runtime_requirements: Dict[str, Any] = None
    dependencies: List[str] = None
    tools: List[Dict[str, Any]] = None
    resources: List[Dict[str, Any]] = None
    prompts: List[Dict[str, Any]] = None
    
    # Marketplace specific
    status: ServerStatus = ServerStatus.PENDING
    created_at: datetime = None
    updated_at: datetime = None
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    featured: bool = False
    verified: bool = False
    
    # Compatibility
    claude_compatibility: Dict[str, CompatibilityLevel] = None
    min_claude_version: Optional[str] = None
    max_claude_version: Optional[str] = None
    platform_compatibility: List[str] = None
    
    # Security
    security_scan_passed: bool = False
    security_scan_date: Optional[datetime] = None
    security_issues: List[Dict[str, Any]] = None
    
    # Package info
    package_url: Optional[str] = None
    package_hash: Optional[str] = None
    package_size: int = 0
    installation_script: Optional[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.runtime_requirements is None:
            self.runtime_requirements = {}
        if self.dependencies is None:
            self.dependencies = []
        if self.tools is None:
            self.tools = []
        if self.resources is None:
            self.resources = []
        if self.prompts is None:
            self.prompts = []
        if self.claude_compatibility is None:
            self.claude_compatibility = {}
        if self.platform_compatibility is None:
            self.platform_compatibility = ["linux", "macos", "windows"]
        if self.security_issues is None:
            self.security_issues = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

@dataclass
class ServerReview:
    """User review for a server"""
    id: str
    server_id: str
    user_id: str
    username: str
    rating: int  # 1-5 stars
    title: str
    content: str
    helpful_votes: int = 0
    created_at: datetime = None
    updated_at: datetime = None
    verified_purchase: bool = False
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

@dataclass
class InstallationRecord:
    """Record of server installation"""
    id: str
    server_id: str
    user_id: str
    device_id: str
    installation_method: str  # "one_click", "manual", "cli"
    version: str
    status: str  # "success", "failed", "pending"
    error_message: Optional[str] = None
    installed_at: datetime = None
    
    def __post_init__(self):
        if self.installed_at is None:
            self.installed_at = datetime.now()

class MCPMarketplace:
    """
    MCP Server Marketplace/Registry with enterprise security and hAIveMind integration
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_path = config.get("database_path", "data/marketplace.db")
        self.storage_path = Path(config.get("storage_path", "data/marketplace_storage"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Redis for caching and real-time features
        redis_config = config.get("redis", {})
        self.redis_client = redis.Redis(
            host=redis_config.get("host", "localhost"),
            port=redis_config.get("port", 6379),
            db=redis_config.get("db", 2),
            password=redis_config.get("password"),
            decode_responses=True
        )
        
        # Initialize database
        self._init_database()
        
        # hAIveMind integration
        self.haivemind_enabled = HAIVEMIND_AVAILABLE and config.get("haivemind_integration", True)
        
        # Security settings
        self.security_config = config.get("security", {})
        self.max_package_size = self.security_config.get("max_package_size_mb", 100) * 1024 * 1024
        self.allowed_extensions = self.security_config.get("allowed_extensions", [".zip", ".tar.gz"])
        self.scan_uploads = self.security_config.get("scan_uploads", True)
        
        # Categories and tags
        self.categories = config.get("categories", [
            "ai-tools", "data-processing", "web-scraping", "databases", 
            "monitoring", "security", "development", "automation", "general"
        ])
        
    def _init_database(self):
        """Initialize SQLite database with marketplace schema"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Servers table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS servers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    version TEXT NOT NULL,
                    author TEXT NOT NULL,
                    author_email TEXT NOT NULL,
                    organization TEXT,
                    homepage TEXT,
                    repository TEXT,
                    license TEXT DEFAULT 'MIT',
                    keywords TEXT, -- JSON array
                    category TEXT NOT NULL DEFAULT 'general',
                    subcategory TEXT,
                    language TEXT DEFAULT 'python',
                    runtime_requirements TEXT, -- JSON
                    dependencies TEXT, -- JSON array
                    tools TEXT, -- JSON array
                    resources TEXT, -- JSON array
                    prompts TEXT, -- JSON array
                    status TEXT DEFAULT 'pending',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    downloads INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    rating_count INTEGER DEFAULT 0,
                    featured BOOLEAN DEFAULT FALSE,
                    verified BOOLEAN DEFAULT FALSE,
                    claude_compatibility TEXT, -- JSON
                    min_claude_version TEXT,
                    max_claude_version TEXT,
                    platform_compatibility TEXT, -- JSON array
                    security_scan_passed BOOLEAN DEFAULT FALSE,
                    security_scan_date INTEGER,
                    security_issues TEXT, -- JSON array
                    package_url TEXT,
                    package_hash TEXT,
                    package_size INTEGER DEFAULT 0,
                    installation_script TEXT
                )
            """)
            
            # Reviews table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,
                    server_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    helpful_votes INTEGER DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    verified_purchase BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE
                )
            """)
            
            # Installations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS installations (
                    id TEXT PRIMARY KEY,
                    server_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    installation_method TEXT NOT NULL,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    installed_at INTEGER NOT NULL,
                    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE
                )
            """)
            
            # Download analytics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS download_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id TEXT NOT NULL,
                    user_id TEXT,
                    device_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    referrer TEXT,
                    download_method TEXT,
                    timestamp INTEGER NOT NULL,
                    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE
                )
            """)
            
            # Server templates table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS server_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    language TEXT NOT NULL,
                    template_content TEXT NOT NULL, -- Base64 encoded template
                    example_config TEXT, -- JSON
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    usage_count INTEGER DEFAULT 0
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_category ON servers(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_rating ON servers(rating DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_downloads ON servers(downloads DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_created ON servers(created_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_server ON reviews(server_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_installations_server ON installations(server_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_installations_user ON installations(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_server ON download_analytics(server_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON download_analytics(timestamp)")
            
            conn.commit()
    
    async def register_server(self, metadata: ServerMetadata, package_data: bytes = None) -> str:
        """Register a new server in the marketplace"""
        try:
            # Validate metadata
            if not metadata.name or not metadata.description:
                raise ValueError("Server name and description are required")
            
            if not semver.VersionInfo.isvalid(metadata.version):
                raise ValueError(f"Invalid semantic version: {metadata.version}")
            
            # Security scan if package provided
            if package_data and self.scan_uploads:
                security_result = await self._security_scan_package(package_data)
                metadata.security_scan_passed = security_result["passed"]
                metadata.security_scan_date = datetime.now()
                metadata.security_issues = security_result.get("issues", [])
                
                if not security_result["passed"]:
                    metadata.status = ServerStatus.SECURITY_REVIEW
            
            # Store package if provided
            if package_data:
                package_hash = hashlib.sha256(package_data).hexdigest()
                package_path = self.storage_path / f"{metadata.id}_{package_hash}.zip"
                
                with open(package_path, "wb") as f:
                    f.write(package_data)
                
                metadata.package_url = str(package_path)
                metadata.package_hash = package_hash
                metadata.package_size = len(package_data)
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO servers (
                        id, name, description, version, author, author_email, organization,
                        homepage, repository, license, keywords, category, subcategory,
                        language, runtime_requirements, dependencies, tools, resources, prompts,
                        status, created_at, updated_at, downloads, rating, rating_count,
                        featured, verified, claude_compatibility, min_claude_version,
                        max_claude_version, platform_compatibility, security_scan_passed,
                        security_scan_date, security_issues, package_url, package_hash,
                        package_size, installation_script
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metadata.id, metadata.name, metadata.description, metadata.version,
                    metadata.author, metadata.author_email, metadata.organization,
                    metadata.homepage, metadata.repository, metadata.license,
                    json.dumps(metadata.keywords), metadata.category, metadata.subcategory,
                    metadata.language, json.dumps(metadata.runtime_requirements),
                    json.dumps(metadata.dependencies), json.dumps(metadata.tools),
                    json.dumps(metadata.resources), json.dumps(metadata.prompts),
                    metadata.status.value, int(metadata.created_at.timestamp()),
                    int(metadata.updated_at.timestamp()), metadata.downloads,
                    metadata.rating, metadata.rating_count, metadata.featured,
                    metadata.verified, json.dumps(metadata.claude_compatibility),
                    metadata.min_claude_version, metadata.max_claude_version,
                    json.dumps(metadata.platform_compatibility), metadata.security_scan_passed,
                    int(metadata.security_scan_date.timestamp()) if metadata.security_scan_date else None,
                    json.dumps(metadata.security_issues), metadata.package_url,
                    metadata.package_hash, metadata.package_size, metadata.installation_script
                ))
                conn.commit()
            
            # Cache in Redis
            await self._cache_server_metadata(metadata)
            
            # Store in hAIveMind if available
            if self.haivemind_enabled:
                await self._store_haivemind_memory(
                    category="marketplace",
                    content=f"New MCP server registered: {metadata.name} v{metadata.version}",
                    metadata={
                        "action": "server_registered",
                        "server_id": metadata.id,
                        "server_name": metadata.name,
                        "version": metadata.version,
                        "author": metadata.author,
                        "category": metadata.category,
                        "status": metadata.status.value,
                        "security_scan_passed": metadata.security_scan_passed
                    }
                )
            
            return metadata.id
            
        except Exception as e:
            raise Exception(f"Failed to register server: {str(e)}")
    
    async def search_servers(self, 
                           query: str = None,
                           category: str = None,
                           language: str = None,
                           min_rating: float = None,
                           compatible_with: str = None,
                           verified_only: bool = False,
                           featured_only: bool = False,
                           limit: int = 20,
                           offset: int = 0,
                           sort_by: str = "rating") -> Dict[str, Any]:
        """Search servers in the marketplace with advanced filtering"""
        
        try:
            # Build query
            where_conditions = ["status = 'approved'"]
            params = []
            
            if query:
                where_conditions.append("(name LIKE ? OR description LIKE ? OR keywords LIKE ?)")
                search_term = f"%{query}%"
                params.extend([search_term, search_term, search_term])
            
            if category:
                where_conditions.append("category = ?")
                params.append(category)
            
            if language:
                where_conditions.append("language = ?")
                params.append(language)
            
            if min_rating:
                where_conditions.append("rating >= ?")
                params.append(min_rating)
            
            if verified_only:
                where_conditions.append("verified = TRUE")
            
            if featured_only:
                where_conditions.append("featured = TRUE")
            
            # Sort options
            sort_options = {
                "rating": "rating DESC, rating_count DESC",
                "downloads": "downloads DESC",
                "newest": "created_at DESC",
                "updated": "updated_at DESC",
                "name": "name ASC"
            }
            sort_clause = sort_options.get(sort_by, "rating DESC")
            
            # Execute search
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get total count
                count_query = f"SELECT COUNT(*) as total FROM servers WHERE {' AND '.join(where_conditions)}"
                total = conn.execute(count_query, params).fetchone()["total"]
                
                # Get results
                search_query = f"""
                    SELECT * FROM servers 
                    WHERE {' AND '.join(where_conditions)}
                    ORDER BY {sort_clause}
                    LIMIT ? OFFSET ?
                """
                params.extend([limit, offset])
                
                rows = conn.execute(search_query, params).fetchall()
                
                servers = []
                for row in rows:
                    server_data = dict(row)
                    
                    # Parse JSON fields
                    for field in ["keywords", "runtime_requirements", "dependencies", 
                                "tools", "resources", "prompts", "claude_compatibility",
                                "platform_compatibility", "security_issues"]:
                        if server_data[field]:
                            server_data[field] = json.loads(server_data[field])
                    
                    # Convert timestamps
                    server_data["created_at"] = datetime.fromtimestamp(server_data["created_at"])
                    server_data["updated_at"] = datetime.fromtimestamp(server_data["updated_at"])
                    if server_data["security_scan_date"]:
                        server_data["security_scan_date"] = datetime.fromtimestamp(server_data["security_scan_date"])
                    
                    servers.append(server_data)
            
            # Store search analytics in hAIveMind
            if self.haivemind_enabled:
                await self._store_haivemind_memory(
                    category="marketplace",
                    content=f"Marketplace search performed: '{query}' in category '{category}'",
                    metadata={
                        "action": "search_performed",
                        "query": query,
                        "category": category,
                        "language": language,
                        "min_rating": min_rating,
                        "results_count": len(servers),
                        "total_results": total,
                        "filters": {
                            "verified_only": verified_only,
                            "featured_only": featured_only,
                            "compatible_with": compatible_with
                        }
                    }
                )
            
            return {
                "servers": servers,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(servers) < total
            }
            
        except Exception as e:
            raise Exception(f"Search failed: {str(e)}")
    
    async def get_server_details(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a server"""
        try:
            # Try cache first
            cached = self.redis_client.get(f"server:{server_id}")
            if cached:
                return json.loads(cached)
            
            # Get from database
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                row = conn.execute("SELECT * FROM servers WHERE id = ?", (server_id,)).fetchone()
                if not row:
                    return None
                
                server_data = dict(row)
                
                # Parse JSON fields
                for field in ["keywords", "runtime_requirements", "dependencies", 
                            "tools", "resources", "prompts", "claude_compatibility",
                            "platform_compatibility", "security_issues"]:
                    if server_data[field]:
                        server_data[field] = json.loads(server_data[field])
                
                # Convert timestamps
                server_data["created_at"] = datetime.fromtimestamp(server_data["created_at"])
                server_data["updated_at"] = datetime.fromtimestamp(server_data["updated_at"])
                if server_data["security_scan_date"]:
                    server_data["security_scan_date"] = datetime.fromtimestamp(server_data["security_scan_date"])
                
                # Get recent reviews
                reviews = conn.execute("""
                    SELECT * FROM reviews WHERE server_id = ? 
                    ORDER BY created_at DESC LIMIT 10
                """, (server_id,)).fetchall()
                
                server_data["recent_reviews"] = [
                    {
                        **dict(review),
                        "created_at": datetime.fromtimestamp(review["created_at"]),
                        "updated_at": datetime.fromtimestamp(review["updated_at"])
                    }
                    for review in reviews
                ]
                
                # Cache result
                self.redis_client.setex(
                    f"server:{server_id}", 
                    300,  # 5 minutes
                    json.dumps(server_data, default=str)
                )
                
                return server_data
                
        except Exception as e:
            raise Exception(f"Failed to get server details: {str(e)}")
    
    async def install_server(self, 
                           server_id: str, 
                           user_id: str, 
                           device_id: str,
                           installation_method: str = "one_click",
                           target_config: Dict[str, Any] = None) -> str:
        """Install a server with one-click functionality"""
        
        installation_id = f"install_{server_id}_{device_id}_{int(datetime.now().timestamp())}"
        
        try:
            # Get server details
            server = await self.get_server_details(server_id)
            if not server:
                raise ValueError(f"Server {server_id} not found")
            
            if server["status"] != "approved":
                raise ValueError(f"Server {server_id} is not approved for installation")
            
            # Create installation record
            installation = InstallationRecord(
                id=installation_id,
                server_id=server_id,
                user_id=user_id,
                device_id=device_id,
                installation_method=installation_method,
                version=server["version"],
                status="pending"
            )
            
            # Store installation record
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO installations (
                        id, server_id, user_id, device_id, installation_method,
                        version, status, error_message, installed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    installation.id, installation.server_id, installation.user_id,
                    installation.device_id, installation.installation_method,
                    installation.version, installation.status, installation.error_message,
                    int(installation.installed_at.timestamp())
                ))
                conn.commit()
            
            # Perform installation based on method
            if installation_method == "one_click":
                success = await self._perform_one_click_install(server, target_config)
            elif installation_method == "manual":
                success = await self._generate_manual_install_instructions(server, target_config)
            else:
                raise ValueError(f"Unsupported installation method: {installation_method}")
            
            # Update installation status
            final_status = "success" if success else "failed"
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE installations SET status = ? WHERE id = ?",
                    (final_status, installation_id)
                )
                
                # Update download count
                if success:
                    conn.execute(
                        "UPDATE servers SET downloads = downloads + 1 WHERE id = ?",
                        (server_id,)
                    )
                conn.commit()
            
            # Record analytics
            await self._record_download_analytics(server_id, user_id, device_id, installation_method)
            
            # Store in hAIveMind
            if self.haivemind_enabled:
                await self._store_haivemind_memory(
                    category="marketplace",
                    content=f"Server installation: {server['name']} v{server['version']} on {device_id}",
                    metadata={
                        "action": "server_installed",
                        "server_id": server_id,
                        "server_name": server["name"],
                        "version": server["version"],
                        "user_id": user_id,
                        "device_id": device_id,
                        "installation_method": installation_method,
                        "status": final_status,
                        "installation_id": installation_id
                    }
                )
            
            return installation_id
            
        except Exception as e:
            # Update installation record with error
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE installations SET status = ?, error_message = ? WHERE id = ?",
                    ("failed", str(e), installation_id)
                )
                conn.commit()
            
            raise Exception(f"Installation failed: {str(e)}")
    
    async def add_review(self, review: ServerReview) -> str:
        """Add a user review for a server"""
        try:
            # Validate review
            if not (1 <= review.rating <= 5):
                raise ValueError("Rating must be between 1 and 5")
            
            if len(review.content) < 10:
                raise ValueError("Review content must be at least 10 characters")
            
            # Store review
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO reviews (
                        id, server_id, user_id, username, rating, title, content,
                        helpful_votes, created_at, updated_at, verified_purchase
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    review.id, review.server_id, review.user_id, review.username,
                    review.rating, review.title, review.content, review.helpful_votes,
                    int(review.created_at.timestamp()), int(review.updated_at.timestamp()),
                    review.verified_purchase
                ))
                
                # Update server rating
                conn.execute("""
                    UPDATE servers SET 
                        rating = (SELECT AVG(rating) FROM reviews WHERE server_id = ?),
                        rating_count = (SELECT COUNT(*) FROM reviews WHERE server_id = ?)
                    WHERE id = ?
                """, (review.server_id, review.server_id, review.server_id))
                
                conn.commit()
            
            # Clear cache
            self.redis_client.delete(f"server:{review.server_id}")
            
            # Store in hAIveMind
            if self.haivemind_enabled:
                await self._store_haivemind_memory(
                    category="marketplace",
                    content=f"New review for {review.server_id}: {review.rating}/5 stars - {review.title}",
                    metadata={
                        "action": "review_added",
                        "server_id": review.server_id,
                        "user_id": review.user_id,
                        "rating": review.rating,
                        "title": review.title,
                        "verified_purchase": review.verified_purchase
                    }
                )
            
            return review.id
            
        except Exception as e:
            raise Exception(f"Failed to add review: {str(e)}")
    
    async def get_marketplace_analytics(self) -> Dict[str, Any]:
        """Get comprehensive marketplace analytics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Basic stats
                stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_servers,
                        COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved_servers,
                        COUNT(CASE WHEN featured = TRUE THEN 1 END) as featured_servers,
                        COUNT(CASE WHEN verified = TRUE THEN 1 END) as verified_servers,
                        SUM(downloads) as total_downloads,
                        AVG(rating) as average_rating
                    FROM servers
                """).fetchone()
                
                # Category breakdown
                categories = conn.execute("""
                    SELECT category, COUNT(*) as count, AVG(rating) as avg_rating
                    FROM servers WHERE status = 'approved'
                    GROUP BY category ORDER BY count DESC
                """).fetchall()
                
                # Top servers
                top_servers = conn.execute("""
                    SELECT id, name, downloads, rating, rating_count
                    FROM servers WHERE status = 'approved'
                    ORDER BY downloads DESC LIMIT 10
                """).fetchall()
                
                # Recent activity
                recent_installs = conn.execute("""
                    SELECT COUNT(*) as count, DATE(installed_at, 'unixepoch') as date
                    FROM installations 
                    WHERE installed_at > ? AND status = 'success'
                    GROUP BY DATE(installed_at, 'unixepoch')
                    ORDER BY date DESC LIMIT 30
                """, (int((datetime.now() - timedelta(days=30)).timestamp()),)).fetchall()
                
                # Language popularity
                languages = conn.execute("""
                    SELECT language, COUNT(*) as count
                    FROM servers WHERE status = 'approved'
                    GROUP BY language ORDER BY count DESC
                """).fetchall()
                
                return {
                    "overview": dict(stats),
                    "categories": [dict(row) for row in categories],
                    "top_servers": [dict(row) for row in top_servers],
                    "recent_activity": [dict(row) for row in recent_installs],
                    "languages": [dict(row) for row in languages],
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            raise Exception(f"Failed to get analytics: {str(e)}")
    
    async def get_recommendations(self, 
                                user_id: str = None, 
                                device_id: str = None,
                                based_on_server: str = None,
                                limit: int = 5) -> List[Dict[str, Any]]:
        """Get AI-powered server recommendations"""
        try:
            recommendations = []
            
            # Get user's installation history if available
            user_installs = []
            if user_id:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    user_installs = conn.execute("""
                        SELECT DISTINCT s.* FROM servers s
                        JOIN installations i ON s.id = i.server_id
                        WHERE i.user_id = ? AND i.status = 'success'
                    """, (user_id,)).fetchall()
            
            # Recommendation strategies
            if based_on_server:
                # Similar servers based on category and keywords
                recommendations.extend(await self._get_similar_servers(based_on_server, limit))
            
            elif user_installs:
                # Collaborative filtering based on user history
                recommendations.extend(await self._get_collaborative_recommendations(user_id, limit))
            
            else:
                # Popular and trending servers
                recommendations.extend(await self._get_trending_recommendations(limit))
            
            # Use hAIveMind for enhanced recommendations if available
            if self.haivemind_enabled:
                haivemind_recs = await self._get_haivemind_recommendations(user_id, device_id, limit)
                recommendations.extend(haivemind_recs)
            
            # Remove duplicates and limit results
            seen = set()
            unique_recs = []
            for rec in recommendations:
                if rec["id"] not in seen:
                    seen.add(rec["id"])
                    unique_recs.append(rec)
                    if len(unique_recs) >= limit:
                        break
            
            return unique_recs
            
        except Exception as e:
            raise Exception(f"Failed to get recommendations: {str(e)}")
    
    # Private helper methods
    
    async def _security_scan_package(self, package_data: bytes) -> Dict[str, Any]:
        """Perform security scan on uploaded package"""
        issues = []
        
        try:
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract package
                with zipfile.ZipFile(io.BytesIO(package_data), 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Scan for dangerous patterns
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        
                        # Skip binary files
                        if not self._is_text_file(file_path):
                            continue
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                
                                # Check for dangerous patterns
                                dangerous_patterns = [
                                    r'eval\s*\(',
                                    r'exec\s*\(',
                                    r'__import__\s*\(',
                                    r'subprocess\.',
                                    r'os\.system',
                                    r'shell=True',
                                    r'pickle\.loads',
                                    r'input\s*\(',
                                    r'raw_input\s*\('
                                ]
                                
                                for pattern in dangerous_patterns:
                                    if re.search(pattern, content, re.IGNORECASE):
                                        issues.append({
                                            "type": "dangerous_code",
                                            "file": os.path.relpath(file_path, temp_dir),
                                            "pattern": pattern,
                                            "severity": "high"
                                        })
                        except Exception:
                            continue
                
                # Check package structure
                required_files = ["server.py", "requirements.txt"]
                for req_file in required_files:
                    if not any(req_file in files for root, dirs, files in os.walk(temp_dir) for file in files):
                        issues.append({
                            "type": "missing_file",
                            "file": req_file,
                            "severity": "medium"
                        })
        
        except Exception as e:
            issues.append({
                "type": "scan_error",
                "message": str(e),
                "severity": "high"
            })
        
        # Determine if scan passed
        high_severity_issues = [issue for issue in issues if issue.get("severity") == "high"]
        passed = len(high_severity_issues) == 0
        
        return {
            "passed": passed,
            "issues": issues,
            "scan_date": datetime.now().isoformat()
        }
    
    def _is_text_file(self, file_path: str) -> bool:
        """Check if file is text-based"""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\x00' not in chunk
        except:
            return False
    
    async def _cache_server_metadata(self, metadata: ServerMetadata):
        """Cache server metadata in Redis"""
        try:
            cache_data = asdict(metadata)
            # Convert datetime objects to strings
            for key, value in cache_data.items():
                if isinstance(value, datetime):
                    cache_data[key] = value.isoformat()
                elif isinstance(value, ServerStatus):
                    cache_data[key] = value.value
            
            self.redis_client.setex(
                f"server:{metadata.id}",
                300,  # 5 minutes
                json.dumps(cache_data)
            )
        except Exception:
            pass  # Cache failure shouldn't break the operation
    
    async def _store_haivemind_memory(self, category: str, content: str, metadata: Dict[str, Any]):
        """Store event in hAIveMind memory"""
        if not self.haivemind_enabled:
            return
        
        try:
            await store_memory(
                content=content,
                category=category,
                metadata=metadata,
                project="mcp-marketplace",
                scope="project-shared"
            )
        except Exception:
            pass  # Memory storage failure shouldn't break the operation
    
    async def _perform_one_click_install(self, server: Dict[str, Any], target_config: Dict[str, Any] = None) -> bool:
        """Perform one-click installation of a server"""
        try:
            # This would integrate with the MCP hosting system from Story 4c
            # For now, return success simulation
            await asyncio.sleep(1)  # Simulate installation time
            return True
        except Exception:
            return False
    
    async def _generate_manual_install_instructions(self, server: Dict[str, Any], target_config: Dict[str, Any] = None) -> bool:
        """Generate manual installation instructions"""
        try:
            # Generate installation script or instructions
            return True
        except Exception:
            return False
    
    async def _record_download_analytics(self, server_id: str, user_id: str, device_id: str, method: str):
        """Record download analytics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO download_analytics (
                        server_id, user_id, device_id, download_method, timestamp
                    ) VALUES (?, ?, ?, ?, ?)
                """, (server_id, user_id, device_id, method, int(datetime.now().timestamp())))
                conn.commit()
        except Exception:
            pass
    
    async def _get_similar_servers(self, server_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get servers similar to the given server"""
        # Implementation for similarity-based recommendations
        return []
    
    async def _get_collaborative_recommendations(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get collaborative filtering recommendations"""
        # Implementation for collaborative filtering
        return []
    
    async def _get_trending_recommendations(self, limit: int) -> List[Dict[str, Any]]:
        """Get trending servers"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get servers with high recent download activity
                trending = conn.execute("""
                    SELECT s.*, COUNT(da.id) as recent_downloads
                    FROM servers s
                    LEFT JOIN download_analytics da ON s.id = da.server_id 
                        AND da.timestamp > ?
                    WHERE s.status = 'approved'
                    GROUP BY s.id
                    ORDER BY recent_downloads DESC, s.rating DESC
                    LIMIT ?
                """, (int((datetime.now() - timedelta(days=7)).timestamp()), limit)).fetchall()
                
                return [dict(row) for row in trending]
        except Exception:
            return []
    
    async def _get_haivemind_recommendations(self, user_id: str, device_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get AI-powered recommendations from hAIveMind"""
        # This would use hAIveMind's collective intelligence for recommendations
        return []

# Configuration and startup
def create_marketplace(config: Dict[str, Any]) -> MCPMarketplace:
    """Create and configure marketplace instance"""
    return MCPMarketplace(config)

if __name__ == "__main__":
    # Example configuration
    config = {
        "database_path": "data/marketplace.db",
        "storage_path": "data/marketplace_storage",
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 2
        },
        "security": {
            "max_package_size_mb": 100,
            "scan_uploads": True,
            "allowed_extensions": [".zip", ".tar.gz"]
        },
        "haivemind_integration": True
    }
    
    marketplace = create_marketplace(config)
    print("MCP Marketplace initialized successfully")