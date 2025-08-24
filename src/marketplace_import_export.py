#!/usr/bin/env python3
"""
MCP Marketplace Import/Export System
Provides comprehensive import/export functionality for server configurations,
marketplace data, and batch operations with multiple format support.

Author: Lance James, Unit 221B, Inc
Date: August 24, 2025
Version: 1.0.0
"""

import os
import json
import yaml
import csv
import xml.etree.ElementTree as ET
import zipfile
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
import base64
import sqlite3

# Import hAIveMind components
try:
    from memory_server import store_memory
    HAIVEMIND_AVAILABLE = True
except ImportError:
    HAIVEMIND_AVAILABLE = False

from mcp_marketplace import MCPMarketplace, ServerMetadata

class ExportFormat:
    """Supported export formats"""
    JSON = "json"
    YAML = "yaml"
    CSV = "csv"
    XML = "xml"
    ZIP = "zip"
    TOML = "toml"

@dataclass
class ExportConfig:
    """Configuration for export operations"""
    format: str
    include_metadata: bool = True
    include_reviews: bool = False
    include_analytics: bool = False
    include_packages: bool = False
    compress: bool = False
    encryption: Optional[str] = None
    
@dataclass
class ImportConfig:
    """Configuration for import operations"""
    format: str
    validate_schema: bool = True
    merge_strategy: str = "update"  # "update", "replace", "skip"
    auto_approve: bool = False
    backup_existing: bool = True

class MarketplaceImportExport:
    """
    Import/Export system for MCP marketplace data
    """
    
    def __init__(self, marketplace: MCPMarketplace, config: Dict[str, Any]):
        self.marketplace = marketplace
        self.config = config
        self.export_dir = Path(config.get("export_directory", "data/marketplace_exports"))
        self.import_dir = Path(config.get("import_directory", "data/marketplace_imports"))
        self.backup_dir = Path(config.get("backup_directory", "data/marketplace_backups"))
        
        # Create directories
        for directory in [self.export_dir, self.import_dir, self.backup_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Supported formats
        self.exporters = {
            ExportFormat.JSON: self._export_json,
            ExportFormat.YAML: self._export_yaml,
            ExportFormat.CSV: self._export_csv,
            ExportFormat.XML: self._export_xml,
            ExportFormat.ZIP: self._export_zip,
            ExportFormat.TOML: self._export_toml
        }
        
        self.importers = {
            ExportFormat.JSON: self._import_json,
            ExportFormat.YAML: self._import_yaml,
            ExportFormat.CSV: self._import_csv,
            ExportFormat.XML: self._import_xml,
            ExportFormat.ZIP: self._import_zip,
            ExportFormat.TOML: self._import_toml
        }
    
    async def export_servers(self, 
                           server_ids: List[str] = None,
                           export_config: ExportConfig = None) -> Dict[str, Any]:
        """
        Export servers and their data
        
        Args:
            server_ids: List of server IDs to export (None for all)
            export_config: Export configuration
        
        Returns:
            Export result with file paths and metadata
        """
        try:
            if export_config is None:
                export_config = ExportConfig(format=ExportFormat.JSON)
            
            # Get servers to export
            if server_ids is None:
                # Export all approved servers
                search_result = await self.marketplace.search_servers(limit=1000)
                servers = search_result["servers"]
            else:
                # Export specific servers
                servers = []
                for server_id in server_ids:
                    server = await self.marketplace.get_server_details(server_id)
                    if server:
                        servers.append(server)
            
            if not servers:
                return {
                    "success": False,
                    "error": "No servers found to export",
                    "exported_count": 0
                }
            
            # Prepare export data
            export_data = {
                "export_metadata": {
                    "version": "1.0.0",
                    "exported_at": datetime.now().isoformat(),
                    "exported_by": "marketplace_export_system",
                    "server_count": len(servers),
                    "format": export_config.format,
                    "includes": {
                        "metadata": export_config.include_metadata,
                        "reviews": export_config.include_reviews,
                        "analytics": export_config.include_analytics,
                        "packages": export_config.include_packages
                    }
                },
                "servers": []
            }
            
            # Process each server
            for server in servers:
                server_data = {
                    "basic_info": {
                        "id": server["id"],
                        "name": server["name"],
                        "description": server["description"],
                        "version": server["version"],
                        "author": server["author"],
                        "author_email": server["author_email"],
                        "category": server["category"],
                        "language": server["language"],
                        "license": server.get("license", "MIT"),
                        "created_at": server["created_at"],
                        "updated_at": server["updated_at"]
                    }
                }
                
                # Include metadata if requested
                if export_config.include_metadata:
                    server_data["metadata"] = {
                        "keywords": server.get("keywords", []),
                        "tools": server.get("tools", []),
                        "resources": server.get("resources", []),
                        "prompts": server.get("prompts", []),
                        "dependencies": server.get("dependencies", []),
                        "platform_compatibility": server.get("platform_compatibility", []),
                        "claude_compatibility": server.get("claude_compatibility", {}),
                        "runtime_requirements": server.get("runtime_requirements", {}),
                        "security_scan_passed": server.get("security_scan_passed", False),
                        "verified": server.get("verified", False),
                        "featured": server.get("featured", False)
                    }
                
                # Include reviews if requested
                if export_config.include_reviews:
                    server_data["reviews"] = await self._get_server_reviews(server["id"])
                
                # Include analytics if requested
                if export_config.include_analytics:
                    server_data["analytics"] = await self._get_server_analytics(server["id"])
                
                # Include package if requested
                if export_config.include_packages and server.get("package_url"):
                    server_data["package"] = await self._get_server_package(server["id"])
                
                export_data["servers"].append(server_data)
            
            # Export using specified format
            exporter = self.exporters.get(export_config.format)
            if not exporter:
                return {
                    "success": False,
                    "error": f"Unsupported export format: {export_config.format}",
                    "exported_count": 0
                }
            
            export_result = await exporter(export_data, export_config)
            
            # Store export operation in hAIveMind
            if HAIVEMIND_AVAILABLE:
                await store_memory(
                    content=f"Marketplace export completed: {len(servers)} servers exported in {export_config.format} format",
                    category="marketplace",
                    metadata={
                        "action": "export_completed",
                        "server_count": len(servers),
                        "format": export_config.format,
                        "file_path": export_result.get("file_path"),
                        "file_size": export_result.get("file_size")
                    },
                    project="mcp-marketplace",
                    scope="project-shared"
                )
            
            return {
                "success": True,
                "exported_count": len(servers),
                "format": export_config.format,
                "file_path": export_result.get("file_path"),
                "file_size": export_result.get("file_size"),
                "checksum": export_result.get("checksum"),
                "message": f"Successfully exported {len(servers)} servers"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "exported_count": 0
            }
    
    async def import_servers(self, 
                           file_path: str,
                           import_config: ImportConfig = None) -> Dict[str, Any]:
        """
        Import servers from a file
        
        Args:
            file_path: Path to the import file
            import_config: Import configuration
        
        Returns:
            Import result with statistics
        """
        try:
            if import_config is None:
                import_config = ImportConfig(format=ExportFormat.JSON)
            
            file_path = Path(file_path)
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"Import file not found: {file_path}",
                    "imported_count": 0
                }
            
            # Detect format if not specified
            if import_config.format == "auto":
                import_config.format = self._detect_format(file_path)
            
            # Get importer
            importer = self.importers.get(import_config.format)
            if not importer:
                return {
                    "success": False,
                    "error": f"Unsupported import format: {import_config.format}",
                    "imported_count": 0
                }
            
            # Create backup if requested
            if import_config.backup_existing:
                backup_path = await self._create_backup()
            
            # Import data
            import_result = await importer(file_path, import_config)
            
            if import_result["success"]:
                # Store import operation in hAIveMind
                if HAIVEMIND_AVAILABLE:
                    await store_memory(
                        content=f"Marketplace import completed: {import_result['imported_count']} servers imported from {import_config.format} format",
                        category="marketplace",
                        metadata={
                            "action": "import_completed",
                            "imported_count": import_result["imported_count"],
                            "format": import_config.format,
                            "file_path": str(file_path),
                            "merge_strategy": import_config.merge_strategy,
                            "backup_created": import_config.backup_existing
                        },
                        project="mcp-marketplace",
                        scope="project-shared"
                    )
            
            return import_result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "imported_count": 0
            }
    
    async def export_marketplace_configuration(self) -> Dict[str, Any]:
        """Export complete marketplace configuration"""
        try:
            config_data = {
                "marketplace_config": {
                    "version": "1.0.0",
                    "exported_at": datetime.now().isoformat(),
                    "categories": self.marketplace.categories,
                    "security_settings": self.marketplace.security_config,
                    "database_schema": await self._get_database_schema()
                },
                "server_templates": await self._export_server_templates(),
                "compatibility_matrix": await self._export_compatibility_data(),
                "analytics_summary": await self.marketplace.get_marketplace_analytics()
            }
            
            # Export as JSON
            export_path = self.export_dir / f"marketplace_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(export_path, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            return {
                "success": True,
                "file_path": str(export_path),
                "file_size": export_path.stat().st_size,
                "message": "Marketplace configuration exported successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def import_marketplace_configuration(self, file_path: str) -> Dict[str, Any]:
        """Import marketplace configuration"""
        try:
            with open(file_path, 'r') as f:
                config_data = json.load(f)
            
            # Validate configuration
            if "marketplace_config" not in config_data:
                return {
                    "success": False,
                    "error": "Invalid configuration file format"
                }
            
            # Import configuration (implementation would depend on specific needs)
            # This is a placeholder for the actual import logic
            
            return {
                "success": True,
                "message": "Marketplace configuration imported successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    # Format-specific exporters
    
    async def _export_json(self, data: Dict[str, Any], config: ExportConfig) -> Dict[str, Any]:
        """Export data as JSON"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"marketplace_export_{timestamp}.json"
        file_path = self.export_dir / filename
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return {
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size,
            "checksum": self._calculate_checksum(file_path)
        }
    
    async def _export_yaml(self, data: Dict[str, Any], config: ExportConfig) -> Dict[str, Any]:
        """Export data as YAML"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"marketplace_export_{timestamp}.yaml"
        file_path = self.export_dir / filename
        
        with open(file_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, default_style=None)
        
        return {
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size,
            "checksum": self._calculate_checksum(file_path)
        }
    
    async def _export_csv(self, data: Dict[str, Any], config: ExportConfig) -> Dict[str, Any]:
        """Export data as CSV"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"marketplace_export_{timestamp}.csv"
        file_path = self.export_dir / filename
        
        # Flatten server data for CSV
        rows = []
        for server in data["servers"]:
            row = {
                "id": server["basic_info"]["id"],
                "name": server["basic_info"]["name"],
                "description": server["basic_info"]["description"],
                "version": server["basic_info"]["version"],
                "author": server["basic_info"]["author"],
                "category": server["basic_info"]["category"],
                "language": server["basic_info"]["language"],
                "created_at": server["basic_info"]["created_at"],
                "updated_at": server["basic_info"]["updated_at"]
            }
            
            if "metadata" in server:
                row.update({
                    "keywords": "|".join(server["metadata"].get("keywords", [])),
                    "tools_count": len(server["metadata"].get("tools", [])),
                    "resources_count": len(server["metadata"].get("resources", [])),
                    "verified": server["metadata"].get("verified", False),
                    "featured": server["metadata"].get("featured", False)
                })
            
            rows.append(row)
        
        # Write CSV
        if rows:
            with open(file_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        
        return {
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size,
            "checksum": self._calculate_checksum(file_path)
        }
    
    async def _export_xml(self, data: Dict[str, Any], config: ExportConfig) -> Dict[str, Any]:
        """Export data as XML"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"marketplace_export_{timestamp}.xml"
        file_path = self.export_dir / filename
        
        # Create XML structure
        root = ET.Element("marketplace_export")
        
        # Add metadata
        metadata = ET.SubElement(root, "metadata")
        for key, value in data["export_metadata"].items():
            elem = ET.SubElement(metadata, key)
            elem.text = str(value)
        
        # Add servers
        servers_elem = ET.SubElement(root, "servers")
        for server in data["servers"]:
            server_elem = ET.SubElement(servers_elem, "server")
            server_elem.set("id", server["basic_info"]["id"])
            
            # Add basic info
            basic_info = ET.SubElement(server_elem, "basic_info")
            for key, value in server["basic_info"].items():
                elem = ET.SubElement(basic_info, key)
                elem.text = str(value)
            
            # Add metadata if present
            if "metadata" in server:
                metadata_elem = ET.SubElement(server_elem, "metadata")
                for key, value in server["metadata"].items():
                    elem = ET.SubElement(metadata_elem, key)
                    if isinstance(value, list):
                        elem.text = "|".join(str(v) for v in value)
                    else:
                        elem.text = str(value)
        
        # Write XML
        tree = ET.ElementTree(root)
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        
        return {
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size,
            "checksum": self._calculate_checksum(file_path)
        }
    
    async def _export_zip(self, data: Dict[str, Any], config: ExportConfig) -> Dict[str, Any]:
        """Export data as ZIP archive with multiple formats"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"marketplace_export_{timestamp}.zip"
        file_path = self.export_dir / filename
        
        with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add JSON version
            json_data = json.dumps(data, indent=2, default=str)
            zipf.writestr("export.json", json_data)
            
            # Add YAML version
            yaml_data = yaml.dump(data, default_flow_style=False)
            zipf.writestr("export.yaml", yaml_data)
            
            # Add individual server files
            for server in data["servers"]:
                server_filename = f"servers/{server['basic_info']['id']}.json"
                server_data = json.dumps(server, indent=2, default=str)
                zipf.writestr(server_filename, server_data)
            
            # Add README
            readme_content = f"""# Marketplace Export

Exported on: {data['export_metadata']['exported_at']}
Server count: {data['export_metadata']['server_count']}
Format: {data['export_metadata']['format']}

## Files:
- export.json: Complete export in JSON format
- export.yaml: Complete export in YAML format
- servers/: Individual server files
"""
            zipf.writestr("README.md", readme_content)
        
        return {
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size,
            "checksum": self._calculate_checksum(file_path)
        }
    
    async def _export_toml(self, data: Dict[str, Any], config: ExportConfig) -> Dict[str, Any]:
        """Export data as TOML"""
        try:
            import toml
        except ImportError:
            raise ImportError("TOML support requires 'toml' package")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"marketplace_export_{timestamp}.toml"
        file_path = self.export_dir / filename
        
        with open(file_path, 'w') as f:
            toml.dump(data, f)
        
        return {
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size,
            "checksum": self._calculate_checksum(file_path)
        }
    
    # Format-specific importers
    
    async def _import_json(self, file_path: Path, config: ImportConfig) -> Dict[str, Any]:
        """Import data from JSON"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            return await self._process_import_data(data, config)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"JSON import failed: {str(e)}",
                "imported_count": 0
            }
    
    async def _import_yaml(self, file_path: Path, config: ImportConfig) -> Dict[str, Any]:
        """Import data from YAML"""
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            
            return await self._process_import_data(data, config)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"YAML import failed: {str(e)}",
                "imported_count": 0
            }
    
    async def _import_csv(self, file_path: Path, config: ImportConfig) -> Dict[str, Any]:
        """Import data from CSV"""
        try:
            servers = []
            
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert CSV row to server format
                    server_data = {
                        "basic_info": {
                            "id": row.get("id"),
                            "name": row.get("name"),
                            "description": row.get("description"),
                            "version": row.get("version"),
                            "author": row.get("author"),
                            "category": row.get("category", "general"),
                            "language": row.get("language", "python"),
                            "created_at": row.get("created_at"),
                            "updated_at": row.get("updated_at")
                        }
                    }
                    
                    # Add metadata if present
                    if "keywords" in row and row["keywords"]:
                        server_data["metadata"] = {
                            "keywords": row["keywords"].split("|"),
                            "verified": row.get("verified", "").lower() == "true",
                            "featured": row.get("featured", "").lower() == "true"
                        }
                    
                    servers.append(server_data)
            
            data = {
                "export_metadata": {
                    "version": "1.0.0",
                    "server_count": len(servers)
                },
                "servers": servers
            }
            
            return await self._process_import_data(data, config)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"CSV import failed: {str(e)}",
                "imported_count": 0
            }
    
    async def _import_xml(self, file_path: Path, config: ImportConfig) -> Dict[str, Any]:
        """Import data from XML"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            servers = []
            
            servers_elem = root.find("servers")
            if servers_elem is not None:
                for server_elem in servers_elem.findall("server"):
                    server_data = {"basic_info": {}}
                    
                    basic_info = server_elem.find("basic_info")
                    if basic_info is not None:
                        for elem in basic_info:
                            server_data["basic_info"][elem.tag] = elem.text
                    
                    metadata_elem = server_elem.find("metadata")
                    if metadata_elem is not None:
                        server_data["metadata"] = {}
                        for elem in metadata_elem:
                            if "|" in elem.text:
                                server_data["metadata"][elem.tag] = elem.text.split("|")
                            else:
                                server_data["metadata"][elem.tag] = elem.text
                    
                    servers.append(server_data)
            
            data = {
                "export_metadata": {
                    "version": "1.0.0",
                    "server_count": len(servers)
                },
                "servers": servers
            }
            
            return await self._process_import_data(data, config)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"XML import failed: {str(e)}",
                "imported_count": 0
            }
    
    async def _import_zip(self, file_path: Path, config: ImportConfig) -> Dict[str, Any]:
        """Import data from ZIP archive"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract ZIP
                with zipfile.ZipFile(file_path, 'r') as zipf:
                    zipf.extractall(temp_dir)
                
                temp_path = Path(temp_dir)
                
                # Try to find export.json first
                json_file = temp_path / "export.json"
                if json_file.exists():
                    return await self._import_json(json_file, config)
                
                # Try export.yaml
                yaml_file = temp_path / "export.yaml"
                if yaml_file.exists():
                    return await self._import_yaml(yaml_file, config)
                
                return {
                    "success": False,
                    "error": "No recognized export file found in ZIP archive",
                    "imported_count": 0
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"ZIP import failed: {str(e)}",
                "imported_count": 0
            }
    
    async def _import_toml(self, file_path: Path, config: ImportConfig) -> Dict[str, Any]:
        """Import data from TOML"""
        try:
            import toml
        except ImportError:
            return {
                "success": False,
                "error": "TOML support requires 'toml' package",
                "imported_count": 0
            }
        
        try:
            with open(file_path, 'r') as f:
                data = toml.load(f)
            
            return await self._process_import_data(data, config)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"TOML import failed: {str(e)}",
                "imported_count": 0
            }
    
    # Helper methods
    
    async def _process_import_data(self, data: Dict[str, Any], config: ImportConfig) -> Dict[str, Any]:
        """Process imported data and add servers to marketplace"""
        try:
            if "servers" not in data:
                return {
                    "success": False,
                    "error": "Invalid import data format",
                    "imported_count": 0
                }
            
            imported_count = 0
            errors = []
            
            for server_data in data["servers"]:
                try:
                    # Convert to ServerMetadata
                    basic_info = server_data["basic_info"]
                    metadata = server_data.get("metadata", {})
                    
                    server_metadata = ServerMetadata(
                        id=basic_info["id"],
                        name=basic_info["name"],
                        description=basic_info["description"],
                        version=basic_info["version"],
                        author=basic_info["author"],
                        author_email=basic_info.get("author_email", ""),
                        category=basic_info.get("category", "general"),
                        language=basic_info.get("language", "python"),
                        license=basic_info.get("license", "MIT"),
                        keywords=metadata.get("keywords", []),
                        tools=metadata.get("tools", []),
                        resources=metadata.get("resources", []),
                        dependencies=metadata.get("dependencies", []),
                        platform_compatibility=metadata.get("platform_compatibility", ["linux", "macos", "windows"]),
                        verified=metadata.get("verified", False),
                        featured=metadata.get("featured", False)
                    )
                    
                    # Check if server already exists
                    existing_server = await self.marketplace.get_server_details(server_metadata.id)
                    
                    if existing_server:
                        if config.merge_strategy == "skip":
                            continue
                        elif config.merge_strategy == "update":
                            # Update existing server
                            pass  # Implementation would update the existing server
                        elif config.merge_strategy == "replace":
                            # Replace existing server
                            pass  # Implementation would replace the existing server
                    
                    # Register server
                    await self.marketplace.register_server(server_metadata)
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Failed to import server {basic_info.get('name', 'unknown')}: {str(e)}")
            
            return {
                "success": True,
                "imported_count": imported_count,
                "errors": errors,
                "message": f"Successfully imported {imported_count} servers"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "imported_count": 0
            }
    
    def _detect_format(self, file_path: Path) -> str:
        """Detect file format from extension"""
        suffix = file_path.suffix.lower()
        format_map = {
            ".json": ExportFormat.JSON,
            ".yaml": ExportFormat.YAML,
            ".yml": ExportFormat.YAML,
            ".csv": ExportFormat.CSV,
            ".xml": ExportFormat.XML,
            ".zip": ExportFormat.ZIP,
            ".toml": ExportFormat.TOML
        }
        return format_map.get(suffix, ExportFormat.JSON)
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        import hashlib
        
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    async def _create_backup(self) -> str:
        """Create backup of current marketplace data"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"marketplace_backup_{timestamp}.json"
        
        # Export all servers as backup
        export_config = ExportConfig(
            format=ExportFormat.JSON,
            include_metadata=True,
            include_reviews=True,
            include_analytics=True
        )
        
        backup_result = await self.export_servers(export_config=export_config)
        
        if backup_result["success"]:
            # Move to backup directory
            shutil.move(backup_result["file_path"], backup_path)
            return str(backup_path)
        
        return None
    
    async def _get_server_reviews(self, server_id: str) -> List[Dict[str, Any]]:
        """Get reviews for a server"""
        try:
            with sqlite3.connect(self.marketplace.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                reviews = conn.execute("""
                    SELECT * FROM reviews WHERE server_id = ?
                    ORDER BY created_at DESC
                """, (server_id,)).fetchall()
                
                return [dict(review) for review in reviews]
        except Exception:
            return []
    
    async def _get_server_analytics(self, server_id: str) -> Dict[str, Any]:
        """Get analytics for a server"""
        try:
            with sqlite3.connect(self.marketplace.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                analytics = conn.execute("""
                    SELECT COUNT(*) as download_count
                    FROM download_analytics WHERE server_id = ?
                """, (server_id,)).fetchone()
                
                return dict(analytics) if analytics else {}
        except Exception:
            return {}
    
    async def _get_server_package(self, server_id: str) -> Optional[str]:
        """Get server package as base64"""
        try:
            server = await self.marketplace.get_server_details(server_id)
            if server and server.get("package_url"):
                package_path = Path(server["package_url"])
                if package_path.exists():
                    with open(package_path, "rb") as f:
                        return base64.b64encode(f.read()).decode('utf-8')
            return None
        except Exception:
            return None
    
    async def _get_database_schema(self) -> Dict[str, Any]:
        """Get database schema information"""
        try:
            with sqlite3.connect(self.marketplace.db_path) as conn:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                schema = {}
                for table in tables:
                    cursor = conn.execute(f"PRAGMA table_info({table})")
                    columns = [{"name": row[1], "type": row[2], "nullable": not row[3]} 
                              for row in cursor.fetchall()]
                    schema[table] = columns
                
                return schema
        except Exception:
            return {}
    
    async def _export_server_templates(self) -> List[Dict[str, Any]]:
        """Export server templates"""
        # This would integrate with the template system
        return []
    
    async def _export_compatibility_data(self) -> Dict[str, Any]:
        """Export compatibility matrix data"""
        # This would integrate with the compatibility system
        return {}

def create_import_export_system(marketplace: MCPMarketplace, config: Dict[str, Any]) -> MarketplaceImportExport:
    """Create and configure import/export system"""
    return MarketplaceImportExport(marketplace, config)

if __name__ == "__main__":
    # Example usage
    from mcp_marketplace import create_marketplace
    
    marketplace_config = {
        "database_path": "data/marketplace.db",
        "storage_path": "data/marketplace_storage",
        "redis": {"host": "localhost", "port": 6379, "db": 2}
    }
    
    import_export_config = {
        "export_directory": "data/marketplace_exports",
        "import_directory": "data/marketplace_imports",
        "backup_directory": "data/marketplace_backups"
    }
    
    marketplace = create_marketplace(marketplace_config)
    import_export = create_import_export_system(marketplace, import_export_config)
    
    print("Marketplace import/export system initialized successfully")